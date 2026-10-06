"""Décisions pures et dépôts des maisons, hors du moteur et de son état."""
from copy import deepcopy

import sim.constants as _constantes
from sim.capitales import maisons_de_l_ia
from sim.intentions import ChoixDepart, TYPE_TRACER_ROUTE, recevoir_intention


def decider_intentions(monde, releve):
    """Propose dans l'ordre des maisons, sans écrire ni tirer d'aléa."""
    annee = _constantes.date_de_tick(monde.ticks_ecoules)['annee']
    actives = {(e['maison']['sorte'], e['maison']['id']) for e in releve
               if _constantes.date_de_tick(e['tick'])['annee'] == annee}
    choix = monde.maison_du_joueur
    if choix is None:
        choix = next((i.identifiant for i in monde.intentions_en_attente if isinstance(i, ChoixDepart)), None)
    propositions = []
    for maison in maisons_de_l_ia(monde):
        if maison.hors_carte is not None or (maison.sorte == 'seigneurie' and maison.id == choix):
            continue
        cellule, plan = monde.cells.get(maison.cell_id), monde.plans.get(maison.cell_id)
        bourg = next((l for l in cellule.lieux if l.rang == 0), None) if cellule is not None else None
        faim = getattr(bourg, 'duree_faim_ticks', None)
        donnee = ('cellule' if cellule is None else 'plan' if plan is None else 'bourg' if bourg is None
                  else 'faim' if isinstance(faim, bool) or not isinstance(faim, int) or faim < 0 else None)
        if donnee is not None:
            raise ValueError(f'maison {maison.sorte} {maison.id} ({maison.nom}) : {donnee} absente ou non calculée')
        if bourg.population > 0 and faim > 0 and (maison.sorte, maison.id) not in actives:
            y = _constantes.IA_LARGEUR_ROUTE_M * len(plan.rues)
            propositions.append({'maison': {'sorte': maison.sorte, 'id': maison.id}, 'intention': {
                'type': TYPE_TRACER_ROUTE, 'cell': maison.cell_id,
                'points': [[0, y], [_constantes.IA_LONGUEUR_ROUTE_M, y]],
                'largeur_m': _constantes.IA_LARGEUR_ROUTE_M, 'foyers': _constantes.IA_FOYERS_ROUTE}})
    return propositions


def jouer_ia(monde, releve):
    """Décide tout avant le premier dépôt ; relève seulement les acceptations."""
    for proposition in decider_intentions(monde, releve):
        recevoir_intention(monde, proposition['intention'])
        releve.append(deepcopy(dict(tick=monde.ticks_ecoules, **proposition)))


def maisons_actives_30j(ticks_ecoules, releve):
    """Compte les couples distincts de la première fenêtre de jours terminée."""
    if ticks_ecoules * _constantes.TICK_DURATION_DAYS < _constantes.IA_DUREE_MESURE_JOURS:
        return -1
    return len({(e['maison']['sorte'], e['maison']['id']) for e in releve
                if 0 <= e['tick'] * _constantes.TICK_DURATION_DAYS < _constantes.IA_DUREE_MESURE_JOURS})
