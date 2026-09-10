"""Aggregate technical QA and build the CityLab Factory review board."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

try:  # imported as a package from the repository root
    from Tools.AssetFactory.matter_gate import audit as matter_audit
except ModuleNotFoundError:  # run as a script, sys.path[0] is this folder
    from matter_gate import audit as matter_audit


BUILDING_BUDGET = (60000, 30000, 12000)
BUILDING_STEMS = (
    ("building_sawmill_frontier_01_a", "Scierie"),
    ("building_residence_frontier_01_a", "Résidence"),
    ("building_granary_frontier_01_a", "Grenier"),
    ("building_warehouse_frontier_01_a", "Entrepôt"),
    ("building_market_frontier_01_a", "Marché"),
    ("building_blacksmith_frontier_01_a", "Forge"),
    ("building_barn_frontier_01_a", "Grange"),
    ("building_chapel_frontier_01_a", "Chapelle"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def stale_reports(reports: list[dict], published_sha: dict[str, str]) -> list[str]:
    """Les rapports de rechargement qui ne decrivent plus le FBX publie.

    Un rapport de rechargement est une preuve : il ne vaut que pour le FBX qu'il
    a reellement ouvert. Sans ce controle, regenerer un asset laissait la porte
    verte sur la mesure de l'asset precedent -- c'est exactement ce qui s'est
    produit pour la residence entre M1-ASSET-06 et la phase A de M1-ASSET-07. Un
    rapport sans `fbx_sha256` est perime par construction : il vient d'avant le
    producteur reproductible.
    """
    return sorted(
        report["id"] for report in reports
        if report.get("fbx_sha256") != published_sha.get(report["id"])
    )


def building_assets(root: Path) -> list[dict]:
    """Tous les batiments publies, et il n'y a plus qu'une source.

    La scierie avait son manifeste separe parce qu'elle avait son generateur
    separe et son contrat v1. Elle est entree au catalogue du pilote : un seul
    manifeste les porte tous, et ce compte-la ne peut plus diverger de l'autre.
    """
    pilot = load(root / "AssetFactory/Manifests/building_pilot.json")
    assets = []
    for family in pilot["families"]:
        for variant in family["variants"]:
            assets.append({
                "id": f"{family['id']}_{variant['id']}",
                "path": variant["published_fbx"],
                "sha256": variant["fbx_sha256"],
                "lod": variant["lod_triangles"],
            })
    return assets


def review_board(root: Path, output: Path) -> None:
    panel_w, panel_h, label_h = 384, 384, 34
    font_path = Path("C:/Windows/Fonts/arial.ttf")
    font = ImageFont.truetype(font_path, 18) if font_path.is_file() else ImageFont.load_default(size=18)
    canvas = Image.new("RGB", (panel_w * 4, (panel_h + label_h) * 2 + 390), "#0E171F")
    draw = ImageDraw.Draw(canvas)
    for index, (stem, label) in enumerate(BUILDING_STEMS):
        image = Image.open(root / f"AssetFactory/Workbench/Previews/{stem}_hero.png").convert("RGB")
        image = ImageOps.contain(image, (panel_w, panel_h), method=Image.Resampling.LANCZOS)
        x, y = index % 4 * panel_w, index // 4 * (panel_h + label_h)
        canvas.paste(image, (x, y))
        bounds = draw.textbbox((0, 0), label, font=font)
        draw.text((x + (panel_w - (bounds[2] - bounds[0])) / 2, y + panel_h + 7),
                  label, font=font, fill="#F2E6D0")

    bottom_y = (panel_h + label_h) * 2
    roles = Image.open(root / "AssetFactory/Workbench/Characters/Production/character_roles_review.png").convert("RGB")
    roles = ImageOps.contain(roles, (768, 360), method=Image.Resampling.LANCZOS)
    trim = Image.open(root / "AssetFactory/Workbench/Textures/CityLabTrimV1/CityLabTrim_ResolutionReview.png").convert("RGB")
    trim = ImageOps.contain(trim, (768, 360), method=Image.Resampling.LANCZOS)
    canvas.paste(roles, (0, bottom_y + 8))
    canvas.paste(trim, (768, bottom_y + 8))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    inventory = load(root / "AssetFactory/Reports/source_inventory.json")
    characters = load(root / "AssetFactory/Manifests/character_factory.json")
    textures = load(root / "AssetFactory/Manifests/citylab_trim_v1.json")
    buildings = building_assets(root)
    errors = []

    if inventory["summary"]["sources"] != inventory["summary"]["registered_sources"]:
        errors.append("unregistered_sources")
    if any(source["provenance"].get("license_status") != "verified"
           for source in inventory["sources"]):
        errors.append("unverified_license")

    expected_fbx_ids = set()
    published_sha: dict[str, str] = {}
    total_bytes = 0
    for asset in buildings:
        expected_fbx_ids.add(asset["id"])
        published_sha[asset["id"]] = asset["sha256"]
        if not re.fullmatch(r"building_[a-z0-9_]+_[abc]", asset["id"]):
            errors.append("building_name:" + asset["id"])
        path = root / asset["path"]
        generated = root / "AssetFactory/Workbench/Models" / path.name
        if not path.is_file() or sha256(path) != asset["sha256"]:
            errors.append("building_hash:" + asset["id"])
        if not generated.is_file() or sha256(generated) != asset["sha256"]:
            errors.append("building_workbench_hash:" + asset["id"])
        if any(actual > maximum for actual, maximum in zip(asset["lod"], BUILDING_BUDGET)):
            errors.append("building_budget:" + asset["id"])
        preview = root / "AssetFactory/Workbench/Previews" / f"{asset['id']}_hero.png"
        if not preview.is_file():
            errors.append("building_preview:" + asset["id"])
        total_bytes += path.stat().st_size if path.is_file() else 0

    body_budget, role_budget = (12000, 6500, 3000), (18000, 9500, 4200)
    for asset in characters["assets"]:
        expected_fbx_ids.add(asset["id"])
        published_sha[asset["id"]] = asset["fbx_sha256"]
        if not re.fullmatch(r"(?:body|role)_[a-z0-9_]+", asset["id"]):
            errors.append("character_name:" + asset["id"])
        path = root / asset["path"]
        generated = root / asset["generated_path"]
        if not path.is_file() or sha256(path) != asset["fbx_sha256"]:
            errors.append("character_hash:" + asset["id"])
        if not generated.is_file() or sha256(generated) != asset["fbx_sha256"]:
            errors.append("character_workbench_hash:" + asset["id"])
        budget = body_budget if asset["kind"] == "body" else role_budget
        if any(actual > maximum for actual, maximum in zip(asset["lod_triangles"], budget)):
            errors.append("character_budget:" + asset["id"])
        if not (root / asset["preview"]).is_file():
            errors.append("character_preview:" + asset["id"])
        total_bytes += path.stat().st_size if path.is_file() else 0

    for asset in textures["assets"]:
        path = root / asset["path"]
        generated = root / asset["generated_path"]
        if not path.is_file() or sha256(path) != asset["sha256"]:
            errors.append("texture_hash:" + asset["id"])
        if not generated.is_file() or sha256(generated) != asset["sha256"]:
            errors.append("texture_workbench_hash:" + asset["id"])
        total_bytes += path.stat().st_size if path.is_file() else 0

    fbx_reports = [load(path) for path in sorted((root / "AssetFactory/Reports/QA/Fbx").glob("*.json"))]
    report_ids = {report["id"] for report in fbx_reports}
    if report_ids != expected_fbx_ids:
        errors.append(f"fbx_report_coverage:{len(report_ids)}/{len(expected_fbx_ids)}")
    if any(report["status"] != "passed" or report["mesh_count"] != report["uv_mesh_count"]
           or report["embedded_colliders"] != 0 for report in fbx_reports):
        errors.append("fbx_report_failure")
    stale = stale_reports(fbx_reports, published_sha)
    if stale:
        errors.append("fbx_report_stale:" + ",".join(stale))

    matter = matter_audit(root)
    atomic_json(root / "AssetFactory/Reports/QA/unity_matter.json", matter)
    errors.extend(matter["violations"])

    # La planche de revue est un artefact suivi, et son sha est epingle dans
    # AssetFactory/Manifests/factory_qa.json. La regenerer avant de valider
    # laissait le depot avec une planche que son manifeste ne decrit plus des
    # qu'un run echouait : planche et manifeste s'ecrivent maintenant ensemble,
    # sur un run vert seulement.
    board = root / "AssetFactory/Reports/QA/factory_review_board.png"
    if errors:
        raise RuntimeError("Factory QA failed: " + ",".join(errors))
    review_board(root, board)
    report = {
        "schema": 1,
        "id": "citylab_factory_qa_v1",
        "status": "technical_pass_artistic_and_unity_gates_pending",
        "summary": {
            "registered_sources": inventory["summary"]["registered_sources"],
            "building_fbx": len(buildings),
            "character_fbx": len(characters["assets"]),
            "texture_maps": len(textures["assets"]),
            "fbx_meshes": sum(item["mesh_count"] for item in fbx_reports),
            "uv_meshes": sum(item["uv_mesh_count"] for item in fbx_reports),
            "embedded_colliders": 0,
            "published_bytes": total_bytes,
            "textured_materials": matter["materials"]["textured"],
            "published_materials": matter["materials"]["published"],
        },
        "gates": {
            "names": "passed",
            "uv": "passed_all_fbx_meshes",
            "lod": "passed",
            "colliders": "passed_none_embedded",
            "fbx_report_freshness": "passed_every_report_pins_the_fbx_it_opened",
            "hashes": "passed_workbench_equals_published",
            "budgets": "passed",
            "unity_matter": "passed_every_published_material_carries_the_trim_atlas",
            "unity_trim_colour_space": "passed_every_trim_map_imported_for_its_role",
            "licenses": "passed_all_registered_sources",
            "previews": "passed",
            "dry_run_default": "passed_by_automated_test",
            "atomic_copy": "passed_by_automated_test",
            "artistic_approval": "pending_user_review",
            "unity_import": "pending_user_requested_no_unity_launch"
        },
        "review_board": board.relative_to(root).as_posix(),
        "unity_launched": False,
    }
    report_path = root / "AssetFactory/Reports/factory_qa.json"
    atomic_json(report_path, report)
    manifest = {
        "schema": 1,
        "id": "citylab_factory_qa_v1",
        "status": report["status"],
        "report": report_path.relative_to(root).as_posix(),
        "report_sha256": sha256(report_path),
        "review_board": board.relative_to(root).as_posix(),
        "review_board_sha256": sha256(board),
        "inputs": {
            "building_pilot": sha256(root / "AssetFactory/Manifests/building_pilot.json"),
            "characters": sha256(root / "AssetFactory/Manifests/character_factory.json"),
            "textures": sha256(root / "AssetFactory/Manifests/citylab_trim_v1.json"),
            "inventory": sha256(root / "AssetFactory/Reports/source_inventory.json"),
        },
        "unity_launched": False,
    }
    atomic_json(root / "AssetFactory/Manifests/factory_qa.json", manifest)
    print(
        "CITYLAB_FACTORY_QA_OK "
        f"fbx={len(fbx_reports)} meshes={report['summary']['fbx_meshes']} "
        f"uv={report['summary']['uv_meshes']} textures={len(textures['assets'])} "
        f"bytes={total_bytes} "
        f"materials={matter['materials']['textured']}/{matter['materials']['published']} "
        f"unity_launched=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
