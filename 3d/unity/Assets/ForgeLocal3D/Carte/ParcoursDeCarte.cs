using Forge.Pont;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem;

namespace ForgeLocal3D
{
    // Lot #524 : le joueur parcourt sa carte. Il glisse, bouton gauche ou du milieu enfoncé, pour se déplacer ; la molette
    // le rapproche ou l'éloigne du point sous la souris. La vue (`VueDeCarte`) ne sort jamais de la carte servie. Avant la
    // carte : la vue s'y applique dans la même image. Avec `automatique`, rien n'est lu : une épreuve ou une capture appelle
    // la vue elle-même, comme ce composant le ferait. Un geste commencé sur un bouton (l'horloge, #525) ne bouge pas la carte.
    [DefaultExecutionOrder(-10)]
    [RequireComponent(typeof(CarteDessinee))]
    public sealed class ParcoursDeCarte : MonoBehaviour
    {
        public bool automatique;
        CarteDessinee carte;
        bool glisse; // le bouton a été enfoncé sur la carte, pas sur un bouton du panneau

        void Awake() => carte = GetComponent<CarteDessinee>();

        void Update()
        {
            var vue = carte.Vue; var souris = Mouse.current;
            if (automatique || vue == null || souris == null || carte.camera == null) return;
            bool surUnBouton = EventSystem.current != null && EventSystem.current.IsPointerOverGameObject();
            if (souris.leftButton.wasPressedThisFrame || souris.middleButton.wasPressedThisFrame) glisse = !surUnBouton;
            if (!souris.leftButton.isPressed && !souris.middleButton.isPressed) glisse = false;
            if (glisse) vue.Glisser(souris.delta.ReadValue(), carte.camera.pixelHeight);
            if (surUnBouton) return;
            // 120 par cran sous Windows, 1 selon la version du paquet (comme la caméra de la ville).
            float molette = souris.scroll.ReadValue().y, crans = Mathf.Abs(molette) >= 20 ? molette / 120 : molette;
            if (crans != 0) vue.Zoomer(crans, carte.camera.ScreenToViewportPoint(souris.position.ReadValue()));
        }
    }
}
