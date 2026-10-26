using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface
{
    public sealed class DossierVoisins : MonoBehaviour
    {
        Feuillet feuillet;
        LectureDossier gestes, maisons;
        double prochaine;
        public void Initialiser(Transform toile, Transform guide, int port)
        {
            gestes = LectureDossier.Locale(port); maisons = LectureDossier.Locale(port);
            feuillet = gameObject.AddComponent<Feuillet>(); feuillet.Initialiser(toile, "Les autres maisons");
            var bouton = SocleInterface.Commande(guide, "Autres maisons", 374, 24, () =>
            {
                if (feuillet.Ouvert) feuillet.Fermer(); else feuillet.Ouvrir();
            });
            bouton.GetComponent<RectTransform>().sizeDelta = new Vector2(240, 44);
            bouton.GetComponentInChildren<Text>().rectTransform.sizeDelta = new Vector2(240, 44);
        }
        void LateUpdate()
        {
            if (feuillet == null || !feuillet.Ouvert) return;
            if (!gestes.EnCours && !maisons.EnCours && Time.realtimeSinceStartupAsDouble >= prochaine)
            {
                prochaine = Time.realtimeSinceStartupAsDouble + 2;
                _ = gestes.Actualiser("/ia"); _ = maisons.Actualiser("/maisons");
            }
            try
            {
                if (gestes.Erreur != null || maisons.Erreur != null) throw new ArgumentException(gestes.Erreur ?? maisons.Erreur);
                if (gestes.Document == null || maisons.Document == null) { feuillet.Ecrire("Lecture des autres maisons…"); return; }
                feuillet.Ecrire(Decrire(gestes.Document, maisons.Document));
            }
            catch (Exception e)
            {
                feuillet.Ecrire(e.Message.Contains("ia désactivée") ? "Les autres maisons ne sont pas actives dans cette partie."
                    : "Journal indisponible : " + e.Message);
            }
        }
        static Dictionary<string, object> Objet(object brut) => brut as Dictionary<string, object>
            ?? throw new ArgumentException("Objet du journal absent");
        static string Kg(Dictionary<string, object> donnees, string cle) =>
            DocumentDuMonde.Nombre(donnees, cle).ToString("0.##", CultureInfo.GetCultureInfo("fr-FR")) + " kg";
        public static string Decrire(DocumentDuMonde document, DocumentDuMonde registre)
        {
            var liste = DocumentDuMonde.Tableau(registre.Champs, "maisons");
            if (liste.Count == 0 || liste.Count != DocumentDuMonde.Entier(registre.Champs, "nombre"))
                throw new ArgumentException("Registre des maisons incomplet");
            var noms = liste.Select(Objet).ToDictionary(m => DocumentDuMonde.Texte(m, "id"),
                m => DocumentDuMonde.Valeur(m, "nom") as string ?? "Maison non nommée");
            double actives = DocumentDuMonde.Nombre(document.Champs, "maisons_actives_30j");
            if (actives < -1 || Math.Floor(actives) != actives) throw new ArgumentException("Mesure des maisons actives invalide");
            var texte = new StringBuilder("Journal au tick " + document.Tick + " · noms au tick " + registre.Tick + "\n");
            texte.AppendLine("Activité des 30 premiers jours : " + (actives == -1 ? "mesure en cours" : actives + (actives == 1 ? " maison" : " maisons")));
            var releve = DocumentDuMonde.Tableau(document.Champs, "releve");
            if (releve.Count == 0) texte.AppendLine("\nAucun ordre transmis.");
            var vus = new HashSet<string>();
            foreach (var e in releve.Select(Objet).OrderByDescending(e => DocumentDuMonde.Entier(e, "tick")))
            {
                long tick = DocumentDuMonde.Entier(e, "tick");
                if (tick > document.Tick) throw new ArgumentException("Ordre daté après le journal");
                var intention = DocumentDuMonde.Objet(e, "intention");
                string id = DocumentDuMonde.Texte(intention, "maison"), type = DocumentDuMonde.Texte(intention, "type");
                long cell = DocumentDuMonde.Entier(intention, "cell");
                if (!vus.Add(tick + "/" + id + "/" + type + "/" + cell)) throw new ArgumentException("Ordre dupliqué dans le journal");
                texte.AppendLine("\n" + (noms.TryGetValue(id, out string nom) ? nom : "Maison absente du registre") + " · tick " + tick);
                texte.AppendLine(type == "tracer_route" ? "Tracer une route · territoire " + cell : "Ordre non interprété par cette vue");
                texte.AppendLine(e.ContainsKey("refus") ? "Refus : " + DocumentDuMonde.Texte(e, "refus") : "Ordre reçu. Achèvement non renseigné.");
                var raison = DocumentDuMonde.Objet(e, "raison");
                if (DocumentDuMonde.Texte(raison, "regle") != "route_si_bourg_affame")
                { texte.AppendLine("Raison non interprétée par cette vue."); continue; }
                var bourg = DocumentDuMonde.Objet(raison, "bourg");
                long faim = DocumentDuMonde.Entier(bourg, "duree_faim_ticks");
                texte.AppendLine("Bourg affamé : " + DocumentDuMonde.Entier(bourg, "population") + " habitants, "
                    + faim + (faim == 1 ? " tick de faim." : " ticks de faim."));
                texte.AppendLine("Dette alimentaire : " + Kg(bourg, "dette_alimentaire_kg") + " · Nourriture : " + Kg(bourg, "nourriture_kg"));
            }
            return texte.ToString();
        }
        void OnDestroy() { gestes?.Vider(); maisons?.Vider(); }
    }
}
