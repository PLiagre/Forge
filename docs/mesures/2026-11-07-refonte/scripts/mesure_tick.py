"""Le tick avec et sans IA, et le profil du tick avec IA.

Depuis jeu/ :

    py ../docs/mesures/2026-11-07-refonte/scripts/mesure_tick.py \
        --sortie ../docs/mesures/2026-11-07-refonte/brut/tick.json

Graine 0. Chaque monde joue `--chauffe` ticks (avec l'IA pour le monde avec
IA), puis on chronomètre `--n` ticks un à un (`time.perf_counter`) : la
décision de l'IA (`jouer_ia`) et le tick (`engine.tick`) séparément. On rend
la médiane, le minimum et le maximum. Le profil (`cProfile`) couvre ensuite
`--n-profil` ticks avec IA, sur le même monde.
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

from sim import engine  # noqa: E402
from sim.ia import jouer_ia  # noqa: E402
from sim.world import World  # noqa: E402
try:  # la liste des maisons de l'IA, calculée une fois par la boucle (après la refonte)
    from sim.capitales import toutes_les_maisons_de_l_ia  # noqa: E402
except ImportError:  # le dépôt d'avant : jouer_ia refait la liste à chaque tick
    toutes_les_maisons_de_l_ia = None
try:  # le mois des jauges, joué par la boucle avant l'IA (après la refonte, le pays et ses jauges)
    from sim.jauges import avant_le_tick  # noqa: E402
except ImportError:  # le dépôt d'avant : pas de jauges
    def avant_le_tick(monde):
        return None


def _liste(monde):
    """Les arguments de plus de jouer_ia : la liste des maisons, si le dépôt la connaît."""
    if toutes_les_maisons_de_l_ia is None:
        return ()
    if getattr(monde, '_liste_mesure', None) is None:
        monde._liste_mesure = toutes_les_maisons_de_l_ia(monde)
    return (monde._liste_mesure,)


def serie(ia: bool, chauffe: int, n: int, seed: int):
    monde = World.charger(rng_seed=seed)
    rng = random.Random(seed)
    gestes: list = []
    for _ in range(chauffe):
        avant_le_tick(monde)
        if ia:
            jouer_ia(monde, gestes, *_liste(monde))
        engine.tick(monde, rng, monde.ticks_ecoules)
    t_ia, t_tick, t_total = [], [], []
    for _ in range(n):
        a = time.perf_counter()
        avant_le_tick(monde)  # compté avec la décision de l'IA : hors du tick
        if ia:
            jouer_ia(monde, gestes, *_liste(monde))
        b = time.perf_counter()
        engine.tick(monde, rng, monde.ticks_ecoules)
        c = time.perf_counter()
        t_ia.append((b - a) * 1000)
        t_tick.append((c - b) * 1000)
        t_total.append((c - a) * 1000)

    def resume(xs):
        return {"mediane_ms": round(statistics.median(xs), 2),
                "min_ms": round(min(xs), 2), "max_ms": round(max(xs), 2)}

    return monde, rng, gestes, {"ticks_mesures": [chauffe, chauffe + n - 1],
                                "jouer_ia": resume(t_ia), "tick": resume(t_tick),
                                "total": resume(t_total)}


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--chauffe", type=int, default=30)
    p.add_argument("--n", type=int, default=60)
    p.add_argument("--n-profil", type=int, default=30)
    p.add_argument("--sortie", required=True)
    a = p.parse_args(argv)
    _, _, _, sans = serie(False, a.chauffe, a.n, a.seed)
    print("sans IA", sans, flush=True)
    monde, rng, gestes, avec = serie(True, a.chauffe, a.n, a.seed)
    print("avec IA", avec, flush=True)
    profil = cProfile.Profile()
    profil.enable()
    for _ in range(a.n_profil):
        avant_le_tick(monde)
        jouer_ia(monde, gestes, *_liste(monde))
        engine.tick(monde, rng, monde.ticks_ecoules)
    profil.disable()
    textes = {}
    for cle in ("tottime", "cumulative"):
        tampon = io.StringIO()
        pstats.Stats(profil, stream=tampon).sort_stats(cle).print_stats(30)
        textes[cle] = tampon.getvalue()
    sortie = Path(a.sortie)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(json.dumps({"seed": a.seed, "sans_ia": sans, "avec_ia": avec,
                                  "profil_ticks": [monde.ticks_ecoules - a.n_profil,
                                                   monde.ticks_ecoules - 1]},
                                 ensure_ascii=False, indent=1), encoding="utf-8")
    for cle, texte in textes.items():
        sortie.with_name(f"profil-{cle}.txt").write_text(texte, encoding="utf-8")
    print(textes["tottime"][:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
