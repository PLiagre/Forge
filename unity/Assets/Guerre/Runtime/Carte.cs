using System;
using System.Collections.Generic;
using Unity.Collections;
using Unity.Entities;
using Unity.Mathematics;
using UnityEngine;

namespace Guerre
{
    // Ce que la carte sait d'elle-même, écrit par Construire.cs à côté de la scène : les emprises des
    // murs, des tours, des maisons ; les tabliers des ponts ; les lieux nommés que visent les essais.
    public sealed class CarteDonnees : ScriptableObject
    {
        [Serializable] public struct Bloc { public string nature; public Vector2 centre, demi; public float angle; }
        [Serializable] public struct Tablier { public string nom; public Vector2 centre, demi; public float angle, hauteur; }
        [Serializable] public struct Lieu { public string nom; public Vector2 p, front; }
        // Un pan de rempart appareillé pierre à pierre, qu'on peut abattre : centre au pied du mur, axe
        // du mur (angle en degrés vers l'extérieur), longueur, hauteur, épaisseur.
        [Serializable] public struct Pan { public Vector3 pied; public float exterieur, longueur, hauteur, epaisseur; }
        // Un engin de siège en batterie : sa place, le point qu'il vise, et la demi-longueur de mur qu'il bat
        // de part et d'autre de ce point (on promène le tir le long du mur pour ouvrir une brèche large).
        [Serializable] public struct Poste { public bool trebuchet; public Vector3 place, cible, etendue; }

        public List<Bloc> blocs = new List<Bloc>();
        public List<Tablier> tabliers = new List<Tablier>();
        public List<Lieu> lieux = new List<Lieu>();
        public List<Pan> pans = new List<Pan>();
        public List<Poste> batterie = new List<Poste>();
        public Tablier porte;   // l'emprise du passage de la porte, pour la fermer

        public Lieu Trouver(string nom)
        {
            foreach (var l in lieux) if (l.nom == nom) return l;
            throw new KeyNotFoundException("lieu inconnu : " + nom);
        }

        // Un point est-il dans l'emprise d'un bloc (rectangle tourné) ?
        public static bool Dans(in Bloc b, Vector2 p, float marge = 0f)
        {
            Vector2 d = p - b.centre;
            float c = Mathf.Cos(b.angle), s = Mathf.Sin(b.angle);
            float x = d.x * c + d.y * s, y = -d.x * s + d.y * c;
            return Mathf.Abs(x) <= b.demi.x + marge && Mathf.Abs(y) <= b.demi.y + marge;
        }
    }

    // La grille des obstacles, au mètre : 1 là où un homme ne peut pas se tenir (un mur, une maison,
    // une paroi trop raide). Elle est lue par chaque soldat, et par le planificateur des chemins.
    public struct ObstaclesBlob
    {
        public BlobArray<byte> Bloque;
        public int Largeur, Hauteur;
        public float2 Origine;
        public float Pas;
    }

    public struct Obstacles : IComponentData
    {
        public BlobAssetReference<ObstaclesBlob> Blob;
    }

    // Une case trop raide pour qu'on s'y tienne : la paroi d'un ravin, un escarpement.
    [Unity.Burst.BurstCompile]
    public struct CalculerPentes : Unity.Jobs.IJobParallelFor
    {
        [ReadOnly] public BlobAssetReference<ReliefBlob> Relief;
        public NativeArray<byte> Bloque;
        public int Largeur;
        public float2 Origine;
        public float Pas, PenteMax;

        public void Execute(int i)
        {
            float2 p = Origine + new float2(i % Largeur + 0.5f, i / Largeur + 0.5f) * Pas;
            float h = 0.5f * Pas;
            float gx = Sol.Hauteur(ref Relief.Value, p + new float2(h, 0)) - Sol.Hauteur(ref Relief.Value, p - new float2(h, 0));
            float gz = Sol.Hauteur(ref Relief.Value, p + new float2(0, h)) - Sol.Hauteur(ref Relief.Value, p - new float2(0, h));
            if (math.length(new float2(gx, gz)) / Pas > PenteMax) Bloque[i] = 1;
        }
    }

    public static class Terrain2D
    {
        public static bool Bloque(ref ObstaclesBlob o, float2 p)
        {
            int2 c = (int2)math.floor((p - o.Origine) / o.Pas);
            if (c.x < 0 || c.y < 0 || c.x >= o.Largeur || c.y >= o.Hauteur) return true;
            return o.Bloque[c.y * o.Largeur + c.x] != 0;
        }
    }

    // Le chemin d'un régiment : une ligne brisée, avec l'abscisse curviligne de chaque point.
    // Le régiment y marche en colonne ; chaque rang suit la route à sa propre abscisse.
    public struct PointChemin : IBufferElementData
    {
        public float2 P;
        public float S;
    }

    public static class Route
    {
        // Le point de la route à l'abscisse s, et la direction de la route autour de lui. Avant le
        // départ et après l'arrivée, la route se prolonge en ligne droite.
        public static float2 Point(DynamicBuffer<PointChemin> c, float s, out float2 tangente)
        {
            int n = c.Length;
            if (n < 2) { tangente = new float2(0, 1); return n == 1 ? c[0].P : float2.zero; }
            if (s <= 0f)
            {
                tangente = math.normalizesafe(c[1].P - c[0].P, new float2(0, 1));
                return c[0].P + tangente * s;
            }
            float l = c[n - 1].S;
            if (s >= l)
            {
                tangente = math.normalizesafe(c[n - 1].P - c[n - 2].P, new float2(0, 1));
                return c[n - 1].P + tangente * (s - l);
            }
            int a = 0, b = n - 1;
            while (b - a > 1) { int m = (a + b) >> 1; if (c[m].S <= s) a = m; else b = m; }
            float u = (s - c[a].S) / math.max(c[b].S - c[a].S, 1e-4f);
            // Aux angles, la direction tourne progressivement sur quelques mètres, comme une colonne qui tourne.
            float2 t0 = math.normalizesafe(c[b].P - c[a].P, new float2(0, 1));
            float2 tAvant = a > 0 ? math.normalizesafe(c[a].P - c[a - 1].P, t0) : t0;
            float2 tApres = b < n - 1 ? math.normalizesafe(c[b + 1].P - c[b].P, t0) : t0;
            float longueur = c[b].S - c[a].S, reste = c[b].S - s, fait = s - c[a].S;
            const float Virage = 3f;
            float2 t = t0;
            if (fait < Virage && a > 0) t = math.normalizesafe(math.lerp(tAvant, t0, 0.5f + 0.5f * fait / Virage), t0);
            else if (reste < Virage && b < n - 1) t = math.normalizesafe(math.lerp(tApres, t0, 0.5f + 0.5f * reste / Virage), t0);
            tangente = t;
            return math.lerp(c[a].P, c[b].P, u);
        }
    }

    public static class RouteProche
    {
        // L'abscisse du point de la route le plus proche de p.
        public static float Abscisse(DynamicBuffer<PointChemin> c, float2 p)
        {
            float meilleure = float.MaxValue, s = 0;
            for (int k = 1; k < c.Length; k++)
            {
                float2 a = c[k - 1].P, d = c[k].P - a;
                float u = math.saturate(math.dot(p - a, d) / math.max(math.lengthsq(d), 1e-6f));
                float l = math.distancesq(p, a + d * u);
                if (l < meilleure) { meilleure = l; s = c[k - 1].S + (c[k].S - c[k - 1].S) * u; }
            }
            return s;
        }
    }

    // Le planificateur : un A* sur la grille au mètre, qui ne passe que là où il reste assez de place
    // de part et d'autre (la dégagement, distance au plus proche obstacle), et préfère le milieu des rues.
    public sealed class Planificateur
    {
        readonly byte[] bloque;
        readonly float[] degagement;
        public readonly int L, H;
        public readonly Vector2 Origine;
        public const float Pas = 1f;

        public Planificateur(byte[] bloque, int l, int h, Vector2 origine)
        {
            this.bloque = bloque; L = l; H = h; Origine = origine;
            degagement = Degagement(bloque, l, h);
        }

        // Distance de chaque case au plus proche obstacle, en mètres (chanfrein 3-4, deux passes).
        static float[] Degagement(byte[] b, int l, int h)
        {
            var d = new int[l * h];
            const int Inf = 1 << 28;
            for (int i = 0; i < d.Length; i++) d[i] = b[i] != 0 ? 0 : Inf;
            for (int y = 0; y < h; y++)
                for (int x = 0; x < l; x++)
                {
                    int i = y * l + x; int v = d[i];
                    if (v == 0) continue;
                    if (x > 0) v = Math.Min(v, d[i - 1] + 3);
                    if (y > 0) { v = Math.Min(v, d[i - l] + 3); if (x > 0) v = Math.Min(v, d[i - l - 1] + 4); if (x < l - 1) v = Math.Min(v, d[i - l + 1] + 4); }
                    d[i] = v;
                }
            for (int y = h - 1; y >= 0; y--)
                for (int x = l - 1; x >= 0; x--)
                {
                    int i = y * l + x; int v = d[i];
                    if (v == 0) continue;
                    if (x < l - 1) v = Math.Min(v, d[i + 1] + 3);
                    if (y < h - 1) { v = Math.Min(v, d[i + l] + 3); if (x < l - 1) v = Math.Min(v, d[i + l + 1] + 4); if (x > 0) v = Math.Min(v, d[i + l - 1] + 4); }
                    d[i] = v;
                }
            var r = new float[l * h];
            for (int i = 0; i < r.Length; i++) r[i] = Math.Min(d[i], Plafond) / 3f * Pas;
            return r;
        }

        // Le dégagement est plafonné à 40 m : au-delà, il ne change rien à aucun chemin. Une fenêtre peut
        // donc se recalculer seule, avec 40 m de marge autour de ce qui a changé.
        const int Plafond = 120;
        const int Marge = 41;

        // Des cases ont changé dans la fenêtre [x0, x1[ × [y0, y1[ (un mur tombé, des gravats, une porte fermée).
        public void Actualiser(byte[] cases, int x0, int y0, int x1, int y1)
        {
            int a0 = Math.Max(0, x0 - Marge), b0 = Math.Max(0, y0 - Marge), a1 = Math.Min(L, x1 + Marge), b1 = Math.Min(H, y1 + Marge);
            int l = a1 - a0, h = b1 - b0;
            var local = new byte[l * h];
            for (int y = 0; y < h; y++) for (int x = 0; x < l; x++) local[y * l + x] = cases[(b0 + y) * L + a0 + x];
            var d = Degagement(local, l, h);
            for (int y = Math.Max(y0, 0); y < Math.Min(y1, H); y++)
                for (int x = Math.Max(x0, 0); x < Math.Min(x1, L); x++)
                    degagement[y * L + x] = d[(y - b0) * l + x - a0];
        }

        int Case(Vector2 p)
        {
            int x = Mathf.FloorToInt((p.x - Origine.x) / Pas), y = Mathf.FloorToInt((p.y - Origine.y) / Pas);
            if (x < 0 || y < 0 || x >= L || y >= H) return -1;
            return y * L + x;
        }
        Vector2 Centre(int i) => Origine + new Vector2((i % L + 0.5f) * Pas, (i / L + 0.5f) * Pas);

        public float DegagementEn(Vector2 p) { int i = Case(p); return i < 0 ? 0f : degagement[i]; }

        // La ligne droite entre deux points garde-t-elle partout ce dégagement ?
        public bool Voit(Vector2 a, Vector2 b, float marge)
        {
            float d = Vector2.Distance(a, b);
            int n = Mathf.Max(1, Mathf.CeilToInt(d / (Pas * 0.5f)));
            for (int k = 0; k <= n; k++)
            {
                int i = Case(Vector2.Lerp(a, b, k / (float)n));
                if (i < 0 || degagement[i] < marge) return false;
            }
            return true;
        }

        // Le plus court chemin qui garde partout au moins `marge` de dégagement, dans une boîte autour des
        // deux points. Renvoie null si aucun n'existe. `degagementMin` reçoit le plus étroit du chemin.
        public List<Vector2> Chercher(Vector2 depart, Vector2 arrivee, float marge, out float degagementMin)
        {
            degagementMin = 0;
            int s = Case(depart), g = Case(arrivee);
            if (s < 0 || g < 0) return null;
            // On part et l'on arrive au plus proche endroit praticable.
            s = Proche(s, marge); g = Proche(g, marge);
            if (s < 0 || g < 0) return null;
            const int Bord = 250;
            int sx = s % L, sy = s / L, gx = g % L, gy = g / L;
            int x0 = Math.Max(0, Math.Min(sx, gx) - Bord), x1 = Math.Min(L - 1, Math.Max(sx, gx) + Bord);
            int y0 = Math.Max(0, Math.Min(sy, gy) - Bord), y1 = Math.Min(H - 1, Math.Max(sy, gy) + Bord);
            int bl = x1 - x0 + 1, bh = y1 - y0 + 1;
            var cout = new float[bl * bh];
            var venu = new int[bl * bh];
            for (int i = 0; i < cout.Length; i++) { cout[i] = float.MaxValue; venu[i] = -1; }
            int Loc(int i) => (i / L - y0) * bl + (i % L - x0);
            var file = new Tas();
            cout[Loc(s)] = 0; file.Ajouter(s, Heur(s, g));
            int[] dx = { 1, -1, 0, 0, 1, 1, -1, -1 }, dy = { 0, 0, 1, -1, 1, -1, 1, -1 };
            float[] pas = { 1, 1, 1, 1, 1.4142f, 1.4142f, 1.4142f, 1.4142f };
            bool trouve = false;
            while (file.Nombre > 0)
            {
                int i = file.Retirer();
                if (i == g) { trouve = true; break; }
                int ix = i % L, iy = i / L; float ci = cout[Loc(i)];
                for (int k = 0; k < 8; k++)
                {
                    int nx = ix + dx[k], ny = iy + dy[k];
                    if (nx < x0 || ny < y0 || nx > x1 || ny > y1) continue;
                    int j = ny * L + nx;
                    float dg = degagement[j];
                    if (dg < marge) continue;
                    // On préfère les voies larges et le milieu des rues : un passage étroit coûte jusqu'à quatre fois plus.
                    float c = ci + pas[k] * Pas * (1f + 3f * Mathf.Max(0f, 4f - dg) / 4f);
                    int lj = Loc(j);
                    if (c >= cout[lj]) continue;
                    cout[lj] = c; venu[lj] = i;
                    file.Ajouter(j, c + Heur(j, g));
                }
            }
            if (!trouve) return null;
            var cases = new List<int>();
            for (int i = g; i >= 0; i = venu[Loc(i)]) { cases.Add(i); if (i == s) break; }
            cases.Reverse();
            degagementMin = float.MaxValue;
            foreach (var i in cases) degagementMin = Mathf.Min(degagementMin, degagement[i]);
            var points = new List<Vector2>();
            foreach (var i in cases) points.Add(Centre(i));
            points[0] = depart; points[points.Count - 1] = arrivee;
            return points;
        }

        float Heur(int a, int b)
        {
            float x = Mathf.Abs(a % L - b % L), y = Mathf.Abs(a / L - b / L);
            return (Mathf.Max(x, y) + 0.4142f * Mathf.Min(x, y)) * Pas;
        }

        int Proche(int i, float marge)
        {
            if (degagement[i] >= marge) return i;
            int x = i % L, y = i / L;
            for (int r = 1; r < 40; r++)
                for (int yy = y - r; yy <= y + r; yy++)
                    for (int xx = x - r; xx <= x + r; xx++)
                    {
                        if (Math.Max(Math.Abs(xx - x), Math.Abs(yy - y)) != r || xx < 0 || yy < 0 || xx >= L || yy >= H) continue;
                        int j = yy * L + xx;
                        if (degagement[j] >= marge) return j;
                    }
            return -1;
        }

        // On tend le fil : on ne garde que les points dont on ne peut pas se passer en ligne droite.
        public List<Vector2> Tendre(List<Vector2> p, float marge)
        {
            var r = new List<Vector2> { p[0] };
            int i = 0;
            while (i < p.Count - 1)
            {
                int j = p.Count - 1;
                while (j > i + 1 && !Voit(p[i], p[j], marge)) j--;
                r.Add(p[j]); i = j;
            }
            return r;
        }

        sealed class Tas
        {
            readonly List<(int i, float f)> t = new List<(int, float)>();
            public int Nombre => t.Count;
            public void Ajouter(int i, float f)
            {
                t.Add((i, f)); int k = t.Count - 1;
                while (k > 0) { int p = (k - 1) >> 1; if (t[p].f <= t[k].f) break; (t[p], t[k]) = (t[k], t[p]); k = p; }
            }
            public int Retirer()
            {
                int r = t[0].i; var last = t[t.Count - 1]; t.RemoveAt(t.Count - 1);
                if (t.Count > 0)
                {
                    t[0] = last; int k = 0;
                    while (true)
                    {
                        int a = 2 * k + 1, b = a + 1, m = k;
                        if (a < t.Count && t[a].f < t[m].f) m = a;
                        if (b < t.Count && t[b].f < t[m].f) m = b;
                        if (m == k) break;
                        (t[m], t[k]) = (t[k], t[m]); k = m;
                    }
                }
                return r;
            }
        }
    }
}
