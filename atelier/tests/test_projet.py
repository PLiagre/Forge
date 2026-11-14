"""Le branchement du dépôt : `atelier.toml` se charge, ou se refuse en nommant la faute.

Le défaut que ces tests gardent : un réglage mal écrit (un rôle de trop, un
modèle hors de l'abonnement, une capacité à zéro) passait pour un réglage qui
joue, et la chaîne s'arrêtait ou appelait le mauvais modèle sans le dire.
"""

from __future__ import annotations

import dataclasses

import pytest

from atelier.projet import ROLES, Projet, ProjetIncomplet, charger, table_des_roles

from conftest import RACINE, TOML

CHEF = 'chef        = "claude/opus@high"'


@pytest.fixture(scope="module")
def vrai():
    """Le vrai `atelier.toml` de la racine du dépôt."""
    return charger(RACINE)


def _charger(tmp_path, texte):
    (tmp_path / "atelier.toml").write_text(texte, encoding="utf-8")
    return charger(tmp_path)


def _refus(tmp_path, texte, *fautes):
    """Le chargement refuse ce fichier, et son message nomme la faute."""
    with pytest.raises(ProjetIncomplet) as refus:
        _charger(tmp_path, texte)
    for faute in fautes:
        assert faute in str(refus.value)


def _sans(debut):
    """Le fichier d'essai, sans la ligne qui commence ainsi."""
    lignes = TOML.splitlines()
    gardees = [l for l in lignes if not l.startswith(debut)]
    assert len(gardees) == len(lignes) - 1
    return "\n".join(gardees)


def _avec_chef(ligne):
    assert CHEF in TOML
    return TOML.replace(CHEF, f'chef        = "{ligne}"')


# ------------------------------------------------------- le vrai fichier
def test_le_vrai_fichier_donne_son_modele_a_chacun_des_cinq_roles(vrai):
    assert ROLES == ("cto", "chef", "developpeur", "relecteur", "lecteur") and set(vrai.agents) == set(ROLES)
    for role, modele in (("cto", "fable"), ("chef", "opus"), ("developpeur", "sonnet"), ("relecteur", "opus"),
                         ("lecteur", "haiku")):
        assert modele in vrai.agent(role).modele and vrai.agent(role).outil == "claude", role


def test_le_vrai_fichier_interdit_a_un_lot_les_regles_et_la_chaine(vrai):
    for chemin in ("CLAUDE.md", "AGENTS.md", "CAP.md", "atelier.toml", "atelier/pilote.py",
                   "atelier/tests/test_projet.py", ".github/workflows/tests.yml"):
        assert vrai.interdit(chemin), chemin
    for chemin in ("jeu/sim/faim.py", "jeu/sim/CLAUDE.md", "3d/unity/Assets/Interface/Carte.cs", "docs/VISION.md"):
        assert not vrai.interdit(chemin), chemin


def test_le_vrai_fichier_nomme_le_coeur_du_moteur(vrai):
    assert vrai.touche_le_coeur(["jeu/data/armees.toml", "jeu/sim/engine.py"])
    assert not vrai.touche_le_coeur(["jeu/sim/faim.py", "jeu/sim/tests/test_engine.py"])
    assert not vrai.touche_le_coeur([])


def test_le_vrai_fichier_a_les_trois_pistes(vrai):
    assert vrai.pistes == ("monde", "ville", "interface")


def test_il_n_y_a_plus_de_plafond_de_lignes(vrai):
    assert "lignes_max" not in (RACINE / "atelier.toml").read_text(encoding="utf-8")
    assert "lignes_max" not in {champ.name for champ in dataclasses.fields(Projet)} and not hasattr(vrai, "lignes_max")


# ------------------------------------------------------------ les refus
def test_un_fichier_absent_se_refuse(tmp_path):
    with pytest.raises(ProjetIncomplet, match="atelier.toml introuvable"):
        charger(tmp_path)


def test_un_champ_obligatoire_manquant_se_refuse_par_son_nom(tmp_path):
    for champ in ("depot", "proprietaire", "interdits", "pistes", "corrections_max"):
        _refus(tmp_path, _sans(f"{champ} "), f"[projet] ne dit pas : {champ}")


def test_un_role_manquant_se_refuse_par_son_nom(tmp_path):
    _refus(tmp_path, _sans("lecteur"), "[agents] ne nomme pas : lecteur")


def test_un_sixieme_role_se_refuse(tmp_path):
    """Le défaut : un rôle d'avant (le dépanneur) restait dans le fichier, et rien ne disait qu'il ne jouait plus."""
    _refus(tmp_path, TOML + 'depanneur = "claude/opus@high"\n', "[agents] nomme des rôles inconnus : depanneur")


def test_un_modele_hors_de_l_abonnement_se_refuse(tmp_path):
    for ligne in ("claude/gpt-5", "claude/gpt-5-opus", "claude/opusculaire"):
        _refus(tmp_path, _avec_chef(ligne), "[agents].chef", ligne, "seuls les modèles de l'abonnement Claude tournent")


def test_un_harnais_inconnu_se_refuse(tmp_path):
    _refus(tmp_path, _avec_chef("codex/opus@high"), "[agents].chef : outil inconnu 'codex' (connus : claude)")


def test_un_effort_inconnu_se_refuse(tmp_path):
    _refus(tmp_path, _avec_chef("claude/opus@turbo"), "[agents].chef", "ne connaît pas l'effort 'turbo'", "xhigh")


def test_une_ligne_de_role_illisible_se_refuse(tmp_path):
    for ligne in ("opus", "claude/opus@", "claude/opus @high", "/opus", "claude/"):
        _refus(tmp_path, _avec_chef(ligne), "[agents].chef illisible", "attendu : harnais/modèle@effort")
    _refus(tmp_path, _avec_chef(""), "[agents].chef est vide")
    _refus(tmp_path, TOML.replace(CHEF, "chef        = 3"), "[agents].chef est vide")


def test_le_delai_d_un_role_inconnu_se_refuse(tmp_path):
    _refus(tmp_path, TOML + "\n[delais]\ndepanneur = 600\n", "[delais] nomme des rôles inconnus : depanneur")


def test_une_capacite_nulle_ou_negative_se_refuse(tmp_path):
    """Le défaut : un zéro arrêtait la chaîne sans le dire."""
    for section, cle, valeur in (("machines", "vps", "0"), ("machines", "pc", "-1"), ("machines", "vps", "true"),
                                 ("machines", "vps", "1.5"), ("outils", "claude", "0"), ("delais", "chef", "0")):
        _refus(tmp_path, TOML + f"\n[{section}]\n{cle} = {valeur}\n", f"[{section}].{cle} doit être un entier ≥ 1, pas")


def test_une_machine_inconnue_se_refuse(tmp_path):
    _refus(tmp_path, TOML + "\n[machines]\nmac = 1\n", "[machines] ne connaît pas 'mac' (connus : vps, pc)")
    _refus(tmp_path, TOML + "\n[outils]\ncodex = 2\n", "[outils] ne connaît pas 'codex'")
    _refus(tmp_path, TOML + "\n[gardes]\nlignes_max = 800\n", "[gardes] ne connaît pas 'lignes_max'")


def test_un_jours_max_nul_se_refuse(tmp_path):
    _refus(tmp_path, TOML + "\n[gardes]\njours_max = 0\n", "[gardes].jours_max doit être un entier ≥ 1, pas 0")
    assert _charger(tmp_path, TOML + "\n[gardes]\njours_max = 30\n").jours_max == 30


# ----------------------------------------------------- ce que dit Projet
def test_interdit_un_chemin_exact_ou_tout_un_dossier_pas_un_nom_voisin(projet):
    assert projet.interdit("atelier.toml") and projet.interdit("atelier/crons/tour.sh")
    assert projet.interdit(".github/ISSUE_TEMPLATE/lot.yml")
    assert not projet.interdit("atelier.toml.bak")
    assert not projet.interdit("atelier-notes/idee.md") and not projet.interdit("jeu/atelier/x.py")


def test_les_antislashs_de_windows_n_ouvrent_pas_un_chemin_interdit(projet):
    assert projet.interdit("atelier\\pilote.py") and projet.interdit(".github\\workflows\\tests.yml")
    assert projet.touche_le_coeur(["jeu\\sim\\engine.py"]) and not projet.interdit("jeu\\sim\\faim.py")


def test_le_delai_la_capacite_et_le_plafond_se_lisent_ou_prennent_leur_defaut(projet, vrai):
    assert all(projet.delai(role) == 1800 for role in ROLES), "sans [delais], trente minutes"
    assert (projet.capacite("vps"), projet.capacite("pc"), projet.plafond("claude")) == (1, 1, None)
    assert (vrai.delai("chef"), vrai.delai("lecteur")) == (3600, 600)
    assert (vrai.capacite("vps"), vrai.capacite("pc"), vrai.plafond("claude")) == (2, 1, 4)
    with pytest.raises(ProjetIncomplet, match="depanneur"):
        projet.agent("depanneur")


def test_la_table_des_roles_a_cinq_lignes_et_dit_le_parallelisme(projet, vrai):
    lignes = table_des_roles(vrai).splitlines()
    assert [l.split()[0] for l in lignes[1:6]] == list(ROLES) and lignes[6] == ""
    assert lignes[1].split() == ["cto", "claude-fable-5-2", "high", "1800", "s"]
    assert lignes[5].split() == ["lecteur", "claude-haiku-5-5", "medium", "600", "s"]
    assert lignes[-2:] == ["lots en même temps : vps 2, pc 1", "agents en même temps : claude 4"]
    assert table_des_roles(projet).splitlines()[-2:] == ["lots en même temps : vps 1, pc 1",
                                                         "agents en même temps : sans plafond"]


def test_changer_un_role_de_modele_est_une_ligne(tmp_path):
    avant = _charger(tmp_path, TOML)
    apres = _charger(tmp_path, _avec_chef("claude/sonnet@max"))
    assert str(avant.agent("chef")) == "claude/opus@high" and str(apres.agent("chef")) == "claude/sonnet@max"
    assert {r: a for r, a in apres.agents.items() if r != "chef"} == {r: a for r, a in avant.agents.items() if r != "chef"}
    assert dataclasses.replace(apres, agents=avant.agents) == avant, "rien d'autre ne change"
