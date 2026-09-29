"""Villes historiques : données, géométrie et amorçage."""

import copy
import json
import math
import random

import pytest

from sim.engine import population_soutenable_de, tick
from sim.villes import Ville, attribuer_villes, charger_villes, point_dans_geometrie
from sim.world import World
import sim.world as module_monde


def _carte(polygones):
    return {"projection": "EPSG:3035", "crs": {"geometry": "EPSG:3035"},
            "cellules": [{"cell_id": cid, "geometry": geom} for cid, geom in polygones]}


def _ville(nom, x, y, population=10):
    return {"nom": nom, "latitude": 45.0, "longitude": 2.0,
            "x_m": x, "y_m": y, "population": population,
            "estimation": {"annee": 1400, "incertitude": "environ",
                           "url": "https://exemple.org/table", "passage": "tableau 1"}}


def _document(villes):
    return {"projection": "EPSG:3035", "reference": "EPSG:4326",
            "conversion": "EPSG:4326 vers EPSG:3035", "sources": ["tableau"],
            "villes": villes}


def test_sources_table_et_contre_epreuves(tmp_path):
    villes = charger_villes()
    assert villes
    assert {"Paris", "Londres", "Venise", "Constantinople", "Le Caire",
            "Alexandrie", "Gand", "Bruges", "Milan", "Grenade", "Palerme"} <= {v.nom for v in villes}
    assert all(v.population > 0 and type(v.population) is int for v in villes)
    assert all(math.isfinite(v.x_m) and math.isfinite(v.y_m) for v in villes)
    assert all(v.estimation["annee"] > 0 and v.estimation["incertitude"]
               and v.estimation["url"] and v.estimation["passage"] for v in villes)
    original = _document([_ville("A", 2, 3)])
    alterations = [
        (lambda d: d.update(villes=[]), "villes"),
        (lambda d: d["villes"][0]["estimation"].update(url=""), "url"),
        (lambda d: d["villes"].append(copy.deepcopy(d["villes"][0])), "A"),
        (lambda d: d["villes"][0].update(population=True), "population"),
        (lambda d: d["villes"][0].update(population=-1), "population"),
        (lambda d: d["villes"][0].update(x_m=float("nan")), "x_m"),
        (lambda d: d.update(projection="EPSG:3857"), "projection"),
    ]
    for alterer, champ in alterations:
        doc = copy.deepcopy(original)
        alterer(doc)
        chemin = tmp_path / "villes.json"
        chemin.write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(ValueError, match=champ):
            charger_villes(chemin)


def test_placement_polygones_et_frontieres():
    gauche = {"type": "Polygon", "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]],
                                                     [[2, 2], [4, 2], [4, 4], [2, 4], [2, 2]]]}
    droite = {"type": "MultiPolygon", "coordinates": [
        [[[10, 0], [20, 0], [20, 10], [10, 10], [10, 0]]],
        [[[30, 0], [32, 0], [32, 2], [30, 2], [30, 0]]]]}
    villes = [_ville("dedans", 1, 1), _ville("trou", 3, 3),
              _ville("dehors", 40, 1), _ville("morceau", 31, 1),
              _ville("frontière", 10, 5)]
    for morceaux in ([(2, droite), (1, gauche)], [(1, gauche), (2, droite)]):
        resultat = attribuer_villes(_carte(morceaux), villes)
        assert resultat.placees == {"dedans": 1, "morceau": 2, "frontière": 1}
        assert set(resultat.hors_carte) == {"trou", "dehors"}
    assert point_dans_geometrie(31, 1, droite)
    with pytest.raises(ValueError, match="geometry"):
        attribuer_villes(_carte([(1, None)]), villes)


def test_placement_reel_et_point_exterieur():
    carte = World.lire_carte()
    villes = charger_villes()
    resultat = attribuer_villes(carte, villes)
    assert len(resultat.placees) + len(resultat.hors_carte) == len(villes)
    geometries = {c["cell_id"]: c["geometry"] for c in carte["cellules"]}
    for ville in villes:
        if ville.nom in resultat.placees:
            assert point_dans_geometrie(ville.x_m, ville.y_m, geometries[resultat.placees[ville.nom]])
    deplacee = copy.deepcopy(villes[0].__dict__)
    deplacee["x_m"] = -1e9
    assert deplacee["nom"] in attribuer_villes(carte, [deplacee]).hors_carte


def test_placement_refuse_le_centroide_le_plus_proche():
    long = {"type": "Polygon", "coordinates": [[[0, 0], [1000, 0],
                [1000, 1], [0, 1], [0, 0]]]}
    proche = {"type": "Polygon", "coordinates": [[[10, 5], [20, 5],
                [20, 15], [10, 15], [10, 5]]]}
    assert attribuer_villes(_carte([(1, long), (2, proche)]),
                           [_ville("longue", 1, 0.5)]).placees == {"longue": 1}
    assert math.dist((1, 0.5), (15, 10)) < math.dist((1, 0.5), (500, 0.5))


def test_amorcage_planchers_sommes_et_determinisme():
    carte = World.lire_carte()
    villes = charger_villes()
    placement = attribuer_villes(carte, villes)
    sommes = {}
    for ville in villes:
        if ville.nom in placement.placees:
            cid = placement.placees[ville.nom]
            sommes[cid] = sommes.get(cid, 0) + ville.population
    assert sommes
    monde = World.charger(rng_seed=0, carte_doc=carte)
    assert all(monde.cells[cid].population >= total for cid, total in sommes.items())
    assert monde.to_dict() == World.charger(rng_seed=0, carte_doc=carte).to_dict()
    cid = next(iter(sommes))
    monde.cells[cid].population = 1
    tick(monde, random.Random(0), numero_tick=0)
    assert monde.cells[cid].population < sommes[cid]


def test_amorcage_somme_et_peuplement_preexistant(monkeypatch):
    carte = World.lire_carte()
    cible = charger_villes()[0]
    cid = attribuer_villes(carte, [cible]).placees[cible.nom]
    monkeypatch.setattr(module_monde, "charger_villes", lambda: ())
    rural = World.charger(rng_seed=0, carte_doc=carte)
    peuplement = rural.cells[cid].population

    a = Ville("A", cible.latitude, cible.longitude, cible.x_m, cible.y_m,
              peuplement + 1, cible.estimation)
    b = Ville("B", cible.latitude, cible.longitude, cible.x_m, cible.y_m,
              peuplement + 2, cible.estimation)
    monkeypatch.setattr(module_monde, "charger_villes", lambda: (a, b))
    avec = World.charger(rng_seed=0, carte_doc=carte)
    assert avec.cells[cid].population == a.population + b.population
    assert avec.cells[cid].population > max(a.population, b.population)
    assert all(avec.cells[i].population == rural.cells[i].population
               and avec.cells[i].food_stock_kg == rural.cells[i].food_stock_kg
               for i in rural.cells if i != cid)

    petits = (Ville("A", cible.latitude, cible.longitude, cible.x_m, cible.y_m,
                    1, cible.estimation),
              Ville("B", cible.latitude, cible.longitude, cible.x_m, cible.y_m,
                    1, cible.estimation))
    monkeypatch.setattr(module_monde, "charger_villes", lambda: petits)
    assert World.charger(rng_seed=0, carte_doc=carte).cells[cid].population == peuplement


def test_amorcage_refuse_geometrie_absente_et_ville_exterieure(monkeypatch):
    carte = World.lire_carte()
    ville = charger_villes()[0]
    cid = attribuer_villes(carte, [ville]).placees[ville.nom]
    monkeypatch.setattr(module_monde, "charger_villes", lambda: ())
    rural = World.charger(rng_seed=0, carte_doc=carte).cells[cid].population
    exterieure = Ville(ville.nom, ville.latitude, ville.longitude, -1e9,
                       ville.y_m, ville.population, ville.estimation)
    monkeypatch.setattr(module_monde, "charger_villes", lambda: (exterieure,))
    monde = World.charger(rng_seed=0, carte_doc=carte)
    assert exterieure.nom in monde.attribution_villes.hors_carte
    assert monde.cells[cid].population == rural
    sans_geometrie = copy.deepcopy(carte)
    del sans_geometrie["cellules"][0]["geometry"]
    with pytest.raises(ValueError, match="geometry"):
        World.charger(rng_seed=0, carte_doc=sans_geometrie)
