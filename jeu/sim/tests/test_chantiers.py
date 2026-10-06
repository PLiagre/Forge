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
from sim.tests.test_intentions import _route_reference
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
    a, b = temoin.to_dict()["cells"], monde.to_dict()["cells"]
    assert a and a.keys() == b.keys()
    assert all(a[cle] == b[cle] for cle in a if cle != str(cid))
    assert {cle: v for cle, v in a[str(cid)].items() if cle != "foyers"} == {
        cle: v for cle, v in b[str(cid)].items() if cle != "foyers"}


def test_tick_depart_avant_recolte_et_retour(monkeypatch):
    production = engine._apply_production

    def jouer():
        temoin, monde = World.charger(0), World.charger(0)
        aleas = [random.Random(0), random.Random(0)]
        geste = _courte(monde)
        recevoir_intention(monde, geste)
        releves = []

        def relever(cell, *a, **kw):
            if cell is monde.cells[geste["cell"]]:
                releves.append(lire_habitants_par_metier(cell).get(k.METIER_OUVRIERS, 0))
            return production(cell, *a, **kw)

        with monkeypatch.context() as sonde:
            sonde.setattr(engine, "_apply_production", relever)
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
        faux, _ = jouer()
        assert faux.travail_fourni == 0
        with pytest.raises(AssertionError):
            assert faux.travail_fourni == faux.travail_requis


def test_recolte_diminue_avec_les_bras_envoyes(monkeypatch):
    production = engine._apply_production
    initial = World.charger(0)
    geste = _route_reference(initial)
    cell = initial.cells[geste["cell"]]
    paysans = lire_habitants_par_metier(cell)[k.METIER_PAYSANS]
    km2 = (cell.area_km2 * engine._facteur_relief_pour_cellule(cell, initial.carte)
           * engine._facteur_eau_pour_cellule(cell, initial.carte)
           * engine._facteur_agricole(cell, initial.carte))
    requis = km2 * k.BRAS_AUX_CHAMPS_PAR_KM2
    moyen = (paysans - 1) // k.TAILLE_FOYER
    gros = 2 * math.ceil(paysans / k.TAILLE_FOYER)
    assert 0 < paysans - moyen * k.TAILLE_FOYER < requis
    ticks = 30
    # Même route pour les trois mondes, assez de journées pour le plus gros envoi.
    geste |= {"points": [[0, 0], [(ticks + 1) * gros * k.TAILLE_FOYER
                                 / k.TRAVAIL_ROUTE_JOURNEES_PAR_M2, 0]], "largeur_m": 1}

    def jouer():
        recoltes = []
        for nombre in (None, 1, moyen, gros):
            monde, alea = World.charger(0), random.Random(0)
            cible = monde.cells[geste["cell"]]
            mesures = []
            if nombre is not None:
                recevoir_intention(monde, geste | {"foyers": nombre})

            def relever(cell, *a, **kw):
                avant = cell.food_stock_kg
                production(cell, *a, **kw)
                if cell is cible:
                    mesures.append(cell.food_stock_kg - avant)

            with monkeypatch.context() as sonde:
                sonde.setattr(engine, "_apply_production", relever)
                for i in range(ticks):
                    engine.tick(monde, alea, i)
            assert len(mesures) == ticks > 0
            if nombre is not None:
                assert monde.plans[cible.cell_id].rues[0].en_chantier
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
    monde.plans[c] = plan
    assert chantiers.avancer_chantiers(monde) == {(c, 5): paysans, (c, "parcelle", 0): 0, (c, "parcelle", 1): 0}
    assert monde.plans[c].rues[0].travail_fourni == paysans
    assert all(p.travail_fourni == 0 for p in monde.plans[c].parcelles)
    # Sans rue, l'identifiant départage les parcelles.
    monde = World.charger(0)
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

    def jouer():
        mondes = [World.charger(0) for _ in range(3)]
        aleas = [random.Random(0) for _ in mondes]
        route = _route_reference(mondes[0])
        for i, monde in enumerate(mondes):
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
        faux, _ = jouer()
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
