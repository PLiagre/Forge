"""La route de chaque lieu jusqu'au grenier de son maître.

Calculée une fois au chargement, gardée sur le monde, hors de l'empreinte.
Le tick ne la lit pas. Aucune variable de module : chaque appel relit les
constantes et ne modifie rien.

La table est rangée en tableaux d'entiers. Des milliers de `Route` vivants
ralentiraient le ramasse-miettes assez pour faire manquer au tick son budget ;
chaque `Route` n'est construite qu'à la lecture.
"""

from __future__ import annotations

import array
import dataclasses
import heapq
import math
from collections.abc import Mapping

import sim.constants as _constantes
from sim.places import distance_km


class RouteInvalide(ValueError):
    """Un lieu dont le maître est inconnu, ou dont le siège est hors carte."""


@dataclasses.dataclass(frozen=True, slots=True)
class Route:
    maitre: str
    siege: tuple
    jours: int


class TableRoutes(Mapping):
    """(cell_id, rang) → Route, sans garder un objet par lieu."""

    __slots__ = (
        "cids", "rangs", "noms", "maitre_idx", "siege_cids", "siege_rangs",
        "jours", "index",
    )

    def __init__(self, entrees):
        self.cids = array.array("i")
        self.rangs = array.array("i")
        self.siege_cids = array.array("i")
        self.siege_rangs = array.array("i")
        self.jours = array.array("i")
        self.maitre_idx = array.array("i")
        self.noms: list[str] = []
        self.index = None
        connu: dict[str, int] = {}
        for cid, rang, maitre, siege_cid, siege_rang, jours in entrees:
            indice = connu.get(maitre)
            if indice is None:
                indice = len(self.noms)
                connu[maitre] = indice
                self.noms.append(maitre)
            self.cids.append(cid)
            self.rangs.append(rang)
            self.maitre_idx.append(indice)
            self.siege_cids.append(siege_cid)
            self.siege_rangs.append(siege_rang)
            self.jours.append(jours)

    def __deepcopy__(self, memo):
        copie = TableRoutes.__new__(TableRoutes)
        memo[id(self)] = copie
        copie.cids = array.array("i", self.cids)
        copie.rangs = array.array("i", self.rangs)
        copie.siege_cids = array.array("i", self.siege_cids)
        copie.siege_rangs = array.array("i", self.siege_rangs)
        copie.jours = array.array("i", self.jours)
        copie.maitre_idx = array.array("i", self.maitre_idx)
        copie.noms = list(self.noms)
        copie.index = None
        return copie

    def __len__(self):
        return len(self.jours)

    def __iter__(self):
        for i in range(len(self.jours)):
            yield self.cids[i], self.rangs[i]

    def __getitem__(self, cle):
        if self.index is None:
            self.index = {
                (self.cids[i], self.rangs[i]): i for i in range(len(self.jours))
            }
        i = self.index[cle]
        return Route(
            self.noms[self.maitre_idx[i]],
            (self.siege_cids[i], self.siege_rangs[i]),
            self.jours[i],
        )

    def __eq__(self, autre):
        if isinstance(autre, TableRoutes):
            return (
                self.cids == autre.cids and self.rangs == autre.rangs
                and self.jours == autre.jours and self.noms == autre.noms
                and self.maitre_idx == autre.maitre_idx
                and self.siege_cids == autre.siege_cids
                and self.siege_rangs == autre.siege_rangs
            )
        if isinstance(autre, Mapping):
            if len(self) != len(autre):
                return False
            for cle in self:
                try:
                    if self[cle] != autre[cle]:
                        return False
                except KeyError:
                    return False
            return True
        return NotImplemented


def routes_des_lieux(monde, places) -> TableRoutes:
    """(cell_id, rang) → route vers le siège du maître. Pure, sans aléa."""
    maisons = {maison.id: maison for maison in monde.maisons}
    entrees = []
    hors_cellule = []
    for cid, cellule in sorted(monde.cells.items()):
        for lieu in sorted(cellule.lieux, key=lambda candidat: candidat.rang):
            if lieu.maitre is None:
                continue
            maison = maisons.get(lieu.maitre)
            if maison is None or maison.cell_id is None:
                raison = "absent du registre" if maison is None else "siège hors carte"
                raise RouteInvalide(
                    f"lieu ({cid}, {lieu.rang}) : maître {lieu.maitre!r} {raison}"
                )
            if maison.cell_id == cid:
                entrees.append((
                    cid, lieu.rang, lieu.maitre, maison.cell_id, maison.rang,
                    _jours(_distance_dans_la_cellule(places, cid, lieu.rang, maison.rang)),
                ))
            else:
                hors_cellule.append((cid, lieu.rang, lieu.maitre, maison.cell_id, maison.rang))
    if hors_cellule:
        atteints = {
            origine: _plus_court(monde, origine)
            for origine in sorted({siege_cid for _, _, _, siege_cid, _ in hors_cellule})
        }
        for cid, rang, maitre, siege_cid, siege_rang in hors_cellule:
            distance = atteints[siege_cid].get(cid)
            jours = _constantes.JOURS_DE_MER if distance is None else _jours(distance)
            entrees.append((cid, rang, maitre, siege_cid, siege_rang, jours))
    return TableRoutes(entrees)


def _jours(distance) -> int:
    """Au moins un jour, même quand le lieu est le siège."""
    return max(1, math.ceil(distance / _constantes.VITESSE_CONVOI_KM_PAR_JOUR))


def _distance_dans_la_cellule(places, cid, rang, rang_siege) -> float:
    try:
        lieux = places[cid]
        return distance_km(lieux[rang], lieux[rang_siege])
    except (KeyError, IndexError, TypeError) as erreur:
        raise RouteInvalide(f"lieu ({cid}, {rang}) : place absente") from erreur


def _plus_court(monde, origine) -> dict[int, float]:
    """Kilomètres freinés depuis la cellule du siège, arêtes terrestres seulement."""
    voisins = _voisins_terrestres(monde)
    dist = {origine: 0.0}
    file = [(0.0, origine)]
    while file:
        cout, noeud = heapq.heappop(file)
        if cout > dist.get(noeud, math.inf):
            continue
        for voisin in voisins.get(noeud, ()):
            nouveau = cout + _longueur_arete(monde, noeud, voisin)
            if nouveau < dist.get(voisin, math.inf):
                dist[voisin] = nouveau
                heapq.heappush(file, (nouveau, voisin))
    return dist


def _voisins_terrestres(monde) -> dict[int, tuple[int, ...]]:
    """Arêtes dont les deux bouts sont des cellules : le nœud de mer est ignoré."""
    voisins: dict[int, list[int]] = {}
    cellules = monde.cells
    for arete in monde.adjacency:
        a, b = arete["a"], arete["b"]
        if a not in cellules or b not in cellules:
            continue
        voisins.setdefault(a, []).append(b)
        voisins.setdefault(b, []).append(a)
    return {cid: tuple(sorted(set(bouts))) for cid, bouts in voisins.items()}


def _longueur_arete(monde, a, b) -> float:
    ax, ay = _centroide(monde.carte, a)
    bx, by = _centroide(monde.carte, b)
    geo = math.hypot(ax - bx, ay - by) / _constantes.metres_par_km()
    return geo / min(_facteur(monde.carte, a), _facteur(monde.carte, b))


def _centroide(carte, cid) -> tuple[float, float]:
    centre = (carte.get(cid) or {}).get("centroid") or {}
    if "x_m" not in centre or "y_m" not in centre:
        raise ValueError(f"cellule {cid} : centroïde absent")
    return centre["x_m"], centre["y_m"]


def _facteur(carte, cid) -> float:
    relief = (carte.get(cid) or {}).get("relief")
    facteurs = _constantes.facteurs_transport_par_relief()
    if relief not in facteurs:
        raise ValueError(f"cellule {cid} : relief {relief!r} inconnu")
    return facteurs[relief]
