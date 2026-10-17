using System;
using NUnit.Framework;
using UnityEngine;

namespace Forge.Interface.Tests
{
    public sealed class PlanBourgTests
    {
        const string Carre = "[[0,0],[20,0],[20,10],[0,10]]";
        const string Base = "{\"cell_id\":12,\"place\":" + Carre + ",\"maisons\":[{\"emprise\":" + Carre + "}],\"rues\":[{\"points\":[[0,0],[100,0]],\"largeur_m\":6}]}";
        const string Json = "{\"tick\":8,\"cell_id\":12,\"base\":" + Base + ",\"rues\":[],\"parcelles\":[],\"batiments\":[]}";
        [Test] public void Le_trace_possede_son_moteur_de_dessin()
        {
            var objet = new GameObject("Plan", typeof(RectTransform), typeof(DessinBourg));
            try { Assert.That(objet.GetComponent<CanvasRenderer>(), Is.Not.Null); }
            finally { UnityEngine.Object.DestroyImmediate(objet); }
        }
        [Test] public void Le_plan_conserve_les_metres_le_tick_et_le_nord()
        {
            var plan = new PlanBourg(new DocumentDuMonde(Json), 12);
            Assert.That(plan.Tick, Is.EqualTo(8));
            Assert.That(plan.Traces.Count, Is.EqualTo(3));
            Assert.That(plan.Maximum.x, Is.EqualTo(100));
            Assert.That(plan.Maximum.y, Is.EqualTo(10));
            Assert.That(plan.Traces[2].Largeur, Is.EqualTo(6));
            Assert.That(plan.Traces[0].Points[2], Is.EqualTo(new Vector2(20, 10)));
        }
        [Test] public void Une_autre_cellule_ou_un_plan_partiel_ne_se_dessine_pas()
        {
            Assert.Throws<ArgumentException>(() => new PlanBourg(new DocumentDuMonde(Json), 13));
            Assert.Throws<ArgumentException>(() => new PlanBourg(new DocumentDuMonde(Json.Replace(Base, "null")), 12));
            Assert.Throws<ArgumentException>(() => new PlanBourg(new DocumentDuMonde(Json.Replace("\"batiments\"", "\"inconnu\"")), 12));
            Assert.Throws<ArgumentException>(() => new PlanBourg(new DocumentDuMonde(Json.Replace("[100,0]", "[100]")), 12));
            Assert.Throws<ArgumentException>(() => new PlanBourg(new DocumentDuMonde(Json.Replace("largeur_m\":6", "largeur_m\":-1")), 12));
        }
        [Test] public void Un_plan_sans_geometrie_est_refuse_et_un_chantier_reste_signale()
        {
            string vide = Json.Replace(Carre, "[]");
            Assert.Throws<ArgumentException>(() => new PlanBourg(new DocumentDuMonde(vide), 12));
            string chantier = Json.Replace("\"parcelles\":[]", "\"parcelles\":[{\"identifiant\":1,\"contour\":" + Carre + ",\"en_chantier\":true}]");
            Assert.That(new PlanBourg(new DocumentDuMonde(chantier), 12).Traces[3].Nature, Is.EqualTo("chantier"));
        }
    }
}
