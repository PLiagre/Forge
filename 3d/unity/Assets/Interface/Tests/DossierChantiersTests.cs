using System;
using System.Threading;
using Forge.Pont;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

namespace Forge.Interface.Tests
{
    public sealed class DossierChantiersTests
    {
        const string Rue = "{\"identifiant\":2,\"en_chantier\":true,\"foyers\":3,\"travail_fourni\":25,\"travail_requis\":181}";
        const string Json = "{\"tick\":68,\"date\":{\"annee\":1400,\"jour_de_l_annee\":69},\"cell_id\":10430,\"rues\":[" + Rue + "],\"parcelles\":[],\"batiments\":[]}";
        static string Lire(string json = Json, long cellule = 10430) =>
            DossierChantiers.Decrire(new DocumentDuMonde(json), cellule, "Bar-le-Duc");

        [Test] public void Le_travail_recu_garde_son_unite_sans_promesse_de_delai()
        {
            string texte = Lire();
            StringAssert.StartsWith("Bar-le-Duc · jour 69 de 1400\n", texte);
            StringAssert.Contains("Rue 2 · En chantier", texte);
            StringAssert.Contains("25 / 181 journées de travail", texte);
            StringAssert.Contains("3 foyers", texte);
            StringAssert.Contains("Coût en pièces : non renseigné", texte);
            StringAssert.Contains("Date de fin : non renseignée", texte);
        }
        [Test] public void Un_plan_vide_et_un_ouvrage_acheve_se_distinguent()
        {
            StringAssert.Contains("Aucun ouvrage ajouté au plan", Lire(Json.Replace(Rue, "")));
            StringAssert.Contains("Rue 2 · Achevé", Lire(Json.Replace("true", "false").Replace(":25", ":181")));
            StringAssert.Contains("Parcelle 2", Lire(Json.Replace("\"rues\"", "\"temp\"").Replace("\"parcelles\"", "\"rues\"").Replace("\"temp\"", "\"parcelles\"")));
        }
        [Test] public void Le_mauvais_territoire_et_les_champs_absents_sont_refuses()
        {
            Assert.Throws<ArgumentException>(() => Lire(Json, 10466));
            Assert.Throws<ArgumentException>(() => Lire(Json.Replace("\"travail_fourni\":25,", "")));
            Assert.Throws<ArgumentException>(() => Lire(Json.Replace("\"batiments\":[]", "\"batiments\":null")));
        }
        [Test] public void Les_doublons_et_un_etat_incoherent_ne_deviennent_pas_un_bilan()
        {
            Assert.Throws<ArgumentException>(() => Lire(Json.Replace(Rue, Rue + "," + Rue)));
            Assert.Throws<ArgumentException>(() => Lire(Json.Replace(":25", ":182")));
            Assert.Throws<ArgumentException>(() => Lire(Json.Replace("true", "false")));
            Assert.Throws<ArgumentException>(() => Lire(Json.Replace("true", "null")));
            Assert.Throws<ArgumentException>(() => Lire(Json.Replace(":3", ":0")));
            Assert.Throws<ArgumentException>(() => Lire(Json.Replace(":25", ":-1")));
        }
        [Test] public void Le_releve_du_jour_distingue_absence_zero_et_motif_recu()
        {
            const string Jour = "{\"nature\":\"rue\",\"identifiant\":2,\"bras\":0,\"grain_paye_kg\":0,\"motif_arret\":\"sans_grain\"}";
            string json = Json.Insert(1, "\"chantiers_du_jour\":[" + Jour + "],");
            StringAssert.Contains("0 ouvriers · 0 kg de grain payés", Lire(json));
            StringAssert.Contains("Arrêt : grain insuffisant", Lire(json));
            StringAssert.Contains("Relevé du jour : non renseigné", Lire());
            Assert.Throws<ArgumentException>(() => Lire(json.Replace(Jour, Jour + "," + Jour)));
            Assert.Throws<ArgumentException>(() => Lire(json.Replace("\"bras\":0", "\"bras\":-1")));
            Assert.Throws<ArgumentException>(() => Lire(json.Replace("\"grain_paye_kg\":0", "\"grain_paye_kg\":-1")));
        }
        [Test] public void Les_chantiers_nomment_le_bourg_datent_et_pesent_le_grain()
        {
            const string Jour = "{\"nature\":\"rue\",\"identifiant\":2,\"bras\":3,\"grain_paye_kg\":1234.5,\"motif_arret\":null}";
            string texte = Lire(Json.Insert(1, "\"chantiers_du_jour\":[" + Jour + "],"));
            StringAssert.Contains("Ce jour : 3 ouvriers · 1,23 t de grain payés", texte);
            StringAssert.Contains("12,5 kg de grain payés", Lire(Json.Insert(1, "\"chantiers_du_jour\":[" + Jour.Replace("1234.5", "12.5") + "],")));
            StringAssert.DoesNotContain("Territoire", texte); StringAssert.DoesNotContain("1234", texte); Assert.IsNull(TexteDuMonde.Interdit(texte, "10430"), texte);
            StringAssert.Contains("Date", Assert.Throws<ArgumentException>(() => Lire(Json.Replace("\"date\":{\"annee\":1400,\"jour_de_l_annee\":69},", ""))).Message);
            Assert.AreEqual("Bar-le-Duc · jour 69 de 1400", DossierBourg.Entete("Bar-le-Duc", new DocumentDuMonde(Json)));
            var noms = new NomsDesTerres(_ => LectureLieu.Absent("lieu 10430 : service coupé"));
            Assert.AreEqual("Bourg sans nom (nom en cours de lecture)", DossierBourg.NomDuBourg(noms, 10430, 0));
            Assert.IsTrue(SpinWait.SpinUntil(() => !noms.LectureEnVol, 5000), "la lecture du nom ne finit pas");
            LogAssert.Expect(LogType.Log, "TexteDuMonde : absence déclarée par le monde : lieu 10430 : service coupé");
            Assert.AreEqual("Bourg sans nom (déclaré absent par le monde)", DossierBourg.NomDuBourg(noms, 10430, 0));
        }
    }
}
