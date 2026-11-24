using System;
using System.Linq;
using Forge.Pont;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using UnityEngine.UI;

namespace Forge.Interface.Tests
{
    public sealed class DossierTerritoireTests
    {
        const string Date = "\"date\":{\"annee\":1400,\"jour_de_l_annee\":9},";
        const string Debut = "{\"tick\":8,\"cell_id\":7," + Date + "\"population\":17,\"lieux\":[";
        const string Premier = "{\"rang\":0,\"nom\":\"Bourg témoin\",\"population\":7,\"surface_km2\":12,\"maitre\":null,\"stocks\":{\"nourriture\":0},\"flux_30j\":null}";
        const string Second = "{\"rang\":2,\"nom\":\"Hameau témoin\",\"population\":10,\"surface_km2\":15,\"maitre\":null,\"stocks\":{\"nourriture\":9},\"flux_30j\":null}";

        // Les terres témoins, comme `/terres` les sert : Tournai au Hainaut (prince d'Empire, sans suzerain), Avignon aux États de l'Église,
        // Bordeaux à la Guyenne, vassale de l'Angleterre, la terre de Pampelune à la Navarre avec un lieu castillan (rang 2), et une terre sans pays.
        public const long TOURNAI = 20, AVIGNON = 21, BORDEAUX = 22, PAMPELUNE = 23, SANS_PAYS = 24;
        public static TerresDeLaCarte Terres() => new TerresDeLaCarte(8, new DateDuMonde(1400, 9),
            new[] { new PaysDeLaCarte("puissance-60", "Hainaut", ensemble: "Saint-Empire"), new PaysDeLaCarte("puissance-12", "États de l'Église"),
                new PaysDeLaCarte("puissance-42", "Guyenne", suzerain: "puissance-1"), new PaysDeLaCarte("puissance-1", "Angleterre"),
                new PaysDeLaCarte("puissance-7", "Navarre"), new PaysDeLaCarte("puissance-5", "Castille") },
            new[] { new TerreLue(TOURNAI, "plausible-20-0", "puissance-60"), new TerreLue(AVIGNON, "institution-12", "puissance-12"), new TerreLue(BORDEAUX, "grande-31", "puissance-42"),
                new TerreLue(PAMPELUNE, "grande-7", "puissance-7", autresPays: new[] { new LieuDAutrePays(2, "plausible-23-2", "puissance-5") }), new TerreLue(SANS_PAYS, null, null) },
            new System.Collections.Generic.Dictionary<string, long> { ["puissance-60"] = 250000, ["puissance-12"] = 61000, ["puissance-42"] = 412300, ["puissance-1"] = 2100000, ["puissance-7"] = 98000, ["puissance-5"] = 3400000 });
        // Le dossier `/lieu` d'une terre : son bourg (le seigneur local « de Basse Haie ») et un hameau de rang 2, d'un autre maître.
        public static DocumentDuMonde Lieu(long cell, string bourg, int tick = 8) => new DocumentDuMonde("{\"tick\":" + tick + ",\"cell_id\":" + cell + "," + Date + "\"population\":12345,"
            + "\"noms\":{\"maisons\":{\"m-1\":{\"nom\":\"de Basse Haie\"},\"m-2\":{\"nom\":\"de Lerín\"}}},\"lieux\":["
            + "{\"rang\":0,\"nom\":\"" + bourg + "\",\"population\":12000,\"surface_km2\":12,\"maitre\":\"m-1\",\"stocks\":{\"nourriture\":1234.5},\"flux_30j\":{\"preleve_kg\":2500,\"partis_personnes\":3,\"arrives_personnes\":1}},"
            + "{\"rang\":2,\"nom\":\"Hameau témoin\",\"population\":345,\"surface_km2\":15,\"maitre\":\"m-2\",\"stocks\":{\"nourriture\":9},\"flux_30j\":null}]}");

        // Le dossier commence par le pays du lieu, puis le lieu, la province et le seigneur ; il parle en noms, en dates et en unités.
        [Test] public void Le_dossier_dit_le_pays_du_lieu_puis_le_lieu_sa_province_et_son_seigneur()
        {
            string texte = DossierTerritoire.Decrire(Lieu(TOURNAI, "Tournai"), Terres(), TOURNAI, 0); var lignes = texte.Split('\n');
            Assert.That(lignes.Take(7), Is.EqualTo(new[] { "Hainaut", "Ensemble : Saint-Empire", "Hainaut : " + TexteDuMonde.Nombre(250000) + " habitants",
                "Tournai : " + TexteDuMonde.Nombre(12000) + " habitants dans ce lieu", "Province de Tournai : " + TexteDuMonde.Nombre(12345) + " habitants",
                "Seigneur : Maison de Basse Haie", "jour 9 de 1400" }), texte);
            foreach (var attendu in new[] { "nourriture : 1,23 t", "nourriture : 9 kg", "Sur 30 jours : 2,50 t prélevés", "3 personnes parties · 1 personne arrivée", "Hameau témoin", "Flux non transmis", "Seigneur : Maison de Lerín" }) StringAssert.Contains(attendu, texte);
            foreach (var interdit in new[] { "rang", "tick", "1234", "Molette", "dans le territoire", "Maison :" }) StringAssert.DoesNotContain(interdit, texte);
            Assert.IsNull(TexteDuMonde.Interdit(texte, "10340", "puissance-60", "m-1"), texte); Assert.IsNull(TexteDuMonde.SansUnite(texte), texte);
            Assert.AreEqual("Province de Tournai", DossierTerritoire.Titre(Lieu(TOURNAI, "Tournai"), TOURNAI));
            Assert.AreEqual("Province d'Avignon", DossierTerritoire.Titre(Lieu(AVIGNON, "Avignon"), AVIGNON));
            StringAssert.Contains("\nProvince d'Avignon : ",DossierTerritoire.Decrire(Lieu(AVIGNON, "Avignon"), Terres(), AVIGNON, 0));
            Assert.AreEqual(DossierTerritoire.PROVINCE_EN_LECTURE, DossierTerritoire.Titre(null, TOURNAI)); Assert.AreEqual(DossierTerritoire.PROVINCE_EN_LECTURE, DossierTerritoire.Titre(Lieu(TOURNAI, "Tournai"), AVIGNON));
        }

        // « de » s'élide devant une voyelle, et ne se double pas devant un nom qui porte déjà sa particule.
        [Test] public void De_s_elide_devant_une_voyelle_et_ne_se_double_pas()
        {
            Assert.That(new[] { "Avignon", "Évreux", "Tournai", "Lancastre-Aquitaine", "de Basse Haie", "d'Armagnac", "Œttingen" }.Select(DossierTerritoire.De),
                Is.EqualTo(new[] { "d'Avignon", "d'Évreux", "de Tournai", "de Lancastre-Aquitaine", "de Basse Haie", "d'Armagnac", "d'Œttingen" }));
        }

        // Chaque nombre d'habitants dit ce qu'il compte : le lieu, la province, ou le pays qu'il nomme.
        [Test] public void Chaque_nombre_d_habitants_dit_ce_qu_il_compte()
        {
            var terres = Terres(); int vues = 0;
            bool Dit(string ligne, string pays) => ligne.EndsWith(" dans ce lieu") || ligne.Contains(" dans ce lieu · ") || ligne.StartsWith("Province d") || ligne.StartsWith(pays + " : ");
            foreach (var (cell, bourg, rang, pays) in new[] { (TOURNAI, "Tournai", 0L, "Hainaut"), (AVIGNON, "Avignon", 0L, "États de l'Église"), (BORDEAUX, "Bordeaux", 2L, "Guyenne"), (PAMPELUNE, "Pampelune", 2L, "Castille") })
                foreach (string ligne in DossierTerritoire.Decrire(Lieu(cell, bourg), terres, cell, rang).Split('\n').Where(l => l.Contains("habitant")))
                {
                    vues++;
                    Assert.That(Dit(ligne, pays), Is.True, "« " + ligne + " » ne dit pas ce qu'il compte");
                }
            Assert.That(vues, Is.GreaterThanOrEqualTo(16), "échantillon vide");
            // Contre-épreuve : les lignes d'hier, un total de la terre et un nombre nu par lieu, ne passent pas.
            Assert.That(Dit(TexteDuMonde.Nombre(12345) + " habitants dans le territoire", "Hainaut") || Dit(TexteDuMonde.Nombre(345) + " habitants · 15 km²", "Hainaut"), Is.False);
        }

        // Le lieu d'un pays vassal commence par son pays et dit son suzerain ; un pays sans suzerain ni ensemble ne dit que lui-même.
        [Test] public void Le_lieu_d_un_vassal_dit_son_pays_puis_son_suzerain()
        {
            var terres = Terres();
            Assert.That(DossierTerritoire.LignesDuPays(terres, BORDEAUX, 0), Is.EqualTo(new[] { "Guyenne", "Suzerain : Angleterre", "Guyenne : " + TexteDuMonde.Nombre(412300) + " habitants" }));
            Assert.That(DossierTerritoire.LignesDuPays(terres, AVIGNON, 0), Is.EqualTo(new[] { "États de l'Église", "États de l'Église : " + TexteDuMonde.Nombre(61000) + " habitants" }));
            Assert.That(DossierTerritoire.LignesDuPays(terres, TOURNAI, 0)[0], Is.EqualTo("Hainaut"));
            // Un pays dont le monde ne sert pas les habitants le dit, sans nombre.
            var sansHabitants = new TerresDeLaCarte(8, new DateDuMonde(1400, 9), new[] { new PaysDeLaCarte("p", "Pays témoin") }, new[] { new TerreLue(5, "m", "p") });
            Assert.That(DossierTerritoire.LignesDuPays(sansHabitants, 5, 0), Is.EqualTo(new[] { "Pays témoin", "Pays témoin : habitants non servis" }));
        }

        // Dans la terre partagée de Pampelune, le lieu castillan dit la Castille, et le bourg la Navarre ; la liste des lieux nomme le pays du lieu qui n'est pas celui du bourg.
        [Test] public void Le_lieu_castillan_de_la_terre_de_Pampelune_dit_la_Castille()
        {
            var terres = Terres(); var lieu = Lieu(PAMPELUNE, "Pampelune");
            var castillan = DossierTerritoire.Decrire(lieu, terres, PAMPELUNE, 2).Split('\n');
            Assert.That(castillan.Take(5), Is.EqualTo(new[] { "Castille", "Castille : " + TexteDuMonde.Nombre(3400000) + " habitants", "Hameau témoin : " + TexteDuMonde.Nombre(345) + " habitants dans ce lieu",
                "Province de Pampelune : " + TexteDuMonde.Nombre(12345) + " habitants", "Seigneur : Maison de Lerín" }));
            Assert.That(castillan, Does.Contain("Hameau témoin · Castille")); Assert.That(castillan, Does.Contain("Pampelune"), "le bourg navarrais se nomme seul");
            Assert.That(DossierTerritoire.Decrire(lieu, terres, PAMPELUNE, 0).Split('\n')[0], Is.EqualTo("Navarre"));
            StringAssert.Contains("Dossier incomplet", DossierTerritoire.Texte(null, lieu, terres, PAMPELUNE, 1));
        }

        // Une terre sans pays le dit, et dit qu'on ne la joue pas ; avant la lecture des terres, le pays attend.
        [Test] public void Une_terre_sans_etat_le_dit_et_l_attente_ne_montre_rien()
        {
            Assert.That(DossierTerritoire.Decrire(Lieu(SANS_PAYS, "Bourg libre"), Terres(), SANS_PAYS, 0).Split('\n')[0], Is.EqualTo(DossierTerritoire.SANS_ETAT));
            StringAssert.Contains("on ne la joue pas", DossierTerritoire.SANS_ETAT);
            Assert.That(DossierTerritoire.Texte(null, null, null, 10340, 0), Is.EqualTo(DossierTerritoire.PAYS_EN_LECTURE + "\n" + DossierTerritoire.ATTENTE));
            Assert.IsNull(TexteDuMonde.Interdit(DossierTerritoire.ATTENTE, "10340"));
        }

        [Test] public void Cellule_incorrecte_rang_duplique_et_echantillon_vide_echouent()
        {
            Assert.Throws<ArgumentException>(() => DossierTerritoire.Decrire(new DocumentDuMonde(Debut + Premier + "]}"), null, 9, 0));
            Assert.Throws<ArgumentException>(() => DossierTerritoire.Decrire(new DocumentDuMonde(Debut + Premier + "," + Premier + "]}"), null, 7, 0));
            Assert.Throws<ArgumentException>(() => DossierTerritoire.Decrire(new DocumentDuMonde(Debut + "]}"), null, 7, 0));
        }
        [Test] public void Bourg_et_date_absents_echouent_et_les_fautes_se_disent()
        {
            StringAssert.Contains("Bourg", Assert.Throws<ArgumentException>(() => DossierTerritoire.Decrire(new DocumentDuMonde(Debut + Second + "]}"), null, 7, 2)).Message);
            StringAssert.Contains("Date", Assert.Throws<ArgumentException>(() => DossierTerritoire.Decrire(new DocumentDuMonde(Debut.Replace(Date, "") + Premier + "]}"), null, 7, 0)).Message);
            const string raison = "Lecture refusée (404) : cell inconnu : reçu 10340"; LogAssert.Expect(LogType.Log, "TexteDuMonde : absence déclarée par le monde : " + raison);
            Assert.AreEqual(DossierTerritoire.PAYS_EN_LECTURE + "\nLecture indisponible : déclaré absent par le monde", DossierTerritoire.Texte(raison, null, null, 10340, 0));
            Assert.AreEqual(DossierTerritoire.PAYS_EN_LECTURE + "\nDossier incomplet : déclaré absent par le monde", DossierTerritoire.Texte(null, new DocumentDuMonde(Debut + Premier + "," + Premier + "]}"), null, 7, 0));
        }
        [Test] public void Le_contenu_long_defile_dans_un_cadre_qui_arrete_les_clics()
        {
            var racine = new GameObject("Dossier témoin");
            try
            {
                var texte = SocleInterface.Texte(racine.transform, "Test", 0, 0, 400);
                racine.AddComponent<DossierTerritoire>().Initialiser(texte, 18080, () => null);
                var scroll = texte.GetComponentInParent<ScrollRect>();
                Assert.NotNull(scroll);
                Assert.IsFalse(scroll.horizontal);
                Assert.NotNull(scroll.viewport.GetComponent<RectMask2D>());
                Assert.IsTrue(scroll.viewport.GetComponent<Image>().raycastTarget);
                Assert.IsFalse(texte.supportRichText);
            }
            finally { UnityEngine.Object.DestroyImmediate(racine); }
        }
    }
}
