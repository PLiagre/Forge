"""Régénère les rapports QA de rechargement FBX depuis les manifestes publiés.

Construit le plan — quel FBX, quel identifiant, quelle nature — puis lance une
seule fois Blender sur `Blender/audit_published_fbx.py`. Ne lance jamais Unity.

    py Tools/AssetFactory/refresh_fbx_qa.py
    py Tools/AssetFactory/refresh_fbx_qa.py --only building_residence_frontier_01
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPORT_DIR = "AssetFactory/Reports/QA/Fbx"
AUDIT_SCRIPT = "Tools/AssetFactory/Blender/audit_published_fbx.py"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def blender_executable(root: Path) -> str:
    override = os.environ.get("CITYLAB_BLENDER")
    if override:
        return override
    config = load(root / "AssetFactory/config.json")
    executable = config["blender"]["executable"]
    if Path(executable).is_file():
        return executable
    for pattern in config["blender"].get("windows_globs", []):
        drive, _, tail = pattern.partition("/")
        for found in sorted(Path(drive + "/").glob(tail)):
            return str(found)
    raise FileNotFoundError("Blender introuvable : renseigner CITYLAB_BLENDER")


def planned_assets(root: Path) -> list[dict]:
    # La scierie avait son manifeste separe. Elle est entree au catalogue du
    # pilote : un seul manifeste porte les vingt-quatre batiments.
    assets: list[dict] = []

    pilot = load(root / "AssetFactory/Manifests/building_pilot.json")
    for family in pilot["families"]:
        for variant in family["variants"]:
            assets.append({
                "id": family["id"] + "_" + variant["id"],
                "kind": "building",
                "fbx": variant["published_fbx"],
            })

    characters = load(root / "AssetFactory/Manifests/character_factory.json")
    for asset in characters["assets"]:
        assets.append({
            "id": asset["id"],
            "kind": "character",
            "fbx": asset["path"],
        })

    return assets


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--only", action="append", default=[],
                        help="ne traiter que les identifiants contenant ce fragment")
    parser.add_argument("--plan-only", action="store_true",
                        help="écrire le plan et s'arrêter, sans lancer Blender")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    assets = planned_assets(root)
    if args.only:
        assets = [item for item in assets
                  if any(fragment in item["id"] for fragment in args.only)]
    if not assets:
        print("CITYLAB_FBX_AUDIT_ERROR aucun asset selectionne")
        return 1

    missing = [item["id"] for item in assets if not (root / item["fbx"]).is_file()]
    if missing:
        print("CITYLAB_FBX_AUDIT_ERROR fbx_absent " + " ".join(missing))
        return 1

    plan_path = root / "AssetFactory/Reports/QA/fbx_audit_plan.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps({
        "project_root": root.as_posix(),
        "report_dir": REPORT_DIR,
        "assets": assets,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.plan_only:
        print("CITYLAB_FBX_AUDIT_PLAN assets=" + str(len(assets))
              + " plan=" + plan_path.relative_to(root).as_posix())
        return 0

    command = [
        blender_executable(root), "--background", "--factory-startup",
        "--python", str(root / AUDIT_SCRIPT), "--", "--plan", str(plan_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    sys.stdout.write(completed.stdout)
    sys.stderr.write(completed.stderr)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
