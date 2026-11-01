"""Programme de l'IA : calculs purs qui disent un geste et sa raison, sans rien brancher."""
import math

import sim.constants as _constantes
import sim.ia as _ia
from sim.chantiers import travail_requis_de_route
from sim.intentions import (
    IntentionRefusee, TYPE_TRACER_ROUTE, _lieux_de_la_maison, maitre_du_bourg,
    verifier_base,
)
from sim.model import contenus_des_paniers
from sim.plan import Rue
from sim.routes_interieures import _places_de, lieu_de_la_route


def _sortie(angle, demi):
    """Point du bord de la place carrée et sa direction.

    Même construction que ``ville1400._sortie``. Ce module ne l'importe pas :
    le plan de base n'admet comme importeurs que ville1400, intentions et service.
    """
    ux, uy = math.cos(angle), math.sin(angle)
    portee = max(abs(ux), abs(uy))
    distance = demi / portee
    return (distance * ux, distance * uy), (ux, uy), (-uy, ux)


def _ecarts_essayes():
    """0, +p, −p, +2p, −2p… tant que l'écart reste strictement sous le cône des routes."""
    pas = _constantes.IA_PAS_ECART_ROUTE_DEGRES
    limite = _constantes.ANGLE_ROUTE_INTERIEURE_DEGRES
    ecarts = [0]
    ecart = pas
    while ecart < limite:
        ecarts += [ecart, -ecart]
        ecart += pas
    return ecarts


def _route_deja_proposee_ce_mois(monde, maison, releve):
    """Une tracer_route de cette maison, acceptée ou refusée, date de moins d'un mois."""
    t = monde.ticks_ecoules
    couple = (maison.sorte, maison.id)
    return any(
        e['intention']['type'] == TYPE_TRACER_ROUTE
        and (e['maison']['sorte'], e['maison']['id']) == couple
        and t - e['tick'] < _constantes.FENETRE_FLUX_TICKS
        for e in releve)


def _faim_du_bourg_ticks(monde, cell_id):
    """Jours de t−30 à t−1 où le bourg (rang 0) est noté affamé."""
    t = monde.ticks_ecoules
    cle = (cell_id, 0)
    return sum(1 for tick in range(t - _constantes.FENETRE_FLUX_TICKS, t)
               if cle in monde.flux.jours[tick].affames)


def _premier_trace(monde, cell_id, places, rang):
    """Premier écart dont la route vise le champ sans toucher une maison de 1400."""
    phi = math.atan2(places[rang].y_m - places[0].y_m, places[rang].x_m - places[0].x_m)
    longueur = _constantes.IA_LONGUEUR_ROUTE_M
    largeur = _constantes.IA_LARGEUR_ROUTE_M
    for ecart in _ecarts_essayes():
        (x0, y0), (ux, uy), _ = _sortie(phi + math.radians(ecart), _constantes.DEMI_COTE_PLACE_1400_M)
        points = [[x0, y0], [x0 + ux * longueur, y0 + uy * longueur]]
        if lieu_de_la_route(Rue(0, points, largeur), places) != (rang, ""):
            continue
        try:
            verifier_base(monde, cell_id, points=points, largeur_m=largeur)
        except IntentionRefusee as refus:
            if refus.__cause__ is not None:
                raise
            continue
        return points, ecart
    return None


def proposer_route_vers_le_champ(monde, maison, releve):
    """Route du bord de la place vers le champ le plus plein, payée par le grenier, ou None."""
    if maison.hors_carte is not None:
        return None
    cell_id = maison.cell_id
    cle = _ia._cle_du_grenier(maison)
    if maitre_du_bourg(monde, cell_id) != cle:
        return None
    if _route_deja_proposee_ce_mois(monde, maison, releve):
        return None
    if not _ia._fenetre_pleine(monde):
        return None
    faim = _faim_du_bourg_ticks(monde, cell_id)
    if faim == 0:
        return None
    nourriture = _constantes.MARCHANDISE_NOURRITURE
    champs = sorted((lieu for lieu in monde.cells[cell_id].lieux if lieu.rang >= 1),
                    key=lambda lieu: lieu.rang)
    vivres = contenus_des_paniers(champs, nourriture)
    vise = None
    for indice, kg in enumerate(vivres):
        if kg > 0 and (vise is None or kg > vivres[vise]):
            vise = indice
    if vise is None:
        return None
    noms = getattr(getattr(monde, 'routes_des_lieux', None), 'noms', ())
    if cle not in noms or cle not in monde.greniers:
        return None
    grenier = monde.greniers[cle].get(nourriture, 0)
    reserve = _ia._reserve_voulue(monde, _lieux_de_la_maison(monde, cle))['reserve_voulue_kg']
    rang = champs[vise].rang
    places = _places_de(monde, cell_id)
    if places is None or rang >= len(places):
        return None
    trace = _premier_trace(monde, cell_id, places, rang)
    if trace is None:
        return None
    points, ecart = trace
    largeur = _constantes.IA_LARGEUR_ROUTE_M
    journees = travail_requis_de_route(points, largeur)
    cout = journees * _constantes.SALAIRE_JOURNEE_KG
    if not grenier > reserve + cout:
        return None
    return {
        'maison': {'sorte': maison.sorte, 'id': maison.id},
        'intention': {
            'type': TYPE_TRACER_ROUTE, 'cell': cell_id, 'maison': cle,
            'points': points, 'largeur_m': largeur, 'foyers': _constantes.IA_FOYERS_ROUTE},
        'raison': {
            'regle': 'route_vers_le_champ',
            'grenier_nourriture_kg': grenier,
            'reserve_voulue_kg': reserve,
            'journees': journees,
            'cout_kg': cout,
            'faim_du_bourg_ticks': faim,
            'champs_nourriture_kg': vivres,
            'champ_vise': rang,
            'ecart_degres': ecart,
        },
    }
