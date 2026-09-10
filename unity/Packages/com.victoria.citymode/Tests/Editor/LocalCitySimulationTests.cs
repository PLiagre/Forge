using NUnit.Framework;
using UnityEngine;

namespace Victoria.CityMode.Tests
{
    public sealed class LocalCitySimulationTests
    {
        const string Fixture = @"{
          ""schemaVersion"":1,""cityId"":1001,""seed"":140001,""stockWood"":72,
          ""households"":[
            {""id"":1,""memberCount"":3},{""id"":2,""memberCount"":4},
            {""id"":3,""memberCount"":2},{""id"":4,""memberCount"":5},
            {""id"":5,""memberCount"":3},{""id"":6,""memberCount"":4}],
          ""roads"":[],""parcels"":[],""buildings"":[],
          ""villagers"":[
            {""id"":1,""householdId"":1,""position"":{""x"":-5,""z"":-5}},
            {""id"":2,""householdId"":1,""position"":{""x"":-3,""z"":-6}},
            {""id"":3,""householdId"":2,""position"":{""x"":-1,""z"":-5}},
            {""id"":4,""householdId"":3,""position"":{""x"":1,""z"":-6}},
            {""id"":5,""householdId"":4,""position"":{""x"":3,""z"":-5}},
            {""id"":6,""householdId"":5,""position"":{""x"":5,""z"":-6}},
            {""id"":7,""householdId"":6,""position"":{""x"":7,""z"":-5}},
            {""id"":8,""householdId"":6,""position"":{""x"":9,""z"":-6}}] }";

        [Test]
        public void SameFixtureAndCommands_ProduceSameSnapshot()
        {
            var left = LocalCitySimulation.FromJson(Fixture);
            var right = LocalCitySimulation.FromJson(Fixture);
            var command = CityCommand.DrawRoad(new Vector3(-42, 0, 12), new Vector3(42, 0, 12));
            var leftRoad = left.Submit(command);
            var rightRoad = right.Submit(command);
            left.Submit(CityCommand.ZoneResidential(leftRoad.createdId));
            right.Submit(CityCommand.ZoneResidential(rightRoad.createdId));
            for (var i = 0; i < 500; i++)
            {
                left.Tick(0.1f);
                right.Tick(0.1f);
            }

            Assert.AreEqual(JsonUtility.ToJson(left.GetSnapshot(1001)), JsonUtility.ToJson(right.GetSnapshot(1001)));
        }

        [Test]
        public void InvalidRoad_IsRejectedWithReason()
        {
            var simulation = LocalCitySimulation.FromJson(Fixture);
            var result = simulation.Submit(CityCommand.DrawRoad(Vector3.zero, Vector3.one));
            Assert.IsFalse(result.accepted);
            Assert.AreEqual("road-too-short", result.reason);
            Assert.AreEqual(0, simulation.GetSnapshot(1001).roads.Count);
        }

        [Test]
        public void Construction_ConservesWoodAndCompletesAHome()
        {
            var simulation = LocalCitySimulation.FromJson(Fixture);
            var initialWood = simulation.TotalWoodInSystem();
            var road = simulation.Submit(CityCommand.DrawRoad(new Vector3(-42, 0, 12), new Vector3(42, 0, 12)));
            Assert.IsTrue(road.accepted);
            Assert.IsTrue(simulation.Submit(CityCommand.ZoneResidential(road.createdId)).accepted);

            for (var i = 0; i < 5000; i++)
                simulation.Tick(0.1f);

            var snapshot = simulation.GetSnapshot(1001);
            Assert.AreEqual(initialWood, simulation.TotalWoodInSystem(), "Le bois ne doit etre ni cree ni perdu.");
            Assert.That(snapshot.buildings.FindAll(item => item.phase == BuildingPhase.Complete).Count, Is.GreaterThan(0));
            Assert.That(snapshot.households.FindAll(item => item.homeBuildingId != 0).Count, Is.GreaterThan(0));
            Assert.GreaterOrEqual(snapshot.stockWood, 0);
        }

        [Test]
        public void BlockedRoad_ReleasesReservationsAndReplansWorkers()
        {
            var simulation = LocalCitySimulation.FromJson(Fixture);
            var initialWood = simulation.TotalWoodInSystem();
            var road = simulation.Submit(CityCommand.DrawRoad(new Vector3(-42, 0, 12), new Vector3(42, 0, 12)));
            simulation.Submit(CityCommand.ZoneResidential(road.createdId));
            for (var i = 0; i < 15; i++)
                simulation.Tick(0.1f);

            Assert.IsTrue(simulation.SetRoadBlocked(road.createdId, true));
            var snapshot = simulation.GetSnapshot(1001);
            Assert.AreEqual(0, snapshot.reservedWood);
            Assert.AreEqual(initialWood, simulation.TotalWoodInSystem());
            Assert.That(snapshot.villagers.TrueForAll(item => item.activity == VillagerActivity.Idle), Is.True);
        }

        [Test]
        public void ZoningUnknownOrBlockedRoad_IsRejected()
        {
            var simulation = LocalCitySimulation.FromJson(Fixture);
            Assert.AreEqual("road-unknown", simulation.Submit(CityCommand.ZoneResidential(999)).reason);
            var road = simulation.Submit(CityCommand.DrawRoad(new Vector3(-20, 0, 0), new Vector3(20, 0, 0)));
            simulation.SetRoadBlocked(road.createdId, true);
            Assert.AreEqual("road-inaccessible", simulation.Submit(CityCommand.ZoneResidential(road.createdId)).reason);
        }

        [Test]
        public void ConstructionPriority_IsClampedAndDrivesWorkerAssignment()
        {
            var simulation = LocalCitySimulation.FromJson(Fixture);
            var road = simulation.Submit(CityCommand.DrawRoad(new Vector3(-42, 0, 12), new Vector3(42, 0, 12)));
            simulation.Submit(CityCommand.ZoneResidential(road.createdId));

            Assert.IsTrue(simulation.Submit(CityCommand.SetPriority(2, 99)).accepted);
            Assert.IsTrue(simulation.Submit(CityCommand.SetPriority(1, -4)).accepted);
            simulation.Tick(0.1f);

            var snapshot = simulation.GetSnapshot(1001);
            Assert.AreEqual(3, snapshot.buildings.Find(item => item.id == 2).priority);
            Assert.AreEqual(0, snapshot.buildings.Find(item => item.id == 1).priority);
            Assert.AreEqual(2, snapshot.villagers.Find(item => item.id == 1).workplaceBuildingId);
            Assert.AreEqual("building-unknown", simulation.Submit(CityCommand.SetPriority(999, 1)).reason);
        }

        [Test]
        public void CompletePlayableLoop_HousesAHouseholdWithinTenSimulatedMinutes()
        {
            var simulation = LocalCitySimulation.FromJson(Fixture);
            var road = simulation.Submit(CityCommand.DrawRoad(new Vector3(-42, 0, 12), new Vector3(42, 0, 12)));
            Assert.IsTrue(road.accepted);
            Assert.IsTrue(simulation.Submit(CityCommand.ZoneResidential(road.createdId)).accepted);

            var elapsed = 0f;
            while (elapsed < 600f && simulation.GetSnapshot(1001).households.TrueForAll(item => item.homeBuildingId == 0))
            {
                simulation.Tick(0.1f);
                elapsed += 0.1f;
            }

            var snapshot = simulation.GetSnapshot(1001);
            Assert.That(snapshot.households.Exists(item => item.homeBuildingId != 0), Is.True);
            Assert.Less(elapsed, 600f);
            Assert.That(snapshot.buildings.Exists(item => item.phase == BuildingPhase.Complete), Is.True);
        }

        [Test]
        public void ZonedHouses_FaceTheirRoadFromBothSides()
        {
            var simulation = LocalCitySimulation.FromJson(Fixture);
            var roadResult = simulation.Submit(CityCommand.DrawRoad(new Vector3(-42, 0, 12), new Vector3(42, 0, 12)));
            simulation.Submit(CityCommand.ZoneResidential(roadResult.createdId));
            var snapshot = simulation.GetSnapshot(1001);
            var road = snapshot.roads.Find(item => item.id == roadResult.createdId);
            var start = road.start.ToVector3();
            var segment = road.end.ToVector3() - start;

            foreach (var building in snapshot.buildings)
            {
                var parcel = snapshot.parcels.Find(item => item.id == building.parcelId);
                var center = parcel.center.ToVector3();
                var t = Mathf.Clamp01(Vector3.Dot(center - start, segment) / segment.sqrMagnitude);
                var towardRoad = (start + segment * t - center).normalized;
                var facadeForward = Quaternion.Euler(0f, building.yaw, 0f) * Vector3.forward;
                Assert.Greater(Vector3.Dot(facadeForward, towardRoad), 0.999f,
                    $"La maison {building.id} doit regarder la route depuis sa parcelle.");
            }
        }

        [Test]
        public void PlaceLumberCamp_DeductsCostAndAssignsAvailableWorkers()
        {
            var simulation = LocalCitySimulation.FromJson(Fixture);
            var definition = simulation.Catalog.Get(BuildingArchetype.LumberCamp);
            var initialWood = simulation.GetSnapshot(1001).stockWood;

            var result = simulation.Submit(CityCommand.PlaceLumberCamp(new Vector3(70f, 9f, 0f)));

            Assert.IsTrue(result.accepted);
            Assert.AreEqual(1, result.createdId);
            var snapshot = simulation.GetSnapshot(1001);
            Assert.AreEqual(initialWood - definition.woodCost, snapshot.stockWood);
            Assert.AreEqual(1, snapshot.productionSites.Count);
            var camp = snapshot.productionSites[0];
            Assert.AreEqual(result.createdId, camp.id);
            Assert.AreEqual(ProductionSiteKind.LumberCamp, camp.kind);
            Assert.AreEqual(70f, camp.position.x);
            Assert.AreEqual(0f, camp.position.y);
            Assert.AreEqual(0f, camp.position.z);
            Assert.AreEqual(definition.maxWorkers, camp.assignedWorkers);
            Assert.AreEqual(definition.maxWorkers, camp.maxWorkers);
            Assert.AreEqual(BuildingPhase.Foundation, camp.constructionPhase);
            Assert.AreEqual(0f, camp.constructionProgress);
            Assert.AreEqual(0f, camp.productionProgress);
            Assert.AreEqual(definition.initialResource, camp.remainingTimber);
        }

        [Test]
        public void LumberCamp_ProducesWoodUntilLocalTimberIsExhausted()
        {
            var simulation = LocalCitySimulation.FromJson(Fixture);
            var definition = simulation.Catalog.Get(BuildingArchetype.LumberCamp);
            Assert.IsTrue(simulation.Submit(CityCommand.PlaceLumberCamp(new Vector3(70f, 0f, 0f))).accepted);
            var stockAfterPlacement = simulation.GetSnapshot(1001).stockWood;

            for (var i = 0; i < 1200 && simulation.GetSnapshot(1001).productionSites[0].constructionPhase != BuildingPhase.Complete; i++)
                simulation.Tick(0.1f);

            var constructed = simulation.GetSnapshot(1001);
            Assert.AreEqual(stockAfterPlacement, constructed.stockWood,
                "La scierie ne doit rien produire avant la fin de ses quatre phases.");

            for (var i = 0; i < 1200 && simulation.GetSnapshot(1001).stockWood == stockAfterPlacement; i++)
                simulation.Tick(0.1f);

            var producing = simulation.GetSnapshot(1001);
            Assert.AreEqual(stockAfterPlacement + 1, producing.stockWood);
            Assert.AreEqual(definition.initialResource - 1,
                producing.productionSites[0].remainingTimber);
            Assert.GreaterOrEqual(producing.productionSites[0].productionProgress, 0f);

            for (var i = 0; i < 5000; i++)
                simulation.Tick(0.1f);

            var exhausted = simulation.GetSnapshot(1001);
            Assert.AreEqual(stockAfterPlacement + definition.initialResource, exhausted.stockWood);
            Assert.AreEqual(0, exhausted.productionSites[0].remainingTimber);
            Assert.AreEqual(0, exhausted.productionSites[0].assignedWorkers);
            Assert.AreEqual(0f, exhausted.productionSites[0].productionProgress);

            for (var i = 0; i < 100; i++)
                simulation.Tick(0.1f);
            Assert.AreEqual(exhausted.stockWood, simulation.GetSnapshot(1001).stockWood);
        }

        [Test]
        public void LumberCamp_ConstructionAdvancesThroughFourDeterministicStages()
        {
            var simulation = LocalCitySimulation.FromJson(Fixture);
            Assert.IsTrue(simulation.Submit(CityCommand.PlaceLumberCamp(new Vector3(70f, 0f, 0f))).accepted);

            var observed = new System.Collections.Generic.List<BuildingPhase>();
            var last = BuildingPhase.Foundation;
            observed.Add(last);
            for (var i = 0; i < 1200 && last != BuildingPhase.Complete; i++)
            {
                simulation.Tick(0.1f);
                var current = simulation.GetSnapshot(1001).productionSites[0].constructionPhase;
                if (current != last)
                {
                    observed.Add(current);
                    last = current;
                }
            }
            CollectionAssert.AreEqual(new[]
            {
                BuildingPhase.Foundation, BuildingPhase.Framing, BuildingPhase.Roofing,
                BuildingPhase.Detailing, BuildingPhase.Complete
            }, observed);
            Assert.AreEqual(BuildingPhase.Complete,
                simulation.GetSnapshot(1001).productionSites[0].constructionPhase);
        }

        [Test]
        public void PlaceLumberCamp_RejectsInvalidPlacementAndInsufficientWoodWithStableReasons()
        {
            var outside = LocalCitySimulation.FromJson(Fixture);
            Assert.AreEqual("lumber-camp-outside-map",
                outside.Submit(CityCommand.PlaceLumberCamp(new Vector3(253f, 0f, 0f))).reason);

            var nearCentre = LocalCitySimulation.FromJson(Fixture);
            Assert.AreEqual("lumber-camp-too-close-to-centre",
                nearCentre.Submit(CityCommand.PlaceLumberCamp(new Vector3(34f, 0f, 0f))).reason);

            var farFromCentre = LocalCitySimulation.FromJson(Fixture);
            Assert.AreEqual("lumber-camp-too-far-from-centre",
                farFromCentre.Submit(CityCommand.PlaceLumberCamp(new Vector3(191f, 0f, 0f))).reason);

            var overlapping = LocalCitySimulation.FromJson(Fixture);
            Assert.IsTrue(overlapping.Submit(CityCommand.PlaceLumberCamp(new Vector3(70f, 0f, 0f))).accepted);
            Assert.AreEqual("lumber-camp-too-close-to-another-camp",
                overlapping.Submit(CityCommand.PlaceLumberCamp(new Vector3(95f, 0f, 0f))).reason);
            Assert.AreEqual(1, overlapping.GetSnapshot(1001).productionSites.Count);

            var lowWoodFixture = Fixture.Replace(@"""stockWood"":72", @"""stockWood"":7");
            var insufficient = LocalCitySimulation.FromJson(lowWoodFixture);
            Assert.AreEqual("lumber-camp-insufficient-wood",
                insufficient.Submit(CityCommand.PlaceLumberCamp(new Vector3(70f, 0f, 0f))).reason);
            var insufficientSnapshot = insufficient.GetSnapshot(1001);
            Assert.AreEqual(7, insufficientSnapshot.stockWood);
            Assert.AreEqual(0, insufficientSnapshot.productionSites.Count);

            var reservedWoodFixture = Fixture.Replace(@"""stockWood"":72",
                @"""stockWood"":8,""reservedWood"":1");
            var reservedWood = LocalCitySimulation.FromJson(reservedWoodFixture);
            Assert.AreEqual("lumber-camp-insufficient-wood",
                reservedWood.Submit(CityCommand.PlaceLumberCamp(new Vector3(70f, 0f, 0f))).reason);
            Assert.AreEqual(8, reservedWood.GetSnapshot(1001).stockWood,
                "Le cout du camp ne doit pas consommer du bois deja reserve a un chantier.");
        }

        [Test]
        public void LumberCamp_SameCommandsAndTicksProduceSameSnapshot()
        {
            var left = LocalCitySimulation.FromJson(Fixture);
            var right = LocalCitySimulation.FromJson(Fixture);
            var positions = new[] { new Vector3(70f, 0f, 0f), new Vector3(-70f, 0f, 0f) };
            foreach (var position in positions)
            {
                Assert.IsTrue(left.Submit(CityCommand.PlaceLumberCamp(position)).accepted);
                Assert.IsTrue(right.Submit(CityCommand.PlaceLumberCamp(position)).accepted);
            }

            for (var i = 0; i < 777; i++)
            {
                left.Tick(0.1f);
                right.Tick(0.1f);
            }

            Assert.AreEqual(JsonUtility.ToJson(left.GetSnapshot(1001)), JsonUtility.ToJson(right.GetSnapshot(1001)));
        }
    }
}
