"""Preuves des maisons tenantes, avec leurs contre-épreuves."""
import ast
import copy
import dataclasses
import json
import pathlib
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
    charge = World.charger(0)
    assert charge.maisons == attendu and isinstance(charge.maisons, tuple)
    assert appels == [charge.carte]
    for maison in charge.maisons:
        with pytest.raises(dataclasses.FrozenInstanceError):
            maison.nom = "Altérée"
    assert World({}, []).maisons == ()
    charge.to_dict()
    maisons_depuis_monde(charge)
    maisons_de_l_ia(charge)
    assert appels == [charge.carte]
    retraits = [next(m for m in attendu if m.sorte == sorte) for sorte in categories]
    retraits += [m for m in attendu if m.nom in homonymes]
    faux = [tuple(m for m in attendu if m.id != retiree.id) for retiree in retraits]
    faux += [(), (dataclasses.replace(attendu[0], nom="Altérée"),) + attendu[1:]]
    for resultat in faux:
        monkeypatch.setattr(etat_monde, "charger_registre_maisons", lambda carte: resultat)
        with pytest.raises(AssertionError):
            assert World.charger(0).maisons == attendu
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
    assert set(monde.to_dict()) == {"cells", "plans", "ticks_ecoules", "maisons"}
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


def _importe_maitres(texte):
    return any((isinstance(n, ast.ImportFrom) and
                (n.module == "sim.maitres" or n.module == "sim" and any(a.name == "maitres" for a in n.names)))
               or (isinstance(n, ast.Import) and any(a.name == "sim.maitres" for a in n.names))
               for n in ast.walk(ast.parse(texte)))


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
        assert not _importe_maitres((TABLE.parents[1] / "sim" / fichier).read_text())
    assert _importe_maitres("from sim.maitres import attribuer_maitres")
