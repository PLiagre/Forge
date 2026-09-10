"""Canal d'échange : git-invisible, lisible par l'agent.

Les deux conditions, ou aucune. Un dossier dans `.gitignore` du dépôt
et filtré par l'agent (`.cursorignore`) a déjà rendu un bundle de
revue illisible (lot 033 de ForgeHistory).
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path


NOM_DOSSIER = "atelier-echange"
FICHIER_PR = "pr.txt"
# Un entier positif, et rien d'autre. On ne concatène pas les chiffres
# d'un texte quelconque : « PR #123 » n'est pas un numéro.
_ENTIER_POSITIF = re.compile(r"^[1-9][0-9]*$")


class EchangeErreur(ValueError):
    pass


def dossier(racine: Path) -> Path:
    return Path(racine) / NOM_DOSSIER


def ouvrir(racine: Path) -> Path:
    cible = dossier(racine)
    cible.mkdir(parents=True, exist_ok=True)
    garde = cible / ".gitignore"
    if not garde.is_file():
        # Un `.gitignore` contenant `*` s'ignore lui-même : le canal
        # ne dépend pas d'une ligne du `.gitignore` du dépôt produit.
        garde.write_text("*\n", encoding="utf-8")
    return cible


def deposer_texte(racine: Path, nom: str, corps: str) -> Path:
    if not corps.strip():
        raise EchangeErreur(f"{nom} est vide")
    cible = ouvrir(racine) / nom
    cible.write_text(corps, encoding="utf-8")
    attendu = hashlib.sha256(corps.encode("utf-8")).hexdigest()
    obtenu = hashlib.sha256(cible.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
    if attendu != obtenu:
        raise EchangeErreur(
            f"copie corrompue pour {nom} : {attendu[:12]} attendu, {obtenu[:12]} relu"
        )
    return cible


def deposer(racine: Path, source: Path, nom: str) -> Path:
    if not source.is_file():
        raise EchangeErreur(f"{nom} introuvable : {source}")
    return deposer_texte(racine, nom, source.read_text(encoding="utf-8"))


def retirer(racine: Path, nom: str) -> None:
    cible = dossier(racine) / nom
    if cible.is_file():
        cible.unlink()


def git_ignore_le_canal(racine: Path) -> bool:
    """Le canal a sa propre garde `*`. Il ne s'appuie pas sur le dépôt."""
    garde = dossier(racine) / ".gitignore"
    return garde.is_file() and "*" in garde.read_text(encoding="utf-8")


def chemin_pr(racine: Path) -> Path:
    return dossier(racine) / FICHIER_PR


def lire_numero_pr(fichier: Path) -> int:
    """Le fichier, après trim, ne porte qu'un entier positif.

    Absent, vide, « PR #123 », « 0 », plusieurs lignes : refus.
    On n'extrait pas les chiffres d'un texte libre.
    """
    cible = Path(fichier)
    if not cible.is_file():
        raise EchangeErreur(f"{FICHIER_PR} est absent : pas de numéro de PR")
    texte = cible.read_text(encoding="utf-8").strip()
    if not texte:
        raise EchangeErreur(f"{FICHIER_PR} est vide : pas de numéro de PR")
    if not _ENTIER_POSITIF.fullmatch(texte):
        apercu = texte.replace("\n", "\\n")
        if len(apercu) > 80:
            apercu = apercu[:77] + "..."
        raise EchangeErreur(
            f"{FICHIER_PR} ne porte pas un entier positif unique (reçu {apercu!r})"
        )
    return int(texte)


def verifier_pr_branche_optionnel(numero: int, branche: str, racine: Path) -> str | None:
    """Si gh répond, la PR doit être sur `branche`. Sinon on se tait.

    La sonde parle à GitHub : elle exige un remote, un binaire `gh`, et
    souvent une authentification. Un échec de sonde n'est pas un défaut
    du lot — on ne bloque pas le tour. Un désaccord *confirmé* l'est.
    Retourne None si la sonde n'a pas tranché, la branche distante si
    elle correspond, et lève si elle diffère.
    """
    if shutil.which("gh") is None:
        return None
    origine = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=racine, text=True, capture_output=True, check=False,
    )
    if origine.returncode != 0 or "github.com" not in origine.stdout:
        return None
    try:
        vue = subprocess.run(
            ["gh", "pr", "view", str(numero), "--json", "headRefName"],
            cwd=racine, text=True, capture_output=True, check=False, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if vue.returncode != 0 or not vue.stdout.strip():
        return None
    try:
        nom = json.loads(vue.stdout).get("headRefName")
    except json.JSONDecodeError:
        return None
    if not isinstance(nom, str) or not nom:
        return None
    if nom != branche:
        raise EchangeErreur(
            f"la PR {numero} est sur la branche {nom}, pas {branche}"
        )
    return nom
