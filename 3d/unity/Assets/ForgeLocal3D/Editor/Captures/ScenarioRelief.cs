using System;
using System.Collections;
using System.Linq;
using Forge.Interface;
using Forge.Pont;
using UnityEngine;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures
{
    // Le terrain de la carte, photographié branché au service : toute la carte, puis quatre vues de plus en plus
    // proches, sur des montagnes, des côtes découpées, des frontières serrées et un rivage, où se jugent les traits
    // que le terrain dessine ; puis deux vues où se jugent les noms des pays, à mi-distance et d'assez près pour que
    // les plus grands s'effacent ; enfin deux vues au plus près, où la caméra est la plus inclinée, sur des montagnes
    // et sur un rivage. Les vues se cadrent sur une ville servie, jamais sur un point écrit en dur ; une
    // ville que la carte ne sert pas fait échouer le scénario, et la première vue attend que les pays soient nommés.
    static class ScenarioRelief
    {
        const float DEMI_ALPES_KM = 420f, DEMI_EGEE_KM = 380f, DEMI_FRONTIERES_KM = 110f, DEMI_RIVAGE_KM = 60f, DEMI_NOMS_KM = 700f, DEMI_NOMS_DE_PRES_KM = 280f, DEMI_INCLINEE_KM = 75f; const int IMAGES_DE_POSE = 12;

        [ScenarioDeCapture("relief", "01-toute-la-carte")]
        static IEnumerator TouteLaCarte(Camera camera)
        {
            SceneManager.LoadScene(OuvertureDeLaCarte.SCENE);
            CarteDessinee carte = null; CarteDeLaGuerre guerre = null;
            for (var e = AttentesDeCapture.Jusqua(() => (carte = Object.FindFirstObjectByType<CarteDessinee>()) != null && carte.Vue != null && carte.camera != null && carte.CellulesPosees > 0
                && (guerre = Object.FindFirstObjectByType<CarteDeLaGuerre>()) != null && guerre.NomsDesPays.Count > 0,
                () => "carte non posée ou pays non nommés (" + (carte == null ? "pas de carte" : carte.TexteAffiche) + (guerre == null ? ", pas de vue de la guerre" : ", " + (guerre.AbsenceDesTerres ?? "terres lues")) + ")"); e.MoveNext();) yield return null;
            carte.camera.rect = new Rect(0, 0, 1, 1);
            carte.Vue.Changer(carte.camera.aspect); carte.Vue.Centrer(carte.Vue.Centre, carte.Vue.DemiMax); carte.Vue.Poser(carte.camera, carte.transform);
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

        [ScenarioDeCapture("relief", "06-noms-a-mi-distance")]
        static IEnumerator NomsAMiDistance(Camera camera) => Sur("Prague", DEMI_NOMS_KM);

        [ScenarioDeCapture("relief", "07-noms-de-pres")]
        static IEnumerator NomsDePres(Camera camera) => Sur("Paris", DEMI_NOMS_DE_PRES_KM);

        [ScenarioDeCapture("relief", "08-montagnes-inclinees")]
        static IEnumerator MontagnesInclinees(Camera camera) => Sur("Milan", DEMI_INCLINEE_KM);

        [ScenarioDeCapture("relief", "09-rivage-incline")]
        static IEnumerator RivageIncline(Camera camera) => Sur("Athènes", DEMI_INCLINEE_KM);

        static IEnumerator Sur(string ville, float demi)
        {
            var carte = Object.FindFirstObjectByType<CarteDessinee>();
            if (carte == null || carte.Vue == null || carte.Lue == null) throw new InvalidOperationException("la carte n'est pas ouverte : « 01-toute-la-carte » n'a pas réussi");
            VilleDeCarte servie = carte.Lue.Cellules.SelectMany(c => c.Villes).FirstOrDefault(v => v.Nom == ville);
            if (servie == null) throw new InvalidOperationException("la carte ne sert pas la ville « " + ville + " »");
            Vector3 ici = carte.PositionSurLaCarte(servie.Position, 0f).Value;
            carte.camera.rect = new Rect(0, 0, 1, 1);
            carte.Vue.Changer(carte.camera.aspect); carte.Vue.Centrer(new Vector2(ici.x, ici.z), demi); carte.Vue.Poser(carte.camera, carte.transform);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            yield return carte.camera;
        }
    }
}
