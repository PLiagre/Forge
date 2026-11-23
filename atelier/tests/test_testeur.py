"""Le testeur joue le build figé d'une étape comme un joueur, et son verdict ne se croit pas sur parole.

Les défauts que ces tests gardent : le premier à jouer un build était le propriétaire ; une démo réussie par
script disait « jouée de bout en bout » d'un jeu où il n'a su ni démarrer ni ouvrir la ville. Un testeur qui lirait
le code saurait où cliquer ; un testeur complaisant dirait « tenue » d'un objectif trouvé au huitième essai ; un
testeur qui joue sur l'écran du propriétaire pendant qu'il s'en sert lui prendrait sa souris.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from atelier import agents as agents_mod
from atelier import consignes, garde_testeur, lots, testeur
from atelier.lots import Lot

from conftest import MAINTENANT, PALIER, Agents

FICHE = ("## Ce que je joue de plus\nJe choisis un pays et je clique « Commencer ».\n\n## Ce que je vois à la démo\n"
         "Avec l'émirat du Zab, le bouton ouvre Biskra.\n\n## La règle du monde\nNiveau 1 : `jeu/data/puissances-1400.json`.\n")


def _objectif(resultat="premier_coup", essais=1, photos=("p01",), nom="Choisir un pays"):
    return {"objectif": nom, "resultat": resultat, "essais": essais, "recit": "J'ai cliqué la France.",
            "photos": list(photos)}


def _recit(verdict="TENUE", objectifs=None, defauts=(), **plus):
    return {"verdict": verdict, "resume": "On s'y retrouve.", "objectifs": objectifs or [_objectif()],
            "non_explique": [{"quoi": "Rien ne dit que seule Biskra est bâtie.", "photo": "p02"}],
            "defauts": list(defauts), "a_corriger_d_abord": ["La France n'a pas de ville."], **plus}


def _defaut(gravite, quoi="Le tracé reste rouge quand il est accepté."):
    return {"quoi": quoi, "nature": "ecran", "gravite": gravite, "photo": "p02"}


# ------------------------------------------------------------- le verdict
def test_tout_du_premier_coup_et_prouve_est_tenu():
    assert testeur.verdict_qui_pese(_recit(), {"p01", "p02"}) == ("TENUE", [])


@pytest.mark.parametrize("recit, attendu, raison", [
    (_recit("TENUE", [_objectif(), _objectif("bloque", 5, (), "Entrer dans la ville")]), "NON_TENUE", "est bloqué"),
    (_recit("TENUE_AVEC_PEINE", [_objectif("apres_essais", 7)]), "NON_TENUE", "au-delà de 5"),
    (_recit("TENUE", [_objectif(), _objectif("non_joue", 0, (), "Lever une armée")]), "NON_TENUE", "n'a pas été joué"),
    (_recit("TENUE", defauts=[_defaut("bloquant")]), "NON_TENUE", "défaut bloquant"),
    (_recit("TENUE", [_objectif("apres_essais", 3)]), "TENUE_AVEC_PEINE", "pas été trouvé du premier coup"),
    (_recit("TENUE", [_objectif("premier_coup", 2)]), "TENUE_AVEC_PEINE", "pas été trouvé du premier coup"),
    (_recit("TENUE", defauts=[_defaut("genant")]), "TENUE_AVEC_PEINE", "défaut gênant"),
], ids=["un objectif bloqué", "trouvé au septième essai", "un objectif pas joué", "un défaut bloquant",
        "trouvé au troisième essai", "premier coup en deux essais", "un défaut gênant"])
def test_un_verdict_complaisant_est_durci_par_ce_que_le_recit_rapporte(recit, attendu, raison):
    """Avoir fini par trouver ne veut pas dire que c'était trouvable : le récit décide, pas l'humeur de celui qui l'écrit."""
    verdict, raisons = testeur.verdict_qui_pese(recit, {"p01", "p02"})
    assert verdict == attendu and any(raison in r for r in raisons)


def test_un_verdict_plus_dur_que_son_recit_est_garde():
    assert testeur.verdict_qui_pese(_recit("NON_TENUE"), {"p01"}) == ("NON_TENUE", [])
    assert testeur.verdict_qui_pese(_recit("TENUE_AVEC_PEINE", defauts=[_defaut("mineur")]), {"p01"})[0] == "TENUE_AVEC_PEINE"


@pytest.mark.parametrize("recit, photos", [
    (_recit(), set()), (_recit(objectifs=[_objectif(photos=())]), {"p01"}),
    (_recit(objectifs=[_objectif(photos=("p09",))]), {"p01"}),
    ({"verdict": "TENUE", "resume": "", "objectifs": [], "non_explique": [], "defauts": [], "a_corriger_d_abord": []}, {"p01"}),
    (_recit("PARFAIT"), {"p01"})],
    ids=["aucune photo prise", "aucune photo citée", "une photo qui n'existe pas", "aucun objectif", "verdict inconnu"])
def test_une_reussite_que_rien_ne_montre_ne_prouve_rien(recit, photos):
    """Un échantillon vide échoue : un « tenue » sans photo n'ouvre aucune étape."""
    assert testeur.verdict_qui_pese(recit, photos)[0] == testeur.SANS_PREUVE


def test_un_passage_interrompu_n_est_pas_un_verdict():
    assert testeur.verdict_qui_pese(_recit("INTERROMPU", [_objectif("bloque", 5, ())]), set()) == ("INTERROMPU", [])


# ----------------------------------------------------------- la promesse
def test_la_promesse_dit_le_but_et_ce_que_chaque_lot_fait_jouer_jamais_ou_cliquer_ni_le_code():
    corps = "Je lance le jeu, je choisis un pays, j'entre dans ma ville.\n\nSes lots : #10, #11\n\nDès que ces lots…"
    livres = [Lot(11, "L'accueil", FICHE, ("lot", "livre"), 1, PALIER), Lot(10, "Chaque pays porte son nom", FICHE, ("lot", "livre"), 1, PALIER)]
    dite = testeur.promesse("On s'y retrouve", corps, livres)
    assert dite.index("Chaque pays porte son nom") < dite.index("L'accueil")
    for attendu in ("L'ÉTAPE : « On s'y retrouve »", "Je lance le jeu, je choisis un pays, j'entre dans ma ville.",
                    "- « L'accueil » : Je choisis un pays et je clique « Commencer »."):
        assert attendu in dite
    for souffle in ("Ses lots", "Dès que ces lots", "émirat du Zab", "Biskra", "puissances-1400.json", "Niveau 1"):
        assert souffle not in dite, f"« {souffle} » dirait où cliquer, ou parlerait du code"


def test_la_promesse_d_une_correction_rappelle_l_etape_qui_reste_a_tenir():
    dite = testeur.promesse("L'accueil réparé", "Je trouve ma ville.\n\nSes lots : #20", [],
                            corrige=("On s'y retrouve", "Je lance le jeu, je choisis un pays."))
    assert "ELLE CORRIGE L'ÉTAPE « On s'y retrouve », QUI RESTE À TENIR :\nJe lance le jeu, je choisis un pays." in dite
    assert "- (aucun lot livré)" in dite


# -------------------------------------------------------------- la garde
OUTIL, DOSSIER = r"D:\Forge\.atelier\pilote-testeur\atelier\jouer_le_build.ps1", r"C:\Users\moi\.atelier\testeur\palier-3"


def _garde(outil_appele, **entree):
    return garde_testeur.refus(outil_appele, entree, OUTIL, DOSSIER)


@pytest.mark.parametrize("commande", [
    f'& "{OUTIL}" -Action lancer', f"& '{OUTIL}' -Action fermer", f'& "{OUTIL}" -Action lancer -Attente 45',
    f'& "{OUTIL}" -Action gestes -Gestes "clic 960 540; attendre 2; photo p01"',
    f'& "{OUTIL.upper()}" -Action gestes -Gestes "rogner 10 20 300 80 p02-zoom; touche 1C"', f'  & "{OUTIL}" -Action sonde  '])
def test_le_testeur_appelle_son_outil_de_jeu_tel_que_sa_consigne_l_ecrit(commande):
    assert _garde("PowerShell", command=commande) == ""


@pytest.mark.parametrize("commande", [
    "Get-Content D:\\Forge\\jeu\\sim\\engine.py", "Invoke-WebRequest http://127.0.0.1:8000/horloge",
    f'& "{OUTIL}" -Action lancer; Get-Content D:\\Forge\\CAP.md', f'& "{OUTIL}" -Action gestes -Gestes "photo p01" | Out-File x',
    f'& "{OUTIL}" -Action gestes -Gestes "photo p01$(Get-Content secret)"', f'& "{OUTIL}" -Action effacer',
    f'& "{OUTIL}" -Action lancer -Build D:\\Forge\\builds\\dernier', f'& "{OUTIL}" -Action lancer -Action fermer',
    '& "D:\\Forge\\.atelier\\direct\\testeur\\outils\\demo.ps1" -Action lancer', f'gh issue list; & "{OUTIL}" -Action sonde', ""])
def test_toute_autre_commande_est_refusee(commande):
    """Le défaut : un testeur qui lit le service du monde ou le code sait où cliquer, et son verdict ne dit plus rien."""
    assert _garde("PowerShell", command=commande)


def test_le_testeur_ne_lit_que_son_dossier_de_passage():
    assert _garde("Read", file_path=DOSSIER + r"\p01.png") == "" and _garde("Read", file_path=DOSSIER + r"\vision.md") == ""
    for ailleurs in (r"D:\Forge\jeu\sim\engine.py", DOSSIER + r"\..\..\journal.jsonl", DOSSIER + "-autre\\p01.png",
                     r"C:\Users\moi\AppData\LocalLow\Victoria Project\Victoria CityLab\Player.log", ""):
        assert "ton dossier de passage" in _garde("Read", file_path=ailleurs)


def test_les_autres_outils_sont_refuses_sauf_celui_qui_rend_son_recit():
    for outil in ("Bash", "Grep", "Glob", "Write", "Edit", "WebFetch", "Agent"):
        assert _garde(outil, command="ls", pattern="x")
    assert _garde("StructuredOutput") == ""


def test_la_garde_refuse_un_appel_illisible(monkeypatch, capsys):
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO("pas du json"))
    assert garde_testeur.main([OUTIL, DOSSIER]) == 2 and "illisible" in capsys.readouterr().err
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"tool_name": "PowerShell", "tool_input": {"command": "dir"}})))
    assert garde_testeur.main([OUTIL, DOSSIER]) == 2 and "ta seule commande" in capsys.readouterr().err
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"tool_name": "Read", "tool_input": {"file_path": DOSSIER + "\\p01.png"}})))
    assert garde_testeur.main([OUTIL, DOSSIER]) == 0


def test_l_appel_du_testeur_n_a_que_ses_deux_outils_et_sa_garde(projet):
    appel = agents_mod.Appel(role="testeur", lecture_seule=True, consigne="joue", outils=("Read", "PowerShell"),
                             garde=("garde_testeur.py", OUTIL, DOSSIER), environnement=(("FORGE_TESTEUR_BUILD", "b"),))
    argv = agents_mod.argv(projet.agent("testeur"), appel, reprise=False, windows=True)
    assert argv[argv.index("--allowedTools") + 1] == "Read,PowerShell" and argv[argv.index("--permission-mode") + 1] == "default"
    refuses = argv[argv.index("--disallowedTools") + 1].split(",")
    assert {"Bash", "Edit", "Write", "Grep", "Glob", "WebFetch", "Agent", "Bash(gh:*)"} <= set(refuses)
    crochet = json.loads(argv[argv.index("--settings") + 1])["hooks"]["PreToolUse"][0]
    assert set(crochet["matcher"].split("|")) >= {"PowerShell", "Read", "Bash", "Grep"}
    assert "garde_testeur.py" in crochet["hooks"][0]["command"] and "garde_commandes.py" not in crochet["hooks"][0]["command"]


def test_l_environnement_de_l_appel_arrive_a_l_agent(projet, tmp_path):
    vus = {}

    def executeur(argv, cwd, env, delai, consigne, trace):
        vus.update(env)
        return 0, "", ""

    appel = agents_mod.Appel(role="testeur", lecture_seule=True, consigne="joue",
                             environnement=(("FORGE_TESTEUR_BUILD", "D:\\builds\\palier-1"),))
    agents_mod.invoquer(projet.agent("testeur"), appel, tmp_path, 60, executeur=executeur)
    assert vus["FORGE_TESTEUR_BUILD"] == "D:\\builds\\palier-1" and vus["CLAUDE_CODE_DISABLE_BACKGROUND_TASKS"] == "1"


# ------------------------------------------------------------- le passage
class FauxBureau:
    """L'écran du PC, dicté : libre ou non à chaque regard ; rien ne se lance."""

    outil = Path(OUTIL)
    gestes_max = 60

    def __init__(self, *regards, gestes=22):
        self.regards = list(regards) or [(True, "LIBRE : devant, explorer")]
        self.gestes, self.sondes, self.fermetures = gestes, 0, 0

    def __call__(self, *, build, sortie):
        self.build, self.sortie = build, sortie
        return self

    def environnement(self):
        return {"FORGE_TESTEUR_BUILD": str(self.build), "FORGE_TESTEUR_SORTIE": str(self.sortie)}

    def sonde(self):
        self.sondes += 1
        return self.regards.pop(0) if len(self.regards) > 1 else self.regards[0]

    def fermer(self):
        self.fermetures += 1

    def gestes_joues(self):
        return self.gestes


PHOTOS = {"p01.png": "image", "p02.png": "image", "publication/p01.jpg": "image", "publication/p02.jpg": "image"}


@pytest.fixture
def gh(gh):
    """Le palier 1 a son issue, la #5 ; ses deux lots sont livrés."""
    gh.ajouter_issue(5, PALIER, ("palier",), corps="Je lance le jeu et je choisis un pays.\n\nSes lots : #10, #11\n")
    gh.ajouter_issue(10, "Chaque pays porte son nom", ("lot", "livre", "monde"), corps=FICHE, etat="CLOSED")
    gh.ajouter_issue(11, "L'accueil", ("lot", "livre", "interface", "pc"), corps=FICHE, etat="CLOSED")
    return gh


def _envoye(gh):
    gh.commenter_issue(5, "🤖 pilote : testeur envoyé\n\n" + lots.marque(role="testeur", etat=lots.ENVOYE, build="palier-1",
                                                                       quand=MAINTENANT.isoformat()))


def _passage(projet, gh, depot, tmp_path, agents, bureau=None, **plus):
    (projet.racine / "docs").mkdir(exist_ok=True)
    (projet.racine / "docs" / "VISION.md").write_text("# Vision\nRien ne naît de rien.\n", encoding="utf-8")
    builds = tmp_path / "builds"
    if plus.pop("construit", True):
        (builds / "palier-1").mkdir(parents=True, exist_ok=True)
        (builds / "palier-1" / "Forge.exe").write_text("", encoding="utf-8")
    publies = []

    def publier(depot_, depot_github, fichiers, dossier):
        publies.extend(Path(f).name for f in fichiers)
        return [f"https://raw.githubusercontent.com/{depot_github}/journal/captures/{dossier}/{Path(f).name}" for f in fichiers]

    bureau = bureau or FauxBureau()
    siestes = []
    lignes = testeur.jouer(projet, gh, depot, journal=tmp_path / "journal.jsonl", builds=builds, executeur_agents=agents,
                           bureau_de=bureau, publier=publier, maintenant=lambda: MAINTENANT, dormir=siestes.append,
                           dossier=plus.pop("dossier", tmp_path / "passages"), **plus)
    return lignes, bureau, publies, siestes


def _marques(gh):
    return [m for m in lots.marques(gh.issues_[5]["comments"]) if m.get("role") == "testeur"]


def test_le_testeur_ne_joue_que_si_le_pilote_l_a_envoye(projet, gh, depot, tmp_path):
    """Un passage resté en file sur le PC et parti deux fois ne rejoue pas l'étape."""
    agents = Agents()
    lignes, bureau, _, _ = _passage(projet, gh, depot, tmp_path, agents)
    assert lignes == ["RIEN — l'étape n'attend pas le testeur (aucun envoi)"]
    assert agents.appels == [] and gh.gestes == [] and bureau.sondes == 0


def test_le_testeur_joue_le_build_fige_et_pose_son_rapport_prouve_sur_l_issue(projet, gh, depot, tmp_path):
    _envoye(gh)
    agents = Agents({"sortie": _recit(), "fichiers": PHOTOS})
    lignes, bureau, publies, _ = _passage(projet, gh, depot, tmp_path, agents)
    pose = gh.issues_[5]["comments"][-1]["body"]
    for attendu in ("# Le testeur a joué le palier 1 — La première guerre", "22 gestes, 2 photos",
                    "**Verdict : PROMESSE TENUE**", "1. **Choisir un pays** — du premier coup ([p01](https://raw.githubusercontent.com/",
                    "## Ce que l'écran n'explique pas\n- Rien ne dit que seule Biskra est bâtie. ([p02](",
                    "## À corriger d'abord\n1. La France n'a pas de ville.", "<details><summary>Ses 2 photos</summary>",
                    "testeur-palier-1-1000-p01.jpg)", "<sub>Joué par le testeur (claude/opus@high).</sub>"):
        assert attendu in pose
    assert publies == ["testeur-palier-1-1000-p01.jpg", "testeur-palier-1-1000-p02.jpg"], "les copies légères, pas les PNG"
    marque = _marques(gh)[-1]
    assert (marque["etat"], marque["verdict"], marque["build"], marque["gestes"]) == ("joue", "TENUE", "palier-1", 22)
    assert marque["machine"] == "pc" and marque["mesure"]["cout"] == 0.5 and marque["a_corriger"] == ["La France n'a pas de ville."]
    assert lignes[-1] == "#5 testeur [claude/opus@high] — palier 1 : PROMESSE TENUE, 22 gestes" and bureau.fermetures == 1


def test_le_testeur_joue_hors_du_depot_avec_la_promesse_la_vision_et_les_reperes_et_rien_d_autre(projet, gh, depot, tmp_path):
    _envoye(gh)
    agents = Agents({"sortie": _recit(), "fichiers": PHOTOS})
    _passage(projet, gh, depot, tmp_path, agents, dossier=None)
    appel = agents.appels[0]
    passage = appel["cwd"]
    assert passage.parent == Path.home() / ".atelier" / "testeur", "sous le dossier personnel, jamais dans le dépôt"
    assert (passage / "vision.md").read_text(encoding="utf-8").startswith("# Vision")
    assert "Qui tient quoi en 1400" in (passage / "reperes-1400.md").read_text(encoding="utf-8")
    consigne, argv = appel["consigne"], appel["argv"]
    for attendu in ("Je lance le jeu et je choisis un pays.", "- « L'accueil » : Je choisis un pays et je clique « Commencer ».",
                    f'& "{OUTIL}" -Action gestes -Gestes', str(passage), "**5 essais sans trouver**", "tes 60 gestes",
                    "Tu as 30 minutes"):
        assert attendu in consigne
    assert "émirat du Zab" not in consigne and "puissances-1400.json" not in consigne, "ni le chemin, ni le code"
    assert appel["modele"] == "opus" and argv[argv.index("--allowedTools") + 1] == "Read,PowerShell"
    assert '"verdict"' in argv[argv.index("--json-schema") + 1]
    assert appel["env"]["FORGE_TESTEUR_BUILD"] == str(tmp_path / "builds" / "palier-1")
    assert appel["env"]["FORGE_TESTEUR_SORTIE"] == str(passage)
    crochet = json.loads(argv[argv.index("--settings") + 1])["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    assert "garde_testeur.py" in crochet and str(passage) in crochet


def test_un_tenue_dement_par_son_recit_est_pose_non_tenue(projet, gh, depot, tmp_path):
    _envoye(gh)
    complaisant = _recit("TENUE", [_objectif(), _objectif("bloque", 5, ("p02",), "Entrer dans la ville")])
    _passage(projet, gh, depot, tmp_path, Agents({"sortie": complaisant, "fichiers": PHOTOS}))
    marque = _marques(gh)[-1]
    assert (marque["verdict"], marque["dit"]) == ("NON_TENUE", "TENUE")
    pose = gh.issues_[5]["comments"][-1]["body"]
    assert "**Verdict : NON TENUE** (il disait « PROMESSE TENUE » ; durci par la chaîne : « Entrer dans la ville » est bloqué)" in pose
    assert "2. **Entrer dans la ville** — **bloqué** après 5 essais" in pose


def test_tant_que_le_proprietaire_est_au_clavier_rien_ne_se_lance_et_le_testeur_attend(projet, gh, depot, tmp_path):
    """Le défaut : un script qui cliquait sans regarder a photographié la fenêtre du propriétaire et y a cliqué."""
    _envoye(gh)
    agents = Agents()
    occupe = FauxBureau((False, "OCCUPE : le proprietaire est au clavier (derniere entree il y a 12 s ; il en faut 600)"))
    lignes, bureau, _, siestes = _passage(projet, gh, depot, tmp_path, agents, occupe, attente=90)
    assert agents.appels == [] and bureau.fermetures == 0, "aucun agent, aucun jeu"
    assert siestes == [testeur.PAS_DU_BUREAU] * 3 and bureau.sondes == 4, "il regarde le bureau jusqu'au bout de son attente"
    marque = _marques(gh)[-1]
    assert marque["etat"] == lots.ATTENTE and "au clavier" in marque["raison"]
    pose = gh.issues_[5]["comments"][-1]["body"]
    assert "il attend pour jouer" in pose and "`D:\\Forge\\builds\\palier-1\\Jouer.cmd`" in pose and "sans l'attendre" in pose
    assert not list((tmp_path / "passages").glob("*")), "rien n'est préparé tant que l'écran n'est pas libre"


def test_le_testeur_part_a_la_premiere_pause_du_proprietaire(projet, gh, depot, tmp_path):
    _envoye(gh)
    bureau = FauxBureau((False, "OCCUPE : le proprietaire est au clavier"), (False, "OCCUPE : le proprietaire est au clavier"),
                        (True, "LIBRE : devant, explorer"))
    agents = Agents({"sortie": _recit(), "fichiers": PHOTOS})
    _, _, _, siestes = _passage(projet, gh, depot, tmp_path, agents, bureau)
    assert len(siestes) == 2 and len(agents.appels) == 1 and _marques(gh)[-1]["etat"] == "joue"


def test_sans_build_sur_le_pc_le_testeur_attend(projet, gh, depot, tmp_path):
    _envoye(gh)
    agents = Agents()
    _, bureau, _, _ = _passage(projet, gh, depot, tmp_path, agents, construit=False)
    assert agents.appels == [] and bureau.sondes == 0
    assert _marques(gh)[-1]["etat"] == lots.ATTENTE and "n'est pas sur le PC" in _marques(gh)[-1]["raison"]


def test_interrompu_par_le_proprietaire_le_testeur_ferme_le_jeu_et_attend(projet, gh, depot, tmp_path):
    _envoye(gh)
    rendu = _recit("INTERROMPU", [_objectif("non_joue", 0, ())], interruption="ARRET : le proprietaire a repris la main")
    _, bureau, publies, _ = _passage(projet, gh, depot, tmp_path, Agents({"sortie": rendu, "fichiers": PHOTOS}),
                                     FauxBureau(gestes=7))
    marque = _marques(gh)[-1]
    assert marque["etat"] == lots.ATTENTE and "après 7 gestes" in marque["raison"] and "repris la main" in marque["raison"]
    assert marque["mesure"]["cout"] == 0.5, "ce que le passage interrompu a coûté se relève"
    assert bureau.fermetures == 1 and publies == [] and not [m for m in _marques(gh) if m["etat"] == "joue"]


@pytest.mark.parametrize("reponse, etat, raison", [
    ({"sortie": _recit()}, lots.ECHEC, "aucune photo ne montre « Choisir un pays »"),
    ({"texte": "Tout va bien.", "fichiers": PHOTOS}, lots.ECHEC, "il n'a rendu aucun récit"),
    ({"coupe": True, "fichiers": PHOTOS}, lots.COUPE, "coupé par son délai"),
    ({"code": 1, "brut": "", "erreur": "panne"}, lots.ECHEC, "code 1")],
    ids=["un récit sans photo", "un texte libre", "coupé par son délai", "en panne"])
def test_un_passage_qui_ne_prouve_rien_ne_rend_pas_de_verdict_et_ferme_le_jeu(projet, gh, depot, tmp_path, reponse, etat, raison):
    _envoye(gh)
    _, bureau, publies, _ = _passage(projet, gh, depot, tmp_path, Agents(reponse))
    marque = _marques(gh)[-1]
    assert marque["etat"] == etat and raison in marque["raison"] and "verdict" not in marque
    assert "sans rendre un récit prouvé" in gh.issues_[5]["comments"][-1]["body"]
    assert bureau.fermetures == 1 and publies == []


def test_quand_le_quota_manque_le_testeur_attend(projet, gh, depot, tmp_path):
    _envoye(gh)
    _, bureau, _, _ = _passage(projet, gh, depot, tmp_path, Agents({"code": 1, "brut": "", "erreur": "You've hit your 5-hour limit"}))
    assert _marques(gh)[-1]["etat"] == lots.ATTENTE and "quota épuisé" in _marques(gh)[-1]["raison"] and bureau.fermetures == 1


def test_a_la_main_le_testeur_joue_un_palier_ferme_sans_rien_publier(projet, gh, depot, tmp_path):
    gh.issues_[5]["state"] = "CLOSED"
    agents = Agents({"sortie": _recit(), "fichiers": PHOTOS})
    lignes, _, publies, _ = _passage(projet, gh, depot, tmp_path, agents, palier=1, force=True, publication=False)
    assert gh.gestes == [] and publies == [], "rien ne part sur GitHub"
    rendu = "\n".join(lignes)
    assert "# Le testeur a joué le palier 1" in rendu and "**Verdict : PROMESSE TENUE**" in rendu
    assert f"Ses photos : {agents.appels[0]['cwd']}" in rendu and str(agents.appels[0]["cwd"] / "p01.png") in rendu


def test_le_testeur_d_une_correction_rejoue_aussi_l_etape_qu_elle_corrige(projet, gh, depot, tmp_path):
    gh.ajouter_issue(3, "Palier 0 — On s'y retrouve", ("palier",), corps="Je trouve ma ville seul.\n\nSes lots : #1", etat="CLOSED")
    gh.issues_[5]["body"] += "\n" + lots.marque(role="pilote", etat="ouvert", par="testeur", verdict="NON_TENUE", corrige=3, refus=1)
    _envoye(gh)
    agents = Agents({"sortie": _recit(), "fichiers": PHOTOS})
    _passage(projet, gh, depot, tmp_path, agents)
    assert "ELLE CORRIGE L'ÉTAPE « On s'y retrouve », QUI RESTE À TENIR :\nJe trouve ma ville seul." in agents.appels[0]["consigne"]
    assert "atelier {" not in agents.appels[0]["consigne"], "la marque du pilote n'est pas une promesse"


def test_un_passage_qui_n_a_pas_pu_partir_repond_par_une_attente(gh):
    assert testeur.repondre_au_silence(gh, raison="la session du propriétaire est fermée").startswith("RIEN")
    _envoye(gh)
    assert testeur.repondre_au_silence(gh, raison="la session du propriétaire est fermée") == "attente marquée sur l'issue #5"
    marque = _marques(gh)[-1]
    assert marque["etat"] == lots.ATTENTE and marque["raison"] == "la session du propriétaire est fermée"
    assert testeur.repondre_au_silence(gh, raison="encore").startswith("RIEN"), "une réponse déjà écrite se garde"


def test_le_schema_du_testeur_exige_un_recit_par_objectif_avec_ses_photos():
    schema = consignes.SCHEMA_TESTEUR
    assert set(schema["required"]) == {"verdict", "resume", "objectifs", "non_explique", "defauts", "a_corriger_d_abord"}
    assert {"essais", "photos", "resultat", "recit"} <= set(schema["properties"]["objectifs"]["items"]["required"])
    assert schema["properties"]["verdict"]["enum"] == ["TENUE", "TENUE_AVEC_PEINE", "NON_TENUE", "INTERROMPU"]


def test_ce_qu_un_testeur_interrompu_avait_trouve_ne_se_perd_pas_sans_faire_un_verdict(projet, gh, depot, tmp_path):
    """Le défaut : 41 gestes joués, puis une interruption, et le récit entier était jeté."""
    _envoye(gh)
    rendu = _recit("INTERROMPU", [_objectif(), _objectif("non_joue", 0, (), "Entrer dans la ville")],
                   interruption="ARRET : le proprietaire a repris la main")
    _passage(projet, gh, depot, tmp_path, Agents({"sortie": rendu, "fichiers": PHOTOS}), FauxBureau(gestes=41))
    pose = gh.issues_[5]["comments"][-1]["body"]
    assert "<details><summary>Ce qu'il avait trouvé avant de s'arrêter (41 gestes ; ce n'est pas un verdict)</summary>" in pose
    assert "1. **Choisir un pays** — du premier coup" in pose and "## À corriger d'abord\n1. La France n'a pas de ville." in pose
    assert pose.rstrip().endswith("-->") and _marques(gh)[-1]["etat"] == lots.ATTENTE and "verdict" not in _marques(gh)[-1]


# ------------------------------------------------------- le PC et son écran
RACINE = Path(__file__).resolve().parents[2]


def test_le_pilote_envoie_un_workflow_qui_existe_et_que_seul_il_lance():
    from atelier import palier
    texte = (RACINE / ".github" / "workflows" / palier.WORKFLOW_DU_TESTEUR).read_text(encoding="utf-8")
    declencheurs = texte.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
    assert "workflow_dispatch:" in declencheurs
    assert "pull_request" not in declencheurs and "push" not in declencheurs and "schedule" not in declencheurs, \
        "le dépôt est public : une fourche ne lance rien sur le PC"
    assert "runs-on: [self-hosted, Windows, unity]" in texte and "contents: read" in texte
    assert "group: testeur-pc" in texte and "cancel-in-progress: false" in texte, "un seul écran : un testeur à la fois"


def test_le_runner_ne_joue_pas_lui_meme_il_demarre_la_tache_de_la_session_ouverte():
    """Le défaut : une session de la chaîne sur le PC n'a pas de bureau, et le jeu y reste bloqué au démarrage."""
    texte = (RACINE / ".github" / "workflows" / "testeur-pc.yml").read_text(encoding="utf-8")
    installeur = (RACINE / "pc" / "installer_testeur.ps1").read_text(encoding="utf-8")
    lanceur = (RACINE / "pc" / "Testeur.cmd").read_text(encoding="utf-8")
    assert "Start-ScheduledTask -TaskName ForgeTesteur" in texte and '$nom = "ForgeTesteur"' in installeur
    assert "Forge.exe" not in texte and "jouer_le_build" not in texte, "le service n'ouvre jamais le jeu"
    assert "-LogonType Interactive" in installeur and "-RunLevel Limited" in installeur, "la session ouverte, sans élévation"
    assert r"D:\Forge\.atelier\pilote-testeur\pc\Testeur.cmd" in installeur and "pilote-testeur" in texte
    assert "conhost.exe" in installeur and "--headless" in installeur, "aucune fenêtre de console sur son bureau"
    assert '-m atelier --projet "%ici%.." testeur %arguments%' in lanceur
    # Deux défauts payés : appelé d'un autre dossier, le lanceur jouait le code de ce dossier-là ; et
    # « echo 4> fichier » redirigeait le canal 4 au lieu d'écrire le code du passage.
    assert lanceur.index('cd /d "%ici%.."') < lanceur.index("py -m atelier")
    assert r'>"%passage%\passage.code" echo %ERRORLEVEL%' in lanceur and "echo %ERRORLEVEL%>" not in lanceur
    for silence in ("SANS_TACHE", "SANS_SESSION", "SANS_FIN"):
        assert f"Attendre $env:{silence}" in texte, "sans passage, l'envoi du pilote reçoit quand même sa réponse"
    assert "testeur --attente $raison" in texte and "testeur --attente $env:RAISON" in texte


def test_la_demande_du_runner_est_un_mot_jamais_une_commande():
    texte = (RACINE / ".github" / "workflows" / "testeur-pc.yml").read_text(encoding="utf-8")
    lanceur = (RACINE / "pc" / "Testeur.cmd").read_text(encoding="utf-8")
    assert "$mode = if ($env:SONDE -eq 'oui') { 'sonde' } else { 'jouer' }" in texte
    assert "${{ inputs" not in texte.split("run: |", 1)[1].split("repondre:", 1)[0], "une entrée ne s'écrit jamais dans le script"
    assert 'if /i "%mode%"=="sonde" set "arguments=--sonde"' in lanceur


def test_l_outil_de_jeu_garde_le_proprietaire_avant_tout_geste():
    """Ce que le script promet au propriétaire, relu dans son texte : il ne tourne que sur le PC."""
    outil = testeur.OUTIL.read_text(encoding="utf-8")
    assert outil.isascii(), "PowerShell 5.1 lit ce fichier en ANSI : un accent y casserait une chaîne"
    for garde in ('"la session Windows est verrouillee"', '"un Forge.exe tourne deja sur ce bureau"',
                  "occupe tout l'ecran", "le proprietaire est au clavier", "le proprietaire a repris la main",
                  "FORGE_TESTEUR_INACTIVITE", "FORGE_TESTEUR_GESTES_MAX"):
        assert garde in outil, garde
    assert outil.index("if (Reprise-Par-Le-Proprietaire)") < outil.index('"clic" { Point'), "la garde passe avant le geste"
    assert "$Build = $env:FORGE_TESTEUR_BUILD" in outil and "$Sortie = $env:FORGE_TESTEUR_SORTIE" in outil
    assert testeur.GARDE.is_file() and testeur.REPERES.is_file()
