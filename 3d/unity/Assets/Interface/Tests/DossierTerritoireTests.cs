using System;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface.Tests
{
    public sealed class DossierTerritoireTests
    {
        const string Debut = "{\"tick\":8,\"cell_id\":7,\"population\":17,\"lieux\":[";
        const string Premier = "{\"rang\":0,\"nom\":\"Bourg témoin\",\"population\":7,\"surface_km2\":12,\"maitre\":null,\"stocks\":{\"nourriture\":0},\"flux_30j\":null}";
        const string Second = "{\"rang\":2,\"nom\":\"Hameau témoin\",\"population\":10,\"surface_km2\":15,\"maitre\":null,\"stocks\":{\"nourriture\":9},\"flux_30j\":null}";
        [Test] public void Chaque_lieu_garde_son_rang_ses_stocks_et_le_tick_de_la_reponse()
        {
            string texte = DossierTerritoire.Decrire(new DocumentDuMonde(Debut + Premier + "," + Second + "]}"), 7);
            StringAssert.Contains("tick 8", texte);
            StringAssert.Contains("Bourg témoin", texte);
            StringAssert.Contains("7 habitants", texte);
            StringAssert.Contains("nourriture : 0 kg", texte);
            StringAssert.Contains("Hameau témoin", texte);
            StringAssert.Contains("nourriture : 9 kg", texte);
            StringAssert.Contains("Flux non transmis", texte);
        }
        [Test] public void Cellule_incorrecte_rang_duplique_et_echantillon_vide_echouent()
        {
            Assert.Throws<ArgumentException>(() => DossierTerritoire.Decrire(new DocumentDuMonde(Debut + Premier + "]}"), 9));
            Assert.Throws<ArgumentException>(() => DossierTerritoire.Decrire(new DocumentDuMonde(Debut + Premier + "," + Premier + "]}"), 7));
            Assert.Throws<ArgumentException>(() => DossierTerritoire.Decrire(new DocumentDuMonde(Debut + "]}"), 7));
        }
        [Test] public void Le_contenu_long_defile_dans_un_cadre_qui_arrete_les_clics()
        {
            var racine = new GameObject("Dossier témoin");
            try
            {
                var texte = SocleInterface.Texte(racine.transform, "Test", 0, 0, 400);
                racine.AddComponent<DossierTerritoire>().Initialiser(texte, 18080, () => null);
                var scroll = texte.GetComponentInParent<ScrollRect>();
                Assert.NotNull(scroll);
                Assert.IsFalse(scroll.horizontal);
                Assert.NotNull(scroll.viewport.GetComponent<RectMask2D>());
                Assert.IsTrue(scroll.viewport.GetComponent<Image>().raycastTarget);
                Assert.IsFalse(texte.supportRichText);
            }
            finally { UnityEngine.Object.DestroyImmediate(racine); }
        }
    }
}
