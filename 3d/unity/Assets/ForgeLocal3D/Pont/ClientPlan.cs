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
    // Un point du plan, en mètres locaux du bourg (x vers l'est, y vers le nord), relu tel quel.
    public readonly struct PointLocal
    {
        public double X { get; }
        public double Y { get; }

        public PointLocal(double x, double y) { X = x; Y = y; }
    }

    // Une rue telle que `sim/` la tient : rien n'est calculé ni borné ici.
    public sealed class RueDuPlan
    {
        public long Identifiant { get; }
        public IReadOnlyList<PointLocal> Points { get; }
        public double LargeurM { get; }
        public bool EnChantier { get; }

        public RueDuPlan(long identifiant, IList<PointLocal> points, double largeurM, bool enChantier)
        {
            if (points == null) throw new ArgumentNullException(nameof(points));
            Identifiant = identifiant;
            Points = new ReadOnlyCollection<PointLocal>(new List<PointLocal>(points));
            LargeurM = largeurM;
            EnChantier = enChantier;
        }
    }

    // Le plan d'une cellule à un tick. `Rues` vide est une mesure (aucune route encore), jamais une absence.
    public sealed class PlanLu
    {
        public long CellId { get; }
        public long Tick { get; }
        public IReadOnlyList<RueDuPlan> Rues { get; }

        public PlanLu(long cellId, long tick, IList<RueDuPlan> rues)
        {
            if (rues == null) throw new ArgumentNullException(nameof(rues));
            CellId = cellId;
            Tick = tick;
            Rues = new ReadOnlyCollection<RueDuPlan>(new List<RueDuPlan>(rues));
        }
    }

    // Soit un plan, soit une absence qui nomme sa cause : jamais les deux, jamais aucun.
    public sealed class LecturePlan
    {
        public PlanLu Plan { get; }
        public string Absence { get; }
        public bool Presente => Plan != null;

        private LecturePlan(PlanLu plan, string absence) { Plan = plan; Absence = absence; }

        public static LecturePlan De(PlanLu plan) =>
            new LecturePlan(plan ?? throw new ArgumentNullException(nameof(plan)), null);

        public static LecturePlan Absent(string cause) =>
            new LecturePlan(null, string.IsNullOrEmpty(cause) ? throw new ArgumentException("une absence nomme sa cause", nameof(cause)) : cause);
    }

    // Demande le plan d'une cellule au service local (`GET /plan?cell=<cell_id>` sur 127.0.0.1).
    // Ne lève jamais pour une cause du service : elle devient une absence déclarée.
    // Une rue mal formée refuse tout le plan : aucun plan partiel n'est rendu.
    public sealed class ClientPlan : IDisposable
    {
        private const string Hote = "127.0.0.1";
        private readonly int port;
        private readonly TimeSpan delai;
        private readonly HttpClient http;

        public ClientPlan(int port, TimeSpan delai)
        {
            if (port < 1 || port > 65535) throw new ArgumentOutOfRangeException(nameof(port), port, "port hors de 1..65535");
            if (delai <= TimeSpan.Zero && delai != Timeout.InfiniteTimeSpan)
                throw new ArgumentOutOfRangeException(nameof(delai), delai, "un délai positif attendu");
            this.port = port;
            this.delai = delai;
            // Aucune redirection suivie, et le délai tenu par Lire, comme dans ClientLieu.
            http = new HttpClient(new HttpClientHandler { AllowAutoRedirect = false })
            {
                Timeout = Timeout.InfiniteTimeSpan
            };
        }

        public void Dispose() => http.Dispose();

        public LecturePlan Lire(long cellId)
        {
            string prefixe = "plan " + cellId.ToString(CultureInfo.InvariantCulture) + " : ";
            HttpStatusCode statut;
            string corps;
            using (var minuterie = new CancellationTokenSource())
            {
                try
                {
                    string url = "http://" + Hote + ":" + port.ToString(CultureInfo.InvariantCulture)
                        + "/plan?cell=" + cellId.ToString(CultureInfo.InvariantCulture);
                    minuterie.CancelAfter(delai);
                    using (HttpResponseMessage reponse = http.GetAsync(url, minuterie.Token).GetAwaiter().GetResult())
                    {
                        statut = reponse.StatusCode;
                        corps = Encoding.UTF8.GetString(reponse.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult());
                    }
                }
                catch (Exception erreur)
                {
                    // Seule la minuterie dit si le délai est échu : le runtime rend l'annulation sous plusieurs formes.
                    if (minuterie.IsCancellationRequested)
                        return LecturePlan.Absent(prefixe + "délai dépassé (" + delai.TotalMilliseconds.ToString(CultureInfo.InvariantCulture) + " ms) sur " + Hote + ":" + port);
                    return LecturePlan.Absent(prefixe + "service absent sur " + Hote + ":" + port + " (" + erreur.GetBaseException().Message + ")");
                }
            }

            if (statut != HttpStatusCode.OK)
                return LecturePlan.Absent(prefixe + "statut " + (int)statut + " pour cell_id " + cellId + ", corps reçu : " + corps);

            Dictionary<string, object> objet;
            try { objet = LecteurJson.LireObjet(corps); }
            catch (ErreurJson erreur)
            {
                return LecturePlan.Absent(prefixe + "JSON invalide à la position " + erreur.Position + " (" + erreur.Message + ")");
            }

            try
            {
                long relu = Entier(Valeur(objet, "cell_id", "cell_id"), "cell_id", long.MinValue);
                if (relu != cellId)
                    return LecturePlan.Absent(prefixe + "le service a rendu cell_id " + relu + " pour cell_id " + cellId + " demandé");
                long tick = Entier(Valeur(objet, "tick", "tick"), "tick", long.MinValue);
                List<object> tableau = Tableau(Valeur(objet, "rues", "rues"), "rues");
                var rues = new List<RueDuPlan>(tableau.Count);
                for (int i = 0; i < tableau.Count; i++)
                    rues.Add(Rue(tableau[i], "rues[" + i.ToString(CultureInfo.InvariantCulture) + "]"));
                return LecturePlan.De(new PlanLu(relu, tick, rues));
            }
            catch (CleRefusee refus)
            {
                return LecturePlan.Absent(prefixe + refus.Message);
            }
        }

        private static RueDuPlan Rue(object valeur, string chemin)
        {
            var rue = valeur as Dictionary<string, object>
                ?? throw new CleRefusee("clé " + chemin + " : un objet attendu, reçu " + Decrire(valeur));

            long identifiant = Entier(Valeur(rue, "identifiant", chemin + ".identifiant"), chemin + ".identifiant", 0);

            string cheminPoints = chemin + ".points";
            List<object> brut = Tableau(Valeur(rue, "points", cheminPoints), cheminPoints);
            if (brut.Count < 2)
                throw new CleRefusee("clé " + cheminPoints + " : au moins 2 points attendus, reçu " + brut.Count);
            var points = new List<PointLocal>(brut.Count);
            for (int j = 0; j < brut.Count; j++)
            {
                string cheminPoint = cheminPoints + "[" + j.ToString(CultureInfo.InvariantCulture) + "]";
                if (!(brut[j] is List<object> paire) || paire.Count != 2)
                    throw new CleRefusee("clé " + cheminPoint + " : un tableau de exactement 2 nombres attendu, reçu " + Decrire(brut[j]));
                points.Add(new PointLocal(Nombre(paire[0], cheminPoint), Nombre(paire[1], cheminPoint)));
            }

            string cheminLargeur = chemin + ".largeur_m";
            double largeur = Nombre(Valeur(rue, "largeur_m", cheminLargeur), cheminLargeur);
            if (!(largeur > 0))
                throw new CleRefusee("clé " + cheminLargeur + " : une largeur > 0 attendue, reçu " + largeur.ToString("R", CultureInfo.InvariantCulture));

            // Jamais `false` par défaut : une rue qui ne dit pas si elle est en chantier refuse le plan.
            string cheminChantier = chemin + ".en_chantier";
            object chantier = Valeur(rue, "en_chantier", cheminChantier);
            if (!(chantier is bool enChantier))
                throw new CleRefusee("clé " + cheminChantier + " : un booléen attendu, reçu " + Decrire(chantier));

            return new RueDuPlan(identifiant, points, largeur, enChantier);
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

        private static List<object> Tableau(object valeur, string chemin) =>
            valeur as List<object> ?? throw new CleRefusee("clé " + chemin + " : un tableau attendu, reçu " + Decrire(valeur));

        private static double Nombre(object valeur, string chemin) =>
            valeur is double nombre ? nombre : throw new CleRefusee("clé " + chemin + " : un nombre attendu, reçu " + Decrire(valeur));

        private static long Entier(object valeur, string chemin, long min)
        {
            double nombre = Nombre(valeur, chemin);
            // Dès 2^53 un double ne dit plus quel entier le texte portait : la borne est refusée plutôt que devinée.
            if (nombre != Math.Floor(nombre) || Math.Abs(nombre) >= 9007199254740992.0 || nombre < min)
                throw new CleRefusee("clé " + chemin + " : un entier" + (min == 0 ? " ≥ 0" : "") + " attendu, reçu " + nombre.ToString("R", CultureInfo.InvariantCulture));
            return (long)nombre;
        }

        private static string Decrire(object valeur) =>
            valeur == null ? "null" : valeur is string texte ? "le texte \"" + texte + "\"" : valeur.GetType().Name;
    }
}
