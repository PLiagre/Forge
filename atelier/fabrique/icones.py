"""Découpe de planches d'icônes et détourage alpha strict (0 / 255).

Permet à un seul appel `generate_image` (grille 3x3 ou 4x4 sur fond uni) de
produire neuf à seize icônes cohérentes, cadrées et prêtes pour Unity, tout en
garantissant un cœur opaque à 255 (jamais de translucidité résiduelle à 254).
"""

from __future__ import annotations

from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image


def _couleur_de_fond(rgba: np.ndarray) -> np.ndarray:
    """Estime la couleur du fond à partir des pixels de bordure (médiane RGB)."""
    h, w, _ = rgba.shape
    bords = np.concatenate([
        rgba[0, :, :3],
        rgba[h - 1, :, :3],
        rgba[:, 0, :3],
        rgba[:, w - 1, :3],
    ], axis=0)
    return np.median(bords, axis=0).astype(np.float32)


def _masque_fond_bords(rgb: np.ndarray, fond: np.ndarray, seuil: float) -> np.ndarray:
    """Remplissage par diffusion depuis le bord : ne mange pas les zones
    intérieures de couleur proche du fond tant qu'elles sont cernées par le sujet."""
    h, w, _ = rgb.shape
    diff = np.linalg.norm(rgb.astype(np.float32) - fond[None, None, :], axis=2)
    candidat = diff <= float(seuil)
    visite = np.zeros((h, w), dtype=bool)
    file: deque[tuple[int, int]] = deque()
    for x in range(w):
        if candidat[0, x]:
            visite[0, x] = True
            file.append((0, x))
        if candidat[h - 1, x] and not visite[h - 1, x]:
            visite[h - 1, x] = True
            file.append((h - 1, x))
    for y in range(h):
        if candidat[y, 0] and not visite[y, 0]:
            visite[y, 0] = True
            file.append((y, 0))
        if candidat[y, w - 1] and not visite[y, w - 1]:
            visite[y, w - 1] = True
            file.append((y, w - 1))
    while file:
        y, x = file.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w and not visite[ny, nx] and candidat[ny, nx]:
                visite[ny, nx] = True
                file.append((ny, nx))
    return visite


def normaliser_alpha(image: Image.Image, *, mode: str = "auto", seuil: float = 28.0) -> Image.Image:
    """Détoure le fond et impose un alpha strict : 0 sur le fond, 255 sur le
    cœur opaque (corrige les fichiers dont le canal alpha plafonne à 254).

    `mode` :
    - `auto` : si l'image a déjà un fond transparent (au moins 5 % de pixels à
      alpha ≤ 10), conserve le détourage existant et durcit son cœur à 255 ;
      sinon retire le fond uni depuis les bords ;
    - `fond` : retire toujours le fond uni depuis les bords ;
    - `aucun` : ne retire pas le fond, durcit seulement les pixels quasi-opaques.
    """
    rgba = np.array(image.convert("RGBA"), dtype=np.uint8)
    alpha = rgba[:, :, 3]
    deja_transparent = float(np.mean(alpha <= 10)) >= 0.05

    if mode == "fond" or (mode == "auto" and not deja_transparent):
        fond = _couleur_de_fond(rgba)
        masque_fond = _masque_fond_bords(rgba[:, :, :3], fond, seuil)
        # Zone de transition douce immédiate au bord du fond pour éviter un crénelage dur.
        diff = np.linalg.norm(rgba[:, :, :3].astype(np.float32) - fond[None, None, :], axis=2)
        nouvel_alpha = np.where(masque_fond, 0, 255).astype(np.uint8)
        # Les pixels collés au fond dont la couleur reste très proche du fond s'adoucissent.
        voisin_fond = np.zeros_like(masque_fond)
        voisin_fond[1:, :] |= masque_fond[:-1, :]
        voisin_fond[:-1, :] |= masque_fond[1:, :]
        voisin_fond[:, 1:] |= masque_fond[:, :-1]
        voisin_fond[:, :-1] |= masque_fond[:, 1:]
        lisiere = (~masque_fond) & voisin_fond & (diff < seuil * 1.6)
        if np.any(lisiere):
            ratio = np.clip((diff[lisiere] - seuil) / max(seuil * 0.6, 1.0), 0.0, 1.0)
            nouvel_alpha[lisiere] = np.round(ratio * 255).astype(np.uint8)
        rgba[:, :, 3] = nouvel_alpha
        rgba[nouvel_alpha == 0, :3] = 0
    else:
        # Durcit le cœur opaque (corrige les alpha 245..254) et nettoie le bruit alpha ≤ 8.
        nouvel_alpha = alpha.copy()
        nouvel_alpha[nouvel_alpha <= 8] = 0
        nouvel_alpha[nouvel_alpha >= 240] = 255
        rgba[:, :, 3] = nouvel_alpha
        rgba[nouvel_alpha == 0, :3] = 0

    return Image.fromarray(rgba, mode="RGBA")


def recadrer_carre(image: Image.Image, taille: int, *, marge: float = 0.08) -> Image.Image:
    """Recadre au plus près du sujet opaque, puis le centre dans un carré
    `taille × taille` avec une marge proportionnelle uniforme."""
    if taille < 16:
        raise ValueError(f"taille d'icône trop petite : {taille}")
    if not (0.0 <= marge < 0.45):
        raise ValueError(f"marge hors bornes [0, 0.45[ : {marge}")
    rgba = image.convert("RGBA")
    boite = rgba.getbbox()
    if boite is None:
        raise ValueError("image vide après détourage : aucun pixel opaque")
    sujet = rgba.crop(boite)
    utile = max(1, int(round(taille * (1.0 - 2.0 * marge))))
    echelle = min(utile / sujet.width, utile / sujet.height)
    nw = max(1, int(round(sujet.width * echelle)))
    nh = max(1, int(round(sujet.height * echelle)))
    redim = sujet.resize((nw, nh), Image.Resampling.LANCZOS)
    toile = Image.new("RGBA", (taille, taille), (0, 0, 0, 0))
    toile.paste(redim, ((taille - nw) // 2, (taille - nh) // 2), redim)
    # Après rééchantillonnage Lanczos, on rétablit la netteté des pixels pleins.
    arr = np.array(toile, dtype=np.uint8)
    arr[arr[:, :, 3] >= 250, 3] = 255
    arr[arr[:, :, 3] <= 4, 3] = 0
    arr[arr[:, :, 3] == 0, :3] = 0
    return Image.fromarray(arr, mode="RGBA")


def detourer_fichier(entree: Path | str, sortie: Path | str, *, taille: int | None = None,
                     marge: float = 0.08, mode: str = "auto", seuil: float = 28.0) -> Path:
    """Détoure un fichier image et l'écrit en PNG prêt pour Unity."""
    entree, sortie = Path(entree), Path(sortie)
    with Image.open(entree) as im:
        propre = normaliser_alpha(im, mode=mode, seuil=seuil)
    if taille is not None:
        propre = recadrer_carre(propre, taille, marge=marge)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    propre.save(sortie, format="PNG")
    return sortie


def lire_grille(texte: str) -> tuple[int, int]:
    """Lit `3x3` ou `4x2` → `(lignes, colonnes)`."""
    morceaux = texte.lower().replace("×", "x").split("x")
    if len(morceaux) != 2 or not all(m.strip().isdigit() for m in morceaux):
        raise ValueError(f"grille illisible : {texte!r} (attendu : RxC, ex. 3x3)")
    lignes, colonnes = int(morceaux[0]), int(morceaux[1])
    if lignes < 1 or colonnes < 1:
        raise ValueError(f"grille vide : {texte!r}")
    return lignes, colonnes


def decouper_planche(planche: Path | str, dossier_sortie: Path | str, *, grille: tuple[int, int],
                     noms: list[str], taille: int = 128, marge: float = 0.08,
                     rognage_cellule: float = 0.04, mode: str = "auto", seuil: float = 28.0) -> list[Path]:
    """Découpe une planche `lignes × colonnes` en icônes PNG individuelles.

    `rognage_cellule` retire une fine bande sur le pourtour de chaque case
    avant détourage pour éliminer d'éventuels filets de grille générés par le
    modèle d'image.
    """
    lignes, colonnes = grille
    capacite = lignes * colonnes
    if not noms:
        raise ValueError("aucun nom fourni pour découper la planche")
    if len(noms) > capacite:
        raise ValueError(f"{len(noms)} noms pour une grille {lignes}x{colonnes} ({capacite} cases)")
    planche, dossier_sortie = Path(planche), Path(dossier_sortie)
    dossier_sortie.mkdir(parents=True, exist_ok=True)
    sorties: list[Path] = []
    with Image.open(planche) as im:
        rgba = im.convert("RGBA")
        w, h = rgba.size
        cw, ch = w / colonnes, h / lignes
        for indice, nom in enumerate(noms):
            r, c = divmod(indice, colonnes)
            x0, y0 = c * cw, r * ch
            x1, y1 = (c + 1) * cw, (r + 1) * ch
            dx, dy = cw * rognage_cellule, ch * rognage_cellule
            case = rgba.crop((int(round(x0 + dx)), int(round(y0 + dy)),
                              int(round(x1 - dx)), int(round(y1 - dy))))
            propre = normaliser_alpha(case, mode=mode, seuil=seuil)
            icone = recadrer_carre(propre, taille, marge=marge)
            cible = dossier_sortie / (nom if nom.lower().endswith(".png") else f"{nom}.png")
            icone.save(cible, format="PNG")
            sorties.append(cible)
    return sorties
