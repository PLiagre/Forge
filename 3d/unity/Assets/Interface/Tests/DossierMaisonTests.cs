using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using Forge.Pont;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

namespace Forge.Interface.Tests
{
    public sealed class DossierMaisonTests
    {
        const string Document = "{\"tick\":7,\"date\":{\"annee\":1400,\"jour_de_l_annee\":8},\"id\":\"bar\",\"nom\":\"Bar\",\"sorte\":\"seigneurie\",\"suzerain\":null,\"siege\":{\"nom\":\"Bar-le-Duc\",\"cell_id\":10430,\"rang\":0},\"lieux\":[{\"cell_id\":10430,\"rang\":0}],\"flux_30j\":{\"preleve_kg\":12.5,\"recu_kg\":4,\"du_envoye_kg\":3,\"mange_en_route_kg\":2,\"rendu_kg\":0,\"partis_personnes\":5,\"arrives_personnes\":6},\"absents\":{}}";
        static readonly Func<long, long, string> Temoin = (c, r) => c == 10430 && r == 0 ? "Bar-le-Duc" : "hors du témoin";
        [Test] public void Les_flux_gardent_periode_unites_et_zero_mesure()
        {
            string texte = DossierMaison.Decrire(new DocumentDuMonde(Document), null, Temoin).Replace("\r", "");
            foreach (string attendu in new[] { "jour 8 de 1400", "30 jours", "12,5 kg", "0 kg", "5 personnes", "6 personnes", "Bar-le-Duc", "aucun", "TERRES TENUES\nBar-le-Duc" })
                StringAssert.Contains(attendu, texte);
            StringAssert.Contains("Salaires : non transmis", texte);
        }
        [Test] public void Une_liste_vide_ou_un_flux_manquant_ne_devient_pas_un_bilan()
        {
            Assert.Throws<ArgumentException>(() => DossierMaison.Decrire(new DocumentDuMonde(Document.Replace("[{\"cell_id\":10430,\"rang\":0}]", "[]")), null, Temoin));
            Assert.Throws<ArgumentException>(() => DossierMaison.Decrire(new DocumentDuMonde(Document.Replace("\"rendu_kg\":0,", "")), null, Temoin));
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
        static string D(string json) => DossierMaison.Decrire(new DocumentDuMonde(json), null, Temoin);
        static string Absent(string champ, string valeur) => Complet.Replace(valeur, "\"" + champ + "\":null,")
            .Replace("\"absents\":{}", "\"absents\":{\"" + champ + "\":\"" + champ + " absent pour la maison bar\"}");
        [Test] public void La_part_et_le_grenier_sont_lus_exactement()
        {
            string texte = D(Complet);
            foreach (string attendu in new[] { "Prélèvement : 25 %", "Grenier : bois : 0 kg · nourriture : 1,23 t", "ABSENCES DÉCLARÉES\naucune", "jour 8 de 1400", "12,5 kg", "Salaires : non transmis" })
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
                    return System.Threading.Tasks.Task.FromResult(new DocumentDuMonde(Complet.Replace("\"tick\":7", "\"tick\":" + servi.ToString(System.Globalization.CultureInfo.InvariantCulture)).Replace("\"jour_de_l_annee\":8", "\"jour_de_l_annee\":" + (servi + 1))));
                });
                var suzerain = new LectureDossier(_ => throw new InvalidOperationException("aucun suzerain"));
                var dossier = parent.AddComponent<DossierMaison>();
                dossier.Initialiser(parent.transform, () => "bar", lecture, suzerain, () => publie, new NomsDesTerres(_ => LectureLieu.Absent("hors du témoin")));
                dossier.Pas(0); Assert.AreEqual(0, appels, "feuillet fermé");
                parent.GetComponentsInChildren<UnityEngine.UI.Button>(true).Single(b => b.name == "Terres et comptes").onClick.Invoke();
                dossier.Pas(0); Assert.AreEqual(1, appels); StringAssert.Contains("jour 8 de 1400", dossier.TexteAffiche);
                dossier.Pas(0); dossier.Pas(10); Assert.AreEqual(1, appels, "même tick");
                publie = 8; servi = 8; dossier.Pas(10); Assert.AreEqual(2, appels); StringAssert.Contains("jour 9 de 1400", dossier.TexteAffiche);
                publie = 9; panne = true;
                dossier.Pas(20); Assert.AreEqual(3, appels); StringAssert.Contains("service en panne", dossier.TexteAffiche);
                dossier.Pas(21); Assert.AreEqual(3, appels, "après un échec");
                dossier.Pas(22.1); Assert.AreEqual(4, appels);
                publie = null; panne = false; servi = 9;
                dossier.Pas(24.2); Assert.AreEqual(5, appels);
                Assert.IsNull(lecture.Erreur, "horloge inconnue");
                Assert.IsNotNull(lecture.Document); Assert.AreEqual(9L, lecture.Document.Tick);
                StringAssert.Contains("jour 10 de 1400", dossier.TexteAffiche);
                dossier.Pas(25); Assert.AreEqual(5, appels, "tick inconnu");
                dossier.Pas(26.3); Assert.AreEqual(6, appels);
            }
            finally { UnityEngine.Object.DestroyImmediate(parent); }
        }
        // Lot 889 : les terres par leur nom, la date servie, les masses en kg ou en t ; une absence qui montre un identifiant se tait.
        static string R(string texte, string avant, string apres) { string change = texte.Replace(avant, apres); Assert.AreNotEqual(texte, change, avant); return change; }
        const string Masque = "TexteDuMonde : absence déclarée par le monde : ", Tu = "déclaré absent par le monde";
        [Test] public void Les_comptes_disent_les_terres_par_leur_nom_la_date_et_les_tonnes()
        {
            var noms = new Dictionary<(long, long), string> { [(10430, 0)] = "Bar-le-Duc", [(10430, 2)] = "Longeville", [(10437, 0)] = "Metz", [(10437, 1)] = "Scy" };
            string json = R(R(R(R(Complet, "[{\"cell_id\":10430,\"rang\":0}]", "[{\"cell_id\":10430,\"rang\":0},{\"cell_id\":10430,\"rang\":2},{\"cell_id\":10437,\"rang\":1}]"),
                "\"preleve_kg\":12.5", "\"preleve_kg\":41712"), "\"partis_personnes\":5", "\"partis_personnes\":1"), "\"arrives_personnes\":6", "\"arrives_personnes\":6,\"salaires_payes_kg\":1500");
            string texte = DossierMaison.Decrire(new DocumentDuMonde(json), null, (c, r) => noms[(c, r)]).Replace("\r", "");
            Assert.AreEqual("Bar · seigneurie · jour 8 de 1400", texte.Split('\n')[0]);
            foreach (string attendu in new[] { "TERRES TENUES\nBar-le-Duc\nBar-le-Duc · Longeville\nMetz · Scy\n", "Prélevé : 41,7 t", "Salaires : 1,50 t", "Grenier : bois : 0 kg · nourriture : 1,23 t", "Départs : 1 personne\n", "Arrivées : 6 personnes" })
                StringAssert.Contains(attendu, texte);
            foreach (string refuse in new[] { "Territoire", "lieu 0", "1234" }) StringAssert.DoesNotContain(refuse, texte);
            Assert.IsNull(TexteDuMonde.Interdit(texte, "10430", "10437")); Assert.IsNull(TexteDuMonde.SansUnite(texte));
        }
        [Test] public void Les_noms_absents_la_date_absente_et_les_erreurs_passent_par_l_absence()
        {
            var noms = new NomsDesTerres(cell => cell != 10430 ? LectureLieu.Absent("lieu 10437 : service coupé") : LectureLieu.De(new Lieu(10430, 1, 1400, 1, 1, new Dictionary<string, double>(), 0, 0,
                lieux: new[] { new LieuPlace(0, null, null, nom: "Bar-le-Duc"), new LieuPlace(2, null, null, absenceDuNom: "clé lieux[1].nom : null déclaré") })));
            void Attendre() => Assert.IsTrue(SpinWait.SpinUntil(() => !noms.LectureEnVol, 10000), "la lecture finit");
            Assert.AreEqual("nom en cours de lecture", DossierMaison.NomDuLieu(noms, 10430, 0, 0)); Attendre();
            Assert.AreEqual("Bar-le-Duc", DossierMaison.NomDuLieu(noms, 10430, 0, 0));
            // « rang » est un mot interdit : la raison du rang manquant se tait aussi, le journal la garde.
            LogAssert.Expect(LogType.Log, Masque + "aucun lieu de ce rang dans la terre"); Assert.AreEqual(Tu, DossierMaison.NomDuLieu(noms, 10430, 5, 0));
            LogAssert.Expect(LogType.Log, Masque + "clé lieux[1].nom : null déclaré"); Assert.AreEqual(Tu, DossierMaison.NomDuLieu(noms, 10430, 2, 0));
            Assert.AreEqual("nom en cours de lecture", DossierMaison.NomDuLieu(noms, 10437, 0, 0)); Attendre();
            LogAssert.Expect(LogType.Log, Masque + "lieu 10437 : service coupé"); Assert.AreEqual(Tu, DossierMaison.NomDuLieu(noms, 10437, 0, 0));
            StringAssert.Contains("Date", Assert.Throws<ArgumentException>(() => D(R(Complet, "\"date\":{\"annee\":1400,\"jour_de_l_annee\":8},", ""))).Message);
            Assert.AreEqual("Comptes indisponibles : Date non transmise", DossierMaison.Indisponible("Date non transmise"));
            LogAssert.Expect(LogType.Log, Masque + "Lecture refusée (404) : maison inconnue");
            Assert.AreEqual("Comptes indisponibles : " + Tu, DossierMaison.Indisponible("Lecture refusée (404) : maison inconnue"));
            LogAssert.Expect(LogType.Log, Masque + "nom de maison absent pour la cellule 10430");
            string nom = D(R(R(Complet, "\"nom\":\"Bar\",", "\"nom\":null,"), "\"absents\":{}", "\"absents\":{\"nom\":\"nom de maison absent pour la cellule 10430\"}"));
            StringAssert.Contains("nom : " + Tu, nom); StringAssert.DoesNotContain("10430", nom);
        }
    }
}
