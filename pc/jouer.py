"""Le lanceur du jeu : démarre le service de sim/, puis le jeu sur une cellule.

    py pc\\jouer.py [--port P] [--cellule C] -- <commande du jeu…>

Sans `--cellule`, la cellule est la plus ensoleillée de la carte
(jeu/ville/cellule_du_desert.py). Le service s'arrête quand le jeu se ferme,
qu'il plante, ou que le joueur interrompt le lanceur.
"""
from __future__ import annotations

import argparse
import collections
import http.client
import importlib.util
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

JEU_PY = Path(__file__).resolve().parents[1] / "jeu"
sys.path.insert(0, str(JEU_PY))
from sim.service import DEFAULT_SERVICE_PORT, SERVICE_HOST  # noqa: E402

REGLE = JEU_PY / "ville" / "cellule_du_desert.py"
DELAI_SERVICE_PRET_S = 60
DELAI_ARRET_S = 5
DELAI_CONNEXION_S = 1
DELAI_REQUETE_S = 10
LIGNES_STDERR_GARDEES = 20
FIN_DE_FLUX = None


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


def _attendre_pret(service: subprocess.Popen, attendue: str, stderr: collections.deque) -> None:
    lignes: queue.Queue = queue.Queue()
    threading.Thread(target=_lire_flux, args=(service.stdout, lignes.put), daemon=True).start()
    echeance = time.monotonic() + DELAI_SERVICE_PRET_S
    while True:
        reste = echeance - time.monotonic()
        try:
            ligne = lignes.get(timeout=max(reste, 0))
        except queue.Empty:
            raise RuntimeError(
                f"le service n'a pas dit « {attendue} » en {DELAI_SERVICE_PRET_S} s ; "
                f"fin de stderr : {_fin(stderr)}"
            )
        if ligne == attendue:
            return
        if ligne is FIN_DE_FLUX:
            raise RuntimeError(
                f"le service s'est arrêté (code {service.poll()}) avant d'être prêt ; "
                f"fin de stderr : {_fin(stderr)}"
            )


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
    return parser


def main(argv: list[str]) -> int:
    parser = analyseur()
    avant, commande = (argv[: argv.index("--")], argv[argv.index("--") + 1:]) if "--" in argv else (argv, [])
    args = parser.parse_args(avant)
    if not commande:
        parser.error("commande du jeu absente : attendu « -- <commande du jeu…> »")

    cellule = _regle().charger_et_choisir() if args.cellule is None else args.cellule
    print(f"cellule {cellule}", flush=True)

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

    attendue = f"service prêt sur {SERVICE_HOST}:{args.port}"
    stderr: collections.deque = collections.deque(maxlen=LIGNES_STDERR_GARDEES)
    service = subprocess.Popen(
        [sys.executable, "-m", "sim.service", "--port", str(args.port)],
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
            _verifier_lieu(args.port, cellule, stderr)
        except RuntimeError as exc:
            print(f"le jeu n'est pas lancé : {exc}", file=sys.stderr)
            return 1
        code = subprocess.call(commande + ["-forgeCell", str(cellule)])
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
