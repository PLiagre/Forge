"""Deux lots ne tiennent pas le même fichier. Un verrou vide échoue."""

from pathlib import Path

import pytest

from atelier import verrou


def test_poser_et_lire(tmp_path: Path):
    pose = verrou.poser(tmp_path, "044-mineur", ["sim/engine.py", "sim/constants.py"])
    assert "sim/engine.py" in pose.fichiers
    tableau = verrou.charger(tmp_path)
    assert len(tableau.poses) == 1


def test_collision(tmp_path: Path):
    verrou.poser(tmp_path, "044-mineur", ["sim/engine.py"])
    with pytest.raises(verrou.Collision, match="044-mineur"):
        verrou.poser(tmp_path, "046-mer", ["sim/engine.py", "sim/world.py"])


def test_perimetres_disjoints_passent(tmp_path: Path):
    verrou.poser(tmp_path, "044-mineur", ["sim/engine.py"])
    verrou.poser(tmp_path, "047-bourg", ["sim/aggregation.py"])
    assert len(verrou.charger(tmp_path).poses) == 2


def test_verrou_sans_fichier_echoue(tmp_path: Path):
    with pytest.raises(verrou.Collision):
        verrou.poser(tmp_path, "vide", [])


def test_fichier_vide_echoue(tmp_path: Path):
    cible = tmp_path / ".atelier"
    cible.mkdir()
    (cible / "verrous.json").write_text("[]\n", encoding="utf-8")
    with pytest.raises(verrou.Collision, match="vide"):
        verrou.charger(tmp_path)


def test_lever(tmp_path: Path):
    verrou.poser(tmp_path, "044-mineur", ["sim/engine.py"])
    verrou.lever(tmp_path, "044-mineur")
    assert verrou.charger(tmp_path).poses == []
