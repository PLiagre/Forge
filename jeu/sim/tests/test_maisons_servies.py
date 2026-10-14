"""Maisons servies : comparaison au monde réel et contre-épreuves des contrôles."""

import copy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import statistics
import time
from urllib.parse import urlencode

import pytest

from sim.flux import flux_de_lieu, flux_de_maison
from sim.maisons_servies import (
    MaisonInconnue, document_de_maison, liste_des_maisons, matiere_des_maisons,
)
from sim.noms import noms_depuis_monde
from sim.seigneuries import charger_seigneuries
from sim.tests.test_carte_servie import _service_local
from sim.tests.test_monde import requete_service


CHAMPS_KG = ('preleve_kg', 'recu_kg', 'du_envoye_kg', 'mange_en_route_kg', 'rendu_kg')
CHAMPS_FICHE = {
    'id', 'nom', 'sorte', 'suzerain', 'siege', 'lieux', 'part', 'grenier',
    'flux_30j', 'absents', 'tick', 'date',
}


def _lire(port, chemin, methode='GET', intention=None):
    corps = None if intention is None else json.dumps(intention).encode('utf-8')
    statut, document, octets = requete_service(port, chemin, methode, corps)
    assert statut == 200, document
    return document, octets


def _route(identifiant):
    return '/maison?' + urlencode({'id': identifiant})


def _preparer(serveur, port, jours=35):
    _lire(port, '/intention', 'POST', {
        'type': 'choisir_depart', 'seigneurie': charger_seigneuries()[0].id,
    })
    _lire(port, '/tick?n=1', 'POST')
    _lire(port, '/intention', 'POST', {
        'type': 'fixer_part', 'maison': serveur.world.maison_du_joueur, 'part': 0.25,
    })
    _lire(port, f'/tick?n={jours}', 'POST')


@pytest.fixture(scope='module')
def service():
    with _service_local() as (serveur, port):
        _preparer(serveur, port)
        yield serveur, port


@pytest.fixture(scope='module')
def documents(service):
    serveur, port = service
    liste = _lire(port, '/maisons')[0]
    fiches = {m['id']: _lire(port, _route(m['id']))[0] for m in liste['maisons']}
    lieux = {cid: _lire(port, f'/lieu?cell={cid}')[0] for cid in serveur.world.cells}
    return liste, fiches, lieux


def _tenus(monde, identifiant):
    return sorted((cid, l.rang) for cid, c in monde.cells.items()
                  for l in c.lieux if l.maitre == identifiant)


def _verifier_liste(document, monde):
    registre = sorted(monde.maisons, key=lambda m: m.id)
    assert registre
    assert set(document) == {'tick', 'date', 'nombre', 'maisons'}
    assert document['tick'] == monde.ticks_ecoules
    assert document['date'] == monde.date_simulation
    assert document['nombre'] == len(document['maisons']) == len(registre)
    assert [m['id'] for m in document['maisons']] == [m.id for m in registre]
    for entree, maison in zip(document['maisons'], registre):
        assert set(entree) == {'id', 'nom', 'sorte', 'suzerain', 'siege', 'lieux'}
        assert entree['sorte'] == maison.sorte
        assert entree['suzerain'] == maison.suzerain
        assert entree['siege'] == (None if maison.cell_id is None else {
            'cell_id': maison.cell_id, 'rang': maison.rang,
        })
        assert entree['lieux'] == len(_tenus(monde, maison.id))


def test_liste_complete_et_contre_epreuves(service, documents):
    document = documents[0]
    _verifier_liste(document, service[0].world)
    ampute = copy.deepcopy(document)
    ampute['maisons'].pop()
    ampute['nombre'] -= 1
    change = copy.deepcopy(document)
    change['maisons'][0]['suzerain'] = 'autre-suzerain'
    for faux in (ampute, change):
        with pytest.raises(AssertionError):
            _verifier_liste(faux, service[0].world)


def _verifier_fiche(document, monde, lieux):
    identifiant = document['id']
    maison = next(m for m in monde.maisons if m.id == identifiant)
    assert set(document) == CHAMPS_FICHE
    assert document['sorte'] == maison.sorte
    assert document['suzerain'] == maison.suzerain
    assert document['tick'] == monde.ticks_ecoules
    assert document['date'] == monde.date_simulation
    assert document['part'] == monde.parts[identifiant]
    assert document['grenier'] == monde.greniers[identifiant]
    tenus = _tenus(monde, identifiant)
    assert document['lieux'] == [{'cell_id': cid, 'rang': rang} for cid, rang in tenus]
    flux = document['flux_30j']
    assert set(flux) == set(CHAMPS_KG) | {'partis_personnes', 'arrives_personnes'}
    assert {cle: flux[cle] for cle in CHAMPS_KG} == flux_de_maison(monde, identifiant)
    for champ in ('partis', 'arrives'):
        assert flux[champ + '_personnes'] == sum(
            flux_de_lieu(monde, cid, rang)[champ] for cid, rang in tenus)
    siege = document['siege']
    assert set(siege) == {'cell_id', 'rang', 'nom', 'point'}
    assert (siege['cell_id'], siege['rang']) == (maison.cell_id, maison.rang)
    if siege['cell_id'] is not None:
        assert siege['point'] == next(l['point'] for l in lieux[siege['cell_id']]['lieux']
                                      if l['rang'] == siege['rang'])


def test_toutes_les_fiches_exactes_et_contre_epreuves(service, documents):
    serveur, port = service
    _, fiches, lieux = documents
    assert fiches and len(fiches) == len(serveur.world.maisons)
    assert _lire(port, '/monde')[0]['tick'] == serveur.world.ticks_ecoules
    for fiche in fiches.values():
        _verifier_fiche(fiche, serveur.world, lieux)
    for champ in ('preleve_kg', 'du_envoye_kg', 'mange_en_route_kg', 'partis_personnes'):
        assert any(f['flux_30j'][champ] > 0 for f in fiches.values())
    joueur = fiches[serveur.world.maison_du_joueur]
    assert joueur['part'] == 0.25 and joueur['flux_30j']['du_envoye_kg'] > 0
    assert _lire(port, _route(joueur['suzerain']))[0] == fiches[joueur['suzerain']]
    faux = copy.deepcopy(joueur)
    faux['flux_30j']['preleve_kg'] += 1e-9
    with pytest.raises(AssertionError):
        _verifier_fiche(faux, serveur.world, lieux)
    autre = next(f for f in fiches.values()
                 if f['id'] != joueur['id'] and f['flux_30j']['partis_personnes'] > 0)
    cid, rang = next((cid, rang) for cid, rang in _tenus(serveur.world, autre['id'])
                    if flux_de_lieu(serveur.world, cid, rang)['partis'] > 0)
    faux = copy.deepcopy(joueur)
    faux['flux_30j']['partis_personnes'] += flux_de_lieu(serveur.world, cid, rang)['partis']
    with pytest.raises(AssertionError):
        _verifier_fiche(faux, serveur.world, lieux)


def _verifier_noms(document, maison, noms, lieux):
    attendu = (noms[maison.cell_id]['maisons'][maison.id]['nom']
               if maison.sorte == 'plausible' else maison.nom)
    assert document['nom'] == attendu
    if maison.sorte == 'plausible':
        assert document['nom'] != maison.id
    if maison.cell_id is not None:
        assert document['siege']['nom'] == next(
            l['nom'] for l in lieux[maison.cell_id]['noms']['lieux'] if l['rang'] == maison.rang)
    else:
        assert document['siege']['nom'] == maison.siege


def test_noms_du_monde_et_contre_epreuve(service, documents):
    noms = noms_depuis_monde(service[0].world)
    _, fiches, lieux = documents
    compteurs = {True: 0, False: 0}
    for maison in service[0].world.maisons:
        _verifier_noms(fiches[maison.id], maison, noms, lieux)
        compteurs[maison.sorte == 'plausible'] += 1
        assert next(m['nom'] for m in documents[0]['maisons'] if m['id'] == maison.id) == fiches[maison.id]['nom']
    assert all(compteurs.values())
    plausible = next(m for m in service[0].world.maisons if m.sorte == 'plausible')
    with pytest.raises(AssertionError):
        _verifier_noms(fiches[plausible.id] | {'nom': plausible.id}, plausible, noms, lieux)


def _verifier_absents(document):
    nuls = {cle for cle in ('nom', 'part', 'grenier') if document[cle] is None}
    if document['siege']['point'] is None:
        nuls.add('siege')
    assert set(document['absents']) == nuls
    assert all(document['absents'].values())


def test_absences_declarees_et_contre_epreuve(service, documents):
    for fiche in documents[1].values():
        _verifier_absents(fiche)
    hors_carte = [m for m in service[0].world.maisons if m.cell_id is None]
    assert hors_carte
    for maison in hors_carte:
        fiche = documents[1][maison.id]
        assert fiche['siege'] == {'cell_id': None, 'rang': None, 'nom': maison.siege, 'point': None}
        assert fiche['absents']['siege'] == maison.hors_carte
    fiche = next(f for f in documents[1].values() if not f['absents'])
    with pytest.raises(AssertionError):
        _verifier_absents(fiche | {'nom': None})


def test_matiere_pure_absences_et_mesures_vides(service):
    serveur, _ = service
    monde = serveur.world
    plausible = next(m for m in monde.maisons if m.sorte == 'plausible')
    noms = copy.deepcopy(serveur._noms)
    del noms[plausible.cell_id]['maisons'][plausible.id]
    parts, greniers = monde.parts.copy(), monde.greniers.copy()
    avant = monde.to_dict()
    try:
        del monde.parts[plausible.id]
        del monde.greniers[plausible.id]
        matiere = matiere_des_maisons(monde, noms, serveur._places_des_lieux())
        fiche = document_de_maison(matiere, plausible.id)
        _verifier_absents(fiche)
        assert fiche['nom'] is fiche['part'] is fiche['grenier'] is None
        assert str(plausible.cell_id) in fiche['absents']['nom']
        with pytest.raises(FrozenInstanceError):
            matiere.tick = -1
        with pytest.raises(MaisonInconnue, match='inconnue'):
            document_de_maison(matiere, 'inconnue')
    finally:
        monde.parts.update(parts)
        monde.greniers.update(greniers)
    assert monde.to_dict() == avant
    matiere = matiere_des_maisons(monde, serveur._noms, serveur._places_des_lieux())
    sans_routes = next(m for m in monde.maisons if m.id not in monde.routes_des_lieux.noms)
    fiche = document_de_maison(matiere, sans_routes.id)
    assert all(fiche['flux_30j'][champ] == 0 for champ in CHAMPS_KG)
    assert fiche['lieux'] == []
    vide = replace(matiere, greniers=matiere.greniers | {plausible.id: {}})
    fiche = document_de_maison(vide, plausible.id)
    assert fiche['grenier'] == {} and 'grenier' not in fiche['absents']
    assert liste_des_maisons(matiere)['nombre'] == len(monde.maisons)


def test_refus_sans_effet_et_tick_zero(service):
    _, port = service
    avant = _lire(port, '/monde')[1]
    statut, document, _ = requete_service(port, '/maison?id=maison-inconnue')
    assert statut == 404
    assert document == {'erreur': "maison inconnue : reçu 'maison-inconnue'"}
    for chemin, recu in (('/maison', None), ('/maison?id=', ''), ('/maison?id=a&id=b', ['a', 'b'])):
        statut, document, _ = requete_service(port, chemin)
        assert statut == 400
        assert document == {'erreur': f'paramètre id invalide : reçu {recu!r}, attendu un identifiant de maison'}
    assert _lire(port, '/monde')[1] == avant
    with _service_local() as (serveur, neuf):
        assert _lire(neuf, '/maisons')[0]['tick'] == 0
        assert _lire(neuf, _route(serveur.world.maisons[0].id))[0]['tick'] == 0


def _verifier_publication(document, attendu):
    for champ in ('grenier', 'part', 'flux_30j', 'tick'):
        assert document[champ] == attendu[champ]


def test_publication_figee_et_cache_a_la_demande(monkeypatch):
    import sim.service as module

    with _service_local() as (serveur, port):
        _preparer(serveur, port)
        origine = module.matiere_des_maisons
        for copie_correcte in (True, False):
            with monkeypatch.context() as patch:
                if not copie_correcte:
                    def partager(monde, noms, places):
                        return replace(origine(monde, noms, places), greniers=monde.greniers)
                    patch.setattr(module, 'matiere_des_maisons', partager)
                _lire(port, '/tick?n=1', 'POST')
                etat = serveur.etat_publie
                assert etat.octets_maisons == {}
                monde = serveur.world
                identifiant = monde.maison_du_joueur
                attendu = {'part': monde.parts[identifiant], 'grenier': dict(monde.greniers[identifiant]),
                           'flux_30j': flux_de_maison(monde, identifiant), 'tick': monde.ticks_ecoules}
                tenus = _tenus(monde, identifiant)
                attendu['flux_30j'].update({champ + '_personnes': sum(
                    flux_de_lieu(monde, cid, rang)[champ] for cid, rang in tenus)
                    for champ in ('partis', 'arrives')})
                panier = monde.greniers[identifiant]
                marchandise = next(iter(panier))
                panier[marchandise] += 1000
                monde.parts[identifiant] = 0.9
                indice = monde.routes_des_lieux.noms.index(identifiant)
                dernier = monde.flux.jours[max(monde.flux.jours)]
                dernier.preleve[indice] += 1
                # Même avec le verrou du tick pris, la première lecture doit répondre.
                with ThreadPoolExecutor(max_workers=1) as lecteur:
                    with serveur.verrou_tick:
                        document, octets = lecteur.submit(_lire, port, _route(identifiant)).result(timeout=5)
                if copie_correcte:
                    _verifier_publication(document, attendu)
                else:
                    with pytest.raises(AssertionError):
                        _verifier_publication(document, attendu)
                assert _lire(port, _route(identifiant))[1] == octets
                assert len(etat.octets_maisons) == 1
                _lire(port, '/maisons')
                assert len(etat.octets_maisons) == 2
                assert _lire(port, '/maisons')[0]['tick'] == attendu['tick']
                _lire(port, '/tick?n=1', 'POST')
                assert _lire(port, _route(identifiant))[0]['tick'] == attendu['tick'] + 1


def test_serialisation_unique_et_concurrente(service, monkeypatch):
    import sim.service as module

    serveur, port = service
    appels = {'document_de_maison': 0, 'liste_des_maisons': 0}
    for nom in appels:
        fonction = getattr(module, nom)

        def compter(*args, _nom=nom, _fonction=fonction):
            assert serveur.verrou_maisons.locked()
            appels[_nom] += 1
            return _fonction(*args)

        monkeypatch.setattr(module, nom, compter)
    serveur.etat_publie = serveur._construire_etat(0, -1)
    assert not any(appels.values())
    assert serveur.etat_publie.octets_maisons == {}
    route = _route(serveur.world.maisons[0].id)
    with ThreadPoolExecutor(max_workers=4) as lecteurs:
        reponses = list(lecteurs.map(lambda chemin: _lire(port, chemin), [route, '/maisons'] * 2))
    assert reponses[0][1] == reponses[2][1]
    assert reponses[1][1] == reponses[3][1]
    assert all(nombre == 1 for nombre in appels.values())
    assert len(serveur.etat_publie.octets_maisons) == 2


def _verifier_modele(texte):
    section = texte.split('## Les maisons servies, vue dérivée')[1].split('\n## ')[0]
    assert all(mot in section for mot in (
        '/maisons', '/maison?id=', '404', 'absents', 'EtatPublie', 'personnes', 'première lecture',
    ))


def test_modele_et_contre_epreuve():
    texte = (Path(__file__).parents[1] / 'MODELE.md').read_text(encoding='utf-8')
    _verifier_modele(texte)
    with pytest.raises(AssertionError):
        _verifier_modele(texte.replace('/maisons', ''))


def _verifier_photographie_documentee(texte):
    section = texte.split('## La photographie de 1400, vue dérivée')[1].split('\n## ')[0]
    assert '`maisons_du_joueur`' in section and '`document_de_maison`' in section
    assert "c'est sa seule différence" not in texte


def test_photographie_documentee():
    texte = (Path(__file__).parents[1] / 'MODELE.md').read_text(encoding='utf-8')
    _verifier_photographie_documentee(texte)
    with pytest.raises(AssertionError):
        _verifier_photographie_documentee(texte.replace('`maisons_du_joueur`', ''))


def test_maisons_du_joueur(monkeypatch):
    from sim import snapshot_export as module
    from sim.places import places_du_monde
    from sim.world import World

    monde = World.charger(0)
    noms, places = noms_depuis_monde(monde), places_du_monde(monde)
    appels = []
    def compter(*args):
        appels.append(args)
        return matiere_des_maisons(*args)
    monkeypatch.setattr(module, 'matiere_des_maisons', compter)
    assert module._maisons_du_joueur(monde, noms, places) is None
    assert not appels
    monde.maison_du_joueur = f'seigneurie-{charger_seigneuries()[0].id}'
    maison = next(m for m in monde.maisons if m.id == monde.maison_du_joueur)
    matiere = matiere_des_maisons(monde, noms, places)
    assert module._maisons_du_joueur(monde, noms, places) == {
        'maison': document_de_maison(matiere, maison.id),
        'suzerain': document_de_maison(matiere, maison.suzerain),
    }
    assert len(appels) == 1 and all(a is b for a, b in zip(appels[0], (monde, noms, places)))
    racine = next(m for m in monde.maisons if m.suzerain is None)
    monde.maison_du_joueur = racine.id
    assert module._maisons_du_joueur(monde, noms, places) == {
        'maison': document_de_maison(matiere, racine.id), 'suzerain': None,
    }
    inconnu = max(m.id for m in monde.maisons) + '-absent'
    monde.maison_du_joueur = maison.id
    monde.maisons = tuple(replace(m, suzerain=inconnu) if m.id == maison.id else m for m in monde.maisons)
    with pytest.raises(module.SnapshotExportError, match=f'maison inconnue : {inconnu}'):
        module._maisons_du_joueur(monde, noms, places)
    monde.maison_du_joueur = inconnu
    with pytest.raises(module.SnapshotExportError, match=f'maison inconnue : {inconnu}'):
        module._maisons_du_joueur(monde, noms, places)


def _verifier_egalite_photographie(document, fiches, octets):
    from sim.service import _serialiser
    assert document['tick'] == 35
    assert document['maisons_du_joueur'] == fiches
    for cle, fiche in document['maisons_du_joueur'].items():
        assert _serialiser(fiche) == octets[cle]


def _verifier_identite_photographie(document, joueur, suzerain):
    assert document['maisons_du_joueur']['maison']['id'] == joueur
    assert document['maisons_du_joueur']['suzerain']['id'] == suzerain


def _verifier_releve_photographie(document, releves):
    assert releves
    for fiche in document['maisons_du_joueur'].values():
        total = dict.fromkeys(CHAMPS_KG + ('partis_personnes', 'arrives_personnes'), 0)
        for kilos, partis, arrives in releves:
            for champ, nombre in zip(CHAMPS_KG, kilos[fiche['id']]):
                total[champ] += nombre
            for lieu in fiche['lieux']:
                cle = (lieu['cell_id'], lieu['rang'])
                total['partis_personnes'] += partis.get(cle, 0)
                total['arrives_personnes'] += arrives.get(cle, 0)
        for champ, nombre in total.items():
            assert fiche['flux_30j'][champ] == nombre, champ


def test_photographie_rejoue(tmp_path, monkeypatch):
    import subprocess
    import sys
    from sim import constants
    from sim.__main__ import _simulate
    from sim.snapshot_export import _round_tree, build_snapshot_document

    bar = next(s for s in charger_seigneuries() if s.nom == 'Duché de Bar')
    gestes, releves = [], []
    with _service_local() as (serveur, port):
        for t in range(35):
            intention = None
            if t == 0:
                intention = {'type': 'choisir_depart', 'seigneurie': bar.id}
            elif t == 1:
                joueur = serveur.world.maison_du_joueur
                assert joueur == f'seigneurie-{bar.id}'
                suzerain = next(m.suzerain for m in serveur.world.maisons if m.id == joueur)
                intention = {'type': 'fixer_part', 'maison': joueur, 'part': 0.25}
            elif t == 20:
                kg = int(serveur.world.greniers[joueur][constants.MARCHANDISE_NOURRITURE] // 2)
                assert kg > 0
                intention = {'type': 'ouvrir_grenier', 'maison': joueur, 'kg': kg}
            if intention is not None:
                gestes.append({'tick': t, 'intention': intention})
                _lire(port, '/intention', 'POST', intention)
            _lire(port, '/tick?n=1', 'POST')
            monde = serveur.world
            ids = (monde.maison_du_joueur, next(m.suzerain for m in monde.maisons if m.id == monde.maison_du_joueur))
            jour = monde.flux.jours[t]
            kilos = {identifiant: tuple(getattr(jour, champ)[monde.routes_des_lieux.noms.index(identifiant)]
                                       for champ in ('preleve', 'recu', 'du', 'mange', 'rendu')) for identifiant in ids}
            releves.append((kilos, dict(jour.partis), dict(jour.arrives)))
        servis = {cle: _lire(port, _route(identifiant)) for cle, identifiant in (('maison', joueur), ('suzerain', suzerain))}
        fiches, octets = ({cle: valeur[i] for cle, valeur in servis.items()} for i in (0, 1))
        assert all(fiches['maison']['flux_30j'][champ] > 0 for champ in CHAMPS_KG)
        assert fiches['maison']['flux_30j']['rendu_kg'] == kg
        assert fiches['maison']['part'] == 0.25
        assert fiches['maison']['grenier'] == monde.greniers[joueur]
        assert fiches['suzerain']['flux_30j']['recu_kg'] > 0
        assert sum(f['flux_30j'][c] for f in fiches.values() for c in ('partis_personnes', 'arrives_personnes')) > 0
        assert releves[4][0][joueur][0] > 0
    fichier, sortie = tmp_path / 'gestes.json', tmp_path / 'photographie.json'
    fichier.write_text(json.dumps(gestes), encoding='utf-8')
    resultat = subprocess.run([sys.executable, '-m', 'sim', '--ticks', '35', '--seed', '0',
                              '--gestes', str(fichier), '--snapshot-json', str(sortie)],
                              cwd=Path(__file__).parents[2], capture_output=True, text=True)
    assert resultat.returncode == 0, resultat.stderr
    document = json.loads(sortie.read_text(encoding='utf-8'))
    _verifier_egalite_photographie(document, fiches, octets)
    _verifier_identite_photographie(document, joueur, suzerain)
    _verifier_releve_photographie(document, releves[5:])
    faux = copy.deepcopy(document)
    faux['maisons_du_joueur']['maison']['flux_30j']['rendu_kg'] += 1
    arrondi = copy.deepcopy(document)
    arrondi['maisons_du_joueur'] = _round_tree(fiches)
    assert arrondi != document
    for altere in (faux, arrondi):
        with pytest.raises(AssertionError):
            _verifier_egalite_photographie(altere, fiches, octets)
    inverse = document | {'maisons_du_joueur': {'maison': fiches['suzerain'], 'suzerain': fiches['maison']}}
    with pytest.raises(AssertionError):
        _verifier_identite_photographie(inverse, joueur, suzerain)
    with pytest.raises(AssertionError, match='preleve_kg'):
        _verifier_releve_photographie(document, releves[6:])
    with monkeypatch.context() as patch:
        patch.setattr(constants, 'FENETRE_FLUX_TICKS', 31)
        _, monde = _simulate(35, 0, gestes)
        trop_long = build_snapshot_document(monde, 0, 35)
    with pytest.raises(AssertionError, match='preleve_kg'):
        _verifier_releve_photographie(trop_long, releves[5:])


@pytest.mark.chronometre
def test_mesure_matiere_et_publication(capsys):
    with _service_local() as (serveur, port):
        _preparer(serveur, port, jours=34)
        assert serveur.world.ticks_ecoules == 35
        mesures = {}
        for nom, fonction in (
            ('matiere_des_maisons', lambda: matiere_des_maisons(serveur.world, serveur._noms, serveur._places_des_lieux())),
            ('_construire_etat', lambda: serveur._construire_etat(0, -1)),
        ):
            durees = []
            for _ in range(9):
                debut = time.perf_counter()
                fonction()
                durees.append((time.perf_counter() - debut) * 1000)
            mesures[nom] = statistics.median(durees)
        with capsys.disabled():
            print(f'Médianes au tick 35 (ms) : {mesures}')
        assert not serveur.etat_publie.octets_maisons
