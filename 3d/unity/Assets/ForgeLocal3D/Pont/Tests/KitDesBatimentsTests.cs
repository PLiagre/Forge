using System;
using System.Collections.Generic;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using Object = UnityEngine.Object;

namespace Forge.Pont.Tests
{
    // Lot #368 — le kit du désert rend, pour chaque nature et chaque étape, sa pièce chargée hors de
    // l'éditeur, ou une absence déclarée ; l'étape suit le travail fourni ; la pose lit la façade sur `c0→c1`.
    public sealed class KitDesBatimentsTests
    {
        private const double Tolerance = 1e-9;

        private static BatimentDuPlan Batiment(bool enChantier, long requis, long fourni, params (double, double)[] emprise)
        {
            var points = new List<PointLocal>();
            foreach (var (x, y) in emprise) points.Add(new PointLocal(x, y));
            return new BatimentDuPlan(7, 0, "maison", points, enChantier, requis, fourni);
        }

        private static (double, double)[] Paires(double[] plat)
        {
            var paires = new (double, double)[plat.Length / 2];
            for (int i = 0; i < paires.Length; i++) paires[i] = (plat[2 * i], plat[2 * i + 1]);
            return paires;
        }

        // ---- Les pièces du kit -------------------------------------------------------------------

        [TestCase("maison", EtapeDuBatiment.Piquets, "chantier_maison_pise_0_piquets")]
        [TestCase("maison", EtapeDuBatiment.Murs, "chantier_maison_pise_0_murs")]
        [TestCase("maison", EtapeDuBatiment.Fini, "maison_pise_0")]
        [TestCase("scierie", EtapeDuBatiment.Piquets, "chantier_scierie_piquets")]
        [TestCase("scierie", EtapeDuBatiment.Murs, "chantier_scierie_murs")]
        [TestCase("scierie", EtapeDuBatiment.Fini, "scierie")]
        [TestCase("four", EtapeDuBatiment.Piquets, "chantier_four_pain_pise_piquets")]
        [TestCase("four", EtapeDuBatiment.Murs, "chantier_four_pain_pise_murs")]
        [TestCase("four", EtapeDuBatiment.Fini, "four_pain_pise")]
        public void LesNeufPiecesSeChargentHorsDeLEditeur(string nature, EtapeDuBatiment etape, string nom)
        {
            var kit = KitDesBatiments.Charger();
            Assert.That(kit, Is.Not.Null, "Resources.Load ne trouve pas " + KitDesBatiments.Ressource);
            var piece = kit.Piece(nature, etape);
            Assert.That(piece.Presente, Is.True, piece.Absence);
            Assert.That(piece.Absence, Is.EqualTo(""));
            Assert.That(piece.Prefab, Is.Not.Null);
            Assert.That(piece.Prefab.name, Is.EqualTo(nom));
            Assert.That(AssetDatabase.GetAssetPath(piece.Prefab),
                Is.EqualTo("Assets/ForgeLocal3D/Desert/Prefabs/" + nom + ".prefab"));
        }

        [TestCase("maison")]
        [TestCase("scierie")]
        [TestCase("four")]
        public void LesTroisPiecesDUneNatureSontDistinctes(string nature)
        {
            var kit = KitDesBatiments.Charger();
            Assert.That(kit, Is.Not.Null);
            var piquets = kit.Piece(nature, EtapeDuBatiment.Piquets).Prefab;
            var murs = kit.Piece(nature, EtapeDuBatiment.Murs).Prefab;
            var fini = kit.Piece(nature, EtapeDuBatiment.Fini).Prefab;
            Assert.That(piquets, Is.Not.Null);
            Assert.That(murs, Is.Not.Null);
            Assert.That(fini, Is.Not.Null);
            Assert.That(piquets, Is.Not.SameAs(murs));
            Assert.That(murs, Is.Not.SameAs(fini));
            Assert.That(piquets, Is.Not.SameAs(fini));
        }

        [Test, Combinatorial]
        public void UneNatureInconnueEstDeclareeAbsente(
            [Values("grenier", "Maison", "maison ", "", null)] string nature, [Values] EtapeDuBatiment etape)
        {
            var kit = KitDesBatiments.Charger();
            Assert.That(kit, Is.Not.Null);
            var piece = kit.Piece(nature, etape);
            Assert.That(piece.Presente, Is.False);
            Assert.That(piece.Prefab, Is.Null);
            Assert.That(piece.Absence, Does.Contain("nature sans pièce au kit"));
            if (nature != null) Assert.That(piece.Absence, Does.Contain(nature));
        }

        [Test]
        public void UnePieceManquanteEstDeclareeAbsenteSansEnChoisirUneAutre()
        {
            var kit = ScriptableObject.CreateInstance<KitDesBatiments>();
            var piquets = new GameObject("piquets");
            var fini = new GameObject("fini");
            try
            {
                kit.natures = new[]
                {
                    new KitDesBatiments.PiecesDUneNature { nature = "maison", piquets = piquets, murs = null, fini = fini },
                };
                var murs = kit.Piece("maison", EtapeDuBatiment.Murs);
                Assert.That(murs.Presente, Is.False);
                Assert.That(murs.Prefab, Is.Null);
                Assert.That(murs.Absence, Is.EqualTo("pièce manquante au kit : maison murs"));
                var present = kit.Piece("maison", EtapeDuBatiment.Piquets);
                Assert.That(present.Presente, Is.True);
                Assert.That(present.Prefab, Is.SameAs(piquets));
                Assert.That(present.Absence, Is.EqualTo(""));
            }
            finally
            {
                Object.DestroyImmediate(piquets);
                Object.DestroyImmediate(fini);
                Object.DestroyImmediate(kit);
            }
        }

        // ---- L'étape -----------------------------------------------------------------------------

        [TestCase(true, 300, 0, EtapeDuBatiment.Piquets)]
        [TestCase(true, 300, 149, EtapeDuBatiment.Piquets)]
        [TestCase(true, 300, 150, EtapeDuBatiment.Murs)]
        [TestCase(true, 300, 299, EtapeDuBatiment.Murs)]
        [TestCase(false, 300, 300, EtapeDuBatiment.Fini)]
        [TestCase(true, 1, 0, EtapeDuBatiment.Piquets)]
        [TestCase(true, 301, 150, EtapeDuBatiment.Piquets)]
        [TestCase(true, 301, 151, EtapeDuBatiment.Murs)]
        public void LEtapeSuitLeTravailFourni(bool enChantier, long requis, long fourni, EtapeDuBatiment attendue)
        {
            var b = Batiment(enChantier, requis, fourni, (5, 2), (15, 2), (15, 22), (5, 22));
            Assert.That(LectureDuBatiment.Etape(b), Is.EqualTo(attendue));
        }

        // ---- La pose -----------------------------------------------------------------------------

        // Les exemples de MODELE.md sur la rue [[0, 0], [40, 0], [40, 25]], largeur 4 m ; la quatrième ligne est
        // le segment 1 à droite, la cinquième le rectangle de la première commencé à un autre coin.
        [TestCase(new double[] { 5, 2, 15, 2, 15, 22, 5, 22 }, 10.0, 12.0, 0.0, -1.0, 0.0)]
        [TestCase(new double[] { 5, -2, 15, -2, 15, -22, 5, -22 }, 10.0, -12.0, 0.0, 1.0, 180.0)]
        [TestCase(new double[] { 38, 0, 38, 25, 28, 25, 28, 0 }, 33.0, 12.5, 1.0, 0.0, 270.0)]
        [TestCase(new double[] { 42, 0, 42, 25, 52, 25, 52, 0 }, 47.0, 12.5, -1.0, 0.0, 90.0)]
        [TestCase(new double[] { 15, 2, 15, 22, 5, 22, 5, 2 }, 10.0, 12.0, 1.0, 0.0, 270.0)]
        public void LaFacadeRegardeLaRue(double[] emprise, double cx, double cy, double fx, double fy, double lacet)
        {
            var pose = LectureDuBatiment.Poser(Batiment(false, 1, 1, Paires(emprise)));
            Assert.That(pose.Presente, Is.True, pose.Absence);
            Assert.That(pose.Absence, Is.EqualTo(""));
            Assert.That(pose.CentreX, Is.EqualTo(cx).Within(Tolerance));
            Assert.That(pose.CentreY, Is.EqualTo(cy).Within(Tolerance));
            Assert.That(pose.FacadeX, Is.EqualTo(fx).Within(Tolerance));
            Assert.That(pose.FacadeY, Is.EqualTo(fy).Within(Tolerance));
            Assert.That(pose.LacetDegres, Is.EqualTo(lacet).Within(Tolerance));
            Assert.That(pose.LacetDegres, Is.GreaterThanOrEqualTo(0.0).And.LessThan(360.0));
            double theta = pose.LacetDegres * Math.PI / 180;
            Assert.That(Math.Sin(theta), Is.EqualTo(-pose.FacadeX).Within(Tolerance));
            Assert.That(Math.Cos(theta), Is.EqualTo(-pose.FacadeY).Within(Tolerance));
        }

        [TestCase(new double[] { 5, 2, 15, 2 }, "emprise de 2 point(s)")]
        [TestCase(new double[] { 5, 2, 5, 2, 15, 22 }, "façade nulle")]
        [TestCase(new double[] { 0, 0, 10, 0, 20, 0 }, "emprise plate")]
        [TestCase(new double[] { 5, 2, 15, double.NaN, 15, 22, 5, 22 }, "point non fini")]
        public void UnePoseImpossibleEstDeclareeAbsente(double[] emprise, string cause)
        {
            var pose = LectureDuBatiment.Poser(Batiment(false, 1, 1, Paires(emprise)));
            Assert.That(pose.Presente, Is.False);
            Assert.That(pose.Absence, Does.Contain("bâtiment 7"));
            Assert.That(pose.Absence, Does.Contain(cause));
            Assert.That(pose.CentreX, Is.NaN);
            Assert.That(pose.CentreY, Is.NaN);
            Assert.That(pose.FacadeX, Is.NaN);
            Assert.That(pose.FacadeY, Is.NaN);
            Assert.That(pose.LacetDegres, Is.NaN);
        }
    }
}
