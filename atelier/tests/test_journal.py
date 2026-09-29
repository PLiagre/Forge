"""Le journal du matin : des faits relevés sur GitHub, jamais inventés, et
publiés même quand le chroniqueur se tait."""

from __future__ import annotations

from datetime import datetime, timezone
import json

import pytest

from atelier import journal, prompts
from atelier.lots import marque

from conftest import Agents

MAINTENANT = datetime(2026, 9, 28, 5, 15, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _sans_la_machine(monkeypatch, tmp_path):
    """Aucun test ne lit le journal du pilote ni la veille de la machine qui le joue."""
    monkeypatch.setattr(journal, "JOURNAL_LOCAL", tmp_path / "absent" / "journal.jsonl")
    monkeypatch.setattr(journal, "VEILLE", tmp_path / "absent" / "veille.txt")


def _preparer(gh):
    gh.ajouter_issue(10, "Le service lit un lieu", ("lot", "en-cours"))
    gh.ajouter_pr(50, "lot/10-le-service-lit-un-lieu")
    gh.ajouter_issue(11, "Le panneau", ("lot", "bloque"))
    gh.issues_[11]["comments"].append({"body": "bloqué\n\n" + marque(role="pilote", etat="bloque", raison="conflit non résolu")})
    gh.ajouter_issue(12, "La preuve du jalon", ("lot", "pret"))
    gh.ajouter_issue(99, journal.TITRE_JOURNAL, ("journal",), jalon=None)
    gh.ajouter_pr(49, "lot/9-le-contrat", etat="MERGED",
                  commentaires=["📷 ![capture](https://raw.githubusercontent.com/moi/essai/journal/captures/a.png)"])
    gh.prs_[49]["mergedAt"] = "2026-09-27T20:00:00Z"
    gh.json = lambda *args: [dict(gh.prs_[49], title="Lot #9 — Le contrat", url="https://x/pull/49")]


def test_les_faits_du_matin(projet, gh):
    _preparer(gh)
    texte = journal.faits(gh, projet, MAINTENANT)
    assert "PR #49 « Lot #9 — Le contrat »" in texte
    assert "![capture](https://raw.githubusercontent.com/moi/essai/journal/captures/a.png)" in texte
    assert "#11 « Le panneau » : conflit non résolu" in texte
    assert "#10 « Le service lit un lieu » (vps), PR #50" in texte
    assert "J1 — Le pont" in texte and "#12 « La preuve du jalon »" in texte


def test_le_journal_se_publie_meme_si_le_chroniqueur_se_tait(projet, gh):
    _preparer(gh)
    corps = journal.ecrire(gh, projet, maintenant=MAINTENANT, executeur=Agents((1, "429 Too Many Requests")),
                           photographe=lambda *a: [])
    assert "faits bruts" in corps and "conflit non résolu" in corps
    # Les faits bruts restent du markdown : une image s'y affiche.
    assert "```" not in corps and "![capture](https://raw.githubusercontent.com" in corps
    assert gh.issues_[99]["comments"][-1]["body"] == corps


def test_le_chroniqueur_met_les_faits_en_phrases(projet, gh):
    _preparer(gh)
    agents = Agents((0, "### Livré hier\nLe contrat.\n"))
    corps = journal.ecrire(gh, projet, maintenant=MAINTENANT, executeur=agents, photographe=lambda *a: [])
    assert corps.startswith("## Journal du 28/09/2026") and "Écrit par cursor/grok" in corps
    assert "--mode" in agents.appels[0] and "ask" in agents.appels[0]


COMPTE_RENDU = ("🤖 **codeur_3d** (claude/claude-opus-5-5) — code, révision `fe2b1e8`.\n\n"
                "## Compte rendu — lot #9\n\nLe contrat ne connaît plus que `cell_id` : Unity reçoit la clé du monde.\n\n"
                "📷 ![capture du lot #9](https://raw.githubusercontent.com/moi/essai/journal/captures/b.png)\n\n"
                + marque(role="codeur_3d", etat="fait", essai=1, agent="claude/claude-opus-5-5", sha="f" * 40))
REVUE = ("## Relecture — ACCEPTE\n\nRévision `fffffff` · relu par codex/gpt-5.6-sol\n\nAucun constat bloquant.\n\n"
         + marque(role="relecteur", verdict="ACCEPTE", sha="f" * 40, agent="codex/gpt-5.6-sol"))


def _journee(gh, tmp_path):
    """Une journée comme le 28 septembre 2026 : un lot livré, un changement de
    la machine, un lot du PC qui attend, et le journal du pilote."""
    gh.ajouter_issue(99, journal.TITRE_JOURNAL, ("journal",), jalon=None)
    gh.ajouter_pr(49, "lot/9-le-contrat", etat="MERGED", commentaires=[COMPTE_RENDU, REVUE])
    gh.ajouter_pr(48, "direct/fusion-propre", etat="MERGED")
    for p in (48, 49):
        gh.prs_[p]["mergedAt"] = "2026-09-27T20:00:00Z"
    titres = {49: "Lot #9 — Le contrat", 48: "Une PR déjà fusionnable se fusionne tout de suite"}
    gh.json = lambda *args: [dict(gh.prs_[n], title=t, url=f"https://x/pull/{n}") for n, t in titres.items()]
    gh.ajouter_issue(10, "Le panneau", ("lot", "en-cours", "pc"))
    attente = ("🤖 **codeur_3d** (PC) : le lot attend — aucun agent n'a pu répondre : claude/claude-opus-5-5 : "
               "quota épuisé (« You've hit your monthly spend limit ») · cursor/claude-opus-5-5-high : session "
               "expirée ou absente (« Error: Authentication required. Please run 'agent login' first »)\n\n"
               + marque(role="codeur_3d", etat="attente", quand="2026-09-28T01:40:24+00:00"))
    gh.ajouter_pr(50, "lot/10-le-panneau", commentaires=[attente])
    local = tmp_path / "journal.jsonl"
    evenements = [("2026-09-28T01:12:00+00:00", 11, "découpé", "#12, #13"),
                  ("2026-09-28T01:21:00+00:00", 10, "envoyé au PC", "coder")]
    evenements += [(f"2026-09-28T02:{m:02d}:00+00:00", 10, "attendre_pc", "PR #50") for m in (0, 10, 20)]
    evenements += [("2026-09-26T01:00:00+00:00", 8, "livré", "trop vieux pour ce journal")]
    local.write_text("".join(json.dumps({"quand": q, "lot": l, "action": a, "detail": d, "agent": None}) + "\n"
                             for q, l, a, d in evenements), encoding="utf-8")
    veille = tmp_path / "veille.txt"
    veille.write_text("PASS  claude — 2.1.283\nFAIL  codex — absent du PATH\n", encoding="utf-8")
    return local, veille


def test_les_faits_racontent_chaque_lot_livre(projet, gh, tmp_path):
    local, veille = _journee(gh, tmp_path)
    texte = journal.faits(gh, projet, MAINTENANT, journal_local=local, veille=veille)
    lots_livres, machine = texte.split("LA MACHINE")[0], texte.split("LA MACHINE")[1]
    # Ce que le lot change, dit par le codeur et jugé par le relecteur, pas seulement son titre.
    assert "Le contrat ne connaît plus que `cell_id`" in lots_livres
    assert "ACCEPTE par codex/gpt-5.6-sol" in lots_livres and "1 passage" in lots_livres
    assert "![capture](https://raw.githubusercontent.com/moi/essai/journal/captures/b.png)" in lots_livres
    # Les changements de la machine ne se mêlent pas aux lots.
    assert "fusionnée tout de suite" not in lots_livres and "PR #48" in machine


def test_les_faits_disent_ce_que_la_chaine_a_vecu(projet, gh, tmp_path):
    local, veille = _journee(gh, tmp_path)
    texte = journal.faits(gh, projet, MAINTENANT, journal_local=local, veille=veille)
    vecu = texte.split("CE QUE LA CHAÎNE A VÉCU")[1]
    assert "#11 : découpé (#12, #13)" in vecu
    assert "attendre_pc ×3" in vecu and "envoyé au PC" in vecu
    assert "trop vieux" not in texte
    # Le lot du PC dit où il en est, avec la raison de son attente.
    assert "monthly spend limit" in texte


def test_les_faits_disent_ce_que_le_proprietaire_doit_faire(projet, gh, tmp_path):
    local, veille = _journee(gh, tmp_path)
    texte = journal.faits(gh, projet, MAINTENANT, journal_local=local, veille=veille)
    a_faire = texte.split("À FAIRE PAR LE PROPRIÉTAIRE")[1]
    assert "cursor-agent login" in a_faire and "PC" in a_faire
    assert "plafond de dépense" in a_faire
    assert "codex — absent du PATH" in a_faire


def test_a_faire_lit_les_secours_du_vps_et_un_lot_du_pc_mis_de_cote(projet, gh, tmp_path):
    # Le 28 septembre 2026 : le chef a répondu par son secours (claude au
    # plafond), et la raison de l'attente du PC était sur la PR de #184, mis
    # de côté : ni l'une ni l'autre ne remontait.
    local, veille = _journee(gh, tmp_path)
    gh.issues_[10]["labels"] = [{"name": n} for n in ("lot", "bloque", "pc")]
    local.write_text(json.dumps({"quand": "2026-09-28T01:38:00+00:00", "lot": 12, "action": "secours",
                                 "detail": "chef : claude/claude-opus-5-5 : quota épuisé (« You've hit your "
                                           "monthly spend limit »)", "agent": "cursor/claude-opus-5-5-high"}) + "\n",
                     encoding="utf-8")
    texte = journal.faits(gh, projet, MAINTENANT, journal_local=local, veille=veille)
    a_faire = texte.split("À FAIRE PAR LE PROPRIÉTAIRE")[1]
    assert "PC : la session cursor est expirée ou absente → cursor-agent login" in a_faire
    assert "plafond de dépense" in a_faire
    assert "#12 : secours" in texte.split("CE QUE LA CHAÎNE A VÉCU")[1]


def test_une_attente_dementie_par_une_reponse_plus_recente_ne_se_demande_plus(projet, gh, tmp_path):
    # Le 29 septembre 2026, le journal demandait de relever le plafond de
    # Claude et disait Codex sans quota : Claude codait sur le PC depuis la
    # veille, et Codex avait relu #186 à 23:31.
    local, veille = _journee(gh, tmp_path)
    reponse = ("🤖 **codeur_3d** (claude/claude-opus-5-5) — code.\n\n"
               + marque(role="codeur_3d", etat="fait", essai=1, agent="claude/claude-opus-5-5", sha="f" * 40))
    gh.prs_[50]["comments"].append({"body": reponse, "createdAt": "2026-09-28T03:10:00Z"})
    evenements = [("2026-09-28T02:30:00+00:00", 10, "attente", None,
                   "relecteur : claude/claude-opus-5-5 : écarté (sa famille, claude, a écrit ce lot) · "
                   "codex/gpt-5.6-sol : quota épuisé (« usage limit · try again later »)"),
                  ("2026-09-28T03:31:00+00:00", 10, "relecture CORRIGER", "codex/gpt-5.6-sol", "PR #50")]
    local.write_text("".join(json.dumps({"quand": q, "lot": l, "action": a, "agent": ag, "detail": d}) + "\n"
                             for q, l, a, ag, d in evenements), encoding="utf-8")
    texte = journal.faits(gh, projet, MAINTENANT, journal_local=local, veille=veille)
    a_faire = texte.split("À FAIRE PAR LE PROPRIÉTAIRE")[1]
    assert "plafond de dépense" not in a_faire
    # Cursor n'a pas répondu depuis sur le PC : sa session reste à rouvrir.
    assert "PC : la session cursor est expirée ou absente → cursor-agent login" in a_faire
    vecu = texte.split("CE QUE LA CHAÎNE A VÉCU")[1].split("BLOQUÉS")[0]
    assert "quota épuisé" in vecu and "LEVÉE DEPUIS" in vecu


def test_une_attente_sans_reponse_plus_recente_reste_a_faire(projet, gh, tmp_path):
    # La contre-épreuve : une réponse plus ancienne que l'attente ne la lève pas.
    local, veille = _journee(gh, tmp_path)
    reponse = marque(role="codeur_3d", etat="fait", essai=1, agent="claude/claude-opus-5-5", sha="f" * 40)
    gh.prs_[50]["comments"].insert(0, {"body": reponse, "createdAt": "2026-09-28T01:00:00Z"})
    local.write_text(json.dumps({"quand": "2026-09-28T02:30:00+00:00", "lot": 10, "action": "relecture ACCEPTE",
                                 "agent": "codex/gpt-5.6-sol", "detail": "PR #50"}) + "\n" +
                     json.dumps({"quand": "2026-09-28T02:40:00+00:00", "lot": 10, "action": "attente", "agent": None,
                                 "detail": "relecteur : codex/gpt-5.6-sol : quota épuisé (« usage limit »)"}) + "\n",
                     encoding="utf-8")
    texte = journal.faits(gh, projet, MAINTENANT, journal_local=local, veille=veille)
    assert "plafond de dépense" in texte.split("À FAIRE PAR LE PROPRIÉTAIRE")[1]
    vecu = texte.split("CE QUE LA CHAÎNE A VÉCU")[1].split("BLOQUÉS")[0]
    assert "quota épuisé" in vecu and "LEVÉE DEPUIS" not in vecu


def test_les_prochains_lots_suivent_l_ordre_du_pilote(projet, gh, tmp_path):
    # Le 28 septembre 2026, le journal annonçait « ensuite #120, #121, #184 » :
    # l'ordre des numéros, alors que les trois attendaient des dépendances.
    local, veille = _journee(gh, tmp_path)
    gh.ajouter_issue(20, "Le lanceur", ("lot", "pret", "pc"), corps="Dépend de : #10")
    gh.ajouter_issue(30, "Le client", ("lot", "pret", "pc"))
    texte = journal.faits(gh, projet, MAINTENANT, journal_local=local, veille=veille)
    prochains = next(l for l in texte.splitlines() if l.startswith("PROCHAINS LOTS"))
    assert "#30" in prochains and "#20" not in prochains
    assert "#20 « Le lanceur » (attend #10)" in texte


def test_le_chroniqueur_doit_raconter_et_non_recopier(projet, gh, tmp_path):
    texte = prompts.chroniqueur(faits="LOTS LIVRÉS …")
    for titre in ("### Ce qui a changé dans le jeu", "### Ce que la chaîne a vécu", "### À faire par toi"):
        assert titre in texte
    assert "pas le titre recopié" in texte


def test_chaque_journal_porte_la_photo_du_monde(projet, gh):
    _preparer(gh)
    url = "https://raw.githubusercontent.com/moi/essai/journal/captures/2026-09-28/monde-2026-09-28.png"
    agents = Agents((1, "429 Too Many Requests"))
    corps = journal.ecrire(gh, projet, maintenant=MAINTENANT, executeur=agents, photographe=lambda *a: [url])
    assert f"![le monde]({url})" in corps
