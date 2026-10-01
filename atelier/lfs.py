"""Les fichiers LFS d'un lot, lisibles par ses agents.

Le VPS n'a pas git-lfs : dans un chantier, une image du lot n'est que son
pointeur (trois lignes de texte). Le 1er octobre 2026, le relecteur de #270
devait juger une planche Unity qu'il ne pouvait pas ouvrir ; il a demandé au
codeur de la décrire, et le lot s'est bloqué après deux corrections.

Installer git-lfs avec son filtre ne conviendrait pas : chaque `git add` du
pilote rangerait ses images en LFS sans jamais les envoyer. On télécharge
donc le contenu des seuls fichiers du lot, par l'API LFS de GitHub (le dépôt
est public, elle répond sans jeton), dans `.atelier/lfs/` du chantier :
ignoré par git, rien n'entre dans un commit.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Callable
import urllib.request

DOSSIER = Path(".atelier") / "lfs"
_POINTEUR = re.compile(rb"\Aversion https://git-lfs\.github\.com/spec/v1\r?\noid sha256:([0-9a-f]{64})\r?\nsize (\d+)\s*\Z")
# Au-delà, l'objet ne se télécharge pas : un agent ne lit pas un modèle 3D.
TAILLE_MAX = 50 * 1024 * 1024

Telechargeur = Callable[[str, str, int], bytes]


def pointeur(contenu: bytes) -> tuple[str, int] | None:
    """(oid, taille) si `contenu` est un pointeur LFS, sinon None."""
    m = _POINTEUR.match(contenu) if len(contenu) < 300 else None
    return (m.group(1).decode(), int(m.group(2))) if m else None


def telecharger(depot: str, oid: str, taille: int) -> bytes:
    """Le contenu d'un objet LFS de `depot` (« moi/essai »), par l'API batch."""
    demande = json.dumps({"operation": "download", "transfers": ["basic"],
                          "objects": [{"oid": oid, "size": taille}]}).encode()
    entetes = {"Accept": "application/vnd.git-lfs+json", "Content-Type": "application/vnd.git-lfs+json"}
    requete = urllib.request.Request(f"https://github.com/{depot}.git/info/lfs/objects/batch",
                                     data=demande, headers=entetes, method="POST")
    with urllib.request.urlopen(requete, timeout=60) as r:
        objet = json.load(r)["objects"][0]
    if "error" in objet or "download" not in (objet.get("actions") or {}):
        raise RuntimeError(f"objet LFS {oid[:12]} absent du serveur : {objet.get('error')}")
    action = objet["actions"]["download"]
    with urllib.request.urlopen(urllib.request.Request(action["href"], headers=action.get("header") or {}),
                                timeout=120) as r:
        contenu = r.read()
    if len(contenu) != taille:
        raise RuntimeError(f"objet LFS {oid[:12]} : {len(contenu)} octets reçus, {taille} attendus")
    return contenu


def rendre_lisibles(chemin: Path, fichiers: list[str], depot: str, *,
                    telechargeur: Telechargeur = telecharger) -> tuple[list[str], list[str]]:
    """Copie dans `chemin/.atelier/lfs/` le contenu réel de ceux des
    `fichiers` qui ne sont, dans le chantier, que des pointeurs LFS. Rend
    (les fichiers rendus lisibles, ceux qui n'ont pas pu l'être, avec leur
    raison)."""
    lisibles, illisibles = [], []
    for f in fichiers:
        source = Path(chemin) / f
        if not source.is_file():
            continue
        try:
            with source.open("rb") as fd:
                tete = fd.read(300)
        except OSError:
            continue
        p = pointeur(tete)
        if p is None:
            continue
        oid, taille = p
        if taille > TAILLE_MAX:
            illisibles.append(f"{f} ({taille // (1024 * 1024)} Mo, trop gros)")
            continue
        try:
            contenu = telechargeur(depot, oid, taille)
        except Exception as e:  # noqa: BLE001 — un téléchargement manqué se dit, il ne casse pas le tour
            illisibles.append(f"{f} ({str(e)[:120]})")
            continue
        cible = Path(chemin) / DOSSIER / f
        cible.parent.mkdir(parents=True, exist_ok=True)
        cible.write_bytes(contenu)
        lisibles.append(f)
    return lisibles, illisibles
