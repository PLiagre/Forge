using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Net.Http;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;

namespace ForgeLocal3D.Captures
{
    // Lot 237 : le service sert les lieux d'une cellule. La capture tourne avec le service de `sim/` sur le
    // port du panneau ; on y lit `/lieu` de la cellule du panneau, et on montre à côté de lui la liste
    // `lieux` telle qu'elle arrive : une ligne par rang, sa surface, ses habitants, et une barre à la mesure
    // de ses habitants. Le scénario ne calcule aucun nombre du monde : il recopie ce que le service dit,
    // et échoue si la réponse ne porte pas de lieux.
    static class Lot237
    {
        const int IMAGES_DE_POSE = 10;
        const int DELAI_LECTURE_S = 60;
        const string HOTE = "127.0.0.1";
        const string POLICE = "LegacyRuntime.ttf";
        const float ECART_PLAN = 0.2f;
        static readonly Vector2 RESOLUTION_REFERENCE = new Vector2(1600, 900);
        const float MARGE = 16f;
        const float LARGEUR = 640f;
        const float HAUTEUR_TITRE = 64f;
        const float HAUTEUR_LISTE = 760f;
        const float LIGNE_MAX = 36f;
        const float LIGNE_MIN = 6f;
        const float LARGEUR_LIBELLE = 330f;
        const int POLICE_TITRE = 22;
        const int POLICE_MAX = 20;
        const int POLICE_MIN = 8;
        static readonly Color FOND = new Color(0.05f, 0.05f, 0.07f, 0.82f);
        static readonly Color BARRE_BOURG = new Color(0.93f, 0.62f, 0.25f, 1f);
        static readonly Color BARRE_LIEU = new Color(0.36f, 0.62f, 0.85f, 1f);

        [ScenarioDeCapture(237, "lieux-de-la-cellule")]
        static IEnumerator LieuxDeLaCellule(Camera camera)
        {
            long cellule = PanneauLieu.LireCellule(Environment.GetCommandLineArgs(), PanneauLieu.CELLULE_PAR_DEFAUT, out string erreur);
            if (erreur != null)
                throw new InvalidOperationException(erreur);
            string url = "http://" + HOTE + ":" + PanneauLieu.DEFAULT_SERVICE_PORT.ToString(CultureInfo.InvariantCulture)
                + "/lieu?cell=" + cellule.ToString(CultureInfo.InvariantCulture);
            // Hors du fil de l'éditeur : y attendre HttpClient peut ne jamais revenir.
            var (statut, corps) = System.Threading.Tasks.Task.Run(() =>
            {
                using (var http = new HttpClient { Timeout = TimeSpan.FromSeconds(DELAI_LECTURE_S) })
                using (var reponse = http.GetAsync(url).GetAwaiter().GetResult())
                    return ((int)reponse.StatusCode, reponse.Content.ReadAsStringAsync().GetAwaiter().GetResult());
            }).GetAwaiter().GetResult();
            if (statut != 200)
                throw new InvalidOperationException("GET " + url + " a rendu " + statut + " : " + corps);

            var lieu = LecteurJson.LireObjet(corps);
            if (!lieu.TryGetValue("lieux", out object brut) || !(brut is List<object> liste) || liste.Count == 0)
                throw new InvalidOperationException("la réponse de " + url + " ne porte pas de lieux");
            var lieux = liste.Cast<Dictionary<string, object>>().ToList();
            Montrer(camera, lieu, lieux);

            for (int i = 0; i < IMAGES_DE_POSE; i++)
                yield return null;
        }

        static string Entier(object valeur) => ((double)valeur).ToString("N0", CultureInfo.GetCultureInfo("fr-FR"));
        static string Surface(object valeur) => ((double)valeur).ToString("N1", CultureInfo.GetCultureInfo("fr-FR"));

        // Le tableau des lieux, en haut à droite, sur la caméra de la photo (le panneau du lieu est à gauche).
        static void Montrer(Camera camera, Dictionary<string, object> lieu, List<Dictionary<string, object>> lieux)
        {
            var toile = new GameObject("Lieux de la cellule (lot 237)", typeof(RectTransform));
            var canvas = toile.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceCamera;
            canvas.worldCamera = camera;
            canvas.planeDistance = camera.nearClipPlane + ECART_PLAN;
            var echelle = toile.AddComponent<CanvasScaler>();
            echelle.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            echelle.referenceResolution = RESOLUTION_REFERENCE;

            float ligne = Mathf.Clamp(HAUTEUR_LISTE / lieux.Count, LIGNE_MIN, LIGNE_MAX);
            int police = Mathf.Clamp(Mathf.RoundToInt(ligne * 0.6f), POLICE_MIN, POLICE_MAX);
            var fond = Rectangle(toile.transform, "Fond", new Vector2(-MARGE, -MARGE),
                new Vector2(LARGEUR, HAUTEUR_TITRE + ligne * lieux.Count + MARGE), new Vector2(1, 1), FOND);

            Texte(fond, "Titre", new Vector2(MARGE, -MARGE / 2), new Vector2(LARGEUR - 2 * MARGE, HAUTEUR_TITRE),
                "Cellule " + Entier(lieu["cell_id"]) + " · tick " + Entier(lieu["tick"]) + " : " + lieux.Count
                + " lieux servis par /lieu\nidentité (cell_id, rang) · " + Entier(lieu["population"]) + " habitants",
                POLICE_TITRE);

            double plusPeuple = Math.Max(1.0, lieux.Max(l => (double)l["population"]));
            float largeurBarre = LARGEUR - LARGEUR_LIBELLE - 2 * MARGE;
            for (int i = 0; i < lieux.Count; i++)
            {
                var l = lieux[i];
                bool bourg = (double)l["rang"] == 0.0;
                float y = -(HAUTEUR_TITRE + i * ligne);
                Texte(fond, "Lieu " + i, new Vector2(MARGE, y), new Vector2(LARGEUR_LIBELLE, ligne),
                    "rang " + Entier(l["rang"]) + (bourg ? " (bourg)" : "") + " · " + Surface(l["surface_km2"]) + " km² · "
                    + Entier(l["population"]) + " hab.", police);
                float part = (float)((double)l["population"] / plusPeuple);
                Rectangle(fond, "Barre " + i, new Vector2(MARGE + LARGEUR_LIBELLE, y - ligne * 0.15f),
                    new Vector2(Mathf.Max(1f, largeurBarre * part), ligne * 0.7f), new Vector2(0, 1),
                    bourg ? BARRE_BOURG : BARRE_LIEU);
            }
        }

        // Un rectangle coloré ancré par son coin `coin` (0,1 en haut à gauche ; 1,1 en haut à droite).
        static Transform Rectangle(Transform parent, string nom, Vector2 position, Vector2 taille, Vector2 coin, Color couleur)
        {
            var objet = new GameObject(nom, typeof(RectTransform));
            objet.transform.SetParent(parent, false);
            var cadre = (RectTransform)objet.transform;
            cadre.anchorMin = cadre.anchorMax = cadre.pivot = coin;
            cadre.anchoredPosition = position;
            cadre.sizeDelta = taille;
            objet.AddComponent<Image>().color = couleur;
            return objet.transform;
        }

        static void Texte(Transform parent, string nom, Vector2 position, Vector2 taille, string contenu, int taillePolice)
        {
            var objet = new GameObject(nom, typeof(RectTransform));
            objet.transform.SetParent(parent, false);
            var cadre = (RectTransform)objet.transform;
            cadre.anchorMin = cadre.anchorMax = cadre.pivot = new Vector2(0, 1);
            cadre.anchoredPosition = position;
            cadre.sizeDelta = taille;
            var texte = objet.AddComponent<Text>();
            texte.font = Resources.GetBuiltinResource<Font>(POLICE);
            texte.text = contenu;
            texte.fontSize = taillePolice;
            texte.color = Color.white;
            texte.alignment = TextAnchor.MiddleLeft;
            texte.horizontalOverflow = HorizontalWrapMode.Overflow;
            texte.verticalOverflow = VerticalWrapMode.Overflow;
        }
    }
}
