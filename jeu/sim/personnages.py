"""Identités initiales, sans âge calculé ni effet sur les habitants."""
import copy
import datetime
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from sim.noms import noms_depuis_monde
from sim.puissances import _DATE_ATTENDUE

CHEMIN = Path(__file__).resolve().parent.parent / 'data/personnages-1400.json'
FORMATS = {'jour': (r'[0-9]{4}-[0-9]{2}-[0-9]{2}', ''),
           'mois': (r'[0-9]{4}-[0-9]{2}', '-01'), 'annee': (r'[0-9]{4}', '-01-01')}


def exiger(condition):
    if not condition:
        raise ValueError('personnages : catalogue ou liens incohérents')


def texte(valeur):
    return isinstance(valeur, str) and bool(valeur.strip())


def valider_catalogue(document, maisons):
    """Valide aussi les références hors carte ; aucune interprétation historique."""
    try:
        exiger(set(document) == {'date', 'fidelite', 'chefs'})
        exiger(document['date'] == _DATE_ATTENDUE and texte(document['fidelite']))
        lignes = document['chefs']
        exiger(isinstance(lignes, list) and bool(lignes))
        ids = [c['maison'] for c in lignes]
        exiger(len(ids) == len(set(ids)) and set(ids) == {m.id for m in maisons if m.sorte != 'plausible'})
        for c in lignes:
            exiger(set(c) == {'maison', 'nom', 'naissance', 'sources', 'lacunes'} and texte(c['maison']))
            exiger(set(c['sources']) == set(c['lacunes']) == {'identite', 'naissance'})
            exiger(c['nom'] is not None or c['naissance'] is None)
            for champ, valeur in (('identite', c['nom']), ('naissance', c['naissance'])):
                source, lacune = c['sources'][champ], c['lacunes'][champ]
                if valeur is None:
                    exiger(source is None and texte(lacune))
                    continue
                exiger(lacune is None and isinstance(source, dict) and set(source) == {'url', 'fait'})
                exiger(texte(source['fait']) and texte(source['url']))
                url = urlsplit(source['url'])
                exiger(url.scheme in {'http', 'https'} and url.hostname and not re.search(r'\s', source['url']))
                if champ == 'identite':
                    exiger(texte(valeur))
                    continue
                exiger(isinstance(valeur, dict) and set(valeur) == {'valeur', 'precision'})
                precision, date = valeur['precision'], valeur['valeur']
                exiger(texte(date) and precision in {*FORMATS, 'vers', 'intervalle'})
                if precision in FORMATS:
                    motif, suffixe = FORMATS[precision]
                    exiger(re.fullmatch(motif, date))
                    exiger(datetime.date.fromisoformat(date + suffixe) <= datetime.date.fromisoformat(_DATE_ATTENDUE))
    except (KeyError, TypeError, ValueError) as erreur:
        raise ValueError(f'personnages : catalogue invalide : {erreur}') from erreur
    return copy.deepcopy(sorted(lignes, key=lambda c: c['maison']))


def charger_catalogue(maisons, chemin=None):
    """Lecteur pur, chemin substituable pour les contre-épreuves."""
    try:
        document = json.loads(Path(chemin or CHEMIN).read_text(encoding='utf-8'))
    except (OSError, ValueError) as erreur:
        raise ValueError(f'personnages : fichier absent ou illisible : {erreur}') from erreur
    return valider_catalogue(document, maisons)


def fiche_plausible(maison, nom):
    return {'maison': maison, 'nom': nom['prenom_chef'] + ' ' + nom['nom'], 'naissance': None,
            'sources': {'identite': None, 'naissance': None},
            'lacunes': {'identite': None, 'naissance': 'Naissance inconnue du chef plausible.'}}


def _attendus(maisons, catalogue, noms):
    fiches = {c['maison']: c for c in catalogue}
    for m in sorted(maisons, key=lambda m: m.id):
        c = fiche_plausible(m.id, noms[m.id]) if m.sorte == 'plausible' else fiches[m.id]
        personne = {**copy.deepcopy(c), 'id': 'personne-' + m.id,
                    'origine': 'plausible' if m.sorte == 'plausible' else 'historique'} if c['nom'] is not None else None
        yield m.id, personne, {'personnage': personne['id'] if personne else None, 'lacune': c['lacunes']['identite']}


def valider_personnages(personnages, chefs, maisons, catalogue, noms):
    """Compare les identités et liens à leurs données initiales, motifs compris."""
    attendus = list(_attendus(maisons, catalogue, noms))
    exiger(list(personnages) == [p for _, p, _ in attendus if p is not None])
    exiger(chefs == {i: lien for i, _, lien in attendus})


def construire_personnages(monde):
    catalogue = charger_catalogue(monde.maisons)
    noms = {i: f for v in noms_depuis_monde(monde).values() for i, f in v['maisons'].items()}
    attendus = list(_attendus(monde.maisons, catalogue, noms))
    return tuple(p for _, p, _ in attendus if p is not None), {i: lien for i, _, lien in attendus}
