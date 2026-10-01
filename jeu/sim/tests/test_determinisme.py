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
import pytest
import random
import time
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


def test_date_determinisme_meme_course_meme_temps():
    """SC6 — deux courses identiques : compteur, date, empreinte et bassin égaux."""
    from sim import constants as _k

    def course():
        monde = World.charger(rng_seed=11)
        rng = random.Random(11)
        n = min(25, _k.CALENDAR_DAYS_PER_YEAR)
        assert n > 0
        for i in range(n):
            engine.tick(monde, rng, i)
        return monde, n

    a, n = course()
    b, _ = course()
    assert a.ticks_ecoules == b.ticks_ecoules == n
    assert a.date_simulation == b.date_simulation
    assert a.to_dict() == b.to_dict()
    assert a.stocks_mer == b.stocks_mer
    empreinte_a = hashlib.sha256(
        json.dumps(a.to_dict(), sort_keys=True).encode()
    ).hexdigest()
    empreinte_b = hashlib.sha256(
        json.dumps(b.to_dict(), sort_keys=True).encode()
    ).hexdigest()
    assert empreinte_a == empreinte_b


def test_date_empreinte_distincte_si_compteur_differe():
    """SC6 — seul le compteur change : cellules identiques, empreinte différente."""
    from sim import constants as _k

    monde = World.charger(0)
    rng = random.Random(0)
    n = min(12, _k.CALENDAR_DAYS_PER_YEAR)
    for i in range(n):
        engine.tick(monde, rng, i)
    assert monde.ticks_ecoules > 0
    autre = copy.deepcopy(monde)
    autre.ticks_ecoules += 3
    assert autre.ticks_ecoules != monde.ticks_ecoules
    assert monde.to_dict()["cells"] == autre.to_dict()["cells"]
    assert monde.to_dict() != autre.to_dict()
    empreinte_a = hashlib.sha256(
        json.dumps(monde.to_dict(), sort_keys=True).encode()
    ).hexdigest()
    empreinte_b = hashlib.sha256(
        json.dumps(autre.to_dict(), sort_keys=True).encode()
    ).hexdigest()
    assert empreinte_a != empreinte_b


def test_service_deterministe_octet_pour_octet_et_sensible_a_la_graine():
    """La même course HTTP est identique ; une autre graine change le monde."""
    from sim.tests.test_monde import lancer_service, requete_service

    def course(seed: int) -> tuple[bytes, bytes]:
        with lancer_service(seed) as port:
            requete_service(port, "/tick?n=3", "POST")
            monde = requete_service(port, "/monde")[2]
            cellules = json.loads(monde.decode("utf-8"))["cells"]
            assert cellules, "échantillon vide : le service ne rend aucune cellule"
            cell_id = min(cellule["cell_id"] for cellule in cellules)
            lieu = requete_service(port, f"/lieu?cell={cell_id}")[2]
            return monde, lieu

    premiere = course(0)
    seconde = course(0)
    autre_graine = course(1)
    assert premiere == seconde
    assert premiere[0] != autre_graine[0]


def _comparer_etats_service(
    observe: tuple[bytes, bytes],
    rejoue: tuple[bytes, bytes],
) -> None:
    """Compare les deux vues canoniques d'un même tick."""
    assert observe[0] == rejoue[0]
    assert observe[1] == rejoue[1]


DUREE_LECTURES_HORLOGE_S = 1.5
VITESSE_DETERMINISME_HORLOGE = 20
TICKS_DISTINCTS_MINIMUM = 3


def test_horloge_publie_des_etats_coherents_et_deterministes():
    """SC2 — chaque photographie concurrente égale le même tick rejoué."""
    from sim.tests.test_monde import lancer_service, requete_service

    observes: dict[int, tuple[bytes, bytes]] = {}
    with lancer_service(0, VITESSE_DETERMINISME_HORLOGE) as port:
        monde_initial = requete_service(port, "/monde")[1]
        cellules = monde_initial["cells"]
        assert cellules, "échantillon vide : le service ne rend aucune cellule"
        cell_id = min(cellule["cell_id"] for cellule in cellules)
        limite = time.monotonic() + DUREE_LECTURES_HORLOGE_S
        while time.monotonic() < limite:
            _, monde, octets_monde = requete_service(port, "/monde")
            _, lieu, octets_lieu = requete_service(port, f"/lieu?cell={cell_id}")
            if monde["tick"] == lieu["tick"]:
                observes[monde["tick"]] = (octets_monde, octets_lieu)
        requete_service(port, "/vitesse?jours_par_seconde=0", "POST")

    assert len(observes) >= TICKS_DISTINCTS_MINIMUM, (
        f"horloge vide ou figée : seulement {len(observes)} ticks distincts"
    )
    dernier_tick = max(observes)
    rejoues: dict[int, tuple[bytes, bytes]] = {}
    with lancer_service(0) as port:
        rejoues[0] = (
            requete_service(port, "/monde")[2],
            requete_service(port, f"/lieu?cell={cell_id}")[2],
        )
        for numero_tick in range(1, dernier_tick + 2):
            requete_service(port, "/tick?n=1", "POST")
            monde = requete_service(port, "/monde")[2]
            lieu = requete_service(port, f"/lieu?cell={cell_id}")[2]
            rejoues[numero_tick] = (monde, lieu)

    for numero_tick, etat in observes.items():
        _comparer_etats_service(etat, rejoues[numero_tick])

    tick_temoin = min(observes)
    with pytest.raises(AssertionError):
        _comparer_etats_service(observes[tick_temoin], rejoues[tick_temoin + 1])


def test_plan_deterministe_independant_de_la_graine_et_du_tick():
    from sim.tests.test_lieux import _construire_plan, _donnees_plan

    a, b = World.charger(0), World.charger(0)
    assert a.plans and b.plans
    def octets_plans(monde):
        return json.dumps(monde.to_dict()["plans"], sort_keys=True).encode()

    assert octets_plans(a) == octets_plans(b) == octets_plans(World.charger(1))
    b.plans[min(b.cells)] = _construire_plan(_donnees_plan())
    avant = octets_plans(b)
    alea_a, alea_b = random.Random(0), random.Random(0)
    for numero in range(30):
        engine.tick(a, alea_a, numero)
        engine.tick(b, alea_b, numero)
        assert a.to_dict()["cells"] == b.to_dict()["cells"]
        assert a.ticks_ecoules == b.ticks_ecoules == numero + 1
        assert alea_a.getstate() == alea_b.getstate()
        assert octets_plans(b) == avant
    copie = copy.deepcopy(b)
    copie.cells[min(copie.cells)].food_stock_kg += 1
    with pytest.raises(AssertionError):
        assert copie.to_dict()["cells"] == b.to_dict()["cells"]


def test_plan_absent_de_l_arbre_du_moteur():
    import ast

    def lectures(source):
        return [noeud for noeud in ast.walk(ast.parse(source))
                if isinstance(noeud, ast.Attribute) and noeud.attr == "plans"]

    assert not lectures(pathlib.Path(engine.__file__).read_text(encoding="utf-8"))
    assert len(lectures("world.plans")) == 1


def test_depart_deterministe_sans_effet_sur_les_cellules():
    from sim.intentions import deposer_intention
    from sim.seigneuries import charger_seigneuries

    table = charger_seigneuries()
    ids = {s.nom: s.id for s in table}
    mondes = [World.charger(0) for _ in range(4)]
    aleas = [random.Random(0) for _ in mondes]
    for monde, nom in zip(mondes, ("Duché de Bar", "Duché de Bar", "Despotat de Morée")):
        deposer_intention(monde, {"type": "choisir_depart", "seigneurie": ids[nom]})
    for numero in range(10):
        for monde, alea in zip(mondes, aleas):
            engine.tick(monde, alea, numero)
    etats = [monde.to_dict() for monde in mondes]
    empreintes = [hashlib.sha256(json.dumps(etat, sort_keys=True).encode()).hexdigest() for etat in etats]
    # Les comparaisons doivent détecter un autre choix et un habitant de plus.
    with pytest.raises(AssertionError):
        assert empreintes[0] == empreintes[2]
    copie = copy.deepcopy(etats[0])
    assert copie["cells"] and copie["plans"]
    copie["cells"][min(copie["cells"])]["population"] += 1
    with pytest.raises(AssertionError):
        assert copie["cells"] == etats[0]["cells"]
    assert etats[0] == etats[1] and empreintes[0] == empreintes[1]
    assert all(alea.getstate() == aleas[0].getstate() for alea in aleas)
    assert set(etats[-1]) == {"cells", "plans", "ticks_ecoules"}
    for etat in etats:
        assert etat["cells"] == etats[-1]["cells"]
        assert etat["plans"] == etats[-1]["plans"]
    print(f"mondes_comparés={len(mondes)}, cellules_vues={len(copie['cells'])}, ticks_joués=10, contre_épreuves_rouges=2")
