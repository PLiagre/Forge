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

# Preuves du dessin : les références viennent de la photographie et des pixels.
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageColor
from vues.relief.raster import index_des_cellules, _vers_pixel
from vues.relief.carte1400 import COULEUR_CHOIX, _lignes_ajustees, MARGE_FICHE, HAUTEUR_LIGNE, COULEUR_FOND, COULEUR_TEXTE

def repere(d, largeur=900):
    e = vue.lire_encart(d); index, bornes, _ = index_des_cellules({'cells': e['cellules']}, largeur=largeur)
    def point(l): return np.array(_vers_pixel(l['point']['x_m'], l['point']['y_m'], bornes, largeur, len(index)), dtype=float)
    return e, index, bornes, point

def nul(d):
    d = deepcopy(d); d['maisons_du_joueur']['maison']['flux_30j']['du_envoye_kg'] = 0
    for c in zone(d):
        for l in c['lieux']: l['flux_30j']['preleve_kg'] = 0
    return d

def alterer(image, controle, geste):
    copie = image.copy(); geste(copie)
    with pytest.raises(AssertionError): controle(copie)

def test_encart_pixels_geometrie(photographies):
    d = photographies[0]; avant = deepcopy(d); e, index, _, point = repere(d)
    image, _ = vue.dessiner_encart(d, largeur=900); assert d == avant
    bord = np.zeros(index.shape, bool)
    for a, b in ((np.s_[:, :-1], np.s_[:, 1:]), (np.s_[:-1, :], np.s_[1:, :])): bord[a] |= index[a] != index[b]
    yy, xx = np.indices(index.shape)
    for l in e['lieux']:
        x, y = point(l); bord &= (xx-x)**2 + (yy-y)**2 > 144
    for f in e['fleches']:
        a, b = point(f['source']), point(f['destination']); v = b-a
        bord &= abs((xx-a[0])*v[1]-(yy-a[1])*v[0]) / np.linalg.norm(v) > 12
    assert bord.any() and any(len({l['maitre'] for l in c['lieux']}) > 1 for c in e['cellules'])
    def controle(i):
        assert np.all(i[:len(index)][bord] == vue.COULEUR_CONTOUR)
        for l in e['lieux']:
            x, y = point(l).astype(int); assert tuple(i[y, x, :3]) == ImageColor.getrgb(l['couleur'])
    controle(image); y, x = np.argwhere(bord)[0]; px, py = point(e['lieux'][0]).astype(int)
    for geste in (lambda i: i.__setitem__((y, x), 0), lambda i: i.__setitem__((py, px), i[py+12, px]), lambda i: i.__setitem__((py, px, slice(0, 3)), ImageColor.getrgb(e['lieux'][-1]['couleur']))): alterer(image, controle, geste)
    sans = deepcopy(d); zone(sans)[0]['lieux'][0]['maitre'] = None
    i, r = vue.dessiner_encart(sans, largeur=900); assert tuple(i[py, px, :3]) == ImageColor.getrgb(vue.COULEUR_SANS_MAITRE) and any('sans maître' in l for l in r['legende'])

def sections(d, image):
    e, _, _, point = repere(d); base, _ = vue.dessiner_encart(nul(d), largeur=900); mesures = []
    for f in e['fleches']:
        a, b = point(f['source']), point(f['destination']); u = (b-a)/np.linalg.norm(b-a); n = np.array([-u[1], u[0]])
        p = np.rint(a + (b-a)*.3 + np.arange(-12, 13)[:, None]*n).astype(int)
        p = p[(p[:, 0]>=0)&(p[:, 0]<900)&(p[:, 1]>=0)&(p[:, 1]<len(base))]; assert len(p)
        mesures.append(np.maximum(0, image[p[:, 1], p[:, 0], :3].astype(int)-base[p[:, 1], p[:, 0], :3]).sum())
    return np.array(mesures)

def test_encart_pixels_bar(photographies, tmp_path):
    resultats = [vue.dessiner_encart(d, largeur=900) for d in photographies]; images = [i for i, _ in resultats]
    def comparer_pixels(a, b): assert np.all(sections(photographies[0], a) > sections(photographies[1], b))
    comparer_pixels(*images)
    for paire in ((images[1], images[1]), (images[0], images[0])):
        with pytest.raises(AssertionError): comparer_pixels(*paire)
    for d, image in zip(photographies, images):
        e, index, _, point = repere(d); attendus = {(c['cell_id'], c['rang']) for c in e['cercles']}
        def controle(i):
            assert not np.any(np.all(i[..., :3] == COULEUR_CHOIX[:3], axis=2))
            for l in e['lieux']:
                x, y = point(l).astype(int); rouge = np.all(i[max(0,y-10):y+11, max(0,x-10):x+11, :3] == vue.COULEUR_PERTE[:3], axis=2)
                assert bool(rouge.any()) == ((l['cell_id'], l['rang']) in attendus)
        controle(image); assert e['compteurs']['cercles_joueur'] == (4 if d is photographies[0] else 0)
        r = resultats[0 if d is photographies[0] else 1][1]; assert r['compteurs'] == e['compteurs'] and r['cercles_dessines'] == len(attendus) and r['fleches_dessinees'] == len(e['fleches'])
        base, _ = vue.dessiner_encart(nul(d), largeur=900)
        yy, xx = np.indices(index.shape)
        for f in e['fleches'][:-1]:
            a, b = point(f['source']), point(f['destination']); u = (b-a)/np.linalg.norm(b-a); w = f['epaisseur_px']
            z = (b[0]-xx)*u[0]+(b[1]-yy)*u[1]; n = abs((b[0]-xx)*u[1]-(b[1]-yy)*u[0]); longueur = max(6,2*w)
            triangle = Image.new('L', (900,len(index))); v = np.array([-u[1],u[0]])*max(3,w); fond = b-longueur*u
            ImageDraw.Draw(triangle).polygon([tuple(b),tuple(fond+v),tuple(fond-v)], fill=255)
            masque = (np.array(triangle)>0)&(n>w/2+.6)&(np.hypot(xx-b[0],yy-b[1])>(8.8 if e['cercles'] else 4)); assert masque.any()
            def pointe(i): assert np.all((i[:len(index),:,:3].astype(int)-base[:len(index),:,:3])[masque].sum(axis=1) > 0)
            pointe(image); alterer(image, pointe, lambda i: i[:len(index)].__setitem__(masque, base[:len(index)][masque]))
            x, y = b.astype(int); boite = (slice(y-12,y+13), slice(x-12,x+13))
            alterer(image, pointe, lambda i: i.__setitem__(boite, np.flip(i[boite], axis=(0,1))))
        alterer(image, controle, lambda i: i.__setitem__((0, 0), COULEUR_CHOIX))
        if e['cercles']:
            c = e['cercles'][0]; x, y = point(c).astype(int)
            alterer(image, controle, lambda i: i.__setitem__((slice(y-10,y+11), slice(x-10,x+11)), 0))
        chemin = tmp_path / f"bar-{e['joueur']['part']}.png"; Image.fromarray(image).save(chemin)
        print(chemin, 'couvertures', sections(d, image), 'cercles', len(attendus), 'hauteur du plan', len(index))

def test_encart_pixels_bord(photographies):
    d = photographies[0]; e, index, bornes, point = repere(d); a, b = point(e['fleches'][-1]['source']), point(e['fleches'][-1]['destination'])
    assert b[0] < 0 or b[0] >= 900 or b[1] < 0 or b[1] >= len(index)
    for deplacement in (0, 180000):
        copie = nul(d); copie['maisons_du_joueur']['suzerain']['siege']['point']['y_m'] += deplacement
        _, autre, limites, proj = repere(copie); assert limites == bornes and autre.shape == index.shape
        a, b = proj(e['fleches'][-1]['source']), proj(copie['maisons_du_joueur']['suzerain']['siege']); u = (b-a)/np.linalg.norm(b-a)
        source = e['fleches'][-1]['source']['point']; cible = copie['maisons_du_joueur']['suzerain']['siege']['point']; minx,miny,maxx,maxy = bornes
        t = min(v for v in [(c-source[k])/(cible[k]-source[k]) for k,c in (('x_m',minx),('x_m',maxx),('y_m',miny),('y_m',maxy)) if cible[k] != source[k]] if v > 0)
        bout = np.array(_vers_pixel(source['x_m']+t*(cible['x_m']-source['x_m']), source['y_m']+t*(cible['y_m']-source['y_m']), bornes,900,len(index))); yy,xx = np.indices(index.shape)
        temoin, _ = vue.dessiner_encart(copie, largeur=900)
        for kg in (0, 1, 10000, 400000, 900000):
            copie['maisons_du_joueur']['maison']['flux_30j']['du_envoye_kg'] = kg; image, r = vue.dessiner_encart(copie, largeur=900)
            delta = image[:len(index), :, :3].astype(int)-temoin[:len(index), :, :3]; w = min(8,kg/vue.KG_PAR_PIXEL); v = np.array([-u[1],u[0]])*max(3,w); fond = bout-u*max(6,2*w)
            triangle = Image.new('L',(900,len(index))); ImageDraw.Draw(triangle).polygon([tuple(bout),tuple(fond+v),tuple(fond-v)], fill=255)
            masque = (np.array(triangle)>0)&(abs((xx-bout[0])*u[1]-(yy-bout[1])*u[0])>w/2+.6); assert masque.any()
            def controle(i):
                diff = i[:len(index), :, :3].astype(int)-temoin[:len(index), :, :3]
                assert bool(np.any(diff)) == (kg > 0)
                if kg: assert np.any(diff[masque]>0) and np.any(diff[max(0,int(bout[1])-2):int(bout[1])+3, max(0,int(bout[0])-2):int(bout[0])+3] > 0)
            controle(image)
            if kg:
                boite = (slice(max(0,bout[1]-24),bout[1]+25),slice(max(0,bout[0]-24),bout[0]+25))
                alterer(image, controle, lambda i: i.__setitem__(boite, temoin[boite]))
            else: alterer(image, controle, lambda i: i.__setitem__((0,0), (100,100,100,255)))
            assert r['fleches_coupees'] == (kg > 0) and any('hors encart' in l and 'Paris' in l for l in r['legende'])
            if kg == 400000: plafond = delta.copy()
            if kg == 900000: assert np.array_equal(delta, plafond)

def test_encart_pixels_legende(photographies):
    d = deepcopy(photographies[0]); d['maisons_du_joueur']['maison']['nom'] += ' ' + 'motlong'*30
    for doc in (d, {'terre_choisie': None, 'tick': 30, 'seed': 0}):
        for largeur in (900, 64):
            image, r = vue.dessiner_encart(doc, largeur=largeur); police = ImageFont.load_default(); crayon = ImageDraw.Draw(Image.new('RGBA', (1,1)))
            attendues = vue.lire_encart(doc)['legende']; assert all(l in r['legende'] for l in attendues)
            lignes = _lignes_ajustees(r['legende'], crayon, police, largeur); h = 2*MARGE_FICHE+HAUTEUR_LIGNE*len(lignes)
            bande = Image.new('RGBA', (largeur,h), COULEUR_FOND); dessin = ImageDraw.Draw(bande)
            for n, ligne in enumerate(lignes): dessin.text((MARGE_FICHE,MARGE_FICHE+n*HAUTEUR_LIGNE), ligne, font=police, fill=COULEUR_TEXTE)
            def controle(i): assert i.shape == (r['hauteur_plan']+h,largeur,4) and np.array_equal(i[r['hauteur_plan']:], np.array(bande))
            controle(image); assert np.any(np.array(bande)[..., :3] != COULEUR_FOND[:3])
            for geste in (lambda i: i.__setitem__((slice(-HAUTEUR_LIGNE,None), slice(None)), COULEUR_FOND), lambda i: i.__setitem__((-h+MARGE_FICHE+5, MARGE_FICHE), 0)): alterer(image, controle, geste)
            if doc['terre_choisie'] is None: assert r['hauteur_plan'] == r['fleches_dessinees'] == r['fleches_coupees'] == r['cercles_dessines'] == 0 and not r['compteurs']
