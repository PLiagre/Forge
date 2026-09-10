using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Profiling;

namespace Victoria.CityMode.Assets
{
    /// <summary>
    /// Scene-owned catalogue. A partition scene holds the only strong references
    /// to its imported content, so unloading that scene makes the partition
    /// eligible for release. No asset lookup service or Resources path is used.
    /// </summary>
    public sealed class CityModeAssetPartitionCatalog : MonoBehaviour
    {
        [SerializeField] string revision = "city-mode-assets-v1";
        [SerializeField] CityModeAssetPartitionKind partition;
        [SerializeField] long maxResidentBytes;
        [SerializeField] CityModeAssetCatalogEntry[] entries = Array.Empty<CityModeAssetCatalogEntry>();

        public string Revision => revision;
        public CityModeAssetPartitionKind Partition => partition;
        public long MaxResidentBytes => maxResidentBytes;
        public IReadOnlyList<CityModeAssetCatalogEntry> Entries => entries;

        public void Configure(
            string catalogRevision,
            CityModeAssetPartitionKind kind,
            long residentBudgetBytes,
            CityModeAssetCatalogEntry[] catalogEntries)
        {
            revision = catalogRevision;
            partition = kind;
            maxResidentBytes = residentBudgetBytes;
            entries = catalogEntries ?? Array.Empty<CityModeAssetCatalogEntry>();
            Validate();
        }

        public void Validate()
        {
            if (string.IsNullOrWhiteSpace(revision))
                throw new InvalidOperationException("Asset catalog revision is required.");
            if (maxResidentBytes <= 0)
                throw new InvalidOperationException("Asset partition budget must be positive: " + partition);
            if (entries == null || entries.Length == 0)
                throw new InvalidOperationException("Asset partition must contain entries: " + partition);

            var ids = new HashSet<string>(StringComparer.Ordinal);
            var guids = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var entry in entries)
            {
                if (entry == null)
                    throw new InvalidOperationException("Asset catalog entry cannot be null: " + partition);
                entry.Validate();
                if (!ids.Add(entry.Id))
                    throw new InvalidOperationException("Duplicate asset id: " + entry.Id);
                if (!guids.Add(entry.Guid))
                    throw new InvalidOperationException("Duplicate asset GUID: " + entry.Guid);
            }
        }

        public long MeasureDirectResidentBytes()
        {
            Validate();
            long total = 0;
            var instances = new HashSet<int>();
            foreach (var entry in entries)
            {
                if (entry.Asset == null || !instances.Add(entry.Asset.GetInstanceID()))
                    continue;
                total += Math.Max(0L, Profiler.GetRuntimeMemorySizeLong(entry.Asset));
            }
            return total;
        }
    }
}
