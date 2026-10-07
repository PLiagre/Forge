"""L'épreuve HTTP se juge contre le vrai rejeu CLI, avec ses contre-épreuves."""
import copy, json
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
