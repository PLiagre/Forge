"""Départs vers un lieu mieux nourri, sur une photo après la migration de famine du tick."""

from collections import defaultdict
from math import floor

import sim.constants as _constantes
from sim import engine as _engine
from sim.model import lire_stock_marchandise


def _meilleur(candidat, actuel, photo):
    """Plus forte réserve, puis plus petit couple (cell_id, rang)."""
    if candidat is None:
        return actuel
    if actuel is None:
        return candidat
    _, _, reserve_candidat = photo[candidat]
    _, _, reserve_actuel = photo[actuel]
    return (candidat if (-reserve_candidat, *candidat) < (-reserve_actuel, *actuel)
            else actuel)


def appliquer_departs(world) -> int:
    """Déplace des foyers entiers ; ni nourriture, ni dette, ni faim ne suivent."""
    nourriture = _constantes.MARCHANDISE_NOURRITURE
    ration = (_constantes.consommation_kg_par_habitant_par_tick(nourriture)
              / _constantes.TICK_DURATION_DAYS)
    photo = {}
    premiers, seconds, bourgs = {}, {}, {}
    # Chaque lieu habité fournit une seule lecture du panier.
    for cid, cell in world.cells.items():
        for lieu in cell.lieux:
            population = lieu.population
            if population <= 0:
                continue
            stock = max(0, lire_stock_marchandise(lieu, nourriture))
            reserve = (stock - lieu.dette_alimentaire_kg) / (population * ration)
            cle = (cid, lieu.rang)
            photo[cle] = (lieu, population, reserve)
            premier = premiers.get(cid)
            if _meilleur(cle, premier, photo) == cle:
                seconds[cid], premiers[cid] = premier, cle
            else:
                seconds[cid] = _meilleur(cle, seconds.get(cid), photo)
            if lieu.rang == 0:
                bourgs[cid] = cle

    voisins = {}
    for edge in world.adjacency:
        a, b = edge['a'], edge['b']
        if a not in world.cells or b not in world.cells:
            continue
        for cid, voisin in ((a, b), (b, a)):
            voisins[cid] = _meilleur(bourgs.get(voisin), voisins.get(cid), photo)

    deltas_lieux, deltas_cellules = defaultdict(int), defaultdict(int)
    total = 0
    # Les destinations et les effectifs restent ceux de la photo.
    for cle, (_, population, reserve) in photo.items():
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
        deltas_lieux[cle] -= partants
        deltas_lieux[destination] += partants
        cible_id, _ = destination
        if cible_id != cid:
            deltas_cellules[cid] -= partants
            deltas_cellules[cible_id] += partants
        total += partants

    for cle, (lieu, population, _) in photo.items():
        lieu.population = population + deltas_lieux.get(cle, 0)
    # Les métiers suivent le solde extérieur une seule fois par cellule.
    for cid in sorted(deltas_cellules):
        delta = deltas_cellules[cid]
        if delta > 0:
            _engine._ajouter_par_les_foyers(world.cells[cid], delta)
        elif delta < 0:
            _engine._retirer_par_les_foyers(world.cells[cid], -delta)
    return total
