"""Preuves que l'eau disponible limite l'unique production agricole."""

import copy
import dataclasses
import json
import math
import pathlib
import statistics

import pytest

from sim import constants as _constantes
from sim.aggregation import charger_positions, facteur_de_projection, projeter
from sim.engine import (
    PluieInvalideError,
    _facteur_eau_pour_cellule,
    _production_du_tick_kg_saison_moyenne,
    population_soutenable_de,
)
from sim.pluie import (
    charger_latitude_moyenne_pluie,
    charger_releves,
    pluie_de_cellule,
    pluie_depuis_monde,
    pluie_par_cellule,
)
from sim.snapshot_export import _couche_consommee, build_snapshot_document
from sim.world import CARTE_PATH, World


POINT_DESERT_OCCIDENTAL = (30.9, 28.5)
POINT_FLANDRE = (51.0, 3.7)


def _cellule_la_plus_proche(point, positions, facteur):
    cible = projeter(*point, facteur)
    return min(
        positions,
        key=lambda cell_id: sum(
            (a - b) ** 2
            for a, b in zip(projeter(*positions[cell_id], facteur), cible)
        ),
    )


def _cellules_repères():
    positions = charger_positions()
    facteur = facteur_de_projection(charger_latitude_moyenne_pluie())
    return (
        _cellule_la_plus_proche(POINT_DESERT_OCCIDENTAL, positions, facteur),
        _cellule_la_plus_proche(POINT_FLANDRE, positions, facteur),
    )


def _densites(monde):
    return {
        cell_id: cellule.population / cellule.area_km2
        for cell_id, cellule in monde.cells.items()
    }


def test_courbe_du_facteur_eau(monkeypatch):
    """SC1 — la courbe est bornée, monotone et relit ses constantes."""
    bas = _constantes.PLUIE_SANS_CULTURE_MM
    haut = _constantes.PLUIE_PLEINE_CULTURE_MM
    milieu = (bas + haut) / _constantes.FACTEUR_DEUX
    pluies = (0.0, bas, milieu, haut, haut * 10)
    facteurs = [_constantes.facteur_eau(pluie) for pluie in pluies]

    assert facteurs[0] == _constantes.FACTEUR_EAU_PLANCHER
    assert facteurs[1] == _constantes.FACTEUR_EAU_PLANCHER
    assert _constantes.FACTEUR_EAU_PLANCHER < facteurs[2] < 1.0
    assert facteurs[3] == 1.0
    assert facteurs[4] == 1.0
    assert all(a <= b for a, b in zip(facteurs, facteurs[1:]))
    assert all(0.0 < facteur <= 1.0 for facteur in facteurs)

    valeur_initiale = facteurs[2]
    monkeypatch.setattr(_constantes, "PLUIE_PLEINE_CULTURE_MM", haut * 2)
    valeur_modifiee = _constantes.facteur_eau(milieu)

    print(f"points_controles = {len(pluies)}")
    print(f"facteurs = {facteurs}")
    print(f"constante_relue = {valeur_modifiee != valeur_initiale}")
    assert valeur_modifiee != valeur_initiale


def test_carte_lue_porte_la_pluie_de_la_vue():
    """SC2 — l'enrichissement mémoire recopie exactement la vue dérivée."""
    carte_doc = World.lire_carte()
    monde = World.charger(0)
    pluies = pluie_depuis_monde(monde)
    attendues = {
        cell_id: pluie_de_cellule(cell_id, pluies) for cell_id in monde.cells
    }
    conformes = sum(
        raw["pluie_mm_par_an"] == attendues[raw["cell_id"]]
        for raw in carte_doc["cellules"]
    )

    document_disque = json.loads(CARTE_PATH.read_text(encoding="utf-8"))
    cles_pluie_disque = sum(
        "pluie_mm_par_an" in raw for raw in document_disque["cellules"]
    )

    releves = charger_releves()
    par_rang = sorted(releves, key=lambda releve: (releve.mm_par_an, releve.id))
    valeurs_inversees = [releve.mm_par_an for releve in reversed(par_rang)]
    inverses = [
        dataclasses.replace(releve, mm_par_an=valeur)
        for releve, valeur in zip(par_rang, valeurs_inversees)
    ]
    contre_vue = pluie_par_cellule(
        charger_positions(), inverses, charger_latitude_moyenne_pluie()
    )
    contre = {pluie.cell_id: pluie.mm_par_an for pluie in contre_vue}
    non_conformes = sum(
        raw["pluie_mm_par_an"] != contre[raw["cell_id"]]
        for raw in carte_doc["cellules"]
    )

    print(f"cellules_conformes = {conformes} / {len(monde.cells)}")
    print(f"cles_pluie_sur_disque = {cles_pluie_disque}")
    print(f"contre_epreuve_non_conforme = {non_conformes}")
    assert len(monde.cells) > 0
    assert conformes == len(monde.cells)
    assert cles_pluie_disque == 0
    assert non_conformes > 0


@pytest.mark.parametrize("valeur", [pytest.param(None, id="absente"), True, "sec", math.nan, -1.0])
def test_refus_des_pluies_invalides(valeur):
    """SC3 — toute pluie absente ou inexploitable est refusée en la nommant."""
    carte_doc = World.lire_carte()
    cell_id = carte_doc["cellules"][0]["cell_id"]
    alteree = copy.deepcopy(carte_doc)
    if valeur is None:
        del alteree["cellules"][0]["pluie_mm_par_an"]
    else:
        alteree["cellules"][0]["pluie_mm_par_an"] = valeur

    with pytest.raises(PluieInvalideError) as capture:
        World.charger(0, carte_doc=alteree)

    print(f"cellule_refusee = {cell_id}")
    print(f"valeur_refusee = {valeur!r}")
    assert str(cell_id) in str(capture.value)


def test_refus_de_la_pluie_non_numerique_et_zero_accepte():
    """SC3 — l'enregistrement absent est refusé, mais zéro reste une mesure."""
    carte_doc = World.lire_carte()
    cell_id = carte_doc["cellules"][0]["cell_id"]
    with pytest.raises(PluieInvalideError) as capture:
        monde_temoin = World.charger(0, carte_doc=carte_doc)
        _facteur_eau_pour_cellule(monde_temoin.cells[cell_id], {})

    zero = copy.deepcopy(carte_doc)
    seuil_bas = copy.deepcopy(carte_doc)
    zero["cellules"][0]["pluie_mm_par_an"] = 0.0
    seuil_bas["cellules"][0]["pluie_mm_par_an"] = (
        _constantes.PLUIE_SANS_CULTURE_MM
    )
    monde_zero = World.charger(0, carte_doc=zero)
    monde_seuil = World.charger(0, carte_doc=seuil_bas)
    soutenable_zero = population_soutenable_de(
        monde_zero.cells[cell_id], monde_zero.carte
    )
    soutenable_plancher = population_soutenable_de(
        monde_seuil.cells[cell_id], monde_seuil.carte
    )

    print(f"cellule_zero = {cell_id}")
    print(f"population_soutenable_au_plancher = {soutenable_zero}")
    assert str(cell_id) in str(capture.value)
    assert soutenable_zero == soutenable_plancher


def test_desert_se_vide_et_terre_mouillee_ne_bouge(monkeypatch):
    """SC4 — l'aridité inverse le faux peuplement du désert occidental."""
    desert_id, flandre_id = _cellules_repères()
    monde = World.charger(0)
    densites = _densites(monde)
    mediane = statistics.median(densites.values())

    assert densites[desert_id] < mediane
    assert densites[flandre_id] > mediane

    monkeypatch.setattr(_constantes, "facteur_eau", lambda pluie: 1.0)
    monde_sans_aridite = World.charger(0)
    densites_sans = _densites(monde_sans_aridite)
    mediane_sans = statistics.median(densites_sans.values())

    print(f"densite_desert = {densites[desert_id]} / mediane {mediane}")
    print(f"densite_flandre = {densites[flandre_id]}")
    print(
        "densite_desert_sans_aridite = "
        f"{densites_sans[desert_id]} / mediane {mediane_sans}"
    )
    assert densites_sans[desert_id] >= mediane_sans


def test_une_seule_formule_de_production(monkeypatch):
    """SC5 — plafond, amorçage et tick partagent le même facteur d'eau."""
    desert_id, flandre_id = _cellules_repères()
    monde = World.charger(0)
    soutenables = {
        cell_id: population_soutenable_de(monde.cells[cell_id], monde.carte)
        for cell_id in (desert_id, flandre_id)
    }
    pluie_desert = monde.carte[desert_id]["pluie_mm_par_an"]
    attendu_desert = _constantes.facteur_eau(pluie_desert)

    monkeypatch.setattr(_constantes, "facteur_eau", lambda pluie: 1.0)
    sans_eau = {
        cell_id: population_soutenable_de(monde.cells[cell_id], monde.carte)
        for cell_id in (desert_id, flandre_id)
    }
    rapport_desert = soutenables[desert_id] / sans_eau[desert_id]

    rendement = _constantes.rendement_moyen_courant()
    ecarts = []
    for cellule in monde.cells.values():
        soutenable = population_soutenable_de(cellule, monde.carte)
        production = _production_du_tick_kg_saison_moyenne(
            cellule, rendement, monde.carte
        )
        ecarts.append(
            math.isclose(
                soutenable
                * _constantes.FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK,
                production,
                rel_tol=1e-9,
            )
        )

    print(f"rapport_desert = {rapport_desert} / attendu {attendu_desert}")
    print(f"soutenable_flandre_inchange = {soutenables[flandre_id] == sans_eau[flandre_id]}")
    print(f"cellules_formule_unique = {sum(ecarts)} / {len(ecarts)}")
    assert rapport_desert == pytest.approx(attendu_desert, abs=1e-12)
    assert soutenables[flandre_id] == sans_eau[flandre_id]
    assert len(ecarts) > 0
    assert all(ecarts)


def test_sonde_voit_la_couche_pluie(monkeypatch):
    """SC6 — le snapshot mesure la consommation de la pluie par le moteur."""
    document = build_snapshot_document(World.charger(0), 0, 0)
    pluie = document["couches"]["pluie"]

    assert pluie == {"dans_la_carte": True, "utilisee_par_le_moteur": True}
    assert document["schema_version"] == "v0a-5"

    monkeypatch.setattr(_constantes, "facteur_eau", lambda valeur: 1.0)
    contre_epreuve = _couche_consommee("pluie")

    print(f"couche_pluie = {pluie}")
    print(f"schema_version = {document['schema_version']}")
    print(f"sonde_neutralisee = {contre_epreuve}")
    assert contre_epreuve is False
