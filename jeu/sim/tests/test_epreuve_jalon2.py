"""Preuve du jalon 2, indépendante des données que lit le moteur."""

import copy
import json
import math
from pathlib import Path
import random
import statistics
from types import SimpleNamespace

import pytest

from sim import constants
from sim.projection import projeter_epsg3035
from sim.puissances import charger_table, puissances_depuis_monde
from sim.villes import point_dans_geometrie
from sim.world import World


SIM = Path(__file__).resolve().parents[1]
REFERENCE = SIM.parent / "data" / "reference-jalon2-1400.json"
BLOCS = ("points_connus", "regions_denses", "regions_vides", "points", "declares")


def lire_reference(document=None):
    """Refuse une référence sans source, une attente inconnue ou une ancre."""
    if document is None:
        document = json.loads(REFERENCE.read_text(encoding="utf-8"))
    if document.get("projection") != "EPSG:4326":
        raise ValueError("projection : EPSG:4326 requis")
    table = charger_table()
    puissances = {p.nom for p in table.puissances}
    ancres = {a.nom for a in table.ancres}
    for bloc, lignes in [("référence", [document])] + [(b, document[b]) for b in BLOCS]:
        noms = set()
        for ligne in lignes:
            nom = ligne.get("nom", bloc)
            source = ligne.get("source")
            if not isinstance(source, str) or not source.strip():
                raise ValueError(f"{nom} : source vide")
            if nom in noms:
                raise ValueError(f"{nom} : point dupliqué")
            noms.add(nom)
            if bloc in ("points_connus", "points") and ligne.get("puissance") not in puissances:
                raise ValueError(f"{nom} : puissance inconnue {ligne.get('puissance')}")
            if bloc == "points" and nom in ancres:
                raise ValueError(f"{nom} : ancre interdite dans l'échantillon")
            if "declare" in ligne and not ligne.get("raison", "").strip():
                raise ValueError(f"{nom} : déclaration sans raison")
            if bloc == "declares" and ("puissance" in ligne or not ligne.get("declare")):
                raise ValueError(f"{nom} : doit rester déclaré sans puissance attendue")
    return document


def placer(monde, point):
    """Une seule appartenance polygonale ; aucune recherche par proximité."""
    x, y = projeter_epsg3035(point["lat"], point["lon"])
    cellules = [cid for cid in monde.cells
                if point_dans_geometrie(x, y, monde.carte[cid]["geometry"])]
    if len(cellules) > 1:
        raise ValueError(f"{point['nom']} : plusieurs polygones {sorted(cellules)}")
    return cellules[0] if cellules else None


def densite_region(monde, region):
    cellules = {placer(monde, {"nom": nom, "lat": lat, "lon": lon})
                for nom, lat, lon in region["points"]} - {None}
    if not cellules:
        raise ValueError(f"{region['nom']} : aucune cellule placée")
    densite = (sum(monde.cells[c].population for c in cellules)
               / sum(monde.cells[c].area_km2 for c in cellules))
    return densite, sorted(cellules)


def epreuve(monde, vue, reference=None):
    """Rend les échecs nommés ; les compteurs se dérivent des points couverts."""
    reference = lire_reference(reference)
    echecs = []
    if not monde.cells:
        return ["monde vide : médiane non calculable, échantillon vide"]
    mediane = statistics.median(c.population / c.area_km2 for c in monde.cells.values())
    print(f"médiane = {mediane:.2f} hab./km²")
    for bloc in ("regions_denses", "regions_vides"):
        for region in reference[bloc]:
            try:
                densite, cellules = densite_region(monde, region)
            except ValueError as erreur:
                echecs.append(str(erreur))
                continue
            print(f"{region['nom']} : {densite:.2f} hab./km² ; cellules {cellules}")
            conforme = densite > mediane if bloc == "regions_denses" else densite < mediane
            if not conforme:
                echecs.append(f"{region['nom']} : densité {densite:.2f}, médiane {mediane:.2f}")
    noms_puissances = {p.id: p.nom for p in charger_table().puissances}
    justes = couverts = 0
    for bloc in ("points_connus", "points", "declares"):
        for point in reference[bloc]:
            nom = point["nom"]
            try:
                cid = placer(monde, point)
            except ValueError as erreur:
                echecs.append(str(erreur))
                continue
            puissance = noms_puissances.get(vue.get(cid))
            print(f"{nom} : cellule {cid} ; puissance {puissance} ; attente {point.get('puissance')}")
            if "declare" in point:
                print(f"{nom} déclaré {point['declare']} : {point['raison']}")
            if point.get("declare") == "hors carte":
                if cid is not None:
                    echecs.append(f"{nom} : déclaré hors carte mais placé dans {cid}")
                continue
            if bloc == "declares":
                continue
            if cid is None or puissance is None:
                echecs.append(f"{nom} : hors carte non déclaré ou cellule non couverte")
                continue
            juste = puissance == point["puissance"]
            if bloc == "points_connus" and not juste:
                echecs.append(f"{nom} : {puissance}, attendu {point['puissance']}")
            if bloc == "points":
                couverts += 1
                justes += juste
    seuil = math.ceil(2 * couverts / 3)
    print(f"justes / couverts / seuil = {justes} / {couverts} / {seuil}")
    if not couverts or justes < seuil:
        echecs.append(f"seuil des deux tiers : {justes} / {couverts}, seuil {seuil} ; échantillon vide interdit")
    return echecs


@pytest.fixture(scope="module")
def temoin():
    monde = World.charger(0)
    return monde, puissances_depuis_monde(monde)


def test_sans_aridite(monkeypatch, temoin):
    monde, _ = temoin
    desert = lire_reference()["regions_vides"][0]
    avant, _ = densite_region(monde, desert)
    monkeypatch.setattr(constants, "facteur_eau", lambda pluie: 1.0)
    sans_aridite = World.charger(0)
    apres, _ = densite_region(sans_aridite, desert)
    assert apres != avant, "la suppression de l'aridité n'a aucun effet"
    echecs = epreuve(sans_aridite, puissances_depuis_monde(sans_aridite))
    print(f"contre-épreuve sans aridité : {echecs}")
    assert any(desert["nom"] in e for e in echecs)


def test_frontieres_melangees(temoin):
    monde, vue = temoin
    cellules = sorted(vue)
    valeurs = [vue[c] for c in cellules]
    random.Random(0).shuffle(valeurs)
    melangee = dict(zip(cellules, valeurs))
    assert any(melangee[c] != vue[c] for c in cellules), "permutation sans effet"
    echecs = epreuve(monde, melangee)
    print(f"contre-épreuve des frontières mélangées : {echecs}")
    assert any("seuil des deux tiers" in e for e in echecs)


def test_table_reelle():
    reference = lire_reference()
    assert [len(reference[b]) for b in BLOCS] == [5, 4, 1, 53, 1]


@pytest.mark.parametrize("bloc,nom,champ,valeur", [
    ("points_connus", "Paris", "source", ""),
    ("points", "Lyon", "puissance", "Bourgogne"),
    ("points", "Stockholm", "declare", None),
    ("points_connus", "Venise", "declare", None),
])
def test_table_alteree_refusee(bloc, nom, champ, valeur, temoin):
    reference = copy.deepcopy(lire_reference())
    point = next(p for p in reference[bloc] if p["nom"] == nom)
    if valeur is None:
        del point[champ]
        assert any(nom in e for e in epreuve(*temoin, reference))
    else:
        point[champ] = valeur
        with pytest.raises(ValueError, match=nom):
            lire_reference(reference)


def test_aucun_module_du_moteur_ne_lit_la_reference():
    modules = [p for p in SIM.rglob("*.py") if "tests" not in p.relative_to(SIM).parts]
    assert modules, "recherche vide dans sim/"
    textes = {p: p.read_text(encoding="utf-8") for p in modules}
    assert any("puissances-1400" in t for t in textes.values()), "recherche aveugle"
    assert not [str(p) for p, t in textes.items() if "reference-jalon2" in t]


def test_epreuve_refuse_vides_et_placement_ambigu(temoin):
    monde, vue = temoin
    reference = lire_reference()
    reference["points"] = []
    assert any("échantillon vide" in e for e in epreuve(monde, vue, reference))
    reference = lire_reference()
    reference["regions_denses"][0]["points"] = [["loin", -80, -170]]
    assert any("Flandre : aucune cellule" in e for e in epreuve(monde, vue, reference))
    point = lire_reference()["points_connus"][0]
    cid = placer(monde, point)
    double = SimpleNamespace(cells={1: monde.cells[cid], 2: monde.cells[cid]},
                             carte={1: monde.carte[cid], 2: monde.carte[cid]})
    assert any("Paris : plusieurs polygones" in e for e in epreuve(double, {1: vue[cid], 2: vue[cid]}))


def test_preuve_tient(temoin):
    assert epreuve(*temoin) == []
