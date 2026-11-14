"""Preuves des maisons tenantes, avec leurs contre-épreuves."""
import ast
import copy
import dataclasses
import json
import pathlib
import re
import subprocess
import sys
from collections import Counter

import pytest

from sim.aggregation import PositionCelluleInconnue, charger_positions, derive_appartenance
from sim import engine, world as etat_monde
from sim.maisons import (
    charger_maisons, maison_de_cellule, maison_par_cellule, maisons_depuis_monde,
)
from sim.puissances import (
    PuissanceInvalide, charger_table, charger_portee,
    charger_latitude_moyenne_puissances, puissances_depuis_monde,
)
from sim.tests.test_puissances import _cellule_la_plus_proche
from sim.registre_maisons import charger_registre_maisons
from sim.world import World

TABLE = pathlib.Path(__file__).parents[2] / "data" / "puissances-1400.json"
NATURES_SANS_MAISON = {"république", "Église", "ordre"}
COUPLES = {
    "Angleterre": "Lancastre", "Écosse": "Stuart", "France": "Valois",
    "Portugal": "Aviz", "Castille": "Trastamare", "Aragon": "Barcelone",
    "Navarre": "Évreux", "Grenade": "Nasrides", "Saint-Empire": "Luxembourg",
    "Bohême": "Luxembourg", "Milan": "Visconti", "Naples": "Anjou-Durazzo",
    "Sicile": "Barcelone", "Savoie": "Savoie", "Union de Kalmar": "Poméranie",
    "Pologne-Lituanie": "Jagellon", "Hongrie": "Luxembourg", "Byzance": "Paléologue",
    "Ottomans": "Osman", "Serbie": "Lazarević", "Bosnie": "Kotromanić",
    "Valachie": "Basarab", "Moldavie": "Mușat", "Horde d'Or": "Djötchides",
    "Mamelouks": "Barquq", "Hafsides": "Hafsides", "Zayyanides": "Zayyanides",
    "Mérinides": "Mérinides", "Chypre": "Lusignan",
}
VASSAUX = {
    "Dijon": "Valois-Bourgogne", "Bruges": "Valois-Bourgogne", "Nantes": "Montfort",
    "Munich": "Wittelsbach", "Heidelberg": "Wittelsbach", "Vienne": "Habsbourg",
}
POINTS = {
    "Paris": (48.86, 2.35, "Valois"), "Dijon": (47.32, 5.04, "Valois-Bourgogne"),
    "Bruges": (51.21, 3.22, "Valois-Bourgogne"), "Nantes": (47.22, -1.55, "Montfort"),
    "Munich": (48.14, 11.58, "Wittelsbach"), "Heidelberg": (49.41, 8.69, "Wittelsbach"),
    "Vienne": (48.21, 16.37, "Habsbourg"), "Prague": (50.08, 14.44, "Luxembourg"),
    "Buda": (47.50, 19.04, "Luxembourg"), "Londres": (51.51, -0.13, "Lancastre"),
    "Constantinople": (41.01, 28.98, "Paléologue"), "Edirne": (41.68, 26.56, "Osman"),
    "Nicosie": (35.17, 33.36, "Lusignan"), "Venise": (45.44, 12.33, None),
}


def _document():
    return json.loads(TABLE.read_text(encoding="utf-8"))


def _ligne(document, liste, nom):
    return next(ligne for ligne in document[liste] if ligne["nom"] == nom)


def _ecrire(tmp_path, document):
    chemin = tmp_path / "maisons.json"
    chemin.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    return chemin


@pytest.fixture
def carte():
    monde, table, maisons = World.charger(0), charger_table(), charger_maisons()
    positions, latitude = charger_positions(), charger_latitude_moyenne_puissances()
    cellules = {nom: _cellule_la_plus_proche(p[:2], positions, latitude)
                for nom, p in POINTS.items()}
    return monde, table, maisons, positions, latitude, cellules


def test_lecture(tmp_path):
    table, maisons = charger_table(), charger_maisons()
    sans = [p for p in table.puissances if maisons.par_puissance[p.id] is None]
    vassaux = sum(maisons.par_ancre[a.id] != maisons.par_puissance[a.puissance]
                 for a in table.ancres)
    print(f"maisons_lues={len(maisons.maisons)}, puissances_lues={len(maisons.par_puissance)}, "
          f"avec_maison={len(table.puissances) - len(sans)}, sans_maison={len(sans)}, "
          f"vassaux_declares={vassaux}")
    assert len(maisons.maisons) == 30
    assert len(maisons.par_puissance) == 39 and len(sans) == 10
    assert all(p.nature in NATURES_SANS_MAISON for p in sans)
    assert vassaux == 6
    assert set(maisons.par_ancre) == {a.id for a in table.ancres}
    assert list(m.id for m in maisons.maisons) == sorted(m.id for m in maisons.maisons)
    document = _document()
    document["maisons"] = [m for m in document["maisons"] if m["nom"] != "Visconti"]
    milan = _ligne(document, "puissances", "Milan")
    milan.pop("maison")
    with pytest.raises(PuissanceInvalide, match=f"puissance {milan['id']}, champ maison"):
        charger_maisons(_ecrire(tmp_path, document))
    print("Milan_sans_maison_refusé=1")


CAS_REFUS = (
    ("maisons_absentes", None, None, "maisons"),
    ("France_absente", "puissances", "France", "maison"),
    ("Venise_ajoutee", "puissances", "Venise", "maison"),
    ("France_inconnue", "puissances", "France", "maison"),
    ("Nantes_inconnue", "ancres", "Nantes", "maison"),
    ("Vienne_redondante", "ancres", "Vienne", "maison"),
    ("nom_vide", "maisons", "Valois", "nom"),
    ("source_absente", "maisons", "Habsbourg", "source"),
    ("id_duplique", "maisons", "Valois", "id"),
    ("id_booleen", "maisons", "Valois", "id"),
    ("Habsbourg_sans_terre", "maisons", "Habsbourg", "maison"),
)


@pytest.mark.parametrize("cas,liste,nom,champ", CAS_REFUS)
def test_refus(tmp_path, cas, liste, nom, champ):
    document = _document()
    ligne = _ligne(document, liste, nom) if liste else None
    identifiant = ligne["id"] if ligne else None
    inconnue = max(m["id"] for m in document["maisons"]) + 1
    if cas == "maisons_absentes": document.pop("maisons")
    elif cas == "France_absente": ligne.pop("maison")
    elif cas == "Venise_ajoutee": ligne["maison"] = _ligne(document, "maisons", "Valois")["id"]
    elif cas in {"France_inconnue", "Nantes_inconnue"}: ligne["maison"] = inconnue
    elif cas == "Vienne_redondante": ligne["maison"] = _ligne(document, "puissances", "Saint-Empire")["maison"]
    elif cas == "nom_vide": ligne["nom"] = "  "
    elif cas == "source_absente": ligne.pop("source")
    elif cas == "id_duplique": ligne["id"] = identifiant = _ligne(document, "maisons", "Lancastre")["id"]
    elif cas == "id_booleen": ligne["id"] = identifiant = True
    elif cas == "Habsbourg_sans_terre": _ligne(document, "ancres", "Vienne").pop("maison")
    chemin = _ecrire(tmp_path, document)
    assert charger_table(chemin) == charger_table()
    with pytest.raises(PuissanceInvalide) as erreur:
        charger_maisons(chemin)
    sorte = {"puissances": "puissance", "ancres": "ancre", "maisons": "maison"}
    attendu = f"{sorte[liste]} {identifiant}, champ {champ}" if liste else "champ maisons"
    assert attendu in str(erreur.value)
    assert charger_maisons()  # Contre-épreuve : le lecteur accepte la vraie table.
    print(f"cas={cas}, refus_observés=1/1, cas_prévus={len(CAS_REFUS)}")


def _connues(table, maisons):
    noms = {m.id: m.nom for m in maisons.maisons}
    puissances = {p.nom: noms.get(maisons.par_puissance[p.id]) for p in table.puissances}
    ancres = {a.nom: noms.get(maisons.par_ancre[a.id]) for a in table.ancres}
    return (bool(COUPLES) and bool(VASSAUX)
            and all(puissances.get(p) == m for p, m in COUPLES.items())
            and all(ancres.get(a) == m for a, m in VASSAUX.items()))


def test_connues(tmp_path):
    assert _connues(charger_table(), charger_maisons())
    for nom, liste, mauvaise in (("France", "puissances", "Lancastre"),
                                ("Vienne", "ancres", "Wittelsbach")):
        document = _document()
        _ligne(document, liste, nom)["maison"] = _ligne(document, "maisons", mauvaise)["id"]
        # Retirer la maison dépossédée permet d'éprouver l'attribution historique,
        # une fois la table acceptée par la validation des tenures.
        depossedee = "Valois" if nom == "France" else "Habsbourg"
        document["maisons"] = [m for m in document["maisons"] if m["nom"] != depossedee]
        chemin = _ecrire(tmp_path, document)
        assert not _connues(charger_table(chemin), charger_maisons(chemin))
    print(f"couples_vus={len(COUPLES)}, ancres_connues={len(VASSAUX)}, contre_épreuves_fausses=2")


def _vassaux(monde, table, maisons, positions, latitude):
    puissances = puissances_depuis_monde(monde, positions, table)
    vue = maisons_depuis_monde(monde, positions, table, maisons)
    declares = [a for a in table.ancres
                if maisons.par_ancre[a.id] != maisons.par_puissance[a.puissance]]
    hors = 0
    for ancre in declares:
        cellule = _cellule_la_plus_proche((ancre.lat, ancre.lon), positions, latitude)
        hors += (puissances[cellule] != ancre.puissance
                 or vue[cellule] != maisons.par_ancre[ancre.id])
    assert declares
    return len(declares), hors


def test_vassaux(carte):
    monde, table, maisons, positions, latitude, cellules = carte
    vus, hors = _vassaux(monde, table, maisons, positions, latitude)
    assert (vus, hors) == (6, 0)
    prague = next(a for a in table.ancres if a.nom == "Prague")
    munich = next(a for a in table.ancres if a.nom == "Munich")
    intruse = dataclasses.replace(prague, id=max(a.id for a in table.ancres) + 1,
                                 puissance=munich.puissance, nom="Vassal intrus à Prague")
    alteree = dataclasses.replace(table, ancres=table.ancres + (intruse,))
    tenantes = dataclasses.replace(maisons, par_ancre={**maisons.par_ancre,
                                  intruse.id: maisons.par_ancre[munich.id]})
    contre_vus, contre_hors = _vassaux(monde, alteree, tenantes, positions, latitude)
    assert contre_hors == 1 and contre_vus == vus + 1
    assert puissances_depuis_monde(monde, table=alteree)[cellules["Prague"]] == prague.puissance
    assert derive_appartenance({cellules["Prague"]: (prague.lat, prague.lon)},
                              alteree.ancres, latitude)[cellules["Prague"]] == prague.id
    print(f"vassaux_vus={vus}, vassaux_hors={hors}, intrus_hors={contre_hors}, "
          "égalité_Prague_gagnée=1")


def test_geographie(carte):
    monde, table, maisons, positions, latitude, cellules = carte
    vue = maisons_depuis_monde(monde)
    assert len(set(cellules.values())) == len(POINTS) > 0
    for nom, (_, _, attendue) in POINTS.items():
        maison = maison_de_cellule(cellules[nom], vue, maisons)
        assert (maison.nom if maison else None) == attendue, nom
    venise = next(p for p in table.puissances if p.nom == "Venise")
    assert venise.nature == "république"
    assert puissances_depuis_monde(monde)[cellules["Venise"]] == venise.id
    ancres = {a.nom: a.id for a in table.ancres}
    ids = {m.nom: m.id for m in maisons.maisons}
    tenantes = dict(maisons.par_ancre)
    for nom in ("Dijon", "Bruges"): tenantes[ancres[nom]] = ids["Valois"]
    sans_bourgogne = maisons_depuis_monde(monde, maisons=dataclasses.replace(maisons, par_ancre=tenantes))
    assert all(sans_bourgogne[cellules[n]] == ids["Valois"] for n in ("Dijon", "Bruges"))
    assert ids["Valois-Bourgogne"] not in sans_bourgogne.values()
    tenantes = dict(maisons.par_ancre)
    tenantes[ancres["Vienne"]], tenantes[ancres["Munich"]] = tenantes[ancres["Munich"]], tenantes[ancres["Vienne"]]
    echange = maisons_depuis_monde(monde, maisons=dataclasses.replace(maisons, par_ancre=tenantes))
    assert echange[cellules["Vienne"]] == ids["Wittelsbach"]
    assert echange[cellules["Munich"]] == ids["Habsbourg"]
    print(f"points_vus={len(POINTS)}, cellules_distinctes={len(set(cellules.values()))}, "
          "Bourgogne_absente=1, villes_échangées=2")


def _compter(monde, table, maisons, vue):
    puissances = puissances_depuis_monde(monde, table=table)
    par_id = {p.id: p for p in table.puissances}
    avec = sans = non_couvertes = incoherentes = 0
    assert set(vue) == set(monde.cells) and vue
    for cellule, puissance in puissances.items():
        maison = vue[cellule]
        if puissance is None:
            non_couvertes += 1
            assert maison is None
        elif par_id[puissance].nature in NATURES_SANS_MAISON:
            sans += 1
            assert maison is None
        else:
            avec += 1
            assert maison is not None
            permises = {maisons.par_puissance[puissance]} | {
                maisons.par_ancre[a.id] for a in table.ancres if a.puissance == puissance}
            incoherentes += maison not in permises
    return avec, sans, non_couvertes, incoherentes


def _chaque_maison(vue, maisons):
    assert vue and maisons.maisons
    comptes = Counter(vue.values())
    for maison in maisons.maisons:
        assert comptes[maison.id] > 0, f"maison {maison.nom} : aucune cellule"


def test_compte(carte):
    monde, table, maisons, positions, latitude, cellules = carte
    vue = maisons_depuis_monde(monde)
    avec, sans, non_couvertes, incoherentes = _compter(monde, table, maisons, vue)
    assert (avec, sans, non_couvertes) == (476, 89, 31)
    assert avec + sans + non_couvertes == len(monde.cells) and incoherentes == 0
    _chaque_maison(vue, maisons)
    ids = {m.nom: m.id for m in maisons.maisons}
    fausse = {**vue, cellules["Paris"]: ids["Habsbourg"]}
    assert _compter(monde, table, maisons, fausse)[-1] == 1
    chypriote = next(p for p in table.puissances if p.nom == "Chypre")
    # Recalcul des tenantes héritées après l'altération de la puissance.
    tenantes = {a.id: ids["Lancastre"] if a.puissance == chypriote.id else maisons.par_ancre[a.id]
                for a in table.ancres}
    alteree = dataclasses.replace(maisons, par_puissance={**maisons.par_puissance,
                                 chypriote.id: ids["Lancastre"]}, par_ancre=tenantes)
    with pytest.raises(AssertionError, match="Lusignan"):
        _chaque_maison(maisons_depuis_monde(monde, maisons=alteree), alteree)
    print(f"avec_maison={avec}, sans_maison_declaree={sans}, non_couvertes={non_couvertes}, "
          f"incoherentes={incoherentes}, Paris_incohérente=1, Lusignan_absente=1")


def test_pure(carte):
    monde, table, maisons, positions, latitude, cellules = carte
    avant = copy.deepcopy(monde.to_dict())
    attributs = {c: copy.deepcopy(vars(cellule)) for c, cellule in monde.cells.items()}
    tables = copy.deepcopy((table, maisons, positions))
    vue = maisons_depuis_monde(monde, positions, table, maisons)
    assert vue == maisons_depuis_monde(monde, positions, table, maisons)
    assert monde.to_dict() == avant
    assert {c: vars(cellule) for c, cellule in monde.cells.items()} == attributs
    assert (table, maisons, positions) == tables
    cellule = cellules["Paris"]
    incompletes = dict(positions)
    incompletes.pop(cellule)
    with pytest.raises(PositionCelluleInconnue, match=f"cellule {cellule}"):
        maisons_depuis_monde(monde, positions=incompletes)
    sim = TABLE.parents[1] / "sim"
    comptes = []
    for fichier in ("engine.py", "model.py", "maisons.py"):
        resultat = subprocess.run(["grep", "-c", "maisons", str(sim / fichier)],
                                  capture_output=True, text=True, check=False)
        assert resultat.returncode in (0, 1)
        comptes.append(int(resultat.stdout))
    assert comptes[:-1] == [0, 0] and comptes[-1] > 0
    source_monde = (sim / "world.py").read_text(encoding="utf-8")
    assert "sim.maisons" not in source_monde and "maisons_depuis_monde" not in source_monde
    assert all("maisons" not in n.name or n.name == "charger_registre_maisons"
               for n in ast.walk(ast.parse(source_monde)) if isinstance(n, ast.alias))
    _tick_sans_lecture_registre(pytest.MonkeyPatch(), monde, engine.tick, 0)
    assert vue
    print(f"cellules_pures={len(vue)}, lectures_tick={comptes[:-1]}, module_lisible={comptes[-1]}")


def test_refus_ancre_absente_de_la_vue(carte):
    monde, table, maisons, positions, latitude, cellules = carte
    ancre = next(a for a in table.ancres if a.nom == "Paris")
    tenantes = dict(maisons.par_ancre)
    tenantes.pop(ancre.id)
    with pytest.raises(PuissanceInvalide, match=f"ancre {ancre.id}, champ maison"):
        maison_par_cellule(positions, table, dataclasses.replace(maisons, par_ancre=tenantes),
                           charger_portee(), latitude)
    print("ancre_absente_refusée=1")


def test_ancre_contenue(carte):
    from sim.projection import projeter_epsg3035
    from sim.puissances import ancre_par_cellule
    from sim.villes import point_dans_geometrie

    monde, table, maisons, positions, latitude, cellules = carte
    geometries = {c: ligne["geometry"] for c, ligne in monde.carte.items()}
    ancres = ancre_par_cellule(positions, table, charger_portee(), latitude, geometries)
    vue = maisons_depuis_monde(monde)
    ids = {m.nom: m.id for m in maisons.maisons}
    assert vue[10374] == ids["Paléologue"]
    assert _compter(monde, table, maisons, vue) == (476, 89, 31, 0)
    assert ancres and all(vue[c] == (maisons.par_ancre[a] if a is not None else None)
                          for c, a in ancres.items())
    deplacee = dataclasses.replace(table, ancres=tuple(
        dataclasses.replace(a, lat=positions[10032][0], lon=positions[10032][1])
        if a.nom == "Constantinople" else a for a in table.ancres))
    assert maisons_depuis_monde(monde, table=deplacee)[10374] == ids["Osman"]
    constantinople = next(a for a in table.ancres if a.nom == "Constantinople")
    lat, lon = positions[10374]
    assert point_dans_geometrie(*projeter_epsg3035(lat, lon), geometries[10374])
    intruse = dataclasses.replace(constantinople, id=max(a.id for a in table.ancres) + 1,
                                 nom="Ancre synthétique", lat=lat, lon=lon)
    alteree = dataclasses.replace(table, ancres=table.ancres + (intruse,))
    tenantes = dataclasses.replace(maisons, par_ancre={**maisons.par_ancre,
                                  intruse.id: ids["Wittelsbach"]})
    assert maisons_depuis_monde(monde, table=alteree, maisons=tenantes)[10374] == ids["Wittelsbach"]
    assert puissances_depuis_monde(monde, table=alteree)[10374] == constantinople.puissance
    print(f"ancres_vérifiées={sum(a is not None for a in ancres.values())}, comptes=(476, 89, 31)")


# Capitales : la maison jouée par l'IA est distincte de sa tenure dérivée.
import random

from sim.capitales import charger_capitales, cellule_de_capitale, maisons_de_l_ia
from sim.engine import tick
from sim.intentions import deposer_intention
from sim.model import _NoBadSpatialField
from sim.projection import projeter_epsg3035
from sim.seigneuries import charger_seigneuries, cellule_du_siege

CAPITALES = TABLE.with_name("capitales-1400.json")
CELLULES_CAPITALES = (
    10237, 10206, 10322, 10231, 10204, 10313, 10192, 10209, 10284, 10466,
    10283, 10433, 9892, 10327, 10374, 10366, 10329, 10300, 10362, 10371,
    None, 8992, 10143, 9788, 9831, 10059, 10420, 10191, 10452, 10294,
)


def test_capitale_lecture():
    capitales = charger_capitales()
    assert len(capitales) == 30
    assert {c.maison for c in capitales} == {m.id for m in charger_maisons().maisons}
    assert tuple(c.maison for c in capitales) == tuple(sorted(c.maison for c in capitales))
    assert all(isinstance(c, _NoBadSpatialField) for c in capitales)
    with pytest.raises(dataclasses.FrozenInstanceError):
        capitales[0].nom = "Paris"


@pytest.mark.parametrize("champ,valeur", [
    ("capitales", None), ("capitales", []), ("capitales", {}),
    ("date", None), ("date", "1401-01-01"),
    ("maison", None), ("maison", 999), ("maison", True), ("maison", 1.5),
    ("maison", 2), ("nom", None), ("nom", "  "),
    ("source", None), ("source", "  "), ("hors_carte", None), ("hors_carte", "  "),
] + [(champ, valeur) for champ in ("lat", "lon")
     for valeur in (None, True, "48", float("nan"), float("inf"), -float("inf"))])
def test_capitale_refus(tmp_path, champ, valeur):
    document = json.loads(CAPITALES.read_text(encoding="utf-8"))
    ligne = document["capitales"][0]
    if champ in ("date", "capitales"):
        if valeur is None:
            document.pop(champ)
        else:
            document[champ] = valeur
        maison = "inconnue"
    else:
        ligne[champ] = valeur
        maison = repr(valeur) if champ == "maison" else "1"
    with pytest.raises(PuissanceInvalide) as erreur:
        charger_capitales(_ecrire(tmp_path, document))
    assert f"maison {maison}, champ {champ}" in str(erreur.value)


def test_capitale_manquante_et_ligne_invalide(tmp_path):
    document = json.loads(CAPITALES.read_text(encoding="utf-8"))
    document["capitales"] = [c for c in document["capitales"] if c["maison"] != 26]
    with pytest.raises(PuissanceInvalide, match="maison 26, champ maison"):
        charger_capitales(_ecrire(tmp_path, document))
    document["capitales"].append(None)
    with pytest.raises(PuissanceInvalide, match="maison inconnue, champ maison"):
        charger_capitales(_ecrire(tmp_path, document))


def _preuve_coherence_capitales(vue, tenantes):
    placees = [m for m in vue if m.sorte == "grande maison" and m.cell_id is not None]
    assert placees
    incoherentes = sum(tenantes[m.cell_id] != m.id for m in placees)
    assert incoherentes == 0, f"capitales incohérentes : {incoherentes}"


def test_capitale_polygones_et_coherence(carte, tmp_path):
    monde = carte[0]
    capitales = charger_capitales()
    vue = maisons_de_l_ia(monde)
    assert tuple(m.cell_id for m in vue[:30]) == CELLULES_CAPITALES
    assert sum(m.cell_id is not None for m in vue[:30]) == 29
    hors = [m for m in vue[:30] if m.cell_id is None]
    assert len(hors) == 1 and hors[0].id == 21
    assert hors[0].nom == "Djötchides" and hors[0].capitale == "Saraï" and hors[0].hors_carte
    tenantes = maisons_depuis_monde(monde)
    _preuve_coherence_capitales(vue, tenantes)
    sarai = next(c for c in capitales if c.maison == 21)
    with pytest.raises(PuissanceInvalide, match="maison 21.*hors carte"):
        cellule_de_capitale(dataclasses.replace(sarai, hors_carte=None), monde.carte)
    paris = next(c for c in capitales if c.maison == 3)
    with pytest.raises(PuissanceInvalide, match="maison 3.*10322"):
        cellule_de_capitale(dataclasses.replace(paris, hors_carte="Déclaration fausse"), monde.carte)
    document = json.loads(CAPITALES.read_text(encoding="utf-8"))
    document["capitales"][0].update(lat=paris.lat, lon=paris.lon)
    fausse = maisons_de_l_ia(monde, capitales=charger_capitales(_ecrire(tmp_path, document)))
    assert sum(tenantes[m.cell_id] != m.id for m in fausse[:30] if m.cell_id is not None) == 1
    with pytest.raises(AssertionError, match="incohérentes : 1"):
        _preuve_coherence_capitales(fausse, tenantes)


def test_capitale_frontiere_sans_centroide():
    capitale = charger_capitales()[0]
    x, y = projeter_epsg3035(capitale.lat, capitale.lon)
    def carre(gauche, droite, bas, haut):
        return {"geometry": {"type": "Polygon", "coordinates": [[
            [gauche, bas], [droite, bas], [droite, haut], [gauche, haut], [gauche, bas]]]}}
    carte = {20: carre(x, x + 100, y - 50, y + 50),
             10: carre(x - 2, x, y - 1, y + 1)}
    assert cellule_de_capitale(capitale, carte) == 10
    # Le point est dans le grand carré, plus proche du centre du petit.
    carte[10] = carre(x - 3, x - 1, y - 1, y + 1)
    assert cellule_de_capitale(capitale, carte) == 20
    with pytest.raises(PuissanceInvalide, match="maison 1.*hors carte"):
        cellule_de_capitale(capitale, {})


def _preuve_departs_ia(vue, monde, seigneuries, joueur=None):
    attendues = [s for s in seigneuries if s.id != joueur]
    departs = [m for m in vue if m.sorte == "seigneurie"]
    assert attendues and [m.id for m in departs] == [s.id for s in attendues]
    for maison, seigneurie in zip(departs, attendues):
        assert (maison.nom, maison.capitale, maison.cell_id, maison.source, maison.hors_carte) == (
            seigneurie.maison, seigneurie.siege.nom,
            cellule_du_siege(seigneurie, monde.carte), seigneurie.source, None)


def test_capitale_maisons_ia_et_choix(carte):
    monde = carte[0]
    seigneuries = charger_seigneuries()
    capitales = charger_capitales()
    grandes, total = len(capitales), len(capitales) + len(seigneuries)
    assert capitales and seigneuries
    vue = maisons_de_l_ia(monde)
    assert len(vue) == total
    assert [m.sorte for m in vue] == ["grande maison"] * grandes + ["seigneurie"] * len(seigneuries)
    assert [m.id for m in vue[:grandes]] == [c.maison for c in capitales]
    _preuve_departs_ia(vue, monde, seigneuries)
    assert sum(m.nom == "Paléologue" for m in vue) == 2
    for seigneurie in seigneuries:
        choisi = copy.deepcopy(monde)
        deposer_intention(choisi, {"type": "choisir_depart", "seigneurie": seigneurie.id})
        assert maisons_de_l_ia(choisi) == vue  # Le dépôt attend le tick.
        tick(choisi, random.Random(0), 0)
        apres = maisons_de_l_ia(choisi)
        assert len(apres) == total - 1 and apres[:grandes] == vue[:grandes]
        _preuve_departs_ia(apres, choisi, seigneuries, seigneurie.id)
        assert {m.id for m in apres if m.sorte == "seigneurie"} == {
            s.id for s in seigneuries if s.id != seigneurie.id}
        assert any(m.id == 15 and m.capitale == "Constantinople" and m.cell_id == 10374
                   for m in apres if m.sorte == "grande maison")
        if seigneurie.maison == "Bar":
            choisi.maison_du_joueur = None
            fausse = maisons_de_l_ia(choisi)
            assert len(fausse) == total
            with pytest.raises(AssertionError):
                assert all(m.nom != "Bar" for m in fausse)


def test_capitale_zab_contre_epreuves(carte):
    monde = carte[0]
    seigneuries = charger_seigneuries()
    zab = next(s for s in seigneuries if s.nom == "Émirat du Zab")
    vue = maisons_de_l_ia(monde)
    sans_zab = tuple(m for m in vue if not (m.sorte == "seigneurie" and m.id == zab.id))
    with pytest.raises(AssertionError):
        _preuve_departs_ia(sans_zab, monde, seigneuries)
    choisi = copy.deepcopy(monde)
    deposer_intention(choisi, {"type": "choisir_depart", "seigneurie": zab.id})
    assert maisons_de_l_ia(choisi) == vue
    tick(choisi, random.Random(0), 0)
    apres = maisons_de_l_ia(choisi)
    _preuve_departs_ia(apres, choisi, seigneuries, zab.id)
    intruse = next(m for m in vue if m.sorte == "seigneurie" and m.id == zab.id)
    with pytest.raises(AssertionError):
        _preuve_departs_ia(apres + (intruse,), choisi, seigneuries, zab.id)


def test_capitale_vue_pure(carte):
    monde, table, maisons, positions = carte[:4]
    capitales, seigneuries = charger_capitales(), charger_seigneuries()
    avant = copy.deepcopy((monde.to_dict(), monde.carte,
                           {c: vars(cell) for c, cell in monde.cells.items()},
                           table, maisons, positions, capitales, seigneuries))
    vue = maisons_de_l_ia(monde, capitales, maisons, seigneuries, positions)
    assert vue == maisons_de_l_ia(monde, capitales, maisons, seigneuries, positions)
    assert (monde.to_dict(), monde.carte, {c: vars(cell) for c, cell in monde.cells.items()},
            table, maisons, positions, capitales, seigneuries) == avant
    assert isinstance(vue, tuple) and all(isinstance(m, _NoBadSpatialField) for m in vue)
    with pytest.raises(dataclasses.FrozenInstanceError):
        vue[0].cell_id = 0
    cellule = min(monde.cells)
    with pytest.raises(PositionCelluleInconnue, match=f"cellule {cellule}"):
        maisons_de_l_ia(monde, positions={c: p for c, p in positions.items() if c != cellule})
    sim = TABLE.parents[1] / "sim"
    comptes = [subprocess.run(["grep", "-c", "capitales", str(sim / fichier)],
                             capture_output=True, text=True, check=False)
               for fichier in ("engine.py", "world.py", "model.py", "capitales.py")]
    assert [int(r.stdout) for r in comptes[:3]] == [0, 0, 0]
    assert int(comptes[-1].stdout) > 0
    with pytest.raises(AssertionError):
        assert int(comptes[-1].stdout) == 0  # La garde détecte un lecteur.

@pytest.fixture
def registre(carte, tmp_path):
    from sim.registre_maisons import charger_registre_maisons, valider_registre_maisons
    chemins = [TABLE, CAPITALES, TABLE.with_name("seigneuries-1400.json")]
    documents = [json.loads(p.read_text(encoding="utf-8")) for p in chemins]
    copies = [tmp_path / p.name for p in chemins]
    def charger():
        for p, d in zip(copies, documents):
            p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        avant = [p.read_bytes() for p in copies]
        resultat = charger_registre_maisons(carte[0].carte, *copies)
        assert [p.read_bytes() for p in copies] == avant
        return resultat
    return carte[0], documents, charger, valider_registre_maisons

def _preuve_registre(vue, documents, carte):
    from sim.villes import point_dans_geometrie
    puissances, capitales, departs = documents
    racines = {p["id"]: f"grande-{p['maison']}" if "maison" in p else f"institution-{p['id']}" for p in puissances["puissances"]}
    noms = {m["id"]: m["nom"] for m in puissances["maisons"]}
    attendus = {f"grande-{c['maison']}": (noms[c["maison"]], "grande maison", None, c) for c in capitales["capitales"]}
    for p in puissances["puissances"]:
        if "maison" not in p:
            ancre = min((a for a in puissances["ancres"] if a["puissance"] == p["id"]), key=lambda a: a["id"])
            attendus[racines[p["id"]]] = (p["nom"], "institution", None, ancre)
    attendus.update({f"seigneurie-{s['id']}": (s["maison"], "seigneurie", racines[s["suzerain"]], s["siege"]) for s in departs["seigneuries"]})
    assert len(vue) == len(attendus) and {m.id for m in vue} == set(attendus)
    for m in vue:
        nom, sorte, suzerain, point = attendus[m.id]
        xy = (point["x_m"], point["y_m"]) if sorte == "seigneurie" else projeter_epsg3035(point["lat"], point["lon"])
        cellules = [cid for cid, c in carte.items() if point_dans_geometrie(*xy, c["geometry"])]
        cid = min(cellules) if cellules else None
        assert (m.nom, m.sorte, m.suzerain, m.siege, m.cell_id, m.rang, m.hors_carte) == (
            nom, sorte, suzerain, point["nom"], cid, 0 if cid is not None else None, point.get("hors_carte"))
        assert cid is not None or m.hors_carte.strip()

def test_registre_chargement(registre):
    monde, documents, charger, _ = registre
    vue = charger()
    _preuve_registre(vue, documents, monde.carte)
    paleologue = [m for m in vue if m.nom == "Paléologue"]
    assert {m.siege for m in paleologue} == {"Constantinople", "Mistra"}
    lignes = [next(m for m in vue if m.sorte == sorte) for sorte in ("grande maison", "institution", "seigneurie")]
    for ligne in lignes + [paleologue[-1]]:
        with pytest.raises(AssertionError):
            _preuve_registre(tuple(m for m in vue if m.id != ligne.id), documents, monde.carte)
    for document, champs in zip(documents, (("maisons", "puissances", "ancres"), ("capitales",), ("seigneuries",))):
        for champ in champs:
            original = document[champ]
            for valeur in (None, []):
                document.pop(champ) if valeur is None else document.update({champ: valeur})
                with pytest.raises(PuissanceInvalide):
                    charger()
                document[champ] = original

def test_registre_pyramide(registre):
    monde, documents, charger, valider = registre
    vue = charger()
    _preuve_registre(vue, documents, monde.carte)
    par_id = {m.id: m for m in vue}
    for m in vue:
        chemin = set()
        while m.suzerain is not None:
            assert m.id not in chemin
            chemin.add(m.id)
            m = par_id[m.suzerain]
    depart = documents[-1]["seigneuries"][0]
    institution = next(m for m in vue if m.sorte == "institution")
    depart["suzerain"] = int(institution.id.split("-")[-1])
    _preuve_registre(charger(), documents, monde.carte)
    depart["suzerain"] = max(p["id"] for p in documents[0]["puissances"]) + 1
    with pytest.raises(PuissanceInvalide, match=f"seigneurie {depart['id']}.*suzerain"):
        charger()
    a, b = vue[:2]
    for changements in ({a.id: "inconnue"}, {a.id: a.id}, {a.id: b.id, b.id: a.id}):
        alteree = tuple(dataclasses.replace(m, suzerain=changements[m.id]) if m.id in changements else m for m in vue)
        with pytest.raises(PuissanceInvalide, match=a.id):
            valider(alteree)
    depart["suzerain"] = int(institution.id.split("-")[-1])
    mauvaise = tuple(dataclasses.replace(m, suzerain=a.id) if m.id == f"seigneurie-{depart['id']}" else m for m in charger())
    valider(mauvaise)
    with pytest.raises(AssertionError):
        _preuve_registre(mauvaise, documents, monde.carte)

def test_registre_sieges(registre):
    monde, documents, charger, _ = registre
    vue, originaux = charger(), copy.deepcopy(documents)
    _preuve_registre(vue, documents, monde.carte)
    assert next(m.cell_id for m in vue if m.nom == "Valois") == 10322
    capitale = next(c for c in documents[1]["capitales"] if c["nom"] == "Paris")
    capitale.update(lat=documents[1]["capitales"][0]["lat"], lon=documents[1]["capitales"][0]["lon"])
    with pytest.raises(AssertionError):
        _preuve_registre(charger(), originaux, monde.carte)
    ancre = next(a for a in documents[0]["ancres"] if a["nom"] == "Arezzo")
    cellule = cellule_de_capitale(dataclasses.replace(charger_capitales()[0], lat=ancre["lat"], lon=ancre["lon"]), monde.carte)
    fausse = tuple(dataclasses.replace(m, siege=ancre["nom"], cell_id=cellule) if m.nom == "Florence" else m for m in vue)
    with pytest.raises(AssertionError):
        _preuve_registre(fausse, originaux, monde.carte)
    x, y = projeter_epsg3035(capitale["lat"], capitale["lon"])
    def carre(gauche, droite, bas, haut):
        return {"geometry": {"type": "Polygon", "coordinates": [[[gauche, bas], [droite, bas], [droite, haut], [gauche, haut], [gauche, bas]]]}}
    synthese = {20: carre(x, x + 100, y - 50, y + 50), 10: carre(x - 2, x, y - 1, y + 1)}
    # Toutes les sources sont au même point ; aucune exception hors carte ne subsiste.
    for lignes in (documents[0]["ancres"], documents[1]["capitales"], [s["siege"] for s in documents[2]["seigneuries"]]):
        for p in lignes:
            p.update(lat=capitale["lat"], lon=capitale["lon"], x_m=x, y_m=y)
            p.pop("hors_carte", None)
    for ordre in (synthese, dict(reversed(list(synthese.items())))):
        monde.carte = ordre
        assert {m.cell_id for m in charger()} == {10}
    monde.carte[10] = carre(x - 3, x - 1, y - 1, y + 1)
    assert {m.cell_id for m in charger()} == {20}
    with pytest.raises(AssertionError):
        _preuve_registre(tuple(dataclasses.replace(m, cell_id=10) for m in charger()), documents, monde.carte)

def test_registre_hors_carte(registre):
    monde, documents, charger, _ = registre
    vue = charger()
    _preuve_registre(vue, documents, monde.carte)
    assert {m.siege for m in vue if m.cell_id is None} == {"Saraï", "Venise"}
    for lignes in (documents[0]["ancres"], documents[1]["capitales"]):
        for p in (p for p in lignes if "hors_carte" in p):
            raison = p["hors_carte"]
            for valeur in (None, "  "):
                p.pop("hors_carte") if valeur is None else p.update(hors_carte=valeur)
                with pytest.raises(PuissanceInvalide, match="hors_carte"):
                    charger()
            p["hors_carte"] = raison
    next(c for c in documents[1]["capitales"] if c["nom"] == "Paris")["hors_carte"] = "Fausse raison"
    with pytest.raises(PuissanceInvalide, match="hors_carte"):
        charger()
    cid = max(monde.carte)
    monde.carte[cid].pop("geometry")
    with pytest.raises(PuissanceInvalide, match=f"cellule {cid}.*géométrie absente"):
        charger()

def test_registre_pure(registre):
    monde, documents, charger, _ = registre
    avant = copy.deepcopy((documents, monde.to_dict(), monde.carte, [vars(c) for c in monde.cells.values()]))
    vue = charger()
    assert isinstance(vue, tuple) and all(isinstance(m, _NoBadSpatialField) for m in vue)
    assert vue == charger()
    assert (documents, monde.to_dict(), monde.carte, [vars(c) for c in monde.cells.values()]) == avant
    with pytest.raises(dataclasses.FrozenInstanceError):
        vue[0].nom = "Altérée"
    with pytest.raises(AssertionError):
        assert vue == (dataclasses.replace(vue[0], nom="Altérée"),) + vue[1:]
    for document in documents:
        for lignes in (v for v in document.values() if isinstance(v, list)):
            lignes.reverse()
    monde.carte = dict(reversed(list(monde.carte.items())))
    assert vue == charger()
    for s in documents[-1]["seigneuries"]:
        monde.maison_du_joueur = f"seigneurie-{s['id']}"
        assert vue == charger()
    alteree = copy.deepcopy(documents)
    alteree[0]["maisons"][0]["nom"] = "Altérée"
    documents[:] = alteree
    with pytest.raises(AssertionError):
        assert vue == charger()


def _octets_registre(document):
    return json.dumps(document, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode()


def _preuve_registre_charge(monde, documents):
    historiques = tuple(m for m in monde.maisons if m.sorte != "plausible")
    _preuve_registre(historiques, documents, monde.carte)
    copie = copy.copy(monde)
    copie.maisons = historiques
    attendus, plausibles = _attente_maitres(copie, puissances_depuis_monde(monde), charger_maisons())
    assert plausibles and isinstance(monde.maisons, tuple)
    assert monde.maisons == tuple(sorted(historiques + plausibles, key=lambda m: m.id))
    assert len({m.id for m in monde.maisons}) == len(monde.maisons)
    assert {(cid, l.rang): l.maitre for cid, c in monde.cells.items() for l in c.lieux} == attendus

def test_registre_world(registre, monkeypatch):
    monde, documents, charger, _ = registre
    attendu = charger()
    _preuve_registre(attendu, documents, monde.carte)
    categories = {m.sorte for m in attendu}
    assert categories == {"grande maison", "institution", "seigneurie"}
    homonymes = {nom for nom, n in Counter(m.nom for m in attendu).items() if n > 1}
    assert homonymes
    appels = []
    def lecteur(carte):
        appels.append(carte)
        return charger_registre_maisons(carte)
    monkeypatch.setattr(etat_monde, "charger_registre_maisons", lecteur)
    from sim import maitres
    attribution, attributions = maitres.attribuer_maitres, []
    def attribuer(monde):
        assert monde.maisons == attendu and all(c.lieux for c in monde.cells.values())
        assert appels == [monde.carte]
        attributions.append(monde)
        return attribution(monde)
    monkeypatch.setattr(maitres, "attribuer_maitres", attribuer)
    charge = World.charger(0)
    _preuve_registre_charge(charge, documents)
    assert attributions == [charge]
    assert appels == [charge.carte]
    for maison in charge.maisons:
        with pytest.raises(dataclasses.FrozenInstanceError):
            maison.nom = "Altérée"
    assert World({}, []).maisons == ()
    charge.to_dict()
    maisons_depuis_monde(charge)
    maisons_de_l_ia(charge)
    assert appels == [charge.carte]
    assert attributions == [charge]
    monkeypatch.setattr(maitres, "attribuer_maitres", attribution)
    retraits = [next(m for m in attendu if m.sorte == sorte) for sorte in categories]
    retraits += [m for m in attendu if m.nom in homonymes]
    faux = [tuple(m for m in attendu if m.id != retiree.id) for retiree in retraits]
    faux += [(), (dataclasses.replace(attendu[0], nom="Altérée"),) + attendu[1:]]
    monkeypatch.setattr(etat_monde, 'construire_personnages', lambda monde: ((), {}))
    for resultat in faux:
        monkeypatch.setattr(etat_monde, "charger_registre_maisons", lambda carte: resultat)
        with pytest.raises(AssertionError):
            _preuve_registre_charge(World.charger(0), documents)
    p = next(m for m in charge.maisons if m.sorte == "plausible")
    for fiches in (tuple(m for m in charge.maisons if m != p), charge.maisons + (p,),
                   charge.maisons + (dataclasses.replace(p, id="plausible-ajouté"),),
                   tuple(dataclasses.replace(m, nom="Altérée") if m == p else m for m in charge.maisons)):
        copie = copy.copy(charge)
        copie.maisons = fiches
        with pytest.raises(AssertionError): _preuve_registre_charge(copie, documents)
    for valeur in (None, "inconnu"):
        copie = copy.deepcopy(charge)
        copie.cells[next(iter(charge.cells))].lieux[0].maitre = valeur
        with pytest.raises(AssertionError): _preuve_registre_charge(copie, documents)
    def refuser(carte):
        raise PuissanceInvalide("registre indisponible")
    monkeypatch.setattr(etat_monde, "charger_registre_maisons", refuser)
    with pytest.raises(PuissanceInvalide, match="registre indisponible"):
        World.charger(0)
    assert World({}, []).maisons == ()  # Aucun chargement sur les mondes d'épreuve.


def test_registre_serialisation(monkeypatch):
    import hashlib
    import sim.maisons as vues_maisons
    import sim.capitales as vues_capitales
    import sim.registre_maisons as lecteur
    import sim.maitres as attribution
    monde = World.charger(0)
    registre = monde.maisons
    assert registre
    attendu = [dataclasses.asdict(m) for m in sorted(registre, key=lambda m: m.id)]
    champs = {"id", "nom", "sorte", "suzerain", "siege", "cell_id", "rang", "hors_carte"}
    assert all(set(m) == champs for m in attendu)
    def interdit(*args, **kwargs):
        raise AssertionError("lecture après chargement")
    for module, nom in ((etat_monde, "charger_registre_maisons"),
                        (lecteur, "charger_registre_maisons"),
                        (attribution, "attribuer_maitres"),
                        (vues_maisons, "maisons_depuis_monde"),
                        (vues_capitales, "maisons_de_l_ia")):
        monkeypatch.setattr(module, nom, interdit)
    document = monde.to_dict()
    def verifier(doc):
        assert doc.get("maisons") == attendu
    verifier(document)
    assert World({}, []).to_dict()["maisons"] == []
    original = _octets_registre(document)
    monde.maisons = tuple(reversed(registre))
    assert _octets_registre(monde.to_dict()) == original
    assert monde.maisons == tuple(reversed(registre))
    sans = {k: v for k, v in document.items() if k != "maisons"}
    assert hashlib.sha256(original).digest() != hashlib.sha256(_octets_registre(sans)).digest()
    faux = [sans, {**document, "maisons": attendu[1:]},
            {**document, "maisons": list(reversed(attendu))}]
    for champ in champs:
        copie = copy.deepcopy(document)
        copie["maisons"][0][champ] = "Altéré"
        faux.append(copie)
    for copie in faux:
        with pytest.raises(AssertionError):
            verifier(copie)
    document["maisons"][0]["nom"] = "Altérée"
    assert _octets_registre(monde.to_dict()) == original
    monde.maisons = (dataclasses.replace(registre[0], nom="Altérée"),) + registre[1:]
    alteres = _octets_registre(monde.to_dict())
    assert alteres != original
    assert hashlib.sha256(alteres).digest() != hashlib.sha256(original).digest()


def _tick_sans_lecture_registre(monkeypatch, monde, tick, numero):
    assert monde.maisons
    acces = []
    original = World.__getattribute__
    def intercepter(self, nom):
        if nom == "maisons":
            acces.append(nom)
            raise RuntimeError("registre consulté au tick")
        return original(self, nom)
    with monkeypatch.context() as garde:
        garde.setattr(World, "__getattribute__", intercepter)
        tick(monde, random.Random(numero), numero)
    assert acces == []


IDENTIFIANTS_SEIGNEURIE_MAL_FORMES = (
    True, None, "grande-3", "seigneurie-03", "seigneurie-", " seigneurie-3",
    "seigneurie-3 ", "seigneurie-+3", "seigneurie--3", "seigneurie-3\n", "seigneurie-٣",
)


def test_registre_identifiant(monkeypatch):
    from sim import seigneuries
    terres = charger_seigneuries()
    assert terres, "échantillon vide"
    attendus = {seigneuries.identifiant_de_seigneurie(s.id) for s in terres}
    assert attendus == {m.id for m in World.charger(0).maisons if m.sorte == "seigneurie"}
    for terre in terres:
        identifiant = seigneuries.identifiant_de_seigneurie(terre.id)
        assert identifiant == f"seigneurie-{terre.id}"
        assert seigneuries.numero_de_seigneurie(identifiant) == terre.id
    def refuser(valeur):
        with pytest.raises(seigneuries.SeigneurieInconnue) as erreur:
            seigneuries.numero_de_seigneurie(valeur)
        assert str(erreur.value) == f"seigneurie inconnue : {valeur!r}"
    for valeur in (terres[0].id, *IDENTIFIANTS_SEIGNEURIE_MAL_FORMES):
        refuser(valeur)
    monkeypatch.setattr(seigneuries, "numero_de_seigneurie", lambda valeur: int(valeur.removeprefix("seigneurie-")))
    with pytest.raises(pytest.fail.Exception):
        refuser("seigneurie-03")


def test_registre_choix(carte, monkeypatch):
    from sim.intentions import ChoixDepart, deposer_intention
    monde = copy.deepcopy(carte[0])
    terres = charger_seigneuries()
    assert terres, "échantillon vide"
    terre = terres[0]
    registre = monde.maisons
    deposer_intention(monde, {"seigneurie": terre.id})
    impur = copy.deepcopy(monde)
    _tick_sans_lecture_registre(monkeypatch, monde, engine.tick, monde.ticks_ecoules)
    assert monde.maison_du_joueur == f"seigneurie-{terre.id}"
    assert any(m.id == monde.maison_du_joueur and m.sorte == "seigneurie" for m in registre)
    original = ChoixDepart.appliquer
    def lire(choix, monde):
        getattr(monde, "maisons")
        original(choix, monde)
    monkeypatch.setattr(ChoixDepart, "appliquer", lire)
    with pytest.raises(RuntimeError, match="registre consulté au tick"):
        _tick_sans_lecture_registre(monkeypatch, impur, engine.tick, impur.ticks_ecoules)


def test_registre_tick(carte, monkeypatch):
    monde = carte[0]
    for numero in range(3):
        _tick_sans_lecture_registre(monkeypatch, monde, engine.tick, numero)
    def impur(monde, rng, numero):
        getattr(monde, "maisons")  # Lecture sans effet, avant le véritable tick.
        return engine.tick(monde, rng, numero)
    with pytest.raises(RuntimeError, match="registre consulté au tick"):
        _tick_sans_lecture_registre(monkeypatch, monde, impur, monde.ticks_ecoules)


def test_registre_vue_impure(carte, monkeypatch):
    original = maisons_depuis_monde
    def impure(monde, *args, **kwargs):
        vue = original(monde, *args, **kwargs)
        monde.maisons = (dataclasses.replace(monde.maisons[0], nom="Altérée"),) + monde.maisons[1:]
        return vue
    monkeypatch.setattr(sys.modules[__name__], "maisons_depuis_monde", impure)
    with pytest.raises(AssertionError):
        test_pure(carte)


def _controler_grenier_etat(monde, raisons):
    assert monde.maisons and monde.greniers
    ids = [m.id for m in monde.maisons]
    assert len(ids) == len(set(ids)) == len(monde.greniers) and set(monde.greniers) == set(ids)
    assert {m.sorte for m in monde.maisons} >= {"grande maison", "institution", "seigneurie"}
    homonymes = [n for n, k in Counter(m.nom for m in monde.maisons).items() if k > 1]
    assert homonymes and any(raisons.values())
    for nom in homonymes:
        freres = [m.id for m in monde.maisons if m.nom == nom]
        assert len(freres) > 1
        assert all(monde.greniers[a] is not monde.greniers[b] for a, b in zip(freres, freres[1:]))
    assert len({id(p) for p in monde.greniers.values()}) == len(monde.greniers)
    assert {m.id: m.hors_carte for m in monde.maisons} == raisons
    sans = World({}, [])
    assert sans.maisons == () and sans.greniers == {} and sans.pertes_kg == 0.0


def test_grenier_etat():
    """Un panier vide et distinct par maison ; le remplir ne touche pas le siège."""
    import sim.constants as constantes
    from sim.model import copier_panier
    monde = World.charger(0)
    raisons = {m.id: m.hors_carte for m in monde.maisons}
    assert all(p == {} for p in monde.greniers.values())
    _controler_grenier_etat(monde, raisons)
    siege = next(m for m in monde.maisons if m.cell_id in monde.cells)
    cellule = monde.cells[siege.cell_id]
    avant = (copier_panier(cellule), [copier_panier(l) for l in cellule.lieux])
    assert avant[0]
    autres = {i: dict(p) for i, p in monde.greniers.items() if i != siege.id}
    monde.greniers[siege.id][constantes.MARCHANDISE_NOURRITURE] = 1000.0
    assert {i: dict(p) for i, p in monde.greniers.items() if i != siege.id} == autres
    assert (copier_panier(cellule), [copier_panier(l) for l in cellule.lieux]) == avant
    assert {m.id: m.hors_carte for m in monde.maisons} == raisons
    nom = next(n for n, k in Counter(m.nom for m in monde.maisons).items() if k > 1)
    freres = [m.id for m in monde.maisons if m.nom == nom]
    for geste in ("retirer", "fusionner", "partager"):
        sauve = {i: dict(p) for i, p in monde.greniers.items()}
        if geste == "retirer":
            monde.greniers.pop(freres[0])
        elif geste == "fusionner":
            del monde.greniers[freres[1]]
        else:
            monde.greniers[freres[1]] = monde.greniers[freres[0]]
        with pytest.raises(AssertionError):
            _controler_grenier_etat(monde, raisons)
        monde.greniers = {i: dict(p) for i, p in sauve.items()}
    print(f"maisons={len(monde.maisons)}, homonymes={len(freres)}")


_CHAMPS_FICHE = {"id", "nom", "sorte", "suzerain", "siege", "cell_id", "rang", "hors_carte"}


def _verifier_grenier_serialise(document, monde):
    fiches = [dataclasses.asdict(m) for m in sorted(monde.maisons, key=lambda m: m.id)]
    assert document["maisons"] == fiches and all(set(f) == _CHAMPS_FICHE for f in fiches)
    non_vides = {i: {n: p[n] for n in sorted(p)} for i, p in sorted(monde.greniers.items()) if p}
    if non_vides:
        assert document.get("greniers") == non_vides and all(document["greniers"].values())
    else:
        assert "greniers" not in document
    if monde.pertes_kg != 0.0:
        assert document.get("pertes_kg") == monde.pertes_kg
    else:
        assert "pertes_kg" not in document


def test_grenier_serialisation():
    """À vide, aucune clé nouvelle ; après perte, paniers pleins et cumul exact."""
    import random
    import sim.constants as constantes
    monde = World.charger(0)
    assert all(p == {} for p in monde.greniers.values()) and monde.pertes_kg == 0.0
    _verifier_grenier_serialise(monde.to_dict(), monde)
    assert set(monde.to_dict()) == {"cells", "plans", "ticks_ecoules", "maisons", "personnages", "chefs"}
    nourriture = constantes.MARCHANDISE_NOURRITURE
    choisis = [m for m in monde.maisons if m.cell_id in monde.cells][:2]
    assert len(choisis) == 2
    for rang, maison in enumerate(choisis, start=1):
        monde.greniers[maison.id][nourriture] = 1000.0 * rang + 0.5
    engine.tick(monde, random.Random(0), 0)
    assert monde.pertes_kg != 0.0
    document = monde.to_dict()
    _verifier_grenier_serialise(document, monde)
    assert set(document["greniers"]) == {m.id for m in choisis}
    octets = json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode()
    monde.greniers = {c: monde.greniers[c] for c in reversed(list(monde.greniers))}
    assert json.dumps(monde.to_dict(), ensure_ascii=False, separators=(",", ":")).encode() == octets
    rendu, identifiant = monde.to_dict(), choisis[0].id
    poids = monde.greniers[identifiant][nourriture]
    assert poids != round(poids)
    rendu["greniers"][identifiant][nourriture] = 0.0
    assert monde.greniers[identifiant][nourriture] == poids
    vide = next(c for c, p in monde.greniers.items() if not p)
    arrondi = copy.deepcopy(document)
    arrondi["greniers"][identifiant][nourriture] = round(poids)
    faux = (
        {**copy.deepcopy(document), "greniers": {k: v for k, v in document["greniers"].items() if k != identifiant}},
        arrondi,
        {**copy.deepcopy(document), "greniers": {**document["greniers"], vide: {}}},
        {k: v for k, v in document.items() if k != "pertes_kg"},
    )
    for altéré in faux:
        with pytest.raises(AssertionError):
            _verifier_grenier_serialise(altéré, monde)
    print(f"paniers_publies={len(document['greniers'])}, pertes_kg={monde.pertes_kg}")


# Attribution des maîtres : l'attente ne consulte jamais sim.maitres.
def _attente_maitres(monde, vue, maisons, depart=4, groupe=3, priorite=True):
    from sim.lieux import lieux_depuis_monde
    from sim.registre_maisons import MaisonDuMonde
    attendus, fiches = {}, []
    for cid, lieux in lieux_depuis_monde(monde).items():
        libres = []
        for lieu in lieux:
            departs = sorted((m.id for m in monde.maisons if m.cell_id == cid
                              and m.sorte == "seigneurie" and lieu.rang < depart))
            sieges = sorted(m.id for m in monde.maisons if m.cell_id == cid
                            and m.sorte in ("grande maison", "institution"))
            candidats = departs + sieges if priorite else sieges + departs
            if candidats:
                attendus[cid, lieu.rang] = candidats[0]
            else:
                libres.append(lieu.rang)
        puissance = vue[cid]
        racine = maisons.par_puissance[puissance] if puissance is not None else None
        suzerain = (f"grande-{racine}" if racine is not None else
                    f"institution-{puissance}" if puissance is not None else None)
        for debut in range(0, len(libres), groupe):
            rangs = libres[debut:debut + groupe]
            identifiant = f"plausible-{cid}-{rangs[0]}"
            fiches.append(MaisonDuMonde(identifiant, identifiant, "plausible", suzerain,
                                       identifiant, cid, rangs[0], None))
            attendus.update({(cid, rang): identifiant for rang in rangs})
    return dict(sorted(attendus.items())), tuple(fiches)


@pytest.fixture(scope="module")
def monde_maitres():
    monde = World.charger(0)
    monde.maisons = charger_registre_maisons(monde.carte)
    return monde, puissances_depuis_monde(monde), charger_maisons()


@pytest.fixture
def cas_maitres():
    import sim.constants as constantes
    from sim.model import Cell
    from sim.registre_maisons import MaisonDuMonde
    monde = World({cid: Cell(cell_id=cid, area_km2=n * constantes.SURFACE_KM2_PAR_LIEU,
                            population=0) for cid, n in ((5, 7), (4, 7), (3, 7), (2, 7), (1, 2))}, [])
    monde.maisons = (
        MaisonDuMonde("seigneurie-a", "A", "seigneurie", "grande-3", "A", 1, 0, None),
        MaisonDuMonde("seigneurie-b", "B", "seigneurie", "grande-3", "B", 2, 0, None),
        MaisonDuMonde("grande-3", "G", "grande maison", None, "G", 2, 0, None),
        MaisonDuMonde("institution-11", "I", "institution", None, "I", None, None, "hors carte"),
    )
    return monde, {1: 3, 2: 3, 3: 3, 4: 11, 5: None}, charger_maisons()


def test_maitre_monde(monde_maitres):
    from sim.maitres import attribuer_maitres, valider_attribution
    from sim.lieux import lieux_depuis_monde
    from sim.registre_maisons import valider_registre_maisons
    monde, vue, maisons = monde_maitres
    maitres, plausibles = attribuer_maitres(monde)
    assert (maitres, plausibles) == _attente_maitres(*monde_maitres)
    couples = [(cid, l.rang) for cid, lieux in lieux_depuis_monde(monde).items() for l in lieux]
    assert couples and list(maitres) == couples
    registre = monde.maisons + plausibles
    assert len({m.id for m in registre}) == len(registre)
    assert set(maitres.values()) <= {m.id for m in registre}
    effectifs = Counter(maitres.values())
    assert sum(effectifs.values()) == len(couples) == sum(len(c.lieux) for c in monde.cells.values())
    for m in monde.maisons:
        if m.cell_id is not None:
            assert maitres[m.cell_id, 0] == m.id
            if m.sorte == "seigneurie":
                assert all(maitres[cid, rang] == m.id for cid, rang in couples
                           if cid == m.cell_id and rang < 4)
        else:
            assert m.id not in effectifs
    assert plausibles and all(cid == m.cell_id for m in plausibles
                             for (cid, rang), maitre in maitres.items() if maitre == m.id)
    assert any(m.suzerain and m.suzerain.startswith("grande-") for m in plausibles)
    assert any(m.suzerain and m.suzerain.startswith("institution-") for m in plausibles)
    assert any(m.suzerain is None for m in plausibles)
    assert any(effectifs[m.id] < 3 for m in plausibles)
    assert any(len(lieux) < 4 for lieux in lieux_depuis_monde(monde).values())
    tenantes = maisons_depuis_monde(monde)
    assert any(m.suzerain != f"grande-{tenantes[m.cell_id]}" for m in plausibles
               if vue[m.cell_id] is not None and maisons.par_puissance[vue[m.cell_id]] is not None)
    valider_attribution(monde, maitres, plausibles)
    valider_registre_maisons(registre)


def test_maitre_cas(cas_maitres):
    from sim.maitres import attribuer_maitres, valider_attribution
    monde, vue, maisons = cas_maitres
    attendu = _attente_maitres(*cas_maitres)
    assert attendu != _attente_maitres(*cas_maitres, priorite=False)
    for registre in (monde.maisons, tuple(reversed(monde.maisons))):
        monde.maisons = registre
        maitres, plausibles = attribuer_maitres(*cas_maitres)
        assert (maitres, plausibles) == attendu
        assert [maitres[1, r] for r in range(2)] == ["seigneurie-a"] * 2
        assert [maitres[2, r] for r in range(7)] == ["seigneurie-b"] * 4 + ["grande-3"] * 3
        for cid, suzerain in ((3, "grande-3"), (4, "institution-11"), (5, None)):
            groupes = [m for m in plausibles if m.cell_id == cid]
            assert [m.rang for m in groupes] == [0, 3, 6]
            assert [Counter(maitres.values())[m.id] for m in groupes] == [3, 3, 1]
            assert all(m.suzerain == suzerain for m in groupes)
        valider_attribution(monde, maitres, plausibles, vue, maisons)


@pytest.mark.parametrize("nom,valeur", [("LIEUX_DE_LA_SEIGNEURIE", 2),
                                        ("LIEUX_PAR_SEIGNEUR_PLAUSIBLE", 5)])
def test_maitre_constantes(cas_maitres, monkeypatch, nom, valeur):
    import sim.constants as constantes
    from sim.maitres import AttributionInvalide, attribuer_maitres
    nominal = attribuer_maitres(*cas_maitres)
    monkeypatch.setattr(constantes, nom, valeur)
    attendu = _attente_maitres(*cas_maitres, depart=constantes.LIEUX_DE_LA_SEIGNEURIE,
                              groupe=constantes.LIEUX_PAR_SEIGNEUR_PLAUSIBLE)
    assert attribuer_maitres(*cas_maitres) == attendu != nominal
    for invalide in (True, 0, 2.5):
        monkeypatch.setattr(constantes, nom, invalide)
        with pytest.raises(AttributionInvalide, match=nom):
            attribuer_maitres(*cas_maitres)


def test_maitre_contre_epreuves(monde_maitres):
    from sim.maitres import AttributionInvalide, attribuer_maitres, valider_attribution
    from sim.registre_maisons import valider_registre_maisons
    monde, vue, maisons = monde_maitres
    maitres, plausibles = attribuer_maitres(monde, vue, maisons)
    premier = next(iter(maitres))
    p = plausibles[0]
    siege = (p.cell_id, p.rang)
    depart = next(m for m in monde.maisons if m.sorte == "seigneurie")
    bourg = (depart.cell_id, 0)
    capitale = next(c for c, m in maitres.items() if m.startswith("grande-") and c[1] > 0)
    a, b = next((a, b) for a, b in zip(plausibles, plausibles[1:]) if a.cell_id == b.cell_id)
    autre = next(m for m in plausibles if m.cell_id != p.cell_id)
    cas = [
        ({c: m for c, m in maitres.items() if c != premier}, plausibles, premier),
        ({**maitres, premier: "inconnu"}, plausibles, premier),
        (maitres, plausibles[1:], siege),
        (maitres, plausibles + (p,), siege),
        ({**maitres, bourg: p.id}, plausibles, bourg),
        ({**maitres, capitale: p.id}, plausibles, capitale),
        ({c: a.id if m == b.id else m for c, m in maitres.items()},
         tuple(m for m in plausibles if m.id != b.id), (b.cell_id, b.rang)),
        ({**maitres, siege: autre.id}, plausibles, siege),
        ({}, plausibles, premier),
        ({**maitres, (max(monde.cells) + 1, 0): p.id}, plausibles, (max(monde.cells) + 1, 0)),
    ]
    for alteres, fiches, couple in cas:
        with pytest.raises(AttributionInvalide) as erreur:
            valider_attribution(monde, alteres, fiches, vue, maisons)
        assert str(couple) in str(erreur.value)
        if not alteres:
            assert "échantillon vide" in str(erreur.value)
    # Toute composante de la fiche est vérifiée, même lorsque les maîtres sont corrects.
    for champ, valeur in (("nom", "altéré"), ("siege", "altéré"), ("sorte", "institution"),
                          ("suzerain", "inconnu"), ("hors_carte", "altéré")):
        with pytest.raises(AttributionInvalide) as erreur:
            valider_attribution(monde, maitres, (dataclasses.replace(p, **{champ: valeur}),)
                               + plausibles[1:], vue, maisons)
        assert str(siege) in str(erreur.value)
    for fiches in ((dataclasses.replace(p, suzerain="inconnu"),) + plausibles[1:],
                   (dataclasses.replace(p, suzerain=plausibles[1].id),
                    dataclasses.replace(plausibles[1], suzerain=p.id)) + plausibles[2:]):
        with pytest.raises(PuissanceInvalide, match=p.id):
            valider_registre_maisons(monde.maisons + fiches)
    valider_attribution(monde, maitres, plausibles, vue, maisons)
    vide = World({}, [])
    with pytest.raises(AttributionInvalide, match="échantillon vide.*\\(None, None\\)"):
        valider_attribution(vide, {}, (), {}, maisons)


def _importe_maitres(texte, chargement=False):
    arbre = ast.parse(texte)
    if chargement:
        for fonction in (f for c in arbre.body if isinstance(c, ast.ClassDef) and c.name == "World"
                         for f in c.body if isinstance(f, ast.FunctionDef) and f.name == "charger"):
            fonction.body = []
    return any((isinstance(n, ast.Call) and
                (isinstance(n.func, ast.Name) and n.func.id == "attribuer_maitres" or
                 isinstance(n.func, ast.Attribute) and n.func.attr == "attribuer_maitres"))
               or (isinstance(n, ast.ImportFrom) and
                (n.module == "sim.maitres" or n.module == "sim" and any(a.name == "maitres" for a in n.names)))
               or (isinstance(n, ast.Import) and any(a.name == "sim.maitres" for a in n.names))
               for n in ast.walk(arbre))


def test_maitre_pur(monde_maitres):
    from sim.maitres import attribuer_maitres
    monde, vue, maisons = monde_maitres
    avant = copy.deepcopy((json.dumps(monde.to_dict(), sort_keys=True), monde.maisons,
                           monde.carte, [vars(c) for c in monde.cells.values()]))
    premier = attribuer_maitres(monde, vue, maisons)
    second = attribuer_maitres(monde, vue, maisons)
    assert premier == second and premier[0] is not second[0]
    assert (json.dumps(monde.to_dict(), sort_keys=True), monde.maisons,
            monde.carte, [vars(c) for c in monde.cells.values()]) == avant
    assert premier[1]
    with pytest.raises(dataclasses.FrozenInstanceError):
        premier[1][0].nom = "altéré"
    for fichier in ("engine.py", "world.py", "snapshot_export.py", "service.py"):
        assert not _importe_maitres((TABLE.parents[1] / "sim" / fichier).read_text(), fichier == "world.py")
    assert _importe_maitres("from sim.maitres import attribuer_maitres")

def test_maitre_permutations(monde_maitres, monkeypatch):
    from sim.maitres import attribuer_maitres
    monde, vue, maisons = monde_maitres
    attendu = attribuer_maitres(monde, vue, maisons)
    assert attendu[0] and attendu[1]
    for cellules, fiches in ((True, False), (False, True), (True, True)):
        copie = copy.copy(monde)
        copie.cells = dict(reversed(list(monde.cells.items()))) if cellules else monde.cells
        copie.maisons = tuple(reversed(monde.maisons)) if fiches else monde.maisons
        assert attribuer_maitres(copie, vue, maisons) == attendu
        if cellules:
            couples = [(cid, l.rang) for cid, c in copie.cells.items() for l in c.lieux]
            faux = (dict(zip(couples, attendu[0].values())), attendu[1])
            with pytest.raises(AssertionError): assert faux == attendu
        document = World.lire_carte()
        if cellules: document["cellules"].reverse()
        with monkeypatch.context() as garde:
            if fiches: garde.setattr(etat_monde, "charger_registre_maisons", lambda carte: tuple(reversed(charger_registre_maisons(carte))))
            charge = World.charger(0, document)
        assert {(cid, l.rang): l.maitre for cid, c in charge.cells.items() for l in c.lieux} == attendu[0]
        assert charge.maisons == tuple(sorted(monde.maisons + attendu[1], key=lambda m: m.id))
    with pytest.raises(AssertionError): assert attribuer_maitres(World({}, []), {}, maisons)[0]
    assert _importe_maitres("class World:\n def to_dict(self):\n  from sim.maitres import attribuer_maitres", True)
    assert _importe_maitres("class World:\n def to_dict(self):\n  attribuer_maitres(self)", True)


def test_noms_maisons():
    from sim.noms import charger_noms, noms_depuis_monde, aire_de_cellule
    from sim.puissances import charger_table, puissances_depuis_monde
    monde = World.charger(0); vue = noms_depuis_monde(monde); listes = charger_noms(); table = charger_table(); puissances = puissances_depuis_monde(monde); registre = {m.id: m for m in monde.maisons}; assert registre and vue
    def verifier(v):
        for cid, c in monde.cells.items():
            fiches = v[cid]['maisons']; aire = listes['aires'][aire_de_cellule(cid, monde.carte[cid], puissances[cid], table, listes)]; assert set(fiches) == {l.maitre for l in c.lieux if l.maitre is not None}
            plausibles = [f for i, f in fiches.items() if registre[i].sorte == 'plausible']; assert len({f['nom'] for f in plausibles}) == len(plausibles)
            for i, fiche in fiches.items():
                m = registre[i]; assert fiche == vue[cid]['maisons'][i]
                if m.sorte == 'plausible': assert fiche == {'nom': aire['maisons'][(cid + m.rang) % len(aire['maisons'])], 'prenom_chef': aire['prenoms'][(cid + m.rang) % len(aire['prenoms'])]}
                else: assert fiche == {'nom': m.nom, 'prenom_chef': None}
    verifier(vue); cid = next(c for c, bloc in vue.items() if len(bloc['maisons']) > 1); a, b = list(vue[cid]['maisons'])[:2]; m = next(m for m in monde.maisons if m.sorte == 'seigneurie')
    for c, fiches in ((cid, {**vue[cid]['maisons'], a: vue[cid]['maisons'][b]}), (cid, {**vue[cid]['maisons'], a: {**vue[cid]['maisons'][a], 'prenom_chef': 'Autre'}}), (m.cell_id, {**vue[m.cell_id]['maisons'], m.id: {'nom': 'Autre', 'prenom_chef': None}}), (cid, {i: f for i,f in vue[cid]['maisons'].items() if i != a})):
        faux = copy.deepcopy(vue); faux[c]['maisons'] = fiches
        with pytest.raises(AssertionError): verifier(faux)


def test_part_etat(monkeypatch):
    import sim.constants as k
    monde = World.charger(0); ids = {m.id for m in monde.maisons}
    assert ids and {m.sorte for m in monde.maisons} >= {"plausible", "institution", "seigneurie"}
    assert any(n > 1 for n in Counter(m.nom for m in monde.maisons).values())
    def verifier(document):
        assert set(monde.parts) == ids
        attendu = {i: p for i, p in sorted(monde.parts.items()) if p != k.PART_COUTUMIERE}
        assert document.get("parts", {}) == attendu and bool(attendu) == ("parts" in document)
    assert monde.parts == dict.fromkeys(ids, k.PART_COUTUMIERE) and World({}, []).parts == {}
    verifier(monde.to_dict())
    identifiant, autre = sorted(ids)[:2]
    valeur = monde.parts.pop(identifiant)
    with pytest.raises(AssertionError): verifier(monde.to_dict())
    monde.parts[identifiant] = valeur
    with pytest.raises(AssertionError): verifier(monde.to_dict() | {"parts": dict(monde.parts)})
    monde.parts[identifiant], monde.parts[autre] = 0, 0.12345678912345678
    document = monde.to_dict(); verifier(document)
    assert list(document["parts"]) == sorted(document["parts"])
    with pytest.raises(AssertionError): verifier(document | {"parts": {identifiant: 0, autre: 0.123}})
    monde.parts = dict(reversed(list(monde.parts.items())))
    assert monde.to_dict() == document
    document["parts"][autre] = 0
    assert monde.parts[autre] == 0.12345678912345678
    monde.parts[identifiant] = monde.parts[autre] = k.PART_COUTUMIERE
    verifier(monde.to_dict())
    monkeypatch.setattr(k, "PART_COUTUMIERE", 0.17)
    charge = World.charger(0)
    assert charge.parts == dict.fromkeys(ids, 0.17) and "parts" not in charge.to_dict()


PERSONNAGES = TABLE.with_name("personnages-1400.json")


def _personnages(chemin=PERSONNAGES):
    return json.loads(chemin.read_text(encoding="utf-8"))


def _personnages_couverture(document, references, vue):
    puissances, capitales, seigneuries = references
    categories = [{f"grande-{c['maison']}" for c in capitales["capitales"]},
                  {f"institution-{p['id']}" for p in puissances["puissances"] if "maison" not in p},
                  {f"seigneurie-{s['id']}" for s in seigneuries["seigneuries"]}]
    assert all(categories)
    attendus = set.union(*categories)
    lignes = [c["maison"] for c in document["chefs"]]
    assert lignes and lignes == sorted(set(lignes))
    assert set(lignes) == attendus == {m.id for m in vue}
    hors_carte = {m.id for m in vue if m.cell_id is None}
    assert hors_carte and hors_carte <= set(lignes)
    assert {m.id for m in vue if m.nom == "Paléologue"} == {"grande-15", "seigneurie-3"}


def test_personnages_couverture(registre, tmp_path):
    _, references, charger, _ = registre
    vue, document = charger(), _personnages()
    _personnages_couverture(document, references, vue)
    with pytest.raises(FileNotFoundError):
        _personnages(tmp_path / "absent.json")
    retraits = [next(m.id for m in vue if m.sorte == s) for s in
                ("grande maison", "institution", "seigneurie")]
    retraits += [m.id for m in vue if m.cell_id is None] + ["seigneurie-3"]
    listes = [[], document["chefs"] * 2, list(reversed(document["chefs"]))]
    listes += [[c for c in document["chefs"] if c["maison"] != i] for i in retraits]
    for inconnu in ("inconnue-1", "plausible-1"):
        copie = copy.deepcopy(document["chefs"])
        copie[0]["maison"] = inconnu
        listes.append(sorted(copie, key=lambda c: c["maison"]))
    for lignes in listes:
        with pytest.raises(AssertionError):
            _personnages_couverture({"chefs": lignes}, references, vue)
    reference_augmente = copy.deepcopy(references)
    reference_augmente[1]["capitales"].append({"maison": 999})
    with pytest.raises(AssertionError):
        _personnages_couverture(document, reference_augmente, vue)


def _personnages_sources(document):
    import datetime
    import re
    from urllib.parse import urlsplit
    def texte(valeur):
        assert isinstance(valeur, str) and valeur.strip()
    assert set(document) == {"date", "fidelite", "chefs", "familles", "liens", "etats"}
    assert document["date"] == "1400-01-01"
    texte(document["fidelite"])
    assert isinstance(document["chefs"], list) and document["chefs"]
    for table in ('familles', 'liens'): assert isinstance(document[table], list) and document[table]
    for table, fiche in ((t, f) for t in ('chefs', 'familles', 'liens') for f in document[t]):
        familial, ajout = table != 'chefs', table != 'liens'
        champs = ({'identite', 'naissance'} if ajout else set()) | ({'pere', 'mere', 'conjoints', 'presence'} if familial else set())
        assert set(fiche) == {'sources', 'lacunes'} | ({'maison', 'nom', 'naissance'} if ajout else set()) | ({'id', 'pere', 'mere', 'conjoints', 'presence'} if familial else set())
        if ajout: texte(fiche['maison'])
        assert set(fiche["sources"]) == set(fiche["lacunes"]) == champs
        if ajout: assert fiche['nom'] is not None or fiche['naissance'] is None
        for champ in champs:
            donnee = fiche['nom'] if champ == 'identite' else None if champ == 'presence' and fiche[champ] == 'indeterminee' else fiche[champ]
            if donnee == []: donnee = None
            source, lacune = fiche["sources"][champ], fiche["lacunes"][champ]
            if donnee is None:
                assert source is None
                texte(lacune)
                continue
            assert lacune is None and isinstance(source, dict) and set(source) == {"url", "fait"}
            texte(source["fait"])
            texte(source["url"])
            url = urlsplit(source["url"])
            assert url.scheme in {"http", "https"} and url.hostname and not re.search(r"\s", source["url"])
            if champ != 'naissance':
                if champ == 'identite': texte(donnee)
                continue
            assert isinstance(donnee, dict) and set(donnee) == {"valeur", "precision"}
            valeur, precision = donnee["valeur"], donnee["precision"]
            texte(valeur)
            assert precision in {"jour", "mois", "annee", "vers", "intervalle"}
            if precision in {"jour", "mois", "annee"}:
                suffixe = {"jour": "", "mois": "-01", "annee": "-01-01"}[precision]
                motif = {"jour": r"[0-9]{4}-[0-9]{2}-[0-9]{2}", "mois": r"[0-9]{4}-[0-9]{2}", "annee": r"[0-9]{4}"}[precision]
                assert re.fullmatch(motif, valeur)
                assert datetime.date.fromisoformat(valeur + suffixe) <= datetime.date(1400, 1, 1)


def _alterer_personnages(document, chemin, valeur):
    copie = copy.deepcopy(document)
    cible = copie
    for cle in chemin[:-1]:
        cible = cible[cle]
    if valeur == "SUPPRIMER":
        del cible[chemin[-1]]
    else:
        cible[chemin[-1]] = valeur
    return copie


def test_personnages_sources():
    document = _personnages()
    _personnages_sources(document)
    alterations = [(('date',), '1400-01-02'), (('fidelite',), ' '), (('chefs',), []),
                   (('chefs', 0, 'nom'), ' '), (('chefs', 0, 'maison'), 'SUPPRIMER'),
                   (('chefs', 0, 'sources', 'identite'), {}),
                   (('chefs', 0, 'sources', 'identite', 'fait'), ' '),
                   (('chefs', 0, 'sources', 'identite', 'url'), 'ftp://exemple.org'),
                   (('chefs', 0, 'sources', 'identite', 'url'), 'https:///absente'),
                   (('chefs', 0, 'sources', 'naissance'), None),
                   (('chefs', 0, 'sources', 'naissance'), 'SUPPRIMER'),
                   (('chefs', 0, 'nom'), None),
                   (('chefs', 0, 'lacunes', 'identite'), 'Motif indu pour une identité connue'),
                   (('chefs', 0, 'naissance', 'precision'), 'seconde'),
                   (('chefs', 0, 'naissance'), {'valeur': '1367-02-30', 'precision': 'jour'}),
                   (('chefs', 0, 'naissance'), {'valeur': '1400-01-02', 'precision': 'jour'}),
                   (('chefs', 0, 'naissance'), {'valeur': '1400-13', 'precision': 'mois'}),
                   (('chefs', 0, 'naissance'), {'valeur': '1401', 'precision': 'annee'})]
    manquantes = [(i, champ) for i, c in enumerate(document['chefs']) for champ in ('identite', 'naissance') if c['sources'][champ] is None]
    assert manquantes
    alterations += [(('chefs', i, 'lacunes', champ), ' ') for i, champ in manquantes]
    alterations += [((t, 0, k), 'SUPPRIMER') for t in ('familles', 'liens') for k in document[t][0]]
    alterations += [((t, 0, 'inconnu'), True) for t in ('chefs', 'familles', 'liens')]
    alterations += [((t, i, 'lacunes', k), '') for t in ('familles', 'liens') for i, f in enumerate(document[t]) for k, v in f['lacunes'].items() if v]
    alterations += [((t, i, 'sources', k), {}) for t in ('familles', 'liens') for i, f in enumerate(document[t]) for k in f['sources']]
    for chemin, valeur in alterations:
        with pytest.raises((AssertionError, ValueError, KeyError)):
            _personnages_sources(_alterer_personnages(document, chemin, valeur))
    _familles_historiques(document['familles'], document['liens'])
    # Une approximation et un intervalle restent textuels, sans conversion en date.
    assert any(c['naissance'] and c['naissance']['precision'] == 'intervalle' for c in document['chefs'])
    assert any(c['naissance'] and c['naissance']['precision'] == 'vers' for c in document['chefs'])


def _personnages_attestes(document):
    fiches = {c['maison']: c for c in document['chefs']}
    # Attentes tirées des pages consultées, indépendantes du document produit.
    temoins = {'seigneurie-1': ('Robert Ier de Bar', 'Robert_Ier_de_Bar', '1354'),
               'seigneurie-2': ('Eberhard III de Wurtemberg', 'sfz35480.html', '1392'),
               'seigneurie-3': ('Théodore Ier Paléologue', 'Despotate_of_the_Morea', '1383'),
               'seigneurie-4': ('Đurađ Vuković Branković', '%C4%90ura%C4%91_Brankovi%C4%87', '1396'),
               'seigneurie-5': ('Gazi Evrenos Bey', 'evrenosogullari', 'Bayezid'),
               'grande-15': ('Manuel II Paléologue', 'Manuel_II_Palaiologos', '1391'),
               'grande-8': ('Abu Abdallah Muhammad VII ibn Yusuf', 'Muhammad_VII_of_Granada', '1392'),
               'institution-13': ('Antonio Venier', 'Antonio_Venier', '1382'),
               'grande-9': ('Venceslas IV de Luxembourg', 'Wenceslaus_IV_of_Bohemia', 'Prague'),
               'grande-29': ('Robert III de Wittelsbach', 'Rupert_of_Germany', 'Heidelberg')}
    for identifiant, (nom, page, fait) in temoins.items():
        fiche = fiches[identifiant]
        assert fiche['nom'] == nom
        assert page in fiche['sources']['identite']['url'] and fait in fiche['sources']['identite']['fait']
    naissances = {'seigneurie-1': ('1344-11-08', 'jour', 'Robert_Ier_de_Bar'),
                  'grande-15': ('1350-06-27', 'jour', 'Manuel_II_Palaiologos'),
                  'grande-1': ('c. April 1367', 'vers', 'Henry_IV_of_England'),
                  'grande-13': ('1381 or 1382', 'intervalle', 'Eric_of_Pomerania')}
    for identifiant, (valeur, precision, page) in naissances.items():
        assert fiches[identifiant]['naissance'] == {'valeur': valeur, 'precision': precision}
        assert page in fiches[identifiant]['sources']['naissance']['url']
        assert fiches[identifiant]['sources']['naissance']['fait'].strip()
    for identifiant in ('grande-21', 'institution-12', 'institution-15', 'institution-31', 'institution-32'):
        assert fiches[identifiant]['nom'] is None and fiches[identifiant]['lacunes']['identite'].strip()
    # Les chefs du Maghreb (#1052) : Tlemcen réel, le Zab plausible et déclaré tel.
    for identifiant, (nom, page, fait) in {'grande-24': ('Abu Muhammad I', 'Zayyanid_dynasty', '1397'),
                                           'seigneurie-6': ('Abd al-Rahman ibn Mozni', 'Zab_Emirate', 'plausible et déclaré')}.items():
        fiche = fiches[identifiant]
        assert fiche['nom'] == nom and fiche['lacunes']['identite'] is None
        assert page in fiche['sources']['identite']['url'] and fait in fiche['sources']['identite']['fait']
        assert fiche['sources']['identite']['fait'].strip()
    for identifiant in ('grande-18', 'grande-20', 'institution-16', 'seigneurie-5', 'seigneurie-6'):
        assert fiches[identifiant]['naissance'] is None and fiches[identifiant]['lacunes']['naissance'].strip()


def test_personnages_attestes():
    document = _personnages()
    _personnages_attestes(document)
    indices = {c['maison']: i for i, c in enumerate(document['chefs'])}
    alterations = []
    for identifiant, champ, valeur in [('grande-15', 'nom', 'Théodore Ier Paléologue'),
                                     ('seigneurie-3', 'nom', 'Manuel II Paléologue'),
                                     ('seigneurie-1', 'naissance', {'valeur': '1344-11-09', 'precision': 'jour'}),
                                     ('grande-1', 'naissance', {'valeur': '1367-04-01', 'precision': 'jour'}),
                                     ('grande-13', 'naissance', {'valeur': '1381', 'precision': 'annee'})]:
        alterations.append(_alterer_personnages(document, ('chefs', indices[identifiant], champ), valeur))
    for champ in ('nom', 'naissance'):
        copie = copy.deepcopy(document)
        for fiche in copie['chefs']:
            fiche[champ] = None
        alterations.append(copie)
    alterations.append(_alterer_personnages(document, ('chefs', indices['grande-21'], 'lacunes', 'identite'), ''))
    for identifiant in ('grande-24', 'seigneurie-6'):
        alterations.append(_alterer_personnages(document, ('chefs', indices[identifiant], 'nom'), None))
        alterations.append(_alterer_personnages(document, ('chefs', indices[identifiant], 'lacunes', 'identite'), 'Lacune inventée'))
    for copie in alterations:
        with pytest.raises(AssertionError):
            _personnages_attestes(copie)


def test_personnes_catalogue(registre, tmp_path, monkeypatch):
    from sim import personnages as p
    monde, references, charger, _ = registre
    document, vue = _personnages(), charger()
    chemin = tmp_path / 'personnes.json'
    def lire(copie):
        chemin.write_text(json.dumps(copie), encoding='utf-8')
        return p.charger_catalogue(vue, chemin)
    assert lire(document) == document
    # Rejouer toutes les mutations de sources de #771 contre le lecteur réel.
    monkeypatch.setattr(sys.modules[__name__], '_personnages_sources', lire)
    test_personnages_sources()
    for maison in vue:
        with pytest.raises(ValueError):
            lire({**document, 'chefs': [c for c in document['chefs'] if c['maison'] != maison.id]})
    for lignes in (document['chefs'] * 2, [{**document['chefs'][0], 'maison': i} for i in ('inconnue', 'plausible-1')]):
        with pytest.raises(ValueError): lire({**document, 'chefs': lignes})
    with pytest.raises(ValueError): p.charger_catalogue(vue + (dataclasses.replace(vue[0], id='grande-999'),))
    for contenu in ('{', '{}', 'null'):
        chemin.write_text(contenu, encoding='utf-8')
        with pytest.raises(ValueError): p.charger_catalogue(vue, chemin)
    with pytest.raises(ValueError): p.charger_catalogue(vue, tmp_path / 'absent')
    monkeypatch.setattr(p, 'CHEMIN', chemin)
    with pytest.raises(ValueError): World.charger(0)


def test_personnes_chefs():
    from sim import personnages as p
    from sim.noms import noms_depuis_monde
    monde, document = World.charger(0), _personnages()
    historiques = {c['maison']: c for c in document['chefs']}
    noms = {i: f for v in noms_depuis_monde(monde).values() for i, f in v['maisons'].items()}
    def preuve(personnes, chefs):
        assert personnes and set(chefs) == {m.id for m in monde.maisons}
        attendu = [{**c, 'id': 'personne-' + c['maison'], 'origine': 'historique'} for c in historiques.values() if c['nom']]
        attendu += [{'id': 'personne-' + m.id, 'maison': m.id, 'origine': 'plausible',
                     'nom': noms[m.id]['prenom_chef'] + ' ' + noms[m.id]['nom'], 'naissance': None,
                     'sources': {'identite': None, 'naissance': None},
                     'lacunes': {'identite': None, 'naissance': 'Naissance inconnue du chef plausible.'}}
                    for m in monde.maisons if m.sorte == 'plausible']
        for lien in document['liens']:
            f = next(c for c in attendu if c['id'] == lien['id'])
            f.update({k: copy.deepcopy(lien[k]) for k in ('pere', 'mere', 'conjoints', 'presence')})
            for k in ('sources', 'lacunes'): f[k] = {**f[k], **lien[k]}
        for e in document['etats']: next(f for f in attendu if f['id'] == 'personne-' + e['maison'])['etat_familial'] = copy.deepcopy(e)
        attendu += [dict(f, origine='historique') for f in document['familles']]
        assert list(personnes) == sorted(attendu, key=lambda c: c['id'])
        p.valider_personnages(personnes, chefs, monde.maisons, document, noms)
    preuve(monde.personnages, monde.chefs)
    assert all(any(m.sorte == s and monde.chefs[m.id]['personnage'] for m in monde.maisons) for s in ('institution', 'plausible', 'seigneurie'))
    assert any(m.cell_id is None and monde.chefs[m.id]['personnage'] for m in monde.maisons)
    for c in historiques.values():
        assert monde.chefs[c['maison']] == {'personnage': 'personne-' + c['maison'] if c['nom'] else None, 'lacune': c['lacunes']['identite']}
    for chemin, valeur in ((('personnages',), monde.personnages[1:]), (('personnages', 0, 'id'), 'invalide'),
                           (('personnages', 0, 'maison'), 'inconnue'), (('personnages', 0, 'nom'), 'Altéré'),
                           (('personnages', 0, 'naissance'), {'valeur': '1367', 'precision': 'annee'}),
                           (('chefs', 'grande-21', 'lacune'), ''),
                           *[(('chefs', c['maison'], 'personnage'), monde.personnages[0]['id']) for c in historiques.values() if c['maison'] != monde.personnages[0]['maison']],
                           (('chefs', 'institution-12'), 'SUPPRIMER'), (('personnages',), monde.personnages * 2)):
        copie = _alterer_personnages({'personnages': list(monde.personnages), 'chefs': monde.chefs}, chemin, valeur)
        with pytest.raises((AssertionError, ValueError)): preuve(copie['personnages'], copie['chefs'])
        with pytest.raises(ValueError): p.valider_personnages(copie['personnages'], copie['chefs'], monde.maisons, document, noms)


@pytest.mark.parametrize('graine', [0, 42])
def test_personnes_serialisation(monkeypatch, graine):
    from sim import personnages as p
    appels = []
    lecteur = p.charger_catalogue
    monkeypatch.setattr(p, 'charger_catalogue', lambda *a: appels.append(a) or lecteur(*a))
    monde = World.charger(graine)
    assert World({}, []).personnages == () and World({}, []).chefs == {}
    document, original = monde.to_dict(), _octets_registre(monde.to_dict())
    assert len(appels) == 1
    assert World.charger(42).personnages == monde.personnages
    catalogue = _personnages()
    monkeypatch.setattr(p, 'charger_catalogue', lambda *a: {**catalogue, **{t: list(reversed(catalogue[t])) for t in ('chefs', 'familles', 'liens', 'etats')}})
    carte = World.lire_carte()
    monkeypatch.setattr(etat_monde, 'charger_registre_maisons', lambda c: tuple(reversed(charger_registre_maisons(c))))
    assert _octets_registre(World.charger(graine, carte).to_dict()) == original
    carte['cellules'].reverse()
    permute = World.charger(graine, carte).to_dict()
    assert _octets_registre(permute) == original
    def refuser(*a): raise RuntimeError('lecture interdite')
    for module, nom in ((p, 'charger_catalogue'), (p, 'construire_personnages'), (etat_monde, 'construire_personnages')):
        monkeypatch.setattr(module, nom, refuser)
    boheme = next(i for i, f in enumerate(document['personnages']) if f['id'] == 'personne-grande-9')
    chemins = [('presence',), ('lacunes', 'pere'), ('etat_familial', 'enfants'), ('etat_familial', 'sources', 'enfants', 'fait'), ('etat_familial', 'lacunes', 'enfants'), ('etat_familial', 'exclusions'), ('etat_familial', 'exclusions', 'Jeanne de Bavière', 'sources', 0, 'fait')]
    famille = next(i for i, f in enumerate(document['personnages']) if f['id'] == 'personne-jeanne')
    def alterer(objet):
        for k, v in (objet.items() if isinstance(objet, dict) else enumerate(objet)):
            if k == 'id': continue
            if isinstance(v, (dict, list)) and v: alterer(v)
            else: objet[k] = 'Altéré'
    def alterer_iles(d):
        for f in (f for f in d['personnages'] if f['maison'] in ('grande-1', 'grande-2', 'grande-4', 'grande-5', 'grande-6', 'grande-7', 'grande-8', 'grande-10', 'grande-11', 'grande-12', 'grande-13', 'grande-14', 'grande-15', 'grande-16', *BALKANS_MAISONS, *MAGHREB_MAISONS, *MCA_MAISONS, BOURGOGNE, PALATINAT, BAR)): alterer(f)
    assert document['personnages'] == list(monde.personnages)
    altere = copy.deepcopy(document); alterer_iles(altere)
    copie = copy.copy(monde); copie.personnages = tuple(altere['personnages'])
    assert _octets_registre(copie.to_dict()) == _octets_registre(altere) != original
    for chemin, valeur in (*[(('personnages', boheme, *k), 'Altéré') for k in chemins], (('personnages', famille, 'mere'), 'autre'), (('personnages', famille, 'conjoints'), []),
                           (('personnages', famille, 'sources', 'presence', 'fait'), 'Altéré'), (('personnages',), []), (('chefs',), {}), (('personnages', 0, 'nom'), 'Altéré'),
                           (('personnages', 0, 'naissance', 'valeur'), 'inconnue'),
                           (('personnages', 0, 'sources', 'identite', 'fait'), 'Altéré'), (('chefs', 'grande-21', 'lacune'), 'Altérée')):
        copie = copy.copy(monde)
        altere = _alterer_personnages(document, chemin, valeur)
        copie.personnages, copie.chefs = tuple(altere['personnages']), altere['chefs']
        assert _octets_registre(copie.to_dict()) == _octets_registre(altere) != original
    alterer_iles(document)
    for k in sorted(chemins, key=len, reverse=True):
        cible = document['personnages'][boheme]
        for cle in k[:-1]: cible = cible[cle]
        cible[k[-1]] = 'Altéré'
    document['personnages'][famille]['mere'] = 'autre'
    document['personnages'][famille]['conjoints'].append('autre')
    document['personnages'][famille]['sources']['presence']['fait'] = 'Altéré'
    document['personnages'][0]['sources']['identite']['fait'] = 'Altéré'
    document['chefs']['grande-21']['lacune'] = 'Altérée'
    assert _octets_registre(monde.to_dict()) == original


def _naissance_famille(valeur, precision='jour'):
    return None if valeur is None else {'valeur': valeur, 'precision': precision}


def _famille_liens():
    return [{'id': i, 'nom': 'Homonyme', 'naissance': _naissance_famille(n),
             'pere': 'p' if i == 'e' else None, 'mere': 'm' if i == 'e' else None,
             'conjoints': conjoints}
            for i, n, conjoints in [('p', '1350-01-01', ['m']),
                                    ('m', '1360-06-15', ['p']), ('e', '1380-06-15', [])]]


def _controler_famille(fiches):
    from sim.personnages import valider_liens_familiaux
    import random
    avant, hasard = copy.deepcopy(fiches), random.getstate()
    try:
        return valider_liens_familiaux(fiches)
    finally:
        assert fiches == avant
        assert random.getstate() == hasard


@pytest.mark.parametrize('json_lu', [False, True])
@pytest.mark.parametrize('chemin,valeur', [
    ((), []), ((0, 'id'), ''), ((0, 'id'), ' '), ((0, 'id'), 'e'),
    ((2, 'pere'), 'inconnu'), ((2, 'mere'), 'inconnue'), ((0, 'conjoints'), ['inconnu']),
    ((2, 'pere'), 'e'), ((2, 'mere'), 'e'), ((0, 'conjoints'), ['p']),
    ((2, 'mere'), 'p'), ((0, 'conjoints'), ['m', 'm']), ((1, 'conjoints'), []),
    ((2, 'pere'), 'SUPPRIMER'), ((2, 'mere'), 'SUPPRIMER'),
    ((2, 'naissance'), 'SUPPRIMER'), ((2, 'conjoints'), 'SUPPRIMER'),
    ((0, 'conjoints'), 'm'), ((2, 'pere'), ''),
])
def test_familles_liens_structure_refus(tmp_path, json_lu, chemin, valeur):
    def lire(fiches):
        return json.loads(_ecrire(tmp_path, fiches).read_text()) if json_lu else fiches
    famille = _famille_liens()
    bilan = _controler_famille(lire(famille))
    assert len(bilan['verifies']) == 3 and bilan['indetermines'] == []
    alteree = _alterer_personnages(famille, chemin, valeur) if chemin else valeur
    with pytest.raises(ValueError): _controler_famille(lire(alteree))


def test_familles_liens_structure_cycles_et_libertes():
    famille = _famille_liens()
    for fiche in famille:
        fiche['naissance'], fiche['conjoints'] = None, []
    assert len(_controler_famille(famille)['indetermines']) == 3
    famille[0]['pere'], famille[1]['pere'] = 'm', 'e'
    with pytest.raises(ValueError, match='cycle'): _controler_famille(famille)
    famille = _famille_liens()
    famille.append({**copy.deepcopy(famille[1]), 'id': 'autre'})
    famille[0]['conjoints'].append('autre')
    assert len(_controler_famille(famille)['verifies']) == 3


@pytest.mark.parametrize('date,acceptee', [
    ('1374-06-15', False), ('1375-06-14', False), ('1375-06-15', True),
    ('1405-06-15', True), ('1406-06-14', True), ('1406-06-15', False),
])
def test_familles_liens_dates_anniversaires(date, acceptee):
    famille = _famille_liens()
    famille[2]['naissance'] = _naissance_famille(date)
    if acceptee:
        bilan = _controler_famille(famille)
        assert bilan['indetermines'] == [] and len(bilan['verifies']) == 3
        assert {'contrainte': 'age_maternel', 'personnes': ('m', 'e')} in bilan['verifies']
    else:
        with pytest.raises(ValueError): _controler_famille(famille)


@pytest.mark.parametrize('index,date', [
    (0, '1380-06-15'), (0, '1380-06-16'), (1, '1380-06-15'), (1, '1380-06-16'),
    (2, '1380-02-30'), (2, '1380-13-01'), (2, '1380-2-01'),
])
def test_familles_liens_dates_refus(index, date):
    famille = _famille_liens()
    famille[index]['naissance'] = _naissance_famille(date)
    with pytest.raises(ValueError): _controler_famille(famille)


@pytest.mark.parametrize('mere,pm,enfant,pe,attendu', [
    ('1360', 'annee', '1380', 'annee', 'verifies'),
    ('1360', 'annee', '1375', 'annee', 'indetermines'),
    ('1360', 'annee', '1374', 'annee', 'refus'),
    ('1360', 'annee', '1405', 'annee', 'verifies'),
    ('1360', 'annee', '1406', 'annee', 'indetermines'),
    ('1360', 'annee', '1407', 'annee', 'refus'),
    ('1360-06', 'mois', '1375-06', 'mois', 'indetermines'),
    ('1360-06', 'mois', '1375-07', 'mois', 'verifies'),
    ('1360-06', 'mois', '1375-05', 'mois', 'refus'),
    ('1360-02', 'mois', '1375-02-28', 'jour', 'indetermines'),
    ('1360-02', 'mois', '1375-03-01', 'jour', 'verifies'),
    ('1360-02-29', 'jour', '1375-02-28', 'jour', 'refus'),
    ('1360-02-29', 'jour', '1375-03-01', 'jour', 'verifies'),
    ('1360-02-29', 'jour', '1406-02-28', 'jour', 'verifies'),
    ('1360-02-29', 'jour', '1406-03-01', 'jour', 'refus'),
    ('vers 1360', 'vers', '1380', 'annee', 'indetermines'),
    ('1359 ou 1360', 'intervalle', '1380', 'annee', 'indetermines'),
    (None, 'jour', '1380', 'annee', 'indetermines'),
    ('1360', 'annee', None, 'jour', 'indetermines'),
    ('1360', 'annee', 'vers 1380', 'vers', 'indetermines'),
    ('1360', 'annee', '1379 ou 1380', 'intervalle', 'indetermines'),
])
def test_familles_liens_precisions_ages(mere, pm, enfant, pe, attendu):
    famille = _famille_liens()
    famille[1]['naissance'], famille[2]['naissance'] = (
        _naissance_famille(mere, pm), _naissance_famille(enfant, pe))
    if attendu == 'refus':
        with pytest.raises(ValueError): _controler_famille(famille)
        return
    bilan = _controler_famille(famille)
    ages = [c for c in bilan[attendu] if c['contrainte'] == 'age_maternel']
    assert len(ages) == 1 and ages[0]['personnes'] == ('m', 'e')
    contraire = 'verifies' if attendu == 'indetermines' else 'indetermines'
    assert not any(c['contrainte'] == 'age_maternel' for c in bilan[contraire])
    assert all(c['motif'].strip() and len(c['personnes']) == 2 for c in bilan['indetermines'])


@pytest.mark.parametrize('pere,enfant,attendu', [
    ('1380', '1380', 'indetermines'), ('1380', '1381', 'verifies'),
    ('1381', '1380', 'refus'), ('1380-02', '1380-02-29', 'indetermines'),
    ('1380-02', '1380-03-01', 'verifies'), ('1380-02', '1380-01-31', 'refus'),
])
def test_familles_liens_precisions_anteriorite(pere, enfant, attendu):
    famille = _famille_liens()
    for index, valeur in ((0, pere), (2, enfant)):
        precision = {4: 'annee', 7: 'mois', 10: 'jour'}[len(valeur)]
        famille[index]['naissance'] = _naissance_famille(valeur, precision)
    if attendu == 'refus':
        with pytest.raises(ValueError): _controler_famille(famille)
    else:
        bilan = _controler_famille(famille)
        assert any(c['contrainte'] == 'anteriorite' and c['personnes'] == ('p', 'e')
                   for c in bilan[attendu])


FAMILLE_1400 = [('isabeau', 'Isabeau de Bavière', '1370', 'vers'),
                ('isabelle', 'Isabelle de France', '1389-11-09', 'jour'),
                ('jeanne', 'Jeanne de France', '1391-01-24', 'jour'),
                ('charles', 'Charles de France', '1392-02-06', 'jour'),
                ('marie', 'Marie de France', '1393-08-22', 'jour'),
                ('michelle', 'Michelle de France', '1395-01-11', 'jour'),
                ('louis', 'Louis de France', '1397-01-22', 'jour'),
                ('jean', 'Jean de France', '1398-08-31', 'jour')]


# Notices individuelles et tableaux des parents consultés le 22 octobre 2026.
ILES_1400 = [('marie-bohun', 'Marie de Bohun', 'vers 1369/1370', 'vers', 'Mary_de_Bohun', '1394-06-04'),
             ('henri-monmouth', 'Henri de Monmouth', '1386 ou 1387', 'intervalle', 'Henry_V_of_England#Birth_and_family', '1422'),
             ('thomas-lancastre', 'Thomas de Lancastre', 'automne 1387', 'intervalle', 'Thomas_of_Lancaster,_Duke_of_Clarence', '1421'),
             ('jean-lancastre', 'Jean de Lancastre', '1389-06-20', 'jour', 'John_of_Lancaster,_Duke_of_Bedford', '1435'),
             ('humphrey-lancastre', 'Humphrey de Lancastre', '1390-10-03', 'jour', 'Humphrey,_Duke_of_Gloucester', '1447'),
             ('blanche-angleterre', 'Blanche d’Angleterre', 'printemps 1392', 'intervalle', 'Blanche_of_England', '1409'),
             ('philippa-angleterre', 'Philippa d’Angleterre', 'milieu de 1394', 'intervalle', 'Philippa_of_England', '1430'),
             ('annabella', 'Annabella Drummond', 'vers 1350', 'vers', 'Annabella_Drummond', '1401'),
             ('marguerite-stuart', 'Marguerite Stuart', 'vers 1370', 'vers', 'Margaret_Stewart,_Duchess_of_Touraine', '1450'),
             ('elisabeth-stuart', 'Élisabeth Stuart', 'vers 1372/1373', 'vers', 'Annabella_Drummond#Issue', '1411'),
             ('david-stuart', 'David Stuart', '1378-10-24', 'jour', 'David_Stewart,_Duke_of_Rothesay', '1402'),
             ('marie-stuart', 'Marie Stuart', 'vers 1380', 'vers', 'Mary_Stewart_(daughter_of_Robert_III)', '1460'),
             ('jacques-stuart', 'Jacques Stuart', '1394-07', 'mois', 'James_I_of_Scotland', '1437'),
             ('jean-ardgowan', 'Jean Stuart d’Ardgowan', '1364', 'annee', 'Robert_III_of_Scotland#Family_and_issue', '1412')]


def _iles_historiques(fiches):
    for rang, (i, nom, date, precision, page, fin) in enumerate(ILES_1400):
        f = fiches['personne-' + i]
        assert set(f['sources']) == set(f['lacunes']) == {'identite', 'naissance', 'presence', 'pere', 'mere', 'conjoints'}
        chef = 'personne-grande-' + ('1' if rang < 7 else '2')
        parents = (None, None) if i in ('marie-bohun', 'annabella') else (chef, None if i == 'jean-ardgowan' else 'personne-' + ('marie-bohun' if rang < 7 else 'annabella'))
        assert (f['nom'], f['maison'], f['naissance'], f['pere'], f['mere']) == (nom, chef[9:], _naissance_famille(date, precision), *parents)
        assert f['presence'] == ('decedee' if i == 'marie-bohun' else 'vivante')
        assert f['conjoints'] == ([chef] if i == 'annabella' else [])
        for k in ('identite', 'naissance', 'presence', 'pere', 'mere', 'conjoints'):
            source, lacune = f['sources'][k], f['lacunes'][k]
            if k in ('identite', 'naissance', 'presence') or f[k]:
                attendu = page if k in ('identite', 'naissance', 'presence') else ('Henry_IV_of_England#Marriages_and_issue' if rang < 7 else 'Robert_III_of_Scotland#Family_and_issue')
                assert source and source['url'] == 'https://en.wikipedia.org/wiki/' + attendu and nom in source['fait'] and lacune is None
                if k == 'naissance': assert all(v in source['fait'] for v in date.replace(' ou ', '/').split('/'))
                if k == 'presence': assert fin in source['fait']
                if k in ('pere', 'mere', 'conjoints'): assert ('Henri IV' if rang < 7 else 'Robert III') in source['fait']
                if k == 'mere': assert ('Marie de Bohun' if rang < 7 else 'Annabella Drummond') in source['fait']
            else:
                assert source is None and lacune and ('aucune absence attestée' in lacune or 'inconnue' in lacune or '1394-06-04' in lacune)
    for i, conjoint in [('1', []), ('2', ['personne-annabella'])]:
        f = fiches['personne-grande-' + i]
        assert {'pere', 'mere', 'conjoints', 'presence'} <= f['sources'].keys() & f['lacunes'].keys()
        for k in ('conjoints', 'presence'):
            if f['sources'][k]: assert f['sources'][k]['url'] == 'https://en.wikipedia.org/wiki/' + ('Henry_IV_of_England#Marriages_and_issue' if i == '1' else 'Robert_III_of_Scotland#Family_and_issue')
        assert (f['pere'], f['mere'], f['conjoints'], f['presence']) == (None, None, conjoint, 'vivante')
        assert f['sources']['presence'] and ('Henri IV' if i == '1' else 'Robert III') in f['sources']['presence']['fait'] and f['lacunes']['presence'] is None
        for k in ('pere', 'mere'): assert f['sources'][k] is None and 'aucune absence attestée' in f['lacunes'][k]
        if i == '1': assert f['sources']['conjoints'] is None and '1394-06-04' in f['lacunes']['conjoints']
        else: assert f['sources']['conjoints'] and 'Annabella Drummond' in f['sources']['conjoints']['fait'] and f['lacunes']['conjoints'] is None


# Notices individuelles et tableaux ibériques consultés le 22 octobre 2026.
IBERIE_1400 = [('philippa-lancastre', 'Philippa de Lancastre', '1360-03-31', 'jour', 'Philippa_of_Lancaster', '1415', '4', None),
               ('afonso-portugal', 'Afonso de Portugal', '1390-07-30', 'jour', 'John_I_of_Portugal#Marriage_and_descendants', '1400-12-22', '4', 'philippa-lancastre'),
               ('edouard-portugal', 'Édouard de Portugal', '1391-10-31', 'jour', 'Edward,_King_of_Portugal', '1438', '4', 'philippa-lancastre'),
               ('pierre-portugal', 'Pierre de Portugal', '1392-12-09', 'jour', 'Peter,_Duke_of_Coimbra', '1449', '4', 'philippa-lancastre'),
               ('henri-portugal', 'Henri de Portugal', '1394-03-04', 'jour', 'Henry_the_Navigator', '1460', '4', 'philippa-lancastre'),
               ('isabelle-portugal', 'Isabelle de Portugal', '1397-02-21', 'jour', 'Isabella_of_Portugal,_Duchess_of_Burgundy', '1471', '4', 'philippa-lancastre'),
               ('ines-pires', 'Inês Pires', 'vers 1350', 'vers', 'John_I_of_Portugal#Marriage_and_descendants', '1400 ?', '4', None),
               ('afonso-bragance', 'Afonso de Bragance', '1377-08-10', 'jour', 'Afonso_I,_Duke_of_Braganza', '1461', '4', 'ines-pires'),
               ('beatrice-portugal', 'Béatrice de Portugal', 'vers 1380', 'vers', 'Beatrice,_Countess_of_Arundel', '1439', '4', 'ines-pires'),
               ('catherine-lancastre', 'Catherine de Lancastre', '1372-06-06 ou 1373-03-31', 'intervalle', 'Catherine_of_Lancaster#Notes', '1418', '5', None),
               ('maria-luna', 'Maria de Luna', 'vers 1358', 'vers', 'Maria_de_Luna', '1406', '6', None),
               ('martin-sicile', 'Martin de Sicile', 'vers 1374/1376', 'vers', 'Martin_I_of_Sicily', '1409', '6', 'maria-luna')]
IBERIE_CHEFS = {
    '4': ('Jean Ier', 'John_I_of_Portugal#Marriage_and_descendants', 'philippa-lancastre', '2 février 1387', '1433'),
    '5': ('Henri III', 'Henry_III_of_Castile#Marriage_and_issue', 'catherine-lancastre', '1388', '1406'),
    '6': ('Martin d’Aragon', 'Martin_of_Aragon', 'maria-luna', '13 juin 1372', '1410')}
IBERIE_EXCLUSIONS = {
    '4': {'Blanche de Portugal': ('1389-03-06',), 'Jean de Portugal': ('1400-01-13',), 'Ferdinand de Portugal': ('1402',)},
    '5': {'Marie de Castille': ('1401',), 'Catherine de Castille': ('1403',), 'Jean de Castille': ('1405',)},
    '6': {'Jacques d’Aragon': ('1378', 'mort jeune', '1391'), 'Jean d’Aragon': ('1380', 'mort jeune', '1391'),
          'Marguerite d’Aragon': ('1384/1388', 'morte jeune', '1391'), 'Marguerite de Prades': ('1409',)}}


def _iberie_historiques(fiches):
    noms = {i: nom for i, nom, *_ in IBERIE_1400}
    for i, nom, date, precision, page, fin, maison, mere in IBERIE_1400:
        f = fiches['personne-' + i]; chef, lien, epouse, union, _ = IBERIE_CHEFS[maison]
        assert set(f['sources']) == set(f['lacunes']) == {'identite', 'naissance', 'presence', 'pere', 'mere', 'conjoints'}
        assert (f['nom'], f['maison'], f['naissance'], f['pere'], f['mere'], f['conjoints'], f['presence']) == (
            nom, 'grande-' + maison, _naissance_famille(date, precision),
            'personne-grande-' + maison if mere else None, 'personne-' + mere if mere else None,
            ['personne-grande-' + maison] if i == epouse else [], 'indeterminee' if i == 'ines-pires' else 'vivante')
        for k in f['sources']:
            source, lacune = f['sources'][k], f['lacunes'][k]
            if k == 'presence' and i == 'ines-pires':
                assert source is None and all(v in lacune for v in ('https://en.wikipedia.org/wiki/Inês_Pires', '1400 ?', 'indéterminée')); continue
            if k in ('identite', 'naissance', 'presence') or f[k]:
                assert source and source['url'] == 'https://en.wikipedia.org/wiki/' + (page if k in ('identite', 'naissance', 'presence') else lien) and nom in source['fait'] and lacune is None
                if k == 'naissance': assert all(v in source['fait'] for v in date.replace(' ou ', '/').split('/'))
                if k == 'presence': assert fin in source['fait']
                justifications = {'maria-luna': ('c. 1358', 'approximation'), 'martin-sicile': ('c. 1374/1376', 'approximation'),
                                  'catherine-lancastre': ('note', 'infobox', 'non départagées')}
                if k == 'naissance' and i in justifications: assert all(v in source['fait'] for v in justifications[i])
                if k in ('pere', 'mere'): assert chef in source['fait'] and noms[mere] in source['fait']
                if k == 'conjoints': assert chef in source['fait'] and union in source['fait']
            else: assert source is None and 'aucune absence attestée' in lacune
    for maison, (nom, page, epouse, union, fin) in IBERIE_CHEFS.items():
        f = fiches['personne-grande-' + maison]
        assert {'pere', 'mere', 'conjoints', 'presence'} <= f['sources'].keys() & f['lacunes'].keys()
        assert (f['pere'], f['mere'], f['conjoints'], f['presence']) == (None, None, ['personne-' + epouse], 'vivante')
        for k in ('pere', 'mere'): assert f['sources'][k] is None and 'aucune absence attestée' in f['lacunes'][k]
        for k in ('conjoints', 'presence'):
            source = f['sources'][k]
            assert source and source['url'] == 'https://en.wikipedia.org/wiki/' + page and nom in source['fait'] and f['lacunes'][k] is None
            assert all(v in source['fait'] for v in ((noms[epouse], union) if k == 'conjoints' else (fin,)))


def _etats_iberie(e):
    maison = e['maison'][7:]; nom, page, epouse, union, _ = IBERIE_CHEFS[maison]
    assert (e['conjoints'], e['enfants'], e['lacunes']) == ('union', 'absence_attestee' if maison == '5' else 'documentes', {'conjoints': None, 'enfants': None})
    assert set(e['sources']) == {'conjoints', 'enfants'}
    for k, source in e['sources'].items():
        assert source and source['url'] == 'https://en.wikipedia.org/wiki/' + page and nom in source['fait']
        attendus = ([union, next(n for i, n, *_ in IBERIE_1400 if i == epouse)] if k == 'conjoints' else
                    [n for _, n, _, _, _, _, m, mere in IBERIE_1400 if m == maison and mere] if maison != '5' else
                    ['1401', '1403', '1405', 'aucun enfant'])
        assert all(v in source['fait'] for v in attendus)
    assert set(e['exclusions']) == set(IBERIE_EXCLUSIONS[maison])
    for nom, faits in IBERIE_EXCLUSIONS[maison].items():
        x = e['exclusions'][nom]
        assert nom in x['motif'] and all(v in x['motif'] for v in faits) and x['sources']
        assert all(s['url'] in {'https://en.wikipedia.org/wiki/' + page, 'https://en.wikipedia.org/wiki/Maria_de_Luna'} and nom in s['fait'] for s in x['sources'])
        assert all(any(v in source['fait'] for source in x['sources']) for v in faits)
        assert {source['url'] for source in x['sources']} == {'https://en.wikipedia.org/wiki/' + page} | (
            {'https://en.wikipedia.org/wiki/Maria_de_Luna'} if maison == '6' and nom != 'Marguerite de Prades' else set())


def _familles_historiques(familles, liens):
    famille = FAMILLE_1400 + [('sophie-baviere', 'Sophie de Bavière', '1376', 'annee')]
    assert len(familles) == len(famille) + len(ILES_1400) + len(IBERIE_1400) + len(FIN_1400) + 4 + len(OTTOMANS) + len(BALKANS) + len(FICHES_MCA) + len(FICHES_BOURGOGNE) + len(FICHES_PALATINAT) + len(FICHES_BAR) == 102
    assert {f['id'] for f in familles} == {'personne-' + i for i, *_ in famille + ILES_1400 + IBERIE_1400 + FIN_1400 + list(OTTOMANS)} | {'personne-marie-bourgogne', 'personne-helena-dragas', 'personne-jean-viii', 'personne-theodore-ii'} | {'personne-' + i for i in BALKANS} | {'personne-' + i for i in FICHES_MCA} | {'personne-' + i for i in FICHES_BOURGOGNE} | {'personne-' + i for i in FICHES_PALATINAT} | {'personne-' + i for i in FICHES_BAR}
    fiches = {f['id']: f for f in familles + liens}
    couples = {'personne-isabeau': 'personne-grande-3', 'personne-jeanne': 'personne-grande-28', 'personne-sophie-baviere': 'personne-grande-9'}
    couples.update({v: k for k, v in list(couples.items())})
    for i, nom, date, precision in famille:
        f = fiches['personne-' + i]
        assert (f['nom'], f['maison'], f['naissance']) == (nom, 'grande-9' if i == 'sophie-baviere' else 'grande-3', {'valeur': date, 'precision': precision})
        assert (f['pere'], f['mere']) == ((None, None) if i in ('isabeau', 'sophie-baviere') else ('personne-grande-3', 'personne-isabeau'))
    assert len(liens) == 29 and {f['id'] for f in liens} == {'personne-grande-' + i for i in ('1', '2', '3', '28', '29', '9', '4', '5', '6', '7', '8', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '22', '23', '25', '26', '27', '30')} | {CHEF_BAR}
    _iles_historiques(fiches)
    _iberie_historiques(fiches)
    _fin_historiques(fiches)
    _voisins_historiques(fiches)
    _constantinople(fiches)
    _ottomans(fiches)
    _balkans(fiches)
    _maghreb(fiches)
    _mca(fiches)
    _bourgogne(fiches)
    _palatinat(fiches)
    _bar(fiches)
    for i, f in fiches.items():
        if i in {'personne-marie-bourgogne'} | {'personne-grande-' + m for m in VOISINS_CHEFS} | {'personne-' + r[0] for r in ILES_1400 + IBERIE_1400 + FIN_1400} | {'personne-grande-' + i for i in ('1', '2', '4', '5', '6', '7', '8', '10')} | {'personne-' + s for s in ('grande-15', 'helena-dragas', 'jean-viii', 'theodore-ii', 'grande-16')} | {'personne-' + o[0] for o in OTTOMANS} | {'personne-' + i for i in BALKANS} | {'personne-' + m for m in BALKANS_MAISONS} | {'personne-' + m for m in MAGHREB_MAISONS} | {'personne-' + i for i in FICHES_MCA} | {'personne-' + m for m in MCA_MAISONS} | {'personne-' + i for i in FICHES_BOURGOGNE} | {'personne-' + BOURGOGNE} | {'personne-' + i for i in FICHES_PALATINAT} | {CHEF_PAL} | {'personne-' + i for i in FICHES_BAR} | {CHEF_BAR}: continue
        assert set(f['sources']) == set(f['lacunes']) == ({'identite', 'naissance'} if 'nom' in f else set()) | {'pere', 'mere', 'conjoints', 'presence'}
        assert f['presence'] == 'vivante'
        if i in ('personne-grande-9', 'personne-sophie-baviere'): assert f['sources']['conjoints'] and '2 mai 1389' in f['sources']['conjoints']['fait']
        assert f['conjoints'] == ([couples[i]] if i in couples else [])
        for champ in ('identite', 'naissance', 'pere', 'mere', 'conjoints', 'presence'):
            if champ in ('identite', 'naissance') and 'nom' not in f: continue
            source = f['sources'][champ]
            if champ in ('identite', 'naissance', 'presence') or f.get(champ):
                assert source and source['fait'].strip()
                if champ in ('pere', 'mere'): assert f['nom'] in source['fait'] and 'Charles VI' in source['fait'] and 'Isabeau' in source['fait']
                page = 'Charles_VI_of_France#Marriage_and_issue'
                if i == 'personne-isabeau' and champ in ('naissance', 'conjoints'): page = 'Isabeau_of_Bavaria'
                if i == 'personne-jeanne' and champ == 'conjoints': page = 'Joan_of_France,_Duchess_of_Brittany'
                if i == 'personne-sophie-baviere': page = 'Sophia_of_Bavaria'
                if i == 'personne-grande-9': page = 'Wenceslaus_IV_of_Bohemia#Personal_life'
                if i == 'personne-grande-28': page = 'John_V_of_Brittany#Family'
                if i.startswith('personne-grande-') and champ in ('identite', 'naissance'): continue
                assert source['url'] == 'https://en.wikipedia.org/wiki/' + page
                assert f['lacunes'][champ] is None
            else: assert source is None and 'aucune absence attestée' in f['lacunes'][champ]
    assert not any(f['pere'] == 'personne-grande-28' or f['mere'] == 'personne-grande-28' for f in familles)


def test_familles_historiques():
    document, monde = _personnages(), World.charger(0)
    r = {f.get('id', f.get('maison')): i for t in ('familles', 'liens', 'etats') for i, f in enumerate(document[t])}
    _familles_historiques(document.get('familles', []), document.get('liens', []))
    _familles_historiques([f for f in monde.personnages if f['id'] != 'personne-' + f['maison']],
                         [f for f in monde.personnages if f['id'] == 'personne-' + f['maison'] and {'pere', 'mere', 'conjoints', 'presence', 'etat_familial'} & f.keys()])
    mutations = [(('familles',), []), (('familles', r['personne-charles'], 'naissance', 'valeur'), '1392-02-07'),
                 (('familles', r['personne-charles'], 'mere'), 'personne-jeanne'), (('familles', r['personne-charles'], 'sources', 'mere'), None),
                 (('familles', r['personne-charles'], 'sources', 'presence'), None)]
    mutations += [(('familles',), [f for f in document['familles'] if f['id'] != 'personne-' + i]) for i, *_ in FAMILLE_1400 + [('sophie-baviere',)] + ILES_1400 + IBERIE_1400 + FIN_1400 + [('marie-bourgogne',)]]
    for i, date in [('charles-1386', '1386-09-25'), ('jeanne-1388', '1388-06-14'), ('catherine', '1401-10-27'),
                    ('charles-1403', '1403-02-22'), ('philippe', '1407-11-10'), ('anne-bretagne', '1409-01-01')]:
        ajout = dict(copy.deepcopy(document['familles'][r['personne-charles']]), id='personne-' + i, naissance=_naissance_famille(date))
        if i == 'anne-bretagne': ajout['pere'] = 'personne-grande-28'
        mutations.append((('familles',), document['familles'] + [ajout]))
    double = copy.deepcopy(document)
    double['familles'].append(dict(copy.deepcopy(next(f for f in double['familles'] if f['id'] == 'personne-jeanne')), id='personne-jeanne-bis'))
    next(f for f in double['liens'] if f['id'] == 'personne-grande-28')['conjoints'].append('personne-jeanne-bis')
    assert _controler_famille(double['familles'] + [{**c, **l} for l in double['liens'] for c in document['chefs'] if 'personne-' + c['maison'] == l['id']])
    mutations.append((('familles',), double['familles']))
    for chemin, valeur in mutations:
        copie = _alterer_personnages(document, chemin, valeur)
        with pytest.raises(AssertionError): _familles_historiques(copie['familles'], copie['liens'])


def test_familles_integration(tmp_path, monkeypatch):
    from sim import personnages as p
    from sim.noms import noms_depuis_monde
    document, monde = _personnages(), World.charger(0)
    r = {f.get('id', f.get('maison')): i for t in ('familles', 'liens', 'etats') for i, f in enumerate(document[t])}
    noms = {i: f for v in noms_depuis_monde(monde).values() for i, f in v['maisons'].items()}
    chemin = tmp_path / 'familles.json'
    monkeypatch.setattr(p, 'CHEMIN', chemin)
    def lire(d):
        chemin.write_text(json.dumps(d), encoding='utf-8')
        return p.charger_catalogue(monde.maisons, chemin)
    assert lire(document) == document and World.charger(0).personnages == monde.personnages
    reelles = [f for f in monde.personnages if 'pere' in f]
    bilan = _controler_famille(reelles)
    parents = [('grande-3', 'isabeau', i) for i, *_ in FAMILLE_1400[1:]] + [('grande-1', 'marie-bohun', i) for i, *_ in ILES_1400[1:7]] + [('grande-2', 'annabella', i) for i, *_ in ILES_1400[8:13]] + [('grande-2', None, 'jean-ardgowan')]
    verifies = {('anteriorite', ('personne-grande-3', 'personne-' + i)) for i, *_ in FAMILLE_1400[1:]}
    parents += [('grande-' + m, mere, i) for i, _, _, _, _, _, m, mere in IBERIE_1400 if mere]
    verifies |= {('anteriorite', ('personne-grande-4', 'personne-' + i)) for i in ('afonso-portugal', 'edouard-portugal', 'pierre-portugal', 'henri-portugal', 'isabelle-portugal', 'afonso-bragance')} | {(k, ('personne-philippa-lancastre', 'personne-' + i)) for i in ('afonso-portugal', 'edouard-portugal', 'pierre-portugal', 'henri-portugal', 'isabelle-portugal') for k in ('anteriorite', 'age_maternel')}
    parents += [('grande-' + m, mere, i) for i, _, _, _, _, _, m, mere in FIN_1400 if i in FIN_ENFANTS]
    verifies |= {('anteriorite', ('personne-grande-' + m, 'personne-' + i)) for i, m in [('jeanne-foix', '7'), ('charles-navarre', '7'), ('lancelot-navarre', '7'), ('valentine-visconti', '10'), ('gian-maria', '10'), ('filippo-maria', '10')]} | {(k, ('personne-' + m, 'personne-' + i)) for m, i in [('isabelle-vertus', 'valentine-visconti'), ('caterina-visconti', 'gian-maria'), ('caterina-visconti', 'filippo-maria')] for k in ('anteriorite', 'age_maternel')}
    parents += [('grande-15', 'helena-dragas', 'jean-viii'), ('grande-15', 'helena-dragas', 'theodore-ii')]
    verifies |= {('anteriorite', ('personne-grande-15', 'personne-jean-viii'))}
    parents += [('grande-16', m, i) for i, _, _, _, m, epoux, *_ in OTTOMANS if not epoux]
    parents += [('grande-19', mere and mere[len('personne-'):], i) for i, (_, _, _, pere, mere, *_) in BALKANS.items() if pere]
    parents += [('grande-30', 'jeanne-sophie-baviere', i) for i in ENFANTS_MCA]
    verifies |= {('anteriorite', ('personne-grande-30', 'personne-' + i)) for i in ENFANTS_MCA}
    parents += [('grande-27', 'marguerite-flandre', i) for i in ENFANTS_BOURGOGNE]
    verifies |= {(k, (p, 'personne-' + i)) for i in ENFANTS_BOURGOGNE for p, ks in (('personne-grande-27', ('anteriorite',)), ('personne-marguerite-flandre', ('anteriorite', 'age_maternel'))) for k in ks}
    parents += [('grande-29', 'elisabeth-nuremberg', i) for i in ENFANTS_PALATINAT]
    verifies |= {(k, (p, 'personne-' + i)) for i in ENFANTS_PALATINAT if i != 'frederic-palatinat' for p, ks in ((CHEF_PAL, ('anteriorite',)), (EPOUSE_PAL, ('anteriorite', 'age_maternel'))) for k in ks}
    parents += [(BAR, 'marie-valois', i) for i in ENFANTS_BAR]
    verifies |= {(k, (p, 'personne-' + i)) for i in ('edouard-bar', 'jean-bar') for p, ks in ((CHEF_BAR, ('anteriorite',)), (EPOUSE_BAR, ('anteriorite', 'age_maternel'))) for k in ks}
    paternels = [i for i, _, _, _, _, epoux, *_ in OTTOMANS if not epoux] + [i for i, v in BALKANS.items() if v[3]] + ['frederic-palatinat'] + list(SANS_BORNES_BAR)
    maternites = [i for i, _, _, _, m, *_ in OTTOMANS if m] + [i for i, v in BALKANS.items() if v[4]] + list(ENFANTS_MCA) + ['frederic-palatinat'] + list(SANS_BORNES_BAR)
    assert len(paternels) == 18 and len(maternites) == 13
    assert len(bilan['verifies']) == 83 and len(bilan['indetermines']) == 86 + len(paternels) + 2 * len(maternites) == 130
    controles = {('anteriorite', ('personne-' + p, 'personne-' + e)) for p, m, e in parents} | {(k, ('personne-' + m, 'personne-' + e)) for p, m, e in parents if m for k in ('anteriorite', 'age_maternel')}
    assert {(c['contrainte'], c['personnes']) for c in bilan['verifies']} == verifies
    assert {(c['contrainte'], c['personnes']) for c in bilan['indetermines']} == controles - verifies
    assert all(c['motif'] == 'Naissance absente ou sans bornes exploitables.' for c in bilan['indetermines'])
    ages = [c for c in bilan['indetermines'] if c['contrainte'] == 'age_maternel']
    assert {c['personnes'] for c in ages if c['personnes'][0] == 'personne-isabeau'} == {('personne-isabeau', 'personne-' + i) for i, *_ in FAMILLE_1400[1:]}
    assert all(c['motif'].strip() for c in ages) and not any(c['contrainte'] == 'age_maternel' and c['personnes'][0] in ('personne-isabeau', 'personne-marie-bohun', 'personne-annabella') for c in bilan['verifies'])
    enfant = next(i for i, f in enumerate(document['familles']) if f['id'] == 'personne-charles')
    mere = next(i for i, f in enumerate(document['familles']) if f['id'] == 'personne-isabeau')
    mutations = [(('familles', enfant, 'pere'), 'inconnu'), (('familles', enfant, 'pere'), 'personne-charles'),
                 (('familles', enfant, 'mere'), 'personne-grande-3'), (('liens', r['personne-grande-28'], 'conjoints'), ['personne-jeanne'] * 2),
                 (('liens', r['personne-grande-28'], 'conjoints'), []),                  (('familles', enfant, 'naissance'), _naissance_famille('1368-12-03')),
                 (('familles', enfant, 'naissance'), _naissance_famille('1368-12-02'))]
    jean = next(i for i, f in enumerate(document['familles']) if f['id'] == 'personne-jean-viii')
    mutations += [(('familles', jean, 'naissance'), _naissance_famille(v)) for v in ('1350-06-27', '1350-06-26')]
    marguerite = next(i for i, f in enumerate(document['familles']) if f['id'] == 'personne-marguerite-autriche')
    mutations += [(('familles', marguerite, 'naissance'), _naissance_famille('1377-09-19'))]
    flandre = next(i for i, f in enumerate(document['familles']) if f['id'] == 'personne-marguerite-flandre')
    mutations += [(('familles', flandre, 'naissance'), _naissance_famille(v)) for v in ('1371-05-28', '1340-01-01')]
    nuremberg = next(i for i, f in enumerate(document['familles']) if f['id'] == EPOUSE_PAL)
    mutations += [(('familles', nuremberg, 'naissance'), _naissance_famille(v)) for v in ('1378-01-23', '1340-01-01')]
    valois = next(i for i, f in enumerate(document['familles']) if f['id'] == EPOUSE_BAR)
    # Marie de Valois placée après la naissance d'Édouard (juin 1377), puis assez tôt pour avoir 46 ans à la naissance de Jean (1380).
    mutations += [(('familles', valois, 'naissance'), _naissance_famille(v)) for v in ('1377-07-01', '1334-01-01')]
    copies = [_alterer_personnages(document, k, v) for k, v in mutations]
    cycle = copy.deepcopy(document)
    cycle['familles'][mere]['pere'] = 'personne-charles'
    cycle['familles'][mere]['sources']['pere'], cycle['familles'][mere]['lacunes']['pere'] = document['familles'][enfant]['sources']['pere'], None
    for f in cycle['familles']: f['naissance'] = {'valeur': 'inconnue', 'precision': 'vers'}
    copies.append(cycle)
    for age in (14, 15, 45, 46):
        d = copy.deepcopy(document)
        d['familles'][mere]['naissance'] = _naissance_famille(f'{1389-age}-11-09')
        for f in d['familles']:
            if f['mere'] == 'personne-isabeau': f['naissance'] = _naissance_famille('1389-11-09')
        if age in (14, 46): copies.append(d)
        else:
            assert lire(d)
            construit = World.charger(0)
            p.valider_personnages(construit.personnages, construit.chefs, construit.maisons, d, noms)
    for d in copies:
        personnes = copy.deepcopy(list(monde.personnages))
        for f in d['familles'] + d['liens']:
            cible = next(c for c in personnes if c['id'] == f['id'])
            cible.update({k: f[k] for k in ('naissance', 'pere', 'mere', 'conjoints') if k in f})
        with pytest.raises(ValueError): lire(d)
        with pytest.raises(ValueError): World.charger(0)
        with pytest.raises(ValueError): _controler_famille([f for f in personnes if 'pere' in f])
        with pytest.raises(ValueError): p.valider_personnages(personnes, monde.chefs, monde.maisons, document, noms)
    lire(document)
    def sentinelle(*a): raise RuntimeError('validateur familial appelé')
    monkeypatch.setattr(p, 'valider_liens_familiaux', sentinelle)
    for appel in (lambda: lire(document), lambda: World.charger(0)):
        with pytest.raises(RuntimeError, match='validateur familial appelé'): appel()
    monkeypatch.setattr(p, 'charger_catalogue', lambda *a: document)
    with pytest.raises(RuntimeError, match='validateur familial appelé'): p.construire_personnages(monde)
    monkeypatch.setattr(p, '_avec_familles', lambda *a: list(monde.personnages))
    with pytest.raises(RuntimeError, match='validateur familial appelé'):
        p.valider_personnages(monde.personnages, monde.chefs, monde.maisons, document, noms)


def _etats_historiques(etats):
    assert len(etats) == 29 and {e['maison'] for e in etats} == {'grande-' + i for i in ('1', '2', '3', '28', '29', '9', '4', '5', '6', '7', '8', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '22', '23', '25', '26', '27', '30')} | {BAR}
    assert {f'grande-{n}' for n in range(11, 21)} <= {e['maison'] for e in etats}
    for e in etats:
        if e['maison'] in BALKANS_MAISONS: _balkans(etat=e); continue
        if e['maison'] in MAGHREB_MAISONS: _maghreb(etat=e); continue
        if e['maison'] in MCA_MAISONS: _mca(etat=e); continue
        if e['maison'] == BOURGOGNE: _bourgogne(etat=e); continue
        if e['maison'] == PALATINAT: _palatinat(etat=e); continue
        if e['maison'] == BAR: _bar(etat=e); continue
        if e['maison'] == 'grande-16':
            _ottomans(etat=e); continue
        if e['maison'] == 'grande-15':
            _constantinople(etat=e); continue
        if e['maison'][7:] in VOISINS_CHEFS:
            _etats_voisins(e); continue
        if e['maison'] in ('grande-7', 'grande-8', 'grande-10'):
            _etats_fin(e); continue
        if e['maison'] in ('grande-4', 'grande-5', 'grande-6'):
            _etats_iberie(e); continue
        if e['maison'] in ('grande-1', 'grande-2'):
            _etats_iles(e); continue
        assert e['conjoints'] == 'union' and e['enfants'] == ('documentes' if e['maison'] == 'grande-3' else 'absence_attestee')
        assert e['lacunes'] == {'conjoints': None, 'enfants': None}
        assert set(e['sources']) == {'conjoints', 'enfants'} and all(s and s['url'] == 'https://en.wikipedia.org/wiki/' + {'grande-3': 'Charles_VI_of_France#Marriage_and_issue', 'grande-28': 'John_V_of_Brittany#Family', 'grande-9': 'Wenceslaus_IV_of_Bohemia#Personal_life'}[e['maison']] and s['fait'].strip() for s in e['sources'].values())
        assert set(e['exclusions']) == ({'Jeanne de Bavière'} if e['maison'] == 'grande-9' else set())
        if e['exclusions']:
            x = e['exclusions']['Jeanne de Bavière']
            assert '1386-12-31' in x['motif'] and x['sources'] and all(s['fait'].strip() for s in x['sources'])


def test_familles_historiques_etats():
    d, monde = _personnages(), World.charger(0)
    r = {f.get('id', f.get('maison')): i for t in ('familles', 'liens', 'etats') for i, f in enumerate(d[t])}
    _etats_historiques(d.get('etats', []))
    _etats_historiques([f['etat_familial'] for f in monde.personnages if 'etat_familial' in f])
    mutations = [(('etats',), d['etats'][:i] + d['etats'][i+1:]) for i in range(len(d['etats']))]
    sophie = next(i for i, f in enumerate(d['familles']) if f['id'] == 'personne-sophie-baviere')
    mutations += [(('familles',), [f for f in d['familles'] if f['id'] != 'personne-sophie-baviere']), (('familles',), d['familles'] + [d['familles'][sophie]])]
    mutations += [(('familles', sophie, k), v) for k, v in [('naissance', _naissance_famille('1376-01-01')), ('naissance', _naissance_famille('1377', 'annee')), ('conjoints', []), ('presence', 'decedee'), ('pere', 'personne-grande-9')]]
    mutations += [(('etats', r['grande-9'], k), v) for k, v in [('exclusions', {}), ('sources', {}), ('enfants', 'lacune')]]
    mutations += [(('etats', r['grande-9'], 'exclusions', 'Jeanne de Bavière', 'sources'), [])]
    mutations += [(('familles',), d['familles'] + [dict(d['familles'][sophie], id='personne-jeanne-baviere', nom='Jeanne de Bavière')])]
    for chemin, valeur in mutations:
        c = _alterer_personnages(d, chemin, valeur)
        with pytest.raises(AssertionError):
            _familles_historiques(c['familles'], c['liens'])
            _etats_historiques(c['etats'])
    for maison in ('grande-15', 'grande-16', 'grande-19'):
        for k in ('pere', 'mere', 'conjoints'):
            personnes = copy.deepcopy(list(monde.personnages))
            next(f for f in personnes if f['id'] == 'personne-' + maison)[k] = 'personne-grande-9'
            with pytest.raises(AssertionError): _familles_historiques([f for f in personnes if f['id'] != 'personne-' + f['maison']], [f for f in personnes if f['id'] == 'personne-' + f['maison'] and {'pere', 'mere', 'conjoints'} & f.keys()])


def test_familles_etats(tmp_path, monkeypatch):
    from sim import personnages as p
    from sim.noms import noms_depuis_monde
    d, monde = _personnages(), World.charger(0)
    r = {f.get('id', f.get('maison')): i for t in ('familles', 'liens', 'etats') for i, f in enumerate(d[t])}
    noms = {i: f for v in noms_depuis_monde(monde).values() for i, f in v['maisons'].items()}
    lecteur = p.charger_catalogue
    def lire(c):
        return lecteur(monde.maisons, _ecrire(tmp_path, c))
    assert lire(d) == d
    mutations = [(('etats',), []), (('etats',), d['etats'] * 2)]
    mutations += [(('etats', r['grande-28'], k), 'SUPPRIMER') for k in d['etats'][r['grande-28']]] + [(('etats', r['grande-28'], 'inconnu'), True)]
    mutations += [(('etats', r['grande-28'], k), v) for k, v in [('maison', 'inconnue'), ('maison', 'grande-21'), ('conjoints', 'celibat'), ('enfants', 'inconnus'), ('enfants', 'documentes'), ('conjoints', 'veuvage')]]
    mutations += [(('etats', r['grande-28'], 'sources', k), v) for k in ('conjoints', 'enfants') for v in (None, {}, {'url': 'ftp://exemple.org', 'fait': 'fait'})]
    mutations += [(('etats', r['grande-9'], 'exclusions', 'Jeanne de Bavière', k), v) for k, v in [('motif', ''), ('sources', []), ('sources', [{}])]]
    mutations += [(('familles', r['personne-charles'], 'presence'), 'absente'), (('liens', r['personne-grande-28'], 'presence'), 'indeterminee'), (('familles', r['personne-jeanne'], 'presence'), 'decedee'), (('familles', r['personne-charles'], 'naissance'), None)]
    for table, index in [('liens', r['personne-grande-9']), ('familles', r['personne-sophie-baviere'])]:
        mutations += [((table, index, 'conjoints'), []), ((table, index, 'presence'), 'decedee')]
    mutations += [(('etats', r['grande-3'], 'enfants'), 'absence_attestee')]
    copies = [_alterer_personnages(d, k, v) for k, v in mutations]
    # L'enfant contradictoire est déjà chef : aucune recherche limitée aux familles.
    c = copy.deepcopy(d)
    c['liens'][r['personne-grande-28']]['pere'], c['liens'][r['personne-grande-28']]['sources']['pere'], c['liens'][r['personne-grande-28']]['lacunes']['pere'] = 'personne-grande-9', d['liens'][r['personne-grande-9']]['sources']['presence'], None
    copies.append(c)
    for presence in ('decedee', 'indeterminee'):
        c = copy.deepcopy(d)
        c['familles'][r['personne-sophie-baviere']]['presence'] = presence
        if presence == 'indeterminee': c['familles'][r['personne-sophie-baviere']]['sources']['presence'], c['familles'][r['personne-sophie-baviere']]['lacunes']['presence'] = None, 'Page Sophie examinée : présence non établie sur cette copie.'
        copies.append(c)
    c = copy.deepcopy(d)
    for f in (c['familles'][r['personne-sophie-baviere']], c['liens'][r['personne-grande-9']]): f['conjoints'], f['sources']['conjoints'], f['lacunes']['conjoints'] = [], None, 'Union non intégrée sur cette copie.'
    copies.append(c)
    for c in copies:
        with pytest.raises(ValueError): lire(c)
        monkeypatch.setattr(p, 'CHEMIN', _ecrire(tmp_path, c))
        with pytest.raises(ValueError): p.construire_personnages(monde)
    # Copies non vides : inconnues explicites, présence décédée, veuvage et parent conservé.
    inconnu = copy.deepcopy(d)
    f = inconnu['familles'][r['personne-charles']]
    f['naissance'], f['sources']['naissance'], f['lacunes']['naissance'] = None, None, 'Naissance non établie dans la page Charles VI examinée.'
    lacunaire = copy.deepcopy(inconnu)
    f = lacunaire['familles'][r['personne-charles']]
    f['presence'], f['sources']['presence'], f['lacunes']['presence'] = 'indeterminee', None, 'Page Charles VI examinée ; présence au départ non établie sur cette copie.'
    for k in ('conjoints', 'enfants'):
        lacunaire['etats'][r['grande-28']][k], lacunaire['etats'][r['grande-28']]['sources'][k], lacunaire['etats'][r['grande-28']]['lacunes'][k] = 'lacune', None, 'Couverture non étudiée sur cette copie.'
    veuf = copy.deepcopy(d)
    veuf['familles'][r['personne-isabeau']]['presence'] = 'decedee'
    for f in (veuf['familles'][r['personne-isabeau']], veuf['liens'][r['personne-grande-3']]):
        f['conjoints'], f['sources']['conjoints'], f['lacunes']['conjoints'] = [], None, 'Union terminée sur cette copie.'
    veuf['etats'][r['grande-3']]['conjoints'] = 'veuvage'
    for c in (inconnu, lacunaire, veuf):
        assert lire(c) == c
        monkeypatch.setattr(p, 'charger_catalogue', lambda *a: c)
        avant = copy.deepcopy(c)
        personnes, chefs = p.construire_personnages(monde)
        assert c == avant
        p.valider_personnages(personnes, chefs, monde.maisons, c, noms)
        copie = copy.copy(monde)
        copie.personnages, copie.chefs = personnes, chefs
        assert copie.to_dict()['personnages'] == list(personnes)
        if c is inconnu:
            assert next(f for f in copie.to_dict()['personnages'] if f['id'] == 'personne-charles')['naissance'] is None
            assert any('personne-charles' in x['personnes'] and x['motif'] for x in p._controler_liens(personnes)['indetermines'])
        for i, f in enumerate(personnes):
            if 'presence' not in f: continue
            for k in ('presence', 'etat_familial', 'lacunes', 'sources', 'naissance'):
                if k not in f: continue
                alterees = copy.deepcopy(list(personnes)); alterees[i][k] = 'Altéré'
                with pytest.raises(ValueError): p.valider_personnages(alterees, chefs, monde.maisons, c, noms)
    for c, chemin, valeur in [(inconnu, ('familles', r['personne-charles'], 'lacunes', 'naissance'), ''), (inconnu, ('familles', r['personne-charles'], 'sources', 'naissance'), d['familles'][r['personne-charles']]['sources']['naissance']), (lacunaire, ('familles', r['personne-charles'], 'lacunes', 'presence'), ''), (lacunaire, ('etats', r['grande-28'], 'lacunes', 'enfants'), '')]:
        with pytest.raises(ValueError): p.valider_catalogue(_alterer_personnages(c, chemin, valeur), monde.maisons)


def _etats_iles(e):
    anglais = e['maison'] == 'grande-1'
    assert (e['conjoints'], e['enfants'], e['lacunes']) == ('veuvage' if anglais else 'union', 'documentes', {'conjoints': None, 'enfants': None})
    assert set(e['sources']) == {'conjoints', 'enfants'}
    for source in e['sources'].values():
        assert source['url'] == 'https://en.wikipedia.org/wiki/' + ('Henry_IV_of_England#Marriages_and_issue' if anglais else 'Robert_III_of_Scotland#Family_and_issue')
        assert ('Henri IV' if anglais else 'Robert III') in source['fait']
    attendus = {'Jeanne de Navarre': ('1403-02-07', 'Henry_IV_of_England'), 'Edmund Leborde': ('1401', 'Henry_IV_of_England')} if anglais else {'Robert Stuart': ('1393', 'Annabella_Drummond'), 'Egidia Stuart': ('1417', 'p10533.htm'), 'Jacques de Kilbride': ('sans dates', 'p10533.htm')}
    assert set(e['exclusions']) == set(attendus)
    for nom, (repere, page) in attendus.items():
        x = e['exclusions'][nom]
        assert nom in x['motif'] and repere in x['motif'] and 'départ' in x['motif']
        assert x['sources'] and all(s['url'].startswith('https://') and s['fait'].strip() for s in x['sources'])
        assert any(page in s['url'] for s in x['sources'])
        if not anglais:
            assert 'indéterminée' in x['motif'] and 'Robert III' in x['motif']
            assert len(x['sources']) >= 2 and any('Robert_III_of_Scotland' in s['url'] for s in x['sources'])
            if nom == 'Robert Stuart': assert all(v in ' '.join(s['fait'] for s in x['sources']) for v in ('après 1393', 'vers 1393'))
            if nom == 'Egidia Stuart': assert all(v in ' '.join(s['fait'] for s in x['sources']) for v in ('1417', 'morte jeune', 'naissance'))


def test_familles_historiques_iles():
    d = _personnages()
    _familles_historiques(d['familles'], d['liens']); _etats_historiques(d['etats'])
    for t, preuve in [('familles', lambda c: _familles_historiques(c['familles'], c['liens'])), ('liens', lambda c: _familles_historiques(c['familles'], c['liens'])), ('etats', lambda c: _etats_historiques(c['etats']))]:
        mutations = []
        for i, f in enumerate(d[t]):
            mutations += [((t, i, k), v) for k, v in ([('sources', {}), ('lacunes', {}), ('presence', 'decedee')] if t != 'etats' else [('sources', {}), ('enfants', 'lacune'), ('conjoints', 'lacune')])]
            if t != 'etats':
                mutations += [((t, i, 'mere'), 'personne-annabella'), ((t, i, 'conjoints'), ['personne-grande-1'])]
                mutations += [((t, i, 'sources', k), None) for k, v in f['sources'].items() if v]
                if f['id'] == 'personne-henri-monmouth': mutations += [((t, i, 'sources', 'naissance', 'fait'), 'Henri de Monmouth : naissance 1386 probable.')]
                mutations += [((t, i, 'sources', k, 'fait'), 'Parenté documentée.') for k in ('pere', 'mere') if f['sources'][k]]
                mutations += [((t, i, 'lacunes', k), 'Absence attestée.') for k, v in f['lacunes'].items() if v]
            else:
                for nom in f['exclusions']:
                    mutations += [((t, i, 'exclusions', nom), 'SUPPRIMER')]
                    mutations += [((t, i, 'exclusions', nom, k), v) for k, v in [('motif', ''), ('sources', [])]]
        for chemin, valeur in mutations:
            if chemin[-1] == 'presence' and d[t][chemin[1]]['presence'] == valeur: valeur = 'vivante'
            if t == 'etats' and chemin[-1] in ('enfants', 'conjoints') and d[t][chemin[1]][chemin[-1]] == valeur: valeur = 'absence_attestee' if chemin[-1] == 'enfants' else 'veuvage'
            if chemin[-1] == 'mere' and d[t][chemin[1]]['mere'] == valeur: valeur = 'personne-marie-bohun'
            with pytest.raises(AssertionError): preuve(_alterer_personnages(d, chemin, valeur))
    monmouth = next(i for i, f in enumerate(d['familles']) if f['id'] == 'personne-henri-monmouth')
    for date, precision in [('1386', 'annee'), ('1387', 'annee'), ('1386-09-16', 'jour'), ('1386', 'intervalle'), ('1387', 'intervalle')]:
        c = _alterer_personnages(d, ('familles', monmouth, 'naissance'), _naissance_famille(date, precision))
        with pytest.raises(AssertionError): _familles_historiques(c['familles'], c['liens'])
    for nom in ('Edmund Leborde', 'Robert Stuart', 'Egidia Stuart', 'Jacques de Kilbride', 'Jeanne de Navarre'):
        c = copy.deepcopy(d); f = copy.deepcopy(next(f for f in c['familles'] if f['id'] == 'personne-jean-ardgowan'))
        f.update(id='personne-intruse', nom=nom)
        if nom == 'Jeanne de Navarre':
            f.update(maison='grande-1', pere=None, mere=None, conjoints=['personne-grande-1'])
            next(l for l in c['liens'] if l['id'] == 'personne-grande-1')['conjoints'] = [f['id']]
            next(e for e in c['etats'] if e['maison'] == 'grande-1')['conjoints'] = 'union'
            for enfant in c['familles']:
                if enfant['pere'] == 'personne-grande-1': enfant['mere'] = f['id']
        c['familles'].append(f)
        assert _controler_famille(c['familles'] + [{**h, **l} for l in c['liens'] for h in c['chefs'] if l['id'] == 'personne-' + h['maison']])
        with pytest.raises(AssertionError): _familles_historiques(c['familles'], c['liens'])
    for enfant in ILES_1400[1:7]:
        c = copy.deepcopy(d); next(f for f in c['familles'] if f['id'] == 'personne-' + enfant[0])['mere'] = 'personne-jeanne'
        with pytest.raises(AssertionError): _familles_historiques(c['familles'], c['liens'])


def test_familles_historiques_iberie():
    d = _personnages()
    _familles_historiques(d['familles'], d['liens']); _etats_historiques(d['etats'])
    def preuve(c): _familles_historiques(c['familles'], c['liens'])
    def resoudre(c):
        return _controler_famille(c['familles'] + [{**h, **l} for l in c['liens'] for h in c['chefs'] if l['id'] == 'personne-' + h['maison']])
    r = {f['id'][9:]: i for i, f in enumerate(d['familles'])}
    mutations = [(('familles', r['afonso-portugal'], 'presence'), 'decedee'), (('familles', r['ines-pires'], 'presence'), 'vivante'), (('familles', r['ines-pires'], 'presence'), 'decedee')]
    mutations += [(('familles', r[i], 'mere'), 'personne-philippa-lancastre') for i in ('afonso-bragance', 'beatrice-portugal')]
    for i, dates in [('catherine-lancastre', [('1372-06-06', 'jour'), ('1373-03-31', 'jour'), ('1372-06-06', 'intervalle'), ('1373-03-31', 'intervalle')]), ('martin-sicile', [('1374', 'annee'), ('1376', 'annee'), ('1374-01-01', 'jour'), ('1374/1376', 'vers')]), ('maria-luna', [('1358', 'annee'), ('1358', 'vers')])]:
        mutations += [(('familles', r[i], 'naissance'), _naissance_famille(date, precision)) for date, precision in dates]
        mutations += [(('familles', r[i], 'sources', 'naissance', 'fait'), v) for v in ('Naissance connue.', next(n + ' : naissance ' + date for ident, n, date, *_ in IBERIE_1400 if ident == i))]
    mutations += [(('familles',), d['familles'] + [d['familles'][r[i]]]) for i, *_ in IBERIE_1400]
    mutations += [(('liens',), d['liens'][:i] + d['liens'][i+1:]) for i in range(len(d['liens']))]
    mutations += [(('liens',), d['liens'] + [d['liens'][i]]) for i in range(len(d['liens']))]
    for chemin, valeur in mutations:
        with pytest.raises(AssertionError): preuve(_alterer_personnages(d, chemin, valeur))
    c = copy.deepcopy(d); c['familles'].pop(r['afonso-portugal'])
    assert resoudre(c)
    with pytest.raises(AssertionError): preuve(c)  # Les deux Afonso ne se fusionnent pas.
    for nom, modele in [('Jean de Portugal', 'afonso-portugal'), ('Blanche de Portugal', 'afonso-portugal'), ('Ferdinand de Portugal', 'afonso-portugal'), ('Marie de Castille', 'afonso-portugal'), ('Catherine de Castille', 'afonso-portugal'), ('Jean de Castille', 'afonso-portugal'), ('Jacques d’Aragon', 'martin-sicile'), ('Jean d’Aragon', 'martin-sicile'), ('Marguerite d’Aragon', 'martin-sicile'), ('Marguerite de Prades', 'maria-luna')]:
        c = copy.deepcopy(d); f = dict(copy.deepcopy(c['familles'][r[modele]]), id='personne-intruse', nom=nom)
        if 'Castille' in nom: f.update(maison='grande-5', pere='personne-grande-5', mere='personne-catherine-lancastre')
        if nom == 'Marguerite de Prades': next(l for l in c['liens'] if l['id'] == 'personne-grande-6')['conjoints'].append(f['id'])
        c['familles'].append(f)
        assert resoudre(c)
        with pytest.raises(AssertionError): preuve(c)
    c = copy.deepcopy(d); f = c['familles'][r['ines-pires']]
    f.update(presence='vivante', conjoints=['personne-grande-4'])
    next(l for l in c['liens'] if l['id'] == 'personne-grande-4')['conjoints'].append(f['id'])
    assert resoudre(c)
    with pytest.raises(AssertionError): preuve(c)
    aragon = next(i for i, e in enumerate(d['etats']) if e['maison'] == 'grande-6')
    for nom in ('Jacques d’Aragon', 'Jean d’Aragon', 'Marguerite d’Aragon'):
        for source in range(2):
            c = copy.deepcopy(d); c['etats'][aragon]['exclusions'][nom]['sources'].pop(source)
            with pytest.raises(AssertionError): _etats_historiques(c['etats'])
    for t in ([], d['etats'] + [d['etats'][0]]):
        with pytest.raises(AssertionError): _etats_historiques(t)


# Relevés indépendants : notices des parents, BOE 436–438, Auñamendi et Germán de Pamplona.
WIKI_FIN = 'https://en.wikipedia.org/wiki/'
BOE_FIN = 'https://www.boe.es/biblioteca_juridica/abrir_pdf.php?id=PUB-DH-2021-233'
JUMELLES_FIN = 'https://dialnet.unirioja.es/descarga/articulo/2240758.pdf'
LEBREL_FIN = 'https://www.lebrelblanco.com/old/anexos/a0177.htm'
LANCELOT_FIN = 'https://aunamendi.eusko-ikaskuntza.eus/en/lancelot-de-navarra/ar-84786/'
AGNESE_FIN = 'https://www.treccani.it/enciclopedia/mantegazza/'
FIN_1400 = [
    ('eleonore-castille', 'Éléonore de Castille', 'vers 1363', 'vers', 'Eleanor_of_Castile,_Queen_of_Navarre', '1415/1416', '7', None),
    ('jeanne-foix', 'Jeanne de Navarre (Foix)', '1382', 'annee', 'Charles_III_of_Navarre#Issue', '1413', '7', 'eleonore-castille'),
    ('marie-navarre', 'Marie de Navarre', '1383 ou 1384', 'intervalle', 'Charles_III_of_Navarre#Issue', '1406', '7', 'eleonore-castille'),
    ('blanche-navarre', 'Blanche de Navarre', '1385 ou 1386', 'intervalle', 'Charles_III_of_Navarre#Issue', '1441', '7', 'eleonore-castille'),
    ('beatrice-navarre', 'Béatrice de Navarre', '1386 ou 1392', 'intervalle', 'Charles_III_of_Navarre#Issue', '1407/1412', '7', 'eleonore-castille'),
    ('isabelle-navarre', 'Isabelle de Navarre', '1395 ou 1396', 'intervalle', 'Charles_III_of_Navarre#Issue', '1435', '7', 'eleonore-castille'),
    ('charles-navarre', 'Charles de Navarre', '1397', 'annee', 'Charles_III_of_Navarre#Issue', '1402', '7', 'eleonore-castille'),
    ('lancelot-navarre', 'Lancelot de Navarre', '1386-04', 'mois', LANCELOT_FIN, '1420', '7', 'maria-esparza'),
    ('godofre-navarre', 'Godofre de Navarre', '1384 ou 1394', 'intervalle', BOE_FIN, '1439', '7', 'teresa-navarre'),
    ('jeanne-zuniga', 'Jeanne de Navarre (Zúñiga)', 'vers 1380', 'vers', BOE_FIN, '1414', '7', None),
    ('maria-esparza', 'María Miguel de Esparza', None, None, LANCELOT_FIN, None, '7', None),
    ('teresa-navarre', 'Teresa', None, None, BOE_FIN, None, '7', None),
    ('caterina-visconti', 'Caterina Visconti', '1361', 'annee', 'Caterina_Visconti', '1404', '10', None),
    ('isabelle-vertus', 'Isabelle de Valois (Vertus)', '1348-10-01', 'jour', 'Isabella,_Countess_of_Vertus', '1372/1373', '10', None),
    ('valentine-visconti', 'Valentine Visconti', '1371', 'annee', 'Valentina_Visconti,_Duchess_of_Orléans', '1408', '10', 'isabelle-vertus'),
    ('gian-maria', 'Gian Maria Visconti', '1388-09-07', 'jour', 'Caterina_Visconti', '1412', '10', 'caterina-visconti'),
    ('filippo-maria', 'Filippo Maria Visconti', '1392-09', 'mois', 'Caterina_Visconti', '1447', '10', 'caterina-visconti'),
    ('gabriele-maria', 'Gabriele Maria Visconti', '1385 ou 1386', 'intervalle', 'Gabriele_Maria_Visconti', '1408', '10', 'agnese-mantegazza'),
    ('agnese-mantegazza', 'Agnese Mantegazza', None, None, AGNESE_FIN, None, '10', None)]
FIN_ENFANTS = {i for i, _, _, _, _, _, _, mere in FIN_1400 if mere} | {'jeanne-zuniga'}
FIN_CHEFS = {'7': ('Charles III', 'Charles_III_of_Navarre#Issue', 'eleonore-castille', '1375', '1425'),
             '8': ('Muhammad VII', 'Muhammad_VII_of_Granada', None, None, '1408'),
             '10': ('Jean Galéas', 'Gian_Galeazzo_Visconti#Marriage_and_issue', 'caterina-visconti', '1380-10-02', '1402')}
FIN_DIVERGENCES = {'eleonore-castille': ('1363', 'approximation'), 'marie-navarre': ('1383', '1384'),
    'blanche-navarre': ('1385', '1386', JUMELLES_FIN, 'hypothèse'), 'beatrice-navarre': ('1386', '1392', JUMELLES_FIN, 'hypothèse'),
    'isabelle-navarre': ('1395', '1396', JUMELLES_FIN), 'lancelot-navarre': ('avril 1386', 'circa 15', BOE_FIN, 'approximation'),
    'godofre-navarre': ('1384', '1394', LEBREL_FIN), 'jeanne-zuniga': ('1380', 'approximation'),
    'filippo-maria': ('3', '23', '1392', WIKI_FIN + 'Gian_Galeazzo_Visconti#Marriage_and_issue'),
    'gabriele-maria': ('1385', '1386', 'seize ans', '1402', 'indéterminée')}
FIN_EXCLUSIONS = {
    '7': {'Louis de Navarre': (BOE_FIN, WIKI_FIN + 'Charles_III_of_Navarre#Issue', '1399', '1402', 'indéterminée'),
          'Marguerite de Navarre': (LEBREL_FIN, BOE_FIN, JUMELLES_FIN, '1390', '1402', '1403', 'indéterminée'),
          'Jumelle non identifiée': (WIKI_FIN + 'Charles_III_of_Navarre#Issue', JUMELLES_FIN, 'morte jeune', 'hypothèse'),
          'Jeanne de Navarre (Beaumont)': (BOE_FIN, LEBREL_FIN, '438', '1419', 'future'),
          'Francés de Navarre': (BOE_FIN, LEBREL_FIN, '438', '1418', '1421', 'naissance inconnue', 'indéterminée'),
          'Pascual de Navarre': (LEBREL_FIN, '1395', 'indéterminée')},
    '8': {}, '10': {'Gian Galeazzo, fils d’Isabelle': (WIKI_FIN + 'Gian_Galeazzo_Visconti#Marriage_and_issue', '1376'),
          'Azzone Visconti': (WIKI_FIN + 'Gian_Galeazzo_Visconti#Marriage_and_issue', '1381'),
          'Carlo Visconti': (WIKI_FIN + 'Gian_Galeazzo_Visconti#Marriage_and_issue', '1374'),
          'Fille de Caterina': (WIKI_FIN + 'Caterina_Visconti', '1385-07-09'),
          'Antonio Visconti': ('https://it.wikipedia.org/wiki/Antonio_Visconti', WIKI_FIN + 'Gian_Galeazzo_Visconti', '1391', 'homonymes')}}


def _fin_historiques(fiches):
    noms = {i: nom for i, nom, *_ in FIN_1400}
    for i, nom, date, precision, page, fin, maison, mere in FIN_1400:
        f = fiches['personne-' + i]; chef, lien, epouse, union, _ = FIN_CHEFS[maison]
        assert set(f['sources']) == set(f['lacunes']) == {'identite', 'naissance', 'presence', 'pere', 'mere', 'conjoints'}
        assert (f['nom'], f['maison'], f['naissance'], f['pere'], f['mere'], f['conjoints'], f['presence']) == (nom, 'grande-' + maison, _naissance_famille(date, precision), 'personne-grande-' + maison if i in FIN_ENFANTS else None, 'personne-' + mere if mere else None, ['personne-grande-' + maison] if i == epouse else [], 'indeterminee' if fin is None else 'decedee' if i == 'isabelle-vertus' else 'vivante')
        for k in f['sources']:
            source, lacune = f['sources'][k], f['lacunes'][k]
            if (k == 'presence' and fin is None) or (k == 'naissance' and date is None):
                assert source is None and lacune and page in lacune and nom in lacune and ('indéterminée' if k == 'presence' else 'inconnue') in lacune
                if k == 'presence': assert 'ne départagent ni vie ni décès' in lacune and all(url in lacune for url in ((BOE_FIN, LEBREL_FIN) if i == 'teresa-navarre' else (page,)))
                continue
            if k in ('identite', 'naissance', 'presence') or f[k]:
                url = (page if page.startswith('https:') else WIKI_FIN + page) if k in ('identite', 'naissance', 'presence') else (BOE_FIN if i in ('godofre-navarre', 'jeanne-zuniga') else LANCELOT_FIN if i == 'lancelot-navarre' else WIKI_FIN + 'Gabriele_Maria_Visconti' if i == 'gabriele-maria' else WIKI_FIN + lien)
                assert source and source['url'] == url
                assert nom in source['fait'] and lacune is None
                if k == 'naissance': assert all(v in source['fait'] for v in FIN_DIVERGENCES.get(i, (date,)))
                if k == 'presence': assert all(v in source['fait'] for v in fin.split('/'))
                if k in ('pere', 'mere'): assert chef in source['fait'] and (noms[mere] if mere else 'mère inconnue') in source['fait']
                if k == 'conjoints': assert chef in source['fait'] and union in source['fait']
                if k == 'presence' and i == 'isabelle-vertus': assert WIKI_FIN + 'Caterina_Visconti' in source['fait']
            else: assert source is None and lacune and ('inconnue' in lacune if i == 'jeanne-zuniga' and k == 'mere' else 'aucune absence attestée' in lacune)
    for maison, (nom, page, epouse, union, fin) in FIN_CHEFS.items():
        f = fiches['personne-grande-' + maison]
        assert {'pere', 'mere', 'conjoints', 'presence'} <= f['sources'].keys() & f['lacunes'].keys()
        assert (f['pere'], f['mere'], f['conjoints'], f['presence']) == (None, None, ['personne-' + epouse] if epouse else [], 'vivante')
        for k in ('pere', 'mere', 'conjoints', 'presence'):
            source, lacune = f['sources'][k], f['lacunes'][k]
            if k == 'presence' or (k == 'conjoints' and epouse):
                assert source and source['url'] == WIKI_FIN + page and lacune is None and nom in source['fait'] and all(v in source['fait'] for v in ((union, noms[epouse]) if k == 'conjoints' else (fin,)))
            else: assert source is None and lacune and 'aucune absence attestée' in lacune


def _etats_fin(e):
    maison = e['maison'][7:]; nom, page, epouse, union, _ = FIN_CHEFS[maison]
    assert set(e['sources']) == set(e['lacunes']) == {'conjoints', 'enfants'}
    assert (e['conjoints'], e['enfants']) == (('lacune', 'lacune') if maison == '8' else ('union', 'documentes'))
    for k in ('conjoints', 'enfants'):
        if maison == '8':
            assert e['sources'][k] is None and e['lacunes'][k] and all(v in e['lacunes'][k] for v in (WIKI_FIN + page, WIKI_FIN + 'Yusuf_III_of_Granada', '1408', '1400', 'identités', 'naissances')); continue
        assert e['lacunes'][k] is None and e['sources'][k] and e['sources'][k]['url'] == WIKI_FIN + page
        assert nom in e['sources'][k]['fait']
        assert all(v in e['sources'][k]['fait'] for v in ([union, next(n for i, n, *_ in FIN_1400 if i == epouse)] if k == 'conjoints' else [n for i, n, _, _, _, _, m, _ in FIN_1400 if m == maison and i in FIN_ENFANTS]))
    assert set(e['exclusions']) == set(FIN_EXCLUSIONS[maison])
    for nom, reperes in FIN_EXCLUSIONS[maison].items():
        x = e['exclusions'][nom]; pages = {v for v in reperes if v.startswith('https:')}
        assert x['sources'] and {s['url'] for s in x['sources']} == pages and nom in x['motif'] and all(v in x['motif'] for v in reperes if v not in pages)
        assert all(nom in s['fait'] and s['fait'].strip() for s in x['sources'])
        assert all(any(v in s['fait'] for s in x['sources']) for v in reperes if v not in pages)


def test_familles_historiques_fin():
    d = _personnages(); _familles_historiques(d['familles'], d['liens']); _etats_historiques(d['etats'])
    def preuve(c): _familles_historiques(c['familles'], c['liens'])
    for t in ('familles', 'liens'):
        for j, f in enumerate(d[t]):
            if f['id'] not in {'personne-' + i for i, *_ in FIN_1400} | {'personne-grande-' + m for m in FIN_CHEFS}: continue
            mutations = [((t, j, 'nom'), 'Homonyme')] if t == 'familles' else []
            if t == 'familles': mutations += [((t,), d[t] + [f]), ((t, j, 'naissance'), _naissance_famille('1385'))]
            mutations += [((t, j, 'sources', k, 'fait'), 'Fait sans personnes ni divergence.') for k, v in f['sources'].items() if v]
            mutations += [((t, j, 'lacunes', k), '') for k, v in f['lacunes'].items() if v]
            mutations += [((t, j, 'lacunes', k), v.replace(url, '')) for k, v in f['lacunes'].items() if v for url in (BOE_FIN, LEBREL_FIN, LANCELOT_FIN, AGNESE_FIN) if url in v and k in ('presence', 'naissance')]
            for chemin, valeur in mutations:
                with pytest.raises(AssertionError): preuve(_alterer_personnages(d, chemin, valeur))
    r = {f['id'][9:]: j for j, f in enumerate(d['familles'])}
    for i, mere in [('lancelot-navarre', 'eleonore-castille'), ('godofre-navarre', 'eleonore-castille'), ('jeanne-zuniga', 'maria-esparza'), ('valentine-visconti', 'caterina-visconti'), ('gabriele-maria', 'caterina-visconti')]:
        with pytest.raises(AssertionError): preuve(_alterer_personnages(d, ('familles', r[i], 'mere'), 'personne-' + mere))
    for i, _, date, precision, *_ in FIN_1400:
        if i not in FIN_DIVERGENCES: continue
        for repere in FIN_DIVERGENCES[i]:
            c = _alterer_personnages(d, ('familles', r[i], 'sources', 'naissance', 'fait'), d['familles'][r[i]]['sources']['naissance']['fait'].replace(repere, 'inconnu'))
            with pytest.raises(AssertionError): preuve(c)
        for valeur in date.replace(' ou ', '/').split('/'):
            if precision == 'mois': valeur += '-03'
            with pytest.raises(AssertionError): preuve(_alterer_personnages(d, ('familles', r[i], 'naissance'), _naissance_famille(valeur, 'jour' if len(valeur) == 10 else 'annee')))
    for i in ('jeanne-foix', 'jeanne-zuniga'):
        c = copy.deepcopy(d); c['familles'].pop(r[i])
        with pytest.raises(AssertionError): preuve(c)
    for role in ('pere', 'conjoints'):
        c = copy.deepcopy(d); f = dict(copy.deepcopy(c['familles'][r['jeanne-zuniga']]), id='personne-inventee', maison='grande-8', pere=None)
        f[role] = 'personne-grande-8' if role == 'pere' else ['personne-grande-8']
        if role == 'conjoints': next(l for l in c['liens'] if l['id'] == 'personne-grande-8')['conjoints'] = [f['id']]
        c['familles'].append(f)
        assert _controler_famille(c['familles'] + [{**h, **l} for l in c['liens'] for h in c['chefs'] if l['id'] == 'personne-' + h['maison']])
        with pytest.raises(AssertionError): preuve(c)
    for i in ('maria-esparza', 'teresa-navarre', 'agnese-mantegazza', 'isabelle-vertus'):
        c = copy.deepcopy(d); f = c['familles'][r[i]]; chef = 'personne-grande-' + ('7' if i in ('maria-esparza', 'teresa-navarre') else '10')
        f.update(presence='vivante', conjoints=[chef]); next(l for l in c['liens'] if l['id'] == chef)['conjoints'].append(f['id'])
        assert _controler_famille(c['familles'] + [{**h, **l} for l in c['liens'] for h in c['chefs'] if l['id'] == 'personne-' + h['maison']])
        with pytest.raises(AssertionError): preuve(c)
    for maison in FIN_CHEFS:
        j = next(j for j, e in enumerate(d['etats']) if e['maison'] == 'grande-' + maison)
        for nom, x in d['etats'][j]['exclusions'].items():
            for chemin, valeur in [(('exclusions', nom), 'SUPPRIMER'), (('exclusions', nom, 'motif'), ''), *[(('exclusions', nom, 'sources'), x['sources'][:a] + x['sources'][a+1:]) for a in range(len(x['sources']))]]:
                with pytest.raises(AssertionError): _etats_historiques(_alterer_personnages(d, ('etats', j, *chemin), valeur)['etats'])
            c = copy.deepcopy(d); f = dict(copy.deepcopy(c['familles'][r['charles-navarre' if maison == '7' else 'gian-maria']]), id='personne-intruse', nom=nom); c['familles'].append(f)
            assert _controler_famille(c['familles'] + [{**h, **l} for l in c['liens'] for h in c['chefs'] if l['id'] == 'personne-' + h['maison']])
            with pytest.raises(AssertionError): preuve(c)
        if maison == '8':
            for k in ('conjoints', 'enfants'):
                for chemin, valeur in [((k,), 'veuvage' if k == 'conjoints' else 'absence_attestee'), (('lacunes', k), ''), *[(('lacunes', k), d['etats'][j]['lacunes'][k].replace(WIKI_FIN + page, '')) for page in ('Muhammad_VII_of_Granada', 'Yusuf_III_of_Granada')]]:
                    with pytest.raises(AssertionError): _etats_historiques(_alterer_personnages(d, ('etats', j, *chemin), valeur)['etats'])


# Notices examinées le 22 octobre 2026 ; attentes indépendantes du catalogue.
NAPLES = 'https://en.wikipedia.org/wiki/Ladislaus_of_Naples#Marriages_and_issue'
TRECCANI = "https://www.treccani.it/enciclopedia/ladislao-d-angio-durazzo-re-di-sicilia_(Dizionario-Biografico)/"
MARIE_SAVOIE = 'https://en.wikipedia.org/wiki/Mary_of_Burgundy,_Duchess_of_Savoy'
AMEDEE = 'https://fr.wikipedia.org/wiki/Am%C3%A9d%C3%A9e_VIII#Mariage_et_enfants'
FMG_SAVOIE = 'https://fmg.ac/Projects/MedLands/SAVOY.htm'
ERIC = 'https://en.wikipedia.org/wiki/Erik_of_Pomerania#Marriage'
PHILIPPA = 'https://en.wikipedia.org/wiki/Philippa_of_England'
JAGELLON = 'https://en.wikipedia.org/wiki/W%C5%82adys%C5%82aw_II_Jagie%C5%82%C5%82o'
FAMILLE_JAGELLON = 'https://en.wikipedia.org/wiki/Family_of_Jogaila'
VOISINS_CHEFS = {'11': ('Ladislas', NAPLES, '1414', None), '12': ('Amédée VIII', AMEDEE, '1451', 'marie-bourgogne'),
                 '13': ('Éric', ERIC, '1459', None), '14': ('Ladislas II Jagellon', JAGELLON, '1434', None)}
UNION_SAVOIE = ('Amédée VIII', 'Marie de Bourgogne', '1386', '1393-10-30', 'procuration', '1401', '1403', AMEDEE)
VOISINS_LACUNES = {('11', 'conjoints'): (NAPLES, TRECCANI, 'Costanza', 'annulée', '1392', '1393', '1402', '1403', '1406', 'schéma', 'veuvage'),
    ('11', 'enfants'): (NAPLES, TRECCANI, 'Rinaldo', 'Marie de Durazzo', 'hors mariage', 'présence indéterminée', 'dates', 'mères', 'aucune absence attestée'),
    ('12', 'enfants'): (MARIE_SAVOIE, AMEDEE, FMG_SAVOIE, 'deux enfants', '403', 'non aboutie', 'aucune absence attestée'),
    ('13', 'conjoints'): (ERIC, 'Philippa', 'Cecilia', '1402', '1406-10-26', '1430', 'schéma', 'célibat'),
    ('13', 'enfants'): (ERIC, PHILIPPA, 'mort-né', '1430', 'antérieurs', 'aucune absence attestée')}
VOISINS_EXCLUSIONS = {
    '11': {'Costanza Chiaramonte': (NAPLES, TRECCANI, '1392', '1393', 'annulée'),
        'Marie de Lusignan': (NAPLES, TRECCANI, '1402', '1403', 'future'), 'Marie d’Enghien': (NAPLES, '1406', 'future'),
        'Fille de Bayezid': (NAPLES, TRECCANI, '1393', 'projet', 'jamais réalisée'),
        'Rinaldo de Durazzo': (NAPLES, 'Reynold', 'hors mariage', 'présence indéterminée', 'dates', 'mère'),
        'Marie de Durazzo': (NAPLES, 'hors mariage', 'présence indéterminée', 'dates', 'mère')},
    '12': {nom: (MARIE_SAVOIE, AMEDEE, *dates, 'future') for nom, dates in [
        ('Marguerite I de Savoie', ('1405',)), ('Antoine I de Savoie', ('1407',)), ('Antoine II de Savoie', ('1408',)),
        ('Marie de Savoie', ('1411',)), ('Amédée de Savoie', ('1412',)), ('Louis de Savoie', ('1413',)),
        ('Bonne de Savoie', ('1415',)), ('Philippe de Savoie', ('1417', '1422')), ('Marguerite II de Savoie', ('1420',))]},
    '13': {'Philippa d’Angleterre': (ERIC, '1402', '1406-10-26', 'future'), 'Cecilia': (ERIC, '1430', 'future'),
        'Fils mort-né de Philippa': (PHILIPPA, '1430', 'future', 'mort-né')},
    '14': {'Jadwiga de Pologne': (FAMILLE_JAGELLON, JAGELLON, '1399-07-17', 'décédée'),
        'Élisabeth Bonifacia': (FAMILLE_JAGELLON, JAGELLON, '1399-06-22', '1399-07-13', 'décédée'),
        **{nom: (FAMILLE_JAGELLON, JAGELLON, date, 'future') for nom, date in [('Anne de Cilli', '1402'),
            ('Élisabeth de Pilica', '1417'), ('Sophie de Holszany', '1422'), ('Jadwiga Jagellon', '1408'),
            ('Ladislas III', '1424'), ('Casimir', '1426'), ('Casimir André', '1427')]}}}


def _reperes_voisins(texte, reperes):
    assert texte and all(v in texte for v in reperes)


def _voisins_historiques(fiches):
    for i, nom, page, fin, epouse in [('marie-bourgogne', 'Marie de Bourgogne', MARIE_SAVOIE, '1422/1428', 'grande-12')] + [
            ('grande-' + m, *v) for m, v in VOISINS_CHEFS.items()]:
        f = fiches['personne-' + i]
        if i == 'marie-bourgogne':
            assert (f['nom'], f['maison'], f['naissance']) == (nom, 'grande-12', _naissance_famille('1386', 'annee'))
        assert (f['pere'], f['mere'], f['conjoints'], f['presence']) == (*((CHEF_BG, EPOUSE_BG) if i == 'marie-bourgogne' else (None, None)), ['personne-' + epouse] if epouse else [], 'vivante')
        champs = {'pere', 'mere', 'conjoints', 'presence'} | ({'identite', 'naissance'} if i == 'marie-bourgogne' else set())
        assert set(f['sources']) == set(f['lacunes']) == champs | ({'identite', 'naissance'} if 'nom' in f else set())
        for k in champs:
            source, lacune = f['sources'][k], f['lacunes'][k]
            if i == 'marie-bourgogne' and k in ('pere', 'mere'):
                assert source and lacune is None  # contenu exact : _bourgogne
            elif k in ('identite', 'naissance', 'presence') or (k == 'conjoints' and epouse):
                assert source and source['url'] == page and lacune is None
                _reperes_voisins(source['fait'], (nom,))
                if k == 'naissance': _reperes_voisins(source['fait'], ('1386', 'septembre', 'probable'))
                if k == 'presence': _reperes_voisins(source['fait'], tuple(fin.split('/')))
                if k == 'conjoints': _reperes_voisins(source['fait'], UNION_SAVOIE)
            else:
                assert source is None
                _reperes_voisins(lacune, VOISINS_LACUNES.get((i[7:], k), (nom, 'périmètre', 'aucune absence attestée')))


def _etats_voisins(e):
    m = e['maison'][7:]; nom, page, _, _ = VOISINS_CHEFS[m]
    assert (e['conjoints'], e['enfants']) == {'11': ('lacune', 'lacune'), '12': ('union', 'lacune'),
        '13': ('lacune', 'lacune'), '14': ('veuvage', 'absence_attestee')}[m]
    assert set(e['sources']) == set(e['lacunes']) == {'conjoints', 'enfants'}
    for k in ('conjoints', 'enfants'):
        if (m, k) in VOISINS_LACUNES:
            assert e['sources'][k] is None
            _reperes_voisins(e['lacunes'][k], (nom, *VOISINS_LACUNES[m, k]))
        else:
            assert e['lacunes'][k] is None and e['sources'][k] and e['sources'][k]['url'] == page
            _reperes_voisins(e['sources'][k]['fait'], UNION_SAVOIE if m == '12' else (nom, FAMILLE_JAGELLON, 'Jadwiga', '1399-07-17') + (() if k == 'conjoints' else ('Élisabeth Bonifacia', '1399-06-22', '1399-07-13', '1402', '1408', '1424', '1426', '1427')))
    assert set(e['exclusions']) == set(VOISINS_EXCLUSIONS[m])
    for nom, reperes in VOISINS_EXCLUSIONS[m].items():
        x = e['exclusions'][nom]; pages = {v for v in reperes if v.startswith('https:')}
        faits = tuple(v for v in reperes if v not in pages)
        assert x['sources'] and {s['url'] for s in x['sources']} == pages
        _reperes_voisins(x['motif'], (nom, *faits))
        assert all(nom in s['fait'] for s in x['sources'])
        assert all(any(v in s['fait'] for s in x['sources']) for v in faits)
        for source in x['sources']:
            dates = {'Costanza Chiaramonte': {NAPLES: '1392', TRECCANI: '1393'}, 'Marie de Lusignan': {NAPLES: '1403', TRECCANI: '1402'}, 'Philippe de Savoie': {AMEDEE: '1417', MARIE_SAVOIE: '1422'}}
            if nom in dates: assert dates[nom][source['url']] in source['fait']


def test_familles_historiques_voisins():
    d = _personnages()
    def preuve(c): _familles_historiques(c['familles'], c['liens']); _etats_historiques(c['etats'])
    preuve(d)
    for t in ('familles', 'liens', 'etats'):
        for j, f in enumerate(d[t]):
            if f.get('id', 'personne-' + f.get('maison', '')) not in {'personne-marie-bourgogne'} | {'personne-grande-' + m for m in VOISINS_CHEFS}: continue
            mutations = [((t,), []), ((t,), d[t][:j] + d[t][j+1:]), ((t,), d[t] + [f])]
            if t != 'etats':
                mutations += [((t, j, k), v) for k, v in [('pere', 'personne-grande-9'), ('mere', 'personne-grande-9'), ('conjoints', [] if f['conjoints'] else ['personne-philippa-angleterre']), ('presence', 'decedee')]]
                if t == 'familles': mutations += [((t, j, k), v) for k, v in [('nom', 'Homonyme'), ('maison', 'grande-11'), ('naissance', _naissance_famille('1386-09', 'mois'))]]
            for k, v in f['sources'].items():
                if v:
                    mutations += [((t, j, 'sources', k), None), ((t, j, 'sources', k, 'url'), 'https://exemple.org'), ((t, j, 'sources', k, 'fait'), 'Fait perdu')]
                    reperes = UNION_SAVOIE if k == 'conjoints' and f.get('conjoints') in ('union', ['personne-marie-bourgogne'], ['personne-grande-12']) else ('1422', '1428') if k == 'presence' and f.get('id') == 'personne-marie-bourgogne' else ()
                    mutations += [((t, j, 'sources', k, 'fait'), v['fait'].replace(r, 'inconnu')) for r in reperes]
            maison = f.get('maison', f.get('id', '')[9:])[7:]
            for k, v in f['lacunes'].items():
                if v: mutations += [((t, j, 'lacunes', k), ''), *[((t, j, 'lacunes', k), v.replace(r, 'inconnu')) for r in VOISINS_LACUNES.get((maison, k), ())]]
            if t == 'etats':
                mutations += [((t, j, k), v) for k, v in [('conjoints', 'veuvage' if f['conjoints'] != 'veuvage' else 'union'), ('enfants', 'absence_attestee' if f['enfants'] == 'lacune' else 'lacune')]]
                for nom, x in f['exclusions'].items():
                    mutations += [((t, j, 'exclusions', nom), 'SUPPRIMER'), ((t, j, 'exclusions', nom, 'motif'), ''), *[((t, j, 'exclusions', nom, 'sources'), x['sources'][:a] + x['sources'][a+1:]) for a in range(len(x['sources']))]]
                    for a, source in enumerate(x['sources']):
                        mutations += [((t, j, 'exclusions', nom, 'sources', a, 'fait'), 'Fait perdu'), ((t, j, 'exclusions', nom, 'sources', a, 'url'), 'https://exemple.org')]
                    for r in VOISINS_EXCLUSIONS[f['maison'][7:]][nom]:
                        if not r.startswith('https:'): mutations += [((t, j, 'exclusions', nom, 'motif'), x['motif'].replace(r, 'inconnu'))]
            for chemin, valeur in mutations:
                with pytest.raises(AssertionError): preuve(_alterer_personnages(d, chemin, valeur))
    # Chaque intrus a des liens résolus : l'échec vient bien des attentes historiques.
    for m, exclusions in VOISINS_EXCLUSIONS.items():
        for nom in [*exclusions, 'Héritier inventé']:
            c = copy.deepcopy(d); modele = next(f for f in c['familles'] if f['id'] == 'personne-marie-bourgogne')
            ajout = dict(copy.deepcopy(modele), id='personne-intruse', nom=nom, maison='grande-' + m, pere=None, mere=None, conjoints=[])
            c['familles'].append(ajout)
            for role in ('pere', 'conjoints'):
                ajout[role] = 'personne-grande-' + m if role == 'pere' else ['personne-grande-' + m]
                if role == 'conjoints': next(f for f in c['liens'] if f['id'] == 'personne-grande-' + m)['conjoints'].append(ajout['id'])
                assert _controler_famille(c['familles'] + [{**h, **l} for l in c['liens'] for h in c['chefs'] if l['id'] == 'personne-' + h['maison']])
                with pytest.raises(AssertionError): preuve(c)
                ajout['pere'] = None
    c = copy.deepcopy(d)
    next(f for f in c['familles'] if f['id'] == 'personne-philippa-angleterre')['conjoints'] = ['personne-grande-13']
    next(f for f in c['liens'] if f['id'] == 'personne-grande-13')['conjoints'] = ['personne-philippa-angleterre']
    with pytest.raises(AssertionError): preuve(c)


# Notices examinées le 28 octobre 2026 ; attentes indépendantes du catalogue.
MANUEL, HELENE, JEAN, THEODORE, ANDRONIC, CONSTANTIN_XI, DEMETRIOS, THOMAS, CELIK, GANCHOU = (
    'https://en.wikipedia.org/wiki/Manuel_II_Palaiologos#Family', 'https://en.wikipedia.org/wiki/Helena_Draga%C5%A1#Marriage_and_issue',
    'https://en.wikipedia.org/wiki/John_VIII_Palaiologos', 'https://en.wikipedia.org/wiki/Theodore_II_Palaiologos',
    'https://en.wikipedia.org/wiki/Andronikos_Palaiologos_(son_of_Manuel_II)', 'https://en.wikipedia.org/wiki/Constantine_XI_Palaiologos',
    'https://en.wikipedia.org/wiki/Demetrios_Palaiologos', 'https://en.wikipedia.org/wiki/Thomas_Palaiologos',
    'https://doi.org/10.1017/9781108874038.021', 'https://www.persee.fr/doc/rebyz_0766-5598_2008_num_66_1_3033')
BORNE_1400 = '1400\u20131402'
MANUEL_LACUNE = ('Jean V', 'Hélène Cantacuzène', 'Théodore Ier', 'seigneurie-3', 'aucune absence attestée')
BYZANCE = (
    ('helena-dragas', 'Hélène Dragaš', 'c. 1372', 'vers', '1450-03-23', None, None, ('personne-grande-15',), HELENE),
    ('jean-viii', 'Jean VIII Paléologue', '1392-12-18', 'jour', '1448-10-31', 'personne-grande-15', 'personne-helena-dragas', (), JEAN),
    ('theodore-ii', 'Théodore II Paléologue', 'c. 1396', 'vers', '1448-06-21', 'personne-grande-15', 'personne-helena-dragas', (), THEODORE),
)
CONTROLES_BYZANCE = [
    ('personne-grande-15', ('sources', 'conjoints', 'fait'), ('Manuel', 'Hélène', '1392')), ('personne-grande-15', ('sources', 'presence', 'fait'), ('Manuel', '1425')),
    ('personne-grande-15', ('lacunes', 'pere'), MANUEL_LACUNE), ('personne-grande-15', ('lacunes', 'mere'), MANUEL_LACUNE),
    ('personne-helena-dragas', ('sources', 'conjoints', 'fait'), ('1392-02-10', 'couronnement', 'Hélène', 'Manuel')),
    ('personne-helena-dragas', ('lacunes', 'pere'), ('Constantin Dragaš', 'aucune absence attestée')), ('personne-helena-dragas', ('lacunes', 'mere'), ('non nommée', 'aucune absence attestée')),
    ('personne-jean-viii', ('sources', 'pere', 'fait'), ('Jean VIII Paléologue', 'Manuel', 'Hélène')), ('personne-jean-viii', ('sources', 'mere', 'fait'), ('Jean VIII Paléologue', 'Manuel', 'Hélène')), ('personne-jean-viii', ('lacunes', 'conjoints'), ('aucune absence attestée',)),
    ('personne-theodore-ii', ('sources', 'identite', 'fait'), ('Théodore II Paléologue', 'Théodore Ier', 'seigneurie-3')), ('personne-theodore-ii', ('sources', 'pere', 'fait'), ('Théodore II Paléologue', 'Manuel', 'Hélène')), ('personne-theodore-ii', ('sources', 'mere', 'fait'), ('Théodore II Paléologue', 'Manuel', 'Hélène')), ('personne-theodore-ii', ('lacunes', 'conjoints'), ('aucune absence attestée',)),
]
BYZANCE_EXCLUSIONS = {
    'Constantin Paléologue (aîné)': (CELIK, MANUEL, HELENE, 'indéterminée', '1393', '1398', BORNE_1400, 'Monemvasia', '1405', '21490', 'died young'),
    'Andronic Paléologue': (ANDRONIC, MANUEL, HELENE, 'indéterminée', '1400', '1429-03-04', 'ordre des naissances'),
    'Fille aînée non nommée': (MANUEL, HELENE, CELIK, 'indéterminée', BORNE_1400), 'Seconde fille non nommée': (MANUEL, HELENE, CELIK, 'indéterminée', BORNE_1400),
    'Zampia Paléologue, fille de Manuel': (HELENE, GANCHOU, 'Ganchou', 'Jean V', 'Ilario Doria', 'demi-sœur', 'fille naturelle'),
    'Constantin XI': (CONSTANTIN_XI, HELENE, 'future', '1404-02-08', '1405', 'divergence'),
    'Michel Paléologue': (MANUEL, 'future', '1406', '1407', '1409', '1410'),
    'Démétrios Paléologue': (HELENE, DEMETRIOS, 'future', '1407'), 'Thomas Paléologue': (HELENE, THOMAS, 'future', '1409'),
}
ETAT_BYZANCE = (('conjoints', ('1392-02-10', '1392', 'couronnement', 'Manuel', 'Hélène')), ('enfants', ('Sphrantzès', 'Jean VIII', 'Théodore II')))


def _lire_chemin(objet, chemin):
    for cle in chemin:
        objet = objet.get(cle) if isinstance(objet, dict) else None
        if objet is None: return None
    return objet


def _constantinople(fiches=None, etat=None):
    if fiches is not None:
        assert {'personne-' + i for i, *_ in BYZANCE} <= set(fiches) and 'personne-grande-15' in fiches
        manuel = fiches['personne-grande-15']
        attendu = {'pere', 'mere', 'conjoints', 'presence'} | ({'identite', 'naissance'} if 'nom' in manuel else set())
        assert set(manuel['sources']) == set(manuel['lacunes']) == attendu
        assert (manuel['pere'], manuel['mere'], manuel['conjoints'], manuel['presence']) == (None, None, ['personne-helena-dragas'], 'vivante')
        assert all(manuel['sources'][champ] and manuel['sources'][champ]['url'] == MANUEL and manuel['lacunes'][champ] is None for champ in ('conjoints', 'presence'))
        assert manuel['sources']['pere'] is None and manuel['sources']['mere'] is None
        assert 'personne-seigneurie-3' not in fiches and all(f.get(k) != 'personne-seigneurie-3' and 'personne-seigneurie-3' not in (f.get('conjoints') or []) for f in fiches.values() for k in ('pere', 'mere'))
        assert all(f.get('nom') not in ('Hélène Cantacuzène', 'Théodore Ier Paléologue') for f in fiches.values())
        for i, nom, date, precision, deces, pere, mere, conjoints, page in BYZANCE:
            f = fiches['personne-' + i]
            assert (f['nom'], f['maison'], f['naissance'], f['pere'], f['mere'], tuple(f['conjoints']), f['presence']) == (nom, 'grande-15', _naissance_famille(date, precision), pere, mere, conjoints, 'vivante')
            assert set(f['sources']) == set(f['lacunes']) == {'identite', 'naissance', 'pere', 'mere', 'conjoints', 'presence'}
            assert all(f['sources'][champ] and f['sources'][champ]['url'] == page and f['lacunes'][champ] is None for champ in ('identite', 'naissance', 'presence'))
            if conjoints:
                assert f['sources']['pere'] is None and f['sources']['mere'] is None and f['lacunes']['conjoints'] is None and f['sources']['conjoints'] and f['sources']['conjoints']['url'] == HELENE
            else:
                assert f['sources']['conjoints'] is None and f['lacunes']['pere'] is None and f['lacunes']['mere'] is None and all(f['sources'][role] and f['sources'][role]['url'] == HELENE for role in ('pere', 'mere'))
            _reperes_voisins(f['sources']['naissance']['fait'], (nom, date)); _reperes_voisins(f['sources']['presence']['fait'], (nom, deces))
        for ident, chemin, reperes in CONTROLES_BYZANCE: _reperes_voisins(_lire_chemin(fiches[ident], chemin), reperes)
    if etat is not None:
        sources, exclusions = etat.get('sources'), etat.get('exclusions')
        assert (etat.get('conjoints'), etat.get('enfants')) == ('union', 'documentes') and etat.get('lacunes') == {'conjoints': None, 'enfants': None}
        assert isinstance(sources, dict) and isinstance(exclusions, dict) and set(exclusions) == set(BYZANCE_EXCLUSIONS)
        for champ, reperes in ETAT_BYZANCE:
            source = sources.get(champ)
            assert isinstance(source, dict) and source.get('url') == HELENE
            _reperes_voisins(source.get('fait'), reperes)
        assert sources['enfants']['fait'].index('Jean VIII') < sources['enfants']['fait'].index('Théodore II')
        for nom, reperes in BYZANCE_EXCLUSIONS.items():
            x, pages = exclusions[nom], {v for v in reperes if str(v).startswith('http')}
            faits = tuple(v for v in reperes if v not in pages)
            assert x.get('sources') and {s.get('url') for s in x['sources']} == pages
            _reperes_voisins(x.get('motif'), (nom, *faits))
            assert all(nom in (s.get('fait') or '') for s in x['sources']) and all(any(v in (s.get('fait') or '') for s in x['sources']) for v in faits)
            if nom == 'Constantin XI': assert all({CONSTANTIN_XI: '1404-02-08', HELENE: '1405'}[s['url']] in s['fait'] for s in x['sources'])


def test_familles_historiques_constantinople():
    d = _personnages()
    def preuve(c):
        _familles_historiques(c['familles'], c['liens']); _etats_historiques(c['etats'])
    def resolus(c):
        return c['familles'] + [{**h, **l} for l in c['liens'] for h in c['chefs'] if l['id'] == 'personne-' + h['maison']]
    def refuse(c, controle=False):
        if controle: assert _controler_famille(resolus(c))
        with pytest.raises(AssertionError): preuve(c)
    preuve(d)
    ids = {'personne-helena-dragas', 'personne-jean-viii', 'personne-theodore-ii', 'personne-grande-15', 'grande-15'}
    for t in ('familles', 'liens', 'etats'):
        for j, f in enumerate(d[t]):
            if f.get('id', f.get('maison')) not in ids: continue
            mutations = [((t,), d[t][:j] + d[t][j+1:]), ((t,), d[t] + [f])]
            if t != 'etats':
                mutations += [((t, j, k), v) for k, v in [('pere', 'personne-seigneurie-3'), ('mere', 'personne-seigneurie-3'), ('conjoints', [] if f['conjoints'] else ['personne-grande-15']), ('presence', 'decedee')]]
                mutations += [((t, j, 'sources', champ), None) for champ, source in f['sources'].items() if source]
                if t == 'familles':
                    mutations += [((t, j, 'nom'), 'Homonyme'), ((t, j, 'maison'), 'seigneurie-3')]
                    if f['id'] == 'personne-jean-viii': mutations.append(((t, j, 'naissance'), _naissance_famille('1392-12', 'mois')))
                    if f['id'] == 'personne-theodore-ii': mutations.append(((t, j, 'naissance'), _naissance_famille('1396', 'annee')))
                    for i, nom, date, _precision, deces, *_reste in BYZANCE:
                        if f['id'] != 'personne-' + i: continue
                        for champ, reperes in (('naissance', (nom, date)), ('presence', (nom, deces))):
                            mutations += [((t, j, 'sources', champ, 'fait'), f['sources'][champ]['fait'].replace(r, 'inconnu')) for r in reperes]
                for ident, chemin, reperes in CONTROLES_BYZANCE:
                    if ident != f.get('id'): continue
                    texte, base = _lire_chemin(f, chemin), (t, j, *chemin)
                    if chemin[-1] == 'fait': mutations += [(base[:-1], None), (base[:-1] + ('url',), 'https://exemple.org'), (base, 'Fait perdu')]
                    else: mutations.append((base, ''))
                    if isinstance(texte, str): mutations += [(base, texte.replace(r, 'inconnu')) for r in reperes]
            else:
                mutations += [((t, j, 'conjoints'), 'veuvage'), ((t, j, 'enfants'), 'absence_attestee'), ((t, j, 'enfants'), 'lacune')]
                for champ, reperes in ETAT_BYZANCE:
                    texte = f['sources'][champ]['fait']
                    mutations += [((t, j, 'sources', champ), None), ((t, j, 'sources', champ, 'url'), 'https://exemple.org'), ((t, j, 'sources', champ, 'fait'), 'Fait perdu')]
                    mutations += [((t, j, 'sources', champ, 'fait'), texte.replace(r, 'inconnu')) for r in reperes]
                for nom, reperes in BYZANCE_EXCLUSIONS.items():
                    x = f['exclusions'][nom]
                    mutations += [((t, j, 'exclusions', nom), 'SUPPRIMER'), ((t, j, 'exclusions', nom, 'motif'), '')]
                    mutations += [((t, j, 'exclusions', nom, 'motif'), x['motif'].replace(r, 'inconnu')) for r in reperes if not str(r).startswith('http')]
                    for a, source in enumerate(x['sources']):
                        mutations += [((t, j, 'exclusions', nom, 'sources'), x['sources'][:a] + x['sources'][a+1:]), ((t, j, 'exclusions', nom, 'sources', a, 'fait'), 'Fait perdu'), ((t, j, 'exclusions', nom, 'sources', a, 'url'), 'https://exemple.org')]
                        if nom == 'Constantin XI': mutations.append(((t, j, 'exclusions', nom, 'sources', a, 'fait'), source['fait'].replace('1404-02-08' if source['url'] == CONSTANTIN_XI else '1405', 'inconnu')))
            for chemin, valeur in mutations: refuse(_alterer_personnages(d, chemin, valeur))
    modele = next(f for f in d['familles'] if f['id'] == 'personne-marie-bourgogne')
    for nom, presence, roles in [(n, 'vivante', ('pere', 'conjoints')) for n in (*BYZANCE_EXCLUSIONS, 'Héritier inventé')] + [(n, 'decedee', ('pere',)) for n in ('Constantin Paléologue (aîné)', 'Andronic Paléologue')]:
        c = copy.deepcopy(d)
        ajout = dict(copy.deepcopy(modele), id='personne-intruse', nom=nom, maison='grande-15', presence=presence, pere=None, mere=None, conjoints=[])
        c['familles'].append(ajout)
        for role in roles:
            ajout[role] = 'personne-grande-15' if role == 'pere' else ['personne-grande-15']
            if role == 'conjoints': next(x for x in c['liens'] if x['id'] == 'personne-grande-15')['conjoints'].append(ajout['id'])
            refuse(c, controle=True)
            ajout['pere'] = None
    c = copy.deepcopy(d); exc = next(x for x in c['etats'] if x['maison'] == 'grande-15')['exclusions']
    exc['Constantin XI'] = exc.pop('Constantin Paléologue (aîné)'); refuse(c)
    for cible, nom in (('personne-theodore-ii', 'Théodore Ier Paléologue'), ('personne-helena-dragas', 'Hélène Cantacuzène')):
        c = copy.deepcopy(d); next(x for x in c['familles'] if x['id'] == cible)['nom'] = nom; refuse(c)
    def lier(c, **kw):
        lien = copy.deepcopy(next(x for x in c['liens'] if x['id'] == 'personne-grande-15'))
        lien.update(mere=None, conjoints=[], **kw); c['liens'].append(lien); refuse(c, controle=True)
    lier(copy.deepcopy(d), id='personne-seigneurie-3', pere='personne-grande-15')
    c = copy.deepcopy(d)
    c['familles'].append(dict(copy.deepcopy(next(x for x in c['familles'] if x['id'] == 'personne-helena-dragas')), id='personne-jean-v', nom='Jean V Paléologue', naissance=_naissance_famille('1332-06-18'), pere=None, mere=None, conjoints=[]))
    next(x for x in c['liens'] if x['id'] == 'personne-grande-15')['pere'] = 'personne-jean-v'
    lier(c, id='personne-seigneurie-3', pere='personne-jean-v')


# Notices examinées le 28 octobre 2026 ; attentes indépendantes du catalogue.
# id, nom, naissance, précision, mère, épouse, page d’identité, repères, pages (naissance, présence, père, mère, conjoints ; - : aucune), identité, présence, conjoint
BAYEZID, MEHMED_P, FETRET = 'https://islamansiklopedisi.org.tr/bayezid-i', 'https://islamansiklopedisi.org.tr/mehmed-i', 'https://islamansiklopedisi.org.tr/fetret-devri'
TTK, UZUNCARSILI = 'https://ttk.gov.tr/osmanli-padisahlari/', 'https://dergipark.org.tr/tr/download/article-file/3043592'
ULUCAY = 'https://turuz.com/storage/Turkologi/2017/2278-Padishahlarin_Qadinlari_Ve_Qizlari-M.Chaghatay_Uluchay-1992-313s.pdf'
DEVLETSAH, HAFSA, OLIVERA = 'https://en.wikipedia.org/wiki/Devlet%C5%9Fah_Hatun', 'https://en.wikipedia.org/wiki/Hafsa_Hatun', 'https://en.wikipedia.org/wiki/Olivera_Despina'
SRC_OTTO, PERE_B = dict(B=BAYEZID, M=MEHMED_P, F=FETRET, T=TTK, U=ULUCAY, Z=UZUNCARSILI, D=DEVLETSAH, H=HAFSA, O=OLIVERA), 'personne-grande-16'
OTTOMANS = (
    ('devletsah-hatun', 'Devletşah Hatun', 'c. 1365', 'vers', None, True, DEVLETSAH, ('c. 1365', '1414', '1378', '1381', 'p. 23-26'), 'DD--U', 'Devletşah Hatun, fille de Süleyman Şah de Germiyan, compagne de Bayezid Ier.', 'Devletşah Hatun, morte en 1414 ; vivante au 1er janvier 1400, décès cité pour la sélection initiale.', 'Devletşah Hatun épouse Bayezid Ier en 1378 ; la notice Bayezid donne vers 1381. Uluçay, p. 23-26.'),
    ('devlet-hatun', 'Devlet Hatun', None, None, None, True, UZUNCARSILI, ('janvier 1414', 'convertie', 'distincte', 'Devletşah Hatun', 'p. 185-188'), '-Z--Z', 'Devlet Hatun, convertie distincte de Devletşah Hatun, compagne de Bayezid Ier et mère de Mehmed Çelebi. Uzunçarşılı, p. 185-188.', 'Devlet Hatun, convertie distincte de Devletşah Hatun, morte en janvier 1414 ; vivante au 1er janvier 1400.', 'Devlet Hatun, convertie distincte de Devletşah Hatun, compagne de Bayezid Ier.'),
    ('olivera-despina', 'Olivera Despina', 'c. 1372', 'vers', None, True, OLIVERA, ('c. 1372', '1444', '1390', '1402'), 'OO--O', 'Olivera Despina, fille de Lazar de Serbie, compagne de Bayezid Ier.', 'Olivera Despina, vivante après 1444, capturée en 1402 avec Oruz Hatun et Paşa Melek Hatun ; vivante au 1er janvier 1400.', 'Olivera Despina épouse Bayezid Ier en 1390.'),
    ('hafsa-hatun', 'Hafsa Hatun', None, None, None, True, HAFSA, ('1390', '1403', 'İsa Bey', 'Aydın'), '-H--H', 'Hafsa Hatun, fille d’İsa Bey d’Aydın, compagne de Bayezid Ier.', 'Hafsa Hatun, présence après 1403 ; vivante au 1er janvier 1400.', 'Hafsa Hatun épouse Bayezid Ier en 1390.'),
    ('suleyman-celebi', 'Süleyman Çelebi', None, None, None, False, BAYEZID, ('après le départ',), '-FB--', 'Süleyman Çelebi, fils de Bayezid Ier, parmi les six fils survivants.', 'Süleyman Çelebi, fils de Bayezid Ier, vivant après le départ.', None),
    ('isa-celebi', 'İsa Çelebi', '1380', 'annee', 'devletsah-hatun', False, DEVLETSAH, ('1380', 'Devletşah Hatun', 'après le départ'), 'DFBU-', 'İsa Çelebi, fils de Bayezid Ier et de Devletşah Hatun.', 'İsa Çelebi, fils de Bayezid Ier et de Devletşah Hatun, vivant après le départ.', None),
    ('musa-celebi', 'Musa Çelebi', None, None, 'devletsah-hatun', False, ULUCAY, ('Devletşah Hatun', 'après le départ'), '-FBU-', 'Musa Çelebi, fils de Bayezid Ier et de Devletşah Hatun.', 'Musa Çelebi, fils de Bayezid Ier, vivant après le départ.', None),
    ('mehmed-ier', 'Mehmed Çelebi', '1386 ou 1387', 'intervalle', 'devlet-hatun', False, MEHMED_P, ('1386 ou 1387', 'Devlet Hatun', 'après le départ'), 'MMBZ-', 'Mehmed Çelebi, fils de Bayezid Ier et de Devlet Hatun.', 'Mehmed Çelebi, fils de Bayezid Ier, vivant après le départ.', None),
    ('kasim-celebi', 'Kasım Çelebi', None, None, None, False, FETRET, ('1403', 'Constantinople', 'après le départ'), '-FB--', 'Kasım Çelebi, fils de Bayezid Ier.', 'Kasım Çelebi, fils de Bayezid Ier, envoyé à Constantinople en 1403 ; vivant après le départ.', None),
    ('mustafa-celebi', 'Mustafa Çelebi', None, None, None, False, MEHMED_P, ('1402', 'après le départ'), '-MB--', 'Mustafa Çelebi, fils de Bayezid Ier.', 'Mustafa Çelebi, fils de Bayezid Ier, capturé en 1402 ; vivant après le départ.', None),
    ('hundi-hatun', 'Hundi Hatun', None, None, None, False, ULUCAY, ('1396', 'Nicopolis', 'après le départ'), '-UU--', 'Hundi Hatun, fille de Bayezid Ier.', 'Hundi Hatun, fille de Bayezid Ier, mariée après Nicopolis (1396) ; vivante après le départ. Uluçay, p. 23-26.', None),
    ('oruz-hatun', 'Oruz Hatun', None, None, 'olivera-despina', False, OLIVERA, ('Olivera Despina', '1402', 'après le départ'), '-OUO-', 'Oruz Hatun, fille de Bayezid Ier et d’Olivera Despina.', 'Oruz Hatun, capturée en 1402 avec Olivera Despina ; vivante après le départ.', None),
    ('pasa-melek-hatun', 'Paşa Melek Hatun', None, None, 'olivera-despina', False, OLIVERA, ('Olivera Despina', '1402', 'après le départ'), '-OUO-', 'Paşa Melek Hatun, fille de Bayezid Ier et d’Olivera Despina.', 'Paşa Melek Hatun, capturée en 1402 avec Olivera Despina ; vivante après le départ.', None),
    ('fatma-hatun', 'Fatma Hatun', None, None, None, False, FETRET, ('1403', 'Kasım Çelebi', 'après le départ'), '-FU--', 'Fatma Hatun, fille de Bayezid Ier.', 'Fatma Hatun, fille de Bayezid Ier, envoyée à Constantinople avec Kasım Çelebi en 1403 ; vivante après le départ.', None),
)
OTTO_EXCLUSIONS = {
    'Ertuğrul Çelebi': (MEHMED_P, TTK, '1400', 'indéterminée', 'sans jour'),
    'Erhondu Hatun': (ULUCAY, 'fille', 'mère', 'indéterminée', 'p. 23-26'),
    **{n: (BAYEZID, TTK, 'divergentes', 'six fils survivants', 'relevé') for n in ('Yusuf Çelebi', 'Hasan Çelebi', 'Ömer Çelebi', 'Korkud Çelebi', 'İbrahim Çelebi')},
    'Fille non nommée proposée à Ladislas': (NAPLES, TRECCANI, 'grande-11', 'jamais fusionnée', 'Hundi Hatun', 'Oruz Hatun', 'Paşa Melek Hatun', 'Fatma Hatun', 'Erhondu Hatun'),
    **{n: (ULUCAY, 'aucune trace', 'confusion', 'Olivera Despina', *s) for n, s in (
        ('Fülane', ()), ('Fille non nommée de Jean V', ('Jean V',)), ('Maria Fadrique', ('Salona',)), ('Angelina', ()), ('Maria', ('Hongrie',)))},
}


PARENTS_OTTO = {('devletsah-hatun', 'pere'): ('Süleyman Şah de Germiyan',), ('devletsah-hatun', 'mere'): ('Mutahhare Hatun',), ('hafsa-hatun', 'pere'): ('İsa Bey d’Aydın',)}
UNION_OTTO, ENFANTS_OTTO = 'union avec Devletşah Hatun, Devlet Hatun, Olivera Despina et Hafsa Hatun', 'Enfants documentés de Bayezid Ier : Süleyman Çelebi, İsa Çelebi, Musa Çelebi, Mehmed Çelebi, Kasım Çelebi, Mustafa Çelebi, Hundi Hatun, Oruz Hatun, Paşa Melek Hatun et Fatma Hatun'
UNIONS_B = 'unions avec Devletşah Hatun (1378, vers 1381), Devlet Hatun, Olivera Despina (1390) et Hafsa Hatun (1390)'
NEGATION = re.compile(r'\b(aucune?s?|pas|sans|jamais|non|ni)\b', re.I)  # un fait établi n’est pas une négation


SENS_IDENTITE = (('convertie', 'née'), ('fille', 'fils'), ('fils de', 'frère de'))
SENS_PRESENCE = (('morte', 'née'), ('capturée', 'libérée'), ('capturé', 'libéré'), ('présence', 'absence'), ('mariée', 'célibataire'), ('envoyée', 'emprisonnée'), ('envoyé', 'emprisonné'), ('fils', 'frère'))
SENS_CONJOINT = (('convertie', 'née'), ('épouse', 'quitte'))


def _ottomans(fiches=None, etat=None):
    if fiches is not None:
        assert {'personne-' + i for i, *_ in OTTOMANS} <= set(fiches) and PERE_B in fiches
        bay, epouses = fiches[PERE_B], tuple('personne-' + i for i, _, _, _, _, epoux, *_ in OTTOMANS if epoux)
        assert set(bay['sources']) == set(bay['lacunes']) == {'pere', 'mere', 'conjoints', 'presence'} | ({'identite', 'naissance'} if 'nom' in bay else set())
        assert (bay['pere'], bay['mere'], tuple(bay['conjoints']), bay['presence']) == (None, None, epouses, 'vivante')
        conjoints, presence_b = bay['sources'].get('conjoints'), bay['sources'].get('presence')
        assert bay['sources'].get('pere') is None and bay['sources'].get('mere') is None and bay['lacunes'].get('conjoints') is None and bay['lacunes'].get('presence') is None
        assert isinstance(conjoints, dict) and conjoints.get('url') == BAYEZID and re.fullmatch(r'Bayezid Ier : ' + re.escape(UNIONS_B) + r'\.', conjoints.get('fait') or '') and isinstance(presence_b, dict) and presence_b.get('url') == BAYEZID and re.fullmatch(r'Bayezid Ier, vivant au 1er janvier 1400, sultan de 1389 à 1402 ; décès postérieur cité pour la sélection initiale\.', presence_b.get('fait') or '')
        assert isinstance(bay['lacunes'].get('pere'), str) and 'aucune absence attestée' in bay['lacunes']['pere'] and isinstance(bay['lacunes'].get('mere'), str) and 'aucune absence attestée' in bay['lacunes']['mere']
        for k in ('pere', 'mere'): _reperes_voisins(bay['lacunes'][k], ('Ancêtres de Bayezid Ier', 'hors périmètre', 'aucune absence attestée'))
        _reperes_voisins(conjoints.get('fait'), (UNIONS_B,)); assert not any(NEGATION.search(s.get('fait') or '') for s in (conjoints, presence_b))
        _reperes_voisins(conjoints.get('fait'), ('1378', '1381', '1390', 'Devletşah Hatun', 'Devlet Hatun', 'Olivera Despina', 'Hafsa Hatun'))
        assert fiches['personne-devlet-hatun']['nom'] != fiches['personne-devletsah-hatun']['nom']
        for i, nom, date, precision, mere, epoux, page, _reperes, pages, identite_attendue, presence_attendue, conjoint_attendu in OTTOMANS:
            f, sexe = fiches['personne-' + i], 'fils' if nom.endswith('Çelebi') else 'fille'
            assert (f['nom'], f['maison'], f['naissance'], f['pere'], f['mere'], tuple(f['conjoints']), f['presence']) == (
                nom, 'grande-16', _naissance_famille(date, precision) if date else None, None if epoux else PERE_B,
                'personne-' + mere if mere else None, (PERE_B,) if epoux else (), 'vivante')
            assert set(f['sources']) == set(f['lacunes']) == {'identite', 'naissance', 'pere', 'mere', 'conjoints', 'presence'}
            identite, presence = f['sources'].get('identite'), f['sources'].get('presence')
            assert isinstance(identite, dict) and identite.get('url') == page and identite.get('fait') == identite_attendue and isinstance(presence, dict) and presence.get('url') == SRC_OTTO[pages[1]] and presence.get('fait') == presence_attendue and f['lacunes'].get('presence') is None
            assert all(isinstance(s, dict) and nom in (s.get('fait') or '') for s in f['sources'].values() if s) and all((f['sources'].get(k) or {}).get('url') == SRC_OTTO.get(c) for k, c in zip(('naissance', 'presence', 'pere', 'mere', 'conjoints'), pages))
            assert not any(NEGATION.search(s.get('fait') or '') for s in f['sources'].values() if s)
            assert next(a for a, _ in SENS_IDENTITE if a in identite_attendue) in identite.get('fait') and next(a for a, _ in SENS_PRESENCE if a in presence_attendue) in presence.get('fait') and (not epoux or next(a for a, _ in SENS_CONJOINT if a in conjoint_attendu) in f['sources']['conjoints'].get('fait'))
            for k in ('pere', 'mere', 'conjoints'):
                if isinstance(f['lacunes'].get(k), str) and not (k == 'mere' and not epoux): _reperes_voisins(f['lacunes'][k], (nom, 'hors périmètre', 'aucune absence attestée', *PARENTS_OTTO.get((i, k), ()))); _reperes_voisins(f['lacunes'][k].lower(), ({'pere': 'père', 'mere': 'mère', 'conjoints': 'conjoints'}[k],))
            if epoux:
                assert f['sources'].get('pere') is None and f['sources'].get('mere') is None and isinstance(f['sources'].get('conjoints'), dict) and f['sources']['conjoints'].get('fait') == conjoint_attendu and f['sources']['conjoints'].get('url') == SRC_OTTO[pages[4]] and f['lacunes'].get('conjoints') is None and isinstance(f['lacunes'].get('pere'), str) and 'aucune absence attestée' in f['lacunes']['pere'] and isinstance(f['lacunes'].get('mere'), str) and 'aucune absence attestée' in f['lacunes']['mere']
            else:
                pere = f['sources'].get('pere')
                assert isinstance(pere, dict) and re.fullmatch(re.escape(nom) + r' est ' + sexe + r' de Bayezid Ier\.', pere.get('fait') or '') and f['sources'].get('conjoints') is None and isinstance(f['lacunes'].get('conjoints'), str) and 'aucune absence attestée' in f['lacunes']['conjoints']
                if mere:
                    mere_source = f['sources'].get('mere')
                    assert isinstance(mere_source, dict) and re.fullmatch(re.escape(nom) + r' est ' + sexe + r' de Bayezid Ier et d(e |’)' + re.escape(next(o[1] for o in OTTOMANS if o[0] == mere)) + r'(?:, convertie distincte de ' + re.escape(next(o[1] for o in OTTOMANS if o[0] == 'devletsah-hatun')) + r')?\.(?: (?:Uluçay, )?p\. [\d-]+\.)?', mere_source.get('fait') or '') and not re.search(r'réfut|refus|\brumeur\b|\bnie\b|n[’\']est pas|prétend|fausse?', mere_source.get('fait') or '', re.I)
                else:
                    assert f['sources'].get('mere') is None and isinstance(f['lacunes'].get('mere'), str)
                    _reperes_voisins(f['lacunes']['mere'], (nom, 'n’établissent pas', 'aucune absence attestée'))
                    _reperes_voisins(f['lacunes']['mere'], ('Les pages examinées n’établissent pas la mère de', 'aucune mère inventée'))
            if date:
                naissance = f['sources'].get('naissance')
                assert isinstance(naissance, dict) and re.fullmatch(re.escape(nom) + r' : naissance ' + re.escape(date) + r'\.', naissance.get('fait') or '') and f['lacunes'].get('naissance') is None
            else:
                assert f['sources'].get('naissance') is None and isinstance(f['lacunes'].get('naissance'), str) and 'naissance inconnue' in f['lacunes']['naissance']
    if etat is not None:
        assert (etat.get('conjoints'), etat.get('enfants'), etat.get('lacunes')) == ('union', 'documentes', {'conjoints': None, 'enfants': None})
        sources, exclusions = etat.get('sources'), etat.get('exclusions')
        assert isinstance(sources, dict) and isinstance(exclusions, dict) and set(exclusions) == set(OTTO_EXCLUSIONS)
        for champ, reperes in (
                ('conjoints', tuple(nom for _, nom, _, _, _, femme, *_ in OTTOMANS if femme) + ('1378', '1381', '1390')),
                ('enfants', tuple(nom for _, nom, _, _, _, femme, *_ in OTTOMANS if not femme))):
            source = sources.get(champ); assert isinstance(source, dict) and source.get('url') == BAYEZID; _reperes_voisins(source.get('fait'), reperes)
            _reperes_voisins(source['fait'], (UNION_OTTO if champ == 'conjoints' else ENFANTS_OTTO,)); assert not NEGATION.search(source['fait']) and re.fullmatch((r'Bayezid Ier : ' + re.escape(UNION_OTTO) + r' ; unions en 1378, vers 1381 et 1390\.') if champ == 'conjoints' else re.escape(ENFANTS_OTTO) + r'\.', source['fait'])
        for nom, reperes in OTTO_EXCLUSIONS.items():
            x, pages = exclusions[nom], {v for v in reperes if str(v).startswith('http')}
            faits = tuple(v for v in reperes if v not in pages); sens = (r' : mort en 1400 sans jour établi ; présence indéterminée au 1er janvier, jamais vivant ni décédée par déduction\.' if nom == 'Ertuğrul Çelebi' else r' : fille et mère attestée par Uluçay, p\. 23-26 ; aucune date n’établit sa présence, présence indéterminée\.' if nom == 'Erhondu Hatun' else r' : listes tardives divergentes, absent des six fils survivants de Bayezid et du relevé TTK ; existence ou présence non promue en fait certain\.' if 'divergentes' in faits else r' : projet déjà conservé dans l’exclusion de grande-11, jamais fusionnée avec Hundi Hatun, Oruz Hatun, Paşa Melek Hatun, Fatma Hatun ou Erhondu Hatun\.' if 'jamais fusionnée' in faits else r' : Uluçay ne trouve aucune trace dans les sources et signale une confusion probable avec Olivera Despina ; aucune personne ni union active(?:\. (?:Comtesse de Salona|Fille du roi de Hongrie))?\.')
            assert x.get('sources') and {s.get('url') for s in x['sources']} == pages and all(nom in (s.get('fait') or '') and re.fullmatch(re.escape(nom) + sens, s.get('fait') or '') for s in x['sources']) and all(any(v in (s.get('fait') or '') for s in x['sources']) for v in faits) and re.fullmatch(re.escape(nom) + sens, x.get('motif') or '')
            _reperes_voisins(x.get('motif'), (nom, *faits))


def test_familles_historiques_ottomans():
    d = _personnages()
    def preuve(c):
        _familles_historiques(c['familles'], c['liens']); _etats_historiques(c['etats'])
    def resolus(c):
        return c['familles'] + [{**h, **l} for l in c['liens'] for h in c['chefs'] if l['id'] == 'personne-' + h['maison']]
    def refuse(c, controle=False):
        if controle: assert _controler_famille(resolus(c))
        with pytest.raises(AssertionError): preuve(c)
    def remplacer(obj, ancien):
        if isinstance(obj, str): return obj.replace(ancien, 'inconnu')
        if isinstance(obj, list): return [remplacer(x, ancien) for x in obj]
        return {k: remplacer(v, ancien) for k, v in obj.items()} if isinstance(obj, dict) else obj
    preuve(d)
    ids = {'personne-' + i for i, *_ in OTTOMANS} | {PERE_B, 'grande-16'}
    for t in ('familles', 'liens', 'etats'):
        for j, f in enumerate(d[t]):
            if f.get('id', f.get('maison')) not in ids: continue
            refuse(_alterer_personnages(d, (t,), d[t][:j] + d[t][j+1:]))
            refuse(_alterer_personnages(d, (t,), d[t] + [copy.deepcopy(f)]))
            if t == 'etats':
                for valeur in ('absence_attestee', 'lacune'): refuse(_alterer_personnages(d, (t, j, 'enfants'), valeur))
                for champ in ('conjoints', 'enfants'):
                    texte = f['sources'][champ]['fait']
                    refuse(_alterer_personnages(d, (t, j, 'sources', champ), None)); refuse(_alterer_personnages(d, (t, j, 'sources', champ, 'fait'), 'Fait perdu')); refuse(_alterer_personnages(d, (t, j, 'sources', champ, 'fait'), 'Rumeur : ' + texte))
                    refuse(_alterer_personnages(d, (t, j, 'sources', champ, 'fait'), texte.replace(*(('union avec', 'aucune union avec') if champ == 'conjoints' else ('Enfants documentés', 'Aucun enfant documenté')))))
                    for r in (('1378', '1381', '1390') if champ == 'conjoints' else ()):
                        refuse(_alterer_personnages(d, (t, j, 'sources', champ, 'fait'), texte.replace(r, 'inconnu')))
                for nom, reperes in OTTO_EXCLUSIONS.items():
                    x = f['exclusions'][nom]
                    refuse(_alterer_personnages(d, (t, j, 'exclusions', nom), 'SUPPRIMER')); refuse(_alterer_personnages(d, (t, j, 'exclusions', nom, 'motif'), '')); refuse(_alterer_personnages(d, (t, j, 'exclusions', nom, 'motif'), x['motif'] + ' Elle est pourtant vivante au départ')); refuse(_alterer_personnages(d, (t, j, 'exclusions', nom, 'sources', 0, 'fait'), f'{nom} est vivant en 1400 ; présence indéterminée, sans jour de décès')) if nom == 'Ertuğrul Çelebi' else None
                    for r in reperes:
                        if not str(r).startswith('http'): refuse(_alterer_personnages(d, (t, j, 'exclusions', nom, 'motif'), x['motif'].replace(r, 'inconnu')))
                    for a in range(len(x['sources'])): refuse(_alterer_personnages(d, (t, j, 'exclusions', nom, 'sources'), x['sources'][:a] + x['sources'][a+1:]))
                continue
            refuse(_alterer_personnages(d, (t, j, 'presence'), 'decedee'))
            for champ, source in ((k, s) for k, s in f['sources'].items() if s):
                refuse(_alterer_personnages(d, (t, j, 'sources', champ), None)); [refuse(_alterer_personnages(d, (t, j, 'sources', champ, 'url'), u)) for u in ('https://exemple.org', BAYEZID if source['url'] != BAYEZID else FETRET)]; refuse(_alterer_personnages(d, (t, j, 'sources', champ, 'fait'), 'Fait perdu'))
            if t == 'liens':
                refuse(_alterer_personnages(d, (t, j, 'conjoints'), f['conjoints'][:1])); refuse(_alterer_personnages(d, (t, j, 'pere'), 'personne-grande-15'))
                texte = f['sources']['conjoints']['fait']
                for r in ('1378', '1381', '1390', 'Devletşah Hatun', 'Devlet Hatun', 'Olivera Despina', 'Hafsa Hatun'):
                    refuse(_alterer_personnages(d, (t, j, 'sources', 'conjoints', 'fait'), texte.replace(r, 'inconnu')))
                refuse(_alterer_personnages(d, (t, j, 'sources', 'conjoints', 'fait'), texte.replace('unions avec', 'aucune union avec'))); refuse(_alterer_personnages(d, (t, j, 'sources', 'conjoints', 'fait'), 'Bayezid Ier nie ses ' + UNIONS_B)); refuse(_alterer_personnages(d, (t, j, 'sources', 'presence', 'fait'), 'Bayezid Ier, mort au 1er janvier 1400.'))
                for k in ('pere', 'mere'): [refuse(_alterer_personnages(d, (t, j, 'lacunes', k), m)) for m in ('Motif arbitraire hors périmètre ; aucune absence attestée.', 'Ancêtres de Bayezid Ier ; aucune absence attestée.', 'Ancêtres de Bayezid Ier hors périmètre ; aucune absence.')]
                continue
            row = next(o for o in OTTOMANS if f['id'] == 'personne-' + o[0])
            refuse(_alterer_personnages(d, (t, j, 'nom'), 'Homonyme')); refuse(_alterer_personnages(d, (t, j, 'sources', 'identite', 'fait'), f'{row[1]} est l’oncle de Bayezid Ier')); refuse(_alterer_personnages(d, (t, j, 'sources', 'identite', 'fait'), f['sources']['identite']['fait'] + ' Attribution fausse')); refuse(_alterer_personnages(d, (t, j, 'sources', 'identite', 'fait'), f['sources']['identite']['fait'].replace('compagne', 'prétendue compagne'))) if row[5] else None; refuse(_alterer_personnages(d, (t, j, 'sources', 'presence', 'fait'), f'{row[1]} meurt après le départ')); refuse(_alterer_personnages(d, (t, j, 'sources', 'presence', 'fait'), f['sources']['presence']['fait'] + ' décédée avant le départ')); refuse(_alterer_personnages(d, (t, j, 'sources', 'identite', 'fait'), row[9].replace(*next(p for p in SENS_IDENTITE if p[0] in row[9]), 1))); refuse(_alterer_personnages(d, (t, j, 'sources', 'presence', 'fait'), row[10].replace(*next(p for p in SENS_PRESENCE if p[0] in row[10]), 1)))
            for k in (k for k, v in f['lacunes'].items() if isinstance(v, str)): [refuse(_alterer_personnages(d, (t, j, 'lacunes', k), m)) for m in ('Motif arbitraire hors périmètre ; aucune absence attestée.', f'Motif arbitraire de {row[1]} hors périmètre ; aucune absence attestée.')]
            for k, parent in ((k, p) for k in ('pere', 'mere') for p in PARENTS_OTTO.get((row[0], k), ())): refuse(_alterer_personnages(d, (t, j, 'lacunes', k), f['lacunes'][k].replace(parent, 'Inconnu')))
            refuse(_alterer_personnages(d, (t, j, 'naissance'), None if f['naissance'] else _naissance_famille('1380', 'annee'))); refuse(_alterer_personnages(d, (t, j, 'sources', 'naissance', 'fait'), f'{row[1]} meurt en {row[2]}')) if row[2] else None
            for r in row[7]:
                c = copy.deepcopy(d); c[t][j]['sources'], c[t][j]['lacunes'] = remplacer(f['sources'], r), remplacer(f['lacunes'], r); refuse(c)
            if row[5]:
                refuse(_alterer_personnages(d, (t, j, 'conjoints'), [])); refuse(_alterer_personnages(d, (t, j, 'lacunes', 'pere'), 'hors sujet')); refuse(_alterer_personnages(d, (t, j, 'sources', 'conjoints', 'fait'), f'{row[1]} est sœur de Bayezid Ier en 1390.')); refuse(_alterer_personnages(d, (t, j, 'sources', 'conjoints', 'fait'), f'{row[1]} refuse d’être compagne de Bayezid Ier')); refuse(_alterer_personnages(d, (t, j, 'sources', 'conjoints', 'fait'), f['sources']['conjoints']['fait'] + ' Attribution fausse')); refuse(_alterer_personnages(d, (t, j, 'sources', 'conjoints', 'fait'), row[11].replace(*next(p for p in SENS_CONJOINT if p[0] in row[11]), 1)))
            else:
                refuse(_alterer_personnages(d, (t, j, 'pere'), None)); refuse(_alterer_personnages(d, (t, j, 'sources', 'pere', 'fait'), f'{row[1]} est sœur de Bayezid Ier.')); refuse(_alterer_personnages(d, (t, j, 'sources', 'pere', 'fait'), f'{row[1]} est {"fille" if row[1].endswith("Çelebi") else "fils"} de Bayezid Ier.'))
                if row[4]:
                    refuse(_alterer_personnages(d, (t, j, 'mere'), None)); refuse(_alterer_personnages(d, (t, j, 'sources', 'mere', 'fait'), f'{row[1]} est sœur de Bayezid Ier et de {next(o[1] for o in OTTOMANS if o[0] == row[4])}.')); refuse(_alterer_personnages(d, (t, j, 'sources', 'mere', 'fait'), f['sources']['mere']['fait'] + ' attribution réfutée')); refuse(_alterer_personnages(d, (t, j, 'sources', 'mere', 'fait'), f['sources']['mere']['fait'] + ' Attribution fausse')); refuse(_alterer_personnages(d, (t, j, 'mere'), 'personne-olivera-despina' if row[4] != 'olivera-despina' else 'personne-devletsah-hatun'))
                else:
                    refuse(_alterer_personnages(d, (t, j, 'mere'), 'personne-devletsah-hatun')); refuse(_alterer_personnages(d, (t, j, 'lacunes', 'mere'), f['lacunes']['mere'].replace('n’établissent pas', 'inconnu')))
    c = copy.deepcopy(d); next(x for x in c['familles'] if x['id'] == 'personne-devlet-hatun')['nom'] = 'Devletşah Hatun'; refuse(c)
    c = copy.deepcopy(d); next(x for x in c['familles'] if x['id'] == 'personne-mehmed-ier')['mere'] = 'personne-devletsah-hatun'; refuse(c)
    modele = next(f for f in d['familles'] if f['id'] == 'personne-marie-bourgogne')
    for nom, presence in [(n, 'vivante') for n in (*OTTO_EXCLUSIONS, 'Héritier inventé')] + [(n, 'decedee') for n in ('Ertuğrul Çelebi', 'Erhondu Hatun')]:
        for role in ('pere', 'conjoints'):
            c = copy.deepcopy(d); ajout = dict(copy.deepcopy(modele), id='personne-intruse', nom=nom, maison='grande-16', presence=presence, pere=None, mere=None, conjoints=[]); c['familles'].append(ajout)
            if role == 'pere': ajout['pere'] = PERE_B
            else: ajout['conjoints'] = [PERE_B]; next(x for x in c['liens'] if x['id'] == PERE_B)['conjoints'].append(ajout['id'])
            refuse(c, controle=True)
    for nom in ('Hundi Hatun', 'Oruz Hatun', 'Paşa Melek Hatun', 'Fatma Hatun', 'Erhondu Hatun'):
        c = copy.deepcopy(d); exc = next(x for x in c['etats'] if x['maison'] == 'grande-16')['exclusions']
        exc[nom] = exc.pop('Fille non nommée proposée à Ladislas'); refuse(c)


# Notices examinées le 1er novembre 2026 ; attentes indépendantes du catalogue.
WP = 'https://en.wikipedia.org/wiki/'
B_STEFAN, B_OSTOJA, B_KUJAVA, B_VITACA, B_OSTOJIC, B_RADIVOJ, B_THOMAS, B_MIRCEA, B_TOLMAY, B_MIHAIL, B_VLAD, B_ALDEA, B_RADU, B_IUGA = (WP + p for p in (
    'Stefan_Lazarevi%C4%87', 'Ostoja_of_Bosnia', 'Kujava_Radinovi%C4%87', 'Vita%C4%8Da', 'Stephen_Ostoji%C4%87_of_Bosnia', 'Radivoj_of_Bosnia', 'Thomas_of_Bosnia',
    'Mircea_the_Elder', 'Maria_Tolmay', 'Michael_I_of_Wallachia', 'Vlad_II_Dracul', 'Alexander_I_Aldea', 'Radu_II_of_Wallachia', 'Iuga_of_Moldavia'))
HORS, BALKANS_MAISONS = ('hors périmètre', 'aucune absence attestée'), ('grande-17', 'grande-18', 'grande-19', 'grande-20')
MIRCEA_ID, OSTOJA_ID = 'personne-grande-19', 'personne-grande-18'
# id : (nom, maison, naissance, père, mère, conjoints, sources {champ : (page, fait)}, repères des lacunes {champ : repères})
BALKANS = {
    'kujava-radinovic': ('Kujava Radinović', 'grande-18', None, None, None, (OSTOJA_ID,), {
        'identite': (B_KUJAVA, 'Kujava Radinović, épouse d’Étienne Ostoja, reine de Bosnie.'),
        'presence': (B_KUJAVA, 'Kujava Radinović, reine de 1399 à 1404 et de 1409 à 1415, encore active en 1422 ; vivante au 1er janvier 1400.'),
        'conjoints': (B_KUJAVA, 'Kujava Radinović et Étienne Ostoja sont mariés en 1399 : la notice la dit reine dans une charte du 5 février 1399, alors que la notice Vitača dit qu’Ostoja appelle encore Vitača son épouse en février 1399 et qu’elle est répudiée en septembre ; divergence conservée.')},
        {'naissance': ('Kujava Radinović', 'naissance inconnue'), 'pere': ('Kujava Radinović', 'père', *HORS), 'mere': ('Kujava Radinović', 'mère', *HORS)}),
    'maria-tolmay': ('Maria Tolmay', 'grande-19', None, None, None, (MIRCEA_ID,), {
        'identite': (B_TOLMAY, 'Maria Tolmay, épouse de Mircea l’Ancien ; le prénom Mara n’est qu’une reconstitution (Klara ou Anna possibles selon Hasan).'),
        'presence': (B_TOLMAY, 'Maria Tolmay visite son domaine du lac Balaton en 1400 et meurt en 1420 ou 1427 (divergence conservée) ; vivante au 1er janvier 1400, décès cité pour la sélection initiale.'),
        'conjoints': (B_TOLMAY, 'Maria Tolmay et Mircea l’Ancien sont conjoints ; aucune date d’union n’est inventée.')},
        {'naissance': ('Maria Tolmay', 'naissance inconnue'), 'pere': ('Maria Tolmay', 'père', *HORS), 'mere': ('Maria Tolmay', 'mère', *HORS)}),
    'mihail-ier': ('Mihail Ier', 'grande-19', None, MIRCEA_ID, 'personne-maria-tolmay', (), {
        'identite': (B_MIHAIL, 'Mihail Ier, fils de Mircea l’Ancien et de Maria Tolmay, seul fils légitime.'),
        'presence': (B_MIHAIL, 'Mihail Ier, co-régent en 1391 et mort en 1420 ; vivant au 1er janvier 1400, décès cité pour la sélection initiale.'),
        'pere': (B_MIHAIL, 'Mihail Ier est fils de Mircea l’Ancien et de Maria Tolmay.'), 'mere': (B_MIHAIL, 'Mihail Ier est fils de Mircea l’Ancien et de Maria Tolmay.')},
        {'naissance': ('Mihail Ier', 'naissance inconnue'), 'conjoints': ('Mihail Ier', *HORS)}),
    'vlad-dracul': ('Vlad II Dracul', 'grande-19', {'valeur': 'c. 1395', 'precision': 'vers'}, MIRCEA_ID, None, (), {
        'identite': (B_VLAD, 'Vlad II Dracul, fils illégitime de Mircea l’Ancien.'),
        'naissance': (B_VLAD, 'Vlad II Dracul : naissance c. 1395 ; le texte de la notice dit « avant 1395 », divergence conservée.'),
        'presence': (B_VLAD, 'Vlad II Dracul, otage chez Sigismond en 1395 ou 1396 ; vivant au 1er janvier 1400.'),
        'pere': (B_VLAD, 'Vlad II Dracul est fils illégitime de Mircea l’Ancien, père de « nombreux » fils illégitimes ; aucun autre n’est inventé.')},
        {'mere': ('Vlad II Dracul', 'mère inconnue', 'aucune mère inventée', 'aucune absence attestée'), 'conjoints': ('Vlad II Dracul', *HORS)}),
    'alexandru-aldea': ('Alexandru Ier Aldea', 'grande-19', {'valeur': '1397', 'precision': 'annee'}, MIRCEA_ID, None, (), {
        'identite': (B_ALDEA, 'Alexandru Ier Aldea, fils de Mircea l’Ancien.'),
        'naissance': (B_ALDEA, 'Alexandru Ier Aldea : naissance 1397.'),
        'presence': (B_ALDEA, 'Alexandru Ier Aldea, né en 1397 et mort en 1436 ; vivant au 1er janvier 1400, décès cité pour la sélection initiale.'),
        'pere': (B_ALDEA, 'Alexandru Ier Aldea est fils de Mircea l’Ancien.')},
        {'mere': ('Alexandru Ier Aldea', 'n’établit pas sa mère', 'aucune mère inventée', 'aucune absence attestée'), 'conjoints': ('Alexandru', *HORS)}),
}
# chef : (conjoints, sources {champ : (page, fait)}, repères des lacunes)
LIENS_B = {
    'grande-17': ((), {'presence': (B_STEFAN, 'Stefan Lazarević, prince de Serbie de 1389 à 1402 puis despote ; en fonction et vivant au 1er janvier 1400.')},
                  {'pere': ('Stefan Lazarević', 'parents et fratrie', *HORS), 'mere': ('Stefan Lazarević', 'parents et fratrie', *HORS),
                   'conjoints': ('aucun conjoint actif', '12 septembre 1405', 'catégorie de célibat', 'aucun veuvage')}),
    'grande-18': (('personne-kujava-radinovic',), {'conjoints': (B_OSTOJA, 'Étienne Ostoja et Kujava Radinović sont conjoints depuis 1399 ; Vitača, répudiée, n’est jamais conjointe active.'),
                  'presence': (B_OSTOJA, 'Étienne Ostoja, roi de Bosnie en premier règne de 1398 à 1404 ; en fonction et vivant au 1er janvier 1400.')},
                  {'pere': ('Étienne Ostoja', 'père', *HORS), 'mere': ('Étienne Ostoja', 'mère', *HORS)}),
    'grande-19': (('personne-maria-tolmay',), {'conjoints': (B_MIRCEA, 'Mircea l’Ancien et Maria Tolmay sont conjoints ; aucune date d’union n’est inventée.'),
                  'presence': (B_MIRCEA, 'Mircea l’Ancien, voïvode de Valachie de janvier 1397 à 1418 ; en fonction et vivant au 1er janvier 1400.')},
                  {'pere': ('Mircea l’Ancien', 'père', *HORS), 'mere': ('Mircea l’Ancien', 'mère', *HORS)}),
    'grande-20': ((), {'presence': (B_IUGA, 'Iuga, prince de Moldavie du 28 novembre 1399 au 19 juillet 1400 ; en fonction et vivant au 1er janvier 1400, aucune mort programmée.')},
                  {'pere': ('Iuga of Moldavia', 'Roman Ier ou Georges Koriatovitch', 'aucune filiation intégrée', 'aucune absence attestée'), 'mere': ('Iuga de Moldavie', 'mère', *HORS),
                   'conjoints': ('Iuga of Moldavia', 'aucun conjoint', 'ni célibat ni veuvage')}),
}
# maison : (conjoints, enfants, sources, repères des lacunes, exclusions {nom : ((page, fait), …)}) ; le motif réunit les faits
ETATS_B = {
    'grande-17': ('lacune', 'lacune', {}, {
        'conjoints': ('Stefan Lazarević', B_STEFAN, 'Helena Gattilusio', '12 septembre 1405', 'aucun conjoint actif', 'catégorie de célibat', 'aucun veuvage'),
        'enfants': ('Luttrell', B_STEFAN, '« apparemment »', 'jamais d’enfant', 'après 1405', 'aucune absence attestée')},
        {'Helena Gattilusio': ((B_STEFAN, 'Helena Gattilusio : épouse future de Stefan Lazarević, mariage du 12 septembre 1405, exclue du départ ; aucun événement programmé.'),)}),
    'grande-18': ('union', 'lacune', {'conjoints': (B_OSTOJA, 'Étienne Ostoja et Kujava Radinović sont mariés en 1399 ; état union. Divergence conservée : charte du 5 février 1399 (Kujava) contre Vitača encore appelée épouse en février 1399 puis répudiée en septembre.')},
        {'enfants': ('Étienne Ostoja', B_VITACA, 'inconnu si Vitača eut des enfants', 'Stephen Ostojić', 'Radivoj', 'aucune absence attestée')}, {
        'Vitača': ((B_VITACA, 'Vitača : épouse répudiée d’Étienne Ostoja en 1399, jamais conjointe active ; il l’appelle encore son épouse en février 1399.'), (B_KUJAVA, 'Vitača : Kujava Radinović est dite reine dans une charte du 5 février 1399 ; divergence conservée.')),
        'Jelena Nelipčić': ((B_OSTOJA, 'Jelena Nelipčić : épouse future d’Étienne Ostoja en 1416 ou 1417, exclue du départ.'),),
        'Stephen Ostojić': ((B_OSTOJIC, 'Stephen Ostojić : fils de Kujava Radinović, parents mariés en 1399, cité pour la première fois fin 1408 ; présence indéterminée au 1er janvier 1400.'),),
        'Radivoj': ((B_RADIVOJ, 'Radivoj : bâtard d’Étienne Ostoja « très probablement né avant 1410 » ; présence indéterminée au 1er janvier 1400.'),),
        'Thomas': ((B_THOMAS, 'Thomas : fils d’Étienne Ostoja né vers 1411, futur, exclu du départ.'),)}),
    'grande-19': ('union', 'documentes', {
        'conjoints': (B_MIRCEA, 'Mircea l’Ancien et Maria Tolmay sont conjoints ; état union, aucune date d’union inventée.'),
        'enfants': (B_MIRCEA, 'Enfants documentés de Mircea l’Ancien : Mihail Ier, seul fils légitime, Vlad II Dracul et Alexandru Ier Aldea, fils illégitimes ; ' + B_VLAD + ' dit Mircea père de « nombreux » fils illégitimes, aucun autre n’est inventé.')}, {}, {
        'Doamna Anca': ((B_MIRCEA, 'Doamna Anca : seconde épouse de Mircea nommée par l’infobox seule, sans date ni présence ; aucune conjointe active.'),),
        'Radu II Praznaglava': ((B_RADU, 'Radu II Praznaglava : naissance inconnue selon la notice ; présence indéterminée au 1er janvier 1400.'),),
        'Ana': ((B_MIRCEA, 'Ana : fille de Mircea l’Ancien citée par l’infobox, sans date ; présence indéterminée au 1er janvier 1400.'),),
        'Arina': ((B_MIRCEA, 'Arina : fille de Mircea l’Ancien citée par l’infobox, sans date ; présence indéterminée au 1er janvier 1400.'),)}),
    'grande-20': ('lacune', 'lacune', {}, {
        'conjoints': ('Iuga de Moldavie', B_IUGA, 'aucun conjoint', 'Roman Ier ou Georges Koriatovitch', 'ni célibat ni veuvage'),
        'enfants': ('Iuga de Moldavie', B_IUGA, 'aucun enfant', 'recherche limitée', 'aucune absence d’enfant attestée')}, {}),
}
BALKANS_DIVERGENCES = ('5 février 1399', 'février 1399', '1420 ou 1427', 'avant 1395', 'Roman Ier ou Georges Koriatovitch', 'Mara', 'Klara ou Anna', '12 septembre 1405', 'Luttrell', 'apparemment', 'ni célibat ni veuvage', 'aucun veuvage')
CHEF_EXCLUSION = {n: m for m, (*_, x) in ETATS_B.items() for n in x}
REPERES_B = {**{'personne-' + i: v[7] for i, v in BALKANS.items()}, **{'personne-' + m: v[2] for m, v in LIENS_B.items()}, **{m: v[3] for m, v in ETATS_B.items()}}


def _lacunes_b(sources, lacunes, attendues, reperes):
    assert set(sources) == set(lacunes) and set(attendues) | set(reperes) == set(sources) and not set(attendues) & set(reperes)
    for champ in sources:
        if champ in attendues: assert sources[champ] == dict(zip(('url', 'fait'), attendues[champ])) and lacunes[champ] is None
        else: assert sources[champ] is None and isinstance(lacunes[champ], str) and all(r in lacunes[champ] for r in reperes[champ])


def _balkans(fiches=None, etat=None):
    try: _balkans_controle(fiches, etat)
    except (KeyError, TypeError, AttributeError) as erreur: raise AssertionError(f'fiche balkanique malformée : {erreur!r}') from erreur


def _balkans_controle(fiches, etat):
    if fiches is not None:
        chefs = {'personne-' + m for m in BALKANS_MAISONS}
        assert chefs | {'personne-' + i for i in BALKANS} | {'personne-olivera-despina'} <= set(fiches)
        assert {i for i, f in fiches.items() if f.get('maison') in BALKANS_MAISONS and i not in chefs} == {'personne-' + i for i in BALKANS}
        for m in chefs:
            assert {i for i, f in fiches.items() if m in (f['pere'], f['mere']) or m in f['conjoints']} == {'personne-' + i for i, v in BALKANS.items() if m in v[3:6]} | {c for c in fiches[m]['conjoints']}
        for i, (nom, maison, naissance, pere, mere, conjoints, sources, reperes) in BALKANS.items():
            f = fiches['personne-' + i]
            assert (f['nom'], f['maison'], f['naissance'], f['pere'], f['mere'], tuple(f['conjoints']), f['presence']) == (nom, maison, naissance, pere, mere, conjoints, 'vivante')
            _lacunes_b(f['sources'], f['lacunes'], sources, reperes)
        for m, (conjoints, sources, reperes) in LIENS_B.items():
            c = fiches['personne-' + m]
            assert (c['pere'], c['mere'], tuple(c['conjoints']), c['presence']) == (None, None, conjoints, 'vivante')
            champs = ('pere', 'mere', 'conjoints', 'presence')
            _lacunes_b({k: c['sources'][k] for k in champs}, {k: c['lacunes'][k] for k in champs}, sources, reperes)
        olivera = fiches['personne-olivera-despina']
        assert (olivera['maison'], olivera['pere'], olivera['mere'], olivera['conjoints']) == ('grande-16', None, None, ['personne-grande-16'])
        assert 'Lazar' in olivera['sources']['identite']['fait'] and not any(f['id'] != olivera['id'] and 'Olivera' in (f.get('nom') or '') for f in fiches.values())
    if etat is not None:
        conjoints, enfants, sources, reperes, exclusions = ETATS_B[etat['maison']]
        assert (etat['conjoints'], etat['enfants']) == (conjoints, enfants) and set(etat['sources']) == set(etat['lacunes']) == {'conjoints', 'enfants'}
        _lacunes_b(etat['sources'], etat['lacunes'], sources, reperes)
        assert set(etat['exclusions']) == set(exclusions)
        for nom, faits in exclusions.items():
            x = etat['exclusions'][nom]
            assert set(x) == {'motif', 'sources'} and x['motif'] == ' '.join(f for _, f in faits) and x['sources'] == [{'url': u, 'fait': f} for u, f in faits]


def _feuilles(objet, chemin=()):
    if isinstance(objet, dict):
        for k, v in objet.items(): yield from _feuilles(v, chemin + (k,))
    elif isinstance(objet, list) and objet:
        for k, v in enumerate(objet): yield from _feuilles(v, chemin + (k,))
    else: yield chemin


def test_familles_historiques_balkans():
    d = _personnages()
    def resolus(c):
        return c['familles'] + [{**h, **l} for l in c['liens'] for h in c['chefs'] if l['id'] == 'personne-' + h['maison']]
    def refuse(c, controle=False):
        if controle: assert _controler_famille(resolus(c))
        with pytest.raises(AssertionError): _familles_historiques(c['familles'], c['liens']); _etats_historiques(c['etats'])
    def altere(chemin, valeur):
        refuse(_alterer_personnages(d, chemin, valeur))
    _familles_historiques(d['familles'], d['liens']); _etats_historiques(d['etats'])
    ids = {'personne-' + i for i in BALKANS} | {'personne-' + m for m in BALKANS_MAISONS} | set(BALKANS_MAISONS)
    for t in ('familles', 'liens', 'etats'):
        for j, f in enumerate(d[t]):
            if f.get('id', f.get('maison')) not in ids: continue
            altere((t,), d[t][:j] + d[t][j+1:]); altere((t,), d[t] + [copy.deepcopy(f)])
            for chemin in _feuilles(f):
                valeur = f
                for cle in chemin: valeur = valeur[cle]
                altere((t, j, *chemin), ['personne-grande-9'] if valeur == [] else 'Altéré')
                if isinstance(valeur, str):
                    for repere in BALKANS_DIVERGENCES:
                        if repere in valeur: altere((t, j, *chemin), valeur.replace(repere, 'inconnu'))
            for nom in f.get('exclusions', {}): altere((t, j, 'exclusions', nom), 'SUPPRIMER')
            if t == 'etats':
                for champ in (k for k in ('conjoints', 'enfants') if f[k] == 'lacune'):
                    for etat in ('absence_attestee', 'union', 'veuvage'): altere((t, j, champ), etat)
            for champ, liste in REPERES_B[f.get('id', f.get('maison'))].items():
                for repere in liste: altere((t, j, 'lacunes', champ), f['lacunes'][champ].replace(repere, 'inconnu'))
    olivera = next(f for f in d['familles'] if f['id'] == 'personne-olivera-despina')
    altere(('familles',), d['familles'] + [dict(copy.deepcopy(olivera), id='personne-olivera-bis')])
    altere(('familles',), d['familles'] + [dict(copy.deepcopy(olivera), nom='Olivera Lazarević', id='personne-olivera-lazarevic')])
    for lien in ('pere', 'mere'):
        refuse(_alterer_personnages(d, ('familles', d['familles'].index(olivera), lien), 'personne-grande-17'), controle=True)
        refuse(_alterer_personnages(d, ('liens', [x['id'] for x in d['liens']].index('personne-grande-17'), lien), 'personne-olivera-despina'), controle=True)
    for fiche, mere in [('mihail-ier', None), ('mihail-ier', 'personne-olivera-despina'), ('vlad-dracul', 'personne-maria-tolmay'), ('alexandru-aldea', 'personne-maria-tolmay')]:
        c = copy.deepcopy(d); next(x for x in c['familles'] if x['id'] == 'personne-' + fiche)['mere'] = mere; refuse(c, controle=True)
    modele = next(f for f in d['familles'] if f['id'] == 'personne-marie-bourgogne')
    for nom, maison in CHEF_EXCLUSION.items():
        for role in ('pere', 'conjoints'):
            c = copy.deepcopy(d); ajout = dict(copy.deepcopy(modele), id='personne-intruse', nom=nom, maison=maison, presence='vivante', pere=None, mere=None, conjoints=[]); c['familles'].append(ajout)
            if role == 'pere': ajout['pere'] = 'personne-' + maison
            else: ajout['conjoints'] = ['personne-' + maison]; next(x for x in c['liens'] if x['id'] == 'personne-' + maison)['conjoints'].append(ajout['id'])
            assert _controler_famille(resolus(c))
            with pytest.raises(AssertionError): _balkans({f['id']: f for f in c['familles'] + c['liens']})
            refuse(c)


# Notices examinées le 11 novembre 2026 ; attentes indépendantes du catalogue. Tlemcen n'a ni fiche, ni lien, ni état.
M_FARIS, M_AHMAD, M_MUNTASIR, M_UTHMAN_H, M_UTHMAN, M_ABDALHAQQ = (WP + p for p in (
    'Abu_Faris_Abd_al-Aziz_II', 'Abu_al-Abbas_Ahmad_II', 'Abu_Abd-Allah_Muhammad_al-Muntasir', 'Abu_%27Amr_%27Uthman', 'Abu_Said_Uthman_III', 'Abd_al-Haqq_II'))
MAGHREB_MAISONS, TLEMCEN = ('grande-23', 'grande-25'), 'grande-24'
CHAMPS_FAMILIAUX = {'pere', 'mere', 'conjoints', 'presence', 'etat_familial'}
# chef : (conjoints, sources {champ : (page, fait)}, repères des lacunes)
LIENS_M = {
    'grande-23': ((), {'presence': (M_FARIS, 'Abu Faris Abd al-Aziz II, souverain hafside de juin 1394 à juillet 1434 ; en fonction et vivant au 1er janvier 1400, aucune mort programmée.')},
                  {'pere': ('Abu Faris Abd al-Aziz II', M_AHMAD, 'Abu al-Abbas Ahmad II', '3 juin 1394', 'successeur', 'hors périmètre', 'aucune fiche créée', 'aucune absence attestée'),
                   'mere': ('Abu Faris Abd al-Aziz II', 'mère', *HORS),
                   'conjoints': ('Abu Faris Abd al-Aziz II', M_FARIS, 'aucune épouse', 'ni célibat ni veuvage')}),
    'grande-25': ((), {'presence': (M_UTHMAN, 'Abu Said Uthman III, sultan mérinide du 19 mars 1398 au 21 octobre 1420 ; en fonction et vivant au 1er janvier 1400, aucune mort programmée. La notice le dit monté sur le trône « à seize ans » (Ibn Khaldūn), alors que la naissance de 1383 lui donne quinze ans en mars 1398 ; divergence conservée.')},
                  {'pere': ('Abu Said Uthman III', 'ibn Abi l-Abbas', 'infobox', 'Abu Amir Abdallah', 'Gibraltar en 1410', 'hors périmètre', 'aucune absence attestée'),
                   'mere': ('Abu Said Uthman III', 'mère', *HORS),
                   'conjoints': ('Abu Said Uthman III', M_UTHMAN, 'infobox', 'ni célibat ni veuvage')}),
}
# maison : (conjoints, enfants, sources, repères des lacunes, exclusions {nom : ((page, fait), …)}) ; le motif réunit les faits
ETATS_M = {
    'grande-23': ('lacune', 'lacune', {}, {
        'conjoints': ('Abu Faris Abd al-Aziz II', M_FARIS, 'aucune épouse', 'ni célibat ni veuvage'),
        'enfants': ('Abu Faris Abd al-Aziz II', M_MUNTASIR, 'Abu Abdallah Muhammad al-Mansur', 'mort en 1430', 'un autre de ses fils', 'al-Mu’tamid', 'sans dates ni filiation écrite', 'aucune absence attestée')}, {
        'Abu Abdallah Muhammad al-Mansur': ((M_MUNTASIR, 'Abu Abdallah Muhammad al-Mansur : fils et héritier d’Abu Faris Abd al-Aziz II, mort en 1430 avant son père ; naissance inconnue.'),
                                            (M_UTHMAN_H, 'Abu Abdallah Muhammad al-Mansur : héritier initial d’Abu Faris, mort en 1430 ; la notice ne donne pas sa naissance, présence indéterminée au 1er janvier 1400.'))}),
    'grande-25': ('lacune', 'lacune', {}, {
        'conjoints': ('Abu Said Uthman III', M_UTHMAN, 'infobox', 'ni célibat ni veuvage'),
        'enfants': ('Abu Said Uthman III', M_UTHMAN, 'Abd al-Haqq II', '1419', 'qu’un enfant d’un an', 'ne prouve rien pour 1400', 'aucune absence attestée')}, {
        'Abd al-Haqq II': ((M_ABDALHAQQ, 'Abd al-Haqq II : fils d’Abu Said Uthman III, né en 1419, futur, exclu du départ ; aucun événement programmé.'),
                           (M_UTHMAN, 'Abd al-Haqq II : fils et héritier d’Abu Said Uthman III, enfant d’un an à la mort du sultan en 1420 ; né après le départ.'))}),
}
MAGHREB_DIVERGENCES = ('3 juin 1394', 'à seize ans', '1419', 'un autre de ses fils', 'al-Mu’tamid', 'ni célibat ni veuvage', 'aucune absence attestée')
CHEF_EXCLUSION_M = {n: m for m, (*_, x) in ETATS_M.items() for n in x}
REPERES_M = {**{'personne-' + m: v[2] for m, v in LIENS_M.items()}, **{m: v[3] for m, v in ETATS_M.items()}}


def _maghreb(fiches=None, etat=None):
    try: _maghreb_controle(fiches, etat)
    except (KeyError, TypeError, AttributeError) as erreur: raise AssertionError(f'fiche maghrébine malformée : {erreur!r}') from erreur


def _maghreb_controle(fiches, etat):
    if fiches is not None:
        chefs = {'personne-' + m for m in MAGHREB_MAISONS}
        assert chefs <= set(fiches)
        tlemcen = 'personne-' + TLEMCEN
        assert not any(f.get('maison') == TLEMCEN or f['id'] == tlemcen or tlemcen in (f.get('pere'), f.get('mere')) or tlemcen in f.get('conjoints', ()) for f in fiches.values())
        for chef in chefs:
            assert not any(chef in (f['pere'], f['mere']) or chef in f['conjoints'] for f in fiches.values())
        for m, (conjoints, sources, reperes) in LIENS_M.items():
            c = fiches['personne-' + m]
            assert (c['pere'], c['mere'], tuple(c['conjoints']), c['presence']) == (None, None, conjoints, 'vivante')
            champs = ('pere', 'mere', 'conjoints', 'presence')
            _lacunes_b({k: c['sources'][k] for k in champs}, {k: c['lacunes'][k] for k in champs}, sources, reperes)
    if etat is not None:
        conjoints, enfants, sources, reperes, exclusions = ETATS_M[etat['maison']]
        assert (etat['conjoints'], etat['enfants']) == (conjoints, enfants) and set(etat['sources']) == set(etat['lacunes']) == {'conjoints', 'enfants'}
        _lacunes_b(etat['sources'], etat['lacunes'], sources, reperes)
        assert set(etat['exclusions']) == set(exclusions)
        for nom, faits in exclusions.items():
            x = etat['exclusions'][nom]
            assert set(x) == {'motif', 'sources'} and x['motif'] == ' '.join(f for _, f in faits) and x['sources'] == [{'url': u, 'fait': f} for u, f in faits]


def _preuve_monde_maghreb(personnes):
    _familles_historiques([f for f in personnes if f['id'] != 'personne-' + f['maison']],
                          [f for f in personnes if f['id'] == 'personne-' + f['maison'] and CHAMPS_FAMILIAUX & f.keys()])
    _etats_historiques([f['etat_familial'] for f in personnes if 'etat_familial' in f])
    assert not any(f['maison'] == TLEMCEN and CHAMPS_FAMILIAUX & f.keys() for f in personnes)


def test_familles_historiques_maghreb(tmp_path):
    from sim import personnages as p
    d, monde = _personnages(), World.charger(0)
    def resolus(c):
        return c['familles'] + [{**h, **l} for l in c['liens'] for h in c['chefs'] if l['id'] == 'personne-' + h['maison']]
    def refuse(c, controle=False):
        if controle: assert _controler_famille(resolus(c))
        with pytest.raises(AssertionError): _familles_historiques(c['familles'], c['liens']); _etats_historiques(c['etats'])
    def altere(chemin, valeur):
        refuse(_alterer_personnages(d, chemin, valeur))
    _familles_historiques(d['familles'], d['liens']); _etats_historiques(d['etats'])
    _maghreb({f['id']: f for f in d['familles'] + d['liens']})
    assert len(d['familles']) == 102 and len(d['liens']) == len(d['etats']) == 29
    assert not any(f['maison'] == TLEMCEN for f in d['familles']) and not any(l['id'] == 'personne-' + TLEMCEN for l in d['liens']) and not any(e['maison'] == TLEMCEN for e in d['etats'])
    chef = next(c for c in d['chefs'] if c['maison'] == TLEMCEN)
    # Depuis #1052, le chef de Tlemcen est nommé (Abu Muhammad Ier) : sa fiche porte une source, plus de lacune d'identité.
    assert chef['nom'] == 'Abu Muhammad I' and chef['lacunes']['identite'] is None and chef['sources']['identite']['url'] == 'https://en.wikipedia.org/wiki/Zayyanid_dynasty' and chef['sources']['identite']['fait'].strip()
    _preuve_monde_maghreb(list(monde.personnages))
    # Tlemcen n'a dans le monde que son chef (#1052), sans aucun champ familial.
    assert [f['id'] for f in monde.personnages if f['maison'] == TLEMCEN] == ['personne-' + TLEMCEN]
    ids = {'personne-' + m for m in MAGHREB_MAISONS} | set(MAGHREB_MAISONS)
    for t in ('liens', 'etats'):
        for j, f in enumerate(d[t]):
            if f.get('id', f.get('maison')) not in ids: continue
            altere((t,), d[t][:j] + d[t][j+1:]); altere((t,), d[t] + [copy.deepcopy(f)])
            for chemin in _feuilles(f):
                valeur = f
                for cle in chemin: valeur = valeur[cle]
                altere((t, j, *chemin), ['personne-grande-9'] if valeur == [] else 'Altéré')
                if isinstance(valeur, str):
                    for repere in MAGHREB_DIVERGENCES:
                        if repere in valeur: altere((t, j, *chemin), valeur.replace(repere, 'inconnu'))
            for nom in f.get('exclusions', {}): altere((t, j, 'exclusions', nom), 'SUPPRIMER')
            if t == 'etats':
                for champ in ('conjoints', 'enfants'):
                    for etat in ('absence_attestee', 'union', 'veuvage'): altere((t, j, champ), etat)
            for champ, liste in REPERES_M[f.get('id', f.get('maison'))].items():
                for repere in liste: altere((t, j, 'lacunes', champ), f['lacunes'][champ].replace(repere, 'inconnu'))
    modele = next(f for f in d['familles'] if f['id'] == 'personne-marie-bourgogne')
    for nom, maison in CHEF_EXCLUSION_M.items():
        for role in ('pere', 'conjoints'):
            c = copy.deepcopy(d); ajout = dict(copy.deepcopy(modele), id='personne-intruse', nom=nom, maison=maison, presence='vivante', pere=None, mere=None, conjoints=[]); c['familles'].append(ajout)
            if role == 'pere': ajout['pere'] = 'personne-' + maison
            else: ajout['conjoints'] = ['personne-' + maison]; next(x for x in c['liens'] if x['id'] == 'personne-' + maison)['conjoints'].append(ajout['id'])
            assert _controler_famille(resolus(c))
            with pytest.raises(AssertionError): _maghreb({f['id']: f for f in c['familles'] + c['liens']})
            refuse(c)
    # Tlemcen : ni fiche, ni complément, ni état.
    lien, etat = (next(x for x in d[t] if x.get('id', x.get('maison')) in ('personne-grande-25', 'grande-25')) for t in ('liens', 'etats'))
    c = copy.deepcopy(d); c['familles'].append(dict(copy.deepcopy(modele), id='personne-intruse', maison=TLEMCEN))
    with pytest.raises(AssertionError): _maghreb({f['id']: f for f in c['familles'] + c['liens']})
    refuse(c)
    c = copy.deepcopy(d); c['liens'].append(dict(copy.deepcopy(lien), id='personne-' + TLEMCEN))
    with pytest.raises(AssertionError): _maghreb({f['id']: f for f in c['familles'] + c['liens']})
    refuse(c)
    c = copy.deepcopy(d); c['etats'].append(dict(copy.deepcopy(etat), maison=TLEMCEN))
    with pytest.raises(AssertionError): _maghreb(etat=c['etats'][-1])
    refuse(c)
    # Tlemcen a un chef depuis #1052 : le chargeur ne refuse plus son état, mais celui d'une maison restée sans chef (`grande-21`).
    c = copy.deepcopy(d); c['etats'].append(dict(copy.deepcopy(etat), maison='grande-21'))
    chemin = tmp_path / 'sans-chef.json'
    chemin.write_text(json.dumps(c), encoding='utf-8')
    with pytest.raises(ValueError): p.charger_catalogue(monde.maisons, chemin)
    # Dans le monde construit, une personne de Tlemcen ne porte aucun champ familial.
    base = next(f for f in monde.personnages if f['id'] == 'personne-grande-25')
    for identifiant in ('personne-' + TLEMCEN, 'personne-intruse'):
        for champ in ('presence', 'etat_familial'):
            clone = {k: copy.deepcopy(v) for k, v in base.items() if k not in CHAMPS_FAMILIAUX - {champ}}
            clone.update(id=identifiant, maison=TLEMCEN)
            with pytest.raises(AssertionError): _preuve_monde_maghreb(list(monde.personnages) + [clone])


# Notices examinées le 12 novembre 2026 ; attentes indépendantes du catalogue. La Horde d'Or n'a ni fiche, ni complément, ni état.
MCA_FARAJ, MCA_JANUS, MCA_ANGLESIA, MCA_ALBERT, MCA_JOANNA, MCA_ALBERTV, MCA_SHADI = (WP + p for p in (
    'An-Nasir_Faraj', 'Janus,_King_of_Cyprus', 'Anglesia_Visconti', 'Albert_IV_of_Austria', 'Joanna_Sophie_of_Bavaria', 'Albert_II_of_Germany', 'Shadi_Beg'))
MCA_MAISONS, HORDE = ('grande-22', 'grande-26', 'grande-30'), 'grande-21'
HORDE_LACUNE = 'https://en.wikipedia.org/wiki/Shadi_Beg : la section Reign place la succession de Timur Qutluq par Shadi Beg fin 1399 ou début 1400 ; titulaire au 1er janvier non départagé, malgré l’infobox 1399–1407.'
ALBERT_ID, JEANNE_SOPHIE_ID = 'personne-grande-30', 'personne-jeanne-sophie-baviere'
ENFANTS_MCA = ('marguerite-autriche', 'albert-v')
# id : (nom, maison, naissance, père, mère, conjoints, sources {champ : (page, fait)}, repères des lacunes {champ : repères})
FICHES_MCA = {
    'jeanne-sophie-baviere': ('Jeanne-Sophie de Bavière', 'grande-30', {'valeur': 'vers 1373', 'precision': 'vers'}, None, None, (ALBERT_ID,), {
        'identite': (MCA_JOANNA, 'Jeanne-Sophie de Bavière, fille d’Albert Ier de Bavière et de Marguerite de Brieg, épouse d’Albert IV d’Autriche.'),
        'naissance': (MCA_JOANNA, 'Jeanne-Sophie de Bavière : naissance vers 1373.'),
        'presence': (MCA_JOANNA, 'Jeanne-Sophie de Bavière, vers 1373 – 15 novembre 1410 ; vivante au 1er janvier 1400, décès cité pour la sélection initiale.'),
        'conjoints': (MCA_ALBERT, 'Jeanne-Sophie de Bavière et Albert IV d’Autriche sont mariés : le 24 avril 1390 selon ' + MCA_ALBERT + ', le 13 juin 1395 selon ' + MCA_JOANNA + ' ; avant le départ dans les deux cas, divergence conservée.')},
        {'pere': ('Jeanne-Sophie de Bavière', 'Albert Ier de Bavière', *HORS), 'mere': ('Jeanne-Sophie de Bavière', 'Marguerite de Brieg', *HORS)}),
    'marguerite-autriche': ("Marguerite d'Autriche", 'grande-30', {'valeur': '1395-06-26', 'precision': 'jour'}, ALBERT_ID, JEANNE_SOPHIE_ID, (), {
        'identite': (MCA_ALBERT, 'Marguerite d’Autriche, fille d’Albert IV d’Autriche et de Jeanne-Sophie de Bavière.'),
        'naissance': (MCA_ALBERT, 'Marguerite d’Autriche : née à Vienne le 26 juin 1395, date que donne aussi ' + MCA_JOANNA + '.'),
        'presence': (MCA_ALBERT, 'Marguerite d’Autriche, morte le 24 décembre 1447 ; vivante au 1er janvier 1400, décès cité pour la sélection initiale.'),
        'pere': (MCA_ALBERT, 'Marguerite d’Autriche est fille d’Albert IV d’Autriche et de Jeanne-Sophie de Bavière.'),
        'mere': (MCA_ALBERT, 'Marguerite d’Autriche est fille d’Albert IV d’Autriche et de Jeanne-Sophie de Bavière.')},
        {'conjoints': ('Marguerite d’Autriche', 'mariage futur', 'Henri XVI de Bavière', '25 novembre 1412', 'aucune absence attestée')}),
    'albert-v': ("Albert V d'Autriche", 'grande-30', {'valeur': '1397-08', 'precision': 'mois'}, ALBERT_ID, JEANNE_SOPHIE_ID, (), {
        'identite': (MCA_ALBERT, 'Albert V d’Autriche, fils d’Albert IV d’Autriche et de Jeanne-Sophie de Bavière, héritier du duché.'),
        'naissance': (MCA_ALBERT, 'Albert V d’Autriche : né en août 1397, le 16 août selon ' + MCA_ALBERT + ' et ' + MCA_JOANNA + ', le 10 août selon ' + MCA_ALBERTV + ' ; aucun jour n’est choisi, divergence conservée.'),
        'presence': (MCA_ALBERT, 'Albert V d’Autriche, mort le 27 octobre 1439 ; vivant au 1er janvier 1400, décès cité pour la sélection initiale.'),
        'pere': (MCA_ALBERT, 'Albert V d’Autriche est fils d’Albert IV d’Autriche et de Jeanne-Sophie de Bavière.'),
        'mere': (MCA_ALBERT, 'Albert V d’Autriche est fils d’Albert IV d’Autriche et de Jeanne-Sophie de Bavière.')},
        {'conjoints': ('Albert V d’Autriche', 'mariage futur', 'Élisabeth de Luxembourg', '1422', 'aucune absence attestée')}),
}
# chef : (conjoints, sources {champ : (page, fait)}, repères des lacunes)
LIENS_MCA = {
    'grande-22': ((), {'presence': (MCA_FARAJ, 'Faraj, sultan mamelouk depuis juin 1399, premier règne jusqu’au 20 septembre 1405, tué le 23 mai 1412 ; en fonction et vivant au 1er janvier 1400, aucune mort programmée.')},
                  {'pere': ('An-Nasir Faraj', MCA_FARAJ, 'Barquq', 'mort subitement en juin 1399', 'hors périmètre', 'aucune fiche créée', 'aucune absence attestée'),
                   'mere': ('An-Nasir Faraj', MCA_FARAJ, 'Khawand Shirin', *HORS),
                   'conjoints': ('An-Nasir Faraj', MCA_FARAJ, 'Khawand Fatima', 'Ibn Taghribirdi', 'sans date d’union', 'ni célibat ni veuvage')}),
    'grande-26': ((), {'presence': (MCA_JANUS, 'Janus, couronné le 11 novembre 1398, roi de Chypre jusqu’en 1432 ; en fonction et vivant au 1er janvier 1400, aucune mort programmée.')},
                  {'pere': ('Janus de Lusignan', MCA_JANUS, 'Jacques Ier de Chypre', 'mort le 9 septembre 1398', 'hors périmètre', 'aucune fiche créée', 'aucune absence attestée'),
                   'mere': ('Janus de Lusignan', MCA_JANUS, 'Helvis de Brunswick-Grubenhagen', *HORS),
                   'conjoints': ('Janus de Lusignan', MCA_JANUS, MCA_ANGLESIA, 'Anglesia Visconti', 'après janvier 1400', '1401 à 1407', 'aucun conjoint actif', 'ni célibat ni veuvage')}),
    'grande-30': ((JEANNE_SOPHIE_ID,), {
        'conjoints': (MCA_ALBERT, 'Albert IV d’Autriche est marié à Jeanne-Sophie de Bavière : le 24 avril 1390 selon ' + MCA_ALBERT + ', le 13 juin 1395 selon ' + MCA_JOANNA + ' ; avant le départ dans les deux cas, divergence conservée.'),
        'presence': (MCA_ALBERT, 'Albert IV, duc d’Autriche de 1395 à sa mort, le 14 septembre 1404 ; en fonction et vivant au 1er janvier 1400, aucune mort programmée.')},
        {'pere': ('Albert IV d’Autriche', MCA_ALBERT, 'Albert III', 'son prédécesseur', 'hors périmètre', 'aucune fiche créée', 'aucune absence attestée'),
         'mere': ('Albert IV d’Autriche', MCA_ALBERT, 'Beatrix de Nuremberg', *HORS)}),
}
# maison : (conjoints, enfants, sources, repères des lacunes, exclusions {nom : ((page, fait), …)}) ; le motif réunit les faits
ETATS_MCA = {
    'grande-22': ('lacune', 'lacune', {}, {
        'conjoints': ('An-Nasir Faraj', MCA_FARAJ, 'Khawand Fatima', 'sans date d’union', 'ni célibat ni veuvage'),
        'enfants': ('An-Nasir Faraj', MCA_FARAJ, 'Ghars ad-Din Khalil', 'Khawand Asiya', 'Khawand Satita', '1416', 'Khawand Shakra', '1482', 'sans aucune naissance', 'treize ans', 'aucune absence attestée')}, {
        'Khawand Fatima': ((MCA_FARAJ, 'Khawand Fatima : épouse de Faraj, sœur d’Ibn Taghribirdi, union non datée, remariée à Inal Nauruzi après 1412 ; épouse active au départ indéterminée, exclue.'),),
        'Lâ Aflaha man Zalama': ((MCA_FARAJ, 'Lâ Aflaha man Zalama : concubine de Faraj, mère de Ghars ad-Din Khalil, union non datée ; le schéma n’a pas de concubinage, elle n’est ni conjointe ni mère référencée.'),),
        'Thuraiya': ((MCA_FARAJ, 'Thuraiya : concubine de Faraj, mère de Khawand Asiya, union non datée ; le schéma n’a pas de concubinage, elle n’est ni conjointe ni mère référencée.'),),
        'Ghars ad-Din Khalil': ((MCA_FARAJ, 'Ghars ad-Din Khalil : fils de Faraj, sans naissance connue ; présence indéterminée au 1er janvier 1400.'),),
        'Khawand Asiya': ((MCA_FARAJ, 'Khawand Asiya : fille de Faraj, sans naissance connue ; présence indéterminée au 1er janvier 1400.'),),
        'Khawand Satita': ((MCA_FARAJ, 'Khawand Satita : fille de Faraj, morte en 1416, sans naissance connue ; présence indéterminée au 1er janvier 1400.'),),
        'Khawand Shakra': ((MCA_FARAJ, 'Khawand Shakra : fille de Faraj, morte en 1482, sans naissance connue ; présence indéterminée au 1er janvier 1400.'),)}),
    'grande-26': ('lacune', 'lacune', {}, {
        'conjoints': ('Janus de Lusignan', MCA_JANUS, MCA_ANGLESIA, 'Anglesia Visconti', 'après janvier 1400', 'aucun conjoint actif', 'ni célibat ni veuvage'),
        'enfants': ('Janus de Lusignan', MCA_JANUS, 'neuf enfants', 'Charlotte de Bourbon', '1411', 'Aloysius', '1408', 'Guy', '1410', 'sans nom ni naissance', '1427', 'aucune absence attestée')}, {
        'Anglesia Visconti': ((MCA_JANUS, 'Anglesia Visconti : épouse future de Janus, mariée après janvier 1400, exclue du départ ; aucun événement programmé.'),
                              (MCA_ANGLESIA, 'Anglesia Visconti : union avec Janus annulée entre 1407 et 1409, sans enfant ; mariée après janvier 1400.')),
        'Charlotte de Bourbon': ((MCA_JANUS, 'Charlotte de Bourbon : épouse future de Janus, mariée en 1411, exclue du départ ; aucun événement programmé.'),),
        'Jean II': ((MCA_JANUS, 'Jean II : fils de Janus et de Charlotte de Bourbon, né en 1414, futur et héritier, exclu du départ ; aucun événement programmé.'),),
        'Aloysius': ((MCA_JANUS, 'Aloysius : fils de Janus hors mariage, né en 1408, futur, exclu du départ ; aucun événement programmé.'),),
        'Guy': ((MCA_JANUS, 'Guy : fils de Janus hors mariage, né en 1410, futur, exclu du départ ; aucun événement programmé.'),)}),
    'grande-30': ('union', 'documentes', {
        'conjoints': (MCA_ALBERT, 'Albert IV d’Autriche et Jeanne-Sophie de Bavière sont mariés ; état union : le 24 avril 1390 selon ' + MCA_ALBERT + ', le 13 juin 1395 selon ' + MCA_JOANNA + ', avant le départ dans les deux cas.'),
        'enfants': (MCA_ALBERT + '#Family_and_children', 'Albert IV d’Autriche a deux enfants documentés, Marguerite (1395) et Albert V (1397), nés de Jeanne-Sophie de Bavière ; aucun autre n’est inventé.')}, {}, {}),
}
MCA_DIVERGENCES = ('juin 1399', 'Khawand Shirin', '9 septembre 1398', 'après janvier 1400', 'neuf enfants', '24 avril 1390', '13 juin 1395', '16 août', '10 août', 'treize ans', 'ni célibat ni veuvage', 'aucune absence attestée')
CHEF_EXCLUSION_MCA = {n: m for m, (*_, x) in ETATS_MCA.items() for n in x}
REPERES_MCA = {**{'personne-' + i: v[7] for i, v in FICHES_MCA.items()}, **{'personne-' + m: v[2] for m, v in LIENS_MCA.items()}, **{m: v[3] for m, v in ETATS_MCA.items()}}


def _mca(fiches=None, etat=None):
    try: _mca_controle(fiches, etat)
    except (KeyError, TypeError, AttributeError) as erreur: raise AssertionError(f'fiche mamelouke, chypriote ou autrichienne malformée : {erreur!r}') from erreur


def _mca_controle(fiches, etat):
    if fiches is not None:
        chefs = {'personne-' + m for m in MCA_MAISONS}
        assert chefs | {'personne-' + i for i in FICHES_MCA} <= set(fiches)
        assert {i for i, f in fiches.items() if f.get('maison') in MCA_MAISONS and i not in chefs} == {'personne-' + i for i in FICHES_MCA}
        for i, (nom, maison, naissance, pere, mere, conjoints, sources, reperes) in FICHES_MCA.items():
            f = fiches['personne-' + i]
            assert (f['nom'], f['maison'], f['naissance'], f['pere'], f['mere'], tuple(f['conjoints']), f['presence']) == (nom, maison, naissance, pere, mere, conjoints, 'vivante')
            _lacunes_b(f['sources'], f['lacunes'], sources, reperes)
        for m, (conjoints, sources, reperes) in LIENS_MCA.items():
            c = fiches['personne-' + m]
            assert (c['pere'], c['mere'], tuple(c['conjoints']), c['presence']) == (None, None, conjoints, 'vivante')
            champs = ('pere', 'mere', 'conjoints', 'presence')
            _lacunes_b({k: c['sources'][k] for k in champs}, {k: c['lacunes'][k] for k in champs}, sources, reperes)
        assert {i for i, f in fiches.items() if ALBERT_ID in (f['pere'], f['mere']) or ALBERT_ID in f['conjoints']} == {'personne-' + i for i in ENFANTS_MCA} | {JEANNE_SOPHIE_ID}
        assert {i for i, f in fiches.items() if JEANNE_SOPHIE_ID in (f['pere'], f['mere']) or JEANNE_SOPHIE_ID in f['conjoints']} == {'personne-' + i for i in ENFANTS_MCA} | {ALBERT_ID}
        assert not any(f['pere'] == c or f['mere'] == c or c in f['conjoints'] for c in ('personne-grande-22', 'personne-grande-26') for f in fiches.values())
        # La Horde d'Or n'a ni fiche, ni complément : son chef est inconnu, aucune famille n'est inventée.
        horde = 'personne-' + HORDE
        assert not any(f.get('maison') == HORDE or f['id'] == horde or horde in (f['pere'], f['mere']) or horde in f['conjoints'] for f in fiches.values())
        assert not any('Jeanne-Sophie' in (f.get('nom') or '') for f in fiches.values() if f['id'] != JEANNE_SOPHIE_ID)
        assert not any(f.get('nom') in ('Sophie de Bavière', 'Jeanne de Bavière') for f in fiches.values() if f.get('maison') == 'grande-30')
    if etat is not None:
        conjoints, enfants, sources, reperes, exclusions = ETATS_MCA[etat['maison']]
        assert (etat['conjoints'], etat['enfants']) == (conjoints, enfants) and set(etat['sources']) == set(etat['lacunes']) == {'conjoints', 'enfants'}
        _lacunes_b(etat['sources'], etat['lacunes'], sources, reperes)
        assert set(etat['exclusions']) == set(exclusions)
        for nom, faits in exclusions.items():
            x = etat['exclusions'][nom]
            assert set(x) == {'motif', 'sources'} and x['motif'] == ' '.join(f for _, f in faits) and x['sources'] == [{'url': u, 'fait': f} for u, f in faits]


def _preuve_monde_mca(personnes):
    _familles_historiques([f for f in personnes if f['id'] != 'personne-' + f['maison']],
                          [f for f in personnes if f['id'] == 'personne-' + f['maison'] and CHAMPS_FAMILIAUX & f.keys()])
    _etats_historiques([f['etat_familial'] for f in personnes if 'etat_familial' in f])
    assert not any(f['maison'] == HORDE and CHAMPS_FAMILIAUX & f.keys() for f in personnes)


def test_familles_historiques_mamelouks_chypre_autriche(tmp_path):
    from sim import personnages as p
    d, monde = _personnages(), World.charger(0)
    def resolus(c):
        return c['familles'] + [{**h, **l} for l in c['liens'] for h in c['chefs'] if l['id'] == 'personne-' + h['maison']]
    def refuse(c, controle=False):
        if controle: assert _controler_famille(resolus(c))
        with pytest.raises(AssertionError): _familles_historiques(c['familles'], c['liens']); _etats_historiques(c['etats'])
    def altere(chemin, valeur):
        refuse(_alterer_personnages(d, chemin, valeur))
    _familles_historiques(d['familles'], d['liens']); _etats_historiques(d['etats'])
    _mca({f['id']: f for f in d['familles'] + d['liens']})
    assert len(d['familles']) == 102 and len(d['liens']) == len(d['etats']) == 29 and len(CHEF_EXCLUSION_MCA) == 12
    _preuve_monde_mca(list(monde.personnages))
    # La Horde : ni fiche, ni complément, ni état ; la lacune d'identité de son chef reste mot pour mot.
    chef = next(c for c in d['chefs'] if c['maison'] == HORDE)
    assert chef['nom'] is None and chef['lacunes']['identite'] == HORDE_LACUNE and monde.chefs[HORDE] == {'personnage': None, 'lacune': HORDE_LACUNE}
    assert not any(f['maison'] == HORDE for f in monde.personnages)
    assert not any(f['maison'] == HORDE for f in d['familles']) and not any(l['id'] == 'personne-' + HORDE for l in d['liens']) and not any(e['maison'] == HORDE for e in d['etats'])
    ids = {'personne-' + i for i in FICHES_MCA} | {'personne-' + m for m in MCA_MAISONS} | set(MCA_MAISONS)
    for t in ('familles', 'liens', 'etats'):
        for j, f in enumerate(d[t]):
            if f.get('id', f.get('maison')) not in ids: continue
            altere((t,), d[t][:j] + d[t][j+1:]); altere((t,), d[t] + [copy.deepcopy(f)])
            for chemin in _feuilles(f):
                valeur = f
                for cle in chemin: valeur = valeur[cle]
                altere((t, j, *chemin), ['personne-grande-9'] if valeur == [] else 'Altéré')
                if isinstance(valeur, str):
                    for repere in MCA_DIVERGENCES:
                        if repere in valeur: altere((t, j, *chemin), valeur.replace(repere, 'inconnu'))
            for nom in f.get('exclusions', {}): altere((t, j, 'exclusions', nom), 'SUPPRIMER')
            if t == 'etats':
                for champ in (k for k in ('conjoints', 'enfants') if f[k] == 'lacune'):
                    for etat in ('absence_attestee', 'union', 'veuvage'): altere((t, j, champ), etat)
                if f['maison'] == 'grande-30': altere((t, j, 'conjoints'), 'lacune'); altere((t, j, 'enfants'), 'lacune')
            for champ, liste in REPERES_MCA[f.get('id', f.get('maison'))].items():
                for repere in liste: altere((t, j, 'lacunes', champ), f['lacunes'][champ].replace(repere, 'inconnu'))
    k = next(i for i, f in enumerate(d['familles']) if f['id'] == 'personne-albert-v')
    altere(('familles', k, 'naissance'), _naissance_famille('1397-08-16'))
    j = next(i for i, f in enumerate(d['familles']) if f['id'] == JEANNE_SOPHIE_ID)
    for nom in ('Sophie de Bavière', 'Jeanne de Bavière'): altere(('familles', j, 'nom'), nom)
    modele = next(f for f in d['familles'] if f['id'] == 'personne-marie-bourgogne')
    for nom, maison in CHEF_EXCLUSION_MCA.items():
        for role in ('pere', 'conjoints'):
            c = copy.deepcopy(d); ajout = dict(copy.deepcopy(modele), id='personne-intruse', nom=nom, maison=maison, presence='vivante', pere=None, mere=None, conjoints=[]); c['familles'].append(ajout)
            if role == 'pere': ajout['pere'] = 'personne-' + maison
            else: ajout['conjoints'] = ['personne-' + maison]; next(x for x in c['liens'] if x['id'] == 'personne-' + maison)['conjoints'].append(ajout['id'])
            assert _controler_famille(resolus(c))
            with pytest.raises(AssertionError): _mca({f['id']: f for f in c['familles'] + c['liens']})
            refuse(c)
    # Horde : une fiche, un complément ou un état de `grande-21` est refusé.
    lien, etat = (next(x for x in d[t] if x.get('id', x.get('maison')) in ('personne-grande-26', 'grande-26')) for t in ('liens', 'etats'))
    c = copy.deepcopy(d); c['familles'].append(dict(copy.deepcopy(modele), id='personne-intruse', maison=HORDE))
    with pytest.raises(AssertionError): _mca({f['id']: f for f in c['familles'] + c['liens']})
    refuse(c)
    c = copy.deepcopy(d); c['liens'].append(dict(copy.deepcopy(lien), id='personne-' + HORDE))
    with pytest.raises(AssertionError): _mca({f['id']: f for f in c['familles'] + c['liens']})
    refuse(c)
    c = copy.deepcopy(d); c['etats'].append(dict(copy.deepcopy(etat), maison=HORDE))
    with pytest.raises(AssertionError): _mca(etat=c['etats'][-1])
    refuse(c)
    chemin = tmp_path / 'sans-chef.json'
    chemin.write_text(json.dumps(c), encoding='utf-8')
    with pytest.raises(ValueError): p.charger_catalogue(monde.maisons, chemin)
    # Dans le monde construit, une personne de la Horde ne porte ni présence ni état familial.
    base = next(f for f in monde.personnages if f['id'] == ALBERT_ID)
    for identifiant in ('personne-' + HORDE, 'personne-intruse'):
        for champ in ('presence', 'etat_familial'):
            clone = {k: copy.deepcopy(v) for k, v in base.items() if k not in CHAMPS_FAMILIAUX - {champ}}
            clone.update(id=identifiant, maison=HORDE)
            with pytest.raises(AssertionError): _preuve_monde_mca(list(monde.personnages) + [clone])


# Notices examinées le 12 novembre 2026 ; attentes indépendantes du catalogue.
PHILIPPE, MARGUERITE, JEAN, MARGUERITE_BAV, MARGUERITE_B, CATHERINE, LEOPOLD, ANTOINE, PHILIPPE_N = (WP + p for p in (
    'Philip_the_Bold#Marriage_and_issue', 'Margaret_III_of_Flanders', 'John_the_Fearless', 'Margaret_of_Bavaria', 'Margaret_of_Burgundy,_Duchess_of_Bavaria',
    'Catherine_of_Burgundy', 'Leopold_IV,_Duke_of_Austria', 'Anthony_of_Brabant', 'Philip_II_of_Nevers'))
BOURGOGNE = 'grande-27'
CHEF_BG, EPOUSE_BG, MARIE_BG, AMEDEE_BG, ALBERT_BG = 'personne-grande-27', 'personne-marguerite-flandre', 'personne-marie-bourgogne', 'personne-grande-12', 'personne-grande-30'
ENFANTS_BOURGOGNE = ('jean-sans-peur', 'marguerite-bourgogne', 'catherine-bourgogne', 'antoine-bourgogne', 'marie-bourgogne', 'philippe-nevers')
PARENTS_BG = 'de Philippe II le Hardi et de Marguerite III de Flandre'


def _filiation_bg(nom, qualite):
    return (PHILIPPE, f'{nom} est {qualite} {PARENTS_BG}.')


def _enfant_bg(nom, naissance, qualite, identite, fait_naissance, fait_presence, reperes, url=None, conjoints=()):
    page = url or PHILIPPE
    return (nom, BOURGOGNE, naissance, CHEF_BG, EPOUSE_BG, conjoints, {
        'identite': (page, identite), 'naissance': (page, fait_naissance), 'presence': (page, fait_presence),
        'pere': _filiation_bg(nom, qualite), 'mere': _filiation_bg(nom, qualite)}, {'conjoints': reperes})


# id : (nom, maison, naissance, père, mère, conjoints, sources {champ : (page, fait)}, repères des lacunes {champ : repères})
FICHES_BOURGOGNE = {
    'marguerite-flandre': ('Marguerite III de Flandre', BOURGOGNE, {'valeur': '1350-04-13', 'precision': 'jour'}, None, None, (CHEF_BG,), {
        'identite': (MARGUERITE, 'Marguerite III de Flandre, comtesse de Flandre, épouse de Philippe II le Hardi, duc de Bourgogne.'),
        'naissance': (MARGUERITE, 'Marguerite III de Flandre : née le 13 avril 1350.'),
        'presence': (MARGUERITE, 'Marguerite III de Flandre, morte le 16 mars 1405 ; vivante au 1er janvier 1400, décès cité pour la sélection initiale.'),
        'conjoints': (MARGUERITE, 'Marguerite III de Flandre et Philippe II le Hardi sont mariés depuis le 19 juin 1369 (' + PHILIPPE + ' ; ' + MARGUERITE + ') ; elle était veuve de Philippe de Rouvres (mariage en 1355, mort en 1361, sans enfant) : cette union passée ne crée aucune fiche.')},
        {'pere': ('Marguerite III de Flandre', 'Louis II de Flandre', MARGUERITE, *HORS), 'mere': ('Marguerite III de Flandre', 'Marguerite de Brabant', MARGUERITE, *HORS)}),
    'jean-sans-peur': _enfant_bg('Jean sans Peur', {'valeur': '1371-05-28', 'precision': 'jour'}, 'fils aîné',
        'Jean sans Peur, fils aîné ' + PARENTS_BG + ', héritier du duché.', 'Jean sans Peur : né le 28 mai 1371.',
        'Jean sans Peur, mort le 10 septembre 1419 ; vivant au 1er janvier 1400, décès cité pour la sélection initiale.',
        ('Jean sans Peur', 'Marguerite de Bavière', '1363', '12 avril 1385', 'Cambrai', JEAN, MARGUERITE_BAV, 'hors périmètre', 'aucune fiche créée', 'aucune absence attestée'), JEAN),
    'marguerite-bourgogne': _enfant_bg('Marguerite de Bourgogne', {'valeur': '1374-10', 'precision': 'mois'}, 'fille',
        'Marguerite de Bourgogne, fille ' + PARENTS_BG + ', duchesse de Bavière.',
        'Marguerite de Bourgogne : née en octobre 1374, mois que donnent ' + MARGUERITE_B + ' et ' + PHILIPPE + '.',
        'Marguerite de Bourgogne, morte le 8 mars 1441 ; vivante au 1er janvier 1400, décès cité pour la sélection initiale.',
        ('Marguerite de Bourgogne', 'Guillaume de Bavière', '12 avril 1385', MARGUERITE_B, '16 août 1401', 'après le départ', 'hors périmètre', 'aucune fiche créée', 'aucune absence attestée'), MARGUERITE_B),
    'catherine-bourgogne': _enfant_bg('Catherine de Bourgogne', {'valeur': '1378-04', 'precision': 'mois'}, 'fille',
        'Catherine de Bourgogne, fille ' + PARENTS_BG + ', duchesse d’Autriche.',
        'Catherine de Bourgogne : née en avril 1378 selon ' + PHILIPPE + ' et ' + MARGUERITE + ' ; ' + CATHERINE + ' ne donne que l’année 1378 ; aucun jour n’est choisi.',
        'Catherine de Bourgogne, morte le 24 janvier 1425 à Gray selon ' + PHILIPPE + ' et ' + MARGUERITE + ', le 26 janvier 1425 à Dijon selon ' + CATHERINE + ' ; vivante au 1er janvier 1400, divergence conservée.',
        ('Catherine de Bourgogne', 'Léopold IV', '15 août 1393', CATHERINE, LEOPOLD, 'sans enfant', 'personne-grande-30', 'hors périmètre', 'aucune fiche créée', 'aucune absence attestée')),
    'antoine-bourgogne': _enfant_bg('Antoine de Bourgogne', {'valeur': '1384-08', 'precision': 'mois'}, 'fils',
        'Antoine de Bourgogne, fils ' + PARENTS_BG + ', futur duc de Brabant.',
        'Antoine de Bourgogne : né en août 1384, mois que donnent ' + ANTOINE + ' et ' + PHILIPPE + '.',
        'Antoine de Bourgogne, mort le 25 octobre 1415 à Azincourt ; vivant au 1er janvier 1400, décès cité pour la sélection initiale.',
        ('Antoine de Bourgogne', 'aucun conjoint au départ', 'Jeanne de Saint-Pol', '21 février 1402', 'Élisabeth de Görlitz', '16 juillet 1409', ANTOINE, 'ni célibat ni veuvage', 'aucune absence attestée'), ANTOINE),
    'philippe-nevers': _enfant_bg('Philippe de Bourgogne', {'valeur': '1389-10', 'precision': 'mois'}, 'fils',
        'Philippe de Bourgogne, comte de Nevers, fils ' + PARENTS_BG + '.',
        'Philippe de Bourgogne : né en octobre 1389.',
        'Philippe de Bourgogne, mort le 25 octobre 1415 à Azincourt ; vivant au 1er janvier 1400, décès cité pour la sélection initiale.',
        ('Philippe de Bourgogne', 'aucun conjoint au départ', 'Isabelle de Coucy', '9 avril 1409', 'Bonne d’Artois', '20 juin 1413', PHILIPPE_N, 'ni célibat ni veuvage', 'aucune absence attestée'), PHILIPPE_N),
}
# Marie de Bourgogne (grande-12) : seuls ses deux liens changent ; le reste est gardé par `_voisins_historiques`.
MARIE_BG_LIENS = {
    'pere': (PHILIPPE, 'Marie de Bourgogne, née en septembre 1386 à Dijon, est fille ' + PARENTS_BG + ', mariée à Amédée VIII.'),
    'mere': (MARGUERITE, 'Marie de Bourgogne est fille de Marguerite III de Flandre et de Philippe II le Hardi ; la page de Marguerite III la dit née en septembre 1380 ; la fiche garde 1386, sans choisir de mois, divergence conservée.')}
# conjoints, sources {champ : (page, fait)}, repères des lacunes
LIEN_BOURGOGNE = ((EPOUSE_BG,), {
    'presence': (PHILIPPE, 'Philippe II le Hardi, duc de Bourgogne jusqu’à sa mort, le 27 avril 1404 ; en fonction et vivant au 1er janvier 1400, aucune mort programmée.'),
    'conjoints': (PHILIPPE, 'Philippe II le Hardi et Marguerite III de Flandre sont mariés depuis le 19 juin 1369 ; union active au départ.')},
    {'pere': ('Philippe II le Hardi', 'Jean II de France', PHILIPPE, 'hors périmètre', 'aucune fiche créée', 'aucune absence attestée'),
     'mere': ('Philippe II le Hardi', 'Bonne de Luxembourg', 'Bonne de Bohême', PHILIPPE, 'hors périmètre', 'aucune absence attestée')})
ETAT_BOURGOGNE = ('union', 'documentes', {
    'conjoints': (PHILIPPE, 'Philippe II le Hardi et Marguerite III de Flandre sont mariés depuis le 19 juin 1369 ; état union, avant le départ.'),
    'enfants': (PHILIPPE, 'Philippe II le Hardi et Marguerite III de Flandre ont neuf enfants, dont six vivants au 1er janvier 1400 : Jean, Marguerite, Catherine, Antoine, Marie et Philippe ; ' + MARGUERITE_B + ' dit aussi « neuf enfants » ; les trois autres sont morts avant 1400 et exclus.')}, {}, {
    'Charles de Bourgogne': ((PHILIPPE, 'Charles de Bourgogne : fils ' + PARENTS_BG + ', né en 1372, mort en 1373, avant le départ ; exclu, aucun événement programmé.'),
                             (MARGUERITE, 'Charles de Bourgogne : enfant de Marguerite III de Flandre, mort en 1373 ; mort avant 1400, il n’a ni fiche ni résurrection.')),
    'Louis de Bourgogne': ((PHILIPPE, 'Louis de Bourgogne : fils ' + PARENTS_BG + ', né en 1377, mort en 1378, avant le départ ; exclu, aucun événement programmé.'),
                           (MARGUERITE, 'Louis de Bourgogne : enfant de Marguerite III de Flandre, mort en 1378 ; mort avant 1400, il n’a ni fiche ni résurrection.')),
    'Bonne de Bourgogne': ((PHILIPPE, 'Bonne de Bourgogne : fille ' + PARENTS_BG + ', née en 1379, fiancée à Jean de Bourbon, morte à Arras en 1399, avant le départ ; exclue, aucun événement programmé.'),
                           (MARGUERITE, 'Bonne de Bourgogne : enfant de Marguerite III de Flandre, morte en 1399 ; morte avant 1400, elle n’a ni fiche ni résurrection.')),
    'Jeanne de Saint-Pol': ((ANTOINE, 'Jeanne de Saint-Pol : première épouse future d’Antoine de Bourgogne, mariée le 21 février 1402, exclue du départ ; aucun événement programmé.'),),
    'Élisabeth de Görlitz': ((ANTOINE, 'Élisabeth de Görlitz : seconde épouse future d’Antoine de Bourgogne, mariée le 16 juillet 1409, exclue du départ ; aucun événement programmé.'),),
    'Isabelle de Coucy': ((PHILIPPE_N, 'Isabelle de Coucy : première épouse future de Philippe de Bourgogne, comte de Nevers, mariée le 9 avril 1409, exclue du départ ; aucun événement programmé.'),),
    'Bonne d’Artois': ((PHILIPPE_N, 'Bonne d’Artois : seconde épouse future de Philippe de Bourgogne, comte de Nevers, mariée le 20 juin 1413, exclue du départ ; aucun événement programmé.'),)})
BOURGOGNE_EXCLUSIONS = ETAT_BOURGOGNE[4]
# Fiche de chef de Philippe II le Hardi (`chefs`) : nom, maison, naissance au mois (le jour diverge, 17 ou 15, et reste indéterminé), sources d'identité et de naissance.
CHEF_FICHE_BG = ('Philippe II le Hardi', BOURGOGNE, {'valeur': '1342-01', 'precision': 'mois'}, WP + 'Philip_the_Bold', ('janvier 1342', '17', '15'))
BOURGOGNE_DIVERGENCES = ('19 juin 1369', '27 avril 1404', 'Bonne de Luxembourg', 'Bonne de Bohême', '1355', '1361', 'fils aîné', '12 avril 1385', 'Marguerite de Bavière', 'Guillaume de Bavière',
                         '16 août 1401', '15 août 1393', 'Léopold IV', '24 janvier', '26 janvier', '21 février 1402', '9 avril 1409', 'septembre 1380', 'neuf enfants', 'ni célibat ni veuvage', 'aucune absence attestée')
REPERES_BG = {**{'personne-' + i: v[7] for i, v in FICHES_BOURGOGNE.items()}, CHEF_BG: LIEN_BOURGOGNE[2], BOURGOGNE: {}}


def _bourgogne(fiches=None, etat=None):
    try: _bourgogne_controle(fiches, etat)
    except (KeyError, TypeError, AttributeError) as erreur: raise AssertionError(f'fiche bourguignonne malformée : {erreur!r}') from erreur


def _bourgogne_controle(fiches, etat):
    if fiches is not None:
        enfants = {'personne-' + i for i in ENFANTS_BOURGOGNE}
        assert {CHEF_BG, EPOUSE_BG, MARIE_BG} | {'personne-' + i for i in FICHES_BOURGOGNE} <= set(fiches)
        assert {i for i, f in fiches.items() if f.get('maison') == BOURGOGNE and i != CHEF_BG} == {'personne-' + i for i in FICHES_BOURGOGNE}
        for i, (nom, maison, naissance, pere, mere, conjoints, sources, reperes) in FICHES_BOURGOGNE.items():
            f = fiches['personne-' + i]
            assert (f['nom'], f['maison'], f['naissance'], f['pere'], f['mere'], tuple(f['conjoints']), f['presence']) == (nom, maison, naissance, pere, mere, conjoints, 'vivante')
            _lacunes_b(f['sources'], f['lacunes'], sources, reperes)
        conjoints, sources, reperes = LIEN_BOURGOGNE
        c = fiches[CHEF_BG]
        assert (c['pere'], c['mere'], tuple(c['conjoints']), c['presence']) == (None, None, conjoints, 'vivante')
        champs = ('pere', 'mere', 'conjoints', 'presence')
        _lacunes_b({k: c['sources'][k] for k in champs}, {k: c['lacunes'][k] for k in champs}, sources, reperes)
        # Marie : la même fiche de `grande-12`, avec ses deux parents sourcés ; ses autres sources restent celles de la Savoie.
        marie = fiches[MARIE_BG]
        assert (marie['nom'], marie['maison'], marie['naissance'], marie['pere'], marie['mere'], tuple(marie['conjoints']), marie['presence']) == (
            'Marie de Bourgogne', 'grande-12', {'valeur': '1386', 'precision': 'annee'}, CHEF_BG, EPOUSE_BG, (AMEDEE_BG,), 'vivante')
        assert set(marie['sources']) == set(marie['lacunes']) == {'identite', 'naissance', 'pere', 'mere', 'conjoints', 'presence'}
        assert all(marie['sources'][k]['url'] == MARIE_SAVOIE for k in ('identite', 'naissance', 'conjoints', 'presence'))
        _lacunes_b({k: marie['sources'][k] for k in MARIE_BG_LIENS}, {k: marie['lacunes'][k] for k in MARIE_BG_LIENS}, MARIE_BG_LIENS, {})
        assert [i for i, f in fiches.items() if f.get('nom') == 'Marie de Bourgogne'] == [MARIE_BG]
        # Seuls les six enfants ont Philippe pour père et Marguerite pour mère ; une seule union, jamais d’union future ni d’enfant inventé.
        assert {i for i, f in fiches.items() if f['pere'] == CHEF_BG} == {i for i, f in fiches.items() if f['mere'] == EPOUSE_BG} == enfants
        assert {i for i, f in fiches.items() if CHEF_BG in f['conjoints']} == {EPOUSE_BG} and {i for i, f in fiches.items() if EPOUSE_BG in f['conjoints']} == {CHEF_BG}
        # Aucun lien vers une autre maison, sauf Marie et Amédée VIII (Albert IV n’est pas Léopold IV).
        famille = enfants | {CHEF_BG, EPOUSE_BG}
        for i, f in fiches.items():
            liens = {f['pere'], f['mere'], *f['conjoints']} - {None}
            if i in famille: assert liens <= famille | ({AMEDEE_BG} if i == MARIE_BG else set())
            else: assert not liens & famille or (i == AMEDEE_BG and liens & famille == {MARIE_BG})
        assert not any(ALBERT_BG in (f['pere'], f['mere']) or ALBERT_BG in f['conjoints'] for i, f in fiches.items() if i in famille)
    if etat is not None:
        conjoints, enfants, sources, reperes, exclusions = ETAT_BOURGOGNE
        assert etat['maison'] == BOURGOGNE and (etat['conjoints'], etat['enfants']) == (conjoints, enfants) and set(etat['sources']) == set(etat['lacunes']) == {'conjoints', 'enfants'}
        _lacunes_b(etat['sources'], etat['lacunes'], sources, reperes)
        assert set(etat['exclusions']) == set(exclusions)
        for nom, faits in exclusions.items():
            x = etat['exclusions'][nom]
            assert set(x) == {'motif', 'sources'} and x['motif'] == ' '.join(f for _, f in faits) and x['sources'] == [{'url': u, 'fait': f} for u, f in faits]


def _chef_bourgogne(chef):
    try:
        nom, maison, naissance, page, reperes = CHEF_FICHE_BG
        assert (chef['nom'], chef['maison'], chef['naissance']) == (nom, maison, naissance)
        assert chef['sources']['identite']['url'] == chef['sources']['naissance']['url'] == page
        assert chef['lacunes']['identite'] is None and chef['lacunes']['naissance'] is None
        assert 'Philippe II le Hardi' in chef['sources']['identite']['fait'] and all(r in chef['sources']['naissance']['fait'] for r in reperes)
    except (KeyError, TypeError, AttributeError) as erreur: raise AssertionError(f'fiche de chef bourguignonne malformée : {erreur!r}') from erreur


def _preuve_monde_bourgogne(personnes):
    _chef_bourgogne(next(f for f in personnes if f['id'] == CHEF_BG))
    _familles_historiques([f for f in personnes if f['id'] != 'personne-' + f['maison']],
                          [f for f in personnes if f['id'] == 'personne-' + f['maison'] and CHAMPS_FAMILIAUX & f.keys()])
    _etats_historiques([f['etat_familial'] for f in personnes if 'etat_familial' in f])


def test_familles_historiques_bourgogne():
    d, monde = _personnages(), World.charger(0)
    def resolus(c):
        return c['familles'] + [{**h, **l} for l in c['liens'] for h in c['chefs'] if l['id'] == 'personne-' + h['maison']]
    def refuse(c, controle=False, bourgogne=False):
        if controle: assert _controler_famille(resolus(c))
        if bourgogne:
            with pytest.raises(AssertionError): _bourgogne({f['id']: f for f in resolus(c)})
        with pytest.raises(AssertionError): _familles_historiques(c['familles'], c['liens']); _etats_historiques(c['etats'])
    def altere(chemin, valeur):
        refuse(_alterer_personnages(d, chemin, valeur))
    _familles_historiques(d['familles'], d['liens']); _etats_historiques(d['etats'])
    _chef_bourgogne(next(c for c in d['chefs'] if c['maison'] == BOURGOGNE))
    _bourgogne({f['id']: f for f in d['familles'] + d['liens']}); _bourgogne(etat=next(e for e in d['etats'] if e['maison'] == BOURGOGNE))
    assert len(d['familles']) == 102 and len(d['liens']) == len(d['etats']) == 29 and len(BOURGOGNE_EXCLUSIONS) == 7 and len(FICHES_BOURGOGNE) == 6
    _preuve_monde_bourgogne(list(monde.personnages))
    assert [f['id'] for f in monde.personnages if f['maison'] == 'grande-12'] == [AMEDEE_BG, MARIE_BG]
    ids = {'personne-' + i for i in FICHES_BOURGOGNE} | {CHEF_BG, MARIE_BG, BOURGOGNE}
    for t in ('familles', 'liens', 'etats'):
        for j, f in enumerate(d[t]):
            if f.get('id', f.get('maison')) not in ids: continue
            altere((t,), d[t][:j] + d[t][j+1:]); altere((t,), d[t] + [copy.deepcopy(f)])
            for chemin in _feuilles(f):
                valeur = f
                for cle in chemin: valeur = valeur[cle]
                altere((t, j, *chemin), ['personne-grande-9'] if valeur == [] else 'Altéré')
                if isinstance(valeur, str):
                    for repere in BOURGOGNE_DIVERGENCES:
                        if repere in valeur: altere((t, j, *chemin), valeur.replace(repere, 'inconnu'))
            for nom in f.get('exclusions', {}): altere((t, j, 'exclusions', nom), 'SUPPRIMER')
            if t == 'etats':
                for champ, etats in (('conjoints', ('lacune', 'veuvage')), ('enfants', ('lacune', 'absence_attestee'))):
                    for etat in etats: altere((t, j, champ), etat)
            for champ, liste in REPERES_BG.get(f.get('id', f.get('maison')), {}).items():
                for repere in liste: altere((t, j, 'lacunes', champ), f['lacunes'][champ].replace(repere, 'inconnu'))
                if f.get('maison') == BOURGOGNE and champ == 'conjoints': altere((t, j, 'lacunes', champ), f['nom'] + ' : absence attestée de tout conjoint.')
    # La fiche du chef : nom, naissance (jour choisi dans la divergence 17/15, précision), repères et sources.
    j = next(k for k, c in enumerate(d['chefs']) if c['maison'] == BOURGOGNE)
    chef = d['chefs'][j]
    for chemin, valeur in ((('nom',), 'Philippe III le Bon'), (('maison',), 'grande-12'), (('naissance',), _naissance_famille('1342-01-17')), (('naissance',), _naissance_famille('1342-01-15')),
                           (('naissance',), _naissance_famille('1342', 'annee')), (('naissance', 'valeur'), '1342-02'),
                           (('sources', 'identite', 'url'), WP + 'John_the_Fearless'), (('sources', 'naissance', 'url'), WP + 'Margaret_III_of_Flanders'), (('lacunes', 'naissance'), 'Naissance inconnue.')):
        with pytest.raises(AssertionError): _chef_bourgogne(_alterer_personnages(chef, chemin, valeur))
    for repere in CHEF_FICHE_BG[4]:
        with pytest.raises(AssertionError): _chef_bourgogne(_alterer_personnages(chef, ('sources', 'naissance', 'fait'), chef['sources']['naissance']['fait'].replace(repere, 'inconnu')))
    # Dans le monde, la même fiche altérée est refusée.
    for chemin, valeur in ((('nom',), 'Philippe III le Bon'), (('naissance',), _naissance_famille('1342-01-17'))):
        with pytest.raises(AssertionError): _chef_bourgogne(_alterer_personnages(next(f for f in monde.personnages if f['id'] == CHEF_BG), chemin, valeur))
    modele = next(f for f in d['familles'] if f['id'] == MARIE_BG)
    # Marie : ses anciens liens vides, avec leurs anciennes lacunes, sont refusés.
    for champ in ('pere', 'mere'):
        c = copy.deepcopy(d); marie = next(f for f in c['familles'] if f['id'] == MARIE_BG)
        marie[champ], marie['sources'][champ], marie['lacunes'][champ] = None, None, f'Marie de Bourgogne : {"père" if champ == "pere" else "mère"} hors périmètre familial, aucune absence attestée.'
        refuse(c, controle=True, bourgogne=True)
    # Une seconde « Marie de Bourgogne », de `grande-27`, enfant de Philippe et de Marguerite.
    c = copy.deepcopy(d); c['familles'].append(dict(copy.deepcopy(modele), id='personne-marie-intruse', maison=BOURGOGNE, pere=CHEF_BG, mere=EPOUSE_BG, conjoints=[]))
    refuse(c, controle=True, bourgogne=True)
    # Les naissances que le lot refuse de redevenir imprécises ou fausses.
    for i, naissance in (('catherine-bourgogne', _naissance_famille('1378-04-01')), ('marie-bourgogne', _naissance_famille('1380', 'annee'))):
        k = next(k for k, f in enumerate(d['familles']) if f['id'] == 'personne-' + i)
        altere(('familles', k, 'naissance'), naissance)
    # Catherine, conjointe réciproque d’Albert IV (`grande-30`) : Léopold IV n’est pas Albert IV.
    c = copy.deepcopy(d); catherine = next(f for f in c['familles'] if f['id'] == 'personne-catherine-bourgogne')
    catherine['conjoints'] = [ALBERT_BG]; next(x for x in c['liens'] if x['id'] == ALBERT_BG)['conjoints'].append(catherine['id'])
    refuse(c, controle=True, bourgogne=True)
    # Des copies de Marie, enfants de Philippe : morts avant 1400, épouses futures, héritier inventé.
    base = next(f for f in monde.personnages if f['id'] == MARIE_BG)
    intrus = [(nom, 'decedee', ('enfant',)) for nom in ('Charles de Bourgogne', 'Louis de Bourgogne', 'Bonne de Bourgogne')]
    intrus += [(nom, 'vivante', ('enfant', 'conjoint')) for nom in ('Jeanne de Saint-Pol', 'Élisabeth de Görlitz', 'Isabelle de Coucy', 'Bonne d’Artois', 'Héritier inventé')]
    for nom, presence, roles in intrus:
        for role in roles:
            c = copy.deepcopy(d); ajout = dict(copy.deepcopy(modele), id='personne-intruse', nom=nom, maison=BOURGOGNE, presence=presence, pere=None, mere=None, conjoints=[]); c['familles'].append(ajout)
            if role == 'enfant': ajout['pere'], ajout['mere'] = CHEF_BG, EPOUSE_BG
            else: ajout['conjoints'] = [CHEF_BG]; next(x for x in c['liens'] if x['id'] == CHEF_BG)['conjoints'].append(ajout['id'])
            refuse(c, controle=True, bourgogne=True)
            clone = {k: copy.deepcopy(v) for k, v in base.items()}
            clone.update(id='personne-intruse', nom=nom, maison=BOURGOGNE, presence=presence, pere=None, mere=None, conjoints=[])
            personnes = [copy.deepcopy(f) for f in monde.personnages]
            chef = next(f for f in personnes if f['id'] == CHEF_BG)
            if role == 'enfant': clone.update(pere=CHEF_BG, mere=EPOUSE_BG)
            else: clone['conjoints'] = [CHEF_BG]; chef['conjoints'].append(clone['id'])
            with pytest.raises(AssertionError): _bourgogne({f['id']: f for f in personnes + [clone]})
            with pytest.raises(AssertionError): _preuve_monde_bourgogne(personnes + [clone])


# Notices examinées le 13 novembre 2026 ; attentes indépendantes du catalogue.
(ROBERT, ELISABETH_N, MARGUERITE_P, CHARLES_L, LOUIS_P, ADOLPHE_C, JEAN_N, CATHERINE_P, ETIENNE_S, ANNA_V, OTTON_M, FREDERIC_A, MATHILDE_S) = (WP + p for p in (
    'Rupert,_King_of_the_Romans#Family_and_children', 'Elisabeth_of_Nuremberg', 'Margaret_of_the_Palatinate', 'Charles_II_of_Lorraine', 'Louis_III,_Elector_Palatine',
    'Adolph_I,_Duke_of_Cleves', 'John,_Count_Palatine_of_Neumarkt', 'Catherine_of_Pomerania,_Countess_Palatine_of_Neumarkt', 'Stephen,_Count_Palatine_of_Simmern-Zweibrücken',
    'Anna_of_Veldenz,_Countess_Palatine_of_Simmern-Zweibrücken', 'Otto_I,_Count_Palatine_of_Mosbach', 'Frederick_IV_of_Austria', 'Matilda_of_Savoy'))
PALATINAT = 'grande-29'
CHEF_PAL, EPOUSE_PAL, BLANCHE_PAL, LOUIS_PAL, AUTRICHE_PAL = 'personne-grande-29', 'personne-elisabeth-nuremberg', 'personne-blanche-angleterre', 'personne-louis-palatinat', 'personne-grande-30'
ENFANTS_PALATINAT = ('marguerite-palatinat', 'frederic-palatinat', 'louis-palatinat', 'agnes-palatinat', 'elisabeth-palatinat', 'jean-neumarkt', 'etienne-simmern', 'otton-mosbach')
PARENTS_PAL = 'de Robert III et d’Élisabeth de Nuremberg'
MAISONS_AVEC_ETAT = {f'grande-{n}' for n in range(1, 31)} - {'grande-21', 'grande-24'} | {'seigneurie-1'}


def _enfant_pal(nom, naissance, qualite, identite, fait_naissance, fait_presence, reperes, url_naissance=ROBERT, url_presence=ROBERT):
    filiation = (ROBERT, f'{nom} est {qualite} {PARENTS_PAL} ; ' + ELISABETH_N + ' donne la même liste d’enfants.')
    return (nom, PALATINAT, naissance, CHEF_PAL, EPOUSE_PAL, (), {
        'identite': (ROBERT, identite), 'naissance': (url_naissance, fait_naissance), 'presence': (url_presence, fait_presence),
        'pere': filiation, 'mere': filiation}, {'conjoints': reperes})


# id : (nom, maison, naissance, père, mère, conjoints, sources {champ : (page, fait)}, repères des lacunes {champ : repères})
FICHES_PALATINAT = {
    'elisabeth-nuremberg': ('Élisabeth de Nuremberg', PALATINAT, {'valeur': '1358-12-13', 'precision': 'jour'}, None, None, (CHEF_PAL,), {
        'identite': (ELISABETH_N, 'Élisabeth de Nuremberg, de la maison de Hohenzollern, épouse de Robert III, électeur palatin.'),
        'naissance': (ELISABETH_N, 'Élisabeth de Nuremberg : née le 13 décembre 1358 ; l’infobox de la même page ne donne que 1358, divergence conservée.'),
        'presence': (ELISABETH_N, 'Élisabeth de Nuremberg, morte le 26 juillet 1411 ; vivante au 1er janvier 1400, décès cité pour la sélection initiale.'),
        'conjoints': (ELISABETH_N, 'Élisabeth de Nuremberg et Robert III sont mariés à Amberg le 27 juin 1374 (' + ROBERT + ' ; ' + ELISABETH_N + ') ; union active au départ.')},
        {'pere': ('Élisabeth de Nuremberg', 'Frédéric V de Nuremberg', ELISABETH_N, 'hors périmètre', 'aucune fiche créée', 'aucune absence attestée'),
         'mere': ('Élisabeth de Nuremberg', 'Élisabeth de Misnie', ELISABETH_N, 'hors périmètre', 'aucune absence attestée')}),
    'marguerite-palatinat': _enfant_pal('Marguerite du Palatinat', {'valeur': '1376', 'precision': 'annee'}, 'fille',
        'Marguerite du Palatinat, fille ' + PARENTS_PAL + ', duchesse de Lorraine.',
        'Marguerite du Palatinat : née en 1376, année que donnent ' + ROBERT + ' et ' + MARGUERITE_P + '.',
        'Marguerite du Palatinat, morte le 27 août 1434 à Nancy selon ' + ROBERT + ' et ' + ELISABETH_N + ', le 26 août 1434 à Einville-au-Jard selon ' + MARGUERITE_P + ' ; vivante au 1er janvier 1400, divergence conservée.',
        ('Marguerite du Palatinat', 'Charles II de Lorraine', '6 février 1393', ROBERT, MARGUERITE_P, CHARLES_L, 'dit 1393', 'hors périmètre', 'aucune fiche créée', 'aucune absence attestée'), url_presence=MARGUERITE_P),
    'frederic-palatinat': _enfant_pal('Frédéric du Palatinat', {'valeur': 'vers 1377', 'precision': 'vers'}, 'fils',
        'Frédéric du Palatinat, fils aîné vivant ' + PARENTS_PAL + ' au départ ; aucun héritier n’est désigné.',
        'Frédéric du Palatinat : né vers 1377 (« c. 1377 »), à Amberg ; aucune borne n’est inventée.',
        'Frédéric du Palatinat, mort le 7 mars 1401 à Amberg, après le départ ; vivant au 1er janvier 1400, aucune mort programmée.',
        ('Frédéric du Palatinat', 'aucune épouse nommée', ROBERT, ELISABETH_N, 'ni célibat ni veuvage', 'aucune absence attestée')),
    'louis-palatinat': _enfant_pal('Louis III du Palatinat', {'valeur': '1378-01-23', 'precision': 'jour'}, 'fils',
        'Louis III du Palatinat, fils ' + PARENTS_PAL + ' ; ' + LOUIS_P + ' le dit « troisième fils ».',
        'Louis III du Palatinat : né le 23 janvier 1378 (' + ROBERT + ' ; ' + LOUIS_P + ').',
        'Louis III du Palatinat, mort le 30 décembre 1436 ; vivant au 1er janvier 1400, décès cité pour la sélection initiale.',
        ('Louis III du Palatinat', 'aucun conjoint au départ', 'Blanche d’Angleterre', '6 juillet 1402', 'Mathilde de Savoie', '30 novembre 1417', LOUIS_P, 'ni célibat ni veuvage', 'aucune absence attestée'), url_presence=LOUIS_P),
    'agnes-palatinat': _enfant_pal('Agnès du Palatinat', {'valeur': '1379', 'precision': 'annee'}, 'fille',
        'Agnès du Palatinat, fille ' + PARENTS_PAL + '.',
        'Agnès du Palatinat : née en 1379.',
        'Agnès du Palatinat, morte en 1401 à Heidelberg, sans enfant (' + ADOLPHE_C + ') ; vivante au 1er janvier 1400, décès cité pour la sélection initiale.',
        ('Agnès du Palatinat', 'Adolphe Ier de Clèves', 'Heidelberg', 'peu avant mars 1400', 'peu avant l’année 1400', ROBERT, ELISABETH_N, ADOLPHE_C,
         'ni fiche, ni exclusion', 'pas si l’union est active au 1er janvier 1400', 'hors périmètre', 'aucune absence attestée'), url_presence=ADOLPHE_C),
    'elisabeth-palatinat': _enfant_pal('Élisabeth du Palatinat', {'valeur': '1381-10-27', 'precision': 'jour'}, 'fille',
        'Élisabeth du Palatinat, fille ' + PARENTS_PAL + '.',
        'Élisabeth du Palatinat : née le 27 octobre 1381.',
        'Élisabeth du Palatinat, morte le 31 décembre 1408 à Innsbruck selon ' + ROBERT + ', le 27 décembre 1408, peu après la naissance de sa fille, selon ' + FREDERIC_A + ' ; vivante au 1er janvier 1400, divergence conservée.',
        ('Élisabeth du Palatinat', 'aucun conjoint au départ', 'Frédéric IV d’Autriche', '24 décembre 1407', 'Innsbruck', ROBERT, FREDERIC_A, 'n’est pas Albert IV', 'personne-grande-30', 'ni célibat ni veuvage', 'aucune absence attestée')),
    'jean-neumarkt': _enfant_pal('Jean de Neumarkt', {'valeur': '1383', 'precision': 'annee'}, 'fils',
        'Jean de Neumarkt, fils ' + PARENTS_PAL + '.',
        'Jean de Neumarkt : né en 1383 à Neunburg vorm Wald, année que donnent ' + ROBERT + ' et ' + JEAN_N + '.',
        'Jean de Neumarkt, mort les 13–14 mars 1443 selon ' + ROBERT + ', le 14 mars 1443 selon ' + JEAN_N + ' ; vivant au 1er janvier 1400, divergence conservée.',
        ('Jean de Neumarkt', 'aucun conjoint au départ', 'Catherine de Poméranie', '1407', '15 août 1407', 'Ribe', JEAN_N, CATHERINE_P, 'ni célibat ni veuvage', 'aucune absence attestée')),
    'etienne-simmern': _enfant_pal('Étienne de Simmern-Deux-Ponts', {'valeur': '1385-06-23', 'precision': 'jour'}, 'fils',
        'Étienne de Simmern-Deux-Ponts, fils ' + PARENTS_PAL + '.',
        'Étienne de Simmern-Deux-Ponts : né le 23 juin 1385 (' + ROBERT + ' ; ' + ETIENNE_S + ').',
        'Étienne de Simmern-Deux-Ponts, mort le 14 février 1459 ; vivant au 1er janvier 1400, décès cité pour la sélection initiale.',
        ('Étienne de Simmern-Deux-Ponts', 'aucun conjoint au départ', 'Anna de Veldenz', 'juin 1410', ETIENNE_S, '1409', ANNA_V, 'ni célibat ni veuvage', 'aucune absence attestée'), url_presence=ETIENNE_S),
    'otton-mosbach': _enfant_pal('Otton de Mosbach', {'valeur': '1390-08-24', 'precision': 'jour'}, 'fils',
        'Otton de Mosbach, fils cadet ' + PARENTS_PAL + ' (' + OTTON_M + ').',
        'Otton de Mosbach : né le 24 août 1390 (' + ROBERT + ' ; ' + OTTON_M + ').',
        'Otton de Mosbach, mort le 5 juillet 1461 ; vivant au 1er janvier 1400, décès cité pour la sélection initiale.',
        ('Otton de Mosbach', 'aucun conjoint au départ', 'Jeanne de Bavière-Landshut', 'janvier 1430', OTTON_M, 'ni célibat ni veuvage', 'aucune absence attestée'), url_presence=OTTON_M),
}
# conjoints, sources {champ : (page, fait)}, repères des lacunes
LIEN_PALATINAT = ((EPOUSE_PAL,), {
    'presence': (ROBERT, 'Robert III, électeur palatin jusqu’à sa mort, le 18 mai 1410 au château de Landskron, à Oppenheim ; élu roi des Romains le 21 août 1400, après le départ ; en fonction et vivant au 1er janvier 1400, aucune mort ni élection programmée.'),
    'conjoints': (ROBERT, 'Robert III et Élisabeth de Nuremberg sont mariés à Amberg depuis le 27 juin 1374 ; union active au départ.')},
    {'pere': ('Robert III', 'Robert II', ROBERT, 'hors périmètre', 'aucune fiche créée', 'aucune absence attestée'),
     'mere': ('Robert III', 'Béatrice de Sicile', 'Beatrice of Aragon', ROBERT, 'hors périmètre', 'aucune absence attestée')})
ETAT_PALATINAT = ('union', 'documentes', {
    'conjoints': (ROBERT, 'Robert III et Élisabeth de Nuremberg sont mariés à Amberg depuis le 27 juin 1374 ; état union, avant le départ.'),
    'enfants': (ROBERT, 'Robert III et Élisabeth de Nuremberg ont neuf enfants, dont huit vivants au 1er janvier 1400 : Marguerite, Frédéric, Louis, Agnès, Élisabeth, Jean, Étienne et Otton ; ' + ELISABETH_N + ' donne la même liste ; Robert Pipan, mort avant 1400, est exclu.')}, {}, {
    'Robert Pipan': ((ROBERT, 'Robert Pipan : fils aîné ' + PARENTS_PAL + ', né le 20 février 1375, mort le 25 janvier 1397 à Amberg, avant le départ ; exclu, aucun événement programmé.'),
                     (ELISABETH_N, 'Robert Pipan : enfant d’Élisabeth de Nuremberg, mort en 1397 ; mort avant 1400, il n’a ni fiche ni résurrection.')),
    'Blanche d’Angleterre': ((LOUIS_P, 'Blanche d’Angleterre : épouse future de Louis III du Palatinat, mariée le 6 juillet 1402 ; elle garde sa seule fiche anglaise et ses parents, sans conjoint actif au départ ; aucun événement programmé.'),),
    'Mathilde de Savoie': ((LOUIS_P, 'Mathilde de Savoie : seconde épouse future de Louis III du Palatinat, mariée le 30 novembre 1417, exclue du départ ; aucun événement programmé.'),
                           (MATHILDE_S, 'Mathilde de Savoie : épouse de Louis III du Palatinat après le départ ; exclue, aucun événement programmé.')),
    'Frédéric IV d’Autriche': ((ROBERT, 'Frédéric IV d’Autriche : époux futur d’Élisabeth du Palatinat, marié le 24 décembre 1407 à Innsbruck, exclu du départ ; aucun événement programmé.'),
                               (FREDERIC_A, 'Frédéric IV d’Autriche : époux futur d’Élisabeth du Palatinat ; il n’est pas Albert IV d’Autriche, aucun lien vers personne-grande-30.')),
    'Catherine de Poméranie': ((CATHERINE_P, 'Catherine de Poméranie : épouse future de Jean de Neumarkt, mariée le 15 août 1407 à Ribe, exclue du départ ; aucun événement programmé.'),
                               (JEAN_N, 'Catherine de Poméranie : épouse future de Jean de Neumarkt, en 1407 ; exclue, aucun événement programmé.')),
    'Anna de Veldenz': ((ETIENNE_S, 'Anna de Veldenz : épouse future d’Étienne de Simmern-Deux-Ponts, en juin 1410, exclue du départ ; aucun événement programmé.'),
                        (ANNA_V, 'Anna de Veldenz : épouse future d’Étienne de Simmern-Deux-Ponts, en 1409 ; divergence conservée, exclue, aucun événement programmé.')),
    'Jeanne de Bavière-Landshut': ((OTTON_M, 'Jeanne de Bavière-Landshut : née en 1413, épouse future d’Otton de Mosbach en janvier 1430, exclue du départ ; aucun événement programmé.'),)})
PALATINAT_EXCLUSIONS = ETAT_PALATINAT[4]
# Fiche de chef de Robert III (`chefs`) : nom, maison, naissance au jour, page d'identité et de naissance, repères de la naissance.
CHEF_FICHE_PAL = ('Robert III de Wittelsbach', PALATINAT, {'valeur': '1352-05-05', 'precision': 'jour'}, WP + 'Rupert_of_Germany', ('1352-05-05',))
PALATINAT_DIVERGENCES = ('27 juin 1374', 'Amberg', '18 mai 1410', '21 août 1400', 'Robert II', 'Béatrice de Sicile', 'Beatrice of Aragon', '13 décembre 1358', '26 juillet 1411', '6 février 1393',
                         'Charles II de Lorraine', '27 août 1434', '26 août 1434', 'vers 1377', '7 mars 1401', 'fils aîné vivant', 'troisième fils', '6 juillet 1402', '30 novembre 1417',
                         'peu avant mars 1400', 'peu avant l’année 1400', '24 décembre 1407', '15 août 1407', '13–14 mars 1443', 'juin 1410', '1409', 'janvier 1430', '1413', 'neuf enfants',
                         '25 janvier 1397', 'ni célibat ni veuvage', 'aucune absence attestée')
REPERES_PAL = {**{'personne-' + i: v[7] for i, v in FICHES_PALATINAT.items()}, CHEF_PAL: LIEN_PALATINAT[2], PALATINAT: {}}


def _palatinat(fiches=None, etat=None):
    try: _palatinat_controle(fiches, etat)
    except (KeyError, TypeError, AttributeError) as erreur: raise AssertionError(f'fiche palatine malformée : {erreur!r}') from erreur


def _palatinat_controle(fiches, etat):
    if fiches is not None:
        enfants = {'personne-' + i for i in ENFANTS_PALATINAT}
        assert {CHEF_PAL, BLANCHE_PAL} | {'personne-' + i for i in FICHES_PALATINAT} <= set(fiches)
        assert {i for i, f in fiches.items() if f.get('maison') == PALATINAT and i != CHEF_PAL} == {'personne-' + i for i in FICHES_PALATINAT}
        for i, (nom, maison, naissance, pere, mere, conjoints, sources, reperes) in FICHES_PALATINAT.items():
            f = fiches['personne-' + i]
            assert (f['nom'], f['maison'], f['naissance'], f['pere'], f['mere'], tuple(f['conjoints']), f['presence']) == (nom, maison, naissance, pere, mere, conjoints, 'vivante')
            _lacunes_b(f['sources'], f['lacunes'], sources, reperes)
        conjoints, sources, reperes = LIEN_PALATINAT
        c = fiches[CHEF_PAL]
        assert (c['pere'], c['mere'], tuple(c['conjoints']), c['presence']) == (None, None, conjoints, 'vivante')
        champs = ('pere', 'mere', 'conjoints', 'presence')
        _lacunes_b({k: c['sources'][k] for k in champs}, {k: c['lacunes'][k] for k in champs}, sources, reperes)
        # Blanche d’Angleterre : la seule de son nom, anglaise, sans conjoint, sa lacune inchangée.
        assert [i for i, f in fiches.items() if f.get('nom') == 'Blanche d’Angleterre'] == [BLANCHE_PAL]
        blanche = fiches[BLANCHE_PAL]
        assert blanche['maison'] == 'grande-1' and blanche['conjoints'] == [] and blanche['sources']['conjoints'] is None
        assert blanche['lacunes']['conjoints'] == 'Relation non intégrée dans ce lot ; aucune absence attestée.'
        # Seuls les huit enfants ont Robert pour père et Élisabeth pour mère ; une seule union, jamais d’union future ni d’enfant inventé.
        assert {i for i, f in fiches.items() if f.get('pere') == CHEF_PAL} == {i for i, f in fiches.items() if f.get('mere') == EPOUSE_PAL} == enfants
        assert {i for i, f in fiches.items() if CHEF_PAL in f.get('conjoints', [])} == {EPOUSE_PAL} and {i for i, f in fiches.items() if EPOUSE_PAL in f.get('conjoints', [])} == {CHEF_PAL}
        # Aucun lien vers une autre maison : ni Blanche, ni Albert IV, ni Frédéric IV.
        famille = enfants | {CHEF_PAL, EPOUSE_PAL}
        for i, f in fiches.items():
            liens = {f.get('pere'), f.get('mere'), *f.get('conjoints', [])} - {None}
            if i in famille: assert liens <= famille
            else: assert not liens & famille
        assert not any({BLANCHE_PAL, AUTRICHE_PAL} & ({f.get('pere'), f.get('mere')} | set(f.get('conjoints', []))) for i, f in fiches.items() if i in famille)
    if etat is not None:
        conjoints, enfants, sources, reperes, exclusions = ETAT_PALATINAT
        assert etat['maison'] == PALATINAT and (etat['conjoints'], etat['enfants']) == (conjoints, enfants) and set(etat['sources']) == set(etat['lacunes']) == {'conjoints', 'enfants'}
        _lacunes_b(etat['sources'], etat['lacunes'], sources, reperes)
        assert set(etat['exclusions']) == set(exclusions)
        for nom, faits in exclusions.items():
            x = etat['exclusions'][nom]
            assert set(x) == {'motif', 'sources'} and x['motif'] == ' '.join(f for _, f in faits) and x['sources'] == [{'url': u, 'fait': f} for u, f in faits]


def _chef_palatinat(chef):
    try:
        nom, maison, naissance, page, reperes = CHEF_FICHE_PAL
        assert (chef['nom'], chef['maison'], chef['naissance']) == (nom, maison, naissance)
        assert chef['sources']['identite']['url'] == chef['sources']['naissance']['url'] == page
        assert chef['lacunes']['identite'] is None and chef['lacunes']['naissance'] is None
        assert 'Robert III' in chef['sources']['identite']['fait'] and all(r in chef['sources']['naissance']['fait'] for r in reperes)
    except (KeyError, TypeError, AttributeError) as erreur: raise AssertionError(f'fiche de chef palatine malformée : {erreur!r}') from erreur


def _preuve_monde_palatinat(personnes):
    _chef_palatinat(next(f for f in personnes if f['id'] == CHEF_PAL))
    _familles_historiques([f for f in personnes if f['id'] != 'personne-' + f['maison']],
                          [f for f in personnes if f['id'] == 'personne-' + f['maison'] and CHAMPS_FAMILIAUX & f.keys()])
    _etats_historiques([f['etat_familial'] for f in personnes if 'etat_familial' in f])


def test_familles_historiques_palatinat():
    d, monde = _personnages(), World.charger(0)
    def resolus(c):
        return c['familles'] + [{**h, **l} for l in c['liens'] for h in c['chefs'] if l['id'] == 'personne-' + h['maison']]
    def refuse(c, controle=False, palatinat=False):
        if controle: assert _controler_famille(resolus(c))
        if palatinat:
            with pytest.raises(AssertionError): _palatinat({f['id']: f for f in resolus(c)})
        with pytest.raises(AssertionError): _familles_historiques(c['familles'], c['liens']); _etats_historiques(c['etats'])
    def altere(chemin, valeur):
        refuse(_alterer_personnages(d, chemin, valeur))
    _familles_historiques(d['familles'], d['liens']); _etats_historiques(d['etats'])
    _chef_palatinat(next(c for c in d['chefs'] if c['maison'] == PALATINAT))
    _palatinat({f['id']: f for f in d['familles'] + d['liens']}); _palatinat(etat=next(e for e in d['etats'] if e['maison'] == PALATINAT))
    assert len(d['familles']) == 102 and len(d['liens']) == len(d['etats']) == 29 and len(PALATINAT_EXCLUSIONS) == 7 and len(FICHES_PALATINAT) == 9 and len(ENFANTS_PALATINAT) == 8
    assert {e['maison'] for e in d['etats']} == {f['etat_familial']['maison'] for f in monde.personnages if 'etat_familial' in f} == MAISONS_AVEC_ETAT
    assert len(monde.personnages) == 2388
    _preuve_monde_palatinat(list(monde.personnages))
    # Chaque repère se lit quelque part dans les feuilles de la famille : un repère introuvable ne prouverait rien.
    feuilles = []
    for t in ('familles', 'liens', 'etats'):
        for f in d[t]:
            if f.get('id', f.get('maison')) not in {'personne-' + i for i in FICHES_PALATINAT} | {CHEF_PAL, PALATINAT}: continue
            for chemin in _feuilles(f):
                valeur = f
                for cle in chemin: valeur = valeur[cle]
                if isinstance(valeur, str): feuilles.append(valeur)
    assert all(any(r in v for v in feuilles) for r in PALATINAT_DIVERGENCES)
    ids = {'personne-' + i for i in FICHES_PALATINAT} | {CHEF_PAL, PALATINAT}
    for t in ('familles', 'liens', 'etats'):
        for j, f in enumerate(d[t]):
            if f.get('id', f.get('maison')) not in ids: continue
            altere((t,), d[t][:j] + d[t][j+1:]); altere((t,), d[t] + [copy.deepcopy(f)])
            for chemin in _feuilles(f):
                valeur = f
                for cle in chemin: valeur = valeur[cle]
                altere((t, j, *chemin), ['personne-grande-9'] if valeur == [] else 'Altéré')
                if isinstance(valeur, str):
                    for repere in PALATINAT_DIVERGENCES:
                        if repere in valeur: altere((t, j, *chemin), valeur.replace(repere, 'inconnu'))
            for nom in f.get('exclusions', {}): altere((t, j, 'exclusions', nom), 'SUPPRIMER')
            if t == 'etats':
                for champ, etats in (('conjoints', ('lacune', 'veuvage')), ('enfants', ('lacune', 'absence_attestee'))):
                    for etat in etats: altere((t, j, champ), etat)
            for champ, liste in REPERES_PAL.get(f.get('id', f.get('maison')), {}).items():
                for repere in liste: altere((t, j, 'lacunes', champ), f['lacunes'][champ].replace(repere, 'inconnu'))
                if f.get('maison') == PALATINAT and champ == 'conjoints': altere((t, j, 'lacunes', champ), f['nom'] + ' : absence attestée de tout conjoint.')
    # La fiche du chef : nom, naissance (jour, précision), sources ; dans le monde aussi.
    j = next(k for k, c in enumerate(d['chefs']) if c['maison'] == PALATINAT)
    chef = d['chefs'][j]
    for chemin, valeur in ((('nom',), 'Robert II du Palatinat'), (('maison',), 'grande-30'), (('naissance',), _naissance_famille('1352-05-06')), (('naissance',), _naissance_famille('1352', 'annee')),
                           (('sources', 'identite', 'url'), ROBERT), (('sources', 'naissance', 'url'), ELISABETH_N), (('lacunes', 'naissance'), 'Naissance inconnue.')):
        with pytest.raises(AssertionError): _chef_palatinat(_alterer_personnages(chef, chemin, valeur))
    with pytest.raises(AssertionError): _chef_palatinat(_alterer_personnages(next(f for f in monde.personnages if f['id'] == CHEF_PAL), ('nom',), 'Robert II du Palatinat'))
    modele = next(f for f in d['familles'] if f['id'] == LOUIS_PAL)
    def relie(c, i, j):
        a, b = (next(f for f in c['familles'] + c['liens'] if f['id'] == k) for k in (i, j))
        a['conjoints'].append(j); b['conjoints'].append(i)
    # Blanche d’Angleterre et Louis, conjoints réciproques ; Élisabeth et Frédéric IV (`grande-30` : Albert IV) ; Agnès et un conjoint actif.
    c = copy.deepcopy(d); relie(c, BLANCHE_PAL, LOUIS_PAL); refuse(c, controle=True, palatinat=True)
    c = copy.deepcopy(d); relie(c, 'personne-elisabeth-palatinat', AUTRICHE_PAL); refuse(c, controle=True, palatinat=True)
    c = copy.deepcopy(d); c['familles'].append(dict(copy.deepcopy(modele), id='personne-adolphe-cleves', nom='Adolphe Ier de Clèves', conjoints=[], pere=None, mere=None))
    relie(c, 'personne-agnes-palatinat', 'personne-adolphe-cleves'); refuse(c, controle=True, palatinat=True)
    # Une seconde « Blanche d’Angleterre », de `grande-29`, conjointe réciproque de Louis.
    c = copy.deepcopy(d); c['familles'].append(dict(copy.deepcopy(modele), id='personne-blanche-intruse', nom='Blanche d’Angleterre', pere=None, mere=None, conjoints=[]))
    relie(c, 'personne-blanche-intruse', LOUIS_PAL); refuse(c, controle=True, palatinat=True)
    # Les naissances que le lot refuse de redevenir imprécises, et un état de la Horde.
    for i, naissance in (('frederic-palatinat', _naissance_famille('1377', 'annee')), ('elisabeth-nuremberg', _naissance_famille('1358', 'annee'))):
        k = next(k for k, f in enumerate(d['familles']) if f['id'] == 'personne-' + i)
        altere(('familles', k, 'naissance'), naissance)
    c = copy.deepcopy(d); c['etats'].append(dict(copy.deepcopy(next(e for e in d['etats'] if e['maison'] == PALATINAT)), maison='grande-21')); refuse(c)
    c = copy.deepcopy(d); c['etats'] = [e for e in c['etats'] if e['maison'] != PALATINAT]; refuse(c)
    # Des copies de Louis, enfants de Robert et d’Élisabeth : mort avant 1400, conjoints futurs, héritier inventé.
    base = next(f for f in monde.personnages if f['id'] == LOUIS_PAL)
    intrus = [('Robert Pipan', 'decedee', ('enfant',))]
    intrus += [(nom, 'vivante', ('enfant', 'conjoint')) for nom in ('Blanche d’Angleterre', 'Mathilde de Savoie', 'Frédéric IV d’Autriche', 'Catherine de Poméranie', 'Anna de Veldenz', 'Jeanne de Bavière-Landshut', 'Héritier inventé')]
    for nom, presence, roles in intrus:
        for role in roles:
            c = copy.deepcopy(d); ajout = dict(copy.deepcopy(modele), id='personne-intruse', nom=nom, presence=presence, pere=None, mere=None, conjoints=[]); c['familles'].append(ajout)
            if role == 'enfant': ajout['pere'], ajout['mere'] = CHEF_PAL, EPOUSE_PAL
            else: ajout['conjoints'] = [CHEF_PAL]; next(x for x in c['liens'] if x['id'] == CHEF_PAL)['conjoints'].append(ajout['id'])
            refuse(c, controle=True, palatinat=True)
            clone = {k: copy.deepcopy(v) for k, v in base.items()}
            clone.update(id='personne-intruse', nom=nom, presence=presence, pere=None, mere=None, conjoints=[])
            personnes = [copy.deepcopy(f) for f in monde.personnages]
            chef = next(f for f in personnes if f['id'] == CHEF_PAL)
            if role == 'enfant': clone.update(pere=CHEF_PAL, mere=EPOUSE_PAL)
            else: clone['conjoints'] = [CHEF_PAL]; chef['conjoints'].append(clone['id'])
            with pytest.raises(AssertionError): _palatinat({f['id']: f for f in personnes + [clone]})
            with pytest.raises(AssertionError): _preuve_monde_palatinat(personnes + [clone])


# Notices examinées le 14 novembre 2026 ; attentes indépendantes du catalogue.
FWP = 'https://fr.wikipedia.org/wiki/'
ROBERT_FR, GUILLAUME_FR, WALERAN_FR, MARIE_FR = (FWP + p for p in ('Robert_Ier_de_Bar#Mariage_et_enfants', 'Guillaume_II_de_Namur', 'Waléran_III_de_Luxembourg-Ligny', 'Marie_de_France_(1344-1404)'))
(ROBERT_EN, MARIE_EN, VIOLANT, JEAN_A, HENRI_B, LOUIS_B, EDOUARD_B, JEAN_BAR, GUILLAUME_EN, WALERAN_EN, THEODORE_M, ADOLPHE_J) = (WP + p for p in (
    'Robert,_Duke_of_Bar#Marriage_and_issue', 'Marie_of_France,_Duchess_of_Bar', 'Violant_of_Bar', 'John_I_of_Aragon', 'Henry_of_Bar', 'Louis_I,_Duke_of_Bar', 'Edward_III_of_Bar',
    'John_of_Bar', 'William_II_of_Namur', 'Waleran_III_of_Ligny', 'Theodore_II_of_Montferrat', 'Adolf,_Duke_of_Jülich-Berg'))
BAR = 'seigneurie-1'
CHEF_BAR, EPOUSE_BAR, MARIE_FRANCE_ID, THEODORE_II_ID, YOLANDE_JEUNE_BAR = 'personne-seigneurie-1', 'personne-marie-valois', 'personne-marie', 'personne-theodore-ii', 'personne-yolande-jeune-bar'
ENFANTS_BAR = ('yolande-bar', 'louis-bar', 'edouard-bar', 'yolande-jeune-bar', 'jean-bar', 'jeanne-bar')
SANS_BORNES_BAR = ('yolande-bar', 'louis-bar', 'yolande-jeune-bar', 'jeanne-bar')
PARENTS_BAR = 'de Robert Ier de Bar et de Marie de Valois'
# La fiche de Marie de France (fille de Charles VI) : elle ne change pas, mot pour mot.
_CF = 'https://en.wikipedia.org/wiki/Charles_VI_of_France#Marriage_and_issue'
FICHE_MARIE_FRANCE = {
    'id': 'personne-marie', 'maison': 'grande-3', 'nom': 'Marie de France', 'naissance': {'valeur': '1393-08-22', 'precision': 'jour'}, 'pere': 'personne-grande-3', 'mere': 'personne-isabeau',
    'conjoints': [], 'presence': 'vivante', 'sources': {
        'identite': {'url': _CF, 'fait': 'Marie de France figure dans la famille de Charles VI.'},
        'naissance': {'url': _CF, 'fait': 'Marie de France : naissance 1393-08-22.'},
        'presence': {'url': _CF, 'fait': 'Marie de France a une naissance antérieure au 1er janvier 1400 et un décès le 1438-08-19 ; présence vivante au départ.'},
        'pere': {'url': _CF, 'fait': 'Marie de France est enfant de Charles VI et d’Isabeau de Bavière.'},
        'mere': {'url': _CF, 'fait': 'Marie de France est enfant de Charles VI et d’Isabeau de Bavière.'}, 'conjoints': None},
    'lacunes': {'identite': None, 'naissance': None, 'presence': None, 'pere': None, 'mere': None, 'conjoints': 'Relation non étudiée dans ce lot ; aucune absence attestée.'}}


def _enfant_bar(nom, naissance, identite, fait_naissance, fait_presence, reperes, url_identite=ROBERT_EN, url_naissance=ROBERT_EN, url_presence=ROBERT_EN, lacune_naissance=None):
    qualite = 'fille' if nom.split()[0] in ('Yolande', 'Jeanne') else 'fils'
    filiation = (ROBERT_EN, f'{nom} est {qualite} {PARENTS_BAR} ; ' + ROBERT_FR + ', ' + MARIE_EN + ' et ' + MARIE_FR + ' donnent la même liste de onze enfants.')
    sources = {'identite': (url_identite, identite), 'presence': (url_presence, fait_presence), 'pere': filiation, 'mere': filiation}
    if fait_naissance: sources['naissance'] = (url_naissance, fait_naissance)
    else: reperes = {**reperes, 'naissance': lacune_naissance}
    return (nom, BAR, naissance, CHEF_BAR, EPOUSE_BAR, (), sources, reperes)


# id : (nom, maison, naissance, père, mère, conjoints, sources {champ : (page, fait)}, repères des lacunes {champ : repères})
FICHES_BAR = {
    'marie-valois': ('Marie de Valois', BAR, {'valeur': '1344-09-18', 'precision': 'jour'}, None, None, (CHEF_BAR,), {
        'identite': (MARIE_EN, 'Marie de Valois, fille de Jean II le Bon, épouse de Robert Ier de Bar ; ses pages la titrent « Marie de France » (' + MARIE_FR + ') ou « Marie of France » (' + MARIE_EN + '), '
                     + ROBERT_EN + ' la nomme « Marie of Valois » ; le monde la distingue de personne-marie, Marie de France, fille de Charles VI née le 22 août 1393.'),
        'naissance': (MARIE_EN, 'Marie de Valois : née le 18 septembre 1344 à Saint-Germain-en-Laye (' + MARIE_EN + ' ; ' + MARIE_FR + ').'),
        'presence': (MARIE_EN, 'Marie de Valois, morte le 15 octobre 1404 (' + MARIE_EN + ' ; ' + MARIE_FR + ') ; vivante au 1er janvier 1400, décès cité pour la sélection initiale.'),
        'conjoints': (ROBERT_FR, 'Marie de Valois et Robert Ier de Bar sont mariés depuis le 5 octobre 1364, avec une dot de soixante mille livres (' + ROBERT_FR + ' ; ' + MARIE_FR + ') ; union active au départ.')},
        {'pere': ('Marie de Valois', 'Jean II le Bon', MARIE_EN, 'Charles V', 'Philippe le Hardi', 'aucun lien de fratrie', 'hors périmètre', 'aucune fiche créée', 'aucune absence attestée'),
         'mere': ('Marie de Valois', 'Bonne de Luxembourg', 'Bonne of Bohemia', MARIE_FR, ROBERT_EN, MARIE_EN, 'hors périmètre', 'aucune fiche créée', 'aucune absence attestée')}),
    'yolande-bar': _enfant_bar('Yolande de Bar', {'valeur': 'vers 1365', 'precision': 'vers'},
        'Yolande de Bar, reine douairière d’Aragon, fille ' + PARENTS_BAR + ', « huitième de onze enfants » pour ' + VIOLANT + '.',
        'Yolande de Bar : née « c. 1365 » (' + VIOLANT + ' ; ' + JEAN_A + ') ; ' + ROBERT_EN + ' et ' + ROBERT_FR + ' donnent 1365, divergence conservée ; aucune borne n’est inventée.',
        'Yolande de Bar, morte le 3 juillet 1431 à Barcelone (' + VIOLANT + ') ; vivante au 1er janvier 1400, décès cité pour la sélection initiale.',
        {'conjoints': ('Yolande de Bar', 'veuve de Jean Ier d’Aragon', '2 février 1380', '1384', '19 mai 1396', '1395', JEAN_A, VIOLANT, MARIE_FR, 'aucune union active', 'personne-grande-6', 'Yolande d’Aragon', 'hors périmètre', 'aucune absence attestée')},
        url_identite=VIOLANT, url_naissance=VIOLANT, url_presence=VIOLANT),
    'louis-bar': _enfant_bar('Louis de Bar', {'valeur': 'entre 1370 et 1375', 'precision': 'intervalle'},
        'Louis de Bar, cardinal, fils ' + PARENTS_BAR + ', « cinquième fils » (' + LOUIS_B + '), cardinal depuis 1391, évêque de Langres depuis 1397 (1395 pour ' + MARIE_FR + ') ; aîné des fils vivants au départ, aucun héritier n’est désigné.',
        'Louis de Bar : né entre 1370 et 1375 (' + LOUIS_B + ' ; ' + ROBERT_EN + ') ; aucune borne n’est inventée.',
        'Louis de Bar, mort le 23 juin 1430 (' + LOUIS_B + '), le 26 juin 1430 (' + ROBERT_EN + ') ou en 1431 (' + MARIE_EN + ' ; ' + MARIE_FR + ') ; vivant au 1er janvier 1400, divergence conservée.',
        {'conjoints': ('Louis de Bar', 'homme d’Église', 'aucune épouse nommée', LOUIS_B, 'ni célibat ni veuvage', 'aucune absence attestée')}, url_identite=LOUIS_B, url_naissance=LOUIS_B, url_presence=LOUIS_B),
    'edouard-bar': _enfant_bar('Édouard de Bar', {'valeur': '1377-06', 'precision': 'mois'},
        'Édouard de Bar, fils ' + PARENTS_BAR + ', marquis de Pont-à-Mousson depuis 1399, héritier du duché après la mort de ses frères aînés (' + EDOUARD_B + ') ; aîné des fils laïcs vivants au départ, aucun héritier n’est désigné.',
        'Édouard de Bar : né fin juin 1377 (« late June 1377 », ' + EDOUARD_B + ') ; ' + ROBERT_EN + ' et ' + ROBERT_FR + ' donnent 1377, divergence conservée.',
        'Édouard de Bar, tué à Azincourt le 25 octobre 1415 (' + EDOUARD_B + ') ; vivant au 1er janvier 1400, décès cité pour la sélection initiale.',
        {'conjoints': ('Édouard de Bar', '« never married »', EDOUARD_B, 'aucune épouse nommée', 'enfants illégitimes', 'hors périmètre', 'aucune absence attestée')},
        url_identite=EDOUARD_B, url_naissance=EDOUARD_B, url_presence=EDOUARD_B),
    'yolande-jeune-bar': _enfant_bar('Yolande la Jeune de Bar', {'valeur': 'vers 1378', 'precision': 'vers'},
        'Yolande la Jeune de Bar, fille ' + PARENTS_BAR + ' ; elle porte le prénom de sa sœur aînée « pour des raisons incertaines » (' + MARIE_EN + ').',
        'Yolande la Jeune de Bar : née « c. 1378 » (' + ADOLPHE_J + ') ; aucune borne n’est inventée.',
        'Yolande la Jeune de Bar, morte le 10 janvier 1421 (' + ADOLPHE_J + ' ; 1421 pour ' + ROBERT_EN + ' et ' + ROBERT_FR + ') ; vivante au 1er janvier 1400, décès cité pour la sélection initiale.',
        {'conjoints': ('Yolande la Jeune de Bar', 'Adolphe de Juliers et de Berg', 'château de Dun', ADOLPHE_J, ROBERT_EN, ROBERT_FR, 'sans jour', 'aucun conjoint actif', 'hors périmètre', 'aucune absence attestée')},
        url_identite=MARIE_EN, url_naissance=ADOLPHE_J, url_presence=ADOLPHE_J),
    'jean-bar': _enfant_bar('Jean de Bar', {'valeur': '1380', 'precision': 'annee'},
        'Jean de Bar, fils ' + PARENTS_BAR + ', seigneur de Puisaye (' + JEAN_BAR + ').',
        'Jean de Bar : né en 1380, année que donnent ' + JEAN_BAR + ', ' + ROBERT_EN + ' et ' + ROBERT_FR + '.',
        'Jean de Bar, tué à Azincourt le 25 octobre 1415 (' + JEAN_BAR + ') ; vivant au 1er janvier 1400, décès cité pour la sélection initiale.',
        {'conjoints': ('Jean de Bar', 'aucune épouse nommée', JEAN_BAR, ROBERT_EN, 'ni célibat ni veuvage', 'aucune absence attestée')}, url_identite=JEAN_BAR, url_naissance=JEAN_BAR, url_presence=JEAN_BAR),
    'jeanne-bar': _enfant_bar('Jeanne de Bar', None,
        'Jeanne de Bar, fille ' + PARENTS_BAR + ', marquise de Montferrat depuis 1393 (' + THEODORE_M + ').',
        None,
        'Jeanne de Bar, morte le 15 janvier 1402 (' + THEODORE_M + ' ; ' + MARIE_EN + ' ; 1402 pour ' + ROBERT_EN + ', ' + ROBERT_FR + ' et ' + MARIE_FR + ') ; vivante au 1er janvier 1400, décès cité pour la sélection initiale.',
        {'conjoints': ('Jeanne de Bar', 'Théodore II Paléologue', 'Montferrat', '1393', THEODORE_M, ROBERT_EN, ROBERT_FR, MARIE_EN, MARIE_FR, 'sans fiche', 'personne-theodore-ii', 'aucune absence attestée')},
        url_identite=THEODORE_M, url_presence=THEODORE_M,
        lacune_naissance=('Jeanne de Bar', 'aucune page ne donne sa naissance', THEODORE_M, ROBERT_EN, ROBERT_FR, MARIE_EN, MARIE_FR, 'aucune borne')),
}
# conjoints, sources {champ : (page, fait)}, repères des lacunes
LIEN_BAR = ((EPOUSE_BAR,), {
    'presence': (ROBERT_FR, 'Robert Ier, duc de Bar jusqu’à sa mort, le 12 avril 1411 (' + ROBERT_FR + ' ; ' + ROBERT_EN + ') ; il cède le duché à Édouard en 1401 en gardant l’usufruit et écarte son petit-fils Robert, fils d’Henri, '
                 'après le départ ; en fonction et vivant au 1er janvier 1400, aucune cession ni mort programmée.'),
    'conjoints': (ROBERT_FR, 'Robert Ier et Marie de Valois sont mariés depuis le 5 octobre 1364, après dispense du pape Urbain V (' + ROBERT_FR + ') ; ' + ROBERT_EN + ' donne 1364 ; union active au départ.')},
    {'pere': ('Robert Ier', 'Henri IV de Bar', ROBERT_FR, 'hors périmètre', 'aucune fiche créée', 'aucune absence attestée'),
     'mere': ('Robert Ier', 'Yolande de Flandre', 'Yolande of Flanders', 'Yolande de Dampierre', ROBERT_FR, ROBERT_EN, 'hors périmètre', 'aucune fiche créée', 'aucune absence attestée')})
ETAT_BAR = ('union', 'documentes', {
    'conjoints': (ROBERT_FR, 'Robert Ier et Marie de Valois sont mariés depuis le 5 octobre 1364 ; état union, avant le départ.'),
    'enfants': (ROBERT_EN, 'Robert Ier et Marie de Valois ont onze enfants (' + ROBERT_EN + ' ; ' + ROBERT_FR + ', ' + MARIE_EN + ' et ' + MARIE_FR + ' donnent la même liste), dont six vivants au 1er janvier 1400 : '
                           'Yolande, Louis, Édouard, Yolande la Jeune, Jean et Jeanne ; Henri et Charles, morts avant 1400, sont exclus, ainsi que Philippe, Marie et Bonne, de présence indéterminée.')}, {}, {
    'Henri de Bar': ((ROBERT_EN, 'Henri de Bar : fils aîné ' + PARENTS_BAR + ', né vers 1362, mort de la peste en octobre 1397 à Trévise, au retour de Nicopolis, avant le départ ; exclu, aucun événement programmé.'),
                     (HENRI_B, 'Henri de Bar : mort à Trévise en octobre 1397 (' + MARIE_EN + ' ; ' + ROBERT_FR + ') ; la naissance de 1362, antérieure au mariage de 1364, est discutée par ' + ROBERT_EN + ' ; il n’a ni fiche ni résurrection.')),
    'Philippe de Bar': ((ROBERT_EN, 'Philippe de Bar : fils ' + PARENTS_BAR + ', tué à Nicopolis en 1396 selon ' + ROBERT_EN + ' et ' + MARIE_FR + ', le 25 septembre 1396 selon ' + MARIE_EN + ', « at or soon after » la bataille selon '
                         + EDOUARD_B + ' ; présence indéterminée au 1er janvier 1400, exclu des vivants, sans décès ni survie déduits.'),
                        (ROBERT_FR, 'Philippe de Bar : ' + ROBERT_FR + ' le dit mort en 1404 dans une prison turque, marié en 1384 à Yolande d’Enghien ; divergence conservée ; il n’a ni fiche ni union active, aucun événement programmé.')),
    'Charles de Bar': ((ROBERT_EN, 'Charles de Bar : fils ' + PARENTS_BAR + ', né en 1373, seigneur de Nogent-le-Rotrou, mort en 1392, avant le départ ; exclu, aucun événement programmé.'),
                       (ROBERT_FR, 'Charles de Bar : mort en 1392 selon ' + ROBERT_FR + ', ' + MARIE_EN + ' et ' + MARIE_FR + ' ; mort avant 1400, il n’a ni fiche ni résurrection.')),
    'Marie de Bar': ((ROBERT_EN, 'Marie de Bar : fille ' + PARENTS_BAR + ', comtesse de Namur, née en 1374, sans date de mort (« 1374 †? ») ; présence indéterminée au 1er janvier 1400, exclue des vivants sans décès inventé.'),
                     (GUILLAUME_EN, 'Marie de Bar : mariée en 1384 à Guillaume II de Namur (' + ROBERT_EN + ' ; ' + ROBERT_FR + ' ; ' + MARIE_EN + ' ; ' + MARIE_FR + ') ; Guillaume II se remarie en 1393 avec Jeanne d’Harcourt ('
                      + GUILLAUME_EN + ' ; ' + GUILLAUME_FR + ') ; elle n’a ni fiche ni union active, aucun événement programmé.')),
    'Bonne de Bar': ((ROBERT_EN, 'Bonne de Bar : fille ' + PARENTS_BAR + ', comtesse de Saint-Pol, morte en 1436 selon ' + ROBERT_EN + ', en 1400 sans jour selon ' + MARIE_FR + ', ' + WALERAN_EN + ' et ' + WALERAN_FR + ' ; '
                      + ROBERT_FR + ' écrit « † 1400 ou 1436 ? » ; présence indéterminée au 1er janvier 1400 : une mort en 1400 sans jour ne dit pas qui vit au départ ; exclue des vivants, ni vivante ni décédée par déduction.'),
                     (WALERAN_EN, 'Bonne de Bar : mariée en 1393 à Waléran III de Luxembourg, comte de Ligny et de Saint-Pol (' + ROBERT_EN + ' ; ' + ROBERT_FR + ' ; ' + MARIE_EN + ' ; ' + WALERAN_FR
                      + ' ; « c. 1392 » dans l’infobox de ' + WALERAN_EN + ') ; elle n’a ni fiche ni union active, aucun événement programmé.')),
    'Adolphe de Juliers': ((ADOLPHE_J, 'Adolphe de Juliers : époux futur de Yolande la Jeune de Bar, marié en 1400 au château de Dun, sans jour (' + ADOLPHE_J + ' ; ' + ROBERT_EN + ' ; ' + ROBERT_FR
                            + ') ; l’union n’est pas établie au départ : ni fiche ni conjoint actif, aucun événement programmé.'),)})
BAR_EXCLUSIONS = ETAT_BAR[4]
# Fiche de chef de Robert Ier (`chefs`) : nom, maison, naissance au jour, page d'identité et de naissance, repères de la naissance.
CHEF_FICHE_BAR = ('Robert Ier de Bar', BAR, {'valeur': '1344-11-08', 'precision': 'jour'}, FWP + 'Robert_Ier_de_Bar', ('1344-11-08',))
BAR_DIVERGENCES = ('5 octobre 1364', 'Urbain V', '12 avril 1411', '1401', 'Henri IV de Bar', 'Yolande de Flandre', 'Yolande of Flanders', 'Yolande de Dampierre', '18 septembre 1344', 'Saint-Germain-en-Laye',
                   '15 octobre 1404', 'Jean II le Bon', 'Bonne de Luxembourg', 'Bonne of Bohemia', 'Marie of Valois', '22 août 1393', 'c. 1365', 'huitième de onze enfants', '3 juillet 1431', '2 février 1380',
                   '1384', '19 mai 1396', '1395', 'entre 1370 et 1375', 'cinquième fils', '23 juin 1430', '26 juin 1430', '1431', 'late June 1377', '1399', 'never married', '25 octobre 1415', 'c. 1378',
                   '10 janvier 1421', 'château de Dun', 'Puisaye', '15 janvier 1402', '1393', 'Montferrat', 'onze enfants', 'octobre 1397', 'Trévise', '25 septembre 1396', '1404', 'Yolande d’Enghien',
                   'Nogent-le-Rotrou', 'Guillaume II de Namur', 'Jeanne d’Harcourt', '1436', 'Saint-Pol', 'présence indéterminée', 'ni célibat ni veuvage', 'aucune absence attestée')
REPERES_BAR = {**{'personne-' + i: v[7] for i, v in FICHES_BAR.items()}, CHEF_BAR: LIEN_BAR[2], BAR: {}}


def _bar(fiches=None, etat=None):
    try: _bar_controle(fiches, etat)
    except (KeyError, TypeError, AttributeError) as erreur: raise AssertionError(f'fiche de Bar malformée : {erreur!r}') from erreur


def _bar_controle(fiches, etat):
    if fiches is not None:
        enfants = {'personne-' + i for i in ENFANTS_BAR}
        assert {CHEF_BAR, MARIE_FRANCE_ID, THEODORE_II_ID, 'personne-grande-6', 'personne-grande-27'} | {'personne-' + i for i in FICHES_BAR} <= set(fiches)
        assert {i for i, f in fiches.items() if f.get('maison') == BAR and i != CHEF_BAR} == {'personne-' + i for i in FICHES_BAR}
        for i, (nom, maison, naissance, pere, mere, conjoints, sources, reperes) in FICHES_BAR.items():
            f = fiches['personne-' + i]
            assert (f['nom'], f['maison'], f['naissance'], f['pere'], f['mere'], tuple(f['conjoints']), f['presence']) == (nom, maison, naissance, pere, mere, conjoints, 'vivante')
            _lacunes_b(f['sources'], f['lacunes'], sources, reperes)
        conjoints, sources, reperes = LIEN_BAR
        c = fiches[CHEF_BAR]
        assert (c['pere'], c['mere'], tuple(c['conjoints']), c['presence']) == (None, None, conjoints, 'vivante')
        champs = ('pere', 'mere', 'conjoints', 'presence')
        _lacunes_b({k: c['sources'][k] for k in champs}, {k: c['lacunes'][k] for k in champs}, sources, reperes)
        # Marie de Valois n'est pas Marie de France : la fille de Charles VI reste la seule de son nom, sa fiche inchangée mot pour mot.
        assert [i for i, f in fiches.items() if f.get('nom') == 'Marie de France'] == [MARIE_FRANCE_ID]
        assert [i for i, f in fiches.items() if f.get('nom') == 'Marie de Valois'] == [EPOUSE_BAR]
        assert {k: v for k, v in fiches[MARIE_FRANCE_ID].items() if k != 'origine'} == FICHE_MARIE_FRANCE
        # Seuls les six enfants ont Robert pour père et Marie de Valois pour mère ; une seule union, jamais d'union future ni d'enfant inventé.
        assert {i for i, f in fiches.items() if f.get('pere') == CHEF_BAR} == {i for i, f in fiches.items() if f.get('mere') == EPOUSE_BAR} == enfants
        assert {i for i, f in fiches.items() if CHEF_BAR in f.get('conjoints', [])} == {EPOUSE_BAR} and {i for i, f in fiches.items() if EPOUSE_BAR in f.get('conjoints', [])} == {CHEF_BAR}
        # Aucun lien vers une autre maison : ni Aragon, ni Montferrat (Théodore II Paléologue de `grande-15`), ni Bourgogne, ni Marie de France.
        famille = enfants | {CHEF_BAR, EPOUSE_BAR}
        for i, f in fiches.items():
            liens = {f.get('pere'), f.get('mere'), *f.get('conjoints', [])} - {None}
            if i in famille: assert liens <= famille
            else: assert not liens & famille
        assert not any({'personne-grande-6', THEODORE_II_ID, 'personne-grande-27', MARIE_FRANCE_ID} & ({f.get('pere'), f.get('mere')} | set(f.get('conjoints', []))) for i, f in fiches.items() if i in famille)
        assert fiches[THEODORE_II_ID]['conjoints'] == [] and fiches['personne-grande-6']['mere'] is None
        # Les cinq autres seigneuries restent sans complément ni fiche.
        assert {i for i in fiches if i.startswith('personne-seigneurie-')} == {CHEF_BAR}
        assert {f['maison'] for f in fiches.values() if f.get('maison', '').startswith('seigneurie-')} == {BAR}
    if etat is not None:
        conjoints, enfants, sources, reperes, exclusions = ETAT_BAR
        assert etat['maison'] == BAR and (etat['conjoints'], etat['enfants']) == (conjoints, enfants) and set(etat['sources']) == set(etat['lacunes']) == {'conjoints', 'enfants'}
        _lacunes_b(etat['sources'], etat['lacunes'], sources, reperes)
        assert set(etat['exclusions']) == set(exclusions)
        for nom, faits in exclusions.items():
            x = etat['exclusions'][nom]
            assert set(x) == {'motif', 'sources'} and x['motif'] == ' '.join(f for _, f in faits) and x['sources'] == [{'url': u, 'fait': f} for u, f in faits]


def _chef_bar(chef):
    try:
        nom, maison, naissance, page, reperes = CHEF_FICHE_BAR
        assert (chef['nom'], chef['maison'], chef['naissance']) == (nom, maison, naissance)
        assert chef['sources']['identite']['url'] == chef['sources']['naissance']['url'] == page
        assert chef['lacunes']['identite'] is None and chef['lacunes']['naissance'] is None
        assert 'Robert Ier de Bar' in chef['sources']['identite']['fait'] and all(r in chef['sources']['naissance']['fait'] for r in reperes)
    except (KeyError, TypeError, AttributeError) as erreur: raise AssertionError(f'fiche de chef de Bar malformée : {erreur!r}') from erreur


def _preuve_monde_bar(personnes):
    _chef_bar(next(f for f in personnes if f['id'] == CHEF_BAR))
    _familles_historiques([f for f in personnes if f['id'] != 'personne-' + f['maison']],
                          [f for f in personnes if f['id'] == 'personne-' + f['maison'] and CHAMPS_FAMILIAUX & f.keys()])
    _etats_historiques([f['etat_familial'] for f in personnes if 'etat_familial' in f])


def test_familles_historiques_bar():
    d, monde = _personnages(), World.charger(0)
    def resolus(c):
        return c['familles'] + [{**h, **l} for l in c['liens'] for h in c['chefs'] if l['id'] == 'personne-' + h['maison']]
    def refuse(c, controle=False, bar=False):
        if controle: assert _controler_famille(resolus(c))
        if bar:
            with pytest.raises(AssertionError): _bar({f['id']: f for f in resolus(c)})
        with pytest.raises(AssertionError): _familles_historiques(c['familles'], c['liens']); _etats_historiques(c['etats'])
    def altere(chemin, valeur):
        refuse(_alterer_personnages(d, chemin, valeur))
    _familles_historiques(d['familles'], d['liens']); _etats_historiques(d['etats'])
    _chef_bar(next(c for c in d['chefs'] if c['maison'] == BAR))
    _bar({f['id']: f for f in d['familles'] + d['liens']}); _bar(etat=next(e for e in d['etats'] if e['maison'] == BAR))
    assert len(d['familles']) == 102 and len(d['liens']) == len(d['etats']) == 29 and len(BAR_EXCLUSIONS) == 6 and len(FICHES_BAR) == 7 and len(ENFANTS_BAR) == 6
    assert {e['maison'] for e in d['etats']} == {f['etat_familial']['maison'] for f in monde.personnages if 'etat_familial' in f} == MAISONS_AVEC_ETAT
    assert not any(e['maison'].startswith('seigneurie-') and e['maison'] != BAR for e in d['etats'] + [f['etat_familial'] for f in monde.personnages if 'etat_familial' in f])
    assert len(monde.personnages) == 2388
    _preuve_monde_bar(list(monde.personnages))
    # Chaque repère se lit quelque part dans les feuilles de la famille : un repère introuvable ne prouverait rien.
    ids = {'personne-' + i for i in FICHES_BAR} | {CHEF_BAR, BAR}
    feuilles = []
    for t in ('familles', 'liens', 'etats'):
        for f in d[t]:
            if f.get('id', f.get('maison')) not in ids: continue
            for chemin in _feuilles(f):
                valeur = f
                for cle in chemin: valeur = valeur[cle]
                if isinstance(valeur, str): feuilles.append(valeur)
    assert all(any(r in v for v in feuilles) for r in BAR_DIVERGENCES)
    for t in ('familles', 'liens', 'etats'):
        for j, f in enumerate(d[t]):
            if f.get('id', f.get('maison')) not in ids: continue
            altere((t,), d[t][:j] + d[t][j+1:]); altere((t,), d[t] + [copy.deepcopy(f)])
            for chemin in _feuilles(f):
                valeur = f
                for cle in chemin: valeur = valeur[cle]
                altere((t, j, *chemin), ['personne-grande-9'] if valeur == [] else 'Altéré')
                if isinstance(valeur, str):
                    for repere in BAR_DIVERGENCES:
                        if repere in valeur: altere((t, j, *chemin), valeur.replace(repere, 'inconnu'))
            for nom in f.get('exclusions', {}): altere((t, j, 'exclusions', nom), 'SUPPRIMER')
            if t == 'etats':
                for champ, etats in (('conjoints', ('lacune', 'veuvage')), ('enfants', ('lacune', 'absence_attestee'))):
                    for etat in etats: altere((t, j, champ), etat)
            for champ, liste in REPERES_BAR.get(f.get('id', f.get('maison')), {}).items():
                for repere in liste: altere((t, j, 'lacunes', champ), f['lacunes'][champ].replace(repere, 'inconnu'))
                if f.get('maison') == BAR and champ == 'conjoints': altere((t, j, 'lacunes', champ), f['nom'] + ' : absence attestée de tout conjoint.')
    # Une lacune d'enfant ne devient pas une absence attestée.
    j = next(k for k, e in enumerate(d['etats']) if e['maison'] == BAR)
    altere(('etats', j, 'enfants'), 'absence_attestee'); altere(('etats', j, 'conjoints'), 'lacune')
    # La fiche du chef : nom, naissance (jour, précision), sources ; dans le monde aussi.
    j = next(k for k, c in enumerate(d['chefs']) if c['maison'] == BAR)
    chef = d['chefs'][j]
    for chemin, valeur in ((('nom',), 'Robert II de Bar'), (('maison',), 'seigneurie-2'), (('naissance',), _naissance_famille('1344-11-09')), (('naissance',), _naissance_famille('1344', 'annee')),
                           (('sources', 'identite', 'url'), ROBERT_EN), (('sources', 'naissance', 'url'), MARIE_EN), (('lacunes', 'naissance'), 'Naissance inconnue.')):
        with pytest.raises(AssertionError): _chef_bar(_alterer_personnages(chef, chemin, valeur))
    with pytest.raises(AssertionError): _chef_bar(_alterer_personnages(next(f for f in monde.personnages if f['id'] == CHEF_BAR), ('nom',), 'Robert II de Bar'))
    modele = next(f for f in d['familles'] if f['id'] == 'personne-edouard-bar')
    def relie(c, i, j):
        a, b = (next(f for f in c['familles'] + c['liens'] if f['id'] == k) for k in (i, j))
        a['conjoints'].append(j); b['conjoints'].append(i)
    # « Marie de Valois » rebaptisée Marie de France ; une seconde Marie de France, de `seigneurie-1`, conjointe réciproque de Robert.
    k = next(k for k, f in enumerate(d['familles']) if f['id'] == EPOUSE_BAR)
    altere(('familles', k, 'nom'), 'Marie de France')
    c = copy.deepcopy(d); c['familles'].append(dict(copy.deepcopy(modele), id='personne-marie-intruse', nom='Marie de France', pere=None, mere=None, conjoints=[]))
    relie(c, 'personne-marie-intruse', CHEF_BAR); refuse(c, controle=True, bar=True)
    # Jeanne et Théodore II Paléologue (`grande-15`) ; Yolande de Bar et `grande-6` ; Yolande la Jeune et un conjoint actif.
    c = copy.deepcopy(d); relie(c, 'personne-jeanne-bar', THEODORE_II_ID); refuse(c, controle=True, bar=True)
    c = copy.deepcopy(d); relie(c, 'personne-yolande-bar', 'personne-grande-6'); refuse(c, controle=True, bar=True)
    c = copy.deepcopy(d); c['familles'].append(dict(copy.deepcopy(modele), id='personne-adolphe-juliers', nom='Adolphe de Juliers', conjoints=[], pere=None, mere=None))
    relie(c, YOLANDE_JEUNE_BAR, 'personne-adolphe-juliers'); refuse(c, controle=True, bar=True)
    # Les naissances que le lot refuse de redevenir imprécises, et un état de plus.
    for i, naissance in (('yolande-bar', _naissance_famille('1365', 'annee')), ('louis-bar', _naissance_famille('1370', 'annee')), ('edouard-bar', _naissance_famille('1377', 'annee'))):
        k = next(k for k, f in enumerate(d['familles']) if f['id'] == 'personne-' + i)
        altere(('familles', k, 'naissance'), naissance)
    c = copy.deepcopy(d); c['etats'].append(dict(copy.deepcopy(next(e for e in d['etats'] if e['maison'] == BAR)), maison='seigneurie-2')); refuse(c)
    c = copy.deepcopy(d); c['etats'] = [e for e in c['etats'] if e['maison'] != BAR]; refuse(c)
    # Des copies d'Édouard : enfants morts avant 1400 ou de présence indéterminée, époux futur, héritier inventé.
    base = next(f for f in monde.personnages if f['id'] == 'personne-edouard-bar')
    intrus = [(nom, 'decedee', 'enfant') for nom in ('Henri de Bar', 'Charles de Bar')]
    intrus += [(nom, presence, 'enfant') for nom in ('Philippe de Bar', 'Marie de Bar', 'Bonne de Bar') for presence in ('vivante', 'decedee')]
    intrus += [('Adolphe de Juliers', 'vivante', 'conjoint'), ('Héritier inventé', 'vivante', 'enfant')]
    for nom, presence, role in intrus:
        c = copy.deepcopy(d); ajout = dict(copy.deepcopy(modele), id='personne-intruse', nom=nom, presence=presence, pere=None, mere=None, conjoints=[]); c['familles'].append(ajout)
        if role == 'enfant': ajout['pere'], ajout['mere'] = CHEF_BAR, EPOUSE_BAR
        else: ajout['conjoints'] = [YOLANDE_JEUNE_BAR]; next(x for x in c['familles'] if x['id'] == YOLANDE_JEUNE_BAR)['conjoints'].append(ajout['id'])
        refuse(c, controle=True, bar=True)
        clone = {k: copy.deepcopy(v) for k, v in base.items()}
        clone.update(id='personne-intruse', nom=nom, presence=presence, pere=None, mere=None, conjoints=[])
        personnes = [copy.deepcopy(f) for f in monde.personnages]
        if role == 'enfant': clone.update(pere=CHEF_BAR, mere=EPOUSE_BAR)
        else: clone['conjoints'] = [YOLANDE_JEUNE_BAR]; next(f for f in personnes if f['id'] == YOLANDE_JEUNE_BAR)['conjoints'].append(clone['id'])
        with pytest.raises(AssertionError): _bar({f['id']: f for f in personnes + [clone]})
        with pytest.raises(AssertionError): _preuve_monde_bar(personnes + [clone])
