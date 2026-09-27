"""Les rôles, et comment on appelle un agent : la ligne de commande exacte,
les clés retirées, le secours sur quota, le relecteur qui n'est pas l'auteur."""

from __future__ import annotations

from pathlib import Path

import pytest

from atelier import agents as A
from atelier.projet import Agent, ProjetIncomplet, charger, lire_poste, table_des_roles

from conftest import RACINE, Agents


def test_le_branchement_du_depot_nomme_chaque_role():
    projet = charger(RACINE)
    assert projet.depot == "PLiagre/Forge"
    assert str(projet.poste("codeur").principal) == "codex/gpt-5.6-sol"
    assert str(projet.poste("chef").principal) == "claude/claude-opus-5-5"
    assert [str(a) for a in projet.poste("relecteur").agents] == ["claude/claude-opus-5-5", "codex/gpt-5.6-sol"]
    assert projet.poste("chroniqueur").lecture_seule and not projet.poste("codeur").lecture_seule
    assert "codeur" in table_des_roles(projet)


def test_un_outil_inconnu_ou_un_role_absent_se_refuse(tmp_path, projet):
    with pytest.raises(ProjetIncomplet):
        lire_poste("codeur", "copilot/gpt")
    with pytest.raises(ProjetIncomplet):
        lire_poste("codeur", "codex")
    texte = (projet.racine / "atelier.toml").read_text(encoding="utf-8")
    (tmp_path / "atelier.toml").write_text(texte.replace('boussole    = "claude/opus"\n', ""), encoding="utf-8")
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


def test_un_echec_ordinaire_ne_passe_pas_au_secours(projet, tmp_path):
    agents = Agents((2, "SyntaxError: invalid syntax"))
    res = A.invoquer(projet.poste("codeur"), "code", tmp_path, 10, executeur=agents)
    assert not res.reussi and not res.attente and str(res.agent) == "codex/sol"
    assert agents.outils() == ["codex"]


def test_le_modele_qui_ecrit_ne_relit_jamais(projet, tmp_path):
    agents = Agents((0, "VERDICT: ACCEPTE"))
    res = A.invoquer(projet.poste("relecteur"), "relis", tmp_path, 10, exclure=frozenset({"claude"}), executeur=agents)
    assert str(res.agent) == "codex/sol" and agents.outils() == ["codex"]
    personne = A.invoquer(projet.poste("relecteur"), "relis", tmp_path, 10,
                          exclure=frozenset({"claude", "codex"}), executeur=Agents())
    assert personne.personne and not personne.attente
