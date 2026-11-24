"""Les frontières de 1400 (`sim/frontieres.py`, `data/frontieres-1400.json`).

Les preuves de chaque région de la table (`ouest`, `empire`, `nord`, `est`, `balkans`, `orient`,
`maghreb` ; `-k <région>`) jugent le monde livré :
- chaque ville témoin de la région tombe dans un lieu du pays que la table lui donne ;
- chaque cellule tenue de la région a un pays, un partage ou une lacune, et aucune ne doit son
  pays à l'ancre la plus proche ;
- chaque pays de la région a un nom, une capitale dans ses lieux et un chef ou une lacune déclarée.
Sur toute la table : chaque témoin est d'une région, et dans une cellule partagée chaque lieu est au
pays de la ville la plus proche de sa place. Sur toute la carte : chaque cellule a un pays, un
partage ou une lacune, et chaque suzerain déclaré est un pays servi, sans boucle. Dans l'Ouest : la Navarre tient moins de lieux que sa
cellule n'en compte, et Bar a ses vrais voisins. Dans l'Empire : aucune terre ni aucun lieu n'a pour
pays le Saint-Empire, le duché de Luxembourg tient au plus les lieux que la table lui donne, chaque
prince servi porte son ensemble, et le Wurtemberg (Stuttgart) a ses vrais voisins. À l'Est : la
Pologne et la Lituanie, la Bohême et la Hongrie ont chacune leur chef.
"""
import copy
import dataclasses
import json
import re
from collections import Counter
from types import SimpleNamespace

import pytest

import sim.constants as constantes
import sim.frontieres as frontieres_module
import sim.puissances as puissances_module
from sim.carte_servie import terres_et_pays
from sim.frontieres import (
    charger_frontieres, decisions_des_frontieres, maison_du_bourg, puissances_des_lieux, terres_des_lieux,
)
from sim.jouables import maisons_jouables
from sim.maisons import charger_maisons, maisons_depuis_monde
from sim.maitres import AttributionInvalide, attribuer_maitres, valider_attribution
from sim.noms import noms_depuis_monde
from sim.pays_servis import (
    SourcesDesPays, fiches_des_pays, identifiant_de_puissance, identifiant_de_terre, pays_des_lieux, pays_des_terres,
    puissance_du_lieu, tete_de_puissance,
)
from sim.places import places_du_monde
from sim.projection import projeter_epsg3035
from sim.puissances import PuissanceInvalide, charger_table, puissances_depuis_monde
from sim.registre_maisons import charger_registre_maisons
from sim.seigneuries import charger_seigneuries, fiche_de_seigneurie, identifiant_de_seigneurie
from sim.villes import point_dans_geometrie
from sim.world import World

# Les villes que la fiche de chaque région nomme : chacune a son témoin dans la table, au pays de la
# région. Stuttgart, siège d'une terre de départ et non d'une puissance, a sa preuve à part.
TEMOINS_NOMMES = {
    "ouest": ("Paris", "Rouen", "Toulouse", "Bordeaux", "Nantes", "Dijon", "Bruges", "Londres", "Édimbourg",
              "Dublin", "Lisbonne", "Séville", "Pampelune", "Barcelone", "Grenade", "Milan", "Venise", "Gênes",
              "Florence", "Rome", "Naples", "Palerme"),
    "empire": ("Vienne", "Munich", "Heidelberg", "Cologne", "Mayence", "Trèves", "Prague", "Bruxelles",
               "Lübeck", "Luxembourg", "Innsbruck", "Linz"),
    "nord": ("Roskilde", "Stockholm", "Bergen", "Kalmar"),
    "est": ("Cracovie", "Vilnius", "Buda", "Novgorod", "Pskov", "Marienbourg"),
    "balkans": ("Constantinople", "Edirne", "Mistra", "Kruševac", "Bobovac", "Târgoviște", "Suceava",
                "Thessalonique", "Sofia", "Brousse", "Konya"),
    "orient": ("Rhodes", "Nicosie", "Le Caire", "Alexandrie", "Candie", "Qırq Yer"),
    "maghreb": ("Tunis", "Tlemcen", "Fès", "Marrakech", "Constantine"),
}
REGIONS = tuple(TEMOINS_NOMMES)
# Les régions que la table ne déclare pas encore. Leurs preuves échouent ; la marque est stricte : dès
# que la table déclare la région, sa preuve passe, et la marque fait échouer le test tant qu'on ne
# l'a pas retirée d'ici.
EN_ATTENTE = frozenset()
# Les vassaux que les fiches nomment, et le suzerain que leur fiche de pays sert.
VASSAUX_NOMMES = {
    "Serbie": "Ottomans", "Gênes": "France", "Naples": "États de l'Église", "Guyenne": "Angleterre",
    "Bourgogne": "France", "Lituanie": "Pologne", "Mazovie": "Pologne",
}
# Un pays plus petit que deux lieux se déclare en lacune, avec sa raison.
LIEUX_MIN_D_UN_PAYS = 2
EMPIRE = "Saint-Empire"
DUCHE_DE_LUXEMBOURG = "Duché de Luxembourg"
# Les princes que la fiche de l'Empire nomme : chacun est un pays servi qui dit son ensemble.
PRINCES_D_EMPIRE = (
    "Autriche", "Bavière", "Palatinat", "Saxe", "Brandebourg", "Brabant", "Hollande", "Hainaut", "Lorraine",
    DUCHE_DE_LUXEMBOURG, "Archevêché de Cologne", "Archevêché de Mayence", "Archevêché de Trèves",
    "Confédération des cantons suisses", "Bohême",
)


def _en_attente(region):
    return pytest.mark.xfail(region in EN_ATTENTE, strict=True,
                             reason=f"la table ne déclare pas encore la région {region}")


PAR_REGION = [pytest.param(region, marks=_en_attente(region), id=region) for region in REGIONS]


@pytest.fixture(scope="module")
def livre():
    monde = World.charger(0)
    table = charger_table()
    frontieres = charger_frontieres(table=table, carte=monde.carte)
    lieux = puissances_des_lieux(monde, table, frontieres)
    vue = puissances_depuis_monde(monde, table=table, frontieres=frontieres)
    maisons, seigneuries = charger_maisons(), charger_seigneuries(table=table)
    noms = noms_depuis_monde(monde, table=table, vue=vue)
    servie = terres_et_pays(monde, SimpleNamespace(noms=noms),
                            SourcesDesPays(table, maisons, seigneuries, vue, lieux,
                                           terres_des_lieux(monde, table, frontieres)))
    return SimpleNamespace(monde=monde, table=table, maisons=maisons, seigneuries=seigneuries,
                           frontieres=frontieres, lieux=lieux, places=places_du_monde(monde), vue=vue,
                           servie=servie)


def _region(livre, nom):
    """Le monde livré vu d'une région : ses pays et ses témoins, ceux dont le pays est de la région."""
    pays = frozenset(livre.frontieres.regions.get(nom, ()))
    return SimpleNamespace(**vars(livre), nom=nom, region=pays,
                           temoins=tuple(t for t in livre.frontieres.temoins if t.pays in pays))


def _cellule_du_point(monde, lat, lon):
    point = projeter_epsg3035(lat, lon)
    return next((c for c in sorted(monde.carte) if point_dans_geometrie(*point, monde.carte[c]["geometry"])), None)


def _carre(place, x, y):
    return (place.x_m - x) * (place.x_m - x) + (place.y_m - y) * (place.y_m - y)


def _lieu_le_plus_proche(places, lat, lon):
    x, y = projeter_epsg3035(lat, lon)
    return min(range(len(places)), key=lambda rang: (_carre(places[rang], x, y), rang))


def _verifier_temoins(s, temoins, nommes):
    assert set(nommes) <= {t.nom for t in temoins}, \
        f"témoins absents : {sorted(set(nommes) - {t.nom for t in temoins})}"
    places = [t for t in temoins if t.hors_carte is None]
    assert places, "échantillon vide"
    for temoin in temoins:
        assert temoin.pays in s.region, f"{temoin.nom} : pays hors de la région"
    for temoin in places:
        cid = _cellule_du_point(s.monde, temoin.lat, temoin.lon)
        assert cid is not None, f"{temoin.nom} : hors carte sans raison"
        rang = _lieu_le_plus_proche(s.places[cid], temoin.lat, temoin.lon)
        servi = puissance_du_lieu(cid, rang, s.vue, s.lieux)
        assert servi == temoin.pays, f"{temoin.nom} : lieu ({cid}, {rang}) au pays {servi}, {temoin.pays} attendu"
    assert {t.pays for t in temoins} <= {t.pays for t in places}, "un pays sans témoin placé"


@pytest.mark.parametrize("region", PAR_REGION)
def test_chaque_ville_temoin_tombe_dans_un_lieu_de_son_pays(livre, region):
    s = _region(livre, region)
    _verifier_temoins(s, s.temoins, TEMOINS_NOMMES[region])
    # Contre-épreuve : le premier témoin placé, déclaré au point d'un témoin d'un autre pays, ne tombe
    # plus dans un lieu de son pays.
    premier = next(t for t in s.temoins if t.hors_carte is None)
    autre = next(t for t in s.frontieres.temoins if t.hors_carte is None and t.pays != premier.pays)
    deplace = dataclasses.replace(premier, lat=autre.lat, lon=autre.lon)
    with pytest.raises(AssertionError, match=re.escape(premier.nom)):
        _verifier_temoins(s, [deplace if t is premier else t for t in s.temoins], ())


def _orphelins(temoins, regions):
    pays = set().union(*regions.values())
    return sorted(t.nom for t in temoins if t.pays not in pays)


def test_chaque_temoin_de_la_table_est_d_une_region(livre):
    temoins, regions = livre.frontieres.temoins, livre.frontieres.regions
    assert temoins, "échantillon vide"
    assert not _orphelins(temoins, regions), _orphelins(temoins, regions)
    # Contre-épreuve : sans régions, chaque témoin est orphelin.
    assert _orphelins(temoins, {"vide": ()}) == sorted(t.nom for t in temoins)


def _tenues(s):
    """Les cellules de la région : celles que la table donne à un pays de la région, en propre ou en partage."""
    f = s.frontieres
    return ({c for c, p in f.cellules.items() if p in s.region}
            | {c for c, villes in f.partages.items() if any(v.pays in s.region for v in villes)})


def _verifier_couverture(s, vue):
    tenues = _tenues(s)
    assert tenues, "échantillon vide"
    for cid in sorted(tenues):
        attendu = s.frontieres.cellules[cid] if cid in s.frontieres.cellules else s.lieux[cid, 0]
        assert vue.get(cid, -1) == attendu, f"cellule {cid} : {vue.get(cid, -1)} servi, {attendu} déclaré"


@pytest.mark.parametrize("region", PAR_REGION)
def test_chaque_cellule_tenue_est_declaree_et_aucune_ne_doit_son_pays_a_l_ancre(livre, region, tmp_path):
    s = _region(livre, region)
    _verifier_couverture(s, s.vue)
    # Les ancres du premier pays de la région qui a une maison, et d'un second (de la région, sinon le
    # premier d'ailleurs), échangées, ne changent aucune cellule de la carte : une ancre est un point,
    # elle ne décide aucun pays. Le siège d'une institution est sa première ancre et place le bourg
    # d'une cellule partagée : les pays échangés ont une maison, dont le siège est sa capitale.
    ancres = {a.puissance for a in s.table.ancres}
    avec_maison = sorted(p for p in ancres if s.maisons.par_puissance[p] is not None)
    dedans = [p for p in avec_maison if p in s.region]
    premier, second = (dedans + [p for p in avec_maison if p not in s.region])[:2]
    echange = {premier: second, second: premier}
    table = dataclasses.replace(s.table, ancres=tuple(
        dataclasses.replace(a, puissance=echange.get(a.puissance, a.puissance)) for a in s.table.ancres))
    assert table != s.table
    assert puissances_depuis_monde(s.monde, table=table, frontieres=s.frontieres) == s.vue
    # Contre-épreuves : une cellule de la région servie à un autre pays se voit ; retirée de la table, elle
    # est refusée au chargement, en la nommant.
    document = json.loads(TABLE_DES_FRONTIERES_LIVREE.read_text(encoding="utf-8"))
    ligne = next(l for l in document["pays"] if l["pays"] in s.region and len(l["cellules"]) > 1)
    retiree = ligne["cellules"].pop(0)
    autre = next(p.id for p in s.table.puissances if p.id != ligne["pays"])
    with pytest.raises(AssertionError, match=f"cellule {retiree} "):
        _verifier_couverture(s, {**s.vue, retiree: autre})
    chemin = tmp_path / "frontieres.json"
    chemin.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(PuissanceInvalide, match=f"cellule {retiree}, champ cell_id : cellule de la carte sans pays"):
        charger_frontieres(chemin, s.table, s.monde.carte)


def _pays_le_plus_proche(place, villes):
    distances = []
    for indice, ville in enumerate(villes):
        x, y = projeter_epsg3035(ville.lat, ville.lon)
        distances.append((_carre(place, x, y), indice, ville.pays))
    return min(distances)[2]


def _verifier_partages(s, lieux):
    partagees = sorted(s.frontieres.partages)
    assert partagees, "échantillon vide : aucune cellule partagée"
    for cid in partagees:
        servis = set()
        for rang, place in enumerate(s.places[cid]):
            attendu = _pays_le_plus_proche(place, s.frontieres.partages[cid])
            assert lieux[cid, rang] == attendu, f"lieu ({cid}, {rang}) : {lieux[cid, rang]}, {attendu} attendu"
            servis.add(attendu)
        assert len(servis) > 1, f"cellule {cid} partagée mais d'un seul pays"


def test_chaque_lieu_partage_est_au_pays_de_la_ville_la_plus_proche(livre):
    _verifier_partages(livre, livre.lieux)
    # Les maîtres suivent le partage : un lieu partagé est au pays de sa ville, sauf la terre de départ.
    par_id = {m.id: m for m in livre.monde.maisons}
    pays = pays_des_lieux(livre.monde, livre.vue, livre.maisons, livre.lieux)
    for (cid, rang), puissance in sorted(livre.lieux.items()):
        maitre = livre.monde.cells[cid].lieux[rang].maitre
        if puissance is not None and par_id[maitre].sorte != "seigneurie":
            assert pays[cid, rang] == identifiant_de_puissance(puissance), (cid, rang)
    # Contre-épreuve : un bourg passé au pays d'une autre ville de sa cellule se voit.
    cid = next(iter(livre.frontieres.partages))
    faux = dict(livre.lieux)
    faux[cid, 0] = next(v.pays for v in livre.frontieres.partages[cid] if v.pays != livre.lieux[cid, 0])
    with pytest.raises(AssertionError):
        _verifier_partages(livre, faux)


def test_ouest_navarre_plus_petite_que_sa_cellule(livre):
    navarre = next(p.id for p in livre.table.puissances if p.nom == "Navarre")
    pampelune = next(a for a in livre.table.ancres if a.nom == "Pampelune")
    cellule = _cellule_du_point(livre.monde, pampelune.lat, pampelune.lon)
    tenus = sum(puissance_du_lieu(cid, lieu.rang, livre.vue, livre.lieux) == navarre
                for cid, c in livre.monde.cells.items() for lieu in c.lieux)
    assert 0 < tenus < len(livre.monde.cells[cellule].lieux), \
        f"la Navarre tient {tenus} lieux, sa cellule {len(livre.monde.cells[cellule].lieux)}"


def _voisins_de_bar(s, vue):
    bar = next(x for x in s.seigneuries if x.nom == "Duché de Bar")
    fiche = fiche_de_seigneurie(bar.id, s.monde, table=s.table, vue=vue)
    return fiche, {v.puissance.nom if v.puissance is not None else None for v in fiche.voisins}


def test_ouest_bar_a_ses_vrais_voisins(livre):
    # Le Barrois relève de la France ; autour, la Champagne royale, puis la Lorraine et le duché de
    # Luxembourg, princes d'Empire : ni Bourgogne ni Trèves.
    fiche, voisins = _voisins_de_bar(livre, livre.vue)
    assert fiche.voisins, "échantillon vide"
    assert fiche.suzerain.nom == "France" and livre.vue[fiche.cell_id] == fiche.suzerain.id
    assert voisins == {"France", "Lorraine", DUCHE_DE_LUXEMBOURG}, voisins
    # Contre-épreuve : un voisin de Bar passé à la Bourgogne se voit.
    bourgogne = _puissance_nommee(livre.table, "Bourgogne")
    _, faux = _voisins_de_bar(livre, {**livre.vue, fiche.voisins[0].cell_id: bourgogne})
    assert faux != voisins and "Bourgogne" in faux


def _capitale(s, puissance, par_id):
    """Le lieu de la capitale d'un pays : le siège de la maison qui y règne s'il est un de ses lieux,
    sinon le lieu de la première ancre du pays qui tombe dans un de ses lieux."""
    tete = par_id.get(tete_de_puissance(puissance, s.maisons))
    if tete is not None and tete.cell_id is not None:
        if puissance_du_lieu(tete.cell_id, tete.rang, s.vue, s.lieux) == puissance:
            return tete.cell_id, tete.rang
    for ancre in (a for a in s.table.ancres if a.puissance == puissance):
        cid = _cellule_du_point(s.monde, ancre.lat, ancre.lon)
        if cid is not None:
            rang = _lieu_le_plus_proche(s.places[cid], ancre.lat, ancre.lon)
            if puissance_du_lieu(cid, rang, s.vue, s.lieux) == puissance:
                return cid, rang
    return None


def _fautes_des_pays(s, chefs):
    par_id = {m.id: m for m in s.monde.maisons}
    puissances = {p.id: p for p in s.table.puissances}
    tenus = Counter(puissance_du_lieu(cid, lieu.rang, s.vue, s.lieux)
                    for cid, cellule in s.monde.cells.items() for lieu in cellule.lieux)
    fautes = []
    for puissance in sorted(s.region):
        nom = puissances[puissance].nom
        if not nom.strip():
            fautes.append(f"{puissance} : sans nom")
        if tenus[puissance] < LIEUX_MIN_D_UN_PAYS:
            fautes.append(f"{nom} : {tenus[puissance]} lieu, à déclarer en petit pays")
        if _capitale(s, puissance, par_id) is None:
            fautes.append(f"{nom} : aucune capitale dans ses lieux")
        chef = chefs.get(tete_de_puissance(puissance, s.maisons))
        if chef is None or (chef["personnage"] is None and not (chef["lacune"] or "").strip()):
            fautes.append(f"{nom} : ni chef ni lacune déclarée")
    return fautes


@pytest.mark.parametrize("region", PAR_REGION)
def test_chaque_pays_a_nom_capitale_et_chef(livre, region):
    s = _region(livre, region)
    assert s.region, "échantillon vide"
    fautes = _fautes_des_pays(s, s.monde.chefs)
    assert not fautes, fautes
    # Contre-épreuve : la maison qui règne sur le premier pays de la région perd son chef et sa lacune.
    tete = tete_de_puissance(min(s.region), s.maisons)
    sans_chef = {**s.monde.chefs, tete: {"personnage": None, "lacune": None}}
    assert any("ni chef ni lacune" in f for f in _fautes_des_pays(s, sans_chef))


# --- Toute la carte -----------------------------------------------------------------------------

def _non_declarees(s, frontieres):
    return sorted(c for c in s.monde.cells if c not in frontieres.declarees())


@pytest.mark.xfail(bool(EN_ATTENTE), strict=True, reason="des régions de la carte restent à déclarer")
def test_toute_cellule_de_la_carte_a_son_pays_son_partage_ou_sa_lacune(livre):
    assert livre.monde.cells, "échantillon vide"
    oubliees = _non_declarees(livre, livre.frontieres)
    assert not oubliees, f"cellules sans pays, partage ni lacune : {oubliees[:12]} ({len(oubliees)})"
    # Aucune ne doit son pays à l'ancre : la puissance servie de chaque cellule est celle que la table décide.
    assert livre.vue == decisions_des_frontieres(livre.monde, livre.table, livre.frontieres, livre.lieux)
    # Contre-épreuve : une cellule retirée de la table se nomme.
    cid = min(livre.frontieres.cellules)
    amputee = dataclasses.replace(livre.frontieres, cellules={
        c: p for c, p in livre.frontieres.cellules.items() if c != cid})
    assert _non_declarees(livre, amputee) == [cid]


def _suzerain_attendu(s, identifiant):
    """Le suzerain que la table donne au pays servi : celui de la puissance, ou la puissance dont relève
    une terre de départ ; aucun pour une terre sans État."""
    puissances = {identifiant_de_puissance(p.id): p for p in s.table.puissances}
    departs = {identifiant_de_seigneurie(x.id): x for x in s.seigneuries}
    if identifiant in puissances:
        suzerain = puissances[identifiant].suzerain
        return None if suzerain is None else identifiant_de_puissance(suzerain)
    if identifiant in departs:
        return identifiant_de_puissance(departs[identifiant].suzerain)
    return None


def _fautes_des_suzerains(s, fiches):
    par_id = {f["id"]: f for f in fiches}
    fautes = []
    for fiche in fiches:
        attendu = _suzerain_attendu(s, fiche["id"])
        if fiche["suzerain"] != attendu:
            fautes.append(f"{fiche['nom']} : suzerain {fiche['suzerain']}, {attendu} attendu")
        if fiche["suzerain"] is not None and (fiche["suzerain"] not in par_id
                                              or not fiche["suzerain"].startswith(identifiant_de_puissance(""))):
            fautes.append(f"{fiche['nom']} : suzerain {fiche['suzerain']} non servi comme pays de la table")
        courant, vus = fiche, set()
        while courant is not None and courant["suzerain"] is not None:
            if courant["id"] in vus:
                fautes.append(f"{fiche['nom']} : boucle de suzerains")
                break
            vus.add(courant["id"])
            courant = par_id.get(courant["suzerain"])
    par_nom = {f["nom"]: f for f in fiches}
    for vassal, suzerain in sorted(VASSAUX_NOMMES.items()):
        fiche = par_nom.get(vassal)
        servi = (par_id.get(fiche["suzerain"]) or {}).get("nom") if fiche is not None else None
        if servi != suzerain:
            fautes.append(f"{vassal} : sa fiche sert le suzerain {servi}, {suzerain} attendu")
    return fautes


def test_chaque_suzerain_declare_est_un_pays_servi_sans_boucle(livre):
    fiches = livre.servie["pays"]
    assert [f for f in fiches if f["suzerain"] is not None], "échantillon vide : aucun suzerain servi"
    assert not _fautes_des_suzerains(livre, fiches), _fautes_des_suzerains(livre, fiches)
    # Contre-épreuves : le suzerain de la Serbie qui la reconnaît pour suzeraine boucle ; un suzerain
    # retiré des pays servis se voit.
    par_nom = {f["nom"]: f for f in fiches}
    serbie, ottomans = par_nom["Serbie"], par_nom["Ottomans"]
    boucle = [dict(f, suzerain=serbie["id"]) if f is ottomans else f for f in fiches]
    assert any("boucle" in f for f in _fautes_des_suzerains(livre, boucle))
    sans = [f for f in fiches if f is not ottomans]
    assert any("non servi" in f for f in _fautes_des_suzerains(livre, sans))


# --- L'Empire -----------------------------------------------------------------------------------

def _puissance_nommee(table, nom):
    identifiant = next((p.id for p in table.puissances if p.nom == nom), None)
    assert identifiant is not None, f"{nom} : pas une puissance de la table"
    return identifiant


def _au_saint_empire(s, vue, lieux):
    """Ce que tient le Saint-Empire : ses cellules, ses lieux, et les terres et lieux servis sous son nom."""
    empire = _puissance_nommee(s.table, EMPIRE)
    servi = identifiant_de_puissance(empire)
    terres = pays_des_terres(s.monde, vue, s.maisons, lieux)
    des_lieux = pays_des_lieux(s.monde, vue, s.maisons, lieux)
    return {
        "cellules": sorted(c for c, p in vue.items() if p == empire),
        "lieux": sorted((c, l.rang) for c, cellule in s.monde.cells.items() for l in cellule.lieux
                        if puissance_du_lieu(c, l.rang, vue, lieux) == empire),
        "terres servies": sorted(c for c, p in terres.items() if p == servi),
        "lieux servis": sorted(k for k, p in des_lieux.items() if p == servi),
    }


@_en_attente("empire")
def test_empire_aucune_terre_ni_aucun_lieu_n_a_pour_pays_le_saint_empire(livre):
    tenu = _au_saint_empire(livre, livre.vue, livre.lieux)
    assert not any(tenu.values()), {sorte: v[:8] for sorte, v in tenu.items() if v}
    # Le Saint-Empire reste un pays de la table : la fiche du Wurtemberg le sert comme suzerain.
    assert any(f["nom"] == EMPIRE for f in livre.servie["pays"])
    # Contre-épreuve : une cellule rendue au Saint-Empire se voit.
    cid = min(livre.vue)
    faux = {**livre.vue, cid: _puissance_nommee(livre.table, EMPIRE)}
    assert _au_saint_empire(livre, faux, livre.lieux)["cellules"] == [cid]


def _lieux_donnes(s, puissance):
    """Les lieux que la table donne à un pays : ceux de ses cellules entières, et ceux d'une cellule
    partagée dont la ville la plus proche est de ce pays."""
    f = s.frontieres
    donnes = {(c, l.rang) for c, p in f.cellules.items() if p == puissance and c in s.monde.cells
              for l in s.monde.cells[c].lieux}
    return donnes | {k for k, p in s.lieux.items() if p == puissance}


def _verifier_luxembourg(s, vue):
    duche = _puissance_nommee(s.table, DUCHE_DE_LUXEMBOURG)
    tenus = {(c, l.rang) for c, cellule in s.monde.cells.items() for l in cellule.lieux
             if puissance_du_lieu(c, l.rang, vue, s.lieux) == duche}
    assert tenus, "échantillon vide : le duché ne tient aucun lieu"
    hors = sorted(tenus - _lieux_donnes(s, duche))
    assert not hors, f"lieux du duché que la table ne lui donne pas : {hors[:8]}"


@_en_attente("empire")
def test_empire_le_duche_de_luxembourg_tient_au_plus_les_lieux_que_la_table_lui_donne(livre):
    _verifier_luxembourg(livre, livre.vue)
    # Contre-épreuve : une cellule que la table donne à un autre pays, donnée au duché, se voit.
    duche = _puissance_nommee(livre.table, DUCHE_DE_LUXEMBOURG)
    autre = next(c for c, p in livre.frontieres.cellules.items() if p != duche)
    with pytest.raises(AssertionError, match="ne lui donne pas"):
        _verifier_luxembourg(livre, {**livre.vue, autre: duche})


def _verifier_ensembles(s, fiches):
    par_nom = {f["nom"]: f for f in fiches}
    absents = [nom for nom in PRINCES_D_EMPIRE if nom not in par_nom]
    assert not absents, f"princes non servis : {absents}"
    sans = [nom for nom in PRINCES_D_EMPIRE if par_nom[nom]["ensemble"] != EMPIRE]
    assert not sans, f"princes servis sans l'ensemble {EMPIRE} : {sans}"
    # Tout pays servi tient son ensemble de la table, et lui seul.
    puissances = {identifiant_de_puissance(p.id): p for p in s.table.puissances}
    for fiche in fiches:
        attendu = puissances[fiche["id"]].ensemble if fiche["id"] in puissances else None
        assert fiche["ensemble"] == attendu, f"{fiche['id']} : {fiche['ensemble']}, {attendu} attendu"


@_en_attente("empire")
def test_empire_chaque_prince_servi_porte_son_ensemble(livre):
    fiches = livre.servie["pays"]
    # Chaque prince nommé tient des terres : sa fiche est servie parce qu'il est présent sur la carte.
    presents = {t["pays"] for t in livre.servie["terres"]} | {
        a["pays"] for t in livre.servie["terres"] for a in t["autres_pays"]}
    _verifier_ensembles(livre, [f for f in fiches if f["id"] in presents])
    # Contre-épreuve : le premier prince servi sans son ensemble se voit.
    premier = next(f for f in fiches if f["nom"] == PRINCES_D_EMPIRE[0])
    with pytest.raises(AssertionError, match="sans l'ensemble"):
        _verifier_ensembles(livre, [dict(f, ensemble=None) if f is premier else f for f in fiches])


def _princes_sans_terre(servie):
    """Les princes nommés qui ne sont le pays d'aucune terre servie : sans cellule à eux sur la carte."""
    par_nom = {f["nom"]: f["id"] for f in servie["pays"]}
    pays_des_terres = {t["pays"] for t in servie["terres"]}
    return [nom for nom in PRINCES_D_EMPIRE if par_nom.get(nom) not in pays_des_terres]


def test_empire_chaque_prince_nomme_a_sa_place_sur_la_carte(livre):
    # Un prince présent par les seuls lieux d'une terre d'un autre pays (`autres_pays`) n'a aucune
    # cellule à lui : la carte le peint aux couleurs du voisin.
    assert not _princes_sans_terre(livre.servie), _princes_sans_terre(livre.servie)
    # Contre-épreuve : les terres du Brandebourg passées à la Saxe, il n'a plus de place sur la carte.
    par_nom = {f["nom"]: f["id"] for f in livre.servie["pays"]}
    brandebourg, saxe = par_nom["Brandebourg"], par_nom["Saxe"]
    sans = dict(livre.servie, terres=[dict(t, pays=saxe) if t["pays"] == brandebourg else t
                                      for t in livre.servie["terres"]])
    assert _princes_sans_terre(sans) == ["Brandebourg"]


def _wurtemberg(s, vue):
    wurtemberg = next(x for x in s.seigneuries if x.nom == "Comté de Wurtemberg")
    return wurtemberg, fiche_de_seigneurie(wurtemberg.id, s.monde, s.seigneuries, s.table, s.maisons, vue)


def _verifier_wurtemberg(s, vue):
    wurtemberg, fiche = _wurtemberg(s, vue)
    empire = _puissance_nommee(s.table, EMPIRE)
    assert fiche.voisins, "échantillon vide"
    voisins = [v.puissance.nom if v.puissance is not None else None for v in fiche.voisins]
    princes = {p.nom for p in s.table.puissances if p.ensemble == EMPIRE}
    assert set(voisins) <= princes, f"voisins qui ne sont pas des princes d'Empire : {sorted(set(voisins) - princes, key=str)}"
    assert len(set(voisins)) > 1, voisins
    # Sa fiche de départ dit qu'il est d'Empire ; le Saint-Empire n'y tient aucune cellule.
    assert fiche.suzerain.nom == EMPIRE and fiche.cellules_du_suzerain == 0, \
        (fiche.suzerain.nom, fiche.cellules_du_suzerain)
    # Stuttgart tombe dans un lieu de la terre de départ, et le Saint-Empire ne tient aucun lieu de sa cellule.
    cid = fiche.cell_id
    rang = _lieu_le_plus_proche(s.places[cid], wurtemberg.siege.lat, wurtemberg.siege.lon)
    pays = pays_des_lieux(s.monde, vue, s.maisons, s.lieux)
    assert pays[cid, rang] == identifiant_de_seigneurie(wurtemberg.id), pays[cid, rang]
    assert all(puissance_du_lieu(cid, l.rang, vue, s.lieux) != empire for l in s.monde.cells[cid].lieux)


@_en_attente("empire")
def test_empire_le_wurtemberg_a_ses_vrais_voisins(livre):
    _verifier_wurtemberg(livre, livre.vue)
    # Contre-épreuve : un voisin rendu au Saint-Empire se voit.
    _, fiche = _wurtemberg(livre, livre.vue)
    voisin = fiche.voisins[0].cell_id
    with pytest.raises(AssertionError, match="pas des princes d'Empire"):
        _verifier_wurtemberg(livre, {**livre.vue, voisin: _puissance_nommee(livre.table, EMPIRE)})


# --- L'Est --------------------------------------------------------------------------------------

def _verifier_deux_chefs(s, premier, second):
    """Deux pays, deux maisons, deux chefs connus au 1er janvier 1400."""
    tetes = [tete_de_puissance(_puissance_nommee(s.table, nom), s.maisons) for nom in (premier, second)]
    assert tetes[0] != tetes[1], f"{premier} et {second} ont la même maison : {tetes[0]}"
    chefs = [(s.monde.chefs.get(tete) or {}).get("personnage") for tete in tetes]
    assert all(chefs), f"{premier}, {second} : chefs {chefs}"
    assert chefs[0] != chefs[1], chefs


def test_est_la_pologne_et_la_lituanie_ont_chacune_leur_chef(livre):
    _verifier_deux_chefs(livre, "Pologne", "Lituanie")
    # Contre-épreuve : deux pays d'une même maison (l'Aragon et la Sicile, des Barcelone) se voient.
    with pytest.raises(AssertionError, match="même maison"):
        _verifier_deux_chefs(livre, "Aragon", "Sicile")


def test_est_la_boheme_et_la_hongrie_ont_chacune_leur_chef(livre):
    _verifier_deux_chefs(livre, "Bohême", "Hongrie")


# ---------------------------------------------------------------------------------------------
# Les preuves de la table et de ses effets sur un partage synthétique. Elles partent de la table
# livrée, trois cellules changées : chacune écrit la sienne dans `tmp_path`, et le monde se charge une
# fois avec cette table, de sorte que la preuve tient quel que soit le pays de ces trois cellules.
# ---------------------------------------------------------------------------------------------
# Les fichiers livrés, lus avant que la fixture ne déplace le chemin de la table des frontières.
TABLE_DES_FRONTIERES_LIVREE = frontieres_module._CHEMIN
TABLE_DES_PUISSANCES_LIVREE = puissances_module._CHEMIN_TABLE
# La terre sans État des lignes sans pays de la table synthétique : la première de la table livrée.
TERRE_D_EPREUVE = json.loads(TABLE_DES_FRONTIERES_LIVREE.read_text(encoding="utf-8"))["terres_sans_etat"][0]["id"]
# Des points de la péninsule : Pampelune et Logroño tombent dans la même cellule de la carte
# figée, Estella aussi ; Burgos et Soria sont chacune dans une autre ; Lisbonne est loin de toutes.
PAMPELUNE = ("Pampelune", 42.82, -1.64)
LOGRONO = ("Logroño", 42.47, -2.45)
ESTELLA = ("Estella", 42.67, -2.03)
BURGOS = (42.34, -3.70)
SORIA = (41.77, -2.47)
LISBONNE = (38.72, -9.14)
SOURCE_SYNTHETIQUE = "table synthétique d'épreuve, sans valeur historique"


def _cellule_de(carte, lat, lon):
    point = projeter_epsg3035(lat, lon)
    cid = next((c for c in sorted(carte) if point_dans_geometrie(*point, carte[c]["geometry"])), None)
    assert cid is not None, f"({lat}, {lon}) : hors de la carte"
    return cid


def _ville(point, pays, raison=None):
    nom, lat, lon = point
    ville = {"nom": nom, "lat": lat, "lon": lon, "pays": pays, "source": SOURCE_SYNTHETIQUE}
    if pays is None:
        ville["raison"] = "ville sans pays d'épreuve" if raison is None else raison
        ville["terre"] = TERRE_D_EPREUVE
    return ville


def _document_synthetique(c):
    """La table livrée, trois cellules changées : celle de Burgos déclarée au Portugal, celle de Pampelune
    partagée entre la Navarre et la Castille, celle de Soria en lacune. Chacune vient en tête de sa liste,
    comme le témoin de Pampelune et le petit pays d'Andorre, pour que les retouches les visent."""
    document = json.loads(TABLE_DES_FRONTIERES_LIVREE.read_text(encoding="utf-8"))
    changees = {c.declaree, c.partagee, c.lacune}
    for ligne in document["pays"]:
        ligne["cellules"] = [cid for cid in ligne["cellules"] if cid not in changees]
    portugal = [cid for ligne in document["pays"] if ligne["pays"] == c.portugal for cid in ligne["cellules"]]
    document["pays"] = [{"pays": c.portugal, "source": SOURCE_SYNTHETIQUE, "cellules": [c.declaree] + portugal}] + [
        ligne for ligne in document["pays"] if ligne["cellules"] and ligne["pays"] != c.portugal]
    document["partages"] = [{"cell_id": c.partagee,
                             "villes": [_ville(PAMPELUNE, c.navarre), _ville(LOGRONO, c.castille)]}] + [
        ligne for ligne in document["partages"] if ligne["cell_id"] not in changees]
    document["lacunes"] = [{"cell_id": c.lacune, "terre": TERRE_D_EPREUVE, "raison": "cellule sans pays d'épreuve"}] + [
        ligne for ligne in document["lacunes"] if ligne["cell_id"] not in changees]
    document["regions"]["peninsule"] = [c.navarre, c.castille, c.portugal]
    document["temoins"] = [{"nom": "Pampelune", "lat": PAMPELUNE[1], "lon": PAMPELUNE[2], "pays": c.navarre,
                            "source": SOURCE_SYNTHETIQUE}] + [t for t in document["temoins"] if t["nom"] != "Pampelune"]
    document["petits_pays"] = sorted(document["petits_pays"], key=lambda ligne: ligne["nom"] != "Andorre")
    return document


@pytest.fixture(scope="module")
def partage(tmp_path_factory):
    """Le vrai monde chargé avec la table livrée, trois cellules changées : la cellule de Pampelune
    partagée entre la Navarre et la Castille, celle de Burgos déclarée au Portugal, celle de Soria en
    lacune."""
    document_carte = World.lire_carte()
    carte = {int(c["cell_id"]): c for c in document_carte["cellules"]}
    table = charger_table()
    pays = {p.nom: p.id for p in table.puissances}
    c = SimpleNamespace(
        navarre=pays["Navarre"], castille=pays["Castille"], portugal=pays["Portugal"],
        pays_inconnu=max(p.id for p in table.puissances) + 1, inconnue=max(carte) + 1,
        partagee=_cellule_de(carte, PAMPELUNE[1], PAMPELUNE[2]),
        declaree=_cellule_de(carte, *BURGOS), lacune=_cellule_de(carte, *SORIA))
    assert _cellule_de(carte, LOGRONO[1], LOGRONO[2]) == c.partagee == _cellule_de(carte, ESTELLA[1], ESTELLA[2])
    assert len({c.partagee, c.declaree, c.lacune}) == 3
    document = _document_synthetique(c)
    chemin = tmp_path_factory.mktemp("frontieres") / "frontieres-synthetiques.json"
    chemin.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    # Le chargement d'un monde attribue les maîtres d'après la table du chemin par défaut : le
    # chemin ne se déplace que le temps du chargement, puis revient à la table livrée.
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(frontieres_module, "_CHEMIN", chemin)
        monde = World.charger(0, carte_doc=document_carte)
    frontieres = charger_frontieres(chemin, table, monde.carte)
    livree = charger_frontieres(TABLE_DES_FRONTIERES_LIVREE, table, monde.carte)
    base = copy.copy(monde)
    base.maisons = charger_registre_maisons(monde.carte)
    vue = puissances_depuis_monde(monde, table=table, frontieres=frontieres)
    lieux = puissances_des_lieux(monde, table, frontieres)
    terres = terres_des_lieux(monde, table, frontieres)
    maisons = charger_maisons()
    seigneuries = charger_seigneuries(table=table)
    return SimpleNamespace(
        monde=monde, base=base, table=table, maisons=maisons, seigneuries=seigneuries, cellules=c,
        document=document, frontieres=frontieres, livree=livree, vue=vue, lieux=lieux, terres=terres,
        vue_livree=puissances_depuis_monde(monde, table=table, frontieres=livree),
        places=places_du_monde(monde), noms=noms_depuis_monde(monde, table=table, vue=vue),
        sources=SourcesDesPays(table, maisons, seigneuries, vue, lieux, terres))


# --- Les refus de charger_frontieres -----------------------------------------------------------

def _lire(tmp_path, document, partage):
    chemin = tmp_path / "frontieres.json"
    chemin.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    return charger_frontieres(chemin, partage.table, partage.monde.carte)


def _ajouter_un_pays(doc, pays, cellules):
    doc["pays"].append({"pays": pays, "source": SOURCE_SYNTHETIQUE, "cellules": cellules})


def _perdre(doc, cle):
    del doc[cle]


def _ville_au_portugal(doc, c):
    doc["partages"][0]["villes"][1].update(lat=LISBONNE[0], lon=LISBONNE[1])


# (nom du cas, retouche de la table valide, message qui nomme la ligne et le champ)
REFUS_DE_LA_TABLE = [
    ("cellule inconnue d'un pays",
     lambda d, c: d["pays"][0].update(cellules=[c.inconnue]),
     lambda c: f"cellule {c.inconnue}, champ cell_id : cellule inconnue"),
    ("cellule inconnue d'un partage",
     lambda d, c: d["partages"][0].update(cell_id=c.inconnue),
     lambda c: f"partage {c.inconnue}, champ cell_id : cellule inconnue"),
    ("cellule inconnue d'une lacune",
     lambda d, c: d["lacunes"][0].update(cell_id=c.inconnue),
     lambda c: f"lacune {c.inconnue}, champ cell_id : cellule inconnue"),
    ("cellule qui n'est pas un entier",
     lambda d, c: d["pays"][0].update(cellules=[str(c.declaree)]),
     lambda c: f"cellule '{c.declaree}', champ cell_id : entier attendu"),
    ("cellule déclarée à deux pays",
     lambda d, c: d["pays"][1]["cellules"].append(c.declaree),
     lambda c: f"cellule {c.declaree}, champ cell_id : cellule déclarée deux fois"),
    ("cellule déclarée à un pays et en lacune",
     lambda d, c: d["lacunes"].append({"cell_id": c.declaree, "raison": "d'épreuve"}),
     lambda c: f"lacune {c.declaree}, champ cell_id : cellule déclarée deux fois"),
    ("cellule déclarée à un pays et partagée",
     lambda d, c: d["partages"][0].update(cell_id=c.declaree),
     lambda c: f"partage {c.declaree}, champ cell_id : cellule déclarée deux fois"),
    ("cellule partagée et en lacune",
     lambda d, c: d["lacunes"][0].update(cell_id=c.partagee),
     lambda c: f"lacune {c.partagee}, champ cell_id : cellule déclarée deux fois"),
    ("pays déclaré deux fois",
     lambda d, c: _ajouter_un_pays(d, c.portugal, [c.partagee]),
     lambda c: f"pays {c.portugal}, champ pays : pays déclaré deux fois"),
    ("pays inconnu d'un pays",
     lambda d, c: d["pays"][0].update(pays=c.pays_inconnu),
     lambda c: f"pays {c.pays_inconnu}, champ pays : pays inconnu {c.pays_inconnu}"),
    ("pays booléen d'un pays",
     lambda d, c: d["pays"][0].update(pays=True),
     lambda c: "pays True, champ pays : pays inconnu True"),
    ("pays inconnu d'une ville de partage",
     lambda d, c: d["partages"][0]["villes"][1].update(pays=c.pays_inconnu),
     lambda c: f"partage {c.partagee}, champ pays : pays inconnu {c.pays_inconnu}"),
    ("pays inconnu d'un témoin",
     lambda d, c: d["temoins"][0].update(pays=c.pays_inconnu),
     lambda c: f"témoin 'Pampelune', champ pays : pays inconnu {c.pays_inconnu}"),
    ("pays inconnu d'une région",
     lambda d, c: d["regions"].update(peninsule=[c.pays_inconnu]),
     lambda c: f"région 'peninsule', champ pays : pays inconnu {c.pays_inconnu}"),
    ("source vide d'un pays",
     lambda d, c: d["pays"][0].update(source="  "),
     lambda c: f"pays {c.portugal}, champ source : texte absent ou vide"),
    ("source absente d'une ville de partage",
     lambda d, c: d["partages"][0]["villes"][0].pop("source"),
     lambda c: f"partage {c.partagee}, champ villes.{PAMPELUNE[0]}.source : texte absent ou vide"),
    ("source vide d'un témoin",
     lambda d, c: d["temoins"][0].update(source=""),
     lambda c: "témoin 'Pampelune', champ source : texte absent ou vide"),
    ("raison vide d'une lacune",
     lambda d, c: d["lacunes"][0].update(raison=""),
     lambda c: f"lacune {c.lacune}, champ raison : texte absent ou vide"),
    ("raison vide d'un petit pays",
     lambda d, c: d["petits_pays"][0].update(raison=" "),
     lambda c: "petit pays 'Andorre', champ raison : texte absent ou vide"),
    ("raison vide d'une ville sans pays",
     lambda d, c: d["partages"][0]["villes"].append(_ville(ESTELLA, None, raison="")),
     lambda c: f"partage {c.partagee}, champ villes.{ESTELLA[0]}.raison : texte absent ou vide"),
    ("ville de partage hors de sa cellule",
     _ville_au_portugal,
     lambda c: f"partage {c.partagee}, champ villes : {LOGRONO[0]} hors de sa cellule"),
    ("partage à une seule ville",
     lambda d, c: d["partages"][0].update(villes=d["partages"][0]["villes"][:1]),
     lambda c: f"partage {c.partagee}, champ villes : au moins deux pays attendus"),
    ("partage à deux villes du même pays",
     lambda d, c: d["partages"][0]["villes"][1].update(pays=c.navarre),
     lambda c: f"partage {c.partagee}, champ villes : au moins deux pays attendus"),
    ("partage à deux villes sans pays",
     lambda d, c: d["partages"][0].update(villes=[_ville(ESTELLA, None), _ville(ESTELLA, None)]),
     lambda c: f"partage {c.partagee}, champ villes : au moins deux pays attendus"),
    ("partage sans villes",
     lambda d, c: d["partages"][0].pop("villes"),
     lambda c: f"partage {c.partagee}, champ villes : au moins deux pays attendus"),
    ("latitude d'une ville qui n'est pas un nombre",
     lambda d, c: d["partages"][0]["villes"][0].update(lat="42"),
     lambda c: f"partage {c.partagee}, champ lat : nombre fini attendu"),
    ("date fausse",
     lambda d, c: d.update(date="1401-01-01"),
     lambda c: "frontières, champ date"),
    ("clé en trop",
     lambda d, c: d.update(supplement=[]),
     lambda c: "frontières : clés"),
    ("clé absente",
     lambda d, c: _perdre(d, "lacunes"),
     lambda c: "frontières : clés"),
    ("aucun témoin",
     lambda d, c: d.update(temoins=[]),
     lambda c: "frontières, champ temoins : liste vide"),
    ("cellule de la carte sans pays, partage ni lacune",
     lambda d, c: d["lacunes"].pop(0),
     lambda c: f"cellule {c.lacune}, champ cell_id : cellule de la carte sans pays, partage ni lacune"),
    ("lacune sans terre sans État",
     lambda d, c: d["lacunes"][0].pop("terre"),
     lambda c: f"lacune {c.lacune}, champ terre : texte absent ou vide"),
    ("lacune d'une terre sans État inconnue",
     lambda d, c: d["lacunes"][0].update(terre="inconnue"),
     lambda c: f"lacune {c.lacune}, champ terre : terre sans État inconnue 'inconnue'"),
    ("ville sans pays sans terre sans État",
     lambda d, c: d["partages"][0]["villes"].append({k: v for k, v in _ville(ESTELLA, None).items() if k != "terre"}),
     lambda c: f"partage {c.partagee}, champ villes.{ESTELLA[0]}.terre : texte absent ou vide"),
    ("ville sans pays d'une terre sans État inconnue",
     lambda d, c: d["partages"][0]["villes"].append({**_ville(ESTELLA, None), "terre": "inconnue"}),
     lambda c: f"partage {c.partagee}, champ villes.{ESTELLA[0]}.terre : terre sans État inconnue 'inconnue'"),
    ("terre sans État sur une ville qui a son pays",
     lambda d, c: d["partages"][0]["villes"][0].update(terre=TERRE_D_EPREUVE),
     lambda c: f"partage {c.partagee}, champ villes.{PAMPELUNE[0]}.terre : terre sur une ville qui a son pays"),
    ("terre sans État déclarée deux fois",
     lambda d, c: d["terres_sans_etat"].append(dict(d["terres_sans_etat"][0])),
     lambda c: f"terre sans État {TERRE_D_EPREUVE!r}, champ id : déclarée deux fois"),
    ("terre sans État que rien ne cite",
     lambda d, c: d["terres_sans_etat"].append({"id": "orpheline", "nom": "Orpheline", "raison": "terre d'épreuve"}),
     lambda c: "terre sans État 'orpheline', champ id : citée par aucune lacune ni ville"),
    ("nom vide d'une terre sans État",
     lambda d, c: d["terres_sans_etat"][0].update(nom=" "),
     lambda c: f"terre sans État {TERRE_D_EPREUVE!r}, champ nom : texte absent ou vide"),
    ("raison vide d'une terre sans État",
     lambda d, c: d["terres_sans_etat"][0].update(raison=""),
     lambda c: f"terre sans État {TERRE_D_EPREUVE!r}, champ raison : texte absent ou vide"),
]


def test_la_table_synthetique_valide_se_lit_et_garde_ses_lignes(partage, tmp_path):
    lue = _lire(tmp_path, partage.document, partage)
    c = partage.cellules
    assert lue.cellules[c.declaree] == c.portugal
    assert lue.lacunes[c.lacune] == "cellule sans pays d'épreuve"
    assert lue.terres_des_lacunes[c.lacune] == TERRE_D_EPREUVE and TERRE_D_EPREUVE in lue.terres_sans_etat
    assert [v.pays for v in lue.partages[c.partagee]] == [c.navarre, c.castille]
    assert lue.declarees() == set(partage.monde.carte)
    assert lue.temoins and lue.regions["peninsule"] == tuple(sorted((c.navarre, c.castille, c.portugal)))


def test_une_ville_sans_pays_dit_sa_raison_et_compte_pour_un_pays(partage, tmp_path):
    document = copy.deepcopy(partage.document)
    document["partages"][0]["villes"] = [_ville(PAMPELUNE, partage.cellules.navarre), _ville(ESTELLA, None)]
    lue = _lire(tmp_path, document, partage)
    sans_pays = [v for v in lue.partages[partage.cellules.partagee] if v.pays is None]
    assert [v.nom for v in sans_pays] == [ESTELLA[0]] and sans_pays[0].raison
    assert sans_pays[0].terre == TERRE_D_EPREUVE


@pytest.mark.parametrize("nom,retouche,message", REFUS_DE_LA_TABLE, ids=[cas[0] for cas in REFUS_DE_LA_TABLE])
def test_la_table_des_frontieres_refuse_et_nomme_la_ligne_et_le_champ(partage, tmp_path, nom, retouche, message):
    document = copy.deepcopy(partage.document)
    retouche(document, partage.cellules)
    with pytest.raises(PuissanceInvalide, match=re.escape(message(partage.cellules))):
        _lire(tmp_path, document, partage)


def test_les_refus_de_la_table_sont_nombreux_et_chacun_vient_de_sa_retouche(partage, tmp_path):
    # Contre-épreuve du paramétrage : la table sans retouche se lit, donc aucun refus ne vient d'ailleurs ;
    # et aucune retouche ne laisse la table inchangée.
    assert REFUS_DE_LA_TABLE, "échantillon vide"
    _lire(tmp_path, partage.document, partage)
    for nom, retouche, _ in REFUS_DE_LA_TABLE:
        document = copy.deepcopy(partage.document)
        retouche(document, partage.cellules)
        assert document != partage.document, f"{nom} : la retouche ne change rien"


def test_sans_carte_la_table_ne_juge_ni_les_cellules_ni_les_villes(partage, tmp_path):
    # La carte fait refuser une cellule inconnue, une ville hors de sa cellule et une cellule de la carte
    # sans pays, partage ni lacune ; sans elle, ces refus manquent, et les autres restent.
    c = partage.cellules
    chemin = tmp_path / "frontieres.json"
    for retouche, refus in (
            (lambda d: d["pays"][0]["cellules"].append(c.inconnue), "cellule inconnue"),
            (lambda d: _ville_au_portugal(d, c), "hors de sa cellule"),
            (lambda d: d["lacunes"].pop(0), "cellule de la carte sans pays, partage ni lacune")):
        document = copy.deepcopy(partage.document)
        retouche(document)
        chemin.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        assert charger_frontieres(chemin, partage.table).declarees()
        with pytest.raises(PuissanceInvalide, match=refus):
            charger_frontieres(chemin, partage.table, partage.monde.carte)


def test_un_monde_partiel_refuse_une_de_ses_cellules_que_la_table_ne_decide_pas(partage, tmp_path):
    # Un monde d'épreuve qui ne porte qu'une part de la carte : la table sans la lacune de Soria se lit
    # sur une part qui ne contient pas Soria, et se refuse, en la nommant, sur une part qui la contient.
    c = partage.cellules
    document = copy.deepcopy(partage.document)
    document["lacunes"].pop(0)
    chemin = tmp_path / "frontieres.json"
    chemin.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    carte = partage.monde.carte
    sans_soria = {cid: carte[cid] for cid in (c.partagee, c.declaree)}
    assert charger_frontieres(chemin, partage.table, sans_soria, partielle=True).declarees() >= set(sans_soria)
    with pytest.raises(PuissanceInvalide, match=f"cellule {c.lacune}, champ cell_id"):
        charger_frontieres(chemin, partage.table, {**sans_soria, c.lacune: carte[c.lacune]}, partielle=True)


def test_la_table_livree_se_lit_sans_refus(partage):
    livree = charger_frontieres(TABLE_DES_FRONTIERES_LIVREE, partage.table, partage.monde.carte)
    assert livree.temoins, "échantillon vide"
    assert livree.regions and livree.date == "1400-01-01"
    assert livree.declarees() == set(partage.monde.carte)


# --- Les refus du suzerain d'une puissance -----------------------------------------------------

def _puissances_retouchees(tmp_path, retouche):
    document = json.loads(TABLE_DES_PUISSANCES_LIVREE.read_text(encoding="utf-8"))
    retouche({p["id"]: p for p in document["puissances"]})
    chemin = tmp_path / "puissances.json"
    chemin.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    return charger_table(chemin)


def _puissance(table, nom):
    return next(p.id for p in table.puissances if p.nom == nom)


def _suzerain(ligne, suzerain, source=SOURCE_SYNTHETIQUE):
    ligne["suzerain"] = suzerain
    if source is None:
        ligne.pop("source_suzerain", None)
    else:
        ligne["source_suzerain"] = source


def test_un_suzerain_valide_se_lit_et_les_autres_puissances_n_en_gagnent_pas(partage, tmp_path):
    table = partage.table
    milan, empire, bohme = _puissance(table, "Milan"), _puissance(table, "Saint-Empire"), _puissance(table, "Bohême")
    lue = _puissances_retouchees(tmp_path, lambda p: _suzerain(p[milan], empire))
    par_id = {p.id: p.suzerain for p in lue.puissances}
    avant = {p.id: p.suzerain for p in table.puissances}
    assert par_id[milan] == empire
    assert {i: s for i, s in par_id.items() if i != milan} == {i: s for i, s in avant.items() if i != milan}
    # Une chaîne de deux suzerains (Milan sous la Bohême, sous le Saint-Empire) n'est pas un cycle.
    chaine = _puissances_retouchees(tmp_path, lambda p: (_suzerain(p[milan], bohme), _suzerain(p[bohme], empire)))
    assert {p.id: p.suzerain for p in chaine.puissances}[milan] == bohme


def _refus_du_suzerain(partage):
    table = partage.table
    milan, empire = _puissance(table, "Milan"), _puissance(table, "Saint-Empire")
    inconnue = max(p.id for p in table.puissances) + 1
    return [
        ("suzerain inconnu", lambda p: _suzerain(p[milan], inconnue),
         f"puissance {milan}, champ suzerain : puissance inconnue"),
        ("suzerain booléen", lambda p: _suzerain(p[milan], True),
         f"puissance {milan}, champ suzerain : entier attendu"),
        ("suzerain en texte", lambda p: _suzerain(p[milan], str(empire)),
         f"puissance {milan}, champ suzerain : entier attendu"),
        ("suzerain nul", lambda p: _suzerain(p[milan], None),
         f"puissance {milan}, champ suzerain : entier attendu"),
        ("suzerain d'elle-même", lambda p: _suzerain(p[milan], milan),
         f"puissance {milan}, champ suzerain : cycle"),
        ("cycle à deux", lambda p: (_suzerain(p[milan], empire), _suzerain(p[empire], milan)),
         rf"puissance ({milan}|{empire}), champ suzerain : cycle"),
        ("source du suzerain absente", lambda p: _suzerain(p[milan], empire, source=None),
         f"puissance {milan}, champ source_suzerain : texte absent ou vide"),
        ("source du suzerain vide", lambda p: _suzerain(p[milan], empire, source="  "),
         f"puissance {milan}, champ source_suzerain : texte absent ou vide"),
    ]


def test_le_suzerain_d_une_puissance_est_refuse_s_il_est_faux(partage, tmp_path):
    cas = _refus_du_suzerain(partage)
    assert len(cas) > 1, "échantillon vide"
    for nom, retouche, message in cas:
        # Un message d'une regex (le cycle à deux) ou d'un texte : les deux se lisent comme une regex.
        with pytest.raises(PuissanceInvalide, match=message):
            _puissances_retouchees(tmp_path, retouche)


# --- Un partage synthétique sur le vrai monde --------------------------------------------------

def _rangs_du_pays(partage, pays):
    cid = partage.cellules.partagee
    return [rang for rang in range(len(partage.monde.cells[cid].lieux)) if partage.lieux[cid, rang] == pays]


def test_chaque_lieu_d_une_cellule_partagee_prend_le_pays_de_la_ville_la_plus_proche(partage):
    cid, c = partage.cellules.partagee, partage.cellules
    villes = partage.frontieres.partages[cid]
    nombre = len(partage.monde.cells[cid].lieux)
    assert nombre > 1 and {k for k in partage.lieux if k[0] == cid} == {(cid, rang) for rang in range(nombre)}
    for rang, place in enumerate(partage.places[cid]):
        assert partage.lieux[cid, rang] == _pays_le_plus_proche(place, villes), rang
    assert {partage.lieux[cid, rang] for rang in range(nombre)} == {c.navarre, c.castille}
    # Contre-épreuve : les deux villes échangent leurs pays, chaque lieu passe de l'autre côté.
    echange = {c.navarre: c.castille, c.castille: c.navarre}
    inversees = dataclasses.replace(partage.frontieres, partages={cid: tuple(
        dataclasses.replace(v, pays=echange[v.pays]) for v in villes)})
    inverses = puissances_des_lieux(partage.monde, partage.table, inversees)
    assert all(inverses[cid, rang] == echange[partage.lieux[cid, rang]] for rang in range(nombre))


def test_le_bourg_partage_est_au_pays_de_sa_ville_la_plus_proche_du_siege(partage):
    # Le bourg est placé au siège de la maison du bourg (Pampelune) : il est navarrais.
    cid, c = partage.cellules.partagee, partage.cellules
    assert maison_du_bourg(partage.monde, cid) == f"grande-{partage.maisons.par_puissance[c.navarre]}"
    assert partage.lieux[cid, 0] == c.navarre


def test_la_puissance_d_une_cellule_est_celle_de_son_bourg_ou_celle_que_la_table_declare(partage):
    c = partage.cellules
    assert partage.vue[c.partagee] == partage.lieux[c.partagee, 0] == c.navarre
    assert partage.vue[c.declaree] == c.portugal
    assert partage.vue[c.lacune] is None
    # Contre-épreuve : avec la table livrée, ces trois cellules ont leurs pays de 1400, et la table d'épreuve
    # ne change qu'elles.
    assert partage.vue_livree[c.declaree] != c.portugal and partage.vue_livree[c.lacune] is not None
    assert {k for k in partage.vue if partage.vue[k] != partage.vue_livree[k]} <= {c.partagee, c.declaree, c.lacune}
    # Quelles que soient les ancres : celles du Portugal et de la Castille échangées, la table décide encore.
    echange = {c.portugal: c.castille, c.castille: c.portugal}
    ancres = tuple(dataclasses.replace(a, puissance=echange.get(a.puissance, a.puissance))
                   for a in partage.table.ancres)
    echangee = dataclasses.replace(partage.table, ancres=ancres)
    assert puissances_depuis_monde(partage.monde, table=echangee, frontieres=partage.frontieres) == partage.vue
    assert decisions_des_frontieres(partage.monde, partage.table, partage.frontieres, partage.lieux) == partage.vue


def test_la_maison_de_chaque_cellule_suit_son_pays(partage):
    c = partage.cellules
    par_puissance = partage.maisons.par_puissance
    suivie = maisons_depuis_monde(partage.monde, table=partage.table, frontieres=partage.frontieres)
    assert suivie[c.partagee] == par_puissance[c.navarre]
    assert suivie[c.declaree] == par_puissance[c.portugal]
    assert suivie[c.lacune] is None
    # Contre-épreuve : avec la table livrée, la cellule déclarée est castillane et celle de la lacune a une maison.
    livree = maisons_depuis_monde(partage.monde, table=partage.table, frontieres=partage.livree)
    assert livree[c.declaree] != suivie[c.declaree] and livree[c.lacune] is not None


def test_les_maitres_d_une_cellule_partagee_suivent_le_pays_de_chaque_lieu(partage):
    s, c = partage, partage.cellules
    cid = c.partagee
    maitres, plausibles = attribuer_maitres(s.base, s.vue, s.maisons, s.lieux)
    # Le monde chargé a reçu cette attribution.
    assert {(i, l.rang): l.maitre for i, cellule in s.monde.cells.items() for l in cellule.lieux} == maitres
    navarrais, castillans = _rangs_du_pays(s, c.navarre), _rangs_du_pays(s, c.castille)
    assert navarrais and castillans, "échantillon vide"
    tete = f"grande-{s.maisons.par_puissance[c.navarre]}"
    assert tete == "grande-7" and s.monde.cells[cid].lieux[0].maitre == tete
    # La grande maison de Navarre ne tient que des lieux navarrais, et tient tous ceux-là.
    assert {rang for (i, rang), m in maitres.items() if i == cid and m == tete} == set(navarrais)
    groupes = [p for p in plausibles if p.cell_id == cid]
    assert groupes, "échantillon vide"
    tenus = {p.id: [rang for rang in sorted(r for (i, r) in maitres if i == cid) if maitres[cid, rang] == p.id]
             for p in groupes}
    for plausible in groupes:
        rangs = tenus[plausible.id]
        assert rangs and len(rangs) <= constantes.LIEUX_PAR_SEIGNEUR_PLAUSIBLE and plausible.rang == rangs[0]
        pays = {s.lieux[cid, rang] for rang in rangs}
        assert len(pays) == 1, f"{plausible.id} tient des lieux de plusieurs pays : {pays}"
        racine = s.maisons.par_puissance[pays.pop()]
        assert plausible.suzerain == f"grande-{racine}", plausible.id
    assert sorted(r for rangs in tenus.values() for r in rangs) == sorted(castillans)
    valider_attribution(s.base, maitres, plausibles, s.vue, s.maisons, s.lieux)


def test_une_attribution_faite_sans_les_lieux_du_partage_est_refusee(partage):
    s, c = partage, partage.cellules
    maitres, plausibles = attribuer_maitres(s.base, s.vue, s.maisons, s.lieux)
    # Contre-épreuve : sans la puissance des lieux, la Navarre prend toute la cellule.
    sans_partage, _ = attribuer_maitres(s.base, s.vue, s.maisons, {})
    assert sans_partage != maitres
    assert {sans_partage[c.partagee, rang] for rang in range(len(s.monde.cells[c.partagee].lieux))} == {"grande-7"}
    with pytest.raises(AttributionInvalide, match="maître différent de la règle"):
        valider_attribution(s.base, maitres, plausibles, s.vue, s.maisons, {})
    # Un partage faussé (chaque lieu de la cellule de Pampelune hors du bourg passe à l'autre pays) change
    # les maîtres.
    echange = {c.navarre: c.castille, c.castille: c.navarre}
    faux = {k: (echange[v] if k[0] == c.partagee and k[1] != 0 else v) for k, v in s.lieux.items()}
    faussee, _ = attribuer_maitres(s.base, s.vue, s.maisons, faux)
    assert faussee != maitres
    with pytest.raises(AttributionInvalide):
        valider_attribution(s.base, maitres, plausibles, s.vue, s.maisons, faux)


def test_un_lieu_sans_pays_se_groupe_a_part_et_ne_releve_de_personne(partage):
    s, cid = partage, partage.cellules.partagee
    nombre = len(s.monde.cells[cid].lieux)
    sans_pays = {k: (v if k[1] == 0 else None) for k, v in s.lieux.items()}
    maitres, plausibles = attribuer_maitres(s.base, s.vue, s.maisons, sans_pays)
    assert [rang for rang in range(nombre) if maitres[cid, rang] == "grande-7"] == [0]
    groupes = [p for p in plausibles if p.cell_id == cid]
    assert groupes and all(p.suzerain is None for p in groupes)
    tenus = Counter(maitres[cid, rang] for rang in range(1, nombre))
    assert set(tenus) == {p.id for p in groupes}
    assert max(tenus.values()) == constantes.LIEUX_PAR_SEIGNEUR_PLAUSIBLE
    assert sum(tenus.values()) == nombre - 1


def test_une_seigneurie_de_depart_garde_ses_lieux_meme_dans_une_cellule_partagee(partage):
    s = partage
    depart = constantes.LIEUX_DE_LA_SEIGNEURIE
    seigneurie = next((m for m in sorted(s.base.maisons, key=lambda m: m.id)
                       if m.sorte == "seigneurie" and len(s.monde.cells[m.cell_id].lieux) > depart
                       and maison_du_bourg(s.base, m.cell_id) == m.id), None)
    assert seigneurie is not None, "échantillon vide : aucune seigneurie dans une cellule de plus de 4 lieux"
    cid = seigneurie.cell_id
    nombre = len(s.monde.cells[cid].lieux)
    # Tous les lieux de la cellule vont au pays de la Castille, que la seigneurie ne tient pas.
    partages = {(cid, rang): s.cellules.castille for rang in range(nombre)}
    maitres, _ = attribuer_maitres(s.base, s.vue, s.maisons, partages)
    assert [maitres[cid, rang] for rang in range(depart)] == [seigneurie.id] * depart
    assert all(maitres[cid, rang] != seigneurie.id for rang in range(depart, nombre))


def test_les_lieux_et_les_terres_servent_les_deux_pays_d_une_cellule_partagee(partage):
    s, c = partage, partage.cellules
    cid = c.partagee
    lieux = s.monde.cells[cid].lieux
    pays_de_lieux = pays_des_lieux(s.monde, s.vue, s.maisons, s.lieux, s.terres)
    for lieu in lieux:
        assert pays_de_lieux[cid, lieu.rang] == identifiant_de_puissance(s.lieux[cid, lieu.rang]), lieu.rang
    assert {pays_de_lieux[cid, lieu.rang] for lieu in lieux} == {identifiant_de_puissance(c.navarre),
                                                                 identifiant_de_puissance(c.castille)}
    servie = terres_et_pays(s.monde, SimpleNamespace(noms=s.noms), s.sources)
    terre = next(t for t in servie["terres"] if t["cell_id"] == cid)
    assert terre["pays"] == identifiant_de_puissance(c.navarre)
    castillans = _rangs_du_pays(s, c.castille)
    assert terre["autres_pays"] == [
        {"rang": rang, "maitre": lieux[rang].maitre, "pays": identifiant_de_puissance(c.castille)}
        for rang in castillans]
    fiches = {f["id"]: f for f in servie["pays"]}
    assert fiches[identifiant_de_puissance(c.castille)]["nom"] == "Castille"
    assert fiches[identifiant_de_puissance(c.navarre)]["nom"] == "Navarre"
    # Hors des cellules partagées, une terre ne porte un lieu d'un autre pays que si son bourg est une
    # terre de départ : les seigneurs d'une lacune ne sont pas des pays, tous ses lieux sont à sa terre
    # sans État.
    par_id = {m.id: m for m in s.monde.maisons}
    autres = {t["cell_id"] for t in servie["terres"] if t["autres_pays"]}
    explique = {t["cell_id"] for t in servie["terres"] if par_id[t["maitre"]].sorte == "seigneurie"}
    assert cid in autres and autres - set(s.frontieres.partages) <= explique and c.declaree not in autres
    lacune = next(t for t in servie["terres"] if t["cell_id"] == c.lacune)
    assert lacune["pays"] == identifiant_de_terre(TERRE_D_EPREUVE) and not lacune["autres_pays"]
    assert {pays_de_lieux[c.lacune, l.rang] for l in s.monde.cells[c.lacune].lieux} == {lacune["pays"]}
    assert next(t for t in servie["terres"] if t["cell_id"] == c.declaree)["pays"] == identifiant_de_puissance(c.portugal)


def test_le_pays_d_un_lieu_hors_cellule_partagee_est_celui_de_sa_cellule(partage):
    s = partage
    assert s.lieux and all(cid in s.frontieres.partages for cid, _ in s.lieux)
    cid = s.cellules.declaree
    assert puissance_du_lieu(cid, 0, s.vue, s.lieux) == s.cellules.portugal
    assert puissance_du_lieu(s.cellules.lacune, 0, s.vue, s.lieux) is None
    # Contre-épreuve : dans la cellule partagée, le lieu prend son pays propre, pas celui de la cellule.
    castillans = _rangs_du_pays(s, s.cellules.castille)
    assert puissance_du_lieu(s.cellules.partagee, castillans[0], s.vue, s.lieux) == s.cellules.castille
    assert s.vue[s.cellules.partagee] == s.cellules.navarre
    assert puissance_du_lieu(s.cellules.partagee, castillans[0], s.vue, None) == s.cellules.navarre


# --- Le suzerain servi -------------------------------------------------------------------------

def _avec_milan_sous_l_empire(partage, tmp_path):
    table = partage.table
    milan, empire = _puissance(table, "Milan"), _puissance(table, "Saint-Empire")
    lue = _puissances_retouchees(tmp_path, lambda p: _suzerain(p[milan], empire))
    sources = SourcesDesPays(lue, partage.maisons, charger_seigneuries(table=lue), partage.vue, partage.lieux,
                             partage.terres)
    return lue, sources, milan, empire


def test_la_fiche_d_une_puissance_sert_le_suzerain_que_la_table_declare(partage, tmp_path):
    s = partage
    table, sources, milan, empire = _avec_milan_sous_l_empire(s, tmp_path)
    matiere = SimpleNamespace(noms=s.noms)
    ids = {identifiant_de_puissance(milan), identifiant_de_puissance(_puissance(table, "France"))}
    fiches = {f["id"]: f for f in fiches_des_pays(ids, s.monde, table, sources.maisons, sources.seigneuries, matiere)}
    assert fiches[identifiant_de_puissance(milan)]["suzerain"] == identifiant_de_puissance(empire)
    # La fiche du suzerain est servie avec celle du vassal, sans suzerain elle-même.
    assert fiches[identifiant_de_puissance(empire)]["nom"] == "Saint-Empire"
    assert fiches[identifiant_de_puissance(empire)]["suzerain"] is None
    assert fiches[identifiant_de_puissance(_puissance(table, "France"))]["suzerain"] is None
    # Contre-épreuve : la même table sans le suzerain de Milan ne sert ni suzerain ni fiche du suzerain.
    sans = dataclasses.replace(table, puissances=tuple(
        dataclasses.replace(p, suzerain=None) for p in table.puissances))
    sans_fiches = {f["id"]: f for f in fiches_des_pays(
        ids, s.monde, sans, sources.maisons, sources.seigneuries, matiere)}
    assert sans_fiches[identifiant_de_puissance(milan)]["suzerain"] is None
    assert identifiant_de_puissance(empire) not in sans_fiches


def test_un_jouable_sert_le_suzerain_de_son_pays_et_un_autre_n_en_a_pas(partage, tmp_path):
    s = partage
    table, sources, milan, empire = _avec_milan_sous_l_empire(s, tmp_path)
    par_id = {m["id"]: m for m in maisons_jouables(s.monde, sources, s.noms)}
    visconti, valois = par_id[f"grande-{s.maisons.par_puissance[milan]}"], par_id[
        f"grande-{s.maisons.par_puissance[_puissance(table, 'France')]}"]
    assert visconti["pays"]["id"] == identifiant_de_puissance(milan)
    tete = f"grande-{s.maisons.par_puissance[empire]}"
    fiche_empire = next(m for m in maisons_jouables(s.monde, sources, s.noms) if m["id"] == tete)
    assert fiche_empire["nom"]
    assert visconti["suzerain"] == {"id": tete, "nom": fiche_empire["nom"],
                                    "pays": {"id": identifiant_de_puissance(empire), "nom": "Saint-Empire"}}
    assert valois["suzerain"] is None
    # Contre-épreuve : sans le suzerain déclaré, Visconti n'en sert pas.
    sans = dataclasses.replace(table, puissances=tuple(
        dataclasses.replace(p, suzerain=None) for p in table.puissances))
    sans_sources = dataclasses.replace(sources, table=sans)
    assert {m["id"]: m for m in maisons_jouables(s.monde, sans_sources, s.noms)}[visconti["id"]]["suzerain"] is None


# --- L'ensemble d'une puissance ------------------------------------------------------------------

def _ensemble(ligne, ensemble, source=SOURCE_SYNTHETIQUE):
    ligne["ensemble"] = ensemble
    if source is None:
        ligne.pop("source_ensemble", None)
    else:
        ligne["source_ensemble"] = source


def _source_sans_ensemble(ligne):
    ligne.pop("ensemble", None)
    ligne["source_ensemble"] = SOURCE_SYNTHETIQUE


def _refus_de_l_ensemble(partage):
    milan = _puissance(partage.table, "Milan")
    vide = f"puissance {milan}, champ ensemble : texte absent ou vide"
    sans_source = f"puissance {milan}, champ source_ensemble : texte absent ou vide"
    return [
        ("ensemble vide", lambda p: _ensemble(p[milan], "  "), vide),
        ("ensemble nul", lambda p: _ensemble(p[milan], None), vide),
        ("ensemble en nombre", lambda p: _ensemble(p[milan], 9), vide),
        ("source absente", lambda p: _ensemble(p[milan], EMPIRE, source=None), sans_source),
        ("source vide", lambda p: _ensemble(p[milan], EMPIRE, source=" "), sans_source),
        ("source sans ensemble", lambda p: _source_sans_ensemble(p[milan]),
         f"puissance {milan}, champ ensemble : source sans ensemble"),
    ]


def test_l_ensemble_d_une_puissance_est_refuse_s_il_est_faux(partage, tmp_path):
    cas = _refus_de_l_ensemble(partage)
    assert len(cas) > 1, "échantillon vide"
    for nom, retouche, message in cas:
        with pytest.raises(PuissanceInvalide, match=re.escape(message)):
            _puissances_retouchees(tmp_path, retouche)
    # Contre-épreuve : un ensemble et sa source valides se lisent.
    milan = _puissance(partage.table, "Milan")
    lue = _puissances_retouchees(tmp_path, lambda p: _ensemble(p[milan], EMPIRE))
    assert {p.id: p.ensemble for p in lue.puissances}[milan] == EMPIRE


def test_l_ensemble_se_sert_dans_la_fiche_du_pays_sans_rien_changer_au_monde(partage, tmp_path):
    s = partage
    milan, france = _puissance(s.table, "Milan"), _puissance(s.table, "France")
    lue = _puissances_retouchees(tmp_path, lambda p: (_ensemble(p[milan], EMPIRE),
                                                      p[france].pop("ensemble", None),
                                                      p[france].pop("source_ensemble", None)))
    sans = dataclasses.replace(lue, puissances=tuple(dataclasses.replace(p, ensemble=None) for p in lue.puissances))
    matiere = SimpleNamespace(noms=s.noms)
    depart = identifiant_de_seigneurie(s.seigneuries[0].id)
    ids = {identifiant_de_puissance(milan), identifiant_de_puissance(france), depart}

    def fiches(table):
        return {f["id"]: f for f in fiches_des_pays(ids, s.monde, table, s.maisons, s.seigneuries, matiere)}

    avec, sans_fiches = fiches(lue), fiches(sans)
    assert avec[identifiant_de_puissance(milan)]["ensemble"] == EMPIRE
    # Une puissance sans ensemble, une terre de départ, leurs suzerains n'en disent pas.
    assert all(f["ensemble"] is None for i, f in avec.items() if i != identifiant_de_puissance(milan))
    assert avec[depart]["suzerain"] in avec
    # Contre-épreuve : sans l'ensemble, la fiche de Milan n'en dit pas, et rien d'autre ne change.
    assert sans_fiches[identifiant_de_puissance(milan)]["ensemble"] is None
    assert {i: dict(f, ensemble=None) for i, f in avec.items()} == sans_fiches
    # L'ensemble n'a aucun effet dans le moteur : la vue des puissances et celle des maisons sont les mêmes.
    assert puissances_depuis_monde(s.monde, table=lue, frontieres=s.frontieres) == \
        puissances_depuis_monde(s.monde, table=sans, frontieres=s.frontieres)
    assert maisons_depuis_monde(s.monde, table=lue, frontieres=s.frontieres) == \
        maisons_depuis_monde(s.monde, table=sans, frontieres=s.frontieres)
