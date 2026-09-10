"""Un inconnu vaut -1. hop refuse de tirer au sort."""

import pytest

from atelier.quota import INCONNU, Quota, hop


def test_sentinelle():
    assert INCONNU == -1
    assert not Quota("cursor", INCONNU).connu
    assert not Quota("cursor", INCONNU).epuise


def test_zero_est_une_mesure():
    q = Quota("claude", 0)
    assert q.connu
    assert q.epuise


def test_hop_prend_le_plus_de_marge():
    choisi = hop(
        [
            Quota("claude", 10),
            Quota("cursor", 80),
            Quota("codex", INCONNU),
        ]
    )
    assert choisi.agent == "cursor"


def test_hop_refuse_si_tout_inconnu():
    with pytest.raises(ValueError, match="inconnu"):
        hop([Quota("claude", INCONNU), Quota("cursor", INCONNU)])


def test_hop_refuse_si_tout_epuise():
    with pytest.raises(ValueError, match="épuis"):
        hop([Quota("claude", 0), Quota("cursor", 0)])


def test_hop_echantillon_vide_echoue():
    with pytest.raises(ValueError, match="vide"):
        hop([])
