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
        // Lot #943 : sous ses deux formes, la légende passe les juges du clerc ; l'ancienne, datée de 1400, en rougit.
        [Test] public void La_legende_des_deux_calques_passe_les_juges_du_clerc()
        {
            var repartition = new RepartitionHabitants(Monde(new CelluleDuMonde(10, 1, -1, -1), new CelluleDuMonde(20, 5631, -1, -1)));
            foreach (string legende in new[] { CalquesCarte.LegendeDuCalque(null), CalquesCarte.LegendeDuCalque(repartition) })
            {
                Assert.IsNull(TexteDuMonde.Interdit(legende), legende);
                Assert.IsNull(TexteDuMonde.SansUnite(legende), legende);
            }
            Assert.AreEqual("Puissances de la carte · Relief non transmis · Rouge : territoire conservé", CalquesCarte.LegendeDuCalque(null));
            Assert.AreEqual("Habitants : 1 habitant (clair) → 5 631 habitants (foncé) · échelle logarithmique · jour 9 de 1400 · Rouge : territoire conservé", CalquesCarte.LegendeDuCalque(repartition));
            Assert.AreEqual("1400", TexteDuMonde.SansUnite("Puissances de la carte de 1400 · Relief non transmis · Rouge : territoire conservé"));
        }
        // Lot #963 : chaque mode a sa couleur, sa légende de trois lignes au plus et son détail ; la terre gardée reste rouge.
        [Test] public void Chaque_mode_a_sa_couleur_et_sa_legende()
        {
            var modes = new[] { ModeDeCarte.Puissances, ModeDeCarte.Habitants, ModeDeCarte.Flux }; Color maison = new Color(.2f, .4f, .8f);
            var teintes = Array.ConvertAll(modes, m => CalquesCarte.Teinte(m, false, maison, .5f)); Assert.That(teintes[0] != teintes[1] && teintes[1] != teintes[2] && teintes[0] != teintes[2], Is.True, string.Join(" / ", teintes));
            foreach (var mode in modes) Assert.AreEqual(SocleInterface.Couleur("alerte"), CalquesCarte.Teinte(mode, true, maison, .5f), mode.ToString());
            Assert.AreEqual(CalquesCarte.FLUX, CalquesCarte.LegendeDuMode(ModeDeCarte.Flux, null)); var repartition = new RepartitionHabitants(Monde(new CelluleDuMonde(10, 1, -1, -1), new CelluleDuMonde(20, 5631, -1, -1)));
            foreach (var mode in modes) foreach (string texte in new[] { CalquesCarte.LegendeDuMode(mode, repartition), CalquesCarte.DetailDuMode(mode) }) Assert.IsNull(TexteDuMonde.Interdit(texte) ?? TexteDuMonde.SansUnite(texte), texte);
            var toile = new GameObject("Toile témoin", typeof(Canvas));
            try
            {
                var calques = toile.AddComponent<CalquesCarte>(); calques.Initialiser(null, toile.transform, () => null, () => null);
                var texte = SocleInterface.Texte(toile.transform, "", 0, 0, 470); const string QUATRE = "Première ligne\nDeuxième ligne\nTroisième ligne\nQuatrième ligne";
                Assert.AreEqual(SocleInterface.Corps, texte.fontSize); Assert.AreEqual(4, CalquesCarte.Lignes(texte, QUATRE, 1f));
                Assert.Throws<ArgumentException>(() => calques.Legender(QUATRE, CalquesCarte.DetailDuMode(ModeDeCarte.Puissances)));
            }
            finally { UnityEngine.Object.DestroyImmediate(toile); }
        }
    }
}
