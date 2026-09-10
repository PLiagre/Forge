"""La chaîne tourne, ou elle tourne à vide — et la page doit savoir laquelle.

Ce fichier protège la mesure qui aurait montré la panne du 7 septembre
2026 : quarante réveils de l'intégration, quarante `RIEN`, et rien pour
le dire. Trois invariants :

1. le nombre de tours à vide se **dérive** de deux dates, jamais d'un
   compteur, et un historique vide **échoue** ;
2. le seuil d'alerte vient du branchement, pas du code — un contrôle
   avec deux seuils différents le prouve ;
3. une lecture d'API refusée s'affiche « inconnu », jamais « absent ».
"""

from datetime import datetime, timedelta, timezone

import pytest

from outils import sante
from outils.mesure import INCONNU, Lecture

MIDI = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)
REQUIS = ("sim", "vues", "forge", "outils", "feuille", "gitleaks")


def _reveils(combien: int, depuis: datetime = MIDI):
    """`combien` réveils, un par heure, du plus récent au plus ancien."""
    return tuple(
        sante.Reveil(depuis - timedelta(hours=rang), "success",
                     f"https://github.com/o/r/actions/runs/{rang}")
        for rang in range(combien)
    )


def _sante(tours: int, seuil: int, **remplace) -> sante.Sante:
    defaut = dict(
        tours_sans_fusion=tours,
        seuil=seuil,
        derniere_fusion=MIDI - timedelta(days=2),
        dernier_reveil=None,
        requis=REQUIS,
        obligatoires=Lecture.sue(REQUIS),
        admins_soumis=Lecture.sue(True),
        pages=Lecture.sue(True),
        rouges=(),
    )
    defaut.update(remplace)
    return sante.Sante(**defaut)


# --------------------------------------------- le compte des tours à vide


def test_un_historique_vide_echoue_au_lieu_de_compter_zero():
    """Mode de défaillance n°6 : un échantillon vide doit ÉCHOUER. Zéro
    tour à vide dirait « la chaîne va bien » sans avoir rien lu."""
    with pytest.raises(ValueError):
        sante.tours_sans_fusion([], MIDI - timedelta(days=1))


def test_les_tours_se_comptent_depuis_la_derniere_fusion():
    reveils = _reveils(40)
    compte = sante.tours_sans_fusion(
        [r.moment for r in reveils], MIDI - timedelta(hours=10)
    )
    assert compte == 10


def test_sans_aucune_fusion_tous_les_tours_lus_ont_tourne_a_vide():
    """Le cas le plus franc : rien n'est jamais entré."""
    reveils = _reveils(7)
    assert sante.tours_sans_fusion([r.moment for r in reveils], None) == 7


def test_une_fusion_plus_recente_que_tous_les_tours_ramene_le_compte_a_zero():
    reveils = _reveils(5)
    assert sante.tours_sans_fusion([r.moment for r in reveils], MIDI) == 0


def test_le_dernier_reveil_est_le_plus_recent_pas_le_premier_lu():
    reveils = _reveils(5)
    dernier = sante.dernier_reveil(reveils)
    assert dernier.moment == MIDI


def test_sans_reveil_le_dernier_reveil_est_absent_pas_invente():
    assert sante.dernier_reveil(()) is None


# ------------------------------------------------ le seuil vient d'ailleurs


def test_le_seuil_decide_de_l_alerte_et_il_vient_du_branchement():
    """Deux seuils différents sur le même nombre de tours. Un seuil écrit
    en dur dans `outils/` ferait échouer l'une des deux moitiés."""
    assert _sante(tours=40, seuil=3).alerte is True
    assert _sante(tours=40, seuil=100).alerte is False


def test_le_seuil_est_atteint_a_l_egalite_pas_seulement_au_dela():
    assert _sante(tours=10, seuil=10).alerte is True
    assert _sante(tours=9, seuil=10).alerte is False


def test_une_sante_sans_seuil_ne_se_construit_pas():
    """Le seuil est un champ obligatoire : aucune valeur par défaut ne
    peut se glisser dans le code."""
    with pytest.raises(TypeError):
        sante.Sante(
            tours_sans_fusion=1, derniere_fusion=None, dernier_reveil=None,
            requis=REQUIS, obligatoires=Lecture.sue(()), admins_soumis=Lecture.sue(True),
            pages=Lecture.sue(True), rouges=(),
        )


def test_jamais_fusionne_se_declare():
    assert _sante(tours=3, seuil=10, derniere_fusion=None).jamais_fusionne is True
    assert _sante(tours=3, seuil=10).jamais_fusionne is False


# ------------------------------------- un inconnu n'est ni un oui ni un non


def test_une_protection_illisible_reste_inconnue():
    """L'API refuse la protection à un jeton non administrateur. La lire
    comme « aucun contrôle obligatoire » afficherait une porte grande
    ouverte là où elle est peut-être fermée à clé."""
    refus = Lecture.inconnue("403 sur branches/master/protection")
    lue = sante.controles_obligatoires(refus)
    assert lue.connue is False
    assert sante.mot(lue, "oui", "non") == INCONNU


def test_une_protection_lue_sans_controle_est_un_non_mesure():
    """Différent du cas précédent : ici GitHub a répondu, et il dit que
    rien n'est exigé."""
    lue = sante.controles_obligatoires(Lecture.sue({"enforce_admins": {"enabled": True}}))
    assert lue.connue is True
    assert lue.valeur == ()


def test_les_controles_reellement_exiges_se_lisent():
    brut = {"required_status_checks": {"contexts": ["sim", "outils"]}}
    assert sante.controles_obligatoires(Lecture.sue(brut)).valeur == ("sim", "outils")


def test_les_controles_declares_que_github_n_exige_pas_se_nomment():
    brut = {"required_status_checks": {"contexts": ["sim", "outils"]}}
    manquants = sante.manquants(REQUIS, sante.controles_obligatoires(Lecture.sue(brut)))
    assert manquants.valeur == ("vues", "forge", "feuille", "gitleaks")


def test_des_controles_manquants_inconnus_restent_inconnus():
    """Ni « tous exigés » ni « aucun exigé » : on ne sait pas."""
    refus = Lecture.inconnue("403")
    assert sante.manquants(REQUIS, sante.controles_obligatoires(refus)).connue is False


def test_enforce_admins_se_lit_sous_ses_deux_formes():
    """L'API rend tantôt un booléen, tantôt un objet. Les deux disent la
    même chose et doivent se lire pareil."""
    assert sante.admins_soumis(Lecture.sue({"enforce_admins": True})).valeur is True
    assert sante.admins_soumis(
        Lecture.sue({"enforce_admins": {"enabled": False}})
    ).valeur is False


def test_pages_absent_est_un_non_mesure_pages_illisible_est_un_inconnu():
    """Un 404 dit « Pages n'existe pas sur ce dépôt » — c'est un fait.
    Une autre erreur ne dit rien du tout."""
    absent = sante.publication(Lecture.sue(None))
    assert absent.connue is True and absent.valeur is False
    illisible = sante.publication(Lecture.inconnue("500"))
    assert illisible.connue is False


def test_pages_publie_par_actions_se_reconnait():
    lue = sante.publication(Lecture.sue({"build_type": "workflow"}))
    assert lue.valeur is True
    assert sante.publication(Lecture.sue({"build_type": "legacy"})).valeur is False


def test_le_mot_d_un_inconnu_n_est_ni_le_oui_ni_le_non():
    assert sante.mot(Lecture.inconnue("403"), "présent", "absent") == INCONNU
    assert sante.mot(Lecture.sue(True), "présent", "absent") == "présent"
    assert sante.mot(Lecture.sue(False), "présent", "absent") == "absent"
