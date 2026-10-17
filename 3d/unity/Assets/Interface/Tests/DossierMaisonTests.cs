using System;
using NUnit.Framework;
using UnityEngine;

namespace Forge.Interface.Tests
{
    public sealed class DossierMaisonTests
    {
        const string Document = "{\"tick\":7,\"id\":\"bar\",\"nom\":\"Bar\",\"sorte\":\"seigneurie\",\"suzerain\":null,\"siege\":{\"nom\":\"Bar-le-Duc\",\"cell_id\":10430,\"rang\":0},\"lieux\":[{\"cell_id\":10430,\"rang\":0}],\"flux_30j\":{\"preleve_kg\":12.5,\"recu_kg\":4,\"du_envoye_kg\":3,\"mange_en_route_kg\":2,\"rendu_kg\":0,\"partis_personnes\":5,\"arrives_personnes\":6},\"absents\":{}}";
        [Test] public void Les_flux_gardent_periode_unites_et_zero_mesure()
        {
            string texte = DossierMaison.Decrire(new DocumentDuMonde(Document));
            foreach (string attendu in new[] { "tick 7", "30 jours", "12,5 kg", "0 kg", "5 personnes", "6 personnes", "Bar-le-Duc", "aucun", "10430" })
                StringAssert.Contains(attendu, texte);
            StringAssert.Contains("Salaires : non transmis", texte);
        }
        [Test] public void Une_liste_vide_ou_un_flux_manquant_ne_devient_pas_un_bilan()
        {
            Assert.Throws<ArgumentException>(() => DossierMaison.Decrire(new DocumentDuMonde(Document.Replace("[{\"cell_id\":10430,\"rang\":0}]", "[]"))));
            Assert.Throws<ArgumentException>(() => DossierMaison.Decrire(new DocumentDuMonde(Document.Replace("\"rendu_kg\":0,", ""))));
        }
        [Test] public void Le_feuillet_se_reouvre_sans_dupliquer_son_contenu()
        {
            var parent = new GameObject("preuve", typeof(RectTransform));
            try
            {
                var f = parent.AddComponent<Feuillet>(); f.Initialiser(parent.transform, "Comptes");
                f.Ouvrir(); f.Ouvrir(); f.Ecrire(new string('a', 5000));
                Assert.AreEqual(1, parent.GetComponentsInChildren<UnityEngine.UI.ScrollRect>().Length);
                Assert.IsTrue(f.Ouvert); f.Fermer(); Assert.IsFalse(f.Ouvert);
            }
            finally { UnityEngine.Object.DestroyImmediate(parent); }
        }
    }
}
