"""Départs vers un lieu mieux nourri, sur une photo après la migration de famine du tick."""

from collections import defaultdict
from math import floor

import sim.constants as _constantes
from sim import engine as _engine
from sim import flux as _flux
from sim.model import lire_stock_marchandise


def _meilleur(candidat, actuel):
    """Plus forte réserve, puis plus petit couple (cell_id, rang)."""
    if candidat is None:
        return actuel
    if actuel is None:
        return candidat
    if candidat[-1] > actuel[-1]:
        return candidat
    if candidat[-1] == actuel[-1] and candidat[:2] < actuel[:2]:
        return candidat
    return actuel


def appliquer_departs(world) -> int:
    """Déplace des foyers entiers ; ni nourriture, ni dette, ni faim ne suivent."""
    nourriture = _constantes.MARCHANDISE_NOURRITURE
    ration = (_constantes.consommation_kg_par_habitant_par_tick(nourriture)
              / _constantes.TICK_DURATION_DAYS)
    photo = {}
    premiers, seconds, bourgs = {}, {}, {}
    reserves_minimales = {}
    # Un vecteur par cellule : pas de clé, tuple ou dictionnaire par lieu.
    # Les références aux lieux restent valides jusqu'à l'application des soldes.
    for cid, cell in world.cells.items():
        reserves = []
        premier = second = None
        reserve_minimale = None
        for indice, lieu in enumerate(cell.lieux):
            population = lieu.population
            if population <= 0:
                reserves.append(None)
                continue
            stock = lire_stock_marchandise(lieu, nourriture)
            stock = stock if stock > 0 else 0
            reserve = (stock - lieu.dette_alimentaire_kg) / (population * ration)
            reserves.append(reserve)
            if reserve_minimale is None or reserve < reserve_minimale:
                reserve_minimale = reserve
            if (premier is None or reserve > premier[-1]
                    or (reserve == premier[-1] and lieu.rang < premier[1])):
                second, premier = premier, (cid, lieu.rang, indice, reserve)
            elif (second is None or reserve > second[-1]
                    or (reserve == second[-1] and lieu.rang < second[1])):
                second = (cid, lieu.rang, indice, reserve)
            if lieu.rang == 0:
                bourgs[cid] = (cid, lieu.rang, indice, reserve)
        if premier is not None:
            photo[cid] = (cell.lieux, reserves)
            reserves_minimales[cid] = reserve_minimale
            premiers[cid], seconds[cid] = premier, second

    voisins = {}
    for edge in world.adjacency:
        a, b = edge['a'], edge['b']
        if a not in world.cells or b not in world.cells:
            continue
        for cid, voisin in ((a, b), (b, a)):
            voisins[cid] = _meilleur(bourgs.get(voisin), voisins.get(cid))

    deltas_cellules = defaultdict(int)
    total = 0
    partis, arrives = defaultdict(int), defaultdict(int)
    mouvements = {}
    for cid, (lieux, reserves) in photo.items():
        premier, second, voisin = premiers[cid], seconds[cid], voisins.get(cid)
        meilleur = _meilleur(premier, voisin)
        # Si même la meilleure destination ne dépasse pas le lieu le moins
        # nourri, aucun habitant de cette cellule ne peut partir sur cette photo.
        if not meilleur[-1] > reserves_minimales[cid] + _constantes.ECART_DE_DEPART_JOURS:
            continue
        # La clé du lieu source accompagne chaque décision, sans index global.
        sources = (((cid, lieux[indice].rang), indice, reserve)
                   for indice, reserve in enumerate(reserves) if reserve is not None)
        for cle, indice, reserve in sources:
            destination = second if premier[2] == indice else premier
            seuil = reserve + _constantes.ECART_DE_DEPART_JOURS
            if destination is None or not destination[-1] > seuil:
                destination = voisin
            if destination is None or not destination[-1] > seuil:
                continue
            ecart = destination[-1] - reserve
            tranches = floor(ecart / _constantes.ECART_DE_DEPART_JOURS)
            part = (min(_constantes.TAUX_DE_DEPART * tranches, _constantes.PLAFOND_DE_DEPART)
                    * _constantes.TICK_DURATION_DAYS)
            partants = floor(lieux[indice].population * part / _constantes.TAILLE_FOYER) * _constantes.TAILLE_FOYER
            if not partants:
                continue
            cible_id, cible_rang, cible_indice, _ = destination
            destination = (cible_id, cible_rang)
            partis[cle] += partants
            arrives[destination] += partants
            # Seuls les lieux touchés ont besoin d'un solde indexé.
            for cellule, position, delta in ((cid, indice, -partants),
                                            (cible_id, cible_indice, partants)):
                mouvements[(cellule, position)] = mouvements.get((cellule, position), 0) + delta
            if cible_id != cid:
                deltas_cellules[cid] -= partants
                deltas_cellules[cible_id] += partants
            total += partants

    for (cid, indice), delta in mouvements.items():
        lieux, _ = photo[cid]
        lieux[indice].population += delta
    # Les métiers suivent le solde extérieur une seule fois par cellule.
    for cid in sorted(deltas_cellules):
        delta = deltas_cellules[cid]
        if delta > 0:
            _engine._ajouter_par_les_foyers(world.cells[cid], delta)
        elif delta < 0:
            _engine._retirer_par_les_foyers(world.cells[cid], -delta)
    _flux.noter_personnes(world, partis, arrives)
    return total
