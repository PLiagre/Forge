"""
Ce qui tient la commande de bout en bout.

La porte de la V1 n'est pas une somme de tests unitaires : c'est
« une commande simule et affiche ». Ce fichier protège ce que seul
l'assemblage peut casser :

  - les trois vues lisent **la même** photographie, pas trois mondes ;
  - la commande refuse ce qu'elle ne peut pas faire, au lieu de rendre
    une sortie muette ;
  - le compte rendu porte de quoi rejouer et de quoi douter.

L'horizon est court exprès. Ce fichier ne mesure pas le monde — c'est le
travail de `sim/tests/` — il mesure que la plomberie tient.
"""

import json
from pathlib import Path

import pytest

from forge.__main__ import main

TICKS_COURTS = 3


def _jouer(tmp_path: Path, *args: str) -> tuple[int, Path]:
    sortie = tmp_path / "sortie"
    code = main([
        "--ticks", str(TICKS_COURTS),
        "--seed", "0",
        "--pas", "2",
        "--largeur", "64",
        "--sortie", str(sortie),
        *args,
    ])
    return code, sortie


def test_une_commande_simule_et_affiche(tmp_path):
    """
    La porte de la V1, en un test.

    Si celui-ci rougit, « lancer une simulation et l'afficher » ne marche
    plus — quelle que soit la couleur des tests unitaires.
    """
    code, sortie = _jouer(tmp_path)
    assert code == 0

    for nom in ("monde.json", "carte.png", "tableau.svg", "planche.html", "resume.json"):
        chemin = sortie / nom
        assert chemin.is_file(), f"{nom} n'a pas été écrit"
        assert chemin.stat().st_size > 0, f"{nom} est vide"


def test_les_vues_lisent_la_meme_photographie(tmp_path):
    """
    Une seule simulation, trois regards. Le tick et la graine du compte rendu
    doivent être ceux du snapshot — sinon une vue montre un autre monde, et
    c'est précisément ce que « une seule source de vérité » interdit.
    """
    _code, sortie = _jouer(tmp_path)
    resume = json.loads((sortie / "resume.json").read_text(encoding="utf-8"))
    monde = json.loads((sortie / "monde.json").read_text(encoding="utf-8"))

    assert resume["carte"]["tick"] == monde["tick"] == TICKS_COURTS
    assert resume["carte"]["seed"] == monde["seed"] == 0
    assert resume["carte"]["cellules"] == monde["cell_count"]
    assert resume["simulation"]["cellules"] == monde["cell_count"]


def test_le_compte_rendu_porte_le_plafond_de_survie(tmp_path):
    """
    Ce que la V1 promet en un chiffre : le monde nourrit ceux qu'il amorce.

    Le compte rendu le publie à chaque exécution, pour qu'une régression se
    voie dans la sortie et pas seulement dans une suite de tests.
    """
    _code, sortie = _jouer(tmp_path)
    resume = json.loads((sortie / "resume.json").read_text(encoding="utf-8"))
    plafond = resume["simulation"]["plafond_de_survie_a_l_amorcage"]
    assert plafond >= 1.0, (
        f"plafond {plafond:.4f} < 1 : la commande affiche un monde condamné."
    )


def test_le_monde_ne_s_effondre_pas_sur_l_horizon_de_la_commande(tmp_path):
    """
    Garde grossière contre le défaut qui a motivé la V1 : avant le lot 055,
    le monde perdait 86 % de ses habitants la première année. Sur trois
    ticks, une chute de plus d'un pour cent est déjà anormale.
    """
    _code, sortie = _jouer(tmp_path)
    part = json.loads((sortie / "resume.json").read_text(encoding="utf-8"))
    part = part["simulation"]["part_survivante"]
    assert part > 0.99, f"part survivante {part:.4f} : le monde s'effondre dès le départ."


def test_sans_chronique_saute_la_planche(tmp_path):
    """La planche rejoue le monde ; on doit pouvoir ne pas la payer."""
    code, sortie = _jouer(tmp_path, "--sans-chronique")
    assert code == 0
    assert not (sortie / "planche.html").exists()
    assert (sortie / "carte.png").is_file()


def test_un_horizon_negatif_est_refuse(tmp_path):
    assert main(["--ticks", "-1", "--sortie", str(tmp_path / "x")]) == 2


def test_un_pas_nul_est_refuse(tmp_path):
    assert main(["--ticks", "1", "--pas", "0", "--sortie", str(tmp_path / "x")]) == 2


def test_une_lecture_inconnue_est_refusee_avant_de_simuler(tmp_path):
    """argparse refuse la lecture : on ne joue pas 365 ticks pour rien."""
    with pytest.raises(SystemExit):
        main(["--lecture", "prosperite", "--sortie", str(tmp_path / "x")])
