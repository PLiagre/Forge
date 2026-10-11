"""Route achevée du bourg vers un lieu de sa cellule (lot #418).

Une rue achevée sans porte vise au plus un lieu, dans un cône. Le lieu
atteint envoie quatre fois plus de grain au bourg. Une route vers le voisin
(`porte_cell_id`) ne compte pas ici. Sans ancre de bourg, l'effet est refusé.
"""

from __future__ import annotations

import math

import sim.constants as _constantes
import sim.places as places
from sim.lieux import lieux_de_cellule


def _eloignement(point) -> float:
    return point[0] * point[0] + point[1] * point[1]


def _rue_qui_compte(rue) -> bool:
    return not rue.en_chantier and rue.porte_cell_id is None


def lieu_de_la_route(rue, places) -> tuple[int | None, str]:
    """Le rang visé par la rue, ou None et la raison du refus."""
    if places is None:
        return None, "ancres des bourgs absentes"
    if len(places) <= 1:
        return None, "un seul lieu"
    premier, dernier = rue.points[0], rue.points[-1]
    bout = dernier if _eloignement(dernier) >= _eloignement(premier) else premier
    if bout[0] == 0 and bout[1] == 0:
        return None, "route sans direction"
    theta = math.atan2(bout[1], bout[0])
    origine = places[0]
    retenu = None
    ecart_retenu = None
    for rang in range(1, len(places)):
        place = places[rang]
        phi = math.atan2(place.y_m - origine.y_m, place.x_m - origine.x_m)
        ecart = abs(math.atan2(math.sin(theta - phi), math.cos(theta - phi)))
        if (ecart_retenu is None or ecart < ecart_retenu
                or (ecart == ecart_retenu and rang < retenu)):
            retenu = rang
            ecart_retenu = ecart
    if ecart_retenu <= math.radians(_constantes.ANGLE_ROUTE_INTERIEURE_DEGRES):
        return retenu, ""
    angle = _constantes.ANGLE_ROUTE_INTERIEURE_DEGRES
    degres = math.degrees(ecart_retenu)
    return None, (
        f"aucun lieu à moins de {angle:g}° (le plus proche, rang {retenu}, à {degres:.1f}°)"
    )


def _places_de(monde, cell_id):
    ancres = getattr(monde, "ancres_des_bourgs", None)
    if ancres is None or cell_id not in ancres:
        return None
    cellule = monde.cells[cell_id]
    surfaces = [lieu.surface_km2 for lieu in lieux_de_cellule(cell_id, cellule.area_km2)]
    carte = getattr(monde, "carte", None) or {}
    return places.places_de_cellule(cell_id, carte.get(cell_id), surfaces, *ancres[cell_id])


def routes_vers_les_lieux(monde, cell_id) -> tuple[dict[int, str] | None, str]:
    """Rangs atteints par une route qui compte, ou None et la raison."""
    plans = getattr(monde, "plans", None) or {}
    plan = plans.get(cell_id)
    rues = [rue for rue in (plan.rues if plan is not None else ()) if _rue_qui_compte(rue)]
    if not rues:
        return None, "aucune route qui compte"
    lieu_places = _places_de(monde, cell_id)
    if lieu_places is None:
        return None, "ancres des bourgs absentes"
    atteints = {}
    raison_echec = None
    for rue in rues:
        rang, raison = lieu_de_la_route(rue, lieu_places)
        if rang is None:
            if raison_echec is None:
                raison_echec = raison
        else:
            atteints[rang] = raison
    if not atteints:
        return None, raison_echec
    return atteints, ""


def facteurs_des_routes(monde) -> dict[int, dict[int, float]]:
    """Multiplicateur par rang, pour les seules cellules qui ont une route qui compte.

    Un rang absent de la table garde la capacité du chemin. Deux routes vers
    le même lieu ne se cumulent pas. Sans ancre, aucun lieu n'est calculé.
    """
    plans = getattr(monde, "plans", None)
    if not plans or getattr(monde, "ancres_des_bourgs", None) is None:
        return {}
    facteur = _constantes.FACTEUR_ROUTE_INTERIEURE
    facteurs = {}
    for cid, plan in plans.items():
        rues = [rue for rue in plan.rues if _rue_qui_compte(rue)]
        if not rues or cid not in monde.cells:
            continue
        lieu_places = _places_de(monde, cid)
        if lieu_places is None:
            continue
        atteints = set()
        for rue in rues:
            rang, _raison = lieu_de_la_route(rue, lieu_places)
            if rang is not None:
                atteints.add(rang)
        if atteints:
            facteurs[cid] = {rang: facteur for rang in atteints}
    return facteurs
