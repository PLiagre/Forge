"""L'épreuve HTTP se juge contre le vrai rejeu CLI, avec ses contre-épreuves."""
import copy, json, os, time
import importlib.util
from contextlib import contextmanager
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
    journal = [{"tick": n, "intention": {"type": nom}} for n, nom in enumerate(types)]
    recus = [{"type": nom, "apres_le_tick": n} for n, nom in enumerate(types)]
    epreuve.juger_recus(journal, recus)
    recus[2]["type"] = "autre"
    with pytest.raises(ValueError, match="reçu Unity différent du journal"): epreuve.juger_recus(journal, recus)

def test_un_monde_change_pendant_la_relance():
    with pytest.raises(ValueError, match="monde changé pendant la relance"):
        epreuve.juger_monde_relance(b"avant", b"apres", b"journal", b"journal")

def _rapports_dessin():
    vide = epreuve.hashlib.sha256(b"").hexdigest()
    ville = {"tick": 10, "rues": [0], "rues_posees": [0],
             "parcelles": [{"identifiant": 0, "nature": "", "etat": "bornes"}],
             "parcelles_plan": [{"identifiant": 0, "nature": "", "etat": "bornes"}],
             "batiments": [{"identifiant": 0, "nature": "scierie", "etat": "piquets"}],
             "batiments_plan": [{"identifiant": 0, "nature": "scierie", "etat": "piquets"}],
             "pieces_parcelles": 1, "pieces_batiments": 1,
             "empreinte_rues": "rue", "empreinte_parcelles": "parcelle", "empreinte_batiments": "batiment"}
    vierge = {"tick": 0, "rues": [], "rues_posees": [], "parcelles": [], "parcelles_plan": [],
              "batiments": [], "batiments_plan": [], "pieces_parcelles": 0, "pieces_batiments": 0,
              "empreinte_rues": "sable", "empreinte_parcelles": vide, "empreinte_batiments": vide}
    return {"ville": ville, "vierge": "sable"}, {"ville": dict(ville), "vierge": "sable"}, {"ville": vierge, "vierge": "sable"}

@pytest.mark.parametrize("cas", ["empreinte", "pièce"])
def test_une_empreinte_ou_une_piece_viole_le_dessin(cas):
    jouer, relance, vierge = copy.deepcopy(_rapports_dessin())
    if cas == "empreinte": relance["ville"]["empreinte_rues"] = "autre"
    else: vierge["ville"]["pieces_parcelles"] = 1
    with pytest.raises(ValueError, match="empreinte de relance|pièce dans le rapport vierge"):
        epreuve.juger_dessin(jouer, relance, vierge, 10)

def test_la_ville_locale_sans_unity_est_refusee(tmp_path):
    assert epreuve.main(["--sortie", str(tmp_path), "--ville-locale"]) == 2

def test_la_recette_unity_fixe_graine_cellule_et_ticks(tmp_path):
    assert epreuve.main(["--avec-unity", "--sortie", str(tmp_path), "--ticks", "9"]) == 2
    assert "code : 2" in (tmp_path / "verdict.txt").read_text(encoding="utf-8")

@pytest.mark.parametrize("panne", ["indisponible", "délai", "session", "rapport", "ancien"])
def test_une_panne_unity_ecrit_le_verdict_et_nettoie(tmp_path, monkeypatch, panne):
    dossier, ferme = tmp_path / "preuve", []
    dossier.mkdir()
    @contextmanager
    def service(*args):
        try: yield None
        finally: ferme.append(True)
    monkeypatch.setattr(epreuve, "lancer_service", service)
    if panne == "indisponible":
        monkeypatch.setattr(epreuve, "charger_aides", lambda: {
            "unity": str(tmp_path / "Unity.exe"), "disposition": {"id": "x", "seed": 0},
            "projet": tmp_path, "sorties": tmp_path})
    else:
        monkeypatch.setattr(epreuve, "charger_aides", lambda: {"unity": sys.executable, "projet": tmp_path})
        monkeypatch.setattr(epreuve, "verifier_prealables", lambda aides: None)
        monkeypatch.setattr(epreuve, "preparer_sessions", lambda aides, locale: dossier)
        if panne == "ancien":
            ancien = dossier / "jouer.json"
            ancien.write_text("{}", encoding="utf-8")
            os.utime(ancien, (time.time() - 30,) * 2)
        def appel(aides, nom, sortie):
            if panne == "délai": raise OSError("délai Unity dépassé")
            return 5 if panne == "session" else 0
        monkeypatch.setattr(epreuve, "appeler_unity", appel)
    sortie = tmp_path / "sortie"
    assert epreuve.main(["--avec-unity", "--sortie", str(sortie)]) == 2
    texte = (sortie / "verdict.txt").read_text(encoding="utf-8")
    assert texte.startswith("essai impossible\n") and "code : 2" in texte and " : tenu" not in texte
    assert {"indisponible": "introuvable", "délai": "délai Unity dépassé", "session": "session en erreur",
            "rapport": "rapport absent", "ancien": "rapport ancien"}[panne] in texte
    assert ferme == ([] if panne == "indisponible" else [True])
    port_libre()
