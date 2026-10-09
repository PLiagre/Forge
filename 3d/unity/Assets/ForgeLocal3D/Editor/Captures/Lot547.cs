using System;
using System.Collections;
using Forge.Pont;
using UnityEngine;

namespace ForgeLocal3D.Captures
{
    // Lot 547 : la carte de 1400 servie par `sim/`, à 20 km au-dessus du désert, vue d'en haut, nord en haut, entière à 3,3 km
    // et 60°. On éteint ce qui reprend la caméra ou rallume le brouillard (fin à 1 500 m), et le panneau des routes qui la cache.
    static class Lot547
    {
        const double ATTENTE_S = 30;
        static readonly Vector3 CARTE = new Vector3(0, 20000, 0), CAMERA = new Vector3(0, 23300, 0);
        static readonly Quaternion VERS_LE_BAS = Quaternion.Euler(90, 0, 0);

        [ScenarioDeCapture(547, "carte-des-cellules")]
        static IEnumerator CarteDesCellules(Camera camera)
        {
            var objet = new GameObject("Carte des cellules"); objet.transform.position = CARTE;
            var carte = objet.AddComponent<CarteDessinee>(); carte.camera = camera;
            double echeance = Time.realtimeSinceStartupAsDouble + ATTENTE_S;
            while (carte.CellulesServies < 0)
            {
                if (Time.realtimeSinceStartupAsDouble > echeance)
                    throw new InvalidOperationException("aucune carte posée en " + ATTENTE_S + " s : " + carte.TexteAffiche);
                yield return null;
            }
            if (carte.CellulesPosees == 0 || carte.CellulesPosees != carte.CellulesServies)
                throw new InvalidOperationException(carte.CellulesPosees + " cellules posées pour " + carte.CellulesServies + " servies");
            foreach (Behaviour b in new Behaviour[] { camera.GetComponent<DesertCityCamera>(), camera.GetComponent<VillageV2Visit>(), UnityEngine.Object.FindFirstObjectByType<DesertEnvironment>() })
                if (b != null) b.enabled = false;
            RenderSettings.fog = false; camera.transform.Find("Panneau des routes")?.gameObject.SetActive(false);
            camera.transform.SetPositionAndRotation(CAMERA, VERS_LE_BAS);
            camera.orthographic = false; camera.fieldOfView = 60; camera.nearClipPlane = 10; camera.farClipPlane = 10000;
            for (int i = 0; i < 10; i++) yield return null; // les 10 images de pose
            if (camera.transform.position != CAMERA || camera.transform.rotation != VERS_LE_BAS)
                throw new InvalidOperationException("la caméra a bougé : " + camera.transform.position + " " + camera.transform.eulerAngles);
        }
    }
}
