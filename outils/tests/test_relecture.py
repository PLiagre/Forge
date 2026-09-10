"""Celui qui a écrit le code ne dit pas s'il est recevable."""

from outils import github

from outils import relecture
from outils.relecture import Revue

TETE = "a" * 40
AVANT = "b" * 40


def test_une_approbation_d_un_tiers_sur_la_tete_passe():
    verdict = relecture.juger(TETE, ["cursor[bot]"], [Revue("claude[bot]", "APPROVED", TETE)])
    assert verdict.passe


def test_sans_approbation_rien_ne_passe():
    verdict = relecture.juger(TETE, ["cursor[bot]"], [])
    assert not verdict.passe
    assert "absente" in verdict.raison


def test_une_approbation_sur_une_revision_anterieure_est_perimee():
    verdict = relecture.juger(TETE, ["cursor[bot]"], [Revue("claude[bot]", "APPROVED", AVANT)])
    assert not verdict.passe
    assert "périmée" in verdict.raison


def test_l_auteur_du_code_ne_s_approuve_pas_lui_meme():
    verdict = relecture.juger(TETE, ["cursor[bot]"], [Revue("cursor[bot]", "APPROVED", TETE)])
    assert not verdict.passe
    assert "recevable" in verdict.raison


def test_la_casse_de_la_connexion_ne_contourne_pas_la_regle():
    verdict = relecture.juger(TETE, ["Cursor[bot]"], [Revue("cursor[BOT]", "APPROVED", TETE)])
    assert not verdict.passe


def test_un_auteur_parmi_d_autres_approbateurs_ne_suffit_pas_a_bloquer():
    verdict = relecture.juger(
        TETE, ["cursor[bot]"],
        [Revue("cursor[bot]", "APPROVED", TETE), Revue("PLiagre", "APPROVED", TETE)],
    )
    assert verdict.passe
    assert "pliagre" in verdict.raison


def test_des_changements_demandes_bloquent():
    verdict = relecture.juger(
        TETE, ["cursor[bot]"],
        [Revue("PLiagre", "APPROVED", TETE), Revue("claude[bot]", "CHANGES_REQUESTED", TETE)],
    )
    assert not verdict.passe
    assert "changements demandés" in verdict.raison


def test_des_changements_demandes_puis_leves_ne_bloquent_plus():
    verdict = relecture.juger(
        TETE, ["cursor[bot]"],
        [Revue("claude[bot]", "CHANGES_REQUESTED", TETE), Revue("claude[bot]", "APPROVED", TETE)],
    )
    assert verdict.passe


def test_des_changements_demandes_sur_une_revision_anterieure_ne_bloquent_plus():
    """Le code a bougé : ce refus-là parlait d'un autre code. C'est la
    même règle que pour l'approbation, dans l'autre sens."""
    verdict = relecture.juger(
        TETE, ["cursor[bot]"],
        [Revue("claude[bot]", "CHANGES_REQUESTED", AVANT), Revue("PLiagre", "APPROVED", TETE)],
    )
    assert verdict.passe


def test_un_commentaire_ne_verdit_rien():
    verdict = relecture.juger(TETE, ["cursor[bot]"], [Revue("claude[bot]", "COMMENTED", TETE)])
    assert not verdict.passe


def test_une_revue_sans_revision_ne_porte_sur_rien():
    verdict = relecture.juger(TETE, ["cursor[bot]"], [Revue("claude[bot]", "APPROVED", "")])
    assert not verdict.passe


def test_sans_auteur_connu_la_regle_ne_peut_pas_etre_tenue():
    """Rule 10 : une donnée absente ne se devine pas. Si on ne sait pas
    qui a écrit le code, on ne peut pas affirmer que le relecteur n'en
    est pas — et on refuse au lieu de supposer."""
    verdict = relecture.juger(TETE, [], [Revue("claude[bot]", "APPROVED", TETE)])
    assert not verdict.passe
    assert "auteur" in verdict.raison


def test_sans_revision_connue_il_n_y_a_rien_a_relire():
    assert not relecture.juger("", ["cursor[bot]"], []).passe


class _GithubRelecture:
    """GitHub de banc : la CLI pose PASS/FAIL et un code, c'est tout ce que le workflow lit."""

    def __init__(self, sha, auteurs, revues_brutes):
        self.sha = sha
        self.auteurs = auteurs
        self.revues_brutes = revues_brutes

    def get(self, _chemin, **_k):
        return {"head": {"sha": self.sha}}


def _cli_relecture(monkeypatch, capsys, faux, revision=None):
    from outils.__main__ import main

    monkeypatch.setattr(github, "Github", lambda *a, **k: faux)
    monkeypatch.setattr(github, "auteurs_du_code", lambda *_a, **_k: faux.auteurs)
    monkeypatch.setattr(github, "revues", lambda *_a, **_k: faux.revues_brutes)
    argv = ["relecture", "--depot", "O/R", "--pr", "200", "--jeton", "x"]
    if revision is not None:
        argv.extend(["--revision", revision])
    code = main(argv)
    return code, capsys.readouterr()


def test_cli_relecture_pass_est_un_succes(monkeypatch, capsys):
    """Le workflow pose `success` si le code est 0. Inverser, c'est verdier sans relecture."""
    faux = _GithubRelecture(
        TETE,
        ["cursor[bot]"],
        [{"user": {"login": "claude[bot]"}, "state": "APPROVED", "commit_id": TETE}],
    )
    code, io = _cli_relecture(monkeypatch, capsys, faux, revision=TETE)
    assert code == 0
    assert io.out.startswith("PASS  PR 200")
    assert io.err == ""


def test_cli_relecture_fail_est_un_echec(monkeypatch, capsys):
    """Le workflow pose `failure` si le code n'est pas 0. Un PASS ici laisserait entrer."""
    faux = _GithubRelecture(TETE, ["cursor[bot]"], [])
    code, io = _cli_relecture(monkeypatch, capsys, faux, revision=TETE)
    assert code == 1
    assert io.out.startswith("FAIL  PR 200")
    assert "absente" in io.out or "périmée" in io.out
    assert io.err == ""


def test_cli_relecture_l_auteur_ne_s_approuve_pas_en_passant(monkeypatch, capsys):
    """La règle de rôle tient aussi à la couture CLI : exit 1, pas un PASS déguisé."""
    faux = _GithubRelecture(
        TETE,
        ["cursor[bot]"],
        [{"user": {"login": "cursor[bot]"}, "state": "APPROVED", "commit_id": TETE}],
    )
    code, io = _cli_relecture(monkeypatch, capsys, faux, revision=TETE)
    assert code == 1
    assert io.out.startswith("FAIL  PR 200")
    assert "recevable" in io.out


def test_cli_relecture_sans_revision_prend_la_tete(monkeypatch, capsys):
    """Sans `--revision`, c'est la tête de la PR. En juger une autre, c'est périmer à l'envers."""
    faux = _GithubRelecture(
        TETE,
        ["cursor[bot]"],
        [{"user": {"login": "claude[bot]"}, "state": "APPROVED", "commit_id": TETE}],
    )
    code, io = _cli_relecture(monkeypatch, capsys, faux)
    assert code == 0
    assert io.out.startswith("PASS  PR 200")
