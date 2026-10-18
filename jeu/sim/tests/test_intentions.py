"""Preuves du dépôt, du tick et du service pour le choix de départ."""

from copy import deepcopy
from sim.intentions import recevoir_intention, IntentionRefusee
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


def _financer(monde, cid, kg=1_000_000):
    bourg = next(l for l in monde.cells[cid].lieux if l.rang == 0)
    assert bourg.maitre is not None and bourg.maitre in monde.greniers
    monde.greniers[bourg.maitre]['nourriture'] = kg

def _verser_salaire(monde, cid, jours):
    from sim import constants as k
    from sim.model import copier_panier, ecrire_stock_marchandise
    bourg = next(l for l in monde.cells[cid].lieux if l.rang == 0)
    kg = jours * k.SALAIRE_JOURNEE_KG
    monde.greniers[bourg.maitre]['nourriture'] -= kg
    for entite in (bourg, monde.cells[cid]):
        ecrire_stock_marchandise(entite, 'nourriture', copier_panier(entite).get('nourriture', 0) + kg)

def _temoin_salaire(sonde, temoin, cid, calendrier):
    affecter = engine._affecter_artisans
    def appliquer(monde):
        if monde is temoin: _verser_salaire(monde, cid, calendrier[monde.ticks_ecoules])
        return affecter(monde)
    sonde.setattr(engine, '_affecter_artisans', appliquer)

def _amorcage(cid, calendrier=None):
    return f"""from sim.world import World
from sim.tests.test_intentions import _financer, _verser_salaire
from sim import engine
charger = World.charger
def amorcer(*a, **kw):
    monde = charger(*a, **kw); _financer(monde, {cid}); return monde
World.charger = staticmethod(amorcer)
affecter = engine._affecter_artisans
def appliquer(monde):
    if {calendrier!r} is not None and not monde.plans[{cid}].rues: _verser_salaire(monde, {cid}, {calendrier!r}[monde.ticks_ecoules])
    return affecter(monde)
engine._affecter_artisans = appliquer
"""

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


def _depart_applique(port):
    """Choisit le Zab et l'applique avant le geste mesuré."""
    terre = _id("Émirat du Zab")
    statut, recu, _ = _poster(port, {"type": "choisir_depart", "seigneurie": terre})
    assert statut == HTTPStatus.OK and recu == {"acceptee": True, "appliquee_au_tick": 0}
    assert requete_service(port, "/tick?n=1", "POST")[1]["tick"] == 1


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


def _route_reference(monde, cell=None):
    assert monde.plans, "échantillon vide : aucun plan"
    cell = min(monde.plans) if cell is None else cell
    return {"type": "tracer_route", "cell": cell, "maison": next(l.maitre for l in monde.cells[cell].lieux if l.rang == 0),
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
    _financer(monde, a["cell"])
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
    route = _route_reference(World.charger(0), 10103)
    chemin = f"/plan?cell={route['cell']}"
    plans, mondes = [], []
    refus_observes = 0
    for avec_route in (True, True, False):
        with lancer_service(0, amorcage=_amorcage(route["cell"], [0, k.TAILLE_FOYER])) as port:
            _depart_applique(port)
            avant = requete_service(port, "/monde")[2]
            plan_avant = requete_service(port, chemin)[2]
            if avec_route:
                statut, recu, _ = _poster(port, route)
                assert statut == HTTPStatus.OK
                assert recu == {"acceptee": True, "appliquee_au_tick": 1}
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
        programme = _amorcage(route['cell'], [5, 5, 5, 10]) + "import runpy; runpy.run_module('sim', run_name='__main__')"
        commande = [sys.executable, '-c', programme, *commande[3:]]
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
    assert (monde["greniers"], monde["pertes_kg"]) == (temoin["greniers"], temoin["pertes_kg"])
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


def _parcelle_reference(monde, cell=None):
    from sim.intentions import recevoir_intention

    route = _route_reference(monde, cell)
    recevoir_intention(monde, route)
    engine._appliquer_intentions(monde)
    return {"type": "decouper_parcelle", "cell": route["cell"], "maison": route["maison"], "rue": 0, "segment": 0,
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

    reference = _parcelle_reference(World.charger(0), 10103)
    c = reference["cell"]
    with lancer_service(0, amorcage=_amorcage(c)) as port:
        _depart_applique(port)
        assert _poster(port, _route_reference(World.charger(0), 10103))[0] == HTTPStatus.OK
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


def _batiment_reference(monde, cell=None):
    from sim.intentions import recevoir_intention

    parcelle = _parcelle_reference(monde, cell)
    recevoir_intention(monde, parcelle)
    engine._appliquer_intentions(monde)
    return {"type": "poser_batiment", "cell": parcelle["cell"], "maison": parcelle["maison"], "parcelle": 0, "nature": "maison"}


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
    decoupe = {"type": "decouper_parcelle", "maison": geste["maison"], "cell": geste["cell"], "rue": 0, "segment": 0,
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
    recevoir_intention(monde, {"type": "decouper_parcelle", "maison": geste["maison"], "cell": c, "rue": 0, "segment": 0,
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
    recevoir_intention(autre, {"type": "decouper_parcelle", "maison": geste["maison"], "cell": c, "rue": 8, "segment": 0,
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
            _financer(monde, c)
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
    ia.jouer_ia(monde, refus)
    assert monde.__dict__ == avant
    assert refus == [dict(tick=0, refus='refus sonde', **p) for p in propositions]
    monkeypatch.setattr(ia, 'recevoir_intention', recevoir_intention)
    releve = []
    ia.jouer_ia(monde, releve)
    assert monde.cells == avant['cells'] and monde.plans == avant['plans']
    assert len(monde.intentions_en_attente) == len(propositions)
    assert releve[0]['intention'] == {'type': 'tracer_route', 'maison': ia._cle_du_grenier(maisons[0]), 'cell': maisons[0].cell_id, 'points': [[0, 0], [40, 0]], 'largeur_m': 4, 'foyers': 1}
    releve[0]['intention']['points'][0][0] += 1
    assert monde.intentions_en_attente[0].points == tuple(map(tuple, propositions[0]['intention']['points']))
    def ecrire_plan(m, i): m.plans.pop(i['cell'], None)
    monkeypatch.setattr(ia, 'recevoir_intention', ecrire_plan)
    with pytest.raises(AssertionError):
        ia.jouer_ia(monde, [])
        assert monde.cells == avant['cells'] and monde.plans == avant['plans']


def test_ia_raison_lue():
    from copy import deepcopy
    from sim.plan import Parcelle, Rue
    from sim.seigneuries import identifiant_de_seigneurie
    from sim.tests.test_monde import _lire_raison_monde
    ia, monde, maisons = _ia_monde()
    maison = maisons[0]
    cellule = monde.cells[maison.cell_id]
    bourg = next(lieu for lieu in cellule.lieux if lieu.rang == 0)
    champs = sorted((lieu for lieu in cellule.lieux if lieu.rang >= 1), key=lambda lieu: lieu.rang)
    assert champs
    bourg.population, bourg.duree_faim_ticks = 20742, 12
    bourg.dette_alimentaire_kg, bourg.stocks['nourriture'] = 4203.3, 0.8
    for indice, champ in enumerate(champs, start=1):
        champ.stocks['nourriture'] = 1000.0 + indice
    cle = f'grande-{maison.id}' if maison.sorte == 'grande maison' else identifiant_de_seigneurie(maison.id)
    monde.greniers[cle] = {'nourriture': 77.25}
    plan = monde.plans[maison.cell_id]
    rue = Rue(max((r.identifiant for r in plan.rues), default=-1) + 1, [(0, 0), (1, 0)], 4, True, 1, 1, 0)
    parcelle = Parcelle(max((p.identifiant for p in plan.parcelles), default=-1) + 1,
                        [(0, 0), (1, 0), (0, 1)], True, 1, 1, 0)
    plan.rues.append(rue)
    plan.parcelles.append(parcelle)
    couple = (maison.sorte, maison.id)
    propositions = _ia_pure(ia.decider_intentions, monde, [])
    proposition = next(p for p in propositions if (p['maison']['sorte'], p['maison']['id']) == couple)
    attendue = _lire_raison_monde(monde, maison)
    assert proposition['raison'] == attendue
    assert attendue['regle'] == 'route_si_bourg_affame' and attendue['departs'] == -1
    assert attendue['bourg'] == {
        'population': 20742, 'duree_faim_ticks': 12,
        'dette_alimentaire_kg': 4203.3, 'nourriture_kg': 0.8}
    assert attendue['champs_nourriture_kg'] == [1000.0 + i for i in range(1, len(champs) + 1)]
    assert attendue['grenier_nourriture_kg'] == 77.25
    assert attendue['chantiers_en_cours']['rues'] == sum(r.en_chantier for r in plan.rues)
    assert attendue['chantiers_en_cours']['parcelles'] == sum(p.en_chantier for p in plan.parcelles)

    def eprouver(muter, restaurer):
        muter()
        assert proposition['raison'] != _lire_raison_monde(monde, maison)
        restaurer()
        assert proposition['raison'] == _lire_raison_monde(monde, maison)

    eprouver(lambda: setattr(bourg, 'duree_faim_ticks', 13), lambda: setattr(bourg, 'duree_faim_ticks', 12))
    eprouver(lambda: champs[0].stocks.__setitem__('nourriture', 1),
             lambda: champs[0].stocks.__setitem__('nourriture', 1001.0))
    eprouver(lambda: monde.greniers[cle].__setitem__('nourriture', 1),
             lambda: monde.greniers[cle].__setitem__('nourriture', 77.25))
    eprouver(lambda: plan.rues.remove(rue), lambda: plan.rues.append(rue))
    bourg.duree_faim_ticks = 0
    fausse = deepcopy(proposition['raison'])
    fausse['bourg']['duree_faim_ticks'] = 12
    with pytest.raises(AssertionError):
        assert fausse == _lire_raison_monde(monde, maison)
    bourg.duree_faim_ticks = 12
    del monde.greniers[cle]
    sans_panier = next(p['raison'] for p in ia.decider_intentions(monde, [])
                       if (p['maison']['sorte'], p['maison']['id']) == couple)
    assert sans_panier['grenier_nourriture_kg'] == -1
    monde.greniers[cle] = {'bois': 3}
    sans_nourriture = next(p['raison'] for p in ia.decider_intentions(monde, [])
                           if (p['maison']['sorte'], p['maison']['id']) == couple)
    assert sans_nourriture['grenier_nourriture_kg'] == 0


def test_ia_refus_compte_pour_l_annee(monkeypatch):
    from copy import deepcopy
    import sim.constants as k
    from sim.intentions import IntentionRefusee
    ia, monde, maisons = _ia_monde()
    assert maisons
    propositions = ia.decider_intentions(monde, [])
    assert propositions
    couples = {(p['maison']['sorte'], p['maison']['id']) for p in propositions}

    def refuser(m, i):
        raise IntentionRefusee('refus sonde')

    monkeypatch.setattr(ia, 'recevoir_intention', refuser)
    avant = deepcopy(monde.__dict__)
    releve = []
    ia.jouer_ia(monde, releve)
    attendu = [dict(tick=0, refus='refus sonde', **p) for p in propositions]

    def controle(etat, obtenu):
        assert obtenu and all('refus' in entree for entree in obtenu)
        assert obtenu == attendu and monde.__dict__ == etat

    controle(avant, releve)
    sans_clef = deepcopy(releve)
    del sans_clef[0]['refus']
    with pytest.raises(AssertionError):
        controle(avant, sans_clef)
    with pytest.raises(AssertionError):
        controle(avant, [])
    avant_second = deepcopy(monde.__dict__)
    assert ia.decider_intentions(monde, releve) == []
    ia.jouer_ia(monde, releve)
    assert releve == attendu and monde.__dict__ == avant_second
    monde.ticks_ecoules = k.CALENDAR_DAYS_PER_YEAR
    prochaines = ia.decider_intentions(monde, releve)
    assert {(p['maison']['sorte'], p['maison']['id']) for p in prochaines} == couples
    avant_an = deepcopy(monde.__dict__)
    ia.jouer_ia(monde, releve)
    assert len(releve) == 2 * len(propositions) and monde.__dict__ == avant_an
    assert ia.maisons_actives_30j(31, releve) == 0
    acceptees = [dict(tick=0, **p) for p in propositions]
    assert ia.maisons_actives_30j(31, acceptees) == len(couples) > 0
    with monkeypatch.context() as isole:
        test_ia_lecture_refus_avant_depot(isole, 'cellule')

    def deposer_puis_lever(m, i):
        m.intentions_en_attente.append(i)
        raise IntentionRefusee('après dépôt')

    monkeypatch.setattr(ia, 'recevoir_intention', deposer_puis_lever)
    avant_sonde = deepcopy(monde.__dict__)
    ia.jouer_ia(monde, [])
    with pytest.raises(AssertionError):
        assert monde.__dict__ == avant_sonde


@pytest.mark.parametrize("porte", ["absente", None, 2, True, "2", 2.0, -1, 99, 1, 3, 4, "origine_absente"])
def test_intention_porte(porte):
    from sim.intentions import IntentionRefusee, recevoir_intention
    from sim.tests.test_commerce import _monde_routes
    monde = _monde_routes()
    monde.adjacency = [{"a": 1, "b": 2}, {"a": 1, "b": 4, "kind": "sea", "shared_length_m": 0}]
    assert monde.cells and monde.adjacency
    _terres_synthetiques(monde)
    geste = _route_reference(monde)
    if porte == "origine_absente":
        del monde.cells[1]
    avant = monde.to_dict()
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
        temoin.parts[maison] = 0.3
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


@pytest.mark.parametrize('cid', [10103, 10322])
def test_base_gestes_et_refus_purs(cid, monkeypatch):
    from copy import deepcopy
    from sim import ville1400 as v
    from sim.intentions import recevoir_intention, IntentionRefusee
    from sim.plan import Parcelle, Rue
    monde = World.charger(0)
    base = v.base_de_cellule(monde, cid)
    maison = base['maisons'][0]
    centre = [sum(p[i] for p in maison['emprise']) / len(maison['emprise']) for i in (0, 1)]
    route = dict(type='tracer_route', maison=monde.cells[cid].lieux[0].maitre, cell=cid, points=[centre, [centre[0]+1, centre[1]]], largeur_m=1)
    monde.plans[cid].rues.append(Rue(0, [(0, 0), (40, 0)], 4))
    parcelle = dict(type='decouper_parcelle', maison=route['maison'], cell=cid, rue=0, segment=0, debut_m=0,
                    facade_m=40, profondeur_m=200, cote='gauche')
    monde.plans[cid].parcelles.append(Parcelle(0, maison['emprise']))
    batiment = dict(type='poser_batiment', maison=route['maison'], cell=cid, parcelle=0, nature='maison')
    emprises = [v.emprise_de_rue(route['points'], 1), [(0, 2), (40, 2), (40, 202), (0, 202)], maison['emprise']]
    def refuser(geste, emprise):
        rang = next(i for i, m in enumerate(base['maisons']) if v.se_chevauchent(emprise, m['emprise']))
        avant, document = deepcopy(monde.__dict__), monde.to_dict()
        try:
            recevoir_intention(monde, geste)
        except IntentionRefusee as erreur:
            message = str(erreur)
        else:
            raise AssertionError("geste interdit accepté")
        assert f'maison de 1400 {rang}' in message
        assert f"{base['maisons'][rang]['foyers']} foyers" in message
        assert str(cid) in message
        assert monde.__dict__ == avant and monde.to_dict() == document
    for geste, emprise in zip((route, parcelle, batiment), emprises):
        refuser(geste, emprise)
        with monkeypatch.context() as sonde:
            sonde.setattr(v, 'maison_touchee', lambda *a: None)
            with pytest.raises(AssertionError):
                refuser(geste, emprise)
            monde.intentions_en_attente.clear()
    recevoir_intention(monde, route | {'points': [[0, 0], [1, 0]]})
    recevoir_intention(monde, parcelle | {'profondeur_m': 10})
    monde.plans[cid].parcelles[0] = Parcelle(0, [(0, 2), (1, 2), (1, 3), (0, 3)])
    recevoir_intention(monde, batiment)
    voie = base['rues'][0]
    recevoir_intention(monde, route | {'points': voie['points'], 'largeur_m': voie['largeur_m']})
    monde.intentions_en_attente.clear()
    population = monde.populations_bourg_amorcage.pop(cid)
    with pytest.raises(IntentionRefusee, match=str(cid)):
        recevoir_intention(monde, route)
    monde.populations_bourg_amorcage[cid] = population
    del monde.carte[cid]['centroid']
    with pytest.raises(IntentionRefusee, match=f'{cid}.*centroïde absent'):
        recevoir_intention(monde, route)
    manuel = World(cells=monde.cells, adjacency=[])
    manuel.maisons = monde.maisons
    recevoir_intention(manuel, route)


@pytest.mark.parametrize('cid', [10103, 10322])
def test_ia_base_route_avant_depot(cid, monkeypatch):
    from copy import deepcopy
    from sim import ia
    from sim.capitales import maisons_de_l_ia
    from sim.intentions import recevoir_intention
    from sim.plan import Rue
    monde = World.charger(0)
    maison = next(m for m in maisons_de_l_ia(monde) if m.cell_id == cid)
    monkeypatch.setattr(ia, 'maisons_de_l_ia', lambda m: [maison])
    monde.cells[cid].lieux[0].duree_faim_ticks = 1
    monde.plans[cid].rues = [Rue(i, [(0, 0), (1, 0)], 4) for i in range(13)]
    avant = deepcopy(monde.__dict__)
    assert ia.decider_intentions(monde, []) == [] and monde.__dict__ == avant
    with monkeypatch.context() as sonde:
        sonde.setattr(ia, 'verifier_base', lambda *a, **kw: None)
        propositions = ia.decider_intentions(monde, [])
        assert propositions[0]['intention']['points'] == [[0, 52], [40, 52]]
        releve = []
        ia.jouer_ia(monde, releve)
        assert 'maison de 1400' in releve[0]['refus'] and monde.__dict__ == avant
    monde.plans[cid].rues.pop()
    propositions = ia.decider_intentions(monde, [])
    assert propositions[0]['intention']['points'] == [[0, 48], [40, 48]]
    recevoir_intention(monde, propositions[0]['intention'])


def _lire_raison_part(monde, cle):
    """Relit la raison de part sans appeler sim/ia.py. None si la maison n'a aucun lieu."""
    from sim import constants as k
    lieux = [(cid, lieu) for cid, cell in monde.cells.items() for lieu in cell.lieux if lieu.maitre == cle]
    if not lieux:
        return None
    habitants = sum(lieu.population for _, lieu in lieux)
    t = monde.ticks_ecoules
    partis = arrives = 0
    affames = set()
    cles = {(cid, lieu.rang) for cid, lieu in lieux}
    for tick in range(t - k.FENETRE_FLUX_TICKS, t):
        jour = monde.flux.jours[tick]
        for c in cles:
            partis += jour.partis.get(c, 0)
            arrives += jour.arrives.get(c, 0)
            if c in jour.affames:
                affames.add(c)
    nourriture = k.MARCHANDISE_NOURRITURE
    grenier = monde.greniers[cle].get(nourriture, 0)
    journees = 0
    vus = set()
    for cid, lieu in lieux:
        if lieu.rang != 0 or cid in vus:
            continue
        vus.add(cid)
        plan = monde.plans[cid]
        for ouvrage in (*plan.rues, *plan.parcelles, *plan.batiments):
            if ouvrage.en_chantier:
                journees += ouvrage.travail_requis - ouvrage.travail_fourni
    salaires = journees * k.SALAIRE_JOURNEE_KG
    reserve_gens = (k.consommation_kg_par_habitant_par_tick(nourriture)
                    * (k.RESERVE_VOULUE_JOURS / k.TICK_DURATION_DAYS)
                    * habitants * k.RESERVE_VOULUE_PART_DES_HABITANTS)
    return {
        'regle': 'part_sur_projets_et_gens', 'part': monde.parts[cle],
        'habitants': habitants, 'partis': partis, 'arrives': arrives,
        'lieux_affames': len(affames), 'grenier_nourriture_kg': grenier,
        'reserve_gens_kg': reserve_gens, 'salaires_a_venir_kg': salaires,
        'reserve_voulue_kg': reserve_gens + salaires,
    }


def _nouvelle_part(raison):
    from sim import constants as k
    part = raison['part']
    if raison['partis'] - raison['arrives'] >= k.TAILLE_FOYER or raison['lieux_affames'] > 0:
        return max(0, round(part - k.IA_PAS_DE_PART, k.DECIMALES_PART))
    if raison['grenier_nourriture_kg'] < raison['reserve_voulue_kg']:
        return min(k.PART_MAXIMALE, round(part + k.IA_PAS_DE_PART, k.DECIMALES_PART))
    return part


def _controler_parts(releve, lectures, captures, monde):
    from sim import constants as k
    entrees = [e for e in releve if e['intention']['type'] == 'fixer_part']
    assert entrees and all('refus' not in e for e in releve)
    assert [c for c in captures if c['type'] == 'fixer_part'] == [e['intention'] for e in entrees]
    baisse_nette = hausse = False
    vues = {}
    for entree in entrees:
        cle = entree['intention']['maison']
        raison = entree['raison']
        assert raison == lectures[entree['tick']][cle]
        nouvelle = _nouvelle_part(raison)
        assert entree['intention']['part'] == nouvelle != raison['part']
        assert 0 <= nouvelle <= k.PART_MAXIMALE
        perte = raison['partis'] - raison['arrives'] >= k.TAILLE_FOYER
        faim = raison['lieux_affames'] > 0
        if nouvelle < raison['part']:
            assert perte or faim
        else:
            assert not perte and not faim and raison['grenier_nourriture_kg'] < raison['reserve_voulue_kg']
        baisse_nette = baisse_nette or (nouvelle < raison['part'] and perte and not faim)
        hausse = hausse or nouvelle > raison['part']
        vues[(entree['tick'], cle)] = entree
    for tick, raisons in lectures.items():
        for cle, raison in raisons.items():
            if (tick, cle) not in vues:
                assert _nouvelle_part(raison) == raison['part']
    assert baisse_nette and hausse
    attendu = {m.id: k.PART_COUTUMIERE for m in monde.maisons}
    for entree in entrees:
        attendu[entree['intention']['maison']] = entree['intention']['part']
    assert monde.parts == attendu


@pytest.fixture(scope='module')
def monde_ia_30():
    monde = World.charger(0)
    alea = random.Random(0)
    for _ in range(30):
        engine.tick(monde, alea, monde.ticks_ecoules)
    return monde


@pytest.fixture(scope='module')
def annee_ia():
    import zlib
    from sim import ia, constants as k
    from sim.capitales import maisons_de_l_ia
    from sim.seigneuries import identifiant_de_seigneurie
    monde, alea, releve, captures, lectures = World.charger(0), random.Random(0), [], [], {}
    fiches = []
    for maison in maisons_de_l_ia(monde):
        if maison.hors_carte is not None:
            continue
        cle = f'grande-{maison.id}' if maison.sorte == 'grande maison' else identifiant_de_seigneurie(maison.id)
        fiches.append((maison, cle))
    original = ia.recevoir_intention

    def capter(m, intention):
        captures.append(deepcopy(intention))
        return original(m, intention)

    with pytest.MonkeyPatch.context() as ctx:
        ctx.setattr(ia, 'recevoir_intention', capter)
        for i in range(365):
            t = monde.ticks_ecoules
            lectures[t] = {}
            jours = getattr(getattr(monde, 'flux', None), 'jours', None)
            pleine = jours is not None and all(tick in jours for tick in range(t - k.FENETRE_FLUX_TICKS, t))
            if pleine:
                choix = monde.maison_du_joueur
                noms = monde.routes_des_lieux.noms
                for maison, cle in fiches:
                    if maison.sorte == 'seigneurie' and identifiant_de_seigneurie(maison.id) == choix:
                        continue
                    if t % k.FENETRE_FLUX_TICKS != zlib.crc32(cle.encode('utf-8')) % k.FENETRE_FLUX_TICKS:
                        continue
                    if cle not in noms:
                        continue
                    raison = _lire_raison_part(monde, cle)
                    if raison is not None:
                        lectures[t][cle] = raison
            ia.jouer_ia(monde, releve)
            engine.tick(monde, alea, i)
    return monde, releve, captures, lectures


def test_an_ia_sans_refus(annee_ia, monkeypatch):
    from sim import ia
    from sim.plan import Rue
    monde, releve, _captures, _lectures = annee_ia
    acceptes = sum('refus' not in e for e in releve)
    print(f'depots_ia_acceptes={acceptes}, refus={len(releve)-acceptes}', flush=True)
    assert acceptes > 0 and all('refus' not in e for e in releve)
    from sim import ville1400 as v
    bande = v.emprise_de_rue([[0, 52], [40, 52]], 4)
    entree = next((e for e in releve if e['intention']['type'] == 'tracer_route' and any(
                   v.se_chevauchent(bande, m['emprise']) for m in
                   v.base_de_cellule(monde, e['intention']['cell'])['maisons'])), None)
    assert entree is not None, 'échantillon vide : aucun dépôt touché après treize rues'
    contre = World.charger(0)
    cid = entree['intention']['cell']
    contre.plans[cid].rues = [Rue(i, [(0, 0), (1, 0)], 4) for i in range(13)]
    contre.cells[cid].lieux[0].duree_faim_ticks = 1
    contre.ticks_ecoules = entree['tick']
    monkeypatch.setattr(ia, 'verifier_base', lambda *a, **kw: None)
    faux = []
    ia.jouer_ia(contre, faux)
    assert any('refus' in e for e in faux)


def _ouverture(maison="seigneurie-1", kg=100):
    return {"type": "ouvrir_grenier", "maison": maison, "kg": kg}


def _monde_ouverture():
    from sim.registre_maisons import MaisonDuMonde
    from sim.convois import TableRoutes
    from sim.model import Cell, EtatDeLieu
    monde = World({1: Cell(1, 1, 10, lieux=[EtatDeLieu(0, 10, {})])}, [])
    monde.maisons = (MaisonDuMonde("seigneurie-1", "Bar", "seigneurie", None, "Bar", 1, 0, None),
                     MaisonDuMonde("hors-carte", "Hors carte", "grande", None, "Ailleurs", None, None, "hors carte"))
    monde.routes_des_lieux = TableRoutes([(1, 0, "seigneurie-1", 1, 0, 1)])
    monde.greniers = {"seigneurie-1": {"nourriture": 100.0}, "hors-carte": {}}
    return monde


@pytest.mark.parametrize("alteration,raison", [
    *[({"maison": v}, f"maison inconnue ou mal formée : {v!r}") for v in ("inconnue", True, None, 1)],
    ({"maison": "hors-carte"}, "maison sans lieu : hors-carte"),
    *[({"kg": v}, f"kg invalide : {v!r}") for v in (True, None, "1", float("nan"), float("inf"), 0, -1)],
    ({"kg": 101}, "grenier insuffisant : 101 kg demandés, 60.0 kg disponibles"),
    ({"kg": 61}, "grenier insuffisant : 61 kg demandés, 60.0 kg disponibles"),
    ({"foyers": 1}, "champ inconnu : foyers"), ({"inconnu": 1}, "champ inconnu : inconnu"),
    *[({"sans": champ}, f"champ manquant : {champ}" if champ != "type" else "type d'intention inconnu : None")
      for champ in ("type", "maison", "kg")],
    ({"vide": True}, "lieux sans dette ni habitants : seigneurie-1"),
])
def test_ouverture_depot_refus(alteration, raison):
    from copy import deepcopy
    from sim.intentions import IntentionRefusee, recevoir_intention
    monde = _monde_ouverture()
    recevoir_intention(monde, _ouverture(kg=40))
    geste = _ouverture() | alteration
    if geste.pop("vide", False):
        monde.cells[1].lieux[0].population = 0
        geste["kg"] = 1
    champ = geste.pop("sans", None)
    if champ: geste.pop(champ)
    file, greniers, document = list(monde.intentions_en_attente), deepcopy(monde.greniers), monde.to_dict()
    with pytest.raises(IntentionRefusee) as refus:
        recevoir_intention(monde, geste)
    assert str(refus.value) == raison
    assert (monde.intentions_en_attente, monde.greniers, monde.to_dict()) == (file, greniers, document)


def test_ouverture_depot_gele_et_reservation(monkeypatch):
    from sim.intentions import recevoir_intention, IntentionRefusee
    monde = _monde_ouverture()
    premier = recevoir_intention(monde, _ouverture(kg=40))
    donnees = _ouverture(kg=60)
    second = recevoir_intention(monde, donnees)
    donnees["kg"] = 200
    assert monde.intentions_en_attente == [premier, second] and second.kg == 60
    with pytest.raises(FrozenInstanceError): second.kg = 0
    def verifier():
        with pytest.raises(IntentionRefusee, match="grenier insuffisant"):
            recevoir_intention(monde, _ouverture(kg=1))
    verifier()
    import sim.intentions as intentions
    original = intentions._ouvrir_grenier
    def sans_reservation(w, intention):
        file = w.intentions_en_attente
        w.intentions_en_attente = []
        try:
            geste = original(w, intention)
        finally:
            w.intentions_en_attente = file
        file.append(geste)
        return geste
    with monkeypatch.context() as garde:
        garde.setattr(intentions, "_ouvrir_grenier", sans_reservation)
        with pytest.raises(pytest.fail.Exception): verifier()
    del monde.intentions_en_attente[2:]
    engine._appliquer_intentions(monde)
    assert monde.greniers["seigneurie-1"]["nourriture"] == 0.0
    # Une somme préalable arrondirait différemment de ces retraits successifs.
    monde = _monde_ouverture()
    monde.greniers["seigneurie-1"]["nourriture"] = 1.0
    for kg in (0.3, 0.3): recevoir_intention(monde, _ouverture(kg=kg))
    with pytest.raises(IntentionRefusee, match="grenier insuffisant"):
        recevoir_intention(monde, _ouverture(kg=0.4))
    reste = (1.0 - 0.3) - 0.3
    recevoir_intention(monde, _ouverture(kg=reste))
    engine._appliquer_intentions(monde)
    assert monde.greniers["seigneurie-1"]["nourriture"] == 0.0


@pytest.mark.parametrize("dettes", [False, True])
def test_ouverture_application_sans_registre(monkeypatch, dettes):
    from sim import constants as c, prelevement
    from sim.intentions import OuvrirGrenier, recevoir_intention
    from sim.lieux import partager
    from sim.model import EtatDeLieu
    from sim.tests.test_maisons import _tick_sans_lecture_registre
    def verifier():
        monde = World.charger(0)
        routes = monde.routes_des_lieux
        indice = routes.noms.index("seigneurie-1")
        entrees = [(cid, rang, jours) for cid, rang, idx, jours in
                   zip(routes.cids, routes.rangs, routes.maitre_idx, routes.jours) if idx == indice]
        lieux = [monde.cells[cid].lieux[rang] for cid, rang, _ in entrees]
        assert lieux and all(l.population > 0 for l in lieux)
        if dettes:
            for rang, lieu in enumerate(lieux): lieu.dette_alimentaire_kg = rang + 1
        poids = [l.dette_alimentaire_kg if dettes else l.population for l in lieux]
        parts = partager(150000, poids)
        monde.parts = dict.fromkeys(monde.parts, 0)
        monde.greniers["seigneurie-1"] = {"nourriture": 200000.0}
        recevoir_intention(monde, _ouverture(kg=150000))
        observes = []
        original = prelevement.prelever
        def observer(w, recoltes):
            observes.append([(cid, rang, w.ticks_ecoules + jours - 1, part)
                             for (cid, rang, jours), part in zip(entrees, parts) if part])
            reel = sorted((cid, rang, arrivee, kg) for arrivee, charges in w.secours.items()
                          for (cid, rang), kg in charges.items())
            assert reel == sorted(observes[-1])
            original(w, recoltes)
        with monkeypatch.context() as garde:
            garde.setattr(c, "PERTE_GRENIER_PAR_AN", 0)
            garde.setattr(prelevement, "prelever", observer)
            garde.setattr(EtatDeLieu, "maitre", property(lambda self: (_ for _ in ()).throw(RuntimeError("maître lu"))))
            _tick_sans_lecture_registre(garde, monde, engine.tick, 0)
        assert observes and monde.greniers["seigneurie-1"]["nourriture"] == 50000
    verifier()
    original = OuvrirGrenier.appliquer
    def sans_retrait(geste, monde):
        original(geste, monde)
        monde.greniers[geste.maison]["nourriture"] += geste.kg
    with monkeypatch.context() as garde:
        garde.setattr(OuvrirGrenier, "appliquer", sans_retrait)
        with pytest.raises(AssertionError): verifier()


def test_ouverture_service(monkeypatch):
    import threading
    from sim import constants as c
    from sim.intentions import recevoir_intention
    from sim.service import ServeurMonde
    serveur = ServeurMonde(("127.0.0.1", 0), 0, 0)
    fil = threading.Thread(target=serveur.serve_forever); fil.start()
    port, monde = serveur.server_port, serveur.world
    maison = "seigneurie-1"
    autre = next(n for n in monde.routes_des_lieux.noms if n != maison)
    monde.parts = dict.fromkeys(monde.parts, 0)
    monde.greniers[maison] = {"nourriture": 200000.0}
    monde.greniers[autre] = {"nourriture": 200000.0}
    def refuser(nom, raison):
        avant = monde.to_dict(), list(monde.intentions_en_attente), requete_service(port, "/monde")[2]
        statut, recu, _ = _poster(port, _ouverture(nom))
        assert statut == 400 and raison == recu["erreur"]
        assert (monde.to_dict(), monde.intentions_en_attente, requete_service(port, "/monde")[2]) == avant
    try:
        refuser(maison, "départ non appliqué : choisir une terre avant d'ouvrir le grenier")
        _poster(port, {"type": "choisir_depart", "seigneurie": 1})
        refuser(maison, "départ non appliqué : choisir une terre avant d'ouvrir le grenier")
        requete_service(port, "/tick?n=1", "POST")
        raison = "maison interdite : seule la maison du joueur peut ouvrir son grenier"
        refuser(autre, raison)
        with monkeypatch.context() as garde:
            garde.setattr(monde, "maison_du_joueur", autre)
            with pytest.raises(AssertionError): refuser(autre, raison)
        monde.intentions_en_attente.clear()
        avant = monde.greniers[maison]["nourriture"]
        with monkeypatch.context() as garde:
            garde.setattr(c, "PERTE_GRENIER_PAR_AN", 0)
            monde.parts = dict.fromkeys(monde.parts, 0)
            assert _poster(port, _ouverture(maison))[:2] == (200, {"acceptee": True, "appliquee_au_tick": 1})
            assert monde.greniers[maison]["nourriture"] == avant
            requete_service(port, "/tick?n=1", "POST")
        assert monde.greniers[maison]["nourriture"] == avant - 100
        assert recevoir_intention(monde, _ouverture(autre)).maison == autre
    finally:
        serveur.shutdown(); fil.join(); serveur.server_close()


def test_ouverture_documentation():
    sim = Path(__file__).resolve().parents[1]
    texte = (sim / "MODELE.md").read_text()
    sections = [texte.split("## " + titre, 1)[1].split("\n## ", 1)[0] for titre in
                ("Le grenier d'une maison", "Le prélèvement", "Les intentions du joueur")]
    def verifier(sections, notice):
        assert "L'ouvrir" in sections[0]
        assert "World.secours" in sections[1] and "t + jours − 1" in sections[1]
        assert "ouvrir_grenier" in sections[2] and "OuvrirGrenier" in sections[2]
        assert "ouvrir_grenier" in notice and "secours" in notice
    notice = (sim / "README.md").read_text()
    verifier(sections, notice)
    with pytest.raises(AssertionError): verifier(["", "", ""], "")



def test_ouverture_cli_gestes(tmp_path):
    import subprocess
    import sys
    gestes = tmp_path / "gestes.json"
    sortie = tmp_path / "monde.json"
    # Le grain récolté au premier tick arrive avant le dépôt du tick 2.
    gestes.write_text(json.dumps([{"tick": 2, "intention": _ouverture(kg=100)}]))
    resultat = subprocess.run([sys.executable, "-m", "sim", "--ticks", "3", "--seed", "0",
                               "--gestes", str(gestes), "--monde-json", str(sortie)],
                              cwd=Path(__file__).parents[2], capture_output=True, text=True)
    assert resultat.returncode == 0, resultat.stderr
    document = json.loads(sortie.read_bytes())
    assert "maison_du_joueur" not in document and document["secours"]
    assert sum(kg for _, _, _, kg in document["secours"]) < 100

@pytest.mark.parametrize('fabrique', [_route_reference, _parcelle_reference, _batiment_reference])
def test_terres_depot(fabrique):
    monde = World.charger(0); geste = fabrique(monde) | {'cell': 10322, 'maison': 'grande-3'}
    monde.plans[10322] = deepcopy(monde.plans[min(monde.plans)])
    bourg = next(l for l in monde.cells[10322].lieux if l.rang == 0)
    for donnee in ('absente', 'inconnue', True, None, [], 'voisin', 'bourg', 'maitre', 'maitre inconnu', 'cellule'):
        copie, intention = deepcopy(monde), deepcopy(geste)
        lieu = next(l for l in copie.cells[10322].lieux if l.rang == 0)
        if donnee == 'absente': intention.pop('maison')
        elif donnee == 'voisin': intention['maison'] = 'seigneurie-3'
        elif donnee == 'bourg': copie.cells[10322].lieux = [l for l in copie.cells[10322].lieux if l.rang != 0]
        elif donnee == 'cellule': del copie.cells[10322]
        elif donnee == 'maitre': lieu.maitre = None
        elif donnee == 'maitre inconnu': lieu.maitre = 'inconnu'
        else: intention['maison'] = donnee
        avant = deepcopy(copie.__dict__)
        with pytest.raises(IntentionRefusee) as erreur: recevoir_intention(copie, intention)
        assert str(erreur.value) and copie.__dict__ == avant
        if donnee == 'voisin': assert str(erreur.value) == "ce lieu n'est pas à toi : grande-3"
    avant = monde.to_dict(); recevoir_intention(monde, geste)
    assert monde.to_dict() == avant and len(monde.intentions_en_attente) == 1
    monde.intentions_en_attente.clear(); bourg.maitre = 'seigneurie-3'
    with pytest.raises(IntentionRefusee, match="ce lieu n'est pas à toi : seigneurie-3"): recevoir_intention(monde, geste)
    recevoir_intention(monde, geste | {'maison': bourg.maitre})

def _terres_synthetiques(monde):
    from sim.model import EtatDeLieu
    monde.maisons = _monde_ouverture().maisons; monde.cells[1].lieux = [EtatDeLieu(0, 0, {}, maitre="seigneurie-1")]

@pytest.mark.parametrize('fabrique', [_route_reference, _parcelle_reference, _batiment_reference])
def test_terres_service(fabrique, monkeypatch):
    from sim import service
    from sim.tests.test_monde import _service_ia_en_processus
    journal, original = [], service.recevoir_intention
    def recevoir(monde, intention):
        assert serveur.verrou_tick.locked()
        resultat = original(monde, intention); journal.append(deepcopy(intention))
        return resultat
    monkeypatch.setattr(service, 'recevoir_intention', recevoir)
    with _service_ia_en_processus(ia=False) as (serveur, port):
        geste = fabrique(World.charger(0), 10103)
        def refuser(intention, raison):
            avant = deepcopy(serveur.world.__dict__), serveur.etat_publie, deepcopy(journal)
            statut, recu, _ = _poster(port, intention)
            assert statut == 400 and raison in recu['erreur']
            assert (serveur.world.__dict__, serveur.etat_publie, journal) == avant
        refuser(geste, 'départ non appliqué'); _poster(port, {'type': 'choisir_depart', 'seigneurie': _id('Émirat du Zab')})
        refuser(geste, 'départ non appliqué'); requete_service(port, '/tick?n=1', 'POST')
        for entree in json.loads((Path(__file__).parents[1] / 'gestes-exemple.json').read_text()):
            if entree['intention']['type'] == geste['type']: break
            assert _poster(port, entree['intention'])[0] == 200
            requete_service(port, '/tick?n=1', 'POST')
        serveur.world.plans[10322] = deepcopy(serveur.world.plans[10103])
        refuser(geste | {'cell': 10322, 'maison': 'grande-3'}, "ce lieu n'est pas à toi : grande-3")
        for identite in (None, 'grande-3'):
            intention = geste | {'maison': identite}
            if identite is None: intention.pop('maison')
            avant = serveur.world.to_dict()
            assert _poster(port, intention)[0] == 200
            assert serveur.world.to_dict() == avant and journal[-1]['maison'] == 'seigneurie-6'
            serveur.world.intentions_en_attente.clear()
        assert _poster(port, geste)[0] == 200; requete_service(port, '/tick?n=1', 'POST')
        assert serveur.world.to_dict() != avant

def test_terres_ia(monkeypatch):
    from sim import ia
    ia, monde, maisons = _ia_monde(); maison = maisons[0]
    monkeypatch.setattr(ia, 'maisons_de_l_ia', lambda m: [maison])
    bourg = next(l for l in monde.cells[maison.cell_id].lieux if l.rang == 0)
    cle = ia._cle_du_grenier(maison); bourg.maitre = next(m.id for m in monde.maisons if m.id != cle)
    assert ia.decider_intentions(monde, []) == []
    for maitre in (None, 'inconnu', True):
        bourg.maitre = maitre
        with pytest.raises(IntentionRefusee, match='maître absent ou inconnu'): ia.jouer_ia(monde, [])
        assert monde.intentions_en_attente == []
    bourg.maitre = cle; assert ia.decider_intentions(monde, [])
    monkeypatch.undo(); monde, releve, depots = World.charger(0), [], []
    original = ia.recevoir_intention
    def verifier(entrees):
        assert entrees and len({e['maison']['id'] for e in entrees}) > 0
        for e in entrees:
            identite = ('grande-' if e['maison']['sorte'] == 'grande maison' else 'seigneurie-') + str(e['maison']['id'])
            assert e['intention']['maison'] == identite
    def recevoir(m, intention):
        if 'cell' in intention:
            assert intention['maison'] == next(l.maitre for l in m.cells[intention['cell']].lieux if l.rang == 0)
        else:
            assert intention['type'] == 'fixer_part'
            assert any(lieu.maitre == intention['maison'] for cell in m.cells.values() for lieu in cell.lieux)
        depots.append(deepcopy(intention)); return original(m, intention)
    monkeypatch.setattr(ia, 'recevoir_intention', recevoir); alea = random.Random(0)
    for i in range(365):
        ia.jouer_ia(monde, releve); engine.tick(monde, alea, i)
    verifier(releve); assert depots == [e['intention'] for e in releve]
    faux = deepcopy(releve); faux[0]['maison']['id'] = next(e['maison']['id'] for e in releve if e['maison']['id'] != faux[0]['maison']['id'])
    for entrees in ([], faux):
        with pytest.raises(AssertionError): verifier(entrees)

def test_terres_gestes(tmp_path):
    import subprocess, sys
    fichier, sortie = tmp_path / 'gestes.json', tmp_path / 'monde.json'
    gestes = json.loads((Path(__file__).parents[1] / 'gestes-exemple.json').read_text())
    def jouer(entrees):
        sortie.unlink(missing_ok=True); fichier.write_text(json.dumps(entrees))
        return subprocess.run([sys.executable, '-m', 'sim', '--ticks', '10', '--seed', '0', '--gestes', str(fichier), '--monde-json', str(sortie)], cwd=Path(__file__).parents[2], capture_output=True, text=True)
    assert jouer(gestes).returncode == 0
    avant = sortie.read_bytes(); plan = json.loads(avant)['plans']['10103']
    assert all(plan[c] for c in ('rues', 'parcelles', 'batiments'))
    assert jouer(gestes).returncode == 0 and sortie.read_bytes() == avant
    for rang in range(len(gestes)):
        for maison in (None, 'seigneurie-3'):
            faux = json.loads(json.dumps(gestes))
            if maison is None: faux[rang]['intention'].pop('maison')
            else: faux[rang]['intention']['maison'] = maison
            resultat = jouer(faux)
            assert resultat.returncode == 2 and f'entrée {rang+1}' in resultat.stderr and not sortie.exists()


def test_ia_part_jour_et_fenetre(monde_ia_30):
    import zlib
    from sim import ia, constants as k
    monde = deepcopy(monde_ia_30)
    assert monde.ticks_ecoules == k.FENETRE_FLUX_TICKS
    assert set(range(k.FENETRE_FLUX_TICKS)) <= set(monde.flux.jours)
    propositions = _ia_pure(ia.decider_intentions, monde, [])
    parts = [p for p in propositions if p['intention']['type'] == 'fixer_part']
    assert parts
    for proposition in parts:
        cle = proposition['intention']['maison']
        assert zlib.crc32(cle.encode('utf-8')) % k.FENETRE_FLUX_TICKS == 0
    copie = deepcopy(monde)
    del copie.flux.jours[29]
    apres = [p for p in _ia_pure(ia.decider_intentions, copie, []) if p['intention']['type'] == 'fixer_part']
    assert apres == []
    with pytest.raises(AssertionError):
        assert apres


def test_ia_budget_routes_seules():
    from sim import constants as k
    ia, monde, maisons = _ia_monde()
    maison = maisons[0]
    couple = (maison.sorte, maison.id)
    cle = ia._cle_du_grenier(maison)
    annee = k.date_de_tick(monde.ticks_ecoules)['annee']

    def routes(releve):
        return [p for p in ia.decider_intentions(monde, releve)
                if p['intention']['type'] == 'tracer_route'
                and (p['maison']['sorte'], p['maison']['id']) == couple]

    assert routes([])
    part = {'tick': monde.ticks_ecoules, 'maison': {'sorte': maison.sorte, 'id': maison.id},
            'intention': {'type': 'fixer_part', 'maison': cle, 'part': k.PART_COUTUMIERE}, 'raison': {}}
    assert routes([part])
    route = {'tick': monde.ticks_ecoules, 'maison': {'sorte': maison.sorte, 'id': maison.id},
             'intention': {'type': 'tracer_route', 'maison': cle, 'cell': maison.cell_id,
                           'points': [[0, 0], [1, 0]], 'largeur_m': 4}, 'raison': {}}
    assert routes([route]) == []

    def compte_tout(releve):
        return {(e['maison']['sorte'], e['maison']['id']) for e in releve
                if k.date_de_tick(e['tick'])['annee'] == annee}

    assert couple in compte_tout([part])
    with pytest.raises(AssertionError):
        assert not routes([part])


def test_ia_part_biskra_batit():
    from sim import __main__ as cli, ia, constants as k
    gestes = json.loads((Path(__file__).parents[1] / 'gestes-exemple.json').read_text())
    _, monde = cli._simulate(46, 0, gestes=gestes)

    def parts_de(m):
        return [p for p in ia.decider_intentions(m, [])
                if p['intention']['type'] == 'fixer_part' and p['intention']['maison'] == 'seigneurie-6']

    propositions = parts_de(monde)
    assert len(propositions) == 1
    proposition = propositions[0]
    attendue = round(k.PART_COUTUMIERE + k.IA_PAS_DE_PART, k.DECIMALES_PART)
    assert proposition['intention']['part'] == attendue
    raison = proposition['raison']
    assert raison['part'] == k.PART_COUTUMIERE
    assert raison['salaires_a_venir_kg'] > 0 and raison['lieux_affames'] == 0
    assert raison['partis'] - raison['arrives'] < k.TAILLE_FOYER
    copie = deepcopy(monde)
    copie.greniers['seigneurie-6'][k.MARCHANDISE_NOURRITURE] = raison['reserve_gens_kg'] + 1
    encore = parts_de(copie)
    assert encore and encore[0]['intention']['part'] == attendue
    _, sans = cli._simulate(46, 0)
    lecture = _lire_raison_part(sans, 'seigneurie-6')
    assert lecture
    sans.greniers['seigneurie-6'][k.MARCHANDISE_NOURRITURE] = lecture['reserve_gens_kg'] + 1
    assert parts_de(sans) == []
    bloque = deepcopy(monde)
    bloque.greniers['seigneurie-6'][k.MARCHANDISE_NOURRITURE] = raison['reserve_voulue_kg']
    with pytest.raises(AssertionError):
        assert parts_de(bloque)
    releve = []
    ia.jouer_ia(monde, releve)
    engine.tick(monde, random.Random(0), monde.ticks_ecoules)
    assert monde.parts['seigneurie-6'] == attendue


def test_ia_part_sur_un_an(annee_ia):
    monde, releve, captures, lectures = annee_ia
    assert any(lectures.values())
    _controler_parts(releve, lectures, captures, monde)
    faux = deepcopy(releve)
    entree = next(e for e in faux if e['intention']['type'] == 'fixer_part')
    entree['raison']['partis'] += 1
    with pytest.raises(AssertionError):
        _controler_parts(faux, lectures, captures, monde)
    baisse = next(e for e in releve if e['intention']['type'] == 'fixer_part' and e['intention']['part'] < e['raison']['part'])
    retournee = deepcopy(releve)
    cible = next(e for e in retournee if e['tick'] == baisse['tick'] and e['intention']['type'] == 'fixer_part'
                 and e['intention']['maison'] == baisse['intention']['maison'])
    cible['intention'] = dict(cible['intention'], part=round(cible['raison']['part'] + cible['raison']['part'], 9))
    captures_hausse = deepcopy(captures)
    for rang, geste in enumerate(captures_hausse):
        if geste['type'] == 'fixer_part' and geste['maison'] == baisse['intention']['maison'] and geste['part'] == baisse['intention']['part']:
            captures_hausse[rang] = dict(geste, part=cible['intention']['part'])
            break
    with pytest.raises(AssertionError):
        _controler_parts(retournee, lectures, captures_hausse, monde)
    with pytest.raises(AssertionError):
        _controler_parts([], lectures, captures, monde)


def _controle_chemin_unique(monde, jouer):
    from sim import ia
    copie = deepcopy(monde)
    vues = []

    def greffier(m, intention):
        vues.append(deepcopy(intention))

    avant = deepcopy(copie.__dict__)
    original = ia.recevoir_intention
    ia.recevoir_intention = greffier
    try:
        releve = []
        jouer(copie, releve)
    finally:
        ia.recevoir_intention = original
    assert copie.__dict__ == avant
    assert vues == [e['intention'] for e in releve]
    assert any(i['type'] == 'fixer_part' for i in vues)


def test_ia_part_chemin_unique(monde_ia_30):
    from sim import ia
    _controle_chemin_unique(deepcopy(monde_ia_30), ia.jouer_ia)
    copie = deepcopy(monde_ia_30)
    releve = []
    ia.jouer_ia(copie, releve)
    engine.tick(copie, random.Random(0), copie.ticks_ecoules)
    decidees = [e for e in releve if e['intention']['type'] == 'fixer_part' and 'refus' not in e]
    assert decidees
    for entree in decidees:
        assert copie.parts[entree['intention']['maison']] == entree['intention']['part']

    def tricher(monde, releve):
        for proposition in ia.decider_intentions(monde, releve):
            intention = proposition['intention']
            if intention['type'] == 'fixer_part':
                monde.parts[intention['maison']] = intention['part']
            releve.append({'tick': monde.ticks_ecoules, **proposition})

    with pytest.raises(AssertionError):
        _controle_chemin_unique(deepcopy(monde_ia_30), tricher)


def test_ia_part_documentation():
    texte = (Path(__file__).parents[1] / 'MODELE.md').read_text(encoding='utf-8')
    titre = "## Les décisions et les gestes de l'IA"

    def controler(document):
        section = document.split(titre)[1].split('\n## ')[0]
        for mot in ('part_sur_projets_et_gens', 'RESERVE_VOULUE_JOURS',
                    'RESERVE_VOULUE_PART_DES_HABITANTS', 'IA_PAS_DE_PART', 'TAILLE_FOYER',
                    'affames', 'crc32', 'niveau 2', 'ms'):
            assert mot in section

    controler(texte)
    avant, apres = texte.split(titre)
    prive = avant + '\n## ' + apres.split('\n## ', 1)[1]
    with pytest.raises((AssertionError, IndexError)):
        controler(prive)
