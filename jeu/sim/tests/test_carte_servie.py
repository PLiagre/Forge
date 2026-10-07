"""Carte servie et terres actuelles : preuves sur les données et contre-épreuves."""

import copy
import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from http import HTTPStatus
import math
import random
import threading

import pytest

from sim.carte_servie import (
    SOMMETS_MIN_ANNEAU, TOLERANCE_CONTOUR_M, contour_servi,
    point_temoin, simplifier_anneau,
)
from sim.engine import tick
from sim.puissances import PuissanceInvalide
from sim.seigneuries import SeigneurieInconnue, charger_seigneuries, fiche_de_seigneurie
from sim.service import ServeurMonde
from sim.snapshot_export import SnapshotExportError, _fiche_document, _round_tree, build_snapshot_document
from sim.tests.test_monde import lancer_service, requete_service
from sim.villes import charger_villes, point_dans_geometrie
from sim.world import World


@pytest.fixture(scope="module")
def monde():
    monde = World.charger(0)
    rng = random.Random(0)
    for numero in range(3):
        tick(monde, rng, numero)
    return monde


@pytest.fixture(scope="module")
def photographie(monde):
    copie = copy.deepcopy(monde)
    copie.maison_du_joueur = next(s.id for s in charger_seigneuries() if s.nom == "Duché de Bar")
    return build_snapshot_document(copie, 0, 3)


def _lire(port, chemin, methode="GET"):
    statut, document, octets = requete_service(port, chemin, methode)
    assert statut == HTTPStatus.OK, document
    return document, octets


def _verifier_cellules(document, ids):
    assert ids
    assert document["cell_count"] == len(document["cells"]) > 0
    assert [c["cell_id"] for c in document["cells"]] == ids


def test_carte_une_fois(monde, photographie):
    ids = sorted(c["cell_id"] for c in World.lire_carte()["cellules"])
    photos = {c["cell_id"]: c for c in photographie["cells"]}
    villes = {v.nom: v for v in charger_villes()}
    with lancer_service(0) as port:
        document, octets = _lire(port, "/carte")
        _verifier_cellules(document, ids)
        assert set(document) == {"crs", "tolerance_m", "version", "cell_count", "cells", "villes_hors_carte"}
        assert document["crs"] == "EPSG:3035"
        assert document["tolerance_m"] == TOLERANCE_CONTOUR_M
        assert document["version"] == monde.carte_meta["version"]
        assert document["villes_hors_carte"] == photographie["villes_hors_carte"]
        for cellule in document["cells"]:
            cid = cellule["cell_id"]
            assert set(cellule) == {"cell_id", "contour", "relief", "puissance", "maison", "villes"}
            assert cellule["relief"] == monde.carte[cid]["relief"]
            for champ in ("puissance", "maison"):
                assert cellule[champ] == photos[cid][champ]
            assert [{k: v[k] for k in ("nom", "population")} for v in cellule["villes"]] == photos[cid]["villes"]
            for ville in cellule["villes"]:
                assert set(ville) == {"nom", "population", "x_m", "y_m"}
                assert (ville["x_m"], ville["y_m"]) == (villes[ville["nom"]].x_m, villes[ville["nom"]].y_m)
        _lire(port, "/tick?n=1", "POST")
        assert _lire(port, "/carte")[1] == octets
    for cellules in (document["cells"][:-1], document["cells"] + document["cells"][:1]):
        with pytest.raises(AssertionError):
            _verifier_cellules(document | {"cells": cellules, "cell_count": len(cellules)}, ids)


def _polygones(geometrie):
    return [geometrie["coordinates"]] if geometrie["type"] == "Polygon" else geometrie["coordinates"]


def _distance_corde(point, debut, fin):
    dx, dy = fin[0] - debut[0], fin[1] - debut[1]
    longueur = math.hypot(dx, dy)
    if longueur == 0:
        return math.dist(point, debut)
    return abs(dx * (debut[1] - point[1]) - (debut[0] - point[0]) * dy) / longueur


def _verifier_distance(original, servi):
    assert original and servi and len(original) == len(servi)
    for anneaux, reduits in zip(original, servi):
        assert len(anneaux) == len(reduits) > 0
        for anneau, reduit in zip(anneaux, reduits):
            arrondis = [[round(x), round(y)] for x, y in anneau]
            assert reduit[0] == reduit[-1] == arrondis[0]
            assert len(reduit) >= SOMMETS_MIN_ANNEAU
            indices, prochain = [0], 1
            for sommet in reduit[1:-1]:
                while prochain < len(arrondis) - 1 and arrondis[prochain] != sommet:
                    prochain += 1
                assert prochain < len(arrondis) - 1, "sommet inventé ou ordre changé"
                indices.append(prochain)
                prochain += 1
            indices.append(len(anneau) - 1)
            for debut, fin in zip(indices, indices[1:]):
                for point in anneau[debut + 1:fin]:
                    assert _distance_corde(point, arrondis[debut], arrondis[fin]) <= TOLERANCE_CONTOUR_M + 1, "distance à la corde dépassée"


def _verifier_temoin(cellule, contour):
    assert point_dans_geometrie(*point_temoin(cellule), contour), "point témoin perdu"


def test_contour(monde, capsys):
    with lancer_service(0) as port:
        document, _ = _lire(port, "/carte")
    servis = {c["cell_id"]: c["contour"] for c in document["cells"]}
    assert set(servis) == set(monde.carte) and servis
    total_original, total_servi, centroides = 0, 0, 0
    sans_garde, trop_loin = [], []
    for cid, cellule in sorted(monde.carte.items()):
        contour = servis[cid]
        assert contour["type"] == "MultiPolygon"
        original = _polygones(cellule["geometry"])
        _verifier_distance(original, contour["coordinates"])
        total_original += sum(len(a) for p in original for a in p)
        total_servi += sum(len(a) for p in contour["coordinates"] for a in p)
        temoin = point_temoin(cellule)
        _verifier_temoin(cellule, contour)
        centre = (cellule["centroid"]["x_m"], cellule["centroid"]["y_m"])
        dedans = point_dans_geometrie(*centre, cellule["geometry"])
        assert (temoin == centre) == dedans
        centroides += dedans
        brut = [[simplifier_anneau(a, TOLERANCE_CONTOUR_M) for a in p] for p in original]
        if any(len(a) < SOMMETS_MIN_ANNEAU for p in brut for a in p) or not point_dans_geometrie(*temoin, {"type": "MultiPolygon", "coordinates": brut}):
            sans_garde.append(cid)
        grossier = [[simplifier_anneau(a, 5 * TOLERANCE_CONTOUR_M) for a in p] for p in original]
        try:
            _verifier_distance(original, grossier)
        except AssertionError as exc:
            # La contre-épreuve doit dépasser la distance, pas seulement effondrer un anneau.
            if "distance à la corde" in str(exc):
                trop_loin.append(cid)
    assert total_servi < total_original
    assert centroides > 0 and sans_garde and trop_loin
    voisins_perdus = [a for a in monde.adjacency if a["kind"] == "land-land"
                      and not point_dans_geometrie(*point_temoin(monde.carte[a["a"]]), servis[a["b"]])]
    assert voisins_perdus
    voisine = voisins_perdus[0]
    with pytest.raises(AssertionError, match="point témoin perdu"):
        _verifier_temoin(monde.carte[voisine["a"]], servis[voisine["b"]])
    print(f"Centroïdes conservés : {centroides}/{len(servis)} ; sommets : {total_servi}/{total_original}")
    with capsys.disabled():
        print(capsys.readouterr().out.strip())


def test_departs(monde, photographie):
    ids = sorted(s.id for s in charger_seigneuries())
    assert ids
    references = [_round_tree(_fiche_document(fiche_de_seigneurie(i, monde))) for i in ids]
    with lancer_service(0) as port:
        _lire(port, "/tick?n=3", "POST")
        document, _ = _lire(port, "/departs")
        assert set(document) == {"tick", "date", "departs"}
        assert document["tick"] == 3 and document["date"] == monde.date_simulation
        assert [f["id"] for f in document["departs"]] == ids
        assert document["departs"] == references
        assert next(f for f in document["departs"] if f["nom"] == "Duché de Bar") == photographie["terre_choisie"]
        _lire(port, "/tick?n=1", "POST")
        actuelles, _ = _lire(port, "/departs")
        assert actuelles["tick"] == 4
        assert any(a["habitants"] != b["habitants"] for a, b in zip(actuelles["departs"], references))


def test_departs_zab():
    from sim.intentions import deposer_intention

    monde = World.charger(0)
    terres = charger_seigneuries()
    ids = [s.id for s in terres]
    assert len(ids) == 6 and ids == sorted(ids)
    zab = next(s for s in terres if s.nom == "Émirat du Zab")
    rng = random.Random(0)
    deposer_intention(monde, {"type": "choisir_depart", "seigneurie": zab.id})
    with lancer_service(0) as port:
        intention = json.dumps({"type": "choisir_depart", "seigneurie": zab.id}).encode("utf-8")
        assert requete_service(port, "/intention", "POST", intention)[0] == HTTPStatus.OK
        assert monde.maison_du_joueur is None
        for numero in range(2):
            tick(monde, rng, numero)
            _lire(port, "/tick?n=1", "POST")
            avant = copy.deepcopy(monde.to_dict())
            doc, _ = _lire(port, "/departs")
            photo = build_snapshot_document(monde, 0, numero + 1)
            fiche = fiche_de_seigneurie(zab.id, monde)
            assert doc["tick"] == photo["tick"] and doc["date"] == monde.date_simulation
            assert [f["id"] for f in doc["departs"]] == ids
            servie = next(f for f in doc["departs"] if f["id"] == zab.id)
            assert servie == photo["terre_choisie"] == _round_tree(_fiche_document(fiche))
            assert servie["habitants"] == monde.cells[fiche.cell_id].population
            assert monde.to_dict() == avant
            sans_zab = [f for f in doc["departs"] if f["id"] != zab.id]
            with pytest.raises(AssertionError):
                assert [f["id"] for f in sans_zab] == ids


def test_contour_cas_geometriques():
    anneau = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
    assert simplifier_anneau(anneau, 0) == anneau
    assert simplifier_anneau(tuple(anneau), 0) == anneau
    assert simplifier_anneau(anneau, 10) == [[0, 0], [10, 10], [0, 0]]
    cellule = {"cell_id": 1, "centroid": {"x_m": 5, "y_m": 5},
               "geometry": {"type": "Polygon", "coordinates": [anneau]}}
    assert contour_servi(cellule)["coordinates"] == [[anneau]]
    trou = [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]]
    cellule["geometry"]["coordinates"].append(trou)
    assert point_temoin(cellule) == (2, 5)
    assert point_dans_geometrie(*point_temoin(cellule), contour_servi(cellule))
    cellule["centroid"]["y_m"] = 20
    with pytest.raises(ValueError, match="1"):
        point_temoin(cellule)
    minuscule = {"cell_id": 2, "centroid": {"x_m": 0.15, "y_m": 0.15},
                 "geometry": {"type": "Polygon", "coordinates": [[[0.1, 0.1], [0.2, 0.1], [0.2, 0.2], [0.1, 0.1]]]}}
    with pytest.raises(ValueError, match="2"):
        contour_servi(minuscule)


def test_contour_departage_des_egalites():
    # Deux sommets sont à la même distance maximale du premier : le premier gagne.
    anneau = [[0, 0], [10, 0], [0, 10], [0, 0]]
    assert simplifier_anneau(anneau, 20) == [[0, 0], [10, 0], [0, 0]]
    # Deux sommets sont à la même distance de la corde ; garder le premier suffit.
    anneau = [[0, 0], [2, 1], [3, 1], [10, 0], [0, -1], [0, 0]]
    assert simplifier_anneau(anneau, 0.8) == [[0, 0], [2, 1], [10, 0], [0, -1], [0, 0]]


@contextmanager
def _service_local():
    serveur = ServeurMonde(("127.0.0.1", 0), 0, 0)
    fil = threading.Thread(target=serveur.serve_forever)
    fil.start()
    try:
        yield serveur, serveur.server_address[1]
    finally:
        serveur.shutdown()
        serveur.server_close()
        fil.join()


def test_carte_une_fois_initialisation_concurrente(monkeypatch):
    import sim.service as service

    appels = {nom: 0 for nom in ("document_carte", "charger_table", "charger_maisons", "charger_seigneuries")}
    for nom in appels:
        fonction = getattr(service, nom)

        def compter(*args, _nom=nom, _fonction=fonction, **kwargs):
            appels[_nom] += 1
            return _fonction(*args, **kwargs)

        monkeypatch.setattr(service, nom, compter)
    with _service_local() as (serveur, port):
        assert not any(appels.values())
        with ThreadPoolExecutor(max_workers=4) as lecteurs:
            reponses = list(lecteurs.map(lambda route: _lire(port, route), ["/departs", "/carte"] * 2))
        assert all(nombre == 1 for nombre in appels.values())
        assert reponses[1][1] == reponses[3][1]
        _lire(port, "/tick?n=1", "POST")
        _lire(port, "/departs")
        assert all(nombre == 1 for nombre in appels.values())


@pytest.mark.parametrize("erreur", [ValueError, SnapshotExportError, PuissanceInvalide, SeigneurieInconnue])
@pytest.mark.parametrize("route", ["/carte", "/departs"])
def test_erreur_sans_arreter_service(monkeypatch, erreur, route):
    import sim.service as service

    with _service_local() as (_, port):
        with monkeypatch.context() as patch:
            def refuser(*args, **kwargs):
                raise erreur("donnée absente")

            patch.setattr(service, "document_carte", refuser)
            statut, document, _ = requete_service(port, route)
            assert statut == HTTPStatus.INTERNAL_SERVER_ERROR
            assert document == {"erreur": "donnée absente"}
            _lire(port, "/monde")
        _lire(port, route)


def test_departs_verrou_et_erreur_de_fiche(monkeypatch):
    import sim.service as service

    with _service_local() as (serveur, port):
        _lire(port, "/carte")
        origine = service.fiche_de_seigneurie
        appels = []

        def lire(*args, **kwargs):
            assert serveur.verrou_tick.locked()
            appels.append(args[0])
            return origine(*args, **kwargs)

        monkeypatch.setattr(service, "fiche_de_seigneurie", lire)
        _lire(port, "/departs")
        assert appels == sorted(s.id for s in charger_seigneuries())
        with monkeypatch.context() as patch:
            def refuser(*args, **kwargs):
                assert serveur.verrou_tick.locked()
                raise PuissanceInvalide("fiche indisponible")

            patch.setattr(service, "fiche_de_seigneurie", refuser)
            statut, document, _ = requete_service(port, "/departs")
            assert statut == HTTPStatus.INTERNAL_SERVER_ERROR
            assert document == {"erreur": "fiche indisponible"}
        assert not serveur.verrou_tick.locked()
        _lire(port, "/tick?n=1", "POST")
        assert _lire(port, "/departs")[0]["tick"] == 1
