using System;
using System.Globalization;
using System.Linq;
using Forge.Pont;
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
        Slider curseur;
        Text legende;
        string cible, erreur;
        bool grenier, disponible;
        double prochaine;
        public string MessageAffiche => message == null ? "" : message.text;

        public void Initialiser(Transform parent, Func<string> maison, LectureDossier lecture, OrdreConfirme ordre)
        {
            this.maison = maison; this.lecture = lecture; Ordre = ordre;
            racine = new GameObject("Commandes de maison", typeof(RectTransform)).transform;
            racine.SetParent(parent, false);
            var rect = (RectTransform)racine;
            rect.anchorMin = rect.anchorMax = rect.pivot = new Vector2(0, 1);
            rect.anchoredPosition = new Vector2(24, -200);
            comptes = SocleInterface.Texte(racine, "Lecture des réserves…", 0, 0, 536);
            comptes.rectTransform.sizeDelta = new Vector2(536, 56);
            part = Bouton("Prélèvement", 0, 60, () => Ouvrir(false), "Prépare un nouveau prélèvement sur vos lieux, en pour cent, sans l'envoyer.");
            secours = Bouton("Ouvrir le grenier", 276, 60, () => Ouvrir(true), "Prépare l'ouverture de votre grenier, en kilos de grain, sans l'envoyer.");
            curseur = CurseurDePart(racine);
            legende = SocleInterface.Texte(racine, "0 %", 420, 108, 116);
            legende.alignment = TextAnchor.MiddleLeft;
            legende.rectTransform.sizeDelta = new Vector2(116, 32);
            curseur.onValueChanged.AddListener(Regler);
            var champ = new GameObject("Quantité", typeof(RectTransform)).GetComponent<RectTransform>();
            champ.SetParent(racine, false);
            champ.anchorMin = champ.anchorMax = champ.pivot = new Vector2(0, 1);
            champ.anchoredPosition = new Vector2(0, -144);
            champ.gameObject.AddComponent<Image>().color = Color.white;
            saisie = champ.gameObject.AddComponent<InputField>();
            saisie.textComponent = SocleInterface.Texte(champ, "", 8, 10, 244);
            saisie.textComponent.supportRichText = false;
            saisie.characterLimit = 18;
            saisie.navigation = new Navigation { mode = Navigation.Mode.Automatic };
            champ.sizeDelta = new Vector2(260, 44);
            preparer = Bouton("Préparer", 276, 144, Preparer, "Relit la valeur saisie et prépare l'ordre, sans l'envoyer.");
            message = SocleInterface.Texte(racine, "", 0, 192, 536);
            message.rectTransform.sizeDelta = new Vector2(536, 88);
            confirmer = Bouton("Confirmer l’ordre", 276, 284, () => { if (disponible) _ = Ordre.Confirmer(); }, "Envoie l'ordre préparé au monde ; il l'applique au jour suivant.");
            MatieresCabinet.Engagement(confirmer);
            retour = Bouton("Annuler / Retour", 0, 284, () => { Ordre.Recommencer(); cible = null; erreur = null; }, "Abandonne l'ordre en préparation ; rien n'est envoyé.");
            foreach (var texte in racine.GetComponentsInChildren<Text>()) texte.supportRichText = false;
            Afficher();
        }
        Button Bouton(string nom, float x, float y, Action action, string phrase)
        {
            var b = SocleInterface.Commande(racine, nom, x, y, action, phrase: phrase);
            b.GetComponent<RectTransform>().sizeDelta = new Vector2(260, 44);
            b.GetComponentInChildren<Text>().rectTransform.sizeDelta = new Vector2(260, 44);
            return b;
        }
        void Ouvrir(bool ouvrirGrenier)
        {
            if (!disponible || Ordre.Brouillon != null || Ordre.EnCours || Ordre.Recu != null) return;
            cible = maison(); grenier = ouvrirGrenier; erreur = null;
            if (ouvrirGrenier) saisie.text = "";
            else { bool lue = PartEntiere(out int pourcent); curseur.SetValueWithoutNotify(pourcent); legende.text = pourcent.ToString(CultureInfo.InvariantCulture) + " %"; saisie.text = lue ? pourcent.ToString(CultureInfo.InvariantCulture) : ""; }
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
            bool brouillon = Ordre.Brouillon != null, recu = Ordre.Recu != null, formulaire = cible != null, partOuverte = formulaire && !grenier;
            part.interactable = secours.interactable = disponible && !brouillon && !recu;
            curseur.gameObject.SetActive(partOuverte); legende.gameObject.SetActive(partOuverte);
            curseur.interactable = partOuverte && disponible && cible == id && !brouillon && !recu && !Ordre.EnCours;
            saisie.gameObject.SetActive(formulaire && !brouillon);
            preparer.gameObject.SetActive(formulaire && !brouillon);
            preparer.interactable = disponible && cible == id;
            confirmer.gameObject.SetActive(brouillon && !recu);
            confirmer.interactable = disponible && cible == id && !Ordre.EnCours;
            retour.gameObject.SetActive(formulaire || recu);
            retour.interactable = !Ordre.EnCours;
            message.text = erreur ?? (brouillon ? Ordre.Resume : formulaire ? (grenier ? "Quantité de grain en kg." : "Part prélevée en %." ) : "Préparez un ordre, puis confirmez son envoi.");
            if (Ordre.EnCours) message.text = "Envoi en cours. Attendez le reçu.";
            if (recu) message.text = (string.IsNullOrEmpty(Ordre.Resume) ? "" : Ordre.Resume + "\n") + TexteDuRecu(Ordre.Recu);
        }
        static string TexteDuRecu(RecuIntention recu) => recu.Acceptee ? "Ordre reçu. Le monde l'applique au tick suivant (après le tick " + recu.AppliqueeAuTick.Value.ToString(CultureInfo.InvariantCulture) + ")."
            : recu.Presente ? "Refus : " + recu.Erreur : "Envoi non confirmé : " + recu.Absence + "\nVérifiez le monde avant tout nouvel ordre.";
        bool PartEntiere(out int pourcent)
        {
            pourcent = 0; var doc = lecture == null ? null : lecture.Document;
            if (doc == null || !(DocumentDuMonde.Valeur(doc.Champs, "part") is double nombre) || double.IsNaN(nombre) || double.IsInfinity(nombre)) return false;
            pourcent = (int)Math.Round(nombre * 100.0, MidpointRounding.AwayFromZero); if (pourcent < 0) pourcent = 0; if (pourcent > 60) pourcent = 60; return true;
        }
        void Regler(float valeur)
        {
            int n = Mathf.RoundToInt(valeur); if (legende != null) legende.text = n.ToString(CultureInfo.InvariantCulture) + " %";
            if (saisie != null && cible != null && !grenier && Ordre.Brouillon == null && Ordre.Recu == null && !Ordre.EnCours) saisie.text = n.ToString(CultureInfo.InvariantCulture);
        }
        static Slider CurseurDePart(Transform parent)
        {
            var piste = new GameObject("Curseur de part", typeof(RectTransform), typeof(Image), typeof(Slider));
            var rect = piste.GetComponent<RectTransform>(); rect.SetParent(parent, false);
            rect.anchorMin = rect.anchorMax = rect.pivot = new Vector2(0, 1); rect.anchoredPosition = new Vector2(0, -108); rect.sizeDelta = new Vector2(400, 32);
            piste.GetComponent<Image>().color = SocleInterface.Couleur("secondaire");
            var niveau = new GameObject("Niveau", typeof(RectTransform), typeof(Image)).GetComponent<RectTransform>();
            niveau.SetParent(rect, false); niveau.anchorMin = Vector2.zero; niveau.anchorMax = Vector2.one; niveau.offsetMin = niveau.offsetMax = Vector2.zero;
            var remplissage = niveau.GetComponent<Image>(); remplissage.color = SocleInterface.Couleur("accent"); remplissage.raycastTarget = false;
            var poignee = new GameObject("Poignée", typeof(RectTransform), typeof(Image)).GetComponent<RectTransform>();
            poignee.SetParent(rect, false); poignee.sizeDelta = new Vector2(24, 0);
            var image = poignee.GetComponent<Image>(); image.color = SocleInterface.Couleur("papier"); image.raycastTarget = true;
            var slider = piste.GetComponent<Slider>(); slider.fillRect = niveau; slider.handleRect = poignee; slider.targetGraphic = image;
            slider.direction = Slider.Direction.LeftToRight; slider.minValue = 0; slider.maxValue = 60; slider.wholeNumbers = true;
            var teinte = slider.colors; teinte.disabledColor = Color.white; teinte.fadeDuration = 0; slider.colors = teinte; return slider;
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
