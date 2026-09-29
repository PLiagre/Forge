"""pc/jouer.py démarre le service, lance le jeu, puis arrête le service (lot #120, SC2).

Le jeu est un faux jeu écrit ici : il lit `-forgeCell`, interroge le service,
écrit ce qu'il a reçu dans un fichier, et sort avec le code demandé.
"""

import importlib.util
import inspect
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

JEU = Path(__file__).resolve().parents[2]
RACINE = JEU.parent
LANCEUR = RACINE / "pc" / "jouer.py"
REGLE = JEU / "ville" / "cellule_du_desert.py"
PANNEAU = RACINE / "3d" / "unity" / "Assets" / "ForgeLocal3D" / "Pont" / "PanneauLieu.cs"
HOTE = "127.0.0.1"
CELLULE_DU_PANNEAU = 1175
CELLULE_ABSENTE = 99999999
CODE_DU_JEU_QUI_PLANTE = 3
DELAI_LANCEUR_S = 180
ECART_ENTRE_HORLOGES_S = 1.5
PAS_DE_SURVEILLANCE_S = 0.05

if str(JEU) not in sys.path:
    sys.path.insert(0, str(JEU))


def _charger(nom, chemin):
    spec = importlib.util.spec_from_file_location(nom, chemin)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def port_refuse(port):
    """Vrai si aucune connexion TCP n'aboutit sur 127.0.0.1:port : rien n'y répond."""
    import socket

    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return False
    except OSError:
        return True


# Le faux jeu embarque la même fonction `port_refuse`, recopiée par inspect :
# le contrôle d'arrêt est unique, et sa contre-épreuve tourne pendant le jeu.
FAUX_JEU = inspect.getsource(port_refuse) + '''
import json, sys, time, urllib.error, urllib.request

sortie, code, port = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
cellule = sys.argv[sys.argv.index("-forgeCell") + 1]
base = f"http://127.0.0.1:{port}"
try:
    with urllib.request.urlopen(f"{base}/lieu?cell={cellule}") as r:
        statut, lieu = r.status, json.loads(r.read())
except urllib.error.HTTPError as exc:
    statut, lieu = exc.code, {}
ticks = []
for attente in (0, ECART):
    time.sleep(attente)
    with urllib.request.urlopen(f"{base}/horloge") as r:
        ticks.append(json.loads(r.read())["tick"])
with open(sortie, "w", encoding="utf-8") as f:
    json.dump({"forgeCell": cellule, "statut": statut, "cell_id": lieu.get("cell_id"),
               "ticks": ticks, "refuse_pendant": port_refuse(port)}, f)
sys.exit(code)
'''.replace("ECART", repr(ECART_ENTRE_HORLOGES_S))


def _port_libre():
    with socket.socket() as s:
        s.bind((HOTE, 0))
        return s.getsockname()[1]


@pytest.fixture
def faux_jeu(tmp_path):
    chemin = tmp_path / "faux_jeu.py"
    chemin.write_text(FAUX_JEU, encoding="utf-8")
    return chemin


def _lancer(port, commande, *options):
    return subprocess.Popen(
        [sys.executable, str(LANCEUR), "--port", str(port), *options, "--", *commande],
        cwd=RACINE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=os.environ | {"PYTHONIOENCODING": "utf-8"},
    )


def _jouer(port, commande, *options):
    lanceur = _lancer(port, commande, *options)
    sortie, _ = lanceur.communicate(timeout=DELAI_LANCEUR_S)
    return lanceur.returncode, sortie


def _commande_du_faux_jeu(faux_jeu, sortie, code, port):
    return [sys.executable, str(faux_jeu), str(sortie), str(code), str(port)]


def test_chemin_nominal(faux_jeu, tmp_path):
    port, sortie = _port_libre(), tmp_path / "recu.json"
    code, texte = _jouer(port, _commande_du_faux_jeu(faux_jeu, sortie, 0, port))
    assert code == 0, texte
    assert port_refuse(port), f"le service répond encore sur {port} après la sortie du lanceur"
    recu = json.loads(sortie.read_text(encoding="utf-8"))
    attendue = _charger("cellule_du_desert", REGLE).charger_et_choisir()
    assert recu["forgeCell"] == str(attendue)
    assert recu["statut"] == 200
    assert recu["cell_id"] == attendue
    premier, second = recu["ticks"]
    assert second > premier, f"l'horloge ne tourne pas : {recu['ticks']}"
    # Contre-épreuve : le même contrôle, appliqué pendant le jeu, dit « répond ».
    assert recu["refuse_pendant"] is False
    for ligne in (f"cellule {attendue}", f"service prêt sur {HOTE}:{port}", "jeu fermé (code 0)", "service arrêté"):
        assert ligne in texte


def test_le_jeu_plante(faux_jeu, tmp_path):
    port, sortie = _port_libre(), tmp_path / "recu.json"
    code, texte = _jouer(port, _commande_du_faux_jeu(faux_jeu, sortie, CODE_DU_JEU_QUI_PLANTE, port))
    assert code == CODE_DU_JEU_QUI_PLANTE, texte
    assert port_refuse(port)


def test_cellule_choisie(faux_jeu, tmp_path):
    port, sortie = _port_libre(), tmp_path / "recu.json"
    code, texte = _jouer(
        port, _commande_du_faux_jeu(faux_jeu, sortie, 0, port), "--cellule", str(CELLULE_DU_PANNEAU)
    )
    assert code == 0, texte
    recu = json.loads(sortie.read_text(encoding="utf-8"))
    assert recu["forgeCell"] == str(CELLULE_DU_PANNEAU)
    assert recu["statut"] == 200
    assert recu["cell_id"] == CELLULE_DU_PANNEAU
    assert port_refuse(port)


def test_cellule_absente_de_la_carte(faux_jeu, tmp_path):
    port, sortie = _port_libre(), tmp_path / "recu.json"
    code, texte = _jouer(
        port, _commande_du_faux_jeu(faux_jeu, sortie, 0, port), "--cellule", str(CELLULE_ABSENTE)
    )
    assert code != 0
    assert str(CELLULE_ABSENTE) in texte and "404" in texte, texte
    assert not sortie.exists(), "le jeu a été lancé malgré le refus du service"
    assert port_refuse(port)


def test_pas_de_build(tmp_path):
    port, absent = _port_libre(), tmp_path / "Forge.exe"
    lanceur = _lancer(port, [str(absent)])
    reponses = []
    while lanceur.poll() is None:
        reponses.append(not port_refuse(port))
        time.sleep(PAS_DE_SURVEILLANCE_S)
    texte, _ = lanceur.communicate(timeout=DELAI_LANCEUR_S)
    assert lanceur.returncode != 0
    assert str(absent) in texte and "builds" in texte, texte
    assert not any(reponses), "un service a répondu alors que le build manquait"
    assert port_refuse(port)


def test_port_deja_pris(faux_jeu, tmp_path):
    sortie = tmp_path / "recu.json"
    with socket.socket() as occupant:
        occupant.bind((HOTE, 0))
        occupant.listen()
        port = occupant.getsockname()[1]
        acceptes = []
        threading.Thread(target=lambda: acceptes.append(occupant.accept()), daemon=True).start()
        code, texte = _jouer(port, _commande_du_faux_jeu(faux_jeu, sortie, 0, port))
        for connexion, _ in acceptes:
            connexion.close()
    assert code != 0
    assert str(port) in texte, texte
    assert not sortie.exists(), "le faux jeu a tourné sur un port déjà pris"


def test_le_meme_port_partout():
    from sim.service import DEFAULT_SERVICE_PORT

    jouer = _charger("jouer", LANCEUR)
    assert jouer.analyseur().get_default("port") == DEFAULT_SERVICE_PORT
    assert PANNEAU.is_file(), f"fichier absent : {PANNEAU}"
    trouve = re.search(r"DEFAULT_SERVICE_PORT\s*=\s*(\d+)\s*;", PANNEAU.read_text(encoding="utf-8"))
    assert trouve, f"constante DEFAULT_SERVICE_PORT introuvable dans {PANNEAU}"
    assert int(trouve.group(1)) == DEFAULT_SERVICE_PORT
