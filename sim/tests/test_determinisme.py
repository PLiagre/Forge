"""
Même graine, même monde.

Ce que ce fichier protège :
  - le rng est réellement consommé à chaque tick ;
  - deux exécutions à graine identique donnent le même condensé, deux
    graines différentes donnent des mondes différents ;
  - la dérivation de province départage les égalités de façon stable et
    ne mute aucune entrée.
"""


import hashlib
import json
import random
from sim import engine
from sim.world import World
N_TICKS_DETERMINISME = 200
def _run_n_ticks_digest(world_seed: int, rng_seed: int) -> str:
    """Lance N_TICKS_DETERMINISME ticks et retourne le condensé SHA256 de l'état final."""
    world = World.charger(rng_seed=world_seed)
    rng = random.Random(rng_seed)
    for _ in range(N_TICKS_DETERMINISME):
        engine.tick(world, rng)
    state = world.to_dict()
    return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()
import copy
import dataclasses
import pathlib
from sim.aggregation import (
    CentreAdministratif,
    charger_centres,
    charger_latitude_moyenne,
    charger_positions,
    derive_appartenance,
    positions_du_monde,
)
RNG_SEED = 42
_RACINE_DEPOT = pathlib.Path(__file__).parent.parent.parent
_CHEMIN_CENTRES = (
    _RACINE_DEPOT / "data" / "province-centres-1400.json"
)
_CHEMIN_CELLULES = _RACINE_DEPOT / "data" / "world-1400.json"
_IDENTIFIANT_PETIT = 3
_IDENTIFIANT_GRAND = 7
_CELLULE_FABRIQUEE = 900001


# --- test_rng.py ---
def test_rng_etat_change_apres_tick():
    """
    Le rng est consommé à chaque tick.
    rng.getstate() avant ≠ rng.getstate() après 10 ticks.
    Compteur : rng_etat_change_apres_tick (True si état différent).
    """
    world = World.charger(rng_seed=42)
    rng = random.Random(42)

    etat_avant = rng.getstate()

    for _ in range(10):
        engine.tick(world, rng)

    etat_apres = rng.getstate()

    rng_etat_change_apres_tick = etat_avant != etat_apres
    print(f"etat_avant == etat_apres : {etat_avant == etat_apres}")
    print(f"rng_etat_change_apres_tick = {rng_etat_change_apres_tick}")

    assert rng_etat_change_apres_tick, (
        "Le rng n'a pas été consommé : son état est identique avant et après 10 ticks."
    )


# --- test_rng.py ---
def test_ticks_deterministes_meme_graine():
    """
    Déterminisme à graine fixe.
    Deux runs de 200 ticks, world_seed=42 et rng_seed=42, donnent
    le même condensé SHA256. Condensés cités par nom (règle 12).
    Compteur : ticks_deterministes_meme_graine (True si condensés égaux).
    """
    hash_run_A = _run_n_ticks_digest(world_seed=42, rng_seed=42)
    hash_run_B = _run_n_ticks_digest(world_seed=42, rng_seed=42)

    print(f"hash_run_A = {hash_run_A}")
    print(f"hash_run_B = {hash_run_B}")
    print(f"égaux : {hash_run_A == hash_run_B}")

    ticks_deterministes_meme_graine = hash_run_A == hash_run_B
    print(f"ticks_deterministes_meme_graine = {ticks_deterministes_meme_graine}")

    assert ticks_deterministes_meme_graine, (
        "Les deux runs avec la même graine ont produit des condensés différents."
    )


# --- test_rng.py ---
def test_ticks_differents_graines_rng_differentes():
    """
    Sensibilité à la graine rng.
    Deux runs de 200 ticks, world_seed=42, mais rng_seed=42 vs rng_seed=999 :
    les condensés doivent être différents (l'écart vient du tick, pas de
    l'amorçage seul).
    Compteur : ticks_differents_graines_rng_differentes (True si condensés différents).
    """
    hash_graine_42 = _run_n_ticks_digest(world_seed=42, rng_seed=42)
    hash_graine_999 = _run_n_ticks_digest(world_seed=42, rng_seed=999)

    print(f"hash_graine_42  = {hash_graine_42}")
    print(f"hash_graine_999 = {hash_graine_999}")
    print(f"différents : {hash_graine_42 != hash_graine_999}")

    ticks_differents_graines_rng_differentes = hash_graine_42 != hash_graine_999
    print(
        f"ticks_differents_graines_rng_differentes = "
        f"{ticks_differents_graines_rng_differentes}"
    )

    assert ticks_differents_graines_rng_differentes, (
        "Les deux runs avec des graines rng différentes ont produit le même condensé. "
        "Le rng n'influence pas le chemin du tick."
    )


# --- test_seeding.py ---
def test_seeding_determinisme():
    """
    Deux runs avec la même graine rng_seed = 42 donnent
    des populations identiques sur toutes les cellules.
    """
    w1 = World.charger(rng_seed=42)
    w2 = World.charger(rng_seed=42)

    assert set(w1.cells.keys()) == set(w2.cells.keys())

    mismatches = [
        cid
        for cid in w1.cells
        if w1.cells[cid].population != w2.cells[cid].population
        or w1.cells[cid].food_stock_kg != w2.cells[cid].food_stock_kg
    ]

    amorçage_deterministe_valide = 0 if mismatches else 1
    print(f"amorçage_deterministe_valide = {amorçage_deterministe_valide}")
    print(f"cellules divergentes = {len(mismatches)}")

    assert amorçage_deterministe_valide == 1, (
        f"Amorçage non déterministe : {len(mismatches)} cellule(s) divergentes."
    )


# --- test_determinisme_departage_purete.py ---
def test_determinisme_agregation_deux_passes():
    """
    Trois appels, une seule appartenance : deux fois les mêmes entrées,
    puis les centres dans l'ordre inverse.

    Compteur : determinisme_agregation_deux_passes.
    """
    monde = World.charger(rng_seed=RNG_SEED)
    positions = positions_du_monde(monde, charger_positions())
    centres = charger_centres()
    latitude_moyenne = charger_latitude_moyenne()

    premiere = derive_appartenance(positions, centres, latitude_moyenne)
    deuxieme = derive_appartenance(positions, centres, latitude_moyenne)
    inverse = derive_appartenance(positions, list(reversed(centres)), latitude_moyenne)

    identiques = sum(
        1
        for cell_id in premiere
        if premiere[cell_id] == deuxieme[cell_id] == inverse[cell_id]
    )
    total = len(positions)
    determinisme_agregation_deux_passes = int(identiques == total and total > 0)

    print(f"cellules comparees = {total}")
    print(f"cellules identiques sur les trois appels = {identiques} / {total}")
    print(f"determinisme_agregation_deux_passes = {determinisme_agregation_deux_passes} / 1")

    assert determinisme_agregation_deux_passes == 1
    assert premiere == deuxieme == inverse


# --- test_determinisme_departage_purete.py ---
def test_departage_egalite_plus_petit_id():
    """
    Deux centres exactement équidistants d'une cellule fabriquée : la
    cellule relève du plus petit `id`, dans les deux ordres de parcours.

    Un simple « premier arrivé, premier servi » passerait dans un ordre et
    échouerait dans l'autre : c'est précisément ce que ce test mesure.

    Compteur : departage_egalite_plus_petit_id.
    """
    latitude_moyenne = charger_latitude_moyenne()

    # La cellule est à l'origine du repère ; les deux centres sont à la même
    # latitude, de part et d'autre en longitude.
    positions = {_CELLULE_FABRIQUEE: (0.0, 0.0)}
    petit = CentreAdministratif(id=_IDENTIFIANT_PETIT, name="Petit", lon=1.0, lat=0.0)
    grand = CentreAdministratif(id=_IDENTIFIANT_GRAND, name="Grand", lon=-1.0, lat=0.0)

    ordres = [[petit, grand], [grand, petit]]
    gagnants = []
    for ordre in ordres:
        appartenance = derive_appartenance(positions, ordre, latitude_moyenne)
        gagnants.append(appartenance[_CELLULE_FABRIQUEE])

    departage_egalite_plus_petit_id = int(
        all(gagnant == _IDENTIFIANT_PETIT for gagnant in gagnants)
    )

    print(f"ordres essayes = {len(ordres)}")
    print(f"gagnants = {gagnants}")
    print(f"departage_egalite_plus_petit_id = {departage_egalite_plus_petit_id} / 1 "
          f"({len(ordres)} ordres x 1 cas synthetique)")

    assert departage_egalite_plus_petit_id == 1, (
        "Le departage depend de l'ordre de parcours : il est accidentel, pas stable."
    )


# --- test_determinisme_departage_purete.py ---
def test_departage_egalite_est_bien_une_egalite_exacte():
    """
    Le cas synthétique est bien une égalité exacte de distance, pas
    une quasi-égalité que le hasard des flottants trancherait. Sans cela, le
    test précédent ne mesurerait pas le départage.
    """
    from sim.aggregation import facteur_de_projection, projeter

    facteur = facteur_de_projection(charger_latitude_moyenne())
    abscisse, ordonnee = projeter(0.0, 0.0, facteur)

    carres = []
    for longitude in (1.0, -1.0):
        centre_x, centre_y = projeter(0.0, longitude, facteur)
        carres.append((abscisse - centre_x) ** 2 + (ordonnee - centre_y) ** 2)

    print(f"carres de distance = {carres}")
    assert carres[0] == carres[1], "le cas synthetique n'est pas une egalite exacte"


# --- test_determinisme_departage_purete.py ---
def test_purete_agregation_ne_mute_pas_les_entrees():
    """
    `derive_appartenance` ne modifie aucun objet reçu et n'écrit
    aucun fichier. Comparaison avant / après sur des copies profondes, et
    comparaison des octets des deux fichiers lus par le module.
    """
    monde = World.charger(rng_seed=RNG_SEED)
    positions = positions_du_monde(monde, charger_positions())
    centres = charger_centres()
    latitude_moyenne = charger_latitude_moyenne()

    positions_temoin = copy.deepcopy(positions)
    centres_temoin = [dataclasses.astuple(centre) for centre in centres]
    serialisation_avant = json.dumps(monde.to_dict(), sort_keys=True)
    octets_centres_avant = _CHEMIN_CENTRES.read_bytes()
    octets_cellules_avant = _CHEMIN_CELLULES.read_bytes()

    derive_appartenance(positions, centres, latitude_moyenne)

    centres_apres = [dataclasses.astuple(centre) for centre in centres]
    serialisation_apres = json.dumps(monde.to_dict(), sort_keys=True)

    positions_mutees = sum(
        1 for cell_id in positions_temoin if positions[cell_id] != positions_temoin[cell_id]
    )
    centres_mutes = sum(
        1 for avant, apres in zip(centres_temoin, centres_apres) if avant != apres
    )
    fichiers_mutes = int(octets_centres_avant != _CHEMIN_CENTRES.read_bytes()) + int(
        octets_cellules_avant != _CHEMIN_CELLULES.read_bytes()
    )

    print(f"positions_mutees = {positions_mutees} / {len(positions_temoin)}")
    print(f"centres_mutes = {centres_mutes} / {len(centres_temoin)}")
    print(f"fichiers_lus_mutes = {fichiers_mutes} / 2")
    print(f"cellules_mutees_par_agregation = {int(serialisation_avant != serialisation_apres)} / 1")

    assert positions_mutees == 0
    assert centres_mutes == 0
    assert fichiers_mutes == 0
    assert len(positions) == len(positions_temoin)
    assert serialisation_avant == serialisation_apres


def test_bassin_maritime_deterministe_a_graine_fixe():
    """
    `World.to_dict` ne porte pas le bassin. Deux runs à graine identique
    doivent quand même rendre le même panier mer, tick après tick — sinon
    un déterminisme qui ne regarderait que les cellules mentirait.
    """
    def serie(seed: int, n: int = 20) -> list:
        world = World.charger(rng_seed=seed)
        rng = random.Random(seed)
        vus = []
        for i in range(n):
            engine.tick(world, rng, i)
            vus.append(dict(world.stocks_mer))
        return vus

    premiere = serie(0)
    seconde = serie(0)
    assert any(panier for panier in premiere), (
        "échantillon vide : le bassin n'a jamais rien porté en 20 ticks"
    )
    assert premiere == seconde
