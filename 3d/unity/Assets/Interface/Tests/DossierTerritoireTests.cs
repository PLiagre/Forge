using System;
using Forge.Pont;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using UnityEngine.UI;

namespace Forge.Interface.Tests
{
    public sealed class DossierTerritoireTests
    {
        const string Date = "\"date\":{\"annee\":1400,\"jour_de_l_annee\":9},";
        const string Debut = "{\"tick\":8,\"cell_id\":7," + Date + "\"population\":17,\"lieux\":[";
        const string Premier = "{\"rang\":0,\"nom\":\"Bourg témoin\",\"population\":7,\"surface_km2\":12,\"maitre\":null,\"stocks\":{\"nourriture\":0},\"flux_30j\":null}";
        const string Second = "{\"rang\":2,\"nom\":\"Hameau témoin\",\"population\":10,\"surface_km2\":15,\"maitre\":null,\"stocks\":{\"nourriture\":9},\"flux_30j\":null}";
        // Lot #873 : le dossier parle en noms, en dates et en unités ; ni cellule, ni rang, ni tick.
        [Test] public void Le_dossier_dit_le_bourg_son_maitre_la_date_et_chaque_lieu_par_son_nom()
        {
            string temoin = "{\"tick\":8,\"cell_id\":10340," + Date + "\"population\":12345,\"noms\":{\"maisons\":{\"m-1\":{\"nom\":\"Maison témoin\"}}},\"lieux\":["
                + "{\"rang\":0,\"nom\":\"Bourg témoin\",\"population\":12000,\"surface_km2\":12,\"maitre\":\"m-1\",\"stocks\":{\"nourriture\":1234.5},"
                + "\"flux_30j\":{\"preleve_kg\":2500,\"partis_personnes\":3,\"arrives_personnes\":1}},"
                + "{\"rang\":2,\"nom\":\"Hameau témoin\",\"population\":345,\"surface_km2\":15,\"maitre\":null,\"stocks\":{\"nourriture\":9},\"flux_30j\":null}]}";
            string texte = DossierTerritoire.Decrire(new DocumentDuMonde(temoin), 10340); var lignes = texte.Split('\n');
            Assert.AreEqual("Bourg témoin · Maison : Maison témoin", lignes[0]); Assert.AreEqual("jour 9 de 1400", lignes[1]);
            foreach (var attendu in new[] { "12 345 habitants", "nourriture : 1,23 t", "nourriture : 9 kg", "Sur 30 jours : 2,50 t prélevés", "3 personnes parties · 1 personne arrivée", "Hameau témoin", "Flux non transmis" }) StringAssert.Contains(attendu, texte);
            foreach (var interdit in new[] { "rang", "tick", "1234" }) StringAssert.DoesNotContain(interdit, texte);
            Assert.IsNull(TexteDuMonde.Interdit(texte, "10340"), texte); Assert.IsNull(TexteDuMonde.SansUnite(texte), texte); Assert.AreEqual("Cellule", TexteDuMonde.Interdit("Cellule 10340 · tick 8", "10340"));
        }
        [Test] public void Cellule_incorrecte_rang_duplique_et_echantillon_vide_echouent()
        {
            Assert.Throws<ArgumentException>(() => DossierTerritoire.Decrire(new DocumentDuMonde(Debut + Premier + "]}"), 9));
            Assert.Throws<ArgumentException>(() => DossierTerritoire.Decrire(new DocumentDuMonde(Debut + Premier + "," + Premier + "]}"), 7));
            Assert.Throws<ArgumentException>(() => DossierTerritoire.Decrire(new DocumentDuMonde(Debut + "]}"), 7));
        }
        [Test] public void Bourg_et_date_absents_echouent_et_l_attente_ne_montre_rien()
        {
            StringAssert.Contains("Bourg", Assert.Throws<ArgumentException>(() => DossierTerritoire.Decrire(new DocumentDuMonde(Debut + Second + "]}"), 7)).Message);
            StringAssert.Contains("Date", Assert.Throws<ArgumentException>(() => DossierTerritoire.Decrire(new DocumentDuMonde(Debut.Replace(Date, "") + Premier + "]}"), 7)).Message);
            Assert.AreEqual(DossierTerritoire.ATTENTE, DossierTerritoire.Texte(null, null, 10340)); Assert.IsNull(TexteDuMonde.Interdit(DossierTerritoire.ATTENTE, "10340"));
            const string raison = "Lecture refusée (404) : cell inconnu : reçu 10340"; LogAssert.Expect(LogType.Log, "TexteDuMonde : absence déclarée par le monde : " + raison);
            Assert.AreEqual("Lecture indisponible : déclaré absent par le monde", DossierTerritoire.Texte(raison, null, 10340));
            Assert.AreEqual("Dossier incomplet : déclaré absent par le monde", DossierTerritoire.Texte(null, new DocumentDuMonde(Debut + Premier + "," + Premier + "]}"), 7));
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
