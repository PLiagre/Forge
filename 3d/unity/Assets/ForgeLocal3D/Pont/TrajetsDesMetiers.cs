using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;

namespace Forge.Pont
{
    // Un trajet de vue vers une destination : soit des points sur une seule rue servie, soit l'absence nommée.
    // Références locales à cette lecture : « base 2 » est un rang dans la base, « rue 7 », « parcelle 7 », « batiment 7 » des identifiants.
    public sealed class TrajetDuMetier
    {
        public string Destination { get; }
        public string Rue { get; } // null : aucune rue retenue.
        public IReadOnlyList<PointLocal> Points { get; } // null : `Absence` nomme la cause.
        public string Absence { get; }

        internal TrajetDuMetier(string destination, string rue, List<PointLocal> points, string absence)
        { Destination = destination; Rue = rue; Points = points == null ? null : new ReadOnlyCollection<PointLocal>(points); Absence = absence; }
    }

    // Où vont les gens d'un métier dans le plan lu : un calcul de vue, sans mémoire, sans rien écrire dans le monde.
    // Un trajet suit une seule polyligne servie et s'arrête sur la rue : ni chemin entre rues, ni entrée de bâtiment.
    public sealed class TrajetsDesMetiers
    {
        public long? CellId { get; }
        public long? Tick { get; }
        public IReadOnlyList<TrajetDuMetier> Trajets { get; }
        public string Absence { get; } // null quand au moins une destination est déclarée, accessible ou non.

        private TrajetsDesMetiers(PlanLu plan, List<TrajetDuMetier> trajets, string absence)
        { CellId = plan?.CellId; Tick = plan?.Tick; Trajets = new ReadOnlyCollection<TrajetDuMetier>(trajets); Absence = absence; }

        public static TrajetsDesMetiers Calculer(LecturePlan lecture, string metier)
        {
            if (lecture?.Presente != true)
                return new TrajetsDesMetiers(null, new List<TrajetDuMetier>(), lecture == null ? "lecture nulle" : "plan absent : " + lecture.Absence);
            PlanLu plan = lecture.Plan;
            IReadOnlyList<RueDeBase> bases = plan.Base?.Rues ?? new RueDeBase[0];
            var trajets = new List<(string Nature, long Id, TrajetDuMetier Trajet)>();
            // Rues pour approcher parcelles et bâtiments, dans l'ordre de départage : la base par rang, puis les gestes achevés par identifiant.
            var servies = new List<(string Ref, List<PointLocal> Points)>();
            for (int i = 0; i < bases.Count; i++) servies.Add(("base " + i, Nettes(bases[i].Points)));
            foreach (RueDuPlan rue in plan.Rues.Where(r => !r.EnChantier).OrderBy(r => r.Identifiant))
                servies.Add(("rue " + rue.Identifiant, Nettes(rue.Points)));
            string absence = null;
            switch (metier)
            {
                case "ouvriers":
                    // Les bras du jour décident, jamais `EnChantier` : un achèvement de ce jour reste une destination.
                    if (plan.ChantiersDuJour == null) { absence = "relevé du jour absent : " + plan.AbsenceDesChantiersDuJour; break; }
                    foreach (ChantierDuJour c in plan.ChantiersDuJour.Where(c => c.Bras > 0))
                    {
                        string reference = c.Nature + " " + c.Identifiant;
                        RueDuPlan rue = c.Nature == "rue" ? plan.Rues.FirstOrDefault(r => r.Identifiant == c.Identifiant) : null;
                        IReadOnlyList<PointLocal> contour = c.Nature == "parcelle" ? plan.Parcelles.FirstOrDefault(p => p.Identifiant == c.Identifiant)?.Contour
                            : c.Nature == "batiment" ? plan.Batiments.FirstOrDefault(b => b.Identifiant == c.Identifiant)?.Emprise : null;
                        trajets.Add((c.Nature, c.Identifiant, rue != null ? Parcourir(reference, rue.Points)
                            : contour != null ? Approcher(reference, contour, servies)
                            : new TrajetDuMetier(reference, null, null, reference + " introuvable dans le plan du tick " + plan.Tick)));
                    }
                    if (trajets.Count == 0) absence = "aucun chantier employant des bras dans le relevé du jour";
                    break;
                case "paysans":
                    // Les débouchés déclarés seulement : jamais une sortie déduite de l'orientation ou de la sorte d'une rue.
                    for (int i = 0; i < bases.Count; i++)
                        if (bases[i].VersCellId != null) trajets.Add(("base", i, Parcourir("base " + i, bases[i].Points)));
                    foreach (RueDuPlan rue in plan.Rues.Where(r => !r.EnChantier && r.PorteCellId != null))
                        trajets.Add(("rue", rue.Identifiant, Parcourir("rue " + rue.Identifiant, rue.Points)));
                    if (trajets.Count == 0) absence = "aucun débouché déclaré dans le plan";
                    break;
                case "artisans":
                    // Des ateliers possibles, sans dire combien d'artisans y travaillent.
                    foreach (BatimentDuPlan b in plan.Batiments.Where(b => !b.EnChantier && (b.Nature == "scierie" || b.Nature == "four")))
                        trajets.Add(("batiment", b.Identifiant, Approcher("batiment " + b.Identifiant, b.Emprise, servies)));
                    if (trajets.Count == 0) absence = "aucun atelier achevé (scierie ou four) dans le plan";
                    break;
                default:
                    absence = "aucune destination déclarée pour le métier " + (metier ?? "null");
                    break;
            }
            return new TrajetsDesMetiers(plan, trajets.OrderBy(t => t.Nature, StringComparer.Ordinal).ThenBy(t => t.Id).Select(t => t.Trajet).ToList(), absence);
        }

        // Une rue parcourue en entier, dans l'ordre de ses points : débouché ou chantier de rue.
        private static TrajetDuMetier Parcourir(string reference, IReadOnlyList<PointLocal> points) => Nettes(points) is var nettes && nettes.Count > 1
            ? new TrajetDuMetier(reference, reference, nettes, null) : new TrajetDuMetier(reference, reference, null, reference + " inaccessible : rue de longueur nulle");

        // Depuis le début de la rue la plus proche de la moyenne des sommets, jusqu'à la projection, virages compris.
        private static TrajetDuMetier Approcher(string reference, IReadOnlyList<PointLocal> contour, List<(string Ref, List<PointLocal> Points)> servies)
        {
            var cible = new PointLocal(contour.Average(p => p.X), contour.Average(p => p.Y));
            (string Rue, List<PointLocal> Points, int Rang, PointLocal Projete)? meilleur = null;
            double plusCourte = double.PositiveInfinity;
            foreach (var (rue, points) in servies)
                for (int k = 0; k + 1 < points.Count; k++)
                {
                    PointLocal a = points[k], b = points[k + 1];
                    double dx = b.X - a.X, dy = b.Y - a.Y, t = ((cible.X - a.X) * dx + (cible.Y - a.Y) * dy) / (dx * dx + dy * dy);
                    PointLocal p = t <= 0 ? a : t >= 1 ? b : new PointLocal(a.X + t * dx, a.Y + t * dy);
                    double d = (p.X - cible.X) * (p.X - cible.X) + (p.Y - cible.Y) * (p.Y - cible.Y);
                    // Strictement plus proche : à égalité, le premier dans l'ordre source, rue, segment l'emporte.
                    if (d < plusCourte) { plusCourte = d; meilleur = (rue, points, k, p); }
                }
            if (meilleur == null) return new TrajetDuMetier(reference, null, null, reference + " inaccessible : aucune rue servie de longueur positive");
            var (retenue, nettes, rang, projete) = meilleur.Value;
            List<PointLocal> chemin = nettes.Take(rang + 1).ToList();
            if (!Egaux(projete, chemin[rang])) chemin.Add(projete);
            // Préfixe nul : la projection est le départ, la rue se parcourt à rebours depuis sa fin.
            if (chemin.Count < 2) chemin = Enumerable.Reverse(nettes).ToList();
            return new TrajetDuMetier(reference, retenue, chemin, null);
        }

        // Les points sans leurs segments de longueur nulle.
        private static List<PointLocal> Nettes(IReadOnlyList<PointLocal> points) => points.Where((p, i) => i == 0 || !Egaux(points[i - 1], p)).ToList();
        private static bool Egaux(PointLocal a, PointLocal b) => a.X == b.X && a.Y == b.Y;
    }
}
