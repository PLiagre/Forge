"""Juge et lanceur de l'épreuve des passants (#898). Les quatre rapports versés sont relus tels quels, mutés en mémoire seulement ; la référence vient d'un vrai service d'épreuve, graine 0."""
import copy, importlib.util, json
from pathlib import Path
import pytest
RACINE = Path(__file__).resolve().parents[3]
M898 = RACINE / "docs/mesures/898-epreuve-passants"
lu = lambda nom: json.loads((M898 / f"rapport-{nom}.json").read_text(encoding="utf-8-sig"))  # noqa: E731
@pytest.fixture(scope="module")
def epreuve():
    assert (chemin := RACINE / "pc/epreuve_passants.py").is_file(), f"fichier introuvable : {chemin}"; module = importlib.util.module_from_spec(spec := importlib.util.spec_from_file_location("epreuve_passants", chemin)); spec.loader.exec_module(module); return module
@pytest.fixture(scope="module")
def refs(epreuve):
    from sim.tests.test_monde import _service_epreuve
    with _service_epreuve(epreuve=True) as (_serveur, port): return epreuve.references(port)
def juge(epreuve, refs, nom="normal", changer=lambda r, f: None):
    r, f = lu(nom), copy.deepcopy(refs); changer(r, f); avant = copy.deepcopy((r, f)); code, lignes = epreuve.juger(r, f); assert (r, f) == avant, "le juge a modifié ses entrées"; return code, lignes, [l.split(" : ")[0] for l in lignes if l.endswith(" · ÉCART")]
TEMOIN = {"artisans": 19, "mineurs": 24, "paysans": 957}
@pytest.mark.parametrize("bourg,metiers,parts", [(109, TEMOIN, {"artisans": 2, "mineurs": 2, "paysans": 6}), (10, {"forgerons": 5, "mineurs": 5, "paysans": 990}, {"forgerons": 1}),
                                                 (10, {"paysans": 990, "mineurs": 5, "forgerons": 5}, {"forgerons": 1}), (20, TEMOIN, {"artisans": 1, "mineurs": 1}), (0, TEMOIN, {})])
def test_passants_attendus(epreuve, bourg, metiers, parts):
    lieu = {"population": 1000, "bourg": {"population": bourg}, "foyers": {m: {"personnes": p} for m, p in metiers.items()}}
    assert {m: n for m, n in epreuve.passants_attendus(lieu).items() if n} == parts and sum(epreuve.passants_attendus(lieu).values()) == bourg // 10
def test_reference_mesuree(epreuve, refs):
    assert epreuve.passants_attendus(refs["chantier"]["lieu"]) == {"ouvriers": 1, "paysans": 15} and epreuve.passants_attendus(refs["vide"]["lieu"]) == {}
def test_normal_egal(epreuve, refs):
    code, lignes, ecarts = juge(epreuve, refs); assert (code, ecarts) == (0, []) and "16 passants vus {ouvriers 1, paysans 15}" in lignes[1] and "ouvriers sur un chantier 1/1" in lignes[1], lignes
@pytest.mark.parametrize("nom,attendus", [("en-trop", ["chantier nombre"]), ("ailleurs", ["chantier ouvrier hors chantier"]), ("anciens", ["vide nombre", "vide anciens objets maintenus"])])
def test_contre_epreuves(epreuve, refs, nom, attendus):
    code, lignes, ecarts = juge(epreuve, refs, nom); assert code == 1 and ecarts == attendus and lu(nom)["contre_epreuve"], lignes
    assert juge(epreuve, refs, nom, lambda r, f: r.update(contre_epreuve=""))[:3:2] == (1, attendus)
def _ouvrier(r): return next(p for p in r["etats"][0]["liste"] if p["metier"] == "ouvriers")
def _paysan(r): return next(i for i, p in enumerate(r["etats"][0]["liste"]) if p["metier"] == "paysans")
@pytest.mark.parametrize("changer,cause", [
    (lambda r, f: _ouvrier(r).update(y=_ouvrier(r)["y"] + 0.1), "chantier ouvrier hors chantier"), (lambda r, f: _ouvrier(r).update(destination="rue 9"), "chantier ouvrier hors chantier"),
    (lambda r, f: r["etats"][0]["liste"].pop(_paysan(r)), "chantier nombre"), (lambda r, f: r["etats"][0]["liste"].append(dict(r["etats"][0]["liste"][_paysan(r)])), "chantier id en double"),
    (lambda r, f: r["etats"][0].update(bourg=r["etats"][0]["bourg"] + 1), "chantier bourg"), (lambda r, f: r["etats"][0].update(tick_plan=r["etats"][0]["tick_plan"] + 1), "chantier tick_plan"),
    (lambda r, f: r["etats"][1]["liste"].append(dict(r["etats"][0]["liste"][0])), "vide nombre")])
def test_ecart_de_mesure(epreuve, refs, changer, cause):
    code, lignes, ecarts = juge(epreuve, refs, changer=changer); assert code == 1 and cause in ecarts, lignes
def test_paysan_double_se_compte_dans_liste(epreuve, refs):
    assert "chantier nombre" in juge(epreuve, refs, changer=lambda r, f: r["etats"][0]["liste"].append(dict(r["etats"][0]["liste"][_paysan(r)])))[2]
@pytest.mark.parametrize("changer,cause", [
    (lambda r, f: r.update(defaut="session interrompue"), "défaut de session"), (lambda r, f: r["etats"].reverse(), "états"), (lambda r, f: r["etats"][1].pop("camera"), "champ absent"),
    (lambda r, f: r["etats"][0].update(bourg=-1), "non mesuré"), (lambda r, f: [x.update(bras=0) for x in f["chantier"]["plan"]["chantiers_du_jour"]], "échantillon vide"),
    (lambda r, f: f["vide"]["lieu"]["bourg"].update(population=5), "bourg vidé à 5")])
def test_impossible(epreuve, refs, changer, cause):
    code, lignes, _ = juge(epreuve, refs, changer=changer); assert code == 2 and len(lignes) == 1 and cause in lignes[0], lignes
def test_service_sans_epreuve(epreuve):
    from sim.tests.test_monde import _service_epreuve
    with _service_epreuve() as (_serveur, port), pytest.raises(RuntimeError, match="POST /epreuve/vider-bourg.* HTTP 404"): epreuve.references(port)
def test_main_sans_unity(epreuve, tmp_path, monkeypatch):
    for nom in ("passants-bourg.json", "verdict.txt", "Scene--01-ouvriers-au-chantier.png", "Scene--02-bourg-vide.png"): (tmp_path / nom).write_text("ancien", encoding="utf-8")
    for cible, nom in ((epreuve.subprocess, "Popen"), (epreuve.JALON1, "_unity"), (epreuve.JOUER, "_repond"), (epreuve.JALON1.JOUER, "_repond")): monkeypatch.setattr(cible, nom, lambda *a, **k: pytest.fail(f"{nom} appelé"))
    assert epreuve.main(["--sortie", str(tmp_path), "--unity", str(tmp_path / "absent" / "Unity.exe")]) == 2
    assert "Unity absent" in (verdict := (tmp_path / "verdict.txt").read_text(encoding="utf-8")) and verdict.startswith("ÉPREUVE IMPOSSIBLE") and sorted(p.name for p in tmp_path.iterdir()) == ["verdict.txt"]
