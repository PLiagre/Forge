"""Usine d'assets visuels locale et déterministe de Forge (zéro API payante).

Seuls les modules sans dépendance tierce (`procedes`, `manifeste`) sont
importés d'emblée ; le traitement d'images (`icones`, `textures`, `controle`)
reste importé à la demande afin que le pilote tourne même sur un Python nu.
"""

from .manifeste import CHEMIN_MANIFESTE, enregistrer_asset, ids_existants, lire_manifeste
from .procedes import PROCEDES, TYPES_ASSETS, Procede, machine_pour, procede_pour

__all__ = [
    "CHEMIN_MANIFESTE",
    "PROCEDES",
    "Procede",
    "TYPES_ASSETS",
    "enregistrer_asset",
    "ids_existants",
    "lire_manifeste",
    "machine_pour",
    "procede_pour",
]
