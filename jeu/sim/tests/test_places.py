"""Lot #393 — chaque lieu a sa place dans sa cellule.

La preuve : chaque point est dans le polygone de sa cellule ; le bourg de chaque seigneurie
de départ est à moins d'un kilomètre de son siège ; deux lieux d'une cellule respectent la
distance minimale ; mêmes carte et cellule, mêmes points. Contre-épreuve : une géométrie
absente est refusée en nommant la cellule, jamais remplacée par un centroïde. Le centroïde
d'une cellule en croissant tombe dehors : le bourg prend alors un point intérieur (décision
A du propriétaire, le 9 octobre 2026).
"""

import itertools
import math
import random
from collections import Counter

import pytest

import sim.constants as _constantes
from sim.engine import tick
from sim.lieux import LieuxInvalides, lieux_de_cellule
from sim.places import (CENTROIDE, INTERIEUR, SIEGE, TIRAGE, VILLE, distance_km, places_de_cellule,
                        places_du_monde)
from sim.projection import deprojeter_epsg3035, projeter_epsg3035
from sim.seigneuries import cellule_du_siege, charger_seigneuries, identifiant_de_seigneurie
from sim.villes import point_dans_geometrie
from sim.world import World

UN_KM_M = 1000.0
TOLERANCE_M = 0.01
TICKS = 5


@pytest.fixture(scope="module")
def monde():
    return World.charger(rng_seed=0)


@pytest.fixture(scope="module")
def places(monde):
    return places_du_monde(monde)


def test_chaque_lieu_a_sa_place_dans_sa_cellule(monde, places):
    lieux = points = 0
    for cid, cellule in monde.cells.items():
        attendus = lieux_de_cellule(cid, cellule.area_km2)
        assert len(places[cid]) == len(attendus) > 0, f"cell_id {cid} : {len(places[cid])} places pour {len(attendus)} lieux"
        geometrie = monde.carte[cid]["geometry"]
        for rang, place in enumerate(places[cid]):
            assert point_dans_geometrie(place.x_m, place.y_m, geometrie), f"lieu ({cid}, {rang}) hors de sa cellule"
            points += 1
        lieux += len(attendus)
    assert points == lieux == sum(len(v) for v in places.values()) > 0
    origines = Counter(place.origine for v in places.values() for place in v)
    # Chaque règle sert au moins une fois : sinon sa preuve serait vide.
    assert all(origines[o] > 0 for o in (SIEGE, VILLE, CENTROIDE, INTERIEUR, TIRAGE)), origines
    assert origines[TIRAGE] == lieux - len(places), "seul le bourg ne vient pas du tirage"


def test_le_bourg_d_une_seigneurie_de_depart_est_a_son_siege(monde, places):
    seigneuries = charger_seigneuries()
    assert seigneuries
    for s in seigneuries:
        cid = cellule_du_siege(s, monde.carte)
        assert monde.cells[cid].lieux[0].maitre == identifiant_de_seigneurie(s.id), f"{s.nom} ne tient pas le bourg de sa cellule"
        bourg = places[cid][0]
        ecart = math.hypot(bourg.x_m - s.siege.x_m, bourg.y_m - s.siege.y_m)
        assert ecart < UN_KM_M and bourg.origine == SIEGE, f"{s.nom} : bourg à {ecart:.0f} m de {s.siege.nom}"


def test_deux_lieux_d_une_cellule_sont_assez_ecartes(monde, places):
    paires = 0
    for cid, cellule in monde.cells.items():
        surfaces = [lieu.surface_km2 for lieu in lieux_de_cellule(cid, cellule.area_km2)]
        ecart_km = _constantes.ECART_MIN_ENTRE_LIEUX * math.sqrt(surfaces[-1])
        for a, b in itertools.combinations(places[cid], 2):
            assert distance_km(a, b) >= ecart_km, f"cell_id {cid} : deux lieux à {distance_km(a, b):.2f} km, il en faut {ecart_km:.2f}"
            paires += 1
    assert paires > 0


def test_memes_carte_et_cellule_memes_points(monde, places):
    assert places_du_monde(World.charger(rng_seed=0)) == places
    assert places_du_monde(World.charger(rng_seed=42)) == places, "la graine du monde déplace les lieux"
    rng = random.Random(0)
    autre = World.charger(rng_seed=0)
    for numero in range(TICKS):
        tick(autre, rng, numero)
    assert places_du_monde(autre) == places, "le tick déplace les lieux"
    # Une cellule ne dépend que d'elle-même : la recalculer seule rend les mêmes points.
    cid = next(c for c, v in places.items() if len(v) > 1)
    seule = places_de_cellule(cid, monde.carte[cid], [l.surface_km2 for l in lieux_de_cellule(cid, monde.cells[cid].area_km2)],
                              siege=(places[cid][0].x_m, places[cid][0].y_m))
    assert seule[1:] == places[cid][1:]


@pytest.mark.parametrize("enregistrement", [None, {}, {"geometry": None, "centroid": {"x_m": 0.0, "y_m": 0.0}},
                                            {"geometry": {"type": "Polygon", "coordinates": []}, "centroid": {"x_m": 0.0, "y_m": 0.0}}])
def test_une_geometrie_absente_est_refusee_en_nommant_la_cellule(enregistrement):
    with pytest.raises(LieuxInvalides, match="cell_id 4242 : géométrie absente"):
        places_de_cellule(4242, enregistrement, [1000.0, 1000.0])


def _croissant():
    """Un C ouvert à l'est, de 100 km de côté : son centroïde tombe dans l'ouverture."""
    exterieur = [(0, 0), (100_000, 0), (100_000, 20_000), (20_000, 20_000), (20_000, 80_000),
                 (100_000, 80_000), (100_000, 100_000), (0, 100_000), (0, 0)]
    return {"geometry": {"type": "Polygon", "coordinates": [[list(p) for p in exterieur]]},
            "centroid": {"x_m": 50_000.0, "y_m": 50_000.0}}


def test_un_centroide_hors_du_polygone_donne_un_point_interieur():
    croissant = _croissant()
    assert not point_dans_geometrie(50_000.0, 50_000.0, croissant["geometry"]), "le témoin a son centroïde dedans"
    places = places_de_cellule(7, croissant, [1000.0] * 5)
    assert places[0].origine == INTERIEUR
    assert all(point_dans_geometrie(p.x_m, p.y_m, croissant["geometry"]) for p in places)
    # Le point intérieur est sur la ligne du centroïde quand elle traverse la cellule.
    assert places[0].y_m == 50_000.0 and 0 < places[0].x_m < 20_000


def test_le_siege_puis_la_ville_puis_le_centroide():
    carre = {"geometry": {"type": "Polygon", "coordinates": [[[0, 0], [60_000, 0], [60_000, 60_000], [0, 60_000], [0, 0]]]},
             "centroid": {"x_m": 30_000.0, "y_m": 30_000.0}}
    siege, ville, dehors = (10_000.0, 12_000.0), (40_000.0, 45_000.0), (90_000.0, 90_000.0)
    bourg = places_de_cellule(1, carre, [1000.0], siege=siege, ville=ville)[0]
    assert (bourg.x_m, bourg.y_m, bourg.origine) == (*siege, SIEGE)
    assert places_de_cellule(1, carre, [1000.0], siege=dehors, ville=ville)[0].origine == VILLE
    assert places_de_cellule(1, carre, [1000.0], siege=None, ville=dehors)[0].origine == CENTROIDE
    sans_centre = {"geometry": carre["geometry"]}
    with pytest.raises(LieuxInvalides, match="cell_id 1 : centroïde absent"):
        places_de_cellule(1, sans_centre, [1000.0])


def test_une_cellule_trop_petite_pour_ses_lieux_est_refusee():
    minuscule = {"geometry": {"type": "Polygon", "coordinates": [[[0, 0], [100, 0], [100, 100], [0, 100], [0, 0]]]},
                 "centroid": {"x_m": 50.0, "y_m": 50.0}}
    with pytest.raises(LieuxInvalides, match="cell_id 9 : pas de place pour le lieu 1"):
        places_de_cellule(9, minuscule, [1000.0, 1000.0])


def test_la_latitude_et_la_longitude_sont_celles_du_point(places):
    for v in places.values():
        for place in v:
            x, y = projeter_epsg3035(place.latitude, place.longitude)
            assert math.hypot(x - place.x_m, y - place.y_m) < TOLERANCE_M


def test_la_projection_inverse_rend_le_point():
    rng = random.Random(0)
    for _ in range(500):
        latitude, longitude = rng.uniform(25, 72), rng.uniform(-15, 45)
        x, y = projeter_epsg3035(latitude, longitude)
        retour = deprojeter_epsg3035(x, y)
        assert math.hypot(*(a - b for a, b in zip(projeter_epsg3035(*retour), (x, y)))) < TOLERANCE_M
        assert abs(retour[0] - latitude) < 1e-7 and abs(retour[1] - longitude) < 1e-7
    assert deprojeter_epsg3035(4_321_000.0, 3_210_000.0) == (52.0, 10.0)


def test_la_distance_entre_deux_lieux_se_derive_de_leurs_points(places):
    a, b = next(v for v in places.values() if len(v) > 1)[:2]
    assert distance_km(a, b) == distance_km(b, a) == math.hypot(a.x_m - b.x_m, a.y_m - b.y_m) / 1000.0 > 0
    assert distance_km(a, a) == 0
