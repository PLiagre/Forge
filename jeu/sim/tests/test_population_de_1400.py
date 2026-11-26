"""Les habitants de 1400 par grande région (`sim/regions.py`, `data/population-1400.json`).

Sur le monde frais, graine 0 : la somme des habitants des lieux de chaque région de la table tombe
dans sa fourchette sourcée (sa cible à un tiers près), et la Lituanie est moins de moitié aussi dense
que la France. Le lieu va à sa région par son pays de 1400 (la table des frontières), ou par la
cellule que la région nomme. La table elle-même : elle se lit et dérive ses cibles de ses sources ;
elle refuse en les nommant une cible sans source ou non positive, une part hors de ]0, 1], un pays
inconnu, un pays dans deux régions ou dans aucune ; une région sans pays sur la carte échoue, et une
cellule de la carte hors de toute région n'a pas de part.
"""
import copy
import dataclasses
import json
import re
from fractions import Fraction
from types import SimpleNamespace

import pytest

from sim.frontieres import charger_frontieres, puissances_des_lieux, terres_des_lieux, villes_des_lieux
from sim.lieux import surfaces_des_lieux
from sim.puissances import charger_table, puissances_depuis_monde
from sim.regions import (
    _CHEMIN, RegionInvalide, charger_regions, habitants_des_regions, parts_cultivees, regions_des_lieux,
)
from sim.world import World

_DOCUMENT = json.loads(_CHEMIN.read_text(encoding="utf-8"))
_REGIONS = [brute["id"] for brute in _DOCUMENT["regions"]]
# Les grandes régions que la table doit porter : celles de la règle du monde, et la Scandinavie
# sans laquelle l'Union de Kalmar n'aurait pas de région.
_ATTENDUES = {"france", "iles", "italie", "iberie", "empire", "pologne-lituanie", "hongrie", "balkans",
              "russie", "anatolie", "maghreb", "egypte", "scandinavie"}


@pytest.fixture(scope="module")
def livre():
    monde = World.charger(0)
    table = charger_table()
    frontieres = charger_frontieres(table=table, carte=monde.carte)
    regions = charger_regions(table=table, frontieres=frontieres, carte=monde.carte)
    return SimpleNamespace(monde=monde, table=table, frontieres=frontieres, regions=regions,
                           habitants=habitants_des_regions(monde, regions, table, frontieres))


def _puissance(table, nom):
    return next(p.id for p in table.puissances if p.nom == nom)


def _ecrire(tmp_path, document):
    chemin = tmp_path / "population.json"
    chemin.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    return chemin


def _region(document, identifiant):
    return next(brute for brute in document["regions"] if brute["id"] == identifiant)


# --- La table livrée ---

def test_la_table_livree_porte_ses_regions_et_derive_ses_cibles(livre):
    regions = livre.regions.par_id()
    assert set(regions) == _ATTENDUES
    assert livre.regions.tolerance == Fraction(1, 3)
    for region in livre.regions.regions:
        assert region.puissances or region.terres, region.id
        assert region.cible == round(sum(pays.habitants * pays.part for pays in region.habitants_1400)) > 0
        assert all(pays.source in livre.regions.sources for pays in region.habitants_1400)
        assert all((pays.part == 1) == (pays.raison is None) for pays in region.habitants_1400), region.id
    # La France de HYDE, en entier : la cible est son chiffre, la fourchette un tiers de part et d'autre.
    france = regions["france"]
    assert [(p.pays_actuel, p.habitants, p.part) for p in france.habitants_1400] == [("France", 10930934, 1)]
    assert livre.regions.fourchette(france) == (Fraction(10930934 * 2, 3), Fraction(10930934 * 4, 3))
    # Chaque puissance de la table est dans une région, et une seule.
    assert set(livre.regions.region_de_puissance) == {p.id for p in livre.table.puissances}


def test_chaque_cellule_de_la_carte_a_sa_region_et_sa_part(livre):
    parts = parts_cultivees(livre.monde.carte, livre.regions, livre.frontieres, livre.table)
    assert list(parts) == sorted(livre.monde.carte)
    assert all(0 < part <= 1 for part in parts.values())
    # Une cellule partagée entre deux régions prend la moyenne des parts de ses villes, une par ville
    # (Ljubljana et Trieste à l'Empire, Modruš à la Hongrie) ; une cellule nommée
    # par une région prend la sienne, quels que soient ses pays.
    ljubljana = next(cid for cid, villes in livre.frontieres.partages.items()
                     if [v.nom for v in villes] == ["Ljubljana", "Trieste", "Modruš"])
    avignon = next(cid for cid, villes in livre.frontieres.partages.items() if "Avignon" in [v.nom for v in villes])
    par_id = livre.regions.par_id()
    retouchees = tuple(dataclasses.replace(r, part_cultivee={"empire": 0.2, "hongrie": 0.6, "italie": 0.9}
                                           .get(r.id, r.part_cultivee))
                       for r in livre.regions.regions)
    table = dataclasses.replace(livre.regions, regions=retouchees)
    parts = parts_cultivees(livre.monde.carte, table, livre.frontieres, livre.table)
    assert parts[ljubljana] == pytest.approx((0.2 + 0.2 + 0.6) / 3)
    assert avignon in table.region_de_cellule and parts[avignon] == par_id["france"].part_cultivee


def test_une_cellule_hors_de_toute_region_n_a_pas_de_part(livre):
    carte = dict(livre.monde.carte)
    inconnue = max(carte) + 1
    carte[inconnue] = carte[min(carte)]
    with pytest.raises(RegionInvalide, match=f"cellule {inconnue}.*sans région"):
        parts_cultivees(carte, livre.regions, livre.frontieres, livre.table)


def test_chaque_lieu_du_monde_a_sa_region(livre):
    des_lieux = regions_des_lieux(livre.monde, livre.regions, livre.table, livre.frontieres)
    lieux = [(cid, lieu.rang) for cid, cellule in sorted(livre.monde.cells.items()) for lieu in cellule.lieux]
    assert lieux and sorted(des_lieux) == lieux
    assert sum(livre.habitants.values()) == sum(c.population for c in livre.monde.cells.values())
    # Les Ottomans se partagent : Constantinople est aux Balkans, Brousse en Anatolie.
    constantinople = next(cid for cid, villes in livre.frontieres.partages.items()
                          if "Constantinople" in [v.nom for v in villes])
    ottomans = _puissance(livre.table, "Ottomans")
    assert {des_lieux[constantinople, lieu.rang] for lieu in livre.monde.cells[constantinople].lieux} == {"balkans"}
    anatoliennes = [cid for cid, p in livre.frontieres.cellules.items() if p == ottomans
                    and cid not in livre.regions.region_de_cellule]
    assert anatoliennes and {des_lieux[cid, 0] for cid in anatoliennes} == {"anatolie"}


# --- Les refus de la table ---

def _retirer_la_premiere_source(document):
    _region(document, "france")["habitants_1400"] = []


def _habitants_nuls(document):
    _region(document, "france")["habitants_1400"][0]["habitants"] = 0
    _region(document, "france")["cible"] = 0


def _cible_qui_ment(document):
    _region(document, "france")["cible"] += 1


def _part_nulle(document):
    _region(document, "egypte")["part_cultivee"] = 0


def _part_trop_grande(document):
    _region(document, "egypte")["part_cultivee"] = 1.5


def _puissance_inconnue(document):
    _region(document, "egypte")["puissances"].append(999)


def _terre_inconnue(document):
    _region(document, "maghreb")["terres"].append("atlantide")


def _pays_dans_deux_regions(document):
    _region(document, "egypte")["puissances"].append(26)


def _pays_dans_aucune_region(document):
    _region(document, "scandinavie")["puissances"].remove(21)


def _cellule_dans_deux_regions(document):
    _region(document, "egypte")["cellules"] = [2943]
    _region(document, "egypte")["raison_cellules"] = "essai"


def _part_sans_raison(document):
    del _region(document, "egypte")["habitants_1400"][0]["raison"]


def _part_hors_bornes(document):
    _region(document, "egypte")["habitants_1400"][0]["part"] = "3/2"
    _region(document, "egypte")["cible"] = 6075000


def _source_inconnue(document):
    _region(document, "france")["habitants_1400"][0]["source"] = "ouï-dire"


@pytest.mark.parametrize("retouche,message", [
    (_retirer_la_premiere_source, "'france', champ habitants_1400 : liste vide"),
    (_habitants_nuls, "'france', champ habitants_1400.France.habitants : nombre positif attendu"),
    (_cible_qui_ment, "'france', champ cible : 10930935 déclarés"),
    (_part_nulle, "'egypte', champ part_cultivee : part hors de"),
    (_part_trop_grande, "'egypte', champ part_cultivee : part hors de"),
    (_puissance_inconnue, "'egypte', champ puissances : puissance inconnue 999"),
    (_terre_inconnue, "'maghreb', champ terres : terre sans État inconnue 'atlantide'"),
    (_pays_dans_deux_regions, "'egypte', champ puissances : 26 déjà dans la région 'anatolie'"),
    (_pays_dans_aucune_region, "puissances 21 : dans aucune région"),
    (_cellule_dans_deux_regions, "champ cellules : 2943 déjà dans la région"),
    (_part_sans_raison, "'egypte', champ habitants_1400.Égypte : une part partielle porte sa part et sa raison"),
    (_part_hors_bornes, "'egypte', champ habitants_1400.Égypte.part : part hors de"),
    (_source_inconnue, "'france', champ habitants_1400.France.source : source inconnue"),
])
def test_la_table_refuse_et_nomme_la_region_et_le_champ(livre, tmp_path, retouche, message):
    document = copy.deepcopy(_DOCUMENT)
    retouche(document)
    with pytest.raises(RegionInvalide, match=re.escape(message)):
        charger_regions(_ecrire(tmp_path, document), table=livre.table, frontieres=livre.frontieres)
    # Contre-épreuve : la table livrée, écrite au même endroit, se lit.
    charger_regions(_ecrire(tmp_path, _DOCUMENT), table=livre.table, frontieres=livre.frontieres)


def test_une_cellule_nommee_hors_de_la_carte_est_refusee(livre, tmp_path):
    document = copy.deepcopy(_DOCUMENT)
    _region(document, "egypte")["cellules"] = [max(livre.monde.carte) + 1]
    _region(document, "egypte")["raison_cellules"] = "essai"
    chemin = _ecrire(tmp_path, document)
    with pytest.raises(RegionInvalide, match="absente de la carte"):
        charger_regions(chemin, table=livre.table, frontieres=livre.frontieres, carte=livre.monde.carte)
    # Sur une part de la carte (un monde d'épreuve), la cellule absente ne se juge pas.
    charger_regions(chemin, table=livre.table, frontieres=livre.frontieres, carte=livre.monde.carte, partielle=True)


def test_une_region_sans_pays_sur_la_carte_echoue(livre, tmp_path):
    """Le Saint-Empire ne tient aucune cellule : une région qui n'aurait que lui n'est pas sur la carte."""
    empire = _puissance(livre.table, "Saint-Empire")
    assert empire not in livre.frontieres.cellules.values()
    document = copy.deepcopy(_DOCUMENT)
    _region(document, "empire")["puissances"].remove(empire)
    vide = copy.deepcopy(_region(document, "egypte")) | {"id": "vide", "nom": "Vide", "puissances": [empire]}
    document["regions"].append(vide)
    chemin = _ecrire(tmp_path, document)
    with pytest.raises(RegionInvalide, match="'vide', champ puissances : aucune cellule de la carte"):
        charger_regions(chemin, table=livre.table, frontieres=livre.frontieres, carte=livre.monde.carte)
    # Contre-épreuve : sans carte à juger, la même table se lit.
    assert "vide" in charger_regions(chemin, table=livre.table, frontieres=livre.frontieres).par_id()


# --- Le monde livré ---

@pytest.mark.parametrize("identifiant", _REGIONS)
def test_les_habitants_de_chaque_region_tombent_dans_leur_fourchette(livre, identifiant):
    region = livre.regions.par_id()[identifiant]
    habitants = livre.habitants[identifiant]
    assert habitants > 0, f"échantillon vide : la région {identifiant} n'a aucun habitant"
    bas, haut = livre.regions.fourchette(region)
    assert bas <= habitants <= haut, (
        f"{region.nom} : {habitants} habitants, hors de [{float(bas):.0f}, {float(haut):.0f}] "
        f"(cible {region.cible})")


def test_la_lituanie_est_moins_de_moitie_aussi_dense_que_la_france(livre):
    monde, table, frontieres = livre.monde, livre.table, livre.frontieres
    vue = puissances_depuis_monde(monde, table=table, frontieres=frontieres)
    villes = villes_des_lieux(monde, table, frontieres)
    puissances = puissances_des_lieux(monde, table, frontieres, villes)
    terres = terres_des_lieux(monde, table, frontieres, villes)
    voulues = {_puissance(table, "Lituanie"): "Lituanie", _puissance(table, "France"): "France"}
    habitants, surfaces = dict.fromkeys(voulues.values(), 0), dict.fromkeys(voulues.values(), 0.0)
    for cid, cellule in sorted(monde.cells.items()):
        surfaces_des_rangs = surfaces_des_lieux(cid, cellule.area_km2)
        for lieu in cellule.lieux:
            cle = (cid, lieu.rang)
            nom = None if cle in terres else voulues.get(puissances.get(cle, vue.get(cid)))
            if nom is not None:
                habitants[nom] += lieu.population
                surfaces[nom] += surfaces_des_rangs[lieu.rang]
    assert all(surfaces.values()) and all(habitants.values()), "échantillon vide"
    lituanie, france = (habitants[n] / surfaces[n] for n in ("Lituanie", "France"))
    assert lituanie < france / 2, f"Lituanie {lituanie:.2f} hab/km², France {france:.2f} hab/km²"
