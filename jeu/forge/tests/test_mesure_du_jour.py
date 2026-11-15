"""L'outil de mesure : chaque phase du tableau se chronomètre sur une vraie fonction du moteur."""

import pytest

import mesure_du_jour

JOURS = 2


def test_passage_instrumente_compte_chaque_phase_et_tout_le_jour():
    """Une phase renommée dans le moteur fait échouer le passage, au lieu de vider sa ligne."""
    passage = mesure_du_jour._dans_un_processus_neuf(JOURS, mesure_du_jour.GRAINE, ia=True, instrumente=True)
    assert len(passage["jours_ms"]) == len(passage["ticks_ms"]) == JOURS
    phases = passage["phases_ms"]
    # Le tick, l'IA et la publication ont tourné : leurs phases portent du temps.
    for phase in ("IA", "tick : production", "tick : commerce", "tick : consommation",
                  "publication : flux", "publication : lieux", "publication : le reste"):
        assert phases[phase] > 0, phase
    # Les phases et le reste font le jour entier, sans temps compté deux fois.
    assert sum(phases.values()) == pytest.approx(sum(passage["jours_ms"]))
    assert phases[mesure_du_jour.RESTE_DU_JOUR] >= 0
    # Le tick seul tient dans le jour, publication comprise.
    assert all(0 < tick <= jour for tick, jour in zip(passage["ticks_ms"], passage["jours_ms"]))


def test_phase_introuvable_refusee(monkeypatch):
    monkeypatch.setattr(mesure_du_jour, "PHASES_DU_TICK", (("sim.engine", "_phase_disparue", "tick : fantôme"),))
    monkeypatch.setattr(mesure_du_jour, "PHASES_DE_LA_PUBLICATION", ())
    monkeypatch.setattr(mesure_du_jour, "METHODES", ())
    with pytest.raises(AttributeError, match="_phase_disparue"):
        mesure_du_jour.Chronometre().poser()


def test_tableau_porte_les_chiffres_et_l_empreinte():
    colonne = {"ia": False, "jour_ms": 100.0, "jour_mediane_ms": 90.0, "jour_centile_ms": 150.0,
               "jour_max_ms": 200.0, "tick_ms": 60.0, "tick_mediane_ms": 55.0, "publication_ms": 40.0,
               "annee_s": 36.5, "empreinte": "abc", "jour_instrumente_ms": 104.0,
               "phases_ms": {"tick : commerce": 25.0, mesure_du_jour.RESTE_DU_JOUR: 75.0}}
    texte = mesure_du_jour.tableau([colonne], 365, 0)
    assert "sans IA" in texte and "avec IA" not in texte
    assert "tick : commerce" in texte and "25.00 25.0 %" in texte
    # Une phase qui n'a pas tourné n'a pas de ligne.
    assert "tick : migration" not in texte
    assert "empreinte du monde au jour 365, sans IA : abc" in texte
