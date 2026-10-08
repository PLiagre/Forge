using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.Linq;
using System.Net.Http;
using System.Text;
using System.Threading;

namespace Forge.Pont
{
    // La date que le service sert, relue telle quelle : Unity ne l'avance jamais.
    public readonly struct DateDuMonde
    {
        public long Annee { get; }
        public long JourDeLAnnee { get; }
        public DateDuMonde(long annee, long jourDeLAnnee) { Annee = annee; JourDeLAnnee = jourDeLAnnee; }
    }

    // Une cellule du monde. `Population` 0 est une mesure ; `HungerTicks` et `FoodDeficitKg` à -1 disent « non calculé », jamais zéro.
    // La faim est une durée en ticks, la dette des kilos de nourriture : aucune ne se déduit d'un stock.
    public sealed class CelluleDuMonde
    {
        public long CellId { get; }
        public long Population { get; }
        public long HungerTicks { get; }
        public double FoodDeficitKg { get; }
        public CelluleDuMonde(long cellId, long population, long hungerTicks, double foodDeficitKg)
        {
            CellId = cellId; Population = population; HungerTicks = hungerTicks; FoodDeficitKg = foodDeficitKg;
        }
    }

    // Le monde servi à un tick, ses cellules dans l'ordre de la réponse.
    public sealed class MondeLu
    {
        public long Tick { get; }
        public DateDuMonde Date { get; }
        public long CellCount { get; }
        public IReadOnlyList<CelluleDuMonde> Cellules { get; }
        public MondeLu(long tick, DateDuMonde date, long cellCount, IEnumerable<CelluleDuMonde> cellules)
        {
            Tick = tick; Date = date; CellCount = cellCount;
            Cellules = new ReadOnlyCollection<CelluleDuMonde>(new List<CelluleDuMonde>(cellules ?? throw new ArgumentNullException(nameof(cellules))));
        }
    }

    // Soit des données, soit une absence qui nomme sa cause : jamais les deux, jamais aucune.
    public sealed class Lecture<T> where T : class
    {
        public T Donnees { get; }
        public string Absence { get; }
        public bool Presente => Donnees != null;
        private Lecture(T donnees, string absence) { Donnees = donnees; Absence = absence; }
        public static Lecture<T> De(T donnees) => new Lecture<T>(donnees ?? throw new ArgumentNullException(nameof(donnees)), null);
        public static Lecture<T> Absent(string cause) =>
            new Lecture<T>(null, string.IsNullOrEmpty(cause) ? throw new ArgumentException("une absence nomme sa cause", nameof(cause)) : cause);
    }

    // Relit le monde servi (`GET /monde` sur 127.0.0.1) : date, habitants, faim et dette de chaque cellule, sans rien recalculer.
    // Ne lève jamais pour une cause du service : elle devient une absence. Une seule clé fautive refuse toute la réponse.
    public sealed class ClientMonde : IDisposable
    {
        private readonly ServiceLocal service;

        public ClientMonde(int port, TimeSpan delai) { service = new ServiceLocal(port, delai, "monde : "); }

        public void Dispose() => service.Dispose();

        public Lecture<MondeLu> Lire() => service.Demander(HttpMethod.Get, "/monde", Monde);

        private static MondeLu Monde(Dictionary<string, object> racine)
        {
            object brutes = ServiceLocal.Valeur(racine, "cells");
            var tableau = brutes as List<object> ?? throw ServiceLocal.Refus("cells", "un tableau", brutes);
            // Un monde sans cellule n'est pas une mesure.
            if (tableau.Count == 0) throw new ServiceLocal.Refusee("clé cells : au moins une cellule attendue, reçu 0");
            var identifiants = new HashSet<long>();
            List<CelluleDuMonde> cellules = tableau.Select((brute, i) => Cellule(brute, "cells[" + i.ToString(CultureInfo.InvariantCulture) + "]", identifiants)).ToList();
            long annonce = ServiceLocal.Entier(racine, "cell_count", 0);
            if (annonce != cellules.Count) throw new ServiceLocal.Refusee("clé cell_count : " + annonce + " annoncées, " + cellules.Count + " lues");
            return new MondeLu(ServiceLocal.Entier(racine, "tick", 0), ServiceLocal.Date(racine), annonce, cellules);
        }

        // `identifiants` : les cell_id déjà lus dans cette réponse ; un second la refuse.
        private static CelluleDuMonde Cellule(object valeur, string chemin, HashSet<long> identifiants)
        {
            var cellule = valeur as Dictionary<string, object> ?? throw ServiceLocal.Refus(chemin, "un objet", valeur);
            long cellId = ServiceLocal.Entier(cellule, chemin + ".cell_id", 0);
            if (!identifiants.Add(cellId)) throw new ServiceLocal.Refusee("clé " + chemin + ".cell_id : " + cellId + " déjà lu dans cette réponse");
            long population = ServiceLocal.Entier(cellule, chemin + ".population", 0), faim = ServiceLocal.Entier(cellule, chemin + ".hunger_ticks", -1);
            double dette = ServiceLocal.Nombre(ServiceLocal.Valeur(cellule, chemin + ".food_deficit_kg"), chemin + ".food_deficit_kg");
            if (dette < 0 && dette != -1) throw ServiceLocal.Refus(chemin + ".food_deficit_kg", "un nombre ≥ 0 ou -1 (non calculé)", dette);
            return new CelluleDuMonde(cellId, population, faim, dette);
        }
    }

    // Ce que ClientMonde et ClientHorloge partagent : un HttpClient réutilisé, sans redirection suivie, une minuterie qui couvre
    // toute la réponse, et la lecture des clés qui nomme le chemin fautif.
    internal sealed class ServiceLocal : IDisposable
    {
        private const string Hote = "127.0.0.1";
        private readonly string adresse, prefixe;
        private readonly TimeSpan delai;
        private readonly HttpClient http;

        internal ServiceLocal(int port, TimeSpan delai, string prefixe)
        {
            if (port < 1 || port > 65535) throw new ArgumentOutOfRangeException(nameof(port), port, "port hors de 1..65535");
            // `Timeout.InfiniteTimeSpan` vaut -1 ms ; au-delà de int.MaxValue ms, la minuterie ne sait plus compter.
            if (delai <= TimeSpan.Zero || delai.TotalMilliseconds > int.MaxValue) throw new ArgumentOutOfRangeException(nameof(delai), delai, "un délai fini et positif attendu");
            adresse = Hote + ":" + port.ToString(CultureInfo.InvariantCulture);
            this.delai = delai;
            this.prefixe = prefixe;
            http = new HttpClient(new HttpClientHandler { AllowAutoRedirect = false }) { Timeout = Timeout.InfiniteTimeSpan };
        }

        public void Dispose() => http.Dispose();

        // `cible` : le chemin et sa requête. Un POST part avec un corps vide (Content-Length: 0).
        internal Lecture<T> Demander<T>(HttpMethod methode, string cible, Func<Dictionary<string, object>, T> lire) where T : class
        {
            int statut;
            string corps;
            using (var minuterie = new CancellationTokenSource())
            using (var requete = new HttpRequestMessage(methode, "http://" + adresse + cible))
            {
                if (methode == HttpMethod.Post) requete.Content = new ByteArrayContent(new byte[0]);
                try
                {
                    minuterie.CancelAfter(delai);
                    using (HttpResponseMessage reponse = http.SendAsync(requete, HttpCompletionOption.ResponseContentRead, minuterie.Token).GetAwaiter().GetResult())
                        (statut, corps) = ((int)reponse.StatusCode, Encoding.UTF8.GetString(reponse.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()));
                }
                catch (Exception erreur)
                {
                    // Seule la minuterie dit si le délai est échu : le runtime rend l'annulation sous plusieurs formes.
                    return Lecture<T>.Absent(prefixe + (minuterie.IsCancellationRequested
                        ? "délai dépassé (" + delai.TotalMilliseconds.ToString(CultureInfo.InvariantCulture) + " ms) sur " + adresse
                        : "service absent sur " + adresse + " (" + erreur.GetBaseException().Message + ")"));
                }
            }
            if (statut != 200) return Lecture<T>.Absent(prefixe + "statut " + statut + ", corps reçu : " + corps);
            try { return Lecture<T>.De(lire(LecteurJson.LireObjet(corps))); }
            catch (ErreurJson erreur) { return Lecture<T>.Absent(prefixe + "JSON invalide à la position " + erreur.Position + " (" + erreur.Message + ")"); }
            catch (Refusee refus) { return Lecture<T>.Absent(prefixe + refus.Message); }
        }

        internal sealed class Refusee : Exception { public Refusee(string message) : base(message) { } }

        internal static Refusee Refus(string chemin, string attendu, object recu) => new Refusee("clé " + chemin + " : " + attendu + " attendu, reçu " + Decrire(recu));

        // La clé lue est le dernier segment du chemin pointé : `cells[1].population` lit `population`.
        internal static object Valeur(Dictionary<string, object> objet, string chemin) =>
            objet.TryGetValue(chemin.Substring(chemin.LastIndexOf('.') + 1), out object valeur) ? valeur : throw new Refusee("clé absente : " + chemin);

        internal static double Nombre(object valeur, string chemin) => valeur is double nombre && !double.IsNaN(nombre) && !double.IsInfinity(nombre) ? nombre : throw Refus(chemin, "un nombre fini", valeur);

        // Un entier ≥ `min` ; `min` à -1 admet -1, « non calculé ». Dès 2^53 un double ne dit plus quel entier le texte portait.
        internal static long Entier(Dictionary<string, object> objet, string chemin, long min)
        {
            double nombre = Nombre(Valeur(objet, chemin), chemin);
            if (nombre != Math.Floor(nombre) || nombre < min || nombre >= 9007199254740992.0)
                throw Refus(chemin, min == -1 ? "un entier ≥ 0 ou -1 (non calculé)" : "un entier ≥ " + min + " sous 2^53", nombre);
            return (long)nombre;
        }

        // L'année et le jour de l'année sont des entiers positifs.
        internal static DateDuMonde Date(Dictionary<string, object> racine)
        {
            object brute = Valeur(racine, "date");
            var date = brute as Dictionary<string, object> ?? throw Refus("date", "un objet", brute);
            return new DateDuMonde(Entier(date, "date.annee", 1), Entier(date, "date.jour_de_l_annee", 1));
        }

        private static string Decrire(object valeur) => valeur == null ? "null" : valeur is string texte ? "le texte \"" + texte + "\""
            : valeur is double nombre ? nombre.ToString("R", CultureInfo.InvariantCulture) : valeur.GetType().Name;
    }
}
