using System;
using System.Linq;
using NUnit.Framework;
using UnityEngine;

namespace Victoria.CityMode.Tests
{
    public sealed class PerformanceSimulationTests
    {
        [Test]
        public void HundredVillagerCoreLoop_AveragesLessThanOneKilobyteAllocationPerTick()
        {
            var snapshot = new CitySnapshot
            {
                cityId = 1001,
                seed = 140001,
                elapsedSeconds = 40f,
                stockWood = 500,
                employmentDay = -1,
                households = Enumerable.Range(1, 20).Select(id => new HouseholdState
                {
                    id = id,
                    memberCount = 3
                }).ToList(),
                villagers = Enumerable.Range(1, 100).Select(id => new VillagerState
                {
                    id = id,
                    householdId = (id - 1) % 20 + 1,
                    position = CityPoint.From(new Vector3(-20f + id % 20 * 2f,
                        0f, -12f + id / 20 * 2f))
                }).ToList()
            };
            for (var id = 1; id <= 10; id++)
                snapshot.buildings.Add(new BuildingState
                {
                    id = id,
                    archetype = BuildingArchetype.Residence,
                    position = CityPoint.From(new Vector3(-60f + id * 12f, 0f, 35f)),
                    phase = BuildingPhase.Foundation,
                    priority = id % 3,
                    requiredWood = 6,
                    workRemaining = 12f
                });
            snapshot.productionSites.Add(new ProductionSiteState
            {
                id = 1,
                kind = ProductionSiteKind.LumberCamp,
                position = CityPoint.From(new Vector3(75f, 0f, -35f)),
                maxWorkers = 2,
                constructionPhase = BuildingPhase.Complete,
                remainingTimber = 120
            });
            var simulation = new LocalCitySimulation(snapshot);
            for (var tick = 0; tick < 600; tick++)
                simulation.Tick(0.1f);

            GC.Collect();
            GC.WaitForPendingFinalizers();
            GC.Collect();
            var collectionsBefore = GC.CollectionCount(0);
            var before = GC.GetAllocatedBytesForCurrentThread();
            const int measuredTicks = 1200;
            for (var tick = 0; tick < measuredTicks; tick++)
                simulation.Tick(0.1f);
            var allocated = GC.GetAllocatedBytesForCurrentThread() - before;
            var collections = GC.CollectionCount(0) - collectionsBefore;
            var bytesPerTick = allocated / (double)measuredTicks;

            Assert.Less(bytesPerTick, 1024d,
                $"Boucle centrale: {allocated} octets, {bytesPerTick:F1} octets/tick.");
            Assert.AreEqual(0, collections, "La boucle centrale ne doit pas provoquer de collecte gen0.");
            Debug.Log($"CITYLAB_CORE_ALLOC_OK villagers=100 ticks={measuredTicks} " +
                $"allocated_bytes={allocated} bytes_per_tick={bytesPerTick:F1} gen0_collections={collections}");
        }
    }
}
