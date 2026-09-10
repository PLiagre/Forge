"""État durable d'un run. Une étape s'écrit avant l'effet suivant."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path
from uuid import uuid4


class Etape(str, Enum):
    CREE = "CREE"
    BRIEF_A_RELIRE = "BRIEF_A_RELIRE"
    A_EXECUTER = "A_EXECUTER"
    DIFF_A_RELIRE = "DIFF_A_RELIRE"
    PRET_AU_PROPRIETAIRE = "PRET_AU_PROPRIETAIRE"
    BLOQUE = "BLOQUE"


class FusionInterdite(RuntimeError):
    pass


@dataclass
class Run:
    id: str
    lot: str
    brief: str
    etape: Etape
    branche: str
    worktree: str
    auteur_code: str
    relecteur: str
    cree_at: str
    fichiers: list[str] = field(default_factory=list)

    def vers_dict(self) -> dict:
        payload = asdict(self)
        payload["etape"] = self.etape.value
        return payload


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def nouveau(
    *,
    lot: str,
    brief: Path,
    branche: str,
    worktree: Path,
    auteur_code: str,
    relecteur: str,
    fichiers: list[str],
) -> Run:
    if auteur_code == relecteur:
        raise ValueError("l'auteur du code ne peut pas être le relecteur")
    return Run(
        id=uuid4().hex[:12],
        lot=lot,
        brief=brief.as_posix(),
        etape=Etape.CREE,
        branche=branche,
        worktree=worktree.as_posix(),
        auteur_code=auteur_code,
        relecteur=relecteur,
        cree_at=_now(),
        fichiers=list(fichiers),
    )


def dossier_runs(racine: Path) -> Path:
    return Path(racine) / ".atelier" / "runs"


def chemin(racine: Path, run_id: str) -> Path:
    return dossier_runs(racine) / run_id / "etat.json"


def sauver(racine: Path, run: Run) -> Path:
    cible = chemin(racine, run.id)
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.write_text(json.dumps(run.vers_dict(), indent=2, ensure_ascii=False) + "\n")
    return cible


def charger(racine: Path, run_id: str) -> Run:
    cible = chemin(racine, run_id)
    if not cible.is_file():
        raise FileNotFoundError(cible)
    brut = json.loads(cible.read_text(encoding="utf-8"))
    brut["etape"] = Etape(brut["etape"])
    return Run(**brut)


def lister(racine: Path) -> list[Run]:
    racine_runs = dossier_runs(racine)
    if not racine_runs.is_dir():
        return []
    runs = []
    for enfant in sorted(racine_runs.iterdir()):
        etat = enfant / "etat.json"
        if etat.is_file():
            runs.append(charger(racine, enfant.name))
    return runs


def fusionner(_run: Run) -> None:
    raise FusionInterdite(
        "l'atelier ne fusionne pas. Le propriétaire lit le diff et fusionne."
    )
