"""Lecture exacte de vraies photographies ; chaque contrôle rejette ses copies altérées."""
from copy import deepcopy
import pytest
from sim.__main__ import _simulate
from sim.seigneuries import charger_seigneuries
from sim.snapshot_export import build_snapshot_document
from vues.relief import encart as vue

@pytest.fixture(scope='module')
def photographies():
    bar = next(t.id for t in charger_seigneuries() if t.nom == 'Duché de Bar')
    documents = []
    for part in (.6, .1):
        gestes = [{'tick': 0, 'intention': {'type': 'choisir_depart', 'seigneurie': bar}},
                  {'tick': 1, 'intention': {'type': 'fixer_part', 'maison': f'seigneurie-{bar}', 'part': part}}]
        _, monde = _simulate(30, 0, gestes)
        documents.append(build_snapshot_document(monde, 0, 30))
    return documents

def zone(d):
    ids = {d['terre_choisie']['cell_id']} | {v['cell_id'] for v in d['terre_choisie']['voisins']}
    return sorted((c for c in d['cells'] if c['cell_id'] in ids), key=lambda c: c['cell_id'])

def rejeter(d, e, modifier):
    copie = deepcopy(e); modifier(copie)
    with pytest.raises(vue.EncartErreur): vue.verifier_legende(d, copie)

def test_zone(photographies):
    d = photographies[0]; avant = deepcopy(d); e = vue.lire_encart(d)
    assert e['cellules'] == zone(d) and e['lieux'] and d == avant
    for l in e['lieux']:
        source = next(x for c in zone(d) if c['cell_id'] == l['cell_id'] for x in c['lieux'] if x['rang'] == l['rang'])
        assert all(l[k] == v for k, v in source.items())
    melange = deepcopy(d); melange['cells'].reverse()
    for c in melange['cells']: c['lieux'].reverse()
    assert vue.lire_encart(melange) == e
    for modifier in (lambda x: x['cellules'].pop(), lambda x: x['lieux'][0].update(point={}), lambda x: x['lieux'][0].update(maitre=None)):
        rejeter(d, e, modifier)
    assert vue.lire_encart({'terre_choisie': None}) == dict(cellules=[], lieux=[], couleurs={}, fleches=[], cercles=[], compteurs={}, legende=['aucune terre choisie'])

def test_couleurs(photographies, monkeypatch):
    d = photographies[0]; e = vue.lire_encart(d); joueur = d['maisons_du_joueur']['maison']['id']
    assert e['couleurs'][joueur] == vue.COULEUR_JOUEUR and vue.COULEUR_JOUEUR not in vue.PALETTE
    groupes = [{l['maitre'] for l in c['lieux'] if l['maitre'] is not None} for c in zone(d)]
    assert any(len(g) > 1 for g in groupes)
    for g in groupes: assert len({e['couleurs'][m] for m in g}) == len(g)
    assert all(c in vue.PALETTE for m, c in e['couleurs'].items() if m != joueur)
    g = next(g for g in groupes if len(g) > 1); a, b = sorted(g)[:2]
    rejeter(d, e, lambda x: x['couleurs'].update({b: x['couleurs'][a]}))
    sans = deepcopy(d); zone(sans)[0]['lieux'][0]['maitre'] = None
    assert vue.lire_encart(sans)['lieux'][0]['maitre'] is None
    monkeypatch.setattr(vue, 'PALETTE', ())
    with pytest.raises(vue.EncartErreur, match='palette'): vue.lire_encart(d)

def test_fleches(photographies):
    d = photographies[0]; e = vue.lire_encart(d); m = d['maisons_du_joueur']['maison']; s = m['siege']
    attendues = [(l['cell_id'], l['rang'], s['cell_id'], s['rang'], l['point'], s['point'], l['flux_30j']['preleve_kg']) for l in e['lieux'] if l['maitre'] == m['id'] and (l['cell_id'], l['rang']) != (s['cell_id'], s['rang'])]
    suz = d['maisons_du_joueur']['suzerain']['siege']
    attendues.append((s['cell_id'], s['rang'], suz['cell_id'], suz['rang'], s['point'], suz['point'], m['flux_30j']['du_envoye_kg']))
    assert attendues and [(f['source']['cell_id'], f['source']['rang'], f['destination']['cell_id'], f['destination']['rang'], f['source']['point'], f['destination']['point'], f['kg']) for f in e['fleches']] == attendues
    assert e['compteurs']['autres_lieux'] == sum(l['maitre'] not in (None, m['id']) for l in e['lieux'])
    assert e['compteurs']['autres_maitres'] == len({l['maitre'] for l in e['lieux'] if l['maitre'] not in (None, m['id'])})
    assert all(f['epaisseur_px'] == min(vue.EPAISSEUR_MAX, f['kg'] / vue.KG_PAR_PIXEL) for f in e['fleches'])
    for modifier in (lambda x: x['fleches'][0].update(source=x['fleches'][0]['destination'], destination=x['fleches'][0]['source']), lambda x: x['fleches'][0].update(kg=0), lambda x: x['fleches'].append(dict(x['fleches'][0], source=s, destination=s)), lambda x: x['fleches'].append(dict(x['fleches'][0], source=next(l for l in x['lieux'] if l['maitre'] not in (None, m['id']))))): rejeter(d, e, modifier)
    racine = deepcopy(d); racine['maisons_du_joueur']['maison']['suzerain'] = None; racine['maisons_du_joueur']['suzerain'] = None
    assert all(f['sorte'] != 'du' for f in vue.lire_encart(racine)['fleches'])

def test_echelle(photographies):
    d = deepcopy(photographies[0]); e = vue.lire_encart(d)
    d['maisons_du_joueur']['maison']['flux_30j']['du_envoye_kg'] *= 10
    assert vue.lire_encart(d)['fleches'][0] == e['fleches'][0]
    for kg in (0, 1, vue.KG_PAR_PIXEL * (vue.EPAISSEUR_MAX + 1)):
        d['maisons_du_joueur']['maison']['flux_30j']['du_envoye_kg'] = kg; x = vue.lire_encart(d)
        assert x['fleches'][-1]['kg'] == kg and x['fleches'][-1]['epaisseur_px'] == min(vue.EPAISSEUR_MAX, kg / vue.KG_PAR_PIXEL)
    for valeur in (vue.EPAISSEUR_MAX * x['fleches'][0]['kg'] / max(f['kg'] for f in x['fleches']), vue.EPAISSEUR_MAX + 1): rejeter(d, x, lambda r: r['fleches'][0].update(epaisseur_px=valeur))
    rejeter(d, x, lambda r: r['legende'].pop(1))

def test_cercles(photographies):
    d = deepcopy(photographies[0]); e = vue.lire_encart(d)
    attendus = {(l['cell_id'], l['rang']): l['flux_30j']['partis_personnes'] - l['flux_30j']['arrives_personnes'] for l in e['lieux'] if l['flux_30j']['partis_personnes'] > l['flux_30j']['arrives_personnes']}
    assert attendus and {(c['cell_id'], c['rang']): c['perte_nette_personnes'] for c in e['cercles']} == attendus
    assert all(all(c[k] == next(l for l in e['lieux'] if (l['cell_id'], l['rang']) == (c['cell_id'], c['rang']))['flux_30j'][k] for k in vue.FLUX_LIEU[1:]) for c in e['cercles'])
    assert all(c['point'] == next(l['point'] for l in e['lieux'] if (l['cell_id'], l['rang']) == (c['cell_id'], c['rang'])) for c in e['cercles'])
    for modifier in (lambda x: x['cercles'].pop(), lambda x: x['cercles'][0].update(perte_nette_personnes=x['cercles'][0]['perte_nette_personnes'] / 5)): rejeter(d, e, modifier)
    l = zone(d)[0]['lieux'][0]
    for arrives in (l['flux_30j']['partis_personnes'], l['flux_30j']['partis_personnes'] + 1):
        l['flux_30j']['arrives_personnes'] = arrives; x = vue.lire_encart(d)
        assert not any(c['cell_id'] == zone(d)[0]['cell_id'] and c['rang'] == l['rang'] for c in x['cercles'])
        rejeter(d, x, lambda r: r['cercles'].append(dict(l, cell_id=zone(d)[0]['cell_id'], perte_nette_personnes=1)))

def test_legende_et_refus(photographies):
    d = photographies[0]; e = vue.lire_encart(d); vue.verifier_legende(d, e)
    assert all(f"maison du joueur, {k} = {v} {'kg' if k.endswith('_kg') else 'personnes'}" in e['legende'] for k, v in d['maisons_du_joueur']['maison']['flux_30j'].items())
    assert e['legende'][0] == f"tick {d['tick']} ; fenêtre de 30 jours"
    assert all(any(f"prélevé = {l['flux_30j']['preleve_kg']} kg ; sorties = {l['flux_30j']['partis_personnes']} personnes ; entrées = {l['flux_30j']['arrives_personnes']} personnes" in ligne for ligne in e['legende']) for c in zone(d) for l in c['lieux'])
    for ligne in e['legende']: rejeter(d, e, lambda x: x['legende'].remove(ligne))
    rejeter(d, e, lambda x: x['legende'].__setitem__(-1, 'kg = 0'))
    for cible in ('bloc', 'maison', 'suzerain', 'lieu', 'siege', 'siege_suzerain'):
        for valeur in ('absent', None):
            copie = deepcopy(d); bloc = copie['maisons_du_joueur']
            objets = {'bloc': (copie, ['maisons_du_joueur']), 'maison': (bloc, ['maison']), 'suzerain': (bloc, ['suzerain']), 'lieu': (zone(copie)[0]['lieux'][0], ['point', 'flux_30j']), 'siege': (bloc['maison']['siege'], ['point']), 'siege_suzerain': (bloc['suzerain']['siege'], ['point'])}
            objet, champs = objets[cible]
            if cible == 'lieu': champs += list(objet['flux_30j'])
            for champ in champs:
                sonde = deepcopy(copie); b = sonde['maisons_du_joueur']; o = sonde if cible == 'bloc' else b if cible in ('maison', 'suzerain') else zone(sonde)[0]['lieux'][0] if cible == 'lieu' else b['maison' if cible == 'siege' else 'suzerain']['siege']
                if champ not in ('point', 'flux_30j', 'maisons_du_joueur', 'maison', 'suzerain'): o = o['flux_30j']
                if valeur == 'absent': o.pop(champ)
                else: o[champ] = valeur
                with pytest.raises(vue.EncartErreur, match=champ): vue.lire_encart(sonde)
    for champ in ('flux_30j', *d['maisons_du_joueur']['maison']['flux_30j']):
        for valeur in ('absent', None):
            sonde = deepcopy(d); o = sonde['maisons_du_joueur']['maison']; o = o if champ == 'flux_30j' else o['flux_30j']
            if valeur == 'absent': o.pop(champ)
            else: o[champ] = valeur
            with pytest.raises(vue.EncartErreur, match=champ): vue.verifier_legende(sonde, e)
    sonde = deepcopy(d); sonde['cells'] = [c for c in sonde['cells'] if c['cell_id'] != zone(d)[-1]['cell_id']]
    with pytest.raises(vue.EncartErreur, match='cell'): vue.lire_encart(sonde)
    sonde = deepcopy(d); l = next(l for c in zone(sonde) for l in c['lieux'] if l['maitre'] == d['maisons_du_joueur']['maison']['id'] and l['rang'] != d['maisons_du_joueur']['maison']['siege']['rang']); l['flux_30j'].pop('preleve_kg')
    with pytest.raises(vue.EncartErreur, match='preleve_kg'): vue.verifier_legende(sonde, e)
    sonde = deepcopy(d); sonde['maisons_du_joueur']['maison']['flux_30j'] = dict.fromkeys(vue.FLUX_MAISON, 0); vue.verifier_legende(sonde, vue.lire_encart(sonde))

def comparer(fort, faible):
    for e in (fort, faible): assert e['compteurs']['lieux_joueur'] == 4 and e['fleches']
    assert sum(l['flux_30j']['preleve_kg'] for l in fort['lieux'] if l['maitre'] == fort['joueur']['id']) > sum(l['flux_30j']['preleve_kg'] for l in faible['lieux'] if l['maitre'] == faible['joueur']['id'])
    assert all(a['kg'] > b['kg'] and a['epaisseur_px'] > b['epaisseur_px'] for a, b in zip(fort['fleches'], faible['fleches']))
    assert fort['compteurs']['cercles_joueur'] == 4 and faible['compteurs']['cercles_joueur'] == 0
    assert sum(c['maitre'] == fort['joueur']['id'] for c in fort['cercles']) == 4

def test_bar(photographies):
    resultats = [vue.lire_encart(d) for d in photographies]
    for d, e in zip(photographies, resultats):
        vue.verifier_legende(d, e); assert [f['kg'] for f in e['fleches']] == [l['flux_30j']['preleve_kg'] for c in zone(d) for l in c['lieux'] if l['maitre'] == d['maisons_du_joueur']['maison']['id'] and (c['cell_id'], l['rang']) != (d['maisons_du_joueur']['maison']['siege']['cell_id'], d['maisons_du_joueur']['maison']['siege']['rang'])] + [d['maisons_du_joueur']['maison']['flux_30j']['du_envoye_kg']]
        assert [(l['cell_id'], l['rang'], l['flux_30j']) for l in e['lieux']] == [(c['cell_id'], l['rang'], l['flux_30j']) for c in zone(d) for l in c['lieux']]
        assert {(c['cell_id'], c['rang'], c['perte_nette_personnes']) for c in e['cercles']} == {(c['cell_id'], l['rang'], l['flux_30j']['partis_personnes'] - l['flux_30j']['arrives_personnes']) for c in zone(d) for l in c['lieux'] if l['flux_30j']['partis_personnes'] > l['flux_30j']['arrives_personnes']}
        print('part', e['joueur']['part'], 'kilos par lieu', [(l['nom'], l['flux_30j']['preleve_kg']) for l in e['lieux'] if l['maitre'] == e['joueur']['id']], 'dû', e['joueur']['flux_30j']['du_envoye_kg'], 'épaisseurs', [f['epaisseur_px'] for f in e['fleches']], 'cercles joueur/autres', e['compteurs']['cercles_joueur'], e['compteurs']['cercles_autres'])
    comparer(*resultats)
    for paire in ([resultats[1]] * 2, resultats[::-1], [dict(resultats[0], lieux=[]), resultats[1]], [dict(resultats[0], cercles=[]), resultats[1]]):
        with pytest.raises(AssertionError): comparer(*paire)
