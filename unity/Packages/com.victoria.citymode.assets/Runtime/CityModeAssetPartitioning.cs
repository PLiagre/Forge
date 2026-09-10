using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;

namespace Victoria.CityMode.Assets
{
    public enum CityModeAssetPartitionKind
    {
        Common = 0,
        Biome = 1,
        City = 2
    }

    [Serializable]
    public sealed class CityModeAssetCatalogEntry
    {
        [SerializeField] string id;
        [SerializeField] string guid;
        [SerializeField] string sha256;
        [SerializeField] string license;
        [SerializeField] UnityEngine.Object asset;

        public string Id => id;
        public string Guid => guid;
        public string Sha256 => sha256;
        public string License => license;
        public UnityEngine.Object Asset => asset;

        public CityModeAssetCatalogEntry()
        {
        }

        public CityModeAssetCatalogEntry(
            string id,
            string guid,
            string sha256,
            string license,
            UnityEngine.Object asset)
        {
            this.id = id;
            this.guid = guid;
            this.sha256 = sha256;
            this.license = license;
            this.asset = asset;
        }

        internal void Validate()
        {
            if (string.IsNullOrWhiteSpace(id))
                throw new InvalidOperationException("Asset catalog entry id is required.");
            if (string.IsNullOrWhiteSpace(guid) || guid.Length != 32)
                throw new InvalidOperationException("Asset catalog GUID must contain 32 characters: " + id);
            if (string.IsNullOrWhiteSpace(sha256) || sha256.Length != 64)
                throw new InvalidOperationException("Asset catalog SHA-256 must contain 64 characters: " + id);
            if (string.IsNullOrWhiteSpace(license))
                throw new InvalidOperationException("Asset catalog licence is required: " + id);
            if (asset == null)
                throw new InvalidOperationException("Asset catalog reference is missing: " + id);
        }
    }

    public readonly struct CityModeAssetPartitionLoad
    {
        public CityModeAssetPartitionLoad(
            CityModeAssetPartitionKind partition,
            int assetCount,
            long residentBytes,
            long budgetBytes)
        {
            Partition = partition;
            AssetCount = assetCount;
            ResidentBytes = residentBytes;
            BudgetBytes = budgetBytes;
        }

        public CityModeAssetPartitionKind Partition { get; }
        public int AssetCount { get; }
        public long ResidentBytes { get; }
        public long BudgetBytes { get; }
    }

    public interface ICityModeAssetPartitionHost
    {
        Task<CityModeAssetPartitionLoad> LoadAsync(
            CityModeAssetPartitionKind partition,
            CancellationToken cancellationToken);

        Task UnloadAsync(
            CityModeAssetPartitionKind partition,
            CancellationToken cancellationToken);
    }

    public sealed class CityModeAssetPartitionMetrics
    {
        readonly Dictionary<CityModeAssetPartitionKind, long> residentBytes =
            new Dictionary<CityModeAssetPartitionKind, long>();

        public int CompletedLoads { get; internal set; }
        public int CompletedUnloads { get; internal set; }
        public double MaximumLoadMilliseconds { get; internal set; }
        public double MaximumUnloadMilliseconds { get; internal set; }
        public long PeakPartitionResidentBytes { get; internal set; }
        public IReadOnlyDictionary<CityModeAssetPartitionKind, long> ResidentBytes => residentBytes;

        internal void RecordLoad(CityModeAssetPartitionLoad load, double milliseconds)
        {
            CompletedLoads++;
            MaximumLoadMilliseconds = Math.Max(MaximumLoadMilliseconds, milliseconds);
            PeakPartitionResidentBytes = Math.Max(PeakPartitionResidentBytes, load.ResidentBytes);
            residentBytes[load.Partition] = load.ResidentBytes;
        }

        internal void RecordUnload(double milliseconds)
        {
            CompletedUnloads++;
            MaximumUnloadMilliseconds = Math.Max(MaximumUnloadMilliseconds, milliseconds);
        }
    }

    public sealed class CityModeAssetPartitionResult
    {
        CityModeAssetPartitionResult(bool succeeded, string message)
        {
            Succeeded = succeeded;
            Message = message ?? string.Empty;
        }

        public bool Succeeded { get; }
        public string Message { get; }

        public static CityModeAssetPartitionResult Success() =>
            new CityModeAssetPartitionResult(true, string.Empty);

        public static CityModeAssetPartitionResult Failure(string message) =>
            new CityModeAssetPartitionResult(false, message);
    }

    /// <summary>
    /// Loads the immutable partition order common -> biome -> city and always
    /// releases it in reverse. The host owns addresses and Unity scene APIs.
    /// </summary>
    public sealed class CityModeAssetPartitionLoader : IDisposable
    {
        static readonly CityModeAssetPartitionKind[] LoadOrder =
        {
            CityModeAssetPartitionKind.Common,
            CityModeAssetPartitionKind.Biome,
            CityModeAssetPartitionKind.City
        };

        readonly ICityModeAssetPartitionHost host;
        readonly List<CityModeAssetPartitionKind> loaded =
            new List<CityModeAssetPartitionKind>();
        int operationActive;
        bool disposed;

        public CityModeAssetPartitionLoader(ICityModeAssetPartitionHost host)
        {
            this.host = host ?? throw new ArgumentNullException(nameof(host));
            Metrics = new CityModeAssetPartitionMetrics();
        }

        public CityModeAssetPartitionMetrics Metrics { get; }
        public bool IsLoaded => loaded.Count == LoadOrder.Length;

        public async Task<CityModeAssetPartitionResult> LoadCityAsync(
            CancellationToken cancellationToken = default)
        {
            ThrowIfDisposed();
            if (Interlocked.CompareExchange(ref operationActive, 1, 0) != 0)
                return CityModeAssetPartitionResult.Failure("Asset partition operation already in progress.");
            try
            {
                if (loaded.Count != 0)
                    return CityModeAssetPartitionResult.Failure("Asset partitions are already loaded.");

                foreach (var partition in LoadOrder)
                {
                    cancellationToken.ThrowIfCancellationRequested();
                    var watch = Stopwatch.StartNew();
                    var result = await host.LoadAsync(partition, cancellationToken);
                    watch.Stop();
                    // A successful host call means the requested partition now
                    // exists and must participate in rollback even if its
                    // returned catalogue or measurements are invalid.
                    loaded.Add(partition);
                    if (result.Partition != partition)
                        throw new InvalidOperationException("Host returned the wrong asset partition.");
                    if (result.AssetCount <= 0 || result.ResidentBytes < 0 || result.BudgetBytes <= 0)
                        throw new InvalidOperationException("Host returned invalid partition metrics: " + partition);
                    if (result.ResidentBytes > result.BudgetBytes)
                        throw new InvalidOperationException(
                            partition + " exceeds resident budget: " +
                            result.ResidentBytes + " > " + result.BudgetBytes);
                    Metrics.RecordLoad(result, watch.Elapsed.TotalMilliseconds);
                }
                return CityModeAssetPartitionResult.Success();
            }
            catch (Exception exception)
            {
                await RollbackAsync();
                return CityModeAssetPartitionResult.Failure(exception.Message);
            }
            finally
            {
                Volatile.Write(ref operationActive, 0);
            }
        }

        public async Task<CityModeAssetPartitionResult> UnloadCityAsync(
            CancellationToken cancellationToken = default)
        {
            ThrowIfDisposed();
            if (Interlocked.CompareExchange(ref operationActive, 1, 0) != 0)
                return CityModeAssetPartitionResult.Failure("Asset partition operation already in progress.");
            try
            {
                for (var index = loaded.Count - 1; index >= 0; index--)
                {
                    cancellationToken.ThrowIfCancellationRequested();
                    var watch = Stopwatch.StartNew();
                    await host.UnloadAsync(loaded[index], cancellationToken);
                    watch.Stop();
                    loaded.RemoveAt(index);
                    Metrics.RecordUnload(watch.Elapsed.TotalMilliseconds);
                }
                return CityModeAssetPartitionResult.Success();
            }
            catch (Exception exception)
            {
                return CityModeAssetPartitionResult.Failure(exception.Message);
            }
            finally
            {
                Volatile.Write(ref operationActive, 0);
            }
        }

        async Task RollbackAsync()
        {
            for (var index = loaded.Count - 1; index >= 0; index--)
            {
                try
                {
                    var watch = Stopwatch.StartNew();
                    await host.UnloadAsync(loaded[index], CancellationToken.None);
                    watch.Stop();
                    Metrics.RecordUnload(watch.Elapsed.TotalMilliseconds);
                }
                catch
                {
                    // Preserve the original load failure. Host unload is required
                    // to be idempotent and a later explicit unload may retry.
                }
                loaded.RemoveAt(index);
            }
        }

        void ThrowIfDisposed()
        {
            if (disposed)
                throw new ObjectDisposedException(nameof(CityModeAssetPartitionLoader));
        }

        public void Dispose()
        {
            disposed = true;
        }
    }
}
