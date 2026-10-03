"""Maisons tenantes de 1400 : une vue pure des ancres des puissances."""
import dataclasses
import json
import pathlib

from sim.aggregation import charger_positions, positions_du_monde
from sim.model import _NoBadSpatialField
from sim.puissances import (
    _CHEMIN_TABLE, _refuser_id, _texte, PuissanceInvalide, charger_table,
    charger_portee, charger_latitude_moyenne_puissances, ancre_par_cellule,
    geometries_du_monde,
)

_NATURES_SANS_MAISON = frozenset({"république", "Église", "ordre"})


@dataclasses.dataclass(frozen=True)
class Maison(_NoBadSpatialField):
    id: int
    nom: str
    source: str


@dataclasses.dataclass(frozen=True)
class TableDesMaisons(_NoBadSpatialField):
    maisons: tuple[Maison, ...]
    par_puissance: dict[int, int | None]
    par_ancre: dict[int, int | None]


def _maison_connue(valeur, sorte, identifiant, ids):
    if isinstance(valeur, bool) or not isinstance(valeur, int) or valeur not in ids:
        raise PuissanceInvalide(f"{sorte} {identifiant}, champ maison : maison inconnue")
    return valeur


def charger_maisons(path=None) -> TableDesMaisons:
    """Valide les maisons et leurs tenures, sans changer le lecteur des puissances."""
    chemin = pathlib.Path(path) if path is not None else _CHEMIN_TABLE
    document = json.loads(chemin.read_text(encoding="utf-8"))
    brutes = document.get("maisons")
    if not isinstance(brutes, list) or not brutes:
        raise PuissanceInvalide("champ maisons : liste absente ou vide")
    maisons, ids = [], set()
    for brute in brutes:
        if not isinstance(brute, dict):
            raise PuissanceInvalide("maison inconnue, champ id : ligne attendue")
        identifiant = _refuser_id(brute.get("id"), "maison", ids)
        nom = _texte(brute.get("nom"), "maison", identifiant, "nom")
        source = _texte(brute.get("source"), "maison", identifiant, "source")
        maisons.append(Maison(identifiant, nom, source))

    table = charger_table(chemin)
    brutes_puissances = {p["id"]: p for p in document["puissances"]}
    brutes_ancres = {a["id"]: a for a in document["ancres"]}
    par_puissance, par_ancre = {}, {}
    for puissance in table.puissances:
        brute = brutes_puissances[puissance.id]
        if puissance.nature in _NATURES_SANS_MAISON:
            if "maison" in brute:
                raise PuissanceInvalide(
                    f"puissance {puissance.id}, champ maison : nature sans maison"
                )
            par_puissance[puissance.id] = None
        else:
            par_puissance[puissance.id] = _maison_connue(
                brute.get("maison"), "puissance", puissance.id, ids
            )
    for ancre in table.ancres:
        brute = brutes_ancres[ancre.id]
        maison = par_puissance[ancre.puissance]
        if "maison" in brute:
            declaree = _maison_connue(brute["maison"], "ancre", ancre.id, ids)
            if declaree == maison:
                raise PuissanceInvalide(
                    f"ancre {ancre.id}, champ maison : déjà celle de sa puissance"
                )
            maison = declaree
        par_ancre[ancre.id] = maison
    tenantes = set(par_puissance.values()) | set(par_ancre.values())
    for identifiant in sorted(ids - tenantes):
        raise PuissanceInvalide(f"maison {identifiant}, champ maison : ne tient rien")
    return TableDesMaisons(
        tuple(sorted(maisons, key=lambda m: m.id)), par_puissance, par_ancre
    )


def maison_par_cellule(
    positions, table, maisons, portee, latitude_moyenne, geometries=None,
) -> dict:
    """Rend la maison de la même ancre que la puissance, dans sa portée."""
    for ancre in table.ancres:
        if ancre.id not in maisons.par_ancre:
            raise PuissanceInvalide(f"ancre {ancre.id}, champ maison : ancre absente")
    appartenance = ancre_par_cellule(positions, table, portee, latitude_moyenne, geometries)
    return {cell_id: maisons.par_ancre[ancre] if ancre is not None else None
            for cell_id, ancre in appartenance.items()}


def maisons_depuis_monde(
    world, positions=None, table=None, maisons=None, portee=None, latitude_moyenne=None,
) -> dict:
    """Recalcule les tenantes des cellules chargées, sans modifier le monde."""
    if positions is None:
        positions = charger_positions()
    if table is None:
        table = charger_table()
    if maisons is None:
        maisons = charger_maisons()
    if portee is None:
        portee = charger_portee()
    if latitude_moyenne is None:
        latitude_moyenne = charger_latitude_moyenne_puissances()
    retenues = positions_du_monde(world, positions)
    return maison_par_cellule(
        retenues, table, maisons, portee, latitude_moyenne, geometries_du_monde(world)
    )


def maison_de_cellule(cell_id, vue, maisons):
    """Rend la maison de la cellule, ou l'absence déclarée de maison."""
    identifiant = vue.get(cell_id)
    if identifiant is None:
        return None
    return next((maison for maison in maisons.maisons if maison.id == identifiant), None)
