"""Un inconnu n'est ni un oui ni un non ; un échantillon vide n'est pas zéro.

Deux invariants, et ce sont les seuls que ce fichier protège. Ils
paraissent évidents écrits comme ça ; ils ne le sont plus dans une page
qui affiche « 0 lot livré » là où elle n'a rien lu, ou « protection
absente » là où l'API a refusé de répondre. Les deux se regardent pareil
et coûtent la même chose.
"""

from datetime import datetime, timedelta, timezone

import pytest

from outils import mesure
from outils.mesure import INCONNU, NON_CALCULE, Lecture, Mesure

MIDI = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)


# --------------------------------------------------------------- Lecture


def test_une_lecture_refusee_porte_sa_raison():
    lue = Lecture.inconnue("403 : le jeton n'est pas administrateur")
    assert lue.connue is False
    assert "403" in lue.raison


def test_un_inconnu_sans_raison_est_refuse():
    """Un « inconnu » muet n'apprend rien : il faut savoir quoi réparer."""
    with pytest.raises(ValueError):
        Lecture.inconnue("")


def test_une_lecture_inconnue_ne_rend_jamais_sa_valeur():
    """La valeur d'une lecture qui n'a pas eu lieu ne veut rien dire."""
    assert Lecture.inconnue("réseau coupé").sinon("secours") == "secours"
    assert Lecture.sue(False).sinon("secours") is False


def test_une_valeur_fausse_reste_une_valeur_connue():
    """`False` est une mesure ; ne pas savoir n'en est pas une."""
    lue = Lecture.sue(False)
    assert lue.connue is True
    assert lue.valeur is False


# ---------------------------------------------------------------- Mesure


def test_un_echantillon_vide_ne_porte_pas_de_valeur():
    with pytest.raises(ValueError):
        Mesure(0.0, 0)


def test_un_echantillon_negatif_n_existe_pas():
    with pytest.raises(ValueError):
        Mesure(NON_CALCULE, -1)


def test_la_sentinelle_de_non_calcule_n_est_pas_zero():
    """Règle 8 : zéro peut être une vraie mesure, la sentinelle ne peut pas."""
    assert NON_CALCULE != 0
    assert mesure.PAS_ENCORE.connue is False


def test_une_mesure_de_zero_reste_une_mesure():
    zero = Mesure(0.0, 3)
    assert zero.connue is True
    assert zero.valeur == 0.0


def test_la_mediane_d_un_echantillon_vide_echoue_au_lieu_de_rendre_zero():
    vide = mesure.mediane([])
    assert vide.connue is False
    assert vide.valeur == NON_CALCULE


def test_la_mediane_impaire_est_la_valeur_du_milieu():
    lue = mesure.mediane([30, 10, 20])
    assert lue.valeur == 20
    assert lue.echantillon == 3


def test_la_mediane_paire_est_la_moyenne_des_deux_du_milieu():
    assert mesure.mediane([10, 20, 30, 40]).valeur == 25


def test_la_mediane_ignore_l_extreme_que_la_moyenne_suivrait():
    """C'est pourquoi c'est une médiane : un lot resté trois semaines en
    attente déplace une moyenne et ne déplace pas la durée ordinaire."""
    ordinaire = mesure.mediane([1, 2, 3])
    avec_extreme = mesure.mediane([1, 2, 3, 4, 10_000])
    assert avec_extreme.valeur == 3
    assert ordinaire.valeur == 2


# ----------------------------------------------------------- les instants


def test_une_date_github_se_lit():
    assert mesure.instant("2026-09-08T08:29:03Z") == datetime(
        2026, 9, 8, 8, 29, 3, tzinfo=timezone.utc
    )


def test_une_date_illisible_ne_devient_pas_maintenant():
    """Une date qui deviendrait l'heure courante ferait paraître frais
    tout ce qui est vieux."""
    assert mesure.instant("hier") is None
    assert mesure.instant("") is None
    assert mesure.instant(None) is None


def test_une_duree_non_calculee_se_dit_inconnue():
    assert mesure.duree(NON_CALCULE) == INCONNU


def test_une_duree_negative_est_refusee():
    """Des dates dans le désordre sont un défaut, pas une durée."""
    with pytest.raises(ValueError):
        mesure.duree(-42)


def test_les_trois_echelles_de_duree():
    assert mesure.duree(600) == "10 min"
    assert mesure.duree(3 * 3600) == "3 h"
    assert mesure.duree(5 * 86400) == "5 j"


def test_depuis_sans_date_est_inconnu_pas_zero():
    assert mesure.depuis(None, MIDI) == INCONNU
    assert mesure.depuis(MIDI - timedelta(days=3), MIDI) == "3 j"
