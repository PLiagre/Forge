using Forge.Pont;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem;

namespace ForgeLocal3D
{
    // Lot #526 : la souris survole la carte, et la fiche de la cellule dessous s'ouvre. Sur un panneau (l'horloge), ou hors
    // de la fenêtre, la fiche se cache. Avec `automatique`, rien n'est lu : une épreuve ou une capture survole elle-même.
    [RequireComponent(typeof(FicheDeCellule))]
    public sealed class SurvolDeCarte : MonoBehaviour
    {
        public bool automatique;
        FicheDeCellule fiche;

        void Awake() => fiche = GetComponent<FicheDeCellule>();

        void Update()
        {
            var souris = Mouse.current;
            if (automatique || souris == null) return;
            Vector2 position = souris.position.ReadValue();
            bool dansLaFenetre = position.x >= 0 && position.y >= 0 && position.x < Screen.width && position.y < Screen.height;
            bool surUnPanneau = EventSystem.current != null && EventSystem.current.IsPointerOverGameObject();
            if (dansLaFenetre && !surUnPanneau) fiche.Survoler(position); else fiche.Quitter();
        }
    }
}
