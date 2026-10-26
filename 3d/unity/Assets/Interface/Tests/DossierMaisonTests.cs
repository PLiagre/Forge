using System;
using System.Linq;
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
        // Lot 655 : la part, le grenier et les absences déclarées, puis la relecture au tick publié.
        static readonly string Complet = Document.Replace("\"suzerain\":null,", "\"suzerain\":null,\"part\":0.25,\"grenier\":{\"nourriture\":1234.5,\"bois\":0},");
        static string D(string json) => DossierMaison.Decrire(new DocumentDuMonde(json));
        static string Absent(string champ, string valeur) => Complet.Replace(valeur, "\"" + champ + "\":null,")
            .Replace("\"absents\":{}", "\"absents\":{\"" + champ + "\":\"" + champ + " absent pour la maison bar\"}");
        [Test] public void La_part_et_le_grenier_sont_lus_exactement()
        {
            string texte = D(Complet);
            foreach (string attendu in new[] { "Prélèvement : 25 %", "Grenier : bois : 0 kg · nourriture : 1234,5 kg", "ABSENCES DÉCLARÉES\naucune", "tick 7", "12,5 kg", "Salaires : non transmis" })
                StringAssert.Contains(attendu, texte.Replace("\r", ""));
            StringAssert.Contains("Suzerain : aucun\nPrélèvement", texte.Replace("\r", ""));
            StringAssert.Contains("Prélèvement : non transmis", D(Document)); StringAssert.Contains("Grenier : non transmis", D(Document));
        }
        [Test] public void Une_absence_garde_sa_raison_et_une_mesure_n_est_pas_une_absence()
        {
            string part = D(Absent("part", "\"part\":0.25,")), grenier = D(Absent("grenier", "\"grenier\":{\"nourriture\":1234.5,\"bois\":0},"));
            StringAssert.Contains("Prélèvement : absent", part); StringAssert.Contains("part : part absent pour la maison bar", part);
            StringAssert.Contains("Grenier : absent", grenier); StringAssert.Contains("grenier : grenier absent pour la maison bar", grenier);
            StringAssert.DoesNotContain("Grenier : 0", grenier); StringAssert.DoesNotContain("Prélèvement : 0", part);
            string vide = D(Complet.Replace("{\"nourriture\":1234.5,\"bois\":0}", "{}")).Replace("\r", "");
            StringAssert.Contains("Grenier : vide", vide); StringAssert.Contains("ABSENCES DÉCLARÉES\naucune", vide);
            string nom = D(Absent("nom", "\"nom\":\"Bar\","));
            StringAssert.Contains("nom absent", nom); StringAssert.Contains("nom : nom absent pour la maison bar", nom);
            foreach (string refuse in new[] { Complet.Replace("0.25", "null"), Complet.Replace("0.25", "1.5"), Complet.Replace("0.25", "\"0.25\""),
                Complet.Replace("{\"nourriture\":1234.5,\"bois\":0}", "null"), Complet.Replace("\"bois\":0", "\"bois\":-1"),
                Complet.Replace("\"absents\":{}", "\"absents\":{\"lieux\":3}"), Complet.Replace(",\"absents\":{}", "") })
                Assert.Throws<ArgumentException>(() => D(refuse), refuse);
        }
        [Test] public void Le_feuillet_suit_le_tick_publie_et_garde_sa_cadence_apres_un_echec()
        {
            var parent = new GameObject("preuve", typeof(RectTransform));
            try
            {
                int appels = 0; long? publie = 7; long servi = 7; bool panne = false;
                var lecture = new LectureDossier(_ =>
                {
                    appels++;
                    if (panne) throw new InvalidOperationException("service en panne");
                    // Le tick servi reste un entier : l'horloge publiée peut être inconnue sans casser le document.
                    return System.Threading.Tasks.Task.FromResult(new DocumentDuMonde(Complet.Replace("\"tick\":7", "\"tick\":" + servi.ToString(System.Globalization.CultureInfo.InvariantCulture))));
                });
                var suzerain = new LectureDossier(_ => throw new InvalidOperationException("aucun suzerain"));
                var dossier = parent.AddComponent<DossierMaison>();
                dossier.Initialiser(parent.transform, () => "bar", lecture, suzerain, () => publie);
                dossier.Pas(0); Assert.AreEqual(0, appels, "feuillet fermé");
                parent.GetComponentsInChildren<UnityEngine.UI.Button>(true).Single(b => b.name == "Terres et comptes").onClick.Invoke();
                dossier.Pas(0); Assert.AreEqual(1, appels); StringAssert.Contains("tick 7", dossier.TexteAffiche);
                dossier.Pas(0); dossier.Pas(10); Assert.AreEqual(1, appels, "même tick");
                publie = 8; servi = 8; dossier.Pas(10); Assert.AreEqual(2, appels); StringAssert.Contains("tick 8", dossier.TexteAffiche);
                publie = 9; panne = true;
                dossier.Pas(20); Assert.AreEqual(3, appels); StringAssert.Contains("service en panne", dossier.TexteAffiche);
                dossier.Pas(21); Assert.AreEqual(3, appels, "après un échec");
                dossier.Pas(22.1); Assert.AreEqual(4, appels);
                publie = null; panne = false; servi = 9;
                dossier.Pas(24.2); Assert.AreEqual(5, appels);
                Assert.IsNull(lecture.Erreur, "horloge inconnue");
                Assert.IsNotNull(lecture.Document); Assert.AreEqual(9L, lecture.Document.Tick);
                StringAssert.Contains("tick 9", dossier.TexteAffiche);
                dossier.Pas(25); Assert.AreEqual(5, appels, "tick inconnu");
                dossier.Pas(26.3); Assert.AreEqual(6, appels);
            }
            finally { UnityEngine.Object.DestroyImmediate(parent); }
        }
    }
}
