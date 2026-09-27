using System;
using UnityEngine;

namespace Victoria.CityMode
{
    /// <summary>
    /// Les quatre phases du contrat de construction v1. Elles restent le
    /// vocabulaire de la scierie publiée ; un bâtiment sous contrat v2 en porte
    /// jusqu'à huit et se pilote par <see cref="FactoryConstructionVisual.ShowProgress"/>.
    /// </summary>
    public enum FactoryConstructionStage : byte
    {
        Foundation = 1,
        Frame = 2,
        Roof = 3,
        Details = 4
    }

    /// <summary>
    /// Contrat visuel commun aux bâtiments générés par l'Asset Factory.
    ///
    /// Les couches sont cumulatives : une étape achevée reste visible aux
    /// suivantes. Le nombre d'étapes est une donnée du bâtiment, pas une
    /// constante : quatre pour le contrat v1, jusqu'à huit pour le v2. Il était
    /// écrit ici comme ailleurs, et un mur entier apparaissait d'un coup.
    /// </summary>
    public sealed class FactoryConstructionVisual : MonoBehaviour
    {
        [SerializeField] GameObject[] stageRoots = Array.Empty<GameObject>();

        /// <summary>
        /// Borne haute de progrès de chaque étape, telle que le contrat la
        /// déclare. La simulation avance par <see cref="BuildingPhase"/>, qui
        /// n'a que quatre valeurs persistées ; c'est cet intervalle qui traduit
        /// son avancement en étapes visibles, quel qu'en soit le nombre.
        /// </summary>
        [SerializeField] float[] stageProgress = Array.Empty<float>();

        public int StageCount => stageRoots?.Length ?? 0;

        /// <summary>Nombre d'étapes actuellement visibles.</summary>
        public int VisibleStageCount
        {
            get
            {
                var visible = 0;
                for (var index = 0; index < StageCount; index++)
                    if (stageRoots[index] != null && stageRoots[index].activeSelf)
                        visible++;
                return visible;
            }
        }

        public GameObject StageRoot(int index) =>
            index >= 0 && index < StageCount ? stageRoots[index] : null;

        public float StageProgress(int index) =>
            stageProgress != null && index >= 0 && index < stageProgress.Length
                ? stageProgress[index]
                : (index + 1f) / Mathf.Max(1, StageCount);

        public void Configure(GameObject[] roots) => Configure(roots, null);

        public void Configure(GameObject[] roots, float[] progress)
        {
            stageRoots = roots ?? Array.Empty<GameObject>();
            if (progress != null && progress.Length == stageRoots.Length)
            {
                stageProgress = progress;
            }
            else
            {
                // Sans intervalle déclaré, les étapes se partagent le chantier à
                // parts égales. C'est une valeur de repli, pas le contrat.
                stageProgress = new float[stageRoots.Length];
                for (var index = 0; index < stageRoots.Length; index++)
                    stageProgress[index] = (index + 1f) / Mathf.Max(1, stageRoots.Length);
            }
            ShowStage(stageRoots.Length);
        }

        /// <summary>Montrer les <paramref name="completedStages"/> premières étapes.</summary>
        public void ShowStage(int completedStages)
        {
            var visibleCount = Mathf.Clamp(completedStages, 0, StageCount);
            for (var index = 0; index < StageCount; index++)
                if (stageRoots[index] != null)
                    stageRoots[index].SetActive(index < visibleCount);
        }

        /// <summary>
        /// Chemin v1 : une phase du contrat à quatre étapes. Le rang de la
        /// phase est le nombre d'étapes achevées ; il ne passe pas par le
        /// progrès, dont les intervalles v1 ne sont pas réguliers.
        /// </summary>
        public void ShowStage(FactoryConstructionStage completedStage) =>
            ShowStage((int)completedStage);

        /// <summary>
        /// Montrer le chantier à un avancement donné, entre 0 et 1. Une étape
        /// est visible dès que son intervalle est franchi.
        /// </summary>
        public void ShowProgress(float progress)
        {
            var clamped = Mathf.Clamp01(progress);
            var visibleCount = 0;
            for (var index = 0; index < StageCount; index++)
                if (StageProgress(index) <= clamped + 0.0001f)
                    visibleCount = index + 1;
            ShowStage(visibleCount);
        }
    }

    /// <summary>
    /// Échafaudage runtime déterministe des chantiers civiques. Son état est
    /// entièrement dérivé de la phase et du terrassement persistés du bâtiment.
    /// </summary>
    public sealed class ConstructionScaffoldVisual : MonoBehaviour
    {
        [SerializeField] GameObject scaffoldRoot;
        [SerializeField] GameObject[] phaseRoots = Array.Empty<GameObject>();
        [SerializeField] GameObject selectionMarkers;
        bool isSelected;

        public BuildingPhase CurrentPhase { get; private set; } = BuildingPhase.Foundation;
        public bool TerrainPrepared { get; private set; }
        public bool IsSelected => isSelected;
        public bool IsVisible => scaffoldRoot != null && scaffoldRoot.activeInHierarchy;
        public int VisibleStageCount
        {
            get
            {
                if (!IsVisible || phaseRoots == null)
                    return 0;
                var count = 0;
                foreach (var phaseRoot in phaseRoots)
                    if (phaseRoot != null && phaseRoot.activeInHierarchy)
                        count++;
                return count;
            }
        }

        public void Initialize(float footprintWidth, float footprintDepth,
            Material timberMaterial, Material accentMaterial)
        {
            if (scaffoldRoot != null)
                return;

            scaffoldRoot = new GameObject("Construction scaffolding");
            scaffoldRoot.transform.SetParent(transform, false);
            phaseRoots = new GameObject[4];
            for (var index = 0; index < phaseRoots.Length; index++)
            {
                phaseRoots[index] = new GameObject($"Scaffold phase {index + 1}");
                phaseRoots[index].transform.SetParent(scaffoldRoot.transform, false);
            }

            var halfWidth = Mathf.Max(2.5f, footprintWidth * 0.5f + 0.75f);
            var halfDepth = Mathf.Max(2.5f, footprintDepth * 0.5f + 0.75f);
            BuildFoundationStage(phaseRoots[0].transform, halfWidth, halfDepth, timberMaterial);
            BuildFramingStage(phaseRoots[1].transform, halfWidth, halfDepth, timberMaterial);
            BuildRoofingStage(phaseRoots[2].transform, halfWidth, halfDepth, timberMaterial);
            BuildDetailingStage(phaseRoots[3].transform, halfWidth, halfDepth,
                timberMaterial, accentMaterial);
            selectionMarkers = BuildSelectionMarkers(scaffoldRoot.transform,
                halfWidth, halfDepth, accentMaterial);
            Refresh(BuildingPhase.Foundation, false);
        }

        public void Refresh(BuildingPhase phase, bool terrainPrepared)
        {
            CurrentPhase = phase;
            TerrainPrepared = terrainPrepared;
            var visibleStages = phase switch
            {
                BuildingPhase.Foundation => terrainPrepared ? 1 : 0,
                BuildingPhase.Framing => 2,
                BuildingPhase.Roofing => 3,
                BuildingPhase.Detailing => 4,
                _ => 0
            };
            if (scaffoldRoot != null)
                scaffoldRoot.SetActive(visibleStages > 0);
            for (var index = 0; index < (phaseRoots?.Length ?? 0); index++)
                if (phaseRoots[index] != null)
                    phaseRoots[index].SetActive(index < visibleStages);
            RefreshSelectionMarkers();
        }

        public void SetSelected(bool selected)
        {
            isSelected = selected;
            RefreshSelectionMarkers();
        }

        void RefreshSelectionMarkers()
        {
            if (selectionMarkers != null)
                selectionMarkers.SetActive(isSelected && IsVisible);
        }

        static void BuildFoundationStage(Transform parent, float halfWidth, float halfDepth,
            Material timberMaterial)
        {
            foreach (var corner in Corners(halfWidth, halfDepth))
                AddVerticalBeam(parent, corner + Vector3.up * 0.65f, 1.3f, 0.18f, timberMaterial);
            AddPerimeter(parent, halfWidth, halfDepth, 0.75f, 0.16f, timberMaterial);
        }

        static void BuildFramingStage(Transform parent, float halfWidth, float halfDepth,
            Material timberMaterial)
        {
            foreach (var corner in Corners(halfWidth, halfDepth))
                AddVerticalBeam(parent, corner + Vector3.up * 2.35f, 3.4f, 0.18f, timberMaterial);
            AddPerimeter(parent, halfWidth, halfDepth, 2.05f, 0.17f, timberMaterial);
            AddDeck(parent, halfWidth, halfDepth, 1.82f, timberMaterial);
        }

        static void BuildRoofingStage(Transform parent, float halfWidth, float halfDepth,
            Material timberMaterial)
        {
            foreach (var corner in Corners(halfWidth, halfDepth))
                AddVerticalBeam(parent, corner + Vector3.up * 4.45f, 2.6f, 0.18f, timberMaterial);
            AddPerimeter(parent, halfWidth, halfDepth, 4.65f, 0.17f, timberMaterial);
            AddDeck(parent, halfWidth, halfDepth, 4.35f, timberMaterial);
            AddBeamBetween(parent,
                new Vector3(-halfWidth, 0.25f, -halfDepth),
                new Vector3(-halfWidth, 4.35f, -halfDepth), 0.16f, timberMaterial);
        }

        static void BuildDetailingStage(Transform parent, float halfWidth, float halfDepth,
            Material timberMaterial, Material accentMaterial)
        {
            AddBeamBetween(parent,
                new Vector3(-halfWidth, 0.85f, -halfDepth),
                new Vector3(halfWidth, 4.45f, -halfDepth), 0.13f, timberMaterial);
            AddBeamBetween(parent,
                new Vector3(halfWidth, 0.85f, halfDepth),
                new Vector3(-halfWidth, 4.45f, halfDepth), 0.13f, timberMaterial);
            AddVerticalBeam(parent, new Vector3(halfWidth + 0.7f, 3.1f, 0f),
                6.2f, 0.20f, timberMaterial);
            AddBeamBetween(parent,
                new Vector3(halfWidth + 0.7f, 5.9f, -0.1f),
                new Vector3(halfWidth + 0.7f, 5.9f, -2.1f), 0.16f, timberMaterial);
            AddVerticalBeam(parent, new Vector3(halfWidth + 0.7f, 4.35f, -2.1f),
                3.1f, 0.06f, accentMaterial);
        }

        static GameObject BuildSelectionMarkers(Transform parent, float halfWidth, float halfDepth,
            Material accentMaterial)
        {
            var root = new GameObject("Selected scaffold markers");
            root.transform.SetParent(parent, false);
            foreach (var corner in Corners(halfWidth, halfDepth))
            {
                var marker = CreatePart("Selection pennant", root.transform,
                    corner + Vector3.up * 5.95f, new Vector3(0.42f, 0.24f, 0.06f),
                    accentMaterial);
                marker.transform.localRotation = Quaternion.Euler(0f, 35f, 18f);
            }
            root.SetActive(false);
            return root;
        }

        static Vector3[] Corners(float halfWidth, float halfDepth) => new[]
        {
            new Vector3(-halfWidth, 0f, -halfDepth),
            new Vector3(-halfWidth, 0f, halfDepth),
            new Vector3(halfWidth, 0f, halfDepth),
            new Vector3(halfWidth, 0f, -halfDepth)
        };

        static void AddPerimeter(Transform parent, float halfWidth, float halfDepth,
            float height, float thickness, Material material)
        {
            AddBeamBetween(parent, new Vector3(-halfWidth, height, -halfDepth),
                new Vector3(halfWidth, height, -halfDepth), thickness, material);
            AddBeamBetween(parent, new Vector3(-halfWidth, height, halfDepth),
                new Vector3(halfWidth, height, halfDepth), thickness, material);
            AddBeamBetween(parent, new Vector3(-halfWidth, height, -halfDepth),
                new Vector3(-halfWidth, height, halfDepth), thickness, material);
            AddBeamBetween(parent, new Vector3(halfWidth, height, -halfDepth),
                new Vector3(halfWidth, height, halfDepth), thickness, material);
        }

        static void AddDeck(Transform parent, float halfWidth, float halfDepth,
            float height, Material material)
        {
            CreatePart("Scaffold deck north", parent,
                new Vector3(0f, height, halfDepth),
                new Vector3(halfWidth * 2f + 0.35f, 0.11f, 0.72f), material);
            CreatePart("Scaffold deck south", parent,
                new Vector3(0f, height, -halfDepth),
                new Vector3(halfWidth * 2f + 0.35f, 0.11f, 0.72f), material);
            CreatePart("Scaffold deck west", parent,
                new Vector3(-halfWidth, height, 0f),
                new Vector3(0.72f, 0.11f, halfDepth * 2f + 0.35f), material);
            CreatePart("Scaffold deck east", parent,
                new Vector3(halfWidth, height, 0f),
                new Vector3(0.72f, 0.11f, halfDepth * 2f + 0.35f), material);
        }

        static void AddVerticalBeam(Transform parent, Vector3 center, float height,
            float thickness, Material material) =>
            CreatePart("Scaffold post", parent, center,
                new Vector3(thickness, height, thickness), material);

        static void AddBeamBetween(Transform parent, Vector3 start, Vector3 end,
            float thickness, Material material)
        {
            var delta = end - start;
            if (delta.sqrMagnitude <= 0.0001f)
                return;
            var beam = CreatePart("Scaffold rail", parent, (start + end) * 0.5f,
                new Vector3(thickness, delta.magnitude, thickness), material);
            beam.transform.localRotation = Quaternion.FromToRotation(Vector3.up, delta.normalized);
        }

        static GameObject CreatePart(string label, Transform parent, Vector3 localPosition,
            Vector3 localScale, Material material)
        {
            var part = GameObject.CreatePrimitive(PrimitiveType.Cube);
            part.name = label;
            part.transform.SetParent(parent, false);
            part.transform.localPosition = localPosition;
            part.transform.localScale = localScale;
            var renderer = part.GetComponent<Renderer>();
            if (renderer != null && material != null)
                renderer.sharedMaterial = material;
            var collider = part.GetComponent<Collider>();
            if (collider != null)
                collider.enabled = false;
            return part;
        }
    }
}
