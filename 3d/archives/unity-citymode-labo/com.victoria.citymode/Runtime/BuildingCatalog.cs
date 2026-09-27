using System;
using System.Collections.Generic;
using UnityEngine;

namespace Victoria.CityMode
{
    public enum BuildingArchetype : byte
    {
        Unknown = 0,
        Residence = 1,
        LumberCamp = 2,
        Granary = 3,
        Warehouse = 4,
        Market = 5,
        Blacksmith = 6,
        Barn = 7,
        Chapel = 8
    }

    [Serializable]
    public sealed class BuildingDefinition
    {
        public string id;
        public string label;
        public BuildingArchetype archetype;
        public int woodCost;
        public float footprintWidth;
        public float footprintDepth;
        public int maxWorkers;
        public float constructionWork;
        public float productionWork;
        public int initialResource;
        public int serviceCapacity;
        public float placementMinDistance;
        public float placementMaxDistance;
        public float placementSpacing;
        public string inputResource;
        public string outputResource;
        public string visualFamily;
        public float[] phaseThresholds;
    }

    [Serializable]
    public sealed class BuildingCatalogDocument
    {
        public int schemaVersion;
        public List<BuildingDefinition> definitions = new List<BuildingDefinition>();
    }

    public sealed class BuildingCatalog
    {
        public const int CurrentSchemaVersion = 1;
        readonly Dictionary<BuildingArchetype, BuildingDefinition> definitions;

        BuildingCatalog(Dictionary<BuildingArchetype, BuildingDefinition> definitions)
        {
            this.definitions = definitions;
        }

        public int Count => definitions.Count;
        public IEnumerable<BuildingDefinition> Definitions => definitions.Values;

        public static BuildingCatalog LoadDefault()
        {
            var asset = Resources.Load<TextAsset>("CityBuildingCatalog");
            if (asset == null)
                throw new InvalidOperationException("Resources/CityBuildingCatalog.json is missing.");
            return FromJson(asset.text);
        }

        public static BuildingCatalog FromJson(string json)
        {
            if (string.IsNullOrWhiteSpace(json))
                throw new ArgumentException("Building catalog JSON is empty.", nameof(json));
            var document = JsonUtility.FromJson<BuildingCatalogDocument>(json);
            if (document == null || document.schemaVersion != CurrentSchemaVersion)
                throw new ArgumentException("Building catalog schema is unsupported.", nameof(json));
            if (document.definitions == null || document.definitions.Count != 8)
                throw new ArgumentException("Building catalog must contain exactly eight definitions.", nameof(json));

            var indexed = new Dictionary<BuildingArchetype, BuildingDefinition>();
            var ids = new HashSet<string>(StringComparer.Ordinal);
            foreach (var definition in document.definitions)
            {
                Validate(definition, json);
                if (!indexed.TryAdd(definition.archetype, definition) || !ids.Add(definition.id))
                    throw new ArgumentException("Building catalog contains a duplicate id or archetype.", nameof(json));
            }
            return new BuildingCatalog(indexed);
        }

        public BuildingDefinition Get(BuildingArchetype archetype)
        {
            if (archetype == BuildingArchetype.Unknown)
                archetype = BuildingArchetype.Residence;
            if (!definitions.TryGetValue(archetype, out var definition))
                throw new KeyNotFoundException("Building definition is missing: " + archetype);
            return definition;
        }

        static void Validate(BuildingDefinition definition, string parameterName)
        {
            if (definition == null || definition.archetype == BuildingArchetype.Unknown ||
                !Enum.IsDefined(typeof(BuildingArchetype), definition.archetype) ||
                string.IsNullOrWhiteSpace(definition.id) || string.IsNullOrWhiteSpace(definition.label) ||
                string.IsNullOrWhiteSpace(definition.visualFamily))
                throw new ArgumentException("Building definition identity is invalid.", nameof(parameterName));
            if (definition.woodCost < 0 || definition.footprintWidth <= 0f ||
                definition.footprintDepth <= 0f || definition.maxWorkers < 0 ||
                definition.constructionWork <= 0f || definition.productionWork < 0f ||
                definition.initialResource < 0 || definition.serviceCapacity < 0)
                throw new ArgumentException("Building definition budgets are invalid.", nameof(parameterName));
            if (definition.phaseThresholds == null || definition.phaseThresholds.Length != 4)
                throw new ArgumentException("Building definition requires four phase thresholds.", nameof(parameterName));
            var previous = 0f;
            foreach (var threshold in definition.phaseThresholds)
            {
                if (threshold <= previous || threshold > 1f)
                    throw new ArgumentException("Building phase thresholds must be increasing.", nameof(parameterName));
                previous = threshold;
            }
            if (!Mathf.Approximately(previous, 1f))
                throw new ArgumentException("Building phase thresholds must end at one.", nameof(parameterName));
            if (definition.archetype == BuildingArchetype.LumberCamp &&
                (definition.maxWorkers <= 0 || definition.productionWork <= 0f ||
                 definition.initialResource <= 0 || definition.placementMinDistance < 0f ||
                 definition.placementMaxDistance <= definition.placementMinDistance ||
                 definition.placementSpacing <= 0f || string.IsNullOrWhiteSpace(definition.outputResource)))
                throw new ArgumentException("Lumber camp production definition is invalid.", nameof(parameterName));
        }
    }
}
