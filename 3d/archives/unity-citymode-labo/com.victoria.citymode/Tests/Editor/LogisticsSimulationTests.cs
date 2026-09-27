using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEngine;

namespace Victoria.CityMode.Tests
{
    public sealed class LogisticsSimulationTests
    {
        [Test]
        public void Priority_SelectsHighestTaskBeforeCreationOrder()
        {
            var simulation = CreateSimulation(8);
            Assert.IsTrue(simulation.DestroyBuilding(2));
            var lowTaskId = simulation.EnqueueLogisticsTask(CityResourceKind.Wood,
                LogisticsEndpointKind.GlobalStock, 0,
                LogisticsEndpointKind.ProductionSite, 1, 4, 0);
            var highTaskId = simulation.EnqueueLogisticsTask(CityResourceKind.Wood,
                LogisticsEndpointKind.GlobalStock, 0,
                LogisticsEndpointKind.ProductionSite, 2, 4, 3);

            simulation.Tick(0.1f);

            var snapshot = simulation.GetSnapshot(1001);
            Assert.IsTrue(snapshot.villagers.Any(item => item.logisticsTaskId == highTaskId));
            Assert.IsFalse(snapshot.villagers.Any(item => item.logisticsTaskId == lowTaskId));
        }

        [Test]
        public void ConcurrentWorkers_ReserveEachUnitAtMostOnce()
        {
            var simulation = CreateSimulation(5);
            var taskId = simulation.EnqueueLogisticsTask(CityResourceKind.Wood,
                LogisticsEndpointKind.GlobalStock, 0,
                LogisticsEndpointKind.ProductionSite, 1, 10, 3);

            simulation.Tick(0.1f);

            var snapshot = simulation.GetSnapshot(1001);
            var task = snapshot.logisticsTasks.Find(item => item.id == taskId);
            Assert.AreEqual(5, snapshot.reservedWood);
            Assert.AreEqual(5, task.reservedQuantity);
            Assert.AreEqual(5, snapshot.villagers.Sum(item => item.reservedWood));
            Assert.LessOrEqual(task.reservedQuantity + task.inTransitQuantity + task.deliveredQuantity,
                task.requestedQuantity);
        }

        [Test]
        public void SourceShortage_LeavesRemainderPendingWithoutNegativeInventory()
        {
            var simulation = CreateSimulation(5);
            var taskId = simulation.EnqueueLogisticsTask(CityResourceKind.Wood,
                LogisticsEndpointKind.GlobalStock, 0,
                LogisticsEndpointKind.ProductionSite, 1, 10, 3);

            for (var tick = 0; tick < 2000; tick++)
                simulation.Tick(0.1f);

            var snapshot = simulation.GetSnapshot(1001);
            var task = snapshot.logisticsTasks.Find(item => item.id == taskId);
            Assert.AreEqual(0, snapshot.stockWood);
            Assert.AreEqual(0, snapshot.reservedWood);
            Assert.AreEqual(5, snapshot.productionSites[0].storedWood);
            Assert.AreEqual(5, task.deliveredQuantity);
            Assert.AreEqual(LogisticsTaskStatus.Active, task.status);
            Assert.IsTrue(snapshot.villagers.All(item => item.reservedWood >= 0 && item.carryingWood >= 0));
            Assert.AreEqual(5, simulation.TotalWoodInSystem());
        }

        [Test]
        public void DestroyedDestination_CancelsTaskAndReturnsReservationsAndCargo()
        {
            var simulation = CreateSimulation(20);
            var taskId = simulation.EnqueueLogisticsTask(CityResourceKind.Wood,
                LogisticsEndpointKind.GlobalStock, 0,
                LogisticsEndpointKind.ProductionSite, 1, 8, 3);
            for (var tick = 0; tick < 1000 &&
                simulation.GetSnapshot(1001).villagers.All(item => item.carryingWood == 0); tick++)
                simulation.Tick(0.1f);

            Assert.IsTrue(simulation.GetSnapshot(1001).villagers.Any(item => item.carryingWood > 0),
                "Le test doit detruire la destination pendant un transport reel.");
            Assert.IsTrue(simulation.DestroyProductionSite(1));

            var snapshot = simulation.GetSnapshot(1001);
            var task = snapshot.logisticsTasks.Find(item => item.id == taskId);
            Assert.AreEqual(LogisticsTaskStatus.Cancelled, task.status);
            Assert.AreEqual(0, task.reservedQuantity);
            Assert.AreEqual(0, task.inTransitQuantity);
            Assert.AreEqual(20, snapshot.stockWood);
            Assert.AreEqual(0, snapshot.reservedWood);
            Assert.IsTrue(snapshot.villagers.All(item => item.logisticsTaskId == 0 &&
                item.reservedWood == 0 && item.carryingWood == 0));
            Assert.AreEqual(20, simulation.TotalWoodInSystem());
        }

        static LocalCitySimulation CreateSimulation(int stockWood)
        {
            var snapshot = new CitySnapshot
            {
                cityId = 1001,
                seed = 140001,
                elapsedSeconds = 40f,
                stockWood = stockWood,
                employmentDay = -1,
                villagers = Enumerable.Range(1, 4).Select(id => new VillagerState
                {
                    id = id,
                    householdId = id,
                    position = CityPoint.From(new Vector3(id, 0f, 0f))
                }).ToList(),
                households = new List<HouseholdState>()
            };
            snapshot.buildings.Add(new BuildingState
            {
                id = 1,
                archetype = BuildingArchetype.Residence,
                position = CityPoint.From(new Vector3(24f, 0f, 0f)),
                phase = BuildingPhase.Foundation,
                priority = 1,
                requiredWood = 6,
                workRemaining = 12f
            });
            snapshot.buildings.Add(new BuildingState
            {
                id = 2,
                archetype = BuildingArchetype.Residence,
                position = CityPoint.From(new Vector3(32f, 0f, 0f)),
                phase = BuildingPhase.Foundation,
                priority = 1,
                requiredWood = 6,
                workRemaining = 12f
            });
            snapshot.productionSites.Add(new ProductionSiteState
            {
                id = 1,
                kind = ProductionSiteKind.LumberCamp,
                position = CityPoint.From(new Vector3(70f, 0f, 0f)),
                constructionPhase = BuildingPhase.Complete
            });
            snapshot.productionSites.Add(new ProductionSiteState
            {
                id = 2,
                kind = ProductionSiteKind.LumberCamp,
                position = CityPoint.From(new Vector3(90f, 0f, 0f)),
                constructionPhase = BuildingPhase.Complete
            });
            return new LocalCitySimulation(snapshot);
        }
    }
}
