using System; using System.Collections; using System.Collections.Generic; using System.IO; using System.Linq; using System.Text;
using Forge.Interface; using UnityEngine; using UnityEngine.EventSystems; using UnityEngine.UI;

namespace ForgeLocal3D.Captures
{
    // Lot 849 : la galerie du registre, sans partie chargée. Les seize jetons, les trois matières, le feuillet, les neuf états côte à côte, et au coin bas droit
    // « Coin de l'écran » dont l'infobulle au filet de cuivre reste entière. Deux définitions, 1920 × 1080 puis 1280 × 720, sur la même galerie.
    // `-forge849OrSurPapier` ajoute aux paires de contraste l'or vieilli sur papier ; `-forge849Teinte` rend reçu identique à repos sauf par ses jetons : le scénario échoue.
    static class Lot849
    {
        const string OR_SUR_PAPIER = "-forge849OrSurPapier", TEINTE = "-forge849Teinte", COIN = "Coin de l'écran";
        const int IMAGES_DE_POSE = 10;
        [Serializable] sealed class PaireDite { public string devant, derriere, usage; public double contraste; }
        [Serializable] sealed class EtatDit { public string nom, matiere, texte, trait, forme, signe, mot; public int epaisseur; }
        [Serializable] sealed class Rapport { public PaireDite[] paires; public EtatDit[] etats; public float[] cadre_de_la_commande, cadre_du_feuillet, cadre_de_l_infobulle; }

        static GameObject racine; static Canvas toile; static EventSystem evenements; static Button coin; static string phrase; static List<(string, string, SocleInterface.Usage)> paires; static List<Declaration> table;
        static InvalidOperationException Echec(string cause) => new InvalidOperationException(cause);
        static bool Drapeau(string nom) => Environment.GetCommandLineArgs().Contains(nom);
        static string Ecran(Vector2 p) => "(" + Mathf.RoundToInt(p.x) + ", " + Mathf.RoundToInt(p.y) + ")"; static string Ecran(Rect r) => "[" + Ecran(r.min) + " – " + Ecran(r.max) + "]";

        static Rect Cadre(Camera camera, RectTransform rect)
        {
            var c = new Vector3[4]; rect.GetWorldCorners(c); Vector2[] e = c.Select(v => (Vector2)RectTransformUtility.WorldToScreenPoint(camera, v)).ToArray();
            return Rect.MinMaxRect(e.Min(p => p.x), e.Min(p => p.y), e.Max(p => p.x), e.Max(p => p.y));
        }
        static bool Coupe(Rect r, Rect image) => r.xMin < image.xMin - .5f || r.yMin < image.yMin - .5f || r.xMax > image.xMax + .5f || r.yMax > image.yMax + .5f;
        static Color Teinte(string nom) => nom == "attenue" ? SocleInterface.Attenue : SocleInterface.Couleur(nom);

        static void Tendre(Camera camera, int largeur, int hauteur)
        {
            RenderTexture ancienne = camera.targetTexture; camera.rect = new Rect(0, 0, 1, 1); camera.targetTexture = new RenderTexture(largeur, hauteur, 24); camera.ResetAspect(); if (ancienne != null) ancienne.Release();
            toile.renderMode = RenderMode.ScreenSpaceCamera; toile.worldCamera = camera; toile.planeDistance = camera.nearClipPlane + 0.2f;
        }
        static void ExigerLaDefinition(Camera camera, int largeur, int hauteur, string ou)
        {
            Rect image = camera.pixelRect; if (Mathf.RoundToInt(image.width) != largeur || Mathf.RoundToInt(image.height) != hauteur) throw Echec(ou + " : l'image fait " + Ecran(image) + ", attendu " + largeur + " × " + hauteur);
        }

        // Étape 4 : chaque texte actif est entier dans l'image et tient dans son cadre.
        static void LesTextes(Camera camera, string ou)
        {
            Rect image = camera.pixelRect; int vus = 0;
            foreach (var t in toile.GetComponentsInChildren<Text>())
            {
                Rect r = Cadre(camera, t.rectTransform); vus++;
                if (Coupe(r, image)) throw Echec(ou + " : le texte « " + t.text + " » " + Ecran(r) + " est coupé par l'image " + Ecran(image));
                if (t.preferredHeight > t.rectTransform.rect.height + .5f) throw Echec(ou + " : le texte « " + t.text + " » demande " + t.preferredHeight + " px, son cadre en a " + t.rectTransform.rect.height);
                if (t.horizontalOverflow == HorizontalWrapMode.Overflow && t.preferredWidth > t.rectTransform.rect.width + .5f) throw Echec(ou + " : le texte « " + t.text + " » demande " + t.preferredWidth + " px de large, son cadre en a " + t.rectTransform.rect.width);
            }
            if (vus == 0) throw Echec(ou + " : aucun texte actif dans la galerie");
        }

        // Étape 5 : le pointeur au centre de « Coin de l'écran » ; un seul feuillet, qui dit sa phrase, entier dans l'image, hors de la commande.
        static Rect Survol(Camera camera, string ou, bool entrer)
        {
            Rect commande = Cadre(camera, (RectTransform)coin.transform);
            if (entrer) ExecuteEvents.Execute(coin.gameObject, new PointerEventData(evenements) { position = commande.center }, ExecuteEvents.pointerEnterHandler);
            RectTransform[] feuillets = toile.GetComponentsInChildren<RectTransform>().Where(t => t.name == "Infobulle").ToArray();
            if (feuillets.Length != 1) throw Echec(ou + " : " + feuillets.Length + " feuillet(s) « Infobulle » actif(s), attendu un seul");
            string dit = feuillets[0].GetComponentInChildren<Text>(true)?.text; if (dit != phrase) throw Echec(ou + " : le feuillet dit « " + dit + " », attendu « " + phrase + " »");
            Rect r = Cadre(camera, feuillets[0]);
            if (Coupe(r, camera.pixelRect)) throw Echec(ou + " : feuillet " + Ecran(r) + " coupé par l'image " + Ecran(camera.pixelRect));
            if (Rect.MinMaxRect(r.xMin + .5f, r.yMin + .5f, r.xMax - .5f, r.yMax - .5f).Overlaps(commande)) throw Echec(ou + " : feuillet " + Ecran(r) + " sur la commande " + Ecran(commande));
            return r;
        }

        static float[] Bords(Rect r) => new[] { r.xMin, r.yMin, r.xMax, r.yMax };
        // Étape 6 : la photo aux définitions exactes, puis son rapport.
        static void Photographier(Camera camera, int largeur, int hauteur, string nom, Rect infobulle)
        {
            CitadelPlayCheck.Capture(camera, Path.Combine(Capture.DossierDesCaptures, nom + ".png"), largeur, hauteur);
            var feuillet = racine.GetComponentsInChildren<RectTransform>(true).Single(t => t.name == "Feuillet du registre");
            var rapport = new Rapport
            {
                paires = paires.Select(p => new PaireDite { devant = p.Item1, derriere = p.Item2, usage = p.Item3.ToString(), contraste = SocleInterface.Contraste(Teinte(p.Item1), Teinte(p.Item2)) }).ToArray(),
                etats = table.Select(d => new EtatDit { nom = d.Nom, matiere = d.Matiere, texte = d.Texte, trait = d.Trait, forme = d.Forme.ToString(), epaisseur = d.Epaisseur, signe = d.Signe, mot = d.Mot }).ToArray(),
                cadre_de_la_commande = Bords(Cadre(camera, (RectTransform)coin.transform)), cadre_du_feuillet = Bords(Cadre(camera, feuillet)), cadre_de_l_infobulle = Bords(infobulle)
            };
            File.WriteAllText(Path.Combine(Capture.DossierDesCaptures, nom + ".json"), JsonUtility.ToJson(rapport, true), new UTF8Encoding(false));
            Debug.Log("CAPTURE_849 " + largeur + " × " + hauteur + " : " + paires.Count + " paires, " + table.Count + " états, commande " + Ecran(Cadre(camera, (RectTransform)coin.transform)) + ", infobulle " + Ecran(infobulle) + " « " + phrase + " »");
        }

        [ScenarioDeCapture(849, "1-galerie-1920x1080")] static IEnumerator Galerie1920(Camera camera)
        {
            racine = GalerieDuRegistre.Creer();
            toile = racine.GetComponentsInChildren<Canvas>(true).SingleOrDefault(c => c.name == "Registre") ?? throw Echec("étape 1 : la galerie n'a pas de toile « Registre »");
            evenements = racine.GetComponentInChildren<EventSystem>() ?? throw Echec("étape 1 : la galerie n'a pas d'EventSystem");
            Button[] coins = racine.GetComponentsInChildren<Button>(true).Where(b => b.name == COIN).ToArray();
            if (coins.Length != 1) throw Echec("étape 1 : " + coins.Length + " commande(s) « " + COIN + " » dans la galerie, attendu une seule");
            coin = coins[0]; phrase = (coin.GetComponent<Infobulle>() ?? throw Echec("étape 1 : « " + COIN + " » n'a pas d'Infobulle")).Phrase;
            Tendre(camera, 1920, 1080); yield return null; Canvas.ForceUpdateCanvases(); ExigerLaDefinition(camera, 1920, 1080, "étape 1");

            paires = SocleInterface.Paires.Select(p => (p.devant, p.derriere, p.usage)).ToList();
            if (Drapeau(OR_SUR_PAPIER)) paires.Add(("or-vieilli", "papier", SocleInterface.Usage.Texte));
            string refus = SocleInterface.Refuse(paires); if (refus != null) throw Echec("étape 2 : " + refus);
            table = EtatsDuCabinet.Table.ToList(); var repos = EtatsDuCabinet.De(EtatDuCabinet.Repos);
            if (Drapeau(TEINTE)) table = table.Select(d => d.Nom == "reçu" ? new Declaration(d.Nom, d.Matiere, d.Texte, d.Trait, repos.Forme, repos.Epaisseur, repos.Signe, repos.Mot) : d).ToList();
            string confondus = EtatsDuCabinet.Confondus(table); if (confondus != null) throw Echec("étape 3 : " + confondus);

            LesTextes(camera, "étape 4"); Survol(camera, "étape 5", true);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            LesTextes(camera, "étape 6"); Rect pose = Survol(camera, "étape 6", false);
            Photographier(camera, 1920, 1080, "lot849-galerie-1920x1080", pose);
        }

        [ScenarioDeCapture(849, "2-galerie-1280x720")] static IEnumerator Galerie1280(Camera camera)
        {
            if (racine == null || toile == null || coin == null || table == null) throw Echec("étape 7 : la galerie du scénario 1 manque");
            ExecuteEvents.Execute(coin.gameObject, new PointerEventData(evenements), ExecuteEvents.pointerExitHandler);
            Tendre(camera, 1280, 720); yield return null; Canvas.ForceUpdateCanvases(); ExigerLaDefinition(camera, 1280, 720, "étape 7");
            LesTextes(camera, "étape 7 (textes)"); Survol(camera, "étape 7 (infobulle)", true);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            LesTextes(camera, "étape 7 (textes, après la pose)"); Rect pose = Survol(camera, "étape 7 (infobulle, après la pose)", false);
            Photographier(camera, 1280, 720, "lot849-galerie-1280x720", pose);
        }
    }
}
