"""La branche du lot et le numéro de PR : déterministes, avant Cursor.

Aucun test n'appelle `agent`, `claude` ni `hermes` réels : le PATH
porte un faux binaire. Les dépôts git sont temporaires.
"""

from pathlib import Path
import subprocess

import pytest

from atelier import boite
from atelier import boite, echange, verrou
from atelier import worktree as worktree_mod
from atelier.__main__ import main
from tests.depot import committer, courante, installer, orpheline, worktree_role
from tests.test_invocation import (
    besoin_bash,
    _boite_de,
    _carte,
    _env,
    _faux,
    _mouchard,
    _projet,
    _tour,
)


def _agent_pr(dossier: Path, temoin: Path, numero: int | None = 44) -> Path:
    if numero is None:
        corps_pr = ""
    else:
        corps_pr = (
            "mkdir -p atelier-echange\n"
            f"printf '%s\\n' '{numero}' > atelier-echange/pr.txt\n"
        )
    return _faux(
        dossier,
        "agent",
        f'printf "%s\\n" "$0" >> "{temoin}"\n'
        f'git branch --show-current >> "{temoin}"\n'
        f"{corps_pr}"
        "exit 0\n",
    )


def _coder_pret(projet: Path, tmp_path: Path) -> Path:
    installer(projet)
    return worktree_role(projet, tmp_path / "coder")


def _env_coder(projet: Path, faux: Path, verrous: Path, worktree: Path, **extra: str) -> dict[str, str]:
    return _env(projet, faux, verrous, ATELIER_WORKDIR_coder=str(worktree), **extra)


# -------------------------------------------------------------- 1. à sec


@besoin_bash
def test_a_sec_ne_change_ni_branche_ni_boite_ni_fichiers(tmp_path: Path):
    projet = _projet(tmp_path)
    _carte(projet)
    worktree = _coder_pret(projet, tmp_path)
    avant_branche = courante(worktree)
    avant_fichiers = {p.relative_to(worktree) for p in worktree.rglob("*") if p.is_file()}
    faux, verrous = tmp_path / "bin", tmp_path / "verrous"
    temoin = tmp_path / "temoin.txt"
    _agent_pr(faux, temoin)
    r = _tour("coder", _env_coder(projet, faux, verrous, worktree))
    assert r.returncode == 0, r.stderr
    assert "ATELIER_INVOQUER n'est pas posé" in r.stdout
    assert "branche du lot : agent/044-mineur" in r.stdout
    assert not temoin.exists()
    assert courante(worktree) == avant_branche == "atelier/coder"
    assert _boite_de(projet, "a-coder") == ["044-mineur"]
    assert _boite_de(projet, "a-relire") == []
    apres = {p.relative_to(worktree) for p in worktree.rglob("*") if p.is_file()}
    assert apres == avant_fichiers


# ------------------------------------------ 2. prefixe_branche


def test_la_branche_attendue_vient_de_prefixe_branche(tmp_path: Path, capsys):
    projet = _projet(tmp_path)
    texte = (projet / "atelier.toml").read_text(encoding="utf-8")
    (projet / "atelier.toml").write_text(
        texte.replace('prefixe_branche = "agent/"', 'prefixe_branche = "lot/"'),
        encoding="utf-8",
    )
    assert main(["branche", "--projet", str(projet), "--lot", "044-mineur"]) == 0
    assert capsys.readouterr().out.strip() == "lot/044-mineur"


@besoin_bash
def test_le_prefixe_du_toml_est_celui_extrait(tmp_path: Path):
    projet = _projet(tmp_path)
    texte = (projet / "atelier.toml").read_text(encoding="utf-8")
    (projet / "atelier.toml").write_text(
        texte.replace('prefixe_branche = "agent/"', 'prefixe_branche = "lot/"'),
        encoding="utf-8",
    )
    _carte(projet)
    worktree = _coder_pret(projet, tmp_path)
    faux, verrous = tmp_path / "bin", tmp_path / "verrous"
    temoin = tmp_path / "temoin.txt"
    _agent_pr(faux, temoin)
    r = _tour("coder", _env_coder(projet, faux, verrous, worktree, ATELIER_INVOQUER="1"))
    assert r.returncode == 0, r.stderr
    assert courante(worktree) == "lot/044-mineur"
    assert "lot/044-mineur" in temoin.read_text(encoding="utf-8")


# ------------------------------------------ 3. worktree sale


def test_preparer_lot_refuse_toujours_un_worktree_sale(tmp_path: Path):
    """Le refus n'a pas bougé là où il compte : dans `preparer_lot`.

    C'est lui qui garde la règle « l'atelier n'efface pas ». Le tour,
    lui, range avant d'appeler — mais si quelque chose salit le
    worktree entre le rangement et la préparation, la fonction refuse
    encore, et elle refuse sans rien détruire.
    """
    projet = _projet(tmp_path)
    worktree = _coder_pret(projet, tmp_path)
    (worktree / "brouillon.txt").write_text("ne pas effacer\n", encoding="utf-8")
    with pytest.raises(worktree_mod.WorktreeErreur, match="non enregistrées"):
        worktree_mod.preparer_lot(worktree, "lot/044-mineur", "master")
    assert (worktree / "brouillon.txt").read_text(encoding="utf-8") == "ne pas effacer\n"
    assert courante(worktree) == "atelier/coder"


@besoin_bash
def test_un_worktree_sale_est_range_et_le_lot_suivant_passe(tmp_path: Path):
    """Un tour ne laisse plus au suivant un répertoire qu'il faut déblayer.

    Avant, un agent qui rendait la main sur un worktree sale faisait
    échouer le lot d'après dès `preparer_lot`, et il fallait qu'une
    personne commite à la main pour débloquer la file : une cascade,
    pas une panne isolée. Le tour enregistre maintenant ce qui traîne
    sur la branche du rôle — il n'efface rien, et `git log` le
    retrouve — puis il continue.
    """
    projet = _projet(tmp_path)
    _carte(projet)
    worktree = _coder_pret(projet, tmp_path)
    (worktree / "brouillon.txt").write_text("ne pas effacer\n", encoding="utf-8")
    faux, verrous = tmp_path / "bin", tmp_path / "verrous"
    temoin = tmp_path / "temoin.txt"
    _agent_pr(faux, temoin)
    r = _tour("coder", _env_coder(projet, faux, verrous, worktree, ATELIER_INVOQUER="1"))
    assert r.returncode == 0, r.stderr
    # Rien n'est perdu. Le brouillon a quitté le répertoire — on a
    # basculé sur la branche du lot — mais il vit dans l'historique de
    # la branche du rôle, et son contenu se relit mot pour mot.
    garde = subprocess.run(
        ["git", "-C", str(worktree), "show", "atelier/coder:brouillon.txt"],
        text=True, capture_output=True, check=True,
    ).stdout
    assert garde == "ne pas effacer\n"
    # Et la file avance : c'est tout l'objet du rangement.
    assert courante(worktree) == "agent/044-mineur"
    assert _boite_de(projet, "echec") == []
    assert _boite_de(projet, "a-relire") == ["044-mineur"]


# -------------------------------- 4. créée depuis la base  5. extraite


@besoin_bash
def test_la_branche_du_lot_est_creee_depuis_la_base_et_l_agent_y_tourne(tmp_path: Path):
    projet = _projet(tmp_path)
    _carte(projet)
    worktree = _coder_pret(projet, tmp_path)
    # Le worktree du rôle a un commit en trop : s'il servait de base,
    # le lot porterait ce fichier. La base du produit, non.
    committer(worktree, worktree / "role-only.txt", "commit du rôle")
    faux, verrous = tmp_path / "bin", tmp_path / "verrous"
    temoin = tmp_path / "temoin.txt"
    _agent_pr(faux, temoin)
    r = _tour("coder", _env_coder(projet, faux, verrous, worktree, ATELIER_INVOQUER="1"))
    assert r.returncode == 0, r.stderr
    assert courante(worktree) == "agent/044-mineur"
    assert not (worktree / "role-only.txt").exists()
    trace = temoin.read_text(encoding="utf-8")
    assert str(faux / "agent") in trace
    assert "agent/044-mineur" in trace
    assert _boite_de(projet, "a-relire") == ["044-mineur"]


# ------------------------------------------ 6. reprise cohérente


@besoin_bash
def test_une_branche_coherente_est_reprise_sans_destruction(tmp_path: Path):
    projet = _projet(tmp_path)
    _carte(projet)
    worktree = _coder_pret(projet, tmp_path)
    from tests.depot import _git
    _git(projet, "checkout", "-b", "agent/044-mineur", "master")
    marque = projet / "deja-la.txt"
    marque.write_text("conserver\n", encoding="utf-8")
    committer(projet, marque, "travail déjà là")
    _git(projet, "checkout", "master")
    faux, verrous = tmp_path / "bin", tmp_path / "verrous"
    temoin = tmp_path / "temoin.txt"
    _agent_pr(faux, temoin)
    r = _tour("coder", _env_coder(projet, faux, verrous, worktree, ATELIER_INVOQUER="1"))
    assert r.returncode == 0, r.stderr
    assert courante(worktree) == "agent/044-mineur"
    assert (worktree / "deja-la.txt").read_text(encoding="utf-8") == "conserver\n"


# ------------------------------------------ 7. incohérente


@besoin_bash
def test_une_branche_incoherente_est_refusee_avant_invocation(tmp_path: Path):
    projet = _projet(tmp_path)
    _carte(projet)
    worktree = _coder_pret(projet, tmp_path)
    orpheline(projet, "agent/044-mineur")
    faux, verrous = tmp_path / "bin", tmp_path / "verrous"
    temoin = tmp_path / "temoin.txt"
    _agent_pr(faux, temoin)
    r = _tour("coder", _env_coder(projet, faux, verrous, worktree, ATELIER_INVOQUER="1"))
    assert r.returncode != 0
    assert not temoin.exists()
    assert courante(worktree) == "atelier/coder"
    assert "incohérente" in r.stderr
    assert _boite_de(projet, "echec") == ["044-mineur"]
    assert _boite_de(projet, "a-relire") == []


# --------------------- 8. 9. 10. 11. code 0 et pr.txt


@besoin_bash
def test_code_0_sans_pr_txt_envoie_en_echec(tmp_path: Path):
    projet = _projet(tmp_path)
    _carte(projet)
    worktree = _coder_pret(projet, tmp_path)
    faux, verrous = tmp_path / "bin", tmp_path / "verrous"
    temoin = tmp_path / "temoin.txt"
    _agent_pr(faux, temoin, numero=None)
    r = _tour("coder", _env_coder(projet, faux, verrous, worktree, ATELIER_INVOQUER="1"))
    assert r.returncode != 0
    assert temoin.exists(), "l'agent a tourné, mais sans livrable"
    assert _boite_de(projet, "a-relire") == []
    assert _boite_de(projet, "echec") == ["044-mineur"]
    assert "PR" in boite.lister(projet, "echec")[0].note


@besoin_bash
def test_pr_txt_vide_est_refuse(tmp_path: Path):
    projet = _projet(tmp_path)
    _carte(projet)
    worktree = _coder_pret(projet, tmp_path)
    faux, verrous = tmp_path / "bin", tmp_path / "verrous"
    temoin = tmp_path / "temoin.txt"
    _faux(
        faux, "agent",
        f'printf "lance\\n" >> "{temoin}"\n'
        "mkdir -p atelier-echange\n"
        ": > atelier-echange/pr.txt\n"
        "exit 0\n",
    )
    r = _tour("coder", _env_coder(projet, faux, verrous, worktree, ATELIER_INVOQUER="1"))
    assert r.returncode != 0
    assert _boite_de(projet, "echec") == ["044-mineur"]
    assert _boite_de(projet, "a-relire") == []


@besoin_bash
def test_pr_diese_n_est_pas_un_numero(tmp_path: Path):
    projet = _projet(tmp_path)
    _carte(projet)
    worktree = _coder_pret(projet, tmp_path)
    faux, verrous = tmp_path / "bin", tmp_path / "verrous"
    _faux(
        faux, "agent",
        "mkdir -p atelier-echange\n"
        "printf '%s\\n' 'PR #123' > atelier-echange/pr.txt\n"
        "exit 0\n",
    )
    r = _tour("coder", _env_coder(projet, faux, verrous, worktree, ATELIER_INVOQUER="1"))
    assert r.returncode != 0
    assert _boite_de(projet, "echec") == ["044-mineur"]
    assert _boite_de(projet, "a-relire") == []


@besoin_bash
def test_un_entier_positif_avance_vers_a_relire(tmp_path: Path):
    projet = _projet(tmp_path)
    _carte(projet)
    worktree = _coder_pret(projet, tmp_path)
    faux, verrous = tmp_path / "bin", tmp_path / "verrous"
    temoin = tmp_path / "temoin.txt"
    _agent_pr(faux, temoin, numero=44)
    r = _tour("coder", _env_coder(projet, faux, verrous, worktree, ATELIER_INVOQUER="1"))
    assert r.returncode == 0, r.stderr
    prise = boite.prochain(projet, "relire")
    assert prise is not None and prise.pr == 44
    assert not (worktree / "atelier-echange" / "pr.txt").exists()


# ------------------------------------------ 12. numéro périmé


@besoin_bash
def test_aucun_numero_perime_n_est_repris(tmp_path: Path):
    projet = _projet(tmp_path)
    _carte(projet)
    worktree = _coder_pret(projet, tmp_path)
    canal = worktree / "atelier-echange"
    canal.mkdir()
    (canal / "pr.txt").write_text("99\n", encoding="utf-8")
    faux, verrous = tmp_path / "bin", tmp_path / "verrous"
    temoin = tmp_path / "temoin.txt"
    _agent_pr(faux, temoin, numero=None)
    r = _tour("coder", _env_coder(projet, faux, verrous, worktree, ATELIER_INVOQUER="1"))
    assert r.returncode != 0
    assert _boite_de(projet, "a-relire") == []
    prise = boite.lister(projet, "echec")
    assert prise and prise[0].pr is None
    assert not (canal / "pr.txt").exists()


# ------------------------------------------ 13. verrous levés


@besoin_bash
def test_les_verrous_sont_liberes_apres_un_echec(tmp_path: Path):
    projet = _projet(tmp_path)
    _carte(projet)
    worktree = _coder_pret(projet, tmp_path)
    faux, verrous = tmp_path / "bin", tmp_path / "verrous"
    _mouchard(faux, "agent", tmp_path / "temoin.txt", code=3)
    r = _tour("coder", _env_coder(projet, faux, verrous, worktree, ATELIER_INVOQUER="1"))
    assert r.returncode != 0
    assert verrou.charger(projet).poses == []
    assert not (projet / ".atelier" / "verrous.json").exists()


# ------------------------------------------ 14. pas de vrais binaires


@besoin_bash
def test_aucun_vrai_binaire_n_est_appele(tmp_path: Path):
    projet = _projet(tmp_path)
    _carte(projet)
    worktree = _coder_pret(projet, tmp_path)
    faux, verrous = tmp_path / "bin", tmp_path / "verrous"
    temoin = tmp_path / "temoin.txt"
    _agent_pr(faux, temoin)
    _mouchard(faux, "claude", tmp_path / "claude.txt")
    _mouchard(faux, "hermes", tmp_path / "hermes.txt")
    r = _tour("coder", _env_coder(projet, faux, verrous, worktree, ATELIER_INVOQUER="1"))
    assert r.returncode == 0, r.stderr
    trace = temoin.read_text(encoding="utf-8")
    assert str(faux / "agent") in trace
    assert not (tmp_path / "claude.txt").exists()
    assert not (tmp_path / "hermes.txt").exists()


def test_le_relecteur_recoit_le_numero_et_la_branche(tmp_path: Path, capsys):
    projet = _projet(tmp_path)
    texte = (projet / "atelier.toml").read_text(encoding="utf-8")
    (projet / "atelier.toml").write_text(
        texte.replace('prefixe_branche = "agent/"', 'prefixe_branche = "lot/"'),
        encoding="utf-8",
    )
    main(["invocation", "--role", "relire", "--projet", str(projet),
          "--lot", "044-mineur", "--brief", "briefs/044-mineur.md", "--pr", "44"])
    sortie = capsys.readouterr().out
    assert "44" in sortie
    assert "lot/044-mineur" in sortie


def test_run_refuse_de_basculer_le_clone_du_produit(tmp_path: Path, capsys):
    projet = _projet(tmp_path)
    installer(projet)
    assert main([
        "branche", "--projet", str(projet), "--lot", "044-mineur",
        "--worktree", str(projet), "--run",
    ]) == 1
    assert "clone du produit" in capsys.readouterr().err


def test_run_exige_un_worktree(tmp_path: Path, capsys):
    projet = _projet(tmp_path)
    assert main(["branche", "--projet", str(projet), "--lot", "044-mineur", "--run"]) == 1
    assert "--worktree" in capsys.readouterr().err


def test_lire_numero_pr_refuse_les_formats_libres(tmp_path: Path):
    cible = tmp_path / "pr.txt"
    with pytest.raises(echange.EchangeErreur, match="absent"):
        echange.lire_numero_pr(cible)
    cible.write_text("   \n", encoding="utf-8")
    with pytest.raises(echange.EchangeErreur, match="vide"):
        echange.lire_numero_pr(cible)
    cible.write_text("PR #123\n", encoding="utf-8")
    with pytest.raises(echange.EchangeErreur, match="entier positif"):
        echange.lire_numero_pr(cible)
    cible.write_text("0\n", encoding="utf-8")
    with pytest.raises(echange.EchangeErreur, match="entier positif"):
        echange.lire_numero_pr(cible)
    cible.write_text(" 44 \n", encoding="utf-8")
    assert echange.lire_numero_pr(cible) == 44
