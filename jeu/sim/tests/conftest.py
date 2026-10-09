"""Les tests du moteur se jouent en tranches sur la CI.

Le 9 octobre 2026, `sim/tests` jouait 987 tests en 3 h 20 sur un seul cœur : chaque PR, de la
chaîne comme du mode direct, attendait ce temps avant de fusionner. La CI les répartit donc sur
plusieurs travaux (`FORGE_TRANCHE=k/n`, k de 1 à n), chacun sur les cœurs de son runner
(pytest-xdist). Les tests se distribuent un à un, à tour de rôle dans l'ordre de collecte : les
longs tests d'un même fichier tombent dans des tranches différentes, et aucun fichier neuf
n'échappe à la répartition. Sans la variable, tout se joue, comme sur le PC.
"""

from __future__ import annotations

import os

import pytest

VARIABLE = "FORGE_TRANCHE"


def lire_tranche(valeur: str | None) -> tuple[int, int] | None:
    """« k/n » → (k, n) ; None sans variable. Une valeur fausse est une erreur, jamais « tout jouer »."""
    if valeur is None or valeur == "":
        return None
    morceaux = valeur.split("/")
    if len(morceaux) != 2 or not all(m.isdigit() for m in morceaux):
        raise pytest.UsageError(f"{VARIABLE}={valeur!r} : attendu « k/n », deux entiers")
    k, n = int(morceaux[0]), int(morceaux[1])
    if not 1 <= k <= n:
        raise pytest.UsageError(f"{VARIABLE}={valeur!r} : attendu 1 ≤ k ≤ n")
    return k, n


def dans_la_tranche(rang: int, k: int, n: int) -> bool:
    """Le test de rang `rang` (0, 1, 2… dans l'ordre de collecte) est-il de la tranche k sur n ?"""
    return rang % n == k - 1


def pytest_collection_modifyitems(config, items):
    tranche = lire_tranche(os.environ.get(VARIABLE))
    if tranche is None:
        return
    gardes = [item for rang, item in enumerate(items) if dans_la_tranche(rang, *tranche)]
    ecartes = [item for rang, item in enumerate(items) if not dans_la_tranche(rang, *tranche)]
    if ecartes:
        config.hook.pytest_deselected(items=ecartes)
    items[:] = gardes
