"""Demande à forge3d une photographie 3D du MNT. Aucune mécanique de monde."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import numpy as np

from vues.relief.raster import HAUTEURS_M, Mnt


class RenduErreur(RuntimeError):
    """Le moteur de rendu a refusé, ou il n'est pas là."""


def _hdr_minimal(path: Path) -> None:
    """Environnement Radiance 2×2, suffisant pour allumer IBL."""
    path.write_bytes(
        b"#?RADIANCE\n"
        b"FORMAT=32-bit_rle_rgbe\n\n"
        b"-Y 2 +X 2\n"
        + bytes([180, 190, 205, 128]) * 4
    )


# Le dégradé du relief géographique : mer, prairie, plateau, roche, neige.
# Ce n'est PAS un dégradé séquentiel — il n'encode aucune magnitude, il donne
# une teinte de terrain à chaque tranche d'altitude, et c'est pourquoi il a le
# droit de changer de teinte. Une carte de STATISTIQUE, elle, prend le dégradé
# d'une seule teinte de `lectures.RAMPE`.
STOPS_RELIEF = [
    (0.00, "#1a3d6e"),
    (0.02, "#2d6a3a"),
    (0.15, "#6b8f3a"),
    (0.40, "#c4a574"),
    (0.70, "#8a7a6a"),
    (1.00, "#f2f0ea"),
]


def rendre_png(mnt: Mnt, destination: Path, *, largeur_px: int = 960, hauteur_px: int = 540) -> Path:
    """Rendu hors écran du relief géographique."""
    h_max = float(max(HAUTEURS_M.values()))
    return rendre_champ_png(
        mnt.altitudes_m,
        (~mnt.masque_terre).astype(np.float32),
        destination,
        stops=STOPS_RELIEF,
        h_max=h_max,
        largeur_px=largeur_px,
        hauteur_px=hauteur_px,
    )


def rendre_champ_png(
    altitudes_m,
    masque_eau,
    destination: Path,
    *,
    stops,
    h_max: float,
    largeur_px: int = 960,
    hauteur_px: int = 540,
) -> Path:
    """
    Élève un champ de valeurs et le rend hors écran.

    UN seul chemin vers forge3d dans tout le visualisateur, deux appelants :
    le relief géographique, qui élève des mètres, et la carte de statistique,
    qui élève une grandeur du monde. Ce qui change entre les deux est le champ
    et son dégradé — jamais la façon de rendre.
    """
    try:
        import forge3d as f3d
        from forge3d.terrain_params import (
            LodSettings,
            PomSettings,
            SamplingSettings,
            ShadowSettings,
            make_terrain_params_config,
        )
    except ImportError as exc:
        raise RenduErreur(
            "forge3d est absent. Dans le venv du visualisateur : "
            "python3 -m pip install forge3d"
        ) from exc

    if not f3d.has_gpu():
        raise RenduErreur(
            "forge3d ne voit aucun adaptateur GPU (ni logiciel). "
            "Installer mesa-vulkan-drivers, ou une carte."
        )
    manquants = [
        nom
        for nom in ("Session", "TerrainRenderer", "MaterialSet", "IBL", "Colormap1D", "OverlayLayer", "TerrainRenderParams")
        if not hasattr(f3d, nom)
    ]
    if manquants:
        raise RenduErreur("forge3d incomplet : " + ", ".join(manquants))

    altitudes = np.clip(np.asarray(altitudes_m) / max(h_max, 1e-6), 0.0, 1.0).astype(np.float32)
    # Le MNT canonique de forge3d vit dans un monde de largeur 2. On s'y tient :
    # l'étendue kilométrique de la carte ne doit pas écraser le relief.
    terrain_span = 2.0
    fraction_lisible = 0.18
    z_scale = fraction_lisible * terrain_span / max(float(altitudes.max()), 1e-6)

    domaine = (0.0, 1.0)
    colormap = f3d.Colormap1D.from_stops(stops=list(stops), domain=domaine)
    overlays = [
        f3d.OverlayLayer.from_colormap1d(
            colormap,
            strength=1.0,
            offset=0.0,
            blend_mode="Alpha",
            domain=domaine,
        )
    ]
    config = make_terrain_params_config(
        size_px=(int(largeur_px), int(hauteur_px)),
        render_scale=1.0,
        terrain_span=terrain_span,
        msaa_samples=1,
        z_scale=float(z_scale),
        exposure=1.15,
        domain=domaine,
        albedo_mode="colormap",
        colormap_strength=1.0,
        ibl_enabled=True,
        sun_intensity=3.0,
        light_azimuth_deg=210.0,
        light_elevation_deg=32.0,
        cam_radius=3.2,
        cam_phi_deg=210.0,
        cam_theta_deg=38.0,
        fov_y_deg=50.0,
        overlays=overlays,
        clip=(0.05, 40.0),
        culling="none",
        camera_mode="mesh:zup",
        pom=PomSettings(False, "Occlusion", 0.0, 1, 1, 0, False, False),
        lod=LodSettings(0, 0.0, 0.0),
        sampling=SamplingSettings(
            "Nearest",
            "Nearest",
            "Nearest",
            1,
            "ClampToEdge",
            "ClampToEdge",
            "ClampToEdge",
        ),
        shadows=ShadowSettings(
            True, "PCF", 512, 2, 40.0, 1.0, 0.8, 0.002, 0.001, 0.3, 1e-4, 0.5, 2.0, 0.9
        ),
    )
    params = f3d.TerrainRenderParams(config)
    session = f3d.Session(window=False)
    renderer = f3d.TerrainRenderer(session)
    materiaux = f3d.MaterialSet.terrain_default()
    masque_eau = np.asarray(masque_eau, dtype=np.float32)

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        hdr = Path(tmp) / "ciel.hdr"
        _hdr_minimal(hdr)
        ibl = f3d.IBL.from_hdr(str(hdr), intensity=1.0)
        cadre = renderer.render_terrain_pbr_pom(
            material_set=materiaux,
            env_maps=ibl,
            params=params,
            heightmap=altitudes,
            target=None,
            water_mask=masque_eau,
        )
        cadre.save(str(destination))
    if not destination.is_file() or destination.stat().st_size < 32:
        raise RenduErreur(f"png absent ou vide : {destination}")
    return destination
