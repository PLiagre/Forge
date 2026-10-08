"""L'épreuve HTTP se juge contre le vrai rejeu CLI, avec ses contre-épreuves."""
import copy, json, os, time
import importlib.util
from pathlib import Path
import socket, subprocess, sys
import pytest
SCRIPT = Path(__file__).resolve().parents[3] / "pc/epreuve_jalon4.py"
spec = importlib.util.spec_from_file_location("epreuve_jalon4", SCRIPT); epreuve = importlib.util.module_from_spec(spec)
spec.loader.exec_module(epreuve)

def port_libre():
    with socket.socket() as prise:
        prise.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        prise.bind(("127.0.0.1", 8000))

@pytest.fixture(scope="module")
def preuve(tmp_path_factory):
    sortie = tmp_path_factory.mktemp("jalon4")
    original = epreuve.service.recevoir_intention
    assert epreuve.main(["--sortie", str(sortie), "--service-sourd"]) == 1 and epreuve.service.recevoir_intention is original
    port_libre()
    sourds = [sortie.joinpath(nom).read_bytes() for nom in epreuve.MONDES]
    with pytest.raises(ValueError, match="octets : écart"): epreuve.juger(*sourds, json.loads(sortie.joinpath("journal.json").read_bytes()), 10)
    assert epreuve.main(["--sortie", str(sortie)]) == 0 and epreuve.service.recevoir_intention is original
    port_libre()
    mondes = [sortie.joinpath(nom).read_bytes() for nom in epreuve.MONDES]
    journal = json.loads(sortie.joinpath("journal.json").read_bytes())
    assert [entree["tick"] for entree in journal] == [2, 3, 5]
    bilan = epreuve.juger(*mondes, journal, 10)
    assert bilan["cellules_modifiees"] == bilan["plans_modifies"] == ["1175"]
    assert bilan["cellules_controlees"] == len(json.loads(mondes[0])["cells"])
    return mondes, journal

@pytest.mark.parametrize("cas", ["journal vide", "type absent", "monde vide", "octets", "témoin"])
def test_le_jugement_refuse_les_fausses_preuves(preuve, cas):
    mondes, journal = copy.deepcopy(preuve)
    if cas == "journal vide": journal = []
    if cas == "type absent": journal.pop()
    if cas == "monde vide": mondes[0] = b"{}"
    if cas == "octets":
        monde = json.loads(mondes[0])
        autre = next(c for cid, c in monde["cells"].items() if cid != "1175")
        autre["stocks"]["sel de contre-épreuve"] = 1
        mondes[0] = epreuve.serialiser(monde)
    if cas == "témoin": mondes[2] = mondes[1]
    with pytest.raises(ValueError, match=cas): epreuve.juger(*mondes, journal, 10)

@pytest.mark.parametrize("population", [0, 100, 103])
def test_la_conservation_independante_des_octets(population):
    complets, dernier = divmod(population, epreuve.constantes.TAILLE_FOYER)
    metiers = {"paysans": dict(personnes=population, complets=complets, dernier=dernier)} if population else {}
    monde = {"cells": {"1": {"population": population, "foyers": metiers}}}
    epreuve.controler_foyers(monde)
    if not population: return
    variantes = [dict(paysans=dict(personnes=population, complets=complets, dernier=dernier - 1)),
                 metiers | {"mineurs": dict(personnes=0, complets=0, dernier=0)},
                 {" ": metiers["paysans"]}, -1, {}]
    for variante in variantes:
        monde["cells"]["1"]["foyers"] = variante
        with pytest.raises(ValueError, match="foyers"): epreuve.controler_foyers(monde)

def test_un_refus_http_ne_journalise_et_ne_change_rien(tmp_path):
    with epreuve.lancer_service(tmp_path, 0, False) as serveur:
        avant = epreuve.http("/monde-complet")
        file_avant = list(serveur.world.intentions_en_attente)
        with pytest.raises(epreuve.HTTPError) as refus: epreuve.http("/intention", {})
        assert refus.value.code == 400
        assert epreuve.http("/monde-complet") == avant and serveur.world.intentions_en_attente == file_avant
        assert json.loads((tmp_path / "journal.json").read_bytes()) == []
    port_libre()

@pytest.mark.parametrize("panne", ["code", "délai", "arrêt"])
def test_une_panne_ferme_le_service_et_interdit_les_anciennes_sorties(tmp_path, monkeypatch, panne):
    for nom in epreuve.MONDES: (tmp_path / nom).write_bytes(b"ancienne preuve")
    if panne == "arrêt":
        fermer = epreuve.service.ServeurMonde.server_close
        def arret(serveur):
            fermer(serveur)
            raise OSError("arrêt refusé")
        monkeypatch.setattr(epreuve.service.ServeurMonde, "server_close", arret)
    else:
        def echouer(commande, **options):
            if panne == "délai": raise subprocess.TimeoutExpired(commande, 1)
            return subprocess.CompletedProcess(commande, 2, b"", "rejeu refusé".encode("utf-8"))
        monkeypatch.setattr(epreuve.subprocess, "run", echouer)
    assert epreuve.main(["--sortie", str(tmp_path)]) == 2
    assert not any((tmp_path / nom).exists() for nom in epreuve.MONDES[1:])
    port_libre()

def test_le_port_occupe_reste_a_son_proprietaire(tmp_path):
    with socket.socket() as occupant:
        occupant.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        occupant.bind(("127.0.0.1", 8000)); occupant.listen()
        resultat = subprocess.run([sys.executable, str(SCRIPT), "--sortie", str(tmp_path)],
                                  capture_output=True, text=True, timeout=30)
        assert resultat.returncode == 2 and "8000" in resultat.stderr
        assert occupant.getsockname() == ("127.0.0.1", 8000)
        with socket.create_connection(occupant.getsockname(), timeout=1): pass

def test_un_recu_unity_different_du_journal():
    types = ("tracer_route", "decouper_parcelle", "poser_batiment")
    journal = [{"tick": n, "intention": {"type": nom}} for n, nom in enumerate(types)]; recus = [{"type": nom, "apres_le_tick": n} for n, nom in enumerate(types)]
    epreuve.juger_recus(journal, recus); recus[2]["type"] = "autre"
    with pytest.raises(ValueError, match="reçu Unity différent du journal"): epreuve.juger_recus(journal, recus)

def test_un_monde_change_pendant_la_relance():
    with pytest.raises(ValueError, match="monde changé pendant la relance"): epreuve.juger_monde_relance(b"avant", b"apres", b"journal", b"journal")

def _rapports():
    vide, trace, bat = epreuve.hashlib.sha256(b"").hexdigest(), [{"identifiant": 0, "nature": "", "etat": "bornes"}], [{"identifiant": 0, "nature": "scierie", "etat": "piquets"}]
    ville = {"tick": 10, "rues": [0], "rues_posees": [0], "parcelles": trace, "parcelles_plan": trace, "batiments": bat, "batiments_plan": bat, "pieces_parcelles": 1, "pieces_batiments": 1, "empreinte_rues": "rue", "empreinte_parcelles": "p", "empreinte_batiments": "b"}
    vierge = {"tick": 0, "rues": [], "rues_posees": [], "parcelles": [], "parcelles_plan": [], "batiments": [], "batiments_plan": [], "pieces_parcelles": 0, "pieces_batiments": 0, "empreinte_rues": "sable", "empreinte_parcelles": vide, "empreinte_batiments": vide}
    return {"ville": ville, "vierge": "sable"}, {"ville": dict(ville), "vierge": "sable"}, {"ville": vierge, "vierge": "sable"}

@pytest.mark.parametrize("cas", ["empreinte", "pièce"])
def test_une_empreinte_ou_une_piece_viole_le_dessin(cas):
    jouer, relance, vierge = _rapports()
    relance["ville"].__setitem__("empreinte_rues", "autre") if cas == "empreinte" else vierge["ville"].__setitem__("pieces_parcelles", 1)
    with pytest.raises(ValueError, match="empreinte de relance|pièce dans le rapport vierge"): epreuve.juger_dessin(jouer, relance, vierge, 10)

def test_les_options_unity_incompatibles_sont_refusees(tmp_path):
    assert epreuve.main(["--sortie", str(tmp_path), "--ville-locale"]) == 2 and epreuve.main(["--avec-unity", "--sortie", str(tmp_path), "--ticks", "9"]) == 2 and "code : 2" in (tmp_path / "verdict.txt").read_text(encoding="utf-8")

def _essai():
    jouer, relance, vierge = _rapports()
    for nom, rapport in (("jouer", jouer), ("relance", relance), ("vierge", vierge)): rapport.update(session=nom, cell=1175, port=8000, implantation="k", defauts=[])
    return type("A", (), {"ticks": 10, "cellule": 1175, "service_sourd": False, "seed": 0})(), jouer, relance, vierge

def test_des_rapports_au_tick_10_et_un_monde_au_tick_9(tmp_path, monkeypatch):
    args, jouer, relance, vierge = _essai(); rapports = {"jouer": jouer, "relance": relance, "vierge": vierge}
    statuts = {nom: ["non exécuté", "x"] for nom in epreuve.STATUTS}; neuf = epreuve.serialiser({"ticks_ecoules": 9})
    assert epreuve.juger_essai(args, tmp_path, statuts, "k", rapports, neuf, neuf, b"j", b"j") == 1
    assert statuts["égalité du monde"][0] == "non exécuté" and "le normal exige 10 ticks" in statuts["relancement"][1] and "tick des rapports différent du monde servi" in statuts["relancement"][1]
    vu = []; monkeypatch.setattr(epreuve, "rejouer", lambda _s, ticks, _seed: vu.append(ticks) or (_ for _ in ()).throw(OSError("stop")))
    jouer["ville"]["tick"] = relance["ville"]["tick"] = 3; args.service_sourd = True; (tmp_path / "journal.json").write_bytes(epreuve.serialiser([]))
    statuts, trois = {nom: ["non exécuté", "x"] for nom in epreuve.STATUTS}, epreuve.serialiser({"ticks_ecoules": 3})
    with pytest.raises(OSError, match="stop"): epreuve.juger_essai(args, tmp_path, statuts, "k", rapports, trois, trois, b"j", b"j")
    assert vu == [3] and "le normal exige 10 ticks" not in statuts["relancement"][1]

@pytest.mark.parametrize("brut", [None, "texte"])
def test_un_rapport_sans_defauts_ne_valide_pas(tmp_path, brut):
    args, jouer, relance, vierge = _essai(); rapports = {"jouer": jouer, "relance": relance, "vierge": vierge}
    for rapport in rapports.values(): rapport.pop("defauts") if brut is None else rapport.__setitem__("defauts", brut)
    with pytest.raises(ValueError, match="défauts absents"): epreuve.juger_essai(args, tmp_path, {}, "k", rapports, b"{}", b"{}", b"j", b"j")

def test_une_exception_unity_est_une_panne(tmp_path):
    args, jouer, relance, vierge = _essai(); rapports = {"jouer": jouer, "relance": relance, "vierge": vierge}
    relance["defauts"] = ["relance : exception : lecture HTTP impossible"]; statuts = {nom: ["non exécuté", "x"] for nom in epreuve.STATUTS}
    assert epreuve.juger_essai(args, tmp_path, statuts, "k", rapports, b"{}", b"{}", b"j", b"j") == 2
    assert statuts["relancement"] == ["non exécuté", "relance : exception : lecture HTTP impossible"] and all(e[0] != "violé" for e in statuts.values())

@pytest.mark.parametrize("panne", ["indisponible", "délai", "session", "rapport", "ancien", "exception"])
def test_une_panne_unity_ecrit_le_verdict_et_nettoie(tmp_path, monkeypatch, panne):
    dossier, ferme = tmp_path / "preuve", []; dossier.mkdir()
    monkeypatch.setattr(epreuve, "lancer_service", lambda *a: type("S", (), {"__enter__": lambda s: None, "__exit__": lambda *a: ferme.append(True) or None})())
    monkeypatch.setattr(epreuve, "port_occupe", lambda: False)
    if panne == "indisponible": monkeypatch.setattr(epreuve, "charger_aides", lambda: {"unity": str(tmp_path / "Unity.exe"), "disposition": {"id": "x", "seed": 0}, "projet": tmp_path, "sorties": tmp_path})
    else:
        monkeypatch.setattr(epreuve, "charger_aides", lambda: {"unity": sys.executable, "projet": tmp_path}); monkeypatch.setattr(epreuve, "verifier_prealables", lambda a: None); monkeypatch.setattr(epreuve, "preparer_sessions", lambda a, _l: dossier)
        if panne == "ancien": ancien = dossier / "jouer.json"; ancien.write_text("{}", encoding="utf-8"); os.utime(ancien, (time.time() - 30,) * 2)
        monkeypatch.setattr(epreuve, "appeler_unity", lambda *_a: (_ for _ in ()).throw(OSError("délai Unity dépassé")) if panne == "délai" else (bool((dossier / "jouer.json").write_text('{"defauts":["jouer : exception : lecture HTTP impossible"]}', encoding="utf-8")) or 1) if panne == "exception" else (5 if panne == "session" else 0))
    sortie = tmp_path / "sortie"; assert epreuve.main(["--avec-unity", "--sortie", str(sortie)]) == 2; texte = (sortie / "verdict.txt").read_text(encoding="utf-8")
    attendu = {"indisponible": "introuvable", "délai": "délai Unity dépassé", "session": "session en erreur", "rapport": "rapport absent", "ancien": "rapport ancien", "exception": "jouer : exception : lecture HTTP impossible"}[panne]
    assert texte.startswith("essai impossible\n") and "code : 2" in texte and " : tenu" not in texte and attendu in texte
    if panne == "exception": assert "invariant violé" not in texte and "violé —" not in texte
    assert ferme == ([] if panne == "indisponible" else [True]); port_libre()
