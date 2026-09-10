using System;
using System.Collections.Generic;
using UnityEngine;

namespace Victoria.CityMode
{
    /// <summary>
    /// Simulation locale volontairement petite. Elle prouve la boucle de jeu,
    /// mais reste derriere les contrats afin de pouvoir etre remplacee par le
    /// moteur Victoria sans exposer de GameObject comme verite metier.
    /// </summary>
    public sealed class LocalCitySimulation : ICityStateSource, ICityCommandSink
    {
        public const int MaxHouseholds = 20;
        public const int MaxBuildings = 30;
        public const float MapHalfExtent = 256f;
        public const float SecondsPerGameDay = 120f;
        public const int DaysPerMonth = 30;
        public const int MonthsPerYear = 12;

        const float ParcelRoadClearance = 3.2f;
        const float ParcelFrontSetback = 1.5f;
        const float MinimumParcelFrontage = 10.5f;
        const float MaximumParcelFrontage = 14.5f;
        const float MinimumParcelDepth = 22f;
        const float MaximumParcelDepth = 36f;
        const float MinimumGardenDepth = 5f;
        const int MaximumParcelSlopePermille = 180;

        static readonly Vector3 StockPosition = new Vector3(0f, 0f, -12f);
        readonly CitySnapshot state;
        readonly BuildingCatalog catalog;
        readonly CityResourceRegistry resourceRegistry;
        readonly ProductionRecipeCatalog productionRecipes;
        readonly DeterministicNavigationGrid navigation = new DeterministicNavigationGrid();
        IParcelTerrainSampler parcelTerrainSampler = FlatParcelTerrainSampler.Instance;
        int nextRoadId = 1;
        int nextParcelId = 1;
        int nextBuildingId = 1;
        int nextProductionSiteId = 1;
        int nextLogisticsTaskId = 1;
        int nextScheduledEventId = 1;
        int nextFoodSourceId = 1;
        int nextFieldId = 1;
        int nextTradeOrderId = 1;
        int employmentDay;

        public LocalCitySimulation(CitySnapshot initial, BuildingCatalog buildingCatalog = null)
        {
            state = initial != null ? initial.DeepCopy() : throw new ArgumentNullException(nameof(initial));
            catalog = buildingCatalog ?? BuildingCatalog.LoadDefault();
            resourceRegistry = CityResourceRegistry.CreateDefault();
            productionRecipes = new ProductionRecipeCatalog();
            state.households ??= new List<HouseholdState>();
            state.roads ??= new List<RoadState>();
            state.parcels ??= new List<ParcelState>();
            state.buildings ??= new List<BuildingState>();
            state.villagers ??= new List<VillagerState>();
            state.productionSites ??= new List<ProductionSiteState>();
            state.logisticsTasks ??= new List<LogisticsTaskState>();
            state.scheduledEvents ??= new List<ScheduledCityEventState>();
            state.resources ??= new List<ResourceStockState>();
            state.foodSources ??= new List<FoodSourceState>();
            state.fields ??= new List<AgriculturalFieldState>();
            state.tradeOrders ??= new List<TradeOrderState>();
            state.calendar ??= new CityCalendarState();
            if (!state.clockStateInitialized)
            {
                state.simulationSpeed = 1f;
                state.lastRunningSpeed = 1f;
                state.clockStateInitialized = true;
            }
            else
            {
                state.simulationSpeed = NormalizeSpeed(state.simulationSpeed, true);
                state.lastRunningSpeed = NormalizeSpeed(state.lastRunningSpeed, false);
            }
            UpdateCalendar();
            InitializeResourceStocks();
            foreach (var villager in state.villagers)
            {
                villager.navigationPath ??= new List<CityPoint>();
                if (!villager.homePositionInitialized)
                {
                    villager.homePosition = villager.position;
                    villager.homePositionInitialized = true;
                }
            }
            foreach (var building in state.buildings)
            {
                building.localStocks ??= new List<StoredResourceState>();
                if (building.archetype == BuildingArchetype.Unknown)
                    building.archetype = BuildingArchetype.Residence;
                if (building.constructionMaterials == null || building.constructionMaterials.Count == 0)
                {
                    building.constructionMaterials = new List<ConstructionMaterialState>();
                    if (building.phase != BuildingPhase.Complete && building.requiredWood > 0)
                        building.constructionMaterials.Add(new ConstructionMaterialState
                        {
                            phase = BuildingPhase.Foundation,
                            resource = CityResourceKind.Wood,
                            required = building.requiredWood,
                            delivered = Mathf.Min(building.requiredWood, building.deliveredWood)
                        });
                    building.terrainPrepared = true;
                    building.terrainWorkRemaining = 0f;
                }
            }
            nextRoadId = NextId(state.roads, item => item.id);
            nextParcelId = NextId(state.parcels, item => item.id);
            nextBuildingId = NextId(state.buildings, item => item.id);
            nextProductionSiteId = NextId(state.productionSites, item => item.id);
            nextLogisticsTaskId = NextId(state.logisticsTasks, item => item.id);
            nextScheduledEventId = NextId(state.scheduledEvents, item => item.id);
            nextFoodSourceId = NextId(state.foodSources, item => item.id);
            nextFieldId = NextId(state.fields, item => item.id);
            nextTradeOrderId = NextId(state.tradeOrders, item => item.id);
            navigation.Rebuild(state, catalog);
            employmentDay = state.employmentDay;
            if (state.employmentRevision == 0)
                RefreshEmployment(true);
            else
                RefreshProductionAssignments();
            RefreshServiceCapacities();
            UpdateParcelEvolution();
        }

        public BuildingCatalog Catalog => catalog;
        public CityResourceRegistry ResourceRegistry => resourceRegistry;
        public ProductionRecipeCatalog ProductionRecipes => productionRecipes;
        public float SimulationSpeed => state.simulationSpeed;
        public float LastRunningSpeed => state.lastRunningSpeed;
        public bool IsPaused => state.simulationSpeed <= 0f;
        internal CitySnapshot DiagnosticState => state;

        public void SetParcelTerrainSampler(IParcelTerrainSampler sampler)
        {
            parcelTerrainSampler = sampler ?? FlatParcelTerrainSampler.Instance;
        }

        public static LocalCitySimulation FromJson(string json, BuildingCatalog buildingCatalog = null)
        {
            if (string.IsNullOrWhiteSpace(json))
                throw new ArgumentException("Fixture JSON vide.", nameof(json));
            var snapshot = JsonUtility.FromJson<CitySnapshot>(json);
            if (snapshot == null || snapshot.cityId <= 0)
                throw new ArgumentException("Fixture CitySnapshot invalide.", nameof(json));
            return new LocalCitySimulation(snapshot, buildingCatalog);
        }

        public CitySnapshot GetSnapshot(int cityId)
        {
            if (cityId != state.cityId)
                throw new KeyNotFoundException($"Ville inconnue: {cityId}");
            SyncWoodResourceFromLegacy();
            return state.DeepCopy();
        }

        public CityCommandResult Submit(CityCommand command)
        {
            if (command == null)
                return CityCommandResult.Reject("command-null");
            return command.kind switch
            {
                CityCommandKind.DrawRoad => DrawRoad(command),
                CityCommandKind.ZoneResidential => ZoneResidential(command.targetId),
                CityCommandKind.SetConstructionPriority => SetPriority(command.targetId, command.priority),
                CityCommandKind.PlaceLumberCamp => PlaceLumberCamp(command.position),
                CityCommandKind.PlaceBuilding => PlaceBuilding(command.archetype, command.position),
                _ => CityCommandResult.Reject("command-unknown")
            };
        }

        public void Tick(float deltaTime)
        {
            if (deltaTime <= 0f)
                return;
            var step = Mathf.Min(deltaTime, 0.1f);
            state.elapsedSeconds += step;
            UpdateCalendar();
            ApplyDailyResourceLosses();
            TriggerScheduledEvents();

            RefreshEmployment(false);

            TickProductionSites(step);

            state.villagers.Sort((a, b) => a.id.CompareTo(b.id));
            for (var i = 0; i < state.villagers.Count; i++)
            {
                var villager = state.villagers[i];
                ApplyScheduleTransition(villager);
                switch (villager.activity)
                {
                    case VillagerActivity.Idle:
                        AssignWork(villager);
                        break;
                    case VillagerActivity.GoingToStock:
                        AdvanceToStock(villager, step);
                        break;
                    case VillagerActivity.GoingToSite:
                        AdvanceToSite(villager, step);
                        break;
                    case VillagerActivity.Building:
                        Build(villager, step);
                        break;
                    case VillagerActivity.GoingToWork:
                        AdvanceToWork(villager, step);
                        break;
                    case VillagerActivity.WorkingJob:
                        villager.isAtWork = true;
                        if (villager.job == VillagerJob.Forager || villager.job == VillagerJob.Hunter)
                            GatherFood(villager, step);
                        else if (villager.job == VillagerJob.GranaryKeeper ||
                            villager.job == VillagerJob.WarehouseKeeper ||
                            villager.job == VillagerJob.MarketTrader)
                            TryAssignLogisticsTask(villager, villager.workplaceBuildingId);
                        break;
                    case VillagerActivity.GoingHome:
                        AdvanceHome(villager, step);
                        break;
                    case VillagerActivity.ReturningFood:
                        ReturnFoodToStock(villager, step);
                        break;
                }
            }
            TickStorageBuildings();
            TickMarkets();
            TickTradeMerchants();
            SyncWoodResourceFromLegacy();
        }

        public bool SetRoadBlocked(int roadId, bool blocked)
        {
            var road = FindRoad(roadId);
            if (road == null)
                return false;
            road.blocked = blocked;
            foreach (var parcel in state.parcels)
                if (parcel.roadId == roadId)
                    parcel.accessible = !blocked;
            if (blocked)
                ReplanInaccessibleWorkers();
            return true;
        }

        public int TotalWoodInSystem()
        {
            var total = state.stockWood;
            foreach (var villager in state.villagers)
                total += villager.carryingWood;
            foreach (var building in state.buildings)
                total += building.deliveredWood;
            foreach (var site in state.productionSites)
                total += site.storedWood;
            return total;
        }

        public int EnqueueLogisticsTask(CityResourceKind resource,
            LogisticsEndpointKind sourceKind, int sourceId,
            LogisticsEndpointKind destinationKind, int destinationId,
            int quantity, int priority = 1)
        {
            if (resource == 0 || !Enum.IsDefined(typeof(CityResourceKind), resource) || quantity <= 0 ||
                !EndpointExists(sourceKind, sourceId) ||
                !EndpointExists(destinationKind, destinationId) ||
                destinationKind == LogisticsEndpointKind.Building &&
                    !CanReceiveAtBuilding(destinationId, resource) ||
                sourceKind == destinationKind && sourceId == destinationId)
                return 0;
            var task = new LogisticsTaskState
            {
                id = nextLogisticsTaskId++,
                resource = resource,
                priority = Mathf.Clamp(priority, 0, 3),
                sourceKind = sourceKind,
                sourceId = sourceId,
                sourcePosition = CityPoint.From(EndpointPosition(sourceKind, sourceId)),
                destinationKind = destinationKind,
                destinationId = destinationId,
                destinationPosition = CityPoint.From(EndpointPosition(destinationKind, destinationId)),
                requestedQuantity = quantity,
                status = LogisticsTaskStatus.Pending
            };
            state.logisticsTasks.Add(task);
            state.logisticsRevision++;
            return task.id;
        }

        public void SetSimulationSpeed(float speed)
        {
            state.simulationSpeed = NormalizeSpeed(speed, true);
            if (state.simulationSpeed > 0f)
                state.lastRunningSpeed = state.simulationSpeed;
        }

        public ResourceStockState GetResource(CityResourceKind kind) =>
            state.resources.Find(item => item.kind == kind);

        public int AddResource(CityResourceKind kind, int quantity)
        {
            if (quantity <= 0)
                return 0;
            var stock = GetResource(kind);
            if (stock == null)
                return 0;
            var accepted = Mathf.Min(quantity, Mathf.Max(0, stock.capacity - stock.quantity));
            stock.quantity += accepted;
            if (kind == CityResourceKind.Wood)
                state.stockWood = stock.quantity;
            return accepted;
        }

        public bool TryReserveResource(CityResourceKind kind, int quantity)
        {
            var stock = GetResource(kind);
            if (stock == null || quantity <= 0 || stock.quantity - stock.reserved < quantity)
                return false;
            stock.reserved += quantity;
            if (kind == CityResourceKind.Wood)
                state.reservedWood = stock.reserved;
            return true;
        }

        public bool TryConsumeReservedResource(CityResourceKind kind, int quantity)
        {
            var stock = GetResource(kind);
            if (stock == null || quantity <= 0 || stock.reserved < quantity || stock.quantity < quantity)
                return false;
            stock.reserved -= quantity;
            stock.quantity -= quantity;
            if (kind == CityResourceKind.Wood)
            {
                state.reservedWood = stock.reserved;
                state.stockWood = stock.quantity;
            }
            return true;
        }

        public void ReleaseResourceReservation(CityResourceKind kind, int quantity)
        {
            var stock = GetResource(kind);
            if (stock == null || quantity <= 0)
                return;
            stock.reserved = Mathf.Max(0, stock.reserved - quantity);
            if (kind == CityResourceKind.Wood)
                state.reservedWood = stock.reserved;
        }

        public int PlaceTradeOrder(TradeDirection direction, CityResourceKind resource,
            int quantity)
        {
            if ((direction != TradeDirection.Import && direction != TradeDirection.Export) ||
                resource == 0 || !Enum.IsDefined(typeof(CityResourceKind), resource) ||
                quantity <= 0 || quantity > 40)
                return 0;
            var unitPrice = TradeUnitPrice(resource);
            var gross = unitPrice * quantity;
            var fee = Mathf.Max(1, (gross + 9) / 10);
            if (direction == TradeDirection.Import)
            {
                var stock = GetResource(resource);
                if (stock == null || stock.capacity - stock.quantity < quantity ||
                    state.treasuryCoins - state.reservedTradeCoins < gross + fee)
                    return 0;
                state.reservedTradeCoins += gross + fee;
            }
            else if (!TryReserveResource(resource, quantity))
                return 0;
            var delay = 2 + (quantity - 1) / 20;
            var order = new TradeOrderState
            {
                id = nextTradeOrderId++,
                direction = direction,
                resource = resource,
                requestedQuantity = quantity,
                unitPrice = unitPrice,
                feeCoins = fee,
                createdDay = state.calendar.absoluteDay,
                deliveryDay = state.calendar.absoluteDay + delay,
                merchantPosition = CityPoint.From(new Vector3(MapHalfExtent, 0f, -MapHalfExtent)),
                status = TradeOrderStatus.Traveling
            };
            state.tradeOrders.Add(order);
            state.tradeRevision++;
            return order.id;
        }

        public bool CancelTradeOrder(int orderId)
        {
            var order = state.tradeOrders.Find(item => item.id == orderId);
            if (order == null || order.status != TradeOrderStatus.Traveling)
                return false;
            if (order.direction == TradeDirection.Import)
                state.reservedTradeCoins = Mathf.Max(0, state.reservedTradeCoins -
                    (order.unitPrice * order.requestedQuantity + order.feeCoins));
            else
                ReleaseResourceReservation(order.resource, order.requestedQuantity);
            order.status = TradeOrderStatus.Cancelled;
            state.tradeRevision++;
            return true;
        }

        public int AddFoodSource(FoodSourceKind kind, Vector3 position, int quantity,
            int maxWorkers = 2)
        {
            if (kind == 0 || quantity <= 0 || maxWorkers <= 0 || !InsideMap(position))
                return 0;
            var source = new FoodSourceState
            {
                id = nextFoodSourceId++,
                kind = kind,
                position = CityPoint.From(new Vector3(position.x, 0f, position.z)),
                accessible = true,
                remainingFood = quantity,
                maxWorkers = maxWorkers,
                workPerFood = kind == FoodSourceKind.HuntingGround ? 8f : 5f
            };
            state.foodSources.Add(source);
            RefreshEmployment(true);
            return source.id;
        }

        public bool SetFoodSourceAccessible(int sourceId, bool accessible)
        {
            var source = state.foodSources.Find(item => item.id == sourceId);
            if (source == null)
                return false;
            source.accessible = accessible;
            RefreshEmployment(true);
            return true;
        }

        public int AddAgriculturalField(Vector3 position, int fertilityPermille = 750)
        {
            if (!InsideMap(position) || fertilityPermille < 0 || fertilityPermille > 1000)
                return 0;
            var field = new AgriculturalFieldState
            {
                id = nextFieldId++,
                position = CityPoint.From(new Vector3(position.x, 0f, position.z)),
                fertilityPermille = fertilityPermille,
                phase = FieldPhase.Fallow,
                lastProcessedDay = state.calendar.absoluteDay
            };
            state.fields.Add(field);
            return field.id;
        }

        public int AddProductionFacility(ProductionSiteKind kind, Vector3 position,
            int rawRemaining = -1)
        {
            if (!productionRecipes.TryGet(kind, out var recipe) || !InsideMap(position))
                return 0;
            var site = new ProductionSiteState
            {
                id = nextProductionSiteId++,
                kind = kind,
                position = CityPoint.From(new Vector3(position.x, 0f, position.z)),
                assignedWorkers = 1,
                maxWorkers = 1,
                constructionPhase = BuildingPhase.Complete,
                rawRemaining = rawRemaining >= 0 ? rawRemaining : recipe.defaultRawReserve
            };
            state.productionSites.Add(site);
            return site.id;
        }

        public BuildingState FindNearestStorage(CityResourceKind resource, Vector3 origin)
        {
            BuildingState chosen = null;
            var chosenDistance = float.MaxValue;
            foreach (var building in state.buildings)
            {
                var stock = FindLocalStock(building, resource);
                if (building.phase != BuildingPhase.Complete || stock == null)
                    continue;
                var distance = PlanarSqrDistance(origin, building.position.ToVector3());
                if (distance > building.storageServiceRadius * building.storageServiceRadius)
                    continue;
                if (chosen == null || distance < chosenDistance - 0.0001f ||
                    Mathf.Abs(distance - chosenDistance) <= 0.0001f && building.id < chosen.id)
                {
                    chosen = building;
                    chosenDistance = distance;
                }
            }
            return chosen;
        }

        public int ScheduleEvent(ScheduledCityEventKind kind, string key, float delaySeconds)
        {
            if (kind == 0 || string.IsNullOrWhiteSpace(key) ||
                float.IsNaN(delaySeconds) || float.IsInfinity(delaySeconds) || delaySeconds < 0f)
                return 0;
            var scheduled = new ScheduledCityEventState
            {
                id = nextScheduledEventId++,
                kind = kind,
                key = key,
                triggerAtElapsedSeconds = state.elapsedSeconds + delaySeconds,
                status = ScheduledCityEventStatus.Pending
            };
            state.scheduledEvents.Add(scheduled);
            state.scheduledEvents.Sort((left, right) =>
            {
                var timeOrder = left.triggerAtElapsedSeconds.CompareTo(right.triggerAtElapsedSeconds);
                return timeOrder != 0 ? timeOrder : left.id.CompareTo(right.id);
            });
            return scheduled.id;
        }

        public bool CancelScheduledEvent(int eventId)
        {
            var scheduled = state.scheduledEvents.Find(item => item.id == eventId);
            if (scheduled == null || scheduled.status != ScheduledCityEventStatus.Pending)
                return false;
            scheduled.status = ScheduledCityEventStatus.Cancelled;
            return true;
        }

        public bool DestroyBuilding(int buildingId)
        {
            var building = FindBuilding(buildingId);
            if (building == null)
                return false;
            CancelTasksForEndpoint(LogisticsEndpointKind.Building, buildingId);
            state.buildings.Remove(building);
            var parcel = FindParcel(building.parcelId);
            if (parcel != null)
            {
                parcel.buildingId = 0;
                parcel.householdId = 0;
            }
            var household = FindHousehold(building.householdId);
            if (household != null)
            {
                household.homeBuildingId = 0;
                household.claimedParcelId = 0;
            }
            UpdateParcelEvolution();
            RebuildNavigation();
            RefreshServiceCapacities();
            RefreshEmployment(true);
            return true;
        }

        public bool DestroyProductionSite(int siteId)
        {
            var site = state.productionSites.Find(item => item.id == siteId);
            if (site == null)
                return false;
            CancelTasksForEndpoint(LogisticsEndpointKind.ProductionSite, siteId);
            state.productionSites.Remove(site);
            RebuildNavigation();
            RefreshEmployment(true);
            return true;
        }

        CityCommandResult DrawRoad(CityCommand command)
        {
            var start = command.start.ToVector3();
            var end = command.end.ToVector3();
            start.y = 0f;
            end.y = 0f;
            if (!InsideMap(start) || !InsideMap(end))
                return CityCommandResult.Reject("road-outside-map");
            var length = Vector3.Distance(start, end);
            if (length < 4f)
                return CityCommandResult.Reject("road-too-short");
            if (length > 150f)
                return CityCommandResult.Reject("road-too-long");

            var road = new RoadState
            {
                id = nextRoadId++,
                start = CityPoint.From(start),
                end = CityPoint.From(end),
                blocked = false
            };
            state.roads.Add(road);
            return CityCommandResult.Accept(road.id);
        }

        CityCommandResult ZoneResidential(int roadId)
        {
            var residence = catalog.Get(BuildingArchetype.Residence);
            var road = FindRoad(roadId);
            if (road == null)
                return CityCommandResult.Reject("road-unknown");
            if (road.blocked)
                return CityCommandResult.Reject("road-inaccessible");
            foreach (var existing in state.parcels)
                if (existing.roadId == roadId)
                    return CityCommandResult.Reject("road-already-zoned");

            var start = road.start.ToVector3();
            var end = road.end.ToVector3();
            var direction = (end - start).normalized;
            var normal = new Vector3(-direction.z, 0f, direction.x);
            var length = Vector3.Distance(start, end);
            var lotCountPerSide = Mathf.Clamp(Mathf.FloorToInt(length / 12f), 1, 8);
            var slotWidth = length / lotCountPerSide;
            var created = 0;

            for (var side = -1; side <= 1; side += 2)
            {
                for (var lot = 0; lot < lotCountPerSide && state.parcels.Count < MaxBuildings; lot++)
                {
                    var t = (lot + 0.5f) / lotCountPerSide;
                    var frontageVariation = StableUnit(state.seed, roadId, side, lot, 17);
                    var depthVariation = StableUnit(state.seed, roadId, side, lot, 31);
                    var width = Mathf.Clamp(slotWidth * Mathf.Lerp(0.82f, 0.96f, frontageVariation),
                        MinimumParcelFrontage, MaximumParcelFrontage);
                    var depth = Mathf.Lerp(MinimumParcelDepth, MaximumParcelDepth, depthVariation);
                    var back = normal * side;
                    var center = Vector3.Lerp(start, end, t) + back * (ParcelRoadClearance + depth * 0.5f);
                    if (!TryMeasureParcelTerrain(center, direction, back, width, depth,
                        out var elevation, out var slopePermille))
                        continue;
                    center.y = elevation;
                    if (OverlapsExistingParcel(center, direction, back, width, depth))
                        continue;
                    var gardenDepth = Mathf.Max(0f,
                        depth - residence.footprintDepth - ParcelFrontSetback * 2f);
                    var extensionCapacity = gardenDepth >= 11f ? 2 : gardenDepth >= 7f ? 1 : 0;
                    state.parcels.Add(new ParcelState
                    {
                        id = nextParcelId++,
                        roadId = roadId,
                        center = CityPoint.From(center),
                        width = width,
                        depth = depth,
                        yaw = Mathf.Atan2(back.x, back.z) * Mathf.Rad2Deg,
                        gardenDepth = gardenDepth,
                        terrainSlopePermille = slopePermille,
                        extensionCapacity = extensionCapacity,
                        extensionLevel = 0,
                        hasGarden = gardenDepth >= MinimumGardenDepth,
                        gardenActive = false,
                        accessible = true
                    });
                    created++;
                }
            }

            if (created == 0)
                return CityCommandResult.Reject("no-valid-parcel");
            ClaimParcelsAndCreateSites();
            return CityCommandResult.Accept(roadId);
        }

        bool TryMeasureParcelTerrain(Vector3 center, Vector3 frontageAxis, Vector3 depthAxis,
            float width, float depth, out float elevation, out int slopePermille)
        {
            var halfWidth = frontageAxis * (width * 0.5f);
            var halfDepth = depthAxis * (depth * 0.5f);
            var points = new[]
            {
                center - halfWidth - halfDepth,
                center + halfWidth - halfDepth,
                center - halfWidth + halfDepth,
                center + halfWidth + halfDepth,
                center
            };
            var minimum = float.PositiveInfinity;
            var maximum = float.NegativeInfinity;
            var sum = 0f;
            foreach (var point in points)
            {
                if (!InsideMap(point))
                {
                    elevation = 0f;
                    slopePermille = 0;
                    return false;
                }
                var height = parcelTerrainSampler.SampleHeight(point);
                if (float.IsNaN(height) || float.IsInfinity(height))
                {
                    elevation = 0f;
                    slopePermille = 0;
                    return false;
                }
                minimum = Mathf.Min(minimum, height);
                maximum = Mathf.Max(maximum, height);
                sum += height;
            }
            elevation = sum / points.Length;
            slopePermille = Mathf.RoundToInt((maximum - minimum) /
                Mathf.Max(MinimumParcelFrontage, Mathf.Min(width, depth)) * 1000f);
            return slopePermille <= MaximumParcelSlopePermille;
        }

        bool OverlapsExistingParcel(Vector3 center, Vector3 frontageAxis, Vector3 depthAxis,
            float width, float depth)
        {
            foreach (var existing in state.parcels)
            {
                var rotation = Quaternion.Euler(0f, existing.yaw, 0f);
                var existingDepth = rotation * Vector3.forward;
                var existingFrontage = rotation * Vector3.right;
                if (OrientedRectanglesOverlap(center, frontageAxis, depthAxis, width, depth,
                    existing.center.ToVector3(), existingFrontage, existingDepth,
                    existing.width, existing.depth))
                    return true;
            }
            return false;
        }

        static bool OrientedRectanglesOverlap(Vector3 leftCenter, Vector3 leftFrontage,
            Vector3 leftDepth, float leftWidth, float leftLength, Vector3 rightCenter,
            Vector3 rightFrontage, Vector3 rightDepth, float rightWidth, float rightLength)
        {
            var delta = rightCenter - leftCenter;
            var axes = new[] { leftFrontage, leftDepth, rightFrontage, rightDepth };
            foreach (var axis in axes)
            {
                var distance = Mathf.Abs(Vector3.Dot(delta, axis));
                var leftRadius = Mathf.Abs(Vector3.Dot(leftFrontage, axis)) * leftWidth * 0.5f +
                    Mathf.Abs(Vector3.Dot(leftDepth, axis)) * leftLength * 0.5f;
                var rightRadius = Mathf.Abs(Vector3.Dot(rightFrontage, axis)) * rightWidth * 0.5f +
                    Mathf.Abs(Vector3.Dot(rightDepth, axis)) * rightLength * 0.5f;
                if (distance >= leftRadius + rightRadius - 0.05f)
                    return false;
            }
            return true;
        }

        static float StableUnit(int seed, int roadId, int side, int lot, int salt)
        {
            unchecked
            {
                uint value = (uint)seed;
                value = (value ^ (uint)roadId * 0x9E3779B9u) * 0x85EBCA6Bu;
                value = (value ^ (uint)(side + 2) * 0xC2B2AE35u) * 0x27D4EB2Fu;
                value = (value ^ (uint)lot * 0x165667B1u) * 0x85EBCA6Bu;
                value ^= (uint)salt * 0x9E3779B9u;
                value ^= value >> 16;
                return (value & 0x00FFFFFFu) / 16777215f;
            }
        }

        CityCommandResult SetPriority(int buildingId, int priority)
        {
            var building = FindBuilding(buildingId);
            if (building == null)
                return CityCommandResult.Reject("building-unknown");
            building.priority = Mathf.Clamp(priority, 0, 3);
            foreach (var task in state.logisticsTasks)
                if (task.destinationKind == LogisticsEndpointKind.Building &&
                    task.destinationId == building.id &&
                    task.status != LogisticsTaskStatus.Completed &&
                    task.status != LogisticsTaskStatus.Cancelled)
                    task.priority = building.priority;
            RefreshEmployment(true, false);
            return CityCommandResult.Accept(buildingId);
        }

        CityCommandResult PlaceLumberCamp(CityPoint requestedPosition)
        {
            var definition = catalog.Get(BuildingArchetype.LumberCamp);
            var position = requestedPosition.ToVector3();
            position.y = 0f;
            if (!InsideMap(position))
                return CityCommandResult.Reject("lumber-camp-outside-map");

            var distanceFromCentre = PlanarDistance(position, Vector3.zero);
            if (distanceFromCentre < definition.placementMinDistance)
                return CityCommandResult.Reject("lumber-camp-too-close-to-centre");
            if (distanceFromCentre > definition.placementMaxDistance)
                return CityCommandResult.Reject("lumber-camp-too-far-from-centre");

            foreach (var existing in state.productionSites)
            {
                if (existing.kind == ProductionSiteKind.LumberCamp &&
                    PlanarDistance(position, existing.position.ToVector3()) < definition.placementSpacing)
                    return CityCommandResult.Reject("lumber-camp-too-close-to-another-camp");
            }

            if (state.stockWood - state.reservedWood < definition.woodCost)
                return CityCommandResult.Reject("lumber-camp-insufficient-wood");

            var camp = new ProductionSiteState
            {
                id = nextProductionSiteId++,
                kind = ProductionSiteKind.LumberCamp,
                position = CityPoint.From(position),
                assignedWorkers = 0,
                maxWorkers = definition.maxWorkers,
                constructionPhase = BuildingPhase.Foundation,
                constructionProgress = 0f,
                productionProgress = 0f,
                remainingTimber = definition.initialResource
            };
            state.stockWood -= definition.woodCost;
            state.productionSites.Add(camp);
            RebuildNavigation();
            RefreshEmployment(true);
            RefreshProductionAssignments();
            return CityCommandResult.Accept(camp.id);
        }

        CityCommandResult PlaceBuilding(BuildingArchetype archetype, CityPoint requestedPosition)
        {
            if (archetype < BuildingArchetype.Granary || archetype > BuildingArchetype.Chapel)
                return CityCommandResult.Reject("building-archetype-not-placeable");
            if (state.buildings.Count >= MaxBuildings)
                return CityCommandResult.Reject("building-limit-reached");
            var definition = catalog.Get(archetype);
            var position = requestedPosition.ToVector3();
            position.y = 0f;
            if (Mathf.Abs(position.x) > MapHalfExtent - definition.footprintWidth * 0.5f ||
                Mathf.Abs(position.z) > MapHalfExtent - definition.footprintDepth * 0.5f)
                return CityCommandResult.Reject("building-outside-map");
            if (state.stockWood - state.reservedWood < definition.woodCost)
                return CityCommandResult.Reject("building-insufficient-wood");

            foreach (var existing in state.buildings)
            {
                var existingDefinition = catalog.Get(existing.archetype);
                var spacing = Mathf.Max(definition.placementSpacing, existingDefinition.placementSpacing);
                if (PlanarDistance(position, existing.position.ToVector3()) < spacing)
                    return CityCommandResult.Reject("building-overlap");
            }
            foreach (var site in state.productionSites)
                if (PlanarDistance(position, site.position.ToVector3()) < definition.placementSpacing)
                    return CityCommandResult.Reject("building-overlap");

            var building = new BuildingState
            {
                id = nextBuildingId++,
                archetype = archetype,
                position = CityPoint.From(position),
                priority = 1,
                requiredWood = definition.woodCost,
                deliveredWood = 0,
                workRemaining = definition.constructionWork,
                phase = BuildingPhase.Foundation
            };
            InitializeNewConstruction(building, definition);
            state.buildings.Add(building);
            RebuildNavigation();
            RefreshEmployment(true);
            return CityCommandResult.Accept(building.id);
        }

        void TickProductionSites(float deltaTime)
        {
            if (state.productionSites.Count == 0)
                return;

            RefreshProductionAssignments();
            var lumberCamp = catalog.Get(BuildingArchetype.LumberCamp);
            var employmentChanged = false;
            foreach (var site in state.productionSites)
            {
                if (productionRecipes.TryGet(site.kind, out var recipe))
                {
                    TickProductionFacility(site, recipe, deltaTime);
                    continue;
                }
                var presentWorkers = PresentWorkers(site.id);
                if (site.kind != ProductionSiteKind.LumberCamp || presentWorkers <= 0 ||
                    site.remainingTimber <= 0)
                    continue;

                if (site.constructionPhase != BuildingPhase.Complete)
                {
                    site.constructionProgress = Mathf.Clamp01(site.constructionProgress +
                        deltaTime * presentWorkers / lumberCamp.constructionWork);
                    site.constructionPhase = ConstructionPhase(site.constructionProgress,
                        lumberCamp.phaseThresholds);
                    continue;
                }

                site.productionProgress += deltaTime * presentWorkers;
                while (site.productionProgress + 0.000001f >= lumberCamp.productionWork &&
                       site.remainingTimber > 0)
                {
                    site.productionProgress = Mathf.Max(0f, site.productionProgress - lumberCamp.productionWork);
                    site.remainingTimber -= 1;
                    state.stockWood += 1;
                }

                if (site.remainingTimber == 0)
                {
                    site.productionProgress = 0f;
                    site.assignedWorkers = 0;
                    employmentChanged = true;
                }
            }
            if (employmentChanged)
                RefreshEmployment(true);
            RefreshProductionAssignments();
        }

        void TickProductionFacility(ProductionSiteState site,
            ProductionRecipeDefinition recipe, float deltaTime)
        {
            EnsureFacilityInputTask(site, recipe.inputA, recipe.inputAQuantity,
                site.inputAStored);
            EnsureFacilityInputTask(site, recipe.inputB, recipe.inputBQuantity,
                site.inputBStored);

            if (site.assignedWorkers > 0 && site.outputStored < 32)
            {
                site.productionProgress = Mathf.Min(recipe.workSeconds,
                    site.productionProgress + deltaTime * site.assignedWorkers);
                while (site.productionProgress + 0.000001f >= recipe.workSeconds &&
                    CanRunRecipe(site, recipe) && site.outputStored + recipe.outputQuantity <= 32)
                {
                    site.productionProgress = Mathf.Max(0f,
                        site.productionProgress - recipe.workSeconds);
                    if (recipe.inputAQuantity > 0)
                        site.inputAStored -= recipe.inputAQuantity;
                    if (recipe.inputBQuantity > 0)
                        site.inputBStored -= recipe.inputBQuantity;
                    if (recipe.defaultRawReserve > 0)
                        site.rawRemaining--;
                    site.outputStored += recipe.outputQuantity;
                    site.totalBatches++;
                }
            }

            if (site.outputStored > 0 && !HasOpenFacilityTask(site.id, recipe.output, false))
                EnqueueLogisticsTask(recipe.output, LogisticsEndpointKind.ProductionSite,
                    site.id, LogisticsEndpointKind.GlobalStock, 0, site.outputStored, 2);
        }

        bool CanRunRecipe(ProductionSiteState site, ProductionRecipeDefinition recipe) =>
            (recipe.inputAQuantity == 0 || site.inputAStored >= recipe.inputAQuantity) &&
            (recipe.inputBQuantity == 0 || site.inputBStored >= recipe.inputBQuantity) &&
            (recipe.defaultRawReserve == 0 || site.rawRemaining > 0);

        void EnsureFacilityInputTask(ProductionSiteState site, CityResourceKind resource,
            int perBatch, int stored)
        {
            if (resource == 0 || perBatch <= 0 || stored >= perBatch * 2 ||
                HasOpenFacilityTask(site.id, resource, true))
                return;
            EnqueueLogisticsTask(resource, LogisticsEndpointKind.GlobalStock, 0,
                LogisticsEndpointKind.ProductionSite, site.id,
                perBatch * 2 - stored, 2);
        }

        bool HasOpenFacilityTask(int siteId, CityResourceKind resource, bool incoming)
        {
            foreach (var task in state.logisticsTasks)
                if (task.resource == resource &&
                    task.status != LogisticsTaskStatus.Completed &&
                    task.status != LogisticsTaskStatus.Cancelled &&
                    (incoming
                        ? task.destinationKind == LogisticsEndpointKind.ProductionSite && task.destinationId == siteId
                        : task.sourceKind == LogisticsEndpointKind.ProductionSite && task.sourceId == siteId))
                    return true;
            return false;
        }

        static BuildingPhase ConstructionPhase(float progress, float[] thresholds)
        {
            if (progress < thresholds[0]) return BuildingPhase.Foundation;
            if (progress < thresholds[1]) return BuildingPhase.Framing;
            if (progress < thresholds[2]) return BuildingPhase.Roofing;
            if (progress < thresholds[3]) return BuildingPhase.Detailing;
            return BuildingPhase.Complete;
        }

        void RefreshProductionAssignments()
        {
            state.productionSites.Sort((left, right) => left.id.CompareTo(right.id));
            foreach (var site in state.productionSites)
            {
                if (site.kind != ProductionSiteKind.LumberCamp)
                    continue;
                if (site.remainingTimber <= 0)
                {
                    site.assignedWorkers = 0;
                    continue;
                }
                var assigned = 0;
                foreach (var villager in state.villagers)
                    if (villager.job == VillagerJob.Lumberjack &&
                        villager.workplaceProductionSiteId == site.id)
                        assigned++;
                site.assignedWorkers = Mathf.Min(site.maxWorkers, assigned);
            }
        }

        int PresentWorkers(int productionSiteId)
        {
            var present = 0;
            foreach (var villager in state.villagers)
                if (villager.job == VillagerJob.Lumberjack &&
                    villager.workplaceProductionSiteId == productionSiteId &&
                    villager.activity == VillagerActivity.WorkingJob && villager.isAtWork)
                    present++;
            return present;
        }

        void ClaimParcelsAndCreateSites()
        {
            var residence = catalog.Get(BuildingArchetype.Residence);
            state.households.Sort((a, b) => a.id.CompareTo(b.id));
            state.parcels.Sort((a, b) => a.id.CompareTo(b.id));
            foreach (var household in state.households)
            {
                if (household.homeBuildingId != 0 || household.claimedParcelId != 0)
                    continue;
                ParcelState parcel = null;
                foreach (var candidate in state.parcels)
                {
                    if (candidate.accessible && candidate.householdId == 0 && candidate.buildingId == 0)
                    {
                        parcel = candidate;
                        break;
                    }
                }
                if (parcel == null || state.buildings.Count >= MaxBuildings)
                    break;

                var building = new BuildingState
                {
                    id = nextBuildingId++,
                    archetype = BuildingArchetype.Residence,
                    parcelId = parcel.id,
                    householdId = household.id,
                    position = ParcelBuildingPosition(parcel, residence),
                    yaw = ParcelFacingYaw(parcel),
                    priority = 1,
                    requiredWood = residence.woodCost,
                    deliveredWood = 0,
                    workRemaining = residence.constructionWork,
                    phase = BuildingPhase.Foundation
                };
                InitializeNewConstruction(building, residence);
                household.claimedParcelId = parcel.id;
                parcel.householdId = household.id;
                parcel.buildingId = building.id;
                state.buildings.Add(building);
            }
            RebuildNavigation();
            RefreshEmployment(true);
            UpdateParcelEvolution();
        }

        CityPoint ParcelBuildingPosition(ParcelState parcel, BuildingDefinition residence)
        {
            var back = Quaternion.Euler(0f, parcel.yaw, 0f) * Vector3.forward;
            var offset = parcel.depth * 0.5f - ParcelFrontSetback - residence.footprintDepth * 0.5f;
            var position = parcel.center.ToVector3() - back * Mathf.Max(0f, offset);
            position.y = parcel.center.y;
            return CityPoint.From(position);
        }

        void InitializeNewConstruction(BuildingState building, BuildingDefinition definition)
        {
            building.usesPhysicalConstruction = true;
            building.constructionMaterials = new List<ConstructionMaterialState>();
            if (building.archetype == BuildingArchetype.Residence)
            {
                AddConstructionMaterial(building, BuildingPhase.Foundation,
                    CityResourceKind.Wood, definition.woodCost);
            }
            else
            {
                AddConstructionMaterial(building, BuildingPhase.Foundation,
                    CityResourceKind.Stone, Mathf.Max(1, Mathf.CeilToInt(definition.woodCost * 0.35f)));
                AddConstructionMaterial(building, BuildingPhase.Framing,
                    CityResourceKind.Wood, definition.woodCost);
                AddConstructionMaterial(building, BuildingPhase.Roofing,
                    CityResourceKind.Planks, Mathf.Max(1, Mathf.CeilToInt(definition.woodCost * 0.45f)));
                AddConstructionMaterial(building, BuildingPhase.Detailing,
                    CityResourceKind.Tools, Mathf.Max(1, Mathf.CeilToInt(definition.woodCost * 0.10f)));
            }

            var position = building.position.ToVector3();
            var rotation = Quaternion.Euler(0f, building.yaw, 0f);
            var right = rotation * Vector3.right * (definition.footprintWidth * 0.5f);
            var forward = rotation * Vector3.forward * (definition.footprintDepth * 0.5f);
            var samples = new[]
            {
                position,
                position - right - forward,
                position + right - forward,
                position - right + forward,
                position + right + forward
            };
            var minimum = float.PositiveInfinity;
            var maximum = float.NegativeInfinity;
            var sum = 0f;
            foreach (var sample in samples)
            {
                var height = parcelTerrainSampler.SampleHeight(sample);
                if (float.IsNaN(height) || float.IsInfinity(height))
                    height = position.y;
                minimum = Mathf.Min(minimum, height);
                maximum = Mathf.Max(maximum, height);
                sum += height;
            }
            position.y = sum / samples.Length;
            building.position = CityPoint.From(position);
            building.terrainCutFillMillimeters = Mathf.Max(0,
                Mathf.RoundToInt((maximum - minimum) * 1000f));
            building.terrainWorkRemaining = 1.5f +
                definition.footprintWidth * definition.footprintDepth / 80f +
                building.terrainCutFillMillimeters / 300f;
            building.terrainPrepared = false;
        }

        static void AddConstructionMaterial(BuildingState building, BuildingPhase phase,
            CityResourceKind resource, int required)
        {
            if (required <= 0)
                return;
            building.constructionMaterials.Add(new ConstructionMaterialState
            {
                phase = phase,
                resource = resource,
                required = required,
                delivered = 0
            });
        }

        void AssignWork(VillagerState villager)
        {
            if (villager.job != VillagerJob.Builder || villager.absentToday || !IsWorkTime())
                return;
            var chosen = FindBuilding(villager.workplaceBuildingId);
            if (chosen == null || chosen.phase == BuildingPhase.Complete || !IsBuildingAccessible(chosen))
                return;
            if (!chosen.usesPhysicalConstruction && TryAssignLogisticsTask(villager))
                return;
            villager.targetBuildingId = chosen.id;
            if (!chosen.terrainPrepared)
            {
                villager.destination = chosen.position;
                villager.activity = VillagerActivity.GoingToSite;
            }
            else if (MissingConstructionMaterial(chosen) is ConstructionMaterialState missing)
            {
                FindOrCreateConstructionTask(chosen, missing);
                TryAssignLogisticsTask(villager,
                    chosen.usesPhysicalConstruction ? chosen.id : 0);
            }
            else
            {
                villager.destination = chosen.position;
                villager.activity = VillagerActivity.GoingToSite;
            }
        }

        void AdvanceToStock(VillagerState villager, float deltaTime)
        {
            var task = FindLogisticsTask(villager.logisticsTaskId);
            if (task == null || task.status == LogisticsTaskStatus.Cancelled ||
                task.status == LogisticsTaskStatus.Completed || villager.reservedWood <= 0 ||
                !EndpointExists(task.sourceKind, task.sourceId) ||
                !EndpointExists(task.destinationKind, task.destinationId))
            {
                AbandonLogistics(villager);
                SetIdle(villager);
                return;
            }
            var sourcePosition = EndpointPosition(task.sourceKind, task.sourceId);
            if (!MoveTowards(villager, sourcePosition, deltaTime))
                return;
            if (!TakeReservedFromSource(task, villager.reservedWood))
            {
                AbandonLogistics(villager);
                SetIdle(villager);
                return;
            }
            villager.carryingWood = villager.reservedWood;
            villager.carryingResource = task.resource;
            task.reservedQuantity = Mathf.Max(0, task.reservedQuantity - villager.reservedWood);
            task.inTransitQuantity += villager.reservedWood;
            villager.reservedWood = 0;
            if (!EndpointExists(task.destinationKind, task.destinationId))
            {
                AbandonLogistics(villager);
                SetIdle(villager);
                return;
            }
            villager.destination = CityPoint.From(EndpointPosition(task.destinationKind, task.destinationId));
            villager.activity = VillagerActivity.GoingToSite;
        }

        void AdvanceToSite(VillagerState villager, float deltaTime)
        {
            var task = FindLogisticsTask(villager.logisticsTaskId);
            if (task == null)
            {
                var worksite = FindBuilding(villager.targetBuildingId);
                if (worksite == null || !IsBuildingAccessible(worksite))
                {
                    SetIdle(villager);
                    return;
                }
                if (MoveTowards(villager, worksite.position.ToVector3(), deltaTime))
                    villager.activity = VillagerActivity.Building;
                return;
            }
            if (task.status == LogisticsTaskStatus.Cancelled ||
                !EndpointExists(task.destinationKind, task.destinationId))
            {
                AbandonLogistics(villager);
                SetIdle(villager);
                return;
            }
            var destination = EndpointPosition(task.destinationKind, task.destinationId);
            if (!MoveTowards(villager, destination, deltaTime))
                return;
            if (villager.carryingWood > 0)
            {
                DeliverToEndpoint(task, villager.carryingWood);
                task.inTransitQuantity = Mathf.Max(0, task.inTransitQuantity - villager.carryingWood);
                task.deliveredQuantity += villager.carryingWood;
                villager.carryingWood = 0;
                villager.carryingResource = 0;
                if (task.deliveredQuantity >= task.requestedQuantity)
                    task.status = LogisticsTaskStatus.Completed;
            }
            villager.logisticsTaskId = 0;
            var building = task.destinationKind == LogisticsEndpointKind.Building
                ? FindBuilding(task.destinationId)
                : null;
            if (building != null && villager.workplaceBuildingId == building.id)
            {
                villager.targetBuildingId = building.id;
                villager.activity = VillagerActivity.Building;
            }
            else
                SetIdle(villager);
        }

        void Build(VillagerState villager, float deltaTime)
        {
            var building = FindBuilding(villager.targetBuildingId);
            if (building == null || !IsBuildingAccessible(building))
            {
                SetIdle(villager);
                return;
            }
            if (building.phase == BuildingPhase.Complete)
            {
                SetIdle(villager);
                return;
            }
            if (!building.terrainPrepared)
            {
                building.terrainWorkRemaining = Mathf.Max(0f,
                    building.terrainWorkRemaining - deltaTime);
                if (building.terrainWorkRemaining <= 0f)
                {
                    building.terrainPrepared = true;
                    SetIdle(villager);
                }
                return;
            }
            if (MissingConstructionMaterial(building) != null)
            {
                SetIdle(villager);
                return;
            }
            building.workRemaining = Mathf.Max(0f, building.workRemaining - deltaTime);
            var definition = catalog.Get(building.archetype);
            var workProgress = 1f - building.workRemaining / definition.constructionWork;
            var previousPhase = building.phase;
            building.phase = ConstructionPhase(workProgress, definition.phaseThresholds);
            if (building.workRemaining > 0f)
            {
                if (building.phase != previousPhase)
                    SetIdle(villager);
                return;
            }
            building.phase = BuildingPhase.Complete;
            var household = FindHousehold(building.householdId);
            if (household != null)
                household.homeBuildingId = building.id;
            UpdateParcelEvolution();
            RefreshServiceCapacities();
            RebuildNavigation();
            RefreshEmployment(true);
            SetIdle(villager);
        }

        void RefreshServiceCapacities()
        {
            state.foodStorageCapacity = 0;
            state.goodsStorageCapacity = 0;
            state.marketServiceCapacity = 0;
            state.toolProductionCapacity = 0;
            state.livestockCapacity = 0;
            state.faithServiceCapacity = 0;
            foreach (var building in state.buildings)
            {
                if (building.phase != BuildingPhase.Complete)
                    continue;
                var capacity = catalog.Get(building.archetype).serviceCapacity;
                switch (building.archetype)
                {
                    case BuildingArchetype.Granary:
                        state.foodStorageCapacity += capacity;
                        EnsureStorageDefinition(building, CityResourceKind.Food, capacity, 85f);
                        break;
                    case BuildingArchetype.Warehouse:
                        state.goodsStorageCapacity += capacity;
                        var perCategory = Mathf.Max(1, capacity / 5);
                        EnsureStorageDefinition(building, CityResourceKind.Wood, perCategory, 110f);
                        EnsureStorageDefinition(building, CityResourceKind.Planks, perCategory, 110f);
                        EnsureStorageDefinition(building, CityResourceKind.Stone, perCategory, 110f);
                        EnsureStorageDefinition(building, CityResourceKind.Tools, perCategory, 110f);
                        EnsureStorageDefinition(building, CityResourceKind.Textile, perCategory, 110f);
                        break;
                    case BuildingArchetype.Market: state.marketServiceCapacity += capacity; break;
                    case BuildingArchetype.Blacksmith: state.toolProductionCapacity += capacity; break;
                    case BuildingArchetype.Barn: state.livestockCapacity += capacity; break;
                    case BuildingArchetype.Chapel: state.faithServiceCapacity += capacity; break;
                }
                if (building.archetype == BuildingArchetype.Market)
                {
                    var perStall = Mathf.Max(1, capacity / 3);
                    EnsureStorageDefinition(building, CityResourceKind.Food, perStall, 95f);
                    EnsureStorageDefinition(building, CityResourceKind.Tools, perStall, 95f);
                    EnsureStorageDefinition(building, CityResourceKind.Textile,
                        capacity - perStall * 2, 95f);
                }
            }
            RefreshResourceCapacities();
        }

        static void EnsureStorageDefinition(BuildingState building, CityResourceKind kind,
            int capacity, float serviceRadius)
        {
            building.localStocks ??= new List<StoredResourceState>();
            var stock = building.localStocks.Find(item => item.kind == kind);
            if (stock == null)
            {
                stock = new StoredResourceState { kind = kind };
                building.localStocks.Add(stock);
            }
            stock.capacity = capacity;
            stock.quantity = Mathf.Clamp(stock.quantity, 0, capacity);
            stock.reserved = Mathf.Clamp(stock.reserved, 0, stock.quantity);
            building.storageServiceRadius = Mathf.Max(building.storageServiceRadius, serviceRadius);
            building.localStocks.Sort((left, right) => left.kind.CompareTo(right.kind));
        }

        void TickStorageBuildings()
        {
            state.buildings.Sort((left, right) => left.id.CompareTo(right.id));
            foreach (var building in state.buildings)
            {
                if ((building.archetype != BuildingArchetype.Granary &&
                    building.archetype != BuildingArchetype.Warehouse) ||
                    building.phase != BuildingPhase.Complete || building.localStocks == null ||
                    building.localStocks.Count == 0 || !HasPresentStorageKeeper(building))
                    continue;
                foreach (var local in building.localStocks)
                {
                    var target = local.capacity / 2;
                    if (local.quantity < target && !HasOpenStorageTask(building.id, local.kind, true))
                    {
                        var global = GetResource(local.kind);
                        var available = global != null ? Mathf.Max(0, global.quantity - global.reserved) : 0;
                        var quantity = Mathf.Min(target - local.quantity, available);
                        if (quantity > 0)
                            EnqueueLogisticsTask(local.kind, LogisticsEndpointKind.GlobalStock, 0,
                                LogisticsEndpointKind.Building, building.id, quantity, 1);
                    }
                    else if (local.quantity > local.capacity * 3 / 4 &&
                        !HasOpenStorageTask(building.id, local.kind, false))
                    {
                        var global = GetResource(local.kind);
                        var free = global != null ? Mathf.Max(0, global.capacity - global.quantity) : 0;
                        var quantity = Mathf.Min(local.quantity - target, free);
                        if (quantity > 0)
                            EnqueueLogisticsTask(local.kind, LogisticsEndpointKind.Building, building.id,
                                LogisticsEndpointKind.GlobalStock, 0, quantity, 1);
                    }
                }
            }
        }

        bool HasPresentStorageKeeper(BuildingState building)
        {
            var job = building.archetype == BuildingArchetype.Granary
                ? VillagerJob.GranaryKeeper : VillagerJob.WarehouseKeeper;
            foreach (var villager in state.villagers)
                if (villager.job == job && villager.workplaceBuildingId == building.id &&
                    villager.isAtWork && villager.activity == VillagerActivity.WorkingJob)
                    return true;
            return false;
        }

        bool HasOpenStorageTask(int buildingId, CityResourceKind resource, bool incoming)
        {
            foreach (var task in state.logisticsTasks)
                if (task.resource == resource && task.status != LogisticsTaskStatus.Completed &&
                    task.status != LogisticsTaskStatus.Cancelled &&
                    (incoming
                        ? task.destinationKind == LogisticsEndpointKind.Building && task.destinationId == buildingId
                        : task.sourceKind == LogisticsEndpointKind.Building && task.sourceId == buildingId))
                    return true;
            return false;
        }

        static StoredResourceState FindLocalStock(BuildingState building, CityResourceKind resource) =>
            building?.localStocks?.Find(item => item.kind == resource);

        void TickMarkets()
        {
            foreach (var market in state.buildings)
            {
                if (market.archetype != BuildingArchetype.Market ||
                    market.phase != BuildingPhase.Complete)
                    continue;
                market.marketCoveredHouseholds = 0;
                foreach (var household in state.households)
                {
                    var home = FindBuilding(household.homeBuildingId);
                    var origin = home?.position.ToVector3() ?? Vector3.zero;
                    if (FindNearestMarket(origin)?.id == market.id)
                        market.marketCoveredHouseholds++;
                }
                var quantity = 0;
                var capacity = 0;
                foreach (var stall in market.localStocks)
                {
                    quantity += stall.quantity;
                    capacity += stall.capacity;
                    if (HasPresentMarketTrader(market) && stall.quantity < stall.capacity / 2 &&
                        !HasOpenStorageTask(market.id, stall.kind, true))
                        EnqueueMarketSupply(market, stall);
                }
                var fillPermille = capacity > 0 ? quantity * 1000 / capacity : 0;
                market.marketScarcityPermille = Mathf.Clamp(1000 - fillPermille, 0, 1000);
                market.marketPricePermille = 1000 + market.marketScarcityPermille;
                if (market.marketLastProcessedDay < state.calendar.absoluteDay)
                {
                    market.marketLastProcessedDay = state.calendar.absoluteDay;
                    if ((FindLocalStock(market, CityResourceKind.Food)?.quantity ?? 0) == 0)
                        market.marketShortageDays++;
                }
            }
        }

        void EnqueueMarketSupply(BuildingState market, StoredResourceState stall)
        {
            var target = stall.capacity / 2;
            var wanted = target - stall.quantity;
            if (wanted <= 0)
                return;
            var source = FindNearestStockedStorage(stall.kind, market.position.ToVector3());
            if (source != null)
            {
                var local = FindLocalStock(source, stall.kind);
                var quantity = Mathf.Min(wanted, local.quantity - local.reserved);
                if (quantity > 0)
                    EnqueueLogisticsTask(stall.kind, LogisticsEndpointKind.Building, source.id,
                        LogisticsEndpointKind.Building, market.id, quantity, 2);
                return;
            }
            var global = GetResource(stall.kind);
            var available = global != null ? Mathf.Max(0, global.quantity - global.reserved) : 0;
            if (available > 0)
                EnqueueLogisticsTask(stall.kind, LogisticsEndpointKind.GlobalStock, 0,
                    LogisticsEndpointKind.Building, market.id, Mathf.Min(wanted, available), 2);
        }

        BuildingState FindNearestStockedStorage(CityResourceKind resource, Vector3 origin)
        {
            BuildingState chosen = null;
            var chosenDistance = float.MaxValue;
            foreach (var building in state.buildings)
            {
                if (building.archetype != BuildingArchetype.Granary &&
                    building.archetype != BuildingArchetype.Warehouse)
                    continue;
                var local = FindLocalStock(building, resource);
                if (local == null || local.quantity <= local.reserved)
                    continue;
                var distance = PlanarSqrDistance(origin, building.position.ToVector3());
                if (distance > building.storageServiceRadius * building.storageServiceRadius)
                    continue;
                if (chosen == null || distance < chosenDistance - 0.0001f ||
                    Mathf.Abs(distance - chosenDistance) <= 0.0001f && building.id < chosen.id)
                {
                    chosen = building;
                    chosenDistance = distance;
                }
            }
            return chosen;
        }

        bool HasPresentMarketTrader(BuildingState market)
        {
            foreach (var villager in state.villagers)
                if (villager.job == VillagerJob.MarketTrader &&
                    villager.workplaceBuildingId == market.id && villager.isAtWork &&
                    villager.activity == VillagerActivity.WorkingJob)
                    return true;
            return false;
        }

        BuildingState FindNearestMarket(Vector3 origin)
        {
            BuildingState chosen = null;
            var chosenDistance = float.MaxValue;
            foreach (var building in state.buildings)
            {
                if (building.archetype != BuildingArchetype.Market ||
                    building.phase != BuildingPhase.Complete)
                    continue;
                var distance = PlanarSqrDistance(origin, building.position.ToVector3());
                if (distance > building.storageServiceRadius * building.storageServiceRadius)
                    continue;
                if (chosen == null || distance < chosenDistance - 0.0001f ||
                    Mathf.Abs(distance - chosenDistance) <= 0.0001f && building.id < chosen.id)
                {
                    chosen = building;
                    chosenDistance = distance;
                }
            }
            return chosen;
        }

        void RefreshEmployment(bool topologyChanged, bool preserveAssignments = true)
        {
            var currentDay = state.calendar.absoluteDay;
            var dayChanged = currentDay != employmentDay;
            if (!topologyChanged && !dayChanged)
                return;

            state.villagers.Sort((left, right) => left.id.CompareTo(right.id));
            var previous = new List<EmploymentRecord>(state.villagers.Count);
            foreach (var villager in state.villagers)
            {
                previous.Add(new EmploymentRecord(villager));
                if (dayChanged)
                {
                    villager.absentToday = IsDeterministicallyAbsent(villager.id, currentDay);
                    if (villager.absentToday && villager.job != VillagerJob.None)
                    {
                        villager.absenceCount++;
                        state.jobAbsences++;
                    }
                }
                villager.job = VillagerJob.None;
                villager.workplaceBuildingId = 0;
                villager.workplaceProductionSiteId = 0;
                villager.workplaceFoodSourceId = 0;
            }

            var slots = BuildEmploymentSlots();
            var previousUsed = new bool[previous.Count];
            foreach (var slot in slots)
            {
                VillagerState chosen = null;
                var absentSlot = false;
                for (var index = 0; preserveAssignments && index < previous.Count; index++)
                {
                    if (previousUsed[index] || state.villagers[index].job != VillagerJob.None ||
                        !previous[index].Matches(slot))
                        continue;
                    if (state.villagers[index].absentToday)
                    {
                        absentSlot = true;
                        previousUsed[index] = true;
                        continue;
                    }
                    chosen = state.villagers[index];
                    previousUsed[index] = true;
                    break;
                }
                if (chosen == null)
                {
                    foreach (var candidate in state.villagers)
                    {
                        if (candidate.job != VillagerJob.None || candidate.absentToday)
                            continue;
                        chosen = candidate;
                        break;
                    }
                }
                if (chosen == null)
                    continue;
                chosen.job = slot.job;
                chosen.workplaceBuildingId = slot.buildingId;
                chosen.workplaceProductionSiteId = slot.productionSiteId;
                chosen.workplaceFoodSourceId = slot.foodSourceId;
                chosen.shiftStartHour = 8f;
                chosen.shiftEndHour = 18f;
                if (dayChanged && absentSlot)
                    state.jobReplacements++;
            }

            for (var index = 0; index < state.villagers.Count; index++)
            {
                var villager = state.villagers[index];
                if (!previous[index].Matches(villager))
                    ResetForEmploymentChange(villager);
            }
            employmentDay = currentDay;
            state.employmentDay = currentDay;
            state.employmentRevision++;
            RefreshProductionAssignments();
        }

        List<EmploymentSlot> BuildEmploymentSlots()
        {
            var slots = new List<EmploymentSlot>();
            var foodSources = new List<FoodSourceState>(state.foodSources);
            foodSources.Sort((left, right) => left.id.CompareTo(right.id));
            foreach (var source in foodSources)
                if (source.accessible && source.remainingFood > 0)
                    for (var worker = 0; worker < source.maxWorkers; worker++)
                        slots.Add(new EmploymentSlot(source.kind == FoodSourceKind.HuntingGround
                            ? VillagerJob.Hunter : VillagerJob.Forager, 0, 0, source.id));
            var productionSites = new List<ProductionSiteState>(state.productionSites);
            productionSites.Sort((left, right) => left.id.CompareTo(right.id));
            foreach (var site in productionSites)
                if (site.kind == ProductionSiteKind.LumberCamp && site.remainingTimber > 0)
                    for (var worker = 0; worker < site.maxWorkers; worker++)
                        slots.Add(new EmploymentSlot(VillagerJob.Lumberjack, 0, site.id, 0));

            var buildings = new List<BuildingState>(state.buildings);
            buildings.Sort((left, right) =>
            {
                var priority = right.priority.CompareTo(left.priority);
                return priority != 0 ? priority : left.id.CompareTo(right.id);
            });
            foreach (var building in buildings)
            {
                if (!IsBuildingAccessible(building))
                    continue;
                var definition = catalog.Get(building.archetype);
                var job = building.phase == BuildingPhase.Complete
                    ? CivicJob(building.archetype)
                    : VillagerJob.Builder;
                if (job == VillagerJob.None)
                    continue;
                for (var worker = 0; worker < definition.maxWorkers; worker++)
                    slots.Add(new EmploymentSlot(job, building.id, 0, 0));
            }
            return slots;
        }

        static VillagerJob CivicJob(BuildingArchetype archetype) => archetype switch
        {
            BuildingArchetype.Granary => VillagerJob.GranaryKeeper,
            BuildingArchetype.Warehouse => VillagerJob.WarehouseKeeper,
            BuildingArchetype.Market => VillagerJob.MarketTrader,
            BuildingArchetype.Blacksmith => VillagerJob.Blacksmith,
            BuildingArchetype.Barn => VillagerJob.Stockman,
            BuildingArchetype.Chapel => VillagerJob.Cleric,
            _ => VillagerJob.None
        };

        bool IsDeterministicallyAbsent(int villagerId, int day)
        {
            unchecked
            {
                var value = state.seed * 486187739 + villagerId * 16777619 + day * 374761393;
                return (value & 0x7fffffff) % 19 == 0;
            }
        }

        bool IsWorkTime(VillagerState villager = null)
        {
            var hour = state.calendar.hour + state.calendar.minute / 60f;
            var start = villager != null ? villager.shiftStartHour : 8f;
            var end = villager != null ? villager.shiftEndHour : 18f;
            return hour >= start && hour < end;
        }

        void ApplyScheduleTransition(VillagerState villager)
        {
            if (villager.job == VillagerJob.None)
            {
                if (villager.activity != VillagerActivity.Idle)
                    ResetForEmploymentChange(villager);
                return;
            }
            if (villager.absentToday || !IsWorkTime(villager))
            {
                if (villager.job == VillagerJob.Builder &&
                    (villager.activity == VillagerActivity.GoingToSite ||
                     villager.activity == VillagerActivity.Building))
                    return;
                var awayFromHome = PlanarSqrDistance(villager.position.ToVector3(),
                    HomePosition(villager)) > 0.25f;
                if (villager.activity != VillagerActivity.GoingHome &&
                    (villager.activity != VillagerActivity.Idle || awayFromHome))
                    BeginGoingHome(villager);
                return;
            }

            if (villager.job == VillagerJob.Builder)
            {
                if (villager.activity == VillagerActivity.GoingHome ||
                    villager.activity == VillagerActivity.GoingToWork ||
                    villager.activity == VillagerActivity.WorkingJob)
                    SetIdle(villager);
                if (villager.logisticsTaskId == 0 && villager.targetBuildingId != 0 &&
                    villager.targetBuildingId != villager.workplaceBuildingId)
                    ResetForEmploymentChange(villager);
                return;
            }

            if ((villager.job == VillagerJob.GranaryKeeper ||
                villager.job == VillagerJob.WarehouseKeeper ||
                villager.job == VillagerJob.MarketTrader) && villager.logisticsTaskId != 0)
                return;

            if (villager.activity != VillagerActivity.GoingToWork &&
                villager.activity != VillagerActivity.WorkingJob)
                BeginGoingToWork(villager);
        }

        void BeginGoingToWork(VillagerState villager)
        {
            villager.isAtWork = false;
            villager.destination = CityPoint.From(WorkplacePosition(villager));
            villager.activity = VillagerActivity.GoingToWork;
            ClearNavigation(villager);
        }

        void AdvanceToWork(VillagerState villager, float deltaTime)
        {
            var target = WorkplacePosition(villager);
            if (!MoveTowards(villager, target, deltaTime))
                return;
            villager.activity = VillagerActivity.WorkingJob;
            villager.isAtWork = true;
        }

        void BeginGoingHome(VillagerState villager)
        {
            AbandonLogistics(villager);
            ReturnCarriedFoodSafely(villager);
            villager.targetBuildingId = 0;
            villager.isAtWork = false;
            villager.destination = CityPoint.From(HomePosition(villager));
            villager.activity = VillagerActivity.GoingHome;
            ClearNavigation(villager);
        }

        void AdvanceHome(VillagerState villager, float deltaTime)
        {
            if (MoveTowards(villager, HomePosition(villager), deltaTime))
                SetIdle(villager);
        }

        void GatherFood(VillagerState villager, float deltaTime)
        {
            var source = state.foodSources.Find(item => item.id == villager.workplaceFoodSourceId);
            if (source == null || !source.accessible || source.remainingFood <= 0)
            {
                villager.gatheringProgress = 0f;
                BeginGoingHome(villager);
                return;
            }
            villager.gatheringProgress += deltaTime;
            while (villager.gatheringProgress + 0.000001f >= source.workPerFood &&
                   source.remainingFood > 0 && villager.carryingFood < 2)
            {
                villager.gatheringProgress -= source.workPerFood;
                source.remainingFood--;
                villager.carryingFood++;
            }
            if (villager.carryingFood < 2 && source.remainingFood > 0)
                return;
            villager.activity = VillagerActivity.ReturningFood;
            villager.destination = CityPoint.From(StockPosition);
            villager.isAtWork = false;
            ClearNavigation(villager);
        }

        void ReturnFoodToStock(VillagerState villager, float deltaTime)
        {
            if (!MoveTowards(villager, StockPosition, deltaTime))
                return;
            var delivered = AddResource(CityResourceKind.Food, villager.carryingFood);
            var overflow = villager.carryingFood - delivered;
            var source = state.foodSources.Find(item => item.id == villager.workplaceFoodSourceId);
            if (overflow > 0 && source != null)
                source.remainingFood += overflow;
            villager.carryingFood = 0;
            if (source != null && source.accessible && source.remainingFood > 0 &&
                !villager.absentToday && IsWorkTime(villager))
                BeginGoingToWork(villager);
            else
            {
                if (source != null && source.remainingFood <= 0)
                    RefreshEmployment(true);
                BeginGoingHome(villager);
            }
        }

        Vector3 WorkplacePosition(VillagerState villager)
        {
            if (villager.workplaceBuildingId != 0)
            {
                var building = FindBuilding(villager.workplaceBuildingId);
                if (building != null)
                    return building.position.ToVector3();
            }
            if (villager.workplaceProductionSiteId != 0)
            {
                var site = state.productionSites.Find(item => item.id == villager.workplaceProductionSiteId);
                if (site != null)
                    return site.position.ToVector3();
            }
            if (villager.workplaceFoodSourceId != 0)
            {
                var source = state.foodSources.Find(item => item.id == villager.workplaceFoodSourceId);
                if (source != null)
                    return source.position.ToVector3();
            }
            return villager.position.ToVector3();
        }

        Vector3 HomePosition(VillagerState villager)
        {
            var household = FindHousehold(villager.householdId);
            var home = household != null ? FindBuilding(household.homeBuildingId) : null;
            return home != null && home.phase == BuildingPhase.Complete
                ? home.position.ToVector3()
                : villager.homePosition.ToVector3();
        }

        void ResetForEmploymentChange(VillagerState villager)
        {
            AbandonLogistics(villager);
            ReturnCarriedFoodSafely(villager);
            SetIdle(villager);
        }

        void ReturnCarriedFoodSafely(VillagerState villager)
        {
            if (villager.carryingFood <= 0)
                return;
            var accepted = AddResource(CityResourceKind.Food, villager.carryingFood);
            var overflow = villager.carryingFood - accepted;
            var source = state.foodSources.Find(item => item.id == villager.workplaceFoodSourceId);
            if (overflow > 0 && source != null)
                source.remainingFood += overflow;
            villager.carryingFood = 0;
        }

        static void ClearNavigation(VillagerState villager)
        {
            villager.navigationPath?.Clear();
            villager.navigationIndex = 0;
            villager.navigationRevision = 0;
        }

        readonly struct EmploymentSlot
        {
            public readonly VillagerJob job;
            public readonly int buildingId;
            public readonly int productionSiteId;
            public readonly int foodSourceId;

            public EmploymentSlot(VillagerJob job, int buildingId, int productionSiteId,
                int foodSourceId)
            {
                this.job = job;
                this.buildingId = buildingId;
                this.productionSiteId = productionSiteId;
                this.foodSourceId = foodSourceId;
            }
        }

        readonly struct EmploymentRecord
        {
            readonly VillagerJob job;
            readonly int buildingId;
            readonly int productionSiteId;
            readonly int foodSourceId;

            public EmploymentRecord(VillagerState villager)
            {
                job = villager.job;
                buildingId = villager.workplaceBuildingId;
                productionSiteId = villager.workplaceProductionSiteId;
                foodSourceId = villager.workplaceFoodSourceId;
            }

            public bool Matches(EmploymentSlot slot) => job == slot.job &&
                buildingId == slot.buildingId && productionSiteId == slot.productionSiteId &&
                foodSourceId == slot.foodSourceId;

            public bool Matches(VillagerState villager) => job == villager.job &&
                buildingId == villager.workplaceBuildingId &&
                productionSiteId == villager.workplaceProductionSiteId &&
                foodSourceId == villager.workplaceFoodSourceId;
        }

        void ReplanInaccessibleWorkers()
        {
            foreach (var villager in state.villagers)
            {
                var building = FindBuilding(villager.targetBuildingId);
                if (building == null || IsBuildingAccessible(building))
                    continue;
                AbandonLogistics(villager);
                SetIdle(villager);
            }
        }

        bool MoveTowards(VillagerState villager, Vector3 target, float deltaTime)
        {
            var pathInvalid = villager.navigationPath == null ||
                villager.navigationIndex >= villager.navigationPath.Count ||
                villager.navigationRevision != navigation.Revision ||
                PlanarSqrDistance(villager.navigationTarget.ToVector3(), target) > 0.01f;
            if (pathInvalid)
            {
                villager.navigationPath = navigation.FindPath(villager.position.ToVector3(), target);
                villager.navigationIndex = 0;
                villager.navigationTarget = CityPoint.From(target);
                villager.navigationRevision = navigation.Revision;
                state.navigationReplans++;
                if (villager.navigationPath == null || villager.navigationPath.Count == 0)
                {
                    state.navigationFailures++;
                    return false;
                }
            }

            var position = villager.position.ToVector3();
            var remaining = 3.5f * deltaTime;
            while (remaining > 0f && villager.navigationIndex < villager.navigationPath.Count)
            {
                var waypoint = villager.navigationPath[villager.navigationIndex].ToVector3();
                var distance = Vector3.Distance(position, waypoint);
                if (distance <= remaining + 0.0001f)
                {
                    position = waypoint;
                    remaining -= distance;
                    villager.navigationIndex++;
                }
                else
                {
                    position = Vector3.MoveTowards(position, waypoint, remaining);
                    remaining = 0f;
                }
            }
            villager.position = CityPoint.From(position);
            return villager.navigationIndex >= villager.navigationPath.Count;
        }

        void RebuildNavigation()
        {
            navigation.Rebuild(state, catalog);
        }

        bool TryAssignLogisticsTask(VillagerState villager, int endpointBuildingId = 0)
        {
            LogisticsTaskState chosen = null;
            foreach (var task in state.logisticsTasks)
            {
                if (task.status == LogisticsTaskStatus.Completed ||
                    task.status == LogisticsTaskStatus.Cancelled ||
                    !EndpointExists(task.sourceKind, task.sourceId) ||
                    !EndpointExists(task.destinationKind, task.destinationId))
                    continue;
                if (endpointBuildingId != 0 &&
                    !(task.sourceKind == LogisticsEndpointKind.Building &&
                        task.sourceId == endpointBuildingId) &&
                    !(task.destinationKind == LogisticsEndpointKind.Building &&
                        task.destinationId == endpointBuildingId))
                    continue;
                var outstanding = task.requestedQuantity - task.deliveredQuantity -
                    task.reservedQuantity - task.inTransitQuantity;
                if (outstanding <= 0 || AvailableAtSource(task) <= 0)
                    continue;
                if (chosen == null || task.priority > chosen.priority ||
                    task.priority == chosen.priority && task.id < chosen.id)
                    chosen = task;
            }
            if (chosen == null)
                return false;
            var quantity = Mathf.Min(4,
                chosen.requestedQuantity - chosen.deliveredQuantity -
                chosen.reservedQuantity - chosen.inTransitQuantity,
                AvailableAtSource(chosen));
            if (quantity <= 0)
                return false;
            ReserveAtSource(chosen, quantity);
            chosen.reservedQuantity += quantity;
            chosen.status = LogisticsTaskStatus.Active;
            villager.logisticsTaskId = chosen.id;
            villager.targetBuildingId = chosen.destinationKind == LogisticsEndpointKind.Building
                ? chosen.destinationId
                : 0;
            villager.reservedWood = quantity;
            villager.reservedResource = chosen.resource;
            villager.destination = CityPoint.From(EndpointPosition(chosen.sourceKind, chosen.sourceId));
            villager.activity = VillagerActivity.GoingToStock;
            return true;
        }

        static ConstructionMaterialState MissingConstructionMaterial(BuildingState building)
        {
            if (building?.constructionMaterials == null)
                return null;
            foreach (var material in building.constructionMaterials)
                if (material != null && material.phase == building.phase &&
                    material.delivered < material.required)
                    return material;
            return null;
        }

        LogisticsTaskState FindOrCreateConstructionTask(BuildingState building,
            ConstructionMaterialState material)
        {
            foreach (var existing in state.logisticsTasks)
                if (existing.resource == material.resource &&
                    existing.destinationKind == LogisticsEndpointKind.Building &&
                    existing.destinationId == building.id &&
                    existing.status != LogisticsTaskStatus.Cancelled &&
                    existing.status != LogisticsTaskStatus.Completed)
                {
                    existing.priority = building.priority;
                    return existing;
                }
            var id = EnqueueLogisticsTask(material.resource,
                LogisticsEndpointKind.GlobalStock, 0,
                LogisticsEndpointKind.Building, building.id,
                material.required, building.priority);
            var task = FindLogisticsTask(id);
            if (task != null)
                task.deliveredQuantity = material.delivered;
            return task;
        }

        LogisticsTaskState FindLogisticsTask(int id) =>
            id == 0 ? null : state.logisticsTasks.Find(item => item.id == id);

        bool EndpointExists(LogisticsEndpointKind kind, int id) => kind switch
        {
            LogisticsEndpointKind.GlobalStock => id == 0,
            LogisticsEndpointKind.Building => FindBuilding(id) is BuildingState building &&
                IsBuildingAccessible(building),
            LogisticsEndpointKind.ProductionSite =>
                state.productionSites.Exists(item => item.id == id),
            _ => false
        };

        Vector3 EndpointPosition(LogisticsEndpointKind kind, int id) => kind switch
        {
            LogisticsEndpointKind.GlobalStock => StockPosition,
            LogisticsEndpointKind.Building => FindBuilding(id)?.position.ToVector3() ?? Vector3.zero,
            LogisticsEndpointKind.ProductionSite =>
                state.productionSites.Find(item => item.id == id)?.position.ToVector3() ?? Vector3.zero,
            _ => Vector3.zero
        };

        int AvailableAtSource(LogisticsTaskState task) => task.sourceKind switch
        {
            LogisticsEndpointKind.GlobalStock => GetResource(task.resource) is ResourceStockState stock
                ? Mathf.Max(0, stock.quantity - stock.reserved) : 0,
            LogisticsEndpointKind.Building => FindLocalStock(FindBuilding(task.sourceId), task.resource)
                is StoredResourceState local ? Mathf.Max(0, local.quantity - local.reserved) : 0,
            LogisticsEndpointKind.ProductionSite => AvailableAtProductionSite(task),
            _ => 0
        };

        int AvailableAtProductionSite(LogisticsTaskState task)
        {
            var site = state.productionSites.Find(item => item.id == task.sourceId);
            if (site == null)
                return 0;
            if (site.kind == ProductionSiteKind.LumberCamp)
                return task.resource == CityResourceKind.Wood
                    ? Mathf.Max(0, site.storedWood - site.reservedWood) : 0;
            return productionRecipes.TryGet(site.kind, out var recipe) && recipe.output == task.resource
                ? Mathf.Max(0, site.outputStored - site.outputReserved) : 0;
        }

        void ReserveAtSource(LogisticsTaskState task, int quantity)
        {
            if (task.sourceKind == LogisticsEndpointKind.GlobalStock)
                TryReserveResource(task.resource, quantity);
            else if (task.sourceKind == LogisticsEndpointKind.Building)
                FindLocalStock(FindBuilding(task.sourceId), task.resource).reserved += quantity;
            else if (task.sourceKind == LogisticsEndpointKind.ProductionSite)
            {
                var site = state.productionSites.Find(item => item.id == task.sourceId);
                if (site.kind == ProductionSiteKind.LumberCamp)
                    site.reservedWood += quantity;
                else
                    site.outputReserved += quantity;
            }
        }

        bool TakeReservedFromSource(LogisticsTaskState task, int quantity)
        {
            if (task.sourceKind == LogisticsEndpointKind.GlobalStock)
            {
                return TryConsumeReservedResource(task.resource, quantity);
            }
            if (task.sourceKind == LogisticsEndpointKind.Building)
            {
                var local = FindLocalStock(FindBuilding(task.sourceId), task.resource);
                if (local == null || local.quantity < quantity || local.reserved < quantity)
                    return false;
                local.quantity -= quantity;
                local.reserved -= quantity;
                return true;
            }
            var site = task.sourceKind == LogisticsEndpointKind.ProductionSite
                ? state.productionSites.Find(item => item.id == task.sourceId)
                : null;
            if (site == null)
                return false;
            if (site.kind == ProductionSiteKind.LumberCamp)
            {
                if (task.resource != CityResourceKind.Wood || site.storedWood < quantity)
                    return false;
                site.storedWood -= quantity;
                site.reservedWood = Mathf.Max(0, site.reservedWood - quantity);
                return true;
            }
            if (!productionRecipes.TryGet(site.kind, out var recipe) ||
                recipe.output != task.resource || site.outputStored < quantity)
                return false;
            site.outputStored -= quantity;
            site.outputReserved = Mathf.Max(0, site.outputReserved - quantity);
            return true;
        }

        void DeliverToEndpoint(LogisticsTaskState task, int quantity)
        {
            if (task.destinationKind == LogisticsEndpointKind.Building)
            {
                var building = FindBuilding(task.destinationId);
                var local = FindLocalStock(building, task.resource);
                if (building.phase == BuildingPhase.Complete && local != null)
                    local.quantity = Mathf.Min(local.capacity, local.quantity + quantity);
                else
                {
                    var material = MissingConstructionMaterial(building);
                    if (material != null && material.resource == task.resource)
                    {
                        var delivered = Mathf.Min(quantity, material.required - material.delivered);
                        material.delivered += delivered;
                        if (task.resource == CityResourceKind.Wood)
                            building.deliveredWood += delivered;
                    }
                    else if (task.resource == CityResourceKind.Wood)
                        building.deliveredWood += quantity;
                }
            }
            else if (task.destinationKind == LogisticsEndpointKind.ProductionSite)
            {
                var site = state.productionSites.Find(item => item.id == task.destinationId);
                if (site.kind == ProductionSiteKind.LumberCamp)
                    site.storedWood += quantity;
                else if (productionRecipes.TryGet(site.kind, out var recipe))
                {
                    if (recipe.inputA == task.resource)
                        site.inputAStored += quantity;
                    else if (recipe.inputB == task.resource)
                        site.inputBStored += quantity;
                }
            }
            else if (task.destinationKind == LogisticsEndpointKind.GlobalStock)
                AddResource(task.resource, quantity);
        }

        void CancelTasksForEndpoint(LogisticsEndpointKind kind, int id)
        {
            foreach (var task in state.logisticsTasks)
            {
                if (task.status == LogisticsTaskStatus.Completed ||
                    task.status == LogisticsTaskStatus.Cancelled ||
                    !((task.sourceKind == kind && task.sourceId == id) ||
                      (task.destinationKind == kind && task.destinationId == id)))
                    continue;
                foreach (var villager in state.villagers)
                    if (villager.logisticsTaskId == task.id)
                    {
                        AbandonLogistics(villager, task.sourceKind == kind && task.sourceId == id);
                        SetIdle(villager);
                    }
                task.status = LogisticsTaskStatus.Cancelled;
                task.reservedQuantity = 0;
                task.inTransitQuantity = 0;
                state.logisticsRevision++;
            }
        }

        void AbandonLogistics(VillagerState villager, bool forceGlobalReturn = false)
        {
            var task = FindLogisticsTask(villager.logisticsTaskId);
            ReleaseReservation(villager);
            if (villager.carryingWood > 0)
            {
                if (!forceGlobalReturn && task != null && task.sourceKind == LogisticsEndpointKind.ProductionSite)
                    ReturnCargoToProductionSite(task, villager.carryingWood);
                else if (!forceGlobalReturn && task != null && task.sourceKind == LogisticsEndpointKind.Building)
                {
                    var local = FindLocalStock(FindBuilding(task.sourceId), task.resource);
                    if (local != null)
                        local.quantity = Mathf.Min(local.capacity, local.quantity + villager.carryingWood);
                    else
                        AddResource(task.resource, villager.carryingWood);
                }
                else if (task != null)
                    AddResource(task.resource, villager.carryingWood);
                else
                    AddResource(villager.carryingResource == 0 ? CityResourceKind.Wood : villager.carryingResource,
                        villager.carryingWood);
                if (task != null)
                    task.inTransitQuantity = Mathf.Max(0, task.inTransitQuantity - villager.carryingWood);
                villager.carryingWood = 0;
                villager.carryingResource = 0;
            }
            if (task != null && task.status == LogisticsTaskStatus.Active &&
                task.reservedQuantity == 0 && task.inTransitQuantity == 0 &&
                task.deliveredQuantity < task.requestedQuantity)
                task.status = LogisticsTaskStatus.Pending;
            villager.logisticsTaskId = 0;
        }

        void ReturnCargoToProductionSite(LogisticsTaskState task, int quantity)
        {
            var site = state.productionSites.Find(item => item.id == task.sourceId);
            if (site == null)
            {
                AddResource(task.resource, quantity);
                return;
            }
            if (site.kind == ProductionSiteKind.LumberCamp)
                site.storedWood += quantity;
            else
                site.outputStored += quantity;
        }

        void ReleaseReservation(VillagerState villager)
        {
            if (villager.reservedWood <= 0)
                return;
            var task = FindLogisticsTask(villager.logisticsTaskId);
            if (task != null)
            {
                task.reservedQuantity = Mathf.Max(0, task.reservedQuantity - villager.reservedWood);
                if (task.sourceKind == LogisticsEndpointKind.GlobalStock)
                    ReleaseResourceReservation(task.resource, villager.reservedWood);
                else if (task.sourceKind == LogisticsEndpointKind.Building)
                {
                    var local = FindLocalStock(FindBuilding(task.sourceId), task.resource);
                    if (local != null)
                        local.reserved = Mathf.Max(0, local.reserved - villager.reservedWood);
                }
                else if (task.sourceKind == LogisticsEndpointKind.ProductionSite &&
                    state.productionSites.Find(item => item.id == task.sourceId) is ProductionSiteState site)
                {
                    if (site.kind == ProductionSiteKind.LumberCamp)
                        site.reservedWood = Mathf.Max(0, site.reservedWood - villager.reservedWood);
                    else
                        site.outputReserved = Mathf.Max(0, site.outputReserved - villager.reservedWood);
                }
            }
            else
                ReleaseResourceReservation(villager.reservedResource == 0
                    ? CityResourceKind.Wood : villager.reservedResource, villager.reservedWood);
            villager.reservedWood = 0;
            villager.reservedResource = 0;
        }

        bool CanReceiveAtBuilding(int buildingId, CityResourceKind resource)
        {
            var building = FindBuilding(buildingId);
            if (building == null)
                return false;
            if (building.phase != BuildingPhase.Complete)
                return building.constructionMaterials != null &&
                    building.constructionMaterials.Exists(item => item != null &&
                        item.phase == building.phase && item.resource == resource &&
                        item.delivered < item.required);
            var stock = FindLocalStock(building, resource);
            return stock != null && stock.quantity < stock.capacity;
        }

        static void SetIdle(VillagerState villager)
        {
            villager.activity = VillagerActivity.Idle;
            villager.targetBuildingId = 0;
            villager.logisticsTaskId = 0;
            villager.destination = villager.position;
            villager.navigationPath?.Clear();
            villager.navigationIndex = 0;
            villager.navigationRevision = 0;
        }

        int WoodInTransit(int buildingId)
        {
            var count = 0;
            foreach (var villager in state.villagers)
                if (villager.targetBuildingId == buildingId)
                    count += villager.carryingWood + villager.reservedWood;
            return count;
        }

        bool IsBuildingAccessible(BuildingState building)
        {
            if (building.parcelId == 0)
                return true;
            var parcel = FindParcel(building.parcelId);
            return parcel != null && parcel.accessible;
        }

        float ParcelFacingYaw(ParcelState parcel)
        {
            var road = FindRoad(parcel.roadId);
            if (road == null)
                return 0f;
            var start = road.start.ToVector3();
            var segment = road.end.ToVector3() - start;
            var lengthSquared = segment.sqrMagnitude;
            if (lengthSquared <= 0.0001f)
                return 0f;
            var center = parcel.center.ToVector3();
            var t = Mathf.Clamp01(Vector3.Dot(center - start, segment) / lengthSquared);
            var facing = (start + segment * t - center).normalized;
            return Mathf.Atan2(facing.x, facing.z) * Mathf.Rad2Deg;
        }

        void UpdateParcelEvolution()
        {
            var navigationChanged = false;
            foreach (var parcel in state.parcels)
            {
                var building = FindBuilding(parcel.buildingId);
                var household = FindHousehold(parcel.householdId);
                var completedHome = building != null &&
                    building.archetype == BuildingArchetype.Residence &&
                    building.phase == BuildingPhase.Complete;
                var desiredExtension = completedHome && household != null
                    ? household.level == HouseholdLevel.Prosperous ? 2
                    : household.level == HouseholdLevel.Established ? 1 : 0
                    : 0;
                desiredExtension = Mathf.Clamp(desiredExtension, 0, parcel.extensionCapacity);
                if (parcel.extensionLevel != desiredExtension)
                {
                    parcel.extensionLevel = desiredExtension;
                    navigationChanged = true;
                }
                parcel.gardenActive = completedHome && parcel.hasGarden;
            }
            if (navigationChanged)
                RebuildNavigation();
        }

        RoadState FindRoad(int id) => state.roads.Find(item => item.id == id);
        ParcelState FindParcel(int id) => state.parcels.Find(item => item.id == id);
        BuildingState FindBuilding(int id) => state.buildings.Find(item => item.id == id);
        HouseholdState FindHousehold(int id) => state.households.Find(item => item.id == id);

        static float PlanarDistance(Vector3 left, Vector3 right)
        {
            var deltaX = left.x - right.x;
            var deltaZ = left.z - right.z;
            return Mathf.Sqrt(deltaX * deltaX + deltaZ * deltaZ);
        }

        static float PlanarSqrDistance(Vector3 left, Vector3 right)
        {
            var deltaX = left.x - right.x;
            var deltaZ = left.z - right.z;
            return deltaX * deltaX + deltaZ * deltaZ;
        }

        sealed class FlatParcelTerrainSampler : IParcelTerrainSampler
        {
            public static readonly FlatParcelTerrainSampler Instance = new FlatParcelTerrainSampler();

            FlatParcelTerrainSampler() { }

            public float SampleHeight(Vector3 worldPosition) => 0f;
        }

        static bool InsideMap(Vector3 point) =>
            Mathf.Abs(point.x) <= MapHalfExtent - 4f && Mathf.Abs(point.z) <= MapHalfExtent - 4f;

        void InitializeResourceStocks()
        {
            var hadPersistedStocks = state.resources.Count > 0;
            foreach (var definition in resourceRegistry.Definitions)
            {
                var stock = state.resources.Find(item => item.kind == definition.kind);
                if (stock == null)
                {
                    stock = new ResourceStockState
                    {
                        kind = definition.kind,
                        capacity = definition.defaultCapacity
                    };
                    if (definition.kind == CityResourceKind.Wood)
                    {
                        stock.quantity = state.stockWood;
                        stock.reserved = state.reservedWood;
                    }
                    state.resources.Add(stock);
                }
                stock.capacity = Mathf.Max(stock.capacity, definition.defaultCapacity);
                stock.quantity = Mathf.Clamp(stock.quantity, 0, stock.capacity);
                stock.reserved = Mathf.Clamp(stock.reserved, 0, stock.quantity);
            }
            state.resources.Sort((left, right) => left.kind.CompareTo(right.kind));
            if (hadPersistedStocks)
            {
                var wood = GetResource(CityResourceKind.Wood);
                state.stockWood = wood.quantity;
                state.reservedWood = wood.reserved;
            }
            else
                SyncWoodResourceFromLegacy();
            if (state.resourceLossDay < 0)
                state.resourceLossDay = state.calendar.absoluteDay;
        }

        void RefreshResourceCapacities()
        {
            foreach (var definition in resourceRegistry.Definitions)
            {
                var stock = GetResource(definition.kind);
                if (stock == null)
                    continue;
                stock.capacity = Mathf.Max(definition.defaultCapacity, stock.quantity);
            }
        }

        void ApplyDailyResourceLosses()
        {
            while (state.resourceLossDay < state.calendar.absoluteDay)
            {
                state.resourceLossDay++;
                foreach (var definition in resourceRegistry.Definitions)
                {
                    if (definition.dailyLossPermille <= 0)
                        continue;
                    var stock = GetResource(definition.kind);
                    var exposed = Mathf.Max(0, stock.quantity - stock.reserved);
                    var scaledLoss = exposed * definition.dailyLossPermille +
                        stock.lossRemainderPermille;
                    var lost = scaledLoss / 1000;
                    stock.lossRemainderPermille = scaledLoss % 1000;
                    stock.quantity = Mathf.Max(stock.reserved, stock.quantity - lost);
                    stock.totalLost += lost;
                }
                ConsumeDailyFood();
                UpdateParcelEvolution();
                UpdateDailyWeather();
                TickAgricultureDay();
                SettleTradeOrders();
            }
        }

        void TickTradeMerchants()
        {
            var routeStart = new Vector3(MapHalfExtent, 0f, -MapHalfExtent);
            foreach (var order in state.tradeOrders)
            {
                if (order.status != TradeOrderStatus.Traveling)
                    continue;
                var duration = Mathf.Max(1, order.deliveryDay - order.createdDay);
                var progress = (state.calendar.absoluteDay - order.createdDay +
                    (state.calendar.hour * 60 + state.calendar.minute) / 1440f) / duration;
                order.travelProgress = Mathf.Clamp01(progress);
                order.merchantPosition = CityPoint.From(Vector3.Lerp(routeStart,
                    StockPosition, order.travelProgress));
            }
        }

        void SettleTradeOrders()
        {
            state.tradeOrders.Sort((left, right) => left.id.CompareTo(right.id));
            foreach (var order in state.tradeOrders)
            {
                if (order.status != TradeOrderStatus.Traveling ||
                    order.deliveryDay > state.calendar.absoluteDay)
                    continue;
                if (order.direction == TradeDirection.Export)
                {
                    if (!TryConsumeReservedResource(order.resource, order.requestedQuantity))
                    {
                        order.status = TradeOrderStatus.Cancelled;
                        continue;
                    }
                    order.deliveredQuantity = order.requestedQuantity;
                    order.balanceDelta = order.unitPrice * order.deliveredQuantity - order.feeCoins;
                    state.treasuryCoins += order.balanceDelta;
                }
                else
                {
                    var reservedCost = order.unitPrice * order.requestedQuantity + order.feeCoins;
                    state.reservedTradeCoins = Mathf.Max(0, state.reservedTradeCoins - reservedCost);
                    order.deliveredQuantity = AddResource(order.resource, order.requestedQuantity);
                    var actualGross = order.unitPrice * order.deliveredQuantity;
                    var actualFee = order.deliveredQuantity > 0
                        ? Mathf.Max(1, (actualGross + 9) / 10) : 0;
                    order.balanceDelta = -(actualGross + actualFee);
                    state.treasuryCoins += order.balanceDelta;
                }
                order.travelProgress = 1f;
                order.merchantPosition = CityPoint.From(StockPosition);
                order.status = TradeOrderStatus.Completed;
                state.tradeRevision++;
            }
        }

        static int TradeUnitPrice(CityResourceKind resource) => resource switch
        {
            CityResourceKind.Wood => 2,
            CityResourceKind.Planks => 4,
            CityResourceKind.Stone => 3,
            CityResourceKind.Food => 2,
            CityResourceKind.Tools => 8,
            CityResourceKind.Textile => 7,
            _ => 1
        };

        void UpdateDailyWeather()
        {
            if (state.weatherDay == state.calendar.absoluteDay)
                return;
            state.weatherDay = state.calendar.absoluteDay;
            unchecked
            {
                var value = (state.seed * 1103515245 + state.weatherDay * 12345) & 0x7fffffff;
                var roll = value % 100;
                state.dailyWeather = state.calendar.season == CitySeason.Winter && roll < 25
                    ? CityWeather.Frost
                    : roll < 25 ? CityWeather.Rain
                    : roll >= 92 ? CityWeather.Drought
                    : CityWeather.Clear;
            }
        }

        void TickAgricultureDay()
        {
            state.fields.Sort((left, right) => left.id.CompareTo(right.id));
            foreach (var field in state.fields)
            {
                if (field.lastProcessedDay >= state.calendar.absoluteDay)
                    continue;
                field.lastProcessedDay = state.calendar.absoluteDay;
                switch (field.phase)
                {
                    case FieldPhase.Fallow:
                        field.fertilityPermille = Mathf.Min(1000, field.fertilityPermille + 5);
                        if (state.calendar.season == CitySeason.Spring)
                        {
                            field.phase = FieldPhase.Plowing;
                            field.workDays = 0;
                        }
                        break;
                    case FieldPhase.Plowing:
                        if (++field.workDays >= 3)
                        {
                            field.phase = FieldPhase.Sown;
                            field.workDays = 0;
                        }
                        break;
                    case FieldPhase.Sown:
                        field.phase = FieldPhase.Growing;
                        field.growthPoints = 0;
                        break;
                    case FieldPhase.Growing:
                        var growth = state.dailyWeather == CityWeather.Rain ? 2 :
                            state.dailyWeather == CityWeather.Drought || state.dailyWeather == CityWeather.Frost ? 0 : 1;
                        field.growthPoints += growth;
                        field.fertilityPermille = Mathf.Max(0, field.fertilityPermille - 2);
                        if (field.growthPoints >= 20)
                            field.phase = FieldPhase.ReadyToHarvest;
                        break;
                    case FieldPhase.ReadyToHarvest:
                        var potentialYield = Mathf.Max(1, field.fertilityPermille / 50);
                        field.lastYield = AddResource(CityResourceKind.Food, potentialYield);
                        field.totalHarvested += field.lastYield;
                        field.phase = FieldPhase.Harvested;
                        break;
                    case FieldPhase.Harvested:
                        field.phase = FieldPhase.Fallow;
                        field.workDays = 0;
                        field.growthPoints = 0;
                        break;
                }
            }
        }

        void ConsumeDailyFood()
        {
            var food = GetResource(CityResourceKind.Food);
            state.households.Sort((left, right) => left.id.CompareTo(right.id));
            foreach (var household in state.households)
            {
                var origin = Vector3.zero;
                var home = FindBuilding(household.homeBuildingId);
                if (home != null)
                    origin = home.position.ToVector3();
                household.preferredFoodSourceId = NearestAccessibleFoodSource(origin)?.id ?? 0;
                var market = FindNearestMarket(origin);
                household.marketBuildingId = market?.id ?? 0;
                household.marketCovered = market != null;
                var required = Mathf.Max(1, (household.memberCount + 2) / 3);
                var marketFood = market != null
                    ? FindLocalStock(market, CityResourceKind.Food) : null;
                var available = marketFood != null
                    ? Mathf.Max(0, marketFood.quantity - marketFood.reserved)
                    : Mathf.Max(0, food.quantity - food.reserved);
                var consumed = Mathf.Min(required, available);
                if (marketFood != null)
                    marketFood.quantity -= consumed;
                else
                    food.quantity -= consumed;
                household.foodConsumedTotal += consumed;
                household.hungry = consumed < required;
                if (household.hungry)
                    household.foodShortageDays++;

                if (state.calendar.absoluteDay % 30 == 0)
                {
                    household.fuelSatisfied = ConsumeHouseholdResource(
                        CityResourceKind.Wood, 1, origin, null);
                    if (!household.fuelSatisfied)
                        household.fuelShortageDays++;
                }
                if (state.calendar.absoluteDay % 30 == 0)
                {
                    household.clothingSatisfied = ConsumeHouseholdResource(
                        CityResourceKind.Textile, 1, origin, market);
                    if (!household.clothingSatisfied)
                        household.clothingShortageDays++;
                }
                if (state.calendar.absoluteDay % 15 == 0)
                {
                    household.toolsSatisfied = ConsumeHouseholdResource(
                        CityResourceKind.Tools, 1, origin, market);
                    if (!household.toolsSatisfied)
                        household.toolShortageDays++;
                }

                var housed = home != null && home.phase == BuildingPhase.Complete;
                household.satisfactionPermille =
                    (household.hungry ? 0 : 350) +
                    (housed ? 250 : 0) +
                    (household.fuelSatisfied ? 150 : 0) +
                    (household.clothingSatisfied ? 125 : 0) +
                    (household.toolsSatisfied ? 125 : 0);
                household.level = household.satisfactionPermille >= 850
                    ? HouseholdLevel.Prosperous
                    : household.satisfactionPermille >= 650 ? HouseholdLevel.Established
                    : household.satisfactionPermille >= 400 ? HouseholdLevel.Basic
                    : HouseholdLevel.Destitute;
            }
        }

        bool ConsumeHouseholdResource(CityResourceKind resource, int quantity,
            Vector3 origin, BuildingState market)
        {
            if ((resource == CityResourceKind.Tools || resource == CityResourceKind.Textile) &&
                market != null)
            {
                var stall = FindLocalStock(market, resource);
                if (stall == null || stall.quantity - stall.reserved < quantity)
                    return false;
                stall.quantity -= quantity;
                return true;
            }
            var storage = FindNearestStockedStorage(resource, origin);
            var local = FindLocalStock(storage, resource);
            if (local != null && local.quantity - local.reserved >= quantity)
            {
                local.quantity -= quantity;
                return true;
            }
            var global = GetResource(resource);
            if (global == null || global.quantity - global.reserved < quantity)
                return false;
            global.quantity -= quantity;
            if (resource == CityResourceKind.Wood)
                state.stockWood = global.quantity;
            return true;
        }

        FoodSourceState NearestAccessibleFoodSource(Vector3 origin)
        {
            FoodSourceState chosen = null;
            var chosenDistance = float.MaxValue;
            foreach (var source in state.foodSources)
            {
                if (!source.accessible || source.remainingFood <= 0)
                    continue;
                var distance = PlanarSqrDistance(origin, source.position.ToVector3());
                if (chosen == null || distance < chosenDistance - 0.0001f ||
                    Mathf.Abs(distance - chosenDistance) <= 0.0001f && source.id < chosen.id)
                {
                    chosen = source;
                    chosenDistance = distance;
                }
            }
            return chosen;
        }

        void SyncWoodResourceFromLegacy()
        {
            var wood = GetResource(CityResourceKind.Wood);
            if (wood == null)
                return;
            wood.quantity = Mathf.Clamp(state.stockWood, 0, wood.capacity);
            wood.reserved = Mathf.Clamp(state.reservedWood, 0, wood.quantity);
        }

        void UpdateCalendar()
        {
            var absoluteDay = Mathf.Max(0, Mathf.FloorToInt(state.elapsedSeconds / SecondsPerGameDay));
            var secondsInDay = Mathf.Clamp(state.elapsedSeconds - absoluteDay * SecondsPerGameDay,
                0f, SecondsPerGameDay - 0.0001f);
            var minuteOfDay = Mathf.Clamp(Mathf.FloorToInt(
                secondsInDay / SecondsPerGameDay * 24f * 60f + 0.0001f), 0, 1439);
            var dayOfYear = absoluteDay % (DaysPerMonth * MonthsPerYear);
            state.calendar.absoluteDay = absoluteDay;
            state.calendar.year = absoluteDay / (DaysPerMonth * MonthsPerYear) + 1;
            state.calendar.month = dayOfYear / DaysPerMonth + 1;
            state.calendar.day = dayOfYear % DaysPerMonth + 1;
            state.calendar.hour = minuteOfDay / 60;
            state.calendar.minute = minuteOfDay % 60;
            state.calendar.season = state.calendar.month switch
            {
                <= 3 => CitySeason.Winter,
                <= 6 => CitySeason.Spring,
                <= 9 => CitySeason.Summer,
                _ => CitySeason.Autumn
            };
        }

        void TriggerScheduledEvents()
        {
            foreach (var scheduled in state.scheduledEvents)
            {
                if (scheduled.status != ScheduledCityEventStatus.Pending ||
                    scheduled.triggerAtElapsedSeconds > state.elapsedSeconds + 0.00001f)
                    continue;
                scheduled.status = ScheduledCityEventStatus.Triggered;
                scheduled.triggeredAtElapsedSeconds = state.elapsedSeconds;
            }
        }

        static float NormalizeSpeed(float speed, bool allowPause)
        {
            if (allowPause && speed <= 0f)
                return 0f;
            return speed <= 1f ? 1f : speed <= 2f ? 2f : 4f;
        }

        static int NextId<T>(List<T> items, Func<T, int> selector)
        {
            var max = 0;
            foreach (var item in items)
                max = Mathf.Max(max, selector(item));
            return max + 1;
        }
    }
}
