using System.Collections.Generic;
using NUnit.Framework;
using UnityEngine;

namespace Victoria.CityMode.Tests
{
    public sealed class FoodSimulationTests
    {
        [Test]
        public void Forager_TravelsToAccessibleSourceAndPhysicallyReturnsFood()
        {
            var simulation = CreateSimulation(40f, villagers: 1, households: 1);
            var sourceId = simulation.AddFoodSource(FoodSourceKind.BerryGrove,
                new Vector3(28f, 0f, 0f), 12, 1);

            for (var tick = 0; tick < 3000 &&
                simulation.GetResource(CityResourceKind.Food).quantity == 0; tick++)
                simulation.Tick(0.1f);

            var snapshot = simulation.GetSnapshot(1001);
            var source = snapshot.foodSources.Find(item => item.id == sourceId);
            var villager = snapshot.villagers[0];
            Assert.Greater(snapshot.resources.Find(item => item.kind == CityResourceKind.Food).quantity, 0);
            Assert.Less(source.remainingFood, 12);
            Assert.AreEqual(VillagerJob.Forager, villager.job);
            Assert.Greater(villager.position.x, 1f,
                "La collecte doit inclure un trajet physique vers la source.");
        }

        [Test]
        public void Households_ConsumeDailyChooseAccessibleSourceAndPersistShortage()
        {
            var simulation = CreateSimulation(LocalCitySimulation.SecondsPerGameDay - 0.05f,
                villagers: 0, households: 1);
            Assert.AreEqual(1, simulation.AddResource(CityResourceKind.Food, 1));
            var blockedId = simulation.AddFoodSource(FoodSourceKind.BerryGrove,
                new Vector3(5f, 0f, 0f), 20);
            var accessibleId = simulation.AddFoodSource(FoodSourceKind.HuntingGround,
                new Vector3(25f, 0f, 0f), 20);
            Assert.IsTrue(simulation.SetFoodSourceAccessible(blockedId, false));

            simulation.Tick(0.1f);
            var fed = simulation.GetSnapshot(1001).households[0];
            Assert.IsFalse(fed.hungry);
            Assert.AreEqual(1, fed.foodConsumedTotal);
            Assert.AreEqual(accessibleId, fed.preferredFoodSourceId);

            for (var tick = 0; tick < 1200; tick++)
                simulation.Tick(0.1f);
            var hungry = simulation.GetSnapshot(1001).households[0];
            Assert.IsTrue(hungry.hungry);
            Assert.AreEqual(1, hungry.foodShortageDays);
        }

        [Test]
        public void FoodCollectionAndConsumption_ReloadDeterministically()
        {
            var simulation = CreateSimulation(40f, villagers: 2, households: 2);
            simulation.AddFoodSource(FoodSourceKind.BerryGrove, new Vector3(24f, 0f, 0f), 30, 2);
            for (var tick = 0; tick < 500; tick++)
                simulation.Tick(0.1f);
            var before = simulation.GetSnapshot(1001);
            var reloaded = new LocalCitySimulation(before);

            for (var tick = 0; tick < 1000; tick++)
            {
                simulation.Tick(0.1f);
                reloaded.Tick(0.1f);
            }

            Assert.AreEqual(JsonUtility.ToJson(simulation.GetSnapshot(1001)),
                JsonUtility.ToJson(reloaded.GetSnapshot(1001)));
        }

        static LocalCitySimulation CreateSimulation(float elapsed, int villagers, int households)
        {
            var snapshot = new CitySnapshot
            {
                cityId = 1001,
                seed = 140001,
                elapsedSeconds = elapsed,
                employmentDay = -1,
                households = new List<HouseholdState>(),
                villagers = new List<VillagerState>()
            };
            for (var id = 1; id <= households; id++)
                snapshot.households.Add(new HouseholdState { id = id, memberCount = 3 });
            for (var id = 1; id <= villagers; id++)
                snapshot.villagers.Add(new VillagerState
                {
                    id = id,
                    householdId = (id - 1) % Mathf.Max(1, households) + 1,
                    position = CityPoint.From(new Vector3(id, 0f, 0f))
                });
            return new LocalCitySimulation(snapshot);
        }
    }
}
