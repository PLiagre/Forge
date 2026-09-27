"""
Les lectures : ce qu'une carte de statistique peut montrer du monde.

Une **lecture** est une grandeur qu'on lit sur une cellule d'une photographie
de `sim/`, et rien d'autre. Ce module ne calcule aucune mécanique, ne devine
aucune valeur et n'invente aucune couleur : il lit, il normalise, il colorie.

Trois règles portent tout ce fichier :

1. **Une absence n'est pas un zéro** (règle 8). Une cellule dont la
   photographie ne porte pas la grandeur demandée rend `None`, jamais 0.0 —
   et la carte la hachure au lieu de la peindre en clair.
2. **Une lecture que le snapshot ne porte pas se refuse** (règle 10). Elle ne
   se remplace pas par une approximation, et elle ne disparaît pas non plus
   du catalogue : elle est déclarée, et elle échoue en disant pourquoi.
3. **Un dégradé séquentiel est d'une seule teinte, du clair au foncé.** Jamais
   un arc-en-ciel. La grandeur montrée est nommée par le titre, pas par la
   couleur : deux lectures ne se distinguent jamais à la teinte, parce
   qu'aucune carte n'en montre deux à la fois.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Optional, Sequence

import numpy as np


class LectureErreur(RuntimeError):
    """Lecture inconnue, ou grandeur absente de la photographie."""


# --- Le dégradé séquentiel -------------------------------------------------
#
# Une seule teinte, du clair au foncé. Ces sept pas viennent du dégradé
# séquentiel bleu de référence (100 → 700) ; leur clarté OKLab décroît
# strictement de 0,905 à 0,338, soit une amplitude de 0,567 — c'est le seul
# contrôle qui vaille pour un dégradé, et il est rejoué par les tests.
RAMPE = (
    "#cde2fb",
    "#9ec5f4",
    "#6da7ec",
    "#3987e5",
    "#256abf",
    "#184f95",
    "#0d366b",
)

# La mer n'est pas une valeur de la grandeur : c'est l'absence de cellule.
# Neutre, et plus sombre que le pas le plus foncé du dégradé (clarté OKLab
# 0,15 contre 0,338) : mesuré, pas supposé. Un bleu marine — le choix
# évident — se confondait avec le haut du dégradé, qui est bleu foncé lui
# aussi : la terre la plus peuplée devenait indiscernable de la mer.
COULEUR_MER = "#0d0d0d"

# « Non mesuré » : la cellule existe, la grandeur n'y est pas. Gris de chroma
# quasi nulle — il ne peut pas passer pour un pas du dégradé, qui est saturé.
# La hachure diagonale le distingue aussi hors couleur (vision des couleurs,
# impression en niveaux de gris, `forced-colors`).
COULEUR_NON_MESUREE = "#898781"
PAS_DE_HACHURE = 6


def _vers_rgb(hexa: str) -> tuple[int, int, int]:
    h = hexa.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


_RAMPE_RGB = np.array([_vers_rgb(h) for h in RAMPE], dtype=np.float32)


def couleurs_de(t: np.ndarray) -> np.ndarray:
    """
    Interpole le dégradé sur `t` ∈ [0, 1]. Rend un tableau RGB uint8.

    L'interpolation est linéaire entre deux pas voisins : le dégradé porte
    déjà sa progression de clarté, ce n'est pas à l'interpolation de la
    fabriquer.
    """
    t = np.clip(np.asarray(t, dtype=np.float32), 0.0, 1.0)
    dernier = len(_RAMPE_RGB) - 1
    position = t * dernier
    bas = np.floor(position).astype(np.int32)
    bas = np.clip(bas, 0, dernier - 1)
    fraction = (position - bas)[..., None]
    return (
        _RAMPE_RGB[bas] * (1.0 - fraction) + _RAMPE_RGB[bas + 1] * fraction
    ).astype(np.uint8)


# --- Les échelles ----------------------------------------------------------
#
# Une population de cellule s'étale sur plusieurs ordres de grandeur : en
# échelle linéaire, une seule cellule décide de la couleur de toutes les
# autres, et la carte devient uniformément claire. L'échelle est donc un
# choix de LECTURE, déclaré par la lecture elle-même, jamais deviné.

def _echelle_lineaire(v: np.ndarray) -> np.ndarray:
    return v


def _echelle_log(v: np.ndarray) -> np.ndarray:
    return np.log1p(np.maximum(v, 0.0))


def _echelle_quantile(v: np.ndarray) -> np.ndarray:
    """
    Remplace chaque valeur par son RANG parmi les autres.

    Pourquoi une carte de population l'exige. Les valeurs du monde s'étalent
    de 5 à 268 922 habitants, et la plupart des cellules se serrent près du
    haut : en échelle linéaire, presque tout le continent prend le pas le plus
    clair ; en logarithme, presque tout prend le plus foncé. Mesuré sur la
    carte figée : les deux rendent une image d'une seule couleur, où l'on ne
    distingue plus rien.

    Le rang garantit que le dégradé est employé sur toute sa longueur, quelle
    que soit la forme de la distribution. Ce qu'il coûte, dit franchement : la
    couleur ne dit plus « combien », elle dit « à quel rang ». Les bornes
    chiffrées du compte rendu restent la seule source de la magnitude.
    """
    ordre = np.argsort(np.argsort(v, kind="stable"), kind="stable")
    dernier = max(len(v) - 1, 1)
    return ordre.astype(np.float64) / dernier


ECHELLES: dict[str, Callable[[np.ndarray], np.ndarray]] = {
    "lineaire": _echelle_lineaire,
    "log": _echelle_log,
    "quantile": _echelle_quantile,
}


@dataclass(frozen=True)
class Lecture:
    """Une grandeur lisible sur une cellule d'une photographie."""

    cle: str
    titre: str
    unite: str
    echelle: str
    extraire: Callable[[dict], Optional[float]]

    def valeur(self, cellule: dict) -> Optional[float]:
        """La grandeur sur cette cellule, ou None si la photographie ne la porte pas."""
        return self.extraire(cellule)


# --- Les extracteurs -------------------------------------------------------
#
# Chacun rend None quand la photographie ne porte pas la donnée. Aucun ne
# fabrique une valeur de remplacement.

def _population(cellule: dict) -> Optional[float]:
    valeur = cellule.get("population")
    return None if valeur is None else float(valeur)


def _densite(cellule: dict) -> Optional[float]:
    population = cellule.get("population")
    surface = cellule.get("area_km2")
    if population is None or surface is None or float(surface) <= 0.0:
        return None
    return float(population) / float(surface)


def _faim(cellule: dict) -> Optional[float]:
    valeur = cellule.get("hunger_ticks")
    return None if valeur is None else float(valeur)


def _nourriture(cellule: dict) -> Optional[float]:
    stocks = cellule.get("stocks")
    if not isinstance(stocks, dict) or "nourriture" not in stocks:
        return None
    return float(stocks["nourriture"])


def _dette_par_habitant(cellule: dict) -> Optional[float]:
    dette = cellule.get("food_deficit_kg")
    population = cellule.get("population")
    if dette is None or population is None:
        return None
    if float(population) <= 0.0:
        return 0.0
    return float(dette) / float(population)


def _bourg(cellule: dict) -> Optional[float]:
    """
    Part des habitants qui vit du bourg plutôt que des champs.

    Le snapshot ne la porte pas encore : c'est le lot 051. La lecture est
    déclarée quand même — elle deviendra verte le jour où le champ arrivera,
    sans que ce fichier change. En attendant elle refuse, et son refus est
    l'inventaire honnête de ce qui manque.
    """
    bourg = cellule.get("bourg")
    if not isinstance(bourg, dict):
        return None
    du_bourg = bourg.get("habitants_du_bourg")
    des_champs = bourg.get("habitants_des_champs")
    if du_bourg is None or des_champs is None:
        return None
    total = float(du_bourg) + float(des_champs)
    if total <= 0.0:
        return 0.0
    return float(du_bourg) / total


LECTURES: dict[str, Lecture] = {
    lecture.cle: lecture
    for lecture in (
        Lecture("population", "Population", "habitants", "quantile", _population),
        Lecture("densite", "Densité de population", "hab/km²", "quantile", _densite),
        Lecture("nourriture", "Stock de nourriture", "kg", "quantile", _nourriture),
        Lecture("faim", "Ticks de faim consécutifs", "ticks", "lineaire", _faim),
        Lecture("dette", "Dette alimentaire par habitant", "kg/hab", "log", _dette_par_habitant),
        Lecture("bourg", "Part du bourg", "part de 0 à 1", "lineaire", _bourg),
    )
}

LECTURE_PAR_DEFAUT = "population"


def lecture_de(cle: str) -> Lecture:
    """La lecture nommée, ou un refus qui dit lesquelles existent."""
    if cle not in LECTURES:
        connues = ", ".join(sorted(LECTURES))
        raise LectureErreur(f"lecture inconnue {cle!r} — connues : {connues}")
    return LECTURES[cle]


def valeurs_de(cellules: Sequence[dict], lecture: Lecture) -> list[Optional[float]]:
    """La grandeur sur chaque cellule, dans l'ordre. None = non mesurée."""
    return [lecture.valeur(cellule) for cellule in cellules]


def normaliser(
    valeurs: Sequence[Optional[float]], lecture: Lecture
) -> tuple[np.ndarray, np.ndarray, tuple[float, float]]:
    """
    Ramène les valeurs mesurées dans [0, 1] selon l'échelle de la lecture.

    Rend `(t, mesurees, (minimum, maximum))`. `t` vaut 0 là où la mesure est
    absente — cette valeur n'est jamais peinte, `mesurees` dit où regarder.

    Une lecture dont AUCUNE cellule ne porte la grandeur est un échantillon
    vide : elle échoue, elle ne rend pas une carte uniforme (règle 6).
    """
    mesurees = np.array([v is not None for v in valeurs], dtype=bool)
    if not bool(mesurees.any()):
        raise LectureErreur(
            f"« {lecture.titre} » n'est portée par aucune cellule de cette "
            "photographie : échantillon vide, rien à montrer."
        )

    brutes = np.array([0.0 if v is None else float(v) for v in valeurs], dtype=np.float64)
    transformees = ECHELLES[lecture.echelle](brutes)

    retenues = transformees[mesurees]
    minimum = float(retenues.min())
    maximum = float(retenues.max())
    etendue = maximum - minimum

    if etendue <= 0.0:
        # Toutes les cellules portent la même valeur. Ce n'est pas une faute :
        # la carte est uniforme, et elle le dit par ses bornes égales.
        t = np.zeros_like(transformees, dtype=np.float32)
    else:
        t = ((transformees - minimum) / etendue).astype(np.float32)

    bornes_brutes = (
        float(min(v for v in valeurs if v is not None)),
        float(max(v for v in valeurs if v is not None)),
    )
    return t, mesurees, bornes_brutes


def altitudes_de_lecture(t: np.ndarray, relief_max_m: float) -> np.ndarray:
    """
    Change la grandeur normalisée en altitudes lisibles.

    C'est ce qui fait la carte de statistique en **relief** : la grandeur
    devient le terrain. Une cellule deux fois plus peuplée s'élève deux fois
    plus haut, et la couleur dit la même chose que la hauteur — les deux
    canaux portent la même variable, donc aucun ne peut contredire l'autre.
    """
    return (np.clip(t, 0.0, 1.0) * float(relief_max_m)).astype(np.float32)
