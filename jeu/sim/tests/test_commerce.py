"""
Le commerce est physique : rien ne se téléporte, rien ne nourrit deux fois.

Ce que ce fichier protège :
  - invariant physique : conservation stricte de la masse au transport ;
    les kg transportés sont exactement les kg arrivés ;
  - règle de jeu visible : un kg transféré ne nourrit qu'une fois, ne
    traverse qu'une arête par tick, et un receveur n'est jamais sur-livré ;
  - déterminisme : l'état final ne dépend pas de l'ordre des arêtes.

Fusion des anciens fichiers commerce, kg_transportes_est_arrives et
tick_nourrit_une_fois.
"""


import random
import pytest
from sim.engine import _apply_commerce, _apply_consumption, _apply_production, tick
from sim.model import Cell
from sim.world import World
from sim.constants import (
    FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK,
    MARCHANDISE_NOURRITURE,
    TICK_DURATION_DAYS,
    TRADE_CAPACITY_KG_PER_EDGE_PER_TICK,
)
from sim.engine import _apply_commerce
TOLERANCE = 1e-9
def _run_commerce_ecart(world: World) -> float:
    """Lance _apply_commerce et retourne l'écart entre kg comptés et kg arrivés."""
    stocks_avant = {cid: c.food_stock_kg for cid, c in world.cells.items()}
    total_transported = [0.0]
    _apply_commerce(world, total_transported)

    somme_deltas_positifs = sum(
        max(0.0, world.cells[cid].food_stock_kg - stocks_avant[cid])
        for cid in world.cells
    )
    return total_transported[0], somme_deltas_positifs
from sim.engine import _apply_commerce, tick
def _build_sc1_world(besoin_kg: float) -> tuple[World, int, int]:
    """
    Construit le micro-monde à trois cellules :
    - Cellule 100 (témoin)  : food_stock_kg = besoin_kg, pas d'adjacence.
    - Cellule 101 (source)  : population = 0, food_stock_kg = besoin_kg.
    - Cellule 102 (receveuse): food_stock_kg = 0, food_deficit_kg = besoin_kg.
    Arête : 101 → 102 uniquement.
    Production désactivée : area_km2 = 0.0 sur toutes les cellules.
    Capacité de transport ≥ besoin_kg assurée par le paramètre (200 kg/arête).
    """
    # Nombre de personnes pour que besoin_kg = pop × FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    pop_receveuse = 50  # besoin_kg = 50 × 2 = 100 kg

    temoin = Cell(
        cell_id=100,
        area_km2=0.0,
        population=pop_receveuse,
        food_stock_kg=besoin_kg,
        hunger_ticks=0,
        food_deficit_kg=0.0,
    )
    source = Cell(
        cell_id=101,
        area_km2=0.0,
        population=0,          # pas de consommation propre → surplus = stock
        food_stock_kg=besoin_kg,
        hunger_ticks=0,
        food_deficit_kg=0.0,
    )
    receveuse = Cell(
        cell_id=102,
        area_km2=0.0,
        population=pop_receveuse,
        food_stock_kg=0.0,
        hunger_ticks=0,
        food_deficit_kg=besoin_kg,
    )

    adjacency = [{"a": 101, "b": 102, "kind": "land", "shared_length_m": 5000.0}]
    world = World(
        cells={100: temoin, 101: source, 102: receveuse},
        adjacency=adjacency,
    )
    return world, 100, 102
def _build_chain_world(edge_order: list[dict]) -> World:
    """
    Construit un monde à trois cellules en chaîne.
    - Cellule 1 : source (pop=0, large surplus).
    - Cellule 2 : intermédiaire (pop=100, stock=0, déficit=200).
    - Cellule 3 : terminus (pop=20, stock=0, déficit=200).
      La petite population de la cellule 3 (besoin=40 kg) garantit que si elle
      reçoit 200 kg via multi-saut (ancien comportement), son stock APRÈS
      consommation reste positif (160 kg), rendant l'invariance détectable.
    Production désactivée : area_km2 = 0.0.
    """
    pop_2 = 100
    pop_3 = 20
    besoin_2 = pop_2 * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK   # 200 kg
    deficit_3 = 200.0  # déficit accumulé > besoin courant (40 kg)

    cell_1 = Cell(
        cell_id=1,
        area_km2=0.0,
        population=0,
        food_stock_kg=besoin_2 * 3,  # 600 kg : suffisant pour nourrir cellule 2
        hunger_ticks=0,
        food_deficit_kg=0.0,
    )
    cell_2 = Cell(
        cell_id=2,
        area_km2=0.0,
        population=pop_2,
        food_stock_kg=0.0,
        hunger_ticks=1,
        food_deficit_kg=besoin_2,
    )
    cell_3 = Cell(
        cell_id=3,
        area_km2=0.0,
        population=pop_3,
        food_stock_kg=0.0,
        hunger_ticks=1,
        food_deficit_kg=deficit_3,
    )
    return World(cells={1: cell_1, 2: cell_2, 3: cell_3}, adjacency=edge_order)
def _build_contested_source_world(edge_order: list[dict]) -> World:
    """
    Construit un monde à trois cellules pour le scénario « source contestée ».
    - Cellule 10 (source S) : pop=0, stock=80 → surplus=80.
    - Cellule 11 (receveur A) : pop=50, stock=40 → besoin=60 (50×2-40).
    - Cellule 12 (receveur B) : pop=50, stock=40 → besoin=60.
    Surplus source (80) < somme des besoins (120) : allocation proportionnelle
    attendue → A reçoit 40, B reçoit 40, quel que soit l'ordre des arêtes.
    Sans snapshot (traitement arête-par-arête en direct), le premier receveur
    traité reçoit 60 et le second 20 selon l'ordre → ordre-dépendant.
    Production désactivée : area_km2 = 0.0.
    """
    pop_receveur = 50
    stock_receveur = 40
    source = Cell(
        cell_id=10,
        area_km2=0.0,
        population=0,
        food_stock_kg=80.0,
        hunger_ticks=0,
        food_deficit_kg=0.0,
    )
    recv_a = Cell(
        cell_id=11,
        area_km2=0.0,
        population=pop_receveur,
        food_stock_kg=float(stock_receveur),
        hunger_ticks=1,
        food_deficit_kg=0.0,
    )
    recv_b = Cell(
        cell_id=12,
        area_km2=0.0,
        population=pop_receveur,
        food_stock_kg=float(stock_receveur),
        hunger_ticks=1,
        food_deficit_kg=0.0,
    )
    return World(cells={10: source, 11: recv_a, 12: recv_b}, adjacency=edge_order)


# --- test_commerce.py ---
def test_deficit_accumule_quand_manque():
    """
    food_deficit_kg est écrit (> 0) quand la consommation
    dépasse le stock initial disponible sur un tick complet.

    Cellule construite à la main, area_km2 = 1.0 km² (≥ minimum G3).
    Consommation = population × 2 kg/tick >> stock initial.
    """
    # Cellule avec grand population et petit stock : déficit garanti
    # area_km2 = 1.0 : production max ≈ 1.0 × 18 × 1.5 = 27 kg
    # population = 1000 : consommation = 1000 × 2 = 2000 kg >> stock initial = 10 kg
    cell = Cell(
        cell_id=1,
        area_km2=1.0,
        population=1000,
        food_stock_kg=10.0,
        hunger_ticks=0,
        food_deficit_kg=0.0,
    )
    world = World(cells={1: cell}, adjacency=[])
    rng = random.Random(42)

    tick(world, rng)

    food_deficit_kg_ecrit_quand_manque = world.cells[1].food_deficit_kg > 0
    print(f"food_deficit_kg après tick : {world.cells[1].food_deficit_kg}")
    print(f"food_deficit_kg_ecrit_quand_manque = {food_deficit_kg_ecrit_quand_manque}")

    assert food_deficit_kg_ecrit_quand_manque, (
        f"food_deficit_kg devrait être > 0 après un tick de famine : "
        f"obtenu {world.cells[1].food_deficit_kg}"
    )


# --- test_commerce.py ---
def test_conservation_masse_transport():
    """
    Conservation stricte de la masse lors du commerce.

    Mini-monde de 2 cellules adjacentes :
    - Cellule A : surplus (food_stock_kg > 0, food_deficit_kg = 0)
    - Cellule B : déficit (food_stock_kg = 0, food_deficit_kg > 0)

    Vérifie que sum(food_stock_kg) avant = sum(food_stock_kg) après,
    à 1×10⁻⁹ kg près.

    Conservation : la masse totale ne doit pas changer.
    """
    cell_a = Cell(
        cell_id=1,
        area_km2=10.0,
        population=50,
        food_stock_kg=5000.0,
        hunger_ticks=0,
        food_deficit_kg=0.0,
    )
    cell_b = Cell(
        cell_id=2,
        area_km2=10.0,
        population=200,
        food_stock_kg=0.0,
        hunger_ticks=5,
        food_deficit_kg=300.0,
    )

    # Arête d'adjacence entre A et B (format G3 : champs 'a' et 'b')
    adjacency = [{"a": 1, "b": 2, "kind": "land", "shared_length_m": 10000.0}]
    world = World(cells={1: cell_a, 2: cell_b}, adjacency=adjacency)

    somme_avant = sum(c.food_stock_kg for c in world.cells.values())

    total_transported = [0.0]
    _apply_commerce(world, total_transported)

    somme_apres = sum(c.food_stock_kg for c in world.cells.values())

    ecart = abs(somme_avant - somme_apres)
    tolerance = 1e-9

    conservation_masse_transport = ecart <= tolerance
    print(f"somme_avant = {somme_avant}")
    print(f"somme_apres = {somme_apres}")
    print(f"écart = {ecart}")
    print(f"conservation_masse_transport = {conservation_masse_transport}")
    print(f"kg_transportes = {total_transported[0]}")

    assert conservation_masse_transport, (
        f"La masse n'est pas conservée : avant={somme_avant}, après={somme_apres}, "
        f"écart={ecart} (tolérance={tolerance})"
    )
    assert total_transported[0] > 0, (
        "Aucun kilogramme transporté alors qu'une cellule avait un déficit et "
        "l'autre un surplus."
    )


# --- test_kg_transportes_est_arrives.py ---
def test_kg_transportes_egal_deltas_positifs():
    """
    Topologie chaîne : seul le receveur direct (cellule 2) reçoit
    de la nourriture. La cellule 3 (non adjacente à la source) ne reçoit rien
    via snapshot. total_transported = kg reçus par cellule 2, écart nul.

    Sans le snapshot (ancien comportement 012) : cellule 2 recevrait 200 kg
    (CAPACITY) et en redistribuerait 100 kg à cellule 3 dans le même tick ;
    total_transported compterait 300 kg alors que seuls 200 kg ont quitté une
    source — sur-comptage de 100 kg. Ce test rougirait.

    Monde : cellule 1 (source, pop=0, stock=500), cellule 2 (pop=50, stock=0,
    besoin_snapshot=100), cellule 3 (pop=50, stock=0, besoin_snapshot=100).
    Arêtes : 1-2 et 2-3.

    Compteur : ecart_kg_transportes_vs_arrives.
    """
    pop = 50
    besoin = pop * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK  # 100 kg

    cell_1 = Cell(
        cell_id=1,
        area_km2=0.0,
        population=0,
        food_stock_kg=500.0,  # grande réserve
        hunger_ticks=0,
        food_deficit_kg=0.0,
    )
    cell_2 = Cell(
        cell_id=2,
        area_km2=0.0,
        population=pop,
        food_stock_kg=0.0,
        hunger_ticks=1,
        food_deficit_kg=500.0,  # grand déficit accumulé
    )
    cell_3 = Cell(
        cell_id=3,
        area_km2=0.0,
        population=pop,
        food_stock_kg=0.0,
        hunger_ticks=1,
        food_deficit_kg=500.0,
    )

    adjacency = [
        {"a": 1, "b": 2, "kind": "land", "shared_length_m": 5000.0},
        {"a": 2, "b": 3, "kind": "land", "shared_length_m": 5000.0},
    ]
    world = World(cells={1: cell_1, 2: cell_2, 3: cell_3}, adjacency=adjacency)

    transported, arrived = _run_commerce_ecart(world)
    ecart_kg_transportes_vs_arrives = abs(transported - arrived)

    print(f"total_transported = {transported}")
    print(f"somme_deltas_positifs (kg arrivés) = {arrived}")
    print(f"ecart_kg_transportes_vs_arrives = {ecart_kg_transportes_vs_arrives}")

    assert transported > 0, (
        "Aucune nourriture transportée alors que cellule 2 avait besoin."
    )
    assert ecart_kg_transportes_vs_arrives <= TOLERANCE, (
        f"Écart entre total_transported ({transported}) et "
        f"kg arrivés ({arrived}) = {ecart_kg_transportes_vs_arrives} > {TOLERANCE}. "
        "Double comptage possible (transport non atomique)."
    )


# --- test_kg_transportes_est_arrives.py ---
def test_kg_transportes_etoile():
    """
    Topologie étoile : une source, deux receveurs.
    Aucun kg ne peut traverser deux arêtes dans cette topologie.
    Le test vérifie que total_transported = kg reçus par les deux receveurs.
    """
    pop = 100
    besoin = pop * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK  # 200 kg

    cell_1 = Cell(
        cell_id=1,
        area_km2=0.0,
        population=0,
        food_stock_kg=besoin * 3,  # peut nourrir les deux
        hunger_ticks=0,
        food_deficit_kg=0.0,
    )
    cell_2 = Cell(
        cell_id=2,
        area_km2=0.0,
        population=pop,
        food_stock_kg=0.0,
        hunger_ticks=1,
        food_deficit_kg=besoin,
    )
    cell_3 = Cell(
        cell_id=3,
        area_km2=0.0,
        population=pop,
        food_stock_kg=0.0,
        hunger_ticks=1,
        food_deficit_kg=besoin,
    )

    adjacency = [
        {"a": 1, "b": 2, "kind": "land", "shared_length_m": 5000.0},
        {"a": 1, "b": 3, "kind": "land", "shared_length_m": 5000.0},
    ]
    world = World(cells={1: cell_1, 2: cell_2, 3: cell_3}, adjacency=adjacency)

    transported, arrived = _run_commerce_ecart(world)
    ecart = abs(transported - arrived)

    print(f"[étoile] total_transported = {transported}")
    print(f"[étoile] somme_deltas_positifs = {arrived}")
    print(f"[étoile] ecart = {ecart}")

    assert transported > 0
    assert ecart <= TOLERANCE


# --- test_tick_nourrit_une_fois.py ---
def test_ecart_temoin_vs_receveuse():
    """
    Le commerce avant consommation garantit qu'un kg transféré ne nourrit
    qu'une fois. L'écart de stock entre la cellule témoin (stock initial = besoin)
    et la cellule receveuse (stock = 0, reçoit besoin via commerce) doit être
    ≤ 1×10⁻⁹ kg après un tick complet (production désactivée).

    Compteur : ecart_stock_temoin_vs_receveuse.

    Note de conception : la cellule receveuse démarre avec food_deficit_kg =
    besoin_kg (déficit accumulé du tick précédent). Après le tick, son
    food_stock_kg final est le même que celui de la cellule témoin (tous deux
    ont consommé exactement leur besoin). Le food_deficit_kg peut différer
    (récupération graduelle sur le déficit accumulé de la receveuse),
    ce qui est cohérent avec la physique : seul le stock alimentaire du tick
    courant est équivalent, pas l'historique de famine.
    """
    besoin_kg = 50 * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK  # 100.0 kg

    world, id_temoin, id_receveuse = _build_sc1_world(besoin_kg)
    rng = random.Random(0)  # graine fixe, production désactivée (area_km2=0)

    tick(world, rng)

    stock_temoin = world.cells[id_temoin].food_stock_kg
    stock_receveuse = world.cells[id_receveuse].food_stock_kg
    ecart_stock_temoin_vs_receveuse = abs(stock_temoin - stock_receveuse)

    print(f"stock_temoin    = {stock_temoin}")
    print(f"stock_receveuse = {stock_receveuse}")
    print(f"ecart_stock_temoin_vs_receveuse = {ecart_stock_temoin_vs_receveuse}")
    print(f"deficit_temoin    = {world.cells[id_temoin].food_deficit_kg}")
    print(f"deficit_receveuse = {world.cells[id_receveuse].food_deficit_kg}")

    assert ecart_stock_temoin_vs_receveuse <= TOLERANCE, (
        f"Écart de stock trop grand : {ecart_stock_temoin_vs_receveuse} > {TOLERANCE}. "
        f"La nourriture a peut-être été comptée deux fois."
    )


# --- test_tick_nourrit_une_fois.py ---
def test_invariance_ordre_aretes():
    """
    L'état final est invariant à l'ordre des arêtes dans adjacency.

    Scénario 1 — chaîne (existant) :
    Deux exécutions avec [1-2, 2-3] et [2-3, 1-2] doivent produire des
    stocks finaux identiques pour les trois cellules (écart ≤ 1×10⁻⁹ kg).

    Scénario 2 — source contestée (N1 feedback 001) :
    Source S surplus=80, receveurs A et B besoin=60 chacun (total 120 > 80).
    Allocation proportionnelle attendue : A=40, B=40 dans les deux ordres.
    Ce scénario rougit dès que le snapshot est retiré (traitement arête-par-arête
    en direct), indépendamment de la définition du besoin/surplus.

    Compteur : etat_final_invariant_ordre_aretes (max écart sur tous les tests).
    """
    # --- Scénario 1 : chaîne ---
    edges_AB = [
        {"a": 1, "b": 2, "kind": "land", "shared_length_m": 5000.0},
        {"a": 2, "b": 3, "kind": "land", "shared_length_m": 5000.0},
    ]
    edges_BA = [
        {"a": 2, "b": 3, "kind": "land", "shared_length_m": 5000.0},
        {"a": 1, "b": 2, "kind": "land", "shared_length_m": 5000.0},
    ]

    world_AB = _build_chain_world(edges_AB)
    world_BA = _build_chain_world(edges_BA)

    rng_AB = random.Random(0)
    rng_BA = random.Random(0)

    tick(world_AB, rng_AB)
    tick(world_BA, rng_BA)

    ecarts_s1 = {}
    for cell_id in [1, 2, 3]:
        ecart = abs(
            world_AB.cells[cell_id].food_stock_kg
            - world_BA.cells[cell_id].food_stock_kg
        )
        ecarts_s1[cell_id] = ecart
        print(
            f"[scénario 1] cellule {cell_id} : "
            f"stock_AB={world_AB.cells[cell_id].food_stock_kg}, "
            f"stock_BA={world_BA.cells[cell_id].food_stock_kg}, écart={ecart}"
        )

    # --- Scénario 2 : source contestée (test du mécanisme commerce seul) ---
    # Appelle _apply_commerce directement pour comparer les stocks APRÈS COMMERCE
    # mais AVANT CONSOMMATION. Ainsi, une livraison inégale entre les deux ordres
    # se manifeste immédiatement dans food_stock_kg sans être masquée par la
    # consommation (qui ramènerait les deux receveurs à 0 dans les deux cas).
    edges_SA_SB = [
        {"a": 10, "b": 11, "kind": "land", "shared_length_m": 5000.0},
        {"a": 10, "b": 12, "kind": "land", "shared_length_m": 5000.0},
    ]
    edges_SB_SA = [
        {"a": 10, "b": 12, "kind": "land", "shared_length_m": 5000.0},
        {"a": 10, "b": 11, "kind": "land", "shared_length_m": 5000.0},
    ]

    world_SA_SB = _build_contested_source_world(edges_SA_SB)
    world_SB_SA = _build_contested_source_world(edges_SB_SA)

    _apply_commerce(world_SA_SB, [0.0])
    _apply_commerce(world_SB_SA, [0.0])

    ecarts_s2 = {}
    for cell_id in [10, 11, 12]:
        ecart = abs(
            world_SA_SB.cells[cell_id].food_stock_kg
            - world_SB_SA.cells[cell_id].food_stock_kg
        )
        ecarts_s2[cell_id] = ecart
        print(
            f"[scénario 2] cellule {cell_id} : "
            f"stock_SA_SB={world_SA_SB.cells[cell_id].food_stock_kg}, "
            f"stock_SB_SA={world_SB_SA.cells[cell_id].food_stock_kg}, écart={ecart}"
        )

    etat_final_invariant_ordre_aretes = max(
        max(ecarts_s1.values()), max(ecarts_s2.values())
    )
    print(
        f"etat_final_invariant_ordre_aretes (max_ecart) = {etat_final_invariant_ordre_aretes}"
    )

    for cell_id, ecart in ecarts_s1.items():
        assert ecart <= TOLERANCE, (
            f"[scénario 1] cellule {cell_id} : écart {ecart} > {TOLERANCE} entre "
            f"ordre [1-2,2-3] et [2-3,1-2]. Dépendance à l'ordre des arêtes."
        )
    for cell_id, ecart in ecarts_s2.items():
        assert ecart <= TOLERANCE, (
            f"[scénario 2] cellule {cell_id} : écart {ecart} > {TOLERANCE} entre "
            f"ordre [S→A,S→B] et [S→B,S→A]. Dépendance à l'ordre (snapshot absent ?)."
        )


# --- test_tick_nourrit_une_fois.py ---
def test_recepteur_pas_sur_livre():
    """
    N3 feedback 001 — Écrêtage côté receveur : un receveur adjacent à plusieurs
    sources en surplus ne reçoit pas plus que son besoin snapshot.

    Topologie : deux sources S1 et S2 (surplus ≥ besoin_R chacune) adjacentes
    au même receveur R.  Sans écrêtage, R recevrait 2 × besoin_R et terminerait
    le tick avec un stock positif. Avec écrêtage,
    R reçoit exactement besoin_R, consomme tout, stock final = 0.

    Sans écrêtage (comportement attendu en échec) :
        R reçoit besoin_R de S1 + besoin_R de S2 = 2 × besoin_R.
        Stock final après consommation = besoin_R > 0.
    Avec écrêtage :
        R reçoit besoin_R au total (réparti entre S1 et S2).
        Stock final = 0.
    """
    pop_r = 100
    besoin_r = pop_r * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK  # 200.0 kg

    source1 = Cell(
        cell_id=1, area_km2=0.0, population=0,
        food_stock_kg=besoin_r * 2,  # large surplus
        hunger_ticks=0, food_deficit_kg=0.0,
    )
    source2 = Cell(
        cell_id=2, area_km2=0.0, population=0,
        food_stock_kg=besoin_r * 2,
        hunger_ticks=0, food_deficit_kg=0.0,
    )
    receveur = Cell(
        cell_id=3, area_km2=0.0, population=pop_r,
        food_stock_kg=0.0,
        hunger_ticks=1, food_deficit_kg=0.0,
    )

    adjacency = [
        {"a": 1, "b": 3, "kind": "land", "shared_length_m": 5000.0},
        {"a": 2, "b": 3, "kind": "land", "shared_length_m": 5000.0},
    ]
    world = World(cells={1: source1, 2: source2, 3: receveur}, adjacency=adjacency)

    rng = random.Random(0)
    tick(world, rng)

    stock_r_final = world.cells[3].food_stock_kg
    print(f"besoin_r = {besoin_r}")
    print(f"stock_receveur_apres_tick = {stock_r_final}")

    assert stock_r_final == 0.0, (
        f"Receveur sur-livré : stock final {stock_r_final} ≠ 0. "
        "L'écrêtage côté receveur n'a pas borné le total reçu à son besoin."
    )

# --- Commerce généralisé : toute marchandise circule ---

# Nom local au test : pas de constante moteur.
_MARCHANDISE_ESSAI = "__essai_commerce__"
_CONSOMMATION_ESSAI = 1.0 * TICK_DURATION_DAYS


def _patch_consommation_essai(monkeypatch):
    """Monkeypatch du seul accès nommé pour la marchandise d'essai."""
    from sim import constants as k

    original = k.consommation_kg_par_habitant_par_tick

    def _patched(marchandise: str) -> float:
        if marchandise == _MARCHANDISE_ESSAI:
            return _CONSOMMATION_ESSAI
        return original(marchandise)

    monkeypatch.setattr(k, "consommation_kg_par_habitant_par_tick", _patched)


def test_maillon_commerce_sans_nom_nourriture():
    """L'AST du maillon commerce ne nomme plus la marchandise alimentaire."""
    import ast
    import pathlib

    engine_file = pathlib.Path(__file__).parent.parent / "engine.py"
    tree = ast.parse(engine_file.read_text(encoding="utf-8"), filename=str(engine_file))
    fonctions = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("_apply_commerce")
    }
    assert fonctions, "maillon commerce introuvable"

    occurrences = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != "_apply_commerce":
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Constant) and sub.value == "nourriture":
                occurrences += 1
            elif isinstance(sub, ast.Attribute) and sub.attr == "MARCHANDISE_NOURRITURE":
                occurrences += 1
    assert occurrences == 0, (
        f"occurrences_nourriture_dans_le_maillon={occurrences} ; "
        f"fonctions_du_maillon={len(fonctions)}"
    )


def _build_sc3_micro_monde() -> tuple[World, int, int]:
    """Deux cellules adjacentes : source et receveuse pour deux marchandises."""
    from sim.model import ecrire_stock_marchandise

    pop = 50
    source = Cell(
        cell_id=201,
        area_km2=0.0,
        population=0,
        stocks={MARCHANDISE_NOURRITURE: 200.0, _MARCHANDISE_ESSAI: 200.0},
        hunger_ticks=0,
        food_deficit_kg=0.0,
    )
    receveuse = Cell(
        cell_id=202,
        area_km2=0.0,
        population=pop,
        stocks={},
        hunger_ticks=0,
        food_deficit_kg=0.0,
    )
    adjacency = [{"a": 201, "b": 202, "kind": "land", "shared_length_m": 1000.0}]
    return World(cells={201: source, 202: receveuse}, adjacency=adjacency), 201, 202


def test_marchandise_essai_circule_sans_ligne_supplementaire(monkeypatch):
    """Une marchandise d'essai consommée circule via l'accès nommé seul."""
    from sim.model import lire_stock_marchandise

    _patch_consommation_essai(monkeypatch)
    world, _src, rcv = _build_sc3_micro_monde()
    stock_avant = lire_stock_marchandise(world.cells[rcv], _MARCHANDISE_ESSAI)
    assert stock_avant == -1.0

    _apply_commerce(world, [0.0])

    stock_apres = lire_stock_marchandise(world.cells[rcv], _MARCHANDISE_ESSAI)
    assert stock_apres > 0.0, (
        "La marchandise d'essai n'a pas circulé sans ligne ajoutée au maillon."
    )


def test_capacite_arete_partagee_entre_marchandises(monkeypatch):
    """Sur une arête saturée, la somme des transferts égale la capacité lue."""
    from sim.model import ecrire_stock_marchandise, lire_stock_marchandise

    _patch_consommation_essai(monkeypatch)
    pop = 100
    besoin_alim = pop * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    besoin_essai = pop * _CONSOMMATION_ESSAI

    source = Cell(
        cell_id=301, area_km2=0.0, population=0,
        stocks={MARCHANDISE_NOURRITURE: 500.0, _MARCHANDISE_ESSAI: 500.0},
        hunger_ticks=0, food_deficit_kg=0.0,
    )
    receveuse = Cell(
        cell_id=302, area_km2=0.0, population=pop,
        stocks={},
        hunger_ticks=0, food_deficit_kg=0.0,
    )
    adjacency = [{"a": 301, "b": 302, "kind": "land", "shared_length_m": 1000.0}]
    world = World(cells={301: source, 302: receveuse}, adjacency=adjacency)

    _apply_commerce(world, [0.0])

    stock_alim_avant = 0.0
    stock_essai_avant = 0.0
    delta_alim = max(
        0.0,
        lire_stock_marchandise(world.cells[302], MARCHANDISE_NOURRITURE) - stock_alim_avant,
    )
    delta_essai = max(
        0.0,
        lire_stock_marchandise(world.cells[302], _MARCHANDISE_ESSAI) - stock_essai_avant,
    )
    somme_transferts = delta_alim + delta_essai
    capacite = TRADE_CAPACITY_KG_PER_EDGE_PER_TICK

    # La généralisation est réelle : sans elle, sur le moteur de base, la
    # marchandise d'essai ne circule pas (delta_essai == 0) et ce contrôle
    # échoue. C'est le rouge prouvé avant correction.
    assert delta_essai > 0, (
        f"marchandise d'essai non transportée : delta_essai={delta_essai} ; "
        f"la généralisation du commerce est absente"
    )
    assert somme_transferts <= capacite + TOLERANCE, (
        f"somme_transferts_sur_arete_partagee={somme_transferts} > capacite={capacite}"
    )
    assert abs(somme_transferts - capacite) <= TOLERANCE, (
        f"somme_transferts={somme_transferts} != capacite={capacite} ; "
        f"besoins additionnés={besoin_alim + besoin_essai}"
    )


def test_conservation_masse_par_marchandise(monkeypatch):
    """Le commerce déplace sans créer ni détruire, par marchandise."""
    from sim.model import lire_stock_marchandise

    _patch_consommation_essai(monkeypatch)
    world, _, _ = _build_sc3_micro_monde()
    for marchandise in (MARCHANDISE_NOURRITURE, _MARCHANDISE_ESSAI):
        somme_avant = sum(
            max(0.0, lire_stock_marchandise(c, marchandise))
            for c in world.cells.values()
        )
        copie = World(
            cells={cid: Cell(
                cell_id=c.cell_id,
                area_km2=c.area_km2,
                population=c.population,
                stocks=dict(c.stocks),
                hunger_ticks=c.hunger_ticks,
                food_deficit_kg=c.food_deficit_kg,
                mortality_remainder=c.mortality_remainder,
            ) for cid, c in world.cells.items()},
            adjacency=list(world.adjacency),
        )
        _apply_commerce(copie, [0.0])
        somme_apres = sum(
            max(0.0, lire_stock_marchandise(c, marchandise))
            for c in copie.cells.values()
        )
        # Identité au bit près, sans tolérance — le commerce déplace,
        # il ne crée ni ne détruit. Aucun seuil n'absorbe un écart.
        assert somme_apres == somme_avant, (
            f"ecart_de_masse pour {marchandise!r} : "
            f"avant={somme_avant!r} après={somme_apres!r}"
        )


def test_commerce_ne_modifie_pas_food_deficit(monkeypatch):
    """Le maillon commerce ne touche jamais food_deficit_kg."""
    _patch_consommation_essai(monkeypatch)
    world, _, _ = _build_sc3_micro_monde()
    deficits_avant = {cid: c.food_deficit_kg for cid, c in world.cells.items()}
    _apply_commerce(world, [0.0])
    for cid, avant in deficits_avant.items():
        assert world.cells[cid].food_deficit_kg == avant, (
            f"modification_de_dette cellule {cid}"
        )


def test_ordre_insertion_paniers_invariant(monkeypatch):
    """Deux ordres d'insertion des paniers donnent le même résultat."""
    from sim.model import ecrire_stock_marchandise, lire_stock_marchandise

    _patch_consommation_essai(monkeypatch)

    def _monde(ordre: list[str]) -> World:
        pop = 40
        a = Cell(
            cell_id=401, area_km2=0.0, population=0,
            stocks={}, hunger_ticks=0, food_deficit_kg=0.0,
        )
        b = Cell(
            cell_id=402, area_km2=0.0, population=pop,
            stocks={}, hunger_ticks=0, food_deficit_kg=0.0,
        )
        for cle in ordre:
            ecrire_stock_marchandise(a, cle, 300.0)
            ecrire_stock_marchandise(b, cle, 0.0)
        adjacency = [{"a": 401, "b": 402, "kind": "land", "shared_length_m": 1000.0}]
        return World(cells={401: a, 402: b}, adjacency=adjacency)

    w1 = _monde([MARCHANDISE_NOURRITURE, _MARCHANDISE_ESSAI])
    w2 = _monde([_MARCHANDISE_ESSAI, MARCHANDISE_NOURRITURE])
    _apply_commerce(w1, [0.0])
    _apply_commerce(w2, [0.0])

    for marchandise in (MARCHANDISE_NOURRITURE, _MARCHANDISE_ESSAI):
        s1 = lire_stock_marchandise(w1.cells[402], marchandise)
        s2 = lire_stock_marchandise(w2.cells[402], marchandise)
        assert abs(s1 - s2) <= TOLERANCE, (
            f"ordre d'insertion change le résultat pour {marchandise!r}: {s1} vs {s2}"
        )

# --- Capacité d'arête selon le relief ---

def _classes_relief_depuis_carte() -> list[str]:
    """Les cinq classes de relief dérivées de World.lire_carte()."""
    from sim import constants as k

    carte_doc = World.lire_carte()
    reliefs = {
        cell.get("relief")
        for cell in carte_doc.get("cellules", [])
        if cell.get("relief") is not None
    }
    attendues = set(k.facteurs_transport_par_relief())
    manquantes = attendues - reliefs
    assert not manquantes, f"classes de relief absentes de la carte : {sorted(manquantes)}"
    return sorted(attendues, key=lambda r: k.facteurs_transport_par_relief()[r], reverse=True)


def _build_micro_monde_relief_transport() -> tuple[World, int, dict[str, int]]:
    """
    Micro-monde : une source en plaine, une receveuse par classe de relief.
    Retourne le monde, l'id source et le mapping relief → cell_id receveuse.
    """
    from sim.model import ecrire_stock_marchandise

    classes = _classes_relief_depuis_carte()
    source_id = 9000
    pop = 100
    besoin = pop * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    stock_source = besoin * len(classes) * 10

    carte: dict[int, dict] = {
        source_id: {"cell_id": source_id, "relief": "plaine"},
    }
    cells = {
        source_id: Cell(
            cell_id=source_id,
            area_km2=0.0,
            population=0,
            stocks={},
            hunger_ticks=0,
            food_deficit_kg=0.0,
        ),
    }
    ecrire_stock_marchandise(cells[source_id], MARCHANDISE_NOURRITURE, stock_source)

    receveuses: dict[str, int] = {}
    adjacency: list[dict] = []
    for idx, relief in enumerate(classes):
        cid = source_id + idx + 1
        receveuses[relief] = cid
        carte[cid] = {"cell_id": cid, "relief": relief}
        cells[cid] = Cell(
            cell_id=cid,
            area_km2=0.0,
            population=pop,
            stocks={},
            hunger_ticks=0,
            food_deficit_kg=0.0,
        )
        adjacency.append(
            {"a": source_id, "b": cid, "kind": "land", "shared_length_m": 1000.0}
        )

    world = World(cells=cells, adjacency=adjacency, carte=carte)
    return world, source_id, receveuses


def _transfert_vers(world: World, receveuse_id: int) -> float:
    from sim.model import lire_stock_marchandise

    stock_avant = lire_stock_marchandise(world.cells[receveuse_id], MARCHANDISE_NOURRITURE)
    stock_avant = stock_avant if stock_avant >= 0 else 0.0
    copie_cells = {
        cid: Cell(
            cell_id=c.cell_id,
            area_km2=c.area_km2,
            population=c.population,
            stocks=dict(c.stocks),
            hunger_ticks=c.hunger_ticks,
            food_deficit_kg=c.food_deficit_kg,
            mortality_remainder=c.mortality_remainder,
        )
        for cid, c in world.cells.items()
    }
    w = World(cells=copie_cells, adjacency=list(world.adjacency), carte=dict(world.carte))
    from sim.engine import _initialiser_capacite_aretes
    cap = _initialiser_capacite_aretes(w)
    _apply_commerce(w, [0.0], MARCHANDISE_NOURRITURE, cap)
    stock_apres = lire_stock_marchandise(w.cells[receveuse_id], MARCHANDISE_NOURRITURE)
    stock_apres = stock_apres if stock_apres >= 0 else 0.0
    return stock_apres - stock_avant


def test_cinq_facteurs_transport_suivent_ordre_strict():
    """Cinq transferts distincts, ordre strict des facteurs de transport."""
    from sim import constants as k

    world, _source_id, receveuses = _build_micro_monde_relief_transport()
    facteurs = k.facteurs_transport_par_relief()
    classes = _classes_relief_depuis_carte()
    transferts = [_transfert_vers(world, receveuses[r]) for r in classes]

    for i in range(len(transferts) - 1):
        assert transferts[i] > transferts[i + 1] + TOLERANCE, (
            f"ordre des transferts violé entre {classes[i]} ({transferts[i]}) "
            f"et {classes[i + 1]} ({transferts[i + 1]}) ; facteurs={facteurs}"
        )

    distincts = len({round(t, 6) for t in transferts})
    assert distincts == len(classes), (
        f"transferts non distincts : {dict(zip(classes, transferts))}"
    )


def _build_monde_arete_relief(relief_a: str, relief_b: str) -> World:
    from sim.model import ecrire_stock_marchandise

    a_id, b_id = 9100, 9101
    pop = 100
    carte = {
        a_id: {"cell_id": a_id, "relief": relief_a},
        b_id: {"cell_id": b_id, "relief": relief_b},
    }
    source = Cell(
        cell_id=a_id, area_km2=0.0, population=0,
        stocks={}, hunger_ticks=0, food_deficit_kg=0.0,
    )
    receveuse = Cell(
        cell_id=b_id, area_km2=0.0, population=pop,
        stocks={}, hunger_ticks=0, food_deficit_kg=0.0,
    )
    ecrire_stock_marchandise(source, MARCHANDISE_NOURRITURE, 10000.0)
    adjacency = [{"a": a_id, "b": b_id, "kind": "land", "shared_length_m": 1000.0}]
    return World(cells={a_id: source, b_id: receveuse}, adjacency=adjacency, carte=carte)


def test_goulot_relief_min_commande_capacite():
    """Le bout le plus difficile commande ; sens de lecture invariant."""
    from sim import constants as k

    base = TRADE_CAPACITY_KG_PER_EDGE_PER_TICK
    facteurs = k.facteurs_transport_par_relief()

    t_plaine_plaine = _transfert_vers(_build_monde_arete_relief("plaine", "plaine"), 9101)
    t_plaine_hm = _transfert_vers(_build_monde_arete_relief("plaine", "haute_montagne"), 9101)
    t_hm_hm = _transfert_vers(_build_monde_arete_relief("haute_montagne", "haute_montagne"), 9101)
    t_hm_plaine = _transfert_vers(_build_monde_arete_relief("haute_montagne", "plaine"), 9101)

    cap_plaine_hm = base * min(facteurs["plaine"], facteurs["haute_montagne"])
    cap_hm_hm = base * facteurs["haute_montagne"]
    cap_plaine_plaine = base * facteurs["plaine"]

    assert abs(t_plaine_hm - t_hm_hm) <= TOLERANCE, (
        f"plaine–haute_montagne ({t_plaine_hm}) != haute_montagne–haute_montagne ({t_hm_hm})"
    )
    assert t_plaine_hm < t_plaine_plaine - TOLERANCE, (
        f"plaine–haute_montagne ({t_plaine_hm}) n'est pas < plaine–plaine ({t_plaine_plaine})"
    )
    assert abs(t_plaine_hm - t_hm_plaine) <= TOLERANCE, (
        f"sens inversé : {t_plaine_hm} vs {t_hm_plaine}"
    )
    besoin = 100 * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    assert abs(t_plaine_hm - min(besoin, cap_plaine_hm)) <= TOLERANCE
    assert abs(t_hm_hm - min(besoin, cap_hm_hm)) <= TOLERANCE
    assert abs(t_plaine_plaine - min(besoin, cap_plaine_plaine)) <= TOLERANCE


def test_relief_inconnu_refuse_sur_monde_charge():
    """Relief inconnu sur monde chargé : erreur explicite avec cell_id et valeur."""
    from sim.engine import ReliefInvalideError

    world = _build_monde_arete_relief("plaine", "plaine")
    a_id, b_id = 9100, 9101
    world.carte[b_id]["relief"] = "relief_inexistant_040"

    with pytest.raises(ReliefInvalideError, match=str(a_id)):
        _apply_commerce(world, [0.0])
    with pytest.raises(ReliefInvalideError, match=str(b_id)):
        _apply_commerce(world, [0.0])
    with pytest.raises(ReliefInvalideError, match="relief_inexistant_040"):
        _apply_commerce(world, [0.0])


def test_sans_carte_capacite_transport_inchangee():
    """Sans carte, tick et commerce gardent la capacité de base."""
    from sim.model import ecrire_stock_marchandise, lire_stock_marchandise

    pop = 50
    source = Cell(
        cell_id=9200, area_km2=0.0, population=0,
        stocks={}, hunger_ticks=0, food_deficit_kg=0.0,
    )
    receveuse = Cell(
        cell_id=9201, area_km2=0.0, population=pop,
        stocks={}, hunger_ticks=0, food_deficit_kg=0.0,
    )
    ecrire_stock_marchandise(source, MARCHANDISE_NOURRITURE, 500.0)
    world = World(
        cells={9200: source, 9201: receveuse},
        adjacency=[{"a": 9200, "b": 9201, "kind": "land", "shared_length_m": 1000.0}],
    )

    tick(world, random.Random(0))
    _apply_commerce(world, [0.0])
    stock = lire_stock_marchandise(world.cells[9201], MARCHANDISE_NOURRITURE)
    assert stock > 0.0
    assert stock <= TRADE_CAPACITY_KG_PER_EDGE_PER_TICK + TOLERANCE


# --- Migration de famine ---

def _somme_populations(world: World) -> int:
    return sum(c.population for c in world.cells.values())


def _build_monde_migration_trois_cellules() -> World:
    """Affamée (201), voisine en surplus (202), témoin sans arête (203)."""
    from sim import constants as _constantes

    pop = 100
    besoin = pop * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    affamee = Cell(
        cell_id=201,
        area_km2=0.0,
        population=pop,
        food_stock_kg=0.0,
        hunger_ticks=0,
        food_deficit_kg=besoin,
        migration_remainder=0.0,
    )
    surplus = Cell(
        cell_id=202,
        area_km2=0.0,
        population=pop,
        food_stock_kg=besoin * 3,
        hunger_ticks=0,
        food_deficit_kg=0.0,
        migration_remainder=0.0,
    )
    temoin = Cell(
        cell_id=203,
        area_km2=0.0,
        population=pop,
        food_stock_kg=besoin,
        hunger_ticks=0,
        food_deficit_kg=0.0,
        migration_remainder=0.0,
    )
    adjacency = [{"a": 201, "b": 202, "kind": "land", "shared_length_m": 1000.0}]
    return World(cells={201: affamee, 202: surplus, 203: temoin}, adjacency=adjacency)


def _penuries_affamee_seule(world: World) -> dict[int, float]:
  from sim.constants import FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
  penuries = {cid: 0.0 for cid in world.cells}
  for cid, cell in world.cells.items():
    if cell.food_stock_kg <= 0 and cell.population > 0:
      penuries[cid] = cell.population * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
  return penuries


def test_conservation_population_migration():
    """La migration déplace sans créer ni détruire d'habitants."""
    from sim.engine import _apply_migration

    world = _build_monde_migration_trois_cellules()
    penuries = _penuries_affamee_seule(world)
    avant = _somme_populations(world)
    _apply_migration(world, penuries)
    apres = _somme_populations(world)
    ecart = abs(apres - avant)
    assert ecart == 0, f"écart de population = {ecart} (attendu 0)"


def test_depart_affame_vers_surplus_temoin_inchange():
    """L'affamée perd, la voisine gagne autant, le témoin ne bouge pas."""
    from sim import constants as _constantes
    from sim.engine import _apply_migration

    world = _build_monde_migration_trois_cellules()
    pop_temoin_avant = world.cells[203].population
    pop_affamee_avant = world.cells[201].population
    pop_surplus_avant = world.cells[202].population
    penuries = _penuries_affamee_seule(world)
    _apply_migration(world, penuries)
    delta_affamee = pop_affamee_avant - world.cells[201].population
    delta_surplus = world.cells[202].population - pop_surplus_avant
    assert delta_affamee > 0, "la cellule affamée devrait perdre des habitants"
    assert delta_affamee == delta_surplus, (
        f"transfert non conservé : -{delta_affamee} vs +{delta_surplus}"
    )
    assert world.cells[203].population == pop_temoin_avant


def test_zero_partant_sans_destination_surplus():
    """Affamée sans voisine en surplus : zéro partant mesuré."""
    from sim.engine import _apply_migration

    affamee = Cell(
        cell_id=301, area_km2=0.0, population=50,
        food_stock_kg=0.0, hunger_ticks=1, food_deficit_kg=100.0,
        migration_remainder=0.0,
    )
    voisine_vide = Cell(
        cell_id=302, area_km2=0.0, population=50,
        food_stock_kg=0.0, hunger_ticks=0, food_deficit_kg=0.0,
        migration_remainder=0.0,
    )
    world = World(
        cells={301: affamee, 302: voisine_vide},
        adjacency=[{"a": 301, "b": 302, "kind": "land", "shared_length_m": 1000.0}],
    )
    pop_avant = world.cells[301].population
    _apply_migration(world, {301: 10.0, 302: 0.0})
    assert world.cells[301].population == pop_avant


def test_zero_partant_depuis_cellule_rassasiee():
    """Cellule rassasiée entourée de surplus : zéro partant."""
    from sim.engine import _apply_migration

    pop = 40
    besoin = pop * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    rassasiee = Cell(
        cell_id=311, area_km2=0.0, population=pop,
        food_stock_kg=besoin, hunger_ticks=0, food_deficit_kg=0.0,
        migration_remainder=0.0,
    )
    surplus = Cell(
        cell_id=312, area_km2=0.0, population=pop,
        food_stock_kg=besoin * 5, hunger_ticks=0, food_deficit_kg=0.0,
        migration_remainder=0.0,
    )
    world = World(
        cells={311: rassasiee, 312: surplus},
        adjacency=[{"a": 311, "b": 312, "kind": "land", "shared_length_m": 1000.0}],
    )
    pop_avant = world.cells[311].population
    _apply_migration(world, {311: 0.0, 312: 0.0})
    assert world.cells[311].population == pop_avant


def test_pas_immobilite_par_arrondi_migration():
    """Le report de fraction permet un départ en temps dérivé."""
    import math
    from sim import constants as _constantes
    from sim.engine import _apply_migration

    pop = 50
    fraction = _constantes.FRACTION_MIGRANTE_PAR_TICK
    borne = math.ceil(1.0 / (pop * fraction))
    besoin = pop * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    affamee = Cell(
        cell_id=401, area_km2=0.0, population=pop,
        food_stock_kg=0.0, hunger_ticks=1, food_deficit_kg=besoin,
        migration_remainder=0.0,
    )
    surplus = Cell(
        cell_id=402, area_km2=0.0, population=pop,
        food_stock_kg=besoin * 3, hunger_ticks=0, food_deficit_kg=0.0,
        migration_remainder=0.0,
    )
    world = World(
        cells={401: affamee, 402: surplus},
        adjacency=[{"a": 401, "b": 402, "kind": "land", "shared_length_m": 1000.0}],
    )
    ticks_jusqu_au_depart = -1
    for t in range(borne):
        pop_avant = world.cells[401].population
        _apply_migration(world, {401: besoin, 402: 0.0})
        if world.cells[401].population < pop_avant:
            ticks_jusqu_au_depart = t + 1
            break
    assert 0 < ticks_jusqu_au_depart <= borne, (
        f"premier départ au tick {ticks_jusqu_au_depart}, borne dérivée {borne}"
    )


def test_receveuse_ne_renvie_pas_meme_tick():
    """Une cellule qui reçoit des arrivants n'en envoie pas le même tick."""
    from sim.engine import _apply_migration

    pop = 80
    besoin = pop * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    affamee_a = Cell(
        cell_id=501, area_km2=0.0, population=pop,
        food_stock_kg=0.0, hunger_ticks=1, food_deficit_kg=besoin,
        migration_remainder=0.0,
    )
    affamee_b = Cell(
        cell_id=502, area_km2=0.0, population=pop,
        food_stock_kg=0.0, hunger_ticks=1, food_deficit_kg=besoin,
        migration_remainder=0.0,
    )
    surplus = Cell(
        cell_id=503, area_km2=0.0, population=pop,
        food_stock_kg=besoin * 5, hunger_ticks=0, food_deficit_kg=0.0,
        migration_remainder=0.0,
    )
    world = World(
        cells={501: affamee_a, 502: affamee_b, 503: surplus},
        adjacency=[
            {"a": 501, "b": 503, "kind": "land", "shared_length_m": 1000.0},
            {"a": 502, "b": 503, "kind": "land", "shared_length_m": 1000.0},
        ],
    )
    penuries = {501: besoin, 502: besoin, 503: 0.0}
    pops_avant = {cid: c.population for cid, c in world.cells.items()}
    _apply_migration(world, penuries)
    # 503 reçoit : elle ne doit pas avoir perdu de population
    assert world.cells[503].population >= pops_avant[503]
    if world.cells[503].population > pops_avant[503]:
        assert penuries.get(503, 0.0) <= 0.0 or world.cells[503].population == pops_avant[503] + (
            pops_avant[501] - world.cells[501].population
        ) + (pops_avant[502] - world.cells[502].population)


def test_invariance_ordre_aretes_migration():
    """Même micro-monde, ordre d'adjacence inversé : état identique."""
    from sim.engine import _apply_migration

    def _jouer(adjacency: list[dict]) -> dict[int, int]:
        pop = 60
        besoin = pop * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
        a = Cell(
            cell_id=601, area_km2=0.0, population=pop,
            food_stock_kg=0.0, hunger_ticks=1, food_deficit_kg=besoin,
            migration_remainder=0.0,
        )
        b = Cell(
            cell_id=602, area_km2=0.0, population=pop,
            food_stock_kg=besoin * 4, hunger_ticks=0, food_deficit_kg=0.0,
            migration_remainder=0.0,
        )
        c = Cell(
            cell_id=603, area_km2=0.0, population=pop,
            food_stock_kg=besoin * 4, hunger_ticks=0, food_deficit_kg=0.0,
            migration_remainder=0.0,
        )
        world = World(cells={601: a, 602: b, 603: c}, adjacency=adjacency)
        penuries = {601: besoin, 602: 0.0, 603: 0.0}
        _apply_migration(world, penuries)
        return {cid: cell.population for cid, cell in world.cells.items()}

    edges_ab = [
        {"a": 601, "b": 602, "kind": "land", "shared_length_m": 1000.0},
        {"a": 601, "b": 603, "kind": "land", "shared_length_m": 1000.0},
    ]
    edges_ba = list(reversed(edges_ab))
    assert _jouer(edges_ab) == _jouer(edges_ba)


def test_sentinelle_migration_remainder():
    """Sentinelle -1.0 sur Cell() nue ; 0.0 sur monde amorcé."""
    from sim.world import World

    assert Cell(cell_id=1, area_km2=1.0, population=1).migration_remainder == -1.0
    monde = World.charger(0)
    for cell in monde.cells.values():
        assert cell.migration_remainder == 0.0


# --- Capacité dérivée de shared_length_m ---

def _longueurs_arete_monde_reel() -> tuple[float, float, float]:
    """Min, médiane et max des longueurs d'arête entre cellules du monde chargé."""
    import statistics

    monde = World.charger(0)
    longueurs = [
        float(e["shared_length_m"])
        for e in monde.adjacency
        if e["a"] in monde.cells and e["b"] in monde.cells
    ]
    return min(longueurs), statistics.median(longueurs), max(longueurs)


def _transfert_commerce_vers(world: World, receveuse_id: int) -> float:
    from sim.model import lire_stock_marchandise

    stock_avant = lire_stock_marchandise(world.cells[receveuse_id], MARCHANDISE_NOURRITURE)
    stock_avant = stock_avant if stock_avant >= 0 else 0.0
    copie_cells = {
        cid: Cell(
            cell_id=c.cell_id,
            area_km2=c.area_km2,
            population=c.population,
            stocks=dict(c.stocks),
            hunger_ticks=c.hunger_ticks,
            food_deficit_kg=c.food_deficit_kg,
            mortality_remainder=c.mortality_remainder,
        )
        for cid, c in world.cells.items()
    }
    w = World(cells=copie_cells, adjacency=list(world.adjacency))
    from sim.engine import _initialiser_capacite_aretes

    total = [0.0]
    cap = _initialiser_capacite_aretes(w)
    _apply_commerce(w, total, MARCHANDISE_NOURRITURE, cap)
    stock_apres = lire_stock_marchandise(w.cells[receveuse_id], MARCHANDISE_NOURRITURE)
    stock_apres = stock_apres if stock_apres >= 0 else 0.0
    return stock_apres - stock_avant


def _build_monde_longueurs_distinctes(
    longueur_courte: float, longueur_mediane: float, longueur_longue: float,
) -> tuple[World, dict[str, int]]:
    """Source unique, trois receveuses identiques, arêtes de longueurs distinctes."""
    from sim.model import ecrire_stock_marchandise

    source_id = 9300
    pop = 25000
    besoin = pop * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    stock_source = besoin * 20

    source = Cell(
        cell_id=source_id,
        area_km2=0.0,
        population=0,
        stocks={},
        hunger_ticks=0,
        food_deficit_kg=0.0,
    )
    ecrire_stock_marchandise(source, MARCHANDISE_NOURRITURE, stock_source)
    cells = {source_id: source}
    adjacency: list[dict] = []
    receveuses: dict[str, int] = {}
    for idx, (nom, longueur) in enumerate(
        (
            ("courte", longueur_courte),
            ("mediane", longueur_mediane),
            ("longue", longueur_longue),
        )
    ):
        cid = source_id + idx + 1
        receveuses[nom] = cid
        cells[cid] = Cell(
            cell_id=cid,
            area_km2=0.0,
            population=pop,
            stocks={},
            hunger_ticks=0,
            food_deficit_kg=0.0,
        )
        adjacency.append(
            {
                "a": source_id,
                "b": cid,
                "kind": "land",
                "shared_length_m": longueur,
            }
        )
    return World(cells=cells, adjacency=adjacency), receveuses


def test_transferts_proportionnels_aux_longueurs_frontiere():
    """Les transferts suivent le rapport des longueurs de frontière."""
    courte, mediane, longue = _longueurs_arete_monde_reel()
    world, receveuses = _build_monde_longueurs_distinctes(courte, mediane, longue)
    t_court = _transfert_commerce_vers(world, receveuses["courte"])
    t_med = _transfert_commerce_vers(world, receveuses["mediane"])
    t_long = _transfert_commerce_vers(world, receveuses["longue"])

    assert t_court > 0.0 and t_med > t_court + TOLERANCE and t_long > t_med + TOLERANCE

    rapport_tm = t_med / t_court
    rapport_tl = t_long / t_court
    rapport_lm = mediane / courte
    rapport_ll = longue / courte
    assert abs(rapport_tm - rapport_lm) / rapport_lm <= 0.01
    assert abs(rapport_tl - rapport_ll) / rapport_ll <= 0.01


def test_expression_capacite_debit_km_fois_shared_length_m():
    """Le moteur multiplie DEBIT_KG_* et shared_length_m pour la capacité."""
    import ast
    from pathlib import Path

    source = Path(__file__).resolve().parents[1] / "engine.py"
    texte = source.read_text(encoding="utf-8")
    tree = ast.parse(texte)
    expressions = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_capacite_base_arete_kg":
            corps = ast.get_source_segment(texte, node) or ""
            if (
                "DEBIT_KG_PAR_KM_DE_FRONTIERE_PAR_TICK" in corps
                and "shared_length_m" in corps
                and "*" in corps
            ):
                expressions += 1
    assert expressions >= 1, (
        "Aucune expression de capacité DEBIT_KG_* × shared_length_m dans "
        "_capacite_base_arete_kg"
    )


def test_frontiere_ponctuelle_transport_zero():
    """shared_length_m=0 : zéro kg transporté, mesure réelle."""
    from sim.model import ecrire_stock_marchandise, lire_stock_marchandise

    pop = 50
    besoin = pop * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    source = Cell(
        cell_id=9400, area_km2=0.0, population=0,
        stocks={}, hunger_ticks=0, food_deficit_kg=0.0,
    )
    receveuse = Cell(
        cell_id=9401, area_km2=0.0, population=pop,
        stocks={}, hunger_ticks=0, food_deficit_kg=besoin,
    )
    ecrire_stock_marchandise(source, MARCHANDISE_NOURRITURE, besoin * 5)
    world = World(
        cells={9400: source, 9401: receveuse},
        adjacency=[{"a": 9400, "b": 9401, "kind": "land", "shared_length_m": 0.0}],
    )
    from sim.engine import _initialiser_capacite_aretes

    total = [0.0]
    cap = _initialiser_capacite_aretes(world)
    _apply_commerce(world, total, MARCHANDISE_NOURRITURE, cap)
    assert total[0] == 0.0
    stock = lire_stock_marchandise(world.cells[9401], MARCHANDISE_NOURRITURE)
    assert stock <= 0.0


def _ticks_survie_cellule_sans_production(debit_kg: float | None = None) -> int:
    """Ticks avant première baisse de population — cellule area_km2=0 nourrie par voisine."""
    import math
    from sim import constants as k
    from sim.model import ecrire_stock_marchandise

    centre_id = 9500
    source_id = 9501
    pop = 1000  # besoin 2000 kg/tick, irréalisable avec capacité plate 200 kg
    besoin = pop * k.FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    longueur = 50000.0  # DEBIT×50 km = 10 000 kg/tick en dérivé
    source = Cell(
        cell_id=source_id, area_km2=0.0, population=0,
        stocks={}, hunger_ticks=0, food_deficit_kg=0.0,
    )
    ecrire_stock_marchandise(source, MARCHANDISE_NOURRITURE, besoin * 200)
    centre = Cell(
        cell_id=centre_id, area_km2=0.0, population=pop,
        stocks={}, hunger_ticks=0, food_deficit_kg=0.0,
    )
    world = World(
        cells={centre_id: centre, source_id: source},
        adjacency=[
            {"a": source_id, "b": centre_id, "kind": "land", "shared_length_m": longueur},
        ],
    )
    rng = random.Random(0)
    nominal = k.DEBIT_KG_PAR_KM_DE_FRONTIERE_PAR_TICK
    if debit_kg is not None:
        k.DEBIT_KG_PAR_KM_DE_FRONTIERE_PAR_TICK = debit_kg
    try:
        borne = math.ceil(1.0 / k.MAX_DEATH_RATE_PER_TICK) + 5
        ticks_survecus = 0
        for _ in range(borne):
            pop_avant = world.cells[centre_id].population
            tick(world, rng)
            if world.cells[centre_id].population < pop_avant:
                break
            ticks_survecus += 1
        return ticks_survecus
    finally:
        k.DEBIT_KG_PAR_KM_DE_FRONTIERE_PAR_TICK = nominal


def test_cellule_sans_production_survit_avec_capacite_derivee():
    """area_km2=0 : la population tient grâce au commerce dérivé."""
    ticks = _ticks_survie_cellule_sans_production()
    assert ticks >= 5, f"population en baisse trop tôt : {ticks} ticks"


def test_cellule_sans_production_depérit_avec_capacite_plate():
    """Garde : capacité plate injectée en mémoire, la cellule dépérit au premier tick."""
    ticks = _ticks_survie_cellule_sans_production()
    assert ticks >= 5, f"population en baisse trop tôt avec capacité dérivée : {ticks} ticks"
    from sim import constants as _k
    # Remplacer DEBIT par un facteur tel que la capacité dérivée = TRADE_CAPACITY,
    # puis vérifier que la cellule dépérit (la garde est payée)
    nominal_debit = _k.DEBIT_KG_PAR_KM_DE_FRONTIERE_PAR_TICK
    # TRADE_CAPACITY = 200 ; DEBIT × (50000/1000) = DEBIT×50 = 200 → DEBIT = 4.0
    _k.DEBIT_KG_PAR_KM_DE_FRONTIERE_PAR_TICK = 4.0
    try:
        ticks_plat = _ticks_survie_cellule_sans_production()
    finally:
        _k.DEBIT_KG_PAR_KM_DE_FRONTIERE_PAR_TICK = nominal_debit
    assert ticks_plat == 0, (
        f"avec capacité équivalente à la plaque ({ticks_plat}), "
        "la cellule ne devrait pas survivre un tick"
    )
    # Preuve : la contrepartie à capacité plate dépérit plus tôt (0 vs ≥5)
    assert ticks > ticks_plat, (
        f"capacité dérivée ({ticks}) pas > capacité plate ({ticks_plat})"
    )


def test_longueur_frontiere_invalide_refusee():
    """Longueur non numérique sur arête dotée : erreur avec les deux cell_id."""
    import math

    from sim.engine import LongueurFrontiereInvalideError, _initialiser_capacite_aretes
    from sim.model import ecrire_stock_marchandise

    source = Cell(
        cell_id=9600, area_km2=0.0, population=0,
        stocks={}, hunger_ticks=0, food_deficit_kg=0.0,
    )
    receveuse = Cell(
        cell_id=9601, area_km2=0.0, population=10,
        stocks={}, hunger_ticks=0, food_deficit_kg=20.0,
    )
    ecrire_stock_marchandise(source, MARCHANDISE_NOURRITURE, 500.0)
    world = World(
        cells={9600: source, 9601: receveuse},
        adjacency=[{"a": 9600, "b": 9601, "kind": "land", "shared_length_m": 1000.0}],
    )
    for invalide in ("chaîne", None, float("nan")):
        edge = world.adjacency[0]
        edge["shared_length_m"] = invalide
        with pytest.raises(LongueurFrontiereInvalideError, match="9600"):
            _apply_commerce(world, [0.0], MARCHANDISE_NOURRITURE, _initialiser_capacite_aretes(world))
        with pytest.raises(LongueurFrontiereInvalideError, match="9601"):
            _apply_commerce(world, [0.0], MARCHANDISE_NOURRITURE, _initialiser_capacite_aretes(world))


def test_arete_sans_shared_length_m_repli_capacite_plate():
    """Clé absente : repli plat, pas d'erreur."""
    from sim.model import ecrire_stock_marchandise, lire_stock_marchandise

    pop = 50
    besoin = pop * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    source = Cell(
        cell_id=9700, area_km2=0.0, population=0,
        stocks={}, hunger_ticks=0, food_deficit_kg=0.0,
    )
    receveuse = Cell(
        cell_id=9701, area_km2=0.0, population=pop,
        stocks={}, hunger_ticks=0, food_deficit_kg=0.0,
    )
    ecrire_stock_marchandise(source, MARCHANDISE_NOURRITURE, besoin * 3)
    world = World(
        cells={9700: source, 9701: receveuse},
        adjacency=[{"a": 9700, "b": 9701, "kind": "land"}],
    )
    from sim.engine import _initialiser_capacite_aretes

    total = [0.0]
    cap = _initialiser_capacite_aretes(world)
    _apply_commerce(world, total, MARCHANDISE_NOURRITURE, cap)
    stock = lire_stock_marchandise(world.cells[9701], MARCHANDISE_NOURRITURE)
    assert stock > 0.0
    assert stock <= TRADE_CAPACITY_KG_PER_EDGE_PER_TICK + TOLERANCE
# --- La migration lit le reste du tick ---


def _paniers_monde(world: World) -> dict[int, dict[str, float]]:
    return {cid: dict(c.stocks) for cid, c in world.cells.items()}


def _verifier_sc5_conservation_paniers(
    world: World,
    pops_avant: dict[int, int],
    stocks_avant: dict[int, dict[str, float]],
) -> None:
    pops_apres = {cid: c.population for cid, c in world.cells.items()}
    assert sum(pops_avant.values()) == sum(pops_apres.values())
    assert stocks_avant == _paniers_monde(world)


def _build_monde_source_reste_dest(
    source_id: int,
    dest_id: int,
    pop_source: int,
    pop_dest: int,
    reste_dest: float,
) -> World:
    ration = FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    source = Cell(
        cell_id=source_id,
        area_km2=0.0,
        population=pop_source,
        food_stock_kg=0.0,
        hunger_ticks=1,
        food_deficit_kg=pop_source * ration,
        migration_remainder=0.0,
    )
    dest = Cell(
        cell_id=dest_id,
        area_km2=0.0,
        population=pop_dest,
        food_stock_kg=reste_dest,
        hunger_ticks=0,
        food_deficit_kg=0.0,
        migration_remainder=0.0,
    )
    return World(
        cells={source_id: source, dest_id: dest},
        adjacency=[
            {"a": source_id, "b": dest_id, "kind": "land", "shared_length_m": 1000.0}
        ],
    )


def test_migration_reste_positif_inferieur_a_ration():
    """Un reste positif inférieur à une ration est une destination."""
    from sim.constants import FRACTION_MIGRANTE_PAR_TICK
    from sim.engine import _apply_migration

    pop_source = 100
    ration = FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    reste = ration * 0.5
    assert 0.0 < reste < ration

    world = _build_monde_source_reste_dest(701, 702, pop_source, 50, reste)
    penurie = pop_source * ration
    pops_avant = {cid: c.population for cid, c in world.cells.items()}
    stocks_avant = _paniers_monde(world)
    pop_src_avant = world.cells[701].population
    pop_dst_avant = world.cells[702].population

    _apply_migration(world, {701: penurie, 702: 0.0})

    delta_src = pop_src_avant - world.cells[701].population
    delta_dst = world.cells[702].population - pop_dst_avant
    partants_attendus = int(pop_source * FRACTION_MIGRANTE_PAR_TICK)
    assert partants_attendus >= 1
    assert delta_src >= 1
    assert delta_src == delta_dst
    _verifier_sc5_conservation_paniers(world, pops_avant, stocks_avant)


def test_migration_stock_nul_ne_deplace_pas():
    """Stock post-consommation nul : zéro déplacement mesuré."""
    from sim.engine import _apply_migration

    pop_source = 100
    ration = FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    world = _build_monde_source_reste_dest(711, 712, pop_source, 50, 0.0)
    penurie = pop_source * ration
    pops_avant = {cid: c.population for cid, c in world.cells.items()}
    stocks_avant = _paniers_monde(world)

    _apply_migration(world, {711: penurie, 712: 0.0})

    assert world.cells[711].population == pops_avant[711]
    assert world.cells[712].population == pops_avant[712]
    _verifier_sc5_conservation_paniers(world, pops_avant, stocks_avant)


def test_migration_sentinelle_negative_ne_deplace_pas():
    """Sentinelle négative : zéro déplacement mesuré."""
    from sim.engine import _apply_migration

    pop_source = 100
    ration = FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    source = Cell(
        cell_id=721,
        area_km2=0.0,
        population=pop_source,
        food_stock_kg=0.0,
        hunger_ticks=1,
        food_deficit_kg=pop_source * ration,
        migration_remainder=0.0,
    )
    dest = Cell(cell_id=722, area_km2=0.0, population=50)
    world = World(
        cells={721: source, 722: dest},
        adjacency=[{"a": 721, "b": 722, "kind": "land", "shared_length_m": 1000.0}],
    )
    penurie = pop_source * ration
    pops_avant = {cid: c.population for cid, c in world.cells.items()}
    stocks_avant = _paniers_monde(world)

    _apply_migration(world, {721: penurie, 722: 0.0})

    assert world.cells[721].population == pops_avant[721]
    assert world.cells[722].population == pops_avant[722]
    _verifier_sc5_conservation_paniers(world, pops_avant, stocks_avant)


def test_migration_poids_independants_de_la_population_destination():
    """Mêmes stocks, populations distinctes, mêmes poids."""
    from sim.constants import FRACTION_MIGRANTE_PAR_TICK
    from sim.engine import _apply_migration

    pop_source = 200
    ration = FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    reste = ration * 50
    pop_dest_a = 10
    pop_dest_b = 200
    poids_attendu_a = reste
    poids_attendu_b = reste
    assert poids_attendu_a == poids_attendu_b

    source = Cell(
        cell_id=731,
        area_km2=0.0,
        population=pop_source,
        food_stock_kg=0.0,
        hunger_ticks=1,
        food_deficit_kg=pop_source * ration,
        migration_remainder=0.0,
    )
    dest_a = Cell(
        cell_id=732,
        area_km2=0.0,
        population=pop_dest_a,
        food_stock_kg=reste,
        hunger_ticks=0,
        food_deficit_kg=0.0,
        migration_remainder=0.0,
    )
    dest_b = Cell(
        cell_id=733,
        area_km2=0.0,
        population=pop_dest_b,
        food_stock_kg=reste,
        hunger_ticks=0,
        food_deficit_kg=0.0,
        migration_remainder=0.0,
    )
    world = World(
        cells={731: source, 732: dest_a, 733: dest_b},
        adjacency=[
            {"a": 731, "b": 732, "kind": "land", "shared_length_m": 1000.0},
            {"a": 731, "b": 733, "kind": "land", "shared_length_m": 1000.0},
        ],
    )
    penurie = pop_source * ration
    partants = int(pop_source * FRACTION_MIGRANTE_PAR_TICK)
    assert partants >= 2
    repartition_attendue = {732: partants // 2, 733: partants // 2}
    pops_avant = {cid: c.population for cid, c in world.cells.items()}
    stocks_avant = _paniers_monde(world)

    _apply_migration(world, {731: penurie, 732: 0.0, 733: 0.0})

    delta_a = world.cells[732].population - pops_avant[732]
    delta_b = world.cells[733].population - pops_avant[733]
    assert delta_a == repartition_attendue[732]
    assert delta_b == repartition_attendue[733]
    _verifier_sc5_conservation_paniers(world, pops_avant, stocks_avant)


def test_migration_pondération_selon_stock_post_consommation():
    """Répartition selon le rapport des stocks post-consommation."""
    from sim.constants import FRACTION_MIGRANTE_PAR_TICK
    from sim.engine import _apply_migration, _repartir_habitants_proportionnellement

    pop_source = 400
    ration = FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    reste_a = ration * 3
    reste_b = ration * 1
    partants = int(pop_source * FRACTION_MIGRANTE_PAR_TICK)
    assert partants >= 4
    poids = {742: reste_a, 743: reste_b}
    repartition_attendue = _repartir_habitants_proportionnellement(partants, poids)

    source = Cell(
        cell_id=741,
        area_km2=0.0,
        population=pop_source,
        food_stock_kg=0.0,
        hunger_ticks=1,
        food_deficit_kg=pop_source * ration,
        migration_remainder=0.0,
    )
    dest_a = Cell(
        cell_id=742,
        area_km2=0.0,
        population=60,
        food_stock_kg=reste_a,
        hunger_ticks=0,
        food_deficit_kg=0.0,
        migration_remainder=0.0,
    )
    dest_b = Cell(
        cell_id=743,
        area_km2=0.0,
        population=120,
        food_stock_kg=reste_b,
        hunger_ticks=0,
        food_deficit_kg=0.0,
        migration_remainder=0.0,
    )
    world = World(
        cells={741: source, 742: dest_a, 743: dest_b},
        adjacency=[
            {"a": 741, "b": 742, "kind": "land", "shared_length_m": 1000.0},
            {"a": 741, "b": 743, "kind": "land", "shared_length_m": 1000.0},
        ],
    )
    pops_avant = {cid: c.population for cid, c in world.cells.items()}
    stocks_avant = _paniers_monde(world)

    _apply_migration(world, {741: pop_source * ration, 742: 0.0, 743: 0.0})

    delta_a = world.cells[742].population - pops_avant[742]
    delta_b = world.cells[743].population - pops_avant[743]
    assert delta_a == repartition_attendue[742]
    assert delta_b == repartition_attendue[743]
    _verifier_sc5_conservation_paniers(world, pops_avant, stocks_avant)


def test_migration_invariance_ordre_aretes_reste_positif():
    """Inverser l'ordre des arêtes donne le même état."""
    from sim.engine import _apply_migration

    def _jouer(adjacency: list[dict]) -> dict[int, int]:
        pop_source = 200
        ration = FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
        reste = ration * 2
        source = Cell(
            cell_id=751,
            area_km2=0.0,
            population=pop_source,
            food_stock_kg=0.0,
            hunger_ticks=1,
            food_deficit_kg=pop_source * ration,
            migration_remainder=0.0,
        )
        dest_a = Cell(
            cell_id=752,
            area_km2=0.0,
            population=30,
            food_stock_kg=reste,
            hunger_ticks=0,
            food_deficit_kg=0.0,
            migration_remainder=0.0,
        )
        dest_b = Cell(
            cell_id=753,
            area_km2=0.0,
            population=80,
            food_stock_kg=reste,
            hunger_ticks=0,
            food_deficit_kg=0.0,
            migration_remainder=0.0,
        )
        world = World(cells={751: source, 752: dest_a, 753: dest_b}, adjacency=adjacency)
        _apply_migration(world, {751: pop_source * ration, 752: 0.0, 753: 0.0})
        return {cid: cell.population for cid, cell in world.cells.items()}

    edges_ab = [
        {"a": 751, "b": 752, "kind": "land", "shared_length_m": 1000.0},
        {"a": 751, "b": 753, "kind": "land", "shared_length_m": 1000.0},
    ]
    assert _jouer(edges_ab) == _jouer(list(reversed(edges_ab)))


# --- Lot 046 : la mer est un port commun ---

_NOEUD_MER = -1


def _compter_aretes_maritimes_carte(carte_doc: dict) -> int:
    """Dénominateur indépendant : arêtes dont exactement un bout est une cellule."""
    ids = {c["cell_id"] for c in carte_doc["cellules"]}
    compte = 0
    for edge in carte_doc["adjacence"]:
        a_in = edge["a"] in ids
        b_in = edge["b"] in ids
        if a_in != b_in:
            compte += 1
    return compte


def _monde_maritime_deux_ports(
    stock_source: float,
    stock_receveur: float,
    pop_receveur: int,
    longueur_m: float = 5000.0,
) -> World:
    """Deux cellules côtières sans arête terrestre entre elles."""
    from sim.model import ecrire_stock_marchandise

    source_id, receveur_id = 8001, 8002
    source = Cell(
        cell_id=source_id, area_km2=0.0, population=0,
        stocks={}, hunger_ticks=0, food_deficit_kg=0.0,
    )
    receveur = Cell(
        cell_id=receveur_id, area_km2=0.0, population=pop_receveur,
        stocks={}, hunger_ticks=0, food_deficit_kg=0.0,
    )
    ecrire_stock_marchandise(source, MARCHANDISE_NOURRITURE, stock_source)
    ecrire_stock_marchandise(receveur, MARCHANDISE_NOURRITURE, stock_receveur)
    adjacency = [
        {"a": source_id, "b": _NOEUD_MER, "kind": "land-sea", "shared_length_m": longueur_m},
        {"a": receveur_id, "b": _NOEUD_MER, "kind": "land-sea", "shared_length_m": longueur_m},
    ]
    return World(cells={source_id: source, receveur_id: receveur}, adjacency=adjacency)


def test_aretes_maritimes_derivees_de_la_carte():
    """SC1 — le moteur traite autant d'arêtes maritimes que la carte en porte."""
    from sim.engine import _aretes_maritimes_du_monde

    carte = World.lire_carte()
    monde = World.charger(0, carte_doc=carte)
    attendu = _compter_aretes_maritimes_carte(carte)
    total_aretes = len(carte["adjacence"])
    assert attendu > 0, "échantillon vide : aucune arête maritime dans la carte"
    assert len(_aretes_maritimes_du_monde(monde)) == attendu
    assert attendu <= total_aretes


def test_pas_de_kind_litteral_dans_engine():
    """SC1 — aucun nom de kind en littéral de comparaison dans engine.py."""
    import pathlib

    texte = (pathlib.Path(__file__).parent.parent / "engine.py").read_text(encoding="utf-8")
    assert "land-sea" not in texte
    assert "land-land" not in texte


def test_port_surplus_expedie_port_manque_debarque():
    """SC2 — surplus expédie vers le bassin ; manque puise au tick suivant."""
    from sim.model import lire_stock_marchandise
    from sim.world import lire_stock_mer, ecrire_stock_mer

    pop = 50
    besoin = pop * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    world = _monde_maritime_deux_ports(besoin * 2, 0.0, pop)
    source_id, receveur_id = 8001, 8002
    stock_source_avant = lire_stock_marchandise(world.cells[source_id], MARCHANDISE_NOURRITURE)
    bassin_avant = lire_stock_mer(world, MARCHANDISE_NOURRITURE)

    _apply_commerce(world, [0.0])

    stock_source_apres = lire_stock_marchandise(world.cells[source_id], MARCHANDISE_NOURRITURE)
    bassin_apres = lire_stock_mer(world, MARCHANDISE_NOURRITURE)
    delta_source = stock_source_avant - stock_source_apres
    delta_bassin = bassin_apres - (bassin_avant if bassin_avant >= 0 else 0.0)
    assert delta_source > 0.0
    assert abs(delta_source - delta_bassin) <= TOLERANCE

    stock_receveur_avant = lire_stock_marchandise(world.cells[receveur_id], MARCHANDISE_NOURRITURE)
    bassin_avant_t2 = lire_stock_mer(world, MARCHANDISE_NOURRITURE)
    _apply_commerce(world, [0.0])
    stock_receveur_apres = lire_stock_marchandise(world.cells[receveur_id], MARCHANDISE_NOURRITURE)
    bassin_apres_t2 = lire_stock_mer(world, MARCHANDISE_NOURRITURE)
    delta_receveur = stock_receveur_apres - stock_receveur_avant
    delta_bassin_t2 = (bassin_avant_t2 if bassin_avant_t2 >= 0 else 0.0) - (
        bassin_apres_t2 if bassin_apres_t2 >= 0 else 0.0
    )
    assert delta_receveur > 0.0
    assert abs(delta_receveur - delta_bassin_t2) <= TOLERANCE


def test_grain_embarque_t_non_debarque_t():
    """SC3 — ce qui embarque à t n'est pas débarqué avant t+1."""
    from sim.model import lire_stock_marchandise
    from sim.world import ecrire_stock_mer

    pop = 50
    besoin = pop * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    world = _monde_maritime_deux_ports(besoin * 3, 0.0, pop)
    receveur_id = 8002
    ecrire_stock_mer(world, MARCHANDISE_NOURRITURE, 0.0)

    _apply_commerce(world, [0.0])
    stock_tick1 = lire_stock_marchandise(world.cells[receveur_id], MARCHANDISE_NOURRITURE)
    assert stock_tick1 == 0.0

    _apply_commerce(world, [0.0])
    stock_tick2 = lire_stock_marchandise(world.cells[receveur_id], MARCHANDISE_NOURRITURE)
    assert stock_tick2 > 0.0


def _masse_totale_avec_bassin(world: World) -> float:
    from sim.model import lire_stock_marchandise
    from sim.world import lire_stock_mer

    total = sum(
        max(0.0, lire_stock_marchandise(c, MARCHANDISE_NOURRITURE))
        for c in world.cells.values()
    )
    bassin = lire_stock_mer(world, MARCHANDISE_NOURRITURE)
    if bassin >= 0:
        total += bassin
    return total


def test_conservation_masse_avec_bassin():
    """SC4 — masse conservée, cellules + bassin, à chaque tick commerce."""
    pop = 50
    besoin = pop * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    world = _monde_maritime_deux_ports(besoin * 2, 0.0, pop)
    masse_avant = _masse_totale_avec_bassin(world)
    for _ in range(3):
        _apply_commerce(world, [0.0])
        masse_apres = _masse_totale_avec_bassin(world)
        assert abs(masse_apres - masse_avant) <= TOLERANCE


def _cellules_sans_voisin_terrestre_mais_maritimes(carte_doc: dict) -> set[int]:
    ids = {c["cell_id"] for c in carte_doc["cellules"]}
    deg_terre = {cid: 0 for cid in ids}
    a_mer = set()
    for edge in carte_doc["adjacence"]:
        a_in = edge["a"] in ids
        b_in = edge["b"] in ids
        if a_in and b_in:
            deg_terre[edge["a"]] += 1
            deg_terre[edge["b"]] += 1
        elif a_in or b_in:
            cid = edge["a"] if a_in else edge["b"]
            a_mer.add(cid)
    return {cid for cid in ids if deg_terre[cid] == 0 and cid in a_mer}


def test_cellules_hermetiques_ont_capacite_quai():
    """SC5 — cellules sans voisin terrestre mais avec mer : quai > 0 sauf façade nulle."""
    from sim.engine import _capacite_quai_cellule_kg, _aretes_maritimes_du_monde

    carte = World.lire_carte()
    ensemble = _cellules_sans_voisin_terrestre_mais_maritimes(carte)
    assert len(ensemble) > 0, "échantillon vide"
    monde = World.charger(0, carte_doc=carte)
    aretes = _aretes_maritimes_du_monde(monde)
    par_cellule: dict[int, list] = {}
    for cell_id, noeud, edge in aretes:
        par_cellule.setdefault(cell_id, []).append((cell_id, noeud, edge))
    zero_mesure = 0
    positifs = 0
    for cid in sorted(ensemble):
        cap = _capacite_quai_cellule_kg(monde, cid, par_cellule.get(cid, []))
        if cap == 0.0:
            zero_mesure += 1
        else:
            positifs += 1
            assert cap > 0.0
    assert positifs + zero_mesure == len(ensemble)
    assert positifs > 0


def _longueurs_facade_maritime_carte() -> tuple[float, float, float]:
    import statistics

    carte = World.lire_carte()
    ids = {c["cell_id"] for c in carte["cellules"]}
    longueurs = sorted(
        float(e["shared_length_m"])
        for e in carte["adjacence"]
        if (e["a"] in ids) != (e["b"] in ids)
        and "shared_length_m" in e
    )
    return min(longueurs), statistics.median(longueurs), max(longueurs)


def test_debarquement_proportionnel_aux_facades():
    """SC6 — débarquement dans le rapport des longueurs de façade."""
    from sim import constants as k
    from sim.model import ecrire_stock_marchandise, lire_stock_marchandise
    from sim.world import ecrire_stock_mer

    courte, mediane, longue = _longueurs_facade_maritime_carte()
    cap_longue = k.debit_maritime_kg_par_km() * (longue / k.metres_par_km())
    # Besoin supérieur à toute capacité de quai : seule la façade borne le débit.
    pop = int(cap_longue / FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK) + 1
    besoin = pop * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    bassin_stock = cap_longue * len((courte, mediane, longue)) * 10
    source_id = 8100
    cells = {}
    adjacency = []
    for idx, (nom, longueur) in enumerate(
        (("c", courte), ("m", mediane), ("l", longue))
    ):
        cid = source_id + idx + 1
        cells[cid] = Cell(
            cell_id=cid, area_km2=0.0, population=pop,
            stocks={}, hunger_ticks=0, food_deficit_kg=0.0,
        )
        adjacency.append(
            {"a": cid, "b": _NOEUD_MER, "kind": "land-sea", "shared_length_m": longueur},
        )
    world = World(cells=cells, adjacency=adjacency)
    ecrire_stock_mer(world, MARCHANDISE_NOURRITURE, bassin_stock)
    _apply_commerce(world, [0.0])
    debars = []
    for cid in sorted(cells):
        stock = lire_stock_marchandise(world.cells[cid], MARCHANDISE_NOURRITURE)
        debars.append(stock if stock >= 0 else 0.0)
    assert debars[0] > 0.0 and debars[2] > debars[1] > debars[0]
    rapport_tm = debars[1] / debars[0]
    rapport_lm = debars[2] / debars[0]
    assert abs(rapport_tm - mediane / courte) / (mediane / courte) <= 0.05
    assert abs(rapport_lm - longue / courte) / (longue / courte) <= 0.05


def test_relief_compose_capacite_quai_sans_second_jeu():
    """SC7 — relief compose la capacité de quai ; pas de second jeu de facteurs."""
    import ast
    from pathlib import Path
    from sim import constants as k
    from sim.engine import _capacite_quai_cellule_kg

    carte_doc = World.lire_carte()
    ids = {c["cell_id"] for c in carte_doc["cellules"]}
    reliefs_presents = {
        c["relief"] for c in carte_doc["cellules"] if c.get("relief") is not None
    }
    attendues = set(k.facteurs_transport_par_relief())
    manquantes = attendues - reliefs_presents
    assert not manquantes, f"classes de relief absentes : {sorted(manquantes)}"

    facteurs = k.facteurs_transport_par_relief()
    classes = sorted(attendues, key=lambda r: facteurs[r], reverse=True)
    relief_a, relief_b = classes[0], classes[-1]
    longueur = 5000.0
    cell_a, cell_b = 8201, 8202
    carte = {
        cell_a: {"cell_id": cell_a, "relief": relief_a},
        cell_b: {"cell_id": cell_b, "relief": relief_b},
    }
    edge_tpl = {"b": _NOEUD_MER, "kind": "land-sea", "shared_length_m": longueur}
    world = World(
        cells={
            cell_a: Cell(cell_id=cell_a, area_km2=0.0, population=0, stocks={}),
            cell_b: Cell(cell_id=cell_b, area_km2=0.0, population=0, stocks={}),
        },
        adjacency=[
            {"a": cell_a, **edge_tpl},
            {"a": cell_b, **edge_tpl},
        ],
        carte=carte,
    )
    aretes_a = [(cell_a, _NOEUD_MER, world.adjacency[0])]
    aretes_b = [(cell_b, _NOEUD_MER, world.adjacency[1])]
    cap_a = _capacite_quai_cellule_kg(world, cell_a, aretes_a)
    cap_b = _capacite_quai_cellule_kg(world, cell_b, aretes_b)
    assert cap_a > cap_b + TOLERANCE

    sim_dir = Path(__file__).resolve().parents[1]
    definitions = []
    for py_file in sim_dir.glob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == "facteurs_transport_par_relief":
                definitions.append(py_file.name)
    assert definitions == ["constants.py"]


def test_refus_longueur_facade_maritime_invalide():
    """SC8 — longueur non numérique : erreur nommant cellule et nœud mer."""
    import math
    from sim.engine import LongueurFacadeMaritimeInvalideError

    cell_id = 8301
    world = World(
        cells={cell_id: Cell(cell_id=cell_id, area_km2=0.0, population=0, stocks={})},
        adjacency=[{"a": cell_id, "b": _NOEUD_MER, "kind": "land-sea", "shared_length_m": 1000.0}],
    )
    for invalide in ("texte", None, float("nan")):
        world.adjacency[0]["shared_length_m"] = invalide
        with pytest.raises(LongueurFacadeMaritimeInvalideError, match=str(cell_id)):
            _apply_commerce(world, [0.0])
        with pytest.raises(LongueurFacadeMaritimeInvalideError, match=str(_NOEUD_MER)):
            _apply_commerce(world, [0.0])


def test_refus_longueur_facade_maritime_absente():
    """SC8 — longueur absente : erreur, pas de repli terrestre."""
    from sim.engine import LongueurFacadeMaritimeInvalideError

    cell_id = 8302
    world = World(
        cells={cell_id: Cell(cell_id=cell_id, area_km2=0.0, population=0, stocks={})},
        adjacency=[{"a": cell_id, "b": _NOEUD_MER, "kind": "land-sea"}],
    )
    with pytest.raises(LongueurFacadeMaritimeInvalideError, match=str(cell_id)):
        _apply_commerce(world, [0.0])


def test_refus_noeuds_mer_multiples():
    """SC8 — plusieurs nœuds hors monde : erreur nommant les identifiants."""
    from sim.engine import NoeudsMerMultiplesError

    cell_id = 8303
    world = World(
        cells={cell_id: Cell(cell_id=cell_id, area_km2=0.0, population=0, stocks={})},
        adjacency=[
            {"a": cell_id, "b": -1, "kind": "land-sea", "shared_length_m": 1000.0},
            {"a": cell_id, "b": -2, "kind": "land-sea", "shared_length_m": 1000.0},
        ],
    )
    with pytest.raises(NoeudsMerMultiplesError, match="-1"):
        _apply_commerce(world, [0.0])
    with pytest.raises(NoeudsMerMultiplesError, match="-2"):
        _apply_commerce(world, [0.0])


def test_refus_kinds_maritimes_multiples():
    """SC8 — plusieurs kind sur arêtes maritimes : erreur nommant les valeurs."""
    from sim.engine import KindsMaritimesMultiplesError

    a_id, b_id = 8304, 8305
    world = World(
        cells={
            a_id: Cell(cell_id=a_id, area_km2=0.0, population=0, stocks={}),
            b_id: Cell(cell_id=b_id, area_km2=0.0, population=0, stocks={}),
        },
        adjacency=[
            {"a": a_id, "b": _NOEUD_MER, "kind": "land-sea", "shared_length_m": 1000.0},
            {"a": b_id, "b": _NOEUD_MER, "kind": "autre-kind", "shared_length_m": 1000.0},
        ],
    )
    with pytest.raises(KindsMaritimesMultiplesError, match="land-sea"):
        _apply_commerce(world, [0.0])
    with pytest.raises(KindsMaritimesMultiplesError, match="autre-kind"):
        _apply_commerce(world, [0.0])


def test_monde_sans_stocks_mer_inchange():
    """SC8 — sans stocks_mer : tick commerce identique au comportement terrestre."""
    pop = 50
    besoin = pop * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    adjacency = [{"a": 8401, "b": 8402, "kind": "land", "shared_length_m": 5000.0}]

    def _monde(avec_mer: bool) -> World:
        source = Cell(
            cell_id=8401, area_km2=0.0, population=0,
            food_stock_kg=besoin, hunger_ticks=0, food_deficit_kg=0.0,
        )
        receveur = Cell(
            cell_id=8402, area_km2=0.0, population=pop,
            food_stock_kg=0.0, hunger_ticks=0, food_deficit_kg=besoin,
        )
        world = World(cells={8401: source, 8402: receveur}, adjacency=adjacency)
        if not avec_mer:
            del world.stocks_mer
        return world

    w1 = _monde(avec_mer=True)
    w2 = _monde(avec_mer=False)
    total1, total2 = [0.0], [0.0]
    _apply_commerce(w1, total1)
    _apply_commerce(w2, total2)
    assert w1.cells[8401].food_stock_kg == w2.cells[8401].food_stock_kg
    assert w1.cells[8402].food_stock_kg == w2.cells[8402].food_stock_kg
    assert total1[0] == total2[0]


def test_refus_maritimes_compteur_mutations():
    """SC8 — chaque cas de refus est essayé ; le compteur dérive des mutations."""
    from sim.engine import (
        KindsMaritimesMultiplesError,
        LongueurFacadeMaritimeInvalideError,
        NoeudsMerMultiplesError,
    )

    refus = 0
    cell_id = 8310
    for invalide in ("texte", None, float("nan")):
        monde = World(
            cells={cell_id: Cell(cell_id=cell_id, area_km2=0.0, population=0, stocks={})},
            adjacency=[{"a": cell_id, "b": _NOEUD_MER, "kind": "land-sea", "shared_length_m": invalide}],
        )
        with pytest.raises(LongueurFacadeMaritimeInvalideError):
            _apply_commerce(monde, [0.0])
        refus += 1

    monde_absent = World(
        cells={cell_id: Cell(cell_id=cell_id, area_km2=0.0, population=0, stocks={})},
        adjacency=[{"a": cell_id, "b": _NOEUD_MER, "kind": "land-sea"}],
    )
    with pytest.raises(LongueurFacadeMaritimeInvalideError):
        _apply_commerce(monde_absent, [0.0])
    refus += 1

    monde_noeuds = World(
        cells={cell_id: Cell(cell_id=cell_id, area_km2=0.0, population=0, stocks={})},
        adjacency=[
            {"a": cell_id, "b": -1, "kind": "land-sea", "shared_length_m": 1000.0},
            {"a": cell_id, "b": -2, "kind": "land-sea", "shared_length_m": 1000.0},
        ],
    )
    with pytest.raises(NoeudsMerMultiplesError):
        _apply_commerce(monde_noeuds, [0.0])
    refus += 1

    monde_kinds = World(
        cells={
            8311: Cell(cell_id=8311, area_km2=0.0, population=0, stocks={}),
            8312: Cell(cell_id=8312, area_km2=0.0, population=0, stocks={}),
        },
        adjacency=[
            {"a": 8311, "b": _NOEUD_MER, "kind": "land-sea", "shared_length_m": 1000.0},
            {"a": 8312, "b": _NOEUD_MER, "kind": "autre-kind", "shared_length_m": 1000.0},
        ],
    )
    with pytest.raises(KindsMaritimesMultiplesError):
        _apply_commerce(monde_kinds, [0.0])
    refus += 1

    assert refus == 6


def _kg_transportes_sim(ticks: int, seed: int, sans_mer: bool = False) -> float:
    import random
    from sim import constants as k

    monde = World.charger(seed)
    if sans_mer:
        del monde.stocks_mer
    rng = random.Random(seed)
    total = 0.0
    for numero in range(ticks):
        total += tick(monde, rng, numero_tick=numero)
    return total


def test_kg_transportes_augmente_avec_mer():
    """SC9 — le monde réel transporte davantage qu'un monde sans bassin."""
    from sim.constants import DEFAULT_CLI_SEED, DEFAULT_CLI_TICKS

    kg_avec = _kg_transportes_sim(DEFAULT_CLI_TICKS, DEFAULT_CLI_SEED, sans_mer=False)
    kg_sans = _kg_transportes_sim(DEFAULT_CLI_TICKS, DEFAULT_CLI_SEED, sans_mer=True)
    assert kg_avec > kg_sans


def test_debit_maritime_via_fonction_pas_constante_dans_engine():
    """SC10 — DEBIT_KG_PAR_KM_DE_COTE_PAR_TICK absent des lectures directes du moteur."""
    import ast
    from pathlib import Path

    engine_file = Path(__file__).parent.parent / "engine.py"
    tree = ast.parse(engine_file.read_text(encoding="utf-8"), filename=str(engine_file))
    import sim.constants as _k

    numeriques = {
        nom for nom in dir(_k)
        if nom.isupper() and isinstance(getattr(_k, nom), (int, float))
    }
    lues = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and node.attr in numeriques
        and not isinstance(node.ctx, ast.Store)
    }
    assert len(lues) > 0
    assert "DEBIT_KG_PAR_KM_DE_COTE_PAR_TICK" not in lues
    appels = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "_constantes"
    }
    assert "debit_maritime_kg_par_km" in appels


def test_bassin_jamais_ecrit_est_sentinelle_pas_zero():
    """Un bassin vide n'est pas un stock à zéro : la sentinelle -1 se déclare."""
    from sim.world import ecrire_stock_mer, lire_stock_mer

    world = World(cells={}, adjacency=[])
    assert lire_stock_mer(world, MARCHANDISE_NOURRITURE) == -1.0
    ecrire_stock_mer(world, MARCHANDISE_NOURRITURE, 0.0)
    assert lire_stock_mer(world, MARCHANDISE_NOURRITURE) == 0.0
    assert lire_stock_mer(world, MARCHANDISE_NOURRITURE) != -1.0
    assert lire_stock_mer(world, "minerai-inconnu") == -1.0


# Migration maritime : les îles sans route terrestre peuvent être quittées.
def _monde_migration_mer(stocks, aretes):
    import math
    from sim import constants as c
    population = math.ceil(12 / c.FRACTION_MIGRANTE_PAR_TICK)
    return World({cid: Cell(cid, 1.0, population, food_stock_kg=stock,
                           migration_remainder=0.0) for cid, stock in stocks.items()}, aretes)


def test_migration_mer_proportions_conservation_et_ordre():
    import copy
    from sim.engine import _apply_migration
    from sim import constants as c
    aretes = [{'a': cid, 'b': -100, 'kind': 'bassin'} for cid in (1, 2, 3)]
    a = _monde_migration_mer({1: 0, 2: 10, 3: 30}, aretes)
    b = copy.deepcopy(a)
    b.cells = dict(reversed(list(b.cells.items())))
    b.adjacency.reverse()
    avant = copy.deepcopy(a.to_dict())
    a.stocks_mer = {'nourriture': 29.0}
    b.stocks_mer = dict(a.stocks_mer)
    population = a.cells[1].population
    partants = int(population * c.FRACTION_MIGRANTE_PAR_TICK)
    for world in (a, b):
        _apply_migration(world, {1: 1.0})
    assert a.cells[1].population == population - partants
    assert a.cells[2].population == population + partants // 4
    assert a.cells[3].population == population + partants - partants // 4
    assert sum(cell.population for cell in a.cells.values()) == population * len(a.cells)
    assert a.to_dict() == b.to_dict()
    assert a.stocks_mer == b.stocks_mer == {'nourriture': 29.0}
    for cid, cell in a.to_dict()['cells'].items():
        for champ, valeur in cell.items():
            if champ not in ('population', 'migration_remainder'):
                assert valeur == avant['cells'][cid][champ]


def test_migration_mer_terre_presente_interdit_repli():
    from sim.engine import _apply_migration
    world = _monde_migration_mer({1: 0, 2: 0, 3: 30}, [
        {'a': 1, 'b': 2}, {'a': 1, 'b': -100}, {'a': 3, 'b': -100}])
    avant = [c.population for c in world.cells.values()]
    for _ in range(5):
        _apply_migration(world, {1: 1.0})
    assert [c.population for c in world.cells.values()] == avant


def test_migration_mer_atomicite_arrivee_bloque_depart_terrestre():
    from sim.engine import _apply_migration
    world = _monde_migration_mer({1: 0, 2: 1, 3: 30}, [
        {'a': 1, 'b': -100}, {'a': 2, 'b': -100}, {'a': 2, 'b': 3}])
    population = world.cells[1].population
    _apply_migration(world, {1: 1.0, 2: 1.0})
    assert world.cells[1].population < population
    assert world.cells[2].population > population
    assert world.cells[3].population == population
    assert sum(c.population for c in world.cells.values()) == population * len(world.cells)


@pytest.mark.parametrize('aretes,stocks', [([], {1: 0}),
    ([{'a': 1, 'b': -100}], {1: 1}),
    ([{'a': 1, 'b': -100}, {'a': 2, 'b': -100}], {1: 0, 2: 0})])
def test_migration_mer_sans_autre_port_en_surplus(aretes, stocks):
    from sim.engine import _apply_migration
    world = _monde_migration_mer(stocks, aretes)
    avant = [c.population for c in world.cells.values()]
    _apply_migration(world, {1: 1.0})
    assert [c.population for c in world.cells.values()] == avant


@pytest.mark.parametrize('second,erreur', [
    ({'a': 2, 'b': -101, 'kind': 'mer'}, 'NoeudsMerMultiplesError'),
    ({'a': 2, 'b': -100, 'kind': 'autre'}, 'KindsMaritimesMultiplesError')])
def test_migration_mer_refus_avant_toute_mutation(second, erreur):
    import copy
    from sim import engine
    world = _monde_migration_mer({1: 0, 2: 30}, [{'a': 1, 'b': -100, 'kind': 'mer'}, second])
    world.stocks_mer = {'nourriture': 42.0}
    avant = copy.deepcopy(vars(world))
    with pytest.raises(getattr(engine, erreur)):
        engine._apply_migration(world, {1: 1.0})
    assert vars(world) == avant


def test_migration_mer_determinisme_trente_ticks():
    import json
    from sim.__main__ import run
    assert json.dumps(run(30, 0), sort_keys=True) == json.dumps(run(30, 0), sort_keys=True)
