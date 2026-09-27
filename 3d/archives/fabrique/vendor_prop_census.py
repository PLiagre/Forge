"""Recense et chiffre le decor disponible dans les packs Vendor.

Le budget d'un village se joue sur le decor, pas sur les batiments : les
vingt-quatre pesent 50 096 triangles au LOD0 et **un seul arbre Polytope en
coute 4 494**. Un inventaire cite de memoire ne dit pas cela ; un inventaire
mesure, si.

    py Tools/AssetFactory/vendor_prop_census.py
    py Tools/AssetFactory/vendor_prop_census.py --plan-only
    py Tools/AssetFactory/vendor_prop_census.py --report

Il lit les sources **sans jamais les modifier**, ne publie rien sous `Assets/`
et ne lance pas Unity. Un seul processus Blender traite toute la liste.

`--report` n'ouvre pas Blender : il relit le recensement deja produit et en tire
le tableau par famille de decor.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Tools.AssetFactory.citylab_factory import (  # noqa: E402
    FactoryPaths,
    find_blender,
    load_config,
)

AUDIT_SCRIPT = "Tools/AssetFactory/Blender/audit_vendor_props.py"
CENSUS = "AssetFactory/Reports/vendor_prop_census.json"

# Les packs qui portent du decor. Les packs d'animation et de personnages n'en
# ont pas : les recenser couterait des minutes pour zero ligne utile.
DECOR_PACKS = ("emaceart_slavic_world_free", "polytope_studio")

# Les familles de decor dont un village a besoin, et les fragments de nom qui
# les designent dans les deux packs. C'est la seule table de correspondance du
# recensement : elle sert a lire le resultat, pas a filtrer la mesure.
DECOR_FAMILIES: dict[str, tuple[str, ...]] = {
    "arbre": ("_Tree_", "PT_Fruit_Tree", "PT_Pine", "PT_Birch", "PT_Oak"),
    "arbuste_souche": ("_Bush_", "_Shrub", "_Stump", "_Trunk", "_Log_"),
    "herbe_fleur": ("_Grass", "_Flower", "_Moss", "_Plant"),
    "rocher": ("Rock", "_Stone_", "EnvRock"),
    "cloture_portail": ("_Fence", "_Gate", "_Railing"),
    "chemin_sol": ("_Road", "_Path", "_Mud", "_Sand", "_Cobble"),
    "eau_pont": ("_River", "_Bridge", "_Well", "_Whell", "_Water"),
    "mobilier": ("_Tabble", "_Table", "_Bench", "_Chair", "_Stool", "_Shelf",
                 "_Bed_", "_Chest"),
    "contenant": ("_Barrel", "_Crate", "_Box_", "_Basket", "_Sack", "_Bag_",
                  "_Bale"),
    "feu_cuisine": ("_Stove", "_Oven", "_cauldron", "_Cauldron", "_Pot_",
                    "_Kettle", "_Fireplace"),
    "marche_etal": ("_Stand", "_Stall", "_Sheet", "_Awning"),
    "outil": ("_Tool", "_Axe", "_Ladder", "_Bucket", "_Wheel_", "_Cart",
              "_Wagon", "_Barrow"),
    "batiment_module": ("_House", "_Village_", "_OutBuilding", "_Hovel",
                        "_Roof_"),
}


def family_of(name: str) -> str:
    for family, fragments in DECOR_FAMILIES.items():
        if any(fragment.lower() in name.lower() for fragment in fragments):
            return family
    return "autre"


def collect(root: Path, config: dict) -> list[dict]:
    sources = []
    for entry in config["sources"]:
        if entry["id"] not in DECOR_PACKS:
            continue
        base = root / entry["path"]
        for path in sorted(base.rglob("*.fbx")):
            relative = path.relative_to(root).as_posix()
            sources.append({
                "id": path.stem,
                "pack": entry["id"],
                "path": relative,
            })
    return sources


def instance_cost(item: dict) -> int:
    """Ce qu'une instance posee dans une scene coute vraiment.

    Le total d'un fichier additionne ses trois LOD : une source EmaceArt porte
    `LOD0`, `LOD1` et `LOD2` dans le meme FBX, et sommer les trois compare des
    choux et des carottes avec le LOD0 d'un batiment. Une source Polytope, elle,
    n'a qu'un maillage sans suffixe -- c'est celui-la qui est pose.
    """
    return item["triangles_lod0"] or item["triangles_unnamed"] or item["triangles"]


def report(root: Path) -> int:
    census = json.loads((root / CENSUS).read_text(encoding="utf-8"))
    measured = [item for item in census["sources"] if item["status"] == "passed"]
    families: dict[str, list[dict]] = {}
    for item in measured:
        families.setdefault(family_of(item["id"]), []).append(item)

    print("Cout LOD0 d'une instance posee. Le total d'un fichier additionne ses "
          "trois LOD :\nle comparer au LOD0 d'un batiment double la facture du "
          "decor.\n")
    print(f"{'famille':<20}{'n':>5}{'min':>8}{'median':>8}{'max':>8}"
          f"{'le moins cher':>36}")
    for family in sorted(families, key=lambda key: -len(families[key])):
        items = sorted(families[family], key=instance_cost)
        counts = [instance_cost(item) for item in items]
        print(f"{family:<20}{len(items):>5}{counts[0]:>8}"
              f"{counts[len(counts) // 2]:>8}{counts[-1]:>8}"
              f"{items[0]['id'][:35]:>36}")

    blind = [item for item in measured if item["triangles_lod0"] == 0]
    print(f"\nsources sans aucun maillage nomme LOD0 : {len(blind)} / "
          f"{len(measured)}.\nUn import « LOD0 seulement » n'en rendrait rien : "
          f"c'est le piege de la lame plate,\nmesure ici avant de le repayer sur "
          f"un rendu.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--report", action="store_true",
                        help="relire le recensement produit, sans Blender")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()

    if args.report:
        return report(root)

    config = load_config(FactoryPaths(root, root / "AssetFactory" / "config.json"))
    sources = collect(root, config)
    if not sources:
        print("CITYLAB_VENDOR_CENSUS_ERROR aucune_source")
        return 1

    plan_path = root / "AssetFactory/Reports/QA/vendor_census_plan.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps({
        "project_root": root.as_posix(),
        "output": CENSUS,
        "sources": sources,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.plan_only:
        packs = {entry["pack"] for entry in sources}
        print(f"CITYLAB_VENDOR_CENSUS_PLAN sources={len(sources)} "
              f"packs={len(packs)}")
        return 0

    blender = find_blender(config, root)
    completed = subprocess.run([
        str(blender), "--background", "--factory-startup",
        "--python", str(root / AUDIT_SCRIPT), "--", "--plan", str(plan_path),
    ], capture_output=True, text=True)
    for line in (completed.stdout or "").splitlines():
        if line.startswith("CITYLAB_VENDOR_CENSUS"):
            print(line)
    if completed.returncode != 0:
        sys.stderr.write(completed.stderr[-4000:])
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
