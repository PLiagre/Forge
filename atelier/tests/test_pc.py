"""Le côté PC d'un lot « machine : pc » : un pas du meneur, et ce qu'Unity en voit.

Aucun test ne lance le vrai Unity. Les défauts que ces tests gardent : un
passage du PC tombé sans réponse faisait attendre le VPS un jour ; une liste
d'assemblies séparée par une virgule ne jouait aucun test et passait pour
verte ; un chemin relatif envoyait les résultats sous `3d/unity/3d/unity`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from atelier import lots, pc
from atelier.depot import DepotErreur

from conftest import Agents

FICHE = "## Ce que je joue de plus\nJe bâtis une caserne.\n\n## Ce que je vois samedi\nLa caserne dans la ville.\n"
ETAPES = [{"titre": "Le bâtiment", "quoi": "Caserne.cs", "qui": "chef", "tests": "Forge.Pont.Tests"},
          {"titre": "La capture", "quoi": "ScenarioCaserne.cs", "qui": "chef", "tests": "Forge.Pont.Tests"}]
PLAN = {"sortie": {"decision": "plan", "resume": "La caserne, puis sa capture.", "etapes": ETAPES}}
QUOTA = {"code": 1, "brut": "", "erreur": "You've hit your 5-hour limit"}
BRANCHE = "lot/10-la-caserne"
XML = ('<?xml version="1.0" encoding="utf-8"?>\n<test-run testcasecount="3" passed="2" failed="1"><test-suite>'
       '<test-case fullname="A.B" result="Failed"/><test-case fullname="A.C" result="Passed"/>'
       '<test-case name="D" result="Passed"/></test-suite></test-run>')


def faite(fichiers=None, **plus):
    return {"sortie": {"etat": "faite", "compte_rendu": "C'est fait.", **plus},
            "fichiers": fichiers if fichiers is not None else {"3d/unity/Assets/Caserne.cs": "class Caserne {}\n"}}


def _tests_verts(chantier, sortie):
    return 12, 0, ""


def publier_tout(depot, depot_github, fichiers, jour):
    return [f"https://x/{jour}/{f.name}" for f in fichiers]


class FauxUnity:
    """La capture, sans Unity : une image par appel, et le groupe qu'on lui a demandé."""

    def __init__(self, ok=True, images=("plan.png",), fin=""):
        self.ok, self.images, self.fin, self.scenarios = ok, images, fin, []

    def __call__(self, chantier, sortie, *, scenario=""):
        self.scenarios.append(scenario)
        sortie.mkdir(parents=True, exist_ok=True)
        for nom in self.images:
            (sortie / nom).write_bytes(b"png")
        return self.ok, [sortie / nom for nom in self.images], self.fin


def _lot_pc(gh, *marques_de_pr, ci="attente"):
    """Le lot #10, un lot de la ville ; avec des marques, sa PR #50 est ouverte."""
    gh.ajouter_issue(10, "La caserne", ("lot", "en-cours", "ville", "pc"), corps=FICHE)
    if marques_de_pr:
        gh.ajouter_pr(50, BRANCHE, brouillon=True, ci=ci, commentaires=marques_de_pr)


def _plan(etapes=2):
    return lots.marque(role="chef", etat=lots.PLAN, etapes=etapes, detail=ETAPES[:etapes], machine="pc")


def _etape(k):
    return lots.marque(role="chef", etat=lots.ETAPE, etape=k, fini=True, machine="pc")


def _travailler(projet, gh, depot, tmp_path, agents, *, unity=None, tests=_tests_verts, publier=publier_tout):
    depot.gh = gh
    return pc.travailler(projet, gh, depot, issue=10, journal=tmp_path / "journal.jsonl", executeur_agents=agents,
                         unity=unity or FauxUnity(), tests=tests, publier=publier)


def _marques(gh, numero=50, *, pr=True):
    return lots.marques((gh.prs_ if pr else gh.issues_)[numero]["comments"])


def _regarder(tmp_path, **plus):
    plus = {"tests": _tests_verts, "unity": FauxUnity(), "publier": lambda fichiers, jour: [f"u/{f.name}" for f in fichiers]} | plus
    return pc.regarder_avec_unity(tmp_path, 10, "abcdef0123", "2026-11-16", **plus)


# --------------------------------------------------- un pas du meneur
def test_un_lot_pc_sans_pr_recoit_son_plan_sur_le_pc(projet, gh, depot, tmp_path):
    _lot_pc(gh)
    agents = Agents(PLAN)
    lignes = _travailler(projet, gh, depot, tmp_path, agents)
    numero_pr = next(n for n, p in gh.prs_.items() if p["headRefName"] == BRANCHE)
    plan = _marques(gh, numero_pr)[0]
    assert (plan["etat"], plan["machine"], plan["role"], plan["etapes"]) == (lots.PLAN, "pc", "chef", 2)
    assert gh.prs_[numero_pr]["isDraft"] and "Machine : pc" in gh.prs_[numero_pr]["body"]
    assert agents.appels[0]["cwd"] == depot.racine / "chantiers" / "pc", "le chantier du PC, pas celui du lot"
    assert "scénario de capture" in agents.appels[0]["consigne"]
    assert lignes[-1].startswith("#10 plan écrit") and (tmp_path / "journal.jsonl").is_file()


def test_le_pc_fait_l_etape_attendue_dans_sa_session(projet, gh, depot, tmp_path):
    _lot_pc(gh)
    agents, unity = Agents(PLAN, faite()), FauxUnity()
    _travailler(projet, gh, depot, tmp_path, agents)
    gh.commenter_pr(101, lots.marque(role="chef", etat=lots.ENVOYE, action="etape", quand="2026-11-16T10:00:00+00:00"))
    _travailler(projet, gh, depot, tmp_path, agents, unity=unity)
    etape = _marques(gh, 101)[-1]
    assert (etape["etat"], etape["etape"], etape["fini"], etape["machine"]) == (lots.ETAPE, 1, True, "pc")
    assert agents.appels[1]["reprise"] and agents.appels[1]["session"] == agents.appels[0]["session"]
    assert agents.appels[1]["cwd"] == depot.racine / "chantiers" / "pc" and "ÉTAPE 1 SUR 2" in agents.appels[1]["consigne"]
    assert ("pousser", BRANCHE) in depot.gestes and "- [x] **1. Le bâtiment**" in gh.prs_[101]["body"]
    assert unity.scenarios == [] and "unity" not in etape, "Unity ne juge que le plan fini"


def test_a_la_derniere_etape_unity_joue_les_tests_et_la_capture(projet, gh, depot, tmp_path):
    _lot_pc(gh, _plan(), _etape(1))
    unity = FauxUnity(images=("plan.png", "caserne.png"))
    _travailler(projet, gh, depot, tmp_path, Agents(faite(capture="caserne")), unity=unity)
    dit, marque = gh.prs_[50]["comments"][-1]["body"], _marques(gh)[-1]
    assert (marque["etape"], marque["unity"], marque["photo"], marque["capture"]) == (2, "vert", "propre", "caserne")
    assert "✅ **Unity** : le projet compile et ses 12 tests EditMode sont verts sur le PC. Capture « caserne » jouée." in dit
    assert dit.count("📷 ![capture du lot #10](https://x/") == 2 and "-1-caserne.png)" in dit
    assert unity.scenarios == ["caserne"], "le groupe rendu par le meneur est celui qu'Unity joue"
    assert not gh.prs_[50]["isDraft"], "le plan fini, la PR sort du brouillon"


def test_le_groupe_de_capture_nomme_a_une_etape_sert_a_la_derniere(projet, gh, depot, tmp_path):
    _lot_pc(gh, _plan())
    agents, unity = Agents(faite(capture="caserne"), faite()), FauxUnity()
    _travailler(projet, gh, depot, tmp_path, agents, unity=unity)
    assert _marques(gh)[-1]["capture"] == "caserne" and unity.scenarios == []
    _travailler(projet, gh, depot, tmp_path, agents, unity=unity)
    assert unity.scenarios == ["caserne"] and _marques(gh)[-1]["photo"] == "propre"


def test_des_tests_editmode_rouges_sont_dits_dans_le_compte_rendu(projet, gh, depot, tmp_path):
    _lot_pc(gh, _plan(1))
    unity = FauxUnity()
    _travailler(projet, gh, depot, tmp_path, Agents(faite()), unity=unity, tests=lambda chantier, sortie: (40, 2, "A.B\nA.C"))
    assert _marques(gh)[-1]["unity"] == "rouge" and unity.scenarios == [], "des tests rouges ne se photographient pas"
    assert "2 test(s) EditMode en échec sur 40" in gh.dits(50, pr=True) and "A.B\nA.C" in gh.dits(50, pr=True)


# ----------------------------------------------------- ce qu'Unity voit
def test_zero_test_joue_est_rouge(tmp_path):
    vu = _regarder(tmp_path, tests=lambda chantier, sortie: (0, 0, "error CS0103: le nom n'existe pas"))
    assert vu.marque == {"unity": "rouge"} and vu.urls == []
    assert "n'a joué aucun test EditMode" in vu.note and "error CS0103" in vu.note


def test_un_test_en_echec_est_rouge_avec_son_nom(tmp_path):
    unity = FauxUnity()
    vu = _regarder(tmp_path, tests=lambda chantier, sortie: (3, 1, "A.B"), unity=unity)
    assert vu.marque == {"unity": "rouge"} and unity.scenarios == []
    assert "1 test(s) EditMode en échec sur 3" in vu.note and "A.B" in vu.note


def test_des__tests_verts_et_une_capture_ratee_restent_verts_avec_la_note(tmp_path):
    vu = _regarder(tmp_path, unity=FauxUnity(ok=False, images=(), fin="CAPTURE : le scénario caserne a échoué"),
                   scenario="caserne")
    assert vu.marque == {"unity": "vert", "photo": "absente"} and vu.urls == []
    assert "12 tests EditMode sont verts" in vu.note
    assert "⚠️ La capture n'a pas abouti" in vu.note and "CAPTURE : le scénario caserne a échoué" in vu.note


def test_un_unity_qui_leve_une_exception_est_dit_absent(tmp_path):
    def absent(chantier, sortie):
        raise FileNotFoundError("Unity.exe introuvable")
    vu = _regarder(tmp_path, tests=absent)
    assert vu.marque == {"unity": "absent"} and "n'a pas tourné sur le PC : Unity.exe introuvable" in vu.note


def test_une_capture_qui_leve_une_exception_ne_perd_pas_les__tests_verts(tmp_path):
    def pendue(chantier, sortie, *, scenario=""):
        raise RuntimeError("No valid Unity Editor license")
    vu = _regarder(tmp_path, unity=pendue)
    assert vu.marque == {"unity": "vert", "photo": "absente"}
    assert "12 tests EditMode verts" in vu.note and "No valid Unity Editor license" in vu.note


def test_sans_groupe_nomme_seul_le_plan_fixe_est_photographie(tmp_path):
    vu = _regarder(tmp_path)
    assert vu.marque == {"unity": "vert", "photo": "plan-fixe"} and "Plan fixe de la scène seulement." in vu.note
    assert vu.urls == ["u/lot-10-abcdef0-0-plan.png"], "l'image porte le lot, la révision et son rang"


def test_une_publication_ratee_ne_retient_pas_le_lot(tmp_path):
    def refusee(fichiers, jour):
        raise RuntimeError("la poussée du journal est refusée")
    vu = _regarder(tmp_path, publier=refusee)
    assert vu.marque["unity"] == "vert" and vu.urls == [] and "Les images n'ont pas pu être publiées." in vu.note


# ------------------------------------------------- le PC répond toujours
def test_un_agent_en_panne_de_quota_laisse_une_attente_sur_la_pr(projet, gh, depot, tmp_path):
    _lot_pc(gh, _plan())
    lignes = _travailler(projet, gh, depot, tmp_path, Agents(QUOTA))
    attente = _marques(gh)[-1]
    assert (attente["etat"], attente["role"]) == (lots.ATTENTE, "chef") and attente["quand"]
    assert "aucun agent n'a pu répondre" in gh.dits(50, pr=True) and "quota épuisé" in gh.dits(50, pr=True)
    assert lots.etapes_faites(_marques(gh)) == set() and any("attente" in l for l in lignes)
    assert not [m for m in _marques(gh) if m.get("etat") in (lots.ECHEC, lots.COUPE)], "une attente n'est pas un essai"


def test_sans_pr_l_attente_d_un_plan_se_marque_sur_l_issue(projet, gh, depot, tmp_path):
    _lot_pc(gh)
    _travailler(projet, gh, depot, tmp_path, Agents(QUOTA))
    assert gh.prs_ == {} and _marques(gh, 10, pr=False)[-1]["etat"] == lots.ATTENTE


def test_une_exception_avant_la_reponse_laisse_une_attente_puis_remonte(projet, gh, depot, tmp_path):
    def casse(nom, branche):
        raise DepotErreur("le worktree est verrouillé")
    _lot_pc(gh, _plan())
    depot.preparer = casse
    agents = Agents()
    with pytest.raises(DepotErreur, match="verrouillé"):
        _travailler(projet, gh, depot, tmp_path, agents)
    assert _marques(gh)[-1]["etat"] == lots.ATTENTE and agents.appels == []
    assert "le passage du PC a cassé avant de répondre : `DepotErreur: le worktree est verrouillé`" in gh.dits(50, pr=True)


def test_une_exception_avant_le_plan_laisse_son_attente_sur_l_issue(projet, gh, depot, tmp_path):
    def casse():
        raise DepotErreur("origin ne répond pas")
    _lot_pc(gh)
    depot.fetch = casse
    with pytest.raises(DepotErreur):
        _travailler(projet, gh, depot, tmp_path, Agents())
    assert _marques(gh, 10, pr=False)[-1]["etat"] == lots.ATTENTE and "`DepotErreur: origin ne répond pas`" in gh.dits(10)


def test_un_lot_qui_n_attend_pas_le_meneur_le_dit_et_ne_fait_rien(projet, gh, depot, tmp_path):
    _lot_pc(gh, _plan(), _etape(1), _etape(2), ci="attente")
    agents = Agents()
    _travailler(projet, gh, depot, tmp_path, agents)
    assert agents.appels == [] and depot.gestes == []
    assert _marques(gh)[-1]["etat"] == lots.ATTENTE
    assert "le lot n'attend pas un passage du meneur (attendre_ci)" in gh.dits(50, pr=True)


def test_l_envoi_auquel_le_pc_repond_ne_compte_pas_pour_decider_du_pas(projet, gh, depot, tmp_path):
    _lot_pc(gh, _plan(), lots.marque(role="chef", etat=lots.ENVOYE, action="etape", quand="2026-11-16T10:00:00+00:00"))
    agents = Agents(faite())
    _travailler(projet, gh, depot, tmp_path, agents)
    assert len(agents.appels) == 1 and _marques(gh)[-1]["etat"] == lots.ETAPE


# ------------------------------------------------- répondre au silence
def test_un_envoi_reste_sans_reponse_recoit_une_attente(projet, gh, depot, tmp_path):
    _lot_pc(gh, _plan(), lots.marque(role="chef", etat=lots.ENVOYE, action="etape"))
    dit = pc.repondre_au_silence(projet, gh, depot, issue=10, raison="le runner a été coupé",
                                 journal=tmp_path / "journal.jsonl")
    assert dit == "attente marquée sur le lot #10" and _marques(gh)[-1]["etat"] == lots.ATTENTE
    assert "le lot attend — le runner a été coupé" in gh.dits(50, pr=True) and gh.issues_[10]["comments"] == []


def test_sans_pr_le_silence_se_repond_sur_l_issue(projet, gh, depot, tmp_path):
    _lot_pc(gh)
    gh.commenter_issue(10, lots.marque(role="chef", etat=lots.ENVOYE, action="planifier"))
    dit = pc.repondre_au_silence(projet, gh, depot, issue=10, raison="PC en veille", journal=tmp_path / "journal.jsonl")
    assert dit == "attente marquée sur le lot #10"
    assert _marques(gh, 10, pr=False)[-1]["etat"] == lots.ATTENTE and "PC en veille" in gh.dits(10)


@pytest.mark.parametrize("derniere, dit", [
    (lots.marque(role="chef", etat=lots.ETAPE, etape=1, fini=True), "RIEN — le lot #10 n'attend pas le PC (etape)"),
    (lots.marque(role="chef", etat=lots.ATTENTE), "RIEN — le lot #10 n'attend pas le PC (attente)"),
])
def test_une_reponse_deja_ecrite_se_garde(projet, gh, depot, tmp_path, derniere, dit):
    _lot_pc(gh, _plan(), lots.marque(role="chef", etat=lots.ENVOYE, action="etape"), derniere)
    avant = list(gh.gestes)
    assert pc.repondre_au_silence(projet, gh, depot, issue=10, raison="coupé", journal=tmp_path / "journal.jsonl") == dit
    assert gh.gestes == avant


def test_un_lot_jamais_envoye_ne_recoit_pas_d_attente(projet, gh, depot, tmp_path):
    _lot_pc(gh)
    dit = pc.repondre_au_silence(projet, gh, depot, issue=10, raison="coupé", journal=tmp_path / "journal.jsonl")
    assert dit == "RIEN — le lot #10 n'attend pas le PC (aucun envoi)" and gh.gestes == []


# ------------------------------------------------- Unity, sans le lancer
class FauxLancement:
    """À la place d'Unity : garde l'argv, et écrit ce qu'on lui dicte là où l'argv le dit."""

    def __init__(self, xml="", journal="", images=(), code=0):
        self.xml, self.journal, self.images, self.code, self.argv = xml, journal, images, code, []

    def apres(self, option):
        return self.argv[self.argv.index(option) + 1]

    def __call__(self, argv, delai):
        self.argv = argv
        if self.journal:
            Path(self.apres("-logFile")).write_text(self.journal, encoding="utf-8")
        if self.xml:
            Path(self.apres("-testResults")).write_text(self.xml, encoding="utf-8")
        for nom in self.images:
            (Path(self.apres("-forgeCaptures")) / nom).write_bytes(b"png")
        return self.code


@pytest.fixture
def lancer(monkeypatch, tmp_path):
    """Remplace Unity ; le dossier courant est celui du test, pour y passer des chemins relatifs."""
    def installer(**ce_qu_unity_ecrit):
        faux = FauxLancement(**ce_qu_unity_ecrit)
        monkeypatch.setattr(pc, "_lancer_unity", faux)
        return faux
    monkeypatch.setattr(pc, "unity_de", lambda projet_unity: Path("Unity.exe"))
    monkeypatch.chdir(tmp_path)
    return installer


def test_le_compte_des_tests_se_lit_dans_le_xml(lancer):
    lancer(xml=XML, code=2)
    assert pc.jouer_les_tests(Path("chantier"), Path("sortie")) == (3, 1, "A.B")


def test_sans_xml_aucun_cas_n_est_joue(lancer):
    lancer(journal="Chargement\nAssets/Caserne.cs(4,9): error CS0103: le nom « x » n'existe pas\nFin")
    joues, echecs, dit = pc.jouer_les_tests(Path("chantier"), Path("sortie"))
    assert (joues, echecs) == (0, 0) and dit == "Assets/Caserne.cs(4,9): error CS0103: le nom « x » n'existe pas"
    lancer()
    assert pc.jouer_les_tests(Path("chantier"), Path("vide")) == (0, 0, "Unity n'a pas écrit de résultats")


def test_la_liste_des_assemblies_est_separee_par_un_point_virgule(lancer):
    """Le défaut : séparée par une virgule, Unity ne jouait aucun cas et sortait 0."""
    unity = lancer(xml=XML)
    pc.jouer_les_tests(Path("chantier"), Path("sortie"))
    assemblies = unity.apres("-assemblyNames")
    assert assemblies.split(";") == ["Forge.Pont.Tests", "Forge.Interface.Tests"] and "," not in assemblies
    assert unity.apres("-testPlatform") == "EditMode" and "-runTests" in unity.argv and "-batchmode" in unity.argv


def test_les_chemins_passes_a_unity_sont_absolus(lancer, tmp_path):
    """Le défaut : Unity lit un chemin relatif depuis son projet, et écrivait sous `3d/unity/3d/unity`."""
    unity = lancer(xml=XML)
    pc.jouer_les_tests(Path("chantier"), Path("sortie"))
    assert Path(unity.apres("-projectPath")) == tmp_path / "chantier" / "3d" / "unity"
    assert Path(unity.apres("-testResults")) == tmp_path / "sortie" / "tests.xml"
    assert all(Path(unity.apres(option)).is_absolute() for option in ("-projectPath", "-testResults", "-logFile"))
    unity = lancer(images=("plan.png",))
    pc.compiler_et_photographier(Path("chantier"), Path("captures"))
    assert Path(unity.apres("-forgeCaptures")) == tmp_path / "captures"
    assert all(Path(unity.apres(option)).is_absolute() for option in ("-projectPath", "-forgeCaptures", "-logFile"))


def test_une_capture_propre_rend_ses_images(lancer, tmp_path):
    unity = lancer(journal="Tout va bien.", images=("plan.png", "caserne.png"), code=124)
    ok, images, fin = pc.compiler_et_photographier(Path("chantier"), Path("captures"))
    assert ok and [i.name for i in images] == ["caserne.png", "plan.png"] and fin == "Tout va bien."
    assert unity.apres("-executeMethod") == "ForgeLocal3D.Capture.Photographier"
    assert "-nographics" not in unity.argv and "-quit" not in unity.argv, "une caméra doit rendre, et la capture rend la main"


@pytest.mark.parametrize("journal, images, code, dit", [
    ("Compilation\nAssets/Caserne.cs(4,9): error CS0103: inconnu\nFin", ("plan.png",), 0, "Assets/Caserne.cs(4,9): error CS0103: inconnu"),
    ("Début\nCAPTURE : le scénario x a échoué\nFin", ("plan.png",), 0, "CAPTURE : le scénario x a échoué"),
    ("Rien n'a été rendu.", (), 0, "Rien n'a été rendu."),
    ("Unity est tombé.", ("plan.png",), 1, "Unity est tombé."),
])
def test_une_capture_ratee_le_dit(lancer, journal, images, code, dit):
    lancer(journal=journal, images=images, code=code)
    ok, rendues, fin = pc.compiler_et_photographier(Path("chantier"), Path("captures"))
    assert not ok and fin == dit and len(rendues) == len(images)


def test_le_scenario_n_est_passe_que_si_un_groupe_est_nomme(lancer):
    unity = lancer(images=("plan.png",))
    pc.compiler_et_photographier(Path("chantier"), Path("captures"))
    assert "-forgeScenario" not in unity.argv
    pc.compiler_et_photographier(Path("chantier"), Path("captures"), scenario="caserne")
    assert unity.apres("-forgeScenario") == "caserne"


def test_la_version_d_unity_se_lit_dans_le_projet(tmp_path):
    reglages = tmp_path / "ProjectSettings"
    reglages.mkdir()
    (reglages / "ProjectVersion.txt").write_text("m_EditorVersion: 6000.0.23f1\nm_EditorVersionWithRevision: 6000.0.23f1 (1c4764c07fb4)\n",
                                                 encoding="utf-8")
    assert pc.unity_de(tmp_path).parts[-3:] == ("6000.0.23f1", "Editor", "Unity.exe")
    (reglages / "ProjectVersion.txt").write_text("rien\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="version d'Unity illisible"):
        pc.unity_de(tmp_path)
