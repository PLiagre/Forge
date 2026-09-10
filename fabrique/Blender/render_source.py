"""Rendu neutre d'une source Vendor sans Unity.

Usage Blender :
  blender --background --factory-startup --python render_source.py -- \
    --input Assets/Publisher/model.fbx --output AssetFactory/Reports/source.png
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--resolution", type=int, default=512)
    return parser.parse_args(argv)


def look_at(obj: bpy.types.Object, point: Vector) -> None:
    obj.rotation_euler = (point - obj.location).to_track_quat("-Z", "Y").to_euler()


def material(name: str, color: tuple[float, float, float, float], roughness: float) -> bpy.types.Material:
    value = bpy.data.materials.new(name)
    value.diffuse_color = color
    value.use_nodes = True
    shader = value.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Roughness"].default_value = roughness
    return value


def main() -> int:
    args = arguments()
    source = Path(args.input).resolve()
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    if source.suffix.lower() == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(source))
    elif source.suffix.lower() in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=str(source))
    else:
        raise SystemExit(f"Format non supporte : {source.suffix}")

    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    lod0 = [obj for obj in meshes if "LOD0" in obj.name.upper()]
    kept = lod0 or meshes
    for obj in list(meshes):
        if obj not in kept:
            bpy.data.objects.remove(obj, do_unlink=True)
    if not kept:
        raise SystemExit("Aucun mesh a rendre")

    neutral = material("source_vendor_neutral", (0.24, 0.13, 0.065, 1.0), 0.72)
    corners: list[Vector] = []
    for obj in kept:
        obj.data.materials.clear()
        obj.data.materials.append(neutral)
        corners.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    minimum = Vector((min(v.x for v in corners), min(v.y for v in corners), min(v.z for v in corners)))
    maximum = Vector((max(v.x for v in corners), max(v.y for v in corners), max(v.z for v in corners)))
    center = (minimum + maximum) * 0.5
    for obj in kept:
        obj.location -= Vector((center.x, center.y, minimum.z))
    size = max(maximum.x - minimum.x, maximum.y - minimum.y, maximum.z - minimum.z)

    ground_mat = material("review_ground", (0.025, 0.035, 0.032, 1.0), 0.92)
    bpy.ops.mesh.primitive_plane_add(size=size * 4.0, location=(0.0, 0.0, -0.03))
    bpy.context.object.data.materials.append(ground_mat)

    bpy.ops.object.light_add(type="AREA", location=(size * 1.1, -size * 1.4, size * 1.8))
    key = bpy.context.object
    key.data.energy = 1100.0
    key.data.shape = "DISK"
    key.data.size = size * 1.4
    look_at(key, Vector((0.0, 0.0, size * 0.3)))
    bpy.ops.object.light_add(type="AREA", location=(-size, size * 0.8, size))
    fill = bpy.context.object
    fill.data.energy = 650.0
    fill.data.color = (0.28, 0.42, 0.65)
    fill.data.size = size
    look_at(fill, Vector((0.0, 0.0, size * 0.25)))

    bpy.ops.object.camera_add(location=(size * 1.25, -size * 1.45, size * 1.05))
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = size * 1.55
    look_at(camera, Vector((0.0, 0.0, size * 0.32)))
    bpy.context.scene.camera = camera

    world = bpy.context.scene.world or bpy.data.worlds.new("CityLab Review World")
    bpy.context.scene.world = world
    world.color = (0.008, 0.012, 0.02)
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.008, 0.012, 0.02, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.18

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = args.resolution
    scene.render.resolution_y = args.resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(output)
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.render.image_settings.color_mode = "RGBA"
    bpy.ops.render.render(write_still=True)
    print(f"CITYLAB_SOURCE_RENDER_OK input={source.name} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
