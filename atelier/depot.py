"""Les gestes git du pilote, dans le dossier de travail d'un lot.

Un lot travaille dans un worktree du dépôt, sous `.atelier/chantiers/<issue>`
(ignoré par git) : la copie principale reste sur la base, et c'est d'elle
que tourne le pilote. Seul le pilote commit et pousse ; l'agent n'a édité
que des fichiers.

Plusieurs tours du pilote tournent en même temps, chacun sur son lot : les
worktrees partagent les références et les objets du dépôt. Chaque geste git
passe donc sous le verrou « git » (`verrous.py`), un à la fois ; un geste
dure quelques secondes, l'agent travaille entre deux.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
from typing import Callable

from .verrous import AucunVerrou

Executeur = Callable[[list[str], Path], tuple[int, str, str]]


class DepotErreur(RuntimeError):
    pass


def executer(argv: list[str], cwd: Path) -> tuple[int, str, str]:
    fini = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=600)
    return fini.returncode, fini.stdout, fini.stderr


class Depot:
    # Un geste git qui attend plus que ceci qu'un autre finisse le sien : un
    # tour est bloqué, et on le dit au lieu d'attendre sans fin.
    ATTENTE_GIT = 900

    def __init__(self, racine: Path, base: str, *, executeur: Executeur = executer,
                 nom: str | None = None, email: str | None = None, verrous=None):
        self.racine = Path(racine).resolve()
        self.base = base
        self._executer = executeur
        self.verrous = verrous or AucunVerrou()
        self.nom = nom or os.environ.get("ATELIER_GIT_NOM", "atelier")
        self.email = email or os.environ.get("ATELIER_GIT_EMAIL", "")

    # --------------------------------------------------------------- bas
    def git_code(self, *args: str, cwd: Path | None = None) -> tuple[int, str, str]:
        with self.verrous.tenir("git", attente=self.ATTENTE_GIT):
            return self._executer(["git", *args], Path(cwd or self.racine))

    def git(self, *args: str, cwd: Path | None = None) -> str:
        code, out, err = self.git_code(*args, cwd=cwd)
        if code != 0:
            raise DepotErreur(f"git {' '.join(args[:3])} : {(err or out).strip()[:400]}")
        return out

    # ---------------------------------------------------------- chantiers
    def chantier(self, nom: str | int) -> Path:
        return self.racine / ".atelier" / "chantiers" / str(nom)

    def fetch(self) -> None:
        self.git("fetch", "--quiet", "--prune", "origin")

    def branche_distante(self, branche: str) -> bool:
        code, _, _ = self.git_code("rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{branche}")
        return code == 0

    def preparer(self, nom: str | int, branche: str) -> Path:
        """Le worktree du lot, sur sa branche, à jour de l'origine.

        La branche part de la base si elle n'existe pas encore sur l'origine.
        Ce qui traînait dans le worktree d'un tour précédent est effacé : il
        n'y a rien à garder que l'origine n'ait pas déjà.
        """
        depart = f"origin/{branche}" if self.branche_distante(branche) else f"origin/{self.base}"
        chemin = self.chantier(nom)
        self.git("worktree", "prune")
        if not (chemin / ".git").exists():
            chemin.parent.mkdir(parents=True, exist_ok=True)
            self.git("worktree", "add", "--force", "-B", branche, str(chemin), depart)
        else:
            self.git("checkout", "--force", "-B", branche, depart, cwd=chemin)
            self.git("reset", "--hard", depart, cwd=chemin)
            self.git("clean", "-fd", cwd=chemin)
        return chemin

    def retirer(self, nom: str | int) -> None:
        chemin = self.chantier(nom)
        if (chemin / ".git").exists():
            self.git_code("worktree", "remove", "--force", str(chemin))
        if chemin.exists():
            shutil.rmtree(chemin, ignore_errors=True)
        self.git_code("worktree", "prune")

    # ------------------------------------------------------- changements
    def changements(self, chemin: Path) -> list[str]:
        sortie = self.git("status", "--porcelain", "-z", "--untracked-files=all", cwd=chemin)
        fichiers = []
        morceaux = sortie.split("\0")
        i = 0
        while i < len(morceaux):
            entree = morceaux[i]
            i += 1
            if len(entree) < 4:
                continue
            code, nom = entree[:2], entree[3:]
            if code[0] in "RC":  # renommage : le nom d'origine suit
                i += 1
            fichiers.append(nom)
        return fichiers

    def annuler(self, chemin: Path, fichiers: list[str]) -> None:
        """Remet ces fichiers comme la tête les porte ; efface les nouveaux."""
        suivis = set(self.git("ls-files", "-z", cwd=chemin).split("\0"))
        for f in fichiers:
            if f in suivis:
                self.git("checkout", "HEAD", "--", f, cwd=chemin)
            else:
                cible = Path(chemin) / f
                if cible.is_file():
                    cible.unlink()

    def enregistrer(self, chemin: Path, message: str) -> str:
        self.git("add", "-A", cwd=chemin)
        identite = ["-c", f"user.name={self.nom}"] + (["-c", f"user.email={self.email}"] if self.email else [])
        self.git(*identite, "commit", "--quiet", "-m", message, cwd=chemin)
        return self.git("rev-parse", "HEAD", cwd=chemin).strip()

    def pousser(self, chemin: Path, branche: str) -> None:
        self.git("push", "--quiet", "-u", "origin", f"HEAD:refs/heads/{branche}", cwd=chemin)

    def tete(self, chemin: Path) -> str:
        return self.git("rev-parse", "HEAD", cwd=chemin).strip()

    # ------------------------------------------------------------ fusion
    def fusionner_base(self, chemin: Path) -> list[str]:
        """Fusionne l'origine de la base. Rend les fichiers en conflit (vide :
        fusion propre, déjà enregistrée)."""
        identite = ["-c", f"user.name={self.nom}"] + (["-c", f"user.email={self.email}"] if self.email else [])
        code, _, _ = self.git_code(*identite, "merge", "--no-edit", f"origin/{self.base}", cwd=chemin)
        if code == 0:
            return []
        conflits = self.git("diff", "--name-only", "--diff-filter=U", cwd=chemin).split()
        if not conflits:
            raise DepotErreur(f"la fusion de origin/{self.base} a échoué sans conflit lisible")
        return conflits

    def marqueurs_restants(self, chemin: Path, fichiers: list[str]) -> list[str]:
        restants = []
        for f in fichiers:
            cible = Path(chemin) / f
            if cible.is_file():
                texte = cible.read_text(encoding="utf-8", errors="replace")
                if any(l.startswith(("<<<<<<< ", ">>>>>>> ")) or l == "=======" for l in texte.splitlines()):
                    restants.append(f)
        return restants

    def conclure_fusion(self, chemin: Path) -> str:
        self.git("add", "-A", cwd=chemin)
        identite = ["-c", f"user.name={self.nom}"] + (["-c", f"user.email={self.email}"] if self.email else [])
        self.git(*identite, "commit", "--quiet", "--no-edit", cwd=chemin)
        return self.tete(chemin)

    # ------------------------------------------------------------ lecture
    def en_retard(self, chemin: Path) -> bool:
        """La base a-t-elle des commits que la branche n'a pas ?"""
        sortie = self.git("rev-list", "--count", f"HEAD..origin/{self.base}", cwd=chemin).strip()
        return int(sortie or 0) > 0

    def diff_base(self, chemin: Path) -> str:
        return self.git("diff", f"origin/{self.base}...HEAD", cwd=chemin)

    def fichiers_du_lot(self, chemin: Path) -> list[str]:
        return self.git("diff", "--name-only", f"origin/{self.base}...HEAD", cwd=chemin).split()
