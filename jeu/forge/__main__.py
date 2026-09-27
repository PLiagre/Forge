"""
python3 -m forge — lancer une simulation et l'afficher.

Une commande, un monde, quatre sorties. C'est la porte de la V1 : si elle
rend 0, le moteur tourne et les trois vues montrent le même monde.

    python3 -m forge --ticks 365 --seed 0 --sortie /tmp/forge

        monde.json      la photographie — la seule source des trois vues
        carte.png       la statistique en plan, coloriée par une grandeur
        planche.html    la chronique : la suite des instants
        tableau.svg     le tableau de bord, en preuve dessinée
        resume.json     ce que la commande a mesuré

Ce que cette commande NE fait pas : rendre en 3D. Le rendu forge3d demande un
adaptateur GPU, que la CI n'a pas. Il se demande à part, et il refuse
proprement quand la carte manque :

    python3 -m vues.relief --snapshot monde.json --statistique relief.png
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

TICKS_PAR_DEFAUT = 365
LECTURE_PAR_DEFAUT = "population"
PAS_DE_CHRONIQUE = 8


def _simuler(ticks: int, seed: int, destination: Path) -> tuple[Path, dict]:
    """Joue le monde et le photographie. C'est la seule simulation de la commande."""
    from sim.engine import production_moyenne_kg_par_tick, tick as jouer_un_tick
    from sim.constants import FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    from sim.snapshot_export import export_snapshot
    from sim.world import World

    monde = World.charger(rng_seed=seed)
    rng = random.Random(seed)

    population_depart = sum(cell.population for cell in monde.cells.values())
    plafond_depart = production_moyenne_kg_par_tick(monde) / (
        FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK * max(population_depart, 1)
    )

    debut = time.monotonic()
    for _ in range(ticks):
        jouer_un_tick(monde, rng)
    duree = time.monotonic() - debut

    population_arrivee = sum(cell.population for cell in monde.cells.values())
    export_snapshot(monde, seed, ticks, destination)

    return destination, {
        "ticks": ticks,
        "seed": seed,
        "cellules": len(monde.cells),
        "population_depart": population_depart,
        "population_arrivee": population_arrivee,
        "part_survivante": population_arrivee / max(population_depart, 1),
        "plafond_de_survie_a_l_amorcage": plafond_depart,
        "secondes": round(duree, 2),
    }


def _carte(snapshot: Path, sortie: Path, lecture: str, largeur: int) -> dict:
    from PIL import Image

    from vues.relief.statistique import carte_de_statistique, plan_avec_legende, resume

    document = json.loads(snapshot.read_text(encoding="utf-8"))
    carte = carte_de_statistique(document, lecture=lecture, largeur=largeur)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(plan_avec_legende(carte), mode="RGBA").save(sortie)
    return resume(carte)


def _tableau(snapshot: Path, sortie: Path, lecture: str) -> dict:
    """Le tableau de bord, rendu en preuve SVG — la même photographie."""
    from vues.tableau.__main__ import main as tableau_main

    code = tableau_main([
        "--snapshot", str(snapshot),
        "--proof-svg", str(sortie),
        "--layer", lecture,
    ])
    return {"code": code, "svg": str(sortie)}


def _planche(ticks: int, seed: int, pas: int, sortie: Path) -> dict:
    """La chronique : elle rejoue le monde pour en garder plusieurs instants."""
    from vues.chronique.__main__ import main as chronique_main

    code = chronique_main([
        "--ticks", str(ticks),
        "--seed", str(seed),
        "--pas", str(pas),
        "--html", str(sortie),
        "--sans-reseau",
    ])
    return {"code": code, "html": str(sortie)}


def main(argv: list[str] | None = None) -> int:
    from vues.relief.lectures import LECTURES

    parser = argparse.ArgumentParser(
        prog="forge",
        description="Lancer une simulation et l'afficher : une commande, trois vues.",
    )
    parser.add_argument("--ticks", type=int, default=TICKS_PAR_DEFAUT)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--sortie", type=Path, default=Path("sortie"))
    parser.add_argument("--lecture", default=LECTURE_PAR_DEFAUT, choices=sorted(LECTURES))
    parser.add_argument("--largeur", type=int, default=900, help="Largeur du raster de la carte.")
    parser.add_argument(
        "--pas", type=int, default=PAS_DE_CHRONIQUE,
        help="Un instant de chronique tous les N ticks.",
    )
    parser.add_argument(
        "--sans-chronique", action="store_true",
        help="Sauter la planche : elle rejoue le monde, donc elle le paie deux fois.",
    )
    args = parser.parse_args(argv)

    if args.ticks < 0:
        print("--ticks ne peut pas être négatif.", file=sys.stderr)
        return 2
    if args.pas < 1:
        print("--pas vaut au moins 1.", file=sys.stderr)
        return 2

    sortie = args.sortie
    sortie.mkdir(parents=True, exist_ok=True)

    compte_rendu: dict = {"sortie": str(sortie)}

    snapshot, mesures = _simuler(args.ticks, args.seed, sortie / "monde.json")
    compte_rendu["simulation"] = mesures
    compte_rendu["snapshot"] = str(snapshot)

    try:
        compte_rendu["carte"] = _carte(snapshot, sortie / "carte.png", args.lecture, args.largeur)
    except Exception as exc:                      # noqa: BLE001 — on dit lequel a manqué
        print(f"carte : {exc}", file=sys.stderr)
        return 2

    try:
        compte_rendu["tableau"] = _tableau(snapshot, sortie / "tableau.svg", args.lecture)
    except Exception as exc:                      # noqa: BLE001
        print(f"tableau : {exc}", file=sys.stderr)
        return 2

    if not args.sans_chronique:
        try:
            compte_rendu["planche"] = _planche(
                args.ticks, args.seed, args.pas, sortie / "planche.html"
            )
        except Exception as exc:                  # noqa: BLE001
            print(f"planche : {exc}", file=sys.stderr)
            return 2

    (sortie / "resume.json").write_text(
        json.dumps(compte_rendu, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(compte_rendu, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
