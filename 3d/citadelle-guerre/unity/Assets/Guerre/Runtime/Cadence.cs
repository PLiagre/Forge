using UnityEngine;

namespace Guerre
{
    // Hors mesure, le jeu s'arrête à 60 images/s au lieu de faire tourner la carte à vide.
    public sealed class Cadence : MonoBehaviour
    {
        void Awake()
        {
            QualitySettings.vSyncCount = 0;
            Application.targetFrameRate = 60;
        }
    }
}
