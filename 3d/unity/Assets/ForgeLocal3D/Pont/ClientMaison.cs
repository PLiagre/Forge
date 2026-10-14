using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.Net.Http;
namespace Forge.Pont
{
    public sealed class LieuTenu
    {
        public long CellId { get; } public long Rang { get; }
        public LieuTenu(long cellId, long rang) { CellId = cellId; Rang = rang; }
    }
    // Hors carte : CellId, Rang et Position nuls, le nom reste. Nom de maison nul seulement avec sa raison.
    public sealed class SiegeDeMaison
    {
        public long? CellId { get; } public long? Rang { get; } public string Nom { get; } public PointCarte? Position { get; }
        public SiegeDeMaison(long? cellId, long? rang, string nom, PointCarte? position) { CellId = cellId; Rang = rang; Nom = nom; Position = position; }
    }
    public sealed class MaisonLue
    {
        public string Id { get; } public string Nom { get; } public SiegeDeMaison Siege { get; }
        public IReadOnlyList<LieuTenu> Lieux { get; } public IReadOnlyDictionary<string, string> Absents { get; }
        public MaisonLue(string id, string nom, SiegeDeMaison siege, IEnumerable<LieuTenu> lieux, IDictionary<string, string> absents)
        {
            Id = id; Nom = nom; Siege = siege ?? throw new ArgumentNullException(nameof(siege));
            Lieux = new ReadOnlyCollection<LieuTenu>(new List<LieuTenu>(lieux ?? throw new ArgumentNullException(nameof(lieux))));
            Absents = new ReadOnlyDictionary<string, string>(new Dictionary<string, string>(absents ?? throw new ArgumentNullException(nameof(absents))));
        }
    }
    // GET /maison?id= sur 127.0.0.1. Une faute refuse toute la fiche. sorte, part, grenier, flux ne sont pas lus.
    public sealed class ClientMaison : IDisposable
    {
        readonly ServiceLocal service;
        public ClientMaison(int port, TimeSpan delai) { service = new ServiceLocal(port, delai, "maison : "); }
        public void Dispose() => service.Dispose();
        public Lecture<MaisonLue> Lire(string identifiant)
        {
            if (string.IsNullOrWhiteSpace(identifiant)) throw new ArgumentException("un identifiant de maison non vide attendu", nameof(identifiant));
            return service.Demander(HttpMethod.Get, "/maison?id=" + Uri.EscapeDataString(identifiant), racine => Fiche(racine, identifiant));
        }
        static MaisonLue Fiche(Dictionary<string, object> racine, string demande)
        {
            string id = Texte(racine, "id");
            if (!string.Equals(id, demande, StringComparison.Ordinal)) throw new ServiceLocal.Refusee("clé id : \"" + id + "\" reçu pour \"" + demande + "\" demandé");
            var absents = Raisons(racine);
            string nom = TexteOuNul(racine, "nom");
            if (nom == null && !absents.ContainsKey("nom")) throw new ServiceLocal.Refusee("clé absents.nom : raison absente pour un nom nul");
            if (nom != null && absents.ContainsKey("nom")) throw new ServiceLocal.Refusee("clé absents.nom : raison sur un nom présent");
            return new MaisonLue(id, nom, Siege(Objet(racine, "siege"), absents), Lieux(racine), absents);
        }
        static SiegeDeMaison Siege(Dictionary<string, object> siege, Dictionary<string, string> absents)
        {
            object cell = ServiceLocal.Valeur(siege, "siege.cell_id"), rang = ServiceLocal.Valeur(siege, "siege.rang"), point = ServiceLocal.Valeur(siege, "siege.point");
            string nom = Texte(siege, "siege.nom");
            bool vide = cell == null && rang == null && point == null, raison = absents.ContainsKey("siege");
            if (vide && !raison) throw new ServiceLocal.Refusee("clé absents.siege : raison absente pour un siège hors carte");
            if (!vide && (cell == null || rang == null || point == null)) throw new ServiceLocal.Refusee("clé " + (cell == null ? "siege.cell_id" : rang == null ? "siege.rang" : "siege.point") + " : null partiel");
            if (!vide && raison) throw new ServiceLocal.Refusee("clé absents.siege : raison sur un siège présent");
            if (vide) return new SiegeDeMaison(null, null, nom, null);
            return new SiegeDeMaison(ServiceLocal.Entier(siege, "siege.cell_id", 0), ServiceLocal.Entier(siege, "siege.rang", 0), nom, Point(point));
        }
        static PointCarte Point(object brut)
        {
            var point = brut as Dictionary<string, object> ?? throw ServiceLocal.Refus("siege.point", "un objet", brut);
            return new PointCarte(ServiceLocal.Nombre(ServiceLocal.Valeur(point, "siege.point.x_m"), "siege.point.x_m"), ServiceLocal.Nombre(ServiceLocal.Valeur(point, "siege.point.y_m"), "siege.point.y_m"));
        }
        static List<LieuTenu> Lieux(Dictionary<string, object> racine)
        {
            object brut = ServiceLocal.Valeur(racine, "lieux");
            var tableau = brut as List<object> ?? throw ServiceLocal.Refus("lieux", "un tableau", brut);
            var vus = new HashSet<(long, long)>(); var liste = new List<LieuTenu>(tableau.Count);
            for (int i = 0; i < tableau.Count; i++) {
                string chemin = "lieux[" + i.ToString(CultureInfo.InvariantCulture) + "]";
                var lieu = tableau[i] as Dictionary<string, object> ?? throw ServiceLocal.Refus(chemin, "un objet", tableau[i]);
                long cell = ServiceLocal.Entier(lieu, chemin + ".cell_id", 0), rang = ServiceLocal.Entier(lieu, chemin + ".rang", 0);
                if (!vus.Add((cell, rang))) throw new ServiceLocal.Refusee("clé " + chemin + " : couple déjà lu");
                liste.Add(new LieuTenu(cell, rang)); }
            return liste;
        }
        static Dictionary<string, string> Raisons(Dictionary<string, object> racine)
        {
            object brut = ServiceLocal.Valeur(racine, "absents");
            var objet = brut as Dictionary<string, object> ?? throw ServiceLocal.Refus("absents", "un objet", brut);
            var raisons = new Dictionary<string, string>(objet.Count);
            foreach (var entree in objet) raisons.Add(entree.Key, entree.Value is string texte && !string.IsNullOrWhiteSpace(texte) ? texte : throw ServiceLocal.Refus("absents." + entree.Key, "un texte non vide", entree.Value));
            return raisons;
        }
        static Dictionary<string, object> Objet(Dictionary<string, object> objet, string chemin)
        { object brut = ServiceLocal.Valeur(objet, chemin); return brut as Dictionary<string, object> ?? throw ServiceLocal.Refus(chemin, "un objet", brut); }
        static string Texte(Dictionary<string, object> objet, string chemin)
        { object brut = ServiceLocal.Valeur(objet, chemin); return brut is string texte && !string.IsNullOrWhiteSpace(texte) ? texte : throw ServiceLocal.Refus(chemin, "un texte non vide", brut); }
        static string TexteOuNul(Dictionary<string, object> objet, string chemin)
        { object brut = ServiceLocal.Valeur(objet, chemin); if (brut == null) return null; return brut is string texte && !string.IsNullOrWhiteSpace(texte) ? texte : throw ServiceLocal.Refus(chemin, "un texte non vide ou null", brut); }
    }
}
