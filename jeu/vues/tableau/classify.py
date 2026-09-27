"""Trois états visuels distincts : zéro mesuré, absent, non calculé."""

from __future__ import annotations

from typing import Any, Optional


ABSENT = "absent"
NON_CALCULE = "non_calcule"
ZERO = "zero"
VALEUR = "valeur"
INCOMPARABLE = "incomparable"


def classify(value: Any) -> str:
    if value is None:
        return ABSENT
    if value == -1 or value == -1.0:
        return NON_CALCULE
    if value == 0 or value == 0.0:
        return ZERO
    return VALEUR


def numeric_or_none(value: Any) -> Optional[float]:
    etat = classify(value)
    if etat in (ABSENT, NON_CALCULE):
        return None
    return float(value)


def diff_status(left: Any, right: Any) -> str:
    if classify(left) in (ABSENT, NON_CALCULE) or classify(right) in (
        ABSENT,
        NON_CALCULE,
    ):
        return INCOMPARABLE
    return VALEUR


def numeric_diff(left: Any, right: Any) -> Optional[float]:
    """Différence B − A seulement si les deux valeurs sont des nombres honnêtes."""
    if diff_status(left, right) == INCOMPARABLE:
        return None
    return float(right) - float(left)
