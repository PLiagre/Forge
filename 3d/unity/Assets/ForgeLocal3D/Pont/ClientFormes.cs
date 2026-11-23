using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Text;
using System.Threading;

namespace Forge.Pont
{
    // Le contour d'un lieu : son rang dans la cellule (0 est le bourg) et ses polygones, en mètres EPSG:3035.
    public sealed class FormeDeLieu
    {
        public long Rang { get; }
        public IReadOnlyList<PolygoneDeCarte> Contour { get; }
        public FormeDeLieu(long rang, IEnumerable<PolygoneDeCarte> contour)
        {
            Rang = rang;
            Contour = ClientCarte.Copier(contour, nameof(contour));
        }
    }

    // Le contour d'une cellule et ceux de ses lieux, dans l'ordre des rangs.
    public sealed class FormeDeCellule
    {
        public long CellId { get; }
        public IReadOnlyList<PolygoneDeCarte> Contour { get; }
        public IReadOnlyList<FormeDeLieu> Lieux { get; }
        public FormeDeCellule(long cellId, IEnumerable<PolygoneDeCarte> contour, IEnumerable<FormeDeLieu> lieux)
        {
            CellId = cellId;
            Contour = ClientCarte.Copier(contour, nameof(contour));
            Lieux = ClientCarte.Copier(lieux, nameof(lieux));
        }
    }

    // Les formes servies : leur version (nulle : le service n'en dit pas) et leurs cellules, triées par `cell_id`.
    public sealed class FormesLues
    {
        public string Version { get; }
        public IReadOnlyList<FormeDeCellule> Cellules { get; }
        private readonly Dictionary<long, FormeDeCellule> parCellule;
        public FormesLues(string version, IEnumerable<FormeDeCellule> cellules)
        {
            Version = version;
            Cellules = ClientCarte.Copier(cellules, nameof(cellules));
            parCellule = Cellules.ToDictionary(c => c.CellId);
        }
        // La cellule servie sous cet identifiant, ou null : la cellule n'est pas dans les formes.
        public FormeDeCellule De(long cellId) => parCellule.TryGetValue(cellId, out FormeDeCellule cellule) ? cellule : null;
    }

    // Soit des formes, soit une absence qui nomme sa cause : jamais les deux, jamais aucune.
    public sealed class LectureFormes
    {
        public FormesLues Formes { get; }
        public string Absence { get; }
        public bool Presente => Formes != null;
        private LectureFormes(FormesLues formes, string absence) { Formes = formes; Absence = absence; }
        public static LectureFormes De(FormesLues formes) => new LectureFormes(formes ?? throw new ArgumentNullException(nameof(formes)), null);
        public static LectureFormes Absent(string cause) =>
            new LectureFormes(null, string.IsNullOrEmpty(cause) ? throw new ArgumentException("une absence nomme sa cause", nameof(cause)) : cause);
    }

    // Demande les formes des cellules et des lieux au service local (`GET /formes` sur 127.0.0.1).
    // Ne lève jamais pour une cause du service : elle devient une absence déclarée.
    // Une seule clé fautive refuse toutes les formes, en nommant son chemin : aucune forme partielle n'est rendue.
    public sealed class ClientFormes : IDisposable
    {
        // La première requête calcule les formes de toute la carte (12 à 20 s sur le VPS) et la réponse pèse près de 19 Mo :
        // le délai de la carte ne suffit pas.
        public static readonly TimeSpan DelaiMinimal = TimeSpan.FromSeconds(60);
        private const string Hote = "127.0.0.1", Prefixe = "formes : ";
        private readonly int port;
        private readonly TimeSpan delai;
        private readonly HttpClient http;

        public ClientFormes(int port, TimeSpan delai)
        {
            if (port < 1 || port > 65535) throw new ArgumentOutOfRangeException(nameof(port), port, "port hors de 1..65535");
            // `Timeout.InfiniteTimeSpan` vaut -1 ms : il tombe sous le minimum, comme tout délai trop court.
            if (delai < DelaiMinimal) throw new ArgumentOutOfRangeException(nameof(delai), delai, "un délai d'au moins " + DelaiMinimal.TotalSeconds + " s attendu");
            this.port = port;
            this.delai = delai;
            // Aucune redirection suivie, et le délai tenu par Lire, comme dans ClientCarte.
            http = new HttpClient(new HttpClientHandler { AllowAutoRedirect = false }) { Timeout = Timeout.InfiniteTimeSpan };
        }

        public void Dispose() => http.Dispose();

        public LectureFormes Lire()
        {
            HttpStatusCode statut;
            string corps;
            using (var minuterie = new CancellationTokenSource())
            {
                try
                {
                    minuterie.CancelAfter(delai);
                    using (HttpResponseMessage reponse = http.GetAsync("http://" + Hote + ":" + port.ToString(CultureInfo.InvariantCulture) + "/formes", minuterie.Token).GetAwaiter().GetResult())
                    {
                        statut = reponse.StatusCode;
                        corps = Encoding.UTF8.GetString(reponse.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult());
                    }
                }
                catch (Exception erreur)
                {
                    // Seule la minuterie dit si le délai est échu : le runtime rend l'annulation sous plusieurs formes.
                    if (minuterie.IsCancellationRequested)
                        return LectureFormes.Absent(Prefixe + "délai dépassé (" + delai.TotalMilliseconds.ToString(CultureInfo.InvariantCulture) + " ms) sur " + Hote + ":" + port);
                    return LectureFormes.Absent(Prefixe + "service absent sur " + Hote + ":" + port + " (" + erreur.GetBaseException().Message + ")");
                }
            }
            if (statut != HttpStatusCode.OK) return LectureFormes.Absent(Prefixe + "statut " + (int)statut + ", corps reçu : " + corps);
            try { return LectureFormes.De(Formes(LecteurJson.LireObjet(corps))); }
            catch (ErreurJson erreur) { return LectureFormes.Absent(Prefixe + "JSON invalide à la position " + erreur.Position + " (" + erreur.Message + ")"); }
            catch (CleRefusee refus) { return LectureFormes.Absent(Prefixe + refus.Message); }
        }

        private static FormesLues Formes(Dictionary<string, object> racine)
        {
            // Les mètres des contours n'ont de sens que dans cette projection ; des formes sans cellule ne sont pas une mesure.
            if (!"EPSG:3035".Equals(Valeur(racine, "crs"))) throw Refus("crs", "le texte \"EPSG:3035\"", racine["crs"]);
            // La version est toujours présente : `null` dit que le monde servi n'en a pas, une clé absente refuse les formes.
            object version = Valeur(racine, "version");
            if (version != null && (!(version is string texte) || string.IsNullOrWhiteSpace(texte))) throw Refus("version", "un texte non vide ou null", version);
            long precedent = -1;
            List<FormeDeCellule> cellules = Liste(Valeur(racine, "cells"), "cells", 1, (brute, chemin) =>
            {
                FormeDeCellule cellule = Cellule(brute, chemin, precedent);
                precedent = cellule.CellId;
                return cellule;
            });
            return new FormesLues((string)version, cellules);
        }

        // `precedent` : le cell_id de la cellule d'avant (-1 pour la première) ; un cell_id qui ne le dépasse pas refuse les formes.
        private static FormeDeCellule Cellule(object valeur, string chemin, long precedent)
        {
            Dictionary<string, object> cellule = Objet(valeur, chemin);
            long cellId = Entier(cellule, chemin + ".cell_id");
            if (cellId <= precedent) throw new CleRefusee("clé " + chemin + ".cell_id : " + cellId + " après " + precedent + ", un ordre strictement croissant attendu");
            List<PolygoneDeCarte> contour = Contour(cellule, chemin + ".contour");
            int rangAttendu = 0;
            List<FormeDeLieu> lieux = Liste(Valeur(cellule, chemin + ".lieux"), chemin + ".lieux", 1, (brut, cheminLieu) => Lieu(brut, cheminLieu, rangAttendu++));
            return new FormeDeCellule(cellId, contour, lieux);
        }

        // Les rangs valent 0, 1, 2… dans l'ordre : le lieu qui vient en i-ème porte le rang `attendu` = i.
        private static FormeDeLieu Lieu(object valeur, string chemin, long attendu)
        {
            Dictionary<string, object> lieu = Objet(valeur, chemin);
            long rang = Entier(lieu, chemin + ".rang");
            if (rang != attendu) throw new CleRefusee("clé " + chemin + ".rang : " + rang + " servi, " + attendu + " attendu (les rangs vont de 0 à n−1 dans l'ordre)");
            return new FormeDeLieu(rang, Contour(lieu, chemin + ".contour"));
        }

        // Un MultiPolygon : au moins un polygone, chacun d'au moins un anneau (l'extérieur, puis les trous).
        private static List<PolygoneDeCarte> Contour(Dictionary<string, object> parent, string chemin)
        {
            Dictionary<string, object> contour = Objet(Valeur(parent, chemin), chemin);
            if (!"MultiPolygon".Equals(Valeur(contour, chemin + ".type"))) throw Refus(chemin + ".type", "le texte \"MultiPolygon\"", contour["type"]);
            return Liste(Valeur(contour, chemin + ".coordinates"), chemin + ".coordinates", 1, (brut, cheminPolygone) =>
            {
                List<List<PointCarte>> anneaux = Liste(brut, cheminPolygone, 1, Anneau);
                return new PolygoneDeCarte(anneaux[0], anneaux.Skip(1));
            });
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
            var lues = new List<T>(tableau.Count);
            for (int i = 0; i < tableau.Count; i++) lues.Add(lire(tableau[i], chemin + "[" + i.ToString(CultureInfo.InvariantCulture) + "]"));
            return lues;
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
