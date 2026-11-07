"""Le monde sans joueur, graine 0, IA active : population et table du jalon 2.

Depuis jeu/ :

    py ../docs/mesures/2026-11-07-refonte/scripts/mesure_monde.py \
        --ticks 3650 --jalons 90,365,3650 \
        --sortie ../docs/mesures/2026-11-07-refonte/brut/monde-ia.json

La boucle est celle de `python -m sim --ia` (sim/__main__.py, `_simulate`) :
l'IA dépose avant chaque tick, puis `tick(monde, rng, monde.ticks_ecoules)`.
Les morts de faim se comptent en enveloppant `engine._apply_mortality`, sans
rien changer à ce qu'il fait. L'empreinte est le sha256 du monde en JSON
canonique (`World.to_dict()`, clés triées), comme `--monde-json`.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from sim import engine  # noqa: E402
from sim.ia import jouer_ia, maisons_actives_30j  # noqa: E402
from sim.puissances import puissances_depuis_monde  # noqa: E402
from sim.world import World  # noqa: E402
from sim.tests.test_epreuve_jalon2 import (  # noqa: E402
    densite_region, epreuve, lire_reference, placer,
)

VILLES = ["Paris", "Milan", "Florence", "Gand", "Bruges", "Le Caire",
          "Constantinople", "Londres"]


def empreinte(monde) -> str:
    texte = json.dumps(monde.to_dict(), sort_keys=True, ensure_ascii=False,
                       separators=(",", ":"))
    return hashlib.sha256(texte.encode("utf-8")).hexdigest()


def cellules_de_la_reference(monde, reference) -> dict[int, list[str]]:
    """Chaque cellule que la table du jalon 2 place, avec les noms qui y tombent."""
    noms: dict[int, list[str]] = {}
    for bloc in ("points_connus", "points", "declares"):
        for point in reference[bloc]:
            cid = placer(monde, point)
            if cid is not None:
                noms.setdefault(cid, []).append(point["nom"])
    for bloc in ("regions_denses", "regions_vides"):
        for region in reference[bloc]:
            for nom, lat, lon in region["points"]:
                cid = placer(monde, {"nom": nom, "lat": lat, "lon": lon})
                if cid is not None:
                    noms.setdefault(cid, []).append(f"{region['nom']}/{nom}")
    return noms


def releve(monde, depart, morts, ref_cellules, reference, gestes, t0):
    villes = {}
    for nom, cid in sorted(monde.attribution_villes.placees.items()):
        if nom not in VILLES:
            continue
        cell = monde.cells[cid]
        bourg = next(l for l in cell.lieux if l.rang == 0)
        villes[nom] = {
            "cell_id": cid,
            "cellule": cell.population,
            "cellule_depart": depart["cellules"][cid],
            "part_cellule": round(cell.population / depart["cellules"][cid], 4),
            "bourg": bourg.population,
            "bourg_depart": depart["bourgs"][cid],
            "part_bourg": round(bourg.population / depart["bourgs"][cid], 4)
            if depart["bourgs"][cid] else -1,
            "morts_de_faim": morts.get(cid, 0),
        }
    europe = sum(c.population for c in monde.cells.values())
    regions = {}
    for bloc in ("regions_denses", "regions_vides"):
        for region in reference[bloc]:
            densite, cellules = densite_region(monde, region)
            regions[region["nom"]] = {"bloc": bloc, "densite": round(densite, 3),
                                      "cellules": cellules}
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        echecs = epreuve(monde, puissances_depuis_monde(monde), reference)
    mediane = next((l for l in tampon.getvalue().splitlines()
                    if l.startswith("médiane")), "")
    faim = []
    for cid, noms in sorted(ref_cellules.items()):
        pop0 = depart["cellules"][cid]
        m = morts.get(cid, 0)
        faim.append({"cell_id": cid, "noms": noms, "depart": pop0,
                     "maintenant": monde.cells[cid].population,
                     "morts_de_faim": m,
                     "part_morte_de_faim": round(m / pop0, 4) if pop0 else -1})
    plus_de_moitie = [f for f in faim if f["part_morte_de_faim"] > 0.5]
    par_type: dict[str, int] = {}
    maisons_annee: set = set()
    annee_t = monde.ticks_ecoules - 365
    refus = 0
    for e in gestes:
        if "refus" in e:
            refus += 1
            continue
        par_type[e["intention"]["type"]] = par_type.get(e["intention"]["type"], 0) + 1
        if e["tick"] >= annee_t:
            maisons_annee.add((e["maison"]["sorte"], e["maison"]["id"]))
    return {
        "tick": monde.ticks_ecoules,
        "date": monde.date_simulation,
        "secondes_ecoulees": round(time.perf_counter() - t0, 1),
        "europe": europe,
        "europe_depart": depart["europe"],
        "part_europe": round(europe / depart["europe"], 4),
        "villes": villes,
        "jalon2": {"mediane": mediane, "regions": regions, "echecs": echecs},
        "faim_table": {"cellules": len(faim),
                       "plus_de_moitie_morte_de_faim": plus_de_moitie,
                       "pire": max(faim, key=lambda f: f["part_morte_de_faim"])},
        "ia": {"gestes_acceptes_par_type": par_type, "refus": refus,
               "maisons_actives_30j": maisons_actives_30j(monde.ticks_ecoules, gestes),
               "maisons_avec_un_geste_sur_365j": len(maisons_annee)},
        "empreinte": empreinte(monde),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--ticks", type=int, default=3650)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--jalons", default="90,365,3650")
    p.add_argument("--sans-ia", action="store_true")
    p.add_argument("--sortie", required=True)
    a = p.parse_args(argv)
    jalons = sorted({int(x) for x in a.jalons.split(",")})
    t0 = time.perf_counter()
    monde = World.charger(rng_seed=a.seed)
    rng = random.Random(a.seed)
    reference = lire_reference()
    ref_cellules = cellules_de_la_reference(monde, reference)
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
    sortie = Path(a.sortie)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    resultat = {"seed": a.seed, "ia": not a.sans_ia, "jalons": [],
                "commande": " ".join(sys.argv)}
    for _ in range(a.ticks):
        if not a.sans_ia:
            jouer_ia(monde, gestes)
        engine.tick(monde, rng, monde.ticks_ecoules)
        if monde.ticks_ecoules in jalons:
            r = releve(monde, depart, morts, ref_cellules, reference, gestes, t0)
            resultat["jalons"].append(r)
            sortie.write_text(json.dumps(resultat, ensure_ascii=False, indent=1),
                              encoding="utf-8")
            v = r["villes"]
            print(f"t={r['tick']} europe={r['part_europe']:.3f} "
                  + " ".join(f"{n}={v[n]['part_cellule']:.3f}" for n in VILLES if n in v)
                  + f" echecs={len(r['jalon2']['echecs'])} "
                  f"faim>50%={len(r['faim_table']['plus_de_moitie_morte_de_faim'])} "
                  f"({r['secondes_ecoulees']} s)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
