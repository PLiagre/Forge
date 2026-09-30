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
