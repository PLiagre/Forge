using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;

namespace Forge.Pont
{
    // Lot #736 — la case `Indice` du logis `Maison`, en mètres locaux, lacet de `LectureDuBatiment`.
    public sealed class CaseDeMaison
    {
        public int Maison { get; }
        public int Indice { get; }
        public double CentreX { get; }
        public double CentreY { get; }
        public double LacetDegres { get; }
        public double LargeurM { get; }
        public double ProfondeurM { get; }

        public CaseDeMaison(int maison, int indice, double cx, double cy, double lacet, double largeur, double profondeur)
        {
            Maison = maison; Indice = indice; CentreX = cx; CentreY = cy;
            LacetDegres = lacet; LargeurM = largeur; ProfondeurM = profondeur;
        }
    }

    // Toutes les cases, ou une absence qui nomme sa cause : jamais de pose partielle.
    public sealed class PoseDesMaisons
    {
        public bool Presente { get; }
        public string Absence { get; }
        public IReadOnlyList<CaseDeMaison> Cases { get; }

        private PoseDesMaisons(bool presente, string absence, IList<CaseDeMaison> cases)
        {
            Presente = presente; Absence = absence; Cases = new ReadOnlyCollection<CaseDeMaison>(cases);
        }

        internal static PoseDesMaisons De(List<CaseDeMaison> cases) => new PoseDesMaisons(true, "", cases);
        internal static PoseDesMaisons Absente(string cause) => new PoseDesMaisons(false, cause, new CaseDeMaison[0]);
    }

    // Vue, niveau 3 : la façade est l'arête la plus proche d'un segment de rue parallèle ; les foyers se rangent depuis cette rue.
    public static class MaisonsDeLaBase
    {
        public const double SinusParallele = 0.001;

        public static PoseDesMaisons Poser(BaseDuPlan @base)
        {
            if (@base == null) throw new ArgumentNullException(nameof(@base));
            var cases = new List<CaseDeMaison>();
            for (int i = 0; i < @base.Maisons.Count; i++)
            {
                string nom = "maison " + i.ToString(CultureInfo.InvariantCulture) + " : ";
                IReadOnlyList<PointLocal> c = @base.Maisons[i].Emprise;
                if (c.Count != 4)
                    return PoseDesMaisons.Absente(nom + "emprise de " + c.Count.ToString(CultureInfo.InvariantCulture) + " points");
                int a = Facade(c, @base.Rues);
                if (a < 0) return PoseDesMaisons.Absente(nom + "aucune rue parallèle");
                PointLocal c0 = c[a], c1 = c[(a + 1) % 4];
                double dx = c1.X - c0.X, dy = c1.Y - c0.Y, f = Math.Sqrt(dx * dx + dy * dy);
                double ux = dx / f, uy = dy / f, gx = 0, gy = 0;
                for (int t = 0; t < 4; t++) { gx += c[t].X; gy += c[t].Y; }
                gx /= 4; gy /= 4;
                // n pointe vers le centre ; la façade sortante est −n, donc le lacet est atan2(nx, ny).
                double nx = -uy, ny = ux, vers = (gx - (c0.X + c1.X) / 2) * nx + (gy - (c0.Y + c1.Y) / 2) * ny;
                if (vers < 0) { nx = -nx; ny = -ny; vers = -vers; }
                double p = 2 * vers;
                if (!(p > 0)) return PoseDesMaisons.Absente(nom + "emprise plate");
                double lacet = Math.Atan2(nx, ny) * 180 / Math.PI;
                if (lacet < 0) lacet += 360; else if (lacet >= 360) lacet -= 360;
                long k = @base.Maisons[i].Foyers, parRang = (long)Math.Ceiling(Math.Sqrt(k * f / p));
                long rangs = (k + parRang - 1) / parRang;
                double largeur = f / parRang, profondeur = p / rangs;
                for (long j = 0; j < k; j++)
                {
                    double le = (j % parRang + 0.5) * largeur, lp = (j / parRang + 0.5) * profondeur;
                    cases.Add(new CaseDeMaison(i, (int)j, c0.X + ux * le + nx * lp, c0.Y + uy * le + ny * lp, lacet, largeur, profondeur));
                }
            }
            return PoseDesMaisons.De(cases);
        }

        // Arête la plus proche d'un segment de rue parallèle où son milieu se projette, la première à égalité ; -1 si aucune.
        private static int Facade(IReadOnlyList<PointLocal> c, IReadOnlyList<RueDeBase> rues)
        {
            int facade = -1; double meilleure = double.PositiveInfinity;
            for (int a = 0; a < 4; a++)
            {
                PointLocal c0 = c[a], c1 = c[(a + 1) % 4];
                double ex = c1.X - c0.X, ey = c1.Y - c0.Y, le = Math.Sqrt(ex * ex + ey * ey);
                if (le == 0) continue;
                double mx = (c0.X + c1.X) / 2, my = (c0.Y + c1.Y) / 2;
                foreach (RueDeBase rue in rues)
                    for (int j = 0; j + 1 < rue.Points.Count; j++)
                    {
                        PointLocal p0 = rue.Points[j], q = rue.Points[j + 1];
                        double sx = q.X - p0.X, sy = q.Y - p0.Y, s2 = sx * sx + sy * sy;
                        if (s2 == 0) continue;
                        double ls = Math.Sqrt(s2);
                        if (!(Math.Abs(ex * sy - ey * sx) / (le * ls) < SinusParallele)) continue;
                        double proj = ((mx - p0.X) * sx + (my - p0.Y) * sy) / s2;
                        if (proj < 0 || proj > 1) continue;
                        double d = Math.Abs((mx - p0.X) * sy - (my - p0.Y) * sx) / ls;
                        if (d < meilleure) { meilleure = d; facade = a; }
                    }
            }
            return facade;
        }
    }
}
