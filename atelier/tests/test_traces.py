"""Lecture des journaux de CI : la synthèse multi-travaux et les extraits."""

from __future__ import annotations

import json
import subprocess

from atelier import consignes, traces


def _resultat(stdout: str = "", code: int = 0, stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["gh"], code, stdout, stderr)


def test_lire_run_met_en_tete_la_synthese_des_echecs_de_tous_les_travaux(monkeypatch):
    jobs = {
        "jobs": [
            {"name": "sim (1)", "conclusion": "failure", "databaseId": 101},
            {"name": "vues", "conclusion": "success", "databaseId": 102},
            {"name": "sim (2)", "conclusion": "failure", "databaseId": 103},
            {"name": "forge", "conclusion": "failure", "databaseId": 104},
        ]
    }
    journaux = {
        "repos/moi/essai/actions/jobs/101/logs": _resultat(
            "2026-11-26T03:00:01.000Z collected 100 items\n"
            "2026-11-26T03:01:00.000Z FAILED sim/tests/test_a.py::test_un - AssertionError: 1 != 2\n"
            "2026-11-26T03:01:05.000Z === short test summary info ===\n"
            "2026-11-26T03:01:05.001Z FAILED sim/tests/test_a.py::test_un - AssertionError: 1 != 2\n"
            "2026-11-26T03:01:06.000Z ##[error]Process completed with exit code 1.\n"
        ),
        "repos/moi/essai/actions/jobs/103/logs": _resultat(
            "2026-11-26T03:02:00.000Z ERROR sim/tests/test_b.py::test_deux - RuntimeError: boom\n"
            "2026-11-26T03:02:01.000Z FAILED sim/tests/test_c.py::test_trois - assert False\n"
            "2026-11-26T03:02:02.000Z ##[error]Process completed with exit code 1.\n"
        ),
        "repos/moi/essai/actions/jobs/104/logs": _resultat("", code=1, stderr="404"),
    }

    def faux_gh(*args: str):
        if args[:2] == ("run", "view"):
            return _resultat(json.dumps(jobs))
        if args[0] == "api":
            return journaux[args[1]]
        raise AssertionError(f"appel gh inattendu : {args}")

    monkeypatch.setattr(traces, "_gh", faux_gh)
    sortie = traces.lire_run("moi/essai", 42, lignes=10)

    assert sortie.startswith("== Synthèse des échecs (tous travaux)\n")
    synthese, reste = sortie.split("\n\n== sim (1)\n", 1)
    assert synthese.count("FAILED sim/tests/test_a.py::test_un - AssertionError: 1 != 2") == 1
    assert "- [sim (1)] FAILED sim/tests/test_a.py::test_un - AssertionError: 1 != 2" in synthese
    assert "- [sim (2)] ERROR sim/tests/test_b.py::test_deux - RuntimeError: boom" in synthese
    assert "- [sim (2)] FAILED sim/tests/test_c.py::test_trois - assert False" in synthese
    assert "vues" not in sortie
    assert "== sim (2)\n" in reste and "== forge\njournal illisible" in reste


def test_lire_run_sans_ligne_failed_ou_error_n_ajoute_pas_de_synthese_vide(monkeypatch):
    jobs = {"jobs": [{"name": "atelier", "conclusion": "failure", "databaseId": 201}]}

    def faux_gh(*args: str):
        if args[:2] == ("run", "view"):
            return _resultat(json.dumps(jobs))
        return _resultat("2026-11-26T03:00:01Z shellcheck: SC2086\n##[error]exit 1\n")

    monkeypatch.setattr(traces, "_gh", faux_gh)
    sortie = traces.lire_run("moi/essai", 43, lignes=10)
    assert "Synthèse des échecs" not in sortie
    assert sortie.startswith("== atelier\n") and "shellcheck: SC2086" in sortie


def test_couper_milieu_garde_le_debut_et_la_fin_sans_depasser_la_limite():
    court = "début et fin"
    assert consignes._couper_milieu(court, 100) == court
    long = "DEBUT:" + ("a" * 500) + "MILIEU" + ("b" * 500) + ":FIN"
    coupe = consignes._couper_milieu(long, 200)
    assert len(coupe) <= 200
    assert coupe.startswith("DEBUT:") and coupe.endswith(":FIN")
    assert "MILIEU" not in coupe and "milieu tronqué" in coupe
