"""Cross-category FBX QA for CityLab Factory outputs, without Unity."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import bpy


BUILDING_NAME = re.compile(
    r"^building_[a-z0-9_]+__P0[1-4]_(?:FOUNDATION|FRAME|ROOF|DETAILS)_LOD[0-2]$"
)


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--fbx", required=True)
    parser.add_argument("--kind", choices=("building", "character"), required=True)
    parser.add_argument("--report", required=True)
    return parser.parse_args(argv)


def fail(message: str) -> None:
    raise RuntimeError("CITYLAB_FACTORY_FBX_QA_INVALID " + message)


def main() -> int:
    args = arguments()
    root = Path(args.project_root).resolve()
    fbx = root / args.fbx
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(fbx), use_anim=False)
    objects = list(bpy.context.scene.objects)
    meshes = [obj for obj in objects if obj.type == "MESH"]
    if not meshes:
        fail("no_meshes")
    if any("collider" in obj.name.lower() or obj.name.lower().startswith(("ucx_", "ubx_", "usp_"))
           for obj in objects):
        fail("embedded_collider")

    uv_meshes = 0
    for obj in meshes:
        if not all(math.isfinite(value) for vertex in obj.data.vertices for value in vertex.co):
            fail(f"non_finite={obj.name}")
        if not obj.data.uv_layers:
            fail(f"missing_uv={obj.name}")
        active = obj.data.uv_layers.active
        if active is None or len(active.data) != len(obj.data.loops):
            fail(f"invalid_uv={obj.name}")
        if not all(math.isfinite(value) for loop in active.data for value in loop.uv):
            fail(f"non_finite_uv={obj.name}")
        uv_meshes += 1

    lod_counts = []
    if args.kind == "building":
        if len(meshes) != 12 or any(not BUILDING_NAME.fullmatch(obj.name) for obj in meshes):
            fail(f"building_mesh_contract={len(meshes)}")
        for level in range(3):
            lod_counts.append(sum(1 for obj in meshes if obj.name.endswith(f"_LOD{level}")))
        if lod_counts != [4, 4, 4]:
            fail(f"building_lods={lod_counts}")
        armature_count = 0
        bone_count = 0
    else:
        if any(not re.search(r"_LOD[0-2]$", obj.name) for obj in meshes):
            fail("character_mesh_name")
        for level in range(3):
            lod_counts.append(sum(1 for obj in meshes if obj.name.endswith(f"_LOD{level}")))
        if not lod_counts[0] or len(set(lod_counts)) != 1:
            fail(f"character_lods={lod_counts}")
        armatures = [obj for obj in objects if obj.type == "ARMATURE"]
        if len(armatures) != 1 or len(armatures[0].data.bones) != 52:
            fail(f"character_rig={len(armatures)}")
        armature_count = 1
        bone_count = 52

    payload = {
        "schema": 1,
        "id": fbx.stem,
        "kind": args.kind,
        "fbx": Path(args.fbx).as_posix(),
        "status": "passed",
        "mesh_count": len(meshes),
        "uv_mesh_count": uv_meshes,
        "lod_mesh_counts": lod_counts,
        "armature_count": armature_count,
        "bone_count": bone_count,
        "embedded_colliders": 0,
        "unity_launched": False,
    }
    report = root / args.report
    report.parent.mkdir(parents=True, exist_ok=True)
    temporary = report.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(report)
    print(
        "CITYLAB_FACTORY_FBX_QA_OK "
        f"id={fbx.stem} kind={args.kind} meshes={len(meshes)} uv={uv_meshes} "
        f"lods={lod_counts} colliders=0 unity_launched=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
