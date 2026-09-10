"""Validate and publish generated character FBXs into the CityLab host boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--catalog", default="AssetFactory/Catalogs/character_factory.json")
    parser.add_argument("--publish", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = arguments()
    root = Path(args.project_root).resolve()
    catalog = json.loads((root / args.catalog).read_text(encoding="utf-8"))
    report_dir = root / catalog["outputs"]["reports"]
    reports = [json.loads(path.read_text(encoding="utf-8"))
               for path in sorted(report_dir.glob("*.json"))]
    bodies = [item for item in reports if item["kind"] == "body"]
    roles = [item for item in reports if item["kind"] == "role"]
    expected_bodies = len(catalog["body_bases"]) * len(catalog["morphologies"])
    expected_roles = len(catalog["role_capsules"])
    if len(bodies) != expected_bodies or len(roles) != expected_roles:
        raise RuntimeError(
            f"Character matrix incomplete bodies={len(bodies)}/{expected_bodies} "
            f"roles={len(roles)}/{expected_roles}"
        )
    if len({item["id"] for item in reports}) != len(reports):
        raise RuntimeError("Duplicate character report id")
    if len({item["canonical_sha256"] for item in reports}) != len(reports):
        raise RuntimeError("Duplicate canonical character geometry")

    body_budget = catalog["lod"]["body_triangles_max"]
    role_budget = catalog["lod"]["role_triangles_max"]
    manifest_assets = []
    for report in reports:
        source = root / report["fbx"]
        if not source.is_file() or sha256(source) != report["fbx_sha256"]:
            raise RuntimeError(f"Generated FBX hash mismatch: {report['id']}")
        if report["bone_count"] != catalog["rig"]["expected_deform_bones"]:
            raise RuntimeError(f"Rig mismatch: {report['id']}")
        if len(report["lod_triangles"]) != 3 or len(report["lod_mesh_counts"]) != 3:
            raise RuntimeError(f"LOD contract mismatch: {report['id']}")
        budgets = body_budget if report["kind"] == "body" else role_budget
        if any(actual > maximum for actual, maximum in zip(report["lod_triangles"], budgets)):
            raise RuntimeError(f"LOD budget exceeded: {report['id']}")

        folder = "Bodies" if report["kind"] == "body" else "Roles"
        destination = root / catalog["outputs"]["published"] / folder / source.name
        if args.publish:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        published_hash = sha256(destination) if args.publish else report["fbx_sha256"]
        if published_hash != report["fbx_sha256"]:
            raise RuntimeError(f"Published FBX hash mismatch: {report['id']}")
        manifest_assets.append({
            "id": report["id"],
            "kind": report["kind"],
            "base": report["base"]["id"],
            "morphology": report["morphology"]["id"],
            "role": report["role"]["id"] if report["role"] else None,
            "bone_count": report["bone_count"],
            "lod_triangles": report["lod_triangles"],
            "canonical_sha256": report["canonical_sha256"],
            "fbx_sha256": published_hash,
            "generated_path": report["fbx"],
            "path": destination.relative_to(root).as_posix(),
            "preview": report["preview"],
        })

    manifest = {
        "schema": 1,
        "id": catalog["id"],
        "status": "published_pending_unity_humanoid_validation" if args.publish else "validated_dry_run",
        "source": catalog["source"],
        "contract": {
            "body_bases": len(catalog["body_bases"]),
            "morphologies": len(catalog["morphologies"]),
            "body_assets": len(bodies),
            "role_capsules": len(roles),
            "lod_levels": 3,
            "bones": catalog["rig"]["expected_deform_bones"],
        },
        "gates": {
            "blender_fbx_validation": True,
            "unity_launched": False,
            "unity_humanoid_import": False,
            "animation_smoke_test": False,
            "city_visual_library_assignment": False,
        },
        "assets": manifest_assets,
    }
    if args.publish:
        manifest_path = root / "AssetFactory/Manifests/character_factory.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = manifest_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temporary.replace(manifest_path)
    print(
        "CITYLAB_CHARACTER_FACTORY_OK "
        f"bodies={len(bodies)} roles={len(roles)} publish={str(args.publish).lower()} "
        "unity_launched=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
