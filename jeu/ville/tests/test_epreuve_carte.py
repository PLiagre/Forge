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


def fiche(epreuve, carte, monde, cellule, bourg, jour=None, **changes):
    """Le texte que FicheDeCellule.Decrire(c, monde, nomDuBourg) écrit pour `cellule`, avec des nombres ou le jour changés au besoin."""
    servie = next(c for c in carte["cells"] if c["cell_id"] == cellule)
    vivante = next(c for c in monde["cells"] if c["cell_id"] == cellule) | changes
    villes = ", ".join(v["nom"] for v in servie["villes"] if v["nom"] != bourg)
    population = vivante["population"]
    faim = "non calculée" if vivante["hunger_ticks"] < 0 else epreuve.jours(vivante["hunger_ticks"]) + " de manque"
    dette = "non calculée" if vivante["food_deficit_kg"] < 0 else epreuve.masse(vivante["food_deficit_kg"])
    date = epreuve.date(monde["date"] | ({} if jour is None else {"jour_de_l_annee": jour}))
    return (bourg + (f" · {villes}" if villes else "") + f"\nPuissance : {_nom(servie['puissance'])}"
            f"\nMaison : {_nom(servie['maison'])}\nHabitants : {epreuve.nombre(population)} "
            f"{'habitant' if population in (0, 1) else 'habitants'} · {date}\nFaim : {faim}\nDette de nourriture : {dette}")


def terre(lieu, cellule, nom=None):
    """Le `/lieu` servi pour `cellule` : la fixture à la terre jugée, son rang 0 renommé au besoin."""
    lieu = copy.deepcopy(lieu)
    lieu["cell_id"] = cellule
    if nom is not None:
        next(l for l in lieu["lieux"] if l["rang"] == 0)["nom"] = nom
    return lieu


def rapport(servie, texte, cellule=METZ, **changes):
    n = len(servie["cells"])
    return {"cellules_posees": n, "cellules_servies": n, "cellule": cellule, "survolee": cellule, "retiree": -1,
            "tick": TICK, "fiche": texte, "carte": "", "defaut": ""} | changes


@pytest.fixture
def lieu_metz(lieu):
    return terre(lieu, METZ, "Metz")


def test_la_carte_qui_dit_le_monde_servi_est_egale(epreuve, carte, monde, lieu_metz):
    egal, lignes = epreuve.juger(rapport(carte, fiche(epreuve, carte, monde, METZ, "Metz")), carte, monde, lieu_metz, METZ)
    assert egal, lignes
    habitants = f"1{NBSP}234 habitants"
    assert any(l.startswith(f"habitants : fiche {habitants!r} · service {habitants!r} · égal") for l in lignes), lignes
    assert any(l.startswith("maison : fiche None · service None") for l in lignes), "le témoin d'une maison absente a changé"


def test_un_bourg_et_une_ville_se_lisent_ensemble(epreuve, carte, monde, lieu):
    lieu = terre(lieu, METZ)
    assert epreuve.bourg(lieu) == "Övre vik"
    egal, lignes = epreuve.juger(rapport(carte, fiche(epreuve, carte, monde, METZ, "Övre vik")), carte, monde, lieu, METZ)
    assert egal, lignes
    assert "villes : fiche ['Metz'] · service ['Metz'] · égal" in lignes


def test_un_jour_de_decalage_est_refuse(epreuve, carte, monde, lieu_metz):
    egal, lignes = epreuve.juger(rapport(carte, fiche(epreuve, carte, monde, METZ, "Metz", jour=TICK + 2)), carte, monde, lieu_metz, METZ)
    assert not egal
    assert any(l.startswith("date : fiche 'jour 32 de 1400' · service 'jour 31 de 1400' · ÉCART") for l in lignes), lignes


LIGNE_DU_CHAMP = {"population": "habitants", "hunger_ticks": "faim", "food_deficit_kg": "dette"}


@pytest.mark.parametrize("champ, valeur", [("population", 1235), ("hunger_ticks", 3), ("food_deficit_kg", 12.25),
                                           ("hunger_ticks", -1), ("food_deficit_kg", -1)])
def test_chaque_nombre_compte(epreuve, carte, monde, lieu_metz, champ, valeur):
    texte = fiche(epreuve, carte, monde, METZ, "Metz", **{champ: valeur})
    egal, lignes = epreuve.juger(rapport(carte, texte), carte, monde, lieu_metz, METZ)
    assert not egal
    assert any(l.startswith(f"{LIGNE_DU_CHAMP[champ]} : ") and l.endswith("ÉCART") for l in lignes), lignes


@pytest.mark.parametrize("premiere_ligne, attendu", [
    ("Övre vik · Metz", "bourg : fiche 'Övre vik' · service 'Metz' · ÉCART"),
    ("Bourg en lecture · Metz", "bourg : fiche None · service 'Metz' · ÉCART"),
    ("Metz · Metz", "villes : fiche ['Metz'] · service [] · ÉCART")])
def test_le_bourg_et_les_villes_comptent(epreuve, carte, monde, lieu_metz, premiere_ligne, attendu):
    texte = premiere_ligne + "\n" + fiche(epreuve, carte, monde, METZ, "Metz").split("\n", 1)[1]
    egal, lignes = epreuve.juger(rapport(carte, texte), carte, monde, lieu_metz, METZ)
    assert not egal
    assert attendu in lignes, lignes


def test_une_faim_non_calculee_se_relit(epreuve, carte, monde, lieu):
    autre = next(c["cell_id"] for c in carte["cells"] if c["cell_id"] != METZ)
    monde = copy.deepcopy(monde)
    monde["cells"][1]["cell_id"] = autre
    egal, lignes = epreuve.juger(rapport(carte, fiche(epreuve, carte, monde, autre, "Övre vik"), cellule=autre), carte, monde,
                                 terre(lieu, autre), autre)
    assert egal, lignes
    assert "faim : fiche 'non calculée' · service 'non calculée' · égal" in lignes
    assert "dette : fiche 'non calculée' · service 'non calculée' · égal" in lignes


def test_une_cellule_perdue_au_dessin_est_refusee(epreuve, carte, monde, lieu_metz):
    n = len(carte["cells"])
    egal, lignes = epreuve.juger(rapport(carte, fiche(epreuve, carte, monde, METZ, "Metz"), cellules_posees=n - 1), carte, monde,
                                 lieu_metz, METZ)
    assert not egal
    assert lignes[0] == f"cellules dessinées : carte {n - 1} · /carte {n}"


def test_une_carte_qui_ne_se_pose_pas_est_un_ecart_qui_le_dit(epreuve, carte, monde, lieu_metz):
    message = "le monde ne répond pas\ncarte : service absent sur 127.0.0.1:8000"
    egal, lignes = epreuve.juger(rapport(carte, "", cellules_posees=0, cellules_servies=-1, survolee=-1, carte=message),
                                 carte, monde, lieu_metz, METZ)
    assert not egal
    assert lignes[-1] == f"la carte ne s'est pas posée : {message!r}"


def test_une_absence_du_monde_n_est_jamais_lue_comme_des_zeros(epreuve, carte, monde, lieu_metz):
    texte = fiche(epreuve, carte, monde, METZ, "Metz").split("\nHabitants")[0] + "\nHabitants et faim : déclaré absent par le monde"
    with pytest.raises(ValueError, match="fiche illisible"):
        epreuve.lire_fiche(texte)
    egal, lignes = epreuve.juger(rapport(carte, texte), carte, monde, lieu_metz, METZ)
    assert not egal and lignes[-1].startswith("fiche illisible")


def test_l_ancienne_fiche_en_identifiants_et_en_ticks_est_illisible(epreuve, carte, monde, lieu_metz):
    texte = ("Cellule 10437 · Metz\nPuissance : Archevêché de Trèves\nMaison : aucune, le monde n'en nomme pas\n"
             "Habitants : 1234 au tick 30\nFaim : 2 ticks de manque\nDette de nourriture : 12.5 kg")
    with pytest.raises(ValueError, match="fiche illisible"):
        epreuve.lire_fiche(texte)
    egal, lignes = epreuve.juger(rapport(carte, texte), carte, monde, lieu_metz, METZ)
    assert not egal and lignes[-1].startswith("fiche illisible")


def test_la_fiche_d_une_autre_cellule_est_refusee(epreuve, carte, monde, lieu_metz):
    egal, lignes = epreuve.juger(rapport(carte, fiche(epreuve, carte, monde, METZ, "Metz"), survolee=1), carte, monde, lieu_metz, METZ)
    assert not egal and lignes[-1] == f"cellule survolée 1, il fallait {METZ}"


def test_un_lieu_d_une_autre_terre_est_dit_avec_les_deux_identifiants(epreuve, carte, monde, lieu):
    with pytest.raises(ValueError, match="9922") as exc:
        epreuve.references(carte, monde, lieu, METZ)
    assert "10437" in str(exc.value)


def test_un_lieu_d_une_autre_terre_rend_l_epreuve_impossible_avant_unity(epreuve, carte, monde, lieu, tmp_path, capsys, monkeypatch):
    services = {"/carte": carte, "/monde": monde, f"/lieu?cell={METZ}": lieu}

    def unity_interdit(*_):
        pytest.fail("Unity a été lancé avec un /lieu d'une autre terre")

    monkeypatch.setattr(epreuve.JOUER, "_repond", lambda *_: False)
    monkeypatch.setattr(epreuve, "_lancer_service", lambda *_: None)
    monkeypatch.setattr(epreuve, "_requete", lambda methode, chemin: services.get(chemin, {}) if methode == "GET" else {})
    monkeypatch.setattr(epreuve.JALON1, "_unity", unity_interdit)
    unity = tmp_path / "Unity.exe"
    unity.write_bytes(b"")
    assert epreuve.main(["--sortie", str(tmp_path / "sortie"), "--unity", str(unity), "--cellule", str(METZ)]) == epreuve.IMPOSSIBLE
    erreur = capsys.readouterr().err
    assert "9922" in erreur and "10437" in erreur


def test_les_libelles_sont_ceux_de_la_fiche_et_du_rapport(epreuve):
    source = FICHE_CS.read_text(encoding="utf-8")
    for libelle in ("\"Bourg en lecture\"", "\" · \"", "\"\\nPuissance : \"", "\"\\nMaison : \"", "\"\\nHabitants : \"",
                    "\" habitant\"", "\" habitants\"", "\"\\nFaim : \"", "\" de manque\"", "\"\\nDette de nourriture : \"",
                    f"\"{epreuve.AUCUNE}\"", f"\"{epreuve.NON_CALCULEE}\"", "TexteDuMonde.Nombre(vivante.Population)",
                    "TexteDuMonde.Date(m.Date)", "TexteDuMonde.Jours(vivante.HungerTicks)", "TexteDuMonde.Masse(vivante.FoodDeficitKg)"):
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


# Lot #911 — le juge écrit comme le clerc : les tables sont celles de TexteDuMondeTests.cs, à l'octet.
NBSP = " "
TEXTE_CS = PONT / "Tests" / "TexteDuMondeTests.cs"
LIEU = PONT / "Tests" / "lieu-graine0-tick3.json"
NOMBRES = [(5631, f"5{NBSP}631"), (-5631, f"-5{NBSP}631"), (1234567, f"1{NBSP}234{NBSP}567"), (12, "12")]
JOURS = [(0, "0 jour"), (1, "1 jour"), (12, "12 jours"), (1234, f"1{NBSP}234 jours")]
DATES = [((1400, 8), "jour 8 de 1400"), ((1401, 1), "jour 1 de 1401"), ((1400, 366), "jour 366 de 1400")]
MASSES = [(0, "0 kg"), (12.5, "12,5 kg"), (999.5, "999,5 kg"), (999.996, "1,00 t"), (1000, "1,00 t"), (1234.5, "1,23 t"),
          (9996, "10,0 t"), (41712, "41,7 t"), (99960, "100 t"), (123456, "123 t"), (5631000, f"5{NBSP}631 t"), (-1234.5, "-1,23 t")]


def _date(annee, jour):
    return {"annee": annee, "jour_de_l_annee": jour}


@pytest.mark.parametrize("n, ecrit", NOMBRES)
def test_nombre_groupe_par_trois_avec_une_espace_insecable(epreuve, n, ecrit):
    assert epreuve.nombre(n) == ecrit


@pytest.mark.parametrize("n", [True, 12.0, "12", None])
def test_nombre_refuse_ce_qui_n_est_pas_un_entier(epreuve, n):
    with pytest.raises(TypeError):
        epreuve.nombre(n)


@pytest.mark.parametrize("n, ecrit", JOURS)
def test_jours_s_accordent(epreuve, n, ecrit):
    assert epreuve.jours(n) == ecrit


def test_jours_refuse_une_duree_negative(epreuve):
    with pytest.raises(ValueError):
        epreuve.jours(-1)


@pytest.mark.parametrize("d, ecrit", DATES)
def test_date_s_ecrit_en_jour_de_l_annee(epreuve, d, ecrit):
    assert epreuve.date(_date(*d)) == ecrit


@pytest.mark.parametrize("d", [_date(1400, 0), _date(1400, 367), _date(0, 8), {"jour_de_l_annee": 8}, {"annee": 1400},
                               _date(1400.0, 8), _date(1400, "8"), _date(True, 8), _date(1400, None), {}])
def test_date_refuse_ce_que_le_monde_ne_sert_pas(epreuve, d):
    with pytest.raises(ValueError):
        epreuve.date(d)


@pytest.mark.parametrize("kg, ecrit", MASSES)
def test_masse_est_celle_du_clerc(epreuve, kg, ecrit):
    assert epreuve.masse(kg) == ecrit


@pytest.mark.parametrize("kg, ecrit", [(0.125, "0,13 kg"), (1125, "1,13 t"), (10250, "10,3 t"), (100500, "101 t"), (-0.001, "0 kg")])
def test_les_moities_montent(epreuve, kg, ecrit):
    assert epreuve.masse(kg) == ecrit


@pytest.mark.parametrize("kg", [float("nan"), float("inf"), float("-inf")])
def test_masse_refuse_un_nombre_non_fini(epreuve, kg):
    with pytest.raises(ValueError):
        epreuve.masse(kg)


def test_aucun_ecrit_ne_porte_d_espace_ordinaire_dans_un_nombre_ni_u202f(epreuve):
    ecrits = [epreuve.nombre(n) for n, _ in NOMBRES] + [epreuve.masse(kg) for kg, _ in MASSES] + [epreuve.jours(n) for n, _ in JOURS]
    assert all(" " not in e for e in ecrits)
    assert all(" " not in e.split(" ")[0] for e in ecrits), "un nombre porte une espace ordinaire"


def _ecrit_cs(ecrit):
    return ecrit.replace(NBSP, '" + NBSP + "')


def test_les_tables_du_juge_sont_celles_de_texte_du_monde_tests():
    source = TEXTE_CS.read_text(encoding="utf-8")
    manquants = []
    for kg, ecrit in MASSES:
        cas = f'({kg!r}, "{_ecrit_cs(ecrit)}")'
        if cas not in source:
            manquants.append(cas)
    for n, ecrit in NOMBRES:
        manquants += [c for c in [f'Assert.AreEqual("{_ecrit_cs(ecrit)}", TexteDuMonde.Nombre({n}))'] if c not in source]
    for n, ecrit in JOURS:
        manquants += [c for c in [f'Assert.AreEqual("{_ecrit_cs(ecrit)}", TexteDuMonde.Jours({n}))'] if c not in source]
    for (annee, jour), ecrit in DATES:
        manquants += [c for c in [f'Assert.AreEqual("{ecrit}", TexteDuMonde.Date(new DateDuMonde({annee}, {jour})))'] if c not in source]
    assert not manquants, f"cas absents de TexteDuMondeTests.cs : {manquants}"


@pytest.fixture
def lieu():
    return json.loads(LIEU.read_text(encoding="utf-8"))


def test_le_bourg_est_le_lieu_de_rang_0(epreuve, lieu):
    assert epreuve.bourg(lieu) == "Övre vik"
    lieu["lieux"].reverse()
    assert lieu["lieux"][0]["rang"] != 0
    assert epreuve.bourg(lieu) == "Övre vik", "le rang compte, pas la place"


def _sans_rang_0(lieu):
    lieu["lieux"] = [l for l in lieu["lieux"] if l["rang"] != 0]


def _deux_rangs_0(lieu):
    lieu["lieux"][1]["rang"] = 0


def _sans_cle(lieu):
    del lieu["lieux"]


def _pas_une_liste(lieu):
    lieu["lieux"] = {"rang": 0}


@pytest.mark.parametrize("abime", [_sans_rang_0, _deux_rangs_0, _sans_cle, _pas_une_liste])
def test_un_bourg_introuvable_ou_double_est_dit(epreuve, lieu, abime):
    abime(lieu)
    with pytest.raises(ValueError, match="rang 0"):
        epreuve.bourg(lieu)


def _rang_0(lieu):
    return next(l for l in lieu["lieux"] if l["rang"] == 0)


@pytest.mark.parametrize("nom", ["<retire>", None, "", "  ", 12])
def test_un_nom_de_bourg_absent_ou_blanc_est_dit(epreuve, lieu, nom):
    if nom == "<retire>":
        del _rang_0(lieu)["nom"]
    else:
        _rang_0(lieu)["nom"] = nom
    with pytest.raises(ValueError, match="nom du rang 0"):
        epreuve.bourg(lieu)


def test_le_bourg_ne_modifie_pas_ce_qu_il_lit(epreuve, lieu):
    avant = copy.deepcopy(lieu)
    epreuve.bourg(lieu)
    assert lieu == avant
