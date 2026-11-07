"""Pourquoi les villes meurent : besoin, plafond local, importations.

Depuis jeu/ :

    py ../docs/mesures/2026-11-06-refonte/scripts/diagnostic_villes.py --ticks 120

Pour chaque cellule de ville de la mesure (Paris, Milan, Florence, Gand et
Bruges, Le Caire, Constantinople, Londres) : la population de départ, ce que
la cellule nourrit au rendement moyen (`population_soutenable_de`), le manque
de chaque jour à la ration, le stock du 1er janvier ; puis, tick après tick,
ce que le commerce lui apporte (le stock de la cellule juste avant et juste
après `_apply_commerce`), moyenné par fenêtre de trente jours. Sans IA : on
mesure le moteur, pas les décisions.
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from sim import constants as K  # noqa: E402
from sim import engine  # noqa: E402
from sim.model import lire_stock_marchandise  # noqa: E402
from sim.world import World  # noqa: E402

VILLES = ["Paris", "Milan", "Florence", "Gand", "Le Caire", "Constantinople", "Londres"]


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--ticks", type=int, default=120)
    p.add_argument("--seed", type=int, default=0)
    a = p.parse_args(argv)
    monde = World.charger(rng_seed=a.seed)
    nourriture = K.MARCHANDISE_NOURRITURE
    ration = K.FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    cibles = {nom: cid for nom, cid in monde.attribution_villes.placees.items() if nom in VILLES}
    print("ville           cell   pop0   soutenable  manque_t/j  stock0_t  voisins")
    voisins = {}
    for arete in monde.adjacency:
        if arete.get("kind") == "land-land":
            voisins.setdefault(arete["a"], set()).add(arete["b"])
            voisins.setdefault(arete["b"], set()).add(arete["a"])
    for nom, cid in sorted(cibles.items()):
        c = monde.cells[cid]
        s = engine.population_soutenable_de(c, monde.carte)
        manque = max(0.0, c.population - s) * ration / 1000
        print(f"{nom:15s} {cid:5d} {c.population:7d} {s:10.0f} {manque:11.1f} "
              f"{lire_stock_marchandise(c, nourriture) / 1000:9.1f}  {len(voisins.get(cid, ()))}")
    apports = {cid: [] for cid in cibles.values()}
    origine = engine._apply_commerce

    profondeur = [0]

    def commerce(world, total, *args, **kw):
        # Le maillon s'appelle lui-même par marchandise : on ne mesure que
        # l'appel extérieur, celui du tick.
        if profondeur[0]:
            return origine(world, total, *args, **kw)
        profondeur[0] += 1
        avant = {cid: lire_stock_marchandise(world.cells[cid], nourriture) for cid in apports}
        try:
            resultat = origine(world, total, *args, **kw)
        finally:
            profondeur[0] -= 1
        for cid in apports:
            apports[cid].append(lire_stock_marchandise(world.cells[cid], nourriture) - avant[cid])
        return resultat

    engine._apply_commerce = commerce
    rng = random.Random(a.seed)
    pops = {cid: [] for cid in cibles.values()}
    for _ in range(a.ticks):
        engine.tick(monde, rng, monde.ticks_ecoules)
        for cid in pops:
            pops[cid].append(monde.cells[cid].population)
    fen = K.FENETRE_FLUX_TICKS
    print(f"\napports nets du commerce (t/jour, moyenne par fenêtre de {fen} jours) et population en fin de fenêtre")
    for nom, cid in sorted(cibles.items()):
        ligne = []
        for debut in range(0, a.ticks, fen):
            tranche = apports[cid][debut:debut + fen]
            ligne.append(f"{sum(tranche) / len(tranche) / 1000:7.1f} t ({pops[cid][min(debut + fen, a.ticks) - 1]:>6})")
        print(f"{nom:15s} " + " | ".join(ligne))
    return 0


if __name__ == "__main__":
    sys.exit(main())
