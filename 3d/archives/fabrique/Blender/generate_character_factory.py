"""Generate production-oriented rigged CityLab character FBXs without Unity."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--kind", choices=("body", "role"), required=True)
    parser.add_argument("--base")
    parser.add_argument("--morphology")
    parser.add_argument("--role")
    parser.add_argument("--skip-preview", action="store_true")
    return parser.parse_args(argv)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def make_material(name: str, color: tuple[float, float, float, float], roughness: float,
                  metallic: float = 0.0) -> bpy.types.Material:
    value = bpy.data.materials.new(name)
    value.diffuse_color = color
    value.use_nodes = True
    shader = value.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    return value


def palette(role: str | None, hair_color: int) -> dict[str, bpy.types.Material]:
    role_colors = {
        "worker": ((0.20, 0.07, 0.02, 1), (0.44, 0.25, 0.06, 1)),
        "wealthy": ((0.34, 0.025, 0.12, 1), (0.72, 0.42, 0.06, 1)),
        "peasant": ((0.15, 0.12, 0.045, 1), (0.34, 0.24, 0.08, 1)),
        "religious": ((0.025, 0.030, 0.040, 1), (0.17, 0.12, 0.07, 1)),
        "soldier": ((0.10, 0.13, 0.15, 1), (0.42, 0.045, 0.025, 1)),
        "noble": ((0.045, 0.07, 0.30, 1), (0.68, 0.40, 0.06, 1)),
        "bourgeois": ((0.06, 0.21, 0.18, 1), (0.46, 0.23, 0.05, 1)),
        "beggar": ((0.085, 0.060, 0.035, 1), (0.19, 0.13, 0.065, 1)),
        None: ((0.20, 0.11, 0.055, 1), (0.34, 0.20, 0.10, 1)),
    }
    primary, accent = role_colors[role]
    hair_colors = {
        1: (0.020, 0.012, 0.009, 1),
        2: (0.055, 0.025, 0.012, 1),
        3: (0.18, 0.055, 0.018, 1),
        4: (0.42, 0.25, 0.08, 1),
        5: (0.42, 0.44, 0.43, 1),
    }
    return {
        "skin": make_material("skin", (0.43, 0.21, 0.12, 1), 0.72),
        "eyes": make_material("eyes", (0.08, 0.18, 0.14, 1), 0.30),
        "hair": make_material("hair", hair_colors.get(hair_color, hair_colors[2]), 0.88),
        "primary": make_material("cloth_primary", primary, 0.90),
        "accent": make_material("cloth_accent", accent, 0.82),
        "leather": make_material("leather", (0.10, 0.032, 0.010, 1), 0.85),
        "iron": make_material("iron", (0.07, 0.085, 0.09, 1), 0.35, 0.82),
        "wood": make_material("wood", (0.22, 0.075, 0.018, 1), 0.88),
    }


def role_mesh_names(role: dict, face_parts: list[str]) -> set[str]:
    armor, color = role["armor_type"], role["color"]
    names = set(face_parts)
    names.update({
        f"Hair Type {role['hair_type']} Color {role['hair_color']}",
        f"Chest Armor Type {armor} Color {color}",
        f"Arm Armor Type {armor} Color {color}",
        f"Legs Armor Type {armor} Color {color}",
        f"Feet Armor Type {armor} Color {color}",
        f"Belt Armor Type {armor} Color {color}",
    })
    if role["head_armor"]:
        names.add(f"Head Armor Type {role['head_armor']} Color {color}")
    if role["facial_hair"]:
        names.add(f"Face Hair Type {role['facial_hair']} Color {role['hair_color']}")
    return names


def assign_materials(meshes: list[bpy.types.Object], mats: dict[str, bpy.types.Material],
                     role: str | None) -> None:
    for obj in meshes:
        obj.data = obj.data.copy()
        obj.data.materials.clear()
        name = obj.name
        if name == "Base Character Mesh" or name.startswith(("Nose", "Ears")):
            value = mats["skin"]
        elif name.startswith("Eyes"):
            value = mats["eyes"]
        elif name.startswith(("Hair", "Face Hair", "Eyebrow")):
            value = mats["hair"]
        elif name.startswith(("Feet", "Belt")):
            value = mats["leather"]
        elif role == "soldier" or name.startswith("Head Armor"):
            value = mats["iron"]
        elif name.startswith("Chest"):
            value = mats["primary"]
        else:
            value = mats["accent"]
        obj.data.materials.append(value)


def base_bounds(meshes: list[bpy.types.Object]) -> tuple[float, float]:
    body = next(obj for obj in meshes if obj.name == "Base Character Mesh")
    values = [(body.matrix_world @ vertex.co).z for vertex in body.data.vertices]
    return min(values), max(values)


def warp_meshes(meshes: list[bpy.types.Object], z_min: float, z_max: float,
                base: dict, morphology: dict) -> None:
    height = max(0.001, z_max - z_min)
    for obj in meshes:
        to_world = obj.matrix_world.copy()
        to_local = to_world.inverted()
        for vertex in obj.data.vertices:
            world = to_world @ vertex.co
            u = max(0.0, min(1.0, (world.z - z_min) / height))
            shoulder = math.exp(-((u - 0.72) / 0.14) ** 2)
            hip = math.exp(-((u - 0.46) / 0.15) ** 2)
            head = max(0.0, min(1.0, (u - 0.80) / 0.15))
            waist = math.exp(-((u - 0.57) / 0.10) ** 2)
            gender_waist = -0.07 * waist if base["gender"] == "female" else 0.0
            # Morphology belongs to the torso and limbs. Fading it out over the
            # head preserves the authored face, eyes and hair alignment.
            morphology_x = 1.0 + (morphology["width"] - 1.0) * (1.0 - head)
            morphology_y = 1.0 + (morphology["depth"] - 1.0) * (1.0 - head)
            x_factor = morphology_x * (
                1.0 + (base["shoulders"] - 1.0) * shoulder
                + (base["hips"] - 1.0) * hip
                + (base["head"] - 1.0) * head * 0.50
                + gender_waist
            )
            y_factor = morphology_y * (
                1.0 + (base["hips"] - 1.0) * hip * 0.45
                + (base["head"] - 1.0) * head * 0.15
            )
            world.x *= x_factor
            world.y *= y_factor
            vertex.co = to_local @ world


def weighted_mesh(name: str, vertices: list[tuple[float, float, float]],
                  faces: list[tuple[int, ...]], material: bpy.types.Material,
                  armature: bpy.types.Object,
                  weights: dict[str, list[tuple[int, float]]]) -> bpy.types.Object:
    # Procedural garment dimensions are authored in CityLab world axes (Z up),
    # while the source FBX armature is imported with a 90-degree X rotation.
    # Convert once into armature-local space so skinning and source parts agree.
    world_to_armature = armature.matrix_world.inverted()
    local_vertices = [tuple(world_to_armature @ Vector(vertex)) for vertex in vertices]
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(local_vertices, [], faces)
    mesh.update()
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for polygon in mesh.polygons:
        axis = max(range(3), key=lambda index: abs(polygon.normal[index]))
        for loop_index in polygon.loop_indices:
            vertex = mesh.vertices[mesh.loops[loop_index].vertex_index].co
            if axis == 0:
                uv = (vertex.y, vertex.z)
            elif axis == 1:
                uv = (vertex.x, vertex.z)
            else:
                uv = (vertex.x, vertex.y)
            uv_layer.data[loop_index].uv = uv
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = armature
    modifier = obj.modifiers.new("Armature", "ARMATURE")
    modifier.object = armature
    for bone_name, entries in weights.items():
        group = obj.vertex_groups.new(name=bone_name)
        for index, value in entries:
            group.add([index], value, "REPLACE")
    return obj


def skirt(name: str, z_min: float, z_max: float, top_x: float, bottom_x: float,
          top_y: float, bottom_y: float, material: bpy.types.Material,
          armature: bpy.types.Object, ragged: bool = False) -> bpy.types.Object:
    segments = 12
    vertices: list[tuple[float, float, float]] = []
    for ring, (z, rx, ry) in enumerate(((z_max, top_x, top_y), (z_min, bottom_x, bottom_y))):
        for index in range(segments):
            angle = 2.0 * math.pi * index / segments
            drop = (0.035 * (index % 3)) if ragged and ring == 1 else 0.0
            vertices.append((math.cos(angle) * rx, math.sin(angle) * ry, z - drop))
    faces = []
    for index in range(segments):
        nxt = (index + 1) % segments
        faces.append((index, nxt, segments + nxt, segments + index))
    weights: dict[str, list[tuple[int, float]]] = {"spine_01": [], "upperleg_l": [], "upperleg_r": []}
    for index, vertex in enumerate(vertices):
        if index < segments:
            weights["spine_01"].append((index, 1.0))
        elif vertex[0] < 0:
            weights["upperleg_l"].append((index, 0.82))
            weights["spine_01"].append((index, 0.18))
        else:
            weights["upperleg_r"].append((index, 0.82))
            weights["spine_01"].append((index, 0.18))
    return weighted_mesh(name, vertices, faces, material, armature, weights)


def panel(name: str, center_y: float, z_bottom: float, z_top: float, half_width: float,
          material: bpy.types.Material, armature: bpy.types.Object,
          ragged: bool = False) -> bpy.types.Object:
    bottom_left = z_bottom - (0.06 if ragged else 0.0)
    vertices = [(-half_width, center_y, z_top), (half_width, center_y, z_top),
                (half_width * 0.92, center_y, z_bottom), (-half_width * 0.82, center_y, bottom_left)]
    weights = {
        "spine_02": [(0, 1.0), (1, 1.0)],
        "upperleg_r": [(2, 0.78)], "upperleg_l": [(3, 0.78)],
        "spine_01": [(2, 0.22), (3, 0.22)]
    }
    return weighted_mesh(name, vertices, [(0, 1, 2, 3)], material, armature, weights)


def cape(name: str, z_bottom: float, z_top: float, width: float,
         material: bpy.types.Material, armature: bpy.types.Object) -> bpy.types.Object:
    y = 0.18
    mid_z = z_top * 0.62 + z_bottom * 0.38
    vertices = [(-width * 0.55, y, z_top), (width * 0.55, y, z_top),
                (-width, y + 0.025, mid_z), (width, y + 0.025, mid_z),
                (-width * 0.78, y + 0.07, z_bottom), (width * 0.78, y + 0.07, z_bottom)]
    weights = {"shoulder_l": [(0, 0.75)], "shoulder_r": [(1, 0.75)],
               "spine_03": [(0, 0.25), (1, 0.25), (2, 1.0), (3, 1.0),
                            (4, 1.0), (5, 1.0)]}
    return weighted_mesh(name, vertices, [(0, 1, 3, 2), (2, 3, 5, 4)], material, armature, weights)


def weighted_box(name: str, center: Vector, dimensions: tuple[float, float, float],
                 material: bpy.types.Material, armature: bpy.types.Object,
                 bone_name: str) -> bpy.types.Object:
    x, y, z = (value * 0.5 for value in dimensions)
    vertices = [(center.x + sx * x, center.y + sy * y, center.z + sz * z)
                for sx, sy, sz in ((-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                                   (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1))]
    faces = [(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(4,0,3,7)]
    return weighted_mesh(name, vertices, faces, material, armature,
                         {bone_name: [(index, 1.0) for index in range(8)]})


def add_special_garment(role: dict, z_min: float, z_max: float,
                        mats: dict[str, bpy.types.Material], armature: bpy.types.Object) -> list[bpy.types.Object]:
    height = z_max - z_min
    waist = z_min + height * 0.50
    result: list[bpy.types.Object] = []
    garment = role["special_garment"]
    if garment in {"long_robe", "ragged_robe", "civilian_overdress"}:
        bottom_ratio = 0.13 if garment != "civilian_overdress" else 0.24
        result.append(skirt(garment, z_min + height * bottom_ratio, waist + height * 0.10,
                            0.30, 0.45 if garment != "ragged_robe" else 0.40,
                            0.22, 0.31, mats["primary"], armature,
                            ragged=garment == "ragged_robe"))
    if garment == "apron":
        result.append(panel(garment, -0.22, z_min + height * 0.43,
                            z_min + height * 0.59, 0.145,
                            mats["leather"], armature))
    if garment == "mantle":
        result.append(cape(garment, z_min + height * 0.50, z_min + height * 0.82,
                           0.42, mats["primary"], armature))

    hand = armature.data.bones.get("hand_r")
    spine = armature.data.bones.get("spine_01")
    if hand and role["id"] in {"worker", "religious", "soldier", "peasant", "bourgeois"}:
        center = armature.matrix_world @ hand.tail_local
        if role["id"] == "worker":
            result.append(weighted_box("hammer_handle", center + Vector((0, 0, -0.16)),
                                       (0.045, 0.045, 0.36), mats["wood"], armature, "hand_r"))
            result.append(weighted_box("hammer_head", center + Vector((0, 0, 0.02)),
                                       (0.22, 0.09, 0.08), mats["iron"], armature, "hand_r"))
        elif role["id"] == "religious":
            result.append(weighted_box("staff", center + Vector((0, 0, -0.42)),
                                       (0.045, 0.045, 1.25), mats["wood"], armature, "hand_r"))
        elif role["id"] == "soldier":
            result.append(weighted_box("sword", center + Vector((0, 0, -0.34)),
                                       (0.055, 0.035, 0.72), mats["iron"], armature, "hand_r"))
        elif role["id"] == "peasant":
            result.append(weighted_box("basket", center + Vector((0, 0, -0.18)),
                                       (0.34, 0.28, 0.30), mats["wood"], armature, "hand_r"))
        elif role["id"] == "bourgeois":
            result.append(weighted_box("ledger", center + Vector((0, 0, -0.04)),
                                       (0.24, 0.08, 0.34), mats["leather"], armature, "hand_r"))
    if spine and role["id"] == "beggar":
        result.append(weighted_box("bundle", (armature.matrix_world @ spine.head_local) + Vector((-0.32, 0.08, 0.12)),
                                   (0.30, 0.22, 0.34), mats["accent"], armature, "spine_01"))
    return result


def join_meshes(meshes: list[bpy.types.Object], armature: bpy.types.Object) -> bpy.types.Object:
    bpy.ops.object.select_all(action="DESELECT")
    active = next(obj for obj in meshes if obj.name == "Base Character Mesh")
    for obj in meshes:
        obj.hide_set(False)
        obj.hide_render = False
        obj.select_set(True)
    bpy.context.view_layer.objects.active = active
    bpy.ops.object.join()
    active.name = "Character_LOD0"
    active.parent = armature
    modifiers = [modifier for modifier in active.modifiers if modifier.type == "ARMATURE"]
    if not modifiers:
        modifier = active.modifiers.new("Armature", "ARMATURE")
        modifier.object = armature
    else:
        modifiers[0].object = armature
        for extra in modifiers[1:]:
            active.modifiers.remove(extra)
    return active


def triangle_count(obj: bpy.types.Object) -> int:
    return sum(len(polygon.vertices) - 2 for polygon in obj.data.polygons)


def lod_copy(source: bpy.types.Object, name: str, ratio: float) -> bpy.types.Object:
    obj = source.copy()
    obj.data = source.data.copy()
    obj.name = name
    bpy.context.collection.objects.link(obj)
    modifier = obj.modifiers.new("LOD Decimate", "DECIMATE")
    modifier.ratio = ratio
    modifier.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_move_to_index(modifier=modifier.name, index=0)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.select_set(False)
    return obj


def prepare_lod_levels(meshes: list[bpy.types.Object], armature: bpy.types.Object,
                       ratios: list[float]) -> list[list[bpy.types.Object]]:
    levels: list[list[bpy.types.Object]] = [[], [], []]
    for index, obj in enumerate(sorted(meshes, key=lambda item: item.name)):
        stem = "".join(character if character.isalnum() else "_" for character in obj.name).strip("_")
        stem = f"Part_{index:02d}_{stem}"
        obj.name = stem + "_LOD0"
        obj.parent = armature
        modifiers = [modifier for modifier in obj.modifiers if modifier.type == "ARMATURE"]
        if not modifiers:
            modifier = obj.modifiers.new("Armature", "ARMATURE")
            modifier.object = armature
        else:
            modifiers[0].object = armature
            for extra in modifiers[1:]:
                obj.modifiers.remove(extra)
        levels[0].append(obj)
        levels[1].append(lod_copy(obj, stem + "_LOD1", ratios[1]))
        levels[2].append(lod_copy(obj, stem + "_LOD2", ratios[2]))
    return levels


def canonical_hash(objects: list[bpy.types.Object], armature: bpy.types.Object) -> str:
    digest = hashlib.sha256()
    for bone in sorted(armature.data.bones, key=lambda item: item.name):
        digest.update(bone.name.encode("utf-8"))
    for obj in objects:
        digest.update(obj.name.encode("utf-8"))
        for vertex in obj.data.vertices:
            digest.update(struct.pack("<3f", *vertex.co))
        for polygon in obj.data.polygons:
            digest.update(struct.pack("<I", len(polygon.vertices)))
            digest.update(struct.pack("<" + "I" * len(polygon.vertices), *polygon.vertices))
        for layer in sorted(obj.data.uv_layers, key=lambda item: item.name):
            digest.update(layer.name.encode("utf-8"))
            for loop in layer.data:
                digest.update(struct.pack("<2f", *loop.uv))
    return digest.hexdigest()


def export_fbx(path: Path, scale_root: bpy.types.Object, armature: bpy.types.Object,
               lods: list[bpy.types.Object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    scale_root.select_set(True)
    armature.select_set(True)
    for obj in lods:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, add_leaf_bones=False,
                             bake_anim=False, axis_forward="-Z", axis_up="Y",
                             mesh_smooth_type="FACE")


def look_at(obj: bpy.types.Object, point: Vector) -> None:
    obj.rotation_euler = (point - obj.location).to_track_quat("-Z", "Y").to_euler()


def render_preview(path: Path, armature: bpy.types.Object, levels: list[list[bpy.types.Object]],
                   mats: dict[str, bpy.types.Material], target_height: float) -> None:
    for obj in levels[1] + levels[2]:
        obj.hide_render = True
    for bone_name, angle in (("upperarm_l", math.radians(-58)), ("upperarm_r", math.radians(58))):
        bone = armature.pose.bones.get(bone_name)
        if bone:
            bone.rotation_mode = "XYZ"
            bone.rotation_euler.z = angle
    bpy.ops.mesh.primitive_plane_add(size=5.5, location=(0, 0, -0.015))
    ground = bpy.context.object
    ground.data.materials.append(make_material("review_ground", (0.018, 0.025, 0.026, 1), 0.94))
    bpy.ops.object.light_add(type="AREA", location=(2.5, -3.5, 4.2))
    bpy.context.object.data.energy = 950
    bpy.context.object.data.size = 3.0
    look_at(bpy.context.object, Vector((0, 0, target_height * 0.48)))
    bpy.ops.object.light_add(type="AREA", location=(-2.2, 1.8, 2.8))
    bpy.context.object.data.energy = 520
    bpy.context.object.data.color = (0.25, 0.42, 0.72)
    bpy.context.object.data.size = 2.5
    look_at(bpy.context.object, Vector((0, 0, target_height * 0.48)))
    bpy.ops.object.camera_add(location=(2.6, -4.0, max(1.35, target_height * 1.15)))
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 2.65
    look_at(camera, Vector((0, 0, target_height * 0.46)))
    bpy.context.scene.camera = camera
    world = bpy.context.scene.world or bpy.data.worlds.new("Character Review")
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
    path.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def main() -> int:
    args = arguments()
    root = Path(args.project_root).resolve()
    catalog_path = root / args.catalog
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    source = root / catalog["source"]["path"]
    if sha256(source) != catalog["source"]["sha256"]:
        raise RuntimeError("Character source hash drift")
    bases = {entry["id"]: entry for entry in catalog["body_bases"]}
    morphologies = {entry["id"]: entry for entry in catalog["morphologies"]}
    roles = {entry["id"]: entry for entry in catalog["role_capsules"]}
    if args.kind == "body":
        if args.base not in bases or args.morphology not in morphologies:
            raise ValueError("body generation requires a valid --base and --morphology")
        base, morphology, role = bases[args.base], morphologies[args.morphology], None
        asset_id = f"body_{base['id']}_{morphology['id']}"
        selected = set(catalog["face_parts"]) | {
            f"Hair Type {base['hair_type']} Color {base['hair_color']}"
        }
    else:
        if args.role not in roles:
            raise ValueError("role generation requires a valid --role")
        role = roles[args.role]
        base, morphology = bases[role["base"]], morphologies[role["morphology"]]
        asset_id = f"role_{role['id']}_{base['id']}_{morphology['id']}"
        selected = role_mesh_names(role, catalog["face_parts"])

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(source))
    armature = next(obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE")
    if armature.name != catalog["rig"]["name"]:
        raise RuntimeError(f"Unexpected armature {armature.name}")
    for obj in list(bpy.context.scene.objects):
        if obj.type == "MESH" and obj.name not in selected:
            bpy.data.objects.remove(obj, do_unlink=True)
        elif obj.type in {"CAMERA", "LIGHT"}:
            bpy.data.objects.remove(obj, do_unlink=True)
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    missing = selected - {obj.name for obj in meshes}
    if missing:
        raise RuntimeError(f"Missing character parts: {sorted(missing)}")
    mats = palette(role["id"] if role else None,
                   role["hair_color"] if role else base["hair_color"])
    assign_materials(meshes, mats, role["id"] if role else None)
    z_min, z_max = base_bounds(meshes)
    if role:
        meshes.extend(add_special_garment(role, z_min, z_max, mats, armature))
    height_scale = base["height"] * morphology["height"]
    warp_meshes(meshes, z_min, z_max, base, morphology)
    levels = prepare_lod_levels(meshes, armature, catalog["lod"]["ratios"])
    lods = levels[0] + levels[1] + levels[2]
    triangles = [sum(triangle_count(obj) for obj in level) for level in levels]
    budget = catalog["lod"]["role_triangles_max" if role else "body_triangles_max"]
    if any(value > maximum for value, maximum in zip(triangles, budget)):
        raise RuntimeError(f"LOD budget exceeded {triangles} > {budget}")
    if len(armature.data.bones) != catalog["rig"]["expected_deform_bones"]:
        raise RuntimeError(f"Expected {catalog['rig']['expected_deform_bones']} bones, got {len(armature.data.bones)}")
    scale_root = bpy.data.objects.new("CityLab_Character_Scale_Root", None)
    bpy.context.collection.objects.link(scale_root)
    armature.parent = scale_root
    # Keep the skinned hierarchy uniformly scaled. A Z-only stature scale skews
    # the facial attachments when Blender evaluates the armature modifiers.
    scale_root.scale = (height_scale, height_scale, height_scale)
    canonical = hashlib.sha256((canonical_hash(lods, armature) + f"|height={height_scale:.6f}")
                               .encode("utf-8")).hexdigest()
    workbench = root / catalog["outputs"]["workbench"]
    reports = root / catalog["outputs"]["reports"]
    fbx = workbench / ("Bodies" if args.kind == "body" else "Roles") / f"{asset_id}.fbx"
    export_fbx(fbx, scale_root, armature, lods)
    preview = workbench / "Previews" / f"{asset_id}.png"
    if not args.skip_preview:
        render_preview(preview, armature, levels, mats, 1.75 * height_scale)
    report = {
        "schema": 1, "id": asset_id, "kind": args.kind,
        "status": "generated_rigged_pending_unity_humanoid_validation",
        "source": catalog["source"], "base": base, "morphology": morphology,
        "role": role, "bone_count": len(armature.data.bones),
        "lod_triangles": triangles, "lod_mesh_counts": [len(level) for level in levels],
        "canonical_sha256": canonical,
        "fbx_sha256": sha256(fbx), "fbx": fbx.relative_to(root).as_posix(),
        "preview": preview.relative_to(root).as_posix() if preview.is_file() else None,
        "unity_launched": False
    }
    reports.mkdir(parents=True, exist_ok=True)
    report_path = reports / f"{asset_id}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"CITYLAB_CHARACTER_GENERATED id={asset_id} kind={args.kind} bones={len(armature.data.bones)} "
          f"triangles={triangles} hash={canonical} unity_launched=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
