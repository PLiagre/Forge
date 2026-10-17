"""La fenêtre de disponibilité du PC (`pc/disponibilite.py`) : ce qu'elle lit,
sans Windows. La fenêtre elle-même et les appels système ne se jouent pas ici.

Ce que ces tests gardent : un nom de service ou un état que `sc` écrit dans la
langue de Windows se lit pareil, une variable absente laisse travailler le PC,
et le lanceur nomme un fichier qui existe.
"""

from __future__ import annotations

import importlib.util
import sys

import pytest

from conftest import RACINE

SCRIPT = RACINE / "pc" / "disponibilite.py"
spec = importlib.util.spec_from_file_location("disponibilite", SCRIPT)
disponibilite = importlib.util.module_from_spec(spec)
sys.modules["disponibilite"] = disponibilite
spec.loader.exec_module(disponibilite)

TASKLIST = '''"System Idle Process","0","Services","0","8 Ko"
"python.exe","41352","Console","1","119 224 Ko"
"python.exe","35420","Console","1","116 100 Ko"
"Unity.exe","9001","Console","1","2 400 000 Ko"
"UnityShaderCompiler.exe","9002","Console","1","80 000 Ko"
"Runner.Worker.exe","7000","Services","0","90 000 Ko"
"chrome.exe","1234","Console","1","300 000 Ko"
"ligne cassée"
'''


def test_les_processus_lourds_se_comptent_par_famille():
    familles, travail = disponibilite.regrouper(disponibilite.lire_tasklist(TASKLIST))
    assert familles == {"Python": [41352, 35420], "Unity": [9001, 9002]}
    assert travail


def test_sans_runner_worker_aucun_travail_n_est_en_cours():
    _, travail = disponibilite.regrouper(disponibilite.lire_tasklist('"python.exe","1","Console","1","1 Ko"\n'))
    assert not travail


def test_la_charge_est_la_part_du_temps_qui_n_est_pas_inactive():
    # Le temps noyau compte déjà l'inactif : 30 % de 1000 = 700 inactifs sur 1000.
    assert disponibilite.charge((0, 0, 0), (700, 800, 200)) == pytest.approx(30.0)
    assert disponibilite.charge((0, 0, 0), (1000, 1000, 0)) == 0.0
    assert disponibilite.charge((5, 10, 10), (5, 10, 10)) == 0.0   # aucun temps écoulé


def test_seule_une_priorite_normale_ou_plus_haute_se_rabaisse():
    d = disponibilite
    assert [d.a_baisser(c) for c in (d.NORMAL, d.ABOVE_NORMAL, d.HIGH)] == [True, True, True]
    assert [d.a_baisser(c) for c in (d.IDLE, d.BELOW_NORMAL, 0)] == [False, False, False]


@pytest.mark.parametrize("sortie", [
    # Windows en anglais, puis en français : seuls les libellés changent.
    "SERVICE_NAME: actions.runner.PLiagre-Forge.pc-forge\nDISPLAY_NAME: GitHub Actions Runner (PLiagre-Forge.pc-forge)\n"
    "        TYPE               : 10  WIN32_OWN_PROCESS\n        STATE              : 4  RUNNING\n",
    "NOM_SERVICE: actions.runner.PLiagre-Forge.pc-forge\nNOM_AFFICHAGE: GitHub Actions Runner (PLiagre-Forge.pc-forge)\n"
    "        TYPE               : 10  WIN32_OWN_PROCESS\n        ÉTAT               : 4  RUNNING\n",
])
def test_le_service_du_runner_se_lit_dans_n_importe_quelle_langue(sortie):
    assert disponibilite.nom_du_service(sortie) == "actions.runner.PLiagre-Forge.pc-forge"
    assert disponibilite.etat_du_service(sortie) == "RUNNING"


def test_un_service_absent_ou_sans_etat_n_invente_rien():
    assert disponibilite.nom_du_service("SERVICE_NAME: Spooler\n") is None
    assert disponibilite.etat_du_service("rien ici") is None
    assert disponibilite.etat_du_service("STATE : 1  STOPPED") == "STOPPED"


@pytest.mark.parametrize("code, sortie, erreur, attendu", [
    (0, "non\n", "", "non"),
    (0, "NON", "", "non"),
    (0, "oui\n", "", "oui"),
    (0, "", "", "oui"),                                  # une valeur vide ne met pas en pause
    (1, "", "gh: Not Found (HTTP 404)", "oui"),          # variable pas encore créée
    (1, "", "gh: Resource not accessible (HTTP 403)", None),
    (127, "", "gh : introuvable", None),
])
def test_la_variable_absente_laisse_travailler_le_pc_et_l_illisible_ne_dit_rien(code, sortie, erreur, attendu):
    assert disponibilite.valeur_de_la_variable(code, sortie, erreur) == attendu


def test_le_depot_est_celui_d_atelier_toml_et_la_variable_celle_du_pilote():
    from atelier.github import VARIABLE_PC

    assert disponibilite.depot_du_projet(RACINE) == "PLiagre/Forge"
    assert disponibilite.VARIABLE == VARIABLE_PC


def test_un_depot_sans_toml_retombe_sur_le_depot_par_defaut(tmp_path):
    assert disponibilite.depot_du_projet(tmp_path) == disponibilite.DEPOT_PAR_DEFAUT


def test_le_lanceur_nomme_un_fichier_qui_existe_et_les_workflows_lisent_la_meme_variable():
    from atelier.github import VARIABLE_PC

    lanceur = (RACINE / "pc" / "Disponibilite.cmd").read_text(encoding="utf-8")
    assert 'set "PANNEAU=%~dp0disponibilite.py"' in lanceur
    assert (RACINE / "pc" / "disponibilite.py").is_file()
    # Les travaux du PC que le pilote n'envoie pas (cron, poussée) lisent la
    # variable eux-mêmes ; un lancement à la main part toujours.
    for nom in ("build-nuit.yml", "unity.yml"):
        texte = (RACINE / ".github" / "workflows" / nom).read_text(encoding="utf-8")
        assert f"vars.{VARIABLE_PC} != 'non' || github.event_name == 'workflow_dispatch'" in texte, nom
