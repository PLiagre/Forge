"""Preuves du dépôt, du tick et du service pour le choix de départ."""

from dataclasses import FrozenInstanceError, replace
from http import HTTPStatus
import json
from pathlib import Path
import random

import pytest

from sim import engine
from sim.seigneuries import charger_seigneuries
from sim.tests.test_monde import (
    _etapes_tick_dans_code, _etapes_tick_dans_modele, _verifier_meme_ordre_tick,
    lancer_service, requete_service,
)
from sim.world import World


def _id(nom):
    return next(s.id for s in charger_seigneuries() if s.nom == nom)


CAS_REFUS = [None, True, "Bar", 2.5, max(s.id for s in charger_seigneuries()) + 1]


@pytest.mark.parametrize("valeur", CAS_REFUS)
def test_refus_inconnu(valeur):
    from sim.intentions import IntentionRefusee, deposer_intention

    monde = World.charger(0)
    avant = monde.to_dict()
    intention = {"type": "choisir_depart"}
    if valeur is not None:
        intention["seigneurie"] = valeur
    with pytest.raises(IntentionRefusee) as erreur:
        deposer_intention(monde, intention)
    assert str(erreur.value) == f"seigneurie inconnue : {valeur!r}"
    assert monde.intentions_en_attente == [] and monde.maison_du_joueur is None
    assert monde.to_dict() == avant
    assert len(CAS_REFUS) > 0
    print(f"refus_observés=1, cas_prévus={len(CAS_REFUS)}, mondes_inchangés=1")


def test_refus_second_choix_et_acceptation():
    from sim.intentions import ChoixDepart, IntentionRefusee, deposer_intention

    monde = World.charger(0)
    bar, moree = _id("Duché de Bar"), _id("Despotat de Morée")
    choix = deposer_intention(monde, {"seigneurie": bar})
    assert choix == ChoixDepart(bar)
    with pytest.raises(FrozenInstanceError):
        choix.identifiant = moree
    for applique in (False, True):
        if applique:
            engine.tick(monde, random.Random(0), 0)
        avant = monde.to_dict()
        with pytest.raises(IntentionRefusee, match=f"départ déjà choisi : {bar}"):
            deposer_intention(monde, {"seigneurie": moree})
        assert monde.to_dict() == avant
        assert monde.maison_du_joueur == (bar if applique else None)
        assert monde.intentions_en_attente == ([] if applique else [choix])
    print("choix_acceptés=1, refus_observés=2, dataclasses_gelées=1")


def test_refus_siege_hors_carte():
    from sim.intentions import IntentionRefusee, deposer_intention

    monde = World.charger(0)
    avant = monde.to_dict()
    bar = next(s for s in charger_seigneuries() if s.nom == "Duché de Bar")
    hors = replace(bar, siege=replace(bar.siege, x_m=0, y_m=0))
    with pytest.raises(IntentionRefusee, match="hors carte"):
        deposer_intention(monde, {"seigneurie": bar.id}, seigneuries=(hors,))
    assert monde.to_dict() == avant and monde.intentions_en_attente == []
    assert monde.maison_du_joueur is None
    assert deposer_intention(monde, {"seigneurie": bar.id}).identifiant == bar.id
    print("sièges_hors_carte_refusés=1, choix_acceptés=1")


def test_applique_seulement_apres_la_garde():
    from sim.intentions import deposer_intention

    monde = World.charger(0)
    avant = monde.to_dict()
    bar = _id("Duché de Bar")
    choix = deposer_intention(monde, {"seigneurie": bar})
    assert monde.maison_du_joueur is None and monde.to_dict() == avant
    with pytest.raises(ValueError, match="numero_tick incohérent"):
        engine.tick(monde, random.Random(0), 5)
    assert monde.to_dict() == avant and monde.intentions_en_attente == [choix]
    engine.tick(monde, random.Random(0), 0)
    assert monde.maison_du_joueur == bar and monde.intentions_en_attente == []
    assert monde.to_dict()["maison_du_joueur"] == bar
    ordre = _etapes_tick_dans_code(Path(engine.__file__).read_text())
    assert ordre[:2] == ["_valider_numero_tick", "_appliquer_intentions"]
    engine._appliquer_intentions(object())
    print(f"choix_appliqués=1, ticks_invalides_refusés=1, étapes_vues={len(ordre)}")


def _poster(port, intention):
    return requete_service(port, "/intention", "POST", json.dumps(intention).encode())


def test_service_refus_et_choix():
    bar, moree = _id("Duché de Bar"), _id("Despotat de Morée")
    with lancer_service(0) as port:
        _, initial, avant = requete_service(port, "/monde")
        assert initial["cells"] and initial["tick"] == 0
        cell = initial["cells"][0]["cell_id"]
        lieux = [requete_service(port, f"/{vue}?cell={cell}")[2] for vue in ("lieu", "plan")]
        for valeur in (max(s.id for s in charger_seigneuries()) + 1, "Bar"):
            statut, erreur, _ = _poster(port, {"type": "choisir_depart", "seigneurie": valeur})
            assert statut == HTTPStatus.BAD_REQUEST and "seigneurie" in erreur["erreur"]
            assert requete_service(port, "/monde")[2] == avant
        statut, reponse, _ = _poster(port, {"type": "choisir_depart", "seigneurie": bar})
        assert statut == HTTPStatus.OK and reponse == {"acceptee": True, "appliquee_au_tick": 0}
        assert requete_service(port, "/monde")[2] == avant
        assert [requete_service(port, f"/{vue}?cell={cell}")[2] for vue in ("lieu", "plan")] == lieux
        assert "maison_du_joueur" not in initial
        # Le choix en attente est déjà protégé contre un second dépôt.
        assert _poster(port, {"type": "choisir_depart", "seigneurie": moree})[0] == HTTPStatus.CONFLICT
        requete_service(port, "/tick?n=1", "POST")
        _, monde, apres = requete_service(port, "/monde")
        assert monde["tick"] == 1 and monde["maison_du_joueur"] == bar
        statut, erreur, _ = _poster(port, {"type": "choisir_depart", "seigneurie": moree})
        assert statut == HTTPStatus.CONFLICT and "déjà choisi" in erreur["erreur"]
        assert requete_service(port, "/monde")[2] == apres
        assert _poster(port, {"route": "essai"})[0] == HTTPStatus.BAD_REQUEST
        assert requete_service(port, "/monde")[2] == apres
    with lancer_service(0) as port:
        requete_service(port, "/tick?n=1", "POST")
        temoin = requete_service(port, "/monde")[1]
        assert "maison_du_joueur" not in temoin
        assert temoin == {cle: valeur for cle, valeur in monde.items() if cle != "maison_du_joueur"}
    print(f"cellules_vues={len(initial['cells'])}, refus_observés=4, choix_appliqués=1, témoins_sans_choix=1")


def test_controles_du_modele(monkeypatch):
    from sim.tests.test_seigneuries import test_pure as verifier_purete

    lire = Path.read_text
    # Le contrôle existant rougit sur un commentaire altéré en mémoire.
    with monkeypatch.context() as sonde:
        sonde.setattr(Path, "read_text", lambda chemin, *a, **kw:
                      lire(chemin, *a, **kw) + ("\n# seigneurie\n" if chemin.name == "world.py" else ""))
        with pytest.raises(AssertionError):
            verifier_purete((World.charger(0), charger_seigneuries(), None, None))
    modele = lire(Path(engine.__file__).with_name("MODELE.md"))
    code = _etapes_tick_dans_code(lire(Path(engine.__file__)))
    document = _etapes_tick_dans_modele(modele)
    assert "_appliquer_intentions" in document
    with pytest.raises(AssertionError):
        _verifier_meme_ordre_tick(code, [etape for etape in document if etape != "_appliquer_intentions"])
    _verifier_meme_ordre_tick(code, document)
    assert modele.splitlines().count("## Les intentions du joueur") == 1
    print(f"sections_intentions=1, étapes_vues={len(document)}, contre_épreuves_rouges=2")


def _route_reference(monde):
    assert monde.plans, "échantillon vide : aucun plan"
    return {"type": "tracer_route", "cell": min(monde.plans),
            "points": [[0, 0], [40, 0], [40, 25]], "largeur_m": 4}


CAS_REFUS_ROUTE = [
    *[({"foyers": valeur}, None, "foyers") for valeur in (0, -1, True, 1.5, "1")],
    ({}, "type", "type"), ({"type": "essai"}, None, "type"),
    ({}, "cell", "champ"), ({"cell": True}, None, "cell"),
    ({"cell": "abc"}, None, "cell"), ({"cell": "absente"}, None, "cell"),
    ({"points": [[0, 0]]}, None, "route invalide"),
    ({"points": [[0], [1, 0]]}, None, "route invalide"),
    ({"points": [[float("nan"), 0], [1, 0]]}, None, "route invalide"),
    ({"points": [["a", 0], [1, 0]]}, None, "route invalide"),
    *[({"largeur_m": valeur}, None, "route invalide")
      for valeur in (0, -1, float("inf"), "4", True)],
    ({"extra": 0}, None, "champ"), ({}, "points", "champ"),
    ({}, "largeur_m", "champ"),
]


@pytest.mark.parametrize("modifications,retire,mot", CAS_REFUS_ROUTE)
def test_refus_route_sans_mutation(modifications, retire, mot):
    from sim.intentions import IntentionRefusee, recevoir_intention

    monde = World.charger(0)
    avant = monde.to_dict()
    intention = _route_reference(monde) | modifications
    if intention["cell"] == "absente":
        intention["cell"] = max(monde.plans) + 1
    if retire:
        del intention[retire]
    with pytest.raises(IntentionRefusee, match=mot):
        recevoir_intention(monde, intention)
    assert monde.intentions_en_attente == [] and monde.to_dict() == avant
    assert len(CAS_REFUS_ROUTE) > 0
    print(f"refus_observés=1, cas_prévus={len(CAS_REFUS_ROUTE)}, mondes_inchangés=1")


def test_refus_et_acceptation_route_copie_gelée():
    from sim.intentions import TraceRoute, recevoir_intention
    from sim.plan import PlanInvalide, Rue

    with pytest.raises(PlanInvalide):
        Rue(0, [(0, 0), (1, 0)], 1, en_chantier=1)
    monde = World.charger(0)
    intention = _route_reference(monde)
    route = recevoir_intention(monde, intention)
    assert isinstance(route, TraceRoute)
    intention["points"][0][0] += 1
    intention["points"].append([2, 2])
    assert route.points == ((0, 0), (40, 0), (40, 25))
    with pytest.raises(FrozenInstanceError):
        route.largeur_m = 1
    assert monde.intentions_en_attente == [route]
    print("routes_acceptées=1, copies_indépendantes=1, états_non_booléens_refusés=1")


def test_route_appliquee_en_tete_et_dans_l_ordre(monkeypatch):
    from sim.intentions import recevoir_intention
    from sim.tests.test_lieux import _construire_plan, _donnees_plan

    monde = World.charger(0)
    a = _route_reference(monde)
    b = a | {"points": [[0, 1], [40, 1]], "largeur_m": 2}
    avant = monde.to_dict()
    attentes = [recevoir_intention(monde, geste) for geste in (a, b)]
    assert monde.to_dict() == avant
    with pytest.raises(ValueError, match="numero_tick incohérent"):
        engine.tick(monde, random.Random(0), 1)
    assert monde.intentions_en_attente == attentes and monde.to_dict() == avant
    engine.tick(monde, random.Random(0), 0)
    rues = monde.plans[a["cell"]].rues
    assert len(rues) == len(attentes) > 0
    for identifiant, (rue, route) in enumerate(zip(rues, attentes)):
        assert (rue.identifiant, rue.points, rue.largeur_m) == (
            identifiant, route.points, route.largeur_m)
        assert rue.en_chantier is True
    assert monde.intentions_en_attente == []
    assert all(not plan.rues for cid, plan in monde.plans.items() if cid != a["cell"])
    autre = World.charger(0)
    autre.plans[a["cell"]] = _construire_plan(_donnees_plan())
    recevoir_intention(autre, a)
    recevoir_intention(autre, {"type": "choisir_depart", "seigneurie": _id("Duché de Bar")})
    engine.tick(autre, random.Random(0), 0)
    assert autre.plans[a["cell"]].rues[-1].identifiant == 8
    assert autre.maison_du_joueur == _id("Duché de Bar")
    assert autre.intentions_en_attente == []
    ignore = World.charger(0)
    recevoir_intention(ignore, a)
    with monkeypatch.context() as sonde:
        sonde.setattr(engine, "_appliquer_intentions", lambda monde: None)
        engine.tick(ignore, random.Random(0), 0)
        with pytest.raises(AssertionError):
            assert ignore.plans[a["cell"]].rues
    print(f"routes_appliquées={len(rues) + 1}, choix_appliqués=1, contre_épreuves_rouges=1")


def test_service_route_recu_refus_et_rejeu():
    from sim import constants as k
    from sim.tests.test_chantiers import _requis

    lieux = []
    route = _route_reference(World.charger(0))
    chemin = f"/plan?cell={route['cell']}"
    plans, mondes = [], []
    refus_observes = 0
    for avec_route in (True, True, False):
        with lancer_service(0) as port:
            avant = requete_service(port, "/monde")[2]
            plan_avant = requete_service(port, chemin)[2]
            if avec_route:
                statut, recu, _ = _poster(port, route)
                assert statut == HTTPStatus.OK
                assert recu == {"acceptee": True, "appliquee_au_tick": 0}
                assert requete_service(port, "/monde")[2] == avant
                assert requete_service(port, chemin)[2] == plan_avant
            refus = [({"route": "essai"}, "type"),
                     (route | {"cell": max(World.charger(0).plans) + 1}, "cell"),
                     (route | {"largeur_m": 0}, "route invalide")]
            for intention, mot in refus:
                statut, recu, _ = _poster(port, intention)
                assert statut == HTTPStatus.BAD_REQUEST
                assert recu["acceptee"] is False and mot in recu["erreur"]
                refus_observes += 1
                assert requete_service(port, "/monde")[2] == avant
                assert requete_service(port, chemin)[2] == plan_avant
            for corps in (b"pas du json", b"[]"):
                statut, recu, _ = requete_service(port, "/intention", "POST", corps)
                assert statut == HTTPStatus.BAD_REQUEST and recu["acceptee"] is False
                refus_observes += 1
                assert requete_service(port, "/monde")[2] == avant
                assert requete_service(port, chemin)[2] == plan_avant
            requete_service(port, "/tick?n=1", "POST")
            _, plan, octets = requete_service(port, chemin)
            if avec_route:
                assert plan["rues"] == [{"identifiant": 0, "foyers": 1, "points": route["points"],
                                         "largeur_m": 4, "en_chantier": True,
                                         "travail_requis": _requis(route),
                                         "travail_fourni": k.TAILLE_FOYER}]
            else:
                assert plan["rues"] == []
            plans.append(octets)
            mondes.append(requete_service(port, "/monde")[2])
            lieu = requete_service(port, f"/lieu?cell={route['cell']}")[1]
            lieux.append(lieu["foyers"])
            if avec_route:
                assert lieu["foyers"][k.METIER_OUVRIERS] == {"personnes": k.TAILLE_FOYER, "foyers": 1}
            else:
                assert k.METIER_OUVRIERS not in lieu["foyers"]
    with pytest.raises(AssertionError):
        assert plans[0] == plans[-1]
    assert plans[0] == plans[1] and mondes[0] == mondes[1] == mondes[2]
    assert len({sum(m["personnes"] for m in metiers.values()) for metiers in lieux}) == 1
    assert refus_observes > 0
    print(f"services_comparés={len(plans)}, refus_observés={refus_observes}, contre_épreuves_rouges=1")


def test_ligne_de_commande_gestes_et_refus(tmp_path):
    from sim import constants as k
    import os
    import subprocess
    import sys

    route = _route_reference(World.charger(0))
    gestes = [{"tick": 0, "intention": route},
              {"tick": 3, "intention": route | {"largeur_m": 2}}]
    fichier = tmp_path / "g.json"
    sortie, snapshot = tmp_path / "m.json", tmp_path / "s.json"
    environnement = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2]))

    def jouer(entrees, avec_gestes=True):
        sortie.unlink(missing_ok=True)
        snapshot.unlink(missing_ok=True)
        fichier.write_text(json.dumps(entrees), encoding="utf-8")
        commande = [sys.executable, "-m", "sim", "--ticks", "4", "--seed", "0",
                    "--monde-json", str(sortie), "--snapshot-json", str(snapshot)]
        if avec_gestes:
            commande += ["--gestes", str(fichier)]
        return subprocess.run(commande, cwd=tmp_path, env=environnement,
                              capture_output=True, text=True)

    octets = []
    for _ in range(2):
        resultat = jouer(gestes)
        assert resultat.returncode == 0, resultat.stderr
        octets.append(sortie.read_bytes())
    assert octets[0] == octets[1]
    monde = json.loads(octets[0])
    rues = monde["plans"][str(route["cell"])]["rues"]
    assert len(rues) == len(gestes) > 0
    assert [rue["identifiant"] for rue in rues] == [0, 1]
    assert all(rue["en_chantier"] is True for rue in rues)
    assert jouer([], avec_gestes=False).returncode == 0
    temoin = json.loads(sortie.read_bytes())
    assert temoin["plans"] and temoin["cells"]
    assert temoin["cells"].keys() == monde["cells"].keys()
    for cle, cell in monde["cells"].items():
        reference = temoin["cells"][cle]
        if cle != str(route["cell"]):
            assert cell == reference
        else:
            assert {k: v for k, v in cell.items() if k != "foyers"} == {
                k: v for k, v in reference.items() if k != "foyers"}
            metiers = cell["foyers"]
            assert sum(m["personnes"] for m in metiers.values()) == sum(m["personnes"] for m in reference["foyers"].values())
            assert sum(metiers.get(nom, {}).get("personnes", 0) for nom in (k.METIER_PAYSANS, k.METIER_OUVRIERS)) == reference["foyers"][k.METIER_PAYSANS]["personnes"]
    assert [rue["travail_fourni"] for rue in rues] == [4 * k.TAILLE_FOYER, k.TAILLE_FOYER]
    assert all(plan["rues"] == [] for plan in temoin["plans"].values())
    cas = [([{"tick": 0, "intention": {"type": "essai"}}], "entrée 1"),
           ([{"tick": 4, "intention": route}], "l'intention s'applique au tick suivant"),
           ([gestes[1], gestes[0]], "décroiss"), ({}, "liste"),
           ([{}], "tick"), ([{"tick": 0}], "intention"),
           *[([{"tick": t, "intention": route}], "tick") for t in (True, -1, "0", 0.5)],
           ([{"tick": 0, "intention": []}], "entrée 1"), ([None], "entrée 1"),
           ([gestes[0], {"tick": 3, "intention": {"type": "essai"}}], "entrée 2")]
    for entrees, mot in cas:
        resultat = jouer(entrees)
        assert resultat.returncode == 2 and mot in resultat.stderr
        assert not sortie.exists() and not snapshot.exists()
    # Un point déplacé doit faire rougir l'égalité du monde rejoué.
    autre = route | {"points": [[1, 0], [40, 0], [40, 25]]}
    assert jouer([{"tick": 0, "intention": autre}, gestes[1]]).returncode == 0
    with pytest.raises(AssertionError):
        assert sortie.read_bytes() == octets[0]
    for contenu in (None, "pas du json"):
        sortie.unlink(missing_ok=True)
        snapshot.unlink(missing_ok=True)
        fichier.unlink(missing_ok=True)
        if contenu is not None:
            fichier.write_text(contenu, encoding="utf-8")
        resultat = subprocess.run(
            [sys.executable, "-m", "sim", "--ticks", "4", "--gestes", str(fichier),
             "--monde-json", str(sortie), "--snapshot-json", str(snapshot)],
            cwd=tmp_path, env=environnement, capture_output=True, text=True)
        assert resultat.returncode == 2 and resultat.stderr
        assert not sortie.exists() and not snapshot.exists()
    print(f"gestes_rejoués={len(gestes)}, refus_observés={len(cas) + 2}, contre_épreuves_rouges=1")


def test_ligne_de_commande_refus_chemin_vide(tmp_path, monkeypatch, capsys):
    from sim import __main__ as cli

    def simulation_interdite(*args):
        raise AssertionError("un fichier illisible doit être refusé avant simulation")

    monkeypatch.setattr(cli, "_simulate", simulation_interdite)
    sortie, snapshot = tmp_path / "monde.json", tmp_path / "snapshot.json"
    assert cli.main(["--ticks", "0", "--gestes", "", "--monde-json", str(sortie),
                     "--snapshot-json", str(snapshot)]) == 2
    assert "refus" in capsys.readouterr().err
    assert not sortie.exists() and not snapshot.exists()
    print("chemins_vides_refusés=1, ticks_joués=0, sorties_écrites=0")
