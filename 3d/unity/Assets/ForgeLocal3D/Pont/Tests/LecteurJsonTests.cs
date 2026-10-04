using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using NUnit.Framework;
using UnityEngine;

namespace Forge.Pont.Tests
{
    // Lot #185 — la réponse `/lieu` figée (SC1 la garde identique à celle du
    // service) est relue en entier ; un texte cassé est refusé en nommant la position.
    public sealed class LecteurJsonTests
    {
        private static string TexteFige()
        {
            string chemin = Path.Combine(Application.dataPath, "ForgeLocal3D/Pont/Tests/lieu-graine0-tick3.json");
            Assert.IsTrue(File.Exists(chemin), "réponse figée absente : " + chemin);
            string texte = File.ReadAllText(chemin);
            Assert.IsNotEmpty(texte, "réponse figée vide : " + chemin);
            return texte;
        }

        private static ErreurJson Refus(Func<object> lecture)
        {
            object rendu = null;
            var erreur = Assert.Throws<ErreurJson>(() => rendu = lecture());
            Assert.IsNull(rendu, "un texte refusé ne rend jamais de résultat");
            StringAssert.Contains("position", erreur.Message);
            return erreur;
        }

        [Test]
        public void LaReponseFigeeEstRelueEnEntierSansListeFermee()
        {
            var lieu = LecteurJson.LireObjet(TexteFige());

            CollectionAssert.AreEqual(
                new[] { "cell_id", "date", "food_deficit_kg", "foyers", "hunger_ticks", "population", "stocks", "tick" },
                lieu.Keys.ToArray());
            var date = (Dictionary<string, object>)lieu["date"];
            Assert.AreEqual(2, date.Count);
            Assert.IsTrue((double)date["annee"] == 1400.0);
            Assert.IsTrue((double)date["jour_de_l_annee"] == 4.0);

            Assert.IsTrue((double)lieu["cell_id"] == 9922.0);
            Assert.IsTrue((double)lieu["population"] == 109752.0);
            Assert.IsTrue((double)lieu["tick"] == 3.0);
            Assert.IsTrue((double)lieu["hunger_ticks"] == 0.0);
            Assert.IsTrue((double)lieu["food_deficit_kg"] == 0.0, "0.0 est une mesure, lue comme un nombre");

            var stocks = (Dictionary<string, object>)lieu["stocks"];
            Assert.GreaterOrEqual(stocks.Count, 2);
            Assert.IsTrue(stocks.ContainsKey("nourriture"));
            Assert.IsTrue(stocks.Keys.Any(cle => cle != "nourriture"));
            CollectionAssert.AreEqual(new[] { "fer", "nourriture", "objet" }, stocks.Keys.ToArray());
            Assert.IsTrue((double)stocks["fer"] == 625.890235);
            Assert.IsTrue((double)stocks["nourriture"] == 1086412.323983);
            Assert.IsTrue((double)stocks["objet"] == 19.415859);

            // Lot #300 — les foyers par métier, lus dans la même photographie.
            var foyers = (Dictionary<string, object>)lieu["foyers"];
            CollectionAssert.AreEqual(new[] { "mineurs", "paysans" }, foyers.Keys.ToArray());
            var mineurs = (Dictionary<string, object>)foyers["mineurs"];
            var paysans = (Dictionary<string, object>)foyers["paysans"];
            CollectionAssert.AreEqual(new[] { "foyers", "personnes" }, mineurs.Keys.ToArray());
            CollectionAssert.AreEqual(new[] { "foyers", "personnes" }, paysans.Keys.ToArray());
            Assert.IsTrue((double)mineurs["personnes"] == 10974.0);
            Assert.IsTrue((double)mineurs["foyers"] == 2195.0, "le dernier foyer incomplet compte");
            Assert.IsTrue((double)paysans["personnes"] == 98778.0);
            Assert.IsTrue((double)paysans["foyers"] == 19756.0);
            Assert.IsTrue(
                (double)mineurs["personnes"] + (double)paysans["personnes"] == (double)lieu["population"],
                "les personnes des métiers font la population");
        }

        [Test]
        public void UnSeulChiffreChangeSeVoitALaRelecture()
        {
            string texte = TexteFige();
            StringAssert.Contains("1086412.323983", texte);
            string altere = texte.Replace("1086412.323983", "1086412.323984");

            var stocks = (Dictionary<string, object>)LecteurJson.LireObjet(altere)["stocks"];
            Assert.AreNotEqual(1086412.323983, (double)stocks["nourriture"]);
            Assert.IsTrue((double)stocks["nourriture"] == 1086412.323984);
        }

        [Test]
        public void UneMarchandiseInventeePasseSansToucherAuLecteur()
        {
            string texte = TexteFige();
            StringAssert.Contains("\"stocks\":{", texte);
            string enrichi = texte.Replace("\"stocks\":{", "\"stocks\":{\"zinc_du_test\":1.5,");

            var stocks = (Dictionary<string, object>)LecteurJson.LireObjet(enrichi)["stocks"];
            Assert.IsTrue((double)stocks["zinc_du_test"] == 1.5);
            Assert.IsTrue((double)stocks["nourriture"] == 1086412.323983);
        }

        [Test]
        public void LeTexteFigeSansSonAccoladeFinaleEstRefuse()
        {
            string texte = TexteFige();
            string tronque = texte.Substring(0, texte.Length - 1);
            Assert.AreEqual(tronque.Length, Refus(() => LecteurJson.LireObjet(tronque)).Position);
        }

        [Test]
        public void LeTexteFigeCoupeApresStocksEstRefuse()
        {
            string texte = TexteFige();
            int fin = texte.IndexOf("\"stocks\":", StringComparison.Ordinal);
            Assert.GreaterOrEqual(fin, 0, "clé stocks absente du texte figé");
            string tronque = texte.Substring(0, fin + "\"stocks\":".Length);
            Assert.AreEqual(tronque.Length, Refus(() => LecteurJson.LireObjet(tronque)).Position);
        }

        [Test]
        public void UnTableauNEstPasUnObjet()
        {
            Assert.AreEqual(0, Refus(() => LecteurJson.LireObjet("[1]")).Position);
            var liste = (List<object>)LecteurJson.Lire("[1]");
            Assert.AreEqual(1, liste.Count);
            Assert.IsTrue((double)liste[0] == 1.0);
        }

        [Test]
        public void LeTexteVideEstRefuseEtNullAussi()
        {
            Assert.AreEqual(0, Refus(() => LecteurJson.LireObjet("")).Position);
            Assert.Throws<ArgumentNullException>(() => LecteurJson.LireObjet(null));
            Assert.Throws<ArgumentNullException>(() => LecteurJson.Lire(null));
        }

        [Test]
        public void UnDechetApresLaRacineEstRefuse()
        {
            Assert.AreEqual(7, Refus(() => LecteurJson.LireObjet("{\"a\":1}x")).Position);
        }

        [Test]
        public void UneCleEnDoubleEstRefusee()
        {
            Refus(() => LecteurJson.LireObjet("{\"a\":1,\"a\":2}"));
        }

        [Test]
        public void LesNombresSuiventLaGrammaireStricte()
        {
            foreach (string faux in new[] { "+1", "01", ".5", "NaN", "1.", "-", "1e" })
                Refus(() => LecteurJson.Lire(faux));
            Assert.IsTrue((double)LecteurJson.Lire(" 0 ") == 0.0);
            Assert.IsTrue((double)LecteurJson.Lire("-2.5e3") == -2500.0);
        }

        [Test]
        public void LesChainesEtLitterauxSontRelus()
        {
            Assert.AreEqual("a\"\\/\b\f\n\r\té", LecteurJson.Lire("\"a\\\"\\\\\\/\\b\\f\\n\\r\\t\\u00e9\""));
            Assert.AreEqual(true, LecteurJson.Lire("true"));
            Assert.AreEqual(false, LecteurJson.Lire("false"));
            Assert.IsNull(LecteurJson.Lire("null"));
            Assert.IsEmpty(LecteurJson.LireObjet("{ }"));
        }
    }
}
