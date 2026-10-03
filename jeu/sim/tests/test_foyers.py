"""Preuves et contre-épreuves des foyers par métier, niveau 2."""

import copy
import hashlib
import json
import pathlib
import random

import pytest

import sim.constants as _constantes
from sim import foyers, service
from sim.aggregation import bourg_depuis_monde
from sim.engine import tick
from sim.model import Cell, cellule_vers_dict, lire_habitants_par_metier
from sim.world import World


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
                    "le tick ne lit pas les métiers"):
        assert attendu.lower() in section.lower()
    assert "sim/foyers.py" in (dossier / "README.md").read_text(encoding="utf-8")
    print(f"contre_épreuves_structurelles={len(contre_epreuves)} sections_contrôlées=1")
    assert len(contre_epreuves) > 0 and section
