using System;
using System.Collections.Generic;
using UnityEngine;

namespace Victoria.CityMode
{
    [Serializable]
    public struct CityPoint : IEquatable<CityPoint>
    {
        public float x;
        public float y;
        public float z;

        public CityPoint(float x, float y, float z)
        {
            this.x = x;
            this.y = y;
            this.z = z;
        }

        public Vector3 ToVector3() => new Vector3(x, y, z);
        public static CityPoint From(Vector3 value) => new CityPoint(value.x, value.y, value.z);
        public bool Equals(CityPoint other) => x.Equals(other.x) && y.Equals(other.y) && z.Equals(other.z);
    }

    public enum CityCommandKind : byte
    {
        DrawRoad = 1,
        ZoneResidential = 2,
        SetConstructionPriority = 3,
        PlaceLumberCamp = 4,
        PlaceBuilding = 5
    }

    [Serializable]
    public sealed class CityCommand
    {
        public CityCommandKind kind;
        public int targetId;
        public int priority;
        public CityPoint start;
        public CityPoint end;
        public CityPoint position;
        public BuildingArchetype archetype;

        public static CityCommand DrawRoad(Vector3 start, Vector3 end) => new CityCommand
        {
            kind = CityCommandKind.DrawRoad,
            start = CityPoint.From(start),
            end = CityPoint.From(end)
        };

        public static CityCommand ZoneResidential(int roadId) => new CityCommand
        {
            kind = CityCommandKind.ZoneResidential,
            targetId = roadId
        };

        public static CityCommand SetPriority(int buildingId, int priority) => new CityCommand
        {
            kind = CityCommandKind.SetConstructionPriority,
            targetId = buildingId,
            priority = priority
        };

        public static CityCommand PlaceLumberCamp(Vector3 position) => new CityCommand
        {
            kind = CityCommandKind.PlaceLumberCamp,
            position = CityPoint.From(position)
        };

        public static CityCommand PlaceBuilding(BuildingArchetype archetype, Vector3 position) => new CityCommand
        {
            kind = CityCommandKind.PlaceBuilding,
            archetype = archetype,
            position = CityPoint.From(position)
        };
    }

    [Serializable]
    public sealed class CityCommandResult
    {
        public bool accepted;
        public string reason;
        public int createdId;

        public static CityCommandResult Accept(int createdId = 0) => new CityCommandResult
        {
            accepted = true,
            reason = "accepted",
            createdId = createdId
        };

        public static CityCommandResult Reject(string reason) => new CityCommandResult
        {
            accepted = false,
            reason = reason,
            createdId = 0
        };
    }

    public interface ICityStateSource
    {
        CitySnapshot GetSnapshot(int cityId);
    }

    public interface ICityCommandSink
    {
        CityCommandResult Submit(CityCommand command);
    }

    /// <summary>
    /// Fournit à la simulation une hauteur de terrain sans lui donner accès à un
    /// GameObject. Les mesures retenues sont persistées dans les parcelles.
    /// </summary>
    public interface IParcelTerrainSampler
    {
        float SampleHeight(Vector3 worldPosition);
    }

    [Serializable]
    public sealed class CitySnapshot
    {
        public int schemaVersion = 1;
        public int cityId;
        public int seed;
        public float elapsedSeconds;
        public bool clockStateInitialized;
        public float simulationSpeed = 1f;
        public float lastRunningSpeed = 1f;
        public CityCalendarState calendar = new CityCalendarState();
        public int stockWood;
        public int reservedWood;
        public int foodStorageCapacity;
        public int goodsStorageCapacity;
        public int marketServiceCapacity;
        public int toolProductionCapacity;
        public int livestockCapacity;
        public int faithServiceCapacity;
        public int navigationReplans;
        public int navigationFailures;
        public int employmentRevision;
        public int jobAbsences;
        public int jobReplacements;
        public int employmentDay = -1;
        public int logisticsRevision;
        public int resourceLossDay = -1;
        public List<HouseholdState> households = new List<HouseholdState>();
        public List<RoadState> roads = new List<RoadState>();
        public List<ParcelState> parcels = new List<ParcelState>();
        public List<BuildingState> buildings = new List<BuildingState>();
        public List<VillagerState> villagers = new List<VillagerState>();
        public List<ProductionSiteState> productionSites = new List<ProductionSiteState>();
        public List<LogisticsTaskState> logisticsTasks = new List<LogisticsTaskState>();
        public List<ScheduledCityEventState> scheduledEvents = new List<ScheduledCityEventState>();
        public List<ResourceStockState> resources = new List<ResourceStockState>();
        public List<FoodSourceState> foodSources = new List<FoodSourceState>();
        public List<AgriculturalFieldState> fields = new List<AgriculturalFieldState>();
        public List<TradeOrderState> tradeOrders = new List<TradeOrderState>();
        public CityWeather dailyWeather;
        public int weatherDay = -1;
        public int treasuryCoins = 1000;
        public int reservedTradeCoins;
        public int tradeRevision;

        public CitySnapshot DeepCopy() => JsonUtility.FromJson<CitySnapshot>(JsonUtility.ToJson(this));
    }

    [Serializable]
    public sealed class HouseholdState
    {
        public int id;
        public int memberCount;
        public int homeBuildingId;
        public int claimedParcelId;
        public int preferredFoodSourceId;
        public int foodConsumedTotal;
        public int foodShortageDays;
        public bool hungry;
        public int marketBuildingId;
        public bool marketCovered;
        public int fuelShortageDays;
        public int clothingShortageDays;
        public int toolShortageDays;
        public bool fuelSatisfied = true;
        public bool clothingSatisfied = true;
        public bool toolsSatisfied = true;
        public int satisfactionPermille;
        public HouseholdLevel level;
    }

    public enum HouseholdLevel : byte
    {
        Destitute = 0,
        Basic = 1,
        Established = 2,
        Prosperous = 3
    }

    [Serializable]
    public sealed class RoadState
    {
        public int id;
        public CityPoint start;
        public CityPoint end;
        public bool blocked;
    }

    [Serializable]
    public sealed class ParcelState
    {
        public int id;
        public int roadId;
        public CityPoint center;
        public float width;
        public float depth;
        public float yaw;
        public float gardenDepth;
        public int terrainSlopePermille;
        public int extensionCapacity;
        public int extensionLevel;
        public bool hasGarden;
        public bool gardenActive;
        public bool accessible;
        public int householdId;
        public int buildingId;
    }

    public enum BuildingPhase : byte
    {
        Foundation = 0,
        Framing = 1,
        // La valeur 2 est conservée pour la compatibilité des fixtures et
        // futures sauvegardes issues du vertical slice.
        Complete = 2,
        Roofing = 3,
        Detailing = 4
    }

    [Serializable]
    public sealed class BuildingState
    {
        public int id;
        public BuildingArchetype archetype;
        public int parcelId;
        public int householdId;
        public CityPoint position;
        public float yaw;
        public int priority;
        public int requiredWood;
        public int deliveredWood;
        public float workRemaining;
        public BuildingPhase phase;
        public bool usesPhysicalConstruction;
        public bool terrainPrepared;
        public float terrainWorkRemaining;
        public int terrainCutFillMillimeters;
        public List<ConstructionMaterialState> constructionMaterials = new List<ConstructionMaterialState>();
        public float storageServiceRadius;
        public List<StoredResourceState> localStocks = new List<StoredResourceState>();
        public int marketCoveredHouseholds;
        public int marketScarcityPermille;
        public int marketPricePermille = 1000;
        public int marketShortageDays;
        public int marketLastProcessedDay = -1;
    }

    [Serializable]
    public sealed class ConstructionMaterialState
    {
        public BuildingPhase phase;
        public CityResourceKind resource;
        public int required;
        public int delivered;
    }

    [Serializable]
    public sealed class StoredResourceState
    {
        public CityResourceKind kind;
        public int quantity;
        public int reserved;
        public int capacity;
    }

    public enum VillagerActivity : byte
    {
        Idle = 0,
        GoingToStock = 1,
        GoingToSite = 2,
        Building = 3,
        GoingToWork = 4,
        WorkingJob = 5,
        GoingHome = 6,
        ReturningFood = 7
    }

    public enum VillagerJob : byte
    {
        None = 0,
        Builder = 1,
        Lumberjack = 2,
        GranaryKeeper = 3,
        WarehouseKeeper = 4,
        MarketTrader = 5,
        Blacksmith = 6,
        Stockman = 7,
        Cleric = 8,
        Forager = 9,
        Hunter = 10
    }

    [Serializable]
    public sealed class VillagerState
    {
        public int id;
        public int householdId;
        public CityPoint position;
        public CityPoint destination;
        public VillagerActivity activity;
        public int targetBuildingId;
        public int carryingWood;
        public int reservedWood;
        public CityResourceKind carryingResource;
        public CityResourceKind reservedResource;
        public int logisticsTaskId;
        public List<CityPoint> navigationPath = new List<CityPoint>();
        public int navigationIndex;
        public CityPoint navigationTarget;
        public int navigationRevision;
        public VillagerJob job;
        public int workplaceBuildingId;
        public int workplaceProductionSiteId;
        public int workplaceFoodSourceId;
        public float shiftStartHour = 8f;
        public float shiftEndHour = 18f;
        public bool absentToday;
        public int absenceCount;
        public bool isAtWork;
        public CityPoint homePosition;
        public bool homePositionInitialized;
        public int carryingFood;
        public float gatheringProgress;
    }

    public enum ProductionSiteKind : byte
    {
        LumberCamp = 1,
        Sawmill = 2,
        Quarry = 3,
        Forge = 4,
        Mill = 5,
        Oven = 6,
        Weaving = 7,
        Workshop = 8
    }

    [Serializable]
    public sealed class ProductionSiteState
    {
        public int id;
        public ProductionSiteKind kind;
        public CityPoint position;
        public int assignedWorkers;
        public int maxWorkers;
        public BuildingPhase constructionPhase;
        public float constructionProgress;
        public float productionProgress;
        public int remainingTimber;
        public int storedWood;
        public int reservedWood;
        public int inputAStored;
        public int inputBStored;
        public int outputStored;
        public int outputReserved;
        public int rawRemaining;
        public int totalBatches;
    }

    public enum CityResourceKind : byte
    {
        Wood = 1,
        Planks = 2,
        Stone = 3,
        Food = 4,
        Tools = 5,
        Textile = 6
    }

    [Serializable]
    public sealed class ResourceStockState
    {
        public CityResourceKind kind;
        public int quantity;
        public int reserved;
        public int capacity;
        public int lossRemainderPermille;
        public int totalLost;
    }

    public enum FoodSourceKind : byte
    {
        BerryGrove = 1,
        HuntingGround = 2
    }

    [Serializable]
    public sealed class FoodSourceState
    {
        public int id;
        public FoodSourceKind kind;
        public CityPoint position;
        public bool accessible = true;
        public int remainingFood;
        public int maxWorkers = 2;
        public float workPerFood = 5f;
    }

    public enum FieldPhase : byte
    {
        Fallow = 0,
        Plowing = 1,
        Sown = 2,
        Growing = 3,
        ReadyToHarvest = 4,
        Harvested = 5
    }

    public enum CityWeather : byte
    {
        Clear = 0,
        Rain = 1,
        Drought = 2,
        Frost = 3
    }

    [Serializable]
    public sealed class AgriculturalFieldState
    {
        public int id;
        public CityPoint position;
        public int fertilityPermille = 750;
        public FieldPhase phase;
        public int workDays;
        public int growthPoints;
        public int lastProcessedDay = -1;
        public int lastYield;
        public int totalHarvested;
    }

    public enum LogisticsEndpointKind : byte
    {
        GlobalStock = 1,
        Building = 2,
        ProductionSite = 3
    }

    public enum TradeDirection : byte
    {
        Import = 1,
        Export = 2
    }

    public enum TradeOrderStatus : byte
    {
        Traveling = 1,
        Completed = 2,
        Cancelled = 3
    }

    [Serializable]
    public sealed class TradeOrderState
    {
        public int id;
        public TradeDirection direction;
        public CityResourceKind resource;
        public int requestedQuantity;
        public int deliveredQuantity;
        public int unitPrice;
        public int feeCoins;
        public int createdDay;
        public int deliveryDay;
        public float travelProgress;
        public CityPoint merchantPosition;
        public TradeOrderStatus status;
        public int balanceDelta;
    }

    public enum LogisticsTaskStatus : byte
    {
        Pending = 0,
        Active = 1,
        Completed = 2,
        Cancelled = 3
    }

    [Serializable]
    public sealed class LogisticsTaskState
    {
        public int id;
        public CityResourceKind resource;
        public int priority;
        public LogisticsEndpointKind sourceKind;
        public int sourceId;
        public CityPoint sourcePosition;
        public LogisticsEndpointKind destinationKind;
        public int destinationId;
        public CityPoint destinationPosition;
        public int requestedQuantity;
        public int reservedQuantity;
        public int inTransitQuantity;
        public int deliveredQuantity;
        public LogisticsTaskStatus status;
    }

    public enum CitySeason : byte
    {
        Winter = 0,
        Spring = 1,
        Summer = 2,
        Autumn = 3
    }

    [Serializable]
    public sealed class CityCalendarState
    {
        public int absoluteDay;
        public int year = 1;
        public int month = 1;
        public int day = 1;
        public int hour;
        public int minute;
        public CitySeason season;
    }

    public enum ScheduledCityEventKind : byte
    {
        Marker = 1,
        Economy = 2,
        Weather = 3
    }

    public enum ScheduledCityEventStatus : byte
    {
        Pending = 0,
        Triggered = 1,
        Cancelled = 2
    }

    [Serializable]
    public sealed class ScheduledCityEventState
    {
        public int id;
        public ScheduledCityEventKind kind;
        public string key;
        public float triggerAtElapsedSeconds;
        public float triggeredAtElapsedSeconds;
        public ScheduledCityEventStatus status;
    }
}
