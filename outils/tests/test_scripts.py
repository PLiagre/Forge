"""Les gestes des workflows, joués sur le banc.

Un seul de ces contrôles aurait suffi à voir la panne du 4 septembre 2026 :
`relecture.sh` mourait sur `errexit` avant de poser son état. Le banc joue
les scripts avec `bash -e`, comme GitHub, avec de faux `gh`, `git` et
`python` — et il affirme le **geste**, pas le message.
"""

import re

import pytest

from outils.tests.banc import Banc

TETE = "a" * 40


@pytest.fixture
def banc(tmp_path):
    return Banc(tmp_path)


# ------------------------------------------------------------ relecture


def test_un_verdict_defavorable_pose_quand_meme_son_etat(banc):
    """Le cas exact de la PR 225 : la relecture manque, la commande sort 1,
    et c'est justement là que l'état doit être posé — en rouge."""
    banc.poser("python", "FAIL  PR 225 — aucune approbation : relecture absente", code=1)
    banc.poser("gh")
    resultat = banc.jouer("relecture.sh", DEPOT="o/r", PR="225", REVISION=TETE)

    assert resultat.returncode == 0, resultat.stderr
    pose = banc.appel("gh", "statuses")
    assert pose is not None, banc.appels
    assert banc.valeur(pose, "state") == "failure"
    assert banc.valeur(pose, "context") == "relecture"
    assert "relecture absente" in (banc.valeur(pose, "description") or "")


def test_un_verdict_favorable_pose_un_etat_vert(banc):
    banc.poser("python", "PASS  PR 225 — approuvée sur aaaaaaa par pliagre", code=0)
    banc.poser("gh")
    resultat = banc.jouer("relecture.sh", DEPOT="o/r", PR="225", REVISION=TETE)

    assert resultat.returncode == 0
    assert banc.valeur(banc.appel("gh", "statuses"), "state") == "success"


def test_la_revision_absente_se_demande(banc):
    banc.poser("python", "PASS  PR 225 — approuvée", code=0)
    banc.poser("gh", sortie=TETE)
    resultat = banc.jouer("relecture.sh", DEPOT="o/r", PR="225", REVISION="")

    assert resultat.returncode == 0
    assert banc.appel("gh pr view 225") is not None
    # L'état est posé sur la révision qu'on vient de demander, pas ailleurs.
    assert banc.appel("gh", f"statuses/{TETE}") is not None


def test_sans_revision_lisible_on_refuse_au_lieu_de_poser_n_importe_ou(banc):
    banc.poser("python", "PASS", code=0)
    banc.poser("gh", sortie="", code=1)
    resultat = banc.jouer("relecture.sh", DEPOT="o/r", PR="225", REVISION="")

    assert resultat.returncode == 1
    assert banc.appel("gh", "statuses") is None
    assert "introuvable" in resultat.stderr


def test_un_etat_refuse_par_github_fait_rougir_le_travail(banc):
    """Ce script rend compte de lui-même : s'il n'a pas posé l'état, il
    doit rougir — sinon un contrôle absent passerait pour un contrôle
    qu'on a choisi de ne pas poser."""
    banc.poser("python", "FAIL  PR 225 — relecture absente", code=1)
    banc.poser("gh", code=1)
    resultat = banc.jouer("relecture.sh", DEPOT="o/r", PR="225", REVISION=TETE)

    assert resultat.returncode == 1
    assert "non posé" in resultat.stderr


def test_un_outil_muet_n_approuve_rien(banc):
    """Un verdict vide avec un code 0 est le pire des cas : il poserait un
    « success » que personne n'a prononcé. On refuse."""
    banc.poser("python", "", code=0)
    banc.poser("gh")
    resultat = banc.jouer("relecture.sh", DEPOT="o/r", PR="225", REVISION=TETE)

    assert resultat.returncode == 1
    assert banc.appel("gh", "statuses") is None
    assert "vide" in resultat.stderr


def test_le_lien_du_journal_accompagne_l_etat(banc):
    banc.poser("python", "PASS  PR 225 — approuvée", code=0)
    banc.poser("gh")
    banc.jouer("relecture.sh", DEPOT="o/r", PR="225", REVISION=TETE,
               LIEN="https://github.com/o/r/actions/runs/1")
    pose = banc.appel("gh", "statuses")
    assert banc.valeur(pose, "target_url") == "https://github.com/o/r/actions/runs/1"


def test_sans_lien_l_etat_se_pose_quand_meme(banc):
    """Un `target_url` vide laisserait un lien mort sur le contrôle."""
    banc.poser("python", "PASS  PR 225 — approuvée", code=0)
    banc.poser("gh")
    banc.jouer("relecture.sh", DEPOT="o/r", PR="225", REVISION=TETE, LIEN="")
    pose = banc.appel("gh", "statuses")
    assert pose is not None
    assert banc.valeur(pose, "target_url") is None


# ----------------------------------------------------------- intégration


def test_fusionner_fusionne_range_la_branche_et_relance_le_tour(banc):
    banc.poser("gh", sortie="agent/049-fabriquer")
    resultat = banc.jouer(
        "integrer.sh", DEPOT="o/r", DECISION="fusionner 217", BASE="master",
        SORTIE=str(banc.dossier / "sortie.txt"),
    )

    assert resultat.returncode == 0, resultat.stderr
    assert banc.appel("gh pr merge 217 --merge") is not None
    assert banc.appel("gh api -X DELETE", "agent/049-fabriquer") is not None
    assert banc.appel("gh workflow run integration.yml") is not None
    assert "fusionnee=217" in (banc.dossier / "sortie.txt").read_text(encoding="utf-8")


def test_une_branche_qu_on_ne_peut_pas_supprimer_n_annule_pas_la_fusion(banc):
    """Un rangement raté ne coûte pas le tour : la fusion est faite, et le
    tour suivant doit partir quand même."""
    banc.poser("gh", selon=[
        (["--json headRefName"], "agent/049-fabriquer"),
        (["api", "-X", "DELETE"], "", 1),
    ])
    resultat = banc.jouer(
        "integrer.sh", DEPOT="o/r", DECISION="fusionner 217",
        SORTIE=str(banc.dossier / "sortie.txt"),
    )

    assert resultat.returncode == 0, resultat.stderr
    assert "fusionnee=217" in (banc.dossier / "sortie.txt").read_text(encoding="utf-8")
    assert banc.appel("gh workflow run integration.yml") is not None
    assert "non supprimée" in resultat.stdout


def test_une_fusion_refusee_fait_rougir_le_tour(banc):
    """L'inverse du cas précédent : si c'est la fusion qui échoue, rien
    n'est fusionné et le tour doit le dire."""
    banc.poser("gh", selon=[
        (["--json headRefName"], "agent/049-fabriquer"),
        (["pr", "merge"], "", 1),
    ])
    resultat = banc.jouer(
        "integrer.sh", DEPOT="o/r", DECISION="fusionner 217",
        SORTIE=str(banc.dossier / "sortie.txt"),
    )

    assert resultat.returncode != 0
    assert not (banc.dossier / "sortie.txt").exists()


def test_rebaser_attend_que_la_tete_ait_bouge_avant_de_redemander(banc):
    """`update-branch` rend 202 : GitHub accepte et pousse plus tard. Un
    contrôle demandé trop tôt s'épingle sur l'ANCIENNE révision, et la
    nouvelle n'en a jamais — bloquée sans rien de rouge à montrer."""
    banc.poser("gh", selon=[
        (["--json headRefName"], "agent/049-fabriquer"),
        # La tête ne bouge qu'au troisième coup d'œil.
        (["--json headRefOid"], ["a" * 40, "a" * 40, "b" * 40]),
    ])
    resultat = banc.jouer("integrer.sh", DEPOT="o/r", DECISION="rebaser 217", BASE="master")

    assert resultat.returncode == 0, resultat.stderr
    assert banc.appel("gh api -X PUT", "update-branch") is not None
    # Les trois contrôles sont demandés APRÈS le dernier coup d'œil.
    rangs = {a[0] + " " + " ".join(a[1:4]): i for i, a in enumerate(banc.brut)}
    dernier_coup = max(i for i, a in enumerate(banc.brut) if "headRefOid" in " ".join(a))
    for travail in ("tests.yml", "security.yml", "relecture.yml"):
        demande = next(i for i, a in enumerate(banc.brut) if travail in " ".join(a))
        assert demande > dernier_coup, f"{travail} demandé trop tôt"
    assert rangs is not None
    assert banc.valeur(banc.appel("gh workflow run relecture.yml"), "pr") == "217"


def test_une_tete_qui_ne_bouge_pas_rougit_au_lieu_de_demander_pour_rien(banc):
    banc.poser("gh", selon=[
        (["--json headRefName"], "agent/049-fabriquer"),
        (["--json headRefOid"], "a" * 40),
    ])
    resultat = banc.jouer("integrer.sh", DEPOT="o/r", DECISION="rebaser 217", BASE="master")

    assert resultat.returncode == 1
    assert "n'a pas bougé" in resultat.stderr
    assert banc.appel("gh workflow run tests.yml") is None


def test_rien_ne_touche_a_rien(banc):
    banc.poser("gh")
    resultat = banc.jouer("integrer.sh", DEPOT="o/r", DECISION="RIEN")

    assert resultat.returncode == 0
    assert banc.appels == []


def test_une_decision_illisible_rougit_au_lieu_de_ne_rien_faire(banc):
    """« Rien » et « je n'ai pas compris » sont deux réponses différentes.
    Les confondre arrêterait la file sans que personne le sache."""
    banc.poser("gh")
    resultat = banc.jouer("integrer.sh", DEPOT="o/r", DECISION="fusionnez-moi ça")

    assert resultat.returncode == 1
    assert "illisible" in resultat.stderr
    assert banc.appels == []


# ---------------------------------------------------------------- palier


def _projet(banc):
    (banc.dossier / "ROADMAP.md").write_text("# registre\n", encoding="utf-8")
    (banc.dossier / "palier.log").write_text(
        "couche 1  finie  (couverts : — · à couvrir : 046, 050)\n", encoding="utf-8"
    )


def _github_sans_palier(banc, url="https://github.com/o/r/pull/231"):
    """Aucune PR de palier ouverte, aucune branche qui traîne."""
    banc.poser("gh", selon=[(["pr list"], "")], sortie=url)
    banc.poser("git", selon=[(["ls-remote"], "", 2)])


def test_le_palier_ouvre_sa_branche_son_commit_et_sa_pr(banc):
    _projet(banc)
    _github_sans_palier(banc)
    resultat = banc.jouer(
        "palier.sh", DEPOT="o/r", LIGNE="palier 055 055-stabilisation-couche-1 couche=1",
        BASE="master", COMPTE_RENDU="palier.log",
    )

    assert resultat.returncode == 0, resultat.stderr
    assert banc.appel("git checkout -b feuille/055-stabilisation-couche-1") is not None
    assert banc.appel("git add ROADMAP.md") is not None
    assert banc.appel("git commit --file message.txt") is not None
    assert banc.appel("git push -u origin feuille/055-stabilisation-couche-1") is not None
    assert banc.appel("gh pr create") is not None
    # Le numéro de la PR se lit dans l'URL rendue, pas dans un second appel.
    assert banc.valeur(banc.appel("gh workflow run relecture.yml"), "pr") == "231"


def test_le_commit_du_palier_porte_une_connexion_que_github_sait_relier(banc):
    """Une adresse que GitHub ne relie à personne rend `auteurs_du_code`
    vide : la relecture refuse avant même de regarder les approbations, et
    la PR du palier ne peut plus jamais devenir intégrable."""
    _projet(banc)
    _github_sans_palier(banc)
    banc.jouer("palier.sh", DEPOT="o/r",
               LIGNE="palier 055 055-stabilisation-couche-1 couche=1", COMPTE_RENDU="palier.log")

    courriel = banc.appel("git config user.email")
    assert courriel is not None
    assert courriel[-1].endswith("users.noreply.github.com"), courriel
    assert "[bot]" in banc.appel("git config user.name")[-1]


def test_le_corps_de_la_pr_reprend_le_compte_rendu_du_registre(banc):
    _projet(banc)
    _github_sans_palier(banc)
    banc.jouer(
        "palier.sh", DEPOT="o/r", LIGNE="palier 055 055-stabilisation-couche-1 couche=1",
        COMPTE_RENDU="palier.log",
    )
    corps = (banc.dossier / "corps.txt").read_text(encoding="utf-8")
    assert "à couvrir : 046, 050" in corps
    assert "a-briefer" in corps
    message = (banc.dossier / "message.txt").read_text(encoding="utf-8")
    assert message.startswith("Palier couche 1 : le lot 055 entre au registre.")


def test_une_pr_de_palier_ouverte_empeche_le_second_depot(banc):
    """La garde porte sur la couche : le numéro libre peut avoir changé
    entre deux tours, la couche non."""
    _projet(banc)
    banc.poser("gh", selon=[(["pr list"], "231")])
    banc.poser("git")
    resultat = banc.jouer(
        "palier.sh", DEPOT="o/r", LIGNE="palier 057 057-stabilisation-couche-1 couche=1",
        COMPTE_RENDU="palier.log",
    )

    assert resultat.returncode == 0
    assert "déjà" in resultat.stdout
    assert banc.appel("gh pr create") is None
    assert banc.appel("git checkout") is None


def test_une_branche_sans_pr_ouverte_ne_bloque_pas_le_palier(banc):
    """Une PR fermée laissait sa branche derrière elle, et cette branche
    bloquait la couche pour toujours, en silence. Refuser un palier se
    fait en passant sa fiche à « abandonne », pas en fermant sa PR."""
    _projet(banc)
    banc.poser("gh", selon=[(["pr list"], "")], sortie="https://github.com/o/r/pull/240")
    banc.poser("git", selon=[(["ls-remote"], "abc\trefs/heads/feuille/055-stabilisation-couche-1", 0)])
    resultat = banc.jouer(
        "palier.sh", DEPOT="o/r", LIGNE="palier 055 055-stabilisation-couche-1 couche=1",
        COMPTE_RENDU="palier.log",
    )

    assert resultat.returncode == 0, resultat.stderr
    assert banc.appel("git push origin --delete feuille/055-stabilisation-couche-1") is not None
    assert banc.appel("gh pr create") is not None


def test_rien_a_deposer_ne_touche_ni_git_ni_github(banc):
    _projet(banc)
    banc.poser("git")
    banc.poser("gh")
    resultat = banc.jouer("palier.sh", DEPOT="o/r", LIGNE="RIEN")

    assert resultat.returncode == 0
    assert banc.appels == []


# ------------------------------------------------------------- saisie


def _registre(banc):
    (banc.dossier / "ROADMAP.md").write_text("# registre\n", encoding="utf-8")


def test_une_demande_devient_une_branche_une_pr_et_une_reponse(banc):
    _registre(banc)
    banc.poser("git", selon=[(["ls-remote"], "", 2)])
    banc.poser("gh", sortie="https://github.com/o/r/pull/240")
    resultat = banc.jouer(
        "lot.sh", DEPOT="o/r", LIGNE="lot 055 055-les-routes", BASE="master", ISSUE="12",
    )

    assert resultat.returncode == 0, resultat.stderr
    assert banc.appel("git checkout -b feuille/055-les-routes") is not None
    assert banc.appel("git add ROADMAP.md") is not None
    assert banc.appel("git push -u origin feuille/055-les-routes") is not None
    assert banc.appel("gh pr create") is not None
    # Les contrôles sont redemandés : une PR du jeton d'Actions n'en a aucun.
    assert banc.valeur(banc.appel("gh workflow run relecture.yml"), "pr") == "240"
    # La demande reçoit sa réponse et se referme : personne ne se demande
    # ce qu'elle est devenue.
    assert banc.appel("gh issue comment 12") is not None
    assert banc.appel("gh issue close 12") is not None


def test_le_commit_de_la_fiche_porte_une_connexion_reliable(banc):
    _registre(banc)
    banc.poser("git", selon=[(["ls-remote"], "", 2)])
    banc.poser("gh", sortie="https://github.com/o/r/pull/240")
    banc.jouer("lot.sh", DEPOT="o/r", LIGNE="lot 055 055-les-routes", ISSUE="12")
    assert banc.appel("git config user.email")[-1].endswith("users.noreply.github.com")


def test_une_demande_deja_traitee_ne_repart_pas(banc):
    """La branche existe : la fiche est déjà partie. Refaire le geste
    ouvrirait une seconde proposition pour le même lot."""
    _registre(banc)
    banc.poser("git", selon=[(["ls-remote"], "abc\trefs/heads/feuille/055-les-routes", 0)])
    banc.poser("gh")
    resultat = banc.jouer("lot.sh", DEPOT="o/r", LIGNE="lot 055 055-les-routes", ISSUE="12")

    assert resultat.returncode == 1
    assert "déjà" in resultat.stderr
    assert banc.appel("gh pr create") is None


def test_sans_demande_a_refermer_le_depot_se_fait_quand_meme(banc):
    """Le geste doit valoir aussi quand on l'appelle à la main."""
    _registre(banc)
    banc.poser("git", selon=[(["ls-remote"], "", 2)])
    banc.poser("gh", sortie="https://github.com/o/r/pull/240")
    resultat = banc.jouer("lot.sh", DEPOT="o/r", LIGNE="lot 055 055-les-routes", ISSUE="")

    assert resultat.returncode == 0
    assert banc.appel("gh pr create") is not None
    assert banc.appel("gh issue close") is None


def _evenement_lot(banc, association="NONE", action="opened"):
    import json
    from outils.tests.banc import RACINE
    evenement = banc.dossier / "evenement.json"
    evenement.write_text(json.dumps({
        "action": action, "sender": {"login": "demandeur"},
        "issue": {"number": 12, "state": "open", "user": {"login": "demandeur"},
                  "author_association": association, "labels": [{"name": "lot"}]},
    }))
    return {"EVENEMENT_LOT": evenement, "PYTHONPATH": str(RACINE)}


def test_232_une_issue_externe_ne_provoque_aucune_ecriture(banc):
    _registre(banc)
    banc.poser("git", selon=[(["ls-remote"], "", 2)])
    banc.poser("gh", sortie="https://github.com/o/r/pull/240")
    resultat = banc.jouer("lot.sh", DEPOT="o/r", ISSUE="12",
                          LIGNE="lot 055 055-les-routes", **_evenement_lot(banc))
    assert resultat.returncode == 0, resultat.stderr
    assert not banc.appels, banc.appels


def test_232_l_evenement_labeled_ne_refait_pas_le_depot(banc):
    _registre(banc)
    banc.poser("git", selon=[(["ls-remote"], "abc\trefs/heads/feuille/055-les-routes", 0)])
    banc.poser("gh")
    resultat = banc.jouer("lot.sh", DEPOT="o/r", ISSUE="12",
                          LIGNE="lot 055 055-les-routes",
                          **_evenement_lot(banc, "OWNER", "labeled"))
    assert resultat.returncode == 0, resultat.stderr
    assert not banc.appels, banc.appels


def _plan_du_lot(banc, plan):
    import sys
    import shlex
    # Le banc de gh/git utilise python3 dans son shebang : il garde le vrai
    # interpréteur. Seule la décision est injectée, les gestes restent réels.
    executable = banc.bin / "python3"
    executable.write_text('#!/bin/bash\nif [ "$1 $2 $3" = "-m outils demande" ]; then\n'
                          + '  echo ' + shlex.quote(plan) + '\nelse\n  exec '
                          + shlex.quote(sys.executable) + ' "$@"\nfi\n')
    executable.chmod(0o755)


def test_la_reprise_apres_push_ouvre_une_seule_pr_sans_repousser(banc):
    _registre(banc)
    _plan_du_lot(banc, "deposer 055 feuille/055-routes-demande-12 12 0 true false")
    banc.poser("git")
    banc.poser("gh", sortie="https://github.com/o/r/pull/240")
    result = banc.jouer("lot.sh", DEPOT="o/r", EVENEMENT_LOT="evenement.json")
    assert result.returncode == 0, result.stderr
    assert not banc.appel("git push")
    assert sum("gh pr create" in a for a in banc.appels) == 1
    assert sum("gh issue comment" in a for a in banc.appels) == 1


def test_la_reprise_apres_commentaire_ne_repete_aucune_ecriture_sauf_fermeture(banc):
    _registre(banc)
    _plan_du_lot(banc, "deposer 055 feuille/055-routes-demande-12 12 240 true true")
    banc.poser("git")
    banc.poser("gh")
    result = banc.jouer("lot.sh", DEPOT="o/r", EVENEMENT_LOT="evenement.json")
    assert result.returncode == 0, result.stderr
    assert len(banc.appels) == 1
    assert banc.appel("gh issue close 12")


def test_les_deux_workflows_partagent_le_verrou_sans_ecraser_la_file():
    from outils.tests.banc import RACINE
    lot = (RACINE / ".github/workflows/lot.yml").read_text()
    integration = (RACINE / ".github/workflows/integration.yml").read_text()
    assert "types: [opened]" in lot
    assert "needs.autoriser.outputs.autorise == 'true'" in lot
    for texte in (lot, integration):
        assert "group: registre" in texte
        assert "queue: max" in texte
        assert "cancel-in-progress: false" in texte
    assert 'outils palier --projet . --depot "$GITHUB_REPOSITORY" --ecrire' in integration
    assert 'ref: master' in integration


def test_pages_absent_conserve_le_succes_sans_annoncer_de_publication(banc):
    executable = banc.bin / "gh"
    executable.write_text('#!/bin/bash\necho "gh: Not Found (HTTP 404)" >&2\nexit 1\n')
    executable.chmod(0o755)
    sortie = banc.dossier / "sortie"
    resume = banc.dossier / "resume"
    result = banc.jouer("pages.sh", DEPOT="o/r", GITHUB_OUTPUT=sortie, GITHUB_STEP_SUMMARY=resume)
    assert result.returncode == 0, result.stderr
    assert sortie.read_text() == "publier=false\n"
    assert "aucune page publiée" in resume.read_text()
    assert "Settings → Pages → Source → GitHub Actions" in resume.read_text()


def test_pages_une_vraie_erreur_reste_rouge(banc):
    executable = banc.bin / "gh"
    executable.write_text('#!/bin/bash\necho "gh: Forbidden (HTTP 403)" >&2\nexit 1\n')
    executable.chmod(0o755)
    result = banc.jouer("pages.sh", DEPOT="o/r", GITHUB_OUTPUT=banc.dossier / "sortie",
                        GITHUB_STEP_SUMMARY=banc.dossier / "resume")
    assert result.returncode == 1
    assert "403" in result.stderr


def test_pages_actions_active_autorise_le_deploiement(banc):
    banc.poser("gh", sortie='{"build_type":"workflow"}')
    sortie = banc.dossier / "sortie"
    result = banc.jouer("pages.sh", DEPOT="o/r", GITHUB_OUTPUT=sortie,
                        GITHUB_STEP_SUMMARY=banc.dossier / "resume")
    assert result.returncode == 0, result.stderr
    assert sortie.read_text() == "publier=true\n"


def test_la_fusion_est_epinglee_sur_la_revision_jugee(banc):
    banc.poser("gh", sortie="brief/049-fabriquer")
    result = banc.jouer("integrer.sh", DEPOT="o/r", DECISION="fusionner 226",
                        REVISION_ATTENDUE=TETE, EXIGER_REVISION="true")
    assert result.returncode == 0, result.stderr
    assert banc.appel("gh pr merge", "--match-head-commit", TETE)


def test_actions_ne_fusionne_pas_sans_revision_jugee(banc):
    banc.poser("gh", sortie="brief/049-fabriquer")
    result = banc.jouer("integrer.sh", DEPOT="o/r", DECISION="fusionner 226",
                        REVISION_ATTENDUE="", EXIGER_REVISION="true")
    assert result.returncode == 1
    assert banc.appel("gh pr merge") is None


def test_le_tableau_absent_ne_declare_pas_un_deploiement_reussi():
    from outils.tests.banc import RACINE
    texte = (RACINE / ".github/workflows/tableau.yml").read_text()
    ecriture, publication = texte.split("\n  publier:\n")
    assert "upload-pages-artifact@" in ecriture
    assert "environment:" not in ecriture
    assert "if: needs.ecrire.outputs.publier == 'true'" in publication
    assert "name: github-pages" in publication
    assert "actions/deploy-pages@" in publication


# ----------------------------------------------------------------------
# Les actions du tableau de pilotage. Chacune a trois cas, et ce sont
# toujours les mêmes trois : le geste nominal, le « déjà fait » qui ne
# refait rien, et l'échec qui rougit. Le deuxième est celui qui compte :
# une action déclenchée deux fois ne fait pas deux fois le geste, et un
# tableau de bord se re-clique.
# ----------------------------------------------------------------------


def _travaux(banc) -> list[str]:
    """Les travaux que ce tour a redemandés, dans l'ordre."""
    return [appel for appel in banc.appels if "gh workflow run" in appel]


# ------------------------------------------- redemander les contrôles


def test_controles_redemande_les_trois_travaux_sur_la_bonne_reference(banc):
    banc.poser("python3", "redemander 226 brief/049-fabriquer " + TETE)
    banc.poser("gh")
    resultat = banc.jouer("controles.sh", DEPOT="o/r", PR="226", BASE="master")

    assert resultat.returncode == 0, resultat.stderr
    assert len(_travaux(banc)) == 3
    # `tests` et `security` se jouent sur la branche de la proposition ;
    # `relecture` depuis la base, parce qu'il ne doit pas tourner sur le
    # code qu'il juge.
    assert banc.appel("gh workflow run tests.yml", "--ref", "brief/049-fabriquer")
    assert banc.appel("gh workflow run security.yml", "--ref", "brief/049-fabriquer")
    assert banc.appel("gh workflow run relecture.yml", "--ref", "master", "pr=226")


def test_controles_deja_poses_ne_relance_rien(banc):
    """Le « déjà fait ». Deux clics ne lancent pas deux fois les mêmes
    contrôles sur la même révision."""
    banc.poser("python3", "RIEN")
    banc.poser("gh")
    resultat = banc.jouer("controles.sh", DEPOT="o/r", PR="226")

    assert resultat.returncode == 0, resultat.stderr
    assert _travaux(banc) == []
    assert "rien à redemander" in resultat.stdout


def test_controles_une_decision_impossible_rougit_sans_rien_lancer(banc):
    banc.poser("python3", "", code=1)
    banc.poser("gh")
    resultat = banc.jouer("controles.sh", DEPOT="o/r", PR="226")

    assert resultat.returncode == 1
    assert _travaux(banc) == []
    assert "rien n'est redemandé" in resultat.stderr


def test_controles_une_ligne_illisible_rougit_au_lieu_de_deviner(banc):
    """Une décision qu'on ne comprend pas traitée comme « rien » serait
    une file qui s'arrête sans le dire."""
    banc.poser("python3", "peut-être bien que oui")
    banc.poser("gh")
    resultat = banc.jouer("controles.sh", DEPOT="o/r", PR="226")

    assert resultat.returncode == 1
    assert _travaux(banc) == []
    assert "illisible" in resultat.stderr


# ------------------------------------------------- sortir du brouillon


def test_brouillon_sort_la_proposition_et_lui_rend_ses_controles(banc):
    """Sortir du brouillon ne déclenche rien côté GitHub : sans ces trois
    appels, la proposition passerait de « brouillon » à « contrôle
    absent »."""
    banc.poser("python3", "sortir 231 cursor/couverture-eb5f")
    banc.poser("gh")
    resultat = banc.jouer("brouillon.sh", DEPOT="o/r", PR="231", BASE="master")

    assert resultat.returncode == 0, resultat.stderr
    assert banc.appel("gh pr ready 231")
    assert len(_travaux(banc)) == 3


def test_brouillon_deja_sortie_ne_refait_rien(banc):
    banc.poser("python3", "RIEN")
    banc.poser("gh")
    resultat = banc.jouer("brouillon.sh", DEPOT="o/r", PR="231")

    assert resultat.returncode == 0, resultat.stderr
    assert banc.appel("gh pr ready") is None
    assert _travaux(banc) == []


def test_brouillon_une_decision_impossible_rougit_sans_toucher_la_proposition(banc):
    banc.poser("python3", "", code=1)
    banc.poser("gh")
    resultat = banc.jouer("brouillon.sh", DEPOT="o/r", PR="231")

    assert resultat.returncode == 1
    assert banc.appel("gh pr ready") is None
    assert "rien n'est touché" in resultat.stderr


# --------------------------------------------- changer l'état d'un lot


def _etat_pose(banc, ligne="etat 049 abandonne etat-049-abandonne", code=0):
    banc.poser("python3", ligne, code=code)


def test_etat_ouvre_une_proposition_et_n_ecrit_jamais_dans_la_base(banc):
    _etat_pose(banc)
    banc.poser("git", selon=[(["ls-remote"], "", 1)])
    banc.poser("gh", selon=[(["pr list"], ""), (["pr create"], "https://x/pull/240")])
    resultat = banc.jouer("etat-lot.sh", DEPOT="o/r", LOT="049", ETAT="abandonne",
                          BASE="master")

    assert resultat.returncode == 0, resultat.stderr
    assert banc.appel("git checkout -b feuille/etat-049-abandonne")
    assert banc.appel("git add ROADMAP.md")
    assert banc.appel("git push -u origin feuille/etat-049-abandonne")
    assert banc.appel("gh pr create", "--base", "master")
    # La proposition ouverte par le jeton d'Actions ne déclenche rien :
    # ses contrôles se demandent nommément.
    assert len(_travaux(banc)) == 3


def test_etat_le_commit_porte_une_connexion_que_github_sait_relier(banc):
    """Une adresse que GitHub ne relie à personne rend `auteurs_du_code`
    vide, et la relecture refuse avant de regarder les approbations."""
    _etat_pose(banc)
    banc.poser("git", selon=[(["ls-remote"], "", 1)])
    banc.poser("gh", selon=[(["pr list"], ""), (["pr create"], "https://x/pull/240")])
    banc.jouer("etat-lot.sh", DEPOT="o/r", LOT="049", ETAT="abandonne")

    assert banc.appel("git config user.email",
                      "41898282+github-actions[bot]@users.noreply.github.com")


def test_etat_une_proposition_deja_ouverte_ne_se_redouble_pas(banc):
    """Le « déjà fait » de cette action-là. Tant que la proposition n'est
    pas fusionnée, la fiche n'a pas bougé dans la base et chaque réveil
    la reproposerait."""
    _etat_pose(banc)
    banc.poser("git")
    banc.poser("gh", selon=[(["pr list"], "241")])
    resultat = banc.jouer("etat-lot.sh", DEPOT="o/r", LOT="049", ETAT="abandonne")

    assert resultat.returncode == 0, resultat.stderr
    assert "241" in resultat.stdout
    assert banc.appel("git checkout") is None
    assert banc.appel("gh pr create") is None


def test_etat_un_lot_deja_dans_l_etat_demande_ne_touche_a_rien(banc):
    _etat_pose(banc, ligne="RIEN")
    banc.poser("git")
    banc.poser("gh")
    resultat = banc.jouer("etat-lot.sh", DEPOT="o/r", LOT="049", ETAT="abandonne")

    assert resultat.returncode == 0, resultat.stderr
    assert banc.appel("gh pr list") is None
    assert banc.appel("git checkout") is None


def test_etat_une_transition_interdite_rougit_sans_rien_ecrire(banc):
    """Le refus vient du juge de l'atelier ; ce script ne fait que le
    porter — et surtout, il ne passe pas outre."""
    _etat_pose(banc, ligne="", code=1)
    banc.poser("git")
    banc.poser("gh")
    resultat = banc.jouer("etat-lot.sh", DEPOT="o/r", LOT="046", ETAT="abandonne")

    assert resultat.returncode == 1
    assert "ne passe pas à" in resultat.stderr
    assert banc.appel("git checkout") is None
    assert banc.appel("gh pr create") is None


def test_etat_une_branche_orpheline_se_retire_avant_la_poussee(banc):
    """Une branche restée d'une proposition fermée porte une fiche qui
    n'a jamais atterri : elle empêcherait la poussée d'aboutir."""
    _etat_pose(banc)
    banc.poser("git", selon=[(["ls-remote"], "abc\trefs/heads/feuille/etat-049-abandonne", 0)])
    banc.poser("gh", selon=[(["pr list"], ""), (["pr create"], "https://x/pull/240")])
    resultat = banc.jouer("etat-lot.sh", DEPOT="o/r", LOT="049", ETAT="abandonne")

    assert resultat.returncode == 0, resultat.stderr
    assert banc.appel("git push origin --delete feuille/etat-049-abandonne")


# ------------------------------------------- les travaux et leurs gestes


def test_chaque_travail_appelle_un_geste_qui_vit_dans_un_fichier():
    """Règle 13 : un bloc de shell écrit dans un YAML ne se joue nulle
    part. La référence est dérivée du dossier, pas recopiée ici."""
    from outils.tests.banc import RACINE, SCRIPTS

    travaux = sorted((RACINE / ".github" / "workflows").glob("*.yml"))
    assert travaux, "aucun travail à contrôler"
    for travail in travaux:
        texte = travail.read_text(encoding="utf-8")
        for appel in re.findall(r"bash (\.github/scripts/[\w.-]+)", texte):
            assert (RACINE / appel).is_file(), f"{travail.name} appelle {appel}, absent"
    poses = {chemin.name for chemin in SCRIPTS.glob("*.sh")}
    appeles = {
        appel.rsplit("/", 1)[-1]
        for travail in travaux
        for appel in re.findall(r"bash (\.github/scripts/[\w.-]+)", travail.read_text(encoding="utf-8"))
    }
    assert poses - appeles == set(), f"scripts que personne n'appelle : {poses - appeles}"


def test_les_trois_actions_nouvelles_ont_leur_travail_et_leur_entree():
    from outils.tests.banc import RACINE

    attendus = {
        "controles.yml": "le numéro de la proposition",
        "brouillon.yml": "le numéro de la proposition",
        "etat-lot.yml": "le numéro du lot",
    }
    for fichier, entree in attendus.items():
        texte = (RACINE / ".github" / "workflows" / fichier).read_text(encoding="utf-8")
        assert "workflow_dispatch:" in texte, fichier
        assert entree in texte, fichier


def test_le_palier_peut_se_forcer_sans_attendre_une_fusion():
    """Si le tour qui devait le déposer est mort en route, la couche
    reste finie et son palier n'arrive jamais."""
    from outils.tests.banc import RACINE

    texte = (RACINE / ".github" / "workflows" / "integration.yml").read_text(encoding="utf-8")
    assert "if: needs.integrer.outputs.fusionnee != '' || inputs.palier == 'oui'" in texte


def test_le_travail_d_etat_partage_le_verrou_du_registre():
    """Trois travaux écrivent le registre ; deux numéros attribués en même
    temps sont deux fiches qui se marchent dessus."""
    from outils.tests.banc import RACINE

    texte = (RACINE / ".github" / "workflows" / "etat-lot.yml").read_text(encoding="utf-8")
    assert "group: registre" in texte
    assert "queue: max" in texte
    assert "cancel-in-progress: false" in texte


def test_le_tableau_a_le_droit_de_lire_l_historique_des_executions():
    """Sans `actions: read`, l'API répond 403 et le bloc de santé se rend
    « non lu » — honnête, mais inutile : c'est ce bloc-là qui aurait
    montré la panne du 7 septembre 2026."""
    from outils.tests.banc import RACINE

    texte = (RACINE / ".github" / "workflows" / "tableau.yml").read_text(encoding="utf-8")
    permissions = texte.split("permissions:", 1)[1].split("\njobs:", 1)[0]
    for droit in ("actions: read", "pull-requests: read", "pages: read"):
        assert droit in permissions, droit
    assert "write" not in permissions, "la page ne fait qu'écrire un fichier : elle ne pousse rien"
