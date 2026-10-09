using Forge.Pont;
using UnityEngine;
using UnityEngine.InputSystem;

namespace ForgeLocal3D
{
    // Lot #524 : le joueur parcourt sa carte. Il glisse, bouton gauche ou du milieu enfoncé, pour se déplacer ; la molette
    // le rapproche ou l'éloigne du point sous la souris. La vue (`VueDeCarte`) ne sort jamais de la carte servie. Avant la
    // carte : la vue s'y applique dans la même image. Avec `automatique`, rien n'est lu : une épreuve ou une capture appelle
    // la vue elle-même, comme ce composant le ferait.
    [DefaultExecutionOrder(-10)]
    [RequireComponent(typeof(CarteDessinee))]
    public sealed class ParcoursDeCarte : MonoBehaviour
    {
        public bool automatique;
        CarteDessinee carte;

        void Awake() => carte = GetComponent<CarteDessinee>();

        void Update()
        {
            var vue = carte.Vue; var souris = Mouse.current;
            if (automatique || vue == null || souris == null || carte.camera == null) return;
            if (souris.leftButton.isPressed || souris.middleButton.isPressed) vue.Glisser(souris.delta.ReadValue(), carte.camera.pixelHeight);
            // 120 par cran sous Windows, 1 selon la version du paquet (comme la caméra de la ville).
            float molette = souris.scroll.ReadValue().y, crans = Mathf.Abs(molette) >= 20 ? molette / 120 : molette;
            if (crans != 0) vue.Zoomer(crans, carte.camera.ScreenToViewportPoint(souris.position.ReadValue()));
        }
    }
}
