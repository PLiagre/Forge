"""Décisions pures et dépôts des maisons, hors du moteur et de son état."""
from copy import deepcopy
import zlib

import sim.constants as _constantes
from sim.capitales import maisons_de_l_ia
from sim.intentions import (
    ChoixDepart, IntentionRefusee, TYPE_FIXER_PART, TYPE_TRACER_ROUTE,
    _lieux_de_la_maison, recevoir_intention, verifier_base, maitre_du_bourg,
)
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


def _fenetre_pleine(monde):
    """Les ticks t−30 … t−1 sont tous notés. Un monde posé à la main se tait."""
    jours = getattr(getattr(monde, 'flux', None), 'jours', None)
    if jours is None:
        return False
    t = monde.ticks_ecoules
    debut = t - _constantes.FENETRE_FLUX_TICKS
    return all(tick in jours for tick in range(debut, t))


def _jour_de_la_part(cle, t):
    """Jour du mois dérivé de l'identifiant, sans hash salé."""
    fenetre = _constantes.FENETRE_FLUX_TICKS
    return t % fenetre == zlib.crc32(cle.encode('utf-8')) % fenetre


def _lire_part(monde, cle, lieux):
    """Habitants, mouvements et faim des lieux, en une passe par jour."""
    habitants = 0
    cles = []
    bourgs = []
    for cid, rang, _jours in lieux:
        habitants += monde.cells[cid].lieux[rang].population
        cles.append((cid, rang))
        if rang == 0 and cid not in bourgs:
            bourgs.append(cid)
    partis, arrives, affames = 0, 0, set()
    t = monde.ticks_ecoules
    for tick in range(t - _constantes.FENETRE_FLUX_TICKS, t):
        jour = monde.flux.jours[tick]
        for cle_lieu in cles:
            partis += jour.partis.get(cle_lieu, 0)
            arrives += jour.arrives.get(cle_lieu, 0)
            if cle_lieu in jour.affames:
                affames.add(cle_lieu)
    journees = 0
    for cid in bourgs:
        plan = monde.plans[cid]
        for ouvrage in (*plan.rues, *plan.parcelles, *plan.batiments):
            if ouvrage.en_chantier:
                journees += ouvrage.travail_requis - ouvrage.travail_fourni
    nourriture = _constantes.MARCHANDISE_NOURRITURE
    grenier = monde.greniers[cle].get(nourriture, 0)
    salaires = journees * _constantes.SALAIRE_JOURNEE_KG
    reserve_gens = (
        _constantes.consommation_kg_par_habitant_par_tick(nourriture)
        * (_constantes.RESERVE_VOULUE_JOURS / _constantes.TICK_DURATION_DAYS)
        * habitants * _constantes.RESERVE_VOULUE_PART_DES_HABITANTS)
    return {
        'habitants': habitants, 'partis': partis, 'arrives': arrives,
        'lieux_affames': len(affames), 'grenier_nourriture_kg': grenier,
        'reserve_gens_kg': reserve_gens, 'salaires_a_venir_kg': salaires,
        'reserve_voulue_kg': reserve_gens + salaires,
    }


def _proposition_de_part(monde, maison, cle):
    """Monte ou baisse la part, ou se tait si la borne est déjà atteinte."""
    noms = getattr(getattr(monde, 'routes_des_lieux', None), 'noms', ())
    if cle not in noms:
        return None
    lieux = _lieux_de_la_maison(monde, cle)
    if not lieux:
        return None
    lecture = _lire_part(monde, cle, lieux)
    part = monde.parts[cle]
    perte = lecture['partis'] - lecture['arrives'] >= _constantes.TAILLE_FOYER
    if perte or lecture['lieux_affames'] > 0:
        nouvelle = max(0, round(part - _constantes.IA_PAS_DE_PART, _constantes.DECIMALES_PART))
    elif lecture['grenier_nourriture_kg'] < lecture['reserve_voulue_kg']:
        nouvelle = min(_constantes.PART_MAXIMALE, round(part + _constantes.IA_PAS_DE_PART, _constantes.DECIMALES_PART))
    else:
        return None
    if nouvelle == part:
        return None
    return {
        'maison': {'sorte': maison.sorte, 'id': maison.id},
        'intention': {'type': TYPE_FIXER_PART, 'maison': cle, 'part': nouvelle},
        'raison': {'regle': 'part_sur_projets_et_gens', 'part': part, **lecture},
    }


def decider_intentions(monde, releve):
    """Propose dans l'ordre des maisons, sans écrire ni tirer d'aléa."""
    annee = _constantes.date_de_tick(monde.ticks_ecoules)['annee']
    actives = {(e['maison']['sorte'], e['maison']['id']) for e in releve
               if e['intention']['type'] == TYPE_TRACER_ROUTE
               and _constantes.date_de_tick(e['tick'])['annee'] == annee}
    choix = monde.maison_du_joueur
    if choix is None:
        choix = next((identifiant_de_seigneurie(i.identifiant) for i in monde.intentions_en_attente if isinstance(i, ChoixDepart)), None)
    pleine = _fenetre_pleine(monde)
    t = monde.ticks_ecoules
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
        if maitre_du_bourg(monde, maison.cell_id) == cle and bourg.population > 0 and faim > 0 and (maison.sorte, maison.id) not in actives:
            y = _constantes.IA_LARGEUR_ROUTE_M * len(plan.rues)
            try:
                verifier_base(monde, maison.cell_id, points=[[0, y], [_constantes.IA_LONGUEUR_ROUTE_M, y]],
                              largeur_m=_constantes.IA_LARGEUR_ROUTE_M)
            except IntentionRefusee as refus:
                if refus.__cause__ is not None:
                    raise
            else:
                propositions.append({
                    'maison': {'sorte': maison.sorte, 'id': maison.id},
                    'intention': {
                        'type': TYPE_TRACER_ROUTE, 'cell': maison.cell_id, 'maison': cle,
                        'points': [[0, y], [_constantes.IA_LONGUEUR_ROUTE_M, y]],
                        'largeur_m': _constantes.IA_LARGEUR_ROUTE_M, 'foyers': _constantes.IA_FOYERS_ROUTE},
                    'raison': _raison_de_la_route(monde, maison, cellule, bourg, plan)})
        if pleine and isinstance(cle, str) and _jour_de_la_part(cle, t):
            proposition = _proposition_de_part(monde, maison, cle)
            if proposition is not None:
                propositions.append(proposition)
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
