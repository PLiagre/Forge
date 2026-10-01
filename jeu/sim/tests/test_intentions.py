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
        assert _poster(port, {"route": "essai"})[0] == HTTPStatus.OK
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
