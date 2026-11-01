using System; using System.Collections; using System.Collections.Generic; using System.Linq;
using Forge.Interface; using Forge.Pont; using UnityEngine; using UnityEngine.EventSystems; using UnityEngine.UI;

namespace ForgeLocal3D.Captures
{
    // Lot 879 : la carte de 1400 et le vrai cabinet, sur le vrai service. Chaque commande du cabinet a sa phrase ; le pointeur au centre de
    // « Pause / Reprendre » montre la sienne sur un feuillet, à côté du point. `-forge879SansPhrase` ajoute une commande sans phrase : le scénario rougit.
    static class Lot879
    {
        const string BOUTON = "Pause / Reprendre", SANS_PHRASE = "-forge879SansPhrase"; const int IMAGES_DE_POSE = 10, LARGEUR = 1600, HAUTEUR = 900, COMMANDES = 26; const float CARRE = 48;
        static InvalidOperationException Echec(string cause) => new InvalidOperationException(cause);
        static string Ecran(Vector2 p) => "(" + Mathf.RoundToInt(p.x) + ", " + Mathf.RoundToInt(p.y) + ")"; static string Ecran(Rect r) => "[" + Ecran(r.min) + " – " + Ecran(r.max) + "]";

        [ScenarioDeCapture(879, "infobulle-du-temps")] static IEnumerator InfobulleDuTemps(Camera camera)
        {
            var ouverte = new Lot549.CarteOuverte(); for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null;
            CarteDessinee carte = ouverte.Carte; CabinetDeCarte cabinet = carte.GetComponent<CabinetDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de CabinetDeCarte");
            Transform toile = carte.transform.Find("Cabinet"); if (toile == null || !toile.gameObject.activeInHierarchy) throw Echec("étape 1 : la toile du cabinet n'est pas active");
            (carte.GetComponent<SurvolDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de survol")).automatique = true; (carte.GetComponent<ParcoursDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de parcours")).automatique = true;
            for (var e = Lot690.Jusqua(() => Lot690.LecturePrete(cabinet.Partie), () => "étape 1 : " + Lot690.Dire(cabinet.Partie)); e.MoveNext();) yield return null;
            Button[] temps = toile.GetComponentsInChildren<Button>(true).Where(b => b.name == BOUTON).ToArray();
            if (temps.Length != 1) throw Echec("étape 1 : " + temps.Length + " bouton(s) « " + BOUTON + " » dans le cabinet, attendu un seul"); Button bouton = temps[0];
            for (var e = Lot690.Jusqua(() => bouton.interactable, () => "étape 1 : « " + BOUTON + " » reste inactif, l'horloge n'est pas lue"); e.MoveNext();) yield return null;

            if (Environment.GetCommandLineArgs().Contains(SANS_PHRASE)) SocleInterface.Commande(toile, "Commande sans phrase", 24, 980, null);
            string[] sans = CabinetDeCarte.CommandesSansPhrase(toile); if (sans.Length > 0) throw Echec("commandes sans phrase : " + string.Join(", ", sans));
            int commandes = toile.GetComponentsInChildren<Button>(true).Length; if (commandes < COMMANDES) throw Echec("étape 2 : " + commandes + " commandes dans le cabinet, attendu au moins " + COMMANDES);
            string phrase = (bouton.GetComponent<Infobulle>() ?? throw Echec("étape 2 : « " + BOUTON + " » n'a pas d'Infobulle")).Phrase;

            // La toile overlay se dessine sur la caméra reçue, comme au lot 873 ; la caméra rend à la taille de la photo, comme au lot 878 :
            // pixelRect, la toile et l'image parlent des mêmes pixels, et le feuillet tombe où le point le demande.
            Lot549.Photographier(camera, carte); camera.rect = new Rect(0, 0, 1, 1); camera.targetTexture = new RenderTexture(LARGEUR, HAUTEUR, 24); camera.ResetAspect();
            Canvas cabinetToile = toile.GetComponent<Canvas>(); cabinetToile.renderMode = RenderMode.ScreenSpaceCamera; cabinetToile.worldCamera = camera; cabinetToile.planeDistance = camera.nearClipPlane + 0.2f;
            yield return null; Canvas.ForceUpdateCanvases();

            var b = new Vector3[4]; ((RectTransform)bouton.transform).GetWorldCorners(b); Vector2 point = RectTransformUtility.WorldToScreenPoint(camera, (b[0] + b[2]) / 2);
            EventSystem evenements = EventSystem.current ?? throw Echec("étape 4 : aucun EventSystem courant");
            Rect Survol(string ou) // rien ne couvre le bouton au point ; un seul feuillet, de la phrase du bouton, entier dans l'image et hors du carré du point
            {
                var touches = new List<RaycastResult>(); evenements.RaycastAll(new PointerEventData(evenements) { position = point }, touches);
                if (touches.Count == 0 || !touches[0].gameObject.transform.IsChildOf(bouton.transform)) throw Echec(ou + " : au point " + Ecran(point) + ", le premier sous le pointeur est « " + (touches.Count == 0 ? "rien" : touches[0].gameObject.name) + " », pas « " + BOUTON + " »");
                RectTransform[] feuillets = toile.GetComponentsInChildren<RectTransform>().Where(t => t.name == "Infobulle").ToArray();
                if (feuillets.Length != 1) throw Echec(ou + " : " + feuillets.Length + " feuillet(s) actif(s) sous la toile, attendu un seul");
                string dit = feuillets[0].GetComponentInChildren<Text>(true)?.text; if (dit != phrase) throw Echec(ou + " : le feuillet dit « " + dit + " », attendu « " + phrase + " »");
                var c = new Vector3[4]; feuillets[0].GetWorldCorners(c); Vector2[] e = c.Select(v => RectTransformUtility.WorldToScreenPoint(camera, v)).ToArray();
                Rect r = Rect.MinMaxRect(e.Min(p => p.x), e.Min(p => p.y), e.Max(p => p.x), e.Max(p => p.y)), ecran = camera.pixelRect;
                if (r.xMin < ecran.xMin - .5f || r.yMin < ecran.yMin - .5f || r.xMax > ecran.xMax + .5f || r.yMax > ecran.yMax + .5f) throw Echec(ou + " : feuillet " + Ecran(r) + " coupé par l'image " + Ecran(ecran));
                if (Rect.MinMaxRect(r.xMin + .5f, r.yMin + .5f, r.xMax - .5f, r.yMax - .5f).Overlaps(new Rect(point - Vector2.one * CARRE / 2, Vector2.one * CARRE))) throw Echec(ou + " : feuillet " + Ecran(r) + " sur le point " + Ecran(point));
                return r;
            }
            ExecuteEvents.Execute(bouton.gameObject, new PointerEventData(evenements) { position = point }, ExecuteEvents.pointerEnterHandler);
            Survol("étape 4");
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            Rect pose = Survol("étape 5, après la pose");
            Debug.Log("CAPTURE_879 " + commandes + " commandes, toutes avec leur phrase ; point " + Ecran(point) + " au centre de « " + BOUTON + " » ; feuillet " + Ecran(pose)
                + " à " + (pose.xMin >= point.x ? "droite" : "gauche") + " du point, « " + phrase + " »");
        }
    }
}
