using System;
using System.Linq;
using NUnit.Framework;
namespace Forge.Pont.Tests
{
    // Lot #958 — le résumé des temps d'image (médiane, 95e centile au rang le plus proche, maximum) et l'interrupteur des optimisations.
    public sealed class TempsDImageTests
    {
        static double[] Suite(int n) => Enumerable.Range(1, n).Select(i => (double)i).ToArray();
        static void Verifier(double[] temps, int nombre, double mediane, double p95, double maximum)
        {
            var r = TempsDImage.Resumer(temps);
            Assert.AreEqual(nombre, r.Nombre, "nombre");
            Assert.AreEqual(mediane, r.MedianeMs, 1e-12, "médiane");
            Assert.AreEqual(p95, r.P95Ms, 1e-12, "95e centile");
            Assert.AreEqual(maximum, r.MaximumMs, 1e-12, "maximum");
        }

        [Test] public void UnAVingtDansLeDesordreSansToucherLeTableau()
        {
            var temps = new double[] { 7, 20, 3, 14, 1, 18, 9, 12, 5, 16, 2, 19, 11, 6, 15, 4, 17, 8, 13, 10 };
            var avant = (double[])temps.Clone();
            Verifier(temps, 20, 10.5, 19, 20);
            CollectionAssert.AreEqual(avant, temps);
        }
        // 1 à 10 : le rang 10, pas 9,55 (interpolé) ni 9 (rang tronqué 95·n/100).
        [TestCase(10, 5.5, 10, 10)]
        [TestCase(21, 11, 20, 21)]
        [TestCase(100, 50.5, 95, 100)]
        public void UnAN(int n, double mediane, double p95, double maximum) => Verifier(Suite(n), n, mediane, p95, maximum);
        [Test] public void CinqDansLeDesordre() => Verifier(new double[] { 5, 1, 4, 2, 3 }, 5, 3, 5, 5);
        [Test] public void UnSeulElement() => Verifier(new[] { 16.7 }, 1, 16.7, 16.7, 16.7);
        [Test] public void ZeroEstPermis() => Verifier(new double[] { 0, 0, 0 }, 3, 0, 0, 0);
        [Test] public void DesDoublons() => Verifier(new double[] { 2, 2, 9, 2 }, 4, 2, 9, 9);
        [Test] public void NulRefuse() => Assert.Throws<ArgumentNullException>(() => TempsDImage.Resumer(null));
        [Test] public void VideRefuse() => StringAssert.Contains("vide", Assert.Throws<ArgumentException>(() => TempsDImage.Resumer(new double[0])).Message);
        [TestCase(double.NaN)]
        [TestCase(double.PositiveInfinity)]
        [TestCase(double.NegativeInfinity)]
        [TestCase(-0.001)]
        public void ValeurRefuseeNommeSonRang(double fautive)
            => StringAssert.Contains("1", Assert.Throws<ArgumentOutOfRangeException>(() => TempsDImage.Resumer(new[] { 1, fautive })).Message);
    }

    public sealed class OptimisationsDeLaVilleTests
    {
        [Test] public void SansArgumentActives() => Assert.IsTrue(OptimisationsDeLaVille.Lire(new string[0]));
        [Test] public void LeDrapeauExactLesCoupe() => Assert.IsFalse(OptimisationsDeLaVille.Lire(new[] { "Unity.exe", "-forgeSansOptimisations", "-batchmode" }));
        [TestCase("-forgesansoptimisations")]
        [TestCase("-forgeSansOptimisationsX")]
        public void UnDrapeauVoisinNeCoupeRien(string argument) => Assert.IsTrue(OptimisationsDeLaVille.Lire(new[] { argument }));
        [Test] public void NulRefuse() => Assert.Throws<ArgumentNullException>(() => OptimisationsDeLaVille.Lire(null));
        [Test] public void ActivesLitLaLigneDeCommande() => Assert.AreEqual(OptimisationsDeLaVille.Lire(Environment.GetCommandLineArgs()), OptimisationsDeLaVille.Actives);
    }
}
