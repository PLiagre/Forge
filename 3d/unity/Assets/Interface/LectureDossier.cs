using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Threading.Tasks;
using Forge.Pont;

namespace Forge.Interface
{
    public sealed class DocumentDuMonde
    {
        public long Tick { get; }
        public Dictionary<string, object> Champs { get; }
        public DocumentDuMonde(string json)
        {
            Champs = LecteurJson.LireObjet(json);
            Tick = Entier(Champs, "tick");
        }
        public static object Valeur(Dictionary<string, object> objet, string cle)
        {
            if (!objet.TryGetValue(cle, out var valeur)) throw new ArgumentException("Champ absent : " + cle);
            return valeur;
        }
        public static double Nombre(Dictionary<string, object> objet, string cle)
        {
            if (!(Valeur(objet, cle) is double nombre) || double.IsNaN(nombre) || double.IsInfinity(nombre))
                throw new ArgumentException("Nombre absent ou invalide : " + cle);
            return nombre;
        }
        public static long Entier(Dictionary<string, object> objet, string cle)
        {
            double n = Nombre(objet, cle);
            if (n < 0 || n >= 9007199254740992 || Math.Floor(n) != n)
                throw new ArgumentException("Entier positif ou nul attendu : " + cle);
            return (long)n;
        }
        public static string Texte(Dictionary<string, object> objet, string cle) => Valeur(objet, cle) as string
            ?? throw new ArgumentException("Texte absent : " + cle);
        public static Dictionary<string, object> Objet(Dictionary<string, object> objet, string cle) =>
            Valeur(objet, cle) as Dictionary<string, object> ?? throw new ArgumentException("Objet absent : " + cle);
        public static List<object> Tableau(Dictionary<string, object> objet, string cle) => Valeur(objet, cle) as List<object>
            ?? throw new ArgumentException("Liste absente : " + cle);
    }
    public sealed class LectureDossier
    {
        public DocumentDuMonde Document { get; private set; }
        public string Erreur { get; private set; }
        public bool EnCours { get; private set; }
        public string Cle { get; private set; }
        readonly Func<string, Task<DocumentDuMonde>> lire;
        int generation;
        public LectureDossier(Func<string, Task<DocumentDuMonde>> lire)
        {
            this.lire = lire ?? throw new ArgumentNullException(nameof(lire));
        }
        public void Vider()
        {
            generation++;
            Cle = null; Document = null; Erreur = null; EnCours = false;
        }
        public async Task Actualiser(string cle)
        {
            if (string.IsNullOrWhiteSpace(cle)) throw new ArgumentException("Dossier absent", nameof(cle));
            if (Cle == cle && EnCours) return;
            if (Cle != cle) { Vider(); Cle = cle; }
            int demande = generation;
            EnCours = true;
            try
            {
                var recu = await lire(cle);
                if (demande != generation) return;
                if (recu == null) throw new ArgumentException("Document absent");
                if (Document != null && recu.Tick < Document.Tick)
                {
                    Erreur = "Relevé ancien refusé ; dernier relevé conservé au tick " + Document.Tick;
                    return;
                }
                Document = recu; Erreur = null;
            }
            catch (Exception erreur)
            {
                if (demande == generation) { Document = null; Erreur = erreur.GetBaseException().Message; }
            }
            finally { if (demande == generation) EnCours = false; }
        }
        public static LectureDossier Locale(int port)
        {
            if (port < 1 || port > 65535) throw new ArgumentOutOfRangeException(nameof(port));
            return new LectureDossier(async chemin =>
            {
                if (!chemin.StartsWith("/") || chemin.StartsWith("//")) throw new ArgumentException("Chemin local attendu");
                using (var client = new HttpClient(new HttpClientHandler { AllowAutoRedirect = false }))
                {
                    client.Timeout = TimeSpan.FromSeconds(10);
                    using (var reponse = await client.GetAsync("http://127.0.0.1:" + port + chemin))
                    {
                        string corps = await reponse.Content.ReadAsStringAsync();
                        if (!reponse.IsSuccessStatusCode) throw new ArgumentException("Lecture refusée (" + (int)reponse.StatusCode + ") : " + corps);
                        return new DocumentDuMonde(corps);
                    }
                }
            });
        }
    }
}
