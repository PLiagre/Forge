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
    assert set(etats[-1]) == {"cells", "plans", "ticks_ecoules", "maisons"}
    assert etats[-1]["maisons"]
    for etat in etats:
        assert etat["maisons"] == etats[-1]["maisons"]
        assert etat["cells"] == etats[-1]["cells"]
        assert etat["plans"] == etats[-1]["plans"]
    print(f"mondes_comparés={len(mondes)}, cellules_vues={len(copie['cells'])}, ticks_joués=10, contre_épreuves_rouges=2")


def test_gestes_routes_deterministes_seule_la_cellule_du_chantier():
    from sim import constants as k
    from sim.intentions import recevoir_intention
    from sim.tests.test_intentions import _route_reference

    mondes = [World.charger(0) for _ in range(4)]
    aleas = [random.Random(0) for _ in mondes]
    route = _route_reference(mondes[0])
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
    assert set(etats[2]) == {"cells", "plans", "ticks_ecoules", "maisons"}
    assert etats[2]["maisons"]
    for etat in etats:
        assert etat["maisons"] == etats[2]["maisons"]
    assert all(plan == {"rues": [], "parcelles": [], "batiments": []}
               for plan in etats[2]["plans"].values())
    assert len(etats[0]["plans"][str(route["cell"])]["rues"]) == 2
    print(f"mondes_comparés={len(mondes)}, cellules_vues={len(copie['cells'])}, ticks_joués=10, contre_épreuves_rouges=2")


# Copies intégrales de 1924f24 : la référence joue réellement les anciens chemins.
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
    document = monde.to_dict()
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
    import math
    from sim import world as etat_monde, maitres
    from sim.model import lire_stock_marchandise, ecrire_stock_marchandise
    from sim.tests.test_maisons import _octets_registre
    from sim.registre_maisons import charger_registre_maisons
    carte = World.lire_carte()
    normal = World.charger(graine_monde, copy.deepcopy(carte))
    with monkeypatch.context() as contexte:
        contexte.setattr(etat_monde, "charger_registre_maisons", lambda carte: ())
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
    """SC5 — greniers vides invisibles ; un grenier plein ne nourrit pas le siège."""
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


# Empreintes capturées avant #395 : document complet et état physique sans arrondi.
_PART_BASE = {
    (0, 0): ("0ea8fef27f922a382761f51cc2303fff43ff9eba4c68683f9ba8afb0e217768f", "0a034d0f3126bf72177537813b5c4f8f190ded5f4235a27e9f3574220ef7c020"),
    (0, 1): ("251beaf57162f143ff0245cbe04beaef700ae114a2de5c0e333ad1b92c287914", "35f5723a777023599a64818334517c875f6819733765b5d1d2f407a833811655"),
    (0, 3): ("3d3ad0b90bdaa8e110405675622b7071a66e97f04323248c85a01d0c987f77c9", "592454f8edc254139768101ea769ab686844c0c7919164c3f41b6bdf57f9033b"),
    (42, 0): ("9ecd7120a327fe9bfd433fae11fa509a11f2df6957c1a1ab197eb96338acf535", "0e7026e17cf733f98032e1c7fdaf1f1205a6828cd71390c5b3b873dc67289a20"),
    (42, 1): ("7b52ad8ba75cf8f6224e6008c6d0958177f5a1201680268f1c15a94273a9c9b1", "7205c27a3507ad18f84fd10fb5f08768726b6252ec4ccaead832a3ae73c87365"),
    (42, 3): ("820ecffc379ada12d00b9072725a37ad5d2ecdb844e5de9d60f1d33800fb6dc2", "04fe962477d55fb6355a4c3dfa68a8bf0a4e3c703ae725fa0273c4090eac41ed"),
}

def test_part_bit_pres():
    import math
    def empreintes(monde, rng, retours):
        assert monde.cells and all(c.lieux for c in monde.cells.values())
        return tuple(hashlib.sha256(b).hexdigest() for b in (
            json.dumps(monde.to_dict(), sort_keys=True).encode(),
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
