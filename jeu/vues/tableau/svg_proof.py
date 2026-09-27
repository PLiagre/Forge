"""Carte SVG déterministe : cellules réelles + légende, sans navigateur."""

from __future__ import annotations

from typing import Any, Iterable, List, Sequence, Tuple

from vues.tableau.classify import ABSENT, NON_CALCULE, classify, numeric_diff, numeric_or_none

_WIDTH = 960
_HEIGHT = 720
_MARGIN = 48
_LEGEND_H = 72


def _rings(geometry: dict) -> List[List[Tuple[float, float]]]:
    kind = geometry.get("type")
    coords = geometry.get("coordinates")
    rings: List[List[Tuple[float, float]]] = []
    if kind == "Polygon":
        rings.append([(float(x), float(y)) for x, y in coords[0]])
    elif kind == "MultiPolygon":
        for poly in coords:
            rings.append([(float(x), float(y)) for x, y in poly[0]])
    return rings


def _bbox(cells: Sequence[dict]) -> Tuple[float, float, float, float]:
    xs: List[float] = []
    ys: List[float] = []
    for cell in cells:
        for ring in _rings(cell["geometry"]):
            for x, y in ring:
                xs.append(x)
                ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def _project(
    x: float,
    y: float,
    bounds: Tuple[float, float, float, float],
) -> Tuple[float, float]:
    minx, miny, maxx, maxy = bounds
    span_x = max(maxx - minx, 1.0)
    span_y = max(maxy - miny, 1.0)
    usable_w = _WIDTH - 2 * _MARGIN
    usable_h = _HEIGHT - 2 * _MARGIN - _LEGEND_H
    scale = min(usable_w / span_x, usable_h / span_y)
    px = _MARGIN + (x - minx) * scale
    py = _MARGIN + (maxy - y) * scale
    return px, py


def _color(value: Any, vmin: float, vmax: float) -> str:
    etat = classify(value)
    if etat == ABSENT:
        return "#9e9e9e"
    if etat == NON_CALCULE:
        return "#6d4c41"
    number = numeric_or_none(value)
    if number is None:
        return "#9e9e9e"
    if vmax <= vmin:
        t = 0.0
    else:
        t = (number - vmin) / (vmax - vmin)
    t = min(1.0, max(0.0, t))
    r = int(8 + 247 * t)
    g = int(48 + 80 * (1.0 - t))
    b = int(107 + 40 * (1.0 - t))
    return f"#{r:02x}{g:02x}{b:02x}"


def _path(ring: Iterable[Tuple[float, float]], bounds) -> str:
    parts = []
    for index, (x, y) in enumerate(ring):
        px, py = _project(x, y, bounds)
        cmd = "M" if index == 0 else "L"
        parts.append(f"{cmd}{px:.3f},{py:.3f}")
    parts.append("Z")
    return " ".join(parts)


def cell_value(cell: dict, layer: str) -> Any:
    if layer == "population":
        return cell["population"]
    stocks = cell.get("stocks")
    if isinstance(stocks, dict) and layer in stocks:
        return stocks[layer]
    if isinstance(stocks, dict) and layer not in ("insolation", "dist_sea"):
        return None
    if layer == "food_deficit_kg":
        return cell.get("food_deficit_kg")
    if layer == "hunger_ticks":
        return cell.get("hunger_ticks")
    climat = cell.get("climat")
    if climat is None:
        raise KeyError(f"couche climat absente du snapshot pour {layer}")
    if layer == "insolation":
        return climat["insolation_annuelle_mj_m2"]
    if layer == "dist_sea":
        return climat["distance_mer_centroide_m"]
    raise KeyError(layer)


def render_svg(document: dict, *, layer: str = "population") -> str:
    cells = sorted(document["cells"], key=lambda cell: int(cell["cell_id"]))
    bounds = _bbox(cells)
    numbers = [
        numeric_or_none(cell_value(cell, layer))
        for cell in cells
    ]
    present = [value for value in numbers if value is not None]
    vmin = min(present) if present else 0.0
    vmax = max(present) if present else 1.0
    groups = []
    for cell in cells:
        value = cell_value(cell, layer)
        fill = _color(value, vmin, vmax)
        paths = []
        for ring in _rings(cell["geometry"]):
            d = _path(ring, bounds)
            paths.append(
                f'<path d="{d}" fill="{fill}" stroke="#37474f" stroke-width="0.4"/>'
            )
        groups.append(
            f'<g id="cell-{int(cell["cell_id"])}">{"".join(paths)}</g>'
        )
    legend = (
        f'<text x="{_MARGIN}" y="{_HEIGHT - 48}" font-size="14" fill="#212121">'
        f"couche {layer} — {len(cells)} cellules — tick {document['tick']} "
        f"graine {document['seed']}</text>"
        f'<rect x="{_MARGIN}" y="{_HEIGHT - 36}" width="18" height="12" fill="#08306b"/>'
        f'<text x="{_MARGIN + 24}" y="{_HEIGHT - 26}" font-size="12">zéro mesuré</text>'
        f'<rect x="{_MARGIN + 160}" y="{_HEIGHT - 36}" width="18" height="12" fill="#9e9e9e"/>'
        f'<text x="{_MARGIN + 184}" y="{_HEIGHT - 26}" font-size="12">absent</text>'
        f'<rect x="{_MARGIN + 280}" y="{_HEIGHT - 36}" width="18" height="12" fill="#6d4c41"/>'
        f'<text x="{_MARGIN + 304}" y="{_HEIGHT - 26}" font-size="12">non calculé (-1)</text>'
        f'<rect x="{_MARGIN + 460}" y="{_HEIGHT - 36}" width="80" height="12" '
        f'fill="url(#grad)"/>'
        f'<text x="{_MARGIN + 546}" y="{_HEIGHT - 26}" font-size="12">'
        f"{vmin:.0f} → {vmax:.0f}</text>"
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_WIDTH}" height="{_HEIGHT}" '
        f'viewBox="0 0 {_WIDTH} {_HEIGHT}">'
        "<defs><linearGradient id=\"grad\" x1=\"0\" x2=\"1\">"
        "<stop offset=\"0%\" stop-color=\"#08306b\"/>"
        "<stop offset=\"100%\" stop-color=\"#ff5037\"/>"
        "</linearGradient></defs>"
        f'<rect width="100%" height="100%" fill="#eceff1"/>'
        f"{''.join(groups)}{legend}</svg>\n"
    )


def render_compare_svg(
    document_a: dict,
    document_b: dict,
    *,
    layer: str = "population",
) -> str:
    cells_a = {int(cell["cell_id"]): cell for cell in document_a["cells"]}
    cells_b = {int(cell["cell_id"]): cell for cell in document_b["cells"]}
    cells = sorted(document_a["cells"], key=lambda cell: int(cell["cell_id"]))
    bounds = _bbox(cells)
    diffs = []
    for cell in cells:
        cid = int(cell["cell_id"])
        other = cells_b.get(cid)
        if other is None:
            diffs.append(None)
            continue
        diffs.append(numeric_diff(cell_value(cell, layer), cell_value(other, layer)))
    present = [value for value in diffs if value is not None]
    vmax = max(abs(value) for value in present) if present else 1.0
    vmin = -vmax
    groups = []
    for cell, delta in zip(cells, diffs):
        if delta is None:
            fill = "#bdbdbd"
        else:
            fill = _color(delta, vmin, vmax)
        paths = []
        for ring in _rings(cell["geometry"]):
            d = _path(ring, bounds)
            paths.append(
                f'<path d="{d}" fill="{fill}" stroke="#37474f" stroke-width="0.4"/>'
            )
        groups.append(
            f'<g id="cell-{int(cell["cell_id"])}">{"".join(paths)}</g>'
        )
    legend = (
        f'<text x="{_MARGIN}" y="{_HEIGHT - 48}" font-size="14" fill="#212121">'
        f"comparaison {layer} — B−A — {len(cells)} cellules — "
        f"tick {document_a['tick']}→{document_b['tick']}</text>"
        f'<rect x="{_MARGIN}" y="{_HEIGHT - 36}" width="18" height="12" fill="#08306b"/>'
        f'<text x="{_MARGIN + 24}" y="{_HEIGHT - 26}" font-size="12">zéro mesuré</text>'
        f'<rect x="{_MARGIN + 160}" y="{_HEIGHT - 36}" width="18" height="12" fill="#9e9e9e"/>'
        f'<text x="{_MARGIN + 184}" y="{_HEIGHT - 26}" font-size="12">absent</text>'
        f'<rect x="{_MARGIN + 280}" y="{_HEIGHT - 36}" width="18" height="12" fill="#6d4c41"/>'
        f'<text x="{_MARGIN + 304}" y="{_HEIGHT - 26}" font-size="12">non calculé (-1)</text>'
        f'<rect x="{_MARGIN + 460}" y="{_HEIGHT - 36}" width="18" height="12" fill="#bdbdbd"/>'
        f'<text x="{_MARGIN + 484}" y="{_HEIGHT - 26}" font-size="12">incomparable</text>'
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_WIDTH}" height="{_HEIGHT}" '
        f'viewBox="0 0 {_WIDTH} {_HEIGHT}">'
        f'<rect width="100%" height="100%" fill="#eceff1"/>'
        f"{''.join(groups)}{legend}</svg>\n"
    )


def write_svg(
    document: dict,
    path,
    *,
    layer: str = "population",
    compare: dict | None = None,
) -> None:
    destination = path
    destination.parent.mkdir(parents=True, exist_ok=True)
    if compare is not None:
        payload = render_compare_svg(document, compare, layer=layer)
    else:
        payload = render_svg(document, layer=layer)
    destination.write_bytes(payload.encode("utf-8"))
