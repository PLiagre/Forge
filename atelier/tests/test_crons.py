"""La cadence : qui se réveille à quelle minute. Joué par bash, comme le cron."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from conftest import RACINE

PROFIL = RACINE / "atelier" / "crons" / "profils" / "jour.sh"
# Sous Windows, `bash` du PATH est souvent le lanceur de WSL : on prend Git Bash.
_GIT_BASH = Path("C:/Program Files/Git/bin/bash.exe")
BASH = str(_GIT_BASH) if sys.platform.startswith("win") and _GIT_BASH.exists() else shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None or (sys.platform.startswith("win") and not _GIT_BASH.exists()),
                                reason="pas de bash utilisable")


def _roles(quand: str, jour_semaine: str = "3") -> list[str]:
    # `date +%u` est remplacé : le lundi se choisit, il ne s'attend pas.
    script = f'date() {{ echo {jour_semaine}; }}; . "{PROFIL.as_posix()}"; roles_du_moment "{quand}"'
    fini = subprocess.run([BASH, "-c", script], capture_output=True, text=True, check=True)
    return fini.stdout.split()


@pytest.mark.parametrize("quand,roles", [
    ("06:45", ["veille"]),
    ("07:15", ["journal"]),
    ("07:20", ["pilote"]),
    ("07:21", []),
    ("07:22", ["pilote"]),
    ("00:00", ["pilote"]),
    ("23:58", ["pilote"]),
    ("23:59", []),
])
def test_qui_se_reveille(quand, roles):
    assert _roles(quand) == roles


def test_la_boussole_le_lundi_seulement():
    assert _roles("07:45", "1") == ["boussole"]
    assert _roles("07:45", "2") == []


def test_le_prochain_reveil():
    script = (f'. "{PROFIL.as_posix()}"; prochain_reveil 07:21; prochain_reveil 07:22; '
              'prochain_reveil 23:59; prochain_reveil 09:08')
    fini = subprocess.run([BASH, "-c", script], capture_output=True, text=True, check=True)
    assert fini.stdout.split("\n")[:4] == ["07:22 pilote", "07:24 pilote", "00:00 pilote", "09:10 pilote"]


def test_le_pilote_passe_toutes_les_deux_minutes():
    # Trente tours par heure, jamais deux minutes de suite : un tour sans agent
    # ne coûte que quelques lectures de GitHub.
    heure = [f"10:{m:02d}" for m in range(60)]
    tours = [q for q in heure if "pilote" in _roles(q)]
    assert len(tours) == 30
    assert all(int(q[-2:]) % 2 == 0 for q in tours)
