"""Le samedi et le vendredi : le palier se décide et se montre, sur son issue.

Le défaut que ces tests gardent : le palier suivant se décidait hors de la
chaîne, et rien ne reliait ce que le propriétaire avait dit en jouant aux lots
ouverts le lundi. Tout se dit maintenant sur l'issue du palier : la note de
démo, la note du propriétaire, la proposition du CTO, le « oui ».
"""

from __future__ import annotations

import pytest

from atelier import lots, palier
from atelier.lots import Lot

from conftest import PALIER, Agents, piloter

FICHE = "## Ce que je joue de plus\nJe lève une armée.\n\n## Ce que je vois samedi\nUne armée sur la carte.\n"
QUOTA = {"code": 1, "brut": "", "erreur": "You've hit your 5-hour limit"}
NOTE = {"texte": "## Quoi essayer\nLève une armée, puis marche sur Biskra.\n\n## Ce qui marche\nLa levée.\n\n"
                 "## Ce qui manque\nLa caserne.\n\n## À revoir samedi\nRien.\n\n## Ce que la semaine a coûté\nPeu."}
PLAN = {"sortie": {"decision": "plan", "resume": "La paix.", "etapes": [
    {"titre": "Le traité", "quoi": "paix.py", "qui": "chef", "tests": "test_paix.py"}]}}
SUIVANT = "Palier 2 — La paix et les alliés"


def _fiche(titre, piste, **plus):
    return {"titre": titre, "piste": piste, "machine": "vps", "meneur": "chef", "joueur": f"Je joue : {titre}.",
            "samedi": f"Je vois : {titre}.", "regle": "Niveau 2.", "preuves": ["py -m pytest jeu/sim/tests/test_paix.py -q"],
            **plus}


def _proposition(*fiches, **plus):
    """Ce que rend le CTO le samedi : par défaut, un lot par piste, l'écran après la règle."""
    fiches = fiches or (_fiche("Traiter la paix", "monde"), _fiche("Les murs vus de la ville", "ville", machine="pc"),
                        _fiche("L'écran des relations", "interface", machine="pc", meneur="developpeur", apres=[1]))
    return {"sortie": {"palier_atteint": True, "titre": "La paix et les alliés", "but": "Le joueur traite la paix.",
                       "note": "La paix d'abord ; l'argent est reporté.", "fiches": list(fiches), **plus}}


@pytest.fixture
def gh(gh):
    """Un GitHub où le palier 1 a son issue, la #5."""
    gh.ajouter_issue(5, PALIER, ("palier",), corps="Ses lots : #10, #11, #12")
    return gh


def _semaine(gh):
    """Les lots du palier 1 : un livré, un en cours, un arrêté, un pas commencé ; et un lot d'un autre palier."""
    gh.ajouter_issue(10, "Lever une armée", ("lot", "livre", "monde"), corps=FICHE, etat="CLOSED")
    gh.ajouter_pr(50, "lot/10-lever-une-armee", etat="MERGED", commentaires=[
        lots.marque(role="chef", etat="plan", etapes=1, mesure={"cout": 1.5, "duree": 120})])
    gh.commenter_issue(10, lots.marque(role="cto", etat="decision", decision="trancher", a_revoir="un homme pour dix foyers"))
    gh.ajouter_issue(11, "Les frontières", ("lot", "en-cours", "interface", "pc"), corps=FICHE)
    gh.ajouter_pr(51, "lot/11-les-frontieres", commentaires=[
        lots.marque(role="chef", etat="plan", etapes=2), lots.marque(role="chef", etat="etape", etape=1, fini=True)])
    gh.ajouter_issue(12, "La caserne", ("lot", "bloque", "ville", "pc"), corps=FICHE)
    gh.commenter_issue(12, lots.marque(role="pilote", etat=lots.BLOQUE, raison="il faut une licence"))
    gh.ajouter_issue(13, "Les noms des pays", ("lot", "pret", "interface"), corps=FICHE)
    gh.ajouter_issue(14, "Abandonné", ("lot", "bloque", "monde"), corps=FICHE, etat="CLOSED")
    gh.ajouter_issue(20, "Le trésor", ("lot", "pret", "monde"), jalon="Palier 3 — L'argent", corps=FICHE)


def _samedi(pilote):
    gh = pilote.gh
    courant = lots.palier_courant(lots.paliers(gh.jalons()))
    return palier.samedi(pilote, courant, [Lot.de(i) for i in gh.issues("open")], [Lot.de(i) for i in gh.issues("closed")])


def _propose(projet, gh, depot, tmp_path, *suite, proposition=None, note="La guerre se joue. Maintenant la paix, et des alliés."):
    """Le propriétaire a écrit sa note, et le CTO a proposé le palier suivant."""
    gh.commentaire_humain(5, note)
    agents = Agents(proposition or _proposition(), *suite)
    pilote = piloter(projet, gh, depot, agents, tmp_path)
    assert _samedi(pilote) is True
    return pilote, agents


def _marques(gh, numero=5):
    return lots.marques(gh.issues_[numero]["comments"])


# --------------------------------------------------------------- l'accord
@pytest.mark.parametrize("texte", ["oui", "OK", "oui, lance", "Go !", "  Oui.\n", "d'accord", "Validé", "c'est bon, vas-y"])
def test_un_mot_vaut_accord(texte):
    assert palier.est_un_accord(texte)


@pytest.mark.parametrize("texte", [
    "non", "", None, "Pas la paix : je veux d'abord l'argent, et la caserne dans la ville.",
    "oui mais la caserne d'abord et aussi les alliés avant la paix, et retire l'écran des relations de la liste",
    "Je dis oui", "ouistiti", "okay", "Lancement repoussé"])
def test_une_reorientation_un_refus_ou_un_long_oui_mais_ne_vaut_pas_accord(texte):
    assert not palier.est_un_accord(texte)


def test_l_issue_du_palier_est_la_plus_recente_qui_porte_l_etiquette(gh):
    gh.ajouter_issue(6, SUIVANT, ("palier",), jalon=SUIVANT)
    gh.ajouter_issue(7, "Palier 3 — un lot qui en parle", ("lot", "pret", "monde"))
    ouvertes = [Lot.de(i) for i in gh.issues("open")]
    assert palier.issue_du_palier(gh, ouvertes).numero == 6
    assert palier.issue_du_palier(gh, [l for l in ouvertes if l.numero == 7]) is None


# -------------------------------------------------------------- le samedi
def test_sans_note_du_proprietaire_le_cto_n_est_pas_appele(projet, gh, depot, tmp_path):
    gh.commenter_issue(5, "# La démo du palier 1\n\n" + lots.marque(role="cto", etat=palier.DEMO, jour="2026-11-13"))
    gh.commentaire_humain(5, "Un robot passe.", auteur="github-actions[bot]")
    agents = Agents()
    pilote = piloter(projet, gh, depot, agents, tmp_path)
    avant = list(gh.gestes)
    assert _samedi(pilote) is False and pilote.tour() == ["RIEN"]
    assert agents.appels == [] and gh.gestes == avant


def test_sans_issue_de_palier_le_samedi_ne_fait_rien(projet, gh, depot, tmp_path):
    gh.issues_[5]["state"] = "CLOSED"
    agents = Agents()
    assert _samedi(piloter(projet, gh, depot, agents, tmp_path)) is False and agents.appels == []


def test_la_note_du_proprietaire_appelle_le_cto_en_lecture_seule(projet, gh, depot, tmp_path):
    _, agents = _propose(projet, gh, depot, tmp_path)
    argv = agents.appels[0]["argv"]
    assert agents.modeles() == ["fable"] and agents.appels[0]["cwd"] == projet.racine
    assert argv[argv.index("--permission-mode") + 1] == "default"
    assert "Edit" in argv[argv.index("--disallowedTools") + 1]
    assert '"palier_atteint"' in argv[argv.index("--json-schema") + 1] and '"fiches"' in argv[argv.index("--json-schema") + 1]


def test_la_consigne_du_samedi_porte_la_note_l_etat_des_lots_et_les_choix_a_revoir(projet, gh, depot, tmp_path):
    _semaine(gh)
    gh.commenter_issue(5, "# La démo du palier 1\n\n" + lots.marque(role="cto", etat=palier.DEMO, jour="2026-11-13"))
    gh.issues_[5]["comments"].insert(0, {"body": "Une vieille idée, d'avant la démo.", "author": {"login": "moi"}})
    _, agents = _propose(projet, gh, depot, tmp_path)
    consigne = agents.appels[0]["consigne"]
    for attendu in ("Tire de sa note le palier 2", "La guerre se joue. Maintenant la paix, et des alliés.",
                    "- #10 « Lever une armée » (monde) : livré", "  Ce que je joue de plus : Je lève une armée.",
                    "- #11 « Les frontières » (interface) : en cours, étape 2 sur 2",
                    "- #12 « La caserne » (ville) : arrêté : il faut une licence",
                    "- #13 « Les noms des pays » (interface) : pas commencé",
                    "- #14 « Abandonné » (monde) : fermé sans être livré",
                    "- #10 Lever une armée : un homme pour dix foyers"):
        assert attendu in consigne
    assert "Le trésor" not in consigne, "un lot d'un autre palier n'est pas de celui-ci"
    assert "Une vieille idée" not in consigne, "la note part de la démo"
    assert "Ta proposition précédente" not in consigne


def test_la_proposition_est_posee_lisible_sur_l_issue_du_palier(projet, gh, depot, tmp_path):
    pilote, _ = _propose(projet, gh, depot, tmp_path)
    pose = gh.issues_[5]["comments"][-1]["body"]
    for attendu in ("🤖 **CTO** (claude/fable@high) propose le palier suivant.", "## " + SUIVANT, "Le joueur traite la paix.",
                    "### 1. Traiter la paix\n*monde · vps · mené par le chef de lot*",
                    "### 3. L'écran des relations\n*interface · pc · mené par le développeur seul · après 1*",
                    "**Ce que je joue de plus** : Je joue : Les murs vus de la ville.",
                    "**Ce que je vois samedi** : Je vois : Les murs vus de la ville.",
                    "- py -m pytest jeu/sim/tests/test_paix.py -q",
                    "### Ce que j'ai fait de ta note\nLa paix d'abord ; l'argent est reporté.", "**Réponds « oui »**"):
        assert attendu in pose
    assert "⚠️" not in pose
    assert pilote.lignes[-1] == "#5 palier proposé [claude/fable@high] — palier 2, 3 lot(s)"
    assert not [g for g in gh.gestes if g[0] in ("creer_issue", "creer_jalon")], "rien ne s'ouvre avant le « oui »"


def test_la_marque_de_la_proposition_porte_les_fiches_et_ce_qu_elle_a_coute(projet, gh, depot, tmp_path):
    _propose(projet, gh, depot, tmp_path, proposition=_proposition(
        _fiche("Traiter la paix", "monde"), {"piste": "ville", "joueur": "une fiche sans titre"}, "pas une fiche",
        _fiche("Les murs vus de la ville", "ville"), _fiche("L'écran des relations", "interface")))
    marque = _marques(gh)[-1]
    assert (marque["role"], marque["etat"], marque["machine"]) == ("cto", palier.PROPOSITION, "vps")
    assert marque["mesure"]["cout"] == 0.5
    assert [f["titre"] for f in marque["sortie"]["fiches"]] == ["Traiter la paix", "Les murs vus de la ville",
                                                               "L'écran des relations"], "une fiche sans titre est écartée"
    assert marque["sortie"]["fiches"][0]["joueur"] == "Je joue : Traiter la paix." and marque["sortie"]["palier_atteint"]


def test_une_proposition_a_laquelle_il_manque_une_piste_le_dit(projet, gh, depot, tmp_path):
    _propose(projet, gh, depot, tmp_path, proposition=_proposition(_fiche("Traiter la paix", "monde")))
    assert ("⚠️ Aucun lot sur : ville, interface. Un palier avance sur les trois pistes."
            in gh.issues_[5]["comments"][-1]["body"])


def test_une_fois_la_proposition_posee_le_cto_attend_la_reponse(projet, gh, depot, tmp_path):
    pilote, agents = _propose(projet, gh, depot, tmp_path)
    assert _samedi(pilote) is False and len(agents.appels) == 1


def test_si_le_proprietaire_corrige_le_cto_repropose_avec_sa_proposition_d_avant(projet, gh, depot, tmp_path):
    pilote, agents = _propose(projet, gh, depot, tmp_path, _proposition(_fiche("Traiter la paix", "monde"), titre="La paix"))
    gh.commentaire_humain(5, "Retire les alliés et l'écran des relations : la paix seule.")
    assert _samedi(pilote) is True and agents.modeles() == ["fable", "fable"]
    consigne = agents.appels[1]["consigne"]
    for attendu in ("Ta proposition précédente", "### 3. L'écran des relations", "Ce que le propriétaire en a dit",
                    "Retire les alliés et l'écran des relations : la paix seule.",
                    "La guerre se joue. Maintenant la paix, et des alliés."):
        assert attendu in consigne
    propositions = [m for m in _marques(gh) if m.get("etat") == palier.PROPOSITION]
    assert [m["sortie"]["titre"] for m in propositions] == ["La paix et les alliés", "La paix"]
    assert "## Palier 2 — La paix" in gh.issues_[5]["comments"][-1]["body"]


def test_le_oui_ouvre_le_palier_sans_appeler_personne(projet, gh, depot, tmp_path):
    pilote, agents = _propose(projet, gh, depot, tmp_path)
    gh.commentaire_humain(5, "Oui, lance.")
    assert _samedi(pilote) is False and len(agents.appels) == 1, "aucun agent n'est appelé pour ouvrir"
    assert ("creer_jalon", SUIVANT) in gh.gestes
    assert [gh.issues_[n]["title"] for n in (101, 102, 103)] == ["Traiter la paix", "Les murs vus de la ville",
                                                                "L'écran des relations"]
    assert all(gh.issues_[n]["milestone"]["title"] == SUIVANT and gh.issues_[n]["state"] == "OPEN" for n in (101, 102, 103))
    assert pilote.lignes[-1] == f"#104 palier ouvert — {SUIVANT} : #101, #102, #103"


def test_chaque_lot_ouvert_a_ses_etiquettes_sa_fiche_et_ce_qu_il_attend(projet, gh, depot, tmp_path):
    pilote, _ = _propose(projet, gh, depot, tmp_path)
    gh.commentaire_humain(5, "oui")
    _samedi(pilote)
    assert gh.etiquettes(101) == ["lot", "pret", "monde"]
    assert gh.etiquettes(102) == ["lot", "pret", "ville", "pc"]
    assert gh.etiquettes(103) == ["lot", "pret", "interface", "pc", "simple"]
    relations = Lot.de(gh.issue(103))
    assert relations.dependances == {101} and "Dépend de : #101" in relations.corps
    assert not Lot.de(gh.issue(101)).dependances and not Lot.de(gh.issue(102)).dependances
    assert "## Ce que je joue de plus\nJe joue : L'écran des relations." in relations.corps
    assert "## Ce que je vois samedi\nJe vois : L'écran des relations." in relations.corps
    assert (relations.palier, relations.machine, relations.meneur) == (2, "pc", "developpeur")


def test_un_lot_qui_attend_une_fiche_placee_apres_lui_garde_sa_dependance(projet, gh, depot, tmp_path):
    ecran_d_abord = _proposition(_fiche("L'écran des relations", "interface", apres=[2]), _fiche("Traiter la paix", "monde"),
                                 _fiche("Les murs vus de la ville", "ville"))
    pilote, _ = _propose(projet, gh, depot, tmp_path, proposition=ecran_d_abord)
    assert "· après 2*" in gh.issues_[5]["comments"][-1]["body"]
    gh.commentaire_humain(5, "oui")
    _samedi(pilote)
    ecran = next(Lot.de(i) for i in gh.issues("open") if i["title"] == "L'écran des relations")
    regle = next(Lot.de(i) for i in gh.issues("open") if i["title"] == "Traiter la paix")
    assert ecran.dependances == {regle.numero}


def test_le_oui_ouvre_l_issue_du_palier_suivant_et_ferme_le_palier_joue(projet, gh, depot, tmp_path):
    pilote, _ = _propose(projet, gh, depot, tmp_path)
    gh.commentaire_humain(5, "oui")
    _samedi(pilote)
    nouvelle = gh.issues_[104]
    assert nouvelle["title"] == SUIVANT and gh.etiquettes(104) == ["palier"] and nouvelle["milestone"]["title"] == SUIVANT
    assert "Le joueur traite la paix." in nouvelle["body"] and "Ses lots : #101, #102, #103" in nouvelle["body"]
    assert ("epingler", 104) in gh.gestes and ("desepingler", 5) in gh.gestes
    assert gh.issues_[5]["state"] == "CLOSED" and ("fermer_jalon", 1) in gh.gestes
    assert [(p.numero, p.ouvert) for p in lots.paliers(gh.jalons())] == [(1, False), (2, True)]
    ouvertes = [Lot.de(i) for i in gh.issues("open")]
    assert palier.issue_du_palier(gh, ouvertes).numero == 104
    assert _samedi(pilote) is False and len([g for g in gh.gestes if g[0] == "creer_jalon"]) == 1, "le « oui » ne joue qu'une fois"


def test_un_oui_ouvre_la_derniere_proposition(projet, gh, depot, tmp_path):
    pilote, _ = _propose(projet, gh, depot, tmp_path, _proposition(_fiche("Traiter la paix", "monde"), titre="La paix"))
    gh.commentaire_humain(5, "Sans les alliés.")
    _samedi(pilote)
    gh.commentaire_humain(5, "ok")
    _samedi(pilote)
    assert ("creer_jalon", "Palier 2 — La paix") in gh.gestes
    assert [g[1] for g in gh.gestes if g[0] == "creer_issue"] == ["Traiter la paix", "Palier 2 — La paix"]


def test_un_oui_sans_proposition_n_ouvre_rien(projet, gh, depot, tmp_path):
    gh.commentaire_humain(5, "oui")
    pilote = piloter(projet, gh, depot, Agents(_proposition()), tmp_path)
    _samedi(pilote)
    assert not [g for g in gh.gestes if g[0] in ("creer_jalon", "creer_issue", "fermer_issue", "fermer_jalon")]
    assert gh.issues_[5]["state"] == "OPEN" and set(gh.issues_) == {5}


def test_quand_le_quota_manque_rien_n_est_pose_et_on_reessaie(projet, gh, depot, tmp_path):
    gh.commentaire_humain(5, "Maintenant la paix.")
    agents = Agents(QUOTA, _proposition())
    pilote = piloter(projet, gh, depot, agents, tmp_path)
    assert _samedi(pilote) is True
    assert gh.gestes == [] and _marques(gh) == [], "une attente ne laisse rien sur l'issue"
    assert any("attente" in l and "quota épuisé" in l for l in pilote.lignes)
    assert _samedi(pilote) is True and _marques(gh)[-1]["etat"] == palier.PROPOSITION


@pytest.mark.parametrize("reponse, raison", [
    ({"sortie": {"palier_atteint": True, "titre": "La paix", "but": "…", "note": "…", "fiches": []}}, "sans fiche"),
    ({"code": 1, "brut": "", "erreur": "panne"}, "code 1"), ({"coupe": True}, "coupé par son délai")])
def test_un_cto_qui_ne_rend_aucune_fiche_ne_pose_pas_de_proposition(projet, gh, depot, tmp_path, reponse, raison):
    gh.commentaire_humain(5, "Maintenant la paix.")
    pilote = piloter(projet, gh, depot, Agents(reponse), tmp_path)
    assert _samedi(pilote) is True
    assert pilote.lignes[-1].startswith("#5 CTO en échec") and raison in pilote.lignes[-1]
    assert not [m for m in _marques(gh) if m.get("etat") == palier.PROPOSITION]
    assert not [g for g in gh.gestes if g[0] in ("creer_issue", "creer_jalon")]


def test_un_cto_coupe_le_samedi_laisse_sa_mesure_sur_l_issue(projet, gh, depot, tmp_path):
    gh.commentaire_humain(5, "Maintenant la paix.")
    _samedi(piloter(projet, gh, depot, Agents({"coupe": True}), tmp_path))
    assert [m for m in _marques(gh) if m.get("role") == "cto" and m["mesure"].get("coupe")]


def test_le_oui_d_un_autre_que_le_proprietaire_n_ouvre_rien(projet, gh, depot, tmp_path):
    pilote, _ = _propose(projet, gh, depot, tmp_path)
    gh.commentaire_humain(5, "oui", auteur="un-inconnu")
    _samedi(pilote)
    assert "creer_jalon" not in gh.noms_des_gestes() and gh.issues_[5]["state"] == "OPEN"


def test_un_seul_tour_a_la_fois_fait_proposer_le_palier(projet, gh, depot, tmp_path):
    """Le défaut : le CTO travaillait encore à sa proposition quand le tour suivant, deux minutes plus tard, relisait
    la même note sans réponse et l'appelait de nouveau. Deux appels sont partis pour une seule note."""
    from atelier.verrous import AucunVerrou

    class UnAutreTourTientLePalier(AucunVerrou):
        gestes: list = []

        def prendre(self, nom):
            self.gestes.append(("prendre", nom))
            return nom != "palier"

        def lacher(self, nom):
            self.gestes.append(("lacher", nom))

    gh.commentaire_humain(5, "Maintenant la paix.")
    agents = Agents(_proposition())
    occupe = UnAutreTourTientLePalier()
    piloter(projet, gh, depot, agents, tmp_path, verrous=occupe).tour()
    assert agents.appels == [] and ("prendre", "palier") in occupe.gestes
    assert ("lacher", "palier") not in occupe.gestes, "on ne rend pas un verrou qu'on n'a pas pris"
    libre = piloter(projet, gh, depot, agents, tmp_path)
    libre.tour()
    assert agents.modeles() == ["fable"] and _marques(gh)[-1]["etat"] == palier.PROPOSITION


def test_le_verrou_du_palier_est_rendu_meme_si_le_samedi_casse(projet, gh, depot, tmp_path, monkeypatch):
    from atelier.github import GitHubErreur
    from atelier.verrous import AucunVerrou

    class Compte(AucunVerrou):
        tenus: list = []

        def prendre(self, nom):
            self.tenus.append(nom)
            return True

        def lacher(self, nom):
            self.tenus.remove(nom)

    def casse(*a, **k):
        raise GitHubErreur("GitHub ne répond pas")

    monkeypatch.setattr(palier, "samedi", casse)
    verrous = Compte()
    piloter(projet, gh, depot, Agents(), tmp_path, verrous=verrous).tour()
    assert "palier" not in verrous.tenus


# ------------------------------------------------- la suite, en semaine
def _vide(gh):
    """Les deux lots du palier 1 sont fermés, et sa démo n'est pas posée."""
    gh.ajouter_issue(10, "Lever une armée", ("lot", "livre", "monde"), corps=FICHE, etat="CLOSED")
    gh.ajouter_issue(11, "Les frontières", ("lot", "livre", "interface", "pc"), corps=FICHE, etat="CLOSED")


def _suite(pilote):
    gh = pilote.gh
    courant = lots.palier_courant(lots.paliers(gh.jalons()))
    return palier.suite(pilote, courant, [Lot.de(i) for i in gh.issues("open")], [Lot.de(i) for i in gh.issues("closed")])


SUITE = {"sortie": {"palier_atteint": False, "titre": "La guerre pour toute maison", "but": "Chaque maison lève.",
                    "note": "La paix attend samedi.",
                    "fiches": [_fiche("La caserne depuis la carte", "interface", machine="pc")]}}
RIEN_A_AJOUTER = {"sortie": {"palier_atteint": False, "titre": "", "but": "", "fiches": [],
                             "note": "Tout ce qui manque change une règle : samedi."}}


def test_un_palier_vide_avant_sa_demo_fait_proposer_sa_suite_par_le_cto(projet, gh, depot, tmp_path):
    """Le défaut : les lots du palier fermés en un jour et demi, rien ne rouvrait de travail avant le samedi,
    et la chaîne a tourné à vide quatre jours."""
    _vide(gh)
    agents = Agents(SUITE)
    pilote = piloter(projet, gh, depot, agents, tmp_path)
    assert _suite(pilote) is True and agents.modeles() == ["fable"]
    consigne = agents.appels[0]["consigne"]
    for attendu in ("Tous les lots du palier 1 sont fermés", "- #10 « Lever une armée » (monde) : livré",
                    "Reste dans le palier 1", "rends une liste de fiches vide"):
        assert attendu in consigne
    pose = gh.issues_[5]["comments"][-1]["body"]
    assert "propose la suite du palier" in pose and "## Palier 1, la suite — La guerre pour toute maison" in pose
    assert "### 1. La caserne depuis la carte" in pose and "pour ouvrir ces lots dans le palier en cours" in pose
    marque = _marques(gh)[-1]
    assert (marque["etat"], marque["suite"], marque["lots"]) == (palier.PROPOSITION, True, 2)
    assert pilote.lignes[-1] == "#5 suite proposée [claude/fable@high] — palier 1, 1 lot(s)"


def test_la_suite_ne_se_propose_qu_une_fois_par_vidage(projet, gh, depot, tmp_path):
    _vide(gh)
    agents = Agents(SUITE)
    pilote = piloter(projet, gh, depot, agents, tmp_path)
    _suite(pilote)
    assert _suite(pilote) is False and _samedi(pilote) is False and len(agents.appels) == 1


@pytest.mark.parametrize("prepare", [
    lambda gh: gh.ajouter_issue(12, "La caserne", ("lot", "en-cours", "ville", "pc"), corps=FICHE),
    lambda gh: (gh.issues_.pop(10), gh.issues_.pop(11)),
    lambda gh: gh.commenter_issue(5, "# La démo\n\n" + lots.marque(role="cto", etat=palier.DEMO, jour="2026-11-13")),
    lambda gh: gh.commentaire_humain(5, "Je regarde ça ce soir."),
], ids=["un lot reste ouvert", "le palier n'a jamais eu de lot", "la démo est posée", "le propriétaire a écrit"])
def test_la_suite_ne_se_propose_pas_hors_d_un_palier_vide_avant_sa_demo(projet, gh, depot, tmp_path, prepare):
    _vide(gh)
    prepare(gh)
    agents = Agents()
    assert _suite(piloter(projet, gh, depot, agents, tmp_path)) is False and agents.appels == []


def test_le_oui_ouvre_la_suite_dans_le_palier_en_cours_sans_le_fermer(projet, gh, depot, tmp_path):
    _vide(gh)
    agents = Agents(SUITE)
    pilote = piloter(projet, gh, depot, agents, tmp_path)
    _suite(pilote)
    gh.commentaire_humain(5, "oui")
    assert _samedi(pilote) is False and len(agents.appels) == 1, "aucun agent n'est appelé pour ouvrir"
    ouvert = gh.issues_[101]
    assert ouvert["title"] == "La caserne depuis la carte" and ouvert["milestone"]["title"] == PALIER
    assert {e["name"] for e in ouvert["labels"]} == {"lot", "pret", "interface", "pc"}
    assert gh.issues_[5]["state"] == "OPEN" and not [g for g in gh.gestes if g[0] in ("creer_jalon", "fermer_jalon")]
    assert _marques(gh)[-1] == {"role": "pilote", "etat": palier.SUITE_OUVERTE, "suite": True, "lots": 2}
    assert "la suite du palier est ouverte : #101." in gh.issues_[5]["comments"][-1]["body"]
    avant = list(gh.gestes)
    assert _samedi(pilote) is False and _suite(pilote) is False and gh.gestes == avant, "le oui n'ouvre qu'une fois"


def test_la_suite_se_repropose_quand_ses_propres_lots_sont_fermes_a_leur_tour(projet, gh, depot, tmp_path):
    _vide(gh)
    agents = Agents(SUITE, SUITE)
    pilote = piloter(projet, gh, depot, agents, tmp_path)
    _suite(pilote)
    gh.commentaire_humain(5, "oui")
    _samedi(pilote)
    assert _suite(pilote) is False, "son lot est ouvert : le palier n'est plus vide"
    gh.fermer_issue(101)
    assert _suite(pilote) is True and _marques(gh)[-1]["lots"] == 3


def test_si_le_proprietaire_corrige_la_suite_le_cto_la_refait_en_suite(projet, gh, depot, tmp_path):
    _vide(gh)
    agents = Agents(SUITE, SUITE)
    pilote = piloter(projet, gh, depot, agents, tmp_path)
    _suite(pilote)
    gh.commentaire_humain(5, "Ajoute la levée dans tous mes lieux.")
    assert _samedi(pilote) is True
    consigne = agents.appels[1]["consigne"]
    for attendu in ("Tous les lots du palier 1 sont fermés", "Ta proposition précédente",
                    "## Palier 1, la suite — La guerre pour toute maison", "Ajoute la levée dans tous mes lieux."):
        assert attendu in consigne
    assert _marques(gh)[-1]["suite"] is True and "creer_jalon" not in gh.noms_des_gestes()


def test_un_cto_qui_n_ajoute_rien_avant_la_demo_le_dit_et_n_est_pas_rappele(projet, gh, depot, tmp_path):
    _vide(gh)
    agents = Agents(RIEN_A_AJOUTER)
    pilote = piloter(projet, gh, depot, agents, tmp_path)
    assert _suite(pilote) is True
    pose = gh.issues_[5]["comments"][-1]["body"]
    assert "n'ajoute aucun lot au palier 1 avant sa démo" in pose and "Tout ce qui manque change une règle : samedi." in pose
    assert _marques(gh)[-1]["etat"] == palier.SUITE_OUVERTE
    assert _suite(pilote) is False and len(agents.appels) == 1


def test_un_cto_qui_ne_rend_pas_la_suite_est_rappele_une_fois_puis_plus(projet, gh, depot, tmp_path):
    _vide(gh)
    panne = {"code": 1, "brut": "", "erreur": "panne"}
    agents = Agents(panne, panne)
    pilote = piloter(projet, gh, depot, agents, tmp_path)
    assert _suite(pilote) is True and "Le pilote le rappelle au tour suivant." in gh.issues_[5]["comments"][-1]["body"]
    assert _suite(pilote) is True and "Il ne sera pas rappelé seul" in gh.issues_[5]["comments"][-1]["body"]
    assert _suite(pilote) is False and len(agents.appels) == 2


def test_une_suite_restee_sans_reponse_ne_s_ouvre_pas_au_oui_d_apres_la_demo(projet, gh, depot, tmp_path):
    _vide(gh)
    agents = Agents(SUITE, _proposition())
    pilote = piloter(projet, gh, depot, agents, tmp_path)
    _suite(pilote)
    gh.commenter_issue(5, "# La démo\n\n" + lots.marque(role="cto", etat=palier.DEMO, jour="2026-11-13"))
    gh.commentaire_humain(5, "oui")
    assert _samedi(pilote) is True, "sans proposition qui attende, le oui d'après la démo fait proposer le palier suivant"
    assert set(gh.issues_) == {5, 10, 11}, "la suite d'avant la démo est close : rien ne s'ouvre"
    assert "## Palier 2 — La paix et les alliés" in gh.issues_[5]["comments"][-1]["body"]


def test_le_tour_du_pilote_propose_la_suite_d_un_palier_vide(projet, gh, depot, tmp_path):
    _vide(gh)
    agents = Agents(SUITE)
    pilote = piloter(projet, gh, depot, agents, tmp_path)
    pilote.tour()
    assert agents.modeles() == ["fable"] and _marques(gh)[-1]["suite"] is True


# ------------------------------------------------------------ le vendredi
def test_le_vendredi_pose_la_note_du_cto_sur_l_issue_du_palier(projet, gh, depot, tmp_path):
    _semaine(gh)
    agents = Agents(NOTE)
    corps = palier.vendredi(piloter(projet, gh, depot, agents, tmp_path))
    pose = gh.issues_[5]["comments"][-1]["body"]
    assert pose.startswith(corps) and corps.startswith("# La démo du palier 1 — La première guerre\n")
    assert "Le build figé : `D:\\Forge\\builds\\palier-1\\Jouer.cmd`\n" in corps
    assert "## Quoi essayer\nLève une armée, puis marche sur Biskra." in corps
    assert corps.endswith("<sub>Écrit par le CTO (claude/fable@high).</sub>")
    marque = _marques(gh)[-1]
    assert (marque["role"], marque["etat"], marque["jour"]) == ("cto", palier.DEMO, "2026-11-16")
    assert marque["mesure"]["cout"] == 0.5
    argv = agents.appels[0]["argv"]
    assert agents.modeles() == ["fable"] and argv[argv.index("--permission-mode") + 1] == "default"


def test_le_vendredi_lance_le_build_fige_du_palier(projet, gh, depot, tmp_path):
    palier.vendredi(piloter(projet, gh, depot, Agents(NOTE), tmp_path))
    assert [g for g in gh.gestes if g[0] == "lancer_workflow"] == [("lancer_workflow", "build-nuit.yml", {"nom": "palier-1"})]


def test_la_note_du_vendredi_attend_que_le_build_soit_construit(projet, gh, depot, tmp_path, monkeypatch):
    """Le défaut : la note partait dès le build lancé, et disait « je ne sais pas si le build de ce soir a abouti »."""
    siestes = []
    monkeypatch.setattr(palier, "dormir", siestes.append)
    gh.builds_ = [None, {"status": "in_progress", "conclusion": None, "url": "https://x/run/9"},
                  {"status": "completed", "conclusion": "success", "url": "https://x/run/9"}]
    agents = Agents(NOTE)
    pilote = piloter(projet, gh, depot, agents, tmp_path)
    corps = palier.vendredi(pilote)
    assert siestes == [palier.PAS_DU_BUILD] * 2, "deux regards sans build fini, puis il l'est"
    assert gh.regards_du_build[0] == ("build-nuit.yml", "2026-11-16T09:58:00Z"), "deux minutes avant le lancement"
    assert ("LE BUILD FIGÉ : D:\\Forge\\builds\\palier-1 (lancer palier-1\\Jouer.cmd) — construit ce soir "
            "(https://x/run/9)\n") in agents.appels[0]["consigne"]
    assert "Le build figé : `D:\\Forge\\builds\\palier-1\\Jouer.cmd`\n" in corps
    assert any(l.startswith("#5 build figé") and "construit" in l for l in pilote.lignes)


@pytest.mark.parametrize("builds, fait, en_tete", [
    ([{"status": "completed", "conclusion": "failure", "url": "https://x/run/9"}],
     "⚠️ sa construction a échoué (https://x/run/9) : le dossier porte un build plus ancien, ou rien",
     "`D:\\Forge\\builds\\palier-1\\Jouer.cmd` (⚠️ sa construction a échoué : https://x/run/9)\n"),
    ([{"status": "queued", "conclusion": None, "url": "https://x/run/9"}] * 60,
     "⚠️ pas encore construit après 50 minutes d'attente (https://x/run/9)",
     "`D:\\Forge\\builds\\palier-1\\Jouer.cmd` (⚠️ pas encore construit quand cette note a été écrite)\n"),
], ids=["le build échoue", "le build ne finit pas"])
def test_un_build_rate_ou_inacheve_est_dit_au_cto_et_en_tete_de_la_note(projet, gh, depot, tmp_path, monkeypatch,
                                                                         builds, fait, en_tete):
    monkeypatch.setattr(palier, "dormir", lambda secondes: None)
    gh.builds_ = list(builds)
    agents = Agents(NOTE)
    corps = palier.vendredi(piloter(projet, gh, depot, agents, tmp_path))
    assert fait in agents.appels[0]["consigne"] and en_tete in corps
    assert len(gh.regards_du_build) <= palier.ATTENTE_DU_BUILD // palier.PAS_DU_BUILD + 1, "l'attente a une fin"
    assert _marques(gh)[-1]["etat"] == palier.DEMO, "une démo ne se tait jamais"


def test_le_run_du_build_est_le_dernier_lance_a_la_main_depuis_le_lancement():
    import json

    from atelier.github import GitHub

    runs = [{"status": "completed", "conclusion": "success", "url": "la-semaine-d-avant", "createdAt": "2026-11-13T17:15:00Z"},
            {"status": "in_progress", "conclusion": None, "url": "ce-soir", "createdAt": "2026-11-20T17:15:41Z"}]
    vus = []

    def executeur(argv, entree):
        vus.append(argv)
        return 0, json.dumps(runs), ""

    vrai = GitHub("moi/essai", executeur)
    assert vrai.run_lance("build-nuit.yml", "2026-11-20T17:13:00Z")["url"] == "ce-soir"
    assert vrai.run_lance("build-nuit.yml", "2026-11-20T18:00:00Z") is None, "GitHub ne montre pas encore le run"
    assert vus[0][vus[0].index("--event") + 1] == "workflow_dispatch" and "--json" in vus[0]


def test_la_consigne_du_vendredi_porte_l_etat_de_chaque_lot_les_choix_a_revoir_et_les_couts(projet, gh, depot, tmp_path):
    _semaine(gh)
    agents = Agents(NOTE)
    palier.vendredi(piloter(projet, gh, depot, agents, tmp_path))
    consigne = agents.appels[0]["consigne"]
    for attendu in ("Le build du palier 1 « La première guerre » est figé",
                    "LE BUILD FIGÉ : D:\\Forge\\builds\\palier-1 (lancer palier-1\\Jouer.cmd)",
                    "- #10 « Lever une armée » (monde) : livré", "  Ce que je vois samedi : Une armée sur la carte.",
                    "- #11 « Les frontières » (interface) : en cours, étape 2 sur 2",
                    "- #12 « La caserne » (ville) : arrêté : il faut une licence",
                    "- #13 « Les noms des pays » (interface) : pas commencé",
                    "À REVOIR SAMEDI :\n- #10 Lever une armée : un homme pour dix foyers",
                    "CE QUE LA SEMAINE A COÛTÉ :\n| rôle | appels |", "| chef | 1 | 2 min | 1.50 $ | — |",
                    "| #10 Lever une armée | 1 | 2 min | 1.50 $ | — |"):
        assert attendu in consigne
    assert "Le trésor" not in consigne


@pytest.mark.parametrize("reponse, pourquoi", [
    ({"code": 1, "brut": "", "erreur": "panne"}, "code 1"), (QUOTA, "quota épuisé"),
    ({"texte": "Tout marche, bon jeu !"}, "Le CTO n'a pas rendu sa note")])
def test_si_le_cto_se_tait_ou_sort_du_gabarit_les_faits_sont_poses_tels_quels(projet, gh, depot, tmp_path, reponse, pourquoi):
    _semaine(gh)
    corps = palier.vendredi(piloter(projet, gh, depot, Agents(reponse), tmp_path))
    assert gh.issues_[5]["comments"][-1]["body"].startswith(corps)
    for attendu in ("Le CTO n'a pas rendu sa note", pourquoi, "LES LOTS DU PALIER :\n- #10 « Lever une armée » (monde) : livré",
                    "À REVOIR SAMEDI :\n- #10 Lever une armée : un homme pour dix foyers", "| chef | 1 | 2 min | 1.50 $ | — |",
                    "<sub>Écrit par le pilote, à partir des faits.</sub>"):
        assert attendu in corps
    assert "bon jeu" not in corps and _marques(gh)[-1]["etat"] == palier.DEMO, "une démo ne se tait jamais"


def test_une_seconde_fois_le_meme_jour_ne_repose_rien(projet, gh, depot, tmp_path):
    agents = Agents(NOTE)
    pilote = piloter(projet, gh, depot, agents, tmp_path)
    palier.vendredi(pilote)
    avant = list(gh.gestes)
    assert palier.vendredi(pilote) == "RIEN — la note de démo du 2026-11-16 est déjà posée"
    assert gh.gestes == avant and len(agents.appels) == 1 and len(gh.issues_[5]["comments"]) == 1


def test_le_lendemain_la_note_se_repose(projet, gh, depot, tmp_path):
    gh.commenter_issue(5, "# La démo d'hier\n\n" + lots.marque(role="cto", etat=palier.DEMO, jour="2026-11-15"))
    palier.vendredi(piloter(projet, gh, depot, Agents(NOTE), tmp_path))
    assert [m["jour"] for m in _marques(gh)] == ["2026-11-15", "2026-11-16"]


def test_pc_en_pause_le_build_n_est_pas_lance_et_la_note_le_dit(projet, gh, depot, tmp_path):
    gh.variables_["PC_ACTIF"] = "non"
    corps = palier.vendredi(piloter(projet, gh, depot, Agents(NOTE), tmp_path))
    assert "lancer_workflow" not in gh.noms_des_gestes()
    assert "`D:\\Forge\\builds\\palier-1\\Jouer.cmd` (le PC est en pause : il n'a pas été construit)" in corps
    assert "## Quoi essayer" in corps and _marques(gh)[-1]["etat"] == palier.DEMO


def test_sans_publication_le_vendredi_ne_touche_pas_github(projet, gh, depot, tmp_path):
    corps = palier.vendredi(piloter(projet, gh, depot, Agents(NOTE), tmp_path), publication=False)
    assert "## Quoi essayer" in corps and gh.gestes == [] and gh.issues_[5]["comments"] == []


def test_sans_issue_de_palier_le_vendredi_ne_fait_rien(projet, gh, depot, tmp_path):
    gh.fermer_issue(5)
    agents = Agents()
    assert palier.vendredi(piloter(projet, gh, depot, agents, tmp_path)) == "RIEN — aucune issue de palier ouverte"
    assert agents.appels == [] and "lancer_workflow" not in gh.noms_des_gestes()


# ------------------------------------------------------ la semaine entière
def test_la_semaine_va_de_la_demo_du_vendredi_au_premier_lot_du_palier_suivant(projet, gh, depot, tmp_path):
    _semaine(gh)
    for numero in (11, 12, 13):
        gh.fermer_issue(numero)
    agents = Agents(NOTE, _proposition(), PLAN)
    pilote = piloter(projet, gh, depot, agents, tmp_path)

    # Vendredi soir : la note de démo, et le build figé.
    palier.vendredi(pilote)
    assert _marques(gh)[-1]["etat"] == palier.DEMO and pilote.tour() == ["RIEN"]

    # Samedi : le propriétaire joue et écrit ; le CTO propose.
    gh.commentaire_humain(5, "La guerre se joue. Maintenant la paix, et des alliés.")
    assert pilote.tour() == ["#5 appel [claude/fable@high] — cto : 0.50 $, 4 tours, 90 s",
                             "#5 palier proposé [claude/fable@high] — palier 2, 3 lot(s)"]
    assert "La guerre se joue." in agents.appels[1]["consigne"]
    assert pilote.tour() == ["RIEN"], "le CTO attend la réponse"

    # Le « oui » ouvre le palier 2 ; au tour suivant, son premier lot est pris.
    gh.commentaire_humain(5, "oui")
    assert pilote.tour() == [f"#104 palier ouvert — {SUIVANT} : #101, #102, #103"]
    assert lots.palier_courant(lots.paliers(gh.jalons())).numero == 2
    pilote.tour()
    assert "en-cours" in gh.etiquettes(101) and "pret" in gh.etiquettes(102) and "pret" in gh.etiquettes(103)
    assert agents.modeles() == ["fable", "fable", "opus"] and "Je joue : Traiter la paix." in agents.appels[2]["consigne"]
    assert any(p["headRefName"] == "lot/101-traiter-la-paix" for p in gh.prs_.values())
