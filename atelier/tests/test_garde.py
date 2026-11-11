"""La chaîne se répare sous garde.

Ce fichier est lui-même hors de portée d'une réparation (`[projet].sensibles`) :
seul le mode direct y écrit. Il prouve la garde (`atelier/garde.py`) et que le
pilote l'applique : une réparation qui retirerait l'appel de la garde ferait
rougir ces tests, et ne pourrait pas les changer pour passer.
"""
from __future__ import annotations

from pathlib import Path

from atelier import garde
from atelier.lots import chaine_en_cause, marque, marques
from atelier.projet import charger

from conftest import Agents
from test_pilote import REVUE_CORRIGER, _bloque, _etiquettes, _gestes, _pilote, _prompt

RACINE = Path(__file__).resolve().parents[2]
REPARABLES = ("atelier/", ".github/workflows/tests.yml", ".github/workflows/security.yml", "docs/WORKFLOW.md")
SENSIBLES = ("atelier/garde.py", "atelier/tests/test_garde.py", "atelier/crons/")
MODE_DIRECT = "Le pilote ne rejoue pas ce contrôle.\nDECISION: MODE-DIRECT :: `atelier/pilote.py` doit rejouer ce contrôle"


def _reparable(projet):
    """Le même projet, dont la chaîne se répare, relue par une direction."""
    chemin = projet.racine / "atelier.toml"
    texte = chemin.read_text(encoding="utf-8")
    texte = texte.replace('prefixe_branche = "lot/"', 'prefixe_branche = "lot/"\n'
                          'reparables = ["atelier/", ".github/workflows/tests.yml"]\n'
                          'sensibles = ["atelier/garde.py", "atelier/tests/test_garde.py"]')
    texte = texte.replace("boussole    =", 'direction   = "claude/haiku"\nboussole    =')
    chemin.write_text(texte, encoding="utf-8")
    return charger(projet.racine)


def _la_chaine_est_en_cause(projet, gh, depot, tmp_path):
    """Un lot bloqué, dont le dépanneur dit que la chaîne est en cause."""
    _bloque(gh)
    _pilote(projet, gh, depot, Agents((0, MODE_DIRECT)), tmp_path).tour()
    assert marques(gh.issues_[10]["comments"])[-1]["raison"].startswith("la chaîne est en cause")


def _vert(gh, numero):
    for c in gh.prs_[numero]["statusCheckRollup"]:
        c.update(status="COMPLETED", conclusion="SUCCESS")


# ------------------------------------------------------------- la garde
def test_une_reparation_ne_touche_que_la_chaine_et_jamais_ce_qui_la_garde():
    for chemin in ("atelier/pilote.py", "atelier/tests/test_pilote.py", ".github/workflows/security.yml",
                   "docs/WORKFLOW.md", "atelier\\lots.py"):
        assert garde.reparable(chemin, REPARABLES, SENSIBLES), chemin
    for chemin in ("atelier/garde.py", "atelier/tests/test_garde.py", "atelier/crons/tour.sh", "atelier.toml",
                   "AGENTS.md", "CLAUDE.md", "CAP.md", "docs/VISION.md", "jeu/sim/engine.py",
                   ".github/workflows/lot-pc.yml", ".github/workflows/unity.yml", ".github/workflows/neuf.yml"):
        assert not garde.reparable(chemin, REPARABLES, SENSIBLES), chemin
    assert not garde.reparable("atelier/pilote.py", (), ()), "sans `reparables`, rien ne se répare"


def test_dans_un_workflow_ni_droits_ni_secrets_ni_machine_ni_declencheurs():
    workflow = ".github/workflows/security.yml"
    ouvert = ['curl -sSfL --retry 5 --retry-all-errors "https://github.com/x" -o x.tar.gz', "set -euo pipefail",
              'GITLEAKS_VERSION: "8.30.1"', "timeout-minutes: 30", "- name: Install gitleaks"]
    assert garde.lignes_sensibles(workflow, ouvert) == []
    for ligne in ("permissions:", "  contents: write   # permissions: élargies", "runs-on: [self-hosted, Windows]",
                  "    runs-on: ubuntu-latest", "- uses: actions/checkout@v4", "  uses: tiers/action@main",
                  "token: ${{ secrets.JETON }}", "GITHUB_TOKEN: x", "on:", "  pull_request_target:",
                  "  workflow_dispatch:", "  push:", "    branches: [master]"):
        assert garde.lignes_sensibles(workflow, [ligne]), ligne
    assert garde.lignes_sensibles("atelier/pilote.py", ["permissions: write-all"]) == [], "hors de .github/, aucune"
    # Une ligne retirée compte autant qu'une ligne ajoutée : retirer `permissions` élargit les droits.
    assert "droits" in garde.hors_reparation(workflow, ["permissions:", "  contents: read"], REPARABLES, SENSIBLES)
    assert garde.hors_reparation(workflow, ouvert, REPARABLES, SENSIBLES) == ""
    assert garde.hors_reparation("AGENTS.md", [], REPARABLES, SENSIBLES) == "hors de portée d'une réparation"


def test_le_depot_garde_sa_garde_et_ses_regles_hors_de_portee():
    """Sur le vrai `atelier.toml` : la garde, ses tests, le cron, les règles et
    les workflows du PC ne se réparent qu'en mode direct."""
    projet = charger(RACINE)
    assert projet.reparables and "atelier/" in projet.reparables
    for chemin in ("atelier/garde.py", "atelier/tests/test_garde.py", "atelier/crons/repartiteur.sh", "atelier.toml",
                   "AGENTS.md", "CAP.md", ".github/workflows/lot-pc.yml", ".github/workflows/build-nuit.yml"):
        assert not garde.reparable(chemin, projet.reparables, projet.sensibles), chemin
    assert garde.reparable("atelier/pilote.py", projet.reparables, projet.sensibles)


# ----------------------------------------------------- le pilote l'applique
def test_la_chaine_se_repare_relue_par_la_direction_et_le_lot_repart(projet, gh, depot, tmp_path):
    """Jusqu'au 10 novembre 2026, un lot que la chaîne bloquait attendait le
    propriétaire : 21 fois en six semaines, et deux jours pour un `--retry`
    que le dépanneur avait écrit sans pouvoir le poser."""
    projet = _reparable(projet)
    _la_chaine_est_en_cause(projet, gh, depot, tmp_path)
    mecanicien = Agents((0, "Le pilote rejoue le contrôle. 3 tests ajoutés, suite verte.", {
        "atelier/pilote.py": "la réparation", "atelier/tests/test_rejeu.py": "son test",
        "atelier/garde.py": "plus de garde", "atelier/tests/test_garde.py": "plus de preuve",
        "AGENTS.md": "d'autres règles", "atelier.toml": "d'autres droits", "jeu/sim/engine.py": "hors sujet",
        ".github/workflows/tests.yml": "permissions: write-all\n"}))
    _pilote(projet, gh, depot, mecanicien, tmp_path).tour()
    prompt = _prompt(mecanicien.appels[0])
    assert mecanicien.outils() == ["fable"] and "c'est la chaîne elle-même" in prompt
    assert "doit rejouer ce contrôle" in prompt and "`atelier/garde.py`" in prompt
    retires = next(g[1] for g in depot.gestes if g[0] == "annuler")
    assert set(retires) == {"atelier/garde.py", "atelier/tests/test_garde.py", "AGENTS.md", "atelier.toml",
                            "jeu/sim/engine.py", ".github/workflows/tests.yml"}
    branche, titre = _gestes(gh, "creer_pr")[-1][1:]
    assert branche.startswith("meca/chaine-10-") and "lot #10" in titre
    numero_pr = max(gh.prs_)
    assert "hors de portée d'une réparation" in gh.prs_[numero_pr]["body"] and "`AGENTS.md`" in gh.prs_[numero_pr]["body"]
    m = marques(gh.issues_[10]["comments"])[-1]
    assert (m["etat"], m["pr"]) == ("reparation", numero_pr) and "bloque" in _etiquettes(gh, 10)
    # La CI verte, la direction relit, contre la garde et non contre un brief.
    _vert(gh, numero_pr)
    direction = Agents((0, "La cause est corrigée, aucune garde n'est touchée.\nVERDICT: ACCEPTE"))
    _pilote(projet, gh, depot, direction, tmp_path).tour()
    relecture = _prompt(direction.appels[0])
    assert direction.outils() == ["haiku"], "le rôle `direction` du dépôt, pas le relecteur des lots"
    assert "réparation de la chaîne elle-même" in relecture and "ne retire ni n'affaiblit aucune garde" in relecture
    assert "docs/briefs/" not in relecture and ("fusion_auto", numero_pr) in gh.gestes
    # Fusionnée : le lot repart.
    gh.prs_[numero_pr]["state"] = "MERGED"
    _pilote(projet, gh, depot, Agents(), tmp_path).tour()
    assert "pret" in _etiquettes(gh, 10) and "bloque" not in _etiquettes(gh, 10)
    assert "la chaîne est réparée" in gh.issues_[10]["comments"][-1]["body"]


def test_une_correction_de_la_reparation_passe_aussi_par_la_garde(projet, gh, depot, tmp_path):
    projet = _reparable(projet)
    fait = marque(role="mecanicien_master", etat="fait", essai=1, agent="claude/fable", sha="a" * 40)
    pr = gh.ajouter_pr(629, "meca/chaine-10-20261110-2100", ci="vert", commentaires=[fait, REVUE_CORRIGER])
    pr["body"] = "Le lot #10 est bloqué, et le dépanneur dit que la chaîne est en cause."
    mecanicien = Agents((0, "Corrigé.", {"atelier/pilote.py": "mieux", "atelier/garde.py": "plus de garde"}))
    _pilote(projet, gh, depot, mecanicien, tmp_path).tour()
    assert "c'est la chaîne elle-même" in _prompt(mecanicien.appels[0]) and "SC6" in _prompt(mecanicien.appels[0])
    assert ("annuler", ("atelier/garde.py",)) in depot.gestes and ("pousser", "meca/chaine-10-20261110-2100") in depot.gestes


def test_sans_reparables_la_chaine_attend_le_mode_direct(projet, gh, depot, tmp_path):
    """Contre-épreuve : le dépôt d'essai ne nomme rien de réparable."""
    _la_chaine_est_en_cause(projet, gh, depot, tmp_path)
    rien = Agents()
    _pilote(projet, gh, depot, rien, tmp_path).tour()
    assert rien.appels == [] and not _gestes(gh, "creer_pr") and "bloque" in _etiquettes(gh, 10)


def test_une_reparation_hors_de_portee_ou_refusee_laisse_le_lot_au_mode_direct(projet, gh, depot, tmp_path):
    """Contre-épreuve : le mécanicien qui ne change que ce qui est gardé, ou
    qui demande le mode direct, n'ouvre aucune PR, et n'est pas rappelé."""
    projet = _reparable(projet)
    for reponse, pourquoi in (((0, "Fait.", {"atelier/garde.py": "plus de garde", "CAP.md": "un autre cap"}),
                               "hors de portée"),
                              ((0, "Il faut git-lfs.\nDECISION: MODE-DIRECT :: installer git-lfs sur le VPS",
                                {"atelier/pilote.py": "à moitié"}), "installer git-lfs"),
                              ((1, "erreur interne"), "code 1")):
        gh.issues_.clear(), gh.prs_.clear(), gh.gestes.clear()
        _la_chaine_est_en_cause(projet, gh, depot, tmp_path)
        _pilote(projet, gh, depot, Agents(reponse), tmp_path).tour()
        assert not _gestes(gh, "creer_pr") and "bloque" in _etiquettes(gh, 10)
        m = marques(gh.issues_[10]["comments"])[-1]
        assert (m["etat"], m["fin"]) == ("reparation", "echec") and pourquoi in m["raison"]
        assert depot.changements(depot.racine / "chantiers" / "meca") == [], "rien ne reste dans le chantier"
        rien = Agents()
        _pilote(projet, gh, depot, rien, tmp_path).tour()
        assert rien.appels == []


def test_une_reparation_abandonnee_ou_une_reponse_du_proprietaire_rendent_la_main(projet, gh, depot, tmp_path):
    projet = _reparable(projet)
    _la_chaine_est_en_cause(projet, gh, depot, tmp_path)
    _pilote(projet, gh, depot, Agents((0, "Réparé.", {"atelier/pilote.py": "la réparation"})), tmp_path).tour()
    numero_pr = max(gh.prs_)
    gh.prs_[numero_pr]["state"] = "CLOSED"
    rien = Agents()
    _pilote(projet, gh, depot, rien, tmp_path).tour()
    m = marques(gh.issues_[10]["comments"])[-1]
    assert (m["etat"], m["fin"]) == ("reparation", "abandonnee") and "bloque" in _etiquettes(gh, 10)
    _pilote(projet, gh, depot, rien, tmp_path).tour()
    assert rien.appels == [], "une réparation abandonnée ne se retente pas"
    # Le propriétaire a répondu : c'est lui qui a la main.
    bloque = {"body": marque(role="pilote", etat="bloque", par="depanneur", raison="la chaîne est en cause, mode direct : x")}
    assert chaine_en_cause([bloque]) == ("la chaîne est en cause, mode direct : x", None)
    assert chaine_en_cause([bloque, {"body": "corrigé en mode direct", "author": {"login": "PLiagre"}}]) is None
    assert chaine_en_cause([{"body": marque(role="pilote", etat="bloque", raison="CI rouge")}]) is None
