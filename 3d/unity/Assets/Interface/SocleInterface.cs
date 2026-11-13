using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem.UI;
using UnityEngine.UI;

namespace Forge.Interface
{
    public sealed class SocleInterface : MonoBehaviour
    {
        void Start() => Creer().transform.SetParent(transform, false);

        public const int Corps = 18, Titre = 28, Espacement = 24, HauteurCommande = 44;
        static readonly Dictionary<string, string> Palette = new Dictionary<string, string>
        {
            { "fond", "#211E1A" }, { "papier", "#E8DDC9" }, { "encre", "#302820" },
            { "secondaire", "#625548" }, { "accent", "#345261" }, { "alerte", "#8B342E" },
            { "or", "#B49A61" }, { "accord", "#405444" }, { "mer", "#384A4D" },
            { "pierre", "#1C1B19" }, { "bois-brule", "#2B211B" }, { "metal", "#3E3B33" }, { "sang", "#7A1E19" },
            { "cuivre", "#A8683C" }, { "or-vieilli", "#B49A61" }, { "vert-de-gris", "#5E8C7A" }
        };
        public static IReadOnlyList<string> Jetons { get; } = new List<string>(Palette.Keys);

        public static Color Couleur(string nom)
        {
            if (!Palette.TryGetValue(nom, out var hex)) throw new ArgumentException("Jeton absent : " + nom);
            ColorUtility.TryParseHtmlString(hex, out var couleur);
            return couleur;
        }

        // Pigments d'atlas : la teinte politique reste celle reçue, seule sa présentation change.
        public static Color Pigment(Color couleur)
        {
            Color.RGBToHSV(couleur, out float teinte, out float saturation, out float valeur);
            return Color.Lerp(Color.HSVToRGB(teinte, saturation * .38f, .53f + valeur * .08f),
                Couleur("papier"), .16f);
        }

        // Lot #849 : le contraste WCAG 2.1 des jetons, jugé contre la matière que chaque texte ou trait borde.
        public static Color Attenue => Color.Lerp(Couleur("papier"), Couleur("metal"), .30f); // le texte de l'état inactif : une teinte dérivée, pas un jeton
        public enum Usage { Texte, Trait }
        static readonly CultureInfo Fr = CultureInfo.GetCultureInfo("fr-FR");
        public static readonly IReadOnlyList<(string devant, string derriere, Usage usage)> Paires = new (string, string, Usage)[]
        {
            ("papier", "pierre", Usage.Texte), ("papier", "bois-brule", Usage.Texte), ("papier", "metal", Usage.Texte), ("papier", "sang", Usage.Texte),
            ("sang", "papier", Usage.Texte), ("encre", "papier", Usage.Texte), ("secondaire", "papier", Usage.Texte),
            ("or-vieilli", "pierre", Usage.Texte), ("vert-de-gris", "pierre", Usage.Texte), ("attenue", "metal", Usage.Texte),
            ("cuivre", "bois-brule", Usage.Trait), ("cuivre", "papier", Usage.Trait), ("or-vieilli", "bois-brule", Usage.Trait),
            ("papier", "bois-brule", Usage.Trait), ("vert-de-gris", "pierre", Usage.Trait), ("sang", "papier", Usage.Trait)
        };

        internal static Color Teinte(string nom) => nom == "attenue" ? Attenue : Couleur(nom);
        static double Luminance(Color c)
        {
            double Lin(float v) => v <= .03928f ? v / 12.92 : Math.Pow((v + .055) / 1.055, 2.4);
            return .2126 * Lin(c.r) + .7152 * Lin(c.g) + .0722 * Lin(c.b);
        }
        public static double Contraste(Color devant, Color derriere)
        {
            double a = Luminance(devant), b = Luminance(derriere);
            return (Math.Max(a, b) + .05) / (Math.Min(a, b) + .05);
        }
        static string Rapport(double v) => v.ToString("0.0", Fr) + ":1";

        // null si chaque paire tient son seuil (4,5 en texte, 3 en trait), sinon la première fautive.
        public static string Refuse(IEnumerable<(string, string, Usage)> paires)
        {
            foreach (var (devant, derriere, usage) in paires)
            {
                double seuil = usage == Usage.Texte ? 4.5 : 3, mesure = Contraste(Teinte(devant), Teinte(derriere));
                if (mesure < seuil) return devant + " sur " + derriere + " : " + Rapport(mesure) + " < " + Rapport(seuil) + " (" + (usage == Usage.Texte ? "texte" : "trait") + ")";
            }
            return null;
        }

        static void Exiger(string contenu, string nom)
        {
            if (string.IsNullOrWhiteSpace(contenu)) throw new ArgumentException("information absente : " + nom, nom);
        }
        internal static Image Aplat(RectTransform cadre, Color couleur)
        {
            var image = cadre.gameObject.AddComponent<Image>(); image.color = couleur; image.raycastTarget = false;
            return image;
        }

        // Un texte à la hauteur de ses lignes, avec de la marge : la toile le recompose à son échelle (1280 × 720 : 2/3), et un cadre calé à l'échelle 1 couperait la dernière ligne.
        internal static void Ajuster(Text texte) => texte.rectTransform.SetSizeWithCurrentAnchors(RectTransform.Axis.Vertical, Mathf.Ceil(texte.preferredHeight * 1.1f) + 2);

        // Le registre : chaque garde passe avant la première création, pour ne laisser aucun enfant à un refus.
        public static Text Rubrique(Transform parent, string titre, float x, float y, float largeur, bool sombre = false)
        {
            Exiger(titre, nameof(titre));
            var texte = Texte(parent, string.Join(" ", titre.ToUpper(Fr).Select(c => c.ToString())), x, y, largeur, Titre);
            texte.name = "Rubrique"; texte.color = Couleur(sombre ? "papier" : "sang");
            Ajuster(texte); float bas = y + texte.rectTransform.rect.height + 6;
            for (int i = 0; i < 2; i++) Aplat(Cadre(parent, "Filet", x, bas + 4 * i, largeur, 1), Couleur("metal"));
            return texte;
        }

        public static RectTransform LigneDeCompte(Transform parent, string libelle, decimal? valeur, string unite, float x, float y, float largeur)
        {
            Exiger(libelle, nameof(libelle)); Exiger(unite, nameof(unite));
            var ligne = Cadre(parent, "Ligne " + libelle, x, y, largeur, Corps);
            var gauche = Texte(ligne, libelle, 0, 0, largeur * .4f); gauche.name = "Libellé";
            var droite = Texte(ligne, "", largeur * .4f, 0, largeur * .6f); droite.name = "Valeur"; droite.alignment = TextAnchor.UpperRight;
            EtatsLecture.Mesure(droite, valeur, unite);
            Ajuster(gauche); Ajuster(droite);
            ligne.sizeDelta = new Vector2(largeur, Mathf.Max(gauche.rectTransform.rect.height, droite.rectTransform.rect.height));
            return ligne;
        }

        public static Text PiedDeFeuillet(Transform parent, string date, float x, float y, float largeur)
        {
            Exiger(date, nameof(date));
            var pied = Texte(parent, date, x, y, largeur, 16); pied.name = "Pied de feuillet"; pied.color = Couleur("secondaire");
            return pied;
        }

        public static Text NoteEnMarge(Transform parent, string texte, float x, float y, float largeur)
        {
            Exiger(texte, nameof(texte));
            if (texte.Any(char.IsDigit)) throw new ArgumentException("une note en marge ne porte aucun nombre : « " + texte + " »", nameof(texte));
            var note = Texte(parent, texte, x, y, largeur, 16); note.name = "Note en marge"; note.color = Couleur("secondaire");
            return note;
        }

        public static RectTransform Separateur(Transform parent, float x, float y, float largeur)
        {
            var separateur = Cadre(parent, "Séparateur", x, y, largeur, 9);
            Aplat(Cadre(separateur, "Filet", 0, 4, largeur, 1), Couleur("metal"));
            var losange = Cadre(separateur, "Losange", 0, 0, 8, 8);
            losange.pivot = new Vector2(.5f, .5f); losange.anchoredPosition = new Vector2(largeur / 2, -4.5f); losange.localRotation = Quaternion.Euler(0, 0, 45);
            Aplat(losange, Couleur("metal"));
            return separateur;
        }

        public static Image Sceau(Transform parent, float x, float y)
        {
            var sceau = Cadre(parent, "Sceau", x, y, 28, 28).gameObject.AddComponent<Image>();
            sceau.sprite = MatieresCabinet.SceauDeCire; sceau.raycastTarget = false;
            return sceau;
        }

        public static Font Police(bool titre) =>
            Resources.Load<Font>(titre ? "Forge/Polices/NotoSerif-Regular" : "Forge/Polices/NotoSans-Regular");

        internal static RectTransform Cadre(Transform parent, string nom, float x, float y, float largeur, float hauteur)
        {
            var rect = new GameObject(nom, typeof(RectTransform)).GetComponent<RectTransform>();
            rect.SetParent(parent, false);
            rect.anchorMin = rect.anchorMax = rect.pivot = new Vector2(0, 1);
            rect.anchoredPosition = new Vector2(x, -y);
            rect.sizeDelta = new Vector2(largeur, hauteur);
            return rect;
        }

        public static Text Texte(Transform parent, string contenu, float x, float y, float largeur, int taille = Corps)
        {
            var texte = Cadre(parent, contenu, x, y, largeur, taille * 3).gameObject.AddComponent<Text>();
            texte.font = Police(taille >= Titre);
            texte.text = contenu;
            texte.fontSize = taille;
            texte.color = Couleur("encre");
            texte.raycastTarget = false;
            return texte;
        }

        public static RectTransform Panneau(Transform parent, string nom, float x, float y, float largeur, float hauteur, bool sombre = false)
        {
            var cadre = Cadre(parent, nom, x, y, largeur, hauteur);
            MatieresCabinet.Habiller(cadre.gameObject.AddComponent<Image>(), sombre);
            var ombre = cadre.gameObject.AddComponent<Shadow>();
            ombre.effectDistance = new Vector2(4, -6);
            ombre.effectColor = new Color(0, 0, 0, .35f);
            Cadre(cadre, "Filet", Espacement, 70, largeur - 2 * Espacement, 1).gameObject.AddComponent<Image>().color = Couleur("or");
            var titre = Texte(cadre, nom, Espacement, Espacement, largeur - 2 * Espacement, Titre);
            if (sombre) titre.color = Couleur("papier");
            return cadre;
        }

        public static Button Commande(Transform parent, string nom, float x, float y, Action action, bool active = true, string phrase = null)
        {
            if (phrase != null && string.IsNullOrWhiteSpace(phrase)) throw new ArgumentException("phrase vide refusée : " + nom);
            var cadre = Cadre(parent, nom, x, y, 340, HauteurCommande);
            var image = cadre.gameObject.AddComponent<Image>();
            MatieresCabinet.Habiller(image, bouton: true);
            var bouton = cadre.gameObject.AddComponent<Button>();
            bouton.targetGraphic = image;
            var couleurs = bouton.colors;
            couleurs.normalColor = Couleur("secondaire");
            couleurs.highlightedColor = Couleur("accent");
            couleurs.selectedColor = Couleur("accent");
            couleurs.pressedColor = Couleur("fond");
            couleurs.disabledColor = new Color(.40f, .38f, .34f, .65f);
            couleurs.fadeDuration = 0;
            bouton.colors = couleurs;
            bouton.interactable = active;
            bouton.onClick.AddListener(() => action?.Invoke());
            var repere = cadre.gameObject.AddComponent<Outline>();
            repere.effectColor = Couleur("or");
            repere.effectDistance = new Vector2(3, -3);
            repere.enabled = false;
            var focus = cadre.gameObject.AddComponent<EventTrigger>();
            foreach (var type in new[] { EventTriggerType.Select, EventTriggerType.Deselect })
            {
                var entree = new EventTrigger.Entry { eventID = type };
                entree.callback.AddListener(_ => repere.enabled = type == EventTriggerType.Select);
                focus.triggers.Add(entree);
            }
            var texte = Texte(cadre, nom, 0, 0, 340);
            texte.rectTransform.sizeDelta = cadre.sizeDelta;
            texte.alignment = TextAnchor.MiddleCenter;
            texte.color = Couleur("papier");
            EmblemeCommande.Poser(bouton, nom);
            if (phrase != null) cadre.gameObject.AddComponent<Infobulle>().phrase = phrase; // lot #878 : la commande dit ce qu'elle fait au survol
            return bouton;
        }

        public static GameObject Creer()
        {
            var racine = new GameObject("Galerie du socle");
            var evenements = new GameObject("Navigation", typeof(EventSystem), typeof(InputSystemUIInputModule));
            evenements.transform.SetParent(racine.transform);
            var toile = new GameObject("Documents", typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
            toile.transform.SetParent(racine.transform);
            var canvas = toile.GetComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            var echelle = toile.GetComponent<CanvasScaler>();
            echelle.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            echelle.referenceResolution = new Vector2(1920, 1080);
            var fond = Cadre(toile.transform, "Fond", 0, 0, 1920, 1080);
            fond.gameObject.AddComponent<Image>().color = Couleur("fond");
            Texte(fond, "F O R G E", 96, 70, 900, 54).color = Couleur("papier");
            Texte(fond, "LE CABINET  /  GALERIE DU SOCLE", 100, 152, 900).color = Couleur("or");
            var domaine = Panneau(fond, "Le domaine", 96, 242, 980, 610);
            Texte(domaine, "Un territoire, des lieux, des habitants.", 24, 88, 900);
            Texte(domaine, "Les dossiers restent ouverts côte à côte pour éclairer vos choix.", 24, 132, 900);
            var retour = Texte(domaine, "Choisissez une commande pour éprouver le composant.", 24, 470, 900);
            Commande(domaine, "Consulter le dossier", 24, 240, () => retour.text = "Le dossier reste ouvert. Aucun ordre envoyé au monde.",
                phrase: "Ouvre le dossier sans rien envoyer au monde.");
            Commande(domaine, "En attente du monde", 24, 320, null, false, "Indisponible : aucune partie chargée.");
            Texte(domaine, "Commande indisponible : aucune partie chargée.", 24, 380, 900);
            var conseil = Panneau(fond, "Le conseil", 1124, 242, 700, 610);
            Texte(conseil, "Décider peu, mais décider de ce qui compte.", 24, 88, 650);
            Texte(conseil, "Papier clair, encre sombre.\nUn accent de cire pour le focus.", 24, 150, 650);
            var focus = Commande(conseil, "Parcourir au clavier", 24, 240, () => retour.text = "Le conseil et le domaine restent visibles ensemble.",
                phrase: "Passe d'une commande à l'autre avec les flèches ; Entrée agit.");
            Texte(conseil, "Flèches pour parcourir · Entrée pour agir", 24, 320, 650);
            evenements.GetComponent<EventSystem>().firstSelectedGameObject = focus.gameObject;
            evenements.GetComponent<EventSystem>().SetSelectedGameObject(focus.gameObject);
            Texte(fond, "Démonstration visuelle — aucune partie chargée", 96, 924, 1200).color = Couleur("papier");
            Texte(fond, "UI-01  ·  Noto Serif & Noto Sans  ·  Aucun chiffre de simulation", 96, 966, 1500).color = Couleur("or");
            return racine;
        }

#if UNITY_EDITOR
        [UnityEditor.MenuItem("Forge/Interface/Galerie du socle")]
        public static void OuvrirGalerie()
        {
            if (!UnityEditor.SceneManagement.EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            UnityEditor.SceneManagement.EditorSceneManager.NewScene(UnityEditor.SceneManagement.NewSceneSetup.EmptyScene);
            var galerie = new GameObject("Scène du socle", typeof(SocleInterface));
            var camera = new GameObject("Caméra de galerie").AddComponent<Camera>();
            camera.transform.SetParent(galerie.transform);
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = Couleur("fond");
            UnityEditor.EditorApplication.ExecuteMenuItem("Window/General/Game");
            UnityEditor.EditorApplication.isPlaying = true;
        }
#endif
    }
}
