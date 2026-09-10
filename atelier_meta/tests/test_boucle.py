"""Le tour se referme, et on peut vérifier avant de basculer.

Trois trous : le numéro de PR qui ne remonte pas, une file bloquée qui
ressemble à une file vide, et une bascule à l'aveugle.
"""

from pathlib import Path
import os
import shutil
import subprocess

import pytest

from atelier import backends, boite, verrou
from atelier.__main__ import main
from tests.depot import installer, worktree_role


RACINE = Path(__file__).resolve().parent.parent
TOUR = RACINE / "crons" / "tour.sh"

besoin_bash = pytest.mark.skipif(shutil.which("bash") is None, reason="bash absent")

ROLES = {"ecriture": "claude", "execution": "cursor", "controle": "claude"}


def _produit(tmp_path: Path) -> Path:
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
        'ecriture = "claude"\n'
        'execution = "cursor"\n'
        'controle = "claude"\n',
        encoding="utf-8",
    )
    (racine / "briefs" / "044-mineur.md").write_text(
        "# Brief 044\n\n## Périmètre\n\n- `sim/engine.py`\n", encoding="utf-8"
    )
    return racine


def _carte(projet: Path, etat: str, lot: str = "044-mineur", **kw) -> None:
    boite.deposer(
        projet, etat,
        boite.Carte(
            lot=lot,
            brief=kw.pop("brief", f"briefs/{lot}.md"),
            fichiers=kw.pop("fichiers", ["sim/engine.py"]),
            **kw,
        ),
    )


def _env(projet: Path, faux: Path, verrous: Path, **extra: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("ATELIER_")}
    env["PATH"] = f"{faux}:{env.get('PATH', '')}"
    env["ATELIER_PROJET"] = str(projet)
    env["ATELIER_ROOT"] = str(RACINE)
    env["ATELIER_VERROUS"] = str(verrous)
    env["ATELIER_INVOQUER"] = "0"
    env.update(extra)
    return env


def _faux(dossier: Path, nom: str, corps: str) -> Path:
    dossier.mkdir(parents=True, exist_ok=True)
    cible = dossier / nom
    cible.write_text("#!/usr/bin/env bash\n" + corps, encoding="utf-8")
    cible.chmod(0o755)
    return cible


def _coder_env(projet: Path, faux: Path, verrous: Path, tmp_path: Path, **extra: str) -> dict[str, str]:
    installer(projet)
    worktree_role(projet, tmp_path / "coder")
    extra.setdefault("ATELIER_WORKDIR_coder", str(tmp_path / "coder"))
    return _env(projet, faux, verrous, **extra)


# ------------------------------------------ le numéro de PR fait le saut


@besoin_bash
def test_le_numero_de_pr_remonte_de_l_executant_a_la_carte(tmp_path: Path):
    projet = _produit(tmp_path)
    _carte(projet, "a-coder")
    faux, verrous = tmp_path / "bin", tmp_path / "verrous"
    # L'exécutant ouvre la PR et dépose son numéro dans le canal.
    _faux(faux, "agent", 'mkdir -p atelier-echange && echo 44 > atelier-echange/pr.txt\n')
    r = subprocess.run(
        ["bash", str(TOUR), "coder"],
        env=_coder_env(projet, faux, verrous, tmp_path, ATELIER_INVOQUER="1"),
        text=True, capture_output=True, timeout=60,
    )
    assert r.returncode == 0, r.stderr
    prise = boite.prochain(projet, "relire")
    assert prise is not None and prise.pr == 44
    # Un numéro périmé ne s'attache pas au lot suivant.
    assert not (tmp_path / "coder" / "atelier-echange" / "pr.txt").exists()


@besoin_bash
def test_sans_numero_la_carte_tombe_en_echec(tmp_path: Path):
    """Un code 0 ne suffit plus : sans PR, a-relire n'est jamais alimenté."""
    projet = _produit(tmp_path)
    _carte(projet, "a-coder")
    faux, verrous = tmp_path / "bin", tmp_path / "verrous"
    _faux(faux, "agent", "exit 0\n")
    r = subprocess.run(
        ["bash", str(TOUR), "coder"],
        env=_coder_env(projet, faux, verrous, tmp_path, ATELIER_INVOQUER="1"),
        text=True, capture_output=True, timeout=60,
    )
    assert r.returncode != 0
    assert boite.prochain(projet, "relire") is None
    assert [c.lot for c in boite.lister(projet, "echec")] == ["044-mineur"]


def test_le_relecteur_sait_quoi_relire(tmp_path: Path, capsys):
    projet = _produit(tmp_path)
    main(["invocation", "--role", "relire", "--projet", str(projet),
          "--lot", "044-mineur", "--brief", "briefs/044-mineur.md", "--pr", "44"])
    sortie = capsys.readouterr().out
    assert "44" in sortie
    assert "agent/044-mineur" in sortie


def test_sans_numero_le_relecteur_a_la_branche(tmp_path: Path, capsys):
    projet = _produit(tmp_path)
    main(["invocation", "--role", "relire", "--projet", str(projet),
          "--lot", "044-mineur", "--brief", "briefs/044-mineur.md"])
    sortie = capsys.readouterr().out
    assert "agent/044-mineur" in sortie
    assert "PR" not in sortie.replace("PR ouverte", "")


# ------------------------------------------------ une file bloquée parle


def test_une_file_bloquee_se_declare(tmp_path: Path, capsys):
    projet = _produit(tmp_path)
    verrou.poser(projet, "046-mer", ["sim/engine.py"])
    _carte(projet, "a-coder")
    code = main(["prochain", "--projet", str(projet), "--role", "coder"])
    capture = capsys.readouterr()
    assert code == 0
    assert capture.out.strip() == "RIEN"
    assert "046-mer" in capture.err


def test_une_file_vide_reste_silencieuse(tmp_path: Path, capsys):
    projet = _produit(tmp_path)
    code = main(["prochain", "--projet", str(projet), "--role", "coder"])
    capture = capsys.readouterr()
    assert code == 0
    assert capture.out.strip() == "RIEN"
    assert capture.err.strip() == ""


# ------------------------------------------------------ la bascule, vue


def test_pret_refuse_un_branchement_illisible(tmp_path: Path, capsys):
    code = main(["pret", "--projet", str(tmp_path / "nulle-part")])
    assert code == 1
    assert "atelier.toml" in capsys.readouterr().out


def test_pret_echoue_si_un_binaire_manque(tmp_path: Path, capsys, monkeypatch):
    projet = _produit(tmp_path)
    monkeypatch.setenv("PATH", str(tmp_path / "vide"))
    code = main(["pret", "--projet", str(projet)])
    sortie = capsys.readouterr().out
    assert code == 1
    assert "FAIL" in sortie
    assert "claude" in sortie and "agent" in sortie


def test_pret_passe_quand_les_binaires_sont_la(tmp_path: Path, capsys, monkeypatch):
    projet = _produit(tmp_path)
    faux = tmp_path / "bin"
    for nom in ("claude", "agent", "hermes", "flock", "timeout"):
        _faux(faux, nom, "exit 0\n")
    monkeypatch.setenv("PATH", str(faux))
    monkeypatch.setenv("ATELIER_VERROUS", str(tmp_path / "verrous"))
    code = main(["pret", "--projet", str(projet)])
    sortie = capsys.readouterr().out
    assert code == 0, sortie
    assert "FAIL" not in sortie


def test_pret_ne_compte_pas_un_quota_inconnu_pour_un_echec(tmp_path: Path, capsys, monkeypatch):
    projet = _produit(tmp_path)
    faux = tmp_path / "bin"
    for nom in ("claude", "agent", "hermes", "flock", "timeout"):
        _faux(faux, nom, "exit 0\n")
    monkeypatch.setenv("PATH", str(faux))
    monkeypatch.setenv("ATELIER_VERROUS", str(tmp_path / "verrous"))
    main(["pret", "--projet", str(projet)])
    sortie = capsys.readouterr().out
    quota = [l for l in sortie.splitlines() if "quota" in l]
    assert quota and quota[0].startswith("?"), sortie


def test_pret_ne_lance_aucun_agent(tmp_path: Path, capsys, monkeypatch):
    """Regarder le PATH n'est pas invoquer."""
    projet = _produit(tmp_path)
    faux = tmp_path / "bin"
    temoin = tmp_path / "temoin.txt"
    for nom in ("claude", "agent", "hermes", "flock", "timeout"):
        _faux(faux, nom, f'echo lance >> "{temoin}"\nexit 0\n')
    monkeypatch.setenv("PATH", str(faux))
    monkeypatch.setenv("ATELIER_INVOQUER", "1")
    monkeypatch.setenv("ATELIER_VERROUS", str(tmp_path / "verrous"))
    main(["pret", "--projet", str(projet)])
    assert not temoin.exists(), temoin.read_text()
