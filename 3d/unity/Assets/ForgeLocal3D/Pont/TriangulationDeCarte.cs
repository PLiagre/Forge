using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using UnityEngine;

namespace Forge.Pont
{
    // Les triangles d'un polygone de la carte, posés à plat (Y = 0), en km autour d'une origine :
    // trois sommets par triangle, non partagés, et `Triangles[i] == i`.
    public sealed class MaillageDePolygone
    {
        public IReadOnlyList<Vector3> Sommets { get; }
        public IReadOnlyList<int> Triangles { get; }

        internal MaillageDePolygone(IEnumerable<Vector3> sommets)
        {
            var liste = new List<Vector3>(sommets);
            Sommets = new ReadOnlyCollection<Vector3>(liste);
            Triangles = new ReadOnlyCollection<int>(Enumerable.Range(0, liste.Count).ToList());
        }
    }

    // Change un polygone de `/carte` (extérieur et trous, en mètres EPSG:3035) en triangles Unity.
    // Pourquoi des bandes et non des oreilles : 29 anneaux servis se croisent eux-mêmes (arrondi au mètre,
    // Douglas-Peucker), et des sommets sont partagés entre anneaux d'un même polygone. Une découpe en
    // oreilles suppose des anneaux simples et disjoints ; ici, on coupe le plan en bandes horizontales à
    // chaque sommet et à chaque croisement, et la règle pair-impair (celle de `point_dans_geometrie` de
    // `jeu/sim/villes.py`) dit dans chaque bande ce qui est dedans : chaque point est couvert une fois au
    // plus, quel que soit le sens des anneaux.
    public static class TriangulationDeCarte
    {
        private readonly struct Arete
        {
            public readonly double X0, Y0, X1, Y1;
            public Arete(PointCarte a, PointCarte b) { X0 = a.X; Y0 = a.Y; X1 = b.X; Y1 = b.Y; }

            // Le x de l'arête à l'ordonnée y, exact aux extrémités.
            public double X(double y)
            {
                if (y == Y0) return X0;
                if (y == Y1) return X1;
                return X0 + (y - Y0) / (Y1 - Y0) * (X1 - X0);
            }
        }

        public static MaillageDePolygone Trianguler(PolygoneDeCarte polygone, PointCarte origine)
        {
            if (polygone == null) throw new ArgumentNullException(nameof(polygone));
            if (!Fini(origine.X) || !Fini(origine.Y))
                throw new ArgumentOutOfRangeException(nameof(origine), "(" + origine.X + " ; " + origine.Y + ")", "une origine finie attendue");

            // L'extérieur et les trous ensemble : un anneau est fermé, aucune arête de retour à ajouter.
            var anneaux = new List<IReadOnlyList<PointCarte>> { polygone.Exterieur };
            anneaux.AddRange(polygone.Trous);
            var aretes = new List<Arete>();
            var coupes = new List<double>();
            foreach (var anneau in anneaux)
            {
                for (int i = 0; i < anneau.Count; i++) coupes.Add(anneau[i].Y);
                for (int i = 0; i + 1 < anneau.Count; i++) aretes.Add(new Arete(anneau[i], anneau[i + 1]));
            }
            // Les croisements propres, d'un même anneau ou de deux anneaux : une bande ne contient aucun croisement.
            for (int i = 0; i < aretes.Count; i++)
                for (int j = i + 1; j < aretes.Count; j++)
                    if (Croisement(aretes[i], aretes[j], out double y)) coupes.Add(y);
            coupes.Sort();
            List<double> ordonnees = coupes.Distinct().ToList();

            // Les arêtes horizontales ne bornent aucune bande.
            List<int> obliques = Enumerable.Range(0, aretes.Count).Where(i => aretes[i].Y0 != aretes[i].Y1).ToList();
            var sommets = new List<Vector3>();
            for (int k = 0; k + 1 < ordonnees.Count; k++)
            {
                double y0 = ordonnees[k], y1 = ordonnees[k + 1], milieu = (y0 + y1) / 2;
                // Triées par leur x à mi-hauteur, l'indice départageant : aucun ordre caché.
                List<Arete> actives = obliques.Where(i => Math.Min(aretes[i].Y0, aretes[i].Y1) <= y0 && Math.Max(aretes[i].Y0, aretes[i].Y1) >= y1)
                    .OrderBy(i => aretes[i].X(milieu)).ThenBy(i => i).Select(i => aretes[i]).ToList();
                if (actives.Count % 2 != 0)
                    throw new InvalidOperationException("bande " + y0 + " – " + y1 + " : " + actives.Count + " arêtes actives, un nombre pair attendu");
                for (int p = 0; p < actives.Count; p += 2)
                {
                    Arete g = actives[p], d = actives[p + 1];
                    Vector3 a = Point(g.X(y0), y0, origine), b = Point(d.X(y0), y0, origine);
                    Vector3 c = Point(d.X(y1), y1, origine), dd = Point(g.X(y1), y1, origine);
                    Ajouter(sommets, a, dd, c);
                    Ajouter(sommets, a, c, b);
                }
            }
            return new MaillageDePolygone(sommets);
        }

        // Un croisement est propre quand il est strictement intérieur aux deux segments.
        private static bool Croisement(Arete p, Arete q, out double y)
        {
            y = 0;
            double rx = p.X1 - p.X0, ry = p.Y1 - p.Y0, sx = q.X1 - q.X0, sy = q.Y1 - q.Y0;
            double denominateur = rx * sy - ry * sx;
            if (denominateur == 0) return false;
            double qpx = q.X0 - p.X0, qpy = q.Y0 - p.Y0;
            double t = (qpx * sy - qpy * sx) / denominateur, u = (qpx * ry - qpy * rx) / denominateur;
            if (!(t > 0 && t < 1 && u > 0 && u < 1)) return false;
            y = p.Y0 + t * ry;
            return true;
        }

        // Tout en double jusqu'ici ; X est l'est, Z le nord, en km.
        internal static Vector3 Point(double x, double y, PointCarte origine) =>
            new Vector3((float)((x - origine.X) / 1000.0), 0f, (float)((y - origine.Y) / 1000.0));

        // Gardé seulement s'il est tourné vers le haut une fois en float : cela retire aussi les triangles plats.
        private static void Ajouter(List<Vector3> sommets, Vector3 a, Vector3 b, Vector3 c)
        {
            double produit = ((double)b.z - a.z) * ((double)c.x - a.x) - ((double)b.x - a.x) * ((double)c.z - a.z);
            if (!(produit > 0)) return;
            sommets.Add(a);
            sommets.Add(b);
            sommets.Add(c);
        }

        private static bool Fini(double v) => !double.IsNaN(v) && !double.IsInfinity(v);
    }
}
