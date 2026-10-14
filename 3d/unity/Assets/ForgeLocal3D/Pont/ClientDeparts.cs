using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.Net.Http;
namespace Forge.Pont
{
    public sealed class SiegeDeDepart
    {
        public string Nom { get; } public double Lat { get; } public double Lon { get; }
        public SiegeDeDepart(string nom, double lat, double lon) { Nom = nom; Lat = lat; Lon = lon; }
    }
    public sealed class VoisinDeDepart
    {
        public long CellId { get; } public long Habitants { get; } public IdentiteDeCarte Puissance { get; }
        public VoisinDeDepart(long cellId, long habitants, IdentiteDeCarte puissance) { CellId = cellId; Habitants = habitants; Puissance = puissance; }
    }
    // `Habitants` mesure la cellule du siège. `Suzerain` nul est une mesure servie, pas un manque.
    public sealed class FicheDeDepart
    {
        public long Id { get; } public string Nom { get; } public string Maison { get; } public SiegeDeDepart Siege { get; }
        public long CellId { get; } public long Habitants { get; } public IdentiteDeCarte Suzerain { get; } public IReadOnlyList<VoisinDeDepart> Voisins { get; }
        public FicheDeDepart(long id, string nom, string maison, SiegeDeDepart siege, long cellId, long habitants, IdentiteDeCarte suzerain, IEnumerable<VoisinDeDepart> voisins)
        { Id = id; Nom = nom; Maison = maison; Siege = siege; CellId = cellId; Habitants = habitants; Suzerain = suzerain; Voisins = new ReadOnlyCollection<VoisinDeDepart>(new List<VoisinDeDepart>(voisins)); }
    }
    public sealed class DepartsLus
    {
        public long Tick { get; } public DateDuMonde Date { get; } public IReadOnlyList<FicheDeDepart> Fiches { get; }
        public DepartsLus(long tick, DateDuMonde date, IEnumerable<FicheDeDepart> fiches)
        { Tick = tick; Date = date; Fiches = new ReadOnlyCollection<FicheDeDepart>(new List<FicheDeDepart>(fiches)); }
    }
    // GET /departs. La première lecture peut calculer la carte : délai d'au moins 10 s.
    // Une clé fautive refuse toute la réponse, sans fiche partielle ni zéro de remplacement.
    public sealed class ClientDeparts : IDisposable
    {
        public static readonly TimeSpan DelaiMinimal = TimeSpan.FromSeconds(10);
        private readonly ServiceLocal service;
        public ClientDeparts(int port, TimeSpan delai)
        {
            if (delai < DelaiMinimal || delai.TotalMilliseconds > int.MaxValue)
                throw new ArgumentOutOfRangeException(nameof(delai), delai, "un délai d'au moins 10 s, fini, attendu");
            service = new ServiceLocal(port, delai, "departs : ");
        }
        public void Dispose() => service.Dispose();
        public Lecture<DepartsLus> Lire() => service.Demander(HttpMethod.Get, "/departs", Racine);
        static DepartsLus Racine(Dictionary<string, object> racine)
        {
            object brutes = ServiceLocal.Valeur(racine, "departs");
            if (!(brutes is List<object> tableau) || tableau.Count == 0) throw ServiceLocal.Refus("departs", "un tableau non vide", brutes);
            var ids = new HashSet<long>(); var fiches = new List<FicheDeDepart>(tableau.Count);
            for (int i = 0; i < tableau.Count; i++) fiches.Add(Fiche(tableau[i], "departs[" + i.ToString(CultureInfo.InvariantCulture) + "]", ids));
            return new DepartsLus(ServiceLocal.Entier(racine, "tick", 0), ServiceLocal.Date(racine), fiches);
        }
        static FicheDeDepart Fiche(object valeur, string chemin, HashSet<long> ids)
        {
            var fiche = valeur as Dictionary<string, object> ?? throw ServiceLocal.Refus(chemin, "un objet", valeur);
            long id = Entier(fiche, chemin + ".id");
            if (!ids.Add(id)) throw new ServiceLocal.Refusee("clé " + chemin + ".id : " + id.ToString(CultureInfo.InvariantCulture) + " déjà lu");
            return new FicheDeDepart(id, Texte(fiche, chemin + ".nom"), Texte(fiche, chemin + ".maison"), Siege(fiche, chemin), Entier(fiche, chemin + ".cell_id"), Entier(fiche, chemin + ".habitants"), Identite(fiche, chemin + ".suzerain"), Voisins(fiche, chemin + ".voisins"));
        }
        static SiegeDeDepart Siege(Dictionary<string, object> fiche, string chemin)
        {
            string ici = chemin + ".siege"; object brut = ServiceLocal.Valeur(fiche, ici);
            var siege = brut as Dictionary<string, object> ?? throw ServiceLocal.Refus(ici, "un objet", brut);
            return new SiegeDeDepart(Texte(siege, ici + ".nom"), Degre(siege, ici + ".lat", -90, 90, "une latitude"), Degre(siege, ici + ".lon", -180, 180, "une longitude"));
        }
        static List<VoisinDeDepart> Voisins(Dictionary<string, object> fiche, string chemin)
        {
            object brut = ServiceLocal.Valeur(fiche, chemin); var tableau = brut as List<object> ?? throw ServiceLocal.Refus(chemin, "un tableau", brut); var liste = new List<VoisinDeDepart>(tableau.Count);
            for (int i = 0; i < tableau.Count; i++) { string ici = chemin + "[" + i.ToString(CultureInfo.InvariantCulture) + "]"; var voisin = tableau[i] as Dictionary<string, object> ?? throw ServiceLocal.Refus(ici, "un objet", tableau[i]); liste.Add(new VoisinDeDepart(Entier(voisin, ici + ".cell_id"), Entier(voisin, ici + ".habitants"), Identite(voisin, ici + ".puissance"))); }
            return liste;
        }
        static IdentiteDeCarte Identite(Dictionary<string, object> objet, string chemin)
        {
            object valeur = ServiceLocal.Valeur(objet, chemin); if (valeur == null) return null;
            return valeur is Dictionary<string, object> identite ? new IdentiteDeCarte(Entier(identite, chemin + ".id"), Texte(identite, chemin + ".nom")) : throw ServiceLocal.Refus(chemin, "null ou un objet", valeur);
        }
        static string Texte(Dictionary<string, object> objet, string chemin)
        { object brute = ServiceLocal.Valeur(objet, chemin); return brute is string texte && !string.IsNullOrWhiteSpace(texte) ? texte : throw ServiceLocal.Refus(chemin, "un texte non vide", brute); }
        static double Degre(Dictionary<string, object> objet, string chemin, double min, double max, string nom)
        {
            double nombre = ServiceLocal.Nombre(ServiceLocal.Valeur(objet, chemin), chemin);
            if (nombre < min || nombre > max) throw ServiceLocal.Refus(chemin, nom + " dans [" + min.ToString(CultureInfo.InvariantCulture) + ", " + max.ToString(CultureInfo.InvariantCulture) + "]", nombre);
            return nombre;
        }
        // Entier ≥ 0 sous 2^53, garde de ServiceLocal. Un booléen ou un texte n'est pas lu comme zéro.
        static long Entier(Dictionary<string, object> objet, string chemin)
        { object valeur = ServiceLocal.Valeur(objet, chemin); if (!(valeur is double)) throw ServiceLocal.Refus(chemin, "un entier ≥ 0 sous 2^53", valeur); return ServiceLocal.Entier(objet, chemin, 0); }
    }
}
