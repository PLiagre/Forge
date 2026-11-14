using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;

namespace ForgeLocal3D.Captures {
    // Avant DesertRoadTool : la touche est dans l'état dynamique, visible par wasPressedThisFrame.
    [DefaultExecutionOrder(-10000)]
    sealed class Frappe : MonoBehaviour {
        public static Key? tenue; public static bool armee;
        void Update() {
            if (!armee) return; Keyboard k = Keyboard.current; if (k == null || !k.added) k = InputSystem.AddDevice<Keyboard>(); if (!k.enabled) InputSystem.EnableDevice(k);
            k.MakeCurrent(); InputState.Change(k, tenue is Key t ? new KeyboardState(t) : new KeyboardState(), InputUpdateType.Dynamic); armee = false; }
    }
}
