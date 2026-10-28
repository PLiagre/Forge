using System;
using System.Globalization;
using System.Threading;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

namespace Forge.Pont.Tests {
    // Lot #870 — les mots du monde : la date servie, les jours, les masses et les grands nombres s'écrivent partout pareil,
    // et deux juges refusent un texte qui montre un identifiant ou un nombre sans unité.
    public sealed class TexteDuMondeTests {
        private const string NBSP = " ";
        private CultureInfo avant;
        // Les sorties ne dépendent jamais de la culture du système : les cas tournent sous une culture à point décimal.
        [SetUp] public void CultureEtrangere() { avant = Thread.CurrentThread.CurrentCulture; Thread.CurrentThread.CurrentCulture = CultureInfo.GetCultureInfo("en-US"); }
        [TearDown] public void CultureRendue() { Thread.CurrentThread.CurrentCulture = avant; }

        private static void Juge(string attendu, string trouve, string texte) => Assert.AreEqual(attendu, trouve, "« " + texte + " »");

        [Test] public void LaDateServieSEcritEnJourDeLAnnee() {
            Assert.AreEqual("jour 8 de 1400", TexteDuMonde.Date(new DateDuMonde(1400, 8)));
            Assert.AreEqual("jour 1 de 1401", TexteDuMonde.Date(new DateDuMonde(1401, 1)));
            Assert.AreEqual("jour 366 de 1400", TexteDuMonde.Date(new DateDuMonde(1400, 366)));
            Assert.Throws<ArgumentOutOfRangeException>(() => TexteDuMonde.Date(new DateDuMonde(1400, 0)));
            Assert.Throws<ArgumentOutOfRangeException>(() => TexteDuMonde.Date(new DateDuMonde(1400, 367)));
            Assert.Throws<ArgumentOutOfRangeException>(() => TexteDuMonde.Date(new DateDuMonde(0, 8)));
            Assert.AreEqual("5" + NBSP + "631", TexteDuMonde.Nombre(5631));
            Assert.AreEqual("-5" + NBSP + "631", TexteDuMonde.Nombre(-5631));
            Assert.AreEqual("1" + NBSP + "234" + NBSP + "567", TexteDuMonde.Nombre(1234567));
            Assert.AreEqual("12", TexteDuMonde.Nombre(12));
        }

        [Test] public void LesJoursSAccordent() {
            Assert.AreEqual("0 jour", TexteDuMonde.Jours(0));
            Assert.AreEqual("1 jour", TexteDuMonde.Jours(1));
            Assert.AreEqual("12 jours", TexteDuMonde.Jours(12));
            Assert.AreEqual("1" + NBSP + "234 jours", TexteDuMonde.Jours(1234));
            Assert.Throws<ArgumentOutOfRangeException>(() => TexteDuMonde.Jours(-1));
        }

        private static readonly (double Kg, string Texte)[] Masses = {
            (0, "0 kg"), (12.5, "12,5 kg"), (999.5, "999,5 kg"), (999.996, "1,00 t"), (1000, "1,00 t"), (1234.5, "1,23 t"), (9996, "10,0 t"),
            (41712, "41,7 t"), (99960, "100 t"), (123456, "123 t"), (5631000, "5" + NBSP + "631 t"), (-1234.5, "-1,23 t") };

        [Test] public void LesKilosPassentEnTonnesATroisChiffres() {
            foreach (var (kg, texte) in Masses) {
                string ecrit = TexteDuMonde.Masse(kg);
                Assert.AreEqual(texte, ecrit, kg.ToString("R", CultureInfo.InvariantCulture) + " kg");
                Assert.AreEqual(-1, ecrit.IndexOf(' '), ecrit); // à l'octet : `StringAssert` compare selon la culture, qui confond U+202F et l'espace
            }
            Assert.Throws<ArgumentException>(() => TexteDuMonde.Masse(double.NaN));
            Assert.Throws<ArgumentException>(() => TexteDuMonde.Masse(double.PositiveInfinity));
        }

        [Test] public void InterditTrouveLePremierIdentifiant() {
            foreach (string texte in new[] { "orange", "arrangé", "ticket", "jour 8 de 1400", "1,23 t", "Maison en attente" }) Juge(null, TexteDuMonde.Interdit(texte), texte);
            Juge(null, TexteDuMonde.Interdit("103405", "10340"), "103405");
            Juge(null, TexteDuMonde.Interdit("Maison_Bar", "maison_bar"), "Maison_Bar");
            foreach (var (texte, mot) in new[] { ("Cellule 7", "Cellule"), ("CELLULE", "CELLULE"), ("tick 7", "tick"), ("3 ticks", "ticks"), ("10340-1", "10340-1"),
                    ("lieu 10340-1 absent", "10340-1"), ("rang 2 de la Cellule 7", "rang") })
                Juge(mot, TexteDuMonde.Interdit(texte), texte);
            Juge("10340", TexteDuMonde.Interdit("Paris, 10340", "10340"), "Paris, 10340");
            Juge("maison_bar", TexteDuMonde.Interdit("maison_bar", "maison_bar"), "maison_bar");
            Juge("10340", TexteDuMonde.Interdit("Paris, 10340 au tick 7, Cellule 9", "10340"), "premier au plus petit indice");
            Juge("tick", TexteDuMonde.Interdit("Paris au tick 7, 10340-1", "10340"), "premier au plus petit indice");
            Assert.Throws<ArgumentException>(() => TexteDuMonde.Interdit("Paris", " "));
            Assert.Throws<ArgumentException>(() => TexteDuMonde.Interdit("Paris", ""));
            Assert.Throws<ArgumentNullException>(() => TexteDuMonde.Interdit(null));
        }

        [Test] public void SansUniteTrouveLeNombreNu() {
            foreach (string texte in new[] { "41,7 t", "5" + NBSP + "631 habitants", "50 %", "50%", "12 jours", "jour 8 de 1400", "Jour 8 de 1400", "Mistra, J4" })
                Juge(null, TexteDuMonde.SansUnite(texte), texte);
            foreach (var (texte, nombre) in new[] { ("5 631", "5 631"), ("5 631 Paris", "5 631"), ("Ville 7", "7"), ("12 kgx", "12"), ("12,5", "12,5"), ("de 1400", "1400"),
                    ("5 631", "5 631"), ("jour 8 de 1 400", "1 400") })
                Juge(nombre, TexteDuMonde.SansUnite(texte), texte);
            // Ce que le Pont écrit avec son unité passe les deux juges ; `Nombre` seul n'en a pas, l'écran la pose.
            foreach (string ecrit in new[] { TexteDuMonde.Date(new DateDuMonde(1400, 8)), TexteDuMonde.Date(new DateDuMonde(1401, 1)),
                    TexteDuMonde.Jours(0), TexteDuMonde.Jours(1), TexteDuMonde.Jours(12), TexteDuMonde.Jours(1234) }) {
                Juge(null, TexteDuMonde.Interdit(ecrit), ecrit); Juge(null, TexteDuMonde.SansUnite(ecrit), ecrit);
            }
            foreach (var (kg, _) in Masses) { string ecrit = TexteDuMonde.Masse(kg); Juge(null, TexteDuMonde.Interdit(ecrit), ecrit); Juge(null, TexteDuMonde.SansUnite(ecrit), ecrit); }
            Assert.Throws<ArgumentNullException>(() => TexteDuMonde.SansUnite(null));
        }

        [Test] public void UneAbsenceQuiNommeUnIdentifiantSeTait() {
            foreach (var (raison, ids) in new[] { ("lieu 10340-1 absent du service", new string[0]), ("Population absente du territoire 10340", new string[0]),
                    ("maison_bar sans siège", new[] { "maison_bar" }) }) {
                LogAssert.Expect(LogType.Log, "TexteDuMonde : absence déclarée par le monde : " + raison);
                Assert.AreEqual("déclaré absent par le monde", TexteDuMonde.Absence(raison, ids), raison);
            }
            Assert.AreEqual("Maison en attente", TexteDuMonde.Absence("Maison en attente", "maison_bar"));
            LogAssert.NoUnexpectedReceived();
            Assert.Throws<ArgumentException>(() => TexteDuMonde.Absence(" "));
            Assert.Throws<ArgumentException>(() => TexteDuMonde.Absence(""));
        }
    }
}
