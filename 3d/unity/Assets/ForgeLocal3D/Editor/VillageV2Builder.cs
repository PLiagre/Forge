using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace ForgeLocal3D
{
    // Un catalogue de prefabs partagés, puis les placements exportés par Blender.
    // Un LOD est une version moins détaillée affichée lorsque l'objet est petit à l'écran.
    public static class VillageV2Builder
    {
        static string Root = "Assets/ForgeLocal3D/V2";
        static string Output = "../local3d/v2/villages/";
        static bool Alpine;
        static bool Citadel;
        // Le désert emprunte la chaîne de la citadelle (matériaux, collisions, marche) sans son décor tiers.
        static bool Desert;
        static bool Lit => Citadel || Desert;
        static string Prefix => Desert ? "Forge_Desert_" : Citadel ? "Forge_Citadelle_" : Alpine ? "Forge_Alpin_" : "Forge_V2_";
        [Serializable] public class Matter { public string name, texture; public bool alpha; public float[] color; public float roughness; }
        [Serializable] public class Asset { public string id, kind; public int[] triangles; public float[] bounds_min, bounds_max; }
        [Serializable] public class Catalog { public Asset[] assets; public Matter[] materials; }
        [Serializable] public class Selection { public string[] variants; }
        [Serializable] public class Instance { public string id, asset, category; public float[] position, scale, color; public float rotation; }
        [Serializable] public class Recipe { public float[] sun; }
        [Serializable] public class Point { public float[] position; }
        [Serializable] public class ViewSpec { public string name; public float[] position, target; public float lens; }
        [Serializable] public class RouteSpec { public string id; public float width; public Point[] points; }
        [Serializable] public class PlotSpec { public string id; public float[] position,size; }
        [Serializable] public class SceneSpec
        {
            public string id, label, description, biome;
            public Instance[] instances;
            public Matter[] materials;
            public Recipe config;
            public int building_count, tree_count, triangles_lod0, static_triangles;
            public int seed, annee;
            public string culture, typologie;
            public Point[] anchors, smokes, torches;
            public string[] wheels, banners;
            public float[] center, camera_position, camera_target;
            public ViewSpec[] cameras;
            public RouteSpec[] routes; public PlotSpec[] plots; public float[] spawn,forest;
        }
        [Serializable] public class Verification
        {
            public string scene, unity, status;
            public int instances, prefab_count, lod_groups, missing_materials, static_triangles;
            public int maisons_independantes=-1;
            // Décor tiers de la citadelle ; -1 : pack absent ou scène sans décor tiers.
            public int batiments_tiers=-1,accessoires_tiers=-1,arbres_morts=-1,rochers=-1;
            public float max_position_error_m;
        }

        static T Read<T>(string name) => JsonUtility.FromJson<T>(File.ReadAllText(Root + "/Data/" + name + ".json"));
        static Vector3 Position(float[] a) => new Vector3(-a[0], a[2], -a[1]);
        static Vector3 Scale(float[] a) => new Vector3(a[0], a[2], a[1]);

        [MenuItem("Forge/V2/Reconstruire les villages")]
        public static void Build()
        {
            BuildAt("Assets/ForgeLocal3D/V2", "../local3d/v2/villages/", false);
        }

        public static void BuildAt(string root, string output, bool alpine, bool citadel=false, bool desert=false)
        {
            Root = root; Output = output; Alpine = alpine; Citadel = citadel; Desert = desert;
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            foreach (var folder in new[] { "Materials", "Prefabs", "Scenes", "Settings" }) Directory.CreateDirectory(Root + "/" + folder);
            AssetDatabase.Refresh();
            var catalog = Read<Catalog>("catalogue");
            var selected = Read<Selection>("selection");
            if (catalog.assets.Length == 0 || selected.variants.Length == 0) throw new InvalidOperationException("Catalogue ou sélection vide");
            var specs = selected.variants.Select(Read<SceneSpec>).ToArray();
            PrepareTextures();
            var materials = new Dictionary<string, Material>();
            foreach (var matter in catalog.materials.Concat(specs.SelectMany(s => s.materials)).GroupBy(m => m.name).Select(g => g.First()))
                materials[matter.name] = MakeMaterial(matter);
            SetupPipeline();
            var prefabs = new Dictionary<string, GameObject>();
            foreach (var asset in catalog.assets) prefabs[asset.id] = MakePrefab(asset, materials);
            if(Citadel)CitadelHabitatBuilder.Prepare(prefabs);
            var names = selected.variants.Select(n => Prefix + n).ToArray();
            // Conserver les autres scènes du projet ; remplacer uniquement les entrées V2 construites.
            var paths = names.Select(n => Root + "/Scenes/" + n + ".unity").ToArray();
            var existing = EditorBuildSettings.scenes.Where(s => !paths.Contains(s.path));
            EditorBuildSettings.scenes = paths.Select(p => new EditorBuildSettingsScene(p, true)).Concat(existing).ToArray();
            foreach (var spec in specs) MakeScene(spec, prefabs, materials, names, specs.Select(s => s.label).ToArray());
            AssetDatabase.SaveAssets();
            EditorSceneManager.OpenScene(paths[0]);
            Debug.Log("FORGE_UNITY_V2_OK scènes=" + specs.Length + " prefabs=" + prefabs.Count);
        }

        static void PrepareTextures()
        {
            foreach (string path in AssetDatabase.FindAssets("t:Texture2D", new[] { Root + "/Textures" }).Select(AssetDatabase.GUIDToAssetPath))
            {
                var importer = (TextureImporter)AssetImporter.GetAtPath(path);
                importer.sRGBTexture = path.Contains("BaseColor");
                importer.textureType = path.Contains("Normal") ? TextureImporterType.NormalMap : TextureImporterType.Default;
                importer.alphaSource = TextureImporterAlphaSource.FromInput;
                importer.alphaIsTransparency = path.Contains("feuille_") || path.Contains("aiguilles_") || path.Contains("neige_rameaux") || path.Contains("palme") || path.Contains("feuillage_acacia");
                importer.mipmapEnabled = true;
                importer.mipMapsPreserveCoverage = importer.alphaIsTransparency;
                importer.alphaTestReferenceValue = .35f;
                importer.maxTextureSize = 2048;
                importer.anisoLevel = 8;
                importer.wrapMode = Path.GetFileName(path).StartsWith("terrain_") ? TextureWrapMode.Clamp : TextureWrapMode.Repeat;
                importer.SaveAndReimport();
            }
        }

        static Material MakeMaterial(Matter matter)
        {
            var shader = Shader.Find(Lit ? "Forge/CitadelLit" : Alpine ? (matter.name == "eau_alpine" ? "Forge/AlpineWater" : "Forge/AlpineLit") : "Universal Render Pipeline/Lit");
            if (!shader) throw new InvalidOperationException("URP absent");
            string path = Root + "/Materials/" + matter.name + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) { m = new Material(shader); AssetDatabase.CreateAsset(m, path); }
            m.shader = shader; m.name = matter.name; m.shaderKeywords = Array.Empty<string>();
            Texture2D Map(string suffix) => AssetDatabase.LoadAssetAtPath<Texture2D>(Root + "/Textures/" + matter.texture + "_" + suffix + ".png");
            var color = Map("BaseColor");
            if (!color) throw new InvalidOperationException("Texture absente : " + matter.name);
            m.SetColor("_BaseColor", Color.white);
            m.SetTexture("_BaseMap", color);
            m.SetFloat("_Metallic", 0);
            m.SetFloat("_Smoothness", 1 - matter.roughness);
            m.SetFloat("_Cull", 0);
            if (Alpine && !Desert)
            {
                bool foliage = matter.alpha || matter.name == "herbe" || matter.name.StartsWith("linge_");
                m.SetFloat("_Wind", foliage ? 1 : 0);
                m.SetFloat("_SnowFactor", matter.name.Contains("roof") ? 1 : matter.name.StartsWith("terrain_") ? .75f : .35f);
                m.SetColor("_EmissionColor", matter.name == "lumiere" || matter.name == "fenetre" ? new Color(1.0f, .46f, .12f) : Color.black);
            }
            if (Citadel)
            {
                m.SetFloat("_Wind",matter.name=="aiguilles_sombres"||matter.name=="neige_rameaux"?1:0);
                m.SetFloat("_Banner",matter.name=="tissu_bordeaux"?1:0);
                m.SetFloat("_SnowFactor",0);
                m.SetColor("_EmissionColor",matter.name=="lumiere"?new Color(1.35f,.62f,.24f):matter.name.StartsWith("vitrail_")?new Color(.65f,.65f,.65f):Color.black);
                m.SetFloat("_BumpScale",matter.name.StartsWith("bois_")?.16f:.35f);
                m.SetFloat("_Weathering",new[]{"basalte","pierre_taille","calcaire","enduit"}.Contains(matter.name)?.16f:0);
                m.SetFloat("_HasGlossMap",Map("MetallicGloss")?1:0);
            }
            if (Desert) DesertBuilder.ConfigureMaterial(m, matter.name, Map("MetallicGloss"));
            m.SetFloat("_AlphaClip", matter.alpha ? 1 : 0);
            m.SetFloat("_Cutoff", .35f);
            m.SetFloat("_Surface", 0);
            m.SetFloat("_ZWrite", 1);
            m.renderQueue = matter.alpha ? (int)RenderQueue.AlphaTest : (int)RenderQueue.Geometry;
            m.SetOverrideTag("RenderType", matter.alpha ? "TransparentCutout" : "Opaque");
            if (matter.alpha) m.EnableKeyword("_ALPHATEST_ON");
            if (Map("Normal")) { m.SetTexture("_BumpMap", Map("Normal")); m.EnableKeyword("_NORMALMAP"); }
            if (Map("MetallicGloss"))
            {
                m.SetTexture("_MetallicGlossMap", Map("MetallicGloss"));
                m.SetFloat("_Smoothness", matter.name == "eau" ? .9f : 1);
                m.EnableKeyword("_METALLICSPECGLOSSMAP");
            }
            m.enableInstancing = true;
            EditorUtility.SetDirty(m);
            return m;
        }

        static void Remap(GameObject go, Dictionary<string, Material> materials)
        {
            foreach (var renderer in go.GetComponentsInChildren<Renderer>(true))
                renderer.sharedMaterials = renderer.sharedMaterials.Select(m =>
                {
                    if (m && materials.TryGetValue(m.name, out var found)) return found;
                    throw new InvalidOperationException("Matériau non résolu : " + (m ? m.name : "vide") + " dans " + go.name);
                }).ToArray();
        }

        static GameObject MakePrefab(Asset asset, Dictionary<string, Material> materials)
        {
            string path = Root + "/Models/" + asset.id + ".fbx";
            var importer = (ModelImporter)AssetImporter.GetAtPath(path);
            if (!importer) throw new InvalidOperationException("FBX absent : " + asset.id);
            importer.importAnimation = false;
            importer.globalScale = 1;
            importer.importCameras = false;
            importer.importLights = false;
            importer.SaveAndReimport();
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            var go = UnityEngine.Object.Instantiate(model);
            go.name = asset.id;
            Remap(go, materials);
            var group = go.GetComponent<LODGroup>();
            if (!group) group = go.AddComponent<LODGroup>();
            var levels = new LOD[3];
            var sizes = asset.kind == "accessoire" ? new[] { .025f, .009f, .001f } : new[] { .12f, .045f, .004f };
            for (int i = 0; i < 3; i++)
            {
                var renderers = go.GetComponentsInChildren<Renderer>(true).Where(r => r.name.EndsWith("_LOD" + i)).ToArray();
                int triangles = renderers.Sum(r => r.GetComponent<MeshFilter>().sharedMesh.triangles.Length / 3);
                if (renderers.Length == 0 || triangles != asset.triangles[i]) throw new InvalidOperationException("Géométrie LOD divergente : " + asset.id + " / " + i+" attendu="+asset.triangles[i]+" reçu="+triangles+" maillages="+string.Join(",",go.GetComponentsInChildren<Renderer>(true).Select(r=>r.name)));
                if (i == 0)
                {
                    var bounds = renderers[0].bounds;
                    foreach (var r in renderers.Skip(1)) bounds.Encapsulate(r.bounds);
                    Vector3 expected = Scale(asset.bounds_max) - Scale(asset.bounds_min);
                    if ((bounds.size - expected).magnitude > .02f) throw new InvalidOperationException("Échelle FBX divergente : " + asset.id + " attendu=" + expected + " reçu=" + bounds.size);
                }
                foreach (var r in renderers) r.enabled = true;
                levels[i] = new LOD(sizes[i], renderers);
            }
            group.SetLODs(levels); group.RecalculateBounds();
            if(Citadel)CitadelBuilder.AddAssetCollision(go,asset.id);
            if(Desert)DesertBuilder.AddAssetCollision(go,asset.id);
            var result = PrefabUtility.SaveAsPrefabAsset(go, Root + "/Prefabs/" + asset.id + ".prefab");
            UnityEngine.Object.DestroyImmediate(go);
            return result;
        }

        static void SetupPipeline()
        {
            string settings = Root + "/Settings/";
            var data = AssetDatabase.LoadAssetAtPath<UniversalRendererData>(settings + "Renderer.asset");
            if (!data) { data = ScriptableObject.CreateInstance<UniversalRendererData>(); AssetDatabase.CreateAsset(data, settings + "Renderer.asset"); }
            var pipeline = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(settings + "Pipeline.asset");
            if (!pipeline) { pipeline = UniversalRenderPipelineAsset.Create(data); AssetDatabase.CreateAsset(pipeline, settings + "Pipeline.asset"); }
            pipeline.shadowDistance = 550;
            pipeline.msaaSampleCount = 4;
            pipeline.renderScale = 1;
            pipeline.supportsHDR = true;
            if (Alpine) { pipeline.mainLightShadowmapResolution = 4096; pipeline.shadowCascadeCount = 4; }
            if (Lit) CitadelBuilder.ConfigureRenderer(data,pipeline);
            // Correction déjà vérifiée sur la V1 : ce pilote mélangeait les
            // matériaux des sous-maillages lorsque SRP Batcher était actif.
            pipeline.useSRPBatcher = false;
            pipeline.supportsDynamicBatching = false;
            EditorUtility.SetDirty(pipeline);
            GraphicsSettings.defaultRenderPipeline = pipeline;
            QualitySettings.renderPipeline = pipeline;
            QualitySettings.lodBias = Lit ? 1f : 1.5f;
        }

        static void MakeScene(SceneSpec spec, Dictionary<string, GameObject> prefabs, Dictionary<string, Material> materials, string[] sceneNames, string[] labels)
        {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var landscapeModel = AssetDatabase.LoadAssetAtPath<GameObject>(Root + "/Landscapes/" + spec.id + ".fbx");
            if (!landscapeModel) throw new InvalidOperationException("Paysage absent : " + spec.id);
            var landscape = (GameObject)PrefabUtility.InstantiatePrefab(landscapeModel);
            landscape.name = "Relief, eau et ouvrages";
            Remap(landscape, materials);
            if(Lit)foreach(var filter in landscape.GetComponentsInChildren<MeshFilter>())
                filter.gameObject.AddComponent<MeshCollider>().sharedMesh=filter.sharedMesh;
            int triangles = landscape.GetComponentsInChildren<MeshFilter>().Sum(f => f.sharedMesh.triangles.Length / 3);
            if (triangles != spec.static_triangles) throw new InvalidOperationException("Paysage divergent : " + spec.id);
            if (Alpine)
            {
                var terrain = landscape.GetComponentsInChildren<MeshFilter>().First(f => f.name.StartsWith("Terrain"));
                var vertices = terrain.sharedMesh.vertices.Select(terrain.transform.TransformPoint).ToArray();
                if (spec.anchors == null || spec.anchors.Length == 0) throw new InvalidOperationException("Repères terrain absents");
                foreach (var anchor in spec.anchors)
                    if (vertices.Min(p => Vector3.Distance(p, Position(anchor.position))) > .01f)
                        throw new InvalidOperationException("Axes Blender/Unity divergents : " + spec.id);
            }
            var containers = new Dictionary<string, Transform>();
            foreach (string key in new[] { "01", "02", "03" }) containers[key] = new GameObject(key == "01" ? "Architecture" : key == "02" ? "Nature" : "Vie du village").transform;
            float maxError = 0;
            foreach (var instance in spec.instances)
            {
                if (!prefabs.TryGetValue(instance.asset, out var prefab)) throw new InvalidOperationException("Asset inconnu : " + instance.asset);
                var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                go.name = instance.id;
                go.transform.SetParent(containers[instance.category]);
                go.transform.SetPositionAndRotation(Position(instance.position), Quaternion.Euler(0, -instance.rotation, 0));
                go.transform.localScale = Scale(instance.scale);
                if(Lit && instance.color!=null && instance.color.Length==3)
                {var appearance=go.AddComponent<CitadelHouseAppearance>();appearance.tint=new Color(instance.color[0],instance.color[1],instance.color[2]);if(Desert)appearance.matter="enduit_pise";appearance.Apply();}
                maxError = Mathf.Max(maxError, Vector3.Distance(go.transform.position, Position(instance.position)));
            }
            if (spec.instances.Length == 0 || maxError > .0002f) throw new InvalidOperationException("Positions divergentes");
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(.63f, .71f, .79f);
            RenderSettings.ambientEquatorColor = new Color(.42f, .46f, .36f);
            RenderSettings.ambientGroundColor = new Color(.22f, .23f, .17f);
            RenderSettings.fog = false;
            var light = new GameObject("Soleil").AddComponent<Light>();
            light.type = LightType.Directional;
            light.color = spec.config?.sun?.Length != 3 ? new Color(1,.88f,.7f) : new Color(spec.config.sun[0], spec.config.sun[1], spec.config.sun[2]);
            light.intensity = 1.8f;
            light.shadows = LightShadows.Soft;
            light.shadowBias = .03f;
            light.transform.rotation = Quaternion.Euler(48, -32, 0);
            RenderSettings.sun = light;
            var camera = new GameObject("Caméra de visite").AddComponent<Camera>();
            camera.tag = "MainCamera";
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = spec.biome == "aride" ? new Color(.40f, .32f, .22f) : new Color(.28f, .34f, .29f);
            camera.nearClipPlane = .3f; camera.farClipPlane = 1500;
            camera.orthographic = true; camera.orthographicSize = 315f / (2 * 1920f / 1260f);
            camera.transform.position = new Vector3(-180, 215, 230);
            Vector3 focus = new Vector3(0, 7, -8);
            camera.transform.LookAt(focus);
            camera.gameObject.AddComponent<UniversalAdditionalCameraData>();
            var visit = camera.gameObject.AddComponent<VillageV2Visit>();
            visit.focus = focus; visit.distance = Vector3.Distance(camera.transform.position, focus);
            visit.yaw = camera.transform.eulerAngles.y; visit.pitch = camera.transform.eulerAngles.x;
            visit.zoomRatio = camera.orthographicSize / visit.distance;
            visit.village = spec.label; visit.description = spec.description; visit.sceneNames = sceneNames; visit.labels = labels;
            if (Alpine)
            {
                visit.showInterface = false;
                if(Desert) DesertBuilder.Configure(spec,camera,light,sceneNames,labels);
                else if(Citadel) CitadelBuilder.Configure(spec,camera,light,sceneNames,labels);
                else AlpineBuilder.Configure(spec, camera, light, sceneNames, labels, materials);
            }
            string path = Root + "/Scenes/" + Prefix + spec.id + ".unity";
            EditorSceneManager.SaveScene(scene, path);
            AssetDatabase.SaveAssets();
            Capture(camera, spec.id, "unity_territoire");
            var position = camera.transform.position; var rotation = camera.transform.rotation; float size = camera.orthographicSize;
            camera.transform.position = Desert?new Vector3(-44,57,109):Citadel?new Vector3(-44,69,109):Alpine ? new Vector3(-99, 100, 145) : new Vector3(-112, 110, 151);
            camera.transform.LookAt(Desert?new Vector3(0,50,21):Citadel?new Vector3(0,62,21):Alpine ? new Vector3(-spec.center[0]+2,5,-spec.center[1]) : new Vector3(-15, 7, 6)); camera.orthographicSize = 150f / (2 * 1920f / 1260f);
            Capture(camera, spec.id, "unity_village");
            if(Lit && spec.cameras!=null)
                foreach(var view in spec.cameras)
                {
                    camera.transform.position=Position(view.position);camera.transform.LookAt(Position(view.target));
                    camera.fieldOfView=2*Mathf.Atan(36f/(2*view.lens)/(1600f/900f))*Mathf.Rad2Deg;
                    Capture(camera,spec.id,"unity_"+view.name.ToLowerInvariant());
                }
            foreach(var m in materials.Values)
                if(ShaderUtil.ShaderHasError(m.shader))throw new InvalidOperationException("Shader refusé après rendu : "+m.shader.name);
            if(Citadel){CitadelTerrainSample.CaptureDetails(camera,Path.GetFullPath(Output+spec.id+"/renders/"));
                var env=UnityEngine.Object.FindFirstObjectByType<CitadelEnvironment>();env.ShowView("Habitat");Capture(camera,spec.id,"unity_habitat");}
            camera.transform.SetPositionAndRotation(position, rotation); camera.orthographicSize = size;
            if(Lit)camera.fieldOfView=26.4f;
            EditorSceneManager.SaveScene(scene, path);
            // Réouvrir la scène sérialisée vérifie que les prefabs et matériaux survivent à la sauvegarde.
            EditorSceneManager.OpenScene(path);
            var groups = UnityEngine.Object.FindObjectsByType<LODGroup>(FindObjectsSortMode.None);
            if (groups.Length != spec.instances.Length) throw new InvalidOperationException("Instances perdues après sauvegarde");
            if (UnityEngine.Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None).Any(r => r.sharedMaterials.Any(m => !m)))
                throw new InvalidOperationException("Matériaux perdus après sauvegarde");
            int independentHouses=-1;
            if(Lit)
            {
                var expected=spec.instances.Where(i=>i.asset.StartsWith("maison_")).Select(i=>i.id).OrderBy(n=>n).ToArray();
                var houses=groups.Where(g=>g.name.StartsWith("maison_")).ToArray();
                if(expected.Length==0 || !houses.Select(g=>g.name).OrderBy(n=>n).SequenceEqual(expected) ||
                   houses.Any(g=>!PrefabUtility.IsPartOfPrefabInstance(g.gameObject)))
                    throw new InvalidOperationException("Une maison a perdu son identité ou son instance de prefab");
                independentHouses=houses.Length;
            }
            var result = new Verification { scene = path, unity = Application.unityVersion, status = "valide", instances = spec.instances.Length,
                prefab_count = prefabs.Count, lod_groups = groups.Length, missing_materials = 0, static_triangles = triangles, max_position_error_m = maxError,maisons_independantes=independentHouses,
                batiments_tiers=Citadel?CitadelDecor.Buildings:-1,accessoires_tiers=Citadel?CitadelDecor.Props:Desert?DesertDecor.Props:-1,arbres_morts=Citadel?CitadelDecor.DeadTrees:Desert?DesertDecor.DeadTrees:-1,rochers=Citadel?CitadelDecor.Rocks:-1 };
            File.WriteAllText(Path.GetFullPath(Output + spec.id + "/unity-verification.json"), JsonUtility.ToJson(result, true));
            if(Citadel){CitadelTerrainSample.Verify(spec,Path.GetFullPath(Output+spec.id+"/terrain-sample-verification.json"));CitadelArchitecture.Verify();CitadelHabitatBuilder.Verify(Path.GetFullPath(Output+spec.id+"/habitat-verification.json"));}
            Debug.Log("VILLAGE_V2_OK " + spec.id + " instances=" + groups.Length);
        }

        static void Capture(Camera camera, string id, string filename)
        {
            int width = Lit ? 1600 : 1920, height = Lit ? 900 : 1260;
            var target = new RenderTexture(width, height, 24, RenderTextureFormat.ARGB32) { antiAliasing = 4 };
            target.Create();
            RenderPipeline.SubmitRenderRequest(camera, new UniversalRenderPipeline.SingleCameraRequest { destination = target });
            var old = RenderTexture.active; RenderTexture.active = target;
            var image = new Texture2D(width, height, TextureFormat.RGB24, false);
            image.ReadPixels(new Rect(0, 0, width, height), 0, 0); image.Apply();
            File.WriteAllBytes(Path.GetFullPath(Output + id + "/renders/" + filename + ".png"), image.EncodeToPNG());
            RenderTexture.active = old; UnityEngine.Object.DestroyImmediate(image);
            target.Release(); UnityEngine.Object.DestroyImmediate(target);
        }

        [MenuItem("Forge/V2/Ouvrir Val d’Aulne")]
        public static void Open()
        {
            EditorSceneManager.OpenScene("Assets/ForgeLocal3D/V2/Scenes/Forge_V2_val_aulne.unity");
            if (SceneView.lastActiveSceneView) SceneView.lastActiveSceneView.LookAt(new Vector3(0, 7, -8), Quaternion.Euler(35, 217, 0), 180);
        }
    }
}
