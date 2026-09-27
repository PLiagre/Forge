"""
Modèle de données du moteur de simulation.

cell_id est la seule clé spatiale. Province est
une agrégation dérivée — jamais un champ stocké sur une entité.
"""

from dataclasses import dataclass, field

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


def cellule_vers_dict(cell: "Cell") -> dict:
    """
    Sérialisation canonique d'une cellule pour World.to_dict().

    Le panier est copié ici : aucun autre module n'indexe stocks directement.
    """
    return {
        "cell_id": cell.cell_id,
        "area_km2": cell.area_km2,
        "population": cell.population,
        "food_stock_kg": lire_stock_marchandise(cell, MARCHANDISE_NOURRITURE),
        "hunger_ticks": cell.hunger_ticks,
        "food_deficit_kg": cell.food_deficit_kg,
        "mortality_remainder": cell.mortality_remainder,
        "natalite_remainder": cell.natalite_remainder,
        "migration_remainder": cell.migration_remainder,
        "stocks": dict(cell.stocks),
    }


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
    ):
        self.cell_id = cell_id
        self.area_km2 = area_km2
        self.population = population
        self.stocks = dict(stocks) if stocks is not None else {}
        self.hunger_ticks = hunger_ticks
        self.food_deficit_kg = food_deficit_kg
        self.mortality_remainder = mortality_remainder
        self.natalite_remainder = natalite_remainder
        self.migration_remainder = migration_remainder
        if food_stock_kg is not None and food_stock_kg >= 0:
            self.stocks = {MARCHANDISE_NOURRITURE: food_stock_kg}
        _NoBadSpatialField.__post_init__(self)

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
