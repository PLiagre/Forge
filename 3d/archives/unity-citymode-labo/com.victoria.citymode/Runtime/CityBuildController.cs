using UnityEngine;
using UnityEngine.InputSystem;

namespace Victoria.CityMode
{
    public enum CityToolMode : byte
    {
        Inspect = 0,
        DrawRoad = 1,
        ZoneResidential = 2,
        PlaceLumberCamp = 3,
        PlaceBuilding = 4
    }

    public sealed class CityBuildController : MonoBehaviour
    {
        CityLabGame game;
        bool hasRoadStart;
        Vector3 roadStart;
        GameObject roadPreview;
        Material roadPreviewMaterial;
        GameObject lumberCampPreview;
        Material lumberCampPreviewMaterial;
        GameObject buildingPreview;
        Material buildingPreviewMaterial;
        Terrain terrain;

        public CityToolMode Mode { get; private set; }
        public int SelectedBuildingId { get; private set; }
        public BuildingArchetype SelectedArchetype { get; private set; } = BuildingArchetype.Granary;
        public string Prompt { get; private set; } = "Selectionnez un outil";

        public void Initialize(CityLabGame owner)
        {
            game = owner;
            terrain = FindFirstObjectByType<Terrain>();
            SetMode(CityToolMode.Inspect);
        }

        public void SetMode(CityToolMode mode)
        {
            Mode = mode;
            hasRoadStart = false;
            if (roadPreview != null) roadPreview.SetActive(false);
            if (lumberCampPreview != null) lumberCampPreview.SetActive(false);
            if (buildingPreview != null) buildingPreview.SetActive(false);
            Prompt = mode switch
            {
                CityToolMode.DrawRoad => "Route: cliquez le point de depart",
                CityToolMode.ZoneResidential => "Parcelles: cliquez une route",
                CityToolMode.PlaceLumberCamp => "Camp forestier: choisissez une clairiere hors du bourg",
                CityToolMode.PlaceBuilding => game.Catalog.Get(SelectedArchetype).label +
                    ": choisissez un emplacement libre",
                _ => "R: route  |  Z: parcelles  |  B: camp forestier  |  Echap: annuler"
            };
        }

        public void SetBuildingMode(BuildingArchetype archetype)
        {
            if (archetype < BuildingArchetype.Granary || archetype > BuildingArchetype.Chapel)
                return;
            SelectedArchetype = archetype;
            SetMode(CityToolMode.PlaceBuilding);
        }

        void Update()
        {
            var keyboard = Keyboard.current;
            var mouse = Mouse.current;
            if (keyboard == null || mouse == null || game == null)
                return;

            if (keyboard.rKey.wasPressedThisFrame) SetMode(CityToolMode.DrawRoad);
            if (keyboard.zKey.wasPressedThisFrame) SetMode(CityToolMode.ZoneResidential);
            if (keyboard.bKey.wasPressedThisFrame) SetMode(CityToolMode.PlaceLumberCamp);
            if (keyboard.gKey.wasPressedThisFrame) SetBuildingMode(BuildingArchetype.Granary);
            if (keyboard.tKey.wasPressedThisFrame) SetBuildingMode(BuildingArchetype.Warehouse);
            if (keyboard.mKey.wasPressedThisFrame) SetBuildingMode(BuildingArchetype.Market);
            if (keyboard.fKey.wasPressedThisFrame) SetBuildingMode(BuildingArchetype.Blacksmith);
            if (keyboard.nKey.wasPressedThisFrame) SetBuildingMode(BuildingArchetype.Barn);
            if (keyboard.cKey.wasPressedThisFrame) SetBuildingMode(BuildingArchetype.Chapel);
            if (keyboard.escapeKey.wasPressedThisFrame) SetMode(CityToolMode.Inspect);
            UpdateRoadPreview(mouse.position.ReadValue());
            UpdateLumberCampPreview(mouse.position.ReadValue());
            UpdateBuildingPreview(mouse.position.ReadValue());
            if (!mouse.leftButton.wasPressedThisFrame)
                return;
            if (game.IsPointerOverHud(mouse.position.ReadValue()))
                return;

            var ray = game.WorldCamera.ScreenPointToRay(mouse.position.ReadValue());
            if (Mode == CityToolMode.DrawRoad)
                HandleRoadClick(ray);
            else if (Mode == CityToolMode.ZoneResidential)
                HandleZoneClick(ray);
            else if (Mode == CityToolMode.PlaceLumberCamp)
                HandleLumberCampClick(ray);
            else if (Mode == CityToolMode.PlaceBuilding)
                HandleBuildingClick(ray);
            else
                HandleInspectClick(ray);
        }

        void HandleInspectClick(Ray ray)
        {
            var selected = 0;
            if (Physics.Raycast(ray, out var hit, 1000f))
            {
                var building = hit.collider.GetComponentInParent<BuildingView>();
                if (building != null)
                    selected = building.BuildingId;
            }
            SelectBuilding(selected);
        }

        public void SelectBuilding(int buildingId)
        {
            SelectedBuildingId = buildingId;
            game.SetSelectedBuilding(buildingId);
            Prompt = buildingId == 0
                ? "R: route  |  Z: parcelles  |  B: camp forestier  |  Cliquez un chantier"
                : $"Chantier {buildingId} selectionne: choisissez sa priorite";
        }

        public void SetSelectedPriority(int priority)
        {
            if (SelectedBuildingId == 0)
            {
                Prompt = "Selectionnez d'abord un chantier";
                return;
            }
            var result = game.Submit(CityCommand.SetPriority(SelectedBuildingId, priority));
            Prompt = result.accepted
                ? $"Priorite du chantier {SelectedBuildingId}: {priority}"
                : $"Priorite refusee : {CityLabGame.DescribeReason(result.reason)}";
        }

        void HandleRoadClick(Ray ray)
        {
            if (!Physics.Raycast(ray, out var hit, 1000f))
            {
                Prompt = "Route refusee: aucun terrain sous le curseur";
                return;
            }
            var point = hit.point;
            point.y = 0f;
            if (!hasRoadStart)
            {
                roadStart = point;
                hasRoadStart = true;
                EnsureRoadPreview();
                Prompt = "Route: cliquez le point d'arrivee";
                return;
            }

            var result = game.Submit(CityCommand.DrawRoad(roadStart, point));
            hasRoadStart = false;
            Prompt = result.accepted
                ? "Route creee. Z puis clic sur la route pour lotir."
                : $"Route refusee : {CityLabGame.DescribeReason(result.reason)}";
            if (roadPreview != null) roadPreview.SetActive(false);
        }

        void EnsureRoadPreview()
        {
            if (roadPreview != null)
                return;
            roadPreview = new GameObject("Road placement preview");
            roadPreview.name = "Road placement preview";
            var baseMaterial = Resources.Load<Material>("CityLabBaseMaterial");
            roadPreviewMaterial = new Material(baseMaterial) { name = "Runtime Road Preview" };
            roadPreviewMaterial.SetFloat("_Surface", 1f);
            roadPreviewMaterial.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha);
            roadPreviewMaterial.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
            roadPreviewMaterial.SetFloat("_ZWrite", 0f);
            roadPreviewMaterial.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            roadPreviewMaterial.renderQueue = 3000;
            var line = roadPreview.AddComponent<LineRenderer>();
            line.useWorldSpace = true;
            line.widthMultiplier = 4.8f;
            line.numCornerVertices = 3;
            line.numCapVertices = 3;
            line.textureMode = LineTextureMode.Tile;
            line.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            line.receiveShadows = false;
            line.sharedMaterial = roadPreviewMaterial;
        }

        void UpdateRoadPreview(Vector2 pointer)
        {
            if (Mode != CityToolMode.DrawRoad || !hasRoadStart)
            {
                if (roadPreview != null) roadPreview.SetActive(false);
                return;
            }
            EnsureRoadPreview();
            var ray = game.WorldCamera.ScreenPointToRay(pointer);
            if (!Physics.Raycast(ray, out var hit, 1000f))
            {
                roadPreview.SetActive(false);
                return;
            }
            var end = hit.point;
            end.y = 0f;
            var delta = end - roadStart;
            var length = delta.magnitude;
            if (length < 0.01f)
            {
                roadPreview.SetActive(false);
                return;
            }
            roadPreview.SetActive(true);
            var line = roadPreview.GetComponent<LineRenderer>();
            var segments = Mathf.Clamp(Mathf.CeilToInt(length / 2.5f), 2, 96);
            line.positionCount = segments + 1;
            for (var i = 0; i <= segments; i++)
            {
                var position = Vector3.Lerp(roadStart, end, i / (float)segments);
                position.y = terrain != null
                    ? terrain.SampleHeight(position) + terrain.transform.position.y + 0.09f
                    : 0.09f;
                line.SetPosition(i, position);
            }
            var valid = length >= 4f && length <= 150f && Mathf.Abs(end.x) <= 250f && Mathf.Abs(end.z) <= 250f;
            roadPreviewMaterial.color = valid
                ? new Color(0.32f, 0.72f, 0.30f, 0.82f)
                : new Color(0.88f, 0.20f, 0.14f, 0.88f);
        }

        void HandleZoneClick(Ray ray)
        {
            if (!Physics.Raycast(ray, out var hit, 1000f))
            {
                Prompt = "Aucune route sous le curseur";
                return;
            }
            var road = hit.collider.GetComponentInParent<RoadView>();
            if (road == null)
            {
                Prompt = "Selectionnez directement une route";
                return;
            }
            var result = game.Submit(CityCommand.ZoneResidential(road.RoadId));
            Prompt = result.accepted
                ? "Parcelles creees: les foyers lancent leurs chantiers"
                : $"Lotissement refuse : {CityLabGame.DescribeReason(result.reason)}";
        }

        void HandleLumberCampClick(Ray ray)
        {
            if (!Physics.Raycast(ray, out var hit, 1000f))
            {
                Prompt = "Camp refuse: aucun terrain sous le curseur";
                return;
            }
            var point = hit.point;
            point.y = 0f;
            var result = game.Submit(CityCommand.PlaceLumberCamp(point));
            if (result.accepted)
            {
                SetMode(CityToolMode.Inspect);
                Prompt = "Camp forestier fonde: deux habitants produisent du bois";
            }
            else
            {
                Prompt = $"Camp refuse : {CityLabGame.DescribeReason(result.reason)}";
            }
        }

        void HandleBuildingClick(Ray ray)
        {
            if (!Physics.Raycast(ray, out var hit, 1000f))
            {
                Prompt = "Bâtiment refusé : aucun terrain sous le curseur";
                return;
            }
            var point = hit.point;
            point.y = 0f;
            var result = game.Submit(CityCommand.PlaceBuilding(SelectedArchetype, point));
            if (result.accepted)
            {
                var label = game.Catalog.Get(SelectedArchetype).label;
                SetMode(CityToolMode.Inspect);
                Prompt = label + " fondé : le chantier attend ses matériaux";
            }
            else
            {
                Prompt = "Bâtiment refusé : " + CityLabGame.DescribeReason(result.reason);
            }
        }

        void UpdateBuildingPreview(Vector2 pointer)
        {
            if (Mode != CityToolMode.PlaceBuilding)
            {
                if (buildingPreview != null) buildingPreview.SetActive(false);
                return;
            }
            EnsureBuildingPreview();
            var ray = game.WorldCamera.ScreenPointToRay(pointer);
            if (!Physics.Raycast(ray, out var hit, 1000f))
            {
                buildingPreview.SetActive(false);
                return;
            }
            var definition = game.Catalog.Get(SelectedArchetype);
            var position = hit.point;
            var valid = Mathf.Abs(position.x) <= LocalCitySimulation.MapHalfExtent - definition.footprintWidth * 0.5f &&
                        Mathf.Abs(position.z) <= LocalCitySimulation.MapHalfExtent - definition.footprintDepth * 0.5f;
            var snapshot = game.StateSource.GetSnapshot(1001);
            valid &= snapshot.stockWood - snapshot.reservedWood >= definition.woodCost;
            foreach (var existing in snapshot.buildings)
            {
                var existingDefinition = game.Catalog.Get(existing.archetype);
                var spacing = Mathf.Max(definition.placementSpacing, existingDefinition.placementSpacing);
                if (Vector2.Distance(new Vector2(position.x, position.z),
                        new Vector2(existing.position.x, existing.position.z)) < spacing)
                    valid = false;
            }
            foreach (var site in snapshot.productionSites)
                if (Vector2.Distance(new Vector2(position.x, position.z),
                        new Vector2(site.position.x, site.position.z)) < definition.placementSpacing)
                    valid = false;

            buildingPreview.SetActive(true);
            position.y = terrain != null
                ? terrain.SampleHeight(position) + terrain.transform.position.y + 0.06f
                : 0.06f;
            buildingPreview.transform.position = position;
            buildingPreview.transform.localScale = new Vector3(
                definition.footprintWidth, 0.08f, definition.footprintDepth);
            buildingPreviewMaterial.color = valid
                ? new Color(0.26f, 0.66f, 0.24f, 0.38f)
                : new Color(0.84f, 0.16f, 0.10f, 0.45f);
        }

        void EnsureBuildingPreview()
        {
            if (buildingPreview != null)
                return;
            buildingPreview = GameObject.CreatePrimitive(PrimitiveType.Cube);
            buildingPreview.name = "Building placement preview";
            var collider = buildingPreview.GetComponent<Collider>();
            if (collider != null) collider.enabled = false;
            var baseMaterial = Resources.Load<Material>("CityLabBaseMaterial");
            buildingPreviewMaterial = new Material(baseMaterial) { name = "Runtime Building Preview" };
            buildingPreviewMaterial.SetFloat("_Surface", 1f);
            buildingPreviewMaterial.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha);
            buildingPreviewMaterial.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
            buildingPreviewMaterial.SetFloat("_ZWrite", 0f);
            buildingPreviewMaterial.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            buildingPreviewMaterial.renderQueue = 3000;
            buildingPreview.GetComponent<Renderer>().sharedMaterial = buildingPreviewMaterial;
        }

        void UpdateLumberCampPreview(Vector2 pointer)
        {
            if (Mode != CityToolMode.PlaceLumberCamp)
            {
                if (lumberCampPreview != null) lumberCampPreview.SetActive(false);
                return;
            }
            EnsureLumberCampPreview();
            var ray = game.WorldCamera.ScreenPointToRay(pointer);
            if (!Physics.Raycast(ray, out var hit, 1000f))
            {
                lumberCampPreview.SetActive(false);
                return;
            }

            var position = hit.point;
            var planar = new Vector2(position.x, position.z);
            var definition = game.Catalog.Get(BuildingArchetype.LumberCamp);
            var valid = planar.magnitude >= definition.placementMinDistance &&
                        planar.magnitude <= definition.placementMaxDistance &&
                        Mathf.Abs(position.x) <= LocalCitySimulation.MapHalfExtent - 4f &&
                        Mathf.Abs(position.z) <= LocalCitySimulation.MapHalfExtent - 4f;
            var snapshot = game.StateSource.GetSnapshot(1001);
            valid &= snapshot.stockWood - snapshot.reservedWood >= definition.woodCost;
            foreach (var site in snapshot.productionSites)
            {
                var existing = site.position.ToVector3();
                if (Vector2.Distance(planar, new Vector2(existing.x, existing.z)) < definition.placementSpacing)
                    valid = false;
            }

            lumberCampPreview.SetActive(true);
            position.y = terrain != null
                ? terrain.SampleHeight(position) + terrain.transform.position.y + 0.06f
                : 0.06f;
            lumberCampPreview.transform.position = position;
            lumberCampPreviewMaterial.color = valid
                ? new Color(0.26f, 0.66f, 0.24f, 0.38f)
                : new Color(0.84f, 0.16f, 0.10f, 0.45f);
        }

        void EnsureLumberCampPreview()
        {
            if (lumberCampPreview != null)
                return;
            lumberCampPreview = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            lumberCampPreview.name = "Lumber camp placement preview";
            lumberCampPreview.transform.localScale = new Vector3(5.8f, 0.035f, 4.6f);
            var collider = lumberCampPreview.GetComponent<Collider>();
            if (collider != null) collider.enabled = false;
            var baseMaterial = Resources.Load<Material>("CityLabBaseMaterial");
            lumberCampPreviewMaterial = new Material(baseMaterial) { name = "Runtime Lumber Camp Preview" };
            lumberCampPreviewMaterial.SetFloat("_Surface", 1f);
            lumberCampPreviewMaterial.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha);
            lumberCampPreviewMaterial.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
            lumberCampPreviewMaterial.SetFloat("_ZWrite", 0f);
            lumberCampPreviewMaterial.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            lumberCampPreviewMaterial.renderQueue = 3000;
            lumberCampPreview.GetComponent<Renderer>().sharedMaterial = lumberCampPreviewMaterial;
        }
    }
}
