using System.Collections;
using UnityEngine;

namespace ForgeLocal3D.Captures
{
    // L'exemple que suit un lot Unity pour sa photo (lot 0 : il ne joue qu'avec `-forgeLot 0`).
    // Un lot écrit son scénario dans ce dossier, `Lot<numéro>.cs`, avec son numéro : il y pose ce qu'il
    // ajoute (un bâtiment du kit, une route, un habitant) ou joue son geste, et place la caméra pour que
    // la photo montre ce qu'il a changé. La chaîne refuse une photo identique au plan fixe.
    static class ScenarioExemple
    {
        const float DISTANCE_M = 60f;
        const float INCLINAISON = 30f;
        const int IMAGES_DE_POSE = 10;

        // La caméra descend vers ce qu'elle vise. Elle passe par `DesertCityCamera.Poser`, la seule entrée de
        // la caméra de la capitale : déplacer `camera.transform` à la main, elle le reprendrait à l'image
        // suivante, et la photo serait le plan fixe.
        [ScenarioDeCapture(0, "descente")]
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
