using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;

namespace Forge.Pont.Tests {
    // Le terrain des Détroits, relevé du vrai service : la cellule du bourg de Constantinople et ses voisines de Thrace et de
    // Bithynie. Il se lève, et il porte côte à côte des lieux de Byzance et des lieux ottomans selon `/terres` de l'Europe,
    // de quoi juger qu'un nom de pays ne s'écrit que sur ses lieux.
    public sealed class TerrainDesDetroitsTests {
        private const string BYZANCE = "puissance-25", OTTOMANS = "puissance-26";

        // Le pays de chaque lieu du terrain selon ces terres, groupé par cellule ; null pour un lieu sans pays.
        private static Dictionary<long, List<string>> PaysParCellule(TerresDeLaCarte terres) {
            TerrainDeCarte t = FormesDeTest.TerrainDetroits; CarteLue carte = FormesDeTest.CarteDetroits;
            var parCellule = new Dictionary<long, List<string>>();
            for (int l = 0; l < t.NombreDeLieux; l++) {
                long cellule = carte.Cellules[t.CelluleDuLieu(l)].CellId;
                if (!parCellule.TryGetValue(cellule, out List<string> pays)) parCellule[cellule] = pays = new List<string>();
                pays.Add(terres.PaysDuLieu(cellule, t.RangDuLieu(l)));
            }
            return parCellule;
        }

        [Test] public void Le_terrain_des_Detroits_se_leve_sur_les_cinq_cellules() {
            CarteLue carte = FormesDeTest.CarteDetroits; TerrainDeCarte t = FormesDeTest.TerrainDetroits;
            Assert.Greater(carte.Cellules.Count, 0, "la carte des Détroits n'a aucune cellule");
            CollectionAssert.AreEquivalent(
                new[] { FormesDeTest.CONSTANTINOPLE, FormesDeTest.EDIRNE, FormesDeTest.THRACE_NORD, FormesDeTest.THRACE_OUEST, FormesDeTest.BITHYNIE },
                carte.Cellules.Select(c => c.CellId), "les cellules gardées ne sont pas celles du bourg et de ses voisines");
            Assert.AreEqual(carte.Cellules.Count, FormesDeTest.FormesDetroits.Cellules.Count, "une cellule sans formes, ou des formes sans cellule");
            Assert.Greater(t.NombreDeLieux, carte.Cellules.Count, "les cellules sont coupées en lieux : le terrain en a plus que de cellules");
        }

        [Test] public void Le_terrain_des_Detroits_a_des_lieux_de_Byzance_et_des_Ottomans_cote_a_cote() {
            Dictionary<long, List<string>> parCellule = PaysParCellule(EuropeDeTest.TerresEurope);
            List<string> pays = parCellule.Values.SelectMany(p => p).ToList();
            Assert.Greater(pays.Count, 0, "le terrain des Détroits n'a aucun lieu");
            Assert.IsTrue(pays.All(p => p != null), "un lieu du terrain n'a pas de pays dans /terres");
            Assert.Greater(pays.Count(p => p == BYZANCE), 0, "aucun lieu de Byzance");
            Assert.Greater(pays.Count(p => p == OTTOMANS), 0, "aucun lieu ottoman");
            // Dans la cellule du bourg, les deux pays se côtoient ; les voisines de Thrace et de Bithynie sont ottomanes.
            Assert.Contains(BYZANCE, parCellule[FormesDeTest.CONSTANTINOPLE], "la cellule de Constantinople n'a pas de lieu byzantin");
            Assert.Contains(OTTOMANS, parCellule[FormesDeTest.CONSTANTINOPLE], "la cellule de Constantinople n'a pas de lieu ottoman");
            foreach (long voisine in new[] { FormesDeTest.EDIRNE, FormesDeTest.THRACE_NORD, FormesDeTest.THRACE_OUEST, FormesDeTest.BITHYNIE })
                Assert.IsTrue(parCellule[voisine].All(p => p == OTTOMANS), "un lieu de la cellule " + voisine + " n'est pas ottoman");
        }

        [Test] public void Des_terres_vides_ne_donnent_aucun_pays_aux_lieux_des_Detroits() {
            // L'échantillon vide échoue : sans les terres de l'Europe, aucun lieu n'a de pays et le test des deux pays est rouge.
            var vides = new TerresDeLaCarte(0, default(DateDuMonde), new PaysDeLaCarte[0], new TerreLue[0]);
            List<string> pays = PaysParCellule(vides).Values.SelectMany(p => p).ToList();
            Assert.Greater(pays.Count, 0, "le terrain des Détroits n'a aucun lieu");
            Assert.IsTrue(pays.All(p => p == null), "des terres vides ont donné un pays à un lieu");
            Assert.AreEqual(0, pays.Count(p => p == BYZANCE) + pays.Count(p => p == OTTOMANS));
        }
    }
}
