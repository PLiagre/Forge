using System;
using System.Collections.Generic;
using NUnit.Framework;

namespace Forge.Pont.Tests
{
    // Lot #374 — deux points posés au sol donnent la parcelle tracée le long d'une rue et son intention
    // `decouper_parcelle`, ou une absence déclarée. La rue R0 est celle des exemples de MODELE.
    public sealed class TraceDeParcelleTests
    {
        private const double Tolerance = 1e-9;

        private static RueDuPlan Rue(long identifiant, double largeurM, bool enChantier, params (double, double)[] points)
        {
            var liste = new List<PointLocal>();
            foreach (var (x, y) in points) liste.Add(new PointLocal(x, y));
            return new RueDuPlan(identifiant, liste, largeurM, enChantier);
        }

        private static RueDuPlan R0(bool enChantier = false) => Rue(0, 4, enChantier, (0, 0), (40, 0), (40, 25));

        // Un plan de cellule 7, tick 0, sans parcelle ni bâtiment.
        private static PlanLu Plan(params RueDuPlan[] rues) =>
            new PlanLu(7, 0, rues, new List<ParcelleDuPlan>(), new List<BatimentDuPlan>());

        private static PlanLu PlanNomme(string nom)
        {
            switch (nom)
            {
                case "R0": return Plan(R0());
                case "R0 en chantier": return Plan(R0(enChantier: true));
                case "R0 + R5": return Plan(R0(), Rue(5, 6, false, (0, 50), (40, 50)));
                case "vide": return Plan();
                case "segment nul": return Plan(Rue(2, 4, false, (3, 3), (3, 3)));
                default: throw new ArgumentException("plan inconnu : " + nom);
            }
        }

        // ---- Les parcelles présentes (cas 1 à 8) -------------------------------------------------

        [TestCase("R0", 5, 3, 15, 22, 0, 0, 5, 10, 20, "gauche", TestName = "Cas01_ExempleGaucheDuModele")]
        [TestCase("R0", 15, 1, 5, 22, 0, 0, 5, 10, 20, "gauche", TestName = "Cas02_OrdreInverseLeLongDeLaRue")]
        [TestCase("R0", 5, -3, 15, -22, 0, 0, 5, 10, 20, "droite", TestName = "Cas03_ExempleDroitDuModele")]
        [TestCase("R0", 39, 25, 28, 0, 0, 1, 0, 25, 10, "gauche", TestName = "Cas04_ExempleDuSegmentUn")]
        [TestCase("R0", 40, 0, 30, 15, 0, 0, 30, 10, 13, "gauche", TestName = "Cas05_EgaliteDesSegmentsLePremierGagne")]
        [TestCase("R0 en chantier", 5, 3, 15, 22, 0, 0, 5, 10, 20, "gauche", TestName = "Cas06_UneRueEnChantierCompte")]
        [TestCase("R0 + R5", 10, 47, 20, 30, 5, 0, 10, 10, 17, "droite", TestName = "Cas07_LaRueLaPlusProcheGagne")]
        [TestCase("R0", 5, 10, 15, 22, 0, 0, 5, 10, 20, "gauche", TestName = "Cas08_DixMetresPileSontAcceptes")]
        public void LaParcelleTraceeEstCalculee(string plan, double x1, double y1, double x2, double y2,
            long rue, int segment, double debutM, double facadeM, double profondeurM, string cote)
        {
            var parcelle = TraceDeParcelle.Calculer(PlanNomme(plan), new PointLocal(x1, y1), new PointLocal(x2, y2));
            Assert.That(parcelle.Presente, Is.True, parcelle.Absence);
            Assert.That(parcelle.Absence, Is.EqualTo(""));
            Assert.That(parcelle.Rue, Is.EqualTo(rue));
            Assert.That(parcelle.Segment, Is.EqualTo(segment));
            Assert.That(parcelle.DebutM, Is.EqualTo(debutM).Within(Tolerance));
            Assert.That(parcelle.FacadeM, Is.EqualTo(facadeM).Within(Tolerance));
            Assert.That(parcelle.ProfondeurM, Is.EqualTo(profondeurM).Within(Tolerance));
            Assert.That(parcelle.Cote, Is.EqualTo(cote));
            Assert.That(parcelle.IntentionJson, Is.Not.Null);
            StringAssert.DoesNotContain("foyers", parcelle.IntentionJson);
        }

        // ---- Les trois intentions exactes des exemples de MODELE ---------------------------------

        [TestCase(5, 3, 15, 22,
            "{\"type\":\"decouper_parcelle\",\"cell\":7,\"rue\":0,\"segment\":0,\"debut_m\":5,\"facade_m\":10,\"profondeur_m\":20,\"cote\":\"gauche\"}",
            TestName = "Intention01_ExempleGauche")]
        [TestCase(5, -3, 15, -22,
            "{\"type\":\"decouper_parcelle\",\"cell\":7,\"rue\":0,\"segment\":0,\"debut_m\":5,\"facade_m\":10,\"profondeur_m\":20,\"cote\":\"droite\"}",
            TestName = "Intention03_ExempleDroit")]
        [TestCase(39, 25, 28, 0,
            "{\"type\":\"decouper_parcelle\",\"cell\":7,\"rue\":0,\"segment\":1,\"debut_m\":0,\"facade_m\":25,\"profondeur_m\":10,\"cote\":\"gauche\"}",
            TestName = "Intention04_ExempleDuSegmentUn")]
        public void LIntentionEstCelleDuModele(double x1, double y1, double x2, double y2, string attendu)
        {
            var parcelle = TraceDeParcelle.Calculer(PlanNomme("R0"), new PointLocal(x1, y1), new PointLocal(x2, y2));
            Assert.That(parcelle.Presente, Is.True, parcelle.Absence);
            Assert.That(parcelle.Absence, Is.EqualTo(""));
            Assert.That(parcelle.IntentionJson, Is.EqualTo(attendu));
            StringAssert.DoesNotContain("foyers", parcelle.IntentionJson);
        }

        // ---- Les refus (cas 9 à 19) --------------------------------------------------------------

        [TestCase("R0", 5, 10.01, 15, 22, "point trop loin d'une rue", TestName = "Cas09_UnPeuPlusDeDixMetres")]
        [TestCase("vide", 5, 3, 15, 22, "aucune rue au plan", TestName = "Cas10_PlanSansRue")]
        [TestCase("segment nul", 3, 3, 15, 22, "aucune rue au plan", TestName = "Cas11_SeulementUnSegmentNul")]
        [TestCase("R0", 5, 3, 45, 22, "façade dépasse le segment", TestName = "Cas12_FacadeAuDelaDuBout")]
        [TestCase("R0", -3, 1, 15, 22, "façade dépasse le segment", TestName = "Cas13_DebutNegatif")]
        [TestCase("R0", 5, 3, 5, 22, "façade nulle", TestName = "Cas14_FacadeNulle")]
        [TestCase("R0", 5, 3, 15, 1.5, "second point dans la chaussée", TestName = "Cas15_SecondPointDansLaChaussee")]
        [TestCase("R0", 5, 3, 15, 2, "second point dans la chaussée", TestName = "Cas16_ProfondeurNulle")]
        [TestCase("R0", double.NaN, 3, 15, 22, "point non fini", TestName = "Cas17_PremierPointNaN")]
        [TestCase("R0", 5, 3, 15, double.PositiveInfinity, "point non fini", TestName = "Cas18_SecondPointInfini")]
        [TestCase("R0", 60, 1, 70, 22, "point trop loin d'une rue", TestName = "Cas19_LoinDuSegmentBorne")]
        public void LeTraceEstRefuseAvecSaCause(string plan, double x1, double y1, double x2, double y2, string cause)
        {
            var parcelle = TraceDeParcelle.Calculer(PlanNomme(plan), new PointLocal(x1, y1), new PointLocal(x2, y2));
            Assert.That(parcelle.Presente, Is.False);
            StringAssert.StartsWith(cause, parcelle.Absence);
            Assert.That(parcelle.Rue, Is.EqualTo(-1));
            Assert.That(parcelle.Segment, Is.EqualTo(-1));
            Assert.That(double.IsNaN(parcelle.DebutM), Is.True);
            Assert.That(parcelle.Cote, Is.EqualTo(""));
            Assert.That(parcelle.IntentionJson, Is.Null);
        }

        [Test]
        public void UnPlanNulLeve()
        {
            Assert.Throws<ArgumentNullException>(() =>
                TraceDeParcelle.Calculer(null, new PointLocal(5, 3), new PointLocal(15, 22)));
        }
    }
}
