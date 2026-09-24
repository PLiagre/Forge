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
        'zone = ["AGENTS.md"]',
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
        depot = "O/R"

        def __init__(self):
            self.appels = []

        def get(self, chemin, **_):
            self.appels.append(chemin)
            if chemin.startswith("pulls/"):
                return {
                    "head": {"sha": "a" * 40, "ref": "agent/049-x"},
                    "mergeable": True,
                    "changed_files": 1,
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
            if chemin.endswith("/files"):
                return [{"filename": "ordinaire.txt", "status": "modified"}]
            if chemin.endswith("/commits"):
                return [{"author": {"login": "auteur"}, "committer": None}]
            if chemin.endswith("/reviews"):
                return []
            raise AssertionError(chemin)

    faux = Faux()
    obtenu = _pr_integrable(
        faux,
        {"number": 200, "head": {"ref": "agent/049-x", "repo": {"full_name": "O/R"}},
         "draft": False},
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

    depot = "O/R"

    def __init__(self, bruts, detail, behind_by, check_runs):
        self.bruts = bruts
        self.detail = detail
        self.detail.setdefault("changed_files", 1)
        self.detail.setdefault("base", {"sha": "f" * 40, "ref": "master"})
        self.behind_by = behind_by
        self.check_runs = check_runs

    def liste(self, chemin, **_k):
        if chemin.endswith("/files"):
            return [{"filename": "ordinaire.txt", "status": "modified"}]
        if chemin == "pulls":
            return self.bruts
        if chemin.endswith("/commits"):
            return [{"author": {"login": "auteur"}, "committer": None}]
        if chemin.endswith("/reviews"):
            return [{"user": {"login": "tiers"}, "state": "APPROVED",
                     "commit_id": self.detail["head"]["sha"],
                     "author_association": "COLLABORATOR"}]
        raise AssertionError(chemin)

    def get(self, chemin, **_k):
        if chemin.startswith("git/commits/"):
            return {"sha": chemin.rsplit("/", 1)[1], "tree": {"sha": "c" * 40}}
        if chemin.startswith("git/trees/"):
            return {"sha": "c" * 40, "truncated": False, "tree": []}
        if chemin.startswith("pulls/"):
            return self.detail
        if "check-runs" in chemin:
            return {"check_runs": self.check_runs}
        if "status" in chemin:
            return {"statuses": []}
        if chemin.startswith("compare/"):
            return {"behind_by": self.behind_by, "merge_base_commit": {"sha": "f" * 40}}
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
            [{"number": 200, "head": {"ref": "agent/049-x", "repo": {"full_name": "O/R"}},
              "draft": False}],
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
            [{"number": 200, "head": {"ref": "agent/049-x", "repo": {"full_name": "O/R"}},
              "draft": False}],
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


def _travaux_de_la_ci(racine) -> set[str]:
    """Les noms de travaux que les workflows de contrôle posent réellement."""
    import re
    noms: set[str] = set()
    for fichier in ("tests.yml", "security.yml"):
        texte = (racine / ".github" / "workflows" / fichier).read_text(encoding="utf-8")
        bloc = texte.split("\njobs:\n", 1)[1]
        noms.update(re.findall(r"^  ([a-z][a-z0-9_-]*):\s*$", bloc, re.MULTILINE))
    return noms


def test_chacun_des_controles_declares_reste_obligatoire_apres_le_rejeu():
    """La liste vient du branchement, jamais d'ici : le 14 septembre 2026,
    `atelier` est entré dans `atelier.toml` et ce contrôle — qui nommait
    six contrôles en dur — a rougi sur `master`, fermant la porte à toute
    PR. Un contrôle déclaré doit avoir un travail qui le pose, sinon il
    est absent, donc bloquant, pour toujours."""
    from pathlib import Path
    from outils import registre
    racine = Path(__file__).resolve().parents[2]
    requis = registre.integration(racine)["controles"]
    assert requis, "aucun contrôle déclaré : rien n'entrerait"
    assert set(requis) <= _travaux_de_la_ci(racine), set(requis) - _travaux_de_la_ci(racine)
    for nom in requis:
        autres = verts(*[n for n in requis if n != nom])
        for controles in (autres, autres + (Controle(nom, integration.ROUGE),),
                          autres + (Controle(nom, integration.EN_COURS),)):
            decision = integration.examiner(pr(controles=controles), requis, PREFIXES)
            assert decision.action == integration.RIEN, nom
    assert integration.examiner(pr(controles=verts(*requis)), requis, PREFIXES).action == integration.FUSIONNER


def test_un_travail_qui_lit_les_controles_a_le_droit_de_les_lire():
    """Le 15 septembre 2026, `integration.yml` ne déclarait ni `checks: read`
    ni `statuses: read`. Le premier lot arrivé à la porte a fait lire ses
    contrôles : 403, `outils integration` est mort, et plus rien ne pouvait
    entrer dans master. Tant qu'aucun lot n'y arrivait, chaque tour
    répondait RIEN avant d'avoir à lire : la panne existait sans se voir.

    La référence se dérive des travaux eux-mêmes : tout travail qui appelle,
    directement ou par un script, une commande d'`outils` qui lit les
    contrôles d'une révision déclare les deux droits.
    """
    import re
    from pathlib import Path

    racine = Path(__file__).resolve().parents[2]
    lecteurs = ("outils integration", "outils controles", "outils tableau")
    examines = []
    for fichier in sorted((racine / ".github" / "workflows").glob("*.yml")):
        texte = fichier.read_text(encoding="utf-8")
        joue = texte + "".join(
            (racine / ".github" / "scripts" / script).read_text(encoding="utf-8")
            for script in re.findall(r"\.github/scripts/([\w-]+\.sh)", texte)
        )
        if not any(lecteur in joue for lecteur in lecteurs):
            continue
        examines.append(fichier.name)
        for droit in ("checks: read", "statuses: read"):
            assert droit in texte, f"{fichier.name} lit les contrôles sans « {droit} »"
    # Un échantillon vide ne prouve rien : si plus aucun travail ne lit les
    # contrôles, c'est la liste des lecteurs qu'il faut regarder.
    assert {"integration.yml", "controles.yml"} <= set(examines), examines


# ------------------------------------------------ une fourche n'entre pas


def test_une_pr_venue_d_une_fourche_ne_se_fusionne_pas():
    """Sur un dépôt public, n'importe qui ouvre une PR depuis sa copie, et
    choisit le nom de sa branche. Un préfixe `agent/` ne dit rien de l'origine :
    tout vert et approuvée, une fourche attend quand même le propriétaire."""
    decision = integration.examiner(pr(interne=False), REQUIS, PREFIXES)
    assert decision.action == integration.RIEN
    assert "fourche" in decision.raison
    assert integration.examiner(pr(interne=True), REQUIS, PREFIXES).action == integration.FUSIONNER


class _GithubOrigine:
    """Un GitHub de banc qui compte ses appels : une fourche ne coûte rien."""

    depot = "O/R"

    def __init__(self):
        self.appels = []

    def get(self, chemin, **_):
        self.appels.append(chemin)
        if chemin.startswith("pulls/"):
            return {"head": {"sha": "a" * 40, "ref": "agent/049-x"}, "mergeable": True, "changed_files": 1}
        if "check-runs" in chemin:
            return {"check_runs": []}
        if "status" in chemin:
            return {"statuses": []}
        if chemin.startswith("compare/"):
            return {"behind_by": 0}
        raise AssertionError(chemin)

    def liste(self, chemin, **_):
        self.appels.append(chemin)
        if chemin.endswith("/files"):
            return [{"filename": "ordinaire.txt", "status": "modified"}]
        if chemin.endswith("/commits"):
            return [{"author": {"login": "auteur"}, "committer": None}]
        if chemin.endswith("/reviews"):
            return []
        raise AssertionError(chemin)


@pytest.mark.parametrize("repo, attendu", [
    ({"full_name": "O/R"}, True),
    ({"full_name": "o/r"}, True),
    ({"full_name": "intrus/R"}, False),
    (None, False),
    ("absent", False),
])
def test_la_couture_github_pose_toujours_l_origine(repo, attendu):
    """`repo: null` est une fourche supprimée ; une clé absente ne se devine
    pas. Dans les deux cas, l'origine vaut une fourche, et rien n'est lu."""
    from outils.__main__ import _pr_integrable

    tete = {"ref": "agent/049-x"}
    if repo != "absent":
        tete["repo"] = repo
    faux = _GithubOrigine()
    obtenu = _pr_integrable(faux, {"number": 200, "head": tete, "draft": False},
                            "master", ("agent/",))
    assert obtenu.interne is attendu
    if not attendu:
        assert faux.appels == [], "une fourche a coûté des appels"


# ------------------------------------------------ la zone du propriétaire


def _zone_du_depot():
    from pathlib import Path
    import tomllib

    chemin = Path(__file__).resolve().parents[2] / "atelier.toml"
    zone = tuple(tomllib.loads(chemin.read_text(encoding="utf-8"))["integration"]["zone"])
    assert zone, "une zone sans cas ne prouve rien"
    return zone


def test_zone_les_modules_des_outils_ne_peuvent_pas_neutraliser_la_garde():
    from pathlib import Path
    racine = Path(__file__).resolve().parents[2]
    chemins = sorted(p.relative_to(racine).as_posix() for p in (racine / "outils").rglob("*.py"))
    assert chemins, "une zone sans module ne prouve rien"
    for chemin in chemins:
        decision = integration.examiner(pr(fichiers=(chemin,)), REQUIS, PREFIXES, _zone_du_depot())
        assert decision.action == integration.RIEN, chemin
        assert "zone protégée" in decision.raison, chemin


@pytest.mark.parametrize("retard", [0, 3])
def test_zone_chaque_entree_retient_avant_fusion_et_rejeu(retard):
    zone = _zone_du_depot()
    for entree in zone:
        chemin = entree + "workflows/essai.yml" if entree.endswith("/") else entree
        decision = integration.examiner(pr(retard=retard, fichiers=(chemin,)), REQUIS, PREFIXES, zone)
        assert decision.action == integration.RIEN, entree
        assert decision.raison.startswith("zone protégée : le propriétaire fusionne"), entree
        assert chemin in decision.raison
    temoin = integration.examiner(pr(retard=retard, fichiers=("ordinaire.txt",)), REQUIS, PREFIXES, zone)
    assert temoin.action == (integration.REBASER if retard else integration.FUSIONNER)


def test_zone_un_fichier_exact_ne_protege_pas_un_suffixe():
    zone = _zone_du_depot()
    fichiers = tuple(entree + ".autre" for entree in zone if not entree.endswith("/"))
    assert fichiers
    assert integration.examiner(pr(fichiers=fichiers), REQUIS, PREFIXES, zone).action == integration.FUSIONNER


def test_zone_remplacer_un_dossier_protege_par_un_fichier_ne_libere_pas():
    zone = _zone_du_depot()
    dossiers = [entree for entree in zone if entree.endswith("/")]
    assert dossiers
    for dossier in dossiers:
        decision = integration.examiner(pr(fichiers=(dossier[:-1],)), REQUIS, PREFIXES, zone)
        assert decision.action == integration.RIEN
        assert "zone protégée" in decision.raison


def test_zone_une_erreur_github_retient_la_pr_sans_cacher_les_suivantes():
    from outils import github
    from outils.__main__ import _pr_integrable

    class Illisible(_GithubOrigine):
        def liste(self, chemin, **kwargs):
            if chemin.endswith("/files"):
                raise github.GithubErreur("accès refusé", 403)
            return super().liste(chemin, **kwargs)
    obtenu = _pr_integrable(Illisible(), {"number": 200, "head": {"ref": "agent/049-x", "repo": {"full_name": "O/R"}}}, "master", PREFIXES)
    rapport = integration.decider([obtenu, pr(numero=201, fichiers=("ordinaire.txt",))], REQUIS, PREFIXES, _zone_du_depot())
    assert rapport.decision.action == integration.FUSIONNER
    assert rapport.decision.pr == 201
    assert "accès refusé" in rapport.lignes[0]


@pytest.mark.parametrize("fichiers", [None, (), ("",), ("../AGENTS.md",), ("/AGENTS.md",)])
def test_zone_une_liste_de_fichiers_inconnue_ne_libere_pas(fichiers):
    decision = integration.examiner(pr(fichiers=fichiers), REQUIS, PREFIXES, _zone_du_depot())
    assert decision.action == integration.RIEN
    assert "fichiers" in decision.raison


@pytest.mark.parametrize("valeur", [None, [], "AGENTS.md", [""], [12], ["../"], ["/"], [".github//"], ["AGENTS.md", "AGENTS.md"]])
def test_zone_absente_vide_ou_mal_formee_fait_echouer_la_commande(tmp_path, monkeypatch, capsys, valeur):
    import json
    from outils import github
    from outils.__main__ import main

    _atelier_integration(tmp_path, REQUIS, PREFIXES)
    config = tmp_path / "atelier.toml"
    texte = "\n".join(l for l in config.read_text(encoding="utf-8").splitlines() if not l.startswith("zone ="))
    if valeur is not None:
        texte += "\nzone = " + json.dumps(valeur)
    config.write_text(texte + "\n", encoding="utf-8")
    def interdit(*a, **k):
        raise AssertionError("une configuration invalide ne consulte pas GitHub")
    monkeypatch.setattr(github, "Github", interdit)
    assert main(["integration", "--depot", "O/R", "--projet", str(tmp_path)]) == 1
    io = capsys.readouterr()
    assert io.out == ""
    assert "zone" in io.err


def test_zone_la_commande_et_le_tableau_retiennent_le_meme_chemin(tmp_path, monkeypatch, capsys):
    from outils import registre
    from outils.__main__ import _examens

    _atelier_integration(tmp_path, REQUIS, PREFIXES)
    class Protegee(_GithubDecision):
        def liste(self, chemin, **kwargs):
            if chemin.endswith("/files"):
                return [{"filename": "AGENTS.md", "status": "modified"}]
            return super().liste(chemin, **kwargs)
    faux = Protegee(
        [{"number": 200, "head": {"ref": "agent/049-x", "repo": {"full_name": "O/R"}}, "draft": False}],
        {"head": {"sha": "a" * 40, "ref": "agent/049-x"}, "mergeable": True, "changed_files": 1},
        0, [{"name": nom, "status": "completed", "conclusion": "success"} for nom in REQUIS],
    )
    code, io = _cli_integration(tmp_path, monkeypatch, capsys, faux)
    assert code == 0
    assert io.out == "RIEN\n"
    examen = _examens(faux, "master", registre.integration(tmp_path))[0][1]
    assert examen.action == integration.RIEN
    assert examen.raison in io.err
    assert "zone protégée" in examen.raison


def test_zone_une_revision_changee_pendant_la_lecture_retient():
    from outils.__main__ import _pr_integrable

    class Mobile(_GithubOrigine):
        def __init__(self):
            super().__init__()
            self.details = 0
        def get(self, chemin, **kwargs):
            resultat = super().get(chemin, **kwargs)
            if chemin == "pulls/200":
                self.details += 1
                resultat["changed_files"] = 1
                resultat["head"]["sha"] = ("a" if self.details == 1 else "b") * 40
            return resultat
        def liste(self, chemin, **kwargs):
            if chemin.endswith("/files"):
                return [{"filename": "outils/tableau.py", "status": "modified"}]
            return super().liste(chemin, **kwargs)
    obtenu = _pr_integrable(Mobile(), {"number": 200, "head": {"ref": "agent/049-x", "repo": {"full_name": "O/R"}}}, "master", PREFIXES)
    decision = integration.examiner(obtenu, REQUIS, PREFIXES, _zone_du_depot())
    assert decision.action == integration.RIEN
    assert "révision" in decision.raison


@pytest.mark.parametrize("retard", [0, 1])
def test_zone_une_revision_changee_pendant_les_revues_retient(retard):
    from copy import deepcopy
    from outils.__main__ import _pr_integrable

    class Mobile(_GithubDecision):
        courant = "a" * 40

        def get(self, chemin, **kwargs):
            resultat = deepcopy(super().get(chemin, **kwargs))
            if chemin == "pulls/200":
                resultat["head"]["sha"] = self.courant
            return resultat

        def liste(self, chemin, **kwargs):
            resultat = super().liste(chemin, **kwargs)
            if chemin.endswith("/reviews"):
                self.courant = "b" * 40
            return resultat

    brut = {"number": 200, "head": {"ref": "agent/049-x", "repo": {"full_name": "O/R"}}}
    faux = Mobile([brut], {"head": {"sha": "a" * 40, "ref": "agent/049-x"},
                          "mergeable": True}, retard,
                  [{"name": nom, "status": "completed", "conclusion": "success"} for nom in REQUIS])
    obtenu = _pr_integrable(faux, brut, "master", PREFIXES)
    decision = integration.examiner(obtenu, REQUIS, PREFIXES, _zone_du_depot())
    assert decision.action == integration.RIEN
    assert "révision" in decision.raison


@pytest.mark.parametrize("retard", [0, 1])
def test_zone_un_aller_retour_de_branche_ne_cache_pas_le_commit_protege(tmp_path, monkeypatch, capsys, retard):
    from copy import deepcopy

    class AllerRetour(_GithubDecision):
        def get(self, chemin, **kwargs):
            if chemin.startswith("git/commits/"):
                sha = chemin.rsplit("/", 1)[1]
                return {"sha": sha, "tree": {"sha": ("c" if sha == "f" * 40 else "d") * 40}}
            if chemin.startswith("git/trees/"):
                sha = chemin.rsplit("/", 1)[1]
                return {"sha": sha, "truncated": False, "tree": [
                    {"path": "AGENTS.md", "type": "blob", "mode": "100644",
                     "sha": ("e" if sha == "c" * 40 else "b") * 40}]}
            resultat = deepcopy(super().get(chemin, **kwargs))
            if chemin.startswith("compare/"):
                resultat["merge_base_commit"] = {"sha": "f" * 40}
            return resultat

        def liste(self, chemin, **kwargs):
            # L'API mutable donne le diff de B, mais le détail initial et
            # final donne A. Les arbres de A touchent réellement AGENTS.md.
            if chemin.endswith("/files"):
                return [{"filename": "ordinaire.txt", "status": "modified"}]
            return super().liste(chemin, **kwargs)

    _atelier_integration(tmp_path, REQUIS, PREFIXES)
    brut = {"number": 200, "head": {"ref": "agent/049-x", "repo": {"full_name": "O/R"}}}
    faux = AllerRetour([brut], {"head": {"sha": "a" * 40, "ref": "agent/049-x"},
                               "base": {"sha": "f" * 40, "ref": "master"}, "mergeable": True}, retard,
                      [{"name": nom, "status": "completed", "conclusion": "success"} for nom in REQUIS])
    code, io = _cli_integration(tmp_path, monkeypatch, capsys, faux)
    assert code == 0
    assert io.out == "RIEN\n"
    assert "zone protégée" in io.err


@pytest.mark.parametrize("moment", [1, 2])
def test_zone_une_pr_retargetee_pendant_l_examen_retient(tmp_path, monkeypatch, capsys, moment):
    from copy import deepcopy

    class Retargetee(_GithubDecision):
        lectures = 0

        def get(self, chemin, **kwargs):
            resultat = deepcopy(super().get(chemin, **kwargs))
            if chemin == "pulls/200":
                self.lectures += 1
                if self.lectures == moment:
                    resultat["base"]["ref"] = "autre"
            return resultat

    _atelier_integration(tmp_path, REQUIS, PREFIXES)
    brut = {"number": 200, "head": {"ref": "agent/049-x", "repo": {"full_name": "O/R"}}}
    faux = Retargetee([brut], {"head": {"sha": "a" * 40, "ref": "agent/049-x"}, "mergeable": True}, 0,
                     [{"name": nom, "status": "completed", "conclusion": "success"} for nom in REQUIS])
    code, io = _cli_integration(tmp_path, monkeypatch, capsys, faux)
    assert code == 0
    assert io.out == "RIEN\n"
    assert "base" in io.err
