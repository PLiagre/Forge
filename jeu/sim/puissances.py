"""Lecture de la table documentée des puissances occidentales en 1400."""

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
