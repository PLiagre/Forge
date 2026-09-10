"""Calcule le plan du village, et refuse celui qui depasse son plafond.

`Assets/CityLabHost/Scenes/CityLabConstruction.unity` aligne huit fois la meme
maison pour prouver les etapes de chantier. C'est une preuve, pas une ville, et
`CityLab.unity` etait vide.

Ce plan est une **donnee** : il est calcule et controle ici, hors Unity, puis
Unity l'ecrit en scene. Trois raisons, et chacune a deja coute quelque chose
ailleurs dans ce depot.

- **Le plafond de triangles est une porte Python.** Une scene qui le depasse ne
  s'ecrit pas. La juger dans l'editeur demanderait d'ouvrir Unity pour savoir
  si elle est acceptable.
- **Le terrain est echantillonne une seule fois.** Chaque batiment porte sa
  hauteur de sol dans le plan ; Unity n'en recalcule aucune. Deux
  implementations de la meme fonction de relief divergeraient, et un batiment
  flotterait -- des accessoires cales sur un Z absolu ont deja flotte de 0,92 m.
- **Le cout d'un decor est son LOD0, pas le total de son fichier.** Une source
  EmaceArt porte ses trois LOD dans le meme FBX : sommer les trois et comparer
  au LOD0 d'un batiment double la facture. C'est ce que fait le recensement, et
  c'est ce que lit ce plan.

    py Tools/AssetFactory/village_plan.py
    py Tools/AssetFactory/village_plan.py --report

Il ne lance pas Unity, ne publie rien sous `Assets/` et ne modifie aucune source
Vendor : il les cite par chemin et par SHA-256.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SPEC = "AssetFactory/Catalogs/village_pilot.json"
PLAN = "AssetFactory/Manifests/village_pilot.json"
STATE = "AssetFactory/Manifests/factory_build_state.json"
CENSUS = "AssetFactory/Reports/vendor_prop_census.json"
PREFAB_ROOT = "Assets/CityLabHost/Adapted/Factory/Prefabs"


class VillageError(RuntimeError):
    """Erreur attendue et lisible du plan de village."""


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def instance_cost(item: dict) -> int:
    """Le LOD0 d'une source, ou son maillage unique quand elle n'en nomme aucun.

    Seize sources sur 243 n'ont aucun maillage nomme `LOD0` -- toutes les
    Polytope, dont les clotures modulaires. Un import « LOD0 seulement » n'en
    rendrait rien : c'est le piege de la lame plate, et il se lit ici en donnee.
    """
    return item["triangles_lod0"] or item["triangles_unnamed"] or item["triangles"]


# --------------------------------------------------------------------------
# Terrain
# --------------------------------------------------------------------------

def heightfield(seed: int, extent: float, cells: int, amplitude: float) -> list[list[float]]:
    """Un relief leger, somme de trois ondes, echantillonne une fois pour toutes.

    Pas de bruit tabule ni de bibliotheque : trois sinusoides suffisent a poser
    des creux et des bosses lisibles, et se rejouent a l'identique depuis la
    graine. Ce qui compte n'est pas le realisme du relief, c'est que le plan et
    la scene lisent **les memes nombres**.
    """
    rng = random.Random(seed)
    waves = [(rng.uniform(0.020, 0.055), rng.uniform(0.020, 0.055),
              rng.uniform(0.0, math.tau), rng.uniform(0.45, 1.0))
             for _ in range(3)]
    weight = sum(wave[3] for wave in waves)
    grid = []
    for row in range(cells + 1):
        z = -extent * 0.5 + extent * row / cells
        line = []
        for column in range(cells + 1):
            x = -extent * 0.5 + extent * column / cells
            value = sum(amp * math.sin(fx * x + phase) * math.cos(fz * z + phase)
                        for fx, fz, phase, amp in waves)
            line.append(round(amplitude * value / weight, 4))
        grid.append(line)
    return grid


def sample_height(grid: list[list[float]], extent: float, x: float, z: float) -> float:
    """Hauteur du terrain en un point, par interpolation bilineaire de la grille.

    C'est la seule facon d'echantillonner : lire une formule ici et la grille
    la-bas ferait diverger le sol du plan et le sol de la scene.
    """
    cells = len(grid) - 1
    u = (x + extent * 0.5) / extent * cells
    v = (z + extent * 0.5) / extent * cells
    u = min(max(u, 0.0), cells - 1e-9)
    v = min(max(v, 0.0), cells - 1e-9)
    column, row = int(u), int(v)
    fu, fv = u - column, v - row
    top = grid[row][column] * (1 - fu) + grid[row][column + 1] * fu
    bottom = grid[row + 1][column] * (1 - fu) + grid[row + 1][column + 1] * fu
    return round(top * (1 - fv) + bottom * fv, 4)


# --------------------------------------------------------------------------
# Choix des batiments
# --------------------------------------------------------------------------

def chosen_buildings(spec: dict, state: dict) -> list[str]:
    """Les vingt-quatre variantes une fois, puis les repetitions.

    Chaque variante produite est posee au moins une fois : une scene qui n'en
    montrerait que la moitie ne dirait pas ce que l'usine sait faire. Les
    repetitions vont d'abord a l'habitat, parce qu'un bourg est fait de maisons
    et non de huit chapelles.
    """
    every = sorted(state["assets"])
    total = int(spec["building_count"])
    if total < len(every):
        raise VillageError(
            f"Le bourg demande {total} batiments pour {len(every)} variantes "
            f"produites : chacune doit pouvoir etre posee au moins une fois.")

    repeatable = [item for item in every
                  if any(key in item for key in ("residence", "granary", "barn",
                                                 "warehouse"))]
    if not repeatable:
        raise VillageError("Aucune variante repetable dans l'etat de build.")
    rng = random.Random(int(spec["seed"]))
    extra = [repeatable[rng.randrange(len(repeatable))]
             for _ in range(total - len(every))]
    return every + extra


# --------------------------------------------------------------------------
# Parcelles
# --------------------------------------------------------------------------

def plots(spec: dict) -> list[dict]:
    """Les rues du bourg, et une bande de parcelles de chaque cote.

    Une parcelle connait son centre et le sens dans lequel elle regarde la rue :
    un batiment tourne au hasard donne un tas de maisons, pas un bourg.

    Les axes sont une donnee. Une croix simple n'ouvrait que **36 parcelles pour
    40 batiments**, et la porte a refuse le plan -- ce qui est son travail. La
    reponse n'est pas de rapprocher les maisons jusqu'a ce que ca rentre, c'est
    d'ouvrir les rues qu'un bourg de cette taille a de toute facon.
    """
    extent = float(spec["extent_m"])
    streets = spec["streets"]
    half = float(streets["half_width_m"])
    depth = float(streets["plot_depth_m"])
    step = depth + float(streets["margin_m"])
    band = half + depth * 0.5
    axes = [float(value) for value in streets["axes_m"]]

    square = float(streets.get("square_radius_m", 0.0))
    found = []
    reach = extent * 0.5 - depth * 0.5
    count = int(reach * 2 // step)
    for index in range(count + 1):
        along = -reach + index * step
        if along > reach:
            break
        for axis in axes:
            for side in (-1, 1):
                for x, z, rotation, name in (
                        # Rue nord-sud : la facade regarde la chaussee.
                        (axis + side * band, along,
                         270.0 if side > 0 else 90.0, f"nord_sud_{axis:+.0f}"),
                        # Rue est-ouest : symetrique.
                        (along, axis + side * band,
                         180.0 if side > 0 else 0.0, f"est_ouest_{axis:+.0f}")):
                    if max(abs(x), abs(z)) + depth * 0.5 > extent * 0.5:
                        continue
                    # La place reste vide de batiments : c'est elle qui fait la
                    # difference entre un bourg et une grille de boites.
                    if math.hypot(x, z) < square:
                        continue
                    found.append({"x": x, "z": z, "rotation_y": rotation,
                                  "street": name})
    # Un ordre stable, et le centre d'abord : le coeur du bourg se remplit avant
    # ses lisieres.
    found.sort(key=lambda plot: (round(plot["x"] ** 2 + plot["z"] ** 2, 3),
                                 plot["street"], plot["x"], plot["z"]))
    return found


def overlaps(a: dict, b: dict, margin: float) -> bool:
    return (abs(a["x"] - b["x"]) * 2.0 < a["w"] + b["w"] + margin
            and abs(a["z"] - b["z"]) * 2.0 < a["d"] + b["d"] + margin)


def footprint(metrics: dict, rotation: float) -> tuple[float, float]:
    """Emprise au sol, tournee avec le batiment.

    Une emprise qui ne tournerait pas laisserait deux maisons se traverser des
    que la rue change d'axe.
    """
    width = float(metrics["grammar"]["width_m"])
    depth = float(metrics["grammar"]["depth_m"])
    return (depth, width) if int(round(rotation)) % 180 == 90 else (width, depth)


# --------------------------------------------------------------------------
# Plan
# --------------------------------------------------------------------------

def build_plan(root: Path) -> dict:
    spec = load(root / SPEC)
    state = load(root / STATE)
    census = {item["id"]: item for item in load(root / CENSUS)["sources"]
              if item["status"] == "passed"}

    extent = float(spec["extent_m"])
    terrain = spec["terrain"]
    grid = heightfield(int(spec["seed"]), extent, int(terrain["cells"]),
                       float(terrain["amplitude_m"]))
    margin = float(spec["streets"]["margin_m"])

    wanted = chosen_buildings(spec, state)
    free = plots(spec)
    if len(free) < len(wanted):
        raise VillageError(
            f"{len(free)} parcelles pour {len(wanted)} batiments : elargir "
            f"l'emprise ou resserrer les parcelles.")

    placed: list[dict] = []
    for index, asset_id in enumerate(wanted):
        metrics = load(root / "AssetFactory" / "Reports" / f"{asset_id}_metrics.json")
        for plot in free:
            if plot.get("taken"):
                continue
            width, depth = footprint(metrics, plot["rotation_y"])
            candidate = {"x": plot["x"], "z": plot["z"], "w": width, "d": depth}
            if any(overlaps(candidate, other, margin) for other in placed):
                continue
            plot["taken"] = True
            family, variant = asset_id.rsplit("_", 1)
            placed.append({
                "id": f"{asset_id}#{index:02d}",
                "asset": asset_id,
                "family": family,
                "variant": variant,
                "prefab": f"{PREFAB_ROOT}/CityLab_{family}_{variant.upper()}.prefab",
                "x": round(plot["x"], 3),
                "z": round(plot["z"], 3),
                "ground_y": sample_height(grid, extent, plot["x"], plot["z"]),
                "rotation_y": plot["rotation_y"],
                "street": plot["street"],
                "w": round(width, 3),
                "d": round(depth, 3),
                "triangles": state["assets"][asset_id]["triangles"]["lod0"],
            })
            break
        else:
            raise VillageError(f"Aucune parcelle libre pour {asset_id}")

    decor, decor_triangles = place_decor(root, spec, census, grid, placed)

    terrain_triangles = int(terrain["cells"]) ** 2 * 2
    building_triangles = sum(item["triangles"] for item in placed)
    total = building_triangles + decor_triangles + terrain_triangles
    ceiling = int(spec["budget"]["scene_triangles_max"])

    return {
        "schema": 1,
        "id": "citylab_village_pilot",
        "spec": SPEC,
        "seed": int(spec["seed"]),
        "extent_m": extent,
        "inhabitants": bool(spec["inhabitants"]),
        "terrain": {
            "kind": terrain["kind"],
            "cells": int(terrain["cells"]),
            "extent_m": extent,
            "amplitude_m": float(terrain["amplitude_m"]),
            # A plat, ligne par ligne, `(cells + 1)` valeurs par ligne : c'est
            # la seule forme que `JsonUtility` sache relire cote Unity, et une
            # grille ecrite deux fois divergerait tot ou tard.
            "heights_row_major": [value for line in grid for value in line],
        },
        "buildings": placed,
        "decor": decor,
        "budget": {
            "scene_triangles_max": ceiling,
            "buildings": building_triangles,
            "decor": decor_triangles,
            "terrain": terrain_triangles,
            "total": total,
        },
        "gates": {
            "V-1_batiments_poses": f"{len(placed)}/{spec['building_count']}",
            "V-2_toutes_variantes_posees":
                sorted({item["asset"] for item in placed}) == sorted(state["assets"]),
            "V-3_aucun_recouvrement": True,
            "V-4_dans_l_emprise": True,
            "V-5_plafond_triangles": total <= ceiling,
        },
        "unity_launched": False,
    }


def on_a_street(spec: dict, x: float, z: float, clearance: float) -> bool:
    """Le point tombe-t-il sur une chaussee ?

    Une chaussee encombree n'est plus une rue. C'est ce qui manquait a la
    premiere carte : le decor la traversait de part en part et le bourg se
    lisait comme un semis de boites dans du bruit.
    """
    half = float(spec["streets"]["half_width_m"]) + clearance
    return any(abs(x - axis) < half or abs(z - axis) < half
               for axis in (float(value) for value in spec["streets"]["axes_m"]))


def draw_spot(placement: str, spec: dict, buildings: list[dict],
              rng: random.Random, radius: float) -> tuple[float, float] | None:
    """Tirer un emplacement qui respecte ce que le catalogue declare.

    `placement` etait ecrit dans le catalogue et **jamais lu** : le decor
    tombait uniformement sur les 140 metres, chaussees comprises. C'est le
    defaut D-1, dans un autre fichier -- une chose declaree et non posee -- et
    il se voyait sur la carte, pas sur les compteurs.

      `hors_parcelle`      la campagne autour du bourg, hors des rues ;
      `bord_de_parcelle`   contre un batiment, du cote de sa facade ;
      `place`              sur la place, au croisement central.
    """
    extent = float(spec["extent_m"])
    limit = extent * 0.5 - radius

    if placement == "place":
        square = float(spec["streets"].get("square_radius_m", 0.0))
        if square <= 0.0:
            return None
        angle = rng.uniform(0.0, math.tau)
        distance = math.sqrt(rng.uniform(0.0, 1.0)) * max(0.0, square - radius)
        return math.cos(angle) * distance, math.sin(angle) * distance

    if placement == "bord_de_parcelle":
        if not buildings:
            return None
        host = buildings[rng.randrange(len(buildings))]
        # Le long du pignon, du cote oppose a la rue : une cloture posee au
        # milieu de la chaussee ne clot rien.
        angle = math.radians(float(host["rotation_y"]))
        away = (-math.sin(angle), -math.cos(angle))
        reach = max(host["w"], host["d"]) * 0.5 + radius + rng.uniform(0.3, 1.6)
        drift = rng.uniform(-0.5, 0.5) * max(host["w"], host["d"])
        x = host["x"] + away[0] * reach - away[1] * drift
        z = host["z"] + away[1] * reach + away[0] * drift
        if abs(x) > limit or abs(z) > limit or on_a_street(spec, x, z, radius):
            return None
        return x, z

    # `hors_parcelle` : la campagne. Elle commence ou le bati s'arrete.
    for _ in range(12):
        x = rng.uniform(-limit, limit)
        z = rng.uniform(-limit, limit)
        if on_a_street(spec, x, z, radius):
            continue
        return x, z
    return None


def pack_prefab(root: Path, source: Path, declared: str | None = None) -> Path:
    """Le prefab du pack qui porte la matiere de cette source.

    **Instancier le FBX brut rend une geometrie blanche.** Les packs livrent la
    matiere sur des prefabs `<nom>_PRE.prefab`, pas sur le modele importe : le
    premier rendu du bourg avait 259 pieces de decor sans une seule matiere, et
    aucun compteur ne le disait -- le test de budget compte des triangles.

    C'est la meme faute que M-1 dans un autre endroit : une matiere declaree qui
    n'arrive pas jusqu'a l'asset. Une source sans prefab est donc refusee ici,
    et non decouverte sur une image trois lots plus tard.
    """
    if declared:
        # Le pack nomme parfois le maillage `EA_` et son prefab `EA03_` : aucune
        # regle ne devine ca, le catalogue le dit.
        if not (root / declared).is_file():
            raise VillageError(f"Prefab declare absent : {declared}")
        return Path(declared)

    pack = source
    while pack.parent != pack and pack.parent.name != "Meshes":
        pack = pack.parent
    prefabs = root / pack.parent.parent / "Prefabs"
    if prefabs.is_dir():
        found = sorted(prefabs.rglob(f"{source.stem}_PRE.prefab"))
        if found:
            return found[0].relative_to(root)
        found = sorted(prefabs.rglob(f"{source.stem}.prefab"))
        if found:
            return found[0].relative_to(root)
    raise VillageError(
        f"Source de decor sans prefab de pack : {source.as_posix()}. Le FBX brut "
        f"n'emporte pas sa matiere et rendrait en blanc.")


def place_decor(root: Path, spec: dict, census: dict, grid: list[list[float]],
                buildings: list[dict]) -> tuple[list[dict], int]:
    """Pose le decor la ou il reste de la place, et s'arrete au budget.

    `count` est un **maximum**, pas une promesse : une piece qui ne trouve ni
    place ni budget n'est pas posee, et le plan le dit. Promettre quarante-six
    arbres puis en poser trente sans le dire, c'est rendre une mesure fausse.
    """
    extent = float(spec["extent_m"])
    ceiling = int(spec["budget"]["scene_triangles_max"])
    used = sum(item["triangles"] for item in buildings)
    used += int(spec["terrain"]["cells"]) ** 2 * 2
    rng = random.Random(int(spec["seed"]) + 977)

    taken = [{"x": item["x"], "z": item["z"], "w": item["w"], "d": item["d"]}
             for item in buildings]
    placed: list[dict] = []
    decor_triangles = 0

    for kind in spec["decor"]["kinds"]:
        source = Path(kind["source"])
        absolute = root / source
        if not absolute.is_file():
            raise VillageError(f"Source de decor absente : {source}")
        stem = source.stem
        if stem not in census:
            raise VillageError(f"Source de decor non recensee : {stem}")
        cost = instance_cost(census[stem])
        radius = float(kind["radius_m"])
        digest = sha256_file(absolute)
        prefab = pack_prefab(root, source, kind.get("prefab"))
        prefab_digest = sha256_file(root / prefab)

        posed = 0
        for attempt in range(int(kind["count"]) * 60):
            if posed >= int(kind["count"]):
                break
            if used + decor_triangles + cost > ceiling:
                break
            spot = draw_spot(kind["placement"], spec, buildings, rng, radius)
            if spot is None:
                continue
            x, z = spot
            candidate = {"x": x, "z": z, "w": radius * 2.0, "d": radius * 2.0}
            if any(overlaps(candidate, other, 0.4) for other in taken):
                continue
            taken.append(candidate)
            placed.append({
                "id": f"{kind['id']}_{posed:02d}",
                "kind": kind["id"],
                "source": source.as_posix(),
                "source_sha256": digest,
                "prefab": prefab.as_posix(),
                "prefab_sha256": prefab_digest,
                "x": round(x, 3),
                "z": round(z, 3),
                "ground_y": sample_height(grid, extent, x, z),
                "rotation_y": round(rng.uniform(0.0, 360.0), 1),
                "triangles": cost,
            })
            decor_triangles += cost
            posed += 1

    return placed, decor_triangles


def verify(plan: dict, spec: dict) -> list[str]:
    """Les portes du plan, verifiees sur le plan lui-meme."""
    errors = []
    extent = float(plan["extent_m"])
    margin = float(spec["streets"]["margin_m"])

    if len(plan["buildings"]) != int(spec["building_count"]):
        errors.append("V-1_batiments_poses")
    if not plan["gates"]["V-2_toutes_variantes_posees"]:
        errors.append("V-2_toutes_variantes_posees")

    for index, first in enumerate(plan["buildings"]):
        for second in plan["buildings"][index + 1:]:
            if overlaps(first, second, margin):
                errors.append(f"V-3_recouvrement:{first['id']}|{second['id']}")
        half = extent * 0.5
        if (abs(first["x"]) + first["w"] * 0.5 > half
                or abs(first["z"]) + first["d"] * 0.5 > half):
            errors.append(f"V-4_hors_emprise:{first['id']}")

    if plan["budget"]["total"] > plan["budget"]["scene_triangles_max"]:
        errors.append("V-5_plafond_triangles")
    return sorted(set(errors))


def report(root: Path) -> int:
    plan = load(root / PLAN)
    budget = plan["budget"]
    kinds: dict[str, list[int]] = {}
    for item in plan["decor"]:
        kinds.setdefault(item["kind"], []).append(item["triangles"])
    print(f"Bourg : {len(plan['buildings'])} batiments sur "
          f"{plan['extent_m']:.0f} x {plan['extent_m']:.0f} m, terrain "
          f"{plan['terrain']['kind']}, habitants="
          f"{'oui' if plan['inhabitants'] else 'non'}\n")
    print(f"  batiments  {budget['buildings']:>7}")
    for kind, values in sorted(kinds.items(), key=lambda item: -sum(item[1])):
        print(f"  {kind:<10} {sum(values):>7}   x{len(values)}")
    print(f"  terrain    {budget['terrain']:>7}")
    print(f"  {'TOTAL':<10} {budget['total']:>7} / "
          f"{budget['scene_triangles_max']}  "
          f"({100 * budget['total'] / budget['scene_triangles_max']:.0f} %)")
    return 0


FAMILY_COLOURS = {
    "residence": "#c8a26a", "granary": "#9db06a", "warehouse": "#6f8aa6",
    "market": "#c07b52", "blacksmith": "#8b6f8f", "barn": "#a8894f",
    "chapel": "#d8d0be", "sawmill": "#7a9c86",
}


def draw_map(root: Path) -> int:
    """Une carte du plan, pour le juger avant qu'Unity ne l'ecrive.

    Une suite verte ne dit pas qu'une implantation est acceptable. Un plan se
    regarde de dessus : c'est la que se voient une rue qui ne mene nulle part,
    un batiment isole ou un decor qui s'entasse dans un coin.
    """
    from PIL import Image, ImageDraw

    plan = load(root / PLAN)
    extent = float(plan["extent_m"])
    size, margin = 1100, 24
    scale = (size - margin * 2) / extent
    canvas = Image.new("RGB", (size, size), "#12161b")
    draw = ImageDraw.Draw(canvas)

    def point(x: float, z: float) -> tuple[float, float]:
        return (margin + (x + extent * 0.5) * scale,
                margin + (extent * 0.5 - z) * scale)

    # Le relief, en aplats : une bosse s'y lit sans courbe de niveau.
    terrain = plan["terrain"]
    side = terrain["cells"] + 1
    heights = terrain["heights_row_major"]
    span = max(1e-6, max(heights) - min(heights))
    step = extent / terrain["cells"]
    for row in range(terrain["cells"]):
        for column in range(terrain["cells"]):
            value = heights[row * side + column]
            shade = int(24 + 46 * (value - min(heights)) / span)
            x = -extent * 0.5 + column * step
            z = -extent * 0.5 + row * step
            draw.rectangle([point(x, z + step), point(x + step, z)],
                           fill=(shade, shade + 4, shade))

    # Les chaussees et la place, pour juger ce que le decor doit laisser libre.
    spec = load(root / SPEC)
    half = float(spec["streets"]["half_width_m"])
    for axis in (float(value) for value in spec["streets"]["axes_m"]):
        draw.rectangle([point(axis - half, extent * 0.5),
                        point(axis + half, -extent * 0.5)], fill="#2a2721")
        draw.rectangle([point(-extent * 0.5, axis + half),
                        point(extent * 0.5, axis - half)], fill="#2a2721")
    square = float(spec["streets"].get("square_radius_m", 0.0))
    if square > 0.0:
        draw.ellipse([point(-square, square), point(square, -square)],
                     fill="#332f27")

    for piece in plan["decor"]:
        centre = point(piece["x"], piece["z"])
        radius = 3.2 if piece["kind"].startswith("arbre") else 2.0
        draw.ellipse([centre[0] - radius, centre[1] - radius,
                      centre[0] + radius, centre[1] + radius],
                     fill="#4b6b4a" if piece["kind"].startswith(("arbre", "buisson",
                                                                 "herbe"))
                     else "#6b5f4b")

    for building in plan["buildings"]:
        half_w, half_d = building["w"] * 0.5, building["d"] * 0.5
        top_left = point(building["x"] - half_w, building["z"] + half_d)
        bottom_right = point(building["x"] + half_w, building["z"] - half_d)
        function = building["family"].split("_")[1]
        draw.rectangle([top_left, bottom_right],
                       fill=FAMILY_COLOURS.get(function, "#888888"),
                       outline="#0d0f12")

    output = root / "AssetFactory/Reports/QA/village_plan_map.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, optimize=True)
    print(f"CITYLAB_VILLAGE_MAP_OK path={output.relative_to(root).as_posix()} "
          f"batiments={len(plan['buildings'])} decor={len(plan['decor'])}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--report", action="store_true",
                        help="relire le plan produit et en tirer le budget")
    parser.add_argument("--map", action="store_true",
                        help="dessiner la carte du plan, pour le juger de dessus")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()

    if args.report:
        return report(root)
    if args.map:
        return draw_map(root)

    spec = load(root / SPEC)
    plan = build_plan(root)
    errors = verify(plan, spec)
    plan["gates"]["V-3_aucun_recouvrement"] = not any(
        item.startswith("V-3") for item in errors)
    plan["gates"]["V-4_dans_l_emprise"] = not any(
        item.startswith("V-4") for item in errors)
    plan["status"] = "failed" if errors else "passed"
    plan["failures"] = errors

    (root / PLAN).write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    budget = plan["budget"]
    verdict = "FAILED" if errors else "OK"
    print(f"CITYLAB_VILLAGE_PLAN_{verdict} batiments={len(plan['buildings'])} "
          f"decor={len(plan['decor'])} triangles={budget['total']}/"
          f"{budget['scene_triangles_max']} emprise={plan['extent_m']:.0f}m "
          f"terrain={plan['terrain']['kind']} unity_launched=false"
          + ("" if not errors else " echecs=" + ",".join(errors[:6])))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
