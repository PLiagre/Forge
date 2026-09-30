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
    assert noms["Le Caire"] is None and cellules["Le Caire"] in non_couvertes
    assert noms["Constantinople"] is None and cellules["Constantinople"] in non_couvertes

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

    table = charger_table()
    ajouts_lus = compter(table)
    document = _document()
    hongrie = next(p for p in document["puissances"] if p["nom"] == "Hongrie")
    document["puissances"].remove(hongrie)
    document["ancres"] = [a for a in document["ancres"] if a["puissance"] != hongrie["id"]]
    table_reduite = charger_table(_ecrire(tmp_path, document))
    ajouts_reduits = compter(table_reduite)
    bornes_valides = (24 <= len(table_reduite.puissances) == len(document["puissances"]) <= 40
                      and 46 <= len(table_reduite.ancres) == len(document["ancres"]) <= 80)
    print(f"ajouts_lus={ajouts_lus}, ajouts_réduits={ajouts_reduits}, bornes_valides={bornes_valides}")
    assert ajouts_lus == len(attendues) == 12
    assert ajouts_reduits == 11 and not bornes_valides


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


def test_geographie_des_douze_nouvelles_puissances():
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
    assert puissance_de_cellule(cellules["Venise"], vue_echangee, table_echangee).nom == "Milan"
    assert puissance_de_cellule(cellules["Milan"], vue_echangee, table_echangee).nom == "Venise"

    verone = dataclasses.replace(next(a for a in table.ancres if a.nom == "Milan"),
                                 id=max(a.id for a in table.ancres) + 1,
                                 nom="Vérone", lat=45.44, lon=10.99)
    table_verone = dataclasses.replace(table, ancres=table.ancres + (verone,))
    vue_verone = puissances_depuis_monde(monde, table=table_verone)
    assert puissance_de_cellule(cellules["Venise"], vue_verone, table_verone).nom == "Milan"

    table_sans_venise = dataclasses.replace(table, ancres=tuple(a for a in table.ancres if a.puissance != venise))
    vue_sans_venise = puissances_depuis_monde(monde, table=table_sans_venise)
    assert venise not in vue_sans_venise.values()


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
