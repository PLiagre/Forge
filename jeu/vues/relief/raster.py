"""Rasterise une photographie de sim/ en MNT (classes de relief → mètres).

Le visualisateur LIT. Il ne décide aucune mécanique. Une classe de
relief inconnue est un refus, pas une invention (règle 10).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw


# Altitudes de lecture, fidélité 2 : ordres de grandeur plausibles,
# jamais sourcés. La mer (pixels sans cellule) reste à 0.
HAUTEURS_M = {
    "marais": 2.0,
    "plaine": 120.0,
    "colline": 400.0,
    "montagne": 1400.0,
    "haute_montagne": 2800.0,
}


class RasterErreur(RuntimeError):
    """Refus : donnée manquante, jamais inventée."""


def _anneaux(geometry: dict) -> List[Tuple[List[Tuple[float, float]], List[List[Tuple[float, float]]]]]:
    kind = geometry.get("type")
    coords = geometry.get("coordinates")
    if kind == "Polygon":
        exterieur = [(float(x), float(y)) for x, y in coords[0]]
        trous = [[(float(x), float(y)) for x, y in ring] for ring in coords[1:]]
        return [(exterieur, trous)]
    if kind == "MultiPolygon":
        out = []
        for poly in coords:
            exterieur = [(float(x), float(y)) for x, y in poly[0]]
            trous = [[(float(x), float(y)) for x, y in ring] for ring in poly[1:]]
            out.append((exterieur, trous))
        return out
    raise RasterErreur(f"geometrie inconnue: {kind!r}")


def _bbox(cells: Sequence[dict]) -> Tuple[float, float, float, float]:
    xs: List[float] = []
    ys: List[float] = []
    for cell in cells:
        for exterieur, _trous in _anneaux(cell["geometry"]):
            for x, y in exterieur:
                xs.append(x)
                ys.append(y)
    if not xs:
        raise RasterErreur("aucune coordonnée dans le snapshot")
    return min(xs), min(ys), max(xs), max(ys)


def _vers_pixel(
    x: float,
    y: float,
    bounds: Tuple[float, float, float, float],
    largeur: int,
    hauteur: int,
) -> Tuple[int, int]:
    minx, miny, maxx, maxy = bounds
    span_x = max(maxx - minx, 1.0)
    span_y = max(maxy - miny, 1.0)
    px = int(round((x - minx) / span_x * (largeur - 1)))
    py = int(round((maxy - y) / span_y * (hauteur - 1)))
    return px, py


@dataclass(frozen=True)
class Mnt:
    """Modèle numérique de terrain dérivé d'un snapshot. Unités : mètres."""

    altitudes_m: np.ndarray
    population: np.ndarray
    masque_terre: np.ndarray
    bounds_m: Tuple[float, float, float, float]
    tick: int
    seed: int
    cellules: int


def index_des_cellules(
    document: dict, *, largeur: int = 512
) -> Tuple[np.ndarray, Tuple[float, float, float, float], List[dict]]:
    """
    Pose chaque cellule sur une grille et rend l'index des cellules par pixel.

    Le pixel porte le rang de sa cellule (1..N), ou 0 pour la mer. C'est le
    seul endroit du visualisateur qui dessine des polygones : la carte de
    relief et la carte de statistique lisent toutes deux ce même index, donc
    elles ne peuvent pas diverger de géométrie.
    """
    cells = document.get("cells")
    if not isinstance(cells, list) or not cells:
        raise RasterErreur("snapshot sans cellule : échantillon vide")
    if largeur < 8:
        raise RasterErreur("largeur de raster trop petite")

    bounds = _bbox(cells)
    minx, miny, maxx, maxy = bounds
    span_x = max(maxx - minx, 1.0)
    span_y = max(maxy - miny, 1.0)
    hauteur = max(8, int(round(largeur * span_y / span_x)))

    index = Image.new("I", (largeur, hauteur), 0)
    dessin = ImageDraw.Draw(index)

    for i, cell in enumerate(cells, start=1):
        if "geometry" not in cell:
            raise RasterErreur(f"geometrie absente pour cell_id={cell.get('cell_id')}")
        for exterieur, trous in _anneaux(cell["geometry"]):
            pts = [_vers_pixel(x, y, bounds, largeur, hauteur) for x, y in exterieur]
            if len(pts) >= 3:
                dessin.polygon(pts, fill=i)
            for trou in trous:
                pts_trou = [_vers_pixel(x, y, bounds, largeur, hauteur) for x, y in trou]
                if len(pts_trou) >= 3:
                    dessin.polygon(pts_trou, fill=0)

    ids = np.array(index, dtype=np.int32)
    if not bool((ids > 0).any()):
        raise RasterErreur("raster vide : aucune cellule n'a touché un pixel")
    return ids, bounds, cells


def rasteriser(document: dict, *, largeur: int = 512) -> Mnt:
    """Pose chaque cellule sur une grille. Échantillon vide → échec."""
    ids, bounds, cells = index_des_cellules(document, largeur=largeur)
    masque = ids > 0

    altitudes = np.zeros(len(cells) + 1, dtype=np.float32)
    pops = np.zeros(len(cells) + 1, dtype=np.float32)
    for i, cell in enumerate(cells, start=1):
        relief = cell.get("relief")
        if relief not in HAUTEURS_M:
            raise RasterErreur(
                f"relief inconnu {relief!r} pour cell_id={cell.get('cell_id')}"
            )
        altitudes[i] = HAUTEURS_M[relief]
        pops[i] = float(cell.get("population") or 0.0)

    return Mnt(
        altitudes_m=np.take(altitudes, ids),
        population=np.take(pops, ids),
        masque_terre=masque,
        bounds_m=bounds,
        tick=int(document.get("tick", -1)),
        seed=int(document.get("seed", -1)),
        cellules=len(cells),
    )


def apercu_altitude(mnt: Mnt) -> np.ndarray:
    """Image RGBA de contrôle, vue du dessus. Pas un rendu 3D."""
    h = mnt.altitudes_m
    plafond = float(max(HAUTEURS_M.values()))
    t = np.clip(h / plafond, 0.0, 1.0)
    rgba = np.zeros(h.shape + (4,), dtype=np.uint8)
    rgba[..., 0] = (40 + 180 * t).astype(np.uint8)
    rgba[..., 1] = (80 + 100 * (1.0 - t)).astype(np.uint8)
    rgba[..., 2] = (50 + 40 * (1.0 - t)).astype(np.uint8)
    rgba[..., 3] = 255
    rgba[~mnt.masque_terre] = (18, 38, 72, 255)
    return rgba
