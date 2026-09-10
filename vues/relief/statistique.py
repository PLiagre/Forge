"""
La carte de statistique : le monde colorié par une de ses grandeurs.

`raster.py` fait le relief — la géographie. Ce module fait la **statistique** :
il prend une photographie de `sim/`, choisit une lecture, et rend deux images
qui disent la même chose de deux façons.

    plan            vue du dessus, chaque cellule peinte selon sa valeur.
                    Pur numpy et Pillow : aucun GPU, donc vérifiable en CI.

    relief          la grandeur DEVIENT le terrain. Une cellule deux fois plus
                    peuplée s'élève deux fois plus haut, et sa couleur dit la
                    même chose que sa hauteur.

**Pourquoi la grandeur devient le relief, et pas une peinture sur le relief
géographique.** Ce serait plus beau de garder les montagnes et de les colorier
par la population. Le moteur de rendu ne le permet pas dans cette version :
`OverlayLayer` ne sait construire une couche que depuis un dégradé
(`from_colormap1d`), appliqué au champ que le terrain élève — il n'accepte
aucun second tableau de valeurs. Colorier la géographie par une grandeur
indépendante demanderait un canal que forge3d n'expose pas ici. On ne le
simule pas en douce : on élève la grandeur elle-même, ce qui est une carte
statistique honnête, et cette limite est nommée plutôt que contournée.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

from vues.relief.lectures import (
    COULEUR_MER,
    COULEUR_NON_MESUREE,
    PAS_DE_HACHURE,
    Lecture,
    LectureErreur,
    altitudes_de_lecture,
    couleurs_de,
    lecture_de,
    normaliser,
    valeurs_de,
)
from vues.relief.raster import RasterErreur, index_des_cellules

# Altitude de lecture du pic de la grandeur. La valeur n'a aucun sens
# physique : c'est une hauteur d'image, choisie pour que le relief se lise.
ALTITUDE_MAX_LECTURE_M = 2400.0

# Épaisseur de la bande de légende, en pixels, et la place laissée au texte.
BANDE_LEGENDE_PX = 14
HAUTEUR_TEXTE_PX = 15
MARGE_LEGENDE_PX = 6
COULEUR_TEXTE = "#c3c2b7"


def _rgb(hexa: str) -> Tuple[int, int, int]:
    h = hexa.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


@dataclass(frozen=True)
class CarteStatistique:
    """Une grandeur du monde, posée sur la grille des cellules."""

    lecture: Lecture
    t: np.ndarray                 # grandeur normalisée par pixel, [0, 1]
    mesuree: np.ndarray           # la cellule de ce pixel porte-t-elle la grandeur ?
    masque_terre: np.ndarray      # ce pixel est-il une cellule, ou la mer ?
    bornes: Tuple[float, float]   # minimum et maximum bruts, dans l'unité de la lecture
    cellules: int
    cellules_mesurees: int
    tick: int
    seed: int


def carte_de_statistique(
    document: dict, *, lecture: str | Lecture = "population", largeur: int = 512
) -> CarteStatistique:
    """
    Lit une grandeur sur chaque cellule et la pose sur la grille.

    Refuse — plutôt que de deviner — une lecture inconnue, une photographie
    sans cellule, ou une grandeur qu'aucune cellule ne porte.
    """
    lec = lecture if isinstance(lecture, Lecture) else lecture_de(lecture)
    ids, _bounds, cells = index_des_cellules(document, largeur=largeur)

    valeurs = valeurs_de(cells, lec)
    t_par_cellule, mesuree_par_cellule, bornes = normaliser(valeurs, lec)

    # Rang 0 = la mer. On décale d'un cran pour indexer par le rang du pixel.
    t_table = np.concatenate(([0.0], t_par_cellule)).astype(np.float32)
    mesuree_table = np.concatenate(([False], mesuree_par_cellule))

    return CarteStatistique(
        lecture=lec,
        t=np.take(t_table, ids),
        mesuree=np.take(mesuree_table, ids),
        masque_terre=ids > 0,
        bornes=bornes,
        cellules=len(cells),
        cellules_mesurees=int(mesuree_par_cellule.sum()),
        tick=int(document.get("tick", -1)),
        seed=int(document.get("seed", -1)),
    )


def _hachure(forme: Tuple[int, int]) -> np.ndarray:
    """Masque diagonal à 45°, pour dire « non mesuré » sans dépendre de la couleur."""
    hauteur, largeur = forme
    lignes = np.arange(hauteur)[:, None]
    colonnes = np.arange(largeur)[None, :]
    return ((lignes + colonnes) % PAS_DE_HACHURE) < (PAS_DE_HACHURE // 2)


def plan(carte: CarteStatistique) -> np.ndarray:
    """
    Vue du dessus, en RGBA. Aucun GPU : c'est l'image que la CI peut vérifier.

    Trois traitements, et ils ne se confondent jamais :
      - la mer, d'un bleu sombre qui n'appartient pas au dégradé ;
      - une cellule mesurée, peinte au pas du dégradé qui lui revient ;
      - une cellule **non mesurée**, hachurée en gris — parce qu'une absence
        n'est pas un zéro, et qu'un zéro se peindrait au clair du dégradé.
    """
    rgba = np.zeros(carte.t.shape + (4,), dtype=np.uint8)
    rgba[..., 3] = 255

    rgba[..., :3] = couleurs_de(carte.t)

    non_mesuree = carte.masque_terre & ~carte.mesuree
    if bool(non_mesuree.any()):
        gris = np.array(_rgb(COULEUR_NON_MESUREE), dtype=np.uint8)
        hachure = _hachure(carte.t.shape)
        rgba[non_mesuree & hachure, :3] = gris
        rgba[non_mesuree & ~hachure, :3] = (gris * 0.55).astype(np.uint8)

    rgba[~carte.masque_terre, :3] = np.array(_rgb(COULEUR_MER), dtype=np.uint8)
    return rgba


def _sans_accent(texte: str) -> str:
    """
    Retire les diacritiques du texte de la légende, et de lui seul.

    La police par défaut de Pillow est une bitmap ASCII : elle rend « é » par
    un carré vide. Plutôt que d'embarquer une fonte — que le dépôt devrait
    alors versionner, licencier et garder à jour — on écrit la légende sans
    accents. Le titre complet, lui, reste accentué dans le compte rendu JSON,
    qui n'a pas ce problème.
    """
    import unicodedata

    decompose = unicodedata.normalize("NFKD", texte)
    return "".join(c for c in decompose if not unicodedata.combining(c))


def _abreger(valeur: float) -> str:
    """Un nombre lisible sur une légende étroite : 268 922 devient « 269 k »."""
    for seuil, suffixe in ((1e9, "G"), (1e6, "M"), (1e3, "k")):
        if abs(valeur) >= seuil:
            return f"{valeur / seuil:.1f} {suffixe}"
    if abs(valeur) >= 10 or valeur == 0:
        return f"{valeur:.0f}"
    return f"{valeur:.2f}"


def plan_avec_legende(carte: CarteStatistique) -> np.ndarray:
    """
    Le plan, surmonté d'une échelle qui dit ce que les couleurs valent.

    Une carte choroplèthe sans échelle n'est pas une carte : la couleur ne dit
    rien si l'on ignore ce que valent ses bouts. La bande porte le dégradé du
    minimum au maximum, le titre de la lecture et les deux bornes dans son
    unité — l'image se suffit, sans le compte rendu.

    Quand la lecture est classée par rang (échelle `quantile`), la bande le
    dit : la couleur y ordonne, elle ne mesure pas.
    """
    from PIL import Image, ImageDraw

    image = plan(carte)
    _hauteur, largeur = carte.t.shape
    hauteur_bande = MARGE_LEGENDE_PX + HAUTEUR_TEXTE_PX + BANDE_LEGENDE_PX + MARGE_LEGENDE_PX

    bande = np.zeros((hauteur_bande, largeur, 4), dtype=np.uint8)
    bande[..., 3] = 255
    bande[..., :3] = np.array(_rgb(COULEUR_MER), dtype=np.uint8)

    haut_gradient = MARGE_LEGENDE_PX + HAUTEUR_TEXTE_PX
    gradient = np.linspace(0.0, 1.0, largeur, dtype=np.float32)[None, :]
    gradient = np.repeat(gradient, BANDE_LEGENDE_PX, axis=0)
    bande[haut_gradient:haut_gradient + BANDE_LEGENDE_PX, :, :3] = couleurs_de(gradient)

    minimum, maximum = carte.bornes
    rang = " (par rang)" if carte.lecture.echelle == "quantile" else ""
    titre = f"{carte.lecture.titre} ({carte.lecture.unite}){rang}"

    vignette = Image.fromarray(bande, mode="RGBA")
    crayon = ImageDraw.Draw(vignette)
    crayon.text((MARGE_LEGENDE_PX, MARGE_LEGENDE_PX - 1), _sans_accent(titre), fill=COULEUR_TEXTE)
    bas_texte = haut_gradient + BANDE_LEGENDE_PX - HAUTEUR_TEXTE_PX + 2
    bas = _sans_accent(_abreger(minimum))
    haut = _sans_accent(_abreger(maximum))
    # Le bas du dégradé est clair, le haut est foncé : l'encre s'inverse avec eux.
    crayon.text((MARGE_LEGENDE_PX, bas_texte), bas, fill="#0b0b0b")
    crayon.text((largeur - MARGE_LEGENDE_PX - len(haut) * 6, bas_texte), haut, fill="#f2f0ea")

    return np.concatenate([np.array(vignette), image], axis=0)


def altitudes_de(carte: CarteStatistique) -> np.ndarray:
    """La grandeur, changée en terrain. C'est ce que forge3d élève."""
    altitudes = altitudes_de_lecture(carte.t, ALTITUDE_MAX_LECTURE_M)
    # La mer n'a pas de valeur : elle reste au niveau zéro, elle ne descend pas.
    altitudes[~carte.masque_terre] = 0.0
    # Une cellule non mesurée ne s'élève pas non plus : rien ne la porte.
    altitudes[carte.masque_terre & ~carte.mesuree] = 0.0
    return altitudes


def resume(carte: CarteStatistique) -> dict:
    """Ce que la commande imprime : de quoi rejouer et de quoi douter."""
    minimum, maximum = carte.bornes
    return {
        "lecture": carte.lecture.cle,
        "titre": carte.lecture.titre,
        "unite": carte.lecture.unite,
        "echelle": carte.lecture.echelle,
        "minimum": minimum,
        "maximum": maximum,
        "cellules": carte.cellules,
        "cellules_mesurees": carte.cellules_mesurees,
        "cellules_non_mesurees": carte.cellules - carte.cellules_mesurees,
        "tick": carte.tick,
        "seed": carte.seed,
    }
