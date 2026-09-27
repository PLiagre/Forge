using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEngine;

namespace Victoria.CityMode.Tests
{
    public sealed class PhysicalConstructionTests
    {
        [Test]
        public void NewSite_PreparesSampledTerrainBeforeRequestingMaterials()
        {
            var simulation = CreateSimulation();
            simulation.SetParcelTerrainSampler(new SlopedTerrainSampler());
            var result = simulation.Submit(CityCommand.PlaceBuilding(
                BuildingArchetype.Granary, new Vector3(20f, 0f, 0f)));
            Assert.IsTrue(result.accepted, result.reason);

            var initial = simulation.GetSnapshot(1001).buildings.Single();
            Assert.IsFalse(initial.terrainPrepared);
            Assert.Greater(initial.terrainCutFillMillimeters, 0);
            Assert.Greater(initial.terrainWorkRemaining, 0f);
            Assert.AreEqual(0, initial.constructionMaterials.Sum(item => item.delivered));

            var observedTerracing = false;
            for (var tick = 0; tick < 700 && !observedTerracing; tick++)
            {
                simulation.Tick(0.1f);
                var building = simulation.GetSnapshot(1001).buildings.Single();
                if (!building.terrainPrepared)
                    Assert.AreEqual(0, building.constructionMaterials.Sum(item => item.delivered));
                else
                    observedTerracing = true;
            }

            Assert.IsTrue(observedTerracing, "Le terrassement ne s'est pas achevé.");
        }

        [Test]
        public void CivicSite_ConsumesPhaseSpecificMaterialsInOrder()
        {
            var simulation = CreateSimulation();
            var result = simulation.Submit(CityCommand.PlaceBuilding(
                BuildingArchetype.Granary, new Vector3(20f, 0f, 0f)));
            Assert.IsTrue(result.accepted, result.reason);

            var expectedPhases = new[]
            {
                BuildingPhase.Foundation,
                BuildingPhase.Framing,
                BuildingPhase.Roofing,
                BuildingPhase.Detailing,
                BuildingPhase.Complete
            };
            var observedPhases = new List<BuildingPhase> { BuildingPhase.Foundation };
            for (var tick = 0; tick < 20000; tick++)
            {
                simulation.Tick(0.1f);
                var phase = simulation.GetSnapshot(1001).buildings.Single().phase;
                if (observedPhases[observedPhases.Count - 1] != phase)
                    observedPhases.Add(phase);
                if (phase == BuildingPhase.Complete)
                    break;
            }

            var completed = simulation.GetSnapshot(1001).buildings.Single();
            CollectionAssert.AreEqual(expectedPhases, observedPhases);
            Assert.IsTrue(completed.terrainPrepared);
            Assert.AreEqual(4, completed.constructionMaterials.Count);
            Assert.IsTrue(completed.constructionMaterials.All(item => item.delivered == item.required));
            CollectionAssert.AreEqual(
                new[] { CityResourceKind.Stone, CityResourceKind.Wood,
                    CityResourceKind.Planks, CityResourceKind.Tools },
                completed.constructionMaterials.Select(item => item.resource));
        }

        [Test]
        public void MidConstruction_SaveReloadRemainsBitExact()
        {
            var original = CreateSimulation();
            Assert.IsTrue(original.Submit(CityCommand.PlaceBuilding(
                BuildingArchetype.Granary, new Vector3(20f, 0f, 0f))).accepted);
            for (var tick = 0; tick < 520; tick++)
                original.Tick(0.1f);

            var beforeReload = original.GetSnapshot(1001);
            var document = CitySaveService.Serialize(beforeReload);
            Assert.IsTrue(CitySaveService.TryDeserialize(document, out var reloaded, out var reason), reason);
            Assert.AreEqual(JsonUtility.ToJson(beforeReload.buildings.Single()),
                JsonUtility.ToJson(reloaded.buildings.Single()));
            var left = new LocalCitySimulation(reloaded);
            var right = new LocalCitySimulation(reloaded);
            for (var tick = 0; tick < 800; tick++)
            {
                left.Tick(0.1f);
                right.Tick(0.1f);
            }

            Assert.AreEqual(JsonUtility.ToJson(left.GetSnapshot(1001)),
                JsonUtility.ToJson(right.GetSnapshot(1001)));
        }

        [Test]
        public void Scaffolding_FollowsFourPersistedPhasesAndSelection()
        {
            var simulation = CreateSimulation();
            Assert.IsTrue(simulation.Submit(CityCommand.PlaceBuilding(
                BuildingArchetype.Granary, new Vector3(20f, 0f, 0f))).accepted);
            var persisted = simulation.GetSnapshot(1001);
            persisted.buildings.Single().terrainPrepared = true;
            persisted.buildings.Single().phase = BuildingPhase.Roofing;
            var document = CitySaveService.Serialize(persisted);
            Assert.IsTrue(CitySaveService.TryDeserialize(document,
                out var reloaded, out var reason), reason);

            var root = new GameObject("Scaffolding phase test");
            try
            {
                var scaffold = root.AddComponent<ConstructionScaffoldVisual>();
                scaffold.Initialize(11f, 13f, null, null);
                scaffold.Refresh(BuildingPhase.Foundation, false);
                Assert.IsFalse(scaffold.IsVisible,
                    "L'échafaudage ne doit pas précéder le terrassement.");

                var phases = new[]
                {
                    BuildingPhase.Foundation,
                    BuildingPhase.Framing,
                    BuildingPhase.Roofing,
                    BuildingPhase.Detailing
                };
                for (var index = 0; index < phases.Length; index++)
                {
                    scaffold.Refresh(phases[index], true);
                    Assert.AreEqual(index + 1, scaffold.VisibleStageCount, phases[index].ToString());
                }

                scaffold.SetSelected(true);
                Assert.IsTrue(scaffold.IsSelected);
                scaffold.Refresh(reloaded.buildings.Single().phase,
                    reloaded.buildings.Single().terrainPrepared);
                Assert.AreEqual(BuildingPhase.Roofing, scaffold.CurrentPhase);
                Assert.AreEqual(3, scaffold.VisibleStageCount,
                    "La phase persistée doit reconstruire exactement trois niveaux.");
                Assert.IsTrue(scaffold.IsSelected);

                scaffold.Refresh(BuildingPhase.Complete, true);
                Assert.AreEqual(0, scaffold.VisibleStageCount);
                Assert.IsFalse(scaffold.IsVisible);
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        static LocalCitySimulation CreateSimulation()
        {
            var snapshot = new CitySnapshot
            {
                cityId = 1001,
                seed = 140001,
                stockWood = 200,
                villagers = new List<VillagerState>
                {
                    new VillagerState
                    {
                        id = 1,
                        householdId = 1,
                        position = CityPoint.From(Vector3.zero)
                    }
                }
            };
            var simulation = new LocalCitySimulation(snapshot);
            simulation.AddResource(CityResourceKind.Stone, 100);
            simulation.AddResource(CityResourceKind.Planks, 100);
            simulation.AddResource(CityResourceKind.Tools, 30);
            return simulation;
        }

        sealed class SlopedTerrainSampler : IParcelTerrainSampler
        {
            public float SampleHeight(Vector3 worldPosition) =>
                worldPosition.x * 0.04f + worldPosition.z * 0.015f;
        }
    }
}
