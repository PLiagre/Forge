"""Appeler un agent : son argv, son environnement, sa session, sa mesure, et
la garde de ses commandes.

Aucun vrai agent n'est appelé : l'exécuteur est une doublure, sauf pour
`executer`, qui lance un petit script Python écrit dans le dossier du test.
"""

from __future__ import annotations

from contextlib import contextmanager
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import textwrap
import time

import pytest

from atelier import agents, garde_commandes
from atelier.agents import Appel, Introuvable
from atelier.projet import Agent

from conftest import flux

OPUS = Agent("claude", "opus", "high")
CONSIGNE = "Lis la fiche du lot #10 et rends ton plan."
SUITE = "ÉTAPE 2 SUR 2 : les données."
SESSION = "6f1c2f0e-5c62-5b8e-9d0a-3f2b1c4d5e6f"


def appel(**plus) -> Appel:
    return Appel(**({"role": "chef", "consigne": CONSIGNE, "lecture_seule": False} | plus))


def option(argv, nom):
    """La valeur qui suit cette option dans l'argv."""
    return argv[argv.index(nom) + 1]


class Executeur:
    """Un faux exécuteur : il rend les réponses dictées et garde ce qu'il a reçu."""

    def __init__(self, *reponses):
        self.reponses = list(reponses)
        self.appels: list[dict] = []

    def __call__(self, argv, cwd, env, delai, consigne, trace):
        self.appels.append({"argv": argv, "cwd": cwd, "env": env, "delai": delai, "consigne": consigne, "trace": trace})
        return self.reponses.pop(0)


# ------------------------------------------------------------- les refus
def test_la_cause_d_un_refus_se_lit_dans_ce_que_l_outil_dit_en_dernier():
    assert agents.cause_de_refus(1, "You've hit your 5-hour limit · resets 9:30pm") == "quota"
    assert agents.cause_de_refus(1, "Invalid API key · Please run /login") == "auth"
    assert agents.cause_de_refus(1, "error: unknown option '--effort'") == "appel"
    assert agents.cause_de_refus(127, "") == "installation" and agents.cause_de_refus(126, "") == "installation"


def test_ni_un_appel_reussi_ni_un_vrai_echec_ne_sont_des_refus():
    assert agents.cause_de_refus(0, "rate limit, 401, oauth") is None
    assert agents.cause_de_refus(1, "AssertionError: 3 != 4") is None
    # Seule la fin compte : un long travail peut citer le quota sans que ce soit un refus.
    travail = "Je lis la règle du quota de grain.\n" + "\n".join(f"ligne {i}" for i in range(30)) + "\nLe test échoue."
    assert agents.cause_de_refus(1, travail) is None
    assert agents.cause_de_refus(1, travail + "\nAPI Error: rate limit exceeded") == "quota"


def test_la_derniere_ligne_ne_montre_rien_qui_ressemble_a_un_jeton():
    jeton = "sk-ant-" + "A1b2C3d4" * 6
    assert agents.derniere_ligne(f"première ligne\nInvalid key {jeton} refusée\n\n   \n") == "Invalid key … refusée"
    assert agents.derniere_ligne("\n \n") == ""
    assert len(agents.derniere_ligne("mot " * 100)) == 160


# ------------------------------------------------- le lancement sous Windows
SHIM = textwrap.dedent("""\
    @ECHO off
    IF EXIST "%dp0%\\node.exe" (
      SET "_prog=%dp0%\\node.exe"
    ) ELSE (
      SET "_prog=node"
    )
    "%_prog%"  "%dp0%\\node_modules\\@anthropic-ai\\claude-code\\cli.js" %*
    """)


def _shim(dossier: Path, *, avec_script: bool = True) -> tuple[Path, Path]:
    """Le `claude.cmd` que pose npm, et le .js qu'il fait lancer par node."""
    dossier.mkdir(parents=True, exist_ok=True)
    cmd = dossier / "claude.cmd"
    cmd.write_text(SHIM, encoding="utf-8")
    script = dossier / "node_modules" / "@anthropic-ai" / "claude-code" / "cli.js"
    if avec_script:
        script.parent.mkdir(parents=True)
        script.write_text("// l'outil", encoding="utf-8")
    return cmd, script


def test_sous_windows_un_exe_se_lance_tel_quel(tmp_path):
    exe = tmp_path / "claude.exe"
    commande, env = agents.lancement(["claude", "-p", "a & b"], {"X": "1"}, windows=True, chercher=lambda nom: str(exe))
    assert commande == [str(exe), "-p", "a & b"] and env == {"X": "1"}


def test_sous_windows_un_shim_npm_devient_node_et_son_script(tmp_path):
    """Le défaut gardé : lancer le `.cmd` ferait passer les arguments par cmd.exe, qui interprète `& | % ^`."""
    cmd, script = _shim(tmp_path)
    chercher = {"claude": str(cmd), "node": str(tmp_path / "ailleurs" / "node.exe")}.get
    commande, _ = agents.lancement(["claude", "-p", "a & b"], {}, windows=True, chercher=chercher)
    assert commande == [str(tmp_path / "ailleurs" / "node.exe"), str(script), "-p", "a & b"]
    (tmp_path / "node.exe").write_bytes(b"")
    commande, _ = agents.lancement(["claude"], {}, windows=True, chercher=chercher)
    assert commande == [str(tmp_path / "node.exe"), str(script)], "le node posé à côté du shim passe d'abord"


def test_sous_windows_ce_qui_n_a_pas_de_lancement_sur_est_introuvable(tmp_path):
    with pytest.raises(Introuvable, match="binaire introuvable : claude"):
        agents.lancement(["claude", "-p"], {}, windows=True, chercher=lambda nom: None)
    with pytest.raises(Introuvable, match="binaire introuvable : claude"):
        agents.lancement(["claude", "-p"], {"PATH": str(tmp_path)}, windows=True)
    # Un `.cmd` qui n'est pas un shim lisible, ou dont le script a disparu, passerait par cmd.exe.
    lot = tmp_path / "outil.cmd"
    lot.write_text("@echo off\nnode autre-chose %*\n", encoding="utf-8")
    with pytest.raises(Introuvable, match="cmd.exe"):
        agents.lancement(["outil"], {}, windows=True, chercher=lambda nom: str(lot))
    orphelin, _ = _shim(tmp_path / "orphelin", avec_script=False)
    with pytest.raises(Introuvable, match="cmd.exe"):
        agents.lancement(["claude"], {}, windows=True, chercher={"claude": str(orphelin), "node": "node.exe"}.get)


def test_hors_de_windows_la_commande_part_telle_quelle():
    def jamais(nom):
        raise AssertionError("hors de Windows, rien n'est cherché")

    commande, env = ["claude", "-p"], {"PATH": "/usr/bin"}
    assert agents.lancement(commande, env, windows=False, chercher=jamais) == (commande, env)


# --------------------------------------------------------- l'environnement
def test_un_agent_ne_recoit_aucune_cle_d_api_ni_le_droit_aux_taches_de_fond(monkeypatch):
    for cle in agents.CLES_API:
        monkeypatch.setenv(cle, "une-cle")
    monkeypatch.setenv("FORGE_TEMOIN", "gardé")
    monkeypatch.setenv("CLAUDE_CODE_DISABLE_BACKGROUND_TASKS", "0")
    env = agents.environnement()
    assert not set(agents.CLES_API) & set(env) and env["FORGE_TEMOIN"] == "gardé"
    assert env["CLAUDE_CODE_DISABLE_BACKGROUND_TASKS"] == "1"


def test_le_jeton_de_l_abonnement_passe_par_l_environnement_jamais_par_l_argv(tmp_path, monkeypatch):
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in agents.environnement(), "sans fichier, pas de jeton"
    fichier = tmp_path / "claude.token"
    fichier.write_text("  jeton-du-test-0123\n", encoding="utf-8")
    monkeypatch.setattr(agents, "FICHIER_JETON_CLAUDE", fichier)
    executeur = Executeur((0, flux(texte="fait"), ""))
    agents.invoquer(OPUS, appel(session=SESSION), tmp_path, 900, executeur=executeur)
    [recu] = executeur.appels
    assert recu["env"]["CLAUDE_CODE_OAUTH_TOKEN"] == "jeton-du-test-0123"
    assert not any("jeton-du-test-0123" in morceau for morceau in recu["argv"])


# ------------------------------------------------------------------ l'argv
def test_la_consigne_n_est_jamais_dans_l_argv():
    for demande in (appel(), appel(lecture_seule=True), appel(sans_outil=True), appel(suite=SUITE, session=SESSION)):
        for reprise in (False, True):
            argv = agents.argv(OPUS, demande, reprise=reprise)
            assert argv[:4] == ["claude", "-p", "--model", "opus"] and option(argv, "--effort") == "high"
            assert not any(CONSIGNE in morceau or SUITE in morceau for morceau in argv)


def test_une_session_neuve_s_ouvre_par_son_nom_et_une_session_reprise_se_reprend():
    neuve = agents.argv(OPUS, appel(session=SESSION), reprise=False)
    reprise = agents.argv(OPUS, appel(session=SESSION), reprise=True)
    assert option(neuve, "--session-id") == SESSION and "--resume" not in neuve
    assert option(reprise, "--resume") == SESSION and "--session-id" not in reprise
    anonyme = agents.argv(OPUS, appel(), reprise=True)
    assert "--resume" not in anonyme and "--session-id" not in anonyme


def test_le_schema_et_les_sous_agents_passent_en_json():
    schema = {"type": "object", "properties": {"décision": {"type": "string"}}, "required": ["décision"]}
    sous_agents = {"developpeur": {"description": "Les tâches bornées.", "model": "sonnet"}}
    argv = agents.argv(OPUS, appel(schema=schema, sous_agents=sous_agents), reprise=False)
    assert json.loads(option(argv, "--json-schema")) == schema
    assert json.loads(option(argv, "--agents")) == sous_agents
    nu = agents.argv(OPUS, appel(), reprise=False)
    assert "--json-schema" not in nu and "--agents" not in nu


def test_un_role_en_lecture_seule_ne_peut_ni_ecrire_ni_confier_ni_faire_les_gestes_du_pilote():
    argv = agents.argv(OPUS, appel(lecture_seule=True, sous_agents={"developpeur": {}}), reprise=False, windows=True)
    permis, interdits = option(argv, "--allowedTools").split(","), option(argv, "--disallowedTools").split(",")
    assert option(argv, "--permission-mode") == "default"
    assert "Read" in permis and not {"Edit", "Write", "Agent", "Bash", "PowerShell"} & set(permis)
    assert {"Edit", "Write", "NotebookEdit", "Agent", *agents.GESTES_DU_PILOTE} <= set(interdits)


def test_un_role_qui_ecrit_edite_sans_faire_les_gestes_du_pilote():
    argv = agents.argv(OPUS, appel(), reprise=False, windows=False)
    assert option(argv, "--permission-mode") == "acceptEdits"
    assert option(argv, "--allowedTools") == "Read,Glob,Grep,Edit,Write,Bash"
    assert option(argv, "--disallowedTools").split(",") == list(agents.GESTES_DU_PILOTE)
    assert "Bash(git push:*)" in agents.GESTES_DU_PILOTE and "Bash(gh:*)" in agents.GESTES_DU_PILOTE
    # L'outil Agent exige des sous-agents, PowerShell exige Windows.
    confie = agents.argv(OPUS, appel(sous_agents={"developpeur": {}}), reprise=False, windows=False)
    seul = agents.argv(OPUS, appel(), reprise=False, windows=True)
    assert option(confie, "--allowedTools").split(",")[-1] == "Agent" and "PowerShell" not in option(confie, "--allowedTools")
    assert option(seul, "--allowedTools").split(",")[-1] == "PowerShell" and "Agent" not in option(seul, "--allowedTools")


def test_un_appel_sans_outil_n_a_ni_outil_ni_reglage():
    argv = agents.argv(OPUS, appel(sans_outil=True, session=SESSION), reprise=False)
    assert argv[-2:] == ["--tools", ""]
    assert not {"--settings", "--allowedTools", "--permission-mode"} & set(argv)


def test_les_reglages_portent_la_garde_des_commandes_et_sa_borne():
    for demande in (appel(jours_max=30), appel(jours_max=30, lecture_seule=True)):
        crochet = json.loads(option(agents.argv(OPUS, demande, reprise=False), "--settings"))["hooks"]["PreToolUse"][0]
        assert crochet["matcher"] == "Bash|PowerShell"
        assert crochet["hooks"] == [{"type": "command", "command": f'"{sys.executable}" "{agents.GARDE}" 30'}]
    assert agents.GARDE.is_file() and agents.GARDE.name == "garde_commandes.py"


# ------------------------------------------------------- lire la sortie en flux
def test_un_appel_fini_rend_son_texte_sa_sortie_et_sa_mesure():
    modeles = {"claude-opus-5-5": {"inputTokens": 10, "outputTokens": 200, "cacheReadInputTokens": 3000,
                                   "cacheCreationInputTokens": 400, "costUSD": 0.4},
               "claude-sonnet-5-5": {"inputTokens": 5, "outputTokens": 50, "costUSD": 0.1}}
    lu = agents.lire_flux(flux(texte="C'est fait.", sortie={"etat": "faite"}, cout=0.5, session="s-7", modeles=modeles,
                               cinq_heures=0.3, semaine=0.1))
    assert (lu.fini, lu.texte, lu.sortie, lu.session) == (True, "C'est fait.", {"etat": "faite"}, "s-7")
    assert lu.mesure == {
        "limites": {"cinq_heures": 0.3, "semaine": 0.1}, "cout": 0.5, "tours": 4, "duree": 90,
        "modeles": {"claude-opus-5-5": {"entree": 10, "sortie": 200, "cache_lu": 3000, "cache_ecrit": 400, "cout": 0.4},
                    "claude-sonnet-5-5": {"entree": 5, "sortie": 50, "cache_lu": 0, "cache_ecrit": 0, "cout": 0.1}}}


def _message(identifiant, texte, *, modele="claude-opus-5-5", sortie=100, parent=None) -> str:
    """Un message de l'agent dans le flux, avec son usage."""
    evenement = {"type": "assistant", "message": {
        "id": identifiant, "model": modele, "content": [{"type": "text", "text": texte}],
        "usage": {"input_tokens": 10, "output_tokens": sortie, "cache_read_input_tokens": 1000}}}
    if parent:
        evenement["parent_tool_use_id"] = parent
    return json.dumps(evenement, ensure_ascii=False)


def test_un_appel_coupe_garde_ses_jetons_et_ses_derniers_mots():
    """Un même message revient pour chacun de ses blocs, avec le même usage :
    le compter à chaque fois gonflerait la mesure d'un appel coupé."""
    lignes = [json.dumps({"type": "system", "subtype": "init", "session_id": "s-9"}),
              _message("m1", "Je lis la fiche."), _message("m1", "Je lis le code."),
              _message("m2", "J'écris la règle.", sortie=40),
              _message("m3", "Les données sont posées.", modele="claude-sonnet-5-5", sortie=7, parent="toolu_1"),
              _message("m4", "Je joue les tests."), '{"type": "assistant", "mess']
    lu = agents.lire_flux("\n".join(lignes))
    assert not lu.fini and lu.sortie is None and lu.session == "s-9"
    assert lu.texte == "Je lis le code.\nJ'écris la règle.\nJe joue les tests.", "sans les mots du sous-agent"
    assert lu.mesure == {"coupe": True, "modeles": {
        "claude-opus-5-5": {"entree": 30, "sortie": 240, "cache_lu": 3000, "cache_ecrit": 0},
        "claude-sonnet-5-5": {"entree": 10, "sortie": 7, "cache_lu": 1000, "cache_ecrit": 0}}}


def test_une_sortie_vide_ou_illisible_ne_rend_rien_sans_exception():
    illisible = '{cassé\n[1, 2]\n"du texte"\n{"type": "assistant", "message": "pas un objet"}\n{"type": 3}'
    for sortie in ("", "claude: command not found\n", illisible):
        lu = agents.lire_flux(sortie)
        assert (lu.texte, lu.sortie, lu.session, lu.fini) == ("", None, None, False)
        assert not {"cout", "tours", "duree", "modeles", "limites"} & set(lu.mesure)


# ------------------------------------------------------------------ invoquer
def test_un_appel_reussi_rend_son_texte_sa_sortie_sa_session_et_sa_trace(tmp_path):
    executeur = Executeur((0, flux(texte="C'est fait.", sortie={"etat": "faite"}), ""))
    trace = tmp_path / "appels" / "10-chef.jsonl"
    res = agents.invoquer(OPUS, appel(session=SESSION), tmp_path, 900, executeur=executeur, trace=trace)
    assert res.reussi and not res.attente and not res.coupe and res.agent == OPUS
    assert (res.texte, res.sortie, res.session, res.neuve) == ("C'est fait.", {"etat": "faite"}, SESSION, True)
    assert res.mesure["cout"] == 0.5 and res.trace == str(trace)
    [recu] = executeur.appels
    assert (recu["consigne"], recu["cwd"], recu["delai"], recu["trace"]) == (CONSIGNE, tmp_path, 900, trace)


def test_un_quota_epuise_ou_un_outil_absent_font_attendre_sans_echec(tmp_path):
    quota = Executeur((1, "", "You've hit your 5-hour limit · resets 9:30pm"))
    res = agents.invoquer(OPUS, appel(), tmp_path, 900, executeur=quota)
    assert res.attente and res.agent is None and not res.reussi and not res.coupe
    assert res.raison == "claude/opus@high : quota épuisé (« You've hit your 5-hour limit · resets 9:30pm »)"
    absent = agents.invoquer(OPUS, appel(), tmp_path, 900, executeur=Executeur((127, "", "binaire introuvable : claude")))
    assert absent.attente and absent.agent is None and "ne démarre pas" in absent.raison


def test_un_appel_refuse_n_est_pas_mesure_comme_un_appel_coupe(tmp_path):
    res = agents.invoquer(OPUS, appel(), tmp_path, 900, executeur=Executeur((1, "", "You've hit your 5-hour limit")))
    assert res.attente and not res.mesure.get("coupe")


def test_un_appel_coupe_par_son_delai_garde_sa_mesure_et_n_est_pas_une_attente(tmp_path):
    coupe = flux(texte="Je relis la règle du quota de grain.", coupe=True)
    executeur = Executeur((agents.CODE_COUPE, coupe, "délai dépassé après 900 s"))
    res = agents.invoquer(OPUS, appel(session=SESSION, reprendre=True), tmp_path, 900, executeur=executeur)
    assert res.coupe and not res.attente and not res.reussi and res.agent == OPUS and len(executeur.appels) == 1
    assert res.mesure["coupe"] is True and res.mesure["modeles"]["claude-opus-5-5"]["sortie"] == 200
    assert res.mesure["limites"] == {"cinq_heures": 0.2, "semaine": 0.05}
    assert res.raison == "délai dépassé après 900 s" and res.sortie is None and res.session == SESSION
    assert "Je relis la règle du quota de grain." in res.texte


def test_une_session_introuvable_est_rouverte_avec_la_consigne_entiere(tmp_path):
    executeur = Executeur((1, "", f"No conversation found with session ID: {SESSION}"), (0, flux(texte="fait"), ""))
    res = agents.invoquer(OPUS, appel(session=SESSION, reprendre=True, suite=SUITE), tmp_path, 900, executeur=executeur)
    refuse, rouvert = executeur.appels
    assert option(refuse["argv"], "--resume") == SESSION and refuse["consigne"] == SUITE
    assert option(rouvert["argv"], "--session-id") == SESSION and "--resume" not in rouvert["argv"]
    assert rouvert["consigne"] == CONSIGNE
    assert res.reussi and res.neuve and res.session == SESSION


def test_une_session_deja_ouverte_est_reprise_avec_la_suite(tmp_path):
    executeur = Executeur((1, "", f"Error: Session ID {SESSION} is already in use."), (0, flux(texte="fait"), ""))
    res = agents.invoquer(OPUS, appel(session=SESSION, suite=SUITE), tmp_path, 900, executeur=executeur)
    refuse, repris = executeur.appels
    assert option(refuse["argv"], "--session-id") == SESSION and refuse["consigne"] == CONSIGNE
    assert option(repris["argv"], "--resume") == SESSION and "--session-id" not in repris["argv"]
    assert repris["consigne"] == SUITE
    assert res.reussi and not res.neuve


def test_une_session_reprise_recoit_la_suite_et_pas_la_consigne(tmp_path):
    executeur = Executeur((0, flux(texte="fait"), ""), (0, flux(texte="fait"), ""))
    res = agents.invoquer(OPUS, appel(session=SESSION, reprendre=True, suite=SUITE), tmp_path, 900, executeur=executeur)
    assert executeur.appels[0]["consigne"] == SUITE and "--resume" in executeur.appels[0]["argv"] and not res.neuve
    agents.invoquer(OPUS, appel(session=SESSION, reprendre=True), tmp_path, 900, executeur=executeur)
    assert executeur.appels[1]["consigne"] == CONSIGNE, "sans suite, la session reprise reçoit la consigne entière"


def test_un_outil_plein_fait_attendre_sans_lancer_personne(tmp_path):
    demandes = []

    @contextmanager
    def place(outil, libre=False):
        demandes.append(outil)
        yield libre

    executeur = Executeur((0, flux(texte="fait"), ""))
    res = agents.invoquer(OPUS, appel(), tmp_path, 900, executeur=executeur, place=place)
    assert res.attente and res.agent is None and "occupé" in res.raison
    assert demandes == ["claude"] and not executeur.appels
    assert agents.invoquer(OPUS, appel(), tmp_path, 900, executeur=executeur,
                           place=lambda outil: place(outil, libre=True)).reussi


def test_une_erreur_dite_dans_le_flux_est_un_echec_meme_avec_le_code_zero(tmp_path):
    dit = flux(texte="La sortie ne respecte pas le schéma.", sortie={"etat": "faite"}, erreur=True)
    res = agents.invoquer(OPUS, appel(), tmp_path, 900, executeur=Executeur((0, dit, "")))
    assert not res.reussi and not res.attente and res.code == 1 and res.agent == OPUS
    assert res.sortie is None and "La sortie ne respecte pas le schéma." in res.texte
    quota = flux(texte="You've hit your weekly limit · resets Monday", erreur=True)
    res = agents.invoquer(OPUS, appel(), tmp_path, 900, executeur=Executeur((0, quota, "")))
    assert res.attente and res.agent is None and "quota épuisé" in res.raison, "un quota dit dans le flux fait attendre"


# ------------------------------------------------------- exécuter pour de vrai
ECHO = """
    import sys
    consigne = sys.stdin.buffer.read()
    open("fait.txt", "wb").write(consigne)
    sys.stdout.buffer.write(b"recu : " + consigne)
"""
DORMEUR = """
    import sys, time
    sys.stdin.read()
    print("debut du travail", flush=True)
    time.sleep(30)
    print("jamais dit", flush=True)
"""


def _agent(dossier: Path, corps: str) -> list[str]:
    """Un « agent » : un script Python du dossier du test, lancé par l'interpréteur des tests."""
    script = dossier / "agent.py"
    script.write_text(textwrap.dedent(corps), encoding="utf-8")
    return [sys.executable, str(script)]


def test_l_agent_lit_sa_consigne_sur_l_entree_standard_et_sa_sortie_reste_dans_la_trace(tmp_path):
    chantier, trace = tmp_path / "chantier", tmp_path / "appels" / "10-chef.jsonl"
    chantier.mkdir()
    consigne = "Lève une armée à Biskra — été 1400."
    code, sortie, erreur = agents.executer(_agent(tmp_path, ECHO), chantier, dict(os.environ), 30, consigne, trace)
    assert (code, sortie, erreur) == (0, f"recu : {consigne}", "")
    assert trace.read_text(encoding="utf-8") == sortie and not trace.with_suffix(".err").exists()
    assert (chantier / "fait.txt").read_text(encoding="utf-8") == consigne, "l'agent tourne dans le dossier du lot"


def test_un_agent_plus_lent_que_son_delai_est_coupe_et_garde_ce_qu_il_avait_dit(tmp_path):
    """Le défaut : un appel coupé par son délai ne laissait ni sortie ni trace."""
    trace = tmp_path / "appels" / "10-chef.jsonl"
    debut = time.monotonic()
    code, sortie, erreur = agents.executer(_agent(tmp_path, DORMEUR), tmp_path, dict(os.environ), 2, "Dors.", trace)
    assert (code, erreur) == (agents.CODE_COUPE, "délai dépassé après 2 s")
    assert "debut du travail" in sortie and "jamais dit" not in sortie
    assert "debut du travail" in trace.read_text(encoding="utf-8")
    assert time.monotonic() - debut < 20, "l'agent coupé est tué : on n'attend pas la fin de son sommeil"


def test_un_binaire_absent_rend_127_sans_exception(tmp_path):
    commande = ["agent-de-forge-qui-n-existe-pas", "-p"]
    code, sortie, erreur = agents.executer(commande, tmp_path, dict(os.environ), 5, "Fais.", tmp_path / "trace.jsonl")
    assert (code, sortie) == (127, "") and "binaire introuvable : agent-de-forge-qui-n-existe-pas" in erreur


# ------------------------------------------------------ la garde des commandes
def test_la_suite_entiere_est_refusee_sous_toutes_ses_formes_un_lancement_borne_passe():
    for commande in ("python3 -m pytest jeu -q", "py -m pytest", "pytest", "python3 -m pytest -x --tb=short jeu/sim",
                     "cd jeu && py -m pytest sim/tests/ -q -n auto"):
        assert "la suite entière" in garde_commandes.refus(commande, 400), commande
    for commande in ("python3 -m pytest jeu/sim/tests/test_lieux.py -q", "py -m pytest jeu -q -k ouverture",
                     "pytest jeu/sim/tests/lieux.py::test_ouverture", "python3 -m pytest atelier/tests -q",
                     "py -m pytest atelier\\tests -q"):
        assert garde_commandes.refus(commande, 400) == "", commande


def test_une_simulation_plus_longue_que_la_borne_est_refusee():
    assert "3650 jours" in garde_commandes.refus("python3 -m forge --ticks 3650 --seed 0", 400)
    assert garde_commandes.refus("py -m forge --jours=401", 400) and garde_commandes.refus("py -m forge --days 500", 400)
    assert garde_commandes.refus("python3 -m forge --ticks 400 --seed 0", 400) == ""
    assert "(30 au plus)" in garde_commandes.refus("python3 -m forge --ticks 365", 30)


def test_une_commande_sans_rapport_passe():
    for commande in ("git log --oneline -5", "ls jeu/sim/tests", "python3 -m forge --seed 3650", ""):
        assert garde_commandes.refus(commande, 400) == "", commande


def test_citer_pytest_sans_le_lancer_n_est_pas_jouer_la_suite():
    assert garde_commandes.refus('grep -rn "pytest" docs/', 400) == ""
    assert garde_commandes.refus("cat pytest.ini", 400) == ""


def _entree_standard(monkeypatch, texte: str) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(texte))


def test_la_garde_sort_2_et_dit_pourquoi_quand_elle_refuse(monkeypatch, capsys):
    suite = json.dumps({"tool_name": "Bash", "tool_input": {"command": "python3 -m pytest jeu -q"}})
    _entree_standard(monkeypatch, suite)
    assert garde_commandes.main(["400"]) == 2
    assert capsys.readouterr().err.startswith("Commande refusée par la chaîne : la suite entière")
    annee = json.dumps({"tool_name": "PowerShell", "tool_input": {"command": "py -m forge --ticks 365"}})
    _entree_standard(monkeypatch, annee)
    assert garde_commandes.main(["30"]) == 2, "la borne vient de l'argument"
    _entree_standard(monkeypatch, annee)
    assert garde_commandes.main([]) == 0, "sans argument, 400 jours"


def test_la_garde_laisse_passer_ce_qu_elle_ne_refuse_pas_ou_ne_sait_pas_lire(monkeypatch, capsys):
    lisibles = [{"tool_input": {"command": "git status"}}, {"tool_input": {}}, {"tool_name": "Read"}, ["pas", "un", "objet"]]
    for entree in (*(json.dumps(e) for e in lisibles), "pytest jeu : pas du JSON", ""):
        _entree_standard(monkeypatch, entree)
        assert garde_commandes.main(["400"]) == 0, entree
    assert capsys.readouterr().err == ""


# ------------------------------------------------------------------ la sonde
@pytest.fixture
def dossier_jetable_du_test(tmp_path, monkeypatch):
    """La sonde ouvre son dossier jetable sous le dossier du test, pas dans le vrai dossier temporaire."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    return tmp_path


def test_la_sonde_d_un_role_en_lecture_seule_attend_le_mot_ok(dossier_jetable_du_test):
    executeur = Executeur((0, flux(texte="OK"), ""), (0, flux(texte="Bonjour."), ""),
                          (1, "", "Invalid API key · Please run /login"))
    assert agents.sonder(OPUS, "relecteur", True, executeur=executeur) == (True, "OK")
    assert option(executeur.appels[0]["argv"], "--permission-mode") == "default"
    assert dossier_jetable_du_test in executeur.appels[0]["cwd"].parents
    assert agents.sonder(OPUS, "relecteur", True, executeur=executeur) == (False, "Bonjour.")
    reussi, detail = agents.sonder(OPUS, "relecteur", True, executeur=executeur)
    assert not reussi and "session de l'abonnement expirée" in detail


def test_la_sonde_d_un_role_qui_ecrit_exige_le_fichier_qu_il_devait_creer(dossier_jetable_du_test):
    def ecrivain(argv, cwd, env, delai, consigne, trace):
        assert agents.FICHIER_SONDE in consigne and option(argv, "--permission-mode") == "acceptEdits"
        (Path(cwd) / agents.FICHIER_SONDE).write_text("OK\n", encoding="utf-8")
        return 0, flux(texte="OK"), ""

    assert agents.sonder(OPUS, "chef", False, executeur=ecrivain) == (True, "OK")
    assert not list(dossier_jetable_du_test.glob("sonde-*")), "le dossier jetable est retiré"
    bavard = Executeur((0, flux(texte="OK"), ""))
    assert agents.sonder(OPUS, "chef", False, executeur=bavard) == (False, "a répondu sans rien écrire : OK")
