using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using Forge.Interface;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures
{
    // La planche de l'étape : la carte politique du jeu à côté de l'atlas de Shepherd (« Europe about 1360 »), cadre par cadre,
    // en 1920 × 1080 :
    //   7-atlas-europe, 8-atlas-france, 9-atlas-empire, 10-atlas-italie, 11-atlas-balkans.
    // À gauche, la carte servie, cadrée comme `ScenarioCartePolitique` le fait (même calcul, sur les terres servies des pays du
    // cadre), rendue dans une texture sans la toile du cabinet ; à droite, la zone de l'atlas que `cadres.json` fait répondre au
    // cadre, à la même hauteur ; sous chacune sa source, et en pied l'écart de date et ce que devient Europa Universalis IV.
    // Europa n'entre jamais dans une image jointe : une capture locale (`<checkout>/references/eu4/<cadre>.png`, hors du dépôt)
    // donne une planche complète écrite à côté d'elle, et la planche publiée dit seulement si elle a été lue.
    // Chaque planche prend la carte dans l'état où elle la trouve et la rend tel quel : l'ordre des noms (« 10- » avant « 2- »)
    // ne change rien aux autres photos du groupe. Elle échoue sans l'atlas, sur une zone hors de l'image, ou si aucun grand pays
    // du cadre ne se lit sur la carte du jeu.
    static class ScenarioCarteEtAtlas
    {
        const string GROUPE = "modes-de-carte", PLANCHE = "Planche de l'atlas";
        const int LARGEUR = 1920, HAUTEUR = 1080, IMAGES_DE_POSE = 12, TERRES_D_UN_GRAND_PAYS = 5, CALQUE_DE_LA_PLANCHE = 5; // le calque « UI »
        // La planche en pixels de la photo : le titre, deux panneaux côte à côte, la source sous chacun, la note en pied.
        const float MARGE = 30, HAUT_DES_PANNEAUX = 92, LARGEUR_PANNEAU = 915, HAUTEUR_PANNEAU = 840;

        [Serializable] sealed class Zone { public string cadre = null, titre = null; public int x = 0, y = 0, largeur = 0, hauteur = 0; }
        [Serializable] sealed class Cadres { public string atlas = null, source = null, ecart = null; public int largeur = 0, hauteur = 0; public Zone[] zones = null; }

        [ScenarioDeCapture(GROUPE, "7-atlas-europe", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator Europe(Camera camera) => Planche("europe");
        [ScenarioDeCapture(GROUPE, "8-atlas-france", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator France(Camera camera) => Planche("france-et-iles");
        [ScenarioDeCapture(GROUPE, "9-atlas-empire", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator Empire(Camera camera) => Planche("empire");
        [ScenarioDeCapture(GROUPE, "10-atlas-italie", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator Italie(Camera camera) => Planche("italie");
        [ScenarioDeCapture(GROUPE, "11-atlas-balkans", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator Balkans(Camera camera) => Planche("balkans-et-orient");

        // `docs/interface/references/atlas-1400`, depuis le projet Unity.
        static string DossierDeLAtlas => Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "..", "docs", "interface", "references", "atlas-1400"));
        // `references/eu4` du checkout principal : celui du dépôt, ou celui dont ce worktree dépend (le `.git` d'un worktree est un
        // fichier qui nomme `<checkout>/.git/worktrees/<nom>`).
        static string DossierDEuropa
        {
            get
            {
                string racine = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "..")), git = Path.Combine(racine, ".git");
                if (File.Exists(git))
                {
                    string ligne = File.ReadAllLines(git).FirstOrDefault(l => l.StartsWith("gitdir:", StringComparison.Ordinal));
                    if (ligne != null) racine = Path.GetFullPath(Path.Combine(ligne.Substring("gitdir:".Length).Trim(), "..", "..", ".."));
                }
                return Path.Combine(racine, "references", "eu4");
            }
        }

        static IEnumerator Planche(string cadre)
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            foreach (var ancienne in Object.FindObjectsByType<Transform>(FindObjectsSortMode.None).Where(t => t.parent == null && t.name.StartsWith(PLANCHE, StringComparison.Ordinal)).ToArray()) Object.Destroy(ancienne.gameObject);
            // L'atlas et la zone qui répond au cadre ; une image qui n'a pas la taille attendue (un pointeur LFS, une autre carte) est refusée.
            string chemin = Path.Combine(DossierDeLAtlas, "cadres.json");
            if (!File.Exists(chemin)) throw Faux("pas de " + chemin);
            var cadres = JsonUtility.FromJson<Cadres>(File.ReadAllText(chemin));
            var zone = cadres.zones?.SingleOrDefault(z => z.cadre == cadre) ?? throw Faux("cadres.json ne donne pas de zone pour « " + cadre + " »");
            var atlas = new Texture2D(2, 2) { name = cadres.atlas };
            if (!atlas.LoadImage(File.ReadAllBytes(Path.Combine(DossierDeLAtlas, cadres.atlas)))) throw Faux("l'atlas " + cadres.atlas + " ne se lit pas comme une image");
            if (atlas.width != cadres.largeur || atlas.height != cadres.hauteur) throw Faux("l'atlas fait " + atlas.width + " × " + atlas.height + ", cadres.json attend " + cadres.largeur + " × " + cadres.hauteur);
            if (zone.largeur <= 0 || zone.hauteur <= 0 || zone.x < 0 || zone.y < 0 || zone.x + zone.largeur > atlas.width || zone.y + zone.hauteur > atlas.height) throw Faux("la zone de « " + cadre + " » sort de l'atlas");
            var calques = carte.GetComponent<CalquesCarte>() ?? throw Faux("pas de calques sur la carte");
            if (calques.Mode != ModeDeCarte.Politique) throw Faux("la planche se pose sur la carte politique, pas sur le mode " + calques.Mode);

            // La carte du cadre, rendue dans une texture de la taille du panneau, sans la toile du cabinet ; puis la carte rendue telle qu'elle était.
            var toile = cabinet.transform.Find("Cabinet").GetComponent<Canvas>();
            RenderTexture cible = carte.camera.targetTexture; float aspectAvant = carte.camera.aspect; Vector2 centreAvant = carte.Vue.Centre; float demiAvant = carte.Vue.Demi; RenderMode modeAvant = toile.renderMode;
            var rendu = new RenderTexture((int)LARGEUR_PANNEAU, (int)HAUTEUR_PANNEAU, 24) { name = "Carte du cadre " + cadre };
            float aspect = LARGEUR_PANNEAU / HAUTEUR_PANNEAU; var terres = ScenarioCartePolitique.TerresDuCadre(guerre, cadre);
            List<string> lisibles;
            try
            {
                toile.renderMode = RenderMode.ScreenSpaceOverlay; carte.camera.targetTexture = rendu; carte.camera.aspect = aspect;
                var (centre, demi) = ScenarioCartePolitique.Cadrer(carte, terres, aspect);
                carte.Vue.Changer(aspect); carte.Vue.Centrer(centre, demi); carte.Vue.Poser(carte.camera, carte.transform); guerre.SuivreLaVue();
                for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
                // Les grands pays du cadre, ceux qui y tiennent au moins `TERRES_D_UN_GRAND_PAYS` terres, et ceux dont le nom se lit.
                var dans = new HashSet<long>(terres);
                var grands = guerre.Terres.Terres.Where(t => t.Pays != null && dans.Contains(t.CellId)).GroupBy(t => t.Pays).Where(g => g.Count() >= TERRES_D_UN_GRAND_PAYS).Select(g => g.Key).ToList();
                lisibles = guerre.NomsDesPays.Where(n => grands.Contains(n.Pays) && n.Opacite > 0f).Select(n => n.Texte).OrderBy(n => n, StringComparer.Ordinal).ToList();
                if (lisibles.Count == 0) throw Faux(cadre + " : aucun grand pays du cadre ne se lit sur la carte du jeu");
            }
            finally
            {
                carte.camera.targetTexture = cible; carte.camera.aspect = aspectAvant; toile.renderMode = modeAvant;
                carte.Vue.Changer(aspectAvant); carte.Vue.Centrer(centreAvant, demiAvant); carte.Vue.Poser(carte.camera, carte.transform); guerre.SuivreLaVue();
            }
            var figee = new RenderTexture(rendu.width, rendu.height, 0) { name = "Carte figée du cadre " + cadre }; Graphics.Blit(rendu, figee); rendu.Release();

            // La planche : sa caméra ne voit que son calque, et sa toile se règle sur une photo de 1920 × 1080.
            var racine = new GameObject(PLANCHE + " " + cadre);
            var camera = new GameObject("Caméra de la planche").AddComponent<Camera>(); camera.transform.SetParent(racine.transform, false);
            camera.clearFlags = CameraClearFlags.SolidColor; camera.backgroundColor = SocleInterface.Couleur("fond"); camera.cullingMask = 1 << CALQUE_DE_LA_PLANCHE;
            camera.targetTexture = new RenderTexture(LARGEUR, HAUTEUR, 24) { name = "Écran de la planche" }; camera.aspect = (float)LARGEUR / HAUTEUR;
            var planche = new GameObject("Toile de la planche", typeof(RectTransform), typeof(Canvas), typeof(CanvasScaler)); planche.transform.SetParent(racine.transform, false);
            var canvas = planche.GetComponent<Canvas>(); canvas.renderMode = RenderMode.ScreenSpaceCamera; canvas.worldCamera = camera; canvas.planeDistance = camera.nearClipPlane + 1f;
            var echelle = planche.GetComponent<CanvasScaler>(); echelle.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize; echelle.referenceResolution = new Vector2(LARGEUR, HAUTEUR);
            Text Ecrire(string texte, float x, float y, float largeur, int taille, string jeton) { var t = SocleInterface.Texte(planche.transform, texte, x, y, largeur, taille); t.color = SocleInterface.Couleur(jeton); t.horizontalOverflow = HorizontalWrapMode.Wrap; t.verticalOverflow = VerticalWrapMode.Overflow; return t; }
            string jour = TexteDuMonde.Date(guerre.Terres.Date);
            Ecrire("Carte politique du jeu et atlas : " + zone.titre, MARGE, 22, LARGEUR - 2 * MARGE, SocleInterface.Titre, "papier");
            Panneau(planche.transform, "Carte du jeu", figee, new Rect(0, 0, 1, 1), MARGE, LARGEUR_PANNEAU, HAUTEUR_PANNEAU);
            float largeurAtlas = zone.largeur, hauteurAtlas = zone.hauteur, s = Mathf.Min(LARGEUR_PANNEAU / largeurAtlas, HAUTEUR_PANNEAU / hauteurAtlas);
            var uv = new Rect((float)zone.x / atlas.width, 1f - (float)(zone.y + zone.hauteur) / atlas.height, (float)zone.largeur / atlas.width, (float)zone.hauteur / atlas.height);
            var droite = Panneau(planche.transform, "Atlas", atlas, uv, 2 * MARGE + LARGEUR_PANNEAU + (LARGEUR_PANNEAU - largeurAtlas * s) / 2f, largeurAtlas * s, hauteurAtlas * s);
            float sous = HAUT_DES_PANNEAUX + HAUTEUR_PANNEAU + 8;
            Ecrire("Le jeu : les pays servis au " + jour + ", cadrés sur leurs terres", MARGE, sous, LARGEUR_PANNEAU, SocleInterface.Corps, "papier");
            var legendeDroite = Ecrire(cadres.source, 2 * MARGE + LARGEUR_PANNEAU, sous, LARGEUR_PANNEAU, SocleInterface.Corps, "papier");
            string fichierEuropa = Path.Combine(DossierDEuropa, cadre + ".png"); bool europa = File.Exists(fichierEuropa);
            string noteEuropa = europa ? "Europa Universalis IV : capture locale lue ; la planche complète s'écrit hors du dépôt, jamais jointe (carte de Paradox)."
                : "Europa Universalis IV : aucune capture locale (" + cadre + ".png dans references/eu4, hors du dépôt) ; référence publique : la carte politique de 1444 du wiki officiel, et 1444 n'est pas 1400.";
            Ecrire(cadres.ecart + "\n" + noteEuropa, MARGE, sous + 34, LARGEUR - 2 * MARGE, SocleInterface.Corps, "or-vieilli");
            foreach (var t in racine.GetComponentsInChildren<Transform>(true)) t.gameObject.layer = CALQUE_DE_LA_PLANCHE;
            Canvas.ForceUpdateCanvases();

            // La planche complète, avec Europa à droite, s'écrit hors du dépôt quand la capture locale existe ; la planche publiée garde l'atlas.
            if (europa)
            {
                var capture = new Texture2D(2, 2) { name = "Europa Universalis IV" };
                if (!capture.LoadImage(File.ReadAllBytes(fichierEuropa))) throw Faux(fichierEuropa + " ne se lit pas comme une image");
                float e = Mathf.Min(LARGEUR_PANNEAU / capture.width, HAUTEUR_PANNEAU / capture.height); var cadreDroit = droite.rectTransform;
                Texture atlasMontre = droite.texture; Rect uvMontre = droite.uvRect; Vector2 place = cadreDroit.anchoredPosition, taille = cadreDroit.sizeDelta;
                droite.texture = capture; droite.uvRect = new Rect(0, 0, 1, 1); legendeDroite.text = "Europa Universalis IV : capture locale (" + cadre + ".png), carte de Paradox, jamais publiée";
                cadreDroit.anchoredPosition = new Vector2(2 * MARGE + LARGEUR_PANNEAU + (LARGEUR_PANNEAU - capture.width * e) / 2f, -(HAUT_DES_PANNEAUX + (HAUTEUR_PANNEAU - capture.height * e) / 2f)); cadreDroit.sizeDelta = new Vector2(capture.width * e, capture.height * e);
                Canvas.ForceUpdateCanvases(); yield return null;
                Directory.CreateDirectory(Path.Combine(DossierDEuropa, "planches"));
                CitadelPlayCheck.Capture(camera, Path.Combine(DossierDEuropa, "planches", cadre + ".png"), LARGEUR, HAUTEUR);
                droite.texture = atlasMontre; droite.uvRect = uvMontre; cadreDroit.anchoredPosition = place; cadreDroit.sizeDelta = taille; legendeDroite.text = cadres.source; Canvas.ForceUpdateCanvases();
            }
            for (int i = 0; i < 3; i++) yield return null;
            Debug.Log("CAPTURE modes de carte : planche « " + cadre + " » au " + jour + ", " + terres.Count + " terres cadrées ; grands pays lisibles : " + string.Join(", ", lisibles)
                + " ; atlas " + zone.x + "," + zone.y + " " + zone.largeur + " × " + zone.hauteur + " ; Europa " + (europa ? "lue, planche complète hors du dépôt" : "absente"));
            yield return camera;
        }

        // Un panneau d'image, centré dans la hauteur des panneaux, `uv` la part de la texture montrée.
        static RawImage Panneau(Transform parent, string nom, Texture texture, Rect uv, float x, float largeur, float hauteur)
        {
            var image = new GameObject(nom, typeof(RectTransform), typeof(RawImage)).GetComponent<RawImage>(); var cadre = image.rectTransform; cadre.SetParent(parent, false);
            cadre.anchorMin = cadre.anchorMax = cadre.pivot = new Vector2(0, 1); cadre.anchoredPosition = new Vector2(x, -(HAUT_DES_PANNEAUX + (HAUTEUR_PANNEAU - hauteur) / 2f)); cadre.sizeDelta = new Vector2(largeur, hauteur);
            image.texture = texture; image.uvRect = uv; image.raycastTarget = false;
            return image;
        }

        static InvalidOperationException Faux(string raison) => new InvalidOperationException("planche de l'atlas : " + raison);
    }
}
