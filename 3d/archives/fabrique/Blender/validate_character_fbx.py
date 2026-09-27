"""Validate a generated CityLab character FBX in Blender, without Unity."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--fbx", required=True)
    parser.add_argument("--report", required=True)
    return parser.parse_args(argv)


def triangles(obj: bpy.types.Object) -> int:
    return sum(len(polygon.vertices) - 2 for polygon in obj.data.polygons)


def fail(message: str) -> None:
    raise RuntimeError("CITYLAB_CHARACTER_FBX_INVALID " + message)


def main() -> int:
    args = arguments()
    root = Path(args.project_root).resolve()
    report = json.loads((root / args.report).read_text(encoding="utf-8"))
    fbx = root / args.fbx
    if not fbx.is_file():
        fail(f"missing={fbx}")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(fbx), use_anim=False)
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        fail(f"armatures={len(armatures)}")
    armature = armatures[0]
    if len(armature.data.bones) != report["bone_count"] or report["bone_count"] != 52:
        fail(f"bones={len(armature.data.bones)} expected=52")

    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    lods: list[list[bpy.types.Object]] = []
    for level in range(3):
        suffix = f"_LOD{level}"
        selected = sorted((obj for obj in meshes if obj.name.endswith(suffix)), key=lambda obj: obj.name)
        if len(selected) != report["lod_mesh_counts"][level] or not selected:
            fail(f"lod{level}_meshes={len(selected)} expected={report['lod_mesh_counts'][level]}")
        actual_triangles = sum(triangles(obj) for obj in selected)
        # FBX may collapse a degenerate decimation edge on import. Keep a tight
        # per-part tolerance while still enforcing the production budget below.
        if abs(actual_triangles - report["lod_triangles"][level]) > max(2, len(selected)):
            fail(f"lod{level}_triangles={actual_triangles} expected={report['lod_triangles'][level]}")
        lods.append(selected)

    if report["kind"] == "body":
        budgets = (12000, 6500, 3000)
    else:
        budgets = (18000, 9500, 4200)
    if any(value > budget for value, budget in zip(report["lod_triangles"], budgets)):
        fail(f"triangle_budget={report['lod_triangles']} max={budgets}")

    weighted_vertices = total_vertices = 0
    for obj in meshes:
        if not all(math.isfinite(value) for vertex in obj.data.vertices for value in vertex.co):
            fail(f"non_finite_vertices={obj.name}")
        groups = {group.index for group in obj.vertex_groups}
        for vertex in obj.data.vertices:
            total_vertices += 1
            if any(link.group in groups and link.weight > 0.0001 for link in vertex.groups):
                weighted_vertices += 1
    coverage = weighted_vertices / max(1, total_vertices)
    if coverage < 0.98:
        fail(f"skin_weight_coverage={coverage:.4f}")

    # Lightweight deformation smoke test: the exported skeleton must accept a pose
    # and every evaluated LOD0 bound must remain finite and non-degenerate.
    for bone_name, angle in (("upperarm_l", -0.35), ("upperarm_r", 0.35)):
        bone = armature.pose.bones.get(bone_name)
        if bone is None:
            fail(f"missing_pose_bone={bone_name}")
        bone.rotation_mode = "XYZ"
        bone.rotation_euler.z = angle
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in lods[0]:
        evaluated = obj.evaluated_get(depsgraph)
        points = [evaluated.matrix_world @ vertex.co for vertex in evaluated.data.vertices]
        if points:
            extent = max(point.length for point in points)
            if not math.isfinite(extent) or extent < 0.01:
                fail(f"pose_bounds={obj.name}")

    print(
        "CITYLAB_CHARACTER_FBX_OK "
        f"id={report['id']} bones=52 lods={report['lod_triangles']} "
        f"weighted={coverage:.4f} unity_launched=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
