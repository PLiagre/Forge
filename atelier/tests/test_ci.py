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
    """Le module qui partage les tests du moteur, et les tranches que la CI lui demande."""
    import importlib.util

    chemin = RACINE / "jeu" / "sim" / "tests" / "tranches.py"
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
    durees = {"a": 30.0, "b": 1.0, "c": 1.0, "d": 12.5}
    # Des tests mesurés, d'autres neufs (absents des durées) : chacun a sa tranche, une seule.
    noms = ["c", "neuf-1", "a", "b", "neuf-2", "d", "neuf-3", "neuf-4"]
    numeros = module.repartir(noms, durees, n)
    assert len(numeros) == len(noms) and set(numeros) <= set(tranches)
    # Le partage ne dépend pas de l'ordre de collecte : chaque tranche fait le même calcul.
    assert dict(zip(noms, numeros)) == dict(zip(reversed(noms), module.repartir(noms[::-1], durees, n)))


def test_les_tranches_du_moteur_s_equilibrent_sur_les_durees_mesurees():
    """Le 11 octobre 2026, le tour de rôle laissait une tranche à 14 min et deux à 1 h 20."""
    module, _, n = _tranches()
    durees = module.lire_durees()
    noms = sorted(durees)
    assert len(noms) >= n, "durees.json ne mesure presque rien : l'équilibre ne prouverait rien"

    def equilibre(charges: list[float]) -> bool:
        # La borne du « plus long d'abord » : jamais plus d'un tiers au-dessus du mieux possible.
        mieux = max(sum(charges) / n, max(durees.values()))
        return max(charges) <= 4 / 3 * mieux

    assert equilibre(module.charges(noms, durees, n)), module.charges(noms, durees, n)
    # Contre-épreuve : tout dans une seule tranche n'est pas équilibré.
    assert not equilibre([sum(durees.values())] + [0.0] * (n - 1)), "le contrôle d'équilibre accepterait tout"


def test_une_tranche_mal_ecrite_est_refusee():
    import pytest

    module, _, _ = _tranches()
    assert module.lire_tranche(None) is None and module.lire_tranche("") is None
    assert module.lire_tranche("2/3") == (2, 3)
    for faute in ("3", "0/3", "4/3", "a/3", "1/3/5", "-1/3"):
        with pytest.raises(ValueError):
            module.lire_tranche(faute)


def _collecter(*options: str, tranche: str | None = None) -> set[str]:
    """Les identifiants que pytest collecterait dans jeu/sim/tests avec ces options."""
    import os
    import subprocess
    import sys

    env = {**os.environ, "PYTHONUTF8": "1"}
    env.pop("FORGE_TRANCHE", None)
    if tranche:
        env["FORGE_TRANCHE"] = tranche
    sortie = subprocess.run(
        [sys.executable, "-m", "pytest", "sim/tests", "--collect-only", "-q", "-p", "no:cacheprovider", *options],
        cwd=RACINE / "jeu", env=env, capture_output=True, text=True, check=True,
    ).stdout
    return {ligne for ligne in sortie.splitlines() if "::" in ligne}


def test_les_tranches_et_les_tests_chronometres_jouent_chaque_test_une_fois():
    _, tranches, n = _tranches()
    tout = _collecter()
    chronometres = _collecter("-m", "chronometre")
    assert tout and chronometres, "aucun test chronometre : le travail `chronometre` n'aurait rien à jouer"

    def jouent_une_fois(parts: list[set[str]]) -> bool:
        return sum(len(p) for p in parts) == len(tout) and set().union(*parts) == tout

    tranchees = [_collecter("-m", "not chronometre", tranche=f"{k}/{n}") for k in tranches]
    assert jouent_une_fois([chronometres, *tranchees])
    # Contre-épreuve : des tranches qui jouent aussi les chronométrés les jouent deux fois.
    assert not jouent_une_fois([chronometres, *[_collecter(tranche=f"{k}/{n}") for k in tranches]])


def test_les_tests_chronometres_ont_leur_travail_et_tests_les_attend_tous():
    texte = WORKFLOW.read_text(encoding="utf-8")
    jobs = texte.split("\njobs:\n", 1)[1]
    noms = re.findall(r"^  (\w+):$", jobs, re.M)
    bloc = lambda nom: re.search(rf"^  {nom}:\n(.*?)(?=^  \w+:$|\Z)", jobs, re.M | re.S).group(1)
    assert "chronometre" in noms and "sim" in noms
    assert '-n auto' in bloc("sim") and '-m "not chronometre"' in bloc("sim")
    commandes = " ".join(re.findall(r"^\s+run: (.+)$", bloc("chronometre"), re.M))
    assert "-m chronometre" in commandes and "-n " not in commandes and "FORGE_TRANCHE" not in bloc("chronometre")
    attendus = re.search(r"needs: \[([^\]]+)\]", bloc("tests")).group(1).replace(" ", "").split(",")
    assert sorted(attendus) == sorted(n for n in noms if n != "tests"), "`tests` doit attendre chaque travail"
