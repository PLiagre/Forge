"""La CI joue chaque test du jeu : un test qu'elle ne joue pas ne protège rien.

Le lot #118 a ajouté `jeu/ville/tests`, que `tests.yml` ne jouait pas ; un
lot ne touche pas `.github/`. D'où une étape qui joue tout ce que les
autres étapes ne jouent pas, et ce test qui en garde la forme.
"""

from __future__ import annotations

import re

from conftest import RACINE

WORKFLOW = RACINE / ".github" / "workflows" / "tests.yml"


def _etapes() -> tuple[list[str], list[str]]:
    """Les dossiers joués explicitement, et ceux que l'étape générique ignore."""
    texte = WORKFLOW.read_text(encoding="utf-8").replace("\\\n", " ")
    explicites = [c.rstrip("/") for c in re.findall(r"python -m pytest ((?!atelier/)[\w/]+/tests)/? -q", texte)]
    generique = re.search(r"python -m pytest \. -q((?:\s+--ignore=\S+)+)", texte)
    assert generique, "tests.yml n'a plus l'étape qui joue les autres tests du jeu"
    return explicites, re.findall(r"--ignore=(\S+)", generique.group(1))


def test_l_etape_generique_ignore_exactement_les_dossiers_deja_joues():
    explicites, ignores = _etapes()
    assert explicites and sorted(ignores) == sorted(explicites)


def test_la_ci_joue_chaque_test_du_jeu():
    explicites, ignores = _etapes()
    jeu = RACINE / "jeu"
    fichiers = [f.relative_to(jeu).as_posix() for f in jeu.rglob("test_*.py")]
    assert fichiers, "aucun test trouvé dans jeu/ : le contrôle ne contrôlerait rien"
    # Un fichier sous un dossier ignoré doit être joué par une étape explicite ;
    # tout autre fichier est joué par l'étape générique.
    orphelins = [f for f in fichiers
                 if any(f.startswith(i + "/") for i in ignores) and not any(f.startswith(c + "/") for c in explicites)]
    assert not orphelins
