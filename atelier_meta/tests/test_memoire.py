"""ADD-only : une leçon ne s'écrase pas. Un vide échoue."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from atelier import memoire


def test_ajouter(tmp_path: Path):
    cible = memoire.ajouter(tmp_path, "Incident quota", "Le lot 035 a brûlé sans livrer.")
    assert cible.is_file()
    assert "035" in cible.read_text(encoding="utf-8")


def test_vide_refuse(tmp_path: Path):
    with pytest.raises(ValueError):
        memoire.ajouter(tmp_path, "   ", "corps")
    with pytest.raises(ValueError):
        memoire.ajouter(tmp_path, "titre", "  \n")


def test_pas_deux_fois_le_meme_fichier(tmp_path: Path, monkeypatch):
    class Horloge:
        timezone = timezone

        @staticmethod
        def now(tz=None):
            return datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(memoire, "datetime", Horloge)
    memoire.ajouter(tmp_path, "meme-titre", "une")
    with pytest.raises(FileExistsError):
        memoire.ajouter(tmp_path, "meme-titre", "deux")
