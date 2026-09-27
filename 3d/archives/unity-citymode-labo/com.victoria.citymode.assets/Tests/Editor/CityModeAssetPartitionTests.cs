using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using NUnit.Framework;
using UnityEngine;

namespace Victoria.CityMode.Assets.Tests
{
    public sealed class CityModeAssetPartitionTests
    {
        [Test]
        public void CatalogRequiresRevisionBudgetHashesLicencesAndReferences()
        {
            var root = new GameObject("catalog");
            var texture = new Texture2D(2, 2);
            try
            {
                var catalog = root.AddComponent<CityModeAssetPartitionCatalog>();
                catalog.Configure(
                    "asset-port-v1",
                    CityModeAssetPartitionKind.Common,
                    1024,
                    new[]
                    {
                        new CityModeAssetCatalogEntry(
                            "trim.base",
                            new string('a', 32),
                            new string('b', 64),
                            "LicenseRef-Victoria-Original",
                            texture)
                    });
                Assert.DoesNotThrow(catalog.Validate);
                Assert.Greater(catalog.MeasureDirectResidentBytes(), 0L);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(texture);
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        [Test]
        public async Task LoaderUsesFixedOrderAndReverseUnload()
        {
            var host = new FakeHost();
            using (var loader = new CityModeAssetPartitionLoader(host))
            {
                var loaded = await loader.LoadCityAsync();
                Assert.IsTrue(loaded.Succeeded, loaded.Message);
                Assert.IsTrue(loader.IsLoaded);
                CollectionAssert.AreEqual(
                    new[] { "load:Common", "load:Biome", "load:City" },
                    host.calls);

                var unloaded = await loader.UnloadCityAsync();
                Assert.IsTrue(unloaded.Succeeded, unloaded.Message);
                CollectionAssert.AreEqual(
                    new[]
                    {
                        "load:Common", "load:Biome", "load:City",
                        "unload:City", "unload:Biome", "unload:Common"
                    },
                    host.calls);
                Assert.AreEqual(3, loader.Metrics.CompletedLoads);
                Assert.AreEqual(3, loader.Metrics.CompletedUnloads);
            }
        }

        [Test]
        public async Task BudgetFailureRollsBackPreviouslyLoadedPartitions()
        {
            var host = new FakeHost { overBudget = CityModeAssetPartitionKind.Biome };
            using (var loader = new CityModeAssetPartitionLoader(host))
            {
                var result = await loader.LoadCityAsync();
                Assert.IsFalse(result.Succeeded);
                StringAssert.Contains("exceeds resident budget", result.Message);
                CollectionAssert.AreEqual(
                    new[] { "load:Common", "load:Biome", "unload:Biome", "unload:Common" },
                    host.calls);
                Assert.IsFalse(loader.IsLoaded);
            }
        }

        [Test]
        public async Task HostFailureRollsBackAndAllowsRetry()
        {
            var host = new FakeHost { fail = CityModeAssetPartitionKind.City };
            using (var loader = new CityModeAssetPartitionLoader(host))
            {
                var first = await loader.LoadCityAsync();
                Assert.IsFalse(first.Succeeded);
                CollectionAssert.AreEqual(
                    new[]
                    {
                        "load:Common", "load:Biome", "load:City",
                        "unload:Biome", "unload:Common"
                    },
                    host.calls);

                host.fail = null;
                host.calls.Clear();
                var retry = await loader.LoadCityAsync();
                Assert.IsTrue(retry.Succeeded, retry.Message);
            }
        }

        sealed class FakeHost : ICityModeAssetPartitionHost
        {
            public readonly List<string> calls = new List<string>();
            public CityModeAssetPartitionKind? fail;
            public CityModeAssetPartitionKind? overBudget;

            public Task<CityModeAssetPartitionLoad> LoadAsync(
                CityModeAssetPartitionKind partition,
                CancellationToken cancellationToken)
            {
                calls.Add("load:" + partition);
                if (fail == partition)
                    throw new InvalidOperationException("synthetic load failure");
                var resident = overBudget == partition ? 2048 : 512;
                return Task.FromResult(new CityModeAssetPartitionLoad(
                    partition, 1, resident, 1024));
            }

            public Task UnloadAsync(
                CityModeAssetPartitionKind partition,
                CancellationToken cancellationToken)
            {
                calls.Add("unload:" + partition);
                return Task.CompletedTask;
            }
        }
    }
}
