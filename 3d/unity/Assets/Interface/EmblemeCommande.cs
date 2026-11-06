using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface
{
    // Signes gravés propres à l'interface, jamais des armoiries attribuées à une maison.
    [RequireComponent(typeof(CanvasRenderer))]
    public sealed class EmblemeCommande : MaskableGraphic
    {
        string motif;
        static string Motif(string nom) => nom == "Terres et comptes" ? "coffre" : nom == "Autres maisons" ? "maisons" : nom == "Menu" ? "livre"
            : nom == "Plan du bourg" ? "bourg" : nom == "Puissances" ? "banniere"
            : nom == "Habitants" ? "foule" : nom == "Flux" ? "fleche" : null;
        public static void Poser(Button bouton, string nom)
        {
            string motif = Motif(nom);
            if (motif == null) return;
            var objet = new GameObject("Repère " + motif, typeof(RectTransform), typeof(EmblemeCommande));
            var rect = objet.GetComponent<RectTransform>(); rect.SetParent(bouton.transform, false);
            rect.anchorMin = rect.anchorMax = new Vector2(0, .5f);
            rect.anchoredPosition = new Vector2(20, 0); rect.sizeDelta = new Vector2(18, 18);
            var signe = objet.GetComponent<EmblemeCommande>();
            signe.motif = motif; signe.color = SocleInterface.Couleur("papier"); signe.raycastTarget = false;
        }
        // Lot #1002 : une commande de la barre du haut réduite à son motif ; son nom ne s'écrit plus, sa phrase le dit au survol.
        public static Button Icone(Transform barre, string nom, float x, System.Action action, string phrase)
        {
            string motif = Motif(nom) ?? throw new System.ArgumentException("icône sans motif : " + nom);
            var bouton = SocleInterface.Commande(barre, nom, x, 0, action, phrase: phrase);
            bouton.GetComponent<RectTransform>().sizeDelta = new Vector2(56, 44);
            bouton.GetComponentInChildren<Text>().gameObject.SetActive(false);
            var repere = (RectTransform)bouton.transform.Find("Repère " + motif);
            repere.anchorMin = repere.anchorMax = repere.pivot = new Vector2(.5f, .5f);
            repere.anchoredPosition = Vector2.zero; repere.localScale = Vector3.one * 1.5f;
            return bouton;
        }
        protected override void OnPopulateMesh(VertexHelper dessin)
        {
            dessin.Clear();
            if (motif == "livre")
            {
                Trait(dessin, -7, -6, 14, 1); Trait(dessin, -7, 6, 14, 1);
                Trait(dessin, -7, -6, 1, 13); Trait(dessin, 6, -6, 1, 13);
                Trait(dessin, 0, -6, 1, 13); Trait(dessin, -4, 2, 2, 1); Trait(dessin, 3, 2, 2, 1);
            }
            else if (motif == "coffre") // une caisse, son couvercle bombé et sa serrure
            {
                Trait(dessin, -7, -7, 14, 1); Trait(dessin, -7, -7, 1, 8); Trait(dessin, 6, -7, 1, 8);
                Trait(dessin, -7, 1, 14, 3); Trait(dessin, -6, 4, 12, 2); Trait(dessin, -1, -3, 2, 4);
            }
            else if (motif == "maisons") // deux pignons côte à côte : le toit en gradins, les murs, le seuil et la porte
                for (int x = -8; x <= 0; x += 8)
                {
                    Trait(dessin, x, -1, 8, 2); Trait(dessin, x + 1, 1, 6, 2); Trait(dessin, x + 2, 3, 4, 2); Trait(dessin, x + 3, 5, 2, 2);
                    Trait(dessin, x + 1, -7, 6, 1); Trait(dessin, x + 1, -7, 1, 6); Trait(dessin, x + 6, -7, 1, 6); Trait(dessin, x + 3, -7, 2, 3);
                }
            else if (motif == "bourg")
            {
                Trait(dessin, -7, -7, 14, 2); Trait(dessin, -7, -5, 3, 11);
                Trait(dessin, 4, -5, 3, 11); Trait(dessin, -4, 0, 8, 2);
                Trait(dessin, -1, -5, 2, 3);
            }
            else if (motif == "banniere")
            {
                Trait(dessin, -5, -8, 2, 16); Trait(dessin, -3, 1, 10, 6);
                Trait(dessin, -7, -8, 6, 1);
            }
            else if (motif == "foule")
            {
                Trait(dessin, -8, -7, 4, 5); Trait(dessin, -2, -7, 4, 7); Trait(dessin, 4, -7, 4, 5);
                Trait(dessin, -7, -1, 2, 2); Trait(dessin, -1, 2, 2, 3); Trait(dessin, 5, -1, 2, 2);
            }
            else if (motif == "fleche")
            {
                Trait(dessin, -8, -1, 11, 2); Trait(dessin, 3, -5, 2, 10);
                Trait(dessin, 5, -3, 2, 6); Trait(dessin, 7, -1, 2, 2);
            }
        }
        void Trait(VertexHelper dessin, float x, float y, float largeur, float hauteur)
        {
            int i = dessin.currentVertCount;
            dessin.AddVert(new Vector3(x, y), color, Vector2.zero);
            dessin.AddVert(new Vector3(x, y + hauteur), color, Vector2.zero);
            dessin.AddVert(new Vector3(x + largeur, y + hauteur), color, Vector2.zero);
            dessin.AddVert(new Vector3(x + largeur, y), color, Vector2.zero);
            dessin.AddTriangle(i, i + 1, i + 2); dessin.AddTriangle(i, i + 2, i + 3);
        }
    }
}
