using System;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Forge.Pont {
    // Lot #524 : `-forgeCarte` ouvre le jeu sur la carte (`pc\Jouer.cmd --carte`). La première scène du build reste la ville
    // du désert ; au lancement, le jeu passe à la scène de la carte, la dernière du build.
    public static class OuvertureDeLaCarte {
        public const string ARGUMENT = "-forgeCarte";
        public const string SCENE = "Forge_Carte";

        public static bool Demandee(string[] arguments) => arguments != null && Array.IndexOf(arguments, ARGUMENT) >= 0;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void AuLancement() {
            if (Demandee(Environment.GetCommandLineArgs()) && SceneManager.GetActiveScene().name != SCENE) SceneManager.LoadScene(SCENE);
        }
    }
}
