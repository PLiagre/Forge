"""Ce qui est mesuré, ce qui ne l'est pas, et la frontière entre les deux.

Une page de pilotage ment de deux façons. Elle invente une valeur quand
la donnée manque — un zéro qui passe pour une mesure — ou elle affiche
« absent » là où l'API a seulement refusé de répondre. Les deux se
regardent pareil et coûtent la même chose : une décision prise sur un
chiffre qui n'existe pas.

Ce module donne les deux formes qui rendent ces mensonges impossibles à
écrire par accident :

- `Lecture` — ce qu'on a demandé à GitHub, et si la réponse est venue.
  Un refus n'est ni un oui ni un non ; il porte sa raison.
- `Mesure` — une valeur et la taille de l'échantillon qui la porte. Un
  échantillon vide donne `NON_CALCULE`, jamais zéro (règle 8 : un zéro
  peut être une vraie mesure, donc la sentinelle ne peut pas en être un).

Bibliothèque standard seule. Aucun appel réseau : ce module ne sait pas
d'où viennent les nombres qu'on lui donne.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

# La sentinelle de « pas calculé ». Elle n'est pas zéro parce que zéro est
# une mesure possible : zéro lot livré cette semaine est un fait, pas une
# absence de fait (AGENTS.md, règle 8).
NON_CALCULE = -1.0

# Ce que la page écrit quand une lecture n'a pas eu lieu. Un seul mot,
# pour qu'on ne puisse pas le confondre avec « absent » ni avec « présent ».
INCONNU = "inconnu"

JOUR = 86400.0


@dataclass(frozen=True)
class Lecture:
    """Une réponse de GitHub, ou l'aveu qu'elle n'est pas venue.

    `connue` est faux quand l'API a refusé — le jeton n'est pas
    administrateur, la ressource n'existe pas encore, le réseau a lâché.
    Dans ce cas `valeur` ne veut rien dire et `raison` dit pourquoi.
    """

    connue: bool
    valeur: object = None
    raison: str = ""

    @classmethod
    def sue(cls, valeur) -> "Lecture":
        return cls(True, valeur, "")

    @classmethod
    def inconnue(cls, raison: str) -> "Lecture":
        if not raison:
            raise ValueError("un inconnu sans raison n'apprend rien : nommer le refus")
        return cls(False, None, raison)

    def sinon(self, defaut):
        """La valeur si elle est connue, le défaut sinon — jamais l'inverse."""
        return self.valeur if self.connue else defaut


@dataclass(frozen=True)
class Mesure:
    """Une valeur dérivée, et le nombre d'observations qui la portent.

    L'échantillon accompagne la valeur partout : c'est lui qui distingue
    « la traversée médiane est de deux jours » de « la traversée médiane
    est de deux jours, sur un seul lot ».
    """

    valeur: float
    echantillon: int

    @property
    def connue(self) -> bool:
        return self.echantillon > 0

    def __post_init__(self) -> None:
        if self.echantillon < 0:
            raise ValueError("un échantillon négatif n'existe pas")
        if self.echantillon == 0 and self.valeur != NON_CALCULE:
            raise ValueError(
                "un échantillon vide ne porte aucune valeur : employer NON_CALCULE, "
                "jamais un zéro qui passerait pour une mesure"
            )


PAS_ENCORE = Mesure(NON_CALCULE, 0)


def mediane(valeurs) -> Mesure:
    """La médiane d'un échantillon, ou l'aveu qu'il est vide.

    La médiane, pas la moyenne : un lot resté trois semaines en attente
    déplace une moyenne et ne déplace pas une médiane, et c'est la
    durée ordinaire qu'on cherche, pas la pire.
    """
    tries = sorted(float(v) for v in valeurs)
    if not tries:
        return PAS_ENCORE
    milieu = len(tries) // 2
    if len(tries) % 2:
        return Mesure(tries[milieu], len(tries))
    return Mesure((tries[milieu - 1] + tries[milieu]) / 2, len(tries))


def instant(texte) -> datetime | None:
    """Une date GitHub (`2026-09-08T08:29:03Z`) en `datetime`, ou rien.

    Rien, pas maintenant : une date illisible qui deviendrait l'heure
    courante ferait paraître frais tout ce qui est vieux.
    """
    if not texte:
        return None
    try:
        lu = datetime.fromisoformat(str(texte).replace("Z", "+00:00"))
    except ValueError:
        return None
    return lu if lu.tzinfo else lu.replace(tzinfo=timezone.utc)


def duree(secondes: float) -> str:
    """Une durée en français court. `NON_CALCULE` se dit, il ne s'affiche pas."""
    if secondes == NON_CALCULE:
        return INCONNU
    if secondes < 0:
        raise ValueError("une durée négative n'existe pas : les dates sont dans le désordre")
    minutes = secondes / 60
    if minutes < 60:
        return f"{round(minutes)} min"
    heures = minutes / 60
    if heures < 48:
        return f"{round(heures)} h"
    return f"{round(heures / 24)} j"


def depuis(moment: datetime | None, maintenant: datetime) -> str:
    """Depuis combien de temps, en toutes lettres. Sans date : `inconnu`."""
    if moment is None:
        return INCONNU
    return duree(max(0.0, (maintenant - moment).total_seconds()))


def jours(nombre: float) -> timedelta:
    return timedelta(seconds=nombre * JOUR)
