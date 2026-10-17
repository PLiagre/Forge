"""Départs vers un lieu mieux nourri, sur une photo après la migration de famine du tick."""

from collections import defaultdict
from math import floor

import sim.constants as _constantes
from sim import engine as _engine
from sim import flux as _flux
from sim.model import lire_stock_marchandise


def _meilleur(candidat, actuel, photo):
    """Plus forte réserve, puis plus petit couple (cell_id, rang)."""
    if candidat is None:
        return actuel
    if actuel is None:
        return candidat
    _, _, reserve_candidat = photo[candidat]
    _, _, reserve_actuel = photo[actuel]
    if reserve_candidat > reserve_actuel:
        return candidat
    if reserve_candidat == reserve_actuel and candidat < actuel:
        return candidat
    return actuel


def appliquer_departs(world) -> int:
    """Déplace des foyers entiers ; ni nourriture, ni dette, ni faim ne suivent."""
    nourriture = _constantes.MARCHANDISE_NOURRITURE
    ration = (_constantes.consommation_kg_par_habitant_par_tick(nourriture)
              / _constantes.TICK_DURATION_DAYS)
    photo = {}
    premiers, seconds, bourgs = {}, {}, {}
    lieux_par_cellule, reserves_minimales = {}, {}
    # Chaque lieu habité fournit une seule lecture du panier.
    for cid, cell in world.cells.items():
        cles = []
        premier = second = None
        reserve_premier = reserve_second = None
        reserve_minimale = None
        for lieu in cell.lieux:
            population = lieu.population
            if population <= 0:
                continue
            stock = max(0, lire_stock_marchandise(lieu, nourriture))
            reserve = (stock - lieu.dette_alimentaire_kg) / (population * ration)
            cle = (cid, lieu.rang)
            photo[cle] = (lieu, population, reserve)
            cles.append(cle)
            if reserve_minimale is None or reserve < reserve_minimale:
                reserve_minimale = reserve
            if (premier is None or reserve > reserve_premier
                    or (reserve == reserve_premier and cle < premier)):
                second, premier = premier, cle
                reserve_second, reserve_premier = reserve_premier, reserve
            elif (second is None or reserve > reserve_second
                    or (reserve == reserve_second and cle < second)):
                second, reserve_second = cle, reserve
            if lieu.rang == 0:
                bourgs[cid] = cle
        if cles:
            lieux_par_cellule[cid] = cles
            reserves_minimales[cid] = reserve_minimale
            premiers[cid], seconds[cid] = premier, second

    voisins = {}
    for edge in world.adjacency:
        a, b = edge['a'], edge['b']
        if a not in world.cells or b not in world.cells:
            continue
        for cid, voisin in ((a, b), (b, a)):
            voisins[cid] = _meilleur(bourgs.get(voisin), voisins.get(cid), photo)

    deltas_lieux, deltas_cellules = defaultdict(int), defaultdict(int)
    total = 0
    partis, arrives = defaultdict(int), defaultdict(int)
    # Si même la meilleure destination ne dépasse pas le lieu le moins
    # nourri, aucun habitant de cette cellule ne peut partir sur cette photo.
    candidats = []
    for cid, cles in lieux_par_cellule.items():
        meilleur = _meilleur(premiers[cid], voisins.get(cid), photo)
        if photo[meilleur][-1] > reserves_minimales[cid] + _constantes.ECART_DE_DEPART_JOURS:
            candidats.extend(cles)
    # Les destinations et les effectifs restent ceux de la photo.
    for cle in candidats:
        _, population, reserve = photo[cle]
        cid, _ = cle
        destination = seconds.get(cid) if premiers[cid] == cle else premiers[cid]
        seuil = reserve + _constantes.ECART_DE_DEPART_JOURS
        if destination is None or not photo[destination][-1] > seuil:
            destination = voisins.get(cid)
        if destination is None or not photo[destination][-1] > seuil:
            continue
        ecart = photo[destination][-1] - reserve
        tranches = floor(ecart / _constantes.ECART_DE_DEPART_JOURS)
        part = (min(_constantes.TAUX_DE_DEPART * tranches, _constantes.PLAFOND_DE_DEPART)
                * _constantes.TICK_DURATION_DAYS)
        partants = floor(population * part / _constantes.TAILLE_FOYER) * _constantes.TAILLE_FOYER
        if partants:
            partis[cle] += partants
            arrives[destination] += partants
        deltas_lieux[cle] -= partants
        deltas_lieux[destination] += partants
        cible_id, _ = destination
        if cible_id != cid:
            deltas_cellules[cid] -= partants
            deltas_cellules[cible_id] += partants
        total += partants

    for cle, delta in deltas_lieux.items():
        lieu, population, _ = photo[cle]
        lieu.population = population + delta
    # Les métiers suivent le solde extérieur une seule fois par cellule.
    for cid in sorted(deltas_cellules):
        delta = deltas_cellules[cid]
        if delta > 0:
            _engine._ajouter_par_les_foyers(world.cells[cid], delta)
        elif delta < 0:
            _engine._retirer_par_les_foyers(world.cells[cid], -delta)
    _flux.noter_personnes(world, partis, arrives)
    return total
