"""Contrôles techniques automatiques des assets visuels livrés.

Principe n° 8 d'AGENTS.md : un contrôle doit pouvoir échouer. Un asset livré
est refusé si un fichier manque, si ses dimensions divergent, si son canal
alpha reste translucide (défaut alpha ≤ 254), si le sujet est vide, si un jeu
PBR est incomplet ou si une texture raccordable montre une couture visible.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from .manifeste import lire_manifeste
from .procedes import TYPES_ASSETS
from .textures import erreur_couture

SEUIL_COUTURE_DEFAUT = 0.08
CARTES_PBR_OBLIGATOIRES = ("albedo", "normal", "roughness", "ao")


@dataclass(frozen=True)
class Defaut:
    asset_id: str
    fichier: str
    raison: str


def _lire_dimensions(texte: str) -> tuple[int, int] | None:
    if not texte:
        return None
    morceaux = texte.lower().replace("×", "x").split("x")
    if len(morceaux) != 2 or not all(m.strip().isdigit() for m in morceaux):
        return None
    return int(morceaux[0]), int(morceaux[1])


def controler_image(chemin: Path, *, asset_id: str, dimensions: tuple[int, int] | None = None,
                    transparent: bool = False, raccordable: bool = False,
                    seuil_couture: float = SEUIL_COUTURE_DEFAUT) -> list[Defaut]:
    """Vérifie une image PNG individuelle contre ses contraintes techniques."""
    defauts: list[Defaut] = []
    nom = chemin.as_posix()
    if not chemin.is_file():
        return [Defaut(asset_id, nom, "fichier introuvable")]
    if chemin.stat().st_size == 0:
        return [Defaut(asset_id, nom, "fichier vide")]
    try:
        with Image.open(chemin) as im:
            im.load()
            w, h = im.size
            if dimensions is not None and (w, h) != dimensions:
                defauts.append(Defaut(asset_id, nom, f"dimensions {w}x{h} au lieu de {dimensions[0]}x{dimensions[1]}"))
            if transparent:
                if "A" not in im.getbands():
                    defauts.append(Defaut(asset_id, nom, "canal alpha absent sur un asset déclaré transparent"))
                else:
                    alpha = np.asarray(im.convert("RGBA"), dtype=np.uint8)[:, :, 3]
                    if int(alpha.min()) > 0:
                        defauts.append(Defaut(asset_id, nom, f"aucun pixel transparent (alpha min = {int(alpha.min())})"))
                    if int(alpha.max()) < 255:
                        defauts.append(Defaut(asset_id, nom,
                                              f"cœur translucide (alpha max = {int(alpha.max())} < 255)"))
                    couverture = float(np.mean(alpha > 16))
                    if couverture < 0.05:
                        defauts.append(Defaut(asset_id, nom, f"sujet quasi vide (couverture {couverture:.1%} < 5 %)"))
                    elif couverture > 0.96:
                        defauts.append(Defaut(asset_id, nom, f"fond non détouré (couverture {couverture:.1%} > 96 %)"))
            if raccordable:
                couture = erreur_couture(im)
                if couture > seuil_couture:
                    defauts.append(Defaut(asset_id, nom,
                                          f"couture visible ({couture:.3f} > {seuil_couture:.3f})"))
    except Exception as e:  # noqa: BLE001
        defauts.append(Defaut(asset_id, nom, f"image illisible : {e}"))
    return defauts


def controler_asset(racine: Path | str, entree: dict, *,
                    seuil_couture: float = SEUIL_COUTURE_DEFAUT) -> list[Defaut]:
    """Vérifie une entrée du manifeste et tous ses fichiers."""
    racine = Path(racine)
    asset_id = str(entree.get("id") or "?")
    type_asset = str(entree.get("type") or "")
    if type_asset not in TYPES_ASSETS:
        return [Defaut(asset_id, "", f"type d'asset inconnu : {type_asset!r}")]
    fichiers = [str(f) for f in entree.get("fichiers") or [] if isinstance(f, str)]
    if not fichiers:
        return [Defaut(asset_id, "", "aucun fichier déclaré")]
    dims = _lire_dimensions(str(entree.get("dimensions") or ""))
    transparent = bool(entree.get("transparent", False))
    raccordable = bool(entree.get("raccordable", False))
    defauts: list[Defaut] = []

    if type_asset == "texture_pbr":
        noms_bas = [Path(f).stem.lower() for f in fichiers]
        manquantes = [c for c in CARTES_PBR_OBLIGATOIRES if not any(n.endswith(f"_{c}") or n == c for n in noms_bas)]
        if manquantes:
            defauts.append(Defaut(asset_id, "", f"cartes PBR manquantes : {', '.join(manquantes)}"))

    tailles_vues: set[tuple[int, int]] = set()
    for rel in fichiers:
        chemin = racine / rel
        if chemin.suffix.lower() not in (".png", ".webp", ".jpg", ".jpeg"):
            if not chemin.is_file() or chemin.stat().st_size == 0:
                defauts.append(Defaut(asset_id, rel, "fichier absent ou vide"))
            continue
        est_albedo = type_asset != "texture_pbr" or Path(rel).stem.lower().endswith("_albedo")
        defauts += controler_image(
            chemin, asset_id=asset_id, dimensions=dims,
            transparent=transparent,
            raccordable=raccordable and est_albedo,
            seuil_couture=seuil_couture,
        )
        if chemin.is_file():
            try:
                with Image.open(chemin) as im:
                    tailles_vues.add(im.size)
            except Exception:  # noqa: BLE001
                pass
    if type_asset == "texture_pbr" and len(tailles_vues) > 1:
        defauts.append(Defaut(asset_id, "", f"cartes PBR de tailles différentes : {sorted(tailles_vues)}"))
    return defauts


def controler_manifeste(racine: Path | str, manifeste_rel: Path | str = "assets/manifeste.json", *,
                        exiger_non_vide: bool = False,
                        seuil_couture: float = SEUIL_COUTURE_DEFAUT) -> list[Defaut]:
    """Vérifie chaque asset du manifeste. Si le manifeste n'existe pas encore
    et `exiger_non_vide=False`, ne signale aucun défaut."""
    racine = Path(racine)
    chemin = Path(manifeste_rel)
    if not chemin.is_absolute():
        chemin = racine / chemin
    if not chemin.is_file():
        return [Defaut("", str(manifeste_rel), "manifeste absent")] if exiger_non_vide else []
    manifeste = lire_manifeste(chemin)
    entrees = manifeste.get("assets") or []
    if exiger_non_vide and not entrees:
        return [Defaut("", str(manifeste_rel), "manifeste vide : aucun asset contrôlé")]
    defauts: list[Defaut] = []
    vus: set[str] = set()
    for entree in entrees:
        if not isinstance(entree, dict):
            defauts.append(Defaut("?", "", "entrée de manifeste mal formée"))
            continue
        aid = str(entree.get("id") or "")
        if aid in vus:
            defauts.append(Defaut(aid, "", "identifiant en double dans le manifeste"))
        vus.add(aid)
        defauts += controler_asset(racine, entree, seuil_couture=seuil_couture)
    return defauts
