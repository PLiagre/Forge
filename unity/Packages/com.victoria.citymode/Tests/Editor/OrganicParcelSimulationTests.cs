using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEngine;

namespace Victoria.CityMode.Tests
{
    public sealed class OrganicParcelSimulationTests
    {
        [Test]
        public void ZoningCreatesVariableOrientedGardenParcelsDeterministically()
        {
            var left = CreateSimulation();
            var right = CreateSimulation();
            var command = CityCommand.DrawRoad(new Vector3(-60f, 0f, 0f),
                new Vector3(60f, 0f, 0f));
            var leftRoad = left.Submit(command);
            var rightRoad = right.Submit(command);

            Assert.IsTrue(left.Submit(CityCommand.ZoneResidential(leftRoad.createdId)).accepted);
            Assert.IsTrue(right.Submit(CityCommand.ZoneResidential(rightRoad.createdId)).accepted);

            var snapshot = left.GetSnapshot(1001);
            Assert.AreEqual(16, snapshot.parcels.Count);
            Assert.GreaterOrEqual(snapshot.parcels.Select(item => Mathf.RoundToInt(item.depth * 10f)).Distinct().Count(), 6);
            Assert.GreaterOrEqual(snapshot.parcels.Select(item => Mathf.RoundToInt(item.width * 10f)).Distinct().Count(), 4);
            Assert.IsTrue(snapshot.parcels.TrueForAll(item => item.depth >= 22f && item.depth <= 36f));
            Assert.IsTrue(snapshot.parcels.TrueForAll(item => item.width >= 10.5f && item.width <= 14.5f));
            Assert.IsTrue(snapshot.parcels.TrueForAll(item => item.hasGarden && item.gardenDepth >= 5f));
            Assert.IsTrue(snapshot.parcels.TrueForAll(item => item.terrainSlopePermille == 0));
            Assert.IsTrue(snapshot.parcels.Exists(item => Mathf.Approximately(item.yaw, 0f)));
            Assert.IsTrue(snapshot.parcels.Exists(item => Mathf.Abs(item.yaw) >= 179.9f));
            Assert.AreEqual(JsonUtility.ToJson(snapshot), JsonUtility.ToJson(right.GetSnapshot(1001)));
        }

        [Test]
        public void TerrainSlopeRejectsOnlyInvalidLotsWithStableOutcome()
        {
            var left = CreateSimulation();
            var right = CreateSimulation();
            left.SetParcelTerrainSampler(new HalfMapSlopeSampler());
            right.SetParcelTerrainSampler(new HalfMapSlopeSampler());
            var leftRoad = left.Submit(CityCommand.DrawRoad(new Vector3(-60f, 0f, 0f),
                new Vector3(60f, 0f, 0f)));
            var rightRoad = right.Submit(CityCommand.DrawRoad(new Vector3(-60f, 0f, 0f),
                new Vector3(60f, 0f, 0f)));

            Assert.IsTrue(left.Submit(CityCommand.ZoneResidential(leftRoad.createdId)).accepted);
            Assert.IsTrue(right.Submit(CityCommand.ZoneResidential(rightRoad.createdId)).accepted);

            var snapshot = left.GetSnapshot(1001);
            Assert.That(snapshot.parcels.Count, Is.GreaterThan(0).And.LessThan(16));
            Assert.IsTrue(snapshot.parcels.TrueForAll(item => item.center.x < 0f));
            Assert.IsTrue(snapshot.parcels.TrueForAll(item => item.terrainSlopePermille <= 180));
            Assert.AreEqual(JsonUtility.ToJson(snapshot), JsonUtility.ToJson(right.GetSnapshot(1001)));
        }

        [Test]
        public void CompletedHomesActivateGardensAndLevelBoundedExtensionsAcrossReload()
        {
            var snapshot = new CitySnapshot { cityId = 1001, seed = 140001, stockWood = 72 };
            snapshot.roads.Add(new RoadState
            {
                id = 1,
                start = CityPoint.From(new Vector3(-20f, 0f, 0f)),
                end = CityPoint.From(new Vector3(20f, 0f, 0f))
            });
            AddCompletedHome(snapshot, 1, -8f, HouseholdLevel.Established);
            AddCompletedHome(snapshot, 2, 8f, HouseholdLevel.Prosperous);

            var simulation = new LocalCitySimulation(snapshot);
            var evolved = simulation.GetSnapshot(1001);
            Assert.IsTrue(evolved.parcels.TrueForAll(item => item.gardenActive));
            Assert.AreEqual(1, evolved.parcels.Find(item => item.id == 1).extensionLevel);
            Assert.AreEqual(2, evolved.parcels.Find(item => item.id == 2).extensionLevel);

            var document = CitySaveService.Serialize(evolved);
            Assert.IsTrue(CitySaveService.TryDeserialize(document, out var reloaded, out var reason), reason);
            Assert.AreEqual(JsonUtility.ToJson(evolved), JsonUtility.ToJson(reloaded));

            Assert.IsTrue(simulation.DestroyBuilding(2));
            var cleared = simulation.GetSnapshot(1001).parcels.Find(item => item.id == 2);
            Assert.IsFalse(cleared.gardenActive);
            Assert.AreEqual(0, cleared.extensionLevel);
        }

        static LocalCitySimulation CreateSimulation()
        {
            var snapshot = new CitySnapshot
            {
                cityId = 1001,
                seed = 140001,
                stockWood = 72,
                households = Enumerable.Range(1, 6).Select(id => new HouseholdState
                {
                    id = id,
                    memberCount = 3
                }).ToList(),
                villagers = new List<VillagerState>()
            };
            return new LocalCitySimulation(snapshot);
        }

        static void AddCompletedHome(CitySnapshot snapshot, int id, float x, HouseholdLevel level)
        {
            snapshot.households.Add(new HouseholdState
            {
                id = id,
                memberCount = 3,
                claimedParcelId = id,
                homeBuildingId = id,
                level = level
            });
            snapshot.parcels.Add(new ParcelState
            {
                id = id,
                roadId = 1,
                center = CityPoint.From(new Vector3(x, 0f, 20f)),
                width = 12f,
                depth = 34f,
                yaw = 0f,
                gardenDepth = 17f,
                terrainSlopePermille = 0,
                extensionCapacity = 2,
                hasGarden = true,
                accessible = true,
                householdId = id,
                buildingId = id
            });
            snapshot.buildings.Add(new BuildingState
            {
                id = id,
                archetype = BuildingArchetype.Residence,
                parcelId = id,
                householdId = id,
                position = CityPoint.From(new Vector3(x, 0f, 8f)),
                phase = BuildingPhase.Complete
            });
        }

        sealed class HalfMapSlopeSampler : IParcelTerrainSampler
        {
            public float SampleHeight(Vector3 worldPosition) => worldPosition.x > 0f
                ? worldPosition.z * 0.55f
                : 0f;
        }
    }
}
