using Forge.Pont;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem;

namespace ForgeLocal3D
{
    // Le joueur parcourt sa carte. Il glisse, bouton gauche ou du milieu enfoncé, pour se déplacer : le point du sol
    // qu'il a saisi reste sous sa souris. La molette le rapproche ou l'éloigne du point du sol sous la souris. La vue
    // (`VueDeCarte`) ne sort jamais de la carte servie. Avant la carte : la vue s'y applique dans la même image. Avec
    // `automatique`, rien n'est lu : une épreuve ou une capture appelle la vue elle-même, comme ce composant le
    // ferait. Un geste commencé sur un bouton (l'horloge) ne bouge pas la carte. Le geste lui-même est `ParcoursDeVue`.
    [DefaultExecutionOrder(-10)]
    [RequireComponent(typeof(CarteDessinee))]
    public sealed class ParcoursDeCarte : MonoBehaviour
    {
        public bool automatique;
        CarteDessinee carte;
        readonly ParcoursDeVue geste = new ParcoursDeVue();
        bool surLaCarte; // le bouton a été enfoncé sur la carte, pas sur un bouton du panneau

        void Awake() => carte = GetComponent<CarteDessinee>();

        void Update()
        {
            var souris = Mouse.current;
            if (automatique || carte.Vue == null || souris == null || carte.camera == null) return;
            bool surUnBouton = EventSystem.current != null && EventSystem.current.IsPointerOverGameObject();
            bool enfonce = souris.leftButton.wasPressedThisFrame || souris.middleButton.wasPressedThisFrame, tenu = souris.leftButton.isPressed || souris.middleButton.isPressed;
            if (enfonce) surLaCarte = !surUnBouton;
            if (!tenu) surLaCarte = false;
            // 120 par cran sous Windows, 1 selon la version du paquet (comme la caméra de la ville).
            float molette = souris.scroll.ReadValue().y, crans = Mathf.Abs(molette) >= 20 ? molette / 120 : molette;
            geste.Pas(carte, souris.position.ReadValue(), enfonce && surLaCarte, tenu && surLaCarte, surUnBouton ? 0f : crans);
        }
    }
}
