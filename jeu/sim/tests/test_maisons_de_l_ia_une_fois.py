"""La liste des maisons de l'IA, calculée une fois par la boucle de jeu.

`capitales.maisons_de_l_ia` refaisait à chaque tick, par point dans polygone
et en relisant les tables de 1400, une liste qui ne dépend que des tables et
de la carte : 170 ms sur les 218 de `jouer_ia` (docs/mesures/2026-11-07-refonte,
section 2). Les boucles (`python -m sim --ia`, la forge, le service) la
calculent une fois avec `toutes_les_maisons_de_l_ia` et la donnent à
`jouer_ia`, qui écarte la maison du joueur à chaque tick. La preuve : même
graine, mêmes gestes, même monde, octet pour octet ; et la liste donnée est
bien celle qui sert.
"""
import copy
import json
import random

import pytest

import sim.ia as ia
from sim import engine
from sim.capitales import maisons_de_l_ia, toutes_les_maisons_de_l_ia
from sim.intentions import deposer_intention
from sim.seigneuries import charger_seigneuries, identifiant_de_seigneurie
from sim.world import World

TICKS = 75


def _jouer(monde, ticks, maisons=None):
    rng, releve = random.Random(0), []
    for _ in range(ticks):
        ia.jouer_ia(monde, releve, maisons)
        engine.tick(monde, rng, monde.ticks_ecoules)
    return releve


def _octets(monde, releve):
    return (json.dumps(monde.to_dict(), sort_keys=True, ensure_ascii=False),
            json.dumps(releve, sort_keys=True, ensure_ascii=False))


@pytest.fixture(scope="module")
def depart():
    return World.charger(rng_seed=0)


def test_la_liste_contient_toutes_les_maisons_et_la_vue_ecarte_le_joueur(depart):
    toutes = toutes_les_maisons_de_l_ia(depart)
    assert toutes == maisons_de_l_ia(depart)  # sans joueur, les deux vues sont égales
    choisi = copy.deepcopy(depart)
    seigneurie = charger_seigneuries()[0]
    choisi.maison_du_joueur = identifiant_de_seigneurie(seigneurie.id)
    assert toutes_les_maisons_de_l_ia(choisi) == toutes
    vue = maisons_de_l_ia(choisi)
    assert len(vue) == len(toutes) - 1
    assert all(not (m.sorte == "seigneurie" and m.id == seigneurie.id) for m in vue)


def test_meme_graine_memes_gestes_meme_monde(depart):
    refait, une_fois = copy.deepcopy(depart), copy.deepcopy(depart)
    releve_refait = _jouer(refait, TICKS)
    releve_une_fois = _jouer(une_fois, TICKS, toutes_les_maisons_de_l_ia(une_fois))
    assert releve_refait, "échantillon vide : l'IA n'a rien proposé"
    assert _octets(une_fois, releve_une_fois) == _octets(refait, releve_refait)


def test_la_maison_choisie_par_le_joueur_reste_hors_de_l_ia(depart):
    seigneurie = charger_seigneuries()[0]
    refait, une_fois = copy.deepcopy(depart), copy.deepcopy(depart)
    for monde in (refait, une_fois):
        deposer_intention(monde, {"type": "choisir_depart", "seigneurie": seigneurie.id})
    liste = toutes_les_maisons_de_l_ia(une_fois)
    assert any(m.sorte == "seigneurie" and m.id == seigneurie.id for m in liste)
    releve_refait = _jouer(refait, TICKS)
    releve_une_fois = _jouer(une_fois, TICKS, liste)
    assert _octets(une_fois, releve_une_fois) == _octets(refait, releve_refait)
    assert not [e for e in releve_une_fois
                if e["maison"] == {"sorte": "seigneurie", "id": seigneurie.id}]


def test_la_liste_donnee_est_celle_qui_sert(depart, monkeypatch):
    liste = toutes_les_maisons_de_l_ia(depart)

    def refaite(_monde):
        raise AssertionError("jouer_ia refait la liste qu'on lui a donnée")

    monde = copy.deepcopy(depart)
    with monkeypatch.context() as sonde:
        sonde.setattr(ia, "maisons_de_l_ia", refaite)
        releve = _jouer(monde, TICKS, liste)
        assert releve
        # Contre-épreuve : sans liste, la vue est refaite (et la sonde le voit).
        with pytest.raises(AssertionError, match="refait"):
            ia.jouer_ia(copy.deepcopy(depart), [])
    # Contre-épreuve : une liste amputée change les gestes, elle est donc lue.
    actives = {(e["maison"]["sorte"], e["maison"]["id"]) for e in releve}
    retiree = next(m for m in liste if (m.sorte, m.id) in actives)
    amputee = tuple(m for m in liste if m is not retiree)
    releve_ampute = _jouer(copy.deepcopy(depart), TICKS, amputee)
    assert not [e for e in releve_ampute
                if (e["maison"]["sorte"], e["maison"]["id"]) == (retiree.sorte, retiree.id)]
