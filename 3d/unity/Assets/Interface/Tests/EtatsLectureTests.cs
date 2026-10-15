using System;
using System.Globalization;
using System.Linq;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface.Tests
{
    public sealed class EtatsLectureTests
    {
        GameObject racine;
        Text texte;

        [SetUp] public void Ouvrir()
        {
            racine = new GameObject("Lecture de contrôle");
            texte = SocleInterface.Texte(racine.transform, "Ancienne mesure : 37 kg", 0, 0, 600);
        }

        [TearDown] public void Fermer() => UnityEngine.Object.DestroyImmediate(racine);

        [TestCase(EtatLecture.Attente, "… En attente")]
        [TestCase(EtatLecture.Absence, "— Donnée absente")]
        [TestCase(EtatLecture.Refus, "× Demande refusée")]
        [TestCase(EtatLecture.Panne, "! Le monde ne répond pas")]
        public void ChaqueEtatRemplaceLaMesureAvecSonMotif(EtatLecture etat, string titre)
        {
            EtatsLecture.Afficher(texte, etat, "Motif fourni par la source.");
            Assert.That(texte.text, Is.EqualTo(titre + "\nMotif fourni par la source."));
            Assert.That(texte.text, Does.Not.Contain("37"));
        }

        [Test] public void UneAbsenceNeDevientPasUnZeroEtUneMesureEffaceLEtat()
        {
            EtatsLecture.Mesure(texte, null, "kg");
            Assert.That(texte.text, Does.StartWith("— Donnée absente"));
            Assert.That(texte.text, Does.Not.Contain("0"));
            EtatsLecture.Mesure(texte, 0m, "kg");
            Assert.That(texte.text, Is.EqualTo("0 kg"));
            Assert.That(texte.color, Is.EqualTo(SocleInterface.Couleur("encre")));
        }

        [Test] public void LaMesureConserveLaPrecisionEnFrancais()
        {
            var culture = CultureInfo.CurrentCulture;
            try
            {
                CultureInfo.CurrentCulture = CultureInfo.GetCultureInfo("en-US");
                EtatsLecture.Mesure(texte, -12.3456m, "kg");
                Assert.That(texte.text, Is.EqualTo("-12,3456 kg"));
            }
            finally { CultureInfo.CurrentCulture = culture; }
        }

        [TestCase(null)]
        [TestCase("")]
        [TestCase("   ")]
        public void UneCauseOuUneUniteManquanteEstRefuseeAvantAffichage(string absent)
        {
            Assert.Throws<ArgumentException>(() => EtatsLecture.Afficher(texte, EtatLecture.Refus, absent));
            Assert.Throws<ArgumentException>(() => EtatsLecture.Mesure(texte, 2m, absent));
            Assert.That(texte.text, Is.EqualTo("Ancienne mesure : 37 kg"));
        }

        [Test] public void UnEtatInconnuEstRefuseAvantAffichage()
        {
            Assert.Throws<ArgumentOutOfRangeException>(() => EtatsLecture.Afficher(texte, (EtatLecture)99, "Cause"));
            Assert.That(texte.text, Is.EqualTo("Ancienne mesure : 37 kg"));
        }

        [Test] public void UneCauseLongueResteLisibleEtNePeutPasMasquerDuTexte()
        {
            string cause = string.Join(" ", Enumerable.Repeat("<size=0>Motif fourni</size>", 12));
            EtatsLecture.Afficher(texte, EtatLecture.Panne, cause);
            Assert.That(texte.supportRichText, Is.False);
            Assert.That(texte.text, Does.EndWith(cause));
            Assert.That(texte.rectTransform.rect.height, Is.GreaterThanOrEqualTo(texte.preferredHeight));
        }

        [Test] public void LaGalerieExposeLesQuatreEtatsSansPartieInventee()
        {
            UnityEngine.Object.DestroyImmediate(racine);
            racine = GalerieEtats.Creer();
            var textes = racine.GetComponentsInChildren<Text>().Select(t => t.text).ToArray();
            foreach (var titre in new[] { "… En attente", "— Donnée absente", "× Demande refusée", "! Le monde ne répond pas" })
                Assert.That(textes.Count(t => t.StartsWith(titre)), Is.EqualTo(1), titre);
            Assert.That(textes.Any(t => t.Contains("aucune partie chargée")), Is.True);
        }
    }
}
