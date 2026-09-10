using System;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Text;
using UnityEngine;

namespace Victoria.CityMode
{
    [Serializable]
    public sealed class CityLongRunReport
    {
        public int seed;
        public int requestedDays;
        public int completedDays;
        public int ticks;
        public int navigationFailures;
        public int blockedAgents;
        public int minimumResourceQuantity = int.MaxValue;
        public string finalHash;
        public string failureReason;
        public CitySnapshot finalSnapshot;
        public bool succeeded => string.IsNullOrEmpty(failureReason);
    }

    public static class CityLongRunHarness
    {
        const float FixedStep = 0.1f;
        const int BlockedAgentThresholdTicks = 300;

        public static CityLongRunReport Run(CitySnapshot initial, int days,
            BuildingCatalog catalog = null)
        {
            if (initial == null || initial.cityId <= 0)
                throw new ArgumentException("Snapshot de harnais invalide.", nameof(initial));
            if (days <= 0)
                throw new ArgumentOutOfRangeException(nameof(days));
            var simulation = new LocalCitySimulation(initial, catalog);
            var report = new CityLongRunReport
            {
                seed = initial.seed,
                requestedDays = days
            };
            var positions = new Dictionary<int, CityPoint>();
            var stalledTicks = new Dictionary<int, int>();
            var targetElapsed = simulation.DiagnosticState.elapsedSeconds +
                days * LocalCitySimulation.SecondsPerGameDay;
            var maximumTicks = Mathf.CeilToInt(days * LocalCitySimulation.SecondsPerGameDay / FixedStep) + 4;

            for (var tick = 0; tick < maximumTicks; tick++)
            {
                var before = simulation.DiagnosticState;
                if (before.elapsedSeconds + 0.0001f >= targetElapsed)
                    break;
                simulation.Tick(Mathf.Min(FixedStep, targetElapsed - before.elapsedSeconds));
                report.ticks++;
                var snapshot = simulation.DiagnosticState;
                if (!ValidateResources(snapshot, report) || !ValidateMovement(snapshot, positions, stalledTicks, report))
                    break;
            }

            report.finalSnapshot = simulation.GetSnapshot(initial.cityId);
            report.completedDays = report.finalSnapshot.calendar.absoluteDay -
                Mathf.FloorToInt(initial.elapsedSeconds / LocalCitySimulation.SecondsPerGameDay);
            report.navigationFailures = report.finalSnapshot.navigationFailures;
            if (string.IsNullOrEmpty(report.failureReason) && report.navigationFailures != 0)
                report.failureReason = "navigation-failure";
            if (string.IsNullOrEmpty(report.failureReason) &&
                report.finalSnapshot.elapsedSeconds + 0.001f < targetElapsed)
                report.failureReason = "duration-incomplete";
            report.finalHash = Sha256(JsonUtility.ToJson(report.finalSnapshot));
            return report;
        }

        static bool ValidateResources(CitySnapshot snapshot, CityLongRunReport report)
        {
            report.minimumResourceQuantity = Mathf.Min(report.minimumResourceQuantity,
                snapshot.stockWood, snapshot.reservedWood);
            if (snapshot.stockWood < 0 || snapshot.reservedWood < 0 ||
                snapshot.reservedWood > snapshot.stockWood)
            {
                report.failureReason = "global-resource-invariant";
                return false;
            }
            foreach (var villager in snapshot.villagers)
            {
                report.minimumResourceQuantity = Mathf.Min(report.minimumResourceQuantity,
                    villager.carryingWood, villager.reservedWood, villager.carryingFood);
                if (villager.carryingWood < 0 || villager.reservedWood < 0 || villager.carryingFood < 0)
                {
                    report.failureReason = "villager-resource-negative";
                    return false;
                }
            }
            foreach (var site in snapshot.productionSites)
            {
                report.minimumResourceQuantity = Mathf.Min(report.minimumResourceQuantity,
                    site.remainingTimber, site.storedWood, site.reservedWood,
                    site.inputAStored, site.inputBStored, site.outputStored,
                    site.outputReserved, site.rawRemaining);
                if (site.remainingTimber < 0 || site.storedWood < 0 || site.reservedWood < 0 ||
                    site.reservedWood > site.storedWood || site.inputAStored < 0 ||
                    site.inputBStored < 0 || site.outputStored < 0 || site.outputReserved < 0 ||
                    site.outputReserved > site.outputStored || site.rawRemaining < 0 ||
                    site.totalBatches < 0)
                {
                    report.failureReason = "site-resource-invariant";
                    return false;
                }
            }
            foreach (var task in snapshot.logisticsTasks)
            {
                report.minimumResourceQuantity = Mathf.Min(report.minimumResourceQuantity,
                    task.reservedQuantity, task.inTransitQuantity, task.deliveredQuantity);
                if (task.requestedQuantity < 0 || task.reservedQuantity < 0 ||
                    task.inTransitQuantity < 0 || task.deliveredQuantity < 0 ||
                    task.reservedQuantity + task.inTransitQuantity + task.deliveredQuantity >
                    task.requestedQuantity)
                {
                    report.failureReason = "logistics-resource-invariant";
                    return false;
                }
            }
            foreach (var building in snapshot.buildings)
            {
                if (building.marketCoveredHouseholds < 0 || building.marketScarcityPermille < 0 ||
                    building.marketScarcityPermille > 1000 || building.marketPricePermille < 0 ||
                    building.marketPricePermille > 2000 || building.marketShortageDays < 0)
                {
                    report.failureReason = "market-invariant";
                    return false;
                }
                foreach (var local in building.localStocks)
                {
                    report.minimumResourceQuantity = Mathf.Min(report.minimumResourceQuantity,
                        local.quantity, local.reserved);
                    if (local.quantity < 0 || local.reserved < 0 ||
                        local.reserved > local.quantity || local.quantity > local.capacity)
                    {
                        report.failureReason = "local-storage-invariant";
                        return false;
                    }
                }
            }
            foreach (var resource in snapshot.resources)
            {
                report.minimumResourceQuantity = Mathf.Min(report.minimumResourceQuantity,
                    resource.quantity, resource.reserved);
                if (resource.quantity < 0 || resource.reserved < 0 ||
                    resource.reserved > resource.quantity || resource.quantity > resource.capacity)
                {
                    report.failureReason = "registry-resource-invariant";
                    return false;
                }
            }
            foreach (var source in snapshot.foodSources)
                if (source.remainingFood < 0)
                {
                    report.failureReason = "food-source-negative";
                    return false;
                }
            foreach (var household in snapshot.households)
                if (household.foodShortageDays < 0 || household.fuelShortageDays < 0 ||
                    household.clothingShortageDays < 0 || household.toolShortageDays < 0 ||
                    household.satisfactionPermille < 0 || household.satisfactionPermille > 1000)
                {
                    report.failureReason = "household-needs-invariant";
                    return false;
                }
            foreach (var field in snapshot.fields)
                if (field.fertilityPermille < 0 || field.fertilityPermille > 1000 ||
                    field.growthPoints < 0 || field.totalHarvested < 0)
                {
                    report.failureReason = "field-invariant";
                    return false;
                }
            if (snapshot.treasuryCoins < 0 || snapshot.reservedTradeCoins < 0 ||
                snapshot.reservedTradeCoins > snapshot.treasuryCoins)
            {
                report.failureReason = "trade-balance-invariant";
                return false;
            }
            foreach (var order in snapshot.tradeOrders)
                if (order.requestedQuantity <= 0 || order.requestedQuantity > 40 ||
                    order.deliveredQuantity < 0 || order.deliveredQuantity > order.requestedQuantity ||
                    order.travelProgress < 0f || order.travelProgress > 1f)
                {
                    report.failureReason = "trade-order-invariant";
                    return false;
                }
            return true;
        }

        static bool ValidateMovement(CitySnapshot snapshot, Dictionary<int, CityPoint> positions,
            Dictionary<int, int> stalledTicks, CityLongRunReport report)
        {
            foreach (var villager in snapshot.villagers)
            {
                var isMoving = villager.activity == VillagerActivity.GoingToStock ||
                    villager.activity == VillagerActivity.GoingToSite ||
                    villager.activity == VillagerActivity.GoingToWork ||
                    villager.activity == VillagerActivity.GoingHome;
                var stalled = 0;
                if (isMoving && positions.TryGetValue(villager.id, out var previous) &&
                    PlanarSqrDistance(previous, villager.position) < 0.000001f)
                    stalledTicks.TryGetValue(villager.id, out stalled);
                stalled = isMoving ? stalled + 1 : 0;
                stalledTicks[villager.id] = stalled;
                positions[villager.id] = villager.position;
                if (stalled < BlockedAgentThresholdTicks)
                    continue;
                report.blockedAgents++;
                report.failureReason = "agent-blocked-" + villager.id;
                return false;
            }
            return true;
        }

        static float PlanarSqrDistance(CityPoint left, CityPoint right)
        {
            var x = left.x - right.x;
            var z = left.z - right.z;
            return x * x + z * z;
        }

        static string Sha256(string text)
        {
            using (var sha = SHA256.Create())
            {
                var bytes = sha.ComputeHash(Encoding.UTF8.GetBytes(text));
                var builder = new StringBuilder(bytes.Length * 2);
                foreach (var value in bytes)
                    builder.Append(value.ToString("x2"));
                return builder.ToString();
            }
        }
    }
}
