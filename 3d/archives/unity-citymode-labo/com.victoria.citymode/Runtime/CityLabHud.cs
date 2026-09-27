using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UIElements;

namespace Victoria.CityMode
{
    public sealed class CityLabHud : MonoBehaviour
    {
        static readonly Color Obsidian = new Color(0.028f, 0.024f, 0.021f, 0.94f);
        static readonly Color CharcoalRaised = new Color(0.105f, 0.075f, 0.050f, 0.98f);
        static readonly Color Bronze = new Color(0.62f, 0.42f, 0.20f, 1f);
        static readonly Color BronzeBright = new Color(0.88f, 0.68f, 0.36f, 1f);
        static readonly Color BronzeMuted = new Color(0.37f, 0.25f, 0.14f, 1f);
        static readonly Color Parchment = new Color(0.93f, 0.86f, 0.72f, 1f);
        static readonly Color ParchmentMuted = new Color(0.67f, 0.61f, 0.51f, 1f);
        static readonly Color Success = new Color(0.55f, 0.72f, 0.43f, 1f);
        static readonly Color Warning = new Color(0.94f, 0.40f, 0.27f, 1f);
        static readonly BuildingArchetype[] CivicArchetypes =
        {
            BuildingArchetype.Granary, BuildingArchetype.Warehouse, BuildingArchetype.Market,
            BuildingArchetype.Blacksmith, BuildingArchetype.Barn, BuildingArchetype.Chapel
        };

        CityLabGame game;
        CityBuildController tools;
        UIDocument document;
        PanelSettings runtimePanel;
        ThemeStyleSheet runtimeTheme;
        bool ownsRuntimePanel;

        Label resources;
        Label population;
        Label construction;
        Label services;
        Label clock;
        Label prompt;
        Label message;
        Label selection;
        Label selectionState;
        Label selectionDetails;
        Label help;
        VisualElement root;
        VisualElement topBar;
        VisualElement brandBlock;
        VisualElement statusStrip;
        VisualElement contentRow;
        VisualElement toolPalette;
        VisualElement toolButtons;
        VisualElement constructionCard;
        VisualElement priorityControls;
        VisualElement footerBar;
        Button routeButton;
        Button zoneButton;
        Button lumberCampButton;
        DropdownField civicBuildingSelector;
        Button civicBuildingButton;
        Button pauseButton;
        Button speedOneButton;
        Button speedTwoButton;
        Button speedFourButton;
        Button lowPriorityButton;
        Button normalPriorityButton;
        Button highPriorityButton;
        CitySnapshot pendingSnapshot;
        string lastMessage = "";
        bool lastMessageSuccess = true;

        public void Initialize(CityLabGame owner, CityBuildController controller)
        {
            game = owner;
            tools = controller;
            document = gameObject.GetComponent<UIDocument>();
            if (document == null)
                document = gameObject.AddComponent<UIDocument>();

            runtimePanel = Resources.Load<PanelSettings>("CityLabPanelSettings");
            if (runtimePanel == null)
            {
                ownsRuntimePanel = true;
                runtimeTheme = ScriptableObject.CreateInstance<ThemeStyleSheet>();
                runtimeTheme.name = "CityLab Runtime Theme Fallback";
                runtimePanel = ScriptableObject.CreateInstance<PanelSettings>();
                runtimePanel.name = "CityLab Runtime Panel Fallback";
                runtimePanel.scaleMode = PanelScaleMode.ScaleWithScreenSize;
                runtimePanel.referenceResolution = new Vector2Int(1920, 1080);
                runtimePanel.match = 0.5f;
                runtimePanel.themeStyleSheet = runtimeTheme;
            }
            document.panelSettings = runtimePanel;
            document.sortingOrder = 100;
        }

        void Start()
        {
            BuildUi();
            if (pendingSnapshot != null)
                Refresh(pendingSnapshot);
        }

        void OnDestroy()
        {
            if (ownsRuntimePanel && runtimePanel != null)
                Destroy(runtimePanel);
            if (ownsRuntimePanel && runtimeTheme != null)
                Destroy(runtimeTheme);
        }

        void BuildUi()
        {
            if (document == null)
                return;

            root = document.rootVisualElement;
            root.Clear();
            root.pickingMode = PickingMode.Ignore;
            root.style.flexGrow = 1;
            root.style.flexDirection = FlexDirection.Column;
            root.style.justifyContent = Justify.SpaceBetween;
            root.style.paddingLeft = 22;
            root.style.paddingRight = 22;
            root.style.paddingTop = 16;
            root.style.paddingBottom = 16;

            BuildStatusBar();
            BuildMainPanels();
            BuildFooter();

            root.RegisterCallback<GeometryChangedEvent>(evt =>
                ApplyResponsiveLayout(evt.newRect.width, evt.newRect.height));
            ApplyResponsiveLayout(1920f, 1080f);
        }

        void BuildStatusBar()
        {
            topBar = MakeFramedPanel();
            topBar.name = "citylab-status-bar";
            topBar.style.flexDirection = FlexDirection.Row;
            topBar.style.alignItems = Align.Stretch;
            topBar.style.flexShrink = 0;
            topBar.style.minHeight = 74;
            topBar.style.paddingLeft = 8;
            topBar.style.paddingRight = 8;
            topBar.style.paddingTop = 6;
            topBar.style.paddingBottom = 6;

            brandBlock = new VisualElement();
            brandBlock.style.width = 300;
            brandBlock.style.flexShrink = 0;
            brandBlock.style.justifyContent = Justify.Center;
            brandBlock.style.paddingLeft = 18;
            brandBlock.style.paddingRight = 18;
            brandBlock.style.borderRightWidth = 1;
            brandBlock.style.borderRightColor = BronzeMuted;

            var title = MakeLabel("VICTORIA  —  DOMAINE 1400", 20, BronzeBright, FontStyle.Bold);
            title.style.letterSpacing = 1.2f;
            title.style.marginBottom = 1;
            var subtitle = MakeLabel("CHRONIQUE DE LA SEIGNEURIE", 10, ParchmentMuted, FontStyle.Normal);
            subtitle.style.letterSpacing = 1.7f;
            subtitle.style.marginBottom = 0;
            brandBlock.Add(title);
            brandBlock.Add(subtitle);
            topBar.Add(brandBlock);

            statusStrip = new VisualElement();
            statusStrip.style.flexGrow = 1;
            statusStrip.style.flexDirection = FlexDirection.Row;
            statusStrip.style.alignItems = Align.Stretch;
            statusStrip.style.justifyContent = Justify.SpaceAround;
            resources = AddStatusCell(statusStrip, "RÉSERVES", "Bois  —");
            population = AddStatusCell(statusStrip, "POPULATION", "Habitants  —");
            construction = AddStatusCell(statusStrip, "OUVRAGES", "Chantiers  —");
            services = AddStatusCell(statusStrip, "SERVICES", "Capacités  —");
            clock = AddStatusCell(statusStrip, "CHRONIQUE", "Jour 01", false);
            topBar.Add(statusStrip);
            root.Add(topBar);
        }

        void BuildMainPanels()
        {
            contentRow = new VisualElement();
            contentRow.name = "citylab-main-hud";
            contentRow.pickingMode = PickingMode.Ignore;
            contentRow.style.flexGrow = 1;
            contentRow.style.flexDirection = FlexDirection.Row;
            contentRow.style.alignItems = Align.FlexStart;
            contentRow.style.justifyContent = Justify.SpaceBetween;
            contentRow.style.paddingTop = 18;
            contentRow.style.paddingBottom = 18;

            toolPalette = MakeFramedPanel();
            toolPalette.name = "citylab-tool-palette";
            toolPalette.style.width = 282;
            toolPalette.style.paddingLeft = 12;
            toolPalette.style.paddingRight = 12;
            toolPalette.style.paddingTop = 12;
            toolPalette.style.paddingBottom = 14;
            toolPalette.Add(MakeSectionHeader("ORDRES DU BAILLI", "OUTILS"));

            var toolsIntro = MakeLabel("Façonnez les voies et les futurs foyers du bourg.", 12, ParchmentMuted);
            toolsIntro.style.whiteSpace = WhiteSpace.Normal;
            toolsIntro.style.marginTop = 8;
            toolsIntro.style.marginBottom = 8;
            toolPalette.Add(toolsIntro);

            toolButtons = new VisualElement();
            toolButtons.style.flexDirection = FlexDirection.Column;
            routeButton = new Button(() => SelectTool(CityToolMode.DrawRoad))
            {
                text = "[R]   TRACER UNE ROUTE"
            };
            zoneButton = new Button(() => SelectTool(CityToolMode.ZoneResidential))
            {
                text = "[Z]   LOTIR DES PARCELLES"
            };
            lumberCampButton = new Button(() => SelectTool(CityToolMode.PlaceLumberCamp))
            {
                text = "[B]   FONDER UN CAMP FORESTIER"
            };
            var civicChoices = new List<string>();
            foreach (var archetype in CivicArchetypes)
                civicChoices.Add(game.Catalog.Get(archetype).label.ToUpperInvariant());
            civicBuildingSelector = new DropdownField("BÂTIMENT", civicChoices, 0);
            civicBuildingSelector.style.marginTop = 8;
            civicBuildingSelector.style.marginBottom = 2;
            civicBuildingSelector.style.color = Parchment;
            civicBuildingButton = new Button(SelectCivicBuilding)
            {
                text = "[C]   PLACER LE BÂTIMENT"
            };
            StyleButton(routeButton, false);
            StyleButton(zoneButton, false);
            StyleButton(lumberCampButton, false);
            StyleButton(civicBuildingButton, false);
            toolButtons.Add(routeButton);
            toolButtons.Add(zoneButton);
            toolButtons.Add(lumberCampButton);
            toolButtons.Add(civicBuildingSelector);
            toolButtons.Add(civicBuildingButton);
            toolPalette.Add(toolButtons);

            var toolHint = MakeLabel("Sélectionnez ensuite un chantier pour régler son urgence.", 11, ParchmentMuted);
            toolHint.style.whiteSpace = WhiteSpace.Normal;
            toolHint.style.marginTop = 7;
            toolHint.style.marginBottom = 0;
            toolPalette.Add(toolHint);
            contentRow.Add(toolPalette);

            constructionCard = MakeFramedPanel();
            constructionCard.name = "citylab-construction-card";
            constructionCard.style.width = 398;
            constructionCard.style.paddingLeft = 15;
            constructionCard.style.paddingRight = 15;
            constructionCard.style.paddingTop = 12;
            constructionCard.style.paddingBottom = 14;
            constructionCard.Add(MakeSectionHeader("FICHE DE CHANTIER", "INSPECTION"));

            selectionState = MakeLabel("AUCUNE SÉLECTION", 10, BronzeBright, FontStyle.Bold);
            selectionState.style.letterSpacing = 1.5f;
            selectionState.style.marginTop = 11;
            selectionState.style.marginBottom = 4;
            selection = MakeLabel("Aucun chantier inspecté", 19, Parchment, FontStyle.Bold);
            selection.style.whiteSpace = WhiteSpace.Normal;
            selection.style.marginBottom = 5;
            selectionDetails = MakeLabel("Cliquez sur un ouvrage pour consulter sa progression.", 12, ParchmentMuted);
            selectionDetails.style.whiteSpace = WhiteSpace.Normal;
            selectionDetails.style.minHeight = 34;
            constructionCard.Add(selectionState);
            constructionCard.Add(selection);
            constructionCard.Add(selectionDetails);
            constructionCard.Add(MakeRule());

            var priorityTitle = MakeLabel("PRIORITÉ DES OUVRIERS", 10, ParchmentMuted, FontStyle.Bold);
            priorityTitle.style.letterSpacing = 1.1f;
            priorityTitle.style.marginTop = 10;
            priorityTitle.style.marginBottom = 3;
            constructionCard.Add(priorityTitle);

            priorityControls = new VisualElement();
            priorityControls.style.flexDirection = FlexDirection.Row;
            lowPriorityButton = new Button(() => tools.SetSelectedPriority(0)) { text = "BASSE" };
            normalPriorityButton = new Button(() => tools.SetSelectedPriority(1)) { text = "NORMALE" };
            highPriorityButton = new Button(() => tools.SetSelectedPriority(3)) { text = "HAUTE" };
            foreach (var button in new[] { lowPriorityButton, normalPriorityButton, highPriorityButton })
            {
                StyleButton(button, true);
                button.style.flexGrow = 1;
                button.style.marginLeft = 2;
                button.style.marginRight = 2;
                priorityControls.Add(button);
            }
            priorityControls.SetEnabled(false);
            priorityControls.style.opacity = 0.42f;
            constructionCard.Add(priorityControls);
            contentRow.Add(constructionCard);
            root.Add(contentRow);
        }

        void BuildFooter()
        {
            footerBar = MakeFramedPanel();
            footerBar.name = "citylab-command-bar";
            footerBar.style.flexDirection = FlexDirection.Row;
            footerBar.style.alignItems = Align.Center;
            footerBar.style.flexShrink = 0;
            footerBar.style.minHeight = 68;
            footerBar.style.paddingLeft = 15;
            footerBar.style.paddingRight = 15;
            footerBar.style.paddingTop = 8;
            footerBar.style.paddingBottom = 8;

            var commandBlock = new VisualElement();
            commandBlock.style.flexGrow = 1;
            commandBlock.style.minWidth = 280;
            var commandCaption = MakeLabel("COMMANDE EN COURS", 9, BronzeBright, FontStyle.Bold);
            commandCaption.style.letterSpacing = 1.4f;
            commandCaption.style.marginBottom = 2;
            prompt = MakeLabel("Choisissez un ordre pour commencer.", 13, Parchment);
            prompt.style.whiteSpace = WhiteSpace.Normal;
            prompt.style.marginBottom = 0;
            commandBlock.Add(commandCaption);
            commandBlock.Add(prompt);
            footerBar.Add(commandBlock);

            var messageBlock = new VisualElement();
            messageBlock.style.width = 360;
            messageBlock.style.minHeight = 42;
            messageBlock.style.justifyContent = Justify.Center;
            messageBlock.style.paddingLeft = 13;
            messageBlock.style.paddingRight = 13;
            messageBlock.style.marginLeft = 12;
            messageBlock.style.marginRight = 12;
            messageBlock.style.backgroundColor = new Color(0.09f, 0.075f, 0.055f, 0.92f);
            messageBlock.style.borderLeftWidth = 3;
            messageBlock.style.borderLeftColor = Bronze;
            message = MakeLabel("Le domaine attend vos ordres.", 12, Success, FontStyle.Bold);
            message.style.whiteSpace = WhiteSpace.Normal;
            message.style.marginBottom = 0;
            messageBlock.Add(message);
            footerBar.Add(messageBlock);

            var timeControls = new VisualElement();
            timeControls.style.flexDirection = FlexDirection.Row;
            timeControls.style.alignItems = Align.Center;
            timeControls.style.marginRight = 12;
            pauseButton = new Button(() => game.TogglePause()) { text = "II" };
            speedOneButton = new Button(() => game.SetSimulationSpeed(1f)) { text = "1" };
            speedTwoButton = new Button(() => game.SetSimulationSpeed(2f)) { text = "2" };
            speedFourButton = new Button(() => game.SetSimulationSpeed(4f)) { text = "4" };
            foreach (var button in new[] { pauseButton, speedOneButton, speedTwoButton, speedFourButton })
            {
                StyleButton(button, true);
                button.style.width = 34;
                button.style.marginLeft = 2;
                button.style.marginRight = 2;
                timeControls.Add(button);
            }
            footerBar.Add(timeControls);

            help = MakeLabel("CAMÉRA  WASD / BORDS     ZOOM  MOLETTE     ROTATION  CLIC DROIT     TEMPS  ESPACE / 1-3", 10,
                ParchmentMuted, FontStyle.Bold);
            help.style.maxWidth = 570;
            help.style.whiteSpace = WhiteSpace.Normal;
            help.style.unityTextAlign = TextAnchor.MiddleRight;
            help.style.marginBottom = 0;
            footerBar.Add(help);
            root.Add(footerBar);
        }

        void ApplyResponsiveLayout(float width, float height)
        {
            if (root == null || width <= 0f)
                return;

            var compact = width < 1420f;
            var narrow = width < 980f;
            var shallow = height < 760f;

            root.style.paddingLeft = compact ? 12 : 22;
            root.style.paddingRight = compact ? 12 : 22;
            root.style.paddingTop = shallow ? 9 : 16;
            root.style.paddingBottom = shallow ? 9 : 16;

            brandBlock.style.width = compact ? 238 : 300;
            topBar.style.minHeight = shallow ? 62 : 74;
            contentRow.style.paddingTop = shallow ? 9 : 18;
            contentRow.style.paddingBottom = shallow ? 9 : 18;

            if (narrow)
            {
                topBar.style.flexDirection = FlexDirection.Column;
                brandBlock.style.width = Length.Percent(100);
                brandBlock.style.borderRightWidth = 0;
                brandBlock.style.borderBottomWidth = 1;
                brandBlock.style.borderBottomColor = BronzeMuted;
                brandBlock.style.paddingTop = 7;
                brandBlock.style.paddingBottom = 7;
                statusStrip.style.minHeight = 58;

                contentRow.style.flexDirection = FlexDirection.Column;
                contentRow.style.alignItems = Align.Stretch;
                toolPalette.style.width = Length.Percent(100);
                constructionCard.style.width = Length.Percent(100);
                constructionCard.style.marginTop = 8;
                toolButtons.style.flexDirection = FlexDirection.Row;
                routeButton.style.flexGrow = 1;
                zoneButton.style.flexGrow = 1;
                lumberCampButton.style.flexGrow = 1;
                civicBuildingButton.style.flexGrow = 1;
                routeButton.style.marginRight = 4;
                zoneButton.style.marginLeft = 4;

                footerBar.style.flexDirection = FlexDirection.Column;
                footerBar.style.alignItems = Align.Stretch;
                message.parent.style.width = Length.Percent(100);
                message.parent.style.marginLeft = 0;
                message.parent.style.marginRight = 0;
                message.parent.style.marginTop = 7;
                message.parent.style.marginBottom = 7;
                help.style.maxWidth = StyleKeyword.None;
                help.style.unityTextAlign = TextAnchor.MiddleLeft;
            }
            else
            {
                topBar.style.flexDirection = FlexDirection.Row;
                brandBlock.style.borderRightWidth = 1;
                brandBlock.style.borderBottomWidth = 0;
                brandBlock.style.paddingTop = 0;
                brandBlock.style.paddingBottom = 0;
                statusStrip.style.minHeight = StyleKeyword.None;

                contentRow.style.flexDirection = FlexDirection.Row;
                contentRow.style.alignItems = Align.FlexStart;
                toolPalette.style.width = compact ? 250 : 282;
                constructionCard.style.width = compact ? 350 : 398;
                constructionCard.style.marginTop = 0;
                toolButtons.style.flexDirection = FlexDirection.Column;
                routeButton.style.flexGrow = 0;
                zoneButton.style.flexGrow = 0;
                lumberCampButton.style.flexGrow = 0;
                civicBuildingButton.style.flexGrow = 0;
                routeButton.style.marginRight = 0;
                zoneButton.style.marginLeft = 0;

                footerBar.style.flexDirection = FlexDirection.Row;
                footerBar.style.alignItems = Align.Center;
                message.parent.style.width = compact ? 300 : 360;
                message.parent.style.marginLeft = 12;
                message.parent.style.marginRight = 12;
                message.parent.style.marginTop = 0;
                message.parent.style.marginBottom = 0;
                help.style.maxWidth = compact ? 430 : 570;
                help.style.unityTextAlign = TextAnchor.MiddleRight;
            }
        }

        public void Refresh(CitySnapshot snapshot)
        {
            pendingSnapshot = snapshot;
            if (resources == null)
                return;

            var complete = 0;
            var active = 0;
            foreach (var building in snapshot.buildings)
            {
                if (building.phase == BuildingPhase.Complete)
                    complete++;
                else
                    active++;
            }

            var housed = 0;
            var totalSatisfaction = 0;
            var prosperous = 0;
            foreach (var household in snapshot.households)
            {
                if (household.homeBuildingId != 0)
                    housed++;
                totalSatisfaction += household.satisfactionPermille;
                if (household.level == HouseholdLevel.Prosperous)
                    prosperous++;
            }

            var timberRemaining = 0;
            var forestryWorkers = 0;
            foreach (var site in snapshot.productionSites)
            {
                timberRemaining += site.remainingTimber;
                forestryWorkers += site.assignedWorkers;
            }

            var employed = 0;
            var atWork = 0;
            var absent = 0;
            var hungry = 0;
            foreach (var household in snapshot.households)
                if (household.hungry) hungry++;
            foreach (var villager in snapshot.villagers)
            {
                if (villager.job != VillagerJob.None) employed++;
                if (villager.isAtWork) atWork++;
                if (villager.absentToday) absent++;
            }

            var food = snapshot.resources?.Find(item => item.kind == CityResourceKind.Food)?.quantity ?? 0;
            var facilityCount = 0;
            var productionBatches = 0;
            var locallyStored = 0;
            var marketCovered = 0;
            var marketScarcity = 0;
            var marketCount = 0;
            foreach (var building in snapshot.buildings)
            {
                foreach (var local in building.localStocks)
                    locallyStored += local.quantity;
                if (building.archetype == BuildingArchetype.Market &&
                    building.phase == BuildingPhase.Complete)
                {
                    marketCount++;
                    marketCovered += building.marketCoveredHouseholds;
                    marketScarcity += building.marketScarcityPermille;
                }
            }
            foreach (var site in snapshot.productionSites)
                if (site.kind != ProductionSiteKind.LumberCamp)
                {
                    facilityCount++;
                    productionBatches += site.totalBatches;
                }
            var travelingMerchants = 0;
            foreach (var order in snapshot.tradeOrders)
                if (order.status == TradeOrderStatus.Traveling)
                    travelingMerchants++;
            var activeFields = 0;
            var harvestableFields = 0;
            foreach (var field in snapshot.fields)
            {
                if (field.phase != FieldPhase.Fallow && field.phase != FieldPhase.Harvested)
                    activeFields++;
                if (field.phase == FieldPhase.ReadyToHarvest)
                    harvestableFields++;
            }
            var activeGardens = 0;
            var extensions = 0;
            foreach (var parcel in snapshot.parcels)
            {
                if (parcel.gardenActive)
                    activeGardens++;
                extensions += parcel.extensionLevel;
            }
            resources.text = $"Bois {snapshot.stockWood}  Réservé {snapshot.reservedWood}  " +
                $"Nourriture {food}  Pièces {snapshot.treasuryCoins}  Marchands {travelingMerchants}";
            population.text = $"Hab. {snapshot.villagers.Count}  Foy. {housed}/{snapshot.households.Count}  " +
                $"Sat. {(snapshot.households.Count > 0 ? totalSatisfaction / snapshot.households.Count : 0)}‰  Prosp. {prosperous}";
            construction.text = $"Actifs {active}  Achevés {complete}  Jardins {activeGardens}  " +
                $"Extensions {extensions}  Champs {activeFields}/{snapshot.fields.Count}  Récolte {harvestableFields}";
            services.text = $"V {snapshot.foodStorageCapacity}  B {snapshot.goodsStorageCapacity}  " +
                $"M {snapshot.marketServiceCapacity}  O {snapshot.toolProductionCapacity}  " +
                $"Marché {marketCovered} foy.  Rareté {(marketCount > 0 ? marketScarcity / marketCount : 0)}‰  Dépôts {locallyStored}";
            var calendar = snapshot.calendar ?? new CityCalendarState();
            var season = calendar.season switch
            {
                CitySeason.Spring => "PRINTEMPS",
                CitySeason.Summer => "ÉTÉ",
                CitySeason.Autumn => "AUTOMNE",
                _ => "HIVER"
            };
            var speedText = game.IsPaused ? "PAUSE" : $"x{game.SimulationSpeed:0}";
            var weather = snapshot.dailyWeather switch
            {
                CityWeather.Rain => "PLUIE",
                CityWeather.Drought => "SÉCHERESSE",
                CityWeather.Frost => "GEL",
                _ => "CLAIR"
            };
            clock.text = $"{calendar.day:00}/{calendar.month:00}/A{calendar.year}  " +
                $"{calendar.hour:00}h{calendar.minute:00}  {season}  {weather}  {speedText}";

            var missingWood = 0;
            foreach (var building in snapshot.buildings)
            {
                if (building.phase != BuildingPhase.Complete)
                    missingWood += Mathf.Max(0, building.requiredWood - building.deliveredWood);
            }

            var selected = snapshot.buildings.Find(item => item.id == tools.SelectedBuildingId);
            if (selected == null)
            {
                selectionState.text = "AUCUNE SÉLECTION";
                selectionState.style.color = BronzeBright;
                selection.text = "Aucun chantier inspecté";
                selectionDetails.text = "Cliquez sur un ouvrage pour consulter sa progression.";
                priorityControls.SetEnabled(false);
                priorityControls.style.opacity = 0.42f;
                SetPriorityButtonState(-1);
            }
            else if (selected.phase == BuildingPhase.Complete)
            {
                selectionState.text = "OUVRAGE ACHEVÉ";
                selectionState.style.color = Success;
                selection.text = $"Maison {selected.id:00}";
                selectionDetails.text = "La demeure est terminée et prête à accueillir un foyer.";
                priorityControls.SetEnabled(false);
                priorityControls.style.opacity = 0.42f;
                SetPriorityButtonState(-1);
            }
            else
            {
                selectionState.text = "CHANTIER EN COURS";
                selectionState.style.color = BronzeBright;
                selection.text = $"Chantier {selected.id:00}";
                if (!selected.terrainPrepared)
                {
                    selectionDetails.text =
                        $"Priorité {PriorityName(selected.priority)}   •   Terrassement {selected.terrainCutFillMillimeters} mm";
                }
                else if (CurrentConstructionMaterial(selected) is ConstructionMaterialState material)
                {
                    selectionDetails.text =
                        $"{PhaseName(selected.phase)}   •   Échafaudage {ScaffoldStage(selected.phase)}/4   •   " +
                        $"{ResourceName(material.resource)} {material.delivered}/{material.required}";
                }
                else
                {
                    selectionDetails.text =
                        $"Priorité {PriorityName(selected.priority)}   •   {PhaseName(selected.phase)}   •   " +
                        $"Échafaudage {ScaffoldStage(selected.phase)}/4";
                }
                priorityControls.SetEnabled(true);
                priorityControls.style.opacity = 1f;
                SetPriorityButtonState(selected.priority);
            }

            SetButtonActive(routeButton, tools.Mode == CityToolMode.DrawRoad);
            SetButtonActive(zoneButton, tools.Mode == CityToolMode.ZoneResidential);
            SetButtonActive(lumberCampButton, tools.Mode == CityToolMode.PlaceLumberCamp);
            SetButtonActive(civicBuildingButton, tools.Mode == CityToolMode.PlaceBuilding);
            SetButtonActive(pauseButton, game.IsPaused);
            SetButtonActive(speedOneButton, !game.IsPaused && Mathf.Approximately(game.SimulationSpeed, 1f));
            SetButtonActive(speedTwoButton, !game.IsPaused && Mathf.Approximately(game.SimulationSpeed, 2f));
            SetButtonActive(speedFourButton, !game.IsPaused && Mathf.Approximately(game.SimulationSpeed, 4f));

            prompt.text = string.IsNullOrWhiteSpace(tools.Prompt)
                ? "Choisissez un ordre pour commencer."
                : tools.Prompt;

            if (snapshot.stockWood == 0 && missingWood > 0)
            {
                message.text = $"Bois insuffisant — {missingWood} unités manquantes";
                message.style.color = Warning;
                message.parent.style.borderLeftColor = Warning;
            }
            else
            {
                message.text = string.IsNullOrWhiteSpace(lastMessage)
                    ? "Le domaine attend vos ordres."
                    : lastMessage;
                message.style.color = lastMessageSuccess ? Success : Warning;
                message.parent.style.borderLeftColor = lastMessageSuccess ? Bronze : Warning;
            }
        }

        public void ShowMessage(string text, bool success)
        {
            lastMessage = text;
            lastMessageSuccess = success;
            if (message == null)
                return;

            message.text = string.IsNullOrWhiteSpace(text) ? "Le domaine attend vos ordres." : text;
            message.style.color = success ? Success : Warning;
            message.parent.style.borderLeftColor = success ? Bronze : Warning;
        }

        public bool ContainsPointer(Vector2 screenPoint)
        {
            if (root == null || root.panel == null)
                return false;
            var panelPoint = RuntimePanelUtils.ScreenToPanel(root.panel,
                new Vector2(screenPoint.x, Screen.height - screenPoint.y));
            return ContainsPanelPoint(topBar, panelPoint) || ContainsPanelPoint(toolPalette, panelPoint) ||
                   ContainsPanelPoint(constructionCard, panelPoint) || ContainsPanelPoint(footerBar, panelPoint);
        }

        void SelectTool(CityToolMode mode)
        {
            tools.SetMode(mode);
            SetButtonActive(routeButton, mode == CityToolMode.DrawRoad);
            SetButtonActive(zoneButton, mode == CityToolMode.ZoneResidential);
            SetButtonActive(lumberCampButton, mode == CityToolMode.PlaceLumberCamp);
            SetButtonActive(civicBuildingButton, mode == CityToolMode.PlaceBuilding);
            if (prompt != null)
                prompt.text = tools.Prompt;
        }

        void SelectCivicBuilding()
        {
            var index = Mathf.Clamp(civicBuildingSelector.index, 0, CivicArchetypes.Length - 1);
            tools.SetBuildingMode(CivicArchetypes[index]);
            SetButtonActive(routeButton, false);
            SetButtonActive(zoneButton, false);
            SetButtonActive(lumberCampButton, false);
            SetButtonActive(civicBuildingButton, true);
            if (prompt != null)
                prompt.text = tools.Prompt;
        }

        void SetPriorityButtonState(int priority)
        {
            SetButtonActive(lowPriorityButton, priority == 0);
            SetButtonActive(normalPriorityButton, priority == 1 || priority == 2);
            SetButtonActive(highPriorityButton, priority >= 3);
        }

        static string PriorityName(int priority)
        {
            if (priority >= 3)
                return "haute";
            return priority <= 0 ? "basse" : "normale";
        }

        static ConstructionMaterialState CurrentConstructionMaterial(BuildingState building)
        {
            if (building.constructionMaterials == null)
                return null;
            foreach (var material in building.constructionMaterials)
                if (material != null && material.phase == building.phase)
                    return material;
            return null;
        }

        static string PhaseName(BuildingPhase phase) => phase switch
        {
            BuildingPhase.Foundation => "Fondations",
            BuildingPhase.Framing => "Charpente",
            BuildingPhase.Roofing => "Couverture",
            BuildingPhase.Detailing => "Finitions",
            _ => "Ouvrage"
        };

        static int ScaffoldStage(BuildingPhase phase) => phase switch
        {
            BuildingPhase.Foundation => 1,
            BuildingPhase.Framing => 2,
            BuildingPhase.Roofing => 3,
            BuildingPhase.Detailing => 4,
            _ => 0
        };

        static string ResourceName(CityResourceKind resource) => resource switch
        {
            CityResourceKind.Wood => "Bois",
            CityResourceKind.Planks => "Planches",
            CityResourceKind.Stone => "Pierre",
            CityResourceKind.Tools => "Outils",
            CityResourceKind.Food => "Vivres",
            CityResourceKind.Textile => "Textile",
            _ => "Matériau"
        };

        static bool ContainsPanelPoint(VisualElement element, Vector2 point) =>
            element != null && element.resolvedStyle.display != DisplayStyle.None && element.worldBound.Contains(point);

        static Label AddStatusCell(VisualElement parent, string caption, string initialValue, bool divider = true)
        {
            var cell = new VisualElement();
            cell.style.flexGrow = 1;
            cell.style.flexBasis = 0;
            cell.style.minWidth = 180;
            cell.style.justifyContent = Justify.Center;
            cell.style.paddingLeft = 18;
            cell.style.paddingRight = 18;
            if (divider)
            {
                cell.style.borderRightWidth = 1;
                cell.style.borderRightColor = BronzeMuted;
            }

            var heading = MakeLabel(caption, 9, BronzeBright, FontStyle.Bold);
            heading.style.letterSpacing = 1.4f;
            heading.style.marginBottom = 3;
            var value = MakeLabel(initialValue, 14, Parchment, FontStyle.Bold);
            value.style.marginBottom = 0;
            value.style.whiteSpace = WhiteSpace.NoWrap;
            cell.Add(heading);
            cell.Add(value);
            parent.Add(cell);
            return value;
        }

        static VisualElement MakeFramedPanel()
        {
            var panel = new VisualElement();
            panel.pickingMode = PickingMode.Position;
            panel.style.backgroundColor = Obsidian;
            panel.style.borderLeftWidth = 1;
            panel.style.borderRightWidth = 1;
            panel.style.borderTopWidth = 1;
            panel.style.borderBottomWidth = 1;
            panel.style.borderLeftColor = Bronze;
            panel.style.borderRightColor = Bronze;
            panel.style.borderTopColor = BronzeBright;
            panel.style.borderBottomColor = BronzeMuted;
            panel.style.borderTopLeftRadius = 3;
            panel.style.borderTopRightRadius = 3;
            panel.style.borderBottomLeftRadius = 3;
            panel.style.borderBottomRightRadius = 3;
            return panel;
        }

        static VisualElement MakeSectionHeader(string title, string tag)
        {
            var row = new VisualElement();
            row.style.flexDirection = FlexDirection.Row;
            row.style.alignItems = Align.Center;
            row.style.justifyContent = Justify.SpaceBetween;
            row.style.paddingBottom = 8;
            row.style.borderBottomWidth = 1;
            row.style.borderBottomColor = BronzeMuted;

            var titleLabel = MakeLabel(title, 13, BronzeBright, FontStyle.Bold);
            titleLabel.style.letterSpacing = 1.1f;
            titleLabel.style.marginBottom = 0;
            var tagLabel = MakeLabel(tag, 8, ParchmentMuted, FontStyle.Bold);
            tagLabel.style.letterSpacing = 1.2f;
            tagLabel.style.marginBottom = 0;
            tagLabel.style.paddingLeft = 7;
            tagLabel.style.paddingRight = 7;
            tagLabel.style.paddingTop = 3;
            tagLabel.style.paddingBottom = 3;
            tagLabel.style.borderLeftWidth = 1;
            tagLabel.style.borderRightWidth = 1;
            tagLabel.style.borderTopWidth = 1;
            tagLabel.style.borderBottomWidth = 1;
            tagLabel.style.borderLeftColor = BronzeMuted;
            tagLabel.style.borderRightColor = BronzeMuted;
            tagLabel.style.borderTopColor = BronzeMuted;
            tagLabel.style.borderBottomColor = BronzeMuted;
            row.Add(titleLabel);
            row.Add(tagLabel);
            return row;
        }

        static VisualElement MakeRule()
        {
            var rule = new VisualElement();
            rule.style.height = 1;
            rule.style.marginTop = 8;
            rule.style.backgroundColor = BronzeMuted;
            return rule;
        }

        static Label MakeLabel(string text, int size, Color color, FontStyle fontStyle = FontStyle.Normal)
        {
            var label = new Label(text);
            label.style.unityFont = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            label.style.unityFontStyleAndWeight = fontStyle;
            label.style.fontSize = size;
            label.style.color = color;
            label.style.marginBottom = 7;
            return label;
        }

        static void StyleButton(Button button, bool compact)
        {
            button.style.unityFont = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            button.style.unityFontStyleAndWeight = FontStyle.Bold;
            button.style.unityTextAlign = compact ? TextAnchor.MiddleCenter : TextAnchor.MiddleLeft;
            button.style.fontSize = compact ? 10 : 12;
            button.style.letterSpacing = compact ? 0.6f : 0.9f;
            button.style.height = compact ? 34 : 46;
            button.style.paddingLeft = compact ? 6 : 14;
            button.style.paddingRight = compact ? 6 : 14;
            button.style.marginTop = 4;
            button.style.marginBottom = 4;
            button.style.backgroundColor = CharcoalRaised;
            button.style.color = Parchment;
            button.style.borderLeftWidth = compact ? 1 : 3;
            button.style.borderRightWidth = 1;
            button.style.borderTopWidth = 1;
            button.style.borderBottomWidth = 1;
            button.style.borderLeftColor = BronzeBright;
            button.style.borderRightColor = BronzeMuted;
            button.style.borderTopColor = Bronze;
            button.style.borderBottomColor = BronzeMuted;
            button.style.borderTopLeftRadius = 2;
            button.style.borderTopRightRadius = 2;
            button.style.borderBottomLeftRadius = 2;
            button.style.borderBottomRightRadius = 2;
            button.userData = false;

            button.RegisterCallback<MouseEnterEvent>(_ =>
            {
                if (button.enabledSelf)
                {
                    button.style.backgroundColor = new Color(0.22f, 0.14f, 0.075f, 1f);
                    button.style.color = Color.white;
                }
            });
            button.RegisterCallback<MouseLeaveEvent>(_ =>
            {
                ApplyButtonState(button);
            });
        }

        static void SetButtonActive(Button button, bool active)
        {
            if (button == null)
                return;
            button.userData = active;
            ApplyButtonState(button);
        }

        static void ApplyButtonState(Button button)
        {
            var active = button.userData is bool value && value;
            button.style.backgroundColor = active
                ? new Color(0.26f, 0.16f, 0.075f, 1f)
                : CharcoalRaised;
            button.style.color = active ? Color.white : Parchment;
            button.style.borderLeftColor = active ? BronzeBright : Bronze;
            button.style.borderTopColor = active ? BronzeBright : Bronze;
        }
    }
}
