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
    public sealed class DossierMaison : MonoBehaviour
    {
        Feuillet feuillet;
        Func<string> maison;
        LectureDossier lecture, suzerain;
        Func<long?> tick;
        NomsDesTerres noms;
        double prochaine;
        public string TexteAffiche { get; private set; }
        public void Initialiser(Transform toile, Func<string> maison, int port) => Initialiser(toile, maison,
            LectureDossier.Locale(port), LectureDossier.Locale(port), () => GetComponent<HorlogeDeCarte>()?.Lue?.Tick, NomsDesTerres.Local(port));
        public void Initialiser(Transform toile, Func<string> maison, LectureDossier lecture, LectureDossier suzerain, Func<long?> tick, NomsDesTerres noms)
        {
            this.maison = maison; this.lecture = lecture; this.suzerain = suzerain; this.tick = tick; this.noms = noms;
            feuillet = gameObject.AddComponent<Feuillet>(); feuillet.Initialiser(toile, "Terres et comptes");
            var bouton = SocleInterface.Commande(toile, "Terres et comptes", 1000, 20, () =>
            {
                if (feuillet.Ouvert) feuillet.Fermer(); else feuillet.Ouvrir();
            }, phrase: "Ouvre ou ferme les terres et les comptes de votre maison.");
            bouton.GetComponent<RectTransform>().sizeDelta = new Vector2(260, 44);
            bouton.GetComponentInChildren<Text>().rectTransform.sizeDelta = new Vector2(260, 44);
        }
        void LateUpdate() => Pas(Time.realtimeSinceStartupAsDouble);
        void Ecrire(string texte) { TexteAffiche = texte; feuillet.Ecrire(texte); }
        public void Pas(double maintenant)
        {
            if (feuillet == null || !feuillet.Ouvert) return;
            string id = maison();
            if (id == null) { Ecrire("Choisissez une maison pour consulter ses terres et ses comptes."); return; }
            // Tick publié connu : relire dès qu'il dépasse le relevé de cette maison, et pas avant ; sinon (ou après un échec), toutes les 2 s.
            string adresse = "/maison?id=" + Uri.EscapeDataString(id); long? publie = tick();
            bool perime = publie != null && lecture.Erreur == null && (lecture.Document == null || lecture.Cle != adresse || lecture.Document.Tick < publie);
            if (!lecture.EnCours && (perime || (publie == null || lecture.Erreur != null) && maintenant >= prochaine))
            {
                prochaine = maintenant + 2;
                _ = lecture.Actualiser(adresse);
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
                Ecrire(Decrire(doc, nom, (c, r) => NomDuLieu(noms, c, r, maintenant)));
            }
            catch (Exception e) { Ecrire(Indisponible(e.Message)); }
        }
        public static string Indisponible(string raison) => "Comptes indisponibles : " + TexteDuMonde.Absence(raison);
        public static string NomDuLieu(NomsDesTerres noms, long cell, long rang, double maintenant) =>
            noms.Nom(cell, rang, maintenant) ?? TexteDuMonde.Absence(noms.Raison(cell, rang), cell.ToString(CultureInfo.InvariantCulture));
        public static string Decrire(DocumentDuMonde doc, string nomSuzerain, Func<long, long, string> nomDuLieu)
        {
            var d = doc.Champs;
            var siege = DocumentDuMonde.Objet(d, "siege");
            var lieux = DocumentDuMonde.Tableau(d, "lieux");
            if (lieux.Count == 0) throw new ArgumentException("Aucun lieu transmis pour cette maison");
            if (doc.Annee == null) throw new ArgumentException("Date non transmise");
            var absents = DocumentDuMonde.Objet(d, "absents");
            var fr = CultureInfo.GetCultureInfo("fr-FR");
            var texte = new StringBuilder();
            var cellules = new List<string> { DocumentDuMonde.Entier(siege, "cell_id").ToString(CultureInfo.InvariantCulture) };
            texte.AppendLine((Absent(d, absents, "nom") ? "nom absent" : DocumentDuMonde.Texte(d, "nom")) + " · " + DocumentDuMonde.Texte(d, "sorte") + " · " + TexteDuMonde.Date(new DateDuMonde(doc.Annee.Value, doc.JourDeLAnnee.Value)));
            texte.AppendLine("Siège : " + DocumentDuMonde.Texte(siege, "nom"));
            texte.AppendLine("Suzerain : " + (DocumentDuMonde.Valeur(d, "suzerain") == null ? "aucun" : nomSuzerain ?? "nom non transmis"));
            texte.AppendLine("Prélèvement : " + (!d.ContainsKey("part") ? "non transmis" : Absent(d, absents, "part") ? "absent"
                : (Borne(DocumentDuMonde.Nombre(d, "part"), 1, "part") * 100).ToString("0.##", fr) + " %"));
            var grenier = !d.ContainsKey("grenier") || Absent(d, absents, "grenier") ? null : DocumentDuMonde.Objet(d, "grenier");
            var panier = grenier?.Keys.OrderBy(k => k, StringComparer.Ordinal)
                .Select(k => k + " : " + TexteDuMonde.Masse(Borne(DocumentDuMonde.Nombre(grenier, k), double.MaxValue, k))).ToList();
            texte.AppendLine("Grenier : " + (!d.ContainsKey("grenier") ? "non transmis" : panier == null ? "absent" : panier.Count == 0 ? "vide" : string.Join(" · ", panier)));
            texte.AppendLine("\nTERRES TENUES");
            foreach (var brut in lieux)
            {
                var lieu = brut as Dictionary<string, object> ?? throw new ArgumentException("Lieu invalide");
                long cell = DocumentDuMonde.Entier(lieu, "cell_id"), rang = DocumentDuMonde.Entier(lieu, "rang");
                cellules.Add(cell.ToString(CultureInfo.InvariantCulture));
                string bourg = nomDuLieu(cell, 0);
                texte.AppendLine(rang == 0 ? bourg : bourg + " · " + nomDuLieu(cell, rang));
            }
            var flux = DocumentDuMonde.Objet(d, "flux_30j");
            texte.AppendLine("\nCirculation sur 30 jours");
            string[] cles = { "preleve_kg", "recu_kg", "du_envoye_kg", "mange_en_route_kg", "rendu_kg" };
            string[] noms = { "Prélevé", "Reçu", "Dû envoyé", "Consommé en route", "Rendu" };
            for (int i = 0; i < cles.Length; i++)
                texte.AppendLine(noms[i] + " : " + TexteDuMonde.Masse(DocumentDuMonde.Nombre(flux, cles[i])));
            texte.AppendLine("Départs : " + Personnes(DocumentDuMonde.Entier(flux, "partis_personnes")));
            texte.AppendLine("Arrivées : " + Personnes(DocumentDuMonde.Entier(flux, "arrives_personnes")));
            texte.AppendLine("Salaires : " + (flux.ContainsKey("salaires_payes_kg") ? TexteDuMonde.Masse(DocumentDuMonde.Nombre(flux, "salaires_payes_kg")) : "non transmis"));
            texte.AppendLine("\nABSENCES DÉCLARÉES");
            if (absents.Count == 0) texte.AppendLine("aucune");
            foreach (var a in absents.OrderBy(p => p.Key, StringComparer.Ordinal))
                texte.AppendLine(a.Key + " : " + TexteDuMonde.Absence(a.Value as string ?? throw new ArgumentException("Raison non textuelle : " + a.Key), cellules.ToArray()));
            return texte.ToString();
        }
        static string Personnes(long n) => TexteDuMonde.Nombre(n) + (n > 1 ? " personnes" : " personne");
        // Une valeur nulle n'est une absence que si le monde en donne la raison ; sinon le bilan est refusé.
        static bool Absent(Dictionary<string, object> d, Dictionary<string, object> absents, string cle) =>
            DocumentDuMonde.Valeur(d, cle) == null && (absents.ContainsKey(cle) ? true : throw new ArgumentException(cle + " nul sans raison déclarée"));
        static double Borne(double n, double max, string cle) => n >= 0 && n <= max ? n : throw new ArgumentException("Hors bornes : " + cle);
        void OnDestroy() { lecture?.Vider(); suzerain?.Vider(); }
    }
}
