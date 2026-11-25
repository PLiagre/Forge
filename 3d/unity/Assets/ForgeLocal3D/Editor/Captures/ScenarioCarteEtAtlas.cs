using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
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
    // ne change rien aux autres photos du groupe ; un autre groupe l'appelle par `Planche`. Elle échoue sans l'atlas, sur une zone
    // hors de l'image, si la zone ne nomme aucun grand pays, ou si l'un des grands pays que `cadres.json` donne à la zone (tirés des
    // repères de 1400) n'est pas servi sous ce nom ou ne se lit pas en entier sur la carte du cadre.
    // Avec -forgeRangerLaPlanche, et sur le monde frais seulement, la planche publiée s'écrit aussi dans le dépôt
    // (`atlas-1400/planche-du-jeu/<cadre>.png`), avec `planche.json` : le monde dont elle est la photo et son empreinte des terres.
    static class ScenarioCarteEtAtlas
    {
        const string GROUPE = "modes-de-carte", PLANCHE = "Planche de l'atlas";
        const int LARGEUR = 1920, HAUTEUR = 1080, IMAGES_DE_POSE = 12, CALQUE_DE_LA_PLANCHE = 5; // le calque « UI »
        // La planche en pixels de la photo : le titre, deux panneaux côte à côte, la source sous chacun, la note en pied.
        const float MARGE = 30, HAUT_DES_PANNEAUX = 92, LARGEUR_PANNEAU = 915, HAUTEUR_PANNEAU = 840;

        [Serializable] sealed class Zone { public string cadre = null, titre = null; public int x = 0, y = 0, largeur = 0, hauteur = 0; public string[] pays = null; }
        [Serializable] sealed class Cadres { public string atlas = null, source = null, ecart = null; public int largeur = 0, hauteur = 0; public Zone[] zones = null; }
        // La planche rangée dans le dépôt : le monde dont elle est la photo (de quoi relancer le même service et le reconnaître),
        // et, par cadre, les grands pays qui s'y lisaient.
        [Serializable] internal sealed class Rangee { public string cadre = null; public string[] pays = null; }
        [Serializable] internal sealed class PlancheRangee { public int graine = 0, jours = 0; public bool ia = false; public string date = null, empreinte = null; public Rangee[] cadres = null; }
        internal const string DOSSIER_RANGE = "planche-du-jeu", FICHE_RANGEE = "planche.json";

        [ScenarioDeCapture(GROUPE, "7-atlas-europe", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator Europe(Camera camera) => Planche("europe");
        [ScenarioDeCapture(GROUPE, "8-atlas-france", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator France(Camera camera) => Planche("france-et-iles");
        [ScenarioDeCapture(GROUPE, "9-atlas-empire", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator Empire(Camera camera) => Planche("empire");
        [ScenarioDeCapture(GROUPE, "10-atlas-italie", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator Italie(Camera camera) => Planche("italie");
        [ScenarioDeCapture(GROUPE, "11-atlas-balkans", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator Balkans(Camera camera) => Planche("balkans-et-orient");

        // `docs/interface/references/atlas-1400`, depuis le projet Unity.
        internal static string DossierDeLAtlas => Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "..", "docs", "interface", "references", "atlas-1400"));
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

        internal static IEnumerator Planche(string cadre)
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            // Rangée, la planche est la photo d'un monde que le build sait relancer : le service tel que la capture l'a lancé, au jour
            // poussé, sans pays choisi. Un autre amorçage, un jour joué ou un choix fait la rendraient impossible à reconnaître.
            bool ranger = Capture.Drapeau(Capture.RANGER_LA_PLANCHE);
            if (ranger)
            {
                string amorce = new[] { Capture.SERVICE_EPREUVE, Capture.SERVICE_PROGRAMME, Capture.SERVICE_MODIFICATEURS, Capture.TRAVAIL_ENCEINTE }.FirstOrDefault(Capture.Drapeau);
                if (amorce != null) throw Faux("la planche ne se range pas sur un service amorcé par " + amorce);
                if (guerre.Terres.Tick != Capture.JoursPousses) throw Faux("la planche ne se range que sur le monde frais : terres du tick " + guerre.Terres.Tick + ", service poussé à " + Capture.JoursPousses);
                if (ScenarioAccueil.Servie(cabinet) != null) throw Faux("la planche ne se range que sur le monde frais : « " + ScenarioAccueil.Servie(cabinet) + " » est déjà choisie");
            }
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
            // Les grands pays de la zone, tirés des repères de 1400 : chacun doit être servi sous ce nom.
            if (zone.pays == null || zone.pays.Length == 0) throw Faux("cadres.json ne nomme aucun grand pays pour « " + cadre + " »");
            string inconnus = string.Join(", ", zone.pays.Where(n => guerre.Terres.Pays.Count(p => p.Nom == n) != 1));
            if (inconnus.Length > 0) throw Faux(cadre + " : grands pays de l'atlas que le service ne sert pas sous ce nom : " + inconnus);
            var attendus = zone.pays.Select(n => guerre.Terres.Pays.Single(p => p.Nom == n).Id).ToList();
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
                // Un nom se lit quand il n'est ni masqué ni effacé, et que chacune de ses lettres tombe dans le panneau.
                bool Lisible(NomCourbe n) => !n.Masque && n.Opacite > 0f && n.Compose != null && n.Compose.Lettres.All(l =>
                    { Vector3 v = carte.camera.WorldToViewportPoint(carte.transform.TransformPoint(new Vector3(l.Point.x, 0f, l.Point.y))); return v.z > 0f && v.x >= 0f && v.x <= 1f && v.y >= 0f && v.y <= 1f; });
                var noms = guerre.NomsDesPays.GroupBy(n => n.Pays).ToDictionary(g => g.Key, g => g.First());
                string illisibles = string.Join(", ", attendus.Where(p => !noms.TryGetValue(p, out NomCourbe n) || !Lisible(n)).Select(p => guerre.Terres.NomDuPays(p)
                    + (noms.TryGetValue(p, out NomCourbe n) ? " (" + n.CorpsPx.ToString("0.#", CultureInfo.InvariantCulture) + " px, opacité " + n.Opacite.ToString("0.##", CultureInfo.InvariantCulture) + (n.Masque ? ", masqué" : "") + ")" : " (sans nom sur la carte)")));
                // Tous les noms lisibles du panneau, pour régler la liste d'une zone sur ce que la carte montre.
                lisibles = guerre.NomsDesPays.Where(Lisible).Select(n => n.Texte).OrderBy(n => n, StringComparer.Ordinal).ToList();
                if (illisibles.Length > 0) throw Faux(cadre + " : grands pays de l'atlas illisibles sur la carte du jeu : " + illisibles + " ; lisibles : " + string.Join(", ", lisibles));
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
            if (ranger) Ranger(camera, cadre, zone.pays, guerre.Terres, jour);
            Debug.Log("CAPTURE modes de carte : planche « " + cadre + " » au " + jour + ", " + terres.Count + " terres cadrées ; grands pays de l'atlas lus : " + string.Join(", ", zone.pays)
                + " ; noms lisibles : " + string.Join(", ", lisibles) + " ; atlas " + zone.x + "," + zone.y + " " + zone.largeur + " × " + zone.hauteur + " ; Europa " + (europa ? "lue, planche complète hors du dépôt" : "absente")
                + (ranger ? " ; rangée dans " + Path.Combine(DossierDeLAtlas, DOSSIER_RANGE) : ""));
            yield return camera;
        }

        // La planche publiée, écrite aussi dans `planche-du-jeu/<cadre>.png`, et sa ligne dans `planche.json`. Une fiche d'un autre monde
        // (autre graine, autres jours, autre IA, autres terres) est remplacée, et les images qu'elle décrivait sont effacées : le dossier
        // ne mêle jamais deux mondes.
        static void Ranger(Camera camera, string cadre, string[] pays, TerresDeLaCarte terres, string jour)
        {
            string dossier = Path.Combine(DossierDeLAtlas, DOSSIER_RANGE), fiche = Path.Combine(dossier, FICHE_RANGEE);
            Directory.CreateDirectory(dossier);
            var monde = new PlancheRangee { graine = Capture.GraineDuService, jours = Capture.JoursPousses, ia = Capture.Drapeau(Capture.SERVICE_IA), date = jour, empreinte = Empreinte(terres), cadres = new Rangee[0] };
            var lue = File.Exists(fiche) ? JsonUtility.FromJson<PlancheRangee>(File.ReadAllText(fiche)) : null;
            if (lue != null && lue.graine == monde.graine && lue.jours == monde.jours && lue.ia == monde.ia && lue.empreinte == monde.empreinte && lue.cadres != null) monde.cadres = lue.cadres;
            else foreach (string image in Directory.GetFiles(dossier, "*.png")) File.Delete(image);
            monde.cadres = monde.cadres.Where(r => r.cadre != cadre).Concat(new[] { new Rangee { cadre = cadre, pays = pays } }).OrderBy(r => r.cadre, StringComparer.Ordinal).ToArray();
            CitadelPlayCheck.Capture(camera, Path.Combine(dossier, cadre + ".png"), LARGEUR, HAUTEUR);
            File.WriteAllText(fiche, JsonUtility.ToJson(monde, true) + "\n", new UTF8Encoding(false));
        }

        // L'empreinte des terres servies : SHA-256 des lignes « cellule=pays » de chaque terre, et « cellule/rang=pays » de chacun de ses
        // lieux d'un autre pays, triées en ordinal et jointes par « \n ». Deux services qui la donnent égale dessinent la même carte politique.
        internal static string Empreinte(TerresDeLaCarte terres)
        {
            var lignes = terres.Terres.SelectMany(t => new[] { t.CellId.ToString(CultureInfo.InvariantCulture) + "=" + (t.Pays ?? "") }
                .Concat(t.AutresPays.Select(a => t.CellId.ToString(CultureInfo.InvariantCulture) + "/" + a.Rang.ToString(CultureInfo.InvariantCulture) + "=" + (a.Pays ?? ""))))
                .OrderBy(l => l, StringComparer.Ordinal);
            using (var sha = System.Security.Cryptography.SHA256.Create())
                return string.Concat(sha.ComputeHash(Encoding.UTF8.GetBytes(string.Join("\n", lignes))).Select(b => b.ToString("x2", CultureInfo.InvariantCulture)));
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
