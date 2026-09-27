using NUnit.Framework;
using UnityEngine;

namespace Victoria.CityMode.Tests
{
    public sealed class AgricultureSimulationTests
    {
        [Test]
        public void SpringField_ProgressesFromPlowingThroughSowingAndGrowthToHarvest()
        {
            var simulation = CreateAtDayBoundary(90);
            var fieldId = simulation.AddAgriculturalField(new Vector3(30f, 0f, 30f), 800);
            simulation.Tick(0.1f);
            Assert.AreEqual(FieldPhase.Plowing,
                simulation.GetSnapshot(1001).fields.Find(item => item.id == fieldId).phase);

            AdvanceDays(simulation, 4);
            Assert.AreEqual(FieldPhase.Growing,
                simulation.GetSnapshot(1001).fields.Find(item => item.id == fieldId).phase);

            for (var day = 0; day < 40 &&
                simulation.GetSnapshot(1001).fields[0].totalHarvested == 0; day++)
                AdvanceDays(simulation, 1);
            var snapshot = simulation.GetSnapshot(1001);
            var field = snapshot.fields[0];
            Assert.Greater(field.totalHarvested, 0);
            Assert.Greater(snapshot.resources.Find(item => item.kind == CityResourceKind.Food).quantity, 0);
            Assert.That(field.phase, Is.EqualTo(FieldPhase.Harvested).Or.EqualTo(FieldPhase.Fallow));
        }

        [Test]
        public void FallowRecoversFertilityAndDailyWeatherIsDeterministic()
        {
            var left = CreateAtDayBoundary(1);
            left.AddAgriculturalField(new Vector3(20f, 0f, 20f), 500);
            var right = new LocalCitySimulation(left.GetSnapshot(1001));

            AdvanceDays(left, 10);
            AdvanceDays(right, 10);

            var leftSnapshot = left.GetSnapshot(1001);
            Assert.AreEqual(550, leftSnapshot.fields[0].fertilityPermille);
            Assert.AreEqual(JsonUtility.ToJson(leftSnapshot), JsonUtility.ToJson(right.GetSnapshot(1001)));
        }

        [Test]
        public void DailyWeatherControlsGrowthWithoutBreakingFertilityBounds()
        {
            const int day = 90;
            var simulation = new LocalCitySimulation(new CitySnapshot
            {
                cityId = 1001,
                seed = 140001,
                elapsedSeconds = day * LocalCitySimulation.SecondsPerGameDay - 0.05f,
                resourceLossDay = day - 1,
                weatherDay = day - 1,
                fields = new System.Collections.Generic.List<AgriculturalFieldState>
                {
                    new AgriculturalFieldState
                    {
                        id = 1,
                        position = CityPoint.From(new Vector3(30f, 0f, 30f)),
                        fertilityPermille = 800,
                        phase = FieldPhase.Growing,
                        lastProcessedDay = day - 1
                    }
                }
            });

            simulation.Tick(0.1f);
            var snapshot = simulation.GetSnapshot(1001);
            var expectedGrowth = snapshot.dailyWeather == CityWeather.Rain ? 2 :
                snapshot.dailyWeather == CityWeather.Drought || snapshot.dailyWeather == CityWeather.Frost ? 0 : 1;
            Assert.AreEqual(expectedGrowth, snapshot.fields[0].growthPoints);
            Assert.AreEqual(798, snapshot.fields[0].fertilityPermille);
            Assert.That(snapshot.fields[0].fertilityPermille, Is.InRange(0, 1000));
        }

        static LocalCitySimulation CreateAtDayBoundary(int day) =>
            new LocalCitySimulation(new CitySnapshot
            {
                cityId = 1001,
                seed = 140001,
                elapsedSeconds = day * LocalCitySimulation.SecondsPerGameDay - 0.05f
            });

        static void AdvanceDays(LocalCitySimulation simulation, int days)
        {
            var targetDay = simulation.GetSnapshot(1001).calendar.absoluteDay + days;
            while (simulation.GetSnapshot(1001).calendar.absoluteDay < targetDay)
                simulation.Tick(0.1f);
        }
    }
}
