"""Rend en argile les `.blend` de revue, pour juger la forme et non la matiere.

Les rendus de la Factory sont nocturnes et lites : ils cachent la geometrie. Les
cinq defauts de conception nommes jusqu'ici ont tous ete trouves en argile,
aucun sur un rendu lite -- et pourtant rien dans le depot ne les produisait.

    py Tools/AssetFactory/clay_review.py
    py Tools/AssetFactory/clay_review.py --only sawmill
    py Tools/AssetFactory/clay_review.py --only barn --resolution 1080

Un seul processus Blender traite toute la liste : ouvrir un `.blend` coute des
secondes, lancer Blender en coute plus.

Il ne lance jamais Unity et ne republie rien : il lit des `.blend` deja produits.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Tools.AssetFactory.citylab_factory import (  # noqa: E402
    FactoryPaths,
    blender_version,
    find_blender,
    load_config,
)

RENDER_SCRIPT = "Tools/AssetFactory/Blender/render_clay_review.py"
OUTPUT_DIR = "AssetFactory/Reports/QA/Clay"
WORKBENCH = "AssetFactory/Workbench"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--catalog", default="AssetFactory/Catalogs/building_pilot.json")
    parser.add_argument("--only", action="append", default=[],
                        help="ne traiter que les assets dont l'identifiant "
                             "contient ce fragment")
    parser.add_argument("--resolution", type=int, default=720)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    catalog = json.loads((root / args.catalog).read_text(encoding="utf-8"))

    assets = []
    for family in catalog["families"]:
        for variant in catalog["variants"]:
            asset_id = f"{family['id']}_{variant['id']}"
            if args.only and not any(item in asset_id for item in args.only):
                continue
            blend = f"{WORKBENCH}/{asset_id}_review.blend"
            if not (root / blend).is_file():
                print("CITYLAB_CLAY_REVIEW_ERROR blend_absent " + asset_id)
                return 1
            assets.append({"id": asset_id, "blend": blend})

    if not assets:
        print("CITYLAB_CLAY_REVIEW_ERROR aucun_asset_selectionne")
        return 1

    plan_path = root / "AssetFactory/Reports/QA/clay_review_plan.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps({
        "project_root": root.as_posix(),
        "output_dir": OUTPUT_DIR,
        "resolution": args.resolution,
        "assets": assets,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.plan_only:
        print("CITYLAB_CLAY_REVIEW_PLAN assets=" + str(len(assets)))
        return 0

    config = load_config(FactoryPaths(root, root / "AssetFactory" / "config.json"))
    blender = find_blender(config, root)
    completed = subprocess.run([
        str(blender), "--background", "--factory-startup",
        "--python", str(root / RENDER_SCRIPT), "--", "--plan", str(plan_path),
    ], capture_output=True, text=True)
    for line in (completed.stdout or "").splitlines():
        if line.startswith("CITYLAB_CLAY_REVIEW"):
            print(line)
    if completed.returncode != 0:
        sys.stderr.write(completed.stderr)
    else:
        print("blender=\"" + blender_version(blender) + "\"")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
