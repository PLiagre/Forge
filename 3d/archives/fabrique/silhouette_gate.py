#!/usr/bin/env python3
"""Porte de silhouette et planche de contact a taille RTS.

Une revue faite sur des rendus heroiques valide des batiments qu'on ne verra
jamais ainsi. Ce module mesure ce que l'œil lit en premier : la silhouette
pleine, a l'angle RTS, a la resolution que le style declare.
"""

from __future__ import annotations

import argparse
import json
import math
from itertools import combinations
from pathlib import Path


def iou_masks(first: list[bool], second: list[bool]) -> float:
    """Intersection sur union de deux silhouettes de meme taille."""
    if len(first) != len(second):
        raise ValueError("Silhouettes de tailles differentes")
    intersection = sum(1 for a, b in zip(first, second) if a and b)
    union = sum(1 for a, b in zip(first, second) if a or b)
    if union == 0:
        raise ValueError("Deux silhouettes vides ne se comparent pas")
    return intersection / union


def normalised_mask(mask: list[bool], size: int, target: int = 64) -> list[bool]:
    """Recadrer la silhouette sur sa boite englobante, puis la remettre a l'echelle.

    Sans cela l'articulation ne mesure pas une forme mais un taux de remplissage
    du cadre : le meme batiment rendu plus petit rend un perimetre plus court et
    une articulation plus faible. Mesure a l'appui, la meme residence est passee
    de 6,88 a 5,16 pour un simple elargissement du cadrage.
    """
    rows = [mask[y * size:(y + 1) * size] for y in range(size)]
    xs = [x for y in range(size) for x in range(size) if rows[y][x]]
    ys = [y for y in range(size) for x in range(size) if rows[y][x]]
    if not xs:
        raise ValueError("Silhouette vide")
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    width, height = x1 - x0 + 1, y1 - y0 + 1
    out: list[bool] = []
    for row in range(target):
        source_y = y0 + min(height - 1, row * height // target)
        for column in range(target):
            source_x = x0 + min(width - 1, column * width // target)
            out.append(rows[source_y][source_x])
    return out


def articulation(mask: list[bool], size: int = 64) -> float:
    """Perimetre / racine(aire) d'une silhouette, normalisee en echelle.

    Une boite a pignon vaut environ 4,4 ; chaque volume ajoute -- porche,
    appentis, lucarne, croupe transversale, souche de cheminee, escalier -- fait
    monter la valeur. C'est la mesure qui a chiffre le refus de la porte A-8 :
    les deux references de style valent 7,03 et 7,49 tandis que les trois
    residences de la phase A tenaient toutes entre 5,42 et 5,63.
    """
    normalised = normalised_mask(mask, size)
    side = 64
    rows = [normalised[y * side:(y + 1) * side] for y in range(side)]
    area = sum(1 for row in rows for value in row if value)
    if area == 0:
        raise ValueError("Silhouette vide")
    perimeter = 0
    for y in range(side):
        for x in range(side):
            if not rows[y][x]:
                continue
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ny, nx = y + dy, x + dx
                if ny < 0 or nx < 0 or ny >= side or nx >= side or not rows[ny][nx]:
                    perimeter += 1
    return perimeter / math.sqrt(area)


def mask_from_png(path: Path, size: int) -> list[bool]:
    """Silhouette pleine : l'alpha du rendu a fond transparent."""
    from PIL import Image

    with Image.open(path) as source:
        image = source.convert("RGBA")
        if image.size != (size, size):
            image = image.resize((size, size), Image.Resampling.NEAREST)
        return [value > 127 for value in image.getchannel("A").tobytes()]


def pair_table(masks: dict[str, list[bool]], threshold: float) -> list[dict]:
    rows = []
    for first, second in combinations(sorted(masks), 2):
        value = iou_masks(masks[first], masks[second])
        rows.append({
            "pair": f"{first}-{second}",
            "iou": round(value, 4),
            "threshold": threshold,
            "passed": value <= threshold,
        })
    return rows


def contact_sheet(rows: list[tuple[str, Path | None, Path | None]], size: int,
                  output: Path) -> None:
    """Planche ancienne / nouvelle, a la taille de revue du style."""
    from PIL import Image, ImageDraw, ImageFont

    font_path = Path("C:/Windows/Fonts/arial.ttf")
    font = (ImageFont.truetype(str(font_path), 13) if font_path.is_file()
            else ImageFont.load_default(size=13))
    margin, gutter, header = 12, 10, 40
    label_width = 96
    width = label_width + margin * 2 + size * 2 + gutter
    height = header + len(rows) * (size + gutter) + margin
    canvas = Image.new("RGB", (width, height), "#0E171F")
    draw = ImageDraw.Draw(canvas)
    draw.text((label_width + margin, 12), "refuse A-8", font=font, fill="#F2E6D0")
    draw.text((label_width + margin + size + gutter, 12), "lot 003", font=font, fill="#F2E6D0")
    for index, (label, before, after) in enumerate(rows):
        top = header + index * (size + gutter)
        draw.text((margin, top + size // 2 - 7), label, font=font, fill="#F2E6D0")
        for column, path in enumerate((before, after)):
            left = label_width + margin + column * (size + gutter)
            if path is None or not Path(path).is_file():
                draw.rectangle([left, top, left + size, top + size], outline="#5A3B2A")
                continue
            with Image.open(path) as source:
                panel = source.convert("RGB").resize((size, size), Image.Resampling.LANCZOS)
            canvas.paste(panel, (left, top))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, optimize=True)


def function_of(root: Path, family_id: str) -> str | None:
    """La fonction d'une famille, telle que le catalogue du pilote la declare."""
    catalog = root / "AssetFactory/Catalogs/building_pilot.json"
    if not catalog.is_file():
        return None
    families = json.loads(catalog.read_text(encoding="utf-8"))["families"]
    return next((item["function"] for item in families
                 if item["id"] == family_id), None)


def min_articulation(style: dict, function: str | None) -> float:
    """Le seuil C-1 qui vaut pour cette fonction.

    Le 6,0 est pose sous la plus sobre de deux references de **maison** -- 6,17
    pour la maison de ville, 7,41 pour la chaumiere -- et il n'avait jamais ete
    mesure ailleurs que sur l'habitat. Mesure sur les sept autres familles, il
    refusait douze batiments sur vingt-quatre.

    **Le proprietaire l'abaisse a 5,5 pour les fonctions non domestiques le
    2026-08-30** : une grange ou un entrepot modeste est une masse simple par
    nature. `scheme.domestic_functions` dit qui reste a 6,0. Deplacer ce seuil
    reste une decision du proprietaire, jamais un reglage : un test garde la
    valeur des deux cotes.
    """
    gate = style["silhouette_gate"]
    domestic = style["scheme"].get("domestic_functions") or []
    if function is not None and function not in domestic:
        return float(gate.get("min_articulation_non_domestic",
                              gate.get("min_articulation", 0.0)))
    return float(gate.get("min_articulation", 0.0))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--family", required=True)
    parser.add_argument("--variants", default="a,b,c")
    parser.add_argument("--style", default="frontier")
    parser.add_argument("--before-root",
                        default="AssetFactory/Workbench/Previews/Refuse_A8")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    style = json.loads((root / "AssetFactory" / "Styles" / f"{args.style}.json")
                       .read_text(encoding="utf-8"))
    gate = style["silhouette_gate"]
    review = style["review"]
    previews = root / "AssetFactory/Workbench/Previews"
    variants = [item.strip() for item in args.variants.split(",") if item.strip()]

    render_px = int(gate["render_px"])
    iou_px = int(gate.get("iou_px", render_px))
    paths = {variant: previews / f"{args.family}_{variant}_silhouette.png"
             for variant in variants}
    masks = {variant: mask_from_png(path, iou_px) for variant, path in paths.items()}
    rows = pair_table(masks, float(gate["max_iou_same_family"]))

    # L'articulation se mesure sur le rendu pleine resolution, recadre sur sa
    # boite englobante : sinon elle mesure le remplissage du cadre et non la
    # forme. L'IoU, lui, reste a la resolution que le style declare.
    function = function_of(root, args.family)
    minimum = min_articulation(style, function)
    shapes = []
    for variant, path in paths.items():
        value = articulation(mask_from_png(path, render_px), render_px)
        shapes.append({
            "variant": variant,
            "articulation": round(value, 3),
            "threshold": minimum,
            "passed": value >= minimum,
        })
    # L'etendue d'articulation entre variantes reste **mesuree et consignee**,
    # elle n'est plus une porte. Elle exigeait que les trois variantes different
    # assez (C-2, seuil 0,80) pendant que C-1 exigeait que chacune soit assez
    # articulee : ameliorer les plus faibles les rapprochait des fortes, et les
    # deux exigences se sont contredites cinq fois de suite. Le proprietaire a
    # tranche le 2026-08-29 : C-2 est supprimee, C-1 reste. Le nombre garde sa
    # valeur d'observation -- une famille dont l'etendue s'effondre a quelque
    # chose a dire -- mais il ne decide plus.
    values = [item["articulation"] for item in shapes]
    spread = round(max(values) - min(values), 3)

    sheet = root / "AssetFactory/Reports/QA" / f"{args.family}_contact_{review['contact_sheet_px']}px.png"
    contact_sheet(
        [(f"{args.family.split('_')[1]} {variant}",
          root / args.before_root / f"{args.family}_{variant}_rts.png",
          previews / f"{args.family}_{variant}_contact.png")
         for variant in variants],
        int(review["contact_sheet_px"]), sheet)

    report = {
        "schema": 1,
        "id": f"silhouette_gate_{args.family}",
        "style": args.style,
        "render_px": int(gate["render_px"]),
        "camera": gate["camera"],
        "max_iou_same_family": float(gate["max_iou_same_family"]),
        "pairs": rows,
        "function": function,
        "articulation": {
            "render_px": render_px,
            "min_articulation": minimum,
            "min_articulation_domestic": float(gate.get("min_articulation", 0.0)),
            "min_articulation_non_domestic":
                float(gate.get("min_articulation_non_domestic",
                               gate.get("min_articulation", 0.0))),
            "variants": shapes,
            "observed_spread": spread,
        },
        "passed": (all(row["passed"] for row in rows)
                   and all(item["passed"] for item in shapes)),
        "contact_sheet": sheet.relative_to(root).as_posix(),
        "contact_sheet_px": int(review["contact_sheet_px"]),
    }
    path = root / "AssetFactory/Reports/QA" / f"{args.family}_silhouette.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    verdict = "OK" if report["passed"] else "FAILED"
    detail = " ".join(f"{row['pair']}={row['iou']}" for row in rows)
    shape_detail = " ".join(f"{item['variant']}={item['articulation']}" for item in shapes)
    print(f"CITYLAB_SILHOUETTE_GATE_{verdict} iou[{detail}] max={gate['max_iou_same_family']} "
          f"articulation[{shape_detail}] min={minimum} "
          f"fonction={function or 'inconnue'} etendue_observee={spread}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
