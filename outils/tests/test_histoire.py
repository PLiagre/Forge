"""Combien la chaîne livre, et où elle passe son temps.

Deux mesures, un invariant commun : elles se **dérivent** des dates de
fusion des propositions, jamais d'un compteur, et un échantillon sans
livraison **échoue** au lieu de rendre zéro. Zéro lot par semaine et
« on n'a rien lu » se ressemblent à l'écran ; le premier est une mesure,
le second un aveu, et les confondre fait prendre une panne pour un
ralentissement.
"""

from datetime import datetime, timedelta, timezone

import pytest

from outils import histoire
from outils.histoire import Proposition

MIDI = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)
JOUR = timedelta(days=1)
HEURE = timedelta(hours=1)


def _prop(numero, branche, **remplace) -> Proposition:
    defaut = dict(
        numero=numero,
        titre=f"Proposition {numero}",
        branche=branche,
        ouverte=MIDI - 10 * JOUR,
        fermee=MIDI - 9 * JOUR,
        fusionnee=MIDI - 9 * JOUR,
    )
    defaut.update(remplace)
    return Proposition(**defaut)


class FicheFactice:
    def __init__(self, numero, etat):
        self.numero = numero
        self.etat = etat


# ---------------------------------------------------- le lot d'une branche


def test_la_branche_dit_le_lot_qu_elle_porte():
    assert histoire.lot_de_la_branche("agent/049-fabriquer") == "049"
    assert histoire.lot_de_la_branche("brief/052-le-regard-mince") == "052"
    assert histoire.lot_de_la_branche("feuille/049-fabriquer") == "049"


def test_une_branche_d_experience_ne_porte_aucun_lot():
    """Rien, et non une chaîne vide : lui inventer un lot ferait entrer du
    bruit dans toutes les mesures qui suivent."""
    assert histoire.lot_de_la_branche("cursor/missing-test-coverage-eb5f") is None
    assert histoire.lot_de_la_branche("") is None
    assert histoire.lot_de_la_branche("agent/sans-numero") is None


def test_un_suffixe_bis_reste_le_meme_lot_numerote():
    assert histoire.lot_de_la_branche("agent/043-bis-monde-epreuve") == "043-bis"


# ------------------------------------------------------------- la vélocité


def test_une_liste_vide_echoue_au_lieu_de_rendre_zero_par_semaine():
    with pytest.raises(ValueError):
        histoire.velocite([], MIDI, 8)


def test_un_echantillon_sans_aucune_livraison_echoue_aussi():
    """Trente propositions de brief fusionnées ne disent rien de la
    vitesse à laquelle des lots sont livrés."""
    with pytest.raises(ValueError):
        histoire.velocite([_prop(1, "brief/049-fabriquer")], MIDI, 8)


def test_une_fenetre_nulle_ne_mesure_rien():
    with pytest.raises(ValueError):
        histoire.velocite([_prop(1, "agent/049-fabriquer")], MIDI, 0)


def test_les_semaines_sortent_de_la_plus_ancienne_a_la_plus_recente():
    livraisons = [
        _prop(1, "agent/046-la-mer", fusionnee=MIDI - 2 * JOUR),
        _prop(2, "agent/047-le-bourg", fusionnee=MIDI - 2 * JOUR),
        _prop(3, "agent/044-un-metier", fusionnee=MIDI - 20 * JOUR),
    ]
    semaines = histoire.velocite(livraisons, MIDI, 4)
    assert [s.compte for s in semaines] == [0, 1, 0, 2]
    assert semaines[0].debut < semaines[-1].debut


def test_une_semaine_vide_dans_un_echantillon_qui_livre_est_une_vraie_mesure():
    """La distinction qui compte : ici zéro veut dire « rien n'est entré
    cette semaine-là », et c'est un fait."""
    semaines = histoire.velocite(
        [_prop(1, "agent/046-la-mer", fusionnee=MIDI - 20 * JOUR)], MIDI, 4
    )
    assert semaines[-1].compte == 0
    assert sum(s.compte for s in semaines) == 1


def test_une_proposition_de_lot_non_fusionnee_ne_livre_rien():
    with pytest.raises(ValueError):
        histoire.velocite(
            [_prop(1, "agent/049-fabriquer", fusionnee=None)], MIDI, 4
        )


# ----------------------------------------------------------- la traversée


def _chaine_complete():
    """Un lot qui a traversé toute la chaîne, étape par étape."""
    return [
        _prop(10, "feuille/049-fabriquer", fusionnee=MIDI - 20 * JOUR),
        _prop(11, "brief/049-fabriquer", fusionnee=MIDI - 18 * JOUR),
        _prop(12, "agent/049-fabriquer",
              ouverte=MIDI - 16 * JOUR,
              approuvee=MIDI - 12 * JOUR,
              fusionnee=MIDI - 11 * JOUR),
    ]


def test_le_parcours_d_un_lot_livre_se_date_etape_par_etape():
    chemins = histoire.parcours(_chaine_complete())
    assert len(chemins) == 1
    chemin = chemins[0]
    assert chemin.lot == "049"
    assert chemin.attente_du_bon == 2 * JOUR.total_seconds()
    assert chemin.ecriture == 2 * JOUR.total_seconds()
    assert chemin.attente_relecture == 4 * JOUR.total_seconds()
    assert chemin.attente_integration == JOUR.total_seconds()
    assert chemin.total == 9 * JOUR.total_seconds()


def test_un_lot_sans_proposition_de_feuille_perd_cette_etape_sans_l_inventer():
    """Le registre a été édité à la main un temps : ces lots-là n'ont pas
    de date d'entrée, et on ne leur en fabrique pas."""
    sans_feuille = [p for p in _chaine_complete() if not p.branche.startswith("feuille/")]
    chemin = histoire.parcours(sans_feuille)[0]
    assert chemin.attente_du_bon is None
    assert chemin.total is None
    assert chemin.attente_relecture == 4 * JOUR.total_seconds()


def test_une_traversee_sans_echantillon_dit_pas_encore_mesurable():
    vide = histoire.traversee(())
    assert vide.mesurable is False
    assert vide.total.connue is False
    assert vide.attente_relecture.connue is False


def test_chaque_mediane_porte_la_taille_de_son_echantillon():
    """« Deux jours » et « deux jours sur un seul lot » ne se valent pas."""
    mesuree = histoire.traversee(histoire.parcours(_chaine_complete()))
    assert mesuree.total.echantillon == 1
    assert mesuree.attente_relecture.echantillon == 1


def test_l_etape_la_plus_lente_se_nomme():
    """C'est ce qui dit *où* la chaîne est lente, et rien d'autre ne le dit."""
    lente = histoire.traversee(histoire.parcours(_chaine_complete())).plus_lente
    assert lente is not None
    assert lente[0] == "attente de relecture"


def test_des_dates_dans_le_desordre_ne_donnent_pas_une_duree_negative():
    """Une approbation antérieure à l'ouverture est un défaut de lecture,
    pas une durée : l'étape sort de l'échantillon."""
    chemins = histoire.parcours([
        _prop(12, "agent/049-fabriquer",
              ouverte=MIDI - 5 * JOUR, approuvee=MIDI - 9 * JOUR, fusionnee=MIDI - JOUR),
    ])
    assert chemins[0].attente_relecture is None


# ------------------------------------------------------ deux mains, ou une


def test_une_proposition_relue_par_son_auteur_ne_compte_pas_pour_relue():
    seule = _prop(1, "agent/049", auteurs=("pliagre",), relecteurs=("pliagre",))
    assert seule.relue_par_un_tiers is False


def test_une_proposition_relue_par_un_tiers_se_reconnait():
    deux = _prop(1, "agent/049", auteurs=("cursor",), relecteurs=("pliagre",))
    assert deux.relue_par_un_tiers is True


def test_une_proposition_sans_relecteur_n_est_pas_relue():
    assert _prop(1, "agent/049", auteurs=("cursor",)).relue_par_un_tiers is False


def test_la_duree_d_une_proposition_fermee_sans_fusion_n_est_pas_calculee():
    from outils.mesure import NON_CALCULE
    fermee = _prop(1, "agent/049", fusionnee=None)
    assert fermee.duree == NON_CALCULE


# ------------------------------------------------------------- les âges


def test_l_age_d_une_fiche_se_date_par_la_fusion_qui_l_a_ecrite():
    propositions = _chaine_complete()
    age = histoire.age(propositions, FicheFactice("049", "livre"), MIDI)
    assert age == 11 * JOUR.total_seconds()


def test_un_etat_qu_aucune_proposition_ne_porte_reste_sans_date():
    """`idee` et `abandonne` s'écrivent par une PR de feuille du
    propriétaire, qui ne porte pas le numéro du lot dans sa branche : on
    ne les date pas, et on ne le cache pas."""
    from outils.mesure import NON_CALCULE
    assert histoire.age(_chaine_complete(), FicheFactice("049", "idee"), MIDI) == NON_CALCULE


def test_l_age_d_une_fiche_prete_se_date_par_la_fusion_de_son_brief():
    age = histoire.age(_chaine_complete(), FicheFactice("049", "pret"), MIDI)
    assert age == 18 * JOUR.total_seconds()


# -------------------------------------------- ce qu'on déduit, et le dire


def test_une_branche_de_code_sans_proposition_ouverte_est_une_deduction():
    deduites = histoire.travaux_commences(
        ["agent/050-on-migre", "master", "cursor/experience"], []
    )
    assert len(deduites) == 1
    assert "050" in deduites[0].texte
    assert deduites[0].sur_quoi == "agent/050-on-migre"


def test_une_branche_qui_porte_deja_sa_proposition_n_est_pas_comptee_deux_fois():
    deduites = histoire.travaux_commences(["agent/050-on-migre"], ["agent/050-on-migre"])
    assert deduites == ()


def test_un_brief_en_proposition_ne_cache_pas_le_code_deja_commence():
    """C'est justement le cas qu'on cherche à voir : quelqu'un a commencé
    à coder pendant que son bon de travail attendait."""
    deduites = histoire.travaux_commences(
        ["agent/050-on-migre"], ["brief/050-on-migre-aussi-par-la-mer"]
    )
    assert len(deduites) == 1


def test_une_branche_sans_lot_ne_deduit_rien():
    assert histoire.travaux_commences(["cursor/engineering-docs-7979"], []) == ()


def test_le_journal_rapporte_le_mot_de_github_pas_la_lecture_de_l_integration():
    """Deux lectures justes, chacune à sa place. Pour l'intégration, un
    `neutral` sur un contrôle requis n'est pas un vert — il n'a rien
    prouvé. Pour le journal d'une fusion déjà faite, dire « rouge » d'un
    robot d'analyse ferait croire à un échec qui n'a jamais existé."""
    fusion = _prop(1, "agent/049", controles=(
        ("outils", "success"), ("sim", "success"), ("Cursor Bugbot", "neutral"),
    ))
    assert fusion.verts == ("outils", "sim")
    assert fusion.non_verts == (("Cursor Bugbot", "neutral"),)


def test_une_proposition_sans_controle_lu_n_en_invente_aucun():
    assert _prop(1, "agent/049").verts == ()
    assert _prop(1, "agent/049").non_verts == ()


def test_un_controle_qui_tourne_encore_n_est_ni_vert_ni_en_echec():
    assert histoire.conclusion("in_progress", None) == histoire.EN_COURS
    assert histoire.conclusion("queued", "success") == histoire.EN_COURS


def test_un_controle_termine_sans_conclusion_le_dit():
    """Règle 10 : une donnée absente se déclare, elle ne se devine pas."""
    assert histoire.conclusion("completed", None) == histoire.SANS_MOT
    assert histoire.conclusion("completed", "neutral") == "neutral"
