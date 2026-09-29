"""Preuves que la crue du Nil apporte de l'eau aux champs du delta."""

import ast
import copy
import json
import math
import pathlib
import statistics

import pytest

from sim import constants as _constantes
from sim.aggregation import charger_positions, derive_appartenance
from sim.engine import (
    CrueInvalideError,
    _production_du_tick_kg_saison_moyenne,
    population_soutenable_de,
)
from sim.fleuve import (
    cellules_traversees,
    charger_latitude_moyenne_fleuve,
    charger_points,
)
from sim.pluie import pluie_de_cellule, pluie_depuis_monde
from sim.world import CARTE_PATH, World


_RACINE_SIM = pathlib.Path(__file__).parent.parent
_POINT_DELTA = (30.8, 31.0)
_POINT_DESERT_OCCIDENTAL = (30.9, 28.5)
_POINT_SUEZ = (30.45, 32.5)
_ABSENTE = object()


def _cellule_de_reference(point) -> int:
    class Centroide:
        def __init__(self, cell_id, position):
            self.id = cell_id
            self.lat, self.lon = position

    positions = charger_positions()
    centroides = [
        Centroide(cell_id, position) for cell_id, position in positions.items()
    ]
    return derive_appartenance(
        {0: point}, centroides, charger_latitude_moyenne_fleuve()
    )[0]


def _cellules_de_reference() -> tuple[int, int, int]:
    return tuple(
        _cellule_de_reference(point)
        for point in (_POINT_DELTA, _POINT_DESERT_OCCIDENTAL, _POINT_SUEZ)
    )


def _densites(monde) -> dict[int, float]:
    return {
        cell_id: cellule.population / cellule.area_km2
        for cell_id, cellule in monde.cells.items()
    }


def _carte_sans_crue() -> dict:
    carte = World.lire_carte()
    for enregistrement in carte["cellules"]:
        enregistrement["crue_mm_par_an"] = 0.0
    return carte


def test_carte_lue_porte_la_crue_du_fleuve():
    """SC1 : toute cellule, et elle seule, reçoit la crue dérivée du Nil."""
    carte = World.lire_carte()
    traversees = {
        cellule.cell_id
        for cellule in cellules_traversees(
            charger_points(),
            charger_positions(),
            charger_latitude_moyenne_fleuve(),
        )
    }
    conformes = sum(
        raw["crue_mm_par_an"]
        == (
            _constantes.CRUE_EQUIVALENT_PLUIE_MM
            if raw["cell_id"] in traversees
            else 0.0
        )
        for raw in carte["cellules"]
    )
    non_nulles = sum(raw["crue_mm_par_an"] != 0.0 for raw in carte["cellules"])

    print(f"cellules_conformes = {conformes} / {len(carte['cellules'])}")
    print(f"cellules_traversees = {len(traversees)}")
    print(f"crues_non_nulles = {non_nulles}")
    assert _constantes.CRUE_EQUIVALENT_PLUIE_MM > _constantes.PLUIE_PLEINE_CULTURE_MM
    assert len(carte["cellules"]) > 0
    assert conformes == len(carte["cellules"])
    assert 0 < non_nulles == len(traversees) < len(carte["cellules"])


def test_carte_lue_preserve_la_pluie_et_le_fichier_disque():
    """SC1 : la crue est une eau distincte et seulement ajoutée en mémoire."""
    carte = World.lire_carte()
    pluies = pluie_depuis_monde(World.charger(0))
    pluies_conformes = sum(
        raw["pluie_mm_par_an"] == pluie_de_cellule(raw["cell_id"], pluies)
        for raw in carte["cellules"]
    )
    document_disque = json.loads(CARTE_PATH.read_text(encoding="utf-8"))
    cles_crue_disque = sum(
        "crue_mm_par_an" in raw for raw in document_disque["cellules"]
    )

    print(f"pluies_conformes = {pluies_conformes} / {len(carte['cellules'])}")
    print(f"cles_crue_sur_disque = {cles_crue_disque}")
    assert len(carte["cellules"]) > 0
    assert pluies_conformes == len(carte["cellules"])
    assert cles_crue_disque == 0


def test_carte_relit_la_constante_de_crue(monkeypatch):
    """SC1 : un remplacement en mémoire atteint chaque nouvelle lecture."""
    monkeypatch.setattr(_constantes, "CRUE_EQUIVALENT_PLUIE_MM", 0.0)
    carte = World.lire_carte()
    non_nulles = sum(raw["crue_mm_par_an"] != 0.0 for raw in carte["cellules"])

    print(f"cellules_lues = {len(carte['cellules'])}")
    print(f"crues_non_nulles = {non_nulles}")
    assert len(carte["cellules"]) > 0
    assert non_nulles == 0


def test_refus_des_crues_invalides():
    """SC2 : toute crue absente ou inexploitable est refusée en la nommant."""
    carte = World.lire_carte()
    delta, _, _ = _cellules_de_reference()
    index_delta = next(
        index
        for index, raw in enumerate(carte["cellules"])
        if raw["cell_id"] == delta
    )
    valeurs = (_ABSENTE, None, True, "crue", math.nan, math.inf, -1.0)
    refus = 0
    for valeur in valeurs:
        alteree = copy.deepcopy(carte)
        if valeur is _ABSENTE:
            del alteree["cellules"][index_delta]["crue_mm_par_an"]
        else:
            alteree["cellules"][index_delta]["crue_mm_par_an"] = valeur
        with pytest.raises(CrueInvalideError) as capture:
            World.charger(0, carte_doc=alteree)
        assert str(delta) in str(capture.value)
        refus += 1

    print(f"cellule_refusee = {delta}")
    print(f"refus_observes = {refus} / {len(valeurs)}")
    assert refus == len(valeurs)


def test_crue_zero_est_une_mesure_et_ne_change_pas_la_pluie():
    """SC2 : zéro est accepté et la pluie lue reste exactement la même."""
    carte = World.lire_carte()
    delta, _, _ = _cellules_de_reference()
    pluie_attendue = next(
        raw["pluie_mm_par_an"]
        for raw in carte["cellules"]
        if raw["cell_id"] == delta
    )
    zero = copy.deepcopy(carte)
    next(
        raw for raw in zero["cellules"] if raw["cell_id"] == delta
    )["crue_mm_par_an"] = 0.0
    monde = World.charger(0, carte_doc=zero)

    print(f"cellule_zero = {delta}")
    print(f"pluie_inchangee = {monde.carte[delta]['pluie_mm_par_an'] == pluie_attendue}")
    assert monde.carte[delta]["crue_mm_par_an"] == 0.0
    assert monde.carte[delta]["pluie_mm_par_an"] == pluie_attendue


def test_densite_du_delta_depasse_la_mediane_grace_a_la_crue():
    """SC3 : la crue remplit le delta sans remplir le désert ni Suez."""
    delta, desert, suez = _cellules_de_reference()
    monde = World.charger(0)
    densites = _densites(monde)
    mediane = statistics.median(densites.values())
    monde_sec = World.charger(0, carte_doc=_carte_sans_crue())
    densites_seches = _densites(monde_sec)
    mediane_seche = statistics.median(densites_seches.values())

    print(f"cellules_distinctes = {len({delta, desert, suez})}")
    print(f"densite_delta = {densites[delta]} / mediane {mediane}")
    print(f"densite_desert = {densites[desert]}")
    print(f"densite_suez = {densites[suez]}")
    print(f"delta_sans_crue = {densites_seches[delta]} / mediane {mediane_seche}")
    assert len({delta, desert, suez}) == 3
    assert densites[delta] > mediane
    assert densites[desert] < mediane
    assert densites[suez] < mediane
    assert densites_seches[delta] < mediane_seche


def test_crue_entre_dans_l_argument_de_l_unique_facteur_eau():
    """SC4 : le gain du delta est exactement le rapport des facteurs d'eau."""
    delta, desert, suez = _cellules_de_reference()
    monde = World.charger(0)
    monde_sec = World.charger(0, carte_doc=_carte_sans_crue())
    soutenables = {
        cell_id: population_soutenable_de(monde.cells[cell_id], monde.carte)
        for cell_id in (delta, desert, suez)
    }
    soutenables_secs = {
        cell_id: population_soutenable_de(
            monde_sec.cells[cell_id], monde_sec.carte
        )
        for cell_id in (delta, desert, suez)
    }
    pluie = monde.carte[delta]["pluie_mm_par_an"]
    crue = monde.carte[delta]["crue_mm_par_an"]
    rapport = soutenables[delta] / soutenables_secs[delta]
    attendu = _constantes.facteur_eau(pluie + crue) / _constantes.facteur_eau(pluie)

    print(f"rapport_delta = {rapport} / attendu {attendu}")
    print(f"cellules_non_traversees_inchangees = {soutenables[desert] == soutenables_secs[desert] and soutenables[suez] == soutenables_secs[suez]}")
    assert rapport == pytest.approx(attendu, rel=1e-12, abs=0.0)
    assert rapport != 1.0
    assert soutenables[desert] == soutenables_secs[desert]
    assert soutenables[suez] == soutenables_secs[suez]


def test_plafond_et_production_partagent_la_meme_formule():
    """SC4 : chaque plafond se déduit de la production moyenne du moteur."""
    monde = World.charger(0)
    rendement = _constantes.rendement_moyen_courant()
    conformes = 0
    for cellule in monde.cells.values():
        soutenable = population_soutenable_de(cellule, monde.carte)
        production = _production_du_tick_kg_saison_moyenne(
            cellule, rendement, monde.carte
        )
        conformes += math.isclose(
            soutenable
            * _constantes.FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK,
            production,
            rel_tol=1e-9,
        )

    print(f"cellules_formule_unique = {conformes} / {len(monde.cells)}")
    assert len(monde.cells) > 0
    assert conformes == len(monde.cells)


def test_vue_du_fleuve_n_a_que_world_pour_lecteur():
    """SC5 : seul le chargement de carte importe la vue dérivée du Nil."""
    def importe_fleuve(source: str) -> bool:
        arbre = ast.parse(source)
        for noeud in ast.walk(arbre):
            if isinstance(noeud, ast.Import) and any(
                alias.name == "sim.fleuve" for alias in noeud.names
            ):
                return True
            if isinstance(noeud, ast.ImportFrom) and noeud.module == "sim.fleuve":
                return True
        return False

    modules = [
        chemin
        for chemin in _RACINE_SIM.glob("*.py")
        if chemin.name != "fleuve.py"
    ]
    lecteurs = {
        chemin.name
        for chemin in modules
        if importe_fleuve(chemin.read_text(encoding="utf-8"))
    }
    contre_epreuve = importe_fleuve("from sim.fleuve import charger_points")

    print(f"modules_parcourus = {len(modules)}")
    print(f"lecteurs = {sorted(lecteurs)}")
    print(f"contre_epreuve_detectee = {contre_epreuve}")
    assert len(modules) > 0
    assert lecteurs == {"world.py"}
    assert contre_epreuve
