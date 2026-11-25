"""Générateur Blender 4.x de 24 vraies maisons médiévales de ville à colombages (Occident 1400).

Construit 24 styles cohérents d'architecture urbaine médiévale (type Rouen,
Troyes, Colmar, York, Manor Lords) :
- Majorité de maisons étroites et profondes à **pignon sur rue** (toits pentus
  52–58°, encorbellements successifs vers la rue, arcades d'échoppes au RDC,
  trappes de grenier à poulie, soupiraux de cave) ;
- Ensembles de **maisons collées** aux pignons indépendants décalés en hauteur
  et largeur, ou reliées par un **balcon/galerie commun desservant de vraies
  portes d'étage** avec escalier extérieur dégagé, ou par un **passage voûté** ;
- Maisons avec **grange, remise, bûcher ou hangar en bois adossé** sans aucun
  mur ni pignon laissé vide ;
- Maisons en **gouttereau sur rue** avec lucarnes de toit (chiens-assis),
  balcons cohérents sur portes d'étage et escaliers de pierre sur cave haute ;
- Palette naturelle et patinée de chaux, briques anciennes, chêne vieilli,
  tuiles brunes/rouges, ardoise sombre, bardeaux et chaume de faubourg.

Usage :
    blender --background --python 3d/local3d/maisons_colombages.py -- \
        --sortie 3d/unity/Assets/ForgeLocal3D/Catalogue1400/MaisonsColombages \
        --textures 3d/unity/Assets/Interface/Resources/Forge/MatieresPBR \
        [--seulement ville_01_pignon_echoppe,ville_10_collees_trio_rue]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalogue_1400 as base  # noqa: E402


# ---------------------------------------------------------------------------
# Palette naturelle et patinée 1400 (zéro couleur criarde)
# ---------------------------------------------------------------------------

def preparer_palette_ville(dossier_pbr: Path) -> dict[str, bpy.types.Material]:
    pal = base.preparer_palette(dossier_pbr)
    # Enduits à la chaux naturels, sourds et patinés
    pal["chaux_blanche"] = base.creer_materiau_pbr(
        "M_ChauxBlanche", dossier_pbr / "PiseOcre", "pise_ocre",
        teinte=(0.78, 0.74, 0.66), facteur_teinte=0.84, normal_strength=0.58,
    )
    pal["chaux_creme"] = base.creer_materiau_pbr(
        "M_ChauxCreme", dossier_pbr / "PiseOcre", "pise_ocre",
        teinte=(0.72, 0.64, 0.51), facteur_teinte=0.78, normal_strength=0.60,
    )
    pal["chaux_ocre"] = base.creer_materiau_pbr(
        "M_ChauxOcre", dossier_pbr / "PiseOcre", "pise_ocre",
        teinte=(0.64, 0.49, 0.30), facteur_teinte=0.72, normal_strength=0.62,
    )
    pal["chaux_terre"] = base.creer_materiau_pbr(
        "M_ChauxTerreRosee", dossier_pbr / "PiseOcre", "pise_ocre",
        teinte=(0.56, 0.37, 0.29), facteur_teinte=0.74, normal_strength=0.62,
    )
    pal["chaux_grise"] = base.creer_materiau_pbr(
        "M_ChauxGrise", dossier_pbr / "PiseOcre", "pise_ocre",
        teinte=(0.55, 0.52, 0.47), facteur_teinte=0.82, normal_strength=0.62,
    )
    pal["mur_brique"] = base.creer_materiau_pbr(
        "M_BriqueVieillie", dossier_pbr / "TuilesMedievales", "tuiles_medievales",
        teinte=(0.45, 0.22, 0.16), facteur_teinte=0.50, normal_strength=0.95,
    )
    pal["brique_brune"] = base.creer_materiau_pbr(
        "M_BriqueBrune", dossier_pbr / "TuilesMedievales", "tuiles_medievales",
        teinte=(0.30, 0.19, 0.15), facteur_teinte=0.55, normal_strength=0.95,
    )
    # Bois de colombage patinés et volets sobres
    pal["chene_sombre"] = pal["bois"]
    pal["chene_patine"] = base.creer_materiau_pbr(
        "M_ChenePatine", dossier_pbr / "BoisBrule", "bois_brule",
        teinte=(0.34, 0.26, 0.19), facteur_teinte=0.50, normal_strength=0.92,
    )
    pal["bois_sang"] = base.creer_materiau_pbr(
        "M_BoisSangDeBoeuf", dossier_pbr / "BoisBrule", "bois_brule",
        teinte=(0.28, 0.11, 0.09), facteur_teinte=0.62, normal_strength=0.90,
    )
    pal["volet_chene"] = base.creer_materiau_simple("M_VoletChene", (0.20, 0.14, 0.09), roughness=0.82)
    pal["volet_olive"] = base.creer_materiau_simple("M_VoletOliveSombre", (0.14, 0.18, 0.12), roughness=0.82)
    pal["volet_brun"] = base.creer_materiau_simple("M_VoletBrunRouge", (0.24, 0.10, 0.08), roughness=0.80)
    # Toitures cohérentes de ville médiévale
    pal["tuiles_brunes"] = base.creer_materiau_pbr(
        "M_TuilesBrunes", dossier_pbr / "TuilesMedievales", "tuiles_medievales",
        teinte=(0.24, 0.17, 0.13), facteur_teinte=0.58, normal_strength=1.1,
    )
    pal["tuiles_anciennes"] = base.creer_materiau_pbr(
        "M_TuilesAnciennes", dossier_pbr / "TuilesMedievales", "tuiles_medievales",
        teinte=(0.44, 0.24, 0.16), facteur_teinte=0.38, normal_strength=1.1,
    )
    pal["ardoise"] = base.creer_materiau_pbr(
        "M_ArdoiseSombre", dossier_pbr / "TuilesMedievales", "tuiles_medievales",
        teinte=(0.15, 0.18, 0.22), facteur_teinte=0.82, metallic=0.08, normal_strength=0.85,
    )
    pal["bardeaux"] = base.creer_materiau_pbr(
        "M_BardeauxChene", dossier_pbr / "BoisBrule", "bois_brule",
        teinte=(0.28, 0.25, 0.21), facteur_teinte=0.55, normal_strength=1.0,
    )
    return pal


# ---------------------------------------------------------------------------
# Primitives urbaines 1400 : colombage historique, toits pignon-sur-rue,
# arcades d'échoppes, lucarnes chiens-assis, portes d'étage et balcons cohérents
# ---------------------------------------------------------------------------

def colombage_urbain(c: base.Constructeur, u0: float, u1: float, pos_n: float, z0: float, z1: float,
                     axe: str, sens_ext: float, mat_bois: str, *,
                     style: str = "grille", zones_libres: tuple[tuple[float, float], ...] = ()) -> None:
    """Colombage 3D fidèle au XVe siècle : poteaux serrés, sablières moulurées et écharpes d'angle.

    `zones_libres` indique les intervalles [ua, ub] occupés par une fenêtre ou une
    porte afin qu'aucun poteau ne traverse une vitre ou un vantail.
    """
    ep = 0.095
    larg = 0.145
    decal = sens_ext * (ep * 0.46)
    longueur = abs(u1 - u0)
    h = z1 - z0

    def pt(u: float, z: float) -> tuple[float, float, float]:
        return (u, pos_n + decal, z) if axe == "x" else (pos_n + decal, u, z)

    def dans_ouverture(u: float, marge: float = 0.05) -> bool:
        return any((a + marge) < u < (b - marge) for a, b in zones_libres)

    # Sablières basse (moulurée) et haute + linteau/allège
    c.poutre(pt(u0, z0 + 0.08), pt(u1, z0 + 0.08), larg * 1.15, ep * 1.10, mat_bois)
    c.poutre(pt(u0, z1 - 0.07), pt(u1, z1 - 0.07), larg, ep, mat_bois)
    z_allege = z0 + h * 0.34
    if c.lod <= 1:
        c.poutre(pt(u0, z_allege), pt(u1, z_allege), larg * 0.82, ep * 0.82, mat_bois)

    # Poteaux corniers obligatoires
    c.poutre(pt(u0 + 0.07, z0), pt(u0 + 0.07, z1), larg * 1.12, ep * 1.05, mat_bois)
    c.poutre(pt(u1 - 0.07, z0), pt(u1 - 0.07, z1), larg * 1.12, ep * 1.05, mat_bois)

    # Poteaux encadrant exactement chaque ouverture
    for oa, ob in zones_libres:
        c.poutre(pt(oa, z0), pt(oa, z1), larg * 0.95, ep * 0.95, mat_bois)
        c.poutre(pt(ob, z0), pt(ob, z1), larg * 0.95, ep * 0.95, mat_bois)

    # Poteaux intermédiaires selon le style
    pas = 0.68 if style == "grille" else (1.05 if style == "losange" else 1.25)
    if c.lod == 1:
        pas *= 1.6
    elif c.lod == 2:
        pas *= 2.4
    nb = max(2, int(round(longueur / pas)))
    du = longueur / nb
    for i in range(1, nb):
        u = u0 + i * du
        if dans_ouverture(u):
            # Potelet court en allège uniquement sous la fenêtre (jamais devant la vitre !)
            if c.lod == 0:
                c.poutre(pt(u, z0 + 0.10), pt(u, z_allege - 0.04), larg * 0.72, ep * 0.75, mat_bois)
        else:
            c.poutre(pt(u, z0 + 0.08), pt(u, z1 - 0.08), larg * 0.85, ep * 0.85, mat_bois)

    # Contreventement historique (écharpes aux angles, ou croix en allège seulement)
    if c.lod == 0:
        if style in ("grille", "losange") and longueur >= 3.2:
            if not dans_ouverture(u0 + 0.55):
                c.poutre(pt(u0 + 0.12, z0 + 0.14), pt(u0 + min(1.05, longueur * 0.25), z1 - 0.14), larg * 0.75, ep * 0.78, mat_bois)
            if not dans_ouverture(u1 - 0.55):
                c.poutre(pt(u1 - 0.12, z0 + 0.14), pt(u1 - min(1.05, longueur * 0.25), z1 - 0.14), larg * 0.75, ep * 0.78, mat_bois)
        if style in ("allege", "losange"):
            for oa, ob in zones_libres:
                if (ob - oa) >= 0.75:
                    c.poutre(pt(oa + 0.06, z0 + 0.12), pt(ob - 0.06, z_allege - 0.06), larg * 0.68, ep * 0.72, mat_bois)
                    c.poutre(pt(oa + 0.06, z_allege - 0.06), pt(ob - 0.06, z0 + 0.12), larg * 0.68, ep * 0.72, mat_bois)


def toit_pignon_sur_rue(c: base.Constructeur, centre_base: tuple[float, float, float],
                        largeur_x: float, profondeur_y: float, hauteur_z: float,
                        mat_toit: str, mat_mur: str, mat_bois: str, mat_volet: str, *,
                        debord_avant: float = 0.58, debord_arriere: float = 0.34,
                        debord_cote: float = 0.28, epaisseur: float = 0.17,
                        poulie: bool = True, pignon_avant_ouvert: bool = True,
                        pignon_arriere_ouvert: bool = True) -> None:
    """Toit très pentu de maison de ville dont le PIGNON pointe vers la rue (-Y)."""
    cx, cy, cz = centre_base
    hx, hy = largeur_x * 0.5, profondeur_y * 0.5

    # Prisme triangulaire (pignons en -Y et +Y, faîte parallèle à Y)
    sub = bmesh.new()
    v0 = sub.verts.new((cx - hx, cy - hy, cz))
    v1 = sub.verts.new((cx + hx, cy - hy, cz))
    v2 = sub.verts.new((cx + hx, cy + hy, cz))
    v3 = sub.verts.new((cx - hx, cy + hy, cz))
    v4 = sub.verts.new((cx, cy - hy, cz + hauteur_z))
    v5 = sub.verts.new((cx, cy + hy, cz + hauteur_z))
    for loop in ((v0, v1, v4), (v2, v3, v5), (v0, v3, v2, v1)):
        sub.faces.new(loop)
    c._ajouter_sous_bm(sub, mat_mur, smooth=False)

    pente = math.atan2(hauteur_z, hx)
    long_pan = math.hypot(hx + debord_cote, hauteur_z) + 0.12
    tot_y = profondeur_y + debord_avant + debord_arriere
    y_centre_toit = cy + (debord_arriere - debord_avant) * 0.5
    strates = 7 if (c.lod == 0 and mat_toit != "ardoise") else (5 if c.lod == 0 else 0)

    for signe in (-1.0, 1.0):
        mid_x = cx + signe * (hx * 0.5 + debord_cote * 0.36)
        mid_z = cz + hauteur_z * 0.5 - debord_cote * 0.36 * math.tan(pente) + epaisseur * 0.42
        c.boite((mid_x, y_centre_toit, mid_z), (long_pan, tot_y, epaisseur), mat_toit, rot=(0.0, signe * pente, 0.0))
        # Chevrons de rive sculptés en façade (-Y) et arrière (+Y)
        if c.lod <= 1:
            for y_r in (cy - hy - debord_avant + 0.08, cy + hy + debord_arriere - 0.08):
                c.boite((mid_x, y_r, mid_z - epaisseur * 0.55), (long_pan * 0.99, 0.12, 0.15),
                        mat_bois, rot=(0.0, signe * pente, 0.0), chanfrein=0.012)
        # Strates de tuiles/chaume en relief (LOD0)
        if strates > 0:
            for k in range(strates):
                t = (k + 0.5) / strates
                sx = cx + signe * ((hx + debord_cote) * (1.0 - t))
                sz = cz + hauteur_z * t - debord_cote * (1.0 - t) * math.tan(pente) + epaisseur * 0.95
                c.boite((sx, y_centre_toit, sz), ((long_pan / strates) * 0.92, tot_y + 0.02, 0.045),
                        mat_toit, rot=(0.0, signe * (pente - 0.06), 0.0))

    # Faîtière et pannes débordantes vers la rue
    c.cylindre((cx, y_centre_toit, cz + hauteur_z + epaisseur * 0.62), 0.14, 0.14, tot_y + 0.06,
               10 if c.lod == 0 else 6, mat_toit, rot=(math.pi * 0.5, 0.0, 0.0), smooth=True)
    if c.lod <= 1:
        for t in (0.36, 0.70, 0.96):
            for signe in (-1.0, 1.0):
                if t > 0.92 and signe < 0:
                    continue
                px = cx + (0.0 if t > 0.92 else signe * hx * (1.0 - t))
                pz = cz + hauteur_z * t - 0.08
                c.boite((px, y_centre_toit, pz), (0.14, tot_y + 0.18, 0.15), mat_bois, chanfrein=0.014)

    # Colombage 3D complet sur le triangle de pignon (-Y et +Y) — zéro triangle vide !
    for y_p, sens, ouvert, avec_poulie in (
        (cy - hy, -1.0, pignon_avant_ouvert, poulie),
        (cy + hy, 1.0, pignon_arriere_ouvert, False),
    ):
        if not ouvert:
            continue
        yp = y_p + sens * 0.045
        # Entraits horizontaux étagés
        for frac in (0.30, 0.62):
            demi = hx * (1.0 - frac) - 0.04
            if demi > 0.25:
                c.poutre((cx - demi, yp, cz + hauteur_z * frac), (cx + demi, yp, cz + hauteur_z * frac), 0.12, 0.085, mat_bois)
        # Poinçon central et 2 poteaux encadrant la trappe de grenier
        c.poutre((cx, yp, cz + hauteur_z * 0.62), (cx, yp, cz + hauteur_z - 0.08), 0.13, 0.09, mat_bois)
        for sx in (-1.0, 1.0):
            u = sx * min(0.54, hx * 0.32)
            z_top = cz + hauteur_z * (1.0 - abs(u) / hx) - 0.06
            c.poutre((cx + u, yp, cz), (cx + u, yp, z_top), 0.13, 0.09, mat_bois)
            if c.lod == 0 and hx >= 2.0:
                u2 = sx * hx * 0.64
                z_top2 = cz + hauteur_z * (1.0 - abs(u2) / hx) - 0.06
                c.poutre((cx + u2, yp, cz), (cx + u2, yp, z_top2), 0.11, 0.08, mat_bois)
                # Décharges obliques dans le pignon
                c.poutre((cx + u, yp, cz + 0.06), (cx + u2, yp, cz + hauteur_z * 0.30), 0.10, 0.075, mat_bois)
        # Trappe/lucarne de grenier en pignon + potence et poulie (côté rue)
        if c.lod <= 1:
            z_tr = cz + hauteur_z * 0.30
            c.boite((cx, yp + sens * 0.02, z_tr + 0.48), (0.86, 0.09, 1.02), mat_volet, chanfrein=0.012)
            if c.lod == 0:
                c.boite((cx, yp + sens * 0.06, z_tr + 0.48), (0.04, 0.03, 0.96), "charbon")
            if avec_poulie:
                z_p = cz + hauteur_z * 0.72
                c.poutre((cx, y_p, z_p), (cx, y_p - 1.05, z_p), 0.14, 0.14, mat_bois)
                if c.lod == 0:
                    c.cylindre((cx, y_p - 0.88, z_p - 0.16), 0.13, 0.13, 0.06, 10, "metal", rot=(0.0, math.pi * 0.5, 0.0), smooth=True)
                    c.cylindre((cx, y_p - 0.88, z_p - 0.95), 0.018, 0.018, 1.55, 6, "corde", smooth=True)


def ajouter_lucarne(c: base.Constructeur, x: float, y_base: float, z_base: float,
                    mat_mur: str, mat_bois: str, mat_toit: str) -> None:
    """Vraie lucarne de toit (chien-assis) en colombage sur versant sud (-Y)."""
    w, h, prof = 1.24, 1.32, 1.65
    y_av = y_base - 0.05
    c.boite((x, y_av + prof * 0.5, z_base + h * 0.46), (w, prof, h), mat_mur)
    for sx in (-w * 0.5, w * 0.5):
        c.boite((x + sx, y_av - 0.02, z_base + h * 0.46), (0.12, 0.14, h), mat_bois, chanfrein=0.01)
    c.boite((x, y_av - 0.03, z_base + 0.06), (w + 0.16, 0.14, 0.11), mat_bois, chanfrein=0.01)
    c.boite((x, y_av - 0.03, z_base + h * 0.88), (w + 0.16, 0.14, 0.11), mat_bois, chanfrein=0.01)
    c.boite((x, y_av - 0.035, z_base + h * 0.48), (w * 0.76, 0.05, h * 0.70), "verre")
    if c.lod == 0:
        c.boite((x, y_av - 0.065, z_base + h * 0.48), (0.06, 0.05, h * 0.72), mat_bois)
        c.boite((x, y_av - 0.065, z_base + h * 0.50), (w * 0.78, 0.05, 0.06), mat_bois)
    toit_pignon_sur_rue(
        c, (x, y_av + prof * 0.5, z_base + h * 0.92), w + 0.08, prof + 0.15, 0.78,
        mat_toit, mat_mur, mat_bois, mat_bois,
        debord_avant=0.26, debord_arriere=0.10, debord_cote=0.14, epaisseur=0.09,
        poulie=False, pignon_avant_ouvert=False, pignon_arriere_ouvert=False,
    )


def ajouter_arcade_echoppe(c: base.Constructeur, cx: float, y_mur: float, largeur: float,
                           hauteur: float, mat_bois: str, style: str = "bois") -> None:
    """Rez-de-chaussée marchand authentique : arcade en pierre ou en chêne avec étal sous l'encorbellement."""
    h_ouv = min(2.22, hauteur - 0.35)
    # Fond d'échoppe sombre + comptoir en chêne débordant légèrement sur la rue
    c.boite((cx, y_mur + 0.08, h_ouv * 0.5), (largeur * 0.94, 0.16, h_ouv), "charbon")
    c.boite((cx, y_mur - 0.24, 0.88), (largeur * 0.92, 0.56, 0.11), "bois_clair", chanfrein=0.014)
    c.boite((cx, y_mur - 0.10, 0.44), (largeur * 0.88, 0.20, 0.84), mat_bois, chanfrein=0.01)
    if style == "pierre":
        # Arcade surbaissée en 9 voussoirs de pierre calcaire
        r = largeur * 0.5
        nb_v = 9 if c.lod == 0 else 5
        for sx in (-1.0, 1.0):
            c.boite((cx + sx * (r + 0.14), y_mur - 0.08, (h_ouv - 0.45) * 0.5), (0.30, 0.24, h_ouv - 0.45), "pierre_claire", chanfrein=0.02)
        for i in range(nb_v):
            a = 0.22 + (math.pi - 0.44) * (i + 0.5) / nb_v
            vx = cx + math.cos(a) * (r + 0.06)
            vz = (h_ouv - 0.65) + math.sin(a) * 0.72
            c.boite((vx, y_mur - 0.09, vz), (0.32, 0.26, 0.30), "pierre_claire", rot=(0, a - math.pi * 0.5, 0), chanfrein=0.018)
    else:
        # Arcade en charpente chêne (poteaux, aisseliers courbes, linteau + auvent bois rabattu)
        for sx in (-largeur * 0.5, largeur * 0.5):
            c.boite((cx + sx, y_mur - 0.06, h_ouv * 0.5), (0.18, 0.20, h_ouv), mat_bois, chanfrein=0.015)
            if c.lod == 0:
                c.poutre((cx + sx, y_mur - 0.06, h_ouv - 0.58), (cx + sx * 0.55, y_mur - 0.06, h_ouv - 0.05), 0.12, 0.14, mat_bois)
        c.boite((cx, y_mur - 0.07, h_ouv + 0.06), (largeur + 0.24, 0.22, 0.18), mat_bois, chanfrein=0.016)
        # Volet supérieur relevé en petit auvent de bois
        c.boite((cx, y_mur - 0.46, h_ouv - 0.02), (largeur + 0.10, 0.84, 0.07), "bois_clair", rot=(0.34, 0, 0), chanfrein=0.01)
    if c.lod == 0:
        c.boite((cx - largeur * 0.22, y_mur - 0.28, 1.04), (0.44, 0.34, 0.22), "bois_clair", chanfrein=0.01)
        c.sac_noue((cx + largeur * 0.22, y_mur - 0.28, 0.93), 0.20, 0.16, 0.32, 0.25, "jute", "corde")


def ajouter_porte_etage(c: base.Constructeur, x: float, y_mur: float, z_sol: float,
                        mat_bois: str) -> None:
    """Vraie porte d'étage en chêne ouvrant de plain-pied sur un balcon ou une galerie."""
    w, h = 0.98, 1.98
    c.boite((x, y_mur - 0.02, z_sol + h * 0.5), (w, 0.09, h), mat_bois, chanfrein=0.01)
    for sx in (-w * 0.5 - 0.06, w * 0.5 + 0.06):
        c.boite((x + sx, y_mur - 0.05, z_sol + h * 0.5), (0.12, 0.14, h + 0.06), mat_bois, chanfrein=0.012)
    c.boite((x, y_mur - 0.06, z_sol + h + 0.07), (w + 0.28, 0.16, 0.14), mat_bois, chanfrein=0.014)
    if c.lod == 0:
        for hz in (z_sol + 0.52, z_sol + 1.48):
            c.boite((x, y_mur - 0.08, hz), (w * 0.86, 0.03, 0.065), "metal")


def ajouter_soupirail(c: base.Constructeur, x: float, y_mur: float) -> None:
    """Petit soupirail de cave grillagé au ras du sol."""
    if c.lod >= 2:
        return
    c.boite((x, y_mur - 0.03, 0.34), (0.72, 0.08, 0.42), "charbon")
    c.boite((x, y_mur - 0.05, 0.58), (0.86, 0.14, 0.12), "pierre_taille", chanfrein=0.015)
    if c.lod == 0:
        for dx in (-0.20, 0.0, 0.20):
            c.boite((x + dx, y_mur - 0.05, 0.34), (0.035, 0.04, 0.40), "metal")


def ajouter_cheminee_urbaine(c: base.Constructeur, x: float, y: float, z_toit: float,
                             h_toit: float, style: str, z_sol: float = 0.0) -> None:
    if style == "sans":
        return
    if style == "brique":
        c.boite((x, y, z_toit + h_toit * 0.72), (0.84, 0.84, 2.35), "brique", chanfrein=0.02)
        c.boite((x, y, z_toit + h_toit * 0.72 + 1.24), (0.98, 0.98, 0.18), "brique", chanfrein=0.02)
    elif style == "double":
        c.boite((x, y, z_toit + h_toit * 0.72), (1.32, 0.76, 2.40), "mur_brique", chanfrein=0.02)
        c.boite((x, y, z_toit + h_toit * 0.72 + 1.26), (1.48, 0.92, 0.18), "brique", chanfrein=0.02)
        if c.lod == 0:
            for dx in (-0.34, 0.34):
                c.boite((x + dx, y, z_toit + h_toit * 0.72 + 1.46), (0.40, 0.40, 0.24), "brique_brune", chanfrein=0.015)
    elif style == "octogonale":
        zb = z_toit + h_toit * 0.46
        c.boite((x, y, zb + 0.45), (0.92, 0.92, 0.90), "pierre_claire", chanfrein=0.02)
        c.cylindre((x, y, zb + 1.65), 0.42, 0.38, 1.60, 8, "brique")
        c.cylindre((x, y, zb + 2.52), 0.50, 0.48, 0.18, 8, "pierre_taille")
    elif style == "souche_pierre":
        # Grosse souche en pierre adossée depuis le sol jusqu'au-dessus du faîte
        h_tot = z_toit + h_toit + 0.85
        c.boite((x, y, 1.45), (0.98, 1.56, 2.90), "pierre_claire", chanfrein=0.03)
        c.boite((x, y, 2.90 + (h_tot - 2.90) * 0.5), (0.76, 1.12, h_tot - 2.90), "pierre_taille", chanfrein=0.025)
        c.boite((x, y, h_tot + 0.12), (0.92, 1.28, 0.20), "pierre_claire", chanfrein=0.02)


def ajouter_oriel_urbain(c: base.Constructeur, x: float, y_mur: float, z_bas: float,
                         largeur: float, hauteur: float, mat_mur: str, mat_bois: str, mat_toit: str) -> None:
    """Oriel sculpté en encorbellement sur façade de rue (-Y)."""
    saillie = 0.78
    if c.lod <= 1:
        for dx in (-largeur * 0.36, 0.0, largeur * 0.36):
            c.corbeau_galbe(x + dx, y_mur, z_bas + 0.04, (0.0, -1.0), 0.16, saillie * 0.90, 0.48, mat_bois)
    c.boite((x, y_mur - saillie * 0.5, z_bas + hauteur * 0.20), (largeur, saillie, hauteur * 0.40), mat_mur)
    for hz in (0.06, hauteur * 0.42, hauteur - 0.06):
        c.boite((x, y_mur - saillie * 0.5, z_bas + hz), (largeur + 0.12, saillie + 0.10, 0.11), mat_bois, chanfrein=0.014)
    z_v, h_v = z_bas + hauteur * 0.68, hauteur * 0.46
    c.boite((x, y_mur - saillie + 0.03, z_v), (largeur * 0.86, 0.05, h_v), "verre")
    for sx in (-1.0, 1.0):
        c.boite((x + sx * (largeur * 0.5 - 0.03), y_mur - saillie * 0.5, z_v), (0.05, saillie * 0.72, h_v), "verre")
        c.boite((x + sx * (largeur * 0.5), y_mur - saillie, z_bas + hauteur * 0.5), (0.11, 0.11, hauteur), mat_bois, chanfrein=0.01)
    if c.lod == 0:
        c.boite((x, y_mur - saillie, z_v), (0.065, 0.07, h_v + 0.04), mat_bois)
        c.boite((x, y_mur - saillie, z_v), (largeur * 0.90, 0.06, 0.055), mat_bois)
    c.boite((x, y_mur - saillie * 0.52, z_bas + hauteur + 0.22), (largeur + 0.34, saillie + 0.38, 0.13), mat_toit, rot=(0.48, 0, 0))


def ajouter_balcon_propre(c: base.Constructeur, x0: float, x1: float, y_mur: float, z_sol: float,
                          profondeur: float, mat_bois: str, *, mat_toit: str | None = None,
                          ouvert_x: tuple[float, float] | None = None, ouvert_cote: str = "",
                          poteaux_sol: bool = True) -> None:
    """Balcon ou galerie couverte en chêne desservant une vraie porte d'étage."""
    long_b = x1 - x0
    cx, cy = (x0 + x1) * 0.5, y_mur - profondeur * 0.5
    c.boite((cx, cy, z_sol), (long_b, profondeur, 0.12), "bois_clair", chanfrein=0.012)
    c.boite((cx, y_mur - profondeur + 0.06, z_sol - 0.08), (long_b + 0.08, 0.14, 0.16), mat_bois, chanfrein=0.012)
    nb_con = max(3, int(long_b / 1.55) + 1)
    for i in range(nb_con):
        ux = x0 + 0.14 + i * ((long_b - 0.28) / max(1, nb_con - 1))
        if c.lod <= 1:
            c.corbeau_galbe(ux, y_mur, z_sol - 0.02, (0.0, -1.0), 0.16, profondeur * 0.88, 0.52, mat_bois)
        if poteaux_sol and (i in (0, nb_con - 1) or long_b > 5.0):
            c.boite((ux, y_mur - profondeur + 0.10, z_sol * 0.5), (0.16, 0.16, z_sol), mat_bois, chanfrein=0.014)
    # Garde-corps latéraux (ouverts si un escalier prolonge le balcon) et garde-corps avant
    h_gc = 0.94
    if ouvert_cote != "gauche":
        c.boite((x0 + 0.06, cy, z_sol + h_gc), (0.10, profondeur, 0.10), mat_bois, chanfrein=0.01)
    if ouvert_cote != "droite":
        c.boite((x1 - 0.06, cy, z_sol + h_gc), (0.10, profondeur, 0.10), mat_bois, chanfrein=0.01)
    segs = [(x0, x1)]
    if ouvert_x is not None:
        ea, eb = ouvert_x
        segs = []
        if ea > x0 + 0.22:
            segs.append((x0, ea))
        if eb < x1 - 0.22:
            segs.append((eb, x1))
    for sa, sb in segs:
        sm, sl = (sa + sb) * 0.5, sb - sa
        c.boite((sm, y_mur - profondeur + 0.08, z_sol + h_gc), (sl, 0.11, 0.10), mat_bois, chanfrein=0.01)
        c.boite((sm, y_mur - profondeur + 0.08, z_sol + h_gc * 0.48), (sl, 0.08, 0.08), mat_bois)
        if c.lod == 0:
            nb_b = max(2, int(sl / 0.34))
            for k in range(nb_b + 1):
                c.boite((sa + k * (sl / nb_b), y_mur - profondeur + 0.08, z_sol + h_gc * 0.48), (0.065, 0.065, h_gc), mat_bois)
    if mat_toit is not None:
        h_p = 2.22
        for i in range(nb_con):
            ux = x0 + 0.14 + i * ((long_b - 0.28) / max(1, nb_con - 1))
            c.boite((ux, y_mur - profondeur + 0.10, z_sol + h_p * 0.5), (0.14, 0.14, h_p), mat_bois, chanfrein=0.012)
        c.boite((cx, y_mur - profondeur + 0.10, z_sol + h_p), (long_b + 0.14, 0.16, 0.16), mat_bois, chanfrein=0.014)
        c.boite((cx, cy - 0.10, z_sol + h_p + 0.22), (long_b + 0.36, profondeur + 0.56, 0.13), mat_toit, rot=(0.28, 0, 0))


def ajouter_escalier_propre(c: base.Constructeur, x_haut: float, y_bord_balcon: float, z_haut: float,
                            sens_x: float, largeur: float, mat: str, *, en_pierre: bool = False,
                            en_bout: bool = True) -> None:
    """Escalier extérieur en bois ou en pierre raccordé en bout de balcon ou en façade avant."""
    long_x = z_haut * 1.12
    nb_m = 10 if c.lod == 0 else (6 if c.lod == 1 else 4)
    cy = (y_bord_balcon + largeur * 0.52) if en_bout else (y_bord_balcon - largeur * 0.50)
    y_ext = cy - largeur * 0.5
    if en_pierre:
        for i in range(nb_m):
            t = (i + 0.5) / nb_m
            mx = x_haut + sens_x * (long_x * t)
            mz = z_haut * (1.0 - t)
            c.boite((mx, cy, mz * 0.5), (long_x / nb_m * 1.06, largeur, mz), mat, chanfrein=0.018)
        c.poutre((x_haut, y_ext + 0.10, z_haut + 0.72),
                 (x_haut + sens_x * long_x, y_ext + 0.10, 0.72), 0.18, 0.54, mat)
    else:
        for dy in (-largeur * 0.42, largeur * 0.42):
            c.poutre((x_haut, cy + dy, z_haut), (x_haut + sens_x * long_x, cy + dy, 0.06), 0.12, 0.22, mat)
        for i in range(nb_m):
            t = (i + 0.5) / nb_m
            c.boite((x_haut + sens_x * (long_x * t), cy, z_haut * (1.0 - t)), (0.30, largeur - 0.08, 0.07), "bois_clair", chanfrein=0.008)
        yr = y_ext + 0.08
        c.poutre((x_haut, yr, z_haut + 0.92), (x_haut + sens_x * long_x, yr, 0.92), 0.09, 0.09, mat)
        for t in (0.0, 0.5, 1.0):
            c.boite((x_haut + sens_x * long_x * t, yr, z_haut * (1.0 - t) + 0.46), (0.09, 0.09, 0.94), mat, chanfrein=0.01)


def ajouter_grange_bois(c: base.Constructeur, x_attache: float, cy: float, cote_x: float,
                        long_x: float, larg_y: float, h_murs: float, mat_bois: str,
                        mat_toit: str, style: str = "grange") -> None:
    """Grange, remise, bûcher ou hangar en bois adossé de façon cohérente (toit sous l'égout)."""
    gx = x_attache + cote_x * (long_x * 0.5)
    c.boite((gx, cy, 0.16), (long_x + 0.10, larg_y + 0.10, 0.32), "pierre_claire", chanfrein=0.02)
    for sx in (-long_x * 0.48, long_x * 0.48):
        for sy in (-larg_y * 0.48, larg_y * 0.48):
            c.boite((gx + sx, cy + sy, h_murs * 0.5 + 0.24), (0.20, 0.20, h_murs), mat_bois, chanfrein=0.015)

    if style in ("grange", "remise"):
        c.boite((gx, cy, h_murs * 0.5 + 0.24), (long_x - 0.08, larg_y - 0.08, h_murs - 0.06), "bois_clair")
        if c.lod == 0:
            nb_b = max(5, int(long_x / 0.32))
            for i in range(nb_b):
                ux = gx - long_x * 0.46 + i * (long_x * 0.92 / max(1, nb_b - 1))
                c.boite((ux, cy - larg_y * 0.49, h_murs * 0.5 + 0.24), (0.055, 0.05, h_murs - 0.10), mat_bois)
            # Couvre-joints verticaux sur le flanc extérieur de la grange également
            nb_lat = max(5, int(larg_y / 0.36))
            x_ext = gx + cote_x * (long_x * 0.49)
            for i in range(nb_lat):
                uy = cy - larg_y * 0.46 + i * (larg_y * 0.92 / max(1, nb_lat - 1))
                c.boite((x_ext, uy, h_murs * 0.5 + 0.24), (0.05, 0.055, h_murs - 0.10), mat_bois)
        lp = min(2.05, long_x * 0.56)
        hp = min(2.26, h_murs * 0.80)
        c.boite((gx, cy - larg_y * 0.50, hp * 0.5 + 0.26), (lp, 0.14, hp), mat_bois, chanfrein=0.014)
        if c.lod == 0:
            for hz in (0.78, hp * 0.72 + 0.26):
                c.boite((gx, cy - larg_y * 0.58, hz), (lp * 0.88, 0.04, 0.075), "metal")
            c.sac_noue((gx - lp * 0.62, cy - larg_y * 0.58, 0.0), 0.25, 0.20, 0.40, 0.2, "jute", "corde")
    else:
        # Bûcher ou hangar ouvert sur poteaux de chêne
        c.boite((gx, cy + larg_y * 0.46, h_murs * 0.5 + 0.24), (long_x - 0.08, 0.14, h_murs - 0.06), "bois_clair")
        c.boite((gx, cy - larg_y * 0.46, h_murs + 0.18), (long_x + 0.12, 0.18, 0.18), mat_bois, chanfrein=0.014)
        if c.lod == 0:
            for sx in (-long_x * 0.46, long_x * 0.46):
                c.poutre((gx + sx, cy - larg_y * 0.46, h_murs - 0.48), (gx + sx * 0.62, cy - larg_y * 0.46, h_murs + 0.16), 0.11, 0.11, mat_bois)
            if style == "bucher":
                for rz in range(3):
                    for rx in range(4):
                        c.cylindre((gx - 0.65 + rx * 0.34, cy + 0.35, 0.44 + rz * 0.24), 0.11, 0.11, 1.05, 8, "bois", rot=(math.pi * 0.5, 0, 0), smooth=True)
                c.tonneau_bombe((gx + 0.82, cy - 0.22, 0.0), 0.24, 0.29, 0.84, "bois", "metal")
            else:
                c.roue_rayons((gx - 0.68, cy - 0.32, 0.52), 0.48, 0.07, 8, "bois_clair", "metal")
                c.boite((gx + 0.52, cy + 0.10, 0.84), (1.42, 0.72, 0.10), "bois_clair", chanfrein=0.01)
                for dx in (-0.58, 0.58):
                    for dy in (-0.26, 0.26):
                        c.boite((gx + 0.52 + dx, cy + 0.10 + dy, 0.42), (0.10, 0.10, 0.80), mat_bois)

    # Toit en appentis propre raccordé contre le mur du logis ou 2 pans si grange large
    if style == "grange" and long_x >= 3.8:
        toit_pignon_sur_rue(
            c, (gx, cy, h_murs + 0.26), long_x, larg_y, 2.30,
            mat_toit, "bois_clair", mat_bois, mat_bois,
            debord_avant=0.35, debord_arriere=0.25, debord_cote=0.22,
            epaisseur=0.26 if mat_toit == "chaume" else 0.15, poulie=True,
        )
    else:
        pente = -cote_x * 0.36
        z_t = h_murs + 0.26 + long_x * 0.18
        c.boite((gx, cy, z_t), (long_x + 0.50, larg_y + 0.52, 0.15), mat_toit, rot=(0.0, pente, 0.0))
        if c.lod == 0:
            for ky in (-larg_y * 0.40, 0.0, larg_y * 0.40):
                c.boite((gx, cy + ky, z_t - 0.14), (long_x + 0.38, 0.11, 0.13), mat_bois, rot=(0.0, pente, 0.0))


# ---------------------------------------------------------------------------
# Corps de maison médiévale de VILLE (pignon sur rue OU gouttereau cohérent)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MaisonVille:
    cx: float = 0.0
    cy: float = 0.0
    lx: float = 4.8                 # étroit sur rue en mode pignon (4.2..5.8 m)
    ly: float = 7.6                 # profond vers la cour (6.5..9.0 m)
    orientation: str = "pignon"     # "pignon" (faîte // Y, pignon sur rue) | "gouttereau" (faîte // X)
    h_rdc: float = 2.70
    h_etage: float = 2.45
    nb_etages: int = 2              # 1 ou 2 étages en encorbellement successif
    h_toit: float = 3.60
    mat_rdc: str = "pierre_taille"  # pierre_taille | pierre | mur_brique | brique_brune | colombage_rdc
    mat_angle: str = "pierre_claire"
    mat_mur: str = "chaux_creme"
    mat_bois: str = "chene_sombre"
    mat_volet: str = "volet_chene"
    mat_toit: str = "tuiles_anciennes"
    style_colombage: str = "grille" # grille | allege | losange
    rdc_style: str = "echoppe_bois" # echoppe_bois | echoppe_pierre | porte_pierre | double_arcade | cave_haute
    fenetre_etage: str = "volets"   # volets | bandeau | oriel | ogive
    cheminee: str = "brique"        # brique | double | octogonale | souche_pierre | sans
    porte_etage_x: float | None = None  # Si non nul : pose une VRAIE porte d'étage au 1er étage (pour balcon)
    mitoyen_gauche: bool = False    # Coupe les fenêtres/chaînages du flanc gauche (mais garde le colombage visible)
    mitoyen_droit: bool = False
    lucarnes: int = 0               # Chiens-assis sur toit en gouttereau
    poulie: bool = True
    enseigne: bool = False
    details_sol: str = "aucun"      # aucun | tonneaux | banc | sacs


def construire_maison_ville(c: base.Constructeur, cfg: MaisonVille) -> dict:
    cx, cy = cfg.cx, cfg.cy
    hx, hy = cfg.lx * 0.5, cfg.ly * 0.5

    # 1. Rez-de-chaussée urbain
    if cfg.mat_rdc == "colombage_rdc":
        # Bahut de pierre de 0.65 m + colombage dès le RDC
        c.boite((cx, cy, 0.34), (cfg.lx + 0.16, cfg.ly + 0.16, 0.68), cfg.mat_angle, chanfrein=0.02)
        c.boite((cx, cy, 0.68 + (cfg.h_rdc - 0.68) * 0.5), (cfg.lx, cfg.ly, cfg.h_rdc - 0.68), cfg.mat_mur)
        colombage_urbain(c, cx - hx, cx + hx, cy - hy, 0.68, cfg.h_rdc, "x", -1.0, cfg.mat_bois, style="grille")
        if not cfg.mitoyen_droit:
            colombage_urbain(c, cy - hy, cy + hy, cx + hx, 0.68, cfg.h_rdc, "y", 1.0, cfg.mat_bois, style="grille")
        if not cfg.mitoyen_gauche:
            colombage_urbain(c, cy - hy, cy + hy, cx - hx, 0.68, cfg.h_rdc, "y", -1.0, cfg.mat_bois, style="grille")
    else:
        c.boite((cx, cy, 0.42), (cfg.lx + 0.18, cfg.ly + 0.18, 0.84), cfg.mat_angle, chanfrein=0.025)
        c.boite((cx, cy, 0.84 + (cfg.h_rdc - 0.84) * 0.5), (cfg.lx, cfg.ly, cfg.h_rdc - 0.84), cfg.mat_rdc, chanfrein=0.015)
        for sx, mit in ((-1.0, cfg.mitoyen_gauche), (1.0, cfg.mitoyen_droit)):
            if mit:
                continue
            for sy in (-1.0, 1.0):
                c.chainage_angle(cx + sx * hx, cy + sy * hy, 0.06, cfg.h_rdc - 0.04, sx, sy, cfg.mat_angle)

    # Ouvertures du RDC sur rue (-Y)
    y_rdc_av = cy - hy - 0.09
    if cfg.rdc_style == "echoppe_bois":
        ajouter_arcade_echoppe(c, cx - cfg.lx * 0.14, cy - hy, min(2.45, cfg.lx * 0.52), cfg.h_rdc, cfg.mat_bois, style="bois")
        c.porte_cintree((cx + cfg.lx * 0.30, y_rdc_av, 0.0), -1.0, 0.98, min(2.08, cfg.h_rdc - 0.36), cfg.mat_angle, cfg.mat_bois, "metal")
    elif cfg.rdc_style == "echoppe_pierre":
        ajouter_arcade_echoppe(c, cx - cfg.lx * 0.14, cy - hy, min(2.50, cfg.lx * 0.52), cfg.h_rdc, cfg.mat_bois, style="pierre")
        c.porte_cintree((cx + cfg.lx * 0.30, y_rdc_av, 0.0), -1.0, 0.98, min(2.08, cfg.h_rdc - 0.36), cfg.mat_angle, cfg.mat_bois, "metal")
    elif cfg.rdc_style == "double_arcade":
        w_a = min(2.35, cfg.lx * 0.38)
        ajouter_arcade_echoppe(c, cx - cfg.lx * 0.24, cy - hy, w_a, cfg.h_rdc, cfg.mat_bois, style="pierre")
        ajouter_arcade_echoppe(c, cx + cfg.lx * 0.24, cy - hy, w_a, cfg.h_rdc, cfg.mat_bois, style="pierre")
    elif cfg.rdc_style == "cave_haute":
        # Cave surélevée avec 2 soupiraux grillagés (la porte principale est au palier de l'escalier !)
        for dx in (-0.26, 0.26):
            ajouter_soupirail(c, cx + dx * cfg.lx, cy - hy - 0.06)
    else:
        # Porte cintrée + soupirail + petite fenêtre haute
        c.porte_cintree((cx - cfg.lx * 0.22, y_rdc_av, 0.0), -1.0, 1.12, min(2.14, cfg.h_rdc - 0.36), cfg.mat_angle, cfg.mat_bois, "metal")
        ajouter_soupirail(c, cx + cfg.lx * 0.24, cy - hy - 0.06)
        c.fenetre_medievale((cx + cfg.lx * 0.24, cy - hy - 0.04, cfg.h_rdc * 0.64), "x", -1.0, 0.72, 0.78,
                            cfg.mat_bois, cfg.mat_volet, "verre", cfg.mat_angle, volets=(c.lod == 0))

    # 2. Étages en encorbellement successif vers la rue (-Y)
    z_cur = cfg.h_rdc
    lx_e, ly_e = cfg.lx, cfg.ly
    y_av = cy - hy
    y_ar = cy + hy

    for niv in range(cfg.nb_etages):
        av_y = 0.34 if cfg.orientation == "pignon" else 0.28
        ar_y = 0.18
        y_av_prev, y_ar_prev = y_av, y_ar
        y_av -= av_y
        y_ar += ar_y
        ly_e = y_ar - y_av
        cy_e = (y_av + y_ar) * 0.5

        # Corbeaux galbés sous l'encorbellement côté rue (-Y)
        if c.lod <= 1:
            nb_c = max(4, int(lx_e / 1.15) + 1)
            for i in range(nb_c):
                ux = cx - lx_e * 0.44 + i * (lx_e * 0.88 / max(1, nb_c - 1))
                c.corbeau_galbe(ux, y_av_prev, z_cur + 0.04, (0.0, -1.0), 0.16, av_y + 0.06, 0.42, cfg.mat_bois)
                c.corbeau_galbe(ux, y_ar_prev, z_cur + 0.04, (0.0, 1.0), 0.15, ar_y + 0.05, 0.34, cfg.mat_bois)

        h_n = cfg.h_etage * (0.93 if niv > 0 else 1.0)
        z_haut = z_cur + h_n
        c.boite((cx, cy_e, z_cur + h_n * 0.5), (lx_e, ly_e, h_n), cfg.mat_mur)

        # Déterminer précisément les zones d'ouvertures avant (-Y) pour aligner le colombage dessus
        z_fen = z_cur + h_n * 0.58
        zones_av: list[tuple[float, float]] = []
        a_porte_ici = (niv == 0 and cfg.porte_etage_x is not None)
        if a_porte_ici:
            px_e = cx + cfg.porte_etage_x
            zones_av.append((px_e - 0.55, px_e + 0.55))
            ajouter_porte_etage(c, px_e, y_av, z_cur, cfg.mat_bois)

        if cfg.fenetre_etage == "oriel" and niv == 0 and not a_porte_ici:
            w_or = min(2.05, lx_e * 0.44)
            zones_av.append((cx - w_or * 0.5, cx + w_or * 0.5))
            ajouter_oriel_urbain(c, cx, y_av, z_cur + 0.24, w_or, h_n * 0.78, cfg.mat_mur, cfg.mat_bois, cfg.mat_toit)
        elif cfg.fenetre_etage == "bandeau":
            nb_b = 3 if lx_e >= 4.2 else 2
            w_b = 0.74
            tot_b = nb_b * w_b + (nb_b - 1) * 0.14
            for i in range(nb_b):
                fx = cx - tot_b * 0.5 + w_b * 0.5 + i * (w_b + 0.14)
                if a_porte_ici and abs(fx - (cx + cfg.porte_etage_x)) < 1.05:
                    continue
                zones_av.append((fx - w_b * 0.5 - 0.05, fx + w_b * 0.5 + 0.05))
                c.fenetre_medievale((fx, y_av - 0.02, z_fen), "x", -1.0, w_b, 1.12,
                                    cfg.mat_bois, cfg.mat_volet, "verre", cfg.mat_bois, volets=False)
        else:
            xs = (cx - lx_e * 0.23, cx + lx_e * 0.23) if lx_e >= 4.4 else (cx,)
            for fx in xs:
                if a_porte_ici and abs(fx - (cx + cfg.porte_etage_x)) < 1.15:
                    continue
                w_f = 0.88 if cfg.fenetre_etage == "volets" else 0.78
                h_f = 1.14 if cfg.fenetre_etage == "volets" else 1.24
                zones_av.append((fx - w_f * 0.5 - 0.06, fx + w_f * 0.5 + 0.06))
                c.fenetre_medievale((fx, y_av - 0.02, z_fen), "x", -1.0, w_f, h_f,
                                    cfg.mat_bois, cfg.mat_volet, "verre",
                                    cfg.mat_angle if cfg.fenetre_etage == "ogive" else cfg.mat_bois,
                                    volets=(cfg.fenetre_etage == "volets"))

        # Colombage 3D sur les 4 faces (même les flancs au-dessus d'un voisin plus bas reçoivent leur colombage !)
        colombage_urbain(c, cx - lx_e * 0.5, cx + lx_e * 0.5, y_av, z_cur, z_haut, "x", -1.0,
                         cfg.mat_bois, style=cfg.style_colombage, zones_libres=tuple(zones_av))
        colombage_urbain(c, cx - lx_e * 0.5, cx + lx_e * 0.5, y_ar, z_cur, z_haut, "x", 1.0,
                         cfg.mat_bois, style=cfg.style_colombage)

        # Flancs droit (+X) et gauche (-X) : colombage TOUJOURS présent, fenêtres si non mitoyen
        for sx, mit in ((1.0, cfg.mitoyen_droit), (-1.0, cfg.mitoyen_gauche)):
            zones_lat = []
            if not mit and ly_e >= 4.8:
                for dy in (-ly_e * 0.22, ly_e * 0.22):
                    fy = cy_e + dy
                    zones_lat.append((fy - 0.48, fy + 0.48))
                    c.fenetre_medievale((cx + sx * (lx_e * 0.5 + 0.02), fy, z_fen), "y", sx, 0.84, 1.08,
                                        cfg.mat_bois, cfg.mat_volet, "verre", cfg.mat_bois, volets=(c.lod == 0 and cfg.fenetre_etage == "volets"))
            colombage_urbain(c, y_av, y_ar, cx + sx * lx_e * 0.5, z_cur, z_haut, "y", sx,
                             cfg.mat_bois, style=cfg.style_colombage, zones_libres=tuple(zones_lat))

        z_cur = z_haut

    # 3. Toiture (pignon sur rue OU gouttereau avec lucarnes)
    cy_e = (y_av + y_ar) * 0.5
    if cfg.orientation == "pignon":
        toit_pignon_sur_rue(
            c, (cx, cy_e, z_cur), lx_e, ly_e, cfg.h_toit,
            cfg.mat_toit, cfg.mat_mur, cfg.mat_bois, cfg.mat_volet,
            debord_avant=0.58, debord_arriere=0.34,
            debord_cote=0.14 if (cfg.mitoyen_gauche or cfg.mitoyen_droit) else 0.30,
            epaisseur=0.28 if cfg.mat_toit == "chaume" else 0.17,
            poulie=cfg.poulie,
        )
    else:
        c.toit_detaille(
            (cx, cy_e, z_cur), lx_e, ly_e, cfg.h_toit,
            cfg.mat_toit, cfg.mat_mur, cfg.mat_bois,
            debord_x=0.14 if (cfg.mitoyen_gauche or cfg.mitoyen_droit) else 0.38,
            debord_y=0.44, epaisseur=0.28 if cfg.mat_toit == "chaume" else 0.17,
            strates=6 if cfg.mat_toit != "ardoise" else 5,
        )
        # Colombage 3D sur les deux triangles de pignon (+X et -X) — JAMAIS un triangle blanc vide !
        if c.lod <= 1:
            hy_e = ly_e * 0.5
            for sx in (-1.0, 1.0):
                gx = cx + sx * (lx_e * 0.5 + 0.04)
                c.poutre((gx, cy_e - hy_e * 0.70, z_cur + cfg.h_toit * 0.30), (gx, cy_e + hy_e * 0.70, z_cur + cfg.h_toit * 0.30), 0.12, 0.08, cfg.mat_bois)
                c.poutre((gx, cy_e - hy_e * 0.36, z_cur + cfg.h_toit * 0.62), (gx, cy_e + hy_e * 0.36, z_cur + cfg.h_toit * 0.62), 0.11, 0.08, cfg.mat_bois)
                c.poutre((gx, cy_e - 0.52, z_cur), (gx, cy_e - 0.52, z_cur + cfg.h_toit * 0.76), 0.12, 0.08, cfg.mat_bois)
                c.poutre((gx, cy_e + 0.52, z_cur), (gx, cy_e + 0.52, z_cur + cfg.h_toit * 0.76), 0.12, 0.08, cfg.mat_bois)
                if c.lod == 0:
                    c.boite((gx + sx * 0.02, cy_e, z_cur + cfg.h_toit * 0.44), (0.08, 0.72, 0.86), cfg.mat_volet, chanfrein=0.01)
        # Lucarnes chiens-assis côté rue (-Y)
        if cfg.lucarnes > 0:
            xs_l = [cx] if cfg.lucarnes == 1 else [cx - lx_e * 0.24, cx + lx_e * 0.24]
            for lx_pos in xs_l:
                ajouter_lucarne(c, lx_pos, y_av + 0.28, z_cur + 0.12, cfg.mat_mur, cfg.mat_bois, cfg.mat_toit)

    # 4. Cheminée cohérente
    if cfg.cheminee == "souche_pierre":
        x_ch = cx - lx_e * 0.5 - 0.42
        ajouter_cheminee_urbaine(c, x_ch, cy_e, z_cur, cfg.h_toit, "souche_pierre")
    elif cfg.cheminee != "sans":
        x_ch = cx + (lx_e * 0.24 if cfg.orientation == "pignon" else -lx_e * 0.18)
        y_ch = cy_e + (ly_e * 0.12 if cfg.orientation == "pignon" else ly_e * 0.15)
        ajouter_cheminee_urbaine(c, x_ch, y_ch, z_cur, cfg.h_toit, cfg.cheminee)

    # 5. Enseigne de taverne ou petits détails de rue (LOD0)
    if cfg.enseigne and c.lod <= 1:
        xe = cx + lx_e * 0.46
        c.poutre((xe, y_av, cfg.h_rdc + 0.65), (xe, y_av - 1.25, cfg.h_rdc + 0.65), 0.055, 0.055, "metal")
        c.poutre((xe, y_av, cfg.h_rdc + 0.10), (xe, y_av - 0.85, cfg.h_rdc + 0.65), 0.045, 0.045, "metal")
        c.boite((xe, y_av - 0.88, cfg.h_rdc + 0.26), (0.06, 0.68, 0.52), "or", chanfrein=0.01)
    if c.lod == 0:
        if cfg.details_sol == "tonneaux":
            c.tonneau_bombe((cx + hx - 0.38, cy - hy - 0.42, 0.0), 0.25, 0.30, 0.86, "bois", "metal")
            c.tonneau_bombe((cx + hx - 0.98, cy - hy - 0.40, 0.0), 0.23, 0.28, 0.80, "bois_clair", "metal")
        elif cfg.details_sol == "banc" and not cfg.mitoyen_droit:
            c.boite((cx + hx + 0.25, cy - 0.6, 0.44), (0.36, 1.36, 0.07), "bois_clair", chanfrein=0.01)
            for dy in (-0.48, 0.48):
                c.boite((cx + hx + 0.25, cy - 0.6 + dy, 0.22), (0.30, 0.08, 0.42), cfg.mat_bois)
        elif cfg.details_sol == "sacs":
            c.sac_noue((cx - hx + 0.55, cy - hy - 0.42, 0.0), 0.26, 0.21, 0.42, 0.2, "jute", "corde")
            c.sac_noue((cx - hx + 1.05, cy - hy - 0.38, 0.0), 0.24, 0.20, 0.38, -0.3, "jute", "corde")

    return {"y_av_e1": cy - hy - (0.34 if cfg.orientation == "pignon" else 0.28), "z_e1": cfg.h_rdc, "z_toit": z_cur, "hx": hx, "hy": hy}


# ---------------------------------------------------------------------------
# Les 24 STYLES COHÉRENTS de maisons médiévales de ville (Occident 1400)
# ---------------------------------------------------------------------------

# Famille 1 — 8 Maisons de ville étroites à PIGNON SUR RUE

def _v01(c, lod):
    construire_maison_ville(c, MaisonVille(
        lx=4.8, ly=7.8, nb_etages=2, h_toit=3.8,
        mat_rdc="pierre_taille", mat_mur="chaux_creme", mat_bois="chene_sombre",
        mat_toit="tuiles_anciennes", style_colombage="grille", rdc_style="echoppe_bois",
        fenetre_etage="volets", cheminee="brique", details_sol="banc",
    ))

def _v02(c, lod):
    construire_maison_ville(c, MaisonVille(
        lx=5.2, ly=7.6, nb_etages=2, h_toit=3.9,
        mat_rdc="pierre_claire", mat_mur="chaux_blanche", mat_bois="chene_sombre",
        mat_volet="volet_chene", mat_toit="tuiles_brunes", style_colombage="allege",
        rdc_style="porte_pierre", fenetre_etage="volets", cheminee="souche_pierre", details_sol="tonneaux",
    ))

def _v03(c, lod):
    construire_maison_ville(c, MaisonVille(
        lx=4.6, ly=8.0, h_rdc=2.8, h_etage=2.35, nb_etages=2, h_toit=4.2,
        mat_rdc="pierre", mat_mur="chaux_ocre", mat_bois="chene_sombre",
        mat_toit="ardoise", style_colombage="grille", rdc_style="echoppe_pierre",
        fenetre_etage="bandeau", cheminee="double",
    ))

def _v04(c, lod):
    construire_maison_ville(c, MaisonVille(
        lx=5.2, ly=7.6, nb_etages=2, h_toit=3.8,
        mat_rdc="pierre_taille", mat_mur="chaux_terre", mat_bois="chene_sombre",
        mat_volet="volet_brun", mat_toit="tuiles_brunes", style_colombage="losange",
        rdc_style="porte_pierre", fenetre_etage="oriel", cheminee="double", details_sol="banc",
    ))

def _v05(c, lod):
    construire_maison_ville(c, MaisonVille(
        lx=5.0, ly=8.0, nb_etages=2, h_toit=4.1,
        mat_rdc="mur_brique", mat_mur="mur_brique", mat_bois="chene_sombre",
        mat_volet="volet_chene", mat_toit="ardoise", style_colombage="grille",
        rdc_style="echoppe_pierre", fenetre_etage="bandeau", cheminee="octogonale",
    ))

def _v06(c, lod):
    construire_maison_ville(c, MaisonVille(
        lx=4.6, ly=7.2, h_rdc=2.55, h_etage=2.45, nb_etages=1, h_toit=3.5,
        mat_rdc="colombage_rdc", mat_mur="chaux_grise", mat_bois="chene_patine",
        mat_toit="bardeaux", style_colombage="grille", rdc_style="porte_pierre",
        fenetre_etage="bandeau", cheminee="brique", details_sol="sacs",
    ))

def _v07(c, lod):
    construire_maison_ville(c, MaisonVille(
        lx=5.6, ly=8.0, nb_etages=2, h_toit=3.9,
        mat_rdc="pierre_claire", mat_mur="chaux_creme", mat_bois="bois_sang",
        mat_volet="volet_brun", mat_toit="tuiles_anciennes", style_colombage="allege",
        rdc_style="double_arcade", fenetre_etage="volets", cheminee="double",
        enseigne=True, details_sol="tonneaux",
    ))

def _v08(c, lod):
    info = construire_maison_ville(c, MaisonVille(
        lx=5.4, ly=8.2, nb_etages=2, h_toit=4.0,
        mat_rdc="pierre_claire", mat_mur="chaux_blanche", mat_bois="chene_sombre",
        mat_toit="ardoise", style_colombage="allege", rdc_style="porte_pierre",
        fenetre_etage="ogive", cheminee="octogonale",
    ))
    # Tourelle d'escalier octogonale en encorbellement sur l'angle avant droit
    tx, ty = 2.65, -info["hy"] + 0.15
    c.cylindre((tx, ty, 4.15), 0.96, 0.92, 8.30, 8, "pierre_claire")
    c.cylindre((tx, ty, 8.38), 1.04, 1.04, 0.16, 8, "pierre_taille")
    c.revolution((tx, ty, 8.45), [(1.14, 0.0), (0.62, 1.05), (0.03, 2.25)], 8, "ardoise", smooth=False)
    if lod <= 1:
        for az in (2.8, 5.2, 7.2):
            c.boite((tx, ty - 0.92, az), (0.30, 0.10, 0.52), "verre")


# Famille 2 — 6 Ensembles de MAISONS DE VILLE COLLÉES cohérentes (pignons décalés, balcons sur portes d'étage)

def _v09(c, lod):
    # Deux maisons à pignons sur rue collées côte à côte (hauteurs et largeurs décalées, même quartier de tuiles)
    construire_maison_ville(c, MaisonVille(
        cx=-2.45, lx=4.9, ly=7.8, nb_etages=2, h_toit=3.9,
        mat_rdc="pierre_taille", mat_mur="chaux_creme", mat_bois="chene_sombre",
        mat_toit="tuiles_anciennes", style_colombage="grille", rdc_style="echoppe_bois",
        mitoyen_droit=True, cheminee="brique",
    ))
    construire_maison_ville(c, MaisonVille(
        cx=2.25, lx=4.5, ly=7.2, h_rdc=2.60, h_etage=2.35, nb_etages=1, h_toit=3.4,
        mat_rdc="pierre", mat_mur="chaux_ocre", mat_bois="chene_patine",
        mat_volet="volet_olive", mat_toit="tuiles_brunes", style_colombage="allege",
        rdc_style="porte_pierre", mitoyen_gauche=True, cheminee="double", details_sol="tonneaux",
    ))

def _v10(c, lod):
    # Trio de maisons collées à pignons sur rue : vraie silhouette de rue médiévale (3 hauteurs, 3 largeurs)
    construire_maison_ville(c, MaisonVille(
        cx=-4.55, lx=4.5, ly=7.4, h_rdc=2.60, nb_etages=1, h_toit=3.4,
        mat_rdc="pierre_taille", mat_mur="chaux_grise", mat_bois="chene_sombre",
        mat_toit="tuiles_brunes", style_colombage="grille", rdc_style="porte_pierre",
        mitoyen_droit=True, cheminee="souche_pierre",
    ))
    construire_maison_ville(c, MaisonVille(
        cx=0.0, lx=4.6, ly=8.0, h_rdc=2.75, h_etage=2.40, nb_etages=2, h_toit=4.0,
        mat_rdc="mur_brique", mat_mur="chaux_creme", mat_bois="bois_sang",
        mat_toit="ardoise", style_colombage="allege", rdc_style="echoppe_pierre",
        fenetre_etage="oriel", mitoyen_gauche=True, mitoyen_droit=True, cheminee="octogonale",
    ))
    construire_maison_ville(c, MaisonVille(
        cx=4.50, lx=4.4, ly=7.6, h_rdc=2.65, h_etage=2.30, nb_etages=2, h_toit=3.6,
        mat_rdc="pierre_claire", mat_mur="chaux_ocre", mat_bois="chene_sombre",
        mat_toit="tuiles_anciennes", style_colombage="grille", rdc_style="echoppe_bois",
        mitoyen_gauche=True, cheminee="brique",
    ))

def _v11(c, lod):
    # Deux maisons collées (gouttereau cohérent) + balcon commun desservant DEUX VRAIES PORTES D'ÉTAGE + escalier bois latéral dégagé
    i1 = construire_maison_ville(c, MaisonVille(
        cx=-2.5, lx=5.0, ly=5.6, orientation="gouttereau", h_rdc=2.65, nb_etages=1, h_toit=3.3,
        mat_rdc="pierre_taille", mat_mur="chaux_creme", mat_bois="chene_sombre",
        mat_toit="tuiles_anciennes", rdc_style="cave_haute", porte_etage_x=0.75,
        mitoyen_droit=True, lucarnes=1, cheminee="brique",
    ))
    construire_maison_ville(c, MaisonVille(
        cx=2.5, lx=5.0, ly=5.6, orientation="gouttereau", h_rdc=2.65, h_etage=2.55, nb_etages=1, h_toit=3.5,
        mat_rdc="pierre_claire", mat_mur="chaux_ocre", mat_bois="chene_patine",
        mat_toit="tuiles_brunes", rdc_style="cave_haute", porte_etage_x=-0.75,
        mitoyen_gauche=True, lucarnes=1, cheminee="double",
    ))
    y_m = i1["y_av_e1"]
    ajouter_balcon_propre(c, -2.5, 2.5, y_m, 2.66, 1.25, "chene_sombre", ouvert_cote="droite")
    ajouter_escalier_propre(c, 2.5, y_m - 1.25, 2.66, 1.0, 1.10, "chene_sombre", en_pierre=False, en_bout=True)

def _v12(c, lod):
    # Assemblage pignon + gouttereau collés, escalier en pierre montant au balcon couvert devant la porte d'étage
    construire_maison_ville(c, MaisonVille(
        cx=-2.6, lx=4.8, ly=7.4, orientation="pignon", h_rdc=2.65, nb_etages=2, h_toit=3.8,
        mat_rdc="pierre_claire", mat_mur="chaux_blanche", mat_bois="chene_sombre",
        mat_toit="tuiles_anciennes", rdc_style="porte_pierre", mitoyen_droit=True, cheminee="brique",
    ))
    i2 = construire_maison_ville(c, MaisonVille(
        cx=2.7, lx=5.8, ly=5.6, orientation="gouttereau", h_rdc=2.65, nb_etages=1, h_toit=3.3,
        mat_rdc="pierre", mat_mur="chaux_grise", mat_bois="chene_sombre",
        mat_toit="tuiles_brunes", rdc_style="cave_haute", porte_etage_x=-0.85,
        mitoyen_gauche=True, lucarnes=1, cheminee="double",
    ))
    y_m = i2["y_av_e1"]
    ajouter_balcon_propre(c, 0.3, 3.3, y_m, 2.66, 1.25, "chene_sombre", mat_toit="tuiles_brunes", ouvert_cote="droite")
    ajouter_escalier_propre(c, 3.3, y_m - 1.25, 2.66, 1.0, 1.12, "pierre_claire", en_pierre=True, en_bout=True)

def _v13(c, lod):
    # Deux maisons à pignons collées par un passage voûté pavé traversant + pont en colombages
    construire_maison_ville(c, MaisonVille(
        cx=-4.1, lx=4.6, ly=7.6, orientation="pignon", h_rdc=2.75, nb_etages=2, h_toit=3.8,
        mat_rdc="pierre_taille", mat_mur="chaux_creme", mat_bois="chene_sombre",
        mat_toit="tuiles_anciennes", rdc_style="porte_pierre", mitoyen_droit=True, cheminee="souche_pierre",
    ))
    construire_maison_ville(c, MaisonVille(
        cx=4.1, lx=4.6, ly=7.6, orientation="pignon", h_rdc=2.75, nb_etages=2, h_toit=3.9,
        mat_rdc="pierre", mat_mur="chaux_ocre", mat_bois="chene_sombre",
        mat_toit="tuiles_brunes", rdc_style="echoppe_bois", mitoyen_gauche=True, cheminee="brique",
    ))
    # Passage voûté en pierre pavée + pont d'habitation en colombage (même gamme de tuiles)
    c.boite((0.0, 0.0, 0.06), (3.60, 7.20, 0.12), "paves")
    c.boite((0.0, 0.0, 4.02), (3.64, 6.20, 2.50), "chaux_creme")
    colombage_urbain(c, -1.82, 1.82, -3.10, 2.76, 5.26, "x", -1.0, "chene_sombre", style="grille", zones_libres=((-0.62, 0.62),))
    colombage_urbain(c, -1.82, 1.82, 3.10, 2.76, 5.26, "x", 1.0, "chene_sombre", style="grille")
    c.fenetre_medievale((0.0, -3.12, 4.18), "x", -1.0, 1.10, 1.12, "chene_sombre", "volet_chene", "verre", "chene_sombre", volets=True)
    nb_v = 11 if lod == 0 else 7
    for fy in (-2.95, 2.95):
        for i in range(nb_v):
            a = math.pi * (i + 0.5) / nb_v
            c.boite((math.cos(a) * 1.72, fy, 1.45 + math.sin(a) * 1.32), (0.34, 0.30, 0.42),
                    "pierre_claire", rot=(0, a - math.pi * 0.5, 0), chanfrein=0.018)
    c.toit_detaille((0.0, 0.0, 5.26), 3.64, 6.20, 2.75, "tuiles_anciennes", "chaux_creme", "chene_sombre",
                    debord_x=0.10, debord_y=0.40, epaisseur=0.17, strates=5)

def _v14(c, lod):
    # Angle de rue en L : haute maison pignon sur rue + aile retour gouttereau avec galerie d'étage sur cour
    construire_maison_ville(c, MaisonVille(
        cx=-2.3, cy=-0.4, lx=4.8, ly=7.8, orientation="pignon", h_rdc=2.65, nb_etages=2, h_toit=3.8,
        mat_rdc="pierre_taille", mat_mur="chaux_creme", mat_bois="chene_sombre",
        mat_toit="tuiles_brunes", rdc_style="echoppe_bois", mitoyen_droit=True, cheminee="octogonale",
    ))
    i2 = construire_maison_ville(c, MaisonVille(
        cx=2.6, cy=1.4, lx=5.2, ly=5.0, orientation="gouttereau", h_rdc=2.65, nb_etages=1, h_toit=3.2,
        mat_rdc="pierre_claire", mat_mur="chaux_ocre", mat_bois="chene_sombre",
        mat_toit="tuiles_anciennes", rdc_style="cave_haute", porte_etage_x=0.0,
        mitoyen_gauche=True, lucarnes=1, cheminee="brique",
    ))
    # Cour pavée dans l'angle avant droit + galerie couverte + escalier bois
    c.boite((2.6, -2.5, 0.05), (5.0, 3.6, 0.10), "paves")
    y_m = i2["y_av_e1"]
    ajouter_balcon_propre(c, 0.3, 4.9, y_m, 2.66, 1.18, "chene_sombre", mat_toit="tuiles_anciennes", ouvert_x=(3.6, 4.8))
    ajouter_escalier_propre(c, 3.6, y_m - 1.18, 2.66, -1.0, 1.0, "chene_sombre", en_pierre=False, en_bout=False)


# Famille 3 — 6 Maisons avec GRANGE, REMISE, BÛCHER ou HANGAR EN BOIS ADOSSÉ (zéro pignon nu !)

def _v15(c, lod):
    info = construire_maison_ville(c, MaisonVille(
        cx=-2.0, lx=5.0, ly=7.6, orientation="pignon", nb_etages=2, h_toit=3.8,
        mat_rdc="pierre_taille", mat_mur="chaux_creme", mat_bois="chene_sombre",
        mat_toit="tuiles_anciennes", rdc_style="porte_pierre", mitoyen_droit=True, cheminee="brique",
    ))
    ajouter_grange_bois(c, -2.0 + info["hx"], 0.2, 1.0, 4.2, 6.2, 3.0, "chene_sombre", "tuiles_brunes", style="grange")

def _v16(c, lod):
    # Maison de faubourg en gouttereau au chaume + grange en bois au chaume (pignon entièrement colombagé !)
    info = construire_maison_ville(c, MaisonVille(
        cx=-2.3, lx=6.0, ly=5.2, orientation="gouttereau", h_rdc=2.45, h_etage=2.35, nb_etages=1, h_toit=3.5,
        mat_rdc="pierre", mat_mur="chaux_grise", mat_bois="chene_patine",
        mat_volet="volet_olive", mat_toit="chaume", rdc_style="porte_pierre",
        mitoyen_droit=True, cheminee="souche_pierre",
    ))
    ajouter_grange_bois(c, -2.3 + info["hx"], 0.0, 1.0, 4.4, 4.8, 2.8, "chene_patine", "chaume", style="grange")

def _v17(c, lod):
    info = construire_maison_ville(c, MaisonVille(
        cx=-1.3, lx=4.8, ly=7.4, orientation="pignon", nb_etages=2, h_toit=3.8,
        mat_rdc="brique_brune", mat_mur="chaux_ocre", mat_bois="chene_sombre",
        mat_toit="tuiles_brunes", rdc_style="porte_pierre", mitoyen_droit=True, cheminee="double",
    ))
    ajouter_grange_bois(c, -1.3 + info["hx"], 0.4, 1.0, 2.9, 5.4, 2.6, "chene_sombre", "tuiles_brunes", style="bucher")

def _v18(c, lod):
    info = construire_maison_ville(c, MaisonVille(
        cx=-1.7, lx=5.0, ly=7.6, orientation="pignon", nb_etages=2, h_toit=3.8,
        mat_rdc="pierre_claire", mat_mur="chaux_creme", mat_bois="bois_sang",
        mat_volet="volet_brun", mat_toit="tuiles_anciennes", rdc_style="echoppe_bois",
        mitoyen_droit=True, cheminee="brique",
    ))
    ajouter_grange_bois(c, -1.7 + info["hx"], 0.3, 1.0, 3.4, 5.6, 2.8, "bois_sang", "tuiles_brunes", style="remise")

def _v19(c, lod):
    info = construire_maison_ville(c, MaisonVille(
        cx=-2.2, lx=6.6, ly=5.4, orientation="gouttereau", nb_etages=1, h_toit=3.5,
        mat_rdc="pierre_claire", mat_mur="chaux_blanche", mat_bois="chene_sombre",
        mat_toit="tuiles_anciennes", rdc_style="porte_pierre", lucarnes=2,
        mitoyen_droit=True, cheminee="souche_pierre",
    ))
    ajouter_grange_bois(c, -2.2 + info["hx"], 0.0, 1.0, 4.2, 5.0, 3.0, "chene_sombre", "tuiles_anciennes", style="grange")

def _v20(c, lod):
    info = construire_maison_ville(c, MaisonVille(
        cx=-1.9, lx=5.0, ly=7.4, orientation="pignon", nb_etages=1, h_toit=3.6,
        mat_rdc="pierre_taille", mat_mur="chaux_terre", mat_bois="chene_sombre",
        mat_toit="tuiles_brunes", rdc_style="porte_pierre", mitoyen_droit=True, cheminee="brique",
    ))
    ajouter_grange_bois(c, -1.9 + info["hx"], 0.2, 1.0, 3.8, 5.4, 2.7, "chene_sombre", "tuiles_brunes", style="hangar")


# Famille 4 — 4 Maisons en GOUTTEREAU SUR RUE à lucarnes, balcons sur portes d'étage et caves hautes

def _v21(c, lod):
    construire_maison_ville(c, MaisonVille(
        lx=7.2, ly=5.4, orientation="gouttereau", h_rdc=2.75, h_etage=2.50, nb_etages=1, h_toit=3.6,
        mat_rdc="pierre_claire", mat_mur="chaux_creme", mat_bois="chene_sombre",
        mat_toit="ardoise", style_colombage="grille", rdc_style="porte_pierre",
        lucarnes=2, cheminee="double", details_sol="banc",
    ))

def _v22(c, lod):
    # Gouttereau avec porte d'étage dédiée + balcon latéral + escalier bois dégagé sur mur plein
    info = construire_maison_ville(c, MaisonVille(
        lx=6.8, ly=5.2, orientation="gouttereau", h_rdc=2.65, nb_etages=1, h_toit=3.4,
        mat_rdc="pierre_taille", mat_mur="chaux_ocre", mat_bois="chene_sombre",
        mat_toit="tuiles_brunes", style_colombage="allege", rdc_style="cave_haute",
        porte_etage_x=-1.45, lucarnes=1, cheminee="souche_pierre",
    ))
    y_m = info["y_av_e1"]
    ajouter_balcon_propre(c, -2.5, 0.1, y_m, 2.66, 1.22, "chene_sombre", ouvert_cote="droite")
    ajouter_escalier_propre(c, 0.1, y_m - 1.22, 2.66, 1.0, 1.08, "chene_sombre", en_pierre=False, en_bout=True)

def _v23(c, lod):
    # Maison sur cave haute : escalier en pierre montant au perron-balcon couvert devant la porte d'étage
    info = construire_maison_ville(c, MaisonVille(
        lx=6.6, ly=5.2, orientation="gouttereau", h_rdc=2.60, nb_etages=1, h_toit=3.4,
        mat_rdc="pierre", mat_mur="chaux_grise", mat_bois="chene_patine",
        mat_toit="tuiles_anciennes", style_colombage="grille", rdc_style="cave_haute",
        porte_etage_x=1.20, lucarnes=1, cheminee="brique",
    ))
    y_m = info["y_av_e1"]
    ajouter_balcon_propre(c, -0.3, 2.5, y_m, 2.62, 1.28, "chene_patine", mat_toit="tuiles_anciennes", ouvert_cote="gauche")
    ajouter_escalier_propre(c, -0.3, y_m - 1.28, 2.62, -1.0, 1.12, "pierre_claire", en_pierre=True, en_bout=True)

def _v24(c, lod):
    # Maison de marchand à double arcade en pierre au RDC + galerie couverte haute desservant la porte d'étage
    info = construire_maison_ville(c, MaisonVille(
        lx=7.2, ly=5.6, orientation="gouttereau", h_rdc=2.75, h_etage=2.55, nb_etages=1, h_toit=3.6,
        mat_rdc="pierre_claire", mat_mur="chaux_creme", mat_bois="chene_sombre",
        mat_volet="volet_brun", mat_toit="tuiles_anciennes", style_colombage="grille",
        rdc_style="double_arcade", porte_etage_x=0.0, lucarnes=2, cheminee="octogonale", details_sol="tonneaux",
    ))
    y_m = info["y_av_e1"]
    ajouter_balcon_propre(c, -2.8, 2.8, y_m, 2.76, 1.18, "chene_sombre", mat_toit="tuiles_anciennes", poteaux_sol=False)


STYLES_MAISONS = [
    ("ville_01_pignon_echoppe", "PignonSurRue", "Pignon sur rue · échoppe bois & colombage serré", _v01),
    ("ville_02_pignon_pierre_rdc", "PignonSurRue", "Pignon bourgeois · RDC pierre, souche & tuiles brunes", _v02),
    ("ville_03_pignon_haute_3etages", "PignonSurRue", "Haute maison urbaine · ocre, bandeau & ardoise", _v03),
    ("ville_04_pignon_oriel", "PignonSurRue", "Maison de drapier · terre rosée & oriel sculpté", _v04),
    ("ville_05_pignon_brique_flandre", "PignonSurRue", "Marchande brique · Flandre & cheminée octogonale", _v05),
    ("ville_06_pignon_tisserand", "PignonSurRue", "Artisan tisserand · gris, bandeau & bardeaux", _v06),
    ("ville_07_pignon_taverne", "PignonSurRue", "Taverne urbaine · double arcade, bois sang & enseigne", _v07),
    ("ville_08_pignon_tourelle", "PignonSurRue", "Notable · pignon ardoise & tourelle d'escalier", _v08),
    ("ville_09_collees_deux_pignons", "MaisonsCollees", "Deux pignons collés · hauteurs & teintes décalées", _v09),
    ("ville_10_collees_trio_rue", "MaisonsCollees", "Trio de pignons sur rue · vraie façade de ville", _v10),
    ("ville_11_collees_balcon_commun", "MaisonsCollees", "Collées · balcon commun sur 2 portes d'étage & escalier bois", _v11),
    ("ville_12_collees_escalier_pierre", "MaisonsCollees", "Pignon + gouttereau · balcon couvert & escalier pierre", _v12),
    ("ville_13_collees_passage_voute", "MaisonsCollees", "Deux pignons collés · passage voûté pavé & pont colombage", _v13),
    ("ville_14_collees_angle_rue", "MaisonsCollees", "Angle de rue en L · cour pavée, galerie & escalier", _v14),
    ("ville_15_pignon_grange_bois", "GrangeAdossee", "Pignon urbain crème + grange bois bardé", _v15),
    ("ville_16_gouttereau_grange_chaume", "GrangeAdossee", "Faubourg chaume + grande grange bois au chaume", _v16),
    ("ville_17_pignon_bucher_appentis", "GrangeAdossee", "Pignon brique/ocre + bûcher ouvert en appentis", _v17),
    ("ville_18_echoppe_remise_bois", "GrangeAdossee", "Échoppe bois sang-de-bœuf + remise latérale", _v18),
    ("ville_19_manoir_grange_pierre_bois", "GrangeAdossee", "Grande maison à 2 lucarnes + grange adossée", _v19),
    ("ville_20_atelier_charron_hangar", "GrangeAdossee", "Artisan terre rosée + hangar ouvert de charron", _v20),
    ("ville_21_gouttereau_lucarnes", "GouttereauUrbain", "Bourgeoise en gouttereau · 2 chiens-assis & ardoise", _v21),
    ("ville_22_gouttereau_balcon_escalier", "GouttereauUrbain", "Gouttereau ocre · porte d'étage, balcon & escalier bois", _v22),
    ("ville_23_gouttereau_escalier_pierre", "GouttereauUrbain", "Cave haute · perron-balcon couvert & escalier pierre", _v23),
    ("ville_24_gouttereau_galerie_cour", "GouttereauUrbain", "Marchande · double arcade pierre & galerie couverte", _v24),
]


def fabriquer_maisons(dossier_sortie: Path, dossier_pbr: Path, filtre: set[str] | None = None) -> list[dict]:
    rapport: list[dict] = []
    for nom_id, famille, titre, fn in STYLES_MAISONS:
        if filtre is not None and nom_id not in filtre:
            continue
        base.vider_scene()
        palette = preparer_palette_ville(dossier_pbr)
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

        lods[1].hide_render = True
        lods[2].hide_render = True
        chemin_rendu = dossier_sortie / "Rendus" / f"{nom_id}_rendu.png"
        base.rendre_studio(lods[0], chemin_rendu)

        mesure = base.verifier_fbx(chemin_fbx, nom_id)
        mesure["famille"] = famille
        mesure["titre"] = titre
        mesure["rendu"] = chemin_rendu.name
        rapport.append(mesure)
        print(f"OK {nom_id:36} tris={mesure['triangles']} dims={mesure['dimensions_m']}m", flush=True)

    if filtre is None:
        (dossier_sortie / "rapport.json").write_text(
            json.dumps({"version": 2, "modeles": rapport}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return rapport


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--sortie", type=Path, required=True)
    parser.add_argument("--textures", type=Path, required=True)
    parser.add_argument("--seulement", default="", help="liste d'IDs séparés par des virgules")
    args = parser.parse_args(argv)
    filtre = {s.strip() for s in args.seulement.split(",") if s.strip()} or None
    fabriquer_maisons(args.sortie, args.textures, filtre=filtre)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
