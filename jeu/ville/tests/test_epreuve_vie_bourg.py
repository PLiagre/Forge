"""Juge et lanceur de l'épreuve de la vie du bourg (#782). Les deux rapports versés sont relus tels quels, mutés en mémoire seulement ; la référence vient d'un vrai service d'épreuve, graine 0."""
import copy, importlib.util, json, re
from pathlib import Path
import pytest
RACINE = Path(__file__).resolve().parents[3]
M782 = RACINE / "docs/mesures/782-epreuve-vie-bourg"
lu = lambda nom: json.loads((M782 / f"rapport-{nom}.json").read_text(encoding="utf-8-sig"))  # noqa: E731
@pytest.fixture(scope="module")
def epreuve():
    assert (chemin := RACINE / "pc/epreuve_vie_bourg.py").is_file(), f"fichier introuvable : {chemin}"
    module = importlib.util.module_from_spec(spec := importlib.util.spec_from_file_location("epreuve_vie_bourg", chemin)); spec.loader.exec_module(module); return module
@pytest.fixture(scope="module")
def refs(epreuve):
    from sim.tests.test_monde import _service_epreuve
    with _service_epreuve(epreuve=True) as (_serveur, port): return epreuve.references(port)
def juge(epreuve, refs, nom="normal", changer=lambda r, f: None):
    r, f = lu(nom), copy.deepcopy(refs); changer(r, f); avant = copy.deepcopy((r, f))
    code, lignes = epreuve.juger(r, f); assert (r, f) == avant, "le juge a modifié ses entrées"
    return code, lignes, [l for l in lignes if l.endswith(" · ÉCART")]
def test_normal_egal(epreuve, refs):
    code, lignes, ecarts = juge(epreuve, refs); fumees = re.findall(r"^(nourrie|affamee) : .* fumées (\d+)/(\d+)", "\n".join(lignes), re.M)
    assert (code, ecarts) == (0, []) and len(fumees) == 2 and int(fumees[0][2]) > 0 and fumees == [("nourrie", fumees[0][2], fumees[0][2]), ("affamee", "0", fumees[0][2])], lignes
@pytest.mark.parametrize("drapeau", [None, False])
def test_contre_etal_plein_en_famine(epreuve, refs, drapeau):
    code, lignes, ecarts = juge(epreuve, refs, "contre", lambda r, f: drapeau is None or r.update(contre_epreuve=drapeau))
    assert code == 1 and [l.split(" : ")[:2] for l in ecarts] == [["affamee étal", "étal plein en famine"]] and lu("contre")["contre_epreuve"] is True, lignes
    assert ecarts == juge(epreuve, refs, "contre")[2]
def _maison(i, **champs): return lambda r, f: r["etats"][i]["maisons"][0].update(champs)
@pytest.mark.parametrize("changer,cause", [
    (_maison(1, emission=True), "affamee fumées"), (_maison(0, particules=0), "nourrie fumées"), (lambda r, f: r["etats"][0]["maisons"].pop(), "nourrie maisons manquantes"),
    (lambda r, f: r["etats"][1]["maisons"].append(dict(r["etats"][1]["maisons"][0])), "affamee maisons en double"), (lambda r, f: r["etats"][0].update(nourriture_kg=r["etats"][0]["nourriture_kg"] + 1e-9), "nourrie nourriture_kg"),
    (lambda r, f: r["etats"][1].update(faim_ticks=r["etats"][1]["faim_ticks"] + 1), "affamee faim_ticks"), (lambda r, f: r["etats"][0].update(tick=r["etats"][0]["tick"] + 1), "nourrie tick"),
    (lambda r, f: r["etats"][1]["maisons"][0].update(intensite=r["etats"][1]["maisons"][0]["intensite"] * 2), "lampes éteintes ou changées")])
def test_ecart_de_mesure(epreuve, refs, changer, cause):
    code, lignes, ecarts = juge(epreuve, refs, changer=changer); assert code == 1 and cause in [l.split(" : ")[0] for l in ecarts], lignes
@pytest.mark.parametrize("changer,cause", [
    *((lambda r, f, i=i, k=k: r["etats"][i].update({k: []}), "échantillon vide") for i in (0, 1) for k in ("maisons", "etals")),
    *((lambda r, f, i=i: [x.update(marchandise="sel") for x in r["etats"][i]["etals"]], "aucun étal nourriture") for i in (0, 1)),
    (lambda r, f: r.update(defaut="session interrompue"), "défaut de session"), (lambda r, f: r["etats"][1].update(faim_ticks=-1), "non mesuré"),
    (lambda r, f: f["affamee"]["lieu"]["bourg"]["stocks"].update(nourriture=1.0), "référence affamee inutilisable")])
def test_impossible(epreuve, refs, changer, cause):
    code, lignes, _ = juge(epreuve, refs, changer=changer); assert code == 2 and len(lignes) == 1 and cause in lignes[0], lignes
def test_service_sans_epreuve(epreuve):
    from sim.tests.test_monde import _service_epreuve
    with _service_epreuve() as (_serveur, port), pytest.raises(RuntimeError, match="POST /epreuve/vider-panier.* HTTP 404"): epreuve.references(port)
def test_main_sans_unity(epreuve, tmp_path, monkeypatch):
    for nom in ("vie-bourg.json", "verdict.txt", "Scene--01-place-nourrie.png"): (tmp_path / nom).write_text("ancien", encoding="utf-8")
    for cible, nom in ((epreuve.subprocess, "Popen"), (epreuve.JALON1, "_unity"), (epreuve.JOUER, "_repond"), (epreuve.JALON1.JOUER, "_repond")): monkeypatch.setattr(cible, nom, lambda *a, **k: pytest.fail(f"{nom} appelé"))
    assert epreuve.main(["--sortie", str(tmp_path), "--unity", str(tmp_path / "absent" / "Unity.exe")]) == 2
    assert "Unity absent" in (verdict := (tmp_path / "verdict.txt").read_text(encoding="utf-8")) and verdict.startswith("ÉPREUVE IMPOSSIBLE") and sorted(p.name for p in tmp_path.iterdir()) == ["verdict.txt"]
