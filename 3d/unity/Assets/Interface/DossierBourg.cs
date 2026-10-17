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
        DocumentDuMonde affiche;
        long cellule = -1;
        double prochaine;
        public void Initialiser(Transform toile, Transform territoire, int port, Func<CelluleDeCarte> selection)
        {
            this.selection = selection; lecture = LectureDossier.Locale(port);
            cadre = SocleInterface.Panneau(toile, "Plan du bourg", 24, 124, 1238, 732);
            ouvrir = Bouton(territoire, "Plan du bourg", 372, 20, 188, () =>
            { cadre.SetAsLastSibling(); cadre.gameObject.SetActive(true); });
            Bouton(cadre, "Revenir à la carte", 1000, 20, 214, () => cadre.gameObject.SetActive(false));
            etat = SocleInterface.Texte(cadre, "Sélectionnez un territoire sur la carte.", 24, 88, 1190);
            var surface = new GameObject("Tracé du bourg", typeof(RectTransform), typeof(DessinBourg));
            var rect = surface.GetComponent<RectTransform>(); rect.SetParent(cadre, false);
            rect.anchorMin = rect.anchorMax = rect.pivot = new Vector2(0, 1);
            rect.anchoredPosition = new Vector2(24, -136); rect.sizeDelta = new Vector2(1190, 510);
            dessin = surface.GetComponent<DessinBourg>(); dessin.raycastTarget = false;
            legende = SocleInterface.Texte(cadre, "", 24, 660, 1190);
            gameObject.AddComponent<DossierChantiers>().Initialiser(toile, cadre, port, selection);
            cadre.gameObject.SetActive(false);
        }
        static Button Bouton(Transform parent, string nom, float x, float y, float largeur, Action action)
        {
            var bouton = SocleInterface.Commande(parent, nom, x, y, action);
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
                if (lecture.Document == null) { etat.text = "Lecture du plan du territoire " + cellule + "…"; return; }
                if (affiche == lecture.Document) return;
                var plan = new PlanBourg(lecture.Document, cellule);
                dessin.Afficher(plan); affiche = lecture.Document;
                etat.text = "Territoire " + cellule + " · tick " + plan.Tick + " · Nord en haut · Consultation du plan";
                legende.text = "Bleu : rues · Encre : maisons · Or : place et parcelles · Rouge : chantiers\nLargeur du cadre : "
                    + (1190 / dessin.PixelsParMetre).ToString("0.#", CultureInfo.GetCultureInfo("fr-FR")) + " m · Aucun outil de construction actif";
            }
            catch (Exception e) { dessin.Afficher(null); affiche = null; legende.text = ""; etat.text = "Plan indisponible : " + e.Message; }
        }
        void OnDestroy() => lecture?.Vider();
    }
}
