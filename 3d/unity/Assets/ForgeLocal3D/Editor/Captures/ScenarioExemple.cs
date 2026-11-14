using System.Collections;
using UnityEngine;

namespace ForgeLocal3D.Captures
{
    // L'exemple d'un scénario de capture (groupe « exemple » : il ne joue qu'avec `-forgeScenario exemple`).
    // Un scénario s'écrit dans ce dossier, dans un fichier nommé d'après ce qu'il montre : il y pose ce
    // qu'on veut voir (un bâtiment du kit, une route, un habitant) ou joue un geste, et place la caméra
    // pour que la photo le montre. Une photo identique au plan fixe ne prouve rien.
    static class ScenarioExemple
    {
        const float DISTANCE_M = 60f;
        const float INCLINAISON = 30f;
        const int IMAGES_DE_POSE = 10;

        // La caméra descend vers ce qu'elle vise. Elle passe par `DesertCityCamera.Poser`, la seule entrée de
        // la caméra de la capitale : déplacer `camera.transform` à la main, elle le reprendrait à l'image
        // suivante, et la photo serait le plan fixe.
        [ScenarioDeCapture("exemple", "descente")]
        static IEnumerator Descente(Camera camera)
        {
            var ville = Object.FindFirstObjectByType<DesertCityCamera>();
            if (ville == null)
                throw new System.InvalidOperationException("la scène n'a pas de DesertCityCamera");
            ville.Poser(ville.Vise, ville.Cap, INCLINAISON, DISTANCE_M);
            // Quelques images : les ombres et le terrain se recalculent à la nouvelle place.
            for (int i = 0; i < IMAGES_DE_POSE; i++)
                yield return null;
        }
    }
}
