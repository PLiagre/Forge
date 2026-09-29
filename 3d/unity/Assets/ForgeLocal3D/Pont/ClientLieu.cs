using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.Net;
using System.Net.Http;
using System.Text;
using System.Threading;

namespace Forge.Pont
{
    // Un lieu tel que `sim/` l'écrit à un tick : rien n'est calculé ici.
    // `Stocks` porte toutes les marchandises reçues, et seulement elles.
    public sealed class Lieu
    {
        public long CellId { get; }
        public long Tick { get; }
        public int Annee { get; }
        public int JourDeLAnnee { get; }
        public long Population { get; }
        public IReadOnlyDictionary<string, double> Stocks { get; }
        public long HungerTicks { get; }
        public double FoodDeficitKg { get; }

        public Lieu(long cellId, long tick, int annee, int jourDeLAnnee, long population,
            IDictionary<string, double> stocks, long hungerTicks, double foodDeficitKg)
        {
            if (stocks == null) throw new ArgumentNullException(nameof(stocks));
            CellId = cellId;
            Tick = tick;
            Annee = annee;
            JourDeLAnnee = jourDeLAnnee;
            Population = population;
            Stocks = new ReadOnlyDictionary<string, double>(new Dictionary<string, double>(stocks));
            HungerTicks = hungerTicks;
            FoodDeficitKg = foodDeficitKg;
        }
    }

    // Soit un lieu, soit une absence qui nomme sa cause : jamais les deux, jamais aucun.
    public sealed class LectureLieu
    {
        public Lieu Lieu { get; }
        public string Absence { get; }
        public bool Presente => Lieu != null;

        private LectureLieu(Lieu lieu, string absence) { Lieu = lieu; Absence = absence; }

        public static LectureLieu De(Lieu lieu) =>
            new LectureLieu(lieu ?? throw new ArgumentNullException(nameof(lieu)), null);

        public static LectureLieu Absent(string cause) =>
            new LectureLieu(null, string.IsNullOrEmpty(cause) ? throw new ArgumentException("une absence nomme sa cause", nameof(cause)) : cause);
    }

    // Demande un lieu au service local (`GET /lieu?cell=<cell_id>` sur 127.0.0.1).
    // Ne lève jamais pour une cause du service : elle devient une absence déclarée.
    public sealed class ClientLieu : IDisposable
    {
        private const string Hote = "127.0.0.1";
        private readonly int port;
        private readonly TimeSpan delai;
        private readonly HttpClient http;

        public ClientLieu(int port, TimeSpan delai)
        {
            if (port < 1 || port > 65535) throw new ArgumentOutOfRangeException(nameof(port), port, "port hors de 1..65535");
            if (delai <= TimeSpan.Zero && delai != Timeout.InfiniteTimeSpan)
                throw new ArgumentOutOfRangeException(nameof(delai), delai, "un délai positif attendu");
            this.port = port;
            this.delai = delai;
            // Aucune redirection suivie : un 3xx est un statut autre que 200, et la
            // lecture ne quitte jamais 127.0.0.1. Le délai est tenu par Lire, qui
            // sait ainsi le distinguer d'une erreur réseau quel que soit le runtime.
            http = new HttpClient(new HttpClientHandler { AllowAutoRedirect = false })
            {
                Timeout = Timeout.InfiniteTimeSpan
            };
        }

        public void Dispose() => http.Dispose();

        public LectureLieu Lire(long cellId)
        {
            string prefixe = "lieu " + cellId.ToString(CultureInfo.InvariantCulture) + " : ";
            HttpStatusCode statut;
            string corps;
            using (var minuterie = new CancellationTokenSource())
            {
                try
                {
                    string url = "http://" + Hote + ":" + port.ToString(CultureInfo.InvariantCulture)
                        + "/lieu?cell=" + cellId.ToString(CultureInfo.InvariantCulture);
                    minuterie.CancelAfter(delai);
                    using (HttpResponseMessage reponse = http.GetAsync(url, minuterie.Token).GetAwaiter().GetResult())
                    {
                        statut = reponse.StatusCode;
                        corps = Encoding.UTF8.GetString(reponse.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult());
                    }
                }
                catch (Exception erreur)
                {
                    // Le runtime peut rendre l'annulation sous plusieurs formes : seule la minuterie fait foi.
                    if (minuterie.IsCancellationRequested)
                        return LectureLieu.Absent(prefixe + "délai dépassé (" + delai.TotalMilliseconds.ToString(CultureInfo.InvariantCulture) + " ms) sur " + Hote + ":" + port);
                    return LectureLieu.Absent(prefixe + "service absent sur " + Hote + ":" + port + " (" + erreur.GetBaseException().Message + ")");
                }
            }

            if (statut != HttpStatusCode.OK)
                return LectureLieu.Absent(prefixe + "statut " + (int)statut + " pour cell_id " + cellId + ", corps reçu : " + corps);

            Dictionary<string, object> objet;
            try { objet = LecteurJson.LireObjet(corps); }
            catch (ErreurJson erreur)
            {
                return LectureLieu.Absent(prefixe + "JSON invalide à la position " + erreur.Position + " (" + erreur.Message + ")");
            }

            try
            {
                var date = Objet(objet, "date", "date");
                long relu = Entier(objet, "cell_id", "cell_id", long.MinValue, long.MaxValue);
                if (relu != cellId)
                    return LectureLieu.Absent(prefixe + "le service a rendu cell_id " + relu + " pour cell_id " + cellId + " demandé");
                var stocks = new Dictionary<string, double>();
                foreach (var marchandise in Objet(objet, "stocks", "stocks"))
                    stocks.Add(marchandise.Key, Nombre(marchandise.Value, "stocks." + marchandise.Key));
                return LectureLieu.De(new Lieu(
                    relu,
                    Entier(objet, "tick", "tick", long.MinValue, long.MaxValue),
                    (int)Entier(date, "annee", "date.annee", int.MinValue, int.MaxValue),
                    (int)Entier(date, "jour_de_l_annee", "date.jour_de_l_annee", int.MinValue, int.MaxValue),
                    Entier(objet, "population", "population", long.MinValue, long.MaxValue),
                    stocks,
                    Entier(objet, "hunger_ticks", "hunger_ticks", long.MinValue, long.MaxValue),
                    Nombre(Valeur(objet, "food_deficit_kg", "food_deficit_kg"), "food_deficit_kg")));
            }
            catch (CleRefusee refus)
            {
                return LectureLieu.Absent(prefixe + refus.Message);
            }
        }

        private sealed class CleRefusee : Exception
        {
            public CleRefusee(string message) : base(message) { }
        }

        private static object Valeur(Dictionary<string, object> objet, string cle, string chemin)
        {
            if (!objet.TryGetValue(cle, out object valeur)) throw new CleRefusee("clé absente : " + chemin);
            return valeur;
        }

        private static Dictionary<string, object> Objet(Dictionary<string, object> objet, string cle, string chemin) =>
            Valeur(objet, cle, chemin) as Dictionary<string, object>
            ?? throw new CleRefusee("clé " + chemin + " : un objet attendu, reçu " + Decrire(objet[cle]));

        private static double Nombre(object valeur, string chemin) =>
            valeur is double nombre ? nombre : throw new CleRefusee("clé " + chemin + " : un nombre attendu, reçu " + Decrire(valeur));

        private static long Entier(Dictionary<string, object> objet, string cle, string chemin, long min, long max)
        {
            double nombre = Nombre(Valeur(objet, cle, chemin), chemin);
            // Dès 2^53 un double ne dit plus quel entier le texte portait (9007199254740993
            // se lit 9007199254740992) : la borne elle-même est refusée plutôt que devinée.
            if (nombre != Math.Floor(nombre) || Math.Abs(nombre) >= 9007199254740992.0 || nombre < min || nombre > max)
                throw new CleRefusee("clé " + chemin + " : un entier attendu, reçu " + nombre.ToString("R", CultureInfo.InvariantCulture));
            return (long)nombre;
        }

        private static string Decrire(object valeur) =>
            valeur == null ? "null" : valeur is string texte ? "le texte \"" + texte + "\"" : valeur.GetType().Name;
    }
}
