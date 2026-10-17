"""Décisions pures et dépôts des maisons, hors du moteur et de son état."""
from copy import deepcopy

import sim.constants as _constantes
from sim.capitales import maisons_de_l_ia
from sim.intentions import ChoixDepart, IntentionRefusee, TYPE_TRACER_ROUTE, recevoir_intention, verifier_base, maitre_du_bourg
from sim.model import contenus_des_paniers
from sim.seigneuries import identifiant_de_seigneurie


def _cle_du_grenier(maison):
    """Identifiant du registre : grande-<id>, ou celui d'une seigneurie."""
    if maison.sorte == 'grande maison':
        return f'grande-{maison.id}'
    if maison.sorte == 'seigneurie':
        return identifiant_de_seigneurie(maison.id)
    return None


def _raison_de_la_route(monde, maison, cellule, bourg, plan):
    """Nombres lus avant le dépôt. Une marchandise absente pèse zéro."""
    nourriture = _constantes.MARCHANDISE_NOURRITURE
    champs = sorted((lieu for lieu in cellule.lieux if lieu.rang >= 1), key=lambda lieu: lieu.rang)
    cle = _cle_du_grenier(maison)
    panier = None if cle is None else monde.greniers.get(cle)
    return {
        'regle': 'route_si_bourg_affame',
        'bourg': {
            'population': bourg.population,
            'duree_faim_ticks': bourg.duree_faim_ticks,
            'dette_alimentaire_kg': bourg.dette_alimentaire_kg,
            'nourriture_kg': contenus_des_paniers([bourg], nourriture)[0],
        },
        'champs_nourriture_kg': contenus_des_paniers(champs, nourriture),
        'grenier_nourriture_kg': -1 if panier is None else panier.get(nourriture, 0),
        'chantiers_en_cours': {
            'rues': sum(1 for rue in plan.rues if rue.en_chantier),
            'parcelles': sum(1 for parcelle in plan.parcelles if parcelle.en_chantier),
            'batiments': sum(1 for batiment in plan.batiments if batiment.en_chantier),
        },
        'departs': -1,
    }


def decider_intentions(monde, releve):
    """Propose dans l'ordre des maisons, sans écrire ni tirer d'aléa."""
    annee = _constantes.date_de_tick(monde.ticks_ecoules)['annee']
    actives = {(e['maison']['sorte'], e['maison']['id']) for e in releve
               if _constantes.date_de_tick(e['tick'])['annee'] == annee}
    choix = monde.maison_du_joueur
    if choix is None:
        choix = next((identifiant_de_seigneurie(i.identifiant) for i in monde.intentions_en_attente if isinstance(i, ChoixDepart)), None)
    propositions = []
    for maison in maisons_de_l_ia(monde):
        if maison.hors_carte is not None or (maison.sorte == 'seigneurie' and identifiant_de_seigneurie(maison.id) == choix):
            continue
        cellule, plan = monde.cells.get(maison.cell_id), monde.plans.get(maison.cell_id)
        bourg = next((l for l in cellule.lieux if l.rang == 0), None) if cellule is not None else None
        faim = getattr(bourg, 'duree_faim_ticks', None)
        donnee = ('cellule' if cellule is None else 'plan' if plan is None else 'bourg' if bourg is None
                  else 'faim' if isinstance(faim, bool) or not isinstance(faim, int) or faim < 0 else None)
        if donnee is not None:
            raise ValueError(f'maison {maison.sorte} {maison.id} ({maison.nom}) : {donnee} absente ou non calculée')
        cle = _cle_du_grenier(maison)
        if maitre_du_bourg(monde, maison.cell_id) != cle:
            continue
        if bourg.population > 0 and faim > 0 and (maison.sorte, maison.id) not in actives:
            y = _constantes.IA_LARGEUR_ROUTE_M * len(plan.rues)
            try:
                verifier_base(monde, maison.cell_id, points=[[0, y], [_constantes.IA_LONGUEUR_ROUTE_M, y]],
                              largeur_m=_constantes.IA_LARGEUR_ROUTE_M)
            except IntentionRefusee as refus:
                if refus.__cause__ is not None:
                    raise
                continue
            propositions.append({
                'maison': {'sorte': maison.sorte, 'id': maison.id},
                'intention': {
                    'type': TYPE_TRACER_ROUTE, 'cell': maison.cell_id, 'maison': cle,
                    'points': [[0, y], [_constantes.IA_LONGUEUR_ROUTE_M, y]],
                    'largeur_m': _constantes.IA_LARGEUR_ROUTE_M, 'foyers': _constantes.IA_FOYERS_ROUTE},
                'raison': _raison_de_la_route(monde, maison, cellule, bourg, plan)})
    return propositions


def jouer_ia(monde, releve):
    """Décide tout avant le premier dépôt ; note l'acceptation ou le refus."""
    for proposition in decider_intentions(monde, releve):
        try:
            recevoir_intention(monde, proposition['intention'])
        except IntentionRefusee as refus:
            releve.append(deepcopy(dict(tick=monde.ticks_ecoules, refus=str(refus), **proposition)))
        else:
            releve.append(deepcopy(dict(tick=monde.ticks_ecoules, **proposition)))


def maisons_actives_30j(ticks_ecoules, releve):
    """Compte les couples distincts déposés, refus exclus, de la première fenêtre."""
    if ticks_ecoules * _constantes.TICK_DURATION_DAYS < _constantes.IA_DUREE_MESURE_JOURS:
        return -1
    return len({(e['maison']['sorte'], e['maison']['id']) for e in releve
                if 'refus' not in e
                and 0 <= e['tick'] * _constantes.TICK_DURATION_DAYS < _constantes.IA_DUREE_MESURE_JOURS})
