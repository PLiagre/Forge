"""Les tests du moteur se jouent en tranches sur la CI.

Le 9 octobre 2026, `sim/tests` jouait 987 tests en 3 h 20 sur un seul cœur : chaque PR, de la
chaîne comme du mode direct, attendait ce temps avant de fusionner. La CI les répartit donc sur
plusieurs travaux (`FORGE_TRANCHE=k/n`, k de 1 à n), chacun sur les cœurs de son runner
(pytest-xdist). Le partage suit les durées mesurées (`tranches.py`) : chaque test est d'une
tranche et d'une seule, un test neuf compris. Sans la variable, tout se joue, comme sur le PC.

Quelques tests comptent des millisecondes (budget d'un tick, cadence de l'horloge) : sur tous les
cœurs d'un runner, leurs mesures sortent du budget. Ils portent `@pytest.mark.chronometre` ; la CI
joue les tranches avec `-m "not chronometre"` et ces tests seuls, un travail à part, sans `-n`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from sim.tests import tranches

VARIABLE = "FORGE_TRANCHE"
# Le fichier où une tranche écrit les durées qu'elle a mesurées (la CI le garde en artefact).
VARIABLE_DUREES = "FORGE_DUREES"

_mesures: dict[str, float] = {}


def pytest_configure(config):
    config.addinivalue_line("markers", "chronometre: compare un temps réel à un budget ; la CI le joue seul, sans -n")


# Après la sélection par `-m` : le partage ne compte que les tests que les tranches jouent.
@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config, items):
    try:
        tranche = tranches.lire_tranche(os.environ.get(VARIABLE))
        if tranche is None:
            return
        durees = tranches.lire_durees()
    except ValueError as e:
        raise pytest.UsageError(f"{VARIABLE} : {e}") from e
    k, n = tranche
    numeros = tranches.repartir([item.nodeid for item in items], durees, n)
    gardes = [item for item, numero in zip(items, numeros) if numero == k]
    ecartes = [item for item, numero in zip(items, numeros) if numero != k]
    if ecartes:
        config.hook.pytest_deselected(items=ecartes)
    items[:] = gardes


def pytest_runtest_logreport(report):
    # Préparation, appel et rangement : tout ce que le test coûte à sa tranche.
    _mesures[report.nodeid] = _mesures.get(report.nodeid, 0.0) + report.duration


def pytest_sessionfinish(session):
    chemin = os.environ.get(VARIABLE_DUREES)
    # Sous xdist, chaque travailleur voit ses tests ; le contrôleur les voit tous et écrit seul.
    if not chemin or hasattr(session.config, "workerinput"):
        return
    Path(chemin).write_text(json.dumps(_mesures, ensure_ascii=False, indent=0), encoding="utf-8")
