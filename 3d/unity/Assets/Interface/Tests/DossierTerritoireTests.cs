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

        // Les terres témoins, comme `/terres` les sert sur le monde livré : chaque pays avec sa maison, sauf la terre sans État des Tribus du
        // désert (`sans-etat-desert`), que le monde sert sans maison. Tournai au Hainaut (prince d'Empire, sans suzerain), Avignon aux États de
        // l'Église, Bordeaux à la Guyenne, vassale de l'Angleterre, la terre de Pampelune à la Navarre avec un lieu castillan (rang 2), la terre
        // de Bar-le-Duc au Duché de Bar, vassal de la France, avec un lieu français (rang 2), une terre des Tribus du désert, et une terre sans pays.
        public const long TOURNAI = 20, AVIGNON = 21, BORDEAUX = 22, PAMPELUNE = 23, SANS_PAYS = 24, BAR = 25, DESERT = 26;
        public static TerresDeLaCarte Terres() => new TerresDeLaCarte(8, new DateDuMonde(1400, 9),
            new[] { new PaysDeLaCarte("puissance-60", "Hainaut", new IdentiteDeMaison("grande-60", "Wittelsbach-Straubing"), ensemble: "Saint-Empire"),
                new PaysDeLaCarte("puissance-12", "États de l'Église", new IdentiteDeMaison("institution-12", "États de l'Église")),
                new PaysDeLaCarte("puissance-42", "Guyenne", new IdentiteDeMaison("grande-1", "Lancastre"), suzerain: "puissance-1"), new PaysDeLaCarte("puissance-1", "Angleterre", new IdentiteDeMaison("grande-1", "Lancastre")),
                new PaysDeLaCarte("puissance-7", "Navarre", new IdentiteDeMaison("grande-7", "Évreux")), new PaysDeLaCarte("puissance-5", "Castille", new IdentiteDeMaison("grande-5", "Trastamare")),
                new PaysDeLaCarte("seigneurie-1", "Duché de Bar", new IdentiteDeMaison("seigneurie-1", "Bar"), suzerain: "puissance-3"), new PaysDeLaCarte("puissance-3", "France", new IdentiteDeMaison("grande-3", "Valois")),
                new PaysDeLaCarte("sans-etat-desert", "Tribus du désert") },
            new[] { new TerreLue(TOURNAI, "plausible-20-0", "puissance-60"), new TerreLue(AVIGNON, "institution-12", "puissance-12"), new TerreLue(BORDEAUX, "grande-31", "puissance-42"),
                new TerreLue(PAMPELUNE, "grande-7", "puissance-7", autresPays: new[] { new LieuDAutrePays(2, "plausible-23-2", "puissance-5") }), new TerreLue(SANS_PAYS, null, null),
                new TerreLue(BAR, "seigneurie-1", "seigneurie-1", autresPays: new[] { new LieuDAutrePays(2, "plausible-25-2", "puissance-3") }), new TerreLue(DESERT, "plausible-26-0", "sans-etat-desert") },
            new System.Collections.Generic.Dictionary<string, long> { ["puissance-60"] = 250000, ["puissance-12"] = 61000, ["puissance-42"] = 412300, ["puissance-1"] = 2100000, ["puissance-7"] = 98000,
                ["puissance-5"] = 3400000, ["seigneurie-1"] = 24947, ["puissance-3"] = 9100000, ["sans-etat-desert"] = 51234 });
        // Le dossier `/lieu` d'une terre, avec le bloc `noms` du monde livré : son bourg, tenu par `maitreDuBourg` (une grande maison, sinon
        // la seigneurie de Bar), et un hameau de rang 2 tenu par un seigneur plausible, servi par sa désignation.
        public const string PLAUSIBLE = "Seigneur de la campagne de Tournai, au nord";
        public static DocumentDuMonde Lieu(long cell, string bourg, int tick = 8, long population = 12345, string maitreDuBourg = "grande-60") => new DocumentDuMonde(LieuServi(cell, bourg, tick, population, maitreDuBourg));
        static string LieuServi(long cell, string bourg, int tick = 8, long population = 12345, string maitreDuBourg = "grande-60") => "{\"tick\":" + tick + ",\"cell_id\":" + cell + "," + Date + "\"population\":" + population + ","
            + "\"noms\":{\"maisons\":{\"grande-60\":{\"nom\":\"Wittelsbach-Straubing\",\"prenom_chef\":null,\"sorte\":\"grande maison\"},\"seigneurie-1\":{\"nom\":\"Bar\",\"prenom_chef\":null,\"sorte\":\"seigneurie\"},"
            + "\"plausible-1\":{\"nom\":\"" + PLAUSIBLE + "\",\"prenom_chef\":\"Jean\",\"sorte\":\"plausible\"}}},\"lieux\":["
            + "{\"rang\":0,\"nom\":\"" + bourg + "\",\"population\":12000,\"surface_km2\":12,\"maitre\":\"" + maitreDuBourg + "\",\"stocks\":{\"nourriture\":1234.5},\"flux_30j\":{\"preleve_kg\":2500,\"partis_personnes\":3,\"arrives_personnes\":1}},"
            + "{\"rang\":2,\"nom\":\"Hameau témoin\",\"population\":345,\"surface_km2\":15,\"maitre\":\"plausible-1\",\"stocks\":{\"nourriture\":9},\"flux_30j\":null}]}";
        static string Habitants(long n) => TexteDuMonde.Nombre(n) + " habitants";

        // Le dossier commence par la ligne du pays du lieu, puis le lieu, la province et le seigneur ; il parle en noms, en dates et en unités.
        [Test] public void Le_dossier_dit_le_pays_du_lieu_puis_le_lieu_sa_province_et_son_seigneur()
        {
            string texte = DossierTerritoire.Decrire(Lieu(TOURNAI, "Tournai"), Terres(), TOURNAI, 0); var lignes = texte.Split('\n');
            Assert.That(lignes.Take(5), Is.EqualTo(new[] { "Hainaut · Saint-Empire · " + Habitants(250000),
                "Tournai : " + Habitants(12000) + " dans ce lieu", "Province de Tournai · " + Habitants(12345),
                "Seigneur : maison Wittelsbach-Straubing", "jour 9 de 1400" }), texte);
            foreach (var attendu in new[] { "nourriture : 1,23 t", "nourriture : 9 kg", "Sur 30 jours : 2,50 t prélevés", "3 personnes parties · 1 personne arrivée", "Hameau témoin", "Flux non transmis", "Seigneur local, que l'histoire ne nomme pas" }) StringAssert.Contains(attendu, texte);
            foreach (var interdit in new[] { "rang", "tick", "1234", "Molette", "dans le territoire", "Maison", "Suzerain :", "Ensemble :", "partagée" }) StringAssert.DoesNotContain(interdit, texte);
            Assert.IsNull(TexteDuMonde.Interdit(texte, "10340", "puissance-60", "grande-60", "plausible-1"), texte); Assert.IsNull(TexteDuMonde.SansUnite(texte), texte);
            Assert.AreEqual("Province de Tournai", DossierTerritoire.Titre(Lieu(TOURNAI, "Tournai"), TOURNAI));
            Assert.AreEqual("Province d'Avignon", DossierTerritoire.Titre(Lieu(AVIGNON, "Avignon"), AVIGNON));
            StringAssert.Contains("\nProvince d'Avignon · ", DossierTerritoire.Decrire(Lieu(AVIGNON, "Avignon"), Terres(), AVIGNON, 0));
            Assert.AreEqual(DossierTerritoire.PROVINCE_EN_LECTURE, DossierTerritoire.Titre(null, TOURNAI)); Assert.AreEqual(DossierTerritoire.PROVINCE_EN_LECTURE, DossierTerritoire.Titre(Lieu(TOURNAI, "Tournai"), AVIGNON));
        }

        // Sur Bar-le-Duc, le duché et la province ne se contredisent plus : la ligne du pays compte les seuls habitants du duché, et la province,
        // qui compte toute la terre, nomme les pays de ses lieux. Le lieu français de la terre dit la France, et la même province.
        [Test] public void Une_province_dont_un_lieu_est_d_un_autre_pays_le_nomme()
        {
            var terres = Terres(); var bar = Lieu(BAR, "Bar-le-Duc", population: 49868, maitreDuBourg: "seigneurie-1");
            string province = "Province de Bar-le-Duc · partagée : Duché de Bar et France · " + Habitants(49868);
            Assert.That(DossierTerritoire.Decrire(bar, terres, BAR, 0).Split('\n').Take(4), Is.EqualTo(new[] { "Duché de Bar · vassal de France · " + Habitants(24947),
                "Bar-le-Duc : " + Habitants(12000) + " dans ce lieu", province, "Seigneur : maison Bar" }));
            Assert.That(DossierTerritoire.Decrire(bar, terres, BAR, 2).Split('\n').Take(4), Is.EqualTo(new[] { "France · " + Habitants(9100000),
                "Hameau témoin : " + Habitants(345) + " dans ce lieu", province, "Seigneur local, que l'histoire ne nomme pas" }));
            Assert.That(InfobulleDeTerre.Decrire(null, bar, terres, BAR, 0).Split('\n'), Does.Contain(province), "l'infobulle ne dit pas la même province que la fiche");
            // Une terre dont tous les lieux sont de son pays ne se dit pas partagée ; sans terres lues, la province ne nomme aucun pays.
            Assert.That(DossierTerritoire.PaysDeLaProvince(terres, BAR), Is.EqualTo(new[] { "Duché de Bar", "France" }));
            Assert.That(DossierTerritoire.PaysDeLaProvince(terres, TOURNAI), Is.EqualTo(new[] { "Hainaut" }));
            Assert.That(DossierTerritoire.PaysDeLaProvince(null, BAR), Is.Empty);
            StringAssert.DoesNotContain("partagée", DossierTerritoire.Texte(null, bar, null, BAR, 0));
        }

        // Un seigneur plausible n'est pas une maison de l'histoire : il ne s'écrit jamais « Maison … », ni par le nom que le monde lui sert.
        // Une grande maison et une seigneurie se disent « maison » ; une sorte que le dossier ne sert pas se dit.
        [Test] public void Une_maison_de_sorte_plausible_ne_s_ecrit_jamais_maison()
        {
            string tenu = DossierTerritoire.Decrire(Lieu(TOURNAI, "Tournai", maitreDuBourg: "plausible-1"), Terres(), TOURNAI, 0);
            Assert.That(tenu.Split('\n'), Has.Exactly(3).EqualTo("Seigneur local, que l'histoire ne nomme pas"), tenu);
            StringAssert.DoesNotContain("Maison", tenu); StringAssert.DoesNotContain("maison", tenu); StringAssert.DoesNotContain(PLAUSIBLE, tenu);
            string sansSorte = DossierTerritoire.Decrire(new DocumentDuMonde(LieuServi(TOURNAI, "Tournai").Replace(",\"sorte\":\"grande maison\"", "")), Terres(), TOURNAI, 0);
            StringAssert.Contains("\nSeigneur : Wittelsbach-Straubing, sorte non transmise\n", sansSorte);
            StringAssert.Contains("\nSeigneur : maison Bar\n", DossierTerritoire.Decrire(Lieu(BAR, "Bar-le-Duc", maitreDuBourg: "seigneurie-1"), Terres(), BAR, 0));
        }

        // « de » s'élide devant une voyelle, et ne se double pas devant un nom qui porte déjà sa particule.
        [Test] public void De_s_elide_devant_une_voyelle_et_ne_se_double_pas()
        {
            Assert.That(new[] { "Avignon", "Évreux", "Tournai", "Lancastre-Aquitaine", "de Basse Haie", "d'Armagnac", "Œttingen" }.Select(DossierTerritoire.De),
                Is.EqualTo(new[] { "d'Avignon", "d'Évreux", "de Tournai", "de Lancastre-Aquitaine", "de Basse Haie", "d'Armagnac", "d'Œttingen" }));
            // Un nom qui commence par son article, comme une région sans ville (« Le Souf », « L'île de Jura ») : « le » et « les » se contractent avec « de ».
            Assert.That(new[] { "Le Souf", "La Rochelle", "Les Andelys", "L'île de Jura", "Le Mans" }.Select(DossierTerritoire.De),
                Is.EqualTo(new[] { "du Souf", "de La Rochelle", "des Andelys", "de L'île de Jura", "du Mans" }));
        }

        // Chaque nombre d'habitants dit ce qu'il compte : le lieu, la province, ou le pays qu'il nomme.
        [Test] public void Chaque_nombre_d_habitants_dit_ce_qu_il_compte()
        {
            var terres = Terres(); int vues = 0;
            bool Dit(string ligne, string pays) => ligne.EndsWith(" dans ce lieu") || ligne.Contains(" dans ce lieu · ") || ligne.StartsWith("Province d") || ligne.StartsWith(pays + " · ");
            foreach (var (cell, bourg, rang, pays) in new[] { (TOURNAI, "Tournai", 0L, "Hainaut"), (AVIGNON, "Avignon", 0L, "États de l'Église"), (BORDEAUX, "Bordeaux", 2L, "Guyenne"), (PAMPELUNE, "Pampelune", 2L, "Castille"), (BAR, "Bar-le-Duc", 0L, "Duché de Bar") })
                foreach (string ligne in DossierTerritoire.Decrire(Lieu(cell, bourg), terres, cell, rang).Split('\n').Where(l => l.Contains("habitant")))
                {
                    vues++;
                    Assert.That(Dit(ligne, pays), Is.True, "« " + ligne + " » ne dit pas ce qu'il compte");
                }
            Assert.That(vues, Is.GreaterThanOrEqualTo(20), "échantillon vide");
            // Contre-épreuve : les lignes d'hier, un total de la terre, un nombre nu par lieu et le pays suivi de deux-points, ne passent pas.
            Assert.That(Dit(TexteDuMonde.Nombre(12345) + " habitants dans le territoire", "Hainaut") || Dit(TexteDuMonde.Nombre(345) + " habitants · 15 km²", "Hainaut")
                || Dit("Hainaut : " + Habitants(250000), "Hainaut"), Is.False);
        }

        // Le pays tient sur une ligne : son nom, son suzerain (« vassal de … ») ou son ensemble, puis ses habitants ; un pays sans suzerain ni
        // ensemble ne dit que son nom et ses habitants.
        [Test] public void Le_lieu_d_un_vassal_dit_son_pays_puis_son_suzerain()
        {
            var terres = Terres();
            Assert.That(DossierTerritoire.LignesDuPays(terres, BORDEAUX, 0), Is.EqualTo(new[] { "Guyenne · vassal d'Angleterre · " + Habitants(412300) }));
            Assert.That(DossierTerritoire.LignesDuPays(terres, BAR, 0), Is.EqualTo(new[] { "Duché de Bar · vassal de France · " + Habitants(24947) }));
            Assert.That(DossierTerritoire.LignesDuPays(terres, AVIGNON, 0), Is.EqualTo(new[] { "États de l'Église · " + Habitants(61000) }));
            Assert.That(DossierTerritoire.LignesDuPays(terres, TOURNAI, 0), Is.EqualTo(new[] { "Hainaut · Saint-Empire · " + Habitants(250000) }));
            // Un pays dont le monde ne sert pas les habitants le dit, sans nombre.
            var sansHabitants = new TerresDeLaCarte(8, new DateDuMonde(1400, 9), new[] { new PaysDeLaCarte("p", "Pays témoin", new IdentiteDeMaison("m", "Témoin")) }, new[] { new TerreLue(5, "m", "p") });
            Assert.That(DossierTerritoire.LignesDuPays(sansHabitants, 5, 0), Is.EqualTo(new[] { "Pays témoin · habitants non servis" }));
        }

        // Dans la terre partagée de Pampelune, le lieu castillan dit la Castille, et le bourg la Navarre ; la liste des lieux nomme le pays du lieu qui n'est pas celui du bourg.
        [Test] public void Le_lieu_castillan_de_la_terre_de_Pampelune_dit_la_Castille()
        {
            var terres = Terres(); var lieu = Lieu(PAMPELUNE, "Pampelune");
            var castillan = DossierTerritoire.Decrire(lieu, terres, PAMPELUNE, 2).Split('\n');
            Assert.That(castillan.Take(4), Is.EqualTo(new[] { "Castille · " + Habitants(3400000), "Hameau témoin : " + Habitants(345) + " dans ce lieu",
                "Province de Pampelune · partagée : Navarre et Castille · " + Habitants(12345), "Seigneur local, que l'histoire ne nomme pas" }));
            Assert.That(castillan, Does.Contain("Hameau témoin · Castille")); Assert.That(castillan, Does.Contain("Pampelune"), "le bourg navarrais se nomme seul");
            Assert.That(DossierTerritoire.Decrire(lieu, terres, PAMPELUNE, 0).Split('\n')[0], Is.EqualTo("Navarre · " + Habitants(98000)));
            StringAssert.Contains("Dossier incomplet", DossierTerritoire.Texte(null, lieu, terres, PAMPELUNE, 1));
        }

        // Le monde sert les Tribus du désert comme un pays sans maison : leur terre se dit sans État, sous son nom, et qu'on ne la joue pas,
        // sans habitants ni seigneur présenté comme une maison. Un lieu sans pays le dit aussi. Avant la lecture des terres, le pays attend.
        [Test] public void Une_terre_sans_etat_le_dit_et_l_attente_ne_montre_rien()
        {
            string desert = DossierTerritoire.Decrire(Lieu(DESERT, "Le Souf", maitreDuBourg: "plausible-1"), Terres(), DESERT, 0);
            Assert.That(desert.Split('\n').Take(4), Is.EqualTo(new[] { "Terre sans État · Tribus du désert · on ne la joue pas", "Le Souf : " + Habitants(12000) + " dans ce lieu",
                "Province du Souf · " + Habitants(12345), "Seigneur local, que l'histoire ne nomme pas" }), desert);
            StringAssert.DoesNotContain("aison", desert); StringAssert.DoesNotContain(TexteDuMonde.Nombre(51234), desert);
            Assert.That(DossierTerritoire.Decrire(Lieu(SANS_PAYS, "Bourg libre"), Terres(), SANS_PAYS, 0).Split('\n')[0], Is.EqualTo("Terre sans État · aucun pays ne la tient · on ne la joue pas"));
            Assert.That(InfobulleDeTerre.Decrire(null, Lieu(DESERT, "Le Souf"), Terres(), DESERT, 0), Does.StartWith("Terre sans État · Tribus du désert · on ne la joue pas\n"));
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
