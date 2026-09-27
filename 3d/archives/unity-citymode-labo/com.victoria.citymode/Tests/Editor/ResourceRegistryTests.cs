using System.Linq;
using NUnit.Framework;
using UnityEngine;

namespace Victoria.CityMode.Tests
{
    public sealed class ResourceRegistryTests
    {
        [Test]
        public void DefaultRegistry_DefinesSixUniqueResourcesWithUnitsAndStorage()
        {
            var simulation = CreateSimulation();
            var definitions = simulation.ResourceRegistry.Definitions.ToArray();
            var snapshot = simulation.GetSnapshot(1001);

            Assert.AreEqual(6, definitions.Length);
            Assert.AreEqual(6, definitions.Select(item => item.kind).Distinct().Count());
            Assert.IsTrue(definitions.All(item => !string.IsNullOrWhiteSpace(item.key) &&
                !string.IsNullOrWhiteSpace(item.unitKey) && item.defaultCapacity > 0));
            CollectionAssert.AreEquivalent(new[]
            {
                CityResourceKind.Wood, CityResourceKind.Planks, CityResourceKind.Stone,
                CityResourceKind.Food, CityResourceKind.Tools, CityResourceKind.Textile
            }, snapshot.resources.Select(item => item.kind));
        }

        [Test]
        public void Storage_ClampsOverflowAndReservationsCannotDuplicateOrOverconsume()
        {
            var simulation = CreateSimulation();
            var food = simulation.GetResource(CityResourceKind.Food);
            Assert.AreEqual(120, food.capacity);
            Assert.AreEqual(120, simulation.AddResource(CityResourceKind.Food, 200));
            Assert.AreEqual(0, simulation.AddResource(CityResourceKind.Food, 1));
            Assert.IsTrue(simulation.TryReserveResource(CityResourceKind.Food, 70));
            Assert.IsFalse(simulation.TryReserveResource(CityResourceKind.Food, 51));
            Assert.IsFalse(simulation.TryConsumeReservedResource(CityResourceKind.Food, 71));
            Assert.IsTrue(simulation.TryConsumeReservedResource(CityResourceKind.Food, 20));
            simulation.ReleaseResourceReservation(CityResourceKind.Food, 50);

            food = simulation.GetResource(CityResourceKind.Food);
            Assert.AreEqual(100, food.quantity);
            Assert.AreEqual(0, food.reserved);
        }

        [Test]
        public void DailyLosses_ProtectReservationsAndReloadDeterministically()
        {
            var simulation = CreateSimulation(LocalCitySimulation.SecondsPerGameDay - 0.05f);
            Assert.AreEqual(100, simulation.AddResource(CityResourceKind.Food, 100));
            Assert.IsTrue(simulation.TryReserveResource(CityResourceKind.Food, 50));
            var before = simulation.GetSnapshot(1001);
            var reloaded = new LocalCitySimulation(before);

            simulation.Tick(0.1f);
            reloaded.Tick(0.1f);

            var after = simulation.GetSnapshot(1001);
            var food = after.resources.Find(item => item.kind == CityResourceKind.Food);
            Assert.AreEqual(99, food.quantity);
            Assert.AreEqual(50, food.reserved);
            Assert.AreEqual(1, food.totalLost);
            Assert.AreEqual(JsonUtility.ToJson(after), JsonUtility.ToJson(reloaded.GetSnapshot(1001)));
        }

        static LocalCitySimulation CreateSimulation(float elapsed = 0f) =>
            new LocalCitySimulation(new CitySnapshot
            {
                cityId = 1001,
                seed = 140001,
                elapsedSeconds = elapsed
            });
    }
}
