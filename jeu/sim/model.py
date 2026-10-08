"""
Modèle de données du moteur de simulation.

cell_id est la seule clé spatiale. Province est
une agrégation dérivée — jamais un champ stocké sur une entité.
"""

from dataclasses import asdict, dataclass, field

import sim.foyers as _foyers
from sim.constants import MARCHANDISE_NOURRITURE


class _NoBadSpatialField:
    """
    Classe de base qui tient la clé spatiale unique : aucun champ province_id
    (ou équivalent) ne peut être déclaré sur une entité spatiale.

    Toute sous-classe dataclass qui déclare un tel champ lèvera une
    TypeError explicite à l'instanciation (via __post_init__).
    """

    _FORBIDDEN_PREFIX = "province"

    def __post_init__(self):
        for name in self.__dataclass_fields__:  # type: ignore[attr-defined]
            normalised = name.lower().replace("_", "")
            if normalised.startswith(self._FORBIDDEN_PREFIX):
                raise TypeError(
                    f"Le champ '{name}' est interdit. "
                    "Province est une agrégation dérivée, jamais un champ "
                    "stocké. Utilisez cell_id comme seule clé spatiale."
                )


def lire_stock_marchandise(cell: "Cell", marchandise: str) -> float:
    """
    Lit le stock d'une marchandise dans le panier de la cellule.

    Une marchandise absente du panier rend la sentinelle -1.0 (« non calculé »).
    Une marchandise présente à zéro se lit 0.0 (règle 8).
    """
    if marchandise not in cell.stocks:
        return -1.0
    return cell.stocks[marchandise]


def ecrire_stock_marchandise(cell: "Cell", marchandise: str, quantite_kg: float) -> None:
    """Écrit le stock d'une marchandise dans le panier de la cellule."""
    cell.stocks[marchandise] = quantite_kg


def copier_panier(entite: "Cell | EtatDeLieu") -> dict[str, float]:
    """Lit un panier par copie, pour une cellule ou l'un de ses lieux."""
    return dict(entite.stocks)


def contenus_des_paniers(entites, marchandise: str) -> list[float]:
    """Lit les poids d'une répartition ; une clé absente y pèse zéro."""
    return [entite.stocks.get(marchandise, 0) for entite in entites]


def remplacer_panier(entite: "Cell | EtatDeLieu", panier: dict[str, float]) -> None:
    """Pose le panier exact, y compris les absences de marchandises."""
    if entite.stocks != panier:
        entite.stocks = dict(panier)


def lire_habitants_par_metier(cell: "Cell") -> dict[str, int] | int:
    """Copie les métiers calculés ; -1 déclare leur absence de calcul."""
    if cell.habitants_par_metier is None:
        return -1
    return dict(cell.habitants_par_metier)


def ecrire_habitants_par_metier(cell: "Cell", metiers: dict[str, int]) -> None:
    """Valide les métiers, les écrit, puis aligne la population sur leur somme.

    `repartir` voit alors une somme égale et ne change rien.
    """
    _foyers.valider_metiers(metiers)
    cell.habitants_par_metier = dict(metiers)
    cell.population = sum(metiers.values())


def cellule_vers_dict(cell: "Cell") -> dict:
    """
    Sérialisation canonique d'une cellule pour World.to_dict().

    Le panier est copié ici : aucun autre module n'indexe stocks directement.
    """
    metiers = lire_habitants_par_metier(cell)
    foyers = -1
    if metiers != -1:
        foyers = {}
        for metier, personnes in sorted(metiers.items()):
            rangement = _foyers.ranger_en_foyers(personnes)
            foyers[metier] = {"personnes": personnes, "complets": rangement.complets,
                              "dernier": rangement.dernier}
    return {
        "cell_id": cell.cell_id,
        "area_km2": cell.area_km2,
        "population": cell.population,
        "foyers": foyers,
        "food_stock_kg": lire_stock_marchandise(cell, MARCHANDISE_NOURRITURE),
        "hunger_ticks": cell.hunger_ticks,
        "food_deficit_kg": cell.food_deficit_kg,
        "mortality_remainder": cell.mortality_remainder,
        "natalite_remainder": cell.natalite_remainder,
        "migration_remainder": cell.migration_remainder,
        "stocks": dict(cell.stocks),
        "lieux": [
            {**asdict(lieu), "maitre": lieu.maitre}
            for lieu in sorted(cell.lieux, key=lambda lieu: lieu.rang)
        ],
    }


@dataclass
class EtatDeLieu(_NoBadSpatialField):
    """Habitants, panier, dette, faim, reports locaux et maître déclaré d'un rang."""

    rang: int
    population: int
    stocks: dict[str, float]
    dette_alimentaire_kg: float = 0.0
    duree_faim_ticks: int = 0
    mortality_remainder: float = 0.0
    natalite_remainder: float = 0.0
    maitre: str | None = None


def ecrire_maitre(etatdelieu: EtatDeLieu, maitre: str | None) -> None:
    """Pose le maître déclaré, sans inventer de maison en cas d'absence."""
    etatdelieu.maitre = maitre


def creer_etat_de_lieu(rang: int, population: int, stocks: dict[str, float], *,
                       dette_alimentaire_kg: float = 0.0,
                       duree_faim_ticks: int = 0,
                       mortality_remainder: float = 0.0,
                       natalite_remainder: float = 0.0,
                       maitre: str | None = None) -> EtatDeLieu:
    """Crée l'état d'un rang avec son propre panier, sans clé recopiée."""
    etatdelieu = EtatDeLieu(rang=rang, population=population, stocks=dict(stocks),
                      dette_alimentaire_kg=dette_alimentaire_kg,
                      duree_faim_ticks=duree_faim_ticks,
                      mortality_remainder=mortality_remainder,
                      natalite_remainder=natalite_remainder)
    ecrire_maitre(etatdelieu, maitre)
    return etatdelieu


@dataclass
class Cell(_NoBadSpatialField):
    """
    Unité géographique de base du monde simulé.

    `natalite_remainder` reporte la fraction de naissance non encore
    appliquée. Sa sentinelle -1.0 signifie « non calculé » ; un monde amorcé
    l'initialise à 0.0.
    """

    cell_id: int
    area_km2: float
    population: int
    stocks: dict[str, float] = field(default_factory=dict)
    hunger_ticks: int = field(default=-1)
    food_deficit_kg: float = field(default=-1.0)
    mortality_remainder: float = field(default=-1.0)
    natalite_remainder: float = field(default=-1.0)
    migration_remainder: float = field(default=-1.0)
    lieux: list = field(default_factory=list)
    habitants_par_metier: dict[str, int] | None = None

    def __init__(
        self,
        cell_id: int,
        area_km2: float,
        population: int,
        stocks: dict[str, float] | None = None,
        hunger_ticks: int = -1,
        food_deficit_kg: float = -1.0,
        mortality_remainder: float = -1.0,
        natalite_remainder: float = -1.0,
        migration_remainder: float = -1.0,
        food_stock_kg: float | None = None,
        lieux: list | None = None,
        habitants_par_metier: dict[str, int] | None = None,
    ):
        if habitants_par_metier is not None:
            _foyers.valider_metiers(habitants_par_metier)
            # Valide la population avant toute écriture, sans corriger la déclaration.
            _foyers.repartir(habitants_par_metier, population)
            if sum(habitants_par_metier.values()) != population:
                raise _foyers.FoyersInvalides("La somme des métiers diffère de la population")
        self.habitants_par_metier = (
            dict(habitants_par_metier) if habitants_par_metier is not None else None
        )
        self.cell_id = cell_id
        self.area_km2 = area_km2
        self.population = population
        self.stocks = dict(stocks) if stocks is not None else {}
        self.hunger_ticks = hunger_ticks
        self.food_deficit_kg = food_deficit_kg
        self.mortality_remainder = mortality_remainder
        self.natalite_remainder = natalite_remainder
        self.migration_remainder = migration_remainder
        self.lieux = list(lieux) if lieux is not None else []
        if food_stock_kg is not None and food_stock_kg >= 0:
            self.stocks = {MARCHANDISE_NOURRITURE: food_stock_kg}
        _NoBadSpatialField.__post_init__(self)

    def __setattr__(self, nom, valeur):
        if nom == "population":
            metiers = self.__dict__.get("habitants_par_metier")
            if metiers is not None:
                repartition = _foyers.repartir(metiers, valeur)
                object.__setattr__(self, "habitants_par_metier", repartition)
        object.__setattr__(self, nom, valeur)

    @property
    def food_stock_kg(self) -> float:
        """Compatibilité tests : délègue à l'accès nommé de lecture."""
        return lire_stock_marchandise(self, MARCHANDISE_NOURRITURE)

    @food_stock_kg.setter
    def food_stock_kg(self, valeur: float) -> None:
        """Compatibilité tests : délègue à l'accès nommé d'écriture."""
        if valeur < 0:
            self.stocks.pop(MARCHANDISE_NOURRITURE, None)
        else:
            ecrire_stock_marchandise(self, MARCHANDISE_NOURRITURE, valeur)
