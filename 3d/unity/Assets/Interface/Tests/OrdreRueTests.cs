using System;
using Forge.Pont;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

namespace Forge.Interface.Tests
{
    public sealed class OrdreRueTests
    {
        [Test] public void Une_largeur_non_numerique_ne_devient_pas_un_ordre()
        {
            Assert.Throws<ArgumentException>(() => OrdreRue.Creer("bar", 12, new[] { Vector2.zero, Vector2.one }, "NaN", "1"));
        }
        [Test] public void Le_droit_vient_du_maitre_du_bourg_et_de_la_cellule_recue()
        {
            var lieu = new DocumentDuMonde("{\"tick\":4,\"cell_id\":12,\"lieux\":[{\"rang\":0,\"maitre\":\"bar\"},{\"rang\":1,\"maitre\":\"autre\"}]}");
            Assert.That(OrdreRue.Permis(lieu, 12, "bar"), Is.True);
            Assert.That(OrdreRue.Permis(lieu, 12, "autre"), Is.False);
            Assert.That(OrdreRue.Permis(lieu, 13, "bar"), Is.False);
            Assert.That(OrdreRue.Permis(null, 12, "bar"), Is.False);
        }
        [Test] public void Le_trace_transmet_les_metres_et_la_maison_sans_effet_local()
        {
            string json = OrdreRue.Creer("bar\"test", 12, new[] { new Vector2(-2.5f, 3), new Vector2(20, 7) }, "6,5", "2");
            var document = new DocumentDuMonde(json.Insert(1, "\"tick\":0,"));
            Assert.That(DocumentDuMonde.Texte(document.Champs, "maison"), Is.EqualTo("bar\"test"));
            Assert.That(DocumentDuMonde.Nombre(document.Champs, "largeur_m"), Is.EqualTo(6.5));
            Assert.That(DocumentDuMonde.Entier(document.Champs, "foyers"), Is.EqualTo(2));
            var point = (System.Collections.Generic.List<object>)DocumentDuMonde.Tableau(document.Champs, "points")[0];
            Assert.That(point[0], Is.EqualTo(-2.5));
        }
        [Test] public void Un_trace_incomplet_ou_une_quantite_invalide_ne_part_pas()
        {
            var points = new[] { Vector2.zero, Vector2.one };
            Assert.Throws<ArgumentException>(() => OrdreRue.Creer("bar", 12, new[] { Vector2.zero }, "6", "1"));
            Assert.Throws<ArgumentException>(() => OrdreRue.Creer("bar", 12, points, "-1", "1"));
            Assert.Throws<ArgumentException>(() => OrdreRue.Creer("bar", 12, points, "6", "0"));
            Assert.Throws<ArgumentException>(() => OrdreRue.Creer(null, 12, points, "6", "1"));
            Assert.Throws<ArgumentException>(() => OrdreRue.Creer("bar", 12, new[] { Vector2.zero, new Vector2(float.NaN, 0) }, "6", "1"));
        }
        [Test] public void Le_recu_et_le_resume_de_la_rue_nomment_le_bourg_sans_tick()
        {
            string resume = OutilRue.Resume("Mistra", 3, "6", "1");
            Assert.AreEqual("Pointillés : tracé préparé · Mistra · 3 points · largeur 6 m · Foyers : 1. Coût calculé par le monde.", resume);
            string recue = OutilRue.Message(RecuIntention.AccepteeAu(68), "Mistra", 10430);
            Assert.AreEqual("Rue reçue pour Mistra, appliquée au jour suivant. Relisez le plan ; ce reçu ne signifie pas chantier terminé.", recue);
            LogAssert.Expect(LogType.Log, "TexteDuMonde : absence déclarée par le monde : cellule 10430 hors de vos terres");
            string refus = OutilRue.Message(RecuIntention.Refusee(409, "cellule 10430 hors de vos terres"), "Mistra", 10430); Assert.AreEqual("Rue refusée : déclaré absent par le monde", refus);
            string court = OutilRue.Message(RecuIntention.Refusee(400, "tracé trop court"), "Mistra", 10430); Assert.AreEqual("Rue refusée : tracé trop court", court);
            string absente = OutilRue.Message(RecuIntention.Absente("Connexion refusée"), "Mistra", 10430); Assert.AreEqual("Reçu inconnu : Connexion refusée. Vérifiez le plan avant toute nouvelle demande.", absente);
            foreach (string texte in new[] { resume, recue, refus, court, absente }) Assert.IsNull(TexteDuMonde.Interdit(texte, "10430"), texte);
        }
    }
}
