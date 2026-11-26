"""Preuves du découpage dérivé des cellules en lieux."""

import copy
import dataclasses
from fractions import Fraction
import json
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

import sim.constants as _constantes
from sim.lieux import Lieu, LieuxInvalides, lieux_de_cellule, lieux_depuis_monde, lieux_par_cellule
from sim.model import _NoBadSpatialField
from sim.world import World


def test_nombre_de_lieux_suit_la_surface(monkeypatch):
    monde = World.charger(0)
    vue = lieux_depuis_monde(monde)
    assert vue and set(vue) == set(monde.cells)
    assert list(vue) == sorted(vue)
    for cell_id, cellule in monde.cells.items():
        attendus = max(1, math.floor(cellule.area_km2 / _constantes.SURFACE_KM2_PAR_LIEU))
        assert len(vue[cell_id]) == attendus >= 1
    lieux_total = sum(map(len, vue.values()))
    cellules_seules = sum(len(lieux) == 1 for lieux in vue.values())
    cellules_multiples = sum(len(lieux) > 1 for lieux in vue.values())
    monkeypatch.setattr(
        _constantes, "SURFACE_KM2_PAR_LIEU", _constantes.SURFACE_KM2_PAR_LIEU * 2
    )
    total_doublé = sum(map(len, lieux_depuis_monde(monde).values()))
    print(f"lieux_total={lieux_total}, cellules_seules={cellules_seules}, "
          f"cellules_multiples={cellules_multiples}, total_doublé={total_doublé}")
    assert lieux_total > len(monde.cells)
    assert cellules_seules > 0 and cellules_multiples > 0
    assert total_doublé < lieux_total


def test_surface_des_lieux_fait_la_cellule_exactement():
    monde = World.charger(0)
    vue = lieux_depuis_monde(monde)
    assert vue and set(vue) == set(monde.cells)
    cellules_exactes = 0
    partages_naifs_inexacts = 0
    for cell_id, lieux in vue.items():
        surface = monde.cells[cell_id].area_km2
        assert lieux and all(lieu.surface_km2 > 0 for lieu in lieux)
        assert sum(Fraction(lieu.surface_km2) for lieu in lieux) == Fraction(surface)
        assert sum(lieu.surface_km2 for lieu in lieux) == surface
        assert all(lieu.surface_km2 == math.floor(lieu.surface_km2) for lieu in lieux[1:])
        assert len({lieu.surface_km2 for lieu in lieux[1:]}) <= 1
        assert lieux[0].surface_km2 == max(lieu.surface_km2 for lieu in lieux)
        cellules_exactes += 1
        partage_naif = [surface / len(lieux)] * len(lieux)
        partages_naifs_inexacts += sum(map(Fraction, partage_naif)) != Fraction(surface)
    print(f"cellules_exactes={cellules_exactes}, "
          f"partages_naifs_inexacts={partages_naifs_inexacts}")
    assert cellules_exactes == len(monde.cells) > 0
    assert partages_naifs_inexacts > 0


def test_identite_et_bourg_unique():
    def champs_attendus(classe):
        return {champ.name for champ in dataclasses.fields(classe)} == {
            "cell_id", "rang", "surface_km2"
        }

    @dataclasses.dataclass(frozen=True)
    class LieuAvecCle(_NoBadSpatialField):
        cell_id: int
        rang: int
        surface_km2: float
        lieu_id: int

    assert champs_attendus(Lieu)
    assert not champs_attendus(LieuAvecCle)
    assert issubclass(Lieu, _NoBadSpatialField)
    with pytest.raises(dataclasses.FrozenInstanceError):
        Lieu(7, 0, 1.0).rang = 1

    monde = World.charger(0)
    vue = lieux_depuis_monde(monde)
    assert vue and set(vue) == set(monde.cells)
    couples = [(lieu.cell_id, lieu.rang) for lieux in vue.values() for lieu in lieux]
    for cell_id, lieux in vue.items():
        assert [lieu.rang for lieu in lieux] == list(range(len(lieux)))
        assert all(lieu.cell_id == cell_id for lieu in lieux)
        assert sum(lieu.est_bourg for lieu in lieux) == 1
        assert lieux[0].est_bourg
        assert all(not lieu.est_bourg for lieu in lieux[1:])
    lieux_total = sum(map(len, vue.values()))
    print(f"lieux_total={lieux_total}, couples_distincts={len(set(couples))}, "
          f"bourgs={sum(lieu.est_bourg for lieux in vue.values() for lieu in lieux)}")
    assert len(couples) == len(set(couples)) == lieux_total > 0


def test_refus_des_surfaces_absentes_ou_invalides(monkeypatch):
    surfaces_invalides = [None, True, "1200", float("nan"), float("inf"), 0, -5.0]
    refus_observés = 0
    for surface in surfaces_invalides:
        with pytest.raises(LieuxInvalides, match="7"):
            lieux_par_cellule({7: surface})
        refus_observés += 1
    with monkeypatch.context() as contexte:
        for valeur in (0.5, float("nan"), float("inf"), True, "1000"):
            contexte.setattr(_constantes, "SURFACE_KM2_PAR_LIEU", valeur)
            with pytest.raises(LieuxInvalides, match="7"):
                lieux_de_cellule(7, 1200.0)
            refus_observés += 1

    monde = copy.deepcopy(World.charger(0))
    plus_petite = min(monde.cells, key=lambda identifiant: monde.cells[identifiant].area_km2)
    monde.cells[plus_petite].area_km2 = None
    with pytest.raises(LieuxInvalides, match=str(plus_petite)):
        lieux_depuis_monde(monde)
    refus_observés += 1
    for surface in (1200.0, 1, 0.3):
        lieux = lieux_par_cellule({7: surface})[7]
        assert len(lieux) == 1 and lieux[0].surface_km2 == surface
        assert lieux[0].est_bourg
    print(f"refus_observés={refus_observés}, surfaces_valides=3")
    assert refus_observés == len(surfaces_invalides) + 5 + 1 > 0


def test_vue_pure_que_le_tick_ne_lit_pas():
    monde = World.charger(0)
    avant = json.dumps(monde.to_dict(), sort_keys=True)
    attributs_avant = {cell_id: vars(cellule).copy() for cell_id, cellule in monde.cells.items()}
    premiere = lieux_depuis_monde(monde)
    seconde = lieux_depuis_monde(monde)
    apres = json.dumps(monde.to_dict(), sort_keys=True)
    attributs_apres = {cell_id: vars(cellule).copy() for cell_id, cellule in monde.cells.items()}
    print(f"vues_identiques={premiere == seconde}, monde_inchangé={avant == apres}, "
          f"attributs_inchangés={attributs_avant == attributs_apres}")
    assert premiere and set(premiere) == set(monde.cells)
    assert premiere == seconde
    assert avant == apres
    assert attributs_avant == attributs_apres


# Habitants et panier persistés, sans calcul économique par lieu.
def _controle_conservation(monde):
    contrôlées = 0
    for cid, cellule in monde.cells.items():
        lieux = cellule.lieux
        assert lieux, f"cell_id={cid} : lieux absents"
        nombre = len(lieux_de_cellule(cid, cellule.area_km2))
        assert [lieu.rang for lieu in lieux] == list(range(nombre)), cid
        assert all(lieu.population >= 0 for lieu in lieux), cid
        assert sum(lieu.population for lieu in lieux) == cellule.population, cid
        for lieu in lieux:
            assert set(lieu.stocks) == set(cellule.stocks), cid
            assert all(quantité >= 0 for quantité in lieu.stocks.values()), cid
        for marchandise, total in cellule.stocks.items():
            parts = [lieu.stocks[marchandise] for lieu in lieux]
            assert sum(parts) == total, (cid, marchandise)
            assert sum(map(Fraction, parts)) == Fraction(total), (cid, marchandise)
        contrôlées += 1
    assert contrôlées > 0
    return contrôlées


def _etats_cellules(monde):
    from sim.model import cellule_vers_dict
    return {cid: {clé: valeur for clé, valeur in cellule_vers_dict(cellule).items()
                  if clé != "lieux"} for cid, cellule in monde.cells.items()}


def _cellule_multiple_peuplee(monde):
    return next(cellule for cellule in monde.cells.values()
                if len(cellule.lieux) > 1 and cellule.lieux[0].population > 0)


def test_partager_plus_fort_reste_et_refus():
    from sim.lieux import partager

    def contrôler(total, poids, parts):
        assert len(parts) == len(poids) > 0
        assert sum(map(Fraction, parts)) == Fraction(total)
        assert all(part >= 0 for part in parts)
        assert all(part == math.floor(part) for part in parts[1:])
        if total == math.floor(total):
            somme = sum(map(Fraction, poids))
            assert all(abs(Fraction(part) - Fraction(total) * Fraction(poids[rang]) / somme) < 1
                       for rang, part in enumerate(parts))

    cas = [(9, [1] * 10), (1234.75, [3, 2, 1]), (0, [0, 1]),
           (17, [0.5, 1.5, 2]), (0.125, [1, 1]), (100, [0, 1, 0])]
    for total, poids in cas:
        contrôler(total, poids, partager(total, poids))
    assert partager(9, [1] * 10) == [1] * 9 + [0]
    assert partager(1234.75, [3, 2, 1])[0] % 1 == 0.75
    invalides = [(1, [-1, 2]), (1, [float("nan")]), (1, [float("inf")]),
                 (1, [True]), (1, [0, 0]), (1, []), (-1, [1]),
                 (float("inf"), [1]), (float("nan"), [1]), (True, [1])]
    refus_observés = 0
    for total, poids in invalides:
        with pytest.raises(LieuxInvalides):
            partager(total, poids)
        refus_observés += 1
    total, poids = cas[0]
    autres = [math.floor(total * poids[rang] / sum(poids)) for rang in range(1, len(poids))]
    with pytest.raises(AssertionError):
        contrôler(total, poids, [total - sum(autres)] + autres)
    print(f"partages_contrôlés={len(cas)}, refus_observés={refus_observés}, biais_naïf_vu=1")
    assert refus_observés == len(invalides) > 0


# Référence prise avant tout remplacement de partager par une contre-épreuve.
from sim.lieux import partager as _partager_reference


def _controle_bourg(monde):
    from sim.model import lire_habitants_par_metier

    différences = non_paysannes_multiples = contrôlées = 0
    for cid, cellule in monde.cells.items():
        surfaces = [lieu.surface_km2 for lieu in lieux_de_cellule(cid, cellule.area_km2)]
        métiers = lire_habitants_par_metier(cellule)
        paysans = cellule.population if métiers == -1 else métiers.get(_constantes.METIER_PAYSANS, 0)
        autres = cellule.population - paysans
        attendus = _partager_reference(paysans, surfaces)
        attendus[0] += autres
        assert [lieu.population for lieu in cellule.lieux] == attendus, f"cell_id={cid} : habitants"
        if autres:
            assert cellule.lieux[0].population >= autres, f"cell_id={cid} : bourg"
        for marchandise, total in cellule.stocks.items():
            if marchandise == _constantes.MARCHANDISE_NOURRITURE:
                # La soudure : chaque lieu porte la ration de ses
                # habitants jusqu'à la moisson, pas une part de surface.
                jours = _constantes.jours_de_soudure(0)
                ration = _constantes.FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK / _constantes.TICK_DURATION_DAYS
                attendue = [lieu.population * ration * jours for lieu in cellule.lieux]
                assert [lieu.stocks[marchandise] for lieu in cellule.lieux] == attendue, (
                    f"cell_id={cid} : {marchandise}")
                assert sum(attendue) == total, f"cell_id={cid} : {marchandise}"
                continue
            assert [lieu.stocks[marchandise] for lieu in cellule.lieux] == _partager_reference(
                total, surfaces), f"cell_id={cid} : {marchandise}"
        différences += attendus != _partager_reference(cellule.population, surfaces)
        non_paysannes_multiples += autres > 0 and len(surfaces) > 1
        contrôlées += 1
    assert contrôlées == len(monde.cells) > 0
    assert différences == non_paysannes_multiples > 0
    return différences


def _controle_champs_etat_de_lieu(classe):
    assert {champ.name for champ in dataclasses.fields(classe)} == {"rang", "population", "stocks", "dette_alimentaire_kg", "duree_faim_ticks", "mortality_remainder", "natalite_remainder", "depart_remainder", "maitre"}


def test_amorcage_conserve_habitants_et_panier(monkeypatch):
    import sim.lieux as lieux_module
    from sim.model import Cell, EtatDeLieu, cellule_vers_dict

    _controle_champs_etat_de_lieu(EtatDeLieu)
    assert issubclass(EtatDeLieu, _NoBadSpatialField)
    monde = World.charger(0)
    contrôlées = _controle_conservation(monde)
    multiples_peuplées = sum(sum(lieu.population > 0 for lieu in cellule.lieux) > 1
                            for cellule in monde.cells.values())
    assert multiples_peuplées > 0
    assert sum(lieu.population for cellule in monde.cells.values() for lieu in cellule.lieux) == sum(
        cellule.population for cellule in monde.cells.values())
    cellule = _cellule_multiple_peuplee(monde)
    différences = _controle_bourg(monde)
    print(f"cellules_avec_non_paysans_et_partage_différent={différences}")
    from sim.model import lire_habitants_par_metier

    minière = next(c for c in monde.cells.values() if len(c.lieux) > 1
                   and c.population > lire_habitants_par_metier(c).get(_constantes.METIER_PAYSANS, 0))
    ancien = copy.deepcopy(monde)
    for c in ancien.cells.values():
        surfaces = [lieu.surface_km2 for lieu in lieux_de_cellule(c.cell_id, c.area_km2)]
        for lieu, population in zip(c.lieux, _partager_reference(c.population, surfaces)):
            lieu.population = population
    _controle_conservation(ancien)
    with pytest.raises(AssertionError, match=f"cell_id={minière.cell_id}"):
        _controle_bourg(ancien)
    déplacé = copy.deepcopy(monde)
    c = déplacé.cells[minière.cell_id]
    autres = c.population - lire_habitants_par_metier(c).get(_constantes.METIER_PAYSANS, 0)
    c.lieux[0].population -= autres
    c.lieux[1].population += autres
    _controle_conservation(déplacé)
    with pytest.raises(AssertionError, match=f"cell_id={minière.cell_id}"):
        _controle_bourg(déplacé)

    # L'absence déclarée de métiers retrouve le partage de tous par surface.
    brut = Cell(cellule.cell_id, cellule.area_km2, cellule.population)
    surfaces = [lieu.surface_km2 for lieu in lieux_de_cellule(brut.cell_id, brut.area_km2)]
    assert lire_habitants_par_metier(brut) == -1
    assert [lieu.population for lieu in lieux_module.amorcer_lieux(brut)] == _partager_reference(
        brut.population, surfaces)
    lectures = 0

    def lire_une_fois(c):
        nonlocal lectures
        lectures += 1
        return lire_habitants_par_metier(c)

    cas = [{_constantes.METIER_PAYSANS: 7, "artisans": 3}, {"artisans": 10}, {}, None]
    with monkeypatch.context() as contexte:
        contexte.setattr(lieux_module, "lire_habitants_par_metier", lire_une_fois)
        for métiers in cas:
            population = 10 if métiers is None else sum(métiers.values())
            c = Cell(cellule.cell_id, cellule.area_km2, population, habitants_par_metier=métiers)
            paysans = population if métiers is None else métiers.get(_constantes.METIER_PAYSANS, 0)
            attendus = _partager_reference(paysans, surfaces)
            attendus[0] += population - paysans
            assert [lieu.population for lieu in lieux_module.amorcer_lieux(c)] == attendus
    assert lectures == len(cas)
    panier = cellule_vers_dict(cellule)["lieux"][0]["stocks"]
    panier.clear()
    assert cellule.lieux[0].stocks
    liste = list(cellule.lieux)
    témoin = Cell(cellule.cell_id, cellule.area_km2, cellule.population, lieux=liste)
    liste.clear()
    assert témoin.lieux and Cell(cellule.cell_id, cellule.area_km2, 0).lieux == []
    corrompu = copy.deepcopy(monde)
    _cellule_multiple_peuplee(corrompu).lieux[0].population -= 1
    with pytest.raises(AssertionError):
        _controle_conservation(corrompu)
    partager = lieux_module.partager

    def perdre_un_habitant(total, poids):
        parts = partager(total, poids)
        if isinstance(total, int) and total > 0:
            parts[next(rang for rang, part in enumerate(parts) if part > 0)] -= 1
        return parts

    monkeypatch.setattr(lieux_module, "partager", perdre_un_habitant)
    with pytest.raises(AssertionError):
        _controle_conservation(World.charger(0))
    print(f"cellules_contrôlées={contrôlées}, multiples_peuplées={multiples_peuplées}, pertes_vues=2")
    assert contrôlées == len(monde.cells)


def test_metiers_lus_a_l_amorcage(monkeypatch):
    # Témoin historique : les deux répartitions ont assez de bras à 0,1.
    monkeypatch.setattr(_constantes, "BRAS_AUX_CHAMPS_PAR_KM2", 0.1)
    import sim.lieux as lieux_module
    import sim.world as monde_module
    from sim.model import ecrire_habitants_par_metier

    appels = 0
    amorcer = lieux_module.amorcer_lieux

    def compter(cellule):
        nonlocal appels
        appels += 1
        return amorcer(cellule)

    def comparer(premier, second):
        assert premier.cells.keys() == second.cells.keys()
        assert premier.cells
        for cid in premier.cells:
            def états(monde):
                return [(lieu.rang, lieu.population, dict(lieu.stocks))
                        for lieu in monde.cells[cid].lieux]
            assert états(premier) == états(second), f"cell_id={cid} : lieux"

    def charger():
        nonlocal appels
        appels = 0
        monde = World.charger(0)
        assert appels == len(monde.cells) > 0
        appels = 0
        paysan = World.charger(0)
        assert appels == len(paysan.cells)
        for cellule in paysan.cells.values():
            ecrire_habitants_par_metier(cellule, {_constantes.METIER_PAYSANS: cellule.population}
                                       if cellule.population else {})
        comparer(monde, paysan)
        appels = 0
        return monde, paysan

    def jouer(monde, paysan, nombre):
        aléas = [random.Random(0), random.Random(0)]
        for numéro in range(nombre):
            tick(monde, aléas[0], numero_tick=numéro)
            tick(paysan, aléas[1], numero_tick=numéro)
            comparer(monde, paysan)

    monkeypatch.setattr(lieux_module, "amorcer_lieux", compter)
    # World lie actuellement la fonction par import : instrumenter aussi cet appel.
    monkeypatch.setattr(monde_module, "amorcer_lieux", compter)
    monde, paysan = charger()
    jouer(monde, paysan, 30)
    assert appels == 0

    def réamorcer(cellule):
        cellule.lieux = lieux_module.amorcer_lieux(cellule)

    monde, paysan = charger()
    monkeypatch.setattr(lieux_module, "repartir_sur_les_lieux", réamorcer)
    with pytest.raises(AssertionError, match="cell_id="):
        jouer(monde, paysan, 1)
    assert appels > 0
    print("ticks_comparés=30, réamorçage_pendant_tick_vu=1")


def test_metiers_lus_a_l_amorcage_bras_calibres(monkeypatch):
    from sim import engine, foyers, lieux, world
    from sim.model import ecrire_habitants_par_metier
    # Au premier mois, les métiers pèsent sur la récolte par la faim qu'ils font
    # venir au bourg : le décor d'avant la soudure (sim/tests/amorcage_d_avant.py),
    # posé avant l'interdit de réamorcer.
    from sim.tests.amorcage_d_avant import amorcer_comme_avant_la_soudure
    amorcer_comme_avant_la_soudure(monkeypatch)

    monde, paysan = World.charger(0), World.charger(0)
    for cellule in paysan.cells.values():
        ecrire_habitants_par_metier(cellule, {_constantes.METIER_PAYSANS: cellule.population}
                                   if cellule.population else {})
    assert monde.cells and monde.cells.keys() == paysan.cells.keys()
    assert all(a.lieux == paysan.cells[cid].lieux for cid, a in monde.cells.items())

    def interdit(*args):
        pytest.fail("réamorçage des lieux pendant un tick")

    monkeypatch.setattr(lieux, "amorcer_lieux", interdit)
    monkeypatch.setattr(world, "amorcer_lieux", interdit)
    vrai_facteur = foyers.facteur_bras
    facteurs, attendus = [], []

    def observer(metiers, km2):
        facteur = vrai_facteur(metiers, km2)
        besoin = km2 * _constantes.BRAS_AUX_CHAMPS_PAR_KM2
        attendu = (1.0 if metiers == -1 or besoin == 0 else
                   min(1.0, metiers.get(_constantes.METIER_PAYSANS, 0) / besoin))
        facteurs.append(facteur)
        attendus.append(attendu)
        return facteur

    def controler(releve):
        assert releve, "relevé de bras vide"
        assert releve == attendus
        assert any(f < 1 for f in releve)

    monkeypatch.setattr(foyers, "facteur_bras", observer)
    aleas = [random.Random(0), random.Random(0)]
    for numero in range(30):
        for m, rng in zip((monde, paysan), aleas):
            engine.tick(m, rng, numero_tick=numero)
            assert _controle_conservation(m) == len(m.cells)
    controler(facteurs)
    with pytest.raises(AssertionError, match="relevé de bras vide"):
        controler([])
    with pytest.raises(AssertionError):
        controler([1.0] * len(facteurs))
    differences = [cid for cid, cellule in monde.cells.items()
                   if cellule.food_stock_kg != paysan.cells[cid].food_stock_kg]
    assert differences, "les métiers doivent peser sur la récolte à 6,2"
    print(f"ticks sans réamorçage=30, facteurs contrôlés={len(facteurs)}, "
          f"cellules aux stocks différents={len(differences)}")


def test_amorcage_documente():
    import pathlib

    def contrôler(texte):
        section = texte.split("### Ce que porte un lieu\n", 1)[1]
        section = section.split("\n### ", 1)[0].split("\n## ", 1)[0]
        for attendu in ("amorcer_lieux", "lire_habitants_par_metier", "paysans", "bourg", "amorçage", "-1", "maitre", "None", "tout lieu chargé"):
            assert attendu in section, f"{attendu} absent de Ce que porte un lieu"
        assert "`amorcer_lieux` partage la population et chaque marchandise selon les surfaces" not in section
        lieux = texte.split("## Les lieux d'une cellule, vue dérivée\n", 1)[1].split("\n## ", 1)[0]
        assert "ni ceux de `RepartitionBourg`" not in lieux

    texte = (pathlib.Path(__file__).parents[1] / "MODELE.md").read_text(encoding="utf-8")
    contrôler(texte)
    with pytest.raises(AssertionError, match="maitre"): contrôler(texte.replace("maitre", "attribut retiré"))
    avant, reste = texte.split("### Ce que porte un lieu\n", 1)
    section, après = reste.split("\n### ", 1)
    with pytest.raises(AssertionError, match="paysans"):
        contrôler(avant + "### Ce que porte un lieu\n" + section.replace("paysans", "gens")
                  + "\n### " + après)


def test_tick_repartit_sur_une_annee_et_suit_les_ecritures(monkeypatch):
    import random
    import time
    import sim.lieux as lieux_module
    from sim.engine import tick

    monde = World.charger(0)
    rng = random.Random(0)
    répartir = lieux_module.repartir_sur_les_lieux
    temps_répartition = 0.0

    def mesurer(cellule):
        nonlocal temps_répartition
        début = time.perf_counter()
        répartir(cellule)
        temps_répartition += time.perf_counter() - début

    populations_modifiées, marchandises_apparues, lieux_modifiés = set(), set(), set()
    temps_ticks = 0.0
    nombre_ticks = _constantes.CALENDAR_DAYS_PER_YEAR
    with monkeypatch.context() as contexte:
        contexte.setattr(lieux_module, "repartir_sur_les_lieux", mesurer)
        for numéro in range(nombre_ticks):
            avant = {cid: (cellule.population, set(cellule.stocks),
                          [(lieu.population, dict(lieu.stocks)) for lieu in cellule.lieux])
                     for cid, cellule in monde.cells.items()}
            début = time.perf_counter()
            tick(monde, rng, numero_tick=numéro)
            temps_ticks += time.perf_counter() - début
            assert _controle_conservation(monde) == len(monde.cells)
            for cid, cellule in monde.cells.items():
                population, marchandises, contenus = avant[cid]
                from sim.model import lire_habitants_par_metier
                assert sum(lire_habitants_par_metier(cellule).values()) == cellule.population
                if cellule.population != population:
                    populations_modifiées.add(cid)
                marchandises_apparues.update((cid, nom) for nom in set(cellule.stocks) - marchandises)
                lieux_modifiés.update((cid, lieu.rang) for lieu, contenu in zip(cellule.lieux, contenus)
                                      if (lieu.population, lieu.stocks) != contenu)
    assert populations_modifiées and marchandises_apparues and lieux_modifiés
    print(f"cellules_population_modifiée={len(populations_modifiées)}, "
          f"marchandises_apparues={len(marchandises_apparues)}, lieux_modifiés={len(lieux_modifiés)}, "
          f"ticks={nombre_ticks}, temps_moyen_tick={temps_ticks / nombre_ticks:.6f}s, "
          f"part_répartition={temps_répartition / temps_ticks:.2%}")

    synthétique = World.charger(0)
    cellule = _cellule_multiple_peuplee(synthétique)
    surfaces = [lieu.surface_km2 for lieu in lieux_de_cellule(cellule.cell_id, cellule.area_km2)]
    cellule.stocks["sonde_retirée"] = 17
    répartir(cellule)
    del cellule.stocks["sonde_retirée"]
    cellule.stocks["sonde"] = 1234.75
    cellule.population += len(cellule.lieux)
    poids_population = [lieu.population for lieu in cellule.lieux]
    reprises = []

    def controler_reprise(c, surfaces, poids_population):
        assert [lieu.stocks.get("sonde", 0) for lieu in c.lieux] == lieux_module.partager(c.stocks["sonde"], surfaces)
        assert all("sonde_retirée" not in lieu.stocks for lieu in c.lieux)
        assert [lieu.population for lieu in c.lieux] == lieux_module.partager(c.population, poids_population)

    def observer_reprise(c):
        répartir(c)
        if c is cellule:
            controler_reprise(c, surfaces, poids_population)
            reprises.append(c.stocks["sonde"])

    with monkeypatch.context() as contexte:
        contexte.setattr(lieux_module, "repartir_sur_les_lieux", observer_reprise)
        tick(synthétique, random.Random(0), numero_tick=0)
    assert reprises == [1234.75]
    assert 0 < cellule.stocks["sonde"] < reprises[0]
    assert sum(lieu.stocks["sonde"] for lieu in cellule.lieux) == cellule.stocks["sonde"]
    assert _controle_conservation(synthétique) == len(synthétique.cells)
    del cellule.stocks["sonde"]
    répartir(cellule)
    assert all("sonde" not in lieu.stocks for lieu in cellule.lieux)
    avant = copy.deepcopy(cellule.lieux)
    répartir(cellule)
    assert cellule.lieux == avant
    for lieu in cellule.lieux:
        lieu.population = 0
    répartir(cellule)
    assert [lieu.population for lieu in cellule.lieux] == lieux_module.partager(cellule.population, surfaces)
    témoin = World.charger(0)
    cible = _cellule_multiple_peuplee(témoin)
    cible.population += 7
    cible.stocks["sonde"] = 1234.75
    surfaces_cible = [lieu.surface_km2 for lieu in lieux_de_cellule(cible.cell_id, cible.area_km2)]
    poids_cible = [lieu.population for lieu in cible.lieux]
    def reprise_inerte(c):
        if c is cible:
            controler_reprise(c, surfaces_cible, poids_cible)
    monkeypatch.setattr(lieux_module, "repartir_sur_les_lieux", reprise_inerte)
    with pytest.raises(AssertionError):
        tick(témoin, random.Random(0), numero_tick=0)


def test_cellule_depend_du_contenu_des_lieux(monkeypatch):
    import random
    from sim.engine import tick
    # La contre-épreuve demande des lieux qui manquent dans le premier mois :
    # le décor d'avant la soudure (sim/tests/amorcage_d_avant.py).
    from sim.tests.amorcage_d_avant import amorcer_comme_avant_la_soudure
    amorcer_comme_avant_la_soudure(monkeypatch)

    monkeypatch.setattr(_constantes, "CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK", float("inf"))
    from sim import engine
    consommation = engine._apply_consumption
    def verifier_consommation(capacite):
        monkeypatch.setattr(_constantes, "CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK", capacite)
        monde, rng = World.charger(0), random.Random(0)
        def comparer(cellule, carte=None):
            copie, sans = copy.deepcopy(cellule), copy.deepcopy(cellule)
            sans.lieux = []
            assert consommation(copie, carte) == consommation(sans, carte)
            assert copie.population == sans.population
            assert copie.stocks == sans.stocks
            assert copie.food_deficit_kg == sans.food_deficit_kg
            assert not (any(l.duree_faim_ticks > 0 for l in copie.lieux)
                        and any(l.stocks.get("nourriture", 0) > 0 for l in copie.lieux))
            return consommation(cellule, carte)
        with monkeypatch.context() as garde:
            garde.setattr(engine, "_apply_consumption", comparer)
            for numero in range(30):
                tick(monde, rng, numero_tick=numero)
        return monde
    avec = verifier_consommation(float("inf"))
    with pytest.raises(AssertionError):
        verifier_consommation(0)
    print(f"cellules_comparées={len(avec.cells)}, ticks_consommation_avant_démographie=30, capacité_nulle_vue=1")

    from sim import engine
    monkeypatch.setattr(_constantes, "CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK", 0)
    # Morts et naissances s'arrondissent lieu par lieu : déplacer des habitants
    # changerait la cellule même avec une consommation gratuite. On les fige
    # dans les deux courses pour que seul le contenu des lieux, par la
    # consommation, puisse faire l'écart.
    monkeypatch.setattr(engine, "_apply_mortality", lambda cellule, *facteurs: None)
    monkeypatch.setattr(engine, "_apply_natalite", lambda cellule, penurie_kg, *facteurs: None)
    def verifier_ecart():
        source = World.charger(0)
        modifié = copy.deepcopy(source)
        cellule = next(c for c in modifié.cells.values() if len(c.lieux) > 1 and
                       _constantes.part_miniere_de(modifié.carte[c.cell_id].get("gisements"),
                                                  _constantes.facteurs_richesse_extraction()) > 0)
        non_paysans = cellule.population - cellule.habitants_par_metier["paysans"]
        assert non_paysans > 0
        cellule.lieux[0].population -= non_paysans
        cellule.lieux[1].population += non_paysans
        assert _controle_conservation(source) == _controle_conservation(modifié)
        rng_source, rng_modifié = random.Random(0), random.Random(0)
        for numéro in range(10):
            tick(source, rng_source, numero_tick=numéro)
            tick(modifié, rng_modifié, numero_tick=numéro)
            if _etats_cellules(source) != _etats_cellules(modifié):
                print(f"écart_cellule={cellule.cell_id}, tick={numéro + 1}")
                return
        raise AssertionError("aucun écart sans chemin après déplacement des non-paysans")
    verifier_ecart()
    original = engine._apply_consumption
    from sim import foyers
    with monkeypatch.context() as sonde:
        sonde.setattr(engine, "_apply_consumption", lambda cellule, carte=None: original(cellule))
        sonde.setattr(foyers, "facteur_bras", lambda metiers, km2: 1.0)
        with pytest.raises(AssertionError, match="aucun écart"):
            verifier_ecart()


def test_photographie_et_empreinte_portent_les_lieux():
    import hashlib
    import pathlib
    import random
    import subprocess
    import sys
    from sim.engine import tick
    from sim.snapshot_export import SnapshotExportError, build_snapshot_document, serialize_snapshot

    courses = [World.charger(0), World.charger(0)]
    for monde in courses:
        rng = random.Random(0)
        for numéro in range(25):
            tick(monde, rng, numero_tick=numéro)
    assert json.dumps(courses[0].to_dict(), sort_keys=True) == json.dumps(courses[1].to_dict(), sort_keys=True)
    assert all("lieux" in cellule for cellule in courses[0].to_dict()["cells"].values())
    monde = World.charger(0)
    document = build_snapshot_document(monde, 0, 0)
    assert document["cells"]
    for cellule in document["cells"]:
        cid = cellule["cell_id"]
        vue = lieux_de_cellule(cid, monde.cells[cid].area_km2)
        assert len(cellule["lieux"]) == len(vue) > 0
        assert [lieu["rang"] for lieu in cellule["lieux"]] == list(range(len(vue)))
        assert all(set(lieu) == {"rang", "surface_km2", "population", "stocks", "maitre", "point", "nom", "flux_30j"} for lieu in cellule["lieux"])
        assert [lieu["surface_km2"] for lieu in cellule["lieux"]] == [lieu.surface_km2 for lieu in vue]
        assert sum(lieu["population"] for lieu in cellule["lieux"]) == cellule["population"]
    def verifier_maitres(photo):
        maisons = {maison.id for maison in monde.maisons}
        assert photo["cells"] and maisons
        for cellule in photo["cells"]:
            assert cellule["lieux"]
            for lieu in cellule["lieux"]:
                assert set(lieu) == {"rang", "surface_km2", "population", "stocks", "maitre", "point", "nom", "flux_30j"}
                assert lieu["maitre"] is not None and lieu["maitre"] in maisons
                assert lieu["maitre"] == monde.cells[cellule["cell_id"]].lieux[lieu["rang"]].maitre
    verifier_maitres(document)
    premier = document["cells"][0]
    autre = next(m.id for m in monde.maisons if m.id != premier["lieux"][0]["maitre"])
    for valeur in (None, "maison-absente-du-registre", autre):
        faux = copy.deepcopy(document)
        if valeur is None: faux["cells"][0]["lieux"][0].pop("maitre")
        else: faux["cells"][0]["lieux"][0]["maitre"] = valeur
        with pytest.raises(AssertionError): verifier_maitres(faux)
    etat_avant = monde.to_dict()
    lieu = monde.cells[premier["cell_id"]].lieux[0]
    ancien = lieu.maitre
    lieu.maitre = autre
    etat_apres = monde.to_dict()
    assert etat_apres != etat_avant
    etat_apres["cells"][str(premier["cell_id"])]["lieux"][0]["maitre"] = ancien
    assert etat_apres == etat_avant
    assert hashlib.sha256(serialize_snapshot(build_snapshot_document(monde, 0, 0))).digest() != hashlib.sha256(serialize_snapshot(document)).digest()
    lieu.maitre = ancien
    assert serialize_snapshot(document) == serialize_snapshot(build_snapshot_document(monde, 0, 0))
    commande = [sys.executable, "-m", "sim", "--ticks", "0", "--seed", "0", "--json"]
    dossier = pathlib.Path(__file__).parents[2]
    assert subprocess.check_output(commande, cwd=dossier) == subprocess.check_output(commande, cwd=dossier)
    empreinte_avant = json.dumps(monde.to_dict(), sort_keys=True)
    sha_avant = hashlib.sha256(serialize_snapshot(document)).hexdigest()
    cellule = _cellule_multiple_peuplee(monde)
    cellule.lieux[0].population -= 1
    cellule.lieux[1].population += 1
    assert _controle_conservation(monde) == len(monde.cells)
    assert json.dumps(monde.to_dict(), sort_keys=True) != empreinte_avant
    assert hashlib.sha256(serialize_snapshot(build_snapshot_document(monde, 0, 0))).hexdigest() != sha_avant
    cellule.lieux.pop()
    with pytest.raises(SnapshotExportError, match=str(cellule.cell_id)):
        build_snapshot_document(monde, 0, 0)
    print(f"cellules_photographiées={len(document['cells'])}, courses_identiques=2, empreintes_modifiées=2, refus_vu=1")

import random

from sim.engine import tick
from sim.lieux import LieuInconnu, lieu_du_monde


def test_chaque_lieu_se_retrouve_par_son_couple():
    monde = World.charger(0)
    vue = lieux_depuis_monde(monde)
    assert vue
    lieux_retrouvés = 0
    for lieux in vue.values():
        for lieu in lieux:
            assert lieu_du_monde(monde, lieu.cell_id, lieu.rang) == lieu
            lieux_retrouvés += 1
    print(f"lieux_retrouvés={lieux_retrouvés}")
    assert lieux_retrouvés == sum(map(len, vue.values())) > 0

    cellules = [cid for cid, lieux in vue.items() if len(lieux) >= 2]
    assert cellules
    c = min(cellules)
    n = len(vue[c])
    # L'indexation naïve rend le dernier lieu ; le rang négatif est refusé.
    dernier = lieux_depuis_monde(monde)[c][-1]
    assert isinstance(dernier, Lieu) and dernier.cell_id == c
    with pytest.raises(LieuInconnu):
        lieu_du_monde(monde, c, -1)
    with pytest.raises(LieuInconnu):
        lieu_du_monde(monde, c, n)


def test_refus_du_couple():
    monde = World.charger(0)
    c = min(monde.cells)
    couples_mal_formes = [
        (True, 0),
        (c, True),
        (c, False),
        (str(c), 0),
        (c, "0"),
        (float(c), 0),
        (c, 0.0),
        (None, 0),
        (c, None),
    ]
    couples_inconnus = [
        (max(monde.cells) + 1, 0),
        (c, -1),
    ]
    refus_observés = 0
    for cell_id, rang in couples_mal_formes:
        with pytest.raises(LieuxInvalides) as info:
            lieu_du_monde(monde, cell_id, rang)
        assert not isinstance(info.value, LieuInconnu)
        message = str(info.value)
        assert repr(cell_id) in message and repr(rang) in message
        refus_observés += 1
    for cell_id, rang in couples_inconnus:
        with pytest.raises(LieuInconnu) as info:
            lieu_du_monde(monde, cell_id, rang)
        message = str(info.value)
        assert repr(cell_id) in message and repr(rang) in message
        refus_observés += 1
    print(f"refus_observés={refus_observés}")
    assert refus_observés == len(couples_mal_formes) + len(couples_inconnus) > 0

    copie = copy.deepcopy(monde)
    copie.cells[c].area_km2 = None
    with pytest.raises(LieuxInvalides) as info:
        lieu_du_monde(copie, c, 0)
    assert str(c) in str(info.value)

    bourg = lieu_du_monde(monde, c, 0)
    assert bourg.est_bourg and bourg.cell_id == c and bourg.rang == 0
    with pytest.raises(LieuxInvalides) as info:
        lieu_du_monde(monde, True, 0)
    assert not isinstance(info.value, LieuInconnu)


def test_le_tick_ne_detache_pas_un_lieu():
    monde = World.charger(0)
    avant = lieux_depuis_monde(monde)
    populations = {
        cid: cellule.population for cid, cellule in monde.cells.items()
    }
    alea = random.Random(0)
    for numero in range(30):
        tick(monde, alea, numero_tick=numero)
    apres = lieux_depuis_monde(monde)
    cellules_changées = sum(
        monde.cells[cid].population != populations[cid] for cid in monde.cells
    )
    assert apres == avant
    assert cellules_changées > 0

    copie = copy.deepcopy(monde)
    plus_grande = max(
        copie.cells, key=lambda cid: copie.cells[cid].area_km2
    )
    copie.cells[plus_grande].area_km2 /= 2
    vue_rognee = lieux_depuis_monde(copie)
    cellules_détachées = sum(
        vue_rognee[cid] != apres[cid] for cid in apres
    )
    print(
        f"cellules_changées={cellules_changées}, "
        f"cellules_détachées={cellules_détachées}"
    )
    assert cellules_détachées == 1


def test_ni_la_graine_ni_l_ordre_ne_changent_l_identite():
    monde_0 = World.charger(0)
    monde_1 = World.charger(1)
    vue_0 = lieux_depuis_monde(monde_0)
    vue_1 = lieux_depuis_monde(monde_1)
    assert vue_0 == vue_1
    populations_différentes = sum(
        monde_0.cells[cid].population != monde_1.cells[cid].population
        for cid in monde_0.cells
    )
    assert populations_différentes > 0

    copie = copy.deepcopy(monde_0)
    copie.cells = {
        cle: copie.cells[cle] for cle in reversed(tuple(monde_0.cells))
    }
    vue_inverse = lieux_depuis_monde(copie)
    assert vue_inverse == vue_0
    assert list(vue_inverse) == list(vue_0)
    for lieux in vue_0.values():
        for lieu in lieux:
            assert lieu_du_monde(monde_0, lieu.cell_id, lieu.rang) == lieu
            assert lieu_du_monde(copie, lieu.cell_id, lieu.rang) == lieu

    def numeros_globaux(world):
        numeros = {}
        position = 0
        for cell_id, cellule in world.cells.items():
            lieux = lieux_de_cellule(
                cell_id, getattr(cellule, "area_km2", None)
            )
            for lieu in lieux:
                numeros[(lieu.cell_id, lieu.rang)] = position
                position += 1
        return numeros

    origine = numeros_globaux(monde_0)
    inverse = numeros_globaux(copie)
    numéros_globaux_déplacés = sum(
        origine[couple] != inverse[couple] for couple in origine
    )
    print(
        f"populations_différentes={populations_différentes}, "
        f"numéros_globaux_déplacés={numéros_globaux_déplacés}"
    )
    assert numéros_globaux_déplacés > 0


def test_la_constante_renumerote(monkeypatch):
    monde = World.charger(0)
    vue = lieux_depuis_monde(monde)
    candidats = [cid for cid, lieux in vue.items() if len(lieux) >= 3]
    assert candidats
    c = min(candidats)
    n = len(vue[c])
    lieu = lieu_du_monde(monde, c, n - 1)
    assert lieu.cell_id == c and lieu.rang == n - 1
    monkeypatch.setattr(
        _constantes,
        "SURFACE_KM2_PAR_LIEU",
        _constantes.SURFACE_KM2_PAR_LIEU * 2,
    )
    with pytest.raises(LieuInconnu):
        lieu_du_monde(monde, c, n - 1)
    n_apres = len(lieux_de_cellule(c, monde.cells[c].area_km2))
    print(f"lieux_avant={n}, lieux_apres={n_apres}")
    assert n_apres < n


def _donnees_plan():
    """Un plan complet ; les mêmes numéros peuvent servir dans deux listes."""
    triangle = [(0, 0), (10, 0), (0, 10)]
    return {
        "rues": [{"identifiant": 7, "points": [(0, 0), (10, 0)], "largeur_m": 4}],
        "parcelles": [{"identifiant": 7, "contour": triangle}],
        "batiments": [{"identifiant": 7, "parcelle": 7, "nature": "atelier", "emprise": triangle}],
    }


def _construire_plan(document):
    from sim.plan import Batiment, Parcelle, Plan, Rue

    return Plan(
        rues=[Rue(**entree) for entree in document["rues"]],
        parcelles=[Parcelle(**entree) for entree in document["parcelles"]],
        batiments=[Batiment(**entree) for entree in document["batiments"]],
    )


def test_plan_valide_trie_et_serialise_sans_muter():
    donnees = _donnees_plan()
    for liste in donnees.values():
        entree = copy.deepcopy(liste[0])
        entree["identifiant"] = 1
        liste.append(entree)
    avant = copy.deepcopy(donnees)
    a = _construire_plan(donnees)
    b = _construire_plan(donnees)
    for liste in (a.rues, a.parcelles, a.batiments):
        assert [entree.identifiant for entree in liste] == [1, 7]
    document = a.to_dict()
    assert all([entree["identifiant"] for entree in liste] == [1, 7]
               for liste in document.values())
    assert document["rues"][0]["points"] == [[0, 0], [10, 0]]
    assert document["batiments"][0]["nature"] == "atelier"
    assert json.dumps(document, sort_keys=True) == json.dumps(b.to_dict(), sort_keys=True)
    assert donnees == avant
    document["rues"][0]["points"][0][0] = 999
    assert a.to_dict() != document


@pytest.mark.parametrize("liste,champ,valeur,message", [
    *[("rues", "points", [(v, 0), (1, 0)], "points")
      for v in (float("nan"), float("inf"), -float("inf"), True, "0", None)],
    ("rues", "points", [(0, 0)], "points"),
    ("rues", "points", [(0,), (1, 0)], "point"),
    *[("rues", "largeur_m", v, "largeur_m")
      for v in (0, -1, float("nan"), float("inf"), True, "4", None)],
    ("parcelles", "contour", [(0, 0), (1, 0)], "contour"),
    ("parcelles", "contour", [(0, 0), (1, True), (0, 1)], "contour"),
    ("batiments", "emprise", [(0, 0), (1, 0)], "emprise"),
    ("batiments", "emprise", [(0, 0), (1, 0), (0, float("nan"))], "emprise"),
    *[("batiments", "nature", v, "nature") for v in ("", "  ", None, 42)],
    ("batiments", "parcelle", 99, "parcelle"),
    *[("batiments", "parcelle", v, "parcelle") for v in (True, "7", -1)],
    *[(liste, "identifiant", v, "identifiant")
      for liste in ("rues", "parcelles", "batiments") for v in (-1, True, "7", 1.5)],
    *[(liste, "doublon", None, "double") for liste in ("rues", "parcelles", "batiments")],
])
def test_plan_refuse_un_seul_defaut(liste, champ, valeur, message):
    from sim.plan import PlanInvalide

    donnees = _donnees_plan()
    assert _construire_plan(donnees).to_dict()
    if champ == "doublon":
        donnees[liste].append(copy.deepcopy(donnees[liste][0]))
    else:
        donnees[liste][0][champ] = valeur
    with pytest.raises(PlanInvalide, match=message):
        _construire_plan(donnees)


def test_plan_relit_les_minimums(monkeypatch):
    from sim.plan import PlanInvalide

    for constante, message in (("POINTS_MIN_RUE", "points"), ("POINTS_MIN_CONTOUR", "contour")):
        with monkeypatch.context() as contexte:
            contexte.setattr(_constantes, constante, getattr(_constantes, constante) + 1)
            with pytest.raises(PlanInvalide, match=message):
                _construire_plan(_donnees_plan())


@pytest.mark.parametrize("liste", ["rues", "parcelles", "batiments"])
@pytest.mark.parametrize("valeur", [None, (), [None]])
def test_plan_refuse_une_liste_absente_ou_un_element_invalide(liste, valeur):
    from sim.plan import Plan, PlanInvalide

    with pytest.raises(PlanInvalide, match=liste):
        Plan(**{liste: valeur})


def test_plan_refuse_un_defaut_ajoute_apres_construction():
    from sim.plan import PlanInvalide

    plan = _construire_plan(_donnees_plan())
    plan.rues.append(plan.rues[0])
    with pytest.raises(PlanInvalide, match="double"):
        plan.to_dict()
    plan = _construire_plan(_donnees_plan())
    plan.rues[0].points[0] = (float("nan"), 0)
    with pytest.raises(PlanInvalide, match="points"):
        plan.to_dict()


def test_plan_accepte_des_metres_locaux_sans_borne_inventee():
    donnees = _donnees_plan()
    donnees["rues"][0]["points"] = [(-1e12, -1e12), (1e12, 1e12)]
    donnees["batiments"][0]["emprise"] = [(-100, -100), (-90, -100), (-100, -90)]
    document = _construire_plan(donnees).to_dict()
    assert document["rues"][0]["points"] == [[-1e12, -1e12], [1e12, 1e12]]
    assert document["batiments"][0]["emprise"][0] == [-100, -100]


def test_enceinte_absente_puis_canonique():
    from sim.plan import Enceinte, Plan, PlanInvalide

    vide = Plan()
    assert vide.enceinte is None and "enceinte" not in vide.to_dict()
    assert vide.to_dict() == {"rues": [], "parcelles": [], "batiments": []}
    triangle = [(0, 0), (3, 0), (0, 4)]
    enceinte = Enceinte(triangle, en_chantier=True, foyers=1, travail_requis=12, travail_fourni=0)
    assert len(enceinte.contour) >= _constantes.POINTS_MIN_CONTOUR
    assert enceinte.en_chantier == (enceinte.travail_fourni < enceinte.travail_requis)
    assert enceinte.foyers >= 1 and enceinte.travail_fourni <= enceinte.travail_requis
    ancienne = Enceinte(triangle)
    assert (ancienne.en_chantier, ancienne.foyers, ancienne.travail_requis, ancienne.travail_fourni) == (
        False, 0, 0, 0)
    document = Plan(enceinte=enceinte).to_dict()
    assert document["enceinte"] == {
        "contour": [[0, 0], [3, 0], [0, 4]],
        "en_chantier": True, "foyers": 1, "travail_requis": 12, "travail_fourni": 0}
    document["enceinte"]["contour"][0][0] = 999
    assert Plan(enceinte=enceinte).to_dict()["enceinte"]["contour"][0] == [0, 0]
    with pytest.raises(PlanInvalide, match="enceinte"):
        Plan(enceinte=[triangle])


@pytest.mark.parametrize("champs,message", [
    ({"contour": [(0, 0), (1, 0)]}, "points"),
    ({"contour": [(float("nan"), 0), (1, 0), (0, 1)]}, "fini"),
    ({"foyers": True}, "invalide"),
    ({"travail_fourni": 2}, "dépasse"),
    ({"en_chantier": False}, "contredit"),
    ({"foyers": 0}, "sans foyer"),
])
def test_enceinte_refuse_contour_ou_chantier(champs, message):
    from sim.plan import Enceinte, PlanInvalide

    base = {"contour": [(0, 0), (1, 0), (0, 1)], "en_chantier": True,
            "foyers": 1, "travail_requis": 1, "travail_fourni": 0}
    with pytest.raises(PlanInvalide, match=message):
        Enceinte(**(base | champs))


def _controle_dette_et_faim_des_lieux(monde):
    mixtes = 0
    assert monde.cells
    for cellule in monde.cells.values():
        assert cellule.lieux
        dettes = [lieu.dette_alimentaire_kg for lieu in cellule.lieux]
        assert sum(dettes) == cellule.food_deficit_kg
        assert sum(map(Fraction, dettes)) == Fraction(cellule.food_deficit_kg)
        assert min(dettes) >= 0
        faims = [lieu.duree_faim_ticks for lieu in cellule.lieux]
        assert (cellule.hunger_ticks > 0) == any(faim > 0 for faim in faims)
        assert all(0 <= faim <= cellule.hunger_ticks for faim in faims)
        mixtes += any(faims) and not all(faims)
    return mixtes


def test_dette_et_faim_des_lieux(monkeypatch):
    from sim import engine
    from sim.model import cellule_vers_dict
    capacite = _constantes.CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK
    for reglage in (capacite, 0):
        monkeypatch.setattr(_constantes, "CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK", reglage)
        monde, rng, mixtes = World.charger(0), random.Random(0), 0
        _controle_dette_et_faim_des_lieux(monde)
        for numero in range(60):
            tick(monde, rng, numero_tick=numero)
            mixtes += _controle_dette_et_faim_des_lieux(monde)
        if reglage == 0:
            assert mixtes > 0
        print(f"capacite={reglage}, couples_cellule_tick_faim_mixte={mixtes}")
    monkeypatch.setattr(engine, "_porter_dette_et_faim_sur_les_lieux", lambda *args: None)
    temoin = World.charger(0)
    tick(temoin, random.Random(0), numero_tick=0)
    assert any(c.food_deficit_kg > 0 for c in temoin.cells.values())
    with pytest.raises(AssertionError):
        _controle_dette_et_faim_des_lieux(temoin)

    def verifier_empreinte(serialiser):
        for cellule in monde.cells.values():
            for lieu in serialiser(cellule)["lieux"]:
                assert {"dette_alimentaire_kg", "duree_faim_ticks"} <= set(lieu)
    verifier_empreinte(cellule_vers_dict)
    def omettre(cellule):
        document = cellule_vers_dict(cellule)
        for lieu in document["lieux"]:
            del lieu["dette_alimentaire_kg"], lieu["duree_faim_ticks"]
        return document
    with pytest.raises(AssertionError):
        verifier_empreinte(omettre)
    avant = json.dumps(monde.to_dict(), sort_keys=True)
    next(iter(monde.cells.values())).lieux[0].dette_alimentaire_kg += 1
    assert json.dumps(monde.to_dict(), sort_keys=True) != avant


def test_dette_a_un_effet_sur_le_monde(monkeypatch):
    from sim import engine
    monkeypatch.setattr(_constantes, "CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK", 0)
    def courses(sans_portage):
        normal, temoin = World.charger(0), World.charger(0)
        rng_normal, rng_temoin = random.Random(0), random.Random(0)
        for numero in range(60):
            tick(normal, rng_normal, numero_tick=numero)
            with monkeypatch.context() as garde:
                if sans_portage:
                    garde.setattr(engine, "_porter_dette_et_faim_sur_les_lieux", lambda *args: None)
                tick(temoin, rng_temoin, numero_tick=numero)
        return [sum(c.population for c in monde.cells.values()) for monde in (normal, temoin)]
    def verifier(populations):
        assert populations[0] != populations[1]
    populations = courses(True)
    verifier(populations)
    with pytest.raises(AssertionError): verifier(courses(False))
    print(f"ticks=60, populations_avec_et_sans_dettes_locales={populations}, courses_normales_refusées=1")


def test_demographie_locale_etat(monkeypatch, tmp_path):
    import ast
    import sim.model as modele
    from sim.tests import test_write_coverage as couverture
    champs = ("mortality_remainder", "natalite_remainder")
    lieu = modele.creer_etat_de_lieu(0, 5, {})
    assert all(getattr(lieu, champ) == 0.0 for champ in champs)
    explicite = modele.creer_etat_de_lieu(0, 5, {}, mortality_remainder=0.5, natalite_remainder=0.75)
    assert [getattr(explicite, champ) for champ in champs] == [0.5, 0.75]
    import inspect
    constructeur = next(n for n in ast.walk(ast.parse(inspect.getsource(modele.creer_etat_de_lieu)))
                        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                        and n.func.id == "EtatDeLieu")
    def verifier_ecrivains(appel):
        assert set(champs) <= {kw.arg for kw in appel.keywords}
    verifier_ecrivains(constructeur)
    for champ in champs:
        sans_ecrivain = copy.deepcopy(constructeur)
        sans_ecrivain.keywords = [kw for kw in sans_ecrivain.keywords if kw.arg != champ]
        with pytest.raises(AssertionError): verifier_ecrivains(sans_ecrivain)
    monde = World.charger(0)
    avant = json.dumps(monde.to_dict(), sort_keys=True)
    for champ in champs:
        copie = copy.deepcopy(monde)
        setattr(next(iter(copie.cells.values())).lieux[0], champ, 0.5)
        assert json.dumps(copie.to_dict(), sort_keys=True) != avant
        def verifier():
            assert all(champ in l for l in modele.cellule_vers_dict(next(iter(monde.cells.values())))["lieux"])
        verifier()
        with monkeypatch.context() as garde:
            garde.setattr(modele, "asdict", lambda l: {k: v for k, v in dataclasses.asdict(l).items() if k != champ})
            with pytest.raises(AssertionError): verifier()
        for mode in ("lecture", "écriture"):
            class Omettre(ast.NodeTransformer):
                def visit_Attribute(self, noeud):
                    if mode == "lecture" and noeud.attr == champ and isinstance(noeud.ctx, ast.Load):
                        return ast.copy_location(ast.Constant(0.0), noeud)
                    return self.generic_visit(noeud)
                def visit_Call(self, noeud):
                    self.generic_visit(noeud)
                    if mode == "écriture":
                        noeud.keywords = [kw for kw in noeud.keywords if kw.arg != champ]
                    return noeud
                def visit_Assign(self, noeud):
                    if mode == "écriture" and any(isinstance(c, ast.Attribute) and c.attr == champ
                                                 for c in noeud.targets):
                        return ast.copy_location(ast.Pass(), noeud)
                    return self.generic_visit(noeud)
            fichiers = []
            for fichier in couverture._SIM_SOURCE_FILES:
                cible = tmp_path / fichier.name
                cible.write_text(ast.unparse(Omettre().visit(ast.parse(fichier.read_text()))), encoding="utf-8")
                fichiers.append(cible)
            with monkeypatch.context() as garde:
                garde.setattr(couverture, "_SIM_SOURCE_FILES", fichiers)
                with pytest.raises(AssertionError, match=f"{champ} : aucun site d.*{mode}"):
                    couverture.test_all_dataclass_fields_have_write_and_read_sites()


def test_demographie_locale_mortalite(monkeypatch):
    from sim import engine
    from sim.model import Cell, creer_etat_de_lieu
    def verifier():
        cellule = Cell(0, 2000, 10, habitants_par_metier={"mineurs": 5, "paysans": 5},
                       mortality_remainder=0.9, food_deficit_kg=1000)
        cellule.lieux = [creer_etat_de_lieu(0, 5, {}, dette_alimentaire_kg=1000),
                         creer_etat_de_lieu(1, 5, {}, mortality_remainder=0.3)]
        voisin = copy.deepcopy(cellule.lieux[1])
        appels, retirer = [], engine._retirer_par_les_foyers
        with monkeypatch.context() as garde:
            garde.setattr(engine, "_retirer_par_les_foyers", lambda c, n: (appels.append(n), retirer(c, n)))
            engine._apply_mortality(cellule)
            assert [l.population for l in cellule.lieux] == [5, 5]
            assert [l.mortality_remainder for l in cellule.lieux] == [0.5, 0.3]
            assert cellule.population == sum(l.population for l in cellule.lieux)
            engine._apply_mortality(cellule)
        assert [l.population for l in cellule.lieux] == [4, 5]
        assert appels == [0, 1]
        assert cellule.population == sum(l.population for l in cellule.lieux) == 9
        assert cellule.habitants_par_metier == {"mineurs": 4, "paysans": 5}
        assert cellule.mortality_remainder == 0.9
        assert cellule.lieux[0].dette_alimentaire_kg == 1000 and cellule.lieux[1] == voisin
        from sim.lieux import repartir_sur_les_lieux
        coherents = copy.deepcopy(cellule.lieux)
        repartir_sur_les_lieux(cellule)
        assert cellule.lieux == coherents
    verifier()
    original = engine._apply_mortality
    with monkeypatch.context() as garde:
        garde.setattr(engine, "_apply_mortality", lambda cellule, *facteurs: None)
        with pytest.raises(AssertionError): verifier()
    def dettes_inversees(cellule, *facteurs):
        cellule.lieux[0].dette_alimentaire_kg, cellule.lieux[1].dette_alimentaire_kg = (
            cellule.lieux[1].dette_alimentaire_kg, cellule.lieux[0].dette_alimentaire_kg)
        original(cellule, *facteurs)
    monkeypatch.setattr(engine, "_apply_mortality", dettes_inversees)
    with pytest.raises(AssertionError): verifier()


def test_demographie_locale_natalite(monkeypatch):
    from sim import engine
    from sim.model import Cell, creer_etat_de_lieu
    def verifier():
        cellule = Cell(0, 3000, 5005, habitants_par_metier={"mineurs": 5, "paysans": 5000},
                       natalite_remainder=0.9, food_deficit_kg=1000)
        cellule.lieux = [creer_etat_de_lieu(0, 5, {}, dette_alimentaire_kg=1000,
                                          duree_faim_ticks=2, natalite_remainder=0.7),
                         creer_etat_de_lieu(1, 5000, {}),
                         creer_etat_de_lieu(2, 0, {}, natalite_remainder=0.8)]
        appels, ajouter = [], engine._ajouter_par_les_foyers
        with monkeypatch.context() as garde:
            garde.setattr(engine, "_ajouter_par_les_foyers", lambda c, n: (appels.append(n), ajouter(c, n)))
            engine._apply_natalite(cellule, 10)
        assert [l.population for l in cellule.lieux] == [5, 5001, 0]
        assert [l.natalite_remainder for l in cellule.lieux] == [0.7, 0.0, 0.8]
        assert cellule.population == sum(l.population for l in cellule.lieux) == 5006
        assert cellule.habitants_par_metier == {"mineurs": 5, "paysans": 5001}
        assert appels == [1] and cellule.natalite_remainder == 0.9
    verifier()
    monkeypatch.setattr(engine, "_apply_natalite", lambda *args: None)
    with pytest.raises(AssertionError): verifier()


def test_demographie_locale_arrondis_apres_consommation_identique(monkeypatch):
    from sim import engine
    from sim.model import Cell, creer_etat_de_lieu

    def verifier():
        cellules = []
        carte = {0: {"relief": "plaine", "gisements": []}}
        ration = 5000 * _constantes.FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
        for populations in ((2500, 2500), (5000, 0)):
            cellule = Cell(0, 2000, 5000, stocks={"nourriture": 2 * ration},
                           food_deficit_kg=0.0)
            cellule.lieux = [creer_etat_de_lieu(rang, population, {"nourriture": ration})
                             for rang, population in enumerate(populations)]
            cellules.append(cellule)
        penuries = [engine._apply_consumption(c, carte) for c in cellules]
        assert penuries == [0.0, 0.0]
        assert cellules[0].stocks == cellules[1].stocks
        assert cellules[0].food_deficit_kg == cellules[1].food_deficit_kg == 0.0
        for cellule, penurie in zip(cellules, penuries):
            engine._apply_natalite(cellule, penurie)
            assert cellule.population == sum(l.population for l in cellule.lieux)
        # Une consommation identique ne promet pas les mêmes arrondis locaux.
        assert [c.population for c in cellules] == [5000, 5001]
        assert [l.natalite_remainder for l in cellules[0].lieux] == [0.5, 0.5]
        assert [l.natalite_remainder for l in cellules[1].lieux] == [0.0, 0.0]

    verifier()
    monkeypatch.setattr(engine, "_apply_natalite", lambda *args: None)
    with pytest.raises(AssertionError): verifier()


@pytest.mark.parametrize("dette,faim", [(0, 2), (7, 0)])
def test_demographie_locale_blocages(dette, faim):
    from sim import engine
    from sim.model import Cell, creer_etat_de_lieu
    cellule = Cell(0, 1000, 5000)
    cellule.lieux = [creer_etat_de_lieu(0, 5000, {}, dette_alimentaire_kg=dette,
                                      duree_faim_ticks=faim, natalite_remainder=0.75,
                                      mortality_remainder=0.5)]
    engine._apply_mortality(cellule)
    if dette:
        assert 0.5 < cellule.lieux[0].mortality_remainder < 1
    else:
        assert cellule.lieux[0].mortality_remainder == 0.5
    assert cellule.population == cellule.lieux[0].population == 5000
    engine._apply_natalite(cellule, 0)
    assert cellule.population == cellule.lieux[0].population == 5000
    assert cellule.lieux[0].natalite_remainder == 0.75
    cellule.lieux[0].dette_alimentaire_kg = 0
    cellule.lieux[0].duree_faim_ticks = 0
    engine._apply_natalite(cellule, 100)
    assert cellule.population == cellule.lieux[0].population == 5001
    assert cellule.lieux[0].natalite_remainder == 0.75


def test_demographie_locale_repli_et_lieu_vide():
    from sim import engine
    from sim.model import Cell, creer_etat_de_lieu
    cellule = Cell(0, 1000, 5, food_deficit_kg=1000)
    for _ in range(2): engine._apply_mortality(cellule)
    assert cellule.population == 4 and cellule.mortality_remainder == 0
    cellule.food_deficit_kg = 0
    cellule.population = 5000
    engine._apply_natalite(cellule, 0)
    assert cellule.population == 5001 and cellule.natalite_remainder == 0
    cellule.population = 0
    cellule.lieux = [creer_etat_de_lieu(0, 0, {}, dette_alimentaire_kg=1000,
                                      mortality_remainder=0.5, natalite_remainder=0.75)]
    avant = copy.deepcopy(cellule.lieux)
    engine._apply_mortality(cellule)
    engine._apply_natalite(cellule, 0)
    assert cellule.population == 0 and cellule.lieux == avant


def test_demographie_locale_documentation():
    from pathlib import Path
    def verifier(texte):
        for titre, report in (("Le déficit alimentaire et la mortalité", "mortality_remainder"),
                              ("La natalité", "natalite_remainder")):
            section = texte.split(f"## {titre}\n")[1].split("\n## ")[0]
            for mot in ("dette", "faim", "local", "prorata", report, "Sans lieux"):
                assert mot in section, f"{mot} absent de {titre}"
    texte = (Path(__file__).parents[1] / "MODELE.md").read_text(encoding="utf-8")
    verifier(texte)
    for report in ("mortality_remainder", "natalite_remainder"):
        with pytest.raises(AssertionError): verifier(texte.replace(report, "fraction"))


@pytest.mark.parametrize("porte", [None, 2, True, "2", 2.0, -1])
def test_plan_porte(porte):
    from sim.plan import PlanInvalide
    donnees = _donnees_plan()
    donnees["rues"][0]["porte_cell_id"] = porte
    if isinstance(porte, bool) or (porte is not None and (type(porte) is not int or porte < 0)):
        with pytest.raises(PlanInvalide, match="porte"):
            _construire_plan(donnees)
        return
    document = _construire_plan(donnees).to_dict()
    assert document["rues"] and _construire_plan(document).to_dict() == document
    if porte is None:
        assert document == _construire_plan(_donnees_plan()).to_dict()
        assert "porte_cell_id" not in document["rues"][0]
    else:
        assert document["rues"][0]["porte_cell_id"] == porte


def test_tick_sans_partage_general_apres_migration(monkeypatch):
    from sim import engine, lieux
    from sim.tests.test_commerce import _cellule_bourg, _conserver_bourg
    monde_initial = World({1: _cellule_bourg(1, [200, 100], [0., 0.], (0,)),
                          2: _cellule_bourg(2, [10, 10], [100., 0.])}, [{'a': 1, 'b': 2}])
    reprendre, migrer = lieux.repartir_sur_les_lieux, engine._apply_migration
    termine = False
    def reprise(cellule):
        assert not termine, 'partage général après migration'
        reprendre(cellule)
    def migration(monde, penuries):
        nonlocal termine
        migrer(monde, {1: 1.})
        termine = True
    monkeypatch.setattr(lieux, 'repartir_sur_les_lieux', reprise)
    monkeypatch.setattr(engine, '_apply_migration', migration)
    # Isoler les flux du tick ; leurs vrais maillons restent exécutés.
    monkeypatch.setattr(engine, '_apply_production', lambda *a: None)
    monkeypatch.setattr(engine, '_apply_consumption', lambda *a: 0.)
    monkeypatch.setattr(engine, '_apply_natalite', lambda *a: None)
    def jouer():
        nonlocal termine
        termine = False
        monde = copy.deepcopy(monde_initial)
        engine.tick(monde, random.Random(0), numero_tick=0)
        assert [l.population for l in monde.cells[2].lieux] == [12, 10]
        assert monde.cells[2].lieux[1].stocks['nourriture'] == 0
        _conserver_bourg(monde)
    jouer()
    avancer = engine._avancer_compteur_ticks
    def ancien_partage(monde):
        for cellule in monde.cells.values(): lieux.repartir_sur_les_lieux(cellule)
        avancer(monde)
    monkeypatch.setattr(engine, '_avancer_compteur_ticks', ancien_partage)
    with pytest.raises(AssertionError, match='partage général après migration'): jouer()


@pytest.mark.parametrize('saison_moyenne', [False, True])
def test_maillons_production_fabrication_extraction_tiennent_leurs_lieux(saison_moyenne, monkeypatch):
    from sim import engine, lieux
    from sim.model import copier_panier
    monde = World.charger(0)
    cellule = next(c for c in monde.cells.values() if len(c.lieux) > 1
                   and engine._extraction_du_tick_kg(c, monde.carte))
    engine._apply_extraction(cellule, monde.carte)
    assert _controle_conservation(monde) == len(monde.cells)
    minerai_avant = copier_panier(cellule)
    engine._apply_fabrication(cellule)
    assert _controle_conservation(monde) == len(monde.cells)
    assert copier_panier(cellule) != minerai_avant
    stocks_avant = [l.stocks['nourriture'] for l in cellule.lieux]
    total_avant = cellule.food_stock_kg
    recoltes = []
    produire = engine._produire_sur_les_lieux
    def observer(c, recolte):
        recoltes.append(recolte)
        produire(c, recolte)
    monkeypatch.setattr(engine, '_produire_sur_les_lieux', observer)
    if saison_moyenne:
        engine._apply_production_saison_moyenne(cellule, random.Random(0), monde.carte)
    else:
        engine._apply_production(cellule, random.Random(0), monde.carte, jour=1)
    assert len(recoltes) == 1 and recoltes[0] > 0
    recolte = recoltes[0]
    assert cellule.food_stock_kg == total_avant + recolte
    surfaces = lieux.surfaces_des_lieux(cellule.cell_id, cellule.area_km2)
    assert [l.stocks['nourriture'] for l in cellule.lieux] == [s + recolte * a / cellule.area_km2 for s, a in zip(stocks_avant, surfaces)]
    engine._apply_consumption(cellule, monde.carte)
    assert _controle_conservation(monde) == len(monde.cells)


def test_maitre_etat_manuel(monkeypatch):
    from sim import world, maitres
    from sim.model import Cell, EtatDeLieu, creer_etat_de_lieu, cellule_vers_dict
    def interdit(*args, **kwargs): raise AssertionError("chargement implicite")
    for module, nom in ((world, "charger_registre_maisons"), (maitres, "attribuer_maitres"),
                        (world, "amorcer_lieux"), (World, "lire_carte")):
        monkeypatch.setattr(module, nom, interdit)
    anciens = EtatDeLieu(0, 7, {"grain": 2.5}, 1.5, 3)
    nomme = creer_etat_de_lieu(1, 2, {}, maitre="maison-déclarée")
    absent = creer_etat_de_lieu(2, 0, {}, maitre=None)
    assert (anciens.maitre, nomme.maitre, absent.maitre) == (None, "maison-déclarée", None) and (anciens.dette_alimentaire_kg, anciens.duree_faim_ticks) == (1.5, 3)
    cellule = Cell(1, 1.0, 9, lieux=[anciens, nomme, absent])
    monde = World({1: cellule}, [])
    assert monde.maisons == () and World({2: Cell(2, 1.0, 0)}, []).cells[2].lieux == []
    attendu = [dataclasses.asdict(lieu) for lieu in cellule.lieux]
    def verifier(document):
        assert document and document == attendu
    verifier(cellule_vers_dict(cellule)["lieux"])
    verifier(monde.to_dict()["cells"]["1"]["lieux"])
    for geste in (lambda f: f.pop("maitre"), lambda f: f.update(parasite=0)):
        document = cellule_vers_dict(cellule)["lieux"]
        geste(document[0])
        with pytest.raises(AssertionError): verifier(document)
    @dataclasses.dataclass
    class EtatDeLieuParasite(EtatDeLieu):
        parasite: int = 0
    _controle_champs_etat_de_lieu(EtatDeLieu)
    with pytest.raises(AssertionError):
        _controle_champs_etat_de_lieu(EtatDeLieuParasite)


def test_photographie_et_empreinte_maitre_manuel_absent():
    from sim.model import Cell, EtatDeLieu
    from sim.snapshot_export import lieux_en_photographie
    cellule = Cell(1, 1.0, 0, lieux=[EtatDeLieu(0, 0, {})])
    photo = lieux_en_photographie(1, cellule)
    assert len(photo) == len(cellule.lieux) > 0
    assert photo[0]["maitre"] is None


# --- Les noms des lieux : une vraie ville, sinon une désignation -------------------------------------------

# Les directions d'une désignation, dans le sens des aiguilles d'une montre depuis le nord.
DIRECTIONS_8 = ("nord", "nord-est", "est", "sud-est", "sud", "sud-ouest", "ouest", "nord-ouest")
DIRECTIONS_16 = ("nord", "nord-nord-est", "nord-est", "est-nord-est", "est", "est-sud-est", "sud-est", "sud-sud-est",
                 "sud", "sud-sud-ouest", "sud-ouest", "ouest-sud-ouest", "ouest", "ouest-nord-ouest", "nord-ouest",
                 "nord-nord-ouest")


def _de_la_province(nom):
    """« de » devant le nom d'une terre, élidé ou contracté : d'Orléans, du Mans, des Baux, du Souf, de La Rochelle."""
    import unicodedata
    for article, contraction in (("le ", "du "), ("les ", "des ")):
        if nom[:len(article)].casefold() == article:
            return contraction + nom[len(article):]
    initiale = unicodedata.normalize("NFD", nom[0])[0].casefold()
    return ("d'" if initiale in "aeiouy" else "de ") + nom


def _vers(direction):
    """« au nord », « à l'est-sud-est » : la préposition d'une direction."""
    return ("à l'" if direction.startswith(("est", "ouest")) else "au ") + direction


def _ville_du_lieu(monde, places, x, y, cid=None):
    """(cell_id, rang) du lieu dont la place est la plus proche du point, dans `cid` ou, sans elle, dans la
    cellule de la carte qui contient le point (la plus petite sur un bord) ; `None` hors du monde."""
    from sim.villes import point_dans_geometrie
    if cid is None:
        cid = next((c for c in sorted(monde.carte) if point_dans_geometrie(x, y, monde.carte[c]["geometry"])), None)
    if cid is None or cid not in monde.cells:
        return None
    return cid, min(range(len(places[cid])), key=lambda r: ((places[cid][r].x_m - x) ** 2 + (places[cid][r].y_m - y) ** 2, r))


def villes_sourcees(monde, places):
    """Nom → lieux (cell_id, rang) où tombe une ville de ce nom : les sièges du registre, les villes de
    `villes-1400.json`, les villes de partage (dans leur cellule déclarée) et les villes témoins des frontières."""
    from sim.frontieres import charger_frontieres
    from sim.noms import attribution_livree
    from sim.places import sieges_des_maisons
    from sim.projection import projeter_epsg3035
    sieges, points = sieges_des_maisons(), []
    points += [(m.siege, *sieges[m.id], m.cell_id) for m in monde.maisons if m.sorte != "plausible" and m.id in sieges and m.cell_id is not None]
    attribution = attribution_livree(monde)
    points += [(v.nom, v.x_m, v.y_m, attribution.placees[v.nom]) for v in attribution.entrees if v.nom in attribution.placees]
    frontieres = charger_frontieres()
    points += [(v.nom, *projeter_epsg3035(v.lat, v.lon), cid) for cid, villes in frontieres.partages.items() for v in villes]
    points += [(t.nom, *projeter_epsg3035(t.lat, t.lon), None) for t in frontieres.temoins if t.hors_carte is None]
    villes = {}
    for nom, x, y, cid in points:
        lieu = _ville_du_lieu(monde, places, x, y, cid)
        if lieu is not None:
            villes.setdefault(nom, set()).add(lieu)
    return villes


def provinces_des_terres(monde, vue):
    """Le nom de la province de chaque terre, tel qu'une désignation l'écrit : la région d'une terre déclarée
    sans ville, avec son article en minuscule ; sinon le nom de son bourg."""
    from sim.noms import charger_chefs_lieux
    regions = charger_chefs_lieux().regions
    return {cid: regions.get(cid, bloc["lieux"][0]["nom"]) for cid, bloc in vue.items()}


def juger_les_noms_des_lieux(monde, vue, places, villes, provinces, interdits):
    """Les fautes des noms des lieux servis (`vue`, celle de `noms_depuis_monde`). Un nom n'est jamais un des
    `interdits` (les listes `lieux` de noms-1400.json) ni le nom d'un autre lieu, à la casse près. Hors du
    bourg, un lieu porte une ville sourcée qui tombe chez lui, ou une désignation « campagne de <province>,
    [à N km] au <direction> » vue depuis la place du bourg ; un lieu chez qui tombe une ville dont le nom
    n'est porté nulle part ne se désigne pas."""
    fautes = []
    if not vue or not any(bloc["lieux"] for bloc in vue.values()):
        return ["échantillon vide : aucun lieu nommé"]
    portes = {}
    for cid, bloc in sorted(vue.items()):
        if [l["rang"] for l in bloc["lieux"]] != [l.rang for l in monde.cells[cid].lieux]:
            fautes.append(f"cellule {cid} : rangs servis différents de ceux de la cellule")
        for lieu in bloc["lieux"]:
            portes.setdefault(lieu["nom"].casefold(), []).append((cid, lieu["rang"]))
    for nom, lieux in sorted(portes.items()):
        if len(lieux) > 1:
            fautes.append(f"« {nom} » nomme {len(lieux)} lieux : {lieux[:4]}")
    interdits = {n.casefold() for n in interdits}
    tombees = {}
    for nom, lieux in villes.items():
        for lieu in lieux:
            tombees.setdefault(lieu, set()).add(nom)
    for cid, bloc in sorted(vue.items()):
        bourg = places[cid][0]
        for lieu in bloc["lieux"]:
            nom, rang = lieu["nom"], lieu["rang"]
            if nom.casefold() in interdits:
                fautes.append(f"({cid}, {rang}) : « {nom} » est un nom des listes")
            if rang == 0:
                continue
            if nom in villes:
                if (cid, rang) not in villes[nom]:
                    fautes.append(f"({cid}, {rang}) : la ville « {nom} » ne tombe pas chez lui")
                continue
            libres = sorted(n for n in tombees.get((cid, rang), ()) if n.casefold() not in portes)
            if libres:
                fautes.append(f"({cid}, {rang}) : désigné « {nom} » alors que {libres} tombe chez lui")
            tete, virgule, position = nom.rpartition(", ")
            if not virgule or tete != "campagne " + _de_la_province(provinces[cid]):
                fautes.append(f"({cid}, {rang}) : « {nom} » n'est ni une ville sourcée ni une désignation de sa province")
                continue
            mots = position.split(" ")
            km = mots[1] if mots[0] == "à" and len(mots) > 3 and mots[2] == "km" else None
            direction = position.removeprefix(f"à {km} km " if km is not None else "")
            direction = direction.removeprefix("au ").removeprefix("à l'")
            dx, dy = places[cid][rang].x_m - bourg.x_m, places[cid][rang].y_m - bourg.y_m
            angle = math.degrees(math.atan2(dx, dy)) % 360
            attendues = {DIRECTIONS_8[round(angle / 45) % 8]} | ({DIRECTIONS_16[round(angle / 22.5) % 16]} if km is not None else set())
            if direction not in attendues or not position.endswith(_vers(direction)):
                fautes.append(f"({cid}, {rang}) : « {position} », mais le lieu est au {sorted(attendues)} du bourg")
            # La distance en kilomètres, ou au dixième de kilomètre (« 112,4 ») quand rien d'autre ne distingue deux lieux.
            distance = math.hypot(dx, dy) / 1000
            mesuree = None if km is None else (str(round(distance)) if "," not in km else f"{round(distance * 10) / 10:.1f}".replace(".", ","))
            if km is not None and km != mesuree:
                fautes.append(f"({cid}, {rang}) : « {position} », mais le lieu est à {mesuree} km du bourg")
    return fautes


@pytest.fixture(scope="module")
def noms_livres():
    from sim.noms import charger_noms, noms_depuis_monde
    from sim.places import places_du_monde
    monde = World.charger(0)
    places = places_du_monde(monde)
    vue = noms_depuis_monde(monde)
    listes = charger_noms()
    return SimpleNamespace(monde=monde, places=places, vue=vue, villes=villes_sourcees(monde, places),
                           provinces=provinces_des_terres(monde, vue),
                           interdits=[n for aire in listes["aires"].values() for n in aire["lieux"]])


def _juger(s, vue=None, villes=None):
    return juger_les_noms_des_lieux(s.monde, s.vue if vue is None else vue, s.places, s.villes if villes is None else villes,
                                    s.provinces, s.interdits)


def test_noms_des_lieux_une_vraie_ville_sinon_une_designation(noms_livres):
    s = noms_livres
    assert sum(len(b["lieux"]) for b in s.vue.values()) > len(s.vue) > 0
    fautes = _juger(s)
    assert not fautes, f"{len(fautes)} fautes :\n" + "\n".join(fautes[:40])
    # Le monde livré porte des villes hors du bourg, et des désignations à chaque degré de la règle.
    noms = [l["nom"] for b in s.vue.values() for l in b["lieux"] if l["rang"] > 0]
    assert any(n in s.villes for n in noms) and any(n.startswith("campagne ") for n in noms)
    assert any(" km " in n for n in noms) and any(n.endswith(tuple(d for d in DIRECTIONS_16 if d not in DIRECTIONS_8)) for n in noms)


def test_noms_des_lieux_le_juge_voit_chaque_faute(noms_livres):
    s = noms_livres
    assert _juger(s, vue={})
    cid = next(c for c in sorted(s.vue) if len(s.vue[c]["lieux"]) > 2 and s.vue[c]["lieux"][1]["nom"].startswith("campagne "))
    def pose(nom, rang=1, c=cid):
        faux = copy.deepcopy(s.vue)
        faux[c]["lieux"][rang]["nom"] = nom
        return faux
    autre = next(c for c in sorted(s.vue) if c != cid)
    designation = s.vue[cid]["lieux"][1]["nom"]
    tete, _, position = designation.rpartition(", ")
    direction = position.split(" ")[-1].removeprefix("l'")
    contraire = "-".join({"nord": "sud", "sud": "nord", "est": "ouest", "ouest": "est"}[m] for m in direction.split("-"))
    for faux in (pose(s.interdits[0]),                                    # un nom des listes
                 pose(s.vue[autre]["lieux"][0]["nom"]),                   # le nom d'une autre terre
                 pose(s.vue[cid]["lieux"][2]["nom"]),                     # le nom d'un autre lieu de la terre
                 pose("Nom inventé"),                                     # ni ville ni désignation
                 pose("campagne de Nulle-Part, " + position),             # la province d'une autre terre
                 pose(f"{tete}, à 999 km {_vers(direction)}"),            # une distance fausse
                 pose(f"{tete}, {_vers(contraire)}")):                    # la direction contraire
        assert _juger(s, vue=faux)
    # Une ville sourcée posée dans un lieu où elle ne tombe pas, ou une ville libre qui tombe chez un lieu désigné.
    ville, lieux = next((n, l) for n, l in sorted(s.villes.items()) if all(r > 0 for _, r in l)
                        and any(b["lieux"][r]["nom"] == n for c, b in s.vue.items() for cc, r in l if cc == c))
    assert _juger(s, vue=pose(ville))
    assert _juger(s, villes={**s.villes, "Ville d'épreuve": {(cid, 1)}})


def test_noms_aires_de_cellule():
    from sim.noms import charger_noms, aire_de_cellule
    from sim.puissances import charger_table
    table, listes = charger_table(), charger_noms()
    for puissance, lat, lon, aire in ((3, 44, 2, 'oc'), (3, 48, 2, 'oïl'), (25, 38, 23, 'grecque'), (None, 61, 22, 'finnoise')):
        assert aire_de_cellule(0, {'centroid': {'lat': lat, 'lon': lon}}, puissance, table, listes) == aire
    with pytest.raises(ValueError, match='cellule 0'):
        aire_de_cellule(0, {'centroid': {'lat': 38, 'lon': 23}}, 25, dataclasses.replace(table, puissances=tuple(
            dataclasses.replace(p, religion='musulmane') if p.id == 25 else p for p in table.puissances)), listes)


@pytest.mark.parametrize('champ,defaut', [(c, d) for c in ('lieux', 'maisons', 'prenoms') for d in ('vide', 'texte', 'doublon')] + [('aire', 'absente'), ('regles', 'absentes')])
def test_noms_refus(tmp_path, champ, defaut):
    from sim.noms import charger_noms, noms_depuis_monde
    monde = World.charger(0); document = charger_noms(); aire = document['regles'][0]['aire']
    if champ == 'aire': del document['aires'][aire]
    elif champ == 'regles': document['regles'] = []
    elif defaut == 'vide': document['aires'][aire][champ] = []
    else: document['aires'][aire][champ].append(' ' if defaut == 'texte' else document['aires'][aire][champ][0])
    chemin = tmp_path / 'noms.json'; chemin.write_text(json.dumps(document))
    with pytest.raises(ValueError, match='cellule' if champ == 'regles' else aire + '.*' + (champ if champ != 'aire' else 'listes')): noms_depuis_monde(monde, noms=charger_noms(chemin))



def test_photographie_et_empreinte_noms_flux_absents():
    from sim.model import Cell, EtatDeLieu
    from sim.snapshot_export import lieux_en_photographie
    photo = lieux_en_photographie(1, Cell(1, 1., 0, lieux=[EtatDeLieu(0, 0, {})]))
    def verifier(p):
        assert p and all(l['nom'] is None and l['flux_30j'] is None for l in p)
    verifier(photo)
    faux = copy.deepcopy(photo); faux[0]['nom'] = 'Deviné'
    with pytest.raises(AssertionError): verifier(faux)


def test_photographie_lit_les_surfaces_sans_recreer_les_lieux(monkeypatch):
    from sim import lieux
    from sim.model import Cell, EtatDeLieu
    from sim.snapshot_export import lieux_en_photographie

    surface = _constantes.SURFACE_KM2_PAR_LIEU * 2 + 0.5
    vue = lieux_de_cellule(1, surface)
    cellule = Cell(1, surface, 0, lieux=[EtatDeLieu(l.rang, 0, {}) for l in vue])
    assert len(vue) > 1

    def construction_interdite(*args):
        pytest.fail('la publication reconstruit des objets de lieux pour lire leurs surfaces')

    monkeypatch.setattr(lieux, 'Lieu', construction_interdite)
    photo = lieux_en_photographie(1, cellule)
    assert [l['surface_km2'] for l in photo] == [l.surface_km2 for l in vue]
    monkeypatch.setattr(_constantes, 'SURFACE_KM2_PAR_LIEU', surface)
    cellule.lieux = cellule.lieux[:1]
    assert [l['surface_km2'] for l in lieux_en_photographie(1, cellule)] == [surface]


def test_raccourci_reprise(monkeypatch):
    import random
    from sim import engine, lieux
    from sim.model import ecrire_stock_marchandise, copier_panier
    monde, rng = World.charger(0), random.Random(0)
    for numero in range(5):
        engine.tick(monde, rng, numero_tick=numero)

    def controler(cellule):
        rapide, ancien = copy.deepcopy(cellule), copy.deepcopy(cellule)
        lieux.repartir_sur_les_lieux(rapide)
        lieux.repartir_sur_les_lieux(ancien, raccourci=False)
        assert dataclasses.asdict(rapide) == dataclasses.asdict(ancien)
        for a, b in zip(rapide.lieux, ancien.lieux):
            assert list(copier_panier(a).items()) == list(copier_panier(b).items())
        return ancien

    for cellule in monde.cells.values():
        cellule.lieux.reverse()
        controler(cellule)
        cellule.population += 1
        controler(cellule)
    cellule = next(c for c in monde.cells.values() if len(c.lieux) > 1)
    ecrire_stock_marchandise(cellule.lieux[0], 'preuve_du_raccourci', 0.0)
    attendu = controler(cellule)
    # Une somme alignée ne suffit pas : l'ancienne reprise enlève cette clé.
    monkeypatch.setattr(lieux, 'lieux_deja_accordes', lambda *a: True)
    fautif = copy.deepcopy(cellule)
    lieux.repartir_sur_les_lieux(fautif)
    with pytest.raises(AssertionError):
        assert dataclasses.asdict(fautif) == dataclasses.asdict(attendu)
    assert len(monde.cells) > 0
    print(f'cellules comparées={len(monde.cells)}, reprises={2 * len(monde.cells) + 1}, clé parasite détectée')


def test_raccourci_partager():
    import random
    from sim import engine, lieux
    from sim.model import contenus_des_paniers
    monde, rng = World.charger(0), random.Random(0)
    for numero in range(5):
        engine.tick(monde, rng, numero_tick=numero)
    cas = 0
    for cellule in monde.cells.values():
        etats = sorted(cellule.lieux, key=lambda lieu: lieu.rang)
        surfaces = lieux.surfaces_des_lieux(cellule.cell_id, cellule.area_km2)
        poids = ([l.population for l in etats], contenus_des_paniers(etats, 'nourriture'),
                 [l.dette_alimentaire_kg for l in etats])
        for total, valeurs in zip((cellule.population, max(0., cellule.food_stock_kg),
                                   max(0., cellule.food_deficit_kg)), poids):
            valeurs = valeurs if any(valeurs) else surfaces
            assert lieux.partager(total, valeurs) == lieux.partager(total, valeurs, raccourci=False)
            cas += 1
    # Des poids seulement voisins ne doivent jamais être regroupés.
    a, b = [1., math.nextafter(1., math.inf)], [1., 1.]
    with pytest.raises(AssertionError):
        assert lieux.partager(1, a) == lieux.partager(1, b)
    assert cas == 3 * len(monde.cells) > 0
    print(f'partages exacts comparés={cas}, regroupement arrondi détecté')


def test_partager_flottants_rend_les_parts_du_chemin_general(monkeypatch):
    import random
    from sim import lieux
    r = random.Random(0)

    def poids_au_hasard():
        n, famille = r.randint(1, 30), r.randrange(5)
        if famille == 0:
            return [r.uniform(0, 10.0 ** r.randint(0, 8)) for _ in range(n)]
        if famille == 1:
            valeur = r.uniform(0, 1000)
            return [valeur if r.random() < 0.8 else 0.0 for _ in range(n)]
        if famille == 2:
            return [float(r.randint(0, 10 ** r.randint(1, 9))) for _ in range(n)]
        if famille == 3:
            reserve = [r.uniform(0, 100) for _ in range(r.randint(1, 4))]
            return [r.choice(reserve) for _ in range(n)]
        return [r.uniform(0, 1) * 10.0 ** r.randint(-320, 300) for _ in range(n)]

    def total_au_hasard(poids):
        famille = r.randrange(5)
        if famille == 0:
            return math.fsum(poids)
        if famille == 1:
            return float(r.randint(0, 10 ** 9))
        if famille == 2:
            return r.uniform(0, 1) * 10.0 ** r.randint(-320, 300)
        if famille == 3:
            return r.uniform(1, 1e9)
        return len(poids) + 0.5

    cas = []
    for _ in range(3000):
        poids = poids_au_hasard()
        cas.append((total_au_hasard(poids), poids))

    def issue(total, poids):
        try:
            return repr(lieux.partager(total, poids))
        except lieux.LieuxInvalides as erreur:
            return ('refus', str(erreur))

    def issues():
        return [issue(total, poids) for total, poids in cas]

    flottantes = issues()
    with monkeypatch.context() as m:
        m.setattr(lieux, '_poids_exacts_flottants', lambda poids: None)
        generales = issues()
    assert flottantes == generales and flottantes

    # Un échantillon qui ne prend jamais l'un des deux chemins ne prouverait rien.
    candidats = [poids for _, poids in cas if poids and all(type(p) is float for p in poids)]
    servis = sum(lieux._poids_exacts_flottants(poids) is not None for poids in candidats)
    replis = len(candidats) - servis
    assert servis >= len(cas) / 2 and replis >= 1

    # Contre-épreuve : des poids tronqués, sans échelle, ne rendent plus les parts du chemin général.
    with monkeypatch.context() as m:
        m.setattr(lieux, '_poids_exacts_flottants', lambda poids: [int(p) for p in poids])
        fausses = issues()
    with pytest.raises(AssertionError):
        assert fausses == generales
    print(f'cas={len(cas)}, servis par le chemin flottant={servis}, replis={replis}')


def test_raccourci_lecture_stock():
    import random
    from sim import engine, model
    monde, rng = World.charger(0), random.Random(0)
    for numero in range(5):
        engine.tick(monde, rng, numero_tick=numero)
    cas = 0
    for cellule in monde.cells.values():
        for entite in (cellule, *cellule.lieux):
            for nom in (*model.copier_panier(entite), '_absente'):
                ancien = model._lire_stock_par_presence(entite, nom)
                rapide = model.lire_stock_marchandise(entite, nom)
                assert rapide == ancien and type(rapide) is type(ancien)
                cas += 1
    with pytest.raises(AssertionError):
        assert model.lire_stock_marchandise(cellule, '_absente') == 0.0
    assert cas > 0
    print(f'lectures comparées={cas}, absence confondue avec zéro détectée')


# `/lieux` : chaque lieu du monde servi en une lecture, ses habitants, sa surface et sa réserve en jours.
JOURS_SERVIS = 3
FIGE_DES_LIEUX = (Path(__file__).resolve().parents[3]
                  / f"3d/unity/Assets/ForgeLocal3D/Pont/Tests/lieux-graine0-tick{JOURS_SERVIS}.json")


@pytest.fixture(scope="module")
def lieux_servis():
    """Le service de la graine 0 après trois jours : le monde vivant, `/monde` et `/lieux` du même tick."""
    from sim import engine, service
    with service.ServeurMonde(("127.0.0.1", 0), 0, 0) as monte:
        for numero in range(JOURS_SERVIS):
            engine.tick(monte.world, monte.rng, numero_tick=numero)
        etat = monte._construire_etat(0, -1)
        yield monte.world, json.loads(etat.monde), json.loads(etat.lieux_du_monde.octets())


def _controler_les_habitants_servis(monde_servi, lieux):
    """Chaque cellule de `/monde` a ses lieux dans `/lieux`, et leurs habitants font les siens."""
    assert lieux["cells"], "aucune cellule servie : l'échantillon ne prouverait rien"
    population = {c["cell_id"]: c["population"] for c in monde_servi["cells"]}
    assert [c["cell_id"] for c in lieux["cells"]] == sorted(population) and lieux["cell_count"] == len(population)
    for cellule in lieux["cells"]:
        assert cellule["lieux"], f"cell_id={cellule['cell_id']} : aucun lieu servi"
        assert [l["rang"] for l in cellule["lieux"]] == list(range(len(cellule["lieux"])))
        assert sum(l["population"] for l in cellule["lieux"]) == population[cellule["cell_id"]], cellule["cell_id"]


def test_lieux_servis_leurs_habitants_font_ceux_de_chaque_cellule(lieux_servis):
    _monde, monde_servi, lieux = lieux_servis
    assert (lieux["tick"], lieux["date"]) == (monde_servi["tick"], monde_servi["date"])
    _controler_les_habitants_servis(monde_servi, lieux)
    # Contre-épreuves : un échantillon vide, un habitant passé d'une cellule à l'autre.
    with pytest.raises(AssertionError, match="aucune cellule servie"):
        _controler_les_habitants_servis(monde_servi, dict(lieux, cells=[]))
    deplace = copy.deepcopy(lieux)
    deplace["cells"][0]["lieux"][0]["population"] += 1
    deplace["cells"][1]["lieux"][0]["population"] -= 1
    with pytest.raises(AssertionError):
        _controler_les_habitants_servis(monde_servi, deplace)


def test_lieux_servis_un_monde_aux_lieux_vides_n_est_pas_servi():
    from sim import service
    from sim.snapshot_export import SnapshotExportError
    with service.ServeurMonde(("127.0.0.1", 0), 0, 0) as monte:
        cid = min(monte.world.cells)
        monte.world.cells[cid].lieux.clear()
        with pytest.raises(SnapshotExportError, match=f"cell_id={cid} : rang 0 absent"):
            monte._construire_etat(0, -1)


def test_lieux_servis_leurs_surfaces_sont_celles_du_decoupage(lieux_servis):
    monde, _monde_servi, lieux = lieux_servis
    for cellule in lieux["cells"]:
        attendues = [l.surface_km2 for l in lieux_de_cellule(cellule["cell_id"], monde.cells[cellule["cell_id"]].area_km2)]
        assert [l["surface_km2"] for l in cellule["lieux"]] == attendues, cellule["cell_id"]


def test_lieux_servis_la_reserve_en_jours_compte_le_stock_et_la_dette():
    from sim.departs import reserve_en_jours
    assert reserve_en_jours(10, 50.0, 0.0, 0.5) == 10.0
    assert reserve_en_jours(10, -1.0, 0.0, 0.5) == 0.0, "un stock absent (-1) compte pour rien"
    assert reserve_en_jours(10, 50.0, 70.0, 0.5) == -4.0, "une dette plus lourde que le stock rend une réserve négative"


def test_lieux_servis_leurs_reserves_sont_celles_du_mieux_vivre(lieux_servis):
    from sim import departs
    from sim.model import lire_stock_marchandise
    monde, _monde_servi, lieux = lieux_servis
    nourriture, ration = _constantes.MARCHANDISE_NOURRITURE, departs.ration_journaliere()
    habites = vides = 0
    for cellule in lieux["cells"]:
        vivants = sorted(monde.cells[cellule["cell_id"]].lieux, key=lambda l: l.rang)
        for servi, lieu in zip(cellule["lieux"], vivants, strict=True):
            if lieu.population <= 0:
                assert servi["reserve_jours"] is None, (cellule["cell_id"], lieu.rang)
                vides += 1
                continue
            attendue = departs.reserve_en_jours(lieu.population, lire_stock_marchandise(lieu, nourriture),
                                                lieu.dette_alimentaire_kg, ration)
            assert servi["reserve_jours"] == attendue, (cellule["cell_id"], lieu.rang)
            habites += 1
    reserves = {l["reserve_jours"] for c in lieux["cells"] for l in c["lieux"] if l["reserve_jours"] is not None}
    assert habites > 0 and len(reserves) > 1, "des réserves toutes égales ne prouveraient rien"
    # Le mieux-vivre photographie les mêmes réserves : une entrée par lieu habité, aucune pour un lieu vide.
    def controler(photo):
        servis = {(c["cell_id"], l["rang"]) for c in lieux["cells"] for l in c["lieux"] if l["reserve_jours"] is not None}
        for cellule in lieux["cells"]:
            for servi in cellule["lieux"]:
                if servi["reserve_jours"] is None:
                    continue
                entree = {e[0]: e for e in photo.get(cellule["cell_id"], [])}.get(servi["rang"])
                assert entree is not None, (cellule["cell_id"], servi["rang"])
                assert entree[3] == servi["reserve_jours"], (cellule["cell_id"], servi["rang"])
        assert sum(len(entrees) for entrees in photo.values()) == habites
        assert all(e[2] > 0 for entrees in photo.values() for e in entrees)
        assert {(cid, e[0]) for cid, entrees in photo.items() for e in entrees} == servis
    controler(departs._photographier(copy.deepcopy(monde), ration)[0])
    # Contre-épreuve : une dette alourdie sur un lieu habité change sa réserve, et le contrôle le voit.
    alourdi = copy.deepcopy(monde)
    next(l for c in alourdi.cells.values() for l in c.lieux if l.population > 0).dette_alimentaire_kg += 1000.0
    with pytest.raises(AssertionError):
        controler(departs._photographier(alourdi, ration)[0])
    print(f"lieux habités={habites}, vides={vides}, réserves distinctes={len(reserves)}")


def test_lieux_servis_fige_du_pont():
    """Les octets figés du pont sont ceux du service, graine 0, après trois jours ; le jour suivant les change."""
    from http import HTTPStatus
    from sim.tests.test_monde import lancer_service, requete_service
    fige = FIGE_DES_LIEUX.read_bytes()
    document = json.loads(fige)
    assert document["cells"] and document["tick"] == JOURS_SERVIS
    with lancer_service(0) as port:
        assert requete_service(port, f"/tick?n={JOURS_SERVIS}", "POST")[0] == HTTPStatus.OK
        statut, _, octets = requete_service(port, "/lieux")
        assert statut == HTTPStatus.OK and octets == fige == requete_service(port, "/lieux")[2]
        requete_service(port, "/tick?n=1", "POST")
        suivants = requete_service(port, "/lieux")[1]["cells"]
        assert any(a["lieux"] != b["lieux"] for a, b in zip(suivants, document["cells"]))
