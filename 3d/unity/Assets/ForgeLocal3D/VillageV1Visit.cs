using UnityEngine;
using UnityEngine.InputSystem;

namespace ForgeLocal3D
{
    // Caméra de visite uniquement : aucune donnée du moteur n'est modifiée.
    public sealed class VillageV1Visit : MonoBehaviour
    {
        Vector3 focus = new Vector3(0, 1, 0);
        float distance = 278;
        float yaw = 220.6f;
        float pitch = 34.0f;
        bool showHelp = true;

        void LateUpdate()
        {
            var keyboard = Keyboard.current;
            var mouse = Mouse.current;
            if (keyboard == null || mouse == null) return;
            if (keyboard.hKey.wasPressedThisFrame) showHelp = !showHelp;
            if (keyboard.fKey.wasPressedThisFrame)
            {
                focus = new Vector3(0, 1, 0); distance = 278; yaw = 220.6f; pitch = 34;
            }
            var move = Vector3.zero;
            if (keyboard.wKey.isPressed || keyboard.upArrowKey.isPressed) move.z += 1;
            if (keyboard.sKey.isPressed || keyboard.downArrowKey.isPressed) move.z -= 1;
            if (keyboard.aKey.isPressed || keyboard.leftArrowKey.isPressed) move.x -= 1;
            if (keyboard.dKey.isPressed || keyboard.rightArrowKey.isPressed) move.x += 1;
            focus += Quaternion.Euler(0, yaw, 0) * move.normalized * (distance * .35f * Time.unscaledDeltaTime);
            focus.x = Mathf.Clamp(focus.x, -70, 70);
            focus.z = Mathf.Clamp(focus.z, -70, 70);
            distance = Mathf.Clamp(distance - mouse.scroll.ReadValue().y * .075f, 16, 320);
            if (mouse.rightButton.isPressed)
            {
                var delta = mouse.delta.ReadValue();
                yaw += delta.x * .17f;
                pitch = Mathf.Clamp(pitch - delta.y * .17f, 18, 80);
            }
            var rotation = Quaternion.Euler(pitch, yaw, 0);
            transform.SetPositionAndRotation(focus + rotation * Vector3.back * distance, rotation);
            GetComponent<Camera>().orthographicSize = distance * .277f;
        }

        void OnGUI()
        {
            if (!showHelp) return;
            GUI.color = new Color(.09f, .13f, .10f, .9f);
            GUI.DrawTexture(new Rect(24, 24, 370, 96), Texture2D.whiteTexture);
            GUI.color = new Color(.95f, .92f, .81f);
            var title = new GUIStyle(GUI.skin.label) { fontSize = 29, fontStyle = FontStyle.Bold };
            var text = new GUIStyle(GUI.skin.label) { fontSize = 14 };
            GUI.Label(new Rect(42, 35, 340, 38), "FORGE  /  LE BOURG", title);
            GUI.Label(new Rect(43, 79, 335, 30), "V1 graphique • village pilote • assets Blender", text);
            GUI.Label(new Rect(26, Screen.height - 40, 1000, 30),
                "Flèches : déplacement    •    Molette : zoom    •    Clic droit : orbite    •    F : vue générale    •    H : aide", text);
        }
    }
}
