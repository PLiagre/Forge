using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface
{
    public sealed class DossierChantiers : MonoBehaviour
    {
        Feuillet feuillet;
        LectureDossier lecture;
        Func<CelluleDeCarte> selection;
        Button bouton;
        long cellule = -1;
        double prochaine;

        public void Initialiser(Transform toile, Transform plan, int port, Func<CelluleDeCarte> selection)
        {
            this.selection = selection;
            lecture = LectureDossier.Locale(port);
            feuillet = gameObject.AddComponent<Feuillet>();
            feuillet.Initialiser(toile, "Les chantiers du bourg");
            bouton = SocleInterface.Commande(plan, "Chantiers", 420, 20, () =>
            {
                if (feuillet.Ouvert) feuillet.Fermer(); else feuillet.Ouvrir();
            }, phrase: "Ouvre ou ferme les chantiers du bourg et ce qu'ils ont coûté.");
            bouton.GetComponent<RectTransform>().sizeDelta = new Vector2(200, 44);
            bouton.GetComponentInChildren<Text>().rectTransform.sizeDelta = new Vector2(200, 44);
        }

        void LateUpdate()
        {
            if (feuillet == null) return;
            var choisie = selection();
            bouton.interactable = choisie != null;
            if (!feuillet.Ouvert) return;
            if (choisie == null) { feuillet.Ecrire("Conservez un territoire sur la carte."); return; }
            if (cellule != choisie.CellId)
            {
                cellule = choisie.CellId;
                lecture.Vider(); prochaine = 0;
            }
            if (!lecture.EnCours && Time.realtimeSinceStartupAsDouble >= prochaine)
            {
                prochaine = Time.realtimeSinceStartupAsDouble + 2;
                _ = lecture.Actualiser("/plan?cell=" + cellule);
            }
            try
            {
                if (lecture.Erreur != null) throw new ArgumentException(lecture.Erreur);
                feuillet.Ecrire(lecture.Document == null ? "Lecture des chantiers du territoire " + cellule + "…"
                    : Decrire(lecture.Document, cellule));
            }
            catch (Exception e) { feuillet.Ecrire("Chantiers indisponibles : " + e.Message); }
        }

        static Dictionary<string, object> Objet(object brut) => brut as Dictionary<string, object>
            ?? throw new ArgumentException("Ouvrage ou relevé absent");

        public static string Decrire(DocumentDuMonde document, long cellule)
        {
            if (DocumentDuMonde.Entier(document.Champs, "cell_id") != cellule)
                throw new ArgumentException("Plan reçu pour un autre territoire");
            var texte = new StringBuilder("Territoire " + cellule + " · tick " + document.Tick + "\n");
            texte.AppendLine("Une journée de travail correspond au travail d’une personne pendant un jour.");
            texte.AppendLine("Coût en pièces : non renseigné · Date de fin : non renseignée");
            bool journalPresent = document.Champs.ContainsKey("chantiers_du_jour");
            var journal = new Dictionary<string, Dictionary<string, object>>();
            if (journalPresent)
                foreach (var brut in DocumentDuMonde.Tableau(document.Champs, "chantiers_du_jour"))
                {
                    var jour = Objet(brut);
                    string cle = DocumentDuMonde.Texte(jour, "nature") + "/" + DocumentDuMonde.Entier(jour, "identifiant");
                    if (journal.ContainsKey(cle)) throw new ArgumentException("Relevé quotidien dupliqué");
                    journal.Add(cle, jour);
                }
            int nombre = 0;
            foreach (string nature in new[] { "rue", "parcelle", "batiment" })
            {
                var vus = new HashSet<long>();
                foreach (var brut in DocumentDuMonde.Tableau(document.Champs, nature + "s"))
                {
                    var ouvrage = Objet(brut);
                    long id = DocumentDuMonde.Entier(ouvrage, "identifiant");
                    long fourni = DocumentDuMonde.Entier(ouvrage, "travail_fourni");
                    long requis = DocumentDuMonde.Entier(ouvrage, "travail_requis");
                    long foyers = DocumentDuMonde.Entier(ouvrage, "foyers");
                    if (!vus.Add(id)) throw new ArgumentException("Ouvrage dupliqué");
                    if (!(DocumentDuMonde.Valeur(ouvrage, "en_chantier") is bool actif)
                        || fourni > requis || actif != (fourni < requis) || (actif && foyers == 0))
                        throw new ArgumentException("État du chantier incohérent");
                    string nom = nature == "rue" ? "Rue" : nature == "parcelle" ? "Parcelle" : "Bâtiment";
                    texte.AppendLine("\n" + nom + " " + id + " · " + (actif ? "En chantier" : "Achevé"));
                    texte.AppendLine(fourni + " / " + requis + " journées de travail · " + foyers
                        + (foyers == 1 ? " foyer affecté" : " foyers affectés"));
                    string cle = nature + "/" + id;
                    if (journal.TryGetValue(cle, out var jour))
                    {
                        texte.AppendLine(DecrireJour(jour));
                        journal.Remove(cle);
                    }
                    else texte.AppendLine(journalPresent ? "Aucun relevé du jour pour cet ouvrage."
                        : "Relevé du jour : non renseigné");
                    nombre++;
                }
            }
            if (journal.Count != 0) throw new ArgumentException("Relevé sans ouvrage correspondant");
            if (nombre == 0) texte.AppendLine("\nAucun ouvrage ajouté au plan. Les formes de départ ne sont pas des chantiers.");
            return texte.ToString();
        }

        static string DecrireJour(Dictionary<string, object> jour)
        {
            long bras = DocumentDuMonde.Entier(jour, "bras");
            double grain = DocumentDuMonde.Nombre(jour, "grain_paye_kg");
            if (grain < 0) throw new ArgumentException("Paiement de grain négatif");
            string texte = "Ce jour : " + bras + " ouvriers · "
                + grain.ToString("0.##", CultureInfo.GetCultureInfo("fr-FR")) + " kg de grain payés";
            object motif = DocumentDuMonde.Valeur(jour, "motif_arret");
            if (motif == null) return texte;
            if (!(motif is string raison)) throw new ArgumentException("Motif d’arrêt invalide");
            string cause;
            switch (raison)
            {
                case "parcelle_en_chantier": cause = "parcelle encore en chantier"; break;
                case "metiers_non_calcules": cause = "métiers non renseignés"; break;
                case "sans_bras": cause = "aucun ouvrier disponible"; break;
                case "payeur_absent": cause = "payeur absent"; break;
                case "sans_grain": cause = "grain insuffisant"; break;
                default: cause = "motif reçu non interprété"; break;
            }
            return texte + "\nArrêt : " + cause;
        }
        void OnDestroy() => lecture?.Vider();
    }
}
