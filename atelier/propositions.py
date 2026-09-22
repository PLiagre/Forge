"""Propositions ouvertes sur GitHub : lecture seule, optionnelle.

La décision de déposer une carte ne dépend pas du réseau : cette couche
ne fait que lister ce que `gh` renvoie, et se tait quand `gh` est absent.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import shutil
import subprocess
import tomllib
from pathlib import Path


@dataclass(frozen=True)
class PropositionOuverte:
    numero: int
    branche: str
    approuvee: bool


def prefixes_integration(racine: Path) -> tuple[str, ...]:
    with open(racine / "atelier.toml", "rb") as fichier:
        brut = tomllib.load(fichier)
    return tuple(
        str(prefixe)
        for prefixe in brut.get("integration", {}).get("branches", ())
        if str(prefixe)
    )


def lot_sous_prefixe(branche: str, prefixe: str) -> str | None:
    if not branche.startswith(prefixe):
        return None
    slug = branche[len(prefixe) :]
    return slug if slug else None


def ouvertes(racine: Path) -> list[PropositionOuverte]:
    """Les PR ouvertes dont la branche porte un préfixe intégré. Vide si `gh` manque."""
    racine = Path(racine)
    if shutil.which("gh") is None:
        return []
    prefixes = prefixes_integration(racine)
    if not prefixes:
        return []
    try:
        vue = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--state",
                "open",
                "--json",
                "number,headRefName,reviews",
            ],
            cwd=racine,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if vue.returncode != 0 or not vue.stdout.strip():
        return []
    try:
        entrees = json.loads(vue.stdout)
    except json.JSONDecodeError:
        return []
    resultat: list[PropositionOuverte] = []
    for entree in entrees:
        if not isinstance(entree, dict):
            continue
        branche = entree.get("headRefName")
        numero = entree.get("number")
        if not isinstance(branche, str) or not isinstance(numero, int):
            continue
        if not any(branche.startswith(prefixe) for prefixe in prefixes):
            continue
        approuvee = _approuvee(entree.get("reviews") or [])
        resultat.append(PropositionOuverte(numero=numero, branche=branche, approuvee=approuvee))
    return resultat


def _approuvee(reviews: list) -> bool:
    for revue in reviews:
        if isinstance(revue, dict) and revue.get("state") == "APPROVED":
            return True
    return False
