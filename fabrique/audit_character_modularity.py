"""Audite hors Unity la couverture modulaire du pack de personnages CityLab."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


PATTERNS = {
    "hair": re.compile(r"^Hair Type \d+ Color \d+ Part\.fbx$", re.I),
    "facial_hair": re.compile(r"^Face Hair Type \d+ Color \d+ Part\.fbx$", re.I),
    "eyes": re.compile(r"^Eyes Type \d+ Color \d+ Part\.fbx$", re.I),
    "eyebrows": re.compile(r"^Eyebrow Type \d+ Color \d+ Part\.fbx$", re.I),
    "noses": re.compile(r"^Nose Type \d+ Part\.fbx$", re.I),
    "ears": re.compile(r"^Ears Type \d+ Part\.fbx$", re.I),
    "chest": re.compile(r"^Chest Armor Type \d+ Color \d+ Part\.fbx$", re.I),
    "arms": re.compile(r"^Arm Armor Type \d+ Color \d+ Part\.fbx$", re.I),
    "legs": re.compile(r"^Legs Armor Type \d+ Color \d+ Part\.fbx$", re.I),
    "feet": re.compile(r"^Feet Armor Type \d+ Color \d+ Part\.fbx$", re.I),
    "belt": re.compile(r"^Belt Armor Type \d+ Color \d+ Part\.fbx$", re.I),
    "head_armor": re.compile(r"^Head Armor Type \d+ Color \d+ Part\.fbx$", re.I),
}


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--catalog", type=Path, default=Path("AssetFactory/Catalogs/character_population.json"))
    return parser.parse_args()


def main() -> int:
    args = arguments()
    root = args.project_root.resolve()
    catalog_path = args.catalog if args.catalog.is_absolute() else root / args.catalog
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    source = root / catalog["source_root"]
    files = sorted(source.rglob("*.fbx"))
    counts = Counter()
    for path in files:
        for category, pattern in PATTERNS.items():
            if pattern.match(path.name):
                counts[category] += 1
                break
    full_bodies = [path for path in files if "Modular Character" in path.name]
    base_body_count = len(full_bodies)
    curated_axes = {
        "genders": len(catalog["genders"]),
        "ages": len(catalog["ages"]),
        "morphologies": len(catalog["morphologies"]),
        "hair_styles": len(catalog["hair"]["styles"]),
        "hair_colors": len(catalog["hair"]["colors"]),
        "social_roles": len(catalog["social_roles"]),
    }
    theoretical = 1
    for value in curated_axes.values():
        theoretical *= value
    direct_requirements = {
        "hair": counts["hair"] >= 25,
        "facial_hair": counts["facial_hair"] >= 25,
        "faces": counts["eyes"] >= 25 and counts["eyebrows"] >= 25 and counts["noses"] >= 5,
        "outfit_sets": all(counts[key] >= 18 for key in ("chest", "arms", "legs", "feet", "belt", "head_armor")),
    }
    report = {
        "schema": 1,
        "id": catalog["id"],
        "status": "source_components_ready_morphology_generation_required",
        "source_fbx_count": len(files),
        "full_body_sources": [path.relative_to(root).as_posix() for path in full_bodies],
        "base_body_count": base_body_count,
        "component_counts": dict(sorted(counts.items())),
        "curated_axes": curated_axes,
        "theoretical_combinations_before_face_variation": theoretical,
        "direct_component_gates": direct_requirements,
        "gaps": [
            "Le pack fournit un rig/corps de base, pas des corps féminin, enfant et âgé validés séparément.",
            "Les morphologies doivent être générées par déformation du rig et contrôlées en animation.",
            "Les tenues sociales sont des compositions CityLab à créer à partir des pièces d'armure, pas des classes prêtes à l'emploi.",
            "Les armes, outils de métier, robes religieuses et vêtements usés demandent des accessoires ou adaptations supplémentaires."
        ],
        "unity_validation": "pending_no_unity_launch"
    }
    output = root / "AssetFactory/Reports/character_modularity.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    if not all(direct_requirements.values()):
        print("CITYLAB_CHARACTER_AUDIT_ERROR " + json.dumps(direct_requirements, sort_keys=True))
        return 1
    print(f"CITYLAB_CHARACTER_AUDIT_OK fbx={len(files)} body_sources={base_body_count} "
          f"hair={counts['hair']} outfits={counts['chest']} theoretical={theoretical} unity_launched=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
