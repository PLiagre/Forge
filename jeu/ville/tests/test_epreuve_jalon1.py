"""pc/epreuve_jalon1.py accepte le panneau égal et refuse le panneau décalé (lot #121, SC1).

Les photographies viennent de la vraie commande `sim` ; le texte du panneau se
construit ici au format de `PanneauLieu.Decrire`, à partir de leurs valeurs.
"""

import copy
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

NIVEAUX_JUSQU_A_JEU = 2  # tests/ → ville/ → jeu/
JEU = Path(__file__).resolve().parents[NIVEAUX_JUSQU_A_JEU]
RACINE = JEU.parent
EPREUVE = RACINE / "pc" / "epreuve_jalon1.py"
PANNEAU_CS = RACINE / "3d" / "unity" / "Assets" / "ForgeLocal3D" / "Pont" / "PanneauLieu.cs"
CAPTURE_CS = RACINE / "3d" / "unity" / "Assets" / "ForgeLocal3D" / "Editor" / "ForgeCapture.cs"
GRAINE = 0
TICK_AVANT = 3
TICK_APRES = TICK_AVANT + 1
CELLULE_SIMULEE = 1
TICK_SIMULE = 0
AGE_CAPTURE_ANTERIEURE_S = 120
PID_RESIDUEL = 4242
NOURRITURE = "nourriture"
MARCHANDISE_AJOUTEE = "sel de test"
CHAMPS_DU_MONDE = ("population", "hunger_ticks", "food_deficit_kg", "stocks.")
CHAMPS_DU_TEMPS = ("tick", "annee", "jour")

if str(JEU) not in sys.path:
    sys.path.insert(0, str(JEU))

from sim.constants import date_de_tick  # noqa: E402
from sim.service import DEFAULT_SERVICE_PORT  # noqa: E402


def _charger(nom, chemin):
    if not chemin.is_file():
        pytest.fail(f"fichier introuvable : {chemin}")
    spec = importlib.util.spec_from_file_location(nom, chemin)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def epreuve():
    return _charger("epreuve_jalon1", EPREUVE)


@pytest.fixture(scope="module")
def cellule():
    return _charger("cellule_du_desert", JEU / "ville" / "cellule_du_desert.py").charger_et_choisir()


@pytest.fixture(scope="module")
def photos(tmp_path_factory):
    dossier = tmp_path_factory.mktemp("photos")
    lues = {}
    for tick in (TICK_AVANT, TICK_APRES):
        chemin = dossier / f"photo-tick-{tick}.json"
        subprocess.run(
            [sys.executable, "-m", "sim", "--ticks", str(tick), "--seed", str(GRAINE), "--snapshot-json", str(chemin)],
            cwd=JEU, check=True, capture_output=True,
        )
        lues[tick] = json.loads(chemin.read_text(encoding="utf-8"))
    return lues


def _r(valeur):
    """Un double au format "R" invariant du C# : 0, 12.5, 1E+15."""
    texte = repr(float(valeur)).replace("e", "E")
    mantisse, _, exposant = texte.partition("E")
    mantisse = mantisse[:-len(".0")] if mantisse.endswith(".0") else mantisse
    if exposant and not exposant.startswith("-"):
        exposant = "+" + exposant.lstrip("+")
    return mantisse + ("E" + exposant if exposant else "")


def _etat(photo, cellule):
    return next(c for c in photo["cells"] if c["cell_id"] == cellule)


def _panneau(photo, cellule, tick_de=None):
    """Le texte de PanneauLieu.Decrire pour cette cellule ; tick et date pris à `tick_de` s'il est donné."""
    etat = _etat(photo, cellule)
    tick = (tick_de or photo)["tick"]
    date = date_de_tick(tick)
    stocks = etat["stocks"]
    lignes = [
        f"Cellule {cellule} · tick {tick}",
        f"Date : jour {date['jour_de_l_annee']} de {date['annee']}",
        f"Habitants : {etat['population']}",
        f"Nourriture : {_r(stocks[NOURRITURE]) + ' kg' if NOURRITURE in stocks else 'absente du panier'}",
    ]
    for nom in sorted((m for m in stocks if m != NOURRITURE), key=lambda m: m.encode("utf-16-be")):
        lignes.append(f"{nom} : {_r(stocks[nom])} kg")
    lignes.append(f"Faim : {etat['hunger_ticks']} ticks de manque")
    lignes.append(f"Dette de nourriture : {_r(etat['food_deficit_kg'])} kg")
    return "\n".join(lignes)


def _champs(ecarts):
    return [ecart.split(" : ", 1)[0] for ecart in ecarts]


def test_le_panneau_egal_ne_donne_aucun_ecart(epreuve, photos, cellule):
    photo = photos[TICK_AVANT]
    assert _etat(photo, cellule)["stocks"], f"la cellule {cellule} n'a aucune marchandise : l'échantillon est vide"
    assert epreuve.comparer(epreuve.lire_panneau(_panneau(photo, cellule)), photo, cellule) == []


def test_le_panneau_decale_d_un_tick_est_refuse(epreuve, photos, cellule):
    avant, apres = photos[TICK_AVANT], photos[TICK_APRES]
    monde = ("population", "stocks", "hunger_ticks", "food_deficit_kg")
    if all(_etat(avant, cellule)[c] == _etat(apres, cellule)[c] for c in monde):
        pytest.fail(f"la cellule {cellule} ne bouge pas entre les ticks {TICK_AVANT} et {TICK_APRES} : la preuve serait aveugle")
    champs = _champs(epreuve.comparer(epreuve.lire_panneau(_panneau(apres, cellule)), avant, cellule))
    assert "tick" in champs
    assert any(champ.startswith(CHAMPS_DU_MONDE) for champ in champs), champs


def test_les_nombres_comptent_pas_seulement_le_tick(epreuve, photos, cellule):
    avant, apres = photos[TICK_AVANT], photos[TICK_APRES]
    ecarts = epreuve.comparer(epreuve.lire_panneau(_panneau(apres, cellule, tick_de=avant)), avant, cellule)
    assert ecarts
    assert not [c for c in _champs(ecarts) if c in CHAMPS_DU_TEMPS], ecarts


def test_le_panier_se_compare_dans_les_deux_sens(epreuve, photos, cellule):
    photo = photos[TICK_AVANT]
    etat = _etat(photo, cellule)
    enrichie = copy.deepcopy(photo)
    _etat(enrichie, cellule)["stocks"][MARCHANDISE_AJOUTEE] = etat["stocks"][NOURRITURE] + 1
    # Une marchandise en trop sur le panneau, puis une marchandise que le panneau oublie.
    en_trop = epreuve.comparer(epreuve.lire_panneau(_panneau(enrichie, cellule)), photo, cellule)
    oubliee = epreuve.comparer(epreuve.lire_panneau(_panneau(photo, cellule)), enrichie, cellule)
    assert _champs(en_trop) == [f"stocks.{MARCHANDISE_AJOUTEE}"]
    assert _champs(oubliee) == [f"stocks.{MARCHANDISE_AJOUTEE}"]
    assert "absente du panier" in oubliee[0]

    texte = _panneau(photo, cellule)
    ligne = next(l for l in texte.split("\n") if l.startswith("Nourriture : "))
    retiree = texte.replace(ligne + "\n", "")
    absente = texte.replace(ligne, "Nourriture : absente du panier")
    for variante in (retiree, absente):
        lu = epreuve.lire_panneau(variante)
        assert NOURRITURE not in lu["stocks"]
        assert _champs(epreuve.comparer(lu, photo, cellule)) == [f"stocks.{NOURRITURE}"]


def test_la_dette_nulle_ecrite_0_n_est_pas_un_ecart(epreuve, photos, cellule):
    photo = copy.deepcopy(photos[TICK_AVANT])
    _etat(photo, cellule)["food_deficit_kg"] = 0.0
    texte = _panneau(photo, cellule)
    assert texte.endswith("Dette de nourriture : 0 kg")
    assert epreuve.comparer(epreuve.lire_panneau(texte), photo, cellule) == []


def test_les_formes_du_csharp_se_relisent(epreuve, photos, cellule):
    texte = _panneau(photos[TICK_AVANT], cellule)
    lu = epreuve.lire_panneau(texte.replace("Faim : ", f"{MARCHANDISE_AJOUTEE} : 1E+15 kg\nFaim : "))
    assert lu["stocks"][MARCHANDISE_AJOUTEE] == float("1E+15")


@pytest.mark.parametrize("texte", [
    "",
    "service absent : 127.0.0.1:8000 — lieu 9 : service absent sur 127.0.0.1:8000 (refus)",
    "lieu illisible : lieu 9 : statut 404 pour cell_id 9, corps reçu : {}",
    "service absent : en attente de 127.0.0.1:8000",
])
def test_une_absence_n_est_jamais_lue_comme_des_zeros(epreuve, texte):
    with pytest.raises(ValueError, match="panneau illisible"):
        epreuve.lire_panneau(texte)


def test_une_ligne_inconnue_est_refusee(epreuve, photos, cellule):
    texte = _panneau(photos[TICK_AVANT], cellule) + "\nHumeur : sereine"
    with pytest.raises(ValueError, match="Humeur"):
        epreuve.lire_panneau(texte)


def test_une_cellule_absente_de_la_photographie_se_nomme(epreuve, photos, cellule):
    photo = photos[TICK_AVANT]
    absente = max(c["cell_id"] for c in photo["cells"]) + 1
    lu = epreuve.lire_panneau(_panneau(photo, cellule))
    with pytest.raises(ValueError, match=f"cell_id {absente}"):
        epreuve.comparer(lu, photo, absente)


def test_les_libelles_sont_ceux_du_panneau(epreuve):
    if not PANNEAU_CS.is_file():
        pytest.fail(f"fichier introuvable : {PANNEAU_CS}")
    source = PANNEAU_CS.read_text(encoding="utf-8")
    manquants = [libelle for libelle in epreuve.LIBELLES if libelle not in source]
    assert not manquants, f"libellés absents de {PANNEAU_CS.name} : {manquants}"


def test_la_capture_lance_le_service_sur_le_port_du_panneau():
    if not CAPTURE_CS.is_file():
        pytest.fail(f"fichier introuvable : {CAPTURE_CS}")
    trouve = re.search(r"const int PORT_SERVICE = (\d+);", CAPTURE_CS.read_text(encoding="utf-8"))
    if trouve is None:
        pytest.fail(f"constante PORT_SERVICE introuvable dans {CAPTURE_CS.name}")
    assert int(trouve[1]) == DEFAULT_SERVICE_PORT


def test_un_unity_introuvable_sort_a_2_en_le_nommant(epreuve, tmp_path, capsys):
    absent = tmp_path / "pas-d-unity.exe"
    assert epreuve.main(["--sortie", str(tmp_path / "j1"), "--unity", str(absent)]) == epreuve.IMPOSSIBLE
    assert str(absent) in capsys.readouterr().err


def _photo_simulee(cellule, tick):
    return {
        "tick": tick,
        "cells": [{
            "cell_id": cellule,
            "population": 1,
            "hunger_ticks": 0,
            "food_deficit_kg": 0.0,
            "stocks": {NOURRITURE: 1.0},
        }],
    }


def _simuler_photographie(monkeypatch, epreuve, photo):
    def run(commande, **kwargs):
        if "-m" in commande and "sim" in commande:
            Path(commande[commande.index("--snapshot-json") + 1]).write_text(json.dumps(photo), encoding="utf-8")
            return subprocess.CompletedProcess(commande, 0, "", "")
        raise AssertionError(commande)
    monkeypatch.setattr(epreuve.subprocess, "run", run)


def _args_simules(tmp_path, sortie):
    unity = tmp_path / "Unity.exe"
    unity.write_bytes(b"")
    return ["--sortie", str(sortie), "--unity", str(unity), "--cellule", str(CELLULE_SIMULEE),
            "--ticks", str(TICK_SIMULE), "--seed", str(GRAINE)]


def _capture_anterieure(dossier, epreuve, photo):
    """Pose une capture déjà égale à la photographie, datée d'avant cet essai."""
    image = dossier / f"{epreuve.SCENE}.png"
    texte = dossier / f"{epreuve.SCENE}.panneau.txt"
    image.write_bytes(b"\x89PNG")
    texte.write_text(_panneau(photo, CELLULE_SIMULEE), encoding="utf-8")
    passe = time.time() - AGE_CAPTURE_ANTERIEURE_S
    os.utime(image, (passe, passe))
    os.utime(texte, (passe, passe))
    return image, texte


def test_une_capture_anterieure_ne_donne_pas_legalite(epreuve, tmp_path, monkeypatch, capsys):
    """Unity rend 0 sans rien écrire : l'ancien panneau, même égal, ne doit pas donner 0."""
    photo = _photo_simulee(CELLULE_SIMULEE, TICK_SIMULE)
    _simuler_photographie(monkeypatch, epreuve, photo)
    monkeypatch.setattr(epreuve.JOUER, "_repond", lambda port: False)
    monkeypatch.setattr(epreuve, "_unity", lambda commande: 0)
    sortie = tmp_path / "reprise"
    sortie.mkdir()
    _capture_anterieure(sortie, epreuve, photo)
    (sortie / "verdict.txt").write_text("ÉGALITÉ\n", encoding="utf-8")
    code = epreuve.main(_args_simules(tmp_path, sortie))
    capture = capsys.readouterr()
    assert code == epreuve.IMPOSSIBLE
    assert epreuve.SCENE in capture.err
    assert "ÉGALITÉ" not in capture.out
    verdict = sortie / "verdict.txt"
    assert not verdict.is_file() or not verdict.read_text(encoding="utf-8").startswith("ÉGALITÉ")


def test_un_fichier_laisse_avec_un_vieil_horodatage_ne_compte_pas(epreuve, tmp_path, monkeypatch, capsys):
    """Même présent après Unity, un fichier antérieur à l'essai n'est pas une capture."""
    photo = _photo_simulee(CELLULE_SIMULEE, TICK_SIMULE)
    _simuler_photographie(monkeypatch, epreuve, photo)
    monkeypatch.setattr(epreuve.JOUER, "_repond", lambda port: False)
    sortie = tmp_path / "horodatage"

    def unity(commande):
        dossier = Path(commande[commande.index("-forgeCaptures") + 1])
        _capture_anterieure(dossier, epreuve, photo)
        return 0

    monkeypatch.setattr(epreuve, "_unity", unity)
    code = epreuve.main(_args_simules(tmp_path, sortie))
    capture = capsys.readouterr()
    assert code == epreuve.IMPOSSIBLE
    assert "non produit pendant cet essai" in capture.err
    assert "ÉGALITÉ" not in capture.out


def test_une_capture_ecrite_pendant_lessai_peut_egaliser(epreuve, tmp_path, monkeypatch, capsys):
    photo = _photo_simulee(CELLULE_SIMULEE, TICK_SIMULE)
    _simuler_photographie(monkeypatch, epreuve, photo)
    monkeypatch.setattr(epreuve.JOUER, "_repond", lambda port: False)
    sortie = tmp_path / "frais"

    def unity(commande):
        dossier = Path(commande[commande.index("-forgeCaptures") + 1])
        (dossier / f"{epreuve.SCENE}.png").write_bytes(b"\x89PNG")
        (dossier / f"{epreuve.SCENE}.panneau.txt").write_text(_panneau(photo, CELLULE_SIMULEE), encoding="utf-8")
        return 0

    monkeypatch.setattr(epreuve, "_unity", unity)
    code = epreuve.main(_args_simules(tmp_path, sortie))
    assert code == epreuve.EGALITE
    assert (sortie / "verdict.txt").read_text(encoding="utf-8").startswith("ÉGALITÉ")
    capsys.readouterr()


@pytest.mark.parametrize("code_unity", [1, "délai dépassé"])
def test_toute_sortie_apres_lancement_ferme_le_service(epreuve, tmp_path, monkeypatch, capsys, code_unity):
    """Un Unity qui ne rend pas 0 doit quand même tuer le service qu'il a laissé."""
    photo = _photo_simulee(CELLULE_SIMULEE, TICK_SIMULE)
    _simuler_photographie(monkeypatch, epreuve, photo)
    reponses = iter([False, True])
    monkeypatch.setattr(epreuve.JOUER, "_repond", lambda port: next(reponses))
    tues = []
    monkeypatch.setattr(epreuve, "_tuer_pid", tues.append)
    sortie = tmp_path / "plante"

    def unity(commande):
        dossier = Path(commande[commande.index("-forgeCaptures") + 1])
        (dossier / "service.pid").write_text(str(PID_RESIDUEL), encoding="utf-8")
        return code_unity

    monkeypatch.setattr(epreuve, "_unity", unity)
    code = epreuve.main(_args_simules(tmp_path, sortie))
    assert code == epreuve.IMPOSSIBLE
    assert tues == [str(PID_RESIDUEL)]
    assert f"rendu {code_unity}" in capsys.readouterr().err
