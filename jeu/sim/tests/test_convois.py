"""La route de chaque lieu jusqu'au grenier de son maître.

La table est calculée une fois au chargement. Le tick ne la lit pas,
et elle n'entre pas dans l'empreinte.
"""

import ast
import copy
import hashlib
import json
import math
import pathlib
import random
import re

import pytest

import sim.constants as constantes
import sim.convois as convois
import sim.places as places
from sim.convois import RouteInvalide, routes_des_lieux
from sim.engine import tick
from sim.model import Cell, creer_etat_de_lieu, ecrire_maitre
from sim.places import Place, distance_km, places_du_monde
from sim.registre_maisons import MaisonDuMonde
from sim.world import World

SIM = pathlib.Path(__file__).resolve().parents[1]
# Quatre terres et la mer : A–B–C en plaine, A–D–C freiné par la montagne.
A, B, C, D, MER = 11, 22, 33, 44, 99


@pytest.fixture(scope="module")
def monde():
    return World.charger(0)


@pytest.fixture(scope="module")
def places_reelles(monde):
    return places_du_monde(monde)


def _maison(identifiant, cid, rang=0, hors_carte=None):
    return MaisonDuMonde(
        identifiant, identifiant, "seigneurie" if cid is not None else "grande maison",
        None, identifiant, cid, rang if cid is not None else None, hors_carte,
    )


def _carte(positions, reliefs):
    km = constantes.metres_par_km()
    return {
        cid: {"relief": reliefs[cid], "centroid": {"x_m": x * km, "y_m": y * km}}
        for cid, (x, y) in positions.items()
    }


def _monde_quatre(relief_b="plaine", sans_bc=False):
    """A (0, 0), B (50, 50), C (100, 0), D (50, 0), en kilomètres."""
    positions = {A: (0, 0), B: (50, 50), C: (100, 0), D: (50, 0)}
    reliefs = {A: "plaine", B: relief_b, C: "plaine", D: "montagne"}
    paires = [(A, B), (B, C), (A, D), (D, C), (A, MER), (C, MER)]
    if sans_bc:
        paires = [paire for paire in paires if set(paire) != {B, C}]
    cells = {
        A: Cell(A, 1.0, 1, lieux=[creer_etat_de_lieu(0, 1, {}, maitre="maison-c")]),
        B: Cell(B, 1.0, 0),
        C: Cell(C, 1.0, 0),
        D: Cell(D, 1.0, 0),
    }
    monde = World(cells, [{"a": a, "b": b} for a, b in paires], carte=_carte(positions, reliefs))
    monde.maisons = (_maison("maison-c", C),)
    return monde


def _jours_terre(carte, depart, arrivee):
    """Durée dérivée des centroïdes et du relief, même formule que la route."""
    ax, ay = carte[depart]["centroid"]["x_m"], carte[depart]["centroid"]["y_m"]
    bx, by = carte[arrivee]["centroid"]["x_m"], carte[arrivee]["centroid"]["y_m"]
    geo = math.hypot(ax - bx, ay - by) / constantes.metres_par_km()
    facteurs = constantes.facteurs_transport_par_relief()
    facteur = min(facteurs[carte[depart]["relief"]], facteurs[carte[arrivee]["relief"]])
    return max(1, math.ceil(geo / facteur / constantes.VITESSE_CONVOI_KM_PAR_JOUR))


def _modules_sim():
    return sorted(SIM.glob("*.py"))


def _importe_convois(texte):
    arbre = ast.parse(texte)
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.ImportFrom) and noeud.module == "sim.convois":
            return True
        if isinstance(noeud, ast.ImportFrom) and noeud.module == "sim":
            if any(alias.name == "convois" for alias in noeud.names):
                return True
        if isinstance(noeud, ast.Import) and any(
            alias.name == "sim.convois" or alias.name.startswith("sim.convois.")
            for alias in noeud.names
        ):
            return True
    return False


def _section_prelevement(texte):
    """La section, ou une erreur : un texte sans elle est un échantillon vide."""
    marque = "## Le prélèvement"
    debut = texte.find(marque)
    if debut < 0:
        raise AssertionError("échantillon vide")
    suite = texte.find("\n## ", debut + len(marque))
    return texte[debut:suite if suite >= 0 else len(texte)]


def test_distance_dans_la_cellule(monde, places_reelles, monkeypatch):
    maisons = {maison.id: maison for maison in monde.maisons}
    table = monde.routes_des_lieux
    lieux = [(cid, lieu) for cid, cellule in monde.cells.items() for lieu in cellule.lieux]
    compares = plus = sieges = 0
    vitesse = constantes.VITESSE_CONVOI_KM_PAR_JOUR
    for cid, lieu in lieux:
        route = table[cid, lieu.rang]
        maison = maisons[route.maitre]
        assert route.maitre == lieu.maitre
        assert route.siege == (maison.cell_id, maison.rang)
        siege_cellule, siege_rang = route.siege
        attendu = max(1, math.ceil(
            distance_km(places_reelles[cid][lieu.rang], places_reelles[siege_cellule][siege_rang]) / vitesse
        ))
        assert route.jours == attendu
        compares += 1
        if route.jours > 1:
            plus += 1
        if (cid, lieu.rang) == route.siege:
            assert route.jours == 1
            sieges += 1
    assert compares == len(lieux) > 0 and plus > 0 and sieges > 0
    print(f"lieux comparés = {compares}, lieux à plus d'un jour = {plus}, sièges à 1 jour = {sieges}")

    bourgs = {cid: tuple(groupe[0] for _ in groupe) for cid, groupe in places_reelles.items()}
    au_bourg = routes_des_lieux(monde, bourgs)
    diff = sum(1 for cle, route in table.items() if route.jours != au_bourg[cle].jours)
    assert diff > 0
    print(f"lieux dont les jours changent si chacun prend la place du bourg = {diff}")

    identique = routes_des_lieux(monde, places_reelles)
    assert identique == table
    with monkeypatch.context() as contexte:
        contexte.setattr(constantes, "VITESSE_CONVOI_KM_PAR_JOUR", vitesse * 2)
        doublee = routes_des_lieux(monde, places_reelles)
    diff_vitesse = sum(1 for cle, route in table.items() if route.jours != doublee[cle].jours)
    assert diff_vitesse > 0
    assert routes_des_lieux(monde, places_reelles) == identique
    print(f"lieux dont les jours changent si la vitesse double = {diff_vitesse}")


def test_chemin_entre_cellules_freine_par_le_relief(monkeypatch):
    route = routes_des_lieux(_monde_quatre(), {})[A, 0]
    assert route.siege == (C, 0) and route.maitre == "maison-c" and route.jours == 6
    print(f"jours par B, relief compris = {route.jours}")

    noms = tuple(constantes.facteurs_transport_par_relief())

    def partout_un():
        return {nom: 1.0 for nom in noms}

    with monkeypatch.context() as contexte:
        contexte.setattr(constantes, "facteurs_transport_par_relief", partout_un)
        sans_relief = routes_des_lieux(_monde_quatre(), {})[A, 0].jours
    assert sans_relief == 4
    print(f"jours relief ignoré = {sans_relief}")

    sans_bc = routes_des_lieux(_monde_quatre(sans_bc=True), {})[A, 0].jours
    assert sans_bc == 14
    print(f"jours sans l'arête B–C = {sans_bc}")

    with pytest.raises(ValueError, match=f"cellule {B}"):
        routes_des_lieux(_monde_quatre(relief_b="abîme"), {})


def test_une_ile_prend_la_mer(monkeypatch):
    terre, ile = 5, 8
    km = constantes.metres_par_km()
    carte = {
        terre: {"relief": "plaine", "centroid": {"x_m": 0.0, "y_m": 0.0}},
        ile: {"relief": "plaine", "centroid": {"x_m": 100 * km, "y_m": 0.0}},
    }
    cells = {
        terre: Cell(terre, 1.0, 0),
        ile: Cell(ile, 1.0, 1, lieux=[creer_etat_de_lieu(0, 1, {}, maitre="maison-a")]),
    }
    monde = World(cells, [{"a": terre, "b": MER}, {"a": ile, "b": MER}], carte=carte)
    monde.maisons = (_maison("maison-a", terre),)
    assert routes_des_lieux(monde, {})[ile, 0].jours == constantes.JOURS_DE_MER
    with monkeypatch.context() as contexte:
        contexte.setattr(constantes, "JOURS_DE_MER", 3)
        assert routes_des_lieux(monde, {})[ile, 0].jours == 3
    monde.adjacency = list(monde.adjacency) + [{"a": terre, "b": ile}]
    obtenu = routes_des_lieux(monde, {})[ile, 0].jours
    terre_jours = _jours_terre(carte, terre, ile)
    assert obtenu == terre_jours != constantes.JOURS_DE_MER
    print(f"jours de mer = {constantes.JOURS_DE_MER}, jours par terre = {obtenu}")


def test_absence_et_refus():
    cid, rang = 7, 1
    libre = creer_etat_de_lieu(0, 1, {})
    tenu = creer_etat_de_lieu(rang, 1, {})
    ecrire_maitre(tenu, "maison-7")
    cellule = Cell(cid, 1.0, 2, lieux=[libre, tenu])
    monde = World({cid: cellule}, [])
    assert monde.routes_des_lieux == {}
    couple = f"({cid}, {rang})"
    with pytest.raises(RouteInvalide, match=re.escape(couple)) as inconnu:
        routes_des_lieux(monde, {})
    assert "absent du registre" in str(inconnu.value)
    monde.maisons = (_maison("maison-7", None, hors_carte="mer"),)
    with pytest.raises(RouteInvalide, match=re.escape(couple)) as hors:
        routes_des_lieux(monde, {})
    assert "siège hors carte" in str(hors.value)
    monde.maisons = (_maison("maison-7", cid),)
    point = Place(0.0, 0.0, 0.0, 0.0, "essai")
    table = routes_des_lieux(monde, {cid: (point, point)})
    assert (cid, 0) not in table and monde.routes_des_lieux == {}
    route = table[cid, rang]
    assert route.maitre == "maison-7" and route.siege == (cid, 0)
    assert route.jours == max(1, math.ceil(distance_km(point, point) / constantes.VITESSE_CONVOI_KM_PAR_JOUR))
    print(f"route rendue pour le lieu {couple}, jours = {route.jours}")


def test_le_tick_ne_lit_pas_la_table(monde, monkeypatch):
    copie = copy.deepcopy(monde)
    avant = copie.routes_des_lieux

    def leve(*_args, **_kwargs):
        raise RuntimeError("recalcul")

    monkeypatch.setattr(convois, "routes_des_lieux", leve)
    monkeypatch.setattr(places, "places_du_monde", leve)
    generateur = random.Random(0)
    for numero in range(3):
        tick(copie, generateur, numero)
    assert copie.routes_des_lieux == avant

    def enveloppe(candidat, rng, numero=None):
        convois.routes_des_lieux(candidat, {})
        return tick(candidat, rng, numero)

    with pytest.raises(RuntimeError, match="recalcul"):
        enveloppe(copie, generateur, copie.ticks_ecoules)

    modules = _modules_sim()
    assert modules
    ecrivains = []
    for chemin in modules:
        source = chemin.read_text(encoding="utf-8")
        arbre = ast.parse(source, filename=str(chemin))
        if any(
            isinstance(noeud, ast.Attribute) and noeud.attr == "routes_des_lieux"
            and isinstance(noeud.ctx, ast.Store)
            for noeud in ast.walk(arbre)
        ):
            ecrivains.append(chemin.name)
        if chemin.name == "engine.py":
            assert not _importe_convois(source)
            assert not any(
                isinstance(noeud, ast.Attribute) and noeud.attr == "routes_des_lieux"
                and isinstance(noeud.ctx, ast.Load)
                for noeud in ast.walk(arbre)
            )
    assert ecrivains == ["world.py"]
    assert _importe_convois("from sim.convois import routes_des_lieux")
    print(f"modules parcourus = {len(modules)}, ticks sans lecture = 3")


def test_rien_d_autre_ne_bouge(monde):
    avant = dict(convois.__dict__)
    premier = World.charger(0)
    second = World.charger(0)
    assert premier.routes_des_lieux == second.routes_des_lieux == monde.routes_des_lieux
    assert dict(convois.__dict__) == avant
    seul = json.dumps(monde.to_dict(), sort_keys=True)
    assert "routes_des_lieux" not in seul
    ajoute = dict(monde.to_dict())
    ajoute["routes_des_lieux"] = [
        [cid, rang, route.jours]
        for (cid, rang), route in sorted(monde.routes_des_lieux.items())
    ]
    avec = json.dumps(ajoute, sort_keys=True)
    empreinte = hashlib.sha256(seul.encode()).hexdigest()
    empreinte_avec = hashlib.sha256(avec.encode()).hexdigest()
    assert empreinte != empreinte_avec
    print(f"lieux dans la table = {len(monde.routes_des_lieux)}, empreintes distinctes = 1")


def test_le_modele_le_dit():
    modele = (SIM / "MODELE.md").read_text(encoding="utf-8")
    grenier = modele.find("## Le grenier d'une maison")
    prelevement = modele.find("## Le prélèvement")
    intentions = modele.find("## Les intentions du joueur")
    assert 0 <= grenier < prelevement < intentions
    section = _section_prelevement(modele)
    assert section
    for attendu in (
        "routes_des_lieux", "VITESSE_CONVOI_KM_PAR_JOUR", "JOURS_DE_MER",
        "facteurs_transport_par_relief", "niveau 2", "niveau 3",
    ):
        assert attendu in section
    assert re.search(r"[Cc]hargement[\s\S]{0,240}\d+[,.]\d+\s*s", section)
    assert "sim/convois.py" in (SIM / "README.md").read_text(encoding="utf-8")
    assert "test_convois.py" in (SIM / "tests" / "README.md").read_text(encoding="utf-8")
    with pytest.raises(AssertionError, match="échantillon vide"):
        assert _section_prelevement("# sans la section")
    print("section Le prélèvement lue = 1")


def test_dus_des_vassaux(monde, places_reelles):
    import dataclasses
    import time
    debut = time.perf_counter()
    table = convois.dus_des_vassaux(monde, places_reelles)
    duree = time.perf_counter() - debut
    assert table == monde.dus_des_vassaux
    maisons = {m.id: m for m in monde.maisons}
    vassaux = {m.id for m in monde.maisons if m.suzerain is not None}
    assert table.routes and table.retenus
    assert not table.routes.keys() & table.retenus.keys()
    assert table.routes.keys() | table.retenus.keys() == vassaux
    noms = monde.routes_des_lieux.noms
    assert len(table.par_indice) == len(noms)
    for vassal, raison in table.retenus.items():
        assert raison == maisons[maisons[vassal].suzerain].hors_carte and raison
        assert maisons[maisons[vassal].suzerain].cell_id is None
        assert table.par_indice[noms.index(vassal)] is None
    for vassal, (suzerain, jours) in table.routes.items():
        assert suzerain == maisons[vassal].suzerain
        assert maisons[suzerain].cell_id is not None and jours >= 1
        assert table.par_indice[noms.index(vassal)] == (noms.index(suzerain), jours)
    bar = maisons['seigneurie-1']; suzerain = maisons[bar.suzerain]
    epreuve = copy.copy(monde)
    epreuve.cells = monde.cells.copy()
    epreuve.cells[bar.cell_id] = Cell(bar.cell_id, 1, 0, lieux=[
        creer_etat_de_lieu(bar.rang, 0, {}, maitre=suzerain.id)])
    attendu = routes_des_lieux(epreuve, places_reelles)[bar.cell_id, bar.rang].jours
    assert table.routes[bar.id] == (suzerain.id, attendu)
    vide = World({}, []).dus_des_vassaux
    assert not vide.routes and not vide.retenus and not vide.par_indice
    assert 'dus_des_vassaux' not in monde.to_dict()
    print(f'dus : routés={len(table.routes)}, retenus={len(table.retenus)}, suzerains={len({s for s, _ in table.routes.values()})}, Bar={attendu} jours, construction={duree:.3f} s')

    prive = copy.copy(monde)
    prive.routes_des_lieux = copy.deepcopy(monde.routes_des_lieux)
    prive.routes_des_lieux.noms.remove(suzerain.id)
    prive.maisons = (bar, suzerain)
    with pytest.raises(RouteInvalide, match=bar.id):
        convois.dus_des_vassaux(prive, places_reelles)
    prive.maisons = (dataclasses.replace(bar, suzerain='inconnu'),)
    with pytest.raises(RouteInvalide, match=bar.id):
        convois.dus_des_vassaux(prive, places_reelles)


def test_dus_registre_charge_incomplet_refuse_avant_routage(monde, monkeypatch):
    import sim.world as etat_monde

    vassal = next(m for m in monde.maisons if m.sorte == "plausible" and m.suzerain)
    registre = tuple(m for m in monde.maisons
                     if m.sorte != "plausible" and m.id != vassal.suzerain)
    assert registre and any(m.id == vassal.suzerain for m in monde.maisons)
    monkeypatch.setattr(etat_monde, "charger_registre_maisons", lambda carte: registre)
    appels = []
    routage = convois.dus_des_vassaux

    def observer(candidat, places):
        appels.append(candidat)
        return routage(candidat, places)

    monkeypatch.setattr(convois, "dus_des_vassaux", observer)
    with pytest.raises(AssertionError, match=re.escape(vassal.suzerain)):
        World.charger(0)
    assert not appels
    print(f"suzerain retiré = {vassal.suzerain}, calculs des dus = {len(appels)}")
