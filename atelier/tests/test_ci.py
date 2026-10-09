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


def _tranches():
    """Le module qui répartit les tests du moteur, et les tranches que la CI lui demande."""
    import importlib.util

    chemin = RACINE / "jeu" / "sim" / "tests" / "conftest.py"
    spec = importlib.util.spec_from_file_location("tranches_du_moteur", chemin)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    texte = WORKFLOW.read_text(encoding="utf-8")
    matrice = re.search(r"tranche: \[([\d, ]+)\]", texte)
    variable = re.search(r"FORGE_TRANCHE: \$\{\{ matrix\.tranche \}\}/(\d+)", texte)
    assert matrice and variable, "tests.yml ne répartit plus les tests du moteur en tranches"
    return module, [int(k) for k in matrice.group(1).split(",")], int(variable.group(1))


def test_les_tranches_du_moteur_jouent_chaque_test_une_fois():
    module, tranches, n = _tranches()
    assert tranches == list(range(1, n + 1)), f"tranches {tranches} pour {n} annoncées"
    for rang in range(3 * n + 7):
        assert sum(module.dans_la_tranche(rang, k, n) for k in tranches) == 1, f"le test de rang {rang}"


def test_une_tranche_mal_ecrite_est_refusee():
    import pytest

    module, _, _ = _tranches()
    assert module.lire_tranche(None) is None and module.lire_tranche("") is None
    assert module.lire_tranche("2/3") == (2, 3)
    for faute in ("3", "0/3", "4/3", "a/3", "1/3/5", "-1/3"):
        with pytest.raises(pytest.UsageError):
            module.lire_tranche(faute)
