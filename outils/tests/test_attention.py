"""Ce qui demande une décision, et la cause exacte — jamais une paraphrase.

Le bloc de tête de la page. Son invariant tient en une phrase : la raison
qu'il affiche est **celle que `integration.examiner` rend**, mot pour
mot. Une présentation qui reformule finit par dire autre chose que ce que
la machine fait, et une page qui dit « en attente » là où l'intégration
dit « contrôle absent : relecture » envoie le propriétaire chercher au
mauvais endroit.

Second invariant : chaque ligne porte une durée. « Une proposition
attend » ne dit rien ; « depuis six jours » dit tout.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from outils import attention, integration

MIDI = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)
JOUR = timedelta(days=1)
REQUIS = ("outils", "feuille")
PREFIXES = ("agent/", "brief/", "feuille/")


@dataclass(frozen=True)
class FicheFactice:
    numero: str
    etat: str
    couche: str | None = None
    titre: str = "Un lot"
    chemin: str = ""
    depend_de: tuple = field(default=())
    prs: tuple = field(default=())

    def __post_init__(self) -> None:
        if not self.chemin:
            object.__setattr__(self, "chemin", f"briefs/{self.numero}-un-lot.md")


def _pr(**remplace) -> integration.PR:
    defaut = dict(
        numero=226, branche="brief/049-fabriquer", brouillon=False,
        fusionnable=True, retard=0,
        controles=(integration.Controle("outils", integration.VERT),
                   integration.Controle("feuille", integration.VERT)),
        relue=True, motif_relecture="approuvée sur aaaaaaa par pliagre",
        ouverte=(MIDI - 6 * JOUR).isoformat().replace("+00:00", "Z"),
        titre="Brief 049",
    )
    defaut.update(remplace)
    return integration.PR(**defaut)


def _examen(pr: integration.PR):
    """La PR et la décision que l'intégration prend sur elle. La vraie."""
    return (pr, integration.examiner(pr, REQUIS, PREFIXES))


# Une couche déjà stabilisée : elle n'appelle aucun palier, et laisse
# donc les contrôles ci-dessous parler de ce qu'ils veulent éprouver. La
# couche qui en appelle un a sa propre fixture, plus bas.
COUCHE_CALME = (
    FicheFactice("046", "livre", "1"),
    FicheFactice("055", "livre", "1", chemin="briefs/055-stabilisation-couche-1.md",
                 depend_de=("046",)),
)


def _alertes(examens=(), fiches=COUCHE_CALME, **remplace):
    defaut = dict(
        examens=examens, fiches=fiches, controles_base=(), requis=REQUIS,
        prefixes=PREFIXES, base="master", brouillon_jours=2, maintenant=MIDI,
        depot="o/r",
    )
    defaut.update(remplace)
    return attention.alertes(**defaut)


# ------------------------------------------------ la cause, mot pour mot


def test_la_cause_affichee_est_celle_que_l_integration_rend():
    """L'invariant du fichier. Si la page reformulait, cette égalité
    tomberait — et c'est exactement ce qu'on veut qu'elle attrape."""
    pr = _pr(controles=(integration.Controle("outils", integration.VERT),))
    _, decision = _examen(pr)
    trouvees = _alertes([_examen(pr)])
    assert len(trouvees) == 1
    assert decision.raison in trouvees[0].texte
    assert decision.raison == "contrôle absent : feuille"


def test_un_conflit_avec_la_base_a_sa_propre_categorie():
    pr = _pr(fusionnable=False)
    trouvees = _alertes([_examen(pr)])
    assert [a.quoi for a in trouvees] == [attention.CONFLIT]
    assert "en conflit avec master" in trouvees[0].texte


def test_une_proposition_retenue_porte_depuis_quand_elle_attend():
    pr = _pr(relue=False, motif_relecture="aucune approbation sur aaaaaaa")
    trouvees = _alertes([_examen(pr)])
    assert trouvees[0].depuis is not None
    assert (MIDI - trouvees[0].depuis).days == 6


def test_une_proposition_qui_avance_n_appelle_personne():
    """Une PR fusionnable ce tour-ci n'est pas une chose qui attend."""
    assert _alertes([_examen(_pr())]) == ()


def test_une_branche_hors_des_prefixes_n_est_pas_une_chose_qui_attend():
    """Une expérience attend le propriétaire, pas la chaîne."""
    pr = _pr(branche="cursor/experience-1234", relue=False)
    assert _alertes([_examen(pr)]) == ()


# ------------------------------------------------------ les brouillons


def test_un_brouillon_plus_vieux_que_le_seuil_est_du_travail_perdu():
    pr = _pr(brouillon=True, ouverte=(MIDI - 5 * JOUR).isoformat().replace("+00:00", "Z"))
    trouvees = _alertes([_examen(pr)])
    assert [a.quoi for a in trouvees] == [attention.BROUILLON]


def test_un_brouillon_frais_ne_derange_personne():
    pr = _pr(brouillon=True, ouverte=MIDI.isoformat().replace("+00:00", "Z"))
    assert _alertes([_examen(pr)]) == ()


def test_le_seuil_du_brouillon_vient_du_branchement_pas_du_code():
    """Deux seuils sur la même proposition. Un défaut écrit dans
    `outils/` ferait échouer l'une des deux moitiés."""
    pr = _pr(brouillon=True, ouverte=(MIDI - 3 * JOUR).isoformat().replace("+00:00", "Z"))
    assert _alertes([_examen(pr)], brouillon_jours=2) != ()
    assert _alertes([_examen(pr)], brouillon_jours=10) == ()


def test_un_brouillon_sans_date_ne_se_declare_pas_vieux():
    """Sans date, on ne sait pas depuis quand : on ne l'invente pas."""
    pr = _pr(brouillon=True, ouverte="")
    assert _alertes([_examen(pr)]) == ()


# --------------------------------------------------- les lots et la base


def test_un_lot_pret_dont_la_dependance_n_est_pas_livree_se_nomme_avec_elle():
    fiches = COUCHE_CALME + (
        FicheFactice("049", "pret", "2", depend_de=("044",)),
        FicheFactice("044", "a-briefer", "2"),
    )
    trouvees = [a for a in _alertes(fiches=fiches) if a.quoi == attention.LOT_BLOQUE]
    assert len(trouvees) == 1
    assert "044" in trouvees[0].texte and "a-briefer" in trouvees[0].texte


def test_un_lot_pret_dont_la_dependance_est_livree_n_attend_rien():
    fiches = COUCHE_CALME + (
        FicheFactice("049", "pret", "2", depend_de=("044",)),
        FicheFactice("044", "livre", "2"),
    )
    assert [a for a in _alertes(fiches=fiches) if a.quoi == attention.LOT_BLOQUE] == []


def test_une_dependance_fantome_se_dit():
    fiches = COUCHE_CALME + (FicheFactice("049", "pret", "2", depend_de=("999",)),)
    trouvees = [a for a in _alertes(fiches=fiches) if a.quoi == attention.LOT_BLOQUE]
    assert "aucune fiche" in trouvees[0].texte


def test_un_palier_du_appelle_une_decision():
    """Une couche finie dont le lot de stabilisation n'est pas au registre."""
    fiches = (FicheFactice("046", "livre", "1"),)
    trouvees = [a for a in _alertes(fiches=fiches) if a.quoi == attention.PALIER_DU]
    assert len(trouvees) == 1
    assert "046" in trouvees[0].texte


def test_un_controle_rouge_sur_la_base_se_nomme():
    trouvees = [
        a for a in _alertes(controles_base=[("outils", "completed", "failure"),
                                            ("sim", "completed", "success")])
        if a.quoi == attention.BASE_ROUGE
    ]
    assert len(trouvees) == 1
    assert "outils" in trouvees[0].texte and "sim" not in trouvees[0].texte


def test_une_base_verte_n_appelle_personne():
    trouvees = [
        a for a in _alertes(controles_base=[("outils", "completed", "success")])
        if a.quoi == attention.BASE_ROUGE
    ]
    assert trouvees == []


def test_un_controle_de_tiers_rouge_sur_la_base_ne_noie_pas_les_vrais():
    """La base porte des contrôles qui ne gouvernent rien — des robots
    qui concluent « neutral », donc rouge au sens de la règle. Une ligne
    rouge permanente sur eux ferait fermer le bloc de tête pour de bon."""
    trouvees = [
        a for a in _alertes(controles_base=[("Cursor Bugbot", "completed", "neutral")])
        if a.quoi == attention.BASE_ROUGE
    ]
    assert trouvees == []


def test_un_controle_en_cours_sur_la_base_n_est_pas_un_rouge():
    trouvees = [
        a for a in _alertes(controles_base=[("outils", "in_progress", None)])
        if a.quoi == attention.BASE_ROUGE
    ]
    assert trouvees == []


# ------------------------------------------------------------- l'ordre


def test_l_ordre_met_ce_qui_bloque_une_fusion_avant_ce_qui_dort():
    vieux_brouillon = _pr(
        numero=235, brouillon=True,
        ouverte=(MIDI - 9 * JOUR).isoformat().replace("+00:00", "Z"),
    )
    conflit = _pr(numero=226, fusionnable=False)
    trouvees = _alertes([_examen(vieux_brouillon), _examen(conflit)])
    assert [a.quoi for a in trouvees][0] == attention.CONFLIT
    assert attention.BROUILLON in [a.quoi for a in trouvees]


def test_la_plus_vieille_passe_devant_dans_une_meme_categorie():
    vieille = _pr(numero=1, relue=False, motif_relecture="rien",
                  ouverte=(MIDI - 9 * JOUR).isoformat().replace("+00:00", "Z"))
    recente = _pr(numero=2, relue=False, motif_relecture="rien",
                  ouverte=(MIDI - JOUR).isoformat().replace("+00:00", "Z"))
    trouvees = [a for a in _alertes([_examen(recente), _examen(vieille)])
                if a.quoi == attention.RETENUE]
    assert [a.depuis for a in trouvees] == sorted(a.depuis for a in trouvees)


def test_rien_qui_attend_rend_une_liste_vide_pas_une_ligne_rassurante():
    """La page dit « rien » elle-même ; ce module ne fabrique pas une
    ligne pour avoir l'air occupé."""
    assert _alertes() == ()
