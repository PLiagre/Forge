"""Le kit de modélisation partagé de la Factory : primitives, LOD, export.

Ce fichier s'appelait `generate_sawmill.py`. Il portait deux choses sans lien :
**953 lignes de kit** que tous les générateurs importent, et **348 lignes** qui
dessinaient une scierie à la main, en coordonnées absolues, hors de la grammaire
et hors du plafond de sommets du style.

La scierie est entrée au catalogue du pilote et se génère comme les sept autres
familles. Les 348 lignes n'avaient plus d'appelant : les garder aurait été du
code mort, et le nom aurait continué à mentir sur le contenu — au point qu'il
fallait un test pour rappeler que `generate_sawmill` était le kit.

Le contrat de construction v1 reste implémenté ici (`PHASES`, marqueur `P`) : le
schéma est publié et l'hôte Unity lit les deux marqueurs. Aucun asset publié ne
l'emploie plus.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
import sys
from pathlib import Path

import bpy
from mathutils import Vector


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as style_module


ASSET_TAG = "citylab_asset"
PHASE_TAG = "citylab_construction_phase"
CATEGORY_TAG = "citylab_lod_category"
CURVED_TAG = "citylab_curved"
TRIM_RECT_TAG = "citylab_trim_rect"
# Contrat de construction, version 1 : quatre phases fixes. C'est ce que la
# scierie publiee produit, et elle n'en bouge pas.
PHASES = ("foundation", "frame", "roof", "details")
# Le decoupage effectif de la piece en cours. Il vaut les quatre phases de la v1
# tant que personne n'en installe d'autres. Le nombre quatre etait ecrit ici, et
# se recopiait dans le validateur FBX et dans l'integration Unity : un mur
# entier apparaissait alors en un seul coup.
STAGES = PHASES
# Le rang d'une etape dans son vocabulaire, qui nomme le nœud du FBX. Il ne se
# renumerote pas quand une etape manque : l'hote lit ce nom.
STAGE_ORDER: dict[str, int] = {name: index for index, name in enumerate(PHASES, start=1)}
# `P` pour le contrat v1, `S` pour le v2. Deux marqueurs, une seule expression
# reguliere du cote hote, et les deux contrats cohabitent dans un meme projet.
STAGE_MARKER = "P"


def set_stages(stages, order=None, marker: str = "S") -> None:
    """Installer le decoupage de construction de la piece en cours.

    `order` donne le rang de chaque etape dans son vocabulaire ; a defaut, le
    rang suit la position dans `stages`.
    """
    global STAGES, STAGE_ORDER, STAGE_MARKER
    STAGES = tuple(stages)
    STAGE_ORDER = dict(order) if order else {
        name: index for index, name in enumerate(STAGES, start=1)}
    missing = [name for name in STAGES if name not in STAGE_ORDER]
    if missing:
        raise ValueError("Etapes sans rang : " + ", ".join(missing))
    STAGE_MARKER = marker
CURRENT_PHASE = "details"
CURRENT_CATEGORY = "prop"
BEVEL_MAX_SEGMENTS = 2
BEVEL_DETAIL_SCALE = 2.0

# Nœuds de texture procedurale : ils ne franchissent ni le FBX ni le glTF. Un
# seul survivant dans le chemin d'export rend l'asset en aplat de couleur unie.
PROCEDURAL_NODES = frozenset({
    "ShaderNodeTexNoise", "ShaderNodeTexMusgrave", "ShaderNodeTexVoronoi",
    "ShaderNodeTexWave", "ShaderNodeTexMagic", "ShaderNodeTexBrick",
    "ShaderNodeTexChecker", "ShaderNodeTexGradient",
})


def principled_material(
    name: str,
    color: tuple[float, float, float, float],
    roughness: float,
    metallic: float = 0.0,
) -> bpy.types.Material:
    """Materiau plat, reserve au decor de revue et jamais exporte."""
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    return material


def load_trim_images(project_root: Path, trim: dict) -> dict[str, bpy.types.Image]:
    """Charger les cartes publiees de l'atlas declare par le style."""
    root = Path(project_root) / trim["published_root"]
    # Le style declare le prefixe des fichiers. Le deduire de l'identifiant
    # donnait "CitylabTrim" pour v1 comme pour v2, alors que v2 publie
    # "CityLabTrimV2_".
    prefix = trim.get("file_prefix")
    if not prefix:
        prefix = "".join(part.capitalize() for part in trim["atlas"].split("_")[:-1]) + "_"
    images: dict[str, bpy.types.Image] = {}
    for name in trim["maps"]:
        path = root / f"{prefix}{name}.png"
        if not path.is_file():
            raise FileNotFoundError(f"Carte d'atlas absente : {path}")
        image = bpy.data.images.load(str(path), check_existing=True)
        image.colorspace_settings.name = "sRGB" if name == "BaseColor" else "Non-Color"
        images[name] = image
    return images


def trim_material(
    name: str,
    images: dict[str, bpy.types.Image],
    rect: dict,
    tint: tuple[float, float, float, float],
    metallic: float = 0.0,
    emission_strength: float = 0.0,
    alpha_from_variation: bool = False,
) -> bpy.types.Material:
    """Construire un materiau d'export sur les cartes de l'atlas.

    Toute la matiere entre par des `ShaderNodeTexImage` branches directement
    sur le Principled ; la palette du style n'intervient qu'en facteur sur
    l'entree, que le FBX transporte a cote de la carte.
    """
    material = bpy.data.materials.new(name)
    material.diffuse_color = tint
    material.use_nodes = True
    tree = material.node_tree
    nodes, links = tree.nodes, tree.links
    shader = nodes.get("Principled BSDF")

    def texture(map_name: str) -> bpy.types.Node:
        node = nodes.new("ShaderNodeTexImage")
        node.image = images[map_name]
        node.extension = "CLIP"
        return node

    # L'exportateur FBX ne suit la carte que si elle entre *directement* dans
    # l'entree du Principled : un simple `MixRGB` de teinte entre les deux et
    # la carte disparait de l'export, ce qui est exactement la panne que ce lot
    # corrige. La palette voyage donc en facteur sur l'entree, que le FBX porte
    # a cote de la texture.
    links.new(texture("BaseColor").outputs["Color"], shader.inputs["Base Color"])
    shader.inputs["Base Color"].default_value = tint

    normal_map = nodes.new("ShaderNodeNormalMap")
    links.new(texture("Normal").outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], shader.inputs["Normal"])
    links.new(texture("Roughness").outputs["Color"], shader.inputs["Roughness"])
    links.new(texture("Metallic").outputs["Color"], shader.inputs["Metallic"])
    shader.inputs["Metallic"].default_value = metallic

    if emission_strength > 0.0:
        shader.inputs["Emission Color"].default_value = tint
        shader.inputs["Emission Strength"].default_value = emission_strength
    if alpha_from_variation:
        links.new(texture("VariationMask").outputs["Color"], shader.inputs["Alpha"])
        # Le nom du reglage a change entre moteurs EEVEE ; la decoupe alpha est
        # demandee par le style, elle ne doit pas dependre de la version.
        if hasattr(material, "surface_render_method"):
            material.surface_render_method = "DITHERED"
        else:
            material.blend_method = "CLIP"

    # `texture_citylab_trim_v1.json` mesure ses bandes en lignes de pixels
    # (`band_bounds` indexe le tableau depuis le haut) et le style reprend ces
    # bornes telles quelles. Le v des UV monte, lui, depuis le bas : sans ce
    # retournement le mur porte les tuiles et le toit porte les planches.
    material[TRIM_RECT_TAG] = [float(rect["u"][0]), 1.0 - float(rect["v"][1]),
                               float(rect["u"][1]), 1.0 - float(rect["v"][0])]
    return material


def procedural_material_nodes(materials) -> list[str]:
    """Lister les nœuds procéduraux survivants dans un jeu de matériaux."""
    survivors: list[str] = []
    for material in materials:
        if material is None or not material.use_nodes:
            continue
        for node in material.node_tree.nodes:
            if node.bl_idname in PROCEDURAL_NODES:
                survivors.append(f"{material.name}:{node.bl_idname}")
    return survivors


def tag(obj: bpy.types.Object, category: str | None = None) -> bpy.types.Object:
    obj[ASSET_TAG] = True
    obj[PHASE_TAG] = CURRENT_PHASE
    obj[CATEGORY_TAG] = category or CURRENT_CATEGORY
    return obj


def set_phase(phase: str, category: str) -> None:
    global CURRENT_PHASE, CURRENT_CATEGORY
    if phase not in STAGES:
        raise ValueError(f"Unknown construction stage: {phase}")
    CURRENT_PHASE = phase
    CURRENT_CATEGORY = category


def retain_used_stages(minimum: int = 1) -> tuple[str, ...]:
    """Ne garder que les etapes qui portent de la geometrie.

    Une maison d'un seul niveau n'a pas de plancher, une maison sans assise de
    pierre n'a pas de soubassement. Le contrat v2 laisse un batiment declarer
    les etapes qu'il emploie ; encore faut-il qu'il ne declare pas les autres.
    """
    global STAGES
    carried = {obj.get(PHASE_TAG) for obj in asset_objects()}
    used = tuple(name for name in STAGES if name in carried)
    if len(used) < minimum:
        raise RuntimeError(
            f"Contrat de construction : {len(used)} etapes portees pour un "
            f"minimum de {minimum} -- {', '.join(used) or 'aucune'}")
    STAGES = used
    return used


def set_category(category: str) -> None:
    global CURRENT_CATEGORY
    CURRENT_CATEGORY = category


def set_bevel_policy(max_segments: int, detail_scale_m: float) -> None:
    """Regler la finesse des arrondis sur les bornes du style."""
    global BEVEL_MAX_SEGMENTS, BEVEL_DETAIL_SCALE
    BEVEL_MAX_SEGMENTS = int(max_segments)
    BEVEL_DETAIL_SCALE = float(detail_scale_m)


def apply_bevel(obj: bpy.types.Object, width: float, segments: int | None = None) -> None:
    if width <= 0.0:
        return
    if segments is None:
        # Un arrondi de trois centimetres sur un poteau de trente ne se voit pas
        # a 96 px. La finesse suit la plus petite section de l'element : seuls
        # les volumes plus epais qu'une tuile de trim payent le maximum de
        # segments que le style autorise.
        segments = (BEVEL_MAX_SEGMENTS if min(obj.dimensions) >= BEVEL_DETAIL_SCALE
                    else 1)
    modifier = obj.modifiers.new("edge_softening", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"
    modifier.angle_limit = 0.35
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def box(
    name: str,
    location: tuple[float, float, float],
    dimensions: tuple[float, float, float],
    material: bpy.types.Material,
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
    bevel: float = 0.045,
    category: str | None = None,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation)
    obj = tag(bpy.context.object, category)
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    apply_bevel(obj, bevel)
    return obj


def cylinder(
    name: str,
    location: tuple[float, float, float],
    radius: float,
    depth: float,
    material: bpy.types.Material,
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
    vertices: int = 16,
    bevel: float = 0.025,
    category: str | None = None,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation
    )
    obj = tag(bpy.context.object, category)
    obj[CURVED_TAG] = True
    obj.name = name
    obj.data.materials.append(material)
    apply_bevel(obj, bevel)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def beam_between(
    name: str,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    thickness: float,
    material: bpy.types.Material,
    bevel: float = 0.035,
    category: str | None = None,
    width: float | None = None,
) -> bpy.types.Object:
    """Membre pose entre deux points. `width` donne une section plate.

    Une planche de rive a section carree lit comme une perche : c'est ce que
    montraient les rendus de revue du lot 003 avant que la section devienne
    rectangulaire.
    """
    a, b = Vector(start), Vector(end)
    delta = b - a
    obj = box(name, tuple((a + b) * 0.5),
              (width if width is not None else thickness, thickness, delta.length),
              material, bevel=bevel, category=category)
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = delta.to_track_quat("Z", "Y")
    return obj


def surface_mesh(
    name: str,
    vertices: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
    material: bpy.types.Material,
    thickness: float = 0.0,
    category: str | None = None,
) -> bpy.types.Object:
    """Construire une surface explicite, epaissie au besoin par un solidify.

    Un versant de toit est une surface, pas une pile de tuiles : deux quads
    epaissis remplacent 160 boites biseautees pour la meme lecture RTS.
    """
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = tag(bpy.data.objects.new(name, mesh), category)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    if thickness > 0.0:
        modifier = obj.modifiers.new("roof_thickness", "SOLIDIFY")
        modifier.thickness = thickness
        modifier.offset = 0.0
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    return obj


def cut_openings(targets: list[bpy.types.Object], cutters: list[bpy.types.Object]) -> None:
    """Percer reellement la coque : une difference booleenne par ouverture.

    Toutes les couches du mur sont percees par les memes outils : un
    soubassement laisse intact reboucherait la porte qu'on vient d'ouvrir.
    """
    for target in targets:
        for cutter in cutters:
            modifier = target.modifiers.new("opening_cut", "BOOLEAN")
            modifier.operation = "DIFFERENCE"
            modifier.object = cutter
            modifier.solver = "EXACT"
            bpy.context.view_layer.objects.active = target
            bpy.ops.object.modifier_apply(modifier=modifier.name)
        target.data.update()
    for cutter in cutters:
        bpy.data.objects.remove(cutter, do_unlink=True)


def planar_edge_loops(obj: bpy.types.Object, axis: int, value: float,
                      tolerance: float = 0.002) -> int:
    """Compter les boucles fermees d'aretes contenues dans un plan.

    Une boite pleine donne une boucle : son contour. Chaque ouverture percee en
    ajoute une. C'est la preuve que le booleen a troue le mur, et non qu'un
    operateur a ete appele.
    """
    mesh = obj.data
    matrix = obj.matrix_world
    world = [matrix @ vertex.co for vertex in mesh.vertices]
    in_plane = [index for index, point in enumerate(world)
                if abs(point[axis] - value) <= tolerance]
    selected = set(in_plane)
    polygons_of_edge: dict[tuple[int, int], list[int]] = {}
    for polygon in mesh.polygons:
        for key in polygon.edge_keys:
            polygons_of_edge.setdefault(key, []).append(polygon.index)
    adjacency: dict[int, set[int]] = {index: set() for index in in_plane}
    for edge in mesh.edges:
        a, b = edge.vertices
        if a not in selected or b not in selected:
            continue
        neighbours = polygons_of_edge.get(tuple(sorted((a, b))), [])
        if len(neighbours) != 2:
            continue
        # Une arete de triangulation a ses deux faces dans le meme plan : elle
        # relierait le contour exterieur aux contours des trous et effacerait
        # la preuve. Seules les aretes vives bordent une ouverture.
        first = mesh.polygons[neighbours[0]].normal
        second = mesh.polygons[neighbours[1]].normal
        if first.angle(second, 0.0) < 0.087:
            continue
        adjacency[a].add(b)
        adjacency[b].add(a)
    loops = 0
    seen: set[int] = set()
    for start in in_plane:
        if start in seen or not adjacency[start]:
            continue
        stack, component = [start], []
        seen.add(start)
        while stack:
            current = stack.pop()
            component.append(current)
            for neighbour in adjacency[current]:
                if neighbour not in seen:
                    seen.add(neighbour)
                    stack.append(neighbour)
        edges = sum(len(adjacency[index]) for index in component) // 2
        if edges >= len(component) and len(component) >= 3:
            loops += 1
    return loops


def uv_place(obj: bpy.types.Object, world_uv_scale: float) -> None:
    """Projeter chaque face puis reposer l'ilot dans le rectangle de son trim.

    Le materiau porte son rectangle ; aucun ilot ne sort de la bande declaree,
    donc aucun ne sort de [0 ; 1]. `world_uv_scale_m` fixe la part de bande
    qu'occupe un element : un volet ne s'etire pas sur toute la planche.
    """
    mesh = obj.data
    if not mesh.polygons:
        return
    material = mesh.materials[0] if mesh.materials else None
    if material is None or TRIM_RECT_TAG not in material:
        raise RuntimeError(f"Objet sans rectangle de trim : {obj.name}")
    u0, v0, u1, v1 = (float(value) for value in material[TRIM_RECT_TAG])
    while mesh.uv_layers:
        mesh.uv_layers.remove(mesh.uv_layers[0])
    layer = mesh.uv_layers.new(name="UVMap")
    matrix = obj.matrix_world
    world = [matrix @ vertex.co for vertex in mesh.vertices]
    for polygon in mesh.polygons:
        normal = matrix.to_3x3() @ polygon.normal
        axis = max(range(3), key=lambda index: abs(normal[index]))
        first, second = [index for index in range(3) if index != axis]
        points = [(world[mesh.loops[loop].vertex_index][first],
                   world[mesh.loops[loop].vertex_index][second])
                  for loop in polygon.loop_indices]
        min_a = min(point[0] for point in points)
        max_a = max(point[0] for point in points)
        min_b = min(point[1] for point in points)
        max_b = max(point[1] for point in points)
        extent_a, extent_b = max_a - min_a, max_b - min_b
        span_a = min(1.0, max(extent_a, 1e-4) / world_uv_scale)
        span_b = min(1.0, max(extent_b, 1e-4) / world_uv_scale)
        # Decalage stable derive de la geometrie : deux elements voisins ne
        # lisent pas la meme portion de bande, et deux executions non plus.
        centre = ((min_a + max_a) * 0.5, (min_b + max_b) * 0.5)
        offset_a = (centre[0] * 0.3719 + centre[1] * 0.5773) % 1.0 * (1.0 - span_a)
        offset_b = (centre[0] * 0.1931 + centre[1] * 0.7549) % 1.0 * (1.0 - span_b)
        for loop, (point_a, point_b) in zip(polygon.loop_indices, points):
            local_a = 0.5 if extent_a <= 1e-6 else (point_a - min_a) / extent_a
            local_b = 0.5 if extent_b <= 1e-6 else (point_b - min_b) / extent_b
            layer.data[loop].uv = (
                u0 + (u1 - u0) * (offset_a + span_a * local_a),
                v0 + (v1 - v0) * (offset_b + span_b * local_b),
            )


def uv_loops_outside_unit(obj: bpy.types.Object) -> int:
    outside = 0
    for layer in obj.data.uv_layers:
        for loop in layer.data:
            if not (0.0 <= loop.uv.x <= 1.0 and 0.0 <= loop.uv.y <= 1.0):
                outside += 1
    return outside


def _swap(point: tuple[float, float, float], axis: str) -> tuple[float, float, float]:
    if axis == "x":
        return point
    return (point[1], point[0], point[2])


def roof_surface(
    name: str,
    form: str,
    half_span: float,
    half_run: float,
    span_axis: str,
    eave_z: float,
    rise: float,
    overhang: float,
    thickness: float,
    material: bpy.types.Material,
    centre: tuple[float, float] = (0.0, 0.0),
) -> bpy.types.Object:
    """Un versant est un plan epaissi : le relief vient de la normal map.

    `span_axis` porte la pente ; le faitage lui est perpendiculaire, ce qui
    rend l'axe de faitage du style visible sur la silhouette.
    """
    span = half_span + overhang
    run = half_run + overhang
    top = eave_z + rise
    if form in {"gable", "gable_dormer"}:
        points = [(-span, -run, eave_z), (-span, run, eave_z), (0.0, run, top),
                  (0.0, -run, top), (span, -run, eave_z), (span, run, eave_z)]
        faces = [(0, 1, 2, 3), (3, 2, 5, 4)]
    elif form == "hipped":
        ridge = max(overhang, run - span)
        points = [(-span, -run, eave_z), (span, -run, eave_z), (span, run, eave_z),
                  (-span, run, eave_z), (0.0, -ridge, top), (0.0, ridge, top)]
        faces = [(0, 1, 4), (1, 2, 5, 4), (2, 3, 5), (3, 0, 4, 5)]
    else:
        raise ValueError(f"Forme de toit hors vocabulaire : {form}")
    vertices = [_swap(point, span_axis) for point in points]
    vertices = [(x + centre[0], y + centre[1], z) for x, y, z in vertices]
    return surface_mesh(name, vertices, faces, material, thickness, category="roof_plane")


def eave_strip(
    name: str,
    half_span: float,
    half_run: float,
    span_axis: str,
    eave_z: float,
    overhang: float,
    depth: float,
    teeth_per_m: float,
    material: bpy.types.Material,
    centre: tuple[float, float] = (0.0, 0.0),
    all_sides: bool = False,
) -> list[bpy.types.Object]:
    """Bande dentelee d'egout : la seule geometrie qui crenele la toiture.

    `teeth_per_m` fixe le nombre de dents, `mode: alpha_clip` du style fixe le
    materiau : la decoupe est portee a la fois par la maille et par le masque.
    Une croupe a quatre egouts a la meme altitude, un pignon deux.
    """
    span = half_span + overhang
    run = half_run + overhang
    strips: list[bpy.types.Object] = []

    def fringe(label: str, fixed: float, extent: float, swapped: bool) -> None:
        length = 2.0 * extent
        teeth = max(1, int(round(teeth_per_m * length)))
        vertices: list[tuple[float, float, float]] = []
        faces: list[tuple[int, ...]] = []
        for index in range(teeth + 1):
            moving = -extent + length * index / teeth
            point = (moving, fixed, eave_z) if swapped else (fixed, moving, eave_z)
            vertices.append(_swap(point, span_axis))
        for index in range(teeth):
            moving = -extent + length * (index + 0.5) / teeth
            point = ((moving, fixed, eave_z - depth) if swapped
                     else (fixed, moving, eave_z - depth))
            vertices.append(_swap(point, span_axis))
            faces.append((index, index + 1, teeth + 1 + index))
        placed = [(x + centre[0], y + centre[1], z) for x, y, z in vertices]
        strips.append(surface_mesh(f"{name}_{label}", placed, faces, material,
                                   category="eave"))

    for side in (-1, 1):
        fringe("lo" if side < 0 else "hi", side * span, run, False)
    if all_sides:
        for side in (-1, 1):
            fringe("end_lo" if side < 0 else "end_hi", side * run, span, True)
    return strips


def add_lantern(
    name: str,
    location: tuple[float, float, float],
    iron: bpy.types.Material,
    ember: bpy.types.Material,
) -> None:
    x, y, z = location
    box(name + "_cap", (x, y, z + 0.34), (0.42, 0.38, 0.12), iron, bevel=0.0,
        category="hardware")
    box(name + "_base", (x, y, z - 0.34), (0.42, 0.38, 0.12), iron, bevel=0.0,
        category="hardware")
    cylinder(name + "_glow", (x, y, z), 0.16, 0.5, ember, vertices=8, bevel=0.0,
             category="lantern_glass")
    bpy.ops.object.light_add(type="POINT", location=location)
    light = tag(bpy.context.object)
    light.name = name + "_light"
    light.data.energy = 125.0
    light.data.color = (1.0, 0.22, 0.035)
    light.data.shadow_soft_size = 1.2


def setup_review(materials: dict[str, bpy.types.Material]) -> None:
    ground = box("review_ground", (0.0, 0.0, -0.16), (24.0, 21.0, 0.25), materials["ground"], bevel=0.18)
    ground[ASSET_TAG] = False
    del ground[PHASE_TAG]
    world = bpy.data.worlds.new("CityLab Dark World")
    bpy.context.scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes["Background"]
    background.inputs["Color"].default_value = (0.006, 0.012, 0.021, 1.0)
    background.inputs["Strength"].default_value = 0.22
    lights = [
        ("key", "AREA", (8.0, -11.0, 16.0), 2100.0, (1.0, 0.62, 0.34), 8.0),
        ("fill", "AREA", (-11.0, -2.0, 10.0), 1650.0, (0.24, 0.42, 0.74), 9.0),
        ("rim", "AREA", (2.0, 10.0, 13.0), 1550.0, (0.38, 0.52, 0.82), 7.0),
    ]
    for name, light_type, location, energy, color, size in lights:
        bpy.ops.object.light_add(type=light_type, location=location)
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.color = color
        light.data.shape = "DISK"
        light.data.size = size
        light.rotation_euler = (Vector((0.0, 0.0, 3.5)) - light.location).to_track_quat("-Z", "Y").to_euler()


def render_view(output: Path, location: tuple[float, float, float], target: tuple[float, float, float], ortho: float, resolution: int) -> None:
    scene = bpy.context.scene
    if scene.camera is None:
        bpy.ops.object.camera_add()
        scene.camera = bpy.context.object
        scene.camera.name = "review_camera"
    camera = scene.camera
    camera.location = location
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = ortho
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = str(output)
    scene.view_settings.look = "AgX - Medium High Contrast"
    bpy.ops.render.render(write_still=True)


def render_silhouette(output: Path, location: tuple[float, float, float],
                      target: tuple[float, float, float], ortho: float,
                      resolution: int) -> None:
    """Rendre la silhouette pleine du bati seul, fond transparent.

    L'alpha du PNG *est* la silhouette : la bande d'egout a decoupe alpha y
    entre comme le reste, ce qui est le point de la porte A-3.
    """
    scene = bpy.context.scene
    transparent = scene.render.film_transparent
    scene.render.film_transparent = True
    render_view(output, location, target, ortho, resolution)
    scene.render.film_transparent = transparent


def category_triangles() -> dict[str, int]:
    """Triangles du LOD0 par categorie de LOD.

    Sans cette mesure, discuter d'un depassement de budget revient a deviner :
    on voyait la somme par phase, jamais ce qui la composait.
    """
    counts: dict[str, int] = {}
    for obj in asset_objects():
        if obj.type != "MESH":
            continue
        obj.data.calc_loop_triangles()
        key = str(obj.get(CATEGORY_TAG) or "?")
        counts[key] = counts.get(key, 0) + len(obj.data.loop_triangles)
    return dict(sorted(counts.items(), key=lambda item: -item[1]))


def asset_objects() -> list[bpy.types.Object]:
    return [obj for obj in bpy.context.scene.objects if obj.type == "MESH" and obj.get(ASSET_TAG, False)]


def phase_objects(phase: str) -> list[bpy.types.Object]:
    return [obj for obj in asset_objects() if obj.get(PHASE_TAG) == phase]


def show_construction_through(stage_index: int,
                              hidden_categories: set[str] | None = None) -> None:
    """Montrer le chantier jusqu'a l'etape donnee, incluse.

    `hidden_categories` retire les categories que le LOD0 ne montre pas -- les
    proxys de coque, qui sont des boites pleines coincidant avec les coques
    creuses. Sans cela le rendu d'etape coiffait chaque niveau d'un couvercle
    plein et bouchait les percements : la revue ne montrait pas ce que le jeu
    affiche.
    """
    hidden = hidden_categories or set()
    for obj in bpy.context.scene.objects:
        phase = obj.get(PHASE_TAG)
        if phase not in STAGES:
            continue
        visible = (STAGES.index(phase) <= stage_index
                   and str(obj.get(CATEGORY_TAG) or "") not in hidden)
        obj.hide_render = not visible
        obj.hide_viewport = not visible


def uv_assets(world_uv_scale: float) -> None:
    """Deposer les UV de tous les elements avant tout decoupage en LOD."""
    for obj in asset_objects():
        uv_place(obj, world_uv_scale)


def decimate_in_place(obj: bpy.types.Object, ratio: float) -> None:
    modifier = obj.modifiers.new("lod_curved_decimate", "DECIMATE")
    modifier.ratio = ratio
    modifier.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def joined_copy(name: str, sources: list[bpy.types.Object] | None = None,
                curved_ratio: float = 1.0) -> bpy.types.Object:
    copies: list[bpy.types.Object] = []
    for source in sources or asset_objects():
        copy = source.copy()
        copy.data = source.data.copy()
        bpy.context.collection.objects.link(copy)
        copy.matrix_world = source.matrix_world.copy()
        copy[ASSET_TAG] = False
        if curved_ratio < 1.0 and source.get(CURVED_TAG, False):
            decimate_in_place(copy, curved_ratio)
        copies.append(copy)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in copies:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = copies[0]
    bpy.ops.object.join()
    joined = bpy.context.object
    joined.name = name
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for layer in joined.data.uv_layers:
        for loop in layer.data:
            # Les importeurs FBX peuvent dériver d'environ 1e-5 entre deux
            # processus Blender. Une grille UV 1/512 rend le master binaire
            # reproductible ; ces matériaux utilisent une palette/trim partagé,
            # donc ce snap sous-pixel ne dégrade pas la lecture du bâtiment.
            loop.uv = (
                round(loop.uv.x * 512.0) / 512.0,
                round(loop.uv.y * 512.0) / 512.0,
            )
    joined.data.calc_loop_triangles()
    return joined


def lod_selection(objects: list[bpy.types.Object], lod: int,
                  policy: dict) -> list[bpy.types.Object]:
    """Choisir les elements d'un LOD par suppression, jamais par decimation.

    LOD1 retire les micro-accessoires declares par le style ; LOD2 ne garde que
    les categories porteuses de silhouette. La decimation ne subsiste que sur
    les elements courbes du LOD1, bornee par le style.
    """
    # Une categorie peut n'exister que pour un LOD lointain : le proxy de coque
    # remplace au LOD2 des niveaux creuses et perces, trop chers pour une
    # silhouette de 96 px. Il doit donc etre absent des LOD proches.
    late = set((policy.get("lod0") or {}).get("drop_categories") or [])
    if lod == 0:
        return [obj for obj in objects if obj.get(CATEGORY_TAG) not in late]
    if lod == 1:
        dropped = set(policy["lod1"]["drop_categories"]) | late
        dropped -= set((policy.get("lod1") or {}).get("keep_categories") or [])
        return [obj for obj in objects if obj.get(CATEGORY_TAG) not in dropped]
    kept = set(policy["lod2"]["keep_categories"])
    return [obj for obj in objects if obj.get(CATEGORY_TAG) in kept]


def triangle_count(obj: bpy.types.Object) -> int:
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def canonical_hash(obj: bpy.types.Object) -> str:
    digest = hashlib.sha256()
    obj.data.calc_loop_triangles()
    for vertex in obj.data.vertices:
        digest.update(struct.pack("<3f", *vertex.co))
    for triangle in obj.data.loop_triangles:
        digest.update(struct.pack("<3I", *triangle.vertices))
        digest.update(struct.pack("<I", triangle.material_index))
    return digest.hexdigest()


def export_assets(
    asset_id: str,
    raw_dir: Path,
    model_dir: Path,
    lod_policy: dict,
) -> tuple[Path, Path, dict[str, list[int]], list[int], str, dict]:
    # L'export ne depend pas de ce que la revue montre. `joined_copy` selectionne
    # les objets pour les fusionner, et un objet masque ne se selectionne pas :
    # masquer les proxys pour le rendu d'etape faisait disparaitre 24 triangles
    # du LOD2. La visibilite est remise a plat ici, une fois pour toutes.
    for obj in asset_objects():
        obj.hide_render = False
        obj.hide_viewport = False
    master = joined_copy(asset_id + "_MASTER_LOD0")
    mesh_hash = canonical_hash(master)
    curved_ratio = float(lod_policy["lod1"]["decimate_curved_min_ratio"])
    phase_triangles: dict[str, list[int]] = {}
    export_lods: list[bpy.types.Object] = []
    for phase in STAGES:
        source = phase_objects(phase)
        if not source:
            # Une etape declaree porte de la geometrie. C'est l'invariant I1 du
            # contrat v2, et le generateur ne declare que ce qu'il pose.
            raise RuntimeError(f"Construction stage has no geometry: {phase}")
        prefix = (f"{asset_id}__{STAGE_MARKER}{STAGE_ORDER[phase]:02d}"
                  f"_{phase.upper()}")
        counts = [0, 0, 0]
        for lod in range(3):
            selection = lod_selection(source, lod, lod_policy)
            if not selection:
                # Une etape peut manquer a un LOD lointain sans manquer a la
                # fin : il n'y a pas de menuiserie lisible a 96 px. Le nœud
                # n'est alors pas emis, plutot que d'exporter un maillage vide
                # ou de forcer une categorie a survivre a une politique de LOD
                # qui la retire.
                if lod == 0:
                    raise RuntimeError(
                        f"Etape {phase} sans element au LOD0 : une etape "
                        "declaree porte de la geometrie")
                continue
            joined = joined_copy(f"{prefix}_LOD{lod}", selection,
                                 curved_ratio if lod == 1 else 1.0)
            counts[lod] = triangle_count(joined)
            export_lods.append(joined)
        phase_triangles[phase] = counts
    triangles = [sum(phase_triangles[phase][lod] for phase in STAGES) for lod in range(3)]
    materials = {slot.material for obj in export_lods for slot in obj.material_slots}
    gates = {
        "procedural_material_nodes": procedural_material_nodes(sorted(
            materials, key=lambda material: material.name if material else "")),
        "uv_loops_outside_unit": sum(uv_loops_outside_unit(obj) for obj in export_lods),
        "export_materials": sorted(material.name for material in materials if material),
    }
    for original in asset_objects():
        original.hide_viewport = True
        original.hide_render = True
    raw_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    glb = raw_dir / f"{asset_id}.glb"
    fbx = model_dir / f"{asset_id}.fbx"
    bpy.ops.object.select_all(action="DESELECT")
    master.select_set(True)
    bpy.context.view_layer.objects.active = master
    bpy.ops.export_scene.gltf(filepath=str(glb), export_format="GLB", use_selection=True)
    bpy.ops.object.select_all(action="DESELECT")
    master.hide_viewport = True
    master.hide_render = True
    for obj in export_lods:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = export_lods[0]
    bpy.ops.export_scene.fbx(
        filepath=str(fbx),
        use_selection=True,
        axis_forward="-Z",
        axis_up="Y",
        apply_scale_options="FBX_SCALE_ALL",
        bake_space_transform=True,
        add_leaf_bones=False,
        mesh_smooth_type="FACE",
    )
    return glb, fbx, phase_triangles, triangles, mesh_hash, gates


def color_from_hex(value: str) -> tuple[float, float, float, float]:
    cleaned = value.removeprefix("#")
    if len(cleaned) != 6:
        raise ValueError(f"Expected #RRGGBB color, got {value}")
    return tuple(int(cleaned[index:index + 2], 16) / 255.0 for index in (0, 2, 4)) + (1.0,)


def tint_from_hex(value: str) -> tuple[float, float, float, float]:
    """Teinte d'une palette : sa couleur, sans sa valeur.

    Les palettes du style sont des couleurs de base presque noires. Multipliees
    telles quelles par l'albedo de l'atlas, elles l'eteignent et la matiere
    disparait. La luminance appartient desormais aux cartes ; la palette ne
    garde que la dominante.
    """
    color = color_from_hex(value)
    peak = max(color[:3])
    if peak <= 0.0:
        return (1.0, 1.0, 1.0, 1.0)
    return tuple(channel / peak for channel in color[:3]) + (1.0,)


def build_materials(project_root: Path, style: dict, palette: dict, suffix: str,
                    wall_system: str, roof_system: str,
                    upper_band: str | None = None,
                    lower_band: str | None = None) -> dict[str, bpy.types.Material]:
    """Un materiau par bande de trim, teinte par la palette du style.

    Le style dit quelle bande porte le soubassement, le corps et la couverture ;
    ce sont les seules surfaces exportees. Le sol de revue reste un aplat, hors
    export.

    La finition tiree par le plan l'emporte sur la valeur par defaut du systeme
    de mur : c'est par elle que deux variantes d'une meme famille recoivent deux
    matieres, sans que leur masse change.
    """
    trim = style["trim"]
    images = load_trim_images(project_root, trim)
    rects = trim["rects"]
    wall_map = dict(trim["wall_system_map"][wall_system])
    if upper_band:
        wall_map["body"] = upper_band
    if lower_band:
        wall_map["base"] = lower_band
    roof_band = trim["roof_system_map"][roof_system]
    wood = tint_from_hex(palette["wood"])
    highlight = tint_from_hex(palette["wood_highlight"])
    roof = tint_from_hex(palette["roof"])
    accent = tint_from_hex(palette["roof_accent"])
    body, base = rects[wall_map["body"]], rects[wall_map["base"]]
    covering = rects[roof_band]
    return {
        "wood": trim_material(f"frontier_body_{suffix}", images, body, highlight),
        "pale_wood": trim_material(f"frontier_body_pale_{suffix}", images, body,
                                   tuple(min(1.0, channel * 1.9) for channel in highlight[:3]) + (1.0,)),
        "bark": trim_material(f"frontier_body_dark_{suffix}", images, body, wood),
        "stone": trim_material(f"frontier_base_{suffix}", images, base, (1.0, 1.0, 1.0, 1.0)),
        "plaster": trim_material(f"frontier_base_pale_{suffix}", images, base,
                                 (0.72, 0.70, 0.64, 1.0)),
        "roof": trim_material(f"frontier_roof_{suffix}", images, covering, roof),
        "roof_alt": trim_material(f"frontier_roof_accent_{suffix}", images, covering, accent),
        "eave": trim_material(f"frontier_eave_{suffix}", images, covering, accent,
                              alpha_from_variation=True),
        "iron": trim_material(f"frontier_iron_{suffix}", images, base,
                              (0.22, 0.24, 0.26, 1.0), metallic=0.85),
        "blade": trim_material(f"frontier_steel_{suffix}", images, base,
                               (0.62, 0.66, 0.68, 1.0), metallic=0.92),
        "bronze": trim_material(f"frontier_bronze_{suffix}", images, base,
                                (0.72, 0.34, 0.10, 1.0), metallic=0.78),
        "ember": trim_material(f"frontier_ember_{suffix}", images, body,
                               (1.0, 0.22, 0.04, 1.0), emission_strength=2.4),
        "ground": principled_material("review_ground", (0.012, 0.020, 0.019, 1.0), 0.94),
    }


