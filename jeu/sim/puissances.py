"""Lecture des puissances d'Europe et de Méditerranée en 1400, et le pays de chaque cellule.

La table `data/puissances-1400.json` déclare les puissances et leurs ancres. Une ancre est un point
sourcé : le siège d'une institution, le lieu d'une capitale ; elle ne décide le pays d'aucune cellule.
Le pays de chaque cellule est celui que la table des frontières décide (`sim/frontieres.py`)."""

import dataclasses
import json
import math
import pathlib

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
_DATE_ATTENDUE = "1400-01-01"

NATURES = frozenset({"royaume", "république", "Église", "ordre", "principauté", "empire", "sultanat", "khanat"})
RELIGIONS = frozenset({"catholique", "orthodoxe", "musulmane"})

class PuissanceInvalide(ValueError):
    """Levée quand la table des puissances est incomplète ou incohérente."""

@dataclasses.dataclass(frozen=True)
class Puissance(_NoBadSpatialField):
    id: int
    nom: str
    nature: str
    religion: str
    suzerain: int | None = None
    # L'ensemble dont la puissance est membre (« Saint-Empire ») : servi dans la fiche du pays, sans
    # effet sur le monde.
    ensemble: str | None = None


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


def _nombre(valeur, identifiant, champ: str, sorte="ancre"):
    if isinstance(valeur, bool) or not isinstance(valeur, (int, float)) or not math.isfinite(valeur):
        raise PuissanceInvalide(
            f"{sorte} {identifiant!r}, champ {champ} : nombre fini attendu"
        )
    return valeur


def _refuser_suzerains(puissances, ids) -> None:
    """Un suzerain déclaré est une puissance connue, et la chaîne des suzerains ne boucle pas."""
    par_id = {p.id: p for p in puissances}
    for puissance in puissances:
        courante, vues = puissance, set()
        while courante.suzerain is not None:
            if courante.suzerain not in ids:
                raise PuissanceInvalide(f"puissance {puissance.id}, champ suzerain : puissance inconnue")
            if courante.id in vues:
                raise PuissanceInvalide(f"puissance {puissance.id}, champ suzerain : cycle")
            vues.add(courante.id)
            courante = par_id[courante.suzerain]


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
        suzerain = None
        if "suzerain" in brute:
            suzerain = brute["suzerain"]
            if isinstance(suzerain, bool) or not isinstance(suzerain, int):
                raise PuissanceInvalide(f"puissance {identifiant}, champ suzerain : entier attendu")
            _texte(brute.get("source_suzerain"), "puissance", identifiant, "source_suzerain")
        ensemble = None
        if "ensemble" in brute:
            ensemble = _texte(brute["ensemble"], "puissance", identifiant, "ensemble")
            _texte(brute.get("source_ensemble"), "puissance", identifiant, "source_ensemble")
        elif "source_ensemble" in brute:
            raise PuissanceInvalide(f"puissance {identifiant}, champ ensemble : source sans ensemble")
        puissances.append(Puissance(identifiant, nom, nature, religion, suzerain, ensemble))
    _refuser_suzerains(puissances, ids_puissances)

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


def geometries_du_monde(world) -> dict:
    """Lit les polygones des cellules chargées, refuse une géométrie absente."""
    geometries = {}
    for cell_id in sorted(world.cells):
        geometrie = world.carte.get(cell_id, {}).get("geometry")
        if geometrie is None:
            raise PuissanceInvalide(f"cellule {cell_id}, champ geometry : géométrie absente")
        geometries[cell_id] = geometrie
    return geometries


def puissances_depuis_monde(world, table=None, frontieres=None) -> dict:
    """cell_id → puissance (ou `None`) de chaque cellule chargée, sans modifier le monde : son pays
    déclaré, le pays de son bourg si elle est partagée, aucun si elle est en lacune. Une cellule du
    monde que la table des frontières ne décide pas est refusée en la nommant."""
    from sim.frontieres import decisions_des_frontieres, frontieres_du_monde
    if table is None:
        table = charger_table()
    if frontieres is None:
        frontieres = frontieres_du_monde(world, table)
    vue = decisions_des_frontieres(world, table, frontieres)
    for cell_id in sorted(world.cells):
        if cell_id not in vue:
            raise PuissanceInvalide(f"cellule {cell_id}, champ cell_id : cellule sans pays, partage ni lacune")
    return vue


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
