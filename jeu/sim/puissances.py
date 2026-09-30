"""Lecture de la table documentée des puissances occidentales en 1400."""

import dataclasses
import json
import math
import pathlib

from sim.aggregation import (
    charger_positions,
    derive_appartenance,
    facteur_de_projection,
    positions_du_monde,
    projeter,
)
from sim.model import _NoBadSpatialField

_RACINE_DEPOT = pathlib.Path(__file__).parent.parent
_CHEMIN_TABLE = _RACINE_DEPOT / "data" / "puissances-1400.json"
_CLE_DATE = "date"
_CLE_PUISSANCES = "puissances"
_CLE_ANCRES = "ancres"
_CLE_ID = "id"
_CLE_NOM = "nom"
_CLE_NATURE = "nature"
_CLE_RELIGION = "religion"
_CLE_PUISSANCE = "puissance"
_CLE_LAT = "lat"
_CLE_LON = "lon"
_CLE_SOURCE = "source"
_CLE_PROJECTION = "projection"
_CLE_LATITUDE_MOYENNE = "mid_latitude"
_CLE_PORTEE = "portee"
_CLE_DEGRES_PROJETES = "degres_projetes"
_CLE_NIVEAU = "niveau"
_DATE_ATTENDUE = "1400-01-01"
_NIVEAU_FRONTIERE = 2

NATURES = frozenset({"royaume", "république", "Église", "ordre"})
RELIGIONS = frozenset({"catholique", "orthodoxe", "musulmane"})

class PuissanceInvalide(ValueError):
    """Levée quand la table des puissances est incomplète ou incohérente."""

@dataclasses.dataclass(frozen=True)
class Puissance(_NoBadSpatialField):
    id: int
    nom: str
    nature: str
    religion: str


@dataclasses.dataclass(frozen=True)
class Ancre(_NoBadSpatialField):
    id: int
    puissance: int
    nom: str
    lat: float
    lon: float
    source: str


@dataclasses.dataclass(frozen=True)
class TableDesPuissances(_NoBadSpatialField):
    date: str
    puissances: tuple
    ancres: tuple

def _refuser_id(valeur, sorte: str, vus: set) -> int:
    if isinstance(valeur, bool) or not isinstance(valeur, int):
        raise PuissanceInvalide(f"{sorte} {valeur!r}, champ id : entier attendu")
    if valeur in vus:
        raise PuissanceInvalide(f"{sorte} {valeur}, champ id : identifiant dupliqué")
    vus.add(valeur)
    return valeur


def _texte(valeur, sorte: str, identifiant, champ: str) -> str:
    if not isinstance(valeur, str) or not valeur.strip():
        raise PuissanceInvalide(
            f"{sorte} {identifiant!r}, champ {champ} : texte absent ou vide"
        )
    return valeur


def _nombre(valeur, identifiant, champ: str):
    if isinstance(valeur, bool) or not isinstance(valeur, (int, float)) or not math.isfinite(valeur):
        raise PuissanceInvalide(
            f"ancre {identifiant!r}, champ {champ} : nombre fini attendu"
        )
    return valeur


def charger_table(path=None) -> TableDesPuissances:
    """Lit la table, la valide entièrement et rend ses lignes triées."""
    chemin = pathlib.Path(path) if path is not None else _CHEMIN_TABLE
    document = json.loads(chemin.read_text(encoding="utf-8"))
    date = document.get(_CLE_DATE)
    if date != _DATE_ATTENDUE:
        raise PuissanceInvalide(f"champ date : {_DATE_ATTENDUE!r} attendu")
    brutes_puissances = document.get(_CLE_PUISSANCES)
    brutes_ancres = document.get(_CLE_ANCRES)
    if not isinstance(brutes_puissances, list) or not brutes_puissances:
        raise PuissanceInvalide("champ puissances : liste absente ou vide")
    if not isinstance(brutes_ancres, list) or not brutes_ancres:
        raise PuissanceInvalide("champ ancres : liste absente ou vide")

    puissances, ids_puissances = [], set()
    for brute in brutes_puissances:
        identifiant = _refuser_id(brute.get(_CLE_ID), "puissance", ids_puissances)
        nom = _texte(brute.get(_CLE_NOM), "puissance", identifiant, _CLE_NOM)
        nature = brute.get(_CLE_NATURE)
        religion = brute.get(_CLE_RELIGION)
        if nature not in NATURES:
            raise PuissanceInvalide(f"puissance {identifiant}, champ nature : valeur inconnue")
        if religion not in RELIGIONS:
            raise PuissanceInvalide(f"puissance {identifiant}, champ religion : valeur inconnue")
        puissances.append(Puissance(identifiant, nom, nature, religion))

    ancres, ids_ancres, puissances_visees = [], set(), set()
    for brute in brutes_ancres:
        identifiant = _refuser_id(brute.get(_CLE_ID), "ancre", ids_ancres)
        puissance = brute.get(_CLE_PUISSANCE)
        if isinstance(puissance, bool) or not isinstance(puissance, int):
            raise PuissanceInvalide(f"ancre {identifiant}, champ puissance : entier attendu")
        if puissance not in ids_puissances:
            raise PuissanceInvalide(f"ancre {identifiant}, champ puissance : puissance inconnue")
        nom = _texte(brute.get(_CLE_NOM), "ancre", identifiant, _CLE_NOM)
        source = _texte(brute.get(_CLE_SOURCE), "ancre", identifiant, _CLE_SOURCE)
        lat = _nombre(brute.get(_CLE_LAT), identifiant, _CLE_LAT)
        lon = _nombre(brute.get(_CLE_LON), identifiant, _CLE_LON)
        ancres.append(Ancre(identifiant, puissance, nom, lat, lon, source))
        puissances_visees.add(puissance)
    if ids_puissances - puissances_visees:
        identifiant = min(ids_puissances - puissances_visees)
        raise PuissanceInvalide(f"puissance {identifiant}, champ ancres : aucune ancre")
    return TableDesPuissances(
        date, tuple(sorted(puissances, key=lambda p: p.id)), tuple(sorted(ancres, key=lambda a: a.id))
    )


def charger_latitude_moyenne_puissances(path=None) -> float:
    """Lit le paramètre fini de la projection propre à la table."""
    chemin = pathlib.Path(path) if path is not None else _CHEMIN_TABLE
    document = json.loads(chemin.read_text(encoding="utf-8"))
    projection = document.get(_CLE_PROJECTION)
    if not isinstance(projection, dict):
        raise PuissanceInvalide("champ projection : bloc absent")
    latitude = projection.get(_CLE_LATITUDE_MOYENNE)
    if (
        isinstance(latitude, bool)
        or not isinstance(latitude, (int, float))
        or not math.isfinite(latitude)
    ):
        raise PuissanceInvalide(
            "champ projection.mid_latitude : nombre fini attendu"
        )
    return latitude


def charger_portee(path=None) -> float:
    """Lit la portée plausible et refuse toute valeur inexploitable."""
    chemin = pathlib.Path(path) if path is not None else _CHEMIN_TABLE
    document = json.loads(chemin.read_text(encoding="utf-8"))
    declaration = document.get(_CLE_PORTEE)
    if not isinstance(declaration, dict):
        raise PuissanceInvalide("champ portee : bloc absent")
    if declaration.get(_CLE_NIVEAU) != _NIVEAU_FRONTIERE:
        raise PuissanceInvalide("champ portee.niveau : niveau 2 attendu")
    portee = declaration.get(_CLE_DEGRES_PROJETES)
    if (
        isinstance(portee, bool)
        or not isinstance(portee, (int, float))
        or not math.isfinite(portee)
        or portee <= 0
    ):
        raise PuissanceInvalide(
            "champ portee.degres_projetes : nombre fini strictement positif attendu"
        )
    return portee


def puissance_par_cellule(
    positions, table, portee, latitude_moyenne
) -> dict:
    """Rend la puissance de l'ancre la plus proche, dans la portée donnée."""
    if (
        isinstance(portee, bool)
        or not isinstance(portee, (int, float))
        or math.isnan(portee)
        or portee <= 0
    ):
        raise PuissanceInvalide("portee : nombre strictement positif attendu")

    ancres_par_id = {ancre.id: ancre for ancre in table.ancres}
    appartenance = derive_appartenance(
        positions, table.ancres, latitude_moyenne
    )
    facteur = facteur_de_projection(latitude_moyenne)
    carre_portee = portee * portee
    vue = {}
    for cell_id in sorted(positions):
        ancre = ancres_par_id[appartenance[cell_id]]
        cellule_x, cellule_y = projeter(*positions[cell_id], facteur)
        ancre_x, ancre_y = projeter(ancre.lat, ancre.lon, facteur)
        ecart_x = cellule_x - ancre_x
        ecart_y = cellule_y - ancre_y
        carre_distance = ecart_x * ecart_x + ecart_y * ecart_y
        vue[cell_id] = ancre.puissance if carre_distance <= carre_portee else None
    return vue


def puissances_depuis_monde(
    world,
    positions=None,
    table=None,
    portee=None,
    latitude_moyenne=None,
) -> dict:
    """Adapte la vue pure aux cellules chargées, sans modifier le monde."""
    if positions is None:
        positions = charger_positions()
    if table is None:
        table = charger_table()
    if portee is None:
        portee = charger_portee()
    if latitude_moyenne is None:
        latitude_moyenne = charger_latitude_moyenne_puissances()
    retenues = positions_du_monde(world, positions)
    return puissance_par_cellule(retenues, table, portee, latitude_moyenne)


def puissance_de_cellule(cell_id, vue, table):
    """Rend la puissance d'une cellule couverte, sinon ``None``."""
    identifiant = vue.get(cell_id)
    if identifiant is None:
        return None
    return next(
        (puissance for puissance in table.puissances if puissance.id == identifiant),
        None,
    )


def cellules_non_couvertes(vue) -> tuple:
    """Rend, triés, les identifiants explicitement non couverts."""
    return tuple(sorted(cell_id for cell_id, puissance in vue.items() if puissance is None))
