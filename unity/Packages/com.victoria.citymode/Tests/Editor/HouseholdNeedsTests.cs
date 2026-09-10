using System.Collections.Generic;
using NUnit.Framework;
using UnityEngine;

namespace Victoria.CityMode.Tests
{
    public sealed class HouseholdNeedsTests
    {
        [Test]
        public void SuppliedHousedHouseholdConsumesFiveNeedsAndBecomesProsperous()
        {
            var snapshot = CreateAtNeedsDay(withHome: true);
            AddMarket(snapshot, food: 10, tools: 4, textile: 4);
            snapshot.buildings.Add(new BuildingState
            {
                id = 3,
                archetype = BuildingArchetype.Warehouse,
                position = CityPoint.From(new Vector3(15f, 0f, 0f)),
                phase = BuildingPhase.Complete,
                localStocks = new List<StoredResourceState>
                {
                    new StoredResourceState
                    {
                        kind = CityResourceKind.Wood,
                        quantity = 8,
                        capacity = 32
                    }
                }
            });
            var simulation = new LocalCitySimulation(snapshot);

            simulation.Tick(0.1f);

            var household = simulation.GetSnapshot(1001).households[0];
            Assert.IsFalse(household.hungry);
            Assert.IsTrue(household.fuelSatisfied);
            Assert.IsTrue(household.clothingSatisfied);
            Assert.IsTrue(household.toolsSatisfied);
            Assert.AreEqual(1000, household.satisfactionPermille);
            Assert.AreEqual(HouseholdLevel.Prosperous, household.level);
        }

        [Test]
        public void MissingNeedsAccumulateShortagesAndKeepHouseholdDestitute()
        {
            var simulation = new LocalCitySimulation(CreateAtNeedsDay(withHome: false));

            simulation.Tick(0.1f);

            var household = simulation.GetSnapshot(1001).households[0];
            Assert.IsTrue(household.hungry);
            Assert.IsFalse(household.fuelSatisfied);
            Assert.IsFalse(household.clothingSatisfied);
            Assert.IsFalse(household.toolsSatisfied);
            Assert.AreEqual(1, household.foodShortageDays);
            Assert.AreEqual(1, household.fuelShortageDays);
            Assert.AreEqual(1, household.clothingShortageDays);
            Assert.AreEqual(1, household.toolShortageDays);
            Assert.AreEqual(0, household.satisfactionPermille);
            Assert.AreEqual(HouseholdLevel.Destitute, household.level);
        }

        [Test]
        public void FoodAndHousingAloneProduceStableBasicLevelAfterReload()
        {
            var snapshot = CreateAtNeedsDay(withHome: true);
            var simulation = new LocalCitySimulation(snapshot);
            simulation.AddResource(CityResourceKind.Food, 10);
            var reloaded = new LocalCitySimulation(simulation.GetSnapshot(1001));

            simulation.Tick(0.1f);
            reloaded.Tick(0.1f);

            var left = simulation.GetSnapshot(1001);
            Assert.AreEqual(600, left.households[0].satisfactionPermille);
            Assert.AreEqual(HouseholdLevel.Basic, left.households[0].level);
            Assert.AreEqual(JsonUtility.ToJson(left), JsonUtility.ToJson(reloaded.GetSnapshot(1001)));
        }

        static CitySnapshot CreateAtNeedsDay(bool withHome)
        {
            var snapshot = new CitySnapshot
            {
                cityId = 1001,
                seed = 140001,
                elapsedSeconds = 30 * LocalCitySimulation.SecondsPerGameDay - 0.05f,
                resourceLossDay = 29,
                households = new List<HouseholdState>
                {
                    new HouseholdState { id = 1, memberCount = 3, homeBuildingId = withHome ? 1 : 0 }
                }
            };
            if (withHome)
                snapshot.buildings.Add(new BuildingState
                {
                    id = 1,
                    archetype = BuildingArchetype.Residence,
                    position = CityPoint.From(Vector3.zero),
                    phase = BuildingPhase.Complete
                });
            return snapshot;
        }

        static void AddMarket(CitySnapshot snapshot, int food, int tools, int textile)
        {
            snapshot.buildings.Add(new BuildingState
            {
                id = 2,
                archetype = BuildingArchetype.Market,
                position = CityPoint.From(new Vector3(8f, 0f, 0f)),
                phase = BuildingPhase.Complete,
                localStocks = new List<StoredResourceState>
                {
                    new StoredResourceState { kind = CityResourceKind.Food, quantity = food, capacity = 8 },
                    new StoredResourceState { kind = CityResourceKind.Tools, quantity = tools, capacity = 8 },
                    new StoredResourceState { kind = CityResourceKind.Textile, quantity = textile, capacity = 8 }
                }
            });
        }
    }
}
