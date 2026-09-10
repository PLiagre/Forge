"""--run crée un worktree, un verrou, un canal, un état. Il n'invoque personne."""

from pathlib import Path
import subprocess

from atelier import echange, etat, verrou
from atelier.__main__ import main
from tests.test_cycle import _produit


def _git(racine: Path, *args: str) -> None:
    subprocess.run(
        [
            "git",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "init.defaultBranch=master",
            *args,
        ],
        cwd=racine,
        check=True,
        capture_output=True,
    )


def _depot_git(tmp_path: Path) -> Path:
    racine = _produit(tmp_path)
    _git(racine, "init", "-b", "master")
    _git(racine, "config", "user.email", "atelier@test")
    _git(racine, "config", "user.name", "atelier")
    _git(racine, "add", ".")
    _git(racine, "commit", "-m", "graine")
    return racine


def test_run_prepare_sans_invoquer(tmp_path: Path):
    racine = _depot_git(tmp_path)
    code = main(
        [
            "start",
            str(racine / "briefs" / "001-un-changement.md"),
            "--projet",
            str(racine),
            "--run",
        ]
    )
    assert code == 0
    runs = etat.lister(racine)
    assert len(runs) == 1
    run = runs[0]
    assert run.auteur_code != run.relecteur
    assert run.etape is etat.Etape.CREE
    tableau = verrou.charger(racine)
    assert tableau.poses[0].lot == "001-un-changement"
    wt = Path(run.worktree)
    assert wt.is_dir()
    assert echange.git_ignore_le_canal(wt)
    assert (echange.dossier(wt) / "prompt-executant.txt").is_file()
    # Personne n'a été lancé : pas de log d'agent, pas de PR.
    assert not list(wt.glob("**/*.agent-log"))
