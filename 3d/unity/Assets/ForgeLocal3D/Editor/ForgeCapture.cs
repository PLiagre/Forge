using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace ForgeLocal3D
{
    // La photo d'un lot, prise par la chaîne en batch sur le PC :
    //   Unity -batchmode -quit -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeCaptures <dossier>
    // La scène du désert se construit à l'exécution (terrain, ville) : on entre en Play, on laisse
    // passer quelques images, on photographie la caméra de la scène, puis on rend la main.
    [InitializeOnLoad]
    public static class Capture
    {
        const string Flag = "Forge.Capture.Actif";
        const string Dossier = "Forge.Capture.Dossier";
        const string Scene = "Forge.Capture.Scene";
        const int Attente = 90;
        static int images, derniere = -1;

        static Capture() { EditorApplication.update += Tick; }

        static string Argument(string nom)
        {
            var a = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(a, nom);
            return i >= 0 && i + 1 < a.Length ? a[i + 1] : null;
        }

        public static void Photographier()
        {
            string dossier = Argument("-forgeCaptures") ?? Path.GetFullPath(Path.Combine(Application.dataPath, "../../../captures"));
            string scene = EditorBuildSettings.scenes.Where(s => s.enabled).Select(s => s.path).FirstOrDefault();
            if (scene == null)
            {
                Debug.LogError("CAPTURE : aucune scène au build");
                EditorApplication.Exit(2);
                return;
            }
            Directory.CreateDirectory(dossier);
            SessionState.SetString(Dossier, dossier);
            SessionState.SetString(Scene, scene);
            SessionState.SetBool(Flag, true);
            images = 0;
            EditorSceneManager.OpenScene(scene, OpenSceneMode.Single);
            EditorApplication.EnterPlaymode();
        }

        static void Tick()
        {
            if (!SessionState.GetBool(Flag, false) || !Application.isPlaying || derniere == Time.frameCount) return;
            derniere = Time.frameCount;
            if (++images < Attente) return;
            SessionState.SetBool(Flag, false);
            try
            {
                var env = UnityEngine.Object.FindFirstObjectByType<DesertEnvironment>();
                var camera = env != null && env.view != null ? env.view : (Camera.main ?? UnityEngine.Object.FindFirstObjectByType<Camera>());
                if (camera == null)
                {
                    Debug.LogError("CAPTURE : aucune caméra dans la scène");
                    CitadelEditorBridge.Finish(1);
                    return;
                }
                string nom = Path.GetFileNameWithoutExtension(SessionState.GetString(Scene, "scene"));
                string chemin = Path.Combine(SessionState.GetString(Dossier, "."), nom + ".png");
                CitadelPlayCheck.Capture(camera, chemin, 1600, 900);
                Debug.Log("CAPTURE_OK " + chemin);
                CitadelEditorBridge.Finish(0);
            }
            catch (Exception e)
            {
                Debug.LogError("CAPTURE : " + e);
                CitadelEditorBridge.Finish(1);
            }
        }
    }
}
