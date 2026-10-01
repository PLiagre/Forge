"""Preuves des terres de départ et contre-épreuves sans altérer le monde de référence."""
import copy
import dataclasses
import json
from pathlib import Path

import pytest

from sim import constants as constantes
from sim.aggregation import charger_positions
from sim.engine import population_soutenable_de
from sim.maisons import charger_maisons
from sim.model import _NoBadSpatialField
from sim.puissances import (
    RELIGIONS, PuissanceInvalide, charger_latitude_moyenne_puissances,
    charger_table, puissances_depuis_monde,
)
from sim.seigneuries import (
    SeigneurieInconnue, cellule_du_siege, charger_seigneuries, fiche_de_seigneurie,
)
from sim.tests.test_puissances import _cellule_la_plus_proche
from sim.world import World

TABLE = Path(__file__).parents[2] / "data" / "seigneuries-1400.json"
SUZERAINS = {
    "Duché de Bar": "France", "Comté de Wurtemberg": "Saint-Empire",
    "Despotat de Morée": "Byzance", "Terre des Branković": "Ottomans",
    "Uç d'Evrenos": "Ottomans",
}
MAISONS = {"France": "Valois", "Saint-Empire": "Luxembourg",
           "Byzance": "Paléologue", "Ottomans": "Osman"}


def _ecrire(tmp_path, document):
    chemin = tmp_path / "seigneuries.json"
    chemin.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    return chemin


def religions_manquantes(seigneuries):
    return RELIGIONS - {s.religion for s in seigneuries}


def _preuve_lecture(seigneuries):
    assert len(seigneuries) == len(SUZERAINS) > 0
    assert len({s.nom for s in seigneuries}) == len(seigneuries)
    assert not religions_manquantes(seigneuries)


def test_lecture(tmp_path):
    document = json.loads(TABLE.read_text(encoding="utf-8"))
    next(s for s in document["seigneuries"] if s["nom"] == "Uç d'Evrenos")["religion"] = "catholique"
    alterees = charger_seigneuries(_ecrire(tmp_path, document))
    assert religions_manquantes(alterees) == {"musulmane"}
    with pytest.raises(AssertionError):
        _preuve_lecture(alterees)
    seigneuries = charger_seigneuries()
    _preuve_lecture(seigneuries)
    assert tuple(s.id for s in seigneuries) == tuple(sorted(s.id for s in seigneuries))
    print(f"seigneuries_lues={len(seigneuries)}, religions_manquantes={religions_manquantes(seigneuries)}, contre_épreuve_rouge=1")


CAS_REFUS = [
    ("liste_vide", "seigneuries"), ("liste_absente", "seigneuries"),
    ("id_duplique", "id"), ("id_booleen", "id"), ("nom_duplique", "nom"),
    ("nom_vide", "nom"), ("religion", "religion"), ("suzerain", "suzerain"),
    ("suzerain_booleen", "suzerain"), ("source", "source"), ("maison", "maison"),
    ("nom_siege", "siege.nom"), ("date", "date"), ("projection", "projection"),
] + [(f"coord_{champ}", f"siege.{champ}") for champ in ("lat", "lon", "x_m", "y_m")]


@pytest.mark.parametrize("cas,champ", CAS_REFUS)
def test_refus(tmp_path, cas, champ):
    document = json.loads(TABLE.read_text(encoding="utf-8"))
    ligne = next(s for s in document["seigneuries"] if s["nom"] == "Duché de Bar")
    autre = next(s for s in document["seigneuries"] if s["nom"] == "Comté de Wurtemberg")
    identifiant = ligne["id"]
    if cas == "liste_vide": document["seigneuries"] = []
    elif cas == "liste_absente": document.pop("seigneuries")
    elif cas == "id_duplique": ligne["id"] = identifiant = autre["id"]
    elif cas == "id_booleen": ligne["id"] = identifiant = True
    elif cas == "nom_duplique":
        autre["nom"] = ligne["nom"]
        identifiant = autre["id"]
    elif cas == "nom_vide": ligne["nom"] = " "
    elif cas == "religion": ligne["religion"] = "arienne"
    elif cas == "suzerain": ligne["suzerain"] = max(p.id for p in charger_table().puissances) + 1
    elif cas == "suzerain_booleen": ligne["suzerain"] = True
    elif cas == "source": ligne["source"] = " "
    elif cas == "maison": ligne.pop("maison")
    elif cas == "nom_siege": ligne["siege"]["nom"] = " "
    elif cas == "date": document["date"] = "1453-05-29"
    elif cas == "projection": document["projection"] = "EPSG:4326"
    else: ligne["siege"][champ.split(".")[-1]] = float("nan")
    with pytest.raises(PuissanceInvalide) as erreur:
        charger_seigneuries(_ecrire(tmp_path, document))
    message = str(erreur.value)
    assert "seigneurie" in message and f"champ {champ}" in message
    if champ not in {"seigneuries", "date", "projection"}:
        assert str(identifiant) in message
    assert charger_seigneuries()
    print(f"cas={cas}, refus_observés=1/1, cas_prévus={len(CAS_REFUS)}")


@pytest.fixture
def contexte():
    return World.charger(0), charger_seigneuries(), charger_table(), charger_maisons()


def test_refus_hors_carte(contexte):
    monde, seigneuries, _, _ = contexte
    bar = next(s for s in seigneuries if s.nom == "Duché de Bar")
    hors = dataclasses.replace(bar, siege=dataclasses.replace(bar.siege, x_m=0, y_m=0))
    with pytest.raises(PuissanceInvalide, match=f"seigneurie {bar.id}, champ siege : hors carte"):
        cellule_du_siege(hors, monde.carte)
    assert cellule_du_siege(bar, monde.carte) in monde.cells
    print("sièges_hors_carte_refusés=1, sièges_valides_acceptés=1")


def _preuve_sieges(monde, seigneuries, table):
    positions, latitude = charger_positions(), charger_latitude_moyenne_puissances()
    vue = puissances_depuis_monde(monde, table=table)
    cellules = [cellule_du_siege(s, monde.carte) for s in seigneuries]
    hors_suzerain = sum(vue[cid] != s.suzerain for s, cid in zip(seigneuries, cellules))
    desaccords = sum(cid != _cellule_la_plus_proche((s.siege.lat, s.siege.lon), positions, latitude)
                    for s, cid in zip(seigneuries, cellules))
    print(f"sièges_vus={len(cellules)}, sièges_distincts={len(set(cellules))}, hors_suzerain={hors_suzerain}, désaccords_point={desaccords}")
    assert len(cellules) == len(SUZERAINS) > 0
    assert hors_suzerain == 0 and desaccords == 0
    assert len(set(cellules)) == len(cellules)


def test_sieges(contexte):
    monde, seigneuries, table, _ = contexte
    bar = next(s for s in seigneuries if s.nom == "Duché de Bar")
    wurtemberg = next(s for s in seigneuries if s.nom == "Comté de Wurtemberg")
    empire = next(p for p in table.puissances if p.nom == "Saint-Empire")
    for mauvais in (dataclasses.replace(bar, suzerain=empire.id),
                    dataclasses.replace(bar, siege=dataclasses.replace(
                        bar.siege, x_m=wurtemberg.siege.x_m, y_m=wurtemberg.siege.y_m))):
        with pytest.raises(AssertionError):
            _preuve_sieges(monde, tuple(mauvais if s == bar else s for s in seigneuries), table)
    _preuve_sieges(monde, seigneuries, table)
    puissances = {p.id: p.nom for p in table.puissances}
    assert {s.nom: puissances[s.suzerain] for s in seigneuries} == SUZERAINS


def test_fiche(contexte):
    monde, seigneuries, table, maisons = contexte
    vue = puissances_depuis_monde(monde, table=table)
    puissances, tenantes = {p.id: p for p in table.puissances}, {m.id: m for m in maisons.maisons}
    fiches = {}
    for s in seigneuries:
        fiche = fiche_de_seigneurie(s.id, monde, seigneuries, table, maisons)
        cid = cellule_du_siege(s, monde.carte)
        cellules = [c for c in monde.cells if vue[c] == s.suzerain]
        voisins = sorted({e["b"] if e["a"] == cid else e["a"] for e in monde.adjacency
                          if e["kind"] == "land-land" and cid in (e["a"], e["b"])})
        assert cellules and voisins
        assert fiche.seigneurie == s and fiche.cell_id == cid
        assert fiche.habitants == monde.cells[cid].population
        assert fiche.production_kg_par_tick > 0
        assert fiche.production_kg_par_tick == population_soutenable_de(monde.cells[cid], monde.carte) * constantes.FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
        assert fiche.suzerain == puissances[s.suzerain]
        assert fiche.maison == tenantes[maisons.par_puissance[s.suzerain]]
        assert fiche.maison.nom == MAISONS[fiche.suzerain.nom]
        assert fiche.cellules_du_suzerain == len(cellules)
        assert fiche.habitants_du_suzerain == sum(monde.cells[c].population for c in cellules)
        assert [(v.cell_id, v.puissance, v.habitants) for v in fiche.voisins] == [
            (c, puissances.get(vue[c]), monde.cells[c].population) for c in voisins]
        fiches[s.nom] = fiche
        print(f"{s.nom}: cell_id={cid}, habitants={fiche.habitants}, production_kg_par_tick={fiche.production_kg_par_tick}, suzerain={fiche.suzerain.nom}, maison={fiche.maison.nom}, cellules_du_suzerain={fiche.cellules_du_suzerain}, habitants_du_suzerain={fiche.habitants_du_suzerain}, voisins={voisins}")
    bar, wurtemberg, moree, brankovic, evrenos = (fiches[n] for n in SUZERAINS)
    assert evrenos.cell_id in {v.cell_id for v in brankovic.voisins}
    assert brankovic.cell_id in {v.cell_id for v in evrenos.voisins}
    assert evrenos.cellules_du_suzerain > moree.cellules_du_suzerain
    assert len(moree.voisins) < len(bar.voisins)
    monde.cells[bar.cell_id].population += 1000
    assert fiche_de_seigneurie(bar.seigneurie.id, monde).habitants == bar.habitants + 1000
    monde.cells[bar.cell_id].population -= 1000
    autre = next(c for c in monde.cells if c != bar.cell_id and vue[c] == bar.suzerain.id)
    monde.cells[autre].population += 1000
    assert fiche_de_seigneurie(bar.seigneurie.id, monde).habitants_du_suzerain == bar.habitants_du_suzerain + 1000
    assert fiche_de_seigneurie(wurtemberg.seigneurie.id, monde).habitants_du_suzerain == wurtemberg.habitants_du_suzerain
    print(f"fiches_vues={len(fiches)}, contre_épreuves_population=2")


def test_inconnue(contexte, monkeypatch):
    monde, seigneuries, _, _ = contexte
    avant = copy.deepcopy(monde.to_dict())
    bar = next(s for s in seigneuries if s.nom == "Duché de Bar")
    assert fiche_de_seigneurie(bar.id, monde).seigneurie == bar
    # Toute consultation du monde pendant le refus ferait échouer le test.
    monkeypatch.setattr("sim.seigneuries.cellule_du_siege", lambda *args: pytest.fail("calcul avant refus"))
    inconnus = (max(s.id for s in seigneuries) + 1, True, "Bar", None)
    for identifiant in inconnus:
        with pytest.raises(SeigneurieInconnue) as erreur:
            fiche_de_seigneurie(identifiant, monde)
        assert repr(identifiant) in str(erreur.value)
        assert monde.to_dict() == avant
    print(f"inconnues_refusées={len(inconnus)}, mondes_inchangés={len(inconnus)}")


def test_pure(contexte):
    monde, seigneuries, _, _ = contexte
    avant = copy.deepcopy(monde.to_dict())
    for s in seigneuries:
        fiche = fiche_de_seigneurie(s.id, monde)
        assert fiche == fiche_de_seigneurie(s.id, monde)
        for objet in (s, s.siege, fiche, *fiche.voisins):
            assert isinstance(objet, _NoBadSpatialField)
            champ = dataclasses.fields(objet)[0].name
            with pytest.raises(dataclasses.FrozenInstanceError):
                setattr(objet, champ, None)
    assert monde.to_dict() == avant
    moteur = Path(__file__).parents[1]
    compteurs = {nom: sum("seigneur" in ligne for ligne in (moteur / nom).read_text().splitlines())
                for nom in ("engine.py", "world.py", "model.py", "seigneuries.py")}
    print(f"fiches_pures={len(seigneuries)}, occurrences_seigneur={compteurs}")
    assert len(seigneuries) > 0 and compteurs.pop("seigneuries.py") > 0
    assert set(compteurs.values()) == {0}


def test_sieges_frontiere(contexte):
    monde, seigneuries, _, _ = contexte
    bar = next(s for s in seigneuries if s.nom == "Duché de Bar")
    ids = sorted(cellule_du_siege(s, monde.carte) for s in seigneuries)
    petit, grand = ids[:2]
    gauche = {"type": "Polygon", "coordinates": [[[-1, -1], [0, -1], [0, 1], [-1, 1], [-1, -1]]]}
    droite = {"type": "Polygon", "coordinates": [[[0, -1], [1, -1], [1, 1], [0, 1], [0, -1]]]}
    carte = {grand: {"geometry": droite}, petit: {"geometry": gauche}}
    frontiere = dataclasses.replace(bar, siege=dataclasses.replace(bar.siege, x_m=0, y_m=0))
    assert cellule_du_siege(frontiere, carte) == petit
    interieur = dataclasses.replace(bar, siege=dataclasses.replace(bar.siege, x_m=0.5, y_m=0))
    assert cellule_du_siege(interieur, carte) == grand
    print("frontières_départagées=1, intérieurs_par_polygone=1")


def test_fiche_voisins_et_absences(contexte, monkeypatch):
    monde, seigneuries, table, maisons = contexte
    bar = next(s for s in seigneuries if s.nom == "Duché de Bar")
    fiche = fiche_de_seigneurie(bar.id, monde)
    arete = next(e for e in monde.adjacency if e["kind"] == "land-land"
                 and fiche.cell_id in (e["a"], e["b"]))
    deja_voisines = {v.cell_id for v in fiche.voisins} | {fiche.cell_id}
    autre = next(cid for cid in monde.cells if cid not in deja_voisines)
    monde.adjacency += [dict(arete), {**arete, "a": arete["b"], "b": arete["a"]},
                        {**arete, "a": fiche.cell_id, "b": autre, "kind": "land-sea"}]
    assert fiche_de_seigneurie(bar.id, monde) == fiche
    venise = next(p for p in table.puissances if p.nom == "Venise")
    sans_maison = dataclasses.replace(bar, suzerain=venise.id)
    assert fiche_de_seigneurie(bar.id, monde, (sans_maison,), table, maisons).maison is None
    vue = puissances_depuis_monde(monde)
    voisin = fiche.voisins[0].cell_id
    vue[voisin] = None
    monkeypatch.setattr("sim.seigneuries.puissances_depuis_monde", lambda *args, **kwargs: vue)
    nouvelle = fiche_de_seigneurie(bar.id, monde)
    assert next(v for v in nouvelle.voisins if v.cell_id == voisin).puissance is None
    print("doublons_ignorés=2, arêtes_marines_ignorées=1, maisons_absentes=1, voisins_non_couverts=1")


def test_controles(tmp_path, monkeypatch):
    from sim.tests import test_no_hardcoded as controle
    source = Path(__file__).parents[1] / "seigneuries.py"
    mauvaise = tmp_path / source.name
    mauvaise.write_text(source.read_text() + "\n\ndef contre_epreuve():\n    return 5\n", encoding="utf-8")
    # Le même contrôle existant doit rougir sur cette copie altérée.
    with monkeypatch.context() as sonde:
        sonde.setattr(controle, "_ENGINE_FILES", [mauvaise])
        with pytest.raises(AssertionError):
            controle.test_no_hardcoded_numeric_literals()
    assert controle._collect_literals_in_functions(source) == []
    modele = (source.parent / "MODELE.md").read_text()
    section = modele.split("## Les seigneuries de départ, vue dérivée\n", 1)[1].split("\n## ", 1)[0]
    compte = sum(any(n in ligne for n in ("Morée", "Evrenos", "Branković")) for ligne in section.splitlines())
    assert compte >= 3
    print(f"littéraux_en_dur=0, contre_épreuve_rouge=1, lignes_modèle={compte}")
