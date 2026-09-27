using System.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;

namespace Victoria.CityMode.Tests
{
    public sealed class FactoryUnityIntegrationTests
    {
        const string LibraryPath = "Assets/CityLabHost/Resources/CityLabVisualLibrary.asset";

        [Test]
        public void BuildingPilot_HasEightFamiliesThreeVariantsAndValidPhaseLods()
        {
            var library = AssetDatabase.LoadAssetAtPath<CityVisualLibrary>(LibraryPath);
            var catalog = BuildingCatalog.LoadDefault();
            Assert.IsNotNull(library);
            var families = new[]
            {
                library.lumberCampPrefabs, library.housePrefabs, library.granaryPrefabs,
                library.warehousePrefabs, library.marketPrefabs, library.blacksmithPrefabs,
                library.barnPrefabs, library.chapelPrefabs
            };
            Assert.AreEqual(8, families.Length);
            foreach (var family in families)
            {
                Assert.IsNotNull(family);
                Assert.AreEqual(3, family.Length);
                foreach (var prefab in family)
                {
                    Assert.IsNotNull(prefab);
                    Assert.AreEqual(0, GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(prefab));
                    var construction = prefab.GetComponent<FactoryConstructionVisual>();
                    Assert.IsNotNull(construction);
                    // Le nombre d'etapes est une donnee du batiment : quatre
                    // sous le contrat de construction v1, jusqu'a huit sous le
                    // v2. Il etait ecrit ici comme ailleurs.
                    Assert.GreaterOrEqual(construction.StageCount, 4, prefab.name);
                    Assert.LessOrEqual(construction.StageCount, 8, prefab.name);
                    Assert.AreEqual(construction.StageCount,
                        prefab.GetComponentsInChildren<LODGroup>(true).Length, prefab.name);
                }
            }
            foreach (var definition in catalog.Definitions)
                Assert.IsNotNull(library.SelectBuildingPrefab(definition.visualFamily, 1001),
                    definition.visualFamily);
        }

        [Test]
        public void CharacterRoles_HaveHumanoidAvatarSingleLodAuthorityAndController()
        {
            var library = AssetDatabase.LoadAssetAtPath<CityVisualLibrary>(LibraryPath);
            Assert.IsNotNull(library);
            Assert.IsNotNull(library.villagerAnimatorController);
            Assert.IsNotNull(library.villagerPrefabs);
            Assert.AreEqual(8, library.villagerPrefabs.Length);
            Assert.AreEqual(8, library.villagerPrefabs.Distinct().Count());
            foreach (var prefab in library.villagerPrefabs)
            {
                Assert.IsNotNull(prefab);
                Assert.AreEqual(0, GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(prefab));
                Assert.AreEqual(1, prefab.GetComponentsInChildren<LODGroup>(true).Length);
                var animator = prefab.GetComponentInChildren<Animator>(true);
                Assert.IsNotNull(animator);
                Assert.IsNotNull(animator.avatar);
                Assert.IsTrue(animator.avatar.isValid);
                Assert.IsTrue(animator.avatar.isHuman);
            }
        }
    }
}
