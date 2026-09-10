#!/usr/bin/env python3
"""Point d'entree hors Unity de l'Asset Factory CityLab.

Cette premiere tranche ne transforme encore aucun asset. Elle etablit le contrat
de production : decouverte de Blender, inventaire immuable des sources Vendor et
empreintes reproductibles avant toute adaptation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SCHEMA_VERSION = 1
MODEL_EXTENSIONS = {".blend", ".dae", ".fbx", ".glb", ".gltf", ".obj"}
TEXTURE_EXTENSIONS = {
    ".bmp", ".exr", ".hdr", ".jpeg", ".jpg", ".png", ".psd", ".tga", ".tif", ".tiff"
}


class FactoryError(RuntimeError):
    """Erreur attendue et lisible de la Factory."""


@dataclass(frozen=True)
class FactoryPaths:
    project_root: Path
    config_path: Path


def default_paths() -> FactoryPaths:
    project_root = Path(__file__).resolve().parents[2]
    return FactoryPaths(project_root, project_root / "AssetFactory" / "config.json")


def load_config(paths: FactoryPaths) -> dict:
    if not paths.config_path.is_file():
        raise FactoryError(f"Configuration absente : {paths.config_path}")
    config = json.loads(paths.config_path.read_text(encoding="utf-8"))
    if config.get("schema") != SCHEMA_VERSION:
        raise FactoryError(
            f"Schema de configuration non supporte : {config.get('schema')!r} "
            f"(attendu {SCHEMA_VERSION})"
        )
    return config


def relative_posix(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_file_record(path: Path, project_root: Path) -> dict:
    return {
        "path": relative_posix(path, project_root),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def configured_source_map(config: dict) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for source in config.get("sources", []):
        rel = Path(source["path"]).as_posix().rstrip("/")
        if rel in result:
            raise FactoryError(f"Source dupliquee dans la configuration : {rel}")
        result[rel] = source
    return result


def source_directories(config: dict, project_root: Path) -> list[tuple[Path, dict | None]]:
    assets_dir = project_root / config.get("assets_root", "Assets")
    if not assets_dir.is_dir():
        raise FactoryError(f"Dossier Assets absent : {assets_dir}")

    registered = configured_source_map(config)
    ignored_names = set(config.get("ignored_asset_roots", []))
    found: dict[str, tuple[Path, dict | None]] = {}

    for rel, metadata in registered.items():
        candidate = project_root / rel
        if not candidate.is_dir():
            raise FactoryError(f"Source enregistree absente : {rel}")
        found[rel] = (candidate, metadata)

    if config.get("discover_unregistered_asset_roots", True):
        for child in sorted(assets_dir.iterdir(), key=lambda item: item.name.casefold()):
            if not child.is_dir() or child.name in ignored_names:
                continue
            rel = relative_posix(child, project_root)
            found.setdefault(rel, (child, None))

    return [found[key] for key in sorted(found, key=str.casefold)]


def iter_candidate_files(source_dir: Path) -> Iterable[Path]:
    for path in source_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() != ".meta":
            yield path


def build_source_record(
    source_dir: Path,
    metadata: dict | None,
    project_root: Path,
) -> dict:
    models: list[dict] = []
    textures: list[dict] = []
    counters = {"files": 0, "prefabs": 0, "materials": 0, "unity_packages": 0}

    for path in sorted(iter_candidate_files(source_dir), key=lambda item: item.as_posix().casefold()):
        counters["files"] += 1
        extension = path.suffix.lower()
        if extension in MODEL_EXTENSIONS:
            models.append(stable_file_record(path, project_root))
        elif extension in TEXTURE_EXTENSIONS:
            textures.append(stable_file_record(path, project_root))
        elif extension == ".prefab":
            counters["prefabs"] += 1
        elif extension == ".mat":
            counters["materials"] += 1
        elif extension == ".unitypackage":
            counters["unity_packages"] += 1

    registered = metadata is not None
    provenance = (metadata or {}).get("provenance", {})
    warnings: list[str] = []
    if not registered:
        warnings.append("source_non_enregistree")
    if not provenance.get("store_url"):
        warnings.append("url_store_manquante")
    if provenance.get("license_status") != "verified":
        warnings.append("licence_a_verifier")
    if not models:
        warnings.append("aucun_modele_importable_par_blender")

    return {
        "id": (metadata or {}).get("id", re.sub(r"[^a-z0-9]+", "_", source_dir.name.lower()).strip("_")),
        "path": relative_posix(source_dir, project_root),
        "registered": registered,
        "provenance": provenance,
        "counts": {
            **counters,
            "model_candidates": len(models),
            "texture_candidates": len(textures),
        },
        "models": models,
        "textures": textures,
        "warnings": warnings,
    }


def build_inventory(config: dict, project_root: Path) -> dict:
    sources = [
        build_source_record(source_dir, metadata, project_root)
        for source_dir, metadata in source_directories(config, project_root)
    ]
    return {
        "schema": SCHEMA_VERSION,
        "generator": "Tools/AssetFactory/citylab_factory.py",
        "policy": {
            "sources_immutable": True,
            "unity_required": False,
            "adapted_output_root": config["adapted_output_root"],
        },
        "summary": {
            "sources": len(sources),
            "registered_sources": sum(1 for source in sources if source["registered"]),
            "model_candidates": sum(source["counts"]["model_candidates"] for source in sources),
            "texture_candidates": sum(source["counts"]["texture_candidates"] for source in sources),
            "sources_requiring_provenance_review": sum(
                1 for source in sources if source["warnings"]
            ),
        },
        "sources": sources,
    }


def discover_unregistered_sources(config: dict, project_root: Path) -> list[dict]:
    """Return stable summaries for new top-level Asset Store folders."""
    candidates = []
    for source_dir, metadata in source_directories(config, project_root):
        if metadata is not None:
            continue
        record = build_source_record(source_dir, None, project_root)
        candidates.append({
            "id": record["id"],
            "path": record["path"],
            "model_candidates": record["counts"]["model_candidates"],
            "texture_candidates": record["counts"]["texture_candidates"],
            "warnings": record["warnings"],
        })
    return candidates


def inventory_output_path(config: dict, project_root: Path) -> Path:
    return project_root / config.get(
        "inventory_output", "AssetFactory/Reports/source_inventory.json"
    )


def render_json(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n"


def scan(config: dict, project_root: Path, check: bool) -> int:
    output = inventory_output_path(config, project_root)
    rendered = render_json(build_inventory(config, project_root))
    if check:
        current = output.read_text(encoding="utf-8") if output.is_file() else ""
        if current != rendered:
            print(f"ASSET_FACTORY_INVENTORY_STALE path={relative_posix(output, project_root)}")
            return 1
        print(f"ASSET_FACTORY_INVENTORY_OK path={relative_posix(output, project_root)}")
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8", newline="\n")
    payload = json.loads(rendered)
    summary = payload["summary"]
    print(
        "ASSET_FACTORY_SCAN_OK "
        f"sources={summary['sources']} models={summary['model_candidates']} "
        f"textures={summary['texture_candidates']} "
        f"review={summary['sources_requiring_provenance_review']} "
        f"output={relative_posix(output, project_root)}"
    )
    return 0


def _ordered_range(value: object) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value)
        and value[0] <= value[1]
    )


def _weighted_choices(value: object) -> bool:
    if not isinstance(value, list) or not value:
        return False
    identifiers: set[str] = set()
    for entry in value:
        if not isinstance(entry, dict):
            return False
        identifier, weight = entry.get("id"), entry.get("weight")
        if not isinstance(identifier, str) or not identifier or identifier in identifiers:
            return False
        identifiers.add(identifier)
        if not isinstance(weight, (int, float)) or isinstance(weight, bool) or weight <= 0:
            return False
    return True


# Une teinte de palette multiplie l'albedo de l'atlas. En dessous de ce
# niveau sur son canal le plus clair, elle eteint la carte au lieu de la
# colorer.
MIN_TINT_CHANNEL = 0x60


def validate_style(style: dict) -> list[str]:
    """Verifier un style architectural hors Blender et hors Unity."""
    errors: list[str] = []
    if style.get("schema") != SCHEMA_VERSION:
        errors.append("schema_invalide")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", style.get("id", "")):
        errors.append("id_invalide")

    for path, node in (
        ("footprint.dimension_jitter", style.get("footprint", {}).get("dimension_jitter")),
        ("wall.height_jitter", style.get("wall", {}).get("height_jitter")),
        ("foundation.height_m", style.get("foundation", {}).get("height_m")),
        ("roof.pitch_deg", style.get("roof", {}).get("pitch_deg")),
        ("roof.overhang_m", style.get("roof", {}).get("overhang_m")),
        ("opening.reveal_depth_m", style.get("opening", {}).get("reveal_depth_m")),
    ):
        if not _ordered_range(node):
            errors.append(f"plage_invalide:{path}")

    pitch = style.get("roof", {}).get("pitch_deg")
    if _ordered_range(pitch) and not (0.0 < pitch[0] and pitch[1] < 90.0):
        errors.append("pente_toit_hors_bornes")

    for path, node in (
        ("footprint.forms", style.get("footprint", {}).get("forms")),
        ("levels.forms", style.get("levels", {}).get("forms")),
        ("roof.forms", style.get("roof", {}).get("forms")),
        ("roof.ridge_axis", style.get("roof", {}).get("ridge_axis")),
    ):
        if not _weighted_choices(node):
            errors.append(f"choix_pondere_invalide:{path}")

    trim = style.get("trim", {})
    rects = trim.get("rects", {})
    if not isinstance(rects, dict) or not rects:
        errors.append("bandes_trim_absentes")
        rects = {}
    bands: list[tuple[float, float, str]] = []
    for name, rect in rects.items():
        u, v = (rect or {}).get("u"), (rect or {}).get("v")
        if not _ordered_range(u) or not _ordered_range(v):
            errors.append(f"bande_trim_invalide:{name}")
            continue
        if not (0.0 <= u[0] and u[1] <= 1.0 and 0.0 <= v[0] and v[1] <= 1.0):
            errors.append(f"bande_trim_hors_unite:{name}")
            continue
        bands.append((float(v[0]), float(v[1]), name))
    bands.sort()
    for (_, previous_end, previous_name), (start, _, name) in zip(bands, bands[1:]):
        if start < previous_end - 0.000001:
            errors.append(f"bandes_trim_superposees:{previous_name}+{name}")

    for system, mapping in (trim.get("wall_system_map") or {}).items():
        for key in ("base", "body"):
            if (mapping or {}).get(key) not in rects:
                errors.append(f"mur_sans_bande:{system}.{key}")
    for system, band in (trim.get("roof_system_map") or {}).items():
        if band not in rects:
            errors.append(f"toit_sans_bande:{system}")

    budget = style.get("budget", {})
    classes = budget.get("classes", {})
    if not isinstance(classes, dict) or not classes:
        errors.append("classes_budget_absentes")
        classes = {}
    for name, entry in classes.items():
        lod = (entry or {}).get("lod")
        if (not isinstance(lod, list) or len(lod) != 3
                or not all(isinstance(item, int) and not isinstance(item, bool) and item > 0 for item in lod)):
            errors.append(f"budget_lod_invalide:{name}")
        elif not lod[0] > lod[1] > lod[2]:
            errors.append(f"budget_lod_non_decroissant:{name}")
    for function, class_name in (budget.get("function_class") or {}).items():
        if class_name not in classes:
            errors.append(f"fonction_sans_classe:{function}")

    if style.get("lod", {}).get("policy") != "element_removal":
        errors.append("politique_lod_invalide")
    ratio = style.get("lod", {}).get("lod1", {}).get("decimate_curved_min_ratio")
    if not isinstance(ratio, (int, float)) or isinstance(ratio, bool) or not 0.0 < ratio <= 1.0:
        errors.append("ratio_decimation_invalide")

    gate = style.get("silhouette_gate", {})
    if gate.get("camera") != "rts":
        errors.append("camera_porte_silhouette_invalide")
    for key in ("max_iou_same_family", "max_iou_cross_function"):
        value = gate.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0.0 < value <= 1.0:
            errors.append(f"seuil_iou_invalide:{key}")

    errors.extend(_validate_scheme(style, rects))
    errors.extend(_validate_finish(style, rects))

    palettes = style.get("palettes", [])
    if not isinstance(palettes, list) or len(palettes) < 3:
        errors.append("palettes_insuffisantes")
    else:
        identifiers: set[str] = set()
        for index, palette in enumerate(palettes):
            identifier = (palette or {}).get("id", "")
            if not re.fullmatch(r"[a-z0-9]+", identifier) or identifier in identifiers:
                errors.append(f"palette_{index}_id_invalide")
            identifiers.add(identifier)
            for key in ("wood", "wood_highlight", "roof", "roof_accent", "plaster"):
                if not re.fullmatch(r"#[0-9a-fA-F]{6}", (palette or {}).get(key, "")):
                    errors.append(f"palette_{index}_{key}_invalide")
                    continue
                # La palette multiplie l'albedo de l'atlas : c'est une teinte,
                # pas une couleur de remplacement. Une teinte sombre rendrait du
                # noir des que la carte arrive -- c'est exactement ce que
                # faisaient les valeurs d'avant le lot 003 (#120702 et voisines).
                channels = [int(palette[key][index_c:index_c + 2], 16)
                            for index_c in (1, 3, 5)]
                if max(channels) < MIN_TINT_CHANNEL:
                    errors.append(f"palette_{index}_{key}_trop_sombre")
    return errors


def _validate_scheme(style: dict, rects: dict) -> list[str]:
    """Un schema de construction doit nommer un vocabulaire qui existe."""
    del rects
    errors: list[str] = []
    scheme = style.get("scheme")
    if not isinstance(scheme, dict):
        errors.append("scheme_absent")
        return errors

    ranks = scheme.get("ranks")
    if not isinstance(ranks, list) or not ranks:
        errors.append("scheme_rangs_absents")
        ranks = []
    forms = scheme.get("forms")
    if not _weighted_choices(forms):
        errors.append("choix_pondere_invalide:scheme.forms")
        return errors

    levels = {str(form.get("id")) for form in (style.get("levels", {}).get("forms") or [])}
    sub_vocabularies = {
        "base": scheme.get("base") or {},
        "roof_composition": scheme.get("roof_composition") or {},
        "edge_trim": scheme.get("edge_trim") or {},
    }
    appendages = scheme.get("appendage") or {}

    seen: set[str] = set()
    for form in forms:
        identifier = str(form.get("id"))
        if identifier in seen:
            errors.append(f"scheme_duplique:{identifier}")
        seen.add(identifier)
        if form.get("rank") not in ranks:
            errors.append(f"scheme_rang_inconnu:{identifier}")
        if form.get("levels") not in levels:
            errors.append(f"scheme_niveaux_inconnus:{identifier}")
        for key, vocabulary in sub_vocabularies.items():
            if form.get(key) not in vocabulary:
                errors.append(f"scheme_{key}_inconnu:{identifier}")
        if form.get("jetty") not in (scheme.get("jetty", {}).get("faces") or {}):
            errors.append(f"scheme_encorbellement_inconnu:{identifier}")
        pitch = form.get("pitch_deg")
        if pitch is not None and not _ordered_range(pitch):
            errors.append(f"scheme_pente_invalide:{identifier}")
        declared = form.get("appendages")
        if not isinstance(declared, list):
            errors.append(f"scheme_volumes_invalides:{identifier}")
            continue
        for appendage in declared:
            if appendage not in appendages:
                errors.append(f"scheme_volume_inconnu:{identifier}.{appendage}")

    # Trois variantes doivent recevoir trois schemas distincts : c'est la porte
    # C-5. Un rang qui n'offre pas assez de schemas la rend inatteignable.
    for rank in ranks:
        available = [form for form in forms if form.get("rank") == rank]
        if not available:
            errors.append(f"scheme_rang_vide:{rank}")
    return errors


def _validate_finish(style: dict, rects: dict) -> list[str]:
    """Une finition doit nommer des bandes que l'atlas porte reellement."""
    errors: list[str] = []
    finish = style.get("finish")
    if not isinstance(finish, dict):
        errors.append("finish_absent")
        return errors
    forms = finish.get("forms")
    if not _weighted_choices(forms):
        errors.append("choix_pondere_invalide:finish.forms")
        return errors

    trim = style.get("trim", {})
    values = trim.get("band_value") or {}
    minimum = float(trim.get("min_finish_contrast", 0.0))
    for band in rects:
        if band not in values:
            errors.append(f"bande_sans_valeur:{band}")

    identifiers: set[str] = set()
    for form in forms:
        identifier = str(form.get("id"))
        identifiers.add(identifier)
        for key in ("upper", "lower"):
            if form.get(key) not in rects:
                errors.append(f"finition_sans_bande:{identifier}.{key}")
        if form.get("monolithic"):
            continue
        upper, lower = values.get(form.get("upper")), values.get(form.get("lower"))
        if upper is None or lower is None:
            continue
        # Deux valeurs voisines l'une sur l'autre ne montrent aucun empilement :
        # mesure a l'appui, dark_frame donnait 0,023 d'ecart avec sa base.
        if abs(float(upper) - float(lower)) < minimum:
            errors.append(f"finition_sans_contraste:{identifier}:"
                          f"{abs(float(upper) - float(lower)):.3f}")

    for system, mapping in (style.get("trim", {}).get("wall_system_map") or {}).items():
        declared = (mapping or {}).get("finishes")
        if declared is None:
            continue
        if not isinstance(declared, list) or not declared:
            errors.append(f"mur_finitions_invalides:{system}")
            continue
        for name in declared:
            if name not in identifiers:
                errors.append(f"mur_finition_inconnue:{system}.{name}")
    return errors


def validate_style_against_atlas(style: dict, texture_recipe: dict) -> list[str]:
    """Refuser un style qui reclame une bande que l'atlas ne produit pas."""
    errors: list[str] = []
    trim = style.get("trim", {})
    if texture_recipe.get("id") != "texture_" + trim.get("atlas", ""):
        errors.append("atlas_non_concordant")
        return errors
    regions = {region["id"]: region for region in texture_recipe.get("regions", [])}
    for name, rect in (trim.get("rects") or {}).items():
        region = regions.get(name)
        if region is None:
            errors.append(f"bande_absente_de_atlas:{name}")
            continue
        v = (rect or {}).get("v")
        if not _ordered_range(v):
            continue
        if abs(v[0] - region["v_min"]) > 0.0001 or abs(v[1] - region["v_max"]) > 0.0001:
            errors.append(f"bande_decalee:{name}")
    return errors


def validate_style_against_catalog(style: dict, catalog: dict) -> list[str]:
    """Refuser un style qui laisse une famille du catalogue sans matiere ni budget."""
    errors: list[str] = []
    trim = style.get("trim", {})
    wall_map = trim.get("wall_system_map") or {}
    roof_map = trim.get("roof_system_map") or {}
    function_class = style.get("budget", {}).get("function_class") or {}
    scheme_forms = (style.get("scheme") or {}).get("forms") or []
    known_ranks = set((style.get("scheme") or {}).get("ranks") or [])
    variant_count = max(1, len(catalog.get("variants") or []))
    for family in catalog.get("families", []):
        identifier = family.get("id", "?")
        if family.get("wall_system") not in wall_map:
            errors.append(f"mur_non_couvert:{identifier}")
        if family.get("roof_system") not in roof_map:
            errors.append(f"toit_non_couvert:{identifier}")
        if family.get("function") not in function_class:
            errors.append(f"fonction_non_budgetee:{identifier}")

        ranks = family.get("scheme_ranks")
        if not isinstance(ranks, list) or not ranks:
            errors.append(f"rangs_de_schema_absents:{identifier}")
            continue
        unknown = [rank for rank in ranks if rank not in known_ranks]
        if unknown:
            errors.append(f"rang_de_schema_inconnu:{identifier}.{','.join(sorted(unknown))}")
            continue
        # Chaque variante d'une famille doit pouvoir recevoir un schema
        # distinct : c'est la porte C-5, et une famille qui n'en atteint pas
        # assez la rend inatteignable en silence.
        reachable = [form for form in scheme_forms if form.get("rank") in ranks]
        if len(reachable) < variant_count:
            errors.append(
                f"schemas_insuffisants:{identifier}:{len(reachable)}/{variant_count}")
    return errors


def check_styles(config: dict, project_root: Path, requested: Path | None) -> int:
    del config
    if requested:
        paths = [requested if requested.is_absolute() else project_root / requested]
    else:
        paths = sorted((project_root / "AssetFactory" / "Styles").glob("*.json"))
    if not paths:
        raise FactoryError("Aucun style JSON a verifier")

    catalog_path = project_root / "AssetFactory" / "Catalogs" / "building_pilot.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8")) if catalog_path.is_file() else {}

    failures = 0
    for path in paths:
        style = json.loads(path.read_text(encoding="utf-8"))
        errors = validate_style(style)
        recipe_path = (project_root / "AssetFactory" / "Recipes"
                       / f"texture_{style.get('trim', {}).get('atlas', '')}.json")
        if recipe_path.is_file():
            errors += validate_style_against_atlas(
                style, json.loads(recipe_path.read_text(encoding="utf-8")))
        else:
            errors.append("recette_atlas_absente")
        errors += validate_style_against_catalog(style, catalog)
        for system, mapping in (style.get("trim", {}).get("wall_system_map") or {}).items():
            debt = mapping.get("requires_atlas")
            if debt and not (project_root / "AssetFactory" / "Recipes"
                             / f"texture_{debt}.json").is_file():
                errors.append(f"dette_atlas_sans_recette:{system}")
        if errors:
            failures += 1
            print(f"ASSET_FACTORY_STYLE_ERROR path={relative_posix(path, project_root)} "
                  f"errors={','.join(errors)}")
        else:
            debts = sorted(
                system for system, mapping in (style["trim"]["wall_system_map"]).items()
                if "requires_atlas" in mapping
            )
            print(
                f"ASSET_FACTORY_STYLE_OK path={relative_posix(path, project_root)} "
                f"id={style['id']} bands={len(style['trim']['rects'])} "
                f"palettes={len(style['palettes'])} atlas_debt={','.join(debts) or 'none'} "
                "unity_launched=false"
            )
    return 1 if failures else 0


# Contrat de construction, version 1 : quatre phases fixes. La scierie publiee
# s'y conforme et n'en bouge pas.
CONSTRUCTION_V1_SCHEMA = "AssetFactory/Schemas/building_construction.schema.json"
CONSTRUCTION_V1_STAGES = ("foundation", "frame", "roof", "details")

# Version 2 : le decoupage devient une donnee. Le vocabulaire reste ferme et
# ordonne -- sans quoi « ossature » ne voudrait plus dire la meme chose d'un
# batiment a l'autre -- mais un batiment declare les etapes qu'il emploie.
CONSTRUCTION_V2_SCHEMA = "AssetFactory/Schemas/building_construction_v2.schema.json"
CONSTRUCTION_V2_STAGES = (
    "groundworks", "basecourse", "framing", "floors",
    "carpentry", "roofing", "joinery", "finishes",
)
CONSTRUCTION_V2_MIN_STAGES = 5


def validate_construction_contract(recipe: dict) -> list[str]:
    if recipe.get("category") != "building":
        return []
    errors: list[str] = []
    schema = recipe.get("construction_schema")
    construction = recipe.get("construction", {})
    stages = construction.get("stages", [])

    if schema == CONSTRUCTION_V2_SCHEMA:
        vocabulary = CONSTRUCTION_V2_STAGES
        contract = 2
    elif schema == CONSTRUCTION_V1_SCHEMA:
        vocabulary = CONSTRUCTION_V1_STAGES
        contract = 1
    else:
        errors.append("schema_construction_manquant")
        vocabulary = CONSTRUCTION_V1_STAGES
        contract = 1

    if construction.get("mode") != "cumulative_layers":
        errors.append("mode_construction_invalide")
    if contract == 2 and construction.get("contract") != 2:
        errors.append("version_contrat_absente")

    minimum = CONSTRUCTION_V2_MIN_STAGES if contract == 2 else len(vocabulary)
    if not (minimum <= len(stages) <= len(vocabulary)):
        errors.append("phases_construction_invalides")
    else:
        cursor = 0.0
        rank = 0
        # Les etapes suivent l'ordre du vocabulaire. Une etape absente est
        # absente : son rang ne se renumerote pas, parce que c'est le rang qui
        # nomme le nœud du FBX et que l'hote lit ce nom.
        for index, stage in enumerate(stages, start=1):
            identifier = stage.get("id")
            progress = stage.get("progress", [])
            if identifier not in vocabulary:
                errors.append(f"phase_{index}_hors_vocabulaire")
            else:
                order = vocabulary.index(identifier) + 1
                if order <= rank:
                    errors.append(f"phase_{index}_ordre_invalide")
                elif stage.get("order") != order:
                    errors.append(f"phase_{index}_rang_invalide")
                rank = order
            if (len(progress) != 2 or not all(isinstance(value, (int, float)) for value in progress)
                    or abs(progress[0] - cursor) > 0.000001 or progress[1] <= progress[0]):
                errors.append(f"phase_{index}_progression_invalide")
            else:
                cursor = float(progress[1])
            if not stage.get("required_categories"):
                errors.append(f"phase_{index}_materiaux_manquants")
        if abs(cursor - 1.0) > 0.000001:
            errors.append("progression_construction_incomplete")
        # En v2, `required_categories` nomme les categories de LOD que l'etape
        # porte, et une categorie appartient a une etape et a une seule : sinon
        # la meme geometrie serait exportee deux fois et l'union des etapes ne
        # vaudrait plus le batiment complet. En v1 le champ nommait des familles
        # de materiaux, que deux phases pouvaient partager -- la scierie publiee
        # emploie `structural_timber` a l'ossature et a la toiture.
        if contract == 2:
            seen: dict[str, int] = {}
            for index, stage in enumerate(stages, start=1):
                for category in stage.get("required_categories") or ():
                    if category in seen:
                        errors.append(f"categorie_partagee:{category}")
                    seen[category] = index

    variants = recipe.get("variants", [])
    if not isinstance(variants, list) or len(variants) < 3:
        errors.append("variantes_insuffisantes")
    else:
        identifiers: set[str] = set()
        for index, variant in enumerate(variants):
            identifier = variant.get("id", "")
            if not re.fullmatch(r"[a-z0-9]+", identifier) or identifier in identifiers:
                errors.append(f"variante_{index}_id_invalide")
            identifiers.add(identifier)
            if not isinstance(variant.get("seed_offset"), int):
                errors.append(f"variante_{index}_graine_invalide")
            palette = variant.get("palette", {})
            for key in ("wood", "wood_highlight", "roof", "roof_accent"):
                if not re.fullmatch(r"#[0-9a-fA-F]{6}", palette.get(key, "")):
                    errors.append(f"variante_{index}_{key}_invalide")
            if not isinstance(variant.get("chimney"), bool):
                errors.append(f"variante_{index}_cheminee_invalide")
    return errors


def validate_texture_recipe(recipe: dict, adapted_output_root: str) -> list[str]:
    errors: list[str] = []
    if recipe.get("schema") != SCHEMA_VERSION:
        errors.append("schema_invalide")
    if not re.fullmatch(r"texture_[a-z0-9]+(?:_[a-z0-9]+)*", recipe.get("id", "")):
        errors.append("id_invalide")
    if recipe.get("status") not in {"draft", "reviewed", "approved"}:
        errors.append("statut_invalide")
    if recipe.get("texture_schema") != "AssetFactory/Schemas/pbr_trim.schema.json":
        errors.append("schema_texture_manquant")
    if not isinstance(recipe.get("seed"), int):
        errors.append("graine_manquante")

    resolution = recipe.get("resolution")
    if (not isinstance(resolution, int) or resolution < 512 or resolution > 4096
            or resolution & (resolution - 1)):
        errors.append("resolution_invalide")

    required_maps = {"BaseColor", "Normal", "AO", "Roughness", "Metallic", "VariationMask"}
    maps = recipe.get("maps")
    if not isinstance(maps, list) or set(maps) != required_maps or len(maps) != len(required_maps):
        errors.append("cartes_pbr_invalides")

    regions = recipe.get("regions")
    if not isinstance(regions, list) or len(regions) < 3:
        errors.append("regions_insuffisantes")
    else:
        cursor = 0.0
        seen_ids: set[str] = set()
        for index, region in enumerate(regions):
            region_id = region.get("id")
            lower = region.get("v_min")
            upper = region.get("v_max")
            if not region_id or region_id in seen_ids:
                errors.append(f"region_{index}_id_invalide")
            seen_ids.add(region_id)
            if (not isinstance(lower, (int, float)) or not isinstance(upper, (int, float))
                    or abs(float(lower) - cursor) > 1e-5 or float(upper) <= float(lower)):
                errors.append(f"region_{index}_intervalle_invalide")
            else:
                cursor = float(upper)
        if abs(cursor - 1.0) > 1e-5:
            errors.append("regions_couverture_incomplete")

    outputs = recipe.get("outputs", {})
    output_prefix = Path(adapted_output_root).as_posix().rstrip("/") + "/"
    if not Path(outputs.get("published", "")).as_posix().startswith(output_prefix):
        errors.append("sortie_hors_adapted_factory")
    if not Path(outputs.get("workbench", "")).as_posix().startswith("AssetFactory/Workbench/"):
        errors.append("workbench_invalide")
    budgets = recipe.get("budgets", {})
    if not isinstance(budgets.get("total_bytes_max"), int) or budgets.get("total_bytes_max", 0) <= 0:
        errors.append("budget_octets_invalide")
    if not isinstance(budgets.get("contrast_min"), (int, float)) or budgets.get("contrast_min", -1) < 0:
        errors.append("budget_contraste_invalide")
    return errors


def validate_recipe(recipe: dict, inventory: dict, adapted_output_root: str) -> list[str]:
    if recipe.get("texture_schema") or str(recipe.get("id", "")).startswith("texture_"):
        return validate_texture_recipe(recipe, adapted_output_root)

    errors: list[str] = []
    recipe_id = recipe.get("id", "")
    if recipe.get("schema") != SCHEMA_VERSION:
        errors.append("schema_invalide")
    if not re.fullmatch(r"(?:building|prop|unit)_[a-z0-9]+(?:_[a-z0-9]+)*", recipe_id):
        errors.append("id_invalide")
    if not isinstance(recipe.get("seed"), int):
        errors.append("graine_manquante")
    if recipe.get("status") not in {"draft", "reviewed", "approved"}:
        errors.append("statut_invalide")
    errors.extend(validate_construction_contract(recipe))

    planned_output = recipe.get("planned_output", "")
    output_prefix = Path(adapted_output_root).as_posix().rstrip("/") + "/"
    if not Path(planned_output).as_posix().startswith(output_prefix):
        errors.append("sortie_hors_adapted_factory")

    indexed: dict[str, tuple[dict, dict]] = {}
    for source in inventory.get("sources", []):
        for model in source.get("models", []):
            indexed[model["path"]] = (source, model)

    inputs = recipe.get("inputs")
    if not isinstance(inputs, list) or not inputs:
        errors.append("entrees_manquantes")
        return errors

    seen_roles: set[str] = set()
    for index, component in enumerate(inputs):
        label = f"entree_{index}"
        role = component.get("role")
        if not role or role in seen_roles:
            errors.append(f"{label}_role_invalide")
        seen_roles.add(role)

        source_path = Path(component.get("path", "")).as_posix()
        indexed_record = indexed.get(source_path)
        if indexed_record is None:
            errors.append(f"{label}_source_absente_inventaire")
            continue
        source, model = indexed_record
        if not source.get("registered"):
            errors.append(f"{label}_source_non_enregistree")
        if source.get("provenance", {}).get("license_status") != "verified":
            errors.append(f"{label}_licence_non_verifiee")
        if component.get("sha256") != model.get("sha256"):
            errors.append(f"{label}_hash_incorrect")

    return errors


def check_recipes(config: dict, project_root: Path, requested: Path | None) -> int:
    inventory_path = inventory_output_path(config, project_root)
    if not inventory_path.is_file():
        raise FactoryError("Inventaire absent : executer la commande scan")
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))

    if requested:
        paths = [requested if requested.is_absolute() else project_root / requested]
    else:
        paths = sorted((project_root / "AssetFactory" / "Recipes").glob("*.json"))
    if not paths:
        raise FactoryError("Aucune recette JSON a verifier")

    failures = 0
    for path in paths:
        recipe = json.loads(path.read_text(encoding="utf-8"))
        errors = validate_recipe(recipe, inventory, config["adapted_output_root"])
        if errors:
            failures += 1
            print(f"ASSET_FACTORY_RECIPE_ERROR path={relative_posix(path, project_root)} errors={','.join(errors)}")
        else:
            component_count = len(recipe.get("inputs", recipe.get("maps", [])))
            print(
                f"ASSET_FACTORY_RECIPE_OK path={relative_posix(path, project_root)} "
                f"id={recipe['id']} components={component_count} "
                f"status={recipe.get('status', 'unknown')}"
            )
    return 1 if failures else 0


def validate_admission_profile(profile: dict, inventory: dict, config: dict) -> list[str]:
    errors: list[str] = []
    if profile.get("schema") != SCHEMA_VERSION:
        errors.append("schema_invalide")
    if not re.fullmatch(r"admission_[a-z0-9]+(?:_[a-z0-9]+)*", profile.get("id", "")):
        errors.append("id_invalide")
    if profile.get("status") != "approved":
        errors.append("statut_non_approuve")
    if profile.get("admission_schema") != "AssetFactory/Schemas/vendor_admission.schema.json":
        errors.append("schema_admission_manquant")

    source_spec = profile.get("source", {})
    source = next((entry for entry in inventory.get("sources", [])
                   if entry.get("id") == source_spec.get("id")), None)
    if source is None or source.get("path") != Path(source_spec.get("path", "")).as_posix():
        errors.append("source_absente_inventaire")
    elif not source.get("registered"):
        errors.append("source_non_enregistree")
    provenance = source_spec.get("provenance", {})
    required_provenance = ("kind", "store_url", "version", "acquired", "license", "license_status")
    for key in required_provenance:
        if not provenance.get(key):
            errors.append(f"provenance_{key}_manquante")
    if provenance.get("license_status") != "verified":
        errors.append("licence_non_verifiee")
    if source is not None:
        registered_provenance = source.get("provenance", {})
        for key in required_provenance:
            if provenance.get(key) != registered_provenance.get(key):
                errors.append(f"provenance_{key}_divergente")

    indexed = {
        model["path"]: model
        for inventory_source in inventory.get("sources", [])
        for model in inventory_source.get("models", [])
    }
    inputs = profile.get("inputs")
    if not isinstance(inputs, list) or not inputs:
        errors.append("entrees_manquantes")
    else:
        roles: set[str] = set()
        for index, component in enumerate(inputs):
            role = component.get("role")
            if not role or role in roles:
                errors.append(f"entree_{index}_role_invalide")
            roles.add(role)
            path = Path(component.get("path", "")).as_posix()
            model = indexed.get(path)
            if model is None:
                errors.append(f"entree_{index}_source_absente")
            elif component.get("sha256") != model.get("sha256"):
                errors.append(f"entree_{index}_hash_incorrect")
            if source is not None and not path.startswith(source["path"].rstrip("/") + "/"):
                errors.append(f"entree_{index}_hors_source")

    adaptation = profile.get("adaptation_profile", {})
    if adaptation.get("source_policy") != "immutable":
        errors.append("source_policy_non_immuable")
    if not isinstance(adaptation.get("metric_scale"), (int, float)) or adaptation.get("metric_scale", 0) <= 0:
        errors.append("echelle_metrique_invalide")
    if adaptation.get("up_axis") not in {"Y", "Z"}:
        errors.append("axe_vertical_invalide")
    if adaptation.get("forward_axis") not in {"X", "-X", "Y", "-Y", "Z", "-Z"}:
        errors.append("axe_avant_invalide")
    if not adaptation.get("operations"):
        errors.append("operations_manquantes")
    if not adaptation.get("material_strategy") or not adaptation.get("lod_strategy"):
        errors.append("strategie_adaptation_incomplete")
    planned_root = Path(adaptation.get("planned_output_root", "")).as_posix().rstrip("/")
    allowed_root = Path(config["adapted_output_root"]).as_posix().rstrip("/")
    if planned_root != allowed_root and not planned_root.startswith(allowed_root + "/"):
        errors.append("sortie_hors_adapted_factory")
    return sorted(set(errors))


def admission_profiles(project_root: Path, requested: Path | None) -> list[Path]:
    if requested:
        return [requested if requested.is_absolute() else project_root / requested]
    return sorted((project_root / "AssetFactory" / "AdmissionProfiles").glob("*.json"))


def check_admissions(config: dict, project_root: Path, requested: Path | None,
                     write_report: bool) -> int:
    inventory_path = inventory_output_path(config, project_root)
    if not inventory_path.is_file():
        raise FactoryError("Inventaire absent : executer la commande scan")
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    paths = admission_profiles(project_root, requested)
    if not paths:
        raise FactoryError("Aucun profil d'admission JSON a verifier")
    results = []
    failures = 0
    for path in paths:
        profile = json.loads(path.read_text(encoding="utf-8"))
        errors = validate_admission_profile(profile, inventory, config)
        results.append({
            "profile": relative_posix(path, project_root),
            "id": profile.get("id"),
            "source": profile.get("source", {}).get("id"),
            "inputs": len(profile.get("inputs", [])),
            "status": "passed" if not errors else "failed",
            "errors": errors,
        })
        if errors:
            failures += 1
            print(f"ASSET_FACTORY_ADMISSION_ERROR path={relative_posix(path, project_root)} errors={','.join(errors)}")
        else:
            print(f"ASSET_FACTORY_ADMISSION_OK path={relative_posix(path, project_root)} inputs={len(profile['inputs'])}")
    if write_report:
        output = project_root / "AssetFactory" / "Reports" / "vendor_admission.json"
        payload = {
            "schema": SCHEMA_VERSION,
            "generator": "Tools/AssetFactory/citylab_factory.py admission-check",
            "unity_launched": False,
            "profiles": results,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(".json.tmp")
        temporary.write_text(render_json(payload), encoding="utf-8", newline="\n")
        temporary.replace(output)
    return 1 if failures else 0


def publication_entries(manifest: dict) -> list[dict]:
    assets = manifest.get("assets")
    if not isinstance(assets, list) or not assets:
        raise FactoryError("Manifest sans liste assets publiable")
    return assets


def publish_from_manifest(config: dict, project_root: Path, manifest_path: Path,
                          publish: bool, republish: bool = False) -> int:
    """Publier un manifeste sous Adapted Factory.

    La publication est ecriture unique : un asset deja publie dont le hash
    differe est une collision, refusee. C'est ce qui empeche un ecrasement
    silencieux. Remplacer une version publiee reste possible, mais devient une
    decision explicite -- `--republish` -- et non un effet de bord.
    """
    path = manifest_path if manifest_path.is_absolute() else project_root / manifest_path
    manifest = json.loads(path.read_text(encoding="utf-8"))
    entries = publication_entries(manifest)
    adapted_root = Path(config["adapted_output_root"]).as_posix().rstrip("/") + "/"
    total_bytes = 0
    replaced = 0
    for index, entry in enumerate(entries):
        source_rel = Path(entry.get("generated_path", "")).as_posix()
        destination_rel = Path(entry.get("path", "")).as_posix()
        expected_hash = entry.get("fbx_sha256") or entry.get("sha256")
        if not source_rel.startswith("AssetFactory/Workbench/"):
            raise FactoryError(f"Publication {index}: source hors workbench")
        if not destination_rel.startswith(adapted_root):
            raise FactoryError(f"Publication {index}: destination hors Adapted Factory")
        source = project_root / source_rel
        destination = project_root / destination_rel
        if not source.is_file() or sha256_file(source) != expected_hash:
            raise FactoryError(f"Publication {index}: hash source incorrect")
        total_bytes += source.stat().st_size
        collision = destination.exists() and sha256_file(destination) != expected_hash
        if collision and not republish:
            raise FactoryError(f"Publication {index}: collision destination")
        if publish and collision:
            replaced += 1
            destination.unlink()
        if publish and not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_suffix(destination.suffix + ".tmp")
            shutil.copy2(source, temporary)
            if sha256_file(temporary) != expected_hash:
                temporary.unlink(missing_ok=True)
                raise FactoryError(f"Publication {index}: hash temporaire incorrect")
            temporary.replace(destination)
    if publish and manifest.get("status_after_publication"):
        manifest["status"] = manifest["status_after_publication"]
        manifest["publication"] = {
            "mode": "explicit_atomic_copy",
            "assets": len(entries),
            "bytes": total_bytes,
            "unity_launched": False,
        }
        temporary_manifest = path.with_suffix(path.suffix + ".tmp")
        temporary_manifest.write_text(render_json(manifest), encoding="utf-8", newline="\n")
        temporary_manifest.replace(path)
    print(
        "ASSET_FACTORY_PUBLICATION_OK "
        f"mode={'publish' if publish else 'dry-run'} assets={len(entries)} bytes={total_bytes} "
        f"atomic=true replaced={replaced} unity_launched=false"
    )
    return 0


def blender_candidates(config: dict, project_root: Path) -> Iterable[Path]:
    override = os.environ.get("CITYLAB_BLENDER")
    if override:
        yield Path(override)

    configured = config.get("blender", {}).get("executable")
    if configured:
        candidate = Path(configured)
        yield candidate if candidate.is_absolute() else project_root / candidate

    for pattern in config.get("blender", {}).get("windows_globs", []):
        pattern_path = Path(pattern)
        parent = pattern_path.parent
        if parent.is_dir():
            yield from sorted(parent.glob(pattern_path.name), reverse=True)


def find_blender(config: dict, project_root: Path) -> Path:
    for candidate in blender_candidates(config, project_root):
        if candidate.is_file():
            return candidate.resolve()
    raise FactoryError(
        "Blender introuvable. Installer Blender LTS ou definir CITYLAB_BLENDER."
    )


def blender_version(executable: Path) -> str:
    process = subprocess.run(
        [str(executable), "--version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if process.returncode != 0:
        raise FactoryError(f"Blender a retourne le code {process.returncode}")
    first_line = (process.stdout or "").splitlines()[0].strip()
    return first_line or "version inconnue"


def doctor(config: dict, project_root: Path, as_json: bool) -> int:
    blender = find_blender(config, project_root)
    payload = {
        "status": "ok",
        "unity_launched": False,
        "python": sys.version.split()[0],
        "blender": {"path": str(blender), "version": blender_version(blender)},
        "configured_sources": len(config.get("sources", [])),
        "adapted_output_root": config["adapted_output_root"],
    }
    if as_json:
        print(render_json(payload), end="")
    else:
        print(
            "ASSET_FACTORY_DOCTOR_OK "
            f"blender=\"{payload['blender']['version']}\" "
            f"python={payload['python']} unity_launched=false"
        )
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    defaults = default_paths()
    parser = argparse.ArgumentParser(description="Asset Factory CityLab (hors Unity)")
    parser.add_argument("--project-root", type=Path, default=defaults.project_root)
    parser.add_argument("--config", type=Path, default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser("doctor", help="Verifier Python et Blender")
    doctor_parser.add_argument("--json", action="store_true")

    scan_parser = subparsers.add_parser("scan", help="Inventorier les sources Vendor")
    scan_parser.add_argument("--check", action="store_true", help="Refuser un inventaire perime")

    recipe_parser = subparsers.add_parser("recipe-check", help="Verifier les recettes et leurs hashes")
    recipe_parser.add_argument("recipe", nargs="?", type=Path, help="Recette precise, sinon toutes")

    style_parser = subparsers.add_parser("style-check", help="Verifier les styles architecturaux")
    style_parser.add_argument("style", nargs="?", type=Path, help="Style precis, sinon tous")

    discovery_parser = subparsers.add_parser("admission-discover", help="Detecter les nouveaux dossiers Vendor")
    discovery_parser.add_argument("--json", action="store_true")

    admission_parser = subparsers.add_parser("admission-check", help="Verifier les profils d'admission")
    admission_parser.add_argument("profile", nargs="?", type=Path, help="Profil precis, sinon tous")
    admission_parser.add_argument("--write-report", action="store_true")

    publish_parser = subparsers.add_parser("publication-check", help="Simuler ou executer une copie atomique")
    publish_parser.add_argument("manifest", type=Path)
    publish_parser.add_argument("--publish", action="store_true")
    publish_parser.add_argument(
        "--republish", action="store_true",
        help="remplacer une version deja publiee ; sans lui une collision est refusee")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    project_root = args.project_root.resolve()
    config_path = args.config.resolve() if args.config else project_root / "AssetFactory" / "config.json"
    paths = FactoryPaths(project_root, config_path)
    try:
        config = load_config(paths)
        if args.command == "doctor":
            return doctor(config, project_root, args.json)
        if args.command == "scan":
            return scan(config, project_root, args.check)
        if args.command == "recipe-check":
            return check_recipes(config, project_root, args.recipe)
        if args.command == "style-check":
            return check_styles(config, project_root, args.style)
        if args.command == "admission-discover":
            candidates = discover_unregistered_sources(config, project_root)
            payload = {"schema": SCHEMA_VERSION, "unity_launched": False, "candidates": candidates}
            if args.json:
                print(render_json(payload), end="")
            else:
                print(f"ASSET_FACTORY_ADMISSION_DISCOVERY_OK candidates={len(candidates)} unity_launched=false")
            return 0
        if args.command == "admission-check":
            return check_admissions(config, project_root, args.profile, args.write_report)
        if args.command == "publication-check":
            return publish_from_manifest(config, project_root, args.manifest,
                                         args.publish, args.republish)
        raise FactoryError(f"Commande inconnue : {args.command}")
    except (FactoryError, json.JSONDecodeError, OSError, subprocess.SubprocessError) as error:
        print(f"ASSET_FACTORY_ERROR {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
