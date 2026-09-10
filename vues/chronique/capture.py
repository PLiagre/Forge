"""Dérouler la simulation, et découper ce qu'elle photographie.

Une photographie de `sim/` pèse deux mégaoctets, dont 95 % de géométrie
qui ne bougera jamais. Photographier cinquante instants coûterait cent
mégaoctets pour montrer quatre nombres par cellule qui changent.

D'où la découpe, qui est **toute** l'idée de ce module :

    photographie  =  décor  +  image

- le **décor** est ce qui ne bouge pas d'un tick à l'autre : la
  géométrie, le relief, le climat, les gisements, la province. Écrit une
  fois.
- une **image** est ce qui bouge : par cellule, la population, le panier,
  la faim et la dette. Écrite à chaque instant capturé, sous forme de
  colonnes parallèles à l'ordre des cellules du décor.

La découpe n'est pas un résumé : `recomposer(decor, image)` rend la
photographie d'origine, au bit près. C'est ce que le test vérifie, et
c'est ce qui interdit à ce module d'inventer ou de perdre quoi que ce
soit. Une découpe qui perdrait une donnée serait un second modèle du
monde — le mode de défaillance n° 4.

C'est aussi la forme que lira Unity : une géométrie chargée une fois, un
flux d'états par tick. Le format ne change pas avec le moteur de rendu.
"""

from __future__ import annotations

import random
from typing import Any, Callable, Iterable

from sim import constants as _constantes
from sim.engine import tick as _tick
# `_round_tree` est l'arrondi de la photographie. La chronique l'emprunte
# au lieu d'en écrire un second : deux règles d'arrondi qui s'ignorent
# finissent par diverger, et la recomposition ne rendrait plus la
# photographie au bit près — c'est-à-dire qu'elle ne prouverait plus rien.
from sim.snapshot_export import _round_tree, build_snapshot_document
from sim.world import World

# Les champs d'une cellule que le tick fait bouger. Cette liste n'est pas
# une déclaration de confiance : `chronique/tests` la MESURE en jouant des
# ticks et en comparant les cellules avant / après (règle 7, la présence
# n'est pas la fonction). Un champ qui se mettrait à bouger sans être ici
# fait rougir ; un champ inerte listé ici aussi.
CHAMPS_MOBILES: tuple[str, ...] = (
    "food_deficit_kg",
    "hunger_ticks",
    "mortality_remainder",
    "population",
    "stocks",
)

# Version du format de chronique. Elle suit le schéma de la photographie
# dont elle est la découpe : une chronique ne peut pas être plus récente
# que ce qu'elle découpe.
FORMAT_CHRONIQUE = "chronique-1"


class CaptureError(RuntimeError):
    """Refus de capture : demande impossible, jamais un résultat inventé."""


def decouper(photographie: dict) -> tuple[dict, dict]:
    """Rend `(decor, image)` pour une photographie `sim/`.

    Le décor porte les cellules privées de leurs champs mobiles ; l'image
    porte ces champs seuls, en colonnes, dans l'ordre des cellules du
    décor. Rien n'est arrondi, rien n'est agrégé.
    """
    cellules = photographie["cells"]
    decor: dict[str, Any] = {
        cle: valeur for cle, valeur in photographie.items() if cle != "cells"
    }
    decor["format"] = FORMAT_CHRONIQUE
    decor["cellules"] = [
        {cle: valeur for cle, valeur in cellule.items() if cle not in CHAMPS_MOBILES}
        for cellule in cellules
    ]
    decor["champs_mobiles"] = list(CHAMPS_MOBILES)
    image = {
        "tick": photographie["tick"],
        "jour": photographie.get("jour_de_tick"),
        "colonnes": {
            champ: [cellule[champ] for cellule in cellules]
            for champ in CHAMPS_MOBILES
        },
    }
    return decor, image


def recomposer(decor: dict, image: dict) -> dict:
    """Rend la photographie d'origine à partir du décor et d'une image.

    L'inverse exact de `decouper`. C'est cette fonction qui rend la
    découpe vérifiable : si elle ne rend pas la photographie au bit près,
    la chronique a perdu ou inventé quelque chose.
    """
    colonnes = image["colonnes"]
    cellules_decor = decor["cellules"]
    for champ in decor["champs_mobiles"]:
        if len(colonnes[champ]) != len(cellules_decor):
            raise CaptureError(
                f"colonne '{champ}' de longueur {len(colonnes[champ])} "
                f"pour {len(cellules_decor)} cellules"
            )
    cellules = []
    for rang, cellule_decor in enumerate(cellules_decor):
        cellule = dict(cellule_decor)
        for champ in decor["champs_mobiles"]:
            cellule[champ] = colonnes[champ][rang]
        cellules.append(cellule)
    photographie = {
        cle: valeur
        for cle, valeur in decor.items()
        if cle not in ("cellules", "champs_mobiles", "format")
    }
    photographie["cells"] = cellules
    photographie["tick"] = image["tick"]
    if image.get("jour") is not None:
        photographie["jour_de_tick"] = image["jour"]
    return photographie


def _instants(ticks: int, pas: int) -> list[int]:
    """Les ticks capturés : t0, puis tous les `pas`, et toujours le dernier."""
    if ticks < 0:
        raise CaptureError("refus : ticks doit être ≥ 0")
    if pas < 1:
        raise CaptureError("refus : pas doit être ≥ 1")
    instants = list(range(0, ticks + 1, pas))
    if instants[-1] != ticks:
        instants.append(ticks)
    return instants


def _image_du_monde(world: World, numero_tick: int) -> dict:
    """L'image d'un monde en cours, lue sans repasser par la géométrie.

    Les colonnes sont lues sur les cellules dans le même ordre que
    `build_snapshot_document` les écrit — l'ordre du `cell_id` croissant.
    C'est la seule chose que ce module sait de la photographie, et le
    test de recomposition est ce qui l'empêche de dériver.
    """
    from sim.model import cellule_vers_dict

    colonnes: dict[str, list] = {champ: [] for champ in CHAMPS_MOBILES}
    for _identifiant, cellule in sorted(
        world.cells.items(), key=lambda item: int(item[0])
    ):
        canonique = cellule_vers_dict(cellule)
        for champ in CHAMPS_MOBILES:
            valeur = canonique[champ] if champ in canonique else getattr(cellule, champ)
            colonnes[champ].append(_round_tree(valeur))
    image = {"tick": numero_tick, "jour": None, "colonnes": colonnes}
    if hasattr(_constantes, "jour_de_tick"):
        image["jour"] = _constantes.jour_de_tick(numero_tick)
    return image


def capturer(
    ticks: int,
    seed: int,
    pas: int = 1,
    *,
    avancement: Callable[[int, int], None] | None = None,
) -> dict:
    """Déroule `ticks` pas et rend une chronique : un décor, N images.

    Le décor est découpé de la photographie de t0 — c'est-à-dire du
    module d'export de `sim/`, jamais d'une seconde lecture de la carte.
    Les images suivantes sont lues sur le monde en cours ; la
    photographie complète n'est refaite à aucun autre instant, parce
    qu'elle coûte cher et qu'elle ne dirait rien de plus.
    """
    instants = _instants(ticks, pas)
    monde = World.charger(rng_seed=seed)
    decor, premiere = decouper(build_snapshot_document(monde, seed, 0))
    images = [premiere]
    rng = random.Random(seed)
    attendus = set(instants)
    for numero_tick in range(ticks):
        _tick(monde, rng, numero_tick)
        acheve = numero_tick + 1
        if acheve in attendus:
            images.append(_image_du_monde(monde, acheve))
        if avancement is not None:
            avancement(acheve, ticks)
    return {"decor": decor, "images": images, "seed": int(seed), "pas": int(pas)}
