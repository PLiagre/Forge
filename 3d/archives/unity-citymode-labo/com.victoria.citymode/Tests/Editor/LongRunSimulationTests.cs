using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEngine;

namespace Victoria.CityMode.Tests
{
    public sealed class LongRunSimulationTests
    {
        const int ReferenceSeed = 140001;
        const string ReferenceHash = "f5c411a96d05f283edcc07d7e9a0cc0a94346d52b972eb81a6b457369d753a82";

        [Test]
        public void ReferenceSeed_RunsThirtyDaysWithStableHashAndNoInvariantFailure()
        {
            var initial = CreateReferenceSnapshot();
            var left = CityLongRunHarness.Run(initial, 30);
            var right = CityLongRunHarness.Run(initial, 30);

            var blocked = left.finalSnapshot.villagers.Find(item =>
                left.failureReason == "agent-blocked-" + item.id);
            Assert.IsTrue(left.succeeded, left.failureReason + " elapsed=" +
                left.finalSnapshot.elapsedSeconds.ToString("F2") + " nav=" +
                left.finalSnapshot.navigationFailures + " villager=" +
                (blocked == null ? "none" : JsonUtility.ToJson(blocked)));
            Assert.IsTrue(right.succeeded, right.failureReason);
            Assert.AreEqual(30, left.completedDays);
            Assert.AreEqual(0, left.navigationFailures);
            Assert.AreEqual(0, left.blockedAgents);
            Assert.GreaterOrEqual(left.minimumResourceQuantity, 0);
            Assert.AreEqual(left.finalHash, right.finalHash);
            Assert.AreEqual(ReferenceHash, left.finalHash);
            Assert.AreEqual(JsonUtility.ToJson(left.finalSnapshot), JsonUtility.ToJson(right.finalSnapshot));
            Debug.Log($"CITYLAB_LONG_RUN_OK seed={ReferenceSeed} days=30 ticks={left.ticks} " +
                $"hash={left.finalHash} minResource={left.minimumResourceQuantity} " +
                $"navigationFailures={left.navigationFailures} blockedAgents={left.blockedAgents}");
        }

        internal static CitySnapshot CreateReferenceSnapshot()
        {
            var snapshot = new CitySnapshot
            {
                cityId = 1001,
                seed = ReferenceSeed,
                stockWood = 500,
                employmentDay = -1,
                households = Enumerable.Range(1, 20).Select(id => new HouseholdState
                {
                    id = id,
                    memberCount = 3
                }).ToList(),
                villagers = Enumerable.Range(1, 30).Select(id => new VillagerState
                {
                    id = id,
                    householdId = (id - 1) % 20 + 1,
                    position = CityPoint.From(new Vector3(-12f + id * 0.7f, 0f, -8f))
                }).ToList()
            };
            for (var id = 1; id <= 8; id++)
                snapshot.buildings.Add(new BuildingState
                {
                    id = id,
                    archetype = BuildingArchetype.Residence,
                    position = CityPoint.From(new Vector3(-56f + id * 14f, 0f, 24f)),
                    phase = BuildingPhase.Foundation,
                    priority = id % 3,
                    requiredWood = 6,
                    workRemaining = 12f
                });
            var civicArchetypes = new[]
            {
                BuildingArchetype.Granary, BuildingArchetype.Warehouse,
                BuildingArchetype.Market, BuildingArchetype.Blacksmith,
                BuildingArchetype.Barn, BuildingArchetype.Chapel
            };
            for (var index = 0; index < civicArchetypes.Length; index++)
                snapshot.buildings.Add(new BuildingState
                {
                    id = 20 + index,
                    archetype = civicArchetypes[index],
                    position = CityPoint.From(new Vector3(-50f + index * 20f, 0f, 60f)),
                    phase = BuildingPhase.Complete,
                    priority = 1
                });
            snapshot.productionSites = new List<ProductionSiteState>
            {
                new ProductionSiteState
                {
                    id = 1,
                    kind = ProductionSiteKind.LumberCamp,
                    position = CityPoint.From(new Vector3(80f, 0f, -40f)),
                    maxWorkers = 2,
                    constructionPhase = BuildingPhase.Complete,
                    remainingTimber = 240
                }
            };
            return snapshot;
        }
    }
}
