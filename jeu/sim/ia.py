"""Décisions pures et dépôts des maisons, hors du moteur et de son état."""
from copy import deepcopy
import zlib

import sim.constants as _constantes
from sim.capitales import cle_du_registre, maisons_de_l_ia
from sim.chantiers import salaire_journee_kg
from sim.intentions import (
    BatirDansUneProvince, IntentionRefusee, LeverArmee, RepondreEvenement, TYPE_ASSIEGER,
    TYPE_BATIR_DANS_UNE_PROVINCE, TYPE_DECLARER_GUERRE, TYPE_DEPENSER_JAUGE, TYPE_FIXER_PART, TYPE_LEVER_ARMEE,
    TYPE_MARCHER, TYPE_OUVRIR_GRENIER, TYPE_RENVOYER_ARMEE, TYPE_REPONDRE_EVENEMENT,
    _lieux_de_la_maison, grain_libre, maison_choisie, recevoir_intention,
)

# Les trois réponses que l'IA sait lire, par leur identifiant dans `data/evenements.toml`.
CHOIX_OUVRIR_LES_GRENIERS = 'ouvrir_les_greniers'
CHOIX_LEVER_UNE_TAXE = 'lever_une_taxe_de_disette'
CHOIX_LAISSER_FAIRE = 'laisser_faire'


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
        # Le coût modifié du chantier, comme le paiera chaque bourg.
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


def _proposition_de_reponse(monde, maison, cle, regles):
    """Répond à l'événement à choix de la maison : le premier choix qui tient, avec sa raison.

    1. ouvrir les greniers si le grenier, une fois la part versée, couvre encore la réserve voulue ;
    2. sinon lever une taxe de disette si le grenier est sous la réserve et la Concorde au-dessus de son minimum ;
    3. sinon laisser faire.
    Se tait sans événement, ou si la réponse est déjà déposée. Le dépôt vérifie à son tour.
    """
    from sim import evenements, jauges
    attente = getattr(monde, 'evenements', {}).get(cle)
    noms = getattr(getattr(monde, 'routes_des_lieux', None), 'noms', ())
    deja = any(isinstance(i, RepondreEvenement) and i.maison == cle for i in monde.intentions_en_attente)
    if attente is None or cle not in noms or deja:
        return None
    definition = evenements.charger_evenements()[attente['identifiant']]
    ouvrir = definition.choix_de(CHOIX_OUVRIR_LES_GRENIERS)
    grenier = monde.greniers[cle].get(_constantes.MARCHANDISE_NOURRITURE, 0)
    reserve = _reserve_voulue(monde, _lieux_de_la_maison(monde, cle))['reserve_voulue_kg']
    concorde = regles.jauges['concorde']
    valeur = jauges.etat(monde, cle, regles)['concorde']
    raison = {'evenement': attente['identifiant'], 'ouvert': attente['ouvert'],
              'grenier_nourriture_kg': grenier, 'reserve_voulue_kg': reserve,
              'part_du_grenier': None if ouvrir is None else ouvrir.grenier}
    if ouvrir is not None and ouvrir.grenier is not None and grenier > 0 and grenier * (1 - ouvrir.grenier) >= reserve:
        choix, raison = CHOIX_OUVRIR_LES_GRENIERS, {'regle': 'grenier_au_dessus_de_sa_reserve', **raison}
    elif (definition.choix_de(CHOIX_LEVER_UNE_TAXE) is not None and grenier < reserve
          and valeur > concorde['minimum']):
        choix = CHOIX_LEVER_UNE_TAXE
        raison = {'regle': 'grenier_sous_sa_reserve', **raison, 'concorde': valeur, 'minimum': concorde['minimum']}
    elif definition.choix_de(CHOIX_LAISSER_FAIRE) is not None:
        choix = CHOIX_LAISSER_FAIRE
        raison = {'regle': 'ni_grain_ni_concorde', **raison, 'concorde': valeur, 'minimum': concorde['minimum']}
    else:
        return None
    return {
        'maison': {'sorte': maison.sorte, 'id': maison.id},
        'intention': {'type': TYPE_REPONDRE_EVENEMENT, 'maison': cle, 'choix': choix},
        'raison': raison,
    }


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


def _vise_une_autre_racine(monde, cle, par_id):
    """Le maître d'une place se prend s'il relève d'une autre racine de suzeraineté que la maison."""
    from sim import guerre
    sienne = guerre.racine(par_id, cle)
    return lambda maitre: guerre.racine(par_id, maitre) != sienne


def _place_a_prendre(monde, maison, cle, regles, par_id):
    from sim import guerre
    if maison.cell_id is None:
        return None
    return guerre.place_a_prendre(monde, cle, maison.cell_id, regles, _vise_une_autre_racine(monde, cle, par_id))


def _proposition_de_batiment(monde, maison, cle, types, guerre_=None):
    """Un bâtiment dans la cellule de sa capitale : le moulin, puis la caserne, la grange et le marché.

    Un chantier à la fois : rien tant que la maison en a un en cours ou déposé.
    Un bâtiment qui n'est ni bâti ni déposé, que le grenier paie au-delà de la
    réserve voulue, se propose pour sa raison, la première qui tient, dans cet
    ordre (le grain nourrit tout le reste). La caserne se bâtit quand une place
    est à prendre (`guerre_` : les règles de la guerre et l'index du registre).
    Un bâtiment déjà déposé en attente arrête la maison : jamais un grenier payé
    deux fois.
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
                          ('caserne', 'caserne_pour_la_guerre'),
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
        if nature == 'caserne':
            place = None if guerre_ is None else _place_a_prendre(monde, maison, cle, *guerre_)
            if place is None:
                continue
            cid_place, jours, maitre = place
            raison |= {'place': cid_place, 'jours_de_marche': jours, 'maitre_de_la_place': maitre}
        elif nature == 'grange':
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


def _proposition(maison, intention, raison):
    return {'maison': {'sorte': maison.sorte, 'id': maison.id}, 'intention': intention, 'raison': raison}


def _propositions_de_guerre(monde, maison, cle, regles, par_id):
    """Déclarer la guerre au maître de la place à prendre et lever l'armée qui la prendra, ou rien.

    La caserne achevée dans sa capitale tenue, sans armée en campagne ni levée déposée, la maison lève
    sur ses lieux de la cellule de sa capitale, chacun à sa part, autant d'hommes que son grenier en
    nourrit au-delà de sa réserve voulue, pour la marche et `ia_jours_de_siege_voulus` jours de siège ;
    jamais moins que `ia_hommes_minimum`. La levée se vérifie par la règle du dépôt.
    """
    from sim import guerre
    if any(a.maison == cle for a in monde.armees) or any(
            isinstance(i, LeverArmee) and i.maison == cle for i in monde.intentions_en_attente):
        return []
    if guerre.raison_levee_fermee(monde, cle, regles) is not None:
        return []
    place = _place_a_prendre(monde, maison, cle, regles, par_id)
    if place is None:
        return []
    cid_place, jours, maitre = place
    capitale = monde.cells[maison.cell_id]
    lieux = [(maison.cell_id, l.rang, guerre.levee_maximale(monde, maison.cell_id, l.rang, regles))
             for l in sorted(capitale.lieux, key=lambda l: l.rang) if l.maitre == cle]
    lieux = [(c, r, n) for c, r, n in lieux if n > 0]
    paysans = guerre._paysans(capitale)
    # Aucun autre geste de la maison ne prend son grain ce jour : le grain libre est celui du grenier.
    grenier = monde.greniers[cle].get(_constantes.MARCHANDISE_NOURRITURE, 0)
    if grain_libre(monde, cle) != grenier:
        return []
    reserve = _reserve_voulue(monde, _lieux_de_la_maison(monde, cle))['reserve_voulue_kg']
    par_homme = (regles.ration_kg_par_homme_par_jour * _constantes.TICK_DURATION_DAYS
                 * (jours + regles.ia_jours_de_siege_voulus))
    payes = int((grenier - reserve) // par_homme) if grenier > reserve else 0
    hommes = min(sum(n for _c, _r, n in lieux), paysans, payes)
    if hommes < regles.ia_hommes_minimum:
        return []
    levee, reste = [], hommes
    for c, r, n in lieux:
        if reste <= 0:
            break
        levee.append([c, r, min(n, reste)])
        reste -= min(n, reste)
    vivres = hommes * par_homme
    if guerre.verifier_levee(monde, cle, tuple(map(tuple, levee)), vivres, regles, grenier) is not None:
        return []
    raison = {'regle': 'guerre_a_la_place_voisine', 'cible': maitre, 'place': cid_place, 'jours_de_marche': jours,
              'habitants_de_la_place': monde.cells[cid_place].lieux[0].population, 'hommes': hommes,
              'grenier_nourriture_kg': grenier, 'reserve_voulue_kg': reserve, 'vivres_kg': vivres}
    propositions = []
    if not guerre.en_guerre(monde, cle, maitre):
        if guerre.verifier_declaration(monde, cle, maitre) is not None:
            return []
        propositions.append(_proposition(maison, {'type': TYPE_DECLARER_GUERRE, 'maison': cle, 'cible': maitre},
                                         raison))
    propositions.append(_proposition(maison, {'type': TYPE_LEVER_ARMEE, 'maison': cle, 'lieux': levee,
                                              'vivres_kg': vivres}, raison))
    return propositions


def _propositions_des_armees(monde, maison, cle, regles):
    """Chaque jour, pour chaque armée de la maison, au plus un geste : rentrer, assiéger ou marcher.

    1. la place qu'elle a prise : elle rentre (`place_prise`) ;
    2. sans vivres et endettée : elle rentre (`armee_affamee`) ;
    3. devant une place, ou en marche : elle continue ;
    4. au bourg d'un maître avec qui la maison est en guerre : elle l'assiège (`place_ennemie`) ;
    5. sinon elle marche vers la plus proche place d'un ennemi (`marche_vers_la_place`), ou rentre
       s'il n'y en a plus à portée (`sans_place_a_prendre`).
    """
    from sim import guerre
    propositions = []
    for armee in sorted((a for a in monde.armees if a.maison == cle), key=lambda a: a.identifiant):
        base = {'armee': armee.identifiant, 'cell_id': armee.cell_id, 'rang': armee.rang, 'hommes': armee.hommes,
                'vivres_kg': armee.vivres_kg, 'dette_kg': armee.dette_kg}
        renvoi = {'type': TYPE_RENVOYER_ARMEE, 'maison': cle, 'armee': armee.identifiant}
        prises = [p for p in monde.prises if p['armee'] == armee.identifiant]
        if prises:
            propositions.append(_proposition(maison, renvoi, {'regle': 'place_prise', **base,
                                                              'place': prises[-1]['cell_id']}))
            continue
        if armee.vivres_kg <= 0 and armee.dette_kg > 0:
            propositions.append(_proposition(maison, renvoi, {'regle': 'armee_affamee', **base}))
            continue
        if armee.siege is not None or armee.destination is not None:
            continue
        if guerre.verifier_siege(monde, cle, armee.identifiant) is None:
            maitre = monde.cells[armee.cell_id].lieux[0].maitre
            propositions.append(_proposition(
                maison, {'type': TYPE_ASSIEGER, 'maison': cle, 'armee': armee.identifiant},
                {'regle': 'place_ennemie', **base, 'maitre_de_la_place': maitre}))
            continue
        place = guerre.place_a_prendre(monde, cle, armee.cell_id, regles,
                                       lambda maitre: guerre.en_guerre(monde, cle, maitre))
        if place is None or guerre.verifier_marche(monde, cle, armee.identifiant, place[0], 0) is not None:
            propositions.append(_proposition(maison, renvoi, {'regle': 'sans_place_a_prendre', **base}))
            continue
        cid_place, jours, maitre = place
        propositions.append(_proposition(
            maison, {'type': TYPE_MARCHER, 'maison': cle, 'armee': armee.identifiant, 'cell': cid_place, 'rang': 0},
            {'regle': 'marche_vers_la_place', **base, 'place': cid_place, 'jours_de_marche': jours,
             'maitre_de_la_place': maitre}))
    return propositions


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
    regles = types = guerre_ = None
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
            # Les jauges, le même jour du mois, par le même chemin que le joueur.
            if regles is None:
                from sim import jauges
                regles = jauges.charger_regles()
            jauge = _proposition_de_jauge(monde, maison, cle, regles)
            if jauge is not None:
                propositions.append(jauge)
            # La réponse à son événement à choix, après le geste de jauge du jour.
            reponse = _proposition_de_reponse(monde, maison, cle, regles)
            if reponse is not None:
                propositions.append(reponse)
            # Bâtir dans sa province, par le même chemin que le joueur.
            if types is None:
                from sim import batiments
                types = batiments.charger_types()
            # Un chantier à la fois : pas de bâtiment le jour où la maison trace une
            # route ou ouvre son grenier (le grenier ne paie pas deux projets).
            if guerre_ is None:
                from sim import guerre
                guerre_ = (guerre.charger_regles(), {m.id: m for m in monde.maisons})
            batiment = None if route is not None or secours is not None else _proposition_de_batiment(
                monde, maison, cle, types, guerre_)
            if batiment is not None:
                propositions.append(batiment)
            # La guerre, par les gestes du joueur, un jour où le grenier ne paie rien d'autre.
            if route is None and secours is None and reponse is None and batiment is None:
                propositions.extend(_propositions_de_guerre(monde, maison, cle, *guerre_))
        # Les armées en campagne, chaque jour.
        if isinstance(cle, str) and getattr(monde, 'armees', None) and any(a.maison == cle for a in monde.armees):
            if guerre_ is None:
                from sim import guerre
                guerre_ = (guerre.charger_regles(), {m.id: m for m in monde.maisons})
            propositions.extend(_propositions_des_armees(monde, maison, cle, guerre_[0]))
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
