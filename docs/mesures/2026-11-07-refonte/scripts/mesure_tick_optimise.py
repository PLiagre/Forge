"""Le tick avec IA quand la boucle calcule une fois la liste des maisons de l'IA.

Rien n'est changé dans le dépôt : `sim.ia.maisons_de_l_ia` est remplacée en
mémoire par la liste calculée une fois au chargement (monde sans joueur, donc
toutes les maisons ; `decider_intentions` écarte déjà celle du joueur). Le
script vérifie d'abord que le monde reste le même (empreinte sha256 du monde au
tick N, avec et sans le remplacement), puis chronomètre et profile. Depuis jeu/ :

    py ../docs/mesures/2026-11-07-refonte/scripts/mesure_tick_optimise.py \
        --sortie ../docs/mesures/2026-11-07-refonte/brut/tick-optimise.json
"""
from __future__ import annotations

import argparse
import cProfile
import io
import json
import pstats
import random
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path(__file__).parent))

from sim import engine  # noqa: E402
import sim.ia as ia  # noqa: E402
from sim.capitales import maisons_de_l_ia  # noqa: E402
from sim.world import World  # noqa: E402
from mesure_monde import empreinte  # noqa: E402

ORIGINE = ia.maisons_de_l_ia


def jouer(ticks, optimise, seed=0, chrono_depuis=None, profil=None):
    monde = World.charger(rng_seed=seed)
    rng = random.Random(seed)
    gestes: list = []
    if optimise:
        liste = maisons_de_l_ia(monde)
        ia.maisons_de_l_ia = lambda m: liste
    else:
        ia.maisons_de_l_ia = ORIGINE
    t_ia, t_tick = [], []
    for _ in range(ticks):
        mesurer = chrono_depuis is not None and monde.ticks_ecoules >= chrono_depuis
        if mesurer and profil is not None:
            profil.enable()
        a = time.perf_counter()
        ia.jouer_ia(monde, gestes)
        b = time.perf_counter()
        engine.tick(monde, rng, monde.ticks_ecoules)
        c = time.perf_counter()
        if mesurer and profil is not None:
            profil.disable()
        if mesurer:
            t_ia.append((b - a) * 1000)
            t_tick.append((c - b) * 1000)
    ia.maisons_de_l_ia = ORIGINE
    return monde, gestes, t_ia, t_tick


def resume(xs):
    return {"mediane_ms": round(statistics.median(xs), 2),
            "min_ms": round(min(xs), 2), "max_ms": round(max(xs), 2)}


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--ticks-egalite", type=int, default=120)
    p.add_argument("--chauffe", type=int, default=30)
    p.add_argument("--n", type=int, default=60)
    p.add_argument("--sortie", required=True)
    a = p.parse_args(argv)
    m1, g1, _, _ = jouer(a.ticks_egalite, optimise=False)
    m2, g2, _, _ = jouer(a.ticks_egalite, optimise=True)
    egal = {"ticks": a.ticks_egalite, "empreinte_depot": empreinte(m1),
            "empreinte_optimise": empreinte(m2), "monde_egal": empreinte(m1) == empreinte(m2),
            "gestes_egaux": json.dumps(g1, sort_keys=True) == json.dumps(g2, sort_keys=True),
            "gestes": len(g1)}
    print("égalité", egal, flush=True)
    profil = cProfile.Profile()
    _, _, t_ia, t_tick = jouer(a.chauffe + a.n, optimise=True, chrono_depuis=a.chauffe)
    total = [x + y for x, y in zip(t_ia, t_tick)]
    chrono = {"ticks_mesures": [a.chauffe, a.chauffe + a.n - 1], "jouer_ia": resume(t_ia),
              "tick": resume(t_tick), "total": resume(total)}
    print("optimisé", chrono, flush=True)
    jouer(a.chauffe + 30, optimise=True, chrono_depuis=a.chauffe + 0, profil=profil)
    tampon = io.StringIO()
    pstats.Stats(profil, stream=tampon).sort_stats("cumulative").print_stats(25)
    sortie = Path(a.sortie)
    sortie.write_text(json.dumps({"egalite": egal, "avec_ia_optimise": chrono},
                                 ensure_ascii=False, indent=1), encoding="utf-8")
    sortie.with_name("profil-optimise-cumulative.txt").write_text(tampon.getvalue(), encoding="utf-8")
    print(tampon.getvalue()[:5000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
