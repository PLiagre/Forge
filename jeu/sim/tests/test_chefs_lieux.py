"""Chaque terre porte le nom de sa vraie ville de 1400.

Le juge lit le monde livré de la graine 0 : le nom du bourg de chaque terre, servi par
`noms_depuis_monde`, qui nomme toute la terre à l'infobulle comme à la fiche. Ce nom est une
ville sourcée, qui tombe dans le polygone de sa cellule : le siège d'une maison du registre, une
ville de `villes-1400.json`, ou le chef-lieu de la cellule dans `chefs-lieux-1400.json`. Une
terre où l'histoire ne nomme aucune ville le déclare avec sa raison et garde un nom plausible des
listes. Deux terres ne portent jamais le même nom. Là où les frontières nomment des villes
(villes de partage, villes témoins), le chef-lieu est l'une d'elles, et dans une cellule
partagée il est du pays du bourg.
"""
import collections
import copy
import dataclasses
import json
import pathlib
import types
from types import SimpleNamespace

import pytest

from sim.frontieres import charger_frontieres, puissances_des_lieux
from sim.noms import charger_noms, noms_depuis_monde
from sim.places import sieges_des_maisons
from sim.projection import projeter_epsg3035
from sim.puissances import charger_table
from sim.villes import point_dans_geometrie
from sim.world import World

CHEMIN_CHEFS_LIEUX = pathlib.Path(__file__).resolve().parents[2] / "data" / "chefs-lieux-1400.json"
# Les propriétés que le juge nomme, dans l'ordre de la fiche.
SOURCE, UNIQUE, POLYGONE, FRONTIERES, DECLAREE, ECHANTILLON = (
    "nom sourcé", "nom unique", "dans son polygone", "villes des frontières", "terre déclarée", "échantillon")


def _boite(geometrie):
    polygones = [geometrie["coordinates"]] if geometrie["type"] == "Polygon" else geometrie["coordinates"]
    points = [p for anneaux in polygones for p in anneaux[0]]
    return (min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points))


def _cellule_du_point(carte, boites, x, y):
    """La cellule de la carte dont le polygone contient le point, ou None ; par identifiant croissant."""
    for cid in sorted(boites):
        x_min, y_min, x_max, y_max = boites[cid]
        if x_min <= x <= x_max and y_min <= y <= y_max and point_dans_geometrie(x, y, carte[cid]["geometry"]):
            return cid
    return None


@pytest.fixture(scope="module")
def livre():
    monde = World.charger(0)
    table = charger_table()
    frontieres = charger_frontieres(table=table, carte=monde.carte)
    vue = noms_depuis_monde(monde)
    bourgs = {cid: next(l["nom"] for l in bloc["lieux"] if l["rang"] == 0) for cid, bloc in vue.items()}
    boites = {cid: _boite(monde.carte[cid]["geometry"]) for cid in monde.cells}
    sieges = sieges_des_maisons(table)
    sources = collections.defaultdict(list)  # nom → points (x, y) des villes sourcées de ce nom
    for maison in monde.maisons:
        if maison.sorte != "plausible" and maison.id in sieges:
            sources[maison.siege].append(sieges[maison.id])
    for ville in monde.attribution_villes.entrees:
        sources[ville.nom].append((ville.x_m, ville.y_m))
    des_frontieres = collections.defaultdict(list)  # cell_id → (nom, lat, lon, pays) des villes de partage et témoins
    for cid, villes in frontieres.partages.items():
        des_frontieres[cid].extend((v.nom, v.lat, v.lon, v.pays) for v in villes)
    for temoin in frontieres.temoins:
        cid = _cellule_du_point(monde.carte, boites, *projeter_epsg3035(temoin.lat, temoin.lon))
        if cid is not None:
            des_frontieres[cid].append((temoin.nom, temoin.lat, temoin.lon, temoin.pays))
    lieux = puissances_des_lieux(monde, table, frontieres)
    listes = charger_noms()
    contexte = SimpleNamespace(
        carte=monde.carte, sources=dict(sources), des_frontieres=dict(des_frontieres),
        pays_du_bourg={cid: lieux.get((cid, 0)) for cid in frontieres.partages if cid in monde.cells},
        noms_des_listes=frozenset(n for aire in listes["aires"].values() for n in aire["lieux"]))
    chefs = json.loads(CHEMIN_CHEFS_LIEUX.read_text(encoding="utf-8"))
    return SimpleNamespace(monde=monde, bourgs=bourgs, contexte=contexte, chefs=chefs,
                           fautes=juger(contexte, bourgs, chefs))


def juger(contexte, bourgs, chefs):
    """Les fautes des noms de terre `bourgs` (cell_id → nom du bourg), en (propriété, cellules accusées, texte)."""
    fautes = []
    if not bourgs:
        return [(ECHANTILLON, (), "échantillon vide : aucune terre jugée")]
    lignes, vues = {}, set()
    for ligne in chefs["chefs_lieux"]:
        cid = ligne["cell_id"]
        if cid in vues:
            fautes.append((SOURCE, (cid,), f"cellule {cid} : deux chefs-lieux"))
        vues.add(cid)
        lignes[cid] = ligne
        if "http" not in (ligne.get("source") or ""):
            fautes.append((SOURCE, (cid,), f"cellule {cid} : chef-lieu « {ligne['nom']} » sans source publique"))
    declarees = {}
    for ligne in chefs["sans_ville"]:
        cid = ligne["cell_id"]
        if cid in declarees or cid in lignes:
            fautes.append((DECLAREE, (cid,), f"cellule {cid} : déclarée deux fois"))
        declarees[cid] = ligne.get("raison")

    for cid, ligne in sorted(lignes.items()):
        if cid not in bourgs:
            continue
        if not point_dans_geometrie(*projeter_epsg3035(ligne["lat"], ligne["lon"]), contexte.carte[cid]["geometry"]):
            fautes.append((POLYGONE, (cid,), f"cellule {cid} : son chef-lieu « {ligne['nom']} » est hors de son polygone"))
        if bourgs[cid] != ligne["nom"]:
            fautes.append((SOURCE, (cid,), f"cellule {cid} : son chef-lieu « {ligne['nom']} » ne nomme pas le bourg « {bourgs[cid]} »"))

    for cid, nom in sorted(bourgs.items()):
        geometrie = contexte.carte[cid]["geometry"]
        villes = contexte.des_frontieres.get(cid, ())
        if cid in declarees:
            if not (declarees[cid] or "").strip():
                fautes.append((DECLAREE, (cid,), f"cellule {cid} : déclarée sans ville, sans raison"))
            nommees = sorted({v[0] for v in villes} | {n for n, points in contexte.sources.items()
                                                       if any(point_dans_geometrie(*p, geometrie) for p in points)})
            if nommees:
                fautes.append((DECLAREE, (cid,), f"cellule {cid} : déclarée sans ville, mais les tables y nomment {', '.join(nommees)}"))
            if nom not in contexte.noms_des_listes:
                fautes.append((DECLAREE, (cid,), f"cellule {cid} : déclarée sans ville, son bourg « {nom} » n'est pas un nom plausible des listes"))
            continue
        chef = lignes.get(cid)
        points = list(contexte.sources.get(nom, ()))
        par_le_chef_lieu = chef is not None and chef["nom"] == nom and nom not in contexte.sources
        if par_le_chef_lieu:
            points.append(projeter_epsg3035(chef["lat"], chef["lon"]))
        if nom in contexte.noms_des_listes:
            fautes.append((SOURCE, (cid,), f"cellule {cid} : « {nom} » est un nom des listes, sans raison déclarée"))
        elif not points:
            fautes.append((SOURCE, (cid,), f"cellule {cid} : « {nom} » n'est ni un siège, ni une ville de villes-1400.json, ni son chef-lieu"))
        elif not any(point_dans_geometrie(*p, geometrie) for p in points):
            fautes.append((POLYGONE, (cid,), f"cellule {cid} : « {nom} » est hors de son polygone"))
        if villes and nom not in contexte.sources:
            # Le bourg n'est nommé ni par un siège ni par une ville de la carte : son chef-lieu est une ville des frontières.
            memes = [v for v in villes if par_le_chef_lieu and (v[0], v[1], v[2]) == (chef["nom"], chef["lat"], chef["lon"])]
            if not memes:
                fautes.append((FRONTIERES, (cid,), f"cellule {cid} : « {nom} » n'est aucune de ses villes des frontières "
                                           f"({', '.join(dict.fromkeys(v[0] for v in villes))}), aux mêmes coordonnées"))
        if cid in contexte.pays_du_bourg:
            for ville in villes:
                if ville[0] == nom and ville[3] != contexte.pays_du_bourg[cid]:
                    fautes.append((FRONTIERES, (cid,), f"cellule {cid} : « {nom} » est du pays {ville[3]}, "
                                               f"son bourg du pays {contexte.pays_du_bourg[cid]}"))

    compte = collections.defaultdict(list)
    for cid, nom in sorted(bourgs.items()):
        compte[nom.casefold()].append(cid)
    for cids in compte.values():
        if len(cids) > 1:
            fautes.append((UNIQUE, tuple(cids), f"« {bourgs[cids[0]]} » nomme {len(cids)} terres : {', '.join(map(str, cids))}"))
    return fautes


def _de(fautes, propriete):
    return [texte for p, _, texte in fautes if p == propriete]


def _rapport(fautes):
    return f"{len(fautes)} fautes :\n" + "\n".join(fautes)


# --- Le monde livré ------------------------------------------------------------------------------

def test_chaque_bourg_porte_une_ville_sourcee(livre):
    assert len(livre.bourgs) == len(livre.monde.cells) > 0
    fautes = _de(livre.fautes, SOURCE)
    assert not fautes, _rapport(fautes)


def test_deux_terres_ne_portent_jamais_le_meme_nom(livre):
    fautes = _de(livre.fautes, UNIQUE)
    assert not fautes, _rapport(fautes)


def test_chaque_ville_nommee_tombe_dans_son_polygone(livre):
    jugees = [cid for cid, nom in livre.bourgs.items() if nom in livre.contexte.sources]
    jugees += [l["cell_id"] for l in livre.chefs["chefs_lieux"]]
    assert jugees, "échantillon vide : aucune terre nommée par une ville"
    fautes = _de(livre.fautes, POLYGONE)
    assert not fautes, _rapport(fautes)


def test_le_chef_lieu_suit_les_villes_des_frontieres(livre):
    assert livre.contexte.des_frontieres and livre.contexte.pays_du_bourg, "échantillon vide : aucune ville des frontières"
    fautes = _de(livre.fautes, FRONTIERES)
    assert not fautes, _rapport(fautes)


def test_chaque_terre_sans_ville_dit_sa_raison(livre):
    assert livre.chefs["sans_ville"], "échantillon vide : aucune terre déclarée sans ville"
    fautes = _de(livre.fautes, DECLAREE)
    assert not fautes, _rapport(fautes)


# --- Les contre-épreuves : le juge voit chaque faute qu'on lui montre ----------------------------

@pytest.fixture(scope="module")
def epreuve(livre):
    """Un monde jugé sans faute : les terres que nomme déjà un siège ou une ville sans faute, puis une terre libre
    `libre` (ni siège, ni ville, ni ville des frontières, centroïde dans son polygone) et une terre
    partagée `partagee` (ni siège ni ville), dont deux villes de partage sont de pays différents."""
    c = livre.contexte
    accusees = {cid for _, cids, _ in livre.fautes for cid in cids}
    sures = {cid: nom for cid, nom in livre.bourgs.items() if nom in c.sources and cid not in accusees}
    libre = next(cid for cid in sorted(livre.bourgs) if cid not in sures and cid not in c.des_frontieres
                 and point_dans_geometrie(livre.monde.carte[cid]["centroid"]["x_m"], livre.monde.carte[cid]["centroid"]["y_m"],
                                          livre.monde.carte[cid]["geometry"]))
    partagee = next(cid for cid in sorted(c.pays_du_bourg) if cid not in sures
                    and any(v[3] == c.pays_du_bourg[cid] for v in c.des_frontieres[cid])
                    and any(v[3] != c.pays_du_bourg[cid] for v in c.des_frontieres[cid]))
    juste = next(v for v in c.des_frontieres[partagee] if v[3] == c.pays_du_bourg[partagee])
    centre = livre.monde.carte[libre]["centroid"]
    vide = {**livre.chefs, "chefs_lieux": [], "sans_ville": []}
    chefs = {**vide, "chefs_lieux": [
        {"cell_id": libre, "nom": "Ville d'épreuve", "lat": centre["lat"], "lon": centre["lon"], "source": "https://exemple.org/epreuve"},
        {"cell_id": partagee, "nom": juste[0], "lat": juste[1], "lon": juste[2], "source": "https://exemple.org/partage"}]}
    bourgs = {**sures, libre: "Ville d'épreuve", partagee: juste[0]}
    assert juger(c, bourgs, chefs) == [], "la base des contre-épreuves doit être sans faute"
    return SimpleNamespace(contexte=c, bourgs=bourgs, chefs=chefs, libre=libre, partagee=partagee, sures=sures)


def _ligne(chefs, cid):
    return next(l for l in chefs["chefs_lieux"] if l["cell_id"] == cid)


def test_le_juge_refuse_un_echantillon_vide(epreuve):
    assert _de(juger(epreuve.contexte, {}, epreuve.chefs), ECHANTILLON)


def test_le_juge_voit_un_nom_en_double(epreuve):
    a, b = sorted(epreuve.sures)[:2]
    assert _de(juger(epreuve.contexte, {**epreuve.bourgs, b: epreuve.bourgs[a]}, epreuve.chefs), UNIQUE)
    casse = {**epreuve.bourgs, epreuve.libre: epreuve.bourgs[a].upper()}
    chefs = copy.deepcopy(epreuve.chefs)
    _ligne(chefs, epreuve.libre)["nom"] = epreuve.bourgs[a].upper()
    assert _de(juger(epreuve.contexte, casse, chefs), UNIQUE)


def test_le_juge_voit_une_ville_hors_de_sa_cellule(epreuve):
    chefs = copy.deepcopy(epreuve.chefs)
    ailleurs = epreuve.contexte.carte[epreuve.partagee]["centroid"]
    _ligne(chefs, epreuve.libre).update(lat=ailleurs["lat"], lon=ailleurs["lon"])
    assert _de(juger(epreuve.contexte, epreuve.bourgs, chefs), POLYGONE)
    a, b = sorted(epreuve.sures)[:2]
    assert _de(juger(epreuve.contexte, {**epreuve.bourgs, a: epreuve.bourgs[b], b: epreuve.bourgs[a]}, epreuve.chefs), POLYGONE)


def test_le_juge_voit_un_nom_de_liste_sans_raison(epreuve):
    plausible = min(epreuve.contexte.noms_des_listes)
    chefs = {**epreuve.chefs, "chefs_lieux": [l for l in epreuve.chefs["chefs_lieux"] if l["cell_id"] != epreuve.libre]}
    assert _de(juger(epreuve.contexte, {**epreuve.bourgs, epreuve.libre: plausible}, chefs), SOURCE)
    assert _de(juger(epreuve.contexte, {**epreuve.bourgs, epreuve.libre: "Nom inventé"}, chefs), SOURCE)
    declare = {**chefs, "sans_ville": [{"cell_id": epreuve.libre, "raison": "erg sans ville nommée par l'histoire"}]}
    assert juger(epreuve.contexte, {**epreuve.bourgs, epreuve.libre: plausible}, declare) == []


def test_le_juge_voit_une_raison_vide(epreuve):
    plausible = min(epreuve.contexte.noms_des_listes)
    chefs = {**epreuve.chefs, "chefs_lieux": [l for l in epreuve.chefs["chefs_lieux"] if l["cell_id"] != epreuve.libre]}
    bourgs = {**epreuve.bourgs, epreuve.libre: plausible}
    for raison in ("", "  ", None):
        assert _de(juger(epreuve.contexte, bourgs, {**chefs, "sans_ville": [{"cell_id": epreuve.libre, "raison": raison}]}), DECLAREE)
    sure = min(epreuve.sures)
    sans = {**chefs, "sans_ville": [{"cell_id": sure, "raison": "aucune ville"}]}
    assert _de(juger(epreuve.contexte, {**bourgs, sure: plausible}, sans), DECLAREE)


def test_le_juge_voit_un_chef_lieu_hors_des_villes_des_frontieres(epreuve):
    c = epreuve.contexte
    etrangere = next(v for v in c.des_frontieres[epreuve.partagee] if v[3] != c.pays_du_bourg[epreuve.partagee])
    chefs = copy.deepcopy(epreuve.chefs)
    _ligne(chefs, epreuve.partagee).update(nom=etrangere[0], lat=etrangere[1], lon=etrangere[2])
    assert _de(juger(c, {**epreuve.bourgs, epreuve.partagee: etrangere[0]}, chefs), FRONTIERES)
    centre = c.carte[epreuve.partagee]["centroid"]
    _ligne(chefs, epreuve.partagee).update(nom="Ville d'ailleurs", lat=centre["lat"], lon=centre["lon"])
    assert _de(juger(c, {**epreuve.bourgs, epreuve.partagee: "Ville d'ailleurs"}, chefs), FRONTIERES)
    chefs = copy.deepcopy(epreuve.chefs)
    _ligne(chefs, epreuve.partagee)["lat"] += 0.01
    assert _de(juger(c, epreuve.bourgs, chefs), FRONTIERES)


# --- Le fichier des chefs-lieux et la règle du bourg ---------------------------------------------

def _document():
    return json.loads(CHEMIN_CHEFS_LIEUX.read_text(encoding="utf-8"))


def _gater(document, defaut):
    ligne, autre, sans = document["chefs_lieux"][0], document["chefs_lieux"][1], document["sans_ville"][0]
    if defaut == "clé en trop": document["auteur"] = "x"
    elif defaut == "clé absente": del document["fidelite"]
    elif defaut == "date": document["date"] = "1401-01-01"
    elif defaut == "fidélité vide": document["fidelite"] = "  "
    elif defaut == "cellule en texte": ligne["cell_id"] = str(ligne["cell_id"])
    elif defaut == "cellule booléenne": ligne["cell_id"] = True
    elif defaut == "cellule deux fois": autre["cell_id"] = ligne["cell_id"]
    elif defaut == "nommée et sans ville": sans["cell_id"] = ligne["cell_id"]
    elif defaut == "nom deux fois": autre["nom"] = ligne["nom"].upper()
    elif defaut == "nom vide": ligne["nom"] = ""
    elif defaut == "source sans URL": ligne["source"] = "Wikipédia, article sans lien"
    elif defaut == "latitude hors bornes": ligne["lat"] = 91
    elif defaut == "longitude non finie": ligne["lon"] = float("nan")
    elif defaut == "champ en trop": ligne["population"] = 1000
    elif defaut == "raison vide": sans["raison"] = ""
    elif defaut == "région vide": sans["region"] = ""
    elif defaut == "région deux fois": document["sans_ville"][1]["region"] = sans["region"].upper()
    elif defaut == "région sans article": sans["region"] = "Jura"
    elif defaut == "région d'un chef-lieu": sans["region"] = "la " + ligne["nom"]
    return document


DEFAUTS = ("clé en trop", "clé absente", "date", "fidélité vide", "cellule en texte", "cellule booléenne", "cellule deux fois",
           "nommée et sans ville", "nom deux fois", "nom vide", "source sans URL", "latitude hors bornes",
           "longitude non finie", "champ en trop", "raison vide", "région vide", "région deux fois", "région sans article",
           "région d'un chef-lieu")


@pytest.mark.parametrize("defaut", DEFAUTS)
def test_le_fichier_des_chefs_lieux_refuse_chaque_defaut(tmp_path, defaut):
    from sim.noms import charger_chefs_lieux
    chemin = tmp_path / "chefs.json"
    chemin.write_text(json.dumps(_document(), ensure_ascii=False), encoding="utf-8")
    assert charger_chefs_lieux(chemin).lignes, "le fichier livré, recopié, doit se lire"
    gate = tmp_path / "gate.json"
    gate.write_text(json.dumps(_gater(_document(), defaut), ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="chefs-lieux"):
        charger_chefs_lieux(gate)


def test_le_fichier_des_chefs_lieux_se_lit_une_fois_et_ne_change_pas():
    from sim.noms import charger_chefs_lieux
    chefs = charger_chefs_lieux()
    assert charger_chefs_lieux() is chefs is charger_chefs_lieux(CHEMIN_CHEFS_LIEUX)
    cid = next(iter(chefs.lignes))
    with pytest.raises(TypeError):
        chefs.lignes[cid] = None
    with pytest.raises(dataclasses.FrozenInstanceError):
        chefs.lignes[cid].nom = "Autre"
    with pytest.raises(TypeError):
        chefs.regions[next(iter(chefs.regions))] = "le Souf"


def test_chaque_terre_sans_ville_porte_sa_region_avec_son_article():
    from sim.noms import _ARTICLES_DE_REGION, charger_chefs_lieux
    chefs = charger_chefs_lieux()
    assert chefs.sans_ville, "échantillon vide : aucune terre déclarée sans ville"
    assert list(chefs.regions) == sorted(chefs.sans_ville)
    assert all(r.startswith(_ARTICLES_DE_REGION) for r in chefs.regions.values())
    assert len({r.casefold() for r in chefs.regions.values()}) == len(chefs.regions)


def test_le_bourg_suit_le_siege_puis_la_ville_puis_le_chef_lieu(livre):
    from sim.frontieres import maison_du_bourg
    from sim.noms import bourgs_historiques
    monde, attribution = livre.monde, livre.monde.attribution_villes
    bourgs = bourgs_historiques(monde, attribution)
    registre = {m.id: m for m in monde.maisons}
    sieges = {cid: registre[m].siege for cid in monde.cells if (m := maison_du_bourg(monde, cid)) is not None}
    villes = collections.defaultdict(list)
    for v in sorted(attribution.entrees, key=lambda v: (-v.population, v.nom)):
        if attribution.placees.get(v.nom) is not None:
            villes[attribution.placees[v.nom]].append(v.nom)
    assert sieges and all(bourgs[cid] == nom for cid, nom in sieges.items())
    # Une ville que le siège d'une autre terre nomme déjà ne nomme pas la sienne (Tolède, à cheval sur deux terres).
    prises = [cid for cid, noms in villes.items() if cid not in sieges and noms[0] in sieges.values()]
    assert prises and all(bourgs[cid] != villes[cid][0] for cid in prises)
    # Un siège passe devant la plus grande ville de sa terre (Eisenach devant Erfurt).
    devant = [cid for cid in sieges if villes.get(cid) and villes[cid][0] != sieges[cid]]
    assert devant and all(bourgs[cid] == sieges[cid] for cid in devant)
    chefs = livre.chefs
    assert all(bourgs[l["cell_id"]] == l["nom"] for l in chefs["chefs_lieux"])
    assert not set(bourgs) & {l["cell_id"] for l in chefs["sans_ville"]}
    assert set(bourgs) | {l["cell_id"] for l in chefs["sans_ville"]} == set(monde.cells)


def test_la_regle_du_bourg_refuse_chaque_ligne_fausse(livre):
    from sim.noms import ChefLieu, ChefsLieux, bourgs_historiques, charger_chefs_lieux
    monde, attribution, chefs = livre.monde, livre.monde.attribution_villes, charger_chefs_lieux()
    def avec(lignes=None, sans_ville=None):
        regions = dict(chefs.regions) if sans_ville is None else {c: chefs.regions.get(c, "la terre d'épreuve") for c in sans_ville}
        return ChefsLieux(types.MappingProxyType(dict(chefs.lignes) if lignes is None else lignes),
                          types.MappingProxyType(dict(chefs.sans_ville) if sans_ville is None else sans_ville),
                          types.MappingProxyType(regions))
    cid, ligne = next(iter(chefs.lignes.items()))
    loin = monde.carte[next(c for c in sorted(chefs.lignes) if c != cid)]["centroid"]
    deplacee = {**chefs.lignes, cid: dataclasses.replace(ligne, lat=loin["lat"], lon=loin["lon"])}
    with pytest.raises(ValueError, match=f"cellule {cid} : .* hors du polygone"):
        bourgs_historiques(monde, attribution, avec(lignes=deplacee))
    nommee = next(c for c in sorted(monde.cells) if c not in chefs.lignes and c not in chefs.sans_ville)
    with pytest.raises(ValueError, match=f"cellule {nommee} : déjà nommée"):
        bourgs_historiques(monde, attribution, avec(lignes={**chefs.lignes, nommee: ligne}))
    with pytest.raises(ValueError, match=f"cellule {nommee} : déjà nommée"):
        bourgs_historiques(monde, attribution, avec(sans_ville={**chefs.sans_ville, nommee: "aucune ville"}))
    oubliee = {c: l for c, l in chefs.lignes.items() if c != cid}
    with pytest.raises(ValueError, match=f"cellule {cid} : ni nommée ni déclarée"):
        bourgs_historiques(monde, attribution, avec(lignes=oubliee))
    # Un monde d'épreuve qui n'a qu'une part des terres laisse de côté les lignes des autres.
    part = copy.copy(monde)
    part.cells = {c: monde.cells[c] for c in sorted(monde.cells)[:40]}
    assert bourgs_historiques(part, attribution) == {c: n for c, n in bourgs_historiques(monde, attribution).items() if c in part.cells}
    assert bourgs_historiques(part, attribution, avec(lignes={**chefs.lignes, 10 ** 9: ligne}))


def test_une_terre_sans_ville_porte_un_nom_plausible_que_nulle_autre_ne_porte(livre):
    from sim.noms import charger_chefs_lieux, _parcours
    from sim.puissances import puissances_depuis_monde
    from sim.noms import aire_de_cellule
    chefs, listes, table = charger_chefs_lieux(), charger_noms(), charger_table()
    vue = puissances_depuis_monde(livre.monde, table=table)
    assert chefs.sans_ville
    for cid in chefs.sans_ville:
        aire = aire_de_cellule(cid, livre.monde.carte[cid], vue[cid], table, listes)
        parcours = _parcours(listes["aires"][aire]["lieux"], cid)
        assert livre.bourgs[cid] in parcours
        autres = {n.casefold() for c, n in livre.bourgs.items() if c != cid}
        # Le premier nom libre du parcours, dans l'ordre des cellules : les terres déclarées avant lui l'ont pu prendre.
        avant = parcours[:parcours.index(livre.bourgs[cid])]
        assert all(n.casefold() in autres for n in avant)


def test_les_rangs_n_emploient_jamais_le_nom_du_bourg_a_la_casse_pres(livre):
    from sim.noms import _parcours, aire_de_cellule
    from sim.puissances import puissances_depuis_monde
    monde, table = livre.monde, charger_table()
    vue = puissances_depuis_monde(monde, table=table)
    cid = next(c for c in sorted(monde.cells) if livre.bourgs[c] in livre.contexte.sources and len(monde.cells[c].lieux) > 2)
    listes = copy.deepcopy(charger_noms()); aire = aire_de_cellule(cid, monde.carte[cid], vue[cid], table, listes)
    lieux = listes["aires"][aire]["lieux"]
    # Le nom du bourg en capitales, posé au second rang de son parcours.
    lieux.insert((cid + 1) % (len(lieux) + 1), livre.bourgs[cid].upper())
    assert _parcours(lieux, cid)[1] == livre.bourgs[cid].upper()
    noms = [l["nom"] for l in noms_depuis_monde(monde, noms=listes)[cid]["lieux"]]
    assert noms[0] == livre.bourgs[cid] and all(n.casefold() != noms[0].casefold() for n in noms[1:])


def test_un_monde_amorce_sans_villes_se_charge_et_garde_les_noms_du_fichier(monkeypatch):
    """Un monde amorcé avec d'autres villes que celles du fichier (aucune, ou une ville d'épreuve) se charge,
    et ses terres portent les noms des villes du fichier."""
    from sim.frontieres import maison_du_bourg
    from sim.noms import charger_chefs_lieux
    from sim.villes import AttributionVilles, Ville, attribuer_villes, charger_villes
    monkeypatch.setattr("sim.world.charger_villes", lambda: ())
    monde = World.charger(0)
    assert monde.attribution_villes.entrees == ()
    chefs = charger_chefs_lieux()
    livree = attribuer_villes({**monde.carte_meta, "cellules": list(monde.carte.values())}, charger_villes())
    par_terre = collections.defaultdict(list)
    for v in sorted(livree.entrees, key=lambda v: (-v.population, v.nom)):
        if livree.placees.get(v.nom) is not None:
            par_terre[livree.placees[v.nom]].append(v.nom)
    sieges = {m.siege.casefold() for m in monde.maisons
              if m.sorte != "plausible" and maison_du_bourg(monde, m.cell_id) == m.id}
    # Seule une ville du fichier nomme ces terres : ni siège, ni ligne des chefs-lieux, ni terre déclarée sans ville.
    attendues = {cid: noms[0] for cid, noms in par_terre.items()
                 if cid in monde.cells and cid not in chefs.lignes and cid not in chefs.sans_ville
                 and maison_du_bourg(monde, cid) is None and noms[0].casefold() not in sieges}
    assert 9905 in attendues, f"échantillon vide ou sans la cellule 9905 : {sorted(attendues)[:10]}"
    vue = noms_depuis_monde(monde)
    assert {cid: vue[cid]["lieux"][0]["nom"] for cid in attendues} == attendues
    # Sans recharger : une ville d'épreuve que le fichier ne connaît pas ne change pas le nom d'une ligne des chefs-lieux.
    cid = next(iter(chefs.lignes))
    centre = monde.carte[cid]["centroid"]
    epreuve = Ville("Ville d'épreuve", centre["lat"], centre["lon"], centre["x_m"], centre["y_m"], 10_000, {})
    essai = copy.copy(monde)
    essai.attribution_villes = AttributionVilles({epreuve.nom: cid}, (), (epreuve,))
    assert noms_depuis_monde(essai)[cid]["lieux"][0]["nom"] == chefs.lignes[cid].nom
