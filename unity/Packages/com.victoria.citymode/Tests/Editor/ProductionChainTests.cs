using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEngine;

namespace Victoria.CityMode.Tests
{
    public sealed class ProductionChainTests
    {
        [Test]
        public void CatalogDefinesSevenDeterministicRecipes()
        {
            var simulation = CreateSimulation();
            var recipes = simulation.ProductionRecipes.Definitions.ToArray();

            Assert.AreEqual(7, recipes.Length);
            CollectionAssert.AreEquivalent(new[]
            {
                ProductionSiteKind.Sawmill, ProductionSiteKind.Quarry,
                ProductionSiteKind.Forge, ProductionSiteKind.Mill,
                ProductionSiteKind.Oven, ProductionSiteKind.Weaving,
                ProductionSiteKind.Workshop
            }, recipes.Select(item => item.kind));
            Assert.IsTrue(recipes.All(item => item.output != 0 && item.outputQuantity > 0 &&
                item.workSeconds > 0f));
        }

        [Test]
        public void EveryRecipeConsumesInputsAndProducesItsLocalOutput()
        {
            var snapshot = BaseSnapshot(withBuilder: false);
            var catalog = new ProductionRecipeCatalog();
            var id = 1;
            foreach (var recipe in catalog.Definitions)
            {
                snapshot.productionSites.Add(new ProductionSiteState
                {
                    id = id++,
                    kind = recipe.kind,
                    position = CityPoint.From(new Vector3(id * 8f, 0f, 0f)),
                    assignedWorkers = 1,
                    maxWorkers = 1,
                    constructionPhase = BuildingPhase.Complete,
                    inputAStored = recipe.inputAQuantity,
                    inputBStored = recipe.inputBQuantity,
                    rawRemaining = recipe.defaultRawReserve
                });
            }
            var simulation = new LocalCitySimulation(snapshot);

            for (var tick = 0; tick < 110; tick++)
                simulation.Tick(0.1f);

            var after = simulation.GetSnapshot(1001);
            Assert.IsTrue(after.productionSites.All(item => item.totalBatches >= 1));
            Assert.IsTrue(after.productionSites.All(item => item.outputStored > 0));
            Assert.IsTrue(after.productionSites.All(item => item.inputAStored >= 0 &&
                item.inputBStored >= 0 && item.rawRemaining >= 0));
        }

        [Test]
        public void SawmillInputsAndPlankOutputsTravelThroughPhysicalLogistics()
        {
            var simulation = CreateSimulation();
            Assert.AreEqual(20, simulation.AddResource(CityResourceKind.Wood, 20));
            var siteId = simulation.AddProductionFacility(ProductionSiteKind.Sawmill,
                new Vector3(14f, 0f, -6f));
            var sawCargoInTransit = false;

            for (var tick = 0; tick < 12000 &&
                simulation.GetResource(CityResourceKind.Planks).quantity == 0; tick++)
            {
                simulation.Tick(0.1f);
                var snapshot = simulation.GetSnapshot(1001);
                sawCargoInTransit |= snapshot.villagers.Any(item => item.carryingWood > 0 &&
                    item.carryingResource != 0);
            }

            var after = simulation.GetSnapshot(1001);
            var site = after.productionSites.Find(item => item.id == siteId);
            Assert.IsTrue(sawCargoInTransit, "La chaîne doit observer une cargaison portée par un habitant.");
            Assert.Greater(site.totalBatches, 0);
            Assert.Greater(after.resources.Find(item => item.kind == CityResourceKind.Planks).quantity, 0);
            Assert.IsTrue(after.logisticsTasks.Any(item => item.resource == CityResourceKind.Planks &&
                item.sourceKind == LogisticsEndpointKind.ProductionSite &&
                item.destinationKind == LogisticsEndpointKind.GlobalStock &&
                item.deliveredQuantity > 0));
        }

        static LocalCitySimulation CreateSimulation() =>
            new LocalCitySimulation(BaseSnapshot(withBuilder: true));

        static CitySnapshot BaseSnapshot(bool withBuilder)
        {
            var snapshot = new CitySnapshot
            {
                cityId = 1001,
                seed = 140001,
                elapsedSeconds = 40f,
                employmentDay = -1,
                households = new List<HouseholdState>()
            };
            if (!withBuilder)
                return snapshot;
            snapshot.households.Add(new HouseholdState { id = 1, memberCount = 1 });
            snapshot.villagers.Add(new VillagerState
            {
                id = 1,
                householdId = 1,
                position = CityPoint.From(Vector3.zero)
            });
            snapshot.buildings.Add(new BuildingState
            {
                id = 1,
                archetype = BuildingArchetype.Residence,
                position = CityPoint.From(new Vector3(32f, 0f, 0f)),
                phase = BuildingPhase.Foundation,
                priority = 1,
                requiredWood = 6,
                workRemaining = 12f
            });
            return snapshot;
        }
    }
}
