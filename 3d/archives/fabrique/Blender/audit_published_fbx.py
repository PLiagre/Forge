"""Recharge chaque FBX publié dans Blender et écrit son rapport QA.

Les rapports `AssetFactory/Reports/QA/Fbx/*.json` sont lus comme preuve par
`Tools/AssetFactory/qa_factory_release.py`, mais rien dans le dépôt ne les
produisait : ils dataient d'une exécution manuelle et décrivaient des FBX qui
avaient depuis changé. Ce script est le producteur manquant.

Chaque rapport épingle maintenant le `fbx_sha256` du fichier réellement
rechargé, de sorte qu'une preuve périmée cesse d'être acceptée en silence.

Un seul processus Blender traite toute la liste : 56 lancements coûtent des
minutes, une importation coûte des secondes.

    blender --background --factory-startup --python \
        Tools/AssetFactory/Blender/audit_published_fbx.py -- --plan <plan.json>

Le plan est produit par `Tools/AssetFactory/refresh_fbx_qa.py`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import bpy

LOD_SUFFIX = re.compile(r"_LOD([0-2])$")
COLLIDER_HINTS = ("UCX_", "UBX_", "USP_", "COLLIDER", "COLLISION")


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    return parser.parse_args(argv)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit_one(asset: dict, root: Path) -> dict:
    path = root / asset["fbx"]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))

    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    lod_counts = [0, 0, 0]
    for obj in meshes:
        match = LOD_SUFFIX.search(obj.name.upper())
        if match:
            lod_counts[int(match.group(1))] += 1
    colliders = sum(
        1 for obj in bpy.context.scene.objects
        if any(hint in obj.name.upper() for hint in COLLIDER_HINTS)
    )
    uv_meshes = sum(1 for obj in meshes if len(obj.data.uv_layers) > 0)
    bones = sum(len(obj.data.bones) for obj in armatures)

    failures = []
    if not meshes:
        failures.append("no_mesh")
    if uv_meshes != len(meshes):
        failures.append("mesh_without_uv")
    if colliders:
        failures.append("embedded_collider")
    if sum(lod_counts) != len(meshes):
        failures.append("mesh_outside_the_lod_naming")

    return {
        "schema": 2,
        "id": asset["id"],
        "kind": asset["kind"],
        "fbx": asset["fbx"],
        "fbx_sha256": sha256(path),
        "status": "failed" if failures else "passed",
        "failures": failures,
        "mesh_count": len(meshes),
        "uv_mesh_count": uv_meshes,
        "lod_mesh_counts": lod_counts,
        "armature_count": len(armatures),
        "bone_count": bones,
        "embedded_colliders": colliders,
        "unity_launched": False,
    }


def main() -> int:
    plan = json.loads(Path(arguments().plan).read_text(encoding="utf-8"))
    root = Path(plan["project_root"]).resolve()
    out_dir = root / plan["report_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    failed = []
    for asset in plan["assets"]:
        report = audit_one(asset, root)
        target = out_dir / (asset["id"] + ".json")
        target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")
        if report["status"] != "passed":
            failed.append(asset["id"] + ":" + ",".join(report["failures"]))
        print("CITYLAB_FBX_AUDIT " + asset["id"] + " " + report["status"]
              + " meshes=" + str(report["mesh_count"])
              + " uv=" + str(report["uv_mesh_count"]))

    if failed:
        print("CITYLAB_FBX_AUDIT_ERROR " + " ".join(failed))
        return 1
    print("CITYLAB_FBX_AUDIT_OK assets=" + str(len(plan["assets"]))
          + " unity_launched=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
