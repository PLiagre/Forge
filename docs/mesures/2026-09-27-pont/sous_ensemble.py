"""Mesure jetable : ce que coûte le tick en Python, morceau par morceau, et
ce que pèse ce qu'Unity aurait à lire. Écrit aussi les entrées du portage C#
du sous-ensemble « par cellule » (production, consommation, faim, mort,
naissances), pour comparer à langage égal.

    py sous_ensemble.py --racine D:/Forge --sortie mesures-python.json
"""
from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import sys
import tempfile
import time

parser = argparse.ArgumentParser()
parser.add_argument("--racine", required=True)
parser.add_argument("--sortie", required=True)
parser.add_argument("--entrees-cs", required=True)
args = parser.parse_args()
sys.path.insert(0, args.racine)

from sim import constants as C  # noqa: E402
from sim import engine as E  # noqa: E402
from sim.model import cellule_vers_dict  # noqa: E402
from sim.snapshot_export import build_snapshot_document, serialize_snapshot  # noqa: E402
from sim.world import World  # noqa: E402


def mediane_ms(durees):
    return round(statistics.median(durees) * 1000, 3)


res = {}
t = time.perf_counter()
monde = World.charger(0)
res["chargement_monde_ms"] = round((time.perf_counter() - t) * 1000, 1)
rng = random.Random(0)
for _ in range(10):
    E.tick(monde, rng, monde.ticks_ecoules)

# 1. le tick entier
durees = []
for _ in range(40):
    t = time.perf_counter()
    E.tick(monde, rng, monde.ticks_ecoules)
    durees.append(time.perf_counter() - t)
res["tick_complet_ms"] = mediane_ms(durees)
res["annee_s"] = round(statistics.median(durees) * C.CALENDAR_DAYS_PER_YEAR, 1)
res["partie_1400_1900_h"] = round(statistics.median(durees) * C.CALENDAR_DAYS_PER_YEAR * 500 / 3600, 2)

# 2. le commerce seul (88 % du tick au profilage)
durees = []
for _ in range(20):
    t = time.perf_counter()
    E._apply_commerce(monde, [0.0])
    durees.append(time.perf_counter() - t)
res["commerce_ms"] = mediane_ms(durees)

# 3. le sous-ensemble par cellule, avec les vraies fonctions du moteur
carte = monde.carte
cellules = list(monde.cells.values())
entrees = []
for c in cellules:
    ete, hiver = E._lire_solstices(c, carte)
    entrees.append({
        "id": c.cell_id, "aire": c.area_km2,
        "relief": E._facteur_relief_pour_cellule(c, carte),
        "agricole": E._facteur_agricole(c, carte),
        "ete": ete, "hiver": hiver, "pop": c.population,
        "stock": max(0.0, c.food_stock_kg), "dette": max(0.0, c.food_deficit_kg),
    })
constantes = {
    "prod": C.FOOD_PRODUCTION_KG_PER_KM2_PER_TICK, "rdt_bas": C.RNG_YIELD_LOW, "rdt_haut": C.RNG_YIELD_HIGH,
    "ration": C.FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK, "rembourse": C.DEFICIT_RECOVERY_RATE_PER_SURPLUS_KG,
    "echelle_mort": C.HUNGER_DEATH_SCALE, "mort_max": C.MAX_DEATH_RATE_PER_TICK,
    "naissances": C.naissances_par_habitant_par_tick(), "equinoxe": C.DUREE_JOUR_EQUINOXE_H,
    "sensibilite": C.SENSIBILITE_SAISON, "solstice": C.JOUR_SOLSTICE_ETE, "annee": C.CALENDAR_DAYS_PER_YEAR,
}
with open(args.entrees_cs, "w", encoding="utf-8") as f:
    json.dump({"constantes": constantes, "cellules": entrees}, f)

durees = []
for i in range(200):
    jour = C.jour_de_tick(monde.ticks_ecoules + i)
    t = time.perf_counter()
    for c in cellules:
        E._apply_production(c, rng, carte, jour=jour)
        p = E._apply_consumption(c)
        E._update_hunger(c, p)
        E._apply_mortality(c)
        E._apply_natalite(c, p)
    durees.append(time.perf_counter() - t)
res["sous_ensemble_par_cellule_ms"] = mediane_ms(durees)
res["cellules"] = len(cellules)

# 4. ce qu'Unity aurait à lire
un_lieu = cellule_vers_dict(cellules[0])
res["octets_un_lieu"] = len(json.dumps(un_lieu).encode())
t = time.perf_counter()
leger = json.dumps({"tick": monde.ticks_ecoules, "cells": [cellule_vers_dict(c) for c in cellules]}).encode()
res["etat_leger_serialisation_ms"] = round((time.perf_counter() - t) * 1000, 2)
res["etat_leger_octets"] = len(leger)
t = time.perf_counter()
doc = build_snapshot_document(monde, 0, monde.ticks_ecoules)
octets = serialize_snapshot(doc)
res["photographie_complete_ms"] = round((time.perf_counter() - t) * 1000, 1)
res["photographie_complete_octets"] = len(octets)

# 5. le pont par fichiers : écrire l'état léger, le relire
dossier = tempfile.mkdtemp()
chemin = os.path.join(dossier, "etat.json")
durees = []
for _ in range(50):
    t = time.perf_counter()
    with open(chemin + ".tmp", "wb") as f:
        f.write(leger)
    os.replace(chemin + ".tmp", chemin)
    with open(chemin, "rb") as f:
        json.loads(f.read())
    durees.append(time.perf_counter() - t)
res["fichier_ecrire_relire_etat_leger_ms"] = mediane_ms(durees)

with open(args.sortie, "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False))
