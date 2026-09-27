using NUnit.Framework;
using UnityEngine;

namespace Victoria.CityMode.Tests
{
    public sealed class TradeSimulationTests
    {
        [Test]
        public void ImportPaysFeeTravelsForTwoDaysAndDeliversWithinCapacity()
        {
            var simulation = CreateSimulation();
            var orderId = simulation.PlaceTradeOrder(TradeDirection.Import,
                CityResourceKind.Food, 20);
            Assert.Greater(orderId, 0);
            var placed = simulation.GetSnapshot(1001);
            Assert.AreEqual(44, placed.reservedTradeCoins);
            Assert.AreEqual(2, placed.tradeOrders[0].deliveryDay);

            AdvanceDays(simulation, 2);

            var after = simulation.GetSnapshot(1001);
            var order = after.tradeOrders[0];
            Assert.AreEqual(TradeOrderStatus.Completed, order.status);
            Assert.AreEqual(20, order.deliveredQuantity);
            Assert.AreEqual(20, after.resources.Find(item => item.kind == CityResourceKind.Food).quantity);
            Assert.AreEqual(956, after.treasuryCoins);
            Assert.AreEqual(0, after.reservedTradeCoins);
            Assert.AreEqual(1f, order.travelProgress);
        }

        [Test]
        public void ExportReservesStockAndCancellationOrSettlementNeverDuplicatesIt()
        {
            var simulation = CreateSimulation();
            simulation.AddResource(CityResourceKind.Tools, 10);
            var cancelled = simulation.PlaceTradeOrder(TradeDirection.Export,
                CityResourceKind.Tools, 5);
            Assert.IsTrue(simulation.CancelTradeOrder(cancelled));
            Assert.AreEqual(0, simulation.GetResource(CityResourceKind.Tools).reserved);
            Assert.AreEqual(10, simulation.GetResource(CityResourceKind.Tools).quantity);

            var completed = simulation.PlaceTradeOrder(TradeDirection.Export,
                CityResourceKind.Tools, 5);
            Assert.Greater(completed, 0);
            AdvanceDays(simulation, 2);

            var after = simulation.GetSnapshot(1001);
            var order = after.tradeOrders.Find(item => item.id == completed);
            Assert.AreEqual(TradeOrderStatus.Completed, order.status);
            Assert.AreEqual(5, after.resources.Find(item => item.kind == CityResourceKind.Tools).quantity);
            Assert.AreEqual(1036, after.treasuryCoins);
            Assert.AreEqual(36, order.balanceDelta);
        }

        [Test]
        public void VolumeFundsAndCapacityLimitsAreDeterministicAcrossReload()
        {
            var simulation = CreateSimulation();
            Assert.AreEqual(0, simulation.PlaceTradeOrder(TradeDirection.Import,
                CityResourceKind.Food, 41));
            var poor = new LocalCitySimulation(new CitySnapshot
            {
                cityId = 1001,
                seed = 140001,
                treasuryCoins = 10
            });
            Assert.AreEqual(0, poor.PlaceTradeOrder(TradeDirection.Import,
                CityResourceKind.Tools, 40));
            simulation.AddResource(CityResourceKind.Food, 110);
            Assert.AreEqual(0, simulation.PlaceTradeOrder(TradeDirection.Import,
                CityResourceKind.Food, 20));
            var orderId = simulation.PlaceTradeOrder(TradeDirection.Import,
                CityResourceKind.Stone, 20);
            Assert.Greater(orderId, 0);

            for (var tick = 0; tick < 700; tick++)
                simulation.Tick(0.1f);
            var middle = simulation.GetSnapshot(1001);
            Assert.That(middle.tradeOrders.Find(item => item.id == orderId).travelProgress,
                Is.GreaterThan(0f).And.LessThan(1f));
            var reloaded = new LocalCitySimulation(middle);

            AdvanceDays(simulation, 2);
            AdvanceDays(reloaded, 2);
            Assert.AreEqual(JsonUtility.ToJson(simulation.GetSnapshot(1001)),
                JsonUtility.ToJson(reloaded.GetSnapshot(1001)));
        }

        static LocalCitySimulation CreateSimulation() =>
            new LocalCitySimulation(new CitySnapshot
            {
                cityId = 1001,
                seed = 140001,
                treasuryCoins = 1000
            });

        static void AdvanceDays(LocalCitySimulation simulation, int days)
        {
            var targetDay = simulation.GetSnapshot(1001).calendar.absoluteDay + days;
            while (simulation.GetSnapshot(1001).calendar.absoluteDay < targetDay)
                simulation.Tick(0.1f);
        }
    }
}
