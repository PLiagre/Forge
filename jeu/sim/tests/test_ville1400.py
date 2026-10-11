"""La ville de 1400 se dérive des foyers du bourg, et le tick ne la change pas."""

import ast
import copy
import hashlib
import json
import math
import pathlib
import random
import re
from types import SimpleNamespace

import pytest

import sim.constants as _constantes
from sim.engine import tick
from sim.foyers import ranger_en_foyers
from sim.model import Cell
from sim.plan import aire_du_contour
from sim.ville1400 import (
    BaseAbsente,
    base_d_une_population,
    base_de_cellule,
    emprise_de_rue,
    se_chevauchent,
)
from sim.world import World

_SIM = pathlib.Path(__file__).parent.parent
_PARIS = 10322
_ISOLEE = 1175
_CLES_BASE = ("place", "rues", "maisons")


def _tolerance_aire():
    pas = 10 ** (-_constantes.SNAPSHOT_FLOAT_DECIMALS)
    facade = _constantes.FACADE_MAISON_1400_M
    profondeur = _constantes.SURFACE_M2_PAR_FOYER_LOGE / facade
    coins = ((1, 1), (1, -1), (-1, -1), (-1, 1))
    return (facade + profondeur) * len(coins) * pas


def _population_du_bourg(cellule):
    for lieu in cellule.lieux:
        if lieu.rang == 0:
            return lieu.population
    raise AssertionError("échantillon vide")


def _rayon(base):
    if not base["maisons"]:
        raise AssertionError("échantillon vide")
    meilleur = 0.0
    for maison in base["maisons"]:
        for x, y in maison["emprise"]:
            meilleur = max(meilleur, math.hypot(x, y))
    return meilleur


def _croissants(rayons):
    if len(rayons) <= 1:
        raise AssertionError("échantillon vide")
    precedent = rayons[0]
    for rayon in rayons[1:]:
        assert rayon > precedent
        precedent = rayon


def _directions(nombre):
    return tuple((indice, indice * math.tau / nombre) for indice in range(nombre))


def _directions_de_base(base):
    directions = []
    for rue in base["rues"]:
        if rue["sorte"] != "principale":
            continue
        depart, arrivee = rue["points"]
        directions.append((
            rue["vers_cell_id"],
            math.atan2(arrivee[1] - depart[1], arrivee[0] - depart[0]),
        ))
    return tuple(directions)


def _voisines_terre(monde, cell_id):
    voisines = set()
    for arete in monde.adjacency:
        if arete.get("kind") != "land-land":
            continue
        if arete.get("a") == cell_id:
            voisines.add(arete.get("b"))
        elif arete.get("b") == cell_id:
            voisines.add(arete.get("a"))
    return voisines


def _au_bord(point):
    x, y = point
    demi = _constantes.DEMI_COTE_PLACE_1400_M
    pas = 10 ** (-_constantes.SNAPSHOT_FLOAT_DECIMALS)
    return (
        abs(max(abs(x), abs(y)) - demi) <= pas
        and abs(x) <= demi + pas
        and abs(y) <= demi + pas
    )


def _sans_identifiant(base):
    return {cle: base[cle] for cle in _CLES_BASE}


def _controler_foyers(bases, populations):
    if not bases:
        raise AssertionError("échantillon vide")
    total = 0
    ecart_max = 0.0
    tolerance = _tolerance_aire()
    surface = _constantes.SURFACE_M2_PAR_FOYER_LOGE
    for base in bases:
        attendu = ranger_en_foyers(populations[base["cell_id"]]).nombre
        obtenu = 0
        for maison in base["maisons"]:
            assert maison["foyers"] == 1
            obtenu += maison["foyers"]
            ecart = abs(aire_du_contour(maison["emprise"]) - surface)
            ecart_max = max(ecart_max, ecart)
            assert ecart <= tolerance
        assert obtenu == attendu
        total += obtenu
    return total, ecart_max


def _boite(points):
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), max(xs), min(ys), max(ys)


def _cases(boite, pas):
    min_x, max_x, min_y, max_y = boite
    ix = math.floor(min_x / pas)
    ix_fin = math.floor(max_x / pas)
    iy = math.floor(min_y / pas)
    iy_fin = math.floor(max_y / pas)
    while ix <= ix_fin:
        iy_case = iy
        while iy_case <= iy_fin:
            yield ix, iy_case
            iy_case += 1
        ix += 1


def _boites_se_recouvrent(gauche, droite, tolerance):
    min_x, max_x, min_y, max_y = gauche
    autre_min_x, autre_max_x, autre_min_y, autre_max_y = droite
    return (
        min(max_x, autre_max_x) - max(min_x, autre_min_x) > tolerance
        and min(max_y, autre_max_y) - max(min_y, autre_min_y) > tolerance
    )


def _controler_chevauchements(bases):
    """Aucune maison ne rencontre la place, une voie ou une autre maison."""
    if not bases:
        raise AssertionError("échantillon vide")
    pas = _constantes.PAS_GRILLE_VILLE_1400_M
    tolerance = _constantes.TOLERANCE_CHEVAUCHEMENT_M
    paires = 0
    for base in bases:
        obstacles = [base["place"]]
        obstacles.extend(
            emprise_de_rue(rue["points"], rue["largeur_m"]) for rue in base["rues"]
        )
        maisons = [maison["emprise"] for maison in base["maisons"]]
        entrees = [("obstacle", poly) for poly in obstacles]
        entrees.extend(("maison", poly) for poly in maisons)
        boites = [_boite(poly) for _sorte, poly in entrees]
        cases = {}
        for indice, boite in enumerate(boites):
            for cle in _cases(boite, pas):
                cases.setdefault(cle, []).append(indice)
        for indice, (sorte, poly) in enumerate(entrees):
            if sorte != "maison":
                continue
            vus = set()
            for cle in _cases(boites[indice], pas):
                for autre in cases.get(cle, ()):
                    if autre in vus:
                        continue
                    vus.add(autre)
                    if entrees[autre][0] == "maison" and autre <= indice:
                        continue
                    if not _boites_se_recouvrent(boites[indice], boites[autre], tolerance):
                        continue
                    paires += 1
                    if se_chevauchent(poly, entrees[autre][1]):
                        raise AssertionError("chevauchement")
    return paires


def _sous_partie(texte, titre):
    lignes = texte.splitlines()
    debut = None
    for indice, ligne in enumerate(lignes):
        if ligne.strip() == titre:
            debut = indice + 1
            break
    if debut is None:
        raise AssertionError("échantillon vide")
    fin = len(lignes)
    for indice in range(debut, len(lignes)):
        if lignes[indice].startswith("## ") or lignes[indice].startswith("### "):
            fin = indice
            break
    section = "\n".join(lignes[debut:fin]).strip()
    if not section:
        raise AssertionError("échantillon vide")
    return section


def _parcourir(sources):
    lecteurs, ecrivains, importeurs = [], [], []
    modules = 0
    for nom, texte in sources:
        modules += 1
        arbre = ast.parse(texte)
        for noeud in ast.walk(arbre):
            if isinstance(noeud, ast.ImportFrom) and noeud.module and (
                noeud.module == "sim.ville1400" or noeud.module.startswith("sim.ville1400.")
            ):
                importeurs.append(nom)
            elif isinstance(noeud, ast.Import):
                for alias in noeud.names:
                    if alias.name == "sim.ville1400" or alias.name.startswith("sim.ville1400."):
                        importeurs.append(nom)
            if isinstance(noeud, ast.Attribute) and noeud.attr == "populations_bourg_amorcage":
                if isinstance(noeud.ctx, ast.Store):
                    ecrivains.append(nom)
                else:
                    lecteurs.append(nom)
    return modules, lecteurs, ecrivains, importeurs


def _sources_moteur():
    return [
        (chemin.name, chemin.read_text(encoding="utf-8"))
        for chemin in sorted(_SIM.glob("*.py"))
    ]


@pytest.fixture(scope="module")
def campagne():
    monde = World.charger(0)
    populations = dict(monde.populations_bourg_amorcage)
    plans_vides = all(
        not plan.rues and not plan.parcelles and not plan.batiments
        for plan in monde.plans.values()
    )
    empreinte = json.dumps(monde.to_dict(), sort_keys=True)
    bases = {}
    octets = {}
    for cell_id in monde.cells:
        base = base_de_cellule(monde, cell_id)
        bases[cell_id] = base
        octets[cell_id] = json.dumps(base, sort_keys=True)
    empreinte_apres = json.dumps(monde.to_dict(), sort_keys=True)
    alea = random.Random(0)
    for numero in range(_constantes.CALENDAR_DAYS_PER_YEAR):
        tick(monde, alea, numero)
    return SimpleNamespace(
        monde=monde,
        populations=populations,
        plans_vides=plans_vides,
        empreinte=empreinte,
        empreinte_apres=empreinte_apres,
        bases=bases,
        octets=octets,
    )


def test_sc1_meme_ville_apres_un_an(campagne):
    monde = campagne.monde
    comparees = 0
    for cell_id in monde.cells:
        assert json.dumps(base_de_cellule(monde, cell_id), sort_keys=True) == campagne.octets[cell_id]
        comparees += 1
    print(f"cellules_comparees={comparees}")
    assert comparees == len(monde.cells) > 0

    autre = World.charger(0)
    memes = 0
    for cell_id in autre.cells:
        assert json.dumps(base_de_cellule(autre, cell_id), sort_keys=True) == campagne.octets[cell_id]
        memes += 1
    print(f"chargeurs_identiques={memes}")
    assert memes == len(monde.cells) > 0

    changements = 0
    for cell_id, cellule in monde.cells.items():
        population = _population_du_bourg(cellule)
        if ranger_en_foyers(population).nombre == ranger_en_foyers(campagne.populations[cell_id]).nombre:
            continue
        changements += 1
        relue = base_d_une_population(population, _directions_de_base(campagne.bases[cell_id]))
        assert relue != _sans_identifiant(campagne.bases[cell_id])
    print(f"cellules_foyers_bouges={changements}")
    assert changements > 0


def test_sc2_une_maison_par_foyer(campagne):
    vide = base_d_une_population(0, ((None, 0.0),))
    assert vide["maisons"] == [] and vide["place"] and vide["rues"]
    total, ecart_max = _controler_foyers(list(campagne.bases.values()), campagne.populations)
    print(f"foyers_loges={total} ecart_aire_max={ecart_max}")
    assert total > 0
    with pytest.raises(AssertionError, match="échantillon vide"):
        _controler_foyers([], {})
    alt = copy.deepcopy(campagne.bases[_PARIS])
    alt["maisons"].pop()
    with pytest.raises(AssertionError):
        _controler_foyers([alt], {_PARIS: campagne.populations[_PARIS]})


def test_sc3_rien_ne_se_chevauche(campagne):
    paires = _controler_chevauchements(list(campagne.bases.values()))
    print(f"paires_eprouvees={paires}")
    assert paires > 0

    def rectangle(x0, y0, x1, y1):
        return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]

    assert se_chevauchent(rectangle(0, 0, 1, 1), rectangle(1, 0, 2, 1)) is False
    assert se_chevauchent(rectangle(0, 0, 1, 1), rectangle(0.98, 0, 2, 1)) is True
    assert se_chevauchent(rectangle(0, 0, 1, 1), rectangle(0.995, 0, 2, 1)) is False

    base = campagne.bases[_PARIS]
    emprise = base["maisons"][0]["emprise"]
    demi_facade = _constantes.FACADE_MAISON_1400_M * _constantes.DEMI_LARGEUR_PAR_LARGEUR
    decalee = [[x + demi_facade, y] for x, y in emprise]
    assert se_chevauchent(emprise, decalee)
    with pytest.raises(AssertionError):
        _controler_chevauchements([{
            "place": base["place"],
            "rues": [],
            "maisons": [
                {"emprise": emprise, "foyers": 1},
                {"emprise": decalee, "foyers": 1},
            ],
        }])
    rue = next(rue for rue in base["rues"] if rue["sorte"] == "principale")
    with pytest.raises(AssertionError):
        _controler_chevauchements([{
            "place": base["place"],
            "rues": [rue],
            "maisons": [{
                "emprise": emprise_de_rue(rue["points"], rue["largeur_m"]),
                "foyers": 1,
            }],
        }])
    with pytest.raises(AssertionError):
        _controler_chevauchements([{
            "place": base["place"],
            "rues": [],
            "maisons": [{"emprise": base["place"], "foyers": 1}],
        }])
    with pytest.raises(AssertionError, match="échantillon vide"):
        _controler_chevauchements([])


def test_sc4_le_rayon_suit_les_foyers(campagne):
    une = []
    sept = []
    for foyers in (10, 100, 1000):
        population = foyers * _constantes.TAILLE_FOYER
        une.append(_rayon(base_d_une_population(population, _directions(1))))
        sept.append(_rayon(base_d_une_population(population, _directions(7))))
    _croissants(une)
    _croissants(sept)
    with pytest.raises(AssertionError):
        _croissants(list(reversed(une)))
    rayon_paris = _rayon(campagne.bases[_PARIS])
    rayon_isolee = _rayon(campagne.bases[_ISOLEE])
    print(f"rayons_une_direction={une}")
    print(f"rayons_sept_directions={sept}")
    print(f"rayon_paris={rayon_paris} rayon_1175={rayon_isolee}")
    assert rayon_paris > rayon_isolee


def test_sc5_les_rues_suivent_les_voisines(campagne):
    monde = campagne.monde
    sans = []
    for cell_id, base in campagne.bases.items():
        voisines = _voisines_terre(monde, cell_id)
        principales = [rue for rue in base["rues"] if rue["sorte"] == "principale"]
        if not voisines:
            sans.append(cell_id)
            assert len(principales) == 1
            assert principales[0]["vers_cell_id"] is None
            depart, arrivee = principales[0]["points"]
            assert math.atan2(arrivee[1] - depart[1], arrivee[0] - depart[0]) == 0.0
        else:
            assert {rue["vers_cell_id"] for rue in principales} == voisines
        for rue in principales:
            assert _au_bord(rue["points"][0])
    print(f"cellules_sans_voisine={len(sans)}")
    assert len(sans) > 0 and _ISOLEE in sans

    arete = next(arete for arete in monde.adjacency if arete.get("kind") == "land-land")
    cell_id = arete["a"]
    origine = arete["kind"]
    try:
        arete["kind"] = "land-sea"
        assert json.dumps(base_de_cellule(monde, cell_id), sort_keys=True) != campagne.octets[cell_id]
    finally:
        arete["kind"] = origine


def test_sc6_absence_declaree(campagne):
    manuel = World({0: Cell(cell_id=0, area_km2=1.0, population=1)}, [])
    assert manuel.populations_bourg_amorcage is None
    with pytest.raises(BaseAbsente, match="0"):
        base_de_cellule(manuel, 0)
    inconnu = max(campagne.monde.cells) + 1
    with pytest.raises(BaseAbsente, match=str(inconnu)):
        base_de_cellule(campagne.monde, inconnu)
    presente = next(iter(campagne.monde.cells))
    assert base_de_cellule(campagne.monde, presente)["cell_id"] == presente


def test_sc7_rien_n_entre_dans_le_monde(campagne):
    assert campagne.plans_vides
    assert "populations_bourg_amorcage" not in campagne.monde.to_dict()
    assert "populations_bourg_amorcage" not in campagne.empreinte
    assert campagne.empreinte == campagne.empreinte_apres
    modules, lecteurs, ecrivains, importeurs = _parcourir(_sources_moteur())
    print(f"modules_parcourus={modules}")
    assert modules > 0
    assert set(lecteurs + importeurs) == {"ville1400.py"}
    assert set(ecrivains) == {"world.py"}
    _modules, _lecteurs, _ecrivains, importeurs_sonde = _parcourir([
        ("sonde.py", "from sim.ville1400 import base_de_cellule\n"),
    ])
    assert importeurs_sonde == ["sonde.py"]


def test_sc8_constantes_relues(monkeypatch):
    population = 20 * _constantes.TAILLE_FOYER
    directions = ((1, 0.0),)
    avant = base_d_une_population(population, directions)
    octets = json.dumps(avant, sort_keys=True)
    demi = _constantes.DEMI_COTE_PLACE_1400_M
    monkeypatch.setattr(_constantes, "DEMI_COTE_PLACE_1400_M", demi * 2)
    place_autre = base_d_une_population(population, directions)
    assert place_autre["place"] != avant["place"]
    assert _rayon(place_autre) != _rayon(avant)
    monkeypatch.setattr(_constantes, "DEMI_COTE_PLACE_1400_M", demi)
    assert json.dumps(base_d_une_population(population, directions), sort_keys=True) == octets

    facade = _constantes.FACADE_MAISON_1400_M
    monkeypatch.setattr(_constantes, "FACADE_MAISON_1400_M", facade * 2)
    facade_autre = base_d_une_population(population, directions)
    assert facade_autre["maisons"][0]["emprise"] != avant["maisons"][0]["emprise"]
    tolerance = _tolerance_aire()
    surface = _constantes.SURFACE_M2_PAR_FOYER_LOGE
    for maison in facade_autre["maisons"]:
        assert abs(aire_du_contour(maison["emprise"]) - surface) <= tolerance
    monkeypatch.setattr(_constantes, "FACADE_MAISON_1400_M", facade)
    assert json.dumps(base_d_une_population(population, directions), sort_keys=True) == octets


def test_sc9_empreinte_hors_to_dict(campagne):
    _modules, lecteurs, _ecrivains, _importeurs = _parcourir([
        ("ajout.py", "def lire(monde):\n    return monde.populations_bourg_amorcage\n"),
    ])
    assert lecteurs == ["ajout.py"]
    document = campagne.monde.to_dict()
    seul = hashlib.sha256(json.dumps(document, sort_keys=True).encode()).hexdigest()
    document["populations_bourg_amorcage"] = {
        str(cell_id): campagne.populations[cell_id]
        for cell_id in sorted(campagne.populations)
    }
    avec = hashlib.sha256(json.dumps(document, sort_keys=True).encode()).hexdigest()
    assert seul != avec


def test_sc10_le_modele_le_dit():
    section = _sous_partie((_SIM / "MODELE.md").read_text(encoding="utf-8"), "### Le plan de base")
    for attendu in (
        "populations_bourg_amorcage",
        "DEMI_COTE_PLACE_1400_M",
        "land-land",
        "niveau 2",
        "niveau 3",
        "vers l'est",
    ):
        assert attendu in section
    assert re.search(r"596\b.{0,160}?\d+(?:[.,]\d+)?\s*s", section, re.S)
    assert re.search(r"Paris.{0,160}?\d+(?:[.,]\d+)?\s*s", section, re.S)
    assert "sim/ville1400.py" in (_SIM / "README.md").read_text(encoding="utf-8")
    with pytest.raises(AssertionError, match="échantillon vide"):
        _sous_partie("## Autre\n", "### Le plan de base")
