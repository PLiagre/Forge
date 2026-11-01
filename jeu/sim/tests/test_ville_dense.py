"""La ville dense de la mesure (#957) : le bourg à 800 habitants, 600 maisons sans îlots."""

import copy
import dataclasses
import hashlib
import json
import pathlib
import pickle

import pytest

import sim.constants as _constantes
from sim.foyers import ranger_en_foyers
from sim.lieux import partager
from sim.service import ServeurMonde
from sim.tests.test_monde import _memoire_epreuve, _service_epreuve, requete_service
from sim.tests.test_ville1400 import (
    _controler_chevauchements,
    _rayon,
    _sous_partie,
    _tolerance_aire,
)
from sim.plan import aire_du_contour
from sim.ville1400 import (
    BaseAbsente,
    _directions_terre,
    base_d_une_population,
    base_de_cellule,
    base_dense_de_cellule,
    base_sans_ilots,
)
from sim.world import World

_BISKRA = 10103
_PARIS = 10322
_BORNE_RAYON_M = 156
# Mesuré sur la base de 1400 de Biskra et de Paris (graine 0) avant l'extraction de la boucle.
_EMPREINTES_BASE = {
    _BISKRA: "9dfd3e281157559030d34e343894021056ebc1777319cbb5cd4ad5de81e8b902",
    _PARIS: "b712f5ebdb9ecfb5efb62dc04c80f639aad21fe40580721b7f18c80ecfda5091",
}
_MODELE = pathlib.Path(__file__).parent.parent / "MODELE.md"


@pytest.fixture(scope="module")
def monde():
    return World.charger(rng_seed=0)


def _get(port, chemin):
    statut, document, octets = requete_service(port, chemin)
    return statut, document, octets


def _post(port, chemin):
    statut, document, _octets = requete_service(port, chemin, "POST")
    return statut, document


def _biskra(port):
    departs = requete_service(port, "/departs")[1]["departs"]
    cell_id = next(d["cell_id"] for d in departs if d["siege"]["nom"] == "Biskra")
    assert cell_id == _BISKRA
    return cell_id


def _bourg(cellule):
    return next(l for l in cellule.lieux if l.rang == 0).population


def _populations_des_autres(cellule):
    return [l.population for l in sorted(cellule.lieux, key=lambda l: l.rang)[1:]]


def _empreinte(base):
    texte = json.dumps(base, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(texte.encode()).hexdigest()


def _controler_rayon(base, borne):
    rayon = _rayon(base)
    assert rayon < borne, f"rayon {rayon:.1f} m, borne {borne} m"
    return rayon


def _controler_dense(base, n_maisons):
    """600 maisons d'un foyer, d'aire exacte, sans chevauchement, dans le rayon dit."""
    assert len(base["maisons"]) == n_maisons
    tolerance = _tolerance_aire()
    surface = _constantes.SURFACE_M2_PAR_FOYER_LOGE
    for maison in base["maisons"]:
        assert maison["foyers"] == 1
        assert abs(aire_du_contour(maison["emprise"]) - surface) <= tolerance
    paires = _controler_chevauchements([base])
    rayon = _controler_rayon(base, _BORNE_RAYON_M)
    return paires, rayon


def test_sc1_fonction_pure(monde, monkeypatch):
    dirs = _directions_terre(monde, _BISKRA)
    n = _constantes.MAISONS_VILLE_DENSE
    base = base_sans_ilots(n, dirs)
    paires, rayon = _controler_dense(base, n)
    print(f"maisons={len(base['maisons'])} voies={len(base['rues'])} paires={paires} rayon={rayon:.1f}")
    principales = [r for r in base["rues"] if r["sorte"] == "principale"]
    assert paires > 0 and len(principales) == len(dirs)

    seuil = _constantes.FOYERS_SANS_ILOTS
    taille = _constantes.TAILLE_FOYER
    assert base_sans_ilots(seuil, dirs) == base_d_une_population(seuil * taille, dirs)
    # Contre-épreuve : un foyer de plus et la seconde a des îlots.
    avec_ilots = base_d_une_population((seuil + 1) * taille, dirs)
    assert base_sans_ilots(seuil + 1, dirs) != avec_ilots
    assert len(avec_ilots["maisons"]) < seuil + 1
    # Contre-épreuve : sans seuil, base_sans_ilots ne bouge pas, l'autre change.
    avant = base_d_une_population(100 * taille, dirs)
    sans = base_sans_ilots(100, dirs)
    with monkeypatch.context() as patch:
        patch.setattr(_constantes, "FOYERS_SANS_ILOTS", 0)
        assert base_sans_ilots(100, dirs) == sans
        assert base_d_une_population(100 * taille, dirs) != avant
    # Contre-épreuve : une maison décalée de 200 m vers l'est sort du rayon.
    decalee = copy.deepcopy(base)
    est = max(decalee["maisons"], key=lambda m: sum(x for x, _y in m["emprise"]))
    est["emprise"] = [[x + 200, y] for x, y in est["emprise"]]
    with pytest.raises(AssertionError):
        _controler_rayon(decalee, _BORNE_RAYON_M)


def test_sc1_cellule_dense_nomme_l_absence(monde, monkeypatch):
    base = base_dense_de_cellule(monde, _BISKRA, 5)
    assert base["cell_id"] == _BISKRA and len(base["maisons"]) == 5
    with monkeypatch.context() as patch:
        patch.delitem(monde.carte[_BISKRA], "centroid")
        with pytest.raises(BaseAbsente, match="centroïde absent"):
            base_dense_de_cellule(monde, _BISKRA, 5)


def _reference_apres_montage(monde, cell_id, poids=None):
    """Monde de référence : seules les populations des lieux ont bougé."""
    reference = copy.deepcopy(monde)
    cellule = reference.cells[cell_id]
    lieux = sorted(cellule.lieux, key=lambda l: l.rang)
    manque = _constantes.HABITANTS_BOURG_VILLE_DENSE - lieux[0].population
    autres = [l.population for l in lieux[1:]]
    parts = partager(manque, autres if poids is None else poids)
    lieux[0].population = _constantes.HABITANTS_BOURG_VILLE_DENSE
    for lieu, part in zip(lieux[1:], parts):
        lieu.population -= part
    return reference


def _meme_monde(serveur, reference):
    assert pickle.dumps(serveur.world) == pickle.dumps(reference)


def test_sc2_le_bourg_passe_a_800(monkeypatch):
    haut = _constantes.HABITANTS_BOURG_VILLE_DENSE
    with _service_epreuve(epreuve=True) as (serveur, port):
        cell_id = _biskra(port)
        cellule = serveur.world.cells[cell_id]
        reference = _reference_apres_montage(serveur.world, cell_id)
        avant = (cellule.population, sum(l.population for l in cellule.lieux),
                 copy.deepcopy(cellule.habitants_par_metier), _bourg(cellule),
                 serveur.rng.getstate(), serveur.world.ticks_ecoules)
        tick = serveur.etat_publie.tick
        statut, document = _post(port, f"/epreuve/ville-dense?cell={cell_id}")
        print(f"bourg {avant[3]} -> {_bourg(cellule)} ; lieux={len(cellule.lieux)} ; habitants={avant[0]}")
        assert (statut, document) == (200, dict(cell_id=cell_id, tick=tick))
        _meme_monde(serveur, reference)
        assert serveur.rng.getstate() == avant[4] and serveur.world.ticks_ecoules == avant[5]
        assert _bourg(cellule) == haut
        assert sum(l.population for l in cellule.lieux) == avant[1] == cellule.population == avant[0]
        assert cellule.habitants_par_metier == avant[2]
        lieu = _get(port, f"/lieu?cell={cell_id}&bourg=1")[1]
        assert lieu["bourg"]["population"] == haut and lieu["bourg"]["tick"] == tick

        # Contre-épreuves : la comparaison échoue contre quatre références fausses.
        faux_bourg = copy.deepcopy(reference)
        next(l for l in faux_bourg.cells[cell_id].lieux if l.rang == 0).population = haut - 1
        perd = copy.deepcopy(reference)
        perd.cells[cell_id].population -= 1
        vide = copy.deepcopy(reference)
        vide.cells[cell_id].habitants_par_metier = {}
        seul_rang_1 = _reference_apres_montage(
            World.charger(rng_seed=0), cell_id,
            poids=[1] + [0] * (len(cellule.lieux) - 2))
        for fausse in (faux_bourg, perd, vide, seul_rang_1):
            with pytest.raises(AssertionError):
                _meme_monde(serveur, fausse)


def _verifier_servi(port, cell_id, tick):
    n = _constantes.MAISONS_VILLE_DENSE
    plan = _get(port, f"/plan?cell={cell_id}")[1]
    occupation = _get(port, f"/occupation?cell={cell_id}")[1]
    assert len(plan["base"]["maisons"]) == n
    assert occupation["base"] == [dict(rang=i, foyers=1) for i in range(n)]
    assert plan["tick"] == occupation["tick"] == tick
    return plan, occupation


def test_sc3_plan_et_occupation_servent_la_ville_dense(monkeypatch):
    n = _constantes.MAISONS_VILLE_DENSE
    with _service_epreuve(epreuve=True) as (serveur, port):
        cell_id = _biskra(port)
        autre = next(c for c in sorted(serveur.world.plans) if c != cell_id)
        plan_avant = _get(port, f"/plan?cell={cell_id}")[1]
        occupation_avant = _get(port, f"/occupation?cell={cell_id}")[1]
        autre_avant = _get(port, f"/plan?cell={autre}")[2]
        print(f"maisons avant={len(plan_avant['base']['maisons'])} après={n}")
        assert len(plan_avant["base"]["maisons"]) < n
        tick = serveur.etat_publie.tick
        assert _post(port, f"/epreuve/ville-dense?cell={cell_id}")[0] == 200
        plan, occupation = _verifier_servi(port, cell_id, tick)
        attendue = json.loads(json.dumps(base_dense_de_cellule(serveur.world, cell_id, n)))
        assert plan["base"] == attendue
        for cle in ("rues", "parcelles", "batiments"):
            assert plan[cle] == plan_avant[cle]
        for cle in ("batiments", "logement"):
            assert occupation[cle] == occupation_avant[cle]
        assert _get(port, f"/plan?cell={autre}")[2] == autre_avant
        octets = _get(port, f"/plan?cell={cell_id}")[2]

        monde_apres = pickle.dumps(serveur.world)
        assert _post(port, f"/epreuve/ville-dense?cell={cell_id}")[0] == 200
        assert pickle.dumps(serveur.world) == monde_apres
        assert _get(port, f"/plan?cell={cell_id}")[1]["base"] == attendue
        assert _get(port, f"/plan?cell={cell_id}")[2] == octets

        assert _post(port, "/tick?n=2")[0] == 200
        plan, _occupation = _verifier_servi(port, cell_id, tick + 2)
        assert plan["base"] == attendue
    with _service_epreuve(epreuve=True) as (autre_serveur, autre_port):
        assert _post(autre_port, f"/epreuve/ville-dense?cell={cell_id}")[0] == 200
        assert _get(autre_port, f"/plan?cell={cell_id}")[2] == octets

    # Contre-épreuve : la base de 1400 au lieu de la base dense échoue.
    with _service_epreuve(epreuve=True) as (serveur, port):
        with monkeypatch.context() as patch:
            patch.setattr("sim.service.base_dense_de_cellule",
                          lambda monde, cid, nombre: base_de_cellule(monde, cid))
            assert _post(port, f"/epreuve/ville-dense?cell={cell_id}")[0] == 200
            with pytest.raises(AssertionError):
                _verifier_servi(port, cell_id, tick)
    # Contre-épreuve : sans reconstruire l'état, l'ancienne base de 1400 reste servie.
    with _service_epreuve(epreuve=True) as (serveur, port):
        _get(port, f"/plan?cell={cell_id}")
        with monkeypatch.context() as patch:
            patch.setattr(ServeurMonde, "_construire_etat", lambda self, *a, **k: self.etat_publie)
            assert _post(port, f"/epreuve/ville-dense?cell={cell_id}")[0] == 200
            with pytest.raises(AssertionError):
                _verifier_servi(port, cell_id, tick)


def _cellules_triees(monde):
    return [monde.cells[cid] for cid in sorted(monde.cells)]


def _refus(serveur, port, chemin, statut, *morceaux):
    avant = (_memoire_epreuve(serveur), dict(serveur._bases))
    reponse, document = _post(port, chemin)
    assert reponse == statut, document
    for morceau in morceaux:
        assert morceau in document["erreur"], document
    assert (_memoire_epreuve(serveur), dict(serveur._bases)) == avant
    return document["erreur"]


def test_sc4_chaque_refus_est_nomme_et_n_ecrit_rien(monkeypatch):
    haut = _constantes.HABITANTS_BOURG_VILLE_DENSE
    with _service_epreuve() as (serveur, port):
        assert _post(port, f"/epreuve/ville-dense?cell={_BISKRA}")[0] == 404
    with _service_epreuve(epreuve=True) as (serveur, port):
        monde = serveur.world
        cellules = _cellules_triees(monde)
        petite = next(c for c in cellules if 0 < c.population < haut and _bourg(c) > 0)
        seule = next(c for c in cellules if len(c.lieux) == 1 and c.population >= haut)
        riche = next(c for c in cellules if len(c.lieux) > 1 and _bourg(c) > haut)
        print(f"petite={petite.cell_id}({petite.population}) seule={seule.cell_id}({seule.population}) "
              f"riche={riche.cell_id}(bourg {_bourg(riche)})")
        inconnue = max(monde.cells) + 1

        # 1. sans --epreuve : vu plus haut. 2. horloge en marche.
        marche = serveur.etat_publie
        serveur.etat_publie = dataclasses.replace(marche, jours_par_seconde=1.0)
        try:
            _refus(serveur, port, f"/epreuve/ville-dense?cell={_BISKRA}", 409, "l'horloge doit être à l'arrêt")
        finally:
            serveur.etat_publie = marche
        # 3. paramètre cell.
        for chemin in ("", "?cell=", f"?cell={_BISKRA}&cell={_BISKRA}", "?cell=abc"):
            _refus(serveur, port, "/epreuve/ville-dense" + chemin, 400, "cell")
        _refus(serveur, port, f"/epreuve/ville-dense?cell={inconnue}", 404, str(inconnue))
        # 5 à 7.
        _refus(serveur, port, f"/epreuve/ville-dense?cell={petite.cell_id}", 400,
               f"cellule {petite.cell_id}", f"{petite.population} habitants", f"il en faut {haut}")
        _refus(serveur, port, f"/epreuve/ville-dense?cell={seule.cell_id}", 400, "aucun autre lieu")
        _refus(serveur, port, f"/epreuve/ville-dense?cell={riche.cell_id}", 400,
               f"{_bourg(riche)} habitants", str(haut))
        # 4. montage incohérent : un lieu de plus que la cellule.
        biskra = monde.cells[_BISKRA]
        with monkeypatch.context() as patch:
            patch.setattr(biskra.lieux[1], "population", biskra.lieux[1].population + 1)
            _refus(serveur, port, f"/epreuve/ville-dense?cell={_BISKRA}", 400, "incohérentes")
        # 8. centroïde absent.
        with monkeypatch.context() as patch:
            patch.delitem(monde.carte[_BISKRA], "centroid")
            _refus(serveur, port, f"/epreuve/ville-dense?cell={_BISKRA}", 500, "centroïde absent")

        # Contre-épreuve : 800 habitants tout juste, à plusieurs lieux, est accepté.
        with monkeypatch.context() as patch:
            lieux = sorted(biskra.lieux, key=lambda l: l.rang)
            parts = partager(haut - lieux[0].population, [l.population for l in lieux[1:]])
            for lieu, part in zip(lieux[1:], parts):
                patch.setattr(lieu, "population", part)
            patch.setattr(biskra, "population", haut)
            assert _bourg(biskra) <= haut and sum(l.population for l in biskra.lieux) == haut
            reponse, document = _post(port, f"/epreuve/ville-dense?cell={_BISKRA}")
            assert reponse == 200, document
            assert _bourg(biskra) == haut and sum(l.population for l in biskra.lieux) == haut
            assert len(_get(port, f"/plan?cell={_BISKRA}")[1]["base"]["maisons"]) \
                == _constantes.MAISONS_VILLE_DENSE


def test_sc5_hors_epreuve_rien_ne_change(monde, monkeypatch):
    with _service_epreuve() as (serveur, port):
        cell_id = _biskra(port)
        attendue = json.loads(json.dumps(base_de_cellule(serveur.world, cell_id)))
        plan = _get(port, f"/plan?cell={cell_id}")[1]
        occupation = _get(port, f"/occupation?cell={cell_id}")[1]
        bourg = _get(port, f"/lieu?cell={cell_id}&bourg=1")[1]["bourg"]["population"]
        print(f"maisons={len(plan['base']['maisons'])} bourg={bourg}")
        assert plan["base"] == attendue
        assert occupation["base"] == [dict(rang=i, foyers=m["foyers"])
                                      for i, m in enumerate(attendue["maisons"])]
        assert len(attendue["maisons"]) < _constantes.MAISONS_VILLE_DENSE
        assert bourg == _bourg(serveur.world.cells[cell_id]) == monde.populations_bourg_amorcage[cell_id]
    assert _constantes.FOYERS_SANS_ILOTS == 500
    for cid, attendu in _EMPREINTES_BASE.items():
        base = base_d_une_population(monde.populations_bourg_amorcage[cid], _directions_terre(monde, cid))
        base["cell_id"] = cid
        assert _empreinte(base) == attendu
    # Contre-épreuve : sans seuil, l'empreinte de Biskra (sous le seuil) change. Paris, déjà
    # au-dessus du seuil avec ses îlots, ne change pas : le brief la citait par erreur.
    foyers_paris = ranger_en_foyers(monde.populations_bourg_amorcage[_PARIS]).nombre
    print(f"foyers Paris={foyers_paris} seuil={_constantes.FOYERS_SANS_ILOTS}")
    assert foyers_paris > _constantes.FOYERS_SANS_ILOTS
    with monkeypatch.context() as patch:
        patch.setattr(_constantes, "FOYERS_SANS_ILOTS", 0)
        base = base_d_une_population(monde.populations_bourg_amorcage[_BISKRA],
                                     _directions_terre(monde, _BISKRA))
        base["cell_id"] = _BISKRA
        assert _empreinte(base) != _EMPREINTES_BASE[_BISKRA]


def test_sc6_le_modele_le_dit():
    section = _sous_partie(_MODELE.read_text(encoding="utf-8"), "### Le plan de base")
    for morceau in ("/epreuve/ville-dense", "HABITANTS_BOURG_VILLE_DENSE",
                    "MAISONS_VILLE_DENSE", "sans îlots"):
        assert morceau in section, morceau
    with pytest.raises(AssertionError, match="échantillon vide"):
        _sous_partie("## Autre titre\n\ntexte", "### Le plan de base")
