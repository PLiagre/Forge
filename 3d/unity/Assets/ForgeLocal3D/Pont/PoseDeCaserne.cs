using System;
using System.Globalization;

namespace Forge.Pont
{
    // Soit une caserne désignée sur une parcelle et son intention `batir_dans_une_province`, soit une absence
    // qui nomme sa cause. Absente : Parcelle vaut -1 et IntentionJson null.
    public sealed class CasernePosee
    {
        public bool Presente { get; }
        public string Absence { get; }
        public long Parcelle { get; }
        public string IntentionJson { get; }

        private CasernePosee(bool presente, string absence, long parcelle, string intentionJson)
        {
            Presente = presente;
            Absence = absence;
            Parcelle = parcelle;
            IntentionJson = intentionJson;
        }

        internal static CasernePosee De(string maison, long cellId, long parcelle)
        {
            string json = "{\"type\":\"batir_dans_une_province\""
                + ",\"maison\":\"" + maison + "\""
                + ",\"cell\":" + cellId.ToString(CultureInfo.InvariantCulture)
                + ",\"nature\":\"" + PoseDeCaserne.Nature + "\""
                + ",\"parcelle\":" + parcelle.ToString(CultureInfo.InvariantCulture) + "}";
            return new CasernePosee(true, "", parcelle, json);
        }

        internal static CasernePosee Absente(string cause) => new CasernePosee(false, cause, -1, null);
    }

    // Le geste « pose la caserne » de la ville : un point désigné au sol, la maison du joueur, et la parcelle du plan
    // qui contient le point (`PoseDeBatiment.ParcelleSous`, la première dans l'ordre de la liste). La caserne est un
    // bâtiment de province (`sim/batiments.py`) : son prix, ses journées et ses bras sont ceux du monde, que la vue
    // ne calcule pas. Le monde reste le seul juge : parcelle en chantier, déjà bâtie ou promise, grenier, terres,
    // c'est son reçu qui le dit.
    public static class PoseDeCaserne
    {
        public const string Nature = "caserne";

        public static CasernePosee Calculer(PlanLu plan, PointLocal point, string maison)
        {
            if (plan == null) throw new ArgumentNullException(nameof(plan));
            if (!CleDeMaison(maison))
                return CasernePosee.Absente("maison mal formée : " + (maison == null ? "null" : "\"" + maison + "\""));
            if (double.IsNaN(point.X) || double.IsInfinity(point.X) || double.IsNaN(point.Y) || double.IsInfinity(point.Y))
                return CasernePosee.Absente("point non fini");
            if (plan.Parcelles.Count == 0) return CasernePosee.Absente("aucune parcelle au plan");

            var sous = PoseDeBatiment.ParcelleSous(plan, point);
            if (sous == null)
                return CasernePosee.Absente("aucune parcelle sous le point : ("
                    + point.X.ToString("R", CultureInfo.InvariantCulture) + ", " + point.Y.ToString("R", CultureInfo.InvariantCulture) + ")");
            return CasernePosee.De(maison, plan.CellId, sous.Identifiant);
        }

        // Une clé du registre des maisons (`seigneurie-6`, `grande-3`…) : minuscules, chiffres et tirets.
        // Elle s'écrit telle quelle dans le JSON, sans échappement à deviner.
        private static bool CleDeMaison(string maison)
        {
            if (string.IsNullOrEmpty(maison)) return false;
            foreach (char c in maison)
                if (!(c >= 'a' && c <= 'z') && !(c >= '0' && c <= '9') && c != '-') return false;
            return true;
        }
    }
}
