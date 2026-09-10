"""CLI : couches, hop, doctor."""

from pathlib import Path
import subprocess
import sys

from tests.test_cycle import _produit


def _atelier(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "atelier", *args],
        capture_output=True,
        text=True,
    )


def test_couches_vertes():
    proc = _atelier("couches")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.count("PASS") == 7


def test_hop_choisit():
    proc = _atelier("hop", "claude=-1", "cursor=40", "codex=5")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "cursor"


def test_hop_inconnu_refuse():
    proc = _atelier("hop", "claude=-1", "cursor=-1")
    assert proc.returncode == 1
    assert "inconnu" in proc.stderr


def test_doctor(tmp_path: Path):
    racine = _produit(tmp_path)
    proc = _atelier("doctor", "--projet", str(racine))
    assert proc.returncode == 0, proc.stderr
    assert "JeuTest" in proc.stdout


def test_doctor_sans_toml(tmp_path: Path):
    proc = _atelier("doctor", "--projet", str(tmp_path))
    assert proc.returncode == 1
    assert "atelier.toml" in proc.stderr
