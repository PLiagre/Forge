"""L'état d'un lot, dérivé de GitHub, et la décision de l'action suivante."""

from __future__ import annotations

import pytest

from atelier import lots
from atelier.github import etat_des_controles
from atelier.lots import Lot, action_suivante, marque, marques


def _issue(numero, titre="Un lieu s'ouvre", etiquettes=("lot", "pret"), jalon="J1 — Le pont"):
    return {"number": numero, "title": titre, "body": "", "labels": [{"name": e} for e in etiquettes],
            "milestone": {"title": jalon} if jalon else None}


def test_un_lot_se_lit_dans_son_issue():
    lot = Lot.de(_issue(12, "Le service local lit un lieu", ("lot", "en-cours", "pc")))
    assert lot.etat == "en-cours" and lot.machine == "pc" and lot.jalon == 1
    assert lot.branche("lot/") == "lot/12-le-service-local-lit-un-lieu"
    assert lot.brief("docs/briefs") == "docs/briefs/12-le-service-local-lit-un-lieu.md"
    assert lots.slug("Élévation : « la » côte !") == "elevation-la-cote"


def test_les_marques_du_pilote_se_relisent_dans_les_commentaires():
    corps = f"texte\n\n{marque(role='relecteur', sha='abc', verdict='ACCEPTE')}"
    assert marques([{"body": corps}, {"body": "rien"}, {"body": "<!-- atelier {cassé -->"}]) == [
        {"role": "relecteur", "sha": "abc", "verdict": "ACCEPTE"}]


def test_le_jalon_courant_est_le_premier_ouvert():
    bruts = [{"number": 2, "title": "J2 — Le geste", "state": "open"},
             {"number": 1, "title": "J1 — Le pont", "state": "closed"},
             {"number": 9, "title": "Divers", "state": "open"}]
    assert lots.jalon_courant(lots.jalons(bruts)).numero == 2


def test_le_lot_suivant_pret_d_abord_puis_idee_et_machine_libre():
    liste = [Lot.de(_issue(5, etiquettes=("lot", "idee"))), Lot.de(_issue(9, etiquettes=("lot", "pret"))),
             Lot.de(_issue(3, etiquettes=("lot", "pret", "pc"))), Lot.de(_issue(1, jalon="J2 — x"))]
    assert lots.a_prendre(liste, 1, {"vps": True, "pc": True}).numero == 3
    assert lots.a_prendre(liste, 1, {"vps": True, "pc": False}).numero == 9
    assert lots.a_prendre(liste[:1], 1, {"vps": True, "pc": False}).numero == 5
    assert lots.a_prendre(liste, 1, {"vps": False, "pc": False}) is None
    assert lots.a_prendre(liste, None, {"vps": True, "pc": True}) is None


def _pr(**champs):
    base = {"number": 7, "state": "OPEN", "headRefOid": "tete", "mergeable": "MERGEABLE", "autoMergeRequest": None}
    base.update(champs)
    return base


FAIT = {"role": "codeur", "etat": "fait", "agent": "codex/sol", "sha": "tete"}


@pytest.mark.parametrize("pr,ci,liste,attendu", [
    (None, "vert", [], "chef"),
    (_pr(state="MERGED"), "vert", [], "livrer"),
    (_pr(state="CLOSED"), "vert", [], "bloquer"),
    (_pr(), "vert", [], "coder"),
    (_pr(mergeable="CONFLICTING"), "vert", [FAIT], "conflit"),
    (_pr(), "attente", [FAIT], "attendre_ci"),
    (_pr(), "rouge", [FAIT], "corriger_ci"),
    (_pr(), "vert", [FAIT], "relire"),
    (_pr(), "vert", [FAIT, {"role": "relecteur", "sha": "vieille", "verdict": "ACCEPTE"}], "relire"),
    (_pr(), "vert", [FAIT, {"role": "relecteur", "sha": "tete", "verdict": "ACCEPTE"}], "fusionner"),
    (_pr(autoMergeRequest={"x": 1}), "vert", [FAIT, {"role": "relecteur", "sha": "tete", "verdict": "ACCEPTE"}], "attendre_fusion"),
    (_pr(), "vert", [FAIT, {"role": "relecteur", "sha": "tete", "verdict": "CORRIGER"}], "corriger_relecture"),
])
def test_l_action_suivante(pr, ci, liste, attendu):
    assert action_suivante(pr, ci, liste, corrections_max=2).nom == attendu


def test_trois_passages_du_codeur_puis_bloque():
    trois = [FAIT, dict(FAIT, etat="fait"), dict(FAIT, etat="fait")]
    assert action_suivante(_pr(), "rouge", trois[:2], corrections_max=2).nom == "corriger_ci"
    action = action_suivante(_pr(), "rouge", trois, corrections_max=2)
    assert action.nom == "bloquer" and "2 correction" in action.raison
    verdict = {"role": "relecteur", "sha": "tete", "verdict": "CORRIGER"}
    assert action_suivante(_pr(), "vert", trois + [verdict], corrections_max=2).nom == "bloquer"
    echecs = [{"role": "codeur", "etat": "echec"}] * 3
    assert action_suivante(_pr(), "vert", echecs, corrections_max=2).nom == "bloquer"


def test_un_envoi_au_pc_attend_son_retour_puis_se_relance():
    envoi = {"role": "codeur_3d", "etat": "envoye"}
    assert action_suivante(_pr(), "vert", [envoi], corrections_max=2, role_codeur="codeur_3d",
                           heures_depuis_envoi_pc=2).nom == "attendre_pc"
    assert action_suivante(_pr(), "vert", [envoi], corrections_max=2, role_codeur="codeur_3d",
                           heures_depuis_envoi_pc=30).nom == "relancer_pc"
    retour = dict(FAIT, role="codeur_3d")
    assert action_suivante(_pr(), "vert", [envoi, retour], corrections_max=2, role_codeur="codeur_3d").nom == "relire"


ENVOI = {"role": "codeur_3d", "etat": "envoye"}
ATTENTE = {"role": "codeur_3d", "etat": "attente"}
ECHEC_PC = {"role": "codeur_3d", "etat": "echec", "agent": "cursor/opus-high"}


def test_une_attente_du_pc_ne_brule_pas_d_essai_et_se_renvoie_apres_une_heure():
    # Tous les agents du PC en attente (quota) : le PC le dit par une marque,
    # qui répond à l'envoi sans compter comme un passage du codeur.
    liste = [ENVOI, ATTENTE]
    assert action_suivante(_pr(), "vert", liste, corrections_max=2, role_codeur="codeur_3d",
                           heures_depuis_attente_pc=0.2).nom == "attendre_pc"
    renvoi = action_suivante(_pr(), "vert", liste, corrections_max=2, role_codeur="codeur_3d",
                             heures_depuis_attente_pc=1.2)
    assert (renvoi.nom, renvoi.essai) == ("coder", 0)
    # Trois attentes après un échec : un seul essai brûlé, le lot n'est pas bloqué.
    longue = [ENVOI, ECHEC_PC] + [ENVOI, ATTENTE] * 3
    action = action_suivante(_pr(), "vert", longue, corrections_max=2, role_codeur="codeur_3d",
                             heures_depuis_attente_pc=2)
    assert (action.nom, action.essai) == ("coder", 1)
    # Renvoyé après l'attente : on attend de nouveau la réponse du PC.
    assert action_suivante(_pr(), "vert", liste + [ENVOI], corrections_max=2, role_codeur="codeur_3d",
                           heures_depuis_envoi_pc=0.1, heures_depuis_attente_pc=1.2).nom == "attendre_pc"


def test_une_reprise_remet_les_compteurs_a_zero():
    reprise = {"role": "pilote", "etat": "reprise"}
    trois_echecs = [ENVOI, ECHEC_PC] * 3
    assert action_suivante(_pr(), "vert", trois_echecs, corrections_max=2, role_codeur="codeur_3d").nom == "bloquer"
    action = action_suivante(_pr(), "vert", trois_echecs + [reprise], corrections_max=2, role_codeur="codeur_3d")
    assert (action.nom, action.essai) == ("coder", 0)
    # Le travail déjà fait reste : un lot repris après trois « CORRIGER »
    # repart en correction de la dernière revue, pas de zéro.
    verdict = {"role": "relecteur", "sha": "tete", "verdict": "CORRIGER"}
    corrige = [FAIT, verdict, FAIT, verdict, FAIT, verdict]
    assert action_suivante(_pr(), "vert", corrige, corrections_max=2).nom == "bloquer"
    action = action_suivante(_pr(), "vert", corrige + [reprise], corrections_max=2)
    assert (action.nom, action.essai) == ("corriger_relecture", 0)


def test_les_echecs_du_chef_comptent_depuis_le_dernier_blocage():
    echec = {"role": "chef", "etat": "echec"}
    bloque = {"role": "pilote", "etat": "bloque"}
    assert lots.echecs_du_chef([echec, echec]) == 2
    assert lots.echecs_du_chef([echec, echec, bloque]) == 0
    assert lots.echecs_du_chef([echec, echec, bloque, echec]) == 1


def test_les_decoupes_imbriquees_retiennent_tous_leurs_ancetres():
    # #119 découpé en #183 et #184, puis #183 en #185 et #186 : tant que #185
    # est ouvert, ce qui dépend de #119 ou de #183 attend, même #184 fermé.
    ouvert = Lot.de(dict(_issue(185), body="Le lecteur.\n\nDécoupé du lot #183 par le chef."))
    ferme = Lot.de(dict(_issue(183), body="Le client.\n\nDécoupé du lot #119 par le chef."))
    assert lots.bloquantes([ouvert], [ferme]) == frozenset({185, 183, 119})
    assert lots.bloquantes([ouvert]) == frozenset({185, 183})
    # Une découpe qui se citerait elle-même ne boucle pas.
    boucle = Lot.de(dict(_issue(7), body="Découpé du lot #7 par le chef."))
    assert lots.bloquantes([boucle]) == frozenset({7})


def test_les_auteurs_d_un_lot():
    # Les familles de modèles qui ont écrit du code : codex/sol est d'OpenAI.
    liste = [FAIT, {"role": "codeur_3d", "etat": "fait", "agent": "claude/opus"},
             {"role": "codeur", "etat": "echec", "agent": "cursor/grok"}, {"role": "chef", "agent": "claude/x"}]
    assert lots.auteurs(liste) == frozenset({"gpt", "claude"})
    # Le même modèle par un autre outil est le même auteur.
    assert lots.auteurs([{"role": "codeur_3d", "etat": "fait", "agent": "cursor/claude-opus-5-5-high"}]) == {"claude"}


def _check(nom, status="COMPLETED", conclusion="SUCCESS", quand="2026-09-27T10:00:00Z"):
    return {"__typename": "CheckRun", "name": nom, "status": status, "conclusion": conclusion, "startedAt": quand}


def test_l_etat_des_controles_exiges():
    assert etat_des_controles({"statusCheckRollup": [_check("tests"), _check("gitleaks")]})[0] == "vert"
    assert etat_des_controles({"statusCheckRollup": [_check("tests")]})[0] == "attente"
    assert etat_des_controles({"statusCheckRollup": [_check("tests", conclusion="FAILURE"), _check("gitleaks")]})[0] == "rouge"
    assert etat_des_controles({"statusCheckRollup": [_check("tests", status="IN_PROGRESS", conclusion=""),
                                                     _check("gitleaks")]})[0] == "attente"
    # Un contrôle non exigé rouge ne retient rien ; un rejeu récent l'emporte.
    rejeu = [_check("tests", conclusion="FAILURE", quand="2026-09-27T09:00:00Z"), _check("tests"),
             _check("gitleaks"), _check("unity", conclusion="FAILURE")]
    assert etat_des_controles({"statusCheckRollup": rejeu})[0] == "vert"


def test_un_lot_attend_ses_dependances_ouvertes():
    service = Lot.de(dict(_issue(12, "Le service"), body=""))
    panneau = Lot.de(dict(_issue(13, "Le panneau", ("lot", "pret", "pc")), body="Ce qu'il fait.\n\nDépend de : #12, #9"))
    assert panneau.dependances == frozenset({12, 9})
    assert lots.a_prendre([panneau], 1, {"vps": True, "pc": True}, frozenset({12})) is None
    assert lots.a_prendre([panneau], 1, {"vps": True, "pc": True}, frozenset({14})).numero == 13
    # Le formulaire écrit « ### Dépend de », puis la valeur au paragraphe suivant.
    formulaire = "### Jalon\n\nJ1 — Le pont\n\n### Dépend de\n\n#3, #4\n\n### Ce que ça doit faire\n\nVoir #99."
    assert Lot.de(dict(_issue(14), body=formulaire)).dependances == frozenset({3, 4})
    # Une référence plus loin dans le texte n'est pas une dépendance.
    assert Lot.de(dict(_issue(15), body="Dépend de : #12\n\nDécoupé du lot #10.")).dependances == frozenset({12})


CAP = """# CAP

| # | jalon | le joueur |
|---|---|---|
| 1 | **Le pont** | ouvre un lieu |

## Jalon 1 — Le pont

Le joueur ouvre un lieu.

## Jalon 2 — Le monde de 1400

Le joueur choisit sa terre.

### Jalon 9 — un titre de niveau trois n'est pas un jalon

## La réserve

Les lots qui ne servent aucun jalon.
"""


def _lot(numero, etiquettes, jalon="J2 — Le monde de 1400", corps=""):
    return Lot.de({"number": numero, "title": "Un lot", "body": corps,
                   "labels": [{"name": e} for e in etiquettes], "milestone": {"title": jalon} if jalon else None})


def test_les_jalons_se_lisent_dans_les_sections_de_cap():
    assert lots.jalons_du_cap(CAP) == {1: "J1 — Le pont", 2: "J2 — Le monde de 1400"}
    assert lots.jalons_du_cap("# CAP\n") == {}


def test_l_accord_renomme_cree_et_ne_touche_pas_au_reste():
    bruts = [{"number": 1, "title": "J1 — Le pont", "state": "closed"},
             {"number": 2, "title": "J2 — Le geste revient", "state": "open"},
             {"number": 7, "title": "J7 — 1400 → 1900", "state": "open"}]
    assert lots.accord_des_jalons(CAP, bruts) == [
        ("renommer", 2, "J2 — Le geste revient", "J2 — Le monde de 1400"), ("creer", "Réserve")]
    # L'accord fait, il ne demande plus rien ; un CAP sans jalon ne demande rien.
    bruts[1]["title"] = "J2 — Le monde de 1400"
    assert lots.accord_des_jalons(CAP, bruts + [{"number": 8, "title": "Réserve", "state": "open"}]) == []
    assert lots.accord_des_jalons("# CAP\n", bruts) == []


def test_un_jalon_absent_se_cree_et_c_est_l_ouvert_qui_porte_le_titre():
    cap = "## Jalon 3 — Le lieu et son maître\n\n## Jalon 4 — La capitale\n"
    bruts = [{"number": 3, "title": "J3 — Ancien", "state": "closed"},
             {"number": 9, "title": "J3 — Moins ancien", "state": "open"}]
    assert lots.accord_des_jalons(cap, bruts) == [
        ("renommer", 9, "J3 — Moins ancien", "J3 — Le lieu et son maître"), ("creer", "J4 — La capitale")]


def test_un_jalon_qui_commence_sans_plan_se_decoupe_une_seule_fois():
    j2 = lots.Jalon(numero=2, titre="J2 — Le monde de 1400", id=2, ouvert=True, ouvertes=0, fermees=0)
    assert lots.a_decouper(j2, CAP, [])
    assert lots.a_decouper(j2, CAP, [_lot(5, ("lot", "idee")), _lot(6, ("lot", "bloque"))])
    # Déjà lancé : un lot prêt, en cours, livré, ou fusionné à l'instant.
    assert not lots.a_decouper(j2, CAP, [_lot(5, ("lot", "pret"))])
    assert not lots.a_decouper(j2, CAP, [], [_lot(5, ("lot", "livre"))])
    assert not lots.a_decouper(j2, CAP, [], [_lot(5, ("lot", "en-cours"))])
    # Sa découpe déjà ouverte, ou déjà faite.
    decoupe = _lot(7, ("lot", "pret"), corps=lots.corps_de_la_decoupe(j2, []))
    assert not lots.a_decouper(j2, CAP, [], [decoupe])
    # Un jalon que CAP.md ne décrit pas ne se devine pas.
    j5 = lots.Jalon(numero=5, titre="J5 — Les autres", id=5, ouvert=True, ouvertes=0, fermees=0)
    assert not lots.a_decouper(j5, CAP, [])
    assert not lots.a_decouper(None, CAP, [])


def test_la_decoupe_d_un_jalon_passe_apres_ses_lots_deja_ouverts():
    j3 = lots.Jalon(numero=3, titre="J3 — Le lieu et son maître", id=3, ouvert=True, ouvertes=2, fermees=0)
    lot = _lot(9, ("lot", "pret"), jalon=j3.titre, corps=lots.corps_de_la_decoupe(j3, [124, 125]))
    assert lot.dependances == frozenset({124, 125})
    assert lots.jalon_a_decouper_par(lot) == 3
    seul = _lot(9, ("lot", "pret"), jalon=j3.titre, corps=lots.corps_de_la_decoupe(j3, []))
    assert seul.dependances == frozenset()


def test_une_ligne_de_decoupe_dit_sa_machine_et_ce_qu_elle_attend():
    s = lots.sous_lot("La carte", "Unity montre les royaumes :: pc :: après 1, 3", "vps")
    assert (s.titre, s.quoi, s.machine, s.apres) == ("La carte", "Unity montre les royaumes", "pc", (1, 3))
    s = lots.sous_lot("Le Nil", "le fleuve arrose :: après rien :: vps", "pc")
    assert (s.quoi, s.machine, s.apres) == ("le fleuve arrose", "vps", ())
    s = lots.sous_lot("L'aridité", "le moteur apprend", "vps")
    assert (s.quoi, s.machine, s.apres) == ("le moteur apprend", "vps", None)
    assert lots.sous_lot("x", "y :: Après : #2 et #1", "vps").apres == (2, 1)


def test_les_sous_lots_n_attendent_que_ce_qu_ils_disent():
    sous = [lots.sous_lot("a", "a", "vps"), lots.sous_lot("b", "b :: après rien", "vps"),
            lots.sous_lot("c", "c", "vps"), lots.sous_lot("d", "d :: après 1, 2", "vps")]
    # Sans « après », le précédent (l'ordre du chef, comme avant).
    assert lots.dependances_des_sous_lots(sous) == [(), (), (2,), (1, 2)]
    # Le dernier d'une découpe de jalon porte la preuve : il attend tout.
    assert lots.dependances_des_sous_lots(sous, preuve_en_dernier=True) == [(), (), (2,), (1, 2, 3)]


@pytest.mark.parametrize("ligne", ["d :: après 4", "d :: après 5", "d :: après 0"])
def test_une_dependance_qui_ne_precede_pas_se_refuse(ligne):
    sous = [lots.sous_lot(t, t, "vps") for t in "abc"] + [lots.sous_lot("d", ligne, "vps")]
    with pytest.raises(ValueError, match="sous-lot 4"):
        lots.dependances_des_sous_lots(sous)
