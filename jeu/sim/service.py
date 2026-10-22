"""Service HTTP local donnant accès au monde simulé, sans le recopier."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import random
import sys
import threading
import time
from urllib.parse import parse_qs, urlsplit

from sim.carte_servie import document_carte
from sim import constants as _constantes
from sim.constants import DEFAULT_CLI_SEED
from sim.engine import tick
from sim.foyers import ranger_en_foyers
from sim.logement import logement_de
from sim.ia import jouer_ia, maisons_actives_30j
from sim.intentions import IntentionRefusee, TYPE_TRACER_ROUTE, TYPE_DECOUPER_PARCELLE, TYPE_POSER_BATIMENT, TYPE_FIXER_PART, TYPE_OUVRIR_GRENIER, recevoir_intention
from sim.maisons import charger_maisons
from sim.maisons_servies import (
    MaisonInconnue, MatiereMaisons, document_de_maison, liste_des_maisons, matiere_des_maisons,
)
from sim.noms import noms_depuis_monde
from sim.flux import flux_des_lieux
from sim.model import copier_panier, lire_habitants_par_metier
from sim.puissances import PuissanceInvalide, charger_table
from sim.seigneuries import SeigneurieInconnue, charger_seigneuries, fiche_de_seigneurie
from sim.places import bourgs_et_maitres, places_du_monde
from sim.plan import aire_du_contour
from sim.snapshot_export import SnapshotExportError, _fiche_document, _round_tree, lieux_en_photographie
from sim.world import World
from sim.ville1400 import BaseAbsente, base_de_cellule


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
    # Lire les seuls champs publiés évite de copier les lieux puis de les jeter.
    return _round_tree(
        {"cell_id": cellule.cell_id}
        | {champ: copier_panier(cellule) if champ == "stocks" else getattr(cellule, champ)
           for champ in _CHAMPS_ETAT}
    )


def _foyers_du_lieu(cellule) -> dict | int:
    """Publie, par métier trié, ses personnes et ses foyers ; -1 si non calculés."""
    metiers = lire_habitants_par_metier(cellule)
    if metiers == -1:
        return -1
    return {
        metier: {"personnes": personnes, "foyers": ranger_en_foyers(personnes).nombre}
        for metier, personnes in sorted(metiers.items())
    }


def _bourg_du_lieu(cellule, numero_tick: int) -> dict:
    """Copie le rang 0 et sa faim mesurée, sans déduction ni arrondi."""
    bourgs = [lieu for lieu in cellule.lieux if lieu.rang == 0]
    if len(bourgs) != 1:
        cause = "absent" if not bourgs else "dupliqué"
        raise SnapshotExportError(f"cell_id={cellule.cell_id} : rang 0 {cause}")
    bourg = bourgs[0]
    faim = getattr(bourg, "duree_faim_ticks", None)
    if type(faim) is not int or faim < 0:
        raise SnapshotExportError(
            f"cell_id={cellule.cell_id} : duree_faim_ticks invalide : reçu {faim!r}, "
            "attendu un entier ≥ 0"
        )
    return {"rang": bourg.rang, "population": bourg.population,
            "stocks": copier_panier(bourg), "duree_faim_ticks": faim, "tick": numero_tick}


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
    """Photographie du tick ; plans et maisons se complètent à la première lecture."""

    monde: bytes
    lieux: dict[int, bytes]
    lieux_avec_bourg: dict[int, bytes]
    plans: dict[int, bytes]
    occupations: dict[int, bytes]
    tick: int
    date: dict[str, int]
    jours_par_seconde: float
    duree_dernier_tick_ms: float
    ia: bytes | None
    maisons: MatiereMaisons
    octets_maisons: dict[str | None, bytes]


class ErreurIA(RuntimeError):
    """Refus de l'IA avant le tick, après retrait de ses dépôts."""


class ServeurMonde(ThreadingHTTPServer):
    """Serveur portant l'unique monde, son générateur et ses verrous."""

    daemon_threads = True

    def __init__(
        self,
        adresse: tuple[str, int],
        seed: int,
        jours_par_seconde: float,
        ia: bool = False,
    ):
        super().__init__(adresse, RequetesMonde)
        self.world = World.charger(rng_seed=seed)
        self.rng = random.Random(seed)
        self.ia = ia
        self.releve = []
        self.verrou_tick = threading.Lock()
        self.verrou_carte = threading.Lock()
        self.verrou_base = threading.Lock()
        self.verrou_maisons = threading.Lock()
        self._bases = {}
        self._occupations_base = {}
        self._carte_figee = None
        self._places = None  # (maîtres des bourgs, places des lieux) : relu tant que les maîtres ne changent pas
        self.condition_vitesse = threading.Condition()
        self._generation_vitesse = 0
        self._arret_horloge = False
        self._tick_en_cours = False
        self._signature_noms = lambda: (self.world.maisons, tuple((cid, c.area_km2, tuple((l.rang, l.maitre) for l in c.lieux)) for cid, c in sorted(self.world.cells.items())))
        self._empreinte_noms = self._signature_noms(); self._noms = noms_depuis_monde(self.world)
        self.etat_publie = self._construire_etat(jours_par_seconde, -1)
        self._fil_horloge = threading.Thread(
            target=self._faire_avancer_horloge,
            name="horloge-simulation",
            daemon=True,
        )
        self._fil_horloge.start()

    def carte_figee(self):
        """Publie une seule fois la géométrie et les tables, à la première lecture."""
        if self._carte_figee is None:
            with self.verrou_carte:
                if self._carte_figee is None:
                    table = charger_table()
                    maisons = charger_maisons()
                    seigneuries = charger_seigneuries(table=table)
                    document, vue = document_carte(self.world, table=table, maisons=maisons)
                    self._carte_figee = (_serialiser(document), vue, seigneuries, table, maisons)
        return self._carte_figee

    def octets_plan(self, etat, cell_id):
        """Assemble les octets figés de la base et ceux du plan publié."""
        with self.verrou_base:
            self._preparer_base(cell_id)
            octets = etat.plans[cell_id]
            if not octets.startswith(b'{"base":'):
                octets = self._bases[cell_id] + octets[1:]
                etat.plans[cell_id] = octets
            return octets

    def _preparer_base(self, cell_id):
        """Prépare les deux lectures immuables sous verrou_base, sans doubler le calcul."""
        if cell_id not in self._bases:
            base = base_de_cellule(self.world, cell_id)
            occupation = [dict(rang=i, foyers=m["foyers"]) for i, m in enumerate(base["maisons"])]
            self._bases[cell_id] = b'{"base":' + _serialiser(base) + b','
            self._occupations_base[cell_id] = b'{"base":' + _serialiser(occupation) + b','

    def octets_occupation(self, etat, cell_id):
        """Assemble la base immuable et les comptes copiés à la publication."""
        with self.verrou_base:
            self._preparer_base(cell_id)
            return self._occupations_base[cell_id] + etat.occupations[cell_id][1:]

    def document_departs(self):
        """Lit les fiches actuelles et leur date sous le même verrou que les intentions."""
        _, vue, seigneuries, table, maisons = self.carte_figee()
        with self.verrou_tick:
            return {
                "tick": self.world.ticks_ecoules,
                "date": self.world.date_simulation,
                "departs": [_round_tree(_fiche_document(fiche_de_seigneurie(
                    s.id, self.world, seigneuries, table, maisons, vue=vue,
                ))) for s in sorted(seigneuries, key=lambda s: s.id)],
            }

    def octets_de_maison(self, etat, identifiant=None):
        """Sérialise une fiche ou la liste une fois par état, sans attendre le tick."""
        with self.verrou_maisons:
            if identifiant not in etat.octets_maisons:
                document = (liste_des_maisons(etat.maisons) if identifiant is None
                            else document_de_maison(etat.maisons, identifiant))
                etat.octets_maisons[identifiant] = _serialiser(document)
            return etat.octets_maisons[identifiant]

    def _places_des_lieux(self) -> dict:
        """Les places des lieux (#393), recalculées seulement quand le maître d'un bourg change : c'est
        la seule chose du monde qui les déplace. Une vue, pas un état : la clé dit d'où elles viennent."""
        cle = bourgs_et_maitres(self.world)
        if self._places is None or self._places[0] != cle:
            self._places = (cle, places_du_monde(self.world))
        return self._places[1]

    def _construire_etat(
        self,
        jours_par_seconde: float,
        duree_dernier_tick_ms: float,
    ) -> EtatPublie:
        """Construit tous les octets d'une photographie avant sa substitution."""
        numero_tick = self.world.ticks_ecoules
        bourgs = {cid: _bourg_du_lieu(cellule, numero_tick)
                  for cid, cellule in sorted(self.world.cells.items())}
        cellules = [
            _cellule_legere(self.world.cells[cell_id])
            for cell_id in sorted(self.world.cells)
        ]
        signature = self._signature_noms()
        if signature != self._empreinte_noms: self._noms = noms_depuis_monde(self.world); self._empreinte_noms = signature
        noms = self._noms
        flux = flux_des_lieux(self.world)
        date = self.world.date_simulation
        places = self._places_des_lieux()
        # Les lieux s'ajoutent après l'arrondi, comme dans la photographie, par la même fonction.
        documents_lieux = {
            cellule["cell_id"]: (
                cellule
                | ({"logement": logement} if (logement := logement_de(
                    self.world.cells[cellule["cell_id"]], self.world.plans[cellule["cell_id"]]
                )) is not None else {})
                | {
                    "foyers": _foyers_du_lieu(self.world.cells[cellule["cell_id"]]),
                    "lieux": lieux_en_photographie(
                        cellule["cell_id"], self.world.cells[cellule["cell_id"]],
                        places[cellule["cell_id"]], noms[cellule["cell_id"]], flux[cellule["cell_id"]],
                    ),
                    "noms": noms[cellule["cell_id"]],
                    "tick": numero_tick,
                    "date": date,
                }
            )
            for cellule in cellules
        }
        lieux = {cid: _serialiser(document) for cid, document in documents_lieux.items()}
        # « bourg » est la première clé canonique ; réutiliser le lieu évite de le sérialiser deux fois.
        lieux_avec_bourg = {
            cid: b'{"bourg":' + _serialiser(bourgs[cid]) + b',' + lieux[cid][1:]
            for cid, document in documents_lieux.items()
        }
        document = {
            "tick": numero_tick,
            "date": date,
            "cell_count": len(cellules),
            "cells": cellules,
        }
        if self.world.maison_du_joueur is not None:
            document["maison_du_joueur"] = self.world.maison_du_joueur
        monde = _serialiser(document)
        chantiers = {}
        natures = ("rue", "parcelle", "batiment")
        for cle, observation in self.world.chantiers_du_jour.items():
            cell_id, *categorie, identifiant = cle
            nature = categorie[0] if categorie else "rue"
            chantiers.setdefault(cell_id, []).append(
                {"nature": nature, "identifiant": identifiant, **observation})
        for observations in chantiers.values():
            observations.sort(key=lambda e: (natures.index(e["nature"]), e["identifiant"]))
        plans = {
            cell_id: _serialiser(
                plan.to_dict()
                | {"cell_id": cell_id, "rang": 0, "tick": numero_tick, "date": date}
                | ({"chantiers_du_jour": chantiers[cell_id]} if cell_id in chantiers else {})
            )
            for cell_id, plan in sorted(self.world.plans.items())
        }
        with self.verrou_base:
            plans = {cid: self._bases.get(cid, b"{") + octets[1:] for cid, octets in plans.items()}
        occupations = {}
        for cid, plan in sorted(self.world.plans.items()):
            logement = documents_lieux[cid].get("logement")
            reste = logement["loges"] if logement is not None else 0
            batiments = []
            for b in sorted((b for b in plan.batiments if b.nature == "maison" and not b.en_chantier), key=lambda b: b.identifiant):
                capacite = max(1, int(aire_du_contour(b.emprise) // _constantes.SURFACE_M2_PAR_FOYER_LOGE))
                loges = -1 if reste == -1 else min(capacite, reste)
                batiments.append(dict(identifiant=b.identifiant, capacite=capacite, loges=loges))
                reste = -1 if reste == -1 else reste - loges
            occupations[cid] = _serialiser(dict(cell_id=cid, rang=0, tick=numero_tick, date=date,
                batiments=batiments, logement=logement))
        return EtatPublie(
            monde=monde,
            lieux=lieux,
            lieux_avec_bourg=lieux_avec_bourg,
            plans=plans,
            occupations=occupations,
            maisons=matiere_des_maisons(self.world, noms, places),
            octets_maisons={},
            tick=numero_tick,
            date=date,
            jours_par_seconde=jours_par_seconde,
            duree_dernier_tick_ms=duree_dernier_tick_ms,
            ia=_serialiser({
                "tick": numero_tick, "date": date, "releve": self.releve,
                "maisons_actives_30j": maisons_actives_30j(numero_tick, self.releve),
            }) if self.ia else None,
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
                if self.ia:
                    longueur_file = len(self.world.intentions_en_attente)
                    longueur_releve = len(self.releve)
                    try:
                        jouer_ia(self.world, self.releve)
                    except Exception as exc:
                        del self.world.intentions_en_attente[longueur_file:]
                        del self.releve[longueur_releve:]
                        raise ErreurIA(f"ia : {exc}") from exc
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

            try:
                etat = self.jouer_un_tick(generation_attendue=generation)
            except ErreurIA as exc:
                self.changer_vitesse(0)
                print(str(exc), file=sys.stderr, flush=True)
                continue
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
        if cible.path in ("/maisons", "/maison"):
            identifiant = None
            if cible.path == "/maison":
                valeurs = parse_qs(cible.query, keep_blank_values=True).get("id")
                recue = None if valeurs is None else valeurs if len(valeurs) != 1 else valeurs[0]
                if not isinstance(recue, str) or not recue:
                    self._refuser(HTTPStatus.BAD_REQUEST,
                                  f"paramètre id invalide : reçu {recue!r}, attendu un identifiant de maison")
                    return
                identifiant = recue
            try:
                corps = self.server.octets_de_maison(etat, identifiant)
            except MaisonInconnue:
                self._refuser(HTTPStatus.NOT_FOUND, f"maison inconnue : reçu {identifiant!r}")
                return
            self._repondre_octets(HTTPStatus.OK, corps)
            return
        if cible.path in ("/carte", "/departs"):
            try:
                corps = (self.server.carte_figee()[0] if cible.path == "/carte"
                         else _serialiser(self.server.document_departs()))
            except (ValueError, SnapshotExportError, PuissanceInvalide, SeigneurieInconnue) as exc:
                self._refuser(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
                return
            self._repondre_octets(HTTPStatus.OK, corps)
            return
        if cible.path == "/ia":
            if etat.ia is None:
                self._refuser(HTTPStatus.NOT_FOUND, "ia désactivée : lancer le service avec --ia")
            else:
                self._repondre_octets(HTTPStatus.OK, etat.ia)
            return
        if cible.path in ("/lieu", "/plan", "/occupation"):
            try:
                cell_id = _parametre_entier(cible.query, "cell")
            except ValueError as exc:
                self._refuser(HTTPStatus.BAD_REQUEST, str(exc))
                return
            documents = etat.lieux if cible.path == "/lieu" else etat.plans
            if cible.path == "/lieu":
                bourg = parse_qs(cible.query, keep_blank_values=True).get("bourg")
                if bourg is not None:
                    if bourg != ["1"]:
                        self._refuser(HTTPStatus.BAD_REQUEST,
                                      f"paramètre bourg invalide : reçu {bourg!r}, attendu une seule valeur 1")
                        return
                    documents = etat.lieux_avec_bourg
            lieu = documents.get(cell_id)
            if lieu is None:
                self._refuser(
                    HTTPStatus.NOT_FOUND,
                    f"cell inconnu : reçu {cell_id!r}",
                )
                return
            if cible.path in ("/plan", "/occupation"):
                try:
                    lecture = self.server.octets_plan if cible.path == "/plan" else self.server.octets_occupation
                    lieu = lecture(etat, cell_id)
                except BaseAbsente as exc:
                    self._refuser(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
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
            try:
                for _ in range(nombre):
                    etat = self.server.jouer_un_tick()
            except ErreurIA as exc:
                self._refuser(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
                return
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
            def refuser(statut, raison):
                self._repondre(statut, {"acceptee": False, "erreur": raison})

            longueur_recue = self.headers.get("Content-Length")
            try:
                longueur = int(longueur_recue)
                if longueur < 0:
                    raise ValueError("longueur négative")
                corps = self.rfile.read(longueur)
                intention = json.loads(corps.decode("utf-8"))
            except (TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
                refuser(
                    HTTPStatus.BAD_REQUEST,
                    f"corps d'intention invalide : reçu {longueur_recue!r}",
                )
                return
            if not isinstance(intention, dict):
                refuser(
                    HTTPStatus.BAD_REQUEST,
                    f"corps d'intention invalide : reçu {intention!r}, attendu un objet JSON",
                )
                return
            try:
                with self.server.verrou_tick:
                    if intention.get("type") == TYPE_OUVRIR_GRENIER:
                        joueur = self.server.world.maison_du_joueur
                        if joueur is None:
                            raise IntentionRefusee("départ non appliqué : choisir une terre avant d'ouvrir le grenier")
                        if intention.get("maison") != joueur:
                            raise IntentionRefusee("maison interdite : seule la maison du joueur peut ouvrir son grenier")
                    if intention.get("type") == TYPE_FIXER_PART:
                        joueur = self.server.world.maison_du_joueur
                        if joueur is None:
                            raise IntentionRefusee("départ non appliqué : choisir une terre avant de fixer la part")
                        if intention.get("maison") != joueur:
                            raise IntentionRefusee("maison interdite : seule la maison du joueur peut fixer sa part")
                    if intention.get("type") in (TYPE_TRACER_ROUTE, TYPE_DECOUPER_PARCELLE, TYPE_POSER_BATIMENT):
                        joueur = self.server.world.maison_du_joueur
                        if joueur is None:
                            raise IntentionRefusee("départ non appliqué : choisir une terre avant de bâtir")
                        intention = dict(intention, maison=joueur)
                    recevoir_intention(self.server.world, intention)
                    etat = self.server.etat_publie
            except IntentionRefusee as exc:
                statut = (HTTPStatus.CONFLICT
                          if str(exc).startswith("départ déjà choisi :")
                          else HTTPStatus.BAD_REQUEST)
                refuser(statut, str(exc))
                return
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
    parser.add_argument("--ia", action="store_true")
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
        ia=args.ia,
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
