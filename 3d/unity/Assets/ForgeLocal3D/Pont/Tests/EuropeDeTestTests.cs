using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;

namespace Forge.Pont.Tests {
    // La carte de l'Europe entière se lit : les quatre réponses figées sont présentes, cohérentes entre elles, et portent
    // de quoi nommer les pays (suzerain, ensemble) et la carte (fleuves, mers, régions, sièges).
    public sealed class EuropeDeTestTests {
        [Test] public void EuropeDeTest_se_lit() {
            CarteLue carte = EuropeDeTest.CarteEurope; TerresDeLaCarte terres = EuropeDeTest.TerresEurope; JouablesLus jouables = EuropeDeTest.JouablesEurope;
            Dictionary<string, object> atlas = EuropeDeTest.AtlasBrut;
            Assert.IsNotNull(carte, "carte"); Assert.IsNotNull(terres, "terres"); Assert.IsNotNull(jouables, "jouables"); Assert.IsNotNull(atlas, "atlas");

            // Une terre par cellule, jamais une terre de trop ni une cellule sans terre ; un échantillon vide échoue.
            Assert.Greater(carte.Cellules.Count, 0, "la carte lue n'a aucune cellule");
            Assert.AreEqual(carte.Cellules.Count, terres.Terres.Count, "les terres lues et les cellules lues ne se comptent pas pareil");
            var terresParCellule = new HashSet<long>(terres.Terres.Select(t => t.CellId));
            Assert.AreEqual(terres.Terres.Count, terresParCellule.Count, "une cellule porte deux terres");
            foreach (CelluleDeCarte cellule in carte.Cellules) Assert.IsTrue(terresParCellule.Contains(cellule.CellId), "la cellule " + cellule.CellId + " n'a pas de terre");
            Assert.AreEqual(carte.Cellules.Count, EuropeDeTest.TerrainEurope.NombreDeLieux, "le terrain prend un lieu par cellule");

            // Les terres et les jouables disent le même jour du monde.
            Assert.AreEqual(jouables.Tick, terres.Tick, "les terres et les jouables ne disent pas le même tick");
            Assert.Greater(jouables.Fiches.Count, 0, "aucune fiche jouable");

            // Le suzerain et l'ensemble d'un pays se comptent dans le corps brut ; `ClientGuerreTests` juge que `PaysDeLaCarte` les lit à l'identique.
            var brutes = (List<object>)LecteurJson.LireObjet(EuropeDeTest.Corps(EuropeDeTest.TERRES))["pays"];
            Assert.AreEqual(terres.Pays.Count, brutes.Count, "les pays lus et les pays servis ne se comptent pas pareil");
            Assert.Greater(terres.Pays.Count, 0, "aucun pays lu");
            int suzerains = brutes.Count(p => ((Dictionary<string, object>)p)["suzerain"] != null);
            int ensembles = brutes.Count(p => ((Dictionary<string, object>)p)["ensemble"] != null);
            Assert.Greater(suzerains, 0, "aucun pays ne porte de suzerain"); Assert.Greater(ensembles, 0, "aucun pays ne porte d'ensemble");

            // Les noms de la carte.
            foreach (string cle in new[] { "fleuves", "mers", "regions", "sieges" }) {
                Assert.IsTrue(atlas.TryGetValue(cle, out object valeur) && valeur is List<object> liste && liste.Count > 0, "atlas." + cle + " est vide ou absent");
            }
            Assert.IsTrue(((List<object>)atlas["sieges"]).Any(s => (string)((Dictionary<string, object>)s)["nom"] == "Biskra"), "aucun siège ne s'appelle Biskra");
            TestContext.WriteLine("EUROPE cellules " + carte.Cellules.Count + " terres " + terres.Terres.Count + " pays " + terres.Pays.Count + " suzerains " + suzerains + " ensembles " + ensembles
                + " fleuves " + ((List<object>)atlas["fleuves"]).Count + " mers " + ((List<object>)atlas["mers"]).Count + " regions " + ((List<object>)atlas["regions"]).Count + " sieges " + ((List<object>)atlas["sieges"]).Count
                + " jouables " + jouables.Fiches.Count + " tick " + terres.Tick);
        }
    }
}
