"""Preuves de la nourriture que le bourg peut atteindre dans sa cellule."""

import copy
import math
import random

import pytest

from sim import constants as constantes, engine
from sim.lieux import lieux_de_cellule
from sim.model import Cell, ecrire_stock_marchandise, lire_stock_marchandise
from sim.world import World


def _stock(cellule):
    return lire_stock_marchandise(cellule, constantes.MARCHANDISE_NOURRITURE)


def _part(cellule, carte):
    return constantes.part_miniere_de(
        carte[cellule.cell_id].get("gisements"), constantes.facteurs_richesse_extraction()
    )


def _epreuve(relief="plaine", surface=None):
    cellule = Cell(0, surface if surface is not None else
                   20 * constantes.SURFACE_KM2_PAR_LIEU, 10_000)
    carte = {cellule.cell_id: {"relief": relief, "gisements": [
        {"ressource": "fer", "richesse": "majeure"}]}}
    besoin = cellule.population * constantes.FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    ecrire_stock_marchandise(cellule, constantes.MARCHANDISE_NOURRITURE, 1.5 * besoin)
    cellule.food_deficit_kg = 0.0
    lieux = lieux_de_cellule(cellule.cell_id, cellule.area_km2)
    besoin_bourg = cellule.population * _part(cellule, carte) * (
        constantes.FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK)
    local = _stock(cellule) * lieux[0].surface_km2 / cellule.area_km2
    return cellule, carte, besoin, besoin_bourg, local, len(lieux) - 1


def _egal_kg(observe, attendu):
    assert math.isclose(observe, attendu, rel_tol=1e-12)


def test_sans_chemin(monkeypatch):
    cellule, carte, besoin, besoin_bourg, local, chemins = _epreuve()
    gratuite, desservie = copy.deepcopy(cellule), copy.deepcopy(cellule)
    assert engine._apply_consumption(gratuite) == 0.0
    assert engine._apply_consumption(desservie, carte) == 0.0
    monkeypatch.setattr(constantes, "CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK", 0.0)
    avant = _stock(cellule)
    penurie = engine._apply_consumption(cellule, carte)
    _egal_kg(penurie, besoin_bourg - local)
    _egal_kg(_stock(cellule), avant - local - (besoin - besoin_bourg))
    _egal_kg(cellule.food_deficit_kg, penurie)
    engine._update_hunger(cellule, penurie)
    assert penurie > 0 and _stock(cellule) > 0 and cellule.hunger_ticks == 1
    print(f"chemins={chemins}, penurie={penurie}, reste_champs={_stock(cellule)}, "
          f"hunger_ticks={cellule.hunger_ticks}, contre_epreuves=2")
    assert chemins > 0


def test_capacite_et_relief(monkeypatch):
    cellule, carte, _, besoin_bourg, local, chemins = _epreuve()
    manque = besoin_bourg - local
    capacite = 2 * manque / chemins
    monkeypatch.setattr(constantes, "CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK", capacite)
    plaine = engine._apply_consumption(cellule, carte)
    montagne, carte_montagne, *_ = _epreuve("montagne")
    penurie_montagne = engine._apply_consumption(montagne, carte_montagne)
    _egal_kg(penurie_montagne, manque - chemins * capacite *
             constantes.FACTEUR_TRANSPORT_MONTAGNE)
    assert plaine == 0.0 and penurie_montagne > plaine
    monkeypatch.setattr(constantes, "CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK", capacite / 4)
    reduite, carte, *_ = _epreuve()
    penurie_reduite = engine._apply_consumption(reduite, carte)
    _egal_kg(penurie_reduite, manque - chemins * capacite / 4 *
             constantes.FACTEUR_TRANSPORT_PLAINE)
    assert 0 < penurie_reduite < manque
    monkeypatch.setattr(constantes, "CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK", 0.0)
    seule, carte, *_, chemins_seuls = _epreuve(surface=constantes.SURFACE_KM2_PAR_LIEU / 2)
    assert chemins_seuls == 0 and engine._apply_consumption(seule, carte) == 0.0
    refus = 0
    for invalide in (float("nan"), -1.0):
        monkeypatch.setattr(constantes, "CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK", invalide)
        with pytest.raises(ValueError, match="CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK"):
            constantes.capacite_chemins_interieurs_kg(chemins, 1.0)
        refus += 1
    print(f"chemins={chemins}, plaine={plaine}, montagne={penurie_montagne}, "
          f"capacite_reduite={penurie_reduite}, cellules_seules=1, refus={refus}")
    assert chemins > 0 and refus > 0


def test_conservation(monkeypatch):
    cellule, carte, besoin, besoin_bourg, local, _ = _epreuve()
    cellule.food_deficit_kg = 1_000.0
    avant, dette_avant = _stock(cellule), cellule.food_deficit_kg
    monkeypatch.setattr(constantes, "CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK", 0.0)
    penurie = engine._apply_consumption(cellule, carte)

    def controle(apres, dette_apres):
        _egal_kg(avant - apres, local + besoin - besoin_bourg)
        assert 0 <= avant - apres <= besoin and apres >= 0
        _egal_kg(dette_apres - dette_avant, penurie)

    controle(_stock(cellule), cellule.food_deficit_kg)
    with pytest.raises(AssertionError):
        controle(avant, cellule.food_deficit_kg)
    assert penurie > 0 and _stock(cellule) > 0
    print(f"cellules_controlees=1, mange={avant - _stock(cellule)}, "
          f"dette_ajoutee={cellule.food_deficit_kg - dette_avant}, contre_epreuves=1")


def test_identique_quand_chemins_suffisent(monkeypatch):
    monkeypatch.setattr(constantes, "CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK", float("inf"))
    monde, rng = World.charger(0), random.Random(0)
    cellules_comparees = avec_bourg = 0
    for etape in range(2):
        if etape:
            for numero in range(30):
                engine.tick(monde, rng, numero)
        for cellule in monde.cells.values():
            copie, gratuite = copy.deepcopy(cellule), copy.deepcopy(cellule)
            assert engine._apply_consumption(copie, monde.carte) == (
                engine._apply_consumption(gratuite))
            assert _stock(copie) == _stock(gratuite)
            assert copie.food_deficit_kg == gratuite.food_deficit_kg
            cellules_comparees += 1
            avec_bourg += _part(cellule, monde.carte) > 0
    assert cellules_comparees == 2 * len(monde.cells) > 0 and avec_bourg > 0
    monkeypatch.setattr(constantes, "CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK", 0.0)
    cellule, carte, *_ = _epreuve()
    gratuite = copy.deepcopy(cellule)
    assert engine._apply_consumption(cellule, carte) > engine._apply_consumption(gratuite)
    print(f"cellules_comparees={cellules_comparees}, avec_bourg={avec_bourg}, "
          "contre_epreuves=1")


def test_monde_ressent_la_distribution(monkeypatch):
    capacite = constantes.CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK
    source = World.charger(0)
    cellules_bourg = [cellule.cell_id for cellule in source.cells.values()
                      if _part(cellule, source.carte) > 0]
    assert cellules_bourg

    def parties():
        populations = []
        for reglage in (0.0, capacite):
            monkeypatch.setattr(constantes, "CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK", reglage)
            monde, rng = World.charger(0), random.Random(0)
            for numero in range(120):
                engine.tick(monde, rng, numero)
            populations.append(sum(monde.cells[cell_id].population for cell_id in cellules_bourg))
        return populations

    def controle(populations):
        assert populations[0] < populations[1]

    populations = parties()
    controle(populations)
    original = engine._apply_consumption
    monkeypatch.setattr(engine, "_apply_consumption", lambda cellule, carte=None: original(cellule))
    gratuites = parties()
    assert gratuites[0] == gratuites[1]
    with pytest.raises(AssertionError):
        controle(gratuites)
    print(f"cellules_avec_bourg={len(cellules_bourg)}, sans_chemin={populations[0]}, "
          f"avec_chemins={populations[1]}, gratuites={gratuites}, contre_epreuves=1")


def test_identique_hors_manque_bourg_avec_surplus(monkeypatch):
    """Sans surplus aux champs ou avec un bourg servi, garder le calcul ancien."""
    cellule, carte, besoin, besoin_bourg, local, _ = _epreuve()
    stock_servant_bourg = besoin_bourg * _stock(cellule) / local
    monkeypatch.setattr(constantes, "CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK", 0.0)
    cellules_comparees = sentinelles = 0
    for stock in (None, 0.0, (besoin - besoin_bourg) / 2, stock_servant_bourg * 1.5):
        copie = copy.deepcopy(cellule)
        if stock is None:
            copie.stocks.clear()
            assert _stock(copie) == -1
            sentinelles += 1
        else:
            ecrire_stock_marchandise(copie, constantes.MARCHANDISE_NOURRITURE, stock)
        copie.food_deficit_kg = 1_000.0
        gratuite = copy.deepcopy(copie)
        assert engine._apply_consumption(copie, carte) == engine._apply_consumption(gratuite)
        assert _stock(copie) == _stock(gratuite)
        assert copie.food_deficit_kg == gratuite.food_deficit_kg
        cellules_comparees += 1
    assert cellules_comparees > 0
    print(f"cellules_comparees={cellules_comparees}, sentinelles={sentinelles}, "
          f"dettes_anciennes={cellules_comparees}")


def test_capacite_calculs_inutiles_evites(monkeypatch):
    """Sans mine, pas de lieux ; avec un seul lieu, pas de transport."""
    def interdit(*args, **kwargs):
        pytest.fail("calcul intérieur inutile")

    cellules_controlees = 0
    cellule, carte, *_ = _epreuve()
    gratuite = copy.deepcopy(cellule)
    with monkeypatch.context() as garde:
        garde.setattr(engine, "lieux_de_cellule", interdit)
        garde.setattr(engine, "_facteur_transport_pour_cellule", interdit)
        garde.setattr(constantes, "capacite_chemins_interieurs_kg", interdit)
        assert engine._apply_consumption(cellule) == engine._apply_consumption(gratuite)
        cellules_controlees += 1
        cellule, carte, *_ = _epreuve()
        carte[cellule.cell_id]["gisements"] = []
        assert _part(cellule, carte) == 0
        gratuite = copy.deepcopy(cellule)
        assert engine._apply_consumption(cellule, carte) == engine._apply_consumption(gratuite)
        assert _stock(cellule) == _stock(gratuite)
        assert cellule.food_deficit_kg == gratuite.food_deficit_kg
        cellules_controlees += 1
    monkeypatch.setattr(engine, "_facteur_transport_pour_cellule", interdit)
    monkeypatch.setattr(constantes, "capacite_chemins_interieurs_kg", interdit)
    seule, carte, *_, chemins = _epreuve(surface=constantes.SURFACE_KM2_PAR_LIEU / 2)
    assert chemins == 0 and _part(seule, carte) > 0
    assert engine._apply_consumption(seule, carte) == 0.0
    cellules_controlees += 1
    assert cellules_controlees > 0
    print(f"cellules_controlees={cellules_controlees}, chemins_cellule_seule={chemins}")


def test_identique_quand_reste_champs_est_nul(monkeypatch):
    """Le manque du bourg ne suffit pas : les champs doivent avoir un surplus."""
    cellule, carte, besoin, besoin_bourg, _, chemins = _epreuve()
    mange_bourg = besoin_bourg / 2
    stock = besoin - besoin_bourg + mange_bourg
    ecrire_stock_marchandise(cellule, constantes.MARCHANDISE_NOURRITURE, stock)
    lieux = lieux_de_cellule(cellule.cell_id, cellule.area_km2)
    local = stock * lieux[0].surface_km2 / cellule.area_km2
    capacite = (mange_bourg - local) / chemins / constantes.FACTEUR_TRANSPORT_PLAINE
    monkeypatch.setattr(constantes, "CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK", capacite)
    accessible = engine._nourriture_accessible_au_rang0_kg(cellule, carte, stock)
    assert besoin_bourg - accessible > 0
    assert stock - accessible - (besoin - besoin_bourg) == 0
    cellule.food_deficit_kg = 1_000.0
    gratuite = copy.deepcopy(cellule)
    assert engine._apply_consumption(cellule, carte) == engine._apply_consumption(gratuite)
    assert _stock(cellule) == _stock(gratuite) == 0
    assert cellule.food_deficit_kg == gratuite.food_deficit_kg
    assert chemins > 0
    print(f"cellules_comparees=1, chemins={chemins}, reste_champs=0")


def test_sans_chemin_part_locale_par_surface(monkeypatch):
    """Le rang 0 reçoit sa surface réelle, y compris le reste du découpage."""
    cellule, carte, besoin, besoin_bourg, local, chemins = _epreuve(
        surface=20 * constantes.SURFACE_KM2_PAR_LIEU + 0.5)
    lieux = lieux_de_cellule(cellule.cell_id, cellule.area_km2)
    assert chemins > 0 and lieux[0].surface_km2 > lieux[1].surface_km2
    avant = _stock(cellule)
    dette_avant = cellule.food_deficit_kg
    monkeypatch.setattr(constantes, "CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK", 0.0)

    def controle(copie):
        penurie = engine._apply_consumption(copie, carte)
        _egal_kg(penurie, besoin_bourg - local)
        _egal_kg(_stock(copie), avant - local - (besoin - besoin_bourg))
        _egal_kg(copie.food_deficit_kg - dette_avant, penurie)
        assert penurie > 0 and _stock(copie) > 0

    controle(copy.deepcopy(cellule))
    monkeypatch.setattr(engine, "_nourriture_accessible_au_rang0_kg",
                        lambda cellule, carte, stock: stock / len(lieux))
    with pytest.raises(AssertionError):
        controle(copy.deepcopy(cellule))
    print(f"cellules_controlees=1, lieux={len(lieux)}, local={local}, "
          "contre_epreuves=1")


def _cellule_par_lieu(populations, paniers):
    from sim.model import creer_etat_de_lieu
    cellule = Cell(0, 3 * constantes.SURFACE_KM2_PAR_LIEU + 0.5, sum(populations))
    cellule.lieux = [creer_etat_de_lieu(rang, population, {"nourriture": stock})
                     for rang, (population, stock) in enumerate(zip(populations, paniers))]
    ecrire_stock_marchandise(cellule, "nourriture", sum(paniers))
    cellule.food_deficit_kg = 9.0
    return cellule, {0: {"relief": "plaine", "gisements": []}}


def _controle_par_lieu(cellule, attendus, avant):
    from fractions import Fraction
    observes = [_stock(lieu) for lieu in cellule.lieux]
    for observe, attendu in zip(observes, attendus):
        _egal_kg(observe, attendu)
    assert sum(observes) == _stock(cellule)
    assert sum(map(Fraction, observes)) == Fraction(_stock(cellule))
    assert min(observes) >= 0
    besoin = cellule.population * constantes.FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
    assert 0 <= avant - _stock(cellule) <= besoin


@pytest.mark.parametrize("capacite,relief,populations,paniers,restes,manque", [
    (0, "plaine", [20, 1, 1], [0, 6, 200], [0, 4, 198], 40),
    (10, "plaine", [20, 1, 1], [0, 6, 200], [0, 0, 188], 26),
    (10, "montagne", [20, 1, 1], [0, 6, 200], [0, 1, 195], 34),
    (10, "plaine", [1, 20, 1], [200, 0, 100], [188, 0, 98], 30),
])
def test_consommation_par_lieu(monkeypatch, capacite, relief, populations, paniers, restes, manque):
    cellule, carte = _cellule_par_lieu(populations, paniers)
    carte[0]["relief"] = relief
    gratuite = copy.deepcopy(cellule)
    monkeypatch.setattr(constantes, "CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK", capacite)
    _egal_kg(engine._apply_consumption(cellule, carte), manque)
    _egal_kg(cellule.food_deficit_kg, 9 + manque)
    engine._update_hunger(cellule, manque)
    assert cellule.hunger_ticks == 1
    _controle_par_lieu(cellule, restes, sum(paniers))
    engine._apply_consumption(gratuite)
    with pytest.raises(AssertionError):
        _controle_par_lieu(gratuite, restes, sum(paniers))


@pytest.mark.parametrize("facteur", [2, 0.5])
def test_commerce_a_proportion(monkeypatch, facteur):
    import sim.lieux as lieux
    paniers, populations = [100, 500, 1000], [1, 2, 3]
    cellule, carte = _cellule_par_lieu(populations, paniers)
    cellule.food_deficit_kg = 0
    ecrire_stock_marchandise(cellule, "nourriture", facteur * sum(paniers))
    monkeypatch.setattr(constantes, "CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK", 0)
    attendus = [facteur * stock - population * constantes.FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
                for population, stock in zip(populations, paniers)]
    def verifier(copie):
        assert engine._apply_consumption(copie, carte) == 0
        _controle_par_lieu(copie, attendus, facteur * sum(paniers))
    verifier(copy.deepcopy(cellule))
    partager = lieux.partager
    surfaces = [lieu.surface_km2 for lieu in lieux_de_cellule(0, cellule.area_km2)]
    monkeypatch.setattr(lieux, "partager", lambda total, poids: partager(total, surfaces))
    with pytest.raises(AssertionError):
        verifier(copy.deepcopy(cellule))


def test_donneurs_par_lieu_par_rang_croissant(monkeypatch):
    """La demande s'arrête avant d'épuiser les deux champs donneurs."""
    paniers = [0, 102, 202, 0]
    cellule, carte = _cellule_par_lieu([2, 1, 1, 20], paniers)
    cellule.area_km2 = len(cellule.lieux) * constantes.SURFACE_KM2_PAR_LIEU + 0.5
    monkeypatch.setattr(constantes, "CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK", 10)

    def verifier(copie):
        # Demande : 4 au bourg + 10 au champ affamé. Envois : 10 puis 4.
        _egal_kg(engine._apply_consumption(copie, carte), 30)
        _egal_kg(copie.food_deficit_kg, 39)
        _controle_par_lieu(copie, [0, 90, 196, 0], sum(paniers))

    inversee = copy.deepcopy(cellule)
    inversee.lieux[1].rang, inversee.lieux[2].rang = 2, 1
    with pytest.raises(AssertionError):
        verifier(inversee)
    verifier(cellule)


def test_consommation_par_lieu_sans_repartage_inutile(monkeypatch):
    """Des paniers déjà exacts et suffisants ne repassent pas par les grands entiers."""
    import sim.lieux as lieux
    cellule, carte = _cellule_par_lieu([1, 2, 3], [100.25, 500, 1000])
    cellule.food_deficit_kg = 0
    def interdit(*args):
        pytest.fail("repartage inutile de paniers déjà exacts")
    monkeypatch.setattr(lieux, "partager", interdit)
    assert engine._apply_consumption(cellule, carte) == 0
    _controle_par_lieu(cellule, [98.25, 496, 994], 1600.25)
    assert all(isinstance(_stock(lieu), int) for lieu in cellule.lieux[1:])


def test_bourg_miniers_ont_faim(monkeypatch):
    original = engine._apply_consumption
    def mesurer(capacite):
        monkeypatch.setattr(constantes, "CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK", capacite)
        monde, rng, affamees = World.charger(0), random.Random(0), set()
        consommation = engine._apply_consumption
        def observer(cellule, carte=None):
            penurie = consommation(cellule, carte)
            if (penurie > 0 and _stock(cellule) > 0
                    and (math.isinf(capacite) or _part(cellule, carte) > 0)):
                affamees.add(cellule.cell_id)
            return penurie
        with monkeypatch.context() as ctx:
            ctx.setattr(engine, "_apply_consumption", observer)
            for numero in range(60):
                engine.tick(monde, rng, numero_tick=numero)
        return len(affamees)
    sans, illimites = mesurer(0), mesurer(float("inf"))
    assert sans > 0 and illimites == 0
    monkeypatch.setattr(engine, "_apply_consumption", lambda cellule, carte=None: original(cellule))
    gratuite = mesurer(0)
    with pytest.raises(AssertionError):
        assert gratuite > 0
    print(f"bourgs_miniers_affames={sans}, illimites={illimites}, gratuits={gratuite}")


def test_distribution_par_lieu_documentee():
    from pathlib import Path
    def verifier(texte):
        section = texte.split("## La distribution à l'intérieur de la cellule\n")[1].split("\n## ")[0]
        for mot in ("partager", "surface", "chemin", "capacite_chemins_interieurs_kg", "par rang",
                    "dette", "somme", "commerce", "à proportion", "sans lieux", "écart", "niveau 3"):
            assert mot in section
        for obsolete in ("réputé réparti au prorata des surfaces", "consommation du stock persisté de chaque lieu"):
            assert obsolete not in section
        assert "sans lire les habitants et paniers persistés" not in texte
        assert "un seul panier reste partagé dans la cellule" not in texte
    texte = (Path(__file__).parents[1] / "MODELE.md").read_text(encoding="utf-8")
    verifier(texte)
    with pytest.raises(AssertionError):
        verifier(texte.replace("à proportion", "au hasard"))


@pytest.mark.parametrize("moyenne", [False, True])
def test_recolte_par_lieu_selon_surface(moyenne):
    monde = World.charger(0)
    cellule = next(c for c in monde.cells.values() if len(c.lieux) > 1)
    surfaces = [lieu.surface_km2 for lieu in lieux_de_cellule(cellule.cell_id, cellule.area_km2)]
    for entite in [cellule, *cellule.lieux]:
        ecrire_stock_marchandise(entite, "nourriture", 0)
    production = engine._apply_production_saison_moyenne if moyenne else engine._apply_production
    production(cellule, random.Random(0), monde.carte)
    assert _stock(cellule) > 0
    for lieu, surface in zip(cellule.lieux, surfaces):
        _egal_kg(_stock(lieu), _stock(cellule) * surface / cellule.area_km2)
