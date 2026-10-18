using System;
using System.Globalization;
using System.Linq;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface
{
    public sealed class CommandesMaison : MonoBehaviour
    {
        Func<string> maison;
        LectureDossier lecture;
        public OrdreConfirme Ordre { get; private set; }
        Transform racine;
        Text comptes, message;
        InputField saisie;
        Button part, secours, preparer, confirmer, retour;
        string cible, erreur;
        bool grenier, disponible;
        double prochaine;

        public void Initialiser(Transform parent, Func<string> maison, LectureDossier lecture, OrdreConfirme ordre)
        {
            this.maison = maison; this.lecture = lecture; Ordre = ordre;
            racine = new GameObject("Commandes de maison", typeof(RectTransform)).transform;
            racine.SetParent(parent, false);
            var rect = (RectTransform)racine;
            rect.anchorMin = rect.anchorMax = rect.pivot = new Vector2(0, 1);
            rect.anchoredPosition = new Vector2(24, -200);
            comptes = SocleInterface.Texte(racine, "Lecture des réserves…", 0, 0, 536);
            comptes.rectTransform.sizeDelta = new Vector2(536, 72);
            part = Bouton("Prélèvement", 0, 80, () => Ouvrir(false));
            secours = Bouton("Secours du grenier", 276, 80, () => Ouvrir(true));
            var champ = new GameObject("Quantité", typeof(RectTransform)).GetComponent<RectTransform>();
            champ.SetParent(racine, false);
            champ.anchorMin = champ.anchorMax = champ.pivot = new Vector2(0, 1);
            champ.anchoredPosition = new Vector2(0, -132);
            champ.gameObject.AddComponent<Image>().color = Color.white;
            saisie = champ.gameObject.AddComponent<InputField>();
            saisie.textComponent = SocleInterface.Texte(champ, "", 8, 10, 244);
            saisie.textComponent.supportRichText = false;
            saisie.characterLimit = 18;
            saisie.navigation = new Navigation { mode = Navigation.Mode.Automatic };
            champ.sizeDelta = new Vector2(260, 44);
            preparer = Bouton("Préparer", 276, 132, Preparer);
            message = SocleInterface.Texte(racine, "", 0, 184, 536);
            message.rectTransform.sizeDelta = new Vector2(536, 80);
            confirmer = Bouton("Confirmer l’ordre", 276, 268, () => { if (disponible) _ = Ordre.Confirmer(); });
            MatieresCabinet.Engagement(confirmer);
            retour = Bouton("Annuler / Retour", 0, 268, () => { Ordre.Recommencer(); cible = null; erreur = null; });
            foreach (var texte in racine.GetComponentsInChildren<Text>()) texte.supportRichText = false;
            Afficher();
        }
        Button Bouton(string nom, float x, float y, Action action)
        {
            var b = SocleInterface.Commande(racine, nom, x, y, action);
            b.GetComponent<RectTransform>().sizeDelta = new Vector2(260, 44);
            b.GetComponentInChildren<Text>().rectTransform.sizeDelta = new Vector2(260, 44);
            return b;
        }
        void Ouvrir(bool ouvrirGrenier)
        {
            if (!disponible || Ordre.Brouillon != null || Ordre.EnCours || Ordre.Recu != null) return;
            cible = maison(); grenier = ouvrirGrenier; saisie.text = ""; erreur = null;
            saisie.ActivateInputField();
        }
        void Preparer()
        {
            if (!disponible || cible == null || cible != maison()) return;
            try
            {
                string json = grenier ? OrdresMaison.Grenier(cible, saisie.text) : OrdresMaison.Part(cible, saisie.text);
                Ordre.Preparer(json, grenier ? "Ouvrir le grenier : " + saisie.text + " kg." : "Fixer le prélèvement à " + saisie.text + " %." );
                erreur = null;
            }
            catch (Exception e) { erreur = e.Message; }
        }
        void LateUpdate()
        {
            if (racine == null) return;
            string id = maison();
            if (id != null && !lecture.EnCours && Time.realtimeSinceStartupAsDouble >= prochaine)
            {
                prochaine = Time.realtimeSinceStartupAsDouble + 2;
                _ = lecture.Actualiser("/maison?id=" + Uri.EscapeDataString(id));
            }
            Afficher();
        }
        public void Afficher()
        {
            string id = maison(); racine.gameObject.SetActive(id != null);
            disponible = false;
            try
            {
                if (lecture.Erreur != null) throw new ArgumentException(lecture.Erreur);
                var doc = lecture.Document;
                if (doc == null || DocumentDuMonde.Texte(doc.Champs, "id") != id) throw new ArgumentException("Réserves en attente du monde");
                comptes.text = Decrire(doc);
                disponible = true;
            }
            catch (Exception e) { comptes.text = e.Message; }
            bool brouillon = Ordre.Brouillon != null, recu = Ordre.Recu != null, formulaire = cible != null;
            part.interactable = secours.interactable = disponible && !brouillon && !recu;
            saisie.gameObject.SetActive(formulaire && !brouillon);
            preparer.gameObject.SetActive(formulaire && !brouillon);
            preparer.interactable = disponible && cible == id;
            confirmer.gameObject.SetActive(brouillon && !recu);
            confirmer.interactable = disponible && cible == id && !Ordre.EnCours;
            retour.gameObject.SetActive(formulaire || recu);
            retour.interactable = !Ordre.EnCours;
            message.text = erreur ?? (brouillon ? Ordre.Resume : formulaire ? (grenier ? "Quantité de grain en kg." : "Part prélevée en %." ) : "Préparez un ordre, puis confirmez son envoi.");
            if (Ordre.EnCours) message.text = "Envoi en cours. Attendez le reçu.";
            if (recu) message.text = Ordre.Recu.Acceptee ? "Ordre reçu. Reprenez le temps pour son application.\nLes réserves ci-dessus restent celles du monde."
                : Ordre.Recu.Presente ? "Refus : " + Ordre.Recu.Erreur
                : "Envoi non confirmé : " + Ordre.Recu.Absence + "\nVérifiez le monde avant tout nouvel ordre.";
        }
        public static string Decrire(DocumentDuMonde doc)
        {
            var d = doc.Champs;
            var absents = DocumentDuMonde.Objet(d, "absents");
            string part = DocumentDuMonde.Valeur(d, "part") == null ? DocumentDuMonde.Texte(absents, "part")
                : (DocumentDuMonde.Nombre(d, "part") * 100).ToString("0.##", CultureInfo.GetCultureInfo("fr-FR")) + " %";
            string reserves = DocumentDuMonde.Valeur(d, "grenier") == null ? DocumentDuMonde.Texte(absents, "grenier")
                : string.Join(" · ", DocumentDuMonde.Objet(d, "grenier").OrderBy(p => p.Key).Select(p => p.Key + " : " + DocumentDuMonde.Nombre(DocumentDuMonde.Objet(d, "grenier"), p.Key).ToString("0.##", CultureInfo.GetCultureInfo("fr-FR")) + " kg"));
            return "Prélèvement : " + part + " · tick " + doc.Tick + "\nGrenier : " + (reserves.Length == 0 ? "vide" : reserves);
        }
        void OnDestroy() => lecture?.Vider();
    }
}
