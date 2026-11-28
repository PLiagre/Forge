"""Preuve indépendante des données que lit le moteur."""

import copy
import json
import math
from pathlib import Path
import random
import statistics
from types import SimpleNamespace

import pytest

from sim import constants
from sim.frontieres import puissances_des_lieux
from sim.places import places_du_monde
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


def puissance_et_lieu_du_point(monde, cid, point, vue, lieux, places):
    """(puissance, clé de lieu) du point : la puissance du lieu le plus proche du point dans sa cellule
    quand la cellule est partagée (`lieux`), avec la clé `(cell_id, rang)` de ce lieu ; sinon celle de
    la cellule, sans clé. La frontière passe entre les lieux."""
    if not lieux or not any(c == cid for c, _ in lieux):
        return vue.get(cid), None
    x, y = projeter_epsg3035(point["lat"], point["lon"])
    rangs = places[cid]
    rang = min(range(len(rangs)), key=lambda r: ((rangs[r].x_m - x) ** 2 + (rangs[r].y_m - y) ** 2, r))
    if (cid, rang) in lieux:
        return lieux[cid, rang], (cid, rang)
    return vue.get(cid), None


def puissance_du_point(monde, cid, point, vue, lieux, places):
    """La puissance du point : celle de son lieu dans une cellule partagée, sinon celle de la cellule."""
    return puissance_et_lieu_du_point(monde, cid, point, vue, lieux, places)[0]


def densite_region(monde, region):
    cellules = {placer(monde, {"nom": nom, "lat": lat, "lon": lon})
                for nom, lat, lon in region["points"]} - {None}
    if not cellules:
        raise ValueError(f"{region['nom']} : aucune cellule placée")
    densite = (sum(monde.cells[c].population for c in cellules)
               / sum(monde.cells[c].area_km2 for c in cellules))
    return densite, sorted(cellules)


def releve_des_points(monde, vue, reference, lieux, places):
    """Un enregistrement par point des blocs `points_connus`, `points` et `declares`, dans l'ordre de
    la référence : nom, bloc, point, cellule (`cid`, ou `erreur` de placement), puissance trouvée (nom),
    puissance attendue et clé de lieu `(cell_id, rang)` retenue (`None` si la cellule a servi).
    `lieux` vide : un point a la puissance de sa cellule."""
    noms_puissances = {p.id: p.nom for p in charger_table().puissances}
    releve = []
    for bloc in ("points_connus", "points", "declares"):
        for point in reference[bloc]:
            ligne = {"nom": point["nom"], "bloc": bloc, "point": point, "cid": None, "erreur": None,
                     "puissance": None, "attendue": point.get("puissance"), "lieu": None}
            try:
                ligne["cid"] = placer(monde, point)
            except ValueError as erreur:
                ligne["erreur"] = erreur
                releve.append(ligne)
                continue
            trouvee, ligne["lieu"] = puissance_et_lieu_du_point(
                monde, ligne["cid"], point, vue, lieux, places)
            ligne["puissance"] = noms_puissances.get(trouvee)
            releve.append(ligne)
    return releve


def epreuve(monde, vue, reference=None, lieux=None):
    """Rend les échecs nommés ; les compteurs se dérivent des points couverts.

    `lieux` : la puissance des lieux des cellules partagées (`frontieres.puissances_des_lieux`) ;
    sans elle, un point a la puissance de sa cellule."""
    lieux = {} if lieux is None else lieux
    places = places_du_monde(monde) if lieux else {}
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
    justes = couverts = 0
    for ligne in releve_des_points(monde, vue, reference, lieux, places):
        nom, bloc, point, cid, puissance = (ligne[c] for c in ("nom", "bloc", "point", "cid", "puissance"))
        if ligne["erreur"] is not None:
            echecs.append(str(ligne["erreur"]))
            continue
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


def juger_le_grain_du_lieu(monde, vue, lieux):
    """(fautes, corrigés) : ce que les lieux changent à la puissance des points de la référence.

    Deux relevés, la cellule seule puis les lieux. Les points qui changent de puissance d'un relevé à
    l'autre se dérivent des deux ; un point corrigé est faux à la cellule et juste avec les lieux, et la
    cellule lui donne alors le pays de son bourg. Les lieux doivent faire monter les justes du bloc
    `points`, et un point qui a servi d'un lieu doit être juste."""
    reference = lire_reference()
    noms_puissances = {p.id: p.nom for p in charger_table().puissances}
    cellule = {(l["bloc"], l["nom"]): l for l in releve_des_points(monde, vue, reference, {}, {})}
    avec_lieux = {(l["bloc"], l["nom"]): l for l in releve_des_points(
        monde, vue, reference, lieux, places_du_monde(monde))}
    fautes = []
    changent = [cle for cle in cellule if cellule[cle]["puissance"] != avec_lieux[cle]["puissance"]]
    if not changent:
        fautes.append("échantillon vide : aucun point ne change de puissance entre la cellule et les lieux")
    for cle in changent:
        print(f"{cle[1]} change : cellule {cellule[cle]['puissance']}, lieux {avec_lieux[cle]['puissance']}"
              f" ; attente {cellule[cle]['attendue']}")
    corriges = [cle for cle in changent
                if cellule[cle]["puissance"] != cellule[cle]["attendue"]
                and avec_lieux[cle]["puissance"] == avec_lieux[cle]["attendue"]]
    for cle in corriges:
        bourg = noms_puissances.get(vue.get(cellule[cle]["cid"]))
        if cellule[cle]["puissance"] != bourg:
            fautes.append(f"{cle[1]} : la cellule seule rend {cellule[cle]['puissance']}, "
                          f"le pays de son bourg est {bourg}")
    for cle, ligne in avec_lieux.items():
        if ligne["lieu"] is not None and ligne["puissance"] != ligne["attendue"] and ligne["attendue"]:
            fautes.append(f"{cle[1]} : son lieu {ligne['lieu']} rend {ligne['puissance']}, "
                          f"attendu {ligne['attendue']}")
    justes = [sum(1 for (bloc, _), l in releve.items()
                  if bloc == "points" and l["puissance"] is not None and l["puissance"] == l["attendue"])
              for releve in (cellule, avec_lieux)]
    print(f"justes du bloc points : cellule {justes[0]}, lieux {justes[1]}")
    if justes[0] >= justes[1]:
        fautes.append(f"les lieux ne font pas monter les justes : cellule {justes[0]}, lieux {justes[1]}")
    return fautes, [cle[1] for cle in corriges]


@pytest.fixture(scope="module")
def temoin():
    monde = World.charger(0)
    return monde, puissances_depuis_monde(monde)


@pytest.fixture(scope="module")
def lieux(temoin):
    return puissances_des_lieux(temoin[0])


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


def test_frontieres_melangees(temoin, lieux):
    monde, vue = temoin
    cellules = sorted(vue)
    valeurs = [vue[c] for c in cellules]
    random.Random(0).shuffle(valeurs)
    melangee = dict(zip(cellules, valeurs))
    assert any(melangee[c] != vue[c] for c in cellules), "permutation sans effet"
    # Les lieux des cellules partagées se mélangent aussi : aucun pays ne reste à sa place.
    couples = sorted(lieux)
    pays = [lieux[c] for c in couples]
    random.Random(0).shuffle(pays)
    echecs = epreuve(monde, melangee, lieux=dict(zip(couples, pays)))
    print(f"contre-épreuve des frontières mélangées : {echecs}")
    assert any("seuil des deux tiers" in e for e in echecs)


def test_table_reelle():
    reference = lire_reference()
    assert [len(reference[b]) for b in BLOCS] == [5, 4, 1, 53, 1]


@pytest.mark.parametrize("bloc,nom,champ,valeur", [
    ("points_connus", "Paris", "source", ""),
    # Une puissance absente de la table : la Bourgogne en est une, la Lotharingie non.
    ("points", "Lyon", "puissance", "Lotharingie"),
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


# Cagliari (Aragon) et Pérouse (États de l'Église) : leur cellule est partagée, et son bourg a le pays
# d'une autre terre que la leur (l'Arborée, Rimini).
POINTS_CORRIGES = ("Cagliari", "Pérouse")


def lignes_des_points_corriges(monde, vue, lieux):
    """Le relevé des POINTS_CORRIGES, à la cellule seule et avec les lieux."""
    reference = lire_reference()
    cellule = releve_des_points(monde, vue, reference, {}, {})
    avec_lieux = releve_des_points(monde, vue, reference, lieux, places_du_monde(monde))
    return {nom: (next(l for l in cellule if l["nom"] == nom), next(l for l in avec_lieux if l["nom"] == nom))
            for nom in POINTS_CORRIGES}


def test_preuve_tient(temoin, lieux):
    monde, vue = temoin
    assert lieux, "échantillon vide : aucune cellule partagée"
    assert epreuve(*temoin, lieux=lieux) == []
    fautes, corriges = juger_le_grain_du_lieu(monde, vue, lieux)
    assert fautes == []
    assert set(POINTS_CORRIGES) <= set(corriges)
    noms_puissances = {p.id: p.nom for p in charger_table().puissances}
    for nom, (cellule, avec_lieux) in lignes_des_points_corriges(monde, vue, lieux).items():
        # Au grain de la cellule, le point prend le pays du bourg, qui est celui d'une autre terre.
        assert cellule["puissance"] == noms_puissances[vue[cellule["cid"]]] != cellule["attendue"], nom
        assert avec_lieux["lieu"] is not None, nom
        assert avec_lieux["puissance"] == avec_lieux["attendue"], nom


@pytest.mark.longue
def test_preuve_tient_rougit_si_les_lieux_rendent_le_pays_du_bourg(temoin, lieux):
    monde, vue = temoin
    mutes = dict(lieux)
    for nom, (cellule, avec_lieux) in lignes_des_points_corriges(monde, vue, lieux).items():
        mutes[avec_lieux["lieu"]] = vue[cellule["cid"]]
    assert mutes != lieux, "mutation sans effet"
    fautes, corriges = juger_le_grain_du_lieu(monde, vue, mutes)
    print(f"contre-épreuve des lieux au pays du bourg : {fautes} ; corrigés {corriges}")
    for nom in POINTS_CORRIGES:
        assert any(f.startswith(f"{nom} : ") for f in fautes), nom
        assert nom not in corriges
