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


def _arbre_master(ref: str) -> set[str]:
    """Les chemins que master suit, lus dans son arbre."""
    proc = subprocess.run(
        ["git", "ls-tree", "-r", "-z", "--full-tree", "--name-only", ref],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 0, (
        f"arbre de {ref!r} illisible ({proc.stderr.strip()})"
    )
    return {p for p in proc.stdout.split("\0") if p}


def _texte_master(relatif: str, ref: str | None = None) -> str:
    """
    Source d'un fichier sur master, rejouée, jamais recopiée.

    `relatif` part du paquet (« sim/engine.py »). L'endroit où master range
    ce paquet se lit dans son arbre — « sim/ », puis « jeu/sim/ » depuis le
    rangement du 27 septembre 2026 — et n'est jamais écrit en dur.

    Un module absent de master (le premier module neuf d'un lot) rend une
    source vide : il n'y porte aucun jeu de facteurs, et c'est une mesure
    juste (lot 248, demande #49). Toute autre erreur reste une erreur.
    """
    ref = ref or _ref_master()
    arbre = _arbre_master(ref)
    paquet, _, reste = relatif.partition("/")
    ancre = f"{paquet}/__init__.py"
    racines = sorted(
        p[: -len("__init__.py")]
        for p in arbre
        if p == ancre or p.endswith("/" + ancre)
    )
    assert len(racines) == 1, (
        f"master ne porte pas un et un seul paquet {paquet!r} : {racines}"
    )
    chemin = racines[0] + reste
    if chemin not in arbre:
        return ""
    proc = subprocess.run(
        ["git", "show", f"{ref}:{chemin}"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 0, (
        f"master ne porte pas {chemin!r} ({proc.stderr.strip()})"
    )
    return proc.stdout


def test_texte_master_rend_vide_un_module_absent_de_master():
    """
    Lot 248 (demande #49) — un module absent de master, comme le premier
    module neuf d'un lot, compte pour une source sans aucun jeu de facteurs :
    c'est une mesure juste, pas un défaut. Le nom absent se dérive de
    l'arbre de master (un module qui y est, suffixé jusqu'à ne plus y être),
    jamais écrit en dur.
    """
    ref = _ref_master()
    chemins = _arbre_master(ref)
    modules = sorted(p for p in chemins if p.endswith("/engine.py") or p == "sim/engine.py")
    assert modules, "échantillon vide : master ne porte aucun engine.py"
    dossier, _, nom = modules[0].rpartition("/")
    absent = nom
    while f"{dossier}/{absent}" in chemins:
        absent = absent.removesuffix(".py") + "_neuf.py"
    assert _texte_master("sim/" + absent) == ""
    # Le module présent, lui, se lit toujours : l'absence ne s'étend pas.
    assert "def tick" in _texte_master("sim/" + nom)


def test_texte_master_echoue_sur_une_reference_illisible():
    """
    Lot 248 (demande #49) — sans ce cas, le précédent ne prouve rien : une
    référence que git ne sait pas lire échoue toujours, elle ne rend jamais
    une source vide. La référence illisible se dérive de celle de master,
    suffixée jusqu'à ce que `git rev-parse` ne la connaisse plus.
    """
    illisible = _ref_master() + "-illisible"
    while subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", illisible],
        cwd=_REPO_ROOT, capture_output=True, text=True,
    ).returncode == 0:
        illisible += "-illisible"
    with pytest.raises(AssertionError):
        _texte_master("sim/engine.py", ref=illisible)


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


# --- Fabrication : le minerai devient un objet ---


def _cellule_epreuve_fabrication() -> Cell:
    return Cell(cell_id=1, area_km2=1.0, population=10)


def test_fabrication_transforme_dans_les_proportions_declarees():
    """SC1 — _apply_fabrication consomme et produit selon les constantes nommées."""
    from sim import constants as _k
    from sim.engine import _apply_fabrication
    from sim.model import ecrire_stock_marchandise, lire_stock_marchandise

    matiere = "fer"
    stock_avant = 200.0
    consomme = stock_avant * _k.TAUX_FABRICATION_PAR_TICK
    produit = consomme * _k.RENDEMENT_FABRICATION

    cell = _cellule_epreuve_fabrication()
    ecrire_stock_marchandise(cell, matiere, stock_avant)
    _apply_fabrication(cell)
    assert lire_stock_marchandise(cell, matiere) == stock_avant - consomme
    assert lire_stock_marchandise(cell, _k.MARCHANDISE_OBJET) == produit

    cell_objet = _cellule_epreuve_fabrication()
    ecrire_stock_marchandise(cell_objet, matiere, stock_avant)
    ecrire_stock_marchandise(cell_objet, _k.MARCHANDISE_OBJET, 7.0)
    _apply_fabrication(cell_objet)
    assert lire_stock_marchandise(cell_objet, _k.MARCHANDISE_OBJET) == 7.0 + produit

    cell_nulle = _cellule_epreuve_fabrication()
    ecrire_stock_marchandise(cell_nulle, matiere, 0.0)
    _apply_fabrication(cell_nulle)
    assert lire_stock_marchandise(cell_nulle, matiere) == 0.0
    assert lire_stock_marchandise(cell_nulle, _k.MARCHANDISE_OBJET) == -1.0

    cell_absente = _cellule_epreuve_fabrication()
    assert lire_stock_marchandise(cell_absente, matiere) == -1.0
    _apply_fabrication(cell_absente)
    assert lire_stock_marchandise(cell_absente, _k.MARCHANDISE_OBJET) == -1.0


def test_fabrication_rendement_strictement_inferieur_a_un():
    """SC2 — La transformation perd de la masse : produit < consommé."""
    from sim import constants as _k
    from sim.engine import _apply_fabrication
    from sim.model import ecrire_stock_marchandise, lire_stock_marchandise

    assert _k.RENDEMENT_FABRICATION < 1.0
    stock_avant = 80.0
    consomme = stock_avant * _k.TAUX_FABRICATION_PAR_TICK
    cell = _cellule_epreuve_fabrication()
    ecrire_stock_marchandise(cell, "cuivre", stock_avant)
    _apply_fabrication(cell)
    produit = lire_stock_marchandise(cell, _k.MARCHANDISE_OBJET)
    assert produit < consomme
    assert produit == consomme * _k.RENDEMENT_FABRICATION


def test_fabrication_deux_matieres_premieres_meme_objet():
    """SC3 — Deux ressources distinctes alimentent le même stock d'objet."""
    from sim import constants as _k
    from sim.engine import _apply_fabrication
    from sim.model import ecrire_stock_marchandise, lire_stock_marchandise

    _, ressources, _ = _agreger_gisements_carte(World.lire_carte())
    assert len(ressources) >= 2, "échantillon vide : moins de deux ressources sur la carte"
    m1, m2 = sorted(ressources)[:2]
    stock = 100.0
    consomme = stock * _k.TAUX_FABRICATION_PAR_TICK
    produit_un = consomme * _k.RENDEMENT_FABRICATION

    seule = _cellule_epreuve_fabrication()
    ecrire_stock_marchandise(seule, m1, stock)
    _apply_fabrication(seule)
    objet_seul = lire_stock_marchandise(seule, _k.MARCHANDISE_OBJET)

    les_deux = _cellule_epreuve_fabrication()
    ecrire_stock_marchandise(les_deux, m1, stock)
    ecrire_stock_marchandise(les_deux, m2, stock)
    _apply_fabrication(les_deux)
    objet_double = lire_stock_marchandise(les_deux, _k.MARCHANDISE_OBJET)

    assert objet_seul == produit_un
    assert objet_double > objet_seul
    assert objet_double == 2.0 * produit_un


def test_fabrication_premier_tick_ne_faconne_pas():
    """SC4 — Au tick 0, aucune cellule ne porte encore d'objet façonné ce jour."""
    import random

    from sim import constants as _k
    from sim.engine import tick
    from sim.model import lire_stock_marchandise

    carte_doc = World.lire_carte()
    porteuses = _porteuses_de_la_carte(carte_doc)
    assert porteuses, "échantillon vide : aucune cellule porteuse sur la carte"

    monde = World.charger(0)
    tick(monde, random.Random(0), numero_tick=0)

    avec_objet = [
        cid
        for cid, cell in monde.cells.items()
        if lire_stock_marchandise(cell, _k.MARCHANDISE_OBJET) > 0.0
    ]
    print(f"porteuses={len(porteuses)} cellules_avec_objet={len(avec_objet)}")
    assert avec_objet == []


def test_fabrication_deuxieme_tick_faconne_extrait():
    """SC5 — Au second tick, l'objet apparaît sur une cellule minière."""
    import random

    from sim import constants as _k
    from sim.engine import tick
    from sim.model import lire_stock_marchandise

    carte_doc = World.lire_carte()
    porteuses = sorted(_porteuses_de_la_carte(carte_doc))
    assert porteuses, "échantillon vide : aucune cellule porteuse sur la carte"

    monde = World.charger(0)
    rng = random.Random(0)
    tick(monde, rng, numero_tick=0)
    tick(monde, rng, numero_tick=1)

    trouvees = 0
    for cid in porteuses:
        stock = lire_stock_marchandise(monde.cells[cid], _k.MARCHANDISE_OBJET)
        if stock > 0.0:
            trouvees += 1
    print(f"porteuses={len(porteuses)} avec_objet={trouvees}")
    assert trouvees > 0


def test_fabrication_objet_ne_circule_pas():
    """SC6 — L'objet n'a pas de consommation par habitant."""
    from sim import constants as _k

    assert _k.consommation_kg_par_habitant_par_tick(_k.MARCHANDISE_OBJET) == 0.0


def test_fabrication_constantes_lues_par_fonction_seulement():
    """SC7 — engine.py ne nomme pas les constantes de façonnage directement."""
    import ast

    engine_path = pathlib.Path(__file__).resolve().parents[1] / "engine.py"
    source = engine_path.read_text(encoding="utf-8")
    arbre = ast.parse(source, filename=str(engine_path))
    interdits = {"TAUX_FABRICATION_PAR_TICK", "RENDEMENT_FABRICATION"}
    cites = {
        node.attr
        for node in ast.walk(arbre)
        if isinstance(node, ast.Attribute)
        and node.attr in interdits
        and isinstance(node.value, ast.Name)
        and node.value.id == "_constantes"
    }
    assert cites == set(), (
        f"constantes_fabrication_citees_directement={sorted(cites)}"
    )

    fautif = source.replace(
        "consomme, produit = _constantes.fabrication_kg(stock)",
        "consomme, produit = _constantes.fabrication_kg(stock)\n"
        "        _ = _constantes.TAUX_FABRICATION_PAR_TICK",
    )
    arbre_fautif = ast.parse(fautif, filename="engine_fautif.py")
    cites_fautif = {
        node.attr
        for node in ast.walk(arbre_fautif)
        if isinstance(node, ast.Attribute)
        and node.attr in interdits
        and isinstance(node.value, ast.Name)
        and node.value.id == "_constantes"
    }
    assert "TAUX_FABRICATION_PAR_TICK" in cites_fautif


def test_fabrication_determinisme_meme_graine():
    """SC9 — Même graine et mêmes ticks : to_dict et stocks_mer identiques."""
    import random

    from sim import constants as _k
    from sim.engine import tick
    from sim.model import lire_stock_marchandise

    def _jouer(monde: World, ticks: int) -> None:
        rng = random.Random(0)
        for t in range(ticks):
            tick(monde, rng, numero_tick=t)

    ticks = 3
    a = World.charger(0)
    b = World.charger(0)
    _jouer(a, ticks)
    _jouer(b, ticks)
    assert a.to_dict() == b.to_dict()
    assert a.stocks_mer == b.stocks_mer

    avec_objet = sum(
        1
        for cell in a.cells.values()
        if lire_stock_marchandise(cell, _k.MARCHANDISE_OBJET) > 0.0
    )
    assert avec_objet > 0, (
        "échantillon vide : aucune cellule avec objet après les ticks d'épreuve"
    )


def test_fabrication_ordre_insertion_panier_invariant():
    """SC9 — L'ordre d'insertion des matières premières ne change pas l'objet."""
    from sim import constants as _k
    from sim.engine import _apply_fabrication
    from sim.model import ecrire_stock_marchandise, lire_stock_marchandise

    _, ressources, _ = _agreger_gisements_carte(World.lire_carte())
    assert len(ressources) >= 2, "échantillon vide : moins de deux ressources sur la carte"
    m1, m2 = sorted(ressources)[:2]
    stock = 50.0

    def _cellule(ordre: list[str]) -> Cell:
        cell = _cellule_epreuve_fabrication()
        for cle in ordre:
            ecrire_stock_marchandise(cell, cle, stock)
        return cell

    c1 = _cellule([m1, m2])
    c2 = _cellule([m2, m1])
    _apply_fabrication(c1)
    _apply_fabrication(c2)
    o1 = lire_stock_marchandise(c1, _k.MARCHANDISE_OBJET)
    o2 = lire_stock_marchandise(c2, _k.MARCHANDISE_OBJET)
    assert o1 == o2
    assert o1 > 0.0


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
    """SC1 — cell['bourg'] du snapshot égale bourg_depuis_monde, jamais Cell."""
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
        cellule_monde = monde.cells[cellule["cell_id"]]
        assert not hasattr(cellule_monde, "bourg")
        comparees += 1
    assert comparees == len(monde.cells), (
        f"cellules comparées={comparees} monde={len(monde.cells)}"
    )
    sonde = type("SondeBourgStocke", (), {"bourg": {}})()
    assert hasattr(sonde, "bourg"), (
        "le contrôle hasattr(..., 'bourg') ne rougit pas sur une sonde"
    )


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
    """Le snapshot qui porte le bourg est déterministe ; sans bourg, l'empreinte change."""
    seed = 0
    tick = 0
    monde_a = World.charger(seed)
    monde_b = World.charger(seed)
    doc_a = build_snapshot_document(monde_a, seed, tick)
    doc_b = build_snapshot_document(monde_b, seed, tick)
    empreinte = _sha(serialize_snapshot(doc_a))
    assert empreinte == _sha(serialize_snapshot(doc_b))

    sans_bourg = copy.deepcopy(doc_a)
    retirees = 0
    for cellule in sans_bourg["cells"]:
        del cellule["bourg"]
        retirees += 1
    assert retirees == len(doc_a["cells"]) > 0
    assert _sha(serialize_snapshot(sans_bourg)) != empreinte, (
        "l'empreinte ignore le bourg"
    )

    proc_a = subprocess.run(
        [sys.executable, "-m", "sim", "--ticks", "0", "--seed", "0", "--json"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    proc_b = subprocess.run(
        [sys.executable, "-m", "sim", "--ticks", "0", "--seed", "0", "--json"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc_a.returncode == 0, proc_a.stderr
    assert proc_b.returncode == 0, proc_b.stderr
    assert proc_a.stdout == proc_b.stdout


def test_snapshot_schema_version_a_change():
    """Le document porte SNAPSHOT_SCHEMA_VERSION, et ce schéma inclut bourg."""
    monde = World.charger(0)
    doc = build_snapshot_document(monde, 0, 0)
    assert doc["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert SNAPSHOT_SCHEMA_VERSION
    assert "bourg" in doc["cells"][0]
    assert "bourg" in _CELL_KEYS
    epreuve = dict(doc["cells"][0])
    del epreuve["bourg"]
    assert "bourg" not in epreuve
    epreuve_cles = set(_CELL_KEYS)
    epreuve_cles.remove("bourg")
    assert "bourg" not in epreuve_cles


# --- lot 053 : temps du monde ---


def test_date_initiale_monde_neuf_porte_debut_annee():
    """SC1 — compteur nul, date dérivée, pas de date stockée sur le monde ni les cellules."""
    import sim.constants as _k

    monde = World.charger(0)
    assert len(monde.cells) > 0
    assert monde.ticks_ecoules == 0
    attendu = {
        "annee": _k.ANNEE_INITIALE,
        "jour_de_l_annee": 1,
    }
    assert monde.date_simulation == attendu
    assert _k.date_de_tick(0) == attendu
    assert not hasattr(monde, "annee")
    assert not hasattr(monde, "jour_de_l_annee")
    premiere_cellule = next(iter(monde.cells.values()))
    assert not hasattr(premiere_cellule, "annee")
    copie = dict(monde.date_simulation)
    copie["jour_de_l_annee"] = 99
    assert monde.date_simulation == attendu


def test_date_ticks_compteur_trois_regimes():
    """SC2 — le compteur suit les ticks réussis dans chaque régime saisonnier."""
    import random

    from sim import constants as _constants
    from sim.engine import _apply_production, tick

    class MondeEpreuve:
        """Monde d'épreuve qui n'est pas un World."""

        def __init__(self):
            self.cells = {
                1: Cell(
                    cell_id=1, area_km2=1.0, population=10,
                    stocks={}, hunger_ticks=0, food_deficit_kg=0.0,
                )
            }
            self.adjacency = []
            self.carte = {}
            self.stocks_mer = {}

    epreuve = MondeEpreuve()
    tick(epreuve, random.Random(0))
    assert not hasattr(epreuve, "ticks_ecoules")

    cellule = Cell(
        cell_id=1, area_km2=1.0, population=10,
        stocks={}, hunger_ticks=0, food_deficit_kg=0.0,
    )
    sans_carte = World(cells={1: cellule}, adjacency=[])

    avec_carte = World.charger(0)
    rng = random.Random(0)
    for n in range(3):
        tick(sans_carte, rng)
        assert sans_carte.ticks_ecoules == n + 1
        assert sans_carte.date_simulation == _constants.date_de_tick(sans_carte.ticks_ecoules)
    rng = random.Random(1)
    for n in range(3):
        tick(avec_carte, rng)
        assert avec_carte.ticks_ecoules == n + 1
    rng = random.Random(2)
    for n in range(3):
        tick(avec_carte, rng, numero_tick=avec_carte.ticks_ecoules)
        assert avec_carte.ticks_ecoules == n + 4
        assert avec_carte.date_simulation == _constants.date_de_tick(avec_carte.ticks_ecoules)

    monde = World.charger(0)
    avant = monde.ticks_ecoules
    _apply_production(next(iter(monde.cells.values())), random.Random(0), monde.carte)
    assert monde.ticks_ecoules == avant


def test_date_calendrier_derive_limites_et_consultation():
    """SC3 — date_de_tick aux limites d'année et constantes substituées."""
    import sim.constants as _k

    annee = _k.CALENDAR_DAYS_PER_YEAR
    assert _k.date_de_tick(0)["jour_de_l_annee"] == 1
    assert _k.date_de_tick(annee - 1)["jour_de_l_annee"] == annee
    assert _k.date_de_tick(annee)["annee"] == _k.ANNEE_INITIALE + 1
    assert _k.date_de_tick(annee)["jour_de_l_annee"] == 1
    assert _k.date_de_tick(2 * annee + 10)["annee"] == _k.ANNEE_INITIALE + 2

    tick_duree = _k.TICK_DURATION_DAYS
    annee_init = _k.ANNEE_INITIALE
    try:
        _k.TICK_DURATION_DAYS = 2
        _k.CALENDAR_DAYS_PER_YEAR = 10
        _k.ANNEE_INITIALE = 1500
        ticks = 7
        jours = ticks * _k.TICK_DURATION_DAYS
        annees, rang = divmod(jours, _k.CALENDAR_DAYS_PER_YEAR)
        attendu = {"annee": _k.ANNEE_INITIALE + annees, "jour_de_l_annee": rang + 1}
        assert _k.date_de_tick(ticks) == attendu
    finally:
        _k.TICK_DURATION_DAYS = tick_duree
        _k.CALENDAR_DAYS_PER_YEAR = annee
        _k.ANNEE_INITIALE = annee_init

    with pytest.raises(ValueError, match="reçu.*attendu"):
        _k.date_de_tick(-1)
    with pytest.raises(ValueError, match="reçu.*attendu"):
        _k.date_de_tick(True)
    with pytest.raises(ValueError, match="reçu.*attendu"):
        _k.date_de_tick(1.5)


def _monde_avec_gisement():
    import random

    from sim.engine import tick

    monde = World.charger(0)
    tick(monde, random.Random(0), numero_tick=0)
    return monde


def test_date_refus_numero_incoherent_avant_effets():
    """SC4 — ValueError, état inchangé, rng inchangé."""
    import random

    from sim import constants as _k
    from sim.engine import tick

    def _etat(monde, rng):
        return (
            monde.ticks_ecoules,
            copy.deepcopy(monde.to_dict()["cells"]),
            dict(monde.stocks_mer),
            copy.deepcopy(monde.carte),
            rng.getstate(),
        )

    monde = _monde_avec_gisement()
    rng = random.Random(99)
    tick(monde, rng, numero_tick=monde.ticks_ecoules)
    avant = _etat(monde, rng)

    for recu in (monde.ticks_ecoules - 1, monde.ticks_ecoules + 5, True, 1.5):
        rng_b = random.Random(99)
        rng_b.setstate(avant[4])
        with pytest.raises(ValueError, match="reçu.*attendu"):
            tick(monde, rng_b, numero_tick=recu)
        assert _etat(monde, rng_b)[:4] == avant[:4]
        assert rng_b.getstate() == avant[4]

    monde_corrompu = World.charger(0)
    monde_corrompu.ticks_ecoules = True
    with pytest.raises(ValueError, match="reçu.*attendu"):
        tick(monde_corrompu, random.Random(0), numero_tick=0)


def test_date_refus_sensibilite_garde_avant_extraction():
    """SC4 — une garde après l'extraction laisserait des traces sur un monde à gisements."""
    import random

    from sim.engine import _apply_extraction, _valider_numero_tick, tick

    monde = World.charger(0)
    rng = random.Random(0)
    stocks_avant = copy.deepcopy(
        {cid: dict(c.stocks) for cid, c in monde.cells.items()}
    )
    with pytest.raises(ValueError, match="reçu.*attendu"):
        tick(monde, rng, numero_tick=9)
    stocks_apres = {cid: dict(c.stocks) for cid, c in monde.cells.items()}
    assert stocks_avant == stocks_apres

    monde = World.charger(0)
    carte = monde.carte
    for cell in monde.cells.values():
        _apply_extraction(cell, carte)
    avec_extraction = {cid: dict(c.stocks) for cid, c in monde.cells.items()}
    with pytest.raises(ValueError, match="reçu.*attendu"):
        _valider_numero_tick(monde, 9)
    assert avec_extraction != stocks_avant, (
        "échantillon vide : l'extraction n'a rien changé avant la garde"
    )


def test_date_refus_exception_maillon_ne_progresse_pas(monkeypatch):
    """SC4 — exception dans un maillon : le compteur ne progresse pas."""
    import random

    from sim.engine import tick

    def _boom(_cell):
        raise RuntimeError("maillon coupé")

    monkeypatch.setattr("sim.engine._apply_fabrication", _boom)
    monde = World.charger(0)
    rng = random.Random(0)
    with pytest.raises(RuntimeError):
        tick(monde, rng, numero_tick=0)
    assert monde.ticks_ecoules == 0


def test_date_cli_resume_json_et_texte():
    """SC5 — résumé JSON et texte portent la date du monde joué."""
    import sim.constants as _k
    from sim.__main__ import _simulate

    resume, monde = _simulate(0, _k.DEFAULT_CLI_SEED)
    assert resume["date_simulation"] == monde.date_simulation
    sans_date = {k: v for k, v in resume.items() if k != "date_simulation"}
    autre, _ = _simulate(0, _k.DEFAULT_CLI_SEED)
    sans_date_b = {k: v for k, v in autre.items() if k != "date_simulation"}
    assert sans_date == sans_date_b

    ticks = _k.CALENDAR_DAYS_PER_YEAR
    resume, monde = _simulate(ticks, 0)
    assert resume["date_simulation"] == monde.date_simulation
    assert resume["date_simulation"]["annee"] == _k.ANNEE_INITIALE + 1
    assert resume["date_simulation"]["jour_de_l_annee"] == 1

    proc = subprocess.run(
        [sys.executable, "-m", "sim", "--ticks", "0", "--seed", "0"],
        cwd=_REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "année" in proc.stdout
    assert "jour dans l'année" in proc.stdout


def test_date_cli_refus_ticks_negatifs_inchange():
    proc = subprocess.run(
        [sys.executable, "-m", "sim", "--ticks", "-1", "--json"],
        cwd=_REPO,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "refus" in proc.stderr.lower()


# --- lot 115 : ordre documenté du tick ---


def _etapes_tick_dans_code(source: str) -> list[str]:
    """Appels de tick vers les fonctions du module, dans l'ordre du source."""
    arbre = ast.parse(source)
    fonctions_module = {
        node.name for node in arbre.body if isinstance(node, ast.FunctionDef)
    }
    ticks = [
        node
        for node in arbre.body
        if isinstance(node, ast.FunctionDef) and node.name == "tick"
    ]
    assert len(ticks) == 1, (
        f"tick() doit avoir une seule définition, trouvé : {len(ticks)}"
    )
    appels = sorted(
        (
            node
            for node in ast.walk(ticks[0])
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in fonctions_module
        ),
        key=lambda node: (node.lineno, node.col_offset),
    )
    ordre: list[str] = []
    for appel in appels:
        if appel.func.id not in ordre:
            ordre.append(appel.func.id)
    return ordre


def _etapes_tick_dans_modele(document: str) -> list[str]:
    """Fonctions citées par la liste numérotée de la section « En une page »."""
    import re

    section = re.search(
        r"^## En une page\s*$\n(.*?)(?=^## )", document, flags=re.MULTILINE | re.DOTALL
    )
    assert section is not None, "section « En une page » absente du modèle"
    items = re.findall(
        r"^\d+\. .*?(?=^\d+\. |\Z)", section.group(1), flags=re.MULTILINE | re.DOTALL
    )
    ordre: list[str] = []
    for item in items:
        for nom in re.findall(r"`(_[A-Za-z][A-Za-z0-9_]*)`", item):
            if nom not in ordre:
                ordre.append(nom)
    return ordre


def _verifier_meme_ordre_tick(code: list[str], document: list[str]) -> None:
    assert code, "ordre du code vide"
    assert document, "ordre du document vide"
    longueur = max(len(code), len(document))
    for indice in range(longueur):
        cote_code = code[indice] if indice < len(code) else "<fin>"
        cote_document = document[indice] if indice < len(document) else "<fin>"
        assert cote_code == cote_document, (
            f"première étape différente au rang {indice + 1} : "
            f"code={cote_code}, document={cote_document}"
        )


def _ordres_reels_du_tick() -> tuple[list[str], list[str]]:
    moteur = (_REPO_ROOT / "sim" / "engine.py").read_text(encoding="utf-8")
    modele = (_REPO_ROOT / "sim" / "MODELE.md").read_text(encoding="utf-8")
    return _etapes_tick_dans_code(moteur), _etapes_tick_dans_modele(modele)


def test_ordre_du_tick_documente_est_celui_du_code():
    code, document = _ordres_reels_du_tick()
    _verifier_meme_ordre_tick(code, document)


@pytest.mark.parametrize(
    "alteration",
    ["code_vide", "document_vide", "fabrication_absente", "deux_etapes_echangees"],
)
def test_ordre_du_tick_contre_epreuves_echouent(alteration: str):
    code, document = _ordres_reels_du_tick()
    if alteration == "code_vide":
        code = []
    elif alteration == "document_vide":
        document = []
    elif alteration == "fabrication_absente":
        assert "_apply_fabrication" in document
        document.remove("_apply_fabrication")
    else:
        assert len(document) >= 2, "moins de deux étapes documentées à échanger"
        document[0], document[1] = document[1], document[0]
    with pytest.raises(AssertionError):
        _verifier_meme_ordre_tick(code, document)


# --- service local ---
from contextlib import contextmanager
from http import HTTPStatus
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import ast
import threading
import time


@contextmanager
def lancer_service(seed: int, jours_par_seconde: float = 0):
    """Lance le vrai module HTTP, livre son port, puis l'arrête dans tous les cas."""
    processus = subprocess.Popen(
        [sys.executable, "-m", "sim.service", "--seed", str(seed), "--port", "0", "--jours-par-seconde", str(jours_par_seconde)],
        cwd=_REPO,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert processus.stdout is not None
        premiere_ligne = processus.stdout.readline().strip()
        prefixe = "service prêt sur 127.0.0.1:"
        assert premiere_ligne.startswith(prefixe), (
            f"première ligne inattendue : {premiere_ligne!r}"
        )
        port = int(premiere_ligne.removeprefix(prefixe))
        assert port > 0
        yield port
    finally:
        processus.terminate()
        try:
            processus.wait(timeout=5)
        except subprocess.TimeoutExpired:
            processus.kill()
            processus.wait(timeout=5)


def requete_service(
    port: int,
    chemin: str,
    methode: str = "GET",
    corps: bytes | None = None,
) -> tuple[HTTPStatus, dict, bytes]:
    """Parle HTTP au service et conserve aussi les octets canoniques reçus."""
    requete = Request(
        f"http://127.0.0.1:{port}{chemin}",
        data=corps,
        method=methode,
    )
    try:
        with urlopen(requete) as reponse:
            octets = reponse.read()
            statut = HTTPStatus(reponse.status)
            assert reponse.headers["Content-Length"] == str(len(octets))
    except HTTPError as erreur:
        octets = erreur.read()
        statut = HTTPStatus(erreur.code)
        assert erreur.headers["Content-Length"] == str(len(octets))
    return statut, json.loads(octets.decode("utf-8")), octets


def _photographie_cli(tmp_path: Path, seed: int, ticks: int) -> dict:
    destination = tmp_path / f"photographie-{seed}-{ticks}.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "sim",
            "--ticks",
            str(ticks),
            "--seed",
            str(seed),
            "--snapshot-json",
            str(destination),
        ],
        cwd=_REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(destination.read_text(encoding="utf-8"))


def _verifier_lieu_contre_photo(port: int, cellule: dict, ticks: int) -> None:
    from sim.constants import date_de_tick

    statut, lieu, _ = requete_service(port, f"/lieu?cell={cellule['cell_id']}")
    assert statut is HTTPStatus.OK
    assert lieu["cell_id"] == cellule["cell_id"]
    for champ in ("population", "stocks", "hunger_ticks", "food_deficit_kg"):
        assert lieu[champ] == cellule[champ]
    assert lieu["tick"] == ticks
    assert lieu["date"] == date_de_tick(ticks)


def test_service_lieu_rend_exactement_la_photographie_du_meme_tick(tmp_path: Path):
    seed = 0
    ticks = 3
    photo = _photographie_cli(tmp_path, seed, ticks)
    photo_suivante = _photographie_cli(tmp_path, seed, ticks + 1)
    suivantes = {cellule["cell_id"]: cellule for cellule in photo_suivante["cells"]}
    champs = ("population", "stocks", "hunger_ticks", "food_deficit_kg")
    temoin = next(
        (
            cellule
            for cellule in photo["cells"]
            if any(
                cellule[champ] != suivantes[cellule["cell_id"]][champ]
                for champ in champs
            )
        ),
        None,
    )
    assert temoin is not None, "échantillon vide : aucune cellule ne change au tick suivant"

    with lancer_service(seed) as port:
        assert requete_service(port, "/tick?n=1", "POST")[1]["tick"] == 1
        assert requete_service(port, "/tick?n=2", "POST")[1]["tick"] == ticks
        for cellule in photo["cells"]:
            _verifier_lieu_contre_photo(port, cellule, ticks)

        requete_service(port, "/tick?n=1", "POST")
        with pytest.raises(AssertionError):
            _verifier_lieu_contre_photo(port, temoin, ticks)
        _verifier_lieu_contre_photo(
            port,
            suivantes[temoin["cell_id"]],
            ticks + 1,
        )


def test_service_refuse_de_deviner_sans_avancer_le_monde():
    cell_id_absent = 999999
    ids_carte = {cellule["cell_id"] for cellule in World.lire_carte()["cellules"]}
    assert cell_id_absent not in ids_carte
    refus = (
        ("GET", f"/lieu?cell={cell_id_absent}", None, HTTPStatus.NOT_FOUND, str(cell_id_absent)),
        ("GET", "/lieu", None, HTTPStatus.BAD_REQUEST, "cell"),
        ("GET", "/lieu?cell=abc", None, HTTPStatus.BAD_REQUEST, "cell"),
        ("POST", "/tick", None, HTTPStatus.BAD_REQUEST, "n"),
        ("POST", "/tick?n=0", None, HTTPStatus.BAD_REQUEST, "n"),
        ("POST", "/tick?n=abc", None, HTTPStatus.BAD_REQUEST, "n"),
        ("POST", "/intention", b"[1]", HTTPStatus.BAD_REQUEST, "intention"),
        ("POST", "/intention", b"pas du json", HTTPStatus.BAD_REQUEST, "intention"),
    )
    with lancer_service(0) as port:
        for methode, chemin, corps, statut_attendu, texte in refus:
            statut, document, _ = requete_service(port, chemin, methode, corps)
            assert statut is statut_attendu
            assert texte in document["erreur"]
        assert requete_service(port, "/monde")[1]["tick"] == 0
        assert requete_service(port, "/tick?n=1", "POST")[1]["tick"] == 1


def test_service_monde_est_leger_et_intention_ne_mute_rien():
    nombre_carte = len(World.lire_carte()["cellules"])
    with lancer_service(0) as port:
        requete_service(port, "/tick?n=2", "POST")
        statut, monde, octets_avant = requete_service(port, "/monde")
        assert statut is HTTPStatus.OK
        assert monde["cell_count"] == nombre_carte == len(monde["cells"])
        assert [c["cell_id"] for c in monde["cells"]] == sorted(
            c["cell_id"] for c in monde["cells"]
        )
        for cellule in monde["cells"]:
            assert "geometry" not in cellule
            assert "centroid" not in cellule
            lieu = requete_service(port, f"/lieu?cell={cellule['cell_id']}")[1]
            assert lieu["population"] == cellule["population"]

        intention = json.dumps({"route": "essai"}).encode("utf-8")
        reponse = requete_service(port, "/intention", "POST", intention)[1]
        assert reponse == {"acceptee": True, "appliquee_au_tick": 2}
        assert requete_service(port, "/monde")[2] == octets_avant


def _imports_hors_bibliotheque_standard(source: str) -> set[str]:
    arbre = ast.parse(source)
    modules = set()
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in noeud.names)
        elif isinstance(noeud, ast.ImportFrom) and noeud.module:
            modules.add(noeud.module.split(".")[0])
    return modules - sys.stdlib_module_names - {"sim", "__future__"}


def test_service_depend_uniquement_de_la_bibliotheque_standard_et_de_sim():
    source = (_REPO / "sim" / "service.py").read_text(encoding="utf-8")
    assert _imports_hors_bibliotheque_standard(source) == set()
    assert _imports_hors_bibliotheque_standard("import requests") == {"requests"}


def _verifier_cadence_horloge(
    ticks: int,
    duree_s: float,
    vitesse: float,
    duree_tick_s: float,
    duree_requete_s: float,
) -> None:
    """Compare une cadence à sa tolérance entièrement dérivée des mesures."""
    ecart = abs(ticks - vitesse * duree_s)
    tolerance = 1 + vitesse * (duree_tick_s + duree_requete_s)
    assert duree_tick_s * vitesse < 1, (
        f"le tick dépasse son budget à {vitesse} jours/s : "
        f"{duree_tick_s * MILLISECONDES_PAR_SECONDE_TEST:.1f} ms"
    )
    assert ecart <= tolerance, (
        f"cadence observée hors tolérance : écart={ecart}, tolérance={tolerance}"
    )


MILLISECONDES_PAR_SECONDE_TEST = 1000
DUREE_PAUSE_TEST_S = 1.5
DUREE_OBSERVATION_HORLOGE_S = 2.5
DUREE_APRES_PAUSE_TEST_S = 1
VITESSE_HORLOGE_TEST = 4
BUDGET_TICK_ATTENDU_MS = 100
DELAI_DEMARRAGE_SERVICE_S = 5
NOMBRE_TICKS_LECTURE_CONCURRENTE = 10


def _verifier_lecture_non_bloquante(
    fin_lecture: float,
    fin_post: float,
    tick_lecture: int,
) -> None:
    """Vérifie qu'une lecture observe un tick intermédiaire avant le POST."""
    assert fin_lecture < fin_post
    assert 1 <= tick_lecture < NOMBRE_TICKS_LECTURE_CONCURRENTE


@pytest.mark.parametrize(
    "ticks,accepte",
    [(5, False), (20, False), (10, True)],
)
def test_horloge_controle_cadence_contre_epreuves(ticks: int, accepte: bool):
    """Le contrôle refuse une demi/double vitesse et accepte la cadence exacte."""
    try:
        _verifier_cadence_horloge(ticks, 2.5, 4, 0.05, 0.01)
    except AssertionError:
        resultat = False
    else:
        resultat = True
    assert resultat is accepte


def test_horloge_pause_vitesse_et_budget():
    """SC1 — pause exacte, cadence choisie, puis nouvelle pause exacte."""
    with lancer_service(0) as port:
        initiale = requete_service(port, "/horloge")[1]
        assert initiale["tick"] == 0
        assert initiale["duree_dernier_tick_ms"] == -1
        assert initiale["budget_tick_ms"] == BUDGET_TICK_ATTENDU_MS
        time.sleep(DUREE_PAUSE_TEST_S)
        assert requete_service(port, "/horloge")[1]["tick"] == 0

        changee = requete_service(
            port,
            f"/vitesse?jours_par_seconde={VITESSE_HORLOGE_TEST}",
            "POST",
        )[1]
        assert changee["jours_par_seconde"] == VITESSE_HORLOGE_TEST

        debut_requete = time.monotonic()
        debut = requete_service(port, "/horloge")[1]
        instant_debut = time.monotonic()
        requete_debut = instant_debut - debut_requete
        time.sleep(DUREE_OBSERVATION_HORLOGE_S)
        fin_requete = time.monotonic()
        fin = requete_service(port, "/horloge")[1]
        instant_fin = time.monotonic()
        requete_fin = instant_fin - fin_requete
        duree = instant_fin - instant_debut
        duree_tick_s = max(
            debut["duree_dernier_tick_ms"], fin["duree_dernier_tick_ms"]
        ) / MILLISECONDES_PAR_SECONDE_TEST
        _verifier_cadence_horloge(
            fin["tick"] - debut["tick"],
            duree,
            VITESSE_HORLOGE_TEST,
            duree_tick_s,
            max(requete_debut, requete_fin),
        )

        requete_service(port, "/vitesse?jours_par_seconde=0", "POST")
        pausee = requete_service(port, "/horloge")[1]["tick"]
        time.sleep(DUREE_APRES_PAUSE_TEST_S)
        assert requete_service(port, "/horloge")[1]["tick"] == pausee


@pytest.mark.parametrize(
    "fin_lecture,fin_post,tick_lecture,accepte",
    [(1.0, 2.0, 5, True), (3.0, 2.0, 5, False), (1.0, 2.0, 10, False)],
)
def test_horloge_controle_lecture_non_bloquante(
    fin_lecture: float,
    fin_post: float,
    tick_lecture: int,
    accepte: bool,
):
    """La preuve refuse une lecture tardive ou prise seulement au dernier tick."""
    try:
        _verifier_lecture_non_bloquante(fin_lecture, fin_post, tick_lecture)
    except AssertionError:
        resultat = False
    else:
        resultat = True
    assert resultat is accepte


def test_horloge_lectures_ne_bloquent_pas_sur_un_lot_de_ticks():
    """SC3 — monde et lieu restent lisibles avant la fin d'un POST long."""
    with lancer_service(0) as port:
        cell_id = min(c["cell_id"] for c in requete_service(port, "/monde")[1]["cells"])
        resultat_post: dict = {}

        def pousser_ticks() -> None:
            resultat_post["document"] = requete_service(
                port,
                f"/tick?n={NOMBRE_TICKS_LECTURE_CONCURRENTE}",
                "POST",
            )[1]
            resultat_post["fin"] = time.monotonic()

        fil = threading.Thread(target=pousser_ticks)
        fil.start()
        limite = time.monotonic() + DELAI_DEMARRAGE_SERVICE_S
        observation = None
        while time.monotonic() < limite:
            horloge = requete_service(port, "/horloge")[1]
            if horloge["tick"] >= 1:
                observation = horloge
                break
        assert observation is not None, "aucun premier tick publié dans le délai"
        limite += (
            NOMBRE_TICKS_LECTURE_CONCURRENTE
            * observation["duree_dernier_tick_ms"]
            / MILLISECONDES_PAR_SECONDE_TEST
        )
        lieu = requete_service(port, f"/lieu?cell={cell_id}")[1]
        fin_lecture_lieu = time.monotonic()
        monde = requete_service(port, "/monde")[1]
        fin_lecture_monde = time.monotonic()
        fil.join(timeout=max(0, limite - time.monotonic()))
        assert not fil.is_alive(), "le POST /tick n'a pas fini dans le délai dérivé"
        _verifier_lecture_non_bloquante(
            fin_lecture_lieu,
            resultat_post["fin"],
            lieu["tick"],
        )
        _verifier_lecture_non_bloquante(
            fin_lecture_monde,
            resultat_post["fin"],
            monde["tick"],
        )
        assert resultat_post["document"]["tick"] == NOMBRE_TICKS_LECTURE_CONCURRENTE


@pytest.mark.parametrize("valeur", [None, "abc", "-1", "nan", "inf"])
def test_horloge_refuse_vitesse_invalide_sans_muter(valeur: str | None):
    """SC4 — une vitesse invalide nomme le champ et sa valeur sans effet."""
    with lancer_service(0) as port:
        suffixe = "" if valeur is None else f"?jours_par_seconde={valeur}"
        statut, document, _ = requete_service(port, f"/vitesse{suffixe}", "POST")
        assert statut is HTTPStatus.BAD_REQUEST
        assert "jours_par_seconde" in document["erreur"]
        assert repr(valeur) in document["erreur"]
        horloge = requete_service(port, "/horloge")[1]
        assert horloge["jours_par_seconde"] == 0
        assert horloge["tick"] == 0


def test_horloge_cli_refuse_vitesse_negative_et_accepte_decimale():
    """SC4 — la CLI refuse avant disponibilité ; l'API accepte un fini positif."""
    processus = subprocess.run(
        [
            sys.executable,
            "-m",
            "sim.service",
            "--jours-par-seconde",
            "-1",
            "--port",
            "0",
        ],
        cwd=_REPO,
        capture_output=True,
        text=True,
    )
    assert processus.returncode != 0
    assert "service prêt" not in processus.stdout
    assert "jours_par_seconde" in processus.stderr
    assert "-1" in processus.stderr
    with lancer_service(0) as port:
        statut, document, _ = requete_service(
            port, "/vitesse?jours_par_seconde=2.5", "POST"
        )
        assert statut is HTTPStatus.OK
        assert document["jours_par_seconde"] == 2.5


def test_service_reponse_figee_du_pont_est_celle_du_service():
    """Lot #185 SC1 — le fichier figé que relit Unity est la réponse `/lieu` du service."""
    fige = (
        _REPO.parent
        / "3d" / "unity" / "Assets" / "ForgeLocal3D" / "Pont" / "Tests"
        / "lieu-graine0-tick3.json"
    ).read_bytes()
    assert len(json.loads(fige.decode("utf-8"))["stocks"]) >= 2
    with lancer_service(0) as port:
        assert requete_service(port, "/tick?n=3", "POST")[1]["tick"] == 3
        monde = requete_service(port, "/monde")[1]
        candidates = sorted(
            cellule["cell_id"]
            for cellule in monde["cells"]
            if len(cellule["stocks"]) >= 2
        )
        assert candidates, "échantillon vide : aucune cellule à deux marchandises au tick 3"
        chemin = f"/lieu?cell={candidates[0]}"
        statut, _, octets = requete_service(port, chemin)
        assert statut is HTTPStatus.OK
        assert octets == fige

        # Contre-épreuve : un tick de plus, et les octets ne sont plus ceux du fichier.
        requete_service(port, "/tick?n=1", "POST")
        assert requete_service(port, chemin)[2] != fige
