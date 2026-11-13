"""Rejoue la première année de 1400 sous quatre réglages de l'appel des villes affamées (lot #1071).

Graine 0, l'IA active, aucun geste du joueur, 365 jours : à chaque jour `jouer_ia`
puis `engine.tick`, comme l'épreuve de la soudure. Les quatre réglages (P est
`appel_ville_affamee_part`, R est `rayon_ville_affamee_jours`) :

    avant   P = 0, R = 1      le commerce d'avant le lot
    rayon   P = 0, R = 6      le rayon seul
    appel   P = 1, R = 1      l'appel seul
    depot   les données du dépôt (`jeu/data/commerce.toml`)

Pour chacun, par ville : habitants et grain au 365e jour, morts de faim
(`engine._apply_mortality`), pertes nettes au pas des départs, et le grain reçu
par le commerce. Puis la pire cellule de `sim/tests/test_soudure.py` : la part
de ses habitants morts de faim (le test exige moins de la moitié).

Se lance depuis n'importe où ; sans argument, joue les quatre réglages :

    python3 docs/mesures/2026-11-12-grain-vers-les-villes/scripts/mesure_un_an.py [avant rayon appel depot]
"""
import copy
import random
import sys
from pathlib import Path

JEU = Path(__file__).resolve().parents[4] / "jeu"
sys.path.insert(0, str(JEU))

import sim.constants as constantes  # noqa: E402
from sim import departs, engine  # noqa: E402
from sim.capitales import toutes_les_maisons_de_l_ia  # noqa: E402
from sim.ia import jouer_ia  # noqa: E402
from sim.model import lire_stock_marchandise  # noqa: E402
from sim.tests.test_soudure import _cellules_de_la_table  # noqa: E402
from sim.world import World  # noqa: E402

JOURS = 365
VILLES = ("Paris", "Milan", "Gand", "Alexandrie", "Le Caire")
REGLAGES = {"avant": (0, 1), "rayon": (0, 6), "appel": (1, 1), "depot": None}


def _jouer(depart, reglage):
    """Joue un an sous `reglage` ; rend (monde, cellules suivies, morts, pertes, reçu)."""
    monde = copy.deepcopy(depart)
    nourriture = constantes.MARCHANDISE_NOURRITURE
    suivies = {nom: monde.attribution_villes.placees[nom] for nom in VILLES}
    table = _cellules_de_la_table(monde)
    cids = set(suivies.values()) | set(table)
    morts = dict.fromkeys(cids, 0)
    pertes = dict.fromkeys(cids, 0)
    recu = dict.fromkeys(cids, 0.0)
    origines = (constantes.appel_ville_affamee_part, constantes.rayon_ville_affamee_jours,
                engine._apply_mortality, departs.appliquer_departs, engine._apply_commerce)
    profondeur = [0]

    def mortalite(cellule, *facteurs):
        avant = cellule.population
        origines[2](cellule, *facteurs)
        if cellule.cell_id in morts:
            morts[cellule.cell_id] += avant - cellule.population

    def pas_des_departs(monde_joue):
        avant = {cid: monde_joue.cells[cid].population for cid in pertes}
        retour = origines[3](monde_joue)
        for cid, population in avant.items():
            pertes[cid] += max(0, population - monde_joue.cells[cid].population)
        return retour

    def commerce(monde_joue, total, *args, **kwargs):
        if profondeur[0]:
            return origines[4](monde_joue, total, *args, **kwargs)
        avant = {cid: lire_stock_marchandise(monde_joue.cells[cid], nourriture) for cid in recu}
        profondeur[0] += 1
        try:
            origines[4](monde_joue, total, *args, **kwargs)
        finally:
            profondeur[0] -= 1
        for cid, stock in avant.items():
            recu[cid] += max(0.0, lire_stock_marchandise(monde_joue.cells[cid], nourriture) - stock)

    try:
        if REGLAGES[reglage] is not None:
            part, rayon = REGLAGES[reglage]
            constantes.appel_ville_affamee_part = lambda chemin=None: part
            constantes.rayon_ville_affamee_jours = lambda chemin=None: rayon
        engine._apply_mortality = mortalite
        departs.appliquer_departs = pas_des_departs
        engine._apply_commerce = commerce
        rng, releve = random.Random(0), []
        maisons = toutes_les_maisons_de_l_ia(monde)
        for _ in range(JOURS):
            jouer_ia(monde, releve, maisons)
            engine.tick(monde, rng, monde.ticks_ecoules)
    finally:
        (constantes.appel_ville_affamee_part, constantes.rayon_ville_affamee_jours,
         engine._apply_mortality, departs.appliquer_departs, engine._apply_commerce) = origines
    return monde, suivies, table, morts, pertes, recu


def main(noms):
    depart = World.charger(0)
    nourriture = constantes.MARCHANDISE_NOURRITURE
    habitants_au_depart = {cid: cell.population for cid, cell in depart.cells.items()}
    print(f"données du dépôt : P = {constantes.appel_ville_affamee_part()}, R = {constantes.rayon_ville_affamee_jours()}")
    for reglage in noms:
        monde, suivies, table, morts, pertes, recu = _jouer(depart, reglage)
        part, rayon = REGLAGES[reglage] or (constantes.appel_ville_affamee_part(), constantes.rayon_ville_affamee_jours())
        print(f"\n== {reglage} : P = {part}, R = {rayon}, {JOURS} jours ==")
        print(f"{'ville':12s} {'départ':>9s} {'habitants':>10s} {'grain (t)':>10s} {'morts':>9s} {'pertes':>9s} {'reçu (t)':>10s}")
        for nom, cid in suivies.items():
            cellule = monde.cells[cid]
            print(f"{nom:12s} {habitants_au_depart[cid]:9d} {cellule.population:10d} "
                  f"{lire_stock_marchandise(cellule, nourriture) / 1000:10.0f} {morts[cid]:9d} {pertes[cid]:9d} "
                  f"{recu[cid] / 1000:10.0f}")
        pire = max(table, key=lambda cid: morts[cid] / habitants_au_depart[cid])
        print(f"pire cellule de test_soudure.py : {table[pire][0]} (cellule {pire}), "
              f"{morts[pire] / habitants_au_depart[pire]:.4f} de ses habitants morts de faim "
              f"({morts[pire]} sur {habitants_au_depart[pire]}) ; seuil 0,5")
        sys.stdout.flush()


if __name__ == "__main__":
    demandes = sys.argv[1:] or list(REGLAGES)
    inconnus = [nom for nom in demandes if nom not in REGLAGES]
    if inconnus:
        sys.exit(f"réglage inconnu : {inconnus} ; attendus : {list(REGLAGES)}")
    main(demandes)
