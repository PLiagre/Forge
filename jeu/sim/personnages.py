"""Identités initiales, sans âge calculé ni effet sur les habitants."""
import calendar
import copy
import datetime
import hashlib
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
MOIS_PAR_AN, JOURS_TIRES, COUPLE = 12, 365, 2
DEPART = datetime.date.fromisoformat(_DATE_ATTENDUE)
# Niveau 2, jamais sourcé : justifications dans MODELE.md, « Les familles plausibles ».
PARAMETRES_FAMILLES_PLAUSIBLES = {
    'graine': 1400, 'age_epoux_min': 21, 'age_chef_plausible': (25, 55), 'ecart_epouse': (2, 12),
    'age_epouse_min': 16, 'age_premier_enfant': 18, 'age_dernier_enfant': 40,
    'intervalle_mois': (24, 40), 'enfants_max': 6}


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
            if ajout:
                exiger(c['maison'] in {m.id for m in maisons} and texte(c['maison']))
                exiger(c['nom'] is not None or c['naissance'] is None)
                if familial: exiger(texte(c['nom']))
            if familial: exiger(c['presence'] in {'vivante', 'decedee', 'indeterminee'})
            exiger(set(c['sources']) == set(c['lacunes']) == champs)
            for champ in champs:
                valeur = c['nom'] if champ == 'identite' else None if champ == 'presence' and c[champ] == 'indeterminee' else c[champ]
                valeur = None if valeur == [] else valeur
                source, lacune = c['sources'][champ], c['lacunes'][champ]
                if valeur is None:
                    exiger(source is None and texte(lacune))
                    continue
                exiger(lacune is None)
                _source(source)
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
        _avec_familles([dict(c, id='personne-' + c['maison']) for c in lignes if c['nom']], document)
    except (KeyError, TypeError, ValueError) as erreur:
        raise ValueError(f'personnages : catalogue invalide : {erreur}') from erreur
    return copy.deepcopy({**document, **{t: sorted(document[t], key=lambda c: c[cle])
                                       for t, cle in (('chefs', 'maison'), ('familles', 'id'), ('liens', 'id'), ('etats', 'maison'))}})


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
    exiger(all(p.get('presence') == 'vivante' for p in personnes if p.get('conjoints')))
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
    personnes += [dict(copy.deepcopy(f), origine='historique') for f in catalogue['familles']]
    _controler_liens(personnes)
    _etats(catalogue['etats'], personnes, chefs)
    return sorted(personnes, key=lambda p: p['id'])


def _source(source):
    exiger(isinstance(source, dict) and set(source) == {'url', 'fait'})
    exiger(texte(source['fait']) and texte(source['url']))
    url = urlsplit(source['url'])
    exiger(url.scheme in {'http', 'https'} and url.hostname and not re.search(r'\s', source['url']))


def _etats(etats, personnes, chefs):
    """Couverture déclarée, contrôlée sur toutes les personnes résolues."""
    exiger(isinstance(etats, list) and bool(etats))
    exiger(len({e['maison'] for e in etats}) == len(etats))
    for e in etats:
        exiger(set(e) == {'maison', 'conjoints', 'enfants', 'sources', 'lacunes', 'exclusions'})
        chef = chefs.get('personne-' + e['maison'])
        exiger(chef is not None and set(e['sources']) == set(e['lacunes']) == {'conjoints', 'enfants'})
        for k, valeurs in (('conjoints', {'union', 'veuvage', 'lacune'}), ('enfants', {'documentes', 'absence_attestee', 'lacune'})):
            exiger(e[k] in valeurs)
            if e[k] == 'lacune': exiger(e['sources'][k] is None and texte(e['lacunes'][k]))
            else:
                exiger(e['lacunes'][k] is None)
                _source(e['sources'][k])
        exiger(isinstance(e['exclusions'], dict))
        for nom, x in e['exclusions'].items():
            exiger(texte(nom) and set(x) == {'motif', 'sources'} and texte(x['motif']))
            exiger(isinstance(x['sources'], list) and bool(x['sources']))
            for source in x['sources']: _source(source)
        conjoints = chef.get('conjoints', [])
        if e['conjoints'] == 'union': exiger(bool(conjoints))
        if e['conjoints'] == 'veuvage': exiger(not conjoints)
        enfants = any(chef['id'] in (p.get('pere'), p.get('mere')) for p in personnes)
        if e['enfants'] != 'lacune': exiger(enfants == (e['enfants'] == 'documentes'))
        chef['etat_familial'] = copy.deepcopy(e)


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


def _controler_parametres(p):
    couples = ('age_chef_plausible', 'ecart_epouse', 'intervalle_mois')
    simples = ('graine', 'age_epoux_min', 'age_epouse_min', 'age_premier_enfant', 'age_dernier_enfant', 'enfants_max')
    ok = isinstance(p, dict) and set(p) == {*couples, *simples}
    ok = ok and all(type(p[k]) is int for k in simples) and all(
        isinstance(p[k], (tuple, list)) and len(p[k]) == COUPLE and all(type(v) is int for v in p[k]) and p[k][0] <= p[k][1]
        for k in couples)
    ok = ok and AGE_MATERNEL_MIN <= p['age_premier_enfant'] <= p['age_dernier_enfant'] < AGE_MATERNEL_MAX_EXCLU
    ok = ok and min(p['intervalle_mois'][0] - 1, p['enfants_max'], p['ecart_epouse'][0], p['age_epouse_min']) >= 0
    if not (ok and p['age_chef_plausible'][0] >= p['age_epoux_min']):
        raise ValueError('familles plausibles : paramètres incohérents')


def _tirer(p, chef, role, intervalle):
    """Entier de l'empreinte de (graine, chef, rôle), ramené dans l'intervalle inclus."""
    empreinte = hashlib.sha256(f"{p['graine']}|{chef}|{role}".encode()).digest()
    return intervalle[0] + int.from_bytes(empreinte, 'big') % (intervalle[1] - intervalle[0] + 1)


def _ajouter_mois(jour, mois):
    annee, m = divmod(jour.year * MOIS_PAR_AN + jour.month - 1 + mois, MOIS_PAR_AN)
    return jour.replace(year=annee, month=m + 1, day=min(jour.day, calendar.monthrange(annee, m + 1)[-1]))


def _personne(i, maison, nom, naissance, pere, mere, conjoints, hypotheses):
    return {'id': i, 'maison': maison, 'nom': nom, 'naissance': {'valeur': naissance.isoformat(), 'precision': 'jour'},
            'origine': 'plausible', 'presence': 'vivante', 'pere': pere, 'mere': mere, 'conjoints': conjoints,
            'sources': {'identite': None, 'naissance': None},
            'lacunes': {'identite': 'Nom descriptif, sans personne historique.', 'naissance': 'Date hypothétique : voir hypotheses.'},
            'hypotheses': hypotheses}


REGLE = 'niveau 2, « Les familles plausibles » (MODELE.md)'


def _admission(chef, p):
    """(motif d'écart ou None, naissance retenue, bornes) d'un chef ; une naissance hypothétique reste au jour près."""
    etat = chef.get('etat_familial', {}).get('conjoints')
    motif = next((m for m, c in (('presence', chef.get('presence') not in (None, 'vivante')),
                                 ('conjoint', bool(chef.get('conjoints'))), (etat, etat in ('union', 'veuvage'))) if c), None)
    naissance = chef['naissance']
    if motif is None and naissance is None and chef.get('origine') == 'plausible':
        ans = _tirer(p, chef['id'], 'chef-age', p['age_chef_plausible'])
        jour = _tirer(p, chef['id'], 'chef-jour', (0, JOURS_TIRES - 1))
        naissance = {'valeur': (_ajouter_mois(DEPART, -MOIS_PAR_AN * ans) - datetime.timedelta(days=jour)).isoformat(),
                     'precision': 'jour'}
    bornes = _bornes_naissance(naissance)
    if motif is None and bornes is None: motif = 'naissance'
    if motif is None and _age_revolu(bornes[-1], DEPART) < p['age_epoux_min']: motif = 'jeune'
    return motif, naissance, bornes


def generer_familles_plausibles(chefs, parametres=PARAMETRES_FAMILLES_PLAUSIBLES):
    """Rend (fiches triées par id, {chef écarté: motif}) ; niveau 2, pur, non activé, entrée intacte."""
    _controler_parametres(parametres)
    p, sortie, ecartes = parametres, [], {}
    for chef in sorted(chefs, key=lambda c: c['id']):
        chef = copy.deepcopy(chef)
        sortie.append(chef)
        i, maison, nom = chef['id'], chef['maison'], chef['nom']
        motif, naissance, bornes = _admission(chef, p)
        if motif:
            ecartes[i] = motif
            continue
        e_id = f'personne-{maison}-epouse'
        lien = f"{REGLE} : age_epoux_min {p['age_epoux_min']} ans, aucune famille connue"
        chef.update(conjoints=[e_id], hypotheses={'conjoints': lien})
        if naissance != chef['naissance']:
            chef.update(naissance=naissance)
            chef['hypotheses']['naissance'] = f"{REGLE} : âge tiré dans age_chef_plausible {p['age_chef_plausible']}"
        ecart = _tirer(p, i, 'epouse-ecart', p['ecart_epouse'])
        jour = _tirer(p, i, 'epouse-jour', (0, JOURS_TIRES - 1))
        mere = min(_ajouter_mois(bornes[-1], MOIS_PAR_AN * ecart) + datetime.timedelta(days=jour),
                   _ajouter_mois(DEPART, -MOIS_PAR_AN * p['age_epouse_min']))
        sortie.append(_personne(e_id, maison, f'Épouse de {nom}', mere, None, None, [i], {
            'conjoints': lien, 'naissance': f"{REGLE} : borne haute du chef + ecart_epouse {p['ecart_epouse']} "
                                            f"(tiré {ecart}) + jour tiré, au plus age_epouse_min {p['age_epouse_min']} ans"}))
        if chef.get('etat_familial', {}).get('enfants') in ('documentes', 'absence_attestee'):
            continue
        naiss = _ajouter_mois(mere, MOIS_PAR_AN * p['age_premier_enfant'])
        for k in range(1, p['enfants_max'] + 1):
            naiss = _ajouter_mois(naiss, _tirer(p, i, f'enfant-{k}-intervalle', p['intervalle_mois']))
            if naiss >= DEPART or _age_revolu(mere, naiss) > p['age_dernier_enfant']:
                break
            sortie.append(_personne(f'personne-{maison}-enfant-{k}', maison, f"{'1er' if k == 1 else f'{k}e'} enfant de {nom}",
                                    naiss, i, e_id, [], {
                'naissance': f"{REGLE} : mère à age_premier_enfant {p['age_premier_enfant']} ans, puis intervalle_mois "
                             f"{p['intervalle_mois']} par enfant jusqu'à age_dernier_enfant {p['age_dernier_enfant']} "
                             f"et enfants_max {p['enfants_max']}",
                'pere': lien, 'mere': lien}))
    return tuple(sorted(sortie, key=lambda f: f['id'])), ecartes


def valider_familles_plausibles(fiches, chefs, parametres=PARAMETRES_FAMILLES_PLAUSIBLES):
    """Refait la génération et exige l'égalité complète, la séparation des hypothèses et des liens valides."""
    attendues, _ = generer_familles_plausibles(chefs, parametres)
    exiger(isinstance(fiches, (list, tuple)) and tuple(fiches) == attendues)
    avant = {c['id']: c for c in chefs}
    for f in fiches:
        exiger('http' not in str(f.get('hypotheses', '')))
        if f['id'] in avant:
            exiger(all(f[k] == avant[f['id']][k] for k in ('nom', 'sources', 'lacunes', 'etat_familial') if k in avant[f['id']]))
            exiger(avant[f['id']]['naissance'] in (None, f['naissance']))
        else:
            exiger(f['origine'] == 'plausible' and set(f['sources'].values()) == {None} and bool(f['hypotheses']))
    return valider_liens_familiaux([{'pere': None, 'mere': None, 'conjoints': [], **f} for f in fiches])
