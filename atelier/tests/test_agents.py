"""Les rôles, et comment on appelle un agent : la ligne de commande exacte,
les clés retirées, le secours sur quota, le relecteur qui n'est pas l'auteur."""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from atelier import agents as A
from atelier.projet import Agent, ProjetIncomplet, charger, lire_agent, lire_poste, table_des_roles

from conftest import RACINE, Agents


def test_le_branchement_du_depot_nomme_chaque_role():
    projet = charger(RACINE)
    assert projet.depot == "PLiagre/Forge"
    assert str(projet.poste("codeur").principal) == "codex/gpt-6-sol@high"
    assert str(projet.poste("chef").principal) == "claude/claude-opus-5-5@high"
    assert [str(a) for a in projet.poste("relecteur").agents] == [
        "claude/claude-opus-5-5@high", "codex/gpt-6-astra@high", "codex/gpt-6-sol@high",
        "cursor/grok-4.7-high@high"]
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


def test_argv_de_chaque_outil_en_ecriture_et_en_lecture():
    claude = A.argv(Agent("claude", "claude-opus-5-5"), "fais", lecture_seule=False, windows=False)
    assert claude[:6] == ["claude", "-p", "fais", "--model", "claude-opus-5-5", "--output-format"]
    assert "acceptEdits" in claude and "Bash(git push:*)" in claude[claude.index("--disallowedTools") + 1]
    relit = A.argv(Agent("claude", "claude-opus-5-5"), "relis", lecture_seule=True, windows=False)
    assert "Edit" in relit[relit.index("--disallowedTools") + 1]
    codex = A.argv(Agent("codex", "gpt-5.6-sol"), "fais", lecture_seule=False, sortie=Path("r.txt"))
    assert codex[:4] == ["codex", "exec", "--model", "gpt-5.6-sol"] and "workspace-write" in codex
    assert codex[-1] == "fais" and "--output-last-message" in codex
    assert "sandbox_workspace_write.network_access=true" in codex
    relit_codex = A.argv(Agent("codex", "gpt-5.6-sol"), "x", lecture_seule=True)
    assert "read-only" in relit_codex and not any("network_access" in a for a in relit_codex)
    cursor = A.argv(Agent("cursor", "grok-4.7-high"), "x", lecture_seule=True)
    assert cursor[0] == "cursor-agent" and cursor[cursor.index("--mode") + 1] == "ask"
    assert "--force" in A.argv(Agent("cursor", "composer-2.5"), "x", lecture_seule=False)


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
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in A.environnement("codex")


@pytest.mark.parametrize("code,texte,cause", [
    (0, "rate limit", None),
    (1, "Error: You've hit your usage limit. Try again later.", "quota"),
    (1, "429 Too Many Requests", "quota"),
    (1, "Invalid API key · Please run /login", "auth"),
    (1, "OAuth token has expired. Run claude setup-token", "auth"),
    (1, "AssertionError: capacité 3 != 4", None),
    (127, "binaire introuvable : cursor-agent", "installation"),
    (126, "ne démarre pas : [WinError 5] Accès refusé", "installation"),
])
def test_quota_et_session_se_reconnaissent_a_la_fin_de_la_sortie(code, texte, cause):
    assert A.cause_de_refus(code, texte) == cause


def test_un_quota_epuise_passe_au_secours(projet, tmp_path):
    agents = Agents((1, "You've hit your usage limit"), (0, "fait"))
    res = A.invoquer(projet.poste("codeur"), "code", tmp_path, 10, executeur=agents)
    assert res.reussi and str(res.agent) == "cursor/grok"
    assert agents.outils() == ["codex", "cursor-agent"]


def test_aucun_agent_ne_repond_le_lot_attend(projet, tmp_path):
    agents = Agents((1, "429 Too Many Requests"), (1, "Please log in"))
    res = A.invoquer(projet.poste("codeur"), "code", tmp_path, 10, executeur=agents)
    assert res.attente and not res.reussi and not res.personne
    assert len(res.essais) == 2


def test_un_binaire_introuvable_passe_au_secours_et_n_est_pas_un_echec(projet, tmp_path):
    # Mesuré le 27 septembre 2026 : trois « 127 binaire introuvable » ont
    # compté comme trois échecs du codeur et bloqué le lot #118.
    agents = Agents((127, "binaire introuvable : codex"), (0, "fait"))
    res = A.invoquer(projet.poste("codeur"), "code", tmp_path, 10, executeur=agents)
    assert res.reussi and str(res.agent) == "cursor/grok"
    personne = A.invoquer(projet.poste("codeur"), "code", tmp_path, 10,
                          executeur=Agents((127, "binaire introuvable : codex"), (1, "429 Too Many Requests")))
    assert personne.attente and not personne.personne


def test_les_essais_disent_pourquoi_chaque_agent_a_ete_ecarte(projet, tmp_path):
    agents = Agents((1, "Error: You've hit your usage limit · resets 5pm"), (2, "SyntaxError"))
    res = A.invoquer(projet.poste("codeur"), "code", tmp_path, 10, executeur=agents)
    assert "codex/sol : quota épuisé" in res.essais[0] and "usage limit" in res.essais[0]
    assert res.essais[1] == "cursor/grok : code 2"


def _faux_cursor(racine: Path) -> Path:
    """Une installation de cursor-agent comme celle du PC : un .cmd, un .ps1
    et une version par dossier, chacune avec son node.exe."""
    dossier = racine / "cursor-agent"
    for version in ("2026.07.23-e383d2b", "2026.08.11-e8db854", "2026.08.9-0aa"):
        (dossier / "versions" / version).mkdir(parents=True)
        (dossier / "versions" / version / "node.exe").write_bytes(b"")
        (dossier / "versions" / version / "index.js").write_text("", encoding="utf-8")
    (dossier / "versions" / "pas-une-version").mkdir()
    (dossier / "cursor-agent.cmd").write_text("@echo off\r\n", encoding="utf-8")
    (dossier / "cursor-agent.ps1").write_text("", encoding="utf-8")
    return dossier


PROMPT_PIEGE = "Ligne 1\nLigne 2 & del /q x | findstr y %PATH% ^ \"guillemets\""


def test_sous_windows_cursor_agent_se_lance_par_son_node_sans_cmd_exe(monkeypatch, tmp_path):
    # CreateProcess n'ajoute que « .exe » : « cursor-agent » est introuvable.
    # Et appeler cursor-agent.cmd passerait le prompt par cmd.exe, qui coupe
    # aux retours à la ligne et interprète & | % ^.
    dossier = _faux_cursor(tmp_path)
    derniere = dossier / "versions" / "2026.08.11-e8db854"
    recu = {}

    def faux_run(commande, **kw):
        recu["argv"], recu["env"] = commande, kw["env"]
        return subprocess.CompletedProcess(commande, 0, "OK", "")

    monkeypatch.setattr(A.subprocess, "run", faux_run)
    monkeypatch.setattr(A, "WINDOWS", True, raising=False)
    env = {"PATH": "", "LOCALAPPDATA": str(tmp_path)}
    code, _, _ = A.executer(A.argv(Agent("cursor", "claude-opus-5-5-high"), PROMPT_PIEGE, lecture_seule=False,
                                   windows=True), tmp_path, env, 10)
    assert code == 0
    assert recu["argv"][:2] == [str(derniere / "node.exe"), str(derniere / "index.js")]
    assert recu["argv"][2:5] == ["-p", PROMPT_PIEGE, "--model"]
    assert recu["env"]["CURSOR_INVOKED_AS"] == "cursor-agent.cmd"


def test_sous_windows_le_lancement_de_chaque_outil(tmp_path):
    dossier = _faux_cursor(tmp_path)
    derniere = dossier / "versions" / "2026.08.11-e8db854"
    # Trouvé par le PATH (le .cmd), ou dans son dossier d'installation par défaut.
    trouve = {"cursor-agent": str(dossier / "cursor-agent.cmd")}
    for chercher in (trouve.get, lambda nom: None):
        commande, env = A.lancement(["cursor-agent", "-p", PROMPT_PIEGE], {"LOCALAPPDATA": str(tmp_path)},
                                    windows=True, chercher=chercher)
        assert commande == [str(derniere / "node.exe"), str(derniere / "index.js"), "-p", PROMPT_PIEGE]
    # Le shim npm de codex : on lance son node et son .js, jamais le .cmd.
    npm = tmp_path / "npm"
    script = npm / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
    script.parent.mkdir(parents=True)
    script.write_text("", encoding="utf-8")
    (npm / "codex.cmd").write_text(
        '@ECHO off\r\nendLocal & goto #_undefined_# 2>NUL || title %COMSPEC% & "%_prog%"  '
        '"%dp0%\\node_modules\\@openai\\codex\\bin\\codex.js" %*\r\n', encoding="utf-8")
    trouve = {"codex": str(npm / "codex.cmd"), "node": r"C:\nodejs\node.exe"}
    commande, _ = A.lancement(["codex", "exec", PROMPT_PIEGE], {}, windows=True, chercher=trouve.get)
    assert commande == [r"C:\nodejs\node.exe", str(script), "exec", PROMPT_PIEGE]
    # Un vrai .exe se lance tel quel.
    commande, _ = A.lancement(["claude", "-p", "x"], {}, windows=True,
                              chercher={"claude": r"C:\bin\claude.exe"}.get)
    assert commande == [r"C:\bin\claude.exe", "-p", "x"]
    # Un script qu'on ne sait pas lire ne passe jamais par cmd.exe : il est introuvable.
    (tmp_path / "autre.cmd").write_text("@echo off\r\nautre %*\r\n", encoding="utf-8")
    with pytest.raises(A.Introuvable):
        A.lancement(["autre", PROMPT_PIEGE], {}, windows=True, chercher={"autre": str(tmp_path / "autre.cmd")}.get)
    # Hors de Windows, rien ne change.
    assert A.lancement(["cursor-agent", "-p", "x"], {}, windows=False)[0] == ["cursor-agent", "-p", "x"]


def test_un_echec_ordinaire_ne_passe_pas_au_secours(projet, tmp_path):
    agents = Agents((2, "SyntaxError: invalid syntax"))
    res = A.invoquer(projet.poste("codeur"), "code", tmp_path, 10, executeur=agents)
    assert not res.reussi and not res.attente and str(res.agent) == "codex/sol"
    assert agents.outils() == ["codex"]


def test_le_modele_qui_ecrit_ne_relit_jamais(projet, tmp_path):
    # `exclure` nomme des familles de modèles, pas des outils.
    agents = Agents((0, "VERDICT: ACCEPTE"))
    res = A.invoquer(projet.poste("relecteur"), "relis", tmp_path, 10, exclure=frozenset({"claude"}), executeur=agents)
    assert str(res.agent) == "codex/sol" and agents.outils() == ["codex"]
    personne = A.invoquer(projet.poste("relecteur"), "relis", tmp_path, 10,
                          exclure=frozenset({"claude", "gpt"}), executeur=Agents())
    assert personne.personne and not personne.attente


@pytest.mark.parametrize("agent,famille", [
    ("claude/claude-opus-5-5", "claude"),
    ("cursor/claude-opus-5-5-high", "claude"),
    ("cursor/sonnet-5", "claude"),
    ("codex/gpt-5.6-sol", "gpt"),
    ("cursor/gpt-5.6", "gpt"),
    ("cursor/grok-4.7-high", "grok"),
    ("cursor/composer-2.5", "composer"),
    ("cursor/gemini-3-pro", "gemini"),
    ("cursor/kimi-k3", "kimi"),
])
def test_la_famille_d_un_modele_ne_depend_pas_de_l_outil(agent, famille):
    # Claude Code ne porte que des modèles Claude, Codex que des modèles
    # d'OpenAI ; Cursor porte tout : sa famille se lit dans le nom du modèle.
    assert lire_agent(agent).famille == famille


def test_du_code_ecrit_par_cursor_claude_n_est_pas_relu_par_claude(projet, tmp_path):
    agents = Agents((0, "VERDICT: ACCEPTE"))
    res = A.invoquer(projet.poste("relecteur"), "relis", tmp_path, 10,
                     exclure=frozenset({lire_agent("cursor/opus-high").famille}), executeur=agents)
    assert str(res.agent) == "codex/sol" and agents.outils() == ["codex"]
    assert "claude/opus : écarté" in res.essais[0]


def test_le_chef_et_la_boussole_ont_un_secours_hors_de_claude_code():
    # Un quota de Claude Code arrêtait net le chef et la boussole : Claude
    # Code en premier, et un secours d'un autre harnais. Astra seul ne suffit
    # pas : son quota Plus est court, et quand Claude est à court, chaque
    # brief lui tombe dessus (29 septembre 2026). Un secours qui n'est ni
    # Claude ni Astra tient le poste quand les deux sont épuisés.
    projet = charger(RACINE)
    for role in ("chef", "boussole"):
        poste = projet.poste(role)
        assert poste.principal.outil == "claude", role
        assert any(a.outil != "claude" for a in poste.secours), role
        assert any(a.outil != "claude" and a.modele != "gpt-6-astra" for a in poste.secours), role


def test_claude_ne_passe_que_par_claude_code():
    # Le choix du propriétaire (29 septembre 2026) : jamais un modèle Claude
    # porté par Cursor ou un autre harnais. Le dépôt n'en a aucun, et le
    # chargement refuse la ligne qui en mettrait un.
    projet = charger(RACINE)
    for poste in projet.postes.values():
        for agent in poste.agents:
            assert agent.famille != "claude" or agent.outil == "claude", f"{poste.role} : {agent}"
    for ligne in ("cursor/claude-opus-5-5-high@high", "claude/opus | cursor/opus-high", "codex/sonnet-4"):
        with pytest.raises(ProjetIncomplet, match="ne passe que par Claude Code"):
            lire_poste("chef", ligne)


def test_chaque_agent_du_depot_dit_son_harnais_son_modele_et_son_effort():
    projet = charger(RACINE)
    for poste in projet.postes.values():
        for agent in poste.agents:
            assert agent.effort, f"{poste.role} : {agent} ne dit pas son effort"
    table = table_des_roles(projet)
    for mot in ("Claude Code", "Codex CLI", "Cursor (cursor-agent)", "claude-opus-5-5", "high"):
        assert mot in table


def test_l_effort_passe_a_chaque_harnais_par_son_chemin():
    claude = A.argv(lire_agent("claude/claude-opus-5-5@xhigh"), "x", lecture_seule=True)
    assert claude[claude.index("--effort") + 1] == "xhigh"
    codex = A.argv(lire_agent("codex/gpt-5.6-sol@medium"), "x", lecture_seule=False)
    assert codex[codex.index("-c") + 1] == 'model_reasoning_effort="medium"'
    cursor = A.argv(lire_agent("cursor/grok-4.7-high@high"), "x", lecture_seule=False)
    assert cursor[cursor.index("--model") + 1] == "grok-4.7-high" and "--effort" not in cursor
    # Sans effort, l'appel reste celui d'avant.
    assert "--effort" not in A.argv(lire_agent("claude/opus"), "x", lecture_seule=True)
    assert not any("reasoning" in a for a in A.argv(lire_agent("codex/sol"), "x", lecture_seule=True))


@pytest.mark.parametrize("texte,motif", [
    ("claude/claude-opus-5-5@minimal", "ne connaît pas l'effort"),   # minimal est à codex
    ("codex/gpt-5.6-sol@max", "ne connaît pas l'effort"),            # max est à Claude Code
    ("cursor/grok-4.7-high@xhigh", "dans le nom du modèle"),         # le nom dit high
    ("cursor/grok-4.7@high", "dans le nom du modèle"),               # le nom ne dit rien
    ("cursor/composer-2.5@high", "dans le nom du modèle"),
    ("cursor/grok-4.7-high@defaut", "dans le nom du modèle"),
    ("codex/gpt-5.6-sol@", "illisible"),
])
def test_un_effort_que_le_harnais_ne_recoit_pas_se_refuse(texte, motif):
    with pytest.raises(ProjetIncomplet, match=motif):
        lire_agent(texte)


def _relecteurs_restants(poste_relecteur, famille_auteur):
    return [a for a in poste_relecteur.agents if a.famille != famille_auteur]


def test_claude_juge_et_ne_code_que_les_lots_du_pc():
    # Le plafond de Claude Code (29 septembre 2026) se garde pour le chef et
    # la relecture : le codeur du VPS n'est pas un Claude. Les lots du PC, peu
    # nombreux et chers quand ils ratent, ont Claude en tête (choix du
    # propriétaire, 29 septembre 2026) ; chaque codeur a un secours d'une
    # autre famille, qu'un quota de Claude n'arrête pas.
    projet = charger(RACINE)
    assert projet.poste("codeur").principal.famille != "claude"
    assert projet.poste("codeur_3d").principal.famille == "claude"
    for role in ("codeur", "codeur_3d"):
        poste = projet.poste(role)
        assert any(a.famille != "claude" for a in poste.secours), role
    assert projet.poste("relecteur").principal.famille == "claude"


def test_gpt_6_astra_ne_passe_qu_en_secours_ou_en_renfort():
    # Avec l'abonnement ChatGPT Plus, GPT-6 Astra n'a que quelques dizaines
    # de messages toutes les cinq heures dans Codex : il n'est en tête que du
    # renfort, qui ne sert qu'au dernier passage d'un lot, et le relecteur a
    # GPT-6 Sol après lui quand son quota s'épuise.
    projet = charger(RACINE)
    for role in projet.postes:
        if role != "renfort":
            assert projet.poste(role).principal.modele != "gpt-6-astra", role
    relecteurs = [a.modele for a in projet.poste("relecteur").agents]
    assert relecteurs.index("gpt-6-sol") > relecteurs.index("gpt-6-astra")


def test_le_renfort_est_astra_puis_le_codeur():
    # Le quota d'Astra épuisé, le dernier passage revient aux agents du
    # codeur, dans le même ordre : le renfort ne fait jamais moins bien.
    projet = charger(RACINE)
    renfort = projet.poste("renfort")
    assert str(renfort.principal) == "codex/gpt-6-astra@high" and not renfort.lecture_seule
    assert renfort.secours == projet.poste("codeur").agents


def test_un_lot_a_toujours_deux_relecteurs_possibles():
    # Quelle que soit la famille qui a écrit, au moins deux agents peuvent
    # relire : un quota ne laisse plus un lot sans relecture (#186, le
    # 28 septembre 2026 : Claude écarté, codex à court de quota).
    projet = charger(RACINE)
    relecteur = projet.poste("relecteur")
    auteurs = {a.famille for role in ("codeur", "codeur_3d", "mecanicien") for a in projet.poste(role).agents}
    for famille in auteurs:
        restants = _relecteurs_restants(relecteur, famille)
        assert len(restants) >= 2, f"un lot écrit par {famille} n'a que {[str(a) for a in restants]}"


def test_l_ancienne_ligne_du_relecteur_laissait_un_lot_sans_secours():
    # Contre-épreuve : la ligne d'avant ne laissait qu'un relecteur à un lot
    # écrit par Claude, et la même règle la refuse.
    ancienne = lire_poste("relecteur", "claude/claude-opus-5-5 | codex/gpt-5.6-sol")
    assert len(_relecteurs_restants(ancienne, "claude")) == 1


def test_un_quota_du_chef_passe_a_son_secours(projet, tmp_path):
    agents = Agents((1, "Error: You've hit your usage limit"), (0, "DECISION: BRIEF"))
    res = A.invoquer(projet.poste("chef"), "prépare", tmp_path, 10, executeur=agents)
    assert res.reussi and str(res.agent) == "codex/sol"


# Le parallélisme : combien de lots par machine, combien d'agents par outil.

def _toml_avec(projet, tmp_path, ajout):
    texte = (projet.racine / "atelier.toml").read_text(encoding="utf-8") + ajout
    (tmp_path / "atelier.toml").write_text(texte, encoding="utf-8")
    return tmp_path


def test_sans_reglage_chaque_machine_tient_un_lot_et_aucun_outil_n_a_de_plafond(projet):
    assert projet.capacite("vps") == 1 and projet.capacite("pc") == 1
    assert projet.plafond("codex") is None


def test_le_parallelisme_se_lit_et_une_faute_se_refuse(projet, tmp_path):
    (tmp_path / "bon").mkdir()
    lu = charger(_toml_avec(projet, tmp_path / "bon", "\n[machines]\nvps = 3\n\n[outils]\ncodex = 2\n"))
    assert lu.capacite("vps") == 3 and lu.capacite("pc") == 1
    assert lu.plafond("codex") == 2 and lu.plafond("claude") is None
    assert "vps 3" in table_des_roles(lu) and "codex 2" in table_des_roles(lu)
    for ajout, motif in (("\n[machines]\nvps = 0\n", "vps"), ("\n[machines]\nmac = 2\n", "mac"),
                         ("\n[outils]\ncodex = \"deux\"\n", "codex"), ("\n[outils]\ncopilot = 1\n", "copilot")):
        dossier = tmp_path / motif
        dossier.mkdir(exist_ok=True)
        with pytest.raises(ProjetIncomplet, match=motif):
            charger(_toml_avec(projet, dossier, ajout))


def test_le_depot_fait_avancer_plusieurs_lots_du_vps_et_plafonne_ses_outils():
    projet = charger(RACINE)
    assert projet.capacite("vps") >= 2 and projet.capacite("pc") == 1
    for outil in ("claude", "codex", "cursor"):
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


def test_un_outil_a_son_plafond_passe_la_main_a_son_secours(projet, tmp_path):
    agents = Agents((0, "fait"))
    res = A.invoquer(projet.poste("codeur"), "code", tmp_path, 10, executeur=agents, place=_Places("codex"))
    assert res.reussi and str(res.agent) == "cursor/grok" and agents.outils() == ["cursor-agent"]
    assert "codex/sol : occupé" in res.essais[0]


def test_tous_les_outils_occupes_le_lot_attend_sans_essai(projet, tmp_path):
    agents = Agents()
    res = A.invoquer(projet.poste("codeur"), "code", tmp_path, 10, executeur=agents,
                     place=_Places("codex", "cursor"))
    assert res.attente and not res.personne and agents.appels == []


# La sonde : un agent qui écrit doit vraiment écrire.

def test_la_sonde_exige_qu_un_agent_qui_ecrit_ecrive(projet):
    codeur = projet.poste("codeur")
    unique = type(codeur)(role="codeur", agents=codeur.agents[:1])
    ok, _ = A.sonder(unique, projet.racine, executeur=Agents((0, "OK", {A.FICHIER_SONDE: "OK"})))
    assert ok
    # Contre-épreuve : le codex du PC du 29 septembre 2026, qui répond « OK »
    # sans rien pouvoir écrire.
    ok, detail = A.sonder(unique, projet.racine, executeur=Agents((0, "OK")))
    assert not ok and "sans rien écrire" in detail


def test_la_sonde_d_un_agent_en_lecture_seule_ne_demande_qu_une_reponse(projet):
    relecteur = projet.poste("relecteur")
    unique = type(relecteur)(role="relecteur", agents=relecteur.agents[:1])
    assert A.sonder(unique, projet.racine, executeur=Agents((0, "OK")))[0]
    assert not A.sonder(unique, projet.racine, executeur=Agents((0, "non")))[0]


def test_codex_ne_code_pas_sur_le_pc():
    # Son bac à sable Windows ne démarre pas : il répond, mais n'écrit rien.
    assert all(a.outil != "codex" for a in charger(RACINE).poste("codeur_3d").agents)


# Un harnais qui refuse l'appel : le réglage est en cause, pas l'agent.

@pytest.mark.parametrize("sortie", [
    "error: unknown option '--effort'",                                         # un Claude Code trop ancien
    "Error loading config.toml: unknown variant `extreme`, expected one of `minimal`, `low`, `medium`, `high`",
    "error: unexpected argument '--effort' found",                              # clap, côté Codex
])
def test_un_harnais_qui_refuse_l_appel_passe_la_main_sans_bruler_d_essai(projet, tmp_path, sortie):
    assert A.cause_de_refus(2, sortie) == "appel"
    agents = Agents((2, sortie), (0, "fait"))
    res = A.invoquer(projet.poste("codeur"), "code", tmp_path, 10, executeur=agents)
    assert res.reussi and str(res.agent) == "cursor/grok"
    assert "refuse l'appel" in res.essais[0]


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
