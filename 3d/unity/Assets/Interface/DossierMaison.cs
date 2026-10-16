using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface
{
    public sealed class DossierMaison : MonoBehaviour
    {
        Feuillet feuillet;
        Func<string> maison;
        LectureDossier lecture, suzerain;
        double prochaine;
        public void Initialiser(Transform toile, Func<string> maison, int port)
        {
            this.maison = maison;
            lecture = LectureDossier.Locale(port); suzerain = LectureDossier.Locale(port);
            feuillet = gameObject.AddComponent<Feuillet>(); feuillet.Initialiser(toile, "Terres et comptes");
            var bouton = SocleInterface.Commande(toile, "Terres et comptes", 1000, 20, () =>
            {
                if (feuillet.Ouvert) feuillet.Fermer(); else feuillet.Ouvrir();
            });
            bouton.GetComponent<RectTransform>().sizeDelta = new Vector2(260, 44);
            bouton.GetComponentInChildren<Text>().rectTransform.sizeDelta = new Vector2(260, 44);
        }
        void LateUpdate()
        {
            if (feuillet == null || !feuillet.Ouvert) return;
            string id = maison();
            if (id == null) { feuillet.Ecrire("Choisissez une maison pour consulter ses terres et ses comptes."); return; }
            if (!lecture.EnCours && Time.realtimeSinceStartupAsDouble >= prochaine)
            {
                prochaine = Time.realtimeSinceStartupAsDouble + 2;
                _ = lecture.Actualiser("/maison?id=" + Uri.EscapeDataString(id));
            }
            try
            {
                if (lecture.Erreur != null) throw new ArgumentException(lecture.Erreur);
                var doc = lecture.Document;
                if (doc == null || DocumentDuMonde.Texte(doc.Champs, "id") != id) throw new ArgumentException("Maison en attente du monde");
                var parent = DocumentDuMonde.Valeur(doc.Champs, "suzerain") as string;
                string nom = null;
                if (parent != null)
                {
                    string cle = "/maison?id=" + Uri.EscapeDataString(parent);
                    if (suzerain.Cle != cle) _ = suzerain.Actualiser(cle);
                    if (suzerain.Document != null && DocumentDuMonde.Texte(suzerain.Document.Champs, "id") == parent)
                        nom = DocumentDuMonde.Texte(suzerain.Document.Champs, "nom");
                }
                feuillet.Ecrire(Decrire(doc, nom));
            }
            catch (Exception e) { feuillet.Ecrire("Comptes indisponibles : " + e.Message); }
        }
        public static string Decrire(DocumentDuMonde doc, string nomSuzerain = null)
        {
            var d = doc.Champs;
            var siege = DocumentDuMonde.Objet(d, "siege");
            var lieux = DocumentDuMonde.Tableau(d, "lieux");
            if (lieux.Count == 0) throw new ArgumentException("Aucun lieu transmis pour cette maison");
            var texte = new StringBuilder();
            texte.AppendLine(DocumentDuMonde.Texte(d, "nom") + " · " + DocumentDuMonde.Texte(d, "sorte") + " · tick " + doc.Tick);
            texte.AppendLine("Siège : " + DocumentDuMonde.Texte(siege, "nom"));
            texte.AppendLine("Suzerain : " + (DocumentDuMonde.Valeur(d, "suzerain") == null ? "aucun" : nomSuzerain ?? "nom non transmis"));
            texte.AppendLine("\nTERRES TENUES");
            foreach (var brut in lieux)
            {
                var lieu = brut as Dictionary<string, object> ?? throw new ArgumentException("Lieu invalide");
                texte.AppendLine("Territoire " + DocumentDuMonde.Entier(lieu, "cell_id") + " · lieu " + DocumentDuMonde.Entier(lieu, "rang"));
            }
            var flux = DocumentDuMonde.Objet(d, "flux_30j");
            texte.AppendLine("\nCirculation sur 30 jours");
            string[] cles = { "preleve_kg", "recu_kg", "du_envoye_kg", "mange_en_route_kg", "rendu_kg" };
            string[] noms = { "Prélevé", "Reçu", "Dû envoyé", "Consommé en route", "Rendu" };
            for (int i = 0; i < cles.Length; i++)
                texte.AppendLine(noms[i] + " : " + DocumentDuMonde.Nombre(flux, cles[i]).ToString("0.##", CultureInfo.GetCultureInfo("fr-FR")) + " kg");
            texte.AppendLine("Départs : " + DocumentDuMonde.Entier(flux, "partis_personnes") + " personnes");
            texte.AppendLine("Arrivées : " + DocumentDuMonde.Entier(flux, "arrives_personnes") + " personnes");
            texte.AppendLine("Salaires : " + (flux.ContainsKey("salaires_payes_kg") ? DocumentDuMonde.Nombre(flux, "salaires_payes_kg").ToString("0.##", CultureInfo.GetCultureInfo("fr-FR")) + " kg" : "non transmis"));
            return texte.ToString();
        }
        void OnDestroy() { lecture?.Vider(); suzerain?.Vider(); }
    }
}
