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
            EditorApplication.Exit(s.result == BuildResult.Succeeded ? 0 : 1);
        }
    }
}
