"""Un seul endroit dit qui tient quel poste : le branchement du produit.

L'atelier sait ce qu'un binaire sait faire (un modèle, une garde de
lecture seule, un abonnement). Il ne sait pas qui relit *ce* produit :
ça, c'est `atelier.toml`.
"""

from pathlib import Path
import os
import shutil
import subprocess

import pytest

from atelier import backends, boite, projet
from atelier.__main__ import main


RACINE = Path(__file__).resolve().parent.parent
TOUR = RACINE / "crons" / "tour.sh"
VEILLE = RACINE / "crons" / "veille.sh"

besoin_bash = pytest.mark.skipif(shutil.which("bash") is None, reason="bash absent")


def _produit(tmp_path: Path, *, ecriture="claude", execution="cursor", controle="claude") -> Path:
    racine = tmp_path / "produit"
    (racine / "briefs").mkdir(parents=True, exist_ok=True)
    (racine / "atelier.toml").write_text(
        "[projet]\n"
        'nom = "Produit"\n'
        'briefs = "briefs"\n'
        'tests = "python3 -m pytest -q"\n'
        'fumee = "echo fumee-ok"\n'
        'branche_base = "master"\n'
        'prefixe_branche = "agent/"\n'
        "\n[roles]\n"
        f'ecriture = "{ecriture}"\n'
        f'execution = "{execution}"\n'
        f'controle = "{controle}"\n',
        encoding="utf-8",
    )
    (racine / "briefs" / "044-mineur.md").write_text(
        "# Brief 044\n\n## Périmètre\n\n- `sim/engine.py`\n", encoding="utf-8"
    )
    return racine


def _roles(**kw) -> dict[str, str]:
    base = {"ecriture": "claude", "execution": "cursor", "controle": "claude"}
    base.update(kw)
    return base


# ------------------------------------------------- la règle, pas plus stricte


def test_briefer_et_relire_peuvent_etre_le_meme_agent(tmp_path: Path):
    """Écrire un brief n'est pas écrire du code."""
    racine = _produit(tmp_path, ecriture="claude", controle="claude")
    produit = projet.charger(racine)
    assert produit.roles.ecriture == produit.roles.controle == "claude"
    assert main(["doctor", "--projet", str(racine)]) == 0


def test_l_executant_ne_se_relit_pas(tmp_path: Path):
    racine = _produit(tmp_path, execution="cursor", controle="cursor")
    with pytest.raises(projet.ProjetIncomplet) as leve:
        projet.charger(racine)
    message = str(leve.value)
    assert "exécution" in message and "contrôle" in message
    assert main(["doctor", "--projet", str(racine)]) == 1


# ------------------------------------------- le poste vient du branchement


def test_le_binaire_du_relecteur_vient_du_branchement(tmp_path: Path, capsys):
    for controle, binaire in (("claude", "claude"), ("codex", "codex")):
        racine = _produit(tmp_path / controle, controle=controle)
        main(["invocation", "--role", "relire", "--projet", str(racine),
              "--lot", "044-mineur", "--brief", "briefs/044-mineur.md"])
        assert capsys.readouterr().out.startswith(binaire + " ")


def test_l_abo_vient_du_branchement(tmp_path: Path, capsys):
    for controle, abo in (("claude", "claude-pro"), ("codex", "chatgpt-plus")):
        racine = _produit(tmp_path / controle, controle=controle)
        main(["poste", "--projet", str(racine), "--role", "relire", "--champ", "abo"])
        assert capsys.readouterr().out.strip() == abo


def test_le_planificateur_et_le_coder_partagent_l_executant(tmp_path: Path):
    roles = _roles(execution="cursor")
    plan = backends.poste_du_role("planifier", roles)
    code = backends.poste_du_role("coder", roles)
    assert plan.backend == code.backend == "cursor"
    assert plan.modele == "cursor-grok-4.6"
    assert code.modele == "composer-2.5"


def test_le_pilote_n_est_pas_un_poste_du_produit(tmp_path: Path):
    """La console tient l'horloge ; le branchement ne la nomme pas."""
    poste = backends.poste_du_role("pilote", _roles(ecriture="codex", controle="codex"))
    assert poste.binaire == "hermes"
    assert poste.abo == "chatgpt-plus"


def test_codex_et_hermes_partagent_le_quota_chatgpt():
    """Un quatrième relecteur Codex n'est pas un quatrième quota."""
    assert backends.pour("codex").abo == backends.pour("hermes").abo == "chatgpt-plus"


def test_aucune_table_de_shell_ne_nomme_un_abonnement():
    texte = TOUR.read_text(encoding="utf-8")
    for abo in ("claude-pro", "cursor-pro", "chatgpt-plus"):
        assert abo not in texte, f"{abo} est écrit en dur dans tour.sh"


# ------------------------------------------------- la garde de lecture seule


def test_la_lecture_seule_se_declare(tmp_path: Path, capsys):
    attendu = {"claude": "tenue", "codex": "non-tenue", "cursor": "non-tenue"}
    for controle, etat in attendu.items():
        # L'exécutant ne se relit jamais : on lui donne l'autre binaire.
        execution = "cursor" if controle != "cursor" else "claude"
        racine = _produit(tmp_path / controle, execution=execution, controle=controle)
        main(["poste", "--projet", str(racine), "--role", "relire", "--champ", "lecture_seule"])
        assert capsys.readouterr().out.strip() == etat


def test_la_lecture_seule_est_sans_objet_hors_relecture(tmp_path: Path, capsys):
    racine = _produit(tmp_path)
    main(["poste", "--projet", str(racine), "--role", "coder", "--champ", "lecture_seule"])
    assert capsys.readouterr().out.strip() == "sans-objet"


@besoin_bash
def test_le_tour_previent_quand_le_relecteur_garde_la_main(tmp_path: Path):
    racine = _produit(tmp_path, execution="claude", controle="codex")
    boite.deposer(
        racine, "a-relire",
        boite.Carte(lot="044-mineur", brief="briefs/044-mineur.md", fichiers=["sim/engine.py"]),
    )
    faux, verrous = tmp_path / "bin", tmp_path / "verrous"
    faux.mkdir(parents=True, exist_ok=True)
    temoin = tmp_path / "temoin.txt"
    (faux / "codex").write_text(
        f'#!/usr/bin/env bash\nprintf "%s\\n" "$*" >> "{temoin}"\nexit 0\n', encoding="utf-8"
    )
    (faux / "codex").chmod(0o755)
    env = {k: v for k, v in os.environ.items() if not k.startswith("ATELIER_")}
    env["PATH"] = f"{faux}:{env.get('PATH', '')}"
    env["ATELIER_PROJET"] = str(racine)
    env["ATELIER_ROOT"] = str(RACINE)
    env["ATELIER_VERROUS"] = str(verrous)
    env["ATELIER_INVOQUER"] = "1"
    r = subprocess.run(
        ["bash", str(TOUR), "relire"], env=env, text=True, capture_output=True, timeout=60
    )
    assert r.returncode == 0, r.stderr
    assert "lecture seule" in r.stderr
    assert temoin.exists(), "le relecteur doit quand même être lancé"


# --------------------------------------------------------------- la veille


@besoin_bash
def test_la_veille_declare_un_branchement_absent(tmp_path: Path):
    vide = tmp_path / "sans-branchement"
    vide.mkdir()
    env = {k: v for k, v in os.environ.items() if not k.startswith("ATELIER_")}
    env["ATELIER_PROJET"] = str(vide)
    env["ATELIER_ROOT"] = str(RACINE)
    r = subprocess.run(
        ["bash", str(VEILLE)], env=env, text=True, capture_output=True, timeout=60
    )
    assert r.returncode != 0, "un branchement absent n'est pas un succès"
    assert "atelier.toml" in r.stderr


@besoin_bash
def test_la_veille_passe_quand_le_branchement_est_la(tmp_path: Path):
    racine = _produit(tmp_path)
    env = {k: v for k, v in os.environ.items() if not k.startswith("ATELIER_")}
    env["ATELIER_PROJET"] = str(racine)
    env["ATELIER_ROOT"] = str(RACINE)
    r = subprocess.run(
        ["bash", str(VEILLE)], env=env, text=True, capture_output=True, timeout=60
    )
    assert r.returncode == 0, r.stderr
