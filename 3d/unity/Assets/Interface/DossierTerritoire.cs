using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface
{
    public sealed class DossierTerritoire : MonoBehaviour
    {
        Text texte;
        Func<CelluleDeCarte> selection;
        LectureDossier lecture;
        ScrollRect defilement;
        long? cellule;
        double prochaineLecture;
        public DocumentDuMonde Document => lecture?.Document;
        public void Initialiser(Text contenu, int port, Func<CelluleDeCarte> selection)
        {
            texte = contenu; this.selection = selection; lecture = LectureDossier.Locale(port);
            var ancien = texte.rectTransform;
            var cadre = new GameObject("Lecture du territoire", typeof(RectTransform), typeof(Image), typeof(RectMask2D), typeof(ScrollRect)).GetComponent<RectTransform>();
            cadre.SetParent(ancien.parent, false);
            cadre.anchorMin = ancien.anchorMin; cadre.anchorMax = ancien.anchorMax; cadre.pivot = ancien.pivot;
            cadre.anchoredPosition = ancien.anchoredPosition; cadre.sizeDelta = ancien.sizeDelta;
            cadre.GetComponent<Image>().color = Color.clear;
            ancien.SetParent(cadre, false);
            ancien.anchorMin = new Vector2(0, 1); ancien.anchorMax = Vector2.one; ancien.pivot = new Vector2(0, 1);
            ancien.anchoredPosition = Vector2.zero; ancien.sizeDelta = new Vector2(0, cadre.sizeDelta.y);
            defilement = cadre.GetComponent<ScrollRect>();
            defilement.viewport = cadre; defilement.content = ancien;
            defilement.horizontal = false; defilement.inertia = false; defilement.scrollSensitivity = 24;
            defilement.movementType = ScrollRect.MovementType.Clamped;
            texte.supportRichText = false;
        }
        void OnDestroy() => lecture?.Vider();
        void LateUpdate()
        {
            var choisie = selection?.Invoke();
            if (choisie == null || lecture == null) return;
            bool change = cellule != choisie.CellId;
            if (change) { cellule = choisie.CellId; defilement.verticalNormalizedPosition = 1; }
            if (change || !lecture.EnCours && Time.realtimeSinceStartupAsDouble >= prochaineLecture)
            {
                prochaineLecture = Time.realtimeSinceStartupAsDouble + 2;
                _ = lecture.Actualiser("/lieu?cell=" + choisie.CellId);
            }
            try
            {
                texte.text = lecture.Erreur != null ? "Lecture indisponible : " + lecture.Erreur
                    : lecture.Document == null ? "Cellule " + cellule + "\nLecture des lieux et des réserves…"
                    : Decrire(lecture.Document, choisie.CellId);
            }
            catch (ArgumentException erreur) { texte.text = "Dossier incomplet : " + erreur.Message; }
            texte.rectTransform.sizeDelta = new Vector2(0, Mathf.Max(defilement.viewport.rect.height, texte.preferredHeight + 16));
        }
        static string Nombre(double n) => n.ToString("0.##", CultureInfo.GetCultureInfo("fr-FR"));
        public static string Decrire(DocumentDuMonde document, long cellule)
        {
            var racine = document.Champs;
            if (DocumentDuMonde.Entier(racine, "cell_id") != cellule) throw new ArgumentException("Territoire différent de la sélection");
            var lieux = DocumentDuMonde.Tableau(racine, "lieux");
            if (lieux.Count == 0) throw new ArgumentException("Aucun lieu transmis");
            var texte = new StringBuilder("Cellule " + cellule + " · tick " + document.Tick + "\n");
            texte.Append(DocumentDuMonde.Entier(racine, "population")).Append(" habitants dans le territoire\nMolette : parcourir les lieux\n");
            var rangs = new HashSet<long>();
            foreach (var brut in lieux)
            {
                var lieu = brut as Dictionary<string, object> ?? throw new ArgumentException("Lieu illisible");
                long rang = DocumentDuMonde.Entier(lieu, "rang");
                if (!rangs.Add(rang)) throw new ArgumentException("Rang de lieu répété");
                string nom = DocumentDuMonde.Valeur(lieu, "nom") as string ?? "Nom du lieu non transmis";
                texte.Append("\n").Append(nom).Append(" · rang ").Append(rang).Append('\n');
                texte.Append(DocumentDuMonde.Entier(lieu, "population")).Append(" habitants · ");
                texte.Append(Nombre(DocumentDuMonde.Nombre(lieu, "surface_km2"))).Append(" km²\n");
                texte.Append(Maitre(racine, lieu)).Append('\n');
                var stocks = DocumentDuMonde.Objet(lieu, "stocks");
                if (stocks.Count == 0) texte.Append("Réserves : panier vide\n");
                foreach (var cle in stocks.Keys.OrderBy(c => c))
                    texte.Append(cle).Append(" : ").Append(Nombre(DocumentDuMonde.Nombre(stocks, cle))).Append(" kg\n");
                var flux = DocumentDuMonde.Valeur(lieu, "flux_30j") as Dictionary<string, object>;
                if (flux == null) texte.Append("Flux non transmis\n");
                else
                {
                    texte.Append("Sur 30 jours : ").Append(Nombre(DocumentDuMonde.Nombre(flux, "preleve_kg"))).Append(" kg prélevés\n");
                    texte.Append(DocumentDuMonde.Entier(flux, "partis_personnes")).Append(" départs · ")
                        .Append(DocumentDuMonde.Entier(flux, "arrives_personnes")).Append(" arrivées\n");
                }
            }
            return texte.ToString();
        }
        static string Maitre(Dictionary<string, object> racine, Dictionary<string, object> lieu)
        {
            var maitre = DocumentDuMonde.Valeur(lieu, "maitre");
            if (maitre == null) return "Sans maître";
            var maisons = DocumentDuMonde.Objet(DocumentDuMonde.Objet(racine, "noms"), "maisons");
            if (!(maitre is string id) || !maisons.TryGetValue(id, out var fiche)
                || !(fiche is Dictionary<string, object> maison)) return "Nom du maître non transmis";
            return "Maison : " + (DocumentDuMonde.Valeur(maison, "nom") as string ?? "nom non transmis");
        }
    }
}
