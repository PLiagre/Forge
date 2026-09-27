"""Mesure chaque source Vendor : triangles, emprise, maillages, LOD nommes.

Le budget d'un village ne se joue pas sur ses batiments. Les vingt-quatre pesent
ensemble 50 096 triangles au LOD0 ; **un seul arbre Polytope en coute 4 494**,
plus que le plus lourd d'entre eux. Choisir un decor sans le chiffrer, c'est
choisir le budget de la scene au hasard.

    blender --background --factory-startup --python \\
        Tools/AssetFactory/Blender/audit_vendor_props.py -- --plan <plan.json>

Le plan est produit par `Tools/AssetFactory/vendor_prop_census.py`.

**Le compte `lod0` n'est pas le compte total, et c'est la mesure qui compte.**
`import_vendor_component` ne retenait que les maillages nommes `LOD0` de la
source : mesure a l'appui, `EA03_Village_HouseModule_Porch_01d` sortait une lame
plate a 763 triangles comme a 160, parce que sa geometrie utile ne portait pas
ce nom. Le recensement rend les deux comptes pour que le piege soit lisible en
donnee, et non retrouve un rendu plus tard.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import bpy

LOD_SUFFIX = re.compile(r"LOD([0-9])", re.IGNORECASE)


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    return parser.parse_args(argv)


def triangles(obj: bpy.types.Object) -> int:
    mesh = obj.data
    return sum(max(0, len(polygon.vertices) - 2) for polygon in mesh.polygons)


def measure(path: Path) -> dict:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    try:
        bpy.ops.import_scene.fbx(filepath=str(path))
    except Exception as error:  # une source illisible est une donnee, pas un arret
        return {"status": "failed", "reason": type(error).__name__}

    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not meshes:
        return {"status": "failed", "reason": "aucun_maillage"}

    total = sum(triangles(obj) for obj in meshes)
    per_lod: dict[str, int] = {}
    unnamed = 0
    for obj in meshes:
        match = LOD_SUFFIX.search(obj.name)
        if match:
            key = "lod" + match.group(1)
            per_lod[key] = per_lod.get(key, 0) + triangles(obj)
        else:
            unnamed += triangles(obj)

    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    for obj in meshes:
        for corner in obj.bound_box:
            point = obj.matrix_world @ type(obj.location)(corner)
            for axis in range(3):
                lo[axis] = min(lo[axis], point[axis])
                hi[axis] = max(hi[axis], point[axis])

    return {
        "status": "passed",
        "triangles": total,
        # Ce que l'import « LOD0 seulement » retiendrait. Quand il vaut zero, la
        # source n'a aucun maillage nomme LOD0 : l'importer par ce chemin ne
        # rendrait rien.
        "triangles_lod0": per_lod.get("lod0", 0),
        "triangles_by_lod": dict(sorted(per_lod.items())),
        "triangles_unnamed": unnamed,
        "mesh_count": len(meshes),
        "size_m": [round(hi[axis] - lo[axis], 3) for axis in range(3)],
    }


def main() -> int:
    plan = json.loads(Path(arguments().plan).read_text(encoding="utf-8"))
    root = Path(plan["project_root"]).resolve()

    entries = []
    for source in plan["sources"]:
        report = measure(root / source["path"])
        report["id"] = source["id"]
        report["pack"] = source["pack"]
        report["path"] = source["path"]
        entries.append(report)
        if len(entries) % 25 == 0:
            print(f"CITYLAB_VENDOR_CENSUS_PROGRESS {len(entries)}/{len(plan['sources'])}")

    out = root / plan["output"]
    out.parent.mkdir(parents=True, exist_ok=True)
    ok = [item for item in entries if item["status"] == "passed"]
    out.write_text(json.dumps({
        "schema": 1,
        "id": "citylab_vendor_prop_census",
        "blender": bpy.app.version_string,
        "sources": sorted(entries, key=lambda item: item["id"]),
        "summary": {
            "measured": len(ok),
            "failed": len(entries) - len(ok),
            "without_lod0_mesh": sum(1 for item in ok
                                     if item["triangles_lod0"] == 0),
        },
        "unity_launched": False,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"CITYLAB_VENDOR_CENSUS_OK mesures={len(ok)} "
          f"echecs={len(entries) - len(ok)} "
          f"sans_maillage_lod0={sum(1 for item in ok if item['triangles_lod0'] == 0)} "
          f"unity_launched=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
