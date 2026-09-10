"""Mémoire ADD-only : une leçon s'ajoute, elle ne s'écrase pas."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def dossier(racine: Path) -> Path:
    return Path(racine) / ".atelier" / "memoire"


def ajouter(racine: Path, titre: str, corps: str) -> Path:
    if not titre.strip() or not corps.strip():
        raise ValueError("une leçon vide n'en est pas une")
    cible_dir = dossier(racine)
    cible_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = "".join(c if c.isalnum() or c in "-_" else "-" for c in titre.lower())[:40]
    cible = cible_dir / f"{stamp}-{slug}.md"
    if cible.exists():
        raise FileExistsError(f"la mémoire n'écrase pas : {cible}")
    cible.write_text(f"# {titre.strip()}\n\n{corps.strip()}\n", encoding="utf-8")
    return cible
