"""Lot #971 : la route vers le champ, calcul pur, sur le vrai monde de la graine 0."""
from copy import deepcopy
from dataclasses import replace
import json
import math

import pytest

import sim.constants as k
import sim.ia as ia
import sim.programme_ia as programme
import sim.ville1400 as ville1400
from sim.chantiers import travail_requis_de_route
from sim.flux import JourDeFlux
from sim.intentions import (
    IntentionRefusee, TYPE_FIXER_PART, TYPE_OUVRIR_GRENIER, TYPE_TRACER_ROUTE,
    _lieux_de_la_maison, maitre_du_bourg, recevoir_intention, verifier_base,
)
from sim.plan import Rue
from sim.routes_interieures import _places_de, lieu_de_la_route
from sim.world import World

NOURRITURE = k.MARCHANDISE_NOURRITURE
CLES_MAISON = {'sorte', 'id'}
CLES_INTENTION = {'type', 'cell', 'maison', 'points', 'largeur_m', 'foyers'}
CLES_RAISON = {
    'regle', 'grenier_nourriture_kg', 'reserve_voulue_kg', 'journees', 'cout_kg',
    'faim_du_bourg_ticks', 'champs_nourriture_kg', 'champ_vise', 'ecart_degres'}


def _ordre_des_ecarts():
    """0, +p, −p, +2p, −2p… tant que l'écart reste strictement sous le cône."""
    pas = k.IA_PAS_ECART_ROUTE_DEGRES
    ordre = [0]
    n = 1
    while n * pas < k.ANGLE_ROUTE_INTERIEURE_DEGRES:
        ordre += [n * pas, -n * pas]
        n += 1
    return ordre


def _monter():
    """Le monde de la graine 0 au tick 30 : bourgs affamés trente jours, greniers pleins."""
    monde = World.charger(0)
    monde.ticks_ecoules = k.FENETRE_FLUX_TICKS
    maisons = []
    for maison in ia.maisons_de_l_ia(monde):
        if maison.hors_carte is not None:
            continue
        cle = ia._cle_du_grenier(maison)
        if maitre_du_bourg(monde, maison.cell_id) != cle:
            continue
        maisons.append(maison)
    for tick in range(k.FENETRE_FLUX_TICKS):
        monde.flux.jours[tick] = JourDeFlux(tick)
    for maison in maisons:
        for tick in range(k.FENETRE_FLUX_TICKS):
            monde.flux.jours[tick].affames.add((maison.cell_id, 0))
        monde.greniers[ia._cle_du_grenier(maison)] = {NOURRITURE: 1e9}
    return monde, maisons


def _proposer(monde, maison, releve=None):
    return programme.proposer_route_vers_le_champ(monde, maison, [] if releve is None else releve)


@pytest.fixture(scope='module')
def montage():
    monde, maisons = _monter()
    propositions = [(maison, _proposer(monde, maison)) for maison in maisons]
    avec = [(maison, p) for maison, p in propositions if p is not None]
    sans = [maison for maison, p in propositions if p is None]
    print(f'{len(maisons)} maisons de l\'IA tiennent leur bourg : {len(avec)} reçoivent une route, {len(sans)} se taisent')
    assert avec, 'aucune maison ne reçoit de route : échantillon vide'
    return {'monde': monde, 'maisons': maisons, 'propositions': avec, 'sans': sans}


@pytest.fixture
def monde(montage):
    return deepcopy(montage['monde'])


@pytest.fixture
def M(montage):
    return montage['propositions'][0][0]


@pytest.fixture
def reference(montage):
    return deepcopy(montage['propositions'][0][1])


def _points_a(places, rang, ecart):
    """Points du bord de la place pour un écart, lus ici sans la fonction éprouvée."""
    phi = math.atan2(places[rang].y_m - places[0].y_m, places[rang].x_m - places[0].x_m)
    (x0, y0), (ux, uy), _ = ville1400._sortie(phi + math.radians(ecart), k.DEMI_COTE_PLACE_1400_M)
    longueur = k.IA_LONGUEUR_ROUTE_M
    return [[x0, y0], [x0 + ux * longueur, y0 + uy * longueur]]


def _valide(monde, cell_id, places, rang, points, verifier=verifier_base):
    """La route vise ce rang et ne touche aucune maison de 1400."""
    if lieu_de_la_route(Rue(0, points, k.IA_LARGEUR_ROUTE_M), places) != (rang, ''):
        return False
    try:
        verifier(monde, cell_id, points=points, largeur_m=k.IA_LARGEUR_ROUTE_M)
    except IntentionRefusee:
        return False
    return True


def _controler(monde, releve, proposition, depot=None, verifier=verifier_base):
    """Relit une proposition sans la fonction éprouvée ; AssertionError au premier écart."""
    assert set(proposition) == {'maison', 'intention', 'raison'}
    maison, intention, raison = proposition['maison'], proposition['intention'], proposition['raison']
    assert set(maison) == CLES_MAISON
    assert set(intention) == CLES_INTENTION
    assert set(raison) == CLES_RAISON
    assert intention['type'] == TYPE_TRACER_ROUTE
    assert intention['largeur_m'] == k.IA_LARGEUR_ROUTE_M
    assert intention['foyers'] == k.IA_FOYERS_ROUTE
    cell_id = intention['cell']
    cle = intention['maison']
    t = monde.ticks_ecoules
    places = _places_de(monde, cell_id)
    assert places is not None
    (x0, y0), (x1, y1) = intention['points']
    assert abs(max(abs(x0), abs(y0)) - k.DEMI_COTE_PLACE_1400_M) < 1e-9
    assert abs(math.dist((x0, y0), (x1, y1)) - k.IA_LONGUEUR_ROUTE_M) < 1e-9

    # Le champ visé est le plus plein, le plus petit rang à égalité.
    champs = sorted((lieu for lieu in monde.cells[cell_id].lieux if lieu.rang >= 1), key=lambda lieu: lieu.rang)
    vivres = [lieu.stocks.get(NOURRITURE, 0) for lieu in champs]
    assert max(vivres) > 0
    attendu = champs[vivres.index(max(vivres))].rang
    rang = raison['champ_vise']
    assert rang == attendu
    assert raison['champs_nourriture_kg'] == vivres

    # L'écart : signé, entier, multiple du pas, sous le cône.
    ecart = raison['ecart_degres']
    assert isinstance(ecart, int) and not isinstance(ecart, bool)
    assert abs(ecart) < k.ANGLE_ROUTE_INTERIEURE_DEGRES
    assert ecart % k.IA_PAS_ECART_ROUTE_DEGRES == 0
    phi = math.atan2(places[rang].y_m - places[0].y_m, places[rang].x_m - places[0].x_m)
    theta = math.atan2(y1 - y0, x1 - x0)
    mesure = math.atan2(math.sin(theta - phi), math.cos(theta - phi))
    assert abs(mesure - math.radians(ecart)) < 1e-9
    assert abs(abs(math.degrees(mesure)) - abs(ecart)) < 1e-9

    # La route vise le champ, ne touche aucune maison de 1400, et elle est la première.
    assert _valide(monde, cell_id, places, rang, intention['points'], verifier)
    ordre = _ordre_des_ecarts()
    assert ecart in ordre
    for essai in ordre[:ordre.index(ecart)]:
        assert not _valide(monde, cell_id, places, rang, _points_a(places, rang, essai), verifier), (
            f'l\'écart {essai} passait avant {ecart}')

    # La bourse : le grenier paie la route et laisse la réserve voulue.
    journees = travail_requis_de_route(intention['points'], intention['largeur_m'])
    cout = journees * k.SALAIRE_JOURNEE_KG
    reserve = ia._reserve_voulue(monde, _lieux_de_la_maison(monde, cle))['reserve_voulue_kg']
    grenier = monde.greniers[cle].get(NOURRITURE, 0)
    assert raison['journees'] == journees and raison['cout_kg'] == cout
    assert raison['reserve_voulue_kg'] == reserve and raison['grenier_nourriture_kg'] == grenier
    assert grenier > reserve + cout

    # Le mois passé : les jours de faim du bourg, et rien d'autre.
    faim = sum(1 for tick in range(t - k.FENETRE_FLUX_TICKS, t)
               if (cell_id, 0) in monde.flux.jours[tick].affames)
    assert faim > 0
    assert raison['faim_du_bourg_ticks'] == faim
    assert raison['regle'] == 'route_vers_le_champ'
    assert not any(
        e['intention']['type'] == TYPE_TRACER_ROUTE and (e['maison']['sorte'], e['maison']['id']) == (maison['sorte'], maison['id'])
        and t - e['tick'] < k.FENETRE_FLUX_TICKS for e in releve)

    # Le chemin du joueur accepte la route telle quelle.
    if depot is not None:
        recevoir_intention(depot, intention)


def test_sc1_route_vers_le_champ_le_plus_plein(montage):
    monde = montage['monde']
    propositions = montage['propositions']
    print(f'{len(propositions)} propositions sur {len(montage["maisons"])} maisons')
    depot = deepcopy(monde)
    for _, proposition in propositions:
        assert proposition['raison']['faim_du_bourg_ticks'] == k.FENETRE_FLUX_TICKS
        _controler(monde, [], proposition, depot=depot)
    # Le dépôt a reçu autant de routes que de propositions : par le chemin du joueur.
    assert len(depot.intentions_en_attente) == len(propositions)


def test_sc1_contre_epreuves(montage, reference):
    monde = montage['monde']
    _controler(monde, [], reference)

    def refuse(proposition):
        with pytest.raises(AssertionError):
            _controler(monde, [], proposition)

    # Points tournés de 30° autour de p0.
    tournee = deepcopy(reference)
    (x0, y0), (x1, y1) = tournee['intention']['points']
    c, s = math.cos(math.radians(30)), math.sin(math.radians(30))
    tournee['intention']['points'][1] = [x0 + c * (x1 - x0) - s * (y1 - y0), y0 + s * (x1 - x0) + c * (y1 - y0)]
    refuse(tournee)

    # p0 rapproché de l'origine d'un mètre.
    rapprochee = deepcopy(reference)
    (x0, y0), _ = rapprochee['intention']['points']
    norme = math.hypot(x0, y0)
    rapprochee['intention']['points'][0] = [x0 - x0 / norme, y0 - y0 / norme]
    refuse(rapprochee)

    # Coût d'un kilo de trop, champ visé d'un autre rang.
    cher = deepcopy(reference)
    cher['raison']['cout_kg'] += 1
    refuse(cher)
    autre = deepcopy(reference)
    rangs = [lieu.rang for lieu in monde.cells[reference['intention']['cell']].lieux if lieu.rang >= 1]
    autre['raison']['champ_vise'] = next(rang for rang in rangs if rang != reference['raison']['champ_vise'])
    refuse(autre)

    # Un écart +10 là où un écart plus petit passe.
    ordre = _ordre_des_ecarts()
    dix = ordre.index(10)
    for maison, proposition in montage['propositions']:
        if ordre.index(proposition['raison']['ecart_degres']) < dix:
            break
    else:
        pytest.fail('aucune proposition ne passe à un écart plus petit que +10')
    copie = deepcopy(proposition)
    places = _places_de(monde, copie['intention']['cell'])
    copie['intention']['points'] = _points_a(places, copie['raison']['champ_vise'], 10)
    copie['raison']['ecart_degres'] = 10
    refuse(copie)


def _ia_pure(decider, monde, releve):
    avant = deepcopy((monde.__dict__, releve))
    propositions = decider(monde, releve)
    assert (monde.__dict__, releve) == avant
    assert propositions == decider(monde, releve)
    return propositions


def test_sc2_pure_et_deterministe(montage, monde, M):
    muette = montage['sans'][0] if montage['sans'] else None
    assert muette is not None, 'aucune maison ne se tait : la pureté du silence n\'est pas éprouvée'
    for maison in (M, muette):
        _ia_pure(lambda m, r, maison=maison: _proposer(m, maison, r), monde, [])
    assert _proposer(monde, M) is not None and _proposer(monde, muette) is None

    def impur(m, r):
        m.greniers[ia._cle_du_grenier(M)][NOURRITURE] += 1
        return _proposer(m, M, r)
    with pytest.raises(AssertionError):
        _ia_pure(impur, monde, [])

    autre, maisons = _monter()
    attendu = [json.dumps(_proposer(montage['monde'], maison), sort_keys=True) for maison in montage['maisons']]
    relu = [json.dumps(_proposer(autre, maison), sort_keys=True) for maison in maisons]
    assert attendu == relu


def test_sc3_grenier_vide_ne_batit_rien(monde, M, reference):
    cle = ia._cle_du_grenier(M)
    reserve, cout = reference['raison']['reserve_voulue_kg'], reference['raison']['cout_kg']
    assert cout > 0 and reserve >= 0

    def avec_grenier(valeur):
        copie = deepcopy(monde)
        if valeur is None:
            del copie.greniers[cle]
        else:
            copie.greniers[cle] = valeur
        return _proposer(copie, M)

    assert avec_grenier({NOURRITURE: 0}) is None
    assert avec_grenier({}) is None
    assert avec_grenier({'or': 1e9}) is None
    assert avec_grenier(None) is None
    assert avec_grenier({NOURRITURE: reserve + cout}) is None
    assert reserve + cout - 1 > reserve
    assert avec_grenier({NOURRITURE: reserve + cout - 1}) is None
    haut = avec_grenier({NOURRITURE: reserve + cout + 1})
    assert haut is not None
    attendu = deepcopy(reference)
    attendu['raison']['grenier_nourriture_kg'] = reserve + cout + 1
    assert haut == attendu

    # Une rue en chantier ajoute des salaires dus : la réserve monte d'autant.
    monde.greniers[cle] = {NOURRITURE: reserve + cout + 1}
    plan = monde.plans[M.cell_id]
    journees = 10
    plan.rues.append(Rue(
        max((rue.identifiant for rue in plan.rues), default=-1) + 1,
        [(0.0, 0.0), (20.0, 0.0)], k.IA_LARGEUR_ROUTE_M,
        en_chantier=True, foyers=k.IA_FOYERS_ROUTE, travail_requis=journees, travail_fourni=0))
    assert _proposer(monde, M) is None
    monde.greniers[cle] = {NOURRITURE: reserve + cout + 1 + journees * k.SALAIRE_JOURNEE_KG}
    relevee = _proposer(monde, M)
    assert relevee is not None
    assert relevee['raison']['reserve_voulue_kg'] == reserve + journees * k.SALAIRE_JOURNEE_KG


def _affamer(monde, cell_id, jours, rang=0):
    """Ne laisse la faim de (cell_id, rang) qu'aux jours donnés ; l'autre faim du bourg s'efface."""
    for tick in range(monde.ticks_ecoules - k.FENETRE_FLUX_TICKS, monde.ticks_ecoules):
        monde.flux.jours[tick].affames.discard((cell_id, 0))
        monde.flux.jours[tick].affames.discard((cell_id, rang))
    for tick in jours:
        monde.flux.jours.setdefault(tick, JourDeFlux(tick)).affames.add((cell_id, rang))


def test_sc4_le_bourg_a_eu_faim_ses_champs_gardaient_des_vivres(monde, M, reference):
    t = monde.ticks_ecoules
    cell_id = M.cell_id
    debut = t - k.FENETRE_FLUX_TICKS

    def depuis(muter):
        copie = deepcopy(monde)
        muter(copie)
        return copie

    copie = depuis(lambda m: _affamer(m, cell_id, ()))
    assert _proposer(copie, M) is None

    # Faim d'un champ seulement : la cellule a faim, pas son bourg.
    copie = depuis(lambda m: _affamer(m, cell_id, range(debut, t), rang=1))
    assert any(c == cell_id for tick in range(debut, t) for c, _ in copie.flux.jours[tick].affames)
    assert _proposer(copie, M) is None

    # Une faim hors fenêtre ne compte pas.
    copie = depuis(lambda m: _affamer(m, cell_id, (debut - 1,)))
    assert (cell_id, 0) in copie.flux.jours[debut - 1].affames
    assert _proposer(copie, M) is None

    # La fenêtre incomplète se tait.
    copie = depuis(lambda m: m.flux.jours.pop(t - 1))
    assert _proposer(copie, M) is None

    # Des champs vides ne valent pas une route.
    def vider(m):
        for lieu in m.cells[cell_id].lieux:
            if lieu.rang >= 1:
                lieu.stocks[NOURRITURE] = 0
    assert _proposer(depuis(vider), M) is None

    # Un seul jour de faim, au tick t − 1.
    copie = depuis(lambda m: _affamer(m, cell_id, (t - 1,)))
    seule = _proposer(copie, M)
    assert seule is not None and seule['raison']['faim_du_bourg_ticks'] == 1
    _controler(copie, [], seule)

    # La durée de faim du bourg au tick courant n'est pas lue.
    def calme(m):
        m.cells[cell_id].lieux[0].duree_faim_ticks = 0
    copie = depuis(calme)
    assert _proposer(copie, M) == reference

    def faim_du_jour(m):
        _affamer(m, cell_id, ())
        m.cells[cell_id].lieux[0].duree_faim_ticks = 5
    assert _proposer(depuis(faim_du_jour), M) is None

    # Le champ de plus petit rang qui ne porte pas le maximum, et qu'une route atteint,
    # porté un kilo au-dessus : à M, le rang 4 n'a aucun écart valide, le test le dérive.
    copie = deepcopy(monde)
    champs = sorted((lieu for lieu in copie.cells[cell_id].lieux if lieu.rang >= 1), key=lambda lieu: lieu.rang)
    maximum = max(lieu.stocks[NOURRITURE] for lieu in champs)
    places = _places_de(copie, cell_id)
    atteignables = [lieu for lieu in champs if lieu.stocks[NOURRITURE] < maximum and any(
        _valide(copie, cell_id, places, lieu.rang, _points_a(places, lieu.rang, ecart))
        for ecart in _ordre_des_ecarts())]
    assert atteignables
    autre = atteignables[0]
    autre.stocks[NOURRITURE] = maximum + 1
    deplacee = _proposer(copie, M)
    assert deplacee is not None and deplacee['raison']['champ_vise'] == autre.rang
    assert deplacee['raison']['champ_vise'] != reference['raison']['champ_vise']
    _controler(copie, [], deplacee)


def _geste(tick, auteur, type_intention, **reste):
    return {'tick': tick, 'maison': {'sorte': auteur.sorte, 'id': auteur.id},
            'intention': {'type': type_intention, **reste}}


def test_sc5_une_fois_par_mois_et_pour_son_bourg(monde, M, montage):
    t = monde.ticks_ecoules
    fenetre = k.FENETRE_FLUX_TICKS
    cle = ia._cle_du_grenier(M)
    ancienne = _geste(t - fenetre + 1, M, TYPE_TRACER_ROUTE)
    assert _proposer(monde, M, [ancienne]) is None
    assert _proposer(monde, M, [{**ancienne, 'refus': 'refusée'}]) is None
    for releve in (
        [_geste(t - fenetre, M, TYPE_TRACER_ROUTE)],
        [_geste(t - 1, montage['propositions'][1][0], TYPE_TRACER_ROUTE)],
        [_geste(t - 1, M, TYPE_FIXER_PART, maison=cle, part=0.1)],
        [_geste(t - 1, M, TYPE_OUVRIR_GRENIER, maison=cle, kg=1)],
    ):
        assert _proposer(monde, M, releve) is not None

    assert _proposer(monde, replace(M, cell_id=None, hors_carte='hors carte')) is None

    bourg = monde.cells[M.cell_id].lieux[0]
    voisine = next(m.id for m in monde.maisons if m.id != cle)
    bourg.maitre = voisine
    assert _proposer(monde, M) is None
    bourg.maitre = 'maison-inconnue'
    with pytest.raises(IntentionRefusee):
        _proposer(monde, M)


def test_sc6_ni_maison_de_1400_touchee_ni_route_hors_des_30_degres(montage, M, monkeypatch):
    monde = montage['monde']
    assert monde.populations_bourg_amorcage is not None
    ordre = _ordre_des_ecarts()
    refusees = []
    for maison in montage['sans']:
        cell_id = maison.cell_id
        champs = sorted((lieu for lieu in monde.cells[cell_id].lieux if lieu.rang >= 1), key=lambda lieu: lieu.rang)
        vivres = [lieu.stocks.get(NOURRITURE, 0) for lieu in champs]
        places = _places_de(monde, cell_id)
        if not champs or max(vivres) <= 0 or places is None:
            continue
        rang = champs[vivres.index(max(vivres))].rang
        if rang >= len(places):
            continue
        for ecart in ordre:
            assert not _valide(monde, cell_id, places, rang, _points_a(places, rang, ecart)), (
                f'{maison.id} : l\'écart {ecart} passait')
        refusees.append(maison)
    print(f'{len(refusees)} maisons dont tout le reste passe mais dont chaque écart est refusé')
    assert refusees

    # Un verifier_base qui accepte tout laisserait passer des routes sur des maisons de 1400.
    monkeypatch.setattr(programme, 'verifier_base', lambda *args, **kwargs: None)
    passantes = [(maison, _proposer(monde, maison)) for maison in refusees]
    passantes = [(maison, p) for maison, p in passantes if p is not None]
    assert passantes
    maison, proposition = passantes[0]
    with pytest.raises(IntentionRefusee):
        verifier_base(monde, maison.cell_id, points=proposition['intention']['points'],
                      largeur_m=k.IA_LARGEUR_ROUTE_M)
    with pytest.raises(AssertionError):
        _controler(monde, [], proposition)

    # Un verifier_base qui refuse le seul écart 0 de M : M prend le suivant valide.
    zero = _proposer_sans_patch(montage, M)['intention']['points']

    def refuse_zero(monde_, cell_id, points=None, largeur_m=None, contour=None):
        if points == zero:
            raise IntentionRefusee('écart 0 refusé')
        return verifier_base(monde_, cell_id, points=points, largeur_m=largeur_m, contour=contour)
    monkeypatch.setattr(programme, 'verifier_base', refuse_zero)
    suivante = _proposer(monde, M)
    assert suivante is not None and suivante['raison']['ecart_degres'] != 0
    _controler(monde, [], suivante, verifier=refuse_zero)

    # Une base absente est une cause : la fonction lève, elle ne se tait pas.
    monkeypatch.setattr(programme, 'verifier_base', verifier_base)

    def absente(*args, **kwargs):
        raise ville1400.BaseAbsente('base absente')
    monkeypatch.setattr(ville1400, 'base_de_cellule', absente)
    with pytest.raises(IntentionRefusee):
        _proposer(monde, M)


def _proposer_sans_patch(montage, M):
    return next(p for maison, p in montage['propositions'] if maison == M)


def _raison_attendue(monde, proposition):
    """La raison, lue ici par le test : grenier, réserve, journées, coût, faim, champs, champ et écart."""
    intention = proposition['intention']
    cell_id, cle = intention['cell'], intention['maison']
    t = monde.ticks_ecoules
    champs = sorted((lieu for lieu in monde.cells[cell_id].lieux if lieu.rang >= 1), key=lambda lieu: lieu.rang)
    vivres = [lieu.stocks.get(NOURRITURE, 0) for lieu in champs]
    journees = travail_requis_de_route(intention['points'], intention['largeur_m'])
    places = _places_de(monde, cell_id)
    rang = champs[vivres.index(max(vivres))].rang
    return {
        'regle': 'route_vers_le_champ',
        'grenier_nourriture_kg': monde.greniers[cle].get(NOURRITURE, 0),
        'reserve_voulue_kg': ia._reserve_voulue(monde, _lieux_de_la_maison(monde, cle))['reserve_voulue_kg'],
        'journees': journees,
        'cout_kg': journees * k.SALAIRE_JOURNEE_KG,
        'faim_du_bourg_ticks': sum(1 for tick in range(t - k.FENETRE_FLUX_TICKS, t)
                                   if (cell_id, 0) in monde.flux.jours[tick].affames),
        'champs_nourriture_kg': vivres,
        'champ_vise': rang,
        'ecart_degres': next(
            e for e in _ordre_des_ecarts() if _points_a(places, rang, e) == intention['points']),
    }


def test_sc7_la_raison_dit_ce_qui_a_decide(montage, reference):
    monde = montage['monde']
    attendue = _raison_attendue(monde, reference)
    assert reference['raison'] == attendue

    bourg = monde.cells[reference['intention']['cell']].lieux[0]
    assert bourg.duree_faim_ticks != attendue['faim_du_bourg_ticks']
    sommee = {**attendue, 'champs_nourriture_kg': sum(attendue['champs_nourriture_kg'])}
    lue_au_jour = {**attendue, 'faim_du_bourg_ticks': bourg.duree_faim_ticks}
    sans_regle = {cle: valeur for cle, valeur in attendue.items() if cle != 'regle'}
    for fausse in (sommee, lue_au_jour, sans_regle):
        assert fausse != reference['raison']
        with pytest.raises(AssertionError):
            _controler(monde, [], {**deepcopy(reference), 'raison': fausse})
