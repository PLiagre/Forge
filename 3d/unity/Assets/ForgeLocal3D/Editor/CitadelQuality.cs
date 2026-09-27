using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace ForgeLocal3D
{
    public static class CitadelQuality
    {
        public static void PrepareScene()
        {
            var renderers=UnityEngine.Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None);
            // Seules les textures réellement utilisées par la scène sont réimportées.
            var textures=renderers.SelectMany(r=>r.sharedMaterials).Where(m=>m)
                .Distinct().SelectMany(m=>m.GetTexturePropertyNames().Select(m.GetTexture))
                .Where(t=>t).Select(AssetDatabase.GetAssetPath).Distinct().Where(p=>p.StartsWith("Assets/Vendor/")).ToArray();
            int changed=0;
            foreach(string path in textures)
            {
                if(AssetImporter.GetAtPath(path) is not TextureImporter importer)continue;
                int size=path.Contains("fe_village")?2048:1024;
                bool leaves=path.Contains("/Trees/")&&path.Contains("Color")&&!path.Contains("Bark")&&!path.Contains("Cap");
                bool coverage=leaves&&!importer.mipMapsPreserveCoverage;
                if(coverage){importer.mipMapsPreserveCoverage=true;importer.alphaTestReferenceValue=.28f;}
                if(!coverage&&importer.maxTextureSize<=size&&importer.mipmapEnabled&&importer.textureCompression==TextureImporterCompression.Compressed)continue;
                importer.maxTextureSize=size;importer.mipmapEnabled=true;importer.textureCompression=TextureImporterCompression.Compressed;
                importer.SaveAndReimport();changed++;
            }
            foreach(var r in renderers)
            {
                // Les arbres abattables, tissus et pales restent mobiles.
                if(r.GetComponentInParent<CitadelTree>()||r.sharedMaterials.Any(m=>m&&
                    (m.HasProperty("_Wind")&&m.GetFloat("_Wind")>0||m.HasProperty("_Banner")&&m.GetFloat("_Banner")>0)))continue;
                if(r.transform.root.name=="Relief, eau et ouvrages"||r.transform.root.name.StartsWith("Décor tiers"))
                    GameObjectUtility.SetStaticEditorFlags(r.gameObject,StaticEditorFlags.BatchingStatic);
            }
            Debug.Log("CITADELLE_QUALITE textures_utilisees="+textures.Length+" reduites="+changed);
        }
        public static void BuildPlayer()
        {
            string output=Path.GetFullPath("../local3d/citadelle/sorties/joueur/Citadelle.exe");
            Directory.CreateDirectory(Path.GetDirectoryName(output));
            var scenes=Directory.GetFiles(CitadelBuilder.Root+"/Scenes","Forge_Citadelle_*.unity").OrderBy(p=>p).ToArray();
            if(scenes.Length==0)throw new InvalidOperationException("Aucune scène de citadelle à mesurer");
            PlayerSettings.fullScreenMode=FullScreenMode.Windowed;PlayerSettings.defaultScreenWidth=1920;PlayerSettings.defaultScreenHeight=1080;
            var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=scenes,locationPathName=output,target=BuildTarget.StandaloneWindows64,options=BuildOptions.None});
            if(report.summary.result!=BuildResult.Succeeded)throw new InvalidOperationException("Construction du joueur échouée : "+report.summary.result);
            Debug.Log("CITADELLE_JOUEUR "+output);
        }
    }
}
