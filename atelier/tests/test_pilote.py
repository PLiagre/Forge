"""Le chemin d'un lot, de la fiche à la fusion, et ce qui arrive quand ça coince.

Chaque défaut mesuré de l'ancienne chaîne a ici le test qui l'aurait vu :
une boucle de dépendances, un appel coupé sans coût ni trace, une décision
arrivée sans ses raisons, un test changé sans raison, une relecture réduite
à sa dernière phrase, un test qui écrit dans le vrai journal.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from atelier import garde_commandes, lots
from atelier.pilote import Pilote

from conftest import Agents, piloter

FICHE = """## Ce que je joue de plus
Je lève une armée.

## Ce que je vois samedi
Une armée sur la carte.

## La règle du monde
Les soldats sont des habitants. Niveau 2.

## Les preuves
- python3 -m pytest jeu/sim/tests/test_armees.py -q
"""
ETAPES = [{"titre": "La règle de la levée", "quoi": "armees.py", "qui": "chef", "tests": "test_armees.py -k levee"},
          {"titre": "Les données", "quoi": "jeu/data/armees.toml", "qui": "developpeur", "tests": "test_armees.py -k donnees"}]
PLAN = {"sortie": {"decision": "plan", "resume": "La levée, puis ses données.", "etapes": ETAPES}}


def faite(fichiers=None, **plus):
    return {"sortie": {"etat": "faite", "compte_rendu": "C'est fait.", **plus},
            "fichiers": fichiers if fichiers is not None else {"jeu/sim/armees.py": "x = 1\n"}}


ACCEPTE = {"sortie": {"verdict": "ACCEPTE", "resume": "Tout tient.", "constats": [],
                      "promesse_joueur_tenue": True, "tests_changes_justifies": True}}


def _marques(gh, numero, *, pr=False):
    source = gh.prs_ if pr else gh.issues_
    return lots.marques(source[numero]["comments"])


def _pr_du_lot(gh, numero):
    return next(n for n, p in gh.prs_.items() if p["headRefName"].startswith(f"lot/{numero}-"))


def _jusqu_a_la_relecture(projet, gh, depot, tmp_path, *reponses, etiquettes=("lot", "pret", "monde")):
    """Un lot dont le plan et les deux étapes sont faits, CI verte : il attend sa relecture."""
    gh.ajouter_issue(10, "Lever une armée", etiquettes, corps=FICHE)
    agents = Agents(PLAN, faite(), faite(), *reponses)
    pilote = piloter(projet, gh, depot, agents, tmp_path)
    for _ in range(3):
        pilote.tour()
    gh.ci(_pr_du_lot(gh, 10), "vert")
    return pilote, agents, _pr_du_lot(gh, 10)


def test_un_lot_va_de_la_fiche_a_la_fusion(projet, gh, depot, tmp_path):
    gh.ajouter_issue(10, "Lever une armée", corps=FICHE)
    agents = Agents(PLAN, faite(), faite(), ACCEPTE)
    pilote = piloter(projet, gh, depot, agents, tmp_path)

    pilote.tour()
    numero_pr = _pr_du_lot(gh, 10)
    assert "en-cours" in gh.etiquettes(10) and gh.prs_[numero_pr]["isDraft"]
    assert "- [ ] **1. La règle de la levée**" in gh.prs_[numero_pr]["body"]
    assert "Closes #10" in gh.prs_[numero_pr]["body"]
    assert not depot.changements(depot.racine / "chantiers" / "10"), "le plan n'écrit aucun fichier"

    pilote.tour()
    assert "- [x] **1. La règle de la levée**" in gh.prs_[numero_pr]["body"]
    assert "- [ ] **2. Les données**" in gh.prs_[numero_pr]["body"] and gh.prs_[numero_pr]["isDraft"]

    pilote.tour()
    assert not gh.prs_[numero_pr]["isDraft"], "le plan fini, la PR sort du brouillon"
    assert pilote.tour() == ["#10 attendre_ci — PR #%d" % numero_pr]

    gh.ci(numero_pr, "vert")
    pilote.tour()
    assert ("fusion_auto", numero_pr) in gh.gestes
    assert agents.modeles() == ["opus", "opus", "opus", "opus"]
    # Une seule session pour le meneur, reprise à chaque étape ; le relecteur a la sienne.
    plan, etape1, etape2, relecture = agents.appels
    assert not plan["reprise"] and etape1["reprise"] and etape2["reprise"]
    assert plan["session"] == etape1["session"] == etape2["session"] != ""
    assert relecture["session"] == "" and "--permission-mode" in relecture["argv"]

    gh.prs_[numero_pr].update(state="MERGED", mergedAt="2026-11-16T12:00:00Z")
    pilote.tour()
    assert "livre" in gh.etiquettes(10) and gh.issues_[10]["state"] == "CLOSED"


def test_la_session_reprise_ne_recoit_que_sa_tache_et_la_session_perdue_recoit_tout(projet, gh, depot, tmp_path):
    gh.ajouter_issue(10, "Lever une armée", corps=FICHE)
    perdue = {"code": 1, "brut": "", "erreur": "No conversation found with session ID: abc"}
    agents = Agents(PLAN, faite(), perdue, faite())
    pilote = piloter(projet, gh, depot, agents, tmp_path)
    for _ in range(3):
        pilote.tour()
    _, etape1, refusee, rouverte = agents.appels
    assert "ÉTAPE 1 SUR 2" in etape1["consigne"] and "Je lève une armée" not in etape1["consigne"]
    assert refusee["reprise"] and not rouverte["reprise"], "la session introuvable est rouverte sous le même nom"
    assert "Je lève une armée" in rouverte["consigne"] and "ÉTAPE 2 SUR 2" in rouverte["consigne"]
    assert "[faite] La règle de la levée" in rouverte["consigne"]


def test_le_chef_confie_au_developpeur_dans_sa_session(projet, gh, depot, tmp_path):
    gh.ajouter_issue(10, "Lever une armée", corps=FICHE)
    agents = Agents(PLAN, faite(), faite())
    pilote = piloter(projet, gh, depot, agents, tmp_path)
    for _ in range(3):
        pilote.tour()
    plan, _, etape2 = agents.appels
    sous = json.loads(etape2["argv"][etape2["argv"].index("--agents") + 1])
    assert sous["developpeur"]["model"] == "sonnet"
    permis = etape2["argv"][etape2["argv"].index("--allowedTools") + 1]
    assert "Agent" in permis.split(",") and "Confie-la au sous-agent `developpeur`" in etape2["consigne"]
    assert "--agents" not in plan["argv"], "le plan ne confie rien"
    # Un sous-agent lancé en arrière-plan laisserait la session rendre la main sans son résultat.
    assert etape2["env"]["CLAUDE_CODE_DISABLE_BACKGROUND_TASKS"] == "1"
    assert not any(cle in etape2["env"] for cle in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY"))


def test_un_lot_simple_est_mene_par_le_developpeur_seul(projet, gh, depot, tmp_path):
    gh.ajouter_issue(10, "Les noms des villes", ("lot", "pret", "interface", "simple"), corps=FICHE)
    agents = Agents(PLAN, faite())
    pilote = piloter(projet, gh, depot, agents, tmp_path)
    pilote.tour()
    pilote.tour()
    assert agents.modeles() == ["sonnet", "sonnet"]
    assert "--agents" not in agents.appels[1]["argv"]
    assert _marques(gh, _pr_du_lot(gh, 10), pr=True)[0]["role"] == "developpeur"


def test_le_plan_lit_sans_ecrire_et_la_garde_refuse_la_suite_entiere(projet, gh, depot, tmp_path):
    """Le défaut : l'agent qui écrivait le brief lançait la suite entière ou
    dix ans de simulation, et se faisait couper, travail perdu."""
    gh.ajouter_issue(10, "Lever une armée", corps=FICHE)
    agents = Agents(PLAN)
    piloter(projet, gh, depot, agents, tmp_path).tour()
    argv = agents.appels[0]["argv"]
    assert argv[argv.index("--permission-mode") + 1] == "default"
    interdits = argv[argv.index("--disallowedTools") + 1]
    assert "Edit" in interdits and "Write" in interdits and "Bash(git push:*)" in interdits
    reglages = json.loads(argv[argv.index("--settings") + 1])
    commande = reglages["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    assert "garde_commandes.py" in commande and commande.endswith(" 400")

    assert garde_commandes.refus("python3 -m pytest jeu -q", 400)
    assert garde_commandes.refus("cd jeu && py -m pytest sim/tests/ -q -n auto", 400)
    assert garde_commandes.refus("python3 -m forge --ticks 3650 --seed 0", 400)
    assert not garde_commandes.refus("python3 -m pytest jeu/sim/tests/test_lieux.py -q -k ouverture", 400)
    assert not garde_commandes.refus("python3 -m pytest atelier/tests -q", 400)
    assert not garde_commandes.refus("python3 -m forge --ticks 365 --seed 0", 400)
    assert not garde_commandes.refus("git log --oneline -5", 400)


def test_un_appel_coupe_garde_son_cout_sa_trace_et_son_travail(projet, gh, depot, tmp_path, sans_le_vrai_dossier_personnel):
    """Le défaut : un appel coupé par son délai n'écrivait ni coût ni trace, et son travail était perdu."""
    gh.ajouter_issue(10, "Lever une armée", corps=FICHE)
    coupee = {"coupe": True, "fichiers": {"jeu/sim/armees.py": "x = 1\n"}}
    agents = Agents(PLAN, coupee, faite())
    pilote = piloter(projet, gh, depot, agents, tmp_path)
    pilote.tour()
    pilote.tour()
    numero_pr = _pr_du_lot(gh, 10)
    coupe = _marques(gh, numero_pr, pr=True)[-1]
    assert coupe["etat"] == lots.COUPE and coupe["mesure"]["coupe"] is True
    assert coupe["mesure"]["modeles"]["claude-opus-5-5"]["sortie"] == 200, "les jetons d'un appel coupé sont relevés"
    assert coupe["mesure"]["limites"] == {"cinq_heures": 0.2, "semaine": 0.05}
    assert ("enregistrer", "Lot #10 — étape 1, coupée par le délai") in depot.gestes, "ce qui était écrit part"
    faits = [json.loads(l) for l in (tmp_path / "journal.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [f for f in faits if f["action"] == "appel" and f["mesure"].get("coupe")]
    trace = agents.appels[1]["trace"]
    assert trace is not None and Path(trace).is_file() and sans_le_vrai_dossier_personnel in Path(trace).parents

    pilote.tour()
    assert agents.appels[2]["reprise"] and "coupé par son délai" in agents.appels[2]["consigne"]
    assert lots.etapes_faites(_marques(gh, numero_pr, pr=True)) == {1}


def test_trois_coupures_de_suite_arretent_le_lot(projet, gh, depot, tmp_path):
    gh.ajouter_issue(10, "Lever une armée", corps=FICHE)
    agents = Agents(PLAN, {"coupe": True}, {"coupe": True}, {"coupe": True})
    pilote = piloter(projet, gh, depot, agents, tmp_path)
    for _ in range(5):
        pilote.tour()
    assert "bloque" in gh.etiquettes(10)
    assert "coupé par son délai 3 fois de suite" in gh.dits(10)


def test_le_quota_fait_attendre_sans_compter_d_essai(projet, gh, depot, tmp_path):
    gh.ajouter_issue(10, "Lever une armée", corps=FICHE)
    quota = {"code": 1, "brut": "", "erreur": "You've hit your 5-hour limit · resets 9:30pm"}
    agents = Agents(quota, quota, PLAN)
    pilote = piloter(projet, gh, depot, agents, tmp_path)
    lignes = pilote.tour()
    assert any("attente" in l and "quota épuisé" in l for l in lignes)
    assert not [m for m in _marques(gh, 10) if m.get("role") == "chef"], "une attente ne laisse aucune marque"
    pilote.tour()
    pilote.tour()
    assert lots.plan_du_lot(_marques(gh, _pr_du_lot(gh, 10), pr=True)) is not None


def test_les_chemins_interdits_sont_retires(projet, gh, depot, tmp_path):
    gh.ajouter_issue(10, "Lever une armée", corps=FICHE)
    agents = Agents(PLAN, faite({"jeu/sim/armees.py": "x = 1\n", "atelier/pilote.py": "tricher\n",
                                 ".github/workflows/tests.yml": "plus de tests\n"}))
    pilote = piloter(projet, gh, depot, agents, tmp_path)
    pilote.tour()
    pilote.tour()
    retires = next(g[1] for g in depot.gestes if g[0] == "annuler")
    assert set(retires) == {"atelier/pilote.py", ".github/workflows/tests.yml"}
    assert "hors de portée d'un lot" in gh.dits(_pr_du_lot(gh, 10), pr=True)


def test_deux_lots_qui_s_attendent_sont_vus_et_le_cto_denoue_la_boucle(projet, gh, depot, tmp_path):
    """Le défaut : deux lots s'attendaient l'un l'autre, et rien ne le disait."""
    gh.ajouter_issue(10, "La règle", corps=FICHE + "\nDépend de : #11\n")
    gh.ajouter_issue(11, "L'écran", ("lot", "pret", "interface"), corps=FICHE + "\nDépend de : #10\n")
    denoue = {"sortie": {"decision": "relancer", "pourquoi": "l'écran attend la règle, pas l'inverse",
                         "consigne": "Rien à changer : la dépendance vers #10 était la bonne.",
                         "dependances_a_retirer": [10]}}
    agents = Agents(denoue, PLAN)
    pilote = piloter(projet, gh, depot, agents, tmp_path)
    assert lots.boucles([lots.Lot.de(gh.issue(n)) for n in (10, 11)]) == [(10, 11)]

    pilote.tour()
    assert "boucle de dépendances : #10 → #11 → #10" in gh.dits(11)
    assert any(m.get("etat") == lots.BLOQUE and m.get("boucle") == [10, 11] for m in _marques(gh, 11))
    assert "boucle de dépendances" in gh.dits(10)
    assert agents.modeles() == ["fable"], "le CTO est appelé dans le même tour"
    assert "boucle de dépendances" in agents.appels[0]["consigne"]
    assert "#10" not in gh.issues_[11]["body"].split("Les preuves")[1], "la dépendance de trop est retirée"
    assert "pret" in gh.etiquettes(11)

    pilote.tour()
    assert not lots.boucles([lots.Lot.de(gh.issue(n)) for n in (10, 11)])
    assert lots.Lot.de(gh.issue(10)).dependances == {11}


def test_la_decision_du_cto_arrive_en_entier_au_meneur(projet, gh, depot, tmp_path):
    """Le défaut : une décision n'arrivait au développeur que par sa lettre, sans ses raisons ni ses bornes."""
    gh.ajouter_issue(10, "Lever une armée", corps=FICHE)
    question = {"sortie": {"decision": "question", "question": {
        "texte": "La levée prend-elle un homme par foyer ?",
        "options": [{"lettre": "A", "reponse": "un homme par foyer", "cout": "vide les champs"},
                    {"lettre": "B", "reponse": "un homme pour dix foyers", "cout": "de petites armées"}],
        "recommandation": {"lettre": "B", "pourquoi": "le monde doit tenir"}}}}
    tranche = {"sortie": {"decision": "trancher", "reponse": "b", "pourquoi": "la décision 35 garde les champs",
                          "bornes": "ne touche pas à la natalité",
                          "a_revoir_samedi": "la levée prend un homme pour dix foyers"}}
    agents = Agents(question, tranche, PLAN)
    pilote = piloter(projet, gh, depot, agents, tmp_path)

    pilote.tour()
    assert "bloque" in gh.etiquettes(10) and "La levée prend-elle un homme par foyer ?" in gh.dits(10)
    pilote.tour()
    assert agents.modeles()[-1] == "fable" and "pret" in gh.etiquettes(10)
    decision = next(m for m in _marques(gh, 10) if m.get("etat") == lots.DECISION)
    assert decision["reponse"] == "B — un homme pour dix foyers" and decision["a_revoir"]
    pilote.tour()
    consigne = agents.appels[-1]["consigne"]
    for attendu in ("La levée prend-elle un homme par foyer ?", "B — un homme pour dix foyers",
                    "la décision 35 garde les champs", "ne touche pas à la natalité"):
        assert attendu in consigne
    assert agents.appels[-1]["reprise"], "le meneur reprend la session où il a posé sa question"


def test_la_consigne_du_proprietaire_suit_le_lot(projet, gh, depot, tmp_path):
    gh.ajouter_issue(10, "Lever une armée", corps=FICHE)
    gh.commentaire_humain(10, "La caserne d'abord, les soldats après.")
    pilote, agents, _ = _jusqu_a_la_relecture_deja_ouvert(projet, gh, depot, tmp_path)
    pilote.tour()
    for appel in agents.appels:
        assert "La caserne d'abord, les soldats après." in appel["consigne"]


def _jusqu_a_la_relecture_deja_ouvert(projet, gh, depot, tmp_path):
    agents = Agents(PLAN, faite(), faite(), ACCEPTE)
    pilote = piloter(projet, gh, depot, agents, tmp_path)
    for _ in range(3):
        pilote.tour()
    gh.ci(_pr_du_lot(gh, 10), "vert")
    return pilote, agents, _pr_du_lot(gh, 10)


def test_un_test_change_sans_raison_est_dit_et_juge(projet, gh, depot, tmp_path):
    """Le défaut : des tests existants étaient basculés sur un « monde d'avant » au lieu de juger le monde livré."""
    depot.etats_ = [("M", "jeu/sim/tests/test_faim.py"), ("M", "jeu/sim/tests/test_part.py"),
                    ("A", "jeu/sim/tests/test_armees.py"), ("M", "jeu/sim/armees.py")]
    gh.ajouter_issue(10, "Lever une armée", corps=FICHE)
    declare = faite(tests_changes=[{"fichier": "jeu/sim/tests/test_faim.py", "pourquoi": "les soldats ne mangent plus au foyer"}])
    complaisant = {"sortie": {"verdict": "ACCEPTE", "resume": "Bien.", "constats": [],
                              "promesse_joueur_tenue": True, "tests_changes_justifies": False}}
    agents = Agents(PLAN, declare, faite(), complaisant)
    pilote = piloter(projet, gh, depot, agents, tmp_path)
    for _ in range(3):
        pilote.tour()
    numero_pr = _pr_du_lot(gh, 10)
    corps = gh.prs_[numero_pr]["body"]
    assert "- `jeu/sim/tests/test_faim.py` : les soldats ne mangent plus au foyer" in corps
    assert "- `jeu/sim/tests/test_part.py` : ⚠️ modifié sans raison donnée" in corps
    assert "test_armees.py" not in corps.split("## Tests changés")[1], "un test ajouté n'est pas un test changé"

    gh.ci(numero_pr, "vert")
    pilote.tour()
    consigne = agents.appels[-1]["consigne"]
    assert "modifiés sans qu'une raison soit donnée : `jeu/sim/tests/test_part.py`" in consigne
    assert "monde d'avant" in consigne
    verdict = next(m for m in _marques(gh, numero_pr, pr=True) if m.get("verdict"))
    assert verdict["verdict"] == "CORRIGER", "un ACCEPTE qui dit les tests changés injustifiés se contredit"
    assert ("fusion_auto", numero_pr) not in gh.gestes


def test_la_relecture_garde_tout_ce_que_le_relecteur_a_ecrit(projet, gh, depot, tmp_path):
    """Le défaut : le texte d'une relecture pouvait se réduire à sa dernière phrase."""
    corriger = {"texte": "CORRIGER.", "sortie": {
        "verdict": "CORRIGER", "resume": "La levée crée des hommes qui n'existent pas.",
        "constats": [{"fichier": "jeu/sim/armees.py", "ligne": 42, "gravite": "bloquant",
                      "quoi": "les soldats ne sont pas retirés des foyers"},
                     {"fichier": "jeu/data/armees.toml", "gravite": "mineur", "quoi": "un seuil sans son niveau"}],
        "promesse_joueur_tenue": False, "tests_changes_justifies": True,
        "tests_rejoues": [{"commande": "pytest test_armees.py", "resultat": "3 passed"}]}}
    pilote, agents, numero_pr = _jusqu_a_la_relecture(projet, gh, depot, tmp_path, corriger, faite())
    pilote.tour()
    revue = gh.prs_[numero_pr]["comments"][-1]["body"]
    for attendu in ("## Relecture — CORRIGER", "La levée crée des hommes qui n'existent pas.",
                    "`jeu/sim/armees.py`:42 — les soldats ne sont pas retirés des foyers",
                    "un seuil sans son niveau", "La promesse au joueur est tenue : non", "3 passed"):
        assert attendu in revue
    pilote.tour()
    correction = agents.appels[-1]
    assert correction["reprise"] and "les soldats ne sont pas retirés des foyers" in correction["consigne"]
    assert "un seuil sans son niveau" in correction["consigne"]
    assert _marques(gh, numero_pr, pr=True)[-1]["etat"] == lots.CORRECTION


def test_le_meneur_conteste_et_le_cto_tranche(projet, gh, depot, tmp_path):
    corriger = {"sortie": {"verdict": "CORRIGER", "resume": "Un nombre est décidé dans la vue.",
                           "constats": [{"fichier": "a.cs", "gravite": "bloquant", "quoi": "calcul dans la vue"}],
                           "promesse_joueur_tenue": True, "tests_changes_justifies": True}}
    conteste = {"sortie": {"etat": "conteste", "compte_rendu": "C'est un affichage.",
                           "conteste": [{"constat": "calcul dans la vue", "pourquoi": "le nombre vient du service"}]}}
    arbitre = {"sortie": {"decision": "meneur", "pourquoi": "le service rend déjà ce nombre"}}
    pilote, agents, numero_pr = _jusqu_a_la_relecture(projet, gh, depot, tmp_path, corriger, conteste, arbitre)
    for _ in range(3):
        pilote.tour()
    assert agents.modeles()[-1] == "fable"
    assert "le nombre vient du service" in agents.appels[-1]["consigne"]
    assert ("fusion_auto", numero_pr) in gh.gestes
    assert _marques(gh, numero_pr, pr=True)[-1]["verdict"] == "ACCEPTE"


def test_le_cto_relit_le_coeur_du_moteur(projet, gh, depot, tmp_path):
    depot.fichiers_ = ["jeu/sim/engine.py", "jeu/sim/tests/test_armees.py"]
    pilote, agents, numero_pr = _jusqu_a_la_relecture(projet, gh, depot, tmp_path, ACCEPTE)
    pilote.tour()
    assert agents.modeles()[-1] == "fable" and "le cœur du moteur" in agents.appels[-1]["consigne"]
    assert _marques(gh, numero_pr, pr=True)[-1]["role"] == "cto"


def test_une_ci_rouge_est_resumee_par_le_lecteur_puis_corrigee_dans_la_session(projet, gh, depot, tmp_path):
    resume = {"sortie": {"resume": "Un test de la levée est rouge.", "echecs": [
        {"travail": "sim (2)", "test": "test_levee", "erreur": "AssertionError: 12 != 10",
         "fichier": "jeu/sim/tests/test_armees.py", "ligne": 31}]}}
    pilote, agents, numero_pr = _jusqu_a_la_relecture(projet, gh, depot, tmp_path, resume, faite())
    gh.ci(numero_pr, "rouge")
    pilote._erreur_ci = lambda numero: "## sim (2)\nAssertionError: 12 != 10"
    pilote.tour()
    lecteur = agents.appels[-1]
    assert lecteur["modele"] == "haiku" and lecteur["argv"][lecteur["argv"].index("--tools") + 1] == ""
    assert "AssertionError: 12 != 10" in lecteur["consigne"]
    assert "`jeu/sim/tests/test_armees.py`:31" in gh.dits(numero_pr, pr=True)
    pilote.tour()
    correction = agents.appels[-1]
    assert correction["modele"] == "opus" and correction["reprise"]
    assert "AssertionError: 12 != 10" in correction["consigne"] and "C'EST UNE CORRECTION" in correction["consigne"]


def test_le_journal_brut_part_si_le_lecteur_se_tait(projet, gh, depot, tmp_path):
    muet = {"code": 1, "brut": "", "erreur": "panne"}
    pilote, agents, numero_pr = _jusqu_a_la_relecture(projet, gh, depot, tmp_path, muet, faite())
    gh.ci(numero_pr, "rouge")
    pilote._erreur_ci = lambda numero: "## sim (2)\nAssertionError: 12 != 10"
    pilote.tour()
    pilote.tour()
    assert "AssertionError: 12 != 10" in agents.appels[-1]["consigne"], "le lot n'attend pas un résumé"


def test_deux_corrections_puis_le_cto_regarde(projet, gh, depot, tmp_path):
    corriger = {"sortie": {"verdict": "CORRIGER", "resume": "Non.", "promesse_joueur_tenue": True,
                           "tests_changes_justifies": True,
                           "constats": [{"fichier": "a.py", "gravite": "bloquant", "quoi": "faux"}]}}
    reporte = {"sortie": {"decision": "reporter", "pourquoi": "la règle est mal posée",
                          "a_revoir_samedi": "la levée est à repenser"}}
    pilote, agents, numero_pr = _jusqu_a_la_relecture(projet, gh, depot, tmp_path, corriger, faite(), corriger,
                                                      faite(), corriger, reporte, faite())
    for _ in range(6):
        pilote.tour()
    assert "relecture « CORRIGER » après 2 correction(s)" in gh.dits(10)
    pilote.tour()
    assert agents.modeles()[-1] == "fable" and "bloque" in gh.etiquettes(10)
    assert "reporte le lot à samedi" in gh.dits(10)
    assert pilote.tour() == ["RIEN"], "un lot reporté n'est pas regardé une seconde fois"
    # Ce que le propriétaire écrit le fait repartir, et suit le lot.
    gh.commentaire_humain(10, "Garde la levée, mais un homme pour vingt foyers.")
    pilote.tour()
    assert "en-cours" in gh.etiquettes(10), "le lot repart dans le même tour, essais remis à zéro"
    assert "un homme pour vingt foyers" in agents.appels[-1]["consigne"]
    assert "la règle est mal posée" in agents.appels[-1]["consigne"], "la décision du CTO suit le lot aussi"


def test_le_cto_redecoupe_un_lot_trop_gros(projet, gh, depot, tmp_path):
    gh.ajouter_issue(10, "La guerre entière", ("lot", "bloque", "monde"), corps=FICHE)
    gh.issues_[10]["comments"].append({"body": lots.marque(role="pilote", etat=lots.BLOQUE, raison="étape trop grosse")})
    fiche = {"piste": "monde", "machine": "vps", "meneur": "chef", "joueur": "Je lève.", "samedi": "Une armée.",
             "regle": "Niveau 2.", "preuves": ["pytest test_armees.py"]}
    decoupe = {"sortie": {"decision": "redecouper", "pourquoi": "deux gestes en un",
                          "fiches": [dict(fiche, titre="Lever"), dict(fiche, titre="Marcher", apres=[1], machine="pc",
                                                                      meneur="developpeur")]}}
    piloter(projet, gh, depot, Agents(decoupe), tmp_path).tour()
    assert gh.issues_[10]["state"] == "CLOSED"
    lever, marcher = gh.issues_[101], gh.issues_[102]
    assert lever["title"] == "Lever" and "Découpé du lot #10 par le CTO" in lever["body"]
    assert "Dépend de : #101" in marcher["body"]
    assert {"lot", "pret", "monde", "pc", "simple"} <= set(gh.etiquettes(102))
    assert marcher["milestone"]["title"] == gh.issues_[10]["milestone"]["title"]


def test_seuls_l_irreversible_l_argent_et_les_droits_arrivent_au_proprietaire(projet, gh, depot, tmp_path):
    gh.ajouter_issue(10, "Un pack de l'Asset Store", ("lot", "bloque", "ville"), corps=FICHE)
    gh.issues_[10]["comments"].append({"body": lots.marque(role="pilote", etat=lots.BLOQUE, raison="il faut une licence")})
    laisse = {"sortie": {"decision": "proprietaire", "pourquoi": "une licence payante"}}
    pilote = piloter(projet, gh, depot, Agents(laisse), tmp_path)
    pilote.tour()
    assert "@moi" in gh.dits(10) and "bloque" in gh.etiquettes(10)
    assert pilote.tour() == ["RIEN"]


def test_master_rouge_ouvre_un_lot_de_reparation_pris_avant_tout_autre(projet, gh, depot, tmp_path, monkeypatch):
    from atelier import traces
    monkeypatch.setattr(traces, "lire_run", lambda depot, run, lignes=80: "FAILED test_faim.py::test_soudure")
    gh.run_master = {"status": "completed", "conclusion": "failure", "databaseId": 77, "url": "https://x/run/77"}
    gh.ajouter_issue(10, "Lever une armée", corps=FICHE)
    fiche = {"sortie": {"titre": "Réparer la soudure", "piste": "monde", "machine": "vps", "meneur": "chef",
                        "joueur": "Tous les lots attendent.", "samedi": "master est vert",
                        "regle": "faim.py ligne 12", "preuves": ["pytest test_faim.py -k soudure"]}}
    agents = Agents(fiche, PLAN)
    pilote = piloter(projet, gh, depot, agents, tmp_path)
    pilote.tour()
    assert agents.modeles() == ["fable"] and "FAILED test_faim.py::test_soudure" in agents.appels[0]["consigne"]
    assert {"lot", "pret", "urgent", "monde"} <= set(gh.etiquettes(101))
    pilote.tour()
    assert "en-cours" in gh.etiquettes(101) and "pret" in gh.etiquettes(10), "la réparation passe d'abord"
    assert len([g for g in gh.gestes if g[0] == "creer_issue"]) == 1, "une seule réparation par run rouge"


def test_un_lot_pc_part_sur_le_pc_et_y_reste(projet, gh, depot, tmp_path):
    gh.ajouter_issue(10, "La caserne", ("lot", "pret", "ville", "pc"), corps=FICHE)
    agents = Agents()
    pilote = piloter(projet, gh, depot, agents, tmp_path)
    pilote.tour()
    assert ("lancer_workflow", "lot-pc.yml", {"issue": "10"}) in gh.gestes
    assert _marques(gh, 10)[-1]["etat"] == lots.ENVOYE and not agents.appels
    assert pilote.tour() == ["#10 attendre_pc — le plan est parti sur le PC"]
    assert len([g for g in gh.gestes if g[0] == "lancer_workflow"]) == 1


def test_un_pc_en_pause_ne_recoit_rien(projet, gh, depot, tmp_path):
    gh.variables_["PC_ACTIF"] = "non"
    gh.ajouter_issue(10, "La caserne", ("lot", "pret", "ville", "pc"), corps=FICHE)
    gh.ajouter_issue(11, "Lever une armée", corps=FICHE)
    agents = Agents(PLAN)
    piloter(projet, gh, depot, agents, tmp_path).tour()
    assert "pret" in gh.etiquettes(10) and "en-cours" in gh.etiquettes(11)
    assert not [g for g in gh.gestes if g[0] == "lancer_workflow"]


def test_une_machine_ne_prend_pas_plus_que_sa_capacite(projet, gh, depot, tmp_path):
    for numero in (10, 11, 12):
        gh.ajouter_issue(numero, f"Lot {numero}", corps=FICHE)
    gh.ajouter_issue(13, "Hors palier", jalon=None, corps=FICHE)
    agents = Agents(PLAN, faite(), PLAN, faite(), faite(), faite())
    pilote = piloter(projet, gh, depot, agents, tmp_path)
    for _ in range(4):
        pilote.tour()
    assert "en-cours" in gh.etiquettes(10) and "pret" in gh.etiquettes(11), "le VPS tient un lot par défaut"
    assert "pret" in gh.etiquettes(13), "un lot hors du palier en cours ne se prend pas"


def test_un_lot_attend_sa_dependance(projet, gh, depot, tmp_path):
    gh.ajouter_issue(10, "L'écran", ("lot", "pret", "interface"), corps=FICHE + "\nDépend de : #11\n")
    gh.ajouter_issue(11, "La règle", corps=FICHE)
    agents = Agents(PLAN)
    piloter(projet, gh, depot, agents, tmp_path).tour()
    assert "pret" in gh.etiquettes(10) and "en-cours" in gh.etiquettes(11)


def test_aucun_test_n_ecrit_dans_le_vrai_journal(projet, gh, depot, tmp_path, sans_le_vrai_dossier_personnel):
    """Le défaut : les tests de l'atelier écrivaient dans le vrai journal du PC."""
    from atelier import agents as agents_mod
    from atelier.__main__ import journal_local
    with pytest.raises(TypeError):
        Pilote(projet, gh, depot)  # le journal n'a pas de chemin par défaut
    assert journal_local() == sans_le_vrai_dossier_personnel / ".atelier" / "journal.jsonl"
    assert agents_mod.dossier_des_traces() == sans_le_vrai_dossier_personnel / ".atelier" / "appels"
    gh.ajouter_issue(10, "Lever une armée", corps=FICHE)
    piloter(projet, gh, depot, Agents(PLAN), tmp_path).tour()
    assert (tmp_path / "journal.jsonl").is_file()
    ecrits = [p for p in sans_le_vrai_dossier_personnel.rglob("*") if p.is_file()]
    assert ecrits and all(p.parent.name == "appels" for p in ecrits), "seule la trace de l'appel, dans le faux dossier"


def test_un_tour_pour_un_seul_lot_ne_touche_a_aucun_autre(projet, gh, depot, tmp_path):
    gh.ajouter_issue(10, "La règle", corps=FICHE + "\nDépend de : #11\n")
    gh.ajouter_issue(11, "L'écran", ("lot", "pret", "interface"), corps=FICHE + "\nDépend de : #10\n")
    gh.ajouter_issue(12, "Un vieux lot", ("lot", "bloque", "monde"), corps=FICHE)
    gh.issues_[12]["comments"].append({"body": lots.marque(role="pilote", etat=lots.BLOQUE, raison="vieux")})
    gh.ajouter_issue(20, "Le lot d'essai", jalon=None, corps=FICHE)
    gh.run_master = {"status": "completed", "conclusion": "failure", "databaseId": 77, "url": "https://x/run/77"}
    agents = Agents(PLAN, faite())
    pilote = piloter(projet, gh, depot, agents, tmp_path, seul=20)
    pilote.tour()
    pilote.tour()
    assert "en-cours" in gh.etiquettes(20) and lots.etapes_faites(_marques(gh, _pr_du_lot(gh, 20), pr=True)) == {1}
    assert agents.modeles() == ["opus", "opus"], "ni le CTO pour le vieux lot, ni la réparation de master"
    touches = {g[1] for g in gh.gestes if g[0] in ("etiqueter", "commenter_issue")}
    assert touches == {20}, "la boucle, le lot bloqué et master rouge restent où ils sont"
