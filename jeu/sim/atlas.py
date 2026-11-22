"""Les noms de l'atlas : fleuves, mers, régions et sièges, vue dérivée et pure.

La provenance est `data/atlas-1400.json`. Un fleuve y est une ligne de points en degrés de sa
source à sa mer, une mer ou une région un nom et un point, chaque ligne avec sa source publique.
Le Nil n'y a pas de ligne : son tracé reste celui de `nil-cours-1400.json`, que l'atlas ne
fait qu'ordonner en deux bras. Le nom d'un siège se dérive du registre des maisons : seuls les
sièges placés sur la carte dont le nom n'est pas celui d'une ville de la table des villes sont
servis, avec leur position.

Le document ne contient aucun tick, stock ou population : il se calcule une fois pour la partie.
Le tick ne lit pas ce module.
"""

import dataclasses
import json
import math
from pathlib import Path

import sim.constants as _constantes
from sim.fleuve import _CHEMIN_COURS, charger_points
from sim.model import _NoBadSpatialField
from sim.places import sieges_des_maisons
from sim.projection import projeter_epsg3035
from sim.registre_maisons import charger_registre_maisons
from sim.villes import LATITUDE_MAX, LONGITUDE_MAX, charger_villes, point_dans_geometrie

_CHEMIN = Path(__file__).parents[1] / "data" / "atlas-1400.json"
_DATE = "1400-01-01"
_PROJECTION = "EPSG:3035"
_REFERENCE = "EPSG:4326"

_CLE_FLEUVES = "fleuves"
_CLE_MERS = "mers"
_CLE_REGIONS = "regions"
_CLE_POINTS = "points"
_CLE_BRAS = "bras"
_CLE_TRACE_DANS = "trace_dans"
_CLE_DECLARATION = "declaration"
_CLE_NOM = "nom"
_CLE_LATITUDE = "lat"
_CLE_LONGITUDE = "lon"
_CLE_SOURCE = "source"

_FLEUVE = "fleuve"
_MER = "mer"
_REGION = "région"


class AtlasInvalide(ValueError):
    """Levée quand l'atlas ne se charge pas, ou qu'un nom n'a pas sa place sur la carte."""


@dataclasses.dataclass(frozen=True)
class Point(_NoBadSpatialField):
    """Un point nommé, en degrés, avec la source qui le place."""

    nom: str
    lat: float
    lon: float
    source: str


@dataclasses.dataclass(frozen=True)
class Fleuve(_NoBadSpatialField):
    """Un fleuve : une ligne de points de la source à la mer, deux pour le delta du Nil."""

    nom: str
    lignes: tuple


@dataclasses.dataclass(frozen=True)
class Atlas(_NoBadSpatialField):
    fleuves: tuple
    mers: tuple
    regions: tuple


def _texte(valeur, genre, nom, champ) -> str:
    if not isinstance(valeur, str) or not valeur.strip():
        raise AtlasInvalide(f"{genre} {nom!r}, champ {champ} : texte absent ou vide")
    return valeur


def _nombre(valeur, genre, nom, champ, borne):
    if isinstance(valeur, bool) or not isinstance(valeur, (int, float)) or not math.isfinite(valeur):
        raise AtlasInvalide(f"{genre} {nom!r}, champ {champ} : nombre fini attendu")
    if not -borne <= valeur <= borne:
        raise AtlasInvalide(f"{genre} {nom!r}, champ {champ} : hors bornes")
    return valeur


def _liste(brut, champ) -> list:
    valeur = brut.get(champ)
    if not isinstance(valeur, list) or not valeur:
        raise AtlasInvalide(f"champ {champ} : liste absente ou vide")
    return valeur


def _point(brut, genre, rang) -> Point:
    if not isinstance(brut, dict):
        raise AtlasInvalide(f"{genre} n°{rang} : ligne attendue")
    nom = _texte(brut.get(_CLE_NOM), genre, f"n°{rang}", _CLE_NOM)
    return Point(
        nom,
        _nombre(brut.get(_CLE_LATITUDE), genre, nom, _CLE_LATITUDE, LATITUDE_MAX),
        _nombre(brut.get(_CLE_LONGITUDE), genre, nom, _CLE_LONGITUDE, LONGITUDE_MAX),
        _texte(brut.get(_CLE_SOURCE), genre, nom, _CLE_SOURCE),
    )


def _ligne_du_fleuve(brut, nom) -> tuple:
    points = brut.get(_CLE_POINTS)
    if not isinstance(points, list) or len(points) < _constantes.POINTS_MIN_FLEUVE:
        raise AtlasInvalide(
            f"{_FLEUVE} {nom!r}, champ {_CLE_POINTS} : au moins {_constantes.POINTS_MIN_FLEUVE} points attendus")
    return tuple(_point(p, f"point de {nom}", rang) for rang, p in enumerate(points, start=1))


def _lignes_du_nil(brut, nom, chemin_du_nil) -> tuple:
    """Les deux bras du Nil, repris point pour point du fichier qui garde son tracé."""
    if brut.get(_CLE_TRACE_DANS) != _CHEMIN_COURS.name:
        raise AtlasInvalide(f"{_FLEUVE} {nom!r}, champ {_CLE_TRACE_DANS} : {_CHEMIN_COURS.name!r} attendu")
    _texte(brut.get(_CLE_DECLARATION), _FLEUVE, nom, _CLE_DECLARATION)
    bras = brut.get(_CLE_BRAS)
    if not isinstance(bras, list) or not bras:
        raise AtlasInvalide(f"{_FLEUVE} {nom!r}, champ {_CLE_BRAS} : liste absente ou vide")
    cours = {p.id: Point(p.nom, p.lat, p.lon, p.source) for p in charger_points(chemin_du_nil)}
    lignes = []
    for rang, un_bras in enumerate(bras, start=1):
        identifiants = un_bras.get(_CLE_POINTS) if isinstance(un_bras, dict) else None
        if (not isinstance(identifiants, list) or len(identifiants) < _constantes.POINTS_MIN_FLEUVE
                or any(i not in cours for i in identifiants)):
            raise AtlasInvalide(
                f"{_FLEUVE} {nom!r}, bras n°{rang} : au moins {_constantes.POINTS_MIN_FLEUVE} "
                "identifiants de points du cours attendus")
        lignes.append(tuple(cours[i] for i in identifiants))
    return tuple(lignes)


def _fleuve(brut, rang, chemin_du_nil) -> Fleuve:
    if not isinstance(brut, dict):
        raise AtlasInvalide(f"{_FLEUVE} n°{rang} : ligne attendue")
    nom = _texte(brut.get(_CLE_NOM), _FLEUVE, f"n°{rang}", _CLE_NOM)
    if _CLE_TRACE_DANS in brut:
        return Fleuve(nom, _lignes_du_nil(brut, nom, chemin_du_nil))
    return Fleuve(nom, (_ligne_du_fleuve(brut, nom),))


def _refuser_les_doubles(noms, ou):
    vus = set()
    for nom in noms:
        if nom.casefold() in vus:
            raise AtlasInvalide(f"{ou}, champ {_CLE_NOM} : {nom!r} en double")
        vus.add(nom.casefold())


def charger_atlas(path=None, chemin_du_nil=None) -> Atlas:
    """Lit et valide toutes les lignes ; `chemin_du_nil` laisse éprouver le renvoi au Nil."""
    document = json.loads(Path(path if path is not None else _CHEMIN).read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise AtlasInvalide("document attendu")
    if document.get("date") != _DATE:
        raise AtlasInvalide(f"champ date : {_DATE!r} attendu")
    for champ, attendu in (("projection", _PROJECTION), ("reference", _REFERENCE)):
        if document.get(champ) != attendu:
            raise AtlasInvalide(f"champ {champ} : {attendu!r} attendu")
    _texte(document.get("fidelite"), "atlas", "document", "fidelite")
    fleuves = tuple(_fleuve(b, rang, chemin_du_nil) for rang, b in enumerate(_liste(document, _CLE_FLEUVES), start=1))
    mers = tuple(_point(b, _MER, rang) for rang, b in enumerate(_liste(document, _CLE_MERS), start=1))
    regions = tuple(_point(b, _REGION, rang) for rang, b in enumerate(_liste(document, _CLE_REGIONS), start=1))
    _refuser_les_doubles([f.nom for f in fleuves] + [m.nom for m in mers] + [r.nom for r in regions], "atlas")
    return Atlas(fleuves, mers, regions)


def pas_de_la_carte(carte) -> float:
    """Le côté, en mètres, d'une cellule de surface moyenne : la distance que l'atlas appelle un pas."""
    if not carte:
        raise AtlasInvalide("carte absente ou vide : l'atlas refuse de deviner")
    surface_km2 = sum(c["area_km2"] for c in carte.values()) / len(carte)
    return math.sqrt(surface_km2) * _constantes.metres_par_km()


class _Terre:
    """Les cellules de la carte, avec la boîte de chacune pour n'essayer que les proches."""

    def __init__(self, carte):
        self.carte = carte
        self.boites = {}
        for cid, cellule in carte.items():
            geometrie = cellule["geometry"]
            polygones = geometrie["coordinates"] if geometrie["type"] == "MultiPolygon" else [geometrie["coordinates"]]
            points = [p for polygone in polygones for anneau in polygone for p in anneau]
            xs, ys = [p[0] for p in points], [p[1] for p in points]
            self.boites[cid] = (min(xs), min(ys), max(xs), max(ys))

    def contient(self, x, y) -> bool:
        return any(x0 <= x <= x1 and y0 <= y <= y1 and point_dans_geometrie(x, y, self.carte[cid]["geometry"])
                   for cid, (x0, y0, x1, y1) in self.boites.items())

    def mer_a_moins_d_un_pas(self, x, y, pas) -> bool:
        """Y a-t-il de la mer (ou le bord de la carte) à moins d'un pas du point ?"""
        if not self.contient(x, y):
            return True
        for anneau in range(1, _constantes.ANNEAUX_DE_SONDE + 1):
            rayon = pas * anneau / _constantes.ANNEAUX_DE_SONDE
            for direction in range(_constantes.DIRECTIONS_DE_SONDE):
                angle = math.tau * direction / _constantes.DIRECTIONS_DE_SONDE
                if not self.contient(x + rayon * math.cos(angle), y + rayon * math.sin(angle)):
                    return True
        return False


def _en_metres(point) -> tuple:
    x, y = projeter_epsg3035(point.lat, point.lon)
    return round(x), round(y)


def verifier_la_place(atlas, carte) -> None:
    """Refuse, en le nommant, tout nom qui n'a pas sa place sur la carte figée.

    Un fleuve part de la terre et finit à moins d'un pas de la côte, une mer est hors de toute
    cellule, une région dans une cellule. Un atlas ou une carte vide est refusé : un échantillon
    vide ne prouve rien.
    """
    if not (atlas.fleuves and atlas.mers and atlas.regions):
        raise AtlasInvalide("atlas vide : fleuves, mers et régions sont tous attendus")
    pas = pas_de_la_carte(carte)
    terre = _Terre(carte)
    for fleuve in atlas.fleuves:
        for ligne in fleuve.lignes:
            if not terre.contient(*_en_metres(ligne[0])):
                raise AtlasInvalide(f"{_FLEUVE} {fleuve.nom!r} : sa source {ligne[0].nom!r} n'est pas dans la terre")
            if not terre.mer_a_moins_d_un_pas(*_en_metres(ligne[-1]), pas):
                raise AtlasInvalide(
                    f"{_FLEUVE} {fleuve.nom!r} : son embouchure {ligne[-1].nom!r} est à plus d'un pas de la côte")
    for mer in atlas.mers:
        if terre.contient(*_en_metres(mer)):
            raise AtlasInvalide(f"{_MER} {mer.nom!r} : son point est sur la terre")
    for region in atlas.regions:
        if not terre.contient(*_en_metres(region)):
            raise AtlasInvalide(f"{_REGION} {region.nom!r} : son point est en mer")


def sieges_a_nommer(registre, sieges, villes) -> list:
    """Les sièges placés sur la carte dont le nom n'est pas celui d'une ville de la table, par nom."""
    noms_des_villes = {v.nom for v in villes}
    nommes = []
    for maison in sorted(registre, key=lambda m: m.id):
        if maison.cell_id is None or maison.siege in noms_des_villes:
            continue
        if maison.id not in sieges:
            raise AtlasInvalide(f"maison {maison.id!r} : siège {maison.siege!r} sans position sourcée")
        x, y = sieges[maison.id]
        nommes.append({"nom": maison.siege, "maison": maison.id, "x_m": round(x), "y_m": round(y)})
    return sorted(nommes, key=lambda s: s["nom"])


def document_de_l_atlas(monde, atlas=None, registre=None, sieges=None, villes=None) -> dict:
    """Ce que `GET /atlas` sert : les noms et les places, en mètres EPSG:3035 entiers.

    Ne dépend que des tables de 1400 et de la carte, jamais du tick : le service le calcule une fois.
    """
    atlas = charger_atlas() if atlas is None else atlas
    verifier_la_place(atlas, monde.carte)
    registre = charger_registre_maisons(monde.carte) if registre is None else registre
    sieges = sieges_des_maisons() if sieges is None else sieges
    villes = charger_villes() if villes is None else villes

    def nomme(point):
        x, y = _en_metres(point)
        return {"nom": point.nom, "x_m": x, "y_m": y}

    document = {
        "crs": _PROJECTION,
        "date": _DATE,
        _CLE_FLEUVES: [
            {"nom": f.nom, "lignes": [[{"x_m": x, "y_m": y} for x, y in map(_en_metres, ligne)]
                                      for ligne in f.lignes]}
            for f in atlas.fleuves],
        _CLE_MERS: [nomme(m) for m in atlas.mers],
        _CLE_REGIONS: [nomme(r) for r in atlas.regions],
        "sieges": sieges_a_nommer(registre, sieges, villes),
    }
    noms = ([f["nom"] for f in document[_CLE_FLEUVES]] + [m["nom"] for m in document[_CLE_MERS]]
            + [r["nom"] for r in document[_CLE_REGIONS]] + [s["nom"] for s in document["sieges"]])
    _refuser_les_doubles(noms, "document de l'atlas")
    return document
