"""Maisons servies : matière du tick et documents dérivés, sans écriture du monde."""

from dataclasses import dataclass
from functools import cached_property, reduce
from operator import add

from sim.flux import _jours_de_fenetre


_CHAMPS_FLUX = ('preleve_kg', 'recu_kg', 'du_envoye_kg', 'mange_en_route_kg', 'rendu_kg')
_VECTEURS_FLUX = ('preleve', 'recu', 'du', 'mange', 'rendu')


class MaisonInconnue(KeyError):
    """Identifiant absent du registre publié."""


@dataclass(frozen=True)
class JourDesMaisons:
    """Ce qu'un jour de la fenêtre dit des maisons, copié à la publication."""

    vecteurs: tuple
    salaires: dict
    partis: dict
    arrives: dict


@dataclass(frozen=True)
class MatiereMaisons:
    """Données nécessaires aux fiches, détachées des nombres du monde vivant.

    Les sommes des trente jours se font à la lecture, sur les jours copiés à la publication : une
    publication que personne ne lit, ou dont on ne lit que la liste, ne les paie pas. Les personnes
    et les salaires se somment pour toutes les maisons à la première fiche et se gardent avec la
    matière ; les kilos se somment pour la seule maison lue."""

    tick: int
    date: dict
    registre: tuple
    noms: dict
    places: dict
    tenus: dict
    parts: dict
    greniers: dict
    jours: tuple
    maitres: dict
    routes: tuple

    @cached_property
    def _indices(self) -> dict:
        return {nom: indice for indice, nom in enumerate(self.routes)}

    def flux_de(self, identifiant) -> tuple:
        """Les kilos d'une maison sur la fenêtre, dans l'ordre de `_CHAMPS_FLUX` ; zéro sans route.

        Chaque vecteur se somme dans l'ordre des jours et depuis le même 0 entier : ni `sum` ni `fsum`
        (ils compensent leurs arrondis et ne rendent plus les mêmes octets). Un jour dont le vecteur
        est trop court pour la maison compte pour 0."""
        indice = self._indices.get(identifiant)
        if indice is None:
            return tuple(0 for _ in _CHAMPS_FLUX)
        return tuple(
            reduce(add, (jour.vecteurs[rang][indice] if indice < len(jour.vecteurs[rang]) else 0
                         for jour in self.jours), 0)
            for rang in range(len(_VECTEURS_FLUX))
        )

    @cached_property
    def _mouvements(self) -> tuple:
        personnes = {m.id: [0, 0] for m in self.registre}
        salaires = {}
        for jour in self.jours:
            for identifiant, kilos in jour.salaires.items():
                salaires[identifiant] = salaires.get(identifiant, 0) + kilos
            for mouvements, colonne in ((jour.partis, 0), (jour.arrives, 1)):
                for cle, nombre in mouvements.items():
                    maitre = self.maitres.get(cle)
                    if maitre is not None:
                        personnes[maitre][colonne] += nombre
        return {identifiant: tuple(nombres) for identifiant, nombres in personnes.items()}, salaires

    @property
    def personnes(self) -> dict:
        """Par maison : les personnes parties de ses lieux et arrivées chez elle sur la fenêtre."""
        return self._mouvements[0]

    @property
    def salaires(self) -> dict:
        """Par maison qui en a payé : les kilos de salaires sur la fenêtre."""
        return self._mouvements[1]


def matiere_des_maisons(monde, noms, places) -> MatiereMaisons:
    """Copie ce que les fiches liront ; les sommes des trente jours attendent la première fiche."""
    registre = monde.maisons
    tenus = {m.id: [] for m in registre}
    maitres = {}
    for cid, cellule in monde.cells.items():
        for lieu in cellule.lieux:
            if lieu.maitre in tenus:
                cle = (cid, lieu.rang)
                tenus[lieu.maitre].append(cle)
                maitres[cle] = lieu.maitre
    routes = getattr(monde, 'routes_des_lieux', None)
    return MatiereMaisons(
        tick=monde.ticks_ecoules, date=monde.date_simulation, registre=registre,
        noms=noms, places=places,
        tenus={identifiant: tuple(sorted(lieux)) for identifiant, lieux in tenus.items()},
        parts=dict(monde.parts),
        greniers={identifiant: dict(panier) for identifiant, panier in monde.greniers.items()},
        jours=tuple(JourDesMaisons(
            vecteurs=tuple(getattr(jour, champ)[:] for champ in _VECTEURS_FLUX),
            salaires=dict(jour.salaires), partis=dict(jour.partis), arrives=dict(jour.arrives),
        ) for jour in _jours_de_fenetre(monde)),
        maitres=maitres, routes=tuple(getattr(routes, 'noms', ())),
    )


def _nom_de_maison(matiere, maison):
    """Un nom plausible vient du bloc de sa cellule, jamais de son identifiant."""
    if maison.sorte != 'plausible':
        return maison.nom
    return matiere.noms.get(maison.cell_id, {}).get('maisons', {}).get(maison.id, {}).get('nom')


def document_de_maison(matiere, identifiant) -> dict:
    """Assemble la fiche exacte d'une maison, en déclarant les champs absents."""
    maison = next((m for m in matiere.registre if m.id == identifiant), None)
    if maison is None:
        raise MaisonInconnue(identifiant)
    absents = {}
    nom = _nom_de_maison(matiere, maison)
    if nom is None:
        absents['nom'] = f'nom de maison absent pour la cellule {maison.cell_id}'
    if maison.cell_id is None:
        siege = {'cell_id': None, 'rang': None, 'nom': maison.siege, 'point': None}
        absents['siege'] = maison.hors_carte
    else:
        nom_lieu = next(l['nom'] for l in matiere.noms[maison.cell_id]['lieux'] if l['rang'] == maison.rang)
        siege = {'cell_id': maison.cell_id, 'rang': maison.rang, 'nom': nom_lieu,
                 'point': matiere.places[maison.cell_id][maison.rang].en_document()}
    for champ, valeurs in (('part', matiere.parts), ('grenier', matiere.greniers)):
        if identifiant not in valeurs:
            absents[champ] = f'{champ} absent pour la maison {identifiant}'
    partis, arrives = matiere.personnes[identifiant]
    grenier = matiere.greniers.get(identifiant)
    return {
        'id': identifiant, 'nom': nom, 'sorte': maison.sorte, 'suzerain': maison.suzerain,
        'siege': siege,
        'lieux': [{'cell_id': cid, 'rang': rang} for cid, rang in matiere.tenus[identifiant]],
        'part': matiere.parts.get(identifiant), 'grenier': None if grenier is None else dict(grenier),
        'flux_30j': dict(zip(_CHAMPS_FLUX, matiere.flux_de(identifiant))) | {
            'partis_personnes': partis, 'arrives_personnes': arrives,
        } | ({'salaires_payes_kg': matiere.salaires[identifiant]} if identifiant in matiere.salaires else {}),
        'absents': absents, 'tick': matiere.tick, 'date': dict(matiere.date),
    }


def liste_des_maisons(matiere) -> dict:
    """Liste légère et triée du registre, sans assembler les fiches complètes."""
    return {
        'tick': matiere.tick, 'date': dict(matiere.date), 'nombre': len(matiere.registre),
        'maisons': [{
            'id': m.id, 'nom': _nom_de_maison(matiere, m), 'sorte': m.sorte, 'suzerain': m.suzerain,
            'siege': None if m.cell_id is None else {'cell_id': m.cell_id, 'rang': m.rang},
            'lieux': len(matiere.tenus[m.id]),
        } for m in sorted(matiere.registre, key=lambda m: m.id)],
    }
