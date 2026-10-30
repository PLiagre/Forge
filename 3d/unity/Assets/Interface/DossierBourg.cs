using System;
using System.Globalization;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface
{
    public sealed class DossierBourg : MonoBehaviour
    {
        RectTransform cadre;
        DessinBourg dessin;
        Text etat, legende;
        Button ouvrir;
        Func<CelluleDeCarte> selection;
        LectureDossier lecture;
        NomsDesTerres noms;
        DocumentDuMonde affiche;
        long cellule = -1;
        double prochaine;
        public long Cellule => cellule;
        public DocumentDuMonde Document => affiche;
        public Text Etat => etat;
        public void Initialiser(Transform toile, Transform territoire, int port, Func<CelluleDeCarte> selection)
        {
            this.selection = selection; lecture = LectureDossier.Locale(port); noms = NomsDesTerres.Local(port);
            cadre = SocleInterface.Panneau(toile, "Plan du bourg", 24, 124, 1238, 732);
            ouvrir = Bouton(territoire, "Plan du bourg", 372, 20, 188, () =>
            { cadre.SetAsLastSibling(); cadre.gameObject.SetActive(true); }, "Ouvre le plan du bourg de la terre conservée.");
            Bouton(cadre, "Revenir à la carte", 1000, 20, 214, () => cadre.gameObject.SetActive(false), "Ferme le plan du bourg et revient à la carte.");
            etat = SocleInterface.Texte(cadre, "Sélectionnez un territoire sur la carte.", 24, 88, 1190);
            var surface = new GameObject("Tracé du bourg", typeof(RectTransform), typeof(DessinBourg));
            var rect = surface.GetComponent<RectTransform>(); rect.SetParent(cadre, false);
            rect.anchorMin = rect.anchorMax = rect.pivot = new Vector2(0, 1);
            rect.anchoredPosition = new Vector2(24, -136); rect.sizeDelta = new Vector2(1190, 510);
            dessin = surface.GetComponent<DessinBourg>(); dessin.raycastTarget = false;
            legende = SocleInterface.Texte(cadre, "", 24, 660, 1190);
            gameObject.AddComponent<DossierChantiers>().Initialiser(toile, cadre, port, selection, Bourg);
            cadre.gameObject.AddComponent<OutilRue>().Initialiser(this, dessin, legende, port);
            cadre.gameObject.SetActive(false);
        }
        static Button Bouton(Transform parent, string nom, float x, float y, float largeur, Action action, string phrase)
        {
            var bouton = SocleInterface.Commande(parent, nom, x, y, action, phrase: phrase);
            bouton.GetComponent<RectTransform>().sizeDelta = new Vector2(largeur, 44);
            bouton.GetComponentInChildren<Text>().rectTransform.sizeDelta = new Vector2(largeur, 44);
            return bouton;
        }
        void LateUpdate()
        {
            if (cadre == null) return;
            var choisie = selection(); ouvrir.interactable = choisie != null;
            if (!cadre.gameObject.activeSelf || choisie == null) return;
            if (cellule != choisie.CellId)
            { cellule = choisie.CellId; lecture.Vider(); affiche = null; dessin.Afficher(null); legende.text = ""; prochaine = 0; }
            if (!lecture.EnCours && Time.realtimeSinceStartupAsDouble >= prochaine)
            { prochaine = Time.realtimeSinceStartupAsDouble + 2; _ = lecture.Actualiser("/plan?cell=" + cellule); }
            try
            {
                if (lecture.Erreur != null) throw new ArgumentException(lecture.Erreur);
                if (lecture.Document == null) { etat.text = "Lecture du plan du bourg…"; return; }
                if (affiche != lecture.Document)
                {
                    dessin.Afficher(new PlanBourg(lecture.Document, cellule)); affiche = lecture.Document;
                    legende.text = "Bleu : rues · Encre : maisons · Or : place et parcelles · Rouge : chantiers\nLargeur du cadre : "
                        + (1190 / dessin.PixelsParMetre).ToString("0.#", CultureInfo.GetCultureInfo("fr-FR")) + " m · Consultation ; tracé sur vos terres seulement";
                }
                etat.text = Entete(Bourg(cellule), lecture.Document) + " · Nord en haut · Consultation du plan"; // réécrit à chaque image : le nom lu après le plan remplace son absence
            }
            catch (Exception e) { dessin.Afficher(null); affiche = null; legende.text = ""; etat.text = "Plan indisponible : " + TexteDuMonde.Absence(e.Message, cellule.ToString(CultureInfo.InvariantCulture)); }
        }
        public static string Entete(string bourg, DocumentDuMonde doc)
        {
            if (doc.Annee == null) throw new ArgumentException("Date non transmise");
            return bourg + " · " + TexteDuMonde.Date(new DateDuMonde(doc.Annee.Value, doc.JourDeLAnnee.Value));
        }
        public static string NomDuBourg(NomsDesTerres noms, long cell, double maintenant) => noms.Bourg(cell, maintenant)
            ?? "Bourg sans nom (" + TexteDuMonde.Absence(noms.Raison(cell, 0), cell.ToString(CultureInfo.InvariantCulture)) + ")";
        public string Bourg(long cellule) => NomDuBourg(noms, cellule, Time.realtimeSinceStartupAsDouble);
        void OnDestroy() => lecture?.Vider();
    }
}
