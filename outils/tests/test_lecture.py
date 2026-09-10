"""La couture avec GitHub : les noms de champs, et ce qu'un blanc veut dire.

Les décisions sont éprouvées ailleurs. Ici on éprouve ce qui les
alimente — l'endroit où une clé mal orthographiée rend un brouillon
éveillé ou une PR conflictuelle fusionnable, sans que rien ne rougisse.
"""

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import threading
from urllib.parse import parse_qs, urlparse

import pytest

from outils import integration, relecture


def test_une_pr_ecartee_n_est_lue_qu_a_moitie():
    """Sans détail, la fusionnabilité est inconnue — pas vraie."""
    pr = integration.depuis_github(
        {"number": 215, "head": {"ref": "cursor/essai"}, "draft": True}
    )
    assert pr.numero == 215
    assert pr.branche == "cursor/essai"
    assert pr.brouillon is True
    assert pr.fusionnable is None
    assert pr.controles == ()


def test_un_brouillon_absent_du_json_n_est_pas_un_brouillon():
    pr = integration.depuis_github({"number": 1, "head": {"ref": "agent/049-x"}})
    assert pr.brouillon is False


def test_les_controles_arrivent_avec_leur_etat_traduit():
    pr = integration.depuis_github(
        {"number": 216, "head": {"ref": "agent/049-x"}},
        {"mergeable": True, "head": {"sha": "a" * 40}},
        [("sim", "completed", "success"), ("vues", "in_progress", None),
         ("gitleaks", "completed", "failure")],
        retard=2,
    )
    assert pr.relue is None  # sans verdict, on ne sait pas — on ne suppose pas
    par_nom = {c.nom: c.etat for c in pr.controles}
    assert par_nom == {
        "sim": integration.VERT,
        "vues": integration.EN_COURS,
        "gitleaks": integration.ROUGE,
    }
    assert pr.retard == 2
    assert pr.fusionnable is True


def test_une_fusionnabilite_que_github_n_a_pas_calculee_reste_inconnue():
    pr = integration.depuis_github(
        {"number": 216, "head": {"ref": "agent/049-x"}},
        {"head": {"sha": "a" * 40}},
    )
    assert pr.fusionnable is None


def test_une_approbation_que_personne_ne_signe_ne_compte_pas():
    """GitHub rend `user: null` pour un compte supprimé. Un auteur vide
    n'est pas un tiers : il n'est personne."""
    revues = relecture.revues_depuis_github(
        [{"user": None, "state": "APPROVED", "commit_id": "a" * 40}]
    )
    assert revues[0].auteur == ""
    assert not relecture.juger("a" * 40, ["cursor[bot]"], revues).passe


def test_une_revue_sans_revision_est_lue_comme_vide():
    revues = relecture.revues_depuis_github(
        [{"user": {"login": "claude[bot]"}, "state": "APPROVED", "commit_id": None}]
    )
    assert revues[0].revision == ""
    assert not relecture.juger("a" * 40, ["cursor[bot]"], revues).passe


def _brancher(dossier, corps: str):
    (dossier / "atelier.toml").write_text(
        '[projet]\nnom = "Essai"\nfeuille = "ROADMAP.md"\nbranche_base = "master"\n' + corps,
        encoding="utf-8",
    )
    return dossier


def test_le_branchement_rend_ce_que_le_projet_declare(tmp_path):
    from outils import registre

    _brancher(tmp_path, "")
    assert registre.branchement(tmp_path)["feuille"] == "ROADMAP.md"
    assert registre.branchement(tmp_path)["base"] == "master"


def test_sans_section_integration_on_refuse_au_lieu_de_deviner(tmp_path):
    from outils import registre

    _brancher(tmp_path, "")
    with pytest.raises(registre.BranchementIncomplet) as refus:
        registre.integration(tmp_path)
    assert "[integration]" in str(refus.value)


def test_une_liste_de_controles_vide_est_un_branchement_incomplet(tmp_path):
    """Une liste vide ferait entrer n'importe quoi. Elle se refuse à la
    lecture, avant même que la décision ait à s'en méfier."""
    from outils import registre

    _brancher(tmp_path, '\n[integration]\ncontroles = []\nbranches = ["agent/"]\n')
    with pytest.raises(registre.BranchementIncomplet) as refus:
        registre.integration(tmp_path)
    assert "controles" in str(refus.value)


def test_le_branchement_d_integration_rend_ce_qu_il_declare(tmp_path):
    from outils import registre

    _brancher(tmp_path, '\n[integration]\ncontroles = ["sim"]\nbranches = ["agent/"]\n')
    reglage = registre.integration(tmp_path)
    assert reglage["controles"] == ("sim",)
    assert reglage["branches"] == ("agent/",)


def test_un_atelier_toml_absent_se_dit(tmp_path):
    from outils import registre

    with pytest.raises(registre.BranchementIncomplet):
        registre.branchement(tmp_path)


def test_une_ligne_courte_passe_telle_quelle():
    from outils import github

    assert github.borner("PASS  PR 225 — approuvée") == "PASS  PR 225 — approuvée"


def test_une_ligne_trop_longue_est_coupee_en_caracteres():
    """GitHub refuse toute la requête au-delà de 140 caractères : l'état ne
    serait pas posé du tout, donc absent, donc bloquant — et muet. La coupe
    se fait en caractères : couper des octets casserait un accent en deux."""
    from outils import github

    longue = "é" * 300
    court = github.borner(longue)
    assert len(court) == github.BORNE_DESCRIPTION
    assert court.endswith("…")
    court.encode("utf-8").decode("utf-8")  # rouge si un caractère a été coupé


def test_une_ligne_bornee_ne_garde_que_sa_premiere_ligne():
    from outils import github

    assert github.borner("FAIL  la raison\net une trace\nqui déborde") == "FAIL  la raison"


def test_le_verdict_le_plus_bavard_tient_dans_une_description():
    """La borne se tient une fois, en Python : le script reprend la ligne
    telle quelle et n'a rien à couper. Le verdict le plus long est celui
    qui énumère des relecteurs — il n'a pas de longueur maximale."""
    from outils import github, relecture

    verdict = relecture.juger(
        "a" * 40,
        ["cursor[bot]"],
        [relecture.Revue(f"un-relecteur-au-nom-interminable-{i}", "APPROVED", "a" * 40)
         for i in range(40)],
    )
    assert len(verdict.raison) > github.BORNE_DESCRIPTION  # sinon le cas ne prouve rien
    ligne = github.borner(f"PASS  PR 225 — {verdict.raison}")
    assert len(ligne) == github.BORNE_DESCRIPTION


def test_le_verdict_de_relecture_voyage_avec_la_pr():
    """Le verdict se calcule dans le code de `master` et arrive ici : la
    décision ne relit pas un état que la PR aurait pu poser elle-même."""
    from outils import relecture

    verdict = relecture.juger(
        "a" * 40, ["cursor[bot]"], [relecture.Revue("pliagre", "APPROVED", "a" * 40)]
    )
    pr = integration.depuis_github(
        {"number": 216, "head": {"ref": "agent/049-x"}},
        {"mergeable": True, "head": {"sha": "a" * 40}},
        verdict=verdict,
    )
    assert pr.relue is True
    assert "pliagre" in pr.motif_relecture


def test_un_verdict_defavorable_voyage_avec_son_motif():
    from outils import relecture

    verdict = relecture.juger("a" * 40, ["cursor[bot]"], [])
    pr = integration.depuis_github(
        {"number": 216, "head": {"ref": "agent/049-x"}},
        {"mergeable": True, "head": {"sha": "a" * 40}},
        verdict=verdict,
    )
    assert pr.relue is False
    assert "absente" in pr.motif_relecture


@contextmanager
def _api(routes):
    """Un GitHub de banc : `chemin` ou `(chemin, page)` → (statut, corps, en-têtes)."""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            return

        def do_GET(self):
            parsed = urlparse(self.path)
            page = parse_qs(parsed.query).get("page", ["1"])[0]
            chemin = parsed.path.lstrip("/")
            cle = (chemin, page) if (chemin, page) in routes else chemin
            if cle not in routes:
                self.send_response(404)
                corps = b'{"message":"absent"}'
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(corps)))
                self.end_headers()
                self.wfile.write(corps)
                return
            statut, corps, extra = routes[cle]
            payload = corps if isinstance(corps, bytes) else json.dumps(corps).encode("utf-8")
            self.send_response(statut)
            self.send_header("Content-Type", "application/json")
            for nom, valeur in extra.items():
                self.send_header(nom, valeur)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    serveur = HTTPServer(("127.0.0.1", 0), Handler)
    fil = threading.Thread(target=serveur.serve_forever, daemon=True)
    fil.start()
    host, port = serveur.server_address[:2]
    try:
        yield f"http://{host}:{port}"
    finally:
        serveur.shutdown()
        serveur.server_close()


def test_une_feuille_non_nommee_se_refuse(tmp_path):
    """Sans [projet].feuille, on ne cherche pas le registre au hasard."""
    from outils import registre

    (tmp_path / "atelier.toml").write_text('[projet]\nnom = "Essai"\n', encoding="utf-8")
    with pytest.raises(registre.BranchementIncomplet) as refus:
        registre.feuille(tmp_path)
    assert "feuille" in str(refus.value)


def test_un_depot_sans_slash_se_refuse():
    from outils import github

    with pytest.raises(github.GithubErreur) as refus:
        github.Github("pas-un-depot", jeton="x")
    assert "proprietaire/nom" in str(refus.value)


def test_sans_jeton_on_refuse_plutot_que_de_lire_un_403_comme_rien(monkeypatch):
    """Un 403 lu comme « rien à faire » arrêterait la boucle en silence."""
    from outils import github

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with pytest.raises(github.GithubErreur) as refus:
        github.Github("O/R", jeton=None)
    assert "jeton" in str(refus.value)


def test_un_403_n_est_pas_une_liste_vide():
    from outils import github

    with _api({"repos/O/R/pulls": (403, {"message": "Forbidden"}, {})}) as api:
        gh = github.Github("O/R", jeton="x", api=api)
        with pytest.raises(github.GithubErreur) as refus:
            gh.liste("pulls")
    assert "403" in str(refus.value)


def test_une_page_oubliee_ne_fait_pas_une_liste_complete():
    """`liste` enchaîne les pages ; s'arrêter à 100 ment par omission."""
    from outils import github

    premiere = [{"number": i} for i in range(100)]
    suite = [{"number": 100}]
    routes = {
        ("repos/O/R/pulls", "1"): (
            200,
            premiere,
            {"Link": '<http://x?page=2>; rel="next"'},
        ),
        ("repos/O/R/pulls", "2"): (200, suite, {}),
    }
    with _api(routes) as api:
        gh = github.Github("O/R", jeton="x", api=api)
        obtenu = gh.liste("pulls")
    assert [p["number"] for p in obtenu] == list(range(101))


def test_une_collection_qui_n_est_pas_une_liste_se_refuse():
    from outils import github

    with _api({"repos/O/R/pulls": (200, {"message": "pas une liste"}, {})}) as api:
        gh = github.Github("O/R", jeton="x", api=api)
        with pytest.raises(github.GithubErreur) as refus:
            gh.liste("pulls")
    assert "liste" in str(refus.value)


def test_les_controles_lisent_check_runs_et_statuts():
    """En lire un seul laisserait un contrôle requis introuvable, donc bloquant."""
    from outils import github

    class Faux:
        def get(self, chemin, **_):
            if "check-runs" in chemin:
                return {
                    "check_runs": [
                        {"name": "sim", "status": "completed", "conclusion": "success"}
                    ]
                }
            if chemin.endswith("/status") or "/status?" in chemin or chemin.endswith("status"):
                return {"statuses": [{"context": "vues", "state": "pending"}]}
            raise AssertionError(chemin)

    trouves = github.controles(Faux(), "a" * 40)
    assert ("sim", "completed", "success") in trouves
    assert ("vues", "in_progress", "pending") in trouves


def test_les_auteurs_dedoublonnent_author_et_committer():
    from outils import github

    class Faux:
        def liste(self, _chemin):
            return [
                {"author": {"login": "alice"}, "committer": {"login": "alice"}},
                {"author": {"login": "bob"}, "committer": {"login": "web-flow"}},
                {"author": None, "committer": {"login": "bob"}},
            ]

    assert github.auteurs_du_code(Faux(), 1) == ["alice", "bob", "web-flow"]


def test_le_retard_lit_behind_by():
    from outils import github

    class Faux:
        def get(self, _chemin, **_):
            return {"behind_by": 3}

    assert github.retard(Faux(), "master", "abc") == 3


def test_un_brouillon_n_appelle_pas_le_detail():
    """Hors préfixe ou brouillon : on n'invente pas une fusionnabilité, on n'appelle pas."""
    from outils.__main__ import _pr_integrable

    class Faux:
        def __init__(self):
            self.appels = []

        def get(self, chemin, **_):
            self.appels.append(chemin)
            return {"head": {"sha": "a" * 40}, "mergeable": True}

    faux = Faux()
    brouillon = _pr_integrable(
        faux, {"number": 1, "head": {"ref": "agent/049-x"}, "draft": True},
        "master", ("agent/",),
    )
    assert brouillon.brouillon is True
    assert brouillon.fusionnable is None
    assert faux.appels == []

    hors = _pr_integrable(
        faux, {"number": 2, "head": {"ref": "cursor/essai"}},
        "master", ("agent/",),
    )
    assert hors.branche == "cursor/essai"
    assert hors.fusionnable is None
    assert faux.appels == []


def test_cli_depot_mal_forme_sort_en_echec():
    import subprocess
    import sys

    proc = subprocess.run(
        [
            sys.executable, "-m", "outils", "relecture",
            "--depot", "pas-un-depot", "--pr", "1", "--jeton", "x",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    assert "FAIL" in proc.stderr
    assert proc.stdout == ""


# ----------------------------------------------------------------------
# Les seuils de la page de pilotage : ils vivent dans le branchement, pas
# dans le code. Et la couture avec GitHub pour ce que la page lit en
# plus — protection, publication, historique.
# ----------------------------------------------------------------------


def test_sans_section_tableau_on_refuse_au_lieu_de_deviner(tmp_path):
    """Un seuil deviné serait un réglage que personne n'a posé."""
    from outils import registre

    _brancher(tmp_path, "")
    with pytest.raises(registre.BranchementIncomplet) as refus:
        registre.tableau(tmp_path)
    assert "[tableau]" in str(refus.value)


def test_un_seuil_manquant_est_un_branchement_incomplet(tmp_path):
    from outils import registre

    _brancher(tmp_path, "\n[tableau]\ntours_sans_fusion = 10\n")
    with pytest.raises(registre.BranchementIncomplet) as refus:
        registre.tableau(tmp_path)
    assert "brouillon_jours" in str(refus.value)


def test_un_seuil_nul_se_refuse_plutot_que_d_alerter_toujours(tmp_path):
    from outils import registre

    _brancher(tmp_path, "\n[tableau]\ntours_sans_fusion = 0\nbrouillon_jours = 2\n"
                        "journal = 30\nsemaines = 8\nexecutions = 100\nhistorique = 200\n")
    with pytest.raises(registre.BranchementIncomplet) as refus:
        registre.tableau(tmp_path)
    assert "positif" in str(refus.value)


def test_les_seuils_du_depot_sont_bien_ceux_qu_atelier_toml_declare():
    """Le branchement réel, pas un gabarit : c'est lui qui gouverne la page."""
    from outils import registre
    from outils.tests.banc import RACINE

    seuils = registre.tableau(RACINE)
    assert set(seuils) == set(registre.CLES_TABLEAU)
    assert all(valeur > 0 for valeur in seuils.values())


def test_un_404_est_un_fait_une_autre_erreur_est_un_inconnu():
    """Distinction qui décide de ce que la page affiche : « absent » ou
    « inconnu ». Les confondre montre une porte ouverte là où elle est
    peut-être fermée à clé."""
    from outils import github

    routes = {
        "repos/O/R/pages": (404, {"message": "Not Found"}, {}),
        "repos/O/R/branches/master/protection": (403, {"message": "Forbidden"}, {}),
    }
    with _api(routes) as api:
        gh = github.Github("O/R", jeton="x", api=api)
        absent = github.pages(gh)
        illisible = github.protection(gh, "master")
    assert absent.connue is True and absent.valeur is None
    assert illisible.connue is False and "403" in illisible.raison


def test_une_erreur_de_github_porte_son_code():
    """Le code voyage avec le message : c'est lui qui distingue les deux
    cas ci-dessus, et une comparaison de chaînes s'userait."""
    from outils import github

    with _api({"repos/O/R/pages": (404, {"message": "Not Found"}, {})}) as api:
        gh = github.Github("O/R", jeton="x", api=api)
        with pytest.raises(github.GithubErreur) as refus:
            gh.get("pages")
    assert refus.value.code == 404


def test_une_collection_sans_fin_se_borne_au_lieu_de_tout_lire():
    """L'historique des exécutions se compte en milliers : les lire tous
    pour n'en montrer dix coûterait un tour entier."""
    from outils import github

    routes = {
        ("repos/O/R/pulls", "1"): (
            200, [{"number": i} for i in range(100)],
            {"Link": '<http://x?page=2>; rel="next"'},
        ),
        ("repos/O/R/pulls", "2"): (200, [{"number": 100}], {}),
    }
    with _api(routes) as api:
        gh = github.Github("O/R", jeton="x", api=api)
        assert len(gh.liste("pulls", limite=10)) == 10
        assert len(gh.liste("pulls")) == 101


def test_les_executions_d_un_travail_se_lisent_avec_leur_lien():
    from outils import github

    course = {
        "workflow_runs": [
            {"name": "integration", "run_started_at": "2026-09-08T08:29:03Z",
             "conclusion": "success", "html_url": "https://github.com/O/R/actions/runs/1"},
        ]
    }
    with _api({"repos/O/R/actions/workflows/integration.yml/runs": (200, course, {})}) as api:
        gh = github.Github("O/R", jeton="x", api=api)
        lues = github.executions(gh, "integration.yml", 10)
    assert lues[0]["conclusion"] == "success"


# ----------------------------------------------------------------------
# SC9 : `outils/` ne dépend que de la bibliothèque standard.
# ----------------------------------------------------------------------


# Le seul module extérieur qu'`outils/` a le droit d'appeler, et le seul
# fichier qui a le droit de l'appeler. L'atelier est le lecteur du
# registre, et il n'y en a qu'un : deux analyseurs du même format
# finiraient par ne pas dire la même chose du même fichier.
LECTEUR_DU_REGISTRE = "atelier"
SON_SEUL_APPELANT = "registre.py"


def _imports(source: str):
    """Les modules qu'un fichier importe, sans les imports relatifs."""
    import ast

    trouves: list[str] = []
    for noeud in ast.walk(ast.parse(source)):
        if isinstance(noeud, ast.Import):
            trouves.extend(alias.name for alias in noeud.names)
        elif isinstance(noeud, ast.ImportFrom) and not noeud.level:
            trouves.append(noeud.module or "")
    return [nom.split(".")[0] for nom in trouves if nom]


def test_outils_n_importe_que_la_bibliotheque_standard_et_lui_meme():
    """C'est ce qui fait qu'`outils/` tourne partout, sans rien installer.

    La référence est dérivée : `sys.stdlib_module_names`, pas une liste
    recopiée ici qui vieillirait sans prévenir (règle 2). La seule
    exception est le lecteur du registre, et elle est bornée au fichier
    qui la déclare — le contrôle suivant l'y tient.
    """
    import sys
    from outils.tests.banc import RACINE

    fichiers = sorted((RACINE / "outils").glob("*.py"))
    assert fichiers, "aucun fichier à contrôler : ce contrôle ne prouverait rien"
    etrangers = [
        f"{fichier.name} : {nom}"
        for fichier in fichiers
        for nom in _imports(fichier.read_text(encoding="utf-8"))
        if nom not in sys.stdlib_module_names
        and nom not in ("outils", LECTEUR_DU_REGISTRE)
    ]
    assert etrangers == [], etrangers


def test_le_registre_n_a_qu_un_lecteur_et_un_seul_fichier_l_appelle():
    """« Il n'y a qu'un lecteur du registre » cesse d'être une consigne."""
    from outils.tests.banc import RACINE

    appelants = sorted(
        fichier.name
        for fichier in (RACINE / "outils").glob("*.py")
        if LECTEUR_DU_REGISTRE in _imports(fichier.read_text(encoding="utf-8"))
    )
    assert appelants == [SON_SEUL_APPELANT]


def test_le_controle_des_imports_rougirait_sur_une_dependance():
    """Prouver le rouge : sans ce cas, le contrôle ci-dessus pourrait
    passer parce qu'il ne regarde rien (règle 4)."""
    import ast
    import sys

    arbre = ast.parse("import numpy\nfrom . import github\nimport json\n")
    etrangers = []
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.Import):
            for alias in noeud.names:
                racine = alias.name.split(".")[0]
                if racine not in sys.stdlib_module_names and racine != "outils":
                    etrangers.append(alias.name)
    assert etrangers == ["numpy"]


# ----------------------------------------------------------------------
# SC11 : changer l'état d'un lot passe par le juge de l'atelier.
# ----------------------------------------------------------------------


def _projet_avec_registre(tmp_path):
    """Un projet minimal : un branchement, un registre, un brief."""
    _brancher(tmp_path, '\n[integration]\ncontroles = ["outils"]\nbranches = ["agent/"]\n'
                        "\n[tableau]\ntours_sans_fusion = 10\nbrouillon_jours = 2\n"
                        "journal = 30\nsemaines = 8\nexecutions = 100\nhistorique = 200\n")
    (tmp_path / "briefs").mkdir(exist_ok=True)
    (tmp_path / "briefs" / "049-fabriquer.md").write_text(
        "# Brief 049 — fabriquer\n", encoding="utf-8"
    )
    (tmp_path / "ROADMAP.md").write_text(
        "# ROADMAP\n\n<!-- lots:debut -->\n\n"
        "### [049 — Fabriquer](briefs/049-fabriquer.md)\n"
        "état : pret · couche : 2 · dépend de : — · PR : —\n\n"
        "### [046 — La mer](briefs/046-la-mer.md)\n"
        "état : livre · couche : 1 · dépend de : — · PR : 206\n\n"
        "<!-- lots:fin -->\n",
        encoding="utf-8",
    )
    return tmp_path


def _etat_cli(projet, lot, etat, *extra):
    import subprocess
    import sys

    return subprocess.run(
        [sys.executable, "-m", "outils", "etat", "--projet", str(projet),
         "--lot", lot, "--etat", etat, *extra],
        capture_output=True, text=True,
    )


def test_une_transition_interdite_est_refusee_avec_le_message_qui_la_nomme():
    """`livre` est un état terminal : un lot livré ne s'abandonne pas."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as dossier:
        projet = _projet_avec_registre(Path(dossier))
        proc = _etat_cli(projet, "046", "abandonne")
    assert proc.returncode == 1
    assert "transition interdite" in proc.stderr
    assert "livre → abandonne" in proc.stderr
    assert proc.stdout == ""


def test_une_transition_permise_rend_la_souche_de_sa_branche():
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as dossier:
        projet = _projet_avec_registre(Path(dossier))
        proc = _etat_cli(projet, "049", "abandonne")
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip() == "etat 049 abandonne etat-049-abandonne"
        # Sans `--ecrire`, le registre n'a pas bougé.
        assert "état : pret" in (projet / "ROADMAP.md").read_text(encoding="utf-8")


def test_un_lot_deja_dans_l_etat_demande_ne_refait_pas_le_geste():
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as dossier:
        projet = _projet_avec_registre(Path(dossier))
        proc = _etat_cli(projet, "049", "pret")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "RIEN"
    assert "déjà fait" in proc.stderr


def test_un_lot_sans_fiche_ne_se_marque_pas():
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as dossier:
        projet = _projet_avec_registre(Path(dossier))
        proc = _etat_cli(projet, "999", "abandonne")
    assert proc.returncode == 1
    assert "aucune fiche" in proc.stderr


def test_avec_ecrire_la_fiche_change_et_rien_d_autre():
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as dossier:
        projet = _projet_avec_registre(Path(dossier))
        avant = (projet / "ROADMAP.md").read_text(encoding="utf-8")
        proc = _etat_cli(projet, "049", "abandonne", "--ecrire")
        apres = (projet / "ROADMAP.md").read_text(encoding="utf-8")
    assert proc.returncode == 0, proc.stderr
    assert "état : abandonne" in apres
    assert avant.count("###") == apres.count("###")
    assert "état : livre · couche : 1" in apres
