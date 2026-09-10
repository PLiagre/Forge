using NUnit.Framework;
using UnityEngine;

namespace Victoria.CityMode.Tests
{
    public sealed class EconomyTwoHourSimulationTests
    {
        [Test]
        public void ReferenceEconomyProgressesForTwoGameHoursWithoutInvariantFailure()
        {
            var report = CityLongRunHarness.Run(
                LongRunSimulationTests.CreateReferenceSnapshot(), 60);

            Assert.IsTrue(report.succeeded, report.failureReason);
            Assert.AreEqual(60, report.completedDays);
            Assert.AreEqual(71954, report.ticks);
            Assert.AreEqual(0, report.navigationFailures);
            Assert.AreEqual(0, report.blockedAgents);
            Assert.GreaterOrEqual(report.minimumResourceQuantity, 0);
            Assert.Greater(report.finalSnapshot.households.Count, 0);
            Assert.IsTrue(report.finalSnapshot.households.TrueForAll(item =>
                item.satisfactionPermille >= 0 && item.satisfactionPermille <= 1000));
            Debug.Log($"CITYLAB_M2_TWO_HOURS_OK days=60 ticks={report.ticks} " +
                $"hash={report.finalHash} minResource={report.minimumResourceQuantity} " +
                $"navigationFailures={report.navigationFailures} blockedAgents={report.blockedAgents}");
        }
    }
}
