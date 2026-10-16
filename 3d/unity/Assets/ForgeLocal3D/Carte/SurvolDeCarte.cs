using Forge.Pont;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem;

namespace ForgeLocal3D
{
    // Lot #526 : la souris survole la carte, et la fiche de la cellule dessous s'ouvre. Sur un panneau (l'horloge), ou hors
    // de la fenêtre, la fiche se cache. Avec `automatique`, rien n'est lu : une épreuve ou une capture survole elle-même.
    // Lot #613 : un clic choisit la terre sous la souris. Si le pointeur dépasse SEUIL_CLIC_PX pendant le geste, même
    // en revenant au point d'appui, ce n'est pas un clic : ParcoursDeCarte garde le glissé.
    [RequireComponent(typeof(FicheDeCellule))]
    public sealed class SurvolDeCarte : MonoBehaviour
    {
        public const float SEUIL_CLIC_PX = 6f;
        public bool automatique;
        FicheDeCellule fiche;
        ReperesDeDepart reperes; // lot #624 : le même survol ouvre la fiche de la terre sous la souris
        readonly GesteDeClic geste = new GesteDeClic();

        void Awake() { fiche = GetComponent<FicheDeCellule>(); reperes = GetComponent<ReperesDeDepart>(); }

        void Update()
        {
            var souris = Mouse.current;
            if (automatique || souris == null) return;
            Vector2 ici = souris.position.ReadValue();
            Survoler(ici);
            if (geste.Noter(ici, souris.leftButton.wasPressedThisFrame, souris.leftButton.wasReleasedThisFrame)) Cliquer(ici);
        }

        public void Survoler(Vector2 position)
        {
            if (Libre(position)) { fiche.Survoler(position); if (reperes != null) reperes.Survoler(position); }
            else { fiche.Quitter(); if (reperes != null) reperes.Quitter(); }
        }

        public void Cliquer(Vector2 position) { if (Libre(position) && reperes != null) reperes.Choisir(position); }

        // Dans la fenêtre, et pas sur un panneau.
        static bool Libre(Vector2 position) => position.x >= 0 && position.y >= 0 && position.x < Screen.width && position.y < Screen.height
            && !(EventSystem.current != null && EventSystem.current.IsPointerOverGameObject());

        // Le relâché choisit seulement si l'écart au point d'appui n'a jamais dépassé le seuil pendant le geste.
        public sealed class GesteDeClic {
            Vector2? appui; bool eloigne;
            public bool Noter(Vector2 ici, bool appuiFrame, bool relache) {
                if (appuiFrame) { appui = ici; eloigne = false; }
                if (appui is Vector2 depart && (ici - depart).magnitude > SEUIL_CLIC_PX) eloigne = true;
                bool clic = relache && appui != null && !eloigne; if (relache) appui = null; return clic;
            }
        }
    }
}
