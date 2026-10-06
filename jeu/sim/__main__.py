"""
Entrée unique de la simulation vivante, sans Unity.

    python -m sim
    python -m sim --ticks 365 --seed 0
    python -m sim --json
    python -m sim --ticks 0 --snapshot-json /tmp/world.json
    python3 -m sim --ticks 4 --gestes gestes.json
    python3 -m sim --ticks 4 --gestes gestes.json --monde-json monde.json

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
from sim.ia import jouer_ia, maisons_actives_30j
from sim.intentions import IntentionRefusee, recevoir_intention
from sim.snapshot_export import SnapshotExportError, export_snapshot
from sim.model import lire_stock_marchandise
from sim.world import World

# Code de sortie pour un argument refusé.
EXIT_REFUS = 2


def _valider_gestes(gestes, ticks):
    """Refuse toute chronologie ambiguë avant de charger ou jouer le monde."""
    if not isinstance(gestes, list):
        raise IntentionRefusee("gestes : liste JSON attendue")
    precedent = -1
    for rang, entree in enumerate(gestes, start=1):
        if not isinstance(entree, dict):
            raise IntentionRefusee(f"entrée {rang} : objet attendu")
        for champ in ("tick", "intention"):
            if champ not in entree:
                raise IntentionRefusee(f"entrée {rang} : champ manquant : {champ}")
        numero = entree["tick"]
        if isinstance(numero, bool) or not isinstance(numero, int) or numero < 0:
            raise IntentionRefusee(f"entrée {rang} : tick invalide : {numero!r}")
        if numero < precedent:
            raise IntentionRefusee(f"entrée {rang} : ticks décroissants")
        if numero >= ticks:
            raise IntentionRefusee(f"entrée {rang} : l'intention s'applique au tick suivant")
        precedent = numero
    return gestes


def _simulate(ticks: int, seed: int, gestes=None, ia=False) -> tuple[dict, World]:
    """Amorce le monde G3 et avance `ticks` pas. Retourne résumé + monde."""
    gestes = _valider_gestes([] if gestes is None else gestes, ticks)
    world = World.charger(rng_seed=seed)
    population_depart = sum(cell.population for cell in world.cells.values())
    stock_depart = sum(
        lire_stock_marchandise(cell, MARCHANDISE_NOURRITURE)
        for cell in world.cells.values()
    )
    rng = random.Random(seed)
    kg_transportes = 0.0
    rang = 0
    releve = []
    for _ in range(ticks):
        while rang < len(gestes) and gestes[rang]["tick"] == world.ticks_ecoules:
            try:
                recevoir_intention(world, gestes[rang]["intention"])
            except IntentionRefusee as exc:
                raise IntentionRefusee(f"entrée {rang + 1} : {exc}") from exc
            rang += 1
        if ia:
            jouer_ia(world, releve)
        kg_transportes += tick(world, rng, world.ticks_ecoules)
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
        "date_simulation": world.date_simulation,
    }
    if ia:
        resume['ia'] = {'releve': releve, 'maisons_actives_30j': maisons_actives_30j(world.ticks_ecoules, releve)}
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
    parser.add_argument("--gestes", help="rejoue une liste JSON d'intentions datées")
    parser.add_argument("--ia", action="store_true", help="active les décisions des maisons de l'IA")
    parser.add_argument("--monde-json", help="écrit le monde final en JSON canonique")
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
    try:
        gestes = None
        if args.gestes is not None:
            gestes = _valider_gestes(
                json.loads(Path(args.gestes).read_text(encoding="utf-8")), args.ticks,
            )
        resume, world = _simulate(args.ticks, args.seed, gestes, ia=args.ia)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"refus : {exc}", file=sys.stderr)
        return EXIT_REFUS
    if args.snapshot_json:
        try:
            export_snapshot(world, args.seed, args.ticks, Path(args.snapshot_json))
        except (OSError, SnapshotExportError, ValueError, KeyError) as exc:
            print(f"refus : snapshot impossible ({exc})", file=sys.stderr)
            return EXIT_REFUS
    if args.monde_json is not None:
        try:
            Path(args.monde_json).write_text(
                json.dumps(world.to_dict(), sort_keys=True, ensure_ascii=False,
                           separators=(",", ":")), encoding="utf-8",
            )
        except OSError as exc:
            print(f"refus : monde impossible ({exc})", file=sys.stderr)
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
    date = resume["date_simulation"]
    print(f"  année              : {date['annee']}")
    print(f"  jour dans l'année  : {date['jour_de_l_annee']}")
    if args.ia:
        print(f"  maisons actives 30j : {resume['ia']['maisons_actives_30j']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
