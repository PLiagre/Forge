"""Preuves des familles plausibles (niveau 2, non activées) et de leurs contre-épreuves."""
import ast
import copy
import datetime
import pathlib
import random
import re

import pytest

from sim import personnages, world as etat_monde
from sim.personnages import (PARAMETRES_FAMILLES_PLAUSIBLES as P, generer_familles_plausibles as generer,
                             valider_familles_plausibles as valider, valider_liens_familiaux)
from sim.world import World

DEPART = datetime.date(1400, 1, 1)
SRC = {'url': 'https://exemple.test/x', 'fait': 'fait'}


def chef(m, naiss, origine='historique', conj=None, enf=None, **champs):
    n = None if naiss is None else {'valeur': naiss[0], 'precision': naiss[1]}
    f = {'id': 'personne-' + m, 'maison': m, 'nom': 'Chef ' + m, 'naissance': n, 'origine': origine,
         'sources': {'identite': SRC, 'naissance': SRC if n else None},
         'lacunes': {'identite': None, 'naissance': None if n else 'Naissance inconnue.'}}
    if conj or enf: f['etat_familial'] = {'conjoints': conj, 'enfants': enf}
    return {**f, **champs}


J = ('1360-05-05', 'jour')
CHEFS = [chef('a21', ('1379-01-01', 'jour')), chef('b70', ('1370', 'annee')), chef('cplaus', None, 'plausible'),
         chef('d20', ('1379-01-02', 'jour')), chef('e79', ('1379', 'annee')), chef('fvers', ('1370', 'vers')),
         chef('gsans', None), chef('hunion', J, conj='union'), chef('iveuf', J, conj='veuvage'),
         chef('jmarie', J, conjoints=['personne-kmarie']), chef('kmarie', J, conjoints=['personne-jmarie']),
         chef('ldec', J, presence='decedee'), chef('m50', ('1350-06-06', 'jour'), conj='lacune', enf='lacune'),
         chef('n62', ('1362-02-02', 'jour')), chef('o66', ('1366-03-03', 'jour')), chef('pdoc', J, enf='documentes')]
ADMIS = {'a21', 'b70', 'cplaus', 'm50', 'n62', 'o66', 'pdoc'}
ECARTES = {'d20': 'jeune', 'e79': 'jeune', 'fvers': 'naissance', 'gsans': 'naissance', 'hunion': 'union',
           'iveuf': 'veuvage', 'jmarie': 'conjoint', 'kmarie': 'conjoint', 'ldec': 'presence'}
FAM, REFUS = generer(CHEFS)


def date(f):
    return datetime.date.fromisoformat(f['naissance']['valeur'])


def age(f, jour=DEPART):
    return jour.year - date(f).year - ((jour.month, jour.day) < (date(f).month, date(f).day))


def epouses(fam):
    return {f['id']: f for f in fam if f['id'].endswith('-epouse')}


def enfants(fam, maison):
    return [f for f in fam if f['id'].startswith(f'personne-{maison}-enfant-')]


def muter(fam, i, **champs):
    return [{**copy.deepcopy(f), **(champs if f['id'] == i else {})} for f in fam]


def refuse(fam, chefs=CHEFS, parametres=P):
    with pytest.raises(ValueError):
        valider(fam, chefs, parametres)


def test_seuils():
    assert {i[len('personne-'):-len('-epouse')] for i in epouses(FAM)} == ADMIS
    assert {i[len('personne-'):]: m for i, m in REFUS.items()} == ECARTES
    assert valider(FAM, CHEFS, P)['verifies']
    sans = [f for f in FAM if f['id'] != 'personne-a21-epouse']
    refuse([{**f, 'conjoints': []} if f['id'] == 'personne-a21' else f for f in sans])
    for maison in ('d20', 'iveuf'):  # épouse ajoutée à un chef de 20 ans, ou veuf
        epouse = {**copy.deepcopy(epouses(FAM)['personne-a21-epouse']), 'id': f'personne-{maison}-epouse',
                  'conjoints': [f'personne-{maison}']}
        refuse(muter(FAM, f'personne-{maison}', conjoints=[epouse['id']]) + [epouse])
    refuse(muter(FAM, 'personne-a21-epouse', conjoints=[]))  # conjoint non réciproque
    vide = tuple(sorted(copy.deepcopy(CHEFS), key=lambda f: f['id']))
    assert {f['id'] for f in epouses(vide)} != {f'personne-{m}-epouse' for m in ADMIS}
    refuse(vide)


def test_age_maternel():
    mm = ('a21', 'n62', 'o66', 'm50')
    nombres = [len(enfants(FAM, m)) for m in mm]
    ages = [age(epouses(FAM)[f'personne-{m}-epouse']) for m in mm]
    assert ages == sorted(set(ages)) and nombres == sorted(set(nombres)) and nombres[0] == 0
    assert all(not enfants(FAM, m) for m in ADMIS if age(epouses(FAM)[f'personne-{m}-epouse']) < P['age_premier_enfant'])
    tous = [f for m in ADMIS for f in enfants(FAM, m)]
    assert tous and all(date(f) < DEPART for f in tous) and max(len(enfants(FAM, m)) for m in ADMIS) <= P['enfants_max']
    bilan = valider(FAM, CHEFS, P)
    assert not [c for c in bilan['indetermines'] if c['personnes'][1] in {f['id'] for f in tous}]
    assert sum(c['contrainte'] in {'age_maternel', 'anteriorite'} for c in bilan['verifies']) == 3 * len(tous)
    premier = lambda p, m='n62': date(enfants(generer(CHEFS, p)[0], m)[0])
    assert premier({**P, 'age_premier_enfant': P['age_premier_enfant'] + 1}) == premier(P).replace(year=premier(P).year + 1)
    assert len(enfants(generer(CHEFS, {**P, 'age_dernier_enfant': P['age_premier_enfant']})[0], 'm50')) <= 1
    assert len(enfants(generer(CHEFS, {**P, 'intervalle_mois': (60, 72)})[0], 'm50')) < len(enfants(FAM, 'm50'))
    mere, e = epouses(FAM)['personne-m50-epouse'], enfants(FAM, 'm50')[0]
    for ans in (14, 46):  # enfant d'une mère de 14 ou de 46 ans
        fausse = muter(FAM, e['id'], naissance={'valeur': str(date(mere).replace(year=date(mere).year + ans)), 'precision': 'jour'})
        refuse(fausse)
        with pytest.raises(ValueError):
            valider_liens_familiaux(fausse)
    refuse(muter(FAM, e['id'], naissance={'valeur': '1400-01-02', 'precision': 'jour'}))
    refuse(muter(FAM, e['id'], naissance={'valeur': str(date(e) + datetime.timedelta(days=1)), 'precision': 'jour'}))
    refuse([f for f in FAM if f['id'] != e['id']])
    refuse(list(FAM) + [{**copy.deepcopy(e), 'id': 'personne-m50-enfant-9'}])
    for changement in ({'age_premier_enfant': 14}, {'age_dernier_enfant': 46}, {'intervalle_mois': (0, 0)},
                       {'intervalle_mois': (40, 24)}):
        with pytest.raises(ValueError):
            generer(CHEFS, {**P, **changement})


def test_graines_permutations(monkeypatch):
    resultats = []
    for graine in (0, 42):
        p = {**P, 'graine': graine}
        assert generer(CHEFS, p) == generer(CHEFS, p)
        valider(generer(CHEFS, p)[0], CHEFS, p)
        resultats.append([f['naissance'] for f in generer(CHEFS, p)[0]])
    assert resultats[0] != resultats[1]
    assert generer(CHEFS[::-1]) == generer(CHEFS[5:] + CHEFS[:5]) == (FAM, REFUS)
    copie, etat = copy.deepcopy(CHEFS), random.getstate()
    def interdit(*args, **kw): raise AssertionError('hasard')
    monkeypatch.setattr(random, 'random', interdit)
    monkeypatch.setattr(random, 'Random', interdit)
    assert generer(copie) == (FAM, REFUS) and copie == CHEFS and random.getstate() == etat
    arbre = ast.parse(pathlib.Path(personnages.__file__).read_text(encoding='utf-8'))
    assert 'random' not in {a.name for n in ast.walk(arbre) if isinstance(n, (ast.Import, ast.ImportFrom))
                            for a in n.names} | {getattr(n, 'module', None) for n in ast.walk(arbre)}
    refuse(tuple(reversed(FAM)))
    refuse(FAM[3:] + FAM[:3])


def test_hypotheses():
    generees = [f for f in FAM if f['id'] not in {c['id'] for c in CHEFS}]
    assert generees and all(f['origine'] == 'plausible' and set(f['sources'].values()) == {None}
                            and f['hypotheses'] and f['presence'] == 'vivante' for f in generees)
    avant = {c['id']: c for c in CHEFS}
    for f in (f for f in FAM if f['id'] in avant and 'hypotheses' in f):
        assert all(f[k] == avant[f['id']][k] for k in ('nom', 'sources', 'lacunes', 'etat_familial') if k in avant[f['id']])
        assert 'http' not in str(f['hypotheses'])
        if avant[f['id']]['naissance'] is not None: assert f['naissance'] == avant[f['id']]['naissance']
    fiche = {f['id']: f for f in FAM}
    assert fiche['personne-gsans']['naissance'] is None and fiche['personne-gsans']['lacunes']['naissance']
    assert 'hypotheses' not in fiche['personne-d20'] and fiche['personne-a21']['naissance'] == avant['personne-a21']['naissance']
    assert P['age_chef_plausible'][0] <= age(fiche['personne-cplaus']) <= P['age_chef_plausible'][1]
    cplaus = avant['personne-cplaus']['lacunes']
    assert fiche['personne-cplaus']['lacunes'] == cplaus
    refuse(muter(FAM, 'personne-a21', hypotheses={'conjoints': 'voir https://exemple.test'}))
    refuse(muter(FAM, 'personne-a21-epouse', origine='historique'))
    refuse(muter(FAM, 'personne-a21', naissance={'valeur': '1370-01-01', 'precision': 'jour'}))
    refuse(muter(FAM, 'personne-cplaus', lacunes={**cplaus, 'naissance': None}))
    refuse(muter(FAM, 'personne-a21-epouse', hypotheses={}))


def _inchange(monde):
    return not any('hypotheses' in p or re.search(r'-(epouse|enfant-)', p['id']) for p in monde.personnages)


def test_production_inchangee(monkeypatch):
    def interdit(*args, **kw): raise AssertionError('la génération ne doit pas être appelée')
    monkeypatch.setattr(personnages, 'generer_familles_plausibles', interdit)
    assert _inchange(World.charger(0))
    vrai = etat_monde.construire_personnages  # contre-épreuve : la génération branchée dans le constructeur
    monkeypatch.undo()
    monkeypatch.setattr(etat_monde, 'construire_personnages', lambda m: (generer(
        [f for f in vrai(m)[0] if f['origine'] == 'plausible'])[0], vrai(m)[1]))
    assert not _inchange(World.charger(0))
