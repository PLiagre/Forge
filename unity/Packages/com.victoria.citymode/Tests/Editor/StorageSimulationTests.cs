using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEngine;

namespace Victoria.CityMode.Tests
{
    public sealed class StorageSimulationTests
    {
        [Test]
        public void GranaryAndWarehouseExposeCategoriesCapacityAndServiceZones()
        {
            var simulation = new LocalCitySimulation(CreateSnapshot(false));
            var snapshot = simulation.GetSnapshot(1001);
            var granary = snapshot.buildings.Find(item => item.archetype == BuildingArchetype.Granary);
            var warehouse = snapshot.buildings.Find(item => item.archetype == BuildingArchetype.Warehouse);

            Assert.AreEqual(1, granary.localStocks.Count);
            Assert.AreEqual(CityResourceKind.Food, granary.localStocks[0].kind);
            Assert.AreEqual(120, granary.localStocks[0].capacity);
            Assert.AreEqual(5, warehouse.localStocks.Count);
            Assert.AreEqual(160, warehouse.localStocks.Sum(item => item.capacity));
            Assert.Greater(granary.storageServiceRadius, 0f);
            Assert.AreEqual(granary.id,
                simulation.FindNearestStorage(CityResourceKind.Food, new Vector3(2f, 0f, 0f)).id);
            Assert.IsNull(simulation.FindNearestStorage(CityResourceKind.Food,
                new Vector3(240f, 0f, 240f)));
            Assert.AreEqual(warehouse.id,
                simulation.FindNearestStorage(CityResourceKind.Textile, new Vector3(42f, 0f, 0f)).id);
        }

        [Test]
        public void PresentKeeperPhysicallyMovesFoodIntoGranary()
        {
            var simulation = new LocalCitySimulation(CreateSnapshot(true));
            Assert.AreEqual(60, simulation.AddResource(CityResourceKind.Food, 60));
            var observedFoodCargo = false;

            for (var tick = 0; tick < 6000; tick++)
            {
                simulation.Tick(0.1f);
                var current = simulation.GetSnapshot(1001);
                observedFoodCargo |= current.villagers.Any(item => item.carryingWood > 0 &&
                    item.carryingResource == CityResourceKind.Food);
                var stored = current.buildings.Find(item => item.archetype == BuildingArchetype.Granary)
                    .localStocks[0].quantity;
                if (stored > 0 && observedFoodCargo)
                    break;
            }

            var snapshot = simulation.GetSnapshot(1001);
            var granary = snapshot.buildings.Find(item => item.archetype == BuildingArchetype.Granary);
            Assert.IsTrue(observedFoodCargo);
            Assert.Greater(granary.localStocks[0].quantity, 0);
            Assert.IsTrue(snapshot.logisticsTasks.Any(item => item.resource == CityResourceKind.Food &&
                item.destinationId == granary.id && item.deliveredQuantity > 0));
        }

        [Test]
        public void OverfilledStorageRebalancesBackTowardHalfCapacity()
        {
            var initial = CreateSnapshot(true);
            var granary = initial.buildings.Find(item => item.archetype == BuildingArchetype.Granary);
            granary.localStocks.Add(new StoredResourceState
            {
                kind = CityResourceKind.Food,
                quantity = 100,
                capacity = 120
            });
            var simulation = new LocalCitySimulation(initial);

            for (var tick = 0; tick < 6000 &&
                simulation.GetResource(CityResourceKind.Food).quantity == 0; tick++)
                simulation.Tick(0.1f);

            var snapshot = simulation.GetSnapshot(1001);
            var after = snapshot.buildings.Find(item => item.id == granary.id).localStocks[0];
            Assert.Greater(snapshot.resources.Find(item => item.kind == CityResourceKind.Food).quantity, 0);
            Assert.Less(after.quantity, 100);
            Assert.GreaterOrEqual(after.quantity, 60);
        }

        static CitySnapshot CreateSnapshot(bool withWorkers)
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
                archetype = BuildingArchetype.Warehouse,
                position = CityPoint.From(new Vector3(40f, 0f, 0f)),
                phase = BuildingPhase.Complete
            });
            if (!withWorkers)
                return snapshot;
            for (var id = 1; id <= 4; id++)
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
