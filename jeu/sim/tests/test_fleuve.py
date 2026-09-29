"""Preuves de la vue dérivée du cours du Nil par cellule."""

import copy
import dataclasses
import json
import pathlib

import pytest

import sim.fleuve as module_fleuve
from sim.aggregation import (
    PositionCelluleInconnue,
    charger_positions,
    derive_appartenance,
    facteur_de_projection,
    projeter,
)
from sim.fleuve import (
    CoursDuNilInvalide,
    PointDuCours,
    cellules_traversees,
    charger_latitude_moyenne_fleuve,
    charger_points,
    cours_depuis_monde,
)
from sim.world import World


_RACINE_DEPOT = pathlib.Path(__file__).parent.parent.parent
_CHEMIN_COURS = _RACINE_DEPOT / "data" / "nil-cours-1400.json"


def _ecrire(tmp_path, document, nom):
    chemin = tmp_path / nom
    chemin.write_text(json.dumps(document), encoding="utf-8")
    return chemin


def _cellule_la_plus_proche(point, positions, latitude_moyenne):
    class Centroide:
        def __init__(self, cell_id, position):
            self.id = cell_id
            self.lat, self.lon = position

    centroides = [Centroide(cell_id, position) for cell_id, position in positions.items()]
    return derive_appartenance({1: point}, centroides, latitude_moyenne)[1]


def test_table_se_lit_et_refuse_les_donnees_invalides(tmp_path):
    """SC1 : chaque ligne est exploitable, sourcée et explicitement limitée."""
    document = json.loads(_CHEMIN_COURS.read_text(encoding="utf-8"))
    points = charger_points()
    assert points
    sources_non_vides = sum(bool(point.source.strip()) for point in points)
    assert 8 <= len(points) <= 14
    assert sources_non_vides == len(points)
    assert document["cours_de_1400"].strip()
    assert document["hors_carte"].strip()

    alterations = []
    for champ, valeur in (
        ("source", None), ("source", "   "), ("lat", "30"),
        ("lon", True), ("lat", float("nan")), ("nom", " "),
        ("id", True),
    ):
        altere = copy.deepcopy(document)
        point_id = altere["points"][0]["id"]
        if valeur is None:
            del altere["points"][0][champ]
        else:
            altere["points"][0][champ] = valeur
        if champ == "id":
            point_id = valeur
        alterations.append((altere, point_id, champ))
    altere = copy.deepcopy(document)
    altere["points"][1]["id"] = altere["points"][0]["id"]
    alterations.append((altere, altere["points"][0]["id"], "id"))
    for champ in ("points", "hors_carte", "cours_de_1400"):
        altere = copy.deepcopy(document)
        if champ == "points":
            altere[champ] = []
        else:
            del altere[champ]
        alterations.append((altere, None, champ))

    refus = 0
    for index, (altere, point_id, champ) in enumerate(alterations):
        with pytest.raises(CoursDuNilInvalide) as capture:
            charger_points(_ecrire(tmp_path, altere, f"invalide-{index}.json"))
        assert champ in str(capture.value)
        if point_id is not None:
            assert str(point_id) in str(capture.value)
        refus += 1

    print(f"points_lus = {len(points)}")
    print(f"sources_non_vides = {sources_non_vides} / {len(points)}")
    print(f"refus_observes = {refus} / {len(alterations)}")
    assert refus == len(alterations)


def test_geographie_du_delta_sans_desert_ni_suez():
    """SC2 : le cours touche le delta, mais ni le désert ni l'isthme."""
    monde = World.charger(0)
    positions = charger_positions()
    latitude_moyenne = charger_latitude_moyenne_fleuve()
    points = charger_points()
    assert points and positions
    references = tuple(
        _cellule_la_plus_proche(point, positions, latitude_moyenne)
        for point in ((30.8, 31.0), (30.9, 28.5), (30.45, 32.5))
    )
    delta, desert, suez = references
    traversees = {vue.cell_id for vue in cours_depuis_monde(monde)}
    fautifs = [dataclasses.replace(point, lon=-point.lon) for point in points]
    traversees_fautives = {
        vue.cell_id
        for vue in cours_depuis_monde(monde, points=fautifs)
    }

    print(f"cellules_de_reference_distinctes = {len(set(references))}")
    print(f"delta_traverse = {delta in traversees}")
    print(f"delta_traverse_longitudes_inversees = {delta in traversees_fautives}")
    assert len(set(references)) == len(references)
    assert delta in traversees
    assert desert not in traversees
    assert suez not in traversees
    assert delta not in traversees_fautives


def test_couverture_de_tous_les_points_et_vallee_hors_carte():
    """SC3 : chaque point sert et le point exclu expliquerait un faux Suez."""
    monde = World.charger(0)
    positions = charger_positions()
    points = charger_points()
    latitude_moyenne = charger_latitude_moyenne_fleuve()
    assert points and positions
    traversees = cours_depuis_monde(monde)
    ids_rendus = {
        point_id for cellule in traversees for point_id in cellule.point_ids
    }
    suez = _cellule_la_plus_proche((30.45, 32.5), positions, latitude_moyenne)
    beni_suef = PointDuCours(
        max(point.id for point in points) + 1,
        "Beni Suef", 29.07, 31.10, "contre-épreuve déclarée par le brief",
    )
    avec_vallee = {
        cellule.cell_id
        for cellule in cours_depuis_monde(monde, points=[*points, beni_suef])
    }

    print(f"points_rendus = {sum(len(c.point_ids) for c in traversees)} / {len(points)}")
    print(f"cellules_vides_rendues = {sum(not c.point_ids for c in traversees)}")
    print(f"suez_traversee_avec_vallee = {suez in avec_vallee}")
    assert sum(len(c.point_ids) for c in traversees) == len(points)
    assert ids_rendus == {point.id for point in points}
    assert all(cellule.point_ids for cellule in traversees)
    assert suez in avec_vallee


def test_egalite_departagee_par_le_plus_petit_cell_id():
    """SC4 : l'égalité exacte est indépendante de l'ordre des positions."""
    point = PointDuCours(1, "Milieu", 0.0, 0.0, "point synthétique")
    latitude_moyenne = charger_latitude_moyenne_fleuve()
    positions = {3: (0.0, -1.0), 7: (0.0, 1.0)}
    facteur = facteur_de_projection(latitude_moyenne)
    cible = projeter(point.lat, point.lon, facteur)
    carres = tuple(
        sum((a - b) ** 2 for a, b in zip(cible, projeter(*position, facteur)))
        for position in positions.values()
    )
    ordres = (positions, dict(reversed(tuple(positions.items()))))
    gagnants = tuple(
        cellules_traversees([point], ordre, latitude_moyenne)[0].cell_id
        for ordre in ordres
    )

    print(f"carres_exactement_egaux = {carres[0] == carres[1]}")
    print(f"cellules_gagnantes = {gagnants}")
    assert carres[0] == carres[1]
    assert gagnants == (3, 3)


def test_vue_pure_refuse_les_entrees_absentes():
    """SC5 : la vue ne modifie rien et refuse toute position manquante."""
    monde = World.charger(0)
    avant = json.dumps(monde.to_dict(), sort_keys=True)
    premiere = cours_depuis_monde(monde)
    seconde = cours_depuis_monde(monde)
    apres = json.dumps(monde.to_dict(), sort_keys=True)
    points = charger_points()
    positions = charger_positions()
    plus_petite = min(monde.cells)
    del positions[plus_petite]
    with pytest.raises(PositionCelluleInconnue) as capture:
        cours_depuis_monde(monde, positions=positions)
    with pytest.raises(CoursDuNilInvalide):
        cellules_traversees([], {1: (0.0, 0.0)}, 0.0)
    with pytest.raises(CoursDuNilInvalide):
        cellules_traversees(points, {}, 0.0)

    print(f"vues_identiques = {premiere == seconde}")
    print(f"monde_inchange = {avant == apres}")
    cellule_absente_nommee = str(plus_petite) in str(capture.value)
    print(f"cellule_absente_nommee = {cellule_absente_nommee}")
    assert premiere
    assert premiere == seconde
    assert avant == apres
    assert str(plus_petite) in str(capture.value)
