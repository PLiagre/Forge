"""Preuves et contre-épreuves des foyers par métier, niveau 2."""

import copy
import hashlib
import json
import math
import pathlib
import random

import pytest

import sim.constants as _constantes
from sim import foyers, service
from sim.aggregation import bourg_depuis_monde
from sim.engine import tick
from sim.model import Cell, cellule_vers_dict, lire_habitants_par_metier
from sim.world import World
import sim.engine as engine
from sim.model import (ecrire_habitants_par_metier, ecrire_stock_marchandise,
                       lire_stock_marchandise)


def _controler_somme(metiers, population):
    assert sum(metiers.values()) == population
    assert all(type(n) is int and n > 0 for n in metiers.values())


def test_aller_retour(monkeypatch):
    monde = World.charger(0)
    comptes = [0, 1, 4, 5, 100, 103] + [
        n for cell in monde.cells.values()
        for n in lire_habitants_par_metier(cell).values()
    ]

    def controler(desagreger):
        for n in comptes:
            assert desagreger(foyers.ranger_en_foyers(n)) == n

    with pytest.raises(AssertionError):
        controler(lambda f: f.complets * f.taille)
    controler(foyers.rendre_les_personnes)
    assert foyers.ranger_en_foyers(100) == foyers.Foyers(5, 20, 0)
    assert foyers.ranger_en_foyers(103) == foyers.Foyers(5, 20, 3)
    assert foyers.ranger_en_foyers(100).nombre == 20
    assert foyers.ranger_en_foyers(103).nombre == 21
    with pytest.raises(AttributeError):
        foyers.ranger_en_foyers(103).dernier = 0
    monkeypatch.setattr(_constantes, "TAILLE_FOYER", 10)
    assert foyers.ranger_en_foyers(103) == foyers.Foyers(10, 10, 3)
    print(f"allers_retours={len(comptes)}")
    assert len(comptes) > len(monde.cells) > 0


def test_amorcage(monkeypatch):
    monde = World.charger(0)
    bourgs = {b.cell_id: b.habitants_du_bourg for b in bourg_depuis_monde(monde)}
    avec = sans = 0
    for cid, cell in monde.cells.items():
        metiers = lire_habitants_par_metier(cell)
        _controler_somme(metiers, cell.population)
        part = _constantes.part_miniere_de(
            monde.carte[cid].get("gisements") or [],
            _constantes.facteurs_richesse_extraction(),
        )
        mineurs = int(cell.population * part)
        assert metiers.get(_constantes.METIER_MINEURS, 0) == mineurs == bourgs[cid]
        assert metiers.get(_constantes.METIER_PAYSANS, 0) == cell.population - mineurs
        assert set(metiers) <= {_constantes.METIER_MINEURS, _constantes.METIER_PAYSANS}
        avec += mineurs > 0
        sans += mineurs == 0
        if not mineurs:
            assert _constantes.METIER_MINEURS not in metiers
    assert avec > 0 and sans > 0

    def proportion(m):
        return sum(c.habitants_par_metier.get(_constantes.METIER_MINEURS, 0)
                   for c in m.cells.values()) / sum(c.population for c in m.cells.values())

    monkeypatch.setattr(_constantes, "PART_MINIERE_PAR_GISEMENT",
                        _constantes.PART_MINIERE_PAR_GISEMENT * 2)
    assert proportion(World.charger(0)) > proportion(monde)
    print(f"cellules_avec_mineurs={avec} cellules_sans_mineurs={sans} "
          f"cellules_contrôlées={len(monde.cells)}")
    assert avec + sans == len(monde.cells) > 0


def test_ecriture():
    monde = copy.deepcopy(World.charger(0))
    avec = min(cid for cid, c in monde.cells.items()
               if _constantes.METIER_MINEURS in c.habitants_par_metier)
    sans = min(cid for cid, c in monde.cells.items()
               if _constantes.METIER_MINEURS not in c.habitants_par_metier)
    verifications = 0
    for cid in (avec, sans):
        cell = monde.cells[cid]
        for n in (0, 1, 100):
            cell.population = n
            assert cell.population == n
            _controler_somme(cell.habitants_par_metier, n)
            verifications += 1
        cell.population += 1
        assert cell.population == 101
        _controler_somme(cell.habitants_par_metier, 101)
        cell.population += 1000
        assert cell.population == 1101
        _controler_somme(cell.habitants_par_metier, 1101)
        cell.population -= 1000
        assert cell.population == 101
        _controler_somme(cell.habitants_par_metier, 101)
        cell.population = int(cell.population) + 1
        assert cell.population == 102
        _controler_somme(cell.habitants_par_metier, 102)
        verifications += 4
        cell.population = 0
        assert cell.habitants_par_metier == {}
        cell.population = 7
        assert cell.habitants_par_metier == {_constantes.METIER_PAYSANS: 7}
        for n in (-1, 2.5, True):
            avant = cellule_vers_dict(cell)
            with pytest.raises(foyers.FoyersInvalides):
                cell.population = n
            assert cellule_vers_dict(cell) == avant
    metiers = {"mineurs": 100, "paysans": 900}
    assert foyers.repartir(metiers, 999) == {"mineurs": 99, "paysans": 900}
    assert metiers == {"mineurs": 100, "paysans": 900}
    assert foyers.repartir({"paysans": 1, "mineurs": 1}, 1) == {"mineurs": 1}
    assert foyers.repartir(metiers, 1000) == metiers
    cell = Cell(cell_id=avec, area_km2=10.0, population=1000,
                habitants_par_metier=metiers)
    cell.population = 999
    assert cell.population == 999 and cell.habitants_par_metier == {"mineurs": 99, "paysans": 900}
    grand = 10**30 + 1
    cell.population = grand
    _controler_somme(cell.habitants_par_metier, grand)
    with pytest.raises(AssertionError):
        _controler_somme({m: 999 * n // 1000 for m, n in metiers.items()}, 999)
    monde = World.charger(0)
    rng = random.Random(0)
    for _ in range(30):
        tick(monde, rng)
        for cell in monde.cells.values():
            _controler_somme(cell.habitants_par_metier, cell.population)
            verifications += 1
    print(f"vérifications={verifications}")
    assert verifications > len(monde.cells) > 0


def test_non_calcule(monkeypatch):
    # L'identifiant se lit du monde, même pour les cellules construites à la main.
    cid = min(World.charger(0).cells)

    def cellule(metiers=None):
        return Cell(cell_id=cid, area_km2=10.0, population=50,
                    habitants_par_metier=metiers)

    cell = cellule()
    assert lire_habitants_par_metier(cell) == cellule_vers_dict(cell)["foyers"] == -1
    cell.population = 60
    assert cell.population == 60 and lire_habitants_par_metier(cell) == -1
    coherent = cellule({"paysans": 50})
    copie = lire_habitants_par_metier(coherent)
    copie["paysans"] = 1
    assert lire_habitants_par_metier(coherent) == {"paysans": 50}
    refus = [lambda n=n: cellule({"paysans": n}) for n in (49, 0, -1, True, 2.5)]
    refus += [lambda: cellule({"": 50})]
    refus += [lambda n=n: foyers.ranger_en_foyers(n) for n in (-1, True, 2.5)]
    refus += [lambda args=args: foyers.Foyers(*args)
              for args in ((5, 1, 5), (5, -1, 0), (5, 0, -1), (0, 0, 0), (5, True, 0))]
    observes = 0
    for action in refus:
        with pytest.raises(foyers.FoyersInvalides, match=".+"):
            action()
        observes += 1
    for taille in (0, 2.5, True):
        monkeypatch.setattr(_constantes, "TAILLE_FOYER", taille)
        with pytest.raises(foyers.FoyersInvalides, match="taille"):
            foyers.ranger_en_foyers(100)
        observes += 1
    print(f"refus_observés={observes}")
    assert observes == len(refus) + 3 > 0


def test_serialisation():
    monde = World.charger(0)
    document = monde.to_dict()
    controles = 0
    for cid, cell in monde.cells.items():
        rangements = document["cells"][str(cid)]["foyers"]
        assert set(rangements) == set(cell.habitants_par_metier)
        for metier, n in cell.habitants_par_metier.items():
            f = foyers.ranger_en_foyers(n)
            assert rangements[metier] == {"personnes": n, "complets": f.complets,
                                         "dernier": f.dernier}
            assert f.complets * _constantes.TAILLE_FOYER + f.dernier == n
        assert "foyers" not in service._cellule_legere(cell)
        controles += 1

    def octets(m):
        return json.dumps(m.to_dict(), sort_keys=True).encode()

    assert octets(monde) == octets(World.charger(0))
    copie = copy.deepcopy(monde)
    cid = min(cid for cid, c in copie.cells.items()
              if c.habitants_par_metier.get(_constantes.METIER_PAYSANS, 0) > 1)
    cell = copie.cells[cid]
    cell.habitants_par_metier[_constantes.METIER_PAYSANS] -= 1
    cell.habitants_par_metier[_constantes.METIER_MINEURS] = (
        cell.habitants_par_metier.get(_constantes.METIER_MINEURS, 0) + 1)
    assert copie.to_dict()["cells"][str(cid)]["population"] == document["cells"][str(cid)]["population"]
    assert copie.to_dict() != document
    assert hashlib.sha256(octets(copie)).digest() != hashlib.sha256(octets(monde)).digest()
    print(f"cellules_sérialisées={controles}")
    assert controles == len(monde.cells) > 0


def test_gardes_et_documentation(monkeypatch):
    from sim.tests import test_monde, test_no_hardcoded

    lire = pathlib.Path.read_text
    contre_epreuves = (
        ("foyers.py", "\ndef sonde():\n    return 5\n",
         test_no_hardcoded.test_no_hardcoded_numeric_literals),
        ("world.py", "\ndef sonde():\n    return constantes.PART_MINIERE_MAXIMALE\n",
         test_monde.test_une_seule_definition_part_miniere),
    )
    for nom, ajout, controle in contre_epreuves:
        def source_alteree(path, *args, **kwargs):
            texte = lire(path, *args, **kwargs)
            return texte + ajout if path.name == nom else texte

        with monkeypatch.context() as contexte:
            contexte.setattr(pathlib.Path, "read_text", source_alteree)
            with pytest.raises(AssertionError):
                controle()
    dossier = pathlib.Path(__file__).parents[1]
    modele = (dossier / "MODELE.md").read_text(encoding="utf-8")
    section = modele.split("## Les foyers par métier\n", 1)[1].split("\n## ", 1)[0]
    for attendu in ("TAILLE_FOYER", "part_miniere_de", "paysans", "-1",
                    "le tick ne lit les métiers que pour la récolte"):
        assert attendu.lower() in section.lower()
    assert "sim/foyers.py" in (dossier / "README.md").read_text(encoding="utf-8")
    print(f"contre_épreuves_structurelles={len(contre_epreuves)} sections_contrôlées=1")
    assert len(contre_epreuves) > 0 and section


def _reference_prorata(n, metiers):
    """Règle du lot, écrite ici : le test n'appelle pas sim.foyers pour se juger."""
    if n == 0:
        return {}
    somme = sum(metiers.values())
    if somme <= 0:
        raise AssertionError("prorata de référence sur des métiers vides")
    parts = {}
    for metier, compte in metiers.items():
        quotient = n * compte // somme
        if quotient > 0:
            parts[metier] = quotient
    restant = n - sum(parts.values())
    ordre = sorted(
        metiers,
        key=lambda metier: (-(n * metiers[metier] % somme), metier),
    )
    for metier in ordre[:restant]:
        parts[metier] = parts.get(metier, 0) + 1
    return parts


def _apres_reference(metiers, delta):
    if delta == 0:
        return dict(metiers)
    if delta < 0:
        parts = _reference_prorata(-delta, metiers)
        return {
            metier: compte - parts.get(metier, 0)
            for metier, compte in metiers.items()
            if compte > parts.get(metier, 0)
        }
    if not metiers:
        return {_constantes.METIER_PAYSANS: delta}
    resultat = dict(metiers)
    for metier, part in _reference_prorata(delta, metiers).items():
        resultat[metier] = resultat.get(metier, 0) + part
    return resultat


def _comparer_prorata(obtenu, metiers, n):
    assert obtenu == _reference_prorata(n, metiers)
    assert sum(obtenu.values()) == n


def test_prorata():
    assert foyers.au_prorata(1, {"mineurs": 50, "paysans": 950}) == {"paysans": 1}
    assert foyers.au_prorata(2, {"mineurs": 5, "paysans": 5}) == {"mineurs": 1, "paysans": 1}
    assert foyers.au_prorata(1, {"paysans": 5, "mineurs": 5}) == {"mineurs": 1}
    complet = {"mineurs": 1, "paysans": 9}
    assert foyers.retirer(complet, 10) == {}
    assert complet == {"mineurs": 1, "paysans": 9}
    assert foyers.ajouter({}, 3) == {_constantes.METIER_PAYSANS: 3}
    assert foyers.ajouter({}, 0) == {}

    rng = random.Random(0)
    noms = ("bateliers", "mineurs", "paysans", "tisserands")
    cas_comparés = 0
    while cas_comparés < 200:
        choisis = rng.sample(noms, rng.randrange(1, len(noms) + 1))
        metiers = {nom: rng.randrange(1, 300) for nom in choisis}
        n = rng.randrange(0, sum(metiers.values()) + 1)
        copie = dict(metiers)
        obtenu = foyers.au_prorata(n, metiers)
        _comparer_prorata(obtenu, metiers, n)
        assert metiers == copie
        cas_comparés += 1
    print(f"cas_comparés={cas_comparés}")
    assert cas_comparés > 0

    def reste_intact(appel):
        metiers = {"paysans": 3}
        with pytest.raises(foyers.FoyersInvalides):
            appel(metiers)
        assert metiers == {"paysans": 3}

    reste_intact(lambda metiers: foyers.retirer(metiers, 4))
    for mauvais in (-1, True, 2.5):
        reste_intact(lambda metiers, mauvais=mauvais: foyers.retirer(metiers, mauvais))
        reste_intact(lambda metiers, mauvais=mauvais: foyers.ajouter(metiers, mauvais))
        reste_intact(lambda metiers, mauvais=mauvais: foyers.au_prorata(mauvais, metiers))
    vide = {}
    with pytest.raises(foyers.FoyersInvalides):
        foyers.au_prorata(1, vide)
    assert vide == {}

    def parts_du_retrait_repartir(metiers):
        somme = sum(metiers.values())
        reste = foyers.repartir(dict(metiers), somme - 1)
        return {
            metier: compte - reste.get(metier, 0)
            for metier, compte in metiers.items()
            if compte > reste.get(metier, 0)
        }

    exemple = {"mineurs": 50, "paysans": 950}
    assert parts_du_retrait_repartir(exemple) == {"mineurs": 1}
    with pytest.raises(AssertionError):
        _comparer_prorata(parts_du_retrait_repartir(exemple), exemple, 1)


def _sans_gisement(monde, cid):
    raw = monde.carte.get(cid) or {}
    return not (raw.get("gisements") or [])


def _annee(n_ticks):
    """Joue n ticks et contrôle somme, gisement, puis la variation de chaque maillon."""
    import sim.engine as engine

    monde = World.charger(0)
    rng = random.Random(0)
    mineurs_au_depart = {
        cid for cid, cell in monde.cells.items()
        if _constantes.METIER_MINEURS in (cell.habitants_par_metier or {})
    }
    compteurs = {
        "vérifications": 0,
        "morts_contrôlées": 0,
        "naissances_contrôlées": 0,
        "départs_contrôlés": 0,
        "arrivées_contrôlées": 0,
        "mouvements_en_cellule_minière": 0,
        "cellules_sans_gisement_contrôlées": 0,
    }
    mouvements = []
    mortalite = engine._apply_mortality
    natalite = engine._apply_natalite
    migration = engine._apply_migration

    def photo(cell):
        return cell.population, lire_habitants_par_metier(cell)

    def voir_mortalite(cell):
        avant = photo(cell)
        mortalite(cell)
        mouvements.append(("mort", cell.cell_id, avant, photo(cell)))

    def voir_natalite(cell, penurie_kg):
        avant = photo(cell)
        natalite(cell, penurie_kg)
        mouvements.append(("naissance", cell.cell_id, avant, photo(cell)))

    def voir_migration(world, penuries):
        avant = {cid: photo(cell) for cid, cell in world.cells.items()}
        migration(world, penuries)
        for cid, cell in world.cells.items():
            mouvements.append(("migration", cid, avant[cid], photo(cell)))

    engine._apply_mortality = voir_mortalite
    engine._apply_natalite = voir_natalite
    engine._apply_migration = voir_migration
    try:
        for _ in range(n_ticks):
            tick(monde, rng)
            for cell in monde.cells.values():
                metiers = lire_habitants_par_metier(cell)
                if sum(metiers.values()) != cell.population:
                    raise AssertionError("somme des foyers ≠ population")
                if any(type(n) is not int or n < 1 for n in metiers.values()):
                    raise AssertionError("métier sans foyer")
                compteurs["vérifications"] += 1
                if (cell.cell_id not in mineurs_au_depart
                        and _sans_gisement(monde, cell.cell_id)):
                    if _constantes.METIER_MINEURS in metiers:
                        raise AssertionError("mineurs sans gisement")
                    compteurs["cellules_sans_gisement_contrôlées"] += 1
            for genre, cid, (pop0, met0), (pop1, met1) in mouvements:
                delta = pop1 - pop0
                if delta == 0:
                    continue
                if met1 != _apres_reference(met0, delta):
                    raise AssertionError("variation par métier")
                if genre == "mort":
                    compteurs["morts_contrôlées"] += 1
                elif genre == "naissance":
                    compteurs["naissances_contrôlées"] += 1
                elif delta < 0:
                    compteurs["départs_contrôlés"] += 1
                else:
                    compteurs["arrivées_contrôlées"] += 1
                if cid in mineurs_au_depart:
                    compteurs["mouvements_en_cellule_minière"] += 1
            mouvements.clear()
    finally:
        engine._apply_mortality = mortalite
        engine._apply_natalite = natalite
        engine._apply_migration = migration
    return compteurs


def test_un_an(monkeypatch):
    import sim.engine as engine

    compteurs = _annee(365)
    print(" ".join(f"{nom}={valeur}" for nom, valeur in compteurs.items()))
    assert all(valeur > 0 for valeur in compteurs.values())

    def retirer_direct(cell, n):
        cell.population = cell.population - n

    def ajouter_direct(cell, n):
        cell.population = cell.population + n

    with monkeypatch.context() as ctx:
        ctx.setattr(engine, "_retirer_par_les_foyers", retirer_direct)
        ctx.setattr(engine, "_ajouter_par_les_foyers", ajouter_direct)
        with pytest.raises(AssertionError, match="variation par métier"):
            _annee(30)

    def retirer_brut(cell, n):
        cell.__dict__["population"] = cell.population - n

    def ajouter_brut(cell, n):
        cell.__dict__["population"] = cell.population + n

    with monkeypatch.context() as ctx:
        ctx.setattr(engine, "_retirer_par_les_foyers", retirer_brut)
        ctx.setattr(engine, "_ajouter_par_les_foyers", ajouter_brut)
        with pytest.raises(AssertionError, match="somme des foyers"):
            _annee(30)

    def ajouter_mineurs(metiers, n):
        if n == 0:
            return dict(metiers)
        resultat = dict(metiers)
        cle = _constantes.METIER_MINEURS
        resultat[cle] = resultat.get(cle, 0) + n
        return resultat

    with monkeypatch.context() as ctx:
        ctx.setattr(foyers, "ajouter", ajouter_mineurs)
        with pytest.raises(AssertionError, match="gisement"):
            _annee(30)


def _octets_sans_foyers(monde):
    document = monde.to_dict()
    for cellule in document["cells"].values():
        del cellule["foyers"]
    return json.dumps(document, sort_keys=True).encode()


def _jouer(n_ticks):
    monde = World.charger(0)
    rng = random.Random(0)
    for _ in range(n_ticks):
        tick(monde, rng)
    return monde


def test_bit(monkeypatch):
    import sim.engine as engine

    def retirer_comme_avant(cell, n):
        cell.population = cell.population - n

    def ajouter_comme_avant(cell, n):
        cell.population = cell.population + n

    course_a = _jouer(365)
    with monkeypatch.context() as ctx:
        ctx.setattr(engine, "_retirer_par_les_foyers", retirer_comme_avant)
        ctx.setattr(engine, "_ajouter_par_les_foyers", ajouter_comme_avant)
        course_b = _jouer(365)
    octets_a = _octets_sans_foyers(course_a)
    octets_b = _octets_sans_foyers(course_b)
    print(
        f"sha256_a={hashlib.sha256(octets_a).hexdigest()} "
        f"sha256_b={hashlib.sha256(octets_b).hexdigest()}"
    )
    assert octets_a == octets_b
    comparees = 0
    for cid, cell_a in course_a.cells.items():
        cell_b = course_b.cells[cid]
        assert type(cell_a.population) is int and type(cell_b.population) is int
        assert cell_a.population == cell_b.population
        comparees += 1
    assert comparees == len(course_a.cells) > 0

    cid = min(course_a.cells)

    def en_famine():
        cell = Cell(
            cell_id=cid,
            area_km2=10.0,
            population=50,
            food_deficit_kg=100000.0,
            mortality_remainder=0.0,
        )
        engine._apply_mortality(cell)
        return cell

    brute = en_famine()
    with monkeypatch.context() as ctx:
        ctx.setattr(engine, "_retirer_par_les_foyers", retirer_comme_avant)
        ctx.setattr(engine, "_ajouter_par_les_foyers", ajouter_comme_avant)
        ancienne = en_famine()
    assert brute.population == ancienne.population < 50
    assert lire_habitants_par_metier(brute) == -1
    assert lire_habitants_par_metier(ancienne) == -1

    vrai_retirer = foyers.retirer

    def retirer_moins(metiers, n):
        if n > 0:
            return vrai_retirer(metiers, n - 1)
        return vrai_retirer(metiers, n)

    with monkeypatch.context() as ctx:
        ctx.setattr(foyers, "retirer", retirer_moins)
        derive = _jouer(30)
    with monkeypatch.context() as ctx:
        ctx.setattr(engine, "_retirer_par_les_foyers", retirer_comme_avant)
        ctx.setattr(engine, "_ajouter_par_les_foyers", ajouter_comme_avant)
        ancienne_30 = _jouer(30)
    assert _octets_sans_foyers(derive) != _octets_sans_foyers(ancienne_30)


def _controler_documentation(texte):
    foyers_section = texte.split("## Les foyers par métier\n", 1)[1].split("\n## ", 1)[0]
    mortalite = texte.split("### La mortalité\n", 1)[1].split("\n## ", 1)[0]
    natalite = texte.split("## La natalité\n", 1)[1].split("\n## ", 1)[0]
    migration = texte.split("## La migration de famine\n", 1)[1].split("\n## ", 1)[0]
    for attendu in ("plus forts restes", "nom de métier", "paysans",
                    "le tick ne lit les métiers que pour la récolte"):
        assert attendu in foyers_section.lower()
    for nom, section in (("mortalité", mortalite), ("natalité", natalite),
                         ("migration", migration)):
        assert "prorata" in section.lower(), nom
    assert foyers_section and mortalite and natalite and migration


def test_documentation():
    texte = (pathlib.Path(__file__).parents[1] / "MODELE.md").read_text(encoding="utf-8")
    _controler_documentation(texte)
    avant, reste = texte.split("## La natalité\n", 1)
    section, apres = reste.split("\n## ", 1)
    privee = section.replace("prorata", "écarté")
    with pytest.raises(AssertionError):
        _controler_documentation(avant + "## La natalité\n" + privee + "\n## " + apres)
    print("sections_contrôlées=4")
    assert texte


def _km2_cultives_reference(cell, carte):
    if not carte:
        return cell.area_km2
    raw = carte[cell.cell_id]
    relief = _constantes.facteurs_production_par_relief()[raw["relief"]]
    eau = _constantes.facteur_eau(raw["pluie_mm_par_an"] + raw["crue_mm_par_an"])
    agricole = 1 - _constantes.part_miniere_de(
        raw.get("gisements"), _constantes.facteurs_richesse_extraction())
    return cell.area_km2 * relief * eau * agricole


def _recolter_reference(cell, carte, moyenne):
    rendement = random.Random(0).uniform(_constantes.RNG_YIELD_LOW, _constantes.RNG_YIELD_HIGH)
    ecrire_stock_marchandise(cell, "nourriture", 0.0)
    if moyenne:
        pleine = engine._production_du_tick_kg_saison_moyenne(cell, rendement, carte)
        engine._apply_production_saison_moyenne(cell, random.Random(0), carte)
    else:
        pleine = (engine.production_du_tick_kg(cell, rendement, carte, jour=0)
                  if carte else engine.production_kg(cell, rendement))
        engine._apply_production(cell, random.Random(0), carte, jour=0)
    return pleine, lire_stock_marchandise(cell, "nourriture")


@pytest.mark.parametrize("moyenne", [False, True])
def test_recolte_bras(monkeypatch, moyenne):
    monde = World.charger(0)
    cell = max((c for c in monde.cells.values() if monde.carte[c.cell_id].get("gisements")),
               key=lambda c: _km2_cultives_reference(c, monde.carte))
    requis = _km2_cultives_reference(cell, monde.carte) * _constantes.BRAS_AUX_CHAMPS_PAR_KM2
    assert requis > 3

    def recolte(paysans, mineurs=0):
        ecrire_habitants_par_metier(cell, {m: n for m, n in
                                         (("paysans", paysans), ("mineurs", mineurs)) if n})
        return _recolter_reference(cell, monde.carte, moyenne)

    for paysans in (math.ceil(requis), math.ceil(10 * requis)):
        pleine, produite = recolte(paysans)
        assert produite == pleine > 0

    def controler_manque():
        productions = []
        for k in (1, 2):
            paysans = math.floor(requis) - k
            pleine, produite = recolte(paysans)
            assert math.isclose(produite, pleine * paysans / requis, rel_tol=1e-12)
            productions.append(produite)
        assert math.isclose(productions[0] - productions[1], pleine / requis, rel_tol=1e-12)
        assert recolte(math.floor(requis) - 2, 1)[1] < productions[0]

    def controler_mineurs():
        paysans = math.floor(requis) - 2
        assert recolte(paysans, 1)[1] == recolte(paysans)[1]
        assert recolte(paysans, math.ceil(requis))[1] == recolte(paysans)[1]

    controler_manque()
    controler_mineurs()
    with monkeypatch.context() as ctx:
        ctx.setattr(foyers, "facteur_bras", lambda *a: 1.0)
        with pytest.raises(AssertionError):
            controler_manque()
    with monkeypatch.context() as ctx:
        ctx.setattr(foyers, "facteur_bras", lambda metiers, km2: min(
            1.0, sum(metiers.values()) / (km2 * _constantes.BRAS_AUX_CHAMPS_PAR_KM2)))
        with pytest.raises(AssertionError):
            controler_mineurs()


@pytest.mark.parametrize("cartee,moyenne", [(False, False), (True, False), (True, True)])
def test_recolte_sans_metiers(monkeypatch, cartee, moyenne):
    monde = World.charger(0)
    origine = monde.cells[min(monde.cells)]
    cell = Cell(cell_id=origine.cell_id, area_km2=origine.area_km2, population=50)
    carte = monde.carte if cartee else None

    def controler_nue():
        assert lire_habitants_par_metier(cell) == -1
        pleine, produite = _recolter_reference(cell, carte, moyenne)
        assert produite == pleine > 0

    controler_nue()
    ecrire_habitants_par_metier(origine, {})
    assert origine.population == 0
    assert _recolter_reference(origine, carte, moyenne)[1] == 0.0
    ecrire_habitants_par_metier(origine, {"mineurs": 50})
    assert _recolter_reference(origine, carte, moyenne)[1] == 0.0
    assert foyers.facteur_bras({}, 0.0) == 1.0
    vrai_facteur = foyers.facteur_bras
    with monkeypatch.context() as ctx:
        ctx.setattr(foyers, "facteur_bras", lambda metiers, km2:
                    vrai_facteur({} if metiers == -1 else metiers, km2))
        with pytest.raises(AssertionError):
            controler_nue()


@pytest.mark.parametrize("numerote", [False, True])
def test_bras_suffisent_un_an(monkeypatch, numerote):
    vrai_facteur = foyers.facteur_bras
    valeurs, rapports = [], []

    def enregistrer(metiers, km2):
        facteur = vrai_facteur(metiers, km2)
        valeurs.append(facteur)
        requis = km2 * _constantes.BRAS_AUX_CHAMPS_PAR_KM2
        if metiers != -1 and requis > 0:
            rapports.append(metiers.get("paysans", 0) / requis)
        return facteur

    def jouer(n):
        valeurs.clear()
        rapports.clear()
        monde = World.charger(0)
        rng = random.Random(0)
        for i in range(n):
            tick(monde, rng, **({"numero_tick": i} if numerote else {}))
        assert len(valeurs) >= max(596, len(monde.cells)) * n
        assert len(rapports) == len(valeurs)
        return monde

    monkeypatch.setattr(foyers, "facteur_bras", enregistrer)
    jouer(365)
    assert all(v == 1.0 for v in valeurs)
    print(f"numéroté={numerote} appels={len(valeurs)} rapport_minimum={min(rapports):.6f}")
    nominal = _octets_sans_foyers(jouer(30))
    with monkeypatch.context() as ctx:
        ctx.setattr(_constantes, "BRAS_AUX_CHAMPS_PAR_KM2",
                    _constantes.BRAS_AUX_CHAMPS_PAR_KM2 * 100)
        altere = _octets_sans_foyers(jouer(30))
        assert any(v < 1.0 for v in valeurs)
        assert altere != nominal


def test_documentation_bras(monkeypatch):
    lire = pathlib.Path.read_text
    chemin = pathlib.Path(__file__).parents[1] / "MODELE.md"

    def controler():
        texte = chemin.read_text(encoding="utf-8")
        section = texte.split("## Les foyers par métier\n", 1)[1].split("\n## ", 1)[0]
        for attendu in ("BRAS_AUX_CHAMPS_PAR_KM2", "km² cultivés", "niveau 2",
                        "Le tick ne lit les métiers que pour la récolte"):
            assert attendu in section
        reste = texte.split("## Ce que le moteur ne fait pas encore\n", 1)[1].split("\n## ", 1)[0]
        assert "aucun nombre du tick ne les lit" not in " ".join(reste.split())

    for ancien, nouveau in (("BRAS_AUX_CHAMPS_PAR_KM2", "constante retirée"),
                            ("Le tick ne lit les métiers que pour la récolte",
                             "Le tick ne lit pas les métiers")):
        def texte_altere(path, *args, **kwargs):
            texte = lire(path, *args, **kwargs)
            avant, suite = texte.split("## Les foyers par métier\n", 1)
            section, apres = suite.split("\n## ", 1)
            return avant + "## Les foyers par métier\n" + section.replace(ancien, nouveau) + "\n## " + apres

        with monkeypatch.context() as ctx:
            ctx.setattr(pathlib.Path, "read_text", texte_altere)
            with pytest.raises(AssertionError):
                controler()
    controler()


def _plan_logement(surface=80):
    from sim.plan import Batiment, Parcelle, Plan
    contour = [(0, 0), (surface, 0), (surface, 1), (0, 1)]
    plan = Plan(parcelles=[Parcelle(i, contour) for i in range(5)], batiments=[
        Batiment(i, i, nature, contour, **kw) for i, nature, kw in [
            (1, "maison", {}), (0, "maison", {}),
            (2, "maison", {"en_chantier": True, "foyers": 1, "travail_requis": 1}),
            (3, "scierie", {}), (4, "four", {})]])
    plan.batiments.reverse()
    return plan


def _reference_logement(cell, plan):
    from sim.plan import aire_du_contour
    capacite = sum(max(1, int(aire_du_contour(b.emprise) // _constantes.SURFACE_M2_PAR_FOYER_LOGE))
                   for b in plan.batiments if b.nature == "maison" and not b.en_chantier)
    metiers = lire_habitants_par_metier(cell)
    if metiers == -1:
        return {"capacite": capacite, "loges": -1, "sans_logis": -1}
    n = metiers.get(_constantes.METIER_ARTISANS, 0)
    nombre = (n + _constantes.TAILLE_FOYER - 1) // _constantes.TAILLE_FOYER
    return {"capacite": capacite, "loges": min(nombre, capacite), "sans_logis": max(0, nombre - capacite)}


def _verifier_logement(cell, plan, fonction):
    avant = copy.deepcopy((cell, plan))
    resultat = fonction(cell, plan)
    assert resultat == _reference_logement(cell, plan)
    if lire_habitants_par_metier(cell) != -1:
        n = cell.habitants_par_metier.get(_constantes.METIER_ARTISANS, 0)
        assert resultat["loges"] + resultat["sans_logis"] == math.ceil(n / _constantes.TAILLE_FOYER)
    assert (cell, plan) == avant


@pytest.mark.parametrize("surface", [20, 40, 80])
def test_logement_compte(surface, monkeypatch):
    from sim import logement
    from sim.plan import Plan
    def controler():
        for n in (0, 1, 10 * _constantes.TAILLE_FOYER + 1):
            cell = Cell(0, 1, n + 30, habitants_par_metier={
                "paysans": 10, "mineurs": 10, "ouvriers": 10} | ({"artisans": n} if n else {}))
            plan = _plan_logement(surface)
            _verifier_logement(cell, plan, logement.logement_de)
            plan.batiments = [b for b in plan.batiments if b.identifiant >= 2]
            _verifier_logement(cell, plan, logement.logement_de)
        _verifier_logement(Cell(0, 1, 30), _plan_logement(surface), logement.logement_de)
        assert logement.logement_de(cell, Plan()) is None
    controler()
    lire, ranger = logement.lire_habitants_par_metier, logement.ranger_en_foyers
    for nom, faux in (
        ("ranger_en_foyers", lambda n: ranger(n - n % _constantes.TAILLE_FOYER)),
        ("lire_habitants_par_metier", lambda c: {"artisans": sum(lire(c).values())} if lire(c) != -1 else -1)):
        with monkeypatch.context() as ctx:
            ctx.setattr(logement, nom, faux)
            with pytest.raises(AssertionError):
                controler()
    vrai = logement.logement_de
    def chantier_loge(cell, plan):
        from dataclasses import replace
        plan = copy.deepcopy(plan)
        plan.batiments = [replace(b, en_chantier=False, travail_fourni=b.travail_requis) for b in plan.batiments]
        return vrai(cell, plan)
    with monkeypatch.context() as ctx:
        ctx.setattr(logement, "logement_de", chantier_loge)
        with pytest.raises(AssertionError):
            controler()


def test_logement_constantes(monkeypatch):
    from sim import logement
    cell = Cell(0, 1, 21, habitants_par_metier={"artisans": 21})
    plan = _plan_logement()
    nominal = logement.logement_de(cell, plan)
    from types import SimpleNamespace
    surface, taille = _constantes.SURFACE_M2_PAR_FOYER_LOGE, _constantes.TAILLE_FOYER
    for nom in ("SURFACE_M2_PAR_FOYER_LOGE", "TAILLE_FOYER"):
        with monkeypatch.context() as ctx:
            ctx.setattr(_constantes, nom, getattr(_constantes, nom) * 2)
            _verifier_logement(cell, plan, logement.logement_de)
            assert logement.logement_de(cell, plan) != nominal
            if nom == "SURFACE_M2_PAR_FOYER_LOGE":
                ctx.setattr(logement, "_constantes", SimpleNamespace(SURFACE_M2_PAR_FOYER_LOGE=surface, METIER_ARTISANS="artisans"))
            else:
                ctx.setattr(logement, "ranger_en_foyers", lambda n: foyers.Foyers(taille, n // taille, n % taille))
            with pytest.raises(AssertionError):
                _verifier_logement(cell, plan, logement.logement_de)


def test_logement_documentation():
    dossier = pathlib.Path(__file__).parents[1]
    texte = (dossier / "MODELE.md").read_text(encoding="utf-8")
    def controler(texte):
        section = texte.split("## Les foyers par métier\n", 1)[1].split("\n## ", 1)[0]
        assert section
        for mot in ("SURFACE_M2_PAR_FOYER_LOGE", "sans_logis", "logement", "seulement si"):
            assert mot in section
    controler(texte)
    avant, suite = texte.split("## Les foyers par métier\n", 1)
    section, apres = suite.split("\n## ", 1)
    with pytest.raises(AssertionError):
        controler(avant + "## Les foyers par métier\n" + section.replace("sans_logis", "absent") + "\n## " + apres)
    assert "La maison achevée reste sans effet" not in texte.split("## Le plan du bourg\n", 1)[1].split("\n## ", 1)[0]
    assert "sim/logement.py" in (dossier / "README.md").read_text(encoding="utf-8")
