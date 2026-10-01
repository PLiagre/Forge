"""Seigneuries de départ de 1400 et fiches recalculées sans effet sur le monde."""

from dataclasses import dataclass
import json
from pathlib import Path

from sim import constants as constantes
from sim.engine import population_soutenable_de
from sim.maisons import Maison, charger_maisons
from sim.model import _NoBadSpatialField
from sim.puissances import (
    RELIGIONS, Puissance, PuissanceInvalide, _nombre, _refuser_id, _texte,
    charger_table, puissances_depuis_monde,
)
from sim.villes import point_dans_geometrie

_CHEMIN = Path(__file__).parents[1] / "data" / "seigneuries-1400.json"
_DATE = "1400-01-01"
_PROJECTION = "EPSG:3035"


@dataclass(frozen=True)
class Siege(_NoBadSpatialField):
    nom: str
    lat: float
    lon: float
    x_m: float
    y_m: float


@dataclass(frozen=True)
class Seigneurie(_NoBadSpatialField):
    id: int
    nom: str
    religion: str
    maison: str
    suzerain: int
    siege: Siege
    source: str


@dataclass(frozen=True)
class Voisin(_NoBadSpatialField):
    cell_id: int
    puissance: Puissance | None
    habitants: int


@dataclass(frozen=True)
class Fiche(_NoBadSpatialField):
    seigneurie: Seigneurie
    cell_id: int
    habitants: int
    production_kg_par_tick: float
    suzerain: Puissance
    maison: Maison | None
    cellules_du_suzerain: int
    habitants_du_suzerain: int
    voisins: tuple[Voisin, ...]


class SeigneurieInconnue(LookupError):
    """Identifiant absent de la table ou qui n'est pas un entier."""


def charger_seigneuries(path=None, table=None) -> tuple[Seigneurie, ...]:
    """Valide toute la table avant de rendre les seigneuries triées par id."""
    document = json.loads(Path(path if path is not None else _CHEMIN).read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise PuissanceInvalide("seigneurie inconnue, champ seigneuries : document attendu")
    for champ, attendu in (("date", _DATE), ("projection", _PROJECTION)):
        if document.get(champ) != attendu:
            raise PuissanceInvalide(f"seigneurie inconnue, champ {champ} : {attendu!r} attendu")
    brutes = document.get("seigneuries")
    if not isinstance(brutes, list) or not brutes:
        raise PuissanceInvalide("seigneurie inconnue, champ seigneuries : liste absente ou vide")
    if table is None:
        table = charger_table()
    puissances = {p.id for p in table.puissances}
    seigneuries, ids, noms = [], set(), set()
    for brute in brutes:
        if not isinstance(brute, dict):
            raise PuissanceInvalide("seigneurie inconnue, champ id : ligne attendue")
        identifiant = _refuser_id(brute.get("id"), "seigneurie", ids)
        textes = {champ: _texte(brute.get(champ), "seigneurie", identifiant, champ)
                  for champ in ("nom", "maison", "source")}
        if textes["nom"] in noms:
            raise PuissanceInvalide(f"seigneurie {identifiant}, champ nom : nom dupliqué")
        noms.add(textes["nom"])
        religion, suzerain = brute.get("religion"), brute.get("suzerain")
        if not isinstance(religion, str) or religion not in RELIGIONS:
            raise PuissanceInvalide(f"seigneurie {identifiant}, champ religion : valeur inconnue")
        if isinstance(suzerain, bool) or not isinstance(suzerain, int) or suzerain not in puissances:
            raise PuissanceInvalide(f"seigneurie {identifiant}, champ suzerain : puissance inconnue")
        siege = brute.get("siege")
        if not isinstance(siege, dict):
            raise PuissanceInvalide(f"seigneurie {identifiant}, champ siege : bloc absent")
        nom_siege = _texte(siege.get("nom"), "seigneurie", identifiant, "siege.nom")
        coordonnees = {champ: _nombre(siege.get(champ), identifiant, f"siege.{champ}", "seigneurie")
                       for champ in ("lat", "lon", "x_m", "y_m")}
        seigneuries.append(Seigneurie(
            identifiant, textes["nom"], religion, textes["maison"], suzerain,
            Siege(nom_siege, **coordonnees), textes["source"],
        ))
    return tuple(sorted(seigneuries, key=lambda s: s.id))


def cellule_du_siege(seigneurie, carte) -> int:
    """Cherche dans les polygones ; sur une frontière, le plus petit cell_id gagne."""
    siege = seigneurie.siege
    for cell_id in sorted(carte):
        if point_dans_geometrie(siege.x_m, siege.y_m, carte[cell_id]["geometry"]):
            return cell_id
    raise PuissanceInvalide(f"seigneurie {seigneurie.id}, champ siege : hors carte")


def fiche_de_seigneurie(identifiant, monde, seigneuries=None, table=None, maisons=None) -> Fiche:
    """Refuse l'identifiant d'abord, puis dérive la fiche des données actuelles."""
    if isinstance(identifiant, bool) or not isinstance(identifiant, int):
        raise SeigneurieInconnue(f"seigneurie inconnue : {identifiant!r}")
    if seigneuries is None:
        seigneuries = charger_seigneuries(table=table)
    seigneurie = next((s for s in seigneuries if s.id == identifiant), None)
    if seigneurie is None:
        raise SeigneurieInconnue(f"seigneurie inconnue : {identifiant!r}")
    if table is None:
        table = charger_table()
    if maisons is None:
        maisons = charger_maisons()
    cell_id = cellule_du_siege(seigneurie, monde.carte)
    cellule = monde.cells[cell_id]
    puissances = {p.id: p for p in table.puissances}
    vue = puissances_depuis_monde(monde, table=table)
    cellules = tuple(cid for cid, puissance in vue.items() if puissance == seigneurie.suzerain)
    maison_id = maisons.par_puissance[seigneurie.suzerain]
    maison = next((m for m in maisons.maisons if m.id == maison_id), None)
    voisins = set()
    for arete in monde.adjacency:
        if arete["kind"] == "land-land" and cell_id in (arete["a"], arete["b"]):
            voisins.add(arete["b"] if arete["a"] == cell_id else arete["a"])
    return Fiche(
        seigneurie, cell_id, cellule.population,
        population_soutenable_de(cellule, monde.carte) * constantes.FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK,
        puissances[seigneurie.suzerain], maison, len(cellules),
        sum(monde.cells[cid].population for cid in cellules),
        tuple(Voisin(cid, puissances.get(vue[cid]), monde.cells[cid].population)
              for cid in sorted(voisins)),
    )
