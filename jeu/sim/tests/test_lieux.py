"""Preuves du découpage dérivé des cellules en lieux."""

import copy
import dataclasses
from fractions import Fraction
import json
import math

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


# Lot 235 : habitants et panier persistés, sans calcul économique par lieu.
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
            assert [lieu.stocks[marchandise] for lieu in cellule.lieux] == _partager_reference(
                total, surfaces), f"cell_id={cid} : {marchandise}"
        différences += attendus != _partager_reference(cellule.population, surfaces)
        non_paysannes_multiples += autres > 0 and len(surfaces) > 1
        contrôlées += 1
    assert contrôlées == len(monde.cells) > 0
    assert différences == non_paysannes_multiples > 0
    return différences


def test_amorcage_conserve_habitants_et_panier(monkeypatch):
    import sim.lieux as lieux_module
    from sim.model import Cell, EtatDeLieu, cellule_vers_dict

    assert {champ.name for champ in dataclasses.fields(EtatDeLieu)} == {"rang", "population", "stocks", "dette_alimentaire_kg", "duree_faim_ticks", "mortality_remainder", "natalite_remainder"}
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


def test_amorcage_documente():
    import pathlib

    def contrôler(texte):
        section = texte.split("### Ce que porte un lieu\n", 1)[1]
        section = section.split("\n### ", 1)[0].split("\n## ", 1)[0]
        for attendu in ("amorcer_lieux", "lire_habitants_par_metier", "paysans", "bourg", "amorçage", "-1"):
            assert attendu in section, f"{attendu} absent de Ce que porte un lieu"
        assert "`amorcer_lieux` partage la population et chaque marchandise selon les surfaces" not in section
        lieux = texte.split("## Les lieux d'une cellule, vue dérivée\n", 1)[1].split("\n## ", 1)[0]
        assert "ni ceux de `RepartitionBourg`" not in lieux

    texte = (pathlib.Path(__file__).parents[1] / "MODELE.md").read_text(encoding="utf-8")
    contrôler(texte)
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
    tick(synthétique, random.Random(0), numero_tick=0)
    assert [lieu.stocks["sonde"] for lieu in cellule.lieux] == lieux_module.partager(cellule.stocks["sonde"], surfaces)
    assert all("sonde_retirée" not in lieu.stocks for lieu in cellule.lieux)
    assert [lieu.population for lieu in cellule.lieux] == lieux_module.partager(cellule.population, poids_population)
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
    monkeypatch.setattr(lieux_module, "repartir_sur_les_lieux", lambda cellule: None)
    tick(témoin, random.Random(0), numero_tick=0)
    with pytest.raises(AssertionError):
        _controle_conservation(témoin)


def test_cellule_depend_du_contenu_des_lieux(monkeypatch):
    import random
    from sim.engine import tick

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
    monkeypatch.setattr(engine, "_apply_consumption", lambda cellule, carte=None: original(cellule))
    with pytest.raises(AssertionError):
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
        assert all(set(lieu) == {"rang", "surface_km2", "population", "stocks"} for lieu in cellule["lieux"])
        assert [lieu["surface_km2"] for lieu in cellule["lieux"]] == [lieu.surface_km2 for lieu in vue]
        assert sum(lieu["population"] for lieu in cellule["lieux"]) == cellule["population"]
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
        garde.setattr(engine, "_apply_mortality", lambda cellule: None)
        with pytest.raises(AssertionError): verifier()
    def dettes_inversees(cellule):
        cellule.lieux[0].dette_alimentaire_kg, cellule.lieux[1].dette_alimentaire_kg = (
            cellule.lieux[1].dette_alimentaire_kg, cellule.lieux[0].dette_alimentaire_kg)
        original(cellule)
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
