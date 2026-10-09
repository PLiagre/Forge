using Forge.Pont;
using UnityEngine;
using UnityEngine.InputSystem;

namespace ForgeLocal3D
{
    // Lot #525 : les touches de l'horloge de la carte. Espace met en pause ou relance, + accélère, − ralentit ; les boutons
    // du panneau font la même chose. Avec `automatique`, rien n'est lu.
    [RequireComponent(typeof(HorlogeDeCarte))]
    public sealed class CommandesDuTemps : MonoBehaviour
    {
        public bool automatique;
        HorlogeDeCarte horloge;

        void Awake() => horloge = GetComponent<HorlogeDeCarte>();

        void Update()
        {
            var k = Keyboard.current;
            if (automatique || k == null) return;
            if (k.spaceKey.wasPressedThisFrame) horloge.Basculer();
            if (k.numpadPlusKey.wasPressedThisFrame || k.equalsKey.wasPressedThisFrame) horloge.Accelerer();
            if (k.numpadMinusKey.wasPressedThisFrame || k.minusKey.wasPressedThisFrame) horloge.Ralentir();
        }
    }
}
