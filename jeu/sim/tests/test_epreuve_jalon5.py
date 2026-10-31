"""Preuve réfutable : l'IA dépose les mêmes intentions que le joueur."""
import ast
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType

import pytest
from sim import ia, intentions
from sim.tests.test_intentions import _ia_monde
from sim.world import World

SOURCE = Path(ia.__file__).read_text(encoding="utf-8")
TYPES = {n: v for n, v in vars(intentions).items() if n.startswith("TYPE_")}
# Ce lecteur est contrôlé sur le vrai monde par test_depot.
LECTEURS = {"maisons_de_l_ia": "énumération des maisons sans changer le monde"}


def controler_chemin(source):
    arbre, echecs = ast.parse(source), []
    parents = {enfant: n for n in ast.walk(arbre) for enfant in ast.iter_child_nodes(n)}

    def fonction(n):
        while n in parents and not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            n = parents[n]
        return n

    def refuser(n, raison):
        echecs.append(f"{raison}, ligne {n.lineno}")

    importes, listes, choix = {}, set(), set()
    interdites = {"sim." + n for n in ("engine", "world", "plan", "chantiers")}
    classes = {n for n, v in vars(intentions).items() if isinstance(v, type) and hasattr(v, "appliquer")}
    mutations = {"append", "extend", "insert", "pop", "remove", "clear", "update", "setdefault",
                 "popitem", "sort", "reverse", "add", "discard", "appliquer"}
    appels_interdits = {"setattr", "delattr", "exec", "eval", "__setitem__"}
    for n in ast.walk(arbre):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            module = n.module if isinstance(n, ast.ImportFrom) else None
            module = "sim." + module if module and n.level and not module.startswith("sim.") else module
            for alias in n.names:
                chemin = f"{module}.{alias.name}" if module else alias.name
                if any(chemin == m or chemin.startswith(m + ".") for m in interdites):
                    refuser(n, "import interdit")
                if alias.name == "deposer_intention" or alias.name in classes - {"ChoixDepart"}:
                    refuser(n, "import interdit")
                if module == "sim.intentions" and alias.name in TYPES:
                    importes[alias.asname or alias.name] = TYPES[alias.name]
                if module == "sim.intentions" and alias.name == "ChoixDepart":
                    choix.add(alias.asname or alias.name)
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.List) and not n.value.elts:
            if isinstance(fonction(n), (ast.FunctionDef, ast.AsyncFunctionDef)):
                listes.update((fonction(n), t.id) for t in n.targets if isinstance(t, ast.Name))
    fonctions = {n.name for n in ast.walk(arbre) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    utilises = set()
    for n in ast.walk(arbre):
        if isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Delete, ast.NamedExpr)):
            cibles = n.targets if isinstance(n, (ast.Assign, ast.Delete)) else [n.target]
            for cible in cibles:
                if not (isinstance(cible, ast.Name) or isinstance(cible, ast.Tuple)
                        and all(isinstance(e, ast.Name) for e in cible.elts)):
                    refuser(n, "cible interdite")
                if any(isinstance(e, ast.Name) and e.id in importes for e in ast.walk(cible)):
                    refuser(n, "type redéfini")
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in TYPES.values():
            refuser(n, "type littéral")
        if isinstance(n, ast.Dict):
            for cle, valeur in zip(n.keys, n.values):
                if isinstance(cle, ast.Constant) and cle.value == "type":
                    if not isinstance(valeur, ast.Name) or not valeur.id.startswith("TYPE_") or valeur.id not in importes:
                        refuser(n, "type non importé")
                    else:
                        utilises.add(valeur.id)
        if isinstance(n, ast.Name) and n.id in choix and isinstance(n.ctx, ast.Load):
            parent = parents[n]
            if not (isinstance(parent, ast.Call) and isinstance(parent.func, ast.Name)
                    and parent.func.id == "isinstance" and n in parent.args[1:]):
                refuser(n, "classe hors lecture")
        if isinstance(n, ast.Call):
            nom = n.func.id if isinstance(n.func, ast.Name) else getattr(n.func, "attr", "")
            if nom in appels_interdits:
                refuser(n, "appel interdit")
            if isinstance(n.func, ast.Attribute) and nom in mutations:
                cible = n.func.value
                if not (isinstance(cible, ast.Name) and (cible.id == "releve"
                        or (fonction(n), cible.id) in listes)):
                    refuser(n, "mutation interdite")
            if any(isinstance(a, ast.Name) and a.id == "monde" for a in [*n.args, *[k.value for k in n.keywords]]):
                if not isinstance(n.func, ast.Name) or nom not in {"recevoir_intention", *fonctions, *LECTEURS}:
                    refuser(n, "appel monde interdit")
    return echecs if utilises else [*echecs, "aucun type utilisé"]


def controler_depot(avant, apres, releve):
    echecs = [] if releve else ["relevé vide"]
    if avant.to_dict() != apres.to_dict():
        echecs.append("monde modifié")
    if ({k: v for k, v in avant.__dict__.items() if k != "intentions_en_attente"}
            != {k: v for k, v in apres.__dict__.items() if k != "intentions_en_attente"}):
        echecs.append("état hors dépôt modifié")
    attendues = list(avant.intentions_en_attente)
    for entree in releve:
        attendues.append(intentions.recevoir_intention(deepcopy(avant), entree["intention"]))
    if apres.intentions_en_attente != attendues:
        echecs.append("attente différente du relevé")
    return echecs


def controler_rejeu(releve, monde_ia, monde_rejoue, monde_sans):
    echecs = [] if releve else ["relevé vide"]
    if any(e["intention"].get("type") not in TYPES.values() for e in releve):
        echecs.append("type inconnu")
    if monde_ia != monde_rejoue:
        echecs.append("rejeu différent")
    if monde_ia == monde_sans:
        echecs.append("témoin identique")
    documents = [json.loads(m) for m in (monde_ia, monde_rejoue, monde_sans)]
    if any(not d.get("cells") or not d.get("plans") for d in documents):
        echecs.append("cellules ou plans vides")
    differences = {champ: sorted(k for k in documents[0][champ].keys() | documents[2][champ].keys()
                                if documents[0][champ].get(k) != documents[2][champ].get(k))
                   for champ in ("cells", "plans")}
    print(f"gestes={releve}; différences avec le témoin={differences}")
    return echecs


def test_types():
    attendus = set(intentions.CHAMPS_OBLIGATOIRES) | {intentions.TYPE_CHOISIR_DEPART}
    assert TYPES and set(TYPES.values()) == attendus
    with pytest.raises(AssertionError):
        assert set([*TYPES.values(), "ecrire_cellule"]) == attendus
    for type_intention in [*TYPES.values(), "ecrire_cellule"]:
        monde = World.charger(0)
        with pytest.raises(intentions.IntentionRefusee) as refus:
            intentions.recevoir_intention(monde, {"type": type_intention})
        assert ("type d'intention inconnu" in str(refus.value)) == (type_intention not in attendus)
        assert not monde.intentions_en_attente


@pytest.mark.parametrize("ajout,nom", [
    ("monde.plans[maison.cell_id] = plan", "cible"),
    ("bourg.population = 0", "cible"),
    ("bourg.population += 1", "cible"),
    ("bourg.population: int = 0", "cible"),
    ("del monde.plans[maison.cell_id]", "cible"),
    ("cellule.lieux.append(bourg)", "mutation"),
    ("setattr(bourg, 'duree_faim_ticks', 0)", "appel interdit"),
    ("delattr(bourg, 'population')", "appel interdit"),
    ("exec('pass')", "appel interdit"),
    ("eval('0')", "appel interdit"),
    ("cellule.__setitem__('population', 0)", "appel interdit"),
    ("from sim.intentions import TraceRoute\nTraceRoute(0, (), 4).appliquer(monde)", "import"),
    ("from sim.engine import tick", "import"),
    ("from sim import world", "import"),
    ("from sim.intentions import deposer_intention", "import"),
    ("inconnu(monde)", "appel monde"),
    ("geste = {'type': 'tracer_route'}", "type littéral"),
    ("TYPE_ECRIRE = 'ecrire_cellule'\ngeste = {'type': TYPE_ECRIRE}", "type non importé"),
    ("TYPE_TRACER_ROUTE = 'ecrire_cellule'", "type redéfini"),
    ("def autre():\n    propositions.append(0)", "mutation"),
])
def test_chemin_contre_epreuves(ajout, nom):
    echecs = controler_chemin(SOURCE + "\n" + ajout + "\n")
    assert any(nom in e and "ligne " in e for e in echecs), echecs


def test_chemin():
    assert controler_chemin(SOURCE) == []
    assert controler_chemin("pass") == ["aucun type utilisé"]


def test_depot(monkeypatch):
    _, monde, _ = _ia_monde()
    avant = deepcopy(monde)
    ia.maisons_de_l_ia(monde)
    assert monde.__dict__ == avant.__dict__, "lecteur impur"
    releve = []
    ia.jouer_ia(monde, releve)
    assert controler_depot(avant, monde, releve) == []
    assert "relevé vide" in controler_depot(avant, avant, [])
    sonde, monde = [], deepcopy(avant)
    monkeypatch.setattr(ia, "recevoir_intention", lambda m, i: sonde.append((m, deepcopy(i))))
    releve = []
    ia.jouer_ia(monde, releve)
    assert releve and monde.__dict__ == avant.__dict__, "écriture hors dépôt"
    assert all(m is monde for m, _ in sonde)
    assert [i for _, i in sonde] == [e["intention"] for e in releve]


@pytest.mark.parametrize("ecriture", [
    "monde.plans.pop(proposition['intention']['cell'])",
    "monde.cells[proposition['intention']['cell']].lieux[0].population = 0",
])
def test_depot_contre_epreuves(ecriture):
    source = SOURCE.replace("        recevoir_intention(monde, proposition['intention'])",
                            "        recevoir_intention(monde, proposition['intention'])\n        " + ecriture)
    assert source != SOURCE and controler_chemin(source), "écriture statique ignorée"
    module = ModuleType("ia_corrompue")
    exec(compile(source, "ia_corrompue", "exec"), module.__dict__)
    _, monde, _ = _ia_monde()
    avant, releve = deepcopy(monde), []
    module.jouer_ia(monde, releve)
    assert "monde modifié" in controler_depot(avant, monde, releve)


@pytest.fixture(scope="module")
def courses(tmp_path_factory):
    dossier = tmp_path_factory.mktemp("jalon5")

    def courir(nom, gestes=None, avec_ia=False):
        sortie = dossier / (nom + ".json")
        commande = [sys.executable, "-m", "sim", "--ticks", "30", "--seed", "0",
                    "--json", "--monde-json", str(sortie)]
        if avec_ia:
            commande.append("--ia")
        if gestes is not None:
            fichier = dossier / (nom + "-gestes.json")
            fichier.write_text(json.dumps(gestes), encoding="utf-8")
            commande += ["--gestes", str(fichier)]
        resultat = subprocess.run(commande, cwd=Path(__file__).parents[2], capture_output=True,
                                  text=True, timeout=120)
        assert resultat.returncode == 0, resultat.stderr
        return json.loads(resultat.stdout), sortie.read_bytes()

    resume, monde_ia = courir("ia", avec_ia=True)
    releve = [{"tick": e["tick"], "intention": e["intention"]} for e in resume["ia"]["releve"]]
    assert releve, "relevé CLI vide"
    monde_rejoue = courir("rejoue", releve)[1]
    monde_sans = courir("sans")[1]
    altere = deepcopy(releve)
    altere[0]["intention"]["points"][0][0] += 1
    return releve, monde_ia, monde_rejoue, monde_sans, courir("altere", altere)[1]


def test_rejeu(courses):
    releve, monde_ia, monde_rejoue, monde_sans, altere = courses
    assert "relevé vide" in controler_rejeu([], monde_ia, monde_rejoue, monde_sans)
    assert "rejeu différent" in controler_rejeu(releve, monde_ia, altere, monde_sans)
    assert "témoin identique" in controler_rejeu(releve, monde_ia, monde_rejoue, monde_rejoue)
    inconnu = deepcopy(releve)
    inconnu[0]["intention"]["type"] = "ecrire_cellule"
    assert "type inconnu" in controler_rejeu(inconnu, monde_ia, monde_rejoue, monde_sans)
    assert controler_rejeu(releve, monde_ia, monde_rejoue, monde_sans) == []
