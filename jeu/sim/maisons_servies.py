"""Maisons servies : matière du tick et documents dérivés, sans écriture du monde."""

from dataclasses import dataclass

from sim.flux import _jours_de_fenetre


_CHAMPS_FLUX = ('preleve_kg', 'recu_kg', 'du_envoye_kg', 'mange_en_route_kg', 'rendu_kg')
_VECTEURS_FLUX = ('preleve', 'recu', 'du', 'mange', 'rendu')


class MaisonInconnue(KeyError):
    """Identifiant absent du registre publié."""


@dataclass(frozen=True)
class MatiereMaisons:
    """Données nécessaires aux fiches, détachées des nombres du monde vivant."""

    tick: int
    date: dict
    registre: tuple
    noms: dict
    places: dict
    tenus: dict
    parts: dict
    greniers: dict
    flux: dict
    personnes: dict
    salaires: dict


def matiere_des_maisons(monde, noms, places) -> MatiereMaisons:
    """Copie les mesures ; une seule passe sur les jours, sans recherche par maison."""
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
    noms_routes = getattr(routes, 'noms', ())
    sommes = [[0] * len(noms_routes) for _ in _CHAMPS_FLUX]
    personnes = {m.id: [0, 0] for m in registre}
    salaires = {}
    for jour in _jours_de_fenetre(monde):
        for identifiant, kilos in jour.salaires.items():
            salaires[identifiant] = salaires.get(identifiant, 0) + kilos
        for total, champ in zip(sommes, _VECTEURS_FLUX):
            for indice, kilos in enumerate(getattr(jour, champ)):
                total[indice] += kilos
        for mouvements, colonne in ((jour.partis, 0), (jour.arrives, 1)):
            for cle, nombre in mouvements.items():
                maitre = maitres.get(cle)
                if maitre is not None:
                    personnes[maitre][colonne] += nombre
    flux = dict.fromkeys(tenus, tuple(0 for _ in _CHAMPS_FLUX))
    flux.update(zip(noms_routes, zip(*sommes)))
    return MatiereMaisons(
        tick=monde.ticks_ecoules, date=monde.date_simulation, registre=registre,
        noms=noms, places=places,
        tenus={identifiant: tuple(sorted(lieux)) for identifiant, lieux in tenus.items()},
        parts=dict(monde.parts),
        greniers={identifiant: dict(panier) for identifiant, panier in monde.greniers.items()},
        flux=flux, personnes={identifiant: tuple(nombres) for identifiant, nombres in personnes.items()},
        salaires=salaires,
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
        'flux_30j': dict(zip(_CHAMPS_FLUX, matiere.flux[identifiant])) | {
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
