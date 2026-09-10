"""Génère les sept familles du pilote CityLab avec 4 phases et 3 LOD.

Le catalogue donne le programme, `AssetFactory/Styles/<style>.json` donne le
regard, `Tools/AssetFactory/style.py` en derive le plan. Ce fichier ne fait que
poser la geometrie de ce plan : aucune dimension, pente, palette ou budget n'y
est ecrit en dur.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
import random
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import building_kit as kit
import style as style_module


# Direction de la camera de revue RTS. Ce n'est pas une valeur de style mais le
# point de vue de la porte : il doit rester identique d'une variante a l'autre,
# sinon l'IoU de silhouette ne compare rien.
RTS_VIEW = (18.0, -21.0, 23.0)

# Le vocabulaire ferme des etapes de chantier du contrat v2, dans l'ordre. Il
# est duplique ici parce que ce fichier tourne dans Blender, sans le paquet
# `Tools.AssetFactory` : `AssetFactory/Schemas/building_construction_v2.schema.json`
# en est la source, et `test_citylab_factory` verifie que les deux concordent.
STAGE_VOCABULARY = (
    "groundworks", "basecourse", "framing", "floors",
    "carpentry", "roofing", "joinery", "finishes",
)
CONSTRUCTION_MIN_STAGES = 5


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--family", required=True)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--skip-previews", action="store_true")
    return parser.parse_args(argv)


def alias_materials(materials: dict[str, bpy.types.Material]) -> None:
    """Nommer les matieres que `citylab_trim_v1` ne distingue pas encore.

    Le style declare lui-meme la dette : `brick_stone` et `timber_plank`
    empruntent une bande voisine jusqu'a `citylab_trim_v2`. Ce sont des alias,
    pas de nouveaux materiaux : rien n'est ajoute au chemin d'export.
    """
    materials["limestone"] = materials["stone"]
    materials["brick"] = materials["stone"]
    materials["slate"] = materials["roof"]
    materials["slate_alt"] = materials["roof_alt"]
    materials["rope"] = materials["bark"]
    materials["coal"] = materials["bark"]
    materials["cloth"] = materials["plaster"]
    materials["hay"] = materials["pale_wood"]
    materials["produce_red"] = materials["ember"]
    materials["produce_green"] = materials["bark"]


def axis_dimensions(plan: style_module.Plan) -> tuple[float, float]:
    """Extension du bati le long de l'axe de portee puis de l'axe de faitage."""
    if plan.span_axis == "x":
        return plan.width, plan.depth
    return plan.depth, plan.width


def foundation(plan: style_module.Plan, materials: dict) -> None:
    projection = plan.foundation_projection
    kit.box("foundation_core", (0.0, 0.0, plan.foundation_height * 0.5),
            (plan.width + 2 * projection, plan.depth + 2 * projection, plan.foundation_height),
            materials["stone"], bevel=plan.foundation_bevel, category="foundation")
    if plan.wing:
        wing = plan.wing
        kit.box("foundation_wing",
                (wing["side"] * (plan.width + wing["width"]) * 0.5,
                 -(plan.depth - wing["depth"]) * 0.5 - wing.get("projection", 0.0),
                 plan.foundation_height * 0.5),
                (wing["width"] + 2 * projection, wing["depth"] + 2 * projection,
                 plan.foundation_height),
                materials["stone"], bevel=plan.foundation_bevel, category="foundation")
    if plan.lean_to:
        lean = plan.lean_to
        kit.box("foundation_lean_to",
                (lean["side"] * (plan.width + lean["depth"]) * 0.5, 0.0,
                 plan.foundation_height * 0.5),
                (lean["depth"] + 2 * projection, plan.depth, plan.foundation_height),
                materials["stone"], bevel=plan.foundation_bevel, category="foundation")


def hollow_block(name: str, centre: tuple[float, float], size: tuple[float, float],
                 bottom: float, height: float, thickness: float,
                 material: bpy.types.Material,
                 category: str = "shell") -> bpy.types.Object:
    """Coque fermee : une boite pleine moins sa cavite. Une ouverture percee y
    debouche sur un vide, ce qui donne son epaisseur au tableau."""
    outer = kit.box(name, (centre[0], centre[1], bottom + height * 0.5),
                    (size[0], size[1], height), material, bevel=0.0, category=category)
    cavity = kit.box(name + "_cavity", (centre[0], centre[1], bottom + height * 0.5),
                     (size[0] - 2 * thickness, size[1] - 2 * thickness, height - 2 * thickness),
                     material, bevel=0.0, category=category)
    kit.cut_openings([outer], [cavity])
    return outer


def gable_wall(name: str, axis: str, position: float, half_width: float,
               bottom: float, peak: float, thickness: float,
               material: bpy.types.Material,
               centre: tuple[float, float] = (0.0, 0.0)) -> bpy.types.Object:
    """Pignon plein entre la sabliere et le faitage.

    `centre` est le centre de l'enveloppe qu'il ferme. Sans lui le pignon
    restait cale sur l'origine tandis que la couverture suivait le niveau du
    haut : sous encorbellement les deux divergeaient de plus d'un demi-metre.
    """
    low, high = position - thickness * 0.5, position + thickness * 0.5
    if axis == "y":
        points = [(-half_width, low, bottom), (half_width, low, bottom), (0.0, low, peak),
                  (-half_width, high, bottom), (half_width, high, bottom), (0.0, high, peak)]
    else:
        points = [(low, -half_width, bottom), (low, half_width, bottom), (low, 0.0, peak),
                  (high, -half_width, bottom), (high, half_width, bottom), (high, 0.0, peak)]
    points = [(x + centre[0], y + centre[1], z) for x, y, z in points]
    faces = [(0, 2, 1), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5)]
    return kit.surface_mesh(name, points, faces, material, category="gable")


def opening_cutter(plan: style_module.Plan, opening: style_module.Opening,
                   material: bpy.types.Material) -> bpy.types.Object:
    """Le volume qui perce le mur, assez profond pour les assises recoupees.

    Un percement centre sur un seul plan de facade suffit tant qu'une baie tient
    dans un niveau. La porte, elle, part du sol et peut recouper plusieurs
    assises : sous une base fruitee le plan recule de 0,37 m d'une assise a
    l'autre, et le percement laissait la jupe pleine.
    """
    out_extent = plan.wall_thickness
    in_extent = plan.wall_thickness * 2.0
    top = opening.sill_z + opening.height
    for storey in plan.storeys:
        if storey.top <= opening.sill_z + 1e-6 or storey.bottom >= top - 1e-6:
            continue
        _, plane, _, _ = style_module.face_of(storey, opening.face)
        recess = (plane - opening.plane) * -opening.outward
        out_extent = max(out_extent, -recess + plan.wall_thickness)
        in_extent = max(in_extent, recess + plan.wall_thickness * 2.0)
    name = f"cut_{opening.kind}_{opening.face}_{opening.along:.3f}_{opening.sill_z:.3f}"
    centre = opening.position((out_extent - in_extent) * 0.5,
                              opening.sill_z + opening.height * 0.5)
    across, thickness, _ = opening.size(opening.width, out_extent + in_extent)
    return kit.box(name, centre, (across, thickness, opening.height), material,
                   bevel=0.0, category="shell")


def opening_reveals(plan: style_module.Plan, materials: dict) -> None:
    """Linteau et appui, a la profondeur du style.

    Les tableaux ont disparu : le boolean traverse une coque creuse, donc
    l'epaisseur du mur se lit deja dans le trou. Deux pieces au lieu de quatre,
    sur quatre faces au lieu d'une.
    """
    if plan.body_role == "annex":
        return
    wood, stone = materials["wood"], materials["stone"]
    reveal = plan.reveal_depth
    for index, opening in enumerate(plan.openings):
        name = f"{opening.kind}_{index}"
        # Chaque niveau a son plan de facade : sous encorbellement, une
        # embrasure calee sur l'emprise nominale flotterait devant le mur.
        depth = -plan.wall_thickness * 0.5
        # Le linteau ne se lit qu'au-dessus de la porte : sous une fenetre de
        # facade il est dans l'ombre du tableau et coutait douze triangles par
        # baie, sur quatre faces.
        if opening.kind == "door":
            lintel_across, lintel_thick, _ = opening.size(opening.width + 2 * reveal,
                                                          plan.wall_thickness)
            kit.box(name + "_lintel",
                    opening.position(depth, opening.sill_z + opening.height + reveal * 0.5),
                    (lintel_across, lintel_thick, reveal), wood,
                    bevel=0.0, category="opening_reveal")
        sill_across, sill_thick, _ = opening.size(opening.width + 2 * reveal,
                                                  plan.wall_thickness + reveal)
        kit.box(name + "_sill",
                opening.position(depth, opening.sill_z - reveal * 0.35),
                (sill_across, sill_thick, reveal * 0.7), stone,
                bevel=0.0, category="opening_reveal")


def wing_ridge_base(plan: style_module.Plan) -> float:
    """Haut de mur de l'aile, deduit de la hauteur de faitage qu'elle vise.

    L'aile est reglee par son faitage et non par son mur : reglee sur la hauteur
    de mur, son arete tombait bien sous celle du corps principal et la projection
    isometrique l'enfouissait entierement.
    """
    if not plan.wing:
        return plan.wall_top
    frame = plan.roof_frame
    ground = plan.storeys[0]
    ratio = float(plan.wing.get("ridge_ratio", 1.0))
    target = ground.bottom + (frame.ridge_z - ground.bottom) * ratio
    span = plan.wing["depth"] if frame.span_axis == "x" else plan.wing["width"]
    rise = math.tan(math.radians(frame.pitch_deg)) * (span * 0.5 + frame.overhang)
    return max(ground.bottom + 1.2, target - rise)


def storey_stage(plan: style_module.Plan, index: int,
                 annex: bool) -> tuple[str, str, str]:
    """L'etape de chantier qui monte ce niveau, et ses deux categories de LOD.

    Un corps accole monte avec le corps principal : ses niveaux vont a
    l'ossature, quel que soit leur rang. Il n'a ni assise propre -- deux
    batiments mitoyens partagent leur fondation -- ni plancher distinct.
    """
    if annex:
        return "framing", "shell_annex", "shell_annex_proxy"
    storey = plan.storeys[index]
    # Les assises de pierre du bas forment le soubassement : elles montent avant
    # les murs. Un niveau de pierre plus haut dans la pile -- un rez de pierre
    # sous un etage a colombage -- appartient a l'ossature, pas au soubassement.
    # Le soubassement, ce sont les assises de pierre du bas de la pile. Une
    # jupe fruitee en fait partie ; un rez de pierre entier aussi.
    stone_base = 0
    while (stone_base < len(plan.storeys)
           and plan.storeys[stone_base].kind == "stone"):
        stone_base += 1
    if index < stone_base:
        return "basecourse", "basecourse", "basecourse_proxy"
    # L'ossature dresse le premier niveau de mur ; les suivants attendent leur
    # plancher.
    if index == stone_base:
        return "framing", "shell", "shell_proxy"
    return "floors", "shell_upper", "shell_upper_proxy"


def shell(plan: style_module.Plan, materials: dict) -> tuple[int, int]:
    """Empiler les niveaux du schema, puis percer.

    La coque n'est plus une boite : c'est une pile de niveaux, chacun avec son
    emprise. Un rez-de-chaussee en pierre est un vrai niveau, et un
    encorbellement fait deborder le niveau du dessus sur celui du dessous. Les
    deux se lisent dans la silhouette a 96 px, ce qu'un soubassement de 0,5 m ne
    faisait pas.
    """
    body = materials["wood"] if plan.wall_system != "dressed_stone" else materials["stone"]
    layers: list[bpy.types.Object] = []
    blocks: list[bpy.types.Object] = []
    annex = plan.body_role == "annex"
    for index, storey in enumerate(plan.storeys):
        material = materials["stone"] if storey.kind == "stone" else body
        centre = storey.centre
        # Le chantier monte le batiment de bas en haut : les assises de pierre
        # d'abord, puis les murs du rez, puis les etages avec leur plancher.
        # Toute la coque appartenait a une seule phase et 1 284 triangles sur
        # 3 024 arrivaient d'un coup a la deuxieme image.
        stage, shell_category, proxy_category = storey_stage(plan, index, annex)
        kit.set_phase(stage, shell_category)
        block = hollow_block(f"shell_storey_{index}", centre,
                             (storey.width, storey.depth), storey.bottom,
                             storey.height, plan.wall_thickness, material,
                             category=shell_category)
        blocks.append(block)
        layers.append(block)
        # Proxy du LOD2 : la meme masse en boite pleine. A 96 px la cavite et
        # les percements ne se voient pas, et ils coutaient l'essentiel du
        # budget du LOD lointain.
        kit.box(f"shell_proxy_{index}",
                (centre[0], centre[1], storey.bottom + storey.height * 0.5),
                (storey.width, storey.depth, storey.height), material,
                bevel=0.0, category=proxy_category)

    # La preuve du percage se lit sur le niveau qui porte la porte, pas sur le
    # premier de la pile : avec une base fruitee, le premier est la jupe.
    door = next((opening for opening in plan.openings if opening.kind == "door"),
                plan.openings[0])
    measured = blocks[door.storey]
    before = kit.planar_edge_loops(measured, 1, door.plane)
    kit.cut_openings(layers, [opening_cutter(plan, opening, body)
                              for opening in plan.openings])
    after = kit.planar_edge_loops(measured, 1, door.plane)
    shell.measured_storey = door.storey
    shell.measured_face = door.face
    # Le percement appartient au mur ; ce qui le remplit -- appui, linteau,
    # vantail, vitrage -- vient a la menuiserie, plus tard dans le chantier.
    kit.set_phase("joinery", "opening_reveal")
    opening_reveals(plan, materials)
    kit.set_phase("floors", "floor")
    storey_bands(plan, materials)
    kit.set_category("jetty_bracket")
    jetty_brackets(plan, materials)

    top = plan.top_storey
    frame = plan.roof_frame
    # Le pignon ferme le triangle entre la sabliere et les chevrons : il se leve
    # avec la charpente, pas avec les murs.
    kit.set_phase("carpentry", "gable")
    if plan.roof_form == "gable":
        # Le pignon remplit exactement le triangle entre la sabliere et les
        # chevrons, sur l'emprise que la charpente couvre. Chaque volee a les
        # siens : c'est ce qui dessine le decrochement contre le ciel.
        frames = [("", frame)]
        if plan.roof_frame_high is not None:
            frames.append(("_high", plan.roof_frame_high))
            high = plan.roof_frame_high
            # Le mur de la volee haute monte du haut du niveau a sa sabliere.
            kit.box("shell_ridge_step",
                    (high.centre[0], high.centre[1],
                     (frame.eave_z + high.eave_z) * 0.5),
                    (high.x1 - high.x0, high.y1 - high.y0,
                     max(0.05, high.eave_z - frame.eave_z)), body,
                    bevel=0.0, category="gable")
            kit.box("shell_proxy_ridge_step",
                    (high.centre[0], high.centre[1],
                     (frame.eave_z + high.eave_z) * 0.5),
                    (high.x1 - high.x0, high.y1 - high.y0,
                     max(0.05, high.eave_z - frame.eave_z)), body,
                    bevel=0.0, category="gable_proxy")
        for suffix, item in frames:
            for side in (-1, 1):
                gable_wall(f"gable{suffix}_{'lo' if side < 0 else 'hi'}", item.ridge_axis,
                           side * item.half_run, item.half_span,
                           item.eave_z, item.ridge_z,
                           plan.wall_thickness, body, centre=item.centre)
    # Les poteaux d'angle dressent le niveau du haut : ils partent avec lui.
    # Rattaches a l'ossature, ils se dressaient dans le vide une etape avant que
    # leur niveau existe.
    kit.set_phase(storey_stage(plan, len(plan.storeys) - 1, annex)[0], "frame_detail")
    for x in (-1, 1):
        for y in (-1, 1):
            kit.box(f"corner_post_{x}_{y}",
                    ((top.x1 if x > 0 else top.x0) - x * plan.corner_post * 0.5,
                     (top.y1 if y > 0 else top.y0) - y * plan.corner_post * 0.5,
                     top.bottom + top.height * 0.5),
                    (plan.corner_post, plan.corner_post, top.height),
                    materials["wood"], bevel=0.0, category="frame_detail")
    # L'aile et l'appentis montent depuis le sol jusqu'au haut du mur, pas
    # depuis le soubassement : avec un rez-de-chaussee en pierre ils flottaient
    # une hauteur d'etage trop bas.
    ground = plan.storeys[0]
    kit.set_phase("framing", "shell")
    if plan.wing:
        wing = plan.wing
        centre = (wing["side"] * (plan.width + wing["width"]) * 0.5,
                  -(plan.depth - wing["depth"]) * 0.5 - wing.get("projection", 0.0))
        size = (wing["width"], wing["depth"])
        # L'aile a sa propre hauteur : a hauteur egale les deux blocs
        # fusionnent sous une seule toiture et la silhouette redevient un bloc
        # unique. C'est le decrochement de faitage des deux references.
        wing_top = wing_ridge_base(plan)
        hollow_block("shell_wing", centre, size, ground.bottom,
                     wing_top - ground.bottom, plan.wall_thickness, body)
        kit.box("shell_proxy_wing",
                (centre[0], centre[1], (ground.bottom + wing_top) * 0.5),
                (size[0], size[1], wing_top - ground.bottom), body,
                bevel=0.0, category="shell_proxy")
    if plan.lean_to:
        lean = plan.lean_to
        centre = (lean["side"] * (plan.width + lean["depth"]) * 0.5, 0.0)
        size = (lean["depth"], plan.depth)
        hollow_block("shell_lean_to", centre, size, ground.bottom,
                     lean["height"], plan.wall_thickness, body)
        kit.box("shell_proxy_lean_to",
                (centre[0], centre[1], ground.bottom + lean["height"] * 0.5),
                (size[0], size[1], lean["height"]), body,
                bevel=0.0, category="shell_proxy")
    return before, after


def storey_bands(plan: style_module.Plan, materials: dict) -> None:
    """Bandeau d'etage : la ligne de plancher, lue depuis la rue.

    L'etape « planchers » du contrat v2 n'avait de geometrie que sur les
    batiments a encorbellement. Un plancher interieur ne se voit pas ; le
    bandeau qui marque son niveau sur la facade, si, et il coute une boite par
    joint de niveau.
    """
    wood = materials["wood"]
    band = plan.jetty_bracket * 0.72
    for index, storey in enumerate(plan.storeys[1:], start=1):
        below = plan.storeys[index - 1]
        if storey.kind == "stone" and below.kind == "stone":
            # Deux assises de pierre se suivent sans plancher entre elles.
            continue
        kit.box(f"storey_band_{index}",
                (storey.centre[0], storey.centre[1], storey.bottom + band * 0.5),
                (max(storey.width, below.width) + band * 0.5,
                 max(storey.depth, below.depth) + band * 0.5, band),
                wood, bevel=0.0, category="floor")


def jetty_brackets(plan: style_module.Plan, materials: dict) -> None:
    """Corbeaux sous le debord : sans eux l'etage flotte."""
    if plan.jetty_overhang <= 0.0:
        return
    wood = materials["wood"]
    size = plan.jetty_bracket
    for index, storey in enumerate(plan.storeys[1:], start=1):
        below = plan.storeys[index - 1]
        if storey.y0 >= below.y0 - 1e-6:
            continue
        overhang = below.y0 - storey.y0
        count = max(2, int(storey.width // 1.6))
        for slot in range(count):
            ratio = (slot + 0.5) / count
            kit.box(f"jetty_bracket_{index}_{slot}",
                    (storey.x0 + ratio * storey.width,
                     storey.y0 + overhang * 0.5,
                     storey.bottom - size * 0.5),
                    (size, overhang, size), wood,
                    bevel=0.0, category="jetty_bracket")


def roof_carpentry(plan: style_module.Plan, materials: dict,
                   frame: style_module.RoofFrame) -> None:
    """La charpente : sabliere, panne faitiere, chevrons.

    Elle n'existait que comme deux triangles de pignon, et la couverture flottait
    a la place des chevrons au lieu de reposer dessus. Un batiment est un chemin
    de charge : le niveau du haut porte la sabliere, la sabliere porte les
    chevrons, les chevrons portent la couverture.
    """
    wood = materials["wood"]
    reach = frame.half_span + frame.overhang

    # Sabliere : une piece sur chaque long-pan, au nu du niveau qu'elle couronne.
    for side in (-1, 1):
        name = "wall_plate_lo" if side < 0 else "wall_plate_hi"
        centre = frame.local(side * (frame.half_span - frame.plate * 0.5), 0.0,
                             frame.eave_z - frame.plate * 0.5)
        size = ((frame.plate, frame.run, frame.plate) if frame.span_axis == "x"
                else (frame.run, frame.plate, frame.plate))
        kit.box(name, centre, size, wood, bevel=0.0, category="roof_frame")

    # Panne faitiere, sous le faite.
    ridge_centre = frame.local(0.0, 0.0, frame.ridge_z - frame.ridge_beam * 0.5)
    ridge_length = frame.run + 2 * frame.overhang
    ridge_size = ((frame.ridge_beam, ridge_length, frame.ridge_beam)
                  if frame.span_axis == "x"
                  else (ridge_length, frame.ridge_beam, frame.ridge_beam))
    kit.box("ridge_beam", ridge_centre, ridge_size, wood, bevel=0.0,
            category="roof_frame")

    # Chevrons : de la sabliere au faite, a l'ecartement que le style declare.
    bays = max(2, int(round(frame.run / frame.rafter_spacing)))
    for index in range(bays + 1):
        along = -frame.half_run + index * (frame.run / bays)
        for rake in (-1, 1):
            side = "l" if rake < 0 else "r"
            kit.beam_between(
                "rafter_" + str(index) + "_" + side,
                frame.local(rake * reach, along, frame.eave_z),
                frame.local(0.0, along, frame.ridge_z),
                frame.rafter_depth, wood, bevel=0.0, category="roof_frame",
                width=frame.rafter)


def roof_covering(plan: style_module.Plan, materials: dict,
                  frame: style_module.RoofFrame, name: str) -> None:
    """La couverture d'une volee, posee sur ses chevrons."""
    covering, eave = materials["roof"], materials["eave"]
    lift = frame.covering_lift
    kit.roof_surface(name, plan.roof_form, frame.half_span, frame.half_run,
                     frame.span_axis, frame.eave_z + lift, frame.rise, frame.overhang,
                     plan.roof_thickness, covering, centre=frame.centre)
    kit.eave_strip(name + "_eave", frame.half_span, frame.half_run, frame.span_axis,
                   frame.eave_z + lift, frame.overhang, plan.eave_depth,
                   plan.eave_teeth_per_m, eave,
                   all_sides=plan.roof_form == "hipped")


def roof(plan: style_module.Plan, materials: dict) -> None:
    frame = plan.roof_frame
    centre = frame.centre
    covering = materials["roof"]
    lift = frame.covering_lift

    roof_covering(plan, materials, frame, "roof_main")
    if plan.roof_frame_high is not None:
        # La volee haute : sa propre couverture, sur sa propre charpente. Le mur
        # qui la porte monte d'un cran, et le pignon du decrochement ferme le
        # joint entre les deux.
        high = plan.roof_frame_high
        roof_covering(plan, materials, high, "roof_high")

    if plan.wing:
        wing = plan.wing
        wing_centre = (wing["side"] * (plan.width + wing["width"]) * 0.5,
                       -(plan.depth - wing["depth"]) * 0.5 - wing.get("projection", 0.0))
        # Le faitage de l'aile est **perpendiculaire** au principal. Parallele,
        # l'aile se fondait dans la masse : mesure a l'appui, elle n'apparaissait
        # pas du tout dans la silhouette. Deux pignons a angle droit font un
        # decrochement que l'œil lit, et c'est la composition de la reference 1.
        wing_axis = frame.ridge_axis
        wing_span = wing["depth"] if frame.span_axis == "x" else wing["width"]
        wing_run = wing["width"] if frame.span_axis == "x" else wing["depth"]
        wing_top = wing_ridge_base(plan)
        wing_rise = math.tan(math.radians(frame.pitch_deg)) * (wing_span * 0.5 + frame.overhang)
        kit.roof_surface("roof_wing", "gable", wing_span * 0.5, wing_run * 0.5,
                         wing_axis, wing_top + lift, wing_rise, frame.overhang,
                         plan.roof_thickness, covering, centre=wing_centre)
        for face in (-1, 1):
            name = "gable_wing_lo" if face < 0 else "gable_wing_hi"
            gable_wall(name, frame.span_axis, face * wing_run * 0.5, wing_span * 0.5,
                       wing_top, wing_top + wing_rise,
                       plan.wall_thickness, materials["wood"], centre=wing_centre)

    # Croupe transversale : une aile qui sort de la facade, pignon en avant. Son
    # mur monte jusqu'a sa propre sabliere et sa couverture repose dessus.
    facing = int(plan.review.get("camera_facing_side_x", 1))

    # Croupe transversale et lucarnes se posent sur un **rampant**, jamais sur un
    # pignon. Elles etaient calees sur `frame.y0`, qui est une extremite de
    # faitage quand la pente court sur x : elles traversaient le versant au lieu
    # d'y mourir. Leur faitage s'arrete desormais la ou il rencontre la pente,
    # calcule par `slope_meets`.
    cross = plan.cross_gable
    if cross:
        secondary_roof(plan, materials, "cross", cross["width"],
                       frame.ridge_z - cross["ridge_drop"], cross["offset"] * frame.run,
                       facing, wall_from=plan.top_storey.bottom)

    for index, dormer in enumerate(plan.dormers):
        apex = frame.eave_z + dormer["height"]
        secondary_roof(plan, materials, f"dormer_{index}", dormer["width"], apex,
                       dormer["offset"], facing,
                       wall_from=frame.eave_z - plan.storey_m * 0.22,
                       category="dormer")


def secondary_roof(plan: style_module.Plan, materials: dict, name: str,
                   width: float, apex: float, offset: float, facing: int,
                   wall_from: float, category: str = "dormer") -> None:
    """Une toiture secondaire posee sur un rampant, dont le faitage y meurt.

    `apex` est la hauteur de son faitage. La profondeur n'est pas choisie : elle
    est celle a laquelle ce faitage rencontre la pente principale. Le mur qui la
    porte monte depuis `wall_from` jusqu'a l'egout de la pente a cet endroit.
    """
    frame = plan.roof_frame
    covering = materials["roof"]
    wood = materials["wood"]
    lift = frame.covering_lift

    eave = frame.eave_side(facing)
    outer = eave + facing * frame.overhang * 0.6
    inner = frame.centre[0] if frame.span_axis == "x" else frame.centre[1]
    inner = inner + facing * frame.slope_meets(apex)
    depth = abs(outer - inner)
    if depth < width * 0.25 or apex <= frame.eave_z + 0.05:
        return
    middle = (outer + inner) * 0.5
    along = (frame.centre[1] if frame.span_axis == "x" else frame.centre[0]) + offset

    # Le mur de la lucarne monte du plancher qu'elle perce jusqu'a son egout.
    face_centre = ((outer - facing * width * 0.0, along) if frame.span_axis == "x"
                   else (along, outer))
    wall_centre = ((middle, along) if frame.span_axis == "x" else (along, middle))
    seat = frame.slope_z(frame.slope_meets(apex)) if False else frame.eave_z
    wall_size = ((depth, width) if frame.span_axis == "x" else (width, depth))
    kit.box(name + "_wall", (wall_centre[0], wall_centre[1],
                             (wall_from + seat) * 0.5),
            (wall_size[0], wall_size[1], max(0.05, seat - wall_from)), wood,
            bevel=0.0, category=category)

    rise = apex - frame.eave_z
    kit.roof_surface(name + "_roof", "gable", width * 0.5, depth * 0.5,
                     frame.ridge_axis, frame.eave_z + lift, rise,
                     frame.overhang * 0.35, plan.roof_thickness, covering,
                     centre=wall_centre)
    # Le pignon de la lucarne ferme son cote exterieur, a l'aplomb de sa facade.
    gable_wall(name + "_gable", frame.span_axis,
               facing * depth * 0.5, width * 0.5,
               frame.eave_z, apex, plan.wall_thickness * 0.6, wood,
               centre=wall_centre)


def opening_quad(name: str, opening: style_module.Opening, depth: float,
                 along: float, width: float, height: float,
                 material: bpy.types.Material, category: str,
                 bottom: float | None = None) -> None:
    """Un plan pose dans le plan d'une baie, oriente selon sa face."""
    z0 = opening.sill_z if bottom is None else bottom
    z1 = z0 + height
    offset = opening.plane + opening.outward * depth
    half = width * 0.5
    if opening.axis == "y":
        points = [(along - half, offset, z0), (along + half, offset, z0),
                  (along + half, offset, z1), (along - half, offset, z1)]
    else:
        points = [(offset, along - half, z0), (offset, along + half, z0),
                  (offset, along + half, z1), (offset, along - half, z1)]
    kit.surface_mesh(name, points, [(0, 1, 2, 3)], material, category=category)


def window_pane(name: str, opening: style_module.Opening, depth: float,
                inset: float, mullion: float, glass: bpy.types.Material,
                wood: bpy.types.Material) -> None:
    """Le vitrage et sa croisee.

    Une baie etait un rectangle lumineux plein : cela se lit comme un trou, pas
    comme une fenetre. Le vitrage reste un plan -- il porte la lumiere a tous les
    LOD -- et la croisee est faite de deux plans sombres poses devant, ranges
    dans une categorie que le LOD1 retire. Quatre triangles de plus au LOD0, zero
    au-dela.
    """
    width = max(0.05, opening.width - 2.0 * inset)
    height = max(0.05, opening.height - 2.0 * inset)
    base = opening.sill_z + inset
    # Le vitrage se pose au nu du percement. Pose en avant il se lisait comme un
    # autocollant lumineux ; enfonce dans le tableau il disparaissait sous le
    # linteau, l'angle de revue etant plongeant. C'est l'epaisseur du mur, que le
    # boolean a ouverte, qui fait l'embrasure.
    opening_quad(name, opening, 0.0, opening.along, width, height, glass,
                 "opening_plane", bottom=base)
    # Meneau et traverse, devant le verre : ils se decoupent en sombre dessus.
    front = depth
    opening_quad(name + "_mullion", opening, front, opening.along,
                 mullion, height, wood, "opening_detail", bottom=base)
    opening_quad(name + "_transom", opening, front, opening.along,
                 width, mullion, wood, "opening_detail",
                 bottom=base + (height - mullion) * 0.5)


def opening_leaves(plan: style_module.Plan, materials: dict) -> None:
    """Vantail, plan d'interieur et volets : ce qui remplit le trou perce."""
    wood, iron, ember = materials["wood"], materials["iron"], materials["ember"]
    reveal = plan.reveal_depth
    for index, opening in enumerate(plan.openings):
        name = f"{opening.kind}_{index}"
        if opening.kind == "door":
            across, thick, _ = opening.size(opening.width * 0.94, reveal * 0.35)
            kit.box(name + "_leaf",
                    opening.position(-reveal, opening.sill_z + opening.height * 0.5),
                    (across, thick, opening.height * 0.97),
                    wood, bevel=0.0, category="opening_plane")
            across, thick, _ = opening.size(opening.width * 0.8, reveal * 0.12)
            kit.box(name + "_strap",
                    opening.position(-reveal * 1.2, opening.sill_z + opening.height * 0.72),
                    (across, thick, opening.height * 0.09),
                    iron, bevel=0.0, category="hardware")
            continue
        # Le plan interieur est ce qui fait briller une fenetre la nuit. C'est un
        # plan : le construire en boite coutait douze triangles la ou deux
        # suffisent, et sur quatre facades la difference se compte en milliers.
        # Le vitrage se pose pres du nu, pas au fond du mur : enfonce de la
        # moitie de l'epaisseur, le linteau le cachait entierement a l'angle de
        # revue, qui est plongeant.
        window_pane(name + "_interior", opening, plan.reveal_depth * 0.16,
                    plan.window_frame_inset, plan.window_mullion, ember, wood)
        if opening.shutters:
            for side in (-1, 1):
                opening_quad(f"{name}_shutter_{side}", opening, reveal * 0.4,
                             opening.along + side * opening.width * 0.72,
                             opening.width * 0.42, opening.height, wood, "hardware")


def chimney(plan: style_module.Plan, offset: float, materials: dict) -> None:
    section = plan.corner_post * 2.2
    top = plan.ridge_z + section
    kit.box("chimney", (offset, plan.depth * 0.22, plan.wall_top + (top - plan.wall_top) * 0.5),
            (section, section, top - plan.wall_top), materials["stone"],
            bevel=plan.wall_bevel, category="chimney")
    kit.box("chimney_cap", (offset, plan.depth * 0.22, top + section * 0.12),
            (section * 1.3, section * 1.3, section * 0.24), materials["iron"],
            bevel=0.0, category="chimney")


# --------------------------------------------------------------------------
# Marqueurs d'identite
#
# Le catalogue declare, famille par famille, ce qui doit rendre un batiment
# reconnaissable : `arcade` pour le marche, `buttresses` et `lancet_windows`
# pour la chapelle, `cross_braced_doors` et `loft` pour la grange. Trente-huit
# marqueurs declares au total.
#
# Ils n'etaient pas poses. `function_details` branchait sur la fonction et
# produisait quelques accessoires au sol, toujours les memes : quatorze
# marqueurs sur trente-huit manquaient, et ce sont exactement ceux qui font
# qu'une grange n'est pas une chapelle. Les sept familles etaient la meme
# maison. Le cas le plus net : la chapelle n'avait **aucune fenetre**, parce que
# `plan_building` retire les baies ordinaires quand `lancet_windows` est
# declare -- et que personne ne posait de lancette.
#
# Un marqueur est donc une entree de registre, et la porte D-1 refuse un
# marqueur declare qui n'a pas ete pose.
# --------------------------------------------------------------------------

IDENTITY_BUILDERS: dict[str, object] = {}


def marker(name: str):
    """Enregistrer le constructeur d'un marqueur d'identite."""
    def register(function):
        if name in IDENTITY_BUILDERS:
            raise ValueError(f"Marqueur declare deux fois : {name}")
        IDENTITY_BUILDERS[name] = function
        return function
    return register


@dataclasses.dataclass(frozen=True)
class MarkerSite:
    """Ce dont un marqueur a besoin pour se poser sur un batiment reel.

    Aucun marqueur ne calcule ses coordonnees a partir de nombres absolus : ils
    se posent sur le rez, sur la facade, sur le haut de mur ou sur le faitage,
    parce que ce sont les seules references qui suivent le schema.
    """

    plan: style_module.Plan
    materials: dict
    variant: dict
    rng: random.Random

    @property
    def ground(self) -> style_module.Storey:
        return self.plan.storeys[0]

    @property
    def front(self) -> float:
        """Plan de facade du rez : le nu sur lequel un marqueur se plaque."""
        return self.ground.y0

    @property
    def side(self) -> float:
        return self.ground.x1

    def material(self, key: str):
        return self.materials[key]


def door_of(plan: style_module.Plan) -> style_module.Opening:
    return next(item for item in plan.openings if item.kind == "door")


# --- residence ------------------------------------------------------------

@marker("shutters")
def _shutters(site: MarkerSite) -> None:
    """Pose par `opening_leaves`. Le catalogue le declare, le plan le force."""


@marker("hearth")
def _hearth(site: MarkerSite) -> None:
    plan, materials = site.plan, site.materials
    if site.variant["chimney"] and "chimney_stack" not in plan.appendages:
        chimney(plan, plan.width * 0.28, materials)
    # La hotte du foyer sort du pignon : c'est ce qui se voit d'un foyer depuis
    # la rue, le conduit restant a l'interieur.
    frame = plan.roof_frame
    kit.box("hearth_hood", (plan.width * 0.28, frame.centre[1], plan.wall_top - 0.55),
            (0.9, 0.34, 1.1), site.material("stone"), bevel=0.0,
            category="appendage_detail")


@marker("bench")
def _bench(site: MarkerSite) -> None:
    plan, pale = site.plan, site.material("pale_wood")
    kit.box("house_bench", (-plan.width * 0.30, site.front - 0.95, 0.44),
            (1.9, 0.52, 0.16), pale, bevel=0.0)
    for edge in (-1, 1):
        kit.box(f"house_bench_leg_{edge}",
                (-plan.width * 0.30 + edge * 0.78, site.front - 0.95, 0.18),
                (0.14, 0.44, 0.36), pale, bevel=0.0)


@marker("woodpile")
def _woodpile(site: MarkerSite) -> None:
    plan = site.plan
    for index in range(3):
        kit.cylinder(f"house_firewood_{index}",
                     (plan.width * 0.38, site.front - 0.65 - index * 0.26, 0.14),
                     0.14, 0.95, site.material("bark"),
                     rotation=(0.0, math.pi / 2, 0.0), vertices=8, bevel=0.0)


@marker("flower_boxes")
def _flower_boxes(site: MarkerSite) -> None:
    plan, wood = site.plan, site.material("wood")
    sills = sorted(item.sill_z for item in plan.openings
                   if item.kind == "window" and item.face == "front")
    ledge = sills[0] if sills else site.ground.bottom + plan.storey_m * 0.55
    for edge in (-1, 1):
        kit.box(f"flower_box_{edge}",
                (edge * plan.width * 0.31, site.front - 0.18, ledge - 0.15),
                (1.1, 0.36, 0.30), wood, bevel=0.0)
        # Une jardiniere vide est une caisse. Trois touffes suffisent a la lire.
        for slot in (-1, 0, 1):
            kit.box(f"flower_tuft_{edge}_{slot}",
                    (edge * plan.width * 0.31 + slot * 0.34,
                     site.front - 0.18, ledge + 0.06),
                    (0.26, 0.28, 0.22), site.material("bark"),
                    bevel=0.0, category="produce")


# --- grenier --------------------------------------------------------------

@marker("raised_floor")
def _raised_floor(site: MarkerSite) -> None:
    """Le grenier est porte sur pilotis champignons : le grain reste au sec."""
    plan, stone, wood = site.plan, site.material("stone"), site.material("wood")
    lift = site.ground.bottom
    for x in (-1, 1):
        for y in (-1, 1):
            centre = (x * plan.width * 0.34, y * plan.depth * 0.32)
            kit.box(f"staddle_post_{x}_{y}", (centre[0], centre[1], lift * 0.45),
                    (0.28, 0.28, max(0.2, lift * 0.9)), stone,
                    bevel=0.0, category="appendage")
            kit.box(f"staddle_cap_{x}_{y}", (centre[0], centre[1], lift * 0.95),
                    (0.62, 0.62, 0.16), stone, bevel=0.0, category="appendage")
    kit.box("granary_deck", (0.0, 0.0, lift - 0.09),
            (plan.width * 0.92, plan.depth * 0.92, 0.18), wood,
            bevel=0.0, category="appendage")


@marker("grain_sacks")
def _grain_sacks(site: MarkerSite) -> None:
    for index, edge in enumerate((-1, 0, 1)):
        kit.cylinder(f"grain_sack_{index}", (edge * 1.5, site.front - 0.7, 0.55),
                     0.42, 1.1, site.material("cloth"), vertices=10, bevel=0.0)


@marker("ventilation_slits")
def _ventilation_slits(site: MarkerSite) -> None:
    plan, iron = site.plan, site.material("iron")
    for edge in (-1, 1):
        kit.box(f"grain_vent_{edge}",
                (edge * plan.width * 0.28, site.front - 0.10, plan.wall_top - 0.55),
                (0.9, 0.10, 0.12), iron, bevel=0.0, category="hardware")


@marker("hoist")
def _hoist(site: MarkerSite) -> None:
    """Lucarne de chargement : une boite en avant du nu, pas une poutre fine.

    Une poutre de 16 cm disparait a 64 px. La scierie a montre qu'un volume
    pose devant la facade se lit, au meme budget. Le grenier a rate C-1 de
    0,007 avec le treuil en fil.
    """
    plan, wood = site.plan, site.material("wood")
    head = plan.wall_top - 0.15
    kit.box("hoist_house", (0.0, site.front - 1.15, head),
            (1.95, 2.25, 1.55), wood, bevel=0.0, category="appendage")
    kit.box("hoist_hood", (0.0, site.front - 2.05, head + 0.95),
            (2.15, 1.05, 0.32), site.material("roof"), bevel=0.0,
            category="appendage")
    kit.beam_between("hoist_rope", (0.0, site.front - 1.42, head - 0.2),
                     (0.0, site.front - 1.42, head - 1.45), 0.05,
                     site.material("bark"), 0.0, category="hardware")


@marker("grain_emblem")
def _grain_emblem(site: MarkerSite) -> None:
    """Une gerbe peinte au pignon : l'enseigne du grenier."""
    plan, pale = site.plan, site.material("pale_wood")
    frame = plan.roof_frame
    height = frame.eave_z + (frame.ridge_z - frame.eave_z) * 0.45
    for slot in (-1, 0, 1):
        kit.beam_between(f"grain_emblem_{slot}",
                         (slot * 0.18, site.front - 0.06, height - 0.35),
                         (slot * 0.42, site.front - 0.06, height + 0.35),
                         0.09, pale, 0.0, category="hardware")


# --- entrepot -------------------------------------------------------------

@marker("loading_dock")
def _loading_dock(site: MarkerSite) -> None:
    """Quai et auvent : l'entrepot se lit a la rue par ce qui depasse le nu.

    Le quai seul etait trop bas pour la silhouette RTS -- 0,7 m sous un
    cottage, invisible a 64 px. L'auvent est le meme levier que le chantier
    de la scierie : un volume devant la facade, presque sans triangles.
    """
    plan, stone, wood = site.plan, site.material("stone"), site.material("wood")
    height = max(0.55, site.ground.bottom)
    depth = min(2.35, plan.depth * 0.34)
    width = plan.width * 0.68
    kit.box("loading_dock", (0.0, site.front - depth * 0.5, height * 0.5),
            (width, depth, height), stone, bevel=0.0, category="foundation")
    head = site.ground.bottom + plan.storey_m * 0.90
    front = site.front - depth
    for edge in (-1, 1):
        kit.box(f"loading_canopy_post_{edge}",
                (edge * width * 0.42, front + 0.18,
                 site.ground.bottom + (head - site.ground.bottom) * 0.5),
                (0.22, 0.22, head - site.ground.bottom), wood,
                bevel=0.0, category="appendage")
    kit.box("loading_canopy",
            (0.0, site.front - depth * 0.5, head + 0.12),
            (width + 0.4, depth + 0.25, 0.18), site.material("roof"),
            bevel=0.0, category="appendage")


@marker("double_door")
def _double_door(site: MarkerSite) -> None:
    """Deux vantaux et leur poteau meneau, sur la porte large du plan.

    Le catalogue demandait deja une porte large -- `plan_building` la tire de ce
    marqueur -- mais rien ne la montrait comme double.
    """
    plan, wood, iron = site.plan, site.material("wood"), site.material("iron")
    door = door_of(plan)
    across, thick, _ = door.size(0.14, plan.reveal_depth * 0.9)
    kit.box("double_door_mullion",
            door.position(-plan.reveal_depth * 0.5,
                          door.sill_z + door.height * 0.5),
            (across, thick, door.height * 0.98), wood,
            bevel=0.0, category="opening_detail")
    for edge in (-1, 1):
        across, thick, _ = door.size(door.width * 0.16, plan.reveal_depth * 0.3)
        centre = door.position(-plan.reveal_depth * 1.1,
                               door.sill_z + door.height * 0.62)
        along = door.along + edge * door.width * 0.3
        centre = ((along, centre[1], centre[2]) if door.axis == "y"
                  else (centre[0], along, centre[2]))
        kit.box(f"double_door_ring_{edge}", centre, (across, thick, 0.12),
                iron, bevel=0.0, category="hardware")


@marker("crates")
def _crates(site: MarkerSite) -> None:
    plan, wood = site.plan, site.material("wood")
    for index, (x, y, size) in enumerate((
            (-plan.width * 0.30, 1.35, 0.78),
            (-plan.width * 0.30 + 0.86, 1.15, 0.62),
            (-plan.width * 0.30 + 0.30, 1.30, 0.54))):
        kit.box(f"warehouse_crate_{index}",
                (x, site.front - y, size * 0.5 + (0.78 if index == 2 else 0.0)),
                (size, size, size), wood, bevel=0.0)


@marker("barrels")
def _barrels(site: MarkerSite) -> None:
    plan, wood = site.plan, site.material("wood")
    for index, edge in enumerate((-1, 1)):
        kit.cylinder(f"warehouse_barrel_{index}",
                     (edge * plan.width * 0.32, site.front - 1.2, 0.62),
                     0.48, 1.25, wood, vertices=10, bevel=0.0)


@marker("pulley")
def _pulley(site: MarkerSite) -> None:
    """Potence de dechargement, en avant du nu, pas une poulie de 14 cm."""
    plan, wood, iron = site.plan, site.material("wood"), site.material("iron")
    kit.beam_between("warehouse_jib",
                     (0.0, site.front - 0.12, plan.wall_top - 0.28),
                     (0.0, site.front - 2.15, plan.wall_top - 0.28),
                     0.18, wood, 0.0, category="appendage")
    kit.cylinder("warehouse_pulley", (0.0, site.front - 2.05, plan.wall_top - 0.42),
                 0.28, 0.14, iron, rotation=(math.pi / 2, 0.0, 0.0),
                 vertices=10, bevel=0.0, category="appendage_detail")


# --- marche ---------------------------------------------------------------

@marker("arcade")
def _arcade(site: MarkerSite) -> None:
    """Une galerie de piliers devant la facade, la signature d'une halle.

    Elle etait declaree au catalogue et absente de la geometrie : le marche
    ressemblait a une maison avec deux etals poses devant.
    """
    plan, stone, wood = site.plan, site.material("stone"), site.material("wood")
    # Profondeur bornee : l'allonger a rapproche a-b jusqu'a IoU 0,817.
    # La hauteur, elle, se lit contre la masse sans agrandir l'emprise --
    # marche c rate C-1 de 0,023 avec l'arcade a 0,86 etage.
    depth = min(2.1, plan.depth * 0.28)
    head = min(plan.wall_top - 0.28, site.ground.bottom + plan.storey_m * 1.28)
    bays = max(3, int(round(plan.width / 2.4)))
    span = plan.width / bays
    for index in range(bays + 1):
        x = -plan.width * 0.5 + index * span
        kit.box(f"arcade_pier_{index}", (x, site.front - depth + 0.18,
                                         site.ground.bottom + (head - site.ground.bottom) * 0.5),
                (0.30, 0.30, head - site.ground.bottom), stone,
                bevel=plan.wall_bevel, category="appendage")
    for index in range(bays):
        # L'arc est un linteau cintre approche par trois claveaux : a la
        # distance de revue, trois suffisent a lire une arcade.
        x = -plan.width * 0.5 + (index + 0.5) * span
        for slot, (offset, lift) in enumerate(((-0.30, 0.0), (0.0, 0.13), (0.30, 0.0))):
            kit.box(f"arcade_voussoir_{index}_{slot}",
                    (x + offset * span, site.front - depth + 0.18, head + 0.16 + lift),
                    (span * 0.36, 0.30, 0.26), stone, bevel=0.0,
                    category="appendage_detail")
    kit.box("arcade_beam", (0.0, site.front - depth + 0.18, head + 0.46),
            (plan.width, 0.34, 0.24), wood, bevel=0.0, category="appendage")
    kit.box("arcade_deck", (0.0, site.front - depth * 0.5, site.ground.bottom - 0.07),
            (plan.width, depth, 0.14), stone, bevel=0.0, category="appendage")


@marker("stalls")
def _stalls(site: MarkerSite) -> None:
    plan, wood = site.plan, site.material("wood")
    for edge in (-1, 1):
        kit.box(f"stall_counter_{edge}",
                (edge * plan.width * 0.26, site.front - 1.4, 0.86),
                (2.8, 0.9, 0.22), wood, bevel=0.0)
        for slot in (-1, 1):
            kit.box(f"stall_leg_{edge}_{slot}",
                    (edge * plan.width * 0.26 + slot * 1.2, site.front - 1.4, 0.38),
                    (0.14, 0.7, 0.75), wood, bevel=0.0, category="appendage_detail")


@marker("awnings")
def _awnings(site: MarkerSite) -> None:
    plan, cloth, wood = site.plan, site.material("cloth"), site.material("wood")
    for edge in (-1, 1):
        kit.box(f"stall_awning_{edge}",
                (edge * plan.width * 0.26, site.front - 1.1, 2.35),
                (3.1, 2.0, 0.14), cloth, rotation=(0.18, 0.0, 0.0), bevel=0.0)
        for slot in (-1, 1):
            kit.box(f"awning_post_{edge}_{slot}",
                    (edge * plan.width * 0.26 + slot * 1.45, site.front - 1.95, 1.1),
                    (0.11, 0.11, 2.2), wood, bevel=0.0, category="appendage_detail")


@marker("goods")
def _goods(site: MarkerSite) -> None:
    pale = site.material("pale_wood")
    for index, x in enumerate((-2.4, -0.8, 0.8, 2.4)):
        kit.cylinder(f"market_basket_{index}", (x, site.front - 1.9, 0.24),
                     0.34, 0.48, pale, vertices=8, bevel=0.0, category="produce")


@marker("hanging_sign")
def _hanging_sign(site: MarkerSite) -> None:
    """Le schema en pose deja une sur `town_house` ; sinon, la voici."""
    plan = site.plan
    if "hanging_sign" in plan.appendages:
        return
    wood, iron = site.material("wood"), site.material("iron")
    head = site.ground.bottom + plan.storey_m * 0.86
    reach = 1.05
    kit.box("sign_bracket", (plan.width * 0.32, site.front - reach * 0.5, head),
            (0.09, reach, 0.09), iron, bevel=0.0, category="appendage_detail")
    kit.box("sign_board", (plan.width * 0.32, site.front - reach, head - 0.42),
            (0.66, 0.06, 0.48), wood, bevel=0.0, category="appendage_detail")


# --- forge ----------------------------------------------------------------

@marker("brick_chimney")
def _brick_chimney(site: MarkerSite) -> None:
    plan = site.plan
    if "chimney_stack" not in plan.appendages:
        chimney(plan, -plan.width * 0.28, site.materials)


@marker("forge")
def _forge(site: MarkerSite) -> None:
    plan = site.plan
    kit.box("forge_hearth", (plan.width * 0.24, site.front - 0.6, 0.55),
            (2.2, 1.3, 1.1), site.material("stone"), bevel=0.0)
    kit.box("forge_ember", (plan.width * 0.24, site.front - 0.95, 1.05),
            (1.6, 0.65, 0.18), site.material("ember"), bevel=0.0)


@marker("anvil")
def _anvil(site: MarkerSite) -> None:
    kit.box("anvil", (-0.4, site.front - 1.5, 0.92),
            (1.3, 0.5, 0.30), site.material("iron"), bevel=0.0)
    kit.box("anvil_base", (-0.4, site.front - 1.5, 0.38),
            (0.7, 0.7, 0.78), site.material("wood"), bevel=0.0)


@marker("coal")
def _coal(site: MarkerSite) -> None:
    plan, bark = site.plan, site.material("bark")
    for index, (x, y, size) in enumerate(((0.0, 0.0, 0.86), (0.52, 0.22, 0.58),
                                          (-0.44, 0.16, 0.5))):
        kit.box(f"forge_coal_{index}",
                (plan.width * 0.24 + x - 1.9, site.front - 1.5 - y, size * 0.3),
                (size, size * 0.8, size * 0.6), bark, bevel=0.0, category="produce")


@marker("horseshoe_sign")
def _horseshoe_sign(site: MarkerSite) -> None:
    """Un fer sur potence : l'enseigne que tout le monde lit."""
    plan, iron = site.plan, site.material("iron")
    head = site.ground.bottom + plan.storey_m * 0.9
    kit.box("horseshoe_bracket", (-plan.width * 0.34, site.front - 0.55, head),
            (0.08, 1.1, 0.08), iron, bevel=0.0, category="appendage_detail")
    for slot, (offset, drop) in enumerate(((-0.22, 0.18), (0.0, 0.34), (0.22, 0.18))):
        kit.box(f"horseshoe_arc_{slot}",
                (-plan.width * 0.34 + offset, site.front - 1.02, head - 0.16 - drop),
                (0.16, 0.07, 0.30), iron, bevel=0.0, category="appendage_detail")


@marker("tool_rack")
def _tool_rack(site: MarkerSite) -> None:
    plan, wood, iron = site.plan, site.material("wood"), site.material("iron")
    kit.box("tool_rack", (-plan.width * 0.30, site.front - 0.2, plan.wall_top - 0.6),
            (2.0, 0.16, 0.16), wood, bevel=0.0, category="tool")
    for index in range(3):
        kit.beam_between(f"smith_tool_{index}",
                         (-plan.width * 0.36 + index * 0.24, site.front - 0.32, 2.2),
                         (-plan.width * 0.36 + index * 0.30, site.front - 0.32,
                          plan.wall_top - 0.65), 0.07, iron, 0.0, category="tool")


# --- grange ---------------------------------------------------------------

@marker("cross_braced_doors")
def _cross_braced_doors(site: MarkerSite) -> None:
    """La grande porte charretiere et ses echarpes en croix.

    C'est la piece qui dit « grange » a cent metres. Elle etait declaree au
    catalogue et le plan tirait bien une porte large ; personne ne la croisait.
    """
    plan, wood, iron = site.plan, site.material("wood"), site.material("iron")
    door = door_of(plan)
    depth = -plan.reveal_depth * 0.9
    for edge in (-1, 1):
        # Deux echarpes par vantail, montant du gond vers le milieu du linteau.
        low = door.position(depth, door.sill_z + 0.12)
        high = door.position(depth, door.sill_z + door.height - 0.12)
        outer = door.along + edge * door.width * 0.46
        inner = door.along + edge * door.width * 0.04
        low = ((outer, low[1], low[2]) if door.axis == "y" else (low[0], outer, low[2]))
        high = ((inner, high[1], high[2]) if door.axis == "y"
                else (high[0], inner, high[2]))
        kit.beam_between(f"barn_brace_{edge}", low, high, 0.10, wood, 0.0,
                         category="opening_detail", width=0.16)
    across, thick, _ = door.size(door.width * 0.98, plan.reveal_depth * 0.35)
    kit.box("barn_door_rail",
            door.position(depth * 1.1, door.sill_z + door.height * 0.52),
            (across, thick, 0.14), wood, bevel=0.0, category="opening_detail")
    for edge in (-1, 1):
        across, thick, _ = door.size(0.18, plan.reveal_depth * 0.5)
        centre = door.position(depth * 1.2, door.sill_z + door.height * 0.82)
        along = door.along + edge * door.width * 0.44
        centre = ((along, centre[1], centre[2]) if door.axis == "y"
                  else (centre[0], along, centre[2]))
        kit.box(f"barn_hinge_{edge}", centre, (across, thick, 0.10), iron,
                bevel=0.0, category="hardware")


@marker("hay")
def _hay(site: MarkerSite) -> None:
    for index, x in enumerate((-2.2, -0.7, 0.8, 2.3)):
        kit.cylinder(f"hay_{index}", (x, site.front - 0.95, 0.58), 0.58, 1.05,
                     site.material("hay"), rotation=(0.0, math.pi / 2, 0.0),
                     vertices=10, bevel=0.0)


@marker("loft")
def _loft(site: MarkerSite) -> None:
    """La trappe de fenil au pignon, sa poutre de levage et son auvent."""
    plan, wood = site.plan, site.material("wood")
    frame = plan.roof_frame
    height = frame.eave_z + (frame.ridge_z - frame.eave_z) * 0.38
    kit.box("loft_hatch", (0.0, site.front - 0.07, height),
            (1.25, 0.14, 1.15), wood, bevel=0.0, category="opening_detail")
    for edge in (-1, 1):
        kit.beam_between(f"loft_brace_{edge}",
                         (edge * 0.58, site.front - 0.10, height - 0.55),
                         (edge * 0.16, site.front - 0.10, height + 0.55),
                         0.08, wood, 0.0, category="opening_detail", width=0.12)
    kit.beam_between("loft_gantry", (0.0, site.front - 0.10, height + 0.85),
                     (0.0, site.front - 1.15, height + 0.85), 0.15, wood, 0.0,
                     category="appendage")
    kit.box("loft_gantry_hood", (0.0, site.front - 0.62, height + 1.06),
            (0.9, 1.2, 0.12), site.material("roof"), rotation=(0.22, 0.0, 0.0),
            bevel=0.0, category="appendage")


@marker("animal_trough")
def _animal_trough(site: MarkerSite) -> None:
    plan = site.plan
    kit.box("animal_trough", (plan.width * 0.32, site.front - 1.5, 0.28),
            (2.4, 0.75, 0.55), site.material("pale_wood"), bevel=0.0)


@marker("pitchfork")
def _pitchfork(site: MarkerSite) -> None:
    plan, wood, iron = site.plan, site.material("wood"), site.material("iron")
    base = (-plan.width * 0.44, site.front - 0.55)
    kit.beam_between("pitchfork_shaft", (base[0], base[1], 0.0),
                     (base[0] + 0.28, base[1] - 0.16, 1.85), 0.07, wood, 0.0,
                     category="tool")
    for slot in (-1, 0, 1):
        kit.box(f"pitchfork_tine_{slot}",
                (base[0] + 0.28 + slot * 0.11, base[1] - 0.16, 2.06),
                (0.05, 0.05, 0.36), iron, bevel=0.0, category="tool")


@marker("pen")
def _pen(site: MarkerSite) -> None:
    """L'enclos s'appuie sur le mur pignon au lieu de flotter a cote.

    Trois poteaux et une lisse etaient poses a `width * 0.52`, dans le vide :
    en projection ils lisaient comme un H suspendu.
    """
    plan, wood = site.plan, site.material("wood")
    start = site.side
    for index in range(4):
        x = start + 0.35 + index * 1.05
        kit.box(f"pen_post_{index}", (x, site.front + 1.1, 0.65),
                (0.14, 0.14, 1.3), wood, bevel=0.0, category="appendage_detail")
    for level, height in enumerate((0.55, 1.05)):
        kit.beam_between(f"pen_rail_{level}",
                         (start, site.front + 1.1, height),
                         (start + 3.5, site.front + 1.1, height),
                         0.09, wood, 0.0, category="appendage_detail", width=0.14)
    kit.beam_between("pen_return", (start + 3.5, site.front + 1.1, 1.05),
                     (start + 3.5, site.front + 3.0, 1.05), 0.09, wood, 0.0,
                     category="appendage_detail", width=0.14)


# --- scierie --------------------------------------------------------------
#
# La scierie etait le dernier batiment sur la grammaire refusee, a 39 980-41 952
# triangles pour un budget de 4 000. Son mecanisme etait dessine en absolu par
# `generate_sawmill.add_saw_mechanism` -- un tore a 32 x 8 segments a lui seul
# coutait plus de mille triangles, et le style plafonne un cylindre a douze
# sommets. Ici il se pose comme les trente-huit autres marqueurs : sur le rez,
# sur la facade et sur le haut de mur, aux vertices que le style autorise.

def sawmill_yard(site: MarkerSite) -> tuple[float, float]:
    """Le chantier de la scierie : son axe en x, son plan en y.

    Deux mesures ont conduit ici, dans cet ordre.

    Place au milieu du batiment, le mecanisme se retrouvait **sous la
    couverture** et n'etait jamais vu -- trouve au rendu en argile, invisible
    sur les rendus lites. Un chassis de scie masque coute ses triangles et ne
    dit rien : c'est le defaut du module Vendor en lame plate, dans l'autre
    sens. Le sortir n'a coute **aucun triangle** et a fait monter l'articulation
    de 5,909 a 6,612 sur `a`, de 6,593 a 6,878 sur `b`.

    Pose ensuite sur le flanc oppose a l'appentis, il changeait de cote d'une
    variante a l'autre : sur `b` il partait derriere le batiment. Le chantier
    se tient donc **devant la facade**, au centre -- le seul plan qu'aucune
    variante n'occupe. Les corps accoles s'adossent au flanc droit ; un
    decalage de ces corps vers la rue ne recouvre pas le chantier.
    """
    return 0.0, site.front - 1.85


@marker("saw_frame")
def _saw_frame(site: MarkerSite) -> None:
    """Le chassis vertical et sa lame : ce qui fait scierie et non remise."""
    plan = site.plan
    wood, blade = site.material("wood"), site.material("blade")
    x, y = sawmill_yard(site)
    top = min(plan.wall_top - 0.35, site.ground.bottom + 3.6)
    bottom = site.ground.bottom + 0.5
    for offset in (-0.62, 0.62):
        kit.box(f"saw_frame_post_{'a' if offset < 0 else 'b'}",
                (x + offset, y, (top + bottom) * 0.5),
                (0.22, 0.24, top - bottom), wood, bevel=0.0,
                category="appendage")
    for name, z in (("saw_frame_top", top), ("saw_frame_sill", bottom)):
        kit.box(name, (x, y, z), (1.46, 0.24, 0.22), wood, bevel=0.0,
                category="appendage_detail")
    # Une lame est une lame : une plaque, pas un volume. Les dents se lisent au
    # contour de la silhouette, elles ne se modelisent pas une a une -- treize
    # boites coutaient 156 triangles pour trois pixels a 96 px.
    kit.box("saw_blade", (x, y, (top + bottom) * 0.5),
            (0.06, 0.16, top - bottom - 0.30), blade, bevel=0.0,
            category="appendage_detail")


@marker("carriage")
def _carriage(site: MarkerSite) -> None:
    """Le chariot qui presente la grume a la lame, sur ses deux rails."""
    plan = site.plan
    iron, pale = site.material("iron"), site.material("pale_wood")
    x, y = sawmill_yard(site)
    run = min(plan.width * 0.95, 5.2)
    z = site.ground.bottom + 0.55
    for offset in (-0.5, 0.5):
        kit.box(f"carriage_rail_{'a' if offset < 0 else 'b'}",
                (x - run * 0.28, y + offset, z), (run, 0.16, 0.12), iron,
                bevel=0.0, category="appendage_detail")
    kit.cylinder("carriage_log", (x - run * 0.34, y, z + 0.44), 0.32,
                 run * 0.72, pale, rotation=(0.0, math.pi / 2, 0.0),
                 vertices=8, bevel=0.0, category="appendage_detail")


@marker("drive_wheel")
def _drive_wheel(site: MarkerSite) -> None:
    """La roue motrice en bout de chantier, et la bielle qui monte au chassis.

    Elle etait un tore a 32 x 8 segments et douze rayons pleins, dans un
    generateur qui ignorait le plafond de douze sommets du style. Une jante en
    huit segments dit la meme chose : c'est le cercle qui se lit de loin, pas
    le nombre de facettes.
    """
    plan = site.plan
    bronze, iron = site.material("bronze"), site.material("iron")
    axis, y = sawmill_yard(site)
    radius = 1.05
    x = axis + 1.5
    z = site.ground.bottom + radius + 0.42
    for index in range(8):
        angle = index * math.tau / 8.0
        nxt = (index + 1) * math.tau / 8.0
        kit.beam_between(
            f"drive_rim_{index}",
            (x + math.cos(angle) * radius, y, z + math.sin(angle) * radius),
            (x + math.cos(nxt) * radius, y, z + math.sin(nxt) * radius),
            0.11, bronze, 0.0, category="appendage_detail", width=0.20)
    for index in range(4):
        angle = index * math.tau / 4.0
        kit.beam_between(
            f"drive_spoke_{index}", (x, y, z),
            (x + math.cos(angle) * radius, y, z + math.sin(angle) * radius),
            0.08, bronze, 0.0, category="appendage_detail")
    kit.beam_between("drive_crank", (x, y, z),
                     (axis, y, site.ground.bottom + 3.2), 0.10, iron, 0.0,
                     category="appendage_detail")


@marker("log_stack")
def _log_stack(site: MarkerSite) -> None:
    """La pile de grumes : la matiere premiere, empilee sur le flanc oppose.

    Elle prend le flanc que le chantier laisse libre, pour que les deux se
    lisent separement au lieu de se confondre en une seule masse.
    """
    plan, bark = site.plan, site.material("bark")
    x0 = site.ground.x0 - 0.78
    length = min(plan.depth * 0.72, 3.8)
    for layer, count in enumerate((3, 2)):
        for index in range(count):
            kit.cylinder(
                f"log_stack_{layer}_{index}",
                (x0 - index * 0.60 - layer * 0.30,
                 site.front + plan.depth * 0.42,
                 site.ground.bottom + 0.30 + layer * 0.54),
                0.29, length, bark, rotation=(math.pi / 2, 0.0, 0.0),
                vertices=8, bevel=0.0, category="appendage_detail")


@marker("sawdust_pile")
def _sawdust_pile(site: MarkerSite) -> None:
    """Le tas de sciure sous la lame. Une icosphere subdivisee trois fois
    coutait 1 280 triangles ; un cone a six pans en dit autant au sol."""
    pale = site.material("pale_wood")
    kit.cylinder("sawdust_mound",
                 (site.side * 0.6, site.front - 1.25, site.ground.bottom + 0.19),
                 0.82, 0.38, pale, vertices=6, bevel=0.0, category="micro_prop")


@marker("crossed_axes_sign")
def _crossed_axes_sign(site: MarkerSite) -> None:
    """L'enseigne aux haches croisees, au-dessus de la porte."""
    plan = site.plan
    wood, blade = site.material("wood"), site.material("blade")
    door = door_of(plan)
    along, z = door.along, door.sill_z + door.height + 0.55
    kit.box("sawmill_sign_board", (along, site.front - 0.16, z),
            (1.15, 0.09, 0.62), wood, bevel=0.0, category="micro_prop")
    for lean in (-1, 1):
        kit.beam_between(
            f"sawmill_sign_axe_{'a' if lean < 0 else 'b'}",
            (along - lean * 0.34, site.front - 0.23, z - 0.22),
            (along + lean * 0.34, site.front - 0.23, z + 0.22),
            0.05, blade, 0.0, category="micro_prop", width=0.09)


# --- chapelle -------------------------------------------------------------

@marker("buttresses")
def _buttresses(site: MarkerSite) -> None:
    """Contreforts a glacis sur les gouttereaux : la masse d'une chapelle."""
    plan, stone = site.plan, site.material("stone")
    height = plan.wall_top - site.ground.bottom
    count = max(2, int(round(plan.depth / 3.2)))
    for edge in (-1, 1):
        x = (site.ground.x1 if edge > 0 else site.ground.x0)
        for index in range(count):
            y = site.ground.y0 + (index + 0.5) * (site.ground.depth / count)
            kit.box(f"buttress_{edge}_{index}",
                    (x + edge * 0.34, y, site.ground.bottom + height * 0.42),
                    (0.68, 0.62, height * 0.84), stone,
                    bevel=plan.wall_bevel, category="appendage")
            # Le glacis : la pente qui renvoie l'eau au pied du contrefort.
            kit.box(f"buttress_weathering_{edge}_{index}",
                    (x + edge * 0.30, y, site.ground.bottom + height * 0.86),
                    (0.60, 0.66, 0.30), stone, rotation=(0.0, edge * 0.55, 0.0),
                    bevel=0.0, category="appendage_detail")


@marker("lancet_windows")
def _lancet_windows(site: MarkerSite) -> None:
    """Les lancettes, seules baies d'une chapelle.

    `plan_building` retire les fenetres ordinaires des que ce marqueur est
    declare. Il n'etait pas pose : la chapelle n'avait **aucune** ouverture, et
    ses quatre murs etaient aveugles.
    """
    plan = site.plan
    glass, wood = site.material("ember"), site.material("wood")
    height = plan.storey_m * 0.74
    base = site.ground.bottom + plan.storey_m * 0.44
    count = max(2, int(round(plan.depth / 3.2)))
    for edge in (-1, 1):
        x = (site.ground.x1 if edge > 0 else site.ground.x0)
        for index in range(count):
            y = site.ground.y0 + (index + 1.0) * (site.ground.depth / (count + 1))
            kit.box(f"lancet_{edge}_{index}", (x - edge * 0.06, y, base + height * 0.45),
                    (0.14, 0.52, height * 0.9), glass,
                    bevel=0.0, category="opening_plane")
            kit.box(f"lancet_head_{edge}_{index}", (x - edge * 0.06, y, base + height * 0.94),
                    (0.14, 0.30, height * 0.24), glass,
                    bevel=0.0, category="opening_plane")
            kit.box(f"lancet_jamb_{edge}_{index}", (x - edge * 0.10, y, base + height * 0.45),
                    (0.10, 0.72, height * 0.98), wood,
                    bevel=0.0, category="opening_detail")
    # Une lancette d'axe au-dessus de la porte, sur la face de rue.
    kit.box("lancet_front", (0.0, site.front + 0.06,
                             site.ground.bottom + plan.storey_m * 1.05),
            (0.62, 0.14, height * 0.8), glass, bevel=0.0, category="opening_plane")


@marker("apse")
def _apse(site: MarkerSite) -> None:
    """Le chevet : un volume a pans coupes au fond du vaisseau, sous sa croupe."""
    plan, stone = site.plan, site.material("stone")
    height = plan.wall_top - site.ground.bottom
    radius = site.ground.width * 0.40
    back = site.ground.y1
    for index, angle in enumerate((-0.9, -0.3, 0.3, 0.9)):
        kit.box(f"apse_facet_{index}",
                (math.sin(angle) * radius * 0.86,
                 back + math.cos(angle) * radius * 0.62,
                 site.ground.bottom + height * 0.46),
                (radius * 0.62, 0.36, height * 0.92), stone,
                rotation=(0.0, 0.0, -angle), bevel=0.0, category="appendage")
    kit.box("apse_roof", (0.0, back + radius * 0.38,
                          site.ground.bottom + height * 0.96),
            (radius * 1.7, radius * 1.1, 0.26), site.material("roof"),
            bevel=0.0, category="roof_plane")


@marker("bell_tower")
def _bell_tower(site: MarkerSite) -> None:
    plan, stone, bronze = site.plan, site.material("stone"), site.material("bronze")
    tower = plan.corner_post * 7.5
    base = plan.ridge_z
    kit.box("bell_tower", (0.0, plan.depth * 0.18, base + tower * 0.5),
            (tower * 0.72, tower * 0.72, tower), stone,
            bevel=plan.wall_bevel, category="appendage")
    kit.box("bell_tower_louvre", (0.0, plan.depth * 0.18 - tower * 0.37,
                                  base + tower * 0.60),
            (tower * 0.42, 0.10, tower * 0.44), site.material("wood"),
            bevel=0.0, category="appendage_detail")
    kit.box("bell", (0.0, plan.depth * 0.18 - tower * 0.30, base + tower * 0.62),
            (tower * 0.26, tower * 0.14, tower * 0.26), bronze, bevel=0.0)


@marker("cross")
def _cross(site: MarkerSite) -> None:
    plan, bronze = site.plan, site.material("bronze")
    tower = plan.corner_post * 7.5
    base = plan.ridge_z
    kit.beam_between("cross_vertical", (0.0, plan.depth * 0.18, base + tower),
                     (0.0, plan.depth * 0.18, base + tower * 1.45), 0.15, bronze, 0.0)
    kit.beam_between("cross_horizontal",
                     (-tower * 0.14, plan.depth * 0.18, base + tower * 1.28),
                     (tower * 0.14, plan.depth * 0.18, base + tower * 1.28),
                     0.15, bronze, 0.0)


@marker("grave_markers")
def _grave_markers(site: MarkerSite) -> None:
    plan, limestone = site.plan, site.material("limestone")
    kit.box("chapel_steps", (0.0, site.front - 0.7,
                             max(0.2, site.ground.bottom) * 0.55),
            (2.9, 1.2, max(0.4, site.ground.bottom * 1.1)), limestone,
            bevel=0.0, category="foundation")
    for edge in (-1, 1):
        kit.box(f"grave_marker_{edge}",
                (edge * plan.width * 0.56, site.front - 1.5, 0.58),
                (0.42, 0.22, 1.15), limestone, bevel=0.0)
        kit.box(f"grave_head_{edge}",
                (edge * plan.width * 0.56, site.front - 1.5, 1.22),
                (0.42, 0.22, 0.26), limestone, bevel=0.0,
                category="appendage_detail")


def function_details(plan: style_module.Plan, variant: dict, materials: dict,
                     rng: random.Random) -> list[str]:
    """Poser les marqueurs d'identite que le catalogue declare.

    Le module Vendor a quitte la facade, decision du proprietaire du 2026-08-29.
    `EA03_Village_HouseModule_Porch_01d` etait importe, mis a l'echelle de 62 %
    de la largeur du mur et plaque au nu du rez. Mesure au rendu isole aux deux
    budgets : ce n'est pas la decimation qui le casse -- a 763 triangles comme a
    160, l'import ne retient que les maillages nommes `LOD0` de la source et il
    en sort une lame plate.

    La porte D-1 est ici : **un marqueur declare au catalogue et absent du
    registre arrete la generation.** C'est ce controle qui manquait, et c'est
    pour cela que quatorze marqueurs sur trente-huit n'existaient pas.
    """
    site = MarkerSite(plan=plan, materials=materials, variant=variant, rng=rng)
    kit.set_category("micro_prop")
    built: list[str] = []
    for name in plan.identity_markers:
        builder = IDENTITY_BUILDERS.get(name)
        if builder is None:
            raise SystemExit(
                f"CITYLAB_BUILDING_ERROR marqueur_sans_constructeur id={plan.asset_id} "
                f"marqueur={name} : le catalogue le declare, le registre ne le "
                f"connait pas")
        kit.set_category("micro_prop")
        builder(site)
        built.append(name)

    kit.set_category("lantern_glass")
    for edge in (-1, 1):
        kit.add_lantern(f"lantern_{'left' if edge < 0 else 'right'}",
                        (edge * plan.width * 0.36, site.front - 0.28,
                         plan.wall_top - 0.7),
                        site.material("iron"), site.material("ember"))
    return built


def edge_trim(plan: style_module.Plan, materials: dict) -> None:
    """Planches de rive, epis et abouts de panne.

    Le trim de bord ne coute presque rien et dessine la silhouette : c'est ce
    qui distingue un pignon nu d'un pignon habite a 96 px. Chaque membre est pose
    entre deux points reels du rampant -- une boite tournee autour de son centre
    partait en antenne des que la pente changeait.
    """
    wood, accent = materials["wood"], materials["roof_alt"]
    for index, frame in enumerate(f for f in (plan.roof_frame, plan.roof_frame_high)
                                  if f is not None):
        edge_trim_on(plan, materials, frame, wood, accent, "" if index == 0 else "_high")


def edge_trim_on(plan: style_module.Plan, materials: dict,
                 frame: style_module.RoofFrame, wood, accent, suffix: str) -> None:
    """Trim de bord d'une volee. Chaque volee a le sien : la volee haute du
    decrochement restait a nu, sans planche de rive ni epi."""
    spec = plan.edge_trim_spec
    board = float(spec.get("board_m", 0.0))
    if board <= 0.0:
        return
    span = frame.span
    half_span = frame.half_span + frame.overhang
    half_run = frame.half_run + frame.overhang
    # La planche de rive suit la couverture, donc le plan des chevrons releve.
    eave_z = frame.eave_z + frame.covering_lift
    ridge_z = frame.ridge_z + frame.covering_lift
    point = frame.local

    # Une croupe n'a pas de rampant : une planche de rive posee dessus part
    # dans le vide, faute d'un pignon ou s'appuyer. Seuls les abouts de panne
    # restent valides.
    for side in (-1, 1) if plan.roof_form == "gable" else ():
        along = side * half_run
        apex = point(0.0, along, ridge_z)
        for rake in (-1, 1):
            kit.beam_between(
                f"barge{suffix}_{'lo' if side < 0 else 'hi'}_{'l' if rake < 0 else 'r'}",
                point(rake * half_span, along, eave_z), apex, board * 0.34, wood,
                bevel=0.0, category="edge_trim", width=board * 1.6)
        finial = float(spec.get("finial_m", 0.0))
        if finial > 0.0:
            for lean in (-1, 1):
                kit.beam_between(
                    f"finial{suffix}_{'lo' if side < 0 else 'hi'}_{'a' if lean < 0 else 'b'}",
                    apex,
                    point(lean * finial * 0.45, along, ridge_z + finial),
                    board * 0.55, accent, bevel=0.0, category="edge_trim",
                    width=board * 0.9)

    ends = int(spec.get("purlin_ends", 0))
    for side in (-1, 1):
        for index in range(ends):
            ratio = (index + 0.5) / max(1, ends)
            across = (ratio * 2.0 - 1.0) * half_span
            # Hauteur du rampant a cette abscisse : les abouts suivent la pente.
            z = eave_z + (ridge_z - eave_z) * (1.0 - abs(across) / half_span)
            inner = point(across, side * (half_run - plan.overhang), z)
            outer = point(across, side * (half_run + board * 1.6), z)
            kit.beam_between(f"purlin{suffix}_{'lo' if side < 0 else 'hi'}_{index}",
                             inner, outer, board * 0.7, wood,
                             bevel=0.0, category="edge_trim", width=board * 1.1)


def appendages(plan: style_module.Plan, materials: dict) -> None:
    """Les volumes rapportes du schema, chacun avec sa propre toiture."""
    wood, stone = materials["wood"], materials["stone"]
    covering, iron = materials["roof"], materials["iron"]
    ground, top = plan.storeys[0], plan.top_storey

    porch = plan.appendages.get("porch")
    if porch:
        depth, width, post = porch["depth"], porch["width"], porch["post"]
        front = ground.y0 - depth
        head = ground.bottom + plan.storey_m * 0.92
        drop = math.tan(math.radians(porch["pitch_deg"])) * depth
        for side in (-1, 1):
            kit.box(f"porch_post_{side}",
                    (side * width * 0.5, front + post * 0.5,
                     ground.bottom + (head - drop - ground.bottom) * 0.5),
                    (post, post, head - drop - ground.bottom), wood,
                    bevel=plan.wall_bevel, category="appendage")
        points = [(-width * 0.5 - post, ground.y0, head),
                  (width * 0.5 + post, ground.y0, head),
                  (width * 0.5 + post, front, head - drop),
                  (-width * 0.5 - post, front, head - drop)]
        kit.surface_mesh("porch_roof", points, [(0, 1, 2, 3)], covering,
                         plan.roof_thickness, category="appendage")

    shed = plan.appendages.get("lean_to")
    if shed:
        side = shed["side"] if not plan.lean_to else -plan.lean_to["side"]
        inner = ground.x1 if side > 0 else ground.x0
        outer = inner + side * shed["depth"]
        head = ground.bottom + shed["height"]
        drop = math.tan(math.radians(shed["pitch_deg"])) * shed["depth"]
        hollow_block("appendage_shed", ((inner + outer) * 0.5, ground.centre[1]),
                     (abs(outer - inner), ground.depth * 0.72), ground.bottom,
                     head - ground.bottom, plan.wall_thickness, stone)
        half = ground.depth * 0.38
        points = [(inner, -half, head), (inner, half, head),
                  (outer, half, head - drop), (outer, -half, head - drop)]
        kit.surface_mesh("appendage_shed_roof", points, [(0, 1, 2, 3)], covering,
                         plan.roof_thickness, category="appendage")

    stair = plan.appendages.get("stair")
    door = next((item for item in plan.openings if item.kind == "door"), None)
    if stair and door is not None:
        # Un perron dessert un seuil, jamais un etage. Quand la porte partait au
        # premier niveau, la meme boucle produisait dix-neuf marches sur 5,70 m
        # et l'escalier devenait un remblai de pierre qui coupait la facade en
        # deux. La borne est une porte, pas un reglage : si le seuil monte trop
        # haut, c'est le plan qui est faux et il doit le dire.
        rise = door.sill_z
        maximum = float(stair["max_rise_m"])
        if rise > maximum:
            raise SystemExit(
                f"CITYLAB_BUILDING_ERROR perron_hors_bornes id={plan.asset_id} "
                f"rise={rise:.2f} max={maximum:.2f} : un perron dessert un "
                f"seuil, un escalier d'etage n'est pas dans le vocabulaire")
        if rise > 0.15:
            width = stair["width"]
            steps = max(2, int(round(rise / 0.19)))
            tread = stair["tread"]
            run = steps * tread
            for step in range(steps):
                # Chaque marche repose sur la precedente. Elles partaient toutes
                # du sol : la pile etait un coin plein, pas des marches.
                bottom = rise * step / steps
                height = rise / steps
                depth_out = run - (step + 0.5) * tread
                centre = door.position(depth_out, bottom + height * 0.5)
                across, thick, _ = door.size(width, tread)
                centre = ((door.along, centre[1], centre[2]) if door.axis == "y"
                          else (centre[0], door.along, centre[2]))
                kit.box(f"stair_step_{step}", centre, (across, thick, height),
                        stone, bevel=0.0, category="appendage_detail")
            for side in (-1, 1):
                # Le limon suit la pente des marches. Il etait horizontal, a
                # mi-hauteur, et debordait le perron des deux cotes.
                low = door.position(run, stair["rail"] * 0.5)
                high = door.position(0.0, rise + stair["rail"] * 0.5)
                along = door.along + side * (width + stair["rail"]) * 0.5
                low = ((along, low[1], low[2]) if door.axis == "y"
                       else (low[0], along, low[2]))
                high = ((along, high[1], high[2]) if door.axis == "y"
                        else (high[0], along, high[2]))
                kit.beam_between(f"stair_string_{side}", low, high,
                                 stair["rail"], stone, bevel=0.0,
                                 category="appendage_detail",
                                 width=stair["rail"] * 1.4)

    gallery = plan.appendages.get("gallery")
    if gallery:
        level = plan.storeys[min(gallery["level"], len(plan.storeys) - 1)]
        depth, rail, post = gallery["depth"], gallery["rail"], gallery["post"]
        front = level.y0 - depth
        kit.box("gallery_deck",
                (level.centre[0], front + depth * 0.5, level.bottom),
                (level.width, depth, rail * 1.4), wood,
                bevel=0.0, category="appendage")
        kit.box("gallery_rail",
                (level.centre[0], front, level.bottom + plan.storey_m * 0.32),
                (level.width, rail, rail), wood, bevel=0.0, category="appendage_detail")
        # Les poteaux descendent jusqu'au niveau du dessous : la galerie flottait
        # devant la facade, portee par rien.
        below = plan.storeys[max(0, gallery["level"] - 1)]
        drop = max(0.4, level.bottom - below.bottom)
        for slot in (-1, 0, 1):
            kit.box(f"gallery_post_{slot}",
                    (level.centre[0] + slot * level.width * 0.4, front,
                     level.bottom - drop * 0.5),
                    (post, post, drop), wood,
                    bevel=0.0, category="appendage_detail")
        for slot in (-1, 0, 1):
            kit.box(f"gallery_rail_post_{slot}",
                    (level.centre[0] + slot * level.width * 0.4, front,
                     level.bottom + plan.storey_m * 0.16),
                    (post, post, plan.storey_m * 0.32), wood,
                    bevel=0.0, category="appendage_detail")

    stack = plan.appendages.get("chimney_stack")
    if stack:
        # La souche monte dans le pignon et sort a l'aplomb du faitage. Plaquee
        # au nu du mur, elle rasait la rive sans jamais traverser un versant.
        frame = plan.roof_frame
        gable = -1 if frame.span_axis == "x" else -1
        along = gable * (frame.half_run - stack["depth"] * 0.55)
        base = frame.local(0.0, along, 0.0)
        height = stack["top"] - ground.bottom
        size = ((stack["width"], stack["depth"], height) if frame.span_axis == "x"
                else (stack["depth"], stack["width"], height))
        kit.box("chimney_stack", (base[0], base[1], ground.bottom + height * 0.5),
                size, stone, bevel=0.0, category="appendage")
        # Solin : le collier de pierre qui ferme la rencontre avec le versant.
        # Sans lui la souche traversait la couverture en interpenetration nue et
        # laissait un joint noir sur les rendus.
        flash_z = frame.ridge_z - stack["depth"] * 0.55 * math.tan(
            math.radians(frame.pitch_deg))
        kit.box("chimney_flashing", (base[0], base[1], flash_z),
                (size[0] + plan.roof_thickness * 2.4,
                 size[1] + plan.roof_thickness * 2.4,
                 plan.roof_thickness * 3.0), stone,
                bevel=0.0, category="appendage")
        # Corbeau : la souche s'evase avant sa couronne. Elle s'arretait en
        # boite nette surmontee d'une plaque de fer, ce qui la faisait lire
        # comme un cube pose sur le toit.
        kit.box("chimney_corbel", (base[0], base[1], stack["top"] - 0.22),
                (size[0] * 1.22, size[1] * 1.22, 0.30), stone,
                bevel=0.0, category="appendage")
        cap = ((size[0] * stack["taper"], size[1] * stack["taper"], 0.36))
        kit.box("chimney_pot", (base[0], base[1], stack["top"] + 0.18),
                cap, iron, bevel=0.0, category="appendage")

    lantern = plan.appendages.get("roof_lantern")
    if lantern:
        # Assis dans le faitage : il flottait au-dessus, sans rien dessous.
        frame = plan.roof_frame
        width, height = lantern["width"], lantern["height"]
        seat = frame.ridge_z - height * 0.35
        centre = frame.centre
        kit.box("roof_lantern", (centre[0], centre[1], seat + height * 0.5),
                (width, width, height), wood, bevel=0.0, category="appendage")
        kit.roof_surface("roof_lantern_cap", "gable", width * 0.6, width * 0.6,
                         frame.span_axis, seat + height, height * 0.5,
                         frame.overhang * 0.2, plan.roof_thickness, covering,
                         centre=centre)

    sign = plan.appendages.get("hanging_sign")
    if sign:
        side = sign["side"]
        anchor = ground.y0
        head = ground.bottom + plan.storey_m * 0.86
        kit.box("sign_bracket",
                (side * ground.width * 0.32, anchor - sign["bracket"] * 0.5, head),
                (0.09, sign["bracket"], 0.09), iron, bevel=0.0, category="appendage_detail")
        kit.box("sign_board",
                (side * ground.width * 0.32, anchor - sign["bracket"],
                 head - sign["board"] * 0.6),
                (sign["board"], 0.06, sign["board"] * 0.72), wood,
                bevel=0.0, category="appendage_detail")


def silhouette_touches_border(path: Path) -> int:
    """Compter les pixels opaques poses sur le bord du rendu.

    Une silhouette coupee par le cadre ment sur son perimetre : elle perd les
    contours que le cadre tranche et gagne de l'aire. C'est ainsi que la maison
    de ville a ete mesuree a 4,82 d'articulation alors qu'elle debordait. Le
    cadrage est donc une porte, pas un reglage.
    """
    image = bpy.data.images.load(str(path))
    try:
        width, height = image.size
        pixels = list(image.pixels)
    finally:
        bpy.data.images.remove(image)
    touching = 0
    for y in range(height):
        for x in range(width):
            if x not in (0, width - 1) and y not in (0, height - 1):
                continue
            if pixels[(y * width + x) * 4 + 3] > 0.5:
                touching += 1
    return touching


def build_annex(plan: style_module.Plan, annex: style_module.Annex,
                materials: dict) -> None:
    """Poser un corps accole : fondation, niveaux, charpente, couverture, trim.

    L'annexe est un batiment complet, donc elle passe par les memes fonctions que
    le corps principal. Une vue du plan lui est fabriquee -- memes reglages de
    style, ses niveaux et son enveloppe a elle -- ce qui evite de dupliquer la
    pose. Les volumes rapportes et les marqueurs de famille restent au corps
    principal : une annexe n'a pas sa propre cheminee ni son propre porche.
    """
    view = dataclasses.replace(
        plan,
        storeys=annex.storeys,
        openings=annex.openings,
        roof_frame=annex.frames[0],
        roof_frame_high=annex.frames[1] if len(annex.frames) > 1 else None,
        annexes=(),
        width=annex.width,
        depth=annex.depth,
        span_axis=annex.span_axis,
        rise=annex.rise,
        half_span=annex.half_span,
        wing={},
        lean_to={},
        cross_gable={},
        dormers=(),
        appendages={},
        body_role="annex",
    )
    kit.set_phase("framing", "shell_annex")
    shell(view, materials)
    kit.set_phase("carpentry", "roof_frame")
    roof_carpentry(view, materials, view.roof_frame)
    kit.set_phase("roofing", "roof_annex")
    roof_covering(view, materials, view.roof_frame, "roof_annex")
    kit.set_phase("joinery", "opening_plane")
    opening_leaves(view, materials)


def review_framing(style: dict, family: dict, variants: list[dict]) -> tuple[float, float]:
    """Cadrage identique pour toutes les variantes d'une famille.

    Il est derive du plan reel des trois variantes, et pris au maximum : deux
    silhouettes comparees a des echelles differentes ne mesurent rien, et une
    silhouette qui touche le bord de l'image ment sur son perimetre. C'est ce
    qui est arrive a la maison de ville, mesuree a 4,82 d'articulation alors
    qu'elle debordait du cadre.
    """
    margin = 1.35
    extent = 0.0
    height = 0.0
    for variant in variants:
        plan = style_module.plan_building(style, family, variants, variant["id"])
        for storey in plan.storeys:
            extent = max(extent, storey.width, storey.depth,
                         2.0 * max(abs(storey.x0), abs(storey.x1)),
                         2.0 * max(abs(storey.y0), abs(storey.y1)))
        extent = max(extent, plan.width, plan.depth)
        extent += 0.0
        top = plan.ridge_z
        stack = plan.appendages.get("chimney_stack")
        if stack:
            top = max(top, stack["top"] + 0.4)
        lantern = plan.appendages.get("roof_lantern")
        if lantern:
            top = max(top, plan.ridge_z + lantern["height"] * 1.6)
        for annex in plan.annexes:
            # Un corps accole deborde l'emprise : sans lui, la silhouette touche
            # le bord du rendu et ment sur son perimetre.
            reach = max(abs(item.x0) for item in annex.storeys)
            reach = max(reach, max(abs(item.x1) for item in annex.storeys))
            deep = max(abs(item.y0) for item in annex.storeys)
            deep = max(deep, max(abs(item.y1) for item in annex.storeys))
            extent = max(extent, 2.0 * reach, 2.0 * deep)
            top = max(top, annex.frames[0].ridge_z)
        if plan.wing:
            # L'aile avance vers la camera et deborde l'emprise : sans elle dans
            # le calcul, la silhouette touchait le bord du rendu et mentait sur
            # son perimetre.
            wing = plan.wing
            extent = max(extent,
                         plan.width + 2.0 * wing["width"],
                         plan.depth + 2.0 * (wing["depth"] + wing.get("projection", 0.0)))
        shed = plan.appendages.get("lean_to")
        if shed:
            extent = max(extent, plan.width + 2.0 * shed["depth"])
        porch = plan.appendages.get("porch")
        if porch:
            extent = max(extent, plan.depth + 2.0 * porch["depth"])
        gallery = plan.appendages.get("gallery")
        if gallery:
            extent = max(extent, plan.depth + 2.0 * gallery["depth"])
        stair = plan.appendages.get("stair")
        if stair:
            extent = max(extent, plan.width + 2.4 * stair["rise"])
        height = max(height, top)
    extent += 2.0 * float(style["roof"]["overhang_m"][1])
    return max(extent, height) * margin, height * 0.5


def main() -> int:
    args = arguments()
    root = Path(args.project_root).resolve()
    output = (root / args.output_root).resolve()
    catalog_path = (root / args.catalog).resolve()
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    families = {item["id"]: item for item in catalog["families"]}
    family = families[args.family]
    style = style_module.load_style(root, catalog["style"])
    plan = style_module.plan_building(style, family, catalog["variants"], args.variant)
    variant = {item["id"]: item for item in catalog["variants"]}[args.variant]
    rng = random.Random(plan.seed)
    asset_id = plan.asset_id

    bpy.ops.wm.read_factory_settings(use_empty=True)
    kit.set_bevel_policy(style["budget"]["max_bevel_segments"],
                         style["trim"]["world_uv_scale_m"])
    materials = kit.build_materials(root, style, plan.palette, plan.palette_id,
                                    plan.wall_system, plan.roof_system,
                                    plan.upper_band, plan.lower_band)
    alias_materials(materials)

    # Contrat de construction v2 : le decoupage est une donnee du catalogue. Le
    # rang d'une etape est sa place dans le vocabulaire ferme, pas sa place dans
    # la liste : il ne se renumerote pas quand une etape manque.
    kit.set_stages(catalog["construction_stages"],
                   order={name: index for index, name
                          in enumerate(STAGE_VOCABULARY, start=1)},
                   marker="S")

    kit.set_phase("groundworks", "foundation")
    foundation(plan, materials)
    loops_before, loops_after = shell(plan, materials)
    kit.set_phase("carpentry", "roof_frame")
    roof_carpentry(plan, materials, plan.roof_frame)
    if plan.roof_frame_high is not None:
        roof_carpentry(plan, materials, plan.roof_frame_high)
    kit.set_phase("roofing", "roof_plane")
    roof(plan, materials)
    kit.set_category("edge_trim")
    edge_trim(plan, materials)
    for annex in plan.annexes:
        build_annex(plan, annex, materials)

    kit.set_phase("joinery", "opening_plane")
    opening_leaves(plan, materials)
    kit.set_phase("finishes", "appendage")
    appendages(plan, materials)
    kit.set_category("micro_prop")
    markers_built = function_details(plan, variant, materials, rng)

    # Une etape sans geometrie n'est pas declaree. Une maison d'un seul niveau
    # n'a pas de plancher et une maison sans assise de pierre n'a pas de
    # soubassement : le contrat v2 le dit, et le batiment ne ment pas sur ce
    # qu'il produit.
    stages = kit.retain_used_stages(minimum=CONSTRUCTION_MIN_STAGES)

    kit.uv_assets(float(style["trim"]["world_uv_scale_m"]))

    previews = output / "Workbench" / "Previews"
    previews.mkdir(parents=True, exist_ok=True)
    ortho, target_z = review_framing(style, family, catalog["variants"])
    silhouette = previews / f"{asset_id}_silhouette.png"
    kit.render_silhouette(silhouette, RTS_VIEW, (0.0, 0.0, target_z), ortho,
                          int(style["silhouette_gate"]["render_px"]))
    clipped = silhouette_touches_border(silhouette)
    if clipped:
        raise SystemExit(
            f"CITYLAB_BUILDING_ERROR silhouette_hors_cadre id={asset_id} "
            f"pixels={clipped} ortho={ortho:.2f} : le cadrage de revue doit "
            f"contenir la variante la plus grande de la famille")

    kit.setup_review(materials)
    stage_previews: list[Path] = []
    if not args.skip_previews:
        late = set((style["lod"].get("lod0") or {}).get("drop_categories") or [])
        for stage_index, stage in enumerate(stages):
            kit.show_construction_through(stage_index, hidden_categories=late)
            image = previews / f"{asset_id}_stage_{stage_index + 1:02d}_{stage}.png"
            kit.render_view(image, RTS_VIEW, (0.0, 0.0, target_z), ortho, 448)
            stage_previews.append(image)
    kit.show_construction_through(len(stages) - 1,
                                  hidden_categories=set(
                                      (style["lod"].get("lod0") or {})
                                      .get("drop_categories") or []))
    if not args.skip_previews:
        kit.render_view(previews / f"{asset_id}_hero.png", RTS_VIEW,
                        (0.0, 0.0, target_z), ortho, int(style["review"]["hero_px"]))
        kit.render_view(previews / f"{asset_id}_rts.png", RTS_VIEW,
                        (0.0, 0.0, target_z), ortho, 512)
        kit.render_view(previews / f"{asset_id}_contact.png", RTS_VIEW,
                        (0.0, 0.0, target_z), ortho,
                        int(style["review"]["contact_sheet_px"]))

    blend = output / "Workbench" / f"{asset_id}_review.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    glb, fbx, phase_triangles, triangles, mesh_hash, gates = kit.export_assets(
        asset_id, output / "Raw", output / "Workbench" / "Models", style["lod"])
    category_triangles = kit.category_triangles()
    gates["front_wall_edge_loops"] = loops_after
    gates["front_wall_edge_loops_before_cut"] = loops_before
    gates["declared_openings"] = len(plan.openings)
    # Porte D-1 : un marqueur declare au catalogue est pose par la geometrie.
    # Quatorze sur trente-huit ne l'etaient pas, et c'etaient exactement ceux
    # qui distinguent une grange d'une chapelle.
    gates["identity_markers_declared"] = list(plan.identity_markers)
    gates["identity_markers_built"] = markers_built
    # Les boucles se comptent sur le seul niveau mesure. Depuis que les
    # ouvertures se repartissent sur plusieurs niveaux, les comparer au total
    # exigeait de la facade du rez les percements des etages.
    gates["measured_storey"] = getattr(shell, "measured_storey", 0)
    gates["measured_face"] = getattr(shell, "measured_face", "front")
    # Les boucles se comptent sur un seul plan de facade. Depuis que les baies
    # se repartissent sur les quatre faces, les comparer a toutes les ouvertures
    # du niveau exigerait de la seule facade avant les percements des trois
    # autres murs.
    gates["declared_openings_in_measured_face"] = sum(
        1 for opening in plan.openings
        if opening.storey == gates["measured_storey"]
        and opening.face == gates["measured_face"])
    metrics = {
        "schema": 1,
        "id": asset_id,
        "family": family["id"],
        "function": plan.function,
        "wall_system": plan.wall_system,
        "roof_system": plan.roof_system,
        "identity_markers": list(plan.identity_markers),
        "variant": args.variant,
        "seed": plan.seed,
        "blender": bpy.app.version_string,
        "style": catalog["style"],
        "vendor_input": family["input"],
        "grammar": {
            "footprint_form": plan.footprint_form,
            "level_form": plan.level_form,
            "roof_form": plan.roof_form,
            "ridge_axis": plan.ridge_axis,
            "width_m": round(plan.width, 4),
            "depth_m": round(plan.depth, 4),
            "wall_height_m": round(plan.wall_height, 4),
            "pitch_deg": round(plan.pitch_deg, 4),
            "rise_m": round(plan.rise, 4),
            "ridge_z_m": round(plan.ridge_z, 4),
        },
        "budget": {"class": plan.budget_class, "lod": list(plan.budget_lod)},
        "triangles": {"lod0": triangles[0], "lod1": triangles[1], "lod2": triangles[2]},
        "construction": {
            "contract": int(catalog.get("construction_contract", 1)),
            "schema": catalog["construction_schema"],
            "declared_stages": list(catalog["construction_stages"]),
            "stages": [
                {"id": stage, "order": STAGE_VOCABULARY.index(stage) + 1,
                 "node_prefix": f"{asset_id}__S{STAGE_VOCABULARY.index(stage) + 1:02d}"
                                f"_{stage.upper()}",
                 "lod0": phase_triangles[stage][0],
                 "lod1": phase_triangles[stage][1],
                 "lod2": phase_triangles[stage][2]}
                for stage in stages
            ],
        },
        "construction_stage_triangles": {
            stage: {"lod0": counts[0], "lod1": counts[1], "lod2": counts[2]}
            for stage, counts in phase_triangles.items()
        },
        "canonical_mesh_sha256": mesh_hash,
        "gates": gates,
        "category_triangles": category_triangles,
        "outputs": {
            "glb": glb.relative_to(root).as_posix(),
            "fbx": fbx.relative_to(root).as_posix(),
            "hero": (previews / f"{asset_id}_hero.png").relative_to(root).as_posix(),
            "rts": (previews / f"{asset_id}_rts.png").relative_to(root).as_posix(),
            "contact": (previews / f"{asset_id}_contact.png").relative_to(root).as_posix(),
            "silhouette": silhouette.relative_to(root).as_posix(),
            "construction_stages": [image.relative_to(root).as_posix()
                                    for image in stage_previews],
        }
    }
    report = output / "Reports" / f"{asset_id}_metrics.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"CITYLAB_BUILDING_GENERATED id={asset_id} triangles={triangles} hash={mesh_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
