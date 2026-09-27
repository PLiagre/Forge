from __future__ import annotations

import hashlib
import json
import math
import random
import tempfile
import unittest
from pathlib import Path

from Tools.AssetFactory.matter_gate import (
    DEBT_MANIFEST,
    DebtGrowth,
    MATERIALS_DIR,
    TRIM_DIRS,
    TRIM_MAP_IMPORT,
    audit as matter_audit,
    declare_debt,
    material_maps,
    texture_import,
)
from Tools.AssetFactory.factory_build import (
    SHARED_SOURCES,
    STATE_MANIFEST,
    asset_fingerprint,
    planned_assets,
    shared_digest,
    staleness,
)
from Tools.AssetFactory.village_plan import (
    PLAN as VILLAGE_PLAN,
    SPEC as VILLAGE_SPEC,
    heightfield,
    instance_cost,
    plots as village_plots,
    sample_height,
    verify as village_verify,
)
from Tools.AssetFactory.publish_building_pilot import family_budget
from Tools.AssetFactory.qa_factory_release import stale_reports
from Tools.AssetFactory.silhouette_gate import (
    articulation,
    iou_masks,
    min_articulation,
)
from Tools.AssetFactory.style import (
    FACES,
    LEVEL_STOREYS,
    STOREY_BASES,
    face_of,
    StyleError,
    load_style,
    plan_building,
    storey_height,
    stratified_picks,
)
from Tools.AssetFactory.citylab_factory import (
    build_inventory,
    discover_unregistered_sources,
    publish_from_manifest,
    render_json,
    sha256_file,
    validate_admission_profile,
    validate_recipe,
    validate_construction_contract,
    validate_style,
    validate_style_against_atlas,
    validate_style_against_catalog,
    validate_texture_recipe,
)


class InventoryTests(unittest.TestCase):
    project_root = Path(__file__).resolve().parents[2]

    def test_inventory_is_deterministic_and_flags_unregistered_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            registered = root / "Assets" / "Publisher" / "Pack"
            unregistered = root / "Assets" / "New Pack"
            registered.mkdir(parents=True)
            unregistered.mkdir(parents=True)
            (registered / "house.fbx").write_bytes(b"house")
            (registered / "wall.png").write_bytes(b"wall")
            (registered / "house.prefab").write_text("prefab", encoding="utf-8")
            (registered / "house.fbx.meta").write_text("ignored", encoding="utf-8")
            (unregistered / "tower.obj").write_bytes(b"tower")

            config = {
                "assets_root": "Assets",
                "adapted_output_root": "Assets/CityLabHost/Adapted/Factory",
                "ignored_asset_roots": ["CityLabHost"],
                "discover_unregistered_asset_roots": True,
                "sources": [
                    {
                        "id": "publisher_pack",
                        "path": "Assets/Publisher",
                        "provenance": {
                            "store_url": "https://example.invalid/pack",
                            "license_status": "verified",
                        },
                    }
                ],
            }

            first = build_inventory(config, root)
            second = build_inventory(config, root)

            self.assertEqual(render_json(first), render_json(second))
            self.assertEqual(first["summary"]["model_candidates"], 2)
            self.assertEqual(first["summary"]["texture_candidates"], 1)
            self.assertEqual(first["sources"][0]["warnings"], [
                "source_non_enregistree",
                "url_store_manquante",
                "licence_a_verifier",
            ])
            publisher = first["sources"][1]
            self.assertEqual(publisher["counts"]["prefabs"], 1)
            self.assertEqual(publisher["models"][0]["sha256"], sha256_file(registered / "house.fbx"))

    def test_recipe_rejects_hash_drift_and_output_outside_adapted(self) -> None:
        inventory = {
            "sources": [
                {
                    "registered": True,
                    "provenance": {"license_status": "verified"},
                    "models": [{"path": "Assets/Vendor/wall.fbx", "sha256": "expected"}],
                }
            ]
        }
        recipe = {
            "schema": 1,
            "id": "building_house_frontier_01",
            "seed": 42,
            "status": "draft",
            "planned_output": "Assets/Vendor/overwritten.fbx",
            "inputs": [{"role": "wall", "path": "Assets/Vendor/wall.fbx", "sha256": "changed"}],
        }

        errors = validate_recipe(recipe, inventory, "Assets/CityLabHost/Adapted/Factory")

        self.assertIn("sortie_hors_adapted_factory", errors)
        self.assertIn("entree_0_hash_incorrect", errors)

    def test_building_contract_requires_four_contiguous_stages_and_three_variants(self) -> None:
        recipe = {
            "category": "building",
            "construction_schema": "AssetFactory/Schemas/building_construction.schema.json",
            "construction": {
                "mode": "cumulative_layers",
                "stages": [
                    {"id": "foundation", "order": 1, "progress": [0.0, 0.25], "required_categories": ["stone"]},
                    {"id": "frame", "order": 2, "progress": [0.25, 0.55], "required_categories": ["wood"]},
                    {"id": "roof", "order": 3, "progress": [0.55, 0.8], "required_categories": ["roofing"]},
                    {"id": "details", "order": 4, "progress": [0.8, 1.0], "required_categories": ["fixtures"]},
                ],
            },
            "variants": [
                {"id": identifier, "seed_offset": index, "chimney": index % 2 == 0,
                 "palette": {"wood": "#110b05", "wood_highlight": "#412611",
                             "roof": "#27140c", "roof_accent": "#55321c"}}
                for index, identifier in enumerate(("a", "b", "c"))
            ],
        }

        self.assertEqual([], validate_construction_contract(recipe))
        recipe["construction"]["stages"][2]["progress"] = [0.6, 0.8]
        recipe["variants"] = recipe["variants"][:2]
        errors = validate_construction_contract(recipe)
        self.assertIn("phase_3_progression_invalide", errors)
        self.assertIn("variantes_insuffisantes", errors)

    def test_building_pilot_declares_coherent_envelopes_and_identity_markers(self) -> None:
        catalog = json.loads((self.project_root / "AssetFactory/Catalogs/building_pilot.json")
                             .read_text(encoding="utf-8"))
        families = {family["function"]: family for family in catalog["families"]}
        # Huit depuis que la scierie est entree au catalogue. Elle etait le
        # dernier batiment sur la grammaire refusee, avec son propre generateur
        # et son propre contrat : 39 980-41 952 triangles pour un budget de
        # 4 000, sans porte de silhouette ni porte D-1 pour la juger.
        self.assertEqual(8, len(families))
        self.assertEqual("stone_timber", families["sawmill"]["wall_system"])
        self.assertEqual("dressed_stone", families["chapel"]["wall_system"])
        self.assertEqual("brick_stone", families["blacksmith"]["wall_system"])
        self.assertEqual("timber_plank", families["granary"]["wall_system"])
        self.assertEqual("timber_plank", families["barn"]["wall_system"])
        for family in families.values():
            self.assertIn(family["roof_system"], {"clay_tile", "wood_shingle", "slate"})
            self.assertGreaterEqual(len(family["identity_markers"]), 5)

    def test_character_proposals_cover_all_roles_and_source_hash(self) -> None:
        catalog = json.loads((self.project_root / "AssetFactory/Catalogs/character_proposals.json")
                             .read_text(encoding="utf-8"))
        proposals = catalog["proposals"]
        self.assertEqual(8, len(proposals))
        self.assertEqual(
            {"worker", "wealthy", "peasant", "religious", "soldier", "noble", "bourgeois", "beggar"},
            {proposal["role"] for proposal in proposals},
        )
        self.assertEqual({"male", "female"}, {proposal["gender"] for proposal in proposals})
        self.assertEqual({"child", "adult", "elder"}, {proposal["age"] for proposal in proposals})
        source = self.project_root / catalog["source"]["path"]
        self.assertEqual(catalog["source"]["sha256"], sha256_file(source))

    def test_character_factory_publishes_complete_rigged_matrix(self) -> None:
        catalog = json.loads((self.project_root / "AssetFactory/Catalogs/character_factory.json")
                             .read_text(encoding="utf-8"))
        manifest = json.loads((self.project_root / "AssetFactory/Manifests/character_factory.json")
                              .read_text(encoding="utf-8"))
        self.assertEqual(6, len(catalog["body_bases"]))
        self.assertEqual(4, len(catalog["morphologies"]))
        self.assertEqual(8, len(catalog["role_capsules"]))
        self.assertEqual({"male", "female"}, set(catalog["genders"]))
        self.assertEqual({"child", "adult", "elder"}, set(catalog["ages"]))
        self.assertEqual(set(catalog["social_roles"]),
                         {role["id"] for role in catalog["role_capsules"]})
        self.assertEqual(52, catalog["rig"]["expected_deform_bones"])
        self.assertEqual(24, manifest["contract"]["body_assets"])
        self.assertEqual(8, manifest["contract"]["role_capsules"])
        self.assertEqual(32, len(manifest["assets"]))
        self.assertEqual(32, len({asset["canonical_sha256"] for asset in manifest["assets"]}))
        self.assertFalse(manifest["gates"]["unity_launched"])
        self.assertFalse(manifest["gates"]["unity_humanoid_import"])
        for asset in manifest["assets"]:
            path = self.project_root / asset["path"]
            self.assertTrue(path.is_file())
            self.assertTrue(asset["path"].startswith("Assets/CityLabHost/Adapted/Factory/Characters/"))
            self.assertEqual(asset["fbx_sha256"], sha256_file(path))
            self.assertEqual(3, len(asset["lod_triangles"]))

    def test_admission_discovers_new_pack_and_validates_production_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack = root / "Assets" / "New Medieval Pack"
            pack.mkdir(parents=True)
            (pack / "building.fbx").write_bytes(b"new-pack")
            config = {
                "assets_root": "Assets",
                "adapted_output_root": "Assets/CityLabHost/Adapted/Factory",
                "ignored_asset_roots": ["CityLabHost"],
                "discover_unregistered_asset_roots": True,
                "sources": [],
            }
            candidates = discover_unregistered_sources(config, root)
            self.assertEqual(1, len(candidates))
            self.assertEqual("Assets/New Medieval Pack", candidates[0]["path"])
            self.assertEqual(1, candidates[0]["model_candidates"])
            self.assertIn("licence_a_verifier", candidates[0]["warnings"])

        config = json.loads((self.project_root / "AssetFactory/config.json")
                            .read_text(encoding="utf-8"))
        inventory = json.loads((self.project_root / "AssetFactory/Reports/source_inventory.json")
                               .read_text(encoding="utf-8"))
        profile = json.loads((self.project_root /
                             "AssetFactory/AdmissionProfiles/ganzse_free_modular_character.json")
                             .read_text(encoding="utf-8"))
        self.assertEqual([], validate_admission_profile(profile, inventory, config))
        profile["source"]["provenance"]["license_status"] = "unknown"
        self.assertIn("licence_non_verifiee",
                      validate_admission_profile(profile, inventory, config))

    def test_generic_publication_is_dry_run_by_default_and_atomic_when_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "AssetFactory/Workbench/Example/model.fbx"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"generated-model")
            destination = root / "Assets/CityLabHost/Adapted/Factory/Example/model.fbx"
            manifest = root / "AssetFactory/Manifests/example.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(json.dumps({
                "status": "generated",
                "status_after_publication": "published",
                "assets": [{
                    "generated_path": "AssetFactory/Workbench/Example/model.fbx",
                    "path": "Assets/CityLabHost/Adapted/Factory/Example/model.fbx",
                    "fbx_sha256": sha256_file(source),
                }]
            }), encoding="utf-8")
            config = {"adapted_output_root": "Assets/CityLabHost/Adapted/Factory"}

            self.assertEqual(0, publish_from_manifest(config, root, manifest, False))
            self.assertFalse(destination.exists())
            self.assertEqual(0, publish_from_manifest(config, root, manifest, True))
            self.assertEqual(source.read_bytes(), destination.read_bytes())
            self.assertFalse(destination.with_suffix(".fbx.tmp").exists())
            published_manifest = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual("published", published_manifest["status"])
            self.assertEqual("explicit_atomic_copy", published_manifest["publication"]["mode"])

    def test_pbr_trim_has_six_coherent_published_maps_and_three_review_scales(self) -> None:
        recipe = json.loads((self.project_root / "AssetFactory/Recipes/texture_citylab_trim_v1.json")
                            .read_text(encoding="utf-8"))
        manifest = json.loads((self.project_root / "AssetFactory/Manifests/citylab_trim_v1.json")
                              .read_text(encoding="utf-8"))
        report = json.loads((self.project_root / "AssetFactory/Reports/Textures/citylab_trim_v1.json")
                            .read_text(encoding="utf-8"))
        self.assertEqual([], validate_texture_recipe(
            recipe, "Assets/CityLabHost/Adapted/Factory"))
        self.assertEqual(
            {"BaseColor", "Normal", "AO", "Roughness", "Metallic", "VariationMask"},
            set(recipe["maps"]),
        )
        self.assertEqual(6, len(manifest["assets"]))
        self.assertTrue(manifest["gates"]["determinism"])
        self.assertEqual("published_pending_unity_material_validation", manifest["status"])
        self.assertEqual({"512", "256", "128"}, set(report["contrast_by_resolution"]))
        for resolution in report["contrast_by_resolution"].values():
            self.assertTrue(all(value >= recipe["budgets"]["contrast_min"]
                                for value in resolution.values()))
        for asset in manifest["assets"]:
            generated = self.project_root / asset["generated_path"]
            published = self.project_root / asset["path"]
            self.assertEqual(asset["sha256"], sha256_file(generated))
            self.assertEqual(asset["sha256"], sha256_file(published))
            self.assertEqual([2048, 2048], asset["resolution"])

        invalid_recipe = json.loads(json.dumps(recipe))
        invalid_recipe["maps"].remove("AO")
        invalid_recipe["outputs"]["published"] = "Assets/Vendor/Textures"
        errors = validate_texture_recipe(invalid_recipe, "Assets/CityLabHost/Adapted/Factory")
        self.assertIn("cartes_pbr_invalides", errors)
        self.assertIn("sortie_hors_adapted_factory", errors)

    def test_factory_qa_covers_every_published_fbx_and_texture(self) -> None:
        report_path = self.project_root / "AssetFactory/Reports/factory_qa.json"
        board_path = self.project_root / "AssetFactory/Reports/QA/factory_review_board.png"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        manifest = json.loads((self.project_root / "AssetFactory/Manifests/factory_qa.json")
                              .read_text(encoding="utf-8"))

        self.assertEqual("technical_pass_artistic_and_unity_gates_pending", report["status"])
        self.assertEqual(24, report["summary"]["building_fbx"])
        self.assertEqual(32, report["summary"]["character_fbx"])
        self.assertEqual(6, report["summary"]["texture_maps"])
        self.assertEqual(report["summary"]["fbx_meshes"], report["summary"]["uv_meshes"])
        self.assertEqual(0, report["summary"]["embedded_colliders"])
        self.assertEqual("passed_all_fbx_meshes", report["gates"]["uv"])
        self.assertEqual("passed_none_embedded", report["gates"]["colliders"])
        self.assertEqual("pending_user_review", report["gates"]["artistic_approval"])
        self.assertFalse(report["unity_launched"])
        self.assertEqual(sha256_file(report_path), manifest["report_sha256"])
        self.assertEqual(sha256_file(board_path), manifest["review_board_sha256"])

    def test_legacy_save_fixture_has_valid_checksum_and_complete_state_axes(self) -> None:
        fixture = json.loads((self.project_root /
                             "Packages/com.victoria.citymode/Tests/Fixtures/city_save_v0.json")
                            .read_text(encoding="utf-8"))
        payload = fixture["payload"]
        self.assertEqual(
            fixture["payloadSha256"],
            hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        )
        snapshot = json.loads(payload)
        self.assertEqual(0, snapshot["schemaVersion"])
        self.assertEqual(1001, snapshot["cityId"])
        self.assertIn("elapsedSeconds", snapshot)
        self.assertIn("stockWood", snapshot)
        self.assertIn("reservedWood", snapshot)
        for collection in ("households", "roads", "parcels", "buildings",
                           "villagers", "productionSites"):
            self.assertIn(collection, snapshot)


try:
    from Tools.AssetFactory.generate_pbr_trim import (
        BAND_GENERATORS,
        band_bounds,
        canonical_sha256,
    )
    import numpy as np
    TRIM_TOOLING = True
except ImportError:  # numpy/Pillow absents : la suite reste utile sans le laboratoire
    TRIM_TOOLING = False


@unittest.skipUnless(TRIM_TOOLING, "numpy et Pillow requis pour le laboratoire de textures")
class TrimBandTests(unittest.TestCase):
    project_root = Path(__file__).resolve().parents[2]

    def _recipe(self, name: str) -> dict:
        return json.loads((self.project_root / "AssetFactory" / "Recipes" / name)
                          .read_text(encoding="utf-8"))

    def test_band_bounds_reproduce_the_historical_three_way_split(self) -> None:
        # Le refactor multi-bandes ne doit pas deplacer d'un pixel le decoupage
        # de citylab_trim_v1, dont les cartes sont deja publiees.
        size = 2048
        regions = self._recipe("texture_citylab_trim_v1.json")["regions"]
        bounds = [band_bounds(region, size) for region in regions]
        self.assertEqual([(0, size // 3), (size // 3, size * 2 // 3), (size * 2 // 3, size)],
                         bounds)

    def test_every_recipe_band_has_a_generator(self) -> None:
        for name in ("texture_citylab_trim_v1.json", "texture_citylab_trim_v2.json"):
            for region in self._recipe(name)["regions"]:
                self.assertIn(region["material"], BAND_GENERATORS,
                              f"{name}:{region['id']}")

    def test_v2_covers_every_wall_system_of_the_building_catalog(self) -> None:
        regions = {region["id"] for region in self._recipe("texture_citylab_trim_v2.json")["regions"]}
        self.assertEqual({"structural_wood", "sawn_planks", "lime_plaster",
                          "dressed_stone", "fired_brick", "roof_tiles"}, regions)

    def test_v2_bands_tile_the_unit_interval_without_gap_or_overlap(self) -> None:
        regions = sorted(self._recipe("texture_citylab_trim_v2.json")["regions"],
                         key=lambda region: region["v_min"])
        self.assertAlmostEqual(0.0, regions[0]["v_min"], places=5)
        self.assertAlmostEqual(1.0, regions[-1]["v_max"], places=5)
        for lower, upper in zip(regions, regions[1:]):
            self.assertAlmostEqual(lower["v_max"], upper["v_min"], places=5,
                                   msg=f"{lower['id']} -> {upper['id']}")

    def test_v2_palette_feeds_every_band_it_declares(self) -> None:
        recipe = self._recipe("texture_citylab_trim_v2.json")
        palette = recipe["palette"]
        required = {
            "wood": ("wood", "wood_highlight", "iron"),
            "plank": ("plank", "plank_highlight"),
            "stone": ("stone", "mortar"),
            "brick": ("brick", "brick_mortar"),
            "roof": ("roof", "roof_highlight"),
            # La bande claire porte le panneau et son pan de bois : elle a donc
            # besoin des deux familles de couleur dans le meme rectangle.
            "plaster": ("plaster", "plaster_shade", "wood", "wood_highlight"),
        }
        for region in recipe["regions"]:
            for key in required[region["material"]]:
                self.assertIn(key, palette, f"{region['id']} exige la couleur {key}")

    def test_canonical_hash_reads_pixels_and_not_the_container(self) -> None:
        array = np.zeros((4, 4), dtype=np.float32)
        self.assertEqual(canonical_sha256(array), canonical_sha256(array.copy()))
        # Le clamp fait partie du canon : deux valeurs hors bornes se rejoignent.
        over = np.full((4, 4), 300.0, dtype=np.float32)
        self.assertEqual(canonical_sha256(over), canonical_sha256(np.full((4, 4), 255.0)))
        changed = array.copy()
        changed[0, 0] = 1.0
        self.assertNotEqual(canonical_sha256(array), canonical_sha256(changed))


class GrammarTests(unittest.TestCase):
    """Le style pilote-t-il vraiment la geometrie, hors Blender."""

    project_root = Path(__file__).resolve().parents[2]

    def setUp(self) -> None:
        self.style = load_style(self.project_root, "frontier")
        self.catalog = json.loads(
            (self.project_root / "AssetFactory/Catalogs/building_pilot.json")
            .read_text(encoding="utf-8"))
        self.family = {family["id"]: family for family in self.catalog["families"]}[
            "building_residence_frontier_01"]

    def _plan(self, variant: str, style: dict | None = None):
        return plan_building(style or self.style, self.family,
                             self.catalog["variants"], variant)

    def test_catalog_holds_the_programme_and_the_style_holds_the_look(self) -> None:
        for variant in self.catalog["variants"]:
            self.assertNotIn("palette", variant)
            self.assertIn(variant["palette_id"],
                          {palette["id"] for palette in self.style["palettes"]})
        for family in self.catalog["families"]:
            # Le quatrieme nombre a disparu : la hauteur de faitage est derivee.
            self.assertEqual(3, len(family["dimensions"]))
        self.assertEqual("frontier", self.catalog["style"])

    def test_ridge_height_is_derived_from_the_pitch_not_read_from_the_catalog(self) -> None:
        plan = self._plan("a")
        expected = math.tan(math.radians(plan.pitch_deg)) * (plan.half_span + plan.overhang)
        self.assertAlmostEqual(expected, plan.rise, places=6)
        self.assertAlmostEqual(plan.wall_top + plan.rise, plan.ridge_z, places=6)

    def test_a_shallower_pitch_range_restyles_every_family(self) -> None:
        shallow = json.loads(json.dumps(self.style))
        # La pente appartient au schema depuis le lot 003 : c'est la que le
        # resserrement doit se lire, sur toutes les familles a la fois.
        shallow["roof"]["pitch_deg"] = [12.0, 14.0]
        for form in shallow["scheme"]["forms"]:
            form["pitch_deg"] = [12.0, 14.0]
        for family in self.catalog["families"]:
            for variant in self.catalog["variants"]:
                steep = plan_building(self.style, family, self.catalog["variants"],
                                      variant["id"])
                flat = plan_building(shallow, family, self.catalog["variants"],
                                     variant["id"])
                self.assertLess(flat.rise, steep.rise, f"{family['id']}_{variant['id']}")

    def test_storey_height_follows_the_weighted_mean_of_the_declared_levels(self) -> None:
        forms = self.style["levels"]["forms"]
        weight = sum(form["weight"] for form in forms)
        mean = sum(LEVEL_STOREYS[form["id"]] * form["weight"] for form in forms) / weight
        self.assertAlmostEqual(5.2 / mean, storey_height(self.style, 5.2), places=9)

    def test_the_mass_is_stratified_across_the_variants_of_a_family(self) -> None:
        # L'emprise seule ne suffit plus a distinguer : le schema porte aussi les
        # niveaux, la base, l'encorbellement et la composition de toiture. C'est
        # la signature complete qui doit differer, et elle est plus exigeante que
        # l'emprise.
        signatures = {variant["id"]: self._plan(variant["id"]) for variant in self.catalog["variants"]}
        masses = {(plan.footprint_form, plan.level_form, plan.base_kind, plan.jetty,
                   plan.roof_composition)
                  for plan in signatures.values()}
        self.assertEqual(3, len(masses), sorted(masses))

    def test_every_family_keeps_three_distinct_masses(self) -> None:
        for family in self.catalog["families"]:
            masses = {(plan.footprint_form, plan.level_form, plan.base_kind,
                       plan.jetty, plan.roof_composition)
                      for plan in (plan_building(self.style, family,
                                                 self.catalog["variants"], variant["id"])
                                   for variant in self.catalog["variants"])}
            self.assertEqual(3, len(masses), family["id"])

    def test_stratified_picks_exhaust_the_pool_before_repeating(self) -> None:
        forms = [{"id": "one", "weight": 1}, {"id": "two", "weight": 1}]
        picks = stratified_picks(random.Random(7), forms, 4)
        self.assertEqual({"one", "two"}, set(picks[:2]))
        self.assertEqual({"one", "two"}, set(picks[2:]))

    def test_a_style_form_outside_the_vocabulary_is_refused_not_ignored(self) -> None:
        broken = json.loads(json.dumps(self.style))
        broken["footprint"]["forms"].append({"id": "dome", "weight": 1})
        with self.assertRaises(StyleError):
            plan_building(broken, self.family, self.catalog["variants"], "a")

    def test_the_plan_is_a_pure_function_of_the_seed(self) -> None:
        self.assertEqual(self._plan("b"), self._plan("b"))


class OpeningTests(unittest.TestCase):
    """Une fenetre est un trou avec de l'epaisseur, pas un decalcomanie."""

    project_root = Path(__file__).resolve().parents[2]

    def setUp(self) -> None:
        self.style = load_style(self.project_root, "frontier")
        self.catalog = json.loads(
            (self.project_root / "AssetFactory/Catalogs/building_pilot.json")
            .read_text(encoding="utf-8"))

    def _plans(self):
        for family in self.catalog["families"]:
            for variant in self.catalog["variants"]:
                yield plan_building(self.style, family, self.catalog["variants"],
                                    variant["id"])

    def test_every_building_has_its_door_on_the_ground(self) -> None:
        """L'entree est au sol, et le perron ne dessert qu'un seuil.

        La porte allait dans le premier niveau assez haut pour la contenir. Sous
        une base fruitee -- une jupe de 1,28 m puis un rez de pierre de 1,76 --
        aucune des deux assises n'atteignait le minimum de 2,0 m : la seule
        porte de `building_residence_frontier_01_c` partait a 3,61 m et un
        escalier de pierre de 5,70 m de long, plein sur toute sa hauteur, coupait
        la facade en deux. Une porte traverse les assises qu'elle recoupe ; ce
        sont des boites de modelisation, pas des etages.
        """
        maximum = float(self.style["scheme"]["appendage"]["stair"]["max_rise_m"])
        minimum = float(self.style["opening"]["door"]["min_height_m"])
        for plan in self._plans():
            doors = [item for item in plan.openings if item.kind == "door"]
            self.assertEqual(1, len(doors), plan.asset_id)
            door = doors[0]
            self.assertEqual(0, door.storey, plan.asset_id)
            self.assertAlmostEqual(plan.storeys[0].bottom, door.sill_z, places=9,
                                   msg=plan.asset_id)
            self.assertAlmostEqual(plan.foundation_height, door.sill_z, places=9,
                                   msg=plan.asset_id)
            self.assertGreaterEqual(door.height, minimum, plan.asset_id)
            self.assertLessEqual(door.sill_z + door.height, plan.storeys[-1].top,
                                 plan.asset_id)
            # Le perron franchit la fondation, jamais un etage.
            self.assertLessEqual(door.sill_z, maximum, plan.asset_id)

    def test_a_skirt_carries_no_window_and_never_lifts_the_door(self) -> None:
        """Une jupe de base fruitee est une assise, pas un niveau habitable.

        Elle ne recoit pas de fenetre : haute de 1,28 m, elle n'en contient
        aucune. La porte, elle, part de son pied -- c'est le sol -- et traverse
        les assises au-dessus. C'est cette assise qui avait fait monter la porte
        d'un etage : `_openings` la comptait comme un niveau candidat, la
        trouvait trop basse pour une porte de 2,0 m, et poussait la seule entree
        de la maison a 3,61 m.
        """
        seen = 0
        for plan in self._plans():
            skirts = {index for index, storey in enumerate(plan.storeys)
                      if storey.role == "skirt"}
            seen += len(skirts)
            for opening in plan.openings:
                if opening.kind == "window":
                    self.assertNotIn(opening.storey, skirts,
                                     f"{plan.asset_id} : fenetre posee sur une jupe")
            if 0 in skirts:
                door = next(item for item in plan.openings if item.kind == "door")
                self.assertGreater(door.sill_z + door.height,
                                   plan.storeys[0].top, plan.asset_id)
        self.assertGreater(seen, 0, "aucune base fruitee dans le pilote : test sans objet")

    def test_no_opening_pierces_above_the_wall_it_sits_in(self) -> None:
        for plan in self._plans():
            for opening in plan.openings:
                self.assertLessEqual(opening.sill_z + opening.height, plan.wall_top,
                                     f"{plan.asset_id}:{opening.kind}")

    def test_piers_between_openings_respect_the_style_minimum(self) -> None:
        minimum = float(self.style["opening"]["min_pier_m"])
        for plan in self._plans():
            # Le trumeau se mesure face par face et niveau par niveau : deux
            # baies sur deux murs differents ne se genent pas.
            rows: dict[tuple[int, str], list[tuple[float, float]]] = {}
            for item in plan.openings:
                rows.setdefault((item.storey, item.face), []).append(
                    (item.along - item.width * 0.5, item.along + item.width * 0.5))
            for (index, face), spans in rows.items():
                spans.sort()
                for (_, right), (left, _) in zip(spans, spans[1:]):
                    self.assertGreaterEqual(left - right, minimum - 1e-9,
                                            f"{plan.asset_id}@{index}.{face}")
                _, _, lo, hi = face_of(plan.storeys[index], face)
                self.assertGreaterEqual(spans[0][0] - lo, minimum - 1e-9,
                                        f"{plan.asset_id}@{index}.{face}")
                self.assertGreaterEqual(hi - spans[-1][1], minimum - 1e-9,
                                        f"{plan.asset_id}@{index}.{face}")

    def test_reveal_depth_stays_inside_the_style_range_and_the_wall(self) -> None:
        low, high = self.style["opening"]["reveal_depth_m"]
        for plan in self._plans():
            self.assertGreaterEqual(plan.reveal_depth, low)
            self.assertLessEqual(plan.reveal_depth, high)
            self.assertLess(plan.reveal_depth, plan.wall_thickness)

    def test_the_boolean_reached_the_front_wall_of_every_generated_variant(self) -> None:
        """Compter les boucles de bord, pas la presence d'un appel a l'operateur."""
        reports = sorted((self.project_root / "AssetFactory/Reports")
                         .glob("building_residence_frontier_01_*_metrics.json"))
        self.assertEqual(3, len(reports))
        for path in reports:
            gates = json.loads(path.read_text(encoding="utf-8"))["gates"]
            self.assertEqual(1, gates["front_wall_edge_loops_before_cut"], path.name)
            # Les boucles se comptent sur le niveau mesure : les comparer au
            # total des ouvertures exigerait de la facade du rez les percements
            # des etages.
            self.assertGreaterEqual(gates["front_wall_edge_loops"],
                                    gates["declared_openings_in_measured_face"],
                                    path.name)
            self.assertGreater(gates["declared_openings"], 1, path.name)


class SilhouetteGateTests(unittest.TestCase):
    project_root = Path(__file__).resolve().parents[2]

    def test_iou_reads_overlap_and_not_area(self) -> None:
        full = [True] * 16
        self.assertEqual(1.0, iou_masks(full, full))
        half = [True] * 8 + [False] * 8
        self.assertEqual(0.5, iou_masks(full, half))
        self.assertEqual(0.0, iou_masks(half, [False] * 8 + [True] * 8))
        with self.assertRaises(ValueError):
            iou_masks([False] * 4, [False] * 4)

    def test_the_three_residences_are_distinguishable_at_the_style_threshold(self) -> None:
        style = load_style(self.project_root, "frontier")
        report = json.loads((self.project_root / "AssetFactory/Reports/QA"
                             / "building_residence_frontier_01_silhouette.json")
                            .read_text(encoding="utf-8"))
        gate = style["silhouette_gate"]
        self.assertEqual(int(gate["render_px"]), report["render_px"])
        self.assertEqual(gate["camera"], report["camera"])
        self.assertEqual(float(gate["max_iou_same_family"]), report["max_iou_same_family"])
        self.assertEqual({"a-b", "a-c", "b-c"}, {row["pair"] for row in report["pairs"]})
        for row in report["pairs"]:
            self.assertLessEqual(row["iou"], float(gate["max_iou_same_family"]), row["pair"])

    def test_the_articulation_gate_is_open_only_on_declared_schemes(self) -> None:
        """Porte C-1 : fermee sur la residence, liste de dette vide.

        Le seuil est pose sous la plus sobre des deux references de style
        (6,17 ; l'autre vaut 7,41). Les trois variantes le franchissent. La
        dette ne peut que rester vide : un schema qui retombe sous le seuil
        sans y avoir ete declare est une erreur, et le seuil ne se deplace pas.
        """
        style = load_style(self.project_root, "frontier")
        report = json.loads((self.project_root / "AssetFactory/Reports/QA"
                             / "building_residence_frontier_01_silhouette.json")
                            .read_text(encoding="utf-8"))
        gate = style["silhouette_gate"]
        shape = report["articulation"]
        self.assertEqual(float(gate["min_articulation"]), shape["min_articulation"])
        debt = json.loads((self.project_root / "AssetFactory" / "Manifests"
                           / "silhouette_debt.json").read_text(encoding="utf-8"))

        catalog = json.loads((self.project_root / "AssetFactory/Catalogs"
                              / "building_pilot.json").read_text(encoding="utf-8"))
        family = next(item for item in catalog["families"]
                      if item["id"] == "building_residence_frontier_01")
        schemes = {variant["id"]: plan_building(style, family, catalog["variants"],
                                                variant["id"]).scheme_id
                   for variant in catalog["variants"]}
        below = {schemes[item["variant"]] for item in shape["variants"]
                 if not item["passed"]}
        declared = set(debt["schemes_below_threshold"])
        # La dette ne peut que retrecir : un schema qui tombe sous le seuil sans
        # y avoir ete declare est une erreur, et le seuil ne bouge pas.
        self.assertLessEqual(below, declared,
                             f"schema neuf sous le seuil C-1 : {sorted(below - declared)}")
        self.assertEqual(set(), below)
        self.assertEqual(set(), declared)
        self.assertTrue(all(item["passed"] for item in shape["variants"]))

    def test_the_spread_between_variants_is_observed_and_not_gated(self) -> None:
        """Porte C-2 : supprimee par le proprietaire le 2026-08-29.

        Elle exigeait que les trois variantes different assez -- etendue
        d'articulation >= 0,80 -- pendant que C-1 exige que chacune soit assez
        articulee. Ameliorer les plus faibles les rapproche des fortes : les
        deux exigences se sont contredites cinq fois de suite, et aucun element
        de vocabulaire ne les reconciliait.

        Ce test garde la decision. L'etendue reste **mesuree et consignee** --
        une famille dont l'etendue s'effondre a quelque chose a dire -- mais
        elle ne prononce plus de verdict, et le style ne porte plus de seuil.
        La remettre est une decision du proprietaire, pas un reglage.
        """
        style = load_style(self.project_root, "frontier")
        self.assertNotIn("min_articulation_spread", style["silhouette_gate"])
        report = json.loads((self.project_root / "AssetFactory/Reports/QA"
                             / "building_residence_frontier_01_silhouette.json")
                            .read_text(encoding="utf-8"))
        shape = report["articulation"]
        self.assertIn("observed_spread", shape)
        for verdict in ("min_spread", "spread_passed", "spread"):
            self.assertNotIn(verdict, shape)
        debt = json.loads((self.project_root / "AssetFactory" / "Manifests"
                           / "silhouette_debt.json").read_text(encoding="utf-8"))
        self.assertIn("c2_removed", debt)
        self.assertNotIn("spread_threshold", debt)
        source = (self.project_root / "Tools/AssetFactory/silhouette_gate.py"
                  ).read_text(encoding="utf-8")
        self.assertNotIn("min_articulation_spread", source)


class ExportMatterTests(unittest.TestCase):
    """Ce qui atteint le FBX : des cartes, pas du bruit procedural."""

    project_root = Path(__file__).resolve().parents[2]

    def _metrics(self) -> list[dict]:
        return [json.loads(path.read_text(encoding="utf-8"))
                for path in sorted((self.project_root / "AssetFactory/Reports")
                                   .glob("building_residence_frontier_01_*_metrics.json"))]

    def test_no_procedural_material_survives_in_the_export_path(self) -> None:
        for metrics in self._metrics():
            self.assertEqual([], metrics["gates"]["procedural_material_nodes"],
                             metrics["id"])

    def test_no_uv_loop_leaves_the_unit_square(self) -> None:
        for metrics in self._metrics():
            self.assertEqual(0, metrics["gates"]["uv_loops_outside_unit"], metrics["id"])

    def test_every_lod_stays_inside_the_budget_its_style_class_declares(self) -> None:
        style = load_style(self.project_root, "frontier")
        for metrics in self._metrics():
            budget = style["budget"]["classes"][metrics["budget"]["class"]]["lod"]
            self.assertEqual(list(budget), metrics["budget"]["lod"], metrics["id"])
            actual = [metrics["triangles"][key] for key in ("lod0", "lod1", "lod2")]
            for value, maximum in zip(actual, budget):
                self.assertLessEqual(value, maximum, f"{metrics['id']}:{actual}")

    STAGE_VOCABULARY = ("groundworks", "basecourse", "framing", "floors",
                        "carpentry", "roofing", "joinery", "finishes")

    def _all_metrics(self) -> list[dict]:
        catalog = json.loads((self.project_root / "AssetFactory/Catalogs"
                              / "building_pilot.json").read_text(encoding="utf-8"))
        return [
            json.loads((self.project_root / "AssetFactory/Reports"
                        / f"{family['id']}_{variant['id']}_metrics.json")
                       .read_text(encoding="utf-8"))
            for family in catalog["families"]
            for variant in catalog["variants"]
        ]

    def test_a_scheme_reaches_only_the_functions_it_declares(self) -> None:
        """Le vocabulaire de masse n'est plus entierement domestique.

        Chaumiere, maison a rez de pierre, maison a encorbellement, maison de
        ville : les six schemas d'origine sont des maisons, et les sept familles
        y puisaient sans filtre. La mesure etait sans appel --
        `building_chapel_frontier_01_a` tirait `town_house` et sortait une
        chapelle **a encorbellement a chaque etage, avec deux lucarnes** ; la
        grange et le grenier avaient le leur.

        Un schema declare desormais son public : `any` pour une masse que tout
        le monde peut prendre, `domestic` pour l'encorbellement et la maison de
        ville, `utility` pour la halle. Une fonction d'habitat ne prend pas de
        halle, et une chapelle ne prend pas d'encorbellement.
        """
        style = load_style(self.project_root, "frontier")
        domestic = set(style["scheme"]["domestic_functions"])
        self.assertTrue(domestic, "aucune fonction domestique declaree")
        audiences = {str(form["id"]): str(form.get("audience", "any"))
                     for form in style["scheme"]["forms"]}
        self.assertEqual({"any", "domestic", "utility"}, set(audiences.values()))
        catalog = json.loads((self.project_root / "AssetFactory/Catalogs"
                              / "building_pilot.json").read_text(encoding="utf-8"))
        seen_utility = 0
        seen_domestic = 0
        for family in catalog["families"]:
            allowed = ({"any", "domestic"} if family["function"] in domestic
                       else {"any", "utility"})
            for variant in catalog["variants"]:
                plan = plan_building(style, family, catalog["variants"], variant["id"])
                audience = audiences[plan.scheme_id]
                self.assertIn(audience, allowed,
                              f"{plan.asset_id} : schema {plan.scheme_id} "
                              f"({audience}) hors du public de {family['function']}")
                seen_utility += audience == "utility"
                seen_domestic += audience == "domestic"
                if family["function"] not in domestic:
                    self.assertEqual("none", plan.jetty, plan.asset_id)
                    self.assertEqual(0.0, plan.jetty_overhang, plan.asset_id)
        self.assertGreater(seen_utility, 0, "aucune halle tiree dans le pilote")
        self.assertGreater(seen_domestic, 0, "aucun schema domestique tire")

    def test_every_family_still_draws_three_distinct_schemes(self) -> None:
        """Porte C-5, qu'un filtre par public pourrait casser en silence."""
        style = load_style(self.project_root, "frontier")
        catalog = json.loads((self.project_root / "AssetFactory/Catalogs"
                              / "building_pilot.json").read_text(encoding="utf-8"))
        for family in catalog["families"]:
            schemes = {plan_building(style, family, catalog["variants"],
                                     variant["id"]).scheme_id
                       for variant in catalog["variants"]}
            self.assertEqual(len(catalog["variants"]), len(schemes),
                             f"{family['id']} : {sorted(schemes)}")

    def test_every_declared_identity_marker_is_built(self) -> None:
        """Porte D-1 : ce que le catalogue declare, la geometrie le pose.

        Trente-huit marqueurs sont declares -- `arcade` pour le marche,
        `buttresses` et `lancet_windows` pour la chapelle, `cross_braced_doors`
        et `loft` pour la grange. Quatorze n'existaient pas, et c'etaient
        exactement ceux qui font qu'une grange n'est pas une chapelle : les sept
        familles etaient la meme maison.

        Le cas le plus net : `plan_building` retire les baies ordinaires des que
        `lancet_windows` est declare. Personne ne posait de lancette, donc la
        chapelle n'avait **aucune** ouverture et ses quatre murs etaient
        aveugles.
        """
        catalog = json.loads((self.project_root / "AssetFactory/Catalogs"
                              / "building_pilot.json").read_text(encoding="utf-8"))
        declared_by_family = {family["id"]: list(family["identity_markers"])
                              for family in catalog["families"]}
        seen = set()
        for metrics in self._all_metrics():
            family = metrics["family"]
            declared = declared_by_family[family]
            gates = metrics["gates"]
            self.assertEqual(declared, gates["identity_markers_declared"], metrics["id"])
            self.assertEqual(declared, gates["identity_markers_built"],
                             f"{metrics['id']} : marqueurs non poses "
                             f"{sorted(set(declared) - set(gates['identity_markers_built']))}")
            seen.update(declared)
        self.assertGreaterEqual(len(seen), 38,
                                "le vocabulaire de marqueurs a retreci")

    def test_every_marker_of_the_catalogue_has_a_builder(self) -> None:
        """Le registre du generateur couvre tout ce que le catalogue declare.

        Le generateur tourne dans Blender, hors du paquet : ce test lit son
        source plutot que de l'importer.
        """
        catalog = json.loads((self.project_root / "AssetFactory/Catalogs"
                              / "building_pilot.json").read_text(encoding="utf-8"))
        source = (self.project_root
                  / "Tools/AssetFactory/Blender/generate_building_family.py"
                  ).read_text(encoding="utf-8")
        for family in catalog["families"]:
            for name in family["identity_markers"]:
                self.assertIn(f'@marker("{name}")', source,
                              f"{family['id']} : {name} sans constructeur")

    def test_a_chapel_is_not_blind(self) -> None:
        """La chapelle a des baies. C'est le defaut que D-1 a revele.

        Ses fenetres ordinaires sont retirees par le plan au profit des
        lancettes ; sans lancettes elle n'avait rien du tout.
        """
        for metrics in self._all_metrics():
            if metrics["function"] != "chapel":
                continue
            categories = metrics["category_triangles"]
            self.assertGreater(categories.get("opening_plane", 0), 0, metrics["id"])

    def test_the_publication_budget_comes_from_the_style(self) -> None:
        """La porte de publication doit contraindre ce que le style declare.

        Elle lisait `catalog.budgets.lod_triangles_max`, un plafond a plat de
        60 000 / 30 000 / 12 000 ecrit apres coup. Le style declare
        4 000 / 1 800 / 600 par classe -- quinze fois moins. La publication a
        donc laisse passer les vingt et un batiments a 37 000-50 000 triangles
        qui ont ete refuses visuellement : elle ne contraignait rien.
        """
        catalog = json.loads((self.project_root / "AssetFactory/Catalogs"
                              / "building_pilot.json").read_text(encoding="utf-8"))
        self.assertNotIn("budgets", catalog,
                         "le plafond a plat du catalogue est revenu")
        style = load_style(self.project_root, catalog["style"])
        source = (self.project_root / "Tools/AssetFactory/publish_building_pilot.py"
                  ).read_text(encoding="utf-8")
        self.assertNotIn("lod_triangles_max\"]", source)
        for family in catalog["families"]:
            budget = family_budget(style, family["function"])
            class_name = style["budget"]["function_class"][family["function"]]
            self.assertEqual(style["budget"]["classes"][class_name]["lod"], budget,
                             family["id"])
            for variant in catalog["variants"]:
                metrics = json.loads(
                    (self.project_root / "AssetFactory/Reports"
                     / f"{family['id']}_{variant['id']}_metrics.json")
                    .read_text(encoding="utf-8"))
                actual = [metrics["triangles"][key] for key in ("lod0", "lod1", "lod2")]
                for value, maximum in zip(actual, budget):
                    self.assertLessEqual(value, maximum,
                                         f"{metrics['id']}:{actual} pour {budget}")

    def test_the_construction_vocabulary_matches_the_contract(self) -> None:
        """Le vocabulaire est duplique dans le generateur Blender, qui tourne
        hors du paquet. Les deux doivent dire la meme chose."""
        schema = json.loads(
            (self.project_root / "AssetFactory/Schemas/building_construction_v2.schema.json")
            .read_text(encoding="utf-8"))
        self.assertEqual(list(self.STAGE_VOCABULARY),
                         schema["$defs"]["stage_id"]["enum"])
        source = (self.project_root
                  / "Tools/AssetFactory/Blender/generate_building_family.py"
                  ).read_text(encoding="utf-8")
        for stage in self.STAGE_VOCABULARY:
            self.assertIn(f'"{stage}"', source, stage)

    def test_every_declared_stage_carries_geometry_at_lod0(self) -> None:
        """Invariant I1 du contrat v2.

        Une etape peut manquer a un LOD lointain -- il n'y a pas de menuiserie
        lisible a 96 px -- mais une etape declaree porte de la geometrie.
        """
        for metrics in self._metrics():
            stages = metrics["construction"]["stages"]
            self.assertGreaterEqual(len(stages), 5, metrics["id"])
            for stage in stages:
                self.assertIn(stage["id"], self.STAGE_VOCABULARY, metrics["id"])
                self.assertGreater(stage["lod0"], 0,
                                   f"{metrics['id']}:{stage['id']}")

    def test_the_stages_follow_the_vocabulary_order_without_renumbering(self) -> None:
        """Le rang d'une etape est sa place dans le vocabulaire, pas dans la
        liste : c'est lui qui nomme le nœud du FBX, et l'hote lit ce nom."""
        for metrics in self._metrics():
            previous = 0
            for stage in metrics["construction"]["stages"]:
                order = self.STAGE_VOCABULARY.index(stage["id"]) + 1
                self.assertEqual(order, stage["order"], metrics["id"])
                self.assertGreater(order, previous, metrics["id"])
                previous = order
                self.assertTrue(
                    stage["node_prefix"].endswith(
                        f"__S{order:02d}_{stage['id'].upper()}"),
                    stage["node_prefix"])

    def test_the_stages_sum_to_the_whole_building_at_every_lod(self) -> None:
        """Invariant I3 : l'union des etapes egale le batiment complet."""
        for metrics in self._metrics():
            for lod in ("lod0", "lod1", "lod2"):
                total = sum(stage[lod] for stage in metrics["construction"]["stages"])
                self.assertEqual(metrics["triangles"][lod], total,
                                 f"{metrics['id']}:{lod}")

    def test_the_cumulative_stages_never_remove_geometry(self) -> None:
        """Invariant I2 : une etape ajoute, elle ne retire jamais."""
        for metrics in self._metrics():
            for lod in ("lod0", "lod1", "lod2"):
                running = 0
                for stage in metrics["construction"]["stages"]:
                    self.assertGreaterEqual(stage[lod], 0,
                                            f"{metrics['id']}:{stage['id']}:{lod}")
                    running += stage[lod]
                self.assertEqual(metrics["triangles"][lod], running,
                                 f"{metrics['id']}:{lod}")

    def test_no_stage_holds_more_than_half_the_budget(self) -> None:
        """Le decoupage doit montrer un chantier, pas deux gros paquets.

        Le contrat v1 avait quatre phases et l'ossature en portait 1 284 sur
        3 024 : un mur entier apparaissait a la deuxieme image. Sous le contrat
        v2, aucune etape ne depasse la moitie du LOD0.
        """
        for metrics in self._metrics():
            total = metrics["triangles"]["lod0"]
            for stage in metrics["construction"]["stages"]:
                self.assertLessEqual(stage["lod0"], total * 0.5,
                                     f"{metrics['id']}:{stage['id']}")

    def test_lod_removal_beats_decimation_on_every_variant(self) -> None:
        for metrics in self._metrics():
            triangles = metrics["triangles"]
            self.assertLess(triangles["lod1"], triangles["lod0"], metrics["id"])
            self.assertLess(triangles["lod2"], triangles["lod1"], metrics["id"])


class StyleTests(unittest.TestCase):
    project_root = Path(__file__).resolve().parents[2]

    def _style(self) -> dict:
        return json.loads((self.project_root / "AssetFactory" / "Styles" / "frontier.json")
                          .read_text(encoding="utf-8"))

    def _catalog(self) -> dict:
        return json.loads((self.project_root / "AssetFactory" / "Catalogs" / "building_pilot.json")
                          .read_text(encoding="utf-8"))

    def _atlas_recipe(self) -> dict:
        # La recette de reference est celle que le style declare : depuis le lot
        # 003 c'est v2, qui porte la bande claire.
        atlas = self._style()["trim"]["atlas"]
        return json.loads((self.project_root / "AssetFactory" / "Recipes"
                           / f"texture_{atlas}.json").read_text(encoding="utf-8"))

    def test_frontier_style_is_valid_and_covers_the_building_catalog(self) -> None:
        style = self._style()
        self.assertEqual([], validate_style(style))
        self.assertEqual([], validate_style_against_atlas(style, self._atlas_recipe()))
        self.assertEqual([], validate_style_against_catalog(style, self._catalog()))
        self.assertEqual("element_removal", style["lod"]["policy"])
        self.assertGreater(style["budget"]["classes"]["hero"]["lod"][0],
                           style["budget"]["classes"]["standard"]["lod"][0])

    def test_style_records_its_atlas_debt_as_data(self) -> None:
        wall_map = self._style()["trim"]["wall_system_map"]
        indebted = {system for system, mapping in wall_map.items() if "requires_atlas" in mapping}
        # La dette est soldee depuis que le style est passe sur citylab_trim_v2 :
        # chaque systeme de mur a sa propre bande.
        self.assertEqual(set(), indebted)
        for system in indebted:
            self.assertEqual("citylab_trim_v2", wall_map[system]["requires_atlas"])

    def test_every_declared_atlas_debt_names_an_existing_recipe(self) -> None:
        for system, mapping in self._style()["trim"]["wall_system_map"].items():
            debt = mapping.get("requires_atlas")
            if not debt:
                continue
            recipe = self.project_root / "AssetFactory" / "Recipes" / f"texture_{debt}.json"
            self.assertTrue(recipe.is_file(), f"{system} reclame {debt} sans recette")

    def test_style_validator_rejects_overlapping_trim_bands(self) -> None:
        style = self._style()
        # La bande de pierre remonte sur celle des planches sciees.
        style["trim"]["rects"]["dressed_stone"]["v"] = [0.25, 0.666667]
        self.assertIn("bandes_trim_superposees:sawn_planks+dressed_stone",
                      validate_style(style))

    def test_style_validator_rejects_a_budget_that_does_not_decrease(self) -> None:
        style = self._style()
        style["budget"]["classes"]["standard"]["lod"] = [4000, 4000, 600]
        self.assertIn("budget_lod_non_decroissant:standard", validate_style(style))

    def test_style_validator_refuses_a_return_to_blind_decimation(self) -> None:
        style = self._style()
        style["lod"]["policy"] = "decimate"
        self.assertIn("politique_lod_invalide", validate_style(style))

    def test_style_validator_rejects_a_wall_system_without_matter(self) -> None:
        style = self._style()
        style["trim"]["wall_system_map"]["stone_timber"]["body"] = "absente"
        self.assertIn("mur_sans_bande:stone_timber.body", validate_style(style))

    def test_style_validator_rejects_an_unreachable_silhouette_threshold(self) -> None:
        style = self._style()
        style["silhouette_gate"]["max_iou_same_family"] = 1.4
        self.assertIn("seuil_iou_invalide:max_iou_same_family", validate_style(style))

    def test_style_rejects_a_band_the_atlas_does_not_produce(self) -> None:
        style = self._style()
        style["trim"]["rects"]["absente_de_l_atlas"] = {"u": [0.0, 1.0], "v": [0.0, 0.1]}
        self.assertIn("bande_absente_de_atlas:absente_de_l_atlas",
                      validate_style_against_atlas(style, self._atlas_recipe()))

    def test_style_rejects_a_band_shifted_against_the_atlas(self) -> None:
        style = self._style()
        style["trim"]["rects"]["roof_tiles"]["v"] = [0.70, 1.0]
        self.assertIn("bande_decalee:roof_tiles",
                      validate_style_against_atlas(style, self._atlas_recipe()))

    def test_style_rejects_a_family_left_without_matter_or_budget(self) -> None:
        style = self._style()
        del style["trim"]["wall_system_map"]["dressed_stone"]
        del style["budget"]["function_class"]["chapel"]
        errors = validate_style_against_catalog(style, self._catalog())
        self.assertIn("mur_non_couvert:building_chapel_frontier_01", errors)
        self.assertIn("fonction_non_budgetee:building_chapel_frontier_01", errors)


class UnityMatterGateTests(unittest.TestCase):
    """The gate that would have caught M1-ASSET-06 at the place it showed.

    The 21 buildings passed every technical gate and both Unity EditMode suites
    and were still refused on sight. Nothing ever read what the published Unity
    data says about matter, so nothing could fail.
    """

    project_root = Path(__file__).resolve().parents[2]

    def _material(self, slots: dict) -> str:
        body = ["Material:", "  m_SavedProperties:", "    m_TexEnvs:"]
        for slot, guid in slots.items():
            reference = "{fileID: 0}" if guid is None else f"{{fileID: 2800000, guid: {guid}, type: 3}}"
            body += [f"    - {slot}:", f"        m_Texture: {reference}",
                     "        m_Scale: {x: 1, y: 1}"]
        return "\n".join(body) + "\n"

    def _meta(self, guid: str, srgb: int, texture_type: int) -> str:
        return (f"fileFormatVersion: 2\nguid: {guid}\nTextureImporter:\n"
                f"  mipmaps:\n    sRGBTexture: {srgb}\n"
                f"  textureType: {texture_type}\n")

    def test_a_slot_left_at_fileid_zero_is_not_a_texture(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "flat.mat"
            path.write_text(self._material({"_BaseMap": None, "_BumpMap": None}), encoding="utf-8")
            self.assertEqual({}, material_maps(path))
            path.write_text(self._material({"_BaseMap": "a" * 32, "_BumpMap": None}), encoding="utf-8")
            self.assertEqual({"_BaseMap": "a" * 32}, material_maps(path))

    def test_import_settings_are_read_and_default_to_the_unsafe_side(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            meta = Path(temp_dir) / "CityLabTrim_Normal.png.meta"
            meta.write_text(self._meta("b" * 32, 0, 1), encoding="utf-8")
            self.assertEqual({"sRGB": 0, "texture_type": 1}, texture_import(meta))
            meta.write_text("fileFormatVersion: 2\n", encoding="utf-8")
            self.assertEqual({"sRGB": 1, "texture_type": 0}, texture_import(meta))

    def _tree(self, temp_dir: str, *, textured: bool, correct_import: bool) -> Path:
        root = Path(temp_dir)
        materials = root / MATERIALS_DIR
        materials.mkdir(parents=True, exist_ok=True)
        guids = {role: f"{index:032x}" for index, role in enumerate(sorted(TRIM_MAP_IMPORT), 1)}
        for folder in TRIM_DIRS:
            target = root / folder
            target.mkdir(parents=True, exist_ok=True)
            for role, (srgb, kind) in TRIM_MAP_IMPORT.items():
                meta = target / f"CityLabTrim_{role}.png.meta"
                meta.write_text(
                    self._meta(guids[role], srgb if correct_import else 1,
                               kind if correct_import else 0),
                    encoding="utf-8")
        slots = {"_BaseMap": guids["BaseColor"] if textured else None,
                 "_BumpMap": guids["Normal"] if textured else None}
        (materials / "wall_stone.mat").write_text(self._material(slots), encoding="utf-8")
        return root

    def test_a_correct_publication_raises_no_violation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = matter_audit(self._tree(temp_dir, textured=True, correct_import=True))
            self.assertEqual([], report["violations"])
            self.assertEqual(1, report["materials"]["textured"])
            self.assertEqual(["BaseColor", "Normal"], report["materials"]["detail"][0]["atlas_roles"])
            self.assertEqual(report["trim_imports"]["checked"], report["trim_imports"]["passed"])

    def test_a_flat_material_and_a_miscoloured_map_both_fail_when_undeclared(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = matter_audit(self._tree(temp_dir, textured=False, correct_import=False))
            self.assertEqual(0, report["materials"]["textured"])
            joined = " ".join(report["violations"])
            self.assertIn("M-1:undeclared_flat_materials:wall_stone", joined)
            self.assertIn("M-2:undeclared_miscoloured_maps:", joined)
            # BaseColor porte de la couleur : sRGB reste correct meme dans l'arbre casse.
            self.assertNotIn("CityLabTrim_BaseColor", joined)
            self.assertIn("CityLabTrim_Normal", joined)

    def test_a_declared_debt_silences_the_violation_but_never_a_new_one(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._tree(temp_dir, textured=False, correct_import=False)
            declare_debt(root, allow_growth=True)
            self.assertEqual([], matter_audit(root)["violations"])

            regression = root / MATERIALS_DIR / "roof_tile.mat"
            regression.write_text(self._material({"_BaseMap": None}), encoding="utf-8")
            violations = " ".join(matter_audit(root)["violations"])
            self.assertIn("M-1:undeclared_flat_materials:roof_tile", violations)
            self.assertNotIn("wall_stone", violations)

    def test_a_repaired_material_is_reported_as_cleared_debt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._tree(temp_dir, textured=False, correct_import=False)
            declare_debt(root, allow_growth=True)
            self._tree(temp_dir, textured=True, correct_import=True)
            report = matter_audit(root)
            self.assertEqual([], report["violations"])
            self.assertEqual(0, report["debt"]["still_owed"])
            self.assertIn("wall_stone", report["debt"]["cleared_since_declaration"])

    def test_the_debt_declaration_refuses_to_absorb_a_new_violation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._tree(temp_dir, textured=False, correct_import=False)
            declare_debt(root, allow_growth=True)

            (root / MATERIALS_DIR / "roof_tile.mat").write_text(
                self._material({"_BaseMap": None}), encoding="utf-8")
            with self.assertRaises(DebtGrowth):
                declare_debt(root)
            # La dette n'a pas bouge : le refus precede l'ecriture.
            self.assertNotIn("roof_tile", json.loads(
                (root / DEBT_MANIFEST).read_text(encoding="utf-8"),
            )["m1_materials_without_any_texture"])

    def test_a_repaired_debt_shrinks_when_it_is_declared_again(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._tree(temp_dir, textured=False, correct_import=False)
            declare_debt(root, allow_growth=True)
            self._tree(temp_dir, textured=True, correct_import=True)
            declared = declare_debt(root)
            self.assertEqual([], declared["m1_materials_without_any_texture"])
            self.assertEqual([], declared["m2_trim_maps_in_the_wrong_colour_space"])

    def test_the_published_factory_owes_exactly_the_debt_it_declares(self) -> None:
        report = matter_audit(self.project_root)
        self.assertEqual([], report["violations"],
                         "une violation matiere hors dette declaree est un echec de lot")
        self.assertLessEqual(report["debt"]["still_owed"],
                             report["debt"]["declared_materials"] + report["debt"]["declared_trim_maps"])
        self.assertGreater(report["materials"]["published"], 0)
        # Six cartes par atlas publie : v1, v2 et la copie du package. La porte
        # doit couvrir chaque exemplaire -- deux copies identiques au sha256 pres
        # divergeraient en silence si une seule etait controlee.
        self.assertEqual(18, report["trim_imports"]["checked"],
                         "trois jeux de six cartes de trim sont publies")
        self.assertEqual(report["trim_imports"]["checked"],
                         report["trim_imports"]["passed"],
                         report["trim_imports"]["failed"])


class FbxEvidenceFreshnessTests(unittest.TestCase):
    """Un rapport de rechargement ne vaut que pour le FBX qu'il a ouvert.

    Les rapports `AssetFactory/Reports/QA/Fbx/*.json` sont lus comme preuve par
    la porte de release, et rien dans le depot ne les produisait : ils dataient
    d'une execution manuelle. La residence a ete regeneree en phase A sans que
    ses trois rapports bougent, et la porte est restee verte sur eux.
    """

    project_root = Path(__file__).resolve().parents[2]

    def test_a_report_that_pins_the_published_fbx_is_fresh(self) -> None:
        reports = [{"id": "building_x_a", "fbx_sha256": "aa"}]
        self.assertEqual([], stale_reports(reports, {"building_x_a": "aa"}))

    def test_a_report_left_behind_by_a_regeneration_is_refused(self) -> None:
        reports = [{"id": "building_x_a", "fbx_sha256": "aa"},
                   {"id": "building_x_b", "fbx_sha256": "bb"}]
        self.assertEqual(["building_x_a"],
                         stale_reports(reports, {"building_x_a": "zz", "building_x_b": "bb"}))

    def test_a_report_from_before_the_producer_is_stale_by_construction(self) -> None:
        self.assertEqual(["building_x_a"],
                         stale_reports([{"id": "building_x_a"}], {"building_x_a": "aa"}))

    def test_every_published_fbx_report_names_the_fbx_it_opened(self) -> None:
        reports = sorted((self.project_root / "AssetFactory/Reports/QA/Fbx").glob("*.json"))
        self.assertEqual(56, len(reports))
        for path in reports:
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(2, payload["schema"], path.name)
            self.assertEqual(
                sha256_file(self.project_root / payload["fbx"]), payload["fbx_sha256"],
                path.name)
            self.assertEqual("passed", payload["status"], path.name)


class ConstructionSchemeTests(unittest.TestCase):
    """La variation doit venir de la masse, pas d'un jitter de dimensions.

    La porte A-8 a ete refusee sur ce point : trois variantes de meme
    complexite, mesurees entre 5,02 et 5,44 d'articulation contre 6,17 et 7,41
    pour les references de style, et une etendue de 0,42 entre elles.
    """

    project_root = Path(__file__).resolve().parents[2]

    def _style(self) -> dict:
        return load_style(self.project_root, "frontier")

    def _catalog(self) -> dict:
        return json.loads((self.project_root / "AssetFactory" / "Catalogs"
                           / "building_pilot.json").read_text(encoding="utf-8"))

    def _plans(self, family_id: str) -> list:
        style, catalog = self._style(), self._catalog()
        family = next(item for item in catalog["families"] if item["id"] == family_id)
        return [plan_building(style, family, catalog["variants"], variant["id"])
                for variant in catalog["variants"]]

    def test_every_family_draws_three_distinct_schemes(self) -> None:
        for family in self._catalog()["families"]:
            schemes = {plan.scheme_id for plan in self._plans(family["id"])}
            self.assertEqual(3, len(schemes), f"{family['id']} : {sorted(schemes)}")

    def test_a_scheme_fixes_the_mass_and_a_finish_never_touches_it(self) -> None:
        style, catalog = self._style(), self._catalog()
        family = next(item for item in catalog["families"]
                      if item["id"] == "building_residence_frontier_01")
        reference = plan_building(style, family, catalog["variants"], "a")

        # Changer une bande de finition ne doit deplacer aucun niveau.
        altered = json.loads(json.dumps(style))
        for form in altered["finish"]["forms"]:
            form["upper"] = "structural_wood"
        moved = plan_building(altered, family, catalog["variants"], "a")
        self.assertEqual([(s.bottom, s.height, s.x0, s.x1, s.y0, s.y1)
                          for s in reference.storeys],
                         [(s.bottom, s.height, s.x0, s.x1, s.y0, s.y1)
                          for s in moved.storeys])
        self.assertNotEqual(reference.upper_band, moved.upper_band)

    def test_a_storey_base_is_a_level_and_not_a_thicker_plinth(self) -> None:
        plans = {plan.scheme_id: plan for plan in
                 self._plans("building_residence_frontier_01")}
        stone = [plan for plan in plans.values() if plan.base_kind in STOREY_BASES]
        self.assertTrue(stone, "aucun schema a rez-de-chaussee en pierre")
        for plan in stone:
            ground = plan.storeys[0]
            self.assertEqual("stone", ground.kind, plan.scheme_id)
            # Un soubassement valait 0,45 a 0,70 m ; un niveau vaut une hauteur
            # d'etage. C'est ce qui porte l'empilement de matieres.
            self.assertGreater(plan.base_storey_height, plan.storey_m * 0.7,
                               plan.scheme_id)

    def test_a_jetty_makes_a_storey_overhang_the_one_below(self) -> None:
        plans = [plan for plan in self._plans("building_residence_frontier_01")
                 if plan.jetty != "none"]
        self.assertTrue(plans, "aucun schema a encorbellement")
        for plan in plans:
            walls = [storey for storey in plan.storeys if storey.kind == "wall"]
            self.assertTrue(any(storey.y0 < plan.depth * -0.5 - 1e-6 for storey in walls),
                            f"{plan.scheme_id} : aucun niveau ne deborde")
            self.assertGreater(plan.jetty_overhang, 0.0, plan.scheme_id)

    def test_each_opening_carries_the_facade_of_its_own_storey(self) -> None:
        for plan in self._plans("building_residence_frontier_01"):
            for opening in plan.openings:
                storey = plan.storeys[opening.storey]
                _, plane, lo, hi = face_of(storey, opening.face)
                self.assertAlmostEqual(plane, opening.plane, places=6,
                                       msg=f"{plan.scheme_id} : {opening.face} hors du plan")
                self.assertGreaterEqual(opening.along, lo - 1e-6, plan.scheme_id)
                self.assertLessEqual(opening.along, hi + 1e-6, plan.scheme_id)

    def test_every_face_of_every_storey_carries_openings(self) -> None:
        """Une facade aveugle se voit immediatement.

        Trois faces sur quatre n'en portaient aucune : toutes les baies etaient
        posees sur un seul mur, et la densite tombait a 2,6 fenetres pour 100 m2
        la ou les references en alignent trois a quatre par niveau et par face.
        """
        for plan in self._plans("building_residence_frontier_01"):
            faces = {opening.face for opening in plan.openings}
            self.assertEqual(set(FACES), faces,
                             f"{plan.scheme_id} : faces aveugles "
                             f"{sorted(set(FACES) - faces)}")

    def test_a_stone_storey_opens_less_than_the_timber_ones(self) -> None:
        for plan in self._plans("building_residence_frontier_01"):
            per_storey = {index: 0 for index in range(len(plan.storeys))}
            for opening in plan.openings:
                if opening.kind == "window":
                    per_storey[opening.storey] += 1
            stone = [index for index, storey in enumerate(plan.storeys)
                     if storey.kind == "stone"]
            timber = [index for index, storey in enumerate(plan.storeys)
                      if storey.kind == "wall"]
            if not stone or not timber:
                continue
            # Un soubassement porteur s'ouvre moins : c'est ce que montrent les
            # deux references.
            self.assertLess(max(per_storey[i] for i in stone),
                            max(per_storey[i] for i in timber), plan.scheme_id)

    def test_two_variants_never_share_a_finish_while_the_style_offers_enough(self) -> None:
        for family in self._catalog()["families"]:
            finishes = {plan.finish_id for plan in self._plans(family["id"])}
            allowed = (self._style()["trim"]["wall_system_map"][family["wall_system"]]
                       .get("finishes") or [])
            self.assertEqual(min(3, len(allowed)), len(finishes), family["id"])

    def test_the_plan_stays_a_pure_function_of_the_seed(self) -> None:
        first = self._plans("building_residence_frontier_01")
        second = self._plans("building_residence_frontier_01")
        for left, right in zip(first, second):
            self.assertEqual(left, right)


class SilhouetteMeasureTests(unittest.TestCase):
    """L'articulation doit mesurer une forme, pas un cadrage."""

    def _rectangle(self, size: int, width: int, height: int,
                   extras: list[tuple[int, int]] | None = None) -> list[bool]:
        mask = [False] * (size * size)
        x0 = (size - width) // 2
        y0 = (size - height) // 2
        for y in range(y0, y0 + height):
            for x in range(x0, x0 + width):
                mask[y * size + x] = True
        for x, y in (extras or []):
            mask[y * size + x] = True
        return mask

    def test_a_box_scores_near_four_and_a_ragged_shape_scores_higher(self) -> None:
        box = articulation(self._rectangle(64, 30, 30), 64)
        self.assertLess(box, 5.0)
        teeth = [(x, 16) for x in range(18, 46, 2)]
        ragged = articulation(self._rectangle(64, 30, 30, teeth), 64)
        self.assertGreater(ragged, box)

    def test_the_same_shape_scores_the_same_at_two_framings(self) -> None:
        tight = articulation(self._rectangle(64, 40, 24), 64)
        loose = articulation(self._rectangle(64, 20, 12), 64)
        # Sans normalisation ces deux mesures differaient de plus d'un point :
        # la mesure suivait le remplissage du cadre et non la forme.
        self.assertAlmostEqual(tight, loose, delta=0.6)

    def test_an_empty_silhouette_is_refused_and_not_scored_zero(self) -> None:
        with self.assertRaises(ValueError):
            articulation([False] * (64 * 64), 64)


class RoofLoadPathTests(unittest.TestCase):
    """Un batiment est un chemin de charge, pas une pile de volumes independants.

    Le proprietaire a refuse le lot 003 sur ce point : deux triangles de pignon
    et une couverture qui ne reposait pas dessus. La cause etait mesurable --
    charpente et couverture etaient calculees depuis deux emprises differentes.
    Sur la maison de ville, encorbellee, l'ecart valait 2,05 m de portee et
    0,51 m de decalage de centre.
    """

    project_root = Path(__file__).resolve().parents[2]

    def _plans(self, family_id: str = "building_residence_frontier_01") -> list:
        style = load_style(self.project_root, "frontier")
        catalog = json.loads((self.project_root / "AssetFactory" / "Catalogs"
                              / "building_pilot.json").read_text(encoding="utf-8"))
        family = next(item for item in catalog["families"] if item["id"] == family_id)
        return [plan_building(style, family, catalog["variants"], variant["id"])
                for variant in catalog["variants"]]

    def test_the_roof_envelope_covers_the_storey_it_rests_on(self) -> None:
        for plan in self._plans():
            frames = [f for f in (plan.roof_frame, plan.roof_frame_high) if f is not None]
            top = plan.top_storey
            self.assertTrue(frames, plan.asset_id)
            # C'est l'**union** des volees qui est le niveau du haut, exactement :
            # ni l'emprise nominale du catalogue, ni un rectangle centre sur
            # l'origine. Un decrochement de faitage partage le meme niveau en
            # deux volees ; aucune ne doit deborder ni laisser de trou.
            self.assertAlmostEqual(top.x0, min(f.x0 for f in frames), places=9,
                                   msg=plan.asset_id)
            self.assertAlmostEqual(top.x1, max(f.x1 for f in frames), places=9,
                                   msg=plan.asset_id)
            self.assertAlmostEqual(top.y0, min(f.y0 for f in frames), places=9,
                                   msg=plan.asset_id)
            self.assertAlmostEqual(top.y1, max(f.y1 for f in frames), places=9,
                                   msg=plan.asset_id)
            covered = sum((f.x1 - f.x0) * (f.y1 - f.y0) for f in frames)
            self.assertAlmostEqual(top.width * top.depth, covered, places=6,
                                   msg=f"{plan.asset_id} : volees qui se recouvrent ou laissent un trou")
            # La volee basse repose sur le mur ; la haute monte d'un cran.
            self.assertAlmostEqual(plan.wall_top, plan.roof_frame.eave_z, places=9,
                                   msg=plan.asset_id)
            if plan.roof_frame_high is not None:
                self.assertGreater(plan.roof_frame_high.eave_z, plan.roof_frame.eave_z,
                                   plan.asset_id)

    def test_the_covering_rests_on_the_rafters_and_never_inside_them(self) -> None:
        for plan in self._plans():
            frame = plan.roof_frame
            # Un plan incline deplace de d selon sa normale monte de d / cos(pente).
            expected = frame.rafter_depth / math.cos(math.radians(frame.pitch_deg))
            self.assertAlmostEqual(expected, frame.covering_lift, places=9,
                                   msg=plan.asset_id)
            self.assertGreater(frame.covering_lift, frame.rafter_depth * 0.999,
                               plan.asset_id)

    def test_the_gable_fills_exactly_the_triangle_the_frame_leaves(self) -> None:
        for plan in self._plans():
            frame = plan.roof_frame
            # Sommet du pignon au faitage, base a la sabliere, demi-largeur egale
            # a la demi-portee : le pignon ne peut ni depasser la charpente ni la
            # laisser a nu.
            self.assertAlmostEqual(frame.eave_z + frame.rise, frame.ridge_z, places=9)
            self.assertGreater(frame.half_span, 0.0, plan.asset_id)
            # Sous les chevrons partout, a l'aplomb du faite seulement.
            for across in (0.0, frame.half_span * 0.5, frame.half_span):
                gable_z = frame.ridge_z - frame.rise * (abs(across) / frame.half_span)
                self.assertLessEqual(round(gable_z, 6), round(frame.slope_z(across), 6),
                                     f"{plan.asset_id} a {across:.2f} m")

    def test_the_frame_spacing_lands_a_rafter_on_each_gable(self) -> None:
        for plan in self._plans():
            frame = plan.roof_frame
            bays = max(2, round(frame.run / frame.rafter_spacing))
            self.assertGreaterEqual(bays, 2, plan.asset_id)
            # Les chevrons sont poses de -half_run a +half_run inclus : les deux
            # extremes tombent donc sur les pignons.
            first = -frame.half_run
            last = -frame.half_run + bays * (frame.run / bays)
            self.assertAlmostEqual(frame.half_run, last, places=9, msg=plan.asset_id)
            self.assertAlmostEqual(-frame.half_run, first, places=9, msg=plan.asset_id)


class JoinedBodyTests(unittest.TestCase):
    """Un corps accole est un batiment complet, pas un volume rapporte.

    Un volume rapporte se noie dans la masse principale : mesure a l'appui,
    l'aile en L n'apparaissait pas du tout dans la silhouette. Un corps accole a
    sa propre pile de niveaux, sa propre enveloppe et sa propre face de rue, et
    il fait monter l'articulation de 0,15 a 0,25 point.
    """

    project_root = Path(__file__).resolve().parents[2]

    def _plans(self, family_id: str = "building_residence_frontier_01") -> list:
        style = load_style(self.project_root, "frontier")
        catalog = json.loads((self.project_root / "AssetFactory" / "Catalogs"
                              / "building_pilot.json").read_text(encoding="utf-8"))
        family = next(item for item in catalog["families"] if item["id"] == family_id)
        return [plan_building(style, family, catalog["variants"], variant["id"])
                for variant in catalog["variants"]]

    def test_an_annex_is_a_complete_body(self) -> None:
        seen = 0
        for plan in self._plans():
            for annex in plan.annexes:
                seen += 1
                self.assertTrue(annex.storeys, plan.scheme_id)
                self.assertTrue(annex.frames, plan.scheme_id)
                self.assertTrue(annex.openings, plan.scheme_id)
                # Sa toiture repose sur ses propres niveaux, pas sur ceux du
                # corps principal.
                self.assertAlmostEqual(annex.storeys[-1].top, annex.frames[0].eave_z,
                                       places=9, msg=plan.scheme_id)
        self.assertGreater(seen, 0, "aucun corps accole dans la residence")

    def test_an_annex_abuts_the_main_body_without_overlapping_it(self) -> None:
        for plan in self._plans():
            main = plan.storeys[0]
            for annex in plan.annexes:
                ground = annex.storeys[0]
                # Mitoyen : colle au flanc, jamais dedans.
                self.assertGreaterEqual(ground.x0, main.x1 - 1e-6, plan.scheme_id)

    def test_an_annex_steps_toward_the_street_when_the_scheme_says_so(self) -> None:
        """Le levier existe dans le plan : un nombre dans le schema, un decalage.

        Il a ete mesure sur le pilote et refuse : avancer l'annexe de 1,85 m
        a fait tomber `town_house` de 6,04 sous 6,0 et a rapproche les deux
        marches jusqu'a IoU 0,817. Le code reste, aucun schema du pilote
        ne l'emploie. Ce test le force pour garder le contrat.
        """
        style = load_style(self.project_root, "frontier")
        style = json.loads(json.dumps(style))
        patched = None
        for form in style["scheme"]["forms"]:
            if form.get("annex"):
                form["annex"]["street_projection_m"] = 1.85
                patched = form["id"]
                break
        self.assertIsNotNone(patched)
        catalog = json.loads((self.project_root / "AssetFactory" / "Catalogs"
                              / "building_pilot.json").read_text(encoding="utf-8"))
        family = next(item for item in catalog["families"]
                      if item["id"] == "building_residence_frontier_01")
        seen = 0
        for variant in catalog["variants"]:
            plan = plan_building(style, family, catalog["variants"], variant["id"])
            if plan.scheme_id != patched or not plan.annexes:
                continue
            seen += 1
            main = plan.storeys[0]
            annex = plan.annexes[0].storeys[0]
            self.assertLess(annex.y0, main.y0 - 0.9, plan.scheme_id)
            self.assertGreaterEqual(annex.x0, main.x1 - 1e-6, plan.scheme_id)
        self.assertGreater(seen, 0, patched)

    def test_an_annex_stays_lower_than_the_body_it_leans_on(self) -> None:
        for plan in self._plans():
            for annex in plan.annexes:
                self.assertLess(annex.frames[0].ridge_z, plan.roof_frame.ridge_z,
                                plan.scheme_id)

    def test_the_street_face_is_declared_and_not_drawn(self) -> None:
        style = load_style(self.project_root, "frontier")
        faces = {form["id"]: form["street_face"] for form in style["scheme"]["forms"]}
        # Les deux presentations doivent exister dans le vocabulaire : un pignon
        # presente un triangle, un gouttereau une bande horizontale.
        self.assertEqual({"gable", "eave"}, set(faces.values()))
        for plan in self._plans():
            expected = "x" if faces[plan.scheme_id] == "gable" else "y"
            self.assertEqual(expected, plan.span_axis, plan.scheme_id)

    def test_stone_base_house_deepens_the_porch_without_extra_rng(self) -> None:
        """Le porche plus profond est un volume deja paye, juste plus grand.

        `stone_base_house` rate C-1 de 0,02 avant cet agrandissement. Allonger
        le porche ne coute aucun triangle : ce sont les memes deux poteaux et
        le meme auvent.
        """
        style = load_style(self.project_root, "frontier")
        del style
        for plan in self._plans():
            if plan.scheme_id != "stone_base_house":
                continue
            porch = plan.appendages["porch"]
            self.assertGreater(porch["depth"], 4.2, plan.asset_id)

    def test_town_house_deepens_the_gallery_without_extra_rng(self) -> None:
        """La galerie plus profonde est le levier de facade de `town_house`.

        Pas de porche sur ce schema : la cheminée seule est trop fine a 64 px.
        Agrandir le pont deja construit ne coute aucun triangle.
        """
        for plan in self._plans():
            if plan.scheme_id != "town_house":
                continue
            gallery = plan.appendages["gallery"]
            self.assertGreater(gallery["depth"], 2.4, plan.asset_id)


class FactoryBuildTests(unittest.TestCase):
    """Une seule commande reconstruit le pilote, et ne refait pas l'inchange.

    La sequence manuelle -- vingt et une generations, les portes de silhouette,
    les planches, la publication, le rafraichissement QA, la porte matiere --
    n'avait rien qui verifie que l'ordre avait ete tenu. Ces tests gardent ce
    qui fait la difference : l'empreinte couvre tout ce qui peut changer la
    geometrie, et le cache ne peut pas sauter un asset perime.
    """

    project_root = Path(__file__).resolve().parents[2]

    def _catalog(self) -> dict:
        return json.loads((self.project_root / "AssetFactory" / "Catalogs"
                           / "building_pilot.json").read_text(encoding="utf-8"))

    def _fingerprint(self, catalog: dict,
                     family_id: str = "building_barn_frontier_01",
                     variant: str = "a", shared: str = "S") -> str:
        family = next(item for item in catalog["families"] if item["id"] == family_id)
        return asset_fingerprint(catalog, family, variant, shared)

    def test_the_shared_kit_is_part_of_the_fingerprint(self) -> None:
        """Le kit partage est dans l'empreinte.

        Un changement dedans change les vingt-quatre batiments sans qu'une
        ligne de leur generateur ne bouge. L'oublier ferait sauter la
        reconstruction de tout le pilote en silence.

        Il s'appelait `generate_sawmill.py` et portait 953 lignes de kit sous
        le nom d'un seul batiment. La scierie est entree au catalogue, ses 348
        lignes propres n'avaient plus d'appelant, et le fichier porte enfin son
        nom -- verifie ici pour que le piege ne revienne pas par un renommage.
        """
        self.assertFalse(
            (self.project_root / "Tools/AssetFactory/Blender/generate_sawmill.py").exists(),
            "le kit ne se cache plus derriere le nom d'un batiment")
        self.assertIn("Tools/AssetFactory/Blender/building_kit.py", SHARED_SOURCES)
        self.assertIn("Tools/AssetFactory/style.py", SHARED_SOURCES)
        self.assertIn("Tools/AssetFactory/Blender/generate_building_family.py",
                      SHARED_SOURCES)
        for source in SHARED_SOURCES:
            self.assertTrue((self.project_root / source).is_file(), source)

    def test_the_shared_digest_moves_with_every_source_it_covers(self) -> None:
        catalog = self._catalog()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            style_dir = root / "AssetFactory" / "Styles"
            style_dir.mkdir(parents=True)
            style_path = style_dir / (catalog["style"] + ".json")
            style_path.write_text("{}", encoding="utf-8")
            for source in SHARED_SOURCES:
                path = root / source
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("originale", encoding="utf-8")

            reference = shared_digest(root, catalog, "Blender 5.2.0 LTS")
            self.assertNotEqual(reference,
                                shared_digest(root, catalog, "Blender 5.3.0 LTS"),
                                "la version de Blender doit compter")
            for source in SHARED_SOURCES:
                path = root / source
                path.write_text("modifiee", encoding="utf-8")
                self.assertNotEqual(
                    reference, shared_digest(root, catalog, "Blender 5.2.0 LTS"),
                    source)
                path.write_text("originale", encoding="utf-8")
            self.assertEqual(reference,
                             shared_digest(root, catalog, "Blender 5.2.0 LTS"),
                             "revenir aux sources d'origine rend l'empreinte")
            style_path.write_text('{"x":1}', encoding="utf-8")
            self.assertNotEqual(reference,
                                shared_digest(root, catalog, "Blender 5.2.0 LTS"),
                                "le style doit compter")

    def test_the_three_variants_enter_the_fingerprint_of_each_one(self) -> None:
        """`plan_building` recoit la liste complete et son tirage est stratifie.

        Changer la variante `c` change ce que `a` tire : une empreinte qui ne
        retiendrait que la variante generee laisserait `a` perimee et muette.
        """
        catalog = self._catalog()
        reference = self._fingerprint(catalog, variant="a")
        moved = json.loads(json.dumps(catalog))
        moved["variants"][2]["seed_offset"] += 1
        self.assertNotEqual(reference, self._fingerprint(moved, variant="a"))

    def test_the_fingerprint_moves_with_the_catalog_entry(self) -> None:
        catalog = self._catalog()
        reference = self._fingerprint(catalog)
        mutations = (
            lambda item: item.__setitem__("seed", item["seed"] + 1),
            lambda item: item["identity_markers"].append("weathervane"),
            lambda item: item["dimensions"].__setitem__(
                0, item["dimensions"][0] + 0.1),
            lambda item: item.__setitem__("roof_system", "thatch"),
        )
        for mutate in mutations:
            moved = json.loads(json.dumps(catalog))
            mutate(next(item for item in moved["families"]
                        if item["id"] == "building_barn_frontier_01"))
            self.assertNotEqual(reference, self._fingerprint(moved))

        stages = json.loads(json.dumps(catalog))
        stages["construction_stages"] = stages["construction_stages"][:-1]
        self.assertNotEqual(reference, self._fingerprint(stages))
        self.assertNotEqual(reference, self._fingerprint(catalog, shared="AUTRE"))
        self.assertNotEqual(reference, self._fingerprint(catalog, variant="b"))

    def test_the_fingerprint_ignores_what_cannot_change_the_geometry(self) -> None:
        catalog = self._catalog()
        reference = self._fingerprint(catalog)
        noise = json.loads(json.dumps(catalog))
        noise["notes"] = ["autre chose"]
        noise["families"] = [item for item in noise["families"]
                             if item["id"] != "building_chapel_frontier_01"]
        self.assertEqual(reference, self._fingerprint(noise),
                         "une autre famille ne perime pas la grange")

    def test_the_plan_names_why_each_asset_is_stale(self) -> None:
        """Un plan qui dit « je refais tout » sans dire pourquoi ne vaut pas
        mieux que vingt et une commandes lancees a la main."""
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            asset = {"id": "building_barn_frontier_01_a",
                     "family": "building_barn_frontier_01", "variant": "a",
                     "fingerprint": "EMPREINTE"}
            self.assertEqual("jamais_construit",
                             staleness(root, asset, {"assets": {}}, False))

            stale_state = {"assets": {asset["id"]: {
                "fingerprint": "AUTRE", "canonical_mesh_sha256": "H"}}}
            self.assertEqual("entrees_changees",
                             staleness(root, asset, stale_state, False))

            state = {"assets": {asset["id"]: {
                "fingerprint": "EMPREINTE", "canonical_mesh_sha256": "H"}}}
            self.assertEqual("metriques_absentes",
                             staleness(root, asset, state, False))

            reports = root / "AssetFactory" / "Reports"
            reports.mkdir(parents=True)
            metrics = reports / (asset["id"] + "_metrics.json")
            metrics.write_text(json.dumps({
                "canonical_mesh_sha256": "AUTRE",
                "outputs": {"fbx": "AssetFactory/Raw/x.fbx"}}), encoding="utf-8")
            self.assertEqual("metriques_desynchronisees",
                             staleness(root, asset, state, False))

            metrics.write_text(json.dumps({
                "canonical_mesh_sha256": "H",
                "outputs": {"fbx": "AssetFactory/Raw/x.fbx"}}), encoding="utf-8")
            self.assertEqual("fbx_absent", staleness(root, asset, state, False))

            fbx = root / "AssetFactory" / "Raw" / "x.fbx"
            fbx.parent.mkdir(parents=True, exist_ok=True)
            fbx.write_bytes(b"fbx")
            self.assertIsNone(staleness(root, asset, state, False),
                              "un asset a jour ne se refait pas")
            self.assertEqual("force", staleness(root, asset, state, True))

    def test_the_selection_covers_the_whole_catalogue_and_filters(self) -> None:
        catalog = self._catalog()
        every = planned_assets(self.project_root, catalog, "S", [])
        self.assertEqual(len(catalog["families"]) * len(catalog["variants"]),
                         len(every))
        self.assertEqual(len(every), len({item["id"] for item in every}))
        self.assertEqual(len({item["fingerprint"] for item in every}), len(every),
                         "deux assets ne partagent pas une empreinte")
        barn = planned_assets(self.project_root, catalog, "S", ["barn"])
        self.assertEqual(len(catalog["variants"]), len(barn))
        self.assertTrue(all(item["family"] == "building_barn_frontier_01"
                            for item in barn))

    def test_the_state_manifest_is_a_pure_function_of_inputs_and_outputs(self) -> None:
        """Aucune date, aucune duree : un etat qui bouge sans que rien n'ait
        change n'est pas relisible, et c'est lui qui justifie chaque saut."""
        path = self.project_root / STATE_MANIFEST
        self.assertTrue(path.is_file(), STATE_MANIFEST)
        state = json.loads(path.read_text(encoding="utf-8"))
        rendered = json.dumps(state)
        for forbidden in ("built_at", "timestamp", "seconds", "duration", "date"):
            self.assertNotIn(forbidden, rendered, forbidden)
        catalog = self._catalog()
        expected = {item["id"] for item
                    in planned_assets(self.project_root, catalog, "S", [])}
        self.assertEqual(expected, set(state["assets"]),
                         "l'etat couvre exactement le catalogue")
        for asset_id, entry in state["assets"].items():
            self.assertEqual({"fingerprint", "blender", "canonical_mesh_sha256",
                              "triangles"}, set(entry), asset_id)

    def test_the_state_matches_the_metrics_it_claims_to_describe(self) -> None:
        """Le hash d'un conteneur FBX change a chaque execution : seul
        `canonical_mesh_sha256` prouve le determinisme, et c'est lui que l'etat
        garde face a l'empreinte qui l'a produit."""
        state = json.loads((self.project_root / STATE_MANIFEST)
                           .read_text(encoding="utf-8"))
        for asset_id, entry in state["assets"].items():
            metrics = json.loads(
                (self.project_root / "AssetFactory" / "Reports"
                 / (asset_id + "_metrics.json")).read_text(encoding="utf-8"))
            self.assertEqual(metrics["canonical_mesh_sha256"],
                             entry["canonical_mesh_sha256"], asset_id)
            self.assertEqual(metrics["triangles"], entry["triangles"], asset_id)

    def test_the_state_holds_the_fingerprint_the_current_inputs_produce(self) -> None:
        """L'etat ne vaut que s'il decrit les entrees d'aujourd'hui.

        Si le catalogue ou le style bouge sans que l'etat suive, la prochaine
        execution refait tout -- c'est le comportement voulu. Ce test dit
        l'inverse : tant que rien n'a bouge, l'empreinte enregistree est celle
        que le depot recalcule.
        """
        state = json.loads((self.project_root / STATE_MANIFEST)
                           .read_text(encoding="utf-8"))
        shared = shared_digest(self.project_root, self._catalog(),
                               state["assets"][next(iter(state["assets"]))]["blender"])
        for asset in planned_assets(self.project_root, self._catalog(), shared, []):
            self.assertEqual(state["assets"][asset["id"]]["fingerprint"],
                             asset["fingerprint"], asset["id"])




class SawmillMigrationTests(unittest.TestCase):
    """La scierie a quitte la grammaire refusee et son generateur separe.

    Elle etait le dernier batiment a 39 980-41 952 triangles pour un budget de
    4 000, avec son propre generateur, son propre contrat v1, son propre
    manifeste et sa propre recette -- donc hors de toutes les portes qui
    jugeaient les sept autres familles.

    Deux chemins etaient possibles : la faire entrer au catalogue du pilote, ou
    lui appliquer la grammaire dans son generateur. Le second demandait de
    dupliquer la porte de silhouette, la porte D-1 et la publication pour une
    seconde source de familles. C'est le premier qui a ete pris.
    """

    project_root = Path(__file__).resolve().parents[2]

    def _catalog(self) -> dict:
        return json.loads((self.project_root / "AssetFactory/Catalogs/building_pilot.json")
                          .read_text(encoding="utf-8"))

    def _family(self) -> dict:
        return next(item for item in self._catalog()["families"]
                    if item["id"] == "building_sawmill_frontier_01")

    def test_the_sawmill_is_a_family_of_the_pilot_catalogue(self) -> None:
        family = self._family()
        self.assertEqual("sawmill", family["function"])
        # Le style connaissait deja la classe de budget de la scierie : c'est la
        # publication qui ne la lui demandait pas.
        style = load_style(self.project_root, "frontier")
        self.assertEqual("standard", style["budget"]["function_class"]["sawmill"])
        self.assertEqual([4000, 1800, 600], family_budget(style, "sawmill"))

    def test_the_sawmill_holds_the_budget_it_was_ten_times_over(self) -> None:
        state = json.loads((self.project_root / STATE_MANIFEST)
                           .read_text(encoding="utf-8"))
        style = load_style(self.project_root, "frontier")
        budget = family_budget(style, "sawmill")
        before = {"a": 39980, "b": 41940, "c": 41952}
        for variant, was in before.items():
            entry = state["assets"][f"building_sawmill_frontier_01_{variant}"]
            lod0 = entry["triangles"]["lod0"]
            self.assertLessEqual(lod0, budget[0], variant)
            self.assertLess(lod0, was // 10, f"{variant} : {was} -> {lod0}")

    def test_the_sawmill_carries_its_own_identity_and_builds_it(self) -> None:
        """Porte D-1 : un marqueur declare et non pose arrete la generation.

        Le mecanisme est ce qui distingue une scierie d'une remise, et il n'y
        avait aucun registre pour le garantir tant qu'elle vivait a part.
        """
        markers = self._family()["identity_markers"]
        self.assertEqual({"saw_frame", "carriage", "drive_wheel", "log_stack",
                          "sawdust_pile", "crossed_axes_sign"}, set(markers))
        for variant in ("a", "b", "c"):
            metrics = json.loads(
                (self.project_root / "AssetFactory" / "Reports"
                 / f"building_sawmill_frontier_01_{variant}_metrics.json")
                .read_text(encoding="utf-8"))
            self.assertEqual(sorted(markers),
                             sorted(metrics["gates"]["identity_markers_built"]),
                             variant)

    def test_the_sawmill_mechanism_stands_outside_the_roof(self) -> None:
        """Trouve au rendu en argile, invisible sur les rendus lites.

        Pose au milieu du batiment, le chassis se retrouvait **sous la
        couverture** : mille triangles que personne ne verrait jamais. Le
        chantier se tient au centre de la facade, le seul plan qu'aucune
        variante n'occupe -- les corps accoles s'adossent au flanc droit.
        Un decalage de ces corps vers la rue ne recouvre pas le chantier.
        Le sortir n'a coute aucun triangle et a rendu la porte C-1 verte sur
        les trois variantes.
        """
        style = load_style(self.project_root, "frontier")
        catalog = self._catalog()
        family = self._family()
        for variant in catalog["variants"]:
            plan = plan_building(style, family, catalog["variants"], variant["id"])
            ground = plan.storeys[0]
            # Le plan du chantier, tel que `sawmill_yard` le calcule.
            yard_y = ground.y0 - 1.85
            self.assertLess(yard_y, ground.y0, plan.asset_id)
            for annex in plan.annexes:
                # Un corps accole s'adosse au flanc droit. Le chantier est au
                # centre de la facade : l'annexe n'a pas le droit d'y entrer.
                self.assertGreaterEqual(annex.storeys[0].x0, ground.x1 - 1e-6,
                                        plan.asset_id)
                self.assertGreaterEqual(annex.storeys[0].y1, yard_y, plan.asset_id)

    def test_the_sawmill_no_longer_has_a_manifest_or_a_recipe_of_its_own(self) -> None:
        """Une preuve qui decrit autre chose que le depot est pire qu'absente.

        Le manifeste declarait 39 980 triangles et un contrat v1 ; la recette
        declarait deux composants Vendor que l'asset ne contient plus. Les
        garder aurait laisse deux descriptions fausses dans le depot.
        """
        for retired in ("AssetFactory/Manifests/building_sawmill_frontier_01.json",
                        "AssetFactory/Recipes/building_sawmill_frontier_01.json"):
            self.assertFalse((self.project_root / retired).exists(), retired)
        manifest = json.loads(
            (self.project_root / "AssetFactory/Manifests/building_pilot.json")
            .read_text(encoding="utf-8"))
        self.assertIn("building_sawmill_frontier_01",
                      {family["id"] for family in manifest["families"]})
        self.assertEqual(8, manifest["gates"]["family_count"])
        self.assertEqual(24, manifest["gates"]["variant_count"])

    def test_no_factory_building_embeds_vendor_geometry_any_more(self) -> None:
        """La scierie etait le dernier asset a importer un maillage Vendor.

        Le module Vendor a quitte la facade le 2026-08-29, decision du
        proprietaire ; la scierie posait encore ses deux composants. Les packs
        restent la provenance et la reference de proportions du catalogue --
        chaque famille cite son `input` et son SHA-256 -- mais aucun maillage
        tiers n'entre plus dans un batiment produit.
        """
        kit = (self.project_root / "Tools/AssetFactory/Blender/building_kit.py"
               ).read_text(encoding="utf-8")
        generator = (self.project_root
                     / "Tools/AssetFactory/Blender/generate_building_family.py"
                     ).read_text(encoding="utf-8")
        self.assertNotIn("import_vendor_component", kit)
        self.assertNotIn("import_vendor_component", generator)
        for family in self._catalog()["families"]:
            source = self.project_root / family["input"]["path"]
            self.assertTrue(source.is_file(), family["id"])
            self.assertEqual(family["input"]["sha256"], sha256_file(source),
                             family["id"])




class VillagePlanTests(unittest.TestCase):
    """Le plan du bourg est une donnee, calculee et jugee hors Unity.

    `CityLabConstruction.unity` alignait huit fois la meme maison : une preuve,
    pas une ville, et `CityLab.unity` etait vide. Le proprietaire a tranche les
    trois questions ouvertes -- 40 batiments, 140 x 140 m, plafond 300 000
    triangles, terrain accidente -- et ces tests gardent ce que la scene ne peut
    pas prouver toute seule.
    """

    project_root = Path(__file__).resolve().parents[2]

    @classmethod
    def setUpClass(cls) -> None:
        cls.spec = json.loads((cls.project_root / VILLAGE_SPEC)
                              .read_text(encoding="utf-8"))
        cls.plan = json.loads((cls.project_root / VILLAGE_PLAN)
                              .read_text(encoding="utf-8"))

    def test_the_plan_holds_the_ceiling_the_owner_set(self) -> None:
        budget = self.plan["budget"]
        self.assertEqual(int(self.spec["budget"]["scene_triangles_max"]),
                         budget["scene_triangles_max"])
        self.assertEqual(budget["buildings"] + budget["decor"] + budget["terrain"],
                         budget["total"], "le total est la somme de ses parts")
        self.assertLessEqual(budget["total"], budget["scene_triangles_max"])
        self.assertEqual("passed", self.plan["status"], self.plan["failures"])

    def test_the_plan_poses_what_the_owner_decided(self) -> None:
        self.assertEqual(int(self.spec["building_count"]),
                         len(self.plan["buildings"]))
        self.assertEqual(float(self.spec["extent_m"]), self.plan["extent_m"])
        self.assertEqual("uneven", self.plan["terrain"]["kind"])
        self.assertFalse(self.plan["inhabitants"],
                         "le proprietaire n'a pas retenu les habitants")

    def test_every_produced_variant_is_posed_at_least_once(self) -> None:
        """Une scene qui ne montrerait que la moitie des variantes ne dirait pas
        ce que l'usine sait faire."""
        state = json.loads((self.project_root / STATE_MANIFEST)
                           .read_text(encoding="utf-8"))
        posed = {item["asset"] for item in self.plan["buildings"]}
        self.assertEqual(set(state["assets"]), posed)

    def test_no_two_buildings_overlap_and_none_leaves_the_extent(self) -> None:
        self.assertEqual([], village_verify(self.plan, self.spec))

    def test_the_gate_refuses_a_plan_that_does_not_fit(self) -> None:
        """Une porte qui ne refuse jamais rien ne garde rien.

        Une simple croix de rues n'ouvrait que 36 parcelles pour 40 batiments,
        et le plan a ete refuse -- la reponse a ete d'ouvrir des rues, pas de
        rapprocher les maisons jusqu'a ce que ca rentre.
        """
        tight = json.loads(json.dumps(self.spec))
        tight["streets"]["axes_m"] = [0.0]
        self.assertLess(len(village_plots(tight)), int(tight["building_count"]),
                        "une simple croix n'ouvre pas assez de parcelles")
        self.assertGreaterEqual(len(village_plots(self.spec)),
                                int(self.spec["building_count"]),
                                "les rues du bourg en ouvrent assez")

        over = json.loads(json.dumps(self.plan))
        over["budget"]["total"] = over["budget"]["scene_triangles_max"] + 1
        self.assertIn("V-5_plafond_triangles", village_verify(over, self.spec))

    def test_a_decor_costs_its_lod0_and_not_the_sum_of_its_levels(self) -> None:
        """Une source EmaceArt porte ses trois LOD dans le meme fichier.

        Sommer les trois et comparer au LOD0 d'un batiment double la facture du
        decor : c'est ce qui faisait croire qu'un arbre coutait plus cher que le
        plus lourd des batiments.
        """
        three_levels = {"triangles": 886, "triangles_lod0": 408,
                        "triangles_unnamed": 0}
        self.assertEqual(408, instance_cost(three_levels))
        # Seize sources sur 243 n'ont aucun maillage nomme : leur unique
        # maillage est ce qui est pose, et le compter zero les ferait
        # disparaitre du budget.
        single_mesh = {"triangles": 392, "triangles_lod0": 0,
                       "triangles_unnamed": 392}
        self.assertEqual(392, instance_cost(single_mesh))

    def test_every_decor_source_exists_and_is_pinned_by_hash(self) -> None:
        """Aucune source Vendor n'est modifiee : le plan les cite, Unity les
        instancie. Le hash rend le mensonge impossible."""
        for piece in self.plan["decor"]:
            source = self.project_root / piece["source"]
            self.assertTrue(source.is_file(), piece["source"])
            self.assertEqual(piece["source_sha256"], sha256_file(source),
                             piece["source"])

    def test_the_terrain_is_sampled_once_and_carried_by_the_plan(self) -> None:
        """Deux implementations de la meme fonction de relief divergeraient, et
        un batiment flotterait -- des accessoires cales sur un Z absolu ont deja
        flotte de 0,92 m. Unity ne recalcule aucune hauteur."""
        terrain = self.plan["terrain"]
        side = terrain["cells"] + 1
        heights = terrain["heights_row_major"]
        self.assertEqual(side * side, len(heights))
        amplitude = float(terrain["amplitude_m"])
        self.assertLessEqual(max(abs(value) for value in heights), amplitude + 1e-6)

        grid = [heights[row * side:(row + 1) * side] for row in range(side)]
        extent = float(terrain["extent_m"])
        # Sur un noeud de la grille, l'echantillonnage rend la valeur du noeud.
        for row, column in ((0, 0), (side // 2, side // 3), (side - 1, side - 1)):
            x = -extent * 0.5 + extent * column / terrain["cells"]
            z = -extent * 0.5 + extent * row / terrain["cells"]
            self.assertAlmostEqual(grid[row][column],
                                   sample_height(grid, extent, x, z), places=3)

        for building in self.plan["buildings"]:
            self.assertAlmostEqual(
                sample_height(grid, extent, building["x"], building["z"]),
                building["ground_y"], places=3, msg=building["id"])

    def test_the_heightfield_is_reproducible_from_its_seed(self) -> None:
        terrain = self.plan["terrain"]
        again = heightfield(int(self.plan["seed"]), float(terrain["extent_m"]),
                            int(terrain["cells"]), float(terrain["amplitude_m"]))
        flat = [value for line in again for value in line]
        self.assertEqual(terrain["heights_row_major"], flat)
        other = heightfield(int(self.plan["seed"]) + 1, float(terrain["extent_m"]),
                            int(terrain["cells"]), float(terrain["amplitude_m"]))
        self.assertNotEqual(again, other, "une autre graine donne un autre relief")

    def test_the_plan_never_promises_more_decor_than_it_poses(self) -> None:
        """`count` est un maximum, pas une promesse.

        Une piece qui ne trouve ni place ni budget n'est pas posee. Annoncer
        quarante-six arbres et en poser trente sans le dire rendrait le budget
        faux.
        """
        posed: dict[str, int] = {}
        for piece in self.plan["decor"]:
            posed[piece["kind"]] = posed.get(piece["kind"], 0) + 1
        declared = {kind["id"]: int(kind["count"])
                    for kind in self.spec["decor"]["kinds"]}
        for kind, count in posed.items():
            self.assertLessEqual(count, declared[kind], kind)
        self.assertEqual(sum(piece["triangles"] for piece in self.plan["decor"]),
                         self.plan["budget"]["decor"])


class ArticulationThresholdTests(unittest.TestCase):
    """Le seuil C-1 est scinde par fonction, decision du proprietaire.

    Le 6,0 etait pose sous la plus sobre de deux references de **maison** --
    maison de ville 6,17, chaumiere 7,41 -- et n'avait jamais ete mesure
    ailleurs que sur l'habitat. Mesure sur les huit familles, il refusait douze
    batiments sur vingt-quatre.

    **Le proprietaire l'abaisse a 5,5 pour les fonctions non domestiques le
    2026-08-30.** Ce test garde la decision : les deux valeurs, qui reste a 6,0.
    Abaisser le seuil a laisse quatre batiments rouges ; la methode de facade
    les a fermes le 2026-09-02, sans second deplacement du seuil.
    """

    project_root = Path(__file__).resolve().parents[2]

    def test_the_threshold_depends_on_the_function(self) -> None:
        style = load_style(self.project_root, "frontier")
        self.assertEqual(6.0, style["silhouette_gate"]["min_articulation"])
        self.assertEqual(5.5, style["silhouette_gate"]["min_articulation_non_domestic"])
        self.assertEqual(["residence", "market"],
                         style["scheme"]["domestic_functions"])
        for function in ("residence", "market"):
            self.assertEqual(6.0, min_articulation(style, function), function)
        for function in ("granary", "warehouse", "blacksmith", "barn", "chapel",
                         "sawmill"):
            self.assertEqual(5.5, min_articulation(style, function), function)
        # Une famille dont la fonction est inconnue garde le seuil le plus haut :
        # un seuil bas ne s'attrape pas par defaut.
        self.assertEqual(6.0, min_articulation(style, None))

    def test_the_decision_is_written_where_the_threshold_lives(self) -> None:
        debt = json.loads((self.project_root / "AssetFactory" / "Manifests"
                           / "silhouette_debt.json").read_text(encoding="utf-8"))
        self.assertEqual({"domestic": 6.0, "non_domestic": 5.5}, debt["threshold"])
        split = debt["threshold_split"]
        self.assertEqual("proprietaire", split["by"])
        self.assertEqual("2026-08-30", split["decided_on"])
        self.assertEqual(6.0, split["was"])
        self.assertEqual(5.5, split["now_non_domestic"])

    def test_the_lower_threshold_did_not_close_the_gate(self) -> None:
        """Abaisser le seuil n'a pas rendu la porte verte. La methode, si.

        Grenier a rate de 0,007 et entrepot a de 0,040. Ces deux-la, puis
        residence a/b et marche c, se corrigent par la methode : la scierie
        est passee de 5,909 a 6,612 en sortant son mecanisme de sous la
        couverture, a zero triangle. La liste historique reste figee ; la
        liste vivante est vide.
        """
        style = load_style(self.project_root, "frontier")
        catalog = json.loads((self.project_root / "AssetFactory/Catalogs"
                              / "building_pilot.json").read_text(encoding="utf-8"))
        functions = {item["id"]: item["function"] for item in catalog["families"]}
        below = {}
        for family, function in functions.items():
            path = (self.project_root / "AssetFactory/Reports/QA"
                    / f"{family}_silhouette.json")
            if not path.is_file():
                continue
            report = json.loads(path.read_text(encoding="utf-8"))
            threshold = min_articulation(style, function)
            self.assertEqual(threshold, report["articulation"]["min_articulation"],
                             family)
            for item in report["articulation"]["variants"]:
                if item["articulation"] < threshold:
                    below[f"{function}_{item['variant']}"] = item["articulation"]
        declared = json.loads((self.project_root / "AssetFactory" / "Manifests"
                               / "silhouette_debt.json").read_text(encoding="utf-8"))
        historical = declared["threshold_split"]["measured_after"]["were_red"]
        self.assertEqual(
            {"granary_a", "warehouse_a", "residence_a", "market_c"},
            set(historical),
        )
        expected = declared["threshold_split"]["measured_after"]["restent_rouges"]
        self.assertEqual({}, expected)
        self.assertEqual([], sorted(below),
                         "la liste des refuses ne peut que retrecir")
        self.assertEqual("closed", declared["status"])
        self.assertEqual([], declared["schemes_below_threshold"])
        closed = declared["threshold_split"]["closed_by_method"]
        self.assertEqual(24, closed["vert"])
        self.assertEqual(24, closed["sur"])


if __name__ == "__main__":
    unittest.main()
