using System;
using System.Collections.Generic;
using System.Globalization;

namespace Forge.Pont
{
    // L'étape qu'un bâtiment du plan montre, et la façon de le poser sur sa parcelle.
    // C'est une convention de la vue (l'orientation est au niveau 3 du modèle) : rien ne retourne au monde.
    public enum EtapeDuBatiment { Piquets, Murs, Fini }

    // Une pose sur le plan, ou une absence qui nomme sa cause : jamais les deux. Absente, les cinq nombres
    // valent NaN, pour qu'aucune vue ne pose une pièce à l'origine par mégarde.
    public sealed class PoseDuBatiment
    {
        public bool Presente { get; }
        public string Absence { get; }
        // Le centre, en mètres locaux du bourg.
        public double CentreX { get; }
        public double CentreY { get; }
        // Unitaire, perpendiculaire à `c0→c1`, tourné vers l'extérieur du lot (vers la rue).
        public double FacadeX { get; }
        public double FacadeY { get; }
        // θ dans [0 ; 360) : `Quaternion.Euler(0, θ, 0)` tourne la façade +Z du prefab vers (-FacadeX, 0, -FacadeY),
        // dans le repère où (x, y) du plan devient (-x, sol, -y).
        public double LacetDegres { get; }

        private PoseDuBatiment(bool presente, string absence, double cx, double cy, double fx, double fy, double lacet)
        {
            Presente = presente;
            Absence = absence;
            CentreX = cx;
            CentreY = cy;
            FacadeX = fx;
            FacadeY = fy;
            LacetDegres = lacet;
        }

        public static PoseDuBatiment De(double cx, double cy, double fx, double fy, double lacet) =>
            new PoseDuBatiment(true, "", cx, cy, fx, fy, lacet);

        public static PoseDuBatiment Absente(string cause) =>
            new PoseDuBatiment(false, cause ?? throw new ArgumentNullException(nameof(cause)),
                double.NaN, double.NaN, double.NaN, double.NaN, double.NaN);
    }

    public static class LectureDuBatiment
    {
        // Achevé : fini. En chantier : piquets tant que moins de la moitié du travail est fournie, murs ensuite.
        // La nature n'y joue aucun rôle.
        public static EtapeDuBatiment Etape(BatimentDuPlan b)
        {
            if (b == null) throw new ArgumentNullException(nameof(b));
            return Etape(b.EnChantier, b.TravailRequis, b.TravailFourni);
        }

        // Un bâtiment de province suit la même règle, sur le chantier que le monde sert.
        public static EtapeDuBatiment Etape(BatimentDeProvinceDuPlan b)
        {
            if (b == null) throw new ArgumentNullException(nameof(b));
            return Etape(b.EnChantier, b.TravailRequis, b.TravailFourni);
        }

        private static EtapeDuBatiment Etape(bool enChantier, long requis, long fourni)
        {
            if (!enChantier) return EtapeDuBatiment.Fini;
            // `fourni × 2 < requis`, écrit sans débordement.
            return fourni < requis - fourni ? EtapeDuBatiment.Piquets : EtapeDuBatiment.Murs;
        }

        // Un bâtiment de province se pose sur le contour de sa parcelle, par la même règle de façade qu'un
        // bâtiment du plan. Sans parcelle (posé depuis la carte) ou sur une parcelle que le plan n'a pas, il est
        // déclaré absent : la vue ne lui invente pas de place.
        public static PoseDuBatiment Poser(BatimentDeProvinceDuPlan b, PlanLu plan)
        {
            if (b == null) throw new ArgumentNullException(nameof(b));
            if (plan == null) throw new ArgumentNullException(nameof(plan));
            string id = b.Identifiant.ToString(CultureInfo.InvariantCulture);
            if (b.Parcelle == BatimentDeProvinceDuPlan.SansParcelle)
                return PoseDuBatiment.Absente(b.Nature + " " + id + " : aucune parcelle, posé depuis la carte");
            foreach (var parcelle in plan.Parcelles)
                if (parcelle.Identifiant == b.Parcelle) return Poser(b.Nature + " " + id, parcelle.Contour);
            return PoseDuBatiment.Absente(b.Nature + " " + id + " : parcelle "
                + b.Parcelle.ToString(CultureInfo.InvariantCulture) + " absente du plan");
        }

        // Le centre est la moyenne des sommets de l'emprise ; la façade est toujours le côté `c0→c1`
        // (MODELE.md : « la façade borde la chaussée »). Les rues ne sont pas lues.
        public static PoseDuBatiment Poser(BatimentDuPlan b)
        {
            if (b == null) throw new ArgumentNullException(nameof(b));
            return Poser("bâtiment " + b.Identifiant.ToString(CultureInfo.InvariantCulture), b.Emprise);
        }

        private static PoseDuBatiment Poser(string nom, IReadOnlyList<PointLocal> emprise)
        {
            if (emprise.Count < 3)
                return PoseDuBatiment.Absente(nom + " : emprise de "
                    + emprise.Count.ToString(CultureInfo.InvariantCulture) + " point(s)");
            foreach (var p in emprise)
                if (!EstFini(p.X) || !EstFini(p.Y))
                    return PoseDuBatiment.Absente(nom + " : point non fini");

            double cx = 0, cy = 0;
            foreach (var p in emprise) { cx += p.X; cy += p.Y; }
            cx /= emprise.Count;
            cy /= emprise.Count;

            PointLocal c0 = emprise[0], c1 = emprise[1];
            double ex = c1.X - c0.X, ey = c1.Y - c0.Y;
            double longueur = Math.Sqrt(ex * ex + ey * ey);
            if (longueur == 0) return PoseDuBatiment.Absente(nom + " : façade nulle");

            double mx = ey / longueur, my = -ex / longueur;
            double s = mx * (cx - (c0.X + c1.X) / 2) + my * (cy - (c0.Y + c1.Y) / 2);
            if (s == 0) return PoseDuBatiment.Absente(nom + " : emprise plate");
            // `m` pointe vers l'intérieur du lot : la façade regarde de l'autre côté.
            if (s > 0) { mx = -mx; my = -my; }

            double lacet = Math.Atan2(-mx, -my) * 180 / Math.PI;
            if (lacet < 0) lacet += 360;
            if (lacet >= 360) lacet -= 360;
            return PoseDuBatiment.De(cx, cy, mx, my, lacet);
        }

        private static bool EstFini(double v) => !double.IsNaN(v) && !double.IsInfinity(v);
    }
}
