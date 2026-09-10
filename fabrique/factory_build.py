"""Reconstruit le pilote de batiments d'une seule commande.

Refaire le pilote demandait **vingt et une invocations Blender a la main**, puis
les metriques, les portes de silhouette famille par famille, les planches, la
publication, le rafraichissement QA et la porte matiere -- chacun lance
separement, dans le bon ordre, sans que rien ne verifie que l'ordre a ete tenu.
Une generation coute douze secondes ; vingt et une en serie, quatre minutes, et
c'est du parallelisme gratuit.

Cet outil est **la** commande : un plan, une execution parallele, un rapport, un
verdict.

    py Tools/AssetFactory/factory_build.py --plan-only
    py Tools/AssetFactory/factory_build.py
    py Tools/AssetFactory/factory_build.py --only barn --jobs 3
    py Tools/AssetFactory/factory_build.py --force

**Il ne refait pas ce qui n'a pas change.** L'empreinte d'un asset couvre tout
ce qui peut changer sa geometrie : le style, l'entree du catalogue, les trois
variantes -- `plan_building` les lit toutes, le tirage est stratifie --, la
source du generateur, celle du plan, celle du **kit partage**
(`building_kit.py`, que tous les generateurs importent) et la version de
Blender. `AssetFactory/Manifests/factory_build_state.json` garde cette empreinte
face au `canonical_mesh_sha256` qu'elle a produit.

Le hash d'un conteneur FBX change a chaque execution : seul
`canonical_mesh_sha256` prouve le determinisme. `--force` sur des entrees
inchangees le verifie et le dit -- `determinism=ok` ou `determinism=drift`.

Il ne lance jamais Unity, ne touche pas au mode du harness et ne fusionne rien.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

# Lance a la main (`py Tools/AssetFactory/factory_build.py`), sys.path pointe sur
# le dossier du script et non sur la racine du depot. Les tests, eux, importent
# `Tools.AssetFactory.factory_build` : les deux chemins doivent marcher.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Tools.AssetFactory.citylab_factory import (  # noqa: E402
    blender_version,
    find_blender,
    load_config,
    FactoryPaths,
)

STATE_MANIFEST = "AssetFactory/Manifests/factory_build_state.json"
RUN_REPORT = "AssetFactory/Reports/factory_build.json"
CATALOG = "AssetFactory/Catalogs/building_pilot.json"
GENERATOR = "Tools/AssetFactory/Blender/generate_building_family.py"

# Tout ce dont la geometrie depend, hors catalogue et style. Le kit est partage :
# un changement dedans change les vingt-quatre batiments sans qu'une ligne de
# leur generateur ne bouge. Il s'appelait `generate_sawmill.py`, et ce nom-la
# valait a lui seul un test de rappel.
SHARED_SOURCES = (
    "Tools/AssetFactory/style.py",
    "Tools/AssetFactory/Blender/building_kit.py",
    "Tools/AssetFactory/Blender/generate_building_family.py",
)


class BuildError(RuntimeError):
    """Erreur attendue et lisible de la reconstruction."""


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def shared_digest(root: Path, catalog: dict, blender: str) -> str:
    """L'empreinte de ce qui vaut pour tous les assets du catalogue.

    Le style et les sources des generateurs ne sont pas propres a une famille :
    les separer evite de recalculer vingt et une fois la meme chose, et rend
    lisible dans le rapport *pourquoi* tout le pilote est perime d'un coup.
    """
    style_path = root / "AssetFactory" / "Styles" / f"{catalog['style']}.json"
    if not style_path.is_file():
        raise BuildError(f"Style absent : {style_path}")
    parts = [f"blender={blender}", f"style={sha256_file(style_path)}"]
    for source in SHARED_SOURCES:
        path = root / source
        if not path.is_file():
            raise BuildError(f"Source de generation absente : {source}")
        parts.append(f"{source}={sha256_file(path)}")
    return sha256_bytes("\n".join(parts).encode("utf-8"))


def asset_fingerprint(catalog: dict, family: dict, variant_id: str,
                      shared: str) -> str:
    """L'empreinte d'un asset : tout ce qui peut changer sa geometrie.

    Les **trois** variantes entrent dans l'empreinte, pas seulement celle qu'on
    genere : `plan_building` recoit la liste complete et son tirage est
    stratifie sur elle. Changer la variante `c` change ce que `a` tire.
    """
    payload = {
        "family": family,
        "variants": catalog["variants"],
        "variant": variant_id,
        "style": catalog["style"],
        "construction_contract": catalog.get("construction_contract", 1),
        "construction_stages": catalog["construction_stages"],
        "construction_schema": catalog["construction_schema"],
        "shared": shared,
    }
    return sha256_bytes(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8"))


def planned_assets(root: Path, catalog: dict, shared: str,
                   only: list[str]) -> list[dict]:
    assets = []
    for family in catalog["families"]:
        for variant in catalog["variants"]:
            asset_id = f"{family['id']}_{variant['id']}"
            if only and not any(fragment in asset_id for fragment in only):
                continue
            assets.append({
                "id": asset_id,
                "family": family["id"],
                "variant": variant["id"],
                "fingerprint": asset_fingerprint(catalog, family, variant["id"],
                                                 shared),
            })
    return assets


def staleness(root: Path, asset: dict, state: dict, force: bool) -> str | None:
    """Pourquoi cet asset doit etre refait, ou None s'il est a jour.

    La raison est rendue au rapport : un plan qui dit « je refais tout » sans
    dire pourquoi ne vaut pas mieux que vingt et une commandes a la main.
    """
    if force:
        return "force"
    previous = state.get("assets", {}).get(asset["id"])
    if previous is None:
        return "jamais_construit"
    if previous.get("fingerprint") != asset["fingerprint"]:
        return "entrees_changees"

    metrics_path = root / "AssetFactory" / "Reports" / f"{asset['id']}_metrics.json"
    if not metrics_path.is_file():
        return "metriques_absentes"
    metrics = load_json(metrics_path)
    if metrics.get("canonical_mesh_sha256") != previous.get("canonical_mesh_sha256"):
        return "metriques_desynchronisees"
    fbx = metrics.get("outputs", {}).get("fbx")
    if not fbx or not (root / fbx).is_file():
        return "fbx_absent"
    return None


def generate_one(blender_path: Path, root: Path, catalog_path: str,
                 asset: dict, skip_previews: bool) -> dict:
    command = [
        str(blender_path), "--background", "--factory-startup",
        "--python", str(root / GENERATOR), "--",
        "--project-root", str(root),
        "--catalog", catalog_path,
        "--output-root", "AssetFactory",
        "--family", asset["family"],
        "--variant", asset["variant"],
    ]
    if skip_previews:
        command.append("--skip-previews")
    started = time.monotonic()
    completed = subprocess.run(command, capture_output=True, text=True)
    elapsed = time.monotonic() - started
    marker = "CITYLAB_BUILDING_GENERATED"
    line = next((item for item in (completed.stdout or "").splitlines()
                 if item.startswith(marker)), "")
    return {
        "id": asset["id"],
        "returncode": completed.returncode,
        "seconds": round(elapsed, 1),
        "line": line,
        "stdout": completed.stdout or "",
        "stderr": completed.stderr or "",
    }


def run_step(root: Path, name: str, command: list[str]) -> dict:
    started = time.monotonic()
    completed = subprocess.run(command, capture_output=True, text=True,
                               cwd=str(root))
    elapsed = time.monotonic() - started
    tail = [line for line in (completed.stdout or "").splitlines() if line.strip()]
    return {
        "step": name,
        "returncode": completed.returncode,
        "seconds": round(elapsed, 1),
        "line": tail[-1] if tail else "",
        "stdout": completed.stdout or "",
        "stderr": completed.stderr or "",
    }


def read_state(root: Path) -> dict:
    path = root / STATE_MANIFEST
    if not path.is_file():
        return {"schema": 1, "id": "citylab_factory_build_state", "assets": {}}
    return load_json(path)


def write_state(root: Path, state: dict) -> None:
    """L'etat est une fonction pure des entrees et des sorties.

    Aucune date, aucune duree : un etat qui bouge sans que rien n'ait change
    n'est pas relisible, et c'est lui qui justifie chaque saut.
    """
    path = root / STATE_MANIFEST
    path.parent.mkdir(parents=True, exist_ok=True)
    state["assets"] = dict(sorted(state["assets"].items()))
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reconstruit le pilote de batiments d'une seule commande.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--catalog", default=CATALOG)
    parser.add_argument("--only", action="append", default=[],
                        help="ne traiter que les assets dont l'identifiant "
                             "contient ce fragment")
    parser.add_argument("--jobs", type=int, default=0,
                        help="generations Blender en parallele (0 = automatique)")
    parser.add_argument("--force", action="store_true",
                        help="tout refaire, et verifier le determinisme de ce "
                             "dont les entrees n'ont pas change")
    parser.add_argument("--plan-only", action="store_true",
                        help="dire ce qui serait refait et pourquoi, sans rien "
                             "lancer")
    parser.add_argument("--skip-previews", action="store_true",
                        help="ne pas rendre les images d'etape (plus rapide, "
                             "mais ni planche ni porte de silhouette)")
    parser.add_argument("--no-publish", action="store_true",
                        help="s'arreter avant la publication sous Assets/ ; "
                             "apres une regeneration, `qa_factory_release` "
                             "tombera sur `building_workbench_hash` tant que la "
                             "publication n'a pas suivi")
    return parser.parse_args(argv)


def default_jobs(count: int) -> int:
    import os
    return max(1, min(count, (os.cpu_count() or 4) // 2, 8))


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    root = Path(args.project_root).resolve()
    catalog = load_json(root / args.catalog)

    config = load_config(FactoryPaths(root, root / "AssetFactory" / "config.json"))
    blender_path = find_blender(config, root)
    blender = blender_version(blender_path)

    shared = shared_digest(root, catalog, blender)
    assets = planned_assets(root, catalog, shared, args.only)
    if not assets:
        print("CITYLAB_FACTORY_BUILD_FAILED aucun_asset_selectionne")
        return 1

    state = read_state(root)
    for asset in assets:
        asset["reason"] = staleness(root, asset, state, args.force)
    stale = [asset for asset in assets if asset["reason"]]
    fresh = [asset for asset in assets if not asset["reason"]]
    jobs = args.jobs if args.jobs > 0 else default_jobs(len(stale) or 1)

    print(f"CITYLAB_FACTORY_BUILD_PLAN selection={len(assets)} "
          f"a_refaire={len(stale)} a_jour={len(fresh)} jobs={jobs} "
          f"blender=\"{blender}\"")
    for asset in stale:
        print(f"  refaire {asset['id']} ({asset['reason']})")

    if args.plan_only:
        return 0

    report: dict = {
        "schema": 1,
        "id": "citylab_factory_build",
        "blender": blender,
        "selection": [asset["id"] for asset in assets],
        "rebuilt": [],
        "up_to_date": [asset["id"] for asset in fresh],
        "steps": [],
        "failures": [],
        "unity_launched": False,
    }
    failures: list[str] = []
    started = time.monotonic()

    # 1. Generation. Vingt et une generations de douze secondes en serie coutent
    #    quatre minutes, et c'est du parallelisme gratuit : chaque Blender ecrit
    #    dans des chemins qui lui sont propres.
    drift: list[str] = []
    if stale:
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
            results = list(pool.map(
                lambda asset: generate_one(blender_path, root, args.catalog,
                                           asset, args.skip_previews),
                stale))
        for asset, result in zip(stale, results):
            if result["returncode"] != 0:
                failures.append(f"generation:{asset['id']}")
                report["failures"].append({
                    "id": asset["id"],
                    "returncode": result["returncode"],
                    "stderr": result["stderr"][-2000:],
                })
                print(f"CITYLAB_FACTORY_BUILD_ERROR generation {asset['id']} "
                      f"code={result['returncode']}")
                sys.stderr.write(result["stderr"])
                continue
            metrics = load_json(root / "AssetFactory" / "Reports"
                                / f"{asset['id']}_metrics.json")
            previous = state.get("assets", {}).get(asset["id"], {})
            # Seul `canonical_mesh_sha256` prouve le determinisme : le hash du
            # conteneur FBX change a chaque execution.
            if (previous.get("fingerprint") == asset["fingerprint"]
                    and previous.get("canonical_mesh_sha256")
                    and previous["canonical_mesh_sha256"]
                    != metrics["canonical_mesh_sha256"]):
                drift.append(asset["id"])
            state.setdefault("assets", {})[asset["id"]] = {
                "fingerprint": asset["fingerprint"],
                "blender": blender,
                "canonical_mesh_sha256": metrics["canonical_mesh_sha256"],
                "triangles": metrics["triangles"],
            }
            report["rebuilt"].append(asset["id"])
            print(f"  genere {asset['id']} en {result['seconds']}s "
                  f"triangles={metrics['triangles']['lod0']}")
        write_state(root, state)

    if drift:
        failures.append("determinisme:" + ",".join(drift))
        report["determinism"] = {"status": "drift", "assets": drift}
    elif args.force and stale:
        report["determinism"] = {"status": "ok", "assets": []}

    generation_failed = any(item.startswith("generation:") for item in failures)

    # Publier et rafraichir la preuve FBX sont des **producteurs** : ils coutent
    # un Blender sur 56 fichiers, et ne se relancent que si la geometrie a bouge
    # -- ou si l'execution precedente ne les a pas atteints. Sinon un lancement
    # interrompu apres la generation laisserait des FBX regeneres et jamais
    # republies : le piege `building_workbench_hash`, rendu invisible par le
    # cache.
    #
    # Une porte rouge, elle, ne rend pas les producteurs perimes. Douze
    # batiments sur vingt et un sont sous le seuil C-1 et la question est ouverte
    # chez le proprietaire : si son rouge forcait a republier, la commande ne
    # serait plus jamais silencieuse tant qu'il n'a pas tranche.
    previous_run = (load_json(root / RUN_REPORT)
                    if (root / RUN_REPORT).is_file() else {})
    produced = {step["step"] for step in previous_run.get("steps", [])
                if step.get("blocking") and step.get("returncode") == 0}
    unfinished = not {"publication", "qa_fbx"} <= produced
    touched = sorted({asset["family"] for asset in
                      (assets if unfinished else stale)})
    report["downstream_reason"] = ("regeneration" if stale
                                   else "producteurs_non_atteints" if unfinished
                                   else "producteurs_a_jour")

    # 2. Les portes qui suivent la geometrie, famille par famille, puis les
    #    portes transversales. L'ordre est ici et nulle part ailleurs : c'est
    #    tout l'interet d'avoir une seule commande.
    #
    #    Deux natures d'echec, et les confondre coute cher. Un **producteur**
    #    qui echoue rend faux tout ce qui vient apres : rien ne se publie d'un
    #    asset qui n'a pas ete genere, et `qa_factory_release` ne juge rien
    #    d'utile sur une publication qui n'a pas eu lieu. Une **porte** qui
    #    echoue, elle, a fait son travail : elle a mesure. S'arreter dessus
    #    cacherait les six familles suivantes, et c'est justement le tableau
    #    complet qu'on vient chercher en lancant une seule commande.
    #
    #    Aucune porte n'est sautee, aucune n'est adoucie : le verdict final est
    #    rouge des qu'une seule l'est, et le code de retour vaut 1.
    steps: list[tuple[str, list[str], bool]] = []
    if not generation_failed:
        if not args.skip_previews:
            # Les portes se mesurent sur toute la selection a chaque lancement :
            # elles coutent une seconde, et c'est leur tableau qu'on vient
            # chercher, pas seulement celui des familles qui ont bouge.
            for family in sorted({asset["family"] for asset in assets}):
                steps.append((f"silhouette:{family}", [
                    sys.executable, "Tools/AssetFactory/silhouette_gate.py",
                    "--family", family], False))
                steps.append((f"planche:{family}", [
                    sys.executable, "Tools/AssetFactory/construction_board.py",
                    "--family", family, "--variant", "c"], False))
        if touched and args.no_publish:
            print("  ATTENTION --no-publish apres une regeneration : la preuve "
                  "FBX publiee reste celle d'avant, et `qa_release` le dira")
        elif touched:
            print(f"  producteurs sur {len(touched)} famille(s) "
                  f"({report['downstream_reason']})")
        if touched and not args.no_publish:
            publish = [sys.executable, "Tools/AssetFactory/publish_building_pilot.py",
                       "--publish"]
            for family in touched:
                publish += ["--only", family]
            steps.append(("publication", publish, True))
            # Piege mesure : apres toute regeneration il faut republier, sinon
            # `qa_factory_release` tombe sur `building_workbench_hash`.
            steps.append(("qa_fbx", [
                sys.executable, "Tools/AssetFactory/refresh_fbx_qa.py"], True))
        steps.append(("matiere",
                      [sys.executable, "Tools/AssetFactory/matter_gate.py"], False))
        steps.append(("qa_release", [
            sys.executable, "Tools/AssetFactory/qa_factory_release.py"], False))

    for name, command, blocking in steps:
        result = run_step(root, name, command)
        report["steps"].append({key: result[key] for key in
                                ("step", "returncode", "seconds", "line")}
                               | {"blocking": blocking,
                                  "status": "passed" if result["returncode"] == 0
                                            else "failed"})
        print(f"  {name} -> {result['line'] or 'code ' + str(result['returncode'])}")
        if result["returncode"] != 0:
            failures.append(name)
            sys.stderr.write(result["stderr"])
            if blocking:
                report["stopped_after"] = name
                break

    report["seconds"] = round(time.monotonic() - started, 1)
    report["failed_steps"] = failures
    report["status"] = "failed" if failures else "passed"
    report_path = root / RUN_REPORT
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")

    determinism = report.get("determinism", {}).get("status", "non_verifie")
    verdict = "FAILED" if failures else "OK"
    print(f"CITYLAB_FACTORY_BUILD_{verdict} refaits={len(report['rebuilt'])} "
          f"a_jour={len(report['up_to_date'])} etapes={len(report['steps'])} "
          f"determinisme={determinism} secondes={report['seconds']} "
          f"unity_launched=false"
          + ("" if not failures else " echecs=" + ",".join(failures)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
