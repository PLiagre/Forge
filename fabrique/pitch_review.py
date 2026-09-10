"""Planche de décision : la même famille rendue à plusieurs pentes de toit.

La porte A-8 de `M1-ASSET-07` demande un jugement humain sur une planche de
contact à 96 px. Telle quelle, elle pose une question fermée — oui ou non — alors
que la remarque à trancher est ouverte : la pente autoritaire du style produit des
combles hauts. Une portée de neuf mètres à 50° donne six mètres de comble pour un
mur de 3,8.

`roof.pitch_deg` vit dans `AssetFactory/Styles/<style>.json` : le resserrer
restyle les vingt et un bâtiments sans toucher une ligne de générateur. Cet outil
rend le même jeu de variantes sous plusieurs plages de pente, à la taille de revue
du style, pour que la décision se prenne sur ce qu'on verra et non sur un nombre.

Il n'écrit jamais dans le style du dépôt : chaque option est un fichier de style
temporaire, supprimé en sortie, et chaque rendu va sous
`AssetFactory/Workbench/` qui n'est pas versionné.

    py Tools/AssetFactory/pitch_review.py
    py Tools/AssetFactory/pitch_review.py --pitch 36,52 --pitch 30,40
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

GENERATOR = "Tools/AssetFactory/Blender/generate_building_family.py"
WORK_ROOT = "AssetFactory/Workbench/PitchReview"
DEFAULT_PITCHES = ("36,52", "32,44", "28,38")


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


def option_label(pitch: tuple[float, float]) -> str:
    return f"{pitch[0]:g}-{pitch[1]:g}"


def render_option(root: Path, blender: str, catalog_path: Path, family: str,
                  variants: list[str], pitch: tuple[float, float]) -> Path:
    """Rend une option de pente et retourne son dossier de previews."""
    catalog = load(catalog_path)
    label = option_label(pitch)
    style_id = catalog["style"]
    temporary_style_id = f"{style_id}__pitch_{label.replace('-', '_')}"

    style_dir = root / "AssetFactory/Styles"
    source_style = style_dir / f"{style_id}.json"
    temporary_style = style_dir / f"{temporary_style_id}.json"

    style = load(source_style)
    style["id"] = temporary_style_id
    style["roof"]["pitch_deg"] = [pitch[0], pitch[1]]

    scratch = root / WORK_ROOT / label
    scratch_catalog = scratch / "catalog.json"
    catalog["style"] = temporary_style_id
    scratch.mkdir(parents=True, exist_ok=True)

    temporary_style.write_text(json.dumps(style, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    scratch_catalog.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    try:
        for variant in variants:
            command = [
                blender, "--background", "--factory-startup",
                "--python", str(root / GENERATOR), "--",
                "--project-root", str(root),
                "--catalog", str(scratch_catalog),
                "--output-root", str(scratch),
                "--family", family,
                "--variant", variant,
            ]
            completed = subprocess.run(command, capture_output=True, text=True)
            if completed.returncode != 0:
                sys.stderr.write(completed.stdout[-2000:])
                sys.stderr.write(completed.stderr[-2000:])
                raise RuntimeError(f"pente {label} variante {variant} : Blender a echoue")
    finally:
        temporary_style.unlink(missing_ok=True)

    return scratch / "Workbench" / "Previews"


def board(root: Path, family: str, variants: list[str],
          columns: list[tuple[str, Path]], size: int, output: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    font_path = Path("C:/Windows/Fonts/arial.ttf")
    font = (ImageFont.truetype(str(font_path), 13) if font_path.is_file()
            else ImageFont.load_default(size=13))
    margin, gutter, header, label_width = 12, 10, 40, 96

    # Le pas des colonnes suit le plus large des deux : la vignette ou son
    # titre. Sinon un libelle un peu long deborde sur la colonne suivante.
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    title_width = max(probe.textbbox((0, 0), title, font=font)[2] for title, _ in columns)
    step = max(size, title_width) + gutter

    width = label_width + margin * 2 + len(columns) * step
    height = header + len(variants) * (size + gutter) + margin
    canvas = Image.new("RGB", (width, height), "#0E171F")
    draw = ImageDraw.Draw(canvas)

    for index, (title, _) in enumerate(columns):
        draw.text((label_width + margin + index * step, 12),
                  title, font=font, fill="#F2E6D0")
    for row, variant in enumerate(variants):
        top = header + row * (size + gutter)
        draw.text((margin, top + size // 2 - 7), f"{family.split('_')[1]} {variant}",
                  font=font, fill="#F2E6D0")
        for index, (_, previews) in enumerate(columns):
            left = label_width + margin + index * step
            tile = previews / f"{family}_{variant}_contact.png"
            if not tile.is_file():
                draw.rectangle([left, top, left + size, top + size], outline="#5A3B2A")
                continue
            with Image.open(tile) as source:
                panel = source.convert("RGB").resize((size, size), Image.Resampling.LANCZOS)
            canvas.paste(panel, (left, top))

    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--catalog", default="AssetFactory/Catalogs/building_pilot.json")
    parser.add_argument("--family", default="building_residence_frontier_01")
    parser.add_argument("--variants", default="a,b,c")
    parser.add_argument("--pitch", action="append", default=[],
                        help="plage de pente 'min,max' ; repetable")
    parser.add_argument("--keep-workbench", action="store_true",
                        help="conserver les rendus intermediaires")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    catalog_path = root / args.catalog
    variants = [item.strip() for item in args.variants.split(",") if item.strip()]
    raw_pitches = args.pitch or list(DEFAULT_PITCHES)
    pitches = [tuple(float(part) for part in item.split(","))  # type: ignore[misc]
               for item in raw_pitches]

    style = load(root / "AssetFactory/Styles" / f"{load(catalog_path)['style']}.json")
    size = int(style["review"]["contact_sheet_px"])
    current = tuple(float(value) for value in style["roof"]["pitch_deg"])
    blender = blender_executable(root)

    columns = []
    for pitch in pitches:
        previews = render_option(root, blender, catalog_path, args.family, variants, pitch)
        label = option_label(pitch)
        title = f"{label} deg" + (" (actuel)" if tuple(pitch) == current else "")
        columns.append((title, previews))

    output = root / "AssetFactory/Reports/QA" / f"{args.family}_pitch_{size}px.png"
    board(root, args.family, variants, columns, size, output)

    if not args.keep_workbench:
        shutil.rmtree(root / WORK_ROOT, ignore_errors=True)

    stray = sorted((root / "AssetFactory/Styles").glob("*__pitch_*.json"))
    if stray:
        print("CITYLAB_PITCH_REVIEW_ERROR style_temporaire_restant "
              + ",".join(path.name for path in stray))
        return 1

    print(f"CITYLAB_PITCH_REVIEW_OK family={args.family} "
          f"options={len(columns)} variants={len(variants)} px={size} "
          f"board={output.relative_to(root).as_posix()} unity_launched=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
