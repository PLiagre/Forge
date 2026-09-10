"""Porte mécanique : refuse un brief infirme. Ne juge pas le fond."""

from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path


SECTIONS = ("But", "Règle du monde", "Périmètre", "Conditions de succès", "Hors périmètre")

_TITRE = re.compile(r"^#\s+Brief\s+\d+", re.MULTILINE)
_COMMANDE = re.compile(
    r"```(?:bash|sh|shell|text)?\s*\n|`[^`\n]*(?:py|python3|pytest|grep|sim)[^`\n]*`",
    re.IGNORECASE,
)
_FICHIER = re.compile(r"`([^`\n]+\.[A-Za-z0-9]+)`")
_SC = re.compile(r"^#{2,3}\s*SC\s*\d+", re.MULTILINE | re.IGNORECASE)


@dataclass(frozen=True)
class Constat:
    nom: str
    ok: bool
    preuve: str


def _section(texte: str, titre: str) -> str | None:
    motif = re.compile(
        rf"^##\s+{re.escape(titre)}\b(.*?)(?=^##\s+|\Z)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    match = motif.search(texte)
    if not match:
        return None
    corps = match.group(1).strip()
    return corps if corps else None


def inspecter(chemin: Path) -> list[Constat]:
    chemin = Path(chemin)
    constats: list[Constat] = []
    if not chemin.is_file():
        return [Constat("fichier", False, f"introuvable : {chemin}")]

    texte = chemin.read_text(encoding="utf-8")
    constats.append(
        Constat("titre", bool(_TITRE.search(texte)), "un brief commence par `# Brief NNN`")
    )

    for titre in SECTIONS:
        corps = _section(texte, titre)
        constats.append(
            Constat(
                f"section:{titre}",
                corps is not None,
                "présente et non vide" if corps else "absente ou vide",
            )
        )

    perimetre = _section(texte, "Périmètre") or ""
    fichiers = _FICHIER.findall(perimetre)
    constats.append(
        Constat(
            "perimetre_fichiers",
            len(fichiers) > 0,
            f"{len(fichiers)} fichier(s) nommé(s) entre backticks"
            if fichiers
            else "aucun fichier nommé dans le périmètre",
        )
    )

    succes = _section(texte, "Conditions de succès") or ""
    sc = _SC.findall(succes)
    commandes = _COMMANDE.findall(succes)
    # Un SC sans commande observable ne peut pas échouer.
    constats.append(
        Constat(
            "criteres_numerotes",
            len(sc) > 0,
            f"{len(sc)} SC" if sc else "aucune condition SC1…SCn",
        )
    )
    constats.append(
        Constat(
            "criteres_commandes",
            len(commandes) > 0,
            f"{len(commandes)} commande(s) nommée(s)"
            if commandes
            else "aucune commande observable dans les conditions de succès",
        )
    )
    return constats


def passer(chemin: Path) -> bool:
    constats = inspecter(chemin)
    return all(c.ok for c in constats)


def rendre(chemin: Path) -> str:
    constats = inspecter(chemin)
    lignes = []
    for c in constats:
        marque = "PASS" if c.ok else "FAIL"
        lignes.append(f"{marque}  {c.nom} — {c.preuve}")
    return "\n".join(lignes)
