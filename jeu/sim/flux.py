"""Mémoire des circulations : des mesures, jamais une règle du monde."""

from array import array
from dataclasses import dataclass, field

import sim.constants as _constantes


@dataclass
class JourDeFlux:
    """Vecteurs par maison et références des récoltes effectivement prélevées."""
    tick: int
    preleve: array = field(default_factory=lambda: array('d'))
    recu: array = field(default_factory=lambda: array('d'))
    du: array = field(default_factory=lambda: array('d'))
    mange: array = field(default_factory=lambda: array('d'))
    rendu: array = field(default_factory=lambda: array('d'))
    taux: list | None = None
    recoltes: dict | None = None
    partis: dict = field(default_factory=dict)
    arrives: dict = field(default_factory=dict)


@dataclass
class Flux:
    """Jours observés et charge courante vers le grenier de chaque maison."""
    jours: dict[int, JourDeFlux] = field(default_factory=dict)
    en_route: array = field(default_factory=lambda: array('d'))


def jour_courant(monde):
    """Crée le jour si nécessaire ; les mondes de fortune restent sans registre."""
    registre = getattr(monde, 'flux', None)
    if registre is None:
        return None
    tick = monde.ticks_ecoules
    jour = registre.jours.get(tick)
    if jour is None:
        debut = tick + 1 - _constantes.FENETRE_FLUX_TICKS
        for ancien in list(registre.jours):
            if ancien < debut:
                del registre.jours[ancien]
        jour = registre.jours[tick] = JourDeFlux(tick)
    routes = getattr(monde, 'routes_des_lieux', None)
    nombre = len(getattr(routes, 'noms', ()))
    for vecteur in (jour.preleve, jour.recu, jour.du, jour.mange, jour.rendu, registre.en_route):
        manque = nombre - len(vecteur)
        if manque > 0:
            vecteur.extend(array('d', [0]) * manque)
    return jour


def noter_personnes(monde, partis, arrives):
    """Accumule les mouvements bruts ; un appel vide ne crée aucun jour."""
    if not partis and not arrives:
        return
    jour = jour_courant(monde)
    if jour is None:
        return
    for source, cible in ((partis, jour.partis), (arrives, jour.arrives)):
        for cle, personnes in source.items():
            cible[cle] = cible.get(cle, 0) + personnes


def _jours_de_fenetre(monde):
    """Filtre aussi à la lecture : le compteur peut avancer sans écriture."""
    debut = monde.ticks_ecoules - _constantes.FENETRE_FLUX_TICKS
    registre = getattr(monde, 'flux', None)
    return (jour for tick, jour in registre.jours.items() if tick >= debut) if registre else ()


def flux_de_maison(monde, maison) -> dict:
    """Somme des kilos observés pour une maison connue, zéro sans route."""
    if not any(fiche.id == maison for fiche in monde.maisons):
        raise ValueError(f'maison inconnue : {maison}')
    noms = getattr(getattr(monde, 'routes_des_lieux', None), 'noms', ())
    champs = {'preleve_kg': 'preleve', 'recu_kg': 'recu', 'du_envoye_kg': 'du',
              'mange_en_route_kg': 'mange', 'rendu_kg': 'rendu'}
    resultat = dict.fromkeys(champs, 0)
    if maison in noms:
        indice = noms.index(maison)
        for jour in _jours_de_fenetre(monde):
            for cle, champ in champs.items():
                vecteur = getattr(jour, champ)
                if indice < len(vecteur):
                    resultat[cle] += vecteur[indice]
    return resultat


def flux_de_lieu(monde, cell_id, rang) -> dict:
    """Relit le même produit part × récolte, puis les déplacements de personnes."""
    cellule = monde.cells.get(cell_id)
    if cellule is None or not any(lieu.rang == rang for lieu in cellule.lieux):
        raise ValueError(f'lieu inconnu : ({cell_id}, {rang})')
    resultat = {'preleve_kg': 0, 'partis': 0, 'arrives': 0}
    routes = getattr(monde, 'routes_des_lieux', None)
    entree = getattr(routes, 'par_cellule', {}).get(cell_id)
    indice = entree[0][rang] if entree and 0 <= rang < len(entree[0]) else -1
    cle = (cell_id, rang)
    for jour in _jours_de_fenetre(monde):
        if indice >= 0 and jour.taux is not None and jour.recoltes is not None:
            recolte = jour.recoltes.get(cell_id)
            if recolte is not None and indice < len(jour.taux) and rang < len(recolte):
                resultat['preleve_kg'] += jour.taux[indice] * recolte[rang]
        resultat['partis'] += jour.partis.get(cle, 0)
        resultat['arrives'] += jour.arrives.get(cle, 0)
    return resultat
