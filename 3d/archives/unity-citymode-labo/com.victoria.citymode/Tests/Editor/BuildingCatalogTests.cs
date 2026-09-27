using System.Linq;
using System.Collections.Generic;
using NUnit.Framework;
using UnityEngine;

namespace Victoria.CityMode.Tests
{
    public sealed class BuildingCatalogTests
    {
        [Test]
        public void DefaultCatalog_ContainsEightValidatedFunctionalDefinitions()
        {
            var catalog = BuildingCatalog.LoadDefault();
            Assert.AreEqual(8, catalog.Count);
            var definitions = catalog.Definitions.OrderBy(item => item.archetype).ToArray();
            CollectionAssert.AreEqual(Enumerable.Range(1, 8),
                definitions.Select(item => (int)item.archetype));
            foreach (var definition in definitions)
            {
                Assert.IsNotEmpty(definition.id);
                Assert.IsNotEmpty(definition.label);
                Assert.Greater(definition.footprintWidth, 0f);
                Assert.Greater(definition.footprintDepth, 0f);
                Assert.Greater(definition.constructionWork, 0f);
                Assert.AreEqual(4, definition.phaseThresholds.Length);
                Assert.AreEqual(1f, definition.phaseThresholds[3]);
                Assert.IsNotEmpty(definition.visualFamily);
            }
        }

        [Test]
        public void Catalog_RejectsMissingDefinitionAndNonIncreasingPhases()
        {
            var source = Resources.Load<TextAsset>("CityBuildingCatalog");
            var document = JsonUtility.FromJson<BuildingCatalogDocument>(source.text);
            document.definitions.RemoveAt(document.definitions.Count - 1);
            Assert.Throws<System.ArgumentException>(() =>
                BuildingCatalog.FromJson(JsonUtility.ToJson(document)));

            document = JsonUtility.FromJson<BuildingCatalogDocument>(source.text);
            document.definitions[0].phaseThresholds[2] = document.definitions[0].phaseThresholds[1];
            Assert.Throws<System.ArgumentException>(() =>
                BuildingCatalog.FromJson(JsonUtility.ToJson(document)));
        }

        [Test]
        public void Simulation_UsesCatalogForResidenceAndLumberCampBudgets()
        {
            const string fixture = "{\"schemaVersion\":1,\"cityId\":1001,\"stockWood\":72," +
                "\"households\":[{\"id\":1,\"memberCount\":3}],\"roads\":[],\"parcels\":[]," +
                "\"buildings\":[],\"villagers\":[{\"id\":1,\"householdId\":1}],\"productionSites\":[]}";
            var simulation = LocalCitySimulation.FromJson(fixture);
            var residence = simulation.Catalog.Get(BuildingArchetype.Residence);
            var lumberCamp = simulation.Catalog.Get(BuildingArchetype.LumberCamp);
            var road = simulation.Submit(CityCommand.DrawRoad(
                new Vector3(-18f, 0f, 8f), new Vector3(18f, 0f, 8f)));
            Assert.IsTrue(road.accepted);
            Assert.IsTrue(simulation.Submit(CityCommand.ZoneResidential(road.createdId)).accepted);
            var building = simulation.GetSnapshot(1001).buildings[0];
            Assert.AreEqual(BuildingArchetype.Residence, building.archetype);
            Assert.AreEqual(residence.woodCost, building.requiredWood);
            Assert.AreEqual(residence.constructionWork, building.workRemaining);

            var woodBeforeCamp = simulation.GetSnapshot(1001).stockWood;
            Assert.IsTrue(simulation.Submit(CityCommand.PlaceLumberCamp(new Vector3(70f, 0f, 0f))).accepted);
            var after = simulation.GetSnapshot(1001);
            Assert.AreEqual(woodBeforeCamp - lumberCamp.woodCost, after.stockWood);
            Assert.AreEqual(lumberCamp.maxWorkers, after.productionSites[0].maxWorkers);
            Assert.AreEqual(lumberCamp.initialResource, after.productionSites[0].remainingTimber);
        }

        [Test]
        public void SixCivicFunctions_CanBePlacedBuiltAndPublishDeterministicCapacities()
        {
            var initial = new CitySnapshot
            {
                cityId = 1001,
                seed = 140001,
                stockWood = 500,
                households = new List<HouseholdState>(),
                villagers = Enumerable.Range(1, 20).Select(id => new VillagerState
                {
                    id = id,
                    householdId = id,
                    position = CityPoint.From(Vector3.zero)
                }).ToList()
            };
            var simulation = new LocalCitySimulation(initial);
            simulation.AddResource(CityResourceKind.Stone, 100);
            simulation.AddResource(CityResourceKind.Planks, 100);
            simulation.AddResource(CityResourceKind.Tools, 30);
            var archetypes = new[]
            {
                BuildingArchetype.Granary, BuildingArchetype.Warehouse, BuildingArchetype.Market,
                BuildingArchetype.Blacksmith, BuildingArchetype.Barn, BuildingArchetype.Chapel
            };
            for (var index = 0; index < archetypes.Length; index++)
            {
                var position = new Vector3(-90f + index * 36f, 0f, 90f);
                var result = simulation.Submit(CityCommand.PlaceBuilding(archetypes[index], position));
                Assert.IsTrue(result.accepted, archetypes[index] + ": " + result.reason);
            }

            for (var tick = 0; tick < 15000; tick++)
                simulation.Tick(0.1f);

            var snapshot = simulation.GetSnapshot(1001);
            Assert.AreEqual(6, snapshot.buildings.Count);
            Assert.IsTrue(snapshot.buildings.All(item => item.phase == BuildingPhase.Complete),
                JsonUtility.ToJson(snapshot));
            Assert.AreEqual(simulation.Catalog.Get(BuildingArchetype.Granary).serviceCapacity,
                snapshot.foodStorageCapacity);
            Assert.AreEqual(simulation.Catalog.Get(BuildingArchetype.Warehouse).serviceCapacity,
                snapshot.goodsStorageCapacity);
            Assert.AreEqual(simulation.Catalog.Get(BuildingArchetype.Market).serviceCapacity,
                snapshot.marketServiceCapacity);
            Assert.AreEqual(simulation.Catalog.Get(BuildingArchetype.Blacksmith).serviceCapacity,
                snapshot.toolProductionCapacity);
            Assert.AreEqual(simulation.Catalog.Get(BuildingArchetype.Barn).serviceCapacity,
                snapshot.livestockCapacity);
            Assert.AreEqual(simulation.Catalog.Get(BuildingArchetype.Chapel).serviceCapacity,
                snapshot.faithServiceCapacity);
            Assert.GreaterOrEqual(snapshot.stockWood, 0);
        }
    }
}
