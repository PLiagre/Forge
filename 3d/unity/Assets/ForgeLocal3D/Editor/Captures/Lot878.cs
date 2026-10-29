using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using Forge.Interface;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace ForgeLocal3D.Captures
{
    // Lot 878 : la galerie du socle sur la caméra reçue, le pointeur au bout droit de « Parcourir au clavier » et son infobulle.
    // Avant, la plus longue phrase est montrée aux quatre coins de l'écran. `-forge878PhraseVide` ajoute une commande à phrase vide : le refus remonte.
    static class Lot878
    {
        const string BOUTON = "Parcourir au clavier", VIDE = "-forge878PhraseVide"; const int IMAGES_DE_POSE = 10, LARGEUR = 1600, HAUTEUR = 900; const float CARRE = 48, RECUL_PX = 8; // LARGEUR × HAUTEUR : la photo
        static InvalidOperationException Echec(string cause) => new InvalidOperationException(cause);
        static string Ecran(Vector2 p) => "(" + Mathf.RoundToInt(p.x) + ", " + Mathf.RoundToInt(p.y) + ")"; static string Ecran(Rect r) => "[" + Ecran(r.min) + " – " + Ecran(r.max) + "]";

        [ScenarioDeCapture(878, "infobulle-de-la-galerie")]
        static IEnumerator InfobulleDeLaGalerie(Camera camera)
        {
            GameObject galerie = SocleInterface.Creer();
            T Trouver<T>(string nom) where T : Component => galerie.GetComponentsInChildren<T>(true).SingleOrDefault(c => c.name == nom) ?? throw Echec("étape 1 : « " + nom + " » (" + typeof(T).Name + ") absent de la galerie");
            if (Environment.GetCommandLineArgs().Contains(VIDE)) SocleInterface.Commande(Trouver<Image>("Le domaine").transform, "Commande sans phrase", 24, 540, null, true, "");
            Canvas toile = Trouver<Canvas>("Documents"); Button bouton = Trouver<Button>(BOUTON);
            EventSystem evenements = galerie.GetComponentInChildren<EventSystem>() ?? throw Echec("étape 1 : la galerie n'a pas d'EventSystem");
            Infobulle infobulle = bouton.GetComponent<Infobulle>() ?? throw Echec("étape 1 : « " + BOUTON + " » ne déclare pas sa phrase");
            string longue = galerie.GetComponentsInChildren<Infobulle>(true).Select(i => i.Phrase).OrderByDescending(p => p.Length).First();

            // La toile overlay se dessine sur la caméra reçue, comme au lot 855. En batch, la vue de jeu fait 640 × 480 : forcer l'aspect de la photo
            // mettrait la toile en page sur 16:9 et laisserait pixelRect en 4:3, et le feuillet tomberait loin du point. La caméra rend donc à la taille
            // de la photo, et pixelRect, la toile et l'image parlent des mêmes pixels.
            camera.rect = new Rect(0, 0, 1, 1); camera.targetTexture = new RenderTexture(LARGEUR, HAUTEUR, 24); camera.ResetAspect();
            toile.renderMode = RenderMode.ScreenSpaceCamera; toile.worldCamera = camera; toile.planeDistance = camera.nearClipPlane + 0.2f;
            yield return null; Canvas.ForceUpdateCanvases();
            var t = new Vector3[4]; ((RectTransform)toile.transform).GetWorldCorners(t); Vector2 t0 = RectTransformUtility.WorldToScreenPoint(camera, t[0]), t2 = RectTransformUtility.WorldToScreenPoint(camera, t[2]);
            if (toile.pixelRect.size != new Vector2(LARGEUR, HAUTEUR) || (t0 - toile.pixelRect.min).magnitude > 1 || (t2 - toile.pixelRect.max).magnitude > 1)
                throw Echec("étape 2 : la toile couvre " + Ecran(Rect.MinMaxRect(t0.x, t0.y, t2.x, t2.y)) + " pour un écran " + Ecran(toile.pixelRect) + ", attendu " + LARGEUR + " × " + HAUTEUR);
            Rect Juger(RectTransform feuillet, Vector2 point, string ou) // le feuillet ramené à l'écran, entier dans la toile et hors du carré du point
            {
                if (feuillet == null || !feuillet.gameObject.activeInHierarchy) throw Echec(ou + " : feuillet absent ou caché");
                var c = new Vector3[4]; feuillet.GetWorldCorners(c); Vector2[] e = c.Select(v => RectTransformUtility.WorldToScreenPoint(camera, v)).ToArray();
                Rect r = Rect.MinMaxRect(e.Min(p => p.x), e.Min(p => p.y), e.Max(p => p.x), e.Max(p => p.y)), ecran = toile.pixelRect;
                if (r.xMin < ecran.xMin - .5f || r.yMin < ecran.yMin - .5f || r.xMax > ecran.xMax + .5f || r.yMax > ecran.yMax + .5f) throw Echec(ou + " : feuillet " + Ecran(r) + " coupé par l'écran " + Ecran(ecran));
                if (Rect.MinMaxRect(r.xMin + .5f, r.yMin + .5f, r.xMax - .5f, r.yMax - .5f).Overlaps(new Rect(point - Vector2.one * CARRE / 2, Vector2.one * CARRE))) throw Echec(ou + " : feuillet " + Ecran(r) + " sur le point " + Ecran(point));
                return r;
            }

            Rect plein = toile.pixelRect; var coins = new List<string>();
            foreach (var (nom, p) in new[] { ("bas gauche", new Vector2(plein.xMin + 1, plein.yMin + 1)), ("bas droit", new Vector2(plein.xMax - 1, plein.yMin + 1)),
                ("haut gauche", new Vector2(plein.xMin + 1, plein.yMax - 1)), ("haut droit", new Vector2(plein.xMax - 1, plein.yMax - 1)) })
                coins.Add(nom + " " + Ecran(p) + " → " + Ecran(Juger(Infobulle.Montrer(toile, longue, p), p, "étape 3, coin " + nom)));
            Infobulle.Cacher(toile);

            var b = new Vector3[4]; ((RectTransform)bouton.transform).GetWorldCorners(b);
            Vector2 point = RectTransformUtility.WorldToScreenPoint(camera, (b[2] + b[3]) / 2) - new Vector2(RECUL_PX, 0); // milieu du bord droit
            ExecuteEvents.Execute(bouton.gameObject, new PointerEventData(evenements) { position = point }, ExecuteEvents.pointerEnterHandler);
            Rect Survol(string ou)
            {
                RectTransform feuillet = toile.transform.Find("Infobulle") as RectTransform;
                string dit = feuillet != null ? feuillet.GetComponentInChildren<Text>(true)?.text : null;
                if (dit != infobulle.Phrase) throw Echec(ou + " : le feuillet dit « " + dit + " », attendu « " + infobulle.Phrase + " »");
                return Juger(feuillet, point, ou);
            }
            Survol("étape 4");
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            Rect pose = Survol("étape 5, après la pose");
            Debug.Log("CAPTURE_878 écran " + Ecran(plein) + " ; coins : " + string.Join(" ; ", coins) + " ; point " + Ecran(point) + ", feuillet " + Ecran(pose)
                + " à " + (pose.xMin >= point.x ? "droite" : "gauche") + " du point, « " + infobulle.Phrase + " »");
        }
    }
}
