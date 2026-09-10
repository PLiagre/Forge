"""Quota : un inconnu vaut -1, jamais 0.

Un zéro peut être une vraie mesure (plus rien). La sentinelle d'un
quota non lu est -1. `hop` refuse de choisir si tout le monde est
inconnu : ce n'est pas un constat, c'est une abdication de le tirer
au sort.
"""

from __future__ import annotations

from dataclasses import dataclass


INCONNU = -1


@dataclass(frozen=True)
class Quota:
    agent: str
    restant: int

    @property
    def connu(self) -> bool:
        return self.restant != INCONNU

    @property
    def epuise(self) -> bool:
        return self.connu and self.restant == 0


def hop(quotas: list[Quota]) -> Quota:
    if not quotas:
        raise ValueError("aucun agent à départager — échantillon vide")
    connus = [q for q in quotas if q.connu and not q.epuise]
    if not connus:
        inconnus = [q.agent for q in quotas if not q.connu]
        epuises = [q.agent for q in quotas if q.epuise]
        raise ValueError(
            "aucun quota connu et disponible "
            f"(inconnus={inconnus or '-'}, épuisés={epuises or '-'})"
        )
    return max(connus, key=lambda q: q.restant)
