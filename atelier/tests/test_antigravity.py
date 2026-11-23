"""Le harnais Antigravity CLI (`agy`) et la chaîne visuelle parallèle.

Aucun vrai appel réseau ni quota Google n'est consommé : l'exécuteur et GitHub
sont des doublures en mémoire.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from atelier import agents, consignes, lots
from atelier.agents import Appel
from atelier.fabrique import CHEMIN_MANIFESTE, enregistrer_asset
from atelier.projet import ARTISTE, Agent

from conftest import Agents, flux_agy, piloter

AGY = Agent("antigravity", "gemini-3.8-flash-medium")


# ------------------------------------------------------ harnais Antigravity
def test_antigravity_retire_toutes_les_cles_api_google(monkeypatch):
    for cle in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "NANOBANANA_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.setenv(cle, "cle-interdite")
    env = agents.environnement("antigravity")
    assert not ({"GEMINI_API_KEY", "GOOGLE_API_KEY", "NANOBANANA_API_KEY", "ANTHROPIC_API_KEY"} & set(env))


def test_antigravity_construit_argv_et_entree_stream_json():
    consigne = "Génère une planche 3x3 d'icônes."
    entree = json.loads(agents.entree(AGY, consigne))
    assert entree == {"event": "user", "message": {"content": consigne}}

    plan_argv = agents.argv(AGY, Appel(role=ARTISTE, consigne=consigne, lecture_seule=True), reprise=False)
    assert plan_argv[:6] == ["agy", "--input-format", "stream-json", "--output-format", "stream-json", "--model"]
    assert "--sandbox" in plan_argv and "--dangerously-skip-permissions" not in plan_argv
    assert "--conversation" not in plan_argv and consigne not in " ".join(plan_argv)

    etape_argv = agents.argv(
        AGY, Appel(role=ARTISTE, consigne=consigne, lecture_seule=False, session="conv-42", reprendre=True,
                   schema={"type": "object"}), reprise=True)
    assert "--dangerously-skip-permissions" in etape_argv and "--sandbox" not in etape_argv
    assert etape_argv[etape_argv.index("--conversation") + 1] == "conv-42"
    assert "--json-schema" in etape_argv


def test_lire_flux_antigravity_lit_sortie_images_et_session():
    brut = flux_agy(texte="Planche livrée.", sortie={"etat": "faite", "compte_rendu": "ok"},
                    session="conv-99", images=2)
    lu = agents.lire_flux(brut)
    assert lu.fini and lu.session == "conv-99"
    assert lu.sortie == {"etat": "faite", "compte_rendu": "ok"}
    assert lu.mesure["images"] == 2 and lu.mesure["duree"] == 12 and lu.mesure["tours"] == 2
    assert lu.mesure["modeles"]["gemini-3.8-flash-medium"]["cache_lu"] == 200


def test_quota_google_ou_auth_mettent_en_attente_sans_echec(tmp_path):
    for erreur_flux, cause in (
        ("RESOURCE_EXHAUSTED: Individual quota reached (resets in 4h)", "quota épuisé"),
        ("HTTP 429 QUOTA_EXHAUSTED on generate_image", "quota épuisé"),
        ("Authentication required: please sign in with agy", "session de l'abonnement expirée ou absente"),
    ):
        brut = flux_agy(texte="", statut="ERROR", erreur=erreur_flux)
        res = agents.invoquer(AGY, Appel(role=ARTISTE, consigne="test", lecture_seule=True),
                              tmp_path, 600, executeur=lambda *a: (1, brut, ""))
        assert res.attente and not res.reussi and cause in res.raison


def test_coupure_antigravity_garde_session_et_images(tmp_path):
    brut = flux_agy(texte="En cours", session="conv-77", images=1, coupe=True)
    res = agents.invoquer(AGY, Appel(role=ARTISTE, consigne="test", lecture_seule=False),
                          tmp_path, 600, executeur=lambda *a: (agents.CODE_COUPE, brut, "délai dépassé"))
    assert res.coupe and res.session == "conv-77" and res.mesure["images"] == 1 and res.mesure["coupe"]


# ----------------------------------------- déclenchement & chaîne parallèle
def _demande(asset_id="icones-ressources", type_asset="planche_icones", bloquant=False):
    return {
        "id": asset_id,
        "titre": f"Assets : {asset_id}",
        "type": type_asset,
        "description": "Neuf icônes médiévales (blé, fer, bois, pierre, or, laine, sel, vin, outils).",
        "destination": "3d/unity/Assets/Interface/Icones/Ressources",
        "dimensions": "128x128",
        "references_da": ["docs/interface/DA.md"],
        "bloquant": bloquant,
    }


def test_un_lot_de_code_declenche_automatiquement_un_lot_asset_deduplique(projet, gh, depot, tmp_path):
    gh.ajouter_issue(10, "Écran des stocks", ("lot", "pret", "interface"))
    # Deux demandes identiques + une demande 3D : seule une issue par id s'ouvre,
    # et le prop 3D reçoit aussi l'étiquette `pc`.
    plan_sortie = {
        "decision": "plan",
        "resume": "Afficher les stocks et leurs icônes.",
        "etapes": [{"titre": "Écran", "quoi": "Vue stocks", "qui": "chef", "tests": "pytest"}],
        "demandes_assets": [
            _demande("icones-ressources", "planche_icones", bloquant=False),
            _demande("icones-ressources", "planche_icones", bloquant=False),
            _demande("prop-puits-pierre", "prop_3d", bloquant=True),
        ],
    }
    p = piloter(projet, gh, depot, Agents({"sortie": plan_sortie}), tmp_path)
    p.tour()

    ouvertes = [lots.Lot.de(i) for i in gh.issues("open") if i["number"] != 10]
    assert len(ouvertes) == 2
    par_id = {l.asset_id: l for l in ouvertes}
    assert set(par_id) == {"icones-ressources", "prop-puits-pierre"}

    ic = par_id["icones-ressources"]
    assert ic.est_un_asset and ic.meneur == ARTISTE and ic.machine == "asset"
    assert "pc" not in ic.etiquettes and "python3 -m atelier.fabrique" in ic.corps

    p3d = par_id["prop-puits-pierre"]
    assert p3d.est_un_asset and p3d.meneur == ARTISTE and p3d.machine == "pc"
    assert "pc" in p3d.etiquettes

    # Seul l'asset bloquant ajoute une dépendance au lot demandeur.
    lot10 = lots.Lot.de(gh.issue(10))
    assert lot10.dependances == frozenset({p3d.numero})


def test_un_asset_deja_livre_dans_le_manifeste_n_est_pas_redemande(projet, gh, depot, tmp_path):
    gh.ajouter_issue(10, "Écran des stocks", ("lot", "pret", "interface"))
    enregistrer_asset(projet.racine / CHEMIN_MANIFESTE, asset_id="icones-ressources", type_asset="planche_icones",
                      fichiers=["3d/unity/Assets/Interface/Icones/ble.png"])
    plan_sortie = {
        "decision": "plan",
        "resume": "Afficher les stocks.",
        "etapes": [{"titre": "Écran", "quoi": "Vue", "qui": "chef", "tests": "pytest"}],
        "demandes_assets": [_demande("icones-ressources", "planche_icones")],
    }
    p = piloter(projet, gh, depot, Agents({"sortie": plan_sortie}), tmp_path)
    p.tour()
    assert [i["number"] for i in gh.issues("open")] == [10]


def test_la_chaine_visuelle_avance_en_parallele_quand_la_file_vps_est_pleine(projet, gh, depot, tmp_path):
    # File VPS pleine (capacité 1 par défaut) : #10 attend sa CI (plan + étape 1 faits).
    gh.ajouter_issue(10, "Lot monde en cours", ("lot", "en-cours", "monde"))
    gh.ajouter_pr(
        200, "lot/10-lot-monde-en-cours", brouillon=False, ci="attente",
        commentaires=[
            lots.marque(role="chef", etat=lots.PLAN, etapes=1, detail=[{"titre": "E1", "quoi": "q", "qui": "chef", "tests": "t"}]),
            lots.marque(role="chef", etat=lots.ETAPE, etape=1, fini=True, sha="a" * 40),
        ],
    )
    # Un lot d'asset est prêt : il a sa propre file `asset` et doit partir sans attendre #10.
    corps = consignes.corps_de_demande_asset(_demande("icones-ressources"), demandeur=10)
    gh.ajouter_issue(11, "Planche d'icônes", ("lot", "pret", "asset"), corps=corps)

    reponses = Agents(
        # Tour 1 : plan de l'artiste via `agy`, session serveur `conv-asset-1`.
        {"session": "conv-asset-1", "sortie": {
            "decision": "plan", "resume": "Générer la planche 3x3 et la découper.",
            "etapes": [{"titre": "Planche", "quoi": "Générer et découper", "qui": "artiste",
                        "tests": "python3 -m atelier.fabrique controler --strict"}],
        }},
        # Tour 2 : étape 1 reprise avec `--conversation conv-asset-1`.
        {"session": "conv-asset-1", "images": 1,
         "fichiers": {"assets/manifeste.json": "{}"},
         "sortie": {"etat": "faite", "compte_rendu": "9 icônes découpées et vérifiées."}},
    )
    p = piloter(projet, gh, depot, reponses, tmp_path)
    p.tour()
    assert "en-cours" in gh.etiquettes(11)
    assert reponses.appels[0]["argv"][0] == "agy" and not reponses.appels[0]["reprise"]

    p.tour()
    assert len(reponses.appels) == 2
    assert reponses.appels[1]["reprise"] and reponses.appels[1]["session"] == "conv-asset-1"
    assert "1 image(s)" in "\n".join(p.lignes) or any("image" in g[2] for g in gh.gestes if g[0] == "commenter_pr")
