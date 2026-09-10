using UnityEngine;

namespace Victoria.CityMode
{
    public static class CityLabBootstrap
    {
        /// <summary>
        /// Explicit laboratory-only entry point. Production hosts must open a
        /// CityModeSession and own their presentation lifecycle instead.
        /// </summary>
        public static CityLabGame StartLaboratory()
        {
            var current = Object.FindFirstObjectByType<CityLabGame>();
            if (current != null)
                return current;
            var root = new GameObject("CityLab Runtime");
            return root.AddComponent<CityLabGame>();
        }

        public static void StopLaboratory(CityLabGame instance)
        {
            if (instance == null)
                return;
            if (Application.isPlaying)
                Object.Destroy(instance.gameObject);
            else
                Object.DestroyImmediate(instance.gameObject);
        }
    }
}

