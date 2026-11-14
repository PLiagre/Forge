"""La CI joue chaque test du jeu : un test qu'elle ne joue pas ne protège rien.

Un dossier de tests que `tests.yml` ne jouerait pas ne protégerait rien ; un
lot ne touche pas `.github/`. D'où une étape qui joue tout ce que les
autres étapes ne jouent pas, et ce test qui en garde la forme.
"""

from __future__ import annotations

import re

from conftest import RACINE

WORKFLOW = RACINE / ".github" / "workflows" / "tests.yml"
NUIT = RACINE / ".github" / "workflows" / "nuit.yml"
# Ce que la suite exigée pour fusionner peut coûter, en minutes, travail le plus lent compris.
BUDGET_DE_LA_SUITE_RAPIDE_MIN = 5
# Les cœurs d'un runner de GitHub pour un dépôt public.
COEURS_D_UN_RUNNER = 4


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

    chemin = RACINE / "jeu" / "tranches.py"
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
    """Un tour de rôle laisserait une tranche à 14 min et deux à 1 h 20."""
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


def _ci_videe(texte: str) -> bool:
    return re.search(r'^env:\n(?:  .*\n)*?  CI: ""\n', texte, re.M) is not None


def test_pytest_ne_se_croit_pas_sur_une_ci():
    """Avec `CI` non vide, pytest compare en entier deux structures inégales,
    même dans un `pytest.raises(AssertionError)` : 6 s sur le PC, 63 min sur la
    CI pour test_maitre_permutations."""
    texte = WORKFLOW.read_text(encoding="utf-8")
    assert _ci_videe(texte), "tests.yml doit vider CI pour tous ses travaux"
    # Contre-épreuve : sans la ligne, ou avec CI posée, le contrôle échoue.
    assert not _ci_videe(texte.replace('  CI: ""\n', ""))
    assert not _ci_videe(texte.replace('  CI: ""\n', '  CI: "true"\n'))


def test_une_tranche_mal_ecrite_est_refusee():
    import pytest

    module, _, _ = _tranches()
    assert module.lire_tranche(None) is None and module.lire_tranche("") is None
    assert module.lire_tranche("2/3") == (2, 3)
    for faute in ("3", "0/3", "4/3", "a/3", "1/3/5", "-1/3"):
        with pytest.raises(ValueError):
            module.lire_tranche(faute)


def _collecter(*options: str, tranche: str | None = None, dossier: str = "sim/tests") -> set[str]:
    """Les identifiants que pytest collecterait dans ce dossier du jeu avec ces options."""
    import os
    import subprocess
    import sys

    env = {**os.environ, "PYTHONUTF8": "1"}
    env.pop("FORGE_TRANCHE", None)
    if tranche:
        env["FORGE_TRANCHE"] = tranche
    sortie = subprocess.run(
        [sys.executable, "-m", "pytest", dossier, "--collect-only", "-q", "-p", "no:cacheprovider", *options],
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
    assert '-n auto' in bloc("sim") and '-m "$CHOIX"' in bloc("sim")
    commandes = " ".join(re.findall(r"^\s+run: (.+)$", bloc("chronometre"), re.M))
    assert "-m chronometre" in commandes and "-n " not in commandes and "FORGE_TRANCHE" not in bloc("chronometre")
    attendus = re.search(r"needs: \[([^\]]+)\]", bloc("tests")).group(1).replace(" ", "").split(",")
    assert sorted(attendus) == sorted(n for n in noms if n != "tests"), "`tests` doit attendre chaque travail"


def _choix() -> tuple[str, str]:
    """Ce que les travaux du jeu jouent avec `tout`, et sans."""
    texte = WORKFLOW.read_text(encoding="utf-8")
    choix = re.search(r"^  CHOIX: \$\{\{ inputs\.tout && '([^']+)' \|\| '([^']+)' \}\}$", texte, re.M)
    assert choix, "tests.yml ne choisit plus entre la suite rapide et tout"
    return choix.group(1), choix.group(2)


def test_chaque_travail_du_jeu_suit_le_choix_et_la_nuit_joue_tout():
    tout, rapide = _choix()
    assert (tout, rapide) == ("not chronometre", "not chronometre and not longue")
    texte = WORKFLOW.read_text(encoding="utf-8").replace("\\\n", " ")
    commandes = [c for c in re.findall(r"python -m pytest [^\n|]+", texte) if "atelier/" not in c and "-m chronometre" not in c]
    assert commandes and all('-m "$CHOIX"' in c for c in commandes), commandes
    nuit = NUIT.read_text(encoding="utf-8")
    assert re.search(r"uses: \./\.github/workflows/tests\.yml\n    with:\n      tout: true", nuit)
    assert "schedule:" in nuit and "pull_request" not in nuit, "la nuit ne retient aucune fusion"


def test_la_suite_rapide_et_les_preuves_longues_jouent_chaque_test_une_fois():
    tout, rapide = _choix()
    for dossier in ("sim/tests", "forge/tests"):
        tous, rapides = _collecter("-m", tout, dossier=dossier), _collecter("-m", rapide, dossier=dossier)
        longues = _collecter("-m", f"({tout}) and longue", dossier=dossier)
        assert rapides and longues, f"{dossier} : la suite rapide ou la nuit n'aurait rien à jouer"
        assert not rapides & longues and rapides | longues == tous


def test_la_suite_rapide_tient_son_budget_sur_les_durees_mesurees():
    """Les coûts de `durees.json` sont ceux d'un test joué seul : leur somme majore ce qu'un travail attend."""
    module, tranches, n = _tranches()
    import importlib.util

    spec = importlib.util.spec_from_file_location("conftest_du_jeu_pour_son_seuil", RACINE / "jeu" / "conftest.py")
    seuil = float(re.search(r"^SEUIL_LONGUE_S = ([\d.]+)$", spec.loader.get_data(spec.origin).decode("utf-8"), re.M).group(1))
    durees = module.lire_durees()
    rapides = {nom: s for nom, s in durees.items() if s < seuil}
    assert len(rapides) < len(durees), "aucune preuve longue : le contrôle ne contrôlerait rien"
    budget = BUDGET_DE_LA_SUITE_RAPIDE_MIN * 60

    def somme(*prefixes: str) -> float:
        return sum(s for nom, s in rapides.items() if nom.startswith(prefixes))

    # Le moteur : ses tranches, chacune sur les cœurs de son runner.
    moteur = [nom for nom in rapides if nom.startswith("sim/")]
    assert max(module.charges(moteur, rapides, n)) / COEURS_D_UN_RUNNER <= budget
    # Les vues et la commande : un travail chacune, un test après l'autre.
    assert somme("vues/") <= budget
    assert somme("forge/", "ville/") <= budget
    # Contre-épreuve : avec les preuves longues, le moteur ne tient pas le budget.
    assert max(module.charges([nom for nom in durees if nom.startswith("sim/")], durees, n)) / COEURS_D_UN_RUNNER > budget
