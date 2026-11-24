"""Contours allégés et identités de 1400, sans modifier le monde."""

import math

from sim.maisons import charger_maisons, maisons_depuis_monde
from sim.puissances import charger_table, puissances_depuis_monde
from sim.snapshot_export import SnapshotExportError
from sim.villes import attribuer_villes, charger_villes, point_dans_geometrie

TOLERANCE_CONTOUR_M = 1000
SOMMETS_MIN_ANNEAU = 4
DIVISEUR_MILIEU = 2


def _distance_corde(point, debut, fin):
    """Distance perpendiculaire à la corde ; corde nulle traitée comme un point."""
    dx, dy = fin[0] - debut[0], fin[1] - debut[1]
    longueur = math.hypot(dx, dy)
    if longueur == 0:
        return math.dist(point, debut)
    return abs(dx * (debut[1] - point[1]) - (debut[0] - point[0]) * dy) / longueur


def _simplifier_chaine(points, tolerance):
    """Douglas-Peucker itératif, avec départage par le premier indice."""
    gardes = {0, len(points) - 1}
    pile = [(0, len(points) - 1)]
    while pile:
        debut, fin = pile.pop()
        if fin <= debut + 1:
            continue
        sommet = max(range(debut + 1, fin),
                     key=lambda i: _distance_corde(points[i], points[debut], points[fin]))
        if _distance_corde(points[sommet], points[debut], points[fin]) > tolerance:
            gardes.add(sommet)
            pile.extend(((debut, sommet), (sommet, fin)))
    return [points[i] for i in sorted(gardes)]


def simplifier_anneau(anneau, tolerance):
    """Coupe l'anneau fermé en deux chaînes, les simplifie puis arrondit au mètre."""
    points = list(anneau[:-1])
    if not points:
        return []
    coupe = max(range(len(points)), key=lambda i: math.dist(points[0], points[i]))
    premiere = _simplifier_chaine(points[:coupe + 1], tolerance)
    seconde = _simplifier_chaine(points[coupe:] + [points[0]], tolerance)
    return [[round(x), round(y)] for x, y in premiere[:-1] + seconde]


def _polygones(geometrie):
    return ([geometrie["coordinates"]] if geometrie["type"] == "Polygon"
            else geometrie["coordinates"])


def point_temoin(cellule_carte):
    """Garde le centroïde intérieur, sinon le milieu du plus large intervalle intérieur."""
    centre = cellule_carte["centroid"]
    x, y = centre["x_m"], centre["y_m"]
    geometrie = cellule_carte["geometry"]
    if point_dans_geometrie(x, y, geometrie):
        return x, y
    intersections = []
    for polygone in _polygones(geometrie):
        for anneau in polygone:
            for (ax, ay), (bx, by) in zip(anneau, anneau[1:]):
                # Une extrémité haute exclue évite de compter deux fois les sommets.
                if (ay > y) != (by > y):
                    intersections.append(ax + (y - ay) * (bx - ax) / (by - ay))
    intersections.sort()
    intervalles = [(a, b) for a, b in zip(intersections[::DIVISEUR_MILIEU],
                                         intersections[1::DIVISEUR_MILIEU]) if b > a]
    if not intervalles:
        raise ValueError(f"cellule {cellule_carte['cell_id']} : aucun intervalle intérieur pour le témoin")
    debut, fin = max(intervalles, key=lambda intervalle: intervalle[1] - intervalle[0])
    return (debut + fin) / DIVISEUR_MILIEU, y


def contour_servi(cellule_carte):
    """Refuse de perdre le témoin ou un anneau, même après l'arrondi du repli."""
    original = _polygones(cellule_carte["geometry"])
    temoin = point_temoin(cellule_carte)
    contour = {"type": "MultiPolygon", "coordinates": [
        [simplifier_anneau(a, TOLERANCE_CONTOUR_M) for a in p] for p in original
    ]}
    if (any(len(a) < SOMMETS_MIN_ANNEAU for p in contour["coordinates"] for a in p)
            or not point_dans_geometrie(*temoin, contour)):
        contour["coordinates"] = [
            [[[round(x), round(y)] for x, y in a] for a in p] for p in original
        ]
        if not point_dans_geometrie(*temoin, contour):
            raise ValueError(f"cellule {cellule_carte['cell_id']} : contour arrondi sans son témoin")
    return contour


def terres_et_pays(monde, matiere, sources=None) -> dict:
    """`terres` et `pays` de `GET /terres`, sans la table des pays des lieux (`terres_pays_et_lieux`)."""
    return terres_pays_et_lieux(monde, matiere, sources)[0]


def habitants_des_pays(pays, des_lieux, populations) -> dict:
    """`habitants_des_pays` de `GET /terres` : chaque pays donné → la somme des habitants de ses lieux.

    `des_lieux` est la table (cell_id, rang) → pays de `terres_pays_et_lieux`, `populations` les
    habitants de chaque lieu, (cell_id, rang) → habitants. Un lieu sans maître n'est d'aucun pays ;
    un pays donné qui ne tient aucun lieu (un suzerain cité, le Saint-Empire) compte 0, une mesure."""
    habitants = {identifiant: 0 for identifiant in pays}
    for cle, population in populations.items():
        identifiant = des_lieux.get(cle)
        if identifiant is not None:
            habitants[identifiant] += population
    return habitants


def terres_pays_et_lieux(monde, matiere, sources=None) -> tuple:
    """`terres` et `pays` de `GET /terres` : le maître du bourg de chaque cellule, sa maison et son pays.
    Rend aussi, hors du document, la table (cell_id, rang) → pays de chaque lieu qui en a un.

    La maison d'une terre est celle au sommet de la suzeraineté du maître de son bourg
    (`guerre.racine`) ; son pays vient de `pays_servis.pays_des_terres` (une puissance de 1400,
    une terre de départ ou un seigneur libre). Une terre sans maître n'a ni maison ni pays.
    `autres_pays` liste, par rang, les lieux de la terre dont le pays n'est pas celui du bourg :
    `{rang, maitre, pays}` (`pays_servis.pays_des_lieux`), vide quand tous en sont.
    `pays` porte la fiche de chaque pays présent, lieux compris, et de chaque suzerain cité, triée
    par identifiant (`pays_servis.fiches_des_pays`). `sources` : celles de `sources_des_pays`,
    déjà lues.
    """
    from sim.guerre import racine
    from sim.pays_servis import fiches_des_pays, pays_des_lieux, pays_des_terres, sources_des_pays
    sources = sources_des_pays(monde) if sources is None else sources
    par_id = {m.id: m for m in monde.maisons}
    pays = pays_des_terres(monde, sources.vue, sources.maisons, sources.lieux)
    des_lieux = pays_des_lieux(monde, sources.vue, sources.maisons, sources.lieux)
    terres = []
    for cid, cellule in sorted(monde.cells.items()):
        maitre = next((l.maitre for l in cellule.lieux if l.rang == 0), None)
        autres = [{"rang": l.rang, "maitre": l.maitre, "pays": des_lieux[cid, l.rang]}
                  for l in sorted(cellule.lieux, key=lambda l: l.rang) if des_lieux[cid, l.rang] != pays[cid]]
        terres.append({"cell_id": cid, "maitre": maitre,
                       "maison": None if maitre is None else racine(par_id, maitre), "pays": pays[cid],
                       "autres_pays": autres})
    presents = set(pays.values()) | set(des_lieux.values())
    fiches = fiches_des_pays({p for p in presents if p is not None}, monde, sources.table,
                             sources.maisons, sources.seigneuries, matiere)
    return {"terres": terres, "pays": fiches}, {cle: p for cle, p in des_lieux.items() if p is not None}


def document_carte(world, table=None, maisons=None):
    """Rend la carte figée et sa vue des puissances, réutilisable pour les départs."""
    if not world.carte:
        raise SnapshotExportError("Le monde n'a aucune carte figée à servir.")
    if table is None:
        table = charger_table()
    if maisons is None:
        maisons = charger_maisons()
    vue = puissances_depuis_monde(world, table=table)
    tenantes = maisons_depuis_monde(world, table=table, maisons=maisons)
    puissances = {p.id: {"id": p.id, "nom": p.nom} for p in table.puissances}
    identites = {m.id: {"id": m.id, "nom": m.nom} for m in maisons.maisons}
    carte = world.carte_meta | {"cellules": [world.carte[c] for c in sorted(world.carte)]}
    attribution = attribuer_villes(carte, charger_villes())
    villes = {cid: [] for cid in world.carte}
    for ville in sorted(attribution.entrees, key=lambda v: v.nom):
        cid = attribution.placees.get(ville.nom)
        if cid is not None:
            villes[cid].append({"nom": ville.nom, "population": ville.population,
                               "x_m": ville.x_m, "y_m": ville.y_m})
    cellules = [{"cell_id": cid, "contour": contour_servi(cellule),
                 "relief": cellule["relief"], "area_km2": cellule["area_km2"], "puissance": puissances.get(vue[cid]),
                 "maison": identites.get(tenantes[cid]), "villes": villes[cid]}
                for cid, cellule in sorted(world.carte.items())]
    return {"crs": "EPSG:3035", "tolerance_m": TOLERANCE_CONTOUR_M,
            "version": world.carte_meta.get("version"), "cell_count": len(cellules),
            "cells": cellules, "villes_hors_carte": sorted(attribution.hors_carte)}, vue
