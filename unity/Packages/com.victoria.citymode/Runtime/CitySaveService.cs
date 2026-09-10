using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using UnityEngine;

namespace Victoria.CityMode
{
    /// <summary>Versioned, checksummed and atomic persistence for simulation snapshots.</summary>
    public static class CitySaveService
    {
        public const int CurrentFormatVersion = 1;
        public const int CurrentSnapshotSchemaVersion = 1;
        const string FormatId = "victoria-citylab-save";

        [Serializable]
        sealed class CitySaveEnvelope
        {
            public string format;
            public int formatVersion;
            public int snapshotSchemaVersion;
            public string payloadSha256;
            public string payload;
        }

        public static string ManualFileName(int cityId) => $"city_{cityId}.save.json";
        public static string AutosaveFileName(int cityId) => $"city_{cityId}.autosave.json";

        public static string SaveManual(string directory, CitySnapshot snapshot) =>
            SaveAtomic(Path.Combine(directory, ManualFileName(RequireCity(snapshot))), snapshot);

        public static string SaveAutosave(string directory, CitySnapshot snapshot) =>
            SaveAtomic(Path.Combine(directory, AutosaveFileName(RequireCity(snapshot))), snapshot);

        public static string SaveAtomic(string path, CitySnapshot snapshot)
        {
            if (string.IsNullOrWhiteSpace(path))
                throw new ArgumentException("Chemin de sauvegarde vide.", nameof(path));
            var document = Serialize(snapshot);
            var fullPath = Path.GetFullPath(path);
            var directory = Path.GetDirectoryName(fullPath);
            if (string.IsNullOrEmpty(directory))
                throw new ArgumentException("Dossier de sauvegarde invalide.", nameof(path));
            Directory.CreateDirectory(directory);
            var temporaryPath = fullPath + ".tmp";
            try
            {
                using (var stream = new FileStream(temporaryPath, FileMode.Create, FileAccess.Write,
                           FileShare.None, 4096, FileOptions.WriteThrough))
                using (var writer = new StreamWriter(stream, new UTF8Encoding(false)))
                {
                    writer.Write(document);
                    writer.Flush();
                    stream.Flush(true);
                }

                if (File.Exists(fullPath))
                    File.Replace(temporaryPath, fullPath, null);
                else
                    File.Move(temporaryPath, fullPath);
                return fullPath;
            }
            finally
            {
                if (File.Exists(temporaryPath))
                    File.Delete(temporaryPath);
            }
        }

        public static bool TryLoad(string path, out CitySnapshot snapshot, out string reason)
        {
            snapshot = null;
            reason = "file-missing";
            if (string.IsNullOrWhiteSpace(path) || !File.Exists(path))
                return false;
            try
            {
                return TryDeserialize(File.ReadAllText(path, Encoding.UTF8), out snapshot, out reason);
            }
            catch (Exception exception) when (exception is IOException || exception is UnauthorizedAccessException)
            {
                reason = "file-read-failed";
                return false;
            }
        }

        public static string Serialize(CitySnapshot snapshot)
        {
            RequireValidSnapshot(snapshot, allowLegacy: true);
            var payload = JsonUtility.ToJson(snapshot);
            var envelope = new CitySaveEnvelope
            {
                format = FormatId,
                formatVersion = CurrentFormatVersion,
                snapshotSchemaVersion = snapshot.schemaVersion,
                payloadSha256 = ComputePayloadSha256(payload),
                payload = payload
            };
            return JsonUtility.ToJson(envelope, true);
        }

        public static bool TryDeserialize(string document, out CitySnapshot snapshot, out string reason)
        {
            snapshot = null;
            reason = "document-empty";
            if (string.IsNullOrWhiteSpace(document))
                return false;
            CitySaveEnvelope envelope;
            try
            {
                envelope = JsonUtility.FromJson<CitySaveEnvelope>(document);
            }
            catch (ArgumentException)
            {
                reason = "envelope-invalid";
                return false;
            }
            if (envelope == null || envelope.format != FormatId)
            {
                reason = "format-invalid";
                return false;
            }
            if (envelope.formatVersion != CurrentFormatVersion)
            {
                reason = "format-version-unsupported";
                return false;
            }
            if (envelope.snapshotSchemaVersion < 0 ||
                envelope.snapshotSchemaVersion > CurrentSnapshotSchemaVersion)
            {
                reason = "snapshot-version-unsupported";
                return false;
            }
            if (string.IsNullOrEmpty(envelope.payload) || string.IsNullOrEmpty(envelope.payloadSha256))
            {
                reason = "payload-missing";
                return false;
            }
            if (!string.Equals(ComputePayloadSha256(envelope.payload), envelope.payloadSha256,
                    StringComparison.OrdinalIgnoreCase))
            {
                reason = "checksum-invalid";
                return false;
            }
            try
            {
                snapshot = JsonUtility.FromJson<CitySnapshot>(envelope.payload);
            }
            catch (ArgumentException)
            {
                reason = "payload-invalid";
                return false;
            }
            if (snapshot == null || snapshot.schemaVersion != envelope.snapshotSchemaVersion)
            {
                snapshot = null;
                reason = "snapshot-schema-mismatch";
                return false;
            }
            try
            {
                Migrate(snapshot);
                RequireValidSnapshot(snapshot, allowLegacy: false);
            }
            catch (ArgumentException)
            {
                snapshot = null;
                reason = "snapshot-invalid";
                return false;
            }
            reason = "accepted";
            return true;
        }

        public static string ComputePayloadSha256(string payload)
        {
            using (var sha = SHA256.Create())
            {
                var bytes = sha.ComputeHash(Encoding.UTF8.GetBytes(payload ?? string.Empty));
                var builder = new StringBuilder(bytes.Length * 2);
                for (var i = 0; i < bytes.Length; i++)
                    builder.Append(bytes[i].ToString("x2"));
                return builder.ToString();
            }
        }

        static int RequireCity(CitySnapshot snapshot)
        {
            RequireValidSnapshot(snapshot, allowLegacy: true);
            return snapshot.cityId;
        }

        static void Migrate(CitySnapshot snapshot)
        {
            if (snapshot.schemaVersion == 0)
            {
                snapshot.households ??= new List<HouseholdState>();
                snapshot.roads ??= new List<RoadState>();
                snapshot.parcels ??= new List<ParcelState>();
                snapshot.buildings ??= new List<BuildingState>();
                snapshot.villagers ??= new List<VillagerState>();
                snapshot.productionSites ??= new List<ProductionSiteState>();
                snapshot.schemaVersion = 1;
            }
            snapshot.logisticsTasks ??= new List<LogisticsTaskState>();
            snapshot.scheduledEvents ??= new List<ScheduledCityEventState>();
            snapshot.calendar ??= new CityCalendarState();
            snapshot.resources ??= new List<ResourceStockState>();
            snapshot.foodSources ??= new List<FoodSourceState>();
            snapshot.fields ??= new List<AgriculturalFieldState>();
            snapshot.tradeOrders ??= new List<TradeOrderState>();
        }

        static void RequireValidSnapshot(CitySnapshot snapshot, bool allowLegacy)
        {
            if (snapshot == null || snapshot.cityId <= 0)
                throw new ArgumentException("Snapshot absent ou ville invalide.", nameof(snapshot));
            var minimumVersion = allowLegacy ? 0 : CurrentSnapshotSchemaVersion;
            if (snapshot.schemaVersion < minimumVersion || snapshot.schemaVersion > CurrentSnapshotSchemaVersion)
                throw new ArgumentException("Version de snapshot non prise en charge.", nameof(snapshot));
            if (!IsFinite(snapshot.elapsedSeconds) || snapshot.elapsedSeconds < 0f)
                throw new ArgumentException("Horloge invalide.", nameof(snapshot));
            if (snapshot.clockStateInitialized &&
                (!IsFinite(snapshot.simulationSpeed) || snapshot.simulationSpeed < 0f ||
                 !IsFinite(snapshot.lastRunningSpeed) || snapshot.lastRunningSpeed <= 0f))
                throw new ArgumentException("Vitesse de simulation invalide.", nameof(snapshot));
            if (snapshot.households == null || snapshot.roads == null || snapshot.parcels == null ||
                snapshot.buildings == null || snapshot.villagers == null || snapshot.productionSites == null ||
                snapshot.logisticsTasks == null || snapshot.scheduledEvents == null || snapshot.calendar == null ||
                snapshot.resources == null || snapshot.foodSources == null || snapshot.fields == null)
                throw new ArgumentException("Collections de snapshot incomplètes.", nameof(snapshot));
            if (snapshot.tradeOrders == null)
                throw new ArgumentException("Collections de snapshot incomplètes.", nameof(snapshot));
            if (snapshot.treasuryCoins < 0 || snapshot.reservedTradeCoins < 0 ||
                snapshot.reservedTradeCoins > snapshot.treasuryCoins)
                throw new ArgumentException("Trésor commercial invalide.", nameof(snapshot));
            foreach (var resource in snapshot.resources)
                if (resource == null || resource.kind == 0 || resource.quantity < 0 ||
                    resource.reserved < 0 || resource.reserved > resource.quantity ||
                    resource.capacity < resource.quantity || resource.lossRemainderPermille < 0 ||
                    resource.lossRemainderPermille >= 1000 || resource.totalLost < 0)
                    throw new ArgumentException("Stock de ressource invalide.", nameof(snapshot));
            foreach (var site in snapshot.productionSites)
                if (site == null || site.remainingTimber < 0 || site.storedWood < 0 ||
                    site.reservedWood < 0 || site.reservedWood > site.storedWood ||
                    site.inputAStored < 0 || site.inputBStored < 0 || site.outputStored < 0 ||
                    site.outputReserved < 0 || site.outputReserved > site.outputStored ||
                    site.rawRemaining < 0 || site.totalBatches < 0)
                    throw new ArgumentException("Site de production invalide.", nameof(snapshot));
            foreach (var parcel in snapshot.parcels)
                if (parcel == null || parcel.id <= 0 || parcel.roadId < 0 ||
                    !IsFinite(parcel.center.x) || !IsFinite(parcel.center.y) || !IsFinite(parcel.center.z) ||
                    !IsFinite(parcel.width) || parcel.width <= 0f ||
                    !IsFinite(parcel.depth) || parcel.depth <= 0f ||
                    !IsFinite(parcel.yaw) || !IsFinite(parcel.gardenDepth) || parcel.gardenDepth < 0f ||
                    parcel.gardenDepth > parcel.depth || parcel.terrainSlopePermille < 0 ||
                    parcel.terrainSlopePermille > 180 || parcel.extensionCapacity < 0 ||
                    parcel.extensionCapacity > 2 || parcel.extensionLevel < 0 ||
                    parcel.extensionLevel > parcel.extensionCapacity)
                    throw new ArgumentException("Parcelle organique invalide.", nameof(snapshot));
            foreach (var building in snapshot.buildings)
            {
                building.localStocks ??= new List<StoredResourceState>();
                building.constructionMaterials ??= new List<ConstructionMaterialState>();
                if (building.marketCoveredHouseholds < 0 || building.marketScarcityPermille < 0 ||
                    building.marketScarcityPermille > 1000 || building.marketPricePermille < 0 ||
                    building.marketPricePermille > 2000 || building.marketShortageDays < 0 ||
                    !IsFinite(building.terrainWorkRemaining) || building.terrainWorkRemaining < 0f ||
                    building.terrainCutFillMillimeters < 0)
                    throw new ArgumentException("État de marché invalide.", nameof(snapshot));
                foreach (var material in building.constructionMaterials)
                    if (material == null || material.resource == 0 ||
                        !Enum.IsDefined(typeof(CityResourceKind), material.resource) ||
                        !Enum.IsDefined(typeof(BuildingPhase), material.phase) ||
                        material.phase == BuildingPhase.Complete || material.required <= 0 ||
                        material.delivered < 0 || material.delivered > material.required)
                        throw new ArgumentException("Matériau de chantier invalide.", nameof(snapshot));
                foreach (var local in building.localStocks)
                    if (local == null || local.kind == 0 || local.quantity < 0 ||
                        local.reserved < 0 || local.reserved > local.quantity ||
                        local.capacity < local.quantity)
                        throw new ArgumentException("Stock local invalide.", nameof(snapshot));
            }
            foreach (var scheduled in snapshot.scheduledEvents)
                if (scheduled == null || !IsFinite(scheduled.triggerAtElapsedSeconds) ||
                    scheduled.triggerAtElapsedSeconds < 0f ||
                    !IsFinite(scheduled.triggeredAtElapsedSeconds))
                    throw new ArgumentException("Événement planifié invalide.", nameof(snapshot));
            foreach (var household in snapshot.households)
                if (household == null || household.foodShortageDays < 0 ||
                    household.fuelShortageDays < 0 || household.clothingShortageDays < 0 ||
                    household.toolShortageDays < 0 || household.satisfactionPermille < 0 ||
                    household.satisfactionPermille > 1000)
                    throw new ArgumentException("Besoins de foyer invalides.", nameof(snapshot));
            foreach (var order in snapshot.tradeOrders)
                if (order == null || order.id <= 0 || order.direction == 0 || order.resource == 0 ||
                    order.requestedQuantity <= 0 || order.requestedQuantity > 40 ||
                    order.deliveredQuantity < 0 || order.deliveredQuantity > order.requestedQuantity ||
                    order.unitPrice <= 0 || order.feeCoins < 0 || order.deliveryDay < order.createdDay ||
                    !IsFinite(order.travelProgress) || order.travelProgress < 0f ||
                    order.travelProgress > 1f || order.status == 0)
                    throw new ArgumentException("Ordre commercial invalide.", nameof(snapshot));
        }

        static bool IsFinite(float value) => !float.IsNaN(value) && !float.IsInfinity(value);
    }
}
