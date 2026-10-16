using System;
using Forge.Pont;
using NUnit.Framework;

namespace Forge.Interface.Tests
{
    public sealed class CalquesCarteTests
    {
        static MondeLu Monde(params CelluleDuMonde[] cellules) => new MondeLu(8, new DateDuMonde(1400, 9), cellules.Length, cellules);
        [Test] public void La_legende_et_les_teintes_derivent_des_populations_recues()
        {
            var repartition = new RepartitionHabitants(Monde(new CelluleDuMonde(10, 0, -1, -1), new CelluleDuMonde(20, 90, -1, -1)));
            Assert.AreEqual(0, repartition.Minimum); Assert.AreEqual(90, repartition.Maximum);
            Assert.AreEqual(0, repartition.Position(10)); Assert.AreEqual(1, repartition.Position(20));
            StringAssert.Contains("tick 8", repartition.Legende);
            StringAssert.Contains("90", repartition.Legende);
            StringAssert.Contains("échelle logarithmique", repartition.Legende);
            Assert.Throws<ArgumentException>(() => repartition.Position(30));
        }
        [Test] public void Une_cellule_manquante_dupliquee_ou_negative_refuse_le_calque()
        {
            var cellule = new CelluleDuMonde(10, 3, -1, -1);
            Assert.Throws<ArgumentException>(() => new RepartitionHabitants(Monde()));
            Assert.Throws<ArgumentException>(() => new RepartitionHabitants(Monde(cellule, cellule)));
            Assert.Throws<ArgumentException>(() => new RepartitionHabitants(Monde(new CelluleDuMonde(10, -1, -1, -1))));
            Assert.Throws<ArgumentException>(() => new RepartitionHabitants(new MondeLu(0, new DateDuMonde(1400, 1), 2, new[] { cellule })));
            Assert.AreEqual(.5f, new RepartitionHabitants(Monde(cellule)).Position(10));
        }
    }
}
