"""Découpage de la surface cellulaire en lieux, recalculé à la demande."""

import dataclasses
import math

import sim.constants as _constantes
from sim.model import _NoBadSpatialField


class LieuxInvalides(ValueError):
    """Une surface ou la règle de découpage empêche de former les lieux."""


@dataclasses.dataclass(frozen=True)
class Lieu(_NoBadSpatialField):
    cell_id: int
    rang: int
    surface_km2: float

    @property
    def est_bourg(self) -> bool:
        """Le premier lieu est le bourg de la cellule."""
        return self.rang == 0


def lieux_de_cellule(cell_id, surface_km2) -> tuple:
    """Découpe une surface sans perdre de kilomètres carrés."""
    surface_par_lieu = _constantes.SURFACE_KM2_PAR_LIEU
    if (
        isinstance(surface_par_lieu, bool)
        or not isinstance(surface_par_lieu, (int, float))
        or not math.isfinite(surface_par_lieu)
        or surface_par_lieu < 1
    ):
        raise LieuxInvalides(f"cell_id {cell_id} : SURFACE_KM2_PAR_LIEU invalide")
    if (
        isinstance(surface_km2, bool)
        or not isinstance(surface_km2, (int, float))
        or not math.isfinite(surface_km2)
        or surface_km2 <= 0
    ):
        raise LieuxInvalides(f"cell_id {cell_id} : surface_km2 absente ou invalide")

    nombre = max(1, math.floor(surface_km2 / surface_par_lieu))
    surface_autres = math.floor(surface_km2 / nombre)
    surface_bourg = surface_km2 - (nombre - 1) * surface_autres
    return (Lieu(cell_id, 0, surface_bourg),) + tuple(
        Lieu(cell_id, rang, surface_autres) for rang in range(1, nombre)
    )


def lieux_par_cellule(surfaces) -> dict:
    """Rend les lieux de chaque cellule, dans l'ordre de leur clé."""
    return {cell_id: lieux_de_cellule(cell_id, surfaces[cell_id]) for cell_id in sorted(surfaces)}


def lieux_depuis_monde(world) -> dict:
    """Lit seulement la surface des cellules du monde."""
    return lieux_par_cellule({
        cell_id: getattr(cellule, "area_km2", None)
        for cell_id, cellule in world.cells.items()
    })
