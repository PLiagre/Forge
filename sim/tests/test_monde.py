"""
Chargement du monde, ligne de commande et snapshot.

Ce que ce fichier protège :
  - le monde chargé correspond au fichier de carte, sans nombre codé en dur ;
  - la ligne de commande amorce un monde et le rend en JSON stable ;
  - le snapshot a un schéma fermé, recalcule la province au lieu de la
    stocker, et distingue une sentinelle « non calculé » d'un zéro mesuré.

Fusion des anciens fichiers world, cli et snapshot_v0a.
"""

from __future__ import annotations

from sim.snapshot_export import SnapshotExportError, export_snapshot
from sim.model import Cell

import json
import pathlib
import pytest
from sim.world import World
_REPO_ROOT = pathlib.Path(__file__).parent.parent.parent
_CARTE_PATH = _REPO_ROOT / "data" / "world-1400.json"
import subprocess
import sys
from pathlib import Path
from sim.__main__ import run
from sim.constants import DEFAULT_CLI_SEED
_REPO = Path(__file__).resolve().parents[2]
import hashlib
import copy
import os
import re
import tempfile
import zipfile
from sim.aggregation import (
    agregat_depuis_monde,
    bourg_depuis_monde,
    identifiant_de_province_de_cellule,
    repartition_bourg_de_cellule_consultation,
    repartitions_avec_bourg,
)
from sim.constants import SNAPSHOT_SCHEMA_VERSION
from sim.snapshot_export import build_snapshot_document, serialize_snapshot
_ROOT_KEYS = {
    "schema_version",
    "seed",
    "tick",
    "cell_count",
    "crs",
    "carte",
    "couches",
    "cells",
    "jour_de_tick",
}
_CELL_KEYS = {
    "cell_id",
    "area_km2",
    "geometry",
    "centroid",
    "population",
    "stocks",
    "food_deficit_kg",
    "hunger_ticks",
    "mortality_remainder",
    "province",
    "bourg",
    "climat",
    "gisements",
    "relief",
}
def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --- test_world.py ---
def test_le_monde_charge_exactement_la_carte():
    """
    Le monde chargé contient exactement ce que porte la carte figée :
    ni cellule inventée, ni arête perdue. Aucun nombre codé en dur.
    """
    world = World.charger()
    carte = json.loads(_CARTE_PATH.read_text(encoding="utf-8"))

    print(f"cellules chargées = {len(world.cells)} / carte = {len(carte['cellules'])}")
    print(f"arêtes chargées = {len(world.adjacency)} / carte = {len(carte['adjacence'])}")

    assert len(world.cells) == len(carte["cellules"])
    assert len(world.adjacency) == len(carte["adjacence"])
    assert set(world.cells) == {c["cell_id"] for c in carte["cellules"]}


def test_cells_have_required_fields():
    """Chaque cellule chargée possède les champs attendus avec des valeurs valides."""
    world = World.charger()
    for cid, cell in world.cells.items():
        assert cell.cell_id == cid
        assert cell.area_km2 > 0
        assert cell.population >= 0
        assert cell.food_stock_kg >= 0
        assert cell.hunger_ticks >= 0


# --- test_cli.py ---
def test_run_zero_tick_preserve_population():
    resume = run(ticks=0, seed=DEFAULT_CLI_SEED)
    assert resume["sans_unity"] is True
    assert resume["ticks"] == 0
    assert resume["cellules"] > 0
    assert resume["population_depart"] == resume["population_arrivee"]
    assert resume["kg_transportes"] == 0.0


# --- test_cli.py ---
def test_run_est_deterministe():
    a = run(ticks=1, seed=DEFAULT_CLI_SEED)
    b = run(ticks=1, seed=DEFAULT_CLI_SEED)
    assert a == b


# --- test_cli.py ---
def test_module_cli_json():
    proc = subprocess.run(
        [sys.executable, "-m", "sim", "--ticks", "0", "--json"],
        cwd=_REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(proc.stdout)
    assert data["sans_unity"] is True
    assert data["ticks"] == 0
    assert data["cellules"] > 0


# --- test_snapshot_v0a.py ---
def test_schema_ferme_et_couches():
    world = World.charger(0)
    doc = build_snapshot_document(world, 0, 0)
    assert set(doc) == _ROOT_KEYS
    assert doc["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert doc["cell_count"] == len(world.cells) == len(doc["cells"])
    assert set(doc["couches"]) == {"relief", "climat", "gisements"}
    for couche in doc["couches"].values():
        assert couche["dans_la_carte"] is True
        assert isinstance(couche["utilisee_par_le_moteur"], bool)
    first = doc["cells"][0]
    assert set(first) == _CELL_KEYS
    assert "province_id" not in first
    assert "elev_mean_m" not in first
    assert first["climat"] is not None


def test_la_consommation_des_couches_est_mesuree_pas_declaree():
    """
    `utilisee_par_le_moteur` doit être une MESURE, pas un booléen écrit à la
    main.

    Il l'était : un triplet `{"relief": False, ...}` dans
    `sim/snapshot_export.py`, et ce test se contentait de figer la valeur
    courante — `assert couche["utilisee_par_le_moteur"] is False`. Il ne
    vérifiait donc rien : un moteur qui aurait commencé à lire le relief, ou
    cessé de lire une couche, aurait continué de déclarer le contraire sans
    qu'aucun contrôle ne rougisse. Mode de défaillance n° 5 du dépôt : un
    compteur dérive des données, ou il n'existe pas.

    Ce test vérifie que la sonde est FALSIFIABLE dans les deux sens, sur les
    deux façons dont un moteur peut consommer une couche :

      * lue à chaque tick — le moteur interroge `world.carte` ;
      * lue au chargement — la valeur est capturée sur la cellule.

    La seconde était l'angle mort de la première version de la sonde, qui
    altérait la carte APRÈS l'amorçage.
    """
    from sim import engine
    from sim.snapshot_export import _couche_consommee

    # 1. Aujourd'hui, le tick ne joue aucune des trois. C'est un constat,
    #    pas une exigence : le jour où le relief entre, il passera à True
    #    tout seul et ce test restera vert.
    mesure = {nom: _couche_consommee(nom) for nom in ("relief", "climat", "gisements")}
    print(f"couches_consommees_par_le_tick = {sum(mesure.values())} / 3 {mesure}")

    # 2. Falsifiabilité : un moteur qui lit le climat à chaque tick doit
    #    faire passer `climat` à True — et lui seul.
    vraie_production = engine.production_kg

    def production_qui_lit_le_climat(cell, yield_factor):
        base = vraie_production(cell, yield_factor)
        return base + getattr(cell, "_sonde_climat", 0.0)

    monde_test = World.charger(0)
    assert monde_test.carte, "la carte doit être chargée pour cette sonde"

    engine.production_kg = production_qui_lit_le_climat
    try:
        # Sans lecture réelle de la couche, rien ne doit bouger.
        # Le climat est désormais consommé ; la sonde pointe
        # vers les gisements, encore inertes.
        assert _couche_consommee("couche_inexistante") is False, (
            "La sonde rend True alors que le moteur ne lit pas la couche : "
            "elle mesure autre chose que la consommation."
        )
    finally:
        engine.production_kg = vraie_production

    # 3. Falsifiabilité, l'autre sens : une couche réellement lue est vue.
    #    On l'obtient en faisant lire `world.carte` par le maillon production.
    def production_qui_lit_le_relief(cell, yield_factor):
        facteurs = {"haute_montagne": 0.1}
        relief = getattr(cell, "_relief_sonde", None)
        return vraie_production(cell, yield_factor) * facteurs.get(relief, 1.0)

    vrai_charger = World.charger

    def charger_en_capturant_le_relief(rng_seed=0, carte_doc=None):
        monde = vrai_charger(rng_seed=rng_seed, carte_doc=carte_doc)
        for cid, cellule in monde.cells.items():
            cellule._relief_sonde = (monde.carte.get(cid) or {}).get("relief")
        return monde

    engine.production_kg = production_qui_lit_le_relief
    World.charger = staticmethod(charger_en_capturant_le_relief)
    try:
        assert _couche_consommee("relief") is True, (
            "Un moteur qui module la production selon le relief n'est pas "
            "détecté : la sonde a un angle mort et le drapeau du snapshot "
            "ne veut rien dire."
        )
    finally:
        engine.production_kg = vraie_production
        World.charger = vrai_charger


# --- test_snapshot_v0a.py ---
def test_province_recalculee_pas_stockee():
    world = World.charger(0)
    doc = build_snapshot_document(world, 0, 0)
    regroupements = agregat_depuis_monde(world)
    for cell in doc["cells"]:
        attendu = identifiant_de_province_de_cellule(cell["cell_id"], regroupements)
        assert cell["province"]["id"] == attendu


# --- test_snapshot_v0a.py ---
def test_deux_passes_identiques_et_graines_differentes():
    world_a = World.charger(0)
    world_b = World.charger(0)
    world_c = World.charger(1)
    a = serialize_snapshot(build_snapshot_document(world_a, 0, 0))
    b = serialize_snapshot(build_snapshot_document(world_b, 0, 0))
    c = serialize_snapshot(build_snapshot_document(world_c, 1, 0))
    assert _sha(a) == _sha(b)
    assert _sha(a) != _sha(c)
    cells_a = json.loads(a)["cells"]
    cells_c = json.loads(c)["cells"]
    assert any(
        left["population"] != right["population"]
        for left, right in zip(cells_a, cells_c)
    )


# --- test_snapshot_v0a.py ---
def test_cli_snapshot_et_refus_schema(tmp_path: Path):
    dest = tmp_path / "nested" / "world.json"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "sim",
            "--ticks",
            "0",
            "--seed",
            "0",
            "--snapshot-json",
            str(dest),
        ],
        cwd=_REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    assert dest.is_file()
    data = json.loads(dest.read_bytes())
    assert data["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert "cells" not in proc.stdout

    broken = json.loads(dest.read_bytes())
    del broken["schema_version"]
    assert "schema_version" not in broken


# --- test_snapshot_v0a.py ---
def test_rouge_sentinelle_et_cle_spatiale():
    world = World.charger(0)
    doc = build_snapshot_document(world, 0, 0)
    raw = serialize_snapshot(doc)
    altered = bytearray(raw)
    altered[len(altered) // 2] ^= 0x01
    assert _sha(bytes(altered)) != _sha(raw)
    cell = doc["cells"][0]
    assert cell["hunger_ticks"] == 0
    assert cell["food_deficit_kg"] == 0.0
    forged = dict(cell)
    forged["hunger_ticks"] = -1
    assert forged["hunger_ticks"] != cell["hunger_ticks"]
    assert "province_id" not in cell
    assert "owner" not in cell


# --- test_snapshot_v0a.py ---
def test_le_relief_est_une_classe_pas_une_altitude():
    """
    Le jeu voit cinq classes de relief, jamais des mètres.
    """
    world = World.charger(0)
    doc = build_snapshot_document(world, 0, 0)
    classes = {"marais", "plaine", "colline", "montagne", "haute_montagne"}
    for cell in doc["cells"]:
        assert cell["relief"] in classes
        assert "elev_mean_m" not in cell
        assert "centroid_elev_m" not in cell


# --- test_snapshot_v0a.py ---
def test_sentinelle_moins_un_n_est_pas_zero():
    world = World.charger(0)
    cell = next(iter(world.cells.values()))
    original = cell.hunger_ticks
    cell.hunger_ticks = -1
    try:
        doc = build_snapshot_document(world, 0, 0)
        exported = next(item for item in doc["cells"] if item["cell_id"] == cell.cell_id)
        assert exported["hunger_ticks"] == -1
        assert exported["hunger_ticks"] != 0
        assert exported["hunger_ticks"] is not None
    finally:
        cell.hunger_ticks = original


# --- test_snapshot_v0a.py ---
def test_zero_mesure_n_est_pas_sentinelle():
    world = World.charger(0)
    doc = build_snapshot_document(world, 0, 0)
    cell = doc["cells"][0]
    assert cell["hunger_ticks"] == 0
    assert cell["hunger_ticks"] != -1



# --- Panier photographié et jour de l'année ---


def test_snapshot_porte_le_panier_du_moteur():
    """Chaque cellule porte stocks ; food_stock_kg absent du document."""
    world = World.charger(0)
    doc = build_snapshot_document(world, 0, 0)
    assert doc["cells"], "document vide"
    for cell_doc, cell in zip(
        sorted(doc["cells"], key=lambda item: int(item["cell_id"])),
        sorted(world.cells.values(), key=lambda cell: cell.cell_id),
    ):
        assert "stocks" in cell_doc
        assert "food_stock_kg" not in cell_doc
        for marchandise, quantite in cell.stocks.items():
            assert cell_doc["stocks"][marchandise] == quantite


def test_jour_de_tick_present_ou_absent():
    """jour_de_tick photographié ou clé absente, jamais inventée."""
    from sim import constants as _constants

    world = World.charger(0)
    tick = 17
    doc = build_snapshot_document(world, 0, tick)
    assert doc["jour_de_tick"] == _constants.jour_de_tick(tick)

    original = _constants.jour_de_tick
    try:
        delattr(_constants, "jour_de_tick")
        sans = build_snapshot_document(world, 0, tick)
        assert "jour_de_tick" not in sans
    finally:
        _constants.jour_de_tick = original

# --- Relief dans le rendement ---


def test_production_kg_modulée_par_le_relief():
    """
    À surface et rendement identiques, chaque classe de relief de la
    carte applique son facteur nominal via l'unique formule production_kg().
    """
    from sim import constants as _k
    from sim import engine

    carte = World.lire_carte()
    par_classe: dict[str, int] = {}
    for raw in carte["cellules"]:
        relief = raw.get("relief")
        if relief and relief not in par_classe:
            par_classe[relief] = int(raw["cell_id"])

    assert par_classe, "échantillon vide : aucune classe de relief mesurée"

    attendus = {
        "plaine": _k.FACTEUR_RELIEF_PLAINE,
        "colline": _k.FACTEUR_RELIEF_COLLINE,
        "montagne": _k.FACTEUR_RELIEF_MONTAGNE,
        "haute_montagne": _k.FACTEUR_RELIEF_HAUTE_MONTAGNE,
        "marais": _k.FACTEUR_RELIEF_MARAIS,
    }
    assert set(par_classe) == set(attendus)

    world = World.charger(0)
    surface_commune = 10.0
    rendement = 1.0
    productions = {}
    for cls, cid in sorted(par_classe.items()):
        cell = world.cells[cid]
        cell.area_km2 = surface_commune
        engine._carte_du_tick = world.carte
        try:
            productions[cls] = engine.production_kg(cell, rendement)
        finally:
            engine._carte_du_tick = None

    ref_plaine = productions["plaine"]
    for cls, facteur in attendus.items():
        ratio = productions[cls] / ref_plaine
        print(f"{cls}: production={productions[cls]} ratio={ratio} facteur={facteur}")
        assert ratio == facteur / attendus["plaine"], (
            f"classe {cls}: ratio {ratio} != facteur nominal {facteur}"
        )


def test_tick_refuse_relief_inconnu():
    """Le tick refuse une classe de relief absente de l'ensemble dérivé."""
    import random

    from sim.engine import ReliefInvalideError, tick

    world = World.charger(0)
    cid = next(iter(world.cells))
    entree = dict(world.carte[cid])
    entree["relief"] = "relief_inconnu_033"
    world.carte[cid] = entree

    with pytest.raises(ReliefInvalideError, match=f"cell_id={cid}") as exc:
        tick(world, random.Random(0))
    assert "relief_inconnu_033" in str(exc.value)


def test_tick_refuse_relief_absent():
    """Une classe manquante dans world.carte est refusée explicitement."""
    import random

    from sim.engine import ReliefInvalideError, tick

    world = World.charger(0)
    cid = next(iter(world.cells))
    entree = dict(world.carte[cid])
    del entree["relief"]
    world.carte[cid] = entree

    with pytest.raises(ReliefInvalideError, match=f"cell_id={cid}") as exc:
        tick(world, random.Random(0))
    assert "relief=None" in str(exc.value)


# --- Le moteur ne garde pas la carte dans un état de module ---


def test_aucune_instruction_global_dans_le_moteur():
    """Aucune fonction de sim/engine.py ne déclare global."""
    import ast

    engine_path = pathlib.Path(__file__).resolve().parents[1] / "engine.py"
    source = engine_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    fonctions: list[str] = []
    fautives: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            fonctions.append(node.name)
            for child in ast.walk(node):
                if isinstance(child, ast.Global):
                    fautives.append(node.name)

    n_fonctions = len(fonctions)
    n_global = len(set(fautives))
    print(f"fonctions_moteur_inspectees={n_fonctions}")
    print(f"fonctions_avec_global={n_global}")
    if fautives:
        print(f"fonctions_fautives={sorted(set(fautives))}")

    assert fonctions, "module sans fonction : échantillon insuffisant"
    assert not fautives, (
        f"instructions global interdites dans : {sorted(set(fautives))}"
    )


def _cartes_par_classe_relief_pour_cellule(carte_originale: dict, cell_id: int) -> dict[str, dict]:
    """Une carte en mémoire par classe de relief présente dans la carte figée."""
    classes: dict[str, int] = {}
    for raw in carte_originale.values():
        relief = raw.get("relief")
        if relief and relief not in classes:
            classes[relief] = cell_id
    assert len(classes) >= 2, "échantillon insuffisant : moins de deux classes de relief"
    cartes: dict[str, dict] = {}
    for cls in sorted(classes):
        carte_x = {cid: dict(entree) for cid, entree in carte_originale.items()}
        entree = dict(carte_x[cell_id])
        entree["relief"] = cls
        carte_x[cell_id] = entree
        cartes[cls] = carte_x
    return cartes


def test_production_du_tick_kg_modulée_par_le_relief():
    """Seule la carte change ; le rapport suit les facteurs nominaux."""
    from sim import constants as _k
    from sim.engine import production_du_tick_kg

    world = World.charger(0)
    cell_id = next(iter(world.cells))
    cell = world.cells[cell_id]
    surface_commune = 10.0
    rendement = 1.0
    cell.area_km2 = surface_commune

    cartes = _cartes_par_classe_relief_pour_cellule(world.carte, cell_id)
    facteurs = _k.facteurs_production_par_relief()
    ref_cls = "plaine"
    assert ref_cls in cartes

    productions: dict[str, float] = {}
    appels = 0
    for cls, carte_x in sorted(cartes.items()):
        productions[cls] = production_du_tick_kg(cell, rendement, carte_x)
        appels += 1

    ref_prod = productions[ref_cls]
    ratios_ok = 0
    for cls in sorted(cartes):
        if cls == ref_cls:
            continue
        ratio = productions[cls] / ref_prod
        attendu = facteurs[cls] / facteurs[ref_cls]
        assert ratio == attendu, (
            f"classe {cls}: ratio {ratio} != facteur nominal {attendu}"
        )
        ratios_ok += 1

    print(f"cartes_comparees_sc2={len(cartes)}")
    print(f"appels_production_du_tick={appels}")
    print(f"ratios_conformes_au_facteur_nominal={ratios_ok}")


def test_production_du_tick_kg_appels_consecutifs_identiques():
    """Mêmes arguments, même flottant ; aucun état de module posé."""
    from sim import engine
    from sim.engine import production_du_tick_kg

    world = World.charger(0)
    cell_id = next(iter(world.cells))
    cell = world.cells[cell_id]
    rendement = 1.0
    cartes = _cartes_par_classe_relief_pour_cellule(world.carte, cell_id)

    appels_repetes_stables = 0
    for carte_x in cartes.values():
        assert engine._carte_du_tick is None
        premier = production_du_tick_kg(cell, rendement, carte_x)
        assert engine._carte_du_tick is None
        second = production_du_tick_kg(cell, rendement, carte_x)
        assert premier == second
        appels_repetes_stables += 1

    assert engine._carte_du_tick is None
    print(f"appels_repetes_stables={appels_repetes_stables}")


def test_tick_ne_pose_pas_carte_dans_le_module():
    """Pendant un tick réel, _carte_du_tick reste None à chaque lecture."""
    import random

    from sim import engine
    from sim.engine import tick

    class CarteInstrumentee(dict):
        def __init__(self, data: dict) -> None:
            super().__init__(data)
            self.lectures: list[object] = []

        def get(self, key, default=None):
            self.lectures.append(engine._carte_du_tick)
            return super().get(key, default)

        def __getitem__(self, key):
            self.lectures.append(engine._carte_du_tick)
            return super().__getitem__(key)

    world = World.charger(0)
    world.carte = CarteInstrumentee(dict(world.carte))
    tick(world, random.Random(0))

    lectures = len(world.carte.lectures)
    non_none = sum(1 for valeur in world.carte.lectures if valeur is not None)
    print(f"lectures_de_carte_pendant_le_tick={lectures}")
    print(f"lectures_voyant_un_etat_de_module={non_none}")

    assert lectures > 0, "zéro lecture : absence de mesure"
    assert non_none == 0, (
        f"{non_none} lectures ont vu un état de module au lieu de None"
    )

# --- Saison dans le rendement ---


def _cellules_par_amplitude_jour(carte: dict) -> tuple[int, int]:
    """Cellules de plus grande et plus petite amplitude, dérivées de la carte."""
    amplitudes: list[tuple[float, int]] = []
    for raw in carte["cellules"]:
        climat = raw.get("climat")
        if not isinstance(climat, dict):
            continue
        ete = climat.get("duree_jour_solstice_ete_h")
        hiver = climat.get("duree_jour_solstice_hiver_h")
        if isinstance(ete, (int, float)) and isinstance(hiver, (int, float)):
            if not isinstance(ete, bool) and not isinstance(hiver, bool):
                amplitudes.append((abs(float(ete) - float(hiver)), int(raw["cell_id"])))
    assert amplitudes, "échantillon vide : aucune cellule avec deux solstices"
    amplitudes.sort()
    return amplitudes[-1][1], amplitudes[0][1]


def test_production_ete_differe_de_hiver_sur_amplitude_max():
    """À surface et rendement identiques, été ≠ hiver sur l'amplitude max."""
    from sim import constants as _k
    from sim.engine import production_du_tick_kg

    carte = World.lire_carte()
    cid_max, _ = _cellules_par_amplitude_jour(carte)
    world = World.charger(0)
    cell = world.cells[cid_max]
    cell.area_km2 = 10.0
    rendement = 1.0
    jour_ete = _k.jour_solstice_ete()
    jour_hiver = _k.jour_solstice_hiver()
    prod_ete = production_du_tick_kg(cell, rendement, world.carte, jour=jour_ete)
    prod_hiver = production_du_tick_kg(cell, rendement, world.carte, jour=jour_hiver)
    ecart = abs(prod_ete - prod_hiver)
    print(f"cellule_amplitude_max={cid_max} prod_ete={prod_ete} prod_hiver={prod_hiver}")
    print(f"ecart_ete_hiver_apres={ecart}")
    assert prod_ete != prod_hiver, (
        "La production d'été et d'hiver sont identiques sur la cellule d'amplitude max."
    )


def test_le_nord_a_une_saison_plus_violente_que_le_sud():
    """Le rapport été/hiver est plus grand au nord qu'au sud."""
    from sim import constants as _k
    from sim.engine import production_du_tick_kg

    carte = World.lire_carte()
    cid_max, cid_min = _cellules_par_amplitude_jour(carte)
    world = World.charger(0)
    rendement = 1.0
    jour_ete = _k.jour_solstice_ete()
    jour_hiver = _k.jour_solstice_hiver()

    def rapport(cid: int) -> float:
        cell = world.cells[cid]
        cell.area_km2 = 10.0
        ete = production_du_tick_kg(cell, rendement, world.carte, jour=jour_ete)
        hiver = production_du_tick_kg(cell, rendement, world.carte, jour=jour_hiver)
        assert hiver > 0.0, "production hiver nulle : dénominateur invalide"
        return ete / hiver

    ratio_nord = rapport(cid_max)
    ratio_sud = rapport(cid_min)
    print(f"rapport_ete_hiver_nord={ratio_nord} rapport_ete_hiver_sud={ratio_sud}")
    assert ratio_nord > ratio_sud, (
        f"Le nord ({ratio_nord}) n'a pas une saison plus violente que le sud ({ratio_sud})."
    )


def test_plafond_survie_coherent_avec_facteur_saison_moyen():
    """production_moyenne_kg_par_tick emploie le facteur saisonnier moyen."""
    from sim import constants as _k
    from sim.engine import (
        _lire_solstices,
        _production_du_tick_kg_saison_moyenne,
        production_moyenne_kg_par_tick,
    )

    world = World.charger(0)
    rendement = _k.rendement_moyen_courant()
    attendu = sum(
        _production_du_tick_kg_saison_moyenne(cell, rendement, world.carte)
        for cell in world.cells.values()
    )
    plafond = production_moyenne_kg_par_tick(world)
    print(f"plafond={plafond} attendu={attendu}")
    assert plafond == attendu

    carte = World.lire_carte()
    cid_max, _ = _cellules_par_amplitude_jour(carte)
    ete_h, hiver_h = _lire_solstices(world.cells[cid_max], world.carte)
    moyenne_calculee = _k.facteur_saison_moyen_annuel(ete_h, hiver_h)
    facteur_ete = _k.facteur_saison(
        _k.duree_jour_h(_k.jour_solstice_ete(), ete_h, hiver_h)
    )
    assert facteur_ete != moyenne_calculee, (
        "Le facteur d'été coïncide avec la moyenne annuelle : le plafond pourrait "
        "se contenter de la valeur 1 sans sommer les jours."
    )
    annee = _k.CALENDAR_DAYS_PER_YEAR
    recomputee = sum(
        _k.facteur_saison(_k.duree_jour_h(j, ete_h, hiver_h))
        for j in range(annee)
    ) / annee
    assert abs(moyenne_calculee - recomputee) < 1e-9


def test_somme_annuelle_saisonniere_egale_somme_au_facteur_moyen():
    """Sur une année, la saison redistribue sans créer ni détruire."""
    from sim import constants as _k
    from sim.engine import (
        _production_du_tick_kg_saison_moyenne,
        production_du_tick_kg,
    )

    world = World.charger(0)
    cid = next(iter(world.cells))
    cell = world.cells[cid]
    cell.area_km2 = 10.0
    rendement = 1.0
    annee = _k.CALENDAR_DAYS_PER_YEAR
    somme_saisonniere = 0.0
    for numero_tick in range(annee):
        jour = _k.jour_de_tick(numero_tick)
        somme_saisonniere += production_du_tick_kg(
            cell, rendement, world.carte, jour=jour
        )
    somme_moyenne = (
        _production_du_tick_kg_saison_moyenne(cell, rendement, world.carte) * annee
    )
    ecart = abs(somme_saisonniere - somme_moyenne)
    print(f"somme_saisonniere={somme_saisonniere} somme_moyenne={somme_moyenne}")
    print(f"ecart_relatif_somme_annuelle={ecart}")
    assert ecart < 1e-6 * max(somme_saisonniere, somme_moyenne, 1.0)


@pytest.mark.parametrize(
    "mutation, cle_attendue",
    [
        ("retirer_climat", "climat"),
        ("ete_invalide", "duree_jour_solstice_ete_h"),
        ("hiver_invalide", "duree_jour_solstice_hiver_h"),
    ],
)
def test_tick_refuse_climat_incomplet(mutation: str, cle_attendue: str):
    """Climat absent ou solstice non numérique : erreur nommée."""
    import random

    from sim.engine import ClimatInvalideError, tick

    world = World.charger(0)
    cid = next(iter(world.cells))
    entree = dict(world.carte[cid])
    if mutation == "retirer_climat":
        entree.pop("climat", None)
    elif mutation == "ete_invalide":
        climat = dict(entree.get("climat") or {})
        climat["duree_jour_solstice_ete_h"] = "invalide"
        entree["climat"] = climat
    else:
        climat = dict(entree.get("climat") or {})
        climat["duree_jour_solstice_hiver_h"] = None
        entree["climat"] = climat
    world.carte[cid] = entree

    with pytest.raises(ClimatInvalideError, match=f"cell_id={cid}") as exc:
        tick(world, random.Random(0), numero_tick=0)
    assert cle_attendue in str(exc.value)

# --- Panier de marchandises ---


def test_sentinelle_panier_absent_vs_zero():
    """Absent → -1.0 ; présent à zéro → 0.0 ; les deux ne se confondent pas."""
    from sim.constants import MARCHANDISE_NOURRITURE
    from sim.model import Cell, ecrire_stock_marchandise, lire_stock_marchandise

    vide = Cell(cell_id=1, area_km2=1.0, population=1)
    assert lire_stock_marchandise(vide, MARCHANDISE_NOURRITURE) == -1.0

    a_zero = Cell(cell_id=2, area_km2=1.0, population=1)
    ecrire_stock_marchandise(a_zero, MARCHANDISE_NOURRITURE, 0.0)
    assert lire_stock_marchandise(a_zero, MARCHANDISE_NOURRITURE) == 0.0

    assert -1.0 != 0.0


def test_acces_directs_au_panier_hors_modele():
    """Aucun module de sim/ hors model.py n'indexe stocks directement."""
    import ast
    import pathlib

    sim_dir = pathlib.Path(__file__).parent.parent
    modules_parcourus = 0
    acces_directs = 0
    for fichier in sorted(sim_dir.rglob("*.py")):
        rel = fichier.relative_to(sim_dir)
        if "tests" in rel.parts or rel.name == "model.py":
            continue
        modules_parcourus += 1
        tree = ast.parse(fichier.read_text(encoding="utf-8"), filename=str(fichier))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "stocks":
                acces_directs += 1
            elif isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute):
                if node.value.attr == "stocks":
                    acces_directs += 1
    assert modules_parcourus > 0
    assert acces_directs == 0, (
        f"acces_directs_au_panier_hors_modele={acces_directs} ; "
        f"modules_sim_parcourus={modules_parcourus}"
    )


# Marchandise d'épreuve : elle n'existe que pour ce test, qui prouve que le
# panier tient plus d'une entrée. Elle n'a rien à faire dans le moteur.
MARCHANDISE_EPREUVE = "__sonde_panier__"


def test_panier_deuxieme_marchandise_et_to_dict():
    """Une deuxième marchandise tient dans le panier, et World.to_dict() l'expose."""
    from sim.constants import MARCHANDISE_NOURRITURE
    from sim.model import Cell, ecrire_stock_marchandise, lire_stock_marchandise
    from sim.world import World

    cell = Cell(cell_id=99, area_km2=1.0, population=10, food_stock_kg=100.0)
    assert lire_stock_marchandise(cell, MARCHANDISE_NOURRITURE) == 100.0
    ecrire_stock_marchandise(cell, MARCHANDISE_EPREUVE, 42.0)
    assert lire_stock_marchandise(cell, MARCHANDISE_EPREUVE) == 42.0
    assert lire_stock_marchandise(cell, MARCHANDISE_NOURRITURE) == 100.0

    world = World(cells={99: cell}, adjacency=[])
    doc = world.to_dict()
    assert doc["cells"]["99"]["stocks"][MARCHANDISE_EPREUVE] == 42.0

    monde_charge = World.charger(0)
    cellules_avec_panier = sum(
        1 for entree in monde_charge.to_dict()["cells"].values() if "stocks" in entree
    )
    assert cellules_avec_panier == len(monde_charge.cells)


# --- Extraction minière ---


def _agreger_gisements_carte(carte_doc: dict) -> tuple[int, set[str], set[str]]:
    """Cellules porteuses, ressources et classes de richesse dérivées de la carte."""
    cellules = 0
    ressources: set[str] = set()
    classes: set[str] = set()
    for raw in carte_doc["cellules"]:
        gisements = raw.get("gisements") or []
        complets = [
            g for g in gisements
            if isinstance(g, dict) and g.get("ressource") is not None and g.get("richesse") is not None
        ]
        if complets:
            cellules += 1
            for g in complets:
                ressources.add(g["ressource"])
                classes.add(g["richesse"])
    return cellules, ressources, classes


def _ressources_minieres_panier(world) -> tuple[int, set[str]]:
    """Cellules avec minerai et ensemble des ressources extraites."""
    from sim.constants import MARCHANDISE_NOURRITURE

    cellules = 0
    ressources: set[str] = set()
    for cell in world.cells.values():
        mineraux = {k for k in cell.stocks if k != MARCHANDISE_NOURRITURE}
        if mineraux:
            cellules += 1
            ressources |= mineraux
    return cellules, ressources


def test_chaque_gisement_produit_sa_ressource():
    """Panier minière aligné sur la carte après un tick."""
    import random

    from sim.engine import tick

    carte = World.lire_carte()
    attendu_cellules, attendu_ressources, _ = _agreger_gisements_carte(carte)
    assert attendu_cellules > 0, "échantillon vide : aucune cellule avec gisement"

    world = World.charger(0)
    tick(world, random.Random(0), numero_tick=0)
    mesure_cellules, mesure_ressources = _ressources_minieres_panier(world)

    print(
        f"cellules_extractrices={mesure_cellules} / carte={attendu_cellules} "
        f"ressources={sorted(mesure_ressources)}"
    )
    assert mesure_cellules == attendu_cellules
    assert mesure_ressources == attendu_ressources


def test_richesse_ordre_les_debits():
    """majeure > notable > mineure à population et ressource égales."""
    import copy
    import random

    from sim import constants as _k
    from sim.engine import _extraction_du_tick_kg, tick

    carte = World.lire_carte()
    _, _, classes_carte = _agreger_gisements_carte(carte)
    attendues = set(_k.facteurs_richesse_extraction())
    assert classes_carte == attendues, (
        f"classes carte {classes_carte} != classes dérivées {attendues}"
    )

    par_classe: dict[str, float] = {}
    population = 1000
    for raw in carte["cellules"]:
        for g in raw.get("gisements") or []:
            if not isinstance(g, dict):
                continue
            richesse = g.get("richesse")
            if richesse in attendues and richesse not in par_classe:
                cid = int(raw["cell_id"])
                monde = World.charger(0)
                cell = monde.cells[cid]
                cell.population = population
                par_classe[richesse] = _extraction_du_tick_kg(cell, monde.carte).get(
                    g["ressource"], 0.0
                )
    assert set(par_classe) == attendues, f"classes manquantes dans l'échantillon : {par_classe}"

    majeure = par_classe["majeure"]
    notable = par_classe["notable"]
    mineure = par_classe["mineure"]
    print(f"debits majeure={majeure} notable={notable} mineure={mineure}")
    assert majeure > notable > mineure


def test_sans_bras_pas_de_minerai():
    """Population nulle : extraction mesurée à 0.0, pas la sentinelle -1."""
    import random

    from sim.engine import _extraction_du_tick_kg, tick

    carte = World.lire_carte()
    cid = next(
        int(raw["cell_id"])
        for raw in carte["cellules"]
        if any(
            isinstance(g, dict) and g.get("ressource") and g.get("richesse")
            for g in (raw.get("gisements") or [])
        )
    )
    world = World.charger(0)
    cell = world.cells[cid]
    cell.population = 0
    ressource = next(
        g["ressource"]
        for g in world.carte[cid]["gisements"]
        if isinstance(g, dict) and g.get("ressource") and g.get("richesse")
    )
    tick(world, random.Random(0))
    extrait = _extraction_du_tick_kg(cell, world.carte).get(ressource, 0.0)
    stock = cell.stocks.get(ressource, -1.0)
    print(f"extraction_population_nulle={extrait} stock={stock}")
    assert extrait == 0.0
    assert stock == 0.0
    assert stock != -1.0


def test_richesse_inconnue_refusee():
    """Richesse hors des trois classes : erreur nommée."""
    import random

    from sim.engine import RichesseGisementInvalideError, tick

    world = World.charger(0)
    cid = next(
        int(raw["cell_id"])
        for raw in world.carte.values()
        if isinstance(raw, dict) and raw.get("gisements")
    )
    entree = dict(world.carte[cid])
    gisements = [dict(g) for g in entree["gisements"]]
    gisements[0]["richesse"] = "inconnue"
    entree["gisements"] = gisements
    world.carte[cid] = entree
    gid = gisements[0].get("id", gisements[0].get("nom", "?"))

    with pytest.raises(RichesseGisementInvalideError) as exc:
        tick(world, random.Random(0), numero_tick=0)
    msg = str(exc.value)
    assert f"cell_id={cid}" in msg
    assert str(gid) in msg or repr(gid).strip("'") in msg
    assert "inconnue" in msg


def test_gisement_incomplet_ignore():
    """Sans ressource ou richesse : ignoré, les autres extraient."""
    import random

    from sim.constants import MARCHANDISE_NOURRITURE
    from sim.engine import tick

    world = World.charger(0)
    cid = next(
        int(raw["cell_id"])
        for raw in World.lire_carte()["cellules"]
        if len([
            g for g in (raw.get("gisements") or [])
            if isinstance(g, dict) and g.get("ressource") and g.get("richesse")
        ]) >= 2
    )
    entree = dict(world.carte[cid])
    gisements = [dict(g) for g in entree["gisements"]]
    complet = next(g for g in gisements if g.get("ressource") and g.get("richesse"))
    ressource_attendue = complet["ressource"]
    incomplet = dict(complet)
    incomplet.pop("ressource", None)
    entree["gisements"] = [incomplet, complet]
    world.carte[cid] = entree

    tick(world, random.Random(0), numero_tick=0)
    assert ressource_attendue in world.cells[cid].stocks
    assert world.cells[cid].stocks[ressource_attendue] > 0.0


def test_ressource_inconnue_acceptee():
    """Ressource inédite : acceptée dans le panier."""
    import random

    from sim.engine import tick

    world = World.charger(0)
    cid = next(iter(world.cells))
    entree = dict(world.carte[cid])
    entree["gisements"] = [{
        "id": "sonde-ressource",
        "ressource": "mythrite",
        "richesse": "notable",
    }]
    world.carte[cid] = entree
    world.cells[cid].population = 100

    tick(world, random.Random(0), numero_tick=0)
    assert "mythrite" in world.cells[cid].stocks
    assert world.cells[cid].stocks["mythrite"] > 0.0


# --- Un métier : le mineur ---


def _gisements_complets(raw: dict) -> list:
    """Enregistrements de gisement avec ressource et richesse."""
    return [
        g
        for g in (raw.get("gisements") or [])
        if isinstance(g, dict) and g.get("ressource") is not None and g.get("richesse") is not None
    ]


def _porteuses_de_la_carte(carte_doc: dict) -> set[int]:
    """Cellules que la carte déclare porteuses d'au moins un gisement complet."""
    return {
        int(raw["cell_id"])
        for raw in carte_doc["cellules"]
        if _gisements_complets(raw)
    }


def _paire_meme_relief_porteuse_et_non(carte_doc: dict) -> tuple[int, int, str]:
    """
    Une porteuse et une non-porteuse de même classe de relief, dérivées
    de la carte. Échoue si aucune paire n'existe.
    """
    par_relief: dict[str, dict[str, int | None]] = {}
    for raw in carte_doc["cellules"]:
        relief = raw.get("relief")
        if not relief:
            continue
        seau = par_relief.setdefault(relief, {"avec": None, "sans": None})
        cid = int(raw["cell_id"])
        if _gisements_complets(raw):
            if seau["avec"] is None:
                seau["avec"] = cid
        else:
            if seau["sans"] is None:
                seau["sans"] = cid
        if seau["avec"] is not None and seau["sans"] is not None:
            return int(seau["avec"]), int(seau["sans"]), relief
    pytest.fail(
        "échantillon vide : aucune paire porteuse/non-porteuse de même relief"
    )


def _carte_sans_gisements(carte: dict) -> dict:
    """Copie en mémoire : listes de gisements vidées, rien d'autre changé."""
    copie = {}
    for cid, raw in carte.items():
        entree = dict(raw)
        entree["gisements"] = []
        copie[cid] = entree
    return copie


def test_cellule_a_gisement_cultive_moins():
    """
    SC1 — À surface, relief, date et rendement identiques, une porteuse
    produit strictement moins qu'une non-porteuse de même classe de relief.
    """
    from sim import constants as _k
    from sim.engine import production_du_tick_kg

    carte_doc = World.lire_carte()
    cid_avec, cid_sans, relief = _paire_meme_relief_porteuse_et_non(carte_doc)
    world = World.charger(0)
    surface = world.cells[cid_sans].area_km2
    world.cells[cid_avec].area_km2 = surface
    rendement = _k.rendement_moyen_courant()
    jour = _k.jour_de_tick(0)

    carte = {cid: dict(raw) for cid, raw in world.carte.items()}
    climat_ref = carte[cid_avec].get("climat")
    carte[cid_sans] = dict(carte[cid_sans])
    carte[cid_sans]["climat"] = climat_ref

    prod_avec = production_du_tick_kg(
        world.cells[cid_avec], rendement, carte, jour=jour
    )
    prod_sans = production_du_tick_kg(
        world.cells[cid_sans], rendement, carte, jour=jour
    )
    print(
        f"relief={relief} cid_avec={cid_avec} cid_sans={cid_sans} "
        f"prod_avec={prod_avec} prod_sans={prod_sans}"
    )
    assert prod_avec < prod_sans, (
        "Une cellule à gisement ne cultive pas moins qu'une non-porteuse "
        f"de même relief : {prod_avec} >= {prod_sans}."
    )


def test_baisse_ne_touche_que_les_porteuses():
    """
    SC2 — Au premier tick, le stock de nourriture ne diffère que sur les
    cellules que la carte déclare porteuses. L'autre monde a les gisements
    vidés, rien d'autre.
    """
    import random

    from sim.constants import MARCHANDISE_NOURRITURE
    from sim.engine import tick
    from sim.model import lire_stock_marchandise

    carte_doc = World.lire_carte()
    porteuses = _porteuses_de_la_carte(carte_doc)
    assert porteuses, "échantillon vide : aucune cellule porteuse sur la carte"

    monde = World.charger(0)
    temoin = World.charger(0)
    temoin.carte = _carte_sans_gisements(temoin.carte)

    tick(monde, random.Random(0), numero_tick=0)
    tick(temoin, random.Random(0), numero_tick=0)

    differentes = {
        cid
        for cid in monde.cells
        if lire_stock_marchandise(monde.cells[cid], MARCHANDISE_NOURRITURE)
        != lire_stock_marchandise(temoin.cells[cid], MARCHANDISE_NOURRITURE)
    }
    print(
        f"porteuses={len(porteuses)} differentes={len(differentes)} "
        f"hors_porteuses={sorted(differentes - porteuses)[:8]}"
    )
    assert differentes == porteuses, (
        "L'ensemble qui change n'est pas exactement celui des porteuses : "
        f"en trop={differentes - porteuses} manquantes={porteuses - differentes}."
    )


def test_richesse_ordonne_la_part_miniere():
    """
    SC3 — À un gisement unique, la part minière suit l'ordre des richesses
    dérivé de la carte : majeure > notable > mineure.
    """
    from sim import constants as _k

    carte_doc = World.lire_carte()
    facteurs = _k.facteurs_richesse_extraction()
    par_classe: dict[str, list] = {}
    for raw in carte_doc["cellules"]:
        complets = _gisements_complets(raw)
        if len(complets) != 1:
            continue
        richesse = complets[0]["richesse"]
        if richesse in facteurs and richesse not in par_classe:
            par_classe[richesse] = complets
    assert set(par_classe) == set(facteurs), (
        f"classe manquante dans l'échantillon : {set(facteurs) - set(par_classe)}"
    )

    parts = {
        richesse: _k.part_miniere_de(gisements, facteurs)
        for richesse, gisements in par_classe.items()
    }
    print(
        f"part_majeure={parts['majeure']} part_notable={parts['notable']} "
        f"part_mineure={parts['mineure']}"
    )
    assert parts["majeure"] > parts["notable"] > parts["mineure"]


def test_plafond_part_miniere():
    """
    SC4 — Assez de gisements majeurs pour dépasser le plafond : la part
    vaut exactement le plafond, et la cellule continue de produire.
    """
    from sim import constants as _k
    from sim.engine import production_du_tick_kg

    facteurs = _k.facteurs_richesse_extraction()
    contrib = _k.PART_MINIERE_PAR_GISEMENT * facteurs["majeure"]
    assert contrib > 0.0, "contribution nulle : le plafond ne peut pas se dériver"
    n_gisements = 0
    acc = 0.0
    plafond = _k.PART_MINIERE_MAXIMALE
    while acc <= plafond:
        n_gisements += 1
        acc += contrib
    gisements = [
        {"ressource": "fer", "richesse": "majeure"} for _ in range(n_gisements)
    ]
    part = _k.part_miniere_de(gisements, facteurs)
    print(f"n_gisements={n_gisements} part={part} plafond={plafond}")
    assert part == plafond

    world = World.charger(0)
    cid = next(iter(world.cells))
    entree = dict(world.carte[cid])
    entree["gisements"] = gisements
    world.carte[cid] = entree
    prod = production_du_tick_kg(
        world.cells[cid], _k.rendement_moyen_courant(), world.carte, jour=0
    )
    print(f"production_sous_plafond={prod}")
    assert prod > 0.0


import ast


def _modules_sim_hors_tests() -> list[pathlib.Path]:
    """Modules de sim/ hors tests ; le dénominateur se dérive du répertoire."""
    sim_dir = pathlib.Path(__file__).parent.parent
    return sorted(
        p
        for p in sim_dir.rglob("*.py")
        if "tests" not in p.relative_to(sim_dir).parts
    )


_REF_MASTER: list[str] = []


def _ref_master() -> str:
    """
    Réf git de master, fetchée si le clone ne la porte pas (CI à profondeur 1).
    """
    if _REF_MASTER:
        return _REF_MASTER[0]
    for ref in ("origin/master", "master"):
        probe = subprocess.run(
            ["git", "rev-parse", "--verify", ref],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
        )
        if probe.returncode == 0:
            _REF_MASTER.append(ref)
            return ref
    fetched = subprocess.run(
        ["git", "fetch", "--depth=1", "origin", "master:refs/remotes/origin/master"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert fetched.returncode == 0, (
        "impossible de rejouer master : "
        f"git fetch origin master a échoué ({fetched.stderr.strip()})"
    )
    _REF_MASTER.append("origin/master")
    return _REF_MASTER[0]


def _texte_master(relatif: str) -> str:
    """Source d'un fichier sur master, rejouée, jamais recopiée."""
    ref = _ref_master()
    proc = subprocess.run(
        ["git", "show", f"{ref}:{relatif}"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        f"master ne porte pas {relatif!r} ({proc.stderr.strip()})"
    )
    return proc.stdout


# La révision de `master` juste avant l'arrivée du lot 051 : le premier
# parent du commit de fusion de la PR 22.
#
# Les trois contrôles de 051 mesurent l'écart que ce lot a introduit dans
# le snapshot. Tant qu'ils lisaient `master` à chaud, sa fusion a mis cet
# écart dans leur propre référence, et ils se sont mis à rougir parce que
# le lot avait réussi. Un contrôle qui ne survit pas au geste qu'il mesure
# ne mesure rien : la référence est donc épinglée ici, et ils redeviennent
# des contrôles qui peuvent rougir pour la bonne raison.
#
# `_ref_master` reste à chaud, pour l'invariant qui doit suivre la branche :
# le second jeu de facteurs de richesse.
REVISION_AVANT_051 = "d7ef7aea96cc470f21c910f3e80c644509e5ef0d"

_REF_AVANT_051: list[str] = []


def _ref_avant_051() -> str:
    """La révision d'avant 051, fetchée si le clone ne la porte pas."""
    if _REF_AVANT_051:
        return _REF_AVANT_051[0]
    probe = subprocess.run(
        ["git", "rev-parse", "--verify", REVISION_AVANT_051 + "^{commit}"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if probe.returncode != 0:
        fetched = subprocess.run(
            ["git", "fetch", "--depth=1", "origin", REVISION_AVANT_051],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert fetched.returncode == 0, (
            "impossible de rejouer la révision d'avant 051 : "
            f"git fetch origin {REVISION_AVANT_051[:7]} a échoué "
            f"({fetched.stderr.strip()})"
        )
    _REF_AVANT_051.append(REVISION_AVANT_051)
    return _REF_AVANT_051[0]


def _texte_avant_051(relatif: str) -> str:
    """Source d'un fichier avant 051, rejouée, jamais recopiée."""
    ref = _ref_avant_051()
    proc = subprocess.run(
        ["git", "show", f"{ref}:{relatif}"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        f"la révision d'avant 051 ne porte pas {relatif!r} ({proc.stderr.strip()})"
    )
    return proc.stdout


def _noms_lus_dans(node: ast.AST) -> set[str]:
    lus: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Attribute) and not isinstance(child.ctx, ast.Store):
            lus.add(child.attr)
        elif isinstance(child, ast.Name) and not isinstance(child.ctx, ast.Store):
            lus.add(child.id)
    return lus


def _fonctions_qui_lisent(source: str, filename: str, noms: set[str]) -> set[str]:
    arbre = ast.parse(source, filename=filename)
    trouvees: set[str] = set()
    for node in ast.walk(arbre):
        if isinstance(node, ast.FunctionDef) and _noms_lus_dans(node) & noms:
            trouvees.add(f"{pathlib.Path(filename).name}:{node.name}")
    return trouvees


def _jeux_indexes_par(source: str, classes: set[str]) -> int:
    """Nombre de dictionnaires dont les clés couvrent les classes données."""
    if not classes:
        return 0
    arbre = ast.parse(source)
    n = 0
    for node in ast.walk(arbre):
        if not isinstance(node, ast.Dict):
            continue
        cles = {
            k.value
            for k in node.keys
            if isinstance(k, ast.Constant) and isinstance(k.value, str)
        }
        if classes <= cles:
            n += 1
    return n


def _constantes_relief_table() -> set[str]:
    """Noms des constantes qui composent la table des facteurs de relief."""
    from sim import constants as _k

    return {
        nom
        for nom in dir(_k)
        if nom.startswith("FACTEUR_RELIEF_") and nom.isupper()
    }


def test_une_seule_definition_part_miniere():
    """
    SC5 — Deux références dérivées : la part minière se calcule autant de
    fois que le motif relief ; les jeux de richesse restent ceux de master.

    Le nombre de formules de production est encore compté et affiché, mais
    plus comparé : sa référence était master, qui porte la duplication
    qu'elle devait interdire. Deux égale deux, et le contrôle restait vert
    sur une propriété fausse. Le brief 044 en demande une qui sait rougir.
    """
    modules = _modules_sim_hors_tests()
    n_modules = len(modules)
    print(f"modules_parcourus={n_modules}")
    assert n_modules > 0, "échantillon vide : aucun module de sim/ hors tests"

    noms_part = {"PART_MINIERE_PAR_GISEMENT", "PART_MINIERE_MAXIMALE"}
    noms_relief = _constantes_relief_table()
    assert noms_relief, "référence vide : aucune constante de table de relief"
    nom_production = "FOOD_PRODUCTION_KG_PER_KM2_PER_TICK"

    _, _, classes_carte = _agreger_gisements_carte(World.lire_carte())
    assert classes_carte, "échantillon vide : aucune classe de richesse sur la carte"

    lecteurs_part: set[str] = set()
    lecteurs_relief: set[str] = set()
    formules_ici = 0
    jeux_ici = 0
    jeux_master = 0

    sim_dir = pathlib.Path(__file__).parent.parent
    for fichier in modules:
        source = fichier.read_text(encoding="utf-8")
        lecteurs_part |= _fonctions_qui_lisent(source, str(fichier), noms_part)
        lecteurs_relief |= _fonctions_qui_lisent(source, str(fichier), noms_relief)
        formules_ici += len(
            _fonctions_qui_lisent(source, str(fichier), {nom_production})
        )
        jeux_ici += _jeux_indexes_par(source, classes_carte)

        relatif = "sim/" + str(fichier.relative_to(sim_dir))
        source_master = _texte_master(relatif)
        jeux_master += _jeux_indexes_par(source_master, classes_carte)

    n_part = len(lecteurs_part)
    n_relief = len(lecteurs_relief)
    print(f"fonctions_lisant_part_miniere={n_part} {sorted(lecteurs_part)}")
    print(f"fonctions_lisant_table_relief={n_relief} {sorted(lecteurs_relief)}")
    print(f"jeux_richesse_ici={jeux_ici} jeux_richesse_master={jeux_master}")
    print(f"formules_prod_ici={formules_ici}")

    assert n_relief > 0, (
        "référence vide : le parcours ne voit aucune lecture de la table "
        "des facteurs de relief"
    )
    assert n_part == n_relief, (
        "la part minière ne se calcule pas au même nombre d'endroits que "
        f"le motif relief : {n_part} != {n_relief}"
    )
    assert jeux_ici > 0 and jeux_master > 0, (
        f"comptage nul des jeux de richesse : ici={jeux_ici} master={jeux_master}"
    )
    assert jeux_ici == jeux_master, (
        f"un second jeu de facteurs de richesse apparaît : {jeux_ici} != {jeux_master}"
    )
    assert formules_ici > 0, (
        f"comptage nul des formules de production : ici={formules_ici}"
    )


def test_formule_agricole_suit_le_motif_relief():
    """
    SC5 — La formule agricole de base n'existe qu'à un seul endroit :
    autant de lectrices de la constante de rendement au km² que de
    lectrices de la table de relief, même parcours, même arbre.
    """
    modules = _modules_sim_hors_tests()
    n_modules = len(modules)
    print(f"modules_parcourus={n_modules}")
    assert n_modules > 0, "échantillon vide : aucun module de sim/ hors tests"

    noms_relief = _constantes_relief_table()
    assert noms_relief, "référence vide : aucune constante de table de relief"
    nom_production = "FOOD_PRODUCTION_KG_PER_KM2_PER_TICK"

    lecteurs_relief: set[str] = set()
    lecteurs_prod: set[str] = set()
    for fichier in modules:
        source = fichier.read_text(encoding="utf-8")
        lecteurs_relief |= _fonctions_qui_lisent(source, str(fichier), noms_relief)
        lecteurs_prod |= _fonctions_qui_lisent(
            source, str(fichier), {nom_production}
        )

    n_relief = len(lecteurs_relief)
    n_prod = len(lecteurs_prod)
    print(f"fonctions_lisant_table_relief={n_relief} {sorted(lecteurs_relief)}")
    print(
        f"fonctions_lisant_rendement_agricole={n_prod} {sorted(lecteurs_prod)}"
    )

    assert n_relief > 0, (
        "référence vide : le parcours ne voit aucune lecture de la table "
        "des facteurs de relief"
    )
    assert n_prod == n_relief, (
        "la constante de rendement agricole n'a pas autant de lectrices "
        f"que la table de relief : {n_prod} != {n_relief}"
    )


def test_moteur_consulte_part_miniere_par_fonction():
    """
    SC9 — Dénominateur dérivé des constantes lues par nom dans engine.py.
    PART_MINIERE_* n'y figurent pas ; part_miniere_de est parmi les appels.
    """
    import sim.constants as _k

    engine_path = pathlib.Path(__file__).resolve().parents[1] / "engine.py"
    source = engine_path.read_text(encoding="utf-8")
    arbre = ast.parse(source, filename=str(engine_path))

    numeriques = {
        nom
        for nom in dir(_k)
        if nom.isupper() and isinstance(getattr(_k, nom), (int, float))
    }
    lues = {
        node.attr
        for node in ast.walk(arbre)
        if isinstance(node, ast.Attribute)
        and node.attr in numeriques
        and not isinstance(node.ctx, ast.Store)
    }
    print(f"constantes_lues_par_nom={len(lues)} {sorted(lues)}")
    assert lues, (
        "dénominateur vide : le parcours ne voit aucune constante lue par nom"
    )
    assert "PART_MINIERE_PAR_GISEMENT" not in lues
    assert "PART_MINIERE_MAXIMALE" not in lues

    appels = {
        node.func.attr
        for node in ast.walk(arbre)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "_constantes"
    }
    print(f"fonctions_appelees_sur_constantes={sorted(appels)}")
    assert appels, (
        "la sonde ne voit aucun appel à sim.constants : elle ne prouve rien"
    )
    assert "part_miniere_de" in appels, (
        "part_miniere_de n'est pas parmi les fonctions que le moteur appelle"
    )


def test_extraction_suit_les_mineurs():
    """
    SC6 — À population égale, l'extraction est proportionnelle à la part
    minière. Une part nulle mesure 0.0, pas la sentinelle -1.
    """
    from sim import constants as _k
    from sim.engine import _extraction_du_tick_kg

    world = World.charger(0)
    facteurs = _k.facteurs_richesse_extraction()
    par_part: dict[int, float] = {}
    for cid, cell in world.cells.items():
        gisements = (world.carte.get(cid) or {}).get("gisements")
        part = _k.part_miniere_de(gisements, facteurs)
        if part > 0.0:
            par_part[cid] = part
    assert par_part, "échantillon vide : aucune part minière strictement positive"

    paires = [
        (a, b)
        for a in par_part
        for b in par_part
        if a < b and par_part[a] != par_part[b]
    ]
    assert paires, "échantillon vide : toutes les parts minières sont égales"
    cid_a, cid_b = paires[0]
    population = 1000
    world.cells[cid_a].population = population
    world.cells[cid_b].population = population
    extrait_a = sum(
        _extraction_du_tick_kg(world.cells[cid_a], world.carte).values()
    )
    extrait_b = sum(
        _extraction_du_tick_kg(world.cells[cid_b], world.carte).values()
    )
    ratio_parts = par_part[cid_a] / par_part[cid_b]
    ratio_extraits = extrait_a / extrait_b
    print(
        f"cid_a={cid_a} part_a={par_part[cid_a]} extrait_a={extrait_a} "
        f"cid_b={cid_b} part_b={par_part[cid_b]} extrait_b={extrait_b}"
    )
    print(f"ratio_parts={ratio_parts} ratio_extraits={ratio_extraits}")
    assert extrait_a > 0.0 and extrait_b > 0.0
    assert abs(ratio_extraits - ratio_parts) < 1e-9, (
        "L'extraction n'est pas proportionnelle à la part minière."
    )

    cid_nulle = next(
        cid for cid in world.cells if cid not in par_part
    )
    extrait_nul = sum(
        _extraction_du_tick_kg(world.cells[cid_nulle], world.carte).values()
    )
    print(f"cid_nulle={cid_nulle} extrait_nul={extrait_nul}")
    assert extrait_nul == 0.0
    assert extrait_nul != -1


def test_cellules_minieres_produisent_moins_et_portent_moins_de_monde():
    """
    SC7 — Sur le monde réel, une cellule qui extrait produit strictement moins
    de nourriture, et porte donc strictement moins d'habitants, que la même
    cellule dont le gisement a été vidé.

    **Ce que ce test mesurait avant, et pourquoi il a changé.** Il demandait
    que les porteuses s'endettent *plus* que les mêmes cellules sans gisement.
    C'était vrai tant que le monde posait dix habitants au kilomètre carré sans
    regarder la terre : une cellule qui détournait une part de ses bras vers la
    mine se retrouvait avec autant de bouches et moins de récolte, donc
    endettée. Ce n'était pas une règle du monde — c'était la conséquence d'un
    amorçage qui ne mesurait rien.

    Depuis que la population d'une cellule est dérivée de sa production, les
    porteuses ne s'endettent plus du tout : mesuré à 15, 20, 25, 30 et 40
    ticks, leur dette vaut exactement zéro, avec gisements comme sans. Garder
    l'ancienne assertion aurait obligé à réintroduire une famine artificielle
    pour la satisfaire.

    La règle du monde, elle, n'a pas bougé, et elle se mesure maintenant là où
    elle agit : moins de bras aux champs, moins de récolte, moins de monde
    nourri. Mesuré : 2 071 681 habitants sur les porteuses contre 2 262 189
    sans leurs gisements, soit 8,4 % de moins.

    Ce test peut échouer : rendre l'amorçage aveugle à la part minière, ou
    faire produire autant une cellule qui extrait, le rend rouge.
    """
    import random

    from sim import constants as _k
    from sim import engine
    from sim.engine import tick

    carte_doc = World.lire_carte()
    porteuses = _porteuses_de_la_carte(carte_doc)
    assert porteuses, "échantillon vide : aucune cellule porteuse"
    # Après la réserve initiale, avant que la mortalité n'ait fini d'ajuster
    # la ration : c'est là que la dette est une mesure, pas un équilibre.
    horizon = _k.INITIAL_FOOD_RESERVE_TICKS + _k.N_BOUND_MORT

    def _jouer(sans_gisements: bool) -> tuple[float, float]:
        monde = World.charger(0)
        if sans_gisements:
            monde.carte = _carte_sans_gisements(monde.carte)
        productions = {cid: 0.0 for cid in porteuses}
        originale = engine.production_du_tick_kg

        def _mesurer(cell, yield_factor, carte, jour=None):
            valeur = originale(cell, yield_factor, carte, jour)
            if cell.cell_id in productions:
                productions[cell.cell_id] += valeur
            return valeur

        engine.production_du_tick_kg = _mesurer
        try:
            rng = random.Random(0)
            for numero in range(horizon):
                tick(monde, rng, numero_tick=numero)
        finally:
            engine.production_du_tick_kg = originale
        production = sum(productions.values())
        dette = sum(monde.cells[cid].food_deficit_kg for cid in porteuses)
        return production, dette

    prod_avec, dette_avec = _jouer(False)
    prod_sans, dette_sans = _jouer(True)

    monde_avec = World.charger(0)
    sans_doc = dict(carte_doc)
    sans_doc["cellules"] = [dict(c, gisements=[]) for c in carte_doc["cellules"]]
    monde_sans = World.charger(0, carte_doc=sans_doc)
    pop_avec = sum(monde_avec.cells[cid].population for cid in porteuses)
    pop_sans = sum(monde_sans.cells[cid].population for cid in porteuses)

    print(
        f"horizon={horizon} porteuses={len(porteuses)} "
        f"prod_avec={prod_avec} prod_sans={prod_sans} "
        f"dette_avec={dette_avec} dette_sans={dette_sans} "
        f"pop_avec={pop_avec} pop_sans={pop_sans}"
    )
    assert prod_avec < prod_sans, (
        "Les porteuses ne produisent pas moins avec leurs gisements."
    )
    assert pop_avec < pop_sans, (
        "Les porteuses n'amorcent pas moins d'habitants avec leurs gisements : "
        "l'amorçage ne lit plus la part minière."
    )


def test_extraction_accumule_dans_le_panier():
    """Deux extractions ajoutent les kg ; elles ne remplacent pas le stock."""
    from sim.engine import _apply_extraction, _extraction_du_tick_kg
    from sim.model import lire_stock_marchandise

    world = World.charger(0)
    cid = next(
        int(raw["cell_id"])
        for raw in World.lire_carte()["cellules"]
        if any(
            isinstance(g, dict) and g.get("ressource") and g.get("richesse")
            for g in (raw.get("gisements") or [])
        )
    )
    cell = world.cells[cid]
    extrait = _extraction_du_tick_kg(cell, world.carte)
    assert extrait, "échantillon vide : la cellule porteuse n'extrait rien"
    for ressource in extrait:
        assert lire_stock_marchandise(cell, ressource) == -1.0

    _apply_extraction(cell, world.carte)
    for ressource, quantite in extrait.items():
        assert lire_stock_marchandise(cell, ressource) == pytest.approx(quantite)

    _apply_extraction(cell, world.carte)
    for ressource, quantite in extrait.items():
        assert lire_stock_marchandise(cell, ressource) == pytest.approx(2.0 * quantite)


def test_cli_refuse_ticks_negatif():
    proc = subprocess.run(
        [sys.executable, "-m", "sim", "--ticks", "-1", "--json"],
        cwd=_REPO,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "refus" in proc.stderr
    assert proc.stdout == ""



def test_snapshot_refuse_monde_sans_carte(tmp_path: Path):
    """Sans carte figée, aucune géométrie à photographier : on refuse, on n'invente pas."""
    monde = World({1: Cell(cell_id=1, area_km2=1.0, population=10)}, [])
    assert not monde.carte
    with pytest.raises(SnapshotExportError) as refus:
        build_snapshot_document(monde, 0, 0)
    assert "carte" in str(refus.value)
    dest = tmp_path / "invente.json"
    with pytest.raises(SnapshotExportError):
        export_snapshot(monde, 0, 0, dest)
    assert not dest.exists()


def test_snapshot_refuse_geometrie_ou_centroide_absent():
    """Une cellule chargée sans géométrie, ou un centroïde amputé, se dit : rien n'est complété."""
    monde = World.charger(0)
    assert monde.cells, "échantillon vide : le monde chargé n'a aucune cellule"
    cid = next(iter(sorted(monde.cells, key=int)))
    brute = dict(monde.carte[cid])

    sans_geo = dict(brute)
    del sans_geo["geometry"]
    monde.carte[cid] = sans_geo
    with pytest.raises(SnapshotExportError) as refus_geo:
        build_snapshot_document(monde, 0, 0)
    assert "geometrie absente" in str(refus_geo.value)
    assert str(cid) in str(refus_geo.value)

    monde.carte[cid] = brute
    centro = dict(brute["centroid"])
    del centro["lon"]
    ampute = dict(brute)
    ampute["centroid"] = centro
    monde.carte[cid] = ampute
    with pytest.raises(SnapshotExportError) as refus_centro:
        build_snapshot_document(monde, 0, 0)
    assert "centroide" in str(refus_centro.value)
    assert str(cid) in str(refus_centro.value)


def test_snapshot_refuse_cellule_sans_position_ou_sans_province(monkeypatch):
    """Position inconnue ou province introuvable : l'absence se déclare, elle ne s'invente pas."""
    monde = World.charger(0)
    assert monde.cells, "échantillon vide : le monde chargé n'a aucune cellule"
    inconnu = max(int(cid) for cid in monde.cells) + 1
    monde.cells[inconnu] = Cell(cell_id=inconnu, area_km2=1.0, population=1)
    with pytest.raises(SnapshotExportError) as refus_pos:
        build_snapshot_document(monde, 0, 0)
    assert str(inconnu) in str(refus_pos.value)
    assert "position" in str(refus_pos.value)

    del monde.cells[inconnu]

    import sim.snapshot_export as export

    monkeypatch.setattr(export, "agregat_depuis_monde", lambda _monde: ())
    with pytest.raises(SnapshotExportError) as refus_prov:
        build_snapshot_document(monde, 0, 0)
    assert "province absente" in str(refus_prov.value)


def test_cli_snapshot_refuse_si_export_impossible(tmp_path: Path, monkeypatch, capsys):
    """La CLI nomme le refus : un SnapshotExportError ne devient pas une trace."""
    from sim import __main__ as cli

    def boom(*_a, **_k):
        raise SnapshotExportError("geometrie absente de la carte pour cell_id=1")

    monkeypatch.setattr(cli, "export_snapshot", boom)
    code = cli.main(["--ticks", "0", "--snapshot-json", str(tmp_path / "x.json")])
    assert code == 2
    sortie = capsys.readouterr()
    assert "refus" in sortie.err
    assert "geometrie absente" in sortie.err
    assert sortie.out == ""


# --- Brief 051 : le snapshot photographie le bourg ---


def _version_schema_avant_051() -> str:
    texte = _texte_avant_051("sim/constants.py")
    match = re.search(r'SNAPSHOT_SCHEMA_VERSION = "([^"]+)"', texte)
    assert match, (
        "SNAPSHOT_SCHEMA_VERSION introuvable sur "
        f"{REVISION_AVANT_051[:7]}"
    )
    return match.group(1)


def _archive_avant_051_dans(repertoire: Path) -> Path:
    """sim/ et data/ d'avant 051, par git archive (jamais l'arbre entier)."""
    ref = _ref_avant_051()
    archive = repertoire / "master.zip"
    proc = subprocess.run(
        ["git", "archive", "--format=zip", "-o", str(archive), ref, "sim", "data"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        f"git archive a échoué ({proc.stderr.strip()})"
    )
    racine = repertoire / "master_tree"
    racine.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(racine)
    return racine


def _snapshot_document_depuis_arbre(arbre: Path, seed: int, tick: int) -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(arbre)
    script = (
        "import json\n"
        "from sim.world import World\n"
        "from sim.snapshot_export import build_snapshot_document\n"
        f"monde = World.charger(rng_seed={seed})\n"
        f"doc = build_snapshot_document(monde, {seed}, {tick})\n"
        "print(json.dumps(doc, sort_keys=True))\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", script],
        cwd=arbre,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        f"snapshot master a échoué ({proc.stderr.strip()})"
    )
    return json.loads(proc.stdout)


def _retirer_bourg_pour_comparaison(document: dict, version: str) -> dict:
    restaure = copy.deepcopy(document)
    restaure["schema_version"] = version
    for cellule in restaure["cells"]:
        del cellule["bourg"]
    return restaure


def _controle_snapshot_export_pas_seconde_formule_bourg(source: str) -> None:
    assert "part_miniere_de" not in source, (
        "sim/snapshot_export.py ne doit pas recalculer la part minière"
    )
    assert "facteurs_richesse_extraction" not in source, (
        "sim/snapshot_export.py ne doit pas lire les facteurs de richesse"
    )
    arbre = ast.parse(source, filename="sim/snapshot_export.py")
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.FunctionDef):
            nom = noeud.name.lower().replace("_", "")
            assert "bourg" not in nom, (
                f"fonction locale interdite : {noeud.name}"
            )


def test_snapshot_bourg_recalcule_pas_stocke():
    """SC1 — cell['bourg'] recalcule bourg_depuis_monde ; avant 051, KeyError."""
    monde = World.charger(0)
    doc = build_snapshot_document(monde, 0, 0)
    repartitions = bourg_depuis_monde(monde)
    comparees = 0
    for cellule in doc["cells"]:
        attendu = repartition_bourg_de_cellule_consultation(
            cellule["cell_id"], repartitions
        )
        assert attendu is not None
        assert cellule["bourg"]["habitants_du_bourg"] == attendu.habitants_du_bourg
        assert (
            cellule["bourg"]["habitants_des_champs"]
            == attendu.habitants_des_champs
        )
        comparees += 1
    assert comparees == len(monde.cells), (
        f"cellules comparées={comparees} monde={len(monde.cells)}"
    )

    with tempfile.TemporaryDirectory() as tmp:
        arbre = _archive_avant_051_dans(Path(tmp))
        doc_avant_051 = _snapshot_document_depuis_arbre(arbre, 0, 0)
    with pytest.raises(KeyError):
        _ = doc_avant_051["cells"][0]["bourg"]


def test_snapshot_bourg_somme_exacte_par_cellule():
    """SC3 — habitants_du_bourg + habitants_des_champs == population."""
    monde = World.charger(0)
    doc = build_snapshot_document(monde, 0, 0)
    ecarts = 0
    for cellule in doc["cells"]:
        bourg = cellule["bourg"]
        somme = bourg["habitants_du_bourg"] + bourg["habitants_des_champs"]
        if somme != cellule["population"]:
            ecarts += 1
    print(f"ecarts_somme_bourg={ecarts} / {len(doc['cells'])}")
    assert ecarts == 0


def test_snapshot_bourg_echantillon_non_vide():
    """SC4 — cellules avec bourg > 0 alignées sur repartitions_avec_bourg."""
    monde = World.charger(0)
    doc = build_snapshot_document(monde, 0, 0)
    repartitions = bourg_depuis_monde(monde)
    attendu = len(repartitions_avec_bourg(repartitions))
    mesure = sum(
        1
        for cellule in doc["cells"]
        if cellule["bourg"]["habitants_du_bourg"] > 0
    )
    print(f"cellules_avec_bourg_document={mesure} vue={attendu}")
    assert mesure > 0
    assert mesure == attendu


def test_snapshot_bourg_une_seule_voie_lecture():
    """SC5 — snapshot_export n'implémente pas une seconde part non agricole."""
    chemin = pathlib.Path(__file__).resolve().parents[1] / "snapshot_export.py"
    source = chemin.read_text(encoding="utf-8")
    _controle_snapshot_export_pas_seconde_formule_bourg(source)
    eprouvee = source + "\n# sonde\npart_miniere_de(gisements, facteurs)\n"
    with pytest.raises(AssertionError):
        _controle_snapshot_export_pas_seconde_formule_bourg(eprouvee)


def test_snapshot_bourg_seule_difference_avec_master():
    """SC6 — Retirer bourg et la version : empreinte identique à avant 051."""
    version_avant = _version_schema_avant_051()
    assert version_avant != SNAPSHOT_SCHEMA_VERSION, (
        "le schéma n'a pas changé par rapport à la révision d'avant 051"
    )
    seed = 0
    tick = 0
    monde = World.charger(seed)
    doc_apres = build_snapshot_document(monde, seed, tick)

    with tempfile.TemporaryDirectory() as tmp:
        arbre = _archive_avant_051_dans(Path(tmp))
        doc_avant = _snapshot_document_depuis_arbre(arbre, seed, tick)
        env = os.environ.copy()
        env["PYTHONPATH"] = str(arbre)
        proc_json = subprocess.run(
            [
                sys.executable,
                "-m",
                "sim",
                "--ticks",
                "365",
                "--seed",
                "0",
                "--json",
            ],
            cwd=arbre,
            env=env,
            capture_output=True,
            text=True,
        )
        assert proc_json.returncode == 0, proc_json.stderr
        sortie_avant = proc_json.stdout

    restaure = _retirer_bourg_pour_comparaison(doc_apres, version_avant)
    empreinte_avant = _sha(serialize_snapshot(doc_avant))
    empreinte_restauree = _sha(serialize_snapshot(restaure))
    print(f"schema_avant={version_avant} schema_lot={SNAPSHOT_SCHEMA_VERSION}")
    assert empreinte_restauree == empreinte_avant

    proc_local = subprocess.run(
        [sys.executable, "-m", "sim", "--ticks", "365", "--seed", "0", "--json"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc_local.returncode == 0, proc_local.stderr
    assert proc_local.stdout == sortie_avant


def test_snapshot_schema_version_a_change():
    """SC2 — SNAPSHOT_SCHEMA_VERSION lu avant 051, pas recopié d'ici."""
    assert SNAPSHOT_SCHEMA_VERSION == "v0a-4"
    assert _version_schema_avant_051() == "v0a-3"
