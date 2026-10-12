"""La part récoltée quitte les lieux, voyage et remplit réellement le grenier."""
import ast
import copy
import json
import pickle
import random
import re
import time
from pathlib import Path

import pytest
from sim import constants as c, engine, prelevement
from sim.model import Cell, EtatDeLieu
from sim.world import World
from sim.tests.test_convois import _importe_convois, _section_prelevement
from sim.tests.test_maisons import _tick_sans_lecture_registre

SIM = Path(__file__).resolve().parents[1]
BAR = 'seigneurie-1'


def test_groupes_arrivee_egalite_de_l_etat():
    """Une copie du monde compare les charges, sans dépendre de leur identité."""
    groupe = prelevement.GroupeArrivee(2)
    groupe.charges[0] = 5.0
    groupe.total = 5.0
    copie = copy.deepcopy(groupe)
    assert copie is not groupe and copie.charges is not groupe.charges
    assert copie == groupe
    for champ in ('facteur', 'total'):
        different = copy.deepcopy(groupe)
        setattr(different, champ, getattr(different, champ) + 1)
        assert different != groupe
    copie.charges[1] = 1.0
    assert copie != groupe
    assert groupe != object()


@pytest.mark.parametrize('nombre_lieux', [1, 2])
@pytest.mark.parametrize('stock_initial', [None, 0.0, 50.0])
def test_paniers_production_puis_prelevement(nombre_lieux, stock_initial):
    """Les paniers absents, nuls et pleins suivent le même chemin du modèle."""
    from sim.convois import TableRoutes
    from sim.model import copier_panier, lire_stock_marchandise
    nourriture = c.MARCHANDISE_NOURRITURE
    objet = c.MARCHANDISE_OBJET
    panier = {objet: 7.0}
    if stock_initial is not None:
        panier[nourriture] = stock_initial
    cellule = Cell(1, c.SURFACE_KM2_PAR_LIEU * nombre_lieux, 10 * nombre_lieux,
                   stocks={k: v * nombre_lieux for k, v in panier.items()},
                   lieux=[EtatDeLieu(rang, 10, dict(panier))
                          for rang in range(nombre_lieux)])
    m = World({1: cellule}, [])
    m.routes_des_lieux = TableRoutes([
        (1, lieu.rang, 'a', 1, 0, 1) for lieu in cellule.lieux
    ])
    m.parts = {'a': 0.5}
    m.greniers = {'a': {}}
    recoltes = {}
    engine._apply_production(cellule, random.Random(0), recoltes=recoltes)
    prelevement.prelever(m, recoltes)
    base = 0.0 if stock_initial is None else stock_initial
    attendu = [base + kg * (1 - m.parts['a']) for kg in recoltes[1]]
    assert recoltes[1] and all(kg > 0 for kg in recoltes[1])
    assert [copier_panier(lieu) for lieu in cellule.lieux] == [
        {objet: panier[objet], nourriture: kg} for kg in attendu
    ]
    assert lire_stock_marchandise(cellule, nourriture) == pytest.approx(sum(attendu))
    assert lire_stock_marchandise(cellule, objet) == panier[objet] * nombre_lieux
    assert _route(m) == pytest.approx(sum(recoltes[1]) * m.parts['a'])


@pytest.fixture(scope='module')
def monde():
    return World.charger(0)


def _food(panier):
    return panier.get(c.MARCHANDISE_NOURRITURE, 0.0)


def _route(m):
    return sum(kg for _, _, kg in prelevement.charges_en_route(m)) if m.convois else 0.0


def _greniers(m):
    return sum(_food(p) for p in m.greniers.values())


def _total(m):
    return sum(_food(cell.stocks) for cell in m.cells.values()) + _route(m) + _greniers(m) + m.mange_convois_kg + m.pertes_kg


def _stocks(m):
    return {cid: (_food(cell.stocks), sum(_food(l.stocks) for l in cell.lieux)) for cid, cell in m.cells.items()}


def _egalite(avant, apres):
    assert avant and avant.keys() == apres.keys()
    for cid, (cell, lieux) in avant.items():
        a, b = apres[cid]
        assert cell - a == pytest.approx(lieux - b, rel=1e-9, abs=1e-8)


def _jouer(m, jours):
    rng = random.Random(0)
    for _ in range(jours):
        engine.tick(m, rng, m.ticks_ecoules)


def test_conservation_sur_un_an(monde, monkeypatch):
    m = copy.deepcopy(monde)
    original = prelevement.prelever
    preleves = arrives = duree = 0.0
    nombre = 0
    def observer(m, recoltes):
        nonlocal preleves, arrives, nombre, duree
        avant, stocks, grenier = _total(m), _stocks(m), _greniers(m)
        nombre += sum(1 for _, t, _ in prelevement.charges_en_route(m) if t == m.ticks_ecoules) if m.convois else 0
        debut = time.perf_counter()
        original(m, recoltes)
        duree += time.perf_counter() - debut
        assert _total(m) == pytest.approx(avant, rel=1e-12)
        apres = _stocks(m)
        _egalite(stocks, apres)
        preleves += sum(stocks[cid][0] - apres[cid][0] for cid in stocks)
        arrives += _greniers(m) - grenier
    monkeypatch.setattr(prelevement, 'prelever', observer)
    _jouer(m, c.CALENDAR_DAYS_PER_YEAR)
    assert preleves == pytest.approx(arrives + _route(m) + m.mange_convois_kg, rel=1e-12)
    assert arrives == pytest.approx(_greniers(m) + m.pertes_kg, rel=1e-12)
    assert preleves > 0 and nombre > 0 and m.mange_convois_kg > 0
    print(f'prélevé={preleves}, arrivé={arrives}, arrivées={nombre}, mangé={m.mange_convois_kg}, étape={duree * 1000 / m.ticks_ecoules:.3f} ms')
    def faux_prelevement(m, recoltes, rendre_lieux):
        avant = {cid: (dict(cell.stocks), [dict(l.stocks) for l in cell.lieux]) for cid, cell in m.cells.items()}
        original(m, recoltes)
        for cid, (stocks, lieux) in avant.items():
            m.cells[cid].stocks = stocks
            if rendre_lieux:
                for lieu, panier in zip(m.cells[cid].lieux, lieux): lieu.stocks = panier
    recoltes = {cid: [1.0] * len(cell.lieux) for cid, cell in monde.cells.items()}
    faux = copy.deepcopy(monde); avant = _total(faux)
    faux_prelevement(faux, recoltes, True)
    assert faux.convois
    with pytest.raises(AssertionError): assert _total(faux) == pytest.approx(avant, rel=1e-12)
    faux = copy.deepcopy(monde); stocks = _stocks(faux)
    faux_prelevement(faux, recoltes, False)
    with pytest.raises(AssertionError): _egalite(stocks, _stocks(faux))


def test_charge_et_jours_de_bar(monde, monkeypatch):
    monkeypatch.setattr(c, 'PERTE_GRENIER_PAR_AN', 0)
    original = prelevement.prelever
    lieux = [(cid, rang, route.jours) for (cid, rang), route in monde.routes_des_lieux.items() if route.maitre == BAR]
    assert lieux and len({j for _, _, j in lieux}) > 1
    def course(perte):
        m = copy.deepcopy(monde)
        m.parts = dict.fromkeys(m.parts, 0.0); m.parts[BAR] = 0.5
        kg = {}
        def observer(m, recoltes):
            avant = {(cid, rang): dict(m.cells[cid].lieux[rang].stocks) for cid, rang, _ in lieux}
            original(m, recoltes)
            for cid, rang, _ in lieux:
                apres = m.cells[cid].lieux[rang].stocks
                if m.ticks_ecoules == 0: kg[cid, rang] = _food(avant[cid, rang]) - _food(apres)
                assert {k: v for k, v in avant[cid, rang].items() if k != c.MARCHANDISE_NOURRITURE} == {k: v for k, v in apres.items() if k != c.MARCHANDISE_NOURRITURE}
        monkeypatch.setattr(prelevement, 'prelever', observer)
        monkeypatch.setattr(c, 'PERTE_CONVOI_PAR_JOUR', perte)
        _jouer(m, 1); m.parts[BAR] = 0
        rng = random.Random(0)
        for t in range(1, max(j for _, _, j in lieux) + 1):
            engine.tick(m, rng, t)
            attendu = sum(kg[cid, rang] * (1 - perte)**j for cid, rang, j in lieux if j <= t)
            assert _food(m.greniers[BAR]) == pytest.approx(attendu, rel=1e-12)
            if t == min(j for _, _, j in lieux): assert attendu != pytest.approx(sum(kg.values()))
        assert all(nom != BAR for nom, _, _ in prelevement.charges_en_route(m))
        return _food(m.greniers[BAR]), sum(kg.values())
    perte = c.PERTE_CONVOI_PAR_JOUR
    normal, total = course(perte)
    sans, brut = course(0)
    assert sans == pytest.approx(brut, rel=1e-12) and normal < sans
    print(f'Bar : prélevé={total}, reçu={normal}, sans perte={sans}')


def test_part_forte_et_part_egale(monde):
    def course(part):
        m = copy.deepcopy(monde); m.parts[BAR] = part
        _jouer(m, 30)
        return _food(m.greniers[BAR]), [_food(m.cells[cid].lieux[rang].stocks) for (cid, rang), route in m.routes_des_lieux.items() if route.maitre == BAR]
    faible, lieux = course(c.PART_COUTUMIERE)
    fort, affaiblis = course(c.PART_COUTUMIERE * 10)
    assert fort > faible and lieux and all(a < b for a, b in zip(affaiblis, lieux))
    assert course(c.PART_COUTUMIERE) == (faible, lieux)
    print(f'grenier supplémentaire={fort-faible}, écarts lieux={[b-a for a,b in zip(affaiblis,lieux)]}')


def test_part_nulle_octets_et_monde_epreuve(monde, monkeypatch):
    def octets(m): return json.dumps(m.to_dict(), sort_keys=True), pickle.dumps(m.cells)
    with monkeypatch.context() as ctx:
        ctx.setattr(c, 'PART_COUTUMIERE', 0)
        normal = World.charger(0); temoin = copy.deepcopy(normal)
        _jouer(normal, 30)
        ctx.setattr(prelevement, 'prelever', lambda *_: None)
        _jouer(temoin, 30)
        assert octets(normal) == octets(temoin)
        assert not {'convois', 'mange_convois_kg', 'parts'} & normal.to_dict().keys()
    actif = copy.deepcopy(monde); actif.parts[BAR] = c.PART_COUTUMIERE * 2
    _jouer(actif, 30)
    assert {'convois', 'mange_convois_kg', 'parts'} <= actif.to_dict().keys()
    assert octets(actif) != octets(normal)
    epreuve = World({1: Cell(1, 1.0, 1)}, [])
    _jouer(epreuve, 2)
    assert epreuve.convois == {} and epreuve.mange_convois_kg == 0
    repos = copy.deepcopy(monde); avant = octets(repos)
    prelevement.prelever(repos, {cid: [0.0] * len(cell.lieux) for cid, cell in repos.cells.items()})
    assert octets(repos) == avant and repos.convois == {} and repos.mange_convois_kg == 0
    print(f'octets comparés={sum(len(o) for o in octets(normal))}')


def _lectures(texte, noms):
    return [n.attr for n in ast.walk(ast.parse(texte)) if isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Load) and n.attr in noms]


def test_tick_sans_maitre_ni_registre(monde, monkeypatch):
    source = (SIM / 'engine.py').read_text()
    assert not _importe_convois(source)
    assert not _lectures(source, {'routes_des_lieux', 'PERTE_CONVOI_PAR_JOUR', 'PART_COUTUMIERE'})
    assert not _lectures((SIM / 'prelevement.py').read_text(), {'maitre', 'maisons'})
    assert _lectures('lieu.maitre', {'maitre'})
    m = copy.deepcopy(monde)
    def leve(_): raise RuntimeError('maître lu')
    monkeypatch.setattr(EtatDeLieu, 'maitre', property(leve))
    for _ in range(3): _tick_sans_lecture_registre(monkeypatch, m, engine.tick, m.ticks_ecoules)
    assert m.convois and m.mange_convois_kg > 0
    print(f'groupes après trois ticks={len(m.convois)}')


def test_modele_et_notices():
    texte = (SIM / 'MODELE.md').read_text()
    section = _section_prelevement(texte)
    for terme in ('PERTE_CONVOI_PAR_JOUR', 'mange_convois_kg', 'World.convois', '(1 − PERTE_CONVOI_PAR_JOUR)^jours', 'PART_COUTUMIERE', 'niveau 2', 'niveau 3', 'ms'):
        assert terme in section
    page = texte.split('## En une page', 1)[1].split('\n## ', 1)[0]
    rangs = {nom: int(rang) for rang, nom in re.findall(r'^([0-9]+)\. \*\*([^*]+)\*\*', page, re.M)}
    assert rangs['Production'] + 1 == rangs['Prélèvement'] == rangs['Commerce'] - 1
    assert 'sim/prelevement.py' in (SIM / 'README.md').read_text()
    assert 'test_prelevement.py' in (SIM / 'tests/README.md').read_text()
    with pytest.raises(AssertionError): _section_prelevement('')
    print(f'taille de la section={len(section)}')


def test_arrivee_commune_de_departs_d_ages_differents(monkeypatch):
    """Le facteur du groupe ne vieillit pas prématurément les nouvelles charges."""
    from sim.convois import TableRoutes
    nourriture = c.MARCHANDISE_NOURRITURE
    cellule = Cell(1, 2.0, 0, stocks={nourriture: 100.0}, lieux=[
        EtatDeLieu(0, 0, {nourriture: 50.0}),
        EtatDeLieu(1, 0, {nourriture: 50.0}),
    ])
    m = World({1: cellule}, [])
    m.routes_des_lieux = TableRoutes([
        (1, 0, 'a', 1, 0, 2), (1, 1, 'b', 1, 1, 1),
    ])
    m.parts = {'a': 0.5, 'b': 0.0}
    m.greniers = {'a': {}, 'b': {}}
    monkeypatch.setattr(c, 'PERTE_CONVOI_PAR_JOUR', 0.1)
    prelevement.prelever(m, {1: [10.0, 0.0]})
    m.ticks_ecoules = 1
    m.parts = {'a': 0.0, 'b': 0.25}
    prelevement.prelever(m, {1: [0.0, 12.0]})
    assert prelevement.charges_en_route(m) == [['a', 2, 4.5], ['b', 2, 3.0]]
    m.ticks_ecoules = 2
    monkeypatch.setattr(c, 'PERTE_CONVOI_PAR_JOUR', 0.2)
    prelevement.prelever(m, {})
    assert not m.convois
    assert _food(m.greniers['a']) == pytest.approx(5.0 * 0.9 * 0.8)
    assert _food(m.greniers['b']) == pytest.approx(3.0 * 0.8)
    assert m.mange_convois_kg == pytest.approx(8.0 - _greniers(m))
    assert _food(cellule.stocks) == sum(_food(l.stocks) for l in cellule.lieux)
    print(f'charges arrivées={_greniers(m)}, mangé={m.mange_convois_kg}')


from functools import cache


@cache
def _habitants_apres_un_an(part):
    """Une année par part et par processus, sur le même monde neuf."""
    monde, rng = World.charger(0), random.Random(0)
    monde.parts = dict.fromkeys(monde.parts, part)
    for numero in range(c.CALENDAR_DAYS_PER_YEAR):
        engine.tick(monde, rng, numero)
    habitants = sum(cell.population for cell in monde.cells.values())
    print(f'part={part:.2f}, habitants après un an={habitants}')
    return habitants


def _perte(part, habitants):
    assert habitants and habitants[0] > 0
    return 1 - habitants[part] / habitants[0]


def _verifier_calibration(part, habitants):
    """La coutume tient le seuil, le centième suivant le dépasse."""
    assert _perte(part, habitants) <= 0.01
    assert _perte(round(part + 0.01, 2), habitants) > 0.01


def _verifier_direction(populations):
    assert len(populations) > 1
    assert all(a > b for a, b in zip(populations, populations[1:]))


def test_calibration_de_la_part_coutumiere():
    part = c.PART_COUTUMIERE
    dessus = round(part + 0.01, 2)
    parts = (0, part, dessus, 0.10)
    habitants = {p: _habitants_apres_un_an(p) for p in parts}
    for p in parts:
        print(f'part={p:.2f}, habitants={habitants[p]}, perte={_perte(p, habitants):.6%}')
    _verifier_calibration(part, habitants)
    with pytest.raises(AssertionError):
        _verifier_calibration(parts[-1], habitants)
    with pytest.raises(AssertionError):
        _verifier_calibration(part, habitants | {dessus: habitants[part]})
    populations = [habitants[p] for p in parts]
    print(f'écarts entre parts successives={[a - b for a, b in zip(populations, populations[1:])]}')
    _verifier_direction(populations)
    with pytest.raises(AssertionError):
        _verifier_direction(populations[::-1])
    with pytest.raises(AssertionError):
        _verifier_direction([])
    with pytest.raises(AssertionError):
        _verifier_calibration(part, {})


def _verifier_modele_calibration(section, habitants):
    parts = (c.PART_COUTUMIERE, round(c.PART_COUTUMIERE + 0.01, 2))
    termes = ['Calibration de la part coutumière', '1 %', 'graine 0', 'niveau 2']
    for part in parts:
        termes.extend((f'{part:.2f}'.replace('.', ','),
                       f'{_perte(part, habitants):.2%}'.replace('.', ',').replace('%', ' %')))
    for terme in termes:
        assert terme in section, terme
    assert 'provisoirement' not in section


def test_modele_calibration_de_la_part_coutumiere():
    part = c.PART_COUTUMIERE
    habitants = {p: _habitants_apres_un_an(p) for p in (0, part, round(part + 0.01, 2))}
    section = _section_prelevement((SIM / 'MODELE.md').read_text())
    _verifier_modele_calibration(section, habitants)
    coutume = f'{part:.2f}'.replace('.', ',')
    autre = f'{round(part - 0.01, 2):.2f}'.replace('.', ',')
    with pytest.raises(AssertionError):
        _verifier_modele_calibration(section.replace(coutume, autre), habitants)
    commentaire = (SIM / 'constants.py').read_text().split('\nPART_COUTUMIERE =', 1)[0].splitlines()[-1]
    assert commentaire.startswith('#') and 'provisoire' not in commentaire
    notice = (SIM / 'tests/README.md').read_text()
    assert 'calibration' in next(l for l in notice.splitlines() if 'test_prelevement.py' in l)
    assert 'fige le monde avec prélèvement' in next(l for l in notice.splitlines() if 'test_determinisme.py' in l)
    print(f'part documentée={coutume}, pertes={[_perte(p, habitants) for p in habitants if p]}')
