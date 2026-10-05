"""Capitales de 1400 et maisons de l'IA : une vue pure, hors du tick."""

from dataclasses import dataclass
import json
from pathlib import Path

from sim.aggregation import charger_positions, positions_du_monde
from sim.maisons import charger_maisons
from sim.model import _NoBadSpatialField
from sim.projection import projeter_epsg3035
from sim.puissances import PuissanceInvalide, _nombre, _texte, geometries_du_monde
from sim.seigneuries import charger_seigneuries, cellule_du_siege
from sim.villes import point_dans_geometrie

_CHEMIN = Path(__file__).parents[1] / "data" / "capitales-1400.json"
_DATE = "1400-01-01"


@dataclass(frozen=True)
class Capitale(_NoBadSpatialField):
    maison: int
    nom: str
    lat: float
    lon: float
    source: str
    hors_carte: str | None = None


@dataclass(frozen=True)
class MaisonDeLIA(_NoBadSpatialField):
    sorte: str
    id: int
    nom: str
    capitale: str
    cell_id: int | None
    hors_carte: str | None
    source: str


def charger_capitales(path=None, maisons=None) -> tuple[Capitale, ...]:
    """Valide une capitale par maison connue, sans stocker sa cellule."""
    document = json.loads(Path(path if path is not None else _CHEMIN).read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise PuissanceInvalide("maison inconnue, champ capitales : document attendu")
    if document.get("date") != _DATE:
        raise PuissanceInvalide(f"maison inconnue, champ date : {_DATE!r} attendu")
    brutes = document.get("capitales")
    if not isinstance(brutes, list) or not brutes:
        raise PuissanceInvalide("maison inconnue, champ capitales : liste absente ou vide")
    if maisons is None:
        maisons = charger_maisons()
    connues = {m.id for m in maisons.maisons}
    capitales, vues = [], set()
    for brute in brutes:
        if not isinstance(brute, dict):
            raise PuissanceInvalide("maison inconnue, champ maison : ligne attendue")
        identifiant = brute.get("maison")
        if isinstance(identifiant, bool) or not isinstance(identifiant, int) or identifiant not in connues:
            raise PuissanceInvalide(f"maison {identifiant!r}, champ maison : entier connu attendu")
        if identifiant in vues:
            raise PuissanceInvalide(f"maison {identifiant}, champ maison : capitale dupliquée")
        vues.add(identifiant)
        textes = {champ: _texte(brute.get(champ), "maison", identifiant, champ)
                  for champ in ("nom", "source")}
        coordonnees = {champ: _nombre(brute.get(champ), identifiant, champ, "maison")
                       for champ in ("lat", "lon")}
        raison = (_texte(brute["hors_carte"], "maison", identifiant, "hors_carte")
                  if "hors_carte" in brute else None)
        capitales.append(Capitale(identifiant, **textes, **coordonnees, hors_carte=raison))
    for identifiant in sorted(connues - vues):
        raise PuissanceInvalide(f"maison {identifiant}, champ maison : capitale absente")
    return tuple(sorted(capitales, key=lambda c: c.maison))


def cellule_de_capitale(capitale, carte) -> int | None:
    """Place par polygone et refuse une déclaration hors carte contradictoire."""
    point = projeter_epsg3035(capitale.lat, capitale.lon)
    for cell_id in sorted(carte):
        geometrie = carte[cell_id].get("geometry")
        if geometrie is None:
            raise PuissanceInvalide(f"cellule {cell_id}, champ geometry : géométrie absente")
        if point_dans_geometrie(*point, geometrie):
            if capitale.hors_carte is not None:
                raise PuissanceInvalide(
                    f"maison {capitale.maison}, champ hors_carte : point dans la cellule {cell_id}"
                )
            return cell_id
    if capitale.hors_carte is None:
        raise PuissanceInvalide(f"maison {capitale.maison}, champ hors_carte : hors carte sans raison")
    return None


def maisons_de_l_ia(
    monde, capitales=None, maisons=None, seigneuries=None, positions=None,
) -> tuple[MaisonDeLIA, ...]:
    """Recalcule les grandes maisons, puis les départs que le joueur n'a pas pris."""
    if positions is None:
        positions = charger_positions()
    positions_du_monde(monde, positions)
    carte = {cid: {"geometry": geo} for cid, geo in geometries_du_monde(monde).items()}
    if maisons is None:
        maisons = charger_maisons()
    if capitales is None:
        capitales = charger_capitales(maisons=maisons)
    if seigneuries is None:
        seigneuries = charger_seigneuries()
    noms = {m.id: m.nom for m in maisons.maisons}
    grandes = tuple(MaisonDeLIA(
        "grande maison", c.maison, noms[c.maison], c.nom,
        cellule_de_capitale(c, carte), c.hors_carte, c.source,
    ) for c in sorted(capitales, key=lambda c: c.maison))
    departs = tuple(MaisonDeLIA(
        "seigneurie", s.id, s.maison, s.siege.nom,
        cellule_du_siege(s, carte), None, s.source,
    ) for s in sorted(seigneuries, key=lambda s: s.id) if s.id != monde.maison_du_joueur)
    return grandes + departs
