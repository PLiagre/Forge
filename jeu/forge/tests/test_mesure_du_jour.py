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


@pytest.mark.longue
def test_temoin_couvre_tout_ce_qui_est_publie(monkeypatch):
    """Un témoin qui ne lirait que `/monde` n'est pas celui de toute la publication."""
    premier = mesure_du_jour.temoin(1, mesure_du_jour.GRAINE, ia=False)
    # Les lieux, les plans, les occupations et les maisons pèsent bien plus que le monde seul.
    monkeypatch.setattr(mesure_du_jour, "_octets_publies", lambda serveur, etat: [etat.monde])
    monde_seul = mesure_du_jour.temoin(1, mesure_du_jour.GRAINE, ia=False)
    assert monde_seul["empreinte"] == premier["empreinte"]
    assert monde_seul["publication"] != premier["publication"]
    assert 0 < monde_seul["octets"] < premier["octets"]


def test_comparaison_joue_les_deux_checkouts_sur_le_meme_monde():
    """Ce checkout contre lui-même : une manche, deux passages, le même monde au dernier jour."""
    colonne = mesure_du_jour.comparer(JOURS, mesure_du_jour.GRAINE, False, mesure_du_jour.JEU, manches=1)
    (manche,) = colonne["manches"]
    assert manche["meme_monde"] is True
    for cote in ("avant", "apres"):
        assert 0 < manche[cote]["tick_ms"] <= manche[cote]["jour_ms"]
        assert manche[cote]["publication_ms"] == pytest.approx(manche[cote]["jour_ms"] - manche[cote]["tick_ms"])


def test_tableau_compare_dit_le_gain_de_chaque_manche_et_un_monde_qui_differe():
    def manche(avant, apres, meme):
        return {"meme_monde": meme,
                "avant": {"jour_ms": avant, "tick_ms": avant / 2, "publication_ms": avant / 2},
                "apres": {"jour_ms": apres, "tick_ms": apres / 2, "publication_ms": apres / 2}}
    colonne = {"ia": True, "manches": [manche(200.0, 100.0, True), manche(100.0, 80.0, True), manche(100.0, 90.0, True)]}
    texte = mesure_du_jour.tableau_compare([colonne], 365, 0, mesure_du_jour.JEU)
    # Le gain se lit manche par manche, puis par sa médiane, jamais par une moyenne des millisecondes.
    assert "50.0 %" in texte and "20.0 %" in texte and "10.0 %" in texte
    assert "le jour  médiane" in texte and texte.count("  20.0 %") == 6
    assert "est le même des deux côtés" in texte and "DIFFÈRE" not in texte
    colonne["manches"][1]["meme_monde"] = False
    assert "DIFFÈRE" in mesure_du_jour.tableau_compare([colonne], 365, 0, mesure_du_jour.JEU)


def test_comparaison_refuse_un_dossier_qui_n_est_pas_un_checkout(tmp_path, capsys):
    with pytest.raises(SystemExit):
        mesure_du_jour.main(["--contre", str(tmp_path)])
    assert "n'est pas le dossier jeu d'un checkout" in capsys.readouterr().err
