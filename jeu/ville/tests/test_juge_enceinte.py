"""Juge et lanceur de l'épreuve de l'enceinte (#938). Les deux rapports versés sont relus tels quels, mutés en mémoire seulement ; les références viennent de vrais services d'épreuve, graine 0, J = 0,01, l'un ignorant tracer_enceinte."""
import copy, importlib.util, json, pytest; from pathlib import Path
M938, LANCEUR = (RACINE := Path(__file__).resolve().parents[3]) / "docs/mesures/938-epreuve-enceinte", RACINE / "pc/epreuve_enceinte.py"
lu = lambda nom: json.loads((M938 / f"rapport-{nom}.json").read_text(encoding="utf-8-sig"))  # noqa: E731
@pytest.fixture(scope="module")
def epreuve():
    assert LANCEUR.is_file(), f"fichier introuvable : {LANCEUR}"; module = importlib.util.module_from_spec(spec := importlib.util.spec_from_file_location("epreuve_enceinte", LANCEUR)); spec.loader.exec_module(module); return module
@pytest.fixture(scope="module")
def refs(epreuve):
    from sim import constants, service; from sim.tests.test_monde import _service_epreuve
    vus, coins = {}, lu("normal")["coins"]
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(constants, "TRAVAIL_ENCEINTE_JOURNEES_PAR_M", 0.01)
        with _service_epreuve(epreuve=True) as (_serveur, port): vus["normal"] = epreuve.references(port, coins, "0.01")
        mp.setattr(service, "recevoir_intention", epreuve.ignorante(service.recevoir_intention))
        with _service_epreuve(epreuve=True) as (_serveur, port): vus["ignore"] = epreuve.references(port, coins, "0.01")
    assert constants.TRAVAIL_ENCEINTE_JOURNEES_PAR_M == 30; return vus
def juge(epreuve, refs, nom="normal", changer=lambda r, f: None, ref="normal"):
    r, f = lu(nom), copy.deepcopy(refs[ref]); changer(r, f); avant = copy.deepcopy((r, f)); code, lignes = epreuve.juger(r, f); assert (r, f) == avant, "le juge a modifié ses entrées"; return code, lignes, [l.split(" : ")[0] for l in lignes if l.endswith(" · ÉCART")]
CARRE = [[-80, -80], [80, -80], [80, 80], [-80, 80]]
@pytest.mark.parametrize("coins,travail,attendu", [(CARRE, "0.01", 7), (CARRE, "30", 19200), ([[0, 0], [0.1, 0], [0, 0.1]], "0.01", 1)])
def test_travail_attendu(epreuve, coins, travail, attendu): assert epreuve.travail_attendu(coins, travail) == attendu
def test_references_mesurees(refs):
    plans, ignores = refs["normal"]["plans"], refs["ignore"]["plans"]
    assert [p["tick"] for p in plans] == [p["tick"] for p in ignores] == list(range(3, 15)) and refs["normal"]["cellule"] == 10103
    assert [p["enceinte"]["travail_fourni"] for p in plans] == [1, 3] + [7] * 10 and [p["enceinte"]["en_chantier"] for p in plans] == [True, True] + [False] * 10
    assert all(p["portes"] == [{"identifiant": 0, "largeur_m": 4, "point": [-80.0, 2.2], "rue": "plan"}] for p in plans) and not any("enceinte" in p and p["enceinte"] or p.get("portes") for p in ignores)
def test_normal_egal(epreuve, refs):
    code, lignes, ecarts = juge(epreuve, refs); assert (code, ecarts) == (0, []) and "7 journées requises" in lignes[0] and lignes[-1].startswith("achevée au tick 5 · servi : 5"), lignes
    assert [l for l in lignes if l.startswith("tick ")] == [f"tick {t} · fourni/requis vu {f}/7, servi {f}/7 · étape {e} · portes dessinées/servies 1/1" for t, f, e in ((3, 1, "piquets"), (4, 3, "piquets"), (5, 7, "fini"))]
def test_reference_ignorante(epreuve, refs):
    code, lignes, ecarts = juge(epreuve, refs, ref="ignore"); assert code == 1 and {"3 contour", "3 travail requis (servi)", "3 portes servies", "achevée"} <= set(ecarts), lignes
@pytest.mark.parametrize("contre", ["forge937SansPorte", ""])
def test_sans_porte(epreuve, refs, contre):
    code, lignes, ecarts = juge(epreuve, refs, "sans-porte", lambda r, f: r.update(contre_epreuve=contre)); assert (code, ecarts) == (1, ["3 portes dessinées", "4 portes dessinées", "5 portes dessinées"]) and lu("sans-porte")["contre_epreuve"], lignes
def _porte(r, i=0): return r["releves"][i]["portes_dessinees"]
@pytest.mark.parametrize("changer,cause", [
    (lambda r, f: _porte(r)[0].update(x=_porte(r)[0]["x"] + 0.1), "3 portes dessinées"), (lambda r, f: _porte(r, 1).append(dict(_porte(r, 1)[0])), "4 portes dessinées"),
    (lambda r, f: r["releves"][1].update(travail_requis=8), "4 travail requis (session)"), (lambda r, f: r.update(acheve_au_tick=4), "achevée"), (lambda r, f: r["releves"][-1].update(etape="piquets"), "5 étape"),
    (lambda r, f: r["releves"][0]["portes_servies"][0].update(rue="rue 1"), "3 portes servies"), (lambda r, f: [q.__setitem__(0, q[0] + 1) for p in f["plans"] for q in p["enceinte"]["contour"]], "3 contour"),
    (lambda r, f: [p["enceinte"].update(travail_requis=19200) for p in f["plans"]], "3 travail requis (servi)")])
def test_ecart(epreuve, refs, changer, cause):
    code, lignes, ecarts = juge(epreuve, refs, changer=changer); assert code == 1 and cause in ecarts, lignes
@pytest.mark.parametrize("changer,cause", [
    (lambda r, f: r.update(defaut="session interrompue"), "défaut de session"), (lambda r, f: r["recu"].update(tick=3), "reçu"), (lambda r, f: r.pop("coins"), "champ absent"),
    (lambda r, f: r["releves"][0].update(tick=-1), "non mesuré"), (lambda r, f: r.update(releves=[]), "échantillon vide"), (lambda r, f: [e.update(tick=t) for e, t in zip(r["releves"], (3, 5, 6))], "ticks des relevés"),
    (lambda r, f: r.update(travail_enceinte="30"), "travail_enceinte"), (lambda r, f: [e.update(portes_servies=[]) for e in r["releves"]], "échantillon vide")])
def test_impossible(epreuve, refs, changer, cause):
    code, lignes, _ = juge(epreuve, refs, changer=changer); assert code == 2 and len(lignes) == 1 and cause in lignes[0], lignes
def test_commande_reference(epreuve):
    normal, ignore = " ".join(epreuve.commande_reference(0, False)), epreuve.commande_reference(0, True); options = "--epreuve --travail-enceinte 0.01 --seed 0 --jours-par-seconde 0"
    assert "-m sim.service" in normal and normal.endswith(options) and "-c" in ignore and str(LANCEUR) in ignore and " ".join(ignore).endswith(options) and "-m" not in ignore
def test_main_sans_unity(epreuve, tmp_path, monkeypatch):
    for nom in ("lot937-enceinte.json", "verdict.txt", "S--1-enceinte-en-chantier.png", "S--2-enceinte-finie.png"): (tmp_path / nom).write_text("ancien", encoding="utf-8")
    for cible, nom in ((epreuve.subprocess, "Popen"), (epreuve.JALON1, "_unity"), (epreuve.JOUER, "_repond")): monkeypatch.setattr(cible, nom, lambda *a, **k: pytest.fail(f"{nom} appelé"))
    assert epreuve.main(["--sortie", str(tmp_path), "--unity", str(tmp_path / "absent" / "Unity.exe")]) == 2 and sorted(p.name for p in tmp_path.iterdir()) == ["verdict.txt"]
@pytest.mark.parametrize("contre", [[], ["--contre", "ignore"], ["--contre", "sans-porte"]])
def test_main_commande_unity(epreuve, tmp_path, monkeypatch, contre):
    (unity := tmp_path / "Unity.exe").write_text("faux", encoding="utf-8"); notes = []
    for cible in {id(m): m for m in (epreuve.JOUER, epreuve.JALON1.JOUER)}.values(): monkeypatch.setattr(cible, "_repond", lambda *a: False)
    monkeypatch.setattr(epreuve.JALON1, "_unity", lambda commande: notes.append(commande) or 1); monkeypatch.setattr(epreuve.subprocess, "Popen", lambda *a, **k: pytest.fail("référence lancée"))
    assert epreuve.main(["--sortie", str(tmp_path / "sortie"), "--unity", str(unity), *contre]) == 2 and len(notes) == 1; vus = " ".join(notes[0])
    assert all(o in vus for o in ("-forgeLot 937", "-forgeServiceEpreuve", "-forgeTravailEnceinte 0.01")) and ("-forge937SansPorte" in vus) == (contre[-1:] == ["sans-porte"])
