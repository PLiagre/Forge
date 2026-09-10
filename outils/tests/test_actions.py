"""Ce que la page emmène faire, et ce que le geste vérifie avant d'agir.

Deux invariants :

1. **la page n'agit pas, elle emmène.** Chaque action est un lien vers la
   page GitHub d'un geste ; rien n'est un appel réseau depuis le
   navigateur, et rien ne porte de jeton ;
2. **un geste déclenché deux fois ne se fait pas deux fois.** Le travail
   relit l'état avant d'agir et sort en disant « déjà fait ». Sans ça,
   deux clics ouvrent deux propositions, ou lancent deux fois les mêmes
   contrôles sur la même révision.
"""

from outils import actions, integration

REQUIS = ("outils", "feuille", "gitleaks")


def _pr(*controles) -> integration.PR:
    return integration.PR(
        numero=226, branche="brief/049-fabriquer", brouillon=False,
        fusionnable=True, retard=0,
        controles=tuple(integration.Controle(nom, etat) for nom, etat in controles),
    )


# --------------------------------------------------------------- les liens


def test_le_lien_de_demande_pointe_vers_le_formulaire():
    lien = actions.lien_demande("PLiagre/ForgeHistory")
    assert lien.startswith("https://github.com/PLiagre/ForgeHistory/issues/new?")
    assert "template=nouveau-lot.yml" in lien


def test_la_couche_se_prerempli_dans_le_formulaire():
    lien = actions.lien_demande("PLiagre/ForgeHistory", "2 — Villes")
    assert "couche=2+%E2%80%94+Villes" in lien


def test_un_depot_illisible_est_refuse_plutot_que_de_faire_un_lien_mort():
    """Un lien mort sur un tableau de bord est pire qu'un lien absent :
    il se clique."""
    import pytest
    with pytest.raises(ValueError):
        actions.lien_demande("ForgeHistory")


def test_chaque_action_nomme_un_travail_qui_existe():
    from outils.tests.banc import RACINE
    fichiers = {a.lien.rsplit("/", 1)[-1] for a in actions.actions("o/r") if "workflows/" in a.lien}
    assert fichiers, "aucune action ne pointe vers un travail"
    for fichier in fichiers:
        assert (RACINE / ".github" / "workflows" / fichier).is_file(), fichier


def test_reprendre_une_carte_ne_pretend_pas_se_faire_d_ici():
    """Les cartes vivent sur le serveur du propriétaire. La page dit quoi
    taper, elle ne fait pas semblant de pouvoir le faire."""
    reprise = [a for a in actions.actions("o/r") if "carte" in a.titre.lower()]
    assert len(reprise) == 1
    assert reprise[0].lien == ""
    assert reprise[0].entree


def test_les_actions_couvrent_les_sept_gestes_du_tableau():
    assert len(actions.actions("PLiagre/ForgeHistory")) == 7


# ------------------------------------------------- redemander les contrôles


def test_un_controle_absent_se_redemande():
    geste = actions.redemander_controles(True, False, _pr(("outils", integration.VERT)), REQUIS)
    assert geste.a_faire
    assert "feuille" in geste.raison


def test_des_controles_deja_poses_ne_se_redemandent_pas():
    """Le « déjà fait » de cette action-là."""
    pr = _pr(*((nom, integration.VERT) for nom in REQUIS))
    geste = actions.redemander_controles(True, False, pr, REQUIS)
    assert not geste.a_faire
    assert "déjà fait" in geste.raison


def test_un_controle_rouge_se_redemande_lui_aussi():
    """Rouge n'est pas absent, mais un rejeu est ce qu'on veut : c'est
    exactement le geste que l'action porte."""
    pr = _pr(("outils", integration.ROUGE), ("feuille", integration.VERT),
             ("gitleaks", integration.VERT))
    assert actions.redemander_controles(True, False, pr, REQUIS).a_faire


def test_un_controle_en_cours_compte_comme_present():
    """Le redemander lancerait une seconde exécution sur la même révision,
    et deux exécutions concurrentes ne prouvent pas deux fois plus."""
    pr = _pr(("outils", integration.EN_COURS), ("feuille", integration.VERT),
             ("gitleaks", integration.VERT))
    assert not actions.redemander_controles(True, False, pr, REQUIS).a_faire


def test_une_proposition_fermee_n_a_plus_de_controle_a_redemander():
    geste = actions.redemander_controles(False, False, _pr(), REQUIS)
    assert not geste.a_faire
    assert "fermée" in geste.raison


def test_un_brouillon_se_sort_du_brouillon_avant_qu_on_rejoue_ses_controles():
    geste = actions.redemander_controles(True, True, _pr(), REQUIS)
    assert not geste.a_faire
    assert "brouillon" in geste.raison


# -------------------------------------------------- sortir du brouillon


def test_un_brouillon_se_sort_du_brouillon():
    assert actions.sortir_du_brouillon(True, True).a_faire


def test_une_proposition_deja_sortie_ne_se_ressort_pas():
    """Le « déjà fait » de cette action-là."""
    geste = actions.sortir_du_brouillon(True, False)
    assert not geste.a_faire
    assert "déjà fait" in geste.raison


def test_un_brouillon_ferme_ne_se_rouvre_pas_par_cette_action():
    geste = actions.sortir_du_brouillon(False, True)
    assert not geste.a_faire
    assert "fermée" in geste.raison
