using System;
using System.Collections.Generic;
using UnityEngine;

namespace Forge.Pont {
    // La place d'une lettre sur le tracé d'un nom : son milieu sur la ligne de base, et le sens de l'écriture en ce
    // point. Le haut des lettres est à gauche de ce sens.
    public readonly struct PlaceDeLettre {
        public Vector2 Point { get; } public Vector2 Sens { get; }
        public PlaceDeLettre(Vector2 point, Vector2 sens) { Point = point; Sens = sens; }
        public Vector2 Haut => new Vector2(-Sens.y, Sens.x);
    }

    // Un nom composé sur son tracé : le corps des lettres, ce qui s'ajoute entre deux lettres et ce que le nom couvre
    // du tracé, en km ; puis la place de chaque lettre, dans l'ordre de la lecture.
    public sealed class NomCompose {
        public float Corps { get; } public float Interlettre { get; } public float Etendue { get; }
        public IReadOnlyList<PlaceDeLettre> Lettres { get; }
        public NomCompose(float corps, float interlettre, float etendue, PlaceDeLettre[] lettres) { Corps = corps; Interlettre = interlettre; Etendue = etendue; Lettres = lettres; }
    }

    // La ligne où s'écrit le nom d'un pays, tirée de la seule forme de sa terre, en km locaux de la carte (x vers l'est,
    // z vers le nord) : un arc de parabole couché sur le grand axe du territoire, de `Debut` à `Fin` le long de cet axe.
    // De la géométrie de dessin : aucun nombre du monde n'en sort.
    public sealed class TraceDeNom {
        // Ce que le nom peut couvrir de la longueur du tracé et de la largeur du territoire ; un nom court s'étale,
        // lettre après lettre, jusqu'à `ETALEMENT` de la longueur, sans jamais écarter deux lettres de plus de
        // `INTERLETTRE_MAX` corps ; et le rayon de l'arc ne descend pas sous `RAYON_MIN` corps, où les lettres se
        // toucheraient du côté creux.
        public const float PART_DE_LA_LONGUEUR = 0.8f, PART_DE_LA_LARGEUR = 0.46f, ETALEMENT = 0.55f, INTERLETTRE_MAX = 0.8f, RAYON_MIN = 1.25f;
        private const int PAS_DE_L_ARC = 48;
        private readonly float a, b, c; private readonly float[] arcs;

        // Le centre du territoire, son grand axe (tourné vers l'est : le nom se lit d'ouest en est) et, en travers,
        // l'axe qui porte le haut des lettres.
        public Vector2 Centre { get; } public Vector2 Axe { get; }
        public Vector2 Travers => new Vector2(-Axe.y, Axe.x);
        public float Debut { get; } public float Fin { get; }
        // La largeur du territoire de part et d'autre du tracé, et la longueur de l'arc, en km.
        public float Largeur { get; } public float Longueur { get; }
        // De combien l'arc se creuse : l'écart en travers vaut `Courbure` fois le carré de l'abscisse, en km.
        public float Courbure => c;
        // Combien de points du territoire ont servi à le tracer.
        public int Echantillons { get; }

        public TraceDeNom(Vector2 centre, Vector2 axe, float debut, float fin, float a, float b, float c, float largeur, int echantillons) {
            Centre = centre; Axe = axe; Debut = debut; Fin = Mathf.Max(fin, debut); this.a = a; this.b = b; this.c = c; Largeur = largeur; Echantillons = echantillons;
            arcs = new float[PAS_DE_L_ARC + 1]; Vector2 avant = Point(Debut);
            for (int k = 1; k <= PAS_DE_L_ARC; k++) { Vector2 p = Point(Debut + (Fin - Debut) * k / PAS_DE_L_ARC); arcs[k] = arcs[k - 1] + (p - avant).magnitude; avant = p; }
            Longueur = arcs[PAS_DE_L_ARC];
        }

        // Le même arc, descendu de `ecart` km sous le pied des lettres (à l'opposé de `Travers`), sur une largeur donnée :
        // la ligne d'un second nom, plus petit, écrit sous le premier.
        public TraceDeNom Dessous(float ecart, float largeur) => new TraceDeNom(Centre, Axe, Debut, Fin, a - ecart, b, c, largeur, Echantillons);

        // Le point du tracé à cette abscisse le long du grand axe, et le sens de l'écriture en ce point.
        public Vector2 Point(float s) => Centre + Axe * s + Travers * (a + b * s + c * s * s);
        public Vector2 Sens(float s) => (Axe + Travers * (b + 2 * c * s)).normalized;
        // L'abscisse du point qui est à cette longueur d'arc du début.
        public float Abscisse(float arc) {
            if (Longueur <= 0f) return Debut;
            arc = Mathf.Clamp(arc, 0f, Longueur); int k = 1;
            while (k < PAS_DE_L_ARC && arcs[k] < arc) k++;
            float t = arcs[k] > arcs[k - 1] ? (arc - arcs[k - 1]) / (arcs[k] - arcs[k - 1]) : 0f;
            return Debut + (Fin - Debut) * (k - 1 + t) / PAS_DE_L_ARC;
        }

        // Compose un nom sur le tracé, d'après ce que chaque lettre avance, en corps. Le corps est le plus grand que
        // permettent la longueur du tracé, la largeur du territoire et le creux de l'arc ; le nom est centré sur le
        // tracé. Null quand il n'y a rien à écrire ou nulle part où l'écrire.
        public NomCompose Composer(IReadOnlyList<float> avances) {
            if (avances == null || avances.Count == 0 || Longueur <= 0f || Largeur <= 0f) return null;
            float naturel = 0f; foreach (float avance in avances) naturel += avance;
            if (naturel <= 0f) return null;
            float corps = Mathf.Min(PART_DE_LA_LARGEUR * Largeur, PART_DE_LA_LONGUEUR * Longueur / naturel);
            if (Mathf.Abs(c) > 0f) corps = Mathf.Min(corps, 1f / (2f * RAYON_MIN * Mathf.Abs(c)));
            int ecarts = avances.Count - 1; float large = corps * naturel, inter = 0f;
            if (ecarts > 0 && large < ETALEMENT * Longueur) inter = Mathf.Min((ETALEMENT * Longueur - large) / ecarts, INTERLETTRE_MAX * corps);
            float etendue = large + inter * ecarts, arc = (Longueur - etendue) / 2f;
            var lettres = new PlaceDeLettre[avances.Count];
            for (int i = 0; i < lettres.Length; i++) {
                float s = Abscisse(arc + avances[i] * corps / 2f); lettres[i] = new PlaceDeLettre(Point(s), Sens(s));
                arc += avances[i] * corps + inter;
            }
            return new NomCompose(corps, inter, etendue, lettres);
        }
    }

    // Le tracé du nom de chaque pays, tiré de la grille des lieux du terrain, chaque lieu au pays de sa cellule. Le
    // territoire d'un pays se lit par échantillons, un texel sur quelques-uns ; d'un pays en plusieurs morceaux, seul le plus grand d'un seul tenant
    // porte le nom : un nom ne s'étire pas par-dessus une mer ou un voisin. Sur ce morceau, le grand axe est celui où
    // les points s'étalent le plus, et l'arc est la parabole qui passe au plus près d'eux. Un territoire à peu près
    // rond n'a pas de grand axe : son nom s'écrit d'ouest en est. Là où l'arc sort de la terre du pays (une baie, un
    // voisin enclavé, un territoire trop tordu pour une parabole), le tracé n'en garde que la plus longue portion qui
    // tient sur elle. Ne dépend que du terrain et des pays donnés : deux tracés des mêmes pays sont égaux.
    public static class TraceDesNoms {
        // Assez d'échantillons pour toute la carte ; un pays qui en reçoit moins que `PETIT_PAYS` est relu texel par texel.
        public const int ECHANTILLONS_VISES = 150000, PETIT_PAYS = 400, ECHANTILLONS_D_UN_PETIT_PAYS = 400000;
        // En deçà de ce rapport entre son étalement en long et en travers, un territoire n'a pas de grand axe.
        public const float ALLONGEMENT_MIN = 1.25f;
        // L'arc ne penche jamais, à ses bouts, de plus de cette pente par rapport au grand axe.
        public const float PENTE_MAX = 1.1f;
        // Les bouts du tracé laissent hors du nom cette part des points, de chaque côté.
        private const float QUEUE = 0.03f;
        // Le tracé est sondé en autant de points ; un trou d'au plus `TROU` sondes hors de la terre (un lac, un bras de
        // mer) ne le coupe pas.
        public const int SONDES = 48, TROU = 2;

        // `pays` dit le pays de chaque rang servi ; un pays négatif n'a pas de nom. Rend le tracé de chaque pays qui
        // tient au moins un texel du terrain.
        public static Dictionary<int, TraceDeNom> Tracer(TerrainDeCarte terrain, IReadOnlyList<int> pays) {
            if (terrain == null) throw new ArgumentNullException(nameof(terrain));
            if (pays == null) throw new ArgumentNullException(nameof(pays));
            int rangs = pays.Count; long terre = 0; var parNumero = new int[terrain.NombreDeLieux + 1]; parNumero[0] = -1;
            // Chaque lieu porte le nom du pays de sa cellule.
            for (int l = 0; l < terrain.NombreDeLieux; l++) parNumero[l + 1] = pays[terrain.CelluleDuLieu(l)];
            var zones = new Dictionary<int, RectInt>();
            for (int r = 0; r < rangs; r++) {
                int texels = terrain.TexelsDe(r);
                if (pays[r] < 0 || texels == 0) continue;
                terre += texels; RectInt zone = terrain.ZoneDe(r);
                zones[pays[r]] = zones.TryGetValue(pays[r], out RectInt deja) ? Union(deja, zone) : zone;
            }
            var traces = new Dictionary<int, TraceDeNom>();
            if (terre == 0) return traces;
            int saut = Math.Max(1, (int)Math.Ceiling(Math.Sqrt(terre / (double)ECHANTILLONS_VISES)));
            Dictionary<int, List<int>> morceaux = Morceaux(terrain, parNumero, terrain.Tout, saut, -1, out int largeur);
            var cles = new List<int>(zones.Keys); cles.Sort();
            foreach (int cle in cles) {
                morceaux.TryGetValue(cle, out List<int> points); int sautDuPays = saut, largeurDuPays = largeur; RectInt zone = terrain.Tout;
                if (saut > 1 && (points == null || points.Count < PETIT_PAYS)) {
                    zone = zones[cle]; sautDuPays = Math.Max(1, (int)Math.Ceiling(Math.Sqrt(zone.width * (double)zone.height / ECHANTILLONS_D_UN_PETIT_PAYS)));
                    Morceaux(terrain, parNumero, zone, sautDuPays, cle, out largeurDuPays).TryGetValue(cle, out points);
                }
                if (points == null || points.Count == 0) continue;
                var km = new Vector2[points.Count]; Vector2 coin = terrain.Coin;
                for (int k = 0; k < km.Length; k++) {
                    int i = zone.xMin + Texel(points[k] % largeurDuPays, sautDuPays, zone.width), j = zone.yMin + Texel(points[k] / largeurDuPays, sautDuPays, zone.height);
                    km[k] = new Vector2(coin.x + (i + 0.5f) * terrain.Pas, coin.y + (j + 0.5f) * terrain.Pas);
                }
                int lePays = cle;
                traces[cle] = Ajuster(km, sautDuPays * terrain.Pas, p => { ushort n = terrain.LieuEn(p.x, p.y); return n != 0 && parNumero[n] == lePays; });
            }
            return traces;
        }

        private static RectInt Union(RectInt u, RectInt v) {
            int x0 = Math.Min(u.xMin, v.xMin), y0 = Math.Min(u.yMin, v.yMin);
            return new RectInt(x0, y0, Math.Max(u.xMax, v.xMax) - x0, Math.Max(u.yMax, v.yMax) - y0);
        }
        // Le texel lu pour l'échantillon de ce rang : le milieu de son pavé, sans sortir de la zone.
        private static int Texel(int rang, int saut, int cote) => Math.Min(rang * saut + saut / 2, cote - 1);

        // Les échantillons du plus grand morceau d'un seul tenant de chaque pays (ou du seul pays demandé), dans la
        // zone, un texel tous les `saut` ; deux échantillons voisins, même par un coin, sont du même morceau. Chaque
        // échantillon est rendu par son rang dans la zone, `largeur` par ligne. À taille égale, le premier morceau
        // rencontré du sud-ouest au nord-est est gardé.
        private static Dictionary<int, List<int>> Morceaux(TerrainDeCarte terrain, int[] parNumero, RectInt zone, int saut, int seul, out int largeur) {
            ushort[] lieux = terrain.TexelsDesLieux; int l = (zone.width + saut - 1) / saut, h = (zone.height + saut - 1) / saut; largeur = l;
            var grille = new int[l * h];
            for (int j = 0; j < h; j++) {
                int ligne = (zone.yMin + Texel(j, saut, zone.height)) * terrain.Largeur + zone.xMin;
                for (int i = 0; i < l; i++) { int p = parNumero[lieux[ligne + Texel(i, saut, zone.width)]]; grille[j * l + i] = p >= 0 && (seul < 0 || p == seul) ? p : -1; }
            }
            var grands = new Dictionary<int, List<int>>(); var pile = new Stack<int>(); var morceau = new List<int>();
            for (int depart = 0; depart < grille.Length; depart++) {
                int p = grille[depart]; if (p < 0) continue;
                morceau.Clear(); pile.Push(depart); grille[depart] = -1;
                while (pile.Count > 0) {
                    int k = pile.Pop(), i = k % l, j = k / l; morceau.Add(k);
                    for (int dj = -1; dj <= 1; dj++)
                        for (int di = -1; di <= 1; di++) {
                            int vi = i + di, vj = j + dj; if (vi < 0 || vj < 0 || vi >= l || vj >= h) continue;
                            int v = vj * l + vi; if (grille[v] != p) continue;
                            grille[v] = -1; pile.Push(v);
                        }
                }
                if (!grands.TryGetValue(p, out List<int> garde) || morceau.Count > garde.Count) grands[p] = new List<int>(morceau);
            }
            return grands;
        }

        // Le tracé qui passe au plus près des points d'un territoire, espacés de `pas` km ; `dedans` dit si un point
        // est sur la terre du pays.
        private static TraceDeNom Ajuster(Vector2[] points, float pas, Func<Vector2, bool> dedans) {
            int n = points.Length; double mx = 0, mz = 0;
            foreach (Vector2 p in points) { mx += p.x; mz += p.y; }
            mx /= n; mz /= n; double xx = 0, zz = 0, xz = 0;
            foreach (Vector2 p in points) { double dx = p.x - mx, dz = p.y - mz; xx += dx * dx; zz += dz * dz; xz += dx * dz; }
            // Le grand axe : la direction où les points s'étalent le plus.
            double angle = 0.5 * Math.Atan2(2 * xz, xx - zz), demi = (xx + zz) / 2, ecart = Math.Sqrt((xx - zz) * (xx - zz) / 4 + xz * xz);
            double long2 = demi + ecart, travers2 = Math.Max(demi - ecart, 0);
            var axe = new Vector2((float)Math.Cos(angle), (float)Math.Sin(angle));
            if (long2 < ALLONGEMENT_MIN * ALLONGEMENT_MIN * travers2 || long2 <= 0) axe = Vector2.right;
            else if (axe.x < 0f || (axe.x == 0f && axe.y < 0f)) axe = -axe;
            var centre = new Vector2((float)mx, (float)mz); var enTravers = new Vector2(-axe.y, axe.x);
            var s = new float[n]; var t = new float[n];
            for (int k = 0; k < n; k++) { Vector2 d = points[k] - centre; s[k] = Vector2.Dot(d, axe); t[k] = Vector2.Dot(d, enTravers); }
            var tries = (float[])s.Clone(); Array.Sort(tries);
            float debut = tries[(int)(QUEUE * (n - 1))], fin = tries[(int)Math.Ceiling((1 - QUEUE) * (n - 1))];
            if (fin - debut < pas) { float milieu = (debut + fin) / 2f; debut = milieu - pas / 2f; fin = milieu + pas / 2f; }
            float longueur = fin - debut;

            // La parabole au plus près des points ; puis, si elle penche trop à ses bouts, la plus creuse permise et
            // la droite qui la porte au plus près des points.
            double echelle = Math.Max(Math.Abs(tries[0]), Math.Abs(tries[n - 1])); if (echelle <= 0) echelle = 1;
            double s1 = 0, s2 = 0, s3 = 0, s4 = 0, t0 = 0, t1 = 0, t2 = 0;
            for (int k = 0; k < n; k++) { double u = s[k] / echelle, u2 = u * u; s1 += u; s2 += u2; s3 += u2 * u; s4 += u2 * u2; t0 += t[k]; t1 += t[k] * u; t2 += t[k] * u2; }
            double a = t0 / n, b = 0, c = 0;
            double det = n * (s2 * s4 - s3 * s3) - s1 * (s1 * s4 - s3 * s2) + s2 * (s1 * s3 - s2 * s2);
            if (n >= 8 && Math.Abs(det) > 1e-9 * n * s2 * s4) {
                a = (t0 * (s2 * s4 - s3 * s3) - s1 * (t1 * s4 - s3 * t2) + s2 * (t1 * s3 - s2 * t2)) / det;
                b = (n * (t1 * s4 - t2 * s3) - t0 * (s1 * s4 - s3 * s2) + s2 * (s1 * t2 - s2 * t1)) / det / echelle;
                c = (n * (s2 * t2 - s3 * t1) - s1 * (s1 * t2 - s2 * t1) + t0 * (s1 * s3 - s2 * s2)) / det / (echelle * echelle);
                double cMax = PENTE_MAX / longueur;
                if (Math.Abs(c) > cMax) {
                    c = Math.Sign(c) * cMax; double r0 = 0, r1 = 0, q1 = 0, q2 = 0;
                    for (int k = 0; k < n; k++) { double reste = t[k] - c * s[k] * s[k]; r0 += reste; r1 += reste * s[k]; q1 += s[k]; q2 += s[k] * (double)s[k]; }
                    double d2 = n * q2 - q1 * q1;
                    if (Math.Abs(d2) > 1e-9) { b = (n * r1 - q1 * r0) / d2; a = (r0 - b * q1) / n; } else { b = 0; a = r0 / n; }
                }
            }
            float A = (float)a, B = (float)b, C = (float)c;
            Vector2 Sur(float abscisse) => centre + axe * abscisse + enTravers * (A + B * abscisse + C * abscisse * abscisse);
            // La plus longue portion du tracé qui tient sur la terre du pays ; sans une seule sonde sur elle, tout le tracé.
            int meilleurDebut = -1, meilleurFin = -1;
            for (int k = 0; k <= SONDES;) {
                if (!dedans(Sur(debut + longueur * k / SONDES))) { k++; continue; }
                int dernier = k, trou = 0;
                for (int j = k + 1; j <= SONDES && trou <= TROU; j++) { if (dedans(Sur(debut + longueur * j / SONDES))) { dernier = j; trou = 0; } else trou++; }
                if (dernier - k > meilleurFin - meilleurDebut) { meilleurDebut = k; meilleurFin = dernier; }
                k = dernier + 1;
            }
            if (meilleurFin > meilleurDebut) { fin = debut + longueur * meilleurFin / SONDES; debut += longueur * meilleurDebut / SONDES; }

            // La largeur du territoire autour du tracé : quatre fois l'écart médian de ses points à l'arc, ce que vaut
            // la largeur d'une bande ; jamais moins que l'espacement des points.
            var ecarts = new List<float>(n);
            for (int k = 0; k < n; k++) if (s[k] >= debut && s[k] <= fin) ecarts.Add(Mathf.Abs(t[k] - (A + B * s[k] + C * s[k] * s[k])));
            float largeur = pas;
            if (ecarts.Count > 0) { ecarts.Sort(); largeur = Mathf.Max(pas, 4f * ecarts[ecarts.Count / 2]); }
            return new TraceDeNom(centre, axe, debut, fin, A, B, C, largeur, n);
        }
    }
}
