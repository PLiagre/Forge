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
    for identifiant in ('grande-21', 'grande-24', 'institution-12', 'institution-15', 'institution-31', 'institution-32', 'seigneurie-6'):
        assert fiches[identifiant]['nom'] is None and fiches[identifiant]['lacunes']['identite'].strip()
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
    alterations.append(_alterer_personnages(document, ('chefs', indices['seigneurie-6'], 'lacunes', 'identite'), ''))
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
                           (('chefs', 'seigneurie-6', 'lacune'), ''),
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
        for f in (f for f in d['personnages'] if f['maison'] in ('grande-1', 'grande-2', 'grande-4', 'grande-5', 'grande-6', 'grande-7', 'grande-8', 'grande-10')): alterer(f)
    assert document['personnages'] == list(monde.personnages)
    altere = copy.deepcopy(document); alterer_iles(altere)
    copie = copy.copy(monde); copie.personnages = tuple(altere['personnages'])
    assert _octets_registre(copie.to_dict()) == _octets_registre(altere) != original
    for chemin, valeur in (*[(('personnages', boheme, *k), 'Altéré') for k in chemins], (('personnages', famille, 'mere'), 'autre'), (('personnages', famille, 'conjoints'), []),
                           (('personnages', famille, 'sources', 'presence', 'fait'), 'Altéré'), (('personnages',), []), (('chefs',), {}), (('personnages', 0, 'nom'), 'Altéré'),
                           (('personnages', 0, 'naissance', 'valeur'), 'inconnue'),
                           (('personnages', 0, 'sources', 'identite', 'fait'), 'Altéré'), (('chefs', 'seigneurie-6', 'lacune'), 'Altérée')):
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
    document['chefs']['seigneurie-6']['lacune'] = 'Altérée'
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
    assert len(familles) == len(famille) + len(ILES_1400) + len(IBERIE_1400) + len(FIN_1400) == 54
    assert {f['id'] for f in familles} == {'personne-' + i for i, *_ in famille + ILES_1400 + IBERIE_1400 + FIN_1400}
    fiches = {f['id']: f for f in familles + liens}
    couples = {'personne-isabeau': 'personne-grande-3', 'personne-jeanne': 'personne-grande-28', 'personne-sophie-baviere': 'personne-grande-9'}
    couples.update({v: k for k, v in list(couples.items())})
    for i, nom, date, precision in famille:
        f = fiches['personne-' + i]
        assert (f['nom'], f['maison'], f['naissance']) == (nom, 'grande-9' if i == 'sophie-baviere' else 'grande-3', {'valeur': date, 'precision': precision})
        assert (f['pere'], f['mere']) == ((None, None) if i in ('isabeau', 'sophie-baviere') else ('personne-grande-3', 'personne-isabeau'))
    assert len(liens) == 11 and {f['id'] for f in liens} == {'personne-grande-' + i for i in ('1', '2', '3', '28', '9', '4', '5', '6', '7', '8', '10')}
    _iles_historiques(fiches)
    _iberie_historiques(fiches)
    _fin_historiques(fiches)
    for i, f in fiches.items():
        if i in {'personne-' + r[0] for r in ILES_1400 + IBERIE_1400 + FIN_1400} | {'personne-grande-' + i for i in ('1', '2', '4', '5', '6', '7', '8', '10')}: continue
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
    mutations += [(('familles',), [f for f in document['familles'] if f['id'] != 'personne-' + i]) for i, *_ in FAMILLE_1400 + [('sophie-baviere',)] + ILES_1400 + IBERIE_1400 + FIN_1400]
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
    assert len(bilan['verifies']) == 35 and len(bilan['indetermines']) == 81
    parents = [('grande-3', 'isabeau', i) for i, *_ in FAMILLE_1400[1:]] + [('grande-1', 'marie-bohun', i) for i, *_ in ILES_1400[1:7]] + [('grande-2', 'annabella', i) for i, *_ in ILES_1400[8:13]] + [('grande-2', None, 'jean-ardgowan')]
    verifies = {('anteriorite', ('personne-grande-3', 'personne-' + i)) for i, *_ in FAMILLE_1400[1:]}
    parents += [('grande-' + m, mere, i) for i, _, _, _, _, _, m, mere in IBERIE_1400 if mere]
    verifies |= {('anteriorite', ('personne-grande-4', 'personne-' + i)) for i in ('afonso-portugal', 'edouard-portugal', 'pierre-portugal', 'henri-portugal', 'isabelle-portugal', 'afonso-bragance')} | {(k, ('personne-philippa-lancastre', 'personne-' + i)) for i in ('afonso-portugal', 'edouard-portugal', 'pierre-portugal', 'henri-portugal', 'isabelle-portugal') for k in ('anteriorite', 'age_maternel')}
    parents += [('grande-' + m, mere, i) for i, _, _, _, _, _, m, mere in FIN_1400 if i in FIN_ENFANTS]
    verifies |= {('anteriorite', ('personne-grande-' + m, 'personne-' + i)) for i, m in [('jeanne-foix', '7'), ('charles-navarre', '7'), ('lancelot-navarre', '7'), ('valentine-visconti', '10'), ('gian-maria', '10'), ('filippo-maria', '10')]} | {(k, ('personne-' + m, 'personne-' + i)) for m, i in [('isabelle-vertus', 'valentine-visconti'), ('caterina-visconti', 'gian-maria'), ('caterina-visconti', 'filippo-maria')] for k in ('anteriorite', 'age_maternel')}
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
                 (('liens', r['personne-grande-28'], 'conjoints'), []), (('familles', enfant, 'naissance'), _naissance_famille('1368-12-03')),
                 (('familles', enfant, 'naissance'), _naissance_famille('1368-12-02'))]
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
    assert len(etats) == 11 and {e['maison'] for e in etats} == {'grande-' + i for i in ('1', '2', '3', '28', '9', '4', '5', '6', '7', '8', '10')}
    for e in etats:
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
    for k in ('pere', 'mere', 'conjoints'):
        personnes = copy.deepcopy(list(monde.personnages))
        next(f for f in personnes if f['id'] == 'personne-grande-11')[k] = 'personne-grande-9'
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
    mutations += [(('etats', r['grande-28'], k), v) for k, v in [('maison', 'inconnue'), ('maison', 'seigneurie-6'), ('conjoints', 'celibat'), ('enfants', 'inconnus'), ('enfants', 'documentes'), ('conjoints', 'veuvage')]]
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
