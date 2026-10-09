using System;
using System.Collections;
using System.Globalization;
using System.Linq;
using Forge.Pont;
using UnityEngine;

namespace ForgeLocal3D.Captures
{
    // Lot 524 : le joueur parcourt sa carte. La carte s'ouvre comme au lot 549 ; le parcours y passe en automatique, et le
    // scénario fait ce que la souris ferait : douze crans de molette sous Metz, puis un glissé de 320 × 120 pixels vers la
    // gauche et le bas, sur une fenêtre de la taille de la photo. La vue doit s'être approchée, être restée dans la carte et
    // avoir suivi le glissé ; la caméra de la carte la montre. La photo : la Lorraine et ses voisines de près.
    static class Lot524
    {
        const string VILLE = "Metz";
        const float CRANS = 12f;
        static readonly Vector2 GLISSE_PX = new Vector2(-320, -120);
        const float HAUTEUR_PX = 900f;
        const float TOLERANCE_KM = 1e-3f;
        const int IMAGES_DE_POSE = 10;

        static string N(float v) => v.ToString("0.###", CultureInfo.InvariantCulture);

        [ScenarioDeCapture(524, "carte-de-pres")]
        static IEnumerator CarteDePres(Camera camera)
        {
            var ouverte = new Lot549.CarteOuverte();
            for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null;
            var carte = ouverte.Carte;
            var parcours = carte.GetComponent<ParcoursDeCarte>() ?? throw new InvalidOperationException("la carte n'a pas de ParcoursDeCarte");
            parcours.automatique = true;
            var vue = carte.Vue ?? throw new InvalidOperationException("la carte n'a pas de vue : sa caméra n'est pas la sienne, ou rien n'est posé");
            if (vue.Echelle != 1f) throw new InvalidOperationException("la carte ne s'ouvre pas sur toute la carte : échelle " + N(vue.Echelle));
            float demiEnsemble = vue.Demi;

            // La molette sous Metz : Metz reste sous la souris.
            var metz = carte.GetComponentsInChildren<TextMesh>().FirstOrDefault(t => t.text == VILLE)
                ?? throw new InvalidOperationException("pas de nom « " + VILLE + " » sur la carte");
            Vector2 ancre = carte.camera.WorldToViewportPoint(metz.transform.position);
            Vector2 sousLaSouris = vue.PointSous(ancre);
            vue.Zoomer(CRANS, ancre);
            if (vue.Demi >= demiEnsemble / 4) throw new InvalidOperationException("douze crans n'ont pas approché la vue : demi-hauteur " + N(vue.Demi) + " km pour " + N(demiEnsemble));
            if ((vue.PointSous(ancre) - sousLaSouris).magnitude > TOLERANCE_KM)
                throw new InvalidOperationException(VILLE + " n'est plus sous la souris : " + vue.PointSous(ancre) + " pour " + sousLaSouris);

            // Le glissé : la carte suit la souris, la vue va à l'opposé.
            Vector2 avant = vue.Centre;
            vue.Glisser(GLISSE_PX, HAUTEUR_PX);
            Vector2 attendu = avant - GLISSE_PX * (2 * vue.Demi / HAUTEUR_PX);
            if ((vue.Centre - attendu).magnitude > TOLERANCE_KM)
                throw new InvalidOperationException("la vue n'a pas suivi le glissé : centre " + vue.Centre + " pour " + attendu);
            yield return null; // la carte pose sa caméra sur la vue
            if (Mathf.Abs(carte.camera.orthographicSize - vue.Demi) > TOLERANCE_KM)
                throw new InvalidOperationException("la caméra de la carte montre " + N(carte.camera.orthographicSize) + " km de demi-hauteur, la vue " + N(vue.Demi));

            camera.CopyFrom(carte.camera); camera.aspect = Lot549.FORME; carte.camera.enabled = false;
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            Debug.Log("CAPTURE_524 échelle " + N(vue.Echelle) + " · demi-hauteur " + N(vue.Demi) + " km sur " + N(demiEnsemble) + " · centre " + vue.Centre);
        }
    }
}
