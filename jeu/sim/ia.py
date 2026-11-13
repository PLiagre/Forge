"""Décisions pures et dépôts des maisons, hors du moteur et de son état."""
from copy import deepcopy
import zlib

import sim.constants as _constantes
from sim.capitales import cle_du_registre, maisons_de_l_ia
from sim.chantiers import salaire_journee_kg
from sim.intentions import (
    BatirDansUneProvince, IntentionRefusee, TYPE_BATIR_DANS_UNE_PROVINCE, TYPE_DEPENSER_JAUGE, TYPE_FIXER_PART,
    TYPE_OUVRIR_GRENIER,
    _lieux_de_la_maison, maison_choisie, recevoir_intention,
)


def _cle_du_grenier(maison):
    """Identifiant du registre : grande-<id>, ou celui d'une seigneurie."""
    return cle_du_registre(maison)


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


def _reserve_voulue(monde, lieux):
    """Habitants, salaires dus et réserve, sans la fenêtre des flux."""
    habitants = 0
    bourgs = []
    for cid, rang, _jours in lieux:
        habitants += monde.cells[cid].lieux[rang].population
        if rang == 0 and cid not in bourgs:
            bourgs.append(cid)
    par_bourg = {}
    for cid in bourgs:
        plan = monde.plans[cid]
        for ouvrage in (*plan.rues, *plan.parcelles, *plan.batiments):
            if ouvrage.en_chantier:
                par_bourg[cid] = par_bourg.get(cid, 0) + ouvrage.travail_requis - ouvrage.travail_fourni
    if getattr(monde, 'modificateurs', None):
        # Le coût modifié du chantier, comme le paiera chaque bourg (décision 38).
        salaires = sum(journees * salaire_journee_kg(monde, cid) for cid, journees in par_bourg.items())
    else:
        salaires = sum(par_bourg.values()) * _constantes.SALAIRE_JOURNEE_KG
    # Les bâtiments de province encore à payer par le maître de ces bourgs.
    if getattr(monde, 'batiments_de_province', None) and bourgs:
        from sim import batiments
        maitre = monde.cells[bourgs[0]].lieux[0].maitre
        salaires += sum(journees * salaire_journee_kg(monde, cid)
                        for cid, journees in batiments.journees_restantes(monde, maitre).items())
    nourriture = _constantes.MARCHANDISE_NOURRITURE
    reserve_gens = (
        _constantes.consommation_kg_par_habitant_par_tick(nourriture)
        * (_constantes.RESERVE_VOULUE_JOURS / _constantes.TICK_DURATION_DAYS)
        * habitants * _constantes.RESERVE_VOULUE_PART_DES_HABITANTS)
    return {
        'habitants': habitants,
        'reserve_gens_kg': reserve_gens,
        'salaires_a_venir_kg': salaires,
        'reserve_voulue_kg': reserve_gens + salaires,
    }


def _lire_part(monde, cle, lieux):
    """Habitants, mouvements et faim des lieux, en une passe par jour."""
    cles = [(cid, rang) for cid, rang, _jours in lieux]
    partis, arrives, affames = 0, 0, set()
    t = monde.ticks_ecoules
    for tick in range(t - _constantes.FENETRE_FLUX_TICKS, t):
        jour = monde.flux.jours[tick]
        for cle_lieu in cles:
            partis += jour.partis.get(cle_lieu, 0)
            arrives += jour.arrives.get(cle_lieu, 0)
            if cle_lieu in jour.affames:
                affames.add(cle_lieu)
    nourriture = _constantes.MARCHANDISE_NOURRITURE
    grenier = monde.greniers[cle].get(nourriture, 0)
    reserve = _reserve_voulue(monde, lieux)
    return {
        'habitants': reserve['habitants'], 'partis': partis, 'arrives': arrives,
        'lieux_affames': len(affames), 'grenier_nourriture_kg': grenier,
        'reserve_gens_kg': reserve['reserve_gens_kg'],
        'salaires_a_venir_kg': reserve['salaires_a_venir_kg'],
        'reserve_voulue_kg': reserve['reserve_voulue_kg'],
    }


def _proposition_de_secours(monde, maison, cle):
    """Ouvre le grenier pour les lieux affamés, sans descendre sous le plancher."""
    noms = getattr(getattr(monde, 'routes_des_lieux', None), 'noms', ())
    if not isinstance(cle, str) or cle not in noms:
        return None
    lieux = _lieux_de_la_maison(monde, cle)
    if not lieux:
        return None
    seuil = _constantes.FAIM_AVANT_SECOURS_JOURS
    duree = _constantes.TICK_DURATION_DAYS
    affames = []
    for cid, rang, _jours in lieux:
        lieu = monde.cells[cid].lieux[rang]
        if lieu.duree_faim_ticks * duree > seuil and lieu.dette_alimentaire_kg > 0:
            affames.append({
                'cell_id': cid,
                'rang': rang,
                'duree_faim_ticks': lieu.duree_faim_ticks,
                'dette_alimentaire_kg': lieu.dette_alimentaire_kg,
            })
    if not affames:
        return None
    affames.sort(key=lambda ligne: (ligne['cell_id'], ligne['rang']))
    panier = monde.greniers.get(cle)
    if panier is None:
        return None
    grenier = panier.get(_constantes.MARCHANDISE_NOURRITURE, 0)
    reserve = _reserve_voulue(monde, lieux)['reserve_voulue_kg']
    plancher = reserve * _constantes.PLANCHER_PART_DE_LA_RESERVE
    disponible = grenier - plancher
    if disponible <= 0:
        return None
    dette = 0
    for ligne in affames:
        dette += ligne['dette_alimentaire_kg']
    if dette <= 0:
        return None
    kg = min(disponible, dette)
    return {
        'maison': {'sorte': maison.sorte, 'id': maison.id},
        'intention': {'type': TYPE_OUVRIR_GRENIER, 'maison': cle, 'kg': kg},
        'raison': {
            'regle': 'secours_apres_faim',
            'lieux': affames,
            'grenier_nourriture_kg': grenier,
            'reserve_voulue_kg': reserve,
            'plancher_kg': plancher,
            'dette_affamee_kg': dette,
        },
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


def _payable(monde, cle, geste, regles):
    """Vrai si les points de la maison paient le geste et que sa jauge n'est pas à sa borne (le dépôt vérifie à son tour)."""
    from sim import jauges
    return jauges.verifier_geste(monde, cle, geste, regles) is None


def _proposition_de_jauge(monde, maison, cle, regles):
    """Au plus un geste de jauge par mois : la concorde d'abord, puis le droit (sim.jauges).

    « Affermir la concorde » quand elle est sous son neutre et que la Plume la paie ;
    sinon « Asseoir le droit » quand le droit est sous le seuil des données
    (`regles.ia['droit_bas']`) et que le Sceau le paie.
    """
    from sim import jauges
    valeurs = jauges.etat(monde, cle, regles)
    geste = 'affermir_la_concorde'
    if geste in regles.gestes and 'concorde' in regles.jauges:
        neutre = regles.jauges['concorde']['neutre']
        if valeurs['concorde'] < neutre and _payable(monde, cle, geste, regles):
            return {
                'maison': {'sorte': maison.sorte, 'id': maison.id},
                'intention': {'type': TYPE_DEPENSER_JAUGE, 'maison': cle, 'geste': geste},
                'raison': {'regle': 'concorde_sous_son_neutre', 'concorde': valeurs['concorde'], 'neutre': neutre,
                           'plume': valeurs['plume'], 'cout': dict(regles.gestes[geste]['cout'])},
            }
    geste = 'asseoir_le_droit'
    if geste in regles.gestes and 'droit' in regles.jauges:
        seuil = regles.ia['droit_bas']
        if valeurs['droit'] < seuil and _payable(monde, cle, geste, regles):
            return {
                'maison': {'sorte': maison.sorte, 'id': maison.id},
                'intention': {'type': TYPE_DEPENSER_JAUGE, 'maison': cle, 'geste': geste},
                'raison': {'regle': 'droit_sous_son_seuil', 'droit': valeurs['droit'], 'seuil': seuil,
                           'sceau': valeurs['sceau'], 'cout': dict(regles.gestes[geste]['cout'])},
            }
    return None


def _partis_et_arrives_30j(monde, cell_id):
    """Les foyers partis et arrivés sur la fenêtre, sommés sur tous les lieux de la cellule."""
    from sim import flux
    partis = arrives = 0
    for lieu in sorted(monde.cells[cell_id].lieux, key=lambda lieu: lieu.rang):
        mesure = flux.flux_de_lieu(monde, cell_id, lieu.rang)
        partis += mesure['partis']
        arrives += mesure['arrives']
    return partis, arrives


def _commerce_30j_kg(monde, cell_id):
    """Les kilos envoyés et reçus par les frontières terrestres de la cellule, sur la fenêtre."""
    from sim import flux
    return sum(voisine['envoye_kg'] + voisine['recu_kg']
               for voisine in flux.commerce_par_voisine(monde, cell_id).values())


def _proposition_de_batiment(monde, maison, cle, types):
    """Un bâtiment dans la cellule de sa capitale : le moulin, puis la grange, puis le marché.

    Un chantier à la fois : rien tant que la maison en a un en cours ou déposé.
    Un bâtiment qui n'est ni bâti ni déposé, que le grenier paie au-delà de la
    réserve voulue, se propose pour sa raison, la première qui tient, dans cet
    ordre (le grain nourrit tout le reste). Un bâtiment déjà déposé en
    attente arrête la maison : jamais un grenier payé deux fois.
    """
    from sim import batiments
    if maison.cell_id is None:
        return None
    if any(b.en_chantier and b.maison == cle for b in getattr(monde, 'batiments_de_province', ())):
        return None
    if any(isinstance(i, BatirDansUneProvince) and i.maison == cle for i in monde.intentions_en_attente):
        return None
    grenier = monde.greniers[cle].get(_constantes.MARCHANDISE_NOURRITURE, 0)
    reserve = None
    for nature, regle in (('moulin', 'moulin_quand_le_grenier_le_permet'),
                          ('grange', 'grange_quand_les_gens_partent'),
                          ('marche', 'marche_quand_la_province_commerce')):
        if nature not in types or batiments.verifier(monde, cle, maison.cell_id, nature, types) is not None:
            continue
        if reserve is None:
            reserve = _reserve_voulue(monde, _lieux_de_la_maison(monde, cle))['reserve_voulue_kg']
        cout = batiments.cout_kg(monde, types[nature], maison.cell_id)
        if not grenier > reserve + cout:
            continue
        raison = {'regle': regle}
        if nature == 'grange':
            partis, arrives = _partis_et_arrives_30j(monde, maison.cell_id)
            if not partis > arrives:
                continue
            raison |= {'partis_30j': partis, 'arrives_30j': arrives}
        elif nature == 'marche':
            commerce = _commerce_30j_kg(monde, maison.cell_id)
            if not commerce > 0:
                continue
            raison |= {'commerce_30j_kg': commerce}
        raison |= {'grenier_nourriture_kg': grenier, 'reserve_voulue_kg': reserve, 'cout_kg': cout}
        return {
            'maison': {'sorte': maison.sorte, 'id': maison.id},
            'intention': {'type': TYPE_BATIR_DANS_UNE_PROVINCE, 'maison': cle, 'cell': maison.cell_id,
                          'nature': nature},
            'raison': raison,
        }
    return None


def decider_intentions(monde, releve, maisons=None):
    """Propose dans l'ordre des maisons, sans écrire ni tirer d'aléa.

    `maisons` : la liste que la boucle de jeu a calculée une fois
    (`capitales.toutes_les_maisons_de_l_ia`) ; sans elle, la vue est refaite.
    La maison du joueur, ou celle qu'il vient de choisir, est écartée ici : seigneurie ou grande maison.
    """
    from sim import programme_ia
    choix = maison_choisie(monde)
    pleine = _fenetre_pleine(monde)
    t = monde.ticks_ecoules
    propositions = []
    regles = types = None
    for maison in (maisons_de_l_ia(monde) if maisons is None else maisons):
        if maison.hors_carte is not None or (choix is not None and _cle_du_grenier(maison) == choix):
            continue
        cellule, plan = monde.cells.get(maison.cell_id), monde.plans.get(maison.cell_id)
        bourg = next((l for l in cellule.lieux if l.rang == 0), None) if cellule is not None else None
        faim = getattr(bourg, 'duree_faim_ticks', None)
        donnee = ('cellule' if cellule is None else 'plan' if plan is None else 'bourg' if bourg is None
                  else 'faim' if isinstance(faim, bool) or not isinstance(faim, int) or faim < 0 else None)
        if donnee is not None:
            raise ValueError(f'maison {maison.sorte} {maison.id} ({maison.nom}) : {donnee} absente ou non calculée')
        cle = _cle_du_grenier(maison)
        route = programme_ia.proposer_route_vers_le_champ(monde, maison, releve)
        if route is not None:
            propositions.append(route)
        secours = _proposition_de_secours(monde, maison, cle)
        if secours is not None:
            propositions.append(secours)
        if pleine and isinstance(cle, str) and _jour_de_la_part(cle, t):
            proposition = _proposition_de_part(monde, maison, cle)
            if proposition is not None:
                propositions.append(proposition)
            # Les jauges, le même jour du mois, par le même chemin que le joueur (décision 38).
            if regles is None:
                from sim import jauges
                regles = jauges.charger_regles()
            jauge = _proposition_de_jauge(monde, maison, cle, regles)
            if jauge is not None:
                propositions.append(jauge)
            # Bâtir dans sa province, par le même chemin que le joueur (décision 38).
            if types is None:
                from sim import batiments
                types = batiments.charger_types()
            # Un chantier à la fois : pas de bâtiment le jour où la maison trace une
            # route ou ouvre son grenier (le grenier ne paie pas deux projets).
            batiment = None if route is not None or secours is not None else _proposition_de_batiment(
                monde, maison, cle, types)
            if batiment is not None:
                propositions.append(batiment)
    return propositions


def jouer_ia(monde, releve, maisons=None):
    """Décide tout avant le premier dépôt ; note l'acceptation ou le refus."""
    for proposition in decider_intentions(monde, releve, maisons):
        try:
            recevoir_intention(monde, proposition['intention'])
        except IntentionRefusee as refus:
            releve.append(deepcopy(dict(tick=monde.ticks_ecoules, refus=str(refus), **proposition)))
        else:
            releve.append(deepcopy(dict(tick=monde.ticks_ecoules, **proposition)))


def maisons_actives_30j(ticks_ecoules, releve):
    """Compte les couples distincts déposés, refus exclus, pendant les trente derniers jours.

    Les gestes sont notés avant le tick, avec le tick écoulé : après T jours, la fenêtre
    couvre les ticks T − D à T − 1. À D jours, elle égale la première fenêtre."""
    duree = _constantes.IA_DUREE_MESURE_JOURS
    fin = ticks_ecoules * _constantes.TICK_DURATION_DAYS
    if fin < duree:
        return -1
    return len({(e['maison']['sorte'], e['maison']['id']) for e in releve
                if 'refus' not in e
                and fin - duree <= e['tick'] * _constantes.TICK_DURATION_DAYS < fin})
