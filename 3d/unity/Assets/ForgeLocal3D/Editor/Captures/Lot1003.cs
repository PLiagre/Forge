using System; using System.Collections; using System.Collections.Generic; using System.Linq; using Forge.Interface; using Forge.Pont; using UnityEngine; using UnityEngine.EventSystems; using UnityEngine.UI;
namespace ForgeLocal3D.Captures {
    // Lot 1003 : la carte de 1400 et le vrai cabinet, sans maison choisie, en 1280 × 720. Le panneau « Parcourir le monde » a quitté le bas de la carte ;
    // ses commandes restent dans la bande des modes et la barre, son aide passe à la phrase du Menu, que le pointeur montre entière.
    // Contre-épreuve : `-forge1003Panneau` remet le panneau, et le scénario échoue.
    static class Lot1003 {
        const string PANNEAU = "-forge1003Panneau", NOM = "Parcourir le monde", BANDEAU = "FORGE · Le cabinet", MENU = "Menu"; const int IMAGES_DE_POSE = 10, LARGEUR = 1280, HAUTEUR = 720;
        static readonly string[] MODES = { "Puissances", "Habitants", "Flux" }, DOSSIERS = { "Terres et comptes", "Autres maisons" };
        static InvalidOperationException Echec(string cause) => new InvalidOperationException(cause); static string Ecran(Vector2 p) => "(" + Mathf.RoundToInt(p.x) + ", " + Mathf.RoundToInt(p.y) + ")"; static string Ecran(Rect r) => "[" + Ecran(r.min) + " – " + Ecran(r.max) + "]";
        static string Chemin(Transform t) => t.parent == null ? t.name : Chemin(t.parent) + "/" + t.name; static bool Dans(Rect r, Rect cadre) => r.xMin >= cadre.xMin - .5f && r.yMin >= cadre.yMin - .5f && r.xMax <= cadre.xMax + .5f && r.yMax <= cadre.yMax + .5f;
        static Rect Coins(Camera camera, Transform cadre) { var c = new Vector3[4]; ((RectTransform)cadre).GetWorldCorners(c); var p = c.Select(v => RectTransformUtility.WorldToScreenPoint(camera, v)).ToArray(); return Rect.MinMaxRect(p.Min(v => v.x), p.Min(v => v.y), p.Max(v => v.x), p.Max(v => v.y)); }
        [ScenarioDeCapture(1003, "barre-sans-panneau")] static IEnumerator BarreSansPanneau(Camera camera) {
            var ouverte = new Lot549.CarteOuverte(); for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null; CarteDessinee carte = ouverte.Carte; // étape 1, comme Lot1002
            CabinetDeCarte cabinet = carte.GetComponent<CabinetDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de CabinetDeCarte"); Transform toile = carte.transform.Find("Cabinet"); if (toile == null || !toile.gameObject.activeInHierarchy) throw Echec("étape 1 : la toile du cabinet n'est pas active");
            (carte.GetComponent<SurvolDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de survol")).automatique = true; (carte.GetComponent<ParcoursDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de parcours")).automatique = true;
            for (var e = Lot690.Jusqua(() => Lot690.LecturePrete(cabinet.Partie), () => "étape 1 : " + Lot690.Dire(cabinet.Partie)); e.MoveNext();) yield return null;
            if (Environment.GetCommandLineArgs().Contains(PANNEAU)) SocleInterface.Panneau(toile, NOM, 24, 872, 740, 184); // la contre-épreuve remet l'ancien panneau
            Transform bandeau = toile.Find(BANDEAU) ?? throw Echec("étape 3 : « " + BANDEAU + " » introuvable"), bande = toile.Find(CalquesCarte.BANDE) ?? throw Echec("étape 3 : « " + CalquesCarte.BANDE + " » introuvable");
            Transform conteneur = toile.Find(BANDEAU + "/" + CabinetDeCarte.DOSSIERS) ?? throw Echec("étape 3 : « " + BANDEAU + "/" + CabinetDeCarte.DOSSIERS + " » introuvable"); Button menu = null; string phrase = null;
            void Panneau(string quand) { Transform reste = UnityEngine.Object.FindObjectsByType<Transform>(FindObjectsInactive.Include, FindObjectsSortMode.None).FirstOrDefault(t => t.name == NOM); // étape 2, inactifs compris
                if (reste != null) throw Echec(quand + " : panneau « " + NOM + " » encore là : " + Chemin(reste)); }
            void Places(string quand) { Button[] boutons = toile.GetComponentsInChildren<Button>(true); // étape 3 : chaque commande de l'ancien panneau, un seul bouton, actif, à sa place
                Button Seul(string nom, Transform parent) { Button[] trouves = boutons.Where(b => b.name == nom).ToArray(); if (trouves.Length != 1) throw Echec(quand + " : " + trouves.Length + " bouton(s) « " + nom + " » dans la toile, attendu un seul");
                    if (trouves[0].transform.parent != parent || !trouves[0].gameObject.activeInHierarchy) throw Echec(quand + " : « " + nom + " » sous « " + Chemin(trouves[0].transform.parent) + " »" + (trouves[0].gameObject.activeInHierarchy ? "" : ", caché") + ", attendu actif sous « " + Chemin(parent) + " »"); return trouves[0]; }
                foreach (string nom in MODES) Seul(nom, bande); foreach (string nom in DOSSIERS) Seul(nom, conteneur); menu = Seul(MENU, toile); phrase = menu.GetComponent<Infobulle>()?.Phrase;
                if (phrase == null || !phrase.EndsWith(CabinetDeCarte.AIDE, StringComparison.Ordinal)) throw Echec(quand + " : la phrase du Menu « " + phrase + " » ne finit pas par l'aide « " + CabinetDeCarte.AIDE + " »");
                Transform etat = toile.Find(CabinetDeCarte.ETAT) ?? throw Echec(quand + " : « " + CabinetDeCarte.ETAT + " » introuvable");
                if (carte.CellulesServies < 0 || etat.gameObject.activeSelf) throw Echec(quand + " : « " + CabinetDeCarte.ETAT + " » " + (etat.gameObject.activeSelf ? "actif" : "inactif") + " pour " + carte.CellulesServies + " cellules servies, attendu inactif, carte servie"); }
            Panneau("étape 2"); Places("étape 3");
            Lot549.Photographier(camera, carte); camera.rect = new Rect(0, 0, 1, 1); camera.targetTexture = new RenderTexture(LARGEUR, HAUTEUR, 24); camera.ResetAspect(); // étape 4, comme Lot1002
            Canvas cab = toile.GetComponent<Canvas>(); cab.renderMode = RenderMode.ScreenSpaceCamera; cab.worldCamera = camera; cab.planeDistance = camera.nearClipPlane + 0.2f; yield return null; Canvas.ForceUpdateCanvases();
            EventSystem evenements = EventSystem.current ?? throw Echec("étape 5 : aucun EventSystem courant"); var m = new Vector3[4]; ((RectTransform)menu.transform).GetWorldCorners(m); Vector2 point = RectTransformUtility.WorldToScreenPoint(camera, (m[0] + m[2]) / 2); Rect image = default, bulle = default;
            void Survol(string quand) { image = camera.pixelRect; var touches = new List<RaycastResult>(); evenements.RaycastAll(new PointerEventData(evenements) { position = point }, touches); // étape 5 : rien sur le Menu, une infobulle de sa phrase, entière
                if (touches.Count == 0 || !touches[0].gameObject.transform.IsChildOf(menu.transform)) throw Echec(quand + " : au point " + Ecran(point) + ", le premier sous le pointeur est « " + (touches.Count == 0 ? "rien" : touches[0].gameObject.name) + " », pas « " + MENU + " »");
                RectTransform[] bulles = toile.GetComponentsInChildren<RectTransform>().Where(t => t.name == "Infobulle").ToArray(); if (bulles.Length != 1) throw Echec(quand + " : " + bulles.Length + " infobulle(s) active(s) sous la toile, attendu une seule");
                string dit = bulles[0].GetComponentInChildren<Text>(true)?.text; if (dit != phrase) throw Echec(quand + " : l'infobulle dit « " + dit + " », attendu « " + phrase + " »");
                bulle = Coins(camera, bulles[0]); if (!Dans(bulle, image)) throw Echec(quand + " : infobulle du Menu coupée : " + Ecran(bulle) + " dans " + Ecran(image));
                foreach (Transform cadre in new[] { bande, bandeau }) { Rect r = Coins(camera, cadre); if (!Dans(r, image)) throw Echec(quand + " : « " + cadre.name + " » " + Ecran(r) + " coupé par l'image " + Ecran(image)); } } // la bande et le bandeau entiers
            ExecuteEvents.Execute(menu.gameObject, new PointerEventData(evenements) { position = point }, ExecuteEvents.pointerEnterHandler); Survol("étape 5");
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null; Panneau("étape 6, après la pose"); Places("étape 6, après la pose"); Survol("étape 6, après la pose");
            Debug.Log("CAPTURE_1003 aucun panneau « " + NOM + " » · commandes : " + string.Join(", ", MODES) + " dans la bande ; " + string.Join(", ", DOSSIERS) + " dans la barre · infobulle du Menu " + Ecran(bulle) + " dans " + Ecran(image)
                + " · « " + phrase.Replace("\r", "").Replace("\n", " | ") + " »"); // étape 7
        }
    } }
