"""
Moteur de simulation : boucle de tick.

`tick(world, rng)` avance le monde d'un pas de temps. Huit maillons, dans
cet ordre — l'ordre est la mécanique, pas une convention :

    _apply_fabrication → les matières premières deviennent de l'objet
    _apply_extraction  → les gisements rendent des kg dans le panier
    _apply_production  → la nourriture pousse, avec variabilité rng
    _apply_commerce    → les marchandises circulent entre cellules voisines
    _apply_consumption → on mange ; ce qui manque devient une dette en kg
    _update_hunger     → la faim suit la pénurie du tick, pas le stock restant
    _apply_mortality   → on meurt de la dette, proportionnellement
    _apply_natalite    → on naît là où on est rassasié et sans dette
    _apply_migration   → les affamés rejoignent un surplus par terre ou par mer

Le commerce vient avant la consommation : on mange ce qui vient d'arriver.
Il est calculé sur un instantané immuable, pour qu'un transfert ne dépende
pas de l'ordre de parcours des cellules, et il ne touche jamais à la dette.

Aucun littéral numérique nu dans les fonctions de calcul : toutes les
constantes réglables vivent dans `sim/constants.py`.
"""

import math
import random
from collections import defaultdict

from sim import constants as _constantes
from sim.model import Cell, cellule_vers_dict, ecrire_stock_marchandise, lire_stock_marchandise

# Carte lue pendant un tick sur un monde chargé ; None hors tick ou sans carte.
_carte_du_tick: dict | None = None


class ReliefInvalideError(ValueError):
    """Classe de relief absente ou inconnue sur une cellule du monde chargé."""


class ClimatInvalideError(ValueError):
    """Climat absent ou durée de solstice invalide sur une cellule du monde chargé."""


class LongueurFrontiereInvalideError(ValueError):
    """Longueur de frontière non numérique ou NaN sur une arête."""


class LongueurFacadeMaritimeInvalideError(ValueError):
    """Longueur de façade maritime absente ou non numérique sur une arête."""


class NoeudsMerMultiplesError(ValueError):
    """Plus d'un nœud hors du monde sur les arêtes maritimes."""


class KindsMaritimesMultiplesError(ValueError):
    """Plus d'une valeur de kind sur les arêtes maritimes identifiées."""


class RichesseGisementInvalideError(ValueError):
    """Classe de richesse absente ou inconnue sur un gisement de la carte."""

# Le moteur lit TOUTES ses constantes réglables par le module `_constantes`,
# jamais par `from sim.constants import ...`. Un nom importé par valeur est
# figé au chargement : le remplacer en mémoire ne change alors rien au moteur,
# et un test de régime mesure un moteur inchangé en croyant mesurer le régime.
# La règle est uniforme et vérifiée par sim/tests/test_write_coverage.py.

def _facteur_relief_pour_cellule(cell: Cell, carte: dict) -> float:
    """Lit world.carte[cell_id]["relief"] et refuse toute classe inconnue."""
    raw = carte.get(cell.cell_id)
    if raw is None:
        raise ReliefInvalideError(
            f"cell_id={cell.cell_id} relief=absent de world.carte"
        )
    relief = raw.get("relief")
    if relief is None:
        raise ReliefInvalideError(
            f"cell_id={cell.cell_id} relief=None"
        )
    facteurs = _constantes.facteurs_production_par_relief()
    if relief not in facteurs:
        raise ReliefInvalideError(
            f"cell_id={cell.cell_id} relief={relief!r}"
        )
    return facteurs[relief]


def _lire_solstices(cell: Cell, carte: dict) -> tuple[float, float]:
    """Lit les deux durées de solstice depuis world.carte[cell_id]["climat"]."""
    raw = carte.get(cell.cell_id)
    if raw is None:
        raise ClimatInvalideError(
            f"cell_id={cell.cell_id} climat=absent de world.carte"
        )
    climat = raw.get("climat")
    if climat is None:
        raise ClimatInvalideError(
            f"cell_id={cell.cell_id} climat=None"
        )
    cle_ete = "duree_jour_solstice_ete_h"
    cle_hiver = "duree_jour_solstice_hiver_h"
    ete_h = climat.get(cle_ete)
    hiver_h = climat.get(cle_hiver)
    if not isinstance(ete_h, (int, float)) or isinstance(ete_h, bool):
        raise ClimatInvalideError(
            f"cell_id={cell.cell_id} {cle_ete}={ete_h!r}"
        )
    if not isinstance(hiver_h, (int, float)) or isinstance(hiver_h, bool):
        raise ClimatInvalideError(
            f"cell_id={cell.cell_id} {cle_hiver}={hiver_h!r}"
        )
    return float(ete_h), float(hiver_h)


def _facteur_saison_pour_cellule(cell: Cell, carte: dict, jour: int) -> float:
    """Facteur saisonnier dérivé du climat de la cellule et du jour de l'année."""
    ete_h, hiver_h = _lire_solstices(cell, carte)
    duree = _constantes.duree_jour_h(jour, ete_h, hiver_h)
    return _constantes.facteur_saison(duree)


def _gisements_de(cell: Cell, carte: dict):
    """Liste des gisements de la cellule, ou None si la carte n'en porte pas."""
    raw = carte.get(cell.cell_id)
    if raw is None:
        return None
    return raw.get("gisements")


def _facteur_agricole(cell: Cell, carte: dict) -> float:
    """Part qui reste aux champs : 1 moins la part minière de la cellule."""
    return 1.0 - _constantes.part_miniere_de(
        _gisements_de(cell, carte),
        _constantes.facteurs_richesse_extraction(),
    )


def _production_base_kg(cell: Cell, yield_factor: float) -> float:
    """Noyau commun de l'unique formule de production alimentaire."""
    return (
        cell.area_km2
        * _constantes.FOOD_PRODUCTION_KG_PER_KM2_PER_TICK
        * yield_factor
    )


def production_du_tick_kg(
    cell: Cell,
    yield_factor: float,
    carte: dict,
    jour: int | None = None,
) -> float:
    """
    Production alimentaire d'une cellule pendant un tick, avec relief, saison
    et part minière lus depuis la carte passée en argument.

    `jour` facultatif : sans jour, relief et part minière seulement (appels
    historiques à trois arguments). Avec un jour explicite, le facteur saisonnier
    s'ajoute — premier jour de l'année via `jour_de_tick(None)`.
    """
    base = _production_base_kg(cell, yield_factor)
    relief = _facteur_relief_pour_cellule(cell, carte)
    agricole = _facteur_agricole(cell, carte)
    produit = base * relief * agricole
    if jour is None:
        return produit
    return produit * _facteur_saison_pour_cellule(cell, carte, jour)


def _production_du_tick_kg_saison_moyenne(
    cell: Cell, yield_factor: float, carte: dict
) -> float:
    """Même formule que le tick, avec le facteur saisonnier moyen sur l'année."""
    ete_h, hiver_h = _lire_solstices(cell, carte)
    saison_moyenne = _constantes.facteur_saison_moyen_annuel(ete_h, hiver_h)
    return production_du_tick_kg(cell, yield_factor, carte) * saison_moyenne


def production_kg(cell: Cell, yield_factor: float) -> float:
    """
    Ce qu'une cellule produit en un tick pour un rendement donné.

    UNE seule formule de production dans le moteur, deux lecteurs : le tick,
    qui lui passe un rendement tiré au sort, et `production_moyenne_kg_par_tick`,
    qui lui passe le rendement moyen. Le plafond physique de survie s'en déduit,
    donc il ne peut pas diverger de ce que le moteur produit vraiment.

    Sur un monde chargé (carte non vide), le relief de world.carte modère la
    production pendant le tick via `_carte_du_tick`. Sans carte, le chemin
    unitaire historique reste inchangé.
    """
    if _carte_du_tick:
        return production_du_tick_kg(cell, yield_factor, _carte_du_tick)
    return _production_base_kg(cell, yield_factor)


def population_soutenable_de(cell: Cell, carte: dict) -> float:
    """
    Combien d'habitants cette cellule nourrit durablement, au rendement moyen.

    DÉRIVÉE de l'unique formule de production du moteur, facteur saisonnier
    moyen compris : c'est exactement ce que le tick produira sur l'année. Le
    plafond ne peut donc pas diverger de ce que le monde produit, et il suivra
    tout seul le jour où le relief, la saison ou la part minière changeront.

    Lue à l'amorçage (`sim.world`) et par personne d'autre : le tick ne la
    consulte jamais. Une cellule qui ne produit rien nourrit zéro habitant —
    et c'est un zéro mesuré, pas une sentinelle.
    """
    rendement_moyen = _constantes.rendement_moyen_courant()
    produite_kg = _production_du_tick_kg_saison_moyenne(cell, rendement_moyen, carte)
    return produite_kg / _constantes.FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK


def production_moyenne_kg_par_tick(world) -> float:
    """
    Nourriture que le monde produit en un tick au rendement moyen.

    Sert de référence DÉRIVÉE au plafond physique de survie : une population
    ne peut pas manger durablement plus que ce que son monde produit
    (`sim/tests/test_survie.py`). Elle n'est jamais lue par le tick.
    """
    rendement_moyen = _constantes.rendement_moyen_courant()
    if not world.carte:
        return sum(
            production_kg(cell, rendement_moyen) for cell in world.cells.values()
        )
    return sum(
        _production_du_tick_kg_saison_moyenne(cell, rendement_moyen, world.carte)
        for cell in world.cells.values()
    )



def _extraction_du_tick_kg(cell: Cell, carte: dict) -> dict[str, float]:
    """
    Kilogrammes extraits ce tick, regroupés par ressource.

    Le débit porte sur la part minière de la population, pas sur la
    population entière. Ignore les enregistrements sans clé ressource ou
    richesse (sonde snapshot). Refuse une richesse présente mais hors des
    trois classes dérivées.
    """
    raw = carte.get(cell.cell_id)
    if raw is None:
        return {}
    gisements = raw.get("gisements")
    if not gisements:
        return {}

    facteurs = _constantes.facteurs_richesse_extraction()
    debit_unitaire = _constantes.extraction_kg_par_habitant_par_tick()
    part = _constantes.part_miniere_de(gisements, facteurs)

    valides = []
    for gisement in gisements:
        if not isinstance(gisement, dict):
            continue
        ressource = gisement.get("ressource")
        richesse = gisement.get("richesse")
        if ressource is None or richesse is None:
            continue
        if richesse not in facteurs:
            gisement_id = gisement.get("id", gisement.get("nom", "?"))
            raise RichesseGisementInvalideError(
                f"cell_id={cell.cell_id} gisement={gisement_id!r} richesse={richesse!r}"
            )
        valides.append(gisement)

    if not valides:
        return {}

    poids = []
    poids_total = 0.0
    for gisement in valides:
        p_g = _constantes.part_miniere_de([gisement], facteurs)
        poids.append((gisement.get("ressource"), p_g))
        poids_total += p_g

    par_ressource: dict[str, float] = {}
    if part == 0.0 or poids_total == 0.0:
        return {}
    mineurs = cell.population * part
    for ressource, p_g in poids:
        extraction = mineurs * debit_unitaire * (p_g / poids_total)
        par_ressource[ressource] = par_ressource.get(ressource, 0.0) + extraction

    return par_ressource


def _matieres_premieres_du_panier(cell: Cell) -> list[str]:
    """Noms des matières premières présentes dans le panier, ordre stable."""
    panier = cellule_vers_dict(cell).get("stocks") or {}
    nourriture = _constantes.MARCHANDISE_NOURRITURE
    objet = _constantes.MARCHANDISE_OBJET
    return sorted(m for m in panier if m not in (nourriture, objet))


def _apply_fabrication(cell: Cell) -> None:
    """
    Maillon 0 — Façonnage des matières premières en objet, sur le panier
    d'ouverture de tick (avant extraction du jour).
    """
    objet = _constantes.MARCHANDISE_OBJET
    for marchandise in _matieres_premieres_du_panier(cell):
        stock = lire_stock_marchandise(cell, marchandise)
        if stock <= 0:
            continue
        consomme, produit = _constantes.fabrication_kg(stock)
        ecrire_stock_marchandise(cell, marchandise, stock - consomme)
        objet_actuel = lire_stock_marchandise(cell, objet)
        base_objet = objet_actuel if objet_actuel >= 0 else 0.0
        ecrire_stock_marchandise(cell, objet, base_objet + produit)


def _apply_extraction(cell: Cell, carte: dict) -> None:
    """Maillon 0 — Extraction minière depuis la carte vers le panier de la cellule."""
    for ressource, quantite in _extraction_du_tick_kg(cell, carte).items():
        actuel = lire_stock_marchandise(cell, ressource)
        base = actuel if actuel >= 0 else 0.0
        ecrire_stock_marchandise(cell, ressource, base + quantite)


def _apply_production(
    cell: Cell,
    rng: random.Random,
    carte: dict | None = None,
    jour: int | None = None,
) -> None:
    """
    Maillon 1 — Production.
    Calcule la nourriture produite avec un facteur de rendement aléatoire
    tiré du rng (fluctuations climatiques/agronomiques) et l'ajoute au stock.
    Traite la sentinelle -1 comme un stock initial nul.
    """
    yield_factor = rng.uniform(_constantes.RNG_YIELD_LOW, _constantes.RNG_YIELD_HIGH)
    if carte:
        food_produced = production_du_tick_kg(cell, yield_factor, carte, jour=jour)
    else:
        food_produced = production_kg(cell, yield_factor)
    current = lire_stock_marchandise(cell, _constantes.MARCHANDISE_NOURRITURE)
    current = current if current >= 0 else 0.0
    ecrire_stock_marchandise(cell, _constantes.MARCHANDISE_NOURRITURE, current + food_produced)


def _apply_production_saison_moyenne(
    cell: Cell, rng: random.Random, carte: dict
) -> None:
    """
    Production avec le facteur saisonnier moyen annuel.

    Chemin des appelants historiques qui n'indiquent pas de numéro de tick
    (sonde des couches, test_survie) : la moyenne annuelle vaut 1 au niveau 2
    et reproduit l'ancien régime de production.
    """
    yield_factor = rng.uniform(_constantes.RNG_YIELD_LOW, _constantes.RNG_YIELD_HIGH)
    food_produced = _production_du_tick_kg_saison_moyenne(cell, yield_factor, carte)
    current = lire_stock_marchandise(cell, _constantes.MARCHANDISE_NOURRITURE)
    current = current if current >= 0 else 0.0
    ecrire_stock_marchandise(cell, _constantes.MARCHANDISE_NOURRITURE, current + food_produced)


def _cle_arête(a_id: int, b_id: int) -> tuple[int, int]:
    """Clé non orientée d'une arête d'adjacence."""
    return (min(a_id, b_id), max(a_id, b_id))


def _facteur_transport_pour_cellule(cell_id: int, carte: dict) -> float:
    """Lit world.carte[cell_id]["relief"] et refuse toute classe inconnue."""
    raw = carte.get(cell_id)
    if raw is None:
        raise ReliefInvalideError(
            f"cell_id={cell_id} relief=absent de world.carte"
        )
    relief = raw.get("relief")
    if relief is None:
        raise ReliefInvalideError(
            f"cell_id={cell_id} relief=None"
        )
    facteurs = _constantes.facteurs_transport_par_relief()
    if relief not in facteurs:
        raise ReliefInvalideError(
            f"cell_id={cell_id} relief={relief!r}"
        )
    return facteurs[relief]


def _arete_adjacence(world, a_id: int, b_id: int) -> dict | None:
    """Entrée d'adjacence appariée aux deux cell_id, sans recalcul."""
    for edge in world.adjacency:
        ea = edge["a"]
        eb = edge["b"]
        if (ea == a_id and eb == b_id) or (ea == b_id and eb == a_id):
            return edge
    return None


def _capacite_base_arete_kg(world, a_id: int, b_id: int) -> float:
    """
    Capacité dérivée de shared_length_m sur l'arête, ou repli plat.

    Longueur absente : repli TRADE_CAPACITY_KG_PER_EDGE_PER_TICK.
    Longueur non numérique : erreur nommant les deux cell_id.
    Longueur nulle : zéro réel (frontière ponctuelle).
    """
    edge = _arete_adjacence(world, a_id, b_id)
    if edge is None or "shared_length_m" not in edge:
        return _constantes.TRADE_CAPACITY_KG_PER_EDGE_PER_TICK
    raw = edge["shared_length_m"]
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise LongueurFrontiereInvalideError(
            f"cell_id={a_id} cell_id={b_id} shared_length_m={raw!r}"
        )
    longueur_m = float(raw)
    if math.isnan(longueur_m):
        raise LongueurFrontiereInvalideError(
            f"cell_id={a_id} cell_id={b_id} shared_length_m={raw!r}"
        )
    if longueur_m == 0.0:
        return 0.0
    return (
        _constantes.DEBIT_KG_PAR_KM_DE_FRONTIERE_PAR_TICK
        * (longueur_m / _constantes.metres_par_km())
    )


def _capacite_transport_arete_kg(world, a_id: int, b_id: int) -> float:
    """
    Capacité de transport d'une arête terrestre entre deux cellules du monde.

    Base dérivée de shared_length_m sur l'adjacence, puis goulot de relief
    si une carte est chargée.
    """
    base = _capacite_base_arete_kg(world, a_id, b_id)
    if base == 0.0:
        return 0.0
    carte = getattr(world, "carte", None)
    if not carte:
        return base
    try:
        fa = _facteur_transport_pour_cellule(a_id, carte)
        fb = _facteur_transport_pour_cellule(b_id, carte)
    except ReliefInvalideError as e:
        raise ReliefInvalideError(
            f"arête ({a_id},{b_id}) : {e}"
        ) from e
    facteur = min(fa, fb)
    return base * facteur


def _initialiser_capacite_aretes(world) -> dict[tuple[int, int], float]:
    """Capacité restante par arête au début du maillon commerce."""
    capacite: dict[tuple[int, int], float] = {}
    for edge in world.adjacency:
        a_id = edge["a"]
        b_id = edge["b"]
        if a_id not in world.cells or b_id not in world.cells:
            continue
        cle = _cle_arête(a_id, b_id)
        capacite[cle] = _capacite_transport_arete_kg(world, a_id, b_id)
    return capacite


def _aretes_maritimes_du_monde(world) -> list[tuple[int, int, dict]]:
    """
    Arêtes dont exactement un bout est une cellule du monde.

    Retourne (cell_id, noeud_mer, arête) pour chaque arête maritime.
    """
    cell_ids = set(world.cells.keys())
    maritimes: list[tuple[int, int, dict]] = []
    kinds: set[str] = set()
    noeuds_mer: set[int] = set()
    for edge in world.adjacency:
        a_id = edge["a"]
        b_id = edge["b"]
        a_in = a_id in cell_ids
        b_in = b_id in cell_ids
        if a_in == b_in:
            continue
        if a_in:
            cell_id, noeud = a_id, b_id
        else:
            cell_id, noeud = b_id, a_id
        maritimes.append((cell_id, noeud, edge))
        noeuds_mer.add(noeud)
        if "kind" in edge:
            kinds.add(edge["kind"])
    if len(noeuds_mer) > 1:
        ids_tries = sorted(noeuds_mer)
        raise NoeudsMerMultiplesError(
            f"noeuds_mer={ids_tries}"
        )
    if len(kinds) > 1:
        valeurs = sorted(kinds)
        raise KindsMaritimesMultiplesError(
            f"kinds_maritimes={valeurs!r}"
        )
    return maritimes


def _lire_longueur_facade_maritime_m(
    edge: dict, cell_id: int, noeud_mer: int,
) -> float:
    """Lit shared_length_m sur une arête maritime ; refuse l'absence."""
    if "shared_length_m" not in edge:
        raise LongueurFacadeMaritimeInvalideError(
            f"cell_id={cell_id} noeud_mer={noeud_mer} shared_length_m=absent"
        )
    raw = edge["shared_length_m"]
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise LongueurFacadeMaritimeInvalideError(
            f"cell_id={cell_id} noeud_mer={noeud_mer} shared_length_m={raw!r}"
        )
    longueur_m = float(raw)
    if math.isnan(longueur_m):
        raise LongueurFacadeMaritimeInvalideError(
            f"cell_id={cell_id} noeud_mer={noeud_mer} shared_length_m={raw!r}"
        )
    return longueur_m


def _capacite_quai_cellule_kg(
    world,
    cell_id: int,
    aretes_cellule: list[tuple[int, int, dict]],
) -> float:
    """Capacité de quai dérivée des façades maritimes d'une cellule."""
    if not aretes_cellule:
        return 0.0
    carte = getattr(world, "carte", None)
    facteur = 1.0
    if carte:
        facteur = _facteur_transport_pour_cellule(cell_id, carte)
    total = 0.0
    debit = _constantes.debit_maritime_kg_par_km()
    km = _constantes.metres_par_km()
    for _, noeud, edge in aretes_cellule:
        longueur_m = _lire_longueur_facade_maritime_m(edge, cell_id, noeud)
        total += debit * (longueur_m / km) * facteur
    return total


def _initialiser_contexte_maritime(world) -> dict:
    """
    Contexte partagé entre toutes les marchandises d'un tick maritime.

    capacite_quai_restante est décrémentée au fil des marchandises ;
    bassin_au_debut est une copie immuable du panier mer au début du tick.
    """
    from sim.world import lire_stock_mer

    aretes = _aretes_maritimes_du_monde(world)
    par_cellule: dict[int, list[tuple[int, int, dict]]] = defaultdict(list)
    for cell_id, noeud, edge in aretes:
        par_cellule[cell_id].append((cell_id, noeud, edge))
    capacite_quai: dict[int, float] = {}
    for cell_id, aretes_cellule in par_cellule.items():
        capacite_quai[cell_id] = _capacite_quai_cellule_kg(
            world, cell_id, aretes_cellule,
        )
    stocks_mer = world.stocks_mer
    bassin_au_debut = dict(stocks_mer)
    return {
        "aretes_par_cellule": par_cellule,
        "capacite_quai_restante": capacite_quai,
        "bassin_au_debut": bassin_au_debut,
        "cellules_cotieres": set(par_cellule.keys()),
    }


def _stock_bassin_au_debut(ctx_maritime: dict, marchandise: str) -> float:
    """Quantité de marchandise dans le bassin au début du tick."""
    raw = ctx_maritime["bassin_au_debut"].get(marchandise)
    if raw is None:
        return 0.0
    return max(0.0, float(raw))


def _planifier_debarquement(
    needs: dict[int, float],
    capacite_quai: dict[int, float],
    bassin_dispo: float,
    cellules_cotieres: set[int],
) -> dict[int, float]:
    """Débarquement depuis le bassin, proportionnel au besoin si insuffisant."""
    if bassin_dispo <= 0.0:
        return {}
    requests: list[tuple[int, float, float]] = []
    for cid in sorted(cellules_cotieres):
        besoin = needs.get(cid, 0.0)
        if besoin <= 0.0:
            continue
        cap = capacite_quai.get(cid, 0.0)
        demande = min(besoin, cap)
        if demande > 0.0:
            requests.append((cid, besoin, demande))
    if not requests:
        return {}
    total_demande = sum(d for _, _, d in requests)
    total_besoin = sum(b for _, b, _ in requests)
    debark: dict[int, float] = {}
    if total_demande <= bassin_dispo:
        for cid, _, demande in requests:
            debark[cid] = demande
    else:
        for cid, besoin, demande in requests:
            part = bassin_dispo * (besoin / total_besoin)
            debark[cid] = min(part, demande, besoin)
    return debark


def _cellules_declarant_gisements(carte: dict) -> set[int]:
    """Cellules dont la carte porte au moins un gisement (couche 1, extraction locale)."""
    return {
        int(cell_id)
        for cell_id, raw in carte.items()
        if isinstance(raw, dict) and (raw.get("gisements") or [])
    }


def _planifier_expedition(
    surplus_apres_terre: dict[int, float],
    capacite_quai: dict[int, float],
    cellules_cotieres: set[int],
    exclure_cellules: set[int] | None = None,
) -> dict[int, float]:
    """Expédition vers le bassin depuis les cellules côtières en surplus."""
    expedition: dict[int, float] = {}
    exclus = exclure_cellules or set()
    for cid in sorted(cellules_cotieres):
        if cid in exclus:
            continue
        surplus = surplus_apres_terre.get(cid, 0.0)
        if surplus <= 0.0:
            continue
        cap = capacite_quai.get(cid, 0.0)
        qty = min(surplus, cap)
        if qty > 0.0:
            expedition[cid] = qty
    return expedition


def _appliquer_flux_maritimes(
    world,
    marchandise: str,
    debark: dict[int, float],
    expedition: dict[int, float],
    capacite_quai: dict[int, float],
    total_transported: list,
) -> None:
    """Applique débarquement et expédition ; met à jour le bassin et les quais."""
    from sim.world import ecrire_stock_mer, lire_stock_mer

    for cid, qty in debark.items():
        if qty <= 0.0:
            continue
        cell = world.cells[cid]
        stock = lire_stock_marchandise(cell, marchandise)
        eff = stock if stock >= 0 else 0.0
        ecrire_stock_marchandise(cell, marchandise, eff + qty)
        bassin = lire_stock_mer(world, marchandise)
        bassin_eff = bassin if bassin >= 0 else 0.0
        ecrire_stock_mer(world, marchandise, bassin_eff - qty)
        total_transported[0] += qty
        capacite_quai[cid] = max(0.0, capacite_quai.get(cid, 0.0) - qty)
    for cid, qty in expedition.items():
        if qty <= 0.0:
            continue
        cell = world.cells[cid]
        stock = lire_stock_marchandise(cell, marchandise)
        eff = stock if stock >= 0 else 0.0
        ecrire_stock_marchandise(cell, marchandise, eff - qty)
        bassin = lire_stock_mer(world, marchandise)
        bassin_eff = bassin if bassin >= 0 else 0.0
        ecrire_stock_mer(world, marchandise, bassin_eff + qty)
        total_transported[0] += qty
        capacite_quai[cid] = max(0.0, capacite_quai.get(cid, 0.0) - qty)


def _marchandises_du_monde(world) -> list[str]:
    """Marchandises jouées : clés de panier présentes, plus la ration alimentaire."""
    noms: set[str] = set()
    if hasattr(world, "to_dict"):
        cellules = world.to_dict()["cells"].values()
        for entree in cellules:
            panier = entree.get("stocks") or {}
            noms.update(panier)
    else:
        for cell in world.cells.values():
            panier = cellule_vers_dict(cell).get("stocks") or {}
            noms.update(panier)
    noms.add(_constantes.MARCHANDISE_NOURRITURE)
    return sorted(noms)


def _apply_commerce(
    world,
    total_transported: list,
    marchandise: str | None = None,
    capacite_restante: dict[tuple[int, int], float] | None = None,
    ctx_maritime: dict | None = None,
) -> None:
    """
    Maillon 2 — Commerce inter-cellules.

    Transporte la marchandise passée en paramètre. Sans paramètre de marchandise,
    joue toutes les marchandises dérivées du monde dans un ordre stable, avec un
    plafond d'arête partagé entre elles pour le tick.

    Calcul en deux passes sur snapshot pour garantir le transport atomique
    (un kg ne traverse au plus qu'une arête par tick) et l'invariance à
    l'ordre des arêtes.

    Définition du besoin et du surplus (détaillée dans sim/MODELE.md) :
    - besoin d'une cellule = max(0, consommation_tick - stock_snapshot)
      (manque prévisible du tick courant)
    - surplus d'une cellule = max(0, stock_snapshot - consommation_tick)
      (excédent disponible après sa propre alimentation du tick)

    Allocation déterministe (plusieurs demandeurs sur la même source) :
    - Les demandes sont triées par cell_id croissant (ordre stable).
    - Si la somme des demandes dépasse le surplus de la source, chaque
      receveur reçoit une part proportionnelle à son besoin.
    - Le transfert par arête est borné par la capacité restante de l'arête.

    Conservation stricte : seul le stock de la marchandise courante est modifié.
    food_deficit_kg n'est jamais touché par ce maillon.
    `total_transported` est une liste à un élément (accumulateur mutable).
    """
    if marchandise is None:
        if capacite_restante is None:
            capacite_restante = _initialiser_capacite_aretes(world)
        ctx = None
        if getattr(world, "stocks_mer", None) is not None:
            aretes = _aretes_maritimes_du_monde(world)
            if aretes:
                ctx = _initialiser_contexte_maritime(world)
        for nom in _marchandises_du_monde(world):
            _apply_commerce(
                world, total_transported, nom, capacite_restante, ctx,
            )
        return

    consommation_unitaire = _constantes.consommation_kg_par_habitant_par_tick(marchandise)
    # Le commerce maritime ne porte que les marchandises consommées : les autres
    # n'ont ni besoin côté mer ni rôle d'expédition dans la couche 1.
    maritime_actif = (
        ctx_maritime is not None and consommation_unitaire > 0.0
    )

    # Passe 1a : snapshot immuable des stocks et populations
    snapshot_stock = {
        cid: max(0.0, lire_stock_marchandise(cell, marchandise))
        for cid, cell in world.cells.items()
    }
    snapshot_pop = {cid: cell.population for cid, cell in world.cells.items()}

    def _tick_consumption(cid: int) -> float:
        return snapshot_pop[cid] * consommation_unitaire

    def _surplus(cid: int) -> float:
        return max(0.0, snapshot_stock[cid] - _tick_consumption(cid))

    def _need(cid: int) -> float:
        return max(0.0, _tick_consumption(cid) - snapshot_stock[cid])

    snapshot_needs = {cid: _need(cid) for cid in world.cells}

    # --- Flux maritime : débarquement planifié sur bassin_au_debut ---
    debark_brut: dict[int, float] = {}
    debark_final: dict[int, float] = {}
    if maritime_actif:
        bassin_dispo = _stock_bassin_au_debut(ctx_maritime, marchandise)
        debark_brut = _planifier_debarquement(
            snapshot_needs,
            ctx_maritime["capacite_quai_restante"],
            bassin_dispo,
            ctx_maritime["cellules_cotieres"],
        )

    # Passe 1b : collecter les demandes par source, triées par cell_id receveur
    by_source: dict[int, list[tuple[int, float, tuple[int, int]]]] = defaultdict(list)

    for edge in world.adjacency:
        a_id = edge["a"]
        b_id = edge["b"]
        if a_id not in world.cells or b_id not in world.cells:
            continue

        cle = _cle_arête(a_id, b_id)
        if cle in capacite_restante:
            cap_arête = capacite_restante[cle]
        else:
            cap_arête = _capacite_transport_arete_kg(world, a_id, b_id)

        surplus_a = _surplus(a_id)
        surplus_b = _surplus(b_id)
        need_a = _need(a_id)
        need_b = _need(b_id)

        if surplus_a > 0 and need_b > 0:
            demand = min(need_b, cap_arête)
            by_source[a_id].append((b_id, demand, cle))

        elif surplus_b > 0 and need_a > 0:
            demand = min(need_a, cap_arête)
            by_source[b_id].append((a_id, demand, cle))

    transfers: list[tuple[int, int, float, tuple[int, int]]] = []

    for source_id in sorted(by_source.keys()):
        requests = sorted(by_source[source_id], key=lambda r: r[0])
        avail = _surplus(source_id)
        total_req = sum(d for _, d, _ in requests)

        for receiver_id, demand, cle in requests:
            if total_req <= avail:
                transfer = demand
            else:
                transfer = avail * (demand / total_req)
                transfer = min(transfer, demand)
            if transfer > 0:
                transfers.append((source_id, receiver_id, transfer, cle))

    by_receiver: dict[int, list[tuple[int, float, tuple[int, int]]]] = defaultdict(list)
    for src, rcv, qty, cle in transfers:
        by_receiver[rcv].append((src, qty, cle))

    final_transfers: list[tuple[int, int, float, tuple[int, int]]] = []
    receveurs = set(by_receiver.keys())
    if maritime_actif:
        receveurs |= set(debark_brut.keys())

    for rcv_id in sorted(receveurs):
        incoming = by_receiver.get(rcv_id, [])
        terre_total = sum(qty for _, qty, _ in incoming)
        mer_total = debark_brut.get(rcv_id, 0.0)
        need_r = snapshot_needs[rcv_id]
        total_in = terre_total + mer_total
        if total_in > need_r and total_in > 0.0:
            scale = need_r / total_in
            for src_id, qty, cle in incoming:
                scaled = qty * scale
                if scaled > 0.0:
                    final_transfers.append((src_id, rcv_id, scaled, cle))
            if maritime_actif and mer_total > 0.0:
                debark_final[rcv_id] = mer_total * scale
        else:
            for src_id, qty, cle in incoming:
                final_transfers.append((src_id, rcv_id, qty, cle))
            if maritime_actif and mer_total > 0.0:
                debark_final[rcv_id] = mer_total

    # --- Flux maritime : expédition après allocation terrestre ---
    expedition_brute: dict[int, float] = {}
    if maritime_actif:
        outgoing_terre: dict[int, float] = defaultdict(float)
        for src_id, _, qty, _ in final_transfers:
            outgoing_terre[src_id] += qty
        surplus_apres: dict[int, float] = {}
        for cid in world.cells:
            surplus_apres[cid] = max(
                0.0, _surplus(cid) - outgoing_terre.get(cid, 0.0),
            )
        cap_apres_debark = dict(ctx_maritime["capacite_quai_restante"])
        for cid, qty in debark_final.items():
            cap_apres_debark[cid] = max(
                0.0, cap_apres_debark.get(cid, 0.0) - qty,
            )
        carte = getattr(world, "carte", None) or {}
        exclure = _cellules_declarant_gisements(carte)
        expedition_brute = _planifier_expedition(
            surplus_apres,
            cap_apres_debark,
            ctx_maritime["cellules_cotieres"],
            exclure_cellules=exclure,
        )

    consomme_par_arête: dict[tuple[int, int], float] = defaultdict(float)
    for source_id, receiver_id, transfer, cle in final_transfers:
        source_cell = world.cells[source_id]
        receiver_cell = world.cells[receiver_id]
        source_stock = lire_stock_marchandise(source_cell, marchandise)
        source_eff = source_stock if source_stock >= 0 else 0.0
        ecrire_stock_marchandise(
            source_cell, marchandise, source_eff - transfer
        )
        receiver_stock = lire_stock_marchandise(receiver_cell, marchandise)
        receiver_eff = receiver_stock if receiver_stock >= 0 else 0.0
        ecrire_stock_marchandise(
            receiver_cell, marchandise, receiver_eff + transfer
        )
        total_transported[0] += transfer
        consomme_par_arête[cle] += transfer

    for cle, qty in consomme_par_arête.items():
        if cle in capacite_restante:
            restant = capacite_restante[cle]
        else:
            restant = _capacite_transport_arete_kg(world, cle[0], cle[1])
        capacite_restante[cle] = max(0.0, restant - qty)

    if maritime_actif:
        _appliquer_flux_maritimes(
            world,
            marchandise,
            debark_final,
            expedition_brute,
            ctx_maritime["capacite_quai_restante"],
            total_transported,
        )


def _apply_consumption(cell: Cell) -> float:
    """
    Maillon 3 — Consommation.

    Lit le stock de nourriture (après commerce), soustrait la consommation, et retourne
    la pénurie du tick en kg (0.0 s'il n'y a pas eu de manque). Cette valeur
    de retour est le critère causal de la faim : c'est elle, et non un stock
    vide, qui dit qu'une cellule a MANQUÉ de nourriture ce tick.

    Si stock ≥ consommation (surplus ou égalité) :
        - le surplus disponible est `remaining`
        - la dette alimentaire est remboursée par des kilogrammes RÉELS :
          remboursement = min(dette, remaining × ratio) où le ratio nommé est
          DEFICIT_RECOVERY_RATE_PER_SURPLUS_KG (1 kg de dette par kg de surplus)
        - ces kilogrammes quittent le stock (ils sont mangés en sus du besoin
          d'entretien) : rien ne se téléporte (principe 3)
        - un surplus d'un nanogramme ne peut donc effacer qu'un nanogramme de
          dette, jamais 10 % d'une dette de 10 000 kg
        - aucun seuil de coupure : la soustraction atteint 0.0 exactement
          quand le surplus couvre, et tout résidu est une dette réelle

    Si stock < consommation (manque) :
        - stock = 0, le manque est ajouté à food_deficit_kg, et la pénurie
          du tick est retournée.
    """
    tick_need = cell.population * _constantes.FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    stock = lire_stock_marchandise(cell, _constantes.MARCHANDISE_NOURRITURE)
    stock_eff = stock if stock >= 0 else 0.0
    remaining = stock_eff - tick_need
    prev_deficit = cell.food_deficit_kg if cell.food_deficit_kg > 0 else 0.0

    if remaining >= 0.0:
        # Le ratio est borné à 1 kg de dette par kg de surplus : la réduction
        # du déficit ne peut jamais dépasser le surplus physique du tick,
        # quelle que soit la valeur donnée à la constante.
        ratio = min(1.0, _constantes.DEFICIT_RECOVERY_RATE_PER_SURPLUS_KG)
        remboursement = min(prev_deficit, max(0.0, remaining) * ratio)
        # Le remboursement est SOUSTRAIT : quand le surplus couvre la dette,
        # `min` rend la dette elle-même et la soustraction donne exactement
        # 0.0. Tout résidu est donc une dette réelle, jamais un artefact de
        # calcul flottant — et l'effacer serait faire disparaître des
        # kilogrammes sans contrepartie (principe 3).
        cell.food_deficit_kg = prev_deficit - remboursement
        ecrire_stock_marchandise(
            cell, _constantes.MARCHANDISE_NOURRITURE, remaining - remboursement
        )
        return 0.0

    shortage = -remaining
    cell.food_deficit_kg = prev_deficit + shortage
    ecrire_stock_marchandise(cell, _constantes.MARCHANDISE_NOURRITURE, 0.0)
    return shortage


def _update_hunger(cell: Cell, penurie_kg: float) -> None:
    """
    Maillon 4 — Faim.

    `penurie_kg` est le manque du tick retourné par _apply_consumption.
    hunger_ticks progresse si et seulement si la cellule a manqué de
    nourriture CE tick.

    Une cellule ravitaillée exactement à son besoin par le commerce termine le
    tick avec un stock nul et un déficit nul : elle a mangé sa ration, elle
    n'est pas affamée. L'ancien critère testait le stock résiduel après
    consommation, ce qui confondait le garde-manger vide et la
    sous-alimentation (voir sim/MODELE.md).
    Traite la sentinelle -1 comme hunger_ticks = 0.
    """
    if penurie_kg > 0.0:
        prev = cell.hunger_ticks if cell.hunger_ticks >= 0 else 0
        cell.hunger_ticks = prev + 1
    else:
        cell.hunger_ticks = 0


def _apply_mortality(cell: Cell) -> None:
    """
    Maillon 5 — Mortalité.

    La mortalité est proportionnelle au déficit alimentaire cumulé par habitant
    (food_deficit_kg / population), plafonnée à MAX_DEATH_RATE_PER_TICK.

    Formule, sans plancher max(1, …) et avec report de la fraction :
        per_capita_deficit = food_deficit_kg / population
        death_rate = min(per_capita_deficit × HUNGER_DEATH_SCALE, MAX_DEATH_RATE_PER_TICK)
        raw    = population × death_rate + mortality_remainder
        deaths = int(raw)
        mortality_remainder = raw - deaths

    Le report de la fraction supprime l'immortalité par arrondi : une cellule
    de 5 habitants en famine totale produit 0.5 mort par tick, que `int()`
    jetait entièrement à chaque tick. La fraction non appliquée est désormais
    conservée et finit par tuer.

    Le taux reste nul si le déficit est infime : aucune mort n'est garantie
    par le seul fait qu'un déficit est non nul.
    """
    remainder = cell.mortality_remainder if cell.mortality_remainder >= 0.0 else 0.0

    if cell.food_deficit_kg > 0 and cell.population > 0:
        per_capita_deficit = cell.food_deficit_kg / cell.population
        death_rate = per_capita_deficit * _constantes.HUNGER_DEATH_SCALE
        death_rate = min(death_rate, _constantes.MAX_DEATH_RATE_PER_TICK)
        raw = cell.population * death_rate + remainder
        deaths = int(raw)
        cell.mortality_remainder = raw - deaths
        cell.population = max(0, cell.population - deaths)
    else:
        # Aucun décès ce tick : la fraction en attente est conservée telle
        # quelle (et la sentinelle -1 devient une mesure réelle : 0.0).
        cell.mortality_remainder = remainder


def _apply_natalite(cell: Cell, penurie_kg: float) -> None:
    remainder = cell.natalite_remainder if cell.natalite_remainder >= 0.0 else 0.0

    if penurie_kg == 0.0 and cell.food_deficit_kg == 0.0 and cell.population > 0:
        rate = _constantes.naissances_par_habitant_par_tick()
        raw = cell.population * rate + remainder
        births = int(raw)
        cell.natalite_remainder = raw - births
        cell.population += births
    else:
        cell.natalite_remainder = remainder


def _surplus_nourriture_tick(population: int, stock: float) -> float:
    """Surplus alimentaire post-consommation sur un instantané migration."""
    stock_eff = stock if stock >= 0 else 0.0
    return max(0.0, stock_eff)


def _repartir_habitants_proportionnellement(
    total: int, poids: dict[int, float]
) -> dict[int, int]:
    """
    Parts entières proportionnelles aux poids ; reliquat par plus fort reste,
    égalité départagée par cell_id croissant.
    """
    if total <= 0 or not poids:
        return {}
    somme_poids = sum(poids.values())
    if somme_poids <= 0.0:
        return {cid: 0 for cid in poids}

    bruts = {cid: total * w / somme_poids for cid, w in poids.items()}
    parts = {cid: int(brut) for cid, brut in bruts.items()}
    reliquat = total - sum(parts.values())
    if reliquat > 0:
        candidats = sorted(
            poids,
            key=lambda cid: (-(bruts[cid] - parts[cid]), cid),
        )
        for cid in candidats[:reliquat]:
            parts[cid] += 1
    return parts


def _voisins_avec_surplus(
    world, source_id: int, surplus_par_cellule: dict[int, float]
) -> dict[int, float]:
    """Voisines d'adjacence dont le surplus du tick est strictement positif."""
    destinations: dict[int, float] = {}
    for edge in world.adjacency:
        a_id = edge["a"]
        b_id = edge["b"]
        if a_id not in world.cells or b_id not in world.cells:
            continue
        if a_id == source_id:
            voisin = b_id
        elif b_id == source_id:
            voisin = a_id
        else:
            continue
        surplus = surplus_par_cellule.get(voisin, 0.0)
        if surplus > 0.0:
            destinations[voisin] = surplus
    return destinations


def _apply_migration(world, penuries: dict[int, float]) -> None:
    """
    Maillon 6 — Migration de famine.

    Une cellule ne part que si la pénurie du tick (retour de _apply_consumption)
    est strictement positive. Les partants se répartissent entre les voisines
    dont le surplus alimentaire du tick est positif, sur un instantané pris
    avant tout mouvement. Sans aucune voisine terrestre, une cellule côtière
    peut rejoindre un autre port en surplus du bassin commun.
    Report de fraction via migration_remainder.

    Atomique : une personne ne traverse qu'une arête ; une cellule qui reçoit
    des arrivants n'en envoie pas le même tick. Aucun kilogramme ne bouge.
    """
    # Valider le bassin avant même de modifier un report de fraction.
    cotieres = {cid for cid, _, _ in _aretes_maritimes_du_monde(world)}
    reliees_par_terre = set()
    for edge in world.adjacency:
        if edge["a"] in world.cells and edge["b"] in world.cells:
            reliees_par_terre.update((edge["a"], edge["b"]))

    snapshot_pop = {cid: cell.population for cid, cell in world.cells.items()}
    snapshot_stock = {
        cid: lire_stock_marchandise(cell, _constantes.MARCHANDISE_NOURRITURE)
        for cid, cell in world.cells.items()
    }
    surplus_par_cellule = {
        cid: _surplus_nourriture_tick(snapshot_pop[cid], snapshot_stock[cid])
        for cid in world.cells
    }

    transfers: list[tuple[int, int, int]] = []

    for cid, cell in world.cells.items():
        if penuries.get(cid, 0.0) <= 0.0 or snapshot_pop[cid] <= 0:
            continue

        remainder = cell.migration_remainder if cell.migration_remainder >= 0.0 else 0.0
        brut = (
            snapshot_pop[cid] * _constantes.FRACTION_MIGRANTE_PAR_TICK + remainder
        )
        partants = int(brut)
        cell.migration_remainder = brut - partants

        if partants <= 0:
            continue

        destinations = _voisins_avec_surplus(world, cid, surplus_par_cellule)
        if cid not in reliees_par_terre and cid in cotieres:
            destinations = {
                voisin: surplus_par_cellule[voisin]
                for voisin in sorted(cotieres)
                if voisin != cid and surplus_par_cellule[voisin] > 0
            }
        if not destinations:
            continue

        repartition = _repartir_habitants_proportionnellement(partants, destinations)
        for dest_id, nb in repartition.items():
            if nb > 0:
                transfers.append((cid, dest_id, nb))

    receveuses = {dest for _, dest, _ in transfers}
    transfers = [(src, dest, nb) for src, dest, nb in transfers if src not in receveuses]

    sorties: dict[int, int] = defaultdict(int)
    entrees: dict[int, int] = defaultdict(int)
    for src, dest, nb in transfers:
        sorties[src] += nb
        entrees[dest] += nb

    for cid, cell in world.cells.items():
        pop_snapshot = snapshot_pop[cid]
        delta = entrees.get(cid, 0) - sorties.get(cid, 0)
        cell.population = pop_snapshot + delta


def tick(world, rng: random.Random, numero_tick: int | None = None) -> float:
    """
    Avance le monde d'un pas de temps.

    Ordre du tick :
        1. Fabrication (_apply_fabrication)  — pour chaque cellule
        2. Extraction  (_apply_extraction)   — pour chaque cellule (si carte)
        3. Production  (_apply_production)   — pour chaque cellule
        4. Commerce    (_apply_commerce)     — sur le monde entier (snapshot)
        5. Consommation (_apply_consumption) — pour chaque cellule
        6. Faim        (_update_hunger)      — pour chaque cellule
        7. Mortalité   (_apply_mortality)    — pour chaque cellule
        8. Natalité    (_apply_natalite)     — pour chaque cellule
        9. Migration   (_apply_migration)    — sur le monde entier (snapshot)

    rng : instance de random.Random initialisée par l'appelant —
          jamais d'aléa global non contrôlé.

    Retourne la quantité totale de nourriture transportée par le commerce
    pendant ce tick (kg).
    """
    total_transported = [0.0]
    for cell in world.cells.values():
        _apply_fabrication(cell)
    carte = world.carte if getattr(world, "carte", None) else None
    if carte is not None:
        for cell in world.cells.values():
            _apply_extraction(cell, carte)
    if carte is None:
        for cell in world.cells.values():
            _apply_production(cell, rng, carte)
    elif numero_tick is None:
        for cell in world.cells.values():
            _apply_production_saison_moyenne(cell, rng, carte)
    else:
        jour = _constantes.jour_de_tick(numero_tick)
        for cell in world.cells.values():
            _apply_production(cell, rng, carte, jour=jour)

    _apply_commerce(world, total_transported)

    penuries: dict[int, float] = {}
    for cell in world.cells.values():
        penurie_kg = _apply_consumption(cell)
        penuries[cell.cell_id] = penurie_kg
        _update_hunger(cell, penurie_kg)
        _apply_mortality(cell)
        _apply_natalite(cell, penurie_kg)

    _apply_migration(world, penuries)

    return total_transported[0]
