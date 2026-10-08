"""Le journal du matin : des faits relevés sur GitHub, jamais inventés, et
publiés même quand le chroniqueur se tait."""

from __future__ import annotations

from datetime import datetime, timezone
import json

import pytest

from atelier import journal, lots, prompts
from atelier.lots import marque

from conftest import Agents

MAINTENANT = datetime(2026, 9, 28, 5, 15, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _sans_la_machine(monkeypatch, tmp_path):
    """Aucun test ne lit le journal du pilote, la veille, ni le réseau."""
    monkeypatch.setattr(journal, "JOURNAL_LOCAL", tmp_path / "absent" / "journal.jsonl")
    monkeypatch.setattr(journal, "VEILLE", tmp_path / "absent" / "veille.txt")

    def _pas_de_reseau(url):
        raise OSError(f"pas de réseau dans les tests ({url})")

    monkeypatch.setattr(journal, "_lire_image", _pas_de_reseau)


def _preparer(gh):
    gh.ajouter_issue(10, "Le service lit un lieu", ("lot", "en-cours"))
    gh.ajouter_pr(50, "lot/10-le-service-lit-un-lieu")
    gh.ajouter_issue(11, "Le panneau", ("lot", "bloque"))
    gh.issues_[11]["comments"].append({"body": "bloqué\n\n" + marque(role="pilote", etat="bloque", raison="conflit non résolu")})
    gh.ajouter_issue(12, "La preuve du jalon", ("lot", "pret"))
    gh.ajouter_issue(99, "Journal de Forge", ("journal",), jalon=None)
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
    # Le pilote écrit seul, dans le gabarit du chroniqueur, et dit pourquoi.
    assert corps.startswith("> **Avancé** : #9 Le contrat est livré.")
    assert "> **Bloqué** : #11 Le panneau (conflit non résolu)." in corps
    assert "Le chroniqueur n'a pas répondu" in corps and "Écrit par le pilote" in corps
    # Du markdown, pas des faits bruts : une image s'y affiche.
    assert "```" not in corps and "![capture](https://raw.githubusercontent.com" in corps
    nouvelle = max(gh.issues_)
    assert gh.issues_[nouvelle]["title"] == "Journal du 28/09/2026" and gh.issues_[nouvelle]["body"] == corps


JOURNAL_BIEN_ECRIT = """> **Avancé** : le contrat ne parle plus qu'en cellules.
> **Bloqué** : le panneau attend la résolution d'un conflit.
> **À faire** : rien.

### Ce qui a changé dans le jeu

**[Le contrat](https://x/pull/49)** — Unity reçoit la clé du monde.

*Le ksar : rien ne bouge, c'est voulu.*
![capture](https://raw.githubusercontent.com/moi/essai/journal/captures/a.png)

### Aujourd'hui

#12 part dès que #11 est débloqué."""


def test_le_chroniqueur_met_les_faits_en_phrases(projet, gh):
    _preparer(gh)
    agents = Agents((0, JOURNAL_BIEN_ECRIT))
    corps = journal.ecrire(gh, projet, maintenant=MAINTENANT, executeur=agents, photographe=lambda *a: [])
    assert corps.startswith(JOURNAL_BIEN_ECRIT) and "Écrit par cursor/grok" in corps
    assert "--mode" in agents.appels[0] and "ask" in agents.appels[0]
    # Sous le texte du chroniqueur, le pilote ajoute l'avancement du jalon et les détails, repliés.
    assert "### Jalon J1 — Le pont" in corps and "- [ ] #11 Le panneau — **bloqué** : conflit non résolu" in corps
    assert "<details><summary>Détails de la chaîne</summary>" in corps


@pytest.mark.parametrize("faute, pourquoi", [
    ("#12 part dès que #11", "#12 part dès que #777"),
    ("captures/a.png", "captures/inventee.png"),
    ("> **Bloqué** :", "> Bloqué :"),
])
def test_un_journal_qui_invente_ou_sort_du_gabarit_ne_parait_pas(projet, gh, faute, pourquoi):
    _preparer(gh)
    agents = Agents((0, JOURNAL_BIEN_ECRIT.replace(faute, pourquoi)))
    corps = journal.ecrire(gh, projet, maintenant=MAINTENANT, executeur=agents, photographe=lambda *a: [])
    texte, signature = corps.rsplit("<sub>", 1)
    assert pourquoi not in texte and "est écarté" in signature and "Écrit par le pilote" in signature
    assert corps.startswith("> **Avancé** : #9 Le contrat")


def test_chaque_journal_est_une_issue_epinglee_qui_ferme_la_precedente(projet, gh):
    _preparer(gh)
    gh.ajouter_issue(98, "Boussole de la semaine du 21/09/2026", ("journal",), jalon=None)
    journal.ecrire(gh, projet, maintenant=MAINTENANT, executeur=Agents((0, JOURNAL_BIEN_ECRIT)),
                   photographe=lambda *a: [])
    hier = max(gh.issues_)
    journal.ecrire(gh, projet, maintenant=MAINTENANT.replace(day=29), executeur=Agents((0, JOURNAL_BIEN_ECRIT)),
                   photographe=lambda *a: [])
    aujourd_hui = max(gh.issues_)
    ouvertes = {i["title"] for i in gh.issues("open") if i["number"] in (98, 99, hier, aujourd_hui)}
    # L'ancienne issue unique et le journal d'hier se ferment ; la boussole reste.
    assert ouvertes == {"Journal du 29/09/2026", "Boussole de la semaine du 21/09/2026"}
    assert ("epingler", aujourd_hui) in gh.gestes and ("desepingler", hier) in gh.gestes
    assert ("fermer_issue", 99, False) in gh.gestes


def test_le_journal_ne_montre_que_la_capture_de_la_revision_livree(projet, gh):
    # Le 29 septembre 2026, #174 montrait ses captures du 27 et du 28.
    _preparer(gh)
    vieille = "📷 ![capture](https://raw.githubusercontent.com/moi/essai/journal/captures/vieille.png)"
    neuve = ("📷 ![capture](https://raw.githubusercontent.com/moi/essai/journal/captures/neuve.png)\n"
             "![carte](https://raw.githubusercontent.com/moi/essai/journal/captures/neuve-carte.png)")
    gh.prs_[49]["comments"] = [{"body": vieille}, {"body": neuve}]
    texte = journal.faits(gh, projet, MAINTENANT)
    assert "neuve.png" in texte and "vieille.png" not in texte and "neuve-carte.png" not in texte


def test_l_avancement_dit_de_chaque_lot_du_jalon_s_il_est_fait_et_sinon_ce_qu_il_attend(projet, gh):
    _preparer(gh)
    gh.ajouter_issue(5, "Le service", ("lot", "livre"), etat="CLOSED")
    gh.ajouter_issue(6, "Le grand lot", ("lot", "pret"), etat="CLOSED")
    gh.ajouter_issue(7, "Un morceau", ("lot", "livre"), corps="Découpé du lot #6", etat="CLOSED")
    gh.ajouter_issue(8, "Un autre morceau", ("lot", "idee"), corps="Découpé du lot #6")
    gh.ajouter_issue(13, "Le lanceur", ("lot", "pret", "pc"), corps="Dépend de : #10, #6")
    gh.ajouter_issue(14, "Hors du jalon", ("lot", "idee"), jalon="J2 — Le geste revient")
    r = journal.releve(gh, projet, MAINTENANT)
    assert r.avancement == [
        "- [x] #5 Le service",
        "- ~~#6 Le grand lot~~ — découpé en #7, #8",
        "- [x] #7 Un morceau",
        "- [ ] #8 Un autre morceau — idée, pas encore prête",
        "- [ ] #10 Le service lit un lieu — en cours sur le VPS",
        "- [ ] #11 Le panneau — **bloqué** : conflit non résolu",
        "- [ ] #12 La preuve du jalon — prêt",
        # #6 est fermé depuis sa découpe : le lanceur attend son morceau encore ouvert.
        "- [ ] #13 Le lanceur — attend #8, #10",
    ]


COMPTE_RENDU = ("🤖 **codeur_3d** (claude/claude-opus-5-5) — code, révision `fe2b1e8`.\n\n"
                "## Compte rendu — lot #9\n\nLe contrat ne connaît plus que `cell_id` : Unity reçoit la clé du monde.\n\n"
                "📷 ![capture du lot #9](https://raw.githubusercontent.com/moi/essai/journal/captures/b.png)\n\n"
                + marque(role="codeur_3d", etat="fait", essai=1, agent="claude/claude-opus-5-5", sha="f" * 40))
REVUE = ("## Relecture — ACCEPTE\n\nRévision `fffffff` · relu par codex/gpt-5.6-sol\n\nAucun constat bloquant.\n\n"
         + marque(role="relecteur", verdict="ACCEPTE", sha="f" * 40, agent="codex/gpt-5.6-sol"))


def _journee(gh, tmp_path):
    """Une journée comme le 28 septembre 2026 : un lot livré, un changement de
    la machine, un lot du PC qui attend, et le journal du pilote."""
    gh.ajouter_issue(99, "Journal de Forge", ("journal",), jalon=None)
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


def test_le_journal_annonce_les_lots_du_jalon_suivant_a_part(projet, gh, tmp_path):
    # La fenêtre de deux jalons : un lot de J2 part quand sa machine n'a plus
    # rien dans J1. Le journal le dit à part, sans le mêler aux prochains de J1.
    local, veille = _journee(gh, tmp_path)
    gh.ajouter_issue(40, "La table de 1400", ("lot", "pret"), "J2 — Le geste revient")
    gh.ajouter_issue(41, "Attend la table", ("lot", "pret"), "J2 — Le geste revient", corps="Dépend de : #40")
    gh.ajouter_issue(42, "Rangé ailleurs", ("lot", "idee", "reserve"), "J2 — Le geste revient")
    r = journal.releve(gh, projet, MAINTENANT, journal_local=local, veille=veille)
    prochains = next(l for l in r.texte.splitlines() if l.startswith("PROCHAINS LOTS"))
    avance = next(l for l in r.texte.splitlines() if l.startswith("EN AVANCE"))
    assert "#40" not in prochains
    assert "J2 — Le geste revient" in avance and "#40 « La table de 1400 » (vps)" in avance
    assert "#41" not in avance and "#42" not in avance
    assert "#40 La table de 1400 : jalon suivant, il part quand le VPS n'a plus rien dans J1 — Le pont." in r.aujourd_hui


def test_le_journal_annonce_les_lots_du_troisieme_jalon(projet, gh, tmp_path):
    # La fenêtre a trois jalons, pour les deux machines.
    local, veille = _journee(gh, tmp_path)
    gh.jalons_.append({"number": 3, "title": "J3 — Le lieu et son maître", "state": "open",
                       "open_issues": 2, "closed_issues": 0})
    gh.ajouter_issue(60, "La caméra survole la ville", ("lot", "pret", "pc"), "J3 — Le lieu et son maître")
    gh.ajouter_issue(61, "La cellule se peuple de lieux", ("lot", "pret"), "J3 — Le lieu et son maître")
    r = journal.releve(gh, projet, MAINTENANT, journal_local=local, veille=veille)
    loin = next(l for l in r.texte.splitlines() if l.startswith("EN AVANCE, DU TROISIÈME JALON"))
    assert "J3 — Le lieu et son maître" in loin and "#60 « La caméra survole la ville » (pc)" in loin
    assert "#61 « La cellule se peuple de lieux » (vps)" in loin
    assert ("#60 La caméra survole la ville : il part quand le PC n'a plus rien dans J1 — Le pont "
            "ni dans J2 — Le geste revient.") in r.aujourd_hui
    assert ("#61 La cellule se peuple de lieux : il part quand le VPS n'a plus rien dans J1 — Le pont "
            "ni dans J2 — Le geste revient.") in r.aujourd_hui


def test_le_chroniqueur_doit_raconter_et_non_recopier(projet, gh, tmp_path):
    texte = prompts.chroniqueur(faits="LOTS LIVRÉS …")
    for debut in journal._ENTETES:
        assert debut in texte
    assert "pas le titre recopié" in texte and "compteurs de la chaîne" in texte
    assert "pour CE lot" in texte and "jamais la photo du monde à la place" in texte


def test_deux_urls_du_meme_fichier_ne_gardent_que_la_premiere():
    a = "https://raw.githubusercontent.com/moi/essai/journal/captures/a.png"
    b = "https://raw.githubusercontent.com/moi/essai/journal/captures/b.png"
    livres = [{"capture": a}, {"capture": b}]
    texte = journal._dedupliquer_images(
        f"![x]({a})\n![y]({b})\n", livres, lire=lambda _u: b"png-identique")
    assert a in texte and b not in texte
    assert livres[0]["capture"] == a and livres[1]["capture"] is None


def test_une_capture_identique_a_la_photo_du_monde_ne_se_repete_pas(projet, gh):
    # Le 2 octobre 2026, six cartes de lots étaient le même fichier que
    # monde-2026-10-02.png ; le chroniqueur les collait toutes.
    _preparer(gh)
    monde = "https://raw.githubusercontent.com/moi/essai/journal/captures/2026-09-28/monde-2026-09-28.png"
    lot = "https://raw.githubusercontent.com/moi/essai/journal/captures/a.png"
    corps = journal.ecrire(
        gh, projet, maintenant=MAINTENANT, executeur=Agents((1, "429 Too Many Requests")),
        photographe=lambda *a: [monde], lire_image=lambda u: b"png-identique")
    assert f"![le monde]({monde})" in corps
    assert lot not in corps
    assert corps.count("![") == 1


def test_deux_captures_differentes_restent(projet, gh):
    _preparer(gh)
    monde = "https://raw.githubusercontent.com/moi/essai/journal/captures/2026-09-28/monde-2026-09-28.png"
    lot = "https://raw.githubusercontent.com/moi/essai/journal/captures/a.png"

    def lire(url):
        return b"monde" if "monde" in url else b"lot"

    corps = journal.ecrire(
        gh, projet, maintenant=MAINTENANT, executeur=Agents((1, "429 Too Many Requests")),
        photographe=lambda *a: [monde], lire_image=lire)
    assert f"![le monde]({monde})" in corps
    assert f"![capture]({lot})" in corps


def test_une_image_illisible_reste(projet, gh):
    # On ne devine pas qu'une capture double une autre : si on n'a pas pu
    # la lire, elle reste.
    _preparer(gh)
    monde = "https://raw.githubusercontent.com/moi/essai/journal/captures/2026-09-28/monde-2026-09-28.png"
    lot = "https://raw.githubusercontent.com/moi/essai/journal/captures/a.png"

    def lire(_url):
        raise OSError("réseau")

    corps = journal.ecrire(
        gh, projet, maintenant=MAINTENANT, executeur=Agents((1, "429 Too Many Requests")),
        photographe=lambda *a: [monde], lire_image=lire)
    assert f"![le monde]({monde})" in corps
    assert f"![capture]({lot})" in corps


def test_le_chroniqueur_ne_colle_pas_deux_fois_la_meme_image(projet, gh):
    _preparer(gh)
    monde = "https://raw.githubusercontent.com/moi/essai/journal/captures/2026-09-28/monde-2026-09-28.png"
    lot = "https://raw.githubusercontent.com/moi/essai/journal/captures/a.png"
    double = JOURNAL_BIEN_ECRIT.replace(
        "![capture](https://raw.githubusercontent.com/moi/essai/journal/captures/a.png)",
        f"![le monde]({monde})\n![capture]({monde})")
    corps = journal.ecrire(
        gh, projet, maintenant=MAINTENANT, executeur=Agents((0, double)),
        photographe=lambda *a: [monde], lire_image=lambda u: b"png-identique")
    assert f"![le monde]({monde})" in corps
    assert corps.count(monde) == 1
    assert lot not in corps


def test_chaque_journal_porte_la_photo_du_monde(projet, gh):
    _preparer(gh)
    url = "https://raw.githubusercontent.com/moi/essai/journal/captures/2026-09-28/monde-2026-09-28.png"
    agents = Agents((1, "429 Too Many Requests"))
    corps = journal.ecrire(gh, projet, maintenant=MAINTENANT, executeur=agents, photographe=lambda *a: [url])
    assert f"![le monde]({url})" in corps


def test_le_journal_dit_quel_agent_refuse_l_appel(tmp_path):
    raisons = ["codeur : codex/gpt-5.6-sol@high : refuse l'appel (option, effort ou réglage) "
               "(« error: unknown option '--effort' »)"]
    gestes = journal._a_faire(raisons, [], tmp_path / "veille.txt", [])
    assert any("VPS : codex/gpt-5.6-sol@high refuse l'appel" in g and "atelier.toml" in g for g in gestes)
    assert journal._a_faire([], [], tmp_path / "veille.txt", []) == ["- rien"]


def test_le_journal_pose_la_question_du_chef(projet, gh):
    _preparer(gh)
    gh.ajouter_issue(13, "Les grandes villes", ("lot", "bloque"))
    q = lots.question_du_chef("- A :: un grenier de départ\n- B :: plafonner les villes\n"
                              "RECOMMANDATION :: A :: garde l'histoire", "Que faire des villes affamées ?")
    gh.issues_[13]["comments"].append({"body": "bloqué\n\n" + marque(
        role="pilote", etat="bloque", raison=f"question au propriétaire : {q.texte}", **q.marque())})
    a_faire = journal.faits(gh, projet, MAINTENANT).split("À FAIRE PAR LE PROPRIÉTAIRE")[1]
    assert ("#13 « Les grandes villes » attend ta décision : Que faire des villes affamées ? "
            "A : un grenier de départ ; B : plafonner les villes. Le chef recommande A (garde l'histoire).") in a_faire
    assert "Réponds par un commentaire sur l'issue #13 (une lettre suffit)" in a_faire
    # Un blocage sans question garde sa consigne, et dit qu'un commentaire suffit.
    assert "#11 bloqué : lire sa raison" in a_faire and "répondre par un commentaire sur l'issue" in a_faire


BRIEF_DU_GRENIER = """# Lot #9 — Le contrat
Jalon : J1

## But
Le monde garde ses réserves.

## Le joueur
Fond. Ton grenier se garde mal : les rats entament ta réserve. Ce lot prépare l'ouverture du grenier (#12).

## Règle du monde
`World.greniers` porte un panier par maison.
"""
CARTE_DU_LOT = "https://raw.githubusercontent.com/moi/essai/journal/captures/2026-09-27/lot-9-fffffff-carte.png"
TERRE = "https://raw.githubusercontent.com/moi/essai/journal/captures/2026-09-28/terre-2026-09-28.png"
FAIM = "https://raw.githubusercontent.com/moi/essai/journal/captures/2026-09-28/faim-2026-09-28.png"
RESERVES = "https://raw.githubusercontent.com/moi/essai/journal/captures/2026-09-28/nourriture-2026-09-28.png"


def _lot_du_grenier(projet, gh):
    _preparer(gh)
    (projet.racine / "docs" / "briefs").mkdir(parents=True)
    (projet.racine / "docs" / "briefs" / "9-le-contrat.md").write_text(BRIEF_DU_GRENIER, encoding="utf-8")
    gh.prs_[49]["comments"] = [{"body": f"📷 ![capture du lot #9]({CARTE_DU_LOT})"}]


def test_les_faits_disent_ce_que_le_joueur_y_gagne(projet, gh):
    _lot_du_grenier(projet, gh)
    texte = journal.faits(gh, projet, MAINTENANT)
    assert "Ce que le joueur y gagne (le brief) : Fond. Ton grenier se garde mal" in texte
    # La règle du monde, écrite pour le codeur, n'entre pas dans le récit.
    assert "World.greniers" not in texte
    # La carte d'Europe que le pilote prend de chaque lot ne montre pas ce lot.
    assert CARTE_DU_LOT not in texte


def test_un_lot_sans_brief_garde_le_compte_rendu_du_codeur(projet, gh, tmp_path):
    local, veille = _journee(gh, tmp_path)
    texte = journal.faits(gh, projet, MAINTENANT, journal_local=local, veille=veille)
    assert "Ce que le joueur y gagne" not in texte and "Le contrat ne connaît plus que `cell_id`" in texte


def test_un_lot_recoit_la_carte_de_son_sujet(projet, gh):
    _lot_du_grenier(projet, gh)
    demandees = []

    def photographe(_gh, _projet, _maintenant, lectures):
        demandees.append(lectures)
        return [TERRE, FAIM, RESERVES]

    corps = journal.ecrire(gh, projet, maintenant=MAINTENANT, executeur=Agents((1, "429 Too Many Requests")),
                           photographe=photographe, lire_image=lambda u: u.encode())
    # Un lot de grenier demande la carte des réserves, et elle va sous lui, pas en tête.
    assert demandees == [("nourriture",)]
    entete, lot = corps.split("**[#9 Le contrat]")
    assert f"![ta terre]({TERRE})" in entete and f"![la faim]({FAIM})" in entete and RESERVES not in entete
    assert f"![les réserves]({RESERVES})" in lot and "*Les réserves de nourriture" in lot
    assert "*Ta terre, cerclée de rouge" in entete
    # Le pilote écrit seul : il raconte le lot par son brief, et dit qu'il est de fond.
    assert ("Rien de visible encore, c'est la fondation de la suite : Ton grenier se garde mal : "
            "les rats entament ta réserve.") in lot
    assert CARTE_DU_LOT not in corps


def test_le_chroniqueur_recoit_les_images_et_leur_legende(projet, gh):
    _lot_du_grenier(projet, gh)
    agents = Agents((1, "429 Too Many Requests"))
    journal.ecrire(gh, projet, maintenant=MAINTENANT, executeur=agents,
                   photographe=lambda *a: [TERRE, RESERVES], lire_image=lambda u: u.encode())
    prompt = " ".join(agents.appels[0])
    assert f"![ta terre]({TERRE}) — Ta terre, cerclée de rouge" in prompt
    assert "IMAGES DES LOTS" in prompt and f"#9 Le contrat : ![les réserves]({RESERVES})" in prompt


def test_un_lot_qui_a_sa_capture_ne_recoit_pas_de_carte(projet, gh):
    _lot_du_grenier(projet, gh)
    unity = "https://raw.githubusercontent.com/moi/essai/journal/captures/2026-09-27/lot-9-fffffff-ksar.png"
    gh.prs_[49]["comments"] = [{"body": f"📷 ![capture du lot #9]({unity})"}]
    demandees = []
    corps = journal.ecrire(gh, projet, maintenant=MAINTENANT, executeur=Agents((1, "429")),
                           photographe=lambda *a: demandees.append(a[3]) or [TERRE],
                           lire_image=lambda u: u.encode())
    assert demandees == [()] and f"![capture]({unity})" in corps


def test_le_chroniqueur_parle_en_joueur():
    texte = prompts.chroniqueur(faits="LOTS LIVRÉS …")
    assert "Ce que le joueur y gagne" in texte and "langage de joueur" in texte
    assert "un tick est un jour" in texte and "rien entre accents graves" in texte
