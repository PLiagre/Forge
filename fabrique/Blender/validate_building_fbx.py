"""Valide le contrat de construction d'un FBX CityLab, v1 ou v2.

Le nom d'un nœud porte le contrat : `__P0n_PHASE_LODk` pour la version 1, qui
fige quatre phases, et `__S0n_ETAPE_LODk` pour la version 2, dont le decoupage
est une donnee. Un seul motif lit les deux, et c'est le meme motif que
l'integration Unity emploie.

Les invariants verifies ici sont ceux du contrat :
  I1  chaque etape presente porte un maillage au LOD0 ;
  I2  les rangs se suivent sans se repeter ;
  I3  l'union des etapes est le fichier entier, aucun maillage hors contrat.

Une etape peut manquer a un LOD lointain sans manquer a la fin : il n'y a pas
de menuiserie lisible a 96 px.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import bpy


V1_STAGES = ("FOUNDATION", "FRAME", "ROOF", "DETAILS")
V2_STAGES = ("GROUNDWORKS", "BASECOURSE", "FRAMING", "FLOORS",
             "CARPENTRY", "ROOFING", "JOINERY", "FINISHES")
VOCABULARIES = {"P": V1_STAGES, "S": V2_STAGES}
NAME_PATTERN = re.compile(r"__([PS])(\d{2})_([A-Z]+)_LOD([0-2])$")
MINIMUM_STAGES = {"P": 4, "S": 5}


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--fbx", required=True)
    return parser.parse_args(argv)


def triangle_count(obj: bpy.types.Object) -> int:
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def main() -> int:
    path = Path(arguments().fbx).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))

    found: dict[tuple[int, int], bpy.types.Object] = {}
    labels: dict[int, str] = {}
    markers: set[str] = set()
    errors: list[str] = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        match = NAME_PATTERN.search(obj.name.upper())
        if match is None:
            # I3 : rien dans le fichier n'echappe au contrat.
            errors.append("mesh_name_invalid:" + obj.name)
            continue
        marker, order, label, lod = (match.group(1), int(match.group(2)),
                                     match.group(3), int(match.group(4)))
        markers.add(marker)
        vocabulary = VOCABULARIES[marker]
        if not 1 <= order <= len(vocabulary) or vocabulary[order - 1] != label:
            errors.append("stage_label_invalid:" + obj.name)
        key = (order, lod)
        if key in found:
            errors.append("stage_lod_duplicate:" + obj.name)
        found[key] = obj
        labels[order] = label

    if len(markers) != 1:
        errors.append("contract_marker_ambiguous:" + ",".join(sorted(markers)) or "none")
        marker = "S"
    else:
        marker = markers.pop()

    orders = sorted(labels)
    if len(orders) < MINIMUM_STAGES[marker]:
        errors.append(f"stages_too_few:{len(orders)}<{MINIMUM_STAGES[marker]}")
    for order in orders:
        # I1 : une etape presente porte un maillage au LOD0.
        if (order, 0) not in found:
            errors.append(f"stage_lod0_missing:{marker}{order:02d}_{labels[order]}")
    if orders != sorted(set(orders)):
        errors.append("stage_order_repeated")

    if errors:
        print("CITYLAB_BUILDING_FBX_ERROR " + " ".join(errors))
        return 1
    summary = " ".join(
        f"{marker.lower()}{order:02d}_lod{lod}={triangle_count(found[(order, lod)])}"
        for order, lod in sorted(found))
    print(f"CITYLAB_BUILDING_FBX_OK file={path.name} contract={marker} "
          f"stages={len(orders)} meshes={len(found)} {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
