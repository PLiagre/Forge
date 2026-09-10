"""Une demande de lot se lit, ou se refuse. Jamais elle ne se devine."""

import pytest

from outils import saisie

GABARIT = """### Titre du lot

{titre}

### Couche

{couche}

### Dépend de

{depend}

### Ce que ça ouvre, et pourquoi maintenant

peu importe
"""


def demande(titre="Les routes relient les villes", couche="2 — Villes", depend="_No response_"):
    return saisie.lire(GABARIT.format(titre=titre, couche=couche, depend=depend))


def test_une_demande_complete_se_lit():
    d = demande(depend="047, 051")
    assert d.titre == "Les routes relient les villes"
    assert d.couche == "2"
    assert d.depend_de == ("047", "051")


def test_la_couche_se_lit_dans_le_libelle_du_formulaire():
    """Le formulaire affiche « 2 — Villes » ; la fiche ne porte que « 2 »."""
    assert demande(couche="4 — Armées").couche == "4"
    assert demande(couche="1 — Monde vivant").couche == "1"


def test_aucune_couche_est_une_reponse():
    assert demande(couche="aucune").couche is None


def test_une_couche_inconnue_est_un_refus():
    with pytest.raises(saisie.DemandeIllisible, match="couche"):
        demande(couche="9 — la couche des rêves")


def test_sans_dependance_la_liste_est_vide():
    assert demande(depend="_No response_").depend_de == ()
    assert demande(depend="").depend_de == ()
    assert demande(depend="—").depend_de == ()


def test_une_dependance_illisible_est_un_refus():
    with pytest.raises(saisie.DemandeIllisible, match="illisible"):
        demande(depend="le lot de la mer")


def test_un_suffixe_bis_reste_une_dependance_valable():
    assert demande(depend="043-bis").depend_de == ("043-bis",)


def test_une_dependance_repetee_ne_compte_qu_une_fois():
    assert demande(depend="047, 047").depend_de == ("047",)


def test_un_lot_sans_titre_n_est_pas_un_lot():
    with pytest.raises(saisie.DemandeIllisible, match="titre"):
        demande(titre="_No response_")


def test_un_formulaire_d_un_autre_gabarit_est_un_refus():
    """Une demande écrite à la main, ou avec un gabarit modifié, ne doit
    pas produire une fiche à moitié remplie."""
    with pytest.raises(saisie.DemandeIllisible, match="formulaire"):
        saisie.lire("Je voudrais que les villes aient des routes, merci")


def test_le_titre_sur_plusieurs_lignes_se_recolle():
    assert demande(titre="Les routes\nrelient les villes").titre == "Les routes relient les villes"


def test_le_slug_perd_les_accents_et_la_ponctuation():
    assert saisie.slug("L'été : la mer, enfin !") == "l-ete-la-mer-enfin"


def test_le_slug_ne_deborde_pas():
    """Un nom trop long finit tronqué par un outil ou un autre, et ce
    jour-là la fiche et le brief ne se ressemblent plus."""
    long = saisie.slug("Les habitants construisent des maisons quand ils ont de quoi "
                       "les payer et de la place où les mettre")
    assert len(long) <= 48
    assert not long.endswith("-")


def test_un_titre_sans_lettre_ne_donne_pas_de_nom():
    with pytest.raises(saisie.DemandeIllisible):
        saisie.slug("!!! ???")


def test_la_fiche_produite_est_relue_par_le_lecteur_du_registre():
    feuille = pytest.importorskip(
        "atelier.feuille",
        reason="ForgeAtelier hors du PYTHONPATH : le lecteur du registre manque",
    )
    from outils import palier

    d = demande(depend="047")
    texte = (
        f"# titre\n\n{feuille.REPERE_DEBUT}\n\n"
        "### [047 — Le bourg](briefs/047-le-bourg.md)\n"
        "état : livre · couche : 2 · dépend de : — · PR : 214\n\n"
        f"{feuille.REPERE_FIN}\n"
    )
    nouveau = palier.inserer(texte, saisie.fiche(d, "055"), feuille.REPERE_DEBUT)
    fiche = feuille.lire_texte(nouveau).fiche("055")
    assert fiche is not None
    assert fiche.etat == "a-briefer"
    assert fiche.couche == "2"
    assert fiche.depend_de == ("047",)
    assert fiche.chemin == "briefs/055-les-routes-relient-les-villes.md"


class _DemandesGithub:
    def __init__(self):
        self.depot = "o/r"
        self.issue = {"number": 12, "state": "open", "author_association": "OWNER",
                      "user": {"login": "proprietaire"},
                      "body": GABARIT.format(titre="Les routes", couche="2", depend="—")}
        self.branches = []
        self.prs = []
        self.commentaires = []
        self.registres = {}
        self.appels = []

    def get(self, chemin, **params):
        self.appels.append((chemin, params))
        if chemin == "issues/12":
            return self.issue
        if chemin == "contents/ROADMAP.md":
            import base64
            return {"content": base64.b64encode(self.registres[params["ref"]].encode()).decode()}
        raise AssertionError(chemin)

    def liste(self, chemin, **params):
        self.appels.append((chemin, params))
        return {"branches": self.branches, "pulls": self.prs,
                "issues/12/comments": self.commentaires}[chemin]


def _evenement_demande(association="OWNER", action="opened"):
    return {"action": action, "sender": {"login": "proprietaire"}, "issue": {
        "number": 12, "author_association": association, "user": {"login": "proprietaire"},
        "labels": [{"name": "lot"}]}}


@pytest.mark.parametrize("association", ["NONE", "CONTRIBUTOR", "FIRST_TIMER", "FIRST_TIME_CONTRIBUTOR", "", None])
def test_une_association_sans_confiance_ne_lit_meme_pas_github(association):
    from outils import demandes
    gh = _DemandesGithub()
    assert demandes.preparer(gh, _evenement_demande(association), [])["action"] == "RIEN"
    assert gh.appels == []


@pytest.mark.parametrize("association", ["OWNER", "MEMBER", "COLLABORATOR"])
def test_les_associations_de_confiance_sont_explicites(association):
    from outils import demandes
    assert demandes.autorisee(_evenement_demande(association))


def test_un_evenement_trafique_ou_sans_libelle_ne_passe_pas():
    from outils import demandes
    event = _evenement_demande()
    event["sender"]["login"] = "externe"
    assert not demandes.autorisee(event)
    event = _evenement_demande()
    event["issue"]["labels"] = []
    assert not demandes.autorisee(event)


def test_la_reprise_garde_la_reservation_meme_si_master_a_avance():
    from outils import demandes
    from outils.tests.test_palier import FicheFactice
    gh = _DemandesGithub()
    plan = demandes.preparer(gh, _evenement_demande(), [FicheFactice("054", "idee")])
    assert plan["numero"] == "055"
    assert plan["fiche"]
    gh.branches = [{"name": plan["branche"]}]
    # Coupure après push : reprendre la même branche, sans fiche nouvelle.
    reprise = demandes.preparer(gh, _evenement_demande(), [FicheFactice("059", "idee")])
    assert reprise["branche"] == plan["branche"]
    assert reprise["reservee"] and not reprise["fiche"]
    gh.prs = [{"number": 240, "state": "open", "head": {"ref": plan["branche"], "sha": "a" * 40, "repo": {"full_name": "o/r"}}}]
    # Coupure après création de PR : ne pas en créer une autre.
    reprise = demandes.preparer(gh, _evenement_demande(), [FicheFactice("059", "idee")])
    assert reprise["pr"] == 240
    gh.commentaires = [{"user": {"login": demandes.BOT}, "body": "<!-- demande-lot:12:succes -->"}]
    assert demandes.preparer(gh, _evenement_demande(), [])["reponse"]
    gh.issue["state"] = "closed"
    assert demandes.preparer(gh, _evenement_demande(), [])["action"] == "RIEN"


def test_un_commentaire_externe_ne_fait_pas_croire_au_succes():
    from outils import demandes
    from outils.tests.test_palier import FicheFactice
    gh = _DemandesGithub()
    gh.commentaires = [{"user": {"login": "externe"}, "body": "<!-- demande-lot:12:succes -->"}]
    assert not demandes.preparer(gh, _evenement_demande(), [FicheFactice("054", "idee")])["reponse"]


def test_les_reservations_lisent_branches_pr_feuille_et_palier():
    from outils import demandes, palier
    from outils.tests.test_palier import FicheFactice
    gh = _DemandesGithub()
    gh.branches = [{"name": "feuille/058-branche-seule"},
                   {"name": "feuille/060-stabilisation-couche-1"}]
    gh.prs = [{"state": "open", "head": {"ref": "feuille/demande", "sha": "tete", "repo": {"full_name": "o/r"}}}]
    gh.registres["tete"] = """<!-- lots:debut -->

### [062 — Réservé par une PR](briefs/062-reserve.md)
état : a-briefer · couche : — · dépend de : — · PR : —

<!-- lots:fin -->
"""
    fiches = [FicheFactice("054", "idee")]
    reserves = demandes.reservations(gh, fiches)
    assert {"054", "058", "060", "062"} <= reserves
    assert palier.numero_libre(fiches, reserves) == "063"


def test_une_lecture_de_reservations_refusee_n_alloue_rien():
    from outils import demandes, github
    gh = _DemandesGithub()
    def refus(*args, **kwargs):
        raise github.GithubErreur("403")
    gh.liste = refus
    with pytest.raises(github.GithubErreur):
        demandes.reservations(gh, [])


def test_232_deux_demandes_cli_ne_reutilisent_pas_une_reservation(tmp_path, monkeypatch, capsys):
    from argparse import Namespace
    from outils import github
    from outils.__main__ import _saisie
    gh = _DemandesGithub()
    monkeypatch.setattr(github, "Github", lambda *_args: gh)
    (tmp_path / "atelier.toml").write_text('[projet]\nfeuille = "ROADMAP.md"\n')
    (tmp_path / "ROADMAP.md").write_text('''<!-- lots:debut -->

### [054 — Présent dans master](briefs/054-present.md)
état : a-briefer · couche : — · dépend de : — · PR : —

<!-- lots:fin -->
''')
    corps = tmp_path / "demande.md"
    corps.write_text(GABARIT.format(titre="Les routes", couche="2", depend="—"))
    args = Namespace(projet=tmp_path, corps=corps, ecrire=False, depot="o/r")
    assert _saisie(args) == 0
    premier = capsys.readouterr().out.split()[1]
    # Le premier dépôt est encore en branche, pas dans master.
    gh.branches.append({"name": f"feuille/{premier}-premiere-demande"})
    assert _saisie(args) == 0
    second = capsys.readouterr().out.split()[1]
    assert second != premier
    assert int(second) > int(premier)


def test_une_pr_de_fourche_ne_reserve_ni_numero_ni_demande():
    from outils import demandes
    from outils.tests.test_palier import FicheFactice
    gh = _DemandesGithub()
    gh.depot = "o/r"
    gh.prs = [{"number": 999, "state": "open", "head": {
        "ref": "feuille/999-injection-demande-12", "sha": "fourche",
        "repo": {"full_name": "externe/r"}}}]
    plan = demandes.preparer(gh, _evenement_demande(), [FicheFactice("054", "idee")])
    assert plan["numero"] == "055"
    assert plan["pr"] == 0
    assert not any(chemin == "contents/ROADMAP.md" for chemin, _ in gh.appels)
