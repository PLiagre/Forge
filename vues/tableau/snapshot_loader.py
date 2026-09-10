"""Lecture et validation d'un snapshot v0a-3. Aucun recalcul métier."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sim.constants import MARCHANDISE_NOURRITURE, SNAPSHOT_SCHEMA_VERSION
from vues.tableau.classify import ABSENT, NON_CALCULE, ZERO, VALEUR, classify

# Nombre de barres de l'histogramme : un paramètre d'affichage, pas une cible.
N_BINS_HISTOGRAMME = 8


class SnapshotLoadError(RuntimeError):
    """Fichier absent ou schéma inconnu."""


class EchantillonVide(ValueError):
    """Aucune cellule à lire : un échantillon vide échoue."""


def proposed_layers(document: dict[str, Any]) -> list[str]:
    """Couches proposées : population puis chaque clé de panier du document."""
    commodities: set[str] = set()
    for cell in document.get("cells") or []:
        stocks = cell.get("stocks")
        if isinstance(stocks, dict):
            commodities.update(stocks.keys())
    return ["population", *sorted(commodities)]


def _cellules(document: dict[str, Any]) -> list[dict[str, Any]]:
    cellules = document.get("cells")
    if not isinstance(cellules, list) or len(cellules) == 0:
        raise EchantillonVide("échantillon vide : aucune cellule à agréger")
    return cellules


def _champ_document(document: dict[str, Any], cle: str) -> dict[str, Any]:
    if cle not in document:
        return {"etat": "absent"}
    valeur = document[cle]
    etat = classify(valeur)
    if etat == ABSENT:
        return {"etat": "absent"}
    if etat == NON_CALCULE:
        return {"etat": "non_calcule"}
    return {"etat": "mesure", "valeur": valeur}


def _valeur_couche(cell: dict[str, Any], couche: str) -> Any:
    if couche == "population":
        return cell["population"] if "population" in cell else None
    stocks = cell.get("stocks")
    if not isinstance(stocks, dict) or couche not in stocks:
        return None
    return stocks[couche]


def _mesures(valeurs: list[Any]) -> list[float]:
    nombres: list[float] = []
    for valeur in valeurs:
        etat = classify(valeur)
        if etat in (ZERO, VALEUR):
            nombres.append(float(valeur))
    return nombres


def agregats_monde(document: dict[str, Any]) -> dict[str, Any]:
    """Totaux du bandeau : sommes des cellules déjà photographiées."""
    cellules = _cellules(document)

    pop_somme = 0
    n_pop = 0
    for cell in cellules:
        if "population" not in cell:
            continue
        etat = classify(cell["population"])
        if etat in (ABSENT, NON_CALCULE):
            continue
        pop_somme += int(cell["population"])
        n_pop += 1
    population: dict[str, Any]
    if n_pop == 0:
        population = {"etat": "absent"}
    else:
        population = {"etat": "mesure", "valeur": pop_somme, "cellules_lues": n_pop}

    n_faim = 0
    n_hunger = 0
    for cell in cellules:
        if "hunger_ticks" not in cell:
            continue
        etat = classify(cell["hunger_ticks"])
        if etat in (ABSENT, NON_CALCULE):
            continue
        n_hunger += 1
        if cell["hunger_ticks"] > 0:
            n_faim += 1
    affamees: dict[str, Any]
    if n_hunger == 0:
        affamees = {"etat": "absent"}
    else:
        affamees = {"etat": "mesure", "valeur": n_faim, "cellules_lues": n_hunger}

    stock_somme = 0.0
    n_stock = 0
    for cell in cellules:
        stocks = cell.get("stocks")
        if not isinstance(stocks, dict) or MARCHANDISE_NOURRITURE not in stocks:
            continue
        etat = classify(stocks[MARCHANDISE_NOURRITURE])
        if etat in (ABSENT, NON_CALCULE):
            continue
        stock_somme += float(stocks[MARCHANDISE_NOURRITURE])
        n_stock += 1
    stock: dict[str, Any]
    if n_stock == 0:
        stock = {"etat": "absent"}
    else:
        stock = {"etat": "mesure", "valeur": stock_somme, "cellules_lues": n_stock}

    return {
        "cellules": {"etat": "mesure", "valeur": len(cellules)},
        "cellules_affamees": affamees,
        "jour_de_tick": _champ_document(document, "jour_de_tick"),
        "kg_transportes": _champ_document(document, "kg_transportes"),
        "population": population,
        "seed": _champ_document(document, "seed"),
        "stock_nourriture_kg": stock,
        "tick": _champ_document(document, "tick"),
    }


def _histogramme(nombres: list[float]) -> dict[str, Any]:
    if not nombres:
        return {"etat": "absent"}
    vmin = min(nombres)
    vmax = max(nombres)
    if vmin == vmax:
        return {
            "etat": "mesure",
            "bornes": [vmin, vmax],
            "effectifs": [len(nombres)],
        }
    n_bins = N_BINS_HISTOGRAMME
    effectifs = [0] * n_bins
    largeur = vmax - vmin
    for valeur in nombres:
        indice = int((valeur - vmin) / largeur * n_bins)
        if indice == n_bins:
            indice = n_bins - 1
        effectifs[indice] += 1
    bornes = [vmin + largeur * i / n_bins for i in range(n_bins + 1)]
    return {"etat": "mesure", "bornes": bornes, "effectifs": effectifs}


def agregats_couche(document: dict[str, Any], couche: str) -> dict[str, Any]:
    """Min, max, histogramme et totaux de province de la couche active."""
    cellules = _cellules(document)
    valeurs = [_valeur_couche(cell, couche) for cell in cellules]
    nombres = _mesures(valeurs)
    histogramme = _histogramme(nombres)

    n_absents = sum(1 for valeur in valeurs if classify(valeur) == ABSENT)
    n_non_calcules = sum(1 for valeur in valeurs if classify(valeur) == NON_CALCULE)
    n_zeros = sum(1 for valeur in valeurs if classify(valeur) == ZERO)
    n_valeurs = sum(1 for valeur in valeurs if classify(valeur) == VALEUR)

    par_province: dict[str, dict[str, Any]] = {}
    n_sans_province = 0
    for cell, valeur in zip(cellules, valeurs):
        province = cell.get("province")
        if not isinstance(province, dict) or not province.get("name"):
            n_sans_province += 1
            continue
        nom = str(province["name"])
        ligne = par_province.setdefault(nom, {"nom": nom, "somme": 0.0, "n": 0})
        if classify(valeur) in (ZERO, VALEUR):
            ligne["somme"] += float(valeur)
            ligne["n"] += 1
    if not par_province:
        provinces: dict[str, Any] = {"etat": "absent"}
    else:
        lignes = sorted(
            par_province.values(),
            key=lambda item: (-item["somme"], item["nom"]),
        )
        provinces = {"etat": "mesure", "lignes": lignes}

    resultat: dict[str, Any] = {
        "couche": couche,
        "histogramme": histogramme,
        "n_absents": n_absents,
        "n_non_calcules": n_non_calcules,
        "n_sans_province": n_sans_province,
        "n_valeurs": n_valeurs,
        "n_zeros": n_zeros,
        "provinces": provinces,
    }
    if nombres:
        resultat["min"] = {"etat": "mesure", "valeur": min(nombres)}
        resultat["max"] = {"etat": "mesure", "valeur": max(nombres)}
    else:
        resultat["min"] = {"etat": "absent"}
        resultat["max"] = {"etat": "absent"}
    return resultat


def construire_dashboard(document: dict[str, Any]) -> dict[str, Any]:
    """Vue dérivée du snapshot, pour le bandeau et le panneau de couche."""
    couches = {
        couche: agregats_couche(document, couche) for couche in proposed_layers(document)
    }
    return {"couches": couches, "monde": agregats_monde(document)}


def serialize_dashboard(payload: dict[str, Any]) -> bytes:
    texte = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    )
    return (texte + "\n").encode("utf-8")


def load_snapshot(path: Path) -> dict[str, Any]:
    destination = Path(path)
    if not destination.is_file():
        raise SnapshotLoadError(f"snapshot absent: {destination}")
    try:
        document = json.loads(destination.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SnapshotLoadError(f"snapshot illisible: {destination}") from exc
    version = document.get("schema_version")
    if version != SNAPSHOT_SCHEMA_VERSION:
        raise SnapshotLoadError(
            f"schema_version inconnu: {version} (attendu: {SNAPSHOT_SCHEMA_VERSION})"
        )
    if "cells" not in document:
        raise SnapshotLoadError("cells absentes")
    return document
