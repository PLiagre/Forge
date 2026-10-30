using System;
using Forge.Pont;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

namespace Forge.Interface.Tests
{
    public sealed class CalquesCarteTests
    {
        [Test] public void LesPigmentsGardentLesFamillesPolitiquesSansCouleursVives()
        {
            var rouge = SocleInterface.Pigment(UnityEngine.Color.red);
            var bleu = SocleInterface.Pigment(UnityEngine.Color.blue);
            Assert.That(rouge.r, Is.GreaterThan(rouge.b));
            Assert.That(bleu.b, Is.GreaterThan(bleu.r));
            foreach (var pigment in new[] { rouge, bleu, SocleInterface.Pigment(UnityEngine.Color.green) })
            {
                UnityEngine.Color.RGBToHSV(pigment, out _, out float saturation, out float valeur);
                Assert.That(saturation, Is.LessThan(.45f));
                Assert.That(valeur, Is.InRange(.5f, .7f));
            }
        }
        // DA du 28 octobre : le thème garde la teinte servie ; un pigment repeint d'un jeton échoue.
        [Test] public void LePigmentGardeLaTeinteServieDeChaqueMaison()
        {
            for (int i = 0; i < 24; i++)
                foreach (float saturation in new[] { 1f, .7f, .5f })
                {
                    var servie = UnityEngine.Color.HSVToRGB(i / 24f, saturation, .9f);
                    UnityEngine.Color.RGBToHSV(SocleInterface.Pigment(servie), out float teinte, out _, out _);
                    float ecart = Math.Abs(teinte - i / 24f);
                    Assert.That(Math.Min(ecart, 1 - ecart) * 360, Is.LessThan(15f), "teinte " + i * 15 + "°");
                }
        }
        static MondeLu Monde(params CelluleDuMonde[] cellules) => new MondeLu(8, new DateDuMonde(1400, 9), cellules.Length, cellules);
        [Test] public void La_legende_et_les_teintes_derivent_des_populations_recues()
        {
            var repartition = new RepartitionHabitants(Monde(new CelluleDuMonde(10, 0, -1, -1), new CelluleDuMonde(20, 90, -1, -1)));
            Assert.AreEqual(0, repartition.Minimum); Assert.AreEqual(90, repartition.Maximum);
            Assert.AreEqual(0, repartition.Position(10)); Assert.AreEqual(1, repartition.Position(20));
            StringAssert.Contains("jour 9 de 1400", repartition.Legende);
            StringAssert.Contains("90 habitants (foncé)", repartition.Legende);
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
        [Test] public void La_legende_des_habitants_dit_la_date_et_compte_en_habitants()
        {
            string legende = new RepartitionHabitants(Monde(new CelluleDuMonde(10, 1, -1, -1), new CelluleDuMonde(20, 5631, -1, -1))).Legende;
            Assert.AreEqual("5\u00A0631", TexteDuMonde.Nombre(5631));
            Assert.AreEqual("Habitants : 1 habitant (clair) → 5\u00A0631 habitants (foncé) · échelle logarithmique · jour 9 de 1400", legende);
            Assert.IsNull(TexteDuMonde.Interdit(legende), legende); Assert.IsNull(TexteDuMonde.SansUnite(legende), legende);
            Assert.Catch<ArgumentException>(() => new RepartitionHabitants(new MondeLu(8, new DateDuMonde(1400, 0), 1, new[] { new CelluleDuMonde(10, 1, -1, -1) })));
            LogAssert.Expect(LogType.Log, "TexteDuMonde : absence déclarée par le monde : Population absente du territoire 30");
            Assert.AreEqual("Calque indisponible : déclaré absent par le monde. Couleurs des puissances conservées.", CalquesCarte.Indisponible("Population absente du territoire 30"));
            Assert.AreEqual("Calque indisponible : Population des territoires incomplète. Couleurs des puissances conservées.", CalquesCarte.Indisponible("Population des territoires incomplète"));
        }
    }
}
