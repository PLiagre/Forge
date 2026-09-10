using System;
using System.Collections.Generic;

namespace Victoria.CityMode
{
    public sealed class CityResourceDefinition
    {
        public CityResourceKind kind;
        public string key;
        public string unitKey;
        public int defaultCapacity;
        public int dailyLossPermille;
    }

    public sealed class CityResourceRegistry
    {
        static readonly CityResourceDefinition[] DefaultDefinitions =
        {
            Define(CityResourceKind.Wood, "wood", "log", 1000, 0),
            Define(CityResourceKind.Planks, "planks", "plank", 500, 0),
            Define(CityResourceKind.Stone, "stone", "block", 800, 0),
            Define(CityResourceKind.Food, "food", "ration", 120, 20),
            Define(CityResourceKind.Tools, "tools", "tool", 100, 1),
            Define(CityResourceKind.Textile, "textile", "bolt", 100, 1)
        };

        readonly Dictionary<CityResourceKind, CityResourceDefinition> definitions =
            new Dictionary<CityResourceKind, CityResourceDefinition>();

        public CityResourceRegistry(IEnumerable<CityResourceDefinition> source)
        {
            if (source == null)
                throw new ArgumentNullException(nameof(source));
            foreach (var definition in source)
            {
                if (definition == null || definition.kind == 0 ||
                    string.IsNullOrWhiteSpace(definition.key) ||
                    string.IsNullOrWhiteSpace(definition.unitKey) ||
                    definition.defaultCapacity < 0 || definition.dailyLossPermille < 0 ||
                    definition.dailyLossPermille > 1000 || definitions.ContainsKey(definition.kind))
                    throw new ArgumentException("Définition de ressource invalide ou dupliquée.", nameof(source));
                definitions.Add(definition.kind, definition);
            }
            foreach (CityResourceKind kind in Enum.GetValues(typeof(CityResourceKind)))
                if (kind != 0 && !definitions.ContainsKey(kind))
                    throw new ArgumentException("Registre de ressources incomplet.", nameof(source));
        }

        public int Count => definitions.Count;
        public IEnumerable<CityResourceDefinition> Definitions => definitions.Values;

        public CityResourceDefinition Get(CityResourceKind kind) =>
            definitions.TryGetValue(kind, out var definition)
                ? definition
                : throw new KeyNotFoundException("Ressource inconnue: " + kind);

        public static CityResourceRegistry CreateDefault() =>
            new CityResourceRegistry(DefaultDefinitions);

        static CityResourceDefinition Define(CityResourceKind kind, string key,
            string unitKey, int capacity, int lossPermille) => new CityResourceDefinition
        {
            kind = kind,
            key = key,
            unitKey = unitKey,
            defaultCapacity = capacity,
            dailyLossPermille = lossPermille
        };
    }
}
