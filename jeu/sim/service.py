"""Service HTTP local donnant accès au monde simulé, sans le recopier."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import random
import threading
import time
from urllib.parse import parse_qs, urlsplit

from sim.constants import DEFAULT_CLI_SEED
from sim.engine import tick
from sim.model import cellule_vers_dict
from sim.snapshot_export import _round_tree
from sim.world import World


DEFAULT_SERVICE_SEED = DEFAULT_CLI_SEED
DEFAULT_SERVICE_PORT = 8000
DEFAULT_JOURS_PAR_SECONDE = 1.0
BUDGET_TICK_MS = 100
MILLISECONDES_PAR_SECONDE = 1000
SERVICE_HOST = "127.0.0.1"

_CHAMPS_ETAT = ("population", "stocks", "hunger_ticks", "food_deficit_kg")


def _serialiser(document: dict) -> bytes:
    """Sérialise un document dans la forme canonique du service."""
    return json.dumps(
        document,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


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


def _lire_vitesse(recue) -> float:
    """Refuse toute vitesse absente, non numérique, infinie ou négative."""
    try:
        valeur = float(recue)
    except (TypeError, ValueError):
        raise ValueError(
            "paramètre jours_par_seconde invalide : "
            f"reçu {recue!r}, attendu un nombre fini ≥ 0"
        )
    if not math.isfinite(valeur) or valeur < 0:
        raise ValueError(
            "paramètre jours_par_seconde invalide : "
            f"reçu {recue!r}, attendu un nombre fini ≥ 0"
        )
    return valeur


def _vitesse_cli(recue: str) -> float:
    """Adapte le même refus explicite à argparse."""
    try:
        return _lire_vitesse(recue)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


@dataclass(frozen=True)
class EtatPublie:
    """Photographie complète qu'aucun écrivain ne modifie après publication."""

    monde: bytes
    lieux: dict[int, bytes]
    plans: dict[int, bytes]
    tick: int
    date: dict[str, int]
    jours_par_seconde: float
    duree_dernier_tick_ms: float


class ServeurMonde(ThreadingHTTPServer):
    """Serveur portant l'unique monde, son générateur et ses deux verrous."""

    daemon_threads = True

    def __init__(
        self,
        adresse: tuple[str, int],
        seed: int,
        jours_par_seconde: float,
    ):
        super().__init__(adresse, RequetesMonde)
        self.world = World.charger(rng_seed=seed)
        self.rng = random.Random(seed)
        self.verrou_tick = threading.Lock()
        self.condition_vitesse = threading.Condition()
        self._generation_vitesse = 0
        self._arret_horloge = False
        self._tick_en_cours = False
        self.etat_publie = self._construire_etat(jours_par_seconde, -1)
        self._fil_horloge = threading.Thread(
            target=self._faire_avancer_horloge,
            name="horloge-simulation",
            daemon=True,
        )
        self._fil_horloge.start()

    def _construire_etat(
        self,
        jours_par_seconde: float,
        duree_dernier_tick_ms: float,
    ) -> EtatPublie:
        """Construit tous les octets d'une photographie avant sa substitution."""
        cellules = [
            _cellule_legere(self.world.cells[cell_id])
            for cell_id in sorted(self.world.cells)
        ]
        numero_tick = self.world.ticks_ecoules
        date = self.world.date_simulation
        lieux = {
            cellule["cell_id"]: _serialiser(
                cellule | {"tick": numero_tick, "date": date}
            )
            for cellule in cellules
        }
        monde = _serialiser(
            {
                "tick": numero_tick,
                "date": date,
                "cell_count": len(cellules),
                "cells": cellules,
            }
        )
        plans = {
            cell_id: _serialiser(
                plan.to_dict()
                | {"cell_id": cell_id, "rang": 0, "tick": numero_tick, "date": date}
            )
            for cell_id, plan in sorted(self.world.plans.items())
        }
        return EtatPublie(
            monde=monde,
            lieux=lieux,
            plans=plans,
            tick=numero_tick,
            date=date,
            jours_par_seconde=jours_par_seconde,
            duree_dernier_tick_ms=duree_dernier_tick_ms,
        )

    def jouer_un_tick(
        self,
        generation_attendue: int | None = None,
    ) -> EtatPublie | None:
        """Joue puis publie un tick, sans jamais bloquer les lecteurs."""
        with self.verrou_tick:
            with self.condition_vitesse:
                if (
                    generation_attendue is not None
                    and generation_attendue != self._generation_vitesse
                ):
                    return None
                self._tick_en_cours = True
            debut = time.perf_counter()
            try:
                tick(self.world, self.rng, self.world.ticks_ecoules)
                duree_ms = (
                    time.perf_counter() - debut
                ) * MILLISECONDES_PAR_SECONDE
                with self.condition_vitesse:
                    vitesse = self.etat_publie.jours_par_seconde
                    nouvel_etat = self._construire_etat(vitesse, duree_ms)
                    self.etat_publie = nouvel_etat
                return nouvel_etat
            finally:
                with self.condition_vitesse:
                    self._tick_en_cours = False
                    self.condition_vitesse.notify_all()

    def changer_vitesse(self, jours_par_seconde: float) -> EtatPublie:
        """Laisse finir le tick commencé, publie la vitesse et réveille l'horloge."""
        with self.condition_vitesse:
            self.etat_publie = replace(
                self.etat_publie,
                jours_par_seconde=jours_par_seconde,
            )
            self._generation_vitesse += 1
            self.condition_vitesse.notify_all()
            while self._tick_en_cours:
                self.condition_vitesse.wait()
            return self.etat_publie

    def _faire_avancer_horloge(self) -> None:
        """Cadence les ticks sur des échéances absolues, sans rafale de retard."""
        generation = -1
        echeance = time.monotonic()
        while True:
            with self.condition_vitesse:
                while True:
                    if self._arret_horloge:
                        return
                    vitesse = self.etat_publie.jours_par_seconde
                    if generation != self._generation_vitesse:
                        generation = self._generation_vitesse
                        echeance = time.monotonic()
                    if vitesse == 0:
                        self.condition_vitesse.wait()
                        continue
                    attente = echeance - time.monotonic()
                    if attente > 0:
                        self.condition_vitesse.wait(timeout=attente)
                        continue
                    break

            etat = self.jouer_un_tick(generation_attendue=generation)
            if etat is None:
                continue

            with self.condition_vitesse:
                if generation != self._generation_vitesse:
                    continue
                intervalle = 1 / vitesse
                prochaine = echeance + intervalle
                maintenant = time.monotonic()
                echeance = prochaine if prochaine > maintenant else maintenant + intervalle

    def server_close(self) -> None:
        """Réveille le fil démon afin qu'il puisse finir proprement."""
        with self.condition_vitesse:
            self._arret_horloge = True
            self.condition_vitesse.notify_all()
        super().server_close()


class RequetesMonde(BaseHTTPRequestHandler):
    """Routes JSON du regard local sur la simulation."""

    server: ServeurMonde

    def log_message(self, format: str, *args) -> None:
        """Le protocole n'écrit rien sur stdout après sa ligne de disponibilité."""

    def _repondre_octets(self, statut: HTTPStatus, corps: bytes) -> None:
        self.send_response(statut)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def _repondre(self, statut: HTTPStatus, document: dict) -> None:
        self._repondre_octets(statut, _serialiser(document))

    def _refuser(self, statut: HTTPStatus, message: str) -> None:
        self._repondre(statut, {"erreur": message})

    def _document_horloge(self, etat: EtatPublie) -> dict:
        return {
            "tick": etat.tick,
            "date": etat.date,
            "jours_par_seconde": etat.jours_par_seconde,
            "duree_dernier_tick_ms": etat.duree_dernier_tick_ms,
            "budget_tick_ms": BUDGET_TICK_MS,
        }

    def do_GET(self) -> None:
        cible = urlsplit(self.path)
        etat = self.server.etat_publie
        if cible.path in ("/lieu", "/plan"):
            try:
                cell_id = _parametre_entier(cible.query, "cell")
            except ValueError as exc:
                self._refuser(HTTPStatus.BAD_REQUEST, str(exc))
                return
            documents = etat.plans if cible.path == "/plan" else etat.lieux
            lieu = documents.get(cell_id)
            if lieu is None:
                self._refuser(
                    HTTPStatus.NOT_FOUND,
                    f"cell inconnu : reçu {cell_id!r}",
                )
                return
            self._repondre_octets(HTTPStatus.OK, lieu)
            return
        if cible.path == "/monde":
            self._repondre_octets(HTTPStatus.OK, etat.monde)
            return
        if cible.path == "/horloge":
            self._repondre(HTTPStatus.OK, self._document_horloge(etat))
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
            etat = self.server.etat_publie
            for _ in range(nombre):
                etat = self.server.jouer_un_tick()
            self._repondre(
                HTTPStatus.OK,
                {"tick": etat.tick, "date": etat.date},
            )
            return
        if cible.path == "/vitesse":
            valeurs = parse_qs(cible.query, keep_blank_values=True).get(
                "jours_par_seconde"
            )
            recue = None if valeurs is None else valeurs if len(valeurs) != 1 else valeurs[0]
            try:
                vitesse = _lire_vitesse(recue)
            except ValueError as exc:
                self._refuser(HTTPStatus.BAD_REQUEST, str(exc))
                return
            etat = self.server.changer_vitesse(vitesse)
            self._repondre(HTTPStatus.OK, self._document_horloge(etat))
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
            etat = self.server.etat_publie
            self._repondre(
                HTTPStatus.OK,
                {"acceptee": True, "appliquee_au_tick": etat.tick},
            )
            return
        self._refuser(HTTPStatus.NOT_FOUND, f"chemin inconnu : reçu {cible.path!r}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Service local du monde Forge")
    parser.add_argument("--seed", type=int, default=DEFAULT_SERVICE_SEED)
    parser.add_argument("--port", type=int, default=DEFAULT_SERVICE_PORT)
    parser.add_argument(
        "--jours-par-seconde",
        type=_vitesse_cli,
        default=DEFAULT_JOURS_PAR_SECONDE,
    )
    args = parser.parse_args(argv)
    serveur = ServeurMonde(
        (SERVICE_HOST, args.port),
        args.seed,
        args.jours_par_seconde,
    )
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
