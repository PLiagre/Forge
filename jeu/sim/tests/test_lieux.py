"""Preuves du découpage dérivé des cellules en lieux."""

import copy
import dataclasses
from fractions import Fraction
import json
import math

import pytest

import sim.constants as _constantes
from sim.lieux import Lieu, LieuxInvalides, lieux_de_cellule, lieux_depuis_monde, lieux_par_cellule
from sim.model import _NoBadSpatialField
from sim.world import World


def test_nombre_de_lieux_suit_la_surface(monkeypatch):
    monde = World.charger(0)
    vue = lieux_depuis_monde(monde)
    assert vue and set(vue) == set(monde.cells)
    assert list(vue) == sorted(vue)
    for cell_id, cellule in monde.cells.items():
        attendus = max(1, math.floor(cellule.area_km2 / _constantes.SURFACE_KM2_PAR_LIEU))
        assert len(vue[cell_id]) == attendus >= 1
    lieux_total = sum(map(len, vue.values()))
    cellules_seules = sum(len(lieux) == 1 for lieux in vue.values())
    cellules_multiples = sum(len(lieux) > 1 for lieux in vue.values())
    monkeypatch.setattr(
        _constantes, "SURFACE_KM2_PAR_LIEU", _constantes.SURFACE_KM2_PAR_LIEU * 2
    )
    total_doublé = sum(map(len, lieux_depuis_monde(monde).values()))
    print(f"lieux_total={lieux_total}, cellules_seules={cellules_seules}, "
          f"cellules_multiples={cellules_multiples}, total_doublé={total_doublé}")
    assert lieux_total > len(monde.cells)
    assert cellules_seules > 0 and cellules_multiples > 0
    assert total_doublé < lieux_total


def test_surface_des_lieux_fait_la_cellule_exactement():
    monde = World.charger(0)
    vue = lieux_depuis_monde(monde)
    assert vue and set(vue) == set(monde.cells)
    cellules_exactes = 0
    partages_naifs_inexacts = 0
    for cell_id, lieux in vue.items():
        surface = monde.cells[cell_id].area_km2
        assert lieux and all(lieu.surface_km2 > 0 for lieu in lieux)
        assert sum(Fraction(lieu.surface_km2) for lieu in lieux) == Fraction(surface)
        assert sum(lieu.surface_km2 for lieu in lieux) == surface
        assert all(lieu.surface_km2 == math.floor(lieu.surface_km2) for lieu in lieux[1:])
        assert len({lieu.surface_km2 for lieu in lieux[1:]}) <= 1
        assert lieux[0].surface_km2 == max(lieu.surface_km2 for lieu in lieux)
        cellules_exactes += 1
        partage_naif = [surface / len(lieux)] * len(lieux)
        partages_naifs_inexacts += sum(map(Fraction, partage_naif)) != Fraction(surface)
    print(f"cellules_exactes={cellules_exactes}, "
          f"partages_naifs_inexacts={partages_naifs_inexacts}")
    assert cellules_exactes == len(monde.cells) > 0
    assert partages_naifs_inexacts > 0


def test_identite_et_bourg_unique():
    def champs_attendus(classe):
        return {champ.name for champ in dataclasses.fields(classe)} == {
            "cell_id", "rang", "surface_km2"
        }

    @dataclasses.dataclass(frozen=True)
    class LieuAvecCle(_NoBadSpatialField):
        cell_id: int
        rang: int
        surface_km2: float
        lieu_id: int

    assert champs_attendus(Lieu)
    assert not champs_attendus(LieuAvecCle)
    assert issubclass(Lieu, _NoBadSpatialField)
    with pytest.raises(dataclasses.FrozenInstanceError):
        Lieu(7, 0, 1.0).rang = 1

    monde = World.charger(0)
    vue = lieux_depuis_monde(monde)
    assert vue and set(vue) == set(monde.cells)
    couples = [(lieu.cell_id, lieu.rang) for lieux in vue.values() for lieu in lieux]
    for cell_id, lieux in vue.items():
        assert [lieu.rang for lieu in lieux] == list(range(len(lieux)))
        assert all(lieu.cell_id == cell_id for lieu in lieux)
        assert sum(lieu.est_bourg for lieu in lieux) == 1
        assert lieux[0].est_bourg
        assert all(not lieu.est_bourg for lieu in lieux[1:])
    lieux_total = sum(map(len, vue.values()))
    print(f"lieux_total={lieux_total}, couples_distincts={len(set(couples))}, "
          f"bourgs={sum(lieu.est_bourg for lieux in vue.values() for lieu in lieux)}")
    assert len(couples) == len(set(couples)) == lieux_total > 0


def test_refus_des_surfaces_absentes_ou_invalides(monkeypatch):
    surfaces_invalides = [None, True, "1200", float("nan"), float("inf"), 0, -5.0]
    refus_observés = 0
    for surface in surfaces_invalides:
        with pytest.raises(LieuxInvalides, match="7"):
            lieux_par_cellule({7: surface})
        refus_observés += 1
    with monkeypatch.context() as contexte:
        for valeur in (0.5, float("nan"), float("inf"), True, "1000"):
            contexte.setattr(_constantes, "SURFACE_KM2_PAR_LIEU", valeur)
            with pytest.raises(LieuxInvalides, match="7"):
                lieux_de_cellule(7, 1200.0)
            refus_observés += 1

    monde = copy.deepcopy(World.charger(0))
    plus_petite = min(monde.cells, key=lambda identifiant: monde.cells[identifiant].area_km2)
    monde.cells[plus_petite].area_km2 = None
    with pytest.raises(LieuxInvalides, match=str(plus_petite)):
        lieux_depuis_monde(monde)
    refus_observés += 1
    for surface in (1200.0, 1, 0.3):
        lieux = lieux_par_cellule({7: surface})[7]
        assert len(lieux) == 1 and lieux[0].surface_km2 == surface
        assert lieux[0].est_bourg
    print(f"refus_observés={refus_observés}, surfaces_valides=3")
    assert refus_observés == len(surfaces_invalides) + 5 + 1 > 0


def test_vue_pure_que_le_tick_ne_lit_pas():
    monde = World.charger(0)
    avant = json.dumps(monde.to_dict(), sort_keys=True)
    attributs_avant = {cell_id: vars(cellule).copy() for cell_id, cellule in monde.cells.items()}
    premiere = lieux_depuis_monde(monde)
    seconde = lieux_depuis_monde(monde)
    apres = json.dumps(monde.to_dict(), sort_keys=True)
    attributs_apres = {cell_id: vars(cellule).copy() for cell_id, cellule in monde.cells.items()}
    print(f"vues_identiques={premiere == seconde}, monde_inchangé={avant == apres}, "
          f"attributs_inchangés={attributs_avant == attributs_apres}")
    assert premiere and set(premiere) == set(monde.cells)
    assert premiere == seconde
    assert avant == apres
    assert attributs_avant == attributs_apres
