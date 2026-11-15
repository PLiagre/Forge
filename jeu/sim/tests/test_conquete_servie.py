"""Une conquête change des noms ; elle ne fait recalculer ni les places ni la géométrie des puissances."""

import json

import pytest

from sim import convois, service
from sim.model import ecrire_maitre
from sim.noms import noms_depuis_monde
from sim.places import origine_des_places, places_du_monde


def _prendre_un_bourg(monde):
    """Une maison qui tient sa capitale prend le bourg d'une autre cellule ; rend (cell_id, preneur, perdant)."""
    routes = monde.routes_des_lieux
    preneur = next(m for m in monde.maisons if m.cell_id is not None and m.id in routes.noms
                   and m.sorte != "plausible" and monde.cells[m.cell_id].lieux[m.rang].maitre == m.id)
    cid, perdant = next((cid, cellule.lieux[0].maitre) for cid, cellule in sorted(monde.cells.items())
                        if cid != preneur.cell_id and cellule.lieux[0].maitre not in (None, preneur.id))
    ecrire_maitre(monde.cells[cid].lieux[0], preneur.id)
    convois.changer_de_maitre(monde, cid, [0], preneur.id)
    return cid, preneur.id, perdant


def _compter(monkeypatch, nom):
    appels = []
    fonction = getattr(service, nom)

    def comptee(*arguments, **options):
        appels.append(1)
        return fonction(*arguments, **options)

    monkeypatch.setattr(service, nom, comptee)
    return appels


def test_une_conquete_refait_les_noms_sans_recalculer_places_ni_puissances(monkeypatch):
    with service.ServeurMonde(("127.0.0.1", 0), 0, 0) as serveur:
        monde = serveur.world
        assert monde.ancres_des_bourgs is not None
        places_avant, noms_avant = serveur._places_des_lieux(), serveur._noms
        places = _compter(monkeypatch, "places_du_monde")
        sources = _compter(monkeypatch, "sources_des_noms")
        cid, preneur, perdant = _prendre_un_bourg(monde)
        etat = serveur._construire_etat(0, -1)
        assert places == [] and sources == []
        # Les places sont celles du chargement, et celles qu'un calcul entier rendrait.
        assert serveur._places_des_lieux() is places_avant == places_du_monde(monde)
        # Les noms suivent le nouveau maître, comme un calcul entier sans rien de gardé.
        assert serveur._noms is not noms_avant
        assert serveur._noms == noms_depuis_monde(monde)
        assert preneur in serveur._noms[cid]["maisons"] and preneur not in noms_avant[cid]["maisons"]
        assert perdant in noms_avant[cid]["maisons"]
        servi = json.loads(etat.lieux[cid])
        assert servi["lieux"][0]["maitre"] == preneur and servi["noms"] == serveur._noms[cid]
        # Sans changement de maître, rien ne se refait.
        noms_apres = serveur._noms
        serveur._construire_etat(0, -1)
        assert serveur._noms is noms_apres and places == []


def test_sans_ancres_un_bourg_qui_change_de_maitre_refait_les_places(monkeypatch):
    with service.ServeurMonde(("127.0.0.1", 0), 0, 0) as serveur:
        monde = serveur.world
        serveur._places_des_lieux()
        ancres, monde.ancres_des_bourgs = monde.ancres_des_bourgs, None
        places = _compter(monkeypatch, "places_du_monde")
        avant = origine_des_places(monde)
        # Les places ne viennent plus des ancres mais des maîtres : elles se refont, une fois.
        serveur._places_des_lieux()
        serveur._places_des_lieux()
        assert places == [1]
        _prendre_un_bourg(monde)
        assert origine_des_places(monde) != avant
        serveur._places_des_lieux()
        assert places == [1, 1]
        # Avec ses ancres, le même monde ne dépend plus des maîtres.
        monde.ancres_des_bourgs = ancres
        origine = origine_des_places(monde)
        _prendre_un_bourg(monde)
        assert origine_des_places(monde) == origine


def test_un_autre_monde_servi_relit_ses_sources_de_noms(monkeypatch):
    with service.ServeurMonde(("127.0.0.1", 0), 0, 0) as serveur:
        premieres = serveur._sources_des_noms()
        assert serveur._sources_des_noms()[2] is premieres[2]
        sources = _compter(monkeypatch, "sources_des_noms")
        serveur.world = service.World.charger(rng_seed=1)
        secondes = serveur._sources_des_noms()
        assert sources == [1] and secondes[2] is not premieres[2] and secondes[2] == premieres[2]


def test_monter_le_service_ne_charge_pas_la_table_de_la_carte(monkeypatch):
    """La table des puissances que compte la carte figée ne se charge qu'à la première lecture de la carte."""
    tables = _compter(monkeypatch, "charger_table")
    with service.ServeurMonde(("127.0.0.1", 0), 0, 0) as serveur:
        assert tables == []
        serveur.carte_figee()
        assert tables == [1]
        _prendre_un_bourg(serveur.world)
        serveur._construire_etat(0, -1)
        serveur.carte_figee()
        assert tables == [1]
