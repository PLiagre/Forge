using System;
using System.IO;
using NUnit.Framework;
using UnityEngine;

namespace Victoria.CityMode.Tests
{
    public sealed class CitySaveServiceTests
    {
        const string Fixture = @"{
          ""schemaVersion"":1,""cityId"":1001,""seed"":140001,""stockWood"":72,
          ""households"":[{""id"":1,""memberCount"":3}],
          ""roads"":[],""parcels"":[],""buildings"":[],
          ""villagers"":[{""id"":1,""householdId"":1,""position"":{""x"":-5,""z"":-5}}],
          ""productionSites"":[] }";

        [Test]
        public void RoundTrip_PreservesCompleteSimulationSnapshot()
        {
            var simulation = LocalCitySimulation.FromJson(Fixture);
            var road = simulation.Submit(CityCommand.DrawRoad(
                new Vector3(-42, 0, 12), new Vector3(42, 0, 12)));
            Assert.IsTrue(road.accepted);
            simulation.Submit(CityCommand.ZoneResidential(road.createdId));
            simulation.Submit(CityCommand.PlaceLumberCamp(new Vector3(70, 0, 0)));
            for (var i = 0; i < 80; i++)
                simulation.Tick(0.1f);

            var before = simulation.GetSnapshot(1001);
            var document = CitySaveService.Serialize(before);
            Assert.IsTrue(CitySaveService.TryDeserialize(document, out var after, out var reason), reason);
            Assert.AreEqual(JsonUtility.ToJson(before), JsonUtility.ToJson(after));
        }

        [Test]
        public void ManualAndAutosave_ReplaceAtomicallyWithoutTemporaryResidue()
        {
            var directory = Path.Combine(Path.GetTempPath(), "citylab-save-tests", Guid.NewGuid().ToString("N"));
            try
            {
                var snapshot = LocalCitySimulation.FromJson(Fixture).GetSnapshot(1001);
                var manual = CitySaveService.SaveManual(directory, snapshot);
                snapshot.stockWood = 41;
                CitySaveService.SaveManual(directory, snapshot);
                var autosave = CitySaveService.SaveAutosave(directory, snapshot);

                Assert.IsTrue(File.Exists(manual));
                Assert.IsTrue(File.Exists(autosave));
                Assert.IsFalse(File.Exists(manual + ".tmp"));
                Assert.IsTrue(CitySaveService.TryLoad(manual, out var loaded, out var reason), reason);
                Assert.AreEqual(41, loaded.stockWood);
            }
            finally
            {
                if (Directory.Exists(directory))
                    Directory.Delete(directory, true);
            }
        }

        [Test]
        public void CorruptedChecksum_IsRefusedCleanly()
        {
            var snapshot = LocalCitySimulation.FromJson(Fixture).GetSnapshot(1001);
            var document = CitySaveService.Serialize(snapshot)
                .Replace("\"payloadSha256\": \"", "\"payloadSha256\": \"x");

            Assert.IsFalse(CitySaveService.TryDeserialize(document, out var loaded, out var reason));
            Assert.IsNull(loaded);
            Assert.AreEqual("checksum-invalid", reason);
        }

        [Test]
        public void VersionZeroFixture_MigratesToCurrentSchema()
        {
            var path = Path.Combine(Directory.GetCurrentDirectory(),
                "Packages/com.victoria.citymode/Tests/Fixtures/city_save_v0.json");
            var document = File.ReadAllText(path);

            Assert.IsTrue(CitySaveService.TryDeserialize(document, out var snapshot, out var reason), reason);
            Assert.AreEqual(CitySaveService.CurrentSnapshotSchemaVersion, snapshot.schemaVersion);
            Assert.AreEqual(1001, snapshot.cityId);
            Assert.AreEqual(12.5f, snapshot.elapsedSeconds);
            Assert.AreEqual(1, snapshot.households.Count);
            Assert.AreEqual(1, snapshot.roads.Count);
        }
    }
}
