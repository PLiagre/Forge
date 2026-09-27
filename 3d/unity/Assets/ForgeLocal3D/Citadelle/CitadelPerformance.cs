using UnityEngine;

namespace ForgeLocal3D
{
    // La visite s'arrête à 60 images/s au lieu de faire tourner la carte à vide.
    public sealed class CitadelPerformance : MonoBehaviour
    {
        void Awake()
        {
            QualitySettings.vSyncCount=0;Application.targetFrameRate=60;
            Application.runInBackground=false;
        }
    }
}
