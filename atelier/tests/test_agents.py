"""Les rôles, et comment on appelle un agent : la ligne de commande exacte,
les clés retirées, le secours sur quota, qui code et qui relit."""

from __future__ import annotations

import json

import pytest

from atelier import agents as A
from atelier.projet import OUTILS, ROLES, Agent, ProjetIncomplet, charger, lire_agent, lire_poste, table_des_roles

from conftest import RACINE, Agents


def test_le_branchement_du_depot_nomme_chaque_role():
    projet = charger(RACINE)
    assert projet.depot == "PLiagre/Forge"
    assert str(projet.poste("codeur").principal) == "claude/claude-sonnet-5-5@high"
    assert str(projet.poste("chef").principal) == "claude/claude-opus-5-5@high"
    assert [str(a) for a in projet.poste("relecteur_moteur").agents] == ["claude/claude-opus-5-5@high"]
    assert [str(a) for a in projet.poste("relecteur").agents] == ["claude/claude-sonnet-5-5@high"]
    assert projet.poste("chroniqueur").lecture_seule and not projet.poste("codeur").lecture_seule
    assert "relecteur_moteur" in table_des_roles(projet)
    assert "codeur" in table_des_roles(projet)


def test_un_outil_inconnu_ou_un_role_absent_se_refuse(tmp_path, projet):
    with pytest.raises(ProjetIncomplet):
        lire_poste("codeur", "copilot/gpt")
    with pytest.raises(ProjetIncomplet):
        lire_poste("codeur", "codex")
    texte = (projet.racine / "atelier.toml").read_text(encoding="utf-8")
    sans_boussole = "".join(l for l in texte.splitlines(keepends=True) if not l.startswith("boussole"))
    (tmp_path / "atelier.toml").write_text(sans_boussole, encoding="utf-8")
    with pytest.raises(ProjetIncomplet, match="boussole"):
        charger(tmp_path)


def test_les_chemins_interdits_a_un_lot(projet):
    assert projet.interdit("atelier/pilote.py")
    assert projet.interdit(".github/workflows/tests.yml")
    assert projet.interdit("atelier.toml")
    assert not projet.interdit("jeu/sim/engine.py")
    assert not projet.interdit("atelier.toml.bak")


def test_argv_de_claude_en_ecriture_et_en_lecture():
    claude = A.argv(Agent("claude", "claude-opus-5-5"), "fais", lecture_seule=False, windows=False)
    assert claude[:7] == ["claude", "-p", "fais", "--model", "claude-opus-5-5", "--output-format", "json"]
    assert "acceptEdits" in claude and "Bash(git push:*)" in claude[claude.index("--disallowedTools") + 1]
    relit = A.argv(Agent("claude", "claude-opus-5-5"), "relis", lecture_seule=True, windows=False)
    assert "Edit" in relit[relit.index("--disallowedTools") + 1]


def test_aucune_cle_api_et_le_jeton_claude_par_l_environnement(monkeypatch, tmp_path):
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    for cle in A.CLES_API:
        monkeypatch.setenv(cle, "secret")
    jeton = tmp_path / "claude.token"
    jeton.write_text("jeton-longue-duree\n", encoding="utf-8")
    monkeypatch.setattr(A, "FICHIER_JETON_CLAUDE", jeton)
    env = A.environnement("claude")
    assert not any(cle in env for cle in A.CLES_API)
    assert env["CLAUDE_CODE_OAUTH_TOKEN"] == "jeton-longue-duree"


@pytest.mark.parametrize("code,texte,cause", [
    (0, "rate limit", None),
    (1, "Error: You've hit your usage limit. Try again later.", "quota"),
    (1, "429 Too Many Requests", "quota"),
    (1, "ActionRequiredError: Increase limits for faster responses You're out of usage. Switch to Auto, "
        "or ask your admin to increase your limit to continue.", "quota"),
    (1, "Invalid API key · Please run /login", "auth"),
    (1, "OAuth token has expired. Run claude setup-token", "auth"),
    (1, "AssertionError: capacité 3 != 4", None),
    (127, "binaire introuvable : claude", "installation"),
    (126, "ne démarre pas : [WinError 5] Accès refusé", "installation"),
])
def test_quota_et_session_se_reconnaissent_a_la_fin_de_la_sortie(code, texte, cause):
    assert A.cause_de_refus(code, texte) == cause


def test_un_quota_epuise_passe_au_secours(projet, tmp_path):
    agents = Agents((1, "You've hit your usage limit"), (0, "fait"))
    res = A.invoquer(projet.poste("codeur"), "code", tmp_path, 10, executeur=agents)
    assert res.reussi and str(res.agent) == "claude/haiku"
    assert agents.outils() == ["sonnet", "haiku"]


def test_aucun_agent_ne_repond_le_lot_attend(projet, tmp_path):
    agents = Agents((1, "429 Too Many Requests"), (1, "Please log in"))
    res = A.invoquer(projet.poste("codeur"), "code", tmp_path, 10, executeur=agents)
    assert res.attente and not res.reussi and not res.personne
    assert len(res.essais) == 2


def test_un_binaire_introuvable_passe_au_secours_et_n_est_pas_un_echec(projet, tmp_path):
    # Mesuré le 27 septembre 2026 : trois « 127 binaire introuvable » ont
    # compté comme trois échecs du codeur et bloqué le lot #118.
    agents = Agents((127, "binaire introuvable : claude"), (0, "fait"))
    res = A.invoquer(projet.poste("codeur"), "code", tmp_path, 10, executeur=agents)
    assert res.reussi and str(res.agent) == "claude/haiku"
    personne = A.invoquer(projet.poste("codeur"), "code", tmp_path, 10,
                          executeur=Agents((127, "binaire introuvable : claude"), (1, "429 Too Many Requests")))
    assert personne.attente and not personne.personne


def test_les_essais_disent_pourquoi_chaque_agent_a_ete_ecarte(projet, tmp_path):
    agents = Agents((1, "Error: You've hit your usage limit · resets 5pm"), (2, "SyntaxError"))
    res = A.invoquer(projet.poste("codeur"), "code", tmp_path, 10, executeur=agents)
    assert "claude/sonnet : quota épuisé" in res.essais[0] and "usage limit" in res.essais[0]
    assert res.essais[1] == "claude/haiku : code 2"


PROMPT_PIEGE = "Ligne 1\nLigne 2 & del /q x | findstr y %PATH% ^ \"guillemets\""


def test_sous_windows_le_lancement_de_chaque_outil(tmp_path):
    # CreateProcess n'ajoute que « .exe ». Et appeler un .cmd passerait le
    # prompt par cmd.exe, qui coupe aux retours à la ligne et interprète & | % ^.
    # Un shim npm : on lance son node et son .js, jamais le .cmd.
    npm = tmp_path / "npm"
    script = npm / "node_modules" / "outil" / "bin" / "outil.js"
    script.parent.mkdir(parents=True)
    script.write_text("", encoding="utf-8")
    (npm / "outil.cmd").write_text(
        '@ECHO off\r\nendLocal & goto #_undefined_# 2>NUL || title %COMSPEC% & "%_prog%"  '
        '"%dp0%\\node_modules\\outil\\bin\\outil.js" %*\r\n', encoding="utf-8")
    trouve = {"outil": str(npm / "outil.cmd"), "node": r"C:\nodejs\node.exe"}
    commande, _ = A.lancement(["outil", "exec", PROMPT_PIEGE], {}, windows=True, chercher=trouve.get)
    assert commande == [r"C:\nodejs\node.exe", str(script), "exec", PROMPT_PIEGE]
    # Un vrai .exe se lance tel quel.
    commande, _ = A.lancement(["claude", "-p", "x"], {}, windows=True,
                              chercher={"claude": r"C:\bin\claude.exe"}.get)
    assert commande == [r"C:\bin\claude.exe", "-p", "x"]
    # Un script qu'on ne sait pas lire ne passe jamais par cmd.exe : il est introuvable.
    (tmp_path / "autre.cmd").write_text("@echo off\r\nautre %*\r\n", encoding="utf-8")
    with pytest.raises(A.Introuvable):
        A.lancement(["autre", PROMPT_PIEGE], {}, windows=True, chercher={"autre": str(tmp_path / "autre.cmd")}.get)
    # Introuvable, il l'est aussi ; hors de Windows, rien ne change.
    with pytest.raises(A.Introuvable):
        A.lancement(["claude", "-p", "x"], {}, windows=True, chercher=lambda nom: None)
    assert A.lancement(["claude", "-p", "x"], {}, windows=False)[0] == ["claude", "-p", "x"]


def test_un_echec_ordinaire_ne_passe_pas_au_secours(projet, tmp_path):
    agents = Agents((2, "SyntaxError: invalid syntax"))
    res = A.invoquer(projet.poste("codeur"), "code", tmp_path, 10, executeur=agents)
    assert not res.reussi and not res.attente and str(res.agent) == "claude/sonnet"
    assert agents.outils() == ["sonnet"]


def test_exclure_ecarte_une_famille_de_modele(projet, tmp_path):
    # `exclure` nomme des familles de modèles, pas des outils : le secours du
    # dépanneur n'est pas le modèle qui vient de lire sans rien décider.
    agents = Agents((0, "DECISION: REPRENDRE :: relis SC6"))
    exclure = frozenset({lire_agent("claude/claude-opus-5-5@high").famille})
    res = A.invoquer(projet.poste("depanneur"), "lis", tmp_path, 10, exclure=exclure, executeur=agents)
    assert str(res.agent) == "claude/sonnet" and agents.outils() == ["sonnet"]
    assert "claude/opus : écarté" in res.essais[0]
    personne = A.invoquer(projet.poste("depanneur"), "lis", tmp_path, 10,
                          exclure=frozenset({"opus", "sonnet"}), executeur=Agents())
    assert personne.personne and not personne.attente


@pytest.mark.parametrize("agent,famille", [
    ("claude/claude-opus-5-5", "opus"),
    ("claude/opus", "opus"),
    ("claude/claude-sonnet-5-5", "sonnet"),
    ("claude/sonnet-renfort", "sonnet"),
    ("claude/claude-haiku-5-5", "haiku"),
    ("claude/claude-fable-5-1", "fable"),
])
def test_chaque_modele_claude_est_sa_propre_famille(agent, famille):
    # Toute la chaîne est Claude depuis le 5 novembre 2026 : si Claude était
    # une seule famille, le secours Sonnet du dépanneur ne lirait jamais
    # après Opus.
    assert lire_agent(agent).famille == famille


def test_seul_opus_ecrit_les_briefs():
    # Choix du propriétaire (30 octobre 2026) : un brief ne s'écrit qu'avec
    # Claude Opus 5.5. Opus à court de quota, le lot attend.
    chef = charger(RACINE).poste("chef")
    assert [str(a) for a in chef.agents] == ["claude/claude-opus-5-5@high"]


def test_opus_est_reserve_au_brief_et_au_moteur():
    # Refonte du 7 novembre 2026 : une seule réserve de quota pour tous les
    # rôles. Opus écrit les briefs et relit les lots qui touchent le moteur ;
    # Sonnet code tous les lots, PC compris, et fait tout le reste, journal du
    # matin compris, en effort moyen.
    projet = charger(RACINE)
    opus = {role for role, poste in projet.postes.items() if any(a.famille == "opus" for a in poste.agents)}
    assert opus == {"chef", "relecteur_moteur"}
    for role in ("codeur", "codeur_3d", "relecteur", "mecanicien", "depanneur", "chroniqueur", "boussole"):
        assert {a.famille for a in projet.poste(role).agents} == {"sonnet"}, role
    assert str(projet.poste("chroniqueur").principal) == "claude/claude-sonnet-5-5@medium"
    assert projet.poste("relecteur_moteur").lecture_seule and projet.poste("relecteur").lecture_seule


def test_le_relecteur_du_moteur_relit_ce_qui_touche_jeu_sim(projet, tmp_path):
    reel = charger(RACINE)
    assert reel.chemins_du_moteur == ("jeu/sim/",)
    assert reel.relecteur_pour(["docs/briefs/1.md", "jeu/sim/engine.py"]) == "relecteur_moteur"
    assert reel.relecteur_pour(["jeu/sim\\tests\\test_x.py"]) == "relecteur_moteur"
    for fichiers in ([], ["jeu/vues/tableau/x.py"], ["3d/unity/Assets/X.cs", "jeu/data/batiments.toml"],
                     ["jeu/simulateur/x.py"]):
        assert reel.relecteur_pour(fichiers) == "relecteur", fichiers
    # Un dépôt qui ne nomme pas de relecteur du moteur : le relecteur relit tout.
    assert projet.relecteur_pour(["jeu/sim/engine.py"]) == "relecteur"
    texte = (projet.racine / "atelier.toml").read_text(encoding="utf-8")
    (tmp_path / "atelier.toml").write_text(texte.replace('[agents]\n', '[agents]\nrenfort = "claude/sonnet"\n'),
                                           encoding="utf-8")
    with pytest.raises(ProjetIncomplet, match="rôles inconnus : renfort"):
        charger(tmp_path)


def test_un_lot_a_la_taille_d_une_ligne_du_cap():
    # Un gain que le joueur voit et sa preuve dans la même PR : 1 500 lignes
    # environ (refonte du 7 novembre 2026 ; à 300, une ligne du CAP devenait
    # 3,9 issues et un lot sur trois n'était qu'une preuve).
    assert charger(RACINE).lignes_max == 1500


def test_plus_rien_que_claude():
    # Le propriétaire n'a plus que l'abonnement Claude : plus de GPT ni de
    # Codex (30 octobre 2026), plus de grok ni de composer par Cursor
    # (5 novembre). Le dépôt n'appelle que Claude Code, l'atelier ne sait plus
    # appeler un autre harnais, et le chargement refuse la ligne qui remettrait
    # un autre modèle.
    projet = charger(RACINE)
    assert OUTILS == {"claude": "claude"}
    assert projet.postes and all(a.outil == "claude" for poste in projet.postes.values() for a in poste.agents)
    for ligne in ("claude/opus | claude/grok-4.7-high@high", "claude/gpt-5.6-sol@high", "claude/composer-2.5"):
        with pytest.raises(ProjetIncomplet, match="seuls les modèles Claude"):
            lire_poste("chef", ligne)
    for texte in ("cursor/grok-4.7-high@high", "cursor/claude-opus-5-5-high", "codex/gpt-5.6-sol@high"):
        with pytest.raises(ProjetIncomplet, match="outil inconnu"):
            lire_agent(texte)


def test_chaque_agent_du_depot_dit_son_harnais_son_modele_et_son_effort():
    projet = charger(RACINE)
    for poste in projet.postes.values():
        for agent in poste.agents:
            assert agent.effort, f"{poste.role} : {agent} ne dit pas son effort"
    table = table_des_roles(projet)
    for mot in ("Claude Code", "claude-opus-5-5", "claude-sonnet-5-5", "high"):
        assert mot in table


def test_l_effort_passe_a_claude_code_par_son_option():
    claude = A.argv(lire_agent("claude/claude-opus-5-5@xhigh"), "x", lecture_seule=True)
    assert claude[claude.index("--effort") + 1] == "xhigh"
    # Sans effort, l'appel reste celui d'avant.
    assert "--effort" not in A.argv(lire_agent("claude/opus"), "x", lecture_seule=True)


@pytest.mark.parametrize("texte,motif", [
    ("claude/claude-opus-5-5@minimal", "ne connaît pas l'effort"),
    ("claude/claude-sonnet-5-5@defaut", "ne connaît pas l'effort"),   # « defaut » était à Cursor
    ("claude/claude-opus-5-5@", "illisible"),
])
def test_un_effort_que_le_harnais_ne_recoit_pas_se_refuse(texte, motif):
    with pytest.raises(ProjetIncomplet, match=motif):
        lire_agent(texte)


def test_sonnet_code_tous_les_lots_et_aucun_renfort():
    # Le renfort donnait le dernier passage à un autre modèle ; avec un seul
    # abonnement, c'était Sonnet encore une fois (retiré le 7 novembre 2026).
    projet = charger(RACINE)
    for role in ("codeur", "codeur_3d", "mecanicien"):
        assert {a.famille for a in projet.poste(role).agents} == {"sonnet"}, role
        assert not projet.poste(role).lecture_seule
    assert "renfort" not in projet.postes and "renfort" not in ROLES


def test_chaque_lot_du_vps_peut_coder_avec_sonnet():
    # Claude tient un codeur par lot du VPS, et il lui reste une place pour
    # juger ; deux lots, un par processeur du VPS (28 octobre 2026).
    projet = charger(RACINE)
    assert projet.capacite("vps") == 2
    assert projet.plafond("claude") > projet.capacite("vps")


def test_un_quota_du_chef_passe_a_son_secours(projet, tmp_path):
    agents = Agents((1, "Error: You've hit your usage limit"), (0, "DECISION: BRIEF"))
    res = A.invoquer(projet.poste("chef"), "prépare", tmp_path, 10, executeur=agents)
    assert res.reussi and str(res.agent) == "claude/sonnet"


# Le parallélisme : combien de lots par machine, combien d'agents par outil.

def _toml_avec(projet, tmp_path, ajout):
    texte = (projet.racine / "atelier.toml").read_text(encoding="utf-8") + ajout
    (tmp_path / "atelier.toml").write_text(texte, encoding="utf-8")
    return tmp_path


def test_sans_reglage_chaque_machine_tient_un_lot_et_aucun_outil_n_a_de_plafond(projet):
    assert projet.capacite("vps") == 1 and projet.capacite("pc") == 1
    assert projet.plafond("claude") is None


def test_le_parallelisme_se_lit_et_une_faute_se_refuse(projet, tmp_path):
    (tmp_path / "bon").mkdir()
    lu = charger(_toml_avec(projet, tmp_path / "bon", "\n[machines]\nvps = 3\n\n[outils]\nclaude = 2\n"))
    assert lu.capacite("vps") == 3 and lu.capacite("pc") == 1
    assert lu.plafond("claude") == 2
    assert "vps 3" in table_des_roles(lu) and "claude 2" in table_des_roles(lu)
    # Cursor n'est plus un outil : son plafond se refuse comme une faute de frappe.
    for ajout, motif in (("\n[machines]\nvps = 0\n", "vps"), ("\n[machines]\nmac = 2\n", "mac"),
                         ("\n[outils]\nclaude = \"deux\"\n", "claude"), ("\n[outils]\ncursor = 1\n", "cursor")):
        dossier = tmp_path / motif
        dossier.mkdir(exist_ok=True)
        with pytest.raises(ProjetIncomplet, match=motif):
            charger(_toml_avec(projet, dossier, ajout))


def test_le_depot_fait_avancer_plusieurs_lots_du_vps_et_plafonne_ses_outils():
    projet = charger(RACINE)
    assert projet.capacite("vps") >= 2 and projet.capacite("pc") == 1
    for outil in {a.outil for poste in projet.postes.values() for a in poste.agents}:
        assert projet.plafond(outil), outil


class _Places:
    """Des places d'outil dictées : `pleins` n'en a plus."""

    def __init__(self, *pleins):
        self.pleins = set(pleins)
        self.demandees: list[str] = []

    def __call__(self, outil):
        from contextlib import nullcontext
        self.demandees.append(outil)
        return nullcontext(outil not in self.pleins)


def test_claude_a_son_plafond_le_lot_attend_sans_essai(projet, tmp_path):
    # Claude est le seul outil : ses places prises, aucun secours n'est libre.
    agents = Agents()
    res = A.invoquer(projet.poste("codeur"), "code", tmp_path, 10, executeur=agents, place=_Places("claude"))
    assert res.attente and not res.personne and agents.appels == []
    assert res.essais and all("occupé (claude a déjà tous ses agents en route)" in e for e in res.essais)


def test_une_place_libre_laisse_coder(projet, tmp_path):
    agents = Agents((0, "fait"))
    places = _Places()
    res = A.invoquer(projet.poste("codeur"), "code", tmp_path, 10, executeur=agents, place=places)
    assert res.reussi and str(res.agent) == "claude/sonnet" and places.demandees == ["claude"]


# La sonde : un agent qui écrit doit vraiment écrire.

def test_la_sonde_exige_qu_un_agent_qui_ecrit_ecrive(projet):
    codeur = projet.poste("codeur")
    unique = type(codeur)(role="codeur", agents=codeur.agents[:1])
    ok, _ = A.sonder(unique, projet.racine, executeur=Agents((0, "OK", {A.FICHIER_SONDE: "OK"})))
    assert ok
    # Contre-épreuve : l'agent du PC du 29 septembre 2026, qui répond « OK »
    # sans rien pouvoir écrire.
    ok, detail = A.sonder(unique, projet.racine, executeur=Agents((0, "OK")))
    assert not ok and "sans rien écrire" in detail


def test_la_sonde_d_un_agent_en_lecture_seule_ne_demande_qu_une_reponse(projet):
    relecteur = projet.poste("relecteur")
    unique = type(relecteur)(role="relecteur", agents=relecteur.agents[:1])
    assert A.sonder(unique, projet.racine, executeur=Agents((0, "OK")))[0]
    assert not A.sonder(unique, projet.racine, executeur=Agents((0, "non")))[0]


# Un harnais qui refuse l'appel : le réglage est en cause, pas l'agent.

@pytest.mark.parametrize("sortie", [
    "error: unknown option '--effort'",                                         # un Claude Code trop ancien
    "Error loading config.toml: unknown variant `extreme`, expected one of `minimal`, `low`, `medium`, `high`",
    "error: unexpected argument '--effort' found",
])
def test_un_harnais_qui_refuse_l_appel_passe_la_main_sans_bruler_d_essai(projet, tmp_path, sortie):
    assert A.cause_de_refus(2, sortie) == "appel"
    agents = Agents((2, sortie), (0, "fait"))
    res = A.invoquer(projet.poste("codeur"), "code", tmp_path, 10, executeur=agents)
    assert res.reussi and str(res.agent) == "claude/haiku"
    assert "refuse l'appel" in res.essais[0]


def test_une_session_claude_perdue_fait_attendre_le_lot(tmp_path):
    # Sur la vraie ligne du codeur : la session Claude du VPS a expiré le
    # 21 octobre 2026. Sans autre harnais, le lot attend, et aucun essai
    # n'est brûlé ; le journal demande de ranger un nouveau jeton.
    refus = "Failed to authenticate: OAuth session expired and could not be refreshed"
    res = A.invoquer(charger(RACINE).poste("codeur"), "code", tmp_path, 10, executeur=Agents((1, refus)))
    assert res.attente and not res.reussi and not res.personne
    assert res.essais and "claude/claude-sonnet-5-5@high : session expirée" in res.essais[0]


def test_un_effort_inconnu_que_claude_code_ignore_n_est_pas_un_refus():
    # Mesuré le 29 septembre 2026 (Claude Code 2.1.284) : il prévient, prend
    # son effort par défaut et rend 0. C'est le chargement qui l'empêche.
    sortie = ("Warning: Unknown --effort value 'bogus' — ignoring it and using the default effort. "
              "Valid values: low, medium, high, xhigh, max.")
    assert A.cause_de_refus(0, sortie) is None
    with pytest.raises(ProjetIncomplet):
        lire_agent("claude/claude-opus-5-5@bogus")


def test_un_test_rouge_de_l_agent_n_est_pas_un_appel_refuse():
    # Contre-épreuve : argparse, lancé par un test que l'agent a joué, écrit
    # « unrecognized arguments » ; c'est l'échec de l'agent, pas du harnais.
    sortie = "E   SystemExit: 2\nusage: forge [-h]\nforge: error: unrecognized arguments: --vite\n1 failed"
    assert A.cause_de_refus(1, sortie) is None


# Ce que Claude Code 2.1.312 rend avec `--output-format json` (relevé le 10 novembre 2026, abrégé).
def _json_de_claude(texte, *, erreur=False, cout=0.42, extra=""):
    return ('{"type":"result","subtype":"' + ("error_during_execution" if erreur else "success") + '","is_error":'
            + ("true" if erreur else "false") + ',"num_turns":7,"duration_ms":93400,"total_cost_usd":' + str(cout)
            + ',"usage":{"input_tokens":12,"cache_creation_input_tokens":8000,"cache_read_input_tokens":30000,'
            '"output_tokens":900},"result":' + json.dumps(texte) + extra + "}")


def test_la_sortie_json_rend_le_texte_de_l_agent_et_ce_que_l_appel_a_coute(projet, tmp_path):
    """Jusqu'au 10 novembre 2026, la sortie était en texte : 1 071 appels en
    cinq semaines, et personne ne savait ce que coûtait un lot."""
    texte, mesure = A.lire_sortie("un avertissement du harnais\n" + _json_de_claude("Fait.\nVERDICT: ACCEPTE") + "\n")
    assert texte == "Fait.\nVERDICT: ACCEPTE"
    assert mesure == {"cout": 0.42, "tours": 7, "duree": 93, "entree": 38012, "sortie": 900, "erreur": False}
    res = A.invoquer(projet.poste("codeur"), "code", tmp_path, 10,
                     executeur=Agents((0, _json_de_claude("Fait."))))
    assert res.reussi and res.texte == "Fait." and res.mesure["cout"] == 0.42


@pytest.mark.parametrize("sortie", ["Fait.\nVERDICT: ACCEPTE", "", '{"pas": "un résultat"}', "{json cassé",
                                    '["type", "result"]'])
def test_une_sortie_qui_n_est_pas_ce_json_reste_telle_quelle_sans_mesure(sortie):
    """Contre-épreuve : on ne devine pas un coût. Un appel coupé par son
    délai, un autre harnais ou une version ancienne rendent leur texte."""
    assert A.lire_sortie(sortie) == (sortie, {})


def test_un_quota_dit_en_json_fait_toujours_attendre_sans_bruler_d_essai(projet, tmp_path):
    """Le refus se lit dans le texte de l'agent, ou ailleurs dans ce que le
    harnais a rendu ; et une erreur dite sans code d'erreur reste une erreur."""
    for refus in (_json_de_claude("You've hit your usage limit", erreur=True),
                  _json_de_claude("", erreur=True, extra=',"api_error_status":429')):
        agents = Agents((1, refus), (0, _json_de_claude("fait")))
        res = A.invoquer(projet.poste("codeur"), "code", tmp_path, 10, executeur=agents)
        assert res.reussi and str(res.agent) == "claude/haiku" and "quota" in res.essais[0]
    sans_code = A.invoquer(projet.poste("relecteur"), "relis", tmp_path, 10,
                           executeur=Agents((0, _json_de_claude("l'outil a planté", erreur=True))))
    assert not sans_code.reussi and sans_code.code == 1 and not sans_code.attente
    # Un agent qui parle de quota dans un travail réussi n'est pas un refus.
    bavard = A.invoquer(projet.poste("codeur"), "code", tmp_path, 10,
                        executeur=Agents((0, _json_de_claude("Le quota de grain est codé."))))
    assert bavard.reussi and str(bavard.agent) == "claude/sonnet"

