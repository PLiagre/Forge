using System;
using System.Collections;
using System.Linq;
using Forge.Pont;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures
{
    // Lot 549 : la scène `Forge_Carte`, dernière de la liste du build, photographiée entière. La capture ouvre la première
    // scène (la ville du désert) et lance le service ; le scénario charge lui-même la carte à côté, en fait la scène active
    // (sa lumière, sans brouillard), met de côté le désert (tout ce qui ne porte pas la caméra photographiée s'éteint, et ce
    // qui reprend la caméra aussi), attend que les cellules posées égalent celles servies, puis la caméra photographiée copie
    // celle que la carte a créée et cadrée.
    static class Lot549
    {
        const double ATTENTE_S = 30;
        internal const float FORME = 1600f / 900f; // celle de la photo
        const int IMAGES_DE_POSE = 10;

        // Ce que `Ouvrir` a posé : la carte de la scène, cadrée sur toute la carte.
        internal sealed class CarteOuverte { public CarteDessinee Carte; public int Scenes; }

        [ScenarioDeCapture(549, "carte-entiere")]
        static IEnumerator CarteEntiere(Camera camera)
        {
            var ouverte = new CarteOuverte();
            for (var e = Ouvrir(camera, ouverte); e.MoveNext();) yield return null;
            var carte = ouverte.Carte;
            camera.CopyFrom(carte.camera); camera.aspect = FORME; carte.camera.enabled = false;
            Vector3 position = camera.transform.position; Quaternion rotation = camera.transform.rotation;
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            if (camera.transform.position != position || camera.transform.rotation != rotation)
                throw new InvalidOperationException("la caméra a bougé : " + camera.transform.position + " " + camera.transform.eulerAngles);
            Debug.Log("CAPTURE_549 " + carte.CellulesPosees + " cellules posées pour " + carte.CellulesServies + " servies, scène " + ouverte.Scenes + " sur " + ouverte.Scenes);
        }

        // La carte chargée à côté du désert, le désert de côté, les cellules servies posées, la caméra de la carte à la forme
        // de la photo. Les captures des lots de la carte (#524, #525, #526) partent de là. Un `yield return` d'un autre
        // IEnumerator ne l'exécute pas : `for (var e = Ouvrir(camera, o); e.MoveNext();) yield return null;`.
        internal static IEnumerator Ouvrir(Camera camera, CarteOuverte ouverte)
        {
            var liste = EditorBuildSettings.scenes.Where(s => s.enabled).Select(s => s.path).ToArray();
            if (liste.Length < 2 || liste[liste.Length - 1] != CarteBuilder.Chemin || liste[0] == CarteBuilder.Chemin)
                throw new InvalidOperationException("la carte doit être la dernière scène du build, pas la première : " + string.Join(", ", liste));

            var chargement = SceneManager.LoadSceneAsync(CarteBuilder.Nom, LoadSceneMode.Additive)
                ?? throw new InvalidOperationException("la scène " + CarteBuilder.Nom + " ne se charge pas");
            double echeance = Time.realtimeSinceStartupAsDouble + ATTENTE_S;
            while (!chargement.isDone)
            {
                if (Time.realtimeSinceStartupAsDouble > echeance) throw new InvalidOperationException(CarteBuilder.Nom + " pas chargée en " + ATTENTE_S + " s");
                yield return null;
            }
            Scene scene = SceneManager.GetSceneByName(CarteBuilder.Nom);
            SceneManager.SetActiveScene(scene);
            Ecarter(camera);

            var cartes = scene.GetRootGameObjects().SelectMany(r => r.GetComponentsInChildren<CarteDessinee>()).ToArray();
            if (cartes.Length != 1) throw new InvalidOperationException(CarteBuilder.Nom + " porte " + cartes.Length + " CarteDessinee, il en faut une");
            var carte = cartes[0];
            if (carte.name != CarteBuilder.CARTE) throw new InvalidOperationException("la carte s'appelle « " + carte.name + " », pas « " + CarteBuilder.CARTE + " »");
            echeance = Time.realtimeSinceStartupAsDouble + ATTENTE_S;
            while (carte.CellulesServies < 0)
            {
                if (Time.realtimeSinceStartupAsDouble > echeance) throw new InvalidOperationException("aucune carte posée en " + ATTENTE_S + " s : " + carte.TexteAffiche);
                yield return null;
            }
            if (carte.CellulesPosees == 0 || carte.CellulesPosees != carte.CellulesServies)
                throw new InvalidOperationException(carte.CellulesPosees + " cellules posées pour " + carte.CellulesServies + " servies");
            if (carte.camera == null || carte.camera.gameObject.scene != scene)
                throw new InvalidOperationException("la carte n'a pas créé sa caméra dans " + CarteBuilder.Nom);

            carte.camera.aspect = FORME; yield return null; // le composant recadre
            ouverte.Carte = carte; ouverte.Scenes = liste.Length;
        }

        // Le désert de côté : dans sa scène, tout objet qui ne mène pas à la caméra photographiée s'éteint, ses enfants aussi ;
        // sur la caméra, ce qui la reprendrait à chaque image.
        static void Ecarter(Camera camera)
        {
            foreach (GameObject racine in camera.gameObject.scene.GetRootGameObjects()) Ecarter(racine.transform, camera.transform);
            foreach (Behaviour b in new Behaviour[] { camera.GetComponent<DesertCityCamera>(), camera.GetComponent<VillageV2Visit>() })
                if (b != null) b.enabled = false;
        }

        static void Ecarter(Transform t, Transform camera)
        {
            if (t == camera) { foreach (Transform enfant in t) enfant.gameObject.SetActive(false); return; }
            if (!camera.IsChildOf(t)) { t.gameObject.SetActive(false); return; }
            foreach (Renderer r in t.GetComponents<Renderer>()) r.enabled = false;
            foreach (Transform enfant in t) Ecarter(enfant, camera);
        }
    }
}
