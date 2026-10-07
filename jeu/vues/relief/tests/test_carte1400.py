"""Preuves et contre-épreuves sur deux vraies photographies de 1400."""

import copy
import random

import numpy as np
import pytest

from sim.engine import tick
from sim.intentions import TYPE_CHOISIR_DEPART, deposer_intention
from sim.seigneuries import charger_seigneuries
from sim.snapshot_export import build_snapshot_document
from sim.world import World
from vues.relief.lectures import LECTURES, LectureErreur
from vues.relief.raster import index_des_cellules
from vues.relief.statistique import _sans_accent, carte_de_statistique, plan_avec_legende

LARGEUR = 900


@pytest.fixture(scope="module")
def photographies():
    monde = World.charger(0)
    sans = build_snapshot_document(monde, 0, 0)
    terres = charger_seigneuries()
    assert terres, "échantillon vide : aucune terre"
    bar = next(t.id for t in terres if t.nom == "Duché de Bar")
    deposer_intention(monde, {"type": TYPE_CHOISIR_DEPART, "seigneurie": bar})
    tick(monde, random.Random(0))
    avec = build_snapshot_document(monde, 0, 1)
    assert sans["cells"] and avec["terre_choisie"]
    return sans, avec


def _rendre(document):
    from vues.relief.carte1400 import carte_de_1400

    return carte_de_1400(document, lecture="densite", largeur=LARGEUR)


def test_densite_lue_sans_division(photographies):
    document, _ = photographies
    cellules = document["cells"]
    assert cellules
    for cellule in cellules:
        assert LECTURES["densite"].valeur(cellule) == cellule["densite_hab_par_km2"]
    sonde = copy.deepcopy(cellules[0])
    del sonde["densite_hab_par_km2"]
    assert "population" in sonde and "area_km2" in sonde
    assert LECTURES["densite"].valeur(sonde) is None
    ancien = copy.deepcopy(document)
    for cellule in ancien["cells"]:
        del cellule["densite_hab_par_km2"]
    with pytest.raises(LectureErreur, match="portée par aucune cellule"):
        carte_de_statistique(ancien, lecture="densite", largeur=LARGEUR)
    print(f"densités_lues={len(cellules)}, absences_refusées=1")


def test_densite_image_invariante_et_contre_epreuve(photographies):
    document, _ = photographies
    image, _ = _rendre(document)
    sonde = copy.deepcopy(document)
    for cellule in sonde["cells"]:
        cellule["population"] *= 2
    assert np.array_equal(image, _rendre(sonde)[0])
    altere = copy.deepcopy(document)
    altere["cells"][0]["densite_hab_par_km2"] = 10 * max(
        c["densite_hab_par_km2"] for c in document["cells"]
    )
    autre, _ = _rendre(altere)
    with pytest.raises(AssertionError):
        assert np.array_equal(image, autre)
    print(f"pixels_comparés={image.shape[0] * image.shape[1]}, contre_épreuves_rouges=1")


def _compter_frontiere(document):
    index, _, cellules = index_des_cellules(document, largeur=LARGEUR)
    cles = np.array([-1] + [c["puissance"]["id"] if c["puissance"] else -1 for c in cellules])
    puissances = cles[index]
    masque = np.zeros(index.shape, dtype=bool)
    for a, b in ((np.s_[:, :-1], np.s_[:, 1:]), (np.s_[:-1, :], np.s_[1:, :])):
        masque[a] |= (index[a] > 0) & (index[b] > 0) & (puissances[a] != puissances[b])
    return int(masque.sum())


def test_frontiere_et_cellules_sans_puissance(photographies):
    document, _ = photographies
    _, compte = _rendre(document)
    puissances = {c["puissance"]["id"] for c in document["cells"] if c["puissance"]}
    sans = sum(c["puissance"] is None for c in document["cells"])
    assert puissances and sans > 0
    assert compte["puissances"] == len(puissances)
    assert compte["cellules_sans_puissance"] == sans
    assert compte["pixels_de_frontiere"] == _compter_frontiere(document) > 0
    unifie = copy.deepcopy(document)
    puissance = next(c["puissance"] for c in document["cells"] if c["puissance"])
    for cellule in unifie["cells"]:
        cellule["puissance"] = copy.deepcopy(puissance)
    _, autre = _rendre(unifie)
    assert autre["pixels_de_frontiere"] == 0
    with pytest.raises(AssertionError):
        assert autre["pixels_de_frontiere"] > 0
    print(f"frontières={compte['pixels_de_frontiere']}, puissances={len(puissances)}, sans={sans}, contre_épreuves_rouges=1")


def test_frontiere_change_avec_un_voisin_documente(photographies):
    document, _ = photographies
    index, _, cellules = index_des_cellules(document, largeur=LARGEUR)
    couples = set()
    for a, b in ((index[:, :-1], index[:, 1:]), (index[:-1], index[1:])):
        terre = (a > 0) & (b > 0) & (a != b)
        couples.update(zip(a[terre].tolist(), b[terre].tolist()))
    candidats = sorted((a, b) for a, b in couples if cellules[a - 1]["puissance"]
                       and cellules[b - 1]["puissance"]
                       and cellules[a - 1]["puissance"] != cellules[b - 1]["puissance"])
    assert candidats, "échantillon vide : aucun voisin de puissance différente"
    reference = _compter_frontiere(document)
    for a, b in candidats:
        altere = copy.deepcopy(document)
        altere["cells"][a - 1]["puissance"] = copy.deepcopy(cellules[b - 1]["puissance"])
        if _compter_frontiere(altere) != reference:
            break
    else:
        pytest.fail("aucune réattribution ne change la frontière")
    _, compte = _rendre(altere)
    assert compte["pixels_de_frontiere"] == _compter_frontiere(altere)
    with pytest.raises(AssertionError):
        assert compte["pixels_de_frontiere"] == reference
    print(f"voisins_candidats={len(candidats)}, avant={reference}, après={compte['pixels_de_frontiere']}, contre_épreuves_rouges=1")


def test_villes_et_contre_epreuve(photographies):
    document, _ = photographies
    image, compte = _rendre(document)
    villes = sum(len(c["villes"]) for c in document["cells"])
    assert villes > 0
    assert compte["villes_dessinees"] == villes
    assert compte["cellules_avec_villes"] == sum(bool(c["villes"]) for c in document["cells"])
    assert compte["villes_hors_carte"] == document["villes_hors_carte"]
    assert isinstance(compte["etiquettes_omises"], int) and compte["etiquettes_omises"] >= 0
    vide = copy.deepcopy(document)
    for cellule in vide["cells"]:
        cellule["villes"] = []
    autre, rapport = _rendre(vide)
    assert rapport["villes_dessinees"] == 0
    with pytest.raises(AssertionError):
        assert np.array_equal(image, autre)
    print(f"villes={villes}, étiquettes_omises={compte['etiquettes_omises']}, contre_épreuves_rouges=1")


def test_fiche_choisie_et_bord_dans_sa_cellule(photographies):
    from vues.relief.carte1400 import COULEUR_CHOIX, lignes_de_fiche

    sans, avec = photographies
    image, rapport = _rendre(sans)
    assert lignes_de_fiche(sans)[0].startswith("Terre choisie : aucune")
    assert rapport["terre_choisie"] is None
    assert not np.all(image == COULEUR_CHOIX, axis=-1).any()
    image, rapport = _rendre(avec)
    fiche = "\n".join(_sans_accent(l) for l in lignes_de_fiche(avec))
    terre = avec["terre_choisie"]
    for texte in (terre["nom"], terre["suzerain"]["nom"], str(terre["habitants"]),
                  str(terre["cell_id"]), *avec["villes_hors_carte"]):
        assert _sans_accent(texte) in fiche
    assert rapport["terre_choisie"] == terre["id"]
    index, _, cellules = index_des_cellules(avec, largeur=LARGEUR)
    hauteur_legende = len(plan_avec_legende(carte_de_statistique(avec, lecture="densite", largeur=LARGEUR))) - len(index)
    rouges = np.all(image == COULEUR_CHOIX, axis=-1)
    bord = rouges[hauteur_legende:hauteur_legende + len(index)]
    assert bord.any() and rouges.sum() == bord.sum()
    rang = next(i for i, c in enumerate(cellules, 1) if c["cell_id"] == terre["cell_id"])
    assert np.all(index[bord] == rang)
    print(f"fiche_lignes={len(lignes_de_fiche(avec))}, bord_rouge={int(bord.sum())}")


def test_fiche_lit_les_habitants_sans_recompter(photographies):
    from vues.relief.carte1400 import lignes_de_fiche

    _, document = photographies
    reference = lignes_de_fiche(document)
    altere = copy.deepcopy(document)
    altere["terre_choisie"]["habitants"] += 1
    lignes = lignes_de_fiche(altere)
    assert str(altere["terre_choisie"]["habitants"]) in "\n".join(lignes)
    with pytest.raises(AssertionError):
        assert lignes == reference
    print(f"habitants_lus={altere['terre_choisie']['habitants']}, contre_épreuves_rouges=1")


@pytest.mark.parametrize("cle", ["puissance", "villes", "terre_choisie", "villes_hors_carte", "cell_id"])
def test_refus_photographie_incomplete(photographies, cle):
    from vues.relief.carte1400 import Carte1400Erreur

    _, document = photographies
    altere = copy.deepcopy(document)
    if cle in ("puissance", "villes"):
        del altere["cells"][0][cle]
    elif cle == "cell_id":
        altere["terre_choisie"][cle] = max(c[cle] for c in document["cells"]) + 1
    else:
        del altere[cle]
    with pytest.raises(Carte1400Erreur, match=cle):
        _rendre(altere)
    # La garde doit être rouge quand on exige le même refus d'un document intact.
    with pytest.raises(pytest.fail.Exception):
        with pytest.raises(Carte1400Erreur):
            _rendre(document)
    print(f"clé={cle}, refus=1, contre_épreuves_rouges=1")


def test_villes_points_et_etiquettes_lisibles_sans_chevauchement(photographies, monkeypatch):
    from PIL import ImageDraw
    from vues.relief.carte1400 import COULEUR_FOND, COULEUR_TEXTE
    from vues.relief.raster import _vers_pixel

    _, document = photographies
    boites = []
    original = ImageDraw.ImageDraw.rectangle

    def observer(self, xy, *args, **kwargs):
        if kwargs.get("fill") == COULEUR_FOND:
            boites.append(tuple(xy))
        return original(self, xy, *args, **kwargs)

    with monkeypatch.context() as sonde:
        sonde.setattr(ImageDraw.ImageDraw, "rectangle", observer)
        image, compte = _rendre(document)
    index, bounds, cellules = index_des_cellules(document, largeur=LARGEUR)
    decalage = len(plan_avec_legende(carte_de_statistique(document, lecture="densite", largeur=LARGEUR))) - len(index)
    assert boites, "échantillon vide : aucun cartouche"
    assert len(boites) == compte["cellules_avec_villes"] + compte["puissances"] - compte["etiquettes_omises"]
    for i, (x0, y0, x1, y1) in enumerate(boites):
        assert 0 <= x0 <= x1 < LARGEUR
        assert decalage <= y0 <= y1 < decalage + len(index)
        for a, b, c, d in boites[:i]:
            assert x1 < a or x0 > c or y1 < b or y0 > d
    points = 0
    for cellule in cellules:
        if cellule["villes"]:
            centre = cellule["centroid"]
            x, y = _vers_pixel(centre["x_m"], centre["y_m"], bounds, LARGEUR, len(index))
            assert np.array_equal(image[y + decalage, x], COULEUR_TEXTE)
            points += 1
    assert points > 0
    sans = copy.deepcopy(document)
    sans["terre_choisie"] = None
    temoin, _ = _rendre(sans)

    def verifier_cartouches(rendu):
        for x0, y0, x1, y1 in boites:
            assert np.array_equal(rendu[y0:y1 + 1, x0:x1 + 1], temoin[y0:y1 + 1, x0:x1 + 1])

    verifier_cartouches(image)
    altere = image.copy()
    x, y, _, _ = boites[0]
    altere[y, x] = COULEUR_TEXTE
    with pytest.raises(AssertionError):
        verifier_cartouches(altere)
    print(f"points_blancs={points}, cartouches_sans_chevauchement={len(boites)}, contre_épreuves_rouges=1")


@pytest.mark.parametrize("choix", [False, True])
def test_villes_aucun_point_ne_recouvre_un_cartouche(photographies, monkeypatch, choix):
    from PIL import ImageDraw
    from vues.relief.carte1400 import COULEUR_FOND, RAYON_VILLE
    from vues.relief.raster import _vers_pixel

    document = photographies[int(choix)]
    boites = []
    original = ImageDraw.ImageDraw.rectangle

    def observer(self, xy, *args, **kwargs):
        if kwargs.get("fill") == COULEUR_FOND:
            boites.append(tuple(xy))
        return original(self, xy, *args, **kwargs)

    with monkeypatch.context() as sonde:
        sonde.setattr(ImageDraw.ImageDraw, "rectangle", observer)
        _, compte = _rendre(document)
    index, bounds, cellules = index_des_cellules(document, largeur=LARGEUR)
    decalage = len(plan_avec_legende(carte_de_statistique(
        document, lecture="densite", largeur=LARGEUR,
    ))) - len(index)
    points = []
    for cellule in cellules:
        if cellule["villes"]:
            centre = cellule["centroid"]
            x, y = _vers_pixel(centre["x_m"], centre["y_m"], bounds, LARGEUR, len(index))
            points.append((cellule["cell_id"], x, y + decalage))
    assert points and boites, "échantillon vide : aucun point ou cartouche"

    def verifier(cartouches):
        for cell_id, x, y in points:
            for gauche, haut, droite, bas in cartouches:
                # Le cercle entier doit rester hors des cartouches, même de puissance.
                assert (x + RAYON_VILLE < gauche or x - RAYON_VILLE > droite
                        or y + RAYON_VILLE < haut or y - RAYON_VILLE > bas), (
                    f"point de cell_id={cell_id} sur le cartouche {(gauche, haut, droite, bas)}"
                )

    verifier(boites)
    altere = copy.deepcopy(boites)
    _, x, y = points[0]
    altere.append((x, y, x, y))
    with pytest.raises(AssertionError):
        verifier(altere)
    print(f"choix={choix}, points_vérifiés={len(points)}, cartouches={len(boites)}, "
          f"étiquettes_omises={compte['etiquettes_omises']}, contre_épreuves_rouges=1")


@pytest.fixture(scope="module")
def photographie_ia():
    monde = World.charger(0)
    deposer_intention(monde, {"type": TYPE_CHOISIR_DEPART, "seigneurie": 1})
    tick(monde, random.Random(0))
    releve = [dict(tick=17, maison={"sorte": "grande maison", "id": identifiant}, intention=intention)
              for identifiant, intention in [(3, {"type": "tracer_route", "cell": 10322,
                  "points": [[0, 0], [12.5, 0], [12.5, 27.1]], "largeur_m": 4, "foyers": 1}),
                  (10, {"type": "premier", "valeur": 1}), (2, {"type": "inventé", "texte": "tel quel", "liste": [2, 1]}),
                  (10, {"type": "second", "valeur": 2})]]
    return build_snapshot_document(monde, 0, 1, releve_ia=releve)

def _voisines_ia(document):
    ids = {v["cell_id"] for v in document["terre_choisie"]["voisins"]} if document["terre_choisie"] else set()
    maisons = {c["maison"]["id"] for c in document["cells"] if c["cell_id"] in ids and c["maison"]}
    return [m for m in document["ia"]["maisons"] if
            (m["sorte"] == "grande maison" and m["id"] in maisons) or
            (m["sorte"] == "seigneurie" and m["cell_id"] in ids)]

def test_capitales_ia_sans(photographies):
    import hashlib
    from vues.relief.carte1400 import COULEUR_CAPITALE, COULEUR_VOISINE, lignes_de_l_ia
    empreintes = ["d1f5a5ba48404264fac7532450fbfe665f17cf9404bec144e51536478b4bfae6",
                  "85150ecc7fe99f71db116aaf6cfb9d5c7940ef1c5dcb5e26f7730b92a7f13776"]
    cles = "lecture titre unite echelle minimum maximum cellules cellules_mesurees cellules_non_mesurees tick seed puissances cellules_sans_puissance pixels_de_frontiere villes_dessinees cellules_avec_villes villes_hors_carte etiquettes_omises terre_choisie".split()
    for document, empreinte in zip(photographies, empreintes):
        image, compte = _rendre(document)
        assert hashlib.sha256(image.tobytes()).hexdigest() == empreinte and list(compte) == cles
        assert lignes_de_l_ia(document) == []
        assert not any(np.all(image == couleur, axis=-1).any() for couleur in (COULEUR_CAPITALE, COULEUR_VOISINE))
        autre = copy.deepcopy(document); autre["ia"] = {"maisons": [], "maisons_actives_30j": -1}
        assert hashlib.sha256(_rendre(autre)[0].tobytes()).hexdigest() != empreinte

def test_capitales_ia_voisines(photographie_ia):
    from vues.relief.carte1400 import COULEUR_CAPITALE, COULEUR_VOISINE, lignes_de_l_ia
    from vues.relief.raster import _vers_pixel
    document, reference = photographie_ia, _voisines_ia(photographie_ia)
    assert [m["nom"] for m in reference] == ["Valois", "Valois-Bourgogne", "Wittelsbach"]
    def verifier(d):
        image, compte = _rendre(d)
        voisines = _voisines_ia(d)
        assert compte["voisines"] == [m["nom"] for m in voisines]
        index, bounds, cellules = index_des_cellules(d, largeur=LARGEUR)
        decalage = len(plan_avec_legende(carte_de_statistique(d, lecture="densite", largeur=LARGEUR))) - len(index)
        placees = [m for m in d["ia"]["maisons"] if m["cell_id"] is not None]
        assert placees and compte["capitales_dessinees"] == len(placees)
        for m in placees:
            centre = next(c["centroid"] for c in cellules if c["cell_id"] == m["cell_id"])
            x, y = _vers_pixel(centre["x_m"], centre["y_m"], bounds, LARGEUR, len(index))
            assert tuple(image[y + decalage, x]) == (COULEUR_VOISINE if m in voisines else COULEUR_CAPITALE)
        return image, compte
    _, compte = verifier(document)
    with pytest.raises(AssertionError): assert compte["voisines"] == [m["nom"] for m in reference[:-1]]
    autre = copy.deepcopy(document)
    siege = next(m for m in autre["ia"]["maisons"] if m["sorte"] == "seigneurie")
    siege["cell_id"] = autre["terre_choisie"]["voisins"][0]["cell_id"]
    verifier(autre)
    assert any(l.startswith(f"Voisine {siege['nom']} :") for l in lignes_de_l_ia(autre))
    autre["terre_choisie"] = None
    image, compte = verifier(autre)
    assert compte["voisines"] == [] and not np.all(image == COULEUR_VOISINE, axis=-1).any()


def test_capitales_ia_encadre(photographie_ia, monkeypatch):
    import math
    from PIL import Image, ImageDraw, ImageFont
    from vues.relief.carte1400 import lignes_de_l_ia, lignes_de_fiche, _lignes_ajustees, MARGE_FICHE, HAUTEUR_LIGNE
    d = photographie_ia; maisons = d["ia"]["maisons"]; voisines = _voisines_ia(d)
    attendues = [f"L'IA : {len(maisons)} maisons ; actives sur 30 jours : non mesuré (moins de 30 jours)"]
    selection = voisines + [m for m in maisons if m not in voisines and m["gestes"]]
    assert voisines and sum(len(m["gestes"]) for m in selection) == 4
    for m in selection:
        gestes = m["gestes"]; nombre = f"{len(gestes)} geste" + ("s" if len(gestes) > 1 else "") if gestes else "aucun geste"
        attendues.append(f"{'Voisine ' if m in voisines else ''}{m['nom']} : capitale {m['capitale']}, cellule {m['cell_id']}, bourg {m['population']} habitants ; {nombre}")
        for g in gestes:
            i = g["intention"]
            if i["type"] == "tracer_route":
                longueur = round(sum(math.dist(a, b) for a, b in zip(i["points"], i["points"][1:])))
                texte = f"trace une route de {longueur} m, large de {i['largeur_m']} m, par {i['foyers']} foyer, dans la cellule {i['cell']}"
            else:
                texte = i["type"] + "".join(f" {k}={v}" for k, v in i.items() if k != "type")
            attendues.append(f"tick {g['tick']} : {texte}")
    attendues += [f"Sans geste : {sum(not m['gestes'] and m not in voisines for m in maisons)} autres maisons",
                  "Capitales hors carte : Saraï (Djötchides)"]
    assert lignes_de_l_ia(d) == attendues
    for action in ("inverser", "retirer", "mesurer"):
        autre = copy.deepcopy(d); visconti = next(m for m in autre["ia"]["maisons"] if m["nom"] == "Visconti")
        if action == "inverser": visconti["gestes"].reverse()
        elif action == "retirer": visconti["gestes"].pop()
        else: autre["ia"]["maisons_actives_30j"] = 3
        with pytest.raises(AssertionError): assert lignes_de_l_ia(autre) == attendues
    traces = []; original = ImageDraw.ImageDraw.text
    def observer(self, xy, texte, *args, **kwargs):
        traces.append((self._image.size, xy, texte)); return original(self, xy, texte, *args, **kwargs)
    monkeypatch.setattr(ImageDraw.ImageDraw, "text", observer)
    image, compte = _rendre(d)
    dessin = ImageDraw.Draw(Image.new("RGBA", (LARGEUR, 1)))
    repliees = _lignes_ajustees(attendues, dessin, ImageFont.load_default(), LARGEUR)
    hauteur = 2 * MARGE_FICHE + HAUTEUR_LIGNE * len(repliees)
    assert traces[-len(repliees):] == [((LARGEUR, hauteur), (MARGE_FICHE, MARGE_FICHE + n * HAUTEUR_LIGNE), l) for n, l in enumerate(repliees)]
    fiche = _lignes_ajustees(lignes_de_fiche(d), dessin, ImageFont.load_default(), LARGEUR)
    plan = plan_avec_legende(carte_de_statistique(d, lecture="densite", largeur=LARGEUR))
    assert len(image) == len(plan) + 2 * MARGE_FICHE + HAUTEUR_LIGNE * len(fiche) + hauteur
    assert compte["etiquettes_voisines_omises"] == len(voisines) - sum(_sans_accent(f"{m['capitale']} ({m['nom']})") in [t for _, _, t in traces] for m in voisines)
    assert compte["gestes_listes"] == sum(len(m["gestes"]) for m in maisons)


@pytest.mark.parametrize("niveau,cle", [("bloc", c) for c in ("maisons", "maisons_actives_30j")] +
    [("maison", c) for c in ("sorte", "id", "nom", "capitale", "cell_id", "hors_carte", "population", "gestes")] +
    [("cellule", "cell_id"), ("geste", "intention"), ("geste", "tick")])
def test_capitales_ia_refus(photographie_ia, niveau, cle):
    from vues.relief.carte1400 import Carte1400Erreur
    autre = copy.deepcopy(photographie_ia); maison = next(m for m in autre["ia"]["maisons"] if m["gestes"])
    if niveau == "cellule": maison[cle] = -999
    else: del {"bloc": autre["ia"], "maison": maison, "geste": maison["gestes"][0]}[niveau][cle]
    with pytest.raises(Carte1400Erreur, match=cle if niveau == "bloc" else (cle if cle == "nom" else maison["nom"])): _rendre(autre)
    assert _rendre(photographie_ia)[1]["capitales_dessinees"] > 0
