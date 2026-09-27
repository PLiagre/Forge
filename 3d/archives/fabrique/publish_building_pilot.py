"""Publie et manifeste le pilote de bâtiments sans lancer Unity."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def load_style(root: Path, style_id: str) -> dict:
    path = root / "AssetFactory" / "Styles" / f"{style_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def family_budget(style: dict, function: str) -> list[int]:
    """Le budget de triangles d'une famille, tel que le style le declare.

    La publication lisait `catalog.budgets.lod_triangles_max`, un plafond a plat
    de 60 000 / 30 000 / 12 000 ecrit apres coup. Le style, lui, declare
    4 000 / 1 800 / 600 par classe -- quinze fois moins. La porte de publication
    laissait donc passer les vingt et un batiments a 37 000-50 000 triangles qui
    ont ete refuses visuellement : elle ne contraignait rien.
    """
    budget = style["budget"]
    class_name = budget["function_class"][function]
    return [int(value) for value in budget["classes"][class_name]["lod"]]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--catalog", type=Path, default=Path("AssetFactory/Catalogs/building_pilot.json"))
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--only", action="append", default=[],
                        help="Ne traiter que ces familles. Sans cette option, "
                             "toutes celles du catalogue.")
    return parser.parse_args()


def construction_failure(metrics: dict, catalog: dict) -> str | None:
    """Verifier le contrat de construction d'un asset contre son catalogue.

    Le contrat v1 imposait quatre phases, et le nombre quatre etait ecrit ici
    comme ailleurs. En v2 le catalogue porte le vocabulaire ; l'asset declare
    les etapes qu'il emploie, dans l'ordre, sans en inventer.
    """
    if int(catalog.get("construction_contract", 1)) < 2:
        return (None if len(metrics.get("construction_phase_triangles", {})) == 4
                else "construction_phases")
    declared = list(catalog["construction_stages"])
    stages = (metrics.get("construction") or {}).get("stages")
    if not stages:
        return "construction_absente"
    if len(stages) < 5:
        return "construction_trop_peu_etapes"
    rank = 0
    for stage in stages:
        if stage["id"] not in declared:
            return "construction_hors_vocabulaire"
        order = declared.index(stage["id"]) + 1
        if order <= rank or stage.get("order") != order:
            return "construction_ordre"
        rank = order
        if stage["lod0"] <= 0:
            return "construction_etape_vide"
    total = metrics["triangles"]
    for lod in ("lod0", "lod1", "lod2"):
        if sum(stage[lod] for stage in stages) != total[lod]:
            return "construction_union_" + lod
    return None


def main() -> int:
    args = arguments()
    root = args.project_root.resolve()
    catalog_path = args.catalog if args.catalog.is_absolute() else root / args.catalog
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    target_root = root / "Assets/CityLabHost/Adapted/Factory/Models"
    target_root.mkdir(parents=True, exist_ok=True)
    style = load_style(root, catalog["style"])
    manifest = {
        "schema": 1,
        "id": catalog["id"],
        "status": "published_pending_unity_import_validation" if args.publish else "dry_run",
        "catalog": catalog_path.relative_to(root).as_posix(),
        "construction": {
            "contract": int(catalog.get("construction_contract", 1)),
            "schema": catalog["construction_schema"],
            "stages": catalog["construction_stages"],
            "lod_per_stage": 3,
        },
        "budget_source": f"AssetFactory/Styles/{catalog['style']}.json",
        "families": [],
        "gates": {"unity_launched": False}
    }
    failures: list[str] = []
    selection = set(args.only)
    # `--only` ne publie qu'une famille, mais le manifeste reste le registre de
    # tout le pilote : les familles non traitees gardent leur enregistrement
    # precedent au lieu de disparaitre.
    previous = {}
    output = root / "AssetFactory/Manifests/building_pilot.json"
    if selection and output.is_file():
        for record in json.loads(output.read_text(encoding="utf-8")).get("families", []):
            previous[record["id"]] = record
    for family in catalog["families"]:
        if selection and family["id"] not in selection:
            if family["id"] in previous:
                manifest["families"].append(previous[family["id"]])
            continue
        record = {
            "id": family["id"],
            "function": family["function"],
            "lod_triangles_max": family_budget(style, family["function"]),
            "wall_system": family["wall_system"],
            "roof_system": family["roof_system"],
            "identity_markers": family["identity_markers"],
            "variants": []
        }
        for variant in catalog["variants"]:
            asset_id = family["id"] + "_" + variant["id"]
            metrics_path = root / "AssetFactory/Reports" / f"{asset_id}_metrics.json"
            source = root / "AssetFactory/Workbench/Models" / f"{asset_id}.fbx"
            target = target_root / f"{asset_id}.fbx"
            if not metrics_path.is_file() or not source.is_file():
                failures.append(asset_id + ":outputs_missing")
                continue
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            triangles = [metrics["triangles"][key] for key in ("lod0", "lod1", "lod2")]
            budget = family_budget(style, family["function"])
            if any(value > maximum for value, maximum in zip(triangles, budget)):
                failures.append(asset_id + ":lod_budget")
            failure = construction_failure(metrics, catalog)
            if failure:
                failures.append(asset_id + ":" + failure)
            if args.publish:
                shutil.copy2(source, target)
            source_hash = sha256(source)
            published_hash = sha256(target) if target.is_file() else None
            if args.publish and source_hash != published_hash:
                failures.append(asset_id + ":published_hash")
            record["variants"].append({
                "id": variant["id"],
                "seed": metrics["seed"],
                "lod_triangles": triangles,
                "canonical_mesh_sha256": metrics["canonical_mesh_sha256"],
                "fbx_sha256": source_hash,
                "published_fbx": target.relative_to(root).as_posix() if args.publish else None
            })
        manifest["families"].append(record)
    manifest["gates"].update({
        "family_count": len(manifest["families"]),
        "variant_count": sum(len(family["variants"]) for family in manifest["families"]),
        "budgets_and_phases": "failed" if failures else "passed",
        "published_copy_hashes": "failed" if failures else ("passed" if args.publish else "not_run"),
        "unity_import": "pending_no_unity_launch"
    })
    manifest["failures"] = failures
    rendered = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(rendered, encoding="utf-8", newline="\n")
    temporary.replace(output)
    if failures:
        print("CITYLAB_BUILDING_PILOT_ERROR " + " ".join(failures))
        return 1
    print(f"CITYLAB_BUILDING_PILOT_OK families={len(manifest['families'])} "
          f"variants={manifest['gates']['variant_count']} publish={str(args.publish).lower()} "
          f"unity_launched=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
