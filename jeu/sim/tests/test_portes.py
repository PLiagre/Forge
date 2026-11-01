"""Preuves des portes de l'enceinte : croisements calculés, contrôlés, publiés, jamais stockés."""

from dataclasses import replace
import copy
import json
from pathlib import Path
import random

import pytest

from sim import engine, portes as modele_portes, service
from sim.constants import TOLERANCE_CHEVAUCHEMENT_M
from sim.plan import Enceinte, Rue
from sim.portes import PorteSansRue, controler_portes, portes_de_l_enceinte
from sim.service import ServeurMonde
from sim.ville1400 import base_de_cellule
from sim.world import World

CARRE = [[-10, -10], [10, -10], [10, 10], [-10, 10]]
RUES = [
    Rue(1, [(-20, 0), (20, 0)], 2),                    # traverse : deux portes
    Rue(2, [(0, 0), (0, 20)], 3),                      # finit dedans : une porte
    Rue(3, [(30, 0), (40, 0)], 4),                     # dehors
    Rue(4, [(-5, 10), (5, 10)], 5),                    # alignée sur le côté du haut
    Rue(5, [(0, 5), (10, 5), (20, 5)], 6),             # sommet posé sur le mur
    Rue(6, [(-20, -5), (0, -5)], 7, True, 1, 10),      # en chantier
]
BASE = [{"points": [[100, 100], [101, 101]], "largeur_m": 1, "sorte": "ruelle"},
        {"points": [[-20, -8], [-5, -8]], "largeur_m": 8, "sorte": "principale"}]


def _porte(point, rue, identifiant, largeur):
    return {"point": point, "rue": rue, "identifiant": identifiant, "largeur_m": largeur}


ATTENDUES = [_porte([10.0, 0.0], "plan", 1, 2), _porte([10.0, 5.0], "plan", 5, 6),
             _porte([0.0, 10.0], "plan", 2, 3), _porte([-10.0, 0.0], "plan", 1, 2),
             _porte([-10.0, -5.0], "plan", 6, 7), _porte([-10.0, -8.0], "base", 1, 8)]


def test_croisements_du_carre():
    entrees = copy.deepcopy((CARRE, RUES, BASE))
    resultat = portes_de_l_enceinte(CARRE, RUES, BASE)
    assert ATTENDUES and resultat == ATTENDUES == portes_de_l_enceinte(CARRE, RUES, BASE)
    assert all(set(porte) == {"point", "rue", "identifiant", "largeur_m"} for porte in resultat)
    assert (CARRE, RUES, BASE) == entrees
    assert portes_de_l_enceinte(CARRE, RUES[2:4], BASE[:1]) == []
    assert portes_de_l_enceinte(CARRE, [], BASE) == [ATTENDUES[-1]]            # côté de fermeture
    assert portes_de_l_enceinte(CARRE, RUES, []) == ATTENDUES[:-1]             # rues de base
    assert portes_de_l_enceinte(CARRE, [Rue(0, [(1 / 3, 5), (1 / 3, 20)], 1)], [])[0]["point"] == [0.333333, 10.0]


def test_porte_sans_rue():
    controler_portes(CARRE, ATTENDUES, RUES, BASE)
    controler_portes(CARRE, [], RUES, BASE)
    for porte in (_porte([-10, 3], "base", 1, 8), _porte([0, 10], "plan", 9, 3), _porte([-10, -8], "base", 2, 8),
                  _porte([-10, -8], "chemin", 1, 8), _porte([-10, -8.02], "base", 1, 8), _porte([-20, -8], "base", 1, 8)):
        with pytest.raises(PorteSansRue, match="porte"):
            controler_portes(CARRE, [ATTENDUES[-1], porte], RUES[:2], BASE)
    with pytest.raises(PorteSansRue):
        controler_portes(CARRE, [_porte([0, 10], "plan", 2, 3)], RUES[2:], BASE)
    controler_portes(CARRE, [_porte([-10, -8 - TOLERANCE_CHEVAUCHEMENT_M / 2], "base", 1, 8)], [], BASE)


def _monde_avec_enceinte():
    monde = World.charger(0)
    contour = [(-60, -60), (60, -60), (60, 60), (-60, 60)]
    monde.plans[10103] = replace(monde.plans[10103], enceinte=Enceinte(contour), rues=[Rue(0, [(0, 55), (0, 80)], 4)])
    return monde, contour


def test_portes_jamais_stockees(monkeypatch):
    monde, contour = _monde_avec_enceinte()
    plan = monde.plans[10103]
    empreinte = json.dumps(monde.to_dict(), sort_keys=True)
    assert "portes" not in json.dumps(plan.to_dict()) + empreinte
    portes_de_l_enceinte(contour, plan.rues, base_de_cellule(monde, 10103)["rues"])
    assert json.dumps(monde.to_dict(), sort_keys=True) == empreinte
    monkeypatch.setattr(modele_portes, "portes_de_l_enceinte", lambda *a: 1 / 0)
    engine.tick(monde, random.Random(0), monde.ticks_ecoules)


def test_plan_publie_portes(monkeypatch):
    serveurs = [ServeurMonde(("127.0.0.1", 0), 0, 0) for _ in range(2)]
    try:
        avec, sans = serveurs
        monde, contour = _monde_avec_enceinte()
        avec.world.plans[10103] = monde.plans[10103]
        plan = avec.world.plans[10103]
        base_rues = base_de_cellule(avec.world, 10103)["rues"]
        etat = avec._construire_etat(0, -1)
        document = json.loads(avec.octets_plan(etat, 10103))
        attendues = json.loads(json.dumps(portes_de_l_enceinte(contour, plan.rues, base_rues)))
        assert document["portes"] == attendues and len(attendues) == 8
        assert sorted(p["rue"] for p in attendues) == ["base"] * 7 + ["plan"]
        assert [(p["identifiant"], p["point"]) for p in attendues if p["rue"] == "plan"] == [(0, [0.0, 60.0])]
        assert sorted(document["enceinte"]) == ["contour", "en_chantier", "foyers", "travail_fourni", "travail_requis"]
        reference = json.loads(sans.octets_plan(sans._construire_etat(0, -1), 10103))
        assert document["base"] == reference["base"]
        autre = next(c for c in avec.world.cells if c != 10103)
        assert avec.octets_plan(etat, autre) == sans.octets_plan(sans._construire_etat(0, -1), autre)
        assert "portes" not in json.loads(avec.octets_plan(etat, autre))
        monkeypatch.setattr(service, "portes_de_l_enceinte",
                            lambda *a: [*portes_de_l_enceinte(*a), _porte([0, 0], "plan", 99, 1)])
        with pytest.raises(PorteSansRue):
            avec._construire_etat(0, -1)
        monkeypatch.setattr(service, "portes_de_l_enceinte", lambda c, p, b: portes_de_l_enceinte(c, p, []))
        assert len(json.loads(avec.octets_plan(avec._construire_etat(0, -1), 10103))["portes"]) == 1
    finally:
        for serveur in serveurs:
            serveur.server_close()


def test_portes_documentees(monkeypatch):
    sim = Path(__file__).resolve().parents[1]
    termes = ("portes", "jamais stockées", "PorteSansRue", "sim/portes.py")

    def controler():
        modele = (sim / "MODELE.md").read_text(encoding="utf-8")
        section = modele.split("## Le plan du bourg\n", 1)[1].split("\n## ", 1)[0]
        readme = (sim / "README.md").read_text(encoding="utf-8")
        assert "Les portes, les matériaux" not in " ".join(section.split())
        assert all(terme in section for terme in termes[:3]) and all(terme in readme for terme in ("portes", "sim/portes.py"))

    controler()
    lire = Path.read_text
    for terme in termes:
        monkeypatch.setattr(Path, "read_text", lambda chemin, *a, t=terme, **k: lire(chemin, *a, **k).replace(t, "retiré"))
        with pytest.raises(AssertionError):
            controler()
