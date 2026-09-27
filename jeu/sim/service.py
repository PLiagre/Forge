"""Service HTTP local donnant accès au monde simulé, sans le recopier."""

from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import random
import threading
from urllib.parse import parse_qs, urlsplit

from sim.constants import DEFAULT_CLI_SEED
from sim.engine import tick
from sim.model import cellule_vers_dict
from sim.snapshot_export import _round_tree
from sim.world import World


DEFAULT_SERVICE_SEED = DEFAULT_CLI_SEED
DEFAULT_SERVICE_PORT = 8000
SERVICE_HOST = "127.0.0.1"

_CHAMPS_ETAT = ("population", "stocks", "hunger_ticks", "food_deficit_kg")


def _cellule_legere(cellule) -> dict:
    """Extrait exactement l'état cellulaire partagé avec la photographie."""
    etat = cellule_vers_dict(cellule)
    return _round_tree(
        {"cell_id": etat["cell_id"]}
        | {champ: etat[champ] for champ in _CHAMPS_ETAT}
    )


def _parametre_entier(requete: str, nom: str, minimum: int | None = None) -> int:
    """Lit un entier obligatoire sans inventer une valeur absente ou invalide."""
    valeurs = parse_qs(requete, keep_blank_values=True).get(nom)
    recue = None if valeurs is None else valeurs if len(valeurs) != 1 else valeurs[0]
    try:
        valeur = int(recue)
    except (TypeError, ValueError):
        raise ValueError(f"paramètre {nom} invalide : reçu {recue!r}, attendu un entier")
    if minimum is not None and valeur < minimum:
        raise ValueError(
            f"paramètre {nom} invalide : reçu {recue!r}, attendu un entier ≥ {minimum}"
        )
    return valeur


class ServeurMonde(ThreadingHTTPServer):
    """Serveur portant l'unique monde, son générateur et leur verrou."""

    def __init__(self, adresse: tuple[str, int], seed: int):
        super().__init__(adresse, RequetesMonde)
        self.world = World.charger(rng_seed=seed)
        self.rng = random.Random(seed)
        self.verrou = threading.Lock()


class RequetesMonde(BaseHTTPRequestHandler):
    """Routes JSON du regard local sur la simulation."""

    server: ServeurMonde

    def log_message(self, format: str, *args) -> None:
        """Le protocole n'écrit rien sur stdout après sa ligne de disponibilité."""

    def _repondre(self, statut: HTTPStatus, document: dict) -> None:
        corps = json.dumps(
            document,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        self.send_response(statut)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def _refuser(self, statut: HTTPStatus, message: str) -> None:
        self._repondre(statut, {"erreur": message})

    def do_GET(self) -> None:
        cible = urlsplit(self.path)
        if cible.path == "/lieu":
            try:
                cell_id = _parametre_entier(cible.query, "cell")
            except ValueError as exc:
                self._refuser(HTTPStatus.BAD_REQUEST, str(exc))
                return
            with self.server.verrou:
                cellule = self.server.world.cells.get(cell_id)
                if cellule is None:
                    self._refuser(
                        HTTPStatus.NOT_FOUND,
                        f"cell inconnu : reçu {cell_id!r}",
                    )
                    return
                document = _cellule_legere(cellule) | {
                    "tick": self.server.world.ticks_ecoules,
                    "date": self.server.world.date_simulation,
                }
            self._repondre(HTTPStatus.OK, document)
            return
        if cible.path == "/monde":
            with self.server.verrou:
                cellules = [
                    _cellule_legere(self.server.world.cells[cell_id])
                    for cell_id in sorted(self.server.world.cells)
                ]
                document = {
                    "tick": self.server.world.ticks_ecoules,
                    "date": self.server.world.date_simulation,
                    "cell_count": len(cellules),
                    "cells": cellules,
                }
            self._repondre(HTTPStatus.OK, document)
            return
        self._refuser(HTTPStatus.NOT_FOUND, f"chemin inconnu : reçu {cible.path!r}")

    def do_POST(self) -> None:
        cible = urlsplit(self.path)
        if cible.path == "/tick":
            try:
                nombre = _parametre_entier(cible.query, "n", minimum=1)
            except ValueError as exc:
                self._refuser(HTTPStatus.BAD_REQUEST, str(exc))
                return
            with self.server.verrou:
                for _ in range(nombre):
                    tick(
                        self.server.world,
                        self.server.rng,
                        self.server.world.ticks_ecoules,
                    )
                document = {
                    "tick": self.server.world.ticks_ecoules,
                    "date": self.server.world.date_simulation,
                }
            self._repondre(HTTPStatus.OK, document)
            return
        if cible.path == "/intention":
            longueur_recue = self.headers.get("Content-Length")
            try:
                longueur = int(longueur_recue)
                if longueur < 0:
                    raise ValueError("longueur négative")
                corps = self.rfile.read(longueur)
                intention = json.loads(corps.decode("utf-8"))
            except (TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
                self._refuser(
                    HTTPStatus.BAD_REQUEST,
                    f"corps d'intention invalide : reçu {longueur_recue!r}",
                )
                return
            if not isinstance(intention, dict):
                self._refuser(
                    HTTPStatus.BAD_REQUEST,
                    f"corps d'intention invalide : reçu {intention!r}, attendu un objet JSON",
                )
                return
            with self.server.verrou:
                document = {
                    "acceptee": True,
                    "appliquee_au_tick": self.server.world.ticks_ecoules,
                }
            self._repondre(HTTPStatus.OK, document)
            return
        self._refuser(HTTPStatus.NOT_FOUND, f"chemin inconnu : reçu {cible.path!r}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Service local du monde Forge")
    parser.add_argument("--seed", type=int, default=DEFAULT_SERVICE_SEED)
    parser.add_argument("--port", type=int, default=DEFAULT_SERVICE_PORT)
    args = parser.parse_args(argv)
    serveur = ServeurMonde((SERVICE_HOST, args.port), args.seed)
    port_reel = serveur.server_address[1]
    print(f"service prêt sur {SERVICE_HOST}:{port_reel}", flush=True)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        serveur.server_close()


if __name__ == "__main__":
    main()
