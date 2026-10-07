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

        public PolygoneDeCarte(IList<PointCarte> exterieur, IList<IList<PointCarte>> trous)
        {
            if (exterieur == null) throw new ArgumentNullException(nameof(exterieur));
            if (trous == null) throw new ArgumentNullException(nameof(trous));
            Exterieur = new ReadOnlyCollection<PointCarte>(new List<PointCarte>(exterieur));
            var copies = new List<IReadOnlyList<PointCarte>>(trous.Count);
            foreach (IList<PointCarte> trou in trous)
                copies.Add(new ReadOnlyCollection<PointCarte>(new List<PointCarte>(trou ?? throw new ArgumentNullException(nameof(trous)))));
            Trous = new ReadOnlyCollection<IReadOnlyList<PointCarte>>(copies);
        }
    }

    // Une puissance ou une maison, telle que le monde la nomme.
    public sealed class IdentiteDeCarte
    {
        public long Id { get; }
        public string Nom { get; }

        public IdentiteDeCarte(long id, string nom)
        {
            Id = id;
            Nom = nom ?? throw new ArgumentNullException(nameof(nom));
        }
    }

    public sealed class VilleDeCarte
    {
        public string Nom { get; }
        public long Population { get; }
        public PointCarte Position { get; }

        public VilleDeCarte(string nom, long population, PointCarte position)
        {
            Nom = nom ?? throw new ArgumentNullException(nameof(nom));
            Population = population;
            Position = position;
        }
    }

    // Une cellule de la carte de 1400. `Puissance` ou `Maison` nulle est une mesure : le service a servi `null`.
    public sealed class CelluleDeCarte
    {
        public long CellId { get; }
        public IReadOnlyList<PolygoneDeCarte> Contour { get; }
        public IdentiteDeCarte Puissance { get; }
        public IdentiteDeCarte Maison { get; }
        public IReadOnlyList<VilleDeCarte> Villes { get; }

        public CelluleDeCarte(long cellId, IList<PolygoneDeCarte> contour, IdentiteDeCarte puissance, IdentiteDeCarte maison, IList<VilleDeCarte> villes)
        {
            if (contour == null) throw new ArgumentNullException(nameof(contour));
            if (villes == null) throw new ArgumentNullException(nameof(villes));
            CellId = cellId;
            Contour = new ReadOnlyCollection<PolygoneDeCarte>(new List<PolygoneDeCarte>(contour));
            Puissance = puissance;
            Maison = maison;
            Villes = new ReadOnlyCollection<VilleDeCarte>(new List<VilleDeCarte>(villes));
        }
    }

    // La carte servie, ses cellules dans l'ordre de la réponse.
    public sealed class CarteLue
    {
        public long CellCount { get; }
        public IReadOnlyList<CelluleDeCarte> Cellules { get; }

        public CarteLue(long cellCount, IList<CelluleDeCarte> cellules)
        {
            if (cellules == null) throw new ArgumentNullException(nameof(cellules));
            CellCount = cellCount;
            Cellules = new ReadOnlyCollection<CelluleDeCarte>(new List<CelluleDeCarte>(cellules));
        }
    }

    // Soit une carte, soit une absence qui nomme sa cause : jamais les deux, jamais aucune.
    public sealed class LectureCarte
    {
        public CarteLue Carte { get; }
        public string Absence { get; }
        public bool Presente => Carte != null;

        private LectureCarte(CarteLue carte, string absence) { Carte = carte; Absence = absence; }

        public static LectureCarte De(CarteLue carte) =>
            new LectureCarte(carte ?? throw new ArgumentNullException(nameof(carte)), null);

        public static LectureCarte Absent(string cause) =>
            new LectureCarte(null, string.IsNullOrEmpty(cause) ? throw new ArgumentException("une absence nomme sa cause", nameof(cause)) : cause);
    }

    // Demande la carte de 1400 au service local (`GET /carte` sur 127.0.0.1).
    // Ne lève jamais pour une cause du service : elle devient une absence déclarée.
    // Une seule clé fautive refuse toute la carte : aucune carte partielle n'est rendue.
    public sealed class ClientCarte : IDisposable
    {
        // La première requête calcule la carte pour toute la partie et prend 1,8 à 2 s :
        // le délai de 2 s des autres lectures n'y suffit pas.
        public static readonly TimeSpan DelaiMinimal = TimeSpan.FromSeconds(10);

        private const string Hote = "127.0.0.1";
        private const string Prefixe = "carte : ";
        private readonly int port;
        private readonly TimeSpan delai;
        private readonly HttpClient http;

        public ClientCarte(int port, TimeSpan delai)
        {
            if (port < 1 || port > 65535) throw new ArgumentOutOfRangeException(nameof(port), port, "port hors de 1..65535");
            // `Timeout.InfiniteTimeSpan` vaut -1 ms : il tombe sous le minimum, comme tout délai trop court.
            if (delai < DelaiMinimal)
                throw new ArgumentOutOfRangeException(nameof(delai), delai, "un délai d'au moins " + DelaiMinimal.TotalSeconds + " s attendu");
            this.port = port;
            this.delai = delai;
            // Aucune redirection suivie, et le délai tenu par Lire, comme dans ClientPlan.
            http = new HttpClient(new HttpClientHandler { AllowAutoRedirect = false })
            {
                Timeout = Timeout.InfiniteTimeSpan
            };
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
                    string url = "http://" + Hote + ":" + port.ToString(CultureInfo.InvariantCulture) + "/carte";
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
                        return LectureCarte.Absent(Prefixe + "délai dépassé (" + delai.TotalMilliseconds.ToString(CultureInfo.InvariantCulture) + " ms) sur " + Hote + ":" + port);
                    return LectureCarte.Absent(Prefixe + "service absent sur " + Hote + ":" + port + " (" + erreur.GetBaseException().Message + ")");
                }
            }

            if (statut != HttpStatusCode.OK)
                return LectureCarte.Absent(Prefixe + "statut " + (int)statut + ", corps reçu : " + corps);

            Dictionary<string, object> objet;
            try { objet = LecteurJson.LireObjet(corps); }
            catch (ErreurJson erreur)
            {
                return LectureCarte.Absent(Prefixe + "JSON invalide à la position " + erreur.Position + " (" + erreur.Message + ")");
            }

            try
            {
                // Les mètres des contours et des villes n'ont de sens que dans cette projection.
                object crs = Valeur(objet, "crs", "crs");
                if (!(crs is string projection && projection == "EPSG:3035"))
                    throw new CleRefusee("clé crs : le texte \"EPSG:3035\" attendu, reçu " + Decrire(crs));

                // Une carte sans cellule n'est pas une mesure.
                List<object> brutes = Tableau(Valeur(objet, "cells", "cells"), "cells");
                if (brutes.Count == 0)
                    throw new CleRefusee("clé cells : au moins une cellule attendue, reçu un tableau vide");
                var cellules = new List<CelluleDeCarte>(brutes.Count);
                var identifiants = new HashSet<long>();
                for (int i = 0; i < brutes.Count; i++)
                    cellules.Add(Cellule(brutes[i], Indice("cells", i), identifiants));

                long annonce = Entier(Valeur(objet, "cell_count", "cell_count"), "cell_count", 0);
                if (annonce != cellules.Count)
                    throw new CleRefusee("clé cell_count : " + annonce + " annoncées, " + cellules.Count + " lues");

                return LectureCarte.De(new CarteLue(annonce, cellules));
            }
            catch (CleRefusee refus)
            {
                return LectureCarte.Absent(Prefixe + refus.Message);
            }
        }

        // `identifiants` : les cell_id déjà lus dans cette carte ; un second refuse la carte.
        private static CelluleDeCarte Cellule(object valeur, string chemin, HashSet<long> identifiants)
        {
            var cellule = valeur as Dictionary<string, object>
                ?? throw new CleRefusee("clé " + chemin + " : un objet attendu, reçu " + Decrire(valeur));

            string cheminId = chemin + ".cell_id";
            long cellId = Entier(Valeur(cellule, "cell_id", cheminId), cheminId, 0);
            if (!identifiants.Add(cellId))
                throw new CleRefusee("clé " + cheminId + " : " + cellId + " déjà lu dans cette carte");

            List<PolygoneDeCarte> contour = Contour(cellule, chemin + ".contour");
            IdentiteDeCarte puissance = Identite(cellule, "puissance", chemin + ".puissance");
            IdentiteDeCarte maison = Identite(cellule, "maison", chemin + ".maison");

            string cheminVilles = chemin + ".villes";
            List<object> brutes = Tableau(Valeur(cellule, "villes", cheminVilles), cheminVilles);
            var villes = new List<VilleDeCarte>(brutes.Count);
            for (int i = 0; i < brutes.Count; i++)
                villes.Add(Ville(brutes[i], Indice(cheminVilles, i)));

            return new CelluleDeCarte(cellId, contour, puissance, maison, villes);
        }

        // Le contour GeoJSON : un MultiPolygon d'au moins un polygone, chacun d'au moins un anneau.
        private static List<PolygoneDeCarte> Contour(Dictionary<string, object> cellule, string chemin)
        {
            object brut = Valeur(cellule, "contour", chemin);
            var contour = brut as Dictionary<string, object>
                ?? throw new CleRefusee("clé " + chemin + " : un objet attendu, reçu " + Decrire(brut));

            string cheminType = chemin + ".type";
            object type = Valeur(contour, "type", cheminType);
            if (!(type is string texte && texte == "MultiPolygon"))
                throw new CleRefusee("clé " + cheminType + " : le texte \"MultiPolygon\" attendu, reçu " + Decrire(type));

            string cheminCoordonnees = chemin + ".coordinates";
            List<object> polygones = Tableau(Valeur(contour, "coordinates", cheminCoordonnees), cheminCoordonnees);
            if (polygones.Count == 0)
                throw new CleRefusee("clé " + cheminCoordonnees + " : au moins un polygone attendu, reçu 0");
            var lus = new List<PolygoneDeCarte>(polygones.Count);
            for (int i = 0; i < polygones.Count; i++)
            {
                string cheminPolygone = Indice(cheminCoordonnees, i);
                List<object> anneaux = Tableau(polygones[i], cheminPolygone);
                if (anneaux.Count == 0)
                    throw new CleRefusee("clé " + cheminPolygone + " : au moins un anneau attendu, reçu 0");
                var trous = new List<IList<PointCarte>>(anneaux.Count - 1);
                for (int j = 1; j < anneaux.Count; j++)
                    trous.Add(Anneau(anneaux[j], Indice(cheminPolygone, j)));
                lus.Add(new PolygoneDeCarte(Anneau(anneaux[0], Indice(cheminPolygone, 0)), trous));
            }
            return lus;
        }

        // Un anneau : au moins 4 points de exactement 2 nombres, le dernier égal au premier.
        private static List<PointCarte> Anneau(object valeur, string chemin)
        {
            List<object> brut = Tableau(valeur, chemin);
            if (brut.Count < 4)
                throw new CleRefusee("clé " + chemin + " : au moins 4 points attendus, reçu " + brut.Count);
            var points = new List<PointCarte>(brut.Count);
            for (int k = 0; k < brut.Count; k++)
            {
                string cheminPoint = Indice(chemin, k);
                if (!(brut[k] is List<object> paire) || paire.Count != 2)
                    throw new CleRefusee("clé " + cheminPoint + " : un tableau de exactement 2 nombres attendu, reçu " + Decrire(brut[k]));
                points.Add(new PointCarte(Nombre(paire[0], cheminPoint), Nombre(paire[1], cheminPoint)));
            }
            PointCarte premier = points[0], dernier = points[points.Count - 1];
            if (premier.X != dernier.X || premier.Y != dernier.Y)
                throw new CleRefusee("clé " + chemin + " : un anneau fermé attendu (dernier point égal au premier)");
            return points;
        }

        // La clé est toujours présente : `null` dit que la cellule n'en a pas, une clé absente refuse la carte.
        private static IdentiteDeCarte Identite(Dictionary<string, object> cellule, string cle, string chemin)
        {
            object valeur = Valeur(cellule, cle, chemin);
            if (valeur == null) return null;
            var identite = valeur as Dictionary<string, object>
                ?? throw new CleRefusee("clé " + chemin + " : null ou un objet attendu, reçu " + Decrire(valeur));
            long id = Entier(Valeur(identite, "id", chemin + ".id"), chemin + ".id", 0);
            return new IdentiteDeCarte(id, Texte(identite, "nom", chemin + ".nom"));
        }

        private static VilleDeCarte Ville(object valeur, string chemin)
        {
            var ville = valeur as Dictionary<string, object>
                ?? throw new CleRefusee("clé " + chemin + " : un objet attendu, reçu " + Decrire(valeur));
            string nom = Texte(ville, "nom", chemin + ".nom");
            long population = Entier(Valeur(ville, "population", chemin + ".population"), chemin + ".population", 0);
            double x = Nombre(Valeur(ville, "x_m", chemin + ".x_m"), chemin + ".x_m");
            double y = Nombre(Valeur(ville, "y_m", chemin + ".y_m"), chemin + ".y_m");
            return new VilleDeCarte(nom, population, new PointCarte(x, y));
        }

        private static string Texte(Dictionary<string, object> objet, string cle, string chemin)
        {
            object brute = Valeur(objet, cle, chemin);
            if (!(brute is string texte) || string.IsNullOrWhiteSpace(texte))
                throw new CleRefusee("clé " + chemin + " : un texte non vide attendu, reçu " + Decrire(brute));
            return texte;
        }

        private static string Indice(string chemin, int i) => chemin + "[" + i.ToString(CultureInfo.InvariantCulture) + "]";

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
