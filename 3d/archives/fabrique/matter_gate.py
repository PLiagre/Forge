"""Unity matter gate: prove the trim atlas actually reaches the published assets.

M1-ASSET-06 passed every technical gate and every Unity EditMode test, and was
still refused on sight. The reason was never checked by anything: the factory
textured with a procedural node that no exporter carries, so the published
materials arrived as flat colour. This module measures the last hop -- what the
Unity data in the repository actually says -- without launching Unity.

Two rules, both readable from the serialized assets:

M-1  a published factory material references at least one texture. A material
     whose every ``m_TexEnvs`` slot holds ``{fileID: 0}`` is a flat colour, which
     is exactly the symptom the lot exists to remove.
M-2  a published trim map is imported in the colour space its role requires.
     ``BaseColor`` is colour and stays sRGB; normal, AO, roughness, metallic and
     the variation mask are data and must be linear, and the normal map must be
     imported as a normal map so Unity unpacks it.

A map that arrives with the wrong colour space is lit wrong even when the mesh
carries it, so M-2 is part of the same question as M-1, not a separate polish.

Both rules are red on the assets M1-ASSET-06 published. That measured debt is
declared in ``AssetFactory/Manifests/unity_matter_debt.json`` -- as data, the way
``requires_atlas`` declares the atlas debt in the style -- and the gate refuses
any violation that is **not** in it. The list can only shrink: a newly published
flat material or a newly miscoloured map fails the gate immediately.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

DEBT_MANIFEST = "AssetFactory/Manifests/unity_matter_debt.json"
MATERIALS_DIR = "Assets/CityLabHost/Adapted/Factory/Materials"
TRIM_DIRS = (
    "Assets/CityLabHost/Adapted/Factory/Textures/CityLabTrimV1",
    "Assets/CityLabHost/Adapted/Factory/Textures/CityLabTrimV2",
    "Packages/com.victoria.citymode.assets/Runtime/Content/Common",
)

# Unity's class id for Texture2D references inside m_TexEnvs.
TEXTURE_FILE_ID = "2800000"
TEXTURE_TYPE_DEFAULT = 0
TEXTURE_TYPE_NORMAL_MAP = 1

# role -> (sRGBTexture, textureType) required for a correct import.
TRIM_MAP_IMPORT = {
    "BaseColor": (1, TEXTURE_TYPE_DEFAULT),
    "Normal": (0, TEXTURE_TYPE_NORMAL_MAP),
    "AO": (0, TEXTURE_TYPE_DEFAULT),
    "Roughness": (0, TEXTURE_TYPE_DEFAULT),
    "Metallic": (0, TEXTURE_TYPE_DEFAULT),
    "VariationMask": (0, TEXTURE_TYPE_DEFAULT),
}

_SLOT = re.compile(r"^\s{4}- (\w+):\s*$")
_TEXTURE = re.compile(r"^\s{8}m_Texture:\s*\{fileID:\s*(-?\d+)(?:,\s*guid:\s*([0-9a-f]{32}))?")
_META_GUID = re.compile(r"^guid:\s*([0-9a-f]{32})\s*$", re.MULTILINE)


def _role_of(filename: str) -> str:
    """"CityLabTrimV2_Normal.png.meta" -> "Normal".

    Le prefixe suit la version de l'atlas ; le role est ce qui suit le dernier
    souligne. Le deduire d'un prefixe fixe faisait manquer v2 entierement.
    """
    stem = filename[:-len(".png.meta")] if filename.endswith(".png.meta") else filename
    return stem.rsplit("_", 1)[-1]


def material_maps(path: Path) -> dict[str, str]:
    """Return {texture slot: guid} for every slot of a .mat that holds a texture.

    Slots left at ``{fileID: 0}`` are absent from the result: an empty dict means
    the material is a flat colour.
    """
    maps: dict[str, str] = {}
    slot = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = _SLOT.match(line)
        if match:
            slot = match.group(1)
            continue
        if slot is None:
            continue
        texture = _TEXTURE.match(line)
        if texture:
            if texture.group(1) == TEXTURE_FILE_ID and texture.group(2):
                maps[slot] = texture.group(2)
            slot = None
    return maps


def texture_import(meta: Path) -> dict[str, int]:
    """Read the two import settings that decide how a map is sampled."""
    text = meta.read_text(encoding="utf-8", errors="replace")
    srgb = re.search(r"^\s*sRGBTexture:\s*(\d+)", text, re.MULTILINE)
    kind = re.search(r"^\s*textureType:\s*(\d+)", text, re.MULTILINE)
    return {
        "sRGB": int(srgb.group(1)) if srgb else 1,
        "texture_type": int(kind.group(1)) if kind else TEXTURE_TYPE_DEFAULT,
    }


def trim_guids(root: Path) -> dict[str, str]:
    """Map every published trim map guid to its role (BaseColor, Normal, ...)."""
    guids: dict[str, str] = {}
    for folder in TRIM_DIRS:
        for meta in sorted((root / folder).glob("CityLabTrim*_*.png.meta")):
            found = _META_GUID.search(meta.read_text(encoding="utf-8", errors="replace"))
            if found:
                guids[found.group(1)] = _role_of(meta.name)
    return guids


def load_debt(root: Path) -> dict[str, list[str]]:
    """Read the declared, measured debt. A missing manifest declares none."""
    path = root / DEBT_MANIFEST
    if not path.is_file():
        return {"materials": [], "trim_maps": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "materials": list(payload.get("m1_materials_without_any_texture", [])),
        "trim_maps": list(payload.get("m2_trim_maps_in_the_wrong_colour_space", [])),
    }


def audit(root: Path) -> dict:
    """Measure M-1 and M-2 over the published Unity data."""
    atlas = trim_guids(root)
    debt = load_debt(root)

    materials = []
    for path in sorted((root / MATERIALS_DIR).glob("*.mat")):
        maps = material_maps(path)
        materials.append({
            "name": path.stem,
            "path": path.relative_to(root).as_posix(),
            "maps": sorted(maps),
            "atlas_roles": sorted({atlas[guid] for guid in maps.values() if guid in atlas}),
        })
    textureless = [item["name"] for item in materials if not item["maps"]]

    imports = []
    for folder in TRIM_DIRS:
        for meta in sorted((root / folder).glob("CityLabTrim*_*.png.meta")):
            role = _role_of(meta.name)
            actual = texture_import(meta)
            wanted_srgb, wanted_type = TRIM_MAP_IMPORT.get(role, (1, TEXTURE_TYPE_DEFAULT))
            imports.append({
                "role": role,
                "path": meta.relative_to(root).as_posix(),
                "sRGB": actual["sRGB"],
                "texture_type": actual["texture_type"],
                "expected_sRGB": wanted_srgb,
                "expected_texture_type": wanted_type,
                "passed": actual["sRGB"] == wanted_srgb and actual["texture_type"] == wanted_type,
            })
    miscoloured = [item["path"] for item in imports if not item["passed"]]

    new_textureless = [name for name in textureless if name not in debt["materials"]]
    new_miscoloured = [path for path in miscoloured if path not in debt["trim_maps"]]
    cleared = ([name for name in debt["materials"] if name not in textureless]
               + [path for path in debt["trim_maps"] if path not in miscoloured])

    violations = []
    if new_textureless:
        violations.append("M-1:undeclared_flat_materials:" + ",".join(sorted(new_textureless)))
    if new_miscoloured:
        violations.append("M-2:undeclared_miscoloured_maps:" + ",".join(sorted(new_miscoloured)))

    return {
        "schema": 1,
        "id": "unity_matter_gate_v1",
        "unity_launched": False,
        "rules": {
            "M-1": "a published factory material references at least one texture",
            "M-2": "a published trim map is imported in the colour space its role requires",
        },
        "materials": {
            "published": len(materials),
            "textured": len(materials) - len(textureless),
            "textureless": textureless,
            "detail": materials,
        },
        "trim_imports": {
            "checked": len(imports),
            "passed": len(imports) - len(miscoloured),
            "failed": miscoloured,
            "detail": imports,
        },
        "debt": {
            "declared_materials": len(debt["materials"]),
            "declared_trim_maps": len(debt["trim_maps"]),
            "still_owed": len(textureless) + len(miscoloured),
            "cleared_since_declaration": sorted(cleared),
        },
        "violations": violations,
    }


class DebtGrowth(Exception):
    """Refus d'absorber une violation neuve dans la dette declaree."""


def declare_debt(root: Path, allow_growth: bool = False) -> dict:
    """Ecrit le manifeste de dette depuis ce qui est mesure sur disque.

    Sert une fois, pour consigner l'etat que M1-ASSET-06 a laisse. Rejoue apres
    une reparation, il retrecit la liste. La regle << la dette ne peut que
    retrecir >> est mecanique et non conventionnelle : declarer une entree qui
    n'etait pas deja dans la dette est refuse, sauf `allow_growth` explicite --
    reserve a la toute premiere declaration.
    """
    measured = audit(root)
    previous = load_debt(root)
    if not allow_growth and (root / DEBT_MANIFEST).is_file():
        grown = ([name for name in measured["materials"]["textureless"]
                  if name not in previous["materials"]]
                 + [path for path in measured["trim_imports"]["failed"]
                    if path not in previous["trim_maps"]])
        if grown:
            raise DebtGrowth(
                "la dette matiere ne peut que retrecir ; entrees neuves : "
                + ", ".join(sorted(grown))
            )
    payload = {
        "schema": 1,
        "id": "unity_matter_debt_v1",
        "status": "declared",
        "why": (
            "Dette matiere mesuree, consignee en donnee et non en prose, sur le "
            "modele de requires_atlas dans AssetFactory/Styles/frontier.json. "
            "Tools/AssetFactory/matter_gate.py refuse toute violation absente de "
            "cette liste : la dette ne peut que retrecir."
        ),
        "rules": dict(measured["rules"]),
        "m1_materials_without_any_texture": sorted(measured["materials"]["textureless"]),
        "m2_trim_maps_in_the_wrong_colour_space": sorted(measured["trim_imports"]["failed"]),
    }
    path = root / DEBT_MANIFEST
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--report", default="AssetFactory/Reports/QA/unity_matter.json")
    parser.add_argument("--declare-debt", action="store_true",
                        help="reecrit le manifeste de dette depuis la mesure courante")
    parser.add_argument("--allow-debt-growth", action="store_true",
                        help="premiere declaration seulement : autorise des entrees neuves")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    if args.declare_debt:
        try:
            declare_debt(root, allow_growth=args.allow_debt_growth)
        except DebtGrowth as refusal:
            print("CITYLAB_MATTER_GATE_REFUS " + str(refusal))
            return 1
    report = audit(root)
    out = root / args.report
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    materials, imports = report["materials"], report["trim_imports"]
    print(
        "CITYLAB_MATTER_GATE "
        f"materials={materials['textured']}/{materials['published']}_textured "
        f"trim_imports={imports['passed']}/{imports['checked']}_correct "
        f"declared_debt={report['debt']['still_owed']} "
        f"violations={len(report['violations'])} unity_launched=false"
    )
    return 1 if report["violations"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
