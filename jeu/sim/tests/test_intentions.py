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


def test_choix_depart_registre(monkeypatch):
    from copy import deepcopy
    from sim.intentions import ChoixDepart, IntentionRefusee, deposer_intention

    terres = charger_seigneuries()
    assert terres, "échantillon vide"
    def verifier(terre):
        monde = World.charger(0)
        identifiant = f"seigneurie-{terre.id}"
        fiche = next(m for m in monde.maisons if m.id == identifiant)
        assert (fiche.sorte, fiche.nom, fiche.siege) == ("seigneurie", terre.maison, terre.siege.nom)
        for sorte in (None, "grande maison"):
            sans = deepcopy(monde)
            sans.maisons = tuple(replace(m, sorte=sorte) if m.id == identifiant else m
                                for m in sans.maisons if sorte is not None or m.id != identifiant)
            avant = sans.to_dict()
            with pytest.raises(IntentionRefusee) as erreur:
                deposer_intention(sans, {"seigneurie": terre.id})
            assert str(erreur.value) == f"seigneurie inconnue : {terre.id}"
            assert sans.to_dict() == avant and sans.intentions_en_attente == []
        choix = deposer_intention(monde, {"seigneurie": terre.id})
        assert choix == ChoixDepart(terre.id)
        for applique in (False, True):
            if applique:
                engine.tick(monde, random.Random(0), 0)
                assert monde.maison_du_joueur == monde.to_dict()["maison_du_joueur"] == identifiant
            avant = monde.to_dict()
            with pytest.raises(IntentionRefusee) as erreur:
                deposer_intention(monde, {"seigneurie": terre.id})
            assert str(erreur.value) == f"départ déjà choisi : {identifiant}"
            assert monde.to_dict() == avant
            assert monde.intentions_en_attente == ([] if applique else [choix])
    for terre in terres:
        verifier(terre)
    monkeypatch.setattr(ChoixDepart, "appliquer", lambda choix, monde: setattr(monde, "maison_du_joueur", choix.identifiant))
    with pytest.raises(AssertionError):
        verifier(terres[0])


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
        with pytest.raises(IntentionRefusee, match=f"départ déjà choisi : seigneurie-{bar}"):
            deposer_intention(monde, {"seigneurie": moree})
        assert monde.to_dict() == avant
        assert monde.maison_du_joueur == (f"seigneurie-{bar}" if applique else None)
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
    assert monde.maison_du_joueur == f"seigneurie-{bar}" and monde.intentions_en_attente == []
    assert monde.to_dict()["maison_du_joueur"] == f"seigneurie-{bar}"
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
        assert monde["tick"] == 1 and monde["maison_du_joueur"] == f"seigneurie-{bar}"
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
    assert autre.maison_du_joueur == f"seigneurie-{_id('Duché de Bar')}"
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


def _parcelle_reference(monde):
    from sim.intentions import recevoir_intention

    route = _route_reference(monde)
    recevoir_intention(monde, route)
    engine._appliquer_intentions(monde)
    return {"type": "decouper_parcelle", "cell": route["cell"], "rue": 0, "segment": 0,
            "debut_m": 5, "facade_m": 10, "profondeur_m": 20, "cote": "gauche"}


CAS_REFUS_PARCELLE = [
    *[({}, champ, "champ") for champ in
      ("type", "cell", "rue", "segment", "debut_m", "facade_m", "profondeur_m", "cote")],
    ({"extra": 0}, None, "champ"), ({"cell": "absente"}, None, "cell"),
    *[({"cell": v}, None, "cell") for v in (True, "0", 0.0)],
    *[({"foyers": v}, None, "foyers") for v in (0, -1, True, 1.5, "1")],
    *[({"rue": v}, None, "rue") for v in (1, -1, True, "0")],
    ({"cell": "autre"}, None, "rue"),
    *[({"segment": v}, None, "segment") for v in (2, -1, True, 0.0)],
    *[({"debut_m": v}, None, "debut_m") for v in (-1, float("nan"), float("inf"), True, "5")],
    *[({"facade_m": v}, None, "facade_m") for v in (0, -1, float("nan"), float("inf"), True)],
    *[({"profondeur_m": v}, None, "profondeur_m") for v in (0, -1, float("inf"), None)],
    ({"facade_m": 36}, None, "dépasse"), ({"debut_m": 40, "facade_m": 1}, None, "dépasse"),
    *[({"cote": v}, None, "cote") for v in ("haut", "Gauche", None)],
    ({"debut_m": 1e308, "facade_m": 1e308}, None, "dépasse"),
]


@pytest.mark.parametrize("modifications,retire,mot", CAS_REFUS_PARCELLE)
def test_refus_parcelle_sans_mutation(modifications, retire, mot):
    from sim.intentions import IntentionRefusee, recevoir_intention

    monde = World.charger(0)
    geste = _parcelle_reference(monde) | modifications
    if geste["cell"] == "absente":
        geste["cell"] = max(monde.plans) + 1
    elif geste["cell"] == "autre":
        geste["cell"] = next(c for c, plan in monde.plans.items() if not plan.rues)
    if retire:
        del geste[retire]
    avant = monde.to_dict()
    with pytest.raises(IntentionRefusee, match=mot):
        recevoir_intention(monde, geste)
    assert monde.intentions_en_attente == [] and monde.to_dict() == avant
    assert CAS_REFUS_PARCELLE
    print(f"refus_observés=1, cas_prévus={len(CAS_REFUS_PARCELLE)}")


def test_refus_parcelle_route_en_attente_et_limite_segment():
    from sim.intentions import IntentionRefusee, recevoir_intention

    monde = World.charger(0)
    reference = _parcelle_reference(World.charger(0))
    route = recevoir_intention(monde, _route_reference(monde))
    avant = monde.to_dict()
    with pytest.raises(IntentionRefusee, match="rue absente du plan"):
        recevoir_intention(monde, reference)
    assert monde.intentions_en_attente == [route] and monde.to_dict() == avant
    engine._appliquer_intentions(monde)
    limite = reference | {"segment": 1, "debut_m": 0, "facade_m": 25}
    assert recevoir_intention(monde, limite)
    attente = list(monde.intentions_en_attente)
    with pytest.raises(IntentionRefusee, match="dépasse"):
        recevoir_intention(monde, limite | {"facade_m": 25.000001})
    assert monde.intentions_en_attente == attente and monde.to_dict() != avant


def test_refus_parcelle_segment_nul_et_contour_non_fini():
    from sim.intentions import IntentionRefusee, recevoir_intention
    from sim.plan import Plan, Rue

    monde = World.charger(0)
    geste = _parcelle_reference(monde)
    for rue, mot in ((Rue(0, [(0, 0), (0, 0)], 4), "dépasse"),
                     (Rue(0, [(0, 1e308), (40, 1e308)], 4), "parcelle invalide")):
        monde.plans[geste["cell"]] = Plan(rues=[rue])
        avant = monde.to_dict()
        with pytest.raises(IntentionRefusee, match=mot):
            recevoir_intention(monde, geste | {"profondeur_m": 1e308})
        assert monde.to_dict() == avant and monde.intentions_en_attente == []


def test_contour_parcelle_cotes_segments_et_copie(monkeypatch):
    from sim import constants as k
    from sim.intentions import DecoupeParcelle, recevoir_intention

    monde = World.charger(0)
    geste = _parcelle_reference(monde)
    d = _route_reference(monde)["largeur_m"] * k.DEMI_LARGEUR_PAR_LARGEUR
    attendus = [((5, d), (15, d), (15, d + 20), (5, d + 20)),
                ((5, -d), (15, -d), (15, -d - 20), (5, -d - 20)),
                ((40 - d, 0), (40 - d, 25), (30 - d, 25), (30 - d, 0))]
    gestes = [geste, geste | {"cote": "droite"},
              geste | {"segment": 1, "debut_m": 0, "facade_m": 25, "profondeur_m": 10}]
    for entree, attendu in zip(gestes, attendus):
        decoupe = recevoir_intention(monde, entree)
        assert isinstance(decoupe, DecoupeParcelle) and decoupe.contour == attendu
        entree["debut_m"] += 1
        assert decoupe.contour == attendu
        with pytest.raises(FrozenInstanceError):
            decoupe.contour = ()
    monkeypatch.setattr(k, "DEMI_LARGEUR_PAR_LARGEUR", 0)
    sur_axe = recevoir_intention(monde, gestes[0] | {"debut_m": 5})
    assert sur_axe.contour[:2] == ((5, 0), (15, 0))
    with pytest.raises(AssertionError):
        assert sur_axe.contour == attendus[0]


def test_parcelle_appliquee_identifiants_et_cout_relu(monkeypatch):
    import math
    from sim import constants as k
    from sim.intentions import recevoir_intention
    from sim.plan import Parcelle, Plan
    from sim.tests.test_lieux import _construire_plan, _donnees_plan

    monde = World.charger(0)
    geste = _parcelle_reference(monde)
    c = geste["cell"]
    avant, rues = monde.to_dict(), monde.plans[c].rues
    decoupe = recevoir_intention(monde, geste)
    assert monde.to_dict() == avant
    requis = max(1, math.ceil(geste["facade_m"] * geste["profondeur_m"]
                              * k.TRAVAIL_PARCELLE_JOURNEES_PAR_M2))
    engine._appliquer_intentions(monde)
    assert monde.plans[c].parcelles == [Parcelle(0, decoupe.contour, True, 1, requis, 0)]
    assert monde.plans[c].rues == rues and all(a is b for a, b in zip(rues, monde.plans[c].rues))
    recevoir_intention(monde, geste | {"foyers": 3})
    engine._appliquer_intentions(monde)
    assert monde.plans[c].parcelles[-1] == Parcelle(1, decoupe.contour, True, 3, requis, 0)
    ancien = _construire_plan(_donnees_plan())
    monde.plans[c] = Plan(rues=rues + ancien.rues, parcelles=ancien.parcelles, batiments=ancien.batiments)
    recevoir_intention(monde, geste)
    engine._appliquer_intentions(monde)
    assert monde.plans[c].parcelles[-1].identifiant == 8
    assert monde.plans[c].batiments == ancien.batiments and ancien.batiments[0].identifiant == 7
    document = Plan(parcelles=[Parcelle(0, [(0, 0), (1, 0), (0, 1)])]).to_dict()["parcelles"][0]
    assert {champ: document[champ] for champ in
            ("en_chantier", "foyers", "travail_requis", "travail_fourni")} == {
                "en_chantier": False, "foyers": 0, "travail_requis": 0, "travail_fourni": 0}
    recevoir_intention(monde, geste)
    monkeypatch.setattr(k, "TRAVAIL_PARCELLE_JOURNEES_PAR_M2", k.TRAVAIL_PARCELLE_JOURNEES_PAR_M2 * 2)
    engine._appliquer_intentions(monde)
    double = monde.plans[c].parcelles[-1].travail_requis
    assert double == max(1, math.ceil(10 * 20 * k.TRAVAIL_PARCELLE_JOURNEES_PAR_M2))
    with pytest.raises(AssertionError):
        assert double == requis


def test_refus_parcelle_ordre_et_messages():
    from sim.intentions import IntentionRefusee, recevoir_intention

    monde = World.charger(0)
    reference = _parcelle_reference(monde)
    geste = reference | {"cell": True, "rue": True, "segment": True, "debut_m": -1,
                         "facade_m": 0, "profondeur_m": 0, "cote": "haut"}
    avant = monde.to_dict()
    controles = [("cell", "cell inconnu : True"), ("rue", "rue absente du plan : True"),
                 ("segment", "segment hors de la rue : True"), ("debut_m", "debut_m invalide : -1"),
                 ("facade_m", "facade_m invalide : 0"), ("profondeur_m", "profondeur_m invalide : 0"),
                 ("cote", "cote invalide : 'haut'")]
    for champ, message in controles:
        with pytest.raises(IntentionRefusee) as erreur:
            recevoir_intention(monde, geste)
        assert str(erreur.value) == message
        assert monde.to_dict() == avant and monde.intentions_en_attente == []
        geste[champ] = reference[champ]
    assert recevoir_intention(monde, geste)


def test_service_parcelle_plan_et_journees():
    import math
    from sim import constants as k

    reference = _parcelle_reference(World.charger(0))
    c = reference["cell"]
    with lancer_service(0) as port:
        assert _poster(port, _route_reference(World.charger(0)))[0] == HTTPStatus.OK
        requete_service(port, "/tick?n=1", "POST")
        avant = requete_service(port, f"/plan?cell={c}")[2]
        assert _poster(port, reference)[0] == HTTPStatus.OK
        assert requete_service(port, f"/plan?cell={c}")[2] == avant
        requete_service(port, "/tick?n=1", "POST")
        document = requete_service(port, f"/plan?cell={c}")[1]
        assert len(document["parcelles"]) == 1
        parcelle = document["parcelles"][0]
        d = 4 * k.DEMI_LARGEUR_PAR_LARGEUR
        assert parcelle == {"identifiant": 0,
                            "contour": [[5, d], [15, d], [15, d + 20], [5, d + 20]],
                            "en_chantier": True, "foyers": 1,
                            "travail_requis": max(1, math.ceil(10 * 20 * k.TRAVAIL_PARCELLE_JOURNEES_PAR_M2)),
                            "travail_fourni": k.TAILLE_FOYER}


def _batiment_reference(monde):
    from sim.intentions import recevoir_intention

    parcelle = _parcelle_reference(monde)
    recevoir_intention(monde, parcelle)
    engine._appliquer_intentions(monde)
    return {"type": "poser_batiment", "cell": parcelle["cell"], "parcelle": 0, "nature": "maison"}


CAS_REFUS_BATIMENT = [
    *[({}, champ, "champ") for champ in ("cell", "parcelle", "nature")],
    ({}, "type", "type"), ({"extra": 0}, None, "champ"),
    *[({"cell": v}, None, "cell") for v in ("absente", True, "0", 0.0)],
    *[({"parcelle": v}, None, "parcelle absente") for v in (1, -1, True, "0", 0.0, None)],
    ({"cell": "autre"}, None, "parcelle absente"),
    *[({"nature": v}, None, "nature") for v in ("atelier", "Maison", " maison", "", None, 0)],
    *[({"foyers": v}, None, "foyers") for v in (0, -1, True, 1.5, "1")],
]


@pytest.mark.parametrize("modifications,retire,mot", CAS_REFUS_BATIMENT)
def test_refus_batiment_sans_mutation(modifications, retire, mot):
    from sim.intentions import IntentionRefusee, recevoir_intention

    monde = World.charger(0)
    geste = _batiment_reference(monde) | modifications
    if geste["cell"] == "absente":
        geste["cell"] = max(monde.plans) + 1
    elif geste["cell"] == "autre":
        geste["cell"] = next(c for c, plan in monde.plans.items() if not plan.parcelles)
    if retire:
        del geste[retire]
    avant = monde.to_dict()
    with pytest.raises(IntentionRefusee, match=mot):
        recevoir_intention(monde, geste)
    assert monde.intentions_en_attente == [] and monde.to_dict() == avant
    assert CAS_REFUS_BATIMENT


def test_refus_batiment_bati_promis_et_en_attente():
    from sim.intentions import IntentionRefusee, recevoir_intention
    from sim.tests.test_lieux import _construire_plan, _donnees_plan

    monde = World.charger(0)
    geste = _batiment_reference(monde)
    decoupe = {"type": "decouper_parcelle", "cell": geste["cell"], "rue": 0, "segment": 0,
               "debut_m": 5, "facade_m": 10, "profondeur_m": 20, "cote": "droite"}
    recevoir_intention(monde, decoupe)
    avant, attente = monde.to_dict(), list(monde.intentions_en_attente)
    with pytest.raises(IntentionRefusee) as erreur:
        recevoir_intention(monde, geste | {"parcelle": 1})
    assert str(erreur.value) == "parcelle absente du plan : 1"
    assert monde.to_dict() == avant and monde.intentions_en_attente == attente
    engine._appliquer_intentions(monde)
    pose = recevoir_intention(monde, geste)
    avant = monde.to_dict()
    with pytest.raises(IntentionRefusee) as erreur:
        recevoir_intention(monde, geste | {"nature": "x", "foyers": 0})
    assert str(erreur.value) == "parcelle déjà promise : 0"
    assert monde.intentions_en_attente == [pose] and monde.to_dict() == avant
    recevoir_intention(monde, geste | {"parcelle": 1, "nature": "scierie"})
    assert len(monde.intentions_en_attente) == 2
    engine._appliquer_intentions(monde)
    assert [b.nature for b in monde.plans[geste["cell"]].batiments] == ["maison", "scierie"]
    for plan, identifiant in ((monde.plans[geste["cell"]], 0), (_construire_plan(_donnees_plan()), 7)):
        monde.plans[geste["cell"]] = plan
        avant = monde.to_dict()
        with pytest.raises(IntentionRefusee) as erreur:
            recevoir_intention(monde, geste | {"parcelle": identifiant, "nature": "x", "foyers": 0})
        assert str(erreur.value) == f"parcelle déjà bâtie : {identifiant}"
        assert monde.intentions_en_attente == [] and monde.to_dict() == avant


def test_refus_batiment_ordre_et_messages():
    from sim.intentions import IntentionRefusee, recevoir_intention

    monde = World.charger(0)
    reference = _batiment_reference(monde)
    geste = reference | {"cell": True, "parcelle": True, "nature": "x", "foyers": 0}
    for champ, message in (("cell", "cell inconnu : True"),
                           ("parcelle", "parcelle absente du plan : True"),
                           ("nature", "nature inconnue : 'x'"),
                           ("foyers", "foyers invalide : attendu un entier ≥ 1, reçu 0")):
        avant = monde.to_dict()
        with pytest.raises(IntentionRefusee) as erreur:
            recevoir_intention(monde, geste)
        assert str(erreur.value) == message
        assert monde.intentions_en_attente == [] and monde.to_dict() == avant
        geste[champ] = reference.get(champ, 1)
    assert recevoir_intention(monde, geste) == monde.intentions_en_attente[0]


def test_batiment_applique_au_plan_et_cout_relu(monkeypatch):
    import math
    from sim import constants as k
    from sim.intentions import PoseBatiment, recevoir_intention
    from sim.plan import Batiment
    from sim.tests.test_lieux import _construire_plan, _donnees_plan

    monde = World.charger(0)
    geste = _batiment_reference(monde)
    c = geste["cell"]
    plan = monde.plans[c]
    avant = monde.to_dict()
    pose = recevoir_intention(monde, geste)
    assert pose == PoseBatiment(c, 0, "maison", 1)
    with pytest.raises(FrozenInstanceError):
        pose.nature = "four"
    assert monde.to_dict() == avant
    engine._appliquer_intentions(monde)
    contour = tuple(tuple(p) for p in plan.parcelles[0].contour)
    requis = max(1, math.ceil(10 * 20 * k.TRAVAIL_BATIMENT_JOURNEES_PAR_M2))
    assert monde.plans[c].batiments == [Batiment(0, 0, "maison", contour, True, 1, requis, 0)]
    assert isinstance(monde.plans[c].batiments[0].emprise, tuple)
    assert all(isinstance(p, tuple) for p in monde.plans[c].batiments[0].emprise)
    assert all(a is b for a, b in zip(plan.rues, monde.plans[c].rues))
    assert all(a is b for a, b in zip(plan.parcelles, monde.plans[c].parcelles))
    recevoir_intention(monde, {"type": "decouper_parcelle", "cell": c, "rue": 0, "segment": 0,
                              "debut_m": 5, "facade_m": 10, "profondeur_m": 20, "cote": "droite"})
    engine._appliquer_intentions(monde)
    recevoir_intention(monde, geste | {"parcelle": 1, "nature": "four", "foyers": 3})
    engine._appliquer_intentions(monde)
    four = monde.plans[c].batiments[1]
    assert (four.identifiant, four.parcelle, four.nature, four.foyers, four.travail_requis) == (
        1, 1, "four", 3, requis)
    autre = World.charger(0)
    autre.plans[c] = _construire_plan(_donnees_plan())
    ancien = autre.plans[c].batiments[0]
    route = _route_reference(autre)
    recevoir_intention(autre, route)
    engine._appliquer_intentions(autre)
    recevoir_intention(autre, {"type": "decouper_parcelle", "cell": c, "rue": 8, "segment": 0,
                              "debut_m": 5, "facade_m": 10, "profondeur_m": 20, "cote": "gauche"})
    engine._appliquer_intentions(autre)
    recevoir_intention(autre, geste | {"parcelle": 8})
    # Le coût doit être lu à l’application, même après le dépôt.
    monkeypatch.setattr(k, "TRAVAIL_BATIMENT_JOURNEES_PAR_M2", 2 * k.TRAVAIL_BATIMENT_JOURNEES_PAR_M2)
    engine._appliquer_intentions(autre)
    assert autre.plans[c].batiments[0] is ancien
    nouveau = autre.plans[c].batiments[1]
    assert (nouveau.identifiant, nouveau.parcelle, nouveau.travail_requis) == (8, 8, 2 * requis)
    with pytest.raises(AssertionError):
        assert nouveau.travail_requis == requis
    document = _construire_plan(_donnees_plan()).to_dict()["batiments"][0]
    assert document["nature"] == "atelier"
    assert {champ: document[champ] for champ in ("en_chantier", "foyers", "travail_requis", "travail_fourni")} == {
        "en_chantier": False, "foyers": 0, "travail_requis": 0, "travail_fourni": 0}


def test_batiment_tick_rejeu_et_temoin(monkeypatch):
    from sim import constants as k
    from sim.intentions import recevoir_intention
    from sim.plan import Parcelle, Plan, Rue

    reference = World.charger(0)
    geste = _batiment_reference(reference)
    c = geste["cell"]
    route = _route_reference(reference)
    contour = reference.plans[c].parcelles[0].contour

    def jouer():
        mondes = [World.charger(0) for _ in range(3)]
        aleas = [random.Random(0) for _ in mondes]
        for i, monde in enumerate(mondes):
            monde.plans[c] = Plan(rues=[Rue(0, route["points"], 4)],
                                  parcelles=[Parcelle(0, contour, True, 1, 4 * k.TAILLE_FOYER, 0)])
            if i < 2:
                recevoir_intention(monde, geste)
        for i in range(3):
            for monde, alea in zip(mondes, aleas):
                engine.tick(monde, alea, numero_tick=i)
        documents = [m.to_dict() for m in mondes]
        assert documents[0] == documents[1]
        assert aleas[0].getstate() == aleas[1].getstate() == aleas[2].getstate()
        assert documents[0]["cells"] == documents[2]["cells"]
        a, b = documents[0]["plans"], documents[2]["plans"]
        assert a and a.keys() == b.keys()
        assert all(a[cle] == b[cle] for cle in a if cle != str(c))
        assert {cle: v for cle, v in a[str(c)].items() if cle != "batiments"} == {
            cle: v for cle, v in b[str(c)].items() if cle != "batiments"}
        assert not b[str(c)]["batiments"]
        return mondes[0], mondes[2]

    monde, temoin = jouer()
    assert monde.plans[c].batiments and monde.plans[c].parcelles[0].en_chantier
    assert monde.plans[c].batiments[0].en_chantier
    assert monde.plans[c].batiments[0].travail_fourni == 0
    assert monde.to_dict()["plans"] != temoin.to_dict()["plans"]
    with monkeypatch.context() as sonde:
        sonde.setattr(engine, "_appliquer_intentions", lambda monde: None)
        monde, temoin = jouer()
        assert monde.to_dict() == temoin.to_dict()
        with pytest.raises(AssertionError):
            assert monde.to_dict()["plans"] != temoin.to_dict()["plans"]


def _ia_monde():
    from sim import ia
    monde = World.charger(0)
    maisons = tuple(m for m in ia.maisons_de_l_ia(monde) if m.hors_carte is None)
    assert maisons
    for maison in maisons:
        monde.cells[maison.cell_id].lieux[0].duree_faim_ticks = 1
    return ia, monde, maisons


def _ia_pure(decider, monde, releve):
    from copy import deepcopy
    avant = deepcopy((monde.__dict__, releve))
    propositions = decider(monde, releve)
    assert (monde.__dict__, releve) == avant
    assert propositions == decider(monde, releve)
    return propositions


@pytest.mark.parametrize('faim,population,stock,attendu', [(1, 10, 0, True), (1, 10, 1000, True), (0, 10, 0, False), (1, 0, 1000, False)])
def test_ia_lecture_locale(monkeypatch, faim, population, stock, attendu):
    ia, monde, maisons = _ia_monde()
    maison = maisons[0]
    monkeypatch.setattr(ia, 'maisons_de_l_ia', lambda m: (maison, replace(maison, cell_id=None, hors_carte='hors carte')))
    bourg = monde.cells[maison.cell_id].lieux[0]
    bourg.duree_faim_ticks, bourg.population, bourg.dette_alimentaire_kg = faim, population, 500
    for lieu in monde.cells[maison.cell_id].lieux[1:]:
        lieu.stocks['nourriture'], lieu.duree_faim_ticks = stock, 1
    assert bool(_ia_pure(ia.decider_intentions, monde, [])) == attendu
    bourg.population, bourg.duree_faim_ticks = 10, 1 - faim
    assert bool(_ia_pure(ia.decider_intentions, monde, [])) != bool(faim)
    def impur(m, r):
        bourg.stocks['nourriture'] += 1
        return []
    with pytest.raises(AssertionError):
        _ia_pure(impur, monde, [])


@pytest.mark.parametrize('donnee', ['cellule', 'plan', 'bourg', 'faim', 'faim_absente'])
def test_ia_lecture_refus_avant_depot(monkeypatch, donnee):
    ia, monde, maisons = _ia_monde()
    cible = maisons[-1]
    monkeypatch.setattr(ia, 'maisons_de_l_ia', lambda m: (maisons[0], cible))
    if donnee == 'cellule': del monde.cells[cible.cell_id]
    elif donnee == 'plan': del monde.plans[cible.cell_id]
    elif donnee == 'bourg': monde.cells[cible.cell_id].lieux = []
    elif donnee == 'faim': monde.cells[cible.cell_id].lieux[0].duree_faim_ticks = -1
    else: monde.cells[cible.cell_id].lieux[0].duree_faim_ticks = None
    with pytest.raises(ValueError, match=f'{cible.id}.*{donnee.split("_")[0]}'):
        ia.jouer_ia(monde, [])
    assert monde.intentions_en_attente == []


def test_ia_registre_choix(monkeypatch):
    ia, _, maisons = _ia_monde()
    # Éprouver aussi le filtre de décision sans l'exclusion préalable de la vue.
    monkeypatch.setattr(ia, "maisons_de_l_ia", lambda monde: maisons)
    test_ia_budget_annuel_et_branches()


def test_ia_budget_annuel_et_branches():
    from copy import deepcopy
    from sim import constants as k
    from sim.intentions import ChoixDepart
    ia, monde, maisons = _ia_monde()
    couples = {(m.sorte, m.id) for m in maisons}
    assert len([m for m in maisons if m.nom == 'Paléologue']) == 2
    for identifiant in (_id('Despotat de Morée'), _id('Duché de Bar')):
        for attente in (False, True):
            monde.maison_du_joueur = None if attente else f"seigneurie-{identifiant}"
            monde.intentions_en_attente = [ChoixDepart(identifiant)] if attente else []
            assert {(p['maison']['sorte'], p['maison']['id']) for p in ia.decider_intentions(monde, [])} == couples - {('seigneurie', identifiant)}
    monde.maison_du_joueur, monde.intentions_en_attente = None, []
    releve = []
    for numero in (0, 0, 1, k.CALENDAR_DAYS_PER_YEAR - 1):
        monde.ticks_ecoules = numero
        ia.jouer_ia(monde, releve)
    assert len(releve) == len(couples)
    oubli = []
    ia.jouer_ia(deepcopy(monde), oubli)  # Oublier l'année permet de redéposer.
    with pytest.raises(AssertionError):
        assert len(releve + oubli) <= len(couples)
    monde.ticks_ecoules = k.CALENDAR_DAYS_PER_YEAR
    ia.jouer_ia(monde, releve)
    assert len(releve) == 2 * len(couples)


def test_ia_depot_commun_et_copies(monkeypatch):
    from copy import deepcopy
    from sim.intentions import recevoir_intention, IntentionRefusee
    ia, monde, maisons = _ia_monde()
    propositions = ia.decider_intentions(monde, [])
    avant, captures, releve = deepcopy(monde.__dict__), [], []
    monkeypatch.setattr(ia, 'recevoir_intention', lambda m, i: captures.append(i))
    ia.jouer_ia(monde, releve)
    assert monde.__dict__ == avant and captures == [p['intention'] for p in propositions]
    assert releve == [dict(tick=0, **p) for p in propositions]
    captures[0]['points'][0][0] += 1
    assert releve[0]['intention'] == propositions[0]['intention']
    def refuser(m, i): raise IntentionRefusee('refus sonde')
    monkeypatch.setattr(ia, 'recevoir_intention', refuser)
    refus = []
    with pytest.raises(IntentionRefusee): ia.jouer_ia(monde, refus)
    assert refus == []
    monkeypatch.setattr(ia, 'recevoir_intention', recevoir_intention)
    releve = []
    ia.jouer_ia(monde, releve)
    assert monde.cells == avant['cells'] and monde.plans == avant['plans']
    assert len(monde.intentions_en_attente) == len(propositions)
    assert releve[0]['intention'] == {'type': 'tracer_route', 'cell': maisons[0].cell_id, 'points': [[0, 0], [40, 0]], 'largeur_m': 4, 'foyers': 1}
    releve[0]['intention']['points'][0][0] += 1
    assert monde.intentions_en_attente[0].points == tuple(map(tuple, propositions[0]['intention']['points']))
    def ecrire_plan(m, i): m.plans.pop(i['cell'], None)
    monkeypatch.setattr(ia, 'recevoir_intention', ecrire_plan)
    with pytest.raises(AssertionError):
        ia.jouer_ia(monde, [])
        assert monde.cells == avant['cells'] and monde.plans == avant['plans']


@pytest.mark.parametrize("porte", ["absente", None, 2, True, "2", 2.0, -1, 99, 1, 3, 4, "origine_absente"])
def test_intention_porte(porte):
    from sim.intentions import IntentionRefusee, recevoir_intention
    from sim.tests.test_commerce import _monde_routes
    monde = _monde_routes()
    monde.adjacency = [{"a": 1, "b": 2}, {"a": 1, "b": 4, "kind": "sea", "shared_length_m": 0}]
    assert monde.cells and monde.adjacency
    if porte == "origine_absente":
        del monde.cells[1]
    avant = monde.to_dict()
    geste = _route_reference(monde)
    if porte != "absente":
        geste["porte_cell_id"] = 2 if porte == "origine_absente" else porte
    if porte not in ("absente", None) and (type(porte) is not int or porte != 2):
        with pytest.raises(IntentionRefusee, match="porte"):
            recevoir_intention(monde, geste)
        assert monde.intentions_en_attente == [] and monde.to_dict() == avant
        return
    route = recevoir_intention(monde, geste)
    assert monde.to_dict() == avant
    geste["porte_cell_id"] = 3
    assert route.porte_cell_id == (2 if porte == 2 else None)
    engine.tick(monde, random.Random(0), 0)
    publie = monde.to_dict()["plans"]["1"]
    def correspondance(document):
        assert document["rues"]
        assert document["rues"][0].get("porte_cell_id") == route.porte_cell_id
    correspondance(publie)
    publie["rues"][0]["porte_cell_id"] = 3
    with pytest.raises(AssertionError):
        correspondance(publie)


def _part_geste(maison, part):
    return {"type": "fixer_part", "maison": maison, "part": part}

@pytest.mark.parametrize("alteration", [
    {"maison": v} for v in ("inconnue", True, None, [], 1, "seigneurie-03", " plausible-1-0")
] + [{"part": v} for v in (True, False, None, "0.25", [], float("nan"), float("inf"), -float("inf"), -0.01, 0.61, 25, 10**400)]
  + [{"foyers": 1}, {"inconnu": 0}] + [{"sans": c} for c in ("type", "maison", "part")])
def test_part_depot_refus(alteration):
    from sim.intentions import IntentionRefusee, recevoir_intention
    monde = World.charger(0)
    maison = monde.maisons[0].id
    recevoir_intention(monde, _part_geste(maison, 0.25))
    file, parts, avant = list(monde.intentions_en_attente), dict(monde.parts), monde.to_dict()
    geste = _part_geste(maison, 0.5) | alteration
    champ = geste.pop("sans", None)
    if champ: geste.pop(champ)
    with pytest.raises(IntentionRefusee, match=champ or next(iter(alteration))): recevoir_intention(monde, geste)
    assert (monde.intentions_en_attente, monde.parts, monde.to_dict()) == (file, parts, avant)

def test_part_depot(monkeypatch):
    from sim.intentions import recevoir_intention
    import sim.constants as k
    monde = World.charger(0)
    a, b = [m.id for m in monde.maisons[:2]]
    choix = recevoir_intention(monde, {"type": "choisir_depart", "seigneurie": charger_seigneuries()[0].id})
    for valeur in (0, k.PART_MAXIMALE, 0.25):
        geste = _part_geste(a, valeur); depose = recevoir_intention(monde, geste)
        geste["part"] = -1
        assert depose.part == valeur
        with pytest.raises(FrozenInstanceError): depose.part = 0
    second = recevoir_intention(monde, _part_geste(b, 0))
    monkeypatch.setattr(k, "PART_MAXIMALE", 0.75)
    dernier = recevoir_intention(monde, _part_geste(a, 0.75))
    assert monde.intentions_en_attente == [choix, dernier, second] and dernier.maison == a != second.maison

def test_part_tick(monkeypatch):
    from sim.intentions import recevoir_intention, FixerPart
    from sim.tests.test_maisons import _tick_sans_lecture_registre
    from copy import deepcopy
    def verifier():
        monde, temoin = World.charger(0), World.charger(0)
        for w in (monde, temoin): recevoir_intention(w, {"type": "choisir_depart", "seigneurie": charger_seigneuries()[0].id})
        maison = monde.maisons[0].id
        avant, parts = monde.to_dict(), dict(monde.parts)
        for part in (0.2, 0.3): recevoir_intention(monde, _part_geste(maison, part))
        file = list(monde.intentions_en_attente)
        assert monde.to_dict() == avant and monde.parts == parts
        with pytest.raises(ValueError, match="numero_tick"): engine.tick(monde, random.Random(0), 1)
        assert monde.to_dict() == avant and monde.intentions_en_attente == file and monde.parts == parts
        rng, rng_temoin, retours = random.Random(0), random.Random(0), []
        _tick_sans_lecture_registre(monkeypatch, monde, lambda w, r, n: retours.append(engine.tick(w, rng, n)), 0)
        retour = engine.tick(temoin, rng_temoin, 0)
        assert monde.parts == parts | {maison: 0.3} and not monde.intentions_en_attente
        copie = deepcopy(monde); copie.parts = dict(temoin.parts)
        assert vars(copie) == vars(temoin) and rng.getstate() == rng_temoin.getstate() and retours == [retour]
        assert engine.tick(monde, rng, 1) == engine.tick(temoin, rng_temoin, 1)
    verifier()
    for appliquer, erreur in ((lambda g, w: None, AssertionError),
                               (lambda g, w: w.parts.update({g.maison: 0.2}), AssertionError),
                               (lambda g, w: getattr(w, "maisons"), RuntimeError)):
        with monkeypatch.context() as garde:
            garde.setattr(FixerPart, "appliquer", appliquer)
            with pytest.raises(erreur): verifier()

def test_part_service(monkeypatch):
    import threading
    from sim.service import ServeurMonde
    from sim.intentions import recevoir_intention
    serveur = ServeurMonde(("127.0.0.1", 0), 0, 0)
    fil = threading.Thread(target=serveur.serve_forever); fil.start()
    port, monde, terre = serveur.server_port, serveur.world, charger_seigneuries()[0]
    maison = f"seigneurie-{terre.id}"
    autre = next(m.id for m in monde.maisons if m.id != maison)
    def refuser(identifiant, raison):
        avant = (dict(monde.parts), list(monde.intentions_en_attente), requete_service(port, "/monde")[2])
        statut, recu, _ = _poster(port, _part_geste(identifiant, 0.25))
        assert statut == 400 and recu["acceptee"] is False and raison in recu["erreur"]
        assert (monde.parts, monde.intentions_en_attente, requete_service(port, "/monde")[2]) == avant
    try:
        refuser(maison, "départ")
        _poster(port, {"type": "choisir_depart", "seigneurie": terre.id})
        refuser(maison, "départ")
        requete_service(port, "/tick?n=1", "POST")
        refuser(autre, "maison")
        with monkeypatch.context() as garde:
            garde.setattr(monde, "maison_du_joueur", autre)
            with pytest.raises(AssertionError): refuser(autre, "maison")
        monde.intentions_en_attente.clear(); coutume = monde.parts[maison]
        assert _poster(port, _part_geste(maison, 0.25))[:2] == (200, {"acceptee": True, "appliquee_au_tick": 1})
        assert monde.parts[maison] == coutume
        requete_service(port, "/tick?n=1", "POST")
        assert monde.parts[maison] == 0.25 and not monde.intentions_en_attente
        assert recevoir_intention(monde, _part_geste(autre, 0)).maison == autre
    finally:
        serveur.shutdown(); fil.join(); serveur.server_close()

def test_part_cli_determinisme(tmp_path):
    import subprocess
    import sys
    terre = charger_seigneuries()[0]; a = f"seigneurie-{terre.id}"
    b = next(m.id for m in World.charger(0).maisons if m.id != a)
    gestes = [{"tick": 0, "intention": {"type": "choisir_depart", "seigneurie": terre.id}}] + [
        {"tick": 1, "intention": _part_geste(i, p)} for i, p in ((a, 0.2), (a, 0.3), (b, 0))]
    fichier, sortie, photo = (tmp_path / n for n in ("gestes.json", "monde.json", "photo.json"))
    def jouer(entrees):
        sortie.unlink(missing_ok=True); photo.unlink(missing_ok=True)
        fichier.write_text(json.dumps(entrees))
        return subprocess.run([sys.executable, "-m", "sim", "--ticks", "3", "--seed", "0", "--gestes", str(fichier),
                               "--monde-json", str(sortie), "--snapshot-json", str(photo)], cwd=Path(__file__).parents[2], capture_output=True, text=True)
    octets = []
    for _ in range(2):
        resultat = jouer(gestes); assert resultat.returncode == 0, resultat.stderr
        octets.append(sortie.read_bytes())
        assert json.loads(octets[-1])["parts"] == {a: 0.3, b: 0}
    assert octets[0] == octets[1]
    assert jouer(gestes + [{"tick": 1, "intention": _part_geste(a, 0.4)}]).returncode == 0
    with pytest.raises(AssertionError): assert sortie.read_bytes() == octets[0]
    refuse = jouer(gestes + [{"tick": 1, "intention": _part_geste(a, True)}])
    assert refuse.returncode == 2 and "part" in refuse.stderr and "entrée 5" in refuse.stderr
    assert not sortie.exists() and not photo.exists()
