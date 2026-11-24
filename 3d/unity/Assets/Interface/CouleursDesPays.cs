using System;
using System.Collections.Generic;
using System.Linq;
using Forge.Pont;
using UnityEngine;

namespace Forge.Interface
{
    // La couleur de chaque pays servi sur la carte politique, et son liseré. Un bloc est un pays racine et tous ceux qui
    // relèvent de lui en remontant la chaîne `suzerain` ; deux blocs voisins prennent deux pigments différents de
    // `SocleInterface.PigmentsDesPays`, et deux pays voisins de blocs différents restent à `ECART_MIN` au moins (ΔE, CIE 1976).
    // La racine porte le pigment de son bloc ; un vassal le porte éclairci d'une des `PARTS`, toujours plus clair que son
    // suzerain, et deux vassaux voisins d'un même bloc ne sont pas éclaircis de la même part. Le liseré d'un membre d'un
    // `ensemble` est celui de l'ensemble (`SocleInterface.LisereDeLEnsemble`) ; celui d'un autre pays est tiré de son pigment.
    // Chaque bloc préfère le pigment tiré de l'identifiant de sa racine, et garde d'une lecture à l'autre celui qu'il avait
    // tant qu'aucun voisin ne le lui interdit : une terre prise ne recolore que ce qu'elle force. De la présentation : aucun
    // nombre du monde n'en sort, et la même lecture donne les mêmes couleurs.
    public sealed class CouleursDesPays
    {
        public const float ECART_MIN = 10f;
        // Les parts d'éclaircissement d'un vassal, de la plus sombre à la plus claire.
        public static readonly IReadOnlyList<float> PARTS = new[] { .22f, .34f, .46f, .58f };

        readonly Dictionary<string, string> racines = new Dictionary<string, string>();
        readonly Dictionary<string, int> pigments = new Dictionary<string, int>(); // par racine, l'indice de son pigment
        readonly Dictionary<string, int> parts = new Dictionary<string, int>(); // par pays, 0 pour une racine, k + 1 pour PARTS[k]
        readonly Dictionary<string, Color> couleurs = new Dictionary<string, Color>(), liseres = new Dictionary<string, Color>();
        readonly Dictionary<string, HashSet<string>> voisins;

        // Les pays voisins de chaque pays servi : ceux de deux terres qui se touchent, et ceux des lieux d'un autre pays,
        // voisins de tout pays de leur terre et des terres d'à côté. Une terre sans pays n'a pas de voisin.
        public IReadOnlyDictionary<string, HashSet<string>> Voisins => voisins;
        // Combien de paires de voisins n'ont pu être séparées faute de pigment permis : 0 sur une carte qu'on peut colorier.
        public int Conflits { get; private set; }

        CouleursDesPays(Dictionary<string, HashSet<string>> voisins) { this.voisins = voisins; }

        // Le pigment d'un pays servi ; celui tiré de son identifiant pour un pays que la lecture ne sert pas, le gris des terres sans pays pour null.
        public Color Couleur(string id) => id == null ? SansPays : couleurs.TryGetValue(id, out Color c) ? c : Repli(id);
        public Color Lisere(string id) => id != null && liseres.TryGetValue(id, out Color c) ? c : CalquesCarte.LisereDuPigment(Couleur(id));
        // La racine du bloc du pays, et l'indice de son éclaircissement (0 : la racine elle-même).
        public string Racine(string id) => id != null && racines.TryGetValue(id, out string r) ? r : id;
        public int Part(string id) => id != null && parts.TryGetValue(id, out int p) ? p : 0;
        public static Color SansPays => SocleInterface.Pigment(MaillageDeCarte.CouleurSansPuissance);
        public static Color Repli(string id) => SocleInterface.PigmentsDesPays[Prefere(id)];
        public static Color Peindre(int pigment, int part) => part == 0 ? SocleInterface.PigmentsDesPays[pigment] : SocleInterface.Eclaircir(SocleInterface.PigmentsDesPays[pigment], PARTS[part - 1]);
        public bool MemesCouleurs(CouleursDesPays autre) => autre != null && couleurs.Count == autre.couleurs.Count && couleurs.All(p => autre.couleurs.TryGetValue(p.Key, out Color c) && c == p.Value)
            && liseres.Count == autre.liseres.Count && liseres.All(p => autre.liseres.TryGetValue(p.Key, out Color c) && c == p.Value);

        // L'indice du pigment tiré de l'identifiant (FNV-1a) : le même sur toute machine.
        static int Prefere(string id)
        {
            uint h = 2166136261u; foreach (char c in id ?? "") { h ^= c; h *= 16777619u; }
            return (int)(h % (uint)SocleInterface.PigmentsDesPays.Count);
        }

        // L'écart perçu entre deux couleurs : la distance de leurs coordonnées Lab (CIE 1976, blanc D65), lues en sRGB.
        public static float Ecart(Color a, Color b)
        {
            Vector3 p = Lab(a), q = Lab(b); return (p - q).magnitude;
        }
        static Vector3 Lab(Color c)
        {
            float Lin(float v) => v <= .04045f ? v / 12.92f : Mathf.Pow((v + .055f) / 1.055f, 2.4f);
            float F(float t) => t > .008856f ? Mathf.Pow(t, 1f / 3f) : 7.787f * t + 16f / 116f;
            float r = Lin(c.r), g = Lin(c.g), b = Lin(c.b);
            float x = F((.4124f * r + .3576f * g + .1805f * b) / .95047f), y = F(.2126f * r + .7152f * g + .0722f * b), z = F((.0193f * r + .1192f * g + .9505f * b) / 1.08883f);
            return new Vector3(116f * y - 16f, 500f * (x - y), 200f * (y - z));
        }

        // Les voisinages entre pays. Deux terres qui se touchent lient leurs pays ; un lieu d'un autre pays lie le sien à celui
        // de sa terre et à ceux des terres d'à côté. `lieux` : les lieux qui se touchent sur le terrain (`LieuxQuiSeTouchent`),
        // qui lient aussi deux lieux d'une même terre ; sans eux, deux lieux d'autres pays d'une même terre ne se lient pas.
        public static Dictionary<string, HashSet<string>> VoisinsDesPays(TerresDeLaCarte terres, IEnumerable<CoteDeCarte> cotes, IEnumerable<(long terre, long rang, long autreTerre, long autreRang)> lieux = null)
        {
            var voisins = new Dictionary<string, HashSet<string>>();
            void Lier(string a, string b)
            {
                if (a == null || b == null || a == b) return;
                if (!voisins.TryGetValue(a, out var va)) voisins[a] = va = new HashSet<string>(); va.Add(b);
                if (!voisins.TryGetValue(b, out var vb)) voisins[b] = vb = new HashSet<string>(); vb.Add(a);
            }
            var autour = new Dictionary<long, List<long>>();
            if (cotes != null)
                foreach (var cote in cotes)
                {
                    Lier(terres.PaysDe(cote.Dedans), terres.PaysDe(cote.Dehors));
                    if (!autour.TryGetValue(cote.Dedans, out var liste)) autour[cote.Dedans] = liste = new List<long>(); liste.Add(cote.Dehors);
                }
            foreach (var terre in terres.Terres)
                foreach (var lieu in terre.AutresPays)
                {
                    Lier(lieu.Pays, terre.Pays);
                    if (autour.TryGetValue(terre.CellId, out var proches)) foreach (long proche in proches) Lier(lieu.Pays, terres.PaysDe(proche));
                }
            if (lieux != null) foreach (var (t, r, u, s) in lieux) Lier(terres.PaysDuLieu(t, r), terres.PaysDuLieu(u, s));
            return voisins;
        }

        // Les paires de lieux qui se touchent sur la grille du terrain, en (terre, rang) : deux texels côte à côte, d'est en
        // ouest ou du nord au sud, de deux lieux différents. La mer ne touche rien. Se calcule hors du fil principal.
        public static List<(long terre, long rang, long autreTerre, long autreRang)> LieuxQuiSeTouchent(TerrainDeCarte terrain, CarteLue lue)
        {
            var paires = new HashSet<(int, int)>(); IReadOnlyList<ushort> grille = terrain.Lieux; int largeur = terrain.Largeur, hauteur = terrain.Hauteur;
            void Voir(ushort a, ushort b) { if (a != 0 && b != 0 && a != b) paires.Add(a < b ? (a, b) : (b, a)); }
            for (int j = 0; j < hauteur; j++)
                for (int i = 0; i < largeur; i++)
                {
                    ushort ici = grille[j * largeur + i]; if (ici == 0) continue;
                    if (i + 1 < largeur) Voir(ici, grille[j * largeur + i + 1]);
                    if (j + 1 < hauteur) Voir(ici, grille[(j + 1) * largeur + i]);
                }
            (long, long) Lieu(int numero) { int l = numero - 1; return (lue.Cellules[terrain.CelluleDuLieu(l)].CellId, terrain.RangDuLieu(l)); }
            return paires.Select(p => { var (t, r) = Lieu(p.Item1); var (u, s) = Lieu(p.Item2); return (t, r, u, s); }).ToList();
        }

        // Colorie les pays servis. `avant` : les couleurs de la lecture d'avant, gardées tant qu'elles restent permises.
        public static CouleursDesPays Colorier(TerresDeLaCarte terres, Dictionary<string, HashSet<string>> voisins, CouleursDesPays avant = null)
        {
            if (terres == null) throw new ArgumentNullException(nameof(terres));
            var c = new CouleursDesPays(voisins ?? new Dictionary<string, HashSet<string>>());
            var ids = terres.Pays.Select(p => p.Id).OrderBy(i => i, StringComparer.Ordinal).ToList();
            // La racine de chaque pays : le haut de sa chaîne de suzerains, sans jamais boucler.
            var profondeurs = new Dictionary<string, int>();
            foreach (string id in ids)
            {
                string r = id; var vus = new HashSet<string> { id }; int profondeur = 0;
                for (string s = terres.SuzerainDe(r); s != null && vus.Add(s); s = terres.SuzerainDe(r)) { r = s; profondeur++; }
                c.racines[id] = r; profondeurs[id] = profondeur;
            }
            var blocs = ids.GroupBy(i => c.racines[i]).ToDictionary(g => g.Key, g => g.ToList());
            HashSet<string> VoisinsDe(string id) => c.voisins.TryGetValue(id, out var v) ? v : new HashSet<string>();
            c.Eclaircir(blocs, profondeurs, VoisinsDe, terres, avant);
            c.Teindre(blocs, VoisinsDe, avant);
            foreach (string id in ids)
            {
                c.couleurs[id] = Peindre(c.pigments[c.racines[id]], c.parts[id]);
                string ensemble = terres.EnsembleDe(id);
                c.liseres[id] = ensemble != null ? SocleInterface.LisereDeLEnsemble(ensemble) : CalquesCarte.LisereDuPigment(c.couleurs[id]);
            }
            return c;
        }

        // Dans chaque bloc, la part de chaque vassal : plus claire que celle de son suzerain, autre que celle de ses voisins du bloc.
        void Eclaircir(Dictionary<string, List<string>> blocs, Dictionary<string, int> profondeurs, Func<string, HashSet<string>> voisinsDe, TerresDeLaCarte terres, CouleursDesPays avant)
        {
            foreach (var bloc in blocs)
            {
                parts[bloc.Key] = 0;
                foreach (string id in bloc.Value.Where(i => i != bloc.Key).OrderBy(i => profondeurs[i]).ThenBy(i => i, StringComparer.Ordinal))
                {
                    int auMoins = parts[terres.SuzerainDe(id)] + 1;
                    var prises = new HashSet<int>(voisinsDe(id).Where(v => racines.TryGetValue(v, out string r) && r == bloc.Key && parts.ContainsKey(v)).Select(v => parts[v]));
                    int gardee = avant != null && avant.racines.TryGetValue(id, out string r0) && r0 == bloc.Key && avant.parts.TryGetValue(id, out int p0) ? p0 : -1;
                    int part = gardee >= auMoins && !prises.Contains(gardee) ? gardee : -1;
                    for (int k = auMoins; part < 0 && k <= PARTS.Count; k++) if (!prises.Contains(k)) part = k;
                    parts[id] = part > 0 ? part : Math.Min(auMoins, PARTS.Count);
                }
            }
        }

        // Le pigment de chaque bloc. D'abord ceux qui gardent le leur, dans l'ordre des racines ; puis les autres, le plus
        // contraint d'abord (le plus de pigments déjà pris autour de lui, puis le plus de voisins), chacun au premier pigment
        // permis à partir de celui qu'il avait, sinon du sien. Sans pigment permis, celui qui écarte le plus de ses voisins, puis
        // son entourage se replace autour de lui ; si un conflit reste, toute la carte se replace, et ce qui reste se compte.
        void Teindre(Dictionary<string, List<string>> blocs, Func<string, HashSet<string>> voisinsDe, CouleursDesPays avant)
        {
            int n = SocleInterface.PigmentsDesPays.Count;
            var voisinsDuBloc = blocs.ToDictionary(b => b.Key, b => new HashSet<string>(b.Value.SelectMany(voisinsDe).Where(racines.ContainsKey).Select(v => racines[v]).Where(r => r != b.Key)));
            // Le plus petit écart entre ce bloc, au pigment k, et ses voisins déjà teints ; infini s'il n'en a aucun.
            float EcartAuxVoisins(string bloc, int k)
            {
                float pire = float.PositiveInfinity;
                foreach (string r in voisinsDuBloc[bloc]) if (pigments.TryGetValue(r, out int autre) && autre == k) return -1f;
                foreach (string id in blocs[bloc])
                    foreach (string v in voisinsDe(id))
                        if (racines.TryGetValue(v, out string r) && r != bloc && pigments.TryGetValue(r, out int autre))
                            pire = Mathf.Min(pire, Ecart(Peindre(k, parts[id]), Peindre(autre, parts[v])));
                return pire;
            }
            if (avant != null)
                foreach (string bloc in blocs.Keys.OrderBy(b => b, StringComparer.Ordinal))
                    if (avant.pigments.TryGetValue(bloc, out int k) && EcartAuxVoisins(bloc, k) >= ECART_MIN) pigments[bloc] = k;
            // Place les blocs donnés, `premier` d'abord s'il est donné ; rend ceux qui n'ont trouvé aucun pigment permis.
            List<string> Placer(IEnumerable<string> aPlacer, string premier = null)
            {
                var restants = new HashSet<string>(aPlacer); var manques = new List<string>();
                while (restants.Count > 0)
                {
                    string bloc = premier != null && restants.Contains(premier) ? premier : restants.OrderByDescending(b => voisinsDuBloc[b].Where(pigments.ContainsKey).Select(r => pigments[r]).Distinct().Count())
                        .ThenByDescending(b => voisinsDuBloc[b].Count).ThenBy(b => b, StringComparer.Ordinal).First();
                    restants.Remove(bloc);
                    int prefere = avant != null && avant.pigments.TryGetValue(bloc, out int ancien) ? ancien : Prefere(bloc), choisi = -1, meilleur = prefere; float meilleurEcart = float.NegativeInfinity;
                    for (int d = 0; d < n && choisi < 0; d++)
                    {
                        int k = (prefere + d) % n; float e = EcartAuxVoisins(bloc, k);
                        if (e >= ECART_MIN) choisi = k; else if (e > meilleurEcart) { meilleurEcart = e; meilleur = k; }
                    }
                    if (choisi < 0) { choisi = meilleur; manques.Add(bloc); }
                    pigments[bloc] = choisi;
                }
                return manques;
            }
            // Un bloc sans pigment permis se replace le premier, ses voisins repris après lui : seul son entourage change.
            var conflits = Placer(blocs.Keys.Where(b => !pigments.ContainsKey(b)).ToList());
            foreach (string bloc in conflits.ToList())
            {
                var zone = new List<string> { bloc }; zone.AddRange(voisinsDuBloc[bloc]); foreach (string b in zone) pigments.Remove(b);
                var restes = Placer(zone, bloc); conflits.Remove(bloc); conflits.AddRange(restes.Where(b => !conflits.Contains(b)));
            }
            // Si un conflit reste, toute la carte se replace, chaque bloc essayant d'abord le pigment qu'il avait.
            if (conflits.Count > 0) { pigments.Clear(); conflits = Placer(blocs.Keys.ToList()); }
            Conflits = conflits.Count;
        }
    }
}
