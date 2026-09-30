"""Villes documentées de 1400 et attribution pure aux cellules de la carte."""

from dataclasses import dataclass
import json
import math
from pathlib import Path


CHEMIN_VILLES = Path(__file__).resolve().parent.parent / "data" / "villes-1400.json"
PROJECTION_VILLES = "EPSG:3035"
REFERENCE_VILLES = "EPSG:4326"
LATITUDE_MAX = 90
LONGITUDE_MAX = 180
SUR_FRONTIERE = 2


@dataclass(frozen=True)
class Ville:
    nom: str
    latitude: float
    longitude: float
    x_m: float
    y_m: float
    population: int
    estimation: dict


@dataclass(frozen=True)
class AttributionVilles:
    placees: dict[str, int]
    hors_carte: tuple[str, ...]
    entrees: tuple[Ville, ...]


def _texte(valeur, champ):
    if not isinstance(valeur, str) or not valeur.strip():
        raise ValueError(f"{champ} absent ou vide")
    return valeur


def _coordonnée(valeur, champ):
    if isinstance(valeur, bool) or not isinstance(valeur, (int, float)) or not math.isfinite(valeur):
        raise ValueError(f"{champ} doit être un nombre fini")
    return valeur


def charger_villes(chemin: Path | None = None) -> tuple[Ville, ...]:
    """Lit et valide toutes les lignes avant qu'un monde ne soit amorcé."""
    document = json.loads(Path(chemin or CHEMIN_VILLES).read_text(encoding="utf-8"))
    if document.get("projection") != PROJECTION_VILLES:
        raise ValueError("projection des villes incompatible")
    if document.get("reference") != REFERENCE_VILLES:
        raise ValueError("reference des villes incompatible")
    _texte(document.get("conversion"), "conversion")
    if not isinstance(document.get("sources"), list) or not document["sources"]:
        raise ValueError("sources absentes")
    lignes = document.get("villes")
    if not isinstance(lignes, list) or not lignes:
        raise ValueError("villes absentes ou vides")
    villes = []
    noms = set()
    for rang, ligne in enumerate(lignes, start=1):
        if not isinstance(ligne, dict):
            raise ValueError(f"ligne {rang} invalide")
        nom = _texte(ligne.get("nom"), f"ligne {rang} nom")
        if nom.casefold() in noms:
            raise ValueError(f"nom dupliqué : {nom}")
        noms.add(nom.casefold())
        lat = _coordonnée(ligne.get("latitude"), f"{nom} latitude")
        lon = _coordonnée(ligne.get("longitude"), f"{nom} longitude")
        if not -LATITUDE_MAX <= lat <= LATITUDE_MAX:
            raise ValueError(f"{nom} latitude hors bornes")
        if not -LONGITUDE_MAX <= lon <= LONGITUDE_MAX:
            raise ValueError(f"{nom} longitude hors bornes")
        x = _coordonnée(ligne.get("x_m"), f"{nom} x_m")
        y = _coordonnée(ligne.get("y_m"), f"{nom} y_m")
        population = ligne.get("population")
        if type(population) is not int or population <= 0:
            raise ValueError(f"{nom} population invalide")
        estimation = ligne.get("estimation")
        if not isinstance(estimation, dict):
            raise ValueError(f"{nom} estimation absente")
        annee = estimation.get("annee")
        if type(annee) is not int or annee <= 0:
            raise ValueError(f"{nom} annee invalide")
        _texte(estimation.get("incertitude"), f"{nom} incertitude")
        url = _texte(estimation.get("url"), f"{nom} url")
        if not url.startswith(("https://", "http://")):
            raise ValueError(f"{nom} url invalide")
        _texte(estimation.get("passage"), f"{nom} passage")
        villes.append(Ville(nom, lat, lon, x, y, population, estimation))
    return tuple(villes)


def _dans_anneau(x, y, anneau):
    """0 dehors, 1 dedans, 2 sur un segment ; rayon horizontal."""
    dedans = False
    for debut, fin in zip(anneau, anneau[1:]):
        ax, ay = debut
        bx, by = fin
        produit = (x - ax) * (by - ay) - (y - ay) * (bx - ax)
        if produit == 0 and min(ax, bx) <= x <= max(ax, bx) and min(ay, by) <= y <= max(ay, by):
            return SUR_FRONTIERE
        if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
            dedans = not dedans
    return 1 if dedans else 0


def point_dans_geometrie(x, y, geometrie):
    """Inclut les frontières et exclut l'intérieur des trous."""
    polygones = ([geometrie["coordinates"]] if geometrie["type"] == "Polygon"
                 else geometrie["coordinates"])
    for anneaux in polygones:
        position = _dans_anneau(x, y, anneaux[0])
        if position == 0:
            continue
        if any(_dans_anneau(x, y, trou) == 1 for trou in anneaux[1:]):
            continue
        return True
    return False


def attribuer_villes(carte_doc: dict, villes) -> AttributionVilles:
    """Attribue par appartenance polygonale ; les points extérieurs restent nommés."""
    if carte_doc.get("projection") != PROJECTION_VILLES or carte_doc.get("crs", {}).get("geometry") != PROJECTION_VILLES:
        raise ValueError("projection de la carte incompatible")
    cellules = carte_doc.get("cellules")
    if not isinstance(cellules, list) or not cellules:
        raise ValueError("cellules ou geometry absentes")
    for cell in cellules:
        geo = cell.get("geometry")
        if not isinstance(geo, dict) or geo.get("type") not in ("Polygon", "MultiPolygon") or not geo.get("coordinates"):
            raise ValueError(f"geometry absente ou invalide pour cell_id={cell.get('cell_id')}")
    triees = sorted(cellules, key=lambda c: c["cell_id"])
    placees = {}
    hors_carte = []
    villes = tuple(Ville(**v) if isinstance(v, dict) else v for v in villes)
    for ville in villes:
        cid = next((cell["cell_id"] for cell in triees
                    if point_dans_geometrie(ville.x_m, ville.y_m, cell["geometry"])), None)
        if cid is None:
            hors_carte.append(ville.nom)
        else:
            placees[ville.nom] = cid
    return AttributionVilles(placees, tuple(hors_carte), villes)
