"""Generate a deterministic CityLab PBR trim sheet from a recipe.

Les bandes sont pilotees par recipe["regions"] : chaque region nomme un
materiau (wood, stone, roof, brick, plank) et son intervalle v. Ajouter une
bande est une entree de recette, pas une branche de code.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(array: np.ndarray) -> str:
    """Empreinte des pixels, pas du conteneur.

    Le sha256 d'un PNG depend de la version de l'encodeur : deux machines
    peuvent produire la meme image et deux fichiers differents. Le projet
    refuse deja le conteneur FBX comme preuve de determinisme pour les
    maillages ; les textures suivent la meme regle.
    """
    return hashlib.sha256(np.clip(array, 0, 255).astype(np.uint8).tobytes()).hexdigest()


def save_rgb(path: Path, array: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(array, 0, 255).astype(np.uint8), "RGB").save(path, optimize=True)


def save_gray(path: Path, array: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(array, 0, 255).astype(np.uint8), "L").save(path, optimize=True)


def smooth(array: np.ndarray, radius: float) -> np.ndarray:
    image = Image.fromarray(np.clip(array * 255.0, 0, 255).astype(np.uint8), "L")
    return np.asarray(image.filter(ImageFilter.GaussianBlur(radius=radius)), dtype=np.float32) / 255.0


def multiscale_noise(rng: np.random.Generator, size: int) -> tuple[np.ndarray, np.ndarray]:
    micro = rng.random((size, size), dtype=np.float32)
    coarse_size = max(16, size // 32)
    coarse = rng.random((coarse_size, coarse_size), dtype=np.float32)
    macro = np.asarray(Image.fromarray((coarse * 255).astype(np.uint8), "L").resize(
        (size, size), Image.Resampling.BICUBIC), dtype=np.float32) / 255.0
    return smooth(micro, 1.2), smooth(macro, 3.0)


class BandContext:
    """Etat partage entre les generateurs de bandes du trim sheet."""

    def __init__(self, size: int, palette: dict[str, np.ndarray],
                 micro: np.ndarray, macro: np.ndarray,
                 xx: np.ndarray, yy: np.ndarray) -> None:
        self.size = size
        self.palette = palette
        self.micro = micro
        self.macro = macro
        self.xx = xx
        self.yy = yy
        self.base = np.zeros((size, size, 3), dtype=np.float32)
        self.height = np.zeros((size, size), dtype=np.float32)
        self.roughness = np.zeros((size, size), dtype=np.float32)
        self.metallic = np.zeros((size, size), dtype=np.float32)
        self.edges = np.zeros((size, size), dtype=np.float32)
        self.material_id = np.zeros((size, size), dtype=np.float32)


def band_bounds(region: dict, size: int) -> tuple[int, int]:
    """Convertir un intervalle v en lignes de pixels.

    Le plancher reproduit exactement les bornes size//3 et size*2//3 du
    decoupage historique en trois bandes.
    """
    return int(region["v_min"] * size), int(region["v_max"] * size)


def band_structural_wood(ctx: BandContext, y_min: int, y_max: int) -> None:
    """Larges planches verticales, fil longitudinal fin et clous forges."""
    size, xx, yy = ctx.size, ctx.xx, ctx.yy
    micro, macro, palette = ctx.micro, ctx.macro, ctx.palette
    band_height = y_max - y_min
    wood = (yy >= y_min) & (yy < y_max)
    plank_width = max(64, size // 8)
    seam = wood & (((xx % plank_width) < max(5, size // 256)) |
                   ((xx % plank_width) > plank_width - max(5, size // 256)))
    grain = 0.5 + 0.5 * np.sin(yy * 0.105 + np.sin(xx * 0.022) * 2.2)
    wood_mix = np.clip(0.20 + 0.48 * macro + 0.16 * grain + 0.10 * micro, 0, 1)
    ctx.base[wood] = palette["wood"] + (palette["wood_highlight"] - palette["wood"]) * wood_mix[wood, None]
    ctx.height[wood] = 0.55 + (grain[wood] - 0.5) * 0.075 + (macro[wood] - 0.5) * 0.10
    ctx.height[seam] = 0.16
    ctx.base[seam] *= 0.38
    ctx.edges[seam] = 1.0
    ctx.roughness[wood] = 0.69 + (micro[wood] - 0.5) * 0.13
    ctx.material_id[wood] = 0.18
    nail_radius = max(4, size // 300)
    for x in range(plank_width // 2, size, plank_width):
        for y in (y_min + band_height // 5, y_min + band_height * 4 // 5):
            nail = wood & ((xx - x) ** 2 + (yy - y) ** 2 <= nail_radius ** 2)
            ctx.base[nail] = palette["iron"]
            ctx.height[nail] = 0.68
            ctx.metallic[nail] = 0.88
            ctx.roughness[nail] = 0.34


def band_dressed_stone(ctx: BandContext, y_min: int, y_max: int) -> None:
    """Assises alternees, variation de bloc deterministe et mortier creuse."""
    size, xx, yy = ctx.size, ctx.xx, ctx.yy
    micro, macro, palette = ctx.micro, ctx.macro, ctx.palette
    stone = (yy >= y_min) & (yy < y_max)
    stone_y = yy - y_min
    course_h = max(48, (y_max - y_min) // 6)
    block_w = max(150, size // 9)
    row = stone_y // course_h
    shifted_x = (xx + (row % 2) * (block_w // 2)) % block_w
    mortar_w = max(5, size // 300)
    mortar = stone & (((stone_y % course_h) < mortar_w) |
                      (shifted_x < mortar_w) | (shifted_x > block_w - mortar_w))
    cell = ((row * 17 + (xx + (row % 2) * block_w // 2) // block_w * 31) % 13) / 12.0
    stone_tone = np.clip(0.64 + (cell - 0.5) * 0.24 + (macro - 0.5) * 0.22, 0.28, 0.94)
    ctx.base[stone] = palette["stone"] * stone_tone[stone, None]
    ctx.base[mortar] = palette["mortar"] * (0.78 + micro[mortar, None] * 0.12)
    ctx.height[stone] = 0.61 + (macro[stone] - 0.5) * 0.16 + (micro[stone] - 0.5) * 0.05
    ctx.height[mortar] = 0.12
    ctx.edges[mortar] = 1.0
    ctx.roughness[stone] = 0.84 + (micro[stone] - 0.5) * 0.10
    ctx.roughness[mortar] = 0.95
    ctx.material_id[stone] = 0.52


def band_roof_tiles(ctx: BandContext, y_min: int, y_max: int) -> None:
    """Tuiles decalees et recouvrantes, rainures lisibles a distance RTS."""
    size, xx, yy = ctx.size, ctx.xx, ctx.yy
    micro, macro, palette = ctx.micro, ctx.macro, ctx.palette
    roof = (yy >= y_min) & (yy < y_max)
    roof_y = yy - y_min
    tile_h = max(48, (y_max - y_min) // 6)
    tile_w = max(96, size // 14)
    tile_row = roof_y // tile_h
    roof_x = (xx + (tile_row % 2) * (tile_w // 2)) % tile_w
    groove_w = max(5, size // 300)
    overlap = roof & ((roof_y % tile_h) < groove_w)
    groove = roof & ((roof_x < groove_w) | (roof_x > tile_w - groove_w) | overlap)
    ramp = (roof_y % tile_h) / float(tile_h)
    roof_mix = np.clip(0.25 + macro * 0.48 + micro * 0.13 + ramp * 0.14, 0, 1)
    ctx.base[roof] = palette["roof"] + (palette["roof_highlight"] - palette["roof"]) * roof_mix[roof, None]
    ctx.height[roof] = 0.43 + ramp[roof] * 0.24 + (macro[roof] - 0.5) * 0.07
    ctx.height[groove] = 0.14
    ctx.base[groove] *= 0.52
    ctx.edges[groove] = 1.0
    ctx.roughness[roof] = 0.74 + (micro[roof] - 0.5) * 0.12
    ctx.material_id[roof] = 0.86


def band_fired_brick(ctx: BandContext, y_min: int, y_max: int) -> None:
    """Briques de terre cuite : assises serrees et joints plus fins que la pierre."""
    size, xx, yy = ctx.size, ctx.xx, ctx.yy
    micro, macro, palette = ctx.micro, ctx.macro, ctx.palette
    brick = (yy >= y_min) & (yy < y_max)
    brick_y = yy - y_min
    # La lisibilite a 128 px tient a la variation de teinte par brique, basse
    # frequence, et non aux joints qui disparaissent au sous-echantillonnage.
    course_h = max(24, (y_max - y_min) // 8)
    block_w = max(64, size // 16)
    row = brick_y // course_h
    shifted_x = (xx + (row % 2) * (block_w // 2)) % block_w
    joint_w = max(4, size // 320)
    joint = brick & (((brick_y % course_h) < joint_w) |
                     (shifted_x < joint_w) | (shifted_x > block_w - joint_w))
    cell = ((row * 23 + (xx + (row % 2) * block_w // 2) // block_w * 41) % 11) / 10.0
    brick_tone = np.clip(0.66 + (cell - 0.5) * 0.52 + (macro - 0.5) * 0.22, 0.26, 1.02)
    ctx.base[brick] = palette["brick"] * brick_tone[brick, None]
    ctx.base[joint] = palette["brick_mortar"] * (0.58 + micro[joint, None] * 0.12)
    ctx.height[brick] = 0.58 + (macro[brick] - 0.5) * 0.12 + (micro[brick] - 0.5) * 0.05
    ctx.height[joint] = 0.10
    ctx.edges[joint] = 1.0
    ctx.roughness[brick] = 0.80 + (micro[brick] - 0.5) * 0.10
    ctx.roughness[joint] = 0.94
    ctx.material_id[brick] = 0.68


def band_sawn_planks(ctx: BandContext, y_min: int, y_max: int) -> None:
    """Planches sciees horizontales : bardage agricole, fil transversal et joints creux."""
    size, xx, yy = ctx.size, ctx.xx, ctx.yy
    micro, macro, palette = ctx.micro, ctx.macro, ctx.palette
    planks = (yy >= y_min) & (yy < y_max)
    plank_y = yy - y_min
    board_h = max(32, (y_max - y_min) // 8)
    seam_w = max(4, size // 350)
    seam = planks & ((plank_y % board_h) < seam_w)
    grain = 0.5 + 0.5 * np.sin(xx * 0.09 + np.sin(plank_y * 0.03) * 2.0)
    plank_mix = np.clip(0.24 + 0.46 * macro + 0.18 * grain + 0.10 * micro, 0, 1)
    ctx.base[planks] = (palette["plank"]
                        + (palette["plank_highlight"] - palette["plank"]) * plank_mix[planks, None])
    ctx.height[planks] = 0.52 + (grain[planks] - 0.5) * 0.08 + (macro[planks] - 0.5) * 0.09
    ctx.height[seam] = 0.14
    ctx.base[seam] *= 0.42
    ctx.edges[seam] = 1.0
    ctx.roughness[planks] = 0.72 + (micro[planks] - 0.5) * 0.12
    ctx.material_id[planks] = 0.34


def band_lime_plaster(ctx: BandContext, y_min: int, y_max: int) -> None:
    """Panneaux de chaux clairs dans une ossature de bois sombre.

    C'est la bande qui manquait, et son absence etait mesurable : sur
    `citylab_trim_v1`, 90 % des pixels tombent sous 78 sur 255, alors que les
    references de style tiennent leur lecture du contraste entre panneaux clairs
    et bois sombre -- p90 a 155 et 162 pour une etendue de 114 et 127.

    Le contraste vit **dans** la bande, pas entre les bandes : le meme rectangle
    de trim porte le panneau clair et le pan de bois qui l'encadre. C'est aussi
    ce que fait un colombage reel, et cela evite de depenser un ilot UV par
    materiau sur une facade.
    """
    size, xx, yy = ctx.size, ctx.xx, ctx.yy
    micro, macro, palette = ctx.micro, ctx.macro, ctx.palette
    band = (yy >= y_min) & (yy < y_max)
    band_h = y_max - y_min
    local_y = yy - y_min

    # Enduit : clair, legerement mottle, jamais uniforme -- un aplat clair lit
    # comme du carton a 96 px.
    render_mix = np.clip(0.34 + 0.44 * macro + 0.22 * micro, 0, 1)
    ctx.base[band] = (palette["plaster_shade"]
                      + (palette["plaster"] - palette["plaster_shade"]) * render_mix[band, None])
    ctx.height[band] = 0.44 + (macro[band] - 0.5) * 0.06 + (micro[band] - 0.5) * 0.04
    ctx.roughness[band] = 0.90 + (micro[band] - 0.5) * 0.06
    ctx.material_id[band] = 0.86

    # Ossature : poteaux, sabliere basse, sabliere haute, et une echarpe par
    # travee. Le bois est proud de l'enduit, la normal map le rend seule.
    # Deux travees par bande. A six, la travee dessinee valait environ 0,4 m sur
    # le mur : un motif uniforme, sans rapport avec les travees reelles de la
    # facade, qui font 2,1 a 2,8 m. L'ossature doit decouper la facade, pas la
    # tapisser.
    bay = max(96, size // 2)
    post_w = max(10, size // 120)
    rail_h = max(12, band_h // 10)
    post = band & (((xx % bay) < post_w) | ((xx % bay) > bay - post_w))
    rail = band & ((local_y < rail_h) | (local_y > band_h - rail_h))

    # Echarpe : diagonale continue dans chaque travee, epaisseur constante.
    bay_x = (xx % bay).astype(np.float32) / float(bay)
    bay_y = local_y.astype(np.float32) / float(max(1, band_h))
    brace = band & (np.abs(bay_x - bay_y) < (post_w * 1.2) / float(bay))

    timber = post | rail | brace
    timber_mix = np.clip(0.30 + 0.40 * macro + 0.20 * micro, 0, 1)
    ctx.base[timber] = (palette["wood"]
                        + (palette["wood_highlight"] - palette["wood"]) * timber_mix[timber, None] * 0.55)
    ctx.height[timber] = 0.70 + (macro[timber] - 0.5) * 0.07
    ctx.roughness[timber] = 0.70 + (micro[timber] - 0.5) * 0.11
    ctx.material_id[timber] = 0.86

    # Le joint enduit/bois est l'arete que l'AO doit creuser.
    joint = band & ~timber & (
        np.roll(timber, 1, axis=1) | np.roll(timber, -1, axis=1)
        | np.roll(timber, 1, axis=0) | np.roll(timber, -1, axis=0))
    ctx.edges[joint] = 1.0
    ctx.height[joint] = 0.40


BAND_GENERATORS = {
    "wood": band_structural_wood,
    "stone": band_dressed_stone,
    "roof": band_roof_tiles,
    "brick": band_fired_brick,
    "plank": band_sawn_planks,
    "plaster": band_lime_plaster,
}


def build_maps(recipe: dict) -> dict[str, np.ndarray]:
    size = recipe["resolution"]
    rng = np.random.default_rng(recipe["seed"])
    micro, macro = multiscale_noise(rng, size)
    yy, xx = np.mgrid[0:size, 0:size]
    palette = {key: np.asarray(value, dtype=np.float32) for key, value in recipe["palette"].items()}
    ctx = BandContext(size, palette, micro, macro, xx, yy)

    for region in recipe["regions"]:
        material = region["material"]
        generator = BAND_GENERATORS.get(material)
        if generator is None:
            raise RuntimeError(f"Unknown trim band material: {material}")
        y_min, y_max = band_bounds(region, size)
        generator(ctx, y_min, y_max)

    base, edges, material_id = ctx.base, ctx.edges, ctx.material_id
    roughness, metallic = ctx.roughness, ctx.metallic
    height = np.clip(ctx.height, 0, 1)
    gy, gx = np.gradient(height)
    strength = 7.5
    nx, ny, nz = -gx * strength, -gy * strength, np.ones_like(height)
    length = np.sqrt(nx * nx + ny * ny + nz * nz)
    normal = np.stack(((nx / length * 0.5 + 0.5) * 255,
                       (ny / length * 0.5 + 0.5) * 255,
                       (nz / length * 0.5 + 0.5) * 255), axis=2)
    blurred = smooth(height, max(2.0, size / 512.0))
    concavity = np.clip(blurred - height, 0, 0.5)
    ao = np.clip(1.0 - concavity * 1.7 - edges * 0.24, 0.22, 1.0) * 255
    variation = np.stack((np.clip(macro * 0.72 + micro * 0.28, 0, 1) * 255,
                          edges * 255, material_id * 255), axis=2)
    return {
        "BaseColor": base,
        "Normal": normal,
        "AO": ao,
        "Roughness": np.clip(roughness, 0, 1) * 255,
        "Metallic": np.clip(metallic, 0, 1) * 255,
        "VariationMask": variation,
    }


def review_sheet(basecolor_path: Path, resolutions: list[int], output: Path,
                 regions: list[dict]) -> dict[str, dict[str, float]]:
    source = Image.open(basecolor_path).convert("RGB")
    panel = 512
    font_path = Path("C:/Windows/Fonts/arial.ttf")
    font = ImageFont.truetype(font_path, 20) if font_path.is_file() else ImageFont.load_default(size=20)
    sheet = Image.new("RGB", (panel * len(resolutions), panel + 42), "#101820")
    draw = ImageDraw.Draw(sheet)
    metrics = {}
    for index, resolution in enumerate(resolutions):
        reduced = source.resize((resolution, resolution), Image.Resampling.LANCZOS)
        array = np.asarray(reduced, dtype=np.float32)
        bands = {}
        for region in regions:
            lower, upper = band_bounds(region, resolution)
            upper = max(upper, lower + 1)
            bands[region["id"]] = round(
                float(np.std(np.mean(array[lower:upper], axis=2))), 4)
        metrics[str(resolution)] = bands
        enlarged = reduced.resize((panel, panel), Image.Resampling.NEAREST)
        sheet.paste(enlarged, (index * panel, 0))
        label = f"{resolution} × {resolution}"
        bounds = draw.textbbox((0, 0), label, font=font)
        draw.text((index * panel + (panel - bounds[2] + bounds[0]) / 2, panel + 9),
                  label, font=font, fill="#F0E5D1")
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, optimize=True)
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--recipe", default="AssetFactory/Recipes/texture_citylab_trim_v1.json")
    parser.add_argument("--verify-determinism", action="store_true")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    recipe = json.loads((root / args.recipe).read_text(encoding="utf-8"))
    manifest_path = root / recipe["outputs"]["manifest"]
    previous_hashes = None
    if args.verify_determinism and manifest_path.is_file():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        previous_hashes = {asset["id"]: asset.get("canonical_sha256")
                           for asset in previous.get("assets", [])}
    maps = build_maps(recipe)
    workbench = root / recipe["outputs"]["workbench"]
    prefix = recipe.get("file_prefix", "CityLabTrim_")
    names = {map_name: f"{prefix}{map_name}.png" for map_name in (
        "BaseColor", "Normal", "AO", "Roughness", "Metallic", "VariationMask")}
    canonical = {map_name: canonical_sha256(array) for map_name, array in maps.items()}
    for map_name, filename in names.items():
        path = workbench / filename
        if maps[map_name].ndim == 3:
            save_rgb(path, maps[map_name])
        else:
            save_gray(path, maps[map_name])
    contrast = review_sheet(workbench / names["BaseColor"], recipe["review_resolutions"],
                            workbench / f"{prefix}ResolutionReview.png", recipe["regions"])
    if any(value < recipe["budgets"]["contrast_min"]
           for resolution in contrast.values() for value in resolution.values()):
        raise RuntimeError(f"Trim readability below budget: {contrast}")

    assets = []
    total_bytes = 0
    for map_name, filename in names.items():
        source = workbench / filename
        total_bytes += source.stat().st_size
        assets.append({
            "id": map_name,
            "generated_path": source.relative_to(root).as_posix(),
            "path": (root / recipe["outputs"]["published"] / filename).relative_to(root).as_posix(),
            "sha256": sha256(source),
            "canonical_sha256": canonical[map_name],
            "bytes": source.stat().st_size,
            "resolution": [recipe["resolution"], recipe["resolution"]],
        })
    if total_bytes > recipe["budgets"]["total_bytes_max"]:
        raise RuntimeError(f"Texture budget exceeded {total_bytes}")
    report = {
        "schema": 1,
        "id": recipe["id"],
        "status": "generated_validated_pending_publication",
        "seed": recipe["seed"],
        "resolution": recipe["resolution"],
        "maps": list(names),
        "total_bytes": total_bytes,
        "budget_bytes": recipe["budgets"]["total_bytes_max"],
        "contrast_by_resolution": contrast,
        "regions": [region["id"] for region in recipe["regions"]],
        "review": (workbench / f"{prefix}ResolutionReview.png").relative_to(root).as_posix(),
        "unity_launched": False,
    }
    report_path = root / recipe["outputs"]["report"]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest = {
        "schema": 1,
        "id": recipe["id"],
        "status": "generated_pending_explicit_publication",
        "status_after_publication": "published_pending_unity_material_validation",
        "recipe": Path(args.recipe).as_posix(),
        "graph": "AssetFactory/Graphs/citylab_trim_pbr_graph.json",
        "unity_launched": False,
        "gates": {
            "maps_generated": True,
            "resolution_review": True,
            "determinism": False,
            "unity_material_import": False,
            "building_application_review": False,
        },
        "assets": assets,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    if args.verify_determinism:
        current_hashes = {asset["id"]: asset["canonical_sha256"] for asset in assets}
        if previous_hashes is None or previous_hashes != current_hashes:
            raise RuntimeError("PBR trim determinism verification failed")
        manifest["gates"]["determinism"] = True
    temporary = manifest_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(manifest_path)
    print(
        "CITYLAB_PBR_TRIM_OK "
        f"maps={len(assets)} resolution={recipe['resolution']} bytes={total_bytes} "
        f"reviews=512,256,128 determinism={str(manifest['gates']['determinism']).lower()} "
        "unity_launched=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
