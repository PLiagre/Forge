using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface
{
    public sealed class Feuillet : MonoBehaviour
    {
        RectTransform cadre;
        Text contenu;
        public bool Ouvert => cadre != null && cadre.gameObject.activeSelf;
        public void Initialiser(Transform parent, string titre)
        {
            if (cadre != null) return;
            cadre = SocleInterface.Panneau(parent, titre, 24, 124, 740, 760);
            var fermer = SocleInterface.Commande(cadre, "Fermer", 588, 20, Fermer);
            fermer.GetComponent<RectTransform>().sizeDelta = new Vector2(128, 44);
            fermer.GetComponentInChildren<Text>().rectTransform.sizeDelta = new Vector2(128, 44);
            var fenetre = new GameObject("Lecture défilante", typeof(RectTransform), typeof(Image), typeof(RectMask2D), typeof(ScrollRect));
            var rect = fenetre.GetComponent<RectTransform>();
            rect.SetParent(cadre, false);
            rect.anchorMin = rect.anchorMax = rect.pivot = new Vector2(0, 1);
            rect.anchoredPosition = new Vector2(24, -88);
            rect.sizeDelta = new Vector2(692, 648);
            fenetre.GetComponent<Image>().color = Color.clear;
            contenu = SocleInterface.Texte(rect, "Lecture en attente…", 0, 0, 692);
            contenu.supportRichText = false;
            var defilement = fenetre.GetComponent<ScrollRect>();
            defilement.viewport = rect; defilement.content = contenu.rectTransform;
            defilement.horizontal = false; defilement.vertical = true;
            defilement.movementType = ScrollRect.MovementType.Clamped;
            defilement.inertia = false; defilement.scrollSensitivity = 24;
            Fermer();
        }
        public void Ouvrir() { cadre.SetAsLastSibling(); cadre.gameObject.SetActive(true); }
        public void Fermer() => cadre.gameObject.SetActive(false);
        public void Ecrire(string texte)
        {
            if (contenu.text == texte) return;
            contenu.text = texte;
            contenu.rectTransform.sizeDelta = new Vector2(692, Mathf.Max(648, contenu.preferredHeight));
        }
    }
}
