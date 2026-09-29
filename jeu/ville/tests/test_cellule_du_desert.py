"""La cellule par défaut du lanceur se dérive de la carte (lot #120, SC1).

Le numéro attendu n'est écrit nulle part : ce test le recalcule lui-même,
indépendamment de `cellule_du_desert.choisir`.
"""

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

JEU = Path(__file__).resolve().parents[2]
RACINE = JEU.parent
REGLE = JEU / "ville" / "cellule_du_desert.py"
LANCEUR = RACINE / "pc" / "jouer.py"
MONDE = JEU / "data" / "world-1400.json"
CLE = "insolation_annuelle_mj_m2"
DIXIEME = 10
DELAI_SCRIPT_S = 60

if str(JEU) not in sys.path:
    sys.path.insert(0, str(JEU))


def _charger_regle():
    spec = importlib.util.spec_from_file_location("cellule_du_desert", REGLE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


regle = _charger_regle()


@pytest.fixture(scope="module")
def monde():
    return json.loads(MONDE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def attendue(monde):
    cellules = monde["cellules"]
    assert cellules, "world-1400.json ne déclare aucune cellule"
    return sorted(cellules, key=lambda c: (-c["climat"][CLE], c["cell_id"]))[0]


def _copie_legere(monde):
    """Une copie qui peut être modifiée, sans les géométries."""
    return {
        "cellules": [
            {"cell_id": c["cell_id"], "centroid": dict(c["centroid"]), "climat": dict(c["climat"])}
            for c in monde["cellules"]
        ]
    }


def test_choisir_rend_la_cellule_recalculee(monde, attendue):
    assert regle.choisir(monde) == attendue["cell_id"]
    assert regle.charger_et_choisir() == attendue["cell_id"]


def test_la_cellule_est_dans_le_dixieme_le_plus_au_sud(monde, attendue):
    latitudes = sorted(c["centroid"]["lat"] for c in monde["cellules"])
    dixieme_sud = latitudes[len(latitudes) // DIXIEME]
    assert attendue["centroid"]["lat"] <= dixieme_sud, (
        f"cellule {attendue['cell_id']} à {attendue['centroid']['lat']}° N, "
        f"au-dessus du 10e centile ({dixieme_sud}° N)"
    )


def test_le_lieu_est_vivant(attendue):
    from sim.world import World

    monde_moteur = World.charger(rng_seed=0)
    assert monde_moteur.cells[attendue["cell_id"]].population > 0


@pytest.mark.parametrize("chemin", [REGLE, LANCEUR], ids=lambda p: p.name)
def test_le_numero_n_est_pas_ecrit(chemin, attendue):
    texte = chemin.read_text(encoding="utf-8")
    assert re.search(rf"(?<!\d){attendue['cell_id']}(?!\d)", texte) is None, (
        f"{chemin.name} écrit le cell_id {attendue['cell_id']} en chiffres"
    )


def test_le_script_ecrit_le_cell_id(attendue):
    fini = subprocess.run(
        [sys.executable, "ville/cellule_du_desert.py"],
        cwd=JEU,
        capture_output=True,
        text=True,
        timeout=DELAI_SCRIPT_S,
    )
    assert fini.returncode == 0, fini.stderr
    assert fini.stdout.strip() == str(attendue["cell_id"])


def test_le_choix_suit_les_donnees(monde):
    copie = _copie_legere(monde)
    maximum = max(c["climat"][CLE] for c in copie["cellules"])
    nord = max(copie["cellules"], key=lambda c: c["centroid"]["lat"])
    nord["climat"][CLE] = maximum + 1
    assert regle.choisir(copie) == nord["cell_id"]


def test_egalite_rend_le_plus_petit_cell_id(monde):
    copie = _copie_legere(monde)
    maximum = max(c["climat"][CLE] for c in copie["cellules"])
    premiere, derniere = copie["cellules"][0], copie["cellules"][-1]
    premiere["climat"][CLE] = derniere["climat"][CLE] = maximum + 1
    assert regle.choisir(copie) == min(premiere["cell_id"], derniere["cell_id"])


def test_une_insolation_absente_se_declare(monde):
    copie = _copie_legere(monde)
    privee = copie["cellules"][-1]
    del privee["climat"][CLE]
    with pytest.raises(ValueError) as erreur:
        regle.choisir(copie)
    assert CLE in str(erreur.value)
    assert str(privee["cell_id"]) in str(erreur.value)


def test_une_carte_vide_se_declare():
    with pytest.raises(ValueError):
        regle.choisir({"cellules": []})
