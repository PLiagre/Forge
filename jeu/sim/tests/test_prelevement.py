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
    monkeypatch.setattr(c, 'PART_DUE_AU_SUZERAIN', 0)
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


def _habitants_apres_un_an(part):
    return _habitants_apres_un_an_calibres(part, c.BRAS_AUX_CHAMPS_PAR_KM2)


@cache
def _habitants_apres_un_an_calibres(part, bras):
    """Une année par part et calibrage, sans mélanger les deux références."""
    assert bras == c.BRAS_AUX_CHAMPS_PAR_KM2
    monde, rng = World.charger(0), random.Random(0)
    monde.parts = dict.fromkeys(monde.parts, part)
    for numero in range(c.CALENDAR_DAYS_PER_YEAR):
        engine.tick(monde, rng, numero)
    habitants = sum(cell.population for cell in monde.cells.values())
    print(f'bras={bras}, part={part:.2f}, habitants après un an={habitants}', flush=True)
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


def test_calibration_de_la_part_coutumiere(monkeypatch):
    monkeypatch.setattr(c, 'TAUX_DE_DEPART', 0)
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


@pytest.mark.parametrize("bras", [0.1, 6.2], ids=["historique", "calibre"])
def test_modele_calibration_de_la_part_coutumiere(monkeypatch, bras):
    monkeypatch.setattr(c, "BRAS_AUX_CHAMPS_PAR_KM2", bras)
    monkeypatch.setattr(c, 'TAUX_DE_DEPART', 0)
    part = c.PART_COUTUMIERE
    habitants = {p: _habitants_apres_un_an(p) for p in (0, part, round(part + 0.01, 2))}
    section = _section_prelevement((SIM / 'MODELE.md').read_text())
    marqueur = '**Calibration de la part coutumière à 6,2, sans départs.**'
    historique, calibree = section.split(marqueur, 1)
    section = historique if bras == 0.1 else marqueur + calibree.split('**Mesures avec départs actifs.**', 1)[0]
    _verifier_modele_calibration(section, habitants)
    _verifier_calibration(part, habitants)
    if bras == 6.2:
        for population in habitants.values():
            assert str(population) in section
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


def test_bar_paie_les_valois(monde, monkeypatch):
    monkeypatch.setattr(c, 'PERTE_GRENIER_PAR_AN', 0)
    suzerain, duree = monde.dus_des_vassaux.routes[BAR]
    lieux = [(cid, rang, r.jours) for (cid, rang), r in monde.routes_des_lieux.items() if r.maitre == BAR]
    original = prelevement.prelever
    part = c.PART_DUE_AU_SUZERAIN
    def course(perte, du):
        m = copy.deepcopy(monde)
        m.parts = dict.fromkeys(m.parts, 0.0); m.parts[BAR] = 0.5
        kg = {}
        def observer(m, recoltes):
            avant = {(cid, rang): _food(m.cells[cid].lieux[rang].stocks) for cid, rang, _ in lieux}
            original(m, recoltes)
            if m.ticks_ecoules == 0:
                kg.update({cle: stock - _food(m.cells[cle[0]].lieux[cle[1]].stocks) for cle, stock in avant.items()})
        with monkeypatch.context() as ctx:
            ctx.setattr(prelevement, 'prelever', observer)
            ctx.setattr(c, 'PERTE_CONVOI_PAR_JOUR', perte)
            ctx.setattr(c, 'PART_DUE_AU_SUZERAIN', du)
            _jouer(m, 1); m.parts[BAR] = 0
            assert kg and sum(kg.values()) > 0
            for t in range(1, max(j for _, _, j in lieux) + duree + 1):
                _jouer(m, 1)
                bar = (1 - du) * sum(kg[cid, rang] * (1 - perte)**j for cid, rang, j in lieux if j <= t)
                valois = du * sum(kg[cid, rang] * (1 - perte)**(j + duree) for cid, rang, j in lieux if j + duree <= t)
                assert _food(m.greniers[BAR]) == pytest.approx(bar, rel=1e-12)
                assert _food(m.greniers[suzerain]) == pytest.approx(valois, rel=1e-12)
                if t < min(j for _, _, j in lieux) + duree:
                    assert _food(m.greniers[suzerain]) == 0
                if du and t == min(j for _, _, j in lieux):
                    charges = [(arrivee, kg) for nom, arrivee, kg in m.to_dict()['convois'] if nom == suzerain]
                    assert charges and all(arrivee == t + duree and kg > 0 for arrivee, kg in charges)
                print(f'tick={t}, Bar={bar}, Valois={valois}')
            assert all(nom not in (BAR, suzerain) for nom, _, _ in prelevement.charges_en_route(m))
        return _food(m.greniers[suzerain]), sum(kg.values())
    normal, total = course(c.PERTE_CONVOI_PAR_JOUR, part)
    sans, brut = course(0, part)
    assert sans == pytest.approx(part * brut, rel=1e-12) and 0 < normal < sans
    assert course(c.PERTE_CONVOI_PAR_JOUR, 0)[0] == 0
    print(f'prélevé={total}, dû arrivé={normal}, sans perte={sans}')


def test_deux_etages_et_pyramide_videe(monde, monkeypatch):
    from sim.convois import TableDus
    monkeypatch.setattr(c, 'PERTE_GRENIER_PAR_AN', 0)
    original = prelevement.prelever
    part = c.PART_DUE_AU_SUZERAIN
    suzerains = {s for s, _ in monde.dus_des_vassaux.routes.values()}
    assert suzerains and not suzerains & monde.dus_des_vassaux.routes.keys()
    base = copy.deepcopy(monde)
    for nom in suzerains: base.parts[nom] = 0
    dus = []
    def observer(m, recoltes, rendre=False):
        avant = _total(m)
        greniers = {v: _food(m.greniers[v]) for v in m.dus_des_vassaux.routes}
        original(m, recoltes)
        for v, (_, jours) in m.dus_des_vassaux.routes.items():
            entree = _food(m.greniers[v]) - greniers[v]
            du = entree / (1 - part) * part
            if du:
                if rendre:
                    m.greniers[v][c.MARCHANDISE_NOURRITURE] += du
                else:
                    dus.append((m.ticks_ecoules + jours, du * (1 - c.PERTE_CONVOI_PAR_JOUR)**jours))
        assert _total(m) == pytest.approx(avant, rel=1e-12)
    normal = copy.deepcopy(base)
    with monkeypatch.context() as ctx:
        ctx.setattr(prelevement, 'prelever', observer)
        _jouer(normal, 30)
    attendu = sum(kg for t, kg in dus if t < normal.ticks_ecoules)
    recu = sum(_food(normal.greniers[s]) for s in suzerains)
    assert attendu > 0 and recu == pytest.approx(attendu, rel=1e-9)
    vide, sans = copy.deepcopy(base), copy.deepcopy(base)
    vide.dus_des_vassaux = TableDus()
    _jouer(vide, 30)
    with monkeypatch.context() as ctx:
        ctx.setattr(c, 'PART_DUE_AU_SUZERAIN', 0)
        _jouer(sans, 30)
    assert pickle.dumps(vide.greniers) == pickle.dumps(sans.greniers)
    assert _food(vide.greniers[BAR]) > _food(normal.greniers[BAR])
    assert pickle.dumps(normal.cells) == pickle.dumps(vide.cells) == pickle.dumps(sans.cells)
    with monkeypatch.context() as ctx:
        ctx.setattr(prelevement, 'prelever', lambda m, r: observer(m, r, rendre=True))
        with pytest.raises(AssertionError): _jouer(copy.deepcopy(base), 30)
    print(f'dus observés={len(dus)}, attendu={attendu}, reçu={recu}, Bar sans dû={_food(vide.greniers[BAR])}, avec dû={_food(normal.greniers[BAR])}')


def test_le_suzerain_paie_a_son_tour():
    from sim.convois import TableRoutes, TableDus
    cellule = Cell(1, 3.0, 0, stocks={c.MARCHANDISE_NOURRITURE: 100.0},
                   lieux=[EtatDeLieu(i, 0, {c.MARCHANDISE_NOURRITURE: 100.0 if i == 0 else 0.0}) for i in range(3)])
    base = World({1: cellule}, [])
    base.routes_des_lieux = TableRoutes([(1, i, nom, 1, i, 1) for i, nom in enumerate(('a', 'b', 'c'))])
    from dataclasses import replace
    from sim.tests.test_convois import _maison
    base.maisons = tuple(replace(_maison(nom, 1, i), suzerain=suzerain)
                        for i, (nom, suzerain) in enumerate((('a', 'b'), ('b', 'c'), ('c', None))))
    base.parts = {'a': 0.5, 'b': 0, 'c': 0}
    base.greniers = {nom: {} for nom in base.parts}
    jours_ab, jours_bc = 2, 3
    part, garde = c.PART_DUE_AU_SUZERAIN, 1 - c.PERTE_CONVOI_PAR_JOUR
    recolte = _food(cellule.lieux[0].stocks)
    entree = base.parts['a'] * recolte * garde
    for retenu in (False, True):
        m = copy.deepcopy(base)
        m.dus_des_vassaux = TableDus(par_indice=[(1, jours_ab), None if retenu else (2, jours_bc), None])
        prelevement.prelever(m, {1: [recolte, 0, 0]})
        m.parts['a'] = 0
        for t in range(1, 1 + jours_ab + jours_bc + 1):
            m.ticks_ecoules = t
            prelevement.prelever(m, {})
        assert _food(m.greniers['a']) == pytest.approx((1 - part) * entree, rel=1e-12)
        assert _food(m.greniers['b']) == pytest.approx((1 if retenu else 1 - part) * part * entree * garde**jours_ab, rel=1e-12)
        assert _food(m.greniers['c']) == pytest.approx(0 if retenu else part**2 * entree * garde**(jours_ab + jours_bc), rel=1e-12)
        assert not m.convois
        assert _total(m) == pytest.approx(_total(base), rel=1e-12)
        print(f'retenu={retenu}, entrée a={entree}, greniers={m.greniers}, pertes={m.mange_convois_kg}')


def test_modele_du_au_suzerain_et_tick_sans_registre():
    texte = (SIM / 'MODELE.md').read_text()
    section = _section_prelevement(texte)
    def verifier(section):
        for terme in ('Le dû au suzerain', f'{c.PART_DUE_AU_SUZERAIN:.2f}'.replace('.', ','), 'hors carte', 'à son tour', 'niveau 2', 'niveau 3'):
            assert terme in section, terme
    verifier(section)
    valeur = f'{c.PART_DUE_AU_SUZERAIN:.2f}'.replace('.', ',')
    autre = f'{c.PART_DUE_AU_SUZERAIN * 2:.2f}'.replace('.', ',')
    with pytest.raises(AssertionError): verifier(section.replace(valeur, autre))
    intentions = texte.split('## Les intentions du joueur', 1)[1].split('\n## ', 1)[0]
    assert 'son dû au suzerain' not in intentions
    assert not _lectures((SIM / 'prelevement.py').read_text(), {'suzerain', 'maitre', 'maisons'})
    notice = (SIM / 'tests/README.md').read_text()
    for fichier in ('test_prelevement.py', 'test_convois.py'):
        assert 'dû' in next(l for l in notice.splitlines() if fichier in l)
    print(f'part due documentée={valeur}')


# Lot 592 : les relevés restent dans les tests, jamais dans le monde.
import inspect
from collections import Counter, defaultdict
from sim import departs
from sim.model import lire_habitants_par_metier


_DEPARTS_REELS = departs.appliquer_departs


@cache
def _instrumenter_departs(etape):
    """Instrumenter l'étape livrée : aucune formule de départ n'est recopiée."""
    if etape.__name__ == '<lambda>':
        return None
    arbre = copy.deepcopy(getattr(etape, '_arbre_observe', None))
    if arbre is None:
        arbre = ast.parse(inspect.getsource(etape))
    fonction = next((n for n in arbre.body if isinstance(n, ast.FunctionDef)), None)
    if fonction is None:
        return None
    points = 0
    for noeud in ast.walk(fonction):
        corps = getattr(noeud, 'body', None)
        if not isinstance(corps, list):
            continue
        for i, instruction in reversed(list(enumerate(corps))):
            if isinstance(instruction, ast.AugAssign) and ast.unparse(instruction) == 'total += partants':
                sonde = ast.parse('_observer(cle, destination, partants)').body[0]
                corps.insert(i, ast.copy_location(sonde, instruction))
                points += 1
    assert points == 1, 'point de mouvement absent ou ambigu'
    fonction.args.args.append(ast.arg(arg='_observer'))
    ast.fix_missing_locations(arbre)
    espace = dict(etape.__globals__)
    exec(compile(arbre, '<observation des départs>', 'exec'), espace)
    return espace[fonction.name]


def _observer_mouvements(monde, etape, capturer=None):
    mouvements = []
    def observer(source, destination, partants):
        if partants:
            if capturer is not None:
                capturer(monde, source)
            mouvements.append((source, destination, partants))
    instrumentee = _instrumenter_departs(etape)
    total = instrumentee(monde, observer) if instrumentee else etape(monde)
    return mouvements, total


def _photo_departs(monde):
    """Figer tous les champs de l'étape, sauf populations et métiers."""
    populations = {(cid, l.rang): l.population
                   for cid, cell in monde.cells.items() for l in cell.lieux}
    cellules = {cid: cell.population for cid, cell in monde.cells.items()}
    immobiles = [
        ({n: v for n, v in vars(cell).items()
          if n not in {'population', 'habitants_par_metier', 'lieux'}},
         [{n: v for n, v in vars(l).items() if n != 'population'} for l in cell.lieux])
        for cell in monde.cells.values()]
    immobiles.extend(getattr(monde, nom) for nom in
                     ('stocks_mer', 'greniers', 'convois', 'mange_convois_kg', 'pertes_kg'))
    return populations, cellules, pickle.dumps(immobiles)


def _verifier_conservation_departs(monde, avant, mouvements, total):
    populations, cellules, immobiles = avant
    apres, _, fixes = _photo_departs(monde)
    sorties, arrivees = Counter(), Counter()
    for source, cible, nombre in mouvements:
        assert source != cible and source in populations and cible in populations
        assert isinstance(nombre, int) and nombre > 0 and nombre % c.TAILLE_FOYER == 0
        sorties[source] += nombre
        arrivees[cible] += nombre
    assert sum(sorties.values()) == sum(arrivees.values()) == total
    assert sum(apres.values()) == sum(populations.values()) == sum(cellules.values())
    assert fixes == immobiles
    for cle, nombre in apres.items():
        assert isinstance(nombre, int) and nombre >= 0
        assert sorties[cle] <= populations[cle]
        assert nombre == populations[cle] - sorties[cle] + arrivees[cle]
    for cell in monde.cells.values():
        metiers = lire_habitants_par_metier(cell)
        assert isinstance(metiers, dict) and all(isinstance(n, int) and n >= 0 for n in metiers.values())
        assert cell.population == sum(l.population for l in cell.lieux) == sum(metiers.values())


def _course_departs(part, etape=_DEPARTS_REELS, toutes=False):
    monde = copy.deepcopy(_reference_departs())
    domaine = frozenset(cle for cle, route in monde.routes_des_lieux.items() if route.maitre == BAR)
    initiaux = {cle: monde.cells[cle[0]].lieux[cle[1]].population // c.TAILLE_FOYER for cle in domaine}
    if toutes:
        monde.parts = dict.fromkeys(monde.parts, part)
    else:
        monde.parts[BAR] = part
    releve = dict(lieux=initiaux, ticks=[], internes=0, externes=0, total=0, croises=0, photo=None)
    def capturer(m, source):
        if releve['photo'] is None and source in domaine:
            releve['photo'] = copy.deepcopy(m)
    def observer(m):
        avant = _photo_departs(m)
        mouvements, total = _observer_mouvements(m, etape, capturer if releve['photo'] is None else None)
        _verifier_conservation_departs(m, avant, mouvements, total)
        releve['ticks'].append(m.ticks_ecoules)
        releve['total'] += total // c.TAILLE_FOYER
        releve['croises'] += len({s for s, _, _ in mouvements} & {d for _, d, _ in mouvements})
        for source, cible, nombre in mouvements:
            if source in domaine:
                categorie = 'internes' if cible in domaine else 'externes'
                releve[categorie] += nombre // c.TAILLE_FOYER
        return total
    with pytest.MonkeyPatch.context() as ctx:
        ctx.setattr(departs, 'appliquer_departs', observer)
        rng = random.Random(0)
        for numero in range(365):
            engine.tick(monde, rng, numero)
            if (numero + 1) % 100 == 0:
                print(f'course {etape.__name__}, part={part:.2f}, toutes={toutes} : {numero + 1}/365 ticks observés', flush=True)
    releve['habitants'] = sum(cell.population for cell in monde.cells.values())
    print(f'part={part:.2f}, toutes={toutes}, étape={etape.__name__}, lieux et foyers initiaux={sorted(initiaux.items())}, '
          f'ticks={len(releve["ticks"])} (0 à 364), lieux envoyant et recevant={releve["croises"]}, internes={releve["internes"]}, hors domaine={releve["externes"]}, '
          f'foyers déplacés monde={releve["total"]}, habitants={releve["habitants"]}', flush=True)
    return releve


@cache
def _reference_departs():
    return World.charger(0)


@cache
def _annee_departs(part, toutes=False):
    assert c.TAUX_DE_DEPART > 0
    return _course_departs(part, toutes=toutes)


def _verifier_direction_departs(faible, forte):
    for releve in (faible, forte):
        assert releve['lieux'] and all(n > 0 for n in releve['lieux'].values())
        assert releve['ticks'] == list(range(365)) and releve['total'] > 0
    assert faible['lieux'] == forte['lieux']
    assert forte['externes'] > faible['externes'] > 0


def _departs_aveugles(world):
    """Contre-épreuve : taux constant et destination géographique fixe."""
    voisins = defaultdict(list)
    for edge in world.adjacency:
        for a, b in ((edge['a'], edge['b']), (edge['b'], edge['a'])):
            if a in world.cells and b in world.cells and world.cells[b].lieux:
                voisins[a].append((b, 0))
    photo = {(cid, l.rang): l.population for cid, cell in world.cells.items() for l in cell.lieux}
    deltas, cellules = Counter(), Counter()
    total = 0
    for cle, population in photo.items():
        candidats = voisins[cle[0]] or [k for k in photo if k[0] == cle[0] and k != cle]
        if not candidats:
            continue
        destination = min(candidats)
        partants = int(population * c.TAUX_DE_DEPART / c.TAILLE_FOYER) * c.TAILLE_FOYER
        deltas[cle] -= partants
        deltas[destination] += partants
        cellules[cle[0]] -= partants
        cellules[destination[0]] += partants
        total += partants
    for (cid, rang), population in photo.items():
        world.cells[cid].lieux[rang].population = population + deltas[cid, rang]
    for cid, delta in sorted(cellules.items()):
        if delta > 0:
            engine._ajouter_par_les_foyers(world.cells[cid], delta)
        elif delta < 0:
            engine._retirer_par_les_foyers(world.cells[cid], -delta)
    return total


def test_departs_direction_et_contre_epreuves():
    faible, forte = _annee_departs(0.1), _annee_departs(0.6)
    for a, b in ((faible | {'lieux': {}}, forte), (forte, faible), (faible, faible),
                 (_course_departs(0.1, lambda m: 0), forte)):
        with pytest.raises(AssertionError):
            _verifier_direction_departs(a, b)
    aveugles = [_course_departs(p, _departs_aveugles) for p in (0.1, 0.6)]
    assert all(r['total'] > 0 and r['externes'] > 0 for r in aveugles)
    with pytest.raises(AssertionError):
        _verifier_direction_departs(*aveugles)
    print('Rouges : vide, inversion, égalité, étape inerte et taux aveugle refusés.')
    assert faible['croises'] + forte['croises'] > 0
    _verifier_direction_departs(faible, forte)


def _verifier_identite_departs(photo, etape):
    a, b = copy.deepcopy(photo), copy.deepcopy(photo)
    noms = list(b.parts)
    permutation = dict(zip(noms, noms[1:] + noms[:1]))
    b.routes_des_lieux.noms = [permutation[n] for n in b.routes_des_lieux.noms]
    for cell in b.cells.values():
        for lieu in cell.lieux:
            if lieu.maitre is not None:
                lieu.maitre = permutation[lieu.maitre]
    a.parts = dict.fromkeys(a.parts, c.PART_COUTUMIERE)
    b.parts = dict(a.parts)
    ma, ta = _observer_mouvements(a, etape)
    mb, tb = _observer_mouvements(b, etape)
    print(f'identité : {len(ma)} et {len(mb)} mouvements, {ta} et {tb} habitants déplacés', flush=True)
    assert ma and mb
    assert Counter(ma) == Counter(mb) and ta == tb
    assert _photo_departs(a)[:2] == _photo_departs(b)[:2]
    assert [lire_habitants_par_metier(cell) for cell in a.cells.values()] == [
        lire_habitants_par_metier(cell) for cell in b.cells.values()]


def test_departs_identite_et_conservation():
    photo = _annee_departs(0.6)['photo']
    assert photo is not None
    # Injecter une dépendance au maître dans la même boucle pour éprouver l'égalité.
    arbre = ast.parse(inspect.getsource(_DEPARTS_REELS))
    boucle = next(n for n in ast.walk(arbre) if isinstance(n, ast.For)
                  and isinstance(n.target, ast.Tuple) and ast.unparse(n.target).startswith('(cle,'))
    garde = ast.parse("if world.routes_des_lieux[cle].maitre == BAR: continue").body[0]
    ast.copy_location(garde, boucle.body[0])
    boucle.body.insert(0, garde)
    ast.fix_missing_locations(arbre)
    ast.increment_lineno(arbre, inspect.getsourcelines(_DEPARTS_REELS)[1] - 1)
    espace = dict(_DEPARTS_REELS.__globals__, BAR=BAR)
    exec(compile(arbre, inspect.getsourcefile(_DEPARTS_REELS), 'exec'), espace)
    espace['appliquer_departs']._arbre_observe = arbre
    with pytest.raises(AssertionError):
        _verifier_identite_departs(photo, espace['appliquer_departs'])
    _verifier_identite_departs(photo, _DEPARTS_REELS)
    monde = copy.deepcopy(photo)
    avant = _photo_departs(monde)
    mouvements, total = _observer_mouvements(monde, _DEPARTS_REELS)
    assert mouvements
    for mutation in ('habitant', 'kilo'):
        faux = copy.deepcopy(monde)
        cid, rang = mouvements[0][1]
        lieu = faux.cells[cid].lieux[rang]
        if mutation == 'habitant':
            lieu.population += 1
        else:
            lieu.stocks[c.MARCHANDISE_NOURRITURE] = _food(lieu.stocks) + 1
        with pytest.raises(AssertionError):
            _verifier_conservation_departs(faux, avant, mouvements, total)
    print('Rouges : identité du maître, habitant créé et kilo ajouté refusés.')
    _verifier_conservation_departs(monde, avant, mouvements, total)


def _mesures_calibration_active():
    parts = (0, c.PART_COUTUMIERE, round(c.PART_COUTUMIERE + 0.01, 2), 0.10)
    releves = {p: _annee_departs(p, toutes=True) for p in parts}
    assert all(r['total'] > 0 and r['ticks'] == list(range(365)) for r in releves.values())
    habitants = {p: r['habitants'] for p, r in releves.items()}
    for p in parts:
        print(f'calibration active : part={p:.2f}, habitants={habitants[p]}, '
              f'perte={_perte(p, habitants):.6%}, départs={releves[p]["total"]} foyers', flush=True)
    print(f'bornes : perte({parts[1]:.2f}) ≤ 1 % < perte({parts[2]:.2f})', flush=True)
    return habitants


def test_calibration_active_et_contre_epreuves():
    habitants = _mesures_calibration_active()
    part, dessus = c.PART_COUTUMIERE, round(c.PART_COUTUMIERE + 0.01, 2)
    for p, mesures in ((0.10, habitants), (part, habitants | {dessus: habitants[part]}), (part, {})):
        with pytest.raises(AssertionError):
            _verifier_calibration(p, mesures)
    populations = list(habitants.values())
    for valeurs in (populations[::-1], []):
        with pytest.raises(AssertionError):
            _verifier_direction(valeurs)
    print('Rouges : part trop coûteuse, borne supérieure, direction et vide refusés.')
    _verifier_direction(populations)
    _verifier_calibration(part, habitants)


def _ligne_calibration_active(part, habitants, releve):
    return (f'- part {part:.2f} : {habitants[part]} habitants ; '
            f'perte {_perte(part, habitants):.6%} ; {releve["total"]} foyers déplacés').replace('.', ',').replace('%', ' %') + '.'


def _verifier_modele_calibration_active(texte, habitants, bar):
    section = _section_prelevement(texte).split('**Mesures avec départs actifs.**', 1)
    assert len(section) == 2, 'mesure active absente'
    active = section[1].split('\n\n', 1)[0]
    for terme in ('graine 0', '365 ticks', 'niveau 2', '1 %'):
        assert terme in active
    for part in habitants:
        assert _ligne_calibration_active(part, habitants, _annee_departs(part, toutes=True)) in active
    part = c.PART_COUTUMIERE
    verdict = 'tenue' if _perte(part, habitants) <= .01 < _perte(round(part + .01, 2), habitants) else 'en échec'
    assert f'Calibration {verdict}' in active
    section = texte.split('## Les départs', 1)[1].split('\n## ', 1)[0]
    for p, r in zip((.1, .6), bar):
        assert f'part {p:.1f} : {r["internes"]} foyers internes, {r["externes"]} foyers hors domaine'.replace('.', ',') in section
    for terme in ('Bar', 'sorties brutes', 'TAILLE_FOYER', '0 à 364', 'graine 0'):
        assert terme in section


def test_modele_calibration_active():
    habitants = _mesures_calibration_active()
    bar = [_annee_departs(p) for p in (.1, .6)]
    texte = (SIM / 'MODELE.md').read_text()
    marqueur = '**Mesures avec départs actifs.**'
    assert marqueur in texte, 'mesure active absente'
    perte = f'{_perte(c.PART_COUTUMIERE, habitants):.6%}'.replace('.', ',').replace('%', ' %')
    debut, active = texte.split(marqueur, 1)
    for faux in (debut, debut + marqueur + active.replace(perte, '99,000000 %')):
        with pytest.raises(AssertionError):
            _verifier_modele_calibration_active(faux, habitants, bar)
    print('Rouges documentaires : mesure absente et perte falsifiée refusées.')
    _verifier_modele_calibration_active(texte, habitants, bar)


def _entrees_ouverture(monde):
    routes = monde.routes_des_lieux
    indice = routes.noms.index(BAR)
    return [(cid, rang, jours) for cid, rang, idx, jours in
            zip(routes.cids, routes.rangs, routes.maitre_idx, routes.jours) if idx == indice]


def _deposer_ouverture(monde, kg):
    from sim.intentions import recevoir_intention
    return recevoir_intention(monde, {"type": "ouvrir_grenier", "maison": BAR, "kg": kg})


def test_ouverture_conservation_delais_et_cellules(monde, monkeypatch):
    from sim.lieux import partager
    from sim.model import lire_stock_marchandise
    monkeypatch.setattr(c, 'PERTE_GRENIER_PAR_AN', 0)
    def verifier():
        m = copy.deepcopy(monde)
        m.parts = dict.fromkeys(m.parts, 0)
        m.greniers[BAR] = {c.MARCHANDISE_NOURRITURE: 200000.0}
        entrees = _entrees_ouverture(m)
        assert entrees
        parts = partager(150000, [m.cells[cid].lieux[rang].population for cid, rang, _ in entrees])
        _deposer_ouverture(m, 150000)
        original, recus = prelevement.prelever, []
        def observer(w, recoltes):
            lieux = [w.cells[cid].lieux[rang] for cid, rang, _ in entrees]
            avant = [lire_stock_marchandise(l, c.MARCHANDISE_NOURRITURE) for l in lieux]
            cellules = {cid: lire_stock_marchandise(w.cells[cid], c.MARCHANDISE_NOURRITURE) for cid, _, _ in entrees}
            original(w, recoltes)
            hausses = [lire_stock_marchandise(l, c.MARCHANDISE_NOURRITURE) - kg for l, kg in zip(lieux, avant)]
            recus.extend(hausses)
            attendu = [part * (1 - c.PERTE_CONVOI_PAR_JOUR)**jours if w.ticks_ecoules == jours - 1 else 0
                       for (_, _, jours), part in zip(entrees, parts)]
            for cid, stock in cellules.items():
                assert lire_stock_marchandise(w.cells[cid], c.MARCHANDISE_NOURRITURE) - stock == pytest.approx(
                    sum(kg for (cell_id, _, _), kg in zip(entrees, hausses) if cell_id == cid), rel=1e-12)
            roulant = sum(sum(charges.values()) for charges in w.secours.values())
            assert 200000 - _food(w.greniers[BAR]) == pytest.approx(sum(recus) + w.mange_convois_kg + roulant, rel=1e-12)
            assert hausses == pytest.approx(attendu, rel=1e-12)
        with monkeypatch.context() as garde:
            garde.setattr(prelevement, 'prelever', observer)
            _jouer(m, max(j for _, _, j in entrees) + 1)
        assert not m.secours and _food(m.greniers[BAR]) == 50000
        assert sum(recus) > 0
    verifier()
    with monkeypatch.context() as garde:
        garde.setattr(prelevement, '_livrer_secours', lambda w, charges: None)
        with pytest.raises(AssertionError): verifier()


def test_ouverture_baisse_dette_a_chaque_tick(monde, monkeypatch):
    monkeypatch.setattr(c, 'RNG_YIELD_LOW', 0)
    monkeypatch.setattr(c, 'RNG_YIELD_HIGH', 0)
    base = copy.deepcopy(monde)
    entrees = _entrees_ouverture(base)
    def dette(m):
        return sum(m.cells[cid].lieux[rang].dette_alimentaire_kg for cid, rang, _ in entrees)
    rng = random.Random(0)
    for _ in range(c.CALENDAR_DAYS_PER_YEAR):
        engine.tick(base, rng, base.ticks_ecoules)
        if dette(base) > 0: break
    assert entrees and dette(base) > 0, 'échantillon sans dette avant ouverture'
    def verifier():
        avec, sans = copy.deepcopy(base), copy.deepcopy(base)
        for m in (avec, sans): m.greniers[BAR] = {c.MARCHANDISE_NOURRITURE: 200000.0}
        _deposer_ouverture(avec, 200000)
        generateurs = [random.Random(), random.Random()]
        for generateur in generateurs: generateur.setstate(rng.getstate())
        for _ in range(6):
            for m, generateur in zip((avec, sans), generateurs): engine.tick(m, generateur, m.ticks_ecoules)
            assert dette(avec) < dette(sans)
        assert _food(avec.greniers[BAR]) < _food(sans.greniers[BAR])
    verifier()
    with monkeypatch.context() as garde:
        garde.setattr(prelevement, '_livrer_secours', lambda w, charges: None)
        with pytest.raises(AssertionError): verifier()


def test_ouverture_suit_le_lieu_et_octets(monde, monkeypatch):
    from sim.lieux import partager
    from sim.model import ecrire_maitre
    monkeypatch.setattr(c, 'PERTE_GRENIER_PAR_AN', 0)
    def verifier():
        base = copy.deepcopy(monde)
        base.parts = dict.fromkeys(base.parts, 0)
        base.greniers[BAR] = {c.MARCHANDISE_NOURRITURE: 200000.0}
        entrees = _entrees_ouverture(base)
        parts = partager(150000, [base.cells[cid].lieux[rang].population for cid, rang, _ in entrees])
        cible, part_cible = next((e, p) for e, p in zip(entrees, parts) if e[-1] > 1 and p > 0)
        copies = [copy.deepcopy(base), copy.deepcopy(base)]
        octets = []
        for m in copies:
            _deposer_ouverture(m, 150000)
            _jouer(m, 1)
            charges = m.to_dict()['secours']
            assert charges == sorted(charges)
            assert charges == sorted([cid, rang, jours - 1, part * (1 - c.PERTE_CONVOI_PAR_JOUR)]
                                     for (cid, rang, jours), part in zip(entrees, parts) if jours > 1 and part)
            cid, rang, jours = cible
            lieu = m.cells[cid].lieux[rang]
            ecrire_maitre(lieu, next(n for n in m.parts if n != BAR))
            original, recus = prelevement.prelever, []
            def observer(w, recoltes):
                avant = _food(lieu.stocks)
                original(w, recoltes)
                if w.ticks_ecoules == jours - 1: recus.append(_food(lieu.stocks) - avant)
            with monkeypatch.context() as garde:
                garde.setattr(prelevement, 'prelever', observer)
                _jouer(m, max(j for _, _, j in entrees))
            assert recus == pytest.approx([part_cible * (1 - c.PERTE_CONVOI_PAR_JOUR)**jours], rel=1e-12)
            assert 'secours' not in m.to_dict()
            octets.append(json.dumps(m.to_dict(), sort_keys=True, ensure_ascii=False).encode())
        assert octets[0] == octets[1]
        _jouer(base, max(j for _, _, j in entrees) + 1)
        assert 'secours' not in base.to_dict() and 'mange_convois_kg' not in base.to_dict()
        assert World({}, []).secours == {}
    verifier()
    original = prelevement._livrer_secours
    def mauvais_maitre(m, charges):
        original(m, {cle: kg for cle, kg in charges.items() if m.cells[cle[0]].lieux[cle[1]].maitre == BAR})
    with monkeypatch.context() as garde:
        garde.setattr(prelevement, '_livrer_secours', mauvais_maitre)
        with pytest.raises(AssertionError): verifier()


# Lot 406 : mesurer les représentations stockées et chaque destination annuelle.
def _jalon3_reference(m):
    from sim.lieux import lieux_depuis_monde
    from sim.maitres import attribuer_maitres, valider_attribution
    from sim.registre_maisons import charger_registre_maisons
    base = copy.copy(m)
    base.maisons = charger_registre_maisons(m.carte)
    maitres, plausibles = attribuer_maitres(base)
    valider_attribution(base, maitres, plausibles)
    assert len({maison.id for maison in m.maisons}) == len(m.maisons)
    assert {maison.id for maison in m.maisons} == {maison.id for maison in base.maisons + plausibles}
    return maitres, lieux_depuis_monde(m)


def _jalon3_lieux(m, reference):
    maitres, vue = reference
    assert m.cells and m.cells.keys() == vue.keys(), 'cellules absentes'
    couples = []
    for cid, cell in m.cells.items():
        assert cell.lieux and [l.rang for l in cell.lieux] == [l.rang for l in vue[cid]]
        assert sum(l.surface_km2 for l in vue[cid]) == cell.area_km2
        assert sum(l.population for l in cell.lieux) == cell.population
        for lieu in cell.lieux:
            couples.append((cid, lieu.rang))
            assert lieu.maitre == maitres[cid, lieu.rang]
            assert lieu.stocks.keys() == cell.stocks.keys(), 'absence de marchandise différente'
        for nom, kg in cell.stocks.items():
            assert sum(l.stocks[nom] for l in cell.lieux) == pytest.approx(kg, rel=1e-12, abs=1e-8)
    assert len(couples) == len(set(couples)) and set(couples) == maitres.keys()
    return len(couples)


def test_jalon3_lieux(monde):
    reference = _jalon3_reference(monde)
    for defaut in ('absent', 'inconnu', 'retire', 'doublon', 'personne', 'kilo', 'marchandise', 'vide'):
        m = copy.deepcopy(monde)
        cell = next(iter(m.cells.values()))
        lieu = cell.lieux[0]
        if defaut == 'absent': lieu.maitre = None
        elif defaut == 'inconnu': lieu.maitre = 'maison-inconnue'
        elif defaut == 'retire': cell.lieux.pop()
        elif defaut == 'doublon': cell.lieux.append(copy.deepcopy(lieu))
        elif defaut == 'personne': lieu.population += 1
        elif defaut == 'kilo': lieu.stocks[c.MARCHANDISE_NOURRITURE] += 1
        elif defaut == 'marchandise': lieu.stocks['absence-non-declaree'] = 0
        else: m.cells.clear()
        with pytest.raises(AssertionError): _jalon3_lieux(m, reference)
        print(f'Rouge lieux : {defaut} refusé')
    print(f'cellules contrôlées={len(monde.cells)}, lieux contrôlés={_jalon3_lieux(monde, reference)}')


def _jalon3_annee(monde, monkeypatch, etape):
    m = copy.deepcopy(monde)
    reference = _jalon3_reference(m)
    lieux = [(cid, rang, r.jours) for (cid, rang), r in m.routes_des_lieux.items() if r.maitre == BAR]
    suzerain, trajet = m.dus_des_vassaux.routes[BAR]
    assert lieux and len(lieux) == c.LIEUX_DE_LA_SEIGNEURIE
    assert suzerain not in m.dus_des_vassaux.routes
    m.parts = dict.fromkeys(m.parts, 0.0); m.parts[BAR] = 0.6
    assert not m.convois and _greniers(m) == m.mange_convois_kg == m.pertes_kg == 0
    bruts, retenus, dus, recus = (defaultdict(float) for _ in range(4))
    charges, entrees = [], Counter()
    garde, part = 1 - c.PERTE_CONVOI_PAR_JOUR, c.PART_DUE_AU_SUZERAIN
    preleve = 0.0
    def observer(w, recoltes):
        nonlocal preleve
        t = w.ticks_ecoules
        avant, stocks = _total(w), _stocks(w)
        paniers = {(cid, rang): _food(w.cells[cid].lieux[rang].stocks) for cid, rang, _ in lieux}
        greniers = {nom: _food(panier) for nom, panier in w.greniers.items()}
        etape(w, recoltes)
        assert _total(w) == pytest.approx(avant, rel=1e-12), 'conservation à l’étape'
        apres = _stocks(w)
        _egalite(stocks, apres)
        debits = {cle: kg - _food(w.cells[cle[0]].lieux[cle[1]].stocks) for cle, kg in paniers.items()}
        assert sum(debits.values()) == pytest.approx(sum(stocks[cid][0] - apres[cid][0] for cid in stocks), rel=1e-12, abs=1e-8)
        for cid, rang, jours in lieux:
            kg = debits[cid, rang]
            assert kg >= 0
            preleve += kg
            arrivee = t + jours
            brut = kg * garde**jours
            bruts[arrivee] += brut
            retenus[arrivee] += brut * (1 - part)
            dus[arrivee] += brut * part
            recus[arrivee + trajet] += brut * part * garde**trajet
            if kg: charges.append((BAR, t, arrivee, kg))
        if dus[t]: charges.append((suzerain, t, t + trajet, dus[t]))
        for nom, panier in w.greniers.items():
            entree = _food(panier) - greniers[nom]
            attendu = retenus[t] if nom == BAR else recus[t] if nom == suzerain else 0
            assert entree == pytest.approx(attendu, rel=1e-12, abs=1e-8), f'entrée {nom}, tick {t}'
            entrees[nom] += entree
    _jalon3_lieux(m, reference)
    with monkeypatch.context() as ctx:
        ctx.setattr(prelevement, 'prelever', observer)
        rng = random.Random(0)
        for t in range(365):
            engine.tick(m, rng, t)
            _jalon3_lieux(m, reference)
    en_route = [(nom, fin, kg * garde**(364 - debut)) for nom, debut, fin, kg in charges if fin > 364]
    assert en_route, 'charges dépassant le dernier tick absentes'
    assert _route(m) == pytest.approx(sum(kg for _, _, kg in en_route), rel=1e-12, abs=1e-8)
    for nom in (BAR, suzerain):
        assert sum(kg for n, _, kg in prelevement.charges_en_route(m) if n == nom) == pytest.approx(sum(kg for n, _, kg in en_route if n == nom), rel=1e-12, abs=1e-8)
    assert preleve == pytest.approx(_route(m) + _greniers(m) + m.mange_convois_kg + m.pertes_kg, rel=1e-12)
    assert all(kg > 0 for kg in (preleve, entrees[BAR], entrees[suzerain], m.mange_convois_kg, m.pertes_kg))
    print(f'cellules={len(m.cells)}, lieux={len(reference[0])}, ticks={m.ticks_ecoules}, prélevé={preleve}, '
          f'brut à Bar={sum(bruts[t] for t in range(365))}, retenu à Bar={entrees[BAR]}, '
          f'dû envoyé={sum(dus[t] for t in range(365))}, reçu par {suzerain}={entrees[suzerain]}, '
          f'transit={_route(m)} ({len(en_route)} charges), mangé={m.mange_convois_kg}, pertes greniers={m.pertes_kg}, stock final={_greniers(m)}')


def test_jalon3_destination_annuelle(monde, monkeypatch):
    original = prelevement.prelever
    suzerain, _ = monde.dus_des_vassaux.routes[BAR]
    for defaut in ('restitution', 'du_double', 'mauvais_grenier'):
        def alterer(w, recoltes):
            stocks = {cid: (dict(cell.stocks), [dict(l.stocks) for l in cell.lieux]) for cid, cell in w.cells.items()}
            arrives = sum(kg for nom, t, kg in prelevement.charges_en_route(w) if nom == BAR and t == w.ticks_ecoules)
            avant = _food(w.greniers[suzerain])
            original(w, recoltes)
            if defaut == 'restitution':
                for cid, (panier, lieux) in stocks.items():
                    w.cells[cid].stocks = panier
                    for lieu, panier in zip(w.cells[cid].lieux, lieux): lieu.stocks = panier
            elif defaut == 'du_double':
                w.greniers[BAR][c.MARCHANDISE_NOURRITURE] = _food(w.greniers[BAR]) + arrives * (1 - c.PERTE_CONVOI_PAR_JOUR) * c.PART_DUE_AU_SUZERAIN
            else:
                entree = _food(w.greniers[suzerain]) - avant
                w.greniers[suzerain][c.MARCHANDISE_NOURRITURE] = avant
                w.greniers[BAR][c.MARCHANDISE_NOURRITURE] = _food(w.greniers[BAR]) + entree
        with pytest.raises(AssertionError, match='conservation à l’étape|entrée'):
            _jalon3_annee(monde, monkeypatch, alterer)
        print(f'Rouge comptable : {defaut} refusé', flush=True)
    _jalon3_annee(monde, monkeypatch, original)


@pytest.mark.parametrize('defaut,code', [('aucun', 0), ('vide', 1), ('absent', 1), ('ignore', 1), ('echec', 1), ('ancienne_image', 1), ('impossible', 2)])
def test_jalon3_lanceur(tmp_path, monkeypatch, capsys, defaut, code):
    import epreuve_jalon3 as preuve
    import xml.etree.ElementTree as ET
    from types import SimpleNamespace
    sortie = tmp_path / 'sortie'
    capture = sortie / 'capture'
    capture.mkdir(parents=True)
    for nom in ('carte.png', 'monde.json', 'resume.json'): (capture / nom).write_text('ancienne')
    def executer(commande, **options):
        assert commande[0] == preuve.sys.executable and options['cwd'] == preuve.Path(preuve.__file__).parent
        if defaut == 'impossible': raise OSError('interpréteur indisponible')
        if commande[2] == 'pytest':
            racine = ET.Element('testsuites')
            for fichier, noms in preuve.CAS.items():
                for nom in noms:
                    ET.SubElement(racine, 'testcase', classname=fichier.removesuffix('.py').replace('/', '.'), name=f'test_{nom}')
            if defaut == 'vide': racine.clear()
            elif defaut == 'absent': racine.remove(next(cas for cas in racine if '[' in cas.get('name')))
            elif defaut in ('ignore', 'echec'): ET.SubElement(racine[0], 'skipped' if defaut == 'ignore' else 'failure')
            ET.ElementTree(racine).write(sortie / 'controles.xml')
        elif defaut != 'ancienne_image':
            for nom in ('carte.png', 'monde.json', 'resume.json'): (capture / nom).write_text('neuve')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(preuve.subprocess, 'run', executer)
    monkeypatch.setattr('sys.argv', ['epreuve_jalon3', '--sortie', str(sortie)])
    assert preuve.main() == code
    sortie_console = capsys.readouterr()
    assert ('J3 prouvé' in sortie_console.out + (sortie / 'preuve.txt').read_text()) == (code == 0)


def test_ia_ouverture_baisse_dette(monkeypatch):
    from sim import ia, engine
    from sim.intentions import OuvrirGrenier
    from sim.tests.test_intentions import _monde_de_secours
    monkeypatch.setattr(c, 'RNG_YIELD_LOW', 0)
    monkeypatch.setattr(c, 'RNG_YIELD_HIGH', 0)
    monde, cle, maison = _monde_de_secours()
    monkeypatch.setattr(ia, 'maisons_de_l_ia', lambda m, maison=maison: (maison,))
    routes = monde.routes_des_lieux
    indice = routes.noms.index(cle)
    endettes = [(cid, rang, jours) for cid, rang, maitre, jours in
                zip(routes.cids, routes.rangs, routes.maitre_idx, routes.jours)
                if maitre == indice and monde.cells[cid].lieux[rang].dette_alimentaire_kg > 0]
    assert endettes
    delai = max(jours for _, _, jours in endettes)
    premier = min(jours for _, _, jours in endettes)
    assert premier > 1

    def dettes(m):
        return sum(m.cells[cid].lieux[rang].dette_alimentaire_kg
                   for cid, rang, maitre, _jours in
                   zip(routes.cids, routes.rangs, routes.maitre_idx, routes.jours) if maitre == indice)

    def verifier():
        avec, sans = copy.deepcopy(monde), copy.deepcopy(monde)
        releve = []
        ia.jouer_ia(avec, releve)
        acceptes = [e for e in releve if e['intention']['type'] == 'ouvrir_grenier' and 'refus' not in e]
        assert len(acceptes) == 1
        plancher = acceptes[0]['raison']['plancher_kg']
        original = engine._appliquer_intentions
        def appliquer(m):
            ouvert = any(isinstance(geste, OuvrirGrenier) and geste.maison == cle for geste in m.intentions_en_attente)
            original(m)
            if ouvert:
                assert m.greniers[cle][c.MARCHANDISE_NOURRITURE] >= plancher
        engine._appliquer_intentions = appliquer
        try:
            generateurs = (random.Random(0), random.Random(0))
            for numero in range(delai):
                for cible, generateur in zip((avec, sans), generateurs):
                    engine.tick(cible, generateur, cible.ticks_ecoules)
                if numero + 1 < premier:
                    assert dettes(avec) == dettes(sans)
            assert dettes(avec) < dettes(sans)
        finally:
            engine._appliquer_intentions = original

    verifier()
    with monkeypatch.context() as ctx:
        ctx.setattr(ia, 'recevoir_intention', lambda m, i: None)
        with pytest.raises(AssertionError):
            verifier()
    with monkeypatch.context() as ctx:
        ctx.setattr(prelevement, '_livrer_secours', lambda w, charges: None)
        with pytest.raises(AssertionError):
            verifier()
