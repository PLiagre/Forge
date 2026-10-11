"""La place de chaque lieu dans sa cellule, vue dérivée et pure (lot #393).

On ne dessine ni un lieu, ni un flux vers un siège, sans savoir où il est. Chaque lieu
reçoit un point du polygone de sa cellule, en mètres EPSG:3035 et en degrés :

- le bourg (rang 0) au siège sourcé de la maison qui le tient (Bar-le-Duc sur
  l'Ornain), sinon à la plus grande ville de la cellule, sinon au centroïde, et si le
  centroïde tombe hors du polygone, à un point intérieur déterministe ;
- les autres rangs par un tirage déterministe dérivé de `cell_id` (jamais l'aléa du
  monde), qui garde entre deux lieux au moins `ECART_MIN_ENTRE_LIEUX` × √(surface d'un
  lieu).

Aucune position n'est stockée : la vue se recalcule depuis la carte figée, les maîtres
des bourgs et les tables sourcées. Une géométrie absente est refusée en nommant la
cellule, jamais remplacée par un centroïde.
"""

from __future__ import annotations

import dataclasses
import math
import random

import sim.constants as _constantes
from sim.capitales import charger_capitales
from sim.lieux import LieuxInvalides, lieux_de_cellule
from sim.maisons import charger_maisons
from sim.model import _NoBadSpatialField
from sim.projection import deprojeter_epsg3035, projeter_epsg3035
from sim.puissances import charger_table
from sim.seigneuries import charger_seigneuries, identifiant_de_seigneurie
from sim.villes import point_dans_geometrie

# D'où vient la place d'un lieu : ce qu'on en sait, du plus sûr au plus plausible.
SIEGE, VILLE, CENTROIDE, INTERIEUR, TIRAGE = "siege", "ville", "centroide", "interieur", "tirage"
# Le milieu d'un segment ; géométrie, pas une règle du monde.
MILIEU = 0.5


@dataclasses.dataclass(frozen=True)
class Place(_NoBadSpatialField):
    x_m: float
    y_m: float
    latitude: float
    longitude: float
    origine: str

    def en_document(self) -> dict:
        """Ce que `/lieu` et la photographie publient du point d'un lieu."""
        return {"x_m": self.x_m, "y_m": self.y_m, "latitude": self.latitude, "longitude": self.longitude}


def _place(x, y, origine) -> Place:
    x, y = round(x, _constantes.DECIMALES_POINT_METRES), round(y, _constantes.DECIMALES_POINT_METRES)
    latitude, longitude = deprojeter_epsg3035(x, y)
    return Place(x, y, round(latitude, _constantes.DECIMALES_POINT_DEGRES),
                 round(longitude, _constantes.DECIMALES_POINT_DEGRES), origine)


def distance_km(a: Place, b: Place) -> float:
    """La distance entre deux lieux, en kilomètres, à vol d'oiseau dans le plan EPSG:3035."""
    return math.hypot(a.x_m - b.x_m, a.y_m - b.y_m) / _constantes.metres_par_km()


def sieges_des_maisons(table=None, maisons=None) -> dict[str, tuple[float, float]]:
    """Le siège sourcé de chaque maison du registre qui en a un, en mètres EPSG:3035.

    Mêmes tables et mêmes identifiants que `charger_registre_maisons` : la capitale d'une
    grande maison, l'ancre de plus petit identifiant d'une institution, le siège d'une
    seigneurie de départ. Une maison plausible n'a pas de siège sourcé.
    """
    table = charger_table() if table is None else table
    maisons = charger_maisons() if maisons is None else maisons
    sieges = {f"grande-{c.maison}": projeter_epsg3035(c.lat, c.lon) for c in charger_capitales(maisons=maisons)}
    for p in table.puissances:
        if maisons.par_puissance[p.id] is None:
            ancre = min((a for a in table.ancres if a.puissance == p.id), key=lambda a: a.id)
            sieges[f"institution-{p.id}"] = projeter_epsg3035(ancre.lat, ancre.lon)
    for s in charger_seigneuries(table=table):
        sieges[identifiant_de_seigneurie(s.id)] = (s.siege.x_m, s.siege.y_m)
    return sieges


def _intervalles(geometrie, y) -> list[tuple[float, float]]:
    """Les segments de la ligne horizontale d'ordonnée y qui sont dans la géométrie (pair-impair, trous compris)."""
    polygones = [geometrie["coordinates"]] if geometrie["type"] == "Polygon" else geometrie["coordinates"]
    coupures = []
    for anneaux in polygones:
        for anneau in anneaux:
            for (xa, ya), (xb, yb) in zip(anneau, anneau[1:] + anneau[:1]):
                if (ya > y) != (yb > y):
                    coupures.append(xa + (y - ya) * (xb - xa) / (yb - ya))
    coupures.sort()
    paires = iter(coupures)  # entrée, sortie, entrée, sortie…
    return list(zip(paires, paires))


def _boite(geometrie):
    polygones = [geometrie["coordinates"]] if geometrie["type"] == "Polygon" else geometrie["coordinates"]
    points = [p for anneaux in polygones for p in anneaux[0]]
    return (min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points))


def point_interieur(cell_id, geometrie, y_prefere) -> tuple[float, float]:
    """Un point intérieur déterministe : le milieu du plus long segment intérieur de la ligne horizontale qui passe par
    `y_prefere`, sinon par des lignes également réparties dans la hauteur de la cellule."""
    x_min, y_min, x_max, y_max = _boite(geometrie)
    lignes = _constantes.BALAYAGES_INTERIEURS
    ordonnees = [y_prefere] + [y_min + (y_max - y_min) * (k + 1) / (lignes + 1) for k in range(lignes)]
    for y in ordonnees:
        segments = sorted(_intervalles(geometrie, y), key=lambda s: (s[1] - s[0], -s[0]), reverse=True)
        for debut, fin in segments:
            x = debut + (fin - debut) * MILIEU
            if fin > debut and point_dans_geometrie(x, y, geometrie):
                return x, y
    raise LieuxInvalides(f"cell_id {cell_id} : aucun point intérieur trouvé dans sa géométrie")


def places_de_cellule(cell_id, enregistrement, surfaces, siege=None, ville=None) -> tuple[Place, ...]:
    """Les places des lieux d'une cellule, dans l'ordre des rangs.

    `enregistrement` est celui de la carte figée (géométrie et centroïde) ; `surfaces` les
    surfaces des lieux (`lieux_de_cellule`) ; `siege` et `ville`, des points (x, y) en
    mètres, ou None. Un point qui n'est pas dans la géométrie n'est pas retenu.
    """
    geometrie = (enregistrement or {}).get("geometry")
    if not geometrie or not geometrie.get("coordinates"):
        raise LieuxInvalides(f"cell_id {cell_id} : géométrie absente, aucune place n'est devinée")
    centre = (enregistrement.get("centroid") or {})
    if not surfaces:
        return ()
    if siege is not None and point_dans_geometrie(*siege, geometrie):
        bourg = _place(*siege, SIEGE)
    elif ville is not None and point_dans_geometrie(*ville, geometrie):
        bourg = _place(*ville, VILLE)
    elif "x_m" not in centre or "y_m" not in centre:
        raise LieuxInvalides(f"cell_id {cell_id} : centroïde absent, aucune place n'est devinée")
    elif point_dans_geometrie(centre["x_m"], centre["y_m"], geometrie):
        bourg = _place(centre["x_m"], centre["y_m"], CENTROIDE)
    else:
        bourg = _place(*point_interieur(cell_id, geometrie, centre["y_m"]), INTERIEUR)
    places = [bourg]
    if len(surfaces) > 1:
        ecart = _constantes.ECART_MIN_ENTRE_LIEUX * math.sqrt(surfaces[-1]) * _constantes.metres_par_km()
        x_min, y_min, x_max, y_max = _boite(geometrie)
        tirage = random.Random(f"places-des-lieux-{cell_id}")
        for rang in range(1, len(surfaces)):
            for _ in range(_constantes.TIRAGES_MAX_PAR_LIEU):
                x, y = tirage.uniform(x_min, x_max), tirage.uniform(y_min, y_max)
                if (point_dans_geometrie(x, y, geometrie)
                        and all(math.hypot(x - p.x_m, y - p.y_m) >= ecart for p in places)):
                    places.append(_place(x, y, TIRAGE))
                    break
            else:
                raise LieuxInvalides(f"cell_id {cell_id} : pas de place pour le lieu {rang} à {ecart:.0f} m "
                                     f"des autres en {_constantes.TIRAGES_MAX_PAR_LIEU} tirages")
    return tuple(places)


def bourgs_et_maitres(monde) -> tuple:
    """Ce qui change la place d'un bourg dans un monde : le maître de chaque bourg."""
    return tuple((cid, cellule.lieux[0].maitre if cellule.lieux else None) for cid, cellule in sorted(monde.cells.items()))


def _villes_placees(monde) -> dict:
    """La plus grande ville placée de chaque cellule, en mètres, ou rien."""
    villes = {}
    attribution = getattr(monde, "attribution_villes", None)
    if attribution is None:
        return villes
    for ville in sorted(attribution.entrees, key=lambda ville: (-ville.population, ville.nom)):
        cid = attribution.placees.get(ville.nom)
        if cid is not None and cid not in villes:
            villes[cid] = (ville.x_m, ville.y_m)
    return villes


def ancres_des_bourgs(monde, sieges=None) -> dict[int, tuple]:
    """Siège du maître du bourg et ville placée, par cellule.

    Ce sont les deux arguments que `places_de_cellule` reçoit après la carte.
    `World.charger` les garde ; le tick les relit et ne relit pas le maître.
    """
    sieges = sieges_des_maisons() if sieges is None else sieges
    villes = _villes_placees(monde)
    ancres = {}
    for cid, cellule in sorted(monde.cells.items()):
        maitre = cellule.lieux[0].maitre if cellule.lieux else None
        ancres[cid] = (sieges.get(maitre), villes.get(cid))
    return ancres


def places_du_monde(monde, sieges=None) -> dict[int, tuple[Place, ...]]:
    """Les places des lieux de chaque cellule du monde, par `cell_id`."""
    sieges = sieges_des_maisons() if sieges is None else sieges
    ancres = ancres_des_bourgs(monde, sieges)
    places = {}
    for cid, cellule in sorted(monde.cells.items()):
        surfaces = [lieu.surface_km2 for lieu in lieux_de_cellule(cid, cellule.area_km2)]
        places[cid] = places_de_cellule(cid, monde.carte.get(cid), surfaces, *ancres[cid])
    return places
