"""Le registre des assets visuels produits par l'usine (`assets/manifeste.json`).

Sert deux rôles :
1. éviter au pilote d'ouvrir deux fois la même demande d'asset (déduplication) ;
2. dire à `controle.py` ce que la CI doit vérifier pour chaque asset livré.
"""

from __future__ import annotations

import json
from pathlib import Path

from .procedes import procede_pour

CHEMIN_MANIFESTE = Path("assets/manifeste.json")


def lire_manifeste(chemin: Path | str) -> dict:
    """Lit le manifeste JSON ; renvoie un manifeste vide s'il n'existe pas encore."""
    chemin = Path(chemin)
    if not chemin.is_file():
        return {"version": 1, "assets": []}
    contenu = json.loads(chemin.read_text(encoding="utf-8"))
    if not isinstance(contenu, dict) or not isinstance(contenu.get("assets"), list):
        raise ValueError(f"manifeste illisible : {chemin}")
    return contenu


def ecrire_manifeste(chemin: Path | str, manifeste: dict) -> Path:
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(manifeste, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return chemin


def ids_existants(chemin: Path | str) -> set[str]:
    """Les identifiants déjà enregistrés dans le manifeste."""
    return {str(a["id"]) for a in lire_manifeste(chemin).get("assets", [])
            if isinstance(a, dict) and a.get("id")}


def enregistrer_asset(chemin: Path | str, *, asset_id: str, type_asset: str, fichiers: list[str],
                      dimensions: str = "", transparent: bool | None = None,
                      raccordable: bool | None = None, lot: int | None = None,
                      demande_par: int | None = None, references_da: list[str] | None = None) -> dict:
    """Ajoute ou met à jour l'entrée d'un asset dans le manifeste."""
    procede = procede_pour(type_asset)
    if not asset_id or not asset_id.strip():
        raise ValueError("asset_id est obligatoire")
    if not fichiers:
        raise ValueError("au moins un fichier est requis pour enregistrer un asset")
    manifeste = lire_manifeste(chemin)
    entree = {
        "id": asset_id.strip(),
        "type": type_asset,
        "fichiers": [f.replace("\\", "/") for f in fichiers],
        "dimensions": dimensions or procede.dimensions_defaut,
        "transparent": procede.transparent if transparent is None else bool(transparent),
        "raccordable": procede.raccordable if raccordable is None else bool(raccordable),
        "references_da": list(references_da or procede.references_da),
    }
    if lot is not None:
        entree["lot"] = int(lot)
    if demande_par is not None:
        entree["demande_par"] = int(demande_par)
    autres = [a for a in manifeste["assets"] if not (isinstance(a, dict) and a.get("id") == entree["id"])]
    autres.append(entree)
    autres.sort(key=lambda a: str(a.get("id", "")))
    manifeste["assets"] = autres
    ecrire_manifeste(chemin, manifeste)
    return entree
