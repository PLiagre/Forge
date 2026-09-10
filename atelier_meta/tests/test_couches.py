"""Un module, une couche. Les sept couches sont occupées."""

from pathlib import Path

from atelier.couches import Couche, MODULES, couches_occupees
from atelier.skills_index import SKILLS, chemins


def test_chaque_module_a_une_couche():
    assert MODULES, "échantillon vide"
    for nom, couche in MODULES.items():
        assert isinstance(couche, Couche), nom


def test_les_sept_couches_sont_occupees():
    occupees = couches_occupees()
    vides = [c.value for c, mods in occupees.items() if not mods]
    assert not vides, f"couches sans module : {vides}"


def test_aucun_module_en_double():
    vus: dict[str, Couche] = {}
    for nom, couche in MODULES.items():
        assert nom not in vus, f"{nom} déclaré deux fois"
        vus[nom] = couche


def test_chaque_skill_existe():
    index = chemins()
    assert set(index) == set(SKILLS)
    manquants = [nom for nom, chemin in index.items() if not chemin.is_file()]
    assert not manquants, f"skills sans SKILL.md : {manquants}"


def test_skills_vivent_dans_ce_depot():
    racine = Path(__file__).resolve().parent.parent
    for chemin in chemins().values():
        assert racine in chemin.parents
