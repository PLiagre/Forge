"""Les tests du jeu sur la CI : la suite rapide, les preuves longues, les tranches.

**Les preuves longues.** Un test est une preuve longue quand, joué seul, il coûte au moins
`SEUIL_LONGUE_S` secondes d'après `durees.json`, ou quand il porte `@pytest.mark.longue`. La suite
exigée pour fusionner (`tests.yml`) joue `-m "not longue"` ; la nuit (`nuit.yml`) joue tout. Sans
option, tout se joue, comme sur le PC. Un test neuf, que la nuit n'a pas encore mesuré, est rapide :
son auteur le marque `longue` quand il sait qu'il fait tourner une année du monde.

**Le coût d'un test joué seul** est sa préparation, son appel et son rangement, plus les
préparations partagées (d'un module, de la session) dont il a besoin, même quand un autre test les a
payées avant lui : sinon, écarter le premier test d'un module ferait payer le monde d'un an au
suivant, et la suite rapide ne le serait pas.

**Les tranches.** Sur un seul cœur, `sim/tests` prend des heures. La CI le répartit sur plusieurs
travaux (`FORGE_TRANCHE=k/n`, k de 1 à n), chacun sur les cœurs de son runner (pytest-xdist). Le
partage suit les durées mesurées (`tranches.py`) : chaque test est d'une tranche et d'une seule, un
test neuf compris.

**Les tests qui chronomètrent.** Quelques tests comptent des millisecondes (budget d'un tick, cadence
de l'horloge) : sur tous les cœurs d'un runner, leurs mesures sortent du budget. Ils portent
`@pytest.mark.chronometre` ; la CI les joue seuls, un travail à part, sans `-n`.

Quand `FORGE_DUREES` nomme un fichier, les coûts mesurés s'y ajoutent ; la CI le garde en artefact.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

import tranches

VARIABLE = "FORGE_TRANCHE"
VARIABLE_DUREES = "FORGE_DUREES"
# Au-dessus, un test est une preuve longue : la nuit le joue, pas la suite exigée pour fusionner.
SEUIL_LONGUE_S = 5.0
# Le coût des préparations partagées qu'un test n'a pas payées lui-même, porté par son compte rendu.
PARTAGE = "forge_preparations_partagees"

_mesures: dict[str, float] = {}
# Par préparation partagée (l'identité de sa définition) : les secondes de sa dernière mise en place.
_preparations: dict[int, float] = {}
# Les préparations partagées mises en place pendant la préparation du test en cours.
_payees: set[int] = set()


def nom(nodeid: str) -> str:
    """L'identifiant d'un test tel que `durees.json` l'écrit : depuis `jeu/`, d'où que pytest parte."""
    fichier, deux_points, reste = nodeid.partition("::")
    return fichier.removeprefix("jeu/") + deux_points + reste


def pytest_configure(config):
    config.addinivalue_line("markers", "chronometre: compare un temps réel à un budget ; la CI le joue seul, sans -n")
    config.addinivalue_line("markers", "longue: preuve longue (une année du monde) ; la nuit la joue, pas la suite "
                                       "exigée pour fusionner")


@pytest.hookimpl(hookwrapper=True)
def pytest_collection_modifyitems(config, items):
    # Avant la sélection par `-m` : la marque `longue` se déduit des durées mesurées.
    try:
        tranche = tranches.lire_tranche(os.environ.get(VARIABLE))
        durees = tranches.lire_durees()
    except ValueError as e:
        raise pytest.UsageError(f"{VARIABLE} ou durees.json : {e}") from e
    for item in items:
        if durees.get(nom(item.nodeid), 0.0) >= SEUIL_LONGUE_S:
            item.add_marker(pytest.mark.longue)
    yield
    # Après la sélection : le partage ne compte que les tests que les tranches jouent.
    if tranche is None:
        return
    k, n = tranche
    numeros = tranches.repartir([nom(item.nodeid) for item in items], durees, n)
    gardes = [item for item, numero in zip(items, numeros) if numero == k]
    ecartes = [item for item, numero in zip(items, numeros) if numero != k]
    if ecartes:
        config.hook.pytest_deselected(items=ecartes)
    items[:] = gardes


@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_setup(fixturedef, request):
    debut = time.perf_counter()
    yield
    if fixturedef.scope != "function":
        _preparations[id(fixturedef)] = time.perf_counter() - debut
        _payees.add(id(fixturedef))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_setup(item):
    _payees.clear()
    yield
    partagees = {id(definitions[-1]) for definitions in item._fixtureinfo.name2fixturedefs.values() if definitions}
    du = sum(_preparations.get(d, 0.0) for d in partagees - _payees)
    item.user_properties.append((PARTAGE, du))


def pytest_runtest_logreport(report):
    cle = nom(report.nodeid)
    _mesures[cle] = _mesures.get(cle, 0.0) + report.duration
    if report.when == "setup":
        _mesures[cle] += sum(valeur for propriete, valeur in report.user_properties if propriete == PARTAGE)


def pytest_sessionfinish(session):
    chemin = os.environ.get(VARIABLE_DUREES)
    # Sous xdist, chaque travailleur voit ses tests ; le contrôleur les voit tous et écrit seul.
    if not chemin or hasattr(session.config, "workerinput"):
        return
    fichier = Path(chemin)
    # Un travail joue plusieurs dossiers l'un après l'autre : leurs mesures s'ajoutent au même fichier.
    deja = json.loads(fichier.read_text(encoding="utf-8")) if fichier.is_file() else {}
    fichier.write_text(json.dumps({**deja, **_mesures}, ensure_ascii=False, indent=0), encoding="utf-8")
