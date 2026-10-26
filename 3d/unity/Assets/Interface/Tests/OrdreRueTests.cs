using System;
using NUnit.Framework;
using UnityEngine;

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
    }
}
