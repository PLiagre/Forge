"""La page montre ce que le registre dit, et rien d'autre."""

from dataclasses import dataclass, field

import pytest

from outils import tableau
from outils.tableau import LignePR


@dataclass(frozen=True)
class FicheFactice:
    numero: str
    etat: str
    couche: str | None = None
    titre: str = "Un lot"
    chemin: str = ""
    depend_de: tuple[str, ...] = field(default=())
    prs: tuple[int, ...] = field(default=())

    def __post_init__(self) -> None:
        if not self.chemin:
            object.__setattr__(self, "chemin", f"briefs/{self.numero}-un-lot.md")


MOMENT = "07/09/2026 à 11h00 UTC"


def test_un_registre_vide_est_une_erreur_pas_une_page_vide():
    """Un échantillon vide échoue ; il ne s'affiche pas en blanc."""
    with pytest.raises(ValueError):
        tableau.rendre([], [], MOMENT)


def test_chaque_lot_apparait_avec_son_etat():
    page = tableau.rendre(
        [FicheFactice("046", "livre", "1", titre="La mer est un port commun"),
         FicheFactice("050", "a-briefer", "1", titre="On migre aussi par la mer")],
        [], MOMENT,
    )
    assert "La mer est un port commun" in page
    assert "On migre aussi par la mer" in page
    assert "livre" in page and "a-briefer" in page


def test_la_couche_porte_son_nom_et_son_avancement():
    page = tableau.rendre(
        [FicheFactice("046", "livre", "1"), FicheFactice("050", "pret", "1")], [], MOMENT
    )
    assert "Monde vivant" in page
    assert "1 lot(s) sur 2" in page
    assert "1 lot(s) en cours" in page


def test_une_couche_finie_et_deja_stabilisee_se_voit():
    """« Finie » veut dire : plus rien n'avance, et le palier est passé.
    Tant qu'il ne l'est pas, la page dit « palier dû » — ce n'est pas la
    même chose, et c'est la seule des deux qui appelle une action."""
    page = tableau.rendre(
        [FicheFactice("046", "livre", "1"),
         FicheFactice("055", "livre", "1", chemin="briefs/055-stabilisation-couche-1.md",
                      depend_de=("046",))],
        [], MOMENT,
    )
    assert "finie" in page
    assert "palier dû" not in page


def test_un_palier_du_se_voit():
    """C'est l'information qui appelle une action : la couche est finie et
    son lot de stabilisation n'est pas encore au registre."""
    page = tableau.rendre([FicheFactice("046", "livre", "1")], [], MOMENT)
    assert "palier dû" in page


def test_les_lots_sans_couche_ne_sont_pas_perdus():
    page = tableau.rendre(
        [FicheFactice("046", "livre", "1"), FicheFactice("048", "livre", None, titre="Le bandeau")],
        [], MOMENT,
    )
    assert "Hors couche" in page
    assert "Le bandeau" in page


def test_chaque_proposition_dit_ce_qui_la_bloque():
    page = tableau.rendre(
        [FicheFactice("046", "livre", "1")],
        [LignePR(226, "brief/049-fabriquer", "rien", "contrôle absent : relecture")],
        MOMENT,
    )
    assert "#226" in page
    assert "brief/049-fabriquer" in page
    assert "contrôle absent : relecture" in page


def test_aucune_proposition_ouverte_se_dit():
    page = tableau.rendre([FicheFactice("046", "livre", "1")], [], MOMENT)
    assert "Aucune proposition ouverte" in page


def test_le_moment_de_l_ecriture_est_sur_la_page():
    """Une page sans date laisse croire qu'elle est d'aujourd'hui."""
    assert MOMENT in tableau.rendre([FicheFactice("046", "livre", "1")], [], MOMENT)


def test_un_titre_qui_porte_du_balisage_ne_casse_pas_la_page():
    page = tableau.rendre(
        [FicheFactice("046", "livre", "1", titre="Le <script>alerte</script> & la mer")],
        [], MOMENT,
    )
    assert "<script>alerte</script>" not in page
    assert "&lt;script&gt;" in page and "&amp;" in page


def test_le_lien_de_demande_pointe_vers_le_formulaire():
    page = tableau.rendre([FicheFactice("046", "livre", "1")], [], MOMENT, "PLiagre/ForgeHistory")
    assert "PLiagre/ForgeHistory/issues/new?template=nouveau-lot.yml" in page


def test_sans_depot_la_page_se_rend_quand_meme():
    page = tableau.rendre([FicheFactice("046", "livre", "1")], [], MOMENT)
    assert "issues/new" not in page


# ----------------------------------------------------------------------
# Le tableau de pilotage : les quatre blocs qui s'ajoutent au registre.
#
# Ils protègent trois choses, et seulement trois : que la page dit la
# même chose que la machine (la cause d'un blocage, mot pour mot), qu'un
# inconnu ne se déguise ni en oui ni en non, et qu'elle reste ce qu'elle
# est — un fichier statique, sans script, sans jeton, lisible dans les
# deux thèmes.
# ----------------------------------------------------------------------

import re
from datetime import datetime, timedelta, timezone

from outils import actions, attention, histoire, integration, sante, tableau
from outils.mesure import Lecture

MAINTENANT = datetime(2026, 9, 8, 11, 0, tzinfo=timezone.utc)
JOUR = timedelta(days=1)
REQUIS = ("outils", "feuille")
PREFIXES = ("agent/", "brief/", "feuille/")
UN_LOT = [FicheFactice("046", "livre", "1")]


def _sante(**remplace) -> sante.Sante:
    defaut = dict(
        tours_sans_fusion=3, seuil=10,
        derniere_fusion=MAINTENANT - 2 * JOUR,
        dernier_reveil=sante.Reveil(MAINTENANT - timedelta(hours=1), "success",
                                    "https://github.com/o/r/actions/runs/1"),
        requis=REQUIS, obligatoires=Lecture.sue(REQUIS),
        admins_soumis=Lecture.sue(True), pages=Lecture.sue(True), rouges=(),
    )
    defaut.update(remplace)
    return sante.Sante(**defaut)


def _etat(**remplace) -> tableau.Etat:
    defaut = dict(maintenant=MAINTENANT, sante=_sante())
    defaut.update(remplace)
    return tableau.Etat(**defaut)


def _style(page: str) -> tuple[str, str]:
    """La feuille de style, coupée en deux : le thème clair, le sombre."""
    dedans = page.split("<style>", 1)[1].split("</style>", 1)[0]
    clair, sombre = dedans.split("@media (prefers-color-scheme:dark)", 1)
    return clair, sombre


# ------------------------------- SC2 : la cause est celle de l'intégration


def test_la_raison_affichee_est_mot_pour_mot_celle_de_l_integration():
    """Le contrat de la page. La cause qui retient une proposition vient
    de `examiner` — la fonction qui fusionne — et pas d'une paraphrase."""
    pr = integration.PR(
        numero=226, branche="brief/049-fabriquer", brouillon=False,
        fusionnable=True, retard=0,
        controles=(integration.Controle("outils", integration.VERT),),
        ouverte=(MAINTENANT - 6 * JOUR).isoformat().replace("+00:00", "Z"),
    )
    decision = integration.examiner(pr, REQUIS, PREFIXES)
    alertes = attention.alertes(
        examens=[(pr, decision)], fiches=UN_LOT, controles_base=(), requis=REQUIS,
        prefixes=PREFIXES, brouillon_jours=2, maintenant=MAINTENANT, depot="o/r",
    )
    page = tableau.rendre(
        UN_LOT,
        [tableau.LignePR(pr.numero, pr.branche, decision.action, decision.raison)],
        MOMENT, "o/r", _etat(alertes=alertes),
    )
    assert decision.raison == "contrôle absent : feuille"
    # Deux fois : dans le bloc de tête, et dans le registre complet.
    assert page.count(decision.raison) >= 2


def test_le_bloc_de_tete_se_referme_en_une_ligne_quand_rien_n_attend():
    page = tableau.rendre(UN_LOT, [], MOMENT, "o/r", _etat(alertes=()))
    assert "Ce qui demande une décision maintenant" in page
    assert "Rien. Aucune proposition retenue" in page


def test_chaque_ligne_du_bloc_de_tete_porte_depuis_quand():
    alerte = attention.Alerte("proposition retenue", "#226 : contrôle absent : feuille",
                              MAINTENANT - 6 * JOUR, "")
    page = tableau.rendre(UN_LOT, [], MOMENT, "o/r", _etat(alertes=(alerte,)))
    assert "6 j" in page


# ---------------------------------- SC5 : les tours à vide, et leur seuil


def test_le_compte_des_tours_a_vide_est_exact_sur_la_page():
    page = tableau.rendre(UN_LOT, [], MOMENT, "o/r",
                          _etat(sante=_sante(tours_sans_fusion=40, seuil=10)))
    assert ">40</div>" in page


def test_l_alerte_ne_se_declenche_qu_au_dela_du_seuil_declare():
    """Le même nombre de tours, deux seuils. Un seuil écrit en dur dans
    le code ferait échouer l'une des deux moitiés."""
    alerte = tableau.rendre(UN_LOT, [], MOMENT, "o/r",
                            _etat(sante=_sante(tours_sans_fusion=40, seuil=10)))
    calme = tableau.rendre(UN_LOT, [], MOMENT, "o/r",
                           _etat(sante=_sante(tours_sans_fusion=40, seuil=100)))
    assert "la chaîne tourne à vide" in alerte
    assert "la chaîne tourne à vide" not in calme
    assert "Le seuil d'alerte est 100 tours" in calme


def test_la_page_dit_quand_rien_n_a_jamais_ete_fusionne():
    page = tableau.rendre(UN_LOT, [], MOMENT, "o/r",
                          _etat(sante=_sante(derniere_fusion=None)))
    assert "aucune fusion dans l'historique lu" in page


def test_le_dernier_reveil_de_l_integration_porte_son_lien():
    page = tableau.rendre(UN_LOT, [], MOMENT, "o/r", _etat())
    assert "https://github.com/o/r/actions/runs/1" in page


def test_la_derniere_execution_rouge_de_chaque_travail_se_voit():
    rouge = sante.Rouge("tests", MAINTENANT - 3 * JOUR,
                        "https://github.com/o/r/actions/runs/9")
    page = tableau.rendre(UN_LOT, [], MOMENT, "o/r", _etat(sante=_sante(rouges=(rouge,))))
    assert "runs/9" in page
    assert "3 j" in page


# ------------------------------------- SC6 : un inconnu n'est ni oui ni non


def test_une_protection_illisible_s_affiche_inconnu_ni_absent_ni_present():
    """Le cas exact du jeton d'Actions, qui n'est pas administrateur."""
    aveugle = _sante(
        obligatoires=Lecture.inconnue("403 sur branches/master/protection"),
        admins_soumis=Lecture.inconnue("403 sur branches/master/protection"),
    )
    page = tableau.rendre(UN_LOT, [], MOMENT, "o/r", _etat(sante=aveugle))
    bloc = page.split("La santé de la chaîne", 1)[1].split("L'avancement", 1)[0]
    assert "inconnu" in bloc
    assert "GitHub n'exige pas" not in bloc
    assert "les 2 contrôles déclarés sont exigés" not in bloc


def test_une_protection_lue_qui_n_exige_rien_le_dit_franchement():
    page = tableau.rendre(UN_LOT, [], MOMENT, "o/r",
                          _etat(sante=_sante(obligatoires=Lecture.sue(()))))
    assert "GitHub n'exige pas" in page
    assert "outils, feuille" in page


def test_pages_non_publie_se_distingue_de_pages_illisible():
    absent = tableau.rendre(UN_LOT, [], MOMENT, "o/r",
                            _etat(sante=_sante(pages=Lecture.sue(False))))
    illisible = tableau.rendre(UN_LOT, [], MOMENT, "o/r",
                               _etat(sante=_sante(pages=Lecture.inconnue("500"))))
    assert "elle est écrite, pas publiée" in absent
    assert "elle est écrite, pas publiée" not in illisible


def test_ce_qui_n_a_pas_pu_etre_lu_se_declare_au_lieu_de_disparaitre():
    """Règle 10 : une absence se déclare. Une page amputée en silence
    laisse croire que sa vue est complète."""
    page = tableau.rendre(UN_LOT, [], MOMENT, "o/r",
                          _etat(refus=("la protection de la branche de base : 403",)))
    assert "ce qui n'a pas pu être lu" in page
    assert "403" in page


def test_une_page_rendue_sans_lecture_dit_qu_elle_n_a_rien_lu():
    page = tableau.rendre(UN_LOT, [], MOMENT, "o/r")
    assert "Non lue : cette page a été écrite sans lire" in page
    assert "Non lu : cette page a été écrite sans lire GitHub." in page


# ----------------------------------- SC7 : vélocité et temps de traversée


def test_une_velocite_non_mesurable_se_dit_au_lieu_d_afficher_zero():
    page = tableau.rendre(UN_LOT, [], MOMENT, "o/r", _etat(velocite=()))
    assert "Pas encore mesurable" in page


def test_la_velocite_dessine_un_histogramme_sans_bibliotheque():
    semaines = (
        histoire.Semaine(MAINTENANT - 14 * JOUR, MAINTENANT - 7 * JOUR, ()),
        histoire.Semaine(MAINTENANT - 7 * JOUR, MAINTENANT, ("046", "047")),
    )
    page = tableau.rendre(UN_LOT, [], MOMENT, "o/r", _etat(velocite=semaines))
    assert "<svg" in page and 'class="barre"' in page
    assert "<script" not in page


def test_une_semaine_sans_livraison_ne_divise_pas_par_zero():
    semaines = (histoire.Semaine(MAINTENANT - 7 * JOUR, MAINTENANT, ()),)
    page = tableau.rendre(UN_LOT, [], MOMENT, "o/r", _etat(velocite=semaines))
    assert "<svg" in page


def test_une_traversee_sans_echantillon_dit_pas_encore_mesurable():
    page = tableau.rendre(UN_LOT, [], MOMENT, "o/r",
                          _etat(traversee=histoire.traversee(())))
    assert "aucun lot livré n'a ses dates" in page


def test_chaque_mediane_affiche_la_taille_de_son_echantillon():
    chemins = (histoire.Parcours("049", MAINTENANT - 9 * JOUR, MAINTENANT - 7 * JOUR,
                                 MAINTENANT - 5 * JOUR, MAINTENANT - 2 * JOUR,
                                 MAINTENANT - JOUR),)
    page = tableau.rendre(UN_LOT, [], MOMENT, "o/r",
                          _etat(traversee=histoire.traversee(chemins)))
    assert "(1 lot(s))" in page
    assert "attente de relecture" in page


def test_l_age_de_chaque_lot_dans_son_etat_est_sur_la_page():
    page = tableau.rendre(UN_LOT, [], MOMENT, "o/r",
                          _etat(ages={"046": 5 * JOUR.total_seconds()}))
    assert "5 j" in page


def test_un_lot_dont_l_etat_n_a_pas_de_date_affiche_inconnu_pas_zero():
    page = tableau.rendre(UN_LOT, [], MOMENT, "o/r", _etat(ages={}))
    assert "0 min" not in page


# ------------------------------------------------- le journal des fusions


def _fusion(**remplace) -> histoire.Proposition:
    defaut = dict(
        numero=214, titre="Lot 047 — le bourg", branche="agent/047-le-bourg",
        auteurs=("cursor[bot]",), relecteurs=("pliagre",),
        ouverte=MAINTENANT - 3 * JOUR, fermee=MAINTENANT - JOUR,
        fusionnee=MAINTENANT - JOUR,
        controles=(("outils", "success"),),
        lien="https://github.com/o/r/pull/214",
    )
    defaut.update(remplace)
    return histoire.Proposition(**defaut)


def test_le_journal_dit_qui_a_ecrit_et_qui_a_relu():
    page = tableau.rendre(UN_LOT, [], MOMENT, "o/r", _etat(journal=(_fusion(),)))
    assert "cursor[bot]" in page
    assert "pliagre" in page
    assert "#214" in page and "agent/047-le-bourg" in page


def test_une_relecture_qui_n_est_pas_d_un_tiers_se_dit():
    """La règle de rôle est mécanique ailleurs ; ici elle est visible."""
    page = tableau.rendre(
        UN_LOT, [], MOMENT, "o/r",
        _etat(journal=(_fusion(auteurs=("pliagre",), relecteurs=("pliagre",)),)),
    )
    assert "pas un tiers" in page


def test_une_proposition_fermee_sans_fusion_le_dit_et_dit_pourquoi():
    page = tableau.rendre(
        UN_LOT, [], MOMENT, "o/r",
        _etat(journal=(_fusion(fusionnee=None,
                               mot_de_la_fin="remplacée par la 236"),)),
    )
    assert "fermée sans fusion" in page
    assert "remplacée par la 236" in page


def test_une_fermeture_sans_explication_ne_s_en_invente_pas_une():
    page = tableau.rendre(
        UN_LOT, [], MOMENT, "o/r", _etat(journal=(_fusion(fusionnee=None),)),
    )
    assert "aucun commentaire ne dit pourquoi" in page


def test_les_controles_au_moment_de_la_fusion_sont_au_journal():
    """Le compte, et le nom de ce qui n'est pas vert : c'est ce dernier
    qu'on cherche quand on ouvre le journal, et c'est lui qu'une liste
    trop longue ferait sortir de la colonne."""
    verte = _fusion(controles=(("outils", "success"), ("sim", "success")))
    page = tableau.rendre(UN_LOT, [], MOMENT, "o/r", _etat(journal=(verte,)))
    assert "2/2 verts" in page

    rouge = _fusion(controles=(("outils", "success"), ("sim", "failure")))
    page = tableau.rendre(UN_LOT, [], MOMENT, "o/r", _etat(journal=(rouge,)))
    assert "1/2 verts" in page
    assert "sim : failure" in page


# ------------------------------------------- ce que la page ne sait pas


def test_la_page_declare_qu_elle_ne_voit_pas_les_cartes_de_l_atelier():
    """Règle 10 : une absence se déclare. Sans cette phrase, la page
    laisserait croire que sa vue est complète."""
    page = tableau.rendre(UN_LOT, [], MOMENT, "o/r", _etat())
    assert "ne sait donc pas si un agent" in page


def test_une_branche_de_code_sans_proposition_est_nommee_comme_une_deduction():
    deduction = histoire.Deduction("un codeur a commencé le lot 050", "agent/050-on-migre")
    page = tableau.rendre(UN_LOT, [], MOMENT, "o/r", _etat(deductions=(deduction,)))
    assert "déduction" in page
    assert "agent/050-on-migre" in page


# ---------------------------------------------------------- les actions


def test_chaque_action_est_un_lien_vers_github_pas_un_bouton():
    page = tableau.rendre(UN_LOT, [], MOMENT, "o/r",
                          _etat(actions=actions.actions("PLiagre/ForgeHistory")))
    assert "actions/workflows/controles.yml" in page
    assert "actions/workflows/etat-lot.yml" in page
    assert "<form" not in page and "<button" not in page


def test_la_couche_porte_son_propre_lien_de_demande():
    page = tableau.rendre(UN_LOT, [], MOMENT, "o/r", _etat())
    assert "couche=1+%E2%80%94+Monde+vivant" in page


# ------------------------------ SC10 : la page est statique, et le reste


def test_la_page_ne_porte_ni_script_ni_appel_reseau_ni_jeton():
    """Elle est publiée sur Pages : un jeton publié est un jeton perdu, et
    un appel réseau depuis le navigateur demanderait un jeton."""
    page = tableau.rendre(
        UN_LOT, [tableau.LignePR(226, "brief/049", "rien", "contrôle absent")],
        MOMENT, "PLiagre/ForgeHistory",
        _etat(journal=(_fusion(),), actions=actions.actions("PLiagre/ForgeHistory")),
    )
    minuscules = page.lower()
    for interdit in ("<script", "javascript:", "fetch(", "xmlhttprequest",
                     "ghp_", "github_pat_", "authorization", "bearer "):
        assert interdit not in minuscules, interdit


def test_aucun_gestionnaire_d_evenement_ne_se_glisse_dans_la_page():
    page = tableau.rendre(UN_LOT, [], MOMENT, "o/r", _etat())
    assert not re.search(r"\son[a-z]+\s*=", page)


# ---------------------------------- SC12 : les deux thèmes, et leurs couleurs


def test_aucune_couleur_n_est_definie_uniquement_dans_le_bloc_sombre():
    """Une couleur qui n'existerait que là serait absente en thème clair,
    et personne ne regarde une page dans les deux thèmes avant de la
    publier."""
    clair, sombre = _style(tableau.rendre(UN_LOT, [], MOMENT, "o/r", _etat()))
    noms = lambda bloc: set(re.findall(r"(--[a-z-]+)\s*:", bloc))
    manquantes = noms(sombre) - noms(clair)
    assert manquantes == set(), manquantes


def test_le_thème_sombre_redefinit_bien_les_couleurs_et_pas_seulement_le_fond():
    """Un contrôle qui ne regarderait que `--fond` laisserait passer une
    page au texte noir sur fond noir."""
    _, sombre = _style(tableau.rendre(UN_LOT, [], MOMENT, "o/r", _etat()))
    for nom in ("--fond", "--encre", "--carte", "--ok", "--du", "--barre"):
        assert f"{nom}:" in sombre, nom


def test_aucune_couleur_en_dur_ne_se_glisse_hors_de_la_feuille_de_style():
    """Une couleur écrite dans le corps de la page ne se rethème pas.

    Le contrôle vise les attributs qui peignent — `style`, `fill`,
    `stroke` — et pas le texte : « #226 » est un numéro de proposition,
    pas une couleur, et un contrôle qui les confondrait serait un
    contrôle trop grossier (règle 6)."""
    page = tableau.rendre(
        UN_LOT, [tableau.LignePR(226, "brief/049", "rien", "contrôle absent")],
        MOMENT, "o/r",
        _etat(journal=(_fusion(),), actions=actions.actions("o/r"),
              velocite=(histoire.Semaine(MAINTENANT - 7 * JOUR, MAINTENANT, ("046",)),)),
    )
    corps = page.split("</style>", 1)[1]
    peintures = re.findall(r'(?:style|fill|stroke|color|bgcolor)="([^"]*)"', corps)
    assert peintures, "aucun attribut de peinture : le contrôle ne prouverait rien"
    assert [v for v in peintures if "#" in v] == []
    assert "<style" not in corps


# --------------------------------------------------------------- l'ordre


def test_l_ordre_des_blocs_met_ce_qui_appelle_avant_ce_qui_va_bien():
    page = tableau.rendre(UN_LOT, [], MOMENT, "o/r", _etat(journal=(_fusion(),)))
    rangs = [
        page.index("Ce qui demande une décision maintenant"),
        page.index("La santé de la chaîne"),
        page.index("L'avancement"),
        page.index("Le journal des fusions"),
        page.index("Le registre complet"),
    ]
    assert rangs == sorted(rangs)
