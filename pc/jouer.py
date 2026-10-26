"""Le lanceur du jeu : démarre le service de sim/, puis le jeu.

    py pc\\jouer.py [--port P] [--cellule C] [--carte] -- <commande du jeu…>

Sans `--cellule`, aucune cellule n'est imposée : le jeu lit la maison du joueur,
ouvre sa capitale ou la carte, ou dit l'absence (lot #688).
Avec `--carte`, le jeu s'ouvre sur la carte
de 1400 (`-forgeCarte`, lot #524) au lieu de la ville. Le service s'arrête
quand le jeu se ferme, qu'il plante, ou que le joueur interrompt le lanceur.
La vitesse d'ouverture vient du fichier de réglages partagé avec Unity : celle
de la carte, ou celle de la ville si `--cellule` est donné sans `--carte`.
"""
from __future__ import annotations

import argparse
import collections
import http.client
import importlib.util
import json
import math
import os
import queue
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http import HTTPStatus
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
JEU_PY = RACINE / "jeu"
REGLAGES = RACINE / "3d/unity/Assets/ForgeLocal3D/Pont/Resources/ReglagesDesVues.json"
sys.path.insert(0, str(JEU_PY))
from sim.service import DEFAULT_SERVICE_PORT, SERVICE_HOST  # noqa: E402

REGLE = JEU_PY / "ville" / "cellule_du_desert.py"
AUCUNE_CELLULE = "aucune cellule imposée : le jeu lit la maison du joueur"
ARGUMENT_CARTE = "-forgeCarte"  # celui d'OuvertureDeLaCarte.cs
DELAI_SERVICE_PRET_S = 60
DELAI_ARRET_S = 5
DELAI_CONNEXION_S = 1
DELAI_REQUETE_S = 10
LIGNES_STDERR_GARDEES = 20
FIN_DE_FLUX = None


def _vitesse(carte: bool, cellule: int | None) -> tuple[str, float]:
    vue = "ville" if cellule is not None and not carte else "carte"
    cle = f"VITESSE_{vue.upper()}"
    try:
        valeur = json.loads(REGLAGES.read_text(encoding="utf-8"))[cle]
        if isinstance(valeur, bool) or not isinstance(valeur, (int, float)):
            raise ValueError("un nombre est attendu")
        vitesse = float(valeur)
        if not math.isfinite(vitesse) or vitesse <= 0:
            raise ValueError("un nombre fini strictement positif est attendu")
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
        raise RuntimeError(f"{REGLAGES} : {cle} invalide ({exc})") from exc
    return vue, vitesse


def _regle():
    spec = importlib.util.spec_from_file_location("cellule_du_desert", REGLE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _cellule(valeur: str) -> int:
    try:
        cellule = int(valeur)
    except ValueError:
        cellule = -1
    if cellule < 0:
        raise argparse.ArgumentTypeError(
            f"--cellule invalide : reçu {valeur!r}, attendu un entier ≥ 0"
        )
    return cellule


def _repond(port: int) -> bool:
    try:
        with socket.create_connection((SERVICE_HOST, port), timeout=DELAI_CONNEXION_S):
            return True
    except OSError:
        return False


def _lire_flux(flux, sortie) -> None:
    for ligne in flux:
        sortie(ligne.rstrip("\r\n"))
    sortie(FIN_DE_FLUX)


def _fin(stderr: collections.deque) -> str:
    return " | ".join(ligne for ligne in stderr if ligne is not FIN_DE_FLUX) or "(vide)"


def _delai_depasse(attendue: str, stderr: collections.deque) -> RuntimeError:
    return RuntimeError(
        f"le service n'a pas dit « {attendue} » en {DELAI_SERVICE_PRET_S} s ; "
        f"fin de stderr : {_fin(stderr)}"
    )


def _attendre_pret(service: subprocess.Popen, attendue: str, stderr: collections.deque) -> None:
    lignes: queue.Queue = queue.Queue()
    threading.Thread(target=_lire_flux, args=(service.stdout, lignes.put), daemon=True).start()
    echeance = time.monotonic() + DELAI_SERVICE_PRET_S
    while True:
        reste = echeance - time.monotonic()
        # Échéance atteinte : on ne lit plus, même si la file a déjà des lignes.
        # Sinon un service bavard (timeout=0 qui rend tout de suite) ne s'arrête jamais.
        if reste <= 0:
            raise _delai_depasse(attendue, stderr)
        try:
            ligne = lignes.get(timeout=reste)
        except queue.Empty:
            raise _delai_depasse(attendue, stderr)
        if ligne == attendue:
            return
        if ligne is FIN_DE_FLUX:
            raise RuntimeError(
                f"le service s'est arrêté (code {service.poll()}) avant d'être prêt ; "
                f"fin de stderr : {_fin(stderr)}"
            )
        # Ligne reçue, mais ce n'est pas « prêt » : l'échéance se recontrôle ici,
        # pas seulement quand la file est vide.
        if time.monotonic() >= echeance:
            raise _delai_depasse(attendue, stderr)


def _verifier_lieu(port: int, cellule: int, stderr: collections.deque) -> None:
    url = f"http://{SERVICE_HOST}:{port}/lieu?cell={cellule}"
    try:
        with urllib.request.urlopen(url, timeout=DELAI_REQUETE_S) as reponse:
            statut, corps = reponse.status, reponse.read()
    except urllib.error.HTTPError as exc:
        statut, corps = exc.code, exc.read()
    except (OSError, http.client.HTTPException) as exc:
        # Service mort après s'être dit prêt (URLError, connexion coupée, réponse
        # tronquée) ou délai de DELAI_REQUETE_S dépassé (TimeoutError) : la cause se dit.
        raise RuntimeError(
            f"GET {url} sans réponse ({type(exc).__name__} : {exc}) ; "
            f"fin de stderr : {_fin(stderr)}"
        ) from exc
    if statut != HTTPStatus.OK:
        raise RuntimeError(
            f"GET {url} a rendu {statut} : {corps.decode('utf-8', errors='replace')}"
        )


def analyseur() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lance le service de sim/, puis le jeu.")
    parser.add_argument("--port", type=int, default=DEFAULT_SERVICE_PORT)
    parser.add_argument("--cellule", type=_cellule)
    parser.add_argument("--carte", action="store_true", help="ouvre le jeu sur la carte de 1400")
    return parser


def main(argv: list[str]) -> int:
    parser = analyseur()
    avant, commande = (argv[: argv.index("--")], argv[argv.index("--") + 1:]) if "--" in argv else (argv, [])
    args = parser.parse_args(avant)
    if not commande:
        parser.error("commande du jeu absente : attendu « -- <commande du jeu…> »")

    cellule = args.cellule
    print(AUCUNE_CELLULE if cellule is None else f"cellule {cellule}", flush=True)

    if not Path(commande[0]).exists() and shutil.which(commande[0]) is None:
        print(
            f"jeu introuvable : {commande[0]}\n"
            "Le build nocturne le dépose dans builds\\dernier\\ ; "
            "pc\\Ouvrir_Unity.cmd ouvre le projet en attendant.",
            file=sys.stderr,
        )
        return 1
    if _repond(args.port):
        print(
            f"quelque chose répond déjà sur {SERVICE_HOST}:{args.port} : "
            "le jeu lirait un autre monde que le nôtre ; fermez-le ou choisissez --port.",
            file=sys.stderr,
        )
        return 1

    try:
        vue, vitesse = _vitesse(args.carte, cellule)
    except RuntimeError as exc:
        print(f"le jeu n'est pas lancé : {exc}", file=sys.stderr)
        return 1
    print(f"vitesse de la {vue} : {vitesse} jours par seconde", flush=True)

    attendue = f"service prêt sur {SERVICE_HOST}:{args.port}"
    stderr: collections.deque = collections.deque(maxlen=LIGNES_STDERR_GARDEES)
    service = subprocess.Popen(
        [sys.executable, "-m", "sim.service", "--port", str(args.port),
         "--jours-par-seconde", repr(vitesse)],
        cwd=JEU_PY,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=os.environ | {"PYTHONIOENCODING": "utf-8"},
    )
    try:
        threading.Thread(target=_lire_flux, args=(service.stderr, stderr.append), daemon=True).start()
        try:
            _attendre_pret(service, attendue, stderr)
            print(attendue, flush=True)
            if cellule is not None:
                _verifier_lieu(args.port, cellule, stderr)
                commande += ["-forgeCell", str(cellule)]
        except RuntimeError as exc:
            print(f"le jeu n'est pas lancé : {exc}", file=sys.stderr)
            return 1
        code = subprocess.call(commande + ([ARGUMENT_CARTE] if args.carte else []))
        print(f"jeu fermé (code {code})", flush=True)
        return code
    finally:
        service.terminate()
        try:
            service.wait(timeout=DELAI_ARRET_S)
        except subprocess.TimeoutExpired:
            service.kill()
            service.wait()
        print("service arrêté", flush=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
