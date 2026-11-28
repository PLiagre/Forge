"""Les gestes du dépôt joués sur un vrai git, dans un dossier jetable."""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from atelier.depot import Depot

IDENTITE = ["-c", "user.name=essai", "-c", "user.email=essai@exemple.invalid", "-c", "commit.gpgsign=false"]


def git(chemin: Path, *args: str, ok: bool = True) -> subprocess.CompletedProcess:
    fini = subprocess.run(["git", *IDENTITE, *args], cwd=chemin, capture_output=True, text=True)
    if ok:
        assert fini.returncode == 0, fini.stderr
    return fini


def ecrire(chemin: Path, nom: str, texte: str) -> None:
    cible = chemin / nom
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.write_text(texte, encoding="utf-8")


@pytest.fixture
def depot(tmp_path):
    racine = tmp_path / "depot"
    racine.mkdir()
    git(racine, "init", "--quiet", "-b", "master")
    ecrire(racine, "atelier/pilote.py", "avant\n")
    ecrire(racine, "jeu/monde.txt", "base\n")
    git(racine, "add", "-A")
    git(racine, "commit", "--quiet", "-m", "départ")
    return racine


def test_hors_fusion_un_fichier_interdit_revient_a_la_tete_et_un_neuf_disparait(depot):
    ecrire(depot, "atelier/pilote.py", "touché par l'agent\n")
    ecrire(depot, "atelier/neuf.py", "écrit par l'agent\n")
    Depot(depot, "master").annuler(depot, ["atelier/pilote.py", "atelier/neuf.py"])
    assert (depot / "atelier/pilote.py").read_text(encoding="utf-8") == "avant\n"
    assert not (depot / "atelier/neuf.py").exists()
    assert git(depot, "status", "--porcelain").stdout == ""


def test_pendant_une_fusion_un_fichier_interdit_garde_la_version_de_la_base(depot):
    """La base change `atelier/` et en crée un fichier, le lot change le même
    fichier du jeu qu'elle : la fusion s'arrête sur un conflit. Annuler ce que
    l'agent a fait dans `atelier/` doit garder la version de la base, jamais
    celle d'avant la fusion, et ne pas échouer sur le fichier neuf."""
    git(depot, "checkout", "--quiet", "-b", "lot/1")
    ecrire(depot, "jeu/monde.txt", "du lot\n")
    git(depot, "commit", "--quiet", "-am", "le lot")
    git(depot, "checkout", "--quiet", "master")
    ecrire(depot, "jeu/monde.txt", "de la base\n")
    ecrire(depot, "atelier/pilote.py", "après\n")
    ecrire(depot, "atelier/traces.py", "neuf sur la base\n")
    git(depot, "add", "-A")
    git(depot, "commit", "--quiet", "-m", "la base avance")
    git(depot, "checkout", "--quiet", "lot/1")
    assert git(depot, "merge", "--no-edit", "master", ok=False).returncode != 0, "la fusion doit s'arrêter"
    ecrire(depot, "atelier/pilote.py", "touché par l'agent\n")
    ecrire(depot, "atelier/traces.py", "touché par l'agent\n")
    ecrire(depot, "atelier/autre.py", "écrit par l'agent\n")

    Depot(depot, "master").annuler(depot, ["atelier/pilote.py", "atelier/traces.py", "atelier/autre.py"])

    assert (depot / "atelier/pilote.py").read_text(encoding="utf-8") == "après\n"
    assert (depot / "atelier/traces.py").read_text(encoding="utf-8") == "neuf sur la base\n"
    assert not (depot / "atelier/autre.py").exists()
    ecrire(depot, "jeu/monde.txt", "résolu\n")
    git(depot, "add", "-A")
    git(depot, "commit", "--quiet", "--no-edit")
    assert git(depot, "diff", "--name-only", "master", "HEAD").stdout.split() == ["jeu/monde.txt"], \
        "le lot ne doit différer de la base que par ce qu'il a fait"
