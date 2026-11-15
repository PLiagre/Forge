"""Départs vers un lieu mieux nourri, sur une photo après la migration de famine du tick."""

from collections import defaultdict
from math import floor
from operator import itemgetter

import sim.constants as _constantes
from sim import engine as _engine
from sim import flux as _flux
from sim.model import lire_stock_marchandise

# Une entrée de la photo : (rang, lieu, population, réserve en jours).
_RANG = itemgetter(0)
_RESERVE = itemgetter(3)


def _le_meilleur(entrees):
    """Plus forte réserve, puis plus petit rang ; None sans entrée."""
    if not entrees:
        return None
    haut = max(entrees, key=_RESERVE)
    reserve = _RESERVE(haut)
    egales = [entree for entree in entrees if _RESERVE(entree) == reserve]
    return haut if len(egales) == 1 else min(egales, key=_RANG)


def appliquer_departs(world) -> int:
    """Déplace des foyers entiers ; ni nourriture, ni dette, ni faim ne suivent."""
    nourriture = _constantes.MARCHANDISE_NOURRITURE
    ration = (_constantes.consommation_kg_par_habitant_par_tick(nourriture)
              / _constantes.TICK_DURATION_DAYS)
    lire = lire_stock_marchandise
    lieux_par_cellule, premiers, bourgs = {}, {}, {}
    # Chaque lieu habité fournit une seule lecture du panier.
    for cid, cell in world.cells.items():
        entrees = []
        for lieu in cell.lieux:
            population = lieu.population
            if population <= 0:
                continue
            stock = lire(lieu, nourriture)
            if stock < 0:
                stock = 0
            entrees.append((lieu.rang, lieu, population,
                            (stock - lieu.dette_alimentaire_kg) / (population * ration)))
        if entrees:
            lieux_par_cellule[cid] = entrees
            premiers[cid] = _le_meilleur(entrees)
            bourg = entrees[0] if entrees[0][0] == 0 else next(
                (entree for entree in entrees if entree[0] == 0), None)
            if bourg is not None:
                bourgs[cid] = bourg

    # Le bourg voisin le mieux nourri, puis le plus petit cell_id.
    voisins = {}
    reserves_voisins = {}
    for a, b, _ in _engine._topologie(world)['terrestres']:
        for cid, voisin in ((a, b), (b, a)):
            candidat = bourgs.get(voisin)
            if candidat is None:
                continue
            reserve = _RESERVE(candidat)
            actuelle = reserves_voisins.get(cid)
            if actuelle is None or reserve > actuelle or (
                    reserve == actuelle and voisin < voisins[cid]):
                voisins[cid] = voisin
                reserves_voisins[cid] = reserve

    photo = {}
    deltas_lieux, deltas_cellules = defaultdict(int), defaultdict(int)
    total = 0
    # Les départs de chaque lieu (registre des modificateurs) : sa part, multipliée
    # par son facteur, jamais plus que tous ses habitants.
    modifies = (getattr(world, 'facteurs_du_tick', None) or {}).get('departs')
    partis, arrives = defaultdict(int), defaultdict(int)
    for cid, entrees in lieux_par_cellule.items():
        premier = premiers[cid]
        meilleure = _RESERVE(premier)
        voisin = voisins.get(cid)
        if voisin is not None and reserves_voisins[cid] > meilleure:
            meilleure = reserves_voisins[cid]
        # Si même la meilleure destination ne dépasse pas le lieu le moins
        # nourri, aucun habitant de cette cellule ne peut partir sur cette photo.
        if not meilleure > _RESERVE(min(entrees, key=_RESERVE)) + _constantes.ECART_DE_DEPART_JOURS:
            continue
        second = premier
        # Les destinations et les effectifs restent ceux de la photo.
        for entree in entrees:
            rang, lieu, population, reserve = entree
            if entree is premier:
                if second is premier:
                    second = _le_meilleur([autre for autre in entrees if autre is not premier])
                cible_id, cible = cid, second
            else:
                cible_id, cible = cid, premier
            seuil = reserve + _constantes.ECART_DE_DEPART_JOURS
            if cible is None or not _RESERVE(cible) > seuil:
                cible_id, cible = voisin, bourgs.get(voisin)
            if cible is None or not _RESERVE(cible) > seuil:
                continue
            rang_arrivee, lieu_arrivee, population_arrivee, reserve_arrivee = cible
            ecart = reserve_arrivee - reserve
            tranches = floor(ecart / _constantes.ECART_DE_DEPART_JOURS)
            part = (min(_constantes.TAUX_DE_DEPART * tranches, _constantes.PLAFOND_DE_DEPART)
                    * _constantes.TICK_DURATION_DAYS)
            cle = (cid, rang)
            if modifies:
                part = min(1.0, part * modifies.get(cle, 1.0))
            partants = floor(population * part / _constantes.TAILLE_FOYER) * _constantes.TAILLE_FOYER
            if not partants:
                continue
            destination = (cible_id, rang_arrivee)
            partis[cle] += partants
            arrives[destination] += partants
            photo[cle] = (lieu, population)
            photo[destination] = (lieu_arrivee, population_arrivee)
            deltas_lieux[cle] -= partants
            deltas_lieux[destination] += partants
            if cible_id != cid:
                deltas_cellules[cid] -= partants
                deltas_cellules[cible_id] += partants
            total += partants

    for cle, delta in deltas_lieux.items():
        lieu, population = photo[cle]
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
