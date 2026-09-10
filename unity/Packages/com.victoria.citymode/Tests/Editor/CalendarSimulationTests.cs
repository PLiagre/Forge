using NUnit.Framework;
using UnityEngine;

namespace Victoria.CityMode.Tests
{
    public sealed class CalendarSimulationTests
    {
        [Test]
        public void Calendar_CrossesMonthSeasonAndYearDeterministically()
        {
            var seasonBoundary = CreateSimulation(LocalCitySimulation.SecondsPerGameDay * 90f - 0.05f);
            seasonBoundary.Tick(0.1f);
            var spring = seasonBoundary.GetSnapshot(1001).calendar;
            Assert.AreEqual(1, spring.year);
            Assert.AreEqual(4, spring.month);
            Assert.AreEqual(1, spring.day);
            Assert.AreEqual(CitySeason.Spring, spring.season);

            var yearBoundary = CreateSimulation(LocalCitySimulation.SecondsPerGameDay * 360f - 0.05f);
            yearBoundary.Tick(0.1f);
            var newYear = yearBoundary.GetSnapshot(1001).calendar;
            Assert.AreEqual(2, newYear.year);
            Assert.AreEqual(1, newYear.month);
            Assert.AreEqual(1, newYear.day);
            Assert.AreEqual(CitySeason.Winter, newYear.season);
        }

        [Test]
        public void ScheduledEvents_TriggerInStableTimeThenIdOrder()
        {
            var simulation = CreateSimulation(40f);
            var firstId = simulation.ScheduleEvent(ScheduledCityEventKind.Weather, "fog", 0.2f);
            var secondId = simulation.ScheduleEvent(ScheduledCityEventKind.Economy, "market", 0.2f);
            simulation.Tick(0.1f);
            Assert.IsTrue(simulation.GetSnapshot(1001).scheduledEvents.TrueForAll(item =>
                item.status == ScheduledCityEventStatus.Pending));

            simulation.Tick(0.1f);

            var events = simulation.GetSnapshot(1001).scheduledEvents;
            Assert.AreEqual(firstId, events[0].id);
            Assert.AreEqual(secondId, events[1].id);
            Assert.IsTrue(events.TrueForAll(item => item.status == ScheduledCityEventStatus.Triggered));
            Assert.AreEqual(events[0].triggeredAtElapsedSeconds, events[1].triggeredAtElapsedSeconds);
        }

        [Test]
        public void ClockPauseCalendarAndPendingEvents_ReloadExactly()
        {
            var simulation = CreateSimulation(1234.5f);
            simulation.SetSimulationSpeed(4f);
            simulation.SetSimulationSpeed(0f);
            simulation.ScheduleEvent(ScheduledCityEventKind.Marker, "reload-proof", 12f);
            var before = simulation.GetSnapshot(1001);

            var document = CitySaveService.Serialize(before);
            Assert.IsTrue(CitySaveService.TryDeserialize(document, out var loaded, out var reason), reason);
            var reloaded = new LocalCitySimulation(loaded);
            var after = reloaded.GetSnapshot(1001);

            Assert.AreEqual(JsonUtility.ToJson(before), JsonUtility.ToJson(after));
            Assert.IsTrue(reloaded.IsPaused);
            Assert.AreEqual(4f, reloaded.LastRunningSpeed);
            Assert.AreEqual(before.calendar.year, after.calendar.year);
            Assert.AreEqual(ScheduledCityEventStatus.Pending, after.scheduledEvents[0].status);
        }

        static LocalCitySimulation CreateSimulation(float elapsedSeconds) =>
            new LocalCitySimulation(new CitySnapshot
            {
                cityId = 1001,
                seed = 140001,
                elapsedSeconds = elapsedSeconds
            });
    }
}
