"""
python3 -m vues.relief — photographie → carte.

Deux cartes, un seul monde :

    --relief PNG      la géographie : le terrain élevé en mètres de lecture.
    --carte PNG       la statistique : une grandeur du monde, en plan colorié.
    --statistique PNG la même statistique, mais élevée en relief par forge3d.

Le plan ne demande aucun GPU : c'est lui que la CI vérifie. Les deux rendus
forge3d refusent proprement, avec le code 2, quand aucun adaptateur n'est là.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# wgpu verrouille le backend au premier contexte. Le poser avant forge3d.
os.environ.setdefault("WGPU_BACKENDS", "vulkan")

SNAPSHOT_PAR_DEFAUT = Path("/tmp/forge-monde.json")


def _photographier(ticks: int, seed: int, chemin: Path) -> Path:
    from sim.world import World
    from sim.engine import tick
    from sim.snapshot_export import export_snapshot
    import random

    monde = World.charger(rng_seed=seed)
    rng = random.Random(seed)
    for _ in range(int(ticks)):
        tick(monde, rng)
    return export_snapshot(monde, seed, ticks, chemin)


def main(argv: list[str] | None = None) -> int:
    from vues.relief.lectures import LECTURES, LECTURE_PAR_DEFAUT

    parser = argparse.ArgumentParser(
        description="Regard 3D : lit une photographie de sim/, en fait des cartes."
    )
    parser.add_argument("--snapshot", type=Path, help="Photographie JSON déjà écrite.")
    parser.add_argument("--ticks", type=int, help="Photographier après N ticks, puis rendre.")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--lecture",
        default=LECTURE_PAR_DEFAUT,
        choices=sorted(LECTURES),
        help="La grandeur que la carte de statistique montre.",
    )
    parser.add_argument("--carte", type=Path, help="Plan colorié de la statistique (sans GPU).")
    parser.add_argument("--statistique", type=Path, help="Statistique élevée en relief (forge3d).")
    parser.add_argument("--relief", type=Path, help="Relief géographique (forge3d).")
    parser.add_argument("--apercu", type=Path, help="Plan des altitudes, contrôle du raster.")
    parser.add_argument("--largeur", type=int, default=640, help="Largeur du raster.")
    parser.add_argument("--largeur-px", type=int, default=1280, help="Largeur des images forge3d.")
    parser.add_argument("--hauteur-px", type=int, default=720, help="Hauteur des images forge3d.")
    args = parser.parse_args(argv)

    if args.snapshot is None and args.ticks is None:
        print("Il faut --snapshot ou --ticks.", file=sys.stderr)
        return 2
    if args.snapshot is not None and args.ticks is not None:
        print("--snapshot et --ticks s'excluent.", file=sys.stderr)
        return 2

    sorties = (args.carte, args.statistique, args.relief, args.apercu)
    if not any(sortie is not None for sortie in sorties):
        print(
            "Aucune sortie demandée : --carte, --statistique, --relief ou --apercu.",
            file=sys.stderr,
        )
        return 2

    if args.snapshot is not None:
        snapshot_path = args.snapshot
        if not snapshot_path.is_file():
            print(f"snapshot introuvable : {snapshot_path}", file=sys.stderr)
            return 2
    else:
        if args.ticks < 0:
            print("--ticks ne peut pas être négatif.", file=sys.stderr)
            return 2
        snapshot_path = SNAPSHOT_PAR_DEFAUT
        _photographier(args.ticks, args.seed, snapshot_path)

    document = json.loads(snapshot_path.read_text(encoding="utf-8"))

    from PIL import Image

    from vues.relief.lectures import LectureErreur
    from vues.relief.raster import RasterErreur, apercu_altitude, rasteriser
    from vues.relief.rendu import RenduErreur, STOPS_RELIEF, rendre_champ_png, rendre_png
    from vues.relief.statistique import (
        ALTITUDE_MAX_LECTURE_M,
        altitudes_de,
        carte_de_statistique,
        plan_avec_legende,
        resume,
    )
    from vues.relief.lectures import RAMPE

    compte_rendu: dict = {"snapshot": str(snapshot_path)}

    # --- la statistique : plan, puis relief ---
    if args.carte is not None or args.statistique is not None:
        try:
            carte = carte_de_statistique(document, lecture=args.lecture, largeur=args.largeur)
        except (LectureErreur, RasterErreur) as exc:
            print(str(exc), file=sys.stderr)
            return 2

        compte_rendu["statistique"] = resume(carte)

        if args.carte is not None:
            args.carte.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(plan_avec_legende(carte), mode="RGBA").save(args.carte)
            compte_rendu["carte"] = str(args.carte)

        if args.statistique is not None:
            stops = [
                (i / (len(RAMPE) - 1), teinte) for i, teinte in enumerate(RAMPE)
            ]
            try:
                rendre_champ_png(
                    altitudes_de(carte),
                    (~carte.masque_terre).astype("float32"),
                    args.statistique,
                    stops=stops,
                    h_max=ALTITUDE_MAX_LECTURE_M,
                    largeur_px=args.largeur_px,
                    hauteur_px=args.hauteur_px,
                )
            except RenduErreur as exc:
                print(str(exc), file=sys.stderr)
                return 2
            compte_rendu["relief_de_statistique"] = str(args.statistique)

    # --- la géographie ---
    if args.relief is not None or args.apercu is not None:
        try:
            mnt = rasteriser(document, largeur=args.largeur)
        except RasterErreur as exc:
            print(str(exc), file=sys.stderr)
            return 2

        compte_rendu["cellules"] = mnt.cellules
        compte_rendu["tick"] = mnt.tick
        compte_rendu["seed"] = mnt.seed

        if args.apercu is not None:
            args.apercu.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(apercu_altitude(mnt), mode="RGBA").save(args.apercu)
            compte_rendu["apercu"] = str(args.apercu)

        if args.relief is not None:
            try:
                rendre_png(
                    mnt,
                    args.relief,
                    largeur_px=args.largeur_px,
                    hauteur_px=args.hauteur_px,
                )
            except RenduErreur as exc:
                print(str(exc), file=sys.stderr)
                return 2
            compte_rendu["relief"] = str(args.relief)

    print(json.dumps(compte_rendu, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
