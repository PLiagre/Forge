"""Un fichier n'est pas dans deux lots actifs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json


class Collision(ValueError):
    pass


@dataclass
class Verrou:
    lot: str
    fichiers: frozenset[str]


@dataclass
class Tableau:
    racine: Path
    poses: list[Verrou] = field(default_factory=list)

    @property
    def fichier(self) -> Path:
        return self.racine / ".atelier" / "verrous.json"


def charger(racine: Path) -> Tableau:
    tableau = Tableau(racine=Path(racine))
    if not tableau.fichier.is_file():
        return tableau
    brut = json.loads(tableau.fichier.read_text(encoding="utf-8"))
    if not brut:
        raise Collision("verrous.json présent mais vide — un échantillon vide échoue")
    for entree in brut:
        tableau.poses.append(
            Verrou(lot=entree["lot"], fichiers=frozenset(entree["fichiers"]))
        )
    return tableau


def _sauver(tableau: Tableau) -> None:
    tableau.fichier.parent.mkdir(parents=True, exist_ok=True)
    payload = [{"lot": v.lot, "fichiers": sorted(v.fichiers)} for v in tableau.poses]
    tableau.fichier.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def poser(racine: Path, lot: str, fichiers: list[str]) -> Verrou:
    if not fichiers:
        raise Collision("un verrou sans fichier n'en est pas un")
    normalises = frozenset(Path(f).as_posix() for f in fichiers)
    tableau = charger(racine)
    for autre in tableau.poses:
        if autre.lot == lot:
            continue
        commun = autre.fichiers & normalises
        if commun:
            raise Collision(
                f"lot {lot} entre en collision avec {autre.lot} : "
                + ", ".join(sorted(commun))
            )
    verrou = Verrou(lot=lot, fichiers=normalises)
    tableau.poses = [v for v in tableau.poses if v.lot != lot]
    tableau.poses.append(verrou)
    _sauver(tableau)
    return verrou


def lever(racine: Path, lot: str) -> None:
    tableau = charger(racine)
    tableau.poses = [v for v in tableau.poses if v.lot != lot]
    if tableau.poses:
        _sauver(tableau)
    elif tableau.fichier.is_file():
        tableau.fichier.unlink()
