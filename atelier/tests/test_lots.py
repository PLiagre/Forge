"""L'état d'un lot, dérivé de GitHub, et la décision de l'action suivante."""

from __future__ import annotations

import pytest

from atelier import lots
from atelier.github import etat_des_controles
from atelier.lots import Lot, action_suivante, marque, marques


def _issue(numero, titre="Un lieu s'ouvre", etiquettes=("lot", "pret"), jalon="J1 — Le pont"):
    return {"number": numero, "title": titre, "body": "", "labels": [{"name": e} for e in etiquettes],
            "milestone": {"title": jalon} if jalon else None}


def test_un_lot_se_lit_dans_son_issue():
    lot = Lot.de(_issue(12, "Le service local lit un lieu", ("lot", "en-cours", "pc")))
    assert lot.etat == "en-cours" and lot.machine == "pc" and lot.jalon == 1
    assert lot.branche("lot/") == "lot/12-le-service-local-lit-un-lieu"
    assert lot.brief("docs/briefs") == "docs/briefs/12-le-service-local-lit-un-lieu.md"
    assert lots.slug("Élévation : « la » côte !") == "elevation-la-cote"


def test_les_marques_du_pilote_se_relisent_dans_les_commentaires():
    corps = f"texte\n\n{marque(role='relecteur', sha='abc', verdict='ACCEPTE')}"
    assert marques([{"body": corps}, {"body": "rien"}, {"body": "<!-- atelier {cassé -->"}]) == [
        {"role": "relecteur", "sha": "abc", "verdict": "ACCEPTE"}]


def test_le_jalon_courant_est_le_premier_ouvert():
    bruts = [{"number": 2, "title": "J2 — Le geste", "state": "open"},
             {"number": 1, "title": "J1 — Le pont", "state": "closed"},
             {"number": 9, "title": "Divers", "state": "open"}]
    assert lots.jalon_courant(lots.jalons(bruts)).numero == 2


def test_le_lot_suivant_pret_d_abord_puis_idee_et_machine_libre():
    liste = [Lot.de(_issue(5, etiquettes=("lot", "idee"))), Lot.de(_issue(9, etiquettes=("lot", "pret"))),
             Lot.de(_issue(3, etiquettes=("lot", "pret", "pc"))), Lot.de(_issue(1, jalon="J2 — x"))]
    assert lots.a_prendre(liste, 1, {"vps": True, "pc": True}).numero == 3
    assert lots.a_prendre(liste, 1, {"vps": True, "pc": False}).numero == 9
    assert lots.a_prendre(liste[:1], 1, {"vps": True, "pc": False}).numero == 5
    assert lots.a_prendre(liste, 1, {"vps": False, "pc": False}) is None
    assert lots.a_prendre(liste, None, {"vps": True, "pc": True}) is None


def _pr(**champs):
    base = {"number": 7, "state": "OPEN", "headRefOid": "tete", "mergeable": "MERGEABLE", "autoMergeRequest": None}
    base.update(champs)
    return base


FAIT = {"role": "codeur", "etat": "fait", "agent": "codex/sol", "sha": "tete"}


@pytest.mark.parametrize("pr,ci,liste,attendu", [
    (None, "vert", [], "chef"),
    (_pr(state="MERGED"), "vert", [], "livrer"),
    (_pr(state="CLOSED"), "vert", [], "bloquer"),
    (_pr(), "vert", [], "coder"),
    (_pr(mergeable="CONFLICTING"), "vert", [FAIT], "conflit"),
    (_pr(), "attente", [FAIT], "attendre_ci"),
    (_pr(), "rouge", [FAIT], "corriger_ci"),
    (_pr(), "vert", [FAIT], "relire"),
    (_pr(), "vert", [FAIT, {"role": "relecteur", "sha": "vieille", "verdict": "ACCEPTE"}], "relire"),
    (_pr(), "vert", [FAIT, {"role": "relecteur", "sha": "tete", "verdict": "ACCEPTE"}], "fusionner"),
    (_pr(autoMergeRequest={"x": 1}), "vert", [FAIT, {"role": "relecteur", "sha": "tete", "verdict": "ACCEPTE"}], "attendre_fusion"),
    (_pr(), "vert", [FAIT, {"role": "relecteur", "sha": "tete", "verdict": "CORRIGER"}], "corriger_relecture"),
])
def test_l_action_suivante(pr, ci, liste, attendu):
    assert action_suivante(pr, ci, liste, corrections_max=2).nom == attendu


def test_trois_passages_du_codeur_puis_bloque():
    trois = [FAIT, dict(FAIT, etat="fait"), dict(FAIT, etat="fait")]
    assert action_suivante(_pr(), "rouge", trois[:2], corrections_max=2).nom == "corriger_ci"
    action = action_suivante(_pr(), "rouge", trois, corrections_max=2)
    assert action.nom == "bloquer" and "2 correction" in action.raison
    verdict = {"role": "relecteur", "sha": "tete", "verdict": "CORRIGER"}
    assert action_suivante(_pr(), "vert", trois + [verdict], corrections_max=2).nom == "bloquer"
    echecs = [{"role": "codeur", "etat": "echec"}] * 3
    assert action_suivante(_pr(), "vert", echecs, corrections_max=2).nom == "bloquer"


def test_un_envoi_au_pc_attend_son_retour_puis_se_relance():
    envoi = {"role": "codeur_3d", "etat": "envoye"}
    assert action_suivante(_pr(), "vert", [envoi], corrections_max=2, role_codeur="codeur_3d",
                           heures_depuis_envoi_pc=2).nom == "attendre_pc"
    assert action_suivante(_pr(), "vert", [envoi], corrections_max=2, role_codeur="codeur_3d",
                           heures_depuis_envoi_pc=30).nom == "relancer_pc"
    retour = dict(FAIT, role="codeur_3d")
    assert action_suivante(_pr(), "vert", [envoi, retour], corrections_max=2, role_codeur="codeur_3d").nom == "relire"


ENVOI = {"role": "codeur_3d", "etat": "envoye"}
ATTENTE = {"role": "codeur_3d", "etat": "attente"}
ECHEC_PC = {"role": "codeur_3d", "etat": "echec", "agent": "cursor/opus-high"}


def test_une_attente_du_pc_ne_brule_pas_d_essai_et_se_renvoie_apres_une_heure():
    # Tous les agents du PC en attente (quota) : le PC le dit par une marque,
    # qui répond à l'envoi sans compter comme un passage du codeur.
    liste = [ENVOI, ATTENTE]
    assert action_suivante(_pr(), "vert", liste, corrections_max=2, role_codeur="codeur_3d",
                           heures_depuis_attente_pc=0.2).nom == "attendre_pc"
    renvoi = action_suivante(_pr(), "vert", liste, corrections_max=2, role_codeur="codeur_3d",
                             heures_depuis_attente_pc=1.2)
    assert (renvoi.nom, renvoi.essai) == ("coder", 0)
    # Trois attentes après un échec : un seul essai brûlé, le lot n'est pas bloqué.
    longue = [ENVOI, ECHEC_PC] + [ENVOI, ATTENTE] * 3
    action = action_suivante(_pr(), "vert", longue, corrections_max=2, role_codeur="codeur_3d",
                             heures_depuis_attente_pc=2)
    assert (action.nom, action.essai) == ("coder", 1)
    # Renvoyé après l'attente : on attend de nouveau la réponse du PC.
    assert action_suivante(_pr(), "vert", liste + [ENVOI], corrections_max=2, role_codeur="codeur_3d",
                           heures_depuis_envoi_pc=0.1, heures_depuis_attente_pc=1.2).nom == "attendre_pc"


def test_une_reprise_remet_les_compteurs_a_zero():
    reprise = {"role": "pilote", "etat": "reprise"}
    trois_echecs = [ENVOI, ECHEC_PC] * 3
    assert action_suivante(_pr(), "vert", trois_echecs, corrections_max=2, role_codeur="codeur_3d").nom == "bloquer"
    action = action_suivante(_pr(), "vert", trois_echecs + [reprise], corrections_max=2, role_codeur="codeur_3d")
    assert (action.nom, action.essai) == ("coder", 0)
    # Le travail déjà fait reste : un lot repris après trois « CORRIGER »
    # repart en correction de la dernière revue, pas de zéro.
    verdict = {"role": "relecteur", "sha": "tete", "verdict": "CORRIGER"}
    corrige = [FAIT, verdict, FAIT, verdict, FAIT, verdict]
    assert action_suivante(_pr(), "vert", corrige, corrections_max=2).nom == "bloquer"
    action = action_suivante(_pr(), "vert", corrige + [reprise], corrections_max=2)
    assert (action.nom, action.essai) == ("corriger_relecture", 0)


def test_les_echecs_du_chef_comptent_depuis_le_dernier_blocage():
    echec = {"role": "chef", "etat": "echec"}
    bloque = {"role": "pilote", "etat": "bloque"}
    assert lots.echecs_du_chef([echec, echec]) == 2
    assert lots.echecs_du_chef([echec, echec, bloque]) == 0
    assert lots.echecs_du_chef([echec, echec, bloque, echec]) == 1


def test_les_decoupes_imbriquees_retiennent_tous_leurs_ancetres():
    # #119 découpé en #183 et #184, puis #183 en #185 et #186 : tant que #185
    # est ouvert, ce qui dépend de #119 ou de #183 attend, même #184 fermé.
    ouvert = Lot.de(dict(_issue(185), body="Le lecteur.\n\nDécoupé du lot #183 par le chef."))
    ferme = Lot.de(dict(_issue(183), body="Le client.\n\nDécoupé du lot #119 par le chef."))
    assert lots.bloquantes([ouvert], [ferme]) == frozenset({185, 183, 119})
    assert lots.bloquantes([ouvert]) == frozenset({185, 183})
    # Une découpe qui se citerait elle-même ne boucle pas.
    boucle = Lot.de(dict(_issue(7), body="Découpé du lot #7 par le chef."))
    assert lots.bloquantes([boucle]) == frozenset({7})


def test_les_auteurs_d_un_lot():
    # Les familles de modèles qui ont écrit du code : codex/sol est d'OpenAI.
    liste = [FAIT, {"role": "codeur_3d", "etat": "fait", "agent": "claude/opus"},
             {"role": "codeur", "etat": "echec", "agent": "cursor/grok"}, {"role": "chef", "agent": "claude/x"}]
    assert lots.auteurs(liste) == frozenset({"gpt", "claude"})
    # Le même modèle par un autre outil est le même auteur.
    assert lots.auteurs([{"role": "codeur_3d", "etat": "fait", "agent": "cursor/claude-opus-5-5-high"}]) == {"claude"}


def _check(nom, status="COMPLETED", conclusion="SUCCESS", quand="2026-09-27T10:00:00Z"):
    return {"__typename": "CheckRun", "name": nom, "status": status, "conclusion": conclusion, "startedAt": quand}


def test_l_etat_des_controles_exiges():
    assert etat_des_controles({"statusCheckRollup": [_check("tests"), _check("gitleaks")]})[0] == "vert"
    assert etat_des_controles({"statusCheckRollup": [_check("tests")]})[0] == "attente"
    assert etat_des_controles({"statusCheckRollup": [_check("tests", conclusion="FAILURE"), _check("gitleaks")]})[0] == "rouge"
    assert etat_des_controles({"statusCheckRollup": [_check("tests", status="IN_PROGRESS", conclusion=""),
                                                     _check("gitleaks")]})[0] == "attente"
    # Un contrôle non exigé rouge ne retient rien ; un rejeu récent l'emporte.
    rejeu = [_check("tests", conclusion="FAILURE", quand="2026-09-27T09:00:00Z"), _check("tests"),
             _check("gitleaks"), _check("unity", conclusion="FAILURE")]
    assert etat_des_controles({"statusCheckRollup": rejeu})[0] == "vert"


def test_un_lot_attend_ses_dependances_ouvertes():
    service = Lot.de(dict(_issue(12, "Le service"), body=""))
    panneau = Lot.de(dict(_issue(13, "Le panneau", ("lot", "pret", "pc")), body="Ce qu'il fait.\n\nDépend de : #12, #9"))
    assert panneau.dependances == frozenset({12, 9})
    assert lots.a_prendre([panneau], 1, {"vps": True, "pc": True}, frozenset({12})) is None
    assert lots.a_prendre([panneau], 1, {"vps": True, "pc": True}, frozenset({14})).numero == 13
    # Le formulaire écrit « ### Dépend de », puis la valeur au paragraphe suivant.
    formulaire = "### Jalon\n\nJ1 — Le pont\n\n### Dépend de\n\n#3, #4\n\n### Ce que ça doit faire\n\nVoir #99."
    assert Lot.de(dict(_issue(14), body=formulaire)).dependances == frozenset({3, 4})
    # Une référence plus loin dans le texte n'est pas une dépendance.
    assert Lot.de(dict(_issue(15), body="Dépend de : #12\n\nDécoupé du lot #10.")).dependances == frozenset({12})
