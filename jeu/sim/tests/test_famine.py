"""Lot #1029 : la famine, premier événement du monde, pose ses modificateurs au lieu qui a faim.

Un lieu dont la faim dépasse `FAIM_AVANT_SECOURS_JOURS` reçoit la pose « Famine »
(−50 % de natalité, source `evenement:famine`), prolongée chaque jour de faim et
effacée 365 jours après le dernier. Réponse A du propriétaire, 10 novembre 2026.
Chaque preuve a sa contre-épreuve : une fausse règle fait échouer la vérification.
"""
import copy
import dataclasses
import json
import random

import pytest

import sim.constants as c
import sim.evenements as evenements
from sim import engine, modificateurs as M
from sim.tests.amorcage_d_avant import couper_la_famine
from sim.tests.test_modificateurs import _masse
from sim.world import World

NOURRITURE = c.MARCHANDISE_NOURRITURE
SEUIL = c.FAIM_AVANT_SECOURS_JOURS
TICKS_DE_LA_PREUVE = 60
# La vraie règle, gardée avant qu'une épreuve ne la remplace dans le module.
_POSER_LES_FAMINES = evenements.poser_les_famines


@pytest.fixture(scope="module")
def donnees():
    return M.charger_donnees()


@pytest.fixture(scope="module")
def depart():
    return World.charger(rng_seed=0)


def _famines(monde):
    return [p for p in monde.modificateurs if p.identifiant == "famine"]


def _jouer_en_relevant(monde):
    """60 ticks : le tick où chaque lieu atteint le premier jour au-dessus du seuil de faim."""
    rng, atteint = random.Random(0), {}
    for numero in range(TICKS_DE_LA_PREUVE):
        engine.tick(monde, rng, numero)
        for cid, cellule in monde.cells.items():
            for lieu in cellule.lieux:
                if lieu.duree_faim_ticks * c.TICK_DURATION_DAYS == SEUIL + 1:
                    atteint.setdefault((cid, lieu.rang), numero)
    return atteint


def _verifier_au_jour_dit(monde, atteint):
    poses = _famines(monde)
    assert poses, "aucune famine posée : la preuve ne porte sur rien"
    assert atteint, "aucun lieu n'a dépassé le seuil de faim : la preuve ne porte sur rien"
    for pose in poses:
        cle = pose.cible[1:]
        assert pose.cible[0] == "lieu" and cle in atteint, f"famine sans faim au-dessus du seuil : {pose.cible}"
        assert pose.debut == atteint[cle], f"{pose.cible} : début {pose.debut}, 8e jour de faim {atteint[cle]}"
        assert pose.source == "evenement:famine"
    assert {p.cible[1:] for p in poses} == set(atteint)
    assert len(poses) == len({p.cible for p in poses})


@pytest.fixture(scope="module")
def monde_de_soixante_ticks():
    monde = World.charger(rng_seed=0)
    return monde, _jouer_en_relevant(monde)


def test_la_famine_est_posee_au_jour_dit_et_seulement_avec_la_faim(monde_de_soixante_ticks, monkeypatch):
    monde, atteint = monde_de_soixante_ticks
    _verifier_au_jour_dit(monde, atteint)

    # Contre-épreuve : une fausse règle pose sur les lieux peuplés de la cellule la plus peuplée, sans
    # regarder leur faim (poser sur tous les lieux du monde rendrait chaque tick interminable).
    def sans_regarder_la_faim(monde, affames, donnees=None):
        cid = max(monde.cells, key=lambda k: monde.cells[k].population)
        for lieu in monde.cells[cid].lieux:
            if lieu.population > 0 and not any(
                    p.identifiant == "famine" and p.cible == ("lieu", cid, lieu.rang) for p in monde.modificateurs):
                M.poser(monde, "famine", "evenement:famine", {"lieu": [cid, lieu.rang]}, donnees)
        return []

    monkeypatch.setattr(evenements, "poser_les_famines", sans_regarder_la_faim)
    faux = World.charger(rng_seed=0)
    with pytest.raises(AssertionError):
        _verifier_au_jour_dit(faux, _jouer_en_relevant(faux))


# --- Prolongée, puis effacée -------------------------------------------------------

def _un_lieu(monde):
    cid = max(monde.cells, key=lambda k: monde.cells[k].population)
    return cid, 0, monde.cells[cid].lieux[0]


def _verifier_prolongee_puis_effacee(poseuse, depart, donnees):
    monde = copy.deepcopy(depart)
    cid, rang, lieu = _un_lieu(monde)
    duree = donnees.definitions["famine"].duree_jours // c.TICK_DURATION_DAYS
    monde.ticks_ecoules = 100
    # Le 7e jour de faim : rien. Le 8e : la famine, du tick courant à 365 jours plus tard.
    lieu.duree_faim_ticks = SEUIL // c.TICK_DURATION_DAYS
    poseuse(monde, {(cid, rang)}, donnees)
    assert _famines(monde) == []
    lieu.duree_faim_ticks += 1
    poseuse(monde, {(cid, rang)}, donnees)
    (pose,) = _famines(monde)
    assert (pose.debut, pose.fin) == (100, 100 + duree) and pose.cible == ("lieu", cid, rang)
    # Un jour de faim de plus, au tick L : la fin devient L + 365, le début reste, aucune seconde pose.
    dernier = 110
    monde.ticks_ecoules = dernier
    lieu.duree_faim_ticks += 1
    poseuse(monde, {(cid, rang)}, donnees)
    (pose,) = _famines(monde)
    assert (pose.debut, pose.fin) == (100, dernier + duree)
    # Encore là à L + 364, partie à L + 365.
    monde.ticks_ecoules = dernier + duree - 1
    M.expirer(monde)
    assert len(_famines(monde)) == 1
    monde.ticks_ecoules = dernier + duree
    M.expirer(monde)
    assert _famines(monde) == []
    # Un lieu dont la faim est de 0 n'a rien.
    lieu.duree_faim_ticks = 0
    poseuse(monde, {(cid, rang)}, donnees)
    assert _famines(monde) == []


def test_la_famine_est_prolongee_puis_s_efface_365_jours_apres_le_dernier_jour_de_faim(depart, donnees):
    _verifier_prolongee_puis_effacee(evenements.poser_les_famines, depart, donnees)

    # Contre-épreuve : une famine sans fin ne s'efface jamais.
    def sans_fin(monde, affames, donnees=None):
        _POSER_LES_FAMINES(monde, affames, donnees)
        monde.modificateurs = [dataclasses.replace(p, fin=None) for p in monde.modificateurs]

    with pytest.raises(AssertionError):
        _verifier_prolongee_puis_effacee(sans_fin, depart, donnees)

    # Contre-épreuve : une famine jamais prolongée garde sa fin du premier jour.
    def jamais_prolongee(monde, affames, donnees=None):
        neufs = {cle for cle in affames if not any(p.cible == ("lieu", *cle) for p in _famines(monde))}
        _POSER_LES_FAMINES(monde, neufs, donnees)

    with pytest.raises(AssertionError):
        _verifier_prolongee_puis_effacee(jamais_prolongee, depart, donnees)


# --- Les naissances baissent de la valeur posée, au tick près ----------------------------

def _naissances_d_un_tick(monde, monkeypatch):
    """Un tick : par lieu, (population avant, reste avant, naissances) tels que `_apply_natalite` les voit."""
    vu = {}
    original = engine._apply_natalite

    def enrober(cell, penurie_kg, facteurs=None):
        avant = {lieu.rang: (lieu.population, lieu.natalite_remainder) for lieu in cell.lieux}
        original(cell, penurie_kg, facteurs)
        for lieu in cell.lieux:
            vu[(cell.cell_id, lieu.rang)] = (*avant[lieu.rang], lieu.population - avant[lieu.rang][0])

    with monkeypatch.context() as m:
        m.setattr(engine, "_apply_natalite", enrober)
        engine.tick(monde, random.Random(0), 0)
    return vu


def _verifier_les_naissances(depart, donnees_posees, donnees_du_depot, monkeypatch):
    cid, rang, _ = _un_lieu(depart)
    temoin, famine = copy.deepcopy(depart), copy.deepcopy(depart)
    lieu = famine.cells[cid].lieux[rang]
    # Faim fixée à la main au-dessus du seuil, la pose faite par l'événement, puis le lieu mange de nouveau.
    lieu.duree_faim_ticks = SEUIL // c.TICK_DURATION_DAYS + 1
    evenements.poser_les_famines(famine, {(cid, rang)}, donnees_posees)
    lieu.duree_faim_ticks, lieu.dette_alimentaire_kg = 0, 0.0
    assert len(_famines(famine)) == 1
    vu_temoin = _naissances_d_un_tick(temoin, monkeypatch)
    vu_famine = _naissances_d_un_tick(famine, monkeypatch)
    taux = c.naissances_par_habitant_par_tick()
    facteur = 1 + donnees_du_depot.definitions["famine"].valeur
    population, reste, naissances = vu_famine[(cid, rang)]
    population_t, reste_t, naissances_t = vu_temoin[(cid, rang)]
    assert (population, reste) == (population_t, reste_t)
    assert naissances_t == int(population * taux + reste)
    assert naissances == int(population * (taux * facteur) + reste)
    assert naissances < naissances_t
    assert {k: v for k, v in vu_famine.items() if k != (cid, rang)} == {k: v for k, v in vu_temoin.items() if k != (cid, rang)}


def test_les_naissances_d_un_lieu_nourri_baissent_de_la_valeur_posee(depart, donnees, monkeypatch):
    assert donnees.definitions["famine"].valeur == -0.5
    _verifier_les_naissances(depart, donnees, donnees, monkeypatch)

    # Contre-épreuve : une valeur de −0,25 dans des données d'épreuve ne donne pas les naissances de −0,5.
    moins_forte = dataclasses.replace(donnees.definitions["famine"], valeur=-0.25)
    epreuve = M.Donnees(donnees.sources, donnees.grandeurs, {**donnees.definitions, "famine": moins_forte})
    with pytest.raises(AssertionError):
        _verifier_les_naissances(depart, epreuve, donnees, monkeypatch)


# --- Ni kilo, ni mort de plus ----------------------------------------------------------

def _affamer(monde, cid):
    """La cellule sans vivres et déjà endettée : le lieu a faim, doit, et perd des gens par la dette."""
    cellule = monde.cells[cid]
    for lieu in cellule.lieux:
        lieu.stocks[NOURRITURE] = 0.0
        lieu.dette_alimentaire_kg = 0.0
    cellule.stocks[NOURRITURE] = 0.0
    cellule.food_deficit_kg = cellule.population * c.FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK * 30
    cellule.lieux[0].dette_alimentaire_kg = cellule.food_deficit_kg
    cellule.lieux[0].duree_faim_ticks = SEUIL // c.TICK_DURATION_DAYS + 3


def _un_tick_avec_la_famine(depart, donnees, avec, monkeypatch, poseuse=None):
    """Un tick du monde de départ, deux cellules : la plus peuplée nourrie, l'autre affamée et endettée."""
    monde = copy.deepcopy(depart)
    peuplees = sorted(monde.cells, key=lambda k: -monde.cells[k].population)
    nourrie, affamee = peuplees[0], peuplees[1]
    _affamer(monde, affamee)
    if avec:
        nourri = monde.cells[nourrie].lieux[0]
        nourri.duree_faim_ticks = SEUIL // c.TICK_DURATION_DAYS + 1
        evenements.poser_les_famines(monde, {(nourrie, 0), (affamee, 0)}, donnees)
        nourri.duree_faim_ticks = 0
        assert len(_famines(monde)) == 2
    morts, naissances = {}, {}
    mortalite, natalite = engine._apply_mortality, engine._apply_natalite

    def enrober_mortalite(cell, *args):
        avant = cell.population
        mortalite(cell, *args)
        morts[cell.cell_id] = avant - cell.population

    def enrober_natalite(cell, *args):
        avant = cell.population
        natalite(cell, *args)
        naissances[cell.cell_id] = cell.population - avant

    with monkeypatch.context() as m:
        m.setattr(engine, "_apply_mortality", enrober_mortalite)
        m.setattr(engine, "_apply_natalite", enrober_natalite)
        if poseuse is not None:
            m.setattr(evenements, "poser_les_famines", poseuse)
        engine.tick(monde, random.Random(0), 0)
    return monde, affamee, morts, naissances


def _verifier_ni_kilo_ni_mort(depart, donnees, monkeypatch, poseuse=None):
    temoin, affamee, morts_t, naissances_t = _un_tick_avec_la_famine(depart, donnees, False, monkeypatch)
    famine, _, morts, naissances = _un_tick_avec_la_famine(depart, donnees, True, monkeypatch, poseuse)
    assert morts_t[affamee] > 0, "le lieu affamé ne perd personne dans le témoin : la preuve ne porte sur rien"
    assert _masse(famine) == _masse(temoin)
    assert morts[affamee] == morts_t[affamee]
    assert naissances[affamee] == naissances_t[affamee] == 0
    assert "mortalite" not in famine.facteurs_du_tick and "natalite" in famine.facteurs_du_tick


def test_la_famine_ni_kilo_ni_mort_de_plus_et_la_faim_tue_comme_avant(depart, donnees, monkeypatch):
    _verifier_ni_kilo_ni_mort(depart, donnees, monkeypatch)

    # Contre-épreuve : une fausse famine qui retire un kilo au panier du lieu fait échouer le bilan.
    def retire_un_kilo(monde, affames, donnees=None):
        _POSER_LES_FAMINES(monde, affames, donnees)
        for pose in _famines(monde):
            monde.cells[pose.cible[1]].stocks[NOURRITURE] -= 1.0
        return []

    with pytest.raises(AssertionError):
        _verifier_ni_kilo_ni_mort(depart, donnees, monkeypatch, retire_un_kilo)


# --- L'infobulle dit la fin ------------------------------------------------------------

def _servir_la_famine(donnees):
    from sim.service import ServeurMonde
    with ServeurMonde(("127.0.0.1", 0), 0, 0) as serveur:
        monde = serveur.world
        cid, rang, lieu = _un_lieu(monde)
        monde.ticks_ecoules = 40
        lieu.duree_faim_ticks = SEUIL // c.TICK_DURATION_DAYS + 1
        evenements.poser_les_famines(monde, {(cid, rang)}, donnees)
        lieu.duree_faim_ticks = 0
        M.poser(monde, "moulin", "batiment:moulin", {"cellule": cid}, donnees)
        monde.ticks_ecoules = 50
        servi = json.loads(serveur._construire_etat(0, -1).modificateurs)
        pose = _famines(monde)[0]
    bourg = next(ligne for ligne in servi["lieux"] if (ligne["cell_id"], ligne["rang"]) == (cid, rang))
    return servi, pose, bourg["grandeurs"]


def test_l_infobulle_dit_la_fin_de_la_famine_par_fin_date(donnees):
    servi, pose, grandeurs = _servir_la_famine(donnees)
    (ligne,) = grandeurs["natalite"]["lignes"]
    assert (ligne["nom"], ligne["valeur"], ligne["source_dite"]) == ("Famine", -0.5, "événement")
    assert servi["tick"] == 50 and pose.fin == 40 + 365
    assert ligne["reste_jours"] == (pose.fin - servi["tick"]) * c.TICK_DURATION_DAYS
    assert ligne["fin_date"] == c.date_de_tick(pose.fin)
    # Une pose sans fin (le moulin) n'a pas de date de fin.
    (moulin,) = grandeurs["recolte"]["lignes"]
    assert moulin["fin"] is None and moulin["fin_date"] is None
    # Contre-épreuve : une date calculée sur le début n'est pas celle de la fin.
    with pytest.raises(AssertionError):
        assert ligne["fin_date"] == c.date_de_tick(pose.debut)


# --- Les deux tests figés gardent leurs octets : la coupure est ce qui les garde ---------

def test_la_famine_coupee_est_ce_qui_garde_les_octets_d_avant(monde_de_soixante_ticks, monkeypatch):
    # Sans coupure, 60 ticks de la graine 0 laissent au moins une pose.
    monde, _ = monde_de_soixante_ticks
    assert _famines(monde)
    # Avec `couper_la_famine`, le même monde n'en porte aucune.
    couper_la_famine(monkeypatch)
    coupe = World.charger(rng_seed=0)
    _jouer_en_relevant(coupe)
    assert coupe.modificateurs == []
