"""Générateur Blender 4.x haute géométrie du catalogue 3D 1400 pour Forge.

Produit 14 modèles 3D en FBX (échelle métrique, pivot au sol z=0, UV cubiques,
chanfreins, charpentes et colombages en relief 3D, portes voûtées en claveaux,
fenêtres creusées à meneaux et volets, bannières ondulées, roues à rayons,
tonneaux bombés et sacs noués), avec trois niveaux de détail strictement
décroissants (`<id>_LOD0`, `<id>_LOD1`, `<id>_LOD2`), rendus studio 3/4 Cycles
et vérification automatique par réimport FBX.

Usage :
    blender --background --python 3d/local3d/catalogue_1400.py -- \
        --sortie 3d/unity/Assets/ForgeLocal3D/Catalogue1400 \
        --textures 3d/unity/Assets/Interface/Resources/Forge/MatieresPBR
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector


# ---------------------------------------------------------------------------
# Utilitaires scène et matériaux PBR
# ---------------------------------------------------------------------------

def vider_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def charger_image(chemin: Path, non_color: bool = False):
    im = bpy.data.images.load(str(chemin.resolve()), check_existing=True)
    if non_color:
        im.colorspace_settings.name = "Non-Color"
    return im


def creer_materiau_pbr(nom: str, dossier: Path, prefixe: str, *,
                       metallic: float = 0.0, normal_strength: float = 0.9,
                       teinte: tuple[float, float, float] | None = None,
                       facteur_teinte: float = 0.45):
    mat = bpy.data.materials.new(name=nom)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Metallic"].default_value = metallic
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    p_albedo = dossier / f"{prefixe}_albedo.png"
    p_rough = dossier / f"{prefixe}_roughness.png"
    p_norm = dossier / f"{prefixe}_normal.png"
    p_ao = dossier / f"{prefixe}_ao.png"

    if p_albedo.is_file():
        tex_a = nt.nodes.new("ShaderNodeTexImage")
        tex_a.image = charger_image(p_albedo, non_color=False)
        sortie_couleur = tex_a.outputs["Color"]

        if p_ao.is_file():
            tex_ao = nt.nodes.new("ShaderNodeTexImage")
            tex_ao.image = charger_image(p_ao, non_color=True)
            mix_ao = nt.nodes.new("ShaderNodeMix")
            mix_ao.data_type = "RGBA"
            mix_ao.blend_type = "MULTIPLY"
            mix_ao.inputs["Factor"].default_value = 0.65
            nt.links.new(sortie_couleur, mix_ao.inputs[6])
            nt.links.new(tex_ao.outputs["Color"], mix_ao.inputs[7])
            sortie_couleur = mix_ao.outputs[2]

        if teinte is not None:
            mix_t = nt.nodes.new("ShaderNodeMix")
            mix_t.data_type = "RGBA"
            mix_t.blend_type = "MIX"
            mix_t.inputs["Factor"].default_value = facteur_teinte
            mix_t.inputs[7].default_value = (*teinte, 1.0)
            nt.links.new(sortie_couleur, mix_t.inputs[6])
            sortie_couleur = mix_t.outputs[2]

        nt.links.new(sortie_couleur, bsdf.inputs["Base Color"])

    if p_rough.is_file():
        tex_r = nt.nodes.new("ShaderNodeTexImage")
        tex_r.image = charger_image(p_rough, non_color=True)
        nt.links.new(tex_r.outputs["Color"], bsdf.inputs["Roughness"])
    else:
        bsdf.inputs["Roughness"].default_value = 0.8

    if p_norm.is_file():
        tex_n = nt.nodes.new("ShaderNodeTexImage")
        tex_n.image = charger_image(p_norm, non_color=True)
        nmap = nt.nodes.new("ShaderNodeNormalMap")
        nmap.inputs["Strength"].default_value = normal_strength
        nt.links.new(tex_n.outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

    return mat


def creer_materiau_simple(nom: str, couleur: tuple[float, float, float], *,
                          roughness: float = 0.78, metallic: float = 0.0,
                          emission: tuple[float, float, float] | None = None,
                          emission_strength: float = 0.0):
    mat = bpy.data.materials.new(name=nom)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*couleur, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if emission is not None and emission_strength > 0.0:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    return mat


def preparer_palette(dossier_pbr: Path) -> dict[str, bpy.types.Material]:
    """Charge les 9 jeux PBR du dépôt et les matériaux architecturaux DA."""
    return {
        "pierre": creer_materiau_pbr("M_PierreSombre", dossier_pbr / "PierreSombre", "pierre_sombre"),
        "pierre_claire": creer_materiau_pbr(
            "M_PierreCalcaire", dossier_pbr / "PavesMedievaux", "paves_medievaux",
            teinte=(0.68, 0.62, 0.50), facteur_teinte=0.42, normal_strength=1.0,
        ),
        "pierre_taille": creer_materiau_pbr(
            "M_PierreTaille", dossier_pbr / "PiseOcre", "pise_ocre",
            teinte=(0.64, 0.59, 0.49), facteur_teinte=0.72, normal_strength=0.65,
        ),
        "torchis": creer_materiau_pbr(
            "M_TorchisCreme", dossier_pbr / "PiseOcre", "pise_ocre",
            teinte=(0.79, 0.74, 0.63), facteur_teinte=0.82, normal_strength=0.55,
        ),
        "brique": creer_materiau_pbr(
            "M_BriqueCheminee", dossier_pbr / "TuilesMedievales", "tuiles_medievales",
            teinte=(0.48, 0.28, 0.20), facteur_teinte=0.35, normal_strength=0.95,
        ),
        "bois": creer_materiau_pbr("M_BoisBrule", dossier_pbr / "BoisBrule", "bois_brule", normal_strength=0.95),
        "bois_clair": creer_materiau_pbr(
            "M_BoisChene", dossier_pbr / "BoisBrule", "bois_brule",
            teinte=(0.44, 0.31, 0.19), facteur_teinte=0.45, normal_strength=0.9,
        ),
        "metal": creer_materiau_pbr(
            "M_MetalPatine", dossier_pbr / "MetalPatine", "metal_patine",
            metallic=0.75, normal_strength=0.75,
        ),
        "plomb": creer_materiau_simple("M_Plomb", (0.28, 0.30, 0.33), roughness=0.42, metallic=0.78),
        "verre": creer_materiau_simple("M_VerrePlombe", (0.09, 0.13, 0.17), roughness=0.14, metallic=0.22),
        "pise": creer_materiau_pbr("M_PiseOcre", dossier_pbr / "PiseOcre", "pise_ocre"),
        "colombage": creer_materiau_pbr("M_Colombage", dossier_pbr / "ColombageTorchis", "colombage_torchis"),
        "chaume": creer_materiau_pbr("M_Chaume", dossier_pbr / "ChaumeMedieval", "chaume_medieval", normal_strength=1.1),
        "tuiles": creer_materiau_pbr("M_Tuiles", dossier_pbr / "TuilesMedievales", "tuiles_medievales", normal_strength=1.1),
        "paves": creer_materiau_pbr("M_Paves", dossier_pbr / "PavesMedievaux", "paves_medievaux"),
        "terre": creer_materiau_pbr("M_TerreBattue", dossier_pbr / "TerreBattue", "terre_battue"),
        "toile": creer_materiau_simple("M_ToileEcrue", (0.76, 0.70, 0.58), roughness=0.88),
        "banniere": creer_materiau_simple("M_BanniereGarance", (0.40, 0.065, 0.055), roughness=0.76),
        "or": creer_materiau_simple("M_OrVieilli", (0.68, 0.52, 0.24), roughness=0.35, metallic=0.86),
        "jute": creer_materiau_pbr(
            "M_ToileJute", dossier_pbr / "ChaumeMedieval", "chaume_medieval",
            teinte=(0.64, 0.54, 0.38), facteur_teinte=0.72, normal_strength=0.45,
        ),
        "corde": creer_materiau_simple("M_Corde", (0.36, 0.27, 0.16), roughness=0.92),
        "cuir": creer_materiau_simple("M_CuirSombre", (0.20, 0.12, 0.07), roughness=0.65),
        "braise": creer_materiau_simple(
            "M_BraiseForge", (0.95, 0.28, 0.04), roughness=0.45,
            emission=(1.0, 0.34, 0.05), emission_strength=6.0,
        ),
        "eau": creer_materiau_simple("M_EauSombre", (0.09, 0.17, 0.20), roughness=0.12),
        "charbon": creer_materiau_simple("M_Charbon", (0.035, 0.035, 0.04), roughness=0.86),
    }


# ---------------------------------------------------------------------------
# Constructeur BMesh haute géométrie (chanfreins, arcs, charpentes, organique)
# ---------------------------------------------------------------------------

class Constructeur:
    """Assemble des formes architecturales et sculpturales en BMesh par matériau."""

    def __init__(self, palette: dict[str, bpy.types.Material], echelle_uv: float = 1.6, lod: int = 0):
        self.palette = palette
        self.echelle_uv = echelle_uv
        self.lod = lod
        self.bm = bmesh.new()
        self.noms_mat: list[str] = []
        self._index_mat: dict[str, int] = {}

    def _slot(self, mat_cle: str) -> int:
        if mat_cle not in self._index_mat:
            self._index_mat[mat_cle] = len(self.noms_mat)
            self.noms_mat.append(mat_cle)
        return self._index_mat[mat_cle]

    def _marquer(self, faces, mat_cle: str, smooth: bool = False) -> None:
        slot = self._slot(mat_cle)
        for f in faces:
            f.material_index = slot
            f.smooth = smooth

    def _ajouter_sous_bm(self, sub: bmesh.types.BMesh, mat_cle: str, smooth: bool = False) -> None:
        slot = self._slot(mat_cle)
        corresp: dict[bmesh.types.BMVert, bmesh.types.BMVert] = {}
        for v in sub.verts:
            corresp[v] = self.bm.verts.new(v.co)
        for f in sub.faces:
            try:
                nf = self.bm.faces.new([corresp[v] for v in f.verts])
                nf.material_index = slot
                nf.smooth = smooth
            except ValueError:
                pass
        sub.free()

    def boite(self, centre: tuple[float, float, float], taille: tuple[float, float, float],
              mat: str, rot: tuple[float, float, float] = (0.0, 0.0, 0.0),
              chanfrein: float = 0.0) -> None:
        sx, sy, sz = taille
        sub = bmesh.new()
        bmesh.ops.create_cube(sub, size=1.0, matrix=Matrix.Diagonal((sx, sy, sz, 1.0)))
        if chanfrein > 0.0 and self.lod == 0:
            lim = min(sx, sy, sz) * 0.35
            off = min(chanfrein, lim)
            if off > 1e-4:
                bmesh.ops.bevel(
                    sub, geom=list(sub.edges), offset=off, offset_type="OFFSET",
                    segments=1, profile=0.5, affect="EDGES", clamp_overlap=True,
                )
        m = Matrix.Translation(Vector(centre)) @ Euler(rot, "XYZ").to_matrix().to_4x4()
        bmesh.ops.transform(sub, matrix=m, verts=sub.verts)
        self._ajouter_sous_bm(sub, mat, smooth=False)

    def poutre(self, p1: tuple[float, float, float], p2: tuple[float, float, float],
               largeur: float, epaisseur: float, mat: str, chanfrein: float = 0.014) -> None:
        """Pose une poutre chanfreinée orientée de p1 vers p2."""
        v1, v2 = Vector(p1), Vector(p2)
        d = v2 - v1
        longueur = d.length
        if longueur < 1e-4:
            return
        milieu = (v1 + v2) * 0.5
        quat = d.normalized().to_track_quat("X", "Z")
        sub = bmesh.new()
        bmesh.ops.create_cube(sub, size=1.0, matrix=Matrix.Diagonal((longueur, largeur, epaisseur, 1.0)))
        if chanfrein > 0.0 and self.lod == 0:
            off = min(chanfrein, largeur * 0.28, epaisseur * 0.28)
            bmesh.ops.bevel(
                sub, geom=list(sub.edges), offset=off, offset_type="OFFSET",
                segments=1, profile=0.5, affect="EDGES", clamp_overlap=True,
            )
        m = Matrix.Translation(milieu) @ quat.to_matrix().to_4x4()
        bmesh.ops.transform(sub, matrix=m, verts=sub.verts)
        self._ajouter_sous_bm(sub, mat, smooth=False)

    def cylindre(self, centre: tuple[float, float, float], rayon_bas: float, rayon_haut: float,
                 hauteur: float, segments: int, mat: str,
                 rot: tuple[float, float, float] = (0.0, 0.0, 0.0), smooth: bool = False) -> None:
        sub = bmesh.new()
        m = Matrix.Translation(Vector(centre)) @ Euler(rot, "XYZ").to_matrix().to_4x4()
        bmesh.ops.create_cone(
            sub, cap_ends=True, cap_tris=False, segments=max(4, segments),
            radius1=rayon_bas, radius2=rayon_haut, depth=hauteur, matrix=m,
        )
        self._ajouter_sous_bm(sub, mat, smooth=smooth)

    def revolution(self, centre_sol: tuple[float, float, float], profil_rz: list[tuple[float, float]],
                   segments: int, mat: str, rot: tuple[float, float, float] = (0.0, 0.0, 0.0),
                   smooth: bool = True, fermer_haut: bool = True, fermer_bas: bool = True) -> None:
        """Surface de révolution autour de Z à partir d'une liste [(rayon, z), ...]."""
        sub = bmesh.new()
        anneaux = []
        segs = max(5, segments)
        for r, z in profil_rz:
            ring = []
            for i in range(segs):
                a = 2.0 * math.pi * i / segs
                ring.append(sub.verts.new((math.cos(a) * r, math.sin(a) * r, z)))
            anneaux.append(ring)
        for k in range(len(anneaux) - 1):
            r0, r1 = anneaux[k], anneaux[k + 1]
            for i in range(segs):
                ni = (i + 1) % segs
                sub.faces.new((r0[i], r0[ni], r1[ni], r1[i]))
        if fermer_bas and profil_rz[0][0] > 1e-4:
            sub.faces.new(list(reversed(anneaux[0])))
        if fermer_haut and profil_rz[-1][0] > 1e-4:
            sub.faces.new(anneaux[-1])
        m = Matrix.Translation(Vector(centre_sol)) @ Euler(rot, "XYZ").to_matrix().to_4x4()
        bmesh.ops.transform(sub, matrix=m, verts=sub.verts)
        self._ajouter_sous_bm(sub, mat, smooth=smooth)

    def corbeau_galbe(self, x: float, y: float, z_haut: float, direction_xy: tuple[float, float],
                      largeur: float, saillie: float, hauteur: float, mat: str) -> None:
        """Corbeau médiéval en console courbée en S soutenant encorbellement ou mâchicoulis."""
        dx, dy = direction_xy
        ang = math.atan2(dy, dx)
        # Profil 2D (s = saillie vers +X local, z relatif à z_haut)
        etapes = 5 if self.lod == 0 else 2
        pts_courbe = []
        for i in range(etapes + 1):
            t = i / etapes
            # Courbe en S douce du haut (saillie) vers le bas (mur)
            s = saillie * (1.0 - 0.5 * (1.0 - math.cos(math.pi * t)))
            z = -hauteur * t
            pts_courbe.append((s, z))
        poly = [(0.0, 0.0), (saillie, 0.0)] + pts_courbe[1:] + [(0.0, -hauteur)]
        sub = bmesh.new()
        hy = largeur * 0.5
        face_g = [sub.verts.new((px, -hy, pz)) for px, pz in poly]
        face_d = [sub.verts.new((px, hy, pz)) for px, pz in poly]
        sub.faces.new(face_g)
        sub.faces.new(list(reversed(face_d)))
        n = len(poly)
        for i in range(n):
            ni = (i + 1) % n
            sub.faces.new((face_g[i], face_g[ni], face_d[ni], face_d[i]))
        m = Matrix.Translation(Vector((x, y, z_haut))) @ Euler((0.0, 0.0, ang), "XYZ").to_matrix().to_4x4()
        bmesh.ops.transform(sub, matrix=m, verts=sub.verts)
        self._ajouter_sous_bm(sub, mat, smooth=False)

    def chainage_angle(self, x_coin: float, y_coin: float, z0: float, z1: float,
                       sx: float, sy: float, mat: str) -> None:
        """Pierres d'angle en harpe (alternance longue/courte biseautée)."""
        if self.lod >= 2:
            return
        nb = max(3, int((z1 - z0) / (0.34 if self.lod == 0 else 0.56)))
        dz = (z1 - z0) / nb
        for i in range(nb):
            long_x = 0.52 if i % 2 == 0 else 0.30
            long_y = 0.30 if i % 2 == 0 else 0.52
            cx = x_coin - sx * (long_x * 0.5 - 0.05)
            cy = y_coin - sy * (long_y * 0.5 - 0.05)
            cz = z0 + (i + 0.5) * dz
            self.boite((cx, cy, cz), (long_x, long_y, dz * 0.90), mat, chanfrein=0.022)

    def panneau_colombage(self, x0: float, x1: float, y_mur: float, z0: float, z1: float,
                          axe: str, sens_ext: float, nb_travees: int, mat_bois: str,
                          croix_indices: tuple[int, ...] = ()) -> None:
        """Vraie ossature bois de colombage en relief 3D (+6 cm devant le torchis)."""
        ep = 0.09
        larg = 0.14
        decal = sens_ext * (ep * 0.45)

        def pt(u: float, z: float) -> tuple[float, float, float]:
            return (u, y_mur + decal, z) if axe == "x" else (y_mur + decal, u, z)

        # Sablières basse, haute et intermédiaire
        self.poutre(pt(x0, z0 + 0.07), pt(x1, z0 + 0.07), larg, ep, mat_bois)
        self.poutre(pt(x0, z1 - 0.07), pt(x1, z1 - 0.07), larg, ep, mat_bois)
        if self.lod <= 1:
            z_mid = z0 + (z1 - z0) * 0.34
            self.poutre(pt(x0, z_mid), pt(x1, z_mid), larg * 0.85, ep * 0.85, mat_bois)
        # Poteaux verticaux
        du = (x1 - x0) / nb_travees
        for i in range(nb_travees + 1):
            u = x0 + i * du
            self.poutre(pt(u, z0), pt(u, z1), larg, ep, mat_bois)
        # Croix de Saint-André et décharges obliques (LOD0/1)
        if self.lod == 0:
            z_mid = z0 + (z1 - z0) * 0.34
            for i in range(nb_travees):
                ua, ub = x0 + i * du, x0 + (i + 1) * du
                if i in croix_indices:
                    self.poutre(pt(ua + 0.06, z0 + 0.10), pt(ub - 0.06, z_mid - 0.06), larg * 0.72, ep * 0.75, mat_bois)
                    self.poutre(pt(ua + 0.06, z_mid - 0.06), pt(ub - 0.06, z0 + 0.10), larg * 0.72, ep * 0.75, mat_bois)
                elif i == 0:
                    self.poutre(pt(ua + 0.06, z0 + 0.10), pt(ub - 0.06, z1 - 0.10), larg * 0.72, ep * 0.75, mat_bois)
                elif i == nb_travees - 1:
                    self.poutre(pt(ub - 0.06, z0 + 0.10), pt(ua + 0.06, z1 - 0.10), larg * 0.72, ep * 0.75, mat_bois)

    def fenetre_medievale(self, pos: tuple[float, float, float], axe: str, sens_ext: float,
                          largeur: float, hauteur: float, mat_bois: str, mat_volet: str,
                          mat_verre: str, mat_pierre: str, volets: bool = True) -> None:
        """Fenêtre creusée avec appui en pierre, meneaux en croix, verre plombé et volets ferrés."""
        x, y, z = pos
        if self.lod == 2:
            t = (largeur, 0.10, hauteur) if axe == "x" else (0.10, largeur, hauteur)
            self.boite(pos, t, mat_bois)
            return

        def loc(du: float, dn: float, dz: float) -> tuple[float, float, float]:
            if axe == "x":
                return (x + du, y + sens_ext * dn, z + dz)
            return (x + sens_ext * dn, y + du, z + dz)

        def dim(lu: float, ln: float, lz: float) -> tuple[float, float, float]:
            return (lu, ln, lz) if axe == "x" else (ln, lu, lz)

        # Vitrage plombé en retrait + encadrement saillant
        self.boite(loc(0, 0.01, 0), dim(largeur * 0.88, 0.04, hauteur * 0.88), mat_verre)
        # Cadre (4 montants)
        self.boite(loc(0, 0.06, hauteur * 0.5), dim(largeur + 0.16, 0.12, 0.11), mat_bois, chanfrein=0.015)
        self.boite(loc(0, 0.08, -hauteur * 0.5), dim(largeur + 0.24, 0.18, 0.12), mat_pierre, chanfrein=0.018)
        for su in (-1.0, 1.0):
            self.boite(loc(su * (largeur * 0.5 + 0.03), 0.055, 0), dim(0.10, 0.11, hauteur), mat_bois, chanfrein=0.012)
        # Meneaux en croix (LOD0)
        if self.lod == 0:
            self.boite(loc(0, 0.04, 0), dim(0.055, 0.05, hauteur * 0.90), mat_bois)
            self.boite(loc(0, 0.04, 0.04), dim(largeur * 0.90, 0.05, 0.055), mat_bois)
        # Deux volets ouverts en planches rainurées + pentures fer
        if volets:
            lv = largeur * 0.46
            for su in (-1.0, 1.0):
                ou = su * (largeur * 0.5 + lv * 0.52 + 0.05)
                self.boite(loc(ou, 0.075, 0), dim(lv, 0.055, hauteur * 0.96), mat_volet, chanfrein=0.01)
                if self.lod == 0:
                    for hz in (-hauteur * 0.28, hauteur * 0.28):
                        self.boite(loc(ou, 0.105, hz), dim(lv * 0.85, 0.025, 0.05), "metal")

    def porte_cintree(self, centre_sol: tuple[float, float, float], sens_y: float,
                      largeur: float, hauteur: float, mat_arc: str, mat_bois: str, mat_fer: str) -> None:
        """Porte médiévale cintrée à 11 voussoirs de pierre, planches rainurées, pentures et marches."""
        x, y, z0 = centre_sol
        r = largeur * 0.5
        z_imp = z0 + hauteur - r
        # Seuil en 2 marches de pierre biseautées
        self.boite((x, y + sens_y * 0.24, z0 + 0.08), (largeur + 0.55, 0.48, 0.16), mat_arc, chanfrein=0.02)
        self.boite((x, y + sens_y * 0.12, z0 + 0.21), (largeur + 0.34, 0.28, 0.12), mat_arc, chanfrein=0.018)
        # Vantail en chêne renfoncé + planches verticales en relief
        self.boite((x, y + sens_y * 0.02, z0 + (hauteur - r * 0.35) * 0.5 + 0.12), (largeur * 0.96, 0.08, hauteur - r * 0.35), mat_bois)
        if self.lod == 0:
            for i in range(-2, 3):
                self.boite((x + i * (largeur * 0.18), y + sens_y * 0.065, z0 + (hauteur - r * 0.5) * 0.5 + 0.14),
                           (largeur * 0.16, 0.03, hauteur - r * 0.55), mat_bois, chanfrein=0.008)
            for hz in (z0 + 0.65, z0 + 1.38):
                self.boite((x, y + sens_y * 0.09, hz), (largeur * 0.86, 0.03, 0.075), mat_fer)
            self.cylindre((x + largeur * 0.28, y + sens_y * 0.11, z0 + 1.05), 0.07, 0.07, 0.03, 10, mat_fer, rot=(math.pi * 0.5, 0, 0))
        # Piédroits en pierre
        nb_p = 5 if self.lod == 0 else 2
        hp = (z_imp - z0) / nb_p
        for sx in (-1.0, 1.0):
            for i in range(nb_p):
                self.boite((x + sx * (r + 0.14), y + sens_y * 0.09, z0 + (i + 0.5) * hp),
                           (0.28, 0.22, hp * 0.92), mat_arc, chanfrein=0.018)
        # Arc de voussoirs en plein cintre
        nb_v = 11 if self.lod == 0 else (7 if self.lod == 1 else 5)
        for i in range(nb_v):
            a = math.pi * (i + 0.5) / nb_v
            vx = x + math.cos(a) * (r + 0.13)
            vz = z_imp + math.sin(a) * (r + 0.13)
            self.boite((vx, y + sens_y * 0.10, vz), (0.28, 0.24, (math.pi * (r + 0.13) / nb_v) * 0.90),
                       mat_arc, rot=(0.0, a - math.pi * 0.5, 0.0), chanfrein=0.016)

    def toit_detaille(self, centre_base: tuple[float, float, float], longueur_x: float,
                      largeur_y: float, hauteur_z: float, mat_toit: str, mat_pignon: str,
                      mat_bois: str, *, debord_x: float = 0.36, debord_y: float = 0.42,
                      epaisseur: float = 0.16, strates: int = 0) -> None:
        """Toit à deux pans avec pignons, chevrons, pannes débordantes, strates de tuiles/chaume et faîtière."""
        cx, cy, cz = centre_base
        hx, hy = longueur_x * 0.5, largeur_y * 0.5
        # Pignons pleins
        sub = bmesh.new()
        v0 = sub.verts.new((cx - hx, cy - hy, cz))
        v1 = sub.verts.new((cx + hx, cy - hy, cz))
        v2 = sub.verts.new((cx + hx, cy + hy, cz))
        v3 = sub.verts.new((cx - hx, cy + hy, cz))
        v4 = sub.verts.new((cx - hx, cy, cz + hauteur_z))
        v5 = sub.verts.new((cx + hx, cy, cz + hauteur_z))
        for loop in ((v0, v3, v4), (v1, v5, v2), (v0, v1, v2, v3)):
            sub.faces.new(loop)
        self._ajouter_sous_bm(sub, mat_pignon, smooth=False)

        pente = math.atan2(hauteur_z, hy)
        long_pan = math.hypot(hy + debord_y, hauteur_z) + 0.10
        tot_x = longueur_x + 2.0 * debord_x

        for signe in (-1.0, 1.0):
            mid_y = cy + signe * (hy * 0.5 + debord_y * 0.36)
            mid_z = cz + hauteur_z * 0.5 - debord_y * 0.36 * math.tan(pente) + epaisseur * 0.42
            self.boite((cx, mid_y, mid_z), (tot_x, long_pan, epaisseur), mat_toit, rot=(-signe * pente, 0.0, 0.0))
            # Chevrons de rive en bois aux extrémités X (LOD0/1)
            if self.lod <= 1:
                for sx in (-1.0, 1.0):
                    rx = cx + sx * (tot_x * 0.5 - 0.06)
                    self.boite((rx, mid_y, mid_z - epaisseur * 0.55), (0.11, long_pan * 0.98, 0.14),
                               mat_bois, rot=(-signe * pente, 0.0, 0.0), chanfrein=0.012)
            # Strates de tuiles/chaume en léger relief (LOD0)
            if self.lod == 0 and strates > 0:
                for k in range(strates):
                    t = (k + 0.5) / strates
                    sy = cy + signe * ((hy + debord_y) * (1.0 - t))
                    sz = cz + hauteur_z * t - debord_y * (1.0 - t) * math.tan(pente) + epaisseur * 0.95
                    self.boite((cx, sy, sz), (tot_x + 0.02, (long_pan / strates) * 0.92, 0.045),
                               mat_toit, rot=(-signe * (pente - 0.06), 0.0, 0.0))
        # Pannes débordantes sous les pignons (LOD0)
        if self.lod == 0:
            for t in (0.35, 0.70, 0.97):
                for signe in (-1.0, 1.0):
                    if t > 0.95 and signe < 0:
                        continue
                    py = cy + (0.0 if t > 0.95 else signe * hy * (1.0 - t))
                    pz = cz + hauteur_z * t - 0.10
                    self.boite((cx, py, pz), (tot_x + 0.24, 0.14, 0.16), mat_bois, chanfrein=0.015)
        # Faîtière profilée
        self.cylindre((cx, cy, cz + hauteur_z + epaisseur * 0.62), 0.15, 0.15, tot_x + 0.06,
                      10 if self.lod == 0 else 6, mat_toit, rot=(0.0, math.pi * 0.5, 0.0), smooth=True)

    def tonneau_bombe(self, centre_sol: tuple[float, float, float], rayon_base: float,
                      rayon_ventre: float, hauteur: float, mat_bois: str, mat_fer: str) -> None:
        """Tonneau galbé par révolution avec 4 cercles de fer forgé en relief."""
        segs = (16, 10, 6)[self.lod]
        profil = []
        etapes = 6 if self.lod == 0 else 3
        for i in range(etapes + 1):
            t = i / etapes
            r = rayon_base + (rayon_ventre - rayon_base) * math.sin(math.pi * t)
            profil.append((r, hauteur * t))
        self.revolution(centre_sol, profil, segs, mat_bois, smooth=True)
        if self.lod <= 1:
            cercles = (0.14, 0.34, 0.66, 0.86) if self.lod == 0 else (0.20, 0.80)
            for tc in cercles:
                rc = rayon_base + (rayon_ventre - rayon_base) * math.sin(math.pi * tc) + 0.014
                self.cylindre((centre_sol[0], centre_sol[1], centre_sol[2] + hauteur * tc),
                              rc, rc, 0.045, segs, mat_fer, smooth=True)

    def sac_noue(self, centre_sol: tuple[float, float, float], rx: float, ry: float, rz: float,
                 rot_z: float, mat_jute: str, mat_corde: str) -> None:
        """Sac de grain organique : base posée, ventre rebondi, col pincé par corde et oreilles."""
        segs = (14, 8, 6)[self.lod]
        profil_rz = [
            (0.65, 0.00),
            (0.95, 0.12),
            (1.02, 0.38),
            (0.88, 0.68),
            (0.42, 0.84),  # col pincé
            (0.58, 1.00),  # oreilles évasées
        ] if self.lod == 0 else [(0.70, 0.0), (1.0, 0.42), (0.45, 0.85), (0.55, 1.0)]
        sub = bmesh.new()
        anneaux = []
        for idx_p, (r, tz) in enumerate(profil_rz):
            ring = []
            for i in range(segs):
                a = 2.0 * math.pi * i / segs
                # Légère ondulation organique déterministe des plis de toile
                pli = 1.0 + (0.06 * math.sin(a * 3.0 + idx_p * 1.1) + 0.04 * math.cos(a * 5.0)) * (1.0 if self.lod == 0 else 0.3)
                ring.append(sub.verts.new((math.cos(a) * rx * r * pli, math.sin(a) * ry * r * pli, rz * tz)))
            anneaux.append(ring)
        for k in range(len(anneaux) - 1):
            r0, r1 = anneaux[k], anneaux[k + 1]
            for i in range(segs):
                ni = (i + 1) % segs
                sub.faces.new((r0[i], r0[ni], r1[ni], r1[i]))
        sub.faces.new(list(reversed(anneaux[0])))
        sub.faces.new(anneaux[-1])
        m = Matrix.Translation(Vector(centre_sol)) @ Euler((0.0, 0.0, rot_z), "XYZ").to_matrix().to_4x4()
        bmesh.ops.transform(sub, matrix=m, verts=sub.verts)
        self._ajouter_sous_bm(sub, mat_jute, smooth=True)
        # Lien de corde autour du col
        if self.lod <= 1:
            self.cylindre((centre_sol[0], centre_sol[1], centre_sol[2] + rz * 0.83),
                          min(rx, ry) * 0.46, min(rx, ry) * 0.46, rz * 0.07, segs, mat_corde, smooth=True)

    def roue_rayons(self, centre: tuple[float, float, float], rayon: float, epaisseur: float,
                    nb_rayons: int, mat_bois: str, mat_fer: str) -> None:
        """Roue médiévale creuse : jante en segments, bandage fer, moyeu et vrais rayons."""
        segs = (16, 10, 6)[self.lod]
        cx, cy, cz = centre
        if self.lod == 2:
            self.cylindre(centre, rayon, rayon, epaisseur, segs, mat_bois, rot=(math.pi * 0.5, 0, 0), smooth=True)
            return
        # Moyeu central
        self.cylindre(centre, rayon * 0.22, rayon * 0.22, epaisseur * 1.8, max(6, segs // 2), mat_bois,
                      rot=(math.pi * 0.5, 0, 0), smooth=True)
        self.cylindre(centre, rayon * 0.12, rayon * 0.12, epaisseur * 2.1, max(6, segs // 2), mat_fer,
                      rot=(math.pi * 0.5, 0, 0), smooth=True)
        # Jante creuse composée de voussoirs bois + bandage fer
        r_int = rayon * 0.82
        r_mid = (rayon + r_int) * 0.5
        corde = 2.0 * math.pi * r_mid / segs * 1.04
        for i in range(segs):
            a = 2.0 * math.pi * i / segs
            px, pz = cx + math.cos(a) * r_mid, cz + math.sin(a) * r_mid
            self.boite((px, cy, pz), (rayon - r_int, epaisseur, corde), mat_bois, rot=(0.0, -a, 0.0))
            fx, fz = cx + math.cos(a) * (rayon + 0.012), cz + math.sin(a) * (rayon + 0.012)
            self.boite((fx, cy, fz), (0.028, epaisseur * 1.06, corde * 1.06), mat_fer, rot=(0.0, -a, 0.0))
        # Rayons
        nr = nb_rayons if self.lod == 0 else max(4, nb_rayons // 2)
        for i in range(nr):
            a = 2.0 * math.pi * i / nr
            p1 = (cx + math.cos(a) * rayon * 0.18, cy, cz + math.sin(a) * rayon * 0.18)
            p2 = (cx + math.cos(a) * r_int, cy, cz + math.sin(a) * r_int)
            self.poutre(p1, p2, epaisseur * 0.55, epaisseur * 0.55, mat_bois, chanfrein=0.005)

    def banniere_ondulee(self, centre_haut: tuple[float, float, float], largeur: float,
                         hauteur: float, mat_tissu: str, mat_or: str) -> None:
        """Étendard flottant ondulé au vent avec découpe en double flamme et galon doré."""
        nx = 8 if self.lod == 0 else (5 if self.lod == 1 else 3)
        nz = 12 if self.lod == 0 else (6 if self.lod == 1 else 4)
        cx, cy, cz = centre_haut
        ep = 0.022
        sub = bmesh.new()
        grille_av, grille_ar = [], []
        for iz in range(nz + 1):
            tz = iz / nz  # 0 en haut, 1 en bas
            row_av, row_ar = [], []
            for ix in range(nx + 1):
                tx = ix / nx - 0.5  # -0.5..0.5
                # Découpe en V au bas de la bannière (double flamme)
                encoche = (1.0 - abs(tx) * 2.0) * 0.24 * (tz ** 2)
                z = cz - hauteur * (tz - encoche)
                x = cx + tx * largeur
                onde = math.sin(tz * 4.8 + tx * 2.4) * 0.085 * tz + 0.04 * (tz ** 1.5)
                row_av.append(sub.verts.new((x, cy + onde - ep * 0.5, z)))
                row_ar.append(sub.verts.new((x, cy + onde + ep * 0.5, z)))
            grille_av.append(row_av)
            grille_ar.append(row_ar)
        for iz in range(nz):
            for ix in range(nx):
                sub.faces.new((grille_av[iz][ix], grille_av[iz][ix + 1], grille_av[iz + 1][ix + 1], grille_av[iz + 1][ix]))
                sub.faces.new((grille_ar[iz][ix], grille_ar[iz + 1][ix], grille_ar[iz + 1][ix + 1], grille_ar[iz][ix + 1]))
        # Fermer les 4 bords
        for ix in range(nx):
            sub.faces.new((grille_av[0][ix], grille_ar[0][ix], grille_ar[0][ix + 1], grille_av[0][ix + 1]))
            sub.faces.new((grille_av[nz][ix], grille_av[nz][ix + 1], grille_ar[nz][ix + 1], grille_ar[nz][ix]))
        for iz in range(nz):
            sub.faces.new((grille_av[iz][0], grille_av[iz + 1][0], grille_ar[iz + 1][0], grille_ar[iz][0]))
            sub.faces.new((grille_av[iz][nx], grille_ar[iz][nx], grille_ar[iz + 1][nx], grille_av[iz + 1][nx]))
        self._ajouter_sous_bm(sub, mat_tissu, smooth=True)
        # Galon doré supérieur
        self.boite((cx, cy + 0.005, cz - 0.04), (largeur * 1.02, 0.045, 0.065), mat_or, chanfrein=0.008)

    def ecu_galbe(self, centre: tuple[float, float, float], largeur: float, hauteur: float,
                  rot: tuple[float, float, float], mat_bord: str, mat_champ: str, mat_or: str) -> None:
        """Écu gothique en pointe réellement profilé et galbé."""
        # Contour 2D de l'écu (demi-largeur normalisée, z normalisé)
        pts = [
            (-0.50, 0.50), (0.50, 0.50), (0.49, 0.14), (0.42, -0.14),
            (0.26, -0.36), (0.0, -0.52), (-0.26, -0.36), (-0.42, -0.14), (-0.49, 0.14),
        ]

        def construire_plaque(echelle: float, ep: float, decal_y: float, mat: str):
            sub = bmesh.new()
            av, ar = [], []
            for px, pz in pts:
                x = px * largeur * echelle
                z = pz * hauteur * echelle
                galbe = -0.055 * (px * 2.0) ** 2 * largeur
                av.append(sub.verts.new((x, decal_y + galbe - ep * 0.5, z)))
                ar.append(sub.verts.new((x, decal_y + galbe + ep * 0.5, z)))
            sub.faces.new(av)
            sub.faces.new(list(reversed(ar)))
            n = len(pts)
            for i in range(n):
                ni = (i + 1) % n
                sub.faces.new((av[i], ar[i], ar[ni], av[ni]))
            m = Matrix.Translation(Vector(centre)) @ Euler(rot, "XYZ").to_matrix().to_4x4()
            bmesh.ops.transform(sub, matrix=m, verts=sub.verts)
            self._ajouter_sous_bm(sub, mat, smooth=False)

        construire_plaque(1.0, 0.055, 0.0, mat_bord)
        construire_plaque(0.86, 0.030, -0.032, mat_champ)
        if self.lod <= 1:
            # Croix dorée en relief sur le champ
            m_rot = Matrix.Translation(Vector(centre)) @ Euler(rot, "XYZ").to_matrix().to_4x4()
            for dx, dz, sx, sz in ((0, 0.02, 0.12, 0.78), (0, 0.10, 0.72, 0.11)):
                sub = bmesh.new()
                bmesh.ops.create_cube(sub, size=1.0, matrix=Matrix.Diagonal((sx * largeur, 0.028, sz * hauteur, 1.0)))
                bmesh.ops.transform(sub, matrix=m_rot @ Matrix.Translation((dx * largeur, -0.052, dz * hauteur)), verts=sub.verts)
                self._ajouter_sous_bm(sub, mat_or, smooth=False)

    def anneau_creneaux(self, z_base: float, cx: float, cy: float, rayon: float,
                        nb: int, largeur: float, profondeur: float, hauteur: float, mat: str) -> None:
        for i in range(nb):
            a = 2.0 * math.pi * i / nb
            x = cx + math.cos(a) * rayon
            y = cy + math.sin(a) * rayon
            self.boite((x, y, z_base + hauteur * 0.5), (profondeur, largeur, hauteur), mat,
                       rot=(0.0, 0.0, a), chanfrein=0.015)

    def finaliser(self, nom: str) -> bpy.types.Object:
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        bmesh.ops.triangulate(self.bm, faces=self.bm.faces)
        if self.bm.verts:
            z_min = min(v.co.z for v in self.bm.verts)
            if abs(z_min) > 1e-5:
                bmesh.ops.translate(self.bm, verts=self.bm.verts, vec=(0.0, 0.0, -z_min))

        uv_layer = self.bm.loops.layers.uv.verify()
        inv = 1.0 / max(self.echelle_uv, 0.1)
        for face in self.bm.faces:
            nx, ny, nz = abs(face.normal.x), abs(face.normal.y), abs(face.normal.z)
            for loop in face.loops:
                co = loop.vert.co
                if nz >= nx and nz >= ny:
                    u, v = co.x * inv, co.y * inv
                elif nx >= ny:
                    u, v = co.y * inv, co.z * inv
                else:
                    u, v = co.x * inv, co.z * inv
                loop[uv_layer].uv = (u, v)

        mesh = bpy.data.meshes.new(nom)
        self.bm.to_mesh(mesh)
        self.bm.free()

        for cle in self.noms_mat:
            mesh.materials.append(self.palette[cle])

        obj = bpy.data.objects.new(nom, mesh)
        bpy.context.scene.collection.objects.link(obj)
        return obj


# ---------------------------------------------------------------------------
# PACK 1 — 4 Pions 3D haute géométrie pour la carte de 1400 (Étape 2)
# ---------------------------------------------------------------------------

def construire_pion_armee(c: Constructeur, lod: int) -> None:
    segs = (28, 16, 10)[lod]
    # Socle circulaire mouluré en pierre + couronne d'or vieilli
    c.revolution((0, 0, 0), [(0.78, 0.0), (0.78, 0.07), (0.72, 0.12), (0.72, 0.16), (0.64, 0.21), (0.62, 0.21)], segs, "pierre")
    if lod <= 1:
        c.revolution((0, 0, 0.12), [(0.745, 0.0), (0.745, 0.045), (0.71, 0.06)], segs, "or")
    # Hampe principale ferrée + fer de lance taillé en losange
    c.cylindre((0.0, -0.02, 1.38), 0.045, 0.036, 2.38, max(8, segs // 2), "bois", smooth=True)
    c.cylindre((0.0, -0.02, 2.58), 0.06, 0.05, 0.12, max(8, segs // 2), "or", smooth=True)
    c.cylindre((0.0, -0.02, 2.80), 0.078, 0.004, 0.34, 4, "metal")
    # Traverse ouvragée à deux pommeaux dorés
    c.cylindre((0.0, -0.02, 2.34), 0.032, 0.032, 1.06, max(6, segs // 2), "or", rot=(0.0, math.pi * 0.5, 0.0), smooth=True)
    if lod <= 1:
        for sx in (-0.55, 0.55):
            c.revolution((sx, -0.02, 2.28), [(0.02, 0.0), (0.06, 0.06), (0.02, 0.12)], 10, "or")
    # Bannière réellement ondulée au vent
    c.banniere_ondulee((0.0, 0.03, 2.31), 0.86, 1.24, "banniere", "or")
    # Écu gothique galbé en pointe au premier plan
    c.ecu_galbe((0.0, -0.34, 0.72), 0.62, 0.82, (-0.18, 0.0, 0.0), "metal", "banniere", "or")
    # Bassinet médiéval posé à côté du bouclier (LOD0/1)
    if lod <= 1:
        c.revolution((0.36, -0.26, 0.21), [(0.17, 0.0), (0.18, 0.12), (0.15, 0.24), (0.08, 0.32), (0.01, 0.36)],
                     14 if lod == 0 else 8, "metal", smooth=True)
        if lod == 0:
            c.boite((0.36, -0.41, 0.32), (0.18, 0.06, 0.08), "metal", rot=(0.25, 0, 0), chanfrein=0.01)
    # 4 lances encadrant la bannière (fers en losange + viroles dorées)
    if lod == 0:
        for sx in (-1.0, 1.0):
            for sy in (-0.22, 0.26):
                p1 = (sx * 0.36, sy * 0.85, 0.20)
                p2 = (sx * 0.62, sy * 1.15, 2.15)
                c.poutre(p1, p2, 0.042, 0.042, "bois", chanfrein=0.006)
                c.cylindre((p2[0] + sx * 0.02, p2[1], p2[2] + 0.14), 0.055, 0.004, 0.28, 4, "metal",
                           rot=(sy * 0.15, sx * 0.12, 0.0))
    elif lod == 1:
        for sx in (-1.0, 1.0):
            c.poutre((sx * 0.42, 0.04, 0.20), (sx * 0.60, 0.08, 2.05), 0.045, 0.045, "bois", chanfrein=0.0)


def construire_pion_siege(c: Constructeur, lod: int) -> None:
    segs = (24, 14, 8)[lod]
    # Socle circulaire de terre battue cerclé d'un muret de pierre
    c.revolution((0, 0, 0), [(1.04, 0.0), (1.02, 0.12), (0.94, 0.16)], segs, "pierre", smooth=False)
    c.cylindre((0, 0, 0.14), 0.94, 0.93, 0.05, segs, "terre")
    # Pavillon médiéval octogonal à parois galbées, toit conique plissé et oriflamme ondulé
    px, py = -0.30, 0.22
    c.revolution((px, py, 0.16), [(0.48, 0.0), (0.45, 0.42), (0.43, 0.78)], 8, "toile", smooth=False)
    c.revolution((px, py, 0.90), [(0.54, 0.0), (0.34, 0.24), (0.14, 0.48), (0.02, 0.66)], 8, "banniere", smooth=False)
    if lod <= 1:
        # Lambrequin festonné doré en bordure du pavillon
        c.revolution((px, py, 0.84), [(0.54, 0.0), (0.55, 0.08)], 8, "or", smooth=False)
        c.cylindre((px, py, 1.72), 0.022, 0.018, 0.44, 8, "or", smooth=True)
        c.banniere_ondulee((px + 0.16, py, 1.92), 0.34, 0.20, "banniere", "or")
        if lod == 0:
            # 6 haubans tendus vers des piquets
            for i in range(6):
                a = 2.0 * math.pi * i / 6.0 + 0.3
                p_haut = (px + math.cos(a) * 0.50, py + math.sin(a) * 0.50, 0.90)
                p_bas = (px + math.cos(a) * 0.68, py + math.sin(a) * 0.68, 0.18)
                c.poutre(p_haut, p_bas, 0.014, 0.014, "corde", chanfrein=0.0)
    # Bélier de siège détaillé à charpente apparente et 4 roues à rayons
    bx, by = 0.34, -0.20
    c.boite((bx, by, 0.32), (0.72, 0.46, 0.06), "bois", chanfrein=0.008)
    for sx in (-0.30, 0.30):
        for sy in (-0.20, 0.20):
            c.boite((bx + sx, by + sy, 0.52), (0.06, 0.06, 0.42), "bois")
    c.toit_detaille((bx, by, 0.66), 0.72, 0.48, 0.28, "bois_clair", "bois", "bois", debord_x=0.06, debord_y=0.06, epaisseur=0.05)
    # Poutre de bélier + tête ferrée
    c.cylindre((bx + 0.06, by, 0.44), 0.072, 0.062, 1.04, max(8, segs // 2), "bois_clair", rot=(0.0, math.pi * 0.5, 0.0), smooth=True)
    c.cylindre((bx + 0.60, by, 0.44), 0.095, 0.072, 0.16, 8, "metal", rot=(0.0, math.pi * 0.5, 0.0), smooth=True)
    for sx in (-0.20, 0.20):
        for sy in (-0.25, 0.25):
            c.roue_rayons((bx + sx, by + sy, 0.26), 0.14, 0.045, 6, "bois", "metal")
    # Palissade courbe de pieux épointés + gabions (LOD0/1)
    if lod <= 1:
        nb_p = 11 if lod == 0 else 5
        for i in range(nb_p):
            a = -1.25 + i * (2.5 / max(1, nb_p - 1))
            rx, ry = math.cos(a) * 0.86, math.sin(a) * 0.86 - 0.04
            c.cylindre((rx, ry, 0.42), 0.046, 0.012, 0.58, 6, "bois", rot=(0.0, 0.22, a))
        if lod == 0:
            for gx, gy in ((0.62, 0.46), (-0.68, -0.44), (-0.42, -0.68)):
                c.cylindre((gx, gy, 0.34), 0.13, 0.13, 0.36, 10, "jute", smooth=True)
                c.cylindre((gx, gy, 0.51), 0.11, 0.11, 0.04, 10, "terre")


def construire_pion_capitale(c: Constructeur, lod: int) -> None:
    segs = (18, 12, 8)[lod]
    # Socle octogonal mouluré pierre + filet doré
    c.revolution((0, 0, 0), [(1.46, 0.0), (1.44, 0.14), (1.36, 0.22)], 8, "pierre", smooth=False)
    c.cylindre((0, 0, 0.20), 1.32, 1.32, 0.06, 8, "paves")
    if lod <= 1:
        c.revolution((0, 0, 0.11), [(1.46, 0.0), (1.46, 0.035), (1.42, 0.05)], 8, "or", smooth=False)
    # Enceinte carrée crénelée + courtines
    for sx in (-0.86, 0.86):
        c.boite((sx, 0, 0.62), (0.24, 1.66, 0.78), "pierre_claire", chanfrein=0.018)
    c.boite((0, 0.86, 0.62), (1.66, 0.24, 0.78), "pierre_claire", chanfrein=0.018)
    c.boite((-0.54, -0.86, 0.62), (0.64, 0.24, 0.78), "pierre_claire", chanfrein=0.018)
    c.boite((0.54, -0.86, 0.62), (0.64, 0.24, 0.78), "pierre_claire", chanfrein=0.018)
    # Châtelet d'entrée à deux tourelles et pont-levis
    c.boite((0.0, -0.88, 0.88), (0.56, 0.32, 0.44), "pierre_taille", chanfrein=0.015)
    c.boite((0.0, -1.04, 0.46), (0.34, 0.06, 0.48), "bois", chanfrein=0.01)
    for sx in (-0.30, 0.30):
        c.cylindre((sx, -0.94, 0.68), 0.13, 0.12, 0.90, max(8, segs - 4), "pierre_taille", smooth=True)
        c.cylindre((sx, -0.94, 1.28), 0.16, 0.015, 0.34, max(8, segs - 4), "tuiles", smooth=True)
    # 4 tours d'angle à mâchicoulis et poivrières coniques
    for sx in (-0.90, 0.90):
        for sy in (-0.90, 0.90):
            c.cylindre((sx, sy, 0.80), 0.30, 0.26, 1.18, segs, "pierre_claire", smooth=True)
            c.cylindre((sx, sy, 1.44), 0.31, 0.31, 0.14, segs, "pierre_taille", smooth=True)
            if lod == 0:
                c.anneau_creneaux(1.48, sx, sy, 0.28, 8, 0.10, 0.07, 0.14, "pierre_taille")
            c.cylindre((sx, sy, 1.84), 0.36, 0.015, 0.62, segs, "tuiles", smooth=True)
            if lod <= 1:
                c.cylindre((sx, sy, 2.20), 0.018, 0.004, 0.18, 6, "or")
    # Grand donjon central à contreforts d'angle, mâchicoulis et bannière ondulée
    c.boite((0, 0.06, 1.24), (1.02, 1.02, 2.02), "pierre_taille", chanfrein=0.025)
    if lod <= 1:
        for sx in (-0.50, 0.50):
            for sy in (-0.44, 0.56):
                c.boite((sx, sy, 1.10), (0.20, 0.20, 1.78), "pierre_claire", chanfrein=0.018)
        # Bandeau de mâchicoulis et créneaux autour du donjon
        c.boite((0, 0.06, 2.24), (1.14, 1.14, 0.16), "pierre_claire", chanfrein=0.018)
        if lod == 0:
            for u in (-0.42, -0.14, 0.14, 0.42):
                for sy in (-0.48, 0.60):
                    c.boite((u, sy, 2.38), (0.14, 0.10, 0.18), "pierre_taille", chanfrein=0.01)
                    c.boite((sy - 0.06, u + 0.06, 2.38), (0.10, 0.14, 0.18), "pierre_taille", chanfrein=0.01)
            # Archères sombres en façade
            for az in (1.18, 1.72):
                c.boite((0.0, -0.46, az), (0.09, 0.05, 0.34), "charbon")
    c.toit_detaille((0, 0.06, 2.34), 1.00, 1.00, 0.64, "tuiles", "pierre_taille", "bois",
                    debord_x=0.10, debord_y=0.10, epaisseur=0.08, strates=4)
    # Bannière royale ondulée au faîte
    c.cylindre((0, 0.06, 3.30), 0.024, 0.018, 0.62, 8, "or", smooth=True)
    c.banniere_ondulee((0.24, 0.06, 3.58), 0.46, 0.26, "banniere", "or")


def construire_pion_bourg(c: Constructeur, lod: int) -> None:
    segs = (20, 12, 8)[lod]
    # Socle circulaire pavé bordé de pierre
    c.revolution((0, 0, 0), [(1.18, 0.0), (1.14, 0.14), (1.08, 0.18)], segs, "pierre", smooth=False)
    c.cylindre((0, 0, 0.16), 1.06, 1.06, 0.05, segs, "paves")
    # Rempart polygonal crénelé
    nb_m = 8
    for i in range(nb_m):
        a = 2.0 * math.pi * i / nb_m + 0.40
        if -1.9 < (a - 2.0 * math.pi) < -1.1 or 4.3 < a < 5.1:
            continue  # ouverture pour la porte Sud
        px, py = math.cos(a) * 0.90, math.sin(a) * 0.90
        c.boite((px, py, 0.46), (0.18, 0.72, 0.56), "pierre_claire", rot=(0.0, 0.0, a), chanfrein=0.014)
        if lod == 0:
            for d in (-0.22, 0.0, 0.22):
                cx = px - math.sin(a) * d
                cy = py + math.cos(a) * d
                c.boite((cx, cy, 0.80), (0.14, 0.13, 0.14), "pierre_taille", rot=(0.0, 0.0, a), chanfrein=0.01)
    # Porte fortifiée Sud à deux tours
    for sx in (-0.34, 0.34):
        c.cylindre((sx, -0.84, 0.56), 0.20, 0.18, 0.78, max(8, segs - 4), "pierre_taille", smooth=True)
        c.cylindre((sx, -0.84, 1.12), 0.24, 0.015, 0.38, max(8, segs - 4), "tuiles", smooth=True)
    c.boite((0, -0.84, 0.62), (0.44, 0.22, 0.34), "pierre_claire", chanfrein=0.012)
    # Beffroi gothique central à contreforts, clocher ouvert et flèche élancée
    c.boite((0.0, 0.18, 0.78), (0.46, 0.46, 1.22), "pierre_taille", chanfrein=0.018)
    if lod <= 1:
        for sx in (-0.22, 0.22):
            for sy in (-0.04, 0.40):
                c.boite((sx, sy, 1.56), (0.10, 0.10, 0.36), "pierre_claire", chanfrein=0.01)
        # Cadran doré d'horloge en façade
        c.cylindre((0.0, -0.06, 1.18), 0.11, 0.11, 0.04, 12, "or", rot=(math.pi * 0.5, 0, 0), smooth=True)
    c.cylindre((0.0, 0.18, 2.08), 0.30, 0.015, 0.74, 4, "tuiles", rot=(0.0, 0.0, math.pi * 0.25))
    # 5 maisons à colombages miniatures autour de la place
    maisons = [
        (-0.46, -0.14, 0.46, 0.34, 0.38, "tuiles", 0.12),
        (0.46, -0.12, 0.44, 0.36, 0.42, "tuiles", -0.15),
        (-0.44, 0.42, 0.44, 0.32, 0.36, "chaume", 0.35),
        (0.46, 0.44, 0.42, 0.32, 0.38, "tuiles", -0.25),
        (0.02, 0.66, 0.50, 0.30, 0.34, "chaume", 0.0),
    ]
    for mx, my, lx, ly, hz, mat_t, rz in maisons[:(5 if lod == 0 else (3 if lod == 1 else 2))]:
        c.boite((mx, my, 0.18 + hz * 0.5), (lx, ly, hz), "colombage", rot=(0.0, 0.0, rz), chanfrein=0.01)
        c.toit_detaille((mx, my, 0.18 + hz), lx, ly, 0.26, mat_t, "torchis", "bois", debord_x=0.04, debord_y=0.04, epaisseur=0.05)


# ---------------------------------------------------------------------------
# PACK 2 — 6 Props de vie urbaine médiévale (améliorés : roues à rayons, sacs noués, tonneaux bombés)
# ---------------------------------------------------------------------------

def construire_prop_charrette(c: Constructeur, lod: int) -> None:
    c.cylindre((0, 0, 0.48), 0.055, 0.055, 1.44, 10 if lod == 0 else 6, "bois", rot=(math.pi * 0.5, 0, 0), smooth=True)
    for sy in (-0.66, 0.66):
        c.roue_rayons((0, sy, 0.48), 0.48, 0.075, 8, "bois_clair", "metal")
    c.boite((-0.05, 0, 0.62), (1.72, 1.08, 0.08), "bois", chanfrein=0.01)
    for sy in (-0.50, 0.50):
        c.boite((-0.05, sy, 0.90), (1.72, 0.06, 0.48), "bois_clair", chanfrein=0.008)
        c.poutre((0.68, sy * 0.86, 0.62), (1.92, sy * 0.70, 0.52), 0.075, 0.075, "bois")
    c.boite((-0.89, 0, 0.90), (0.06, 1.08, 0.48), "bois_clair", chanfrein=0.008)
    c.boite((0.79, 0, 0.84), (0.06, 1.08, 0.36), "bois_clair", chanfrein=0.008)
    if lod <= 1:
        for sx, sy, rz in ((-0.44, -0.20, 0.2), (-0.40, 0.20, -0.3), (0.18, 0.0, 0.6)):
            c.sac_noue((sx, sy, 0.66), 0.30, 0.22, 0.42, rz, "jute", "corde")


def construire_prop_etal_marche(c: Constructeur, lod: int) -> None:
    for sx in (-1.26, 1.26):
        c.boite((sx, -0.58, 1.24), (0.11, 0.11, 2.48), "bois", chanfrein=0.012)
        c.boite((sx, 0.58, 1.06), (0.11, 0.11, 2.12), "bois", chanfrein=0.012)
        if lod == 0:
            c.poutre((sx, -0.58, 1.95), (sx, -0.18, 2.38), 0.08, 0.08, "bois")
    c.boite((0, 0, 0.88), (2.68, 1.18, 0.09), "bois_clair", chanfrein=0.012)
    c.boite((0, -0.52, 0.44), (2.56, 0.08, 0.84), "bois", chanfrein=0.01)
    c.boite((0, 0.0, 2.32), (2.86, 1.66, 0.06), "toile", rot=(-0.24, 0, 0))
    if lod == 0:
        for i in (-1.0, -0.34, 0.34, 1.0):
            c.boite((i, 0.0, 2.35), (0.30, 1.66, 0.03), "banniere", rot=(-0.24, 0, 0))
        c.boite((0, -0.78, 2.42), (2.86, 0.04, 0.20), "banniere")
    if lod <= 1:
        c.boite((-0.78, -0.05, 1.09), (0.58, 0.44, 0.34), "bois_clair", chanfrein=0.012)
        c.boite((0.02, 0.05, 1.06), (0.52, 0.42, 0.28), "bois", chanfrein=0.012)
        c.sac_noue((0.76, 0.0, 0.92), 0.24, 0.20, 0.38, 0.4, "jute", "corde")


def construire_prop_puits_pierre(c: Constructeur, lod: int) -> None:
    segs = (22, 12, 8)[lod]
    c.revolution((0, 0, 0), [(0.86, 0.0), (0.82, 0.14), (0.78, 0.16), (0.76, 0.84), (0.84, 0.86), (0.84, 0.96), (0.64, 0.96)], segs, "pierre_claire", smooth=False)
    c.cylindre((0, 0, 0.76), 0.62, 0.62, 0.04, segs, "eau")
    for sx in (-0.72, 0.72):
        c.boite((sx, 0, 1.32), (0.12, 0.12, 2.16), "bois", chanfrein=0.014)
        if lod == 0:
            c.poutre((sx, 0, 1.88), (sx * 0.48, 0, 2.30), 0.085, 0.085, "bois")
    if lod <= 1:
        c.cylindre((0, 0, 1.56), 0.075, 0.075, 1.50, 10, "bois_clair", rot=(0, math.pi * 0.5, 0), smooth=True)
        c.cylindre((0.86, 0, 1.56), 0.028, 0.028, 0.26, 8, "metal", rot=(0, math.pi * 0.5, 0), smooth=True)
        c.cylindre((0.0, 0, 1.24), 0.016, 0.016, 0.58, 6, "corde", smooth=True)
        c.tonneau_bombe((0.0, 0.0, 0.88), 0.14, 0.16, 0.28, "bois", "metal")
    c.toit_detaille((0, 0, 2.30), 1.66, 1.28, 0.66, "tuiles", "bois", "bois", debord_x=0.14, debord_y=0.18, epaisseur=0.08, strates=4)


def construire_prop_sacs_grain(c: Constructeur, lod: int) -> None:
    c.boite((0, 0, 0.05), (1.56, 1.24, 0.08), "bois", chanfrein=0.01)
    if lod == 0:
        for sy in (-0.44, -0.15, 0.15, 0.44):
            c.boite((0, sy, 0.11), (1.56, 0.22, 0.04), "bois_clair", chanfrein=0.006)
    sacs = [(-0.38, -0.26, 0.13, 0.18), (0.36, -0.24, 0.13, -0.22),
            (-0.36, 0.26, 0.13, -0.14), (0.34, 0.28, 0.13, 0.30)]
    for sx, sy, sz, rz in sacs:
        c.sac_noue((sx, sy, sz), 0.32, 0.24, 0.44, rz, "jute", "corde")
    if lod <= 1:
        c.sac_noue((-0.16, 0.02, 0.46), 0.31, 0.23, 0.42, 0.55, "jute", "corde")
        c.sac_noue((0.28, -0.02, 0.45), 0.29, 0.22, 0.40, -0.45, "jute", "corde")


def construire_prop_echafaudage(c: Constructeur, lod: int) -> None:
    segs = (10, 6, 5)[lod]
    for sx in (-1.45, 1.45):
        for sy in (-0.52, 0.52):
            c.cylindre((sx, sy, 2.20), 0.062, 0.052, 4.40, segs, "bois", smooth=True)
    for z in (1.80, 3.50):
        c.boite((0, 0, z), (3.18, 1.16, 0.07), "bois_clair", chanfrein=0.01)
        c.boite((0, -0.52, z - 0.08), (3.12, 0.08, 0.08), "bois")
        c.boite((0, 0.52, z - 0.08), (3.12, 0.08, 0.08), "bois")
    if lod <= 1:
        c.poutre((-1.45, 0.52, 0.15), (1.45, 0.52, 1.78), 0.065, 0.065, "bois")
        c.poutre((1.45, 0.52, 1.85), (-1.45, 0.52, 3.48), 0.065, 0.065, "bois")
        c.boite((0, 0.52, 4.25), (3.04, 0.075, 0.075), "bois", chanfrein=0.01)
    if lod == 0:
        for lx in (-0.75, -0.35):
            c.poutre((lx, -1.04, 0.02), (lx, -0.52, 3.88), 0.06, 0.06, "bois_clair")
        for k in range(10):
            t = (k + 0.8) / 10.6
            c.boite((-0.55, -1.04 + 0.52 * t, 0.02 + 3.86 * t), (0.44, 0.04, 0.04), "bois")


def construire_prop_tonneaux_caisses(c: Constructeur, lod: int) -> None:
    c.tonneau_bombe((-0.52, -0.22, 0.0), 0.25, 0.31, 0.92, "bois", "metal")
    c.tonneau_bombe((-0.40, 0.44, 0.0), 0.24, 0.30, 0.88, "bois_clair", "metal")
    c.boite((0.36, 0.16, 0.34), (0.76, 0.68, 0.68), "bois_clair", chanfrein=0.018)
    c.boite((0.40, 0.12, 0.92), (0.54, 0.52, 0.48), "bois", rot=(0.0, 0.0, 0.24), chanfrein=0.016)
    if lod == 0:
        # Bandes d'encadrement cloutées sur la grande caisse
        for sz in (0.06, 0.62):
            c.boite((0.36, 0.16, sz), (0.79, 0.71, 0.06), "bois", chanfrein=0.008)
        c.sac_noue((0.28, -0.46, 0.0), 0.28, 0.22, 0.44, 0.35, "jute", "corde")


# ---------------------------------------------------------------------------
# PACK 3 — 4 Bâtiments d'Occident 1400 HAUTE GÉOMÉTRIE (prototype Manor Lords)
# ---------------------------------------------------------------------------

def construire_bat_maison_colombages(c: Constructeur, lod: int) -> None:
    # 1. Soubassement saillant + rez-de-chaussée en pierre calcaire + chaînages d'angle en harpe
    c.boite((0, 0, 0.48), (6.46, 5.46, 0.96), "pierre_claire", chanfrein=0.03)
    c.boite((0, 0, 1.82), (6.24, 5.24, 1.80), "pierre_taille", chanfrein=0.02)
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            c.chainage_angle(sx * 3.12, sy * 2.62, 0.08, 2.68, sx, sy, "pierre_claire")

    # 2. Porte d'entrée cintrée à 11 voussoirs de pierre, marches et pentures fer (façade -Y, alignée sur le soubassement)
    c.porte_cintree((-0.85, -2.73, 0.0), -1.0, 1.20, 2.24, "pierre_claire", "bois", "metal")
    # Petites fenêtres du rez-de-chaussée (façade -Y et mur droit +X)
    c.fenetre_medievale((-2.35, -2.64, 1.56), "x", -1.0, 0.62, 0.68, "bois", "bois_clair", "verre", "pierre_claire", volets=False)
    c.fenetre_medievale((0.85, -2.64, 1.56), "x", -1.0, 0.62, 0.68, "bois", "bois_clair", "verre", "pierre_claire", volets=False)
    for fy in (-1.50, 0.0, 1.50):
        c.fenetre_medievale((3.14, fy, 1.54), "y", 1.0, 0.72, 0.64, "bois", "bois_clair", "verre", "pierre_claire", volets=(lod == 0))

    # 3. Corbeaux galbés en bois soutenant l'encorbellement (4 façades)
    if lod <= 1:
        for sx in (-2.75, -1.38, 0.0, 1.38, 2.75):
            for sy in (-1.0, 1.0):
                c.corbeau_galbe(sx, sy * 2.62, 2.74, (0.0, sy), 0.18, 0.34, 0.44, "bois")
        for sy in (-1.90, -0.64, 0.64, 1.90):
            for sx in (-1.0, 1.0):
                c.corbeau_galbe(sx * 3.12, sy, 2.74, (sx, 0.0), 0.18, 0.34, 0.44, "bois")

    # 4. Étage à encorbellement : murs en torchis crème + VRAIE ossature colombage 3D sur les 4 faces
    c.boite((0, 0, 4.04), (6.76, 5.76, 2.64), "torchis")
    c.panneau_colombage(-3.38, 3.38, -2.88, 2.72, 5.36, "x", -1.0, 4, "bois", croix_indices=(0, 1, 2, 3))
    c.panneau_colombage(-3.38, 3.38, 2.88, 2.72, 5.36, "x", 1.0, 4, "bois", croix_indices=(0, 3))
    c.panneau_colombage(-2.88, 2.88, 3.38, 2.72, 5.36, "y", 1.0, 3, "bois", croix_indices=(0, 1, 2))
    c.panneau_colombage(-2.88, 2.88, -3.38, 2.72, 5.36, "y", -1.0, 3, "bois", croix_indices=(0, 2))

    # 5. Fenêtres d'étage creusées avec meneaux et volets ouverts
    for fx in (-1.70, 1.70):
        c.fenetre_medievale((fx, -2.90, 4.24), "x", -1.0, 1.05, 1.24, "bois", "bois_clair", "verre", "bois", volets=True)
        c.fenetre_medievale((fx, 2.90, 4.24), "x", 1.0, 1.05, 1.24, "bois", "bois_clair", "verre", "bois", volets=(lod == 0))
    for fy in (-1.15, 1.15):
        c.fenetre_medievale((3.40, fy, 4.24), "y", 1.0, 1.02, 1.22, "bois", "bois_clair", "verre", "bois", volets=True)

    # 6. Toit pentu en tuiles à strates 3D, pannes, colombage de pignon et cheminée en briques avec solin
    c.toit_detaille((0, 0, 5.36), 6.76, 5.76, 3.35, "tuiles", "torchis", "bois",
                    debord_x=0.40, debord_y=0.46, epaisseur=0.18, strates=7)
    # Colombage 3D sur les triangles de pignon (+X et -X)
    if lod <= 1:
        for sx in (-1.0, 1.0):
            gx = sx * 3.41
            c.poutre((gx, -2.10, 6.28), (gx, 2.10, 6.28), 0.13, 0.08, "bois")
            c.poutre((gx, -1.05, 7.36), (gx, 1.05, 7.36), 0.12, 0.08, "bois")
            c.poutre((gx, -0.58, 5.36), (gx, -0.58, 7.80), 0.13, 0.08, "bois")
            c.poutre((gx, 0.58, 5.36), (gx, 0.58, 7.80), 0.13, 0.08, "bois")
            if lod == 0:
                c.poutre((gx, -1.65, 5.42), (gx, -0.62, 6.24), 0.11, 0.07, "bois")
                c.poutre((gx, -1.65, 6.24), (gx, -0.62, 5.42), 0.11, 0.07, "bois")
                c.poutre((gx, 0.62, 5.42), (gx, 1.65, 6.24), 0.11, 0.07, "bois")
                c.poutre((gx, 0.62, 6.24), (gx, 1.65, 5.42), 0.11, 0.07, "bois")
                # Volet de grenier en haut du pignon
                c.boite((gx + sx * 0.03, 0.0, 6.84), (0.08, 0.78, 0.96), "bois_clair", chanfrein=0.01)

    # Cheminée en brique avec couronnement mouluré et solin en plomb
    c.boite((-0.95, 0.90, 7.90), (0.94, 0.94, 2.55), "brique", chanfrein=0.02)
    c.boite((-0.95, 0.90, 9.22), (1.10, 1.10, 0.18), "brique", chanfrein=0.02)
    if lod <= 1:
        c.boite((-0.95, 0.90, 6.82), (1.16, 1.32, 0.10), "plomb", rot=(-0.55, 0.0, 0.0))

    # 7. Détails de vie au pied des façades (bancs en chêne, tonneau bombé, descente de gouttière)
    if lod == 0:
        for by in (-1.10, 1.05):
            c.boite((3.42, by, 0.44), (0.38, 1.38, 0.07), "bois_clair", chanfrein=0.01)
            for dy in (-0.52, 0.52):
                c.boite((3.42, by + dy, 0.22), (0.32, 0.08, 0.42), "bois")
        c.tonneau_bombe((3.52, 2.38, 0.0), 0.28, 0.34, 0.94, "bois", "metal")
        c.cylindre((3.48, 2.38, 3.05), 0.045, 0.045, 4.30, 8, "plomb", smooth=True)


def construire_bat_grenier_medieval(c: Constructeur, lod: int) -> None:
    # 1. 8 dés de fondation en pierre calcaire chanfreinés + longrines porteuses
    for sx in (-3.8, -1.25, 1.25, 3.8):
        for sy in (-2.55, 2.55):
            c.boite((sx, sy, 0.26), (0.64, 0.64, 0.52), "pierre_claire", chanfrein=0.03)
    c.boite((0, 0, 0.60), (8.46, 5.86, 0.22), "bois", chanfrein=0.02)

    # 2. Volume principal + vraie charpente 3D (poteaux, sablières, décharges) + bardage vertical en relief
    c.boite((0, 0, 2.26), (8.20, 5.60, 3.12), "bois_clair")
    if lod <= 1:
        for sx in (-4.12, -2.06, 0.0, 2.06, 4.12):
            for sy in (-2.82, 2.82):
                c.boite((sx, sy, 2.26), (0.24, 0.20, 3.24), "bois", chanfrein=0.018)
        c.boite((0, 0, 3.82), (8.48, 5.88, 0.22), "bois", chanfrein=0.02)
        if lod == 0:
            # Contreventements obliques d'angle + couvre-joints verticaux
            for sy in (-2.84, 2.84):
                c.poutre((-4.05, sy, 0.75), (-2.12, sy, 3.75), 0.14, 0.12, "bois")
                c.poutre((4.05, sy, 0.75), (2.12, sy, 3.75), 0.14, 0.12, "bois")
            for k in range(-14, 15):
                ux = k * 0.28
                if abs(ux) > 1.25:
                    c.boite((ux, -2.83, 2.26), (0.06, 0.05, 3.04), "bois")
                c.boite((ux, 2.83, 2.26), (0.06, 0.05, 3.04), "bois")

    # 3. Grande double porte charretière ferrée + rampe en madriers
    c.boite((0.0, -2.86, 1.94), (2.36, 0.18, 2.48), "bois", chanfrein=0.015)
    for sx in (-1.22, 1.22):
        c.boite((sx, -2.90, 1.94), (0.20, 0.24, 2.58), "bois", chanfrein=0.018)
    c.boite((0.0, -2.90, 3.24), (2.68, 0.26, 0.22), "bois", chanfrein=0.02)
    if lod == 0:
        for hz in (1.12, 2.02, 2.82):
            for sx in (-0.60, 0.60):
                c.boite((sx, -2.98, hz), (1.02, 0.04, 0.085), "metal")
        # Rampe de chargement en madriers
        for r in range(6):
            c.boite((0.0, -3.02 - r * 0.22, 0.56 - r * 0.095), (2.54, 0.20, 0.10), "bois_clair", chanfrein=0.01)
    else:
        c.boite((0.0, -3.45, 0.28), (2.50, 1.15, 0.52), "bois_clair", rot=(0.28, 0, 0))

    # 4. Grand toit en chaume épais à strates organiques + pannes + potence de levage en pignon
    c.toit_detaille((0, 0, 3.88), 8.24, 5.64, 3.55, "chaume", "bois_clair", "bois",
                    debord_x=0.52, debord_y=0.58, epaisseur=0.32, strates=6)
    if lod <= 1:
        # Lucarne à foin + potence et poulie en fer sur pignon gauche (-X)
        c.boite((-4.18, 0.0, 5.05), (0.16, 1.24, 1.42), "bois", chanfrein=0.015)
        c.poutre((-4.12, 0.0, 6.22), (-5.28, 0.0, 6.22), 0.18, 0.18, "bois")
        c.poutre((-4.12, 0.0, 5.45), (-4.95, 0.0, 6.18), 0.13, 0.13, "bois")
        if lod == 0:
            c.cylindre((-5.12, 0.0, 6.02), 0.15, 0.15, 0.07, 12, "metal", rot=(math.pi * 0.5, 0, 0), smooth=True)
            c.cylindre((-5.12, 0.0, 4.30), 0.02, 0.02, 3.30, 6, "corde", smooth=True)
            # Caillebotis et 4 vrais sacs noués devant le grenier
            for sx in (-2.25, 2.25):
                c.boite((sx, -3.35, 0.06), (1.10, 0.85, 0.10), "bois", chanfrein=0.01)
                c.sac_noue((sx - 0.22, -3.35, 0.11), 0.28, 0.22, 0.44, 0.25, "jute", "corde")
                c.sac_noue((sx + 0.24, -3.32, 0.11), 0.27, 0.21, 0.42, -0.35, "jute", "corde")


def construire_bat_forge_medievale(c: Constructeur, lod: int) -> None:
    # 1. Atelier principal en pierre sombre à chaînages d'angle calcaire + porte + fenêtre
    c.boite((-1.00, 0.0, 1.50), (5.60, 4.90, 3.00), "pierre", chanfrein=0.025)
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            c.chainage_angle(-1.00 + sx * 2.80, sy * 2.45, 0.05, 2.95, sx, sy, "pierre_claire")
    c.porte_cintree((-1.40, -2.47, 0.0), -1.0, 1.18, 2.15, "pierre_claire", "bois", "metal")
    c.fenetre_medievale((-2.85, -2.47, 1.62), "x", -1.0, 0.78, 0.82, "bois", "bois_clair", "verre", "pierre_claire", volets=True)

    # Toit en tuiles + colombage 3D sur les pignons
    c.toit_detaille((-1.00, 0.0, 3.00), 5.64, 4.94, 2.65, "tuiles", "torchis", "bois",
                    debord_x=0.36, debord_y=0.40, epaisseur=0.17, strates=6)
    if lod <= 1:
        c.poutre((1.84, -1.75, 3.85), (1.84, 1.75, 3.85), 0.13, 0.09, "bois")
        c.poutre((1.84, -0.65, 3.02), (1.84, -0.65, 5.10), 0.13, 0.09, "bois")
        c.poutre((1.84, 0.65, 3.02), (1.84, 0.65, 5.10), 0.13, 0.09, "bois")

    # 2. Grosse cheminée de forge en pierre biseautée à hotte saillante
    c.boite((-3.10, 0.45, 1.55), (1.68, 1.78, 3.10), "pierre_claire", chanfrein=0.03)
    c.boite((-3.10, 0.45, 4.85), (1.28, 1.34, 3.70), "pierre", chanfrein=0.025)
    c.boite((-3.10, 0.45, 6.76), (1.50, 1.56, 0.22), "pierre_taille", chanfrein=0.025)

    # 3. Grande charpente d'auvent ouvert (+X) : 3 poteaux, sablière, aisseliers courbes, chevrons et toit tuiles
    for py in (-2.20, 0.0, 2.20):
        c.boite((3.55, py, 0.16), (0.38, 0.38, 0.32), "pierre_claire", chanfrein=0.02)
        c.boite((3.55, py, 1.46), (0.22, 0.22, 2.38), "bois", chanfrein=0.018)
        if lod == 0:
            c.poutre((3.55, py, 2.15), (2.70, py, 2.75), 0.14, 0.14, "bois")
            if py != 0.0:
                c.poutre((3.55, py, 2.05), (3.55, py * 0.60, 2.60), 0.12, 0.12, "bois")
    c.boite((3.55, 0.0, 2.62), (0.22, 4.78, 0.22), "bois", chanfrein=0.018)
    c.boite((2.80, 0.0, 3.08), (3.65, 4.96, 0.16), "tuiles", rot=(0.0, 0.26, 0.0))
    if lod == 0:
        for ky in range(-4, 5):
            c.boite((2.80, ky * 0.56, 2.94), (3.55, 0.10, 0.13), "bois", rot=(0.0, 0.26, 0.0))

    # 4. Équipement complet du forgeron sous l'auvent (foyer creusé ardent + soufflet + enclume sculptée + auge + tonneau)
    # Foyer maçonné creusé avec rebord pierre + lit de charbon et braises incandescentes
    c.boite((2.35, -1.05, 0.56), (1.36, 1.24, 1.12), "pierre_claire", chanfrein=0.025)
    c.boite((2.35, -1.05, 1.14), (0.94, 0.84, 0.14), "charbon")
    c.boite((2.38, -1.05, 1.19), (0.76, 0.64, 0.12), "braise")
    if lod <= 1:
        # Soufflet de forge à double panneau bois/cuir
        c.boite((1.95, 0.02, 1.18), (0.72, 0.52, 0.08), "bois_clair", rot=(0.15, 0.0, 0.15), chanfrein=0.01)
        c.boite((1.95, 0.02, 1.32), (0.64, 0.44, 0.22), "cuir")
        c.boite((1.95, 0.02, 1.46), (0.72, 0.52, 0.08), "bois_clair", rot=(-0.15, 0.0, 0.15), chanfrein=0.01)
    # Enclume sculptée (pied + taille + table + bigorne pointue) sur billot de chêne cerclé
    c.cylindre((2.75, 0.72, 0.36), 0.34, 0.31, 0.72, 14 if lod == 0 else 8, "bois", smooth=True)
    if lod <= 1:
        c.cylindre((2.75, 0.72, 0.54), 0.33, 0.33, 0.06, 14 if lod == 0 else 8, "metal", smooth=True)
    c.boite((2.75, 0.72, 0.78), (0.48, 0.30, 0.12), "metal", chanfrein=0.012)  # pied
    c.boite((2.75, 0.72, 0.90), (0.34, 0.22, 0.16), "metal", chanfrein=0.01)   # taille
    c.boite((2.75, 0.72, 1.03), (0.68, 0.28, 0.14), "metal", chanfrein=0.014)  # table
    c.cylindre((3.22, 0.72, 1.03), 0.12, 0.018, 0.34, 8, "metal", rot=(0.0, math.pi * 0.5, 0.0), smooth=True)  # bigorne
    # Auge de trempe en bois + eau sombre + tonneau bombé + tas de charbon
    c.boite((2.42, -2.02, 0.34), (0.98, 0.62, 0.62), "bois", chanfrein=0.015)
    c.boite((2.42, -2.02, 0.62), (0.84, 0.48, 0.06), "eau")
    if lod == 0:
        c.tonneau_bombe((3.32, 1.85, 0.0), 0.25, 0.30, 0.86, "bois", "metal")
        c.boite((2.05, 1.88, 0.24), (1.05, 0.78, 0.44), "charbon", chanfrein=0.14)


def construire_bat_porte_fortifiee(c: Constructeur, lod: int) -> None:
    segs = (24, 14, 8)[lod]
    # 1. Deux grosses tours rondes à base talutée (fruit en pierre), bandeau mouluré, mâchicoulis et poivrières
    for sx in (-3.45, 3.45):
        c.revolution(
            (sx, 0.0, 0.0),
            [(2.46, 0.0), (2.18, 1.55), (2.14, 1.65), (2.06, 7.15), (2.28, 7.38), (2.28, 8.05)],
            segs, "pierre_claire", smooth=True,
        )
        # Bandeaux moulurés horizontaux
        for bz in (1.60, 4.65, 7.22):
            br = 2.22 if bz < 2.0 else (2.14 if bz < 6.0 else 2.34)
            c.cylindre((sx, 0.0, bz), br, br, 0.18, segs, "pierre_taille", smooth=True)
        # 12 corbeaux galbés de mâchicoulis + créneaux (LOD0/1)
        if lod <= 1:
            nb_c = 12 if lod == 0 else 8
            for i in range(nb_c):
                a = 2.0 * math.pi * i / nb_c
                cx = sx + math.cos(a) * 2.02
                cy = math.sin(a) * 2.02
                c.corbeau_galbe(cx, cy, 7.30, (math.cos(a), math.sin(a)), 0.24, 0.32, 0.56, "pierre_taille")
            c.anneau_creneaux(8.04, sx, 0.0, 2.12, nb_c, 0.52, 0.32, 0.62, "pierre_taille")
        # Archères cruciformes sombres en façade (-Y)
        if lod == 0:
            for az in (3.20, 5.75):
                c.boite((sx, -2.08, az), (0.16, 0.10, 0.96), "charbon")
                c.boite((sx, -2.08, az + 0.12), (0.48, 0.10, 0.14), "charbon")
        # Toit conique en tuiles posé au-dessus des créneaux + épi de faîtage en fer
        c.revolution((sx, 0.0, 8.58), [(2.42, 0.0), (1.70, 1.15), (0.92, 2.40), (0.04, 3.65)], segs, "tuiles", smooth=True)
        if lod <= 1:
            c.cylindre((sx, 0.0, 12.63), 0.04, 0.01, 0.88, 8, "metal", smooth=True)

    # 2. Passage pavé + grande arche ogivale en 13 voussoirs de pierre + herse + vantaux entrouverts
    c.boite((0.0, 0.0, 0.08), (4.20, 4.90, 0.16), "paves")
    # Piédroits et corps central au-dessus de l'arche (passage libre 3.3 m × 3.9 m)
    c.boite((0.0, 0.0, 5.75), (4.30, 3.25, 3.55), "pierre_claire", chanfrein=0.03)
    # Grand arc de 13 voussoirs en façade avant et arrière
    r_arc = 1.72
    z_imp = 2.45
    nb_v = 13 if lod == 0 else 7
    for fy in (-1.66, 1.66):
        for i in range(nb_v):
            a = math.pi * (i + 0.5) / nb_v
            vx = math.cos(a) * (r_arc + 0.22)
            vz = z_imp + math.sin(a) * (r_arc + 0.22)
            c.boite((vx, fy, vz), (0.46, 0.34, (math.pi * (r_arc + 0.22) / nb_v) * 0.92),
                    "pierre_taille", rot=(0.0, a - math.pi * 0.5, 0.0), chanfrein=0.022)
    # Herse ferrée relevée à pointes métalliques
    if lod <= 1:
        for hz in (3.15, 3.72):
            c.boite((0.0, -1.25, hz), (3.25, 0.14, 0.14), "bois", chanfrein=0.01)
        for gx in (-1.35, -0.90, -0.45, 0.0, 0.45, 0.90, 1.35):
            c.boite((gx, -1.25, 3.45), (0.11, 0.13, 1.35), "bois")
            if lod == 0:
                c.cylindre((gx, -1.25, 2.66), 0.06, 0.005, 0.26, 4, "metal", rot=(math.pi, 0.0, 0.0))
    # Deux vantaux massifs entrouverts à l'intérieur du passage (LOD0)
    if lod == 0:
        for sx in (-1.0, 1.0):
            c.boite((sx * 1.38, 0.55, 1.75), (0.18, 1.45, 3.30), "bois", rot=(0.0, 0.0, sx * 0.25), chanfrein=0.015)

    # 3. Galerie de garde supérieure en hourds de chêne sur consoles galbées + toit en tuiles
    if lod <= 1:
        for hx in (-1.6, -0.8, 0.0, 0.8, 1.6):
            for sy in (-1.0, 1.0):
                c.corbeau_galbe(hx, sy * 1.62, 7.36, (0.0, sy), 0.20, 0.42, 0.56, "bois")
    c.boite((0.0, 0.0, 7.82), (4.60, 3.85, 0.96), "bois_clair", chanfrein=0.02)
    if lod == 0:
        for hx in (-1.3, 0.0, 1.3):
            c.boite((hx, -1.94, 7.86), (0.58, 0.08, 0.44), "charbon")
    c.toit_detaille((0.0, 0.0, 8.30), 4.64, 3.90, 1.85, "tuiles", "bois", "bois",
                    debord_x=0.28, debord_y=0.32, epaisseur=0.16, strates=5)


# ---------------------------------------------------------------------------
# Catalogue, export FBX, rendu Cycles studio 40 samples et vérification réimport
# ---------------------------------------------------------------------------

CATALOGUE = [
    ("pion_armee", "PionsCarte", 0.9, construire_pion_armee),
    ("pion_siege", "PionsCarte", 0.9, construire_pion_siege),
    ("pion_capitale", "PionsCarte", 1.1, construire_pion_capitale),
    ("pion_bourg", "PionsCarte", 1.0, construire_pion_bourg),
    ("prop_charrette", "PropsVille", 1.0, construire_prop_charrette),
    ("prop_etal_marche", "PropsVille", 1.2, construire_prop_etal_marche),
    ("prop_puits_pierre", "PropsVille", 1.2, construire_prop_puits_pierre),
    ("prop_sacs_grain", "PropsVille", 0.8, construire_prop_sacs_grain),
    ("prop_echafaudage", "PropsVille", 1.5, construire_prop_echafaudage),
    ("prop_tonneaux_caisses", "PropsVille", 0.9, construire_prop_tonneaux_caisses),
    ("bat_maison_colombages", "BatimentsOccident", 2.2, construire_bat_maison_colombages),
    ("bat_grenier_medieval", "BatimentsOccident", 2.4, construire_bat_grenier_medieval),
    ("bat_forge_medievale", "BatimentsOccident", 2.2, construire_bat_forge_medievale),
    ("bat_porte_fortifiee", "BatimentsOccident", 2.8, construire_bat_porte_fortifiee),
]


def rendre_studio(obj_lod0: bpy.types.Object, sortie_png: Path) -> None:
    """Rend une vue 3/4 neutre Cycles CPU (40 samples) de `obj_lod0`."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 40
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.025
    scene.cycles.use_denoising = False
    scene.cycles.max_bounces = 4
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.image_settings.file_format = "PNG"
    transforms = [i.identifier for i in scene.view_settings.bl_rna.properties["view_transform"].enum_items]
    scene.view_settings.view_transform = "AgX" if "AgX" in transforms else "Filmic"

    world = bpy.data.worlds.new("Studio")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.16, 0.155, 0.148, 1.0)
    bg.inputs["Strength"].default_value = 0.95

    coins = [obj_lod0.matrix_world @ Vector(c) for c in obj_lod0.bound_box]
    bmin = Vector((min(v.x for v in coins), min(v.y for v in coins), min(v.z for v in coins)))
    bmax = Vector((max(v.x for v in coins), max(v.y for v in coins), max(v.z for v in coins)))
    centre = (bmin + bmax) * 0.5
    rayon = max((bmax - bmin).length * 0.5, 0.5)

    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=rayon * 1.48, depth=0.04, location=(centre.x, centre.y, -0.02))
    sol = bpy.context.active_object
    sol.data.materials.append(creer_materiau_simple("M_SolStudio", (0.19, 0.18, 0.17), roughness=0.92))

    cam_data = bpy.data.cameras.new("CamStudio")
    cam_data.lens = 52.0
    cam = bpy.data.objects.new("CamStudio", cam_data)
    scene.collection.objects.link(cam)
    dist = rayon * 2.68
    cam.location = centre + Vector((dist * 0.72, -dist * 0.84, dist * 0.50))
    direction = (centre - cam.location).normalized()
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam

    # Éclairage 3 points (soleil chaud, fill froid, rim doux)
    for nom, energie, col, angle, rot in (
        ("KeySun", 3.6, (1.0, 0.94, 0.84), 6.0, (46, 12, -36)),
        ("FillSun", 1.25, (0.76, 0.85, 1.0), 22.0, (62, 0, 140)),
        ("RimSun", 0.95, (1.0, 0.96, 0.90), 12.0, (32, 0, -165)),
    ):
        light = bpy.data.lights.new(nom, type="SUN")
        light.energy = energie
        light.color = col
        light.angle = math.radians(angle)
        lo = bpy.data.objects.new(nom, light)
        lo.rotation_euler = Euler(tuple(math.radians(a) for a in rot), "XYZ")
        scene.collection.objects.link(lo)

    sortie_png.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(sortie_png.resolve())
    bpy.ops.render.render(write_still=True)


def verifier_fbx(chemin_fbx: Path, nom_id: str) -> dict:
    vider_scene()
    bpy.ops.import_scene.fbx(filepath=str(chemin_fbx.resolve()))
    objets = {o.name: o for o in bpy.data.objects if o.type == "MESH"}
    tris = {}
    z_min = None
    dims = None
    for k in (0, 1, 2):
        cle = f"{nom_id}_LOD{k}"
        if cle not in objets:
            raise RuntimeError(f"{chemin_fbx.name} : objet {cle} absent au réimport")
        o = objets[cle]
        o.data.calc_loop_triangles()
        tris[f"LOD{k}"] = len(o.data.loop_triangles)
        if k == 0:
            coins = [o.matrix_world @ Vector(c) for c in o.bound_box]
            z_min = round(min(v.z for v in coins), 4)
            dims = [
                round(max(v.x for v in coins) - min(v.x for v in coins), 3),
                round(max(v.y for v in coins) - min(v.y for v in coins), 3),
                round(max(v.z for v in coins) - min(v.z for v in coins), 3),
            ]
    if not (tris["LOD0"] > tris["LOD1"] > tris["LOD2"] > 0):
        raise RuntimeError(f"{chemin_fbx.name} : LOD non strictement décroissants : {tris}")
    if z_min is None or abs(z_min) > 0.05:
        raise RuntimeError(f"{chemin_fbx.name} : pivot hors sol (z_min={z_min})")
    return {"id": nom_id, "fbx": chemin_fbx.name, "triangles": tris, "dimensions_m": dims, "z_min": z_min}


def fabriquer_tout(dossier_sortie: Path, dossier_pbr: Path) -> list[dict]:
    rapport: list[dict] = []
    for nom_id, categorie, echelle_uv, fn in CATALOGUE:
        vider_scene()
        palette = preparer_palette(dossier_pbr)
        lods: list[bpy.types.Object] = []
        for k in (0, 1, 2):
            c = Constructeur(palette, echelle_uv=echelle_uv, lod=k)
            fn(c, k)
            obj = c.finaliser(f"{nom_id}_LOD{k}")
            lods.append(obj)

        chemin_fbx = dossier_sortie / categorie / f"{nom_id}.fbx"
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
        rendre_studio(lods[0], chemin_rendu)

        mesure = verifier_fbx(chemin_fbx, nom_id)
        mesure["categorie"] = categorie
        mesure["rendu"] = chemin_rendu.name
        rapport.append(mesure)
        print(f"OK {nom_id:24} tris={mesure['triangles']} dims={mesure['dimensions_m']}m")

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
    args = parser.parse_args(argv)
    fabriquer_tout(args.sortie, args.textures)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
