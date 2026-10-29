using System;
using System.Collections.Generic;
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
            { "or", "#B49A61" }, { "accord", "#405444" }, { "mer", "#384A4D" }
        };

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

        public static Font Police(bool titre) =>
            Resources.Load<Font>(titre ? "Forge/Polices/NotoSerif-Regular" : "Forge/Polices/NotoSans-Regular");

        static RectTransform Cadre(Transform parent, string nom, float x, float y, float largeur, float hauteur)
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
