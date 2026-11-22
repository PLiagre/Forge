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
- le contour de chaque cellule s'assemble de ses côtés et de ses bords brisés ;
- chaque cellule se partage entre ses lieux : chacun reçoit la terre plus proche de sa
  place que de celle d'un autre lieu de la cellule (le diagramme des places, rogné par le
  contour), et les bords entre lieux se brisent de la même façon que ceux entre cellules.
  Les points où un bord entre lieux touche le contour sont insérés dans les côtés qu'il
  coupe, chez les deux cellules qui les partagent : l'union des lieux est exactement le
  contour servi.

Le calcul n'emploie que l'addition, la multiplication, la division, la racine et les
tirages de `random` : les mêmes bits sous Windows et sous Linux. Rien n'est stocké dans
le monde ; le tick ne lit pas ce module.
"""

from __future__ import annotations

import bisect
import dataclasses
import functools
import math
import random

import sim.constants as _constantes
from sim.villes import _dans_anneau

# Le milieu d'un segment ; géométrie, pas une règle du monde.
MOITIE = 0.5
# Un segment a deux bouts, et sépare au plus deux cellules.
BOUTS_D_UN_SEGMENT = 2
# Les facteurs de la formule du centre d'un cercle (2) et du centre d'un polygone (6).
DEUX, SIX = 2, 6
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
    segment sans arête `land-land` dans l'adjacence de la carte. `lieux` : par `cell_id`, le
    MultiPolygon de chaque lieu, par rang. `coupures` : les points où un bord entre deux
    lieux touche le contour, insérés dans ses côtés.
    """
    contours: dict
    lieux: dict
    bords: dict
    droits: tuple
    hors_adjacence: tuple
    coupures: tuple


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


def _boite_du_segment(u, v):
    (ux, uy), (vx, vy) = u, v
    return (ux if ux < vx else vx, uy if uy < vy else vy, vx if ux < vx else ux, vy if uy < vy else uy)


class _Index:
    """Des segments rangés par cases de `MAILLE_D_INDEX_M` : ceux dont la boîte touche une
    boîte donnée, dans l'ordre où ils ont été donnés."""

    def __init__(self, segments):
        self.segments = [(segment, _boite_du_segment(*segment)) for segment in segments]
        self.cases = {}
        for k, (_, boite) in enumerate(self.segments):
            for case in self._cases(boite):
                self.cases.setdefault(case, []).append(k)

    @staticmethod
    def _cases(boite):
        x_min, y_min, x_max, y_max = (int(borne // MAILLE_D_INDEX_M) for borne in boite)
        return [(x, y) for x in range(x_min, x_max + 1) for y in range(y_min, y_max + 1)]

    def strictement_dedans(self, x, y, x_max) -> bool:
        """Le point est-il à l'intérieur des anneaux rangés ici (règle pair-impair), hors de leurs bords ?"""
        dedans = False
        for ((ax, ay), (bx, by)), _ in self.autour((x, y, x_max, y)):
            produit = (x - ax) * (by - ay) - (y - ay) * (bx - ax)
            if produit == 0 and min(ax, bx) <= x <= max(ax, bx) and min(ay, by) <= y <= max(ay, by):
                return False
            if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
                dedans = not dedans
        return dedans

    def autour(self, boite) -> list:
        indices = sorted({k for case in self._cases(boite) for k in self.cases.get(case, ())})
        return [self.segments[k] for k in indices if _boites_se_touchent(boite, self.segments[k][1])]


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
        boite = _boite_du_segment(*morceau)
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
    cotes = {cid: _Index([(u, v) for polygone in polygones for anneau in polygone for u, v in zip(anneau, anneau[1:])])
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
            proches = [(cote, sa_boite) for cid in (a, b) for cote, sa_boite in cotes[cid].autour(boite)
                       if _cle(*cote) != (p, q)]
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


def _contour(polygones, remplacements) -> list:
    """Les polygones d'une cellule, chaque segment partagé remplacé par sa ligne brisée."""
    coordonnees = []
    for polygone in polygones:
        anneaux = []
        for anneau in polygone:
            points = [anneau[0]]
            for u, v in zip(anneau, anneau[1:]):
                ligne = remplacements.get(_cle(u, v))
                if ligne is None:
                    points.append(v)
                    continue
                suite = ligne if ligne[0] == u else ligne[::-1]
                points += list(suite[1:])
            anneaux.append(points)
        coordonnees.append(anneaux)
    return coordonnees


def _en_document(polygones) -> dict:
    return {"type": "MultiPolygon",
            "coordinates": [[[list(point) for point in anneau] for anneau in polygone] for polygone in polygones]}


# --- Les lieux dans leur cellule ---

# Les côtés de la boîte qui borne le diagramme des places : x minimal, y minimal, x maximal, y maximal.
OUEST, SUD, EST, NORD = "ouest", "sud", "est", "nord"
# Les indices des bornes maximales dans une boîte (x minimal, y minimal, x maximal, y maximal).
EST_INDICE, NORD_INDICE = 2, 3


def _croisement(premiere, seconde, places, boite):
    """Le point commun de deux droites du diagramme, calculé de la même façon d'où qu'on le
    demande : une médiatrice ("m", i, j), i < j, entre les places i et j, ou un côté de la
    boîte ("b", côté). Deux médiatrices se coupent au centre du cercle de leurs places,
    prises dans l'ordre de leurs rangs."""
    premiere, seconde = sorted((premiere, seconde), key=lambda droite: (droite[0] == "b", droite))
    if premiere[0] == "b":
        return (boite[0] if OUEST in (premiere[1], seconde[1]) else boite[EST_INDICE],
                boite[1] if SUD in (premiere[1], seconde[1]) else boite[NORD_INDICE])
    if seconde[0] == "b":
        _, i, j = premiere
        (xi, yi), (xj, yj) = places[i], places[j]
        mx, my, dx, dy = (xi + xj) * MOITIE, (yi + yj) * MOITIE, xj - xi, yj - yi
        if seconde[1] in (OUEST, EST):
            x = boite[0] if seconde[1] == OUEST else boite[EST_INDICE]
            return x, my - (x - mx) * dx / dy
        y = boite[1] if seconde[1] == SUD else boite[NORD_INDICE]
        return mx - (y - my) * dy / dx, y
    a, b, c = sorted(set(premiere[1:]) | set(seconde[1:]))
    (ax, ay), (bx, by), (cx, cy) = places[a], places[b], places[c]
    bx, by, cx, cy = bx - ax, by - ay, cx - ax, cy - ay
    d = (bx * cy - by * cx) * DEUX
    b2, c2 = bx * bx + by * by, cx * cx + cy * cy
    return ax + (cy * b2 - by * c2) / d, ay + (bx * c2 - cx * b2) / d


def _region(i, places, boite) -> list:
    """Les droites qui bordent la région de la place i (les points plus près d'elle que de
    toute autre), dans l'ordre du tour : la boîte rognée par chaque médiatrice."""
    droites = [("b", SUD), ("b", EST), ("b", NORD), ("b", OUEST)]
    xi, yi = places[i]
    for j in range(len(places)):
        if j == i:
            continue
        xj, yj = places[j]
        mx, my, dx, dy = (xi + xj) * MOITIE, (yi + yj) * MOITIE, xj - xi, yj - yi
        coupe = ("m", min(i, j), max(i, j))
        sommets = [_croisement(droites[k - 1], droites[k], places, boite) for k in range(len(droites))]
        dedans = [(x - mx) * dx + (y - my) * dy <= 0.0 for x, y in sommets]
        nouvelles = []
        for k in range(len(droites)):
            suivant = (k + 1) % len(droites)
            if dedans[k]:
                nouvelles.append(droites[k])
                if not dedans[suivant]:
                    nouvelles.append(coupe)
            elif dedans[suivant]:
                nouvelles.append(droites[k])
        droites = nouvelles
    return droites


def aretes_du_diagramme(places, boite) -> list:
    """Les arêtes (i, j, A, B) du diagramme des places, i < j, bouts en mètres entiers, triées."""
    aretes = set()
    for i in range(len(places)):
        droites = _region(i, places, boite)
        for k, droite in enumerate(droites):
            if droite[0] != "m":
                continue
            debut = _croisement(droites[k - 1], droite, places, boite)
            fin = _croisement(droite, droites[(k + 1) % len(droites)], places, boite)
            a, b = (round(debut[0]), round(debut[1])), (round(fin[0]), round(fin[1]))
            _, premiere, seconde = droite
            if a != b:
                aretes.add((premiere, seconde) + _cle(a, b))
    return sorted(aretes)


def _coupures(polygones, places) -> tuple[list, dict]:
    """Les bords intérieurs droits (P, Q) entre les lieux d'une cellule, et les points où ils
    coupent un côté du contour, à insérer dans ce côté : par côté (u, v), u < v, ses points."""
    boite = _boite([point for polygone in polygones for anneau in polygone for point in anneau])
    largeur, hauteur = boite[EST_INDICE] - boite[0], boite[NORD_INDICE] - boite[1]
    boite = (boite[0] - largeur, boite[1] - hauteur, boite[EST_INDICE] + largeur, boite[NORD_INDICE] + hauteur)
    cotes = _Index([(u, v) for polygone in polygones for anneau in polygone for u, v in zip(anneau, anneau[1:])])
    internes, insertions = [], {}
    for _, _, a, b in aretes_du_diagramme(places, boite):
        dx, dy = b[0] - a[0], b[1] - a[1]
        sa_boite = _boite_du_segment(a, b)
        passages = [a, b]
        for (u, v), _ in cotes.autour(sa_boite):
            o1, o2, o3, o4 = _orientation(a, b, u), _orientation(a, b, v), _orientation(u, v, a), _orientation(u, v, b)
            if o1 * o2 < 0 and o3 * o4 < 0:
                ex, ey = v[0] - u[0], v[1] - u[1]
                t = ((u[0] - a[0]) * ey - (u[1] - a[1]) * ex) / (dx * ey - dy * ex)
                point = (round(a[0] + t * dx), round(a[1] + t * dy))
                passages.append(point)
                if point not in (u, v):
                    insertions.setdefault(_cle(u, v), set()).add(point)
                continue
            for sommet, orientation in ((u, o1), (v, o2)):
                if orientation == 0 and _sur_le_segment(a, b, sommet):
                    passages.append(sommet)
            for bout, orientation in ((a, o3), (b, o4)):
                if orientation == 0 and bout not in (u, v) and _sur_le_segment(u, v, bout):
                    insertions.setdefault(_cle(u, v), set()).add(bout)
        passages = sorted(set(passages), key=lambda point: ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy, point))
        for p, q in zip(passages, passages[1:]):
            if cotes.strictement_dedans((p[0] + q[0]) * MOITIE, (p[1] + q[1]) * MOITIE, boite[EST_INDICE]):
                internes.append(_cle(p, q))
    return sorted(set(internes)), insertions


def _avec_insertions(anneau, poses) -> list:
    points = [anneau[0]]
    for u, v in zip(anneau, anneau[1:]):
        milieu = poses.get(_cle(u, v), [])
        points += (milieu if u < v else milieu[::-1]) + [v]
    return points


def _ordonner_les_insertions(insertions) -> dict:
    """Les points à insérer dans chaque côté (u, v), u < v, rangés de u vers v."""
    poses = {}
    for (u, v), points in insertions.items():
        dx, dy = v[0] - u[0], v[1] - u[1]
        poses[(u, v)] = sorted(points - {u, v}, key=lambda p: ((p[0] - u[0]) * dx + (p[1] - u[1]) * dy, p))
    return poses


def _angle_avant(a, b) -> int:
    """Ordre des directions autour d'un sommet, en tournant dans le sens trigonométrique depuis l'est."""
    moitie_a = 0 if a[1] > 0 or (a[1] == 0 and a[0] > 0) else 1
    moitie_b = 0 if b[1] > 0 or (b[1] == 0 and b[0] > 0) else 1
    if moitie_a != moitie_b:
        return moitie_a - moitie_b
    produit = a[0] * b[1] - a[1] * b[0]
    return -1 if produit > 0 else (1 if produit < 0 else 0)


def _aire_double(anneau) -> int:
    return sum(ux * vy - vx * uy for (ux, uy), (vx, vy) in zip(anneau, anneau[1:]))


def _faces(polygones, internes) -> list:
    """Les faces de terre du contour coupé par les bords intérieurs : (anneau extérieur, trous),
    anneaux fermés dans le sens de la carte (extérieur horaire, trous trigonométriques)."""
    voisins = {}
    sens_de_la_carte = set()
    for polygone in polygones:
        for anneau in polygone:
            for u, v in zip(anneau, anneau[1:]):
                sens_de_la_carte.add((u, v))
                voisins.setdefault(u, set()).add(v)
                voisins.setdefault(v, set()).add(u)
    for u, v in internes:
        voisins.setdefault(u, set()).add(v)
        voisins.setdefault(v, set()).add(u)
    autour = {}
    for sommet, autres in voisins.items():
        if len(autres) <= BOUTS_D_UN_SEGMENT:
            autour[sommet] = sorted(autres)
            continue
        cle = functools.cmp_to_key(lambda p, q: _angle_avant((p[0] - sommet[0], p[1] - sommet[1]),
                                                            (q[0] - sommet[0], q[1] - sommet[1])))
        autour[sommet] = sorted(autres, key=cle)
    rang_autour = {sommet: {autre: k for k, autre in enumerate(autres)} for sommet, autres in autour.items()}
    vues, bornees, bords_de_composante = set(), [], []
    for depart in sorted((u, v) for u in voisins for v in voisins[u]):
        if depart in vues:
            continue
        anneau, (u, v) = [depart[0]], depart
        while (u, v) not in vues:
            vues.add((u, v))
            anneau.append(v)
            liste = autour[v]
            w = liste[rang_autour[v][u] - 1]
            u, v = v, w
        aire = _aire_double(anneau)
        (bornees if aire > 0 else bords_de_composante).append(anneau)
    terres = []
    for anneau in bornees:
        cotes = list(zip(anneau, anneau[1:]))
        a_l_endroit = any(cote in sens_de_la_carte for cote in cotes)
        a_l_envers = any(cote[::-1] in sens_de_la_carte for cote in cotes)
        if a_l_endroit and a_l_envers:
            raise FormesInvalides(f"une face touche la côte des deux côtés près de {anneau[0]}")
        terres.append((anneau, not a_l_endroit))
    faces = [(anneau[::-1], []) for anneau, terre in terres if terre]
    sommets_des_faces = [set(anneau) for anneau, _ in terres]
    for bord in bords_de_composante:
        sommets_du_bord = set(bord)
        hotes = [(_aire_double(anneau), anneau, terre) for (anneau, terre), sommets in zip(terres, sommets_des_faces)
                 if sommets_du_bord.isdisjoint(sommets) and _dans_anneau(*bord[0], anneau) == 1]
        if hotes:
            _, hote, terre = min(hotes)
            if terre:
                next(trous for exterieur, trous in faces if exterieur == hote[::-1]).append(bord[::-1])
    return faces


def _centre(anneau) -> tuple:
    aire = _aire_double(anneau)
    x = sum((ux + vx) * (ux * vy - vx * uy) for (ux, uy), (vx, vy) in zip(anneau, anneau[1:]))
    y = sum((uy + vy) * (ux * vy - vx * uy) for (ux, uy), (vx, vy) in zip(anneau, anneau[1:]))
    return x / (aire * SIX / DEUX), y / (aire * SIX / DEUX)


def _lieux_de_la_cellule(cid, polygones, internes, places) -> tuple:
    """Les polygones de chaque lieu, par rang, une fois les bords intérieurs brisés."""
    if len(places) <= 1:
        return (polygones,) * len(places)
    noeuds = sorted({point for polygone in polygones for anneau in polygone for point in anneau}
                    | {point for interne in internes for point in interne})
    cotes = _Index([(u, v) for polygone in polygones for anneau in polygone for u, v in zip(anneau, anneau[1:])])
    traces = {interne: ([(interne, _boite_du_segment(*interne))], _boite_du_segment(*interne)) for interne in internes}
    lignes = {}
    for p, q in internes:
        boite = _boite(losange(p, q, _constantes.RAPPORT_LOSANGE))
        x_min, y_min, x_max, y_max = boite
        proches = cotes.autour(boite)
        autres = [(morceau, b) for autre, (morceaux, toute) in traces.items()
                  if autre != (p, q) and _boites_se_touchent(boite, toute)
                  for morceau, b in morceaux if _boites_se_touchent(boite, b)]
        debut, fin = bisect.bisect_left(noeuds, (x_min,)), bisect.bisect_right(noeuds, (x_max, math.inf))
        points = [point for point in list(places) + noeuds[debut:fin]
                  if point not in (p, q) and x_min <= point[0] <= x_max and y_min <= point[1] <= y_max]
        ligne, hauteur = (p, q), _constantes.RAPPORT_LOSANGE
        for _ in range(_constantes.ESSAIS_LOSANGE):
            essai = ligne_brisee(p, q, hauteur, f"lieu-{cid}-{p[0]}-{p[1]}-{q[0]}-{q[1]}", points)
            if _ligne_sure(essai, proches, autres, points):
                ligne = tuple(essai)
                break
            hauteur *= MOITIE
        lignes[(p, q)] = ligne
        morceaux = [(morceau, _boite_du_segment(*morceau)) for morceau in zip(ligne, ligne[1:])]
        traces[(p, q)] = (morceaux, _boite(ligne))
    par_rang = [[] for _ in places]
    for exterieur, trous in _faces(polygones, internes):
        cx, cy = _centre(exterieur)
        rang = min(range(len(places)), key=lambda r: ((places[r][0] - cx) * (places[r][0] - cx)
                                                     + (places[r][1] - cy) * (places[r][1] - cy), r))
        par_rang[rang] += _polygones_simples(_avec_lignes(exterieur, lignes), [_avec_lignes(trou, lignes) for trou in trous])
    for rang, morceaux in enumerate(par_rang):
        if not morceaux:
            raise FormesInvalides(f"cell_id {cid} : le lieu {rang} ne reçoit aucune terre")
    return tuple(sorted(morceaux) for morceaux in par_rang)


def _boucles(anneau) -> list:
    """Un anneau fermé qui repasse par un sommet, coupé en anneaux simples à ce sommet."""
    boucles, pile, place = [], [], {}
    for point in anneau[:-1]:
        if point in place:
            debut = place[point]
            boucles.append(pile[debut:] + [point])
            for retire in pile[debut + 1:]:
                del place[retire]
            del pile[debut + 1:]
            continue
        place[point] = len(pile)
        pile.append(point)
    return boucles + [pile + pile[:1]]


def _polygones_simples(exterieur, trous) -> list:
    """Les polygones d'une face, chaque anneau simple : une face qui se touche en un sommet se
    sépare en ses lobes (anneaux horaires) et ses trous accolés (anneaux trigonométriques)."""
    lobes, poches = [], []
    for anneau in [exterieur] + trous:
        for boucle in _boucles(anneau):
            (lobes if _aire_double(boucle) < 0 else poches).append(boucle)
    if len(lobes) == 1:
        return [[lobes[0]] + poches]
    polygones = [[lobe] for lobe in lobes]
    for poche in poches:
        hotes = [(-_aire_double(lobe), k) for k, lobe in enumerate(lobes)
                 if any(point not in lobe and _dans_anneau(*point, lobe) == 1 for point in poche)]
        if not hotes:
            raise FormesInvalides(f"un trou de lieu près de {poche[0]} n'est dans aucun de ses lobes")
        polygones[min(hotes)[1]].append(poche)
    return polygones


def _avec_lignes(anneau, lignes) -> list:
    points = [anneau[0]]
    for u, v in zip(anneau, anneau[1:]):
        ligne = lignes.get(_cle(u, v))
        if ligne is None:
            points.append(v)
        else:
            points += list((ligne if ligne[0] == u else ligne[::-1])[1:])
    return points


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
    points_des_places = {cid: [(p.x_m, p.y_m) for p in places.get(cid, ())] for cid in contours}
    internes, insertions = {}, {}
    for cid in sorted(contours):
        internes[cid] = []
        if len(points_des_places[cid]) > 1:
            internes[cid], a_inserer = _coupures(contours[cid], points_des_places[cid])
            for cote, points in a_inserer.items():
                insertions.setdefault(cote, set()).update(points)
    poses = _ordonner_les_insertions(insertions)
    contours = {cid: [[_avec_insertions(anneau, poses) for anneau in polygone] for polygone in polygones]
                for cid, polygones in contours.items()}
    bords = {couple: tuple(tuple(_avec_insertions(ligne, poses)) for ligne in lignes) for couple, lignes in bords.items()}
    lieux = {cid: tuple(_en_document(morceaux) for morceaux in
                        _lieux_de_la_cellule(cid, contours[cid], internes[cid], points_des_places[cid]))
             for cid in sorted(contours)}
    return Decoupe(contours={cid: _en_document(polygones) for cid, polygones in contours.items()}, lieux=lieux,
                   bords=bords, droits=tuple(droits), hors_adjacence=tuple(sorted(set(couples) - voisines)),
                   coupures=tuple(sorted({point for points in poses.values() for point in points})))


def decoupe_du_monde(monde) -> Decoupe:
    """Le découpage de la carte d'un monde chargé, sur les places de ses lieux."""
    from sim.places import places_du_monde
    return decouper_la_carte(monde.carte, monde.adjacency, places_du_monde(monde))


# Le dernier découpage fait dans ce processus, avec ce qui l'a posé : (clé, découpage).
_DERNIER = [None, None]


def formes_du_monde(monde, places=None) -> Decoupe:
    """Le découpage d'un monde, calculé une fois par processus pour la même carte et les mêmes places.

    Les places suivent les ancres des bourgs gardées au chargement (`places_du_monde`) : une
    conquête ne les bouge pas, et le découpage n'est pas refait. `places` : celles du monde,
    déjà lues (le service les lit sous le verrou du tick et calcule hors de lui).
    """
    from sim.places import places_du_monde
    places = places_du_monde(monde) if places is None else places
    cle = (monde.carte_meta.get("version"), tuple(sorted(monde.carte)),
           tuple((cid, tuple((p.x_m, p.y_m) for p in liste)) for cid, liste in sorted(places.items())))
    if _DERNIER[0] != cle:
        _DERNIER[1] = decouper_la_carte(monde.carte, monde.adjacency, places)
        _DERNIER[0] = cle
    return _DERNIER[1]


def document_des_formes(monde, places=None) -> dict:
    """Ce que sert `GET /formes` : le contour de chaque cellule et celui de chacun de ses lieux, par rang."""
    decoupe = formes_du_monde(monde, places)
    return {"crs": "EPSG:3035", "version": monde.carte_meta.get("version"),
            "cells": [{"cell_id": cid, "contour": decoupe.contours[cid],
                       "lieux": [{"rang": rang, "contour": contour} for rang, contour in enumerate(decoupe.lieux[cid])]}
                      for cid in sorted(decoupe.contours)]}
