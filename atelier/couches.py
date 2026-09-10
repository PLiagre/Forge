"""Les sept couches. Un module en déclare une, une seule."""

from __future__ import annotations

from enum import Enum


class Couche(str, Enum):
    INTELLIGENCE = "intelligence"
    OUTILS = "outils"
    MEMOIRE = "memoire"
    EXECUTION = "execution"
    ORCHESTRATION = "orchestration"
    COORDINATION = "coordination"
    VERIFICATION = "verification"


# Chaque module public de l'atelier déclare sa couche ici.
# Un nom absent, ou un nom en double couche, fait rougir test_couches.
MODULES: dict[str, Couche] = {
    "atelier.backends": Couche.INTELLIGENCE,
    "atelier.skills_index": Couche.OUTILS,
    "atelier.memoire": Couche.MEMOIRE,
    "atelier.worktree": Couche.EXECUTION,
    "atelier.cycle": Couche.ORCHESTRATION,
    "atelier.etat": Couche.ORCHESTRATION,
    "atelier.feuille": Couche.ORCHESTRATION,
    "atelier.verrou": Couche.COORDINATION,
    "atelier.quota": Couche.COORDINATION,
    "atelier.echange": Couche.COORDINATION,
    "atelier.boite": Couche.COORDINATION,
    "atelier.reprise": Couche.COORDINATION,
    "atelier.porte": Couche.VERIFICATION,
}


def couche_de(module: str) -> Couche:
    if module not in MODULES:
        raise KeyError(f"module sans couche déclarée : {module}")
    return MODULES[module]


def couches_occupees() -> dict[Couche, list[str]]:
    occupees: dict[Couche, list[str]] = {c: [] for c in Couche}
    for nom, couche in MODULES.items():
        occupees[couche].append(nom)
    return occupees
