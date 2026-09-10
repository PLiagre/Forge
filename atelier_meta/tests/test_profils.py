"""Deux boucles, une ligne de cron, et une bascule qui ne demande pas root.

`/etc/cron.d/forgeatelier` appartient à root : tant qu'il portait les
treize réveils, changer de cadence demandait le propriétaire. Le
crontab n'appelle plus qu'un répartiteur ; le profil actif vit dans un
fichier que `hermes` écrit.
"""

from pathlib import Path
import os
import shutil
import subprocess

import pytest


RACINE = Path(__file__).resolve().parent.parent
CRONS = RACINE / "crons"
REPARTITEUR = CRONS / "repartiteur.sh"
BOUCLE = CRONS / "atelier-boucle"
PROFILS = CRONS / "profils"

besoin_bash = pytest.mark.skipif(
    shutil.which("bash") is None, reason="bash absent"
)


def _sh(script: Path, *args: str, **env: str) -> subprocess.CompletedProcess[str]:
    complet = dict(os.environ)
    complet.update(env)
    return subprocess.run(
        ["bash", str(script), *args],
        text=True, capture_output=True, timeout=90, env=complet,
    )


def _demander(profil: str, fonction: str, *args: str) -> str:
    """Interroge un profil dans un sous-shell, comme le fait le répartiteur."""
    corps = f'source "{PROFILS}/{profil}.sh"; {fonction} {" ".join(args)}'
    return subprocess.run(
        ["bash", "-c", corps], text=True, capture_output=True, timeout=30, check=True
    ).stdout.strip()


# ------------------------------------------------------- les deux profils


@besoin_bash
@pytest.mark.parametrize("profil", ["jour", "atelier"])
def test_un_profil_dit_les_trois_choses_qu_on_lui_demande(profil):
    """Quel environnement, quels rôles maintenant, quel réveil ensuite."""
    for fonction in ("roles_du_moment", "prochain_reveil"):
        corps = f'source "{PROFILS}/{profil}.sh"; declare -F {fonction}'
        assert subprocess.run(["bash", "-c", corps], capture_output=True).returncode == 0
    assert _demander(profil, "bash -c", "'echo $ATELIER_PROJET'")


@besoin_bash
def test_le_profil_jour_garde_les_treize_reveils():
    assert _demander("jour", "roles_du_moment", "07:00") == "pilote"
    assert _demander("jour", "roles_du_moment", "07:30") == "coder"
    assert _demander("jour", "roles_du_moment", "19:00") == "relire"
    # Une minute sans réveil ne réveille personne : c'est le cas courant.
    assert _demander("jour", "roles_du_moment", "07:01") == ""
    # Et il sait dire ce qui vient, sans qu'on lise la table.
    assert "07:30 coder" in _demander("jour", "prochain_reveil", "07:00")


@besoin_bash
def test_le_profil_atelier_boucle_en_quatre_minutes():
    tour = [_demander("atelier", "roles_du_moment", f"10:{m:02d}") for m in range(8)]
    assert tour == ["pilote", "coder", "relire", "briefer"] * 2


@besoin_bash
def test_le_profil_atelier_ne_peut_pas_atteindre_un_agent_payant(tmp_path: Path):
    """Aucun quota, et pas par convention : le vrai binaire est hors de portée.

    Un profil qui *choisit* de ne pas appeler `agent` finit toujours par
    l'appeler une fois. Le PATH du banc commence par ses faux agents :
    `command -v agent` ne peut pas rendre autre chose.
    """
    banc = tmp_path / "banc"
    assert _sh(CRONS / "banc.sh", ATELIER_BANC=str(banc)).returncode == 0
    corps = (
        f'export ATELIER_BANC="{banc}"; source "{PROFILS}/atelier.sh"; '
        "command -v agent; command -v claude"
    )
    trouves = subprocess.run(
        ["bash", "-c", corps], text=True, capture_output=True, check=True
    ).stdout
    for ligne in trouves.splitlines():
        assert ligne.startswith(str(banc)), ligne


@besoin_bash
def test_le_profil_atelier_ne_touche_pas_forgehistory(tmp_path: Path):
    banc = tmp_path / "banc"
    _sh(CRONS / "banc.sh", ATELIER_BANC=str(banc))
    corps = (
        f'export ATELIER_BANC="{banc}"; source "{PROFILS}/atelier.sh"; '
        'echo "$ATELIER_PROJET"; echo "$ATELIER_WORKDIR_coder"; echo "$ATELIER_VERROUS"'
    )
    sortie = subprocess.run(
        ["bash", "-c", corps], text=True, capture_output=True, check=True
    ).stdout
    assert "ForgeHistory" not in sortie
    for ligne in sortie.splitlines():
        assert ligne.startswith(str(banc))


# ---------------------------------------------------------- le répartiteur


@besoin_bash
def test_sans_profil_le_repartiteur_ne_reveille_personne(tmp_path: Path):
    """Le défaut n'arme jamais : pas de fichier, pas de réveil."""
    r = _sh(REPARTITEUR, ATELIER_ETAT=str(tmp_path), ATELIER_ROOT=str(RACINE))
    assert r.returncode == 0
    assert r.stdout == ""


@besoin_bash
def test_un_profil_illisible_ne_reveille_personne(tmp_path: Path):
    (tmp_path / "profil").write_text("nawak\n", encoding="utf-8")
    r = _sh(REPARTITEUR, ATELIER_ETAT=str(tmp_path), ATELIER_ROOT=str(RACINE))
    assert r.returncode == 2
    assert "profil inconnu" in r.stderr


@besoin_bash
def test_un_profil_vide_vaut_l_arret(tmp_path: Path):
    (tmp_path / "profil").write_text("\n", encoding="utf-8")
    r = _sh(REPARTITEUR, ATELIER_ETAT=str(tmp_path), ATELIER_ROOT=str(RACINE))
    assert r.returncode == 0


# ------------------------------------------------------------- la bascule


@besoin_bash
def test_basculer_n_est_que_l_ecriture_d_un_fichier(tmp_path: Path):
    """Le point de toute la conception : aucun `sudo` sur ce chemin."""
    r = _sh(BOUCLE, "jour", ATELIER_ETAT=str(tmp_path), ATELIER_ROOT=str(RACINE))
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "profil").read_text(encoding="utf-8").strip() == "jour"

    r = _sh(BOUCLE, "arret", ATELIER_ETAT=str(tmp_path), ATELIER_ROOT=str(RACINE))
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "profil").read_text(encoding="utf-8").strip() == "arret"


@besoin_bash
def test_un_profil_inconnu_ne_remplace_pas_celui_qui_tourne(tmp_path: Path):
    _sh(BOUCLE, "jour", ATELIER_ETAT=str(tmp_path), ATELIER_ROOT=str(RACINE))
    r = _sh(BOUCLE, "nawak", ATELIER_ETAT=str(tmp_path), ATELIER_ROOT=str(RACINE))
    assert r.returncode == 2
    assert (tmp_path / "profil").read_text(encoding="utf-8").strip() == "jour"


@besoin_bash
def test_etat_dit_le_profil_depuis_quand_et_le_prochain_reveil(tmp_path: Path):
    _sh(BOUCLE, "jour", ATELIER_ETAT=str(tmp_path), ATELIER_ROOT=str(RACINE))
    r = _sh(BOUCLE, "etat", ATELIER_ETAT=str(tmp_path), ATELIER_ROOT=str(RACINE))
    assert r.returncode == 0, r.stderr
    assert "profil   jour" in r.stdout
    assert "depuis   " in r.stdout
    assert "prochain " in r.stdout
    assert "en cours " in r.stdout


@besoin_bash
def test_etat_dement_ca_tourne_quand_le_cron_n_appelle_pas_le_repartiteur(tmp_path: Path):
    """Un profil posé sans cron ne réveille personne, et il faut le dire."""
    _sh(BOUCLE, "jour", ATELIER_ETAT=str(tmp_path), ATELIER_ROOT=str(RACINE))
    r = _sh(BOUCLE, "etat", ATELIER_ETAT=str(tmp_path), ATELIER_ROOT=str(RACINE))
    if not Path("/etc/cron.d/forgeatelier").is_file():
        assert "ATTENTION" in r.stdout


@besoin_bash
def test_arret_attend_le_tour_en_cours_au_lieu_de_le_couper(tmp_path: Path):
    """Tuer un tour serait la façon la plus sûre de laisser une carte prise.

    `crons/tour.sh` range sa carte sur tous ses chemins de sortie ; il
    faut donc qu'il les atteigne. `arret` empêche les réveils suivants,
    puis attend.
    """
    import fcntl

    verrous = tmp_path / "verrous"
    verrous.mkdir()
    _sh(BOUCLE, "jour", ATELIER_ETAT=str(tmp_path), ATELIER_ROOT=str(RACINE))
    tenu = open(verrous / "atelier-coder.lock", "w")
    fcntl.flock(tenu.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        r = _sh(
            BOUCLE, "arret",
            ATELIER_ETAT=str(tmp_path), ATELIER_ROOT=str(RACINE),
            ATELIER_VERROUS=str(verrous), ATELIER_ARRET_ATTENTE="10",
        )
        # Il a attendu, puis il a dit qu'il attendait encore — il n'a pas
        # tué le tour, et il n'a pas prétendu que tout était calme.
        assert r.returncode == 1
        # Le profil a bien basculé — aucun réveil ne s'ajoutera — mais on
        # ne prétend pas que tout est calme.
        assert (tmp_path / "profil").read_text(encoding="utf-8").strip() == "arret"
        assert "coder" in (r.stdout + r.stderr)
    finally:
        fcntl.flock(tenu.fileno(), fcntl.LOCK_UN)
        tenu.close()


@besoin_bash
@pytest.mark.parametrize("script", ["atelier-boucle", "repartiteur.sh"])
def test_appele_par_un_lien_le_script_trouve_encore_ses_profils(tmp_path: Path, script):
    """Une commande qu'on tape vit dans ~/bin, et c'est un lien.

    `dirname "$0"` rend le répertoire du *lien*, pas celui du script :
    la racine devenait le parent de ~/bin, aucun profil n'était trouvé,
    et `atelier-boucle jour` refusait « profil inconnu : jour » sans
    rien basculer. Mesuré sur le VPS après un `ln -s` dans ~/bin.
    """
    bin_utilisateur = tmp_path / "bin"
    bin_utilisateur.mkdir()
    lien = bin_utilisateur / script
    lien.symlink_to(CRONS / script)

    etat = tmp_path / "etat"
    env = dict(os.environ)
    env.pop("ATELIER_ROOT", None)   # sans elle, la racine se dérive de $0
    env["ATELIER_ETAT"] = str(etat)
    r = subprocess.run(
        ["bash", str(lien), "jour"] if script == "atelier-boucle" else ["bash", str(lien)],
        text=True, capture_output=True, timeout=90, env=env,
    )
    assert r.returncode == 0, r.stderr
    if script == "atelier-boucle":
        assert (etat / "profil").read_text(encoding="utf-8").strip() == "jour"
        assert "profil inconnu" not in (r.stdout + r.stderr)


@besoin_bash
def test_le_crontab_livre_n_a_qu_une_ligne_et_n_arme_rien():
    """Ce que root installe une fois ne doit plus jamais changer."""
    texte = (CRONS / "crontab-repartiteur").read_text(encoding="utf-8")
    lignes = [
        l for l in texte.splitlines()
        if l.strip() and not l.startswith("#") and "=" not in l.split()[0]
    ]
    assert len(lignes) == 1, lignes
    assert "repartiteur.sh" in lignes[0]
    # L'armement vit dans le profil : sinon désarmer redemanderait root.
    # C'est la ligne active qu'on lit — le commentaire, lui, a le droit
    # de dire où ATELIER_INVOQUER a déménagé.
    actives = [l for l in texte.splitlines() if l.strip() and not l.startswith("#")]
    assert not any("ATELIER_INVOQUER" in l for l in actives), actives
