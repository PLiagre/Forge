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
    objets = grandes = objets_paris = 0
    for base in bases:
        attendu = ranger_en_foyers(populations[base["cell_id"]]).nombre
        obtenu = sum(maison["foyers"] for maison in base["maisons"])
        assert obtenu == attendu, "somme des foyers"
        ilots = attendu > _constantes.FOYERS_SANS_ILOTS
        grandes += ilots
        objets += len(base["maisons"])
        if base["cell_id"] == _PARIS:
            objets_paris = len(base["maisons"])
        for maison in base["maisons"]:
            foyers = maison["foyers"]
            if ilots:
                assert 1 <= foyers <= _constantes.MAISONS_PAR_ILOT_MAX, "borne des foyers par îlot"
                points = maison["emprise"]
                perimetre = sum(math.dist(a, b) for a, b in zip(points, points[1:] + points[:1]))
                tolerance_objet = perimetre * 10 ** (-_constantes.SNAPSHOT_FLOAT_DECIMALS)
            else:
                assert foyers == 1, "maison sous le seuil"
                tolerance_objet = tolerance
            ecart = abs(aire_du_contour(maison["emprise"]) - foyers * surface)
            ecart_max = max(ecart_max, ecart)
            assert ecart <= tolerance_objet, "aire des foyers"
        if ilots:
            assert len(base["maisons"]) <= math.ceil(attendu / _constantes.MAISONS_PAR_ILOT_MAX) + 1, "nombre d'objets"
        total += obtenu
    print(f"foyers={total} objets={objets} cellules_au_dessus={grandes} objets_Paris={objets_paris}")
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
    assert set(lecteurs + importeurs) == {"ville1400.py", "intentions.py", "service.py"}
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


def _objet_de_foyers(foyers):
    """Rectangle de bonne aire pour isoler les fautes de compte."""
    facade = _constantes.FACADE_MAISON_1400_M
    profondeur = foyers * _constantes.SURFACE_M2_PAR_FOYER_LOGE / facade
    return {"foyers": foyers, "emprise": [[0, 0], [facade, 0], [facade, profondeur], [0, profondeur]]}


def test_ilots_sc1_compte_et_contre_epreuves(campagne):
    grandes = [base for cid, base in campagne.bases.items()
               if ranger_en_foyers(campagne.populations[cid]).nombre > _constantes.FOYERS_SANS_ILOTS]
    print(f"cellules_avec_ilots={len(grandes)}")
    assert grandes
    for base in grandes:
        foyers = ranger_en_foyers(campagne.populations[base["cell_id"]]).nombre
        pleins, reste = divmod(foyers, _constantes.MAISONS_PAR_ILOT_MAX)
        assert [objet["foyers"] for objet in base["maisons"]] == (
            [_constantes.MAISONS_PAR_ILOT_MAX] * pleins + ([reste] if reste else []))
    paris = campagne.bases[_PARIS]
    maximum = _constantes.MAISONS_PAR_ILOT_MAX
    pleins = [i for i, objet in enumerate(paris["maisons"]) if objet["foyers"] == maximum]
    assert len(pleins) > 1
    alt = copy.deepcopy(paris)
    alt["maisons"][pleins[0]] = _objet_de_foyers(maximum + 1)
    alt["maisons"][pleins[1]] = _objet_de_foyers(maximum - 1)
    with pytest.raises(AssertionError, match="borne des foyers par îlot"):
        _controler_foyers([alt], campagne.populations)
    alt = copy.deepcopy(paris)
    alt["maisons"].pop(pleins[0])
    alt["maisons"].extend(_objet_de_foyers(1) for _ in range(maximum))
    with pytest.raises(AssertionError, match="nombre d'objets"):
        _controler_foyers([alt], campagne.populations)
    petite = next(base for cid, base in campagne.bases.items()
                  if 1 < ranger_en_foyers(campagne.populations[cid]).nombre <= _constantes.FOYERS_SANS_ILOTS)
    alt = copy.deepcopy(petite)
    alt["maisons"][:2] = [_objet_de_foyers(2)]
    with pytest.raises(AssertionError, match="maison sous le seuil"):
        _controler_foyers([alt], campagne.populations)
    alt = copy.deepcopy(paris)
    alt["maisons"].pop()
    with pytest.raises(AssertionError, match="somme des foyers"):
        _controler_foyers([alt], campagne.populations)
    for base in (petite, paris):
        alt = copy.deepcopy(base)
        alt["maisons"][0]["emprise"] = _objet_de_foyers(0)["emprise"]
        with pytest.raises(AssertionError, match="aire des foyers"):
            _controler_foyers([alt], campagne.populations)
    with pytest.raises(AssertionError, match="échantillon vide"):
        _controler_foyers([], {})


@pytest.mark.parametrize("directions", [1, 7])
def test_ilots_sc2_seuil_et_constantes(directions, monkeypatch):
    seuil = _constantes.FOYERS_SANS_ILOTS
    maximum = _constantes.MAISONS_PAR_ILOT_MAX
    population = (seuil + 1) * _constantes.TAILLE_FOYER
    dirs = _directions(directions)
    petite = base_d_une_population(seuil * _constantes.TAILLE_FOYER, dirs)
    assert len(petite["maisons"]) == seuil
    assert all(objet["foyers"] == 1 for objet in petite["maisons"])
    grande = base_d_une_population(population, dirs)
    assert len(grande["maisons"]) == math.ceil((seuil + 1) / maximum)
    assert [objet["foyers"] for objet in grande["maisons"]] == [maximum] * ((seuil + 1) // maximum) + [(seuil + 1) % maximum]
    with monkeypatch.context() as patch:
        patch.setattr(_constantes, "FOYERS_SANS_ILOTS", seuil + 1)
        autre = base_d_une_population(population, dirs)
        assert len(autre["maisons"]) == seuil + 1
        assert all(objet["foyers"] == 1 for objet in autre["maisons"])
    with monkeypatch.context() as patch:
        patch.setattr(_constantes, "MAISONS_PAR_ILOT_MAX", maximum // 2)
        autre = base_d_une_population(population, dirs)
        assert len(autre["maisons"]) == math.ceil((seuil + 1) / (maximum // 2))
        assert all(1 <= objet["foyers"] <= maximum // 2 for objet in autre["maisons"])
        assert sum(objet["foyers"] for objet in autre["maisons"]) == seuil + 1
    assert json.dumps(base_d_une_population(population, dirs), sort_keys=True) == json.dumps(grande, sort_keys=True)


def test_ilots_sc2_facade_relue(campagne, monkeypatch):
    avant = campagne.bases[_PARIS]
    with monkeypatch.context() as patch:
        patch.setattr(_constantes, "MAISONS_EN_FACADE_ILOT", 7)
        autre = base_de_cellule(campagne.monde, _PARIS)
        assert autre["maisons"][0]["emprise"] != avant["maisons"][0]["emprise"]
        _controler_foyers([autre], campagne.populations)
    assert json.dumps(base_de_cellule(campagne.monde, _PARIS), sort_keys=True) == campagne.octets[_PARIS]


def test_ilots_sc3_petites_bases_identiques(campagne, monkeypatch):
    cellules = sorted(cid for cid, population in campagne.populations.items()
                      if ranger_en_foyers(population).nombre <= _constantes.FOYERS_SANS_ILOTS)
    print(f"petites_cellules_comparees={len(cellules)}")
    assert cellules

    def empreinte():
        texte = "\n".join(json.dumps(base_de_cellule(campagne.monde, cid), sort_keys=True) for cid in cellules)
        return hashlib.sha256(texte.encode()).hexdigest()

    avant = empreinte()
    assert avant == "7f9be1e18e336199993e260423bfe32e5d211b7f6d1c2211d72905506d517004"
    monkeypatch.setattr(_constantes, "FOYERS_SANS_ILOTS", 0)
    assert empreinte() != avant


def test_ilots_sc4_chevauchement_detecte(campagne):
    alt = copy.deepcopy(campagne.bases[_PARIS])
    pleins = [objet for objet in alt["maisons"] if objet["foyers"] == _constantes.MAISONS_PAR_ILOT_MAX]
    assert len(pleins) > 1
    points = pleins[0]["emprise"]
    # Le dernier côté suit la façade ; déplacer d'une demi-façade force le recouvrement.
    dx, dy = ((points[0][axe] - points[-1][axe]) / 2 for axe in (0, 1))
    pleins[1]["emprise"] = [[x + dx, y + dy] for x, y in points]
    with pytest.raises(AssertionError, match="chevauchement"):
        _controler_chevauchements([alt])


def test_ilots_sc5_grande_ville_une_direction(campagne):
    foyers = ranger_en_foyers(campagne.populations[_PARIS]).nombre
    base = base_d_une_population(foyers * _constantes.TAILLE_FOYER, _directions(1))
    print(f"grande_ville_foyers={foyers} objets={len(base['maisons'])}")
    assert len(base["maisons"]) == math.ceil(foyers / _constantes.MAISONS_PAR_ILOT_MAX)
    base["cell_id"] = _PARIS
    _controler_foyers([base], {_PARIS: foyers * _constantes.TAILLE_FOYER})
    _controler_chevauchements([base])


def test_ilots_sc6_modele_et_notice():
    section = _sous_partie((_SIM / "MODELE.md").read_text(encoding="utf-8"), "### Le plan de base")
    for nom in ("FOYERS_SANS_ILOTS", "MAISONS_PAR_ILOT_MAX", "MAISONS_EN_FACADE_ILOT", "îlot"):
        assert nom in section
    assert "Jusqu'à `FOYERS_SANS_ILOTS` foyers, chaque foyer a une maison" in section
    assert "Chaque foyer a une maison" not in section
    ligne = next(ligne for ligne in (_SIM / "README.md").read_text(encoding="utf-8").splitlines()
                 if "sim/ville1400.py" in ligne)
    assert "îlots" in ligne
    with pytest.raises(AssertionError, match="échantillon vide"):
        _sous_partie("## Autre\n", "### Le plan de base")


def test_base_lecteurs_et_regle_de_refus():
    sources = _sources_moteur()
    def verifier(liste):
        modules, lecteurs, _, importeurs = _parcourir(liste)
        assert modules > 0, "échantillon vide"
        assert set(lecteurs + importeurs) == {"ville1400.py", "intentions.py", "service.py"}
    verifier(sources)
    with pytest.raises(AssertionError):
        verifier([*sources, ("engine.py", "from sim.ville1400 import base_de_cellule\n")])
    section = _sous_partie((_SIM / "MODELE.md").read_text(encoding="utf-8"), "### Le plan de base")
    assert all(mot in section for mot in ("maison de 1400", "refus", "/plan"))


def test_pont_plan_biskra_fige():
    from sim.tests.test_carte_servie import _service_local
    from sim.tests.test_monde import requete_service
    fixture = (_SIM.parent.parent / "3d/unity/Assets/ForgeLocal3D/Pont/Tests/plan-biskra-graine0-tick0.json").read_bytes()
    base = json.loads(fixture)["base"]
    assert len(base["maisons"]) == 33 and len(base["rues"]) == 7
    with _service_local() as (_serveur, port):
        assert requete_service(port, "/plan?cell=10103")[2] == fixture
        assert requete_service(port, "/plan?cell=1175")[1]["base"] != base
        requete_service(port, "/tick?n=1", "POST")
        _, plan, octets = requete_service(port, "/plan?cell=10103")
        assert octets != fixture and plan["base"] == base


def _lisible_par_le_pont(base, cell_id):
    """Les exigences de `ClientPlan` (Unity) sur `base` : une base qu'il refuserait refuse tout le plan."""
    nombre = lambda v: type(v) in (int, float) and math.isfinite(v)  # noqa: E731
    def points(liste, minimum):
        assert len(liste) >= minimum and all(len(p) == 2 and all(map(nombre, p)) for p in liste), "points"
    assert base["cell_id"] == cell_id, "cell_id"
    points(base["place"], 3)
    for rue in base["rues"]:
        points(rue["points"], 2)
        assert nombre(rue["largeur_m"]) and rue["largeur_m"] > 0, "largeur_m"
        assert type(rue["sorte"]) is str and rue["sorte"].strip(), "sorte"
    for maison in base["maisons"]:
        points(maison["emprise"], 3)
        assert nombre(maison["foyers"]) and maison["foyers"] % 1 == 0 and maison["foyers"] >= 1, "foyers"


def test_pont_bases_lisibles(campagne):
    assert len(campagne.bases) == len(campagne.monde.cells) > 0 and any(b["maisons"] for b in campagne.bases.values()), "échantillon vide"
    for cell_id, base in campagne.bases.items():
        _lisible_par_le_pont(json.loads(json.dumps(base)), cell_id)
    for liste, cle in (("rues", "largeur_m"), ("maisons", "foyers")):
        alt = copy.deepcopy(campagne.bases[10103])
        alt[liste][0][cle] = 0
        with pytest.raises(AssertionError, match=cle):
            _lisible_par_le_pont(alt, 10103)
