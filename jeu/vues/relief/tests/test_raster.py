"""Invariants du raster : échantillon vide, relief inconnu, pixels de terre."""

from __future__ import annotations

import pytest

from vues.relief.raster import (
    HAUTEURS_M, RasterErreur, index_des_cellules, index_des_lieux, rasteriser,
)


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


def _carre(x0, x1):
    return {"type": "Polygon", "coordinates": [[(x0, 0), (x1, 0), (x1, 20), (x0, 20), (x0, 0)]]}


def _deux_cellules():
    """Deux carrés côte à côte ; la cellule 7 porte deux lieux, la 3 en porte un."""
    cells = [_cellule(7, "plaine", [(0, 0), (20, 0), (20, 20), (0, 20), (0, 0)]),
             _cellule(3, "plaine", [(20, 0), (40, 0), (40, 20), (20, 20), (20, 0)])]
    formes = {"cells": [
        {"cell_id": 3, "contour": _carre(20, 40), "lieux": [{"rang": 0, "contour": _carre(20, 40)}]},
        {"cell_id": 7, "contour": _carre(0, 20),
         "lieux": [{"rang": 1, "contour": _carre(10, 20)}, {"rang": 0, "contour": _carre(0, 10)}]},
    ]}
    return {"cells": cells}, formes


def test_index_des_cellules_suit_les_contours_servis():
    document, formes = _deux_cellules()
    formes["cells"][1]["contour"] = _carre(0, 10)
    brut, bornes, _ = index_des_cellules(document, largeur=64)
    servi, bornes_servies, _ = index_des_cellules(document, largeur=64, formes=formes)
    assert bornes == bornes_servies
    assert (brut == 1).sum() > (servi == 1).sum() > 0
    assert (brut == 2).sum() == (servi == 2).sum()


def test_cellule_absente_des_formes_est_refusee_par_son_cell_id():
    document, formes = _deux_cellules()
    formes["cells"] = [c for c in formes["cells"] if c["cell_id"] != 3]
    with pytest.raises(RasterErreur, match="cell_id=3"):
        index_des_cellules(document, largeur=64, formes=formes)
    with pytest.raises(RasterErreur, match="cell_id=3"):
        index_des_lieux(document, formes, largeur=64)


def test_index_des_lieux_numerote_cellule_apres_cellule_puis_par_rang():
    document, formes = _deux_cellules()
    # Le lieu de la cellule 3 laisse sa moitié est à la mer : le cadre reste celui de la géométrie brute.
    formes["cells"][0]["lieux"][0]["contour"] = _carre(20, 30)
    index, bornes, lieux = index_des_lieux(document, formes, largeur=64)
    assert lieux == [(7, 0), (7, 1), (3, 0)]
    assert bornes == index_des_cellules(document, largeur=64)[1]
    assert set(index.reshape(-1).tolist()) == {0, 1, 2, 3}
    ligne = index[index.shape[0] // 2]
    assert ligne[3] == 1 and ligne[24] == 2 and ligne[40] == 3 and ligne[60] == 0
