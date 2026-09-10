using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEngine;

namespace Victoria.CityMode.Tests
{
    public sealed class DeterministicNavigationGridTests
    {
        [Test]
        public void Pathfinding_AvoidsFootprintsAndReturnsStableRoute()
        {
            var catalog = BuildingCatalog.LoadDefault();
            var snapshot = new CitySnapshot
            {
                cityId = 1001,
                buildings = new List<BuildingState>
                {
                    new BuildingState
                    {
                        id = 1,
                        archetype = BuildingArchetype.Warehouse,
                        position = CityPoint.From(Vector3.zero),
                        phase = BuildingPhase.Complete
                    }
                }
            };
            var navigation = new DeterministicNavigationGrid();
            navigation.Rebuild(snapshot, catalog);

            var first = navigation.FindPath(new Vector3(-28f, 0f, 0f), new Vector3(28f, 0f, 0f));
            var second = navigation.FindPath(new Vector3(-28f, 0f, 0f), new Vector3(28f, 0f, 0f));

            Assert.IsNotNull(first);
            Assert.Greater(first.Count, 0);
            CollectionAssert.AreEqual(first, second);
            Assert.IsTrue(first.All(point => navigation.IsWalkable(point.ToVector3())));
            Assert.IsTrue(first.Any(point => Mathf.Abs(point.z) > 8f),
                "Le trajet doit contourner l'entrepot, pas traverser son emprise.");
        }

        [Test]
        public void Pathfinding_ResolvesBlockedDestinationToStableAccessCell()
        {
            var catalog = BuildingCatalog.LoadDefault();
            var snapshot = new CitySnapshot
            {
                cityId = 1001,
                buildings = new List<BuildingState>
                {
                    new BuildingState
                    {
                        id = 1,
                        archetype = BuildingArchetype.Chapel,
                        position = CityPoint.From(new Vector3(24f, 0f, 24f))
                    }
                }
            };
            var navigation = new DeterministicNavigationGrid();
            navigation.Rebuild(snapshot, catalog);

            var path = navigation.FindPath(new Vector3(-24f, 0f, -24f), new Vector3(24f, 0f, 24f));

            Assert.IsNotNull(path);
            Assert.Greater(path.Count, 0);
            Assert.IsTrue(navigation.IsWalkable(path[path.Count - 1].ToVector3()));
            Assert.AreNotEqual(CityPoint.From(new Vector3(24f, 0f, 24f)), path[path.Count - 1]);
        }

        [Test]
        public void HundredVillagers_RunTwentyMinutesWithoutNavigationFailureDeterministically()
        {
            var left = CreateStressSimulation();
            var right = CreateStressSimulation();

            for (var tick = 0; tick < 12000; tick++)
            {
                left.Tick(0.1f);
                right.Tick(0.1f);
            }

            var leftSnapshot = left.GetSnapshot(1001);
            var rightSnapshot = right.GetSnapshot(1001);
            Assert.GreaterOrEqual(leftSnapshot.elapsedSeconds, 1199.8f);
            Assert.AreEqual(0, leftSnapshot.navigationFailures);
            Assert.Greater(leftSnapshot.navigationReplans, 0);
            Assert.IsTrue(leftSnapshot.villagers.Any(item =>
                Mathf.Abs(item.position.x) > 10f || Mathf.Abs(item.position.z) > 10f));
            Assert.IsTrue(leftSnapshot.villagers.All(item => !item.isAtWork));
            Assert.AreEqual(JsonUtility.ToJson(leftSnapshot), JsonUtility.ToJson(rightSnapshot));
        }

        static LocalCitySimulation CreateStressSimulation()
        {
            var initial = new CitySnapshot
            {
                cityId = 1001,
                seed = 140001,
                stockWood = 2000,
                households = new List<HouseholdState>(),
                villagers = Enumerable.Range(1, 100).Select(id => new VillagerState
                {
                    id = id,
                    householdId = id,
                    position = CityPoint.From(new Vector3((id % 10) * 0.2f, 0f, (id / 10) * 0.2f))
                }).ToList()
            };
            var simulation = new LocalCitySimulation(initial);
            simulation.AddResource(CityResourceKind.Stone, 400);
            simulation.AddResource(CityResourceKind.Planks, 300);
            simulation.AddResource(CityResourceKind.Tools, 80);
            var archetypes = new[]
            {
                BuildingArchetype.Granary, BuildingArchetype.Warehouse, BuildingArchetype.Market,
                BuildingArchetype.Blacksmith, BuildingArchetype.Barn, BuildingArchetype.Chapel
            };
            for (var index = 0; index < 18; index++)
            {
                var position = new Vector3(-108f + index % 6 * 42f, 0f, 64f + index / 6 * 42f);
                var result = simulation.Submit(CityCommand.PlaceBuilding(
                    archetypes[index % archetypes.Length], position));
                Assert.IsTrue(result.accepted, $"Placement {index}: {result.reason}");
            }
            return simulation;
        }
    }
}
