using System;
using System.Linq;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem;
using UnityEngine.UI;

namespace Forge.Interface
{
    public sealed class MenuCabinet : MonoBehaviour
    {
        RectTransform panneau;
        Button retour;
        GameObject precedent;
        Transform toile;
        public bool Ouvert => panneau != null && panneau.gameObject.activeSelf;
        public void Initialiser(Transform toile)
        {
            if (panneau != null) return;
            this.toile = toile;
            var ouvrir = SocleInterface.Commande(toile, "Menu", 330, 20, Basculer);
            ouvrir.GetComponent<RectTransform>().sizeDelta = new Vector2(120, 44);
            ouvrir.GetComponentInChildren<Text>().rectTransform.sizeDelta = new Vector2(120, 44);
            panneau = SocleInterface.Panneau(toile, "Menu du cabinet", 24, 124, 740, 760);
            retour = SocleInterface.Commande(panneau, "Revenir au jeu", 24, 88, Fermer);
            var aide = SocleInterface.Texte(panneau,
                "PARCOURIR\nGlisser avec le bouton du milieu : déplacer la carte.\nMolette sur la carte : zoomer.\nClic droit sur une terre : conserver son dossier.\nMolette dans un dossier : faire défiler son contenu.\n\nDÉCIDER\nChoisissez une maison, puis confirmez votre choix.\nUn ordre reçu attend le prochain tick du monde.\nPause et Reprendre restent dans le bandeau.\n\nCLAVIER\nTabulation ou flèches : parcourir les commandes.\nEntrée : activer la commande sélectionnée.\nÉchap : ouvrir ou fermer ce menu.", 24, 156, 692);
            aide.rectTransform.sizeDelta = new Vector2(692, 370);
            var libelle = SocleInterface.Texte(panneau, "Volume du jeu", 24, 544, 692);
            var piste = new GameObject("Volume", typeof(RectTransform), typeof(Image), typeof(Slider));
            var rect = piste.GetComponent<RectTransform>(); rect.SetParent(panneau, false);
            rect.anchorMin = rect.anchorMax = rect.pivot = new Vector2(0, 1);
            rect.anchoredPosition = new Vector2(24, -584); rect.sizeDelta = new Vector2(692, 44);
            piste.GetComponent<Image>().color = SocleInterface.Couleur("secondaire");
            var curseur = new GameObject("Curseur", typeof(RectTransform), typeof(Image)).GetComponent<RectTransform>();
            curseur.SetParent(rect, false); curseur.sizeDelta = new Vector2(16, 44);
            curseur.GetComponent<Image>().color = SocleInterface.Couleur("papier");
            var volume = piste.GetComponent<Slider>(); volume.handleRect = curseur;
            volume.targetGraphic = curseur.GetComponent<Image>(); volume.minValue = 0; volume.maxValue = 1;
            volume.SetValueWithoutNotify(AudioListener.volume);
            volume.onValueChanged.AddListener(valeur =>
            {
                AudioListener.volume = valeur;
                libelle.text = valeur == 0 ? "Volume du jeu : silence" : "Volume du jeu : " + Mathf.RoundToInt(valeur * 100) + " %";
            });
            var note = SocleInterface.Texte(panneau, "Le menu conserve le rythme du monde. Utilisez Pause si nécessaire.\nLes dossiers et votre sélection restent ouverts au retour.", 24, 660, 692);
            note.rectTransform.sizeDelta = new Vector2(692, 60);
            foreach (var texte in panneau.GetComponentsInChildren<Text>()) texte.supportRichText = false;
            panneau.gameObject.SetActive(false);
        }
        void Update()
        {
            if (Keyboard.current?.tabKey.wasPressedThisFrame == true)
                Parcourir(Keyboard.current.leftShiftKey.isPressed || Keyboard.current.rightShiftKey.isPressed);
            if (Keyboard.current?.escapeKey.wasPressedThisFrame != true) return;
            var selection = EventSystem.current?.currentSelectedGameObject;
            if (selection != null && selection.TryGetComponent<InputField>(out var champ) && champ.isFocused) return;
            Basculer();
        }
        public void Parcourir(bool inverse)
        {
            if (EventSystem.current == null) return;
            var choix = (Ouvert ? panneau : toile).GetComponentsInChildren<Selectable>()
                .Where(s => s.IsActive() && s.IsInteractable()).ToArray();
            if (choix.Length == 0) return;
            int actuel = Array.FindIndex(choix, s => s.gameObject == EventSystem.current.currentSelectedGameObject);
            int suivant = actuel < 0 ? (inverse ? choix.Length - 1 : 0) : (actuel + (inverse ? -1 : 1) + choix.Length) % choix.Length;
            EventSystem.current.SetSelectedGameObject(choix[suivant].gameObject);
        }
        void Basculer() { if (Ouvert) Fermer(); else Ouvrir(); }
        public void Ouvrir()
        {
            if (Ouvert) return;
            precedent = EventSystem.current?.currentSelectedGameObject;
            panneau.SetAsLastSibling(); panneau.gameObject.SetActive(true);
            EventSystem.current?.SetSelectedGameObject(retour.gameObject);
        }
        public void Fermer()
        {
            if (!Ouvert) return;
            panneau.gameObject.SetActive(false);
            if (precedent != null && precedent.activeInHierarchy) EventSystem.current?.SetSelectedGameObject(precedent);
        }
    }
}
