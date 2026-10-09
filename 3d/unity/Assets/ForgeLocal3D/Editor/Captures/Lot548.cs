using System;
using System.Collections;
using Forge.Pont;
using UnityEngine;

namespace ForgeLocal3D.Captures
{
    // Lot 548 : la carte de 1400 à 20 km au-dessus du désert, ses contours et ses noms, cadrée par sa propre caméra, que la
    // caméra photographiée copie. On éteint ce qui reprend la caméra, le brouillard et le panneau des routes, comme au lot 547.
    static class Lot548
    {
        const double ATTENTE_S = 30;
        const float FORME = 1600f / 900f; // celle de la photo

        [ScenarioDeCapture(548, "carte-contours-et-villes")]
        static IEnumerator CarteContoursEtVilles(Camera camera)
        {
            var objet = new GameObject("Carte de 1400"); objet.transform.position = new Vector3(0, 20000, 0);
            var carte = objet.AddComponent<CarteDessinee>(); // sans caméra donnée : elle crée la sienne
            double echeance = Time.realtimeSinceStartupAsDouble + ATTENTE_S;
            while (carte.CellulesServies < 0)
            {
                if (Time.realtimeSinceStartupAsDouble > echeance)
                    throw new InvalidOperationException("aucune carte posée en " + ATTENTE_S + " s : " + carte.TexteAffiche);
                yield return null;
            }
            if (carte.CellulesPosees == 0 || carte.CellulesPosees != carte.CellulesServies)
                throw new InvalidOperationException(carte.CellulesPosees + " cellules posées pour " + carte.CellulesServies + " servies");
            if (objet.GetComponentsInChildren<LineRenderer>().Length == 0) throw new InvalidOperationException("aucun contour sous la carte");
            if (objet.GetComponentsInChildren<TextMesh>().Length == 0) throw new InvalidOperationException("aucun nom de ville sous la carte");
            carte.camera.aspect = FORME; yield return null; // le composant recadre
            foreach (Behaviour b in new Behaviour[] { camera.GetComponent<DesertCityCamera>(), camera.GetComponent<VillageV2Visit>(), UnityEngine.Object.FindFirstObjectByType<DesertEnvironment>() })
                if (b != null) b.enabled = false;
            RenderSettings.fog = false; camera.transform.Find("Panneau des routes")?.gameObject.SetActive(false);
            camera.CopyFrom(carte.camera); camera.aspect = FORME; carte.camera.enabled = false;
            Vector3 position = camera.transform.position; Quaternion rotation = camera.transform.rotation;
            for (int i = 0; i < 10; i++) yield return null; // les 10 images de pose
            if (camera.transform.position != position || camera.transform.rotation != rotation)
                throw new InvalidOperationException("la caméra a bougé : " + camera.transform.position + " " + camera.transform.eulerAngles);
        }
    }
}
