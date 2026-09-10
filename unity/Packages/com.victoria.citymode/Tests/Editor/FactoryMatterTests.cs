using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;

namespace Victoria.CityMode.Tests
{
    /// <summary>
    /// La porte que M1-ASSET-06 n'avait pas.
    ///
    /// Les 21 bâtiments passaient toutes les portes techniques et les deux
    /// suites EditMode en étant visuellement refusés : rien ne vérifiait que la
    /// matière arrive jusqu'à l'asset publié. Ces tests lisent ce que Unity a
    /// réellement importé. Leur équivalent hors Unity est
    /// Tools/AssetFactory/matter_gate.py, règles M-1 et M-2.
    /// </summary>
    public sealed class FactoryMatterTests
    {
        const string TrimFolder = "Assets/CityLabHost/Adapted/Factory/Textures/CityLabTrimV2";
        const string PrefabRoot = "Assets/CityLabHost/Adapted/Factory/Prefabs";

        static readonly string[] TrimMatteredPrefabs =
        {
            PrefabRoot + "/CityLab_building_residence_frontier_01_A.prefab",
            PrefabRoot + "/CityLab_building_residence_frontier_01_B.prefab",
            PrefabRoot + "/CityLab_building_residence_frontier_01_C.prefab"
        };

        /// <summary>Rôle de carte -> (sRGB, type d'import) exigés. Miroir de M-2.</summary>
        static readonly Dictionary<string, (bool sRGB, TextureImporterType Type)> Roles =
            new Dictionary<string, (bool, TextureImporterType)>
            {
                { "BaseColor", (true, TextureImporterType.Default) },
                { "Normal", (false, TextureImporterType.NormalMap) },
                { "AO", (false, TextureImporterType.Default) },
                { "Roughness", (false, TextureImporterType.Default) },
                { "Metallic", (false, TextureImporterType.Default) },
                { "VariationMask", (false, TextureImporterType.Default) }
            };

        static IEnumerable<string> TrimMaps() =>
            AssetDatabase.FindAssets("t:Texture2D CityLabTrim", new[] { TrimFolder })
                .Select(AssetDatabase.GUIDToAssetPath)
                .Where(path => path.EndsWith(".png"))
                .Distinct()
                .OrderBy(path => path);

        [Test]
        public void TrimAtlas_PublishesSixMapsImportedForTheirRole()
        {
            var maps = TrimMaps().ToArray();
            Assert.AreEqual(6, maps.Length, TrimFolder);
            foreach (var path in maps)
            {
                var name = System.IO.Path.GetFileNameWithoutExtension(path);
                var role = name.Substring(name.LastIndexOf('_') + 1);
                Assert.IsTrue(Roles.ContainsKey(role), path);
                var importer = AssetImporter.GetAtPath(path) as TextureImporter;
                Assert.IsNotNull(importer, path);

                var wanted = Roles[role];
                // Une carte de données décodée en gamma, ou un normal map non
                // déballé, éclaire faux même quand le maillage la porte.
                Assert.AreEqual(wanted.Type, importer.textureType, path);
                Assert.AreEqual(wanted.sRGB, importer.sRGBTexture, path);
            }
        }

        [Test]
        public void ResidencePrefabs_CarryTheTrimAtlasAndNotAFlatColour()
        {
            var trimTextures = new HashSet<Texture>(
                TrimMaps().Select(AssetDatabase.LoadAssetAtPath<Texture>));
            Assert.AreEqual(6, trimTextures.Count);

            foreach (var prefabPath in TrimMatteredPrefabs)
            {
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
                Assert.IsNotNull(prefab, prefabPath);

                var materials = prefab.GetComponentsInChildren<Renderer>(true)
                    .SelectMany(renderer => renderer.sharedMaterials)
                    .Where(material => material != null)
                    .Distinct()
                    .ToArray();
                Assert.IsNotEmpty(materials, prefabPath);

                foreach (var material in materials)
                {
                    var albedo = material.HasProperty("_BaseMap")
                        ? material.GetTexture("_BaseMap") : null;
                    Assert.IsNotNull(albedo,
                        prefabPath + " -> " + material.name + " : aplat sans carte");
                    Assert.IsTrue(trimTextures.Contains(albedo),
                        prefabPath + " -> " + material.name + " : carte hors de l'atlas publié");
                    Assert.IsNotNull(material.GetTexture("_BumpMap"),
                        prefabPath + " -> " + material.name + " : sans normal map");
                }
            }
        }

        /// <summary>
        /// Le decoupage de construction est une donnee du batiment, pas une
        /// constante : quatre phases sous le contrat v1, huit etapes sous le v2.
        /// Ce qui ne bouge pas, c'est qu'une etape porte un groupe de LOD et que
        /// ce groupe expose trois distances -- une etape qui n'a rien a montrer
        /// de loin y garde son dernier niveau au lieu de disparaitre.
        /// </summary>
        [Test]
        public void ResidencePrefabs_KeepOneLodGroupPerConstructionStage()
        {
            foreach (var prefabPath in TrimMatteredPrefabs)
            {
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
                Assert.IsNotNull(prefab, prefabPath);
                var construction = prefab.GetComponent<FactoryConstructionVisual>();
                Assert.IsNotNull(construction, prefabPath);
                Assert.GreaterOrEqual(construction.StageCount, 5, prefabPath);
                var groups = prefab.GetComponentsInChildren<LODGroup>(true);
                Assert.AreEqual(construction.StageCount, groups.Length, prefabPath);
                foreach (var group in groups)
                    Assert.AreEqual(3, group.GetLODs().Length, prefabPath);
            }
        }
    }
}
