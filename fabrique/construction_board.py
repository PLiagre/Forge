#!/usr/bin/env python3
"""Planche de chantier : une variante, toutes ses étapes de construction.

Le contrat de construction v2 découpe un bâtiment en étapes nommées et le
générateur rend une image par étape. Cet outil les aligne pour que le chantier
se juge d'un coup d'œil, à côté du compte de triangles que chaque étape ajoute.

Il ne rend rien : il assemble des images déjà produites. Relancer un rendu qu'on
peut mesurer sur un artefact existant est du temps perdu.

    py Tools/AssetFactory/construction_board.py
    py Tools/AssetFactory/construction_board.py --family building_residence_frontier_01 --variant b
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREVIEWS = ROOT / "AssetFactory/Workbench/Previews"
REPORTS = ROOT / "AssetFactory/Reports"
OUTPUT = ROOT / "AssetFactory/Reports/QA"


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--family", default="building_residence_frontier_01")
    parser.add_argument("--variant", default="b")
    parser.add_argument("--tile", type=int, default=300)
    parser.add_argument("--columns", type=int, default=4)
    return parser.parse_args()


def main() -> int:
    from PIL import Image, ImageDraw

    args = arguments()
    asset_id = f"{args.family}_{args.variant}"
    metrics_path = REPORTS / f"{asset_id}_metrics.json"
    if not metrics_path.is_file():
        raise SystemExit(f"CITYLAB_CONSTRUCTION_BOARD_ERROR metriques absentes : {metrics_path}")
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    construction = metrics.get("construction")
    if not construction:
        raise SystemExit(
            "CITYLAB_CONSTRUCTION_BOARD_ERROR "
            f"{asset_id} n'est pas sous le contrat de construction v2")
    stages = construction["stages"]

    tiles: list[tuple[str, Image.Image]] = []
    running = 0
    for index, stage in enumerate(stages, start=1):
        image_path = PREVIEWS / f"{asset_id}_stage_{index:02d}_{stage['id']}.png"
        if not image_path.is_file():
            raise SystemExit(
                f"CITYLAB_CONSTRUCTION_BOARD_ERROR rendu d'etape absent : {image_path}")
        running += stage["lod0"]
        caption = (f"{index}. {stage['id']}  +{stage['lod0']} tris"
                   f"  ({running}/{metrics['triangles']['lod0']})")
        with Image.open(image_path) as source:
            tiles.append((caption, source.convert("RGB")
                          .resize((args.tile, args.tile), Image.LANCZOS)))

    columns = min(args.columns, len(tiles))
    rows = (len(tiles) + columns - 1) // columns
    header = 26
    board = Image.new("RGB", (columns * args.tile, rows * (args.tile + header)),
                      (12, 12, 16))
    draw = ImageDraw.Draw(board)
    for index, (caption, tile) in enumerate(tiles):
        x = (index % columns) * args.tile
        y = (index // columns) * (args.tile + header)
        draw.text((x + 8, y + 7), caption, fill=(230, 225, 215))
        board.paste(tile, (x, y + header))

    OUTPUT.mkdir(parents=True, exist_ok=True)
    target = OUTPUT / f"{asset_id}_construction_board.png"
    board.save(target)
    print(f"CITYLAB_CONSTRUCTION_BOARD_OK id={asset_id} stages={len(stages)} "
          f"lod0={metrics['triangles']['lod0']} "
          f"path={target.relative_to(ROOT).as_posix()} unity_launched=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
