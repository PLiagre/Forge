using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.Net.Http;
namespace Forge.Pont
{
    // `ReserveJours` nul veut dire « lieu sans habitants » : une absence déclarée, pas une réserve de zéro jour.
    // Une réserve négative est lue telle quelle (dette plus lourde que le stock).
    public sealed class LieuServi
    {
        public long Rang { get; } public long Population { get; } public double SurfaceKm2 { get; } public double? ReserveJours { get; }
        public LieuServi(long rang, long population, double surfaceKm2, double? reserveJours) { Rang = rang; Population = population; SurfaceKm2 = surfaceKm2; ReserveJours = reserveJours; }
    }
    // Les lieux d'une cellule, par rang : 0, 1, … n−1 sans trou.
    public sealed class CelluleServie
    {
        public long CellId { get; } public IReadOnlyList<LieuServi> Lieux { get; }
        public CelluleServie(long cellId, IEnumerable<LieuServi> lieux) { CellId = cellId; Lieux = new ReadOnlyCollection<LieuServi>(new List<LieuServi>(lieux)); }
    }
    public sealed class LieuxLus
    {
        public long Tick { get; } public DateDuMonde Date { get; } public long CellCount { get; } public IReadOnlyList<CelluleServie> Cellules { get; }
        private readonly Dictionary<long, CelluleServie> parCellule = new Dictionary<long, CelluleServie>();
        public LieuxLus(long tick, DateDuMonde date, long cellCount, IEnumerable<CelluleServie> cellules)
        {
            Tick = tick; Date = date; CellCount = cellCount; var liste = new List<CelluleServie>(cellules);
            foreach (CelluleServie cellule in liste) parCellule.Add(cellule.CellId, cellule);
            Cellules = new ReadOnlyCollection<CelluleServie>(liste);
        }
        // Nul si le service n'a servi aucun lieu pour cette cellule.
        public CelluleServie Cellule(long cellId) => parCellule.TryGetValue(cellId, out CelluleServie cellule) ? cellule : null;
    }
    // GET /lieux. La première lecture peut calculer la carte : délai d'au moins 10 s.
    // Une clé fautive refuse toute la réponse, sans cellule partielle ni zéro de remplacement.
    public sealed class ClientLieux : IDisposable
    {
        public static readonly TimeSpan DelaiMinimal = TimeSpan.FromSeconds(10);
        private readonly ServiceLocal service;
        public ClientLieux(int port, TimeSpan delai)
        {
            if (delai < DelaiMinimal || delai.TotalMilliseconds > int.MaxValue)
                throw new ArgumentOutOfRangeException(nameof(delai), delai, "un délai d'au moins 10 s, fini, attendu");
            service = new ServiceLocal(port, delai, "lieux : ");
        }
        public void Dispose() => service.Dispose();
        public Lecture<LieuxLus> Lire() => service.Demander(HttpMethod.Get, "/lieux", Racine);
        static LieuxLus Racine(Dictionary<string, object> racine)
        {
            object brutes = ServiceLocal.Valeur(racine, "cells");
            if (!(brutes is List<object> tableau) || tableau.Count == 0) throw ServiceLocal.Refus("cells", "un tableau non vide", brutes);
            var ids = new HashSet<long>(); var cellules = new List<CelluleServie>(tableau.Count);
            for (int i = 0; i < tableau.Count; i++) cellules.Add(Cellule(tableau[i], "cells[" + i.ToString(CultureInfo.InvariantCulture) + "]", ids));
            long annonce = Entier(racine, "cell_count");
            if (annonce != cellules.Count)
                throw new ServiceLocal.Refusee("clé cell_count : " + cellules.Count.ToString(CultureInfo.InvariantCulture) + " cellules lues, " + annonce.ToString(CultureInfo.InvariantCulture) + " annoncées");
            return new LieuxLus(ServiceLocal.Entier(racine, "tick", 0), ServiceLocal.Date(racine), annonce, cellules);
        }
        static CelluleServie Cellule(object valeur, string chemin, HashSet<long> ids)
        {
            var cellule = valeur as Dictionary<string, object> ?? throw ServiceLocal.Refus(chemin, "un objet", valeur);
            long id = Entier(cellule, chemin + ".cell_id");
            if (!ids.Add(id)) throw new ServiceLocal.Refusee("clé " + chemin + ".cell_id : " + id.ToString(CultureInfo.InvariantCulture) + " déjà lu");
            string ici = chemin + ".lieux"; object brut = ServiceLocal.Valeur(cellule, ici);
            if (!(brut is List<object> tableau) || tableau.Count == 0) throw ServiceLocal.Refus(ici, "un tableau non vide", brut);
            var rangs = new HashSet<long>(); var lieux = new List<LieuServi>(tableau.Count);
            for (int i = 0; i < tableau.Count; i++) lieux.Add(Lieu(tableau[i], ici + "[" + i.ToString(CultureInfo.InvariantCulture) + "]", i, rangs));
            return new CelluleServie(id, lieux);
        }
        // Les rangs vont de 0 à n−1 dans l'ordre servi : le lieu à la position `position` porte le rang `position`.
        static LieuServi Lieu(object valeur, string chemin, int position, HashSet<long> rangs)
        {
            var lieu = valeur as Dictionary<string, object> ?? throw ServiceLocal.Refus(chemin, "un objet", valeur);
            long rang = Entier(lieu, chemin + ".rang");
            if (!rangs.Add(rang)) throw new ServiceLocal.Refusee("clé " + chemin + ".rang : " + rang.ToString(CultureInfo.InvariantCulture) + " déjà lu");
            if (rang != position) throw new ServiceLocal.Refusee("clé " + chemin + ".rang : rang " + position.ToString(CultureInfo.InvariantCulture) + " attendu, reçu " + rang.ToString(CultureInfo.InvariantCulture));
            long population = Entier(lieu, chemin + ".population");
            string cheminSurface = chemin + ".surface_km2"; double surface = ServiceLocal.Nombre(ServiceLocal.Valeur(lieu, cheminSurface), cheminSurface);
            if (surface <= 0) throw ServiceLocal.Refus(cheminSurface, "un nombre fini > 0", surface);
            return new LieuServi(rang, population, surface, Reserve(lieu, chemin + ".reserve_jours"));
        }
        // Un nombre fini, négatif compris, ou null : la réserve d'un lieu sans habitants est absente.
        static double? Reserve(Dictionary<string, object> lieu, string chemin)
        {
            object valeur = ServiceLocal.Valeur(lieu, chemin); if (valeur == null) return null;
            return valeur is double nombre && !double.IsNaN(nombre) && !double.IsInfinity(nombre) ? nombre : throw ServiceLocal.Refus(chemin, "null ou un nombre fini", valeur);
        }
        // Entier ≥ 0 sous 2^53, garde de ServiceLocal. Un booléen ou un texte n'est pas lu comme zéro.
        static long Entier(Dictionary<string, object> objet, string chemin)
        { object valeur = ServiceLocal.Valeur(objet, chemin); if (!(valeur is double)) throw ServiceLocal.Refus(chemin, "un entier ≥ 0 sous 2^53", valeur); return ServiceLocal.Entier(objet, chemin, 0); }
    }
}
