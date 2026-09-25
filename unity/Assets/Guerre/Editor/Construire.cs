using System.IO;
using System.Linq;
using Unity.Mathematics;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace Guerre.EditeurOutils
{
    // Tout se reconstruit depuis ce fichier : pipeline de rendu, vallée, scène, joueur.
    //   Unity.exe -batchmode -projectPath unity -executeMethod Guerre.EditeurOutils.Construire.Tout -quit
    // Le joueur se compile dans un second Unity : un réglage changé (Input System)
    // dans la même session rend le build incompatible avec l'éditeur.
    public static partial class Construire
    {
        const string Dossier = "Assets/Guerre";
        const string Scene = Dossier + "/Scenes/Bataille_Vallee.unity";
        const float Cote = 2400f, Hauteur = 340f;
        const int Resolution = 1025;

        [MenuItem("Guerre/Tout reconstruire")]
        public static void Tout()
        {
            Reglages();
            var pipeline = Pipeline();
            var kit = ImporterKit();
            Carte(out var terrain);
            var (materiaux, maillages) = Soldats();
            ConstruireScene(terrain, pipeline, materiaux, maillages, kit);
            Debug.Log("[Construire] scène prête : " + Scene);
        }

        [MenuItem("Guerre/Construire le joueur")]
        public static void Joueur()
        {
            string sortie = Path.GetFullPath(Path.Combine(Application.dataPath, "../../sorties/joueur/Citadelle-Guerre.exe"));
            var r = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = new[] { Scene }, locationPathName = sortie,
                target = BuildTarget.StandaloneWindows64, options = BuildOptions.None,
            });
            Debug.Log("[Construire] joueur : " + r.summary.result + " " + sortie);
            if (r.summary.result != UnityEditor.Build.Reporting.BuildResult.Succeeded) EditorApplication.Exit(1);
        }

        static void Reglages()
        {
            PlayerSettings.companyName = "Citadelle";
            PlayerSettings.productName = "Citadelle-Guerre";
            PlayerSettings.fullScreenMode = FullScreenMode.Windowed;
            PlayerSettings.defaultScreenWidth = 1920; PlayerSettings.defaultScreenHeight = 1080;
            PlayerSettings.resizableWindow = true;
            PlayerSettings.runInBackground = true;
            PlayerSettings.colorSpace = ColorSpace.Linear;
            // Input System seul : les touches se lisent par position physique.
            var ps = new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/ProjectSettings.asset")[0]);
            var input = ps.FindProperty("activeInputHandler");
            if (input != null) { input.intValue = 1; ps.ApplyModifiedPropertiesWithoutUndo(); }
            // Entities Graphics dessine par BatchRendererGroup : ses variantes de shader doivent survivre au build.
            var gs = new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/GraphicsSettings.asset")[0]);
            var brg = gs.FindProperty("m_BrgStripping");
            if (brg != null) { brg.intValue = 2; gs.ApplyModifiedPropertiesWithoutUndo(); }
            else Debug.LogWarning("[Construire] m_BrgStripping introuvable");
        }

        static UniversalRenderPipelineAsset Pipeline()
        {
            Directory.CreateDirectory(Dossier + "/Settings");
            string pRenderer = Dossier + "/Settings/Rendu_Renderer.asset", pAsset = Dossier + "/Settings/Rendu_Pipeline.asset";
            var rd = AssetDatabase.LoadAssetAtPath<UniversalRendererData>(pRenderer);
            if (!rd) { rd = ScriptableObject.CreateInstance<UniversalRendererData>(); AssetDatabase.CreateAsset(rd, pRenderer); }
            // Entities Graphics exige Forward+ dans URP.
            rd.renderingMode = RenderingMode.ForwardPlus;
            EditorUtility.SetDirty(rd);

            var asset = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(pAsset);
            if (!asset) { asset = UniversalRenderPipelineAsset.Create(rd); AssetDatabase.CreateAsset(asset, pAsset); }
            asset.useSRPBatcher = true;
            asset.supportsHDR = true;
            asset.msaaSampleCount = 4;
            asset.renderScale = 1f;
            asset.shadowDistance = 450f;
            asset.shadowCascadeCount = 4;
            var so = new SerializedObject(asset);
            var resolution = so.FindProperty("m_MainLightShadowmapResolution");
            if (resolution != null) resolution.intValue = 4096;
            var douces = so.FindProperty("m_SoftShadowsSupported");
            if (douces != null) douces.boolValue = true;
            so.ApplyModifiedPropertiesWithoutUndo();
            EditorUtility.SetDirty(asset);

            GraphicsSettings.defaultRenderPipeline = asset;
            for (int i = 0; i < QualitySettings.names.Length; i++)
            {
                QualitySettings.SetQualityLevel(i, false);
                QualitySettings.renderPipeline = asset;
            }
            var globaux = AssetDatabase.LoadAssetAtPath<RenderPipelineGlobalSettings>(Dossier + "/Settings/UniversalRenderPipelineGlobalSettings.asset");
            if (globaux) UnityEditor.Rendering.EditorGraphicsSettings.SetRenderPipelineGlobalSettingsAsset<UniversalRenderPipeline>(globaux);
            AssetDatabase.SaveAssets();
            return asset;
        }

        // Une vallée glaciaire orientée est-ouest : un fond de 700 m presque plat,
        // des versants qui montent en auge, des crêtes enneigées. Terrain provisoire,
        // en attendant la carte dédiée du jalon 8.
        static void Carte(out TerrainData td)
        {
            Directory.CreateDirectory(Dossier + "/Carte");
            string chemin = Dossier + "/Carte/Vallee.asset";
            AssetDatabase.DeleteAsset(chemin);
            td = new TerrainData { heightmapResolution = Resolution, alphamapResolution = 512 };
            td.size = new Vector3(Cote, Hauteur, Cote);
            var h = new float[Resolution, Resolution];
            for (int z = 0; z < Resolution; z++)
                for (int x = 0; x < Resolution; x++)
                {
                    float wx = x / (float)(Resolution - 1) * Cote, wz = z / (float)(Resolution - 1) * Cote;
                    // L'axe de la vallée ondule un peu, comme un vrai lit glaciaire.
                    float axe = Cote / 2 + 90f * math.sin(wx / 520f);
                    float d = math.abs(wz - axe);
                    float auge = math.pow(math.smoothstep(340f, 1150f, d), 1.5f) * 290f;
                    float rugosite = Fbm(wx, wz) * (5f + 45f * math.smoothstep(250f, 900f, d));
                    float pente = wx / Cote * 18f;
                    h[z, x] = math.saturate(Relief(wx, wz, 12f + auge + rugosite + pente) / Hauteur);
                }
            td.SetHeights(0, 0, h);
            // L'asset avant les couches : sinon elles disparaissent au changement de scène.
            AssetDatabase.CreateAsset(td, chemin);

            var herbe = Couche("Herbe", new Color(0.36f, 0.42f, 0.27f), new Color(0.46f, 0.47f, 0.33f), 6f);
            var roche = Couche("Roche", new Color(0.36f, 0.35f, 0.34f), new Color(0.52f, 0.5f, 0.48f), 10f);
            var neige = Couche("Neige", new Color(0.86f, 0.89f, 0.94f), new Color(0.97f, 0.98f, 1f), 12f);
            // Les pavés du plateau, avec la texture du kit de Forge.
            var pave = Couche("Pave", Kit + "/Textures/sol_pave_BaseColor.png", 4f);
            td.terrainLayers = new[] { herbe, roche, neige, pave };
            int n = td.alphamapResolution;
            var a = new float[n, n, 4];
            for (int z = 0; z < n; z++)
                for (int x = 0; x < n; x++)
                {
                    float u = x / (float)(n - 1), v = z / (float)(n - 1);
                    float alt = td.GetInterpolatedHeight(u, v);
                    float pente = td.GetSteepness(u, v);
                    float wN = math.smoothstep(150f, 210f, alt + Fbm(u * Cote * 2, v * Cote * 2) * 30f) * (1 - math.smoothstep(35f, 50f, pente));
                    float wR = math.smoothstep(22f, 34f, pente);
                    float wH = math.max(0, 1 - wN - wR);
                    float s = wN + wR + wH;
                    // Le plateau de la citadelle est pavé, sauf là où il tombe en paroi.
                    if (math.distance(new float2(u, v) * Cote, Eperon) < RavinDedans - 1f) { a[z, x, 0] = 0; a[z, x, 1] = wR; a[z, x, 2] = 0; a[z, x, 3] = 1 - wR; }
                    else { a[z, x, 0] = wH / s; a[z, x, 1] = wR / s; a[z, x, 2] = wN / s; a[z, x, 3] = 0; }
                }
            td.SetAlphamaps(0, 0, a);
            EditorUtility.SetDirty(td);
            AssetDatabase.SaveAssets();
        }

        // Une couche de terrain tirée d'une texture existante (celles du kit de Forge).
        static TerrainLayer Couche(string nom, string texture, float tuile)
        {
            string pLayer = Dossier + "/Carte/" + nom + ".terrainlayer";
            AssetDatabase.DeleteAsset(pLayer);
            var layer = new TerrainLayer { diffuseTexture = AssetDatabase.LoadAssetAtPath<Texture2D>(texture), tileSize = new Vector2(tuile, tuile) };
            AssetDatabase.CreateAsset(layer, pLayer);
            return layer;
        }

        static TerrainLayer Couche(string nom, Color sombre, Color clair, float tuile)
        {
            string pTex = Dossier + "/Carte/" + nom + ".png", pLayer = Dossier + "/Carte/" + nom + ".terrainlayer";
            const int N = 256;
            var tex = new Texture2D(N, N, TextureFormat.RGBA32, true);
            for (int y = 0; y < N; y++)
                for (int x = 0; x < N; x++)
                {
                    // Bruit périodique, pour que la tuile se raccorde sans couture.
                    float2 p = new float2(x, y) / N * 2 * math.PI;
                    float b = 0.5f + 0.25f * noise.cnoise(new float4(math.cos(p.x), math.sin(p.x), math.cos(p.y), math.sin(p.y)) * 2.2f)
                                   + 0.15f * noise.cnoise(new float4(math.cos(p.x), math.sin(p.x), math.cos(p.y), math.sin(p.y)) * 6.5f);
                    tex.SetPixel(x, y, Color.Lerp(sombre, clair, math.saturate(b)));
                }
            File.WriteAllBytes(pTex, tex.EncodeToPNG());
            Object.DestroyImmediate(tex);
            AssetDatabase.ImportAsset(pTex);
            AssetDatabase.DeleteAsset(pLayer);
            var layer = new TerrainLayer { diffuseTexture = AssetDatabase.LoadAssetAtPath<Texture2D>(pTex), tileSize = new Vector2(tuile, tuile) };
            AssetDatabase.CreateAsset(layer, pLayer);
            return layer;
        }

        static float Fbm(float x, float z)
        {
            float s = 0, a = 1, f = 1f / 260f;
            for (int o = 0; o < 5; o++) { s += a * noise.snoise(new float2(x, z) * f); a *= 0.5f; f *= 2.1f; }
            return s;
        }

        static void ConstruireScene(TerrainData td, UniversalRenderPipelineAsset pipeline, Material[] materiaux, Mesh[] maillages, System.Collections.Generic.Dictionary<string, GameObject> kit)
        {
            Directory.CreateDirectory(Dossier + "/Scenes");
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

            var soleil = new GameObject("Soleil").AddComponent<Light>();
            soleil.type = LightType.Directional; soleil.intensity = 1.25f; soleil.color = new Color(1f, 0.95f, 0.86f);
            soleil.shadows = LightShadows.Soft;
            soleil.transform.rotation = Quaternion.Euler(38, -35, 0);
            RenderSettings.sun = soleil;
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(0.55f, 0.62f, 0.75f);
            RenderSettings.ambientEquatorColor = new Color(0.45f, 0.47f, 0.5f);
            RenderSettings.ambientGroundColor = new Color(0.25f, 0.24f, 0.22f);
            RenderSettings.fog = true; RenderSettings.fogMode = FogMode.Linear;
            RenderSettings.fogColor = new Color(0.68f, 0.74f, 0.82f);
            RenderSettings.fogStartDistance = 500; RenderSettings.fogEndDistance = 3200;
            var ciel = new Material(Shader.Find("Skybox/Procedural"));
            ciel.SetFloat("_AtmosphereThickness", 0.8f);
            AssetDatabase.CreateAsset(ciel, Dossier + "/Settings/Ciel.mat");
            RenderSettings.skybox = ciel;

            var terrainGo = Terrain.CreateTerrainGameObject(td);
            terrainGo.name = "Vallée";
            var terrain = terrainGo.GetComponent<Terrain>();
            var matTerrain = new Material(Shader.Find("Universal Render Pipeline/Terrain/Lit"));
            AssetDatabase.CreateAsset(matTerrain, Dossier + "/Settings/Terrain.mat");
            terrain.materialTemplate = matTerrain;
            terrain.heightmapPixelError = 4;
            terrain.basemapDistance = 1500;
            terrain.drawInstanced = true;


            var camGo = new GameObject("Caméra");
            camGo.tag = "MainCamera";
            var cam = camGo.AddComponent<Camera>();
            cam.nearClipPlane = 0.5f; cam.farClipPlane = 5000f; cam.fieldOfView = 45;
            camGo.AddComponent<UniversalAdditionalCameraData>();
            var trait = new Material(Shader.Find("Universal Render Pipeline/Unlit"));
            trait.SetColor("_BaseColor", new Color(1f, 0.86f, 0.35f));
            AssetDatabase.CreateAsset(trait, Dossier + "/Settings/Trait.mat");
            camGo.AddComponent<Commandement>().trait = trait;

            var bataille = new GameObject("Bataille").AddComponent<Bataille>();
            var carreau = new Material(Shader.Find("Universal Render Pipeline/Lit"));
            carreau.SetColor("_BaseColor", new Color(0.3f, 0.22f, 0.14f));
            AssetDatabase.CreateAsset(carreau, Dossier + "/Settings/Carreau.mat");
            var pavoisMat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
            pavoisMat.SetFloat("_Smoothness", 0.2f);
            AssetDatabase.CreateAsset(pavoisMat, Dossier + "/Settings/Pavois.mat");
            bataille.materiauCarreau = carreau;
            bataille.materiauPavois = pavoisMat;
            bataille.materiaux = materiaux;
            bataille.maillages = maillages;
            bataille.terrain = terrain;
            var citadelle = new GameObject("Citadelle");
            bataille.carte = BatirCitadelle(citadelle.transform, td, kit);

            new GameObject("Performance").AddComponent<Cadence>();

            EditorSceneManager.SaveScene(scene, Scene);
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(Scene, true) };
            AssetDatabase.SaveAssets();
        }
    }
}
