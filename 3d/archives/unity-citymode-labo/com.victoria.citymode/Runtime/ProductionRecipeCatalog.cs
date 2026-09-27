using System;
using System.Collections.Generic;

namespace Victoria.CityMode
{
    public sealed class ProductionRecipeDefinition
    {
        public ProductionSiteKind kind;
        public CityResourceKind inputA;
        public int inputAQuantity;
        public CityResourceKind inputB;
        public int inputBQuantity;
        public CityResourceKind output;
        public int outputQuantity;
        public float workSeconds;
        public int defaultRawReserve;
    }

    public sealed class ProductionRecipeCatalog
    {
        static readonly ProductionRecipeDefinition[] Defaults =
        {
            Define(ProductionSiteKind.Sawmill, CityResourceKind.Wood, 2, 0, 0,
                CityResourceKind.Planks, 1, 5f),
            Define(ProductionSiteKind.Quarry, 0, 0, 0, 0,
                CityResourceKind.Stone, 1, 8f, 80),
            Define(ProductionSiteKind.Forge, CityResourceKind.Stone, 2,
                CityResourceKind.Wood, 1, CityResourceKind.Tools, 1, 10f),
            Define(ProductionSiteKind.Mill, CityResourceKind.Food, 2, 0, 0,
                CityResourceKind.Food, 3, 6f),
            Define(ProductionSiteKind.Oven, CityResourceKind.Food, 2,
                CityResourceKind.Wood, 1, CityResourceKind.Food, 3, 7f),
            Define(ProductionSiteKind.Weaving, CityResourceKind.Food, 2,
                CityResourceKind.Tools, 1, CityResourceKind.Textile, 1, 9f),
            Define(ProductionSiteKind.Workshop, CityResourceKind.Planks, 2,
                CityResourceKind.Textile, 1, CityResourceKind.Tools, 1, 9f)
        };

        readonly Dictionary<ProductionSiteKind, ProductionRecipeDefinition> definitions =
            new Dictionary<ProductionSiteKind, ProductionRecipeDefinition>();

        public ProductionRecipeCatalog()
        {
            foreach (var definition in Defaults)
                definitions.Add(definition.kind, definition);
        }

        public int Count => definitions.Count;
        public IEnumerable<ProductionRecipeDefinition> Definitions => definitions.Values;

        public ProductionRecipeDefinition Get(ProductionSiteKind kind) =>
            definitions.TryGetValue(kind, out var definition)
                ? definition
                : throw new KeyNotFoundException("Recette de production inconnue: " + kind);

        public bool TryGet(ProductionSiteKind kind, out ProductionRecipeDefinition definition) =>
            definitions.TryGetValue(kind, out definition);

        static ProductionRecipeDefinition Define(ProductionSiteKind kind,
            CityResourceKind inputA, int inputAQuantity,
            CityResourceKind inputB, int inputBQuantity,
            CityResourceKind output, int outputQuantity, float workSeconds,
            int rawReserve = 0) => new ProductionRecipeDefinition
        {
            kind = kind,
            inputA = inputA,
            inputAQuantity = inputAQuantity,
            inputB = inputB,
            inputBQuantity = inputBQuantity,
            output = output,
            outputQuantity = outputQuantity,
            workSeconds = workSeconds,
            defaultRawReserve = rawReserve
        };
    }
}
