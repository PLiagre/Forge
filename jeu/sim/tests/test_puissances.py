"""Preuves de lecture et de refus de la table des puissances de 1400."""
import json
import math
import pathlib

import pytest
from sim.aggregation import charger_positions
from sim.puissances import PuissanceInvalide, charger_table

TABLE = pathlib.Path(__file__).parents[2] / "data" / "puissances-1400.json"
CAS_REFUS = [
    ("nature", "puissance 1", "nature"),
    ("religion", "puissance 1", "religion"),
    ("source_absente", "ancre 1", "source"),
    ("source_vide", "ancre 1", "source"),
    ("nom_vide", "ancre 1", "nom"),
    ("puissance_inconnue", "ancre 1", "puissance"),
    ("puissance_booleenne", "ancre 1", "puissance"),
    ("navarre_sans_ancre", "puissance 7", "ancres"),
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
    assert 12 <= puissances_lues == len(brut["puissances"]) <= 16
    assert 20 <= ancres_lues == len(brut["ancres"]) <= 30
    assert puissances_sans_ancre == 0
    assert charger_table(_ecrire(tmp_path, brut)) == table

def _alterer(document, cas):
    puissance, ancre = document["puissances"][0], document["ancres"][0]
    if cas == "nature": puissance["nature"] = "duché"
    elif cas == "religion": puissance["religion"] = "protestante"
    elif cas == "source_absente": ancre.pop("source")
    elif cas == "source_vide": ancre["source"] = "   "
    elif cas == "nom_vide": ancre["nom"] = "  "
    elif cas == "puissance_inconnue": ancre["puissance"] = max(p["id"] for p in document["puissances"]) + 1
    elif cas == "puissance_booleenne": ancre["puissance"] = True
    elif cas == "navarre_sans_ancre": document["ancres"] = [a for a in document["ancres"] if a["puissance"] != 7]
    elif cas == "id_puissance_duplique": document["puissances"][1]["id"] = puissance["id"]
    elif cas == "id_puissance_booleen": puissance["id"] = True
    elif cas == "id_ancre_duplique": document["ancres"][1]["id"] = ancre["id"]
    elif cas == "id_ancre_booleen": ancre["id"] = False
    elif cas == "lat_texte": ancre["lat"] = "51.51"
    elif cas == "lon_nan": ancre["lon"] = math.nan
    elif cas == "lat_infinie": ancre["lat"] = math.inf
    elif cas == "date": document["date"] = "1453-05-29"
    elif cas == "ancres_vides": document["ancres"] = []

@pytest.mark.parametrize("cas,ligne,champ", CAS_REFUS)
def test_refus_d_une_alteration(tmp_path, cas, ligne, champ):
    document = _document()
    _alterer(document, cas)
    with pytest.raises(PuissanceInvalide) as erreur:
        charger_table(_ecrire(tmp_path, document))
    nombre_de_cas = len(CAS_REFUS)
    print(f"nombre_de_cas={nombre_de_cas}, cas_joué={cas}")
    assert nombre_de_cas > 0 and ligne in str(erreur.value) and champ in str(erreur.value)

def _connues(table):
    attendues = {"Angleterre", "Écosse", "France", "Portugal", "Castille", "Aragon", "Navarre", "Grenade", "Saint-Empire", "Bohême"}
    par_nom = {p.nom: p for p in table.puissances}
    villes = {a.nom for a in table.ancres if a.puissance == par_nom["Angleterre"].id}
    return (attendues <= par_nom.keys() and par_nom["Grenade"].religion == "musulmane"
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
