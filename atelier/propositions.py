"""Propositions ouvertes sur GitHub : lecture seule, optionnelle.

La décision du pilote ne dépend pas du réseau : cette liste entre comme
une donnée. Sans `gh`, ou sans remote GitHub, on se tait au lieu de
faire tomber le tour.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import shutil
import subprocess
from pathlib import Path

from . import projet


@dataclass(frozen=True)
class PropositionOuverte:
    numero: int
    branche: str
    tiers_approuvee: bool


def _gh(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["gh", *args],
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return subprocess.CompletedProcess(["gh", *args], 127, "", "")


def _github_accessible(racine: Path) -> bool:
    if shutil.which("gh") is None:
        return False
    origine = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=racine,
        text=True,
        capture_output=True,
        check=False,
    )
    return origine.returncode == 0 and "github.com" in origine.stdout


def _tiers_a_approuve(reviews: list, auteur: str) -> bool:
    for revue in reviews:
        if revue.get("state") != "APPROVED":
            continue
        login = (revue.get("author") or {}).get("login") or ""
        if login and login != auteur:
            return True
    return False


def lister_ouvertes(racine: Path) -> list[PropositionOuverte] | None:
    """Les PR ouvertes du dépôt, ou None si la sonde n'a pas répondu."""
    racine = Path(racine)
    if not _github_accessible(racine):
        return None
    try:
        produit = projet.charger(racine)
    except projet.ProjetIncomplet:
        return None
    prefixes = tuple(produit.branches_fusionnees)
    if not prefixes:
        return None
    vue = _gh(
        "pr", "list", "--state", "open",
        "--json", "number,headRefName,author,reviews",
        cwd=racine,
    )
    if vue.returncode != 0 or not vue.stdout.strip():
        return None
    try:
        brut = json.loads(vue.stdout)
    except json.JSONDecodeError:
        return None
    resultat: list[PropositionOuverte] = []
    for entree in brut:
        if not isinstance(entree, dict):
            continue
        numero = entree.get("number")
        branche = entree.get("headRefName")
        if not isinstance(numero, int) or not isinstance(branche, str):
            continue
        if not any(branche.startswith(p) for p in prefixes):
            continue
        auteur = ((entree.get("author") or {}).get("login")) or ""
        reviews = entree.get("reviews") or []
        if not isinstance(reviews, list):
            reviews = []
        resultat.append(PropositionOuverte(
            numero=numero,
            branche=branche,
            tiers_approuvee=_tiers_a_approuve(reviews, auteur),
        ))
    return resultat
