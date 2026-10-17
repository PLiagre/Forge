"""pc/epreuve_moree.py accepte la session qui fait retenir la Morée au monde et refuse celle qui s'en écarte (lot #652).

`/departs` est la fixture servie de la graine 0 (celle que lisent les tests du pont), ramenée au tick 0 ; `/monde`
avant et après le tick se construit ici. Les rapports sont ceux que la session de #651 a versés, ou construits au
format d'`EpreuveChoix.Rapport` avec les textes de `ReperesDeDepart.DireLeChoix`.
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
EPREUVE = RACINE / "pc" / "epreuve_moree.py"
UNITY = RACINE / "3d" / "unity" / "Assets" / "ForgeLocal3D"
REPERES_CS = UNITY / "Pont" / "ReperesDeDepart.cs"
EPREUVE_CS = UNITY / "Editor" / "EpreuveChoix.cs"
INTENTIONS = JEU / "sim" / "intentions.py"
DEPARTS = UNITY / "Pont" / "Tests" / "departs-graine0-tick3.json"
RAPPORTS = RACINE / "docs" / "mesures" / "651-session-choix-moree"
BAR, MOREE, ZAB = 1, 3, 6

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
    return _charger("epreuve_moree", EPREUVE)


@pytest.fixture
def departs():
    servi = json.loads(DEPARTS.read_text(encoding="utf-8"))
    servi["tick"] = 0
    return servi


def _monde(tick, maison=None):
    monde = {"tick": tick, "date": {"annee": 1400, "jour_de_l_annee": tick + 1}, "cell_count": 0, "cells": []}
    return monde if maison is None else monde | {"maison_du_joueur": maison}


AVANT = _monde(0)


def _verse(nom):
    return json.loads((RAPPORTS / nom).read_text(encoding="utf-8"))


def _nom(departs, ident):
    return next(f["nom"] for f in departs["departs"] if f["id"] == ident)


def rapport_zab(departs):
    """Ce que rend la session pour `-forgeTerre 6 -forgeSecondeTerre 1` : le Zab accepté, Bar refusé."""
    refus = "départ déjà choisi : seigneurie-6"
    return {"terre": ZAB, "seconde_terre": BAR, "tick_avant": 0, "tick_apres": 0, "reperes": 6,
            "premier": {"statut": 200, "tick": 0, "raison": ""}, "second": {"statut": 409, "tick": -1, "raison": refus},
            "premier_texte": f"Terre choisie : {_nom(departs, ZAB)}\nLe monde l'applique au tick suivant (après le tick 0).",
            "second_texte": f"Choix refusé pour {_nom(departs, BAR)} :\n{refus}", "defaut": ""}


def _ligne(lignes, debut):
    trouvees = [l for l in lignes if l.startswith(debut)]
    assert len(trouvees) == 1, lignes
    return trouvees[0]


def test_la_session_versee_qui_fait_retenir_la_moree_est_egale(epreuve, departs):
    egal, lignes = epreuve.juger(_verse("rapport-normal.json"), departs, AVANT, _monde(1, "seigneurie-3"))
    assert egal, lignes
    assert len(lignes) == 8 and all(l.endswith(" · égal") for l in lignes), lignes
    assert _ligne(lignes, "maison après le tick") == "maison après le tick : /monde 'seigneurie-3' · attendu 'seigneurie-3' · égal"


def test_la_contre_epreuve_du_zab_rougit_par_le_monde(epreuve, departs):
    egal, lignes = epreuve.juger(rapport_zab(departs), departs, AVANT, _monde(1, "seigneurie-6"))
    assert not egal
    assert _ligne(lignes, "premier reçu").endswith(" · égal"), "le Zab est bien accepté au tick 0"
    for debut, cite in (("second reçu", "seigneurie-6"), ("maison après le tick", "seigneurie-6"), ("premier texte", "Émirat du Zab")):
        ligne = _ligne(lignes, debut)
        assert ligne.endswith("ÉCART") and cite in ligne, ligne


def test_deux_refus_sont_un_ecart_sur_le_premier_recu(epreuve, departs):
    egal, lignes = epreuve.juger(_verse("rapport-deja-choisi.json"), departs, AVANT, _monde(1, "seigneurie-1"))
    assert not egal
    assert _ligne(lignes, "premier reçu").endswith("ÉCART")


def test_une_maison_deja_retenue_avant_le_tick_est_un_ecart(epreuve, departs):
    egal, lignes = epreuve.juger(_verse("rapport-normal.json"), departs, _monde(0, "seigneurie-3"), _monde(1, "seigneurie-3"))
    assert not egal
    assert _ligne(lignes, "maison avant le tick") == "maison avant le tick : /monde 'seigneurie-3' · attendu None · ÉCART"


def test_une_session_qui_fait_avancer_le_monde_est_un_ecart(epreuve, departs):
    rapport = _verse("rapport-normal.json") | {"tick_apres": 1}
    egal, lignes = epreuve.juger(rapport, departs, AVANT, _monde(1, "seigneurie-3"))
    assert not egal
    assert _ligne(lignes, "tick de la session") == "tick de la session : avant 0 · après 1 · /departs 0 · ÉCART"


def test_un_tick_pousse_qui_ne_vient_pas_est_un_ecart(epreuve, departs):
    egal, lignes = epreuve.juger(_verse("rapport-normal.json"), departs, AVANT, _monde(0))
    assert not egal
    assert _ligne(lignes, "tick après la poussée").endswith("ÉCART")
    assert _ligne(lignes, "maison après le tick").endswith("ÉCART")


@pytest.mark.parametrize("ligne, change", [
    ("premier texte", lambda r: r | {"premier_texte": r["premier_texte"].replace("après le tick 0", "après le tick 1")}),
    ("second texte", lambda r: r | {"second_texte": r["second_texte"].replace(" :\n", " : ")}),
    ("second reçu", lambda r: r | {"second": r["second"] | {"raison": "départ déjà choisi : seigneurie-1"}}),
])
def test_le_texte_est_juge_mot_pour_mot(epreuve, departs, ligne, change):
    rapport = change(copy.deepcopy(_verse("rapport-normal.json")))
    egal, lignes = epreuve.juger(rapport, departs, AVANT, _monde(1, "seigneurie-3"))
    assert not egal
    assert _ligne(lignes, ligne).endswith("ÉCART")
    assert [l for l in lignes if l.endswith("ÉCART")] == [_ligne(lignes, ligne)], lignes


def test_un_defaut_de_la_session_est_un_ecart_qui_le_dit(epreuve, departs):
    defaut = "repères : 0 posés sur 6 en 30 s"
    rapport = _verse("rapport-normal.json") | {"defaut": defaut}
    egal, lignes = epreuve.juger(rapport, departs, AVANT, _monde(1, "seigneurie-3"))
    assert not egal
    assert lignes[-1].startswith("défaut : ") and defaut in lignes[-1]


def test_les_terres_se_lisent_dans_departs(epreuve, departs):
    ids = lambda trio: tuple(f["id"] for f in trio)  # noqa: E731
    assert ids(epreuve.terres(departs, None)) == (MOREE, MOREE, BAR)
    assert ids(epreuve.terres(departs, ZAB)) == (MOREE, ZAB, BAR)
    with pytest.raises(ValueError):
        epreuve.terres(departs, 99)
    sans_moree = departs | {"departs": [f for f in departs["departs"] if f["nom"] != epreuve.MOREE]}
    with pytest.raises(ValueError):
        epreuve.terres(sans_moree, None)


def test_la_moree_se_trouve_par_son_nom(epreuve, departs):
    """Une Morée servie sous un autre id reste la Morée : l'attendu suit le nom, jamais l'id 3."""
    for fiche in departs["departs"]:
        if fiche["id"] == MOREE:
            fiche["id"] = 33
    moree, cliquee, seconde = epreuve.terres(departs, None)
    assert (moree["id"], cliquee["id"], seconde["id"]) == (33, 33, BAR)
    egal, lignes = epreuve.juger(_verse("rapport-normal.json"), departs, AVANT, _monde(1, "seigneurie-3"))
    assert not egal and _ligne(lignes, "maison après le tick").endswith("attendu 'seigneurie-33' · ÉCART")


def _litteral_cs(texte):
    return texte.replace("\n", "\\n")


def test_les_libelles_sont_ceux_du_panneau_du_service_et_de_la_session(epreuve):
    sources = REPERES_CS.read_text(encoding="utf-8") + INTENTIONS.read_text(encoding="utf-8")
    for morceau in (epreuve.TERRE_CHOISIE, epreuve.APPLIQUE, epreuve.FIN_APPLIQUE, epreuve.CHOIX_REFUSE,
                    epreuve.SUITE_REFUS, epreuve.DEJA_CHOISI):
        assert f"\"{_litteral_cs(morceau)}\"" in sources or morceau in sources, f"{morceau!r} absent de ReperesDeDepart.cs et d'intentions.py"
    session = EPREUVE_CS.read_text(encoding="utf-8")
    for cle in ("tick_avant", "tick_apres", "premier", "second", "premier_texte", "second_texte", "defaut",
                "\"-forgeEpreuve\"", "\"-forgeTerre\"", "\"-forgeSecondeTerre\""):
        assert cle in session, f"{cle} absent d'EpreuveChoix.cs"
    espace, classe, methode = epreuve.METHODE.split(".")
    assert f"namespace {espace}" in session and f"class {classe}" in session and f"public static void {methode}()" in session


def test_un_unity_introuvable_sort_a_2_en_le_nommant(epreuve, tmp_path, capsys):
    absent = tmp_path / "Unity.exe"
    assert epreuve.main(["--sortie", str(tmp_path / "sortie"), "--unity", str(absent)]) == epreuve.IMPOSSIBLE
    assert str(absent) in capsys.readouterr().err
