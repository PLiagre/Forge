"""Expériences sur le monde sans joueur : ce qui ferait tenir les villes.

Rien n'est changé dans le dépôt : les constantes sont remplacées en mémoire
avant le chargement du monde, puis la boucle de `mesure_monde.py` joue.
Depuis jeu/ :

    py ../docs/mesures/2026-11-07-refonte/scripts/experience_monde.py \
        --nom soudure-213 --soudure-jours 213 --ticks 365

--soudure-jours N : chaque cellule part avec N jours de sa propre ration
                    (à la place des cinq jours et du mois des villes) ;
--transport K     : chemins intérieurs et frontières portent K fois plus ;
--ia              : les maisons de l'IA jouent (plus lent).
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path(__file__).parent))

from sim import constants as K  # noqa: E402
from sim import engine  # noqa: E402
import sim.world as monde_mod  # noqa: E402
from sim.ia import jouer_ia  # noqa: E402
from sim.world import World  # noqa: E402
from sim.tests.test_epreuve_jalon2 import lire_reference  # noqa: E402
import mesure_monde as M  # noqa: E402


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--nom", required=True)
    p.add_argument("--ticks", type=int, default=365)
    p.add_argument("--jalons", default="90,365")
    p.add_argument("--soudure-jours", type=float, default=None)
    p.add_argument("--transport", type=float, default=1.0)
    p.add_argument("--ia", action="store_true")
    a = p.parse_args(argv)
    if a.soudure_jours is not None:
        jours = a.soudure_jours
        monde_mod._seed_food_stock = (
            lambda population: population * K.FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK * jours)
        K.RESERVE_VILLES_TICKS = 0
    if a.transport != 1.0:
        K.CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK *= a.transport
        K.DEBIT_KG_PAR_KM_DE_FRONTIERE_PAR_TICK *= a.transport
    jalons = sorted({int(x) for x in a.jalons.split(",")})
    t0 = time.perf_counter()
    monde = World.charger(rng_seed=0)
    rng = random.Random(0)
    reference = lire_reference()
    ref_cellules = M.cellules_de_la_reference(monde, reference)
    depart = {
        "europe": sum(c.population for c in monde.cells.values()),
        "cellules": {cid: c.population for cid, c in monde.cells.items()},
        "bourgs": {cid: next(l for l in c.lieux if l.rang == 0).population
                   for cid, c in monde.cells.items()},
    }
    morts: dict[int, int] = {}
    origine = engine._apply_mortality

    def compter(cell):
        avant = cell.population
        origine(cell)
        morts[cell.cell_id] = morts.get(cell.cell_id, 0) + (avant - cell.population)

    engine._apply_mortality = compter
    gestes: list = []
    sortie = Path(__file__).parents[1] / "brut" / f"experience-{a.nom}.json"
    resultat = {"nom": a.nom, "options": vars(a), "jalons": []}
    for _ in range(a.ticks):
        if a.ia:
            jouer_ia(monde, gestes)
        engine.tick(monde, rng, monde.ticks_ecoules)
        if monde.ticks_ecoules in jalons:
            r = M.releve(monde, depart, morts, ref_cellules, reference, gestes, t0)
            resultat["jalons"].append(r)
            sortie.write_text(json.dumps(resultat, ensure_ascii=False, indent=1), encoding="utf-8")
            v = r["villes"]
            pire = r["faim_table"]["pire"]
            print(f"{a.nom} t={r['tick']} europe={r['part_europe']:.3f} "
                  + " ".join(f"{n}={v[n]['part_cellule']:.2f}" for n in M.VILLES if n in v)
                  + f" echecs={len(r['jalon2']['echecs'])}"
                  f" faim>50%={len(r['faim_table']['plus_de_moitie_morte_de_faim'])}"
                  f" pire={pire['noms'][0]}:{pire['part_morte_de_faim']:.2f}"
                  f" ({r['secondes_ecoulees']} s)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
