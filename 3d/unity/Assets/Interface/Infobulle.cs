using System;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace Forge.Interface
{
    // Lot #878 : la phrase d'une commande, sur un feuillet de papier près du curseur. Le feuillet vit sous la toile racine.
    public sealed class Infobulle : MonoBehaviour, IPointerEnterHandler, IPointerMoveHandler, IPointerExitHandler
    {
        public const float ECART_PX = 24f, LARGEUR_MAX = 420f, MARGE = 12f;
        const string NOM = "Infobulle";
        internal string phrase;
        public string Phrase => phrase;
        Canvas Toile { get { var toile = GetComponentInParent<Canvas>(); return toile != null ? toile.rootCanvas : null; } }

        public void OnPointerEnter(PointerEventData evenement) => Montrer(Toile, phrase, evenement.position);
        public void OnPointerMove(PointerEventData evenement) => Montrer(Toile, phrase, evenement.position);
        public void OnPointerExit(PointerEventData evenement) => Cacher(Toile);
        void OnDisable() { var toile = Toile; if (toile != null && toile.gameObject.activeInHierarchy) Cacher(toile); }

        // En pixels d'écran, origine en bas à gauche : à droite du point s'il y tient, sinon à gauche ; dessous, sinon dessus.
        // Le bord tourné vers le point est posé tel quel, sans arrondi ; si aucun côté ne tient, rien n'est recadré.
        public static Rect Placer(Vector2 point, Vector2 taille, Vector2 ecran)
        {
            float gauche = point.x + ECART_PX, droite = point.x - ECART_PX, haut = point.y - ECART_PX, bas = point.y + ECART_PX;
            if (gauche + taille.x <= ecran.x) droite = gauche + taille.x;
            else if (droite - taille.x >= 0) gauche = droite - taille.x;
            else throw new ArgumentException("infobulle de " + taille.x + " px sans place de part et d'autre de x = " + point.x + " sur " + ecran.x);
            if (haut - taille.y >= 0) bas = haut - taille.y;
            else if (bas + taille.y <= ecran.y) haut = bas + taille.y;
            else throw new ArgumentException("infobulle de " + taille.y + " px sans place de part et d'autre de y = " + point.y + " sur " + ecran.y);
            return Rect.MinMaxRect(gauche, bas, droite, haut);
        }

        public static RectTransform Montrer(Canvas toile, string texte, Vector2 point)
        {
            if (string.IsNullOrWhiteSpace(texte)) throw new ArgumentException("infobulle sans texte refusée");
            var feuillet = toile.transform.Find(NOM) as RectTransform;
            if (feuillet == null)
            {
                feuillet = new GameObject(NOM, typeof(RectTransform)).GetComponent<RectTransform>();
                feuillet.SetParent(toile.transform, false);
                feuillet.anchorMin = feuillet.anchorMax = feuillet.pivot = Vector2.zero;
                var papier = feuillet.gameObject.AddComponent<Image>();
                MatieresCabinet.Habiller(papier); papier.raycastTarget = false; // sinon le feuillet volerait le survol, et HorsCarte le prendrait pour un panneau
                SocleInterface.Texte(feuillet, "", MARGE, MARGE, LARGEUR_MAX - 2 * MARGE).name = "Phrase";
            }
            var ecrit = feuillet.GetComponentInChildren<Text>(true);
            ecrit.text = texte; ecrit.horizontalOverflow = HorizontalWrapMode.Wrap; ecrit.verticalOverflow = VerticalWrapMode.Overflow;
            float largeur = Mathf.Min(ecrit.preferredWidth + 2 * MARGE, LARGEUR_MAX);
            ecrit.rectTransform.sizeDelta = new Vector2(largeur - 2 * MARGE, 0); // la hauteur se lit à cette largeur
            var taille = new Vector2(largeur, ecrit.preferredHeight + 2 * MARGE);
            ecrit.rectTransform.sizeDelta = taille - 2 * MARGE * Vector2.one;
            feuillet.sizeDelta = taille;
            feuillet.SetAsLastSibling(); feuillet.gameObject.SetActive(true);
            float echelle = toile.scaleFactor; Rect ecran = toile.pixelRect;
            feuillet.anchoredPosition = Placer(point - ecran.position, taille * echelle, ecran.size).position / echelle;
            return feuillet;
        }

        public static void Cacher(Canvas toile) { var feuillet = toile.transform.Find(NOM); if (feuillet != null) feuillet.gameObject.SetActive(false); }
    }
}
