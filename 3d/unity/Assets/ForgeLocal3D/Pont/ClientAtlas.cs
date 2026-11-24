using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.Net.Http;
namespace Forge.Pont
{
    // Le nom d'une mer ou d'une région, et le point de la carte où le lire.
    public sealed class NomDeLAtlas
    {
        public string Nom { get; } public PointCarte Point { get; }
        public NomDeLAtlas(string nom, PointCarte point) { Nom = nom ?? throw new ArgumentNullException(nameof(nom)); Point = point; }
    }
    // Un fleuve : son nom et ses lignes, de sa source à sa mer (le Nil en a deux), chacune d'au moins deux points.
    public sealed class FleuveDeLAtlas
    {
        public string Nom { get; } public IReadOnlyList<IReadOnlyList<PointCarte>> Lignes { get; }
        public FleuveDeLAtlas(string nom, IEnumerable<IEnumerable<PointCarte>> lignes)
        {
            Nom = nom ?? throw new ArgumentNullException(nameof(nom));
            var copie = new List<IReadOnlyList<PointCarte>>();
            foreach (var ligne in lignes ?? throw new ArgumentNullException(nameof(lignes))) copie.Add(new ReadOnlyCollection<PointCarte>(new List<PointCarte>(ligne ?? throw new ArgumentNullException(nameof(lignes)))));
            Lignes = new ReadOnlyCollection<IReadOnlyList<PointCarte>>(copie);
        }
    }
    // Le siège d'une maison : son nom, l'identifiant de la maison et son point.
    public sealed class SiegeDeLAtlas
    {
        public string Nom { get; } public string Maison { get; } public PointCarte Point { get; }
        public SiegeDeLAtlas(string nom, string maison, PointCarte point) { Nom = nom ?? throw new ArgumentNullException(nameof(nom)); Maison = maison ?? throw new ArgumentNullException(nameof(maison)); Point = point; }
    }
    // Les noms de la carte tels que `/atlas` les sert, dans l'ordre servi. Version : celle de la carte figée (nulle quand le service la sert nulle).
    public sealed class AtlasLu
    {
        public string Version { get; } public IReadOnlyList<FleuveDeLAtlas> Fleuves { get; } public IReadOnlyList<NomDeLAtlas> Mers { get; }
        public IReadOnlyList<NomDeLAtlas> Regions { get; } public IReadOnlyList<SiegeDeLAtlas> Sieges { get; }
        public AtlasLu(string version, IEnumerable<FleuveDeLAtlas> fleuves, IEnumerable<NomDeLAtlas> mers, IEnumerable<NomDeLAtlas> regions, IEnumerable<SiegeDeLAtlas> sieges)
        {
            Version = version;
            Fleuves = new ReadOnlyCollection<FleuveDeLAtlas>(new List<FleuveDeLAtlas>(fleuves ?? throw new ArgumentNullException(nameof(fleuves))));
            Mers = new ReadOnlyCollection<NomDeLAtlas>(new List<NomDeLAtlas>(mers ?? throw new ArgumentNullException(nameof(mers))));
            Regions = new ReadOnlyCollection<NomDeLAtlas>(new List<NomDeLAtlas>(regions ?? throw new ArgumentNullException(nameof(regions))));
            Sieges = new ReadOnlyCollection<SiegeDeLAtlas>(new List<SiegeDeLAtlas>(sieges ?? throw new ArgumentNullException(nameof(sieges))));
        }
    }
    // GET /atlas sur 127.0.0.1. Une faute refuse toute la réponse et nomme la clé ; une absence du service devient une absence qui nomme sa cause.
    // Rien ne se recalcule : les points sont ceux que le service sert en mètres EPSG:3035, et une clé absente est une faute.
    public sealed class ClientAtlas : IDisposable
    {
        const string Projection = "EPSG:3035";
        readonly ServiceLocal atlas;
        public ClientAtlas(int port, TimeSpan delai) { atlas = new ServiceLocal(port, delai, "atlas : "); }
        public void Dispose() => atlas.Dispose();
        public Lecture<AtlasLu> Lire() => atlas.Demander(HttpMethod.Get, "/atlas", Atlas);
        static AtlasLu Atlas(Dictionary<string, object> racine)
        {
            object crs = ServiceLocal.Valeur(racine, "crs");
            if (!(crs is string projection) || projection != Projection) throw ServiceLocal.Refus("crs", "\"" + Projection + "\"", crs);
            object version = ServiceLocal.Valeur(racine, "version");
            if (version != null && !(version is string texte && !string.IsNullOrWhiteSpace(texte))) throw ServiceLocal.Refus("version", "un texte non vide ou null", version);
            var fleuves = new List<FleuveDeLAtlas>();
            foreach (var (chemin, f) in Objets(racine, "fleuves")) fleuves.Add(new FleuveDeLAtlas(Texte(f, chemin + ".nom"), Lignes(f, chemin + ".lignes")));
            var mers = new List<NomDeLAtlas>();
            foreach (var (chemin, m) in Objets(racine, "mers")) mers.Add(new NomDeLAtlas(Texte(m, chemin + ".nom"), Point(m, chemin)));
            var regions = new List<NomDeLAtlas>();
            foreach (var (chemin, r) in Objets(racine, "regions")) regions.Add(new NomDeLAtlas(Texte(r, chemin + ".nom"), Point(r, chemin)));
            var sieges = new List<SiegeDeLAtlas>();
            foreach (var (chemin, s) in Objets(racine, "sieges")) sieges.Add(new SiegeDeLAtlas(Texte(s, chemin + ".nom"), Texte(s, chemin + ".maison"), Point(s, chemin)));
            return new AtlasLu((string)version, fleuves, mers, regions, sieges);
        }
        // Les lignes d'un fleuve : au moins une, chacune d'au moins deux points.
        static List<List<PointCarte>> Lignes(Dictionary<string, object> fleuve, string chemin)
        {
            object brut = ServiceLocal.Valeur(fleuve, chemin); var tableau = brut as List<object> ?? throw ServiceLocal.Refus(chemin, "un tableau", brut);
            if (tableau.Count == 0) throw new ServiceLocal.Refusee("clé " + chemin + " : au moins une ligne attendue, reçu 0");
            var lignes = new List<List<PointCarte>>(tableau.Count);
            for (int i = 0; i < tableau.Count; i++)
            {
                string c = chemin + "[" + i.ToString(CultureInfo.InvariantCulture) + "]";
                var points = tableau[i] as List<object> ?? throw ServiceLocal.Refus(c, "un tableau de points", tableau[i]);
                if (points.Count < 2) throw new ServiceLocal.Refusee("clé " + c + " : au moins 2 points attendus, reçu " + points.Count.ToString(CultureInfo.InvariantCulture));
                var ligne = new List<PointCarte>(points.Count);
                for (int j = 0; j < points.Count; j++)
                {
                    string cp = c + "[" + j.ToString(CultureInfo.InvariantCulture) + "]";
                    ligne.Add(Point(points[j] as Dictionary<string, object> ?? throw ServiceLocal.Refus(cp, "un objet", points[j]), cp));
                }
                lignes.Add(ligne);
            }
            return lignes;
        }
        // Un point : ses mètres en x et en y, tels que servis.
        static PointCarte Point(Dictionary<string, object> point, string chemin) =>
            new PointCarte(ServiceLocal.Nombre(ServiceLocal.Valeur(point, chemin + ".x_m"), chemin + ".x_m"), ServiceLocal.Nombre(ServiceLocal.Valeur(point, chemin + ".y_m"), chemin + ".y_m"));
        // Les objets d'un tableau, chacun avec son chemin (`mers[0]`).
        static List<(string chemin, Dictionary<string, object> objet)> Objets(Dictionary<string, object> parent, string chemin)
        {
            object brut = ServiceLocal.Valeur(parent, chemin); var tableau = brut as List<object> ?? throw ServiceLocal.Refus(chemin, "un tableau", brut);
            var liste = new List<(string, Dictionary<string, object>)>(tableau.Count);
            for (int i = 0; i < tableau.Count; i++)
            {
                string c = chemin + "[" + i.ToString(CultureInfo.InvariantCulture) + "]";
                liste.Add((c, tableau[i] as Dictionary<string, object> ?? throw ServiceLocal.Refus(c, "un objet", tableau[i])));
            }
            return liste;
        }
        static string Texte(Dictionary<string, object> objet, string chemin)
        { object brut = ServiceLocal.Valeur(objet, chemin); return brut is string texte && !string.IsNullOrWhiteSpace(texte) ? texte : throw ServiceLocal.Refus(chemin, "un texte non vide", brut); }
    }
}
