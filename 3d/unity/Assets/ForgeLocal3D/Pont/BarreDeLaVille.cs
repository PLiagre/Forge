using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Pont
{
    // Ce qui donne son apparence à la barre : un bouton (parent, nom, action), un texte (parent), un panneau titré (parent,
    // titre, largeur, hauteur). La ville y branche le socle de l'interface ; la barre ne pose ni couleur ni police à elle.
    public sealed class FabriqueDeLaBarre
    {
        public Func<Transform, string, Action, Button> Bouton { get; }
        public Func<Transform, Text> Texte { get; }
        public Func<Transform, string, float, float, RectTransform> Panneau { get; }
        public FabriqueDeLaBarre(Func<Transform, string, Action, Button> bouton, Func<Transform, Text> texte, Func<Transform, string, float, float, RectTransform> panneau)
        {
            Bouton = bouton ?? throw new ArgumentNullException(nameof(bouton)); Texte = texte ?? throw new ArgumentNullException(nameof(texte));
            Panneau = panneau ?? throw new ArgumentNullException(nameof(panneau));
        }
    }

    // La barre des outils de la ville, sur une toile donnée : en bas, un panneau « Outils de la ville » qui porte un bouton par
    // geste de `OutilsDeLaVille.Gestes` sauf le retour, et sous eux la seule ligne d'aide ; en haut, « Retour à la carte ».
    // `Appliquer` montre une composition : les boutons visibles se rangent de gauche à droite, l'outil en main garde la couleur
    // pressée de son propre bouton, un bouton grisé n'est plus cliquable. Rien n'est lu ni décidé ici.
    public sealed class BarreDeLaVille
    {
        public const string TITRE = "Outils de la ville";
        const float MARGE = 24f, HAUT_TITRE = 88f, LARGEUR_BOUTON = 280f, HAUTEUR_BOUTON = 60f, ECART = 16f, HAUTEUR_LIGNE = 54f;
        const float LARGEUR_RETOUR = 320f, HAUTEUR_RETOUR = 52f;

        public RectTransform Panneau { get; }
        public Text Ligne { get; }
        readonly Dictionary<GesteDeLaVille, (Button bouton, Text texte, ColorBlock couleurs)> boutons = new();

        public BarreDeLaVille(Transform toile, FabriqueDeLaBarre fabrique, IReadOnlyDictionary<GesteDeLaVille, Action> gestes)
        {
            if (toile == null) throw new ArgumentNullException(nameof(toile));
            if (fabrique == null) throw new ArgumentNullException(nameof(fabrique));
            if (gestes == null) throw new ArgumentNullException(nameof(gestes));
            var dans = OutilsDeLaVille.Gestes.Where(g => g.geste != GesteDeLaVille.Retour).ToArray();
            float largeur = 2 * MARGE + dans.Length * LARGEUR_BOUTON + (dans.Length - 1) * ECART;
            Panneau = fabrique.Panneau(toile, TITRE, largeur, HAUT_TITRE + HAUTEUR_BOUTON + ECART + HAUTEUR_LIGNE + MARGE);
            Placer(Panneau, new Vector2(.5f, 0), new Vector2(0, MARGE), new Vector2(largeur, Panneau.sizeDelta.y));
            foreach (var (geste, nom, _) in OutilsDeLaVille.Gestes)
            {
                if (!gestes.TryGetValue(geste, out var action) || action == null) throw new ArgumentException("geste sans action : " + nom, nameof(gestes));
                var bouton = fabrique.Bouton(geste == GesteDeLaVille.Retour ? toile : Panneau, nom, action);
                var texte = bouton.GetComponentInChildren<Text>(true) ?? throw new InvalidOperationException("bouton sans texte : " + nom);
                var rect = (RectTransform)bouton.transform;
                if (geste == GesteDeLaVille.Retour) Placer(rect, new Vector2(.5f, 1), new Vector2(0, -MARGE), new Vector2(LARGEUR_RETOUR, HAUTEUR_RETOUR));
                else rect.sizeDelta = new Vector2(LARGEUR_BOUTON, HAUTEUR_BOUTON);
                // Le texte couvre tout le bouton : un libellé de deux lignes y tient.
                var t = texte.rectTransform; t.anchorMin = Vector2.zero; t.anchorMax = Vector2.one; t.pivot = new Vector2(.5f, .5f); t.offsetMin = t.offsetMax = Vector2.zero;
                texte.alignment = TextAnchor.MiddleCenter; texte.supportRichText = false;
                boutons[geste] = (bouton, texte, bouton.colors);
            }
            Ligne = fabrique.Texte(Panneau);
            Ligne.name = "Ligne d'aide"; Ligne.supportRichText = false; Ligne.horizontalOverflow = HorizontalWrapMode.Wrap;
            var l = Ligne.rectTransform; l.anchorMin = l.anchorMax = l.pivot = new Vector2(0, 1);
            l.anchoredPosition = new Vector2(MARGE, -(HAUT_TITRE + HAUTEUR_BOUTON + ECART)); l.sizeDelta = new Vector2(largeur - 2 * MARGE, HAUTEUR_LIGNE);
        }

        public Button Bouton(GesteDeLaVille geste) => boutons[geste].bouton;

        public void Appliquer(CompositionDesOutils composition)
        {
            if (composition == null) throw new ArgumentNullException(nameof(composition));
            float x = MARGE;
            foreach (var b in composition.Boutons)
            {
                var (bouton, texte, couleurs) = boutons[b.Geste];
                if (bouton.gameObject.activeSelf != b.Visible) bouton.gameObject.SetActive(b.Visible);
                if (texte.text != b.Libelle) texte.text = b.Libelle;
                if (bouton.interactable != b.Actif) bouton.interactable = b.Actif;
                var voulues = couleurs;
                if (b.Enfonce) voulues.normalColor = voulues.highlightedColor = voulues.selectedColor = couleurs.pressedColor;
                if (bouton.colors != voulues) bouton.colors = voulues;
                if (b.Geste == GesteDeLaVille.Retour || !b.Visible) continue;
                Placer((RectTransform)bouton.transform, new Vector2(0, 1), new Vector2(x, -HAUT_TITRE), new Vector2(LARGEUR_BOUTON, HAUTEUR_BOUTON));
                x += LARGEUR_BOUTON + ECART;
            }
            if (Ligne.text != composition.Ligne) Ligne.text = composition.Ligne;
        }

        // Une ancre, son pivot au même point, une position et une taille.
        static void Placer(RectTransform rect, Vector2 ancre, Vector2 position, Vector2 taille)
        {
            rect.anchorMin = rect.anchorMax = rect.pivot = ancre; rect.anchoredPosition = position; rect.sizeDelta = taille;
        }
    }
}
