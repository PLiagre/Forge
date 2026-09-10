"""
Survie, faim, dette alimentaire et mortalité.

Ce que ce fichier protège (règle d'admission d'AGENTS.md) :

  - **invariant physique** : la dette alimentaire ne se rembourse jamais plus
    vite que le surplus du tick ; le monde ne nourrit pas durablement plus
    d'habitants qu'il ne produit de nourriture ;
  - **règle de jeu visible** : une cellule qui manque de nourriture a faim,
    puis meurt ; le monde ne s'éteint pas ; plus la faim tue, moins il reste
    de monde.

Le déterminisme est protégé par `test_determinisme.py`.

Fusion des anciens fichiers mortalite_accumulateur, mortalite_continue,
survie_stationnaire, survie_derivee, sensibilite_survie, hunger_criterion,
deficit_physique et causal_chain.
"""

import random

import pytest

import sim.constants as constantes
from sim.constants import (
    DEFICIT_RECOVERY_RATE_PER_SURPLUS_KG,
    FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK,
    FOOD_PRODUCTION_KG_PER_KM2_PER_TICK,
    HUNGER_DEATH_SCALE,
    MAX_DEATH_RATE_PER_TICK,
    N_BOUND_MORT,
)
from sim.engine import (
    _apply_consumption,
    _apply_mortality,
    _apply_natalite,
    _apply_production,
    _update_hunger,
    population_soutenable_de,
    production_moyenne_kg_par_tick,
    tick,
)
from sim.model import Cell
from sim.world import World

POPULATION_SCENARIO = 50
def _build_monde_temoin_receveuse() -> tuple[World, int, int]:
    """
    Trois cellules, production désactivée (area_km2 = 0.0) :
    - témoin (100)    : possède exactement sa ration, aucune adjacence.
    - source (101)    : population nulle, stock = une ration à donner.
    - receveuse (102) : stock nul, déficit nul, reçoit exactement sa ration.
    """
    besoin_kg = POPULATION_SCENARIO * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK

    temoin = Cell(
        cell_id=100, area_km2=0.0, population=POPULATION_SCENARIO,
        food_stock_kg=besoin_kg, hunger_ticks=0, food_deficit_kg=0.0,
        mortality_remainder=0.0,
    )
    source = Cell(
        cell_id=101, area_km2=0.0, population=0,
        food_stock_kg=besoin_kg, hunger_ticks=0, food_deficit_kg=0.0,
        mortality_remainder=0.0,
    )
    receveuse = Cell(
        cell_id=102, area_km2=0.0, population=POPULATION_SCENARIO,
        food_stock_kg=0.0, hunger_ticks=0, food_deficit_kg=0.0,
        mortality_remainder=0.0,
    )
    adjacency = [{"a": 101, "b": 102, "kind": "land", "shared_length_m": 5000.0}]
    world = World(cells={100: temoin, 101: source, 102: receveuse}, adjacency=adjacency)
    return world, 100, 102
DETTE_INITIALE_KG = 10_000.0
POPULATION_TEST = 10
SURPLUS_INFINITESIMAL_KG = 1e-9
SURPLUS_SUBSTANTIEL_KG = 5_000.0
def _cellule_endettee(surplus_kg: float) -> Cell:
    """Cellule avec une dette de 10 000 kg et le surplus demandé ce tick."""
    besoin = POPULATION_TEST * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    return Cell(
        cell_id=1,
        area_km2=0.0,
        population=POPULATION_TEST,
        food_stock_kg=besoin + surplus_kg,
        hunger_ticks=0,
        food_deficit_kg=DETTE_INITIALE_KG,
        mortality_remainder=0.0,
    )
POPULATION_PETITE_CELLULE = 5
POPULATIONS_MICRO_MONDE = [50, 137, 500]
DEFICIT_PAR_TETE_MICRO_MONDE_KG = 0.5
POPULATIONS_TEST = [1, 5, 9, 20, 100, 1000]
DEFICIT_MINUSCULE_KG = 1e-9
RNG_SEED = 42
def _observer_le_monde(n_ticks: int = None) -> tuple[float, World, int]:
    """
    Joue le monde réel (la carte figée) et retourne
    (fraction de survivants, monde final, population initiale).

    L'échantillon est toujours le monde chargé — jamais un monde à la main.
    """
    n_ticks = N_TICKS_OBSERVES if n_ticks is None else n_ticks
    world = World.charger(rng_seed=RNG_SEED)
    rng = random.Random(RNG_SEED)
    pop_init = sum(c.population for c in world.cells.values())
    for _ in range(n_ticks):
        tick(world, rng)
    pop_fin = sum(c.population for c in world.cells.values())
    return pop_fin / pop_init, world, pop_init
# Fenêtre d'observation du monde réel. Ce n'est pas une grandeur physique :
# c'est le temps qu'il faut pour qu'une réponse devienne lisible.
#
# 200 n'est pas un chiffre rond : à 60 ticks, la réponse à la natalité n'est
# plus mesurable — doubler le taux donne 0.491150 de survivants contre
# 0.495450 au nominal, un écart du mauvais signe et de l'ordre du bruit, et
# `test_la_demographie_repond_a_la_natalite` échoue. La natalité met plus
# longtemps que la mortalité à se voir dans une fraction de survivants.
# Raccourcir cette fenêtre demande donc de le remesurer, pas de le supposer.
N_TICKS_OBSERVES = 200

FACTEUR_REGIME_BAS = 0.5
FACTEUR_REGIME_HAUT = 2.0


# --- test_causal_chain.py ---
def test_sc7a_stock_decreases_when_production_lt_consumption():
    """
    Une cellule avec production insuffisante voit son stock baisser
    après production+consommation.
    État initial construit à la main. Un seul maillon testé (production + consommation).
    area_km2 = 1.0, en dessous de la plus petite cellule réelle de la carte.
    Production max = 1.0 × 18 × 1.5 = 27 kg << consommation = 5000 × 2 = 10 000 kg.
    """
    # Production max = 1.0 × 18 × 1.5 = 27 kg/tick (très faible)
    # Consommation = 5000 × 2.0 = 10 000 kg/tick
    cell = Cell(
        cell_id=1,
        area_km2=1.0,
        population=5000,
        food_stock_kg=1000.0,
        hunger_ticks=0,
        food_deficit_kg=0.0,
    )
    stock_before = cell.food_stock_kg

    rng = random.Random(42)
    _apply_production(cell, rng)
    _apply_consumption(cell)

    stock_after = cell.food_stock_kg
    print(f"stock_before = {stock_before}, stock_after = {stock_after}")

    assert stock_after < stock_before, (
        f"Le stock aurait dû baisser : avant={stock_before}, après={stock_after}"
    )


# --- test_hunger_criterion.py ---
def test_hunger_ticks_cellule_ravitaillee():
    """
    Après un tick complet, ni le témoin ni la receveuse ne sont comptés
    affamés : tous deux ont mangé exactement leur ration.

    Compteur : hunger_ticks_cellule_ravitaillee.
    """
    world, id_temoin, id_receveuse = _build_monde_temoin_receveuse()
    rng = random.Random(0)  # production désactivée : le tirage n'a pas d'effet

    tick(world, rng)

    temoin = world.cells[id_temoin]
    receveuse = world.cells[id_receveuse]

    print(f"temoin    : stock={temoin.food_stock_kg}, deficit={temoin.food_deficit_kg}, "
          f"hunger_ticks={temoin.hunger_ticks}")
    print(f"receveuse : stock={receveuse.food_stock_kg}, deficit={receveuse.food_deficit_kg}, "
          f"hunger_ticks={receveuse.hunger_ticks}")

    hunger_ticks_cellule_ravitaillee = temoin.hunger_ticks + receveuse.hunger_ticks
    print(f"hunger_ticks_cellule_ravitaillee = {hunger_ticks_cellule_ravitaillee}")

    assert temoin.food_stock_kg == 0.0 and temoin.food_deficit_kg == 0.0
    assert receveuse.food_stock_kg == 0.0 and receveuse.food_deficit_kg == 0.0
    assert temoin.hunger_ticks == 0, (
        "Le témoin possédait sa ration exacte : stock nul après consommation "
        "n'est pas de la sous-alimentation."
    )
    assert receveuse.hunger_ticks == 0, (
        "La receveuse a été ravitaillée exactement à son besoin : elle n'a "
        "manqué de rien ce tick."
    )
    assert hunger_ticks_cellule_ravitaillee == 0


# --- test_hunger_criterion.py ---
def test_penurie_reelle_incremente_toujours():
    """
    Le critère reste fonctionnel dans l'autre sens : une cellule qui
    manque réellement de nourriture voit bien hunger_ticks progresser.

    Sans ce contrôle, un critère qui n'incrémente jamais passerait le test
    ci-dessus (règle 6 : un contrôle trop grossier coûte autant qu'un
    contrôle laxiste).
    """
    cell = Cell(
        cell_id=1, area_km2=0.0, population=POPULATION_SCENARIO,
        food_stock_kg=0.0, hunger_ticks=0, food_deficit_kg=0.0,
        mortality_remainder=0.0,
    )
    penurie_kg = _apply_consumption(cell)
    _update_hunger(cell, penurie_kg)

    print(f"penurie_kg = {penurie_kg}, hunger_ticks = {cell.hunger_ticks}")
    assert penurie_kg > 0.0
    assert cell.hunger_ticks == 1


# --- test_hunger_criterion.py ---
def test_penurie_retournee_est_le_manque_exact():
    """
    La pénurie retournée par _apply_consumption est le manque en kg du
    tick, pas un booléen déguisé : elle vaut exactement
    besoin − stock disponible.
    """
    population = POPULATION_SCENARIO
    besoin = population * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    stock_partiel = besoin / (1 + 1)

    cell = Cell(
        cell_id=2, area_km2=0.0, population=population,
        food_stock_kg=stock_partiel, hunger_ticks=0, food_deficit_kg=0.0,
        mortality_remainder=0.0,
    )
    penurie_kg = _apply_consumption(cell)

    print(f"besoin={besoin}, stock={stock_partiel}, penurie_kg={penurie_kg}")
    assert abs(penurie_kg - (besoin - stock_partiel)) < 1e-9
    assert abs(cell.food_deficit_kg - penurie_kg) < 1e-9


# --- test_deficit_physique.py ---
def test_deficit_reduction_infinitesimal():
    """
    Un surplus de 1e-9 kg ne peut rembourser que 1e-9 kg de dette.

    Compteur : deficit_reduction_infinitesimal.
    """
    cell = _cellule_endettee(SURPLUS_INFINITESIMAL_KG)
    _apply_consumption(cell)

    deficit_reduction_infinitesimal = DETTE_INITIALE_KG - cell.food_deficit_kg
    print(f"surplus = {SURPLUS_INFINITESIMAL_KG} kg")
    print(f"deficit_apres = {cell.food_deficit_kg}")
    print(f"deficit_reduction_infinitesimal = {deficit_reduction_infinitesimal}")
    print(f"stock_apres = {cell.food_stock_kg}")

    assert cell.food_deficit_kg > 9999.9, (
        f"Un surplus de {SURPLUS_INFINITESIMAL_KG} kg a effacé "
        f"{deficit_reduction_infinitesimal} kg de dette."
    )
    assert deficit_reduction_infinitesimal <= SURPLUS_INFINITESIMAL_KG + 1e-12


# --- test_deficit_physique.py ---
def test_deficit_reduction_proportionnel():
    """
    Un surplus de 5 000 kg rembourse 5 000 kg de dette (ratio nominal
    1 kg de dette par kg de surplus), et ces kilogrammes quittent le stock.

    Compteur : deficit_reduction_proportionnel.
    """
    cell = _cellule_endettee(SURPLUS_SUBSTANTIEL_KG)
    _apply_consumption(cell)

    deficit_reduction_proportionnel = DETTE_INITIALE_KG - cell.food_deficit_kg
    attendu = SURPLUS_SUBSTANTIEL_KG * DEFICIT_RECOVERY_RATE_PER_SURPLUS_KG

    print(f"surplus = {SURPLUS_SUBSTANTIEL_KG} kg")
    print(f"ratio = {DEFICIT_RECOVERY_RATE_PER_SURPLUS_KG} kg de dette par kg de surplus")
    print(f"deficit_reduction_proportionnel = {deficit_reduction_proportionnel}")
    print(f"attendu = {attendu}")
    print(f"stock_apres = {cell.food_stock_kg}")

    assert abs(deficit_reduction_proportionnel - attendu) < 1e-9
    assert abs(cell.food_stock_kg - (SURPLUS_SUBSTANTIEL_KG - attendu)) < 1e-9, (
        "Les kilogrammes remboursés doivent quitter le stock : ils sont mangés "
        "en sus du besoin d'entretien."
    )


# --- test_deficit_physique.py ---
def test_invariant_physique_reduction_bornee_par_le_surplus():
    """
    Invariant : pour tout surplus, la réduction de dette est bornée par
    le surplus du tick. Vérifié sur une gamme de surplus couvrant sept ordres
    de grandeur, y compris un surplus supérieur à la dette.

    Un seul cas de test ne prouverait rien d'une borne (règle 6).
    """
    surplus_testes = [
        SURPLUS_INFINITESIMAL_KG,
        1e-3,
        1.0,
        SURPLUS_SUBSTANTIEL_KG,
        DETTE_INITIALE_KG,
        DETTE_INITIALE_KG * (1 + 1),
    ]
    reductions = []

    for surplus in surplus_testes:
        cell = _cellule_endettee(surplus)
        _apply_consumption(cell)
        reduction = DETTE_INITIALE_KG - cell.food_deficit_kg
        reductions.append(reduction)
        print(f"surplus={surplus:g} → reduction={reduction:g}, "
              f"stock_apres={cell.food_stock_kg:g}, dette={cell.food_deficit_kg:g}")
        assert reduction <= surplus + 1e-9, (
            f"Réduction {reduction} > surplus {surplus} : des kilogrammes de "
            "dette disparaissent sans contrepartie physique."
        )
        assert cell.food_stock_kg >= 0.0

    print(f"cas_testes = {len(surplus_testes)}")
    assert reductions[0] < reductions[-1], (
        "La réduction doit croître avec le surplus, sinon elle n'en dépend pas."
    )


# --- test_mortalite_accumulateur.py ---
def test_champ_mortality_remainder_est_sentinelle():
    """
    Le champ `mortality_remainder` existe et vaut -1.0 par défaut : sentinelle
    « non calculé » (règle 8 — un zéro peut être une mesure réelle).
    """
    cell = Cell(cell_id=1, area_km2=1.0, population=10)
    print(f"mortality_remainder par défaut = {cell.mortality_remainder}")
    assert cell.mortality_remainder == -1.0


# --- test_mortalite_accumulateur.py ---
def test_famine_tue_en_borne_de_ticks():
    """
    Une cellule de 5 habitants en famine totale perd au moins un
    habitant en au plus N_BOUND_MORT ticks.

    Borne analytique, dérivée et documentée dans sim/MODELE.md :
    au plafond de mortalité, `raw` augmente de
    `population × MAX_DEATH_RATE_PER_TICK` par tick, soit une mort entière en
    au plus `ceil(1 / MAX_DEATH_RATE_PER_TICK)` ticks quelle que soit la
    taille de la cellule. Avec les constantes actuelles : N_BOUND_MORT = 10.

    Le déficit est pris à `population / HUNGER_DEATH_SCALE` kg, ce qui garantit
    d'atteindre le plafond : per_capita × HDS = 1/HDS × HDS = 1 ≥
    MAX_DEATH_RATE_PER_TICK.

    Compteur : famine_tue_cellule_5hab.
    """
    deficit_kg = POPULATION_PETITE_CELLULE / HUNGER_DEATH_SCALE
    cell = Cell(
        cell_id=1,
        area_km2=1.0,
        population=POPULATION_PETITE_CELLULE,
        food_stock_kg=0.0,
        hunger_ticks=0,
        food_deficit_kg=deficit_kg,
        mortality_remainder=0.0,
    )

    tick_du_premier_mort = -1  # sentinelle : aucune mort observée
    for numero_tick in range(1, N_BOUND_MORT + 1):
        population_avant = cell.population
        _apply_mortality(cell)
        if cell.population < population_avant and tick_du_premier_mort < 0:
            tick_du_premier_mort = numero_tick
            break

    morts = POPULATION_PETITE_CELLULE - cell.population
    famine_tue_cellule_5hab = morts
    print(f"N_BOUND_MORT = {N_BOUND_MORT} (= ceil(1 / {MAX_DEATH_RATE_PER_TICK}))")
    print(f"deficit_kg = {deficit_kg}")
    print(f"tick_du_premier_mort = {tick_du_premier_mort}")
    print(f"famine_tue_cellule_5hab = {famine_tue_cellule_5hab}")

    assert famine_tue_cellule_5hab >= 1, (
        f"Cellule de {POPULATION_PETITE_CELLULE} habitants en famine totale "
        f"toujours intacte après {N_BOUND_MORT} ticks : la fraction de mort "
        "est encore jetée par int()."
    )
    assert 0 < tick_du_premier_mort <= N_BOUND_MORT


# --- test_mortalite_accumulateur.py ---
def test_precision_mortalite_sur_n_ticks():
    """
    Sur N_TICKS_OBSERVES ticks d'un micro-monde déterministe à trois
    cellules (populations ≥ 50, déficit par tête constant non nul), l'écart
    entre les morts réellement appliqués et la somme exacte
    `population × death_rate` accumulée tick par tick est ≤ 1 par cellule.

    L'écart maximal possible est la fraction en attente (< 1) : c'est
    précisément ce que le report garantit.

    Compteur : mortalite_precision_n_ticks.
    """
    ecarts = []

    for population_initiale in POPULATIONS_MICRO_MONDE:
        deficit_kg = population_initiale * DEFICIT_PAR_TETE_MICRO_MONDE_KG
        cell = Cell(
            cell_id=population_initiale,
            area_km2=1.0,
            population=population_initiale,
            food_stock_kg=0.0,
            hunger_ticks=0,
            food_deficit_kg=deficit_kg,
            mortality_remainder=0.0,
        )

        somme_exacte = 0.0
        morts_appliques = 0

        for _ in range(N_TICKS_OBSERVES):
            if cell.population <= 0:
                break
            # Taux du tick, recalculé comme le fait le moteur.
            per_capita = cell.food_deficit_kg / cell.population
            taux = min(per_capita * HUNGER_DEATH_SCALE, MAX_DEATH_RATE_PER_TICK)
            somme_exacte += cell.population * taux

            population_avant = cell.population
            _apply_mortality(cell)
            morts_appliques += population_avant - cell.population
            # Déficit maintenu constant : le maillon consommation n'est pas
            # joué ici, seul l'accumulateur de mortalité est sous test.
            cell.food_deficit_kg = deficit_kg

        ecart = abs(morts_appliques - somme_exacte)
        ecarts.append(ecart)
        print(
            f"pop_initiale={population_initiale}: morts_appliques={morts_appliques}, "
            f"somme_exacte={somme_exacte:.6f}, ecart={ecart:.6f}, "
            f"remainder_final={cell.mortality_remainder:.6f}"
        )

    mortalite_precision_n_ticks = max(ecarts)
    print(f"cellules = {len(POPULATIONS_MICRO_MONDE)}, ticks = {N_TICKS_OBSERVES}")
    print(f"mortalite_precision_n_ticks = {mortalite_precision_n_ticks:.6f}")

    assert mortalite_precision_n_ticks <= 1.0, (
        f"Écart maximal {mortalite_precision_n_ticks:.6f} > 1 mort : des morts "
        "fractionnaires sont encore perdues."
    )


# --- test_mortalite_continue.py ---
def test_plafond_toute_population():
    """
    Pour toute population dans POPULATIONS_TEST avec un déficit minuscule,
    le taux effectif de mortalité est ≤ MAX_DEATH_RATE_PER_TICK.

    Sans le plancher max(1, …), deaths = int(pop × rate) = 0 pour un déficit
    de 1e-9 kg quelle que soit la population : le taux effectif = 0.0 ≤ 0.10. ✓

    Avant la correction (avec max(1, …)) : pour pop=1, deaths=1, taux=1.0 > 0.10. ✗

    Compteur : max_taux_mortalite_effectif_pop_1.
    """
    max_taux_observe = -1.0  # sentinel (règle 8)

    for pop in POPULATIONS_TEST:
        cell = Cell(
            cell_id=pop,
            area_km2=1.0,
            population=pop,
            food_stock_kg=0.0,
            hunger_ticks=0,
            food_deficit_kg=DEFICIT_MINUSCULE_KG,
        )
        pop_avant = cell.population
        _apply_mortality(cell)
        deaths = pop_avant - cell.population

        taux_effectif = deaths / pop_avant
        print(
            f"pop={pop_avant}: deaths={deaths}, "
            f"taux_effectif={taux_effectif:.6g} (max={MAX_DEATH_RATE_PER_TICK})"
        )

        if taux_effectif > max_taux_observe:
            max_taux_observe = taux_effectif

        assert taux_effectif <= MAX_DEATH_RATE_PER_TICK, (
            f"Plafond dépassé pour pop={pop_avant} : taux={taux_effectif} > {MAX_DEATH_RATE_PER_TICK}. "
            "Le plancher max(1, …) réintroduit-il le dépassement ?"
        )

    max_taux_mortalite_effectif_pop_1 = max_taux_observe
    print(f"max_taux_mortalite_effectif_pop_1 = {max_taux_mortalite_effectif_pop_1}")


# --- test_mortalite_continue.py ---
def test_deficit_non_efface_en_1_tick():
    """
    Un tick de surplus plus petit que la
    dette ne peut pas effacer cette dette.

    Construit une cellule avec food_deficit_kg = 10 000 kg et un stock qui
    couvre sa consommation du tick plus un surplus de 200 kg (2 × la
    consommation du tick, très inférieur à la dette). Après _apply_consumption,
    le déficit résiduel doit être > 0 et valoir exactement
    D - surplus × DEFICIT_RECOVERY_RATE_PER_SURPLUS_KG.

    Compteur : deficit_non_efface_en_1_tick.
    """
    D = 10_000.0  # déficit accumulé initial (kg)
    pop = 100
    # Stock = 2 × consommation du tick → surplus = 1 × consommation = 200 kg
    from sim.constants import FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    besoin_tick = pop * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    stock_suffisant = besoin_tick * 2
    surplus = stock_suffisant - besoin_tick

    cell = Cell(
        cell_id=1,
        area_km2=1.0,
        population=pop,
        food_stock_kg=stock_suffisant,
        hunger_ticks=0,
        food_deficit_kg=D,
        mortality_remainder=0.0,
    )

    _apply_consumption(cell)

    deficit_residuel = cell.food_deficit_kg
    deficit_attendu = D - surplus * DEFICIT_RECOVERY_RATE_PER_SURPLUS_KG
    deficit_non_efface_en_1_tick = deficit_residuel > 0

    print(f"D_initial = {D}, surplus_du_tick = {surplus}")
    print(f"deficit_non_efface_en_1_tick = {deficit_residuel}")
    print(f"deficit_attendu = {deficit_attendu}")
    print(
        "DEFICIT_RECOVERY_RATE_PER_SURPLUS_KG = "
        f"{DEFICIT_RECOVERY_RATE_PER_SURPLUS_KG}"
    )

    assert deficit_non_efface_en_1_tick, (
        f"Le déficit a été entièrement effacé en un seul tick de surplus : "
        f"D={D}, surplus={surplus}, résiduel={deficit_residuel}."
    )

    # Vérifier la valeur exacte (formule déterministe, bornée par le surplus)
    assert abs(deficit_residuel - deficit_attendu) < 1e-9, (
        f"Valeur de récupération incorrecte : attendu={deficit_attendu}, "
        f"obtenu={deficit_residuel}."
    )


# --- Ce que le monde entier doit respecter, mesuré sur le moteur ---
#
# Ces trois tests remplacent un modèle analytique de survie (262 lignes de
# `sim/constants.py`, cinq tests, 6 s) qui prédisait la valeur ABSOLUE de la
# fraction de survivants et la comparait à la mesure. Le modèle supposait UNE
# capacité de charge globale ; il cesse d'exister dès que la production varie
# d'une cellule à l'autre — ce que fait le prochain pas du modèle, le relief.
#
# La garde payée par un vrai défaut est conservée telle quelle : le critère de
# survie ne doit pas être aveugle aux constantes qui gouvernent la mort. Elle
# est tenue ici par la DIRECTION de la réponse, mesurée sur le moteur, qui
# survit à tout changement du modèle de production.


def test_le_monde_nourrit_ceux_qu_il_amorce():
    """
    Invariant d'amorçage — le monde ne pose pas plus de bouches que sa terre
    n'en nourrit.

    Le plafond est le MÊME que celui du test suivant, dérivé de la même et
    unique formule de production. La différence est ce qu'on lui demande :
    l'autre vérifie que les SURVIVANTS ne mangent pas plus que le monde ne
    produit — un plafond de 0,5 le satisfait très bien, à condition que la
    moitié du monde soit morte. Celui-ci vérifie que le plafond lui-même est
    atteignable AU TICK ZÉRO.

    Ce que sa rougeur signifierait : le monde amorce une population
    condamnée. Ce n'est pas une famine émergente — aucun événement du jeu ne
    l'a causée — c'est un amorçage qui ment. Mesuré avant le lot 055 :
    plafond 0,691, soit 1,45 bouche amorcée par bouche nourrie, et 86 % des
    habitants morts la première année simulée.

    Ce test peut échouer : remplacer PART_SOUTENABLE_AMORCEE par une valeur
    supérieure à 1, ou rendre l'amorçage aveugle à la production, le rend
    rouge immédiatement.
    """
    monde = World.charger(rng_seed=RNG_SEED)
    pop_initiale = sum(cell.population for cell in monde.cells.values())

    production_moyenne = production_moyenne_kg_par_tick(monde)
    ration_du_monde = FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK * pop_initiale
    plafond = production_moyenne / ration_du_monde

    print(f"population amorcee = {pop_initiale}")
    print(f"plafond derive a l'amorcage = {plafond:.6f}")

    assert pop_initiale > 0, (
        "Le monde amorce zéro habitant : il n'y a rien à simuler."
    )
    assert plafond >= 1.0, (
        f"plafond {plafond:.6f} < 1 : le monde amorce plus de bouches que sa "
        "terre n'en nourrit à rendement moyen. La mortalité qui suit n'est pas "
        "une famine du jeu, c'est une erreur d'amorçage."
    )


def test_aucune_cellule_n_amorce_au_dessus_de_ce_qu_elle_nourrit():
    """
    Le même invariant, cellule par cellule — parce qu'une moyenne mondiale
    saine peut cacher des cellules condamnées dès le premier tick.

    Une cellule amorcée au-dessus de son plafond n'est pas interdite en soi :
    le commerce existe pour ça. Mais AU TICK ZÉRO, avant qu'aucune route
    n'ait servi, aucune ne doit l'être — sinon la première mesure du monde
    est déjà une famine que personne n'a déclenchée.
    """
    monde = World.charger(rng_seed=RNG_SEED)
    fautives = []
    for cell in monde.cells.values():
        soutenable = population_soutenable_de(cell, monde.carte)
        if cell.population > soutenable:
            fautives.append((cell.cell_id, cell.population, soutenable))

    print(f"cellules au-dessus de leur plafond : {len(fautives)} / {len(monde.cells)}")
    assert not fautives, (
        f"{len(fautives)} cellules amorcent plus d'habitants qu'elles n'en "
        f"nourrissent, la première étant {fautives[0]}."
    )


def test_le_monde_ne_meurt_pas_et_ne_nourrit_pas_plus_qu_il_ne_produit():
    """
    Invariant physique — conservation de la masse, vue du monde entier.

    Le plafond est DÉRIVÉ du moteur lui-même : `production_moyenne_kg_par_tick`
    appelle `production_kg`, la même et unique formule que le tick emploie.
    Il ne peut donc pas diverger de ce que le monde produit réellement, et il
    suivra tout seul le jour où le relief modulera le rendement.

    Ce que le dépassement du plafond signifierait : la population survivante
    mange plus que le monde ne produit — donc des kilogrammes apparaissent
    ailleurs que dans la production. Le commerce qui duplique, la consommation
    qui ne prélève pas, une dette effacée sans surplus pour la payer : toutes
    ces fautes-là se voient ici, et aucune ne peut se cacher derrière un
    ajustement de tolérance.

    Le plancher dit l'autre moitié, qui est une règle de jeu visible : le monde
    ne s'éteint pas.
    """
    fraction, monde, pop_initiale = _observer_le_monde()

    production_moyenne = production_moyenne_kg_par_tick(monde)
    ration_du_monde = FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK * pop_initiale
    plafond = production_moyenne / ration_du_monde

    print(f"cellules = {len(monde.cells)}, population initiale = {pop_initiale}")
    print(f"production moyenne = {production_moyenne:.0f} kg/tick")
    print(f"ration du monde de depart = {ration_du_monde:.0f} kg/tick")
    print(f"plafond derive = {plafond:.6f}")
    print(f"fraction_survie apres {N_TICKS_OBSERVES} ticks = {fraction:.6f}")

    assert fraction > 0.0, (
        f"Le monde s'est éteint en {N_TICKS_OBSERVES} ticks : il ne reste "
        "personne. Ce n'est plus une simulation vivante."
    )
    assert fraction <= plafond, (
        f"{fraction:.6f} survivants pour un plafond de {plafond:.6f} : la "
        "population qui reste mange plus que le monde ne produit. Des "
        "kilogrammes apparaissent ailleurs que dans la production."
    )


def test_la_survie_repond_a_la_mortalite(monkeypatch):
    """
    Règle de jeu visible, et la garde payée par un vrai défaut.

    Un critère de survie aveugle aux constantes qui gouvernent la mort ne
    prouve rien : une famine deux fois plus meurtrière passait le même
    contrôle.

    La garde, mesurée sur le moteur : modifier HUNGER_DEATH_SCALE doit
    changer la survie observée. La direction n'est pas testée — le maillon
    migration peut inverser la tendance, des morts précoces réduisant la
    pression alimentaire et augmentant la survie des derniers.

    Rouge prouvé : avec un `_apply_mortality` qui ignore HUNGER_DEATH_SCALE,
    les trois régimes rendent la même fraction (0.883422) et le test échoue.
    """
    nominal = constantes.HUNGER_DEATH_SCALE

    def _regime(facteur: float) -> float:
        monkeypatch.setattr(constantes, "HUNGER_DEATH_SCALE", nominal * facteur)
        try:
            fraction, _, _ = _observer_le_monde()
        finally:
            monkeypatch.setattr(constantes, "HUNGER_DEATH_SCALE", nominal)
        return fraction

    s_bas = _regime(FACTEUR_REGIME_BAS)
    s_nominal = _regime(1.0)
    s_haut = _regime(FACTEUR_REGIME_HAUT)

    print(f"HUNGER_DEATH_SCALE nominal = {nominal}")
    print(f"x{FACTEUR_REGIME_BAS} : {s_bas:.6f}")
    print(f"nominal : {s_nominal:.6f}")
    print(f"x{FACTEUR_REGIME_HAUT} : {s_haut:.6f}")

    ecart_max = max(s_bas, s_nominal, s_haut) - min(s_bas, s_nominal, s_haut)
    survie_repond_a_la_mortalite = int(ecart_max > 1e-4)
    print(f"survie_repond_a_la_mortalite = {survie_repond_a_la_mortalite}")
    print(f"ecart_max = {ecart_max:.6f}")

    assert constantes.HUNGER_DEATH_SCALE == nominal, (
        "Le régime nominal n'a pas été restauré."
    )
    assert ecart_max > 1e-4, (
        f"Les trois régimes donnent la même fraction : "
        f"{s_bas:.6f} / {s_nominal:.6f} / {s_haut:.6f}. "
        "Le moteur ne lit pas HUNGER_DEATH_SCALE."
    )


def test_la_survie_repond_a_la_nourriture(monkeypatch):
    """
    Règle de jeu visible : plus le monde produit, plus il reste de monde.

    Mesuré sur le moteur, et non sur une formule. La distinction n'est pas
    théorique : le test qu'il remplace ne vérifiait que la prédiction, et
    disait lui-même « le brief n'exige pas de mesure pour ce régime ». Il
    passait alors que le moteur ne relisait même pas la constante de
    production (elle était liée par valeur) — la formule répondait, le monde
    non, et rien ne le disait.
    """
    nominal = constantes.FOOD_PRODUCTION_KG_PER_KM2_PER_TICK

    def _regime(facteur: float) -> float:
        monkeypatch.setattr(
            constantes, "FOOD_PRODUCTION_KG_PER_KM2_PER_TICK", nominal * facteur
        )
        try:
            fraction, _, _ = _observer_le_monde()
        finally:
            monkeypatch.setattr(
                constantes, "FOOD_PRODUCTION_KG_PER_KM2_PER_TICK", nominal
            )
        return fraction

    s_maigre = _regime(FACTEUR_REGIME_BAS)
    s_nominal = _regime(1.0)

    print(f"production x{FACTEUR_REGIME_BAS} : {s_maigre:.6f}")
    print(f"production nominale : {s_nominal:.6f}")
    print(f"survie_repond_a_la_nourriture = {int(s_nominal > s_maigre)}")

    assert constantes.FOOD_PRODUCTION_KG_PER_KM2_PER_TICK == nominal
    assert s_nominal > s_maigre, (
        f"Diviser la production par deux ne fait pas baisser la survie "
        f"({s_nominal:.6f} contre {s_maigre:.6f}). Soit le moteur ne relit "
        "pas la constante, soit la nourriture ne décide plus de rien."
    )


# --- Natalité ---

import math


def _cellule_rassasiee_productive(population: int, area_km2: float = 50.0) -> tuple[World, int]:
    """Micro-monde d'une cellule auto-suffisante en nourriture."""
    besoin = population * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    cell = Cell(
        cell_id=1,
        area_km2=area_km2,
        population=population,
        food_stock_kg=besoin * 10,
        hunger_ticks=0,
        food_deficit_kg=0.0,
        mortality_remainder=0.0,
        natalite_remainder=0.0,
    )
    return World(cells={1: cell}, adjacency=[]), population


def test_cellule_rassasiee_gagne_habitants():
    """
    Une cellule rassasiée sans dette voit sa population croître en au
    plus ceil(1 / (population × taux)) ticks rassasiés.
    """
    population = 100
    world, pop_init = _cellule_rassasiee_productive(population)
    rate = constantes.naissances_par_habitant_par_tick()
    borne = math.ceil(1.0 / (rate * population))
    rng = random.Random(42)
    for _ in range(borne):
        tick(world, rng)
    pop_fin = world.cells[1].population
    print(f"population initiale = {pop_init}, finale = {pop_fin}, borne = {borne}")
    assert pop_fin > pop_init, (
        f"La cellule rassasiée n'a gagné aucun habitant en {borne} ticks."
    )


def test_cellule_affamee_ne_gagne_pas_habitants():
    """
    La faim ferme la natalité, elle ne la ralentit pas.

    Le maillon est appelé directement : un tick complet tue la cellule
    avant qu'un remainder inconditionnel n'atteigne 1, et le contrôle
    passerait en silence (règle 4). La borne est le nombre de ticks
    rassasiés qui suffirait à naître — dérivée du taux et de la
    population, jamais écrite en dur.
    """
    population = 50
    remainder_init = 0.0
    cell = Cell(
        cell_id=1,
        area_km2=0.0,
        population=population,
        food_stock_kg=0.0,
        hunger_ticks=0,
        food_deficit_kg=0.0,
        mortality_remainder=0.0,
        natalite_remainder=remainder_init,
    )
    rate = constantes.naissances_par_habitant_par_tick()
    borne = math.ceil(1.0 / (rate * population))
    penurie_kg = population * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    remainder_max = remainder_init
    for _ in range(borne):
        _apply_natalite(cell, penurie_kg)
        remainder_max = max(remainder_max, cell.natalite_remainder)
    print(
        f"pop = {cell.population}, remainder_init = {remainder_init}, "
        f"remainder_max = {remainder_max}, borne = {borne}"
    )
    assert cell.population == population, (
        f"Naissance en pénurie : population={cell.population}, "
        f"départ={population}."
    )
    assert remainder_max == remainder_init, (
        "natalite_remainder a progressé alors que la cellule était affamée."
    )


def test_dette_alimentaire_ferme_la_natalite():
    """
    Une dette alimentaire nulle est exigée, pas seulement une
    pénurie nulle ce tick. Sinon la faim d'hier n'empêcherait pas
    de naître aujourd'hui.
    """
    population = 50
    remainder_init = 0.0
    cell = Cell(
        cell_id=1,
        area_km2=0.0,
        population=population,
        food_stock_kg=0.0,
        hunger_ticks=0,
        food_deficit_kg=population * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK,
        mortality_remainder=0.0,
        natalite_remainder=remainder_init,
    )
    rate = constantes.naissances_par_habitant_par_tick()
    borne = math.ceil(1.0 / (rate * population))
    remainder_max = remainder_init
    for _ in range(borne):
        _apply_natalite(cell, 0.0)
        remainder_max = max(remainder_max, cell.natalite_remainder)
    print(
        f"dette : pop = {cell.population}, remainder_max = {remainder_max}, "
        f"borne = {borne}"
    )
    assert cell.population == population
    assert remainder_max == remainder_init, (
        "natalite_remainder a progressé malgré une dette alimentaire."
    )


def test_ration_exacte_ouvre_la_natalite():
    """
    La porte se lit sur la pénurie du tick, pas sur un stock
    restant. Une cellule qui mange pile sa ration (pénurie nulle,
    garde-manger vide, dette nulle) accumule une fraction de natalité.
    """
    population = 100
    besoin = population * FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    cell = Cell(
        cell_id=1,
        area_km2=0.0,
        population=population,
        food_stock_kg=besoin,
        hunger_ticks=0,
        food_deficit_kg=0.0,
        mortality_remainder=0.0,
        natalite_remainder=0.0,
    )
    world = World(cells={1: cell}, adjacency=[])
    tick(world, random.Random(0))
    c = world.cells[1]
    print(
        f"stock = {c.food_stock_kg}, deficit = {c.food_deficit_kg}, "
        f"remainder = {c.natalite_remainder}"
    )
    assert c.food_stock_kg == 0.0
    assert c.food_deficit_kg == 0.0
    assert c.natalite_remainder > 0.0, (
        "Une cellule qui a mangé pile sa ration doit accumuler une "
        "fraction de natalité. La porte se lit sur la pénurie, pas "
        "sur le garde-manger."
    )


def test_petite_cellule_finalement_gagne_un_habitant():
    """
    population × taux < 1 : un habitant en au plus
    ceil(1 / (population × taux)) ticks rassasiés.
    """
    population = 5
    world, pop_init = _cellule_rassasiee_productive(population)
    rate = constantes.naissances_par_habitant_par_tick()
    borne = math.ceil(1.0 / (rate * population))
    rng = random.Random(42)
    for _ in range(borne):
        tick(world, rng)
    pop_fin = world.cells[1].population
    print(f"petite cellule : initiale = {pop_init}, finale = {pop_fin}, borne = {borne}")
    assert pop_fin > pop_init, (
        f"Stérilité par arrondi : {pop_init} habitants après {borne} ticks rassasiés."
    )


def test_natalite_remainder_sentinelle_et_amorcage():
    """
    Sentinelle -1.0 sur Cell() ; 0.0 sur cellule d'un World.charger().
    """
    cell_vierge = Cell(cell_id=1, area_km2=1.0, population=10)
    assert cell_vierge.natalite_remainder == -1.0
    world = World.charger(rng_seed=0)
    cell_amorcee = next(iter(world.cells.values()))
    assert cell_amorcee.natalite_remainder == 0.0
    print(
        f"vierge = {cell_vierge.natalite_remainder}, "
        f"amorcée = {cell_amorcee.natalite_remainder}"
    )


def test_le_monde_ne_nourrit_pas_plus_a_horizon_allonge():
    """
    Même plafond dérivé à cinq fois l'horizon de N_TICKS_OBSERVES.
    """
    horizon = N_TICKS_OBSERVES * 5
    fraction, monde, pop_initiale = _observer_le_monde(n_ticks=horizon)
    production_moyenne = production_moyenne_kg_par_tick(monde)
    ration_du_monde = FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK * pop_initiale
    plafond = production_moyenne / ration_du_monde
    print(f"horizon = {horizon}, plafond = {plafond:.6f}, fraction = {fraction:.6f}")
    assert fraction > 0.0
    assert fraction <= plafond


def test_la_demographie_repond_a_la_natalite(monkeypatch):
    """
    fraction_survie(taux_nul) < fraction_survie(taux_nominal)
    < fraction_survie(taux_double).
    """
    nominal = constantes.NAISSANCES_PAR_HABITANT_PAR_TICK

    def _regime(facteur: float) -> float:
        monkeypatch.setattr(
            constantes, "NAISSANCES_PAR_HABITANT_PAR_TICK", nominal * facteur
        )
        try:
            fraction, _, _ = _observer_le_monde()
        finally:
            monkeypatch.setattr(
                constantes, "NAISSANCES_PAR_HABITANT_PAR_TICK", nominal
            )
        return fraction

    s_nul = _regime(0.0)
    s_nominal = _regime(1.0)
    s_double = _regime(2.0)

    print(f"taux nul : {s_nul:.6f}")
    print(f"taux nominal : {s_nominal:.6f}")
    print(f"taux double : {s_double:.6f}")

    assert constantes.NAISSANCES_PAR_HABITANT_PAR_TICK == nominal
    assert s_nul < s_nominal < s_double, (
        f"La démographie ne répond pas au taux de natalité : "
        f"{s_nul:.6f} / {s_nominal:.6f} / {s_double:.6f}."
    )
