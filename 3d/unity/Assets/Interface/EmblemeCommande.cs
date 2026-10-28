using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface
{
    // Signes gravés propres à l'interface, jamais des armoiries attribuées à une maison.
    [RequireComponent(typeof(CanvasRenderer))]
    public sealed class EmblemeCommande : MaskableGraphic
    {
        string motif;
        public static void Poser(Button bouton, string nom)
        {
            string motif = nom == "Terres et comptes" || nom == "Menu" ? "livre"
                : nom == "Plan du bourg" ? "bourg" : nom == "Puissances" ? "banniere" : null;
            if (motif == null) return;
            var objet = new GameObject("Repère " + motif, typeof(RectTransform), typeof(EmblemeCommande));
            var rect = objet.GetComponent<RectTransform>(); rect.SetParent(bouton.transform, false);
            rect.anchorMin = rect.anchorMax = new Vector2(0, .5f);
            rect.anchoredPosition = new Vector2(20, 0); rect.sizeDelta = new Vector2(18, 18);
            var signe = objet.GetComponent<EmblemeCommande>();
            signe.motif = motif; signe.color = SocleInterface.Couleur("papier"); signe.raycastTarget = false;
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
