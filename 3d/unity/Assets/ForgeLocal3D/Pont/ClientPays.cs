using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.Net.Http;
namespace Forge.Pont
{
    // Une jauge du pays : ses bornes, son neutre, et ce que dit `data/jauges.toml` d'elle. minimum ≤ valeur ≤ maximum.
    public sealed class JaugeLue
    {
        public string Nom { get; } public string Dit { get; } public double Valeur { get; } public double Minimum { get; } public double Maximum { get; } public double Neutre { get; }
        public JaugeLue(string nom, string dit, double valeur, double minimum, double maximum, double neutre)
        { Nom = nom; Dit = dit; Valeur = valeur; Minimum = minimum; Maximum = maximum; Neutre = neutre; }
    }
    // Une réserve de points. ParMois nul : le chef de la maison n'est pas connu, le gain est absent (jamais zéro).
    public sealed class PointsLus
    {
        public string Nom { get; } public string Dit { get; } public double Valeur { get; } public double Plafond { get; } public string Domaine { get; } public double? ParMois { get; }
        public PointsLus(string nom, string dit, double valeur, double plafond, string domaine, double? parMois)
        { Nom = nom; Dit = dit; Valeur = valeur; Plafond = plafond; Domaine = domaine; ParMois = parMois; }
    }
    // Ce qu'une jauge pose au pays : la grandeur, son nom lu dans `jauges.grandeurs`, la valeur (0,02 = +2 %) et la jauge de la source.
    public sealed class PoseLue
    {
        public string Grandeur { get; } public string NomDeLaGrandeur { get; } public double Valeur { get; } public string Jauge { get; }
        public PoseLue(string grandeur, string nomDeLaGrandeur, double valeur, string jauge)
        { Grandeur = grandeur; NomDeLaGrandeur = nomDeLaGrandeur; Valeur = valeur; Jauge = jauge; }
    }
    // Compétences nulles : chef non connu, avec sa raison dans SansChef ; alors chaque ParMois est nul. Sinon SansChef est nul.
    public sealed class PaysLu
    {
        public string MaisonId { get; } public string Nom { get; } public long Tick { get; } public DateDuMonde Date { get; }
        public IReadOnlyDictionary<string, JaugeLue> Jauges { get; } public IReadOnlyDictionary<string, PointsLus> Points { get; }
        public IReadOnlyDictionary<string, long> Competences { get; } public string SansChef { get; } public IReadOnlyList<PoseLue> Poses { get; }
        public PaysLu(string maisonId, string nom, long tick, DateDuMonde date, IDictionary<string, JaugeLue> jauges, IDictionary<string, PointsLus> points,
            IDictionary<string, long> competences, string sansChef, IEnumerable<PoseLue> poses)
        {
            MaisonId = maisonId; Nom = nom; Tick = tick; Date = date; SansChef = sansChef;
            Jauges = new ReadOnlyDictionary<string, JaugeLue>(new Dictionary<string, JaugeLue>(jauges ?? throw new ArgumentNullException(nameof(jauges))));
            Points = new ReadOnlyDictionary<string, PointsLus>(new Dictionary<string, PointsLus>(points ?? throw new ArgumentNullException(nameof(points))));
            Competences = competences == null ? null : new ReadOnlyDictionary<string, long>(new Dictionary<string, long>(competences));
            Poses = new ReadOnlyCollection<PoseLue>(new List<PoseLue>(poses ?? throw new ArgumentNullException(nameof(poses))));
        }
    }
    // GET /pays?maison= sur 127.0.0.1. Une faute refuse toute la réponse et nomme la clé. Les lieux, les totaux, les gestes et les bâtiments ne sont pas lus.
    public sealed class ClientPays : IDisposable
    {
        readonly ServiceLocal service;
        public ClientPays(int port, TimeSpan delai) { service = new ServiceLocal(port, delai, "pays : "); }
        public void Dispose() => service.Dispose();
        public Lecture<PaysLu> Lire(string id)
        {
            if (string.IsNullOrWhiteSpace(id)) throw new ArgumentException("un identifiant de maison non vide attendu", nameof(id));
            return service.Demander(HttpMethod.Get, "/pays?maison=" + Uri.EscapeDataString(id), racine => Pays(racine, id));
        }
        static PaysLu Pays(Dictionary<string, object> racine, string demande)
        {
            var maison = Objet(racine, "maison"); string id = Texte(maison, "maison.id");
            if (!string.Equals(id, demande, StringComparison.Ordinal)) throw new ServiceLocal.Refusee("clé maison.id : \"" + id + "\" reçu pour \"" + demande + "\" demandé");
            string nom = Texte(maison, "maison.nom"); long tick = ServiceLocal.Entier(racine, "tick", 0); DateDuMonde date = ServiceLocal.Date(racine);
            var jauges = Objet(racine, "jauges"); var servies = Jauges(Objet(jauges, "jauges.jauges"));
            var absents = Raisons(Objet(jauges, "jauges.absents")); var competences = Competences(jauges, absents);
            string sansChef = absents.TryGetValue("competences", out string raison) ? raison : null;
            var points = Points(Objet(jauges, "jauges.points"), competences);
            return new PaysLu(id, nom, tick, date, servies, points, competences, sansChef, Poses(jauges, id, servies, Grandeurs(Objet(jauges, "jauges.grandeurs"))));
        }
        static Dictionary<string, JaugeLue> Jauges(Dictionary<string, object> brutes)
        {
            var jauges = new Dictionary<string, JaugeLue>(brutes.Count);
            foreach (var e in brutes)
            {
                string chemin = "jauges.jauges." + e.Key; var j = e.Value as Dictionary<string, object> ?? throw ServiceLocal.Refus(chemin, "un objet", e.Value);
                double valeur = ServiceLocal.Nombre(ServiceLocal.Valeur(j, chemin + ".valeur"), chemin + ".valeur"), minimum = ServiceLocal.Nombre(ServiceLocal.Valeur(j, chemin + ".minimum"), chemin + ".minimum");
                double maximum = ServiceLocal.Nombre(ServiceLocal.Valeur(j, chemin + ".maximum"), chemin + ".maximum"), neutre = ServiceLocal.Nombre(ServiceLocal.Valeur(j, chemin + ".neutre"), chemin + ".neutre");
                if (valeur < minimum || valeur > maximum) throw ServiceLocal.Refus(chemin + ".valeur", "un nombre entre " + minimum.ToString("R", CultureInfo.InvariantCulture) + " et " + maximum.ToString("R", CultureInfo.InvariantCulture), valeur);
                jauges.Add(e.Key, new JaugeLue(Texte(j, chemin + ".nom"), Texte(j, chemin + ".dit"), valeur, minimum, maximum, neutre));
            }
            return jauges;
        }
        // Chaque gain est lu avec les compétences : connues, un nombre ; absentes, nul.
        static Dictionary<string, PointsLus> Points(Dictionary<string, object> brutes, Dictionary<string, long> competences)
        {
            var points = new Dictionary<string, PointsLus>(brutes.Count);
            foreach (var e in brutes)
            {
                string chemin = "jauges.points." + e.Key; var p = e.Value as Dictionary<string, object> ?? throw ServiceLocal.Refus(chemin, "un objet", e.Value);
                double valeur = ServiceLocal.Nombre(ServiceLocal.Valeur(p, chemin + ".valeur"), chemin + ".valeur");
                if (valeur < 0) throw ServiceLocal.Refus(chemin + ".valeur", "un nombre fini ≥ 0", valeur);
                double plafond = ServiceLocal.Nombre(ServiceLocal.Valeur(p, chemin + ".plafond"), chemin + ".plafond"); string domaine = Texte(p, chemin + ".domaine");
                if (competences != null && !competences.ContainsKey(domaine)) throw new ServiceLocal.Refusee("clé " + chemin + ".domaine : \"" + domaine + "\" absent des compétences");
                object brut = ServiceLocal.Valeur(p, chemin + ".par_mois"); double? parMois = null;
                if (competences == null && brut != null) throw ServiceLocal.Refus(chemin + ".par_mois", "null (chef non connu)", brut);
                if (competences != null) parMois = brut == null ? throw ServiceLocal.Refus(chemin + ".par_mois", "un nombre fini (chef connu)", brut) : ServiceLocal.Nombre(brut, chemin + ".par_mois");
                points.Add(e.Key, new PointsLus(Texte(p, chemin + ".nom"), Texte(p, chemin + ".dit"), valeur, plafond, domaine, parMois));
            }
            return points;
        }
        static Dictionary<string, long> Competences(Dictionary<string, object> jauges, Dictionary<string, string> absents)
        {
            object brut = ServiceLocal.Valeur(jauges, "jauges.competences"); bool raison = absents.ContainsKey("competences");
            if (brut == null) { if (!raison) throw new ServiceLocal.Refusee("clé jauges.absents.competences : raison absente pour des compétences nulles"); return null; }
            if (raison) throw new ServiceLocal.Refusee("clé jauges.absents.competences : raison sur des compétences présentes");
            var objet = brut as Dictionary<string, object> ?? throw ServiceLocal.Refus("jauges.competences", "un objet ou null", brut);
            var competences = new Dictionary<string, long>(objet.Count);
            foreach (var e in objet) competences.Add(e.Key, ServiceLocal.Entier(objet, "jauges.competences." + e.Key, 0));
            return competences;
        }
        static Dictionary<string, string> Grandeurs(Dictionary<string, object> brutes)
        {
            var noms = new Dictionary<string, string>(brutes.Count);
            foreach (var e in brutes) noms.Add(e.Key, e.Value is string texte && !string.IsNullOrWhiteSpace(texte) ? texte : throw ServiceLocal.Refus("jauges.grandeurs." + e.Key, "un texte non vide", e.Value));
            return noms;
        }
        // Une pose vient de `jauge:<jauge>:<maison>` : cette maison, une jauge servie ; sa grandeur a son nom.
        static List<PoseLue> Poses(Dictionary<string, object> jauges, string maison, Dictionary<string, JaugeLue> servies, Dictionary<string, string> noms)
        {
            object brut = ServiceLocal.Valeur(jauges, "jauges.modificateurs");
            var tableau = brut as List<object> ?? throw ServiceLocal.Refus("jauges.modificateurs", "un tableau", brut);
            var poses = new List<PoseLue>(tableau.Count);
            for (int i = 0; i < tableau.Count; i++)
            {
                string chemin = "jauges.modificateurs[" + i.ToString(CultureInfo.InvariantCulture) + "]";
                var pose = tableau[i] as Dictionary<string, object> ?? throw ServiceLocal.Refus(chemin, "un objet", tableau[i]);
                string grandeur = Texte(pose, chemin + ".grandeur"), source = Texte(pose, chemin + ".source");
                double valeur = ServiceLocal.Nombre(ServiceLocal.Valeur(pose, chemin + ".valeur"), chemin + ".valeur");
                string[] morceaux = source.Split(':');
                if (morceaux.Length != 3 || morceaux[0] != "jauge" || morceaux[2] != maison || !servies.ContainsKey(morceaux[1]))
                    throw new ServiceLocal.Refusee("clé " + chemin + ".source : \"jauge:<jauge servie>:" + maison + "\" attendu, reçu \"" + source + "\"");
                if (!noms.TryGetValue(grandeur, out string nomDeLaGrandeur)) throw new ServiceLocal.Refusee("clé " + chemin + ".grandeur : \"" + grandeur + "\" absente de jauges.grandeurs");
                poses.Add(new PoseLue(grandeur, nomDeLaGrandeur, valeur, morceaux[1]));
            }
            return poses;
        }
        static Dictionary<string, string> Raisons(Dictionary<string, object> brutes)
        {
            var raisons = new Dictionary<string, string>(brutes.Count);
            foreach (var e in brutes) raisons.Add(e.Key, e.Value is string texte && !string.IsNullOrWhiteSpace(texte) ? texte : throw ServiceLocal.Refus("jauges.absents." + e.Key, "un texte non vide", e.Value));
            return raisons;
        }
        static Dictionary<string, object> Objet(Dictionary<string, object> objet, string chemin)
        { object brut = ServiceLocal.Valeur(objet, chemin); return brut as Dictionary<string, object> ?? throw ServiceLocal.Refus(chemin, "un objet", brut); }
        static string Texte(Dictionary<string, object> objet, string chemin)
        { object brut = ServiceLocal.Valeur(objet, chemin); return brut is string texte && !string.IsNullOrWhiteSpace(texte) ? texte : throw ServiceLocal.Refus(chemin, "un texte non vide", brut); }
    }
}
