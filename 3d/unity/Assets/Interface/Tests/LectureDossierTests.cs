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
    }
}
