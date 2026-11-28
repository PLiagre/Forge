"""Le chronométrage d'un jour du monde, tel que le service le joue.

Les tests de budget (`BUDGET_TICK_MS`) mesurent tous par `chronometrer_les_jours` :

- un monde chargé par `World.charger(0)`, seul de son espèce en mémoire, jamais
  une copie : une copie joue les mêmes appels, mais sa mémoire est dispersée et
  un second monde reste en vie à côté ;
- figé hors du ramasse-miettes par `service.regler_le_ramasse_miettes()`, comme
  `main()` le fait au lancement du service ;
- `RODAGE` jours joués d'abord, puis `MESURES` jours chronométrés.

Le réglage est défait (`gc.unfreeze()`) à la fin de la mesure, même quand elle
échoue : les objets des autres tests restent ramassés.
"""
import gc
import random
import time

from sim import engine, service
from sim.world import World

RODAGE = 5
MESURES = 20
MS = 1000


def _jouer_un_tick(monde, rng, numero):
    engine.tick(monde, rng, numero)


def chronometrer_les_jours(preparer=None, *, charger=None, jouer=None):
    """Rend le monde joué et la durée, en millisecondes, de chacun des `MESURES` jours chronométrés."""
    monde = (charger or (lambda: World.charger(0)))()
    if preparer is not None:
        preparer(monde)
    jouer = jouer or _jouer_un_tick
    rng, durees = random.Random(0), []
    service.regler_le_ramasse_miettes()
    try:
        for numero in range(RODAGE + MESURES):
            debut = time.perf_counter()
            jouer(monde, rng, numero)
            if numero >= RODAGE:
                durees.append((time.perf_counter() - debut) * MS)
    finally:
        gc.unfreeze()
    return monde, durees
