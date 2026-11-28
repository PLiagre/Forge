"""La soudure de 1400 : le monde tient sa première année sans joueur.

Au 1er janvier 1400, les greniers des foyers portent ce qui reste de la
récolte de 1399, de quoi manger jusqu'à la moisson (`JOUR_DE_LA_MOISSON`,
`jours_de_soudure`, `sim.world._seed_food_stock`). La preuve : graine 0,
sans joueur, l'IA active, au 365e jour, aucune cellule de la table de
référence ne perd plus de la moitié de ses habitants
par la faim. Contre-épreuves : la réserve de cinq jours d'avant la fait échouer,
et le bourg d'une ville affamée qui ne tire plus le grain de ses champs au rayon
(`engine._chemins_des_villes_affamees`) aussi.

La pire cellule de la table, Paris, perd 44,3 % de ses habitants par la faim au
365e jour, et Gand 27,1 % ; leurs gens restent au bourg (Paris y passe de 39 330
à 55 287 habitants). Sans le grain des champs au bourg, Paris en perd 55,2 % et
Gand 51,7 % ; avec cinq jours de réserve, Paris en perd 89 % dès le 90e jour.
"""
import random

import pytest

import sim.constants as constantes
from sim import engine
from sim.capitales import toutes_les_maisons_de_l_ia
from sim.ia import jouer_ia
from sim.tests.test_epreuve_jalon2 import lire_reference, placer
from sim.world import World

PART_MORTE_DE_FAIM_MAXIMALE = 0.5


def _cellules_de_la_table(monde):
    """Chaque cellule que place la table de référence (points, régions), avec ses noms."""
    reference = lire_reference()
    noms = {}
    for bloc in ("points_connus", "points", "declares"):
        for point in reference[bloc]:
            cid = placer(monde, point)
            if cid is not None:
                noms.setdefault(cid, []).append(point["nom"])
    for bloc in ("regions_denses", "regions_vides"):
        for region in reference[bloc]:
            for nom, lat, lon in region["points"]:
                cid = placer(monde, {"nom": nom, "lat": lat, "lon": lon})
                if cid is not None:
                    noms.setdefault(cid, []).append(f"{region['nom']}/{nom}")
    return noms


def _jouer_sans_joueur(monkeypatch, ticks):
    """Graine 0, l'IA active, aucun geste du joueur ; rend le monde, ses morts de faim et la table."""
    monde = World.charger(rng_seed=0)
    table = _cellules_de_la_table(monde)
    depart = {cid: monde.cells[cid].population for cid in table}
    morts = dict.fromkeys(table, 0)
    mortalite = engine._apply_mortality

    def compter(cellule, *facteurs):
        avant = cellule.population
        mortalite(cellule, *facteurs)
        if cellule.cell_id in morts:
            morts[cellule.cell_id] += avant - cellule.population

    monkeypatch.setattr(engine, "_apply_mortality", compter)
    rng, releve = random.Random(0), []
    maisons = toutes_les_maisons_de_l_ia(monde)
    for _ in range(ticks):
        jouer_ia(monde, releve, maisons)
        engine.tick(monde, rng, monde.ticks_ecoules)
    return monde, table, depart, morts, releve


def _au_bourg(monde, cid):
    """Les habitants du bourg (rang 0) de la cellule."""
    return next(lieu.population for lieu in monde.cells[cid].lieux if lieu.rang == 0)


def _mortes_de_faim(table, depart, morts):
    """Les cellules de la table qui ont perdu plus de la moitié de leurs habitants par la faim."""
    assert table, "échantillon vide : la table de référence ne place aucune cellule"
    assert all(depart[cid] > 0 for cid in table), "une cellule de la table part sans habitant"
    return sorted((round(morts[cid] / depart[cid], 4), cid, table[cid][0]) for cid in table
                  if morts[cid] / depart[cid] > PART_MORTE_DE_FAIM_MAXIMALE)


def test_la_soudure_porte_la_ration_jusqu_a_la_moisson():
    monde = World.charger(rng_seed=0)
    jours = constantes.jours_de_soudure(0)
    assert jours == constantes.JOUR_DE_LA_MOISSON == 212
    ration = constantes.FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK / constantes.TICK_DURATION_DAYS
    habitants = sum(c.population for c in monde.cells.values())
    stock = sum(c.food_stock_kg for c in monde.cells.values())
    # Niveau 1, ordre de grandeur : les sept douzièmes d'une année de ration.
    assert stock == pytest.approx(habitants * ration * jours, rel=1e-9)
    assert 0.5 < stock / (habitants * ration * constantes.CALENDAR_DAYS_PER_YEAR) < 0.65
    # Une ville porte sa ration comme une campagne : Paris, pas seulement sa cellule.
    paris = monde.cells[monde.attribution_villes.placees["Paris"]]
    assert paris.food_stock_kg == pytest.approx(paris.population * ration * jours)
    # La moisson passée, la soudure recommence à l'année : jamais négative, jamais nulle avant.
    assert constantes.jours_de_soudure(constantes.JOUR_DE_LA_MOISSON) == 0
    assert constantes.jours_de_soudure(constantes.JOUR_DE_LA_MOISSON + 1) == constantes.CALENDAR_DAYS_PER_YEAR - 1


def test_la_premiere_annee_tient_sans_joueur(monkeypatch):
    monde, table, depart, morts, releve = _jouer_sans_joueur(monkeypatch, constantes.CALENDAR_DAYS_PER_YEAR)
    assert monde.ticks_ecoules == constantes.CALENDAR_DAYS_PER_YEAR
    assert len(table) >= 50 and releve, "échantillon vide : ni table ni geste de l'IA"
    fautives = _mortes_de_faim(table, depart, morts)
    pires = sorted(table, key=lambda cid: (-morts[cid] / depart[cid], cid))[:3]
    print(f"{len(table)} cellules ; pires : " + " ; ".join(
        f"{table[cid][0]} ({cid}) {morts[cid] / depart[cid]:.1%} morts de faim, "
        f"{monde.cells[cid].population} habitants dont {_au_bourg(monde, cid)} au bourg" for cid in pires)
        + f" ; {len(releve)} gestes de l'IA")
    assert not fautives, f"cellules mortes de faim à plus de moitié au 365e jour : {fautives}"


@pytest.mark.longue
def test_sans_le_grain_des_champs_au_bourg_paris_et_gand_meurent_de_faim(monkeypatch):
    # Le bourg d'une ville affamée ne tire plus le grain de ses champs au rayon : ses chemins
    # intérieurs gardent la capacité d'une cellule nourrie.
    monkeypatch.setattr(engine, "_chemins_des_villes_affamees", lambda monde: {})
    _, table, depart, morts, _ = _jouer_sans_joueur(monkeypatch, constantes.CALENDAR_DAYS_PER_YEAR)
    fautives = _mortes_de_faim(table, depart, morts)
    print(f"sans le grain des champs au bourg, au 365e jour : {fautives}")
    nommees = {nom for _, cid, _ in fautives for nom in table[cid]}
    assert {"Paris", "Gand"} <= nommees, fautives


def test_la_reserve_de_cinq_jours_fait_echouer_la_preuve(monkeypatch):
    # Cinq jours de ration, comme avant la soudure. Les morts de faim ne font que
    # s'accumuler : un échec au 90e jour est un échec au 365e.
    monkeypatch.setattr(constantes, "JOUR_DE_LA_MOISSON", 5)
    assert constantes.jours_de_soudure(0) == 5
    _, table, depart, morts, _ = _jouer_sans_joueur(monkeypatch, 90)
    fautives = _mortes_de_faim(table, depart, morts)
    print(f"avec cinq jours, au 90e jour : {fautives}")
    assert fautives
    assert any("Paris" in table[cid] for _, cid, _ in fautives)
