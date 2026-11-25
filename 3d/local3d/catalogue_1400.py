"""Générateur Blender 4.x du catalogue 3D 1400 pour Forge.

Produit 14 modèles 3D en FBX (échelle métrique, pivot au sol z=0, UV projetés,
trois niveaux de détail décroissants `<id>_LOD0`, `<id>_LOD1`, `<id>_LOD2`),
habillés par les matériaux PBR du dépôt, puis rend une vue studio 3/4 de chaque
modèle et vérifie chaque FBX par réimport dans une scène vierge.

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
# Utilitaires scène, matériaux PBR et géométrie BMesh
# ---------------------------------------------------------------------------

def vider_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def charger_image(chemin: Path, non_color: bool = False):
    im = bpy.data.images.load(str(chemin.resolve()), check_existing=True)
    if non_color:
        im.colorspace_settings.name = "Non-Color"
    return im


def creer_materiau_pbr(nom: str, dossier: Path, prefixe: str, *,
                       metallic: float = 0.0, normal_strength: float = 0.85,
                       teinte: tuple[float, float, float] | None = None):
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
            mix_t.blend_type = "MULTIPLY"
            mix_t.inputs["Factor"].default_value = 0.45
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
    """Charge les 9 jeux PBR du dépôt et les matériaux complémentaires DA."""
    return {
        "pierre": creer_materiau_pbr("M_PierreSombre", dossier_pbr / "PierreSombre", "pierre_sombre"),
        "pierre_claire": creer_materiau_pbr(
            "M_PierreClaire", dossier_pbr / "PavesMedievaux", "paves_medievaux",
            teinte=(0.95, 0.90, 0.80),
        ),
        "bois": creer_materiau_pbr("M_BoisBrule", dossier_pbr / "BoisBrule", "bois_brule"),
        "bois_clair": creer_materiau_pbr(
            "M_BoisChene", dossier_pbr / "BoisBrule", "bois_brule",
            teinte=(1.35, 1.15, 0.90),
        ),
        "metal": creer_materiau_pbr("M_MetalPatine", dossier_pbr / "MetalPatine", "metal_patine", metallic=0.65),
        "pise": creer_materiau_pbr("M_PiseOcre", dossier_pbr / "PiseOcre", "pise_ocre"),
        "colombage": creer_materiau_pbr("M_Colombage", dossier_pbr / "ColombageTorchis", "colombage_torchis"),
        "chaume": creer_materiau_pbr("M_Chaume", dossier_pbr / "ChaumeMedieval", "chaume_medieval"),
        "tuiles": creer_materiau_pbr("M_Tuiles", dossier_pbr / "TuilesMedievales", "tuiles_medievales"),
        "paves": creer_materiau_pbr("M_Paves", dossier_pbr / "PavesMedievaux", "paves_medievaux"),
        "terre": creer_materiau_pbr("M_TerreBattue", dossier_pbr / "TerreBattue", "terre_battue"),
        "toile": creer_materiau_simple("M_ToileEcrue", (0.76, 0.69, 0.56), roughness=0.88),
        "banniere": creer_materiau_simple("M_BanniereGarance", (0.38, 0.07, 0.06), roughness=0.82),
        "or": creer_materiau_simple("M_OrVieilli", (0.64, 0.50, 0.25), roughness=0.42, metallic=0.82),
        "jute": creer_materiau_simple("M_ToileJute", (0.58, 0.47, 0.31), roughness=0.92),
        "braise": creer_materiau_simple(
            "M_BraiseForge", (0.85, 0.25, 0.04), roughness=0.5,
            emission=(1.0, 0.32, 0.05), emission_strength=4.0,
        ),
        "eau": creer_materiau_simple("M_EauSombre", (0.12, 0.20, 0.22), roughness=0.18),
        "charbon": creer_materiau_simple("M_Charbon", (0.04, 0.04, 0.045), roughness=0.88),
    }


class Constructeur:
    """Assemble des primitives BMesh par matériau avec projection UV cubique."""

    def __init__(self, palette: dict[str, bpy.types.Material], echelle_uv: float = 1.6):
        self.palette = palette
        self.echelle_uv = echelle_uv
        self.bm = bmesh.new()
        self.noms_mat: list[str] = []
        self._index_mat: dict[str, int] = {}

    def _slot(self, mat_cle: str) -> int:
        if mat_cle not in self._index_mat:
            self._index_mat[mat_cle] = len(self.noms_mat)
            self.noms_mat.append(mat_cle)
        return self._index_mat[mat_cle]

    def _marquer_faces(self, geom: list, mat_cle: str) -> None:
        slot = self._slot(mat_cle)
        for g in geom:
            if isinstance(g, bmesh.types.BMFace):
                g.material_index = slot

    def boite(self, centre: tuple[float, float, float], taille: tuple[float, float, float],
              mat: str, rot: tuple[float, float, float] = (0.0, 0.0, 0.0)) -> None:
        sx, sy, sz = taille
        m = (
            Matrix.Translation(Vector(centre))
            @ Euler(rot, "XYZ").to_matrix().to_4x4()
            @ Matrix.Diagonal((sx, sy, sz, 1.0))
        )
        res = bmesh.ops.create_cube(self.bm, size=1.0, matrix=m)
        verts = set(res["verts"])
        faces = [f for f in self.bm.faces if all(v in verts for v in f.verts)]
        self._marquer_faces(faces, mat)

    def cylindre(self, centre: tuple[float, float, float], rayon_bas: float, rayon_haut: float,
                 hauteur: float, segments: int, mat: str,
                 rot: tuple[float, float, float] = (0.0, 0.0, 0.0)) -> None:
        m = Matrix.Translation(Vector(centre)) @ Euler(rot, "XYZ").to_matrix().to_4x4()
        res = bmesh.ops.create_cone(
            self.bm, cap_ends=True, cap_tris=False, segments=max(4, segments),
            radius1=rayon_bas, radius2=rayon_haut, depth=hauteur, matrix=m,
        )
        verts = set(res["verts"])
        faces = [f for f in self.bm.faces if all(v in verts for v in f.verts)]
        self._marquer_faces(faces, mat)

    def sphere(self, centre: tuple[float, float, float], rayons: tuple[float, float, float],
               segments: int, anneaux: int, mat: str,
               rot: tuple[float, float, float] = (0.0, 0.0, 0.0)) -> None:
        rx, ry, rz = rayons
        m = (
            Matrix.Translation(Vector(centre))
            @ Euler(rot, "XYZ").to_matrix().to_4x4()
            @ Matrix.Diagonal((rx, ry, rz, 1.0))
        )
        res = bmesh.ops.create_uvsphere(
            self.bm, u_segments=max(6, segments), v_segments=max(4, anneaux), radius=1.0, matrix=m,
        )
        verts = set(res["verts"])
        faces = [f for f in self.bm.faces if all(v in verts for v in f.verts)]
        for f in faces:
            f.smooth = True
        self._marquer_faces(faces, mat)

    def prisme_toit(self, centre_base: tuple[float, float, float], longueur_x: float,
                    largeur_y: float, hauteur_z: float, mat_toit: str, mat_pignon: str,
                    debord_x: float = 0.25, debord_y: float = 0.25,
                    epaisseur_toit: float = 0.14) -> None:
        """Construit un toit à deux pans (pignons selon X, faîte parallèle à X)."""
        cx, cy, cz = centre_base
        hx = longueur_x * 0.5
        hy = largeur_y * 0.5
        # Prisme de pignon
        v0 = self.bm.verts.new((cx - hx, cy - hy, cz))
        v1 = self.bm.verts.new((cx + hx, cy - hy, cz))
        v2 = self.bm.verts.new((cx + hx, cy + hy, cz))
        v3 = self.bm.verts.new((cx - hx, cy + hy, cz))
        v4 = self.bm.verts.new((cx - hx, cy, cz + hauteur_z))
        v5 = self.bm.verts.new((cx + hx, cy, cz + hauteur_z))
        slot_p = self._slot(mat_pignon)
        for loop in ((v0, v3, v4), (v1, v5, v2), (v0, v1, v2, v3)):
            f = self.bm.faces.new(loop)
            f.material_index = slot_p
        # Deux versants de toit épais avec débord
        pente = math.atan2(hauteur_z, hy)
        long_pan = math.hypot(hy + debord_y, hauteur_z) + 0.12
        for signe in (-1.0, 1.0):
            mid_y = cy + signe * (hy * 0.5 + debord_y * 0.35)
            mid_z = cz + hauteur_z * 0.5 - debord_y * 0.35 * math.tan(pente) + epaisseur_toit * 0.45
            self.boite(
                (cx, mid_y, mid_z),
                (longueur_x + 2.0 * debord_x, long_pan, epaisseur_toit),
                mat_toit,
                rot=(-signe * pente, 0.0, 0.0),
            )
        # Faîtière
        self.boite((cx, cy, cz + hauteur_z + epaisseur_toit * 0.55),
                   (longueur_x + 2.0 * debord_x + 0.05, 0.22, 0.16), mat_toit)

    def anneau_creneaux(self, centre_z: float, cx: float, cy: float, rayon: float,
                        nb: int, largeur: float, profondeur: float, hauteur: float, mat: str) -> None:
        for i in range(nb):
            a = 2.0 * math.pi * i / nb
            x = cx + math.cos(a) * rayon
            y = cy + math.sin(a) * rayon
            self.boite((x, y, centre_z + hauteur * 0.5), (profondeur, largeur, hauteur), mat, rot=(0.0, 0.0, a))

    def finaliser(self, nom: str) -> bpy.types.Object:
        """Projette les UV cubiques, recalcule les normales, pose z_min=0 et crée l'objet."""
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        bmesh.ops.triangulate(self.bm, faces=self.bm.faces)

        # Recaler exactement sur z = 0
        if self.bm.verts:
            z_min = min(v.co.z for v in self.bm.verts)
            if abs(z_min) > 1e-5:
                bmesh.ops.translate(self.bm, verts=self.bm.verts, vec=(0.0, 0.0, -z_min))

        # Projection UV cubique métrique
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
# PACK 1 — 4 Pions 3D pour la carte de 1400 (Étape 2)
# ---------------------------------------------------------------------------

def construire_pion_armee(c: Constructeur, lod: int) -> None:
    segs = (24, 14, 8)[lod]
    # Socle circulaire en pierre + anneau doré
    c.cylindre((0, 0, 0.08), 0.72, 0.66, 0.16, segs, "pierre")
    if lod <= 1:
        c.cylindre((0, 0, 0.18), 0.65, 0.60, 0.06, segs, "or")
    # Hampe principale + pointe de lance
    c.cylindre((0.0, -0.05, 1.30), 0.045, 0.035, 2.30, max(6, segs // 2), "bois")
    c.cylindre((0.0, -0.05, 2.58), 0.075, 0.005, 0.30, max(6, segs // 2), "metal")
    # Barre transversale d'étendard + bannière flottante à deux pans
    c.boite((0.0, -0.05, 2.25), (0.85, 0.06, 0.06), "or")
    c.boite((0.0, 0.03, 1.72), (0.76, 0.04, 0.96), "banniere", rot=(0.06, 0.0, 0.0))
    if lod == 0:
        # Bordure dorée + deux pointes basses alignées sur la bannière
        c.boite((-0.24, 0.05, 1.15), (0.28, 0.04, 0.24), "banniere", rot=(0.06, 0.0, 0.0))
        c.boite((0.24, 0.05, 1.15), (0.28, 0.04, 0.24), "banniere", rot=(0.06, 0.0, 0.0))
        c.boite((0.0, 0.04, 2.16), (0.76, 0.05, 0.07), "or")
    # Écu médiéval au pied de la hampe
    c.boite((0.0, -0.26, 0.66), (0.52, 0.08, 0.66), "metal", rot=(-0.18, 0.0, 0.0))
    if lod <= 1:
        c.boite((0.0, -0.31, 0.68), (0.44, 0.04, 0.56), "banniere", rot=(-0.18, 0.0, 0.0))
        c.boite((0.0, -0.33, 0.68), (0.06, 0.03, 0.52), "or", rot=(-0.18, 0.0, 0.0))
        c.boite((0.0, -0.33, 0.72), (0.40, 0.03, 0.06), "or", rot=(-0.18, 0.0, 0.0))
    # Faisceau de 4 lances latérales encadrant la bannière sans la traverser (LOD0/1)
    if lod == 0:
        for sx in (-1.0, 1.0):
            for sy in (-0.18, 0.24):
                c.cylindre((sx * 0.48, sy, 1.05), 0.025, 0.02, 1.85, 8, "bois", rot=(sy * 0.2, sx * 0.14, 0.0))
                c.cylindre((sx * 0.61, sy * 1.25, 2.04), 0.05, 0.005, 0.24, 6, "metal", rot=(sy * 0.2, sx * 0.14, 0.0))
    elif lod == 1:
        for sx in (-1.0, 1.0):
            c.cylindre((sx * 0.50, 0.05, 1.05), 0.03, 0.025, 1.80, 6, "bois", rot=(0.0, sx * 0.14, 0.0))


def construire_pion_siege(c: Constructeur, lod: int) -> None:
    segs = (20, 12, 8)[lod]
    # Socle circulaire de terre battue
    c.cylindre((0, 0, 0.07), 0.95, 0.88, 0.14, segs, "terre")
    # Pavillon de siège conique à l'arrière
    c.cylindre((-0.26, 0.18, 0.52), 0.44, 0.40, 0.76, segs // 2 + 2, "toile")
    c.cylindre((-0.26, 1.0 * 0.18, 1.15), 0.48, 0.02, 0.56, segs // 2 + 2, "banniere")
    if lod <= 1:
        c.cylindre((-0.26, 0.18, 1.56), 0.025, 0.02, 0.36, 6, "or")
        c.boite((-0.12, 0.18, 1.66), (0.28, 0.03, 0.14), "banniere")
    # Bélier couvert devant le pavillon
    c.boite((0.32, -0.18, 0.38), (0.64, 0.40, 0.32), "bois")
    c.prisme_toit((0.32, -0.18, 0.54), 0.68, 0.46, 0.26, "bois_clair", "bois", debord_x=0.06, debord_y=0.06, epaisseur_toit=0.05)
    c.cylindre((0.36, -0.18, 0.32), 0.07, 0.06, 0.95, max(6, segs // 2), "bois_clair", rot=(0.0, math.pi * 0.5, 0.0))
    if lod <= 1:
        c.cylindre((0.86, -0.18, 0.32), 0.09, 0.07, 0.14, 8, "metal", rot=(0.0, math.pi * 0.5, 0.0))
        # Roues du bélier
        for sx in (-0.18, 0.18):
            for sy in (-0.23, 0.23):
                c.cylindre((0.32 + sx, -0.18 + sy, 0.20), 0.14, 0.14, 0.06, max(6, segs // 2), "bois", rot=(math.pi * 0.5, 0.0, 0.0))
    # Palissade de pieux en arc à l'avant (LOD0/1)
    if lod == 0:
        for i in range(9):
            a = -1.1 + i * 0.275
            px, py = math.cos(a) * 0.78, math.sin(a) * 0.78 - 0.05
            c.cylindre((px, py, 0.34), 0.045, 0.015, 0.56, 6, "bois", rot=(0.0, 0.18, a))
    elif lod == 1:
        for i in range(5):
            a = -1.0 + i * 0.5
            px, py = math.cos(a) * 0.78, math.sin(a) * 0.78 - 0.05
            c.cylindre((px, py, 0.32), 0.05, 0.02, 0.52, 5, "bois")


def construire_pion_capitale(c: Constructeur, lod: int) -> None:
    segs = (16, 10, 6)[lod]
    # Socle rocheux / pavé
    c.boite((0, 0, 0.10), (2.20, 2.20, 0.20), "paves")
    # Enceinte carrée
    for sx in (-0.85, 0.85):
        c.boite((sx, 0, 0.55), (0.24, 1.70, 0.74), "pierre")
    c.boite((0, 0.85, 0.55), (1.70, 0.24, 0.74), "pierre")
    c.boite((-0.52, -0.85, 0.55), (0.68, 0.24, 0.74), "pierre")
    c.boite((0.52, -0.85, 0.55), (0.68, 0.24, 0.74), "pierre")
    c.boite((0.0, -0.85, 0.76), (0.44, 0.24, 0.32), "pierre")
    # 4 tours d'angle à toits coniques en tuiles
    for sx in (-0.90, 0.90):
        for sy in (-0.90, 0.90):
            c.cylindre((sx, sy, 0.72), 0.28, 0.25, 1.15, segs, "pierre")
            c.cylindre((sx, sy, 1.54), 0.34, 0.02, 0.56, segs, "tuiles")
    # Donjon central élevé
    c.boite((0, 0.05, 1.12), (0.94, 0.94, 1.88), "pierre_claire")
    c.prisme_toit((0, 0.05, 2.06), 0.96, 0.96, 0.55, "tuiles", "pierre_claire", debord_x=0.10, debord_y=0.10, epaisseur_toit=0.08)
    # Créneaux + bannière au sommet (LOD0/1)
    if lod == 0:
        for i in (-0.36, -0.12, 0.12, 0.36):
            for sy in (-0.42, 0.52):
                c.boite((i, sy, 2.12), (0.14, 0.10, 0.16), "pierre_claire")
        c.cylindre((0, 0.05, 2.86), 0.025, 0.02, 0.58, 8, "or")
        c.boite((0.18, 0.05, 3.00), (0.36, 0.03, 0.20), "banniere")
        # Châtelet d'entrée
        c.boite((0, -0.92, 0.42), (0.34, 0.08, 0.48), "bois")
    elif lod == 1:
        c.cylindre((0, 0.05, 2.82), 0.03, 0.02, 0.48, 6, "or")
        c.boite((0.16, 0.05, 2.94), (0.32, 0.03, 0.18), "banniere")


def construire_pion_bourg(c: Constructeur, lod: int) -> None:
    segs = (14, 10, 6)[lod]
    # Socle circulaire en pavés
    c.cylindre((0, 0, 0.08), 1.05, 1.00, 0.16, segs, "paves")
    # Rempart polygonal (4 pans + 2 tourelles)
    for a in (0.3, 1.2, 2.1, 3.0, 3.9, 5.4):
        px, py = math.cos(a) * 0.80, math.sin(a) * 0.80
        c.boite((px, py, 0.38), (0.18, 0.62, 0.50), "pierre", rot=(0.0, 0.0, a))
    for sx in (-0.35, 0.35):
        c.cylindre((sx, -0.78, 0.48), 0.18, 0.16, 0.72, max(6, segs - 2), "pierre")
        c.cylindre((sx, -0.78, 0.98), 0.22, 0.02, 0.32, max(6, segs - 2), "tuiles")
    # Beffroi central + 3 maisons groupées
    c.boite((0.0, 0.15, 0.74), (0.42, 0.42, 1.20), "pierre_claire")
    c.cylindre((0.0, 0.15, 1.62), 0.30, 0.02, 0.58, 4, "tuiles", rot=(0.0, 0.0, math.pi * 0.25))
    maisons = [(-0.36, -0.08, 0.42, 0.34, 0.36), (0.38, -0.05, 0.40, 0.36, 0.38), (0.05, 0.52, 0.48, 0.32, 0.34)]
    for mx, my, lx, ly, hz in maisons[:(3 if lod <= 1 else 2)]:
        c.boite((mx, my, 0.16 + hz * 0.5), (lx, ly, hz), "colombage")
        c.prisme_toit((mx, my, 0.16 + hz), lx, ly, 0.26, "tuiles", "colombage", debord_x=0.04, debord_y=0.04, epaisseur_toit=0.05)


# ---------------------------------------------------------------------------
# PACK 2 — 6 Props de vie urbaine médiévale (Étape 4)
# ---------------------------------------------------------------------------

def construire_prop_charrette(c: Constructeur, lod: int) -> None:
    segs = (18, 10, 6)[lod]
    # Essieu + 2 roues cerclées
    c.cylindre((0, 0, 0.48), 0.055, 0.055, 1.38, max(6, segs // 2), "bois", rot=(math.pi * 0.5, 0.0, 0.0))
    for sy in (-0.64, 0.64):
        c.cylindre((0, sy, 0.48), 0.48, 0.48, 0.07, segs, "metal", rot=(math.pi * 0.5, 0.0, 0.0))
        c.cylindre((0, sy, 0.48), 0.43, 0.43, 0.08, segs, "bois_clair", rot=(math.pi * 0.5, 0.0, 0.0))
        if lod == 0:
            for k in range(8):
                a = k * math.pi / 4.0
                c.boite((0, sy, 0.48), (0.82, 0.05, 0.045), "bois", rot=(0.0, a, 0.0))
    # Caisse à ridelles + timons
    c.boite((-0.05, 0, 0.62), (1.70, 1.06, 0.08), "bois")
    for sy in (-0.50, 0.50):
        c.boite((-0.05, sy, 0.90), (1.70, 0.06, 0.48), "bois_clair")
        c.boite((1.28, sy * 0.78, 0.58), (1.15, 0.07, 0.07), "bois", rot=(0.0, 0.08, 0.0))
    c.boite((-0.88, 0, 0.90), (0.06, 1.06, 0.48), "bois_clair")
    c.boite((0.78, 0, 0.84), (0.06, 1.06, 0.36), "bois_clair")
    # 3 sacs de grain dans la caisse (LOD0/1)
    if lod <= 1:
        sacs = [(-0.42, -0.18, 0.84), (-0.40, 0.22, 0.84), (0.18, 0.0, 0.86)]
        for sx, sy, sz in sacs:
            c.sphere((sx, sy, sz), (0.34, 0.22, 0.20), max(8, segs - 4), 6 if lod == 0 else 4, "jute", rot=(0.0, 0.1, 0.2))


def construire_prop_etal_marche(c: Constructeur, lod: int) -> None:
    # 4 poteaux + comptoir
    for sx in (-1.25, 1.25):
        c.boite((sx, -0.58, 1.22), (0.10, 0.10, 2.44), "bois")
        c.boite((sx, 0.58, 1.05), (0.10, 0.10, 2.10), "bois")
    c.boite((0, 0, 0.88), (2.65, 1.15, 0.08), "bois_clair")
    c.boite((0, -0.52, 0.44), (2.55, 0.08, 0.84), "bois")
    # Auvent incliné en toile + bande garance
    c.boite((0, 0.0, 2.30), (2.82, 1.62, 0.06), "toile", rot=(-0.24, 0.0, 0.0))
    if lod == 0:
        for i in (-1.0, -0.34, 0.34, 1.0):
            c.boite((i, 0.0, 2.33), (0.30, 1.62, 0.03), "banniere", rot=(-0.24, 0.0, 0.0))
        c.boite((0, -0.78, 2.40), (2.82, 0.04, 0.20), "banniere")
    # Marchandises sur le comptoir (caisses + sacs)
    if lod <= 1:
        c.boite((-0.78, -0.05, 1.08), (0.58, 0.44, 0.34), "bois_clair")
        c.boite((0.02, 0.05, 1.05), (0.52, 0.42, 0.28), "bois")
        c.sphere((0.76, 0.0, 1.08), (0.28, 0.22, 0.20), 10 if lod == 0 else 6, 5, "jute")


def construire_prop_puits_pierre(c: Constructeur, lod: int) -> None:
    segs = (20, 12, 8)[lod]
    # Margelle cylindrique en pierre + eau au fond
    c.cylindre((0, 0, 0.44), 0.78, 0.76, 0.88, segs, "pierre_claire")
    c.cylindre((0, 0, 0.86), 0.82, 0.82, 0.10, segs, "pierre")
    c.cylindre((0, 0, 0.78), 0.56, 0.56, 0.04, segs, "eau")
    # Deux poteaux + treuil + seau
    for sx in (-0.72, 0.72):
        c.boite((sx, 0, 1.25), (0.11, 0.11, 2.10), "bois")
        if lod == 0:
            c.boite((sx * 0.75, 0, 2.02), (0.42, 0.08, 0.08), "bois", rot=(0.0, sx * 0.85, 0.0))
    if lod <= 1:
        c.cylindre((0, 0, 1.52), 0.07, 0.07, 1.48, max(6, segs // 2), "bois_clair", rot=(0.0, math.pi * 0.5, 0.0))
        c.cylindre((0.84, 0, 1.52), 0.03, 0.03, 0.24, 6, "metal", rot=(0.0, math.pi * 0.5, 0.0))
        c.cylindre((0.0, 0, 1.18), 0.015, 0.015, 0.60, 6, "jute")
        c.cylindre((0.0, 0, 1.04), 0.14, 0.17, 0.26, max(6, segs // 2), "bois")
    # Petit toit à deux pans en tuiles
    c.prisme_toit((0, 0, 2.26), 1.62, 1.25, 0.62, "tuiles", "bois", debord_x=0.14, debord_y=0.16, epaisseur_toit=0.07)


def construire_prop_sacs_grain(c: Constructeur, lod: int) -> None:
    u_seg = (12, 8, 6)[lod]
    v_seg = (8, 5, 4)[lod]
    # Caillebotis en bois au sol
    c.boite((0, 0, 0.06), (1.50, 1.20, 0.10), "bois")
    if lod == 0:
        for sy in (-0.42, 0.0, 0.42):
            c.boite((0, sy, 0.12), (1.50, 0.18, 0.04), "bois_clair")
    # Empilement de sacs de grain
    couche1 = [(-0.38, -0.24, 0.28, 0.08), (0.36, -0.22, 0.28, -0.10),
               (-0.36, 0.24, 0.28, -0.06), (0.34, 0.26, 0.28, 0.12)]
    for sx, sy, sz, rotz in couche1:
        c.sphere((sx, sy, sz), (0.34, 0.22, 0.18), u_seg, v_seg, "jute", rot=(0.0, 0.0, rotz))
    if lod <= 1:
        c.sphere((-0.18, 0.0, 0.56), (0.33, 0.22, 0.18), u_seg, v_seg, "jute", rot=(0.0, 0.08, 0.3))
        c.sphere((0.30, -0.02, 0.55), (0.30, 0.21, 0.18), u_seg, v_seg, "jute", rot=(0.05, -0.06, -0.4))
    if lod == 0:
        c.sphere((0.05, 0.04, 0.80), (0.28, 0.20, 0.17), u_seg, v_seg, "jute", rot=(0.04, 0.0, 0.15))


def construire_prop_echafaudage(c: Constructeur, lod: int) -> None:
    segs = (10, 6, 5)[lod]
    # 4 perches verticales
    for sx in (-1.45, 1.45):
        for sy in (-0.52, 0.52):
            c.cylindre((sx, sy, 2.20), 0.06, 0.05, 4.40, segs, "bois")
    # 2 planchers (1.8 m et 3.5 m)
    for z in (1.80, 3.50):
        c.boite((0, 0, z), (3.15, 1.15, 0.07), "bois_clair")
        c.boite((0, -0.52, z - 0.08), (3.10, 0.08, 0.08), "bois")
        c.boite((0, 0.52, z - 0.08), (3.10, 0.08, 0.08), "bois")
    # Contreventements croisés et garde-corps (LOD0/1)
    if lod <= 1:
        c.boite((0, 0.52, 0.90), (3.30, 0.06, 0.06), "bois", rot=(0.0, 0.54, 0.0))
        c.boite((0, 0.52, 2.65), (3.30, 0.06, 0.06), "bois", rot=(0.0, -0.54, 0.0))
        c.boite((0, 0.52, 4.25), (3.00, 0.07, 0.07), "bois")
    # Échelle en façade (LOD0)
    if lod == 0:
        for lx in (-0.75, -0.35):
            c.boite((lx, -0.78, 1.95), (0.06, 0.06, 3.95), "bois_clair", rot=(-0.15, 0.0, 0.0))
        for k in range(10):
            z = 0.35 + k * 0.36
            y = -0.98 + k * 0.052
            c.boite((-0.55, y, z), (0.44, 0.04, 0.04), "bois")


def construire_prop_tonneaux_caisses(c: Constructeur, lod: int) -> None:
    segs = (16, 10, 6)[lod]
    # 2 tonneaux debout cerclés
    for tx, ty in ((-0.52, -0.22), (-0.42, 0.42)):
        c.cylindre((tx, ty, 0.46), 0.27, 0.27, 0.92, segs, "bois")
        if lod <= 1:
            for hz in (0.20, 0.72):
                c.cylindre((tx, ty, hz), 0.285, 0.285, 0.05, segs, "metal")
    # 2 caisses cloutées empilées
    c.boite((0.36, 0.16, 0.34), (0.76, 0.68, 0.68), "bois_clair")
    c.boite((0.40, 0.12, 0.92), (0.54, 0.52, 0.48), "bois", rot=(0.0, 0.0, 0.22))
    # 1 tonneau couché devant (LOD0/1)
    if lod <= 1:
        c.cylindre((0.28, -0.46, 0.27), 0.25, 0.25, 0.76, segs, "bois", rot=(0.0, math.pi * 0.5, 0.28))
        if lod == 0:
            c.boite((0.36, 0.16, 0.34), (0.78, 0.70, 0.06), "bois")


# ---------------------------------------------------------------------------
# PACK 3 — 4 Bâtiments d'Occident 1400 (prototype Manor Lords)
# ---------------------------------------------------------------------------

def construire_bat_maison_colombages(c: Constructeur, lod: int) -> None:
    # Rez-de-chaussée en pierre appareillée (6.2 x 5.2 x 2.7 m)
    c.boite((0, 0, 1.35), (6.20, 5.20, 2.70), "pierre_claire")
    # Porte d'entrée en chêne + perron
    c.boite((0.0, -2.62, 1.05), (1.15, 0.14, 2.10), "bois")
    c.boite((0.0, -2.76, 0.12), (1.50, 0.42, 0.24), "pierre")
    # Étage à encorbellement en colombages/torchis (6.7 x 5.7 x 2.6 m)
    c.boite((0, 0, 4.00), (6.70, 5.70, 2.60), "colombage")
    # Poutres de ceinture + corbeaux sous l'encorbellement (LOD0/1)
    if lod <= 1:
        c.boite((0, 0, 2.72), (6.80, 5.80, 0.18), "bois")
        c.boite((0, 0, 5.26), (6.82, 5.82, 0.16), "bois")
        for sx in (-2.7, -1.35, 0.0, 1.35, 2.7):
            for sy in (-2.72, 2.72):
                c.boite((sx, sy, 2.46), (0.20, 0.34, 0.36), "bois")
    # Toit pentu en tuiles médiévales + cheminée en pierre
    c.prisme_toit((0, 0, 5.30), 6.70, 5.70, 3.10, "tuiles", "colombage", debord_x=0.36, debord_y=0.40, epaisseur_toit=0.18)
    c.boite((-1.20, 0.85, 7.65), (0.85, 0.85, 2.40), "pierre")
    if lod == 0:
        c.boite((-1.20, 0.85, 8.90), (0.98, 0.98, 0.16), "pierre_claire")
        # Fenêtres à volets de bois en façade avant et pignon droit
        for fx in (-1.85, 1.85):
            c.boite((fx, -2.88, 4.05), (0.95, 0.10, 1.15), "bois")
            c.boite((fx - 0.62, -2.90, 4.05), (0.28, 0.08, 1.15), "bois_clair")
            c.boite((fx + 0.62, -2.90, 4.05), (0.28, 0.08, 1.15), "bois_clair")
        for fy in (-1.35, 1.35):
            c.boite((3.38, fy, 4.05), (0.10, 0.95, 1.15), "bois")
        # Banc + tonneau contre la façade (écho à la vue de référence)
        c.boite((2.20, -2.92, 0.42), (1.35, 0.36, 0.08), "bois_clair")
        c.cylindre((3.45, -2.45, 0.44), 0.28, 0.28, 0.88, 12, "bois")


def construire_bat_grenier_medieval(c: Constructeur, lod: int) -> None:
    # Plots de fondation en pierre (anti-humidité)
    for sx in (-3.6, -1.2, 1.2, 3.6):
        for sy in (-2.4, 2.4):
            c.boite((sx, sy, 0.25), (0.55, 0.55, 0.50), "pierre")
    # Corps principal en bois & colombage (8.2 x 5.6 x 3.2 m)
    c.boite((0, 0, 2.10), (8.20, 5.60, 3.20), "bois_clair")
    if lod <= 1:
        # Poteaux verticaux d'ossature
        for sx in (-4.12, -2.05, 0.0, 2.05, 4.12):
            for sy in (-2.82, 2.82):
                c.boite((sx, sy, 2.10), (0.22, 0.18, 3.28), "bois")
        c.boite((0, 0, 0.56), (8.36, 5.76, 0.20), "bois")
        c.boite((0, 0, 3.66), (8.36, 5.76, 0.20), "bois")
    # Grande double porte charretière + rampe bois
    c.boite((0.0, -2.85, 1.72), (2.20, 0.16, 2.35), "bois")
    c.boite((0.0, -3.35, 0.24), (2.40, 1.05, 0.48), "bois_clair", rot=(0.28, 0.0, 0.0))
    if lod == 0:
        for hz in (1.05, 2.25):
            c.boite((0.0, -2.95, hz), (2.05, 0.05, 0.09), "metal")
    # Toit pentu en chaume médiéval
    c.prisme_toit((0, 0, 3.70), 8.20, 5.60, 3.30, "chaume", "bois_clair", debord_x=0.45, debord_y=0.50, epaisseur_toit=0.28)
    # Lucarne de grenier en pignon + 2 sacs au seuil (LOD0/1)
    if lod <= 1:
        c.boite((-4.15, 0.0, 4.75), (0.14, 1.10, 1.25), "bois")
        c.boite((-4.45, 0.0, 5.65), (0.85, 0.16, 0.16), "bois")
        c.sphere((-1.55, -3.15, 0.24), (0.34, 0.24, 0.22), 10 if lod == 0 else 6, 5, "jute")
        c.sphere((1.55, -3.15, 0.24), (0.34, 0.24, 0.22), 10 if lod == 0 else 6, 5, "jute")


def construire_bat_forge_medievale(c: Constructeur, lod: int) -> None:
    # Atelier fermé en pierre sombre (5.6 x 4.8 x 2.9 m)
    c.boite((-0.90, 0.0, 1.45), (5.60, 4.80, 2.90), "pierre")
    c.prisme_toit((-0.90, 0.0, 2.90), 5.60, 4.80, 2.40, "tuiles", "colombage", debord_x=0.32, debord_y=0.35, epaisseur_toit=0.16)
    # Haute cheminée de foyer en pierre
    c.boite((-2.80, 0.40, 3.20), (1.35, 1.35, 6.40), "pierre")
    if lod <= 1:
        c.boite((-2.80, 0.40, 6.48), (1.52, 1.52, 0.20), "pierre_claire")
    # Auvent ouvert à droite (3.4 x 4.4 m) abritant le travail du forgeron
    c.boite((3.25, -2.10, 1.32), (0.20, 0.20, 2.64), "bois")
    c.boite((3.25, 2.10, 1.32), (0.20, 0.20, 2.64), "bois")
    c.boite((2.65, 0.0, 2.86), (3.45, 4.75, 0.16), "tuiles", rot=(0.0, 0.24, 0.0))
    # Foyer ardent extérieur + enclume sur billot + bac de trempe + charbon (placés vers l'avant -Y)
    c.boite((2.20, -0.85, 0.56), (1.28, 1.15, 1.12), "pierre_claire")
    c.boite((2.28, -0.85, 1.14), (0.82, 0.72, 0.16), "braise")
    c.cylindre((2.55, 0.65, 0.36), 0.30, 0.28, 0.72, 12 if lod == 0 else 6, "bois")
    c.boite((2.55, 0.65, 0.84), (0.68, 0.28, 0.24), "metal")
    if lod == 0:
        c.boite((2.98, 0.65, 0.88), (0.28, 0.16, 0.14), "metal")  # bigorne
        c.boite((2.45, -1.95, 0.32), (0.88, 0.56, 0.58), "bois")
        c.boite((2.45, -1.95, 0.56), (0.76, 0.44, 0.06), "eau")
        c.sphere((2.15, 1.65, 0.24), (0.62, 0.48, 0.32), 10, 6, "charbon")


def construire_bat_porte_fortifiee(c: Constructeur, lod: int) -> None:
    segs = (20, 12, 8)[lod]
    # Deux grosses tours circulaires encadrant le passage (entraxe 6.8 m)
    for sx in (-3.40, 3.40):
        c.cylindre((sx, 0.0, 3.80), 2.15, 1.95, 7.60, segs, "pierre_claire")
        # Collerette de mâchicoulis + chemin de ronde
        c.cylindre((sx, 0.0, 7.75), 2.22, 2.22, 0.55, segs, "pierre")
        if lod == 0:
            c.anneau_creneaux(8.02, sx, 0.0, 2.04, 12, 0.52, 0.30, 0.55, "pierre_claire")
        # Toit conique en tuiles
        c.cylindre((sx, 0.0, 9.85), 2.38, 0.05, 3.40, segs, "tuiles")
    # Corps central au-dessus de l'arche (passage libre 3.2 m de large × 3.8 m de haut)
    c.boite((0.0, 0.0, 5.45), (4.20, 3.10, 3.50), "pierre_claire")
    c.boite((0.0, 0.0, 7.42), (4.50, 3.50, 0.55), "bois")  # hourd en bois
    c.prisme_toit((0.0, 0.0, 7.70), 4.40, 3.40, 1.70, "tuiles", "bois", debord_x=0.25, debord_y=0.25, epaisseur_toit=0.14)
    # Piédroits de l'arche + pavage au sol
    c.boite((0.0, 0.0, 0.06), (3.80, 4.40, 0.12), "paves")
    # Herse relevée en fer/bois sous l'arche (LOD0/1)
    if lod <= 1:
        c.boite((0.0, -1.25, 3.25), (3.10, 0.14, 0.14), "metal")
        for gx in (-1.2, -0.6, 0.0, 0.6, 1.2):
            c.boite((gx, -1.25, 3.15), (0.10, 0.12, 1.35), "metal")
    if lod == 0:
        for hx in (-1.5, -0.75, 0.0, 0.75, 1.5):
            c.boite((hx, -1.58, 7.02), (0.20, 0.36, 0.42), "bois")


# ---------------------------------------------------------------------------
# Catalogue complet, export FBX, rendu Cycles studio et vérification réimport
# ---------------------------------------------------------------------------

CATALOGUE = [
    # Pack 1 — Pions 3D carte
    ("pion_armee", "PionsCarte", 0.9, construire_pion_armee),
    ("pion_siege", "PionsCarte", 0.9, construire_pion_siege),
    ("pion_capitale", "PionsCarte", 1.2, construire_pion_capitale),
    ("pion_bourg", "PionsCarte", 1.0, construire_pion_bourg),
    # Pack 2 — Props vie urbaine
    ("prop_charrette", "PropsVille", 1.0, construire_prop_charrette),
    ("prop_etal_marche", "PropsVille", 1.2, construire_prop_etal_marche),
    ("prop_puits_pierre", "PropsVille", 1.2, construire_prop_puits_pierre),
    ("prop_sacs_grain", "PropsVille", 0.9, construire_prop_sacs_grain),
    ("prop_echafaudage", "PropsVille", 1.5, construire_prop_echafaudage),
    ("prop_tonneaux_caisses", "PropsVille", 0.9, construire_prop_tonneaux_caisses),
    # Pack 3 — Bâtiments d'Occident 1400
    ("bat_maison_colombages", "BatimentsOccident", 2.4, construire_bat_maison_colombages),
    ("bat_grenier_medieval", "BatimentsOccident", 2.6, construire_bat_grenier_medieval),
    ("bat_forge_medievale", "BatimentsOccident", 2.4, construire_bat_forge_medievale),
    ("bat_porte_fortifiee", "BatimentsOccident", 3.0, construire_bat_porte_fortifiee),
]


def rendre_studio(obj_lod0: bpy.types.Object, sortie_png: Path) -> None:
    """Rend une vue 3/4 neutre Cycles CPU de l'objet `obj_lod0`."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = False
    scene.cycles.max_bounces = 4
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX" if "AgX" in [i.identifier for i in scene.view_settings.bl_rna.properties["view_transform"].enum_items] else "Filmic"

    # Fond studio gris chaud sombre neutre
    world = bpy.data.worlds.new("Studio")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.11, 0.105, 0.098, 1.0)
    bg.inputs["Strength"].default_value = 0.85

    # Boîte englobante du modèle
    coins = [obj_lod0.matrix_world @ Vector(c) for c in obj_lod0.bound_box]
    bmin = Vector((min(v.x for v in coins), min(v.y for v in coins), min(v.z for v in coins)))
    bmax = Vector((max(v.x for v in coins), max(v.y for v in coins), max(v.z for v in coins)))
    centre = (bmin + bmax) * 0.5
    rayon = max((bmax - bmin).length * 0.5, 0.5)

    # Disque de sol discret pour ancrer le pivot
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=rayon * 1.45, depth=0.04, location=(centre.x, centre.y, -0.02))
    sol = bpy.context.active_object
    sol.data.materials.append(creer_materiau_simple("M_SolStudio", (0.14, 0.13, 0.12), roughness=0.92))

    # Caméra 3/4 cadrée automatiquement sur la boîte englobante
    cam_data = bpy.data.cameras.new("CamStudio")
    cam_data.lens = 50.0
    cam = bpy.data.objects.new("CamStudio", cam_data)
    scene.collection.objects.link(cam)
    dist = rayon * 2.75
    cam.location = centre + Vector((dist * 0.72, -dist * 0.82, dist * 0.52))
    direction = (centre - cam.location).normalized()
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam

    # Éclairage 3 points (soleil chaud + lumière de débouchage froide)
    sun1 = bpy.data.lights.new("KeySun", type="SUN")
    sun1.energy = 3.2
    sun1.color = (1.0, 0.94, 0.84)
    sun1.angle = math.radians(8.0)
    o1 = bpy.data.objects.new("KeySun", sun1)
    o1.rotation_euler = Euler((math.radians(48), math.radians(12), math.radians(-38)), "XYZ")
    scene.collection.objects.link(o1)

    sun2 = bpy.data.lights.new("FillSun", type="SUN")
    sun2.energy = 1.1
    sun2.color = (0.76, 0.84, 1.0)
    sun2.angle = math.radians(20.0)
    o2 = bpy.data.objects.new("FillSun", sun2)
    o2.rotation_euler = Euler((math.radians(65), 0.0, math.radians(145)), "XYZ")
    scene.collection.objects.link(o2)

    sortie_png.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(sortie_png.resolve())
    bpy.ops.render.render(write_still=True)


def verifier_fbx(chemin_fbx: Path, nom_id: str) -> dict:
    """Réimporte le FBX dans une scène vierge et vérifie les 3 LOD et dimensions."""
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
            c = Constructeur(palette, echelle_uv=echelle_uv)
            fn(c, k)
            obj = c.finaliser(f"{nom_id}_LOD{k}")
            lods.append(obj)

        # Export FBX des 3 LOD ensemble
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

        # Rendu studio du seul LOD0
        lods[1].hide_render = True
        lods[2].hide_render = True
        chemin_rendu = dossier_sortie / "Rendus" / f"{nom_id}_rendu.png"
        rendre_studio(lods[0], chemin_rendu)

        # Vérification stricte par réimport FBX
        mesure = verifier_fbx(chemin_fbx, nom_id)
        mesure["categorie"] = categorie
        mesure["rendu"] = chemin_rendu.name
        rapport.append(mesure)
        print(f"OK {nom_id:24} tris={mesure['triangles']} dims={mesure['dimensions_m']}m")

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
    fabriquer_tout(args.sortie, args.textures)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
