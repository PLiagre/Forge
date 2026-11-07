"""Expériences de soudure : ce que porte le grenier des foyers au 1er janvier 1400.

Rien n'est changé dans le dépôt : l'amorçage est remplacé en mémoire avant le
chargement du monde, puis la boucle de `mesure_monde.py` joue. Depuis jeu/ :

    py ../docs/mesures/2026-11-07-refonte/scripts/experience_soudure.py \
        --nom ration-212-habitants --jours 212 --par-habitants --ia

--jours J        : chaque cellule part avec J jours de la ration de ses
                   habitants (à la place des cinq jours et du mois des villes) ;
                   sans --jours, l'amorçage du dépôt (témoin) ;
--perte          : la perte du grenier jusqu'à la moisson est retirée d'avance,
                   × (1 − PERTE_GRENIER_PAR_AN × J / 365) ;
--par-habitants  : le stock de la cellule se partage entre ses lieux à
                   proportion de leurs habitants (le dépôt partage par surface) ;
--ia             : les maisons de l'IA jouent.
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
import sim.lieux as lieux_mod  # noqa: E402
import sim.world as monde_mod  # noqa: E402
from sim.ia import jouer_ia  # noqa: E402
from sim.model import copier_panier, creer_etat_de_lieu, lire_habitants_par_metier  # noqa: E402
from sim.world import World  # noqa: E402
from sim.tests.test_epreuve_jalon2 import lire_reference  # noqa: E402
import mesure_monde as M  # noqa: E402


def amorcer_par_habitants(cellule):
    """Comme lieux.amorcer_lieux, mais les paniers suivent les habitants."""
    surfaces = lieux_mod.surfaces_des_lieux(cellule.cell_id, cellule.area_km2)
    metiers = lire_habitants_par_metier(cellule)
    paysans = cellule.population if metiers == -1 else metiers.get(K.METIER_PAYSANS, 0)
    populations = lieux_mod.partager(paysans, surfaces)
    populations[0] += cellule.population - paysans
    poids = populations if sum(populations) > 0 else list(surfaces)
    paniers = {nom: lieux_mod.partager(total, poids) for nom, total in copier_panier(cellule).items()}
    return [creer_etat_de_lieu(rang, population, {nom: parts[rang] for nom, parts in paniers.items()})
            for rang, population in enumerate(populations)]


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--nom", required=True)
    p.add_argument("--ticks", type=int, default=365)
    p.add_argument("--jalons", default="90,180,365")
    p.add_argument("--jours", type=float, default=None)
    p.add_argument("--perte", action="store_true")
    p.add_argument("--par-habitants", action="store_true")
    p.add_argument("--ia", action="store_true")
    a = p.parse_args(argv)
    if a.jours is not None:
        jours = a.jours
        facteur = (1 - K.PERTE_GRENIER_PAR_AN * jours / K.CALENDAR_DAYS_PER_YEAR) if a.perte else 1.0
        monde_mod._seed_food_stock = (
            lambda population: population * K.FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK * jours * facteur)
        K.RESERVE_VILLES_TICKS = 0
    if a.par_habitants:
        monde_mod.amorcer_lieux = amorcer_par_habitants
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
        "stock_europe_kg": sum(c.stocks.get(K.MARCHANDISE_NOURRITURE, 0) for c in monde.cells.values()),
    }
    morts: dict[int, int] = {}
    origine = engine._apply_mortality

    def compter(cell):
        avant = cell.population
        origine(cell)
        morts[cell.cell_id] = morts.get(cell.cell_id, 0) + (avant - cell.population)

    engine._apply_mortality = compter
    gestes: list = []
    sortie = Path(__file__).parents[1] / "brut" / f"soudure-{a.nom}.json"
    resultat = {"nom": a.nom, "options": vars(a), "commande": " ".join(sys.argv),
                "stock_europe_depart_kg": depart["stock_europe_kg"], "jalons": []}
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
