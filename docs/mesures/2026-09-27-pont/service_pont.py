"""Mesure jetable du pont : la simulation comme service local.

Un seul monde, tenu par ce processus. Unity ne fait que lire un lieu et
déposer une intention. Bibliothèque standard seule, comme sim/.

    py service_pont.py --racine D:/Forge --port 8765
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

parser = argparse.ArgumentParser()
parser.add_argument("--racine", required=True)
parser.add_argument("--port", type=int, default=8765)
parser.add_argument("--seed", type=int, default=0)
args = parser.parse_args()
sys.path.insert(0, args.racine)

from sim.engine import tick  # noqa: E402
from sim.model import cellule_vers_dict  # noqa: E402
from sim.world import World  # noqa: E402

verrou = threading.Lock()
monde = World.charger(args.seed)
rng = random.Random(args.seed)
intentions: list[dict] = []
mesures = {"serveur_lieu_us": [], "serveur_tick_ms": []}


def lieu(cid: int) -> dict:
    cellule = monde.cells[cid]
    brut = monde.carte[cid]
    d = cellule_vers_dict(cellule)
    d["relief"] = brut.get("relief")
    d["tick"] = monde.ticks_ecoules
    d["date"] = monde.date_simulation
    return d


class Requete(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"  # connexion gardée ouverte, comme un vrai client

    def _json(self, obj, code=200):
        corps = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/lieu":
            t = time.perf_counter()
            with verrou:
                d = lieu(int(q["cell"][0]))
            mesures["serveur_lieu_us"].append((time.perf_counter() - t) * 1e6)
            return self._json(d)
        if u.path == "/monde":
            with verrou:
                d = {"tick": monde.ticks_ecoules,
                     "cells": [cellule_vers_dict(c) for c in monde.cells.values()]}
            return self._json(d)
        if u.path == "/mesures":
            return self._json({k: sorted(v) for k, v in mesures.items()} | {"intentions": intentions})
        return self._json({"erreur": "chemin inconnu"}, 404)

    def do_POST(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        longueur = int(self.headers.get("Content-Length", "0") or 0)
        corps = self.rfile.read(longueur) if longueur else b""
        if u.path == "/tick":
            n = int(q.get("n", ["1"])[0])
            t = time.perf_counter()
            with verrou:
                for _ in range(n):
                    tick(monde, rng, monde.ticks_ecoules)
            ms = (time.perf_counter() - t) * 1000
            mesures["serveur_tick_ms"].append(ms)
            return self._json({"tick": monde.ticks_ecoules, "duree_ms": ms})
        if u.path == "/intention":
            with verrou:
                recue = monde.ticks_ecoules
                intentions.append({"recue_au_tick": recue, **json.loads(corps or b"{}")})
            return self._json({"acceptee": True, "appliquee_au_tick": recue + 1})
        return self._json({"erreur": "chemin inconnu"}, 404)

    def log_message(self, *a):
        pass


serveur = ThreadingHTTPServer(("127.0.0.1", args.port), Requete)
print(f"service prêt sur 127.0.0.1:{args.port}, {len(monde.cells)} cellules", flush=True)
serveur.serve_forever()
