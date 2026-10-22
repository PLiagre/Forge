using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.Net.Http;

namespace Forge.Pont
{
    // Le rang 0 servi par `/lieu?cell=X&bourg=1`, au tick de sa réponse. `Stocks` porte les seules marchandises reçues, valeurs
    // exactes : une absente n'a pas de clé, un zéro est une mesure. La faim locale ne se déduit d'aucun stock ni de la cellule.
    public sealed class BourgLu
    {
        public long CellId { get; } public long Tick { get; } public DateDuMonde Date { get; }
        public long Rang { get; } public long Population { get; } public IReadOnlyDictionary<string, double> Stocks { get; }
        public long DureeFaimTicks { get; } public long TickLocal { get; }
        public BourgLu(long cellId, long tick, DateDuMonde date, long rang, long population, IDictionary<string, double> stocks, long dureeFaimTicks, long tickLocal)
        {
            CellId = cellId; Tick = tick; Date = date; Rang = rang; Population = population; DureeFaimTicks = dureeFaimTicks; TickLocal = tickLocal;
            Stocks = new ReadOnlyDictionary<string, double>(new Dictionary<string, double>(stocks ?? throw new ArgumentNullException(nameof(stocks))));
        }
    }

    // `/occupation?cell=X` tel que servi, dans ses ordres : la base de 1400, toute habitée, et les maisons bâties, seules à loger
    // les artisans ; la base ne s'ajoute jamais au logement. `Logement` null ou à -1 (métiers non calculés) : `RaisonDuLogement` le dit.
    public sealed class OccupationLue
    {
        public long CellId { get; } public long Rang { get; } public long Tick { get; } public DateDuMonde Date { get; }
        public IReadOnlyList<(long Rang, long Foyers)> Base { get; }
        public IReadOnlyList<(long Identifiant, long Capacite, long Loges)> Batiments { get; }
        public Logement Logement { get; } public string RaisonDuLogement { get; }
        public OccupationLue(long cellId, long rang, long tick, DateDuMonde date, IEnumerable<(long Rang, long Foyers)> ilots,
            IEnumerable<(long Identifiant, long Capacite, long Loges)> batiments, Logement logement, string raisonDuLogement)
        {
            CellId = cellId; Rang = rang; Tick = tick; Date = date; Logement = logement; RaisonDuLogement = raisonDuLogement;
            Base = new ReadOnlyCollection<(long, long)>(new List<(long, long)>(ilots ?? throw new ArgumentNullException(nameof(ilots))));
            Batiments = new ReadOnlyCollection<(long, long, long)>(new List<(long, long, long)>(batiments ?? throw new ArgumentNullException(nameof(batiments))));
        }
    }

    // Deux lectures indépendantes, chacune avec son tick et sa date : ni fusion, ni attente de tick, ni réussite antérieure gardée ;
    // le consommateur compare cellule et tick avant de les associer. Une faute refuse toute la lecture et nomme son chemin.
    public sealed class ClientVieDuBourg : IDisposable
    {
        private readonly ServiceLocal service;

        public ClientVieDuBourg(int port, TimeSpan delai) { service = new ServiceLocal(port, delai, ""); }

        public void Dispose() => service.Dispose();

        public Lecture<BourgLu> LireBourg(long cellId) =>
            Nommer("bourg", cellId, service.Demander(HttpMethod.Get, "/lieu?cell=" + Texte(cellId) + "&bourg=1", racine => Bourg(racine, cellId)));

        public Lecture<OccupationLue> LireOccupation(long cellId) =>
            Nommer("occupation", cellId, service.Demander(HttpMethod.Get, "/occupation?cell=" + Texte(cellId), racine => Occupation(racine, cellId)));

        private static Lecture<T> Nommer<T>(string route, long cellId, Lecture<T> lecture) where T : class =>
            lecture.Presente ? lecture : Lecture<T>.Absent(route + " de la cellule " + Texte(cellId) + " : " + lecture.Absence);

        private static BourgLu Bourg(Dictionary<string, object> racine, long demandee)
        {
            long cellId = Exige(racine, "cell_id", demandee, "cellule demandée"), tick = ServiceLocal.Entier(racine, "tick", 0);
            DateDuMonde date = ServiceLocal.Date(racine);
            var bourg = De<Dictionary<string, object>>(racine, "bourg", "un objet");
            long rang = Exige(bourg, "bourg.rang", 0, "le bourg"), population = ServiceLocal.Entier(bourg, "bourg.population", 0);
            var stocks = new Dictionary<string, double>();
            foreach (var m in De<Dictionary<string, object>>(bourg, "bourg.stocks", "un objet"))
                stocks.Add(m.Key, ServiceLocal.Nombre(m.Value, "bourg.stocks." + m.Key) is double kg && kg >= 0 ? kg : throw ServiceLocal.Refus("bourg.stocks." + m.Key, "un stock ≥ 0", m.Value));
            long faim = ServiceLocal.Entier(bourg, "bourg.duree_faim_ticks", 0), tickLocal = Exige(bourg, "bourg.tick", tick, "tick de la réponse");
            return new BourgLu(cellId, tick, date, rang, population, stocks, faim, tickLocal);
        }

        private static OccupationLue Occupation(Dictionary<string, object> racine, long demandee)
        {
            long cellId = Exige(racine, "cell_id", demandee, "cellule demandée"), rang = Exige(racine, "rang", 0, "le bourg"), tick = ServiceLocal.Entier(racine, "tick", 0);
            DateDuMonde date = ServiceLocal.Date(racine);
            var ilots = new List<(long Rang, long Foyers)>();
            List<object> brutes = De<List<object>>(racine, "base", "un tableau");
            for (int i = 0; i < brutes.Count; i++)
            {
                var ilot = Element(brutes, i, "base", out string chemin);
                ilots.Add((Exige(ilot, chemin + ".rang", i, "rangs successifs depuis 0"), ServiceLocal.Entier(ilot, chemin + ".foyers", 1)));
            }
            // Le logement d'abord : il dit si les comptes des maisons sont calculés.
            object brut = ServiceLocal.Valeur(racine, "logement");
            var l = brut == null ? null : brut as Dictionary<string, object> ?? throw ServiceLocal.Refus("logement", "un objet ou null", brut);
            Logement logement = l == null ? null : new Logement(ServiceLocal.Entier(l, "logement.capacite", 0), ServiceLocal.Entier(l, "logement.loges", -1), ServiceLocal.Entier(l, "logement.sans_logis", -1));
            if (logement != null && (logement.SansLogis == -1) != (logement.Loges == -1)) throw Ecart("logement.sans_logis", "-1 avec loges à -1, et seulement avec lui", logement.SansLogis);
            bool nonCalcules = logement != null && logement.Loges == -1;
            string raison = logement == null ? "logement null déclaré par le service : aucun bâtiment au plan" : nonCalcules ? "métiers non calculés : loges et sans_logis à -1" : null;
            List<object> maisons = De<List<object>>(racine, "batiments", "un tableau");
            if (logement == null && maisons.Count > 0) throw new ServiceLocal.Refusee("clé logement : null déclaré avec " + Texte(maisons.Count) + " bâtiments servis");
            var batiments = new List<(long Identifiant, long Capacite, long Loges)>();
            long capacites = 0, loges = 0;
            for (int i = 0; i < maisons.Count; i++)
            {
                var maison = Element(maisons, i, "batiments", out string chemin);
                long identifiant = ServiceLocal.Entier(maison, chemin + ".identifiant", 0);
                if (i > 0 && identifiant <= batiments[i - 1].Identifiant) throw Ecart(chemin + ".identifiant", "plus de " + Texte(batiments[i - 1].Identifiant) + " (ordre strictement croissant)", identifiant);
                long capacite = ServiceLocal.Entier(maison, chemin + ".capacite", 1), loge = ServiceLocal.Entier(maison, chemin + ".loges", -1);
                if ((loge == -1) != nonCalcules || loge > capacite) throw Ecart(chemin + ".loges", nonCalcules ? "-1 (métiers non calculés)" : "un entier de 0 à " + Texte(capacite), loge);
                batiments.Add((identifiant, capacite, loge)); capacites += capacite; loges += loge;
            }
            if (logement != null && capacites != logement.Capacite) throw Ecart("logement.capacite", Texte(capacites) + " (somme des maisons)", logement.Capacite);
            if (logement != null && !nonCalcules && loges != logement.Loges) throw Ecart("logement.loges", Texte(loges) + " (somme des maisons)", logement.Loges);
            return new OccupationLue(cellId, rang, tick, date, ilots, batiments, logement, raison);
        }

        // Un entier qui doit valoir exactement `attendu` : la cellule demandée, le rang 0, le tick de la réponse.
        private static long Exige(Dictionary<string, object> objet, string chemin, long attendu, string sens)
        { long lu = ServiceLocal.Entier(objet, chemin, 0); return lu == attendu ? lu : throw Ecart(chemin, Texte(attendu) + " (" + sens + ")", lu); }
        private static T De<T>(Dictionary<string, object> objet, string chemin, string attendu) where T : class
        { object valeur = ServiceLocal.Valeur(objet, chemin); return valeur as T ?? throw ServiceLocal.Refus(chemin, attendu, valeur); }
        private static Dictionary<string, object> Element(List<object> liste, int i, string nom, out string chemin)
        { chemin = nom + "[" + Texte(i) + "]"; return liste[i] as Dictionary<string, object> ?? throw ServiceLocal.Refus(chemin, "un objet", liste[i]); }
        private static ServiceLocal.Refusee Ecart(string chemin, string attendu, long recu) => new ServiceLocal.Refusee("clé " + chemin + " : " + attendu + " attendu, reçu " + Texte(recu));
        private static string Texte(long nombre) => nombre.ToString(CultureInfo.InvariantCulture);
    }
}
