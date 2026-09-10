"""Dépôts git temporaires pour les tests. Jamais un clone de production."""

from __future__ import annotations

from pathlib import Path
import subprocess


def _git(racine: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "git",
            "-c", "user.email=atelier@test",
            "-c", "user.name=Atelier",
            "-c", "commit.gpgsign=false",
            "-C", str(racine),
            *args,
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def installer(projet: Path, *, branche: str = "master") -> None:
    _git(projet, "init")
    _git(projet, "checkout", "-B", branche)
    _git(projet, "add", "-A")
    _git(projet, "commit", "-m", "base", "--allow-empty")


def worktree_role(projet: Path, dest: Path, *, branche: str = "atelier/coder") -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    _git(projet, "worktree", "add", "-b", branche, str(dest), "master")
    return dest


def committer(racine: Path, chemin: Path, message: str) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if not chemin.exists():
        chemin.write_text("travail\n", encoding="utf-8")
    _git(racine, "add", "--", str(chemin.relative_to(racine)))
    _git(racine, "commit", "-m", message)


def orpheline(projet: Path, branche: str) -> None:
    _git(projet, "checkout", "--orphan", branche)
    _git(projet, "commit", "--allow-empty", "-m", "orpheline")
    _git(projet, "checkout", "master")


def courante(racine: Path) -> str:
    return _git(racine, "branch", "--show-current").stdout.strip()
