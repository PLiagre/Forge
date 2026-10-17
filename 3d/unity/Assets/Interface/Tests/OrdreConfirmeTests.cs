using System;
using System.Threading.Tasks;
using Forge.Pont;
using NUnit.Framework;

namespace Forge.Interface.Tests
{
    public sealed class OrdreConfirmeTests
    {
        [Test] public async Task Preparer_puis_annuler_ne_depose_rien()
        {
            int envois = 0;
            var ordre = new OrdreConfirme(json => { envois++; return Task.FromResult(RecuIntention.AccepteeAu(3)); });
            Assert.IsTrue(ordre.Preparer("{\"type\":\"fixer_part\"}", "Part de démonstration"));
            Assert.NotNull(ordre.Brouillon);
            ordre.Annuler(); await ordre.Confirmer();
            Assert.AreEqual(0, envois);
            Assert.IsNull(ordre.Brouillon);
        }
        [Test] public async Task Double_confirmation_et_recu_accepte_ne_renvoient_pas_l_ordre()
        {
            int envois = 0;
            var lente = new TaskCompletionSource<RecuIntention>();
            var ordre = new OrdreConfirme(json => { envois++; return lente.Task; });
            ordre.Preparer("{}", "Démonstration");
            Task premier = ordre.Confirmer(); await ordre.Confirmer();
            Assert.IsFalse(ordre.Recommencer());
            lente.SetResult(RecuIntention.AccepteeAu(4)); await premier;
            await ordre.Confirmer();
            Assert.AreEqual(1, envois);
            Assert.AreEqual(4, ordre.Recu.AppliqueeAuTick);
            Assert.IsFalse(ordre.Preparer("{}", "Autre ordre"));
        }
        [Test] public async Task Refus_et_panne_conservent_le_brouillon_sans_nouvel_envoi()
        {
            foreach (bool panne in new[] { false, true })
            {
                int envois = 0;
                var ordre = new OrdreConfirme(json => { envois++; return panne
                    ? Task.FromException<RecuIntention>(new Exception("coupure témoin"))
                    : Task.FromResult(RecuIntention.Refusee(400, "grenier insuffisant")); });
                ordre.Preparer("{}", "Secours témoin"); await ordre.Confirmer(); await ordre.Confirmer();
                Assert.AreEqual(1, envois);
                Assert.AreEqual("{}", ordre.Brouillon);
                Assert.NotNull(ordre.Recu);
                Assert.IsFalse(ordre.Recu.Acceptee);
                Assert.IsFalse(ordre.EnCours);
            }
        }
        [Test] public void Les_saisies_francaises_deviennent_des_unites_du_contrat()
        {
            var part = LecteurJson.LireObjet(OrdresMaison.Part("maison-\"témoin", "25,5"));
            Assert.AreEqual(.255, part["part"]);
            Assert.AreEqual("maison-\"témoin", part["maison"]);
            Assert.AreEqual(2.5, LecteurJson.LireObjet(OrdresMaison.Grenier("témoin", "2.5"))["kg"]);
            foreach (string invalide in new[] { "NaN", "Infinity", "-1", "", "2,3,4" })
                Assert.Throws<ArgumentException>(() => OrdresMaison.Grenier("témoin", invalide));
            Assert.Throws<ArgumentException>(() => OrdresMaison.Part("", "20"));
        }
    }
}
