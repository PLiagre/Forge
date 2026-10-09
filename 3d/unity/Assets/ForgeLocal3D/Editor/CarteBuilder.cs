using System.IO;
using System.Linq;
using Forge.Pont;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace ForgeLocal3D
{
    // Lot 549 : la scène de la carte du joueur, `Forge_Carte`, qui porte `CarteDessinee` sans caméra donnée (le composant crée
    // la sienne et cadre toute la carte), et une lumière tombant à la verticale : la couleur d'une puissance ne dépend pas de
    // l'heure. Elle va en dernier dans la liste du build : la capture et le jeu ouvrent la première, la ville du désert.
    //   Unity -batchmode -quit -projectPath 3d/unity -executeMethod ForgeLocal3D.CarteBuilder.Construire
    public static class CarteBuilder
    {
        public const string Dossier = "Assets/ForgeLocal3D/Carte";
        public const string Nom = "Forge_Carte";
        public const string Chemin = Dossier + "/" + Nom + ".unity";
        public const string CARTE = "Carte de 1400";
        static readonly Color AMBIANCE = new Color(.35f, .35f, .35f);

        [MenuItem("Forge/Carte/Construire la scène")]
        public static void Construire()
        {
            if (!AssetDatabase.IsValidFolder(Dossier)) { Directory.CreateDirectory(Dossier); AssetDatabase.Refresh(); }
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            new GameObject(CARTE).AddComponent<CarteDessinee>();
            var lumiere = new GameObject("Lumière de la carte").AddComponent<Light>();
            lumiere.type = LightType.Directional; lumiere.shadows = LightShadows.None; lumiere.intensity = 1f;
            lumiere.transform.rotation = Quaternion.Euler(90, 0, 0);
            RenderSettings.sun = lumiere; RenderSettings.skybox = null; RenderSettings.fog = false;
            RenderSettings.ambientMode = AmbientMode.Flat; RenderSettings.ambientLight = AMBIANCE;
            if (!EditorSceneManager.SaveScene(scene, Chemin)) throw new IOException("la scène n'a pas pu s'écrire : " + Chemin);
            // En dernier, une seule fois : ce qui précède garde son ordre.
            EditorBuildSettings.scenes = EditorBuildSettings.scenes.Where(s => s.path != Chemin)
                .Append(new EditorBuildSettingsScene(Chemin, true)).ToArray();
            AssetDatabase.SaveAssets();
            Debug.Log("CARTE_SCENE " + Chemin + " : scène " + EditorBuildSettings.scenes.Length + " de la liste du build");
        }
    }
}
