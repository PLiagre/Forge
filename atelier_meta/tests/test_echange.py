"""Git-invisible et lisible : les deux, ou aucune."""

from pathlib import Path

import pytest

from atelier import echange


def test_deposer_et_relire(tmp_path: Path):
    source = tmp_path / "corps.json"
    source.write_text('{"verdict": "PASS"}', encoding="utf-8")
    cible = echange.deposer(tmp_path, source, "revue.json")
    assert cible.is_file()
    assert cible.read_text(encoding="utf-8") == '{"verdict": "PASS"}'
    assert echange.git_ignore_le_canal(tmp_path)


def test_garde_independante_du_depot(tmp_path: Path):
    echange.ouvrir(tmp_path)
    garde = echange.dossier(tmp_path) / ".gitignore"
    assert garde.read_text(encoding="utf-8") == "*\n"


def test_vide_refuse(tmp_path: Path):
    with pytest.raises(echange.EchangeErreur):
        echange.deposer_texte(tmp_path, "vide.txt", "   \n")


def test_retirer_n_est_pas_une_archive(tmp_path: Path):
    echange.deposer_texte(tmp_path, "prompt.txt", "exécute le brief")
    echange.retirer(tmp_path, "prompt.txt")
    assert not (echange.dossier(tmp_path) / "prompt.txt").exists()
