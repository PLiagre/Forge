using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.Net.Http;
namespace Forge.Pont
{
    // Un pays de la carte : son identifiant et son nom (nul quand le monde n'en dit pas).
    public sealed class PaysDeLaCarte
    {
        public string Id { get; } public string Nom { get; }
        public PaysDeLaCarte(string id, string nom) { Id = id; Nom = nom; }
    }
    // Une terre, son maître (nul : terre sans maître) et son pays (nul : terre sans pays).
    public sealed class TerreLue
    {
        public long CellId { get; } public string Maitre { get; } public string Pays { get; }
        public TerreLue(long cellId, string maitre, string pays) { CellId = cellId; Maitre = maitre; Pays = pays; }
    }
    // Les terres de la carte telles que `/terres` les sert : à qui est chaque terre et de quel pays elle est, dans l'ordre servi.
    public sealed class TerresDeLaCarte
    {
        public long Tick { get; } public DateDuMonde Date { get; }
        public IReadOnlyList<PaysDeLaCarte> Pays { get; } public IReadOnlyList<TerreLue> Terres { get; }
        readonly Dictionary<long, TerreLue> parCellule; readonly Dictionary<string, PaysDeLaCarte> parPays;
        public TerresDeLaCarte(long tick, DateDuMonde date, IEnumerable<PaysDeLaCarte> pays, IEnumerable<TerreLue> terres)
        {
            Tick = tick; Date = date;
            var listePays = new List<PaysDeLaCarte>(pays ?? throw new ArgumentNullException(nameof(pays))); var listeTerres = new List<TerreLue>(terres ?? throw new ArgumentNullException(nameof(terres)));
            parPays = new Dictionary<string, PaysDeLaCarte>(listePays.Count); foreach (var p in listePays) parPays.Add(p.Id, p);
            parCellule = new Dictionary<long, TerreLue>(listeTerres.Count); foreach (var t in listeTerres) parCellule.Add(t.CellId, t);
            Pays = new ReadOnlyCollection<PaysDeLaCarte>(listePays); Terres = new ReadOnlyCollection<TerreLue>(listeTerres);
        }
        // L'identifiant du pays de la terre, ou null : terre sans pays, ou terre que `/terres` ne sert pas.
        public string PaysDe(long cellId) => parCellule.TryGetValue(cellId, out TerreLue t) ? t.Pays : null;
        // Le maître de la terre, ou null : terre sans maître, ou terre que `/terres` ne sert pas.
        public string MaitreDe(long cellId) => parCellule.TryGetValue(cellId, out TerreLue t) ? t.Maitre : null;
        // Le nom du pays, ou null : nom non dit, ou pays que `/terres` ne sert pas.
        public string NomDuPays(string id) => id != null && parPays.TryGetValue(id, out PaysDeLaCarte p) ? p.Nom : null;
    }
    // Une guerre déclarée : qui attaque, qui défend, et le tick de la déclaration.
    public sealed class GuerreLue
    {
        public long Identifiant { get; } public string Agresseur { get; } public string Defenseur { get; } public long Debut { get; }
        public GuerreLue(long identifiant, string agresseur, string defenseur, long debut) { Identifiant = identifiant; Agresseur = agresseur; Defenseur = defenseur; Debut = debut; }
    }
    // Une armée telle que `/guerres` la sert. Siege nul : elle n'assiège pas ; Destination nulle : elle ne marche pas (une terre et un rang) ;
    // Route : les terres qu'il lui reste à traverser ; Point : où elle est ; Etapes : les points de sa marche.
    public sealed class ArmeeLue
    {
        public long Identifiant { get; } public string Maison { get; } public long CellId { get; } public long Rang { get; } public long Hommes { get; } public double VivresKg { get; }
        public long? Siege { get; } public LieuDuPays Destination { get; } public IReadOnlyList<long> Route { get; } public PointCarte Point { get; } public IReadOnlyList<PointCarte> Etapes { get; }
        public ArmeeLue(long identifiant, string maison, long cellId, long rang, long hommes, double vivresKg, long? siege, LieuDuPays destination, IEnumerable<long> route, PointCarte point, IEnumerable<PointCarte> etapes)
        {
            Identifiant = identifiant; Maison = maison; CellId = cellId; Rang = rang; Hommes = hommes; VivresKg = vivresKg; Siege = siege; Destination = destination; Point = point;
            Route = new ReadOnlyCollection<long>(new List<long>(route ?? throw new ArgumentNullException(nameof(route))));
            Etapes = new ReadOnlyCollection<PointCarte>(new List<PointCarte>(etapes ?? throw new ArgumentNullException(nameof(etapes))));
        }
    }
    // Une terre prise : l'armée, l'ancien maître (nul : terre sans maître), le nouveau, les rangs pris et le tick de la prise.
    public sealed class PriseLue
    {
        public long Armee { get; } public long CellId { get; } public string De { get; } public string A { get; } public IReadOnlyList<long> Rangs { get; } public long Tick { get; }
        public PriseLue(long armee, long cellId, string de, string a, IEnumerable<long> rangs, long tick)
        {
            Armee = armee; CellId = cellId; De = de; A = a; Tick = tick;
            Rangs = new ReadOnlyCollection<long>(new List<long>(rangs ?? throw new ArgumentNullException(nameof(rangs))));
        }
    }
    // Les guerres, leurs armées et leurs prises, dans l'ordre servi, avec les morts des armées tels que le monde les compte.
    public sealed class GuerresLues
    {
        public long Tick { get; } public DateDuMonde Date { get; } public IReadOnlyList<GuerreLue> Guerres { get; } public IReadOnlyList<ArmeeLue> Armees { get; }
        public IReadOnlyList<PriseLue> Prises { get; } public long MortsDesArmees { get; }
        public GuerresLues(long tick, DateDuMonde date, IEnumerable<GuerreLue> guerres, IEnumerable<ArmeeLue> armees, IEnumerable<PriseLue> prises, long mortsDesArmees)
        {
            Tick = tick; Date = date; MortsDesArmees = mortsDesArmees;
            Guerres = new ReadOnlyCollection<GuerreLue>(new List<GuerreLue>(guerres ?? throw new ArgumentNullException(nameof(guerres))));
            Armees = new ReadOnlyCollection<ArmeeLue>(new List<ArmeeLue>(armees ?? throw new ArgumentNullException(nameof(armees))));
            Prises = new ReadOnlyCollection<PriseLue>(new List<PriseLue>(prises ?? throw new ArgumentNullException(nameof(prises))));
        }
    }
    // Un lieu où la maison peut lever des hommes, et combien au plus.
    public sealed class LieuDeLevee
    {
        public long CellId { get; } public long Rang { get; } public long HommesMax { get; }
        public LieuDeLevee(long cellId, long rang, long hommesMax) { CellId = cellId; Rang = rang; HommesMax = hommesMax; }
    }
    // Le devis du bâtiment qui ouvre la levée (la caserne), dans la capitale : ses journées, ses bras d'un jour et son grain,
    // comptés par le monde comme au dépôt, et le refus de son dépôt aujourd'hui (nul : il serait accepté).
    public sealed class BatimentDeLevee
    {
        public string Nature { get; } public string Nom { get; } public long CellId { get; } public long Journees { get; } public long BrasParJour { get; } public double CoutKg { get; }
        // Le grain qui manque au grenier pour ce dépôt, servi par le monde : 0 s'il n'en manque pas.
        public double ManqueKg { get; } public string Refus { get; }
        public BatimentDeLevee(string nature, string nom, long cellId, long journees, long brasParJour, double coutKg, double manqueKg, string refus)
        {
            Nature = nature ?? throw new ArgumentNullException(nameof(nature)); Nom = nom ?? throw new ArgumentNullException(nameof(nom));
            CellId = cellId; Journees = journees; BrasParJour = brasParJour; CoutKg = coutKg; ManqueKg = manqueKg; Refus = refus;
        }
    }
    // Ce que la maison peut lever. Refus nul : la levée est permise. Batiment nul : la capitale est hors de la carte.
    public sealed class LeveeLue
    {
        public string Refus { get; } public IReadOnlyList<LieuDeLevee> Lieux { get; } public long Paysans { get; } public double GrainLibreKg { get; } public double RationKgParHommeParJour { get; }
        public BatimentDeLevee Batiment { get; }
        public LeveeLue(string refus, IEnumerable<LieuDeLevee> lieux, long paysans, double grainLibreKg, double rationKgParHommeParJour, BatimentDeLevee batiment = null)
        {
            Refus = refus; Paysans = paysans; GrainLibreKg = grainLibreKg; RationKgParHommeParJour = rationKgParHommeParJour; Batiment = batiment;
            Lieux = new ReadOnlyCollection<LieuDeLevee>(new List<LieuDeLevee>(lieux ?? throw new ArgumentNullException(nameof(lieux))));
        }
    }
    // La terre visée : son maître (nul : sans maître) et le refus de déclarer la guerre (nul : permis).
    public sealed class CibleLue
    {
        public long CellId { get; } public string Maitre { get; } public string RefusDeDeclaration { get; }
        public CibleLue(long cellId, string maitre, string refusDeDeclaration) { CellId = cellId; Maitre = maitre; RefusDeDeclaration = refusDeDeclaration; }
    }
    // La marche d'une armée vers sa destination : la route, sa longueur en km, sa durée en jours, et le refus de la marche (nul : permise).
    public sealed class MarcheLue
    {
        public string Refus { get; } public IReadOnlyList<long> Route { get; } public double Km { get; } public long Jours { get; }
        public MarcheLue(string refus, IEnumerable<long> route, double km, long jours)
        {
            Refus = refus; Km = km; Jours = jours;
            Route = new ReadOnlyCollection<long>(new List<long>(route ?? throw new ArgumentNullException(nameof(route))));
        }
    }
    // Ce que le monde permet à une armée de la maison. Marche nulle : pas de terre visée ; chaque refus nul : le geste est permis.
    // HommesRendus et VivresRendusKg : ce que le renvoi rendrait à la terre.
    public sealed class OrdresDUneArmee
    {
        public long Identifiant { get; } public long CellId { get; } public long Rang { get; } public long Hommes { get; } public double VivresKg { get; } public long? Siege { get; }
        public LieuDuPays Destination { get; } public MarcheLue Marche { get; } public string RefusDuSiege { get; } public string RefusDuRenvoi { get; }
        public long HommesRendus { get; } public double VivresRendusKg { get; }
        public OrdresDUneArmee(long identifiant, long cellId, long rang, long hommes, double vivresKg, long? siege, LieuDuPays destination, MarcheLue marche,
            string refusDuSiege, string refusDuRenvoi, long hommesRendus, double vivresRendusKg)
        {
            Identifiant = identifiant; CellId = cellId; Rang = rang; Hommes = hommes; VivresKg = vivresKg; Siege = siege; Destination = destination; Marche = marche;
            RefusDuSiege = refusDuSiege; RefusDuRenvoi = refusDuRenvoi; HommesRendus = hommesRendus; VivresRendusKg = vivresRendusKg;
        }
    }
    // Les ordres de guerre d'une maison, sur une terre visée ou non. Cible nulle : aucune terre visée.
    public sealed class OrdresDeGuerre
    {
        public string MaisonId { get; } public long Tick { get; } public DateDuMonde Date { get; } public LeveeLue Levee { get; } public CibleLue Cible { get; } public IReadOnlyList<OrdresDUneArmee> Armees { get; }
        public OrdresDeGuerre(string maisonId, long tick, DateDuMonde date, LeveeLue levee, CibleLue cible, IEnumerable<OrdresDUneArmee> armees)
        {
            MaisonId = maisonId; Tick = tick; Date = date; Cible = cible; Levee = levee ?? throw new ArgumentNullException(nameof(levee));
            Armees = new ReadOnlyCollection<OrdresDUneArmee>(new List<OrdresDUneArmee>(armees ?? throw new ArgumentNullException(nameof(armees))));
        }
    }
    // GET /terres, /guerres et /guerres/ordres sur 127.0.0.1. Une faute refuse toute la réponse et nomme la clé ; une absence du service devient une absence qui nomme sa cause.
    // Rien ne se recalcule : une clé servie à null est une mesure (terre sans maître, siège nul, refus nul), une clé absente est une faute.
    public sealed class ClientGuerre : IDisposable
    {
        readonly ServiceLocal terres, guerres, ordres;
        public ClientGuerre(int port, TimeSpan delai)
        {
            terres = new ServiceLocal(port, delai, "terres : "); guerres = new ServiceLocal(port, delai, "guerres : "); ordres = new ServiceLocal(port, delai, "ordres : ");
        }
        public void Dispose() { terres.Dispose(); guerres.Dispose(); ordres.Dispose(); }
        public Lecture<TerresDeLaCarte> LireTerres() => terres.Demander(HttpMethod.Get, "/terres", Terres);
        public Lecture<GuerresLues> LireGuerres() => guerres.Demander(HttpMethod.Get, "/guerres", Guerres);
        // Les ordres de la maison ; `cellId` désigne la terre visée, ou rien.
        public Lecture<OrdresDeGuerre> LireOrdres(string maison, long? cellId)
        {
            if (string.IsNullOrWhiteSpace(maison)) throw new ArgumentException("un identifiant de maison non vide attendu", nameof(maison));
            string cible = "/guerres/ordres?maison=" + Uri.EscapeDataString(maison) + (cellId.HasValue ? "&cell=" + cellId.Value.ToString(CultureInfo.InvariantCulture) : "");
            return ordres.Demander(HttpMethod.Get, cible, racine => Ordres(racine, maison));
        }
        static TerresDeLaCarte Terres(Dictionary<string, object> racine)
        {
            long tick = ServiceLocal.Entier(racine, "tick", 0); DateDuMonde date = ServiceLocal.Date(racine);
            var pays = new List<PaysDeLaCarte>(); var ids = new HashSet<string>();
            foreach (var (chemin, p) in Objets(racine, "pays"))
            {
                string id = Texte(p, chemin + ".id");
                if (!ids.Add(id)) throw new ServiceLocal.Refusee("clé " + chemin + ".id : \"" + id + "\" servi deux fois");
                pays.Add(new PaysDeLaCarte(id, TexteOuNul(p, chemin + ".nom")));
            }
            var terres = new List<TerreLue>(); var vues = new HashSet<long>();
            foreach (var (chemin, t) in Objets(racine, "terres"))
            {
                long cell = ServiceLocal.Entier(t, chemin + ".cell_id", 0); string maitre = TexteOuNul(t, chemin + ".maitre"), paysDeLaTerre = TexteOuNul(t, chemin + ".pays");
                if (!vues.Add(cell)) throw new ServiceLocal.Refusee("clé " + chemin + ".cell_id : la terre " + cell + " est servie deux fois");
                if (paysDeLaTerre != null && !ids.Contains(paysDeLaTerre)) throw new ServiceLocal.Refusee("clé " + chemin + ".pays : \"" + paysDeLaTerre + "\" absent de la liste pays");
                terres.Add(new TerreLue(cell, maitre, paysDeLaTerre));
            }
            return new TerresDeLaCarte(tick, date, pays, terres);
        }
        static GuerresLues Guerres(Dictionary<string, object> racine)
        {
            long tick = ServiceLocal.Entier(racine, "tick", 0); DateDuMonde date = ServiceLocal.Date(racine);
            var guerres = new List<GuerreLue>();
            foreach (var (chemin, g) in Objets(racine, "guerres"))
                guerres.Add(new GuerreLue(ServiceLocal.Entier(g, chemin + ".identifiant", 0), Texte(g, chemin + ".agresseur"), Texte(g, chemin + ".defenseur"), ServiceLocal.Entier(g, chemin + ".debut", 0)));
            var armees = new List<ArmeeLue>();
            foreach (var (chemin, a) in Objets(racine, "armees"))
            {
                long identifiant = ServiceLocal.Entier(a, chemin + ".identifiant", 0); string maison = Texte(a, chemin + ".maison");
                long cell = ServiceLocal.Entier(a, chemin + ".cell_id", 0), rang = ServiceLocal.Entier(a, chemin + ".rang", 0), hommes = ServiceLocal.Entier(a, chemin + ".hommes", 0);
                double vivres = Masse(a, chemin + ".vivres_kg");
                armees.Add(new ArmeeLue(identifiant, maison, cell, rang, hommes, vivres, EntierOuNul(a, chemin + ".siege", 0), Destination(a, chemin + ".destination"),
                    Entiers(a, chemin + ".route"), Point(Objet(a, chemin + ".point"), chemin + ".point"), Etapes(a, chemin + ".etapes")));
            }
            var prises = new List<PriseLue>();
            foreach (var (chemin, p) in Objets(racine, "prises"))
                prises.Add(new PriseLue(ServiceLocal.Entier(p, chemin + ".armee", 0), ServiceLocal.Entier(p, chemin + ".cell_id", 0), TexteOuNul(p, chemin + ".de"), Texte(p, chemin + ".a"),
                    Entiers(p, chemin + ".rangs"), ServiceLocal.Entier(p, chemin + ".tick", 0)));
            return new GuerresLues(tick, date, guerres, armees, prises, ServiceLocal.Entier(racine, "morts_des_armees", 0));
        }
        static OrdresDeGuerre Ordres(Dictionary<string, object> racine, string demande)
        {
            string maison = Texte(racine, "maison");
            if (!string.Equals(maison, demande, StringComparison.Ordinal)) throw new ServiceLocal.Refusee("clé maison : \"" + maison + "\" reçu pour \"" + demande + "\" demandé");
            long tick = ServiceLocal.Entier(racine, "tick", 0); DateDuMonde date = ServiceLocal.Date(racine);
            var levee = Levee(Objet(racine, "levee"));
            CibleLue cible = null; object brute = ServiceLocal.Valeur(racine, "cible");
            if (brute != null)
            {
                var c = brute as Dictionary<string, object> ?? throw ServiceLocal.Refus("cible", "un objet ou null", brute);
                cible = new CibleLue(ServiceLocal.Entier(c, "cible.cell_id", 0), TexteOuNul(c, "cible.maitre"), TexteOuNul(Objet(c, "cible.declaration"), "cible.declaration.refus"));
            }
            var armees = new List<OrdresDUneArmee>();
            foreach (var (chemin, a) in Objets(racine, "armees"))
            {
                var assieger = Objet(a, chemin + ".assieger"); var renvoyer = Objet(a, chemin + ".renvoyer"); MarcheLue marche = null; object m = ServiceLocal.Valeur(a, chemin + ".marche");
                if (m != null)
                {
                    var objet = m as Dictionary<string, object> ?? throw ServiceLocal.Refus(chemin + ".marche", "un objet ou null", m);
                    marche = new MarcheLue(TexteOuNul(objet, chemin + ".marche.refus"), Entiers(objet, chemin + ".marche.route"), Masse(objet, chemin + ".marche.km"), ServiceLocal.Entier(objet, chemin + ".marche.jours", 0));
                }
                armees.Add(new OrdresDUneArmee(ServiceLocal.Entier(a, chemin + ".identifiant", 0), ServiceLocal.Entier(a, chemin + ".cell_id", 0), ServiceLocal.Entier(a, chemin + ".rang", 0),
                    ServiceLocal.Entier(a, chemin + ".hommes", 0), Masse(a, chemin + ".vivres_kg"), EntierOuNul(a, chemin + ".siege", 0), Destination(a, chemin + ".destination"), marche,
                    TexteOuNul(assieger, chemin + ".assieger.refus"), TexteOuNul(renvoyer, chemin + ".renvoyer.refus"),
                    ServiceLocal.Entier(renvoyer, chemin + ".renvoyer.hommes", 0), Masse(renvoyer, chemin + ".renvoyer.vivres_kg")));
            }
            return new OrdresDeGuerre(maison, tick, date, levee, cible, armees);
        }
        static LeveeLue Levee(Dictionary<string, object> levee)
        {
            var lieux = new List<LieuDeLevee>();
            foreach (var (chemin, l) in Objets(levee, "levee.lieux"))
                lieux.Add(new LieuDeLevee(ServiceLocal.Entier(l, chemin + ".cell_id", 0), ServiceLocal.Entier(l, chemin + ".rang", 0), ServiceLocal.Entier(l, chemin + ".hommes_max", 0)));
            BatimentDeLevee batiment = null; object brut = ServiceLocal.Valeur(levee, "levee.batiment");
            if (brut != null)
            {
                var b = brut as Dictionary<string, object> ?? throw ServiceLocal.Refus("levee.batiment", "un objet ou null", brut);
                batiment = new BatimentDeLevee(Texte(b, "levee.batiment.nature"), Texte(b, "levee.batiment.nom"), ServiceLocal.Entier(b, "levee.batiment.cell_id", 0),
                    ServiceLocal.Entier(b, "levee.batiment.journees", 1), ServiceLocal.Entier(b, "levee.batiment.bras_par_jour", 1), Masse(b, "levee.batiment.cout_kg"), Masse(b, "levee.batiment.manque_kg"), TexteOuNul(b, "levee.batiment.refus"));
            }
            return new LeveeLue(TexteOuNul(levee, "levee.refus"), lieux, ServiceLocal.Entier(levee, "levee.paysans", 0), Masse(levee, "levee.grain_libre_kg"), Masse(levee, "levee.ration_kg_par_homme_par_jour"), batiment);
        }
        // Une destination : null, ou une terre et un rang entiers ≥ 0.
        static LieuDuPays Destination(Dictionary<string, object> objet, string chemin)
        {
            object brut = ServiceLocal.Valeur(objet, chemin); if (brut == null) return null;
            var tableau = brut as List<object> ?? throw ServiceLocal.Refus(chemin, "un tableau [terre, rang] ou null", brut);
            if (tableau.Count != 2) throw new ServiceLocal.Refusee("clé " + chemin + " : 2 entiers [terre, rang] attendus, reçu " + tableau.Count);
            return new LieuDuPays(EntierDe(tableau[0], chemin + "[0]"), EntierDe(tableau[1], chemin + "[1]"));
        }
        static List<PointCarte> Etapes(Dictionary<string, object> armee, string chemin)
        {
            var etapes = new List<PointCarte>();
            foreach (var (c, e) in Objets(armee, chemin)) etapes.Add(Point(e, c));
            return etapes;
        }
        // Un point : ses mètres en x et en y, tels que servis ; la latitude et la longitude ne sont pas lues.
        static PointCarte Point(Dictionary<string, object> point, string chemin) =>
            new PointCarte(ServiceLocal.Nombre(ServiceLocal.Valeur(point, chemin + ".x_m"), chemin + ".x_m"), ServiceLocal.Nombre(ServiceLocal.Valeur(point, chemin + ".y_m"), chemin + ".y_m"));
        static double Masse(Dictionary<string, object> objet, string chemin)
        {
            double masse = ServiceLocal.Nombre(ServiceLocal.Valeur(objet, chemin), chemin);
            return masse >= 0 ? masse : throw ServiceLocal.Refus(chemin, "un nombre fini ≥ 0", masse);
        }
        static long EntierDe(object valeur, string chemin)
        {
            double nombre = ServiceLocal.Nombre(valeur, chemin);
            if (nombre != Math.Floor(nombre) || nombre < 0 || nombre >= 9007199254740992.0) throw ServiceLocal.Refus(chemin, "un entier ≥ 0 sous 2^53", nombre);
            return (long)nombre;
        }
        static long? EntierOuNul(Dictionary<string, object> objet, string chemin, long min) => ServiceLocal.Valeur(objet, chemin) == null ? (long?)null : ServiceLocal.Entier(objet, chemin, min);
        static List<long> Entiers(Dictionary<string, object> objet, string chemin)
        {
            object brut = ServiceLocal.Valeur(objet, chemin); var tableau = brut as List<object> ?? throw ServiceLocal.Refus(chemin, "un tableau", brut);
            var liste = new List<long>(tableau.Count);
            for (int i = 0; i < tableau.Count; i++) liste.Add(EntierDe(tableau[i], chemin + "[" + i.ToString(CultureInfo.InvariantCulture) + "]"));
            return liste;
        }
        // Les objets d'un tableau, chacun avec son chemin (`armees[0]`).
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
        static Dictionary<string, object> Objet(Dictionary<string, object> objet, string chemin)
        { object brut = ServiceLocal.Valeur(objet, chemin); return brut as Dictionary<string, object> ?? throw ServiceLocal.Refus(chemin, "un objet", brut); }
        static string Texte(Dictionary<string, object> objet, string chemin)
        { object brut = ServiceLocal.Valeur(objet, chemin); return brut is string texte && !string.IsNullOrWhiteSpace(texte) ? texte : throw ServiceLocal.Refus(chemin, "un texte non vide", brut); }
        static string TexteOuNul(Dictionary<string, object> objet, string chemin)
        {
            object brut = ServiceLocal.Valeur(objet, chemin);
            return brut == null ? null : brut is string texte && !string.IsNullOrWhiteSpace(texte) ? texte : throw ServiceLocal.Refus(chemin, "un texte non vide ou null", brut);
        }
    }
}
