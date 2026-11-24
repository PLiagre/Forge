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
import marshal
import pickle
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
    """Deux courses identiques : compteur, date, empreinte et bassin égaux."""
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
    """Seul le compteur change : cellules identiques, empreinte différente."""
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


@pytest.mark.chronometre
def test_horloge_publie_des_etats_coherents_et_deterministes():
    """Chaque photographie concurrente égale le même tick rejoué."""
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


def test_depart_deterministe_sans_effet_sur_les_cellules(monkeypatch):
    monkeypatch.setattr("sim.constants.PART_COUTUMIERE", 0)
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
    assert set(etats[-1]) == {"cells", "plans", "ticks_ecoules", "maisons", "personnages", "chefs"}
    assert etats[-1]["maisons"]
    for etat in etats:
        assert etat["maisons"] == etats[-1]["maisons"]
        assert etat["cells"] == etats[-1]["cells"]
        assert etat["plans"] == etats[-1]["plans"]
    print(f"mondes_comparés={len(mondes)}, cellules_vues={len(copie['cells'])}, ticks_joués=10, contre_épreuves_rouges=2")


def test_gestes_routes_deterministes_seule_la_cellule_du_chantier(monkeypatch):
    monkeypatch.setattr("sim.constants.PART_COUTUMIERE", 0)
    from sim import constants as k
    from sim.intentions import recevoir_intention
    from sim.tests.test_intentions import _route_reference, _financer, _temoin_salaire

    mondes = [World.charger(0) for _ in range(4)]
    aleas = [random.Random(0) for _ in mondes]
    route = _route_reference(mondes[0])
    for monde in mondes: _financer(monde, route['cell'])
    _temoin_salaire(monkeypatch, mondes[2], route['cell'], [k.TAILLE_FOYER] * 3 + [2 * k.TAILLE_FOYER] * 7)
    for numero in range(10):
        for rang, (monde, alea) in enumerate(zip(mondes, aleas)):
            if numero in (0, 3) and rang != 2:
                geste = copy.deepcopy(route)
                if rang == 3:
                    geste["points"][0][0] += 1
                recevoir_intention(monde, geste)
            engine.tick(monde, alea, numero)
    etats = [monde.to_dict() for monde in mondes]
    empreintes = [hashlib.sha256(json.dumps(etat, sort_keys=True).encode()).hexdigest()
                  for etat in etats]
    with pytest.raises(AssertionError):
        assert empreintes[0] == empreintes[3]
    copie = copy.deepcopy(etats[0])
    assert copie["cells"] and copie["plans"]
    copie["cells"][min(copie["cells"])]["population"] += 1
    with pytest.raises(AssertionError):
        assert copie["cells"] == etats[0]["cells"]
    assert etats[0] == etats[1] and empreintes[0] == empreintes[1]
    def comparer_cellules(etat):
        cellules, temoin = etat["cells"], etats[2]["cells"]
        cid = str(route["cell"])
        assert cellules and cellules.keys() == temoin.keys()
        assert all(cellules[cle] == temoin[cle] for cle in cellules if cle != cid)
        assert {cle: v for cle, v in cellules[cid].items() if cle != "foyers"} == {
            cle: v for cle, v in temoin[cid].items() if cle != "foyers"}
        metiers, reference = cellules[cid]["foyers"], temoin[cid]["foyers"]
        assert sum(m["personnes"] for m in metiers.values()) == sum(m["personnes"] for m in reference.values())
        assert sum(metiers.get(nom, {}).get("personnes", 0) for nom in (k.METIER_PAYSANS, k.METIER_OUVRIERS)) == reference[k.METIER_PAYSANS]["personnes"]

    for etat in etats:
        comparer_cellules(etat)
    autre = next(cle for cle in copie["cells"]
                 if cle != str(route["cell"]) and copie["cells"][cle]["foyers"])
    copie = copy.deepcopy(etats[0])
    copie["cells"][autre]["foyers"] = {}
    with pytest.raises(AssertionError):
        comparer_cellules(copie)
    for etat in (etats[0], etats[1], etats[3]):
        assert [rue["travail_fourni"] for rue in etat["plans"][str(route["cell"])]["rues"]] == [10 * k.TAILLE_FOYER, 7 * k.TAILLE_FOYER]
    assert all(alea.getstate() == aleas[0].getstate() for alea in aleas)
    assert set(etats[2]) == {"cells", "plans", "ticks_ecoules", "maisons", "greniers", "pertes_kg", "personnages", "chefs"}
    stock, pertes = 1_000_000, 0
    for jours in [k.TAILLE_FOYER] * 3 + [2 * k.TAILLE_FOYER] * 7:
        perte = stock * (k.PERTE_GRENIER_PAR_AN * k.TICK_DURATION_DAYS / k.CALENDAR_DAYS_PER_YEAR)
        pertes += perte; stock -= perte; stock -= jours * k.SALAIRE_JOURNEE_KG
    payeur = next(l.maitre for l in mondes[2].cells[route['cell']].lieux if l.rang == 0)
    for etat in etats:
        assert etat['greniers'] == {payeur: {'nourriture': stock}} and etat['pertes_kg'] == pertes
    assert etats[2]["maisons"]
    for etat in etats:
        assert etat["maisons"] == etats[2]["maisons"]
    assert all(plan == {"rues": [], "parcelles": [], "batiments": []}
               for plan in etats[2]["plans"].values())
    assert len(etats[0]["plans"][str(route["cell"])]["rues"]) == 2
    print(f"mondes_comparés={len(mondes)}, cellules_vues={len(copie['cells'])}, ticks_joués=10, contre_épreuves_rouges=2")


# Copies intégrales des anciens chemins : la référence les joue réellement.
_REFERENCE_TICK_331 = {
    "engine": '''
def _matieres_premieres_du_panier(cell: Cell) -> list[str]:
    """Noms des matières premières présentes dans le panier, ordre stable."""
    panier = cellule_vers_dict(cell).get("stocks") or {}
    nourriture = _constantes.MARCHANDISE_NOURRITURE
    objet = _constantes.MARCHANDISE_OBJET
    return sorted(m for m in panier if m not in (nourriture, objet))

def _arete_adjacence(world, a_id: int, b_id: int) -> dict | None:
    """Entrée d'adjacence appariée aux deux cell_id, sans recalcul."""
    for edge in world.adjacency:
        ea = edge["a"]
        eb = edge["b"]
        if (ea == a_id and eb == b_id) or (ea == b_id and eb == a_id):
            return edge
    return None

def _capacite_base_arete_kg(world, a_id: int, b_id: int) -> float:
    """
    Capacité dérivée de shared_length_m sur l'arête, ou repli plat.

    Longueur absente : repli TRADE_CAPACITY_KG_PER_EDGE_PER_TICK.
    Longueur non numérique : erreur nommant les deux cell_id.
    Longueur nulle : zéro réel (frontière ponctuelle).
    """
    edge = _arete_adjacence(world, a_id, b_id)
    if edge is None or "shared_length_m" not in edge:
        return _constantes.TRADE_CAPACITY_KG_PER_EDGE_PER_TICK
    raw = edge["shared_length_m"]
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise LongueurFrontiereInvalideError(
            f"cell_id={a_id} cell_id={b_id} shared_length_m={raw!r}"
        )
    longueur_m = float(raw)
    if math.isnan(longueur_m):
        raise LongueurFrontiereInvalideError(
            f"cell_id={a_id} cell_id={b_id} shared_length_m={raw!r}"
        )
    if longueur_m == 0.0:
        return 0.0
    return (
        _constantes.DEBIT_KG_PAR_KM_DE_FRONTIERE_PAR_TICK
        * (longueur_m / _constantes.metres_par_km())
    )

def _capacite_transport_arete_kg(world, a_id: int, b_id: int) -> float:
    """
    Capacité de transport d'une arête terrestre entre deux cellules du monde.

    Base dérivée de shared_length_m sur l'adjacence, puis goulot de relief
    si une carte est chargée.
    """
    base = _capacite_base_arete_kg(world, a_id, b_id)
    if base == 0.0:
        return 0.0
    carte = getattr(world, "carte", None)
    if not carte:
        return base
    try:
        fa = _facteur_transport_pour_cellule(a_id, carte)
        fb = _facteur_transport_pour_cellule(b_id, carte)
    except ReliefInvalideError as e:
        raise ReliefInvalideError(
            f"arête ({a_id},{b_id}) : {e}"
        ) from e
    facteur = min(fa, fb)
    return base * facteur

def _initialiser_capacite_aretes(world) -> dict[tuple[int, int], float]:
    """Capacité restante par arête au début du maillon commerce."""
    capacite: dict[tuple[int, int], float] = {}
    for edge in world.adjacency:
        a_id = edge["a"]
        b_id = edge["b"]
        if a_id not in world.cells or b_id not in world.cells:
            continue
        cle = _cle_arête(a_id, b_id)
        capacite[cle] = _capacite_transport_arete_kg(world, a_id, b_id)
    return capacite

def _marchandises_du_monde(world) -> list[str]:
    """Marchandises jouées : clés de panier présentes, plus la ration alimentaire."""
    noms: set[str] = set()
    if hasattr(world, "to_dict"):
        cellules = world.to_dict()["cells"].values()
        for entree in cellules:
            panier = entree.get("stocks") or {}
            noms.update(panier)
    else:
        for cell in world.cells.values():
            panier = cellule_vers_dict(cell).get("stocks") or {}
            noms.update(panier)
    noms.add(_constantes.MARCHANDISE_NOURRITURE)
    return sorted(noms)
''',
    "lieux": '''
def repartir_sur_les_lieux(cellule) -> None:
    """Suit l'état de la cellule, sans intervenir dans ses calculs."""
    if not cellule.lieux:
        return
    lieux = sorted(cellule.lieux, key=lambda lieu: lieu.rang)

    def parts_pour(total, contenus):
        if sum(contenus) == total:
            return contenus
        poids = contenus
        if all(contenu == 0 for contenu in contenus):
            poids = [lieu.surface_km2 for lieu in lieux_de_cellule(cellule.cell_id, cellule.area_km2)]
        return partager(total, poids)

    populations = parts_pour(cellule.population, [lieu.population for lieu in lieux])
    contenus = [copier_panier(lieu) for lieu in lieux]
    paniers = {nom: parts_pour(total, [panier.get(nom, 0) for panier in contenus])
               for nom, total in copier_panier(cellule).items()}
    for rang, lieu in enumerate(lieux):
        lieu.population = populations[rang]
        remplacer_panier(lieu, {nom: parts[rang] for nom, parts in paniers.items()})
''',
}


def _empreinte_tick_331(monde, rng, retour):
    octets = json.dumps([monde.to_dict(), monde.stocks_mer, retour], sort_keys=True).encode()
    return hashlib.sha256(octets).hexdigest(), hashlib.sha256(
        repr(rng.getstate()).encode()).hexdigest()


def _comparer_empreintes_tick_331(neuves, references):
    assert len(neuves) == len(references) == 366
    for numero, (neuve, reference) in enumerate(zip(neuves, references)):
        assert neuve == reference, f"empreinte différente au tick {numero - 1}"


def test_tick_bit_pres_sur_une_annee(monkeypatch):
    import math
    import sim.lieux as lieux
    from sim.model import ecrire_stock_marchandise, lire_stock_marchandise

    compteurs = {}
    serialisations = {"monde": 0, "cellule": 0}

    def compter(fonction, compte, nom):
        def enveloppe(*args, **kwargs):
            compte[nom] += 1
            return fonction(*args, **kwargs)
        return enveloppe

    def course(reference):
        with monkeypatch.context() as ctx:
            if reference:
                for nom_module, source in _REFERENCE_TICK_331.items():
                    module = {"engine": engine, "lieux": lieux}[nom_module]
                    anciennes = {}
                    exec(source, module.__dict__, anciennes)
                    for nom, fonction in anciennes.items():
                        compteurs[nom] = 0
                        ctx.setattr(module, nom, compter(fonction, compteurs, nom))
            ctx.setattr(World, "to_dict", compter(World.to_dict, serialisations, "monde"))
            ctx.setattr(engine, "cellule_vers_dict", compter(
                engine.cellule_vers_dict, serialisations, "cellule"))
            debut = time.perf_counter()
            monde, rng = World.charger(0), random.Random(0)
            empreintes = [_empreinte_tick_331(monde, rng, None)]
            appels = {"monde": 0, "cellule": 0}
            retour = None
            for numero in range(365):
                serialisations.update(monde=0, cellule=0)
                retour = engine.tick(monde, rng, numero_tick=numero)
                for nom, nombre in serialisations.items():
                    appels[nom] += nombre
                    if not reference:
                        assert nombre == 0, f"sérialisation {nom} pendant le tick {numero}"
                empreintes.append(_empreinte_tick_331(monde, rng, retour))
            duree = time.perf_counter() - debut
            print(f"reference={reference} premiere={empreintes[0]} "
                  f"derniere={empreintes[-1]} duree={duree:.2f} s appels={appels}")
            return empreintes, monde, rng, retour, appels

    neuves, monde, rng, retour, appels_neufs = course(False)
    references, _, _, _, appels_reference = course(True)
    _comparer_empreintes_tick_331(neuves, references)
    assert compteurs and all(nombre > 0 for nombre in compteurs.values()), compteurs
    assert all(nombre == 0 for nombre in appels_neufs.values())
    assert all(nombre >= 365 for nombre in appels_reference.values())
    cellule = next(c for c in monde.cells.values() if len(c.lieux) > 1)
    lieu = next(lieu for lieu in cellule.lieux if lieu.rang == 1)
    stock = lire_stock_marchandise(lieu, "nourriture")
    assert stock >= 0
    ecrire_stock_marchandise(lieu, "nourriture", math.nextafter(stock, math.inf))
    alterees = [*neuves[:-1], _empreinte_tick_331(monde, rng, retour)]
    assert alterees[-1] != neuves[-1]
    with pytest.raises(AssertionError, match="tick 364"):
        _comparer_empreintes_tick_331(alterees, references)


def _point_registre_bit_pres(monde, alea, retour):
    document = _sans_personnes(monde)
    document.pop("maisons")
    for cellule in document["cells"].values():
        for lieu in cellule["lieux"]:
            lieu.pop("maitre")
    cellules = {cid: {**vars(c), "lieux": [{k: v for k, v in vars(l).items() if k != "maitre"}
                for l in c.lieux]} for cid, c in monde.cells.items()}
    # Les cellules complètes couvrent aussi les flottants que to_dict arrondit.
    octets = json.dumps(document, sort_keys=True).encode()
    complet = pickle.dumps((cellules,
                            monde.stocks_mer, retour, alea.getstate()))
    # Chaque point inclut toute la carte, ses flottants et le graphe, sans arrondi.
    terrain = marshal.dumps((monde.carte, monde.carte_meta, monde.adjacency), 2)
    return hashlib.sha256(octets + complet + terrain).digest()


def _comparer_registre_bit_pres(points, reference):
    assert points and len(points) == len(reference)
    for numero, (point, temoin) in enumerate(zip(points, reference)):
        assert point == temoin, f"divergence au point {numero}"


@pytest.mark.parametrize("graine_monde,graine_tick", ((0, 0), (0, 42), (42, 0), (42, 42)))
def test_registre_bit_pres(monkeypatch, graine_monde, graine_tick):
    monkeypatch.setattr("sim.constants.PART_COUTUMIERE", 0)
    import math
    from sim import world as etat_monde, maitres
    from sim.model import lire_stock_marchandise, ecrire_stock_marchandise
    from sim.tests.test_maisons import _octets_registre
    from sim.registre_maisons import charger_registre_maisons
    carte = World.lire_carte()
    normal = World.charger(graine_monde, copy.deepcopy(carte))
    with monkeypatch.context() as contexte:
        contexte.setattr(etat_monde, "charger_registre_maisons", lambda carte: ())
        contexte.setattr(etat_monde, 'construire_personnages', lambda monde: ((), {}))
        contexte.setattr(maitres, "attribuer_maitres", lambda monde: ({}, ()))
        temoin = World.charger(graine_monde, copy.deepcopy(carte))
    assert normal is not temoin and normal.maisons and temoin.maisons == ()
    assert normal.cells and normal.carte
    assert all(l.maitre is None for c in temoin.cells.values() for l in c.lieux)
    aleas = [random.Random(graine_tick) for _ in range(2)]
    registre = _octets_registre(normal.to_dict()["maisons"])
    historiques = charger_registre_maisons(normal.carte)
    assert tuple(m for m in normal.maisons if m.sorte != "plausible") == historiques
    # L'historique exact et les points projetés prouvent les seuls nouveaux champs et fiches.
    initiaux = {(cid, l.rang): l.maitre for cid, c in normal.cells.items() for l in c.lieux}
    assert initiaux and all(initiaux.values())
    def stabilite_maitres():
        assert {(cid, l.rang): l.maitre for cid, c in normal.cells.items() for l in c.lieux} == initiaux
    def stabilite():
        assert _octets_registre(normal.to_dict()["maisons"]) == registre
    points, references = [], []
    retours = [None, None]
    for numero in range(366):
        if numero:
            retours = [engine.tick(m, rng, numero - 1)
                       for m, rng in zip((normal, temoin), aleas)]
        stabilite()
        stabilite_maitres()
        points.append(_point_registre_bit_pres(normal, aleas[0], retours[0]))
        references.append(_point_registre_bit_pres(temoin, aleas[1], retours[1]))
        _comparer_registre_bit_pres(points[-1:], references[-1:])
    assert len(points) == 366 and normal.ticks_ecoules == temoin.ticks_ecoules == 365
    _comparer_registre_bit_pres(points, references)
    initial = normal.maisons
    for sorte in ("grande maison", "plausible"):
        cible = next(m for m in initial if m.sorte == sorte)
        normal.maisons = tuple(dataclasses.replace(m, nom="Altérée") if m == cible else m for m in initial)
        with pytest.raises(AssertionError): stabilite()
    normal.maisons = initial
    lieu = next(iter(normal.cells.values())).lieux[0]
    lieu.maitre = "inconnu"
    with pytest.raises(AssertionError): stabilite_maitres()
    lieu.maitre = initiaux[next(iter(normal.cells)), lieu.rang]
    stock_lieu = next(l for c in normal.cells.values() for l in c.lieux if l.stocks)
    marchandise, poids = next(iter(stock_lieu.stocks.items()))
    stock_lieu.stocks[marchandise] = math.nextafter(poids, math.inf)
    with pytest.raises(AssertionError, match="point 365"): _comparer_registre_bit_pres(
        points[:-1] + [_point_registre_bit_pres(normal, aleas[0], retours[0])], references)
    stock_lieu.stocks[marchandise] = poids
    cellule = next(c for c in normal.cells.values() if lire_stock_marchandise(c, "nourriture") >= 0)
    stock = lire_stock_marchandise(cellule, "nourriture")
    ecrire_stock_marchandise(cellule, "nourriture", math.nextafter(stock, math.inf))
    alteres = points[:-1] + [_point_registre_bit_pres(normal, aleas[0], retours[0])]
    with pytest.raises(AssertionError, match="point 365"):
        _comparer_registre_bit_pres(alteres, references)
    with pytest.raises(AssertionError):
        _comparer_registre_bit_pres([], [])
    print(f"graines={graine_monde}/{graine_tick}, points_comparés={len(points)}, registre_stable=1")


def _point_grenier_bit_pres(monde, alea, retour):
    """Octets complets, cellules, lieux, bassin, retour et générateur, sans retirer de clé."""
    octets = json.dumps(monde.to_dict(), sort_keys=True).encode()
    cellules = pickle.dumps({cid: vars(cellule) for cid, cellule in monde.cells.items()})
    bassin = pickle.dumps(monde.stocks_mer)
    reste = pickle.dumps((retour, alea.getstate()))
    return hashlib.sha256(octets + cellules + bassin + reste).digest()


def _comparer_grenier_bit_pres(points, reference):
    assert points and len(points) == len(reference)
    for numero, (point, temoin) in enumerate(zip(points, reference)):
        assert point == temoin, f"divergence au point {numero}"


def _garder_siege(plein, vide, maison):
    """La faim et la consommation du siège ne lisent pas le grenier."""
    assert plein.cells and vide.cells and plein.cells.keys() == vide.cells.keys()
    cid = maison.cell_id
    assert cid in plein.cells
    for cle in plein.cells:
        a, b = plein.cells[cle], vide.cells[cle]
        assert (a.population, a.hunger_ticks, a.food_deficit_kg, a.food_stock_kg) == (
            b.population, b.hunger_ticks, b.food_deficit_kg, b.food_stock_kg)
        assert [(lieu.rang, lieu.population, dict(lieu.stocks)) for lieu in a.lieux] == [
            (lieu.rang, lieu.population, dict(lieu.stocks)) for lieu in b.lieux]
    siege, temoin = plein.cells[cid], vide.cells[cid]
    assert siege.hunger_ticks == temoin.hunger_ticks
    assert siege.food_stock_kg == temoin.food_stock_kg
    assert siege.food_deficit_kg == temoin.food_deficit_kg


@pytest.mark.parametrize("graine_monde,graine_tick", ((0, 0), (42, 42)))
def test_grenier_bit_pres(monkeypatch, graine_monde, graine_tick):
    """Greniers vides invisibles ; un grenier plein ne nourrit pas le siège."""
    monkeypatch.setattr("sim.constants.PART_COUTUMIERE", 0)
    import math
    import sim.constants as constantes
    from sim.model import ecrire_stock_marchandise, lire_stock_marchandise

    def course(neutraliser):
        monde = World.charger(graine_monde)
        assert monde.maisons and set(monde.greniers) == {maison.id for maison in monde.maisons}
        assert all(panier == {} for panier in monde.greniers.values()) and monde.pertes_kg == 0.0
        alea = random.Random(graine_tick)
        points, retour = [], None
        with monkeypatch.context() as contexte:
            if neutraliser:
                contexte.setattr(engine, "_appliquer_pertes_greniers", lambda world: None)
            for numero in range(constantes.CALENDAR_DAYS_PER_YEAR + 1):
                if numero:
                    retour = engine.tick(monde, alea, numero - 1)
                points.append(_point_grenier_bit_pres(monde, alea, retour))
        return monde, alea, points, retour

    normal, alea, points, retour = course(False)
    _, _, references, _ = course(True)
    assert normal is not None and len(points) == constantes.CALENDAR_DAYS_PER_YEAR + 1
    _comparer_grenier_bit_pres(points, references)
    cellule = next(c for c in normal.cells.values() if lire_stock_marchandise(c, "nourriture") >= 0)
    stock = lire_stock_marchandise(cellule, "nourriture")
    ecrire_stock_marchandise(cellule, "nourriture", math.nextafter(stock, math.inf))
    alteres = points[:-1] + [_point_grenier_bit_pres(normal, alea, retour)]
    with pytest.raises(AssertionError, match="point 365"):
        _comparer_grenier_bit_pres(alteres, references)
    with pytest.raises(AssertionError):
        _comparer_grenier_bit_pres([], [])

    plein, vide = World.charger(graine_monde), World.charger(graine_monde)
    maison = next(m for m in plein.maisons if m.cell_id in plein.cells)
    plein.greniers[maison.id][constantes.MARCHANDISE_NOURRITURE] = 1_000_000.0
    assert plein.greniers[maison.id][constantes.MARCHANDISE_NOURRITURE] > 0
    aleas = [random.Random(graine_tick) for _ in range(2)]
    for numero in range(2):
        for monde, generateur in zip((plein, vide), aleas):
            engine.tick(monde, generateur, numero)
    _garder_siege(plein, vide, maison)
    plein.cells[maison.cell_id].food_stock_kg += plein.greniers[maison.id][constantes.MARCHANDISE_NOURRITURE]
    plein.greniers[maison.id][constantes.MARCHANDISE_NOURRITURE] = 0.0
    with pytest.raises(AssertionError):
        _garder_siege(plein, vide, maison)
    print(f"graines={graine_monde}/{graine_tick}, points={len(points)}")

def test_maitre_tick(monkeypatch):
    from sim import maitres
    from sim.model import EtatDeLieu
    from sim.tests.test_maisons import _tick_sans_lecture_registre
    monde = World.charger(0)
    assert monde.cells and all(c.lieux for c in monde.cells.values())
    def lire(self):
        raise RuntimeError("maître lu au tick")
    def attribuer(*args): raise RuntimeError("attribution au tick")
    def controler(tick):
        with monkeypatch.context() as garde:
            garde.setattr(EtatDeLieu, "maitre", property(lire))
            garde.setattr(maitres, "attribuer_maitres", attribuer)
            _tick_sans_lecture_registre(garde, monde, tick, monde.ticks_ecoules)
    controler(engine.tick)
    for lecture, message in ((lambda m: next(iter(m.cells.values())).lieux[0].maitre, "maître lu"),
                             (lambda m: m.maisons, "registre consulté"),
                             (lambda m: maitres.attribuer_maitres(m), "attribution au tick")):
        def impur(m, rng, numero):
            lecture(m)
            return engine.tick(m, rng, numero)
        with pytest.raises(RuntimeError, match=message): controler(impur)

def test_noms_purete_et_tick(monkeypatch):
    import sim.noms as noms
    monde = World.charger(0); rng = random.Random(0); listes = noms.charger_noms()
    def lire(lecteur):
        avant = copy.deepcopy((monde.to_dict(), monde.carte, monde.attribution_villes, monde.maisons, listes, rng.getstate())); resultat = lecteur(monde, noms=listes)
        assert (monde.to_dict(), monde.carte, monde.attribution_villes, monde.maisons, listes, rng.getstate()) == avant; return resultat
    attendu = lire(noms.noms_depuis_monde); assert attendu == lire(noms.noms_depuis_monde); autre = World.charger(19); autre.cells = dict(reversed(list(autre.cells.items()))); autre.maisons = tuple(reversed(autre.maisons)); assert noms.noms_depuis_monde(autre) == attendu
    for impur in (lambda m, **k: setattr(m.cells[next(iter(m.cells))], 'population', m.cells[next(iter(m.cells))].population + 1), lambda *a, **k: rng.random()):
        with pytest.raises(AssertionError): lire(impur)
    temoin = copy.deepcopy(monde); rng_temoin = copy.deepcopy(rng)
    with monkeypatch.context() as garde:
        def interdit(*a, **k): raise RuntimeError('noms consultés au tick')
        for nom in ('charger_noms', 'aire_de_cellule', 'noms_depuis_monde'): garde.setattr(noms, nom, interdit)
        for _ in range(3):
            assert engine.tick(monde, rng) == engine.tick(temoin, rng_temoin); assert (monde.to_dict(), monde.stocks_mer, rng.getstate()) == (temoin.to_dict(), temoin.stocks_mer, rng_temoin.getstate())
        with pytest.raises(RuntimeError, match='noms consultés'): (lambda m, r: (noms.noms_depuis_monde(m), engine.tick(m, r)))(monde, rng)
    assert lire(noms.noms_depuis_monde) == attendu; faux = copy.deepcopy(attendu); faux[next(iter(faux))]['lieux'][0]['nom'] = 'Altéré'
    with pytest.raises(AssertionError): assert faux == attendu


# Empreintes du document complet et de l'état physique, sans arrondi. La soudure de 1400
# fixe l'amorçage (le stock de départ porte la ration jusqu'à la moisson) ; l'appel des villes
# affamées change les points 1 et 3 (elles appellent leur manque dès le premier jour), pas le point 0.
# Les frontières de 1400 changent tous les points : le registre des maisons (les pays neufs de l'Ouest,
# puis les princes d'Empire, la Lituanie, la Mazovie et la Hongrie de Sigismond, et leurs chefs), les
# maîtres des lieux des cellules partagées et des capitales neuves, et leurs greniers.
# Celles des Balkans, de l'Orient et du Maghreb changent encore, à chaque point et pour les deux graines, deux
# couches et elles seules : le registre (32 maisons plausibles neuves, 24 retirées, le suzerain de 242 maisons)
# et le maître de 100 lieux de dix cellules partagées. Aucune cellule ne change hors du maître de ses lieux :
# population, stocks, bassin, tirages et retours sont ceux d'avant.
# Le mieux-vivre au rythme de l'année ajoute à chaque lieu son report de départ (seule différence au point 0),
# puis ne déplace plus les foyers que l'ancien taux quotidien faisait partir dès le premier jour : au point 1,
# la population de 218 lieux (214 pour la graine 42) et de deux cellules, leurs métiers et 117 (115) reports non
# nuls ; au point 3, avec 655 (653) lieux, ce qui suit les bouches : stocks, dettes, commerce, bassin et retours.
# Les tirages sont inchangés.
_PART_BASE = {
    (0, 0): ('f1ff2c0889387485c51245d6f7515ed5b149e5f07764b993f513c632f5ea6954', '7d193f29a3097ef5d0f205d04419906aec44cd1b9974882d8d41be98fe8957f7'),
    (0, 1): ('ff3093a54ef36d449abee33843100583eef4573fa6b822d396113ddeeb610c18', 'c14478a306e3e7f1209e5368241c3ccb3a1853750584a0e5225aab865c903890'),
    (0, 3): ('711de786f1d56c9ce49607eae5e36f3b613dd6b09b715a70f951d24b81dc304d', 'fde36df1a3aa9435913bfbbf7286ffaf90fe2254921fe1c69966bc09661700ec'),
    (42, 0): ('3f9c67e8ecb9121f3de78a4c3552db1b9c3324207719cdc4c01686d10a868d6c', 'b1e8dfbe984d7c97ba0222c55f62154afc60355a6bc1c1143d225c120df9d1e9'),
    (42, 1): ('c94b24b3d96935d62bbb5079d9bad326ee1e5adf04448dfba783b9b2674ff2e1', 'e63a9e0db8aa64a62a2a9dcf3044d8515ed30657f1f301635297de28abd26c28'),
    (42, 3): ('e97d30bc36e9e46bedef68bb0587672a74f8b05e3a4e201d5bdfe45636fe16d1', '1862f2d6aaafa5e726d01a209c86daa3e7381de57384b1581bbf263af6abda5b'),
}

def test_part_bit_pres(monkeypatch):
    monkeypatch.setattr("sim.constants.PART_COUTUMIERE", 0)
    import math
    def empreintes(monde, rng, retours):
        assert monde.cells and all(c.lieux for c in monde.cells.values())
        return tuple(hashlib.sha256(b).hexdigest() for b in (
            json.dumps(_sans_personnes(monde), sort_keys=True).encode(),
            pickle.dumps(([dataclasses.asdict(c) for c in monde.cells.values()], monde.stocks_mer, rng.getstate(), retours))))
    mesures = {}
    for seed in (0, 42):
        monde, rng, retours = World.charger(seed), random.Random(seed), []
        for tick in range(4):
            if tick in (0, 1, 3): mesures[seed, tick] = empreintes(monde, rng, retours)
            if tick < 3: retours.append(engine.tick(monde, rng, tick))
    def verifier(observe):
        assert observe == _PART_BASE and observe
    verifier(mesures)
    with pytest.raises(AssertionError): verifier({})
    with pytest.raises(AssertionError): verifier({k: v for k, v in mesures.items() if k != (42, 3)})
    cellule = next(c for c in monde.cells.values() if c.stocks); nom = next(iter(cellule.stocks))
    cellule.stocks[nom] = math.nextafter(cellule.stocks[nom], math.inf)
    with pytest.raises(AssertionError): verifier(mesures | {(42, 3): empreintes(monde, rng, retours)})


# Monde avec prélèvement : JSON public et état physique sans aucun arrondi.
# Avec la soudure de 1400 et l'appel des villes affamées : tous les points. Les frontières de 1400
# changent les maîtres des lieux, donc les greniers où va le prélèvement et les convois qui l'y portent ;
# celles de l'Empire, du Nord et de l'Est en changent d'autres, et les suzerains des seigneurs plausibles.
# Celles des Balkans, de l'Orient et du Maghreb changent, à chaque point, le registre (+32 et −24 maisons, 242
# suzerains) et le maître de 100 lieux ; et, avec les maîtres, les greniers (32 neufs, 24 retirés, et aux points
# 3 et 20 le contenu de 10 puis de 16 greniers) et les convois (le total de 9 groupes sur 12 au point 1, de 9
# sur 14 ensuite). Les cellules, le bassin, les tirages et les retours sont inchangés.
# Le mieux-vivre au rythme de l'année change les mêmes couches que pour `_PART_BASE` aux points 1 et 3 ; au
# point 20, la population de 3 133 lieux (3 128) et de 225 cellules (232), leurs métiers et ce qui en découle,
# jusqu'à deux greniers, aux convois et aux cumuls mangé et perdu. Les tirages sont inchangés.
_PRELEVEMENT_BASE = {
    (0, 1): ('fe54e7b999c71158534df18c010b34c71a4485408a4626ab62d95b49a8dfe6c8', '70a6e636a9cfdecdd5044b00b95f292b5781cb5b8bc975336d444f7801fb65c9'),
    (0, 3): ('c8a50ae854511a2c01aed633c00a68fd978d437d19ff220065529e2e7f098cb8', '1cf623e01432b6751cdf9911fba48f02df90ed9a31f632544ed312347a716b05'),
    (0, 20): ('fb0451964178ee4048f181376c405ebb6de1f38b83d08bc3dc75bb12ce6a97ac', 'de40e497c4a72c4cc8147d29792d4297fbe6ae2bbf2b27bca7569b6b493ae19d'),
    (42, 1): ('73d1e83de670094265c3b9bdedbc2ac6632e2c1478a31a51d5f0a3568f7577d8', '4ae28f77b65162dac213a6dc7ed674a42ad47aacb18b82a165bd3e9044cda736'),
    (42, 3): ('d33cde77b4c6905d6cf846e6eefb00d9fcf3640bc5fb8db2a99cccac7a1e443a', '42127b5d1ecffc7b914e2b51c45a0570e2dbe134be98cf9ec4b7686bcc316402'),
    (42, 20): ('a73ba212686595dadb88426af72c14a303087918c303cd9256cac15f8720f176', 'e909fb82efdbe4d4ef5ce81b5d7600f0557d94a4c8c8ab341ac0dbbb234004ca'),
}


def _empreintes_prelevement(monde, rng, retours):
    assert monde.cells and all(cell.lieux for cell in monde.cells.values())
    greniers = [(nom, sorted(panier.items())) for nom, panier in sorted(monde.greniers.items())]
    convois = [(arrivee, groupe.facteur, groupe.total, groupe.charges)
               for arrivee, groupe in sorted(monde.convois.items())]
    physique = ([dataclasses.asdict(cell) for cell in monde.cells.values()],
                monde.stocks_mer, rng.getstate(), retours, greniers, convois,
                monde.mange_convois_kg, monde.pertes_kg)
    return tuple(hashlib.sha256(octets).hexdigest() for octets in (
        json.dumps(_sans_personnes(monde), sort_keys=True).encode(), pickle.dumps(physique)))


def _verifier_prelevement(observe):
    assert observe and observe == _PRELEVEMENT_BASE


def test_prelevement_bit_pres(monkeypatch):
    monkeypatch.setattr("sim.constants.PART_DUE_AU_SUZERAIN", 0)
    import math
    from sim import constants as c
    mesures = {}
    for seed in (0, 42):
        monde, rng, retours = World.charger(seed), random.Random(seed), []
        for numero in range(20):
            retours.append(engine.tick(monde, rng, numero))
            point = numero + 1
            if point in (1, 3, 20):
                mesures[seed, point] = _empreintes_prelevement(monde, rng, retours)
                print(f'point={(seed, point)}, empreintes={mesures[seed, point]}')
                document = monde.to_dict()
                if point == 1:
                    assert document['convois'] and not any(monde.greniers.values())
                    # Les départs n'ont pas encore mangé : un cumul nul reste omis.
                    assert monde.mange_convois_kg == 0 and 'mange_convois_kg' not in document
                if point == 3:
                    assert document['greniers']
                    assert document['mange_convois_kg'] == monde.mange_convois_kg > 0
    _verifier_prelevement(mesures)
    with pytest.raises(AssertionError):
        _verifier_prelevement({})
    with pytest.raises(AssertionError):
        _verifier_prelevement({k: v for k, v in mesures.items() if k != (42, 20)})
    panier = next(p for p in monde.greniers.values() if p.get(c.MARCHANDISE_NOURRITURE, 0) > 0)
    panier[c.MARCHANDISE_NOURRITURE] = math.nextafter(panier[c.MARCHANDISE_NOURRITURE], math.inf)
    with pytest.raises(AssertionError):
        _verifier_prelevement(mesures | {(42, 20): _empreintes_prelevement(monde, rng, retours)})
    communs = mesures.keys() & _PART_BASE.keys()
    assert communs
    for point in sorted(communs):
        assert all(a != b for a, b in zip(_PRELEVEMENT_BASE[point], _PART_BASE[point]))
    print(f'points figés={len(mesures)}, points comparés sans prélèvement={len(communs)}')


# Monde avec dû : capturé une fois, JSON public et état physique sans arrondi.
# Avec la soudure de 1400 et l'appel des villes affamées. Les frontières de 1400 changent les maîtres
# et leurs suzerains, donc les dus des vassaux et les greniers des suzerains, à l'Ouest puis dans
# l'Empire, au Nord et à l'Est. Ceux des Balkans, de l'Orient et du Maghreb changent, aux points 3 et 20,
# le contenu de 187 puis de 201 greniers (32 neufs, 24 retirés) et les convois (76 groupes au lieu de 72 au
# point 3, 99 au lieu de 111 au point 20, tous de total différent), avec le registre et le maître de 100 lieux ;
# les cellules, le bassin, les tirages et les retours sont inchangés.
# Le mieux-vivre au rythme de l'année y change les mêmes couches qu'au monde avec prélèvement, aux mêmes points.
_DU_BASE = {
    (0, 3): ('97c0119795eb37d25e296f3d2a739ae8cbb22799f09b45d71aa123a4a43393da', '28a0b00a5097815aa4e5fb6f4c22e4265554a5e06fb453bc45f8f25e5d9de3f2'),
    (0, 20): ('e583226c72da8e9921cfb96f3ede6281bc703e6f10558a7a04bbb0b0ac51e1bb', '634ee556426e54ec617e6235572d3788771df3c9145da2ceb04f2fb8f80f92c3'),
    (42, 3): ('8776d73d3b0218e8797f0b4fa3cee6c78a345f235992781b31e28ec2f9b56f3b', 'e649d69c904fb407d209970e0c07e926d6065a520c68d23d73bab0f6908f71c1'),
    (42, 20): ('0e3fce0c3d4cafec62f4503cd5ea913d518587ff9fd723b8953c93fa2591c08a', 'ebb088d13984af3ceac4caed31d475b38830a77d346123e017a7fd62596cccae'),
}


def test_du_au_suzerain_bit_pres():
    import math
    from sim import constants as c
    mesures = {}
    for seed in (0, 42):
        monde, rng, retours = World.charger(seed), random.Random(seed), []
        for numero in range(20):
            retours.append(engine.tick(monde, rng, numero))
            point = numero + 1
            if point in (1, 3, 20):
                mesures[seed, point] = _empreintes_prelevement(monde, rng, retours)
                print(f'point={(seed, point)}, empreintes avec dû={mesures[seed, point]}')
    reference = {k: v for k, v in _PRELEVEMENT_BASE.items() if k[1] == 1} | _DU_BASE
    def verifier(observe):
        assert observe and observe == reference
    verifier(mesures)
    for point, empreintes in mesures.items():
        if point[1] == 1:
            assert empreintes == _PRELEVEMENT_BASE[point]
        else:
            assert all(a != b for a, b in zip(empreintes, _PRELEVEMENT_BASE[point]))
    with pytest.raises(AssertionError): verifier({})
    with pytest.raises(AssertionError): verifier({k: v for k, v in mesures.items() if k != (42, 20)})
    valois = next(m.suzerain for m in monde.maisons if m.id == 'seigneurie-1')
    panier = monde.greniers[valois]
    assert panier[c.MARCHANDISE_NOURRITURE] > 0
    panier[c.MARCHANDISE_NOURRITURE] = math.nextafter(panier[c.MARCHANDISE_NOURRITURE], math.inf)
    with pytest.raises(AssertionError):
        verifier(mesures | {(42, 20): _empreintes_prelevement(monde, rng, retours)})
    print(f'points figés avec dû={len(_DU_BASE)}, points inchangés={len(reference) - len(_DU_BASE)}')


def _sans_personnes(monde):
    document = monde.to_dict()
    for cle in ('personnages', 'chefs'):
        document.pop(cle)
    return document


@pytest.mark.parametrize('graine', (0, 42))
def test_personnes_neutres(monkeypatch, graine):
    from sim import personnages as p, world as w
    monde = World.charger(graine)
    temoin = copy.deepcopy(monde)
    temoin.personnages, temoin.chefs = (), {}
    initial = copy.deepcopy((monde.personnages, monde.chefs))
    aleas = [random.Random(graine), random.Random(graine)]
    original = World.__getattribute__
    def intercepter(self, nom):
        if nom in ('personnages', 'chefs'):
            raise RuntimeError('personnes consultées au tick')
        return original(self, nom)
    def refuser(*a): raise RuntimeError('personnes consultées au tick')
    for numero in range(3):
        with monkeypatch.context() as garde:
            garde.setattr(World, '__getattribute__', intercepter)
            for module, nom in ((p, 'charger_catalogue'), (p, 'construire_personnages'), (w, 'construire_personnages')):
                garde.setattr(module, nom, refuser)
                with pytest.raises(RuntimeError): getattr(module, nom)(monde)
            for nom in ('personnages', 'chefs'):
                with pytest.raises(RuntimeError): getattr(monde, nom)
            retours = [engine.tick(m, rng, numero) for m, rng in zip((monde, temoin), aleas)]
        assert (monde.personnages, monde.chefs, temoin.personnages, temoin.chefs) == (*initial, (), {})
        assert _empreintes_prelevement(monde, aleas[0], retours[0]) == _empreintes_prelevement(temoin, aleas[1], retours[1])
