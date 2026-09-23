"""
Constantes nommées du moteur de simulation.

Une seule place pour tout ce qui se règle. Le corps d'une fonction du
moteur ne contient aucun littéral numérique en dehors de 0, 1 et -1 —
vérifié par `sim/tests/test_no_hardcoded.py`.

Toutes les valeurs sont documentées dans `sim/MODELE.md`, et toutes les
durées dérivent de TICK_DURATION_DAYS : jamais un second littéral de temps.
"""

import math

# --- Marchandises ---

# Première marchandise du panier ; seule entrée réellement simulée pour l'instant.
MARCHANDISE_NOURRITURE = "nourriture"

# Marchandise générique issue de la façonnage des matières premières ; niveau 2.
MARCHANDISE_OBJET = "objet"

# Part du stock de matière première façonnée par tick ; niveau 2.
TAUX_FABRICATION_PAR_TICK = 0.05

# Kilogrammes d'objet produits par kilogramme de matière consommée ; niveau 2.
RENDEMENT_FABRICATION = 0.6


def fabrication_kg(stock_brut_kg: float) -> tuple[float, float]:
    """
    Consommation et production d'un tick de façonnage pour un stock brut.

    Relit TAUX_FABRICATION_PAR_TICK et RENDEMENT_FABRICATION à chaque appel.
    """
    consomme = stock_brut_kg * TAUX_FABRICATION_PAR_TICK
    produit = consomme * RENDEMENT_FABRICATION
    return consomme, produit

# --- Base de temps unique ---

# Durée d'un tick en jours (proxy paramétrique, voir MODELE.md).
# Toutes les constantes temporelles ci-dessous sont dérivées de cette valeur.
TICK_DURATION_DAYS = 1

# --- Production alimentaire ---

# Rendement agricole paramétrique : kilogrammes de nourriture produits
# par km² et par tick.
# Proxy : 6 570 kg/km²/an (rendement médiéval estimé) ÷ 365 jours ×
# TICK_DURATION_DAYS (voir MODELE.md).
FOOD_PRODUCTION_KG_PER_KM2_PER_TICK = 18.0 * TICK_DURATION_DAYS


# --- Saison dans le rendement (fidélité niveau 2) ---

# Durée d'un jour d'équinoxe — niveau 1 (douze heures partout).
DUREE_JOUR_EQUINOXE_H = 12.0

# Sensibilité du rendement à l'écart de durée du jour par rapport à l'équinoxe ;
# ordre de grandeur plausible niveau 2, jamais sourcé.
SENSIBILITE_SAISON = 0.5

# Rang du solstice d'été dans l'année calendaire ; niveau 2.
JOUR_SOLSTICE_ETE = 172


def jour_de_tick(numero_tick: int | None) -> int:
    """
    Jour de l'année pour un numéro de tick ; absence = premier jour.

    Relit TICK_DURATION_DAYS et CALENDAR_DAYS_PER_YEAR à chaque appel.
    """
    if numero_tick is None:
        return 0
    return (numero_tick * TICK_DURATION_DAYS) % CALENDAR_DAYS_PER_YEAR


def jour_solstice_ete() -> int:
    """Rang du solstice d'été ; relu à chaque appel."""
    return JOUR_SOLSTICE_ETE


def jour_solstice_hiver() -> int:
    """Rang du solstice d'hiver, dérivé de la base de temps."""
    return (JOUR_SOLSTICE_ETE + CALENDAR_DAYS_PER_YEAR // FACTEUR_DEUX) % CALENDAR_DAYS_PER_YEAR


def duree_jour_h(jour: int, ete_h: float, hiver_h: float) -> float:
    """
    Durée du jour à une date, oscillant entre les deux solstices de la cellule.

    Relit JOUR_SOLSTICE_ETE et CALENDAR_DAYS_PER_YEAR à chaque appel.
    """
    moyenne_h = (ete_h + hiver_h) / FACTEUR_DEUX
    amplitude_h = (ete_h - hiver_h) / FACTEUR_DEUX
    annee = CALENDAR_DAYS_PER_YEAR
    solstice = JOUR_SOLSTICE_ETE
    return moyenne_h + amplitude_h * math.cos(math.tau * (jour - solstice) / annee)


def facteur_saison(duree_jour_h_val: float) -> float:
    """
    Modulation du rendement selon la durée du jour, par rapport à l'équinoxe.

    Relit SENSIBILITE_SAISON et DUREE_JOUR_EQUINOXE_H à chaque appel.
    Le plancher à zéro est un invariant physique : pas de production négative.
    """
    equinoxe = DUREE_JOUR_EQUINOXE_H
    sensibilite = SENSIBILITE_SAISON
    ecart = (duree_jour_h_val - equinoxe) / equinoxe
    plancher = 0.0
    return max(plancher, 1.0 + sensibilite * ecart)


# Moyennes annuelles déjà calculées. La clé porte TOUTES les constantes que
# le calcul relit : changer l'une d'elles change la clé, donc rate le cache et
# recalcule. Sans cela, un test qui remplace une constante en mémoire
# mesurerait une valeur figée en croyant mesurer le nouveau régime.
_moyennes_annuelles: dict[tuple, float] = {}


def facteur_saison_moyen_annuel(ete_h: float, hiver_h: float) -> float:
    """
    Moyenne du facteur saisonnier sur une année calendaire complète.

    Somme jour par jour, divisée par le nombre de jours dérivé des constantes
    de temps — pas la valeur 1 supposée.

    Le résultat ne dépend que de ses deux arguments et des constantes citées
    dans la clé ci-dessous ; il est donc gardé plutôt que refait à chaque
    appel. C'est une année entière de calcul par cellule et par tick.
    """
    cle = (
        ete_h,
        hiver_h,
        CALENDAR_DAYS_PER_YEAR,
        JOUR_SOLSTICE_ETE,
        DUREE_JOUR_EQUINOXE_H,
        SENSIBILITE_SAISON,
        FACTEUR_DEUX,
    )
    garde = _moyennes_annuelles.get(cle)
    if garde is not None:
        return garde

    annee = CALENDAR_DAYS_PER_YEAR
    total = 0.0
    jour = 0
    while jour < annee:
        duree = duree_jour_h(jour, ete_h, hiver_h)
        total += facteur_saison(duree)
        jour += 1
    moyenne = total / annee
    _moyennes_annuelles[cle] = moyenne
    return moyenne


# --- Extraction minière (fidélité niveau 2) ---

# Kilogrammes extraits par habitant et par tick sur un gisement notable ;
# ordre de grandeur plausible niveau 2, jamais sourcé.
EXTRACTION_KG_PAR_HABITANT_PAR_TICK = 0.02

# Facteurs de débit par classe de richesse du gisement ; niveau 2.
FACTEUR_RICHESSE_MAJEURE = 2.0
FACTEUR_RICHESSE_NOTABLE = 1.0
FACTEUR_RICHESSE_MINEURE = 0.4


def extraction_kg_par_habitant_par_tick() -> float:
    """Débit unitaire par habitant ; relu à chaque appel."""
    return EXTRACTION_KG_PAR_HABITANT_PAR_TICK


def facteurs_richesse_extraction() -> dict[str, float]:
    """
    Table des facteurs de débit par classe de richesse d'un gisement.

    Relue les constantes nommées à chaque appel : un test de régime qui
    remplace une constante en mémoire doit changer le moteur.
    """
    return {
        "majeure": FACTEUR_RICHESSE_MAJEURE,
        "notable": FACTEUR_RICHESSE_NOTABLE,
        "mineure": FACTEUR_RICHESSE_MINEURE,
    }


# Part de la population qu'un gisement notable occupe ; niveau 2.
PART_MINIERE_PAR_GISEMENT = 0.05

# Plafond : une cellule ne devient jamais entièrement minière. Invariant,
# pas un réglage de confort — sans lui une cellule chargée de gisements
# majeurs verrait toute sa population descendre à la mine.
PART_MINIERE_MAXIMALE = 0.30


def part_miniere_de(gisements, facteurs_richesse) -> float:
    """
    Part de la population occupée par les gisements de la cellule.

    Relit PART_MINIERE_PAR_GISEMENT et PART_MINIERE_MAXIMALE à chaque appel.
    Un gisement incomplet (sans ressource ou sans richesse) est ignoré.
    Une richesse hors des trois classes ne compte pas : le moteur la refuse
    à l'extraction.
    """
    if not gisements:
        return 0.0
    total = 0.0
    part_par = PART_MINIERE_PAR_GISEMENT
    plafond = PART_MINIERE_MAXIMALE
    for gisement in gisements:
        if not isinstance(gisement, dict):
            continue
        if gisement.get("ressource") is None or gisement.get("richesse") is None:
            continue
        richesse = gisement.get("richesse")
        if richesse not in facteurs_richesse:
            continue
        total += part_par * facteurs_richesse[richesse]
    return min(plafond, total)


# --- Relief dans le rendement (fidélité niveau 2) ---

# Facteurs de production par classe de relief : ordres de grandeur plausibles
# niveau 2, jamais sourcés historiquement.
FACTEUR_RELIEF_PLAINE = 1.0
FACTEUR_RELIEF_COLLINE = 0.80
FACTEUR_RELIEF_MONTAGNE = 0.45
FACTEUR_RELIEF_HAUTE_MONTAGNE = 0.15
FACTEUR_RELIEF_MARAIS = 0.50


def facteurs_production_par_relief() -> dict[str, float]:
    """
    Table des facteurs de production par classe de relief.

    Relue les constantes nommées à chaque appel : un test de régime qui
    remplace une constante en mémoire doit changer le moteur.
    """
    return {
        "plaine": FACTEUR_RELIEF_PLAINE,
        "colline": FACTEUR_RELIEF_COLLINE,
        "montagne": FACTEUR_RELIEF_MONTAGNE,
        "haute_montagne": FACTEUR_RELIEF_HAUTE_MONTAGNE,
        "marais": FACTEUR_RELIEF_MARAIS,
    }


# --- Relief dans le transport (fidélité niveau 2) ---

# Facteurs de capacité de transport par classe de relief : ordres de grandeur
# plausibles niveau 2, jamais sourcés historiquement — échelle distincte de
# la production (un marais se traverse mal et produit mal, sans coïncidence
# garantie entre les deux tables).
FACTEUR_TRANSPORT_PLAINE = 1.00
FACTEUR_TRANSPORT_COLLINE = 0.70
FACTEUR_TRANSPORT_MARAIS = 0.40
FACTEUR_TRANSPORT_MONTAGNE = 0.30
FACTEUR_TRANSPORT_HAUTE_MONTAGNE = 0.10


def facteurs_transport_par_relief() -> dict[str, float]:
    """
    Table des facteurs de capacité de transport par classe de relief.

    Relue les constantes nommées à chaque appel : un test de régime qui
    remplace une constante en mémoire doit changer le moteur.
    """
    return {
        "plaine": FACTEUR_TRANSPORT_PLAINE,
        "colline": FACTEUR_TRANSPORT_COLLINE,
        "marais": FACTEUR_TRANSPORT_MARAIS,
        "montagne": FACTEUR_TRANSPORT_MONTAGNE,
        "haute_montagne": FACTEUR_TRANSPORT_HAUTE_MONTAGNE,
    }

# --- Variabilité de rendement ---

# Le rendement de chaque cellule est multiplié par un facteur uniforme
# tiré du rng à chaque tick (fluctuations climatiques/agronomiques).
# Distribution : rng.uniform(RNG_YIELD_LOW, RNG_YIELD_HIGH)
# Documentée dans MODELE.md.
RNG_YIELD_LOW = 0.5
RNG_YIELD_HIGH = 1.5

# --- Consommation alimentaire ---

# Consommation alimentaire par personne et par tick (kg).
# Proxy : ration journalière médiévale ~2 kg × TICK_DURATION_DAYS.
FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK = 2.0 * TICK_DURATION_DAYS


def consommation_kg_par_habitant_par_tick(marchandise: str) -> float:
    """
    Kilogrammes consommés par habitant et par tick pour une marchandise.

    Seul lieu du moteur qui distingue une marchandise d'une autre pour la
    consommation. Relit les constantes nommées à chaque appel.
    """
    if marchandise == MARCHANDISE_NOURRITURE:
        return FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    return 0.0

# --- Commerce inter-cellules ---

# Débit par kilomètre de frontière partagée (niveau 2) : une arête de 1 000 m
# produit la même capacité que TRADE_CAPACITY_KG_PER_EDGE_PER_TICK.
DEBIT_KG_PAR_KM_DE_FRONTIERE_PAR_TICK = 200.0 * TICK_DURATION_DAYS

# Conversion mètres → kilomètres ; relue via metres_par_km() pour ne pas figer
# une constante de conversion dans le balayage du monde d'épreuve.
METRES_PAR_KM = 1000.0


def metres_par_km() -> float:
    """Relit METRES_PAR_KM à chaque appel."""
    return METRES_PAR_KM


# Capacité de transport maximale par arête d'adjacence et par tick (kg).
# Proxy paramétrique : convoi à dos de mulet ≈ 200 kg/jour sur une
# liaison rurale (voir MODELE.md).
TRADE_CAPACITY_KG_PER_EDGE_PER_TICK = 200.0 * TICK_DURATION_DAYS

# Débit maritime par kilomètre de façade (niveau 2) : dix fois le débit
# terrestre au kilomètre — un navire porte sans commune mesure ce que porte
# un convoi de bêtes de somme.
DEBIT_KG_PAR_KM_DE_COTE_PAR_TICK = 2000.0 * TICK_DURATION_DAYS


def debit_maritime_kg_par_km() -> float:
    """Relit DEBIT_KG_PAR_KM_DE_COTE_PAR_TICK à chaque appel."""
    return DEBIT_KG_PAR_KM_DE_COTE_PAR_TICK

# --- Mortalité par famine ---

# Facteur de mortalité : fraction de la population mourant par tick
# par kg de déficit alimentaire cumulé par habitant.
# Mortalité = population × min(per_capita_deficit × HUNGER_DEATH_SCALE,
#                              MAX_DEATH_RATE_PER_TICK)
# Proxy paramétrique — voir MODELE.md.
HUNGER_DEATH_SCALE = 0.005

# Taux de mortalité maximal par tick (plafond) — empêche l'effondrement
# instantané même avec un déficit extrême.
MAX_DEATH_RATE_PER_TICK = 0.10

# --- Natalité (fidélité niveau 2) ---

# Naissances par habitant et par tick, sur les seuls ticks où la cellule
# a mangé sa ration entière sans dette alimentaire — ordre de grandeur
# plausible niveau 2, jamais sourcé.
NAISSANCES_PAR_HABITANT_PAR_TICK = 0.0002


def naissances_par_habitant_par_tick() -> float:
    """Relit NAISSANCES_PAR_HABITANT_PAR_TICK à chaque appel (motif 033)."""
    return NAISSANCES_PAR_HABITANT_PAR_TICK

# --- Amorçage initial ---

# Part du plafond physique de survie que le monde amorce.
#
# La population initiale d'une cellule n'est plus une densité plate : elle est
# DÉRIVÉE de ce que cette cellule produit, par la même formule que le tick
# emploie (`sim.engine.population_soutenable_de`). Cette constante dit
# seulement quelle part de ce plafond le monde porte au tick zéro.
#
# Pourquoi strictement moins de 1 : le rendement d'un tick est tiré autour de
# sa moyenne. Un monde amorcé EXACTEMENT à son plafond n'a aucune marge, et
# tout tick sous la moyenne creuse une dette que le suivant ne rembourse
# qu'en partie. La marge est ce qui laisse le monde respirer — et croître,
# puisque la natalité ne joue que sur les ticks sans dette.
#
# Ce que cette valeur a remplacé : INITIAL_POPULATION_PER_KM2 = 10.0 hab/km²,
# appliquée à toute cellule sans regarder ce qu'elle produit. Mesuré avant
# retrait : plafond dérivé 0,691 — le monde amorçait 1,45 bouche pour chaque
# bouche que sa terre nourrit, et perdait 86 % de ses habitants la première
# année simulée. Ce n'était pas une famine émergente, c'était l'amorçage.
PART_SOUTENABLE_AMORCEE = 0.8

# Variation aléatoire autour de la densité nominale lors de l'amorçage.
SEED_POPULATION_VARIATION_LOW = 0.9
SEED_POPULATION_VARIATION_HIGH = 1.1

# Nombre de ticks de consommation couverts par le stock alimentaire initial.
# L'unité est le tick, pas le jour calendaire.
INITIAL_FOOD_RESERVE_TICKS = 5

# --- Récupération physique du déficit alimentaire ---

# Kilogrammes de dette alimentaire remboursés par kilogramme de surplus
# RÉELLEMENT consommé au-delà du besoin d'entretien. Ratio 1:1 : les kg
# remboursés quittent le stock. Une dette ne peut donc pas s'effacer sans
# contrepartie physique — l'économie est physique, rien ne se téléporte.
DEFICIT_RECOVERY_RATE_PER_SURPLUS_KG = 1.0

# --- Rendement moyen (seule grandeur dérivée que le moteur consulte) ---

# Le corps d'une fonction de sim/ ne peut pas contenir de littéral numérique
# autre que 0, 1 et -1 (sim/tests/test_no_hardcoded.py) : le diviseur d'une
# moyenne de deux bornes se nomme.
FACTEUR_DEUX = 2.0


def rendement_moyen_courant() -> float:
    """
    Rendement moyen du tirage uniforme de rendement agricole.

    Relit les globales du module à chaque appel : remplacer une borne de
    rendement en mémoire doit changer la moyenne, comme cela change le moteur.
    """
    return (RNG_YIELD_LOW + RNG_YIELD_HIGH) / FACTEUR_DEUX


# --- Ce qui a été retiré ici, et pourquoi ---
#
# Un modèle analytique de survie occupait 262 des 358 lignes de ce fichier :
# capacité de charge, densité stationnaire d'un oscillateur déficit/population,
# espérance du manque de production, probabilité de tick déficitaire, fraction
# de survie prédite, trois tolérances dérivées et un horizon de 1 000 ticks.
# Il prédisait la valeur ABSOLUE de la fraction de survivants, et deux tests
# comparaient la mesure à cette prédiction.
#
# Il est remplacé par trois propriétés mesurées sur le moteur lui-même
# (`sim/tests/test_survie.py`) : le monde ne meurt pas et ne nourrit pas plus
# de monde qu'il ne produit ; la survie répond aux constantes de mortalité ;
# la survie répond à la nourriture.
#
# La raison n'est pas le poids, c'est que la dérivation suppose UNE capacité
# de charge globale, `cap = F x rendement_moyen / C`. Dès que la production
# varie d'une cellule à l'autre — ce que fait le prochain pas du modèle, le
# relief — cette grandeur n'existe plus. Mesuré : avec le relief qui joue, la
# survie tombe à 0.447 contre une prédiction de 0.797 +/- 0.101, soit 3,5 fois
# la tolérance. Le test devient rouge sans qu'aucun défaut n'existe, et la
# seule issue commode est d'élargir la tolérance après avoir vu la mesure —
# exactement la calibration après mesure que ce fichier interdisait.
#
# La garde payée par un vrai défaut est conservée : le critère de survie ne
# doit pas être aveugle aux constantes qui gouvernent la mort. Elle est tenue
# par la DIRECTION de la réponse, mesurée sur le moteur, qui survit à tout
# changement du modèle de production.

# --- Borne de ticks pour qu'une fraction de mort devienne une mort entière ---
# N_BOUND_MORT = ceil(1 / MAX_DEATH_RATE_PER_TICK) : au plafond de mortalité,
# une cellule accumule au moins MAX_DEATH_RATE_PER_TICK mort par habitant et
# par tick ; le report de la fraction (mortality_remainder) garantit qu'une
# mort entière est appliquée en au plus ce nombre de ticks.
N_BOUND_MORT = math.ceil(1.0 / MAX_DEATH_RATE_PER_TICK)

# --- Migration de famine ---

# Part de la population d'une cellule affamée qui émigre en un tick.
# Niveau 2 : ordre de grandeur plausible, jamais sourcé (voir MODELE.md).
FRACTION_MIGRANTE_PAR_TICK = 0.01

# --- Entrée en ligne de commande (python -m sim) ---
# Un an calendaire de ticks, dérivé de la base de temps unique : jamais un
# second littéral de durée. TICK_DURATION_DAYS vaut 1 aujourd'hui.
CALENDAR_DAYS_PER_YEAR = 365

# Année de départ du calendrier simplifié (niveau 2) ; cadre produit 1400-1900.
ANNEE_INITIALE = 1400


def date_de_tick(ticks_ecoules: int) -> dict[str, int]:
    """
    Date calendaire dérivée du nombre de ticks terminés depuis l'amorçage.

    Relit TICK_DURATION_DAYS, CALENDAR_DAYS_PER_YEAR et ANNEE_INITIALE à chaque appel.
    """
    if isinstance(ticks_ecoules, bool) or not isinstance(ticks_ecoules, int):
        raise ValueError(
            f"ticks_ecoules invalide : reçu {ticks_ecoules!r}, attendu un entier non négatif"
        )
    if ticks_ecoules < 0:
        raise ValueError(
            f"ticks_ecoules invalide : reçu {ticks_ecoules}, attendu un entier non négatif"
        )
    jours_ecoules = ticks_ecoules * TICK_DURATION_DAYS
    annees_ecoulees, rang_jour = divmod(jours_ecoules, CALENDAR_DAYS_PER_YEAR)
    return {
        "annee": ANNEE_INITIALE + annees_ecoulees,
        "jour_de_l_annee": rang_jour + 1,
    }


DEFAULT_CLI_TICKS = CALENDAR_DAYS_PER_YEAR * TICK_DURATION_DAYS
DEFAULT_CLI_SEED = 0

# --- Snapshot cellulaire ---
# Photographie cellulaire déterministe ; le suffixe numéroté permet une
# révision du contrat sans réutiliser le même nom.
SNAPSHOT_SCHEMA_VERSION = "v0a-4"
# Plus fin serait du bruit, plus gros écraserait des centroïdes voisins.
SNAPSHOT_FLOAT_DECIMALS = 6
