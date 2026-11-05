using System; using System.Collections; using System.Collections.Generic; using System.Linq; using Forge.Interface; using Forge.Pont; using UnityEngine; using UnityEngine.EventSystems; using UnityEngine.UI;
namespace ForgeLocal3D.Captures {
    // Lot 1002 : la carte de 1400 et le vrai cabinet, sans maison choisie. « Terres et comptes » et « Autres maisons » sont deux icônes de la barre, entre la date et
    // les commandes du temps ; « Les autres maisons », ouvert par son icône, commence sous la barre ; le pointeur sur « Terres et comptes » montre sa phrase.
    // Contre-épreuve : `-forge1002Recouvrir` remonte le feuillet sur la barre, et le scénario échoue.
    static class Lot1002 {
        const string RECOUVRIR = "-forge1002Recouvrir", BANDEAU = "FORGE · Le cabinet", COMPTES = "Terres et comptes", VOISINS = "Autres maisons", FEUILLET = "Les autres maisons"; const int IMAGES_DE_POSE = 10, LARGEUR = 1600, HAUTEUR = 900;
        static InvalidOperationException Echec(string cause) => new InvalidOperationException(cause); static string Ecran(Vector2 p) => "(" + Mathf.RoundToInt(p.x) + ", " + Mathf.RoundToInt(p.y) + ")"; static string Ecran(Rect r) => "[" + Ecran(r.min) + " – " + Ecran(r.max) + "]";
        static Rect Coins(Camera camera, Transform cadre) { var c = new Vector3[4]; ((RectTransform)cadre).GetWorldCorners(c); var p = c.Select(v => RectTransformUtility.WorldToScreenPoint(camera, v)).ToArray(); return Rect.MinMaxRect(p.Min(v => v.x), p.Min(v => v.y), p.Max(v => v.x), p.Max(v => v.y)); }
        static bool Dans(Rect r, Rect cadre) => r.xMin >= cadre.xMin - .5f && r.yMin >= cadre.yMin - .5f && r.xMax <= cadre.xMax + .5f && r.yMax <= cadre.yMax + .5f;
        [ScenarioDeCapture(1002, "icones-de-la-barre")] static IEnumerator IconesDeLaBarre(Camera camera) {
            var ouverte = new Lot549.CarteOuverte(); for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null; CarteDessinee carte = ouverte.Carte; // étape 1, comme Lot879
            CabinetDeCarte cabinet = carte.GetComponent<CabinetDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de CabinetDeCarte"); Transform toile = carte.transform.Find("Cabinet"); if (toile == null || !toile.gameObject.activeInHierarchy) throw Echec("étape 1 : la toile du cabinet n'est pas active");
            (carte.GetComponent<SurvolDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de survol")).automatique = true; (carte.GetComponent<ParcoursDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de parcours")).automatique = true;
            for (var e = Lot690.Jusqua(() => Lot690.LecturePrete(cabinet.Partie), () => "étape 1 : " + Lot690.Dire(cabinet.Partie)); e.MoveNext();) yield return null;
            Transform bandeau = toile.Find(BANDEAU), conteneur = toile.Find(BANDEAU + "/" + CabinetDeCarte.DOSSIERS); if (conteneur == null || !conteneur.gameObject.activeInHierarchy) throw Echec("étape 2 : dossiers de la barre introuvables");
            Button[] icones = conteneur.GetComponentsInChildren<Button>(true).OrderBy(b => ((RectTransform)b.transform).anchoredPosition.x).ToArray(); // étape 2 : les deux icônes, et elles seules
            if (icones.Length != 2 || icones[0].name != COMPTES || icones[1].name != VOISINS) throw Echec("étape 2 : icônes " + string.Join(", ", icones.Select(b => "« " + b.name + " »")) + ", attendu « " + COMPTES + " » puis « " + VOISINS + " »");
            foreach (Button icone in icones) {
                if (!icone.gameObject.activeInHierarchy || string.IsNullOrWhiteSpace(icone.GetComponent<Infobulle>()?.Phrase)) throw Echec("étape 2 : l'icône « " + icone.name + " » est cachée ou sans phrase");
                int n = toile.GetComponentsInChildren<Button>(true).Count(b => b.name == icone.name); if (n != 1) throw Echec("étape 2 : " + n + " bouton(s) « " + icone.name + " » dans la toile, attendu un seul"); }
            int directs = bandeau.Cast<Transform>().Count(t => t.GetComponent<Button>() != null); if (directs != 3) throw Echec("étape 2 : " + directs + " bouton(s) enfants directs du bandeau, attendu les trois commandes du temps");
            Button comptes = icones[0]; string phrase = comptes.GetComponent<Infobulle>().Phrase; icones[1].onClick.Invoke(); // étape 3 : « Les autres maisons » ouvert par son icône
            var feuillet = toile.Cast<Transform>().OfType<RectTransform>().SingleOrDefault(t => t.name == FEUILLET && t.GetComponentInChildren<ScrollRect>(true) != null);
            if (feuillet == null || !feuillet.gameObject.activeInHierarchy) throw Echec("étape 3 : feuillet « " + FEUILLET + " » fermé"); if (Environment.GetCommandLineArgs().Contains(RECOUVRIR)) feuillet.anchoredPosition = new Vector2(24, -60);
            Lot549.Photographier(camera, carte); camera.rect = new Rect(0, 0, 1, 1); camera.targetTexture = new RenderTexture(LARGEUR, HAUTEUR, 24); camera.ResetAspect(); // étape 4, comme Lot879
            Canvas cab = toile.GetComponent<Canvas>(); cab.renderMode = RenderMode.ScreenSpaceCamera; cab.worldCamera = camera; cab.planeDistance = camera.nearClipPlane + 0.2f; yield return null; Canvas.ForceUpdateCanvases();
            EventSystem evenements = EventSystem.current ?? throw Echec("étape 6 : aucun EventSystem courant"); var m = new Vector3[4]; ((RectTransform)comptes.transform).GetWorldCorners(m); Vector2 point = RectTransformUtility.WorldToScreenPoint(camera, (m[0] + m[2]) / 2);
            Rect rangee = default, ouvert = default;
            void Juger(string quand) {
                Rect image = camera.pixelRect, barre = Coins(camera, bandeau), reduite = Rect.MinMaxRect(barre.xMin + .5f, barre.yMin + .5f, barre.xMax - .5f, barre.yMax - .5f); // étape 5, en coins d'écran
                foreach (Transform panneau in toile.Cast<Transform>().Where(t => t != bandeau && t.gameObject.activeInHierarchy && t.Find("Filet") != null)) {
                    Rect r = Coins(camera, panneau); if (r.Overlaps(reduite)) throw Echec(quand + " : « " + panneau.name + " » recouvre la barre : " + Ecran(r) + " sur " + Ecran(barre)); }
                foreach (Button icone in icones) { Rect r = Coins(camera, icone.transform); if (!Dans(r, barre) || !Dans(r, image)) throw Echec(quand + " : l'icône « " + icone.name + " » " + Ecran(r) + " sort de la barre " + Ecran(barre) + " ou de l'image " + Ecran(image)); }
                Rect a = Coins(camera, icones[0].transform), b = Coins(camera, icones[1].transform); rangee = Rect.MinMaxRect(a.xMin, Mathf.Min(a.yMin, b.yMin), b.xMax, Mathf.Max(a.yMax, b.yMax)); ouvert = Coins(camera, feuillet);
                var touches = new List<RaycastResult>(); evenements.RaycastAll(new PointerEventData(evenements) { position = point }, touches); // étape 6 : rien sur l'icône, une infobulle de sa phrase
                if (touches.Count == 0 || !touches[0].gameObject.transform.IsChildOf(comptes.transform)) throw Echec(quand + " : au point " + Ecran(point) + ", le premier sous le pointeur est « " + (touches.Count == 0 ? "rien" : touches[0].gameObject.name) + " », pas « " + COMPTES + " »");
                RectTransform[] bulles = toile.GetComponentsInChildren<RectTransform>().Where(t => t.name == "Infobulle").ToArray(); if (bulles.Length != 1) throw Echec(quand + " : " + bulles.Length + " infobulle(s) active(s) sous la toile, attendu une seule");
                string dit = bulles[0].GetComponentInChildren<Text>(true)?.text; if (dit != phrase) throw Echec(quand + " : l'infobulle dit « " + dit + " », attendu « " + phrase + " »");
                Rect bulle = Coins(camera, bulles[0]); if (!Dans(bulle, image)) throw Echec(quand + " : infobulle " + Ecran(bulle) + " coupée par l'image " + Ecran(image)); }
            ExecuteEvents.Execute(comptes.gameObject, new PointerEventData(evenements) { position = point }, ExecuteEvents.pointerEnterHandler); Juger("étapes 5 et 6");
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null; Juger("étape 7, après la pose");
            Debug.Log("CAPTURE_1002 icônes « " + COMPTES + " », « " + VOISINS + " » dans la barre " + Ecran(rangee) + " · feuillet « " + FEUILLET + " » " + Ecran(ouvert) + " · infobulle « " + phrase + " »"); // étape 8
        }
    } }
