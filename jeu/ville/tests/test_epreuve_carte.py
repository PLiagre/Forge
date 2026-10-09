"""pc/epreuve_carte.py accepte la carte qui dit le monde servi et refuse celle qui s'en écarte (lot #527).

La carte servie est la fixture de la graine 0 (celle que lisent les tests du pont) ; le monde
servi se construit ici pour une cellule témoin. Le texte de la fiche se construit au format de
`FicheDeCellule.Decrire`, et le rapport au format d'`EpreuveCarte.Rapport`.
"""

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

NIVEAUX_JUSQU_A_JEU = 2  # tests/ → ville/ → jeu/
JEU = Path(__file__).resolve().parents[NIVEAUX_JUSQU_A_JEU]
RACINE = JEU.parent
EPREUVE = RACINE / "pc" / "epreuve_carte.py"
PONT = RACINE / "3d" / "unity" / "Assets" / "ForgeLocal3D" / "Pont"
FICHE_CS = PONT / "FicheDeCellule.cs"
EPREUVE_CS = RACINE / "3d" / "unity" / "Assets" / "ForgeLocal3D" / "Editor" / "EpreuveCarte.cs"
CARTE = PONT / "Tests" / "carte-graine0.json"
METZ = 10437
TICK = 30

if str(JEU) not in sys.path:
    sys.path.insert(0, str(JEU))


def _charger(nom, chemin):
    if not chemin.is_file():
        pytest.fail(f"fichier introuvable : {chemin}")
    spec = importlib.util.spec_from_file_location(nom, chemin)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def epreuve():
    return _charger("epreuve_carte", EPREUVE)


@pytest.fixture(scope="module")
def carte():
    return json.loads(CARTE.read_text(encoding="utf-8"))


@pytest.fixture
def monde():
    return {"tick": TICK, "date": {"annee": 1400, "jour_de_l_annee": TICK + 1}, "cell_count": 2,
            "cells": [{"cell_id": METZ, "population": 1234, "hunger_ticks": 2, "food_deficit_kg": 12.5},
                      {"cell_id": 1, "population": 0, "hunger_ticks": -1, "food_deficit_kg": -1}]}


def _nom(identite):
    return "aucune, le monde n'en nomme pas" if identite is None else identite["nom"]


def fiche(carte, monde, cellule, **changes):
    """Le texte que FicheDeCellule.Decrire écrit pour `cellule`, avec des nombres changés au besoin."""
    servie = next(c for c in carte["cells"] if c["cell_id"] == cellule)
    vivante = next(c for c in monde["cells"] if c["cell_id"] == cellule) | changes
    villes = ", ".join(v["nom"] for v in servie["villes"])
    faim = "non calculée" if vivante["hunger_ticks"] < 0 else f"{vivante['hunger_ticks']} ticks de manque"
    dette = "non calculée" if vivante["food_deficit_kg"] < 0 else f"{vivante['food_deficit_kg']!r} kg"
    return (f"Cellule {cellule}" + (f" · {villes}" if villes else "") + f"\nPuissance : {_nom(servie['puissance'])}"
            f"\nMaison : {_nom(servie['maison'])}\nHabitants : {vivante['population']} au tick {changes.get('tick', monde['tick'])}"
            f"\nFaim : {faim}\nDette de nourriture : {dette}")


def rapport(servie, texte, cellule=METZ, **changes):
    n = len(servie["cells"])
    return {"cellules_posees": n, "cellules_servies": n, "cellule": cellule, "survolee": cellule, "retiree": -1,
            "tick": TICK, "fiche": texte, "carte": "", "defaut": ""} | changes


def test_la_carte_qui_dit_le_monde_servi_est_egale(epreuve, carte, monde):
    egal, lignes = epreuve.juger(rapport(carte, fiche(carte, monde, METZ)), carte, monde, METZ)
    assert egal, lignes
    assert any(l.startswith("population : fiche 1234 · service 1234 · égal") for l in lignes)
    assert any(l.startswith("maison : fiche None · service None") for l in lignes), "le témoin d'une maison absente a changé"


def test_un_tick_de_decalage_est_refuse(epreuve, carte, monde):
    egal, lignes = epreuve.juger(rapport(carte, fiche(carte, monde, METZ, tick=TICK + 1)), carte, monde, METZ)
    assert not egal
    assert any(l.startswith("tick : fiche 31 · service 30 · ÉCART") for l in lignes), lignes


@pytest.mark.parametrize("champ, valeur", [("population", 1235), ("hunger_ticks", 3), ("food_deficit_kg", 12.25),
                                           ("hunger_ticks", -1), ("food_deficit_kg", -1)])
def test_chaque_nombre_compte(epreuve, carte, monde, champ, valeur):
    egal, lignes = epreuve.juger(rapport(carte, fiche(carte, monde, METZ, **{champ: valeur})), carte, monde, METZ)
    assert not egal
    assert any(l.startswith(f"{champ} : ") and l.endswith("ÉCART") for l in lignes), lignes


def test_une_faim_non_calculee_se_relit(epreuve, carte, monde):
    autre = next(c["cell_id"] for c in carte["cells"] if c["cell_id"] != METZ)
    monde = copy.deepcopy(monde)
    monde["cells"][1]["cell_id"] = autre
    egal, lignes = epreuve.juger(rapport(carte, fiche(carte, monde, autre), cellule=autre), carte, monde, autre)
    assert egal, lignes
    assert "hunger_ticks : fiche -1 · service -1 · égal" in lignes


def test_une_cellule_perdue_au_dessin_est_refusee(epreuve, carte, monde):
    n = len(carte["cells"])
    egal, lignes = epreuve.juger(rapport(carte, fiche(carte, monde, METZ), cellules_posees=n - 1), carte, monde, METZ)
    assert not egal
    assert lignes[0] == f"cellules dessinées : carte {n - 1} · /carte {n}"


def test_une_carte_qui_ne_se_pose_pas_est_un_ecart_qui_le_dit(epreuve, carte, monde):
    message = "le monde ne répond pas\ncarte : service absent sur 127.0.0.1:8000"
    egal, lignes = epreuve.juger(rapport(carte, "", cellules_posees=0, cellules_servies=-1, survolee=-1, carte=message),
                                 carte, monde, METZ)
    assert not egal
    assert lignes[-1] == f"la carte ne s'est pas posée : {message!r}"


def test_une_absence_du_monde_n_est_jamais_lue_comme_des_zeros(epreuve, carte, monde):
    texte = fiche(carte, monde, METZ).split("\nHabitants")[0] + "\nHabitants et faim : le monde ne répond pas (monde : service absent)"
    with pytest.raises(ValueError, match="fiche illisible"):
        epreuve.lire_fiche(texte)
    egal, lignes = epreuve.juger(rapport(carte, texte), carte, monde, METZ)
    assert not egal and lignes[-1].startswith("fiche illisible")


def test_la_fiche_d_une_autre_cellule_est_refusee(epreuve, carte, monde):
    egal, lignes = epreuve.juger(rapport(carte, fiche(carte, monde, METZ), survolee=1), carte, monde, METZ)
    assert not egal and lignes[-1] == f"cellule survolée 1, il fallait {METZ}"


def test_les_libelles_sont_ceux_de_la_fiche_et_du_rapport(epreuve):
    source = FICHE_CS.read_text(encoding="utf-8")
    for libelle in ("\"Cellule \"", "\"\\nPuissance : \"", "\"\\nMaison : \"", "\"\\nHabitants : \"", "\" au tick \"",
                    "\"\\nFaim : \"", "\" ticks de manque\"", "\"\\nDette de nourriture : \"", "\" kg\"",
                    f"\"{epreuve.AUCUNE}\"", f"\"{epreuve.NON_CALCULEE}\""):
        assert libelle in source, f"{libelle} absent de FicheDeCellule.cs"
    rapport_cs = EPREUVE_CS.read_text(encoding="utf-8")
    for cle in ("cellules_posees", "cellules_servies", "survolee", "retiree", "fiche", "carte", "defaut", "\"-forgeEpreuve\"",
                "\"-forgeEpreuveRetirer\""):
        assert cle in rapport_cs, f"{cle} absent d'EpreuveCarte.cs"
    espace, classe, methode = epreuve.METHODE.split(".")
    assert f"namespace {espace}" in rapport_cs and f"class {classe}" in rapport_cs and f"public static void {methode}()" in rapport_cs


def test_un_unity_introuvable_sort_a_2_en_le_nommant(epreuve, tmp_path, capsys):
    absent = tmp_path / "Unity.exe"
    assert epreuve.main(["--sortie", str(tmp_path / "sortie"), "--unity", str(absent)]) == epreuve.IMPOSSIBLE
    assert str(absent) in capsys.readouterr().err
