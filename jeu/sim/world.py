"""
Chargement et représentation du monde simulé.

World.charger() lit la carte figée `data/world-1400.json` — un seul
fichier, produit une fois pour toutes par l'outil carte — et
amorce la population de chaque cellule avec un rng_seed déterministe.
"""

import dataclasses
import json
import pathlib
import random

import sim.constants as constantes
from sim import foyers
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
from sim.fleuve import (
    cellules_traversees,
    charger_latitude_moyenne_fleuve,
    charger_points,
)
from sim.model import Cell, cellule_vers_dict, ecrire_stock_marchandise, ecrire_maitre
from sim.lieux import amorcer_lieux
from sim.plan import Plan
from sim.pluie import (
    charger_latitude_moyenne_pluie,
    charger_releves,
    pluie_par_cellule,
)
from sim.registre_maisons import charger_registre_maisons
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
        populations_bourg_amorcage : population du lieu de rang 0 juste après
                     l'amorçage, par cellule. Hors de to_dict, jamais lue par
                     le tick. None si le monde n'a pas été amorcé : la ville
                     de 1400 se déclare alors absente, elle ne se devine pas.
        ancres_des_bourgs : cell_id → (siège du maître du bourg ou None,
                     ville placée ou None). Posé au chargement, hors de
                     to_dict. None si le monde est construit à la main :
                     une route intérieure se déclare alors sans ancre.
        plans      : dict cell_id → Plan du bourg (rang 0), chantiers lus au tick.
        intentions_en_attente : choix validés, invisibles avant le tick suivant.
        maison_du_joueur : identifiant de la maison du registre appliquée, ou None sans choix.
        maisons    : tuple initial de fiches gelées, jamais consulté au tick.
        greniers   : identifiant de maison → panier (marchandise → kg), vide au chargement.
        parts      : identifiant de maison → fraction commune à ses lieux.
        pertes_kg  : cumul des kilogrammes retirés des greniers, 0 tant qu'aucune perte.
        routes_des_lieux : (cell_id, rang) → route jusqu'au siège du maître.
                     Calculée une fois au chargement, absente de to_dict,
                     lue par le prélèvement. {} pour un monde construit à la main.
        dus_des_vassaux : routes vers les suzerains, retenues hors carte et index dense,
                     calculés au chargement, hors de to_dict ; table vide en épreuve.
        convois : groupes d’arrivée, facteur commun et charges par maison.
        secours : arrivée → charges courantes par lieu (cell_id, rang).
        mange_convois_kg : kilos consommés en route, cumul sans arrondi.
    """

    def __init__(self, cells: dict, adjacency: list,
                 carte: dict | None = None, carte_meta: dict | None = None,
                 attribution_villes=None):
        self.cells = cells
        self.plans = {cid: Plan() for cid in sorted(cells)}
        self.adjacency = adjacency
        self.carte = carte or {}
        self.carte_meta = carte_meta or {}
        self.stocks_mer: dict[str, float] = {}
        self.attribution_villes = attribution_villes
        self.populations_bourg_amorcage = None
        self.ancres_des_bourgs = None
        self.ticks_ecoules = 0
        self.intentions_en_attente = []
        self.maison_du_joueur = None
        self.maisons = ()
        self.greniers = {}
        self.parts = {}
        self.pertes_kg = 0.0
        self.routes_des_lieux = {}
        from sim.convois import TableDus
        self.dus_des_vassaux = TableDus()
        self.convois = {}
        self.secours = {}
        self.mange_convois_kg = 0.0

    @property
    def date_simulation(self) -> dict[str, int]:
        """Date dérivée du compteur ; une nouvelle valeur à chaque lecture."""
        return date_de_tick(self.ticks_ecoules)

    @classmethod
    def lire_carte(cls) -> dict:
        """La carte figée enrichie en mémoire de la pluie et de la crue."""
        if not CARTE_PATH.is_file():
            raise FileNotFoundError(
                f"Carte du monde introuvable : {CARTE_PATH}. "
                "Elle est versionnée : la récupérer avec "
                "`git checkout -- data/world-1400.json`."
            )
        document = json.loads(CARTE_PATH.read_text(encoding="utf-8"))
        positions = charger_positions()
        pluies = pluie_par_cellule(
            positions,
            charger_releves(),
            charger_latitude_moyenne_pluie(),
        )
        pluie_par_id = {pluie.cell_id: pluie.mm_par_an for pluie in pluies}
        traversees = {
            cellule.cell_id
            for cellule in cellules_traversees(
                charger_points(),
                positions,
                charger_latitude_moyenne_fleuve(),
            )
        }
        for enregistrement in document["cellules"]:
            cell_id = enregistrement["cell_id"]
            if cell_id not in pluie_par_id:
                raise PositionCelluleInconnue(
                    f"pluie absente pour cell_id={cell_id}"
                )
            enregistrement["pluie_mm_par_an"] = pluie_par_id[cell_id]
            enregistrement["crue_mm_par_an"] = (
                constantes.CRUE_EQUIVALENT_PLUIE_MM
                if cell_id in traversees
                else 0.0
            )
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
        populations_bourg_amorcage = {}
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
            metiers = foyers.metiers_d_amorcage(pop, raw.get("gisements") or [])
            stock = _seed_food_stock(pop)
            if cid in populations_villes:
                manque_kg = max(0.0, pop - soutenable) * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
                stock = round(stock + manque_kg * constantes.RESERVE_VILLES_TICKS,
                              constantes.SNAPSHOT_FLOAT_DECIMALS)
            cell = Cell(
                cell_id=cid,
                area_km2=area,
                population=pop,
                habitants_par_metier=metiers,
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
            bourg = cell.lieux[0]
            if bourg.rang != 0:
                raise ValueError(
                    f"cellule {cid} : le lieu de rang 0 manque après l'amorçage"
                )
            populations_bourg_amorcage[cid] = bourg.population
            cells[cid] = cell

        monde = cls(cells=cells, adjacency=raw_adjacency,
                   carte=carte, carte_meta=carte_meta,
                   attribution_villes=attribution)
        monde.populations_bourg_amorcage = populations_bourg_amorcage
        monde.maisons = charger_registre_maisons(monde.carte)
        from sim.maitres import attribuer_maitres

        maitres, plausibles = attribuer_maitres(monde)
        for cid, cellule in monde.cells.items():
            for lieu in cellule.lieux:
                if (cid, lieu.rang) in maitres:
                    ecrire_maitre(lieu, maitres[cid, lieu.rang])
        monde.maisons = tuple(sorted(monde.maisons + plausibles, key=lambda m: m.id))
        # Les fiches plausibles doivent aussi respecter le registre chargé,
        # avant que les routes utilisent leurs références aux suzerains.
        maisons_connues = {maison.id for maison in monde.maisons}
        for maison in monde.maisons:
            if maison.suzerain is not None and maison.suzerain not in maisons_connues:
                raise AssertionError(
                    f"registre chargé : vassal {maison.id}, "
                    f"suzerain {maison.suzerain!r} inconnu"
                )
        # Une fois, après les maîtres : le prélèvement lit cet index sans recalcul.
        from sim.convois import routes_des_lieux, dus_des_vassaux
        from sim.places import places_du_monde

        places = places_du_monde(monde)
        monde.routes_des_lieux = routes_des_lieux(monde, places)
        monde.dus_des_vassaux = dus_des_vassaux(monde, places)
        monde.greniers = {maison.id: {} for maison in monde.maisons}
        monde.parts = {maison.id: constantes.PART_COUTUMIERE for maison in monde.maisons}
        from sim.places import ancres_des_bourgs

        monde.ancres_des_bourgs = ancres_des_bourgs(monde)
        return monde

    def to_dict(self) -> dict:
        """
        Sérialisation canonique pour calcul d'empreinte SHA256.
        Les clés sont triées pour garantir le déterminisme.
        """
        document = {
            "cells": {
                str(cid): cellule_vers_dict(c)
                for cid, c in sorted(self.cells.items())
            },
            "plans": {
                str(cid): plan.to_dict()
                for cid, plan in sorted(self.plans.items())
            },
            "ticks_ecoules": self.ticks_ecoules,
            "maisons": [dataclasses.asdict(maison)
                        for maison in sorted(self.maisons, key=lambda m: m.id)],
        }
        if self.maison_du_joueur is not None:
            document["maison_du_joueur"] = self.maison_du_joueur
        greniers = {
            identifiant: {nom: panier[nom] for nom in sorted(panier)}
            for identifiant, panier in sorted(self.greniers.items())
            if panier
        }
        if greniers:
            document["greniers"] = greniers
        if self.pertes_kg != 0.0:
            document["pertes_kg"] = self.pertes_kg
        parts = {i: p for i, p in sorted(self.parts.items()) if p != constantes.PART_COUTUMIERE}
        if parts:
            document["parts"] = parts
        if self.convois:
            from sim import prelevement
            document["convois"] = prelevement.charges_en_route(self)
        if self.mange_convois_kg:
            document["mange_convois_kg"] = self.mange_convois_kg
        if self.secours:
            document["secours"] = sorted(
                [cid, rang, arrivee, kg]
                for arrivee, charges in self.secours.items()
                for (cid, rang), kg in charges.items()
            )
        return document
