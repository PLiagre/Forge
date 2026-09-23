"""Index des skills. Couche outils : des compétences, pas des ordres."""

from __future__ import annotations

from pathlib import Path


SKILLS = (
    "ecrire-un-brief",
    "relire-un-brief",
    "executer-un-lot",
    "relire-un-diff",
    "isoler-un-worktree",
)


def racine_skills() -> Path:
    """Les skills vivent avec la distribution, pas avec le runtime.

    Le runtime est `atelier/` ; ce qui l'accompagne — provenance, profils,
    crons, skills, tests amont — est dans `atelier_meta/`. Chercher
    `skills/` à côté de la racine du produit rendait un chemin qui
    n'existe nulle part, et l'index nommait cinq fichiers absents.
    """
    return Path(__file__).resolve().parent.parent / "atelier_meta" / "skills"


def chemins() -> dict[str, Path]:
    base = racine_skills()
    return {nom: base / nom / "SKILL.md" for nom in SKILLS}
