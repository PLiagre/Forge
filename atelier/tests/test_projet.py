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
def test_le_vrai_fichier_donne_son_modele_a_chacun_des_sept_roles(vrai):
    assert ROLES == ("cto", "chef", "developpeur", "relecteur", "lecteur", "testeur", "artiste")
    assert set(vrai.agents) == set(ROLES)
    for role, outil, modele in (
        ("cto", "claude", "fable"), ("chef", "claude", "opus"), ("developpeur", "claude", "sonnet"),
        ("relecteur", "claude", "opus"), ("lecteur", "claude", "haiku"), ("testeur", "claude", "opus"),
        ("artiste", "antigravity", "gemini-"),
    ):
        assert modele in vrai.agent(role).modele and vrai.agent(role).outil == outil, role


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


def test_le_vrai_fichier_a_les_quatre_pistes(vrai):
    assert vrai.pistes == ("monde", "ville", "interface", "asset")


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


def test_un_role_inconnu_se_refuse(tmp_path):
    """Le défaut : un rôle d'avant (le dépanneur) restait dans le fichier, et rien ne disait qu'il ne jouait plus."""
    _refus(tmp_path, TOML + 'depanneur = "claude/opus@high"\n', "[agents] nomme des rôles inconnus : depanneur")


def test_un_modele_hors_de_l_abonnement_se_refuse(tmp_path):
    for ligne in ("claude/gpt-5", "claude/gpt-5-opus", "claude/opusculaire"):
        _refus(tmp_path, _avec_chef(ligne), "[agents].chef", ligne, "seuls les modèles de l'abonnement Claude tournent")
    _refus(tmp_path, _avec_chef("antigravity/gpt-5"), "[agents].chef",
           "seuls les modèles Gemini de l'abonnement Google")


def test_un_harnais_inconnu_se_refuse(tmp_path):
    _refus(tmp_path, _avec_chef("codex/opus@high"),
           "[agents].chef : outil inconnu 'codex' (connus : antigravity, claude)")


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
    _refus(tmp_path, TOML + "\n[machines]\nmac = 1\n", "[machines] ne connaît pas 'mac' (connus : vps, pc, asset)")
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
    assert (projet.capacite("vps"), projet.capacite("pc"), projet.capacite("asset"), projet.plafond("claude")) == (
        1, 1, 1, None)
    assert (vrai.delai("chef"), vrai.delai("lecteur"), vrai.delai("artiste")) == (3600, 600, 1800)
    assert (vrai.capacite("vps"), vrai.capacite("pc"), vrai.capacite("asset"),
            vrai.plafond("claude"), vrai.plafond("antigravity")) == (2, 2, 1, 4, 1)
    with pytest.raises(ProjetIncomplet, match="depanneur"):
        projet.agent("depanneur")


def test_la_table_des_roles_a_sept_lignes_et_dit_le_parallelisme_et_le_poids_du_testeur(projet, vrai):
    lignes = table_des_roles(vrai).splitlines()
    assert [l.split()[0] for l in lignes[1:8]] == list(ROLES) and lignes[8] == ""
    assert lignes[1].split() == ["cto", "claude-fable-5-2", "high", "1800", "s"]
    assert lignes[5].split() == ["lecteur", "claude-haiku-5-5", "medium", "600", "s"]
    assert lignes[6].split() == ["testeur", "claude-opus-5-5", "high", "2700", "s"]
    assert lignes[7].split() == ["artiste", "gemini-3.8-flash-medium", "—", "1800", "s"]
    assert lignes[-3:] == ["lots en même temps : vps 2, pc 2, asset 1",
                           "agents en même temps : antigravity 1, claude 4",
                           "verdict du testeur : il ouvre l'étape suivante ; après 5 « non tenue » de suite, le "
                           "propriétaire décide"]
    assert table_des_roles(projet).splitlines()[-3:] == [
        "lots en même temps : vps 1, pc 1, asset 1", "agents en même temps : sans plafond",
        "verdict du testeur : il informe ; le « oui » du propriétaire ouvre l'étape suivante"]


def test_le_poids_du_verdict_du_testeur_se_regle_et_se_refuse_s_il_se_lit_mal(tmp_path, vrai):
    """Sans la section, le testeur informe et le propriétaire ouvre : un dépôt ne perd pas sa garde par oubli."""
    assert (vrai.testeur_ouvre, vrai.testeur_refus_max) == (True, 5)
    assert (_charger(tmp_path, TOML).testeur_ouvre, _charger(tmp_path, TOML).testeur_refus_max) == (False, 2)
    regle = _charger(tmp_path, TOML + "\n[testeur]\nouvre = true\nrefus_max = 3\n")
    assert (regle.testeur_ouvre, regle.testeur_refus_max) == (True, 3)
    _refus(tmp_path, TOML + '\n[testeur]\nouvre = "oui"\n', "[testeur].ouvre doit être true ou false")
    _refus(tmp_path, TOML + "\n[testeur]\nrefus_max = 0\n", "[testeur].refus_max doit être un entier ≥ 1, pas 0")
    _refus(tmp_path, TOML + "\n[testeur]\nouvert = true\n", "[testeur] ne connaît pas 'ouvert'")


def test_changer_un_role_de_modele_est_une_ligne(tmp_path):
    avant = _charger(tmp_path, TOML)
    apres = _charger(tmp_path, _avec_chef("claude/sonnet@max"))
    assert str(avant.agent("chef")) == "claude/opus@high" and str(apres.agent("chef")) == "claude/sonnet@max"
    assert {r: a for r, a in apres.agents.items() if r != "chef"} == {r: a for r, a in avant.agents.items() if r != "chef"}
    assert dataclasses.replace(apres, agents=avant.agents) == avant, "rien d'autre ne change"
