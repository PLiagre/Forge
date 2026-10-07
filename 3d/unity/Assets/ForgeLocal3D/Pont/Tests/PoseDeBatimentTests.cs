using System;
using System.Collections.Generic;
using NUnit.Framework;

namespace Forge.Pont.Tests
{
    // Lot #376 — un point posé au sol et une nature donnent la parcelle sous le point et l'intention
    // `poser_batiment`, ou une absence déclarée. P0, P1 et P2 sont les trois contours d'exemple de MODELE.
    public sealed class PoseDeBatimentTests
    {
        private static List<PointLocal> Contour(params (double, double)[] points)
        {
            var liste = new List<PointLocal>();
            foreach (var (x, y) in points) liste.Add(new PointLocal(x, y));
            return liste;
        }

        private static RueDuPlan R0() => new RueDuPlan(0, Contour((0, 0), (40, 0), (40, 25)), 4, false);

        private static ParcelleDuPlan P0() => new ParcelleDuPlan(0, Contour((5, 2), (15, 2), (15, 22), (5, 22)), true, 0, 0);
        private static List<PointLocal> ContourP1() => Contour((5, -2), (15, -2), (15, -22), (5, -22));
        private static ParcelleDuPlan P1() => new ParcelleDuPlan(1, ContourP1(), false, 0, 0);
        private static ParcelleDuPlan P2() => new ParcelleDuPlan(2, Contour((38, 0), (38, 25), (28, 25), (28, 0)), false, 0, 0);
        private static ParcelleDuPlan P4() => new ParcelleDuPlan(4,
            Contour((50, 0), (70, 0), (70, 20), (65, 20), (65, 5), (55, 5), (55, 20), (50, 20)), false, 0, 0);
        private static ParcelleDuPlan P5() => new ParcelleDuPlan(5, Contour((10, 10), (20, 10), (20, 20), (10, 20)), false, 0, 0);
        private static ParcelleDuPlan P6() => new ParcelleDuPlan(6, Contour((30, 40), (40, 50), (30, 60), (20, 50)), false, 0, 0);

        // Un plan de cellule 7, tick 0, avec la rue R0.
        private static PlanLu Plan(List<BatimentDuPlan> batiments, params ParcelleDuPlan[] parcelles) =>
            new PlanLu(7, 0, new List<RueDuPlan> { R0() }, parcelles, batiments);

        private static PlanLu B() => Plan(
            new List<BatimentDuPlan> { new BatimentDuPlan(0, 1, "maison", ContourP1(), false, 0, 0) },
            P0(), P1(), P2(), P4(), P6());

        private static PlanLu PlanNomme(string nom)
        {
            switch (nom)
            {
                case "B": return B();
                case "P5, P0": return Plan(new List<BatimentDuPlan>(), P5(), P0());
                case "P0, P5": return Plan(new List<BatimentDuPlan>(), P0(), P5());
                case "R0 seule": return Plan(new List<BatimentDuPlan>());
                case "contour de deux points":
                    return Plan(new List<BatimentDuPlan>(), new ParcelleDuPlan(3, Contour((0, 0), (40, 0)), false, 0, 0));
                default: throw new ArgumentException("plan inconnu : " + nom);
            }
        }

        // ---- Les poses présentes ---------------------------------------------------------------

        [TestCase("B", 10, 12, "maison", 0, TestName = "Cas01_MaisonSurP0EnChantier")]
        [TestCase("B", 10, -12, "scierie", 1, TestName = "Cas02_P1BatieLePontNeLitPasLesBatiments")]
        [TestCase("B", 33, 12, "four", 2, TestName = "Cas03_FourSurP2")]
        [TestCase("B", 52, 10, "maison", 4, TestName = "Cas04_BrasGaucheDuU")]
        [TestCase("B", 68, 15, "maison", 4, TestName = "Cas05_BrasDroitDuU")]
        [TestCase("B", 60, 2, "maison", 4, TestName = "Cas06_BaseDuU")]
        [TestCase("B", 30, 50, "maison", 6, TestName = "Cas08_CentreDuLosange")]
        [TestCase("P5, P0", 12, 12, "maison", 5, TestName = "Cas11_LaPremiereDeLaListeGagneP5")]
        [TestCase("P0, P5", 12, 12, "maison", 0, TestName = "Cas12_LaPremiereDeLaListeGagneP0")]
        public void LaPoseEstCalculee(string plan, double x, double y, string nature, long parcelle)
        {
            var pose = PoseDeBatiment.Calculer(PlanNomme(plan), new PointLocal(x, y), nature);
            Assert.That(pose.Presente, Is.True, pose.Absence);
            Assert.That(pose.Absence, Is.EqualTo(""));
            Assert.That(pose.Parcelle, Is.EqualTo(parcelle));
            Assert.That(pose.Nature, Is.EqualTo(nature));
            Assert.That(pose.IntentionJson, Is.Not.Null);
            StringAssert.DoesNotContain("foyers", pose.IntentionJson);
        }

        // ---- Les trois intentions exactes des exemples de MODELE -------------------------------

        [TestCase(10, 12, "maison", "{\"type\":\"poser_batiment\",\"cell\":7,\"parcelle\":0,\"nature\":\"maison\"}",
            TestName = "Intention01_MaisonSurP0")]
        [TestCase(10, -12, "scierie", "{\"type\":\"poser_batiment\",\"cell\":7,\"parcelle\":1,\"nature\":\"scierie\"}",
            TestName = "Intention02_ScierieSurP1")]
        [TestCase(33, 12, "four", "{\"type\":\"poser_batiment\",\"cell\":7,\"parcelle\":2,\"nature\":\"four\"}",
            TestName = "Intention03_FourSurP2")]
        public void LIntentionEstCelleDuModele(double x, double y, string nature, string attendu)
        {
            var pose = PoseDeBatiment.Calculer(B(), new PointLocal(x, y), nature);
            Assert.That(pose.Presente, Is.True, pose.Absence);
            Assert.That(pose.Absence, Is.EqualTo(""));
            Assert.That(pose.Nature, Is.EqualTo(nature));
            Assert.That(pose.IntentionJson, Is.EqualTo(attendu));
            StringAssert.DoesNotContain("foyers", pose.IntentionJson);
        }

        // ---- Les refus -------------------------------------------------------------------------

        [TestCase("B", 60, 10, "maison", "aucune parcelle sous le point", false, TestName = "Cas07_CreuxDuU")]
        [TestCase("B", 22, 42, "maison", "aucune parcelle sous le point", false, TestName = "Cas09_CadreDuLosangeHorsDeLui")]
        [TestCase("B", 0, 30, "maison", "aucune parcelle sous le point : (0, 30)", true, TestName = "Cas10_MessageExact")]
        [TestCase("R0 seule", 10, 12, "maison", "aucune parcelle au plan", false, TestName = "Cas13_AucuneParcelleAuPlan")]
        [TestCase("contour de deux points", 10, 0, "maison", "aucune parcelle sous le point", false, TestName = "Cas14_ContourDeDeuxPoints")]
        [TestCase("B", 10, 12, "Maison", "nature inconnue : \"Maison\"", true, TestName = "Cas15_CasseNonToleree")]
        [TestCase("B", 10, 12, " four", "nature inconnue : \" four\"", true, TestName = "Cas16_EspaceNonTolere")]
        [TestCase("B", 10, 12, "", "nature inconnue : \"\"", true, TestName = "Cas17_NatureVide")]
        [TestCase("B", 10, 12, "atelier", "nature inconnue : \"atelier\"", true, TestName = "Cas18_NatureHorsListe")]
        [TestCase("B", 10, 12, null, "nature inconnue : null", true, TestName = "Cas19_NatureNulle")]
        [TestCase("B", 0, 30, "Maison", "nature inconnue : \"Maison\"", true, TestName = "Cas20_LaNatureDAbord")]
        [TestCase("B", double.NaN, 12, "maison", "point non fini", false, TestName = "Cas21_XNaN")]
        [TestCase("B", 10, double.NegativeInfinity, "maison", "point non fini", false, TestName = "Cas22_YMoinsInfini")]
        public void LaPoseEstRefuseeAvecSaCause(string plan, double x, double y, string nature, string cause, bool exacte)
        {
            var pose = PoseDeBatiment.Calculer(PlanNomme(plan), new PointLocal(x, y), nature);
            Assert.That(pose.Presente, Is.False);
            if (exacte) Assert.That(pose.Absence, Is.EqualTo(cause));
            else StringAssert.StartsWith(cause, pose.Absence);
            Assert.That(pose.Parcelle, Is.EqualTo(-1));
            Assert.That(pose.Nature, Is.EqualTo(""));
            Assert.That(pose.IntentionJson, Is.Null);
        }

        // ---- La parcelle sous le point ---------------------------------------------------------

        [Test]
        public void LaParcelleSousLePointEstLaMemeInstance()
        {
            var plan = B();
            Assert.That(PoseDeBatiment.ParcelleSous(plan, new PointLocal(10, 12)), Is.SameAs(plan.Parcelles[0]));
        }

        [TestCase(60, 10, TestName = "ParcelleSous_CreuxDuU")]
        [TestCase(double.NaN, 12, TestName = "ParcelleSous_PointNaN")]
        public void AucuneParcelleSousLePoint(double x, double y)
        {
            Assert.That(PoseDeBatiment.ParcelleSous(B(), new PointLocal(x, y)), Is.Null);
        }

        // ---- Les nuls et la liste des natures --------------------------------------------------

        [Test]
        public void UnContourNulLeve()
        {
            Assert.Throws<ArgumentNullException>(() => PoseDeBatiment.Contient(null, new PointLocal(10, 12)));
        }

        [Test]
        public void UnPlanNulLeveAuCalcul()
        {
            Assert.Throws<ArgumentNullException>(() => PoseDeBatiment.Calculer(null, new PointLocal(10, 12), "maison"));
        }

        [Test]
        public void UnPlanNulLeveALaRecherche()
        {
            Assert.Throws<ArgumentNullException>(() => PoseDeBatiment.ParcelleSous(null, new PointLocal(10, 12)));
        }

        [Test]
        public void LesNaturesSontCellesDuMonde()
        {
            Assert.That(PoseDeBatiment.Natures, Is.EqualTo(new[] { "maison", "scierie", "four" }));
        }
    }
}
