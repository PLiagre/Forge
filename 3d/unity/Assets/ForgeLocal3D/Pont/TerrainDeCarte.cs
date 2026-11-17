using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using UnityEngine;

namespace Forge.Pont {
    // Le terrain de la carte, levé d'un seul tenant depuis la carte servie. Rien ici ne touche un objet d'Unity : le
    // levé part hors du fil principal. Trois grilles couvrent le même rectangle, la boîte des cellules bordée de mer :
    // - les cellules : un texel tous les `Pas` km, 0 pour la mer, sinon le rang servi + 1. Un texel est à la cellule
    //   dont un polygone contient son centre (règle pair-impair, trous compris). Une cellule plus petite qu'un texel
    //   en reçoit un quand même, pris à la mer ou à une voisine qui en garde : aucune cellule servie ne disparaît ;
    // - le relief : une altitude tous les `PasDuRelief` km, positive à terre, nulle au rivage, négative en mer ;
    // - le maillage : un sommet tous les `PasDuMaillage` km, à son altitude, la plus haute cime possible au plan 0.
    //   Tout le terrain reste donc sous les calques posés à plat au-dessus de ce plan.
    // Le relief est un décor : il ne vient d'aucune mesure et ne décide aucune grandeur du monde. Il habille la classe
    // de relief servie de chaque cellule, plus haute et plus heurtée de la plaine à la haute montagne, et s'efface vers
    // la côte. Il ne dépend que de la carte : deux levés de la même carte sont égaux.
    public sealed class TerrainDeCarte {
        public const float MARGE_DE_MER_KM = 160f, PAS_MINIMAL_KM = 1f;
        public const int COTE_MAXIMAL = 4096, TEXELS_PAR_RELIEF = 2, TEXELS_PAR_MAILLE = 8;
        // En km de décor : la plus haute cime possible, le fond de la mer au large, et la terre au ras de l'eau.
        public const float PLAFOND = 40f, FOND = 6f, RIVAGE = 0.15f;
        // La côte monte sur COTE_KM ; le fond descend sur LARGE_KM, vite près du rivage puis de moins en moins, et se
        // lisse sur FLOU_DE_MER_KM. Les deux ensemble tiennent dans la marge : le bord du terrain est au fond.
        private const double COTE_KM = 30, LARGE_KM = 130, FLOU_KM = 12, FLOU_DE_MER_KM = 7;
        // Le socle et le heurt de chaque classe servie, en km de décor ; le socle dépasse toujours le heurt.
        private static readonly Dictionary<string, (float socle, float heurt)> CLASSES = new Dictionary<string, (float, float)> {
            { "marais", (0.3f, 0.1f) }, { "plaine", (1.2f, 0.6f) }, { "colline", (5f, 2.5f) },
            { "montagne", (14f, 7f) }, { "haute_montagne", (26f, 12f) }
        };
        private const string SANS_CLASSE = "plaine"; // un relief non servi, ou d'une classe inconnue, se dessine en plaine

        private readonly ushort[] cellules; private readonly int[] texels; private readonly float[] altitudes;
        private readonly Vector3[] sommets; private readonly Vector2[] uv; private readonly int[] triangles;
        private readonly double minX, minZ, pas;

        public PointCarte Origine { get; }
        // La boîte des cellules, en km locaux, sans la marge de mer.
        public Bounds Boite { get; }
        public int Largeur { get; }
        public int Hauteur { get; }
        public float Pas { get; }
        public float PasDuRelief => Pas * TEXELS_PAR_RELIEF;
        public float PasDuMaillage => Pas * TEXELS_PAR_MAILLE;
        public int LargeurDuRelief => Largeur / TEXELS_PAR_RELIEF;
        public int HauteurDuRelief => Hauteur / TEXELS_PAR_RELIEF;
        // Le coin sud-ouest du rectangle, en km locaux : le texel (0, 0) part de là, vers l'est puis vers le nord.
        public Vector2 Coin => new Vector2((float)minX, (float)minZ);
        public IReadOnlyList<ushort> Cellules => cellules;
        public IReadOnlyList<float> Altitudes => altitudes;
        public IReadOnlyList<Vector3> Sommets => sommets;
        public IReadOnlyList<Vector2> Uv => uv;
        public IReadOnlyList<int> Triangles => triangles;
        // Combien de texels porte la cellule de ce rang servi.
        public int TexelsDe(int rang) => texels[rang];
        internal ushort[] TexelsDesCellules => cellules;
        internal float[] TexelsDuRelief => altitudes;
        internal Vector3[] SommetsDuMaillage => sommets;
        internal Vector2[] UvDuMaillage => uv;
        internal int[] TrianglesDuMaillage => triangles;

        private TerrainDeCarte(PointCarte origine, Bounds boite, int largeur, int hauteur, double pas, double minX, double minZ, ushort[] cellules, int[] texels, float[] altitudes) {
            Origine = origine; Boite = boite; Largeur = largeur; Hauteur = hauteur; Pas = (float)pas; this.pas = pas; this.minX = minX; this.minZ = minZ;
            this.cellules = cellules; this.texels = texels; this.altitudes = altitudes;
            int nx = largeur / TEXELS_PAR_MAILLE + 1, nz = hauteur / TEXELS_PAR_MAILLE + 1; double maille = pas * TEXELS_PAR_MAILLE;
            sommets = new Vector3[nx * nz]; uv = new Vector2[nx * nz]; triangles = new int[(nx - 1) * (nz - 1) * 6];
            for (int j = 0; j < nz; j++)
                for (int i = 0; i < nx; i++) {
                    float x = (float)(minX + i * maille), z = (float)(minZ + j * maille);
                    sommets[j * nx + i] = new Vector3(x, Altitude(x, z) - PLAFOND, z);
                    uv[j * nx + i] = new Vector2(i * TEXELS_PAR_MAILLE / (float)largeur, j * TEXELS_PAR_MAILLE / (float)hauteur);
                }
            int t = 0; // deux triangles par maille, tournés vers le haut
            for (int j = 0; j + 1 < nz; j++)
                for (int i = 0; i + 1 < nx; i++) {
                    int a = j * nx + i, b = a + 1, c = a + nx, d = c + 1;
                    triangles[t++] = a; triangles[t++] = c; triangles[t++] = b; triangles[t++] = b; triangles[t++] = c; triangles[t++] = d;
                }
        }

        // La cellule du texel sous un point en km locaux : 0 pour la mer ou hors du rectangle, sinon le rang servi + 1.
        public ushort CelluleEn(float x, float z) {
            int i = (int)Math.Floor((x - minX) / pas), j = (int)Math.Floor((z - minZ) / pas);
            return i < 0 || j < 0 || i >= Largeur || j >= Hauteur ? (ushort)0 : cellules[j * Largeur + i];
        }

        // L'altitude du relief sous un point en km locaux, lue entre les quatre altitudes voisines ; hors du rectangle, celle du bord.
        public float Altitude(float x, float z) {
            int l = LargeurDuRelief, h = HauteurDuRelief; double relief = pas * TEXELS_PAR_RELIEF;
            double u = Math.Min(Math.Max((x - minX) / relief - 0.5, 0), l - 1), v = Math.Min(Math.Max((z - minZ) / relief - 0.5, 0), h - 1);
            int i = Math.Min((int)u, l - 2), j = Math.Min((int)v, h - 2); double fu = u - i, fv = v - j;
            double bas = altitudes[j * l + i] + fu * (altitudes[j * l + i + 1] - altitudes[j * l + i]);
            double haut = altitudes[(j + 1) * l + i] + fu * (altitudes[(j + 1) * l + i + 1] - altitudes[(j + 1) * l + i]);
            return (float)(bas + fv * (haut - bas));
        }

        public static TerrainDeCarte Lever(CarteLue carte) {
            if (carte == null) throw new ArgumentNullException(nameof(carte));
            int n = carte.Cellules.Count;
            if (n == 0) throw new ArgumentException("une carte vide n'a aucun terrain");
            if (n >= ushort.MaxValue) throw new ArgumentException(n + " cellules : trop pour un terrain");
            PointCarte origine = MaillageDeCarte.Centre(carte);
            // Les anneaux en km locaux, x puis z, par cellule puis par polygone ; la boîte de tous leurs points.
            var polygones = new List<List<double[]>>[n];
            double x0 = double.PositiveInfinity, z0 = double.PositiveInfinity, x1 = double.NegativeInfinity, z1 = double.NegativeInfinity;
            for (int r = 0; r < n; r++) {
                CelluleDeCarte cellule = carte.Cellules[r]; polygones[r] = new List<List<double[]>>(); int points = 0;
                foreach (PolygoneDeCarte polygone in cellule.Contour) {
                    var anneaux = new List<double[]>();
                    for (int a = -1; a < polygone.Trous.Count; a++) {
                        IReadOnlyList<PointCarte> anneau = a < 0 ? polygone.Exterieur : polygone.Trous[a];
                        var local = new double[anneau.Count * 2];
                        for (int k = 0; k < anneau.Count; k++) {
                            double x = (anneau[k].X - origine.X) / 1000.0, z = (anneau[k].Y - origine.Y) / 1000.0; local[2 * k] = x; local[2 * k + 1] = z;
                            if (x < x0) x0 = x; if (x > x1) x1 = x; if (z < z0) z0 = z; if (z > z1) z1 = z;
                        }
                        anneaux.Add(local); points += anneau.Count;
                    }
                    polygones[r].Add(anneaux);
                }
                if (points == 0) throw new ArgumentException("cellule " + cellule.CellId + " : aucun contour");
            }
            var boite = new Bounds(); boite.SetMinMax(new Vector3((float)x0, 0f, (float)z0), new Vector3((float)x1, 0f, (float)z1));
            double minX = x0 - MARGE_DE_MER_KM, minZ = z0 - MARGE_DE_MER_KM, large = x1 - x0 + 2 * MARGE_DE_MER_KM, haut = z1 - z0 + 2 * MARGE_DE_MER_KM;
            double pas = Math.Max(PAS_MINIMAL_KM, Math.Max(large, haut) / COTE_MAXIMAL);
            int largeur = ParMailles(large / pas), hauteur = ParMailles(haut / pas);

            var cellules = new ushort[largeur * hauteur]; var texels = new int[n];
            for (int r = 0; r < n; r++)
                foreach (List<double[]> polygone in polygones[r]) Remplir(cellules, texels, largeur, hauteur, minX, minZ, pas, polygone, (ushort)(r + 1));
            for (int r = 0; r < n; r++)
                if (texels[r] == 0) Garantir(cellules, texels, largeur, hauteur, minX, minZ, pas, polygones[r][0][0], (ushort)(r + 1));

            var socles = new float[n]; var heurts = new float[n];
            for (int r = 0; r < n; r++) {
                string classe = carte.Cellules[r].Relief;
                (socles[r], heurts[r]) = classe != null && CLASSES.TryGetValue(classe, out var valeurs) ? valeurs : CLASSES[SANS_CLASSE];
            }
            float[] altitudes = Relief(cellules, largeur, hauteur, minX, minZ, pas, socles, heurts);
            return new TerrainDeCarte(origine, boite, largeur, hauteur, pas, minX, minZ, cellules, texels, altitudes);
        }

        // Le nombre de texels d'un côté : assez pour le couvrir, en mailles entières.
        private static int ParMailles(double texels) => Math.Max(2, (int)Math.Ceiling(texels / TEXELS_PAR_MAILLE)) * TEXELS_PAR_MAILLE;

        private static void Prendre(ushort[] cellules, int[] texels, int index, ushort valeur) {
            ushort avant = cellules[index]; if (avant == valeur) return;
            if (avant != 0) texels[avant - 1]--;
            cellules[index] = valeur; texels[valeur - 1]++;
        }

        // Ligne de texels par ligne : les centres pris entre deux croisements du bord, l'ouest compris, l'est exclu, pour
        // que deux cellules voisines ne prennent jamais le même texel.
        private static void Remplir(ushort[] cellules, int[] texels, int largeur, int hauteur, double minX, double minZ, double pas, List<double[]> polygone, ushort valeur) {
            double bas = double.PositiveInfinity, haut = double.NegativeInfinity;
            foreach (double[] anneau in polygone) for (int k = 1; k < anneau.Length; k += 2) { if (anneau[k] < bas) bas = anneau[k]; if (anneau[k] > haut) haut = anneau[k]; }
            int j0 = Math.Max(0, (int)Math.Ceiling((bas - minZ) / pas - 0.5)), j1 = Math.Min(hauteur - 1, (int)Math.Floor((haut - minZ) / pas - 0.5));
            var croisements = new List<double>();
            for (int j = j0; j <= j1; j++) {
                double z = minZ + (j + 0.5) * pas; croisements.Clear();
                foreach (double[] a in polygone)
                    for (int k = 0; k + 3 < a.Length; k += 2)
                        if ((a[k + 1] > z) != (a[k + 3] > z)) croisements.Add(a[k] + (z - a[k + 1]) / (a[k + 3] - a[k + 1]) * (a[k + 2] - a[k]));
                croisements.Sort();
                for (int c = 0; c + 1 < croisements.Count; c += 2) {
                    int i0 = Math.Max(0, (int)Math.Ceiling((croisements[c] - minX) / pas - 0.5)), i1 = Math.Min(largeur, (int)Math.Ceiling((croisements[c + 1] - minX) / pas - 0.5));
                    for (int i = i0; i < i1; i++) Prendre(cellules, texels, j * largeur + i, valeur);
                }
            }
        }

        // Une cellule qu'aucun centre de texel ne touche prend le texel de son premier anneau, ou le plus proche qui soit
        // à la mer ou à une cellule qui en garde un autre. Faute d'un tel texel, elle reste sans texel, et cela se compte.
        private static void Garantir(ushort[] cellules, int[] texels, int largeur, int hauteur, double minX, double minZ, double pas, double[] anneau, ushort valeur) {
            double x = 0, z = 0; int points = anneau.Length / 2;
            for (int k = 0; k < points; k++) { x += anneau[2 * k]; z += anneau[2 * k + 1]; }
            int ci = Math.Min(Math.Max((int)Math.Floor((x / points - minX) / pas), 0), largeur - 1), cj = Math.Min(Math.Max((int)Math.Floor((z / points - minZ) / pas), 0), hauteur - 1);
            for (int rayon = 0; rayon <= 2; rayon++)
                for (int dj = -rayon; dj <= rayon; dj++)
                    for (int di = -rayon; di <= rayon; di++) {
                        if (Math.Max(Math.Abs(di), Math.Abs(dj)) != rayon) continue;
                        int i = ci + di, j = cj + dj; if (i < 0 || j < 0 || i >= largeur || j >= hauteur) continue;
                        ushort avant = cellules[j * largeur + i];
                        if (avant != 0 && texels[avant - 1] < 2) continue;
                        Prendre(cellules, texels, j * largeur + i, valeur); return;
                    }
        }

        private static float[] Relief(ushort[] cellules, int largeur, int hauteur, double minX, double minZ, double pasDesCellules, float[] socles, float[] heurts) {
            int l = largeur / TEXELS_PAR_RELIEF, h = hauteur / TEXELS_PAR_RELIEF; double pas = pasDesCellules * TEXELS_PAR_RELIEF;
            // Chaque altitude résume ses texels de cellules : terre si la moitié l'est, socle et heurt moyens (la mer compte pour rien).
            var socle = new float[l * h]; var heurt = new float[l * h]; var terre = new bool[l * h]; var mer = new bool[l * h];
            float part = 1f / (TEXELS_PAR_RELIEF * TEXELS_PAR_RELIEF);
            Parallel.For(0, h, j => {
                for (int i = 0; i < l; i++) {
                    int aTerre = 0; float s = 0, e = 0;
                    for (int dj = 0; dj < TEXELS_PAR_RELIEF; dj++)
                        for (int di = 0; di < TEXELS_PAR_RELIEF; di++) {
                            ushort c = cellules[(j * TEXELS_PAR_RELIEF + dj) * largeur + i * TEXELS_PAR_RELIEF + di];
                            if (c == 0) continue;
                            aTerre++; s += socles[c - 1]; e += heurts[c - 1];
                        }
                    int k = j * l + i; socle[k] = s * part; heurt[k] = e * part; terre[k] = aTerre * 2 >= TEXELS_PAR_RELIEF * TEXELS_PAR_RELIEF; mer[k] = !terre[k];
                }
            });
            // Les classes se fondent d'une cellule à l'autre au lieu de dessiner des marches le long des bords.
            int rayon = Math.Max(1, (int)Math.Round(FLOU_KM / pas));
            Flouter(socle, l, h, rayon); Flouter(heurt, l, h, rayon);
            float[] versLaMer = Distances(mer, l, h, (float)pas), versLaTerre = Distances(terre, l, h, (float)pas);
            // Le fond, nul à terre, lissé pour que les lignes où deux rivages sont aussi loin ne se voient pas.
            var fond = new float[l * h];
            Parallel.For(0, h, j => { for (int i = 0; i < l; i++) { int k = j * l + i; if (!terre[k]) fond[k] = (float)(FOND * Plonge(versLaTerre[k] / LARGE_KM)); } });
            Flouter(fond, l, h, Math.Max(1, (int)Math.Round(FLOU_DE_MER_KM / pas)));
            var altitudes = new float[l * h];
            Parallel.For(0, h, j => {
                for (int i = 0; i < l; i++) {
                    int k = j * l + i;
                    if (!terre[k]) { altitudes[k] = -fond[k]; continue; }
                    double brut = socle[k] + heurt[k] * (2 * Bruit(minX + (i + 0.5) * pas, minZ + (j + 0.5) * pas) - 1);
                    altitudes[k] = (float)Math.Min(Math.Max(RIVAGE + Lisse(versLaMer[k] / COTE_KM) * brut, RIVAGE), PLAFOND);
                }
            });
            return altitudes;
        }

        // De 0 à 1 sans cassure, 0 avant et 1 après.
        private static double Lisse(double t) { t = Math.Min(Math.Max(t, 0), 1); return t * t * (3 - 2 * t); }
        // De 0 à 1, d'abord vite puis de plus en plus doucement, 1 après.
        private static double Plonge(double t) { t = 1 - Math.Min(Math.Max(t, 0), 1); return 1 - t * t * t; }

        // Deux passes de moyenne glissante par axe ; au bord, la moyenne ne compte que ce qui existe.
        private static void Flouter(float[] valeurs, int l, int h, int rayon) {
            var tampon = new float[valeurs.Length];
            for (int passe = 0; passe < 2; passe++) {
                Parallel.For(0, h, j => { Glisser(valeurs, tampon, j * l, 1, l, rayon); });
                Parallel.For(0, l, i => { Glisser(tampon, valeurs, i, l, h, rayon); });
            }
        }
        private static void Glisser(float[] source, float[] cible, int debut, int saut, int nombre, int rayon) {
            double somme = 0; int compte = 0;
            for (int k = 0; k < Math.Min(rayon, nombre); k++) { somme += source[debut + k * saut]; compte++; }
            for (int k = 0; k < nombre; k++) {
                if (k + rayon < nombre) { somme += source[debut + (k + rayon) * saut]; compte++; }
                if (k - rayon - 1 >= 0) { somme -= source[debut + (k - rayon - 1) * saut]; compte--; }
                cible[debut + k * saut] = (float)(somme / compte);
            }
        }

        // La distance en km de chaque texel au plus proche texel marqué, par deux balayages (droit 1, diagonale √2).
        private static float[] Distances(bool[] marques, int l, int h, float pas) {
            const float LOIN = 1e9f; float droit = pas, biais = pas * 1.41421356f;
            var d = new float[marques.Length];
            for (int k = 0; k < d.Length; k++) d[k] = marques[k] ? 0f : LOIN;
            for (int j = 0; j < h; j++)
                for (int i = 0; i < l; i++) {
                    int k = j * l + i; float m = d[k]; if (m == 0f) continue;
                    if (i > 0) m = Math.Min(m, d[k - 1] + droit);
                    if (j > 0) { m = Math.Min(m, d[k - l] + droit); if (i > 0) m = Math.Min(m, d[k - l - 1] + biais); if (i + 1 < l) m = Math.Min(m, d[k - l + 1] + biais); }
                    d[k] = m;
                }
            for (int j = h - 1; j >= 0; j--)
                for (int i = l - 1; i >= 0; i--) {
                    int k = j * l + i; float m = d[k]; if (m == 0f) continue;
                    if (i + 1 < l) m = Math.Min(m, d[k + 1] + droit);
                    if (j + 1 < h) { m = Math.Min(m, d[k + l] + droit); if (i + 1 < l) m = Math.Min(m, d[k + l + 1] + biais); if (i > 0) m = Math.Min(m, d[k + l - 1] + biais); }
                    d[k] = m;
                }
            return d;
        }

        // Un bruit à crêtes entre 0 et 1, le même pour le même point : cinq octaves sur un sol un peu tordu, pour que
        // les chaînes ne suivent pas la grille.
        private static double Bruit(double x, double z) {
            double tx = x + 18 * Onde(x / 90 + 11.3, z / 90 - 4.7), tz = z + 18 * Onde(x / 90 - 7.1, z / 90 + 3.9);
            double somme = 0, poids = 0, force = 1, frequence = 1 / 70.0;
            for (int octave = 0; octave < 5; octave++) {
                double crete = 1 - Math.Abs(Onde(tx * frequence, tz * frequence));
                somme += crete * crete * force; poids += force; force *= 0.5; frequence *= 2.1;
            }
            return somme / poids;
        }
        // Un bruit de gradient entre -1 et 1, nul aux nœuds de la grille entière, tiré d'un hachage d'entiers.
        private static double Onde(double x, double z) {
            double fx = Math.Floor(x), fz = Math.Floor(z); int ix = (int)fx, iz = (int)fz; double dx = x - fx, dz = z - fz;
            double u = dx * dx * dx * (dx * (dx * 6 - 15) + 10), v = dz * dz * dz * (dz * (dz * 6 - 15) + 10);
            double sud = Pente(ix, iz, dx, dz) + u * (Pente(ix + 1, iz, dx - 1, dz) - Pente(ix, iz, dx, dz));
            double nord = Pente(ix, iz + 1, dx, dz - 1) + u * (Pente(ix + 1, iz + 1, dx - 1, dz - 1) - Pente(ix, iz + 1, dx, dz - 1));
            return sud + v * (nord - sud);
        }
        private static double Pente(int ix, int iz, double dx, double dz) {
            uint h = unchecked((uint)ix * 0x9E3779B1u ^ (uint)iz * 0x85EBCA77u);
            h ^= h >> 15; h = unchecked(h * 0x2C1B3C6Du); h ^= h >> 12; h = unchecked(h * 0x297A2D39u); h ^= h >> 15;
            switch (h & 7) {
                case 0: return dx + dz; case 1: return dx - dz; case 2: return dz - dx; case 3: return -dx - dz;
                case 4: return dx * 1.41421356; case 5: return -dx * 1.41421356; case 6: return dz * 1.41421356; default: return -dz * 1.41421356;
            }
        }
    }
}
