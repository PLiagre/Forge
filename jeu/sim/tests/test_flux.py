"""Les mesures des circulations restent exactes et sans effet sur le monde."""
import copy
import json
import random
import statistics
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from sim import constants as c, engine, prelevement, departs
from sim.flux import Flux, jour_courant, noter_personnes, flux_de_maison, flux_de_lieu
from sim import flux
from sim.convois import TableRoutes
from sim.intentions import recevoir_intention, IntentionRefusee
from sim.tests.test_commerce import _cellule_bourg
from sim.world import World


@pytest.fixture(scope='module')
def monde():
    return World.charger(0)


def _jouer(monde, nombre):
    rng = random.Random(0)
    for _ in range(nombre):
        engine.tick(monde, rng)


def _petit():
    m = World({1: _cellule_bourg(1, [5000, 2500], [350000., 0.])}, [])
    m.maisons = (SimpleNamespace(id='a'),)
    m.routes_des_lieux = TableRoutes([(1, r, 'a', 1, 0, 1) for r in range(2)])
    m.parts, m.greniers = {'a': .5}, {'a': {}}
    return m


def _controler_preleve(m):
    noms = m.routes_des_lieux.noms
    lieux = {nom: [] for nom in noms}
    for cid, (indices, _) in m.routes_des_lieux.par_cellule.items():
        for rang, indice in enumerate(indices):
            if indice >= 0:
                lieux[noms[indice]].append(flux_de_lieu(m, cid, rang)['preleve_kg'])
    assert any(flux_de_maison(m, nom)['preleve_kg'] > 0 for nom in noms)
    for nom in noms:
        assert sum(lieux[nom]) == pytest.approx(flux_de_maison(m, nom)['preleve_kg'], rel=1e-12)


@pytest.fixture(scope='module')
def course(monde):
    m, rng, hausses = copy.deepcopy(monde), random.Random(0), {}
    noms = m.routes_des_lieux.noms
    with pytest.MonkeyPatch.context() as ctx:
        ctx.setattr(c, 'PERTE_GRENIER_PAR_AN', 0)
        for tick in range(35):
            stocks = [m.greniers[n].get(c.MARCHANDISE_NOURRITURE, 0) for n in noms]
            charge = sum(kg for _, _, kg in prelevement.charges_en_route(m))
            mange = m.mange_convois_kg
            engine.tick(m, rng)
            jour = m.flux.jours[tick]
            hausses[tick] = [m.greniers[n].get(c.MARCHANDISE_NOURRITURE, 0) - s
                             for n, s in zip(noms, stocks)]
            assert sum(jour.mange) == pytest.approx(m.mange_convois_kg - mange, rel=1e-9)
            assert sum(jour.preleve) == pytest.approx(
                sum(kg for _, _, kg in prelevement.charges_en_route(m)) - charge
                + sum(jour.recu) + m.mange_convois_kg - mange, rel=1e-9)
            for i, route in enumerate(m.dus_des_vassaux.par_indice):
                if route is not None:
                    assert jour.du[i] == pytest.approx(
                        c.PART_DUE_AU_SUZERAIN / (1-c.PART_DUE_AU_SUZERAIN) * jour.recu[i], rel=1e-9)
    return m, hausses


def test_preleve_des_lieux_et_contre_epreuve(course):
    m, _ = course
    _controler_preleve(m)
    faux = copy.deepcopy(m)
    next(iter(faux.flux.jours.values())).preleve[0] += 1
    with pytest.raises(AssertionError):
        _controler_preleve(faux)


def _controler_en_route(m):
    charges = dict.fromkeys(m.routes_des_lieux.noms, 0.)
    for nom, _, kg in prelevement.charges_en_route(m):
        charges[nom] += kg
    assert list(m.flux.en_route) == pytest.approx(list(charges.values()), rel=1e-9)


def test_compteurs_mesures_independantes_et_du(course):
    m, hausses = course
    debut = m.ticks_ecoules - c.FENETRE_FLUX_TICKS
    for i, nom in enumerate(m.routes_des_lieux.noms):
        assert flux_de_maison(m, nom)['recu_kg'] == pytest.approx(
            sum(h[i] for tick, h in hausses.items() if tick >= debut), rel=1e-9)
    assert sum(flux_de_maison(m, n)['du_envoye_kg'] for n in m.routes_des_lieux.noms) > 0
    _controler_en_route(m)
    faux = copy.deepcopy(m)
    indice, kg = next((route[0], jour.du[i] * (1-c.PERTE_CONVOI_PAR_JOUR) **
                       (m.ticks_ecoules - 1 - jour.tick))
                      for jour in m.flux.jours.values()
                      for i, route in enumerate(m.dus_des_vassaux.par_indice)
                      if route is not None and jour.du[i] > 0
                      and jour.tick + route[1] >= m.ticks_ecoules)
    faux.flux.en_route[indice] -= kg
    with pytest.raises(AssertionError):
        _controler_en_route(faux)


def test_fenetre_trentieme_et_trente_et_unieme_jour(monkeypatch, monde):
    m = _petit()
    recoltes = {1: [10., 20.]}
    prelevement.prelever(m, recoltes)
    assert m.flux.jours[0].taux == [.5]
    assert m.flux.jours[0].recoltes is recoltes
    assert departs.appliquer_departs(m) > 0
    m.parts['a'] = 0
    m.ticks_ecoules = 1
    prelevement.prelever(m, {1: [0., 0.]})
    m.ticks_ecoules = 30
    assert flux_de_maison(m, 'a')['preleve_kg'] == 15
    assert flux_de_lieu(m, 1, 1)['partis'] > 0
    assert flux_de_lieu(m, 1, 0)['arrives'] > 0
    m.ticks_ecoules = 31
    def controler():
        assert flux_de_maison(m, 'a')['preleve_kg'] == 0
        assert flux_de_lieu(m, 1, 1) == {'preleve_kg': 0, 'partis': 0, 'arrives': 0}
        assert flux_de_lieu(m, 1, 0) == {'preleve_kg': 0, 'partis': 0, 'arrives': 0}
    controler()
    with monkeypatch.context() as ctx:
        ctx.setattr(c, 'FENETRE_FLUX_TICKS', 31)
        with pytest.raises(AssertionError): controler()
    with monkeypatch.context() as ctx:
        ctx.setattr(flux, '_jours_de_fenetre', lambda monde: monde.flux.jours.values())
        with pytest.raises(AssertionError): controler()
    reel = copy.deepcopy(monde)
    _jouer(reel, 40)
    assert len(reel.flux.jours) <= c.FENETRE_FLUX_TICKS


def test_departs_bruts_et_solde_contre_epreuve():
    m = World({1: _cellule_bourg(1, [5000, 2500], [350000., 0.]),
               2: _cellule_bourg(2, [1000], [140000.])}, [{'a': 1, 'b': 2}])
    avant = {(cid, l.rang): l.population for cid, cell in m.cells.items() for l in cell.lieux}
    total = departs.appliquer_departs(m)
    def controler():
        assert total == 15
        assert flux_de_lieu(m, 1, 1)['partis'] == 5
        assert flux_de_lieu(m, 1, 0)['partis'] == 10
        assert flux_de_lieu(m, 1, 0)['arrives'] == 5
        assert flux_de_lieu(m, 2, 0)['arrives'] == 10
        assert sum(flux_de_lieu(m, *cle)['partis'] for cle in avant) == total
        for (cid, rang), population in avant.items():
            f = flux_de_lieu(m, cid, rang)
            assert f['arrives'] - f['partis'] == m.cells[cid].lieux[rang].population - population
        assert [m.cells[cid].lieux[rang].population for cid, rang in [(1, 1), (1, 0), (2, 0)]] == [2495, 4995, 1010]
    controler()
    m.flux.jours[0].partis[(1, 0)] = 5
    m.flux.jours[0].arrives[(1, 0)] = 0
    with pytest.raises(AssertionError): controler()


def test_migration_famine_et_absence_de_depart():
    m = World({1: _cellule_bourg(1, [150, 250, 100], [0., 20., 0.], (0, 1)),
               2: _cellule_bourg(2, [10, 20], [100., 0.])}, [{'a': 1, 'b': 2}])
    avant = copy.deepcopy(m)
    engine._apply_migration(m, {1: 1.})
    assert m.cells[2].population > avant.cells[2].population
    for cid, cell in m.cells.items():
        for l in cell.lieux:
            f = flux_de_lieu(m, cid, l.rang)
            delta = l.population - avant.cells[cid].lieux[l.rang].population
            assert f['arrives'] == max(0, delta)
            assert f['partis'] == max(0, -delta)
    sans_lieux = World({1: _cellule_bourg(1, [1000], [0.]),
                        2: _cellule_bourg(2, [10], [1000.])}, [{'a': 1, 'b': 2}])
    for cell in sans_lieux.cells.values():
        cell.lieux = []
    engine._apply_migration(sans_lieux, {1: 1.})
    assert sans_lieux.cells[1].population < 1000
    assert not sans_lieux.flux.jours
    vide = World({1: _cellule_bourg(1, [10], [0.])}, [])
    assert departs.appliquer_departs(vide) == 0
    engine._apply_migration(vide, {})
    noter_personnes(vide, {}, {})
    assert not vide.flux.jours
    fortune = SimpleNamespace()
    assert jour_courant(fortune) is None
    noter_personnes(fortune, {(1, 0): 5}, {})


def test_ouverture_secours_refus_et_maisons_absentes(monde):
    m = copy.deepcopy(monde)
    m.greniers['seigneurie-1'][c.MARCHANDISE_NOURRITURE] = 1000.
    sans = copy.deepcopy(m)
    with pytest.raises(IntentionRefusee):
        recevoir_intention(m, {'type': 'ouvrir_grenier', 'maison': 'seigneurie-1', 'kg': 1001})
    assert m.flux == sans.flux == Flux()
    recevoir_intention(m, {'type': 'ouvrir_grenier', 'maison': 'seigneurie-1', 'kg': 400})
    rng, rng_sans = random.Random(0), random.Random(0)
    engine.tick(m, rng); engine.tick(sans, rng_sans)
    assert flux_de_maison(m, 'seigneurie-1')['rendu_kg'] == 400
    limite = max(m.secours, default=0)
    while m.ticks_ecoules <= limite:
        engine.tick(m, rng); engine.tick(sans, rng_sans)
    assert not m.secours
    assert flux_de_maison(m, 'seigneurie-1')['mange_en_route_kg'] > flux_de_maison(sans, 'seigneurie-1')['mange_en_route_kg']
    absent = next(maison.id for maison in m.maisons if maison.id not in m.routes_des_lieux.noms)
    assert list(flux_de_maison(m, absent).values()) == [0] * 5
    with pytest.raises(ValueError, match='inconnue'):
        flux_de_maison(m, 'inconnue')
    with pytest.raises(ValueError): flux_de_lieu(m, -1, 0)
    with pytest.raises(ValueError): flux_de_lieu(m, next(iter(m.cells)), -1)


def test_egalite_vecteurs_extension_et_lecture_sans_route():
    m = _petit()
    jour = jour_courant(m)
    assert jour_courant(m) is jour
    assert m.flux == copy.deepcopy(m.flux)
    noter_personnes(m, {(1, 0): 5}, {(1, 1): 5})
    noter_personnes(m, {(1, 0): 5}, {})
    assert flux_de_lieu(m, 1, 0)['partis'] == 10
    m.routes_des_lieux.noms.append('b')
    assert jour_courant(m) is jour
    assert all(len(getattr(jour, n)) == 2 for n in ('preleve', 'recu', 'du', 'mange', 'rendu'))
    assert list(m.flux.en_route) == [0., 0.]
    m.routes_des_lieux = {}
    assert flux_de_lieu(m, 1, 0)['preleve_kg'] == 0


def _controler_neutralite(base):
    a, b = copy.deepcopy(base), copy.deepcopy(base)
    ra, rb = random.Random(0), random.Random(0)
    for _ in range(40):
        engine.tick(a, ra); engine.tick(b, rb)
        b.flux = Flux()
    octets = lambda m: json.dumps(m.to_dict(), sort_keys=True).encode()
    assert octets(a) == octets(b)
    assert 'flux' not in octets(a).decode()


def test_neutralite_empreintes_et_contre_epreuve(monde, monkeypatch):
    _controler_neutralite(monde)
    ancien = prelevement.prelever
    def mauvais(m, recoltes):
        if any(any(j.preleve) for j in m.flux.jours.values()):
            m.parts = {n: part * 2 for n, part in m.parts.items()}
        ancien(m, recoltes)
    with monkeypatch.context() as ctx:
        ctx.setattr(prelevement, 'prelever', mauvais)
        with pytest.raises(AssertionError): _controler_neutralite(monde)


def _mesurer(base):
    m, rng, durees, etapes = copy.deepcopy(base), random.Random(0), [], []
    ancien = prelevement.prelever
    def observer(*args):
        debut = time.perf_counter(); ancien(*args)
        etapes.append((time.perf_counter() - debut) * 1000)
    with pytest.MonkeyPatch.context() as ctx:
        ctx.setattr(prelevement, 'prelever', observer)
        for numero in range(25):
            debut = time.perf_counter(); engine.tick(m, rng, numero)
            if numero >= 5: durees.append((time.perf_counter() - debut) * 1000)
    assert len(durees) == 20 and len(m.flux.jours) >= 20
    assert any(any(j.preleve) for j in m.flux.jours.values())
    assert any(any(j.mange) for j in m.flux.jours.values())
    mediane = statistics.median(durees)
    print(f'flux : médiane tick={mediane:.3f} ms ; prélèvement={statistics.median(etapes[5:]):.3f} ms')
    from sim.service import BUDGET_TICK_MS
    assert mediane < BUDGET_TICK_MS


@pytest.mark.chronometre
def test_budget_flux_et_contre_epreuve(monde, monkeypatch):
    from sim.service import BUDGET_TICK_MS
    _mesurer(monde)
    ancien = flux.jour_courant
    def lent(m):
        time.sleep(BUDGET_TICK_MS / 1000)
        return ancien(m)
    with monkeypatch.context() as ctx:
        ctx.setattr(flux, 'jour_courant', lent)
        with pytest.raises(AssertionError): _mesurer(monde)


def test_documentation_et_contre_epreuve():
    texte = (Path(__file__).parents[1] / 'MODELE.md').read_text(encoding='utf-8')
    titre = '## Les flux sur trente jours'
    def controler(document):
        section = document.split(titre)[1].split('\n## ')[0]
        assert all(mot in section for mot in ('FENETRE_FLUX_TICKS', 'to_dict', 'aucune règle', 'en_route', 'ms'))
    controler(texte)
    avant, apres = texte.split(titre)
    prive = avant + '\n## ' + apres.split('\n## ', 1)[1]
    with pytest.raises((AssertionError, IndexError)): controler(prive)


def test_ouverture_cherche_indice_une_seule_fois():
    from sim.intentions import OuvrirGrenier

    class NomsComptes(list):
        recherches = 0

        def index(self, nom):
            self.recherches += 1
            return super().index(nom)

    m = _petit()
    m.routes_des_lieux.noms = NomsComptes(m.routes_des_lieux.noms)
    m.greniers['a'][c.MARCHANDISE_NOURRITURE] = 1000.
    OuvrirGrenier('a', 400).appliquer(m)
    assert m.routes_des_lieux.noms.recherches == 1
    assert flux_de_maison(m, 'a')['rendu_kg'] == 400
    assert sum(sum(charges.values()) for charges in m.secours.values()) == 400



def test_flux_des_lieux_mesures_et_contre_epreuves(monde, monkeypatch):
    m, releves, rng = copy.deepcopy(monde), {}, random.Random(0)
    noter = flux.noter_personnes
    def observer(m, partis, arrives):
        jour = releves.setdefault(m.ticks_ecoules, ({}, {}))
        for source, cible in zip((partis, arrives), jour):
            for cle, nombre in source.items(): cible[cle] = cible.get(cle, 0) + nombre
        noter(m, partis, arrives)
    with monkeypatch.context() as ctx:
        ctx.setattr(flux, 'noter_personnes', observer)
        for _ in range(35): engine.tick(m, rng)
    debut = m.ticks_ecoules - c.FENETRE_FLUX_TICKS
    attendus = ({}, {})
    for tick, mouvements in releves.items():
        if tick >= debut:
            for source, cible in zip(mouvements, attendus):
                for cle, nombre in source.items(): cible[cle] = cible.get(cle, 0) + nombre
    assert 0 not in m.flux.jours and attendus[0] and attendus[1]
    def verifier(monde, egalite=True):
        vue = flux.flux_des_lieux(monde)
        assert set(vue) == set(monde.cells)
        sommes = dict.fromkeys(monde.routes_des_lieux.noms, 0.)
        nombre = 0
        for cid, cellule in monde.cells.items():
            assert len(vue[cid]) == len(cellule.lieux)
            for lieu in cellule.lieux:
                f = vue[cid][lieu.rang]; nombre += 1
                assert type(f['preleve_kg']) is float
                if egalite: assert f == flux_de_lieu(monde, cid, lieu.rang)
                assert [f['partis'], f['arrives']] == [a.get((cid, lieu.rang), 0) for a in attendus]
                indices = monde.routes_des_lieux.par_cellule.get(cid)
                if indices and indices[0][lieu.rang] >= 0:
                    sommes[monde.routes_des_lieux.noms[indices[0][lieu.rang]]] += f['preleve_kg']
        assert nombre == sum(len(cell.lieux) for cell in monde.cells.values()) > 0
        assert any(sommes.values())
        for nom, kg in sommes.items(): assert kg == pytest.approx(flux_de_maison(monde, nom)['preleve_kg'], rel=1e-12)
    verifier(m)
    with monkeypatch.context() as ctx:
        ctx.setattr(c, 'FENETRE_FLUX_TICKS', 29)
        with pytest.raises(AssertionError): verifier(m)
    faux = copy.deepcopy(m)
    jour = next(j for j in faux.flux.jours.values() if any(j.preleve))
    indice = next(i for i, kg in enumerate(jour.preleve) if kg > 0)
    jour.taux[indice] *= 2
    with pytest.raises(AssertionError): verifier(faux)
    jours = flux._jours_de_fenetre
    with monkeypatch.context() as ctx:
        ctx.setattr(flux, '_jours_de_fenetre', lambda m: [j for j in jours(m) for _ in range(2)])
        with pytest.raises(AssertionError): verifier(m, egalite=False)
    fortune = SimpleNamespace(cells=m.cells, ticks_ecoules=0)
    assert all(f == {'preleve_kg': 0., 'partis': 0, 'arrives': 0} and type(f['preleve_kg']) is float
               for lignes in flux.flux_des_lieux(fortune).values() for f in lignes)


def test_flux_des_lieux_documentation():
    texte = (Path(__file__).parents[1] / 'MODELE.md').read_text()
    section = texte.split('## Les flux sur trente jours')[1].split('\n## ')[0]
    assert 'flux_des_lieux' in section
