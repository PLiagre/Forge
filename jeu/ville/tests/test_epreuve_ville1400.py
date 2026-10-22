"""Juge et lanceur de l'épreuve de la ville de 1400 (#740). Les huit rapports #739 sont relus tels quels, mutés en mémoire seulement : ce ne sont pas des mesures PC."""
import copy, hashlib, importlib.util, io, json, os, re, time, urllib.request
from pathlib import Path
import pytest
RACINE = Path(__file__).resolve().parents[3]
M739, CELLULES, SUPPR = RACINE / "docs/mesures/739-session-ville1400", (10103, 1175, 1232, 10337), object()
lu = lambda s: {c: json.loads((M739 / f"{s}-{c}.json").read_text(encoding="utf-8")) for c in CELLULES}  # noqa: E731
@pytest.fixture(scope="module")
def epreuve():
    assert (chemin := RACINE / "pc/epreuve_ville1400.py").is_file(), f"fichier introuvable : {chemin}"
    module = importlib.util.module_from_spec(spec := importlib.util.spec_from_file_location("epreuve_ville1400", chemin)); spec.loader.exec_module(module); return module
@pytest.fixture(scope="module")
def plans():
    """Deux vrais services graine 0 en pause : quatre `/plan` chacun, aides de test du service."""
    from sim.tests.test_carte_servie import _service_local
    from sim.tests.test_monde import requete_service
    def lire():
        with _service_local() as (_serveur, port): return {c: requete_service(port, f"/plan?cell={c}")[1] for c in CELLULES}
    return lire(), lire()
def juge(epreuve, plans, changer=lambda e: None):
    e = {"jouer": lu("jouer"), "relance": lu("relance"), "pj": copy.deepcopy(plans[0]), "pr": copy.deepcopy(plans[1])}; changer(e); avant = copy.deepcopy(e)
    code, lignes = epreuve.juger(e["jouer"], e["relance"], e["pj"], e["pr"]); assert e == avant, "le juge a modifié ses entrées"
    return code, lignes, [l.split(" : ")[0] for l in lignes if l.endswith("ÉCART") or " · ÉCART · " in l]
def _maj(r, lignes, posees=True):  # lignes remplacées, compteur et empreinte recalculés
    r["maisons"], r["empreinte"] = lignes, hashlib.sha256("".join(l + "\n" for l in lignes).encode("utf-8")).hexdigest(); r["posees"] = len(lignes) if posees else r["posees"]
def _ligne(l, i, f): v = l.split(" "); v[i] = f(v[i]); return " ".join(v)
def test_huit_rapports_egaux(epreuve, plans):
    code, lignes, ecarts = juge(epreuve, plans); vus = re.findall(r"^(\d+)/(\w+) : foyers attendus du plan (\d+) · posées (\d+) · refus (\d+)", "\n".join(lignes), re.M)
    assert (code, ecarts) == (0, []) and [(int(c), int(p), int(r)) for c, _s, _f, p, r in vus] == [(c, n, 0) for c, n in zip(CELLULES, (33, 66, 493, 541)) for _ in "jr"], lignes
    assert all(f"{c} jouer/relance : références" in "\n".join(lignes) for c in CELLULES)
MUTATIONS = [("retirée", lambda r: r["maisons"].pop(0), "1232/jouer couples manquants"), ("retirée et recomptée", lambda r: _maj(r, r["maisons"][1:]), "1232/jouer couples manquants"),
    ("copie ajoutée", lambda r: _maj(r, r["maisons"] + r["maisons"][:1]), "1232/jouer doublons"), ("variante fausse", lambda r: _maj(r, [_ligne(r["maisons"][0], 2, lambda v: str((int(v) + 1) % 6))] + r["maisons"][1:]), "1232/jouer variante"),
    ("hors emprise", lambda r: _maj(r, [_ligne(r["maisons"][0], 3, lambda v: f"{float(v) + 20:.2f}")] + r["maisons"][1:]), "1232/jouer hors emprise")]
@pytest.mark.parametrize("drapeau", ["", "sauter"])
@pytest.mark.parametrize("nom,muter,cause", MUTATIONS + [("relance déplacée", None, "1232 relance maisons")])
def test_maisons_en_ecart(epreuve, plans, drapeau, nom, muter, cause):
    def changer(e):
        for s in ("jouer", "relance"): [r.update(contre_epreuve=drapeau) for r in e[s].values()]
        muter(e["jouer"][1232]) if muter else _maj(e["relance"][1232], [_ligne(e["relance"][1232]["maisons"][0], 3, lambda v: f"{float(v) + .01:.2f}")] + e["relance"][1232]["maisons"][1:])
    code, lignes, ecarts = juge(epreuve, plans, changer); print(f"{nom}, drapeau {drapeau!r} : {code} {ecarts}")
    assert code == 1 and cause in ecarts and not any("drapeau" in l or "contre" in l for l in lignes if "ÉCART" in l), lignes
    assert ecarts == juge(epreuve, plans, lambda e: (changer(e), [r.update(contre_epreuve="") for s in ("jouer", "relance") for r in e[s].values()]))[2]
def _refus(e, c, quoi="hors du terrain", retirer=True, double=False):
    for s in ("jouer", "relance"):
        r = e[s][c]; rang, indice = r["maisons"][0].split(" ")[:2]; r["refus"] = [f"Maison {rang} indice {indice} : {quoi}"] * (1 + double); _maj(r, r["maisons"][1:]) if retirer else None
@pytest.mark.parametrize("nom,changer,code,cause", [
    ("foyers d'une référence", lambda e: [p[1232]["base"]["maisons"][0].update(foyers=p[1232]["base"]["maisons"][0]["foyers"] + 1) for p in (e["pj"], e["pr"])], 1, "1232/jouer foyers"),
    ("emprise d'une référence", lambda e: [m.__setitem__("emprise", [[x + 30, y] for x, y in m["emprise"]]) for p in (e["pj"], e["pr"]) for m in p[1232]["base"]["maisons"][:1]], 1, "1232/relance hors emprise"),
    ("foyers = îlots", lambda e: [e[s][10337].update(foyers=len(e["pj"][10337]["base"]["maisons"])) for s in ("jouer", "relance")], 1, "10337/jouer foyers"),
    ("refus hors Biskra", lambda e: _refus(e, 1175), 0, "refus 1 — Maison "), ("refus à Biskra", lambda e: _refus(e, 10103), 1, "10103/jouer refus à Biskra"),
    ("refus en double", lambda e: _refus(e, 1175, double=True), 1, "1175/jouer doublons"), ("refus sans raison", lambda e: _refus(e, 1175, quoi=""), 2, "refus illisible"),
    ("refus hors ensemble", lambda e: [e[s][1175].update(refus=["Maison 999 indice 0 : hors du terrain"]) for s in ("jouer", "relance")], 1, "1175/jouer couples inconnus"),
    ("refus d'une maison présente", lambda e: _refus(e, 1175, retirer=False), 1, "1175/jouer doublons")])
def test_plan_reference_et_refus(epreuve, plans, nom, changer, code, cause):
    vu, lignes, ecarts = juge(epreuve, plans, changer); print(f"{nom} : {vu} {ecarts}")
    assert vu == code and (cause in ecarts or cause in "\n".join(lignes)) and (code != 0 or not ecarts), lignes
@pytest.mark.parametrize("chemin,valeur,code,cause", [(("jouer",), {}, 2, "jouer : rapports des cellules []"), (("jouer", 1232), SUPPR, 2, "rapports des cellules"), (("relance",), None, 2, "relance : rapports"),
    (("jouer", 1175, "posees"), SUPPR, 2, "champ absent ou illisible : posees"), (("relance", 10337, "foyers"), -1, 2, "foyers non mesuré"), (("jouer", 10103, "defaut"), "service absent", 2, "défaut de session"),
    (("jouer", 1232, "absence"), "base non servie", 2, "absence déclarée"), (("pj", 1232, "base"), SUPPR, 2, "base absente"), (("pr", 1175, "base", "maisons"), [], 2, "base absente, vide"),
    (("jouer", 1232, "posees"), True, 2, "illisible : posees"), (("relance", 1175, "image_ms"), float("nan"), 2, "illisible : image_ms"), (("jouer", 1175, "maisons", 0), "pas une maison", 2, "ligne de maison illisible"),
    (("jouer", 1175, "maisons", 0), "0 0 -1 1.00 1.00 1.00 0.00", 2, "non mesurée"), (("jouer", 10337, "duree_dessin_ms"), 0, 2, "temps non mesuré"), (("relance", 10103, "images"), 0, 2, "temps non mesuré"),
    (("jouer", 1232, "empreinte"), "0" * 64, 1, "1232/jouer empreinte recalculée"), (("jouer", 1175, "cellule"), 1176, 1, "1175/jouer cellule"), (("relance", 1232, "tick"), 1, 1, "1232/relance tick"),
    (("pr", 10103, "tick"), 3, 1, "10103 relance références"), (("jouer", 10103, "session"), "relance", 1, "10103/jouer libellé de session"),
    (("jouer", 10103, "duree_dessin_ms"), 1e7, 0, "dessin 10000000.0 ms"), (("relance", 10337, "image_ms"), 5000.0, 0, "0.2 images/s sur 300 images"), (("jouer", 10103, "contre_epreuve"), "ajouter", 0, "drapeau ajouter")])
def test_absence_ou_ecart(epreuve, plans, chemin, valeur, code, cause):
    def changer(e):
        cible = e
        for cle in chemin[:-1]: cible = cible[cle]
        cible.pop(chemin[-1]) if valeur is SUPPR else cible.__setitem__(chemin[-1], valeur)
    vu, lignes, ecarts = juge(epreuve, plans, changer); assert vu == code and (cause in ecarts or cause in "\n".join(lignes)) and (code == 1 or not ecarts) and (code != 2 or len(lignes) == 1), lignes
def _harnais(monkeypatch, epreuve, tmp_path, plans, plan, options=()):
    """Processus, HTTP et Unity en mémoire : le câblage de `main`, pas une exécution PC."""
    e, sortie = {"services": [], "http": [], "unity": []}, tmp_path / "sortie"
    class Service:
        def __init__(s, cmd, **k):
            assert all(v.code is not None for v in e["services"]), "le service précédent vit encore"; e["services"].append(s); s.cmd, s.code, s.stderr = cmd, None, io.StringIO(""); s.stdout = io.StringIO("" if plan.get("muet") else "service prêt sur 127.0.0.1:8000\n")
        poll = wait = lambda s, timeout=None: s.code
        def terminate(s): s.code = 0
    def http(methode, chemin, corps=None, delai=None):
        assert e["services"][-1].code is None, "lecture après l'arrêt du service"; e["http"].append((methode, chemin, corps))
        if plan.get("http") == chemin: raise RuntimeError(f"{methode} {chemin} : panne")
        return copy.deepcopy(plans[len(e["services"]) - 1][int(chemin.rsplit("=", 1)[1])])
    def unity(cmd):
        e["unity"].append(cmd); session = "jouer" if cmd[5].endswith(".Jouer") else "relance"
        for c, r in lu(session).items():
            (plan.get("manque") == (session, c) and _maj(r, r["maisons"][1:])); plan.get("absent") != (session, c) and (f := Path(cmd[7]) / f"{session}-{c}.json").write_text(json.dumps(r), encoding="utf-8"); plan.get("vieux") == (session, c) and os.utime(f, (time.time() - 3600,) * 2)
        return plan.get("code", 0)
    sortie.mkdir(); exe = tmp_path / "Unity.exe"; exe.write_bytes(b""); (sortie / "verdict.txt").write_text("ÉGALITÉ\ncode 0\nancien\n", encoding="utf-8")
    for s in ("jouer", "relance"): [(sortie / f"{s}-{c}.json").write_text(json.dumps(r), encoding="utf-8") for c, r in lu(s).items()]
    for cible, nom, faux in ((epreuve.subprocess, "Popen", Service), (epreuve, "_http", http), (epreuve.JALON1, "_unity", unity), (epreuve.JOUER, "_repond", lambda _p: plan.get("port", False)),
                             (urllib.request, "urlopen", lambda *a, **k: pytest.fail("accès réseau réel"))): monkeypatch.setattr(cible, nom, faux)
    code = epreuve.main(["--sortie", str(sortie), "--unity", str(exe if plan.get("exe", True) else tmp_path / "absent.exe"), *options])
    assert all(s.code is not None for s in e["services"]), "un service reste ouvert"
    return code, e, (sortie / "verdict.txt").read_text(encoding="utf-8")
@pytest.mark.parametrize("options,drapeau", [((), []), (("--sauter",), ["-forgeSauter"]), (("--ajouter",), ["-forgeAjouter"])])
def test_main_deux_essais(epreuve, plans, tmp_path, monkeypatch, options, drapeau):
    assert not any(m in (RACINE / "pc/epreuve_ville1400.py").read_text(encoding="utf-8") for m in ("/tick", "/vitesse", "/intention", "POST", "-quit", "-nographics"))
    code, e, verdict = _harnais(monkeypatch, epreuve, tmp_path, plans, {}, options)
    assert code == 0 and verdict.startswith("ÉGALITÉ") and "ancien" not in verdict and f"drapeau transmis à Jouer : {(drapeau or ['aucun'])[0]}" in verdict and [s.cmd[1:] for s in e["services"]] == [["-m", "sim.service", "--seed", "0", "--jours-par-seconde", "0"]] * 2 and e["http"] == [("GET", f"/plan?cell={c}", None) for c in CELLULES] * 2, verdict
    assert [c[1:2] + c[2:10:2] for c in e["unity"]] == [["-batchmode", "-projectPath", "-executeMethod", "-forgeEpreuve", "-logFile"]] * 2 and [c[5] for c in e["unity"]] == list(epreuve.METHODES.values()) and e["unity"][0][10:] == drapeau and e["unity"][1][10:] == [] and all(Path(c[3]).is_absolute() and Path(c[7]).is_absolute() for c in e["unity"])
    with pytest.raises(SystemExit): epreuve.main(["--sortie", str(tmp_path), "--sauter", "--ajouter"])
@pytest.mark.parametrize("plan,code,cause", [({"port": True}, 2, "répond déjà"), ({"exe": False}, 2, "Unity absent"), ({"code": 3}, 2, "Unity (jouer) a rendu 3"), ({"absent": ("relance", 1175)}, 2, "rapport absent ou antérieur à cet essai : relance-1175.json"),
    ({"vieux": ("jouer", 10337)}, 2, "antérieur à cet essai : jouer-10337.json"), ({"http": "/plan?cell=1232"}, 2, "GET /plan?cell=1232 : panne"), ({"muet": True}, 2, "avant d'être prêt"), ({"manque": ("jouer", 10103)}, 1, "10103/jouer couples manquants")])
def test_main_impossible_ou_ecart(epreuve, plans, tmp_path, monkeypatch, plan, code, cause):
    vu, e, verdict = _harnais(monkeypatch, epreuve, tmp_path, plans, plan)
    assert vu == code and verdict.startswith(("", "ÉCART", "ÉPREUVE IMPOSSIBLE")[code]) and cause in verdict and "ancien" not in verdict and (code == 1 or " · égal" not in verdict), verdict
