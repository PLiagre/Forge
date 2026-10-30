using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface
{
    public sealed class DossierVoisins : MonoBehaviour
    {
        Feuillet feuillet;
        LectureDossier gestes, maisons;
        NomsDesTerres noms;
        double prochaine;
        public string TexteAffiche { get; private set; }
        public void Initialiser(Transform toile, Transform guide, int port)
        {
            gestes = LectureDossier.Locale(port); maisons = LectureDossier.Locale(port); noms = NomsDesTerres.Local(port);
            feuillet = gameObject.AddComponent<Feuillet>(); feuillet.Initialiser(toile, "Les autres maisons");
            var bouton = SocleInterface.Commande(guide, "Autres maisons", 374, 24, () =>
            {
                if (feuillet.Ouvert) feuillet.Fermer(); else feuillet.Ouvrir();
            }, phrase: "Ouvre ou ferme le journal des ordres des autres maisons.");
            bouton.GetComponent<RectTransform>().sizeDelta = new Vector2(240, 44);
            bouton.GetComponentInChildren<Text>().rectTransform.sizeDelta = new Vector2(240, 44);
        }
        void Ecrire(string texte) { TexteAffiche = texte; feuillet.Ecrire(texte); }
        void LateUpdate()
        {
            if (feuillet == null || !feuillet.Ouvert) return;
            double maintenant = Time.realtimeSinceStartupAsDouble;
            if (!gestes.EnCours && !maisons.EnCours && maintenant >= prochaine)
            {
                prochaine = maintenant + 2;
                _ = gestes.Actualiser("/ia"); _ = maisons.Actualiser("/maisons");
            }
            try
            {
                if (gestes.Erreur != null || maisons.Erreur != null) throw new ArgumentException(gestes.Erreur ?? maisons.Erreur);
                if (gestes.Document == null || maisons.Document == null) { Ecrire("Lecture des autres maisons…"); return; }
                Ecrire(Decrire(gestes.Document, maisons.Document, c => DossierMaison.NomDuLieu(noms, c, 0, maintenant)));
            }
            catch (Exception e)
            {
                Ecrire(e.Message.Contains("ia désactivée") ? "Les autres maisons ne sont pas actives dans cette partie." : Indisponible(e.Message));
            }
        }
        static Dictionary<string, object> Objet(object brut) => brut as Dictionary<string, object>
            ?? throw new ArgumentException("Objet du journal absent");
        static string Masse(Dictionary<string, object> donnees, string cle) => TexteDuMonde.Masse(DocumentDuMonde.Nombre(donnees, cle));
        public static string Indisponible(string raison) => "Journal indisponible : " + TexteDuMonde.Absence(raison);
        public static string Decrire(DocumentDuMonde document, DocumentDuMonde registre, Func<long, string> nomDuBourg)
        {
            if (nomDuBourg == null) throw new ArgumentNullException(nameof(nomDuBourg));
            if (document.Annee == null) throw new ArgumentException("Date non transmise");
            var liste = DocumentDuMonde.Tableau(registre.Champs, "maisons");
            if (liste.Count == 0 || liste.Count != DocumentDuMonde.Entier(registre.Champs, "nombre"))
                throw new ArgumentException("Registre des maisons incomplet");
            var noms = liste.Select(Objet).ToDictionary(m => DocumentDuMonde.Texte(m, "id"),
                m => DocumentDuMonde.Valeur(m, "nom") as string ?? "Maison non nommée");
            double actives = DocumentDuMonde.Nombre(document.Champs, "maisons_actives_30j");
            if (actives < -1 || Math.Floor(actives) != actives) throw new ArgumentException("Mesure des maisons actives invalide");
            var texte = new StringBuilder("Journal du " + TexteDuMonde.Date(new DateDuMonde(document.Annee.Value, document.JourDeLAnnee.Value)) + "\n");
            texte.AppendLine("Activité des premiers 30 jours : " + (actives == -1 ? "mesure en cours"
                : TexteDuMonde.Nombre((long)actives) + (actives == 1 ? " maison" : " maisons")));
            var releve = DocumentDuMonde.Tableau(document.Champs, "releve");
            if (releve.Count == 0) texte.AppendLine("\nAucun ordre transmis.");
            var vus = new HashSet<string>();
            foreach (var e in releve.Select(Objet).OrderByDescending(e => DocumentDuMonde.Entier(e, "tick")))
            {
                long tick = DocumentDuMonde.Entier(e, "tick");
                if (tick > document.Tick) throw new ArgumentException("Ordre daté après le journal");
                var intention = DocumentDuMonde.Objet(e, "intention");
                string id = DocumentDuMonde.Texte(intention, "maison"), type = DocumentDuMonde.Texte(intention, "type");
                // Seule une route a une terre : un ordre de part ou de grenier n'a pas de `cell`.
                bool route = type == "tracer_route";
                long cell = route ? DocumentDuMonde.Entier(intention, "cell") : -1;
                if (!vus.Add(tick + "/" + id + "/" + type + (route ? "/" + cell : ""))) throw new ArgumentException("Ordre dupliqué dans le journal");
                long ecart = document.Tick - tick; // un tick dure un jour
                texte.AppendLine("\n" + (noms.TryGetValue(id, out string nom) ? nom : "Maison absente du registre") + " · "
                    + (ecart == 0 ? "ce jour" : "il y a " + TexteDuMonde.Jours(ecart)));
                texte.AppendLine(route ? "Tracer une route à " + nomDuBourg(cell) : "Ordre non interprété par cette vue");
                texte.AppendLine(e.ContainsKey("refus") ? "Refus : " + DocumentDuMonde.Texte(e, "refus") : "Ordre reçu. Achèvement non renseigné.");
                var raison = DocumentDuMonde.Objet(e, "raison");
                if (DocumentDuMonde.Texte(raison, "regle") != "route_si_bourg_affame")
                { texte.AppendLine("Raison non interprétée par cette vue."); continue; }
                var bourg = DocumentDuMonde.Objet(raison, "bourg");
                long population = DocumentDuMonde.Entier(bourg, "population");
                texte.AppendLine("Bourg affamé : " + TexteDuMonde.Nombre(population) + (population <= 1 ? " habitant, " : " habitants, ")
                    + TexteDuMonde.Jours(DocumentDuMonde.Entier(bourg, "duree_faim_ticks")) + " de faim.");
                texte.AppendLine("Dette alimentaire : " + Masse(bourg, "dette_alimentaire_kg") + " · Nourriture : " + Masse(bourg, "nourriture_kg"));
            }
            return texte.ToString();
        }
        void OnDestroy() { gestes?.Vider(); maisons?.Vider(); }
    }
}
