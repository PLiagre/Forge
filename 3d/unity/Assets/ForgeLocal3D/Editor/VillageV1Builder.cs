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
    // Reconstruit la scène de visite depuis l'export Blender, sans lancer le jeu.
    public static class VillageV1Builder
    {
        const string Root = "Assets/ForgeLocal3D";
        [Serializable] public class Matter
        {
            public string name;
            public float[] color;
            public bool textured;
            public float metallic;
            public float roughness;
        }
        [Serializable] public class Report { public Matter[] materials; public int buildings; public int triangles; }

        [MenuItem("Forge/Construire la scène Blender V1")]
        public static void Build()
        {
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            var report = JsonUtility.FromJson<Report>(File.ReadAllText(Root + "/rapport.json"));
            Directory.CreateDirectory(Root + "/Materials");
            Directory.CreateDirectory(Root + "/Scenes");
            Directory.CreateDirectory(Root + "/Settings");
            foreach (string path in AssetDatabase.FindAssets("t:Texture2D", new[] { Root + "/Textures" }).Select(AssetDatabase.GUIDToAssetPath))
            {
                var importer = (TextureImporter)AssetImporter.GetAtPath(path);
                importer.sRGBTexture = path.Contains("BaseColor");
                importer.textureType = path.Contains("Normal") ? TextureImporterType.NormalMap : TextureImporterType.Default;
                importer.maxTextureSize = 2048;
                importer.wrapMode = TextureWrapMode.Clamp;
                importer.SaveAndReimport();
            }
            Texture2D Map(string name) => AssetDatabase.LoadAssetAtPath<Texture2D>(Root + "/Textures/CityLabTrimV2_" + name + ".png");
            var shader = Shader.Find("Universal Render Pipeline/Lit");
            if (shader == null) throw new InvalidOperationException("Shader URP absent");
            var materials = new Dictionary<string, Material>();
            foreach (var entry in report.materials)
            {
                string safe = string.Concat(entry.name.Select(c => char.IsLetterOrDigit(c) || c == '_' ? c : '_'));
                string path = Root + "/Materials/" + safe + ".mat";
                var m = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (m == null) { m = new Material(shader); AssetDatabase.CreateAsset(m, path); }
                m.name = entry.name;
                m.SetColor("_BaseColor", entry.textured ? Color.white : new Color(entry.color[0], entry.color[1], entry.color[2], 1));
                m.SetFloat("_Smoothness", 1 - entry.roughness);
                m.SetFloat("_Metallic", entry.metallic);
                m.SetFloat("_Cull", 0);
                if (entry.textured)
                {
                    m.SetTexture("_BaseMap", Map("BaseColor"));
                    m.SetTexture("_BumpMap", Map("Normal"));
                    m.SetTexture("_OcclusionMap", Map("AO"));
                    m.SetTexture("_MetallicGlossMap", Map("MetallicGloss"));
                    m.SetFloat("_Smoothness", 1);
                    m.EnableKeyword("_NORMALMAP");
                    m.EnableKeyword("_OCCLUSIONMAP");
                    m.EnableKeyword("_METALLICSPECGLOSSMAP");
                }
                materials.Add(entry.name, m);
                EditorUtility.SetDirty(m);
            }
            var rendererData = AssetDatabase.LoadAssetAtPath<UniversalRendererData>(Root + "/Settings/Renderer.asset");
            if (rendererData == null)
            {
                rendererData = ScriptableObject.CreateInstance<UniversalRendererData>();
                AssetDatabase.CreateAsset(rendererData, Root + "/Settings/Renderer.asset");
            }
            var pipeline = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(Root + "/Settings/Pipeline.asset");
            if (pipeline == null)
            {
                pipeline = UniversalRenderPipelineAsset.Create(rendererData);
                AssetDatabase.CreateAsset(pipeline, Root + "/Settings/Pipeline.asset");
            }
            pipeline.shadowDistance = 260;
            pipeline.msaaSampleCount = 4;
            pipeline.renderScale = 1;
            pipeline.supportsHDR = true;
            // Sur ce rendu Unity 6, le regroupement SRP mélange les couleurs
            // des sous-maillages : constaté sur le terrain et le feuillage.
            pipeline.useSRPBatcher = false;
            pipeline.supportsDynamicBatching = false;
            EditorUtility.SetDirty(pipeline);
            GraphicsSettings.defaultRenderPipeline = pipeline;
            QualitySettings.renderPipeline = pipeline;
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(Root + "/Models/Forge_Village_V1.fbx");
            if (model == null) throw new InvalidOperationException("Export Blender absent");
            var village = (GameObject)PrefabUtility.InstantiatePrefab(model);
            village.name = "Forge — village pilote Blender V1";
            int missing = 0;
            foreach (var renderer in village.GetComponentsInChildren<MeshRenderer>(true))
            {
                renderer.sharedMaterials = renderer.sharedMaterials.Select(m =>
                {
                    if (m != null && materials.TryGetValue(m.name, out var found)) return found;
                    missing++;
                    return m;
                }).ToArray();
            }
            if (missing != 0) throw new InvalidOperationException("Matériaux non résolus : " + missing);
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(.58f, .67f, .78f);
            RenderSettings.ambientEquatorColor = new Color(.39f, .43f, .34f);
            RenderSettings.ambientGroundColor = new Color(.18f, .20f, .14f);
            RenderSettings.fog = false;
            var light = new GameObject("Soleil").AddComponent<Light>();
            light.type = LightType.Directional;
            light.color = new Color(1, .87f, .69f);
            light.intensity = 1.9f;
            light.shadows = LightShadows.Soft;
            light.transform.rotation = Quaternion.Euler(48, -32, 0);
            RenderSettings.sun = light;
            var camera = new GameObject("Caméra de visite").AddComponent<Camera>();
            camera.tag = "MainCamera";
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = new Color(.34f, .39f, .32f);
            camera.nearClipPlane = .2f;
            camera.farClipPlane = 1500;
            camera.fieldOfView = 42;
            camera.orthographic = true;
            camera.orthographicSize = 77;
            camera.transform.position = new Vector3(150, 155, 175);
            camera.transform.LookAt(new Vector3(0, 1, 0));
            camera.gameObject.AddComponent<UniversalAdditionalCameraData>();
            camera.gameObject.AddComponent<VillageV1Visit>();
            var volume = new GameObject("Étalonnage").AddComponent<Volume>();
            volume.isGlobal = true;
            var profile = AssetDatabase.LoadAssetAtPath<VolumeProfile>(Root + "/Settings/Volume.asset");
            if (profile == null)
            {
                profile = ScriptableObject.CreateInstance<VolumeProfile>();
                AssetDatabase.CreateAsset(profile, Root + "/Settings/Volume.asset");
                var tone = profile.Add<Tonemapping>(true);
                tone.mode.Override(TonemappingMode.ACES);
                AssetDatabase.AddObjectToAsset(tone, profile);
            }
            volume.sharedProfile = profile;
            camera.GetUniversalAdditionalCameraData().renderPostProcessing = true;
            string scenePath = Root + "/Scenes/Forge_Village_V1.unity";
            EditorSceneManager.SaveScene(scene, scenePath);
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(scenePath, true) };
            AssetDatabase.SaveAssets();
            var bounds = new Bounds(village.transform.position, Vector3.zero);
            foreach (var r in village.GetComponentsInChildren<Renderer>()) bounds.Encapsulate(r.bounds);
            if (bounds.size.x < 139 || bounds.size.x > 160 || bounds.size.z < 139 || bounds.size.z > 160)
                throw new InvalidOperationException("Échelle de l'import incorrecte : " + bounds.size);
            Capture(camera);
            File.WriteAllText(Path.GetFullPath("../local3d/v1/unity-verification.json"),
                "{\"scene\":\"" + scenePath + "\",\"missing_materials\":0,\"mesh_renderers\":" +
                village.GetComponentsInChildren<MeshRenderer>().Length + ",\"unity\":\"" + Application.unityVersion + "\"}");
            Debug.Log("FORGE_UNITY_V1_OK scene=" + scenePath + " bâtiments=" + report.buildings + " triangles=" + report.triangles);
        }

        public static void CaptureSaved()
        {
            EditorSceneManager.OpenScene(Root + "/Scenes/Forge_Village_V1.unity");
            var camera = Camera.main;
            Capture(camera);
        }

        public static void Open()
        {
            EditorSceneManager.OpenScene(Root + "/Scenes/Forge_Village_V1.unity");
            if (SceneView.lastActiveSceneView != null)
                SceneView.lastActiveSceneView.LookAt(new Vector3(0, 1, 0), Quaternion.Euler(34, 220.6f, 0), 110);
        }

        static void Capture(Camera camera)
        {
            var target = new RenderTexture(1600, 1200, 24, RenderTextureFormat.ARGB32);
            target.antiAliasing = 4;
            target.Create();
            var request = new UniversalRenderPipeline.SingleCameraRequest { destination = target };
            RenderPipeline.SubmitRenderRequest(camera, request);
            var old = RenderTexture.active;
            RenderTexture.active = target;
            var image = new Texture2D(1600, 1200, TextureFormat.RGB24, false);
            image.ReadPixels(new Rect(0, 0, 1600, 1200), 0, 0);
            image.Apply();
            File.WriteAllBytes(Path.GetFullPath("../local3d/v1/renders/03_unity.png"), image.EncodeToPNG());
            RenderTexture.active = old;
            UnityEngine.Object.DestroyImmediate(image);
            target.Release();
            UnityEngine.Object.DestroyImmediate(target);
        }
    }
}
