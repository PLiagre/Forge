using System;
using System.Globalization;

namespace Forge.Pont
{
    // Soit la parcelle tracée et son intention `decouper_parcelle`, soit une absence qui nomme sa cause.
    // Quand l'absence est déclarée : Rue et Segment valent -1, les mesures NaN, Cote "" et IntentionJson null.
    public sealed class ParcelleTracee
    {
        public bool Presente { get; }
        public string Absence { get; }
        public long Rue { get; }
        public int Segment { get; }
        public double DebutM { get; }
        public double FacadeM { get; }
        public double ProfondeurM { get; }
        public string Cote { get; }
        public string IntentionJson { get; }

        private ParcelleTracee(bool presente, string absence, long rue, int segment,
            double debutM, double facadeM, double profondeurM, string cote, string intentionJson)
        {
            Presente = presente;
            Absence = absence;
            Rue = rue;
            Segment = segment;
            DebutM = debutM;
            FacadeM = facadeM;
            ProfondeurM = profondeurM;
            Cote = cote;
            IntentionJson = intentionJson;
        }

        internal static ParcelleTracee De(long cellId, long rue, int segment,
            double debutM, double facadeM, double profondeurM, string cote)
        {
            string json = "{\"type\":\"decouper_parcelle\""
                + ",\"cell\":" + cellId.ToString(CultureInfo.InvariantCulture)
                + ",\"rue\":" + rue.ToString(CultureInfo.InvariantCulture)
                + ",\"segment\":" + segment.ToString(CultureInfo.InvariantCulture)
                + ",\"debut_m\":" + TraceDeParcelle.Nombre(debutM)
                + ",\"facade_m\":" + TraceDeParcelle.Nombre(facadeM)
                + ",\"profondeur_m\":" + TraceDeParcelle.Nombre(profondeurM)
                + ",\"cote\":\"" + cote + "\"}";
            return new ParcelleTracee(true, "", rue, segment, debutM, facadeM, profondeurM, cote, json);
        }

        internal static ParcelleTracee Absente(string cause) =>
            new ParcelleTracee(false, cause, -1, -1, double.NaN, double.NaN, double.NaN, "", null);
    }

    // Le calcul du geste « découpe des parcelles » : deux coins opposés posés au sol, le premier près
    // de la rue (il choisit la rue et le segment), le second qui dit la façade, le côté et la profondeur.
    // Le monde reste le seul juge : il revalide l'intention au dépôt. Ni parcelle ni bâtiment du plan
    // n'est lu ici (les chevauchements sont au niveau 3 du modèle) ; aucune mesure n'est arrondie.
    public static class TraceDeParcelle
    {
        // Convention de la vue, pas du monde : au-delà, le premier point est « trop loin d'une rue ».
        public const double SaisieMaxM = 10;

        public static ParcelleTracee Calculer(PlanLu plan, PointLocal premier, PointLocal second)
        {
            if (plan == null) throw new ArgumentNullException(nameof(plan));
            if (!Fini(premier) || !Fini(second)) return ParcelleTracee.Absente("point non fini");

            // La rue et le segment les plus proches du premier point, au segment borné.
            // Plus petite distance strictement : à égalité, la première rue puis le plus petit segment.
            RueDuPlan rue = null;
            int segment = -1;
            double meilleure = double.PositiveInfinity;
            foreach (var candidate in plan.Rues)
            {
                for (int i = 0; i + 1 < candidate.Points.Count; i++)
                {
                    PointLocal a = candidate.Points[i], b = candidate.Points[i + 1];
                    double dx = b.X - a.X, dy = b.Y - a.Y;
                    double carre = dx * dx + dy * dy;
                    if (carre == 0) continue; // un segment nul ne porte aucune façade
                    double t = ((premier.X - a.X) * dx + (premier.Y - a.Y) * dy) / carre;
                    t = Math.Max(0, Math.Min(1, t));
                    double ex = premier.X - (a.X + t * dx), ey = premier.Y - (a.Y + t * dy);
                    double distance = Math.Sqrt(ex * ex + ey * ey);
                    if (rue == null || distance < meilleure)
                    {
                        rue = candidate;
                        segment = i;
                        meilleure = distance;
                    }
                }
            }
            if (rue == null) return ParcelleTracee.Absente("aucune rue au plan");
            if (meilleure > SaisieMaxM)
                return ParcelleTracee.Absente("point trop loin d'une rue : " + Nombre(meilleure) + " m > " + Nombre(SaisieMaxM) + " m");

            PointLocal debut = rue.Points[segment], fin = rue.Points[segment + 1];
            double sx = fin.X - debut.X, sy = fin.Y - debut.Y;
            double longueur = Math.Sqrt(sx * sx + sy * sy);
            double ux = sx / longueur, uy = sy / longueur;
            double nx = -uy, ny = ux; // la normale gauche, en regardant dans le sens du tracé

            double t1 = (premier.X - debut.X) * ux + (premier.Y - debut.Y) * uy;
            double t2 = (second.X - debut.X) * ux + (second.Y - debut.Y) * uy;
            double debutM = Math.Min(t1, t2);
            double facadeM = Math.Max(t1, t2) - Math.Min(t1, t2);
            // Le même calcul que le monde, sans tolérance.
            if (debutM < 0 || debutM + facadeM > longueur)
                return ParcelleTracee.Absente("façade dépasse le segment : " + Nombre(debutM) + " + " + Nombre(facadeM) + " > " + Nombre(longueur));
            if (facadeM == 0) return ParcelleTracee.Absente("façade nulle");

            double h = (second.X - debut.X) * nx + (second.Y - debut.Y) * ny;
            string cote = h > 0 ? "gauche" : "droite";
            double demiLargeur = rue.LargeurM * 0.5;
            double profondeurM = Math.Abs(h) - demiLargeur;
            if (profondeurM <= 0)
                return ParcelleTracee.Absente("second point dans la chaussée : " + Nombre(Math.Abs(h)) + " m ≤ " + Nombre(demiLargeur) + " m");

            return ParcelleTracee.De(plan.CellId, rue.Identifiant, segment, debutM, facadeM, profondeurM, cote);
        }

        internal static string Nombre(double valeur) => valeur.ToString("R", CultureInfo.InvariantCulture);

        private static bool Fini(PointLocal p) =>
            !double.IsNaN(p.X) && !double.IsInfinity(p.X) && !double.IsNaN(p.Y) && !double.IsInfinity(p.Y);
    }
}
