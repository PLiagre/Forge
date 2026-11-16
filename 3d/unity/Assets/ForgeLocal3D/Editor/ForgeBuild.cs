using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace ForgeLocal3D
{
    // Le build Windows de la nuit (.github/workflows/build-nuit.yml) :
    //   Unity -batchmode -quit -projectPath 3d/unity -executeMethod ForgeLocal3D.Build.Nuit -forgeSortie <dossier>
    // Les scènes sont celles de la liste du build, dans son ordre : la première s'ouvre au lancement.
    public static class Build
    {
        static string Argument(string nom)
        {
            var a = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(a, nom);
            return i >= 0 && i + 1 < a.Length ? a[i + 1] : null;
        }

        public static void Nuit()
        {
            string sortie = Argument("-forgeSortie") ?? Path.GetFullPath(Path.Combine(Application.dataPath, "../../../builds/manuel"));
            var scenes = EditorBuildSettings.scenes.Where(s => s.enabled).Select(s => s.path).ToArray();
            if (scenes.Length == 0)
            {
                Debug.LogError("BUILD : aucune scène au build");
                EditorApplication.Exit(2);
                return;
            }
            Directory.CreateDirectory(sortie);
            var rapport = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = scenes,
                locationPathName = Path.Combine(sortie, "Forge.exe"),
                target = BuildTarget.StandaloneWindows64,
                options = BuildOptions.None,
            });
            var s = rapport.summary;
            Debug.Log($"BUILD : {s.result}, {s.totalErrors} erreur(s), {s.totalSize / (1024 * 1024)} Mo, {s.totalTime}");
            if (s.result != BuildResult.Succeeded) { EditorApplication.Exit(1); return; }
            string manque = CopierLaVille(Path.Combine(sortie, "Forge_Data", "StreamingAssets"));
            if (manque != null) { Debug.LogError("BUILD : " + manque); EditorApplication.Exit(1); return; }
            EditorApplication.Exit(0);
        }

        // Les gestes.json de chaque implantation du désert, que la ville lit au lancement (`DesertRoads.CheminGestes`),
        // copiés sous StreamingAssets du jeu construit : il les lit près de lui, d'où qu'on le lance. Rend la cause d'un
        // manque, ou null.
        public static string CopierLaVille(string streamingAssets)
        {
            string source = Path.GetFullPath(Path.Combine(Application.dataPath, "..", DesertRoads.Sorties));
            if (!Directory.Exists(source)) return "sorties de la ville absentes : " + source;
            int copies = 0;
            foreach (string dossier in Directory.GetDirectories(source).OrderBy(d => d, StringComparer.Ordinal))
            {
                string gestes = Path.Combine(dossier, "routes", "gestes.json");
                if (!File.Exists(gestes)) continue;
                string cible = Path.Combine(streamingAssets, DesertRoads.DossierDuBuild, Path.GetFileName(dossier), "routes", "gestes.json");
                Directory.CreateDirectory(Path.GetDirectoryName(cible));
                File.Copy(gestes, cible, true);
                copies++;
                Debug.Log("BUILD : ville copiée, " + cible);
            }
            return copies == 0 ? "aucun gestes.json sous " + source : null;
        }
    }
}
