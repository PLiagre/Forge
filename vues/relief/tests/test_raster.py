"""Invariants du raster : échantillon vide, relief inconnu, pixels de terre."""

from __future__ import annotations

import pytest

from vues.relief.raster import HAUTEURS_M, RasterErreur, rasteriser


def _cellule(cell_id: int, relief: str, ring):
    return {
        "cell_id": cell_id,
        "relief": relief,
        "population": 10,
        "geometry": {"type": "Polygon", "coordinates": [ring]},
    }


def test_snapshot_vide_echoue():
    with pytest.raises(RasterErreur, match="vide"):
        rasteriser({"cells": []}, largeur=32)


def test_relief_inconnu_est_un_refus():
    cells = [
        _cellule(1, "volcan_invente", [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]),
    ]
    with pytest.raises(RasterErreur, match="inconnu"):
        rasteriser({"cells": cells, "tick": 0, "seed": 0}, largeur=32)


def test_chaque_classe_pose_son_altitude():
    # Un carré par classe, côte à côte, assez grand pour toucher des pixels.
    classes = list(HAUTEURS_M)
    cells = []
    for i, nom in enumerate(classes):
        x0 = i * 20.0
        ring = [(x0, 0), (x0 + 18, 0), (x0 + 18, 18), (x0, 18), (x0, 0)]
        cells.append(_cellule(i, nom, ring))
    mnt = rasteriser({"cells": cells, "tick": 0, "seed": 0}, largeur=64)
    assert mnt.cellules == len(classes)
    assert bool(mnt.masque_terre.any())
    for nom, metres in HAUTEURS_M.items():
        assert metres in set(mnt.altitudes_m.reshape(-1).tolist())
