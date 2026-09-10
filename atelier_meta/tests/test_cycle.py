"""Auteur ≠ relecteur. L'atelier ne fusionne pas. Sans --run, rien n'est écrit."""

from pathlib import Path
import subprocess
import sys

import pytest

from atelier import etat, projet
from atelier.__main__ import main
from atelier.cycle import preparer, CycleErreur
from atelier.etat import FusionInterdite
from tests.test_porte import BRIEF_SAIN


def _produit(tmp_path: Path) -> Path:
    (tmp_path / "briefs").mkdir()
    (tmp_path / "atelier.toml").write_text(
        """
[projet]
nom = "JeuTest"
briefs = "briefs"
tests = "python3 -m pytest tests/ -q"
fumee = "python3 -m jeu --ticks 0"
branche_base = "master"
prefixe_branche = "agent/"

[roles]
ecriture = "claude"
execution = "cursor"
controle = "codex"
""".lstrip(),
        encoding="utf-8",
    )
    brief = tmp_path / "briefs" / "001-un-changement.md"
    brief.write_text(BRIEF_SAIN, encoding="utf-8")
    return tmp_path


def test_roles_identiques_refuses(tmp_path: Path):
    (tmp_path / "atelier.toml").write_text(
        """
[projet]
nom = "X"
briefs = "briefs"
tests = "true"
fumee = "true"
branche_base = "master"
prefixe_branche = "agent/"

[roles]
ecriture = "cursor"
execution = "cursor"
controle = "cursor"
""".lstrip(),
        encoding="utf-8",
    )
    with pytest.raises(projet.ProjetIncomplet):
        projet.charger(tmp_path)


def test_apercu_sans_ecriture(tmp_path: Path):
    racine = _produit(tmp_path)
    apercu = preparer(racine / "briefs" / "001-un-changement.md", racine)
    assert apercu.executant == "cursor"
    assert apercu.relecteur == "codex"
    assert apercu.executant != apercu.relecteur
    assert apercu.worktree == str(racine.parent / f"{racine.name}-001-un-changement")
    assert not (racine / ".atelier").exists()
    assert list(racine.glob("atelier-echange/**/*")) == []


def test_start_sans_run_n_ecrit_rien(tmp_path: Path):
    racine = _produit(tmp_path)
    code = main(
        [
            "start",
            str(racine / "briefs" / "001-un-changement.md"),
            "--projet",
            str(racine),
        ]
    )
    assert code == 0
    assert not (racine / ".atelier").exists()


def test_fusionner_refuse():
    with pytest.raises(FusionInterdite):
        etat.fusionner(
            etat.nouveau(
                lot="001",
                brief=Path("briefs/001.md"),
                branche="agent/001",
                worktree=Path("/tmp/wt"),
                auteur_code="cursor",
                relecteur="codex",
                fichiers=["src/foo.py"],
            )
        )


def test_cli_fusionner_code_2():
    proc = subprocess.run(
        [sys.executable, "-m", "atelier", "fusionner"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "ne fusionne pas" in proc.stderr


def test_auteur_egal_relecteur_refuse():
    with pytest.raises(ValueError, match="relecteur"):
        etat.nouveau(
            lot="001",
            brief=Path("briefs/001.md"),
            branche="agent/001",
            worktree=Path("/tmp/wt"),
            auteur_code="cursor",
            relecteur="cursor",
            fichiers=["src/foo.py"],
        )


BRIEF_AVEC_INTERDITS = """# Brief 046 — la mer

## But
Une phrase.

## Règle du monde
Aucun fondement.

## Périmètre

En écriture : `sim/engine.py`, `sim/constants.py` **uniquement** pour déclarer
un panier, et `sim/tests/test_commerce.py` pour y **ajouter** des cas.

**`sim/tests/test_write_coverage.py` n'est pas modifiable.** Élargir le monde
d'épreuve n'est pas la solution retenue.

Tout autre chemin est interdit, nommément : `sim/MODELE.md`, `sim/model.py`,
`sim/aggregation.py`, la carte figée `data/world-1400.json`, et ce brief.

## Conditions de succès

### SC1 — une commande
```bash
python3 -m pytest sim/tests/ -q
```

## Hors périmètre
Rien d'autre.
"""


def test_le_perimetre_ne_compte_pas_les_fichiers_interdits(tmp_path: Path):
    """Un périmètre nomme aussi ce qu'il interdit (règle 6 du produit).

    Le verrou ne doit tenir que les fichiers autorisés : sinon le lot 046
    tiendrait `sim/aggregation.py`, qui est le périmètre du 047, et les
    deux lots « disjoints » se bloqueraient l'un l'autre.
    """
    from atelier.cycle import _fichiers_du_perimetre

    brief = tmp_path / "046-la-mer.md"
    brief.write_text(BRIEF_AVEC_INTERDITS, encoding="utf-8")
    fichiers = _fichiers_du_perimetre(brief)
    assert fichiers, "échantillon vide"
    assert fichiers == ["sim/engine.py", "sim/constants.py", "sim/tests/test_commerce.py"]
    for interdit in ("sim/aggregation.py", "sim/tests/test_write_coverage.py", "data/world-1400.json"):
        assert interdit not in fichiers


def test_brief_infirme_bloque_le_cycle(tmp_path: Path):
    racine = _produit(tmp_path)
    brief = racine / "briefs" / "001-un-changement.md"
    brief.write_text("# Brief 001\n\nrien.\n", encoding="utf-8")
    with pytest.raises(CycleErreur, match="porte"):
        preparer(brief, racine)
