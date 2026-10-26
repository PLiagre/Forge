using System;
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;

namespace Forge.Pont.Tests
{
    // Lot #787 — chaque métier va vers ses destinations déclarées, sur une seule rue servie, sans raccourci ni sortie devinée.
    public sealed class TrajetsDesMetiersTests
    {
        private static List<PointLocal> L(params double[] xy) => Enumerable.Range(0, xy.Length / 2).Select(i => new PointLocal(xy[2 * i], xy[2 * i + 1])).ToList();
        private static List<PointLocal> Carre(double x, double y) => L(x - 1, y - 1, x + 1, y - 1, x + 1, y + 1, x - 1, y + 1);
        private static RueDuPlan Geste(long id, bool chantier, long? porte, params double[] xy) => new RueDuPlan(id, L(xy), 4, chantier, porte);
        private static RueDeBase Base(long? vers, params double[] xy) => new RueDeBase(L(xy), 6, "grande", vers);
        private static BatimentDuPlan Bat(long id, string nature, bool chantier, double x, double y) => new BatimentDuPlan(id, 1, nature, Carre(x, y), chantier, 10, chantier ? 5 : 10);
        private static ChantierDuJour C(string nature, long id, long bras) => new ChantierDuJour(nature, id, bras, bras, bras == 0 ? "aucun bras" : null);
        private static LecturePlan Plan(RueDeBase[] @base, RueDuPlan[] rues, BatimentDuPlan[] bats, ChantierDuJour[] releve = null, ParcelleDuPlan[] parcelles = null, long tick = 3) =>
            LecturePlan.De(new PlanLu(1000, tick, rues ?? new RueDuPlan[0], parcelles ?? new ParcelleDuPlan[0], bats ?? new BatimentDuPlan[0],
                @base == null ? null : new BaseDuPlan(L(0, 0, 1, 0, 1, 1), @base, new MaisonDeBase[0]), releve));
        // Le premier trajet des artisans vers un four achevé centré en (x, y).
        private static TrajetDuMetier Atelier(RueDeBase[] @base, RueDuPlan[] rues, double x, double y) =>
            TrajetsDesMetiers.Calculer(Plan(@base, rues, new[] { Bat(1, "four", false, x, y) }), "artisans").Trajets[0];

        private static void Trajet(TrajetDuMetier t, string destination, string rue, params double[] xy)
        {
            Assert.AreEqual(destination + " par " + rue + " ", t.Destination + " par " + t.Rue + " " + t.Absence);
            Assert.AreEqual(string.Join(" ", xy), string.Join(" ", t.Points.Select(p => Math.Round(p.X, 9) + " " + Math.Round(p.Y, 9))), destination);
        }
        private static void Absent(TrajetDuMetier t, string destination, string rue, string cause)
        {
            Assert.AreEqual(destination + " par " + rue, t.Destination + " par " + t.Rue);
            Assert.IsTrue(t.Points == null && t.Absence != null && t.Absence.Contains(cause), t.Absence);
        }
        private static TrajetsDesMetiers Aucun(LecturePlan lecture, string metier, string cause)
        {
            var r = TrajetsDesMetiers.Calculer(lecture, metier);
            Assert.IsTrue(r.Trajets.Count == 0 && r.Absence != null && r.Absence.Contains(cause), r.Absence);
            return r;
        }

        [Test]
        public void ChaqueMetierGardeSesDestinations()
        {
            var bases = new[] { Base(55, 0, 0, 20, 0), Base(null, 0, -5, 0, -20) };
            var rues = new[] { Geste(8, true, 9, 0, 5, -10, 5, -10, 15), Geste(7, false, 0, 20, 0, 20, 20) };
            var bats = new[] { Bat(7, "scierie", false, 10, 3), Bat(4, "four", false, 22, 15), Bat(5, "maison", false, 5, 1), Bat(6, "scierie", true, 1, 1) };
            var releve = new[] { C("rue", 7, 1), C("parcelle", 7, 2), C("batiment", 7, 1), C("rue", 8, 3), C("batiment", 6, 0), C("batiment", 99, 2) };
            var parcelles = new[] { new ParcelleDuPlan(7, Carre(5, -3), false, 0, 0), new ParcelleDuPlan(1, Carre(1, 1), false, 0, 0) };
            var o = TrajetsDesMetiers.Calculer(Plan(bases, rues, bats, releve, parcelles), "ouvriers");
            Assert.AreEqual(5, o.Trajets.Count, o.Absence);
            Trajet(o.Trajets[0], "batiment 7", "base 0", 0, 0, 10, 0);
            Absent(o.Trajets[1], "batiment 99", null, "introuvable");
            Trajet(o.Trajets[2], "parcelle 7", "base 0", 0, 0, 5, 0);
            Trajet(o.Trajets[3], "rue 7", "rue 7", 20, 0, 20, 20);
            Trajet(o.Trajets[4], "rue 8", "rue 8", 0, 5, -10, 5, -10, 15);
            // Seules les sorties déclarées : ni la rue de base sans débouché, ni la rue de geste en chantier portant une porte.
            var p = TrajetsDesMetiers.Calculer(Plan(bases, rues, bats), "paysans");
            Assert.AreEqual(2, p.Trajets.Count);
            Trajet(p.Trajets[0], "base 0", "base 0", 0, 0, 20, 0);
            Trajet(p.Trajets[1], "rue 7", "rue 7", 20, 0, 20, 20);
            var a = TrajetsDesMetiers.Calculer(Plan(bases, rues, bats), "artisans");
            Assert.AreEqual(2, a.Trajets.Count);
            Trajet(a.Trajets[0], "batiment 4", "rue 7", 20, 0, 20, 15);
            Trajet(a.Trajets[1], "batiment 7", "base 0", 0, 0, 10, 0);
            // Relevé absent et relevé vide se distinguent.
            Aucun(Plan(bases, rues, bats), "ouvriers", "relevé du jour absent : relevé du jour non fourni");
            Aucun(Plan(bases, rues, bats, new ChantierDuJour[0]), "ouvriers", "aucun chantier employant des bras");
        }

        [Test]
        public void AucunRaccourciNiSortieDevinee()
        {
            var coude = new[] { Base(null, 0, 0, 10, 0, 10, 10) };
            Trajet(Atelier(coude, null, 12, 7), "batiment 1", "base 0", 0, 0, 10, 0, 10, 7);
            Trajet(Atelier(coude, null, 15, 15), "batiment 1", "base 0", 0, 0, 10, 0, 10, 10);
            // Projection sur le départ : préfixe nul, la rue est parcourue à rebours jusqu'à elle.
            Trajet(Atelier(coude, null, -3, -1), "batiment 1", "base 0", 10, 10, 10, 0, 0, 0);
            Trajet(Atelier(null, new[] { Geste(2, false, null, 0, 0, 0, 0, 10, 0, 10, 0, 10, 10) }, 12, 7), "batiment 1", "rue 2", 0, 0, 10, 0, 10, 7);
            var point = new[] { Geste(2, true, 4, 3, 3, 3, 3), Geste(3, false, null, 3, 3, 3, 3) };
            Absent(Atelier(null, point, 12, 7), "batiment 1", null, "inaccessible");
            Absent(TrajetsDesMetiers.Calculer(Plan(null, point, null, new[] { C("rue", 2, 1) }), "ouvriers").Trajets[0], "rue 2", "rue 2", "inaccessible");
            Aucun(Plan(new[] { Base(null, 0, 0, 0, -50) }, new[] { Geste(2, true, 4, 0, 0, 50, 0) }, null), "paysans", "aucun débouché");
        }

        [Test]
        public void BaseGestesEtAbsencesSontIndependants()
        {
            var bas = new[] { Base(null, 0, 0, 10, 0) };
            var haut = new[] { Geste(5, false, null, 0, 10, 10, 10) };
            Trajet(Atelier(bas, haut, 5, 3), "batiment 1", "base 0", 0, 0, 5, 0);
            Trajet(Atelier(bas, haut, 5, 7), "batiment 1", "rue 5", 0, 10, 5, 10);
            Trajet(Atelier(bas, haut, 5, 5), "batiment 1", "base 0", 0, 0, 5, 0);
            Trajet(Atelier(null, haut, 5, 3), "batiment 1", "rue 5", 0, 10, 5, 10);
            Trajet(Atelier(null, new[] { Geste(9, false, null, 0, 0, 10, 0), Geste(4, false, null, 0, 10, 10, 10) }, 5, 5), "batiment 1", "rue 4", 0, 10, 5, 10);
            Absent(Atelier(null, null, 5, 3), "batiment 1", null, "inaccessible");
            Aucun(Plan(bas, haut, new[] { Bat(1, "maison", false, 5, 3), Bat(2, "four", true, 5, 3) }), "artisans", "aucun atelier achevé");
            Absent(TrajetsDesMetiers.Calculer(Plan(bas, haut, null, new[] { C("parcelle", 3, 2) }), "ouvriers").Trajets[0], "parcelle 3", null, "introuvable");
        }

        [Test]
        public void LesResultatsSontRecalculesSansMemoire()
        {
            var bas = new[] { Base(null, 0, 0, 10, 0) };
            var deplace = new[] { Bat(1, "four", false, 8, 3) };
            var premier = TrajetsDesMetiers.Calculer(Plan(bas, null, new[] { Bat(1, "four", false, 5, 3) }, new[] { C("batiment", 1, 2) }), "ouvriers");
            var second = TrajetsDesMetiers.Calculer(Plan(bas, null, deplace, new[] { C("batiment", 1, 0) }, tick: 4), "artisans");
            var retires = Aucun(Plan(bas, null, deplace, new[] { C("batiment", 1, 0) }, tick: 4), "ouvriers", "aucun chantier employant des bras");
            var absente = Aucun(LecturePlan.Absent("service absent sur 127.0.0.1:8000"), "artisans", "service absent");
            Assert.IsTrue(absente.CellId == null && absente.Tick == null);
            var valide = TrajetsDesMetiers.Calculer(Plan(bas, null, deplace, tick: 5), "artisans");
            Trajet(valide.Trajets[0], "batiment 1", "base 0", 0, 0, 8, 0);
            Trajet(second.Trajets[0], "batiment 1", "base 0", 0, 0, 8, 0);
            Assert.AreEqual("3 4 4 5 1000", premier.Tick + " " + second.Tick + " " + retires.Tick + " " + valide.Tick + " " + second.CellId);
            Assert.AreEqual(1000, Aucun(Plan(bas, null, null), "mineurs", "mineurs").CellId);
            Aucun(Plan(bas, null, null), null, "aucune destination");
            Aucun(null, "artisans", "lecture nulle");
            Assert.Throws<NotSupportedException>(() => ((IList<TrajetDuMetier>)premier.Trajets).Clear());
            Assert.Throws<NotSupportedException>(() => ((IList<PointLocal>)premier.Trajets[0].Points)[1] = new PointLocal(9, 9));
            Trajet(premier.Trajets[0], "batiment 1", "base 0", 0, 0, 5, 0);
        }
    }
}
