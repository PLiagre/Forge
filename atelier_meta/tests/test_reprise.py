"""echec/ n'est plus un cul-de-sac, et il ne devient pas une boucle.

Une carte revient seule quand refaire le même geste peut donner un
autre résultat, et seulement dans ce cas. Le reste attend une personne :
un brief absent ne s'écrit pas tout seul, et réessayer à l'identique
brûle un quota pour arriver au même endroit.
"""

from pathlib import Path
import json

import pytest

from atelier import boite, reprise
from atelier.__main__ import main


def _carte(projet: Path, etat: str, lot: str = "044-mineur", **kw) -> None:
    boite.deposer(
        projet, etat,
        boite.Carte(lot=lot, brief=f"briefs/{lot}.md", fichiers=["sim/engine.py"], **kw),
    )


def _en_echec(projet: Path, lot: str = "044-mineur") -> dict:
    fichier = boite.racine_boite(projet) / "echec" / f"{lot}.json"
    return json.loads(fichier.read_text(encoding="utf-8"))


# ------------------------------------------------------------- la règle


def test_ce_qui_se_retente_et_ce_qui_ne_se_retente_pas():
    # Un délai dépassé ne dit rien du travail, seulement de sa durée.
    assert reprise.retentable(reprise.TIMEOUT, essais=1)
    assert reprise.retentable(reprise.TIMEOUT, essais=2)
    # Et il se borne : sans plafond, une cause retentable est une boucle.
    assert not reprise.retentable(reprise.TIMEOUT, essais=3)
    # Un agent qui plante deux fois de suite ne plante pas par hasard.
    assert reprise.retentable(reprise.AGENT, essais=1)
    assert not reprise.retentable(reprise.AGENT, essais=2)


@pytest.mark.parametrize(
    "cause",
    [reprise.BRIEF_ABSENT, reprise.PERIMETRE, reprise.BRANCHE,
     reprise.PR, reprise.VERROU, reprise.AVANCER],
)
def test_ce_qui_demande_une_personne_ne_revient_jamais_seul(cause):
    assert not reprise.retentable(cause, essais=1)
    assert "décision" in reprise.raison_du_refus(cause, essais=1)


def test_une_cause_inconnue_ne_parie_pas_un_quota():
    """On ne retente pas ce qu'on n'a pas nommé : le doute ne dépense pas."""
    assert not reprise.retentable("quelque-chose-de-neuf", essais=1)
    assert not reprise.retentable("", essais=1)


# ------------------------------------------------------------- le rappel


def test_une_carte_qui_a_depasse_le_delai_revient_seule(tmp_path: Path):
    _carte(tmp_path, "a-coder")
    boite.echouer(tmp_path, "coder", "044-mineur", "délai dépassé", reprise.TIMEOUT)
    assert [c.lot for c in boite.lister(tmp_path, "a-coder")] == []

    rappelees = boite.rappeler(tmp_path, "coder")

    assert [c.lot for c in rappelees] == ["044-mineur"]
    assert [c.lot for c in boite.lister(tmp_path, "a-coder")] == ["044-mineur"]
    assert boite.lister(tmp_path, "echec") == []


def test_une_carte_sans_brief_reste_ou_elle_est(tmp_path: Path):
    _carte(tmp_path, "a-coder")
    boite.echouer(tmp_path, "coder", "044-mineur", "brief introuvable", reprise.BRIEF_ABSENT)

    assert boite.rappeler(tmp_path, "coder") == []
    assert [c.lot for c in boite.lister(tmp_path, "echec")] == ["044-mineur"]


def test_la_carte_revient_dans_la_boite_du_role_qui_l_a_laissee_tomber(tmp_path: Path):
    """Un lot qui a échoué en relecture n'est pas un lot à recoder."""
    _carte(tmp_path, "a-relire")
    boite.echouer(tmp_path, "relire", "044-mineur", "l'agent a rendu 7", reprise.AGENT)

    boite.rappeler(tmp_path, "relire")

    assert [c.lot for c in boite.lister(tmp_path, "a-relire")] == ["044-mineur"]
    assert boite.lister(tmp_path, "a-coder") == []


def test_un_role_ne_rappelle_pas_la_carte_d_un_autre(tmp_path: Path):
    _carte(tmp_path, "a-relire")
    boite.echouer(tmp_path, "relire", "044-mineur", "délai dépassé", reprise.TIMEOUT)

    assert boite.rappeler(tmp_path, "coder") == []
    assert [c.lot for c in boite.lister(tmp_path, "echec")] == ["044-mineur"]


def test_le_rappel_ne_fabrique_pas_de_doublon(tmp_path: Path):
    """Si la file porte déjà le lot, la trace reste dans echec/ et rien ne bouge."""
    _carte(tmp_path, "a-coder")
    boite.echouer(tmp_path, "coder", "044-mineur", "délai dépassé", reprise.TIMEOUT)
    _carte(tmp_path, "a-coder")  # le pilote l'a redéposée entre-temps

    assert boite.rappeler(tmp_path, "coder") == []
    assert [c.lot for c in boite.lister(tmp_path, "a-coder")] == ["044-mineur"]
    assert [c.lot for c in boite.lister(tmp_path, "echec")] == ["044-mineur"]


def test_les_essais_se_comptent_et_le_plafond_arrete_la_boucle(tmp_path: Path):
    _carte(tmp_path, "a-coder")
    for attendu in (1, 2, 3):
        boite.echouer(tmp_path, "coder", "044-mineur", "délai dépassé", reprise.TIMEOUT)
        assert _en_echec(tmp_path)["essais"] == attendu
        rappelees = boite.rappeler(tmp_path, "coder")
        if attendu <= reprise.plafond(reprise.TIMEOUT):
            assert [c.lot for c in rappelees] == ["044-mineur"]
        else:
            assert rappelees == []
    assert [c.lot for c in boite.lister(tmp_path, "echec")] == ["044-mineur"]


# ---------------------------------------------- le second échec du même lot


def test_un_second_echec_ecrase_le_premier_au_lieu_de_lever(tmp_path: Path):
    """Mesuré : `echouer` levait « carte déjà là », `tour.sh` sortait avant
    de lever le verrou, la carte restait dans la file du rôle — et le
    réveil suivant la repayait. Une boucle de dépense.
    """
    _carte(tmp_path, "a-coder")
    boite.echouer(tmp_path, "coder", "044-mineur", "premier", reprise.AGENT)
    _carte(tmp_path, "a-coder")

    boite.echouer(tmp_path, "coder", "044-mineur", "second", reprise.AGENT)

    assert [c.lot for c in boite.lister(tmp_path, "echec")] == ["044-mineur"]
    assert boite.lister(tmp_path, "a-coder") == []
    trace = _en_echec(tmp_path)
    assert trace["note"] == "second"
    assert trace["essais"] == 2


# --------------------------------------------------- une carte illisible


def test_une_carte_illisible_est_ecartee_et_la_file_repart(tmp_path: Path):
    """Un seul JSON tronqué bloquait le rôle à chaque réveil."""
    dossier = boite._ouvrir(tmp_path, "a-coder")
    (dossier / "000-corrompue.json").write_text("{ pas du json", encoding="utf-8")
    _carte(tmp_path, "a-coder", lot="044-mineur")

    cartes = boite.lister(tmp_path, "a-coder")

    assert [c.lot for c in cartes] == ["044-mineur"]
    # Écartée, pas effacée : c'est le fichier qu'on répare.
    assert (dossier / f"000-corrompue.json{boite.SUFFIXE_ILLISIBLE}").is_file()
    assert not (dossier / "000-corrompue.json").exists()


def test_une_carte_vide_echoue_toujours(tmp_path: Path):
    """« Je ne sais pas lire ce fichier » n'est pas « ce fichier dit faux ».

    Une carte vide dit quelque chose de faux : l'échantillon vide
    échoue, et la file s'arrête pour qu'on répare.
    """
    dossier = boite._ouvrir(tmp_path, "a-coder")
    (dossier / "vide.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(boite.BoiteErreur):
        boite.lister(tmp_path, "a-coder")


# --------------------------------------------------------- reprendre élargi


@pytest.mark.parametrize("depuis", ["faite", "a-relire", "echec"])
def test_reprendre_sort_une_carte_de_n_importe_quelle_boite(tmp_path: Path, capsys, depuis):
    """`faite` et `a-relire` n'avaient aucune sortie : il fallait supprimer
    un fichier JSON à la main pour remettre une carte en circulation.
    """
    _carte(tmp_path, depuis)
    from atelier import verrou
    verrou.poser(tmp_path, "044-mineur", ["sim/engine.py"])

    assert main(["reprendre", "--projet", str(tmp_path), "--lot", "044-mineur"]) == 0

    assert boite.lister(tmp_path, depuis) == []
    # Le verrou tombe avec elle : sinon les fichiers resteraient tenus
    # par un lot qui n'est plus nulle part.
    assert verrou.charger(tmp_path).poses == []
    assert depuis in capsys.readouterr().out


def test_reprendre_le_dit_quand_aucune_boite_ne_porte_la_carte(tmp_path: Path, capsys):
    assert main(["reprendre", "--projet", str(tmp_path), "--lot", "999-fantome"]) == 1
    assert "aucune boîte" in capsys.readouterr().err
