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
    return Path(__file__).resolve().parent.parent / "skills"


def chemins() -> dict[str, Path]:
    base = racine_skills()
    return {nom: base / nom / "SKILL.md" for nom in SKILLS}
