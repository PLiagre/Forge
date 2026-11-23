"""Maisons tenantes de 1400 : la maison de chaque cellule est celle de son pays."""
import dataclasses
import json
import pathlib

from sim.model import _NoBadSpatialField
from sim.puissances import _CHEMIN_TABLE, _refuser_id, _texte, PuissanceInvalide, charger_table, puissances_depuis_monde

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
    par_puissance = {}
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
    # Une ancre est un point de sa puissance : elle ne désigne pas de maison.
    for ancre in table.ancres:
        if "maison" in brutes_ancres[ancre.id]:
            raise PuissanceInvalide(f"ancre {ancre.id}, champ maison : une ancre ne désigne pas de maison")
    tenantes = set(par_puissance.values())
    for identifiant in sorted(ids - tenantes):
        raise PuissanceInvalide(f"maison {identifiant}, champ maison : ne tient rien")
    return TableDesMaisons(tuple(sorted(maisons, key=lambda m: m.id)), par_puissance)


def maisons_depuis_monde(world, table=None, maisons=None, frontieres=None) -> dict:
    """cell_id → maison tenante de chaque cellule chargée, sans modifier le monde : la maison de son
    pays (`par_puissance`), sans maison pour une république, une Église, un ordre ou une lacune."""
    if table is None:
        table = charger_table()
    if maisons is None:
        maisons = charger_maisons()
    vue = puissances_depuis_monde(world, table=table, frontieres=frontieres)
    return {cell_id: None if pays is None else maisons.par_puissance[pays] for cell_id, pays in vue.items()}


def maison_de_cellule(cell_id, vue, maisons):
    """Rend la maison de la cellule, ou l'absence déclarée de maison."""
    identifiant = vue.get(cell_id)
    if identifiant is None:
        return None
    return next((maison for maison in maisons.maisons if maison.id == identifiant), None)
