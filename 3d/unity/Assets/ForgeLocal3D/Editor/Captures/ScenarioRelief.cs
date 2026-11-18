using System;
using System.Collections;
using System.Linq;
using Forge.Pont;
using UnityEngine;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures
{
    // Le terrain de la carte, photographié branché au service : toute la carte, puis quatre vues de plus en plus
    // proches, sur des montagnes, des côtes découpées, des frontières serrées et un rivage, où se jugent les traits
    // que le terrain dessine. Les vues se cadrent sur une ville servie, jamais sur un point écrit en dur ; une ville
    // que la carte ne sert pas fait échouer le scénario.
    static class ScenarioRelief
    {
        const float DEMI_ALPES_KM = 420f, DEMI_EGEE_KM = 380f, DEMI_FRONTIERES_KM = 110f, DEMI_RIVAGE_KM = 60f; const int IMAGES_DE_POSE = 12;

        [ScenarioDeCapture("relief", "01-toute-la-carte")]
        static IEnumerator TouteLaCarte(Camera camera)
        {
            SceneManager.LoadScene(OuvertureDeLaCarte.SCENE);
            CarteDessinee carte = null;
            for (var e = AttentesDeCapture.Jusqua(() => (carte = Object.FindFirstObjectByType<CarteDessinee>()) != null && carte.Vue != null && carte.camera != null && carte.CellulesPosees > 0,
                () => "carte non posée (" + (carte == null ? "pas de carte" : carte.TexteAffiche) + ")"); e.MoveNext();) yield return null;
            carte.camera.rect = new Rect(0, 0, 1, 1);
            carte.Vue.Changer(carte.camera.aspect); carte.Vue.Centrer(carte.Vue.Centre, carte.Vue.DemiMax); carte.Vue.Poser(carte.camera, carte.transform, CarteDessinee.HAUTEUR_CAMERA);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            yield return carte.camera;
        }

        [ScenarioDeCapture("relief", "02-montagnes")]
        static IEnumerator Montagnes(Camera camera) => Sur("Milan", DEMI_ALPES_KM);

        [ScenarioDeCapture("relief", "03-cotes")]
        static IEnumerator Cotes(Camera camera) => Sur("Athènes", DEMI_EGEE_KM);

        [ScenarioDeCapture("relief", "04-frontieres")]
        static IEnumerator Frontieres(Camera camera) => Sur("Mantoue", DEMI_FRONTIERES_KM);

        [ScenarioDeCapture("relief", "05-rivage")]
        static IEnumerator Rivage(Camera camera) => Sur("Gênes", DEMI_RIVAGE_KM);

        static IEnumerator Sur(string ville, float demi)
        {
            var carte = Object.FindFirstObjectByType<CarteDessinee>();
            if (carte == null || carte.Vue == null || carte.Lue == null) throw new InvalidOperationException("la carte n'est pas ouverte : « 01-toute-la-carte » n'a pas réussi");
            VilleDeCarte servie = carte.Lue.Cellules.SelectMany(c => c.Villes).FirstOrDefault(v => v.Nom == ville);
            if (servie == null) throw new InvalidOperationException("la carte ne sert pas la ville « " + ville + " »");
            Vector3 ici = carte.PositionSurLaCarte(servie.Position, 0f).Value;
            carte.camera.rect = new Rect(0, 0, 1, 1);
            carte.Vue.Changer(carte.camera.aspect); carte.Vue.Centrer(new Vector2(ici.x, ici.z), demi); carte.Vue.Poser(carte.camera, carte.transform, CarteDessinee.HAUTEUR_CAMERA);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            yield return carte.camera;
        }
    }
}
