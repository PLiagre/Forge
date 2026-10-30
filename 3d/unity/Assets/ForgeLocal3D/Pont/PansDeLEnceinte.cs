using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;

namespace Forge.Pont
{
    // Lot #925 — où poser chaque pièce du mur le long du contour servi, et quelle étape montrer.
    // Convention de la vue : rien ne retourne au monde. Longueurs du kit (`rempart_pise_10m`, `tour_ksar_0`).
    public enum NatureDePiece { Tour, Pan }
    // `Cote` : le sommet i d'une tour, le côté `c[i] → c[(i+1) % n]` d'un pan. `Indice` (rang depuis `c[i]`) et
    // `AbscisseM` (du centre à `c[i]`) valent 0 pour une tour. Le lacet est celui de `LectureDuBatiment`, façade dehors.
    public sealed class PieceDeLEnceinte
    {
        public NatureDePiece Nature { get; } public int Cote { get; } public int Indice { get; }
        public double CentreX { get; } public double CentreY { get; } public double AbscisseM { get; } public double LongueurM { get; } public double LacetDegres { get; }
        public PieceDeLEnceinte(NatureDePiece nature, int cote, int indice, double cx, double cy, double abscisse, double longueur, double lacet)
        { Nature = nature; Cote = cote; Indice = indice; CentreX = cx; CentreY = cy; AbscisseM = abscisse; LongueurM = longueur; LacetDegres = lacet; }
    }

    // Toutes les pièces, ou une absence qui nomme sa cause : jamais de découpe partielle.
    public sealed class DecoupeDeLEnceinte
    {
        public bool Presente { get; } public string Absence { get; } public IReadOnlyList<PieceDeLEnceinte> Pieces { get; }
        private DecoupeDeLEnceinte(bool presente, string absence, IList<PieceDeLEnceinte> pieces)
        { Presente = presente; Absence = absence; Pieces = new ReadOnlyCollection<PieceDeLEnceinte>(pieces); }
        internal static DecoupeDeLEnceinte De(List<PieceDeLEnceinte> pieces) => new DecoupeDeLEnceinte(true, "", pieces);
        internal static DecoupeDeLEnceinte Absente(string cause) => new DecoupeDeLEnceinte(false, cause, new PieceDeLEnceinte[0]);
    }

    public static class PansDeLEnceinte
    {
        public const double LongueurPanM = 10, CoteTourM = 7.2;
        public static DecoupeDeLEnceinte Decouper(EnceinteDuPlan e)
        {
            if (e == null) throw new ArgumentNullException(nameof(e));
            IReadOnlyList<PointLocal> c = e.Contour; int n = c.Count;
            for (int i = 0; i < n; i++)
                if (!EstFini(c[i].X) || !EstFini(c[i].Y)) return DecoupeDeLEnceinte.Absente("point " + Nom(i) + " non fini");
            // Le côté de fermeture `c[n-1] → c[0]` est un côté comme les autres.
            double[] ux = new double[n], uy = new double[n], lg = new double[n], tours = new double[n]; double aire = 0;
            for (int i = 0; i < n; i++)
            {
                PointLocal a = c[i], b = c[(i + 1) % n];
                lg[i] = Math.Sqrt((b.X - a.X) * (b.X - a.X) + (b.Y - a.Y) * (b.Y - a.Y));
                if (lg[i] == 0) return DecoupeDeLEnceinte.Absente("côté " + Nom(i) + " : longueur nulle");
                ux[i] = (b.X - a.X) / lg[i]; uy[i] = (b.Y - a.Y) / lg[i]; aire += a.X * b.Y - b.X * a.Y;
            }
            if (aire == 0) return DecoupeDeLEnceinte.Absente("contour plat");
            // Normale sortante du côté i : s·(uy, −ux), quel que soit le sens du tracé. Une tour suit la bissectrice extérieure.
            double s = aire > 0 ? 1 : -1;
            for (int i = 0; i < n; i++)
            {
                int p = (i + n - 1) % n; double bx = s * (uy[p] + uy[i]), by = -s * (ux[p] + ux[i]);
                if (Math.Sqrt(bx * bx + by * by) < 1e-9) return DecoupeDeLEnceinte.Absente("sommet " + Nom(i) + " : demi-tour");
                tours[i] = Lacet(bx, by);
            }
            var pieces = new List<PieceDeLEnceinte>();
            for (int i = 0; i < n; i++)
            {
                pieces.Add(new PieceDeLEnceinte(NatureDePiece.Tour, i, 0, c[i].X, c[i].Y, 0, CoteTourM, tours[i]));
                // Une demi-tour retirée à chaque bout ; les pans se partagent le reste, jamais plus longs que la pièce du kit.
                double libre = lg[i] - CoteTourM; if (libre <= 0) continue;
                int k = (int)Math.Ceiling(libre / LongueurPanM); double longueur = libre / k, lacet = Lacet(s * uy[i], -s * ux[i]);
                for (int j = 0; j < k; j++)
                {
                    double x = CoteTourM / 2 + (j + 0.5) * longueur;
                    pieces.Add(new PieceDeLEnceinte(NatureDePiece.Pan, i, j, c[i].X + ux[i] * x, c[i].Y + uy[i] * x, x, longueur, lacet));
                }
            }
            return DecoupeDeLEnceinte.De(pieces);
        }

        // Une seule étape pour tout le mur, comme un seul chantier : celle de `LectureDuBatiment.Etape` (`fourni × 2 < requis`).
        public static EtapeDuBatiment Etape(EnceinteDuPlan e)
        {
            if (e == null) throw new ArgumentNullException(nameof(e));
            if (!e.EnChantier) return EtapeDuBatiment.Fini;
            return e.TravailFourni < e.TravailRequis - e.TravailFourni ? EtapeDuBatiment.Piquets : EtapeDuBatiment.Murs;
        }
        private static double Lacet(double fx, double fy) { double l = Math.Atan2(-fx, -fy) * 180 / Math.PI; if (l < 0) l += 360; return l >= 360 ? l - 360 : l; }
        private static string Nom(int i) => i.ToString(CultureInfo.InvariantCulture);
        private static bool EstFini(double v) => !double.IsNaN(v) && !double.IsInfinity(v);
    }
}
