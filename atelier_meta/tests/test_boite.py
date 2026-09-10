"""Crons indépendants : une boîte vide n'est pas un échec."""

from pathlib import Path

import pytest

from atelier import boite
from atelier.__main__ import main


def _carte(lot: str = "044-mineur") -> boite.Carte:
    return boite.Carte(
        lot=lot,
        brief=f"briefs/{lot}.md",
        fichiers=["sim/engine.py"],
    )


def test_prochain_vide_est_rien(tmp_path: Path):
    assert boite.prochain(tmp_path, "coder") is None


def test_coder_ne_depend_pas_du_planificateur(tmp_path: Path):
    # Grok a une carte en attente : Composer s'en fiche.
    boite.deposer(tmp_path, "a-planifier", _carte("046-mer"))
    boite.deposer(tmp_path, "a-coder", _carte("044-mineur"))
    prise = boite.prochain(tmp_path, "coder")
    assert prise is not None
    assert prise.lot == "044-mineur"
    assert boite.prochain(tmp_path, "planifier") is not None


def test_echec_ne_bloque_pas_l_autre_role(tmp_path: Path):
    boite.deposer(tmp_path, "a-briefer", _carte("044-mineur"))
    boite.deposer(tmp_path, "a-coder", _carte("047-bourg"))
    boite.echouer(tmp_path, "briefer", "044-mineur", "quota claude épuisé")
    assert boite.prochain(tmp_path, "briefer") is None
    assert boite.prochain(tmp_path, "coder").lot == "047-bourg"
    assert boite.lister(tmp_path, "echec")[0].note == "quota claude épuisé"


def test_avancer_briefer_attend_la_fusion_du_brief(tmp_path: Path):
    # Le brief est en PR : ni le planificateur ni le coder ne le trouveraient
    # sur master. La carte attend la fusion ; le pilote redéposera d'après
    # la feuille de route.
    boite.deposer(tmp_path, "a-briefer", _carte())
    cible = boite.avancer(tmp_path, "briefer", "044-mineur")
    assert cible.parent.name == "brief-a-fusionner"
    assert boite.prochain(tmp_path, "planifier") is None
    assert boite.prochain(tmp_path, "coder") is None


def test_cli_rien_sort_zero(tmp_path: Path):
    code = main(["prochain", "--projet", str(tmp_path), "--role", "coder"])
    assert code == 0


def test_cli_rien_affiche_rien(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    main(["prochain", "--projet", str(tmp_path), "--role", "relire"])
    assert capsys.readouterr().out.strip() == "RIEN"


def test_carte_vide_echoue(tmp_path: Path):
    dossier = boite._ouvrir(tmp_path, "a-coder")
    (dossier / "vide.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(boite.BoiteErreur):
        boite.lister(tmp_path, "a-coder")


def test_une_carte_sans_brief_n_en_est_pas_une(tmp_path: Path):
    # Un échantillon vide qui traverse la boîte ferait dépenser un
    # quota sur une instruction qui n'existe pas.
    with pytest.raises(boite.BoiteErreur):
        boite.Carte(lot="044-mineur", brief="", fichiers=[])


def test_avancer_ne_reecrit_pas_le_brief(tmp_path: Path):
    # Le brief est la seule source d'instruction : un rôle qui passe
    # la carte au suivant ne change pas ce qu'elle nomme.
    boite.deposer(tmp_path, "a-planifier", _carte())
    with pytest.raises(boite.BoiteErreur):
        boite.avancer(tmp_path, "planifier", "044-mineur", brief="autre.md")
    assert boite.prochain(tmp_path, "planifier").brief == "briefs/044-mineur.md"


def test_avancer_accepte_la_pr_et_la_note(tmp_path: Path):
    boite.deposer(tmp_path, "a-coder", _carte())
    boite.avancer(tmp_path, "coder", "044-mineur", pr=44, note="PR ouverte")
    prise = boite.prochain(tmp_path, "relire")
    assert prise.pr == 44 and prise.note == "PR ouverte"


def test_le_coder_saute_une_carte_verrouillee(tmp_path: Path):
    # « 044 occupe engine.py ? 046 attend. Le cron prend 047. »
    from atelier import verrou

    verrou.poser(tmp_path, "044-mineur", ["sim/engine.py"])
    boite.deposer(
        tmp_path, "a-coder",
        boite.Carte(lot="046-mer", brief="briefs/046-mer.md", fichiers=["sim/engine.py"]),
    )
    boite.deposer(
        tmp_path, "a-coder",
        boite.Carte(lot="047-bourg", brief="briefs/047-bourg.md", fichiers=["sim/monde.py"]),
    )
    assert boite.prochain(tmp_path, "coder").lot == "047-bourg"


def test_tout_verrouille_vaut_rien(tmp_path: Path):
    from atelier import verrou

    verrou.poser(tmp_path, "044-mineur", ["sim/engine.py"])
    boite.deposer(
        tmp_path, "a-coder",
        boite.Carte(lot="046-mer", brief="briefs/046-mer.md", fichiers=["sim/engine.py"]),
    )
    assert boite.prochain(tmp_path, "coder") is None


def test_le_relecteur_ne_regarde_pas_les_verrous(tmp_path: Path):
    # Relire ne touche pas aux fichiers : un verrou ne le suspend pas.
    from atelier import verrou

    verrou.poser(tmp_path, "044-mineur", ["sim/engine.py"])
    boite.deposer(tmp_path, "a-relire", _carte())
    assert boite.prochain(tmp_path, "relire") is not None


def test_regarder_une_boite_vide_n_ecrit_rien(tmp_path: Path):
    # « Sans --run, rien n'est écrit. » Un aperçu n'est pas une dépense,
    # et regarder une boîte n'est pas la créer.
    assert boite.prochain(tmp_path, "coder") is None
    assert boite.lister(tmp_path, "echec") == []
    assert not (tmp_path / ".atelier").exists()
