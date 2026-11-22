"""Les noms de l'atlas (MODELE.md, « Les noms de l'atlas, vue dérivée »).

Les fleuves : chacun part de la terre, finit à moins d'un pas de la côte (le pas est le côté
d'une cellule moyenne, dérivé de la carte) et passe par les cellules de ses villes témoins,
prises dans les tables sourcées (villes, ancres des puissances). Le Nil garde le tracé de
`nil-cours-1400.json`. Les mers : le point de chacune est hors de toute terre. Les régions :
le point de chacune est dans une cellule. Les sièges : celui de chaque maison placée a un nom
servi, par la table des villes ou par l'atlas ; Biskra, Bar-le-Duc et Mistra y sont. Aucun nom
n'est en double, et un échantillon vide échoue.

Le service : `GET /atlas` sert ce que le module calcule, calculé une fois à la première lecture,
hors du verrou du tick ; ni un tick ni une prise ne le refont, et une erreur rend 500 sans
arrêter le service.

Contre-épreuves : un fleuve qui finit dans les terres, un fleuve qui ne part pas de la terre,
une mer posée sur la terre, une région en mer, un doublon, des listes vides, une source
absente, un siège retiré rougissent.
"""

import copy
import json
import math
import pathlib
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from http import HTTPStatus

import pytest

from sim.atlas import (AtlasInvalide, Atlas, charger_atlas, document_de_l_atlas, pas_de_la_carte,
                       verifier_la_place)
from sim.fleuve import charger_points
from sim.places import sieges_des_maisons
from sim.projection import projeter_epsg3035
from sim.service import ServeurMonde, _serialiser
from sim.tests.test_monde import requete_service
from sim.puissances import charger_table
from sim.registre_maisons import charger_registre_maisons
from sim.villes import charger_villes, point_dans_geometrie
from sim.world import World

_FICHIER = pathlib.Path(__file__).parents[2] / "data" / "atlas-1400.json"

# Ce que la fiche du lot promet de nommer.
FLEUVES_PROMIS = ("Loire", "Seine", "Rhône", "Rhin", "Danube", "Elbe", "Pô", "Èbre", "Tage", "Vistule", "Dniepr", "Nil")
MERS_PROMISES = ("Méditerranée", "Atlantique", "Mer du Nord", "Baltique", "Mer Noire", "Adriatique", "Mer Égée")
REGIONS_PROMISES = ("Aquitaine", "Lombardie", "Bohême", "Anatolie")
SIEGES_PROMIS = ("Biskra", "Bar-le-Duc", "Mistra")

# Les villes témoins de chaque fleuve : des lieux de ses rives, dont la position vient d'une
# table sourcée du monde (villes de 1400 ou ancres des puissances), jamais de ce fichier.
TEMOINS = {
    "Loire": ("Orléans", "Angers", "Nantes"),
    "Seine": ("Paris", "Rouen"),
    "Rhône": ("Lyon", "Avignon"),
    "Rhin": ("Cologne", "Coblence"),
    "Danube": ("Vienne", "Buda", "Belgrade"),
    "Elbe": ("Prague",),
    "Pô": ("Plaisance", "Crémone"),
    "Èbre": ("Saragosse",),
    "Tage": ("Tolède", "Lisbonne"),
    "Vistule": ("Cracovie",),
    "Dniepr": ("Kiev", "Smolensk"),
    "Nil": ("Le Caire", "Damiette"),
}

# Une ligne se parcourt à ce nombre de pas par pas de la carte, pour ne sauter aucune cellule.
ECHANTILLONS_PAR_PAS = 8


@pytest.fixture(scope="module")
def monde():
    return World.charger(rng_seed=0)


@pytest.fixture(scope="module")
def carte(monde):
    return monde.carte


@pytest.fixture(scope="module")
def atlas():
    return charger_atlas()


@pytest.fixture(scope="module")
def document(monde, atlas):
    return document_de_l_atlas(monde, atlas)


@pytest.fixture(scope="module")
def boites(carte):
    """La boîte de chaque cellule, pour ne tester que les cellules proches d'un point."""
    resultat = {}
    for cid, cellule in carte.items():
        polygones = cellule["geometry"]["coordinates"]
        points = [p for polygone in (polygones if cellule["geometry"]["type"] == "MultiPolygon" else [polygones])
                  for anneau in polygone for p in anneau]
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        resultat[cid] = (min(xs), min(ys), max(xs), max(ys))
    return resultat


def cellules_du_point(carte, boites, x, y):
    """Les cellules dont le polygone contient le point (plusieurs sur un bord)."""
    return {cid for cid, (x0, y0, x1, y1) in boites.items()
            if x0 <= x <= x1 and y0 <= y <= y1 and point_dans_geometrie(x, y, carte[cid]["geometry"])}


def cellules_de_la_ligne(carte, boites, pas, ligne):
    """Les cellules que la ligne traverse, échantillonnée plus finement que la plus petite cellule."""
    cellules = set()
    for (x1, y1), (x2, y2) in zip(ligne, ligne[1:]):
        n = max(1, math.ceil(math.hypot(x2 - x1, y2 - y1) / (pas / ECHANTILLONS_PAR_PAS)))
        for i in range(n + 1):
            cellules |= cellules_du_point(carte, boites, x1 + (x2 - x1) * i / n, y1 + (y2 - y1) * i / n)
    return cellules


def lignes_xy(entree):
    return [[(p["x_m"], p["y_m"]) for p in ligne] for ligne in entree["lignes"]]


def positions_connues():
    """Villes de 1400 et ancres des puissances : les positions sourcées des témoins."""
    positions = {a.nom: projeter_epsg3035(a.lat, a.lon) for a in charger_table().ancres}
    positions.update({v.nom: (v.x_m, v.y_m) for v in charger_villes()})
    return positions


def sieges_manquants(registre, document, villes):
    """Les maisons placées dont le nom du siège n'est servi ni par la table des villes ni par l'atlas."""
    servis = {s["nom"] for s in document["sieges"]} | {v.nom for v in villes}
    return sorted(m.siege for m in registre if m.cell_id is not None and m.siege not in servis)


def noms_du_document(document):
    return ([f["nom"] for f in document["fleuves"]] + [m["nom"] for m in document["mers"]]
            + [r["nom"] for r in document["regions"]] + [s["nom"] for s in document["sieges"]])


def fichier_altere(tmp_path, modifier):
    """Écrit une copie du fichier de l'atlas que `modifier` a changée ; rend son chemin."""
    brut = json.loads(_FICHIER.read_text(encoding="utf-8"))
    modifier(brut)
    chemin = tmp_path / "atlas.json"
    chemin.write_text(json.dumps(brut, ensure_ascii=False), encoding="utf-8")
    return chemin


def trouver(liste, nom):
    return next(entree for entree in liste if entree["nom"] == nom)


# --- Ce que la fiche promet de nommer ---

def test_l_atlas_nomme_ce_que_la_fiche_promet(atlas, document):
    assert {f.nom for f in atlas.fleuves} >= set(FLEUVES_PROMIS)
    assert {m.nom for m in atlas.mers} >= set(MERS_PROMISES)
    assert {r.nom for r in atlas.regions} >= set(REGIONS_PROMISES)
    assert {s["nom"] for s in document["sieges"]} >= set(SIEGES_PROMIS)
    for entree in document["fleuves"]:
        assert entree["lignes"] and all(len(ligne) >= 2 for ligne in entree["lignes"]), entree["nom"]


def test_aucun_nom_en_double(document):
    noms = [nom.casefold() for nom in noms_du_document(document)]
    assert len(noms) > len(FLEUVES_PROMIS) + len(MERS_PROMISES) + len(REGIONS_PROMISES)
    doubles = sorted({nom for nom in noms if noms.count(nom) > 1})
    assert not doubles, f"noms servis plusieurs fois : {doubles}"


def test_chaque_ligne_de_donnee_cite_sa_source(atlas):
    lignes = [p for f in atlas.fleuves for ligne in f.lignes for p in ligne] + list(atlas.mers) + list(atlas.regions)
    assert lignes
    sans = [p.nom for p in lignes if not p.source.strip()]
    assert not sans, f"sans source : {sans}"


# --- Les fleuves ---

def test_chaque_fleuve_part_de_la_terre_et_finit_a_moins_d_un_pas_de_la_cote(carte, boites, document):
    pas = pas_de_la_carte(carte)
    assert pas > 0
    assert document["fleuves"]
    for entree in document["fleuves"]:
        for ligne in lignes_xy(entree):
            assert cellules_du_point(carte, boites, *ligne[0]), f"{entree['nom']} ne part pas de la terre"
            x, y = ligne[-1]
            en_mer = not cellules_du_point(carte, boites, x, y)
            # Une mer à moins d'un pas : un point de sonde de la couronne d'un pas est hors de toute cellule.
            if not en_mer:
                couronne = [(x + pas * math.cos(a * math.pi / 8), y + pas * math.sin(a * math.pi / 8)) for a in range(16)]
                en_mer = any(not cellules_du_point(carte, boites, px, py) for px, py in couronne)
            assert en_mer, f"{entree['nom']} finit à plus d'un pas de la côte"


def test_chaque_fleuve_passe_par_ses_villes_temoins(carte, boites, document):
    pas = pas_de_la_carte(carte)
    positions = positions_connues()
    assert {f["nom"] for f in document["fleuves"]} <= set(TEMOINS), "un fleuve sans ville témoin"
    verifies = 0
    for nom, temoins in TEMOINS.items():
        traversees = set()
        for ligne in lignes_xy(trouver(document["fleuves"], nom)):
            traversees |= cellules_de_la_ligne(carte, boites, pas, ligne)
        for temoin in temoins:
            assert temoin in positions, f"{temoin} : aucune position sourcée"
            cellules = cellules_du_point(carte, boites, *positions[temoin])
            assert cellules, f"{temoin} hors carte"
            assert cellules & traversees, f"{nom} ne passe pas par la cellule de {temoin}"
            verifies += 1
    assert verifies >= len(TEMOINS)


def test_le_nil_garde_le_trace_de_son_fichier(document):
    points = {p.id: projeter_epsg3035(p.lat, p.lon) for p in charger_points()}
    servis = {(round(x), round(y)) for ligne in lignes_xy(trouver(document["fleuves"], "Nil")) for x, y in ligne}
    attendus = {(round(x), round(y)) for x, y in points.values()}
    assert servis == attendus, "le Nil servi n'est pas celui de nil-cours-1400.json"


# --- Les mers et les régions ---

def test_le_point_de_chaque_mer_est_hors_de_toute_terre(carte, boites, document):
    assert document["mers"]
    for mer in document["mers"]:
        assert not cellules_du_point(carte, boites, mer["x_m"], mer["y_m"]), f"{mer['nom']} est sur la terre"


def test_le_point_de_chaque_mer_est_dans_le_cadre_de_la_carte(boites, document):
    x0, y0 = min(b[0] for b in boites.values()), min(b[1] for b in boites.values())
    x1, y1 = max(b[2] for b in boites.values()), max(b[3] for b in boites.values())
    assert document["mers"]
    for mer in document["mers"]:
        assert x0 <= mer["x_m"] <= x1 and y0 <= mer["y_m"] <= y1, f"{mer['nom']} est hors du cadre de la carte"


def test_le_point_de_chaque_region_est_dans_une_cellule(carte, boites, document):
    assert document["regions"]
    for region in document["regions"]:
        assert cellules_du_point(carte, boites, region["x_m"], region["y_m"]), f"{region['nom']} est en mer"


# --- Les sièges ---

def test_le_siege_de_chaque_maison_placee_a_un_nom_servi(monde, document):
    registre = charger_registre_maisons(monde.carte)
    assert [m for m in registre if m.cell_id is not None]
    assert sieges_manquants(registre, document, charger_villes()) == []


def test_un_siege_servi_n_est_pas_une_ville_de_la_table_et_reste_dans_sa_cellule(monde, document, carte, boites):
    villes = {v.nom for v in charger_villes()}
    registre = {m.siege: m for m in charger_registre_maisons(monde.carte) if m.cell_id is not None}
    assert document["sieges"]
    for siege in document["sieges"]:
        assert siege["nom"] not in villes, f"{siege['nom']} est déjà une ville de la table"
        maison = registre[siege["nom"]]
        assert siege["maison"] == maison.id
        assert maison.cell_id in cellules_du_point(carte, boites, siege["x_m"], siege["y_m"]), siege["nom"]


def test_les_sieges_servis_sont_ceux_du_registre_sans_siege_synthetique(monde, document):
    registre = charger_registre_maisons(monde.carte)
    assert not [s for s in document["sieges"] if s["nom"].startswith("plausible")]
    assert {s["maison"] for s in document["sieges"]} <= {m.id for m in registre}
    assert set(sieges_des_maisons()) >= {s["maison"] for s in document["sieges"]}


def test_un_siege_retire_du_document_rougit(monde, document):
    registre = charger_registre_maisons(monde.carte)
    sans_biskra = copy.deepcopy(document)
    sans_biskra["sieges"] = [s for s in sans_biskra["sieges"] if s["nom"] != "Biskra"]
    assert sieges_manquants(registre, sans_biskra, charger_villes()) == ["Biskra"]


# --- L'échantillon vide échoue, et les données altérées rougissent ---

def test_un_atlas_vide_est_refuse(carte):
    with pytest.raises(AtlasInvalide):
        verifier_la_place(Atlas(fleuves=(), mers=(), regions=()), carte)


def test_une_carte_vide_est_refusee(atlas):
    with pytest.raises(AtlasInvalide):
        verifier_la_place(atlas, {})


@pytest.mark.parametrize("clef", ["fleuves", "mers", "regions"])
def test_une_liste_vide_est_refusee(tmp_path, clef):
    chemin = fichier_altere(tmp_path, lambda brut: brut.__setitem__(clef, []))
    with pytest.raises(AtlasInvalide, match=clef):
        charger_atlas(chemin)


def _fleuve_finit_dans_les_terres(brut):
    trouver(brut["fleuves"], "Loire")["points"][-1].update(lat=47.9025, lon=1.909)


def _fleuve_ne_part_pas_de_la_terre(brut):
    trouver(brut["fleuves"], "Loire")["points"][0].update(lat=45.5, lon=-4.4)


def _mer_sur_la_terre(brut):
    trouver(brut["mers"], "Méditerranée").update(lat=41.9, lon=12.5)


def _mer_hors_du_cadre(brut):
    trouver(brut["mers"], "Atlantique").update(lat=0.0, lon=-25.0)


def _region_en_mer(brut):
    trouver(brut["regions"], "Aquitaine").update(lat=45.5, lon=-4.4)


@pytest.mark.parametrize("modifier, attendu", [
    (_fleuve_finit_dans_les_terres, "Loire"),
    (_fleuve_ne_part_pas_de_la_terre, "Loire"),
    (_mer_sur_la_terre, "Méditerranée"),
    (_mer_hors_du_cadre, "Atlantique"),
    (_region_en_mer, "Aquitaine"),
])
def test_une_place_fausse_est_refusee_et_nommee(tmp_path, carte, modifier, attendu):
    altere = charger_atlas(fichier_altere(tmp_path, modifier))
    with pytest.raises(AtlasInvalide, match=attendu):
        verifier_la_place(altere, carte)


def _doublon_de_nom(brut):
    brut["mers"][1]["nom"] = brut["mers"][0]["nom"]


def _doublon_entre_listes(brut):
    brut["regions"][0]["nom"] = brut["fleuves"][0]["nom"].upper()


def _source_absente(brut):
    del brut["mers"][0]["source"]


def _source_de_point_vide(brut):
    trouver(brut["fleuves"], "Seine")["points"][2]["source"] = "  "


def _nom_vide(brut):
    brut["regions"][0]["nom"] = ""


def _fleuve_a_un_point(brut):
    trouver(brut["fleuves"], "Seine")["points"] = trouver(brut["fleuves"], "Seine")["points"][:1]


def _latitude_impossible(brut):
    brut["regions"][0]["lat"] = 123.0


def _coordonnee_non_finie(brut):
    brut["mers"][0]["lon"] = float("nan")


def _nil_sans_bras(brut):
    del trouver(brut["fleuves"], "Nil")["bras"]


def _nil_point_inconnu(brut):
    trouver(brut["fleuves"], "Nil")["bras"][0]["points"][1] = 9999


def _nil_autre_fichier(brut):
    trouver(brut["fleuves"], "Nil")["trace_dans"] = "autre-cours.json"


def _projection_etrangere(brut):
    brut["projection"] = "EPSG:4326"


@pytest.mark.parametrize("modifier, attendu", [
    (_doublon_de_nom, "double"),
    (_doublon_entre_listes, "double"),
    (_source_absente, "source"),
    (_source_de_point_vide, "source"),
    (_nom_vide, "nom"),
    (_fleuve_a_un_point, "Seine"),
    (_latitude_impossible, "lat"),
    (_coordonnee_non_finie, "lon"),
    (_nil_sans_bras, "Nil"),
    (_nil_point_inconnu, "Nil"),
    (_nil_autre_fichier, "Nil"),
    (_projection_etrangere, "projection"),
])
def test_une_donnee_alteree_est_refusee_et_nommee(tmp_path, modifier, attendu):
    with pytest.raises(AtlasInvalide, match=attendu):
        charger_atlas(fichier_altere(tmp_path, modifier))


def test_le_document_est_le_meme_a_chaque_appel(monde, atlas, document):
    assert document_de_l_atlas(monde, atlas) == document
    assert json.loads(json.dumps(document)) == document


# --- Le service : GET /atlas ---

@contextmanager
def _service_local():
    """Un service de graine 0, dont l'horloge ne joue pas seule."""
    serveur = ServeurMonde(("127.0.0.1", 0), 0, 0)
    fil = threading.Thread(target=serveur.serve_forever)
    fil.start()
    try:
        yield serveur, serveur.server_address[1]
    finally:
        serveur.shutdown()
        serveur.server_close()
        fil.join()


def test_la_route_sert_ce_que_le_module_calcule(monde, document):
    attendu = _serialiser(document_de_l_atlas(monde))
    with _service_local() as (_, port):
        statut, servi, octets = requete_service(port, "/atlas")
        _, carte_servie, _ = requete_service(port, "/carte")
    assert statut == HTTPStatus.OK
    assert octets == attendu and len(attendu) > 0
    assert set(servi) == {"crs", "version", "fleuves", "mers", "regions", "sieges"}
    assert servi["crs"] == "EPSG:3035"
    assert servi["version"] == carte_servie["version"] == monde.carte_meta["version"]
    assert servi == document
    # Contre-épreuve : un octet de plus ne passe pas.
    with pytest.raises(AssertionError):
        assert octets + b" " == attendu


def test_la_route_calcule_une_fois_et_garde_ses_octets(monkeypatch):
    import sim.service as service

    appels = []
    vraie = service.document_de_l_atlas

    def compter(*args, **kwargs):
        appels.append(1)
        return vraie(*args, **kwargs)

    monkeypatch.setattr(service, "document_de_l_atlas", compter)
    with _service_local() as (serveur, port):
        assert not appels
        with ThreadPoolExecutor(max_workers=4) as lecteurs:
            reponses = list(lecteurs.map(lambda _: requete_service(port, "/atlas"), range(4)))
        assert len(appels) == 1
        assert {statut for statut, _, _ in reponses} == {HTTPStatus.OK}
        premiers = reponses[0][2]
        assert premiers and all(octets == premiers for _, _, octets in reponses)
        requete_service(port, "/tick?n=1", "POST")
        # Une prise de bourg : le maître d'un lieu devient celui d'une autre maison.
        with serveur.verrou_tick:
            cid = next(c for c in sorted(serveur.world.cells) if serveur.world.cells[c].lieux)
            lieu = serveur.world.cells[cid].lieux[0]
            lieu.maitre = next(m for m in sorted({l.maitre for c in serveur.world.cells.values()
                                                  for l in c.lieux if l.maitre}) if m != lieu.maitre)
        requete_service(port, "/tick?n=1", "POST")
        statut, _, apres = requete_service(port, "/atlas")
        assert statut == HTTPStatus.OK
        assert apres == premiers
        assert len(appels) == 1


def test_le_tick_ne_calcule_aucun_atlas(monkeypatch):
    import sim.service as service

    def sonde(*args, **kwargs):
        raise AssertionError("le tick a calculé l'atlas")

    monkeypatch.setattr(service, "document_de_l_atlas", sonde)
    serveur = ServeurMonde(("127.0.0.1", 0), 0, 0)
    try:
        serveur.jouer_un_tick()
        serveur.jouer_un_tick()
        assert serveur._atlas_figee is None
    finally:
        serveur.server_close()


@pytest.mark.parametrize("erreur", [AtlasInvalide, ValueError, OSError])
def test_une_erreur_de_calcul_rend_500_sans_arreter_le_service(monkeypatch, monde, erreur):
    import sim.service as service

    with _service_local() as (_, port):
        with monkeypatch.context() as patch:
            def refuser(*args, **kwargs):
                raise erreur("donnée absente")

            patch.setattr(service, "document_de_l_atlas", refuser)
            statut, document, _ = requete_service(port, "/atlas")
            assert statut == HTTPStatus.INTERNAL_SERVER_ERROR
            assert document == {"erreur": "donnée absente"}
            assert requete_service(port, "/monde")[0] == HTTPStatus.OK
        statut, _, octets = requete_service(port, "/atlas")
        assert statut == HTTPStatus.OK
        assert octets == _serialiser(document_de_l_atlas(monde))


# --- La règle écrite ---

def test_documentation_des_noms_de_l_atlas(document):
    texte = (pathlib.Path(__file__).parents[1] / "MODELE.md").read_text(encoding="utf-8")
    section = texte.split("## Les noms de l'atlas, vue dérivée\n", 1)[1].split("\n## ", 1)[0]
    for attendu in ("GET /atlas", "atlas-1400.json", "nil-cours-1400.json", "`trace_dans`", "Niveau 1",
                    "Niveau 2", "Niveau 3", "AtlasInvalide", "verrou propre", "Le tick ne lit jamais cette vue",
                    "charger_registre_maisons", "villes-1400.json", "`POINTS_MIN_FLEUVE`", "`DIRECTIONS_DE_SONDE`",
                    "`ANNEAUX_DE_SONDE`"):
        assert attendu in section, f"{attendu!r} absent de « Les noms de l'atlas »"
    # Les nombres que la section annonce sont ceux du document servi.
    assert f"{len(document['mers'])} mers" in section
    assert f"{len(document['regions'])} régions" in section
    assert f"{len(document['sieges'])} sièges" in section
    assert f"nomme onze" in section and len(document["fleuves"]) == 12
    for renvoi in ("La carte et les terres servies, vue dérivée", "La forme des lieux, vue dérivée"):
        autre = texte.split(f"## {renvoi}\n", 1)[1].split("\n## ", 1)[0]
        assert "« Les noms de l'atlas, vue dérivée »" in autre.replace("\n", " "), f"{renvoi} ne renvoie pas à l'atlas"
