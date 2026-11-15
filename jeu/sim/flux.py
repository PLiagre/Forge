"""Mémoire des circulations : des mesures, jamais une règle du monde."""

from array import array
from collections.abc import Mapping
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
    salaires: dict = field(default_factory=dict)
    affames: set = field(default_factory=set)
    commerce: dict = field(default_factory=dict)


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


def noter_affames(monde, lieux):
    """Note les lieux affamés du jour ; un appel vide ne crée aucun jour."""
    if not lieux:
        return
    jour = jour_courant(monde)
    if jour is None:
        return
    jour.affames.update(lieux)


def noter_commerce(monde, transferts):
    """Accumule les kilos passés d'une cellule à l'autre ; un appel vide ne crée aucun jour."""
    if not transferts:
        return
    jour = jour_courant(monde)
    if jour is None:
        return
    for source, receveur, kilos, _ in transferts:
        cle = (source, receveur)
        jour.commerce[cle] = jour.commerce.get(cle, 0.0) + kilos


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



class FluxDesLieux(Mapping):
    """cell_id → les mesures de chaque lieu de la cellule sur la fenêtre, par rang.

    La vue copie à sa construction les routes et, de chaque jour de la fenêtre, les parts, la table
    des récoltes et les déplacements : elle ne suit plus le monde. Les récoltes d'une cellule, elles,
    sont partagées avec le jour : le moteur pose une liste neuve par cellule et par tick, et ne la
    réécrit jamais en place. Les trente jours d'une cellule ne se somment qu'à sa première lecture,
    et la somme se garde avec la vue : une publication dont on ne lit qu'une cellule ne paie que
    celle-là."""

    def __init__(self, monde):
        self._lieux = {cid: len(cell.lieux) for cid, cell in monde.cells.items()}
        routes = getattr(getattr(monde, 'routes_des_lieux', None), 'par_cellule', {})
        self._indices = {cid: tuple(entree[0]) for cid, entree in routes.items() if cid in self._lieux}
        self._jours = tuple(
            (None if jour.taux is None or jour.recoltes is None
             else (list(jour.taux), dict(jour.recoltes)),
             dict(jour.partis), dict(jour.arrives))
            for jour in _jours_de_fenetre(monde))
        self._lus = {}

    def __getitem__(self, cell_id):
        lignes = self._lus.get(cell_id)
        if lignes is None:
            lignes = self._lus[cell_id] = self._sommer(cell_id)
        return lignes

    def __iter__(self):
        return iter(self._lieux)

    def __len__(self):
        return len(self._lieux)

    def _sommer(self, cell_id) -> list:
        """Les sommes d'une cellule, dans l'ordre des jours : le même produit part × récolte que
        `flux_de_lieu`, puis les déplacements de personnes."""
        nombre = self._lieux[cell_id]
        kilos, partis, arrives = [0.0] * nombre, [0] * nombre, [0] * nombre
        prises = [(rang, indice) for rang, indice in enumerate(self._indices.get(cell_id, ()))
                  if indice >= 0 and rang < nombre]
        for prelevement, partis_du_jour, arrives_du_jour in self._jours:
            if prelevement is not None and prises:
                taux, recoltes = prelevement
                recolte = recoltes.get(cell_id)
                if recolte is not None:
                    limite, combien = len(taux), len(recolte)
                    for rang, indice in prises:
                        if indice < limite and rang < combien:
                            kilos[rang] += taux[indice] * recolte[rang]
            for rang in range(nombre):
                cle = (cell_id, rang)
                if cle in partis_du_jour:
                    partis[rang] += partis_du_jour[cle]
                if cle in arrives_du_jour:
                    arrives[rang] += arrives_du_jour[cle]
        return [{'preleve_kg': kilos[rang], 'partis': partis[rang], 'arrives': arrives[rang]}
                for rang in range(nombre)]


def flux_des_lieux(monde) -> FluxDesLieux:
    """Les mesures de tous les lieux, lues une fois sur le monde et sommées cellule par cellule
    à leur première lecture, dans l'ordre des jours du registre."""
    return FluxDesLieux(monde)


def commerce_par_voisine(monde, cell_id) -> dict:
    """Kilos envoyés et reçus avec chaque voisine terrestre, sur la fenêtre."""
    if cell_id not in monde.cells:
        raise ValueError(f'cellule inconnue : {cell_id}')
    voisines = set()
    for arete in monde.adjacency:
        a, b = arete['a'], arete['b']
        if a == b or a not in monde.cells or b not in monde.cells:
            continue
        if a == cell_id:
            voisines.add(b)
        elif b == cell_id:
            voisines.add(a)
    resultat = {voisine: {'envoye_kg': 0.0, 'recu_kg': 0.0} for voisine in sorted(voisines)}
    for jour in _jours_de_fenetre(monde):
        for voisine, mesure in resultat.items():
            mesure['envoye_kg'] += jour.commerce.get((cell_id, voisine), 0.0)
            mesure['recu_kg'] += jour.commerce.get((voisine, cell_id), 0.0)
    return resultat
