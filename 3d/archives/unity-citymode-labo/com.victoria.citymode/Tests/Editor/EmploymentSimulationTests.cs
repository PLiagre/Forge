using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEngine;

namespace Victoria.CityMode.Tests
{
    public sealed class EmploymentSimulationTests
    {
        [Test]
        public void Employment_AssignsExclusivePhysicalSlotsWithoutDoubleCounting()
        {
            var simulation = CreateSimulation(140001, false);
            Assert.IsTrue(simulation.Submit(CityCommand.PlaceLumberCamp(new Vector3(70f, 0f, 0f))).accepted);
            Assert.IsTrue(simulation.Submit(CityCommand.PlaceBuilding(
                BuildingArchetype.Granary, new Vector3(40f, 0f, 40f))).accepted);

            var snapshot = simulation.GetSnapshot(1001);
            Assert.AreEqual(2, snapshot.productionSites[0].assignedWorkers);
            Assert.AreEqual(2, snapshot.villagers.Count(item => item.job == VillagerJob.Lumberjack));
            Assert.AreEqual(2, snapshot.villagers.Count(item => item.job == VillagerJob.Builder));
            Assert.IsTrue(snapshot.villagers.All(item =>
                item.workplaceBuildingId == 0 || item.workplaceProductionSiteId == 0));
            Assert.IsTrue(snapshot.villagers.Where(item => item.job != VillagerJob.None).All(item =>
                item.workplaceBuildingId != 0 || item.workplaceProductionSiteId != 0));
        }

        [Test]
        public void ScheduledWorkers_CommuteWorkAndReturnHome()
        {
            var simulation = CreateSimulation(140001, true);
            for (var tick = 0; tick < 700; tick++)
                simulation.Tick(0.1f);

            var atWork = simulation.GetSnapshot(1001);
            var keepers = atWork.villagers.Where(item => item.job == VillagerJob.GranaryKeeper).ToArray();
            Assert.AreEqual(2, keepers.Length);
            Assert.IsTrue(keepers.All(item => item.activity == VillagerActivity.WorkingJob && item.isAtWork),
                JsonUtility.ToJson(atWork));
            Assert.IsTrue(keepers.All(item => item.position.x > 20f),
                "Le trajet vers le lieu de travail doit etre physique.");

            for (var tick = 0; tick < 600; tick++)
                simulation.Tick(0.1f);
            var afterShift = simulation.GetSnapshot(1001);
            Assert.IsTrue(afterShift.villagers.Where(item => item.job == VillagerJob.GranaryKeeper)
                .All(item => !item.isAtWork &&
                    (item.activity == VillagerActivity.GoingHome || item.activity == VillagerActivity.Idle)));
        }

        [Test]
        public void DailyAbsence_IsReplacedAndEntireRunRemainsDeterministic()
        {
            var seed = FindSeedWithFirstWorkerAbsentOnDayOne();
            var left = CreateSimulation(seed, true);
            var right = CreateSimulation(seed, true);
            for (var tick = 0; tick < 1202; tick++)
            {
                left.Tick(0.1f);
                right.Tick(0.1f);
            }

            var snapshot = left.GetSnapshot(1001);
            Assert.IsTrue(snapshot.villagers[0].absentToday);
            Assert.AreEqual(VillagerJob.None, snapshot.villagers[0].job);
            Assert.GreaterOrEqual(snapshot.jobAbsences, 1);
            Assert.GreaterOrEqual(snapshot.jobReplacements, 1);
            Assert.AreEqual(2, snapshot.villagers.Count(item => item.job == VillagerJob.GranaryKeeper));
            Assert.AreEqual(JsonUtility.ToJson(snapshot), JsonUtility.ToJson(right.GetSnapshot(1001)));
        }

        [Test]
        public void EmploymentState_ReloadsWithoutReassignmentOrClockDrift()
        {
            var simulation = CreateSimulation(140001, true);
            for (var tick = 0; tick < 715; tick++)
                simulation.Tick(0.1f);
            var before = simulation.GetSnapshot(1001);

            var reloaded = new LocalCitySimulation(before);

            Assert.AreEqual(JsonUtility.ToJson(before),
                JsonUtility.ToJson(reloaded.GetSnapshot(1001)));
        }

        static LocalCitySimulation CreateSimulation(int seed, bool completedGranary)
        {
            var snapshot = new CitySnapshot
            {
                cityId = 1001,
                seed = seed,
                stockWood = 500,
                households = new List<HouseholdState>(),
                villagers = Enumerable.Range(1, 8).Select(id => new VillagerState
                {
                    id = id,
                    householdId = id,
                    position = CityPoint.From(new Vector3(id * 0.25f, 0f, 0f))
                }).ToList()
            };
            if (completedGranary)
            {
                snapshot.buildings.Add(new BuildingState
                {
                    id = 1,
                    archetype = BuildingArchetype.Granary,
                    position = CityPoint.From(new Vector3(40f, 0f, 0f)),
                    phase = BuildingPhase.Complete,
                    priority = 1
                });
            }
            return new LocalCitySimulation(snapshot);
        }

        static int FindSeedWithFirstWorkerAbsentOnDayOne()
        {
            for (var seed = 1; seed < 10000; seed++)
                if (!Absent(seed, 1, 0) && Absent(seed, 1, 1))
                    return seed;
            Assert.Fail("Aucune graine d'absence deterministe trouvee.");
            return 0;
        }

        static bool Absent(int seed, int villagerId, int day)
        {
            unchecked
            {
                var value = seed * 486187739 + villagerId * 16777619 + day * 374761393;
                return (value & 0x7fffffff) % 19 == 0;
            }
        }
    }
}
