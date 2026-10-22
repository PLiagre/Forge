"""Juge et lanceur de l'épreuve de la transition (#733). Rapports #732 relus ou copiés en mémoire : ce ne sont pas des mesures PC."""
import copy, importlib.util, io, json, os, time, urllib.error, urllib.request
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[3]
M732, RELEVES = RACINE / "docs/mesures/732-session-transition", ("carte_avant", "ville_apres", "ville_avant", "carte_apres")
REGLAGES = json.loads((RACINE / "3d/unity/Assets/ForgeLocal3D/Pont/Resources/ReglagesDesVues.json").read_text(encoding="utf-8"))
DEPARTS = json.loads((RACINE / "3d/unity/Assets/ForgeLocal3D/Pont/Tests/departs-graine0-tick3.json").read_text(encoding="utf-8"))
SIEGE = next(f["cell_id"] for f in DEPARTS["departs"] if f["nom"] == "Émirat du Zab")
VILLE, SUPPR = ["ville_apres vitesse", "ville_avant vitesse", "carte_apres vitesse"], object()
lu = lambda nom: json.loads((M732 / f"rapport-{nom}.json").read_text(encoding="utf-8"))  # noqa: E731
exemple = lambda: lu("marche") | {"carte_avant": {"tick": 35, "jours_par_seconde": 1, "scene": "Forge_Carte"}}  # noqa: E731  # construit, seule la vitesse initiale change
@pytest.fixture(scope="module")
def epreuve():
    assert (chemin := RACINE / "pc/epreuve_transition.py").is_file(), f"fichier introuvable : {chemin}"
    module = importlib.util.module_from_spec(spec := importlib.util.spec_from_file_location("epreuve_transition", chemin)); spec.loader.exec_module(module); return module
def ecarts(epreuve, r, reglages=REGLAGES, siege=SIEGE):
    avant = copy.deepcopy((r, reglages)); code, lignes = epreuve.juger(r, reglages, siege)
    assert (r, reglages) == avant and len(lignes) == 12 and all(l.endswith((" · égal", " · ÉCART")) for l in lignes), lignes
    return code, [l.split(" : ", 1)[0] for l in lignes if l.endswith("ÉCART")]
def test_marche_pause_et_exemple(epreuve):
    assert exemple()["carte_avant"] == lu("marche")["carte_avant"] | {"jours_par_seconde": 1} and ecarts(epreuve, exemple()) == (0, [])
    assert exemple()["ville_apres"]["tick"] == exemple()["ville_avant"]["tick"] and ecarts(epreuve, lu("marche")) == (1, ["carte_avant vitesse"])
    assert ecarts(epreuve, lu("pause")) == (1, ["carte_avant vitesse", *VILLE, "descente", "retour"])
def _ticks(*t): return lambda r: [r[n].update(tick=v) for n, v in zip(RELEVES, t)]
@pytest.mark.parametrize("nom,changer,attendu", [("vitesses à 1", lambda r: [r[n].update(jours_par_seconde=1) for n in RELEVES], VILLE),
    ("retour à VITESSE_VILLE", lambda r: r["carte_apres"].update(jours_par_seconde=REGLAGES["VITESSE_VILLE"]), ["carte_apres vitesse"]),
    ("arrivée en ville figée", _ticks(35, 35, 37, 39), ["descente"]), ("retour figé", _ticks(35, 37, 37, 37), ["retour"]),
    ("quatre ticks figés", _ticks(37, 37, 37, 37), ["descente", "retour"]), ("chronologie inversée", _ticks(39, 37, 37, 35), ["descente", "retour"])])
def test_contre_epreuve(epreuve, nom, changer, attendu):
    changer(r := exemple()); code, vus = ecarts(epreuve, r)
    print(f"{nom} : ticks {[r[n]['tick'] for n in RELEVES]} -> juge {code}, écarts {vus}"); assert (code, vus) == (1, attendu)
def test_references_donnees(epreuve):
    autres, r = {"VITESSE_VILLE": 0.25, "VITESSE_CARTE": 4}, exemple()
    assert ecarts(epreuve, r, autres) == (1, VILLE)
    for n, cle in zip(RELEVES[1:], ("VITESSE_VILLE", "VITESSE_VILLE", "VITESSE_CARTE")): r[n]["jours_par_seconde"] = autres[cle]
    assert ecarts(epreuve, r, autres) == (0, []) and ecarts(epreuve, r, autres, SIEGE + 1) == (1, ["cellule"])
    r["cellule"] = SIEGE + 1; assert ecarts(epreuve, r, autres, SIEGE + 1) == (0, [])
@pytest.mark.parametrize("chemin,valeur,code,cause", [(("ville_avant", "scene"), "Forge_Carte", 1, "ville_avant scène"),
    (("carte_apres", "jours_par_seconde"), 0, 1, "carte_apres vitesse"), (("ville_avant", "tick"), SUPPR, 2, "ville_avant.tick"), (("carte_apres",), {}, 2, "carte_apres.tick"),
    ((), {}, 2, "rapport absent ou vide"), (("ville_apres", "tick"), -1, 2, "ville_apres.tick non mesuré"), (("defaut",), "4. ville : transition arrêtée", 2, "défaut de session"),
    (("cellule",), True, 2, "cellule"), (("carte_avant", "jours_par_seconde"), float("nan"), 2, "carte_avant.jours_par_seconde"), (("réglages", "VITESSE_CARTE"), SUPPR, 2, "réglage VITESSE_CARTE"),
    (("réglages", "VITESSE_VILLE"), False, 2, "réglage VITESSE_VILLE"), (("siège",), None, 2, "siège de référence")])
def test_ecart_ou_impossible(epreuve, chemin, valeur, code, cause):
    e = {"rapport": exemple(), "réglages": dict(REGLAGES), "siège": SIEGE}
    *tete, fin = chemin if chemin[:1] in (("réglages",), ("siège",)) else ("rapport", *chemin); cible = e
    for cle in tete: cible = cible[cle]
    cible.pop(fin) if valeur is SUPPR else cible.__setitem__(fin, valeur)
    vu, lignes = epreuve.juger(e["rapport"], e["réglages"], e["siège"])
    assert vu == code and cause in " ".join(lignes) and (code == 1 or len(lignes) == 1), lignes
def _harnais(monkeypatch, epreuve, tmp_path, plan):
    """Processus, HTTP et Unity en mémoire : le câblage de `main`, pas une exécution PC. Le Zab y prend l'id 913."""
    e, sortie = {"services": [], "http": [], "unity": [], "horloge": 0}, tmp_path / "sortie"
    class Service:
        def __init__(s, cmd, **k):
            e["services"].append(s); s.cmd, s.code, s.stderr = cmd, None, io.StringIO("")
            s.stdout = io.StringIO("" if plan.get("muet") else "service prêt sur 127.0.0.1:8000\n")
        poll = wait = lambda s, timeout=None: s.code
        def terminate(s): s.code = 0
    def http(methode, chemin, corps=None, delai=None):  # « lent » : chaque /monde avance l'horloge ; « sourd » : la réponse ignore la borne
        e["http"].append((methode, chemin, corps)); e["horloge"] += (lent := plan.get("lent", 0) * (chemin == "/monde"))
        if lent > (delai if delai and not plan.get("sourd") else lent): raise TimeoutError("timed out")
        if plan.get("http") == chemin: raise urllib.error.URLError("lecture impossible")
        d = copy.deepcopy(DEPARTS); d["departs"].reverse(); z = next(f for f in d["departs"] if f["nom"] == epreuve.CAPITALE.ZAB); z["id"] = 913
        if chemin == "/departs": return d | {"departs": d["departs"] + [z] * (plan.get("zab") == "double")}
        if chemin == "/intention": return {"acceptee": plan.get("accepte", True), "appliquee_au_tick": 3}
        if chemin == "/monde": return {"tick": 4} | ({} if plan.get("jamais") or len(e["http"]) < 4 else {"maison_du_joueur": "seigneurie-913"})
        return {"id": "seigneurie-913", "nom": z["maison"], "tick": 4, "siege": plan.get("siege", {"cell_id": SIEGE, "nom": "Biskra"})}
    def unity(cmd):
        e["unity"].append(cmd); rapport = Path(cmd[7])
        if plan.get("rapport", True): rapport.write_text(plan.get("texte") or json.dumps(plan.get("lu") or exemple()), encoding="utf-8")
        if plan.get("vieux"): os.utime(rapport, (time.time() - 3600,) * 2)
        return plan.get("code", 0)
    sortie.mkdir(); exe = tmp_path / "Unity.exe"; exe.write_bytes(b""); (sortie / "verdict.txt").write_text("ÉGALITÉ\ncode 0\nancien\n", encoding="utf-8")
    for cible, nom, faux in ((epreuve.subprocess, "Popen", Service), (epreuve, "_http", http), (epreuve.JALON1, "_unity", unity), (epreuve, "PAS_S", 0), (epreuve, "ATTENTE_CHOIX_S", .2), (time, "monotonic", lambda m=time.monotonic: m() + e["horloge"]),
                             (epreuve.JOUER, "_repond", lambda _p: plan.get("port", False)), (urllib.request, "urlopen", lambda *a, **k: pytest.fail("accès réseau réel"))): monkeypatch.setattr(cible, nom, faux)
    code = epreuve.main(["--sortie", str(sortie), "--unity", str(exe if plan.get("exe", True) else tmp_path / "absent.exe")])
    assert all(s.code is not None for s in e["services"]), "un service reste ouvert"
    return code, e, (sortie / "verdict.txt").read_text(encoding="utf-8")
@pytest.mark.parametrize("plan,attendu", [({}, 0), ({"lu": lu("marche")}, 1)])
def test_main_juge_une_session(epreuve, tmp_path, monkeypatch, plan, attendu):
    assert epreuve.ATTENTE_CHOIX_S == 30 and not any(m in (RACINE / "pc/epreuve_transition.py").read_text(encoding="utf-8") for m in ("/tick", "/vitesse", "-quit", "-nographics"))
    code, e, verdict = _harnais(monkeypatch, epreuve, tmp_path, plan)
    assert code == attendu and verdict.startswith(("ÉGALITÉ", "ÉCART")[attendu]) and f"siège de référence {SIEGE}" in verdict and "ancien" not in verdict, verdict
    assert [s.cmd[1:] for s in e["services"]] == [["-m", "sim.service", "--seed", "0", "--port", "8000", "--jours-par-seconde", "1"]]
    assert [h for h in e["http"] if h[0] != "GET"] == [("POST", "/intention", {"type": "choisir_depart", "seigneurie": 913})]
    assert [h[1] for h in e["http"]] == ["/departs", "/intention", "/monde", "/monde", "/maison?id=seigneurie-913"]
    assert [c[1:2] + c[2::2] for c in e["unity"]] == [["-batchmode", "-projectPath", "-executeMethod", "-forgeEpreuve", "-logFile"]] and e["unity"][0][5] == epreuve.METHODE
@pytest.mark.parametrize("plan,cause", [({"port": True}, "répond déjà"), ({"exe": False}, "Unity absent"), ({"code": 3}, "Unity a rendu 3"),
    ({"rapport": False}, "rapport absent"), ({"vieux": True}, "antérieur"), ({"texte": "pas du json"}, "rapport invalide"), ({"texte": "{}"}, "rapport absent ou vide"), ({"zab": "double"}, "2 trouvée(s)"),
    ({"accepte": False}, "choix refusé"), ({"jamais": True}, "choix jamais appliqué"), ({"lent": .15}, "timed out"), ({"lent": .15, "sourd": True}, "dernière lecture maison_du_joueur 'seigneurie-913'"), ({"siege": None}, "siège nul"), ({"muet": True}, "avant d'être prêt"), ({"http": "/maison?id=seigneurie-913"}, "lecture impossible")])
def test_main_impossible(epreuve, tmp_path, monkeypatch, plan, cause):
    code, e, verdict = _harnais(monkeypatch, epreuve, tmp_path, plan)
    assert code == 2 and verdict.startswith("ÉPREUVE IMPOSSIBLE") and cause in verdict and "ancien" not in verdict and " · égal" not in verdict, verdict
    assert len(e["services"]) == (0 if "port" in plan or "exe" in plan else 1)
