"""La forme des cellules sur la carte : des bords brisés, vue dérivée et pure.

La carte figée trace le bord entre deux cellules voisines en droites, d'où les nids
d'abeille. Ce module en tire un dessin sans toucher la carte :

- les sommets de la carte sont arrondis au mètre, et ceux qui tombent sur un côté à
  l'arrondi près y sont posés (`accrocher_les_sommets`) ; un segment que deux cellules
  partagent est un segment terre-terre, tout autre segment est de la côte (ou du bord
  de la carte) et reste tel quel, sommet pour sommet ;
- chaque segment terre-terre se brise en une ligne tirée de ses deux `cell_id` (jamais
  de l'aléa du monde), la même des deux côtés. Elle reste dans un losange dont le
  segment est la grande diagonale ; elle ne touche aucun autre côté de ses deux
  cellules ni aucune ligne déjà brisée, et ne fait passer de l'autre côté ni une place
  de leurs lieux ni un sommet. Sinon le losange se rétrécit, et au bout des essais le
  segment reste droit ;
- le contour de chaque cellule s'assemble de ses côtés et de ses bords brisés.

Le calcul n'emploie que l'addition, la multiplication, la division, la racine et les
tirages de `random` : les mêmes bits sous Windows et sous Linux. Rien n'est stocké dans
le monde ; le tick ne lit pas ce module.
"""

from __future__ import annotations

import dataclasses
import math
import random

import sim.constants as _constantes
from sim.villes import _dans_anneau

# Le milieu d'un segment ; géométrie, pas une règle du monde.
MOITIE = 0.5
# Un segment a deux bouts, et sépare au plus deux cellules.
BOUTS_D_UN_SEGMENT = 2
# Le côté des cases de l'index qui trouve les sommets proches d'un côté, en mètres.
MAILLE_D_INDEX_M = 20000


class FormesInvalides(ValueError):
    """La carte ne se découpe pas : la cellule ou le couple fautif est nommé."""


@dataclasses.dataclass(frozen=True)
class Decoupe:
    """Ce que rend le découpage de la carte.

    `contours` : par `cell_id`, un MultiPolygon en mètres entiers, anneaux dans le sens de
    la carte figée. `bords` : par couple (a, b) de cellules, a < b, les lignes brisées de
    leurs segments communs, chacune du plus petit bout au plus grand. `droits` : les
    segments (a, b, k) restés droits. `hors_adjacence` : les couples qui partagent un
    segment sans arête `land-land` dans l'adjacence de la carte.
    """
    contours: dict
    bords: dict
    droits: tuple
    hors_adjacence: tuple


def _polygones(geometrie):
    return [geometrie["coordinates"]] if geometrie["type"] == "Polygon" else geometrie["coordinates"]


def anneaux_arrondis(cell_id, enregistrement) -> list:
    """Les polygones d'une cellule, anneaux fermés en mètres entiers, sans sommet répété."""
    geometrie = (enregistrement or {}).get("geometry")
    if not geometrie or not geometrie.get("coordinates"):
        raise FormesInvalides(f"cell_id {cell_id} : géométrie absente, aucun contour n'est deviné")
    polygones = []
    for polygone in _polygones(geometrie):
        anneaux = []
        for anneau in polygone:
            points = []
            for x, y in anneau:
                point = (round(x), round(y))
                if not points or point != points[-1]:
                    points.append(point)
            if points[0] != points[-1]:
                points.append(points[0])
            anneaux.append(points)
        polygones.append(anneaux)
    return polygones


def _cle(u, v):
    return (u, v) if u < v else (v, u)


def _sans_pointes(anneau) -> list:
    """L'anneau fermé sans sommet répété ni aller-retour sur un même côté (une pointe de
    largeur nulle), en tournant autour de l'anneau ; vide s'il ne reste rien."""
    points = list(anneau[:-1])
    change = True
    while change:
        change, i = False, 0
        while len(points) > BOUTS_D_UN_SEGMENT and i < len(points):
            n = len(points)
            avant, apres = points[i - 1], points[(i + 1) % n]
            if points[i] == apres:
                retirer = {(i + 1) % n}
            elif avant == apres:
                retirer = {i, (i + 1) % n}
            else:
                i += 1
                continue
            for j in sorted(retirer, reverse=True):
                del points[j]
            change, i = True, max(min(i, len(points)) - BOUTS_D_UN_SEGMENT, 0)
    return points + points[:1] if len(points) > BOUTS_D_UN_SEGMENT else []


def accrocher_les_sommets(anneaux_par_cellule) -> dict:
    """Pose sur un côté chaque sommet de la carte qui y tombe à l'arrondi près.

    Arrondie au mètre, la carte figée garde des sommets à quelques décimètres d'un côté
    qui devrait passer par eux : une cellule qui touche le milieu d'un côté de sa voisine,
    un anneau qui se pince. Le côté reçoit ce sommet, dans le même ordre pour toutes les
    cellules qui le portent : le trait ne bouge pas de plus de `ACCROCHE_SOMMET_M`, et deux
    cellules qui se touchent partagent enfin les mêmes côtés.
    """
    tolerance = _constantes.ACCROCHE_SOMMET_M
    index = {}
    cotes = set()
    for polygones in anneaux_par_cellule.values():
        for polygone in polygones:
            for anneau in polygone:
                for point in anneau[:-1]:
                    case = (point[0] // MAILLE_D_INDEX_M, point[1] // MAILLE_D_INDEX_M)
                    index.setdefault(case, set()).add(point)
                cotes.update(_cle(u, v) for u, v in zip(anneau, anneau[1:]))
    poses = {}
    for u, v in sorted(cotes):
        dx, dy = v[0] - u[0], v[1] - u[1]
        carre = dx * dx + dy * dy
        x_min, y_min = (min(u[0], v[0]) - tolerance) // MAILLE_D_INDEX_M, (min(u[1], v[1]) - tolerance) // MAILLE_D_INDEX_M
        x_max, y_max = (max(u[0], v[0]) + tolerance) // MAILLE_D_INDEX_M, (max(u[1], v[1]) + tolerance) // MAILLE_D_INDEX_M
        sur_le_cote = []
        for case_x in range(int(x_min), int(x_max) + 1):
            for case_y in range(int(y_min), int(y_max) + 1):
                for point in index.get((case_x, case_y), ()):
                    produit = dx * (point[1] - u[1]) - dy * (point[0] - u[0])
                    avance = dx * (point[0] - u[0]) + dy * (point[1] - u[1])
                    if 0 < avance < carre and produit * produit <= tolerance * tolerance * carre:
                        sur_le_cote.append((avance, point))
        if sur_le_cote:
            poses[(u, v)] = [point for _, point in sorted(sur_le_cote)]
    resultat = {}
    for cid, polygones in anneaux_par_cellule.items():
        nouveaux = []
        for polygone in polygones:
            anneaux = []
            for anneau in polygone:
                points = [anneau[0]]
                for u, v in zip(anneau, anneau[1:]):
                    milieu = poses.get(_cle(u, v), [])
                    points += (milieu if u < v else milieu[::-1]) + [v]
                anneaux.append(_sans_pointes(points))
            # Un anneau réduit à une pointe disparaît ; sans son bord extérieur, l'île entière.
            if anneaux[0]:
                nouveaux.append([anneau for anneau in anneaux if anneau])
        resultat[cid] = nouveaux
    return resultat


def segments_partages(anneaux_par_cellule) -> dict:
    """Chaque segment que deux cellules partagent, par couple (a, b), a < b, triés."""
    tenants = {}
    for cid in sorted(anneaux_par_cellule):
        for polygone in anneaux_par_cellule[cid]:
            for anneau in polygone:
                for u, v in zip(anneau, anneau[1:]):
                    tenants.setdefault(_cle(u, v), []).append(cid)
    couples = {}
    for cle in sorted(tenants):
        cellules = tenants[cle]
        if len(cellules) == 1:
            continue
        if len(cellules) > len(set(cellules)) or len(cellules) > BOUTS_D_UN_SEGMENT:
            raise FormesInvalides(f"cell_id {', '.join(map(str, cellules))} : le segment {cle} n'a pas deux "
                                  "cellules distinctes de part et d'autre")
        couples.setdefault(tuple(sorted(cellules)), []).append(cle)
    return couples


def losange(p, q, hauteur) -> list:
    """Le losange de grande diagonale pq, de demi-largeur `hauteur` × |pq|."""
    dx, dy = q[0] - p[0], q[1] - p[1]
    mx, my = p[0] + dx * MOITIE, p[1] + dy * MOITIE
    return [p, (mx - hauteur * dy, my + hauteur * dx), q, (mx + hauteur * dy, my - hauteur * dx)]


def _orientation(a, b, c) -> int:
    """Le signe du produit vectoriel ab × ac ; exact sur des mètres entiers."""
    produit = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return (produit > 0) - (produit < 0)


def _sur_le_segment(a, b, c) -> bool:
    """c, aligné avec ab, est-il entre a et b ?"""
    return min(a[0], b[0]) <= c[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= c[1] <= max(a[1], b[1])


def se_touchent(premier, second) -> bool:
    """Deux segments ont-ils un point commun autre qu'un bout qu'ils partagent ?"""
    (a, b), (c, d) = premier, second
    communs = {a, b} & {c, d}
    if len(communs) == BOUTS_D_UN_SEGMENT:
        return True
    if communs:
        commun = communs.pop()
        autre, autre_second = (b if a == commun else a), (d if c == commun else c)
        return ((_orientation(commun, autre, autre_second) == 0)
                and (_sur_le_segment(commun, autre, autre_second) or _sur_le_segment(commun, autre_second, autre)))
    o1, o2, o3, o4 = _orientation(a, b, c), _orientation(a, b, d), _orientation(c, d, a), _orientation(c, d, b)
    if o1 != o2 and o3 != o4 and 0 not in (o1, o2, o3, o4):
        return True
    return ((o1 == 0 and _sur_le_segment(a, b, c)) or (o2 == 0 and _sur_le_segment(a, b, d))
            or (o3 == 0 and _sur_le_segment(c, d, a)) or (o4 == 0 and _sur_le_segment(c, d, b)))


def _boite(points):
    xs, ys = [x for x, _ in points], [y for _, y in points]
    return min(xs), min(ys), max(xs), max(ys)


def _boites_se_touchent(a, b):
    (ax_min, ay_min, ax_max, ay_max), (bx_min, by_min, bx_max, by_max) = a, b
    return ax_min <= bx_max and bx_min <= ax_max and ay_min <= by_max and by_min <= ay_max


def ligne_brisee(p, q, hauteur, graine, points=()) -> list:
    """La ligne brisée de p à q, en mètres entiers, dans son losange (`losange`).

    Le milieu de chaque morceau s'écarte de la moyenne de ses bouts d'un tirage, borné par
    le losange : la ligne est le graphe d'une fonction le long de pq, elle ne se recoupe pas.
    Chaque point de `points` (une place, un sommet) reste du côté de pq où il est : là où la
    ligne passe à sa hauteur, elle s'en tient au plus à mi-chemin de pq.
    """
    dx, dy = q[0] - p[0], q[1] - p[1]
    carre = dx * dx + dy * dy
    pas, niveaux, largeur_finale = math.sqrt(carre), 0, 1.0
    while pas > _constantes.PAS_BRISURE_M:
        pas *= MOITIE
        largeur_finale *= MOITIE
        niveaux += 1
    reperes = []
    for x, y in points:
        s_point = ((x - p[0]) * dx + (y - p[1]) * dy) / carre
        f_point = ((y - p[1]) * dx - (x - p[0]) * dy) / carre
        if 0.0 < s_point < 1.0 and f_point != 0.0:
            reperes.append((s_point, f_point * MOITIE))
    tirage = random.Random(graine)
    abscisses, ecarts, amplitude = [0.0, 1.0], [0.0, 0.0], _constantes.ECART_BRISURE
    for _ in range(niveaux):
        nouvelles, nouveaux = [0.0], [0.0]
        for i in range(len(abscisses) - 1):
            s = (abscisses[i] + abscisses[i + 1]) * MOITIE
            largeur = abscisses[i + 1] - abscisses[i]
            borne = (hauteur + hauteur) * min(s, 1.0 - s)
            proches = [f for s_point, f in reperes if abs(s_point - s) <= largeur_finale]
            bas = max([-borne] + [f for f in proches if f < 0.0])
            haut = min([borne] + [f for f in proches if f > 0.0])
            ecart = (ecarts[i] + ecarts[i + 1]) * MOITIE + tirage.uniform(-amplitude, amplitude) * largeur
            nouvelles += [s, abscisses[i + 1]]
            nouveaux += [max(bas, min(haut, ecart)), ecarts[i + 1]]
        abscisses, ecarts = nouvelles, nouveaux
        amplitude *= _constantes.AMORTI_BRISURE
    ligne = [p]
    for s, f in zip(abscisses[1:-1], ecarts[1:-1]):
        point = (round(p[0] + s * dx - f * dy), round(p[1] + s * dy + f * dx))
        if point not in (ligne[-1], q):
            ligne.append(point)
    return ligne + [q]


def ecart_a_la_corde(ligne) -> float:
    """La plus grande distance d'un sommet de la ligne au segment de ses deux bouts, en mètres."""
    (px, py), (qx, qy) = ligne[0], ligne[-1]
    dx, dy = qx - px, qy - py
    longueur = math.sqrt(dx * dx + dy * dy)
    return max((abs(dx * (py - y) - (px - x) * dy) / longueur for x, y in ligne[1:-1]), default=0.0)


def _ligne_sure(ligne, cotes, deja, points) -> bool:
    """La ligne ne touche ni un côté ni une ligne déjà brisée hors de ses bouts, et la poche
    qu'elle ferme avec son segment ne contient aucun point (place ou sommet)."""
    morceaux = list(zip(ligne, ligne[1:]))
    for morceau in morceaux:
        boite = _boite(morceau)
        if any(_boites_se_touchent(boite, sa_boite) and se_touchent(morceau, autre) for autre, sa_boite in cotes + deja):
            return False
    poche = list(ligne) + [ligne[0]]
    return not any(_dans_anneau(x, y, poche) for x, y in points)


def _brisures(anneaux_par_cellule, couples, places) -> tuple[dict, list]:
    """Les lignes brisées de chaque couple, et les segments restés droits.

    Les couples se brisent dans l'ordre de leurs `cell_id`, puis de leurs segments. Une ligne
    se garde des côtés de la carte de ses deux cellules (côte comprise), des lignes déjà
    brisées de ces cellules, des places de leurs lieux et de leurs sommets ; quand il ne
    trouve pas de ligne sûre, le segment reste droit.
    """
    cotes = {cid: [((u, v), _boite((u, v))) for polygone in polygones for anneau in polygone
                   for u, v in zip(anneau, anneau[1:])]
             for cid, polygones in anneaux_par_cellule.items()}
    sommets = {cid: sorted({point for polygone in polygones for anneau in polygone for point in anneau})
               for cid, polygones in anneaux_par_cellule.items()}
    lieux = {cid: [(p.x_m, p.y_m) for p in places.get(cid, ())] for cid in anneaux_par_cellule}
    deja = {cid: [] for cid in anneaux_par_cellule}
    bords, droits = {}, []
    for (a, b), segments in sorted(couples.items()):
        lignes = []
        for k, (p, q) in enumerate(segments):
            boite = _boite(losange(p, q, _constantes.RAPPORT_LOSANGE))
            proches = [(cote, sa_boite) for cid in (a, b) for cote, sa_boite in cotes[cid]
                       if _cle(*cote) != (p, q) and _boites_se_touchent(boite, sa_boite)]
            brisees = [(morceau, sa_boite) for cid in (a, b) for morceau, sa_boite in deja[cid]
                       if _boites_se_touchent(boite, sa_boite)]
            points = [point for cid in (a, b) for point in lieux[cid] + sommets[cid]
                      if point not in (p, q) and _boites_se_touchent(boite, _boite([point]))]
            ligne, hauteur = [p, q], _constantes.RAPPORT_LOSANGE
            for _ in range(_constantes.ESSAIS_LOSANGE):
                essai = ligne_brisee(p, q, hauteur, f"bord-{a}-{b}-{k}", points)
                if _ligne_sure(essai, proches, brisees, points):
                    ligne = essai
                    break
                hauteur *= MOITIE
            if ecart_a_la_corde(ligne) < _constantes.ECART_MIN_BRISE_M:
                droits.append((a, b, k))
            for morceau in zip(ligne, ligne[1:]):
                for cid in (a, b):
                    deja[cid].append((morceau, _boite(morceau)))
            lignes.append(tuple(ligne))
        bords[(a, b)] = tuple(lignes)
    return bords, droits


def _contour(polygones, remplacements) -> dict:
    coordonnees = []
    for polygone in polygones:
        anneaux = []
        for anneau in polygone:
            points = [list(anneau[0])]
            for u, v in zip(anneau, anneau[1:]):
                ligne = remplacements.get(_cle(u, v))
                if ligne is None:
                    points.append(list(v))
                    continue
                suite = ligne if ligne[0] == u else ligne[::-1]
                points += [list(point) for point in suite[1:]]
            anneaux.append(points)
        coordonnees.append(anneaux)
    return {"type": "MultiPolygon", "coordinates": coordonnees}


def decouper_la_carte(carte, adjacence, places) -> Decoupe:
    """Les contours brisés de toutes les cellules de la carte figée.

    `carte` : par `cell_id`, l'enregistrement de la carte figée ; `adjacence` : ses arêtes ;
    `places` : par `cell_id`, les places des lieux (`places_du_monde`). Une arête
    `land-land` sans segment commun est refusée en nommant ses deux cellules.
    """
    anneaux = accrocher_les_sommets({cid: anneaux_arrondis(cid, carte[cid]) for cid in sorted(carte)})
    couples = segments_partages(anneaux)
    voisines = {_cle(arete["a"], arete["b"]) for arete in adjacence
                if arete.get("kind") == "land-land" and arete["a"] in carte and arete["b"] in carte}
    sans_segment = sorted(voisines - set(couples))
    if sans_segment:
        raise FormesInvalides("cell_id " + " ; ".join(f"{a} et {b}" for a, b in sans_segment)
                              + " : voisines dans l'adjacence, sans segment commun sur la carte")
    bords, droits = _brisures(anneaux, couples, places)
    remplacements = {}
    for (a, b), lignes in bords.items():
        for ligne in lignes:
            remplacements[_cle(ligne[0], ligne[-1])] = ligne
    contours = {cid: _contour(anneaux[cid], remplacements) for cid in sorted(anneaux)}
    return Decoupe(contours=contours, bords=bords, droits=tuple(droits),
                   hors_adjacence=tuple(sorted(set(couples) - voisines)))


def decoupe_du_monde(monde) -> Decoupe:
    """Le découpage de la carte d'un monde chargé, sur les places de ses lieux."""
    from sim.places import places_du_monde
    return decouper_la_carte(monde.carte, monde.adjacency, places_du_monde(monde))
