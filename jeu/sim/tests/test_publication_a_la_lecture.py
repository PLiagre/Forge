"""Les lieux et leurs flux se calculent à la première lecture, sur ce que la publication a copié."""

import copy
import json

import pytest

from sim import flux, service
from sim.engine import tick
from sim.flux import flux_de_lieu
from sim.snapshot_export import SnapshotExportError

JOURS = 35


@pytest.fixture(scope="module")
def serveur():
    with service.ServeurMonde(("127.0.0.1", 0), 0, 0) as monte:
        for _ in range(JOURS):
            tick(monte.world, monte.rng)
        yield monte


def _cellule_routee(monde):
    """Une cellule de plusieurs lieux dont un lieu au moins a été prélevé et a vu partir ou arriver."""
    for cid, cellule in monde.cells.items():
        if len(cellule.lieux) < 2:
            continue
        mesures = [flux_de_lieu(monde, cid, lieu.rang) for lieu in cellule.lieux]
        if any(m["preleve_kg"] > 0 for m in mesures) and any(m["partis"] or m["arrives"] for m in mesures):
            return cid
    pytest.fail("aucune cellule prélevée et traversée : l'échantillon ne prouverait rien")


def test_la_vue_des_flux_ne_somme_que_la_cellule_lue(serveur):
    monde = serveur.world
    vue = flux.flux_des_lieux(monde)
    assert set(vue) == set(monde.cells) and len(vue) == len(monde.cells)
    assert vue._lus == {}
    cid = _cellule_routee(monde)
    lues = vue[cid]
    assert list(vue._lus) == [cid]
    assert lues == [flux_de_lieu(monde, cid, rang) for rang in range(len(monde.cells[cid].lieux))]
    # Une seconde lecture rend la même somme, sans la refaire.
    assert vue[cid] is lues
    with pytest.raises(KeyError):
        vue[max(monde.cells) + 1]


def test_la_vue_des_flux_ne_suit_pas_le_monde(serveur):
    monde = copy.deepcopy(serveur.world)
    cid = _cellule_routee(monde)
    attendues = [flux_de_lieu(monde, cid, rang) for rang in range(len(monde.cells[cid].lieux))]
    vue = flux.flux_des_lieux(monde)
    # Le monde change après la construction de la vue, avant la première lecture de la cellule.
    for jour in monde.flux.jours.values():
        jour.partis.clear()
        jour.arrives[(cid, 0)] = 10_000
        if jour.taux is not None:
            jour.taux[:] = [2 * part for part in jour.taux]
            jour.recoltes[cid] = [2 * kilos for kilos in jour.recoltes[cid]]
    monde.routes_des_lieux.par_cellule[cid][0][:] = [-1] * len(monde.cells[cid].lieux)
    monde.cells[cid].lieux.pop()
    monde.ticks_ecoules += 2 * JOURS
    assert vue[cid] == attendues
    # Contre-épreuve : une vue prise après le changement ne rend plus ces mesures.
    assert flux.flux_des_lieux(monde)[cid] != attendues[:-1]


def test_la_publication_ne_somme_aucun_flux_et_ne_photographie_aucun_lieu(serveur, monkeypatch):
    appels = []
    photographier = service.lieux_en_photographie

    def compter(cid, *arguments):
        appels.append(cid)
        return photographier(cid, *arguments)

    monkeypatch.setattr(service, "lieux_en_photographie", compter)
    etat = serveur._construire_etat(0, -1)
    vue = etat.lieux._contexte
    assert appels == [] and vue._lus == {}
    cid = _cellule_routee(serveur.world)
    document = json.loads(etat.lieux[cid])
    assert appels == [cid] and list(vue._lus) == [cid]
    assert [l["flux_30j"]["preleve_kg"] for l in document["lieux"]] == [m["preleve_kg"] for m in vue[cid]]
    # Le bourg reprend les octets du lieu, et une relecture ne refait rien.
    assert etat.lieux_avec_bourg[cid].endswith(etat.lieux[cid][1:])
    assert appels == [cid]


def test_un_etat_lu_apres_coup_rend_les_octets_de_son_tick():
    with service.ServeurMonde(("127.0.0.1", 0), 0, 0) as monte:
        for _ in range(JOURS):
            tick(monte.world, monte.rng)
        cid = _cellule_routee(monte.world)
        lu_tout_de_suite, lu_plus_tard = monte._construire_etat(0, -1), monte._construire_etat(0, -1)
        attendus = (lu_tout_de_suite.lieux[cid], lu_tout_de_suite.lieux_avec_bourg[cid])
        for _ in range(3):
            monte.jouer_un_tick()
        assert (lu_plus_tard.lieux[cid], lu_plus_tard.lieux_avec_bourg[cid]) == attendus
        # Contre-épreuve : le monde a bien bougé, l'état du jour ne rend pas ces octets.
        assert monte.etat_publie.lieux[cid] != attendus[0]
        assert json.loads(monte.etat_publie.lieux[cid])["lieux"] != json.loads(attendus[0])["lieux"]


def test_une_cellule_incoherente_arrete_la_publication_pas_la_lecture():
    with service.ServeurMonde(("127.0.0.1", 0), 0, 0) as monte:
        cid = next(cid for cid, cellule in monte.world.cells.items() if len(cellule.lieux) > 1)
        monte.world.cells[cid].lieux.pop()
        with pytest.raises(SnapshotExportError, match=f"nombre de lieux incohérent pour cell_id={cid}"):
            monte._construire_etat(0, -1)
