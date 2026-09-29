"""Les verrous des tours parallèles : deux instances sur le même dossier se
comportent comme deux processus (flock verrouille par fichier ouvert)."""

from __future__ import annotations

import sys

import pytest

from atelier.verrous import AucunVerrou, VerrouOccupe, Verrous

pytestmark = pytest.mark.skipif(sys.platform.startswith("win"), reason="flock : le pilote ne tourne que sur le VPS")


def test_un_verrou_pris_par_un_tour_ne_se_prend_pas_ailleurs(tmp_path):
    a, b = Verrous(tmp_path), Verrous(tmp_path)
    assert a.prendre("lot-12")
    assert a.prendre("lot-12"), "un tour qui tient déjà son verrou le garde"
    assert not b.prendre("lot-12")
    assert b.pris_ailleurs("lot-12") and not a.pris_ailleurs("lot-12")
    a.lacher("lot-12")
    assert b.prendre("lot-12") and a.pris_ailleurs("lot-12")


def test_un_verrou_lache_par_un_processus_mort_se_reprend(tmp_path):
    a = Verrous(tmp_path)
    assert a.prendre("decider")
    # Un processus qui meurt ferme ses fichiers : le système rend le verrou.
    for f in list(a._tenus.values()):
        f.close()
    assert Verrous(tmp_path).prendre("decider")


def test_tenir_attend_son_tour_puis_renonce(tmp_path):
    a, b = Verrous(tmp_path), Verrous(tmp_path)
    b.ATTENTE_ENTRE_ESSAIS = 0.01
    with a.tenir("decider"):
        with a.tenir("decider"):  # réentrant : le même tour ne s'attend pas
            pass
        assert a.pris_ailleurs("decider") is False and b.pris_ailleurs("decider")
        with pytest.raises(VerrouOccupe, match="decider"):
            with b.tenir("decider", attente=0.05):
                pass
    with b.tenir("decider", attente=0.05):
        assert a.pris_ailleurs("decider")
    assert not a.pris_ailleurs("decider")


def test_un_outil_n_a_que_ses_places(tmp_path):
    a, b, c = Verrous(tmp_path), Verrous(tmp_path), Verrous(tmp_path)
    with a.place("outil-codex", 2) as premiere, b.place("outil-codex", 2) as seconde:
        assert premiere and seconde
        assert a.pris_ailleurs("outil-codex-2") and b.pris_ailleurs("outil-codex-1")
        with c.place("outil-codex", 2) as troisieme:
            assert not troisieme
        with c.place("outil-claude", 2) as autre_outil:
            assert autre_outil
    with c.place("outil-codex", 2) as liberee:
        assert liberee
    with c.place("outil-codex", None) as sans_plafond:
        assert sans_plafond


def test_sans_verrou_tout_est_libre():
    rien = AucunVerrou()
    assert rien.prendre("lot-1") and not rien.pris_ailleurs("lot-1")
    with rien.tenir("decider"), rien.place("outil-codex", 1) as libre:
        assert libre


def test_le_depot_fait_ses_gestes_git_un_a_la_fois(tmp_path):
    from atelier.depot import Depot

    appels = []
    depot = Depot(tmp_path, "master", executeur=lambda argv, cwd: (appels.append(argv), (0, "", ""))[1],
                  verrous=Verrous(tmp_path / "v"))
    depot.ATTENTE_GIT = 0.05
    autre = Verrous(tmp_path / "v")
    assert autre.prendre("git")  # un autre tour pousse
    with pytest.raises(VerrouOccupe, match="git"):
        depot.git_code("status")
    assert appels == []
    autre.lacher("git")
    depot.git_code("status")
    assert appels == [["git", "status"]]


def test_une_publication_de_captures_a_la_fois(tmp_path):
    from atelier import captures
    from atelier.depot import Depot

    depot = Depot(tmp_path, "master", executeur=lambda argv, cwd: (0, "", ""), verrous=Verrous(tmp_path / "v"))
    depot.ATTENTE_GIT = 0.05
    image = tmp_path / "carte.png"
    image.write_bytes(b"png")
    autre = Verrous(tmp_path / "v")
    assert autre.prendre("captures")  # le journal publie sa carte du matin
    with pytest.raises(VerrouOccupe, match="captures"):
        captures.publier(depot, "moi/essai", [image], "2026-09-29")
