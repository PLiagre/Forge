using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.Net.Http;
namespace Forge.Pont
{
    // Un pays : son identifiant et son nom (nul quand le monde n'en dit pas).
    public sealed class IdentiteDePays
    {
        public string Id { get; } public string Nom { get; }
        public IdentiteDePays(string id, string nom) { Id = id; Nom = nom; }
    }
    // Le siège de la maison. Nom et Lieu nuls : le monde n'en dit pas ; CellId nul : siège hors de la carte.
    public sealed class SiegeJouable
    {
        public string Nom { get; } public string Lieu { get; } public long? CellId { get; }
        public SiegeJouable(string nom, string lieu, long? cellId) { Nom = nom; Lieu = lieu; CellId = cellId; }
    }
    // Le suzerain de la maison, et le pays au nom duquel il la tient.
    public sealed class SuzerainJouable
    {
        public string Id { get; } public string Nom { get; } public IdentiteDePays Pays { get; }
        public SuzerainJouable(string id, string nom, IdentiteDePays pays) { Id = id; Nom = nom; Pays = pays; }
    }
    // La ville de la capitale. Batie : sa scène est servie et sa raison est nulle ; sinon la raison dit pourquoi elle ne l'est pas.
    public sealed class VilleJouable
    {
        public bool Batie { get; } public string Scene { get; } public string Raison { get; }
        public VilleJouable(bool batie, string scene, string raison) { Batie = batie; Scene = scene; Raison = raison; }
        // Le nom de la scène, celui que `TransitionDeVue.Lancer` charge : le fichier servi sans son dossier ni son extension. Nul sans scène.
        public string NomDeScene
        {
            get
            {
                if (Scene == null) return null;
                string fichier = Scene.Substring(Scene.LastIndexOfAny(new[] { '/', '\\' }) + 1); int point = fichier.LastIndexOf('.');
                return point > 0 ? fichier.Substring(0, point) : fichier;
            }
        }
    }
    // Une maison que le joueur peut prendre. Nom nul : le monde ne la nomme pas ; Suzerain nul : elle ne relève de personne.
    public sealed class FicheJouable
    {
        public string Id { get; } public string Nom { get; } public string Sorte { get; } public long Lieux { get; } public IdentiteDePays Pays { get; } public IReadOnlyList<IdentiteDePays> Regne { get; }
        public SiegeJouable Siege { get; } public SuzerainJouable Suzerain { get; } public VilleJouable Ville { get; }
        public FicheJouable(string id, string nom, string sorte, long lieux, IdentiteDePays pays, IEnumerable<IdentiteDePays> regne, SiegeJouable siege, SuzerainJouable suzerain, VilleJouable ville)
        {
            Id = id; Nom = nom; Sorte = sorte; Lieux = lieux; Pays = pays; Siege = siege; Suzerain = suzerain; Ville = ville;
            Regne = new ReadOnlyCollection<IdentiteDePays>(new List<IdentiteDePays>(regne ?? throw new ArgumentNullException(nameof(regne))));
        }
    }
    public sealed class JouablesLus
    {
        public long Tick { get; } public DateDuMonde Date { get; } public IReadOnlyList<FicheJouable> Fiches { get; }
        public JouablesLus(long tick, DateDuMonde date, IEnumerable<FicheJouable> fiches)
        { Tick = tick; Date = date; Fiches = new ReadOnlyCollection<FicheJouable>(new List<FicheJouable>(fiches)); }
    }
    // GET /jouables. La première lecture peut calculer les pays : délai d'au moins 10 s.
    // Une clé fautive refuse toute la réponse, sans fiche partielle. Un null servi est une mesure ; une clé absente est une faute.
    // La ville est lue sans être recalculée : bâtie exige une scène non vide et aucune raison, non bâtie exige une raison non vide.
    public sealed class ClientJouables : IDisposable
    {
        public static readonly TimeSpan DelaiMinimal = TimeSpan.FromSeconds(10);
        private readonly ServiceLocal service;
        public ClientJouables(int port, TimeSpan delai)
        {
            if (delai < DelaiMinimal || delai.TotalMilliseconds > int.MaxValue)
                throw new ArgumentOutOfRangeException(nameof(delai), delai, "un délai d'au moins 10 s, fini, attendu");
            service = new ServiceLocal(port, delai, "jouables : ");
        }
        public void Dispose() => service.Dispose();
        public Lecture<JouablesLus> Lire() => service.Demander(HttpMethod.Get, "/jouables", Racine);
        static JouablesLus Racine(Dictionary<string, object> racine)
        {
            object brutes = ServiceLocal.Valeur(racine, "jouables");
            if (!(brutes is List<object> tableau) || tableau.Count == 0) throw ServiceLocal.Refus("jouables", "un tableau non vide", brutes);
            var ids = new HashSet<string>(); var fiches = new List<FicheJouable>(tableau.Count);
            for (int i = 0; i < tableau.Count; i++) fiches.Add(Fiche(tableau[i], "jouables[" + i.ToString(CultureInfo.InvariantCulture) + "]", ids));
            return new JouablesLus(ServiceLocal.Entier(racine, "tick", 0), ServiceLocal.Date(racine), fiches);
        }
        static FicheJouable Fiche(object valeur, string chemin, HashSet<string> ids)
        {
            var fiche = valeur as Dictionary<string, object> ?? throw ServiceLocal.Refus(chemin, "un objet", valeur);
            string id = Texte(fiche, chemin + ".id");
            if (!ids.Add(id)) throw new ServiceLocal.Refusee("clé " + chemin + ".id : \"" + id + "\" déjà lu");
            return new FicheJouable(id, TexteOuNul(fiche, chemin + ".nom"), Texte(fiche, chemin + ".sorte"), Entier(fiche, chemin + ".lieux"), Pays(fiche, chemin + ".pays"), Regne(fiche, chemin + ".regne"),
                Siege(fiche, chemin + ".siege"), Suzerain(fiche, chemin + ".suzerain"), Ville(fiche, chemin + ".ville"));
        }
        static IdentiteDePays Pays(Dictionary<string, object> objet, string chemin)
        {
            object brut = ServiceLocal.Valeur(objet, chemin); var pays = brut as Dictionary<string, object> ?? throw ServiceLocal.Refus(chemin, "un objet", brut);
            return new IdentiteDePays(Texte(pays, chemin + ".id"), TexteOuNul(pays, chemin + ".nom"));
        }
        static List<IdentiteDePays> Regne(Dictionary<string, object> fiche, string chemin)
        {
            object brut = ServiceLocal.Valeur(fiche, chemin); var tableau = brut as List<object> ?? throw ServiceLocal.Refus(chemin, "un tableau", brut); var liste = new List<IdentiteDePays>(tableau.Count);
            for (int i = 0; i < tableau.Count; i++)
            {
                string ici = chemin + "[" + i.ToString(CultureInfo.InvariantCulture) + "]"; var pays = tableau[i] as Dictionary<string, object> ?? throw ServiceLocal.Refus(ici, "un objet", tableau[i]);
                liste.Add(new IdentiteDePays(Texte(pays, ici + ".id"), TexteOuNul(pays, ici + ".nom")));
            }
            return liste;
        }
        static SiegeJouable Siege(Dictionary<string, object> fiche, string chemin)
        {
            object brut = ServiceLocal.Valeur(fiche, chemin); var siege = brut as Dictionary<string, object> ?? throw ServiceLocal.Refus(chemin, "un objet", brut);
            string nom = TexteOuNul(siege, chemin + ".nom"), lieu = TexteOuNul(siege, chemin + ".lieu");
            return new SiegeJouable(nom, lieu, ServiceLocal.Valeur(siege, chemin + ".cell_id") == null ? (long?)null : Entier(siege, chemin + ".cell_id"));
        }
        static SuzerainJouable Suzerain(Dictionary<string, object> fiche, string chemin)
        {
            object brut = ServiceLocal.Valeur(fiche, chemin); if (brut == null) return null;
            var suzerain = brut as Dictionary<string, object> ?? throw ServiceLocal.Refus(chemin, "null ou un objet", brut);
            return new SuzerainJouable(Texte(suzerain, chemin + ".id"), TexteOuNul(suzerain, chemin + ".nom"), Pays(suzerain, chemin + ".pays"));
        }
        static VilleJouable Ville(Dictionary<string, object> fiche, string chemin)
        {
            object brut = ServiceLocal.Valeur(fiche, chemin); var ville = brut as Dictionary<string, object> ?? throw ServiceLocal.Refus(chemin, "un objet", brut);
            object batie = ServiceLocal.Valeur(ville, chemin + ".batie"); if (!(batie is bool estBatie)) throw ServiceLocal.Refus(chemin + ".batie", "un booléen", batie);
            string scene = TexteOuNul(ville, chemin + ".scene"), raison = TexteOuNul(ville, chemin + ".raison");
            if (estBatie && scene == null) throw ServiceLocal.Refus(chemin + ".scene", "un texte non vide (la ville est bâtie)", null);
            if (estBatie && raison != null) throw ServiceLocal.Refus(chemin + ".raison", "null (la ville est bâtie)", raison);
            if (!estBatie && raison == null) throw ServiceLocal.Refus(chemin + ".raison", "un texte non vide (la ville n'est pas bâtie)", null);
            return new VilleJouable(estBatie, scene, raison);
        }
        static string Texte(Dictionary<string, object> objet, string chemin)
        { object brute = ServiceLocal.Valeur(objet, chemin); return brute is string texte && !string.IsNullOrWhiteSpace(texte) ? texte : throw ServiceLocal.Refus(chemin, "un texte non vide", brute); }
        static string TexteOuNul(Dictionary<string, object> objet, string chemin)
        { object brute = ServiceLocal.Valeur(objet, chemin); return brute == null ? null : brute is string texte && !string.IsNullOrWhiteSpace(texte) ? texte : throw ServiceLocal.Refus(chemin, "un texte non vide ou null", brute); }
        // Entier ≥ 0 sous 2^53, garde de ServiceLocal. Un booléen ou un texte n'est pas lu comme un nombre.
        static long Entier(Dictionary<string, object> objet, string chemin)
        { object valeur = ServiceLocal.Valeur(objet, chemin); if (!(valeur is double)) throw ServiceLocal.Refus(chemin, "un entier ≥ 0 sous 2^53", valeur); return ServiceLocal.Entier(objet, chemin, 0); }
    }
}
