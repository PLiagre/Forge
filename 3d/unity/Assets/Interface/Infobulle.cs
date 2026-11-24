using System;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace Forge.Interface
{
    // La phrase d'une commande, sur un feuillet de papier près du curseur. Le feuillet vit sous la toile racine.
    public sealed class Infobulle : MonoBehaviour, IPointerEnterHandler, IPointerMoveHandler, IPointerExitHandler
    {
        public const float ECART_PX = 24f, LARGEUR_MAX = 420f, MARGE = 12f;
        const string NOM = "Infobulle";
        internal string phrase;
        public RectTransform eviter; // une zone que le feuillet ne recouvre pas, quand elle est affichée
        public string Phrase => phrase;
        Canvas Toile { get { var toile = GetComponentInParent<Canvas>(); return toile != null ? toile.rootCanvas : null; } }

        public void OnPointerEnter(PointerEventData evenement) => Montrer(Toile, phrase, evenement.position, ZoneAEviter());
        public void OnPointerMove(PointerEventData evenement) => Montrer(Toile, phrase, evenement.position, ZoneAEviter());
        // La zone à éviter en pixels d'écran, origine en bas à gauche ; nulle sans zone ou zone masquée.
        Rect? ZoneAEviter()
        {
            if (eviter == null || !eviter.gameObject.activeInHierarchy) return null;
            var toile = Toile; Camera camera = toile != null && toile.renderMode != RenderMode.ScreenSpaceOverlay ? toile.worldCamera : null; var coins = new Vector3[4]; eviter.GetWorldCorners(coins);
            Vector2 a = RectTransformUtility.WorldToScreenPoint(camera, coins[0]), b = RectTransformUtility.WorldToScreenPoint(camera, coins[2]);
            return Rect.MinMaxRect(Mathf.Min(a.x, b.x), Mathf.Min(a.y, b.y), Mathf.Max(a.x, b.x), Mathf.Max(a.y, b.y));
        }
        public void OnPointerExit(PointerEventData evenement) => Cacher(Toile);
        void OnDisable() { var toile = Toile; if (toile != null && toile.gameObject.activeInHierarchy) Cacher(toile); }

        // En pixels d'écran, origine en bas à gauche : à droite du point s'il y tient, sinon à gauche ; dessous, sinon dessus.
        // Le bord tourné vers le point est posé tel quel, sans arrondi ; si aucun côté ne tient, rien n'est recadré.
        // Si le feuillet ainsi placé recouvre la zone à éviter, il passe au-dessus d'elle à `ECART_PX` s'il y tient, sinon au-dessous, sinon à sa droite, sinon à sa gauche ;
        // si aucun côté de la zone ne tient dans l'écran, il reste où il était.
        public static Rect Placer(Vector2 point, Vector2 taille, Vector2 ecran, Rect? eviter = null)
        {
            Rect pose = PlacerSansZone(point, taille, ecran); if (eviter == null || !pose.Overlaps(eviter.Value)) return pose;
            Rect zone = eviter.Value;
            if (zone.yMax + ECART_PX + taille.y <= ecran.y) return new Rect(pose.x, zone.yMax + ECART_PX, taille.x, taille.y);
            if (zone.yMin - ECART_PX - taille.y >= 0) return new Rect(pose.x, zone.yMin - ECART_PX - taille.y, taille.x, taille.y);
            if (zone.xMax + ECART_PX + taille.x <= ecran.x) return new Rect(zone.xMax + ECART_PX, pose.y, taille.x, taille.y);
            if (zone.xMin - ECART_PX - taille.x >= 0) return new Rect(zone.xMin - ECART_PX - taille.x, pose.y, taille.x, taille.y);
            return pose;
        }

        static Rect PlacerSansZone(Vector2 point, Vector2 taille, Vector2 ecran)
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

        // `eviter` : la zone à ne pas recouvrir, en pixels d'écran.
        public static RectTransform Montrer(Canvas toile, string texte, Vector2 point, Rect? eviter = null)
        {
            if (string.IsNullOrWhiteSpace(texte)) throw new ArgumentException("infobulle sans texte refusée");
            var feuillet = toile.transform.Find(NOM) as RectTransform;
            if (feuillet == null)
            {
                feuillet = new GameObject(NOM, typeof(RectTransform)).GetComponent<RectTransform>();
                feuillet.SetParent(toile.transform, false);
                feuillet.anchorMin = feuillet.anchorMax = feuillet.pivot = Vector2.zero;
                var papier = feuillet.gameObject.AddComponent<Image>();
                MatieresCabinet.Habiller(papier, infobulle: true); papier.raycastTarget = false; // sinon le feuillet volerait le survol, et HorsCarte le prendrait pour un panneau
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
            Rect zone = eviter ?? default; feuillet.anchoredPosition = Placer(point - ecran.position, taille * echelle, ecran.size, eviter == null ? (Rect?)null : new Rect(zone.position - ecran.position, zone.size)).position / echelle;
            return feuillet;
        }

        public static void Cacher(Canvas toile) { var feuillet = toile.transform.Find(NOM); if (feuillet != null) feuillet.gameObject.SetActive(false); }
    }
}
