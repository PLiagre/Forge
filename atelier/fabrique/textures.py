"""Textures PBR raccordables et synthèse locale des cartes (zéro API).

À partir d'une seule image d'albedo orthographique produite par `agy`, ce
module corrige le raccord aux bords, mesure la couture résiduelle et calcule
localement les cartes `height`, `normal`, `roughness` et `ao` prêtes pour
Unity URP.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


def erreur_couture(image: Image.Image) -> float:
    """Discontinuité normalisée [0, 1] entre bords opposés (gauche↔droite et
    haut↔bas). Plus elle est proche de 0, plus le raccord en tuiles est discret."""
    arr = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    if arr.shape[0] < 2 or arr.shape[1] < 2:
        return 0.0
    horiz = float(np.mean(np.abs(arr[:, 0, :] - arr[:, -1, :])))
    vert = float(np.mean(np.abs(arr[0, :, :] - arr[-1, :, :])))
    return round(0.5 * (horiz + vert), 6)


def rendre_raccordable(image: Image.Image, *, largeur_fondu: float = 0.22) -> Image.Image:
    """Rend une texture raccordable par décalage d'une demi-période et fondu
    cosinus doux sur les coutures intérieures.

    Le décalage place les anciens bords au centre de l'image ; un masque en
    cosinus élevé les fond dans la texture d'origine, rendant les nouveaux
    bords rigoureusement continus.
    """
    if not (0.05 <= largeur_fondu <= 0.45):
        raise ValueError(f"largeur_fondu hors bornes [0.05, 0.45] : {largeur_fondu}")
    src = np.asarray(image.convert("RGB"), dtype=np.float32)
    h, w, _ = src.shape
    decale = np.roll(np.roll(src, h // 2, axis=0), w // 2, axis=1)

    # Poids 1 près des nouveaux bords (continus dans `decale`), 0 au centre (où
    # se trouvent les anciennes coutures, remplacées par `src` sans couture).
    y = np.linspace(0.0, 1.0, h, endpoint=False, dtype=np.float32)
    x = np.linspace(0.0, 1.0, w, endpoint=False, dtype=np.float32)
    dy = np.minimum(np.abs(y - 0.5), 0.5) * 2.0  # 0 au centre, 1 aux bords
    dx = np.minimum(np.abs(x - 0.5), 0.5) * 2.0
    # Courbe lisse en cosinus centrée sur le seuil de transition.
    fy = np.clip((dy - (0.5 - largeur_fondu)) / (2.0 * largeur_fondu), 0.0, 1.0)
    fx = np.clip((dx - (0.5 - largeur_fondu)) / (2.0 * largeur_fondu), 0.0, 1.0)
    wy = 0.5 - 0.5 * np.cos(np.pi * fy)
    wx = 0.5 - 0.5 * np.cos(np.pi * fx)
    poids = np.maximum(wy[:, None], wx[None, :])[:, :, None]

    # Sur les pixels exactement au bord (0 et -1), poids == 1 : `decale` est déjà périodique.
    fondu = decale * poids + src * (1.0 - poids)
    return Image.fromarray(np.clip(np.round(fondu), 0, 255).astype(np.uint8), mode="RGB")


def _luminance(rgb: np.ndarray) -> np.ndarray:
    return (0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]).astype(np.float32)


def _normal_depuis_hauteur(hauteur: np.ndarray, force: float = 3.0) -> Image.Image:
    """Normal map en espace tangent (convention OpenGL/Unity : Y vers le haut,
    fond plat = RGB(128, 128, 255)) par filtre de Sobel périodique."""
    haut = np.roll(hauteur, 1, axis=0)
    bas = np.roll(hauteur, -1, axis=0)
    gauche = np.roll(hauteur, 1, axis=1)
    droite = np.roll(hauteur, -1, axis=1)
    hg = np.roll(haut, 1, axis=1)
    hd = np.roll(haut, -1, axis=1)
    bg = np.roll(bas, 1, axis=1)
    bd = np.roll(bas, -1, axis=1)

    gx = (hd + 2.0 * droite + bd) - (hg + 2.0 * gauche + bg)
    gy = (bg + 2.0 * bas + bd) - (hg + 2.0 * haut + hd)

    nx = -gx * force
    ny = gy * force
    nz = np.ones_like(hauteur, dtype=np.float32)
    norme = np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-8
    nx, ny, nz = nx / norme, ny / norme, nz / norme
    rgb = np.stack([(nx * 0.5 + 0.5) * 255.0, (ny * 0.5 + 0.5) * 255.0, (nz * 0.5 + 0.5) * 255.0], axis=2)
    return Image.fromarray(np.clip(np.round(rgb), 0, 255).astype(np.uint8), mode="RGB")


def _flou_gris(tableau: np.ndarray, rayon: float) -> np.ndarray:
    im = Image.fromarray(np.clip(np.round(tableau * 255.0), 0, 255).astype(np.uint8), mode="L")
    return np.asarray(im.filter(ImageFilter.GaussianBlur(radius=rayon)), dtype=np.float32) / 255.0


def generer_pbr(albedo_source: Path | str, dossier_sortie: Path | str, *, nom: str,
                taille: int | None = None, raccorder: bool = True, force_normale: float = 3.0,
                rugosite_min: float = 0.42, rugosite_max: float = 0.92) -> dict[str, Path]:
    """Produit le jeu complet de cartes PBR dans `dossier_sortie` :
    `<nom>_albedo.png`, `<nom>_height.png`, `<nom>_normal.png`,
    `<nom>_roughness.png`, `<nom>_ao.png`."""
    albedo_source, dossier_sortie = Path(albedo_source), Path(dossier_sortie)
    dossier_sortie.mkdir(parents=True, exist_ok=True)
    with Image.open(albedo_source) as im:
        albedo = im.convert("RGB")
        if taille is not None:
            albedo = albedo.resize((taille, taille), Image.Resampling.LANCZOS)
        if raccorder:
            albedo = rendre_raccordable(albedo)

    rgb = np.asarray(albedo, dtype=np.float32) / 255.0
    lum = _luminance(rgb)
    lo, hi = float(np.percentile(lum, 2)), float(np.percentile(lum, 98))
    hauteur = np.clip((lum - lo) / max(hi - lo, 1e-4), 0.0, 1.0)

    # Normal map tangent-space.
    normale = _normal_depuis_hauteur(hauteur, force=force_normale)

    # Roughness : les matériaux médiévaux (pierre, bois, crépi) restent mats ;
    # les zones creuses et granuleuses sont plus rugueuses que les arêtes usées.
    micro = np.abs(hauteur - _flou_gris(hauteur, 2.0))
    brut_rug = 0.7 * (1.0 - hauteur) + 0.3 * np.clip(micro * 4.0, 0.0, 1.0)
    rugosite = rugosite_min + (rugosite_max - rugosite_min) * np.clip(brut_rug, 0.0, 1.0)
    im_rugosite = Image.fromarray(np.clip(np.round(rugosite * 255.0), 0, 255).astype(np.uint8), mode="L")

    # Ambient occlusion : assombrit les cavités locales par rapport à leur voisinage.
    moyen = _flou_gris(hauteur, max(3.0, min(albedo.width, albedo.height) / 64.0))
    cavite = np.clip(moyen - hauteur, 0.0, 1.0)
    ao = np.clip(1.0 - cavite * 1.8, 0.25, 1.0)
    im_ao = Image.fromarray(np.clip(np.round(ao * 255.0), 0, 255).astype(np.uint8), mode="L")
    im_hauteur = Image.fromarray(np.clip(np.round(hauteur * 255.0), 0, 255).astype(np.uint8), mode="L")

    chemins = {
        "albedo": dossier_sortie / f"{nom}_albedo.png",
        "height": dossier_sortie / f"{nom}_height.png",
        "normal": dossier_sortie / f"{nom}_normal.png",
        "roughness": dossier_sortie / f"{nom}_roughness.png",
        "ao": dossier_sortie / f"{nom}_ao.png",
    }
    albedo.save(chemins["albedo"], format="PNG")
    im_hauteur.save(chemins["height"], format="PNG")
    normale.save(chemins["normal"], format="PNG")
    im_rugosite.save(chemins["roughness"], format="PNG")
    im_ao.save(chemins["ao"], format="PNG")
    return chemins
