"""
Entrée unique de la simulation vivante, sans Unity.

    python -m sim
    python -m sim --ticks 365 --seed 0
    python -m sim --json
    python -m sim --ticks 0 --snapshot-json /tmp/world.json

Ce module est le produit qu'on lance. Il tourne sans moteur de rendu.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from sim.constants import DEFAULT_CLI_SEED, DEFAULT_CLI_TICKS, MARCHANDISE_NOURRITURE
from sim.engine import tick
from sim.snapshot_export import SnapshotExportError, export_snapshot
from sim.model import lire_stock_marchandise
from sim.world import World

# Code de sortie pour un argument refusé.
EXIT_REFUS = 2


def _simulate(ticks: int, seed: int) -> tuple[dict, World]:
    """Amorce le monde G3 et avance `ticks` pas. Retourne résumé + monde."""
    world = World.charger(rng_seed=seed)
    population_depart = sum(cell.population for cell in world.cells.values())
    stock_depart = sum(
        lire_stock_marchandise(cell, MARCHANDISE_NOURRITURE)
        for cell in world.cells.values()
    )
    rng = random.Random(seed)
    kg_transportes = 0.0
    for numero_tick in range(ticks):
        kg_transportes += tick(world, rng, numero_tick)
    population_arrivee = sum(cell.population for cell in world.cells.values())
    stock_arrivee = sum(
        lire_stock_marchandise(cell, MARCHANDISE_NOURRITURE)
        for cell in world.cells.values()
    )
    cellules_affamees = sum(
        1 for cell in world.cells.values() if cell.hunger_ticks > 0
    )
    resume = {
        "ticks": ticks,
        "seed": seed,
        "cellules": len(world.cells),
        "population_depart": population_depart,
        "population_arrivee": population_arrivee,
        "stock_kg_depart": stock_depart,
        "stock_kg_arrivee": stock_arrivee,
        "kg_transportes": kg_transportes,
        "cellules_affamees": cellules_affamees,
        "sans_unity": True,
    }
    return resume, world


def run(ticks: int, seed: int) -> dict:
    """Amorce le monde G3 et avance `ticks` pas. Retourne un résumé mesuré."""
    resume, _world = _simulate(ticks, seed)
    return resume


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Moteur ForgeHistory — la simulation, sans moteur de rendu."
    )
    parser.add_argument("--ticks", type=int, default=DEFAULT_CLI_TICKS)
    parser.add_argument("--seed", type=int, default=DEFAULT_CLI_SEED)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument(
        "--snapshot-json",
        dest="snapshot_json",
        default=None,
        help="écrit une photographie cellulaire déterministe (schéma v0a-1)",
    )
    args = parser.parse_args(argv)
    if args.ticks < 0:
        print("refus : --ticks doit être ≥ 0", file=sys.stderr)
        return EXIT_REFUS
    resume, world = _simulate(args.ticks, args.seed)
    if args.snapshot_json:
        try:
            export_snapshot(world, args.seed, args.ticks, Path(args.snapshot_json))
        except (OSError, SnapshotExportError, ValueError, KeyError) as exc:
            print(f"refus : snapshot impossible ({exc})", file=sys.stderr)
            return EXIT_REFUS
    if args.as_json:
        print(json.dumps(resume, sort_keys=True))
        return 0
    print("ForgeHistory — simulation sans Unity")
    print(f"  ticks              : {resume['ticks']}")
    print(f"  graine             : {resume['seed']}")
    print(f"  cellules           : {resume['cellules']}")
    print(f"  population départ  : {resume['population_depart']}")
    print(f"  population arrivée : {resume['population_arrivee']}")
    print(f"  stock kg départ    : {resume['stock_kg_depart']:.1f}")
    print(f"  stock kg arrivée   : {resume['stock_kg_arrivee']:.1f}")
    print(f"  kg transportés     : {resume['kg_transportes']:.1f}")
    print(f"  cellules affamées  : {resume['cellules_affamees']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
