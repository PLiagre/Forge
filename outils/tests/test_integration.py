"""L'intégration lit des contrôles, jamais un avis — et un inconnu retient."""


import pytest

from outils import integration
from outils.integration import Controle, PR

REQUIS = ("sim", "vues", "feuille", "gitleaks")
PREFIXES = ("agent/", "brief/", "feuille/")



def _atelier_integration(dossier, controles, branches):
    """Un branchement de banc : les listes sont celles du test, pas du dépôt."""
    lignes = [
        "[projet]",
        'nom = "Essai"',
        'feuille = "ROADMAP.md"',
        'branche_base = "master"',
        "",
        "[integration]",
        "controles = [" + ", ".join(f'"{c}"' for c in controles) + "]",
        "branches = [" + ", ".join(f'"{b}"' for b in branches) + "]",
    ]
    (dossier / "atelier.toml").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    return dossier


def test_une_liste_de_branches_vide_est_un_branchement_incomplet(tmp_path):
    """Sans préfixe, toute PR serait « hors préfixe » : on refuse à la lecture."""
    from outils import registre

    _atelier_integration(tmp_path, controles=("sim",), branches=())
    with pytest.raises(registre.BranchementIncomplet) as refus:
        registre.integration(tmp_path)
    assert "branches" in str(refus.value)


def test_un_statut_github_en_echec_n_est_pas_un_succes():
    """`state: failure` d'un status externe se lit comme un contrôle rouge,
    pas comme un succès déguisé. La clé `check_runs` absente n'invente rien."""
    from outils import github

    class Faux:
        def get(self, chemin, **_):
            if "check-runs" in chemin:
                return {}
            return {"statuses": [{"context": "sim", "state": "failure"}]}

    trouves = github.controles(Faux(), "a" * 40)
    assert trouves == [("sim", "completed", "failure")]
    assert integration.etat_du_controle(*trouves[0][1:]) == integration.ROUGE


def test_github_injoignable_se_nomme():
    """Un réseau mort n'est pas une liste vide : la boucle doit s'arrêter à voix haute."""
    from outils import github

    gh = github.Github("O/R", jeton="x", api="http://127.0.0.1:1")
    with pytest.raises(github.GithubErreur) as refus:
        gh.get("pulls/1")
    assert "injoignable" in str(refus.value)


def test_une_pr_integrable_demande_le_detail():
    """Le complément du brouillon : une PR dans le préfixe appelle le détail,
    sinon la fusionnabilité reste inconnue et rien n'entre — pour toujours."""
    from outils.__main__ import _pr_integrable

    class Faux:
        def __init__(self):
            self.appels = []

        def get(self, chemin, **_):
            self.appels.append(chemin)
            if chemin.startswith("pulls/"):
                return {
                    "head": {"sha": "a" * 40, "ref": "agent/049-x"},
                    "mergeable": True,
                }
            if "check-runs" in chemin:
                return {"check_runs": []}
            if "status" in chemin:
                return {"statuses": []}
            if chemin.startswith("compare/"):
                return {"behind_by": 0}
            raise AssertionError(chemin)

        def liste(self, chemin, **_):
            self.appels.append(chemin)
            if chemin.endswith("/commits"):
                return [{"author": {"login": "auteur"}, "committer": None}]
            if chemin.endswith("/reviews"):
                return []
            raise AssertionError(chemin)

    faux = Faux()
    obtenu = _pr_integrable(
        faux,
        {"number": 200, "head": {"ref": "agent/049-x"}, "draft": False},
        "master",
        ("agent/",),
    )
    assert obtenu.fusionnable is True
    assert obtenu.retard == 0
    assert any(appel.startswith("pulls/") for appel in faux.appels)
    assert any("check-runs" in appel for appel in faux.appels)
    assert any("compare/" in appel for appel in faux.appels)


class _GithubDecision:
    """GitHub de banc pour la ligne que le workflow découpe."""

    def __init__(self, bruts, detail, behind_by, check_runs):
        self.bruts = bruts
        self.detail = detail
        self.behind_by = behind_by
        self.check_runs = check_runs

    def liste(self, chemin, **_k):
        if chemin == "pulls":
            return self.bruts
        if chemin.endswith("/commits"):
            return [{"author": {"login": "auteur"}, "committer": None}]
        if chemin.endswith("/reviews"):
            return [{"user": {"login": "tiers"}, "state": "APPROVED",
                     "commit_id": self.detail["head"]["sha"]}]
        raise AssertionError(chemin)

    def get(self, chemin, **_k):
        if chemin.startswith("pulls/"):
            return self.detail
        if "check-runs" in chemin:
            return {"check_runs": self.check_runs}
        if "status" in chemin:
            return {"statuses": []}
        if chemin.startswith("compare/"):
            return {"behind_by": self.behind_by}
        raise AssertionError(chemin)


def _cli_integration(tmp_path, monkeypatch, capsys, faux):
    from outils import github
    from outils.__main__ import main

    monkeypatch.setattr(github, "Github", lambda *a, **k: faux)
    code = main(
        ["integration", "--depot", "O/R", "--projet", str(tmp_path), "--jeton", "x"]
    )
    return code, capsys.readouterr()


def test_cli_integration_imprime_rien_quand_aucune_pr(tmp_path, monkeypatch, capsys):
    """Le workflow lit stdout : `RIEN` tout seul, rien d'autre."""
    _atelier_integration(tmp_path, controles=REQUIS, branches=PREFIXES)
    code, io = _cli_integration(
        tmp_path, monkeypatch, capsys,
        _GithubDecision([], {}, 0, []),
    )
    assert code == 0
    assert io.out == "RIEN\n"


def test_cli_integration_imprime_fusionner_puis_le_numero(tmp_path, monkeypatch, capsys):
    """`cut -d' ' -f1/f2` du workflow : `fusionner 200`, pas un autre format."""
    _atelier_integration(tmp_path, controles=REQUIS, branches=PREFIXES)
    verts = [
        {"name": nom, "status": "completed", "conclusion": "success"} for nom in REQUIS
    ]
    code, io = _cli_integration(
        tmp_path, monkeypatch, capsys,
        _GithubDecision(
            [{"number": 200, "head": {"ref": "agent/049-x"}, "draft": False}],
            {"head": {"sha": "a" * 40, "ref": "agent/049-x"}, "mergeable": True},
            0,
            verts,
        ),
    )
    assert code == 0
    assert io.out == "fusionner 200\n"


def test_cli_integration_imprime_rebaser_avant_la_relecture(tmp_path, monkeypatch, capsys):
    """En retard, la ligne est `rebaser N` : le workflow rejoue, il ne fusionne pas."""
    _atelier_integration(
        tmp_path, controles=REQUIS, branches=PREFIXES
    )
    sans_relecture = [
        {"name": nom, "status": "completed", "conclusion": "success"}
        for nom in REQUIS
        if nom != "relecture"
    ]
    code, io = _cli_integration(
        tmp_path, monkeypatch, capsys,
        _GithubDecision(
            [{"number": 200, "head": {"ref": "agent/049-x"}, "draft": False}],
            {"head": {"sha": "a" * 40, "ref": "agent/049-x"}, "mergeable": True},
            3,
            sans_relecture,
        ),
    )
    assert code == 0
    assert io.out == "rebaser 200\n"


def test_la_plus_ancienne_en_retard_passe_avant_une_verte_a_jour():
    """L'intégration est séquentielle : la plus ancienne d'abord, même si une
    plus récente est déjà prête à entrer. Sauter le rejeu, c'est fusionner
    deux PR qui n'ont jamais été testées l'une sur l'autre."""
    rapport = integration.decider(
        [pr(numero=210), pr(numero=205, retard=2)], REQUIS, PREFIXES
    )
    assert rapport.decision.action == integration.REBASER
    assert rapport.decision.pr == 205


def verts(*noms):
    return tuple(Controle(nom, integration.VERT) for nom in noms)


def pr(**kw):
    defaut = dict(
        numero=200,
        branche="agent/049-fabriquer",
        brouillon=False,
        fusionnable=True,
        retard=0,
        controles=verts(*REQUIS),
        relue=True,
        motif_relecture="approuvée sur aaaaaaa par pliagre",
    )
    defaut.update(kw)
    return PR(**defaut)


def test_une_pr_verte_a_jour_et_relue_entre():
    decision = integration.examiner(pr(), REQUIS, PREFIXES)
    assert decision.action == integration.FUSIONNER


def test_un_controle_requis_absent_n_est_pas_un_controle_vert():
    incomplet = verts(*[n for n in REQUIS if n != "gitleaks"])
    decision = integration.examiner(pr(controles=incomplet), REQUIS, PREFIXES)
    assert decision.action == integration.RIEN
    assert "gitleaks" in decision.raison


def test_un_controle_rouge_retient():
    controles = verts(*REQUIS[:-1]) + (Controle("gitleaks", integration.ROUGE),)
    decision = integration.examiner(pr(controles=controles), REQUIS, PREFIXES)
    assert decision.action == integration.RIEN
    assert "rouge" in decision.raison


def test_un_controle_en_cours_retient():
    controles = verts(*REQUIS[:-1]) + (Controle("gitleaks", integration.EN_COURS),)
    decision = integration.examiner(pr(controles=controles), REQUIS, PREFIXES)
    assert decision.action == integration.RIEN
    assert "en cours" in decision.raison


def test_un_controle_hors_de_la_liste_ne_change_rien():
    """La liste requise gouverne seule ; un contrôle facultatif rouge
    ne bloque pas, sinon la liste ne voudrait plus rien dire."""
    controles = verts(*REQUIS) + (Controle("un-essai", integration.ROUGE),)
    assert integration.examiner(pr(controles=controles), REQUIS, PREFIXES).action == integration.FUSIONNER


def test_une_fusionnabilite_inconnue_retient():
    decision = integration.examiner(pr(fusionnable=None), REQUIS, PREFIXES)
    assert decision.action == integration.RIEN
    assert "inconnue" in decision.raison


def test_un_conflit_retient():
    assert integration.examiner(pr(fusionnable=False), REQUIS, PREFIXES).action == integration.RIEN


def test_un_brouillon_n_entre_pas():
    assert integration.examiner(pr(brouillon=True), REQUIS, PREFIXES).action == integration.RIEN


def test_une_branche_hors_prefixe_reste_au_proprietaire():
    decision = integration.examiner(pr(branche="cursor/un-essai"), REQUIS, PREFIXES)
    assert decision.action == integration.RIEN
    assert "propriétaire" in decision.raison


def test_une_pr_en_retard_est_rejouee_avant_d_entrer():
    decision = integration.examiner(pr(retard=3), REQUIS, PREFIXES)
    assert decision.action == integration.REBASER


def test_une_pr_en_retard_et_rouge_n_est_pas_rejouee_pour_rien():
    controles = verts(*REQUIS[:-1]) + (Controle("gitleaks", integration.ROUGE),)
    decision = integration.examiner(pr(retard=3, controles=controles), REQUIS, PREFIXES)
    assert decision.action == integration.RIEN


def test_une_seule_pr_avance_par_tour():
    rapport = integration.decider(
        [pr(numero=210), pr(numero=205)], REQUIS, PREFIXES
    )
    assert rapport.decision.action == integration.FUSIONNER
    assert rapport.decision.pr == 205  # la plus ancienne d'abord
    assert len(rapport.lignes) == 2  # les deux sont dites, une seule avance


def test_une_pr_qui_attend_ne_bloque_pas_la_suivante():
    rapport = integration.decider(
        [pr(numero=205, fusionnable=False), pr(numero=210)], REQUIS, PREFIXES
    )
    assert rapport.decision.pr == 210


def test_sans_controle_requis_declare_rien_n_entre():
    rapport = integration.decider([pr()], (), PREFIXES)
    assert rapport.decision.action == integration.RIEN
    assert "aucun contrôle requis" in rapport.decision.raison


def test_aucune_pr_ouverte_n_est_pas_une_erreur():
    rapport = integration.decider([], REQUIS, PREFIXES)
    assert rapport.decision.action == integration.RIEN
    assert rapport.decision.pr is None


def test_un_controle_qui_n_a_pas_fini_n_est_ni_vert_ni_rouge():
    assert integration.etat_du_controle("in_progress", None) == integration.EN_COURS
    assert integration.etat_du_controle("queued", None) == integration.EN_COURS


def test_un_controle_ignore_n_a_rien_prouve():
    assert integration.etat_du_controle("completed", "skipped") == integration.ROUGE
    assert integration.etat_du_controle("completed", "cancelled") == integration.ROUGE
    assert integration.etat_du_controle("completed", "failure") == integration.ROUGE
    assert integration.etat_du_controle("completed", "success") == integration.VERT


def test_une_pr_sans_relecture_n_entre_pas():
    decision = integration.examiner(
        pr(relue=False, motif_relecture="aucune approbation : relecture absente"),
        REQUIS, PREFIXES,
    )
    assert decision.action == integration.RIEN
    assert "relecture absente" in decision.raison


def test_une_relecture_inconnue_retient():
    """La PR n'a pas été interrogée : un blanc n'est pas une approbation."""
    decision = integration.examiner(pr(relue=None), REQUIS, PREFIXES)
    assert decision.action == integration.RIEN
    assert "inconnue" in decision.raison


def test_une_pr_en_retard_se_rejoue_avant_qu_on_demande_la_relecture():
    """Le rejeu périme la relecture : la demander avant, c'est la payer
    deux fois, et la deuxième pour rien."""
    decision = integration.examiner(pr(retard=1, relue=False), REQUIS, PREFIXES)
    assert decision.action == integration.REBASER
    assert "relecture" in decision.raison


def test_un_controle_de_ci_rouge_ne_se_rejoue_pas_pour_autant():
    """Un rejeu ne répare pas un test rouge : il coûte un tour de CI pour
    rougir au même endroit."""
    controles = (Controle("sim", integration.ROUGE),) + verts(
        *[n for n in REQUIS if n != "sim"]
    )
    decision = integration.examiner(pr(retard=1, controles=controles), REQUIS, PREFIXES)
    assert decision.action == integration.RIEN
    assert "sim" in decision.raison


def test_la_raison_de_la_fusion_dit_qui_a_relu():
    decision = integration.examiner(pr(), REQUIS, PREFIXES)
    assert decision.action == integration.FUSIONNER
    assert "pliagre" in decision.raison


def test_232_un_nouveau_controle_absent_ne_bloque_pas_le_rejeu():
    nouveaux = (*REQUIS, "forge", "outils")
    decision = integration.examiner(pr(numero=226, retard=2, relue=False), nouveaux, PREFIXES)
    assert decision.action == integration.REBASER
    # Après le rejeu, les mêmes contrôles absents interdisent la fusion.
    assert integration.examiner(pr(retard=0), nouveaux, PREFIXES).action == integration.RIEN


def test_chacun_des_six_controles_reste_obligatoire_apres_le_rejeu():
    from pathlib import Path
    from outils import registre
    requis = registre.integration(Path(__file__).resolve().parents[2])["controles"]
    assert set(requis) == {"sim", "vues", "forge", "outils", "feuille", "gitleaks"}
    for nom in requis:
        autres = verts(*[n for n in requis if n != nom])
        for controles in (autres, autres + (Controle(nom, integration.ROUGE),),
                          autres + (Controle(nom, integration.EN_COURS),)):
            decision = integration.examiner(pr(controles=controles), requis, PREFIXES)
            assert decision.action == integration.RIEN, nom
    assert integration.examiner(pr(controles=verts(*requis)), requis, PREFIXES).action == integration.FUSIONNER
