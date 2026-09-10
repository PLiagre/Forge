using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEngine;

namespace Victoria.CityMode.Tests
{
    public sealed class MarketSimulationTests
    {
        [Test]
        public void TraderPhysicallySuppliesFoodStallFromNearbyGranary()
        {
            var snapshot = CreateMarketSnapshot(true);
            snapshot.buildings[0].localStocks.Add(new StoredResourceState
            {
                kind = CityResourceKind.Food,
                quantity = 40,
                capacity = 120
            });
            var simulation = new LocalCitySimulation(snapshot);
            var observedCargo = false;

            for (var tick = 0; tick < 6000; tick++)
            {
                simulation.Tick(0.1f);
                var current = simulation.GetSnapshot(1001);
                observedCargo |= current.villagers.Any(item => item.carryingWood > 0 &&
                    item.carryingResource == CityResourceKind.Food);
                var stall = current.buildings[1].localStocks
                    .Find(item => item.kind == CityResourceKind.Food);
                if (observedCargo && stall.quantity > 0)
                    break;
            }

            var after = simulation.GetSnapshot(1001);
            var market = after.buildings[1];
            Assert.IsTrue(observedCargo);
            Assert.Greater(market.localStocks.Find(item => item.kind == CityResourceKind.Food).quantity, 0);
            Assert.Less(market.marketScarcityPermille, 1000);
            Assert.That(market.marketPricePermille, Is.InRange(1000, 2000));
        }

        [Test]
        public void CoveredHouseholdConsumesMarketFoodWhileRemoteHouseholdUsesGlobalStock()
        {
            var snapshot = CreateMarketSnapshot(false);
            snapshot.elapsedSeconds = LocalCitySimulation.SecondsPerGameDay - 0.05f;
            snapshot.buildings[1].localStocks.Add(new StoredResourceState
            {
                kind = CityResourceKind.Food,
                quantity = 10,
                capacity = 8
            });
            snapshot.buildings.Add(new BuildingState
            {
                id = 3,
                archetype = BuildingArchetype.Residence,
                position = CityPoint.From(new Vector3(10f, 0f, 0f)),
                phase = BuildingPhase.Complete
            });
            snapshot.buildings.Add(new BuildingState
            {
                id = 4,
                archetype = BuildingArchetype.Residence,
                position = CityPoint.From(new Vector3(220f, 0f, 220f)),
                phase = BuildingPhase.Complete
            });
            snapshot.households.Add(new HouseholdState { id = 1, memberCount = 1, homeBuildingId = 3 });
            snapshot.households.Add(new HouseholdState { id = 2, memberCount = 1, homeBuildingId = 4 });
            var simulation = new LocalCitySimulation(snapshot);
            simulation.AddResource(CityResourceKind.Food, 5);

            simulation.Tick(0.1f);

            var after = simulation.GetSnapshot(1001);
            Assert.IsTrue(after.households[0].marketCovered);
            Assert.AreEqual(2, after.households[0].marketBuildingId);
            Assert.IsFalse(after.households[1].marketCovered);
            Assert.AreEqual(7, after.buildings[1].localStocks
                .Find(item => item.kind == CityResourceKind.Food).quantity);
            Assert.AreEqual(4, after.resources.Find(item => item.kind == CityResourceKind.Food).quantity);
        }

        [Test]
        public void EmptyMarketAccumulatesOneShortagePerDayAtMaximumScarcity()
        {
            var snapshot = CreateMarketSnapshot(false);
            snapshot.elapsedSeconds = LocalCitySimulation.SecondsPerGameDay - 0.05f;
            var simulation = new LocalCitySimulation(snapshot);

            simulation.Tick(0.1f);
            var first = simulation.GetSnapshot(1001).buildings[1];
            Assert.AreEqual(1, first.marketShortageDays);
            Assert.AreEqual(1000, first.marketScarcityPermille);
            Assert.AreEqual(2000, first.marketPricePermille);

            var targetDay = simulation.GetSnapshot(1001).calendar.absoluteDay + 1;
            while (simulation.GetSnapshot(1001).calendar.absoluteDay < targetDay)
                simulation.Tick(0.1f);
            Assert.AreEqual(2, simulation.GetSnapshot(1001).buildings[1].marketShortageDays);
        }

        static CitySnapshot CreateMarketSnapshot(bool withWorkers)
        {
            var snapshot = new CitySnapshot
            {
                cityId = 1001,
                seed = 140001,
                elapsedSeconds = 40f,
                employmentDay = -1,
                households = new List<HouseholdState>()
            };
            snapshot.buildings.Add(new BuildingState
            {
                id = 1,
                archetype = BuildingArchetype.Granary,
                position = CityPoint.From(Vector3.zero),
                phase = BuildingPhase.Complete
            });
            snapshot.buildings.Add(new BuildingState
            {
                id = 2,
                archetype = BuildingArchetype.Market,
                position = CityPoint.From(new Vector3(30f, 0f, 0f)),
                phase = BuildingPhase.Complete
            });
            if (!withWorkers)
                return snapshot;
            for (var id = 1; id <= 6; id++)
            {
                snapshot.households.Add(new HouseholdState { id = id, memberCount = 1 });
                snapshot.villagers.Add(new VillagerState
                {
                    id = id,
                    householdId = id,
                    position = CityPoint.From(new Vector3(id, 0f, 0f))
                });
            }
            return snapshot;
        }
    }
}
