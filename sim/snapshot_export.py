"""Photographie déterministe du monde déjà simulé (schéma v0a-3).

Ce module ne recalcule aucune mécanique. Il joint ce que porte la carte
figée (géométrie, relief, climat, gisements) à la province dérivée et à
l'état que le moteur fait évoluer.

Une seule entrée géographique, `data/world-1400.json`, déjà
chargée par le monde. Ce module ne lit plus aucun artefact de pipeline.

Honnêteté des couches : `dans_la_carte` dit que la donnée est là ;
`utilisee_par_le_moteur` dit si le tick s'en sert. Aujourd'hui le tick ne
se sert d'aucune des trois — elles sont exportées, pas encore jouées.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Optional

from sim.aggregation import (
    PositionCelluleInconnue,
    agregat_depuis_monde,
    identifiant_de_province_de_cellule,
    nom_de_province_de_cellule,
)
from sim import constants as _constants
from sim.constants import SNAPSHOT_FLOAT_DECIMALS, SNAPSHOT_SCHEMA_VERSION
from sim.model import cellule_vers_dict
from sim.world import CARTE_PATH, CARTE_RELATIVE, World

_HASH_CHUNK_BYTES = 1024 * 1024

# Les trois couches que la carte apporte au-delà de la géométrie.
#
# Leur consommation par le tick n'est PAS déclarée ici : elle est MESURÉE
# (voir `_couche_consommee`). Ce dictionnaire n'était auparavant qu'un
# triplet de booléens écrits à la main, et le test se contentait de figer
# leur valeur courante — il ne vérifiait rien. Un moteur qui aurait cessé de
# lire une couche, ou qui aurait commencé à en lire une, l'aurait dit faux
# sans que rien ne rougisse. C'est le mode de défaillance n° 5 du dépôt :
# un compteur dérive des données, ou il n'existe pas.
_COUCHES = ("relief", "climat", "gisements")

# Assez de ticks pour que production, commerce, consommation et mortalité
# aient tous joué au moins une fois : une couche qui n'agirait qu'au
# deuxième tick serait sinon déclarée inerte à tort.
_TICKS_SONDE_COUCHE = 3

# Valeurs de substitution, choisies pour être franchement différentes de
# tout ce que la carte porte. Elles ne prétendent à aucune vraisemblance :
# une sonde n'est pas une simulation, elle demande « le moteur regarde-t-il
# cette clé ? ».
_SONDE_RELIEF = "haute_montagne"
_SONDE_CLIMAT_FACTEUR = 7.0
_SONDE_GISEMENT = [{"nature": "sonde", "classe": "sonde"}]


class SnapshotExportError(RuntimeError):
    """Refus d'export : donnée manquante, jamais inventée."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_HASH_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _round_float(value: Any) -> Any:
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        return round(value, SNAPSHOT_FLOAT_DECIMALS)
    return value


def _round_tree(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _round_tree(value[key]) for key in value}
    if isinstance(value, list):
        return [_round_tree(item) for item in value]
    return _round_float(value)


def _empreinte_apres_ticks(world: World) -> str:
    """État du monde après quelques ticks, sous forme comparable."""
    import random

    from sim.engine import tick as _tick

    rng = random.Random(0)
    for _ in range(_TICKS_SONDE_COUCHE):
        _tick(world, rng)
    return json.dumps(world.to_dict(), sort_keys=True)


def _alterer(carte_doc: dict, couche: str) -> None:
    """
    Remplace franchement une couche dans une carte EN MÉMOIRE, avant que le
    monde ne soit amorcé. Altérer après le chargement ne prouverait rien
    d'un moteur qui lit la couche au chargement plutôt qu'à chaque tick.
    """
    for enregistrement in carte_doc["cellules"]:
        if couche == "relief":
            enregistrement["relief"] = _SONDE_RELIEF
        elif couche == "climat":
            climat = enregistrement.get("climat")
            if isinstance(climat, dict):
                enregistrement["climat"] = {
                    cle: (valeur * _SONDE_CLIMAT_FACTEUR
                          if isinstance(valeur, (int, float)) and not isinstance(valeur, bool)
                          else valeur)
                    for cle, valeur in climat.items()
                }
        elif couche == "gisements":
            enregistrement["gisements"] = list(_SONDE_GISEMENT)


def _couche_consommee(couche: str) -> bool:
    """
    Le tick joue-t-il cette couche ? Mesuré, jamais déclaré.

    On charge deux mondes identiques, on altère franchement la couche dans
    l'un, on joue le même nombre de ticks avec la même graine, et on compare
    l'état obtenu. S'il diffère, le moteur a lu la couche ; s'il est
    identique au bit près, il ne l'a pas lue.

    C'est la même technique que `sim/tests/test_write_coverage.py` emploie
    pour les constantes : la présence n'est pas la fonction (règle 7). Et
    c'est une référence DÉRIVÉE — la mesure se compare à une autre mesure,
    jamais à un nombre écrit à la main (règle 2).

    Conséquence voulue : le jour où le tick consommera le relief, ce drapeau
    passera à `true` tout seul. Personne n'aura de constante à retourner, et
    personne ne pourra le retourner sans que le moteur ait changé.
    """
    carte = World.lire_carte()
    temoin = World.charger(rng_seed=0, carte_doc=copy.deepcopy(carte))
    _alterer(carte, couche)
    altere = World.charger(rng_seed=0, carte_doc=carte)
    return _empreinte_apres_ticks(temoin) != _empreinte_apres_ticks(altere)


def _couches(carte_meta: dict) -> dict:
    """L'état honnête de chaque couche portée par la carte."""
    return {
        nom: {
            "dans_la_carte": True,
            "utilisee_par_le_moteur": _couche_consommee(nom),
        }
        for nom in _COUCHES
    }


def build_snapshot_document(world: World, seed: int, tick: int) -> dict:
    if not world.carte:
        raise SnapshotExportError(
            "Le monde n'a pas été chargé depuis la carte figée ; "
            "aucune géométrie à photographier."
        )
    try:
        regroupements = agregat_depuis_monde(world)
    except PositionCelluleInconnue as exc:
        raise SnapshotExportError(str(exc)) from exc

    cells_out = []
    for cell_id, cell in sorted(world.cells.items(), key=lambda item: int(item[0])):
        cid = int(cell_id)
        raw = world.carte.get(cid)
        if raw is None or "geometry" not in raw or "centroid" not in raw:
            raise SnapshotExportError(f"geometrie absente de la carte pour cell_id={cid}")
        centroid_src = raw["centroid"]
        try:
            centroid = {
                "lat": centroid_src["lat"],
                "lon": centroid_src["lon"],
                "x_m": centroid_src["x_m"],
                "y_m": centroid_src["y_m"],
            }
        except KeyError as exc:
            raise SnapshotExportError(
                f"centroide G3 incomplet pour cell_id={cid}"
            ) from exc
        province_id = identifiant_de_province_de_cellule(cid, regroupements)
        province_name = nom_de_province_de_cellule(cid, regroupements)
        if province_id is None or province_name is None:
            raise SnapshotExportError(f"province absente pour cell_id={cid}")
        cells_out.append(
            {
                "area_km2": cell.area_km2,
                "cell_id": cid,
                "centroid": centroid,
                "climat": raw.get("climat"),
                "food_deficit_kg": cell.food_deficit_kg,
                "geometry": raw["geometry"],
                "gisements": raw.get("gisements", []),
                "hunger_ticks": cell.hunger_ticks,
                "mortality_remainder": cell.mortality_remainder,
                "population": cell.population,
                "province": {"id": int(province_id), "name": province_name},
                "relief": raw.get("relief"),
                "stocks": cellule_vers_dict(cell)["stocks"],
            }
        )

    document: dict[str, Any] = {
        "cell_count": len(cells_out),
        "cells": cells_out,
        "crs": "EPSG:3035",
        "carte": {
            "path": CARTE_RELATIVE,
            "sha256": _sha256_file(CARTE_PATH),
            "version": world.carte_meta.get("version"),
        },
        "couches": _couches(world.carte_meta),
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "seed": int(seed),
        "tick": int(tick),
    }
    if hasattr(_constants, "jour_de_tick"):
        document["jour_de_tick"] = _constants.jour_de_tick(int(tick))
    return _round_tree(document)


def serialize_snapshot(document: dict) -> bytes:
    payload = json.dumps(
        document,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    )
    return (payload + "\n").encode("utf-8")


def export_snapshot(world: World, seed: int, tick: int, path: Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = serialize_snapshot(build_snapshot_document(world, seed, tick))
    destination.write_bytes(payload)
    return destination
