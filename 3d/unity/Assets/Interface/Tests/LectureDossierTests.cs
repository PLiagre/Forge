using System;
using System.Threading.Tasks;
using NUnit.Framework;

namespace Forge.Interface.Tests
{
    public sealed class LectureDossierTests
    {
        static DocumentDuMonde Doc(int tick) => new DocumentDuMonde("{\"tick\":" + tick + ",\"stock\":0}");
        [Test] public void Un_tick_et_une_quantite_absents_ne_deviennent_pas_zero()
        {
            Assert.Throws<ArgumentException>(() => new DocumentDuMonde("{}"));
            Assert.Throws<ArgumentException>(() => new DocumentDuMonde("{\"tick\":-1}"));
            Assert.Throws<ArgumentException>(() => new DocumentDuMonde("{\"tick\":1.5}"));
            var doc = Doc(7);
            Assert.AreEqual(7, doc.Tick);
            Assert.AreEqual(0, DocumentDuMonde.Nombre(doc.Champs, "stock"));
            Assert.Throws<ArgumentException>(() => DocumentDuMonde.Nombre(doc.Champs, "absent"));
        }
        [Test] public async Task Une_reponse_de_l_ancien_lieu_ne_remplace_pas_le_nouveau()
        {
            var lente = new TaskCompletionSource<DocumentDuMonde>();
            var lecture = new LectureDossier(cle => cle == "ancien" ? lente.Task : Task.FromResult(Doc(8)));
            Task ancien = lecture.Actualiser("ancien");
            await lecture.Actualiser("nouveau");
            lente.SetResult(Doc(2)); await ancien;
            Assert.AreEqual("nouveau", lecture.Cle);
            Assert.AreEqual(8, lecture.Document.Tick);
        }
        [Test] public async Task Une_panne_retire_les_donnees_et_ne_relance_pas_la_requete()
        {
            int appels = 0;
            var lecture = new LectureDossier(cle => ++appels == 1 ? Task.FromResult(Doc(3))
                : Task.FromException<DocumentDuMonde>(new Exception("service coupé")));
            await lecture.Actualiser("lieu");
            Assert.NotNull(lecture.Document);
            await lecture.Actualiser("lieu");
            Assert.IsNull(lecture.Document);
            StringAssert.Contains("service coupé", lecture.Erreur);
            Assert.AreEqual(2, appels);
            Assert.IsFalse(lecture.EnCours);
        }
        [Test] public async Task Une_lecture_en_vol_n_est_pas_doublee_et_le_tick_ne_recule_pas()
        {
            int appels = 0;
            var lente = new TaskCompletionSource<DocumentDuMonde>();
            var lecture = new LectureDossier(cle => ++appels == 1 ? lente.Task : Task.FromResult(Doc(2)));
            Task premiere = lecture.Actualiser("lieu");
            await lecture.Actualiser("lieu");
            Assert.AreEqual(1, appels);
            lente.SetResult(Doc(9)); await premiere;
            await lecture.Actualiser("lieu");
            Assert.AreEqual(9, lecture.Document.Tick);
            StringAssert.Contains("ancien", lecture.Erreur);
        }
        // Lot #871 — la date que le monde a servie, lue telle quelle ; absente, elle reste nulle.
        [Test] public void La_date_servie_est_lue_et_son_absence_reste_nulle()
        {
            var doc = new DocumentDuMonde("{\"tick\":7,\"date\":{\"annee\":1400,\"jour_de_l_annee\":8}}");
            Assert.IsTrue(doc.Annee == 1400 && doc.JourDeLAnnee == 8);
            string chemin = System.IO.Path.Combine(UnityEngine.Application.dataPath, "ForgeLocal3D/Pont/Tests/lieu-graine0-tick3.json");
            var servi = new DocumentDuMonde(System.IO.File.ReadAllText(chemin));
            Assert.IsTrue(servi.Tick == 3 && servi.Annee == 1400 && servi.JourDeLAnnee == 4, chemin);
            var sans = new DocumentDuMonde("{\"tick\":7}");
            Assert.IsTrue(sans.Annee == null && sans.JourDeLAnnee == null, "une date absente n'est ni 0 ni 1400");
            var bornes = new DocumentDuMonde("{\"tick\":7,\"date\":{\"annee\":1,\"jour_de_l_annee\":366}}");
            Assert.IsTrue(bornes.Annee == 1 && bornes.JourDeLAnnee == 366);
            foreach (string date in new[] { "null", "{\"annee\":1400}", "{\"annee\":1400,\"jour_de_l_annee\":0}", "{\"annee\":1400,\"jour_de_l_annee\":367}",
                "{\"annee\":1400,\"jour_de_l_annee\":1.5}", "{\"annee\":0,\"jour_de_l_annee\":8}", "\"1400\"" })
                Assert.Throws<ArgumentException>(() => new DocumentDuMonde("{\"tick\":7,\"date\":" + date + "}"), date);
        }
    }
}
