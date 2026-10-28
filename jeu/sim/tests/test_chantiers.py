"""Preuves du travail compté, des métiers conservés et de la récolte du chantier."""

from dataclasses import replace
import copy
import math
from pathlib import Path
import random

import pytest

from sim import constants as k, engine, foyers
from sim.intentions import recevoir_intention
from sim.model import lire_habitants_par_metier
from sim.plan import Plan, PlanInvalide, Rue
from sim.tests.test_intentions import _route_reference, _financer, _temoin_salaire
from sim.world import World


def _requis(geste):
    longueur = sum(math.dist(a, b) for a, b in zip(geste["points"], geste["points"][1:]))
    return max(1, math.ceil(longueur * geste["largeur_m"] * k.TRAVAIL_ROUTE_JOURNEES_PAR_M2))


@pytest.mark.parametrize("nombre", [None, 3])
def test_foyers_du_geste(nombre, monkeypatch):
    monde = World.charger(0)
    geste = _route_reference(monde)
    if nombre is not None:
        geste["foyers"] = nombre
    route = recevoir_intention(monde, geste)
    assert route.foyers == (1 if nombre is None else nombre)
    engine._appliquer_intentions(monde)
    rue = monde.plans[geste["cell"]].rues[0]
    nominal = _requis(geste)
    assert (rue.foyers, rue.travail_requis, rue.travail_fourni) == (route.foyers, nominal, 0)
    monkeypatch.setattr(k, "TRAVAIL_ROUTE_JOURNEES_PAR_M2", k.TRAVAIL_ROUTE_JOURNEES_PAR_M2 * 2)
    recevoir_intention(monde, geste)
    engine._appliquer_intentions(monde)
    double = monde.plans[geste["cell"]].rues[-1].travail_requis
    assert double == _requis(geste)
    with pytest.raises(AssertionError):
        assert double == nominal


@pytest.mark.parametrize("champs", [
    {"travail_fourni": 2}, {"travail_fourni": 1}, {"en_chantier": False}, {"foyers": 0},
    *[{champ: valeur} for champ in ("foyers", "travail_requis", "travail_fourni")
      for valeur in (True, -1, 1.5, "1")],
])
def test_rue_invalide(champs):
    with pytest.raises(PlanInvalide):
        Rue(0, [(0, 0), (1, 0)], 1, **(
            {"en_chantier": True, "foyers": 1, "travail_requis": 1, "travail_fourni": 0} | champs))


def _courte(monde):
    # Deux foyers entiers, puis un dernier jour incomplet, dérivés de leur taille.
    requis = 3 * k.TAILLE_FOYER - 2
    assert requis % k.TAILLE_FOYER != 0
    return _route_reference(monde) | {
        "points": [[0, 0], [requis / k.TRAVAIL_ROUTE_JOURNEES_PAR_M2, 0]], "largeur_m": 1}


def _controler_compte(cell, rue, envoi, total, population, paysans):
    metiers = lire_habitants_par_metier(cell)
    assert metiers.get(k.METIER_OUVRIERS, 0) == envoi
    assert metiers.get(k.METIER_PAYSANS, 0) + envoi == paysans
    assert cell.population == population == sum(metiers.values())
    assert rue.travail_fourni == total <= rue.travail_requis
    assert rue.en_chantier == (total < rue.travail_requis)


def test_compte_journees_et_retour(monkeypatch):
    from sim import chantiers

    monde = World.charger(0)
    geste = _courte(monde)
    recevoir_intention(monde, geste)
    engine._appliquer_intentions(monde)
    _financer(monde, geste["cell"])
    cell = monde.cells[geste["cell"]]
    population, paysans = cell.population, lire_habitants_par_metier(cell)[k.METIER_PAYSANS]
    requis = _requis(geste)
    total = 0
    for attendu in (k.TAILLE_FOYER, k.TAILLE_FOYER, requis - 2 * k.TAILLE_FOYER):
        envois = chantiers.avancer_chantiers(monde)
        assert envois == {(cell.cell_id, 0): attendu}
        total += attendu
        rue = monde.plans[cell.cell_id].rues[0]
        _controler_compte(cell, rue, attendu, total, population, paysans)
        if total < requis:
            fausse_rue = replace(rue, travail_fourni=total + 1,
                                 en_chantier=total + 1 < requis)
            with pytest.raises(AssertionError):
                _controler_compte(cell, fausse_rue, attendu, total, population, paysans)
    assert total == requis
    faux = copy.deepcopy(cell)
    faux.habitants_par_metier[k.METIER_OUVRIERS] += 1
    faux.habitants_par_metier[k.METIER_PAYSANS] -= 1
    with pytest.raises(AssertionError):
        _controler_compte(faux, rue, attendu, total, population, paysans)
    assert chantiers.avancer_chantiers(monde) == {}
    _controler_compte(cell, rue, 0, total, population, paysans)
    # Sans travail ni ouvrier : aucun écrivain ni nouvelle instance de plan.
    plan = monde.plans[cell.cell_id]
    monkeypatch.setattr(chantiers, "ecrire_habitants_par_metier", lambda *a: pytest.fail("écriture inutile"))
    monkeypatch.setattr(chantiers, "Plan", lambda **kw: pytest.fail("plan reconstruit sans travail"))
    assert chantiers.avancer_chantiers(monde) == {} and monde.plans[cell.cell_id] is plan


def test_compte_priorite_et_metiers_non_calcules():
    from sim import chantiers

    monde = World.charger(0)
    candidats = [c for c in monde.cells.values()
                 if lire_habitants_par_metier(c).get(k.METIER_PAYSANS, 0) > 0]
    assert candidats, "échantillon vide : aucun paysan"
    cell = min(candidats, key=lambda c: (lire_habitants_par_metier(c)[k.METIER_PAYSANS], c.cell_id))
    paysans = lire_habitants_par_metier(cell)[k.METIER_PAYSANS]
    requis = paysans + k.TAILLE_FOYER
    rues = [Rue(i, [(0, 0), (1, 0)], 1, True, paysans + 1, requis) for i in (1, 0)]
    _financer(monde, cell.cell_id)
    monde.plans[cell.cell_id] = Plan(rues=rues)
    population = cell.population
    envois = chantiers.avancer_chantiers(monde)
    assert envois == {(cell.cell_id, 0): paysans, (cell.cell_id, 1): 0}
    assert [r.travail_fourni for r in monde.plans[cell.cell_id].rues] == [paysans, 0]
    assert sum(lire_habitants_par_metier(cell).values()) == population
    monde = World.charger(0)
    cell = monde.cells[cell.cell_id]
    monde.plans[cell.cell_id] = Plan(rues=rues)
    cell.habitants_par_metier = None
    avant = monde.to_dict()
    plan = monde.plans[cell.cell_id]
    assert chantiers.avancer_chantiers(monde) == {(cell.cell_id, 0): 0, (cell.cell_id, 1): 0}
    assert monde.to_dict() == avant and monde.plans[cell.cell_id] is plan
    assert all(rue.travail_fourni == 0 for rue in plan.rues)


def _cellules_identiques_sauf_metiers(temoin, monde, cid):
    assert (temoin.greniers, temoin.pertes_kg) == (monde.greniers, monde.pertes_kg)
    a, b = temoin.to_dict()["cells"], monde.to_dict()["cells"]
    assert a and a.keys() == b.keys()
    assert all(a[cle] == b[cle] for cle in a if cle != str(cid))
    assert {cle: v for cle, v in a[str(cid)].items() if cle != "foyers"} == {
        cle: v for cle, v in b[str(cid)].items() if cle != "foyers"}


def test_tick_depart_avant_recolte_et_retour(monkeypatch):
    production = engine._apply_production

    def jouer(financer_temoin=True):
        temoin, monde = World.charger(0), World.charger(0)
        aleas = [random.Random(0), random.Random(0)]
        geste = _courte(monde)
        for m in (temoin, monde): _financer(m, geste["cell"])
        recevoir_intention(monde, geste)
        releves = []

        def relever(cell, *a, **kw):
            if cell is monde.cells[geste["cell"]]:
                releves.append(lire_habitants_par_metier(cell).get(k.METIER_OUVRIERS, 0))
            return production(cell, *a, **kw)

        with monkeypatch.context() as sonde:
            sonde.setattr(engine, "_apply_production", relever)
            if financer_temoin: _temoin_salaire(sonde, temoin, geste["cell"], [k.TAILLE_FOYER, k.TAILLE_FOYER, _requis(geste) - 2 * k.TAILLE_FOYER, 0, 0, 0])
            for i in range(6):
                for m, alea in zip((temoin, monde), aleas):
                    engine.tick(m, alea, i)
        assert aleas[0].getstate() == aleas[1].getstate()
        _cellules_identiques_sauf_metiers(temoin, monde, geste["cell"])
        return monde.plans[geste["cell"]].rues[0], releves

    rue, releves = jouer()
    assert releves == [k.TAILLE_FOYER, k.TAILLE_FOYER, rue.travail_requis - 2 * k.TAILLE_FOYER, 0, 0, 0]
    assert rue.travail_fourni == rue.travail_requis and not rue.en_chantier
    engine._avancer_chantiers(object())
    with monkeypatch.context() as sonde:
        sonde.setattr(engine, "_avancer_chantiers", lambda monde: None)
        faux, _ = jouer(False)
        assert faux.travail_fourni == 0
        with pytest.raises(AssertionError):
            assert faux.travail_fourni == faux.travail_requis


def test_recolte_diminue_avec_les_bras_envoyes(monkeypatch):
    # Isoler le coût des bras : une naissance changerait les effectifs au jour 16.
    monkeypatch.setattr(engine, "_apply_natalite", lambda cell, penurie_kg: None)
    production = engine._apply_production
    initial = World.charger(0)
    geste = _route_reference(initial, cell=1175)
    cell = initial.cells[geste["cell"]]
    assert cell.cell_id == 1175 and len(cell.lieux) == 1
    paysans = lire_habitants_par_metier(cell)[k.METIER_PAYSANS]
    km2 = (cell.area_km2 * engine._facteur_relief_pour_cellule(cell, initial.carte)
           * engine._facteur_eau_pour_cellule(cell, initial.carte)
           * engine._facteur_agricole(cell, initial.carte))
    requis = km2 * k.BRAS_AUX_CHAMPS_PAR_KM2
    moyen = (paysans - 1) // k.TAILLE_FOYER
    gros = 2 * math.ceil(paysans / k.TAILLE_FOYER)
    assert paysans - moyen * k.TAILLE_FOYER == 2
    ticks = 30
    # Même travail, replié dans la place : les bandes peuvent se recroiser.
    travail = (ticks + 1) * gros * k.TAILLE_FOYER
    largeur = k.DEMI_COTE_PLACE_1400_M / 5
    limite = k.DEMI_COTE_PLACE_1400_M - largeur / 2
    longueur = travail / k.TRAVAIL_ROUTE_JOURNEES_PAR_M2 / largeur
    points, sens = [[-limite, -limite + largeur / 2]], 1
    while longueur > 0:
        distance = min(2 * limite, longueur)
        points.append([points[-1][0] + sens * distance, points[-1][1]])
        longueur -= distance
        if longueur > 0:
            distance = min(1, longueur)
            points.append([points[-1][0], points[-1][1] + distance])
            longueur -= distance
        sens *= -1
    def dans_place(trace):
        assert all(abs(v) + largeur / 2 <= k.DEMI_COTE_PLACE_1400_M for p in trace for v in p), "dans la place"
    dans_place(points)
    with pytest.raises(AssertionError, match="dans la place"):
        dans_place([[x + k.DEMI_COTE_PLACE_1400_M, y] for x, y in points])
    geste |= {"points": points, "largeur_m": largeur}

    def jouer():
        recoltes = []
        for nombre in (None, 1, moyen, gros):
            monde, alea = World.charger(0), random.Random(0)
            _financer(monde, geste["cell"], travail * 3 * 2)
            cible = monde.cells[geste["cell"]]
            mesures = []
            if nombre is not None:
                recevoir_intention(monde, geste | {"foyers": nombre})

            def relever(cell, *a, **kw):
                if cell is cible:
                    etat_alea = a[0].getstate()
                production(cell, *a, **kw)
                if cell is cible:
                    jour = kw["jour"]
                    besoin = requis * engine._facteur_saison_pour_cellule(cell, monde.carte, jour)
                    restants = lire_habitants_par_metier(cell).get(k.METIER_PAYSANS, 0)
                    if nombre == moyen:
                        assert restants == 2 < besoin
                    tirage = random.Random(); tirage.setstate(etat_alea)
                    rendement = tirage.uniform(k.RNG_YIELD_LOW, k.RNG_YIELD_HIGH)
                    pleine = engine.production_du_tick_kg(cell, rendement, monde.carte, jour)
                    observe = kw["recoltes"][cell.cell_id][0]
                    assert observe == pytest.approx(pleine * min(1, restants / besoin), rel=1e-12)
                    mesures.append(observe)

            with monkeypatch.context() as sonde:
                sonde.setattr(engine, "_apply_production", relever)
                for i in range(ticks):
                    engine.tick(monde, alea, i)
            assert len(mesures) == ticks > 0
            if nombre is not None:
                assert monde.plans[cible.cell_id].rues[0].en_chantier
                assert monde.plans[cible.cell_id].rues[0].travail_requis == travail
            recoltes.append(sum(mesures))
        return recoltes

    def controler(valeurs):
        temoin, petit, moyen, gros = valeurs
        assert temoin == petit > moyen > gros == 0

    valeurs = jouer()
    print(f"récoltes_témoin_un_moyen_gros={valeurs}")
    controler(valeurs)
    with monkeypatch.context() as sonde:
        sonde.setattr(foyers, "facteur_bras", lambda *a: 1.0)
        with pytest.raises(AssertionError):
            controler(jouer())


def test_documentation(monkeypatch):
    dossier = Path(engine.__file__).parent
    lire = Path.read_text

    def controler():
        texte = (dossier / "MODELE.md").read_text(encoding="utf-8")
        assert texte.splitlines().count("## Le chantier et ses bras") == 1
        section = texte.split("## Le chantier et ses bras\n", 1)[1].split("\n## ", 1)[0]
        assert all(mot in section for mot in ("TRAVAIL_ROUTE_JOURNEES_PAR_M2", "ouvriers", "niveau 2"))
        assert "_avancer_chantiers" in texte.split("## En une page\n", 1)[1].split("\n## ", 1)[0]
        plan = texte.split("## Le plan du bourg\n", 1)[1].split("\n## ", 1)[0]
        assert "Aucune règle ne fait passer une rue en chantier à achevée" not in plan
        assert "sim/chantiers.py" in (dossier / "README.md").read_text(encoding="utf-8")

    controler()
    for ancien, nouveau in (("TRAVAIL_ROUTE_JOURNEES_PAR_M2", "constante retirée"),
                            ("## Le chantier et ses bras", "Aucune règle ne fait passer une rue en chantier à achevée\n\n## Le chantier et ses bras")):
        with monkeypatch.context() as sonde:
            sonde.setattr(Path, "read_text", lambda path, *a, **kw: lire(path, *a, **kw).replace(ancien, nouveau)
                          if path.name == "MODELE.md" else lire(path, *a, **kw))
            with pytest.raises(AssertionError):
                controler()


CAS_PARCELLE_INVALIDE = [
    {"travail_fourni": 2}, {"travail_fourni": 1}, {"en_chantier": False}, {"foyers": 0},
    {"en_chantier": 1},
    *[{champ: valeur} for champ in ("foyers", "travail_requis", "travail_fourni")
      for valeur in (True, -1, 1.5, "1")],
]


@pytest.mark.parametrize("champs", CAS_PARCELLE_INVALIDE)
def test_parcelle_invalide(champs):
    from sim.plan import Parcelle

    triangle = [(0, 0), (1, 0), (0, 1)]
    coherent = {"en_chantier": True, "foyers": 1, "travail_requis": 1, "travail_fourni": 0}
    with pytest.raises(PlanInvalide, match="parcelle"):
        Parcelle(0, triangle, **(coherent | champs))
    assert Parcelle(0, triangle, **coherent).en_chantier
    assert CAS_PARCELLE_INVALIDE


def test_parcelle_compte_journees_et_retour(monkeypatch):
    from sim import chantiers
    from sim.plan import Parcelle

    monde = World.charger(0)
    c = _route_reference(monde)["cell"]
    requis = 3 * k.TAILLE_FOYER - 2
    plan = Plan(parcelles=[Parcelle(0, [(0, 0), (1, 0), (0, 1)], True, 1, requis)])
    _financer(monde, c)
    monde.plans[c] = plan
    cell = monde.cells[c]
    population, paysans = cell.population, lire_habitants_par_metier(cell)[k.METIER_PAYSANS]
    assert paysans >= k.TAILLE_FOYER > 0
    total = 0
    for attendu in (k.TAILLE_FOYER, k.TAILLE_FOYER, requis - 2 * k.TAILLE_FOYER):
        assert chantiers.avancer_chantiers(monde) == {(c, "parcelle", 0): attendu}
        total += attendu
        _controler_compte(cell, monde.plans[c].parcelles[0], attendu, total, population, paysans)
    assert total == requis and chantiers.avancer_chantiers(monde) == {}
    _controler_compte(cell, monde.plans[c].parcelles[0], 0, requis, population, paysans)
    # Une reconstruction inerte doit faire échouer le compte du travail.
    monde.plans[c] = plan
    with monkeypatch.context() as sonde:
        sonde.setattr(chantiers, "Plan", lambda **kw: plan)
        assert chantiers.avancer_chantiers(monde) == {(c, "parcelle", 0): k.TAILLE_FOYER}
        assert monde.plans[c].parcelles[0].travail_fourni == 0
        with pytest.raises(AssertionError):
            assert monde.plans[c].parcelles[0].travail_fourni == k.TAILLE_FOYER


def test_parcelle_compte_priorite_et_metiers_non_calcules():
    from sim import chantiers
    from sim.plan import Parcelle

    monde = World.charger(0)
    candidats = [c for c in monde.cells.values()
                 if lire_habitants_par_metier(c).get(k.METIER_PAYSANS, 0) > 0]
    assert candidats, "échantillon vide : aucun paysan"
    cell = min(candidats, key=lambda c: (lire_habitants_par_metier(c)[k.METIER_PAYSANS], c.cell_id))
    c = cell.cell_id
    paysans = lire_habitants_par_metier(cell)[k.METIER_PAYSANS]
    requis = paysans + k.TAILLE_FOYER
    parcelles = [Parcelle(i, [(0, 0), (1, 0), (0, 1)], True, paysans + 1, requis) for i in (1, 0)]
    rue = Rue(5, [(0, 0), (1, 0)], 1, True, paysans + 1, requis)
    plan = Plan(rues=[rue], parcelles=parcelles)
    _financer(monde, c)
    monde.plans[c] = plan
    assert chantiers.avancer_chantiers(monde) == {(c, 5): paysans, (c, "parcelle", 0): 0, (c, "parcelle", 1): 0}
    assert monde.plans[c].rues[0].travail_fourni == paysans
    assert all(p.travail_fourni == 0 for p in monde.plans[c].parcelles)
    # Sans rue, l'identifiant départage les parcelles.
    monde = World.charger(0)
    _financer(monde, c)
    monde.plans[c] = Plan(parcelles=parcelles)
    assert chantiers.avancer_chantiers(monde) == {(c, "parcelle", 0): paysans, (c, "parcelle", 1): 0}
    monde = World.charger(0)
    monde.plans[c] = plan
    monde.cells[c].habitants_par_metier = None
    avant = monde.to_dict()
    assert chantiers.avancer_chantiers(monde) == {(c, 5): 0, (c, "parcelle", 0): 0, (c, "parcelle", 1): 0}
    assert monde.to_dict() == avant and monde.plans[c] is plan


def test_parcelle_tick_rejeu_temoin_et_achevement(monkeypatch):
    from sim.tests.test_intentions import _parcelle_reference

    production = engine._apply_production
    reference = _parcelle_reference(World.charger(0)) | {"profondeur_m": 13}
    c = reference["cell"]
    requis = max(1, math.ceil(reference["facade_m"] * reference["profondeur_m"]
                              * k.TRAVAIL_PARCELLE_JOURNEES_PAR_M2))
    assert requis % k.TAILLE_FOYER != 0 and requis > 2 * k.TAILLE_FOYER

    def jouer(financer_temoin=True):
        mondes = [World.charger(0) for _ in range(3)]
        aleas = [random.Random(0) for _ in mondes]
        route = _route_reference(mondes[0])
        for i, monde in enumerate(mondes):
            _financer(monde, c)
            monde.plans[c] = Plan(rues=[Rue(0, route["points"], route["largeur_m"])])
            if i < 2:
                recevoir_intention(monde, reference)
        releves = []

        def relever(cell, *a, **kw):
            if cell is mondes[0].cells[c]:
                releves.append(lire_habitants_par_metier(cell).get(k.METIER_OUVRIERS, 0))
            return production(cell, *a, **kw)

        with monkeypatch.context() as sonde:
            sonde.setattr(engine, "_apply_production", relever)
            if financer_temoin: _temoin_salaire(sonde, mondes[2], c, [k.TAILLE_FOYER, k.TAILLE_FOYER, requis - 2 * k.TAILLE_FOYER] + [0] * 3)
            for i in range(6):
                for monde, alea in zip(mondes, aleas):
                    engine.tick(monde, alea, numero_tick=i)
        assert mondes[0].to_dict() == mondes[1].to_dict()
        assert aleas[0].getstate() == aleas[1].getstate() == aleas[2].getstate()
        _cellules_identiques_sauf_metiers(mondes[2], mondes[0], c)
        a, b = mondes[0].to_dict()["plans"], mondes[2].to_dict()["plans"]
        assert a and a.keys() == b.keys()
        assert all(a[cle] == b[cle] for cle in a if cle != str(c))
        assert {cle: v for cle, v in a[str(c)].items() if cle != "parcelles"} == {
            cle: v for cle, v in b[str(c)].items() if cle != "parcelles"}
        assert not b[str(c)]["parcelles"]
        return mondes[0].plans[c].parcelles[0], releves

    parcelle, releves = jouer()
    assert releves == [k.TAILLE_FOYER, k.TAILLE_FOYER, requis - 2 * k.TAILLE_FOYER, 0, 0, 0]
    assert parcelle.travail_fourni == parcelle.travail_requis == requis and not parcelle.en_chantier
    with monkeypatch.context() as sonde:
        sonde.setattr(engine, "_avancer_chantiers", lambda monde: None)
        faux, _ = jouer(False)
        assert faux.travail_fourni == 0
        with pytest.raises(AssertionError):
            assert faux.travail_fourni == faux.travail_requis


def test_documentation_parcelle(monkeypatch):
    dossier = Path(engine.__file__).parent
    lire = Path.read_text

    def controler():
        texte = (dossier / "MODELE.md").read_text(encoding="utf-8")
        section = texte.split("## Le chantier et ses bras\n", 1)[1].split("\n## ", 1)[0]
        assert "TRAVAIL_PARCELLE_JOURNEES_PAR_M2" in section
        intentions = texte.split("## Les intentions du joueur\n", 1)[1].split("\n## ", 1)[0]
        assert "decouper_parcelle" in intentions and "DecoupeParcelle" in intentions
        plan = texte.split("## Le plan du bourg\n", 1)[1].split("\n## ", 1)[0]
        assert "gestes de parcelle" not in plan
        assert "decouper_parcelle" in (dossier / "README.md").read_text(encoding="utf-8")
        assert "journées de route puis de parcelle" in (dossier / "engine.py").read_text(encoding="utf-8")

    controler()
    for ancien, nouveau in (("TRAVAIL_PARCELLE_JOURNEES_PAR_M2", "constante retirée"),
                            ("gestes de bâtiment", "gestes de parcelle et de bâtiment")):
        with monkeypatch.context() as sonde:
            sonde.setattr(Path, "read_text", lambda path, *a, **kw: lire(path, *a, **kw).replace(ancien, nouveau)
                          if path.name == "MODELE.md" else lire(path, *a, **kw))
            with pytest.raises(AssertionError):
                controler()


def test_aire_batiment_lacet_et_travail(monkeypatch):
    from sim.chantiers import travail_requis_de_batiment
    from sim.plan import aire_du_contour
    from sim.tests.test_intentions import _parcelle_reference

    triangle = [(0, 0), (10, 0), (0, 10)]
    nominal = 100 * k.AIRE_PAR_PRODUIT_CROISE
    monde = World.charger(0)
    geste = _parcelle_reference(monde)
    for cote in ("gauche", "droite"):
        recevoir_intention(monde, geste | {"cote": cote})
    engine._appliquer_intentions(monde)
    contours = [p.contour for p in monde.plans[geste["cell"]].parcelles]
    assert len(contours) == 2
    plat = [(0, 0), (1, 0), (2, 0)]
    petit = [(0, 0), (0.1, 0), (0, 0.1)]
    for contour, aire in [(triangle, nominal), (triangle[::-1], nominal),
                           *[(c, 400 * k.AIRE_PAR_PRODUIT_CROISE) for c in contours],
                           (plat, 0), (petit, 0.01 * k.AIRE_PAR_PRODUIT_CROISE)]:
        assert aire_du_contour(contour) == pytest.approx(aire)
        assert travail_requis_de_batiment(contour) == max(1, math.ceil(aire * k.TRAVAIL_BATIMENT_JOURNEES_PAR_M2))
    assert travail_requis_de_batiment(plat) == travail_requis_de_batiment(petit) == 1
    monkeypatch.setattr(k, "AIRE_PAR_PRODUIT_CROISE", 1)
    assert aire_du_contour(triangle) == 2 * nominal
    with pytest.raises(AssertionError):
        assert aire_du_contour(triangle) == nominal


@pytest.mark.parametrize("champs", CAS_PARCELLE_INVALIDE)
def test_batiment_invalide(champs):
    from sim.plan import Batiment

    coherent = {"en_chantier": True, "foyers": 1, "travail_requis": 1, "travail_fourni": 0}
    triangle = [(0, 0), (1, 0), (0, 1)]
    with pytest.raises(PlanInvalide, match="bâtiment"):
        Batiment(0, 0, "maison", triangle, **(coherent | champs))
    assert Batiment(0, 0, "maison", triangle, **coherent).en_chantier
    assert CAS_PARCELLE_INVALIDE


def test_documentation_batiment(monkeypatch):
    dossier = Path(engine.__file__).parent
    lire = Path.read_text

    def controler():
        texte = (dossier / "MODELE.md").read_text(encoding="utf-8")
        sections = {titre: texte.split(f"## {titre}\n", 1)[1].split("\n## ", 1)[0]
                    for titre in ("Le chantier et ses bras", "Les intentions du joueur", "Le plan du bourg")}
        assert all(mot in sections["Le chantier et ses bras"] for mot in (
            "TRAVAIL_BATIMENT_JOURNEES_PAR_M2", "AIRE_PAR_PRODUIT_CROISE"))
        assert all(mot in sections["Les intentions du joueur"] for mot in ("poser_batiment", "PoseBatiment"))
        assert "poser_batiment" in sections["Le plan du bourg"]
        assert "poser_batiment" in (dossier / "README.md").read_text(encoding="utf-8")

    controler()
    for mot in ("TRAVAIL_BATIMENT_JOURNEES_PAR_M2", "PoseBatiment"):
        with monkeypatch.context() as sonde:
            sonde.setattr(Path, "read_text", lambda path, *a, **kw: lire(path, *a, **kw).replace(mot, "retiré"))
            with pytest.raises(AssertionError):
                controler()


def test_batiment_priorite(monkeypatch):
    from sim import chantiers
    from sim.plan import Batiment, Parcelle

    monde = World.charger(0)
    candidats = [c for c in monde.cells.values()
                 if lire_habitants_par_metier(c).get(k.METIER_PAYSANS, 0) > 0]
    assert candidats, "échantillon vide : aucun paysan"
    cell = min(candidats, key=lambda c: (lire_habitants_par_metier(c)[k.METIER_PAYSANS], c.cell_id))
    c, population = cell.cell_id, cell.population
    paysans = lire_habitants_par_metier(cell)[k.METIER_PAYSANS]
    requis, foyers = paysans + k.TAILLE_FOYER, paysans + 1
    triangle = [(0, 0), (1, 0), (0, 1)]
    rue = Rue(5, [(0, 0), (1, 0)], 1, True, foyers, requis)
    parcelles = [Parcelle(0, triangle, True, foyers, requis),
                 Parcelle(1, triangle), Parcelle(2, triangle)]
    batiments = [Batiment(i, i + 1, "maison", triangle, True, foyers, requis) for i in (1, 0)]
    plan = Plan(rues=[rue], parcelles=parcelles, batiments=batiments)
    _financer(monde, c)
    monde.plans[c] = plan
    attendu = {(c, 5): paysans, (c, "parcelle", 0): 0,
               (c, "batiment", 0): 0, (c, "batiment", 1): 0}
    assert chantiers.avancer_chantiers(monde) == attendu
    assert monde.plans[c].rues[0].travail_fourni == paysans
    assert all(p.travail_fourni == 0 for p in monde.plans[c].parcelles)
    assert all(b.travail_fourni == 0 for b in monde.plans[c].batiments)
    monde = World.charger(0)
    _financer(monde, c)
    monde.plans[c] = Plan(parcelles=parcelles[1:], batiments=batiments)
    assert chantiers.avancer_chantiers(monde) == {(c, "batiment", 0): paysans, (c, "batiment", 1): 0}
    assert [b.travail_fourni for b in monde.plans[c].batiments] == [paysans, 0]
    assert sum(lire_habitants_par_metier(monde.cells[c]).values()) == population
    monde = World.charger(0)
    monde.plans[c] = plan
    monde.cells[c].habitants_par_metier = None
    avant = monde.to_dict()
    assert chantiers.avancer_chantiers(monde) == {cle: 0 for cle in attendu}
    assert monde.to_dict() == avant and monde.plans[c] is plan
    monde = World.charger(0)
    _financer(monde, c)
    monkeypatch.setitem(monde.plans, c, Plan(rues=[Rue(5, rue.points, rue.largeur_m)],
                                           parcelles=parcelles, batiments=batiments))
    envois = chantiers.avancer_chantiers(monde)
    assert envois == {(c, "parcelle", 0): paysans, (c, "batiment", 0): 0, (c, "batiment", 1): 0}
    with pytest.raises(AssertionError):
        assert envois == attendu


def test_batiment_attend_sa_parcelle(monkeypatch):
    from sim import chantiers
    from sim.plan import Batiment, Parcelle

    monde = World.charger(0)
    c = _route_reference(monde)["cell"]
    t = k.TAILLE_FOYER
    assert lire_habitants_par_metier(monde.cells[c])[k.METIER_PAYSANS] > 2 * t > 0
    triangle = [(0, 0), (1, 0), (0, 1)]
    parcelle = Parcelle(0, triangle, True, 1, t, 0)
    batiment = Batiment(0, 0, "four", triangle, True, 1, 3 * t, 0)
    plan = Plan(parcelles=[parcelle], batiments=[batiment])
    _financer(monde, c)
    monde.plans[c] = plan
    assert chantiers.avancer_chantiers(monde) == {(c, "parcelle", 0): t, (c, "batiment", 0): 0}
    assert not monde.plans[c].parcelles[0].en_chantier
    assert monde.plans[c].batiments[0].travail_fourni == 0
    assert lire_habitants_par_metier(monde.cells[c])[k.METIER_PAYSANS] > 0
    assert chantiers.avancer_chantiers(monde) == {(c, "batiment", 0): t}
    monde = World.charger(0)
    _financer(monde, c)
    monde.plans[c] = Plan(parcelles=[parcelle, Parcelle(1, triangle)],
                          batiments=[batiment, Batiment(1, 1, "four", triangle, True, 1, 3 * t, 0)])
    assert chantiers.avancer_chantiers(monde) == {
        (c, "parcelle", 0): t, (c, "batiment", 0): 0, (c, "batiment", 1): t}
    monde = World.charger(0)
    _financer(monde, c)
    monkeypatch.setitem(monde.plans, c, Plan(parcelles=[Parcelle(0, triangle)], batiments=[batiment]))
    assert chantiers.avancer_chantiers(monde) == {(c, "batiment", 0): t}
    with pytest.raises(AssertionError):
        assert monde.plans[c].batiments[0].travail_fourni == 0


@pytest.mark.parametrize("nature", ["maison", "scierie", "four"])
def test_batiment_compte(nature, monkeypatch):
    from sim import chantiers
    from sim.plan import Batiment, Parcelle

    monde = World.charger(0)
    c = _route_reference(monde)["cell"]
    requis = 3 * k.TAILLE_FOYER - 2
    assert requis % k.TAILLE_FOYER != 0
    triangle = [(0, 0), (1, 0), (0, 1)]
    depart = Plan(parcelles=[Parcelle(0, triangle)],
                  batiments=[Batiment(0, 0, nature, triangle, True, 1, requis, 0)])
    _financer(monde, c)
    monde.plans[c] = depart
    cell = monde.cells[c]
    population, paysans = cell.population, lire_habitants_par_metier(cell)[k.METIER_PAYSANS]
    assert paysans >= k.TAILLE_FOYER > 0
    total = 0
    for attendu in (k.TAILLE_FOYER, k.TAILLE_FOYER, requis - 2 * k.TAILLE_FOYER):
        assert chantiers.avancer_chantiers(monde) == {(c, "batiment", 0): attendu}
        total += attendu
        _controler_compte(cell, monde.plans[c].batiments[0], attendu, total, population, paysans)
    assert total == requis
    assert chantiers.avancer_chantiers(monde) == {}
    _controler_compte(cell, monde.plans[c].batiments[0], 0, requis, population, paysans)
    plan = monde.plans[c]
    with monkeypatch.context() as sonde:
        sonde.setattr(chantiers, "ecrire_habitants_par_metier", lambda *a: pytest.fail("écriture inutile"))
        sonde.setattr(chantiers, "Plan", lambda **kw: pytest.fail("plan reconstruit sans travail"))
        assert chantiers.avancer_chantiers(monde) == {} and monde.plans[c] is plan
    monde.plans[c] = depart
    with monkeypatch.context() as sonde:
        sonde.setattr(chantiers, "Plan", lambda **kw: depart)
        assert chantiers.avancer_chantiers(monde) == {(c, "batiment", 0): k.TAILLE_FOYER}
        assert monde.plans[c].batiments[0].travail_fourni == 0
        with pytest.raises(AssertionError):
            assert monde.plans[c].batiments[0].travail_fourni == k.TAILLE_FOYER


def test_batiment_tick(monkeypatch):
    from sim.chantiers import travail_requis_de_batiment
    from sim.plan import Batiment, Parcelle
    from sim.tests.test_intentions import _batiment_reference

    reference = World.charger(0)
    geste = _batiment_reference(reference)
    c = geste["cell"]
    contour = reference.plans[c].parcelles[0].contour
    route = _route_reference(reference)
    requis = travail_requis_de_batiment(contour)
    f = math.ceil(requis / (3 * k.TAILLE_FOYER))
    bras = f * k.TAILLE_FOYER
    assert 2 * bras < requis <= 3 * bras
    assert 0 < bras <= lire_habitants_par_metier(reference.cells[c])[k.METIER_PAYSANS]
    base = Plan(rues=[Rue(0, route["points"], 4)], parcelles=[Parcelle(0, contour)])
    production = engine._apply_production

    def jouer(financer_temoin=True):
        mondes = [World.charger(0) for _ in range(3)]
        aleas = [random.Random(0) for _ in mondes]
        for i, monde in enumerate(mondes):
            _financer(monde, c)
            monde.plans[c] = base
            if i < 2:
                recevoir_intention(monde, geste | {"foyers": f})
        releves = []

        def relever(cell, *a, **kw):
            if cell is mondes[0].cells[c]:
                releves.append(lire_habitants_par_metier(cell).get(k.METIER_OUVRIERS, 0))
            return production(cell, *a, **kw)

        with monkeypatch.context() as sonde:
            sonde.setattr(engine, "_apply_production", relever)
            if financer_temoin: _temoin_salaire(sonde, mondes[2], c, [bras, bras, requis - 2 * bras] + [0] * 2)
            for i in range(5):
                for monde, alea in zip(mondes, aleas):
                    engine.tick(monde, alea, numero_tick=i)
        assert mondes[0].to_dict() == mondes[1].to_dict()
        assert aleas[0].getstate() == aleas[1].getstate() == aleas[2].getstate()
        _cellules_identiques_sauf_metiers(mondes[2], mondes[0], c)
        a, b = mondes[0].to_dict()["plans"], mondes[2].to_dict()["plans"]
        assert a and a.keys() == b.keys()
        assert all(a[cle] == b[cle] for cle in a if cle != str(c))
        assert {cle: v for cle, v in a[str(c)].items() if cle != "batiments"} == {
            cle: v for cle, v in b[str(c)].items() if cle != "batiments"}
        assert not b[str(c)]["batiments"]
        return mondes[0].plans[c].batiments[0], releves

    batiment, releves = jouer()
    assert releves == [bras, bras, requis - 2 * bras, 0, 0]
    assert not batiment.en_chantier and batiment.travail_fourni == batiment.travail_requis == requis
    with monkeypatch.context() as sonde:
        sonde.setattr(engine, "_avancer_chantiers", lambda monde: None)
        faux, _ = jouer(False)
        assert faux.travail_fourni == 0
        with pytest.raises(AssertionError):
            assert not faux.en_chantier

    def comparer_acheve():
        mondes = [World.charger(0) for _ in range(2)]
        aleas = [random.Random(0) for _ in mondes]
        for monde in mondes: _financer(monde, c)
        mondes[0].plans[c] = Plan(rues=base.rues, parcelles=base.parcelles, batiments=[cas["batiment"]])
        mondes[1].plans[c] = base
        for i in range(3):
            for monde, alea in zip(mondes, aleas):
                engine.tick(monde, alea, numero_tick=i)
        assert aleas[0].getstate() == aleas[1].getstate()
        return mondes

    acheve = Batiment(0, 0, "maison", contour, False, 1, requis, requis)
    cas = {"batiment": acheve}
    mondes = comparer_acheve()
    assert mondes[0].to_dict()["cells"] == mondes[1].to_dict()["cells"]
    assert mondes[0].plans[c].batiments == [acheve]
    with monkeypatch.context() as sonde:
        sonde.setitem(cas, "batiment", replace(acheve, en_chantier=True, travail_fourni=0))
        mondes = comparer_acheve()
        with pytest.raises(AssertionError):
            assert mondes[0].to_dict()["cells"] == mondes[1].to_dict()["cells"]


def test_documentation_chantier_batiment(monkeypatch):
    dossier = Path(engine.__file__).parent
    lire = Path.read_text

    def controler():
        texte = (dossier / "MODELE.md").read_text(encoding="utf-8")
        sections = {titre: texte.split(f"## {titre}\n", 1)[1].split("\n## ", 1)[0]
                    for titre in ("Le chantier et ses bras", "Ce que le moteur ne fait pas encore", "En une page")}
        assert '"batiment"' in sections["Le chantier et ses bras"]
        assert "Aucune étape ne sert encore un bâtiment" not in sections["Le chantier et ses bras"]
        assert "aucune étape ne le servant encore" not in sections["Ce que le moteur ne fait pas encore"]
        assert "bâtiments" in sections["En une page"]
        assert "journées de route puis de parcelle puis de bâtiment" in (dossier / "engine.py").read_text(encoding="utf-8")
        assert "aucune étape ne lui fournissant encore" not in (dossier / "README.md").read_text(encoding="utf-8")

    controler()
    for fichier, ancien, nouveau in (
        ("MODELE.md", "## Le chantier et ses bras\n", "## Le chantier et ses bras\nAucune étape ne sert encore un bâtiment\n"),
        ("engine.py", " puis de bâtiment", ""),
    ):
        with monkeypatch.context() as sonde:
            sonde.setattr(Path, "read_text", lambda path, *a, **kw: lire(path, *a, **kw).replace(ancien, nouveau)
                          if path.name == fichier else lire(path, *a, **kw))
            with pytest.raises(AssertionError):
                controler()


def _contre_ateliers(monkeypatch, module, nom, faux, controler):
    with monkeypatch.context() as ctx:
        ctx.setattr(module, nom, faux, raising=False)
        with pytest.raises(AssertionError): controler()

def _atelier(surface=80, nature="four", personnes=None):
    from sim.model import Cell, ecrire_habitants_par_metier; from sim.plan import Batiment, Parcelle; contour = [(0, 0), (surface, 0), (surface, 1), (0, 1)]; monde = World({0: Cell(0, 100, 0)}, [])
    from sim.model import EtatDeLieu
    monde.cells[0].lieux = [EtatDeLieu(0, 100, {}, maitre='atelier')]; monde.greniers = {'atelier': {}}; _financer(monde, 0)
    ecrire_habitants_par_metier(monde.cells[0], personnes if personnes is not None else {"paysans": 100}); monde.plans[0] = Plan(parcelles=[Parcelle(0, contour)], batiments=[Batiment(0, 0, nature, contour)]); return monde

@pytest.mark.parametrize("surface", [20, 40, 80])
def test_ateliers_effectifs(surface, monkeypatch):
    from sim import ateliers
    def controler():
        monde = _atelier(surface, personnes={"paysans": k.TAILLE_FOYER + 2, "mineurs": 1, "ouvriers": 1}); plan, cell = monde.plans[0], monde.cells[0]
        plan.batiments = [replace(plan.batiments[0], identifiant=i, nature=n, **kw) for i, n, kw in
                           [(1, "four", {}), (0, "scierie", {}), (2, "maison", {}),
                            (3, "four", {"en_chantier": True, "foyers": 1, "travail_requis": 1})]]
        total, population = k.TAILLE_FOYER + 2, cell.population; premier = min(total, max(1, int(surface // k.SURFACE_M2_PAR_FOYER_ARTISAN)) * k.TAILLE_FOYER)
        for _ in range(2):
            assert ateliers.affecter_artisans(monde) == {(0, 0): premier, (0, 1): total - premier}; assert lire_habitants_par_metier(cell) == {"artisans": total, "mineurs": 1, "ouvriers": 1}
            assert cell.population == population == sum(cell.habitants_par_metier.values()) and monde.plans[0] is plan
        plan.batiments = []; ateliers.affecter_artisans(monde); assert lire_habitants_par_metier(cell) == {"paysans": total, "mineurs": 1, "ouvriers": 1}
        with monkeypatch.context() as ctx:
            ctx.setattr(ateliers, "ecrire_habitants_par_metier", lambda *a: pytest.fail("écriture inutile")); assert ateliers.affecter_artisans(monde) == {}
            for metiers in (None, {}):
                vide = _atelier(personnes={"paysans": k.TAILLE_FOYER} if metiers is None else {}); population = vide.cells[0].population; vide.cells[0].habitants_par_metier = metiers; assert ateliers.affecter_artisans(vide) == {(0, 0): 0}; assert lire_habitants_par_metier(vide.cells[0]) == (-1 if metiers is None else {}) and vide.cells[0].population == population
    controler()
    for cible, faux in (("sorted", lambda xs, **kw: list(reversed(sorted(xs, **kw)))),
                        ("lire_habitants_par_metier", lambda c: {m: n for m, n in c.habitants_par_metier.items() if m != "artisans"})):
        _contre_ateliers(monkeypatch, ateliers, cible, faux, controler)

@pytest.mark.parametrize("requis", [1, 2 * k.TAILLE_FOYER + 1])
def test_ateliers_tick(requis, monkeypatch):
    def controler():
        monde = _atelier(personnes={"paysans": k.TAILLE_FOYER + 1}); monde.plans[0].batiments[0] = replace(monde.plans[0].batiments[0], en_chantier=True, foyers=1, travail_requis=requis); cell, releves = monde.cells[0], []
        cell.food_stock_kg = 100; fabrication, recolte = engine._apply_fabrication, engine._apply_production
        def relever(c):
            releves.append(lire_habitants_par_metier(c)); fabrication(c)
        def recolter(c, *a, **kw):
            assert lire_habitants_par_metier(c) == releves[-1]; avant = c.food_stock_kg; recolte(c, *a, **kw)
            nominal = c.area_km2 * k.FOOD_PRODUCTION_KG_PER_KM2_PER_TICK * random.Random(0).uniform(k.RNG_YIELD_LOW, k.RNG_YIELD_HIGH)
            facteur = min(1, releves[-1].get("paysans", 0) / (c.area_km2 * k.BRAS_AUX_CHAMPS_PAR_KM2))
            assert 0 <= facteur < 1 and c.food_stock_kg - avant == pytest.approx(nominal * facteur)
        with monkeypatch.context() as ctx:
            ctx.setattr(engine, "_apply_fabrication", relever); ctx.setattr(engine, "_apply_production", recolter)
            for numero in range(2):
                engine.tick(monde, random.Random(0), numero)
        attendu = [{"ouvriers": 1, "artisans": k.TAILLE_FOYER}, {"artisans": k.TAILLE_FOYER + 1}] if requis == 1 else [{"ouvriers": k.TAILLE_FOYER, "paysans": 1}] * 2
        assert releves == attendu and monde.plans[0].batiments[0].en_chantier == (requis > 1); assert sum(releves[0].values()) == sum(releves[1].values()) == k.TAILLE_FOYER + 1
    controler()
    if requis == 1: _contre_ateliers(monkeypatch, engine, "_affecter_artisans", lambda m: None, controler)

@pytest.mark.parametrize("nature", ["scierie", "four"])
def test_ateliers_rejeu(nature, monkeypatch):
    from sim.tests.test_intentions import _batiment_reference; from sim.service import _foyers_du_lieu
    def controler():
        reference = World.charger(0); geste = _batiment_reference(reference) | {"nature": nature, "foyers": 1000}; cid = geste["cell"]
        base = replace(reference.plans[cid].parcelles[0], en_chantier=False, travail_fourni=reference.plans[cid].parcelles[0].travail_requis); mondes, aleas = [World.charger(0) for _ in range(3)], [random.Random(0) for _ in range(3)]
        for i, monde in enumerate(mondes):
            _financer(monde, cid)
            monde.plans[cid] = Plan(parcelles=[base]); assert lire_habitants_par_metier(monde.cells[cid])["paysans"] > 0; monde.cells[cid].stocks["fer"] = 1000
            if i < 2: recevoir_intention(monde, geste)
        for numero in range(3):
            for monde, alea in zip(mondes, aleas):
                engine.tick(monde, alea, numero)
        assert mondes[0].to_dict() == mondes[1].to_dict() and mondes[0].stocks_mer == mondes[1].stocks_mer; assert aleas[0].getstate() == aleas[1].getstate() == aleas[2].getstate(); cell, temoin = mondes[0].cells[cid], mondes[2].cells[cid]
        assert not mondes[0].plans[cid].batiments[0].en_chantier and not mondes[2].plans[cid].batiments; assert _foyers_du_lieu(cell).get("artisans", {}).get("personnes", 0) == lire_habitants_par_metier(cell).get("artisans", 0) > 0
        assert "artisans" not in lire_habitants_par_metier(temoin) and cell.stocks["fer"] < temoin.stocks["fer"]
    controler(); _contre_ateliers(monkeypatch, engine, "_affecter_artisans", lambda m: None, controler)


def test_porte_achevement_ouvre_commerce(monkeypatch):
    from sim.model import ecrire_habitants_par_metier
    from sim.tests.test_commerce import _monde_routes
    commerce = engine._apply_commerce
    def jouer():
        mondes, aleas, mesures = [_monde_routes(), _monde_routes()], [random.Random(0), random.Random(0)], []
        for monde in mondes:
            from sim.tests.test_intentions import _terres_synthetiques
            _terres_synthetiques(monde)
            monde.greniers = {'seigneurie-1': {}}; _financer(monde, 1)
            ecrire_habitants_par_metier(monde.cells[1], {k.METIER_PAYSANS: 100})
            monde.cells[1].food_stock_kg = 10000
            recevoir_intention(monde, _route_reference(monde) | {
                "points": [[0, 0], [6.5, 0]], "porte_cell_id": 2})
        def observer(monde, *args, **kwargs):
            if monde is mondes[0] and len(mesures) == monde.ticks_ecoules:
                rue = monde.plans[1].rues[0]
                _controler_compte(monde.cells[1], rue, lire_habitants_par_metier(monde.cells[1]).get(
                    k.METIER_OUVRIERS, 0), rue.travail_fourni, 100, 100)
                mesures.append((rue.travail_fourni, rue.en_chantier, rue.porte_cell_id,
                                engine._capacite_transport_arete_kg(monde, 1, 2),
                                lire_habitants_par_metier(monde.cells[1]).get(k.METIER_OUVRIERS, 0)))
            return commerce(monde, *args, **kwargs)
        with monkeypatch.context() as sonde:
            sonde.setattr(engine, "_apply_commerce", observer)
            for numero in range(4):
                for monde, alea in zip(mondes, aleas):
                    engine.tick(monde, alea, numero)
                assert mondes[0].to_dict() == mondes[1].to_dict()
                assert aleas[0].getstate() == aleas[1].getstate()
        assert mesures and mondes[0].plans[1].rues
        return mesures
    def controler(mesures):
        assert mesures == [(5, True, 2, 200., 5), (10, True, 2, 200., 5),
                           (13, False, 2, 20200., 3), (13, False, 2, 20200., 0)]
    controler(jouer())
    with monkeypatch.context() as sonde:
        sonde.setattr(engine, "_avancer_chantiers", lambda monde: None)
        with pytest.raises(AssertionError):
            controler(jouer())

def _epreuve_salaire(stock=100):
    from sim.model import Cell, EtatDeLieu
    from sim.plan import Parcelle, Batiment
    triangle = [(0, 0), (1, 0), (0, 1)]
    monde = World({i: Cell(i, 1, 30, stocks={'nourriture': 100, 'fer': 7},
        habitants_par_metier={'paysans': 30}, lieux=[
            EtatDeLieu(1, 20, {'nourriture': 60, 'fer': 7}),
            EtatDeLieu(0, 10, {'nourriture': 40}, maitre='payeur')]) for i in (2, 1)}, [])
    monde.greniers = {'payeur': {'nourriture': stock, 'fer': 11}, 'autre': {'nourriture': 50}}
    monde.plans[1] = Plan(rues=[Rue(0, [(0, 0), (1, 0)], 1, True, 1, 3)],
        parcelles=[Parcelle(0, triangle, True, 1, 2), Parcelle(1, triangle)],
        batiments=[Batiment(0, 1, 'maison', triangle, True, 1, 8)])
    return monde

def _controler_salaire(avant, monde, envois):
    apres = monde.to_dict(); cid = '1'; assert k.SALAIRE_JOURNEE_KG == 3
    travaux = lambda d: [e for nom in ('rues', 'parcelles', 'batiments') for e in d['plans'][cid][nom]]
    deltas = [b['travail_fourni'] - a['travail_fourni'] for a, b in zip(travaux(avant), travaux(apres))]
    assert deltas and all(n > 0 for n in (deltas[0], deltas[1], deltas[-1]))
    jours = sum(deltas); assert jours == sum(envois.values()) > 0; kg = jours * k.SALAIRE_JOURNEE_KG
    assert avant['greniers']['payeur']['nourriture'] - apres['greniers']['payeur']['nourriture'] == kg
    a, b = avant['cells'][cid], apres['cells'][cid]
    assert b['stocks']['nourriture'] - a['stocks']['nourriture'] == b['food_stock_kg'] - a['food_stock_kg'] == kg
    assert sum(l['stocks']['nourriture'] for l in b['lieux']) == b['food_stock_kg']
    assert b['lieux'][0]['stocks']['nourriture'] - a['lieux'][0]['stocks']['nourriture'] == kg
    assert b['lieux'][1] == a['lieux'][1] and b['stocks']['fer'] == a['stocks']['fer']
    assert apres['cells']['2'] == avant['cells']['2']
    assert apres['greniers']['autre'] == avant['greniers']['autre'] and apres['greniers']['payeur']['fer'] == 11

def test_salaire_conservation():
    from sim.chantiers import avancer_chantiers; from sim.lieux import repartir_sur_les_lieux
    monde = _epreuve_salaire(); avant = monde.to_dict()
    envois = avancer_chantiers(monde); _controler_salaire(avant, monde, envois)
    repartir_sur_les_lieux(monde.cells[1]); _controler_salaire(avant, monde, envois)
    monde.greniers['payeur']['nourriture'] = avant['greniers']['payeur']['nourriture']
    with pytest.raises(AssertionError): _controler_salaire(avant, monde, envois)

@pytest.mark.parametrize('absence', [0, 2, 'lieux', 'bourg', 'maitre', 'grenier', 'marchandise', 'metiers'])
@pytest.mark.parametrize('anciens', [False, True])
def test_salaire_vide(absence, anciens):
    from sim.chantiers import avancer_chantiers
    monde = _epreuve_salaire(absence if isinstance(absence, int) else 100); cell = monde.cells[1]
    if absence == 'lieux': cell.lieux = []
    if absence == 'bourg': cell.lieux = cell.lieux[:1]
    if absence == 'maitre': cell.lieux[1].maitre = None
    if absence in ('grenier', 'marchandise'): (monde.greniers if absence == 'grenier' else monde.greniers['payeur']).pop('payeur' if absence == 'grenier' else 'nourriture')
    if anciens: cell.habitants_par_metier = {'paysans': 25, 'ouvriers': 5}
    if absence == 'metiers': cell.habitants_par_metier = None
    avant, plan = monde.to_dict(), monde.plans[1]; envois = avancer_chantiers(monde)
    assert envois and set(envois.values()) == {0} and monde.plans[1] is plan
    if anciens and absence != 'metiers': avant['cells']['1']['foyers'] = {'paysans': dict(personnes=30, complets=30 // k.TAILLE_FOYER, dernier=30 % k.TAILLE_FOYER)}
    assert monde.to_dict() == avant
    contre = _epreuve_salaire(3); reference = contre.to_dict(); assert sum(avancer_chantiers(contre).values()) == 1
    with pytest.raises(AssertionError): assert contre.to_dict() == reference

def test_salaire_partiel(monkeypatch):
    from sim.chantiers import avancer_chantiers
    def jouer(salaire):
        monkeypatch.setattr(k, 'SALAIRE_JOURNEE_KG', salaire); monde = _epreuve_salaire(22)
        monde.plans[2] = Plan(rues=[Rue(0, [(0, 0), (1, 0)], 1, True, 10, 50)])
        envois = avancer_chantiers(monde); jours = 22 // salaire
        assert sum(envois.values()) == jours == sum(e.travail_fourni for p in monde.plans.values() for nom in ('rues', 'parcelles', 'batiments') for e in getattr(p, nom))
        assert monde.greniers['payeur']['nourriture'] == 22 % salaire
        assert envois[(1, 0)] == 3 and envois[(1, 'parcelle', 0)] == 2
        assert envois[(1, 'batiment', 0)] == min(5, jours - 5)
        assert envois[(2, 0)] == max(0, jours - 10)
        assert sum(lire_habitants_par_metier(c).get('ouvriers', 0) for c in monde.cells.values()) == jours
        assert sum(lire_habitants_par_metier(c).get('paysans', 0) for c in monde.cells.values()) == 60 - jours
        return jours
    assert jouer(3) == 7 and jouer(2) == 11

def test_salaire_rythme():
    from sim.chantiers import avancer_chantiers
    monde = _epreuve_salaire(13 * 3); monde.plans[1] = Plan(rues=[Rue(0, [(0, 0), (1, 0)], 1, True, 1, 13)])
    for fourni in (0, 5, 10):
        attendu = min(30, k.TAILLE_FOYER, 13 - fourni)
        assert avancer_chantiers(monde) == {(1, 0): attendu}
        assert monde.plans[1].rues[0].travail_fourni == fourni + attendu
    assert not monde.plans[1].rues[0].en_chantier and monde.greniers['payeur']['nourriture'] == 0
    assert avancer_chantiers(monde) == {} and lire_habitants_par_metier(monde.cells[1]) == {'paysans': 30}
    vide = _epreuve_salaire(0); assert sum(avancer_chantiers(vide).values()) == 0
    with pytest.raises(AssertionError): assert vide.plans[1].rues[0].travail_fourni == vide.plans[1].rues[0].travail_requis


def _attendu_chantiers(avant, monde, envois, salaire, motifs=None):
    attendu = {}
    for cid, plan in avant['plans'].items():
        for nom, cle in (('rues', ()), ('parcelles', ('parcelle',)), ('batiments', ('batiment',))):
            apres = {e.identifiant: e for e in getattr(monde.plans[int(cid)], nom)}
            for element in plan[nom]:
                if element['en_chantier']:
                    identifiant = element['identifiant']; index = (int(cid), *cle, identifiant)
                    bras = apres[identifiant].travail_fourni - element['travail_fourni']
                    assert envois[index] == bras
                    attendu[index] = dict(bras=bras, grain_paye_kg=bras * salaire,
                                         motif_arret=(motifs or {}).get(index))
    assert attendu and set(attendu) == set(envois)
    return attendu


def _verifier_chantiers(releve, attendu):
    assert attendu and releve == attendu


def test_releve_chantiers_comptes():
    from sim.chantiers import avancer_chantiers
    monde = _epreuve_salaire(); avant = monde.to_dict()
    assert monde.chantiers_du_jour == {}
    envois = avancer_chantiers(monde); _controler_salaire(avant, monde, envois)
    attendu = _attendu_chantiers(avant, monde, envois, k.SALAIRE_JOURNEE_KG)
    _verifier_chantiers(monde.chantiers_du_jour, attendu)
    assert all(e['bras'] > 0 for e in attendu.values())
    assert sum(e['grain_paye_kg'] for e in attendu.values()) == avant['greniers']['payeur']['nourriture'] - monde.greniers['payeur']['nourriture']
    faux = copy.deepcopy(attendu); cles = list(faux); faux[cles[0]], faux[cles[1]] = faux[cles[1]], faux[cles[0]]
    with pytest.raises(AssertionError): _verifier_chantiers(faux, attendu)
    faux = copy.deepcopy(attendu); faux[cles[-1]]['grain_paye_kg'] += 1
    with pytest.raises(AssertionError): _verifier_chantiers(faux, attendu)
    with pytest.raises(AssertionError): _verifier_chantiers({}, {})


@pytest.mark.parametrize('cas', ['parcelle', 'parcelle_sans_metiers', 'metiers', 'bras', 'bras_epuises', 'lieux', 'bourg', 'maitre', 'grenier', 'marchandise', 'grain', 'partage', 'salaire'])
def test_releve_chantiers_arrets(cas):
    from sim.chantiers import avancer_chantiers
    monde = _epreuve_salaire(); cell = monde.cells[1]; motifs = {}
    if cas.startswith('parcelle'): monde.plans[1].batiments[0] = replace(monde.plans[1].batiments[0], parcelle=0)
    if cas == 'bras_epuises': cell.habitants_par_metier = {'paysans': 3}
    if cas in ('metiers', 'bras', 'parcelle_sans_metiers'):
        cell.habitants_par_metier = None if cas != 'bras' else {'mineurs': 30}
        monde.greniers.clear()  # La cause métier précède celle du payeur.
    if cas == 'lieux': cell.lieux = []
    if cas == 'bourg': cell.lieux = cell.lieux[:1]
    if cas == 'maitre': cell.lieux[1].maitre = None
    if cas == 'grenier': monde.greniers.clear()
    if cas == 'marchandise': monde.greniers['payeur'].pop('nourriture')
    if cas in ('grain', 'salaire', 'partage'): monde.greniers['payeur']['nourriture'] = k.SALAIRE_JOURNEE_KG if cas == 'salaire' else (3 * k.SALAIRE_JOURNEE_KG if cas == 'partage' else 0)
    if cas == 'partage': monde.plans[2] = Plan(rues=[Rue(0, [(0, 0), (1, 0)], 1, True, 1, 10)])
    cause = {'metiers': 'metiers_non_calcules', 'parcelle_sans_metiers': 'metiers_non_calcules', 'bras': 'sans_bras', 'bras_epuises': 'sans_bras', 'lieux': 'payeur_absent', 'bourg': 'payeur_absent', 'maitre': 'payeur_absent', 'grenier': 'payeur_absent'}.get(cas, 'sans_grain')
    avant = monde.to_dict(); envois = avancer_chantiers(monde)
    motifs = {cle: cause for cle, bras in envois.items() if bras == 0}
    if cas.startswith('parcelle'):
        motifs[(1, 'batiment', 0)] = 'parcelle_en_chantier'
        if cas == 'parcelle': assert not monde.plans[1].parcelles[0].en_chantier
    attendu = _attendu_chantiers(avant, monde, envois, k.SALAIRE_JOURNEE_KG, motifs)
    _verifier_chantiers(monde.chantiers_du_jour, attendu)
    if cas == 'salaire': assert attendu[(1, 0)] == dict(bras=1, grain_paye_kg=k.SALAIRE_JOURNEE_KG, motif_arret=None)
    for cle in motifs:
        faux = copy.deepcopy(attendu); del faux[cle]
        with pytest.raises(AssertionError): _verifier_chantiers(faux, attendu)
        faux = copy.deepcopy(attendu); faux[cle]['motif_arret'] = 'autre'
        with pytest.raises(AssertionError): _verifier_chantiers(faux, attendu)


def test_releve_chantiers_jour(monkeypatch):
    from sim.chantiers import avancer_chantiers
    monde = _epreuve_salaire(1000); requis = 2 * k.TAILLE_FOYER + 1
    monde.plans[1] = Plan(rues=[Rue(0, [(0, 0), (1, 0)], 1, True, 1, requis)])
    precedent = None
    for salaire in (3, 2, 4):
        monkeypatch.setattr(k, 'SALAIRE_JOURNEE_KG', salaire); avant = monde.to_dict()
        envois = avancer_chantiers(monde); attendu = _attendu_chantiers(avant, monde, envois, salaire)
        _verifier_chantiers(monde.chantiers_du_jour, attendu)
        if precedent:
            with pytest.raises(AssertionError): _verifier_chantiers(precedent, attendu)
            faux = copy.deepcopy(attendu); faux[(1, 0)]['bras'] = monde.plans[1].rues[0].travail_fourni
            with pytest.raises(AssertionError): _verifier_chantiers(faux, attendu)
        precedent = monde.chantiers_du_jour
    assert precedent[(1, 0)]['bras'] == 1 and precedent[(1, 0)]['grain_paye_kg'] == 4
    assert avancer_chantiers(monde) == {} and monde.chantiers_du_jour == {}
    assert lire_habitants_par_metier(monde.cells[1]) == {'paysans': 30}
    monde = _epreuve_salaire(2 * k.TAILLE_FOYER * 4)
    monde.plans[1] = Plan(rues=[Rue(0, [(0, 0), (1, 0)], 1, True, 1, requis)])
    for _ in range(3):
        avant = monde.to_dict(); envois = avancer_chantiers(monde)
        motifs = {cle: 'sans_grain' for cle, bras in envois.items() if not bras}
        _verifier_chantiers(monde.chantiers_du_jour, _attendu_chantiers(avant, monde, envois, 4, motifs))
    assert monde.chantiers_du_jour[(1, 0)] == dict(bras=0, grain_paye_kg=0, motif_arret='sans_grain')


def test_releve_chantiers_purete():
    mondes = [World.charger(0) for _ in range(2)]; aleas = [random.Random(0) for _ in mondes]
    cid = next(c for c, cell in sorted(mondes[0].cells.items()) if any(l.rang == 0 and l.maitre for l in cell.lieux))
    for monde in mondes:
        monde.plans[cid] = _epreuve_salaire().plans[1]
        for grenier in monde.greniers.values(): grenier['nourriture'] = 1000
    def etat(monde, alea): return monde.to_dict(), monde.stocks_mer, alea.getstate()
    for faux in ({}, {(cid, 0): dict(bras=999, grain_paye_kg=-1, motif_arret='faux')}, {}):
        mondes[1].chantiers_du_jour = faux
        assert engine.tick(mondes[0], aleas[0]) == engine.tick(mondes[1], aleas[1])
        assert etat(mondes[0], aleas[0]) == etat(mondes[1], aleas[1])
        assert mondes[0].chantiers_du_jour == mondes[1].chantiers_du_jour
    copie = copy.deepcopy(mondes[0]); rue = copie.plans[cid].rues[0]
    copie.plans[cid].rues[0] = replace(rue, travail_requis=rue.travail_requis + 1, travail_fourni=rue.travail_fourni + 1)
    with pytest.raises(AssertionError): assert etat(copie, aleas[0]) == etat(mondes[0], aleas[0])


def _autoconstruction(n=1, personnes=None):
    from sim.plan import Parcelle
    monde = _atelier(k.SURFACE_M2_PAR_FOYER_LOGE, personnes={"artisans": n * k.TAILLE_FOYER} if personnes is None else personnes)
    contour = monde.plans[0].parcelles[0].contour
    monde.plans[0] = Plan(parcelles=[Parcelle(i, contour) for i in reversed(range(n))]); monde.greniers['atelier'] = {}
    return monde


def test_autoconstruction_dix(monkeypatch):
    from sim import chantiers, logement
    from sim.plan import aire_du_contour
    def jouer():
        monde = _autoconstruction(10); observations = []; requis = chantiers.travail_requis_de_batiment(monde.plans[0].parcelles[0].contour)
        for jour in range(10 + requis):
            chantiers.avancer_chantiers(monde); maisons = monde.plans[0].batiments
            assert [b.parcelle for b in maisons] == list(range(min(jour + 1, 10)))
            capacite = sum(max(1, int(aire_du_contour(b.emprise) // k.SURFACE_M2_PAR_FOYER_LOGE)) for b in maisons if not b.en_chantier)
            assert logement.logement_de(monde.cells[0], monde.plans[0])['capacite'] == capacite
            observations.append(len(maisons))
        assert len(maisons) == 10 and all(b.travail_fourni == b.travail_requis for b in maisons)
        assert lire_habitants_par_metier(monde.cells[0]) == {'artisans': 10 * k.TAILLE_FOYER}
        assert logement.logement_de(monde.cells[0], monde.plans[0]) == dict(capacite=10, loges=10, sans_logis=0)
        return observations
    def verifier(observations):
        assert len(observations) >= 10 and observations[:10] == list(range(1, 11))
    verifier(jouer())
    with pytest.raises(AssertionError): verifier([0] * 10)
    with monkeypatch.context() as ctx:
        ctx.setattr(chantiers, '_ouvrir_maisons', lambda plan, *a: plan)
        with pytest.raises(AssertionError): verifier(jouer())


def test_autoconstruction_limites(monkeypatch):
    from sim import chantiers
    from sim.plan import Batiment
    def jouer(cas, limite=1):
        monde = _autoconstruction(2); plan, cell = monde.plans[0], monde.cells[0]; contour = plan.parcelles[0].contour
        if cas == 'vide': plan.parcelles.clear()
        if cas in ('occupe', 'promis', 'loge'):
            plan.batiments = [Batiment(i, i, 'four' if cas == 'occupe' else 'maison', contour, cas != 'loge', 1, 10 if cas != 'loge' else 0) for i in range(2)]
        if cas == 'promis': plan.batiments = [replace(plan.batiments[0], emprise=[(x * 2, y) for x, y in contour])]
        if cas == 'preparation': plan.parcelles = [replace(p, en_chantier=True, foyers=1, travail_requis=1) for p in plan.parcelles]
        if cas in ('artisans', 'metiers'): cell.habitants_par_metier = {'paysans': cell.population} if cas == 'artisans' else None
        if cas == 'bourg': cell.lieux.clear()
        if cas == 'maitre': cell.lieux[0].maitre = None
        if cas == 'incomplet': cell.population = 1
        if cas == 'deux': monde.cells[1] = copy.deepcopy(cell); monde.cells[1].cell_id = 1; monde.plans[1] = copy.deepcopy(plan)
        avant = sum(len(p.batiments) for p in monde.plans.values()); chantiers.avancer_chantiers(monde)
        ouvertures = sum(len(p.batiments) for p in monde.plans.values()) - avant
        assert ouvertures == (2 if cas == 'deux' else min(limite, 2) if cas in ('libre', 'incomplet') else 0)
        if cas == 'libre':
            chantiers.avancer_chantiers(monde); chantiers.avancer_chantiers(monde)
            assert len(monde.plans[0].batiments) == min(2, limite * 3)
    for cas in ('vide', 'occupe', 'promis', 'loge', 'preparation', 'artisans', 'metiers', 'bourg', 'maitre', 'incomplet', 'deux', 'libre'): jouer(cas)
    for limite in (0, 2):
        with monkeypatch.context() as ctx:
            ctx.setattr(k, 'MAISONS_OUVERTES_PAR_JOUR', limite); jouer('libre', limite)
            from types import SimpleNamespace
            ctx.setattr(chantiers, '_constantes', SimpleNamespace(**(vars(k) | {'MAISONS_OUVERTES_PAR_JOUR': 1})))
            with pytest.raises(AssertionError): jouer('libre', limite)
    monde = _autoconstruction(1, {'paysans': 1, 'artisans': 1}); monde.greniers['atelier'] = {'nourriture': k.SALAIRE_JOURNEE_KG}
    monde.plans[0].parcelles[0] = replace(monde.plans[0].parcelles[0], en_chantier=True, foyers=1, travail_requis=1)
    chantiers.avancer_chantiers(monde); assert not monde.plans[0].batiments
    chantiers.avancer_chantiers(monde); assert len(monde.plans[0].batiments) == 1
    ouvrir = chantiers._ouvrir_maisons
    for cas in ('occupe', 'promis'):
        def ignorer(plan, *args):
            faux = copy.deepcopy(plan); faux.batiments.clear(); ajout = ouvrir(faux, *args).batiments
            return Plan(parcelles=plan.parcelles, batiments=plan.batiments + [replace(b, identifiant=max(e.identifiant for e in plan.batiments) + 1 + i) for i, b in enumerate(ajout)])
        with monkeypatch.context() as ctx:
            ctx.setattr(chantiers, '_ouvrir_maisons', ignorer)
            with pytest.raises(AssertionError): jouer(cas)


def test_autoconstruction_journees(monkeypatch):
    from sim import chantiers
    def jouer(mixte=False):
        monde = _autoconstruction(2, {'artisans': 1, 'paysans': k.TAILLE_FOYER} if mixte else {'artisans': 1}); cell = monde.cells[0]
        if mixte:
            monde.plans[0].rues = [Rue(0, [(0, 0), (1, 0)], 1, True, 1, 1)]; monde.greniers['atelier'] = {'nourriture': k.SALAIRE_JOURNEE_KG}
        for jour in range(chantiers.travail_requis_de_batiment(monde.plans[0].parcelles[0].contour) + 1):
            grenier = copy.deepcopy(monde.greniers); avant = monde.to_dict(); travail = sum(b.travail_fourni for b in monde.plans[0].batiments); envois = chantiers.avancer_chantiers(monde)
            gain = sum(b.travail_fourni for b in monde.plans[0].batiments) - travail; metiers = lire_habitants_par_metier(cell)
            bras = sum(v for cle, v in envois.items() if 'batiment' in cle); assert gain == bras == metiers.get(k.METIER_AUTOCONSTRUCTEURS, 0)
            assert metiers.get('artisans', 0) + bras == 1 and sum(metiers.values()) == cell.population == sum(avant['cells']['0']['foyers'][m]['personnes'] for m in avant['cells']['0']['foyers'])
            for cle, v in envois.items():
                if 'batiment' in cle: assert v <= 1 and monde.chantiers_du_jour[cle] == dict(bras=v, grain_paye_kg=0, motif_arret=None if v else 'sans_bras')
            salaire = envois.get((0, 0), 0) * k.SALAIRE_JOURNEE_KG
            assert grenier['atelier'].get('nourriture', 0) - monde.greniers['atelier'].get('nourriture', 0) == salaire
            assert cell.stocks == avant['cells']['0']['stocks'] | ({'nourriture': avant['cells']['0']['stocks'].get('nourriture', 0) + salaire} if salaire else {})
            assert cell.lieux[0].stocks == avant['cells']['0']['lieux'][0]['stocks'] | ({'nourriture': avant['cells']['0']['lieux'][0]['stocks'].get('nourriture', 0) + salaire} if salaire else {})
        assert not monde.plans[0].batiments[0].en_chantier and metiers.get('artisans') == 1
    jouer(); jouer(True)
    avancer = chantiers.avancer_chantiers
    def salaire_illicite(monde):
        envois = avancer(monde); monde.greniers['atelier']['nourriture'] = monde.greniers['atelier'].get('nourriture', 0) - sum(envois.values()) * k.SALAIRE_JOURNEE_KG; return envois
    with monkeypatch.context() as ctx:
        ctx.setattr(chantiers, 'avancer_chantiers', salaire_illicite)
        with pytest.raises(AssertionError): jouer()
    monde = _autoconstruction(); avancer(monde); monde.cells[0].population = 0
    envois = avancer(monde); assert envois and not any(envois.values()) and lire_habitants_par_metier(monde.cells[0]) == {}
    monde.cells[0].habitants_par_metier = None; avancer(monde); assert all(r['motif_arret'] == 'metiers_non_calcules' for r in monde.chantiers_du_jour.values())
    monde = _autoconstruction(2); avancer(monde); avancer(monde); monde.cells[0].population = 1; monde.cells[0].habitants_par_metier = {'artisans': 1}
    envois = avancer(monde); assert len(envois) == 2 and sum(envois.values()) == 1 and lire_habitants_par_metier(monde.cells[0]) == {k.METIER_AUTOCONSTRUCTEURS: 1}
    servir = chantiers._servir
    for faute in ('double', 'paysans'):
        def corrompre(element, metiers, payables, autonome=False):
            resultat, bras = servir(element, metiers, payables, autonome)
            if autonome and bras:
                source = k.METIER_AUTOCONSTRUCTEURS; metiers.pop(source); metiers['artisans' if faute == 'double' else 'paysans'] = metiers.get('artisans' if faute == 'double' else 'paysans', 0) + bras
            return resultat, bras
        with monkeypatch.context() as ctx:
            ctx.setattr(chantiers, '_servir', corrompre)
            with pytest.raises(AssertionError): jouer()


def test_autoconstruction_tick(monkeypatch):
    from sim import chantiers
    def jouer():
        mondes = [_autoconstruction() for _ in range(3)]; aleas = [random.Random(0) for _ in mondes]; observations = []
        for i, monde in enumerate(mondes):
            atelier = _atelier(k.SURFACE_M2_PAR_FOYER_LOGE).plans[0].batiments[0]; monde.plans[0].batiments = [replace(atelier, parcelle=1)]
            monde.plans[0].parcelles.append(replace(monde.plans[0].parcelles[0], identifiant=1)); monde.cells[0].food_stock_kg = 100000; monde.cells[0].stocks['fer'] = 100000
            if i == 2: monde.plans[0].parcelles = monde.plans[0].parcelles[1:]
        fabrication = engine._apply_fabrication
        def observer(cell):
            metiers = lire_habitants_par_metier(cell); bras = metiers.get(k.METIER_AUTOCONSTRUCTEURS, 0)
            if cell is mondes[0].cells[0]: observations.append(bras)
            assert metiers.get('artisans', 0) == cell.population - bras
            avant = cell.stocks['fer']; fabrication(cell)
            assert avant - cell.stocks['fer'] == pytest.approx(k.fabrication_kg(avant)[0] + k.budget_artisanal_kg(metiers.get('artisans', 0)))
        with monkeypatch.context() as ctx:
            ctx.setattr(engine, '_apply_fabrication', observer)
            for jour in range(chantiers.travail_requis_de_batiment(mondes[0].plans[0].parcelles[0].contour) + 1):
                retours = [engine.tick(m, a, jour) for m, a in zip(mondes, aleas)]
                assert mondes[0].to_dict() == mondes[1].to_dict() and retours[0] == retours[1] and aleas[0].getstate() == aleas[1].getstate() == aleas[2].getstate()
        assert observations and observations[0] == 1 and observations[-1] == 0
        assert len(mondes[0].plans[0].batiments) == 2 and not mondes[0].plans[0].batiments[-1].en_chantier and len(mondes[2].plans[0].batiments) == 1
    jouer()
    for nom, faux in (('_avancer_chantiers', lambda m: None), ('_affecter_artisans', lambda m: [setattr(c, 'habitants_par_metier', {'artisans': c.population}) for c in m.cells.values()])):
        with monkeypatch.context() as ctx:
            ctx.setattr(engine, nom, faux)
            with pytest.raises(AssertionError): jouer()


def test_autoconstruction_etat():
    from sim import chantiers
    from dataclasses import asdict
    monde = _autoconstruction(); ordinaire = _atelier().plans[0].batiments[0]
    ancien = asdict(ordinaire); ancien.pop('autoconstruction'); ancien['emprise'] = [list(p) for p in ordinaire.emprise]
    assert Plan(parcelles=_atelier().plans[0].parcelles, batiments=[ordinaire]).to_dict()['batiments'][0] == ancien
    for valeur in (1, 'oui', None):
        with pytest.raises(PlanInvalide): replace(ordinaire, autoconstruction=valeur)
    with pytest.raises(PlanInvalide): replace(ordinaire, autoconstruction=True)
    chantiers.avancer_chantiers(monde); maison = monde.plans[0].batiments[0]
    def verifier(b, document): assert b.autoconstruction is True and document['batiments'][0]['autoconstruction'] is True
    verifier(maison, monde.plans[0].to_dict()); chantiers.avancer_chantiers(monde); verifier(monde.plans[0].batiments[0], monde.plans[0].to_dict())
    with pytest.raises(AssertionError): verifier(replace(maison, autoconstruction=False), monde.plans[0].to_dict())
    faux = monde.plans[0].to_dict(); faux['batiments'][0].pop('autoconstruction')
    with pytest.raises(KeyError): verifier(maison, faux)


def test_autoconstruction_documentation():
    texte = (Path(__file__).parents[1] / 'MODELE.md').read_text(encoding='utf-8').split('## Le chantier et ses bras\n')[1].split('\n## ')[0]
    def verifier(texte): assert 'autoconstruction' in texte and 'sans salaire' in texte
    verifier(texte)
    with pytest.raises(AssertionError): verifier(texte.replace('sans salaire', ''))


def test_autoconstruction_sans_terrain_sans_calcul_logement(monkeypatch):
    from sim import chantiers
    monde = _atelier(personnes={'artisans': k.TAILLE_FOYER}); plan = monde.plans[0]
    monkeypatch.setattr(chantiers, 'ranger_en_foyers', lambda *a: pytest.fail('calcul du logement sans parcelle libre'))
    assert chantiers.avancer_chantiers(monde) == {} and monde.plans[0] is plan
