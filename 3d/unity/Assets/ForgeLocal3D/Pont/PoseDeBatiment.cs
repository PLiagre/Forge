using System;
using System.Collections.Generic;
using System.Globalization;

namespace Forge.Pont
{
    // Soit la pose d'un bâtiment sur une parcelle et son intention `poser_batiment`, soit une absence
    // qui nomme sa cause. Quand l'absence est déclarée : Parcelle vaut -1, Nature "" et IntentionJson null.
    public sealed class BatimentPose
    {
        public bool Presente { get; }
        public string Absence { get; }
        public long Parcelle { get; }
        public string Nature { get; }
        public string IntentionJson { get; }

        private BatimentPose(bool presente, string absence, long parcelle, string nature, string intentionJson)
        {
            Presente = presente;
            Absence = absence;
            Parcelle = parcelle;
            Nature = nature;
            IntentionJson = intentionJson;
        }

        internal static BatimentPose De(long cellId, long parcelle, string nature)
        {
            string json = "{\"type\":\"poser_batiment\""
                + ",\"cell\":" + cellId.ToString(CultureInfo.InvariantCulture)
                + ",\"parcelle\":" + parcelle.ToString(CultureInfo.InvariantCulture)
                + ",\"nature\":\"" + nature + "\"}";
            return new BatimentPose(true, "", parcelle, nature, json);
        }

        internal static BatimentPose Absente(string cause) => new BatimentPose(false, cause, -1, "", null);
    }

    // Le calcul du geste « pose un atelier » : une nature choisie, puis un point désigné au sol.
    // Le bâtiment va sur la première parcelle du plan, dans l'ordre de sa liste, qui contient le point.
    // Le monde reste le seul juge : il revalide l'intention au dépôt. Les bâtiments du plan ne sont
    // pas lus ici : « parcelle déjà bâtie » ou « déjà promise », c'est le reçu du monde qui le dit.
    public static class PoseDeBatiment
    {
        // La liste fermée du geste `poser_batiment` du monde (`NATURES_BATIMENT` de `sim/intentions.py`).
        public static readonly IReadOnlyList<string> Natures = Array.AsReadOnly(new[] { "maison", "scierie", "four" });

        // La règle pair-impair, contour fermé (le dernier sommet rejoint le premier).
        // Un point sur le bord suit ce que la formule rend.
        public static bool Contient(IReadOnlyList<PointLocal> contour, PointLocal point)
        {
            if (contour == null) throw new ArgumentNullException(nameof(contour));
            if (contour.Count < 3 || !Fini(point)) return false;

            double px = point.X, py = point.Y;
            bool dedans = false;
            for (int i = 0, j = contour.Count - 1; i < contour.Count; j = i++)
            {
                double xi = contour[i].X, yi = contour[i].Y;
                double xj = contour[j].X, yj = contour[j].Y;
                if ((yi > py) != (yj > py) && px < (xj - xi) * (py - yi) / (yj - yi) + xi)
                    dedans = !dedans;
            }
            return dedans;
        }

        public static ParcelleDuPlan ParcelleSous(PlanLu plan, PointLocal point)
        {
            if (plan == null) throw new ArgumentNullException(nameof(plan));
            foreach (var parcelle in plan.Parcelles)
                if (Contient(parcelle.Contour, point)) return parcelle;
            return null;
        }

        public static BatimentPose Calculer(PlanLu plan, PointLocal point, string nature)
        {
            if (plan == null) throw new ArgumentNullException(nameof(plan));
            // La nature d'abord, comparée comme le monde : ni casse ni espace tolérés.
            bool connue = false;
            if (nature != null)
                foreach (var n in Natures)
                    if (string.Equals(n, nature, StringComparison.Ordinal)) connue = true;
            if (!connue)
                return BatimentPose.Absente("nature inconnue : " + (nature == null ? "null" : "\"" + nature + "\""));
            if (!Fini(point)) return BatimentPose.Absente("point non fini");
            if (plan.Parcelles.Count == 0) return BatimentPose.Absente("aucune parcelle au plan");

            var sous = ParcelleSous(plan, point);
            if (sous == null)
                return BatimentPose.Absente("aucune parcelle sous le point : (" + Nombre(point.X) + ", " + Nombre(point.Y) + ")");
            return BatimentPose.De(plan.CellId, sous.Identifiant, nature);
        }

        private static string Nombre(double valeur) => valeur.ToString("R", CultureInfo.InvariantCulture);

        private static bool Fini(PointLocal p) =>
            !double.IsNaN(p.X) && !double.IsInfinity(p.X) && !double.IsNaN(p.Y) && !double.IsInfinity(p.Y);
    }
}
