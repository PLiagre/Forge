"""Rapports bâtis en mémoire au format #659 ; ce ne sont pas des mesures PC."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[3]
MESURES = RACINE / "docs/mesures/763-juge-part"


def _rapport(p, corps):
    m = json.loads(corps)
    panier = " · ".join(f"{k} : {v:.2f}".rstrip("0").rstrip(".").replace(".", ",") + " kg" for k, v in sorted(m["grenier"].items()))
    return dict(terre=3, part_demandee_pct=p, curseur_pct=p, maison=m["id"], tick_avant=0, tick_apres_choix=1, tick_apres=31, ticks_part=30,
                choix=dict(statut=200, tick=0, raison=""), ordre=dict(statut=200, tick=1, raison=""),
                intention_json=json.dumps(dict(type="fixer_part", maison=m["id"], part=p / 100)), message_ordre="", defaut="",
                panneau=f"Prélèvement : {100 * m['part']:g} % · tick {m['tick']}\nGrenier : {panier or 'vide'}".replace(".", ","),
                maison_statut=200, maison_json=corps)


@pytest.fixture
def base():
    d = json.loads((RACINE / "3d/unity/Assets/ForgeLocal3D/Pont/Tests/departs-graine0-tick3.json").read_text())
    d["tick"] = 0
    a, b = [(MESURES / f"maison-moree-{p}.json").read_text() for p in (50, 10)]
    return [_rapport(50, a), _rapport(10, b), d, a, b, 50, 10]


@pytest.fixture(scope="module")
def epreuve():
    chemin = RACINE / "pc/epreuve_part.py"
    assert chemin.is_file(), f"fichier introuvable : {chemin}"
    spec = importlib.util.spec_from_file_location("epreuve_part", chemin)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _verifier(epreuve, base, noms=()):
    code, lignes = epreuve.juger(*base)
    assert code == bool(noms) and len(lignes) == 23, lignes
    assert [l.split(" : ", 1)[0] for l in lignes if l.endswith(" · ÉCART")] == list(noms), lignes
    assert all(l.endswith((" · égal", " · ÉCART")) for l in lignes)
    return lignes

def test_corps_mesures(base):
    for corps, part, kg in zip(base[3:5], (.5, .1), (570982.179398794, 115486.43624743563)):
        m = json.loads(corps)
        assert corps and not corps.endswith("\n") and (m["id"], m["tick"], m["part"], m["grenier"]["nourriture"]) == ("seigneurie-3", 31, part, kg)


def test_rapports_et_contre_epreuve(epreuve, base):
    assert base[0]["panneau"] == "Prélèvement : 50 % · tick 31\nGrenier : nourriture : 570982,18 kg"
    assert base[1]["panneau"] == "Prélèvement : 10 % · tick 31\nGrenier : nourriture : 115486,44 kg"
    lignes = _verifier(epreuve, base)
    assert "570982.18" in lignes[-1] and "115486.44" in lignes[-1]
    base[0], base[3], base[5] = copy.deepcopy(base[1]), base[4], 10
    print("\n".join(_verifier(epreuve, base, ("grenier",))))


@pytest.mark.parametrize("champ,valeur,nom", [
    ("panneau", "51 %", "panneau part"), ("panneau", "570982,20", "panneau grenier"),
    ("panneau", "570982,19", "panneau grenier"), ("panneau", "tick 32", "panneau part"),
    ("corps", " ", "corps"), ("ordre", 2, "ordre"), ("ticks_part", 29, "ticks"), ("intention_json", "{}", "intention"),
    ("intention_json", '{"type":"fixer_part","maison":"seigneurie-3","part":0.4}', "intention"),
    ("intention_json", "illisible", "intention"), ("curseur_pct", 40, "demande"), ("choix", 409, "choix"),
    ("tick_apres", 32, "ticks"), ("maison", "autre", "maison"), ("terre", 99, "terre"),
    ("part", .49, "part relue"), ("panneau", "illisible", "panneau part|panneau grenier")])
def test_ecart(epreuve, base, champ, valeur, nom):
    r = base[0]
    if champ == "panneau":
        r[champ] = r[champ].replace("50 %", valeur) if "%" in valeur else r[champ].replace("570982,18", valeur) if valeur[0].isdigit() else r[champ].replace("tick 31", valeur) if valeur.startswith("tick") else valeur
    elif champ == "part":
        base[3] = json.dumps(json.loads(base[3]) | {"part": valeur}); r["maison_json"] = base[3]; r["panneau"] = r["panneau"].replace("50 %", "49 %")
    elif champ == "corps": r["maison_json"] += valeur
    elif champ in ("ordre", "choix"): r[champ]["tick" if champ == "ordre" else "statut"] = valeur
    else: r[champ] = valeur
    _verifier(epreuve, base, tuple("forte · " + n for n in nom.split("|")))


@pytest.mark.parametrize("cas,cause", [("vide", "rapport"), ("absent", "panneau"), ("defaut", "session interrompue"), ("bool", "ticks_part"), ("fiche", "Morée"), ("double", "Morée"), ("tick", "tick"), ("json", "relu"), ("grenier", "grenier"), ("nul", "grenier"), ("inf", "grenier"), ("part", "pourcentage")])
@pytest.mark.parametrize("cote", [0, 1])
def test_impossible(epreuve, base, cas, cause, cote):
    r, d, i = base[cote], base[2], cote + 3
    if cas == "vide": base[cote] = {}
    elif cas == "absent": del r["panneau"]
    elif cas == "defaut": r["defaut"] = "session interrompue"
    elif cas == "bool": r["ticks_part"] = True
    elif cas in ("fiche", "double"):
        f = next(f for f in d["departs"] if f["nom"] == "Despotat de Morée")
        d["departs"].remove(f) if cas == "fiche" else d["departs"].append(copy.deepcopy(f))
    elif cas == "tick": d["tick"] = 3
    elif cas == "part": base[cote + 5] = 61
    else:
        m = json.loads(base[i])
        if cas == "grenier": del m["grenier"]
        else: m["grenier"] = None if cas == "nul" else {"nourriture": float("inf")}
        base[i] = "pas du json" if cas == "json" else json.dumps(m)
    base[1 - cote]["curseur_pct"] = 42
    code, lignes = epreuve.juger(*base)
    assert code == 2 and lignes and cause in " ".join(lignes) and not any(l.endswith(" · égal") for l in lignes)


@pytest.mark.parametrize("paniers", [({"bois": 1, "grain": 20}, {"bois": 2, "grain": 3}), ({"bois": 1}, {})])
def test_references(epreuve, base, paniers):
    base[2]["departs"].reverse()
    _verifier(epreuve, base)
    next(f for f in base[2]["departs"] if f["nom"] == "Despotat de Morée")["id"] = 913
    for i, panier in enumerate(paniers):
        m = json.loads(base[i + 3]) | {"id": "seigneurie-913", "grenier": panier}
        base[i + 3] = json.dumps(m); base[i] = _rapport(base[i + 5], base[i + 3]); base[i]["terre"] = 913
    avant = copy.deepcopy(base)
    assert _verifier(epreuve, base) == _verifier(epreuve, base) and base == avant
    for i in (0, 1):
        m = json.loads(base[i + 3]) | {"grenier": paniers[1 - i]}
        base[i + 3] = json.dumps(m); base[i] = _rapport(base[i + 5], base[i + 3]); base[i]["terre"] = 913
    _verifier(epreuve, base, ("grenier",))
    for texte in ("Grenier : bois : 2 kg", "Grenier : bois : 2 kg · bois : 2 kg"):
        base[0]["panneau"] = "Prélèvement : 50 % · tick 31\n" + texte
        _verifier(epreuve, base, ("forte · panneau grenier", "grenier"))

@pytest.mark.parametrize("cle", "terre part_demandee_pct curseur_pct maison tick_avant tick_apres_choix tick_apres ticks_part choix ordre intention_json message_ordre panneau maison_statut maison_json defaut".split())
@pytest.mark.parametrize("valeur", [None, True, []])
def test_impossible_champs(epreuve, base, cle, valeur):
    if valeur is None: del base[0][cle]
    else: base[0][cle] = valeur
    code, lignes = epreuve.juger(*base)
    assert code == 2 and cle in " ".join(lignes) and not any(l.endswith(" · égal") for l in lignes)
