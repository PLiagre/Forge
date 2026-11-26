using UnityEngine;

namespace Forge.Pont {
    // La fenêtre du jeu tient dans l'écran. Lancé en fenêtre à la taille de l'écran (`-screen-width 1920 -screen-height
    // 1080 -screen-fullscreen 0`), le jeu y ajoute la barre de titre de Windows : le bas de l'image passe sous le bord de
    // l'écran, une bande noire d'une trentaine de pixels qui coupe les boutons du bas. Une fenêtre au moins aussi haute ou
    // aussi large que l'écran passe donc, au démarrage, en plein écran fenêtré, sans bord, à la taille de l'écran ; une
    // fenêtre plus petite garde sa taille, et le plein écran demandé reste tel quel. L'éditeur n'est jamais touché.
    public static class FenetreDuJeu {
        public static bool Deborde(int largeur, int hauteur, int largeurDeLEcran, int hauteurDeLEcran, FullScreenMode mode) =>
            mode == FullScreenMode.Windowed && largeurDeLEcran > 0 && hauteurDeLEcran > 0 && (largeur >= largeurDeLEcran || hauteur >= hauteurDeLEcran);

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        private static void Ajuster() {
            if (Application.isEditor) return;
            Display ecran = Display.main;
            if (!Deborde(Screen.width, Screen.height, ecran.systemWidth, ecran.systemHeight, Screen.fullScreenMode)) return;
            Debug.Log("FENETRE : " + Screen.width + " × " + Screen.height + " en fenêtre ne tient pas dans l'écran de " + ecran.systemWidth + " × " + ecran.systemHeight + " : plein écran fenêtré");
            Screen.SetResolution(ecran.systemWidth, ecran.systemHeight, FullScreenMode.FullScreenWindow);
        }
    }
}
