"""La cellule par défaut du lanceur : la plus ensoleillée de la carte.

    py ville/cellule_du_desert.py        (depuis jeu/)

La carte ne porte aucune température ; sa seule mesure de chaleur est
`climat.insolation_annuelle_mj_m2`. La règle : la cellule dont l'insolation
annuelle est la plus forte ; à égalité, le plus petit `cell_id`. Le numéro
obtenu n'est écrit nulle part : il se recalcule depuis les données.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

CARTE = Path(__file__).resolve().parents[1] / "data" / "world-1400.json"
CLE_CLIMAT = "climat"
CLE_INSOLATION = "insolation_annuelle_mj_m2"


def choisir(monde: dict) -> int:
    """Rend le `cell_id` de la cellule la plus ensoleillée ; refuse toute absence."""
    cellules = monde.get("cellules")
    if not cellules:
        raise ValueError("la carte ne déclare aucune cellule (clé « cellules » vide ou absente)")
    meilleure = None
    for cellule in cellules:
        cell_id = cellule["cell_id"]
        insolation = (cellule.get(CLE_CLIMAT) or {}).get(CLE_INSOLATION)
        if insolation is None:
            raise ValueError(
                f"cellule {cell_id} : clé {CLE_CLIMAT}.{CLE_INSOLATION} absente"
            )
        cle = (-insolation, cell_id)
        if meilleure is None or cle < meilleure:
            meilleure = cle
    return meilleure[1]


def charger_et_choisir(chemin: Path = CARTE) -> int:
    """Lit la carte puis applique la règle."""
    return choisir(json.loads(Path(chemin).read_text(encoding="utf-8")))


if __name__ == "__main__":
    print(charger_et_choisir())
    sys.exit(0)
