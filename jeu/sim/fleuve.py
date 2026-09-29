"""Vue dérivée des cellules traversées par le cours documenté du Nil."""

import dataclasses
import json
import math
import pathlib

from sim.aggregation import (
    charger_positions,
    derive_appartenance,
    positions_du_monde,
)
from sim.model import _NoBadSpatialField


_RACINE_DEPOT = pathlib.Path(__file__).parent.parent
_CHEMIN_COURS = _RACINE_DEPOT / "data" / "nil-cours-1400.json"

_CLE_COURS_DE_1400 = "cours_de_1400"
_CLE_HORS_CARTE = "hors_carte"
_CLE_PROJECTION = "projection"
_CLE_LATITUDE_MOYENNE = "mid_latitude"
_CLE_POINTS = "points"
_CLE_IDENTIFIANT = "id"
_CLE_NOM = "nom"
_CLE_LATITUDE = "lat"
_CLE_LONGITUDE = "lon"
_CLE_SOURCE = "source"


class CoursDuNilInvalide(ValueError):
    """Levée quand la table ne permet pas de dériver honnêtement le cours."""


@dataclasses.dataclass(frozen=True)
class PointDuCours(_NoBadSpatialField):
    """Point géographique documenté du cours actuel du Nil."""

    id: int
    nom: str
    lat: float
    lon: float
    source: str


@dataclasses.dataclass(frozen=True)
class CelluleTraversee(_NoBadSpatialField):
    """Cellule à laquelle appartiennent un ou plusieurs points du cours."""

    cell_id: int
    point_ids: tuple


@dataclasses.dataclass(frozen=True)
class _CentroideCellule(_NoBadSpatialField):
    id: int
    lat: float
    lon: float


def _lire_document(path=None) -> dict:
    chemin = pathlib.Path(path) if path is not None else _CHEMIN_COURS
    return json.loads(chemin.read_text(encoding="utf-8"))


def _refuser_texte_vide(valeur, point_id, champ: str) -> str:
    if not isinstance(valeur, str) or not valeur.strip():
        raise CoursDuNilInvalide(
            f"point {point_id!r}, champ {champ} : texte absent ou vide"
        )
    return valeur


def _refuser_nombre_invalide(valeur, point_id, champ: str):
    if (
        isinstance(valeur, bool)
        or not isinstance(valeur, (int, float))
        or not math.isfinite(valeur)
    ):
        raise CoursDuNilInvalide(
            f"point {point_id!r}, champ {champ} : nombre fini attendu"
        )
    return valeur


def charger_points(path=None) -> list:
    """Lit les points du cours après validation des déclarations et lignes."""
    document = _lire_document(path)
    for champ in (_CLE_COURS_DE_1400, _CLE_HORS_CARTE):
        declaration = document.get(champ)
        if not isinstance(declaration, str) or not declaration.strip():
            raise CoursDuNilInvalide(
                f"champ {champ} : déclaration absente ou vide"
            )

    bruts = document.get(_CLE_POINTS)
    if not isinstance(bruts, list) or not bruts:
        raise CoursDuNilInvalide(
            f"champ {_CLE_POINTS} : la table de points est vide"
        )

    vus = set()
    points = []
    for brut in bruts:
        point_id = brut.get(_CLE_IDENTIFIANT)
        if isinstance(point_id, bool) or not isinstance(point_id, int):
            raise CoursDuNilInvalide(
                f"point {point_id!r}, champ {_CLE_IDENTIFIANT} : entier attendu"
            )
        if point_id in vus:
            raise CoursDuNilInvalide(
                f"point {point_id}, champ {_CLE_IDENTIFIANT} : identifiant dupliqué"
            )
        vus.add(point_id)
        nom = _refuser_texte_vide(brut.get(_CLE_NOM), point_id, _CLE_NOM)
        source = _refuser_texte_vide(
            brut.get(_CLE_SOURCE), point_id, _CLE_SOURCE
        )
        latitude = _refuser_nombre_invalide(
            brut.get(_CLE_LATITUDE), point_id, _CLE_LATITUDE
        )
        longitude = _refuser_nombre_invalide(
            brut.get(_CLE_LONGITUDE), point_id, _CLE_LONGITUDE
        )
        points.append(PointDuCours(point_id, nom, latitude, longitude, source))
    return points


def charger_latitude_moyenne_fleuve(path=None) -> float:
    """Lit le paramètre de projection porté par la table du cours."""
    return _lire_document(path)[_CLE_PROJECTION][_CLE_LATITUDE_MOYENNE]


def cellules_traversees(points, positions, latitude_moyenne) -> tuple:
    """Attribue chaque point à son unique centroïde de cellule le plus proche."""
    if not points:
        raise CoursDuNilInvalide(
            "Aucun point du cours fourni : la vue refuse de deviner."
        )
    if not positions:
        raise CoursDuNilInvalide(
            "Aucune position de cellule fournie : la vue refuse de deviner."
        )
    centroides = [
        _CentroideCellule(cell_id, latitude, longitude)
        for cell_id, (latitude, longitude) in positions.items()
    ]
    appartenance = derive_appartenance(
        {point.id: (point.lat, point.lon) for point in points},
        centroides,
        latitude_moyenne,
    )
    points_par_cellule = {}
    for point_id, cell_id in appartenance.items():
        points_par_cellule.setdefault(cell_id, []).append(point_id)
    return tuple(
        CelluleTraversee(cell_id, tuple(sorted(points_par_cellule[cell_id])))
        for cell_id in sorted(points_par_cellule)
    )


def cours_depuis_monde(
    world, positions=None, points=None, latitude_moyenne=None
) -> tuple:
    """Restreint les positions au monde chargé et en dérive le cours du Nil."""
    if positions is None:
        positions = charger_positions()
    if points is None:
        points = charger_points()
    if latitude_moyenne is None:
        latitude_moyenne = charger_latitude_moyenne_fleuve()
    retenues = positions_du_monde(world, positions)
    return cellules_traversees(points, retenues, latitude_moyenne)
