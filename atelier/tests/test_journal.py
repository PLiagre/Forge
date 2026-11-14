"""Le journal du matin, et ce que la chaîne coûte.

Le défaut que ces tests gardent : le coût se lisait dans le journal local de
chaque machine. Celui d'un appel du PC ne remontait jamais au VPS, et un appel
coupé par son délai n'en écrivait aucun. Il se lit maintenant dans les marques
des commentaires, sur GitHub.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from atelier import journal, lots, pc
from atelier.journal import Mesure

from conftest import MAINTENANT, PALIER, Agents, piloter

FICHE = """## Ce que je joue de plus
Je lève une armée.

## Ce que je vois samedi
Une armée sur la carte.

## La règle du monde
Les soldats sont des habitants. Niveau 2.
"""
FORMULAIRE = "### Ce que je joue de plus\n\nJe trace une route.\n\n### Ce que je vois samedi\n\nUne route sur la carte.\n"
MATIN = MAINTENANT + timedelta(hours=1)
CE_MATIN = "2026-11-16T08:00:00Z"
PLAN = {"sortie": {"decision": "plan", "resume": "La levée.", "etapes": [
    {"titre": "La règle", "quoi": "armees.py", "qui": "chef", "tests": "test_armees.py"}]}}
FIDELE = """> **Avancé** : on lève enfin une armée.
> **Arrêté** : rien.
> **Pour toi** : rien.

### Ce qui a changé dans le jeu

**[Lever une armée](https://x/pull/50)**
Le lot #10 donne la levée : une armée paraît sur la carte.

### En route
- rien

### À revoir samedi
- rien"""


def _marque(role="chef", cout=0.5, duree=90, **champs):
    """La marque d'un appel mesuré, telle que le pilote la pose."""
    return lots.marque(role=role, agent="claude/x", machine="vps", mesure={"cout": cout, "duree": duree}, **champs)


def _mesure(lot, role, cout=0.5, duree=90, quand=MAINTENANT, **plus):
    return Mesure(lot=lot, role=role, quand=quand, mesure={"cout": cout, "duree": duree, **plus})


def _livre(gh, commentaires=()):
    """Le lot #10, livré ce matin par la PR #50 ; rend la liste des PR fusionnées que GitHub donnera."""
    gh.ajouter_issue(10, "Lever une armée", ("lot", "livre", "monde"), corps=FICHE, etat="CLOSED")
    gh.ajouter_pr(50, "lot/10-lever-une-armee", etat="MERGED", commentaires=commentaires)
    gh.prs_[50]["mergedAt"] = CE_MATIN
    fusionnees = [{"number": 50, "title": "Lot #10", "headRefName": "lot/10-lever-une-armee", "mergedAt": CE_MATIN,
                   "url": "https://x/pull/50"}]
    gh.json = lambda *a: fusionnees
    return fusionnees


def _arrete(gh, *marques_du_cto):
    """Le lot #12, arrêté faute de licence."""
    gh.ajouter_issue(12, "La caserne", ("lot", "bloque", "ville", "pc"), corps=FICHE)
    for texte in (lots.marque(role="pilote", etat=lots.BLOQUE, raison="il faut une licence"), *marques_du_cto):
        gh.commenter_issue(12, texte)


# -------------------------------------------------------------- la fiche
def test_une_section_se_lit_dans_la_fiche_comme_dans_le_formulaire():
    assert journal.section(FICHE, "Ce que je joue de plus") == "Je lève une armée."
    assert journal.section(FICHE, "La règle du monde") == "Les soldats sont des habitants. Niveau 2."
    assert journal.section(FORMULAIRE, "Ce que je vois samedi") == "Une route sur la carte."
    assert journal.section(FORMULAIRE.replace("\n", "\r\n"), "Ce que je joue de plus") == "Je trace une route."


def test_une_section_absente_est_vide():
    assert journal.section(FICHE, "Les preuves") == ""
    assert journal.section(FICHE, "Ce que je joue") == "", "un début de titre n'est pas le titre"
    assert journal.section("", "Ce que je joue de plus") == "" and journal.section(None, "Ce que je joue de plus") == ""


# ------------------------------------------------------------ les mesures
def test_seules_les_marques_d_un_role_qui_portent_une_mesure_comptent():
    commentaires = [{"body": _marque("chef", etat="plan") + "\n" + _marque("lecteur", cout=0.01)},
                    {"body": lots.marque(role="chef", etat="envoye")},
                    {"body": _marque("pilote")}, {"body": _marque("depanneur")},
                    {"body": lots.marque(role="chef", mesure="0,50 $")}, {"body": "Un mot du propriétaire."}]
    lues = journal.mesures_des_commentaires(10, commentaires)
    assert [(m.lot, m.role, m.cout, m.duree) for m in lues] == [(10, "chef", 0.5, 90), (10, "lecteur", 0.01, 90)]


def test_une_mesure_porte_la_date_de_son_commentaire():
    datee, sans_date, illisible = (journal.mesures_des_commentaires(10, [{"body": _marque(), **plus}])[0]
                                   for plus in ({"createdAt": "2026-11-16T09:30:00Z"}, {}, {"createdAt": "hier"}))
    assert datee.quand == datetime(2026, 11, 16, 9, 30, tzinfo=timezone.utc)
    assert sans_date.quand is None and illisible.quand is None


def test_les_mesures_d_un_lot_viennent_de_son_issue_et_de_sa_pr(projet, gh):
    gh.ajouter_issue(10, "Lever une armée")
    gh.commenter_issue(10, _marque("cto", cout=2.0, etat="decision"))
    gh.ajouter_pr(50, "lot/10-lever-une-armee", commentaires=[_marque("chef", etat="plan"), _marque("relecteur", cout=1.0)])
    gh.ajouter_issue(11, "Les frontières")
    gh.commenter_issue(11, _marque("chef", cout=0.25, etat="coupe"))
    lues = journal.mesures_des_lots(gh, projet, [10, 11])
    assert [(m.lot, m.role, m.cout) for m in lues] == [(10, "cto", 2.0), (10, "chef", 0.5), (10, "relecteur", 1.0),
                                                      (11, "chef", 0.25)]


# ------------------------------------------------------------- la table
def test_la_table_compte_et_additionne_par_role_par_lot_et_pour_tous():
    table = journal.table_des_couts([_mesure(10, "chef", 1.0, 600), _mesure(10, "chef", 0.5, 45),
                                     _mesure(11, "chef", 2.25, 15), _mesure(10, "relecteur", 0.75, 30),
                                     _mesure(11, "cto", 3.0, 6)], {10: "Lever une armée"}).splitlines()
    assert table[2:6] == ["| cto | 1 | 6 s | 3.00 $ | — |", "| chef | 3 | 11 min | 3.75 $ | — |",
                          "| relecteur | 1 | 30 s | 0.75 $ | — |", "| **tous** | 5 | 11 min | 7.50 $ | — |"]
    assert table[-2:] == ["| #10 Lever une armée | 3 | 11 min | 2.25 $ | — |", "| #11 | 2 | 21 s | 5.25 $ | — |"]
    assert not [l for l in table if l.startswith(("| developpeur", "| lecteur"))], "un rôle sans appel n'a pas de ligne"


def test_un_appel_coupe_est_compte_a_part_et_sans_cout():
    coupe = Mesure(lot=10, role="chef", quand=MAINTENANT, mesure={"coupe": True, "modeles": {"opus": {"sortie": 200}}})
    table = journal.table_des_couts([_mesure(10, "chef", 0.5, 90), coupe]).splitlines()
    assert coupe.cout == 0.0 and coupe.duree == 0
    assert table[2] == "| chef | 2 | 1 min | 0.50 $ | 1 |" and table[3] == "| **tous** | 2 | 1 min | 0.50 $ | 1 |"


def test_la_table_dit_ou_en_est_l_abonnement_au_dernier_appel():
    table = journal.table_des_couts([
        _mesure(10, "chef", quand=MAINTENANT, limites={"cinq_heures": 0.4, "semaine": 0.12}),
        _mesure(10, "chef", quand=MAINTENANT - timedelta(hours=5), limites={"cinq_heures": 0.9, "semaine": 0.05}),
        _mesure(10, "chef", quand=None, limites={"cinq_heures": 1.0, "semaine": 1.0})])
    assert table.splitlines()[-1] == ("Abonnement, au dernier appel : limite de cinq heures à 40%, limite hebdomadaire "
                                      "à 12% (elle était à 5% au premier appel compté).")
    muette = journal.table_des_couts([_mesure(10, "chef", limites={"cinq_heures": 0.4, "semaine": None})])
    assert muette.endswith("limite de cinq heures à 40%, limite hebdomadaire à non dite.")
    assert "Abonnement" not in journal.table_des_couts([_mesure(10, "chef")]), "sans limite dite, pas de ligne"


def test_sans_mesure_la_table_le_dit():
    assert journal.table_des_couts([]) == "Aucun appel mesuré."


def test_le_cout_d_un_appel_du_pc_et_d_un_appel_coupe_remonte_comme_les_autres(projet, gh, depot, tmp_path):
    """Le défaut : le coût d'un appel du PC restait dans le journal du PC, et un appel coupé n'en avait pas."""
    gh.ajouter_issue(10, "Lever une armée", corps=FICHE)
    gh.ajouter_issue(11, "La caserne", ("lot", "en-cours", "ville", "pc"), corps=FICHE)
    pilote = piloter(projet, gh, depot, Agents({**PLAN, "cout": 1.25}, {"coupe": True}), tmp_path)
    pilote.tour()
    pilote.tour()
    pc.travailler(projet, gh, depot, issue=11, journal=tmp_path / "pc.jsonl",
                  executeur_agents=Agents({**PLAN, "cout": 2.0}))
    mesures = journal.mesures_des_lots(gh, projet, [10, 11])
    assert [(m.lot, m.cout, bool(m.mesure.get("coupe"))) for m in mesures] == [(10, 1.25, False), (10, 0.0, True),
                                                                              (11, 2.0, False)]
    table = journal.couts_du_palier(gh, projet).splitlines()
    assert table[2] == "| chef | 3 | 3 min | 3.25 $ | 1 |"
    assert "| #11 La caserne | 1 | 1 min | 2.00 $ | — |" in table
    assert table[-1].startswith("Abonnement, au dernier appel : limite de cinq heures à 20%")


def test_le_cout_de_la_fiche_de_reparation_remonte(projet, gh, depot, tmp_path, monkeypatch):
    from atelier import traces
    monkeypatch.setattr(traces, "lire_run", lambda depot, run, lignes=80: "FAILED test_faim.py::test_soudure")
    gh.run_master = {"status": "completed", "conclusion": "failure", "databaseId": 77, "url": "https://x/run/77"}
    fiche = {"titre": "Réparer la soudure", "piste": "monde", "machine": "vps", "meneur": "chef",
             "joueur": "Tous les lots attendent.", "samedi": "master est vert", "regle": "faim.py", "preuves": ["pytest"]}
    piloter(projet, gh, depot, Agents({"sortie": fiche, "cout": 2.0}), tmp_path).tour()
    assert gh.issues_[101]["title"] == "Réparer la soudure"
    assert [(m.role, m.cout) for m in journal.mesures_des_lots(gh, projet, [101])] == [("cto", 2.0)]


def test_le_cout_du_cto_sur_l_issue_du_palier_est_compte(projet, gh):
    gh.ajouter_issue(5, PALIER, ("palier",))
    gh.commenter_issue(5, _marque("cto", cout=4.0, etat="proposition"))
    assert "| cto | 1 | 1 min | 4.00 $ | — |" in journal.couts_du_palier(gh, projet).splitlines()


# -------------------------------------------------- où en est chaque lot
def test_a_revoir_samedi_ne_garde_que_les_choix_que_le_cto_a_pris_seul():
    commentaires = [{"body": lots.marque(role="cto", etat="decision", decision="trancher", a_revoir="un homme pour dix foyers")},
                    {"body": lots.marque(role="cto", etat="decision", decision="relancer", a_revoir="  ")},
                    {"body": lots.marque(role="cto", etat="arbitrage", a_revoir="un arbitrage n'est pas un choix")},
                    {"body": lots.marque(role="chef", etat="decision", a_revoir="le chef ne décide pas")},
                    {"body": "à revoir samedi : un mot du propriétaire"}]
    assert journal.a_revoir_samedi(10, "Lever une armée", commentaires) == ["#10 Lever une armée : un homme pour dix foyers"]


def test_un_lot_en_cours_dit_son_plan_son_etape_sa_relecture_ou_sa_fusion():
    plan = {"role": "chef", "etat": "plan", "etapes": 2}
    faites = [plan, {"role": "chef", "etat": "etape", "etape": 1, "fini": True},
              {"role": "chef", "etat": "etape", "etape": 2, "fini": False}, {"role": "chef", "etat": "etape", "etape": 2, "fini": True}]
    assert journal.ou_en_est([]) == journal.ou_en_est([{"role": "chef", "etat": "coupe"}]) == "son plan s'écrit"
    assert journal.ou_en_est([plan]) == "étape 1 sur 2" and journal.ou_en_est(faites[:3], "attente") == "étape 2 sur 2"
    assert journal.ou_en_est(faites, "attente") == "ses tests tournent"
    assert journal.ou_en_est(faites, "rouge") == "en correction, la CI est rouge"
    assert journal.ou_en_est(faites, "vert") == "en relecture"
    corriger = faites + [{"role": "relecteur", "verdict": "CORRIGER"}]
    assert journal.ou_en_est(corriger, "vert") == "en correction après la relecture"
    assert journal.ou_en_est(corriger + [{"role": "relecteur", "verdict": "ACCEPTE"}], "vert") == "accepté, il attend sa fusion"


# -------------------------------------------------------------- le relevé
def test_le_releve_donne_la_fiche_d_un_lot_livre(projet, gh):
    fusionnees = _livre(gh)
    fusionnees.append({"number": 40, "title": "La veille", "headRefName": "lot/9-la-veille",
                       "mergedAt": "2026-11-15T10:59:00Z", "url": "u"})
    fusionnees.append({"number": 60, "title": "Refonte", "headRefName": "direct/refonte", "mergedAt": CE_MATIN, "url": "u"})
    r = journal.releve(gh, projet, MATIN)
    assert r.livres == [{"numero": 10, "titre": "Lever une armée", "url": "https://x/pull/50",
                         "joueur": "Je lève une armée.", "samedi": "Une armée sur la carte."}]
    for attendu in ("LE PALIER EN COURS : " + PALIER, "LOTS LIVRÉS DEPUIS 2026-11-15 11:00 UTC (1) :",
                    "- #10 « Lever une armée » — https://x/pull/50 (piste : monde)",
                    "  Ce que je joue de plus : Je lève une armée.", "  Ce que je vois samedi : Une armée sur la carte."):
        assert attendu in r.texte.splitlines()


def test_le_releve_dit_ou_en_est_un_lot_en_cours(projet, gh):
    gh.ajouter_issue(11, "Les frontières", ("lot", "en-cours", "interface", "pc"), corps=FICHE)
    gh.ajouter_issue(13, "Les noms des pays", ("lot", "en-cours", "interface"), corps=FICHE)
    gh.ajouter_issue(14, "Pas encore pris", ("lot", "pret", "monde"), corps=FICHE)
    gh.ajouter_pr(51, "lot/11-les-frontieres", ci="attente", commentaires=[
        lots.marque(role="chef", etat="plan", etapes=2), lots.marque(role="chef", etat="etape", etape=1, fini=True)])
    r = journal.releve(gh, projet, MATIN)
    assert r.en_cours == ["#11 « Les frontières » (interface) : étape 2 sur 2",
                          "#13 « Les noms des pays » (interface) : son plan s'écrit"]
    assert "- #11 « Les frontières » (interface) : étape 2 sur 2" in r.texte and "#14" not in r.texte


def test_le_releve_dit_la_raison_d_un_lot_arrete(projet, gh):
    _arrete(gh)
    r = journal.releve(gh, projet, MATIN)
    assert r.arretes == ["#12 « La caserne » : il faut une licence — le CTO le regarde"]
    assert r.pour_toi == [] and "- #12 « La caserne » : il faut une licence — le CTO le regarde" in r.texte


def test_un_lot_laisse_au_proprietaire_apparait_dans_pour_toi(projet, gh):
    _arrete(gh, lots.marque(role="cto", etat="decision", decision="proprietaire", pourquoi="une licence payante"))
    r = journal.releve(gh, projet, MATIN)
    assert r.arretes == ["#12 « La caserne » : il faut une licence — il attend le propriétaire"]
    assert r.pour_toi == ["#12 « La caserne » : le CTO te laisse la décision (une licence payante)"]
    assert "POUR LE PROPRIÉTAIRE :\n- #12 « La caserne » : le CTO te laisse la décision" in r.texte


def test_le_pc_en_pause_est_dit_au_proprietaire(projet, gh):
    assert journal.releve(gh, projet, MATIN).pour_toi == []
    gh.variables_["PC_ACTIF"] = "non"
    r = journal.releve(gh, projet, MATIN)
    assert r.pour_toi == ["le PC est en pause (PC_ACTIF = non) : les lots de la ville et de l'interface attendent"]
    assert "POUR LE PROPRIÉTAIRE :\n- le PC est en pause" in r.texte


def test_le_releve_rassemble_les_choix_du_cto_a_revoir_samedi(projet, gh):
    _livre(gh)
    gh.commenter_issue(10, lots.marque(role="cto", etat="decision", decision="trancher", a_revoir="un homme pour dix foyers"))
    gh.ajouter_issue(11, "Les frontières", ("lot", "en-cours", "interface"), corps=FICHE)
    gh.commenter_issue(11, lots.marque(role="cto", etat="decision", decision="relancer", a_revoir="les frontières en gris"))
    _arrete(gh, lots.marque(role="cto", etat="decision", decision="reporter", a_revoir="la caserne attend le kit"))
    r = journal.releve(gh, projet, MATIN)
    assert r.a_revoir == ["#10 Lever une armée : un homme pour dix foyers", "#11 Les frontières : les frontières en gris",
                          "#12 La caserne : la caserne attend le kit"]
    assert r.arretes == ["#12 « La caserne » : il faut une licence — reporté à samedi par le CTO"] and r.pour_toi == []
    assert "À REVOIR SAMEDI (les choix que le CTO a pris seul) :\n- #10 Lever une armée : un homme pour dix foyers" in r.texte


def test_le_releve_porte_la_table_des_couts_depuis_hier(projet, gh):
    _livre(gh, commentaires=[_marque("chef", cout=1.5, etat="plan"), _marque("relecteur", cout=0.5, verdict="ACCEPTE")])
    gh.prs_[50]["comments"].append({"body": _marque("chef", cout=40.0), "createdAt": "2026-11-12T08:00:00Z"})
    _arrete(gh, _marque("cto", cout=3.0, etat="decision", decision="reporter"))
    table = journal.releve(gh, projet, MATIN).couts.splitlines()
    assert "| **tous** | 3 | 4 min | 5.00 $ | — |" in table, "l'appel d'il y a quatre jours n'est pas compté"
    assert "| #10 Lever une armée | 2 | 3 min | 2.00 $ | — |" in table and "| #12 La caserne | 1 | 1 min | 3.00 $ | — |" in table
    assert "| **tous** | 4 | 6 min | 45.00 $ | — |" in journal.releve(gh, projet, MATIN, heures=24 * 7).couts.splitlines()
    gh.issues_.clear()
    gh.json = lambda *a: []
    assert journal.releve(gh, projet, MATIN).couts == "Aucun appel mesuré."


# ------------------------------------------------------------- la fidélité
def test_un_texte_hors_gabarit_est_infidele():
    assert journal.infidele(FIDELE, "#10 https://x/pull/50") is None
    sans_entete = FIDELE.replace("> **Pour toi** : rien.\n", "")
    assert journal.infidele(sans_entete, "#10") == "il sort du gabarit (> **Pour toi** : absent)"
    assert "### Ce qui a changé dans le jeu absent" in journal.infidele("Tout va bien.", "#10")


def test_un_texte_qui_cite_un_numero_absent_des_faits_est_infidele():
    assert journal.infidele(FIDELE, "- #11 « Les frontières »") == "il cite #10, que les faits ne donnent pas"
    assert journal.infidele(FIDELE + "\n- #7 et #99 avancent", "#10 #7") == "il cite #99, que les faits ne donnent pas"
    assert journal.infidele(FIDELE.replace("#10", "#50"), "#10 — https://x/pull/50") is None, "le numéro de la PR est un fait"


def test_la_redaction_du_pilote_tient_dans_le_gabarit(projet, gh):
    vide = journal.redaction_du_pilote(journal.Releve())
    assert journal.infidele(vide, "") is None and "> **Avancé** : rien de livré depuis hier." in vide
    _livre(gh)
    gh.ajouter_issue(11, "Les frontières", ("lot", "en-cours", "interface"), corps=FICHE)
    _arrete(gh, lots.marque(role="cto", etat="decision", decision="proprietaire", pourquoi="une licence, voir #12",
                            a_revoir="la caserne attend sa licence"))
    r = journal.releve(gh, projet, MATIN)
    redaction = journal.redaction_du_pilote(r)
    assert journal.infidele(redaction, r.texte) is None
    for attendu in ("> **Avancé** : Lever une armée.", "> **Arrêté** : #12 « La caserne » : il faut une licence",
                    "> **Pour toi** : #12 « La caserne » : le CTO te laisse la décision",
                    "**[Lever une armée](https://x/pull/50)**\nJe lève une armée.\nUne armée sur la carte.",
                    "### En route\n- #11 « Les frontières » (interface) : son plan s'écrit",
                    "### À revoir samedi\n- #12 La caserne : la caserne attend sa licence"):
        assert attendu in redaction


# ----------------------------------------------------------------- écrire
def test_le_texte_fidele_du_lecteur_est_garde(projet, gh, tmp_path):
    _livre(gh, commentaires=[_marque("chef", cout=1.5, etat="plan")])
    agents = Agents({"texte": FIDELE, "cout": 0.04})
    corps = journal.ecrire(gh, projet, maintenant=MATIN, executeur=agents, dossier=tmp_path)
    appel = agents.appels[0]
    assert appel["modele"] == "haiku" and appel["argv"][appel["argv"].index("--tools") + 1] == ""
    assert "--allowedTools" not in appel["argv"] and appel["cwd"] == tmp_path
    assert "- #10 « Lever une armée » — https://x/pull/50" in appel["consigne"]
    assert corps.startswith(FIDELE + "\n\n<details>")
    assert "<sub>Écrit par claude/haiku@medium. Ce journal a coûté 0.04 $ au prix de l'API.</sub>" in corps
    assert "| chef | 1 | 1 min | 1.50 $ | — |" in corps, "les coûts sont ajoutés par le pilote, pas par le lecteur"


@pytest.mark.parametrize("reponse, pourquoi", [
    ({"code": 1, "brut": "", "erreur": "panne"}, "Le lecteur n'a pas répondu (code 1)"),
    ({"texte": "Tout va bien, rien à signaler."}, "Le texte du lecteur (claude/haiku@medium) est écarté : il sort du gabarit"),
    ({"texte": FIDELE.replace("#10", "#77")}, "Le texte du lecteur (claude/haiku@medium) est écarté : il cite #77"),
], ids=["il se tait", "il sort du gabarit", "il invente un lot"])
def test_sans_texte_fidele_du_lecteur_le_pilote_ecrit_seul_et_le_dit(projet, gh, tmp_path, reponse, pourquoi):
    _livre(gh)
    corps = journal.ecrire(gh, projet, maintenant=MATIN, executeur=Agents(reponse), dossier=tmp_path)
    assert corps.startswith("> **Avancé** : Lever une armée.\n> **Arrêté** : rien.\n> **Pour toi** : rien.")
    assert pourquoi in corps and "Écrit par le pilote, à partir des faits." in corps
    assert "Tout va bien" not in corps and "paraît sur la carte" not in corps, "rien du texte écarté ne reste"
    assert gh.noms_des_gestes() == ["creer_issue", "epingler"], "un journal ne se tait jamais"


def test_publier_ouvre_une_issue_l_epingle_et_ferme_celle_d_avant(projet, gh, tmp_path):
    gh.ajouter_issue(90, "Journal du 15/11/2026", ("journal",), jalon=None)
    gh.ajouter_issue(91, "Un lot qui parle du journal", ("lot", "pret", "monde"))
    journal.ecrire(gh, projet, maintenant=MATIN, executeur=Agents({"texte": FIDELE.replace("#10", "")}), dossier=tmp_path)
    assert gh.issues_[101]["title"] == "Journal du 16/11/2026" and gh.etiquettes(101) == ["journal"]
    assert gh.issues_[101]["state"] == "OPEN" and gh.issues_[101]["body"].startswith("> **Avancé**")
    assert gh.gestes == [("creer_issue", "Journal du 16/11/2026"), ("desepingler", 90), ("fermer_issue", 90, False),
                         ("epingler", 101)]
    assert gh.issues_[90]["state"] == "CLOSED" and gh.issues_[91]["state"] == "OPEN"


def test_une_epingle_refusee_ne_retient_pas_le_journal(gh):
    def refuser(numero):
        raise RuntimeError("trois issues sont déjà épinglées")
    gh.ajouter_issue(90, "Journal de la veille", ("journal",), jalon=None)
    gh.epingler = gh.desepingler = refuser
    assert journal.publier(gh, "Journal du jour", "le corps") == 101
    assert gh.issues_[90]["state"] == "CLOSED" and gh.issues_[101]["body"] == "le corps"


def test_sans_publication_github_n_est_pas_touche(projet, gh, tmp_path):
    _livre(gh)
    corps = journal.ecrire(gh, projet, maintenant=MATIN, publication=False, executeur=Agents({"texte": FIDELE}),
                           dossier=tmp_path)
    assert corps.startswith(FIDELE) and gh.gestes == [] and set(gh.issues_) == {10}


def test_l_appel_du_lecteur_garde_sa_trace(projet, gh, tmp_path):
    agents = Agents({"texte": "Tout va bien."})
    journal.ecrire(gh, projet, maintenant=MATIN, publication=False, executeur=agents, dossier=tmp_path)
    assert agents.appels[0]["trace"] is not None


# -------------------------------------------------------------- le palier
def test_les_couts_du_palier_comptent_ses_lots_ouverts_et_fermes(projet, gh):
    gh.jalons_.insert(0, {"number": 7, "title": "Palier 0 — Le socle", "state": "closed"})
    gh.ajouter_issue(10, "Lever une armée", ("lot", "livre", "monde"), etat="CLOSED")
    gh.ajouter_pr(50, "lot/10-lever-une-armee", etat="MERGED", commentaires=[_marque("chef", cout=1.5)])
    gh.ajouter_issue(11, "Les frontières", ("lot", "en-cours", "interface"))
    gh.commenter_issue(11, _marque("cto", cout=3.0))
    gh.ajouter_issue(8, "Le socle", ("lot", "livre", "monde"), jalon="Palier 0 — Le socle", etat="CLOSED")
    gh.commenter_issue(8, _marque("chef", cout=100.0))
    gh.ajouter_issue(9, "Hors palier", ("lot", "pret", "monde"), jalon=None)
    gh.commenter_issue(9, _marque("chef", cout=100.0))
    table = journal.couts_du_palier(gh, projet).splitlines()
    assert table[2:5] == ["| cto | 1 | 1 min | 3.00 $ | — |", "| chef | 1 | 1 min | 1.50 $ | — |",
                          "| **tous** | 2 | 3 min | 4.50 $ | — |"]
    assert table[-2:] == ["| #10 Lever une armée | 1 | 1 min | 1.50 $ | — |", "| #11 Les frontières | 1 | 1 min | 3.00 $ | — |"]
    gh.jalons_[1]["state"] = "closed"
    assert journal.couts_du_palier(gh, projet) == "Aucun appel mesuré.", "sans palier ouvert, rien n'est compté"
