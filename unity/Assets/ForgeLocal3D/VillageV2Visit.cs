using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.SceneManagement;

namespace ForgeLocal3D
{
    // Visite graphique. La caméra ne lit ni n'écrit le moteur de simulation.
    public sealed class VillageV2Visit : MonoBehaviour
    {
        public string village;
        public string description;
        public string[] sceneNames;
        public string[] labels;
        public Vector3 focus = new Vector3(0, 7, -8);
        public float distance = 365;
        public float yaw = 217;
        public float pitch = 35;
        public float minPitch = 18;
        public float focusLimit = 130;
        public float zoomRatio = .285f;
        public bool showInterface = true;
        Camera view;
        Vector3 originalFocus;
        float originalDistance, originalYaw, originalPitch;
        bool showHelp = true;

        void Awake()
        {
            view = GetComponent<Camera>();
            originalFocus = focus;
            originalDistance = distance;
            originalYaw = yaw;
            originalPitch = pitch;
        }

        void LateUpdate()
        {
            var keyboard = Keyboard.current;
            var mouse = Mouse.current;
            if (keyboard == null || mouse == null) return;
            bool blocked=CitadelConstruction.Current&&CitadelConstruction.Current.BlocksPointer;
            if (keyboard.hKey.wasPressedThisFrame) showHelp = !showHelp;
            if (keyboard.fKey.wasPressedThisFrame)
            {
                focus = originalFocus; distance = originalDistance;
                yaw = originalYaw; pitch = originalPitch;
            }
            if (keyboard.f1Key.wasPressedThisFrame) Change(0);
            if (keyboard.f2Key.wasPressedThisFrame) Change(1);
            if (keyboard.f3Key.wasPressedThisFrame) Change(2);
            if (keyboard.f4Key.wasPressedThisFrame) Change(3);
            var move = Vector3.zero;
            if (keyboard.upArrowKey.isPressed || keyboard.wKey.isPressed) move.z++;
            if (keyboard.downArrowKey.isPressed || keyboard.sKey.isPressed) move.z--;
            if (keyboard.leftArrowKey.isPressed || keyboard.aKey.isPressed) move.x--;
            if (keyboard.rightArrowKey.isPressed || keyboard.dKey.isPressed) move.x++;
            focus += Quaternion.Euler(0, yaw, 0) * move.normalized * distance * .3f * Time.unscaledDeltaTime;
            focus.x = Mathf.Clamp(focus.x, -focusLimit, focusLimit);
            focus.z = Mathf.Clamp(focus.z, -focusLimit, focusLimit);
            if (!blocked&&mouse.middleButton.isPressed)
            {
                Vector2 delta = mouse.delta.ReadValue();
                focus += Quaternion.Euler(0, yaw, 0) * new Vector3(-delta.x, 0, -delta.y) * distance * .0007f;
            }
            if (!blocked&&mouse.rightButton.isPressed)
            {
                Vector2 delta = mouse.delta.ReadValue();
                yaw += delta.x * .17f;
                pitch = Mathf.Clamp(pitch - delta.y * .17f, minPitch, 82);
            }
            if(!blocked)distance = Mathf.Clamp(distance - mouse.scroll.ReadValue().y * .10f, 20, 450);
            var rotation = Quaternion.Euler(pitch, yaw, 0);
            transform.SetPositionAndRotation(focus + rotation * Vector3.back * distance, rotation);
            view.orthographicSize = distance * zoomRatio;
        }

        void Change(int index)
        {
            if (sceneNames == null || index >= sceneNames.Length) return;
            SceneManager.LoadScene(sceneNames[index]);
        }

        void OnGUI()
        {
            if (!showHelp || !showInterface) return;
            float width = Mathf.Min(Screen.width - 40, 540);
            GUI.color = new Color(.07f, .11f, .09f, .94f);
            GUI.DrawTexture(new Rect(20, 20, width, 112), Texture2D.whiteTexture);
            GUI.color = new Color(.95f, .92f, .81f);
            GUI.Label(new Rect(38, 31, width - 30, 22), "FORGE  /  ATLAS DES VILLAGES", new GUIStyle(GUI.skin.label) { fontSize = 12 });
            GUI.Label(new Rect(36, 52, width - 30, 40), village, new GUIStyle(GUI.skin.label) { fontSize = 28, fontStyle = FontStyle.Bold });
            GUI.Label(new Rect(38, 96, width - 30, 25), description, new GUIStyle(GUI.skin.label) { fontSize = 14 });
            if (labels != null)
                for (int i = 0; i < labels.Length; i++)
                    if (GUI.Button(new Rect(20 + i * 164, 144, 156, 30), "F" + (i + 1) + " · " + labels[i])) Change(i);
            GUI.Label(new Rect(24, Screen.height - 35, Screen.width - 48, 28),
                "Flèches : déplacer   ·   Molette : zoom   ·   Clic droit : tourner   ·   Clic milieu : glisser   ·   F : vue générale   ·   H : aide",
                new GUIStyle(GUI.skin.label) { fontSize = 13 });
        }
    }
}
