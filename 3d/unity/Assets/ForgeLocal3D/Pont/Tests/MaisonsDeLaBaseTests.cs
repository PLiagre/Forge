using System.Collections.Generic;
using NUnit.Framework;

namespace Forge.Pont.Tests
{
    // Lot #736 — chaque logis regarde sa rue ; un îlot de k foyers se coupe en k cases depuis cette rue.
    public sealed class MaisonsDeLaBaseTests
    {
        private const double Tol = 1e-9;

        private static List<PointLocal> Pts(params double[] xy)
        {
            var l = new List<PointLocal>(xy.Length / 2);
            for (int i = 0; i < xy.Length; i += 2) l.Add(new PointLocal(xy[i], xy[i + 1]));
            return l;
        }

        // Principale, ruelle d'angle, deux ruelles qui ne longent pas les îlots, cinq maisons.
        private static BaseDuPlan Synthese(double yFin = 0, bool trois = false) => new BaseDuPlan(Pts(0, 0, 1, 0, 1, 1), new[]
        {
            new RueDeBase(Pts(50, 0, 150, yFin), 6, "principale"), new RueDeBase(Pts(90, 3, 90, 63), 3, "ruelle"),
            new RueDeBase(Pts(134, -20, 194, -20), 3, "ruelle"), new RueDeBase(Pts(134, -40, 134, -100), 3, "ruelle"),
        }, new[]
        {
            new MaisonDeBase(trois ? Pts(62.5, 12, 62.5, 4, 57.5, 4) : Pts(62.5, 12, 62.5, 4, 57.5, 4, 57.5, 12), 1),
            new MaisonDeBase(Pts(62.5, -4, 62.5, -12, 57.5, -12, 57.5, -4), 1),
            new MaisonDeBase(Pts(92.5, 8, 100.5, 8, 100.5, 3, 92.5, 3), 1),
            new MaisonDeBase(Pts(132.5, -4, 132.5, -36, 107.5, -36, 107.5, -4), 20),
            new MaisonDeBase(Pts(132.5, 13.6, 132.5, 4, 107.5, 4, 107.5, 13.6), 6),
        });

        private static void Case(CaseDeMaison c, int maison, int indice, double x, double y, double lacet, double lar, double pro)
        {
            Assert.IsTrue(c.Maison == maison && c.Indice == indice, c.Maison + "," + c.Indice);
            Assert.AreEqual(x, c.CentreX, Tol);
            Assert.AreEqual(y, c.CentreY, Tol);
            Assert.AreEqual(lacet, c.LacetDegres, Tol);
            Assert.AreEqual(lar, c.LargeurM, Tol);
            Assert.AreEqual(pro, c.ProfondeurM, Tol);
        }

        [Test]
        public void LesMaisonsDeLaBaseRegardentLeurRue()
        {
            PoseDesMaisons pose = MaisonsDeLaBase.Poser(Synthese());
            Assert.IsTrue(pose.Presente, pose.Absence);
            Assert.AreEqual("", pose.Absence);
            Assert.AreEqual(29, pose.Cases.Count);
            var foyers = new[] { 1, 1, 1, 20, 6 };
            for (int maison = 0, n = 0; maison < foyers.Length; maison++)
                for (int j = 0; j < foyers[maison]; j++, n++)
                    Assert.IsTrue(pose.Cases[n].Maison == maison && pose.Cases[n].Indice == j, n.ToString());
            Case(pose.Cases[0], 0, 0, 60, 8, 0, 5, 8);
            Case(pose.Cases[1], 1, 0, 60, -8, 180, 5, 8);
            Case(pose.Cases[2], 2, 0, 96.5, 5.5, 90, 5, 8);
            Case(pose.Cases[3], 3, 0, 110.625, -7.2, 180, 6.25, 6.4);
            Case(pose.Cases[6], 3, 3, 129.375, -7.2, 180, 6.25, 6.4);
            Case(pose.Cases[7], 3, 4, 110.625, -13.6, 180, 6.25, 6.4);
            Case(pose.Cases[22], 3, 19, 129.375, -32.8, 180, 6.25, 6.4);
            Case(pose.Cases[23], 4, 0, 129.375, 6.4, 0, 6.25, 4.8);
            Case(pose.Cases[26], 4, 3, 110.625, 6.4, 0, 6.25, 4.8);
            Case(pose.Cases[27], 4, 4, 129.375, 11.2, 0, 6.25, 4.8);
            Case(pose.Cases[28], 4, 5, 123.125, 11.2, 0, 6.25, 4.8);
        }

        [Test]
        public void UnePoseImpossibleEstDeclareeAbsente()
        {
            PoseDesMaisons reference = MaisonsDeLaBase.Poser(Synthese());
            PoseDesMaisons proche = MaisonsDeLaBase.Poser(Synthese(0.05));
            Assert.IsTrue(proche.Presente, proche.Absence);
            Assert.AreEqual(29, proche.Cases.Count);
            for (int i = 0; i < 29; i++)
            {
                CaseDeMaison a = reference.Cases[i];
                Case(proche.Cases[i], a.Maison, a.Indice, a.CentreX, a.CentreY, a.LacetDegres, a.LargeurM, a.ProfondeurM);
            }

            PoseDesMaisons loin = MaisonsDeLaBase.Poser(Synthese(0.15));
            Assert.IsFalse(loin.Presente);
            StringAssert.Contains("maison 1", loin.Absence);
            StringAssert.Contains("aucune rue parallèle", loin.Absence);
            Assert.AreEqual(0, loin.Cases.Count);

            PoseDesMaisons trois = MaisonsDeLaBase.Poser(Synthese(trois: true));
            Assert.IsFalse(trois.Presente);
            StringAssert.Contains("maison 0 : emprise de 3 points", trois.Absence);
            Assert.AreEqual(0, trois.Cases.Count);

            PoseDesMaisons vide = MaisonsDeLaBase.Poser(new BaseDuPlan(Pts(0, 0, 1, 0, 1, 1), new RueDeBase[0], new MaisonDeBase[0]));
            Assert.IsTrue(vide.Presente, vide.Absence);
            Assert.AreEqual("", vide.Absence);
            Assert.AreEqual(0, vide.Cases.Count);
            Assert.Throws<System.ArgumentNullException>(() => MaisonsDeLaBase.Poser(null));
        }
    }
}
