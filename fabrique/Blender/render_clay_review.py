"""Rend un `.blend` de revue en **argile** : Workbench, cavite, contour.

Les rendus de la Factory sont nocturnes et lites, et ils cachent la geometrie.
Les cinq defauts de conception nommes jusqu'ici -- la porte partie a 3,61 m,
l'escalier devenu remblai, les accessoires flottants, la souche sans solin, le
module Vendor en lame plate -- ont **tous** ete trouves en argile, aucun sur un
rendu lite.

Le depot n'avait pas de producteur pour ces images : elles etaient faites a la
main, donc pas refaites. C'est celui-la.

    blender --background --factory-startup --python \
        Tools/AssetFactory/Blender/render_clay_review.py -- --plan <plan.json>

Le plan est produit par `Tools/AssetFactory/clay_review.py`.

Une matiere unique remplace toutes les autres : l'argile ne juge pas la couleur,
elle juge la forme. La cavite creuse les angles rentrants et le contour ferme la
silhouette -- c'est ce couple qui rend une planche flottante visible.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy

# Trois vues, et elles ne se choisissent pas au hasard. La vue RTS est celle du
# jeu. Le profil montre ce qui flotte : un accessoire cale sur un Z absolu se
# detache du terrain des qu'on regarde a l'horizontale. Le dessus montre
# l'emprise et les volumes rapportes qui debordent.
VIEWS = {
    "rts": (1.0, -1.0, 0.62),
    "profil": (1.0, -0.06, 0.10),
    "dessus": (0.05, -0.35, 1.0),
}


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    return parser.parse_args(argv)


def clay_material() -> bpy.types.Material:
    material = bpy.data.materials.new("clay")
    material.use_nodes = False
    material.diffuse_color = (0.62, 0.60, 0.57, 1.0)
    material.roughness = 0.9
    return material


def visible_meshes() -> list[bpy.types.Object]:
    """Ce que la revue montre, et rien d'autre.

    Un objet masque ne se selectionne pas dans Blender : la revue lit donc la
    visibilite telle que le generateur l'a laissee, elle ne la rejoue pas.
    """
    return [obj for obj in bpy.context.scene.objects
            if obj.type == "MESH" and obj.visible_get()]


def frame(objects: list[bpy.types.Object]) -> tuple[tuple[float, float, float], float]:
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    for obj in objects:
        for corner in obj.bound_box:
            point = obj.matrix_world @ type(obj.location)(corner)
            for axis in range(3):
                lo[axis] = min(lo[axis], point[axis])
                hi[axis] = max(hi[axis], point[axis])
    centre = tuple((lo[axis] + hi[axis]) * 0.5 for axis in range(3))
    span = max(hi[axis] - lo[axis] for axis in range(3))
    return centre, span * 1.18


def setup_clay(scene: bpy.types.Scene) -> None:
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "SINGLE"
    shading.single_color = (0.62, 0.60, 0.57)
    shading.show_cavity = True
    shading.cavity_type = "BOTH"
    shading.curvature_ridge_factor = 1.6
    shading.curvature_valley_factor = 1.6
    shading.show_object_outline = True
    shading.object_outline_color = (0.05, 0.05, 0.06)
    shading.show_shadows = True
    scene.display.render_aa = "8"
    scene.render.film_transparent = False
    scene.world.color = (0.88, 0.88, 0.90) if scene.world else None


def render(output: Path, direction: tuple[float, float, float],
           centre: tuple[float, float, float], ortho: float,
           resolution: int) -> None:
    scene = bpy.context.scene
    length = math.sqrt(sum(value * value for value in direction))
    unit = tuple(value / length for value in direction)
    distance = ortho * 2.6
    camera_data = bpy.data.cameras.new("clay_camera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = ortho
    camera = bpy.data.objects.new("clay_camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = tuple(centre[axis] + unit[axis] * distance for axis in range(3))
    direction_vector = camera.location - type(camera.location)(centre)
    camera.rotation_euler = direction_vector.to_track_quat("Z", "Y").to_euler()
    scene.camera = camera

    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera, do_unlink=True)


def review_one(asset: dict, root: Path, out_dir: Path, resolution: int) -> dict:
    bpy.ops.wm.open_mainfile(filepath=str(root / asset["blend"]))
    setup_clay(bpy.context.scene)

    meshes = visible_meshes()
    if not meshes:
        return {"id": asset["id"], "status": "failed", "images": [],
                "reason": "aucun_maillage_visible"}

    clay = clay_material()
    for obj in meshes:
        obj.data.materials.clear()
        obj.data.materials.append(clay)

    centre, ortho = frame(meshes)
    images = []
    for name, direction in VIEWS.items():
        image = out_dir / f"{asset['id']}_clay_{name}.png"
        render(image, direction, centre, ortho, resolution)
        images.append(image.relative_to(root).as_posix())
    return {"id": asset["id"], "status": "passed", "images": images,
            "meshes": len(meshes), "ortho_m": round(ortho, 3)}


def main() -> int:
    plan = json.loads(Path(arguments().plan).read_text(encoding="utf-8"))
    root = Path(plan["project_root"]).resolve()
    out_dir = root / plan["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    resolution = int(plan.get("resolution", 720))

    reports = []
    for asset in plan["assets"]:
        report = review_one(asset, root, out_dir, resolution)
        reports.append(report)
        print("CITYLAB_CLAY_REVIEW " + report["id"] + " " + report["status"]
              + " images=" + str(len(report["images"])))

    failed = [item["id"] for item in reports if item["status"] != "passed"]
    (out_dir / "clay_review.json").write_text(
        json.dumps({"schema": 1, "id": "citylab_clay_review",
                    "assets": reports, "unity_launched": False},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if failed:
        print("CITYLAB_CLAY_REVIEW_ERROR " + " ".join(failed))
        return 1
    print("CITYLAB_CLAY_REVIEW_OK assets=" + str(len(reports))
          + " vues=" + str(len(VIEWS)) + " unity_launched=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
