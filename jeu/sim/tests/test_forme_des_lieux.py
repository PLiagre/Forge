"""La forme des lieux : les bords brisés entre cellules (MODELE.md, « La forme des lieux »).

La preuve : le bord entre deux cellules voisines est le même des deux côtés et n'est plus
une droite ; chaque sommet neuf est dans la terre de la carte figée ; la côte de la carte
se retrouve côté pour côté ; chaque place reste dans sa cellule ; deux calculs, et deux
graines du monde, donnent les mêmes contours ; les couples de cellules qui se touchent sont
ceux de l'adjacence. Contre-épreuves : un bord recopié droit, un sommet poussé en mer, une
ligne retournée d'un seul côté rougissent.
"""

import copy
import math

import pytest

import sim.constants as _constantes
from sim.formes import (FormesInvalides, accrocher_les_sommets, anneaux_arrondis, decouper_la_carte,
                        ecart_a_la_corde, segments_partages)
from sim.places import places_du_monde
from sim.villes import point_dans_geometrie
from sim.world import World

# Les segments restés droits ne pèsent pas plus que cette part de la longueur des bords.
PART_DROITE_MAX = 0.01


@pytest.fixture(scope="module")
def monde():
    return World.charger(rng_seed=0)


@pytest.fixture(scope="module")
def places(monde):
    return places_du_monde(monde)


@pytest.fixture(scope="module")
def decoupe(monde, places):
    return decouper_la_carte(monde.carte, monde.adjacency, places)


@pytest.fixture(scope="module")
def accrochee(monde):
    return accrocher_les_sommets({cid: anneaux_arrondis(cid, monde.carte[cid]) for cid in sorted(monde.carte)})


def _cle(u, v):
    return (u, v) if u < v else (v, u)


def _cotes(polygones):
    """Les côtés orientés de polygones (anneaux fermés), sommets en tuples."""
    return [(tuple(u), tuple(v)) for polygone in polygones for anneau in polygone for u, v in zip(anneau, anneau[1:])]


def _distance_au_segment(point, u, v):
    dx, dy = v[0] - u[0], v[1] - u[1]
    t = max(0.0, min(1.0, ((point[0] - u[0]) * dx + (point[1] - u[1]) * dy) / (dx * dx + dy * dy)))
    return math.hypot(point[0] - u[0] - t * dx, point[1] - u[1] - t * dy)


def bords_communs(contours) -> dict:
    """Par couple de cellules, les côtés qu'elles partagent ; chacun doit être parcouru une fois
    par chaque cellule, en sens contraires, et par deux cellules au plus."""
    tenants = {}
    for cid, contour in contours.items():
        for u, v in _cotes(contour["coordinates"]):
            tenants.setdefault(_cle(u, v), []).append((cid, (u, v)))
    couples = {}
    for cle, liste in tenants.items():
        assert len(liste) <= 2, f"côté {cle} parcouru {len(liste)} fois : {[cid for cid, _ in liste]}"
        if len(liste) == 2:
            (a, sens_a), (b, sens_b) = liste
            assert a != b, f"côté {cle} parcouru deux fois par la cellule {a}"
            assert sens_a == sens_b[::-1], f"côté {cle} parcouru dans le même sens par {a} et {b}"
            couples.setdefault(_cle(a, b), []).append(cle)
    return couples


def verifier_lignes_servies(contours, bords, couples):
    """Les côtés communs de chaque couple sont exactement ceux de ses lignes brisées."""
    communs = bords_communs({cid: contours[cid] for couple in couples for cid in couple})
    for couple in couples:
        attendus = {_cle(u, v) for ligne in bords[couple] for u, v in zip(ligne, ligne[1:])}
        assert set(communs.get(couple, [])) == attendus, f"couple {couple} : bord différent des deux côtés"


def bords_brises(contours, accrochee, couples) -> list:
    """Les couples dont aucun sommet commun ne s'écarte de plus du seuil de leurs segments
    de la carte figée : ceux restés droits."""
    communs = bords_communs({cid: contours[cid] for couple in couples for cid in couple})
    bruts = segments_partages({cid: accrochee[cid] for couple in couples for cid in couple})
    droits = []
    for couple in couples:
        sommets = {point for cote in communs.get(couple, []) for point in cote}
        assert sommets, f"couple {couple} : aucun côté commun"
        ecart = max(min(_distance_au_segment(point, u, v) for u, v in bruts[couple]) for point in sommets)
        if ecart < _constantes.ECART_MIN_BRISE_M:
            droits.append(couple)
    return droits


def sommets_neufs_hors_de_la_terre(contours, carte, accrochee, cellules) -> list:
    """Les sommets neufs des contours de ces cellules qui ne sont dans la terre brute
    d'aucune des cellules qui les portent."""
    anciens = {point for polygones in accrochee.values() for polygone in polygones for anneau in polygone
               for point in anneau}
    porteurs = {}
    for cid, contour in contours.items():
        for u, _ in _cotes(contour["coordinates"]):
            porteurs.setdefault(u, set()).add(cid)
    dehors = []
    for cid in cellules:
        for point in sorted({u for u, _ in _cotes(contours[cid]["coordinates"])} - anciens):
            if not any(point_dans_geometrie(*point, carte[autre]["geometry"]) for autre in sorted(porteurs[point])):
                dehors.append((cid, point))
    return dehors


def test_le_bord_est_le_meme_des_deux_cotes_et_n_est_pas_une_droite(decoupe, accrochee):
    communs = bords_communs(decoupe.contours)
    assert communs, "échantillon vide : aucun bord commun"
    assert set(communs) == set(decoupe.bords)
    verifier_lignes_servies(decoupe.contours, decoupe.bords, sorted(communs))
    droits = bords_brises(decoupe.contours, accrochee, sorted(communs))
    print(f"bords={len(communs)}, restés_droits={len(droits)} {droits}")
    assert len(droits) <= len(communs) * PART_DROITE_MAX
    segments = {(a, b, k): ligne for (a, b), lignes in decoupe.bords.items() for k, ligne in enumerate(lignes)}
    longueur = sum(math.dist(ligne[0], ligne[-1]) for ligne in segments.values())
    droite = sum(math.dist(segments[s][0], segments[s][-1]) for s in decoupe.droits)
    print(f"segments={len(segments)}, droits={len(decoupe.droits)}, longueur_droite={droite:.0f} m sur {longueur:.0f} m")
    assert droite <= longueur * PART_DROITE_MAX
    for couple in droits:
        assert all((*couple, k) in decoupe.droits for k in range(len(decoupe.bords[couple])))
    for s, ligne in segments.items():
        assert (ecart_a_la_corde(ligne) < _constantes.ECART_MIN_BRISE_M) == (s in decoupe.droits)


def test_un_bord_recopie_droit_rougit(decoupe, accrochee):
    couple = next(c for c, lignes in sorted(decoupe.bords.items())
                  if len(lignes) == 1 and (*c, 0) not in decoupe.droits)
    ligne = decoupe.bords[couple][0]
    assert bords_brises(decoupe.contours, accrochee, [couple]) == []
    contours = {cid: copy.deepcopy(decoupe.contours[cid]) for cid in couple}
    neufs = {tuple(point) for point in ligne[1:-1]}
    for contour in contours.values():
        for polygone in contour["coordinates"]:
            for i, anneau in enumerate(polygone):
                polygone[i] = [point for point in anneau if tuple(point) not in neufs]
    assert bords_brises(contours, accrochee, [couple]) == [couple]


def test_une_ligne_retournee_d_un_seul_cote_rougit(decoupe):
    couple = next(c for c, lignes in sorted(decoupe.bords.items())
                  if len(lignes) == 1 and (*c, 0) not in decoupe.droits)
    (px, py), (qx, qy) = decoupe.bords[couple][0][0], decoupe.bords[couple][0][-1]
    neufs = {tuple(point) for point in decoupe.bords[couple][0][1:-1]}

    def miroir(point):
        # Le symétrique par rapport à la corde pq.
        dx, dy = qx - px, qy - py
        t = ((point[0] - px) * dx + (point[1] - py) * dy) / (dx * dx + dy * dy)
        hx, hy = px + t * dx, py + t * dy
        return [round(2 * hx - point[0]), round(2 * hy - point[1])]

    contours = {cid: copy.deepcopy(decoupe.contours[cid]) for cid in couple}
    verifier_lignes_servies(contours, decoupe.bords, [couple])
    for polygone in contours[couple[0]]["coordinates"]:
        for i, anneau in enumerate(polygone):
            polygone[i] = [miroir(point) if tuple(point) in neufs else point for point in anneau]
    with pytest.raises(AssertionError, match="bord différent des deux côtés"):
        verifier_lignes_servies(contours, decoupe.bords, [couple])


def test_chaque_sommet_neuf_est_dans_la_terre_de_la_carte_figee(monde, decoupe, accrochee):
    cellules = sorted({cid for couple in decoupe.bords for cid in couple})
    assert cellules, "échantillon vide : aucune cellule bordée"
    assert sommets_neufs_hors_de_la_terre(decoupe.contours, monde.carte, accrochee, cellules) == []
    # Contre-épreuve : un sommet neuf poussé au large de l'Atlantique.
    couple = next(c for c, lignes in sorted(decoupe.bords.items()) if (*c, 0) not in decoupe.droits)
    neuf = decoupe.bords[couple][0][len(decoupe.bords[couple][0]) // 2]
    contours = copy.deepcopy(decoupe.contours)
    for cid in couple:
        for polygone in contours[cid]["coordinates"]:
            for anneau in polygone:
                for point in anneau:
                    if tuple(point) == neuf:
                        point[:] = [0, 0]
    assert sommets_neufs_hors_de_la_terre(contours, monde.carte, accrochee, list(couple))


def test_la_cote_de_la_carte_se_retrouve_cote_pour_cote(monde, decoupe, accrochee):
    cotes_de_la_carte = {}
    for cid, polygones in accrochee.items():
        for u, v in _cotes(polygones):
            cotes_de_la_carte.setdefault(_cle(u, v), []).append((cid, (u, v)))
    cote = [(cid, sens) for liste in cotes_de_la_carte.values() if len(liste) == 1 for cid, sens in liste]
    assert cote, "échantillon vide : aucun côté de côte"
    servis = {cid: set(_cotes(contour["coordinates"])) for cid, contour in decoupe.contours.items()}
    manquants = [(cid, sens) for cid, sens in cote if sens not in servis[cid]]
    assert manquants == []
    print(f"côtés_de_côte={len(cote)}")
    # L'accroche ne déplace pas le trait : la surface de chaque cellule bouge de moins d'une
    # bande de ACCROCHE_SOMMET_M le long de son périmètre.
    for cid in sorted(monde.carte):
        brut = anneaux_arrondis(cid, monde.carte[cid])
        perimetre = sum(math.dist(u, v) for u, v in _cotes(brut))
        assert abs(_aire(brut) - _aire(accrochee[cid])) <= _constantes.ACCROCHE_SOMMET_M * perimetre


def _aire(polygones):
    """L'aire signée totale, anneaux dans le sens de la carte (les trous retranchés)."""
    return sum(ux * vy - vx * uy for (ux, uy), (vx, vy) in _cotes(polygones)) / 2


def test_chaque_place_est_dans_le_contour_brise_de_sa_cellule(decoupe, places):
    total = 0
    for cid, liste in sorted(places.items()):
        for place in liste:
            assert point_dans_geometrie(place.x_m, place.y_m, decoupe.contours[cid]), (cid, place)
            total += 1
    assert total, "échantillon vide : aucune place"
    print(f"places={total}")


def test_deux_calculs_et_deux_graines_donnent_les_memes_contours(monde, places, decoupe):
    carte = copy.deepcopy(monde.carte)
    assert decouper_la_carte(monde.carte, monde.adjacency, places) == decoupe
    assert monde.carte == carte, "le découpage a touché la carte figée"
    autre = World.charger(rng_seed=1)
    assert decouper_la_carte(autre.carte, autre.adjacency, places_du_monde(autre)) == decoupe


def test_les_couples_sont_ceux_de_l_adjacence(monde, decoupe, places):
    voisines = {_cle(a["a"], a["b"]) for a in monde.adjacency
                if a["kind"] == "land-land" and a["a"] in monde.carte and a["b"] in monde.carte}
    assert voisines, "échantillon vide : aucune arête land-land"
    assert set(decoupe.bords) == voisines | set(decoupe.hors_adjacence)
    # Un couple hors de l'adjacence ne se touche qu'une fois la carte arrondie : ses sommets
    # ne diffèrent dans la carte figée que par les derniers bits.
    exacts = {}
    for cid in sorted(monde.carte):
        geometrie = monde.carte[cid]["geometry"]
        polygones = [geometrie["coordinates"]] if geometrie["type"] == "Polygon" else geometrie["coordinates"]
        for u, v in _cotes(polygones):
            exacts.setdefault(_cle(u, v), set()).add(cid)
    touchent = {tuple(sorted(c)) for c in exacts.values() if len(c) == 2}
    assert set(decoupe.hors_adjacence) == set(decoupe.bords) - touchent
    assert not set(decoupe.hors_adjacence) & voisines
    print(f"couples={len(decoupe.bords)}, hors_adjacence={decoupe.hors_adjacence}")
    # Une arête land-land entre deux cellules qui ne se touchent pas est refusée en les nommant.
    a, b = min(voisines)
    loin = next(cid for cid in sorted(monde.carte, reverse=True) if _cle(a, cid) not in decoupe.bords and cid != a)
    fausse = monde.adjacency + [{"a": a, "b": loin, "kind": "land-land", "shared_length_m": 1.0}]
    with pytest.raises(FormesInvalides, match=f"{min(a, loin)} et {max(a, loin)}"):
        decouper_la_carte(monde.carte, fausse, places)


def test_une_geometrie_absente_est_refusee_en_nommant_la_cellule():
    with pytest.raises(FormesInvalides, match="cell_id 7"):
        anneaux_arrondis(7, {"geometry": None})
