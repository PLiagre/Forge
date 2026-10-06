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

    // Une parcelle telle que `sim/` la tient : contour en mètres locaux, chantier et travail relus tels quels.
    public sealed class ParcelleDuPlan
    {
        public long Identifiant { get; }
        public IReadOnlyList<PointLocal> Contour { get; }
        public bool EnChantier { get; }
        public long TravailRequis { get; }
        public long TravailFourni { get; }

        public ParcelleDuPlan(long identifiant, IList<PointLocal> contour, bool enChantier, long travailRequis, long travailFourni)
        {
            if (contour == null) throw new ArgumentNullException(nameof(contour));
            Identifiant = identifiant;
            Contour = new ReadOnlyCollection<PointLocal>(new List<PointLocal>(contour));
            EnChantier = enChantier;
            TravailRequis = travailRequis;
            TravailFourni = travailFourni;
        }
    }

    // Un bâtiment tel que `sim/` le tient, posé sur la parcelle `Parcelle` du même plan.
    // `Nature` n'est pas bornée : un bâtiment ancien peut porter un autre texte que maison, scierie ou four.
    public sealed class BatimentDuPlan
    {
        public long Identifiant { get; }
        public long Parcelle { get; }
        public string Nature { get; }
        public IReadOnlyList<PointLocal> Emprise { get; }
        public bool EnChantier { get; }
        public long TravailRequis { get; }
        public long TravailFourni { get; }

        public BatimentDuPlan(long identifiant, long parcelle, string nature, IList<PointLocal> emprise,
            bool enChantier, long travailRequis, long travailFourni)
        {
            if (nature == null) throw new ArgumentNullException(nameof(nature));
            if (emprise == null) throw new ArgumentNullException(nameof(emprise));
            Identifiant = identifiant;
            Parcelle = parcelle;
            Nature = nature;
            Emprise = new ReadOnlyCollection<PointLocal>(new List<PointLocal>(emprise));
            EnChantier = enChantier;
            TravailRequis = travailRequis;
            TravailFourni = travailFourni;
        }
    }

    // Le plan d'une cellule à un tick. Une liste vide (aucune rue, parcelle ou bâtiment encore)
    // est une mesure, jamais une absence.
    public sealed class PlanLu
    {
        public long CellId { get; }
        public long Tick { get; }
        public IReadOnlyList<RueDuPlan> Rues { get; }
        public IReadOnlyList<ParcelleDuPlan> Parcelles { get; }
        public IReadOnlyList<BatimentDuPlan> Batiments { get; }

        public PlanLu(long cellId, long tick, IList<RueDuPlan> rues, IList<ParcelleDuPlan> parcelles, IList<BatimentDuPlan> batiments)
        {
            if (rues == null) throw new ArgumentNullException(nameof(rues));
            if (parcelles == null) throw new ArgumentNullException(nameof(parcelles));
            if (batiments == null) throw new ArgumentNullException(nameof(batiments));
            CellId = cellId;
            Tick = tick;
            Rues = new ReadOnlyCollection<RueDuPlan>(new List<RueDuPlan>(rues));
            Parcelles = new ReadOnlyCollection<ParcelleDuPlan>(new List<ParcelleDuPlan>(parcelles));
            Batiments = new ReadOnlyCollection<BatimentDuPlan>(new List<BatimentDuPlan>(batiments));
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
    // Une rue, une parcelle ou un bâtiment mal formé refuse tout le plan : aucun plan partiel n'est rendu.
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

                List<object> brutesParcelles = Tableau(Valeur(objet, "parcelles", "parcelles"), "parcelles");
                var parcelles = new List<ParcelleDuPlan>(brutesParcelles.Count);
                var identifiantsParcelles = new HashSet<long>();
                for (int i = 0; i < brutesParcelles.Count; i++)
                {
                    ParcelleDuPlan parcelle = Parcelle(brutesParcelles[i], "parcelles[" + i.ToString(CultureInfo.InvariantCulture) + "]");
                    parcelles.Add(parcelle);
                    identifiantsParcelles.Add(parcelle.Identifiant);
                }

                List<object> brutsBatiments = Tableau(Valeur(objet, "batiments", "batiments"), "batiments");
                var batiments = new List<BatimentDuPlan>(brutsBatiments.Count);
                for (int i = 0; i < brutsBatiments.Count; i++)
                    batiments.Add(Batiment(brutsBatiments[i], "batiments[" + i.ToString(CultureInfo.InvariantCulture) + "]", identifiantsParcelles));

                return LecturePlan.De(new PlanLu(relu, tick, rues, parcelles, batiments));
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

        private static ParcelleDuPlan Parcelle(object valeur, string chemin)
        {
            var parcelle = valeur as Dictionary<string, object>
                ?? throw new CleRefusee("clé " + chemin + " : un objet attendu, reçu " + Decrire(valeur));

            long identifiant = Entier(Valeur(parcelle, "identifiant", chemin + ".identifiant"), chemin + ".identifiant", 0);
            List<PointLocal> contour = Contour(parcelle, "contour", chemin + ".contour");
            Chantier(parcelle, chemin, out bool enChantier, out long requis, out long fourni);
            return new ParcelleDuPlan(identifiant, contour, enChantier, requis, fourni);
        }

        // `parcelles` : les identifiants des parcelles lues dans ce plan ; un bâtiment posé ailleurs refuse le plan.
        private static BatimentDuPlan Batiment(object valeur, string chemin, HashSet<long> parcelles)
        {
            var batiment = valeur as Dictionary<string, object>
                ?? throw new CleRefusee("clé " + chemin + " : un objet attendu, reçu " + Decrire(valeur));

            long identifiant = Entier(Valeur(batiment, "identifiant", chemin + ".identifiant"), chemin + ".identifiant", 0);

            string cheminParcelle = chemin + ".parcelle";
            long parcelle = Entier(Valeur(batiment, "parcelle", cheminParcelle), cheminParcelle, 0);
            if (!parcelles.Contains(parcelle))
                throw new CleRefusee("clé " + cheminParcelle + " : aucune parcelle " + parcelle + " dans ce plan");

            string cheminNature = chemin + ".nature";
            object brute = Valeur(batiment, "nature", cheminNature);
            if (!(brute is string nature) || string.IsNullOrWhiteSpace(nature))
                throw new CleRefusee("clé " + cheminNature + " : un texte non vide attendu, reçu " + Decrire(brute));

            List<PointLocal> emprise = Contour(batiment, "emprise", chemin + ".emprise");
            Chantier(batiment, chemin, out bool enChantier, out long requis, out long fourni);
            return new BatimentDuPlan(identifiant, parcelle, nature, emprise, enChantier, requis, fourni);
        }

        // Le contour d'une parcelle ou l'emprise d'un bâtiment : au moins 3 points de exactement 2 nombres.
        private static List<PointLocal> Contour(Dictionary<string, object> objet, string cle, string chemin)
        {
            List<object> brut = Tableau(Valeur(objet, cle, chemin), chemin);
            if (brut.Count < 3)
                throw new CleRefusee("clé " + chemin + " : au moins 3 points attendus, reçu " + brut.Count);
            var points = new List<PointLocal>(brut.Count);
            for (int j = 0; j < brut.Count; j++)
            {
                string cheminPoint = chemin + "[" + j.ToString(CultureInfo.InvariantCulture) + "]";
                if (!(brut[j] is List<object> paire) || paire.Count != 2)
                    throw new CleRefusee("clé " + cheminPoint + " : un tableau de exactement 2 nombres attendu, reçu " + Decrire(brut[j]));
                points.Add(new PointLocal(Nombre(paire[0], cheminPoint), Nombre(paire[1], cheminPoint)));
            }
            return points;
        }

        // Jamais `false` par défaut, et un chantier qui contredit son travail refuse le plan :
        // les vues n'ont pas à choisir entre `en_chantier` et le travail restant.
        private static void Chantier(Dictionary<string, object> objet, string chemin, out bool enChantier, out long requis, out long fourni)
        {
            string cheminChantier = chemin + ".en_chantier";
            object chantier = Valeur(objet, "en_chantier", cheminChantier);
            if (!(chantier is bool booleen))
                throw new CleRefusee("clé " + cheminChantier + " : un booléen attendu, reçu " + Decrire(chantier));

            string cheminRequis = chemin + ".travail_requis";
            requis = Entier(Valeur(objet, "travail_requis", cheminRequis), cheminRequis, 0);
            string cheminFourni = chemin + ".travail_fourni";
            fourni = Entier(Valeur(objet, "travail_fourni", cheminFourni), cheminFourni, 0);

            if (fourni > requis)
                throw new CleRefusee("clé " + cheminFourni + " : " + fourni + " dépasse le travail requis " + requis);
            if (booleen != (fourni < requis))
                throw new CleRefusee("clé " + cheminChantier + " : " + (booleen ? "true" : "false")
                    + " contredit le travail restant (" + fourni + " fourni sur " + requis + " requis)");
            enChantier = booleen;
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
