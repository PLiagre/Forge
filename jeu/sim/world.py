"""
Chargement et représentation du monde simulé.

World.charger() lit la carte figée `data/world-1400.json` — un seul
fichier, produit une fois pour toutes par l'outil carte — et
amorce la population de chaque cellule avec un rng_seed déterministe.
"""

import json
import pathlib
import random

import sim.constants as constantes
from sim.aggregation import PositionCelluleInconnue, charger_positions
from sim.constants import (
    FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK,
    INITIAL_FOOD_RESERVE_TICKS,
    MARCHANDISE_NOURRITURE,
    PART_SOUTENABLE_AMORCEE,
    SEED_POPULATION_VARIATION_HIGH,
    SEED_POPULATION_VARIATION_LOW,
    date_de_tick,
)
from sim.model import Cell, cellule_vers_dict, ecrire_stock_marchandise
from sim.lieux import amorcer_lieux
from sim.pluie import (
    charger_latitude_moyenne_pluie,
    charger_releves,
    pluie_par_cellule,
)
from sim.villes import attribuer_villes, charger_villes

# Racine du dépôt : deux niveaux au-dessus du paquet sim/
_REPO_ROOT = pathlib.Path(__file__).parent.parent

# La carte figée est la seule entrée géographique du jeu.
CARTE_RELATIVE = "data/world-1400.json"
CARTE_PATH = _REPO_ROOT / "data" / "world-1400.json"


def _seed_population(soutenable: float, rng: random.Random) -> int:
    """
    Amorçage de la population d'une cellule, dérivé de ce qu'elle produit.

    `soutenable` vient de `sim.engine.population_soutenable_de` : le nombre
    d'habitants que la cellule nourrit au rendement moyen, saison comprise.
    Le monde en amorce une part (PART_SOUTENABLE_AMORCEE), pour garder la
    marge que les ticks sous la moyenne consomment.

    Ce que cette fonction ne fait plus : appliquer une densité plate au
    kilomètre carré sans regarder la terre. Voir sim/MODELE.md § « Population
    initiale par cellule ».
    """
    base = soutenable * PART_SOUTENABLE_AMORCEE
    variation = rng.uniform(SEED_POPULATION_VARIATION_LOW, SEED_POPULATION_VARIATION_HIGH)
    return max(0, int(base * variation))


def _seed_food_stock(population: int) -> float:
    """Stock alimentaire initial : INITIAL_FOOD_RESERVE_TICKS ticks de consommation."""
    tick_need = population * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    return tick_need * INITIAL_FOOD_RESERVE_TICKS


def lire_stock_mer(world: "World", marchandise: str) -> float:
    """
    Lit le stock d'une marchandise dans le bassin maritime.

    Absent du bassin : sentinelle -1.0 (jamais confondu avec zéro réel).
    """
    stocks_mer = getattr(world, "stocks_mer", None)
    if stocks_mer is None or marchandise not in stocks_mer:
        return -1.0
    return stocks_mer[marchandise]


def ecrire_stock_mer(world: "World", marchandise: str, quantite_kg: float) -> None:
    """Écrit le stock d'une marchandise dans le bassin maritime."""
    world.stocks_mer[marchandise] = quantite_kg


class World:
    """
    Représentation complète du monde simulé à un instant donné.

    Attributs :
        cells      : dict cell_id → Cell (l'état que le moteur fait évoluer)
        adjacency  : liste des arêtes d'adjacence entre cellules
        carte      : dict cell_id → enregistrement de la carte lue
                     (géométrie, centroïde, relief, climat, gisements, pluie).
                     Donnée de terrain, en lecture seule : le moteur ne la
                     modifie jamais.
        carte_meta : l'en-tête de la carte (version, projection, versions
                     du pipeline qui l'a produite).
        stocks_mer : panier de marchandises du bassin maritime commun.
        attribution_villes : résultat initial des points historiques, y
                     compris ceux hors carte ; le tick ne le consulte pas.
    """

    def __init__(self, cells: dict, adjacency: list,
                 carte: dict | None = None, carte_meta: dict | None = None,
                 attribution_villes=None):
        self.cells = cells
        self.adjacency = adjacency
        self.carte = carte or {}
        self.carte_meta = carte_meta or {}
        self.stocks_mer: dict[str, float] = {}
        self.attribution_villes = attribution_villes
        self.ticks_ecoules = 0

    @property
    def date_simulation(self) -> dict[str, int]:
        """Date dérivée du compteur ; une nouvelle valeur à chaque lecture."""
        return date_de_tick(self.ticks_ecoules)

    @classmethod
    def lire_carte(cls) -> dict:
        """La carte figée enrichie en mémoire de la pluie de chaque cellule."""
        if not CARTE_PATH.is_file():
            raise FileNotFoundError(
                f"Carte du monde introuvable : {CARTE_PATH}. "
                "Elle est versionnée : la récupérer avec "
                "`git checkout -- data/world-1400.json`."
            )
        document = json.loads(CARTE_PATH.read_text(encoding="utf-8"))
        pluies = pluie_par_cellule(
            charger_positions(),
            charger_releves(),
            charger_latitude_moyenne_pluie(),
        )
        pluie_par_id = {pluie.cell_id: pluie.mm_par_an for pluie in pluies}
        for enregistrement in document["cellules"]:
            cell_id = enregistrement["cell_id"]
            if cell_id not in pluie_par_id:
                raise PositionCelluleInconnue(
                    f"pluie absente pour cell_id={cell_id}"
                )
            enregistrement["pluie_mm_par_an"] = pluie_par_id[cell_id]
        return document

    @classmethod
    def charger(cls, rng_seed: int = 0, carte_doc: dict | None = None) -> "World":
        """
        Amorce le monde à partir de la carte figée.

        Le nombre de cellules est dérivé du fichier — jamais codé en dur.

        `carte_doc` permet d'amorcer depuis une carte déjà en mémoire au lieu
        du disque. Sert aux sondes qui demandent « le moteur lit-il cette
        couche ? » : altérer la carte APRÈS le chargement ne prouverait rien
        d'un moteur qui la lit AU chargement. Aucun appelant du jeu ne s'en
        sert ; le comportement par défaut est inchangé.
        """
        rng = random.Random(rng_seed)

        if carte_doc is None:
            carte_doc = cls.lire_carte()

        raw_cells = carte_doc["cellules"]
        raw_adjacency = carte_doc["adjacence"]
        carte = {int(raw["cell_id"]): raw for raw in raw_cells}
        carte_meta = {cle: valeur for cle, valeur in carte_doc.items()
                      if cle not in ("cellules", "adjacence")}
        attribution = attribuer_villes(carte_doc, charger_villes())
        populations_villes = {}
        for ville in attribution.entrees:
            cid = attribution.placees.get(ville.nom)
            if cid is not None:
                populations_villes[cid] = populations_villes.get(cid, 0) + ville.population

        # L'amorçage se fait en deux temps, et l'ordre porte : la population
        # d'une cellule se dérive de ce que cette cellule produit, et la
        # production se lit sur une cellule. On construit donc la cellule
        # vide, on lui demande ce qu'elle nourrit, puis on la peuple.
        from sim.engine import population_soutenable_de

        cells: dict = {}
        for raw in raw_cells:
            cid = raw["cell_id"]
            area = raw["area_km2"]
            cellule_vide = Cell(
                cell_id=cid, area_km2=area, population=0,
                stocks={}, hunger_ticks=0, food_deficit_kg=0.0,
                mortality_remainder=0.0, natalite_remainder=0.0,
                migration_remainder=0.0,
            )
            soutenable = population_soutenable_de(cellule_vide, carte)
            pop_rurale = _seed_population(soutenable, rng)
            pop = max(pop_rurale, populations_villes.get(cid, 0))
            stock = _seed_food_stock(pop)
            if cid in populations_villes:
                manque_kg = max(0.0, pop - soutenable) * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
                stock = round(stock + manque_kg * constantes.RESERVE_VILLES_TICKS,
                              constantes.SNAPSHOT_FLOAT_DECIMALS)
            cell = Cell(
                cell_id=cid,
                area_km2=area,
                population=pop,
                stocks={},
                hunger_ticks=0,
                food_deficit_kg=0.0,
                # Monde amorcé : aucune fraction de mort en attente.
                # La sentinelle -1.0 signifie « non calculé », jamais « nul ».
                mortality_remainder=0.0,
                # Monde amorcé : aucune fraction de naissance en attente.
                natalite_remainder=0.0,
                migration_remainder=0.0,
            )
            ecrire_stock_marchandise(cell, MARCHANDISE_NOURRITURE, stock)
            cell.lieux = amorcer_lieux(cell)
            cells[cid] = cell

        return cls(cells=cells, adjacency=raw_adjacency,
                   carte=carte, carte_meta=carte_meta,
                   attribution_villes=attribution)

    def to_dict(self) -> dict:
        """
        Sérialisation canonique pour calcul d'empreinte SHA256.
        Les clés sont triées pour garantir le déterminisme.
        """
        return {
            "cells": {
                str(cid): cellule_vers_dict(c)
                for cid, c in sorted(self.cells.items())
            },
            "ticks_ecoules": self.ticks_ecoules,
        }
