"""Les rôles, et comment on appelle un agent : la ligne de commande exacte,
les clés retirées, le secours sur quota, le relecteur qui n'est pas l'auteur."""

from __future__ import annotations

import pytest

from atelier import agents as A
from atelier.projet import OUTILS, Agent, ProjetIncomplet, charger, lire_agent, lire_poste, table_des_roles

from conftest import RACINE, Agents


def test_le_branchement_du_depot_nomme_chaque_role():
    projet = charger(RACINE)
    assert projet.depot == "PLiagre/Forge"
    assert str(projet.poste("codeur").principal) == "claude/claude-sonnet-5-5@high"
    assert str(projet.poste("chef").principal) == "claude/claude-opus-5-5@high"
    assert [str(a) for a in projet.poste("relecteur").agents] == [
        "claude/claude-opus-5-5@high", "claude/claude-sonnet-5-5@high"]
    assert projet.poste("chroniqueur").lecture_seule and not projet.poste("codeur").lecture_seule
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
    assert claude[:6] == ["claude", "-p", "fais", "--model", "claude-opus-5-5", "--output-format"]
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


def test_le_modele_qui_ecrit_ne_relit_jamais(projet, tmp_path):
    # `exclure` nomme des familles de modèles, pas des outils.
    agents = Agents((0, "VERDICT: ACCEPTE"))
    res = A.invoquer(projet.poste("relecteur"), "relis", tmp_path, 10, exclure=frozenset({"opus"}), executeur=agents)
    assert str(res.agent) == "claude/sonnet" and agents.outils() == ["sonnet"]
    personne = A.invoquer(projet.poste("relecteur"), "relis", tmp_path, 10,
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
    # une seule famille, aucun lot n'aurait plus de relecteur. Opus relit
    # Sonnet, Sonnet relit Opus.
    assert lire_agent(agent).famille == famille


def test_du_code_ecrit_par_opus_est_relu_par_sonnet(projet, tmp_path):
    agents = Agents((0, "VERDICT: ACCEPTE"))
    res = A.invoquer(projet.poste("relecteur"), "relis", tmp_path, 10,
                     exclure=frozenset({lire_agent("claude/claude-opus-5-5@high").famille}), executeur=agents)
    assert str(res.agent) == "claude/sonnet" and agents.outils() == ["sonnet"]
    assert "claude/opus : écarté" in res.essais[0]


def test_seul_opus_ecrit_les_briefs():
    # Choix du propriétaire (30 octobre 2026) : un brief ne s'écrit qu'avec
    # Claude Opus 5.5. Opus à court de quota, le lot attend.
    chef = charger(RACINE).poste("chef")
    assert [str(a) for a in chef.agents] == ["claude/claude-opus-5-5@high"]


def test_les_roles_qui_lisent_ont_un_secours_d_un_autre_modele():
    # Un quota d'Opus arrêtait net la boussole. Le secours du dépanneur lit le
    # lot quand Opus n'a rien décidé, en écartant sa famille
    # (pilote._depanner) : il doit être d'un autre modèle.
    projet = charger(RACINE)
    for role in ("boussole", "depanneur", "chroniqueur"):
        poste = projet.poste(role)
        assert str(poste.principal).startswith("claude/claude-opus-5-5@"), role
        assert any(a.famille != poste.principal.famille for a in poste.secours), role


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


def _relecteurs_restants(poste_relecteur, auteurs):
    return [str(a) for a in poste_relecteur.agents if a.famille not in auteurs]


def test_sonnet_code_le_vps_opus_le_pc_et_chacun_relit_l_autre():
    # Sonnet code les lots du VPS (28 octobre 2026), Opus ceux du PC, peu
    # nombreux et chers quand ils ratent (29 septembre 2026). Sans autre
    # famille que Claude, chacun relit le code de l'autre.
    projet = charger(RACINE)
    assert [str(a) for a in projet.poste("codeur").agents] == ["claude/claude-sonnet-5-5@high"]
    assert [str(a) for a in projet.poste("codeur_3d").agents] == ["claude/claude-opus-5-5@high"]
    relecteur = projet.poste("relecteur")
    assert _relecteurs_restants(relecteur, {"sonnet"}) == ["claude/claude-opus-5-5@high"]
    assert _relecteurs_restants(relecteur, {"opus"}) == ["claude/claude-sonnet-5-5@high"]


def test_le_renfort_est_le_modele_du_codeur():
    # Le dernier passage d'un lot du VPS compte comme un passage du codeur :
    # un renfort d'un autre modèle ferait écrire le lot par les deux, et
    # personne ne pourrait plus le relire.
    projet = charger(RACINE)
    renfort = projet.poste("renfort")
    assert str(renfort.principal) == "claude/claude-sonnet-5-5@high" and not renfort.lecture_seule
    assert {a.famille for a in renfort.agents} == {a.famille for a in projet.poste("codeur").agents}


def test_chaque_lot_du_vps_peut_coder_avec_sonnet():
    # Claude tient un codeur par lot du VPS, et il lui reste une place pour
    # juger ; deux lots, un par processeur du VPS (28 octobre 2026).
    projet = charger(RACINE)
    assert projet.capacite("vps") == 2
    assert projet.plafond("claude") > projet.capacite("vps")


def test_aucun_lot_ne_reste_sans_relecteur_possible():
    # Tout est Claude : un lot qu'Opus et Sonnet auraient écrit tous les deux
    # se bloquerait, « aucun relecteur possible ». Quel que soit l'agent de sa
    # ligne qui code un lot, un modèle qui ne l'a pas écrit peut le relire.
    projet = charger(RACINE)
    relecteur = projet.poste("relecteur")
    for roles in (("codeur", "renfort"), ("codeur_3d",), ("mecanicien",)):
        auteurs = {a.famille for role in roles for a in projet.poste(role).agents}
        assert _relecteurs_restants(relecteur, auteurs), f"un lot écrit par {sorted(auteurs)} n'a plus de relecteur"


def test_un_codeur_avec_opus_en_secours_laisserait_un_lot_sans_relecteur():
    # Contre-épreuve : Sonnet code, Opus prend la correction sur un quota, et
    # la même règle ne trouve plus personne pour relire.
    relecteur = lire_poste("relecteur", "claude/claude-opus-5-5 | claude/claude-sonnet-5-5")
    codeur = lire_poste("codeur", "claude/claude-sonnet-5-5 | claude/claude-opus-5-5")
    assert _relecteurs_restants(relecteur, {a.famille for a in codeur.agents}) == []


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
