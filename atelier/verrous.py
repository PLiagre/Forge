"""Les verrous que partagent les tours du pilote qui tournent en même temps.

Le cron lance un tour toutes les deux minutes, qu'un autre tourne encore ou
non : plusieurs lots avancent donc en même temps, chacun dans son worktree,
et chaque tour n'invoque toujours qu'un agent. Ce qui ne doit se faire
qu'une fois se tient par un verrou de fichier (flock), que le système rend
seul quand le processus meurt :

- `lot-<n>` : un lot n'avance que dans un tour à la fois ;
- `decider` : relire GitHub, ranger, reprendre, livrer et choisir le lot
  suivant se font un tour après l'autre, en quelques secondes ;
- `git` : un geste git à la fois sur le dépôt partagé (fetch, worktrees,
  poussées) ;
- `captures` : une publication à la fois sur la branche `journal` ;
- `meca` : un mécanicien de master à la fois ;
- `outil-<outil>-<i>` : les places d'un outil, jusqu'à son plafond
  d'agents simultanés ;
- `tour-<i>` : les places des tours eux-mêmes. Si GitHub ne répond plus,
  les tours ne s'empilent pas toutes les deux minutes.

Les fichiers vivent dans `ATELIER_VERROUS` (`~/.atelier/verrous`), à côté
de ceux des crons : `atelier-boucle etat` les montre en vol.
"""

from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import time
from typing import IO, Iterator


class VerrouOccupe(RuntimeError):
    """Un verrou attendu trop longtemps : un tour bloqué le tient."""


def dossier_par_defaut() -> Path:
    return Path(os.environ.get("ATELIER_VERROUS") or Path.home() / ".atelier" / "verrous")


class AucunVerrou:
    """Un seul tour à la fois : les tests, le tour à sec, le côté PC."""

    def prendre(self, nom: str) -> bool:
        return True

    def lacher(self, nom: str) -> None:
        pass

    def pris_ailleurs(self, nom: str) -> bool:
        return False

    @contextmanager
    def tenir(self, nom: str, attente: float = 600) -> Iterator[None]:
        yield

    @contextmanager
    def place(self, nom: str, plafond: int | None) -> Iterator[bool]:
        yield True


class Verrous(AucunVerrou):
    """Des verrous flock dans un dossier. Un tour tient un verrou par le
    fichier qu'il a ouvert ; un autre processus, ou une autre instance, ne
    peut pas le prendre tant qu'il n'est pas lâché."""

    ATTENTE_ENTRE_ESSAIS = 0.2

    def __init__(self, dossier: Path | str | None = None):
        self.dossier = Path(dossier) if dossier is not None else dossier_par_defaut()
        self._tenus: dict[str, IO] = {}

    def _fichier(self, nom: str) -> Path:
        return self.dossier / f"atelier-{nom}.lock"

    def prendre(self, nom: str) -> bool:
        """Sans attendre : vrai si ce tour tient `nom` (déjà, ou désormais)."""
        import fcntl  # POSIX : le pilote ne tourne que sur le VPS

        if nom in self._tenus:
            return True
        self.dossier.mkdir(parents=True, exist_ok=True)
        f = open(self._fichier(nom), "a+")
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            f.close()
            return False
        self._tenus[nom] = f
        return True

    def lacher(self, nom: str) -> None:
        import fcntl

        f = self._tenus.pop(nom, None)
        if f is not None:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()

    def pris_ailleurs(self, nom: str) -> bool:
        """Un autre tour tient `nom` en ce moment."""
        if nom in self._tenus:
            return False
        if self.prendre(nom):
            self.lacher(nom)
            return False
        return True

    @contextmanager
    def tenir(self, nom: str, attente: float = 600) -> Iterator[None]:
        """Attend son tour, `attente` secondes au plus, et lâche à la sortie.
        Déjà tenu par ce tour : rien de plus, et rien n'est lâché."""
        if nom in self._tenus:
            yield
            return
        debut = time.monotonic()
        while not self.prendre(nom):
            if time.monotonic() - debut > attente:
                raise VerrouOccupe(f"verrou « {nom} » tenu depuis plus de {attente:.0f} s par un autre tour")
            time.sleep(self.ATTENTE_ENTRE_ESSAIS)
        try:
            yield
        finally:
            self.lacher(nom)

    @contextmanager
    def place(self, nom: str, plafond: int | None) -> Iterator[bool]:
        """Une des `plafond` places `nom-1` … `nom-<plafond>`, tenue le temps
        du bloc ; faux si toutes sont prises. Sans plafond, toujours vrai."""
        if not plafond:
            yield True
            return
        for i in range(1, plafond + 1):
            une = f"{nom}-{i}"
            if une not in self._tenus and self.prendre(une):
                try:
                    yield True
                finally:
                    self.lacher(une)
                return
        yield False
