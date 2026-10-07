"""Preuves de lecture et de refus de la table des puissances de 1400."""
import json
import math
import pathlib

import pytest
from sim.aggregation import charger_positions
from sim.puissances import PuissanceInvalide, charger_table

import copy
import dataclasses

from sim.aggregation import (
    PositionCelluleInconnue,
    derive_appartenance,
    facteur_de_projection,
    projeter,
)
from sim.puissances import (
    Ancre,
    Puissance,
    TableDesPuissances,
    cellules_non_couvertes,
    charger_latitude_moyenne_puissances,
    charger_portee,
    puissance_de_cellule,
    puissance_par_cellule,
    puissances_depuis_monde,
)
from sim.world import World

TABLE = pathlib.Path(__file__).parents[2] / "data" / "puissances-1400.json"
CAS_REFUS = [
    ("nature", "puissance 1", "nature"),
    ("religion", "puissance 1", "religion"),
    ("source_absente", "ancre 1", "source"),
    ("source_vide", "ancre 1", "source"),
    ("nom_vide", "ancre 1", "nom"),
    ("puissance_inconnue", "ancre 1", "puissance"),
    ("puissance_booleenne", "ancre 1", "puissance"),
    ("navarre_sans_ancre", "puissance {id_navarre}", "ancres"),
    ("id_puissance_duplique", "puissance 1", "id"),
    ("id_puissance_booleen", "puissance True", "id"),
    ("id_ancre_duplique", "ancre 1", "id"),
    ("id_ancre_booleen", "ancre False", "id"),
    ("lat_texte", "ancre 1", "lat"),
    ("lon_nan", "ancre 1", "lon"),
    ("lat_infinie", "ancre 1", "lat"),
    ("date", "champ date", "date"),
    ("ancres_vides", "champ ancres", "ancres"),
]
def _document():
    return json.loads(TABLE.read_text(encoding="utf-8"))
def _ecrire(tmp_path, document):
    chemin = tmp_path / "table.json"
    chemin.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    return chemin
def test_lecture_de_toutes_les_lignes(tmp_path):
    brut, table = _document(), charger_table()
    puissances_lues, ancres_lues = len(table.puissances), len(table.ancres)
    visees = {ancre.puissance for ancre in table.ancres}
    puissances_sans_ancre = sum(p.id not in visees for p in table.puissances)
    print(f"puissances_lues={puissances_lues}, ancres_lues={ancres_lues}")
    print(f"puissances_sans_ancre={puissances_sans_ancre}")
    assert 24 <= puissances_lues == len(brut["puissances"]) <= 40
    assert 46 <= ancres_lues == len(brut["ancres"]) <= 80
    assert puissances_sans_ancre == 0
    assert charger_table(_ecrire(tmp_path, brut)) == table
def _alterer(document, cas, id_navarre):
    puissance, ancre = document["puissances"][0], document["ancres"][0]
    if cas == "nature": puissance["nature"] = "duché"
    elif cas == "religion": puissance["religion"] = "protestante"
    elif cas == "source_absente": ancre.pop("source")
    elif cas == "source_vide": ancre["source"] = "   "
    elif cas == "nom_vide": ancre["nom"] = "  "
    elif cas == "puissance_inconnue": ancre["puissance"] = max(p["id"] for p in document["puissances"]) + 1
    elif cas == "puissance_booleenne": ancre["puissance"] = True
    elif cas == "navarre_sans_ancre": document["ancres"] = [a for a in document["ancres"] if a["puissance"] != id_navarre]
    elif cas == "id_puissance_duplique": document["puissances"][1]["id"] = puissance["id"]
    elif cas == "id_puissance_booleen": puissance["id"] = True
    elif cas == "id_ancre_duplique": document["ancres"][1]["id"] = ancre["id"]
    elif cas == "id_ancre_booleen": ancre["id"] = False
    elif cas == "lat_texte": ancre["lat"] = "51.51"
    elif cas == "lon_nan": ancre["lon"] = math.nan
    elif cas == "lat_infinie": ancre["lat"] = math.inf
    elif cas == "date": document["date"] = "1453-05-29"
    elif cas == "ancres_vides": document["ancres"] = []
def test_refus_d_une_alteration(tmp_path):
    refus_observes = 0
    for cas, ligne, champ in CAS_REFUS:
        document = _document()
        id_navarre = next(p["id"] for p in document["puissances"] if p["nom"] == "Navarre")
        _alterer(document, cas, id_navarre)
        with pytest.raises(PuissanceInvalide) as erreur:
            charger_table(_ecrire(tmp_path, document))
        message = str(erreur.value)
        assert ligne.format(id_navarre=id_navarre) in message and champ in message
        refus_observes += 1
    print(f"refus_observés={refus_observes}/{len(CAS_REFUS)}")
    assert refus_observes == len(CAS_REFUS)
    assert refus_observes > 0
def _connues(table):
    attendues = {"Angleterre", "Écosse", "France", "Portugal", "Castille", "Aragon", "Navarre", "Grenade", "Saint-Empire", "Bohême"}
    par_nom = {p.nom: p for p in table.puissances}
    if not attendues <= par_nom.keys():
        return False
    villes = {a.nom for a in table.ancres if a.puissance == par_nom["Angleterre"].id}
    return (par_nom["Grenade"].religion == "musulmane"
            and all(par_nom[n].religion == "catholique" for n in attendues - {"Grenade"})
            and any(p.nature == "Église" for p in table.puissances)
            and any(p.nature == "république" for p in table.puissances)
            and {"Londres", "Bordeaux", "Dublin"} <= villes)
def test_puissances_connues(tmp_path):
    assert _connues(charger_table())
    document = _document()
    next(p for p in document["puissances"] if p["nom"] == "Grenade")["religion"] = "catholique"
    religion_fausse = _connues(charger_table(_ecrire(tmp_path, document)))
    document = _document()
    document["ancres"] = [a for a in document["ancres"] if a["nom"] != "Bordeaux"]
    bordeaux_absente = _connues(charger_table(_ecrire(tmp_path, document)))
    print(f"vraie=1, religion_fausse={int(religion_fausse)}, bordeaux_absente={int(bordeaux_absente)}")
    assert not religion_fausse and not bordeaux_absente
def _compter_ancrage(table):
    positions = charger_positions()
    lats, lons = zip(*positions.values())
    hors = sum(not (min(lats) <= a.lat <= max(lats) and min(lons) <= a.lon <= max(lons)) for a in table.ancres)
    exclues = ((50.95, 1.86), (43.95, 4.81))
    sur_exclue = sum(any(abs(a.lat - lat) < .2 and abs(a.lon - lon) < .2 for lat, lon in exclues) for a in table.ancres)
    return hors, sur_exclue

def test_ancrage_dans_la_carte(tmp_path):
    assert _compter_ancrage(charger_table()) == (0, 0)
    document = _document()
    document["ancres"].append({"id": 24, "puissance": 1, "nom": "Calais", "lat": 50.95, "lon": 1.86, "source": "contre-épreuve"})
    calais = _compter_ancrage(charger_table(_ecrire(tmp_path, document)))
    document = _document()
    paris = next(a for a in document["ancres"] if a["nom"] == "Paris")
    paris["lat"], paris["lon"] = paris["lon"], paris["lat"]
    paris_inversee = _compter_ancrage(charger_table(_ecrire(tmp_path, document)))
    print(f"Calais={calais}, Paris_inversée={paris_inversee}")
    assert calais == (0, 1) and paris_inversee == (1, 0)


def test_portee_et_projection_se_lisent_et_se_refusent(tmp_path):
    document = _document()
    centres = json.loads(
        (TABLE.parent / "province-centres-1400.json").read_text(encoding="utf-8")
    )
    portee = charger_portee()
    latitude = charger_latitude_moyenne_puissances()
    assert math.isfinite(portee) and portee > 0
    assert latitude == centres["projection"]["mid_latitude"]

    alterations = []
    for champ, valeur in (
        ("portee", None),
        ("degres_projetes", None),
        ("degres_projetes", "4.0"),
        ("degres_projetes", True),
        ("degres_projetes", math.nan),
        ("degres_projetes", math.inf),
        ("degres_projetes", 0),
        ("degres_projetes", -1),
        ("niveau", 1),
        ("projection", None),
        ("mid_latitude", None),
        ("mid_latitude", "47.5"),
        ("mid_latitude", math.inf),
    ):
        altere = copy.deepcopy(document)
        if champ in ("portee", "projection"):
            del altere[champ]
        elif champ in ("degres_projetes", "niveau"):
            if valeur is None:
                del altere["portee"][champ]
            else:
                altere["portee"][champ] = valeur
        elif valeur is None:
            del altere["projection"][champ]
        else:
            altere["projection"][champ] = valeur
        alterations.append((champ, altere))

    refus_observes = 0
    for index, (champ, altere) in enumerate(alterations):
        chemin = tmp_path / f"portee-{index}.json"
        chemin.write_text(json.dumps(altere), encoding="utf-8")
        chargeur = (
            charger_latitude_moyenne_puissances
            if champ in ("projection", "mid_latitude")
            else charger_portee
        )
        with pytest.raises(PuissanceInvalide) as capture:
            chargeur(chemin)
        attendu = "projection" if champ == "projection" else champ
        assert attendu in str(capture.value)
        assert charger_table(chemin) == charger_table()
        refus_observes += 1

    print(f"portee={portee}, latitude_moyenne={latitude}")
    print(f"refus_observés={refus_observes}/{len(alterations)}")
    assert refus_observes == len(alterations)
    assert refus_observes > 0


def _cellule_la_plus_proche(point, positions, latitude_moyenne):
    @dataclasses.dataclass(frozen=True)
    class Centroide:
        id: int
        lat: float
        lon: float

    centroides = (
        Centroide(cell_id, latitude, longitude)
        for cell_id, (latitude, longitude) in positions.items()
    )
    return derive_appartenance({0: point}, centroides, latitude_moyenne)[0]


def test_geographie_des_puissances_et_des_non_couvertes():
    monde = World.charger(0)
    positions = charger_positions()
    latitude = charger_latitude_moyenne_puissances()
    table = charger_table()
    points = {
        "Paris": (48.86, 2.35),
        "Londres": (51.51, -0.13),
        "Le Caire": (30.04, 31.24),
        "Constantinople": (41.01, 28.98),
    }
    cellules = {
        nom: _cellule_la_plus_proche(point, positions, latitude)
        for nom, point in points.items()
    }
    assert len(set(cellules.values())) == len(cellules)
    vue = puissances_depuis_monde(monde)
    noms = {nom: puissance_de_cellule(cell_id, vue, table) for nom, cell_id in cellules.items()}
    non_couvertes = cellules_non_couvertes(vue)
    assert noms["Paris"].nom == "France"
    assert noms["Londres"].nom == "Angleterre"
    assert noms["Le Caire"].nom == "Mamelouks" and cellules["Le Caire"] not in non_couvertes
    assert noms["Constantinople"].nom == "Byzance" and cellules["Constantinople"] not in non_couvertes

    par_nom = {puissance.nom: puissance.id for puissance in table.puissances}
    france, angleterre = par_nom["France"], par_nom["Angleterre"]
    ancres_echangees = tuple(
        dataclasses.replace(
            ancre,
            puissance=(
                angleterre if ancre.puissance == france
                else france if ancre.puissance == angleterre
                else ancre.puissance
            ),
        )
        for ancre in table.ancres
    )
    table_echangee = dataclasses.replace(table, ancres=ancres_echangees)
    vue_echangee = puissances_depuis_monde(monde, table=table_echangee)
    assert puissance_de_cellule(cellules["Paris"], vue_echangee, table_echangee).nom == "Angleterre"
    assert puissance_de_cellule(cellules["Londres"], vue_echangee, table_echangee).nom == "France"

    vue_infinie = puissances_depuis_monde(monde, portee=math.inf)
    print(f"cellules_de_référence_distinctes={len(set(cellules.values()))}")
    print(f"non_couvertes={len(non_couvertes)}")
    assert puissance_de_cellule(cellules["Le Caire"], vue_infinie, table) is not None
    assert cellules_non_couvertes(vue_infinie) == ()


def test_compte_de_toutes_les_cellules_et_de_toutes_les_puissances():
    monde = World.charger(0)
    positions = charger_positions()
    table = charger_table()
    latitude = charger_latitude_moyenne_puissances()
    vue = puissances_depuis_monde(monde)
    non_couvertes = len(cellules_non_couvertes(vue))
    couvertes = sum(puissance_id is not None for puissance_id in vue.values())
    ids_puissances = {puissance.id for puissance in table.puissances}
    assert set(vue) == set(monde.cells)
    assert couvertes + non_couvertes == len(monde.cells)
    assert couvertes > 0 and non_couvertes > 0
    assert {valeur for valeur in vue.values() if valeur is not None} <= ids_puissances
    for puissance in table.puissances:
        assert puissance.id in vue.values(), puissance.nom

    facteur = facteur_de_projection(latitude)
    carres = []
    for position in positions.values():
        cellule_x, cellule_y = projeter(*position, facteur)
        for ancre in table.ancres:
            ancre_x, ancre_y = projeter(ancre.lat, ancre.lon, facteur)
            carres.append((cellule_x - ancre_x) ** 2 + (cellule_y - ancre_y) ** 2)
    plus_petite_distance = math.sqrt(min(carres))
    portee_minuscule = plus_petite_distance / 2
    vue_vide = puissances_depuis_monde(monde, portee=portee_minuscule)
    print(f"couvertes={couvertes}, non_couvertes={non_couvertes}")
    print(f"couvertes_portee_minuscule={sum(v is not None for v in vue_vide.values())}")
    assert plus_petite_distance > 0
    assert sum(valeur is not None for valeur in vue_vide.values()) == 0


def test_egalite_des_ancres_et_bord_de_portee():
    puissances = (
        Puissance(1, "A", "royaume", "catholique"),
        Puissance(2, "B", "royaume", "catholique"),
    )
    ancres = (
        Ancre(3, 1, "Ouest", 0.0, -1.0, "synthétique"),
        Ancre(7, 2, "Est", 0.0, 1.0, "synthétique"),
    )
    facteur = facteur_de_projection(0.0)
    cellule = projeter(0.0, 0.0, facteur)
    carres = tuple(
        sum((a - b) ** 2 for a, b in zip(cellule, projeter(ancre.lat, ancre.lon, facteur)))
        for ancre in ancres
    )
    gagnants = []
    for ordre in (ancres, tuple(reversed(ancres))):
        table = TableDesPuissances("1400-01-01", puissances, ordre)
        gagnants.append(puissance_par_cellule({11: (0.0, 0.0)}, table, 1.0, 0.0)[11])
    ancre_origine = dataclasses.replace(ancres[0], lon=0.0)
    table_une_ancre = TableDesPuissances("1400-01-01", puissances[:1], (ancre_origine,))
    sur_bord = puissance_par_cellule({11: (0.0, 1.0)}, table_une_ancre, 1.0, 0.0)
    au_dela = puissance_par_cellule(
        {11: (0.0, math.nextafter(1.0, math.inf))},
        table_une_ancre,
        1.0,
        0.0,
    )
    print(f"carres_exactement_egaux={carres[0] == carres[1]}, gagnants={gagnants}")
    assert carres[0] == carres[1]
    assert gagnants == [1, 1]
    assert sur_bord[11] == 1
    assert au_dela[11] is None


def test_vue_pure_que_le_tick_ne_lit_pas():
    monde = World.charger(0)
    avant = json.dumps(monde.to_dict(), sort_keys=True)
    attributs_avant = {cell_id: tuple(vars(cellule)) for cell_id, cellule in monde.cells.items()}
    premiere = puissances_depuis_monde(monde)
    seconde = puissances_depuis_monde(monde)
    apres = json.dumps(monde.to_dict(), sort_keys=True)
    attributs_apres = {cell_id: tuple(vars(cellule)) for cell_id, cellule in monde.cells.items()}
    positions = charger_positions()
    plus_petite = min(monde.cells)
    del positions[plus_petite]
    with pytest.raises(PositionCelluleInconnue) as capture:
        puissances_depuis_monde(monde, positions=positions)

    print(f"vues_identiques={premiere == seconde}, monde_inchangé={avant == apres}")
    print(f"cellule_absente_nommée={str(plus_petite) in str(capture.value)}")
    assert premiere == seconde
    assert avant == apres
    assert attributs_avant == attributs_apres
    assert str(plus_petite) in str(capture.value)


def test_lecture_des_douze_ajouts(tmp_path):
    attendues = {
        "Venise", "Milan", "Florence", "Gênes", "Papauté", "Naples",
        "Sicile", "Savoie", "Union de Kalmar", "Ordre teutonique",
        "Pologne-Lituanie", "Hongrie",
    }

    def compter(table):
        visees = {ancre.puissance for ancre in table.ancres}
        return sum(p.nom in attendues and p.id in visees for p in table.puissances)

    def verifier_bornes(table, document):
        assert 39 <= len(table.puissances) == len(document["puissances"]) <= 40
        assert 73 <= len(table.ancres) == len(document["ancres"]) <= 80

    table = charger_table()
    verifier_bornes(table, _document())
    ajouts_lus = compter(table)
    document = _document()
    hongrie = next(p for p in document["puissances"] if p["nom"] == "Hongrie")
    document["puissances"].remove(hongrie)
    document["ancres"] = [a for a in document["ancres"] if a["puissance"] != hongrie["id"]]
    table_reduite = charger_table(_ecrire(tmp_path, document))
    ajouts_reduits = compter(table_reduite)
    with pytest.raises(AssertionError):
        verifier_bornes(table_reduite, document)
    print(f"ajouts_lus={ajouts_lus}, ajouts_réduits={ajouts_reduits}, bornes_refusées=1")
    assert ajouts_lus == len(attendues) == 12
    assert ajouts_reduits == 11


@pytest.mark.parametrize("nom,champ,valeur", [
    ("Gênes", "ancres", None),
    ("Milan", "nature", "duché"),
    ("Savoie", "nature", "comté"),
    ("Hongrie", "religion", "protestante"),
])
def test_refus_des_nouveaux_cas(tmp_path, nom, champ, valeur):
    document = _document()
    puissance = next(p for p in document["puissances"] if p["nom"] == nom)
    if champ == "ancres":
        document["ancres"] = [a for a in document["ancres"] if a["puissance"] != puissance["id"]]
    else:
        puissance[champ] = valeur
    with pytest.raises(PuissanceInvalide) as erreur:
        charger_table(_ecrire(tmp_path, document))
    message = str(erreur.value)
    refus_observes = int(f"puissance {puissance['id']}" in message and champ in message)
    print(f"refus_observés={refus_observes}/1, cas={nom}, champ={champ}")
    assert refus_observes == 1
    assert next(p for p in charger_table().puissances if p.nom == "Milan").nature == "principauté"


def test_nouvelles_puissances_connues(tmp_path):
    attendues = {
        "Venise": "république", "Milan": "principauté", "Florence": "république",
        "Gênes": "république", "Papauté": "Église", "Naples": "royaume",
        "Sicile": "royaume", "Savoie": "principauté", "Union de Kalmar": "royaume",
        "Ordre teutonique": "ordre", "Pologne-Lituanie": "royaume", "Hongrie": "royaume",
    }

    def connues(table):
        par_nom = {p.nom: p for p in table.puissances}
        return (attendues.keys() <= par_nom.keys()
                and all(par_nom[nom].nature == nature and par_nom[nom].religion == "catholique"
                        for nom, nature in attendues.items()))

    vraie = connues(charger_table())
    document = _document()
    next(p for p in document["puissances"] if p["nom"] == "Papauté")["nature"] = "royaume"
    papaute_fausse = connues(charger_table(_ecrire(tmp_path, document)))
    document = _document()
    milan = next(p for p in document["puissances"] if p["nom"] == "Milan")
    document["puissances"].remove(milan)
    document["ancres"] = [a for a in document["ancres"] if a["puissance"] != milan["id"]]
    milan_absente = connues(charger_table(_ecrire(tmp_path, document)))
    print(f"connues={int(vraie)}, papauté_fausse={int(papaute_fausse)}, milan_absente={int(milan_absente)}")
    assert vraie and not papaute_fausse and not milan_absente


def test_geographie_et_compte_des_douze_nouvelles_puissances():
    monde = World.charger(0)
    positions = charger_positions()
    latitude = charger_latitude_moyenne_puissances()
    table = charger_table()
    points = {
        "Venise": (45.44, 12.33), "Milan": (45.46, 9.19),
        "Florence": (43.77, 11.26), "Papauté": (41.90, 12.50),
        "Gênes": (44.41, 8.93), "Naples": (40.85, 14.27),
        "Sicile": (38.12, 13.36), "Savoie": (45.57, 5.92),
        "Union de Kalmar": (55.68, 12.57), "Ordre teutonique": (54.04, 19.03),
        "Pologne-Lituanie": (50.06, 19.94), "Hongrie": (47.50, 19.04),
    }
    cellules = {nom: _cellule_la_plus_proche(point, positions, latitude)
                for nom, point in points.items()}
    vue = puissances_depuis_monde(monde)
    noms = {nom: puissance_de_cellule(cell_id, vue, table).nom
            for nom, cell_id in cellules.items()}
    couvertes = sum(p is not None for p in vue.values())
    non_couvertes = len(cellules_non_couvertes(vue))
    print(f"cellules_distinctes={len(set(cellules.values()))}, couvertes={couvertes}, non_couvertes={non_couvertes}")
    assert len(set(cellules.values())) == len(points) > 0
    assert noms == {nom: nom for nom in points}
    assert couvertes + non_couvertes == len(monde.cells)

    ids = {p.nom: p.id for p in table.puissances}
    venise, milan = ids["Venise"], ids["Milan"]
    echangees = tuple(dataclasses.replace(a, puissance=milan if a.puissance == venise
                                           else venise if a.puissance == milan else a.puissance)
                      for a in table.ancres)
    table_echangee = dataclasses.replace(table, ancres=echangees)
    vue_echangee = puissances_depuis_monde(monde, table=table_echangee)
    venise_echangee = puissance_de_cellule(cellules["Venise"], vue_echangee, table_echangee).nom
    milan_echangee = puissance_de_cellule(cellules["Milan"], vue_echangee, table_echangee).nom
    print(f"Venise_après_échange={venise_echangee}, Milan_après_échange={milan_echangee}")
    assert venise_echangee == "Milan" and milan_echangee == "Venise"

    verone = dataclasses.replace(next(a for a in table.ancres if a.nom == "Milan"),
                                 id=max(a.id for a in table.ancres) + 1,
                                 nom="Vérone", lat=45.44, lon=10.99)
    table_verone = dataclasses.replace(table, ancres=table.ancres + (verone,))
    vue_verone = puissances_depuis_monde(monde, table=table_verone)
    venise_avec_verone = puissance_de_cellule(cellules["Venise"], vue_verone, table_verone).nom
    print(f"Venise_avec_ancre_à_Vérone={venise_avec_verone}")
    assert venise_avec_verone == "Milan"

    table_sans_venise = dataclasses.replace(table, ancres=tuple(a for a in table.ancres if a.puissance != venise))
    vue_sans_venise = puissances_depuis_monde(monde, table=table_sans_venise)
    cellules_venise = sum(p == venise for p in vue.values())
    cellules_venise_sans_ancre = sum(p == venise for p in vue_sans_venise.values())
    print(f"cellules_de_Venise={cellules_venise}, sans_ancre={cellules_venise_sans_ancre}")
    assert cellules_venise > 0 and cellules_venise_sans_ancre == 0


def test_ancrage_sans_piege():
    table = charger_table()
    pieges = {
        "Vérone": (45.44, 10.99), "Pise": (43.72, 10.40),
        "Sienne": (43.32, 11.33), "Pérouse": (43.11, 12.39),
        "Bologne": (44.49, 11.34), "Padoue": (45.41, 11.88),
        "Turin": (45.07, 7.69), "Visby": (57.64, 18.29),
        "Candie": (35.34, 25.14), "Corfou": (39.62, 19.92),
    }

    def compter(ancres):
        return sum(any(abs(a.lat - lat) < .2 and abs(a.lon - lon) < .2
                       for lat, lon in pieges.values()) for a in ancres)

    ancres_sur_piege = compter(table.ancres)
    florence = next(a for a in table.ancres if a.nom == "Florence")
    lat, lon = pieges["Pise"]
    pise = dataclasses.replace(florence, id=max(a.id for a in table.ancres) + 1,
                               nom="Pise", lat=lat, lon=lon)
    contre_epreuve = compter(table.ancres + (pise,))
    print(f"ancres_sur_piege={ancres_sur_piege}, avec_Pise={contre_epreuve}")
    assert ancres_sur_piege == 0 and contre_epreuve == 1


ORIENT_CONNU = {
    "Byzance": ("empire", "orthodoxe"), "Ottomans": ("sultanat", "musulmane"),
    "Serbie": ("principauté", "orthodoxe"), "Bosnie": ("royaume", "catholique"),
    "Valachie": ("principauté", "orthodoxe"), "Moldavie": ("principauté", "orthodoxe"),
    "Novgorod": ("république", "orthodoxe"), "Pskov": ("république", "orthodoxe"),
    "Horde d'Or": ("khanat", "musulmane"), "Mamelouks": ("sultanat", "musulmane"),
    "Hafsides": ("sultanat", "musulmane"), "Zayyanides": ("sultanat", "musulmane"),
    "Mérinides": ("sultanat", "musulmane"), "Chypre": ("royaume", "catholique"),
    "Hospitaliers": ("ordre", "catholique"),
}


def test_lecture_des_quinze_ajouts_orientaux(tmp_path):
    def compter(table):
        visees = {a.puissance for a in table.ancres}
        return sum(p.nom in ORIENT_CONNU and p.id in visees for p in table.puissances)

    table = charger_table()
    ajouts_lus = compter(table)
    print(f"ajouts_lus={ajouts_lus}")
    assert ajouts_lus == len(ORIENT_CONNU) == 15
    lituanie = next(p.id for p in table.puissances if p.nom == "Pologne-Lituanie")
    assert {"Kiev", "Smolensk"} <= {a.nom for a in table.ancres if a.puissance == lituanie}
    document = _document()
    byzance = next(p for p in document["puissances"] if p["nom"] == "Byzance")
    document["puissances"].remove(byzance)
    document["ancres"] = [a for a in document["ancres"] if a["puissance"] != byzance["id"]]
    ajouts_reduits = compter(charger_table(_ecrire(tmp_path, document)))
    print(f"sans_Byzance={ajouts_reduits}")
    assert ajouts_reduits == 14
    with pytest.raises(AssertionError):
        assert ajouts_reduits == len(ORIENT_CONNU)


@pytest.mark.parametrize("nom,champ,valeur", [
    ("Byzance", "ancres", None), ("Ottomans", "nature", "beylik"),
    ("Horde d'Or", "nature", "horde"), ("Mamelouks", "religion", "copte"),
])
def test_refus_des_cas_orientaux(tmp_path, nom, champ, valeur):
    document = _document()
    puissance = next(p for p in document["puissances"] if p["nom"] == nom)
    if champ == "ancres":
        document["ancres"] = [a for a in document["ancres"] if a["puissance"] != puissance["id"]]
    else:
        puissance[champ] = valeur
    with pytest.raises(PuissanceInvalide) as erreur:
        charger_table(_ecrire(tmp_path, document))
    refus_observes = int(f"puissance {puissance['id']}" in str(erreur.value) and champ in str(erreur.value))
    print(f"refus_observés={refus_observes}/1, cas={nom}, champ={champ}")
    assert refus_observes == 1
    assert next(p for p in charger_table().puissances if p.nom == "Byzance").nature == "empire"


def test_puissances_orientales_connues(tmp_path):
    def connues(table):
        par_nom = {p.nom: (p.nature, p.religion) for p in table.puissances}
        return all(par_nom.get(nom) == traits for nom, traits in ORIENT_CONNU.items())

    vraie = connues(charger_table())
    print(f"connues={int(vraie)}, attendues={len(ORIENT_CONNU)}")
    assert vraie and len(ORIENT_CONNU) > 0
    document = _document()
    next(p for p in document["puissances"] if p["nom"] == "Byzance")["religion"] = "catholique"
    byzance_fausse = connues(charger_table(_ecrire(tmp_path, document)))
    document = _document()
    hospitaliers = next(p for p in document["puissances"] if p["nom"] == "Hospitaliers")
    document["puissances"].remove(hospitaliers)
    document["ancres"] = [a for a in document["ancres"] if a["puissance"] != hospitaliers["id"]]
    hospitaliers_absents = connues(charger_table(_ecrire(tmp_path, document)))
    print(f"Byzance_fausse={int(byzance_fausse)}, Hospitaliers_absents={int(hospitaliers_absents)}")
    assert not byzance_fausse and not hospitaliers_absents


def test_geographie_et_compte_des_puissances_orientales():
    monde, table = World.charger(0), charger_table()
    positions, latitude = charger_positions(), charger_latitude_moyenne_puissances()
    points = {
        "Mistra": (37.07, 22.37, "Byzance"), "Edirne": (41.68, 26.56, "Ottomans"),
        "Ankara": (39.93, 32.85, "Ottomans"), "Kruševac": (43.58, 21.33, "Serbie"),
        "Bobovac": (44.14, 18.22, "Bosnie"), "Târgoviște": (44.93, 25.46, "Valachie"),
        "Suceava": (47.65, 26.26, "Moldavie"), "Novgorod": (58.52, 31.27, "Novgorod"),
        "Pskov": (57.82, 28.33, "Pskov"), "Qırq Yer": (44.74, 33.88, "Horde d'Or"),
        "Tunis": (36.81, 10.18, "Hafsides"), "Tlemcen": (34.88, -1.32, "Zayyanides"),
        "Fès": (34.03, -5.00, "Mérinides"), "Nicosie": (35.17, 33.36, "Chypre"),
        "Rhodes": (36.43, 28.22, "Hospitaliers"), "Kiev": (50.45, 30.52, "Pologne-Lituanie"),
    }
    cellules = {nom: _cellule_la_plus_proche((lat, lon), positions, latitude)
                for nom, (lat, lon, _) in points.items()}
    vue = puissances_depuis_monde(monde)
    couvertes, non_couvertes = sum(p is not None for p in vue.values()), len(cellules_non_couvertes(vue))
    print(f"cellules_distinctes={len(set(cellules.values()))}, couvertes={couvertes}, non_couvertes={non_couvertes}")
    assert len(set(cellules.values())) == len(points) > 0
    assert couvertes + non_couvertes == len(monde.cells)
    assert {nom: puissance_de_cellule(cellule, vue, table).nom for nom, cellule in cellules.items()} == {
        nom: puissance for nom, (_, _, puissance) in points.items()}

    constantinople = _cellule_la_plus_proche((41.01, 28.98), positions, latitude)
    par_nom = {p.nom: p.id for p in table.puissances}
    byzance, ottomans = par_nom["Byzance"], par_nom["Ottomans"]
    echange = {byzance: ottomans, ottomans: byzance}
    table_echangee = dataclasses.replace(table, ancres=tuple(
        dataclasses.replace(a, puissance=echange.get(a.puissance, a.puissance)) for a in table.ancres))
    vue_echangee = puissances_depuis_monde(monde, table=table_echangee)
    assert puissance_de_cellule(constantinople, vue_echangee, table_echangee).nom == "Ottomans"
    assert puissance_de_cellule(cellules["Edirne"], vue_echangee, table_echangee).nom == "Byzance"
    bursa = dataclasses.replace(next(a for a in table.ancres if a.puissance == ottomans),
                               id=max(a.id for a in table.ancres) + 1, nom="Bursa", lat=40.19, lon=29.06)
    table_bursa = dataclasses.replace(table, ancres=table.ancres + (bursa,))
    vue_bursa = puissances_depuis_monde(monde, table=table_bursa)
    assert puissance_de_cellule(constantinople, vue_bursa, table_bursa).nom == "Ottomans"
    sans_nicosie = dataclasses.replace(table, ancres=tuple(a for a in table.ancres if a.nom != "Nicosie"))
    cellules_chypre = sum(p == par_nom["Chypre"] for p in vue.values())
    sans_ancre = sum(p == par_nom["Chypre"] for p in puissances_depuis_monde(monde, table=sans_nicosie).values())
    print(f"Constantinople_échangée=Ottomans, Edirne_échangée=Byzance, avec_Bursa=Ottomans, Chypre={cellules_chypre}, sans_Nicosie={sans_ancre}")
    assert cellules_chypre > 0 and sans_ancre == 0


def test_lacunes_expliquent_toutes_les_cellules_non_couvertes():
    from sim.puissances import charger_lacunes, lacune_par_cellule

    monde, positions = World.charger(0), charger_positions()
    vue, lacunes = puissances_depuis_monde(monde), charger_lacunes()
    portee, latitude = charger_portee(), charger_latitude_moyenne_puissances()
    assert len(lacunes) == 8 and all(l.raison.strip() for l in lacunes)
    assert tuple(l.id for l in lacunes) == tuple(sorted(l.id for l in lacunes))
    avant = copy.deepcopy((positions, vue, lacunes, monde.to_dict()))

    def compter(retenues):
        raisons = lacune_par_cellule(positions, vue, retenues, portee, latitude)
        assert set(raisons) == set(cellules_non_couvertes(vue))
        return len(raisons), sum(r is None for r in raisons.values()), sum(l.id not in raisons.values() for l in retenues)

    non_couvertes, sans_raison, lacunes_inutiles = compter(lacunes)
    print(f"non_couvertes={non_couvertes}, sans_raison={sans_raison}, lacunes_inutiles={lacunes_inutiles}")
    assert non_couvertes > 0 and sans_raison == lacunes_inutiles == 0
    sans_cyrenaique = compter(tuple(l for l in lacunes if l.nom != "Cyrénaïque"))
    paris = dataclasses.replace(lacunes[0], id=max(l.id for l in lacunes) + 1,
                                nom="Paris", lat=48.86, lon=2.35)
    avec_paris = compter(lacunes + (paris,))
    print(f"sans_Cyrénaïque={sans_cyrenaique}, avec_Paris={avec_paris}")
    assert sans_cyrenaique[1] == 1 and avec_paris[2] == 1
    assert compter(tuple(reversed(lacunes))) == (non_couvertes, sans_raison, lacunes_inutiles)
    assert (positions, vue, lacunes, monde.to_dict()) == avant
    with pytest.raises(dataclasses.FrozenInstanceError):
        paris.raison = "modifiée"


def test_refus_des_lacunes_sans_affecter_la_table(tmp_path):
    from sim.puissances import charger_lacunes

    cas = [
        ("lacunes", None), ("lacunes", []), ("lacunes", {}),
        ("raison", ""), ("raison", None), ("nom", "  "), ("nom", None),
        ("lat", "32.89"), ("lon", math.nan), ("lat", math.inf), ("lon", True),
        ("id", "dupliqué"), ("id", False),
    ]
    refus_observes = 0
    for champ, valeur in cas:
        document = _document()
        lacune = document["lacunes"][0]
        identifiant = lacune["id"]
        if champ == "lacunes":
            if valeur is None:
                del document[champ]
            else:
                document[champ] = valeur
            ligne = "champ lacunes"
        else:
            if valeur is None:
                del lacune[champ]
            elif champ == "id" and valeur == "dupliqué":
                document["lacunes"][1]["id"] = identifiant
            else:
                lacune[champ] = valeur
            ligne = f"lacune {valeur if champ == 'id' and isinstance(valeur, bool) else identifiant}"
        chemin = _ecrire(tmp_path, document)
        with pytest.raises(PuissanceInvalide) as erreur:
            charger_lacunes(chemin)
        assert ligne in str(erreur.value) and champ in str(erreur.value)
        assert charger_table(chemin) == charger_table()
        refus_observes += 1
    print(f"refus_observés={refus_observes}/{len(cas)}")
    assert refus_observes == len(cas) > 0


def test_ancrage_oriental_sans_piege():
    table = charger_table()
    pieges = {"Bursa": (40.19, 29.06), "Iznik": (40.43, 29.72), "Athènes": (37.98, 23.73)}

    def compter(ancres):
        return sum(any(abs(a.lat - lat) < .2 and abs(a.lon - lon) < .2
                       for lat, lon in pieges.values()) for a in ancres)

    ancres_sur_piege = compter(table.ancres)
    ottomans = next(p.id for p in table.puissances if p.nom == "Ottomans")
    bursa = dataclasses.replace(next(a for a in table.ancres if a.puissance == ottomans),
                               id=max(a.id for a in table.ancres) + 1, nom="Bursa", lat=40.19, lon=29.06)
    contre_epreuve = compter(table.ancres + (bursa,))
    print(f"ancres_sur_piege={ancres_sur_piege}, avec_Bursa={contre_epreuve}")
    assert ancres_sur_piege == 0 and contre_epreuve == 1


def test_lacune_departage_projection_et_bord_de_portee():
    from sim.puissances import charger_lacunes, lacune_par_cellule

    positions = charger_positions()
    latitude = charger_latitude_moyenne_puissances()
    paris = _cellule_la_plus_proche((48.86, 2.35), positions, latitude)
    londres = _cellule_la_plus_proche((51.51, -.13), positions, latitude)
    assert paris != londres
    lacunes = charger_lacunes()
    ouest = dataclasses.replace(lacunes[0], lat=0.0, lon=-1.0)
    est = dataclasses.replace(lacunes[1], lat=0.0, lon=1.0)
    vue = {paris: None, londres: charger_table().puissances[0].id}
    gagnants = [lacune_par_cellule({paris: (0.0, 0.0)}, vue, ordre, 1.0, 0.0)
                for ordre in ((ouest, est), (est, ouest))]
    assert gagnants == [{paris: ouest.id}, {paris: ouest.id}]
    origine = dataclasses.replace(ouest, lon=0.0)
    sur_bord = lacune_par_cellule({paris: (0.0, 1.0)}, vue, (origine,), 1.0, 0.0)
    au_dela = lacune_par_cellule({paris: (0.0, math.nextafter(1.0, math.inf))}, vue, (origine,), 1.0, 0.0)
    assert sur_bord == {paris: origine.id} and au_dela == {paris: None}
    portee = (facteur_de_projection(latitude) + 1.0) / 2
    avec_projection = lacune_par_cellule({paris: (0.0, 1.0)}, vue, (origine,), portee, latitude)
    sans_projection = lacune_par_cellule({paris: (0.0, 1.0)}, vue, (origine,), portee, 0.0)
    assert avec_projection == {paris: origine.id} and sans_projection == {paris: None}
    assert lacune_par_cellule({}, {}, lacunes, portee, latitude) == {}
    refus_observes = 0
    for invalide in (True, "1", math.nan, 0, -1):
        with pytest.raises(PuissanceInvalide, match="portee"):
            lacune_par_cellule({paris: (0.0, 0.0)}, vue, lacunes, invalide, latitude)
        refus_observes += 1
    print(f"départages={len(gagnants)}, bord_couvert={sur_bord[paris] is not None}, au_delà={au_dela[paris]}, refus_observés={refus_observes}")
    assert refus_observes > 0


def test_projection_epsg3035_au_centimetre():
    from sim.projection import projeter_epsg3035

    villes = json.loads((TABLE.parent / "villes-1400.json").read_text(encoding="utf-8"))["villes"]
    sieges = json.loads((TABLE.parent / "seigneuries-1400.json").read_text(encoding="utf-8"))["seigneuries"]
    points = [(v["latitude"], v["longitude"], v["x_m"], v["y_m"]) for v in villes]
    points += [(s["siege"]["lat"], s["siege"]["lon"], s["siege"]["x_m"], s["siege"]["y_m"])
               for s in sieges]
    assert len(villes) == 58 and sieges and len(points) == len(villes) + len(sieges)
    ecarts = [abs(obtenu - attendu) for lat, lon, x, y in points
              for obtenu, attendu in zip(projeter_epsg3035(lat, lon), (x, y))]
    assert max(ecarts) <= 0.01
    for alteration in ({"longitude_origine": 9.0}, {"aplatissement": 0.0}):
        assert any(abs(obtenu - attendu) > 0.01 for lat, lon, x, y in points
                   for obtenu, attendu in zip(projeter_epsg3035(lat, lon, **alteration), (x, y)))
    print(f"points_comparés={len(points)}, écart_maximal_m={max(ecarts)}")


def _carre_projete(latitude, longitude, demi_cote):
    from sim.projection import projeter_epsg3035

    x, y = projeter_epsg3035(latitude, longitude)
    return {"type": "Polygon", "coordinates": [[
        [x - demi_cote, y - demi_cote], [x + demi_cote, y - demi_cote],
        [x + demi_cote, y + demi_cote], [x - demi_cote, y + demi_cote],
        [x - demi_cote, y - demi_cote],
    ]]}


def test_ancre_contenue_synthetique():
    from sim.projection import projeter_epsg3035

    a = Ancre(3, 1, "A", 40.5, 10.0, "synthétique")
    b = Ancre(7, 2, "B", 40.1, 10.0, "synthétique")
    table = TableDesPuissances("1400-01-01", (), (a, b))
    positions, geometries = {11: (40.0, 10.0)}, {11: _carre_projete(a.lat, a.lon, 100)}
    assert puissance_par_cellule(positions, table, 1.0, 0.0, geometries)[11] == 1
    assert puissance_par_cellule(positions, table, 1.0, 0.0)[11] == 2
    assert puissance_par_cellule(positions, table, 0.2, 0.0, geometries)[11] is None
    deplacee = dataclasses.replace(table, ancres=(dataclasses.replace(a, lat=41.0), b))
    assert puissance_par_cellule(positions, deplacee, 2.0, 0.0, geometries)[11] == 2
    grande = {11: _carre_projete(40.0, 10.0, 200_000)}
    for ancres, attendue in (((a, b), 2),
                             ((dataclasses.replace(a, lat=40.0, lon=9.0),
                               dataclasses.replace(b, lat=40.0, lon=11.0)), 1)):
        for ordre in (ancres, tuple(reversed(ancres))):
            assert puissance_par_cellule(positions, dataclasses.replace(table, ancres=ordre),
                                         2.0, 0.0, grande)[11] == attendue
    # Le bord contient A ; un trou autour d'A l'exclut ; un MultiPolygon le retrouve.
    bord = _carre_projete(a.lat, a.lon, 100)
    x, _ = projeter_epsg3035(a.lat, a.lon)
    for sommet in (bord["coordinates"][0][0], bord["coordinates"][0][3], bord["coordinates"][0][4]):
        sommet[0] = x
    trou = copy.deepcopy(grande[11])
    trou["coordinates"].append(geometries[11]["coordinates"][0])
    multi = {"type": "MultiPolygon", "coordinates": [geometries[11]["coordinates"]]}
    for geometrie, attendue in ((bord, 1), (trou, 2), (multi, 1)):
        assert puissance_par_cellule(positions, table, 2.0, 0.0, {11: geometrie})[11] == attendue


def test_ancre_contenue_carte():
    from collections import Counter
    from sim.projection import projeter_epsg3035
    from sim.villes import point_dans_geometrie

    monde, table = World.charger(0), charger_table()
    positions, latitude = charger_positions(), charger_latitude_moyenne_puissances()
    vue = puissances_depuis_monde(monde)
    ancienne = puissance_par_cellule(positions, table, charger_portee(), latitude)
    ids = {p.nom: p.id for p in table.puissances}
    assert [vue[c] for c in (10374, 10032, 10366)] == [ids["Byzance"], ids["Byzance"], ids["Ottomans"]]
    assert [c for c in vue if vue[c] != ancienne[c]] == [10374]
    hors = {(a.id, a.nom) for a in table.ancres if not any(
        point_dans_geometrie(*projeter_epsg3035(a.lat, a.lon), cell["geometry"])
        for cell in monde.carte.values())}
    assert hors == {(25, "Venise"), (37, "Copenhague")}
    comptes = Counter(vue.values())
    assert (comptes[ids["Byzance"]], comptes[ids["Ottomans"]]) == (24, 48)
    assert (sum(p is not None for p in vue.values()), comptes[None]) == (565, 31)
    grenade = [a for a in table.ancres if a.nom in {"Grenade", "Malaga"}]
    assert len(grenade) == 2 and all(point_dans_geometrie(
        *projeter_epsg3035(a.lat, a.lon), monde.carte[10209]["geometry"]) for a in grenade)
    assert vue[10209] == ids["Grenade"]
    edirne = next(a for a in table.ancres if a.nom == "Edirne")
    for point, attendues in ((positions[10032], {10374: ids["Ottomans"], 10032: ids["Byzance"]}),
                             ((edirne.lat, edirne.lon), {10366: ids["Byzance"]})):
        alteree = dataclasses.replace(table, ancres=tuple(
            dataclasses.replace(a, lat=point[0], lon=point[1]) if a.nom == "Constantinople" else a
            for a in table.ancres))
        contre = puissances_depuis_monde(monde, table=alteree)
        assert all(contre[c] == p for c, p in attendues.items())
    print(f"Byzance={comptes[ids['Byzance']]}, Ottomans={comptes[ids['Ottomans']]}, hors_carte={hors}")


@pytest.mark.parametrize("absence", ["champ", "cellule", "valeur_nulle"])
def test_geometrie_absente(absence):
    from sim.maisons import maisons_depuis_monde

    monde = World.charger(0)
    assert puissances_depuis_monde(monde) and maisons_depuis_monde(monde)
    monde.carte = copy.deepcopy(monde.carte)
    cellule = min(monde.cells)
    if absence == "champ":
        monde.carte[cellule].pop("geometry")
    elif absence == "cellule":
        monde.carte.pop(cellule)
    else:
        monde.carte[cellule]["geometry"] = None
    for adapter in (puissances_depuis_monde, maisons_depuis_monde):
        with pytest.raises(PuissanceInvalide, match=f"cellule {cellule}"):
            adapter(monde)
