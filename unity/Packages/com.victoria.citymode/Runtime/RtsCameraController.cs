using UnityEngine;
using UnityEngine.InputSystem;

namespace Victoria.CityMode
{
    public sealed class RtsCameraController : MonoBehaviour
    {
        public Vector3 focus = Vector3.zero;
        public float distance = 85f;
        public float yaw = 35f;
        public float pitch = 48f;
        public float moveSpeed = 45f;
        public float edgeSize = 10f;

        void LateUpdate()
        {
            var keyboard = Keyboard.current;
            var mouse = Mouse.current;
            if (keyboard == null || mouse == null)
                return;

            var move = Vector2.zero;
            if (keyboard.wKey.isPressed) move.y += 1f;
            if (keyboard.sKey.isPressed) move.y -= 1f;
            if (keyboard.dKey.isPressed) move.x += 1f;
            if (keyboard.aKey.isPressed) move.x -= 1f;

            var pointer = mouse.position.ReadValue();
            if (pointer.x <= edgeSize) move.x -= 1f;
            if (pointer.x >= Screen.width - edgeSize) move.x += 1f;
            if (pointer.y <= edgeSize) move.y -= 1f;
            if (pointer.y >= Screen.height - edgeSize) move.y += 1f;

            var planarRotation = Quaternion.Euler(0f, yaw, 0f);
            var planar = planarRotation * new Vector3(move.x, 0f, move.y);
            focus += planar.normalized * (moveSpeed * Mathf.Lerp(0.45f, 1.8f, distance / 180f)) * Time.unscaledDeltaTime;
            focus.x = Mathf.Clamp(focus.x, -245f, 245f);
            focus.z = Mathf.Clamp(focus.z, -245f, 245f);

            var scroll = mouse.scroll.ReadValue().y;
            distance = Mathf.Clamp(distance - scroll * 0.025f, 18f, 180f);

            if (mouse.rightButton.isPressed)
            {
                var delta = mouse.delta.ReadValue();
                yaw += delta.x * 0.18f;
                pitch = Mathf.Clamp(pitch - delta.y * 0.14f, 25f, 75f);
            }

            if (keyboard.fKey.wasPressedThisFrame)
            {
                focus = Vector3.zero;
                distance = 85f;
                yaw = 35f;
                pitch = 48f;
            }

            var rotation = Quaternion.Euler(pitch, yaw, 0f);
            transform.SetPositionAndRotation(focus - rotation * Vector3.forward * distance, rotation);
        }
    }
}

