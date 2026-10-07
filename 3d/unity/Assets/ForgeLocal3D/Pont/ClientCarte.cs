using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Text;
using System.Threading;

namespace Forge.Pont
{
    // Un point de la carte, en mètres EPSG:3035, relu tel quel : ni origine ni conversion.
    public readonly struct PointCarte
    {
        public double X { get; }
        public double Y { get; }
        public PointCarte(double x, double y) { X = x; Y = y; }
    }

    // Un polygone GeoJSON : l'anneau extérieur puis ses trous, gardés fermés comme servis.
    public sealed class PolygoneDeCarte
    {
        public IReadOnlyList<PointCarte> Exterieur { get; }
        public IReadOnlyList<IReadOnlyList<PointCarte>> Trous { get; }
        public PolygoneDeCarte(IEnumerable<PointCarte> exterieur, IEnumerable<IEnumerable<PointCarte>> trous)
        {
            Exterieur = ClientCarte.Copier(exterieur, nameof(exterieur));
            Trous = ClientCarte.Copier(ClientCarte.Copier(trous, nameof(trous)).Select(t => (IReadOnlyList<PointCarte>)ClientCarte.Copier(t, nameof(trous))), nameof(trous));
        }
    }

    // Une puissance ou une maison, telle que le monde la nomme.
    public sealed class IdentiteDeCarte
    {
        public long Id { get; }
        public string Nom { get; }
        public IdentiteDeCarte(long id, string nom) { Id = id; Nom = nom ?? throw new ArgumentNullException(nameof(nom)); }
    }

    public sealed class VilleDeCarte
    {
        public string Nom { get; }
        public long Population { get; }
        public PointCarte Position { get; }
        public VilleDeCarte(string nom, long population, PointCarte position) { Nom = nom ?? throw new ArgumentNullException(nameof(nom)); Population = population; Position = position; }
    }

    // Une cellule de la carte de 1400. `Puissance` ou `Maison` nulle est une mesure : le service a servi `null`.
    public sealed class CelluleDeCarte
    {
        public long CellId { get; }
        public IReadOnlyList<PolygoneDeCarte> Contour { get; }
        public IdentiteDeCarte Puissance { get; }
        public IdentiteDeCarte Maison { get; }
        public IReadOnlyList<VilleDeCarte> Villes { get; }
        public CelluleDeCarte(long cellId, IEnumerable<PolygoneDeCarte> contour, IdentiteDeCarte puissance, IdentiteDeCarte maison, IEnumerable<VilleDeCarte> villes)
        {
            CellId = cellId;
            Contour = ClientCarte.Copier(contour, nameof(contour));
            Puissance = puissance;
            Maison = maison;
            Villes = ClientCarte.Copier(villes, nameof(villes));
        }
    }

    // La carte servie, ses cellules dans l'ordre de la réponse.
    public sealed class CarteLue
    {
        public long CellCount { get; }
        public IReadOnlyList<CelluleDeCarte> Cellules { get; }
        public CarteLue(long cellCount, IEnumerable<CelluleDeCarte> cellules) { CellCount = cellCount; Cellules = ClientCarte.Copier(cellules, nameof(cellules)); }
    }

    // Soit une carte, soit une absence qui nomme sa cause : jamais les deux, jamais aucune.
    public sealed class LectureCarte
    {
        public CarteLue Carte { get; }
        public string Absence { get; }
        public bool Presente => Carte != null;
        private LectureCarte(CarteLue carte, string absence) { Carte = carte; Absence = absence; }
        public static LectureCarte De(CarteLue carte) => new LectureCarte(carte ?? throw new ArgumentNullException(nameof(carte)), null);
        public static LectureCarte Absent(string cause) =>
            new LectureCarte(null, string.IsNullOrEmpty(cause) ? throw new ArgumentException("une absence nomme sa cause", nameof(cause)) : cause);
    }

    // Demande la carte de 1400 au service local (`GET /carte` sur 127.0.0.1).
    // Ne lève jamais pour une cause du service : elle devient une absence déclarée.
    // Une seule clé fautive refuse toute la carte, en nommant son chemin : aucune carte partielle n'est rendue.
    public sealed class ClientCarte : IDisposable
    {
        // La première requête calcule la carte pour toute la partie et prend 1,8 à 2 s :
        // le délai de 2 s des autres lectures n'y suffit pas.
        public static readonly TimeSpan DelaiMinimal = TimeSpan.FromSeconds(10);
        private const string Hote = "127.0.0.1", Prefixe = "carte : ";
        private readonly int port;
        private readonly TimeSpan delai;
        private readonly HttpClient http;

        public ClientCarte(int port, TimeSpan delai)
        {
            if (port < 1 || port > 65535) throw new ArgumentOutOfRangeException(nameof(port), port, "port hors de 1..65535");
            // `Timeout.InfiniteTimeSpan` vaut -1 ms : il tombe sous le minimum, comme tout délai trop court.
            if (delai < DelaiMinimal) throw new ArgumentOutOfRangeException(nameof(delai), delai, "un délai d'au moins " + DelaiMinimal.TotalSeconds + " s attendu");
            this.port = port;
            this.delai = delai;
            // Aucune redirection suivie, et le délai tenu par Lire, comme dans ClientPlan.
            http = new HttpClient(new HttpClientHandler { AllowAutoRedirect = false }) { Timeout = Timeout.InfiniteTimeSpan };
        }

        public void Dispose() => http.Dispose();

        public LectureCarte Lire()
        {
            HttpStatusCode statut;
            string corps;
            using (var minuterie = new CancellationTokenSource())
            {
                try
                {
                    minuterie.CancelAfter(delai);
                    using (HttpResponseMessage reponse = http.GetAsync("http://" + Hote + ":" + port.ToString(CultureInfo.InvariantCulture) + "/carte", minuterie.Token).GetAwaiter().GetResult())
                    {
                        statut = reponse.StatusCode;
                        corps = Encoding.UTF8.GetString(reponse.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult());
                    }
                }
                catch (Exception erreur)
                {
                    // Seule la minuterie dit si le délai est échu : le runtime rend l'annulation sous plusieurs formes.
                    if (minuterie.IsCancellationRequested)
                        return LectureCarte.Absent(Prefixe + "délai dépassé (" + delai.TotalMilliseconds.ToString(CultureInfo.InvariantCulture) + " ms) sur " + Hote + ":" + port);
                    return LectureCarte.Absent(Prefixe + "service absent sur " + Hote + ":" + port + " (" + erreur.GetBaseException().Message + ")");
                }
            }
            if (statut != HttpStatusCode.OK) return LectureCarte.Absent(Prefixe + "statut " + (int)statut + ", corps reçu : " + corps);
            try { return LectureCarte.De(Carte(LecteurJson.LireObjet(corps))); }
            catch (ErreurJson erreur) { return LectureCarte.Absent(Prefixe + "JSON invalide à la position " + erreur.Position + " (" + erreur.Message + ")"); }
            catch (CleRefusee refus) { return LectureCarte.Absent(Prefixe + refus.Message); }
        }

        internal static ReadOnlyCollection<T> Copier<T>(IEnumerable<T> liste, string nom) => new ReadOnlyCollection<T>(new List<T>(liste ?? throw new ArgumentNullException(nom)));

        private static CarteLue Carte(Dictionary<string, object> racine)
        {
            // Les mètres des contours et des villes n'ont de sens que dans cette projection ; une carte sans cellule n'est pas une mesure.
            if (!"EPSG:3035".Equals(Valeur(racine, "crs"))) throw Refus("crs", "le texte \"EPSG:3035\"", racine["crs"]);
            var identifiants = new HashSet<long>();
            List<CelluleDeCarte> cellules = Liste(Valeur(racine, "cells"), "cells", 1, (brute, chemin) => Cellule(brute, chemin, identifiants));
            long annonce = Entier(racine, "cell_count");
            if (annonce != cellules.Count) throw new CleRefusee("clé cell_count : " + annonce + " annoncées, " + cellules.Count + " lues");
            return new CarteLue(annonce, cellules);
        }

        // `identifiants` : les cell_id déjà lus dans cette carte ; un second refuse la carte.
        private static CelluleDeCarte Cellule(object valeur, string chemin, HashSet<long> identifiants)
        {
            Dictionary<string, object> cellule = Objet(valeur, chemin), contour = Objet(Valeur(cellule, chemin + ".contour"), chemin + ".contour");
            long cellId = Entier(cellule, chemin + ".cell_id");
            if (!identifiants.Add(cellId)) throw new CleRefusee("clé " + chemin + ".cell_id : " + cellId + " déjà lu dans cette carte");
            if (!"MultiPolygon".Equals(Valeur(contour, chemin + ".contour.type"))) throw Refus(chemin + ".contour.type", "le texte \"MultiPolygon\"", contour["type"]);
            // Au moins un polygone, chacun d'au moins un anneau : l'extérieur, puis les trous.
            List<PolygoneDeCarte> polygones = Liste(Valeur(contour, chemin + ".contour.coordinates"), chemin + ".contour.coordinates", 1, (brut, cheminPolygone) =>
            {
                List<List<PointCarte>> anneaux = Liste(brut, cheminPolygone, 1, Anneau);
                return new PolygoneDeCarte(anneaux[0], anneaux.Skip(1));
            });
            List<VilleDeCarte> villes = Liste(Valeur(cellule, chemin + ".villes"), chemin + ".villes", 0, Ville);
            return new CelluleDeCarte(cellId, polygones, Identite(cellule, chemin + ".puissance"), Identite(cellule, chemin + ".maison"), villes);
        }

        // Un anneau : au moins 4 points de exactement 2 nombres, le dernier égal au premier.
        private static List<PointCarte> Anneau(object valeur, string chemin)
        {
            List<PointCarte> points = Liste(valeur, chemin, 4, (brut, cheminPoint) =>
            {
                if (!(brut is List<object> paire) || paire.Count != 2) throw Refus(cheminPoint, "un tableau de exactement 2 nombres", brut);
                return new PointCarte(Nombre(paire[0], cheminPoint), Nombre(paire[1], cheminPoint));
            });
            if (points[0].X != points[points.Count - 1].X || points[0].Y != points[points.Count - 1].Y)
                throw new CleRefusee("clé " + chemin + " : un anneau fermé attendu (dernier point égal au premier)");
            return points;
        }

        // La clé est toujours présente : `null` dit que la cellule n'en a pas, une clé absente refuse la carte.
        private static IdentiteDeCarte Identite(Dictionary<string, object> cellule, string chemin)
        {
            object valeur = Valeur(cellule, chemin);
            if (valeur == null) return null;
            var identite = valeur as Dictionary<string, object> ?? throw Refus(chemin, "null ou un objet", valeur);
            return new IdentiteDeCarte(Entier(identite, chemin + ".id"), Texte(identite, chemin + ".nom"));
        }

        private static VilleDeCarte Ville(object valeur, string chemin)
        {
            Dictionary<string, object> ville = Objet(valeur, chemin);
            var position = new PointCarte(Nombre(Valeur(ville, chemin + ".x_m"), chemin + ".x_m"), Nombre(Valeur(ville, chemin + ".y_m"), chemin + ".y_m"));
            return new VilleDeCarte(Texte(ville, chemin + ".nom"), Entier(ville, chemin + ".population"), position);
        }

        private sealed class CleRefusee : Exception { public CleRefusee(string message) : base(message) { } }

        private static CleRefusee Refus(string chemin, string attendu, object recu) => new CleRefusee("clé " + chemin + " : " + attendu + " attendu, reçu " + Decrire(recu));

        // La clé lue est le dernier segment du chemin pointé : `cells[1].contour` lit `contour`.
        private static object Valeur(Dictionary<string, object> objet, string chemin) =>
            objet.TryGetValue(chemin.Substring(chemin.LastIndexOf('.') + 1), out object valeur) ? valeur : throw new CleRefusee("clé absente : " + chemin);

        private static Dictionary<string, object> Objet(object valeur, string chemin) => valeur as Dictionary<string, object> ?? throw Refus(chemin, "un objet", valeur);

        // Un tableau d'au moins `min` éléments, chacun lu avec son chemin indicé.
        private static List<T> Liste<T>(object valeur, string chemin, int min, Func<object, string, T> lire)
        {
            var tableau = valeur as List<object> ?? throw Refus(chemin, "un tableau", valeur);
            if (tableau.Count < min) throw new CleRefusee("clé " + chemin + " : au moins " + min + (min > 1 ? " éléments attendus" : " élément attendu") + ", reçu " + tableau.Count);
            return tableau.Select((brute, i) => lire(brute, chemin + "[" + i.ToString(CultureInfo.InvariantCulture) + "]")).ToList();
        }

        private static string Texte(Dictionary<string, object> objet, string chemin)
        {
            object brute = Valeur(objet, chemin);
            return brute is string texte && !string.IsNullOrWhiteSpace(texte) ? texte : throw Refus(chemin, "un texte non vide", brute);
        }

        private static double Nombre(object valeur, string chemin) => valeur is double nombre ? nombre : throw Refus(chemin, "un nombre", valeur);

        // Un entier ≥ 0. Dès 2^53 un double ne dit plus quel entier le texte portait : la borne est refusée plutôt que devinée.
        private static long Entier(Dictionary<string, object> objet, string chemin)
        {
            double nombre = Nombre(Valeur(objet, chemin), chemin);
            if (nombre != Math.Floor(nombre) || nombre < 0 || nombre >= 9007199254740992.0)
                throw new CleRefusee("clé " + chemin + " : un entier ≥ 0 attendu, reçu " + nombre.ToString("R", CultureInfo.InvariantCulture));
            return (long)nombre;
        }

        private static string Decrire(object valeur) => valeur == null ? "null" : valeur is string texte ? "le texte \"" + texte + "\"" : valeur.GetType().Name;
    }
}
