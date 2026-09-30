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


import random

from sim.engine import tick
from sim.lieux import LieuInconnu, lieu_du_monde


def test_chaque_lieu_se_retrouve_par_son_couple():
    monde = World.charger(0)
    vue = lieux_depuis_monde(monde)
    assert vue
    lieux_retrouvés = 0
    for lieux in vue.values():
        for lieu in lieux:
            assert lieu_du_monde(monde, lieu.cell_id, lieu.rang) == lieu
            lieux_retrouvés += 1
    print(f"lieux_retrouvés={lieux_retrouvés}")
    assert lieux_retrouvés == sum(map(len, vue.values())) > 0

    cellules = [cid for cid, lieux in vue.items() if len(lieux) >= 2]
    assert cellules
    c = min(cellules)
    n = len(vue[c])
    # L'indexation naïve rend le dernier lieu ; le rang négatif est refusé.
    dernier = lieux_depuis_monde(monde)[c][-1]
    assert isinstance(dernier, Lieu) and dernier.cell_id == c
    with pytest.raises(LieuInconnu):
        lieu_du_monde(monde, c, -1)
    with pytest.raises(LieuInconnu):
        lieu_du_monde(monde, c, n)


def test_refus_du_couple():
    monde = World.charger(0)
    c = min(monde.cells)
    couples_mal_formes = [
        (True, 0),
        (c, True),
        (c, False),
        (str(c), 0),
        (c, "0"),
        (float(c), 0),
        (c, 0.0),
        (None, 0),
        (c, None),
    ]
    couples_inconnus = [
        (max(monde.cells) + 1, 0),
        (c, -1),
    ]
    refus_observés = 0
    for cell_id, rang in couples_mal_formes:
        with pytest.raises(LieuxInvalides) as info:
            lieu_du_monde(monde, cell_id, rang)
        assert not isinstance(info.value, LieuInconnu)
        message = str(info.value)
        assert repr(cell_id) in message and repr(rang) in message
        refus_observés += 1
    for cell_id, rang in couples_inconnus:
        with pytest.raises(LieuInconnu) as info:
            lieu_du_monde(monde, cell_id, rang)
        message = str(info.value)
        assert repr(cell_id) in message and repr(rang) in message
        refus_observés += 1
    print(f"refus_observés={refus_observés}")
    assert refus_observés == len(couples_mal_formes) + len(couples_inconnus) > 0

    copie = copy.deepcopy(monde)
    copie.cells[c].area_km2 = None
    with pytest.raises(LieuxInvalides) as info:
        lieu_du_monde(copie, c, 0)
    assert str(c) in str(info.value)

    bourg = lieu_du_monde(monde, c, 0)
    assert bourg.est_bourg and bourg.cell_id == c and bourg.rang == 0
    with pytest.raises(LieuxInvalides) as info:
        lieu_du_monde(monde, True, 0)
    assert not isinstance(info.value, LieuInconnu)


def test_le_tick_ne_detache_pas_un_lieu():
    monde = World.charger(0)
    avant = lieux_depuis_monde(monde)
    populations = {
        cid: cellule.population for cid, cellule in monde.cells.items()
    }
    alea = random.Random(0)
    for numero in range(30):
        tick(monde, alea, numero_tick=numero)
    apres = lieux_depuis_monde(monde)
    cellules_changées = sum(
        monde.cells[cid].population != populations[cid] for cid in monde.cells
    )
    assert apres == avant
    assert cellules_changées > 0

    copie = copy.deepcopy(monde)
    plus_grande = max(
        copie.cells, key=lambda cid: copie.cells[cid].area_km2
    )
    copie.cells[plus_grande].area_km2 /= 2
    vue_rognee = lieux_depuis_monde(copie)
    cellules_détachées = sum(
        vue_rognee[cid] != apres[cid] for cid in apres
    )
    print(
        f"cellules_changées={cellules_changées}, "
        f"cellules_détachées={cellules_détachées}"
    )
    assert cellules_détachées == 1


def test_ni_la_graine_ni_l_ordre_ne_changent_l_identite():
    monde_0 = World.charger(0)
    monde_1 = World.charger(1)
    vue_0 = lieux_depuis_monde(monde_0)
    vue_1 = lieux_depuis_monde(monde_1)
    assert vue_0 == vue_1
    populations_différentes = sum(
        monde_0.cells[cid].population != monde_1.cells[cid].population
        for cid in monde_0.cells
    )
    assert populations_différentes > 0

    copie = copy.deepcopy(monde_0)
    copie.cells = {
        cle: copie.cells[cle] for cle in reversed(tuple(monde_0.cells))
    }
    vue_inverse = lieux_depuis_monde(copie)
    assert vue_inverse == vue_0
    assert list(vue_inverse) == list(vue_0)
    for lieux in vue_0.values():
        for lieu in lieux:
            assert lieu_du_monde(monde_0, lieu.cell_id, lieu.rang) == lieu
            assert lieu_du_monde(copie, lieu.cell_id, lieu.rang) == lieu

    def numeros_globaux(world):
        numeros = {}
        position = 0
        for cell_id, cellule in world.cells.items():
            lieux = lieux_de_cellule(
                cell_id, getattr(cellule, "area_km2", None)
            )
            for lieu in lieux:
                numeros[(lieu.cell_id, lieu.rang)] = position
                position += 1
        return numeros

    origine = numeros_globaux(monde_0)
    inverse = numeros_globaux(copie)
    numéros_globaux_déplacés = sum(
        origine[couple] != inverse[couple] for couple in origine
    )
    print(
        f"populations_différentes={populations_différentes}, "
        f"numéros_globaux_déplacés={numéros_globaux_déplacés}"
    )
    assert numéros_globaux_déplacés > 0


def test_la_constante_renumerote(monkeypatch):
    monde = World.charger(0)
    vue = lieux_depuis_monde(monde)
    candidats = [cid for cid, lieux in vue.items() if len(lieux) >= 3]
    assert candidats
    c = min(candidats)
    n = len(vue[c])
    lieu = lieu_du_monde(monde, c, n - 1)
    assert lieu.cell_id == c and lieu.rang == n - 1
    monkeypatch.setattr(
        _constantes,
        "SURFACE_KM2_PAR_LIEU",
        _constantes.SURFACE_KM2_PAR_LIEU * 2,
    )
    with pytest.raises(LieuInconnu):
        lieu_du_monde(monde, c, n - 1)
    n_apres = len(lieux_de_cellule(c, monde.cells[c].area_km2))
    print(f"lieux_avant={n}, lieux_apres={n_apres}")
    assert n_apres < n
