"""Preuves de la vue dérivée de pluie annuelle par cellule."""

import ast
import copy
import dataclasses
import json
import pathlib
import statistics

import pytest

import sim.pluie as module_pluie
from sim.aggregation import (
    PositionCelluleInconnue,
    charger_positions,
    facteur_de_projection,
    projeter,
)
from sim.pluie import (
    ReleveDePluie,
    ReleveDePluieInvalide,
    charger_latitude_moyenne_pluie,
    charger_releves,
    pluie_de_cellule,
    pluie_depuis_monde,
    pluie_par_cellule,
    releves_sans_cellule,
)
from sim.world import World


_RACINE_DEPOT = pathlib.Path(__file__).parent.parent.parent
_CHEMIN_RELEVES = _RACINE_DEPOT / "data" / "pluie-releves-1400.json"
_SIM = pathlib.Path(module_pluie.__file__).parent
_NOMS_PUBLICS = {
    "charger_releves",
    "charger_latitude_moyenne_pluie",
    "pluie_par_cellule",
    "pluie_depuis_monde",
    "pluie_de_cellule",
    "releves_sans_cellule",
}


def _ecrire_document(tmp_path, document, nom):
    chemin = tmp_path / nom
    chemin.write_text(json.dumps(document), encoding="utf-8")
    return chemin


def test_table_se_lit_et_refuse_les_donnees_invalides(tmp_path):
    """SC1 : source, déclaration, unité et nombres sont tous explicites."""
    document = json.loads(_CHEMIN_RELEVES.read_text(encoding="utf-8"))
    releves = charger_releves()
    releves_lus = len(releves)
    sources_non_vides = sum(bool(releve.source.strip()) for releve in releves)

    assert 35 <= releves_lus <= 45
    assert sources_non_vides == releves_lus
    assert document["climat_de_1400"].strip()
    assert document["unite"] == "mm/an"

    alterations = []
    for champ, valeur in (
        ("source", None),
        ("source", "   "),
        ("mm_par_an", -1),
        ("mm_par_an", "100"),
        ("mm_par_an", True),
        ("mm_par_an", float("nan")),
    ):
        altere = copy.deepcopy(document)
        if valeur is None:
            del altere["releves"][0][champ]
        else:
            altere["releves"][0][champ] = valeur
        alterations.append((altere, 1, champ))

    altere = copy.deepcopy(document)
    altere["releves"][1]["id"] = altere["releves"][0]["id"]
    alterations.append((altere, altere["releves"][0]["id"], "id"))

    altere = copy.deepcopy(document)
    altere["releves"] = []
    alterations.append((altere, None, "releves"))
    altere = copy.deepcopy(document)
    del altere["climat_de_1400"]
    alterations.append((altere, None, "climat_de_1400"))
    altere = copy.deepcopy(document)
    altere["unite"] = "cm/an"
    alterations.append((altere, None, "unite"))

    refus_observes = 0
    for index, (altere, releve_id, champ) in enumerate(alterations):
        chemin = _ecrire_document(tmp_path, altere, f"invalide-{index}.json")
        with pytest.raises(ReleveDePluieInvalide) as capture:
            charger_releves(chemin)
        message = str(capture.value)
        assert champ in message
        if releve_id is not None:
            assert str(releve_id) in message
        refus_observes += 1

    avec_zero = copy.deepcopy(document)
    avec_zero["releves"][0]["mm_par_an"] = 0
    zero_accepte = charger_releves(
        _ecrire_document(tmp_path, avec_zero, "zero.json")
    )[0].mm_par_an

    print(f"releves_lus = {releves_lus}")
    print(f"sources_non_vides = {sources_non_vides} / {releves_lus}")
    print(f"refus_observes = {refus_observes} / {len(alterations)}")
    print(f"zero_accepte = {zero_accepte}")
    assert refus_observes == len(alterations)
    assert zero_accepte == 0


def test_couverture_de_toutes_les_cellules_et_utilite_des_releves():
    """SC2 : toute cellule reçoit une pluie et tout relevé sert."""
    monde = World.charger(0)
    positions = charger_positions()
    releves = charger_releves()
    latitude_moyenne = charger_latitude_moyenne_pluie()
    pluies = pluie_depuis_monde(
        monde,
        positions=positions,
        releves=releves,
        latitude_moyenne=latitude_moyenne,
    )
    cellules_avec_pluie = len(pluies)
    cellules_sans_pluie = len(monde.cells) - cellules_avec_pluie
    relevés_morts = releves_sans_cellule(pluies, releves)

    premier = releves[0]
    parasite = dataclasses.replace(
        premier,
        id=max(releve.id for releve in releves) + 1,
        lat=premier.lon,
        lon=premier.lat,
    )
    pluies_avec_parasite = pluie_par_cellule(
        positions, [*releves, parasite], latitude_moyenne
    )
    morts_avec_parasite = releves_sans_cellule(
        pluies_avec_parasite, [*releves, parasite]
    )

    plus_petite_cellule = min(monde.cells)
    positions_amputees = dict(positions)
    del positions_amputees[plus_petite_cellule]
    with pytest.raises(PositionCelluleInconnue) as capture:
        pluie_depuis_monde(monde, positions=positions_amputees)

    print(f"cellules_avec_pluie = {cellules_avec_pluie} / {len(monde.cells)}")
    print(f"cellules_sans_pluie = {cellules_sans_pluie}")
    print(f"releves_sans_cellule = {len(relevés_morts)}")
    print(f"releves_sans_cellule_contre_epreuve = {len(morts_avec_parasite)}")
    assert cellules_avec_pluie == len(monde.cells)
    assert cellules_sans_pluie == 0
    assert len(relevés_morts) == 0
    assert morts_avec_parasite == (parasite.id,)
    assert str(plus_petite_cellule) in str(capture.value)


def test_egalite_departagee_par_le_plus_petit_identifiant():
    """SC3 : une égalité exacte ne dépend pas de l'ordre des relevés."""
    latitude_moyenne = charger_latitude_moyenne_pluie()
    facteur = facteur_de_projection(latitude_moyenne)
    positions = {1: (0.0, 0.0)}
    petit = ReleveDePluie(3, "Ouest", 0.0, -1.0, 10, "source A")
    grand = ReleveDePluie(7, "Est", 0.0, 1.0, 20, "source B")
    cellule = projeter(*positions[1], facteur)
    point_petit = projeter(petit.lat, petit.lon, facteur)
    point_grand = projeter(grand.lat, grand.lon, facteur)
    carre_petit = sum((a - b) ** 2 for a, b in zip(cellule, point_petit))
    carre_grand = sum((a - b) ** 2 for a, b in zip(cellule, point_grand))

    dans_ordre = pluie_par_cellule(positions, [petit, grand], latitude_moyenne)
    ordre_inverse = pluie_par_cellule(positions, [grand, petit], latitude_moyenne)
    identifiants_gagnants = (dans_ordre[0].releve_id, ordre_inverse[0].releve_id)

    print(f"carres_exactement_egaux = {carre_petit == carre_grand}")
    print(f"identifiants_gagnants = {identifiants_gagnants}")
    assert carre_petit == carre_grand
    assert identifiants_gagnants == (petit.id, petit.id)


def _cellule_la_plus_proche(point, positions, facteur):
    cible = projeter(*point, facteur)
    return min(
        positions,
        key=lambda cell_id: sum(
            (a - b) ** 2
            for a, b in zip(projeter(*positions[cell_id], facteur), cible)
        ),
    )


def _contraste_geographique(pluies, cellules_seches, cellules_mouillees):
    mediane = statistics.median(pluie.mm_par_an for pluie in pluies)
    seches = [pluie_de_cellule(cell_id, pluies) for cell_id in cellules_seches]
    mouillees = [
        pluie_de_cellule(cell_id, pluies) for cell_id in cellules_mouillees
    ]
    return max(seches) < mediane < min(mouillees), mediane, seches, mouillees


def test_geographie_du_desert_sec_et_de_atlantique_mouille():
    """SC4 : quatre points indépendants prouvent le contraste attendu."""
    positions = charger_positions()
    releves = charger_releves()
    latitude_moyenne = charger_latitude_moyenne_pluie()
    facteur = facteur_de_projection(latitude_moyenne)
    points_secs = ((30.9, 28.5), (30.45, 32.5))
    points_mouilles = ((60.39, 5.32), (53.27, -9.05))
    cellules_seches = tuple(
        _cellule_la_plus_proche(point, positions, facteur) for point in points_secs
    )
    cellules_mouillees = tuple(
        _cellule_la_plus_proche(point, positions, facteur)
        for point in points_mouilles
    )
    pluies = pluie_par_cellule(positions, releves, latitude_moyenne)
    contraste, mediane, seches, mouillees = _contraste_geographique(
        pluies, cellules_seches, cellules_mouillees
    )

    par_rang = sorted(releves, key=lambda releve: (releve.mm_par_an, releve.id))
    valeurs_inversees = [releve.mm_par_an for releve in reversed(par_rang)]
    inverses = [
        dataclasses.replace(releve, mm_par_an=valeur)
        for releve, valeur in zip(par_rang, valeurs_inversees)
    ]
    contre_vue = pluie_par_cellule(positions, inverses, latitude_moyenne)
    contre_contraste, _, _, _ = _contraste_geographique(
        contre_vue, cellules_seches, cellules_mouillees
    )

    print(f"mediane_des_pluies_du_monde = {mediane}")
    print(f"pluies_cellules_seches = {seches}")
    print(f"pluies_cellules_mouillees = {mouillees}")
    print(f"contre_epreuve_inverse_reussit = {contre_contraste}")
    assert contraste
    assert not contre_contraste


def _usages_interdits(source):
    arbre = ast.parse(source)
    usages = []
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.ImportFrom) and noeud.module == "sim.pluie":
            usages.append(noeud.lineno)
        elif isinstance(noeud, ast.Import):
            if any(alias.name == "sim.pluie" for alias in noeud.names):
                usages.append(noeud.lineno)
        elif isinstance(noeud, (ast.Name, ast.Attribute)):
            nom = noeud.id if isinstance(noeud, ast.Name) else noeud.attr
            if nom in _NOMS_PUBLICS:
                usages.append(noeud.lineno)
    return usages


def test_pure_et_non_lue_par_le_tick():
    """SC5 : la consultation est stable, pure et isolée du moteur."""
    monde = World.charger(0)
    avant = json.dumps(monde.to_dict(), sort_keys=True)
    premiere = pluie_depuis_monde(monde)
    seconde = pluie_depuis_monde(monde)
    apres = json.dumps(monde.to_dict(), sort_keys=True)

    modules_parcourus = 0
    usages_interdits = []
    for chemin in sorted(_SIM.glob("*.py")):
        if chemin == pathlib.Path(module_pluie.__file__):
            continue
        modules_parcourus += 1
        usages_interdits.extend(
            (chemin.name, ligne)
            for ligne in _usages_interdits(chemin.read_text(encoding="utf-8"))
        )
    contre_epreuve = _usages_interdits(
        "from sim.pluie import pluie_depuis_monde"
    )

    print(f"cellules_comparees = {len(premiere)}")
    print(f"modules_parcourus = {modules_parcourus}")
    print(f"lecteurs_de_la_vue = {usages_interdits}")
    print(f"contre_epreuve_detectee = {bool(contre_epreuve)}")
    assert premiere == seconde
    assert avant == apres
    assert modules_parcourus > 0
    assert {nom for nom, _ in usages_interdits} == {"world.py"}
    assert contre_epreuve
