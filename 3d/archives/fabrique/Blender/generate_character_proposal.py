"""Generate a static modular-character art proposal from the immutable GanzSe source.

The output is deliberately a review artifact, not a runtime-ready rig. It selects
compatible source parts, applies a silhouette transform and renders the role at a
fixed scale without opening Unity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--proposal", required=True)
    return parser.parse_args(argv)


def material(name: str, color: tuple[float, float, float, float], roughness: float,
             metallic: float = 0.0) -> bpy.types.Material:
    value = bpy.data.materials.new(name)
    value.diffuse_color = color
    value.use_nodes = True
    shader = value.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    return value


def replace_material(obj: bpy.types.Object, value: bpy.types.Material) -> None:
    obj.data.materials.clear()
    obj.data.materials.append(value)


def look_at(obj: bpy.types.Object, point: Vector) -> None:
    obj.rotation_euler = (point - obj.location).to_track_quat("-Z", "Y").to_euler()


def selected_names(entry: dict) -> set[str]:
    armor = entry["armor_type"]
    color = entry["color"]
    names = {
        "Base Character Mesh",
        "Eyes Type 2 Color 2",
        "Eyebrow Type 3 Color 2",
        "Nose Type 3",
        "Ears Type 1",
        f"Hair Type {entry['hair_type']} Color {entry['hair_color']}",
        f"Chest Armor Type {armor} Color {color}",
        f"Arm Armor Type {armor} Color {color}",
        f"Legs Armor Type {armor} Color {color}",
        f"Feet Armor Type {armor} Color {color}",
        f"Belt Armor Type {armor} Color {color}",
    }
    if entry["head_armor"]:
        names.add(f"Head Armor Type {entry['head_armor']} Color {color}")
    if entry["facial_hair"]:
        names.add(f"Face Hair Type {entry['facial_hair']} Color {entry['hair_color']}")
    return names


def palette(role: str) -> dict[str, bpy.types.Material]:
    colors = {
        "worker": ((0.20, 0.075, 0.025, 1), (0.34, 0.20, 0.06, 1)),
        "wealthy": ((0.34, 0.025, 0.12, 1), (0.66, 0.31, 0.04, 1)),
        "peasant": ((0.16, 0.12, 0.045, 1), (0.30, 0.22, 0.08, 1)),
        "religious": ((0.035, 0.040, 0.050, 1), (0.15, 0.12, 0.08, 1)),
        "soldier": ((0.12, 0.15, 0.16, 1), (0.38, 0.045, 0.025, 1)),
        "noble": ((0.055, 0.08, 0.30, 1), (0.62, 0.38, 0.06, 1)),
        "bourgeois": ((0.08, 0.22, 0.19, 1), (0.42, 0.22, 0.05, 1)),
        "beggar": ((0.10, 0.075, 0.045, 1), (0.18, 0.13, 0.07, 1)),
    }
    primary, accent = colors[role]
    return {
        "skin": material("skin", (0.42, 0.20, 0.11, 1), 0.72),
        "primary": material("role_primary", primary, 0.88),
        "accent": material("role_accent", accent, 0.78),
        "leather": material("worn_leather", (0.10, 0.035, 0.012, 1), 0.84),
        "hair": material("hair", (0.055, 0.025, 0.012, 1), 0.88),
        "iron": material("iron", (0.08, 0.10, 0.11, 1), 0.38, 0.78),
        "eye": material("eyes", (0.09, 0.16, 0.12, 1), 0.34),
    }


def add_box(name: str, location: tuple[float, float, float],
            dimensions: tuple[float, float, float], value: bpy.types.Material) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(value)
    modifier = obj.modifiers.new("soft_edges", "BEVEL")
    modifier.width = min(dimensions) * 0.08
    modifier.segments = 2
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    return obj


def add_cylinder(name: str, location: tuple[float, float, float], radius: float,
                 depth: float, value: bpy.types.Material,
                 rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=radius, depth=depth,
                                        location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(value)
    return obj


def add_role_marker(role: str, mats: dict[str, bpy.types.Material], height: float) -> None:
    if role == "worker":
        add_box("worker_hammer", (0.43, -0.02, height * 0.40), (0.045, 0.045, 0.28), mats["leather"])
        add_box("hammer_head", (0.43, -0.02, height * 0.48), (0.18, 0.08, 0.07), mats["iron"])
    elif role == "wealthy":
        pass
    elif role == "peasant":
        add_cylinder("peasant_basket", (0.54, -0.02, height * 0.28), 0.20, 0.30, mats["accent"])
    elif role == "religious":
        add_box("staff", (0.52, 0.0, height * 0.48), (0.045, 0.045, height * 0.82), mats["leather"])
    elif role == "soldier":
        add_box("sword_blade", (0.48, 0.03, height * 0.34), (0.045, 0.035, height * 0.40), mats["iron"])
        add_box("sword_guard", (0.48, 0.03, height * 0.50), (0.22, 0.06, 0.05), mats["accent"])
    elif role == "noble":
        pass
    elif role == "bourgeois":
        add_box("ledger", (0.43, -0.12, height * 0.45), (0.22, 0.07, 0.30), mats["leather"])
    elif role == "beggar":
        add_box("walking_stick", (0.52, 0.0, height * 0.40), (0.045, 0.045, height * 0.70), mats["leather"])
        add_box("patched_bundle", (-0.42, 0.05, height * 0.48), (0.25, 0.20, 0.28), mats["accent"])


def main() -> int:
    args = arguments()
    root = Path(args.project_root).resolve()
    catalog = json.loads((root / args.catalog).read_text(encoding="utf-8"))
    entry = next(item for item in catalog["proposals"] if item["id"] == args.proposal)
    source = root / catalog["source"]["path"]
    if hashlib.sha256(source.read_bytes()).hexdigest() != catalog["source"]["sha256"]:
        raise RuntimeError("Character source hash drift")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(source))
    keep = selected_names(entry)
    armature = next(obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE")
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    for obj in meshes:
        if obj.name not in keep:
            bpy.data.objects.remove(obj, do_unlink=True)
    kept = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    missing = keep - {obj.name for obj in kept}
    if missing:
        raise RuntimeError(f"Missing modular parts: {sorted(missing)}")

    mats = palette(entry["role"])
    for obj in kept:
        name = obj.name
        if name == "Base Character Mesh" or name.startswith(("Nose", "Ears")):
            replace_material(obj, mats["skin"])
        elif name.startswith("Eyes"):
            replace_material(obj, mats["eye"])
        elif name.startswith(("Hair", "Face Hair", "Eyebrow")):
            replace_material(obj, mats["hair"])
        elif name.startswith(("Feet", "Belt")):
            replace_material(obj, mats["leather"])
        elif entry["role"] == "soldier" or name.startswith("Head Armor"):
            replace_material(obj, mats["iron"])
        elif name.startswith("Chest"):
            replace_material(obj, mats["primary"])
        else:
            replace_material(obj, mats["accent"])

    # A relaxed presentation pose; runtime deformation remains a separate validation gate.
    armature.rotation_mode = "XYZ"
    for bone_name, angle in (("upperarm_l", math.radians(-58)), ("upperarm_r", math.radians(58))):
        bone = armature.pose.bones.get(bone_name)
        if bone:
            bone.rotation_mode = "XYZ"
            bone.rotation_euler.z = angle
    if entry["age"] == "elder":
        for bone_name, angle in (("spine_03", math.radians(6)), ("neck", math.radians(-4))):
            bone = armature.pose.bones.get(bone_name)
            if bone:
                bone.rotation_mode = "XYZ"
                bone.rotation_euler.x = angle

    corners = [obj.matrix_world @ Vector(corner) for obj in kept for corner in obj.bound_box]
    minimum = Vector((min(v.x for v in corners), min(v.y for v in corners), min(v.z for v in corners)))
    maximum = Vector((max(v.x for v in corners), max(v.y for v in corners), max(v.z for v in corners)))
    base_height = max(0.001, maximum.z - minimum.z)
    age_scale = {"child": 0.72, "adult": 1.0, "elder": 0.96}[entry["age"]]
    width_scale = {"slender": 0.86, "average": 1.0, "sturdy": 1.14, "tall": 0.96}[entry["morphology"]]
    height_scale = age_scale * (1.08 if entry["morphology"] == "tall" else 1.0)
    gender_scale = 0.93 if entry["gender"] == "female" else 1.0
    target_height = 1.75 * height_scale
    scale = 1.75 / base_height
    armature.scale = (scale * width_scale * gender_scale, scale * width_scale, scale * height_scale)
    armature.location = (-((minimum.x + maximum.x) * 0.5) * armature.scale.x,
                         -((minimum.y + maximum.y) * 0.5) * armature.scale.y,
                         -minimum.z * armature.scale.z)
    add_role_marker(entry["role"], mats, target_height)

    ground = material("ground", (0.018, 0.025, 0.026, 1), 0.94)
    bpy.ops.mesh.primitive_plane_add(size=5.5, location=(0.0, 0.0, -0.015))
    bpy.context.object.data.materials.append(ground)
    bpy.ops.object.light_add(type="AREA", location=(2.5, -3.5, 4.2))
    bpy.context.object.data.energy = 900
    bpy.context.object.data.size = 3.0
    look_at(bpy.context.object, Vector((0.0, 0.0, target_height * 0.48)))
    bpy.ops.object.light_add(type="AREA", location=(-2.2, 1.8, 2.8))
    bpy.context.object.data.energy = 520
    bpy.context.object.data.color = (0.25, 0.42, 0.72)
    bpy.context.object.data.size = 2.5
    look_at(bpy.context.object, Vector((0.0, 0.0, target_height * 0.5)))
    bpy.ops.object.camera_add(location=(2.6, -4.0, 2.25))
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 2.65
    look_at(camera, Vector((0.0, 0.0, target_height * 0.48)))
    bpy.context.scene.camera = camera
    world = bpy.context.scene.world or bpy.data.worlds.new("CityLab Character Review")
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.006, 0.010, 0.016, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.20
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 512
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.look = "AgX - Medium High Contrast"
    preview = root / "AssetFactory/Workbench/Previews/Characters" / f"{entry['id']}.png"
    preview.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(preview)
    bpy.ops.render.render(write_still=True)
    blend = root / "AssetFactory/Workbench/Characters" / f"{entry['id']}_proposal.blend"
    blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    report = {
        "schema": 1,
        "id": entry["id"],
        "status": "visual_proposal_not_rig_validated",
        "selection": entry,
        "source": catalog["source"],
        "selected_parts": sorted(keep),
        "preview": preview.relative_to(root).as_posix(),
        "blend": blend.relative_to(root).as_posix(),
        "unity_launched": False
    }
    report_path = root / "AssetFactory/Reports/Characters" / f"{entry['id']}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"CITYLAB_CHARACTER_PROPOSAL_OK id={entry['id']} parts={len(keep)} unity_launched=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
