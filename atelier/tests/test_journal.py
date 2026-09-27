"""Le journal du matin : des faits relevés sur GitHub, jamais inventés, et
publiés même quand le chroniqueur se tait."""

from __future__ import annotations

from datetime import datetime, timezone

from atelier import journal
from atelier.lots import marque

from conftest import Agents

MAINTENANT = datetime(2026, 9, 28, 5, 15, tzinfo=timezone.utc)


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
    corps = journal.ecrire(gh, projet, maintenant=MAINTENANT, executeur=Agents((1, "429 Too Many Requests")))
    assert "faits bruts" in corps and "conflit non résolu" in corps
    assert gh.issues_[99]["comments"][-1]["body"] == corps


def test_le_chroniqueur_met_les_faits_en_phrases(projet, gh):
    _preparer(gh)
    agents = Agents((0, "### Livré hier\nLe contrat.\n"))
    corps = journal.ecrire(gh, projet, maintenant=MAINTENANT, executeur=agents)
    assert corps.startswith("## Journal du 28/09/2026") and "Écrit par cursor/grok" in corps
    assert "--mode" in agents.appels[0] and "ask" in agents.appels[0]
