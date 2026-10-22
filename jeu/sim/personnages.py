"""Identités initiales, sans âge calculé ni effet sur les habitants."""
import calendar
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
AGE_MATERNEL_MIN, AGE_MATERNEL_MAX_EXCLU = 15, 46


def exiger(condition):
    if not condition:
        raise ValueError('personnages : catalogue ou liens incohérents')


def texte(valeur):
    return isinstance(valeur, str) and bool(valeur.strip())


def valider_catalogue(document, maisons):
    """Valide aussi les références hors carte ; aucune interprétation historique."""
    try:
        exiger(set(document) == {'date', 'fidelite', 'chefs', 'familles', 'liens', 'etats'})
        exiger(document['date'] == _DATE_ATTENDUE and texte(document['fidelite']))
        lignes = document['chefs']
        exiger(isinstance(lignes, list) and bool(lignes))
        ids = [c['maison'] for c in lignes]
        exiger(len(ids) == len(set(ids)) and set(ids) == {m.id for m in maisons if m.sorte != 'plausible'})
        for table in ('familles', 'liens'):
            exiger(isinstance(document[table], list) and bool(document[table]))
        for table, c in ((t, c) for t in ('chefs', 'familles', 'liens') for c in document[t]):
            familial, ajout = table != 'chefs', table != 'liens'
            champs = {'identite', 'naissance'} if ajout else set()
            champs |= {'pere', 'mere', 'conjoints', 'presence'} if familial else set()
            cles = {'sources', 'lacunes'} | ({'maison', 'nom', 'naissance'} if ajout else set())
            exiger(set(c) == cles | ({'id', 'pere', 'mere', 'conjoints', 'presence'} if familial else set()))
            if familial: exiger(c['presence'] in {'vivante', 'decedee', 'indeterminee'})
            if ajout:
                exiger(c['maison'] in {m.id for m in maisons} and texte(c['maison']))
                exiger(c['nom'] is not None or c['naissance'] is None)
                if familial: exiger(texte(c['nom']))
            exiger(set(c['sources']) == set(c['lacunes']) == champs)
            for champ in champs:
                valeur = c['nom'] if champ == 'identite' else True if champ == 'presence' else c[champ]
                valeur = None if valeur == [] else valeur
                source, lacune = c['sources'][champ], c['lacunes'][champ]
                if valeur is None:
                    exiger(source is None and texte(lacune))
                    continue
                exiger(lacune is None and isinstance(source, dict) and set(source) == {'url', 'fait'})
                exiger(texte(source['fait']) and texte(source['url']))
                url = urlsplit(source['url'])
                exiger(url.scheme in {'http', 'https'} and url.hostname and not re.search(r'\s', source['url']))
                if champ != 'naissance':
                    if champ == 'identite': exiger(texte(valeur))
                    continue
                exiger(isinstance(valeur, dict) and set(valeur) == {'valeur', 'precision'})
                precision, date = valeur['precision'], valeur['valeur']
                exiger(texte(date) and precision in {*FORMATS, 'vers', 'intervalle'})
                if precision in FORMATS:
                    motif, suffixe = FORMATS[precision]
                    exiger(re.fullmatch(motif, date))
                    exiger(datetime.date.fromisoformat(date + suffixe) <= datetime.date.fromisoformat(_DATE_ATTENDUE))
        valider_etats(document, maisons)
        _avec_familles([dict(c, id='personne-' + c['maison']) for c in lignes if c['nom']], document)
    except (KeyError, TypeError, ValueError) as erreur:
        raise ValueError(f'personnages : catalogue invalide : {erreur}') from erreur
    return copy.deepcopy({**document, **{t: sorted(document[t], key=lambda c: c[cle])
                                       for t, cle in (('chefs', 'maison'), ('familles', 'id'), ('liens', 'id'), ('etats', 'maison'))}})


def valider_etats(document, maisons):
    """Les états déclarent la couverture, pas une règle de mariage ou un héritier."""
    etats = document['etats']
    exiger(isinstance(etats, list) and bool(etats))
    exiger(len({e['maison'] for e in etats}) == len(etats))
    liens = {l['id']: l for l in document['liens']}
    for e in etats:
        exiger(set(e) == {'maison', 'conjoints', 'enfants', 'sources', 'lacunes', 'exclusions'})
        exiger(e['maison'] in {m.id for m in maisons})
        f = liens['personne-' + e['maison']]
        exiger(set(e['sources']) == set(e['lacunes']) == {'conjoints', 'enfants'})
        exiger(e['conjoints'] in {'union', 'veuvage', 'lacune'})
        exiger(e['enfants'] in {'documentes', 'absence_attestee', 'lacune'})
        exiger(bool(f['conjoints']) == (e['conjoints'] == 'union'))
        enfants = [p for p in document['familles'] if p['pere'] == f['id'] or p['mere'] == f['id']]
        exiger(e['enfants'] != 'absence_attestee' or not enfants)
        exiger(e['enfants'] != 'documentes' or bool(enfants))
        for k in ('conjoints', 'enfants'):
            source, lacune = e['sources'][k], e['lacunes'][k]
            exiger((source is None and texte(lacune)) if e[k] == 'lacune' else (lacune is None and source_valide(source)))
        exiger(isinstance(e['exclusions'], dict))
        for nom, recherche in e['exclusions'].items():
            exiger(texte(nom) and set(recherche) == {'motif', 'sources'} and texte(recherche['motif']))
            exiger(isinstance(recherche['sources'], list) and bool(recherche['sources']))
            exiger(all(source_valide(s) for s in recherche['sources']))


def source_valide(source):
    if not isinstance(source, dict) or set(source) != {'url', 'fait'}: return False
    url = urlsplit(source['url']) if texte(source['url']) else None
    return texte(source['fait']) and url is not None and url.scheme in {'http', 'https'} and bool(url.hostname) and not re.search(r'\s', source['url'])


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
    fiches = {c['maison']: c for c in catalogue['chefs']}
    for m in sorted(maisons, key=lambda m: m.id):
        c = fiche_plausible(m.id, noms[m.id]) if m.sorte == 'plausible' else fiches[m.id]
        personne = {**copy.deepcopy(c), 'id': 'personne-' + m.id,
                    'origine': 'plausible' if m.sorte == 'plausible' else 'historique'} if c['nom'] is not None else None
        yield m.id, personne, {'personnage': personne['id'] if personne else None, 'lacune': c['lacunes']['identite']}


def valider_personnages(personnages, chefs, maisons, catalogue, noms):
    """Compare les identités et liens à leurs données initiales, motifs compris."""
    attendus = list(_attendus(maisons, catalogue, noms))
    _controler_liens(personnages)
    exiger(list(personnages) == _avec_familles([p for _, p, _ in attendus if p is not None], catalogue))
    exiger(chefs == {i: lien for i, _, lien in attendus})


def construire_personnages(monde):
    catalogue = charger_catalogue(monde.maisons)
    noms = {i: f for v in noms_depuis_monde(monde).values() for i, f in v['maisons'].items()}
    attendus = list(_attendus(monde.maisons, catalogue, noms))
    return tuple(_avec_familles([p for _, p, _ in attendus if p is not None], catalogue)), {i: lien for i, _, lien in attendus}


def _controler_liens(personnes):
    # Les valeurs neutres servent au contrôle ; elles n'attestent aucune absence.
    return valider_liens_familiaux([{'pere': None, 'mere': None, 'conjoints': [], **p} for p in personnes])


def _avec_familles(personnes, catalogue):
    personnes = copy.deepcopy(personnes)
    chefs = {p['id']: p for p in personnes}
    liens = catalogue['liens']
    exiger(len({l['id'] for l in liens}) == len(liens))
    for lien in liens:
        exiger(lien['id'] in chefs)
        p = chefs[lien['id']]
        for champ in ('pere', 'mere', 'conjoints', 'presence'): p[champ] = copy.deepcopy(lien[champ])
        for champ in ('sources', 'lacunes'): p[champ].update(copy.deepcopy(lien[champ]))
    for etat in catalogue['etats']:
        chefs['personne-' + etat['maison']]['etat_familial'] = copy.deepcopy(etat)
    personnes += [dict(copy.deepcopy(f), origine='historique') for f in catalogue['familles']]
    _controler_liens(personnes)
    return sorted(personnes, key=lambda p: p['id'])


def _bornes_naissance(naissance):
    if naissance is None:
        return None
    exiger(isinstance(naissance, dict) and set(naissance) == {'valeur', 'precision'})
    valeur, precision = naissance['valeur'], naissance['precision']
    exiger(texte(valeur) and texte(precision) and precision in {*FORMATS, 'vers', 'intervalle'})
    if precision not in FORMATS:
        return None
    motif, suffixe = FORMATS[precision]
    exiger(re.fullmatch(motif, valeur))
    debut = datetime.date.fromisoformat(valeur + suffixe)
    fin = debut
    if precision == 'annee':
        fin = debut.replace(month=datetime.date.max.month, day=datetime.date.max.day)
    elif precision == 'mois':
        fin = debut.replace(day=calendar.monthrange(debut.year, debut.month)[-1])
    return debut, fin


def _age_revolu(parent, enfant):
    return enfant.year - parent.year - ((enfant.month, enfant.day) < (parent.month, parent.day))


def valider_liens_familiaux(fiches):
    """Contrôle pur d'une liste/tuple non vide de fiches, sans accès au catalogue.

    Champs requis : id textuel non vide unique, naissance (None ou valeur/precision
    au format du catalogue), pere et mere (id ou None explicite), conjoints
    (liste/tuple d'id). Les autres champs restent libres, homonymes compris.
    ValueError signale un schéma invalide, un lien incohérent ou une impossibilité
    certaine. Ni mariage des parents ni monogamie ne sont exigés.
    L'enfant doit naître strictement après chaque parent ; la mère doit avoir
    de 15 à 45 ans révolus inclus à sa naissance.
    Le bilan contient deux listes, verifies et indetermines : chaque contrôle
    chronologique porte une contrainte et les personnes (parent, enfant) ; les
    indéterminés portent aussi un motif. Aucun lien absent ne produit de contrôle.
    Les bornes calendaires sont inclusives ; vers/intervalle/None n'en donnent
    aucune. L'âge est révolu (anniversaire du 29 février au 1er mars hors bissextile).
    Chaque contrainte est évaluée sur toutes ses dates compatibles, séparément.
    Aucune fiche n'est modifiée et aucun hasard n'est consommé.
    """
    try:
        exiger(isinstance(fiches, (list, tuple)) and bool(fiches))
        exiger(all(isinstance(f, dict) and {'id', 'naissance', 'pere', 'mere', 'conjoints'} <= f.keys()
                   and texte(f['id']) for f in fiches))
        personnes = {f['id']: f for f in fiches}
        exiger(len(personnes) == len(fiches))
        parents, enfants = {}, {i: [] for i in personnes}
        for i, f in personnes.items():
            exiger(isinstance(f['conjoints'], (list, tuple)))
            liens = [f[r] for r in ('pere', 'mere') if f[r] is not None]
            exiger(all(texte(l) and l in personnes and l != i for l in liens + list(f['conjoints'])))
            exiger(len(set(liens)) == len(liens) and len(set(f['conjoints'])) == len(f['conjoints']))
            exiger(all(i in personnes[c]['conjoints'] for c in f['conjoints']))
            exiger(not f['conjoints'] or f.get('presence', 'vivante') == 'vivante')
            parents[i] = len(liens)
            for p in liens:
                enfants[p].append(i)
        libres = [i for i, nombre in parents.items() if nombre == 0]
        visites = 0
        while libres:
            visites += 1
            for enfant in enfants[libres.pop()]:
                parents[enfant] -= 1
                if parents[enfant] == 0:
                    libres.append(enfant)
        if visites != len(personnes):
            raise ValueError('cycle de filiation')
        bornes = {i: _bornes_naissance(f['naissance']) for i, f in personnes.items()}
        bilan = {'verifies': [], 'indetermines': []}
        def noter(contrainte, p, e, impossible, verifie, motif):
            controle = {'contrainte': contrainte, 'personnes': (p, e)}
            if impossible:
                raise ValueError(f'{contrainte} impossible : {p}, {e}')
            if not verifie:
                controle['motif'] = motif
            bilan['verifies' if verifie else 'indetermines'].append(controle)
        for e, f in personnes.items():
            for role in ('pere', 'mere'):
                p = f[role]
                if p is None:
                    continue
                a, b = bornes[p], bornes[e]
                connues = a is not None and b is not None
                motif = 'Bornes chevauchant une limite.' if connues else 'Naissance absente ou sans bornes exploitables.'
                noter('anteriorite', p, e, connues and b[-1] <= a[0],
                      connues and b[0] > a[-1], motif)
                if role == 'mere':
                    minimum, maximum = (_age_revolu(a[-1], b[0]), _age_revolu(a[0], b[-1])) if connues else (None, None)
                    noter('age_maternel', p, e,
                          connues and (maximum < AGE_MATERNEL_MIN or minimum >= AGE_MATERNEL_MAX_EXCLU),
                          connues and minimum >= AGE_MATERNEL_MIN and maximum < AGE_MATERNEL_MAX_EXCLU, motif)
        return bilan
    except (KeyError, TypeError, ValueError) as erreur:
        raise ValueError(f'personnages : famille invalide : {erreur}') from erreur
