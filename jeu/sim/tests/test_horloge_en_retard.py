"""La cadence de l'horloge quand un jour prend plus que son intervalle."""

import time

import pytest

from sim.service import ServeurMonde, prochaine_echeance

INTERVALLE_S = 0.1


def test_a_l_heure_les_echeances_restent_absolues():
    """Un jour plus court que son intervalle ne décale rien : dix jours finissent à dix intervalles."""
    echeance = 100.0
    for jour in range(10):
        # Le jour a pris 30 ms : l'échéance suivante ne dépend pas de cette durée.
        echeance = prochaine_echeance(echeance, INTERVALLE_S, echeance + 0.03)
        assert echeance == pytest.approx(100.0 + (jour + 1) * INTERVALLE_S)


def test_en_retard_le_jour_suivant_part_tout_de_suite_sans_rattrapage():
    # Le jour a pris 116 ms pour un intervalle de 100 : le suivant part à la fin du premier.
    assert prochaine_echeance(100.0, INTERVALLE_S, 100.116) == 100.116
    # Une attente d'un intervalle entier donnerait une période de 216 ms au lieu de 116.
    assert prochaine_echeance(100.0, INTERVALLE_S, 100.116) < 100.116 + INTERVALLE_S
    # Dix jours manqués ne se rattrapent pas : après le retard, les échéances repartent de maintenant.
    echeance = prochaine_echeance(100.0, INTERVALLE_S, 101.0)
    assert echeance == 101.0
    assert prochaine_echeance(echeance, INTERVALLE_S, 101.02) == pytest.approx(101.1)
    # Pile à l'heure, le jour suivant part aussitôt.
    assert prochaine_echeance(100.0, INTERVALLE_S, 100.1) == 100.1


@pytest.mark.chronometre
def test_l_horloge_donne_les_jours_que_la_machine_joue(monkeypatch):
    """Des jours de 150 ms à 10 jours par seconde demandés : un jour toutes les 150 ms, pas toutes les 250."""
    jour_s, duree_s = 0.15, 3.0

    def jour_lent(self, generation_attendue=None):
        with self.condition_vitesse:
            if generation_attendue is not None and generation_attendue != self._generation_vitesse:
                return None
        time.sleep(jour_s)
        joues.append(time.monotonic())
        return self.etat_publie

    joues = []
    monkeypatch.setattr(ServeurMonde, "jouer_un_tick", jour_lent)
    with ServeurMonde(("127.0.0.1", 0), 0, 0) as serveur:
        serveur.changer_vitesse(1 / INTERVALLE_S)
        time.sleep(duree_s)
        serveur.changer_vitesse(0)
    # Sans attente ajoutée : 20 jours en 3 s. Avec un intervalle d'attente après chaque retard : 12.
    assert len(joues) >= 0.85 * duree_s / jour_s
    ecarts = [apres - avant for avant, apres in zip(joues, joues[1:])]
    assert max(ecarts) < jour_s + INTERVALLE_S
