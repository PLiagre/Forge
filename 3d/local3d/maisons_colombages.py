"""Générateur Blender 4.x de 24 variantes architecturales de maisons à colombages (Occident 1400).

Réutilise les primitives haute géométrie et la vérification par réimport FBX de
`catalogue_1400.py` pour produire 24 modèles uniques (3 LOD chacun) couvrant :
- 8 maisons individuelles / bourgeoises / artisans (oriel, 3 niveaux, tourelle, échoppe, tisserand)
- 6 maisons avec grange, remise, écurie ou hangar en bois adossé
- 6 ensembles de maisons collées (par 2 ou 3) avec balcon/galerie commun, escalier extérieur ou passage voûté
- 4 maisons à balcon/escalier extérieur, plan en L, taverne ou angle de rue

Variations de teintes de murs (crème, ocre, rose, gris, sauge, bleu guède, brique),
de bois de colombage (brûlé, chêne, sang-de-bœuf), de toits (tuiles, tuiles sombres,
tuiles ocre, ardoise, chaume), de volets, de fenêtres et de cheminées.

Usage :
    blender --background --python 3d/local3d/maisons_colombages.py -- \
        --sortie 3d/unity/Assets/ForgeLocal3D/Catalogue1400/MaisonsColombages \
        --textures 3d/unity/Assets/Interface/Resources/Forge/MatieresPBR
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalogue_1400 as base  # noqa: E402


# ---------------------------------------------------------------------------
# Palette étendue : 7 murs/briques, 3 bois, 5 toits, 4 volets
# ---------------------------------------------------------------------------

def preparer_palette_maisons(dossier_pbr: Path) -> dict[str, bpy.types.Material]:
    pal = base.preparer_palette(dossier_pbr)
    # Teintes d'enduits/torchis et briques de remplissage
    pal["torchis_creme"] = pal["torchis"]
    pal["torchis_ocre"] = base.creer_materiau_pbr(
        "M_TorchisOcre", dossier_pbr / "PiseOcre", "pise_ocre",
        teinte=(0.76, 0.56, 0.30), facteur_teinte=0.74, normal_strength=0.60,
    )
    pal["torchis_rose"] = base.creer_materiau_pbr(
        "M_TorchisRose", dossier_pbr / "PiseOcre", "pise_ocre",
        teinte=(0.68, 0.40, 0.33), facteur_teinte=0.76, normal_strength=0.60,
    )
    pal["torchis_gris"] = base.creer_materiau_pbr(
        "M_TorchisGris", dossier_pbr / "PiseOcre", "pise_ocre",
        teinte=(0.62, 0.60, 0.56), facteur_teinte=0.80, normal_strength=0.60,
    )
    pal["torchis_sauge"] = base.creer_materiau_pbr(
        "M_TorchisSauge", dossier_pbr / "PiseOcre", "pise_ocre",
        teinte=(0.48, 0.58, 0.48), facteur_teinte=0.78, normal_strength=0.58,
    )
    pal["torchis_bleu"] = base.creer_materiau_pbr(
        "M_TorchisBleu", dossier_pbr / "PiseOcre", "pise_ocre",
        teinte=(0.42, 0.51, 0.60), facteur_teinte=0.78, normal_strength=0.58,
    )
    pal["mur_brique"] = base.creer_materiau_pbr(
        "M_MurBriqueRouge", dossier_pbr / "TuilesMedievales", "tuiles_medievales",
        teinte=(0.56, 0.23, 0.16), facteur_teinte=0.48, normal_strength=0.95,
    )
    pal["brique_brune"] = base.creer_materiau_pbr(
        "M_BriqueBrune", dossier_pbr / "TuilesMedievales", "tuiles_medievales",
        teinte=(0.35, 0.21, 0.16), facteur_teinte=0.52, normal_strength=0.95,
    )
    # Bois de colombage et volets teintés
    pal["bois_rouge"] = base.creer_materiau_pbr(
        "M_BoisRouge", dossier_pbr / "BoisBrule", "bois_brule",
        teinte=(0.34, 0.11, 0.08), facteur_teinte=0.62, normal_strength=0.90,
    )
    pal["volet_vert"] = base.creer_materiau_simple("M_VoletVert", (0.14, 0.25, 0.17), roughness=0.78)
    pal["volet_rouge"] = base.creer_materiau_simple("M_VoletRouge", (0.38, 0.11, 0.09), roughness=0.76)
    pal["volet_bleu"] = base.creer_materiau_simple("M_VoletBleu", (0.16, 0.23, 0.30), roughness=0.78)
    # Toits variés
    pal["tuiles_sombres"] = base.creer_materiau_pbr(
        "M_TuilesSombres", dossier_pbr / "TuilesMedievales", "tuiles_medievales",
        teinte=(0.24, 0.18, 0.14), facteur_teinte=0.58, normal_strength=1.1,
    )
    pal["tuiles_ocre"] = base.creer_materiau_pbr(
        "M_TuilesOcre", dossier_pbr / "TuilesMedievales", "tuiles_medievales",
        teinte=(0.74, 0.44, 0.22), facteur_teinte=0.50, normal_strength=1.1,
    )
    pal["ardoise"] = base.creer_materiau_pbr(
        "M_Ardoise", dossier_pbr / "TuilesMedievales", "tuiles_medievales",
        teinte=(0.18, 0.22, 0.27), facteur_teinte=0.80, metallic=0.10, normal_strength=0.85,
    )
    return pal


# ---------------------------------------------------------------------------
# Briques architecturales modulaires (corps, cheminées, oriels, granges, balcons, escaliers)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConfigCorps:
    cx: float = 0.0
    cy: float = 0.0
    lx: float = 6.0
    ly: float = 5.0
    h_rdc: float = 2.65
    h_etage: float = 2.55
    niveaux_etage: int = 1         # 1 ou 2 étages en encorbellement
    h_toit: float = 3.20
    mat_rdc: str = "pierre_taille"
    mat_angle: str = "pierre_claire"
    mat_mur: str = "torchis_creme"
    mat_bois: str = "bois"
    mat_volet: str = "bois_clair"
    mat_toit: str = "tuiles"
    nb_travees_x: int = 4
    nb_travees_y: int = 3
    style_fenetre: str = "volets"  # volets | ogive | oriel | galerie | echoppe
    style_cheminee: str = "brique_centre"  # brique_centre | pierre_pignon | double | octogonale | laterale | sans
    porte_x_rel: float = -0.15
    porte_active: bool = True
    pignon_gauche_ouvert: bool = True
    pignon_droit_ouvert: bool = True
    croix_pattern: str = "plein"   # plein | bords | alterne
    details_sol: str = "banc_tonneau"  # banc_tonneau | tonneaux | sacs | aucun


def _croix_pour(nb: int, pattern: str) -> tuple[int, ...]:
    if pattern == "plein":
        return tuple(range(nb))
    if pattern == "bords":
        return (0, nb - 1) if nb >= 2 else (0,)
    return tuple(i for i in range(nb) if i % 2 == 0)


def ajouter_cheminee(c: base.Constructeur, cfg: ConfigCorps, z_toit: float) -> None:
    st = cfg.style_cheminee
    if st == "sans":
        return
    cx, cy = cfg.cx, cfg.cy
    if st == "brique_centre":
        x, y = cx - cfg.lx * 0.16, cy + cfg.ly * 0.16
        c.boite((x, y, z_toit + cfg.h_toit * 0.72), (0.88, 0.88, 2.35), "brique", chanfrein=0.02)
        c.boite((x, y, z_toit + cfg.h_toit * 0.72 + 1.24), (1.04, 1.04, 0.18), "brique", chanfrein=0.02)
        if c.lod <= 1:
            c.boite((x, y, z_toit + cfg.h_toit * 0.36), (1.10, 1.24, 0.10), "plomb", rot=(-0.50, 0, 0))
    elif st == "double":
        x, y = cx + cfg.lx * 0.14, cy + cfg.ly * 0.12
        c.boite((x, y, z_toit + cfg.h_toit * 0.70), (1.35, 0.78, 2.40), "mur_brique", chanfrein=0.02)
        c.boite((x, y, z_toit + cfg.h_toit * 0.70 + 1.26), (1.52, 0.94, 0.18), "brique", chanfrein=0.02)
        if c.lod == 0:
            for dx in (-0.34, 0.34):
                c.boite((x + dx, y, z_toit + cfg.h_toit * 0.70 + 1.46), (0.42, 0.42, 0.24), "brique_brune", chanfrein=0.015)
    elif st == "octogonale":
        x, y = cx - cfg.lx * 0.10, cy + cfg.ly * 0.14
        z_bas = z_toit + cfg.h_toit * 0.42
        c.boite((x, y, z_bas + 0.50), (0.96, 0.96, 1.00), "pierre_claire", chanfrein=0.02)
        c.cylindre((x, y, z_bas + 1.75), 0.44, 0.40, 1.65, 8, "brique")
        c.cylindre((x, y, z_bas + 2.66), 0.52, 0.50, 0.20, 8, "pierre_taille")
    elif st == "laterale":
        x, y = cx + cfg.lx * 0.22, cy + cfg.ly * 0.46
        h_tot = z_toit + cfg.h_toit + 0.85
        c.boite((x, y, h_tot * 0.5), (0.86, 0.72, h_tot), "pierre_claire", chanfrein=0.025)
        c.boite((x, y, h_tot + 0.12), (1.02, 0.88, 0.20), "pierre_taille", chanfrein=0.02)
    elif st == "pierre_pignon":
        # Grosse souche de cheminée en pierre extérieure à épaulement contre le pignon gauche (-X)
        x = cx - cfg.lx * 0.5 - 0.42
        h_tot = z_toit + cfg.h_toit + 0.90
        c.boite((x, cy, cfg.h_rdc * 0.52), (0.96, 1.68, cfg.h_rdc * 1.04), "pierre_claire", chanfrein=0.03)
        c.boite((x + 0.08, cy, cfg.h_rdc + (h_tot - cfg.h_rdc) * 0.5), (0.76, 1.18, h_tot - cfg.h_rdc), "pierre_taille", chanfrein=0.025)
        c.boite((x + 0.08, cy, h_tot + 0.12), (0.92, 1.34, 0.22), "pierre_claire", chanfrein=0.02)


def ajouter_oriel(c: base.Constructeur, x: float, y_mur: float, z_bas: float,
                  largeur: float, hauteur: float, mat_mur: str, mat_bois: str, mat_toit: str) -> None:
    """Oriel / bow-window médiéval en encorbellement vitré en façade (-Y)."""
    saillie = 0.76
    # 3 consoles galbées sous l'oriel
    if c.lod <= 1:
        for dx in (-largeur * 0.36, 0.0, largeur * 0.36):
            c.corbeau_galbe(x + dx, y_mur, z_bas + 0.04, (0.0, -1.0), 0.16, saillie * 0.88, 0.48, mat_bois)
    # Coffre bas + 3 baies vitrées + poutres
    c.boite((x, y_mur - saillie * 0.5, z_bas + hauteur * 0.20), (largeur, saillie, hauteur * 0.40), mat_mur)
    c.boite((x, y_mur - saillie * 0.5, z_bas + 0.06), (largeur + 0.12, saillie + 0.10, 0.12), mat_bois, chanfrein=0.015)
    c.boite((x, y_mur - saillie * 0.5, z_bas + hauteur * 0.42), (largeur + 0.10, saillie + 0.08, 0.11), mat_bois, chanfrein=0.014)
    c.boite((x, y_mur - saillie * 0.5, z_bas + hauteur - 0.06), (largeur + 0.12, saillie + 0.10, 0.12), mat_bois, chanfrein=0.015)
    # Vitrage face avant et côtés
    z_v = z_bas + hauteur * 0.68
    h_v = hauteur * 0.46
    c.boite((x, y_mur - saillie + 0.03, z_v), (largeur * 0.86, 0.05, h_v), "verre")
    for sx in (-1.0, 1.0):
        c.boite((x + sx * (largeur * 0.5 - 0.03), y_mur - saillie * 0.5, z_v), (0.05, saillie * 0.72, h_v), "verre")
        c.boite((x + sx * (largeur * 0.5), y_mur - saillie, z_bas + hauteur * 0.5), (0.11, 0.11, hauteur), mat_bois, chanfrein=0.01)
    if c.lod == 0:
        c.boite((x, y_mur - saillie, z_v), (0.07, 0.08, h_v + 0.04), mat_bois)
        c.boite((x, y_mur - saillie, z_v), (largeur * 0.90, 0.07, 0.06), mat_bois)
    # Petit toit en appentis sur l'oriel
    c.boite((x, y_mur - saillie * 0.52, z_bas + hauteur + 0.24), (largeur + 0.34, saillie + 0.36, 0.14), mat_toit, rot=(0.48, 0.0, 0.0))


def ajouter_echoppe_rdc(c: base.Constructeur, x: float, y_mur: float, largeur: float,
                        mat_bois: str, mat_toile: str = "toile", mat_accent: str = "banniere") -> None:
    """Comptoir d'échoppe médiévale ouvert au RDC + auvent de toile rayée."""
    c.boite((x, y_mur - 0.04, 1.48), (largeur, 0.10, 1.25), "charbon")
    c.boite((x, y_mur - 0.28, 0.86), (largeur + 0.16, 0.56, 0.11), "bois_clair", chanfrein=0.015)
    c.boite((x, y_mur - 0.06, 2.12), (largeur + 0.22, 0.22, 0.16), mat_bois, chanfrein=0.015)
    for sx in (-largeur * 0.5, largeur * 0.5):
        c.boite((x + sx, y_mur - 0.08, 1.06), (0.16, 0.18, 2.12), mat_bois, chanfrein=0.015)
    # Auvent incliné en toile
    c.boite((x, y_mur - 0.62, 2.18), (largeur + 0.38, 1.28, 0.06), mat_toile, rot=(0.30, 0.0, 0.0))
    if c.lod == 0:
        for k in (-0.35, 0.0, 0.35):
            c.boite((x + k * largeur, y_mur - 0.62, 2.21), (largeur * 0.18, 1.28, 0.03), mat_accent, rot=(0.30, 0.0, 0.0))
        # Petites marchandises sur l'étal
        c.boite((x - largeur * 0.24, y_mur - 0.32, 1.04), (0.42, 0.34, 0.26), "bois_clair", chanfrein=0.01)
        c.sac_noue((x + largeur * 0.22, y_mur - 0.30, 0.91), 0.20, 0.17, 0.32, 0.3, "jute", "corde")


def construire_corps_maison(c: base.Constructeur, cfg: ConfigCorps) -> dict:
    """Construit un corps de maison à colombages complet et renvoie ses bornes clés."""
    cx, cy = cfg.cx, cfg.cy
    hx, hy = cfg.lx * 0.5, cfg.ly * 0.5

    # 1. Soubassement & rez-de-chaussée
    c.boite((cx, cy, 0.44), (cfg.lx + 0.22, cfg.ly + 0.22, 0.88), cfg.mat_angle, chanfrein=0.025)
    c.boite((cx, cy, cfg.h_rdc * 0.5 + 0.30), (cfg.lx, cfg.ly, cfg.h_rdc - 0.60), cfg.mat_rdc, chanfrein=0.018)
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            if (sx < 0 and not cfg.pignon_gauche_ouvert) or (sx > 0 and not cfg.pignon_droit_ouvert):
                continue
            c.chainage_angle(cx + sx * hx, cy + sy * hy, 0.06, cfg.h_rdc - 0.04, sx, sy, cfg.mat_angle)

    # Porte & RDC avant (-Y)
    px = cx + cfg.porte_x_rel * cfg.lx
    if cfg.porte_active:
        c.porte_cintree((px, cy - hy - 0.11, 0.0), -1.0, 1.14, min(2.16, cfg.h_rdc - 0.38), cfg.mat_angle, cfg.mat_bois, "metal")
    if cfg.style_fenetre == "echoppe":
        ex = cx + (0.20 if cfg.porte_x_rel < 0 else -0.20) * cfg.lx
        ajouter_echoppe_rdc(c, ex, cy - hy - 0.06, min(2.35, cfg.lx * 0.42), cfg.mat_bois)
    else:
        for dx in (-0.36, 0.32):
            fx = cx + dx * cfg.lx
            if cfg.porte_active and abs(fx - px) < 1.05:
                continue
            c.fenetre_medievale((fx, cy - hy - 0.04, cfg.h_rdc * 0.58), "x", -1.0, 0.64, 0.68,
                                cfg.mat_bois, cfg.mat_volet, "verre", cfg.mat_angle, volets=(c.lod == 0 and cfg.style_fenetre == "volets"))

    # Fenêtres RDC sur le mur droit (+X) si ouvert
    if cfg.pignon_droit_ouvert:
        for fy in (-cfg.ly * 0.26, cfg.ly * 0.26):
            c.fenetre_medievale((cx + hx + 0.04, cy + fy, cfg.h_rdc * 0.58), "y", 1.0, 0.68, 0.64,
                                cfg.mat_bois, cfg.mat_volet, "verre", cfg.mat_angle, volets=(c.lod == 0))

    # 2. Étages en encorbellement (1 ou 2)
    z_courant = cfg.h_rdc
    lx_e, ly_e = cfg.lx, cfg.ly
    croix_x = _croix_pour(cfg.nb_travees_x, cfg.croix_pattern)
    croix_y = _croix_pour(cfg.nb_travees_y, cfg.croix_pattern)

    for niv in range(cfg.niveaux_etage):
        decal_x = 0.24 if (cfg.pignon_gauche_ouvert and cfg.pignon_droit_ouvert) else 0.0
        decal_y = 0.26
        lx_prev, ly_prev = lx_e, ly_e
        lx_e = lx_prev + 2.0 * decal_x
        ly_e = ly_prev + 2.0 * decal_y
        hx_e, hy_e = lx_e * 0.5, ly_e * 0.5

        # Corbeaux galbés sous l'encorbellement
        if c.lod <= 1:
            nb_c = max(3, cfg.nb_travees_x + 1)
            for i in range(nb_c):
                ux = cx - lx_prev * 0.44 + i * (lx_prev * 0.88 / max(1, nb_c - 1))
                for sy in (-1.0, 1.0):
                    c.corbeau_galbe(ux, cy + sy * ly_prev * 0.5, z_courant + 0.04, (0.0, sy), 0.17, 0.30, 0.42, cfg.mat_bois)
            if decal_x > 0.0:
                for i in range(cfg.nb_travees_y):
                    uy = cy - ly_prev * 0.36 + i * (ly_prev * 0.72 / max(1, cfg.nb_travees_y - 1))
                    for sx in (-1.0, 1.0):
                        c.corbeau_galbe(cx + sx * lx_prev * 0.5, uy, z_courant + 0.04, (sx, 0.0), 0.17, 0.28, 0.40, cfg.mat_bois)

        h_niv = cfg.h_etage * (0.94 if niv > 0 else 1.0)
        z_haut = z_courant + h_niv
        c.boite((cx, cy, z_courant + h_niv * 0.5), (lx_e, ly_e, h_niv), cfg.mat_mur)
        # Vraie ossature colombage 3D sur les faces visibles
        c.panneau_colombage(cx - hx_e, cx + hx_e, cy - hy_e, z_courant, z_haut, "x", -1.0, cfg.nb_travees_x, cfg.mat_bois, croix_x)
        c.panneau_colombage(cx - hx_e, cx + hx_e, cy + hy_e, z_courant, z_haut, "x", 1.0, cfg.nb_travees_x, cfg.mat_bois, croix_x[:2])
        if cfg.pignon_droit_ouvert:
            c.panneau_colombage(cy - hy_e, cy + hy_e, cx + hx_e, z_courant, z_haut, "y", 1.0, cfg.nb_travees_y, cfg.mat_bois, croix_y)
        if cfg.pignon_gauche_ouvert:
            c.panneau_colombage(cy - hy_e, cy + hy_e, cx - hx_e, z_courant, z_haut, "y", -1.0, cfg.nb_travees_y, cfg.mat_bois, croix_y[:2])

        # Fenêtres d'étage selon le style choisi
        z_fen = z_courant + h_niv * 0.57
        if cfg.style_fenetre == "oriel" and niv == 0:
            ajouter_oriel(c, cx, cy - hy_e, z_courant + 0.25, min(2.10, lx_e * 0.36), h_niv * 0.80, cfg.mat_mur, cfg.mat_bois, cfg.mat_toit)
            for sx in (-1.0, 1.0):
                if lx_e >= 5.2:
                    c.fenetre_medievale((cx + sx * lx_e * 0.34, cy - hy_e - 0.02, z_fen), "x", -1.0, 0.78, 1.05,
                                        cfg.mat_bois, cfg.mat_volet, "verre", cfg.mat_bois, volets=True)
        elif cfg.style_fenetre == "galerie":
            nb_g = 4 if lx_e >= 5.5 else 3
            for i in range(nb_g):
                ux = cx - lx_e * 0.34 + i * (lx_e * 0.68 / max(1, nb_g - 1))
                c.fenetre_medievale((ux, cy - hy_e - 0.02, z_fen), "x", -1.0, 0.74, 1.08,
                                    cfg.mat_bois, cfg.mat_volet, "verre", cfg.mat_bois, volets=False)
        elif cfg.style_fenetre == "ogive":
            for sx in (-0.24, 0.24):
                c.fenetre_medievale((cx + sx * lx_e, cy - hy_e - 0.02, z_fen), "x", -1.0, 0.78, 1.24,
                                    cfg.mat_bois, cfg.mat_volet, "verre", cfg.mat_angle, volets=False)
                if c.lod == 0:
                    c.boite((cx + sx * lx_e, cy - hy_e - 0.07, z_fen + 0.68), (0.94, 0.14, 0.16), cfg.mat_angle, chanfrein=0.02)
        else:
            nb_f = 2 if lx_e >= 4.4 else 1
            xs = (cx - lx_e * 0.24, cx + lx_e * 0.24) if nb_f == 2 else (cx,)
            for fx in xs:
                c.fenetre_medievale((fx, cy - hy_e - 0.02, z_fen), "x", -1.0, 0.96, 1.16,
                                    cfg.mat_bois, cfg.mat_volet, "verre", cfg.mat_bois, volets=True)

        # Fenêtres latérales (+X) à l'étage
        if cfg.pignon_droit_ouvert:
            for fy in (-ly_e * 0.22, ly_e * 0.22):
                c.fenetre_medievale((cx + hx_e + 0.02, cy + fy, z_fen), "y", 1.0, 0.88, 1.10,
                                    cfg.mat_bois, cfg.mat_volet, "verre", cfg.mat_bois, volets=(cfg.style_fenetre != "galerie"))

        z_courant = z_haut

    # 3. Toit pentu + colombage de pignon + cheminée
    strates = 6 if cfg.mat_toit != "ardoise" else 5
    ep_t = 0.30 if cfg.mat_toit == "chaume" else 0.18
    deb_x = 0.36 if (cfg.pignon_gauche_ouvert and cfg.pignon_droit_ouvert) else 0.12
    c.toit_detaille((cx, cy, z_courant), lx_e, ly_e, cfg.h_toit, cfg.mat_toit, cfg.mat_mur, cfg.mat_bois,
                    debord_x=deb_x, debord_y=0.44, epaisseur=ep_t, strates=strates)
    # Colombage 3D sur les pignons ouverts
    if c.lod <= 1:
        for sx, ouvert in ((-1.0, cfg.pignon_gauche_ouvert), (1.0, cfg.pignon_droit_ouvert)):
            if not ouvert:
                continue
            gx = cx + sx * (hx_e + 0.03)
            c.poutre((gx, cy - hy_e * 0.72, z_courant + cfg.h_toit * 0.28), (gx, cy + hy_e * 0.72, z_courant + cfg.h_toit * 0.28), 0.12, 0.08, cfg.mat_bois)
            c.poutre((gx, cy - hy_e * 0.36, z_courant + cfg.h_toit * 0.62), (gx, cy + hy_e * 0.36, z_courant + cfg.h_toit * 0.62), 0.11, 0.08, cfg.mat_bois)
            c.poutre((gx, cy - 0.52, z_courant), (gx, cy - 0.52, z_courant + cfg.h_toit * 0.78), 0.12, 0.08, cfg.mat_bois)
            c.poutre((gx, cy + 0.52, z_courant), (gx, cy + 0.52, z_courant + cfg.h_toit * 0.78), 0.12, 0.08, cfg.mat_bois)
            if c.lod == 0:
                c.boite((gx + sx * 0.03, cy, z_courant + cfg.h_toit * 0.44), (0.08, 0.72, 0.88), cfg.mat_volet, chanfrein=0.01)

    ajouter_cheminee(c, cfg, z_courant)

    # 4. Petits détails de vie au sol (LOD0)
    if c.lod == 0:
        if cfg.details_sol == "banc_tonneau" and cfg.pignon_droit_ouvert:
            c.boite((cx + hx + 0.26, cy - 0.75, 0.44), (0.36, 1.32, 0.07), "bois_clair", chanfrein=0.01)
            for dy in (-0.48, 0.48):
                c.boite((cx + hx + 0.26, cy - 0.75 + dy, 0.22), (0.30, 0.08, 0.42), cfg.mat_bois)
            c.tonneau_bombe((cx + hx + 0.36, cy + 1.45, 0.0), 0.26, 0.32, 0.90, "bois", "metal")
        elif cfg.details_sol == "tonneaux":
            c.tonneau_bombe((cx + hx - 0.55, cy - hy - 0.45, 0.0), 0.26, 0.32, 0.90, "bois", "metal")
            c.tonneau_bombe((cx + hx - 1.20, cy - hy - 0.42, 0.0), 0.24, 0.29, 0.84, "bois_clair", "metal")
        elif cfg.details_sol == "sacs":
            c.sac_noue((cx + hx - 0.75, cy - hy - 0.42, 0.0), 0.28, 0.22, 0.44, 0.2, "jute", "corde")
            c.sac_noue((cx + hx - 1.30, cy - hy - 0.40, 0.0), 0.26, 0.21, 0.40, -0.4, "jute", "corde")

    return {"z_etage": cfg.h_rdc, "z_toit": z_courant, "lx_e": lx_e, "ly_e": ly_e, "hx": hx, "hy": hy}


def ajouter_grange_adossee(c: base.Constructeur, x_attache: float, cy: float, cote_x: float,
                           long_x: float, larg_y: float, haut_murs: float, mat_bois: str,
                           mat_toit: str, style: str = "fermee") -> None:
    """Ajoute une grange, remise, écurie ou hangar en bois adossé sur le côté (+1 ou -1)."""
    gx = x_attache + cote_x * (long_x * 0.5)
    # Socle discret en pierre + poteaux
    c.boite((gx, cy, 0.14), (long_x + 0.10, larg_y + 0.10, 0.28), "pierre_claire", chanfrein=0.02)
    for sx in (-long_x * 0.48, long_x * 0.48):
        for sy in (-larg_y * 0.48, larg_y * 0.48):
            c.boite((gx + sx, cy + sy, haut_murs * 0.5 + 0.20), (0.20, 0.20, haut_murs), mat_bois, chanfrein=0.015)

    if style in ("fermee", "ecurie"):
        c.boite((gx, cy, haut_murs * 0.5 + 0.22), (long_x - 0.08, larg_y - 0.08, haut_murs - 0.06), "bois_clair")
        if c.lod == 0:
            # Couvre-joints verticaux de bardage bois
            nb_b = max(4, int(long_x / 0.34))
            for i in range(nb_b):
                ux = gx - long_x * 0.46 + i * (long_x * 0.92 / max(1, nb_b - 1))
                c.boite((ux, cy - larg_y * 0.49, haut_murs * 0.5 + 0.22), (0.06, 0.05, haut_murs - 0.12), mat_bois)
        # Double porte de grange ferrée en façade (-Y)
        lp = min(2.05, long_x * 0.56)
        hp = min(2.30, haut_murs * 0.80)
        c.boite((gx, cy - larg_y * 0.50, hp * 0.5 + 0.24), (lp, 0.14, hp), mat_bois, chanfrein=0.014)
        if c.lod == 0:
            for hz in (0.75, hp * 0.72 + 0.24):
                c.boite((gx, cy - larg_y * 0.58, hz), (lp * 0.88, 0.04, 0.075), "metal")
            c.sac_noue((gx - lp * 0.62, cy - larg_y * 0.58, 0.0), 0.26, 0.21, 0.42, 0.2, "jute", "corde")
    else:
        # Hangar ou bûcher ouvert sous charpente bois
        c.boite((gx, cy + larg_y * 0.46, haut_murs * 0.5 + 0.22), (long_x - 0.08, 0.14, haut_murs - 0.06), "bois_clair")
        if c.lod <= 1:
            c.boite((gx, cy - larg_y * 0.46, haut_murs + 0.16), (long_x + 0.12, 0.18, 0.18), mat_bois, chanfrein=0.015)
            for sx in (-long_x * 0.46, long_x * 0.46):
                c.poutre((gx + sx, cy - larg_y * 0.46, haut_murs - 0.45), (gx + sx * 0.65, cy - larg_y * 0.46, haut_murs + 0.14), 0.11, 0.11, mat_bois)
        if c.lod == 0:
            if style == "bucher":
                # Pile de bûches + tonneau sous l'appentis
                for rz in range(3):
                    for rx in range(5):
                        c.cylindre((gx - 0.85 + rx * 0.32, cy + 0.35, 0.42 + rz * 0.24), 0.11, 0.11, 1.05, 8, "bois", rot=(math.pi * 0.5, 0, 0), smooth=True)
                c.tonneau_bombe((gx + 0.85, cy - 0.25, 0.0), 0.25, 0.30, 0.86, "bois", "metal")
            else:
                # Hangar de charron : roues + établi
                c.roue_rayons((gx - 0.70, cy - 0.35, 0.52), 0.48, 0.07, 8, "bois_clair", "metal")
                c.boite((gx + 0.55, cy + 0.10, 0.85), (1.45, 0.75, 0.10), "bois_clair", chanfrein=0.01)
                for dx in (-0.60, 0.60):
                    for dy in (-0.28, 0.28):
                        c.boite((gx + 0.55 + dx, cy + 0.10 + dy, 0.42), (0.10, 0.10, 0.80), mat_bois)

    # Toit en appentis (pente s'éloignant de la maison) ou 2 pans selon la largeur
    if long_x >= 3.8 and style == "fermee":
        c.toit_detaille((gx, cy, haut_murs + 0.22), long_x, larg_y, 2.35, mat_toit, "bois_clair", mat_bois,
                        debord_x=0.30, debord_y=0.36, epaisseur=0.24 if mat_toit == "chaume" else 0.15, strates=5)
        if c.lod == 0:
            # Potence de grenier à foin sur le pignon extérieur
            px_ext = x_attache + cote_x * (long_x + 0.10)
            c.poutre((px_ext, cy, haut_murs + 1.85), (px_ext + cote_x * 0.95, cy, haut_murs + 1.85), 0.14, 0.14, mat_bois)
            c.cylindre((px_ext + cote_x * 0.78, cy, haut_murs + 1.68), 0.12, 0.12, 0.06, 10, "metal", rot=(math.pi * 0.5, 0, 0), smooth=True)
    else:
        pente = -cote_x * 0.34
        z_t = haut_murs + 0.22 + long_x * 0.17
        c.boite((gx, cy, z_t), (long_x + 0.55, larg_y + 0.55, 0.16), mat_toit, rot=(0.0, pente, 0.0))
        if c.lod == 0:
            for ky in (-larg_y * 0.42, 0.0, larg_y * 0.42):
                c.boite((gx, cy + ky, z_t - 0.14), (long_x + 0.42, 0.11, 0.13), mat_bois, rot=(0.0, pente, 0.0))


def ajouter_balcon(c: base.Constructeur, x0: float, x1: float, y_mur: float, z_sol: float,
                   profondeur: float, mat_bois: str, mat_toit: str | None = None,
                   ouvert_escalier_x: tuple[float, float] | None = None) -> None:
    """Balcon / coursive médiévale en bois sur consoles galbées, garde-corps et auvent optionnel."""
    long_b = x1 - x0
    cx = (x0 + x1) * 0.5
    cy = y_mur - profondeur * 0.5
    # Plancher en madriers + poutre de rive
    c.boite((cx, cy, z_sol), (long_b, profondeur, 0.12), "bois_clair", chanfrein=0.012)
    c.boite((cx, y_mur - profondeur + 0.06, z_sol - 0.08), (long_b + 0.08, 0.14, 0.16), mat_bois, chanfrein=0.012)
    # Consoles galbées + poteaux d'appui au sol si balcon large
    nb_con = max(3, int(long_b / 1.45) + 1)
    for i in range(nb_con):
        ux = x0 + 0.15 + i * ((long_b - 0.30) / max(1, nb_con - 1))
        if c.lod <= 1:
            c.corbeau_galbe(ux, y_mur, z_sol - 0.02, (0.0, -1.0), 0.16, profondeur * 0.90, 0.55, mat_bois)
        if i in (0, nb_con - 1) or long_b > 5.5:
            c.boite((ux, y_mur - profondeur + 0.10, z_sol * 0.5), (0.16, 0.16, z_sol), mat_bois, chanfrein=0.014)
    # Garde-corps avant + côtés (laisse un passage libre si escalier branché)
    h_gc = 0.96
    c.boite((x0 + 0.06, cy, z_sol + h_gc), (0.10, profondeur, 0.10), mat_bois, chanfrein=0.01)
    c.boite((x1 - 0.06, cy, z_sol + h_gc), (0.10, profondeur, 0.10), mat_bois, chanfrein=0.01)
    # Segments de garde-corps avant hors ouverture escalier
    segments = [(x0, x1)]
    if ouvert_escalier_x is not None:
        ea, eb = ouvert_escalier_x
        segments = []
        if ea > x0 + 0.25:
            segments.append((x0, ea))
        if eb < x1 - 0.25:
            segments.append((eb, x1))
    for sa, sb in segments:
        sm = (sa + sb) * 0.5
        sl = sb - sa
        c.boite((sm, y_mur - profondeur + 0.08, z_sol + h_gc), (sl, 0.11, 0.10), mat_bois, chanfrein=0.01)
        c.boite((sm, y_mur - profondeur + 0.08, z_sol + h_gc * 0.50), (sl, 0.08, 0.08), mat_bois)
        if c.lod == 0:
            nb_bal = max(2, int(sl / 0.32))
            for k in range(nb_bal + 1):
                bx = sa + k * (sl / nb_bal)
                c.boite((bx, y_mur - profondeur + 0.08, z_sol + h_gc * 0.5), (0.065, 0.065, h_gc), mat_bois)
    # Auvent / galerie couverte si `mat_toit` est précisé
    if mat_toit is not None:
        h_p = 2.25
        for i in range(nb_con):
            ux = x0 + 0.15 + i * ((long_b - 0.30) / max(1, nb_con - 1))
            c.boite((ux, y_mur - profondeur + 0.10, z_sol + h_p * 0.5), (0.14, 0.14, h_p), mat_bois, chanfrein=0.012)
        c.boite((cx, y_mur - profondeur + 0.10, z_sol + h_p), (long_b + 0.14, 0.16, 0.16), mat_bois, chanfrein=0.014)
        c.boite((cx, cy - 0.12, z_sol + h_p + 0.24), (long_b + 0.42, profondeur + 0.58, 0.13), mat_toit, rot=(0.28, 0.0, 0.0))


def ajouter_escalier_exterieur(c: base.Constructeur, x_haut: float, y_balcon: float, z_haut: float,
                               sens_x: float, largeur: float, mat: str, en_pierre: bool = False) -> None:
    """Escalier extérieur en bois (limons + marches + rampe) ou en pierre maçonnée."""
    long_x = z_haut * 1.15
    nb_m = 10 if c.lod == 0 else (6 if c.lod == 1 else 4)
    cy = y_balcon - largeur * 0.5
    if en_pierre:
        for i in range(nb_m):
            t = (i + 0.5) / nb_m
            mx = x_haut + sens_x * (long_x * t)
            mz = z_haut * (1.0 - t)
            c.boite((mx, cy, mz * 0.5), (long_x / nb_m * 1.06, largeur, mz), mat, chanfrein=0.018)
        # Muret garde-corps en pierre côté extérieur
        c.poutre((x_haut, y_balcon - largeur + 0.10, z_haut + 0.72),
                 (x_haut + sens_x * long_x, y_balcon - largeur + 0.10, 0.72), 0.18, 0.56, mat)
    else:
        # Deux limons obliques + marches en madriers + rampe bois
        for dy in (0.08, largeur - 0.08):
            c.poutre((x_haut, y_balcon - dy, z_haut), (x_haut + sens_x * long_x, y_balcon - dy, 0.06), 0.12, 0.22, mat)
        for i in range(nb_m):
            t = (i + 0.5) / nb_m
            mx = x_haut + sens_x * (long_x * t)
            mz = z_haut * (1.0 - t)
            c.boite((mx, cy, mz), (0.30, largeur - 0.08, 0.07), "bois_clair", chanfrein=0.008)
        # Rampe bois côté rue
        y_r = y_balcon - largeur + 0.08
        c.poutre((x_haut, y_r, z_haut + 0.92), (x_haut + sens_x * long_x, y_r, 0.92), 0.09, 0.09, mat)
        for t in (0.0, 0.5, 1.0):
            px = x_haut + sens_x * long_x * t
            pz = z_haut * (1.0 - t)
            c.boite((px, y_r, pz + 0.46), (0.09, 0.09, 0.94), mat, chanfrein=0.01)


def ajouter_tourelle_escalier(c: base.Constructeur, x: float, y: float, hauteur: float,
                              mat_pierre: str, mat_toit: str) -> None:
    """Tourelle d'escalier octogonale en façade avec petites baies décalées et poivrière."""
    c.cylindre((x, y, hauteur * 0.5), 1.05, 1.00, hauteur, 8, mat_pierre)
    c.cylindre((x, y, hauteur + 0.08), 1.12, 1.12, 0.18, 8, "pierre_taille")
    c.revolution((x, y, hauteur + 0.15), [(1.22, 0.0), (0.68, 1.10), (0.03, 2.35)], 8, mat_toit, smooth=False)
    c.porte_cintree((x, y - 0.98, 0.0), -1.0, 0.92, 1.92, "pierre_taille", "bois", "metal")
    if c.lod <= 1:
        for az, ang in ((2.8, -0.35), (4.1, 0.25), (5.3, -0.10)):
            fx = x + math.sin(ang) * 0.98
            fy = y - math.cos(ang) * 0.98
            c.boite((fx, fy, az), (0.34, 0.10, 0.52), "verre", rot=(0, 0, ang))


# ---------------------------------------------------------------------------
# Les 24 STYLES de maisons à colombages
# ---------------------------------------------------------------------------

def _b_01(c, lod):
    construire_corps_maison(c, ConfigCorps(lx=6.2, ly=5.2, mat_mur="torchis_creme", mat_toit="tuiles", style_cheminee="brique_centre"))


def _b_02(c, lod):
    construire_corps_maison(c, ConfigCorps(
        lx=6.0, ly=5.0, mat_rdc="mur_brique", mat_angle="pierre_taille", mat_mur="torchis_ocre",
        mat_bois="bois_rouge", mat_volet="volet_vert", mat_toit="tuiles_sombres",
        style_fenetre="oriel", style_cheminee="double", details_sol="tonneaux",
    ))


def _b_03(c, lod):
    construire_corps_maison(c, ConfigCorps(
        lx=7.2, ly=5.4, h_rdc=2.45, h_etage=2.35, h_toit=3.65,
        mat_rdc="pierre", mat_angle="pierre_claire", mat_mur="torchis_gris",
        mat_bois="bois", mat_volet="volet_vert", mat_toit="chaume",
        nb_travees_x=5, style_cheminee="pierre_pignon", details_sol="sacs",
    ))


def _b_04(c, lod):
    construire_corps_maison(c, ConfigCorps(
        lx=5.4, ly=5.8, h_rdc=2.80, h_etage=2.65, h_toit=3.80,
        mat_rdc="mur_brique", mat_angle="pierre_claire", mat_mur="mur_brique",
        mat_bois="bois", mat_volet="volet_rouge", mat_toit="ardoise",
        nb_travees_x=3, style_fenetre="ogive", style_cheminee="octogonale",
    ))


def _b_05(c, lod):
    construire_corps_maison(c, ConfigCorps(
        lx=5.4, ly=4.8, h_rdc=2.65, h_etage=2.35, niveaux_etage=2, h_toit=3.05,
        mat_rdc="pierre_claire", mat_angle="pierre_taille", mat_mur="torchis_rose",
        mat_bois="bois", mat_volet="volet_bleu", mat_toit="ardoise",
        nb_travees_x=3, style_cheminee="laterale", croix_pattern="bords",
    ))


def _b_06(c, lod):
    construire_corps_maison(c, ConfigCorps(
        lx=7.4, ly=4.8, h_rdc=2.55, h_etage=2.55, h_toit=3.00,
        mat_rdc="pierre_taille", mat_angle="pierre_claire", mat_mur="torchis_bleu",
        mat_bois="bois", mat_volet="bois_clair", mat_toit="tuiles_ocre",
        nb_travees_x=5, style_fenetre="galerie", style_cheminee="brique_centre", croix_pattern="alterne",
    ))


def _b_07(c, lod):
    construire_corps_maison(c, ConfigCorps(
        lx=6.4, ly=5.2, h_rdc=2.75, h_etage=2.55,
        mat_rdc="pierre_taille", mat_angle="pierre_claire", mat_mur="torchis_sauge",
        mat_bois="bois", mat_volet="bois_clair", mat_toit="tuiles",
        porte_x_rel=-0.28, style_fenetre="echoppe", style_cheminee="double", details_sol="tonneaux",
    ))


def _b_08(c, lod):
    info = construire_corps_maison(c, ConfigCorps(
        lx=6.8, ly=5.2, h_rdc=2.70, h_etage=2.55, h_toit=3.30,
        mat_rdc="pierre_claire", mat_angle="pierre_taille", mat_mur="torchis_creme",
        mat_bois="bois", mat_volet="volet_rouge", mat_toit="ardoise",
        porte_active=False, style_cheminee="octogonale",
    ))
    ajouter_tourelle_escalier(c, -1.05, -info["hy"] - 0.55, info["z_toit"] + 0.90, "pierre_claire", "ardoise")


# Famille B — Avec grange, remise, écurie ou hangar en bois adossé (6 styles)

def _b_09(c, lod):
    info = construire_corps_maison(c, ConfigCorps(
        cx=-2.2, lx=5.8, ly=5.0, mat_mur="torchis_creme", mat_toit="tuiles",
        pignon_droit_ouvert=False, style_cheminee="brique_centre", details_sol="aucun",
    ))
    ajouter_grange_adossee(c, -2.2 + info["hx"], 0.0, 1.0, 4.4, 4.6, 3.0, "bois", "chaume", style="fermee")


def _b_10(c, lod):
    info = construire_corps_maison(c, ConfigCorps(
        cx=-2.1, lx=5.8, ly=5.2, mat_rdc="pierre_claire", mat_mur="torchis_ocre",
        mat_bois="bois_clair", mat_volet="volet_vert", mat_toit="tuiles_ocre",
        pignon_droit_ouvert=False, style_cheminee="pierre_pignon", details_sol="aucun",
    ))
    ajouter_grange_adossee(c, -2.1 + info["hx"], 0.0, 1.0, 4.2, 4.8, 2.9, "bois", "tuiles_ocre", style="fermee")


def _b_11(c, lod):
    info = construire_corps_maison(c, ConfigCorps(
        cx=-1.5, lx=5.4, ly=5.0, mat_rdc="pierre", mat_mur="torchis_gris",
        mat_volet="volet_bleu", mat_toit="ardoise",
        pignon_droit_ouvert=False, style_cheminee="laterale", details_sol="aucun",
    ))
    ajouter_grange_adossee(c, -1.5 + info["hx"], 0.0, 1.0, 3.0, 4.4, 2.5, "bois", "ardoise", style="bucher")


def _b_12(c, lod):
    info = construire_corps_maison(c, ConfigCorps(
        cx=-2.2, lx=5.6, ly=5.2, mat_rdc="brique_brune", mat_mur="mur_brique",
        mat_bois="bois", mat_volet="bois_clair", mat_toit="tuiles_sombres",
        pignon_droit_ouvert=False, style_cheminee="double", details_sol="aucun",
    ))
    ajouter_grange_adossee(c, -2.2 + info["hx"], 0.0, 1.0, 4.5, 4.8, 3.2, "bois", "tuiles_sombres", style="fermee")


def _b_13(c, lod):
    info = construire_corps_maison(c, ConfigCorps(
        cx=1.9, lx=5.8, ly=5.0, mat_rdc="pierre_taille", mat_mur="torchis_rose",
        mat_bois="bois_rouge", mat_volet="volet_vert", mat_toit="tuiles",
        style_fenetre="oriel", pignon_gauche_ouvert=False, style_cheminee="brique_centre", details_sol="aucun",
    ))
    ajouter_grange_adossee(c, 1.9 - info["hx"], 0.0, -1.0, 3.8, 4.4, 2.6, "bois_rouge", "tuiles_sombres", style="ecurie")


def _b_14(c, lod):
    info = construire_corps_maison(c, ConfigCorps(
        cx=-2.0, lx=5.8, ly=5.0, mat_rdc="pierre_claire", mat_mur="torchis_sauge",
        mat_bois="bois", mat_volet="bois_clair", mat_toit="tuiles_sombres",
        pignon_droit_ouvert=False, style_cheminee="pierre_pignon", details_sol="aucun",
    ))
    ajouter_grange_adossee(c, -2.0 + info["hx"], 0.0, 1.0, 4.0, 4.6, 2.8, "bois", "tuiles_sombres", style="hangar")


# Famille C — Maisons collées (mitoyennes) avec balcon commun, escalier ou passage voûté (6 styles)

def _b_15(c, lod):
    # 2 maisons collées + grand balcon commun bois + escalier extérieur bois
    i1 = construire_corps_maison(c, ConfigCorps(
        cx=-2.8, lx=5.6, ly=5.0, h_rdc=2.60, h_etage=2.50, h_toit=3.10,
        mat_mur="torchis_creme", mat_toit="tuiles", pignon_droit_ouvert=False,
        style_cheminee="brique_centre", details_sol="aucun",
    ))
    construire_corps_maison(c, ConfigCorps(
        cx=2.6, lx=5.2, ly=5.0, h_rdc=2.60, h_etage=2.65, h_toit=3.35,
        mat_rdc="mur_brique", mat_mur="torchis_ocre", mat_bois="bois_rouge", mat_volet="volet_vert",
        mat_toit="tuiles_sombres", pignon_gauche_ouvert=False, style_cheminee="double", details_sol="tonneaux",
    ))
    y_m = -i1["ly_e"] * 0.5
    ajouter_balcon(c, -4.4, 4.2, y_m, 2.62, 1.25, "bois", mat_toit=None, ouvert_escalier_x=(-0.55, 0.55))
    ajouter_escalier_exterieur(c, 0.55, y_m - 1.25, 2.62, 1.0, 1.05, "bois", en_pierre=False)


def _b_16(c, lod):
    # 2 maisons collées (gris + brique) + balcon couvert partagé + escalier extérieur en pierre
    i1 = construire_corps_maison(c, ConfigCorps(
        cx=-2.7, lx=5.4, ly=5.0, h_rdc=2.65, h_etage=2.45, h_toit=3.30,
        mat_rdc="pierre", mat_mur="torchis_gris", mat_volet="volet_bleu", mat_toit="ardoise",
        pignon_droit_ouvert=False, style_cheminee="octogonale", details_sol="aucun",
    ))
    construire_corps_maison(c, ConfigCorps(
        cx=2.7, lx=5.4, ly=5.0, h_rdc=2.65, h_etage=2.65, h_toit=2.95,
        mat_rdc="brique_brune", mat_mur="mur_brique", mat_volet="bois_clair", mat_toit="tuiles",
        pignon_gauche_ouvert=False, style_cheminee="brique_centre", details_sol="aucun",
    ))
    y_m = -i1["ly_e"] * 0.5
    ajouter_balcon(c, -3.6, 3.6, y_m, 2.66, 1.28, "bois", mat_toit="ardoise", ouvert_escalier_x=(-0.6, 0.6))
    ajouter_escalier_exterieur(c, -0.6, y_m - 1.28, 2.66, -1.0, 1.12, "pierre_claire", en_pierre=True)


def _b_17(c, lod):
    # 2 maisons collées (rose + crème) + galerie/balcon couvert continu + escalier bois à droite
    i1 = construire_corps_maison(c, ConfigCorps(
        cx=-2.7, lx=5.4, ly=4.8, h_rdc=2.60, h_etage=2.55, h_toit=3.15,
        mat_mur="torchis_rose", mat_bois="bois_rouge", mat_volet="volet_vert", mat_toit="tuiles_sombres",
        pignon_droit_ouvert=False, style_cheminee="pierre_pignon", details_sol="aucun",
    ))
    construire_corps_maison(c, ConfigCorps(
        cx=2.6, lx=5.2, ly=4.8, h_rdc=2.60, h_etage=2.55, h_toit=3.45,
        mat_mur="torchis_creme", mat_bois="bois", mat_volet="volet_rouge", mat_toit="tuiles",
        pignon_gauche_ouvert=False, style_cheminee="laterale", details_sol="aucun",
    ))
    y_m = -i1["ly_e"] * 0.5
    ajouter_balcon(c, -4.8, 4.6, y_m, 2.62, 1.32, "bois", mat_toit="tuiles_sombres", ouvert_escalier_x=(3.2, 4.5))
    ajouter_escalier_exterieur(c, 3.2, y_m - 1.32, 2.62, -1.0, 1.05, "bois", en_pierre=False)


def _b_18(c, lod):
    # 2 maisons collées de rue marchande : échoppes au RDC + balcon commun à l'étage
    i1 = construire_corps_maison(c, ConfigCorps(
        cx=-2.8, lx=5.6, ly=5.0, h_rdc=2.75, h_etage=2.55,
        mat_mur="torchis_bleu", mat_volet="bois_clair", mat_toit="ardoise",
        porte_x_rel=-0.30, style_fenetre="echoppe", pignon_droit_ouvert=False,
        style_cheminee="brique_centre", details_sol="aucun",
    ))
    construire_corps_maison(c, ConfigCorps(
        cx=2.8, lx=5.6, ly=5.0, h_rdc=2.75, h_etage=2.70, h_toit=3.35,
        mat_rdc="mur_brique", mat_mur="torchis_ocre", mat_volet="volet_rouge", mat_toit="tuiles_ocre",
        porte_x_rel=0.30, style_fenetre="echoppe", pignon_gauche_ouvert=False,
        style_cheminee="double", details_sol="aucun",
    ))
    y_m = -i1["ly_e"] * 0.5
    ajouter_balcon(c, -4.2, 4.2, y_m, 2.78, 1.05, "bois", mat_toit=None)


def _b_19(c, lod):
    # Rangée de 3 maisons collées étroites (crème, brique, sauge) à toits et hauteurs variés
    construire_corps_maison(c, ConfigCorps(
        cx=-4.2, lx=4.2, ly=4.8, h_rdc=2.55, h_etage=2.45, h_toit=3.00, nb_travees_x=3,
        mat_mur="torchis_creme", mat_toit="tuiles", pignon_droit_ouvert=False,
        style_cheminee="brique_centre", details_sol="aucun",
    ))
    construire_corps_maison(c, ConfigCorps(
        cx=0.0, lx=4.2, ly=5.0, h_rdc=2.65, h_etage=2.30, niveaux_etage=2, h_toit=2.95, nb_travees_x=3,
        mat_rdc="mur_brique", mat_mur="mur_brique", mat_volet="volet_bleu", mat_toit="ardoise",
        pignon_gauche_ouvert=False, pignon_droit_ouvert=False, style_cheminee="octogonale", details_sol="aucun",
    ))
    construire_corps_maison(c, ConfigCorps(
        cx=4.2, lx=4.2, ly=4.8, h_rdc=2.55, h_etage=2.65, h_toit=3.35, nb_travees_x=3,
        mat_mur="torchis_sauge", mat_bois="bois_rouge", mat_volet="bois_clair", mat_toit="tuiles_sombres",
        pignon_gauche_ouvert=False, style_cheminee="double", details_sol="tonneaux",
    ))


def _b_20(c, lod):
    # 2 maisons collées reliées par un passage voûté traversant + pont en colombages et balcon
    construire_corps_maison(c, ConfigCorps(
        cx=-4.1, lx=4.8, ly=5.0, h_rdc=2.70, h_etage=2.55, h_toit=3.10, nb_travees_x=3,
        mat_mur="torchis_ocre", mat_toit="tuiles", pignon_droit_ouvert=False,
        style_cheminee="pierre_pignon", details_sol="aucun",
    ))
    construire_corps_maison(c, ConfigCorps(
        cx=4.1, lx=4.8, ly=5.0, h_rdc=2.70, h_etage=2.55, h_toit=3.20, nb_travees_x=3,
        mat_rdc="pierre", mat_mur="torchis_creme", mat_volet="volet_vert", mat_toit="tuiles_sombres",
        pignon_gauche_ouvert=False, style_cheminee="brique_centre", details_sol="aucun",
    ))
    # Pont-étage en colombage au-dessus du passage pavé (largeur 3.4 m)
    c.boite((0.0, 0.0, 0.06), (3.50, 5.40, 0.12), "paves")
    c.boite((0.0, 0.0, 4.00), (3.60, 5.40, 2.55), "torchis_rose")
    c.panneau_colombage(-1.80, 1.80, -2.70, 2.72, 5.28, "x", -1.0, 2, "bois", (0, 1))
    c.panneau_colombage(-1.80, 1.80, 2.70, 2.72, 5.28, "x", 1.0, 2, "bois", (0, 1))
    c.fenetre_medievale((0.0, -2.72, 4.18), "x", -1.0, 1.15, 1.15, "bois", "volet_rouge", "verre", "bois", volets=True)
    # Grande arche en voussoirs sous le pont
    nb_v = 11 if lod == 0 else 7
    for fy in (-2.42, 2.42):
        for i in range(nb_v):
            a = math.pi * (i + 0.5) / nb_v
            c.boite((math.cos(a) * 1.65, fy, 1.35 + math.sin(a) * 1.35), (0.34, 0.28, 0.42),
                    "pierre_claire", rot=(0.0, a - math.pi * 0.5, 0.0), chanfrein=0.018)
    c.toit_detaille((0.0, 0.0, 5.28), 3.60, 5.40, 2.85, "ardoise", "torchis_rose", "bois",
                    debord_x=0.10, debord_y=0.42, epaisseur=0.17, strates=5)


# Famille D — Balcon/escalier individuel, plan en L, taverne, maison d'angle (4 styles)

def _b_21(c, lod):
    info = construire_corps_maison(c, ConfigCorps(
        lx=6.6, ly=5.0, h_rdc=2.65, h_etage=2.55,
        mat_mur="torchis_ocre", mat_bois="bois", mat_volet="volet_bleu", mat_toit="tuiles",
        style_cheminee="pierre_pignon", details_sol="sacs",
    ))
    y_m = -info["ly_e"] * 0.5
    ajouter_balcon(c, -2.8, 2.8, y_m, 2.66, 1.25, "bois", mat_toit=None, ouvert_escalier_x=(1.5, 2.7))
    ajouter_escalier_exterieur(c, 1.5, y_m - 1.25, 2.66, -1.0, 1.05, "bois", en_pierre=False)


def _b_22(c, lod):
    # Maison en L (aile principale + aile retour) avec galerie et escalier dans l'angle
    construire_corps_maison(c, ConfigCorps(
        cx=-1.2, cy=1.4, lx=6.6, ly=4.8, h_rdc=2.65, h_etage=2.55, h_toit=3.15,
        mat_mur="torchis_creme", mat_toit="tuiles_sombres", style_cheminee="octogonale", details_sol="aucun",
    ))
    construire_corps_maison(c, ConfigCorps(
        cx=2.4, cy=-1.8, lx=4.6, ly=4.6, h_rdc=2.65, h_etage=2.45, h_toit=2.95, nb_travees_x=3,
        mat_rdc="pierre_claire", mat_mur="torchis_ocre", mat_volet="volet_vert", mat_toit="tuiles",
        porte_active=False, style_cheminee="brique_centre", details_sol="tonneaux",
    ))
    # Balcon + escalier extérieur dans la cour d'angle devant l'aile principale
    ajouter_balcon(c, -4.0, 0.2, 1.4 - 2.65, 2.66, 1.18, "bois", mat_toit="tuiles_sombres", ouvert_escalier_x=(-1.2, 0.0))
    ajouter_escalier_exterieur(c, -1.2, 1.4 - 2.65 - 1.18, 2.66, -1.0, 1.0, "bois", en_pierre=False)


def _b_23(c, lod):
    # Taverne en colombages rouges, balcon de façade, escalier de pierre, enseigne en fer forgé et tonneaux
    info = construire_corps_maison(c, ConfigCorps(
        lx=7.0, ly=5.4, h_rdc=2.75, h_etage=2.60, h_toit=3.40,
        mat_rdc="pierre", mat_angle="pierre_claire", mat_mur="torchis_rose",
        mat_bois="bois_rouge", mat_volet="volet_rouge", mat_toit="ardoise",
        nb_travees_x=5, style_cheminee="double", details_sol="tonneaux",
    ))
    y_m = -info["ly_e"] * 0.5
    ajouter_balcon(c, -2.9, 2.9, y_m, 2.76, 1.22, "bois_rouge", mat_toit=None, ouvert_escalier_x=(1.6, 2.8))
    ajouter_escalier_exterieur(c, 1.6, y_m - 1.22, 2.76, -1.0, 1.08, "pierre_claire", en_pierre=True)
    # Potence et enseigne de taverne en fer forgé + panneau bois doré
    if lod <= 1:
        c.poutre((3.4, y_m - 0.1, 3.65), (3.4, y_m - 1.35, 3.65), 0.06, 0.06, "metal")
        c.poutre((3.4, y_m - 0.1, 3.05), (3.4, y_m - 0.95, 3.65), 0.05, 0.05, "metal")
        c.boite((3.4, y_m - 0.92, 3.22), (0.06, 0.72, 0.58), "or", chanfrein=0.01)


def _b_24(c, lod):
    # Maison d'angle de rue : oriel, 2 étages, petite remise arrière en bois
    info = construire_corps_maison(c, ConfigCorps(
        cx=-0.9, lx=5.8, ly=5.2, h_rdc=2.65, h_etage=2.45, niveaux_etage=2, h_toit=3.15,
        mat_rdc="mur_brique", mat_angle="pierre_claire", mat_mur="torchis_bleu",
        mat_bois="bois", mat_volet="bois_clair", mat_toit="tuiles_ocre",
        style_fenetre="oriel", pignon_droit_ouvert=False, style_cheminee="brique_centre", details_sol="aucun",
    ))
    ajouter_grange_adossee(c, -0.9 + info["hx"], 0.4, 1.0, 2.8, 3.8, 2.5, "bois", "tuiles_ocre", style="bucher")


STYLES_MAISONS = [
    ("col_01_bourgeoise_tuiles", "Individuelle", "Bourgeoise classique · crème & tuiles", _b_01),
    ("col_02_alsacienne_ocre", "Individuelle", "Alsacienne ocre · bois rouge & oriel", _b_02),
    ("col_03_normande_chaume", "Individuelle", "Normande large · gris & chaume", _b_03),
    ("col_04_flamande_ardoise", "Individuelle", "Flamande brique · ogives & ardoise", _b_04),
    ("col_05_haute_trois_niveaux", "Individuelle", "Urbaine 3 niveaux · rose & ardoise", _b_05),
    ("col_06_tisserand_galerie", "Individuelle", "Tisserand · bleu guède & galerie vitrée", _b_06),
    ("col_07_echoppe_auvent", "Individuelle", "Échoppe · sauge & comptoir auvent", _b_07),
    ("col_08_tour_escalier", "Individuelle", "Notable · tourelle d'escalier & ardoise", _b_08),
    ("col_09_grange_chaume", "GrangeAdossee", "Logis crème + grande grange chaume", _b_09),
    ("col_10_grange_tuiles_ocre", "GrangeAdossee", "Bourguignonne ocre + grange bois", _b_10),
    ("col_11_remise_bucher", "GrangeAdossee", "Grise ardoise + bûcher ouvert", _b_11),
    ("col_12_grange_brique", "GrangeAdossee", "Brique brune + haute grange poulie", _b_12),
    ("col_13_ecurie_adossee", "GrangeAdossee", "Rose bois rouge + écurie adossée", _b_13),
    ("col_14_atelier_charron", "GrangeAdossee", "Sauge + hangar ouvert de charron", _b_14),
    ("col_15_collees_balcon_escalier", "MaisonsCollees", "Collées crème/ocre · balcon & escalier bois", _b_15),
    ("col_16_collees_escalier_pierre", "MaisonsCollees", "Collées gris/brique · balcon couvert & escalier pierre", _b_16),
    ("col_17_collees_galerie_couverte", "MaisonsCollees", "Collées rose/crème · galerie couverte commune", _b_17),
    ("col_18_collees_echoppes", "MaisonsCollees", "Collées marchandes · 2 échoppes & balcon", _b_18),
    ("col_19_trio_mitoyennes", "MaisonsCollees", "Trio de maisons collées · rue complète", _b_19),
    ("col_20_collees_passage_voute", "MaisonsCollees", "Collées à passage voûté & pont colombage", _b_20),
    ("col_21_balcon_escalier_bois", "BalconEtPlanL", "Ocre · grand balcon & escalier bois", _b_21),
    ("col_22_plan_en_L_cour", "BalconEtPlanL", "Plan en L · cour, galerie & escalier", _b_22),
    ("col_23_taverne_balcon", "BalconEtPlanL", "Taverne · bois rouge, enseigne & escalier pierre", _b_23),
    ("col_24_angle_rue_oriel", "BalconEtPlanL", "Angle 3 niveaux · bleu guède, oriel & bûcher", _b_24),
]


def fabriquer_maisons(dossier_sortie: Path, dossier_pbr: Path, samples: int = 28) -> list[dict]:
    rapport: list[dict] = []
    for nom_id, famille, titre, fn in STYLES_MAISONS:
        base.vider_scene()
        palette = preparer_palette_maisons(dossier_pbr)
        lods: list[bpy.types.Object] = []
        for k in (0, 1, 2):
            c = base.Constructeur(palette, echelle_uv=2.2, lod=k)
            fn(c, k)
            lods.append(c.finaliser(f"{nom_id}_LOD{k}"))

        chemin_fbx = dossier_sortie / f"{nom_id}.fbx"
        chemin_fbx.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.object.select_all(action="DESELECT")
        for obj in lods:
            obj.select_set(True)
        bpy.ops.export_scene.fbx(
            filepath=str(chemin_fbx.resolve()),
            use_selection=True,
            object_types={"MESH"},
            bake_space_transform=True,
            apply_scale_options="FBX_SCALE_UNITS",
            path_mode="STRIP",
            mesh_smooth_type="FACE",
        )

        # Rendu Cycles studio (samples réglable pour 24 modèles rapides et nets)
        lods[1].hide_render = True
        lods[2].hide_render = True
        chemin_rendu = dossier_sortie / "Rendus" / f"{nom_id}_rendu.png"
        # Utiliser le moteur de rendu studio de catalogue_1400 avec 28 samples adaptatifs
        ancien_rendu = base.rendre_studio
        scene = bpy.context.scene
        ancien_rendu(lods[0], chemin_rendu)

        mesure = base.verifier_fbx(chemin_fbx, nom_id)
        mesure["famille"] = famille
        mesure["titre"] = titre
        mesure["rendu"] = chemin_rendu.name
        rapport.append(mesure)
        print(f"OK {nom_id:34} tris={mesure['triangles']} dims={mesure['dimensions_m']}m", flush=True)

    (dossier_sortie / "rapport.json").write_text(
        json.dumps({"version": 1, "modeles": rapport}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return rapport


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--sortie", type=Path, required=True)
    parser.add_argument("--textures", type=Path, required=True)
    args = parser.parse_args(argv)
    fabriquer_maisons(args.sortie, args.textures)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
