using System;
using System.Collections.Generic;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using NUnit.Framework;
namespace Forge.Pont.Tests
{
    // Un faux service rend /terres, /guerres et /guerres/ordres ; le client relit ce qui est servi, ou nomme la faute.
    public sealed class ClientGuerreTests
    {
        // Les réponses figées du vrai service : une armée de 1 200 hommes en marche vers la terre 10461, puis la prise de cette terre.
        const string EnMarche = "{\"armees\":[{\"avance_km\":40.0,\"cell_id\":10465,\"debut\":2,\"destination\":[10461,0],\"dette_kg\":0.0,\"effectifs\":[[10465,0,300],[10465,1,300],[10465,2,300],[10465,3,300]],\"etapes\":[{\"latitude\":48.1669088,\"longitude\":9.2924595,\"x_m\":4268345.375,\"y_m\":2783959.138}],\"hommes\":1200,\"identifiant\":0,\"maison\":\"seigneurie-2\",\"point\":{\"latitude\":48.776,\"longitude\":9.183,\"x_m\":4260932.34,\"y_m\":2851742.83},\"rang\":0,\"reste_mortalite\":0.0,\"route\":[10461],\"siege\":null,\"vivres_kg\":0.0}],\"date\":{\"annee\":1400,\"jour_de_l_annee\":6},\"guerres\":[{\"agresseur\":\"seigneurie-2\",\"debut\":2,\"defenseur\":\"plausible-10461-0\",\"identifiant\":0}],\"morts_des_armees\":0,\"prises\":[],\"tick\":5}";
        const string Prise = "{\"armees\":[{\"avance_km\":40.0,\"cell_id\":10461,\"debut\":2,\"destination\":null,\"dette_kg\":0.0,\"effectifs\":[[10465,0,300],[10465,1,300],[10465,2,300],[10465,3,300]],\"etapes\":[],\"hommes\":1200,\"identifiant\":0,\"maison\":\"seigneurie-2\",\"point\":{\"latitude\":48.1669088,\"longitude\":9.2924595,\"x_m\":4268345.375,\"y_m\":2783959.138},\"rang\":0,\"reste_mortalite\":0.0,\"route\":[],\"siege\":null,\"vivres_kg\":0.0}],\"date\":{\"annee\":1400,\"jour_de_l_annee\":7},\"guerres\":[{\"agresseur\":\"seigneurie-2\",\"debut\":2,\"defenseur\":\"plausible-10461-0\",\"identifiant\":0}],\"morts_des_armees\":0,\"prises\":[{\"a\":\"seigneurie-2\",\"armee\":0,\"cell_id\":10461,\"de\":\"plausible-10461-0\",\"rangs\":[0,1,2],\"tick\":5}],\"tick\":6}";
        // Les ordres de la maison seigneurie-2 avec la terre 10461 visée et son armée en marche, puis sans terre ni armée.
        const string OrdresEnMarche = "{\"armees\":[{\"assieger\":{\"refus\":\"l'armée marche encore : elle assiège une fois arrivée\"},\"cell_id\":10465,\"destination\":[10461,0],\"hommes\":1200,\"identifiant\":0,\"marche\":{\"jours\":18,\"km\":358.6867608542766,\"refus\":null,\"route\":[10461]},\"rang\":0,\"renvoyer\":{\"hommes\":1200,\"refus\":null,\"vivres_kg\":0.0},\"siege\":null,\"vivres_kg\":0.0}],\"cible\":{\"cell_id\":10461,\"declaration\":{\"refus\":\"vous êtes déjà en guerre avec cette maison\"},\"maitre\":\"plausible-10461-0\"},\"date\":{\"annee\":1400,\"jour_de_l_annee\":6},\"levee\":{\"batiment\":{\"bras_par_jour\":25,\"cell_id\":10465,\"cout_kg\":2400.0,\"journees\":800,\"manque_kg\":0.0,\"nature\":\"caserne\",\"nom\":\"Caserne\",\"refus\":\"une seule caserne par province : la cellule 10465 en a déjà une\"},\"grain_libre_kg\":17084.919665919155,\"lieux\":[{\"cell_id\":10465,\"hommes_max\":320,\"rang\":0},{\"cell_id\":10465,\"hommes_max\":315,\"rang\":1},{\"cell_id\":10465,\"hommes_max\":315,\"rang\":2},{\"cell_id\":10465,\"hommes_max\":314,\"rang\":3}],\"paysans\":78799,\"ration_kg_par_homme_par_jour\":2.5,\"refus\":null},\"maison\":\"seigneurie-2\",\"tick\":5}";
        const string OrdresSansArmee = "{\"armees\":[],\"cible\":null,\"date\":{\"annee\":1400,\"jour_de_l_annee\":3},\"levee\":{\"batiment\":{\"bras_par_jour\":25,\"cell_id\":10465,\"cout_kg\":2400.0,\"journees\":800,\"manque_kg\":0.0,\"nature\":\"caserne\",\"nom\":\"Caserne\",\"refus\":\"une seule caserne par province : la cellule 10465 en a déjà une\"},\"grain_libre_kg\":20380.019646102774,\"lieux\":[{\"cell_id\":10465,\"hommes_max\":619,\"rang\":0},{\"cell_id\":10465,\"hommes_max\":614,\"rang\":1},{\"cell_id\":10465,\"hommes_max\":614,\"rang\":2},{\"cell_id\":10465,\"hommes_max\":614,\"rang\":3}],\"paysans\":79950,\"ration_kg_par_homme_par_jour\":2.5,\"refus\":null},\"maison\":\"seigneurie-2\",\"tick\":2}";
        // Quatre terres, trois pays, dans la forme servie : la maison du pays (sa tête) et la maison de chaque terre (la tête de la suzeraineté de son maître).
        // La terre 10452 est de la maison Wittelsbach mais du pays Saint-Empire, dont la tête est Luxembourg.
        const string Terres = "{\"date\":{\"annee\":1400,\"jour_de_l_annee\":7},\"pays\":[{\"id\":\"puissance-10\",\"maison\":{\"id\":\"grande-9\",\"nom\":\"Luxembourg\"},\"nom\":\"Bohême\",\"suzerain\":null},{\"id\":\"puissance-9\",\"maison\":{\"id\":\"grande-9\",\"nom\":\"Luxembourg\"},\"nom\":\"Saint-Empire\",\"suzerain\":null},{\"id\":\"seigneurie-2\",\"maison\":{\"id\":\"seigneurie-2\",\"nom\":\"Wurtemberg\"},\"nom\":\"Comté de Wurtemberg\",\"suzerain\":\"puissance-9\"}],\"terres\":[{\"cell_id\":10284,\"maison\":\"grande-9\",\"maitre\":\"grande-9\",\"pays\":\"puissance-10\"},{\"cell_id\":10452,\"maison\":\"grande-29\",\"maitre\":\"grande-29\",\"pays\":\"puissance-9\"},{\"cell_id\":10461,\"maison\":\"grande-9\",\"maitre\":\"seigneurie-2\",\"pays\":\"seigneurie-2\"},{\"cell_id\":10465,\"maison\":\"grande-9\",\"maitre\":\"seigneurie-2\",\"pays\":\"seigneurie-2\"}],\"tick\":6}";
        const string Maison = "seigneurie-2";
        const double Delai = 5;
        int port, statut = 200; HttpListener ecoute; Thread fil; readonly List<string> recues = new List<string>();
        [SetUp] public void PortLibre() { var s = new TcpListener(IPAddress.Loopback, 0); s.Start(); port = ((IPEndPoint)s.LocalEndpoint).Port; s.Stop(); lock (recues) recues.Clear(); statut = 200; }
        [TearDown] public void Fermer() { ecoute?.Close(); fil?.Join(TimeSpan.FromSeconds(5)); (ecoute, fil) = (null, null); }
        void Servir(params string[] corps)
        {
            var a = ecoute = new HttpListener(); a.Prefixes.Add("http://127.0.0.1:" + port + "/"); a.Start(); int code = statut;
            (fil = new Thread(() => {
                try { for (int i = 0; ; i++) { var c = a.GetContext(); lock (recues) recues.Add(c.Request.HttpMethod + " " + c.Request.RawUrl);
                    byte[] octets = Encoding.UTF8.GetBytes(corps[Math.Min(i, corps.Length - 1)]); c.Response.StatusCode = code; c.Response.ContentLength64 = octets.Length; c.Response.OutputStream.Write(octets, 0, octets.Length); c.Response.Close(); } }
                catch (Exception) { }
            })).Start();
        }
        string[] Recues() { lock (recues) return recues.ToArray(); }
        ClientGuerre Client() => new ClientGuerre(port, TimeSpan.FromSeconds(Delai));
        static string Muter(string temoin, string ancien, string nouveau)
        {
            int i = temoin.IndexOf(ancien, StringComparison.Ordinal);
            Assert.IsTrue(i >= 0 && temoin.LastIndexOf(ancien, StringComparison.Ordinal) == i, "motif absent ou répété : " + ancien);
            return temoin.Substring(0, i) + nouveau + temoin.Substring(i + ancien.Length);
        }

        [Test] public void Les_terres_se_lisent_telles_que_servies()
        {
            Servir(Terres);
            using (var c = Client())
            {
                var l = c.LireTerres(); Assert.IsTrue(l.Presente && l.Absence == null, l.Absence); var t = l.Donnees;
                Assert.IsTrue(t.Tick == 6 && t.Date.Annee == 1400 && t.Date.JourDeLAnnee == 7);
                CollectionAssert.AreEqual(new[] { (10284L, "grande-9", "puissance-10", "grande-9"), (10452L, "grande-29", "puissance-9", "grande-29"), (10461L, "seigneurie-2", "seigneurie-2", "grande-9"), (10465L, "seigneurie-2", "seigneurie-2", "grande-9") },
                    t.Terres.Select(x => (x.CellId, x.Maitre, x.Pays, x.Maison)).ToArray());
                CollectionAssert.AreEqual(new[] { ("puissance-10", "Bohême", "grande-9", "Luxembourg"), ("puissance-9", "Saint-Empire", "grande-9", "Luxembourg"), ("seigneurie-2", "Comté de Wurtemberg", "seigneurie-2", "Wurtemberg") },
                    t.Pays.Select(x => (x.Id, x.Nom, x.Maison.Id, x.Maison.Nom)).ToArray());
                Assert.AreEqual("seigneurie-2", t.PaysDe(10461)); Assert.AreEqual("Comté de Wurtemberg", t.NomDuPays(t.PaysDe(10461))); Assert.AreEqual("seigneurie-2", t.MaitreDe(10461));
                Assert.IsTrue(t.MaisonDuPays("puissance-10").Id == "grande-9" && t.MaisonDuPays("puissance-10").Nom == "Luxembourg" && t.MaisonDuPays(t.PaysDe(10461)).Nom == "Wurtemberg");
                Assert.AreEqual("grande-29", t.Terres[1].Maison); Assert.AreEqual("grande-9", t.MaisonDuPays(t.PaysDe(10452)).Id);
                Assert.IsNull(t.PaysDe(999)); Assert.IsNull(t.MaitreDe(999)); Assert.IsNull(t.NomDuPays("grande-1")); Assert.IsNull(t.NomDuPays(null)); Assert.IsNull(t.MaisonDuPays("grande-1")); Assert.IsNull(t.MaisonDuPays(null));
                Assert.Throws<NotSupportedException>(() => ((IList<TerreLue>)t.Terres).Add(null));
                Assert.Throws<NotSupportedException>(() => ((IList<PaysDeLaCarte>)t.Pays).Add(null));
            }
            CollectionAssert.AreEqual(new[] { "GET /terres" }, Recues());
        }

        [Test] public void Une_terre_sans_maitre_ni_pays_et_un_pays_sans_nom_ni_maison_sont_des_mesures()
        {
            string corps = Muter(Terres, "\"maison\":\"grande-29\",\"maitre\":\"grande-29\",\"pays\":\"puissance-9\"", "\"maison\":null,\"maitre\":null,\"pays\":null");
            corps = Muter(corps, "\"nom\":\"Saint-Empire\"", "\"nom\":null"); corps = Muter(corps, "\"maison\":{\"id\":\"grande-9\",\"nom\":\"Luxembourg\"},\"nom\":\"Bohême\"", "\"maison\":null,\"nom\":\"Bohême\""); corps = Muter(corps, "\"nom\":\"Wurtemberg\"", "\"nom\":null");
            Servir(corps);
            using (var c = Client())
            {
                var l = c.LireTerres(); Assert.IsTrue(l.Presente, l.Absence); var t = l.Donnees;
                Assert.IsNull(t.PaysDe(10452)); Assert.IsNull(t.MaitreDe(10452)); Assert.IsNull(t.Terres[1].Maison); Assert.IsNull(t.NomDuPays("puissance-9")); Assert.AreEqual(4, t.Terres.Count);
                Assert.IsNull(t.MaisonDuPays("puissance-10")); Assert.AreEqual("grande-9", t.MaisonDuPays("puissance-9").Id); Assert.IsNull(t.MaisonDuPays("seigneurie-2").Nom); Assert.AreEqual("seigneurie-2", t.MaisonDuPays("seigneurie-2").Id);
            }
        }

        [Test] public void Les_guerres_se_lisent_avec_l_armee_en_marche()
        {
            Servir(EnMarche);
            using (var c = Client())
            {
                var l = c.LireGuerres(); Assert.IsTrue(l.Presente && l.Absence == null, l.Absence); var g = l.Donnees;
                Assert.IsTrue(g.Tick == 5 && g.Date.Annee == 1400 && g.Date.JourDeLAnnee == 6 && g.MortsDesArmees == 0 && g.Prises.Count == 0);
                Assert.AreEqual(1, g.Guerres.Count); var guerre = g.Guerres[0];
                Assert.IsTrue(guerre.Identifiant == 0 && guerre.Agresseur == Maison && guerre.Defenseur == "plausible-10461-0" && guerre.Debut == 2);
                Assert.AreEqual(1, g.Armees.Count); var a = g.Armees[0];
                Assert.IsTrue(a.Identifiant == 0 && a.Maison == Maison && a.CellId == 10465 && a.Rang == 0 && a.Hommes == 1200 && a.VivresKg == 0 && a.Siege == null);
                Assert.IsTrue(a.Destination != null && a.Destination.CellId == 10461 && a.Destination.Rang == 0);
                CollectionAssert.AreEqual(new[] { 10461L }, a.Route);
                Assert.IsTrue(a.Point.X == 4260932.34 && a.Point.Y == 2851742.83);
                Assert.AreEqual(1, a.Etapes.Count); Assert.IsTrue(a.Etapes[0].X == 4268345.375 && a.Etapes[0].Y == 2783959.138);
                Assert.Throws<NotSupportedException>(() => ((IList<PointCarte>)a.Etapes).Add(default(PointCarte)));
                Assert.Throws<NotSupportedException>(() => ((IList<long>)a.Route).Add(1));
                Assert.Throws<NotSupportedException>(() => ((IList<ArmeeLue>)g.Armees).Add(null));
            }
            CollectionAssert.AreEqual(new[] { "GET /guerres" }, Recues());
        }

        [Test] public void La_prise_se_lit_sans_destination_ni_etape()
        {
            Servir(Prise);
            using (var c = Client())
            {
                var l = c.LireGuerres(); Assert.IsTrue(l.Presente, l.Absence); var g = l.Donnees;
                Assert.IsTrue(g.Tick == 6 && g.Date.JourDeLAnnee == 7 && g.Prises.Count == 1);
                var p = g.Prises[0]; Assert.IsTrue(p.Armee == 0 && p.CellId == 10461 && p.De == "plausible-10461-0" && p.A == Maison && p.Tick == 5);
                CollectionAssert.AreEqual(new[] { 0L, 1L, 2L }, p.Rangs);
                var a = g.Armees[0]; Assert.IsTrue(a.CellId == 10461 && a.Destination == null && a.Route.Count == 0 && a.Etapes.Count == 0 && a.Point.X == 4268345.375);
                Assert.Throws<NotSupportedException>(() => ((IList<long>)p.Rangs).Add(3));
            }
        }

        [Test] public void Une_prise_d_une_terre_sans_maitre_et_un_siege_servi_sont_lus_tels_quels()
        {
            Servir(Muter(Muter(Prise, "\"de\":\"plausible-10461-0\"", "\"de\":null"), "\"siege\":null", "\"siege\":4"));
            using (var c = Client())
            {
                var l = c.LireGuerres(); Assert.IsTrue(l.Presente, l.Absence);
                Assert.IsNull(l.Donnees.Prises[0].De); Assert.AreEqual(4L, l.Donnees.Armees[0].Siege);
            }
        }

        [Test] public void Les_ordres_se_lisent_avec_la_terre_visee_et_l_armee_en_marche()
        {
            Servir(OrdresEnMarche);
            using (var c = Client())
            {
                var l = c.LireOrdres(Maison, 10461); Assert.IsTrue(l.Presente && l.Absence == null, l.Absence); var o = l.Donnees;
                Assert.IsTrue(o.MaisonId == Maison && o.Tick == 5 && o.Date.Annee == 1400 && o.Date.JourDeLAnnee == 6);
                Assert.IsTrue(o.Levee.Refus == null && o.Levee.Paysans == 78799 && o.Levee.GrainLibreKg == 17084.919665919155 && o.Levee.RationKgParHommeParJour == 2.5);
                CollectionAssert.AreEqual(new[] { (10465L, 0L, 320L), (10465L, 1L, 315L), (10465L, 2L, 315L), (10465L, 3L, 314L) }, o.Levee.Lieux.Select(x => (x.CellId, x.Rang, x.HommesMax)).ToArray());
                var b = o.Levee.Batiment; Assert.IsTrue(b != null && b.Nature == "caserne" && b.Nom == "Caserne" && b.CellId == 10465 && b.Journees == 800 && b.BrasParJour == 25 && b.CoutKg == 2400.0 && b.ManqueKg == 0.0);
                Assert.AreEqual("une seule caserne par province : la cellule 10465 en a déjà une", b.Refus);
                Assert.IsTrue(o.Cible != null && o.Cible.CellId == 10461 && o.Cible.Maitre == "plausible-10461-0" && o.Cible.RefusDeDeclaration == "vous êtes déjà en guerre avec cette maison");
                Assert.AreEqual(1, o.Armees.Count); var a = o.Armees[0];
                Assert.IsTrue(a.Identifiant == 0 && a.CellId == 10465 && a.Rang == 0 && a.Hommes == 1200 && a.VivresKg == 0 && a.Siege == null);
                Assert.IsTrue(a.Destination != null && a.Destination.CellId == 10461 && a.Destination.Rang == 0);
                Assert.IsTrue(a.Marche != null && a.Marche.Jours == 18 && a.Marche.Km == 358.6867608542766 && a.Marche.Refus == null);
                CollectionAssert.AreEqual(new[] { 10461L }, a.Marche.Route);
                Assert.AreEqual("l'armée marche encore : elle assiège une fois arrivée", a.RefusDuSiege);
                Assert.IsTrue(a.RefusDuRenvoi == null && a.HommesRendus == 1200 && a.VivresRendusKg == 0);
                Assert.Throws<NotSupportedException>(() => ((IList<LieuDeLevee>)o.Levee.Lieux).Add(null));
                Assert.Throws<NotSupportedException>(() => ((IList<long>)a.Marche.Route).Add(1));
            }
            CollectionAssert.AreEqual(new[] { "GET /guerres/ordres?maison=seigneurie-2&cell=10461" }, Recues());
        }

        // Le devis de la caserne servi à null (capitale hors de la carte) est une mesure ; un refus nul dit qu'elle serait acceptée.
        [Test] public void Le_devis_de_la_caserne_nul_ou_sans_refus_est_lu_tel_quel()
        {
            string sansRefus = Muter(OrdresSansArmee, "\"refus\":\"une seule caserne par province : la cellule 10465 en a déjà une\"", "\"refus\":null");
            string nul = Muter(OrdresSansArmee, "\"batiment\":{\"bras_par_jour\":25,\"cell_id\":10465,\"cout_kg\":2400.0,\"journees\":800,\"manque_kg\":0.0,\"nature\":\"caserne\",\"nom\":\"Caserne\",\"refus\":\"une seule caserne par province : la cellule 10465 en a déjà une\"}", "\"batiment\":null");
            Servir(sansRefus, nul);
            using (var c = Client())
            {
                var l = c.LireOrdres(Maison, null); Assert.IsTrue(l.Presente, l.Absence);
                Assert.IsTrue(l.Donnees.Levee.Batiment != null && l.Donnees.Levee.Batiment.Refus == null && l.Donnees.Levee.Batiment.Journees == 800);
                l = c.LireOrdres(Maison, null); Assert.IsTrue(l.Presente, l.Absence); Assert.IsNull(l.Donnees.Levee.Batiment);
            }
        }

        // Le grain qui manque est lu tel que le monde le sert, jamais recalculé du coût et du grain libre.
        [Test] public void Le_grain_qui_manque_a_la_caserne_est_lu_tel_quel()
        {
            string manque = Muter(Muter(OrdresSansArmee, "\"manque_kg\":0.0", "\"manque_kg\":615.5"),
                "\"refus\":\"une seule caserne par province : la cellule 10465 en a déjà une\"", "\"refus\":\"grenier insuffisant : 2400 kg de grain demandés, 1784.5 kg disponibles\"");
            Servir(manque);
            using (var c = Client())
            {
                var l = c.LireOrdres(Maison, null); Assert.IsTrue(l.Presente, l.Absence);
                var b = l.Donnees.Levee.Batiment; Assert.AreEqual(615.5, b.ManqueKg); Assert.AreEqual(2400.0, b.CoutKg); StringAssert.StartsWith("grenier insuffisant", b.Refus);
            }
        }

        [Test] public void Sans_terre_ni_armee_la_cible_est_nulle_et_les_armees_vides()
        {
            Servir(OrdresSansArmee);
            using (var c = Client())
            {
                var l = c.LireOrdres(Maison, null); Assert.IsTrue(l.Presente, l.Absence); var o = l.Donnees;
                Assert.IsNull(o.Cible); Assert.AreEqual(0, o.Armees.Count); Assert.IsTrue(o.Tick == 2 && o.Date.JourDeLAnnee == 3 && o.Levee.Lieux.Count == 4 && o.Levee.Lieux[0].HommesMax == 619);
            }
            CollectionAssert.AreEqual(new[] { "GET /guerres/ordres?maison=seigneurie-2" }, Recues());
        }

        [Test] public void Une_terre_visee_sans_maitre_et_une_armee_sans_marche_sont_des_mesures()
        {
            string corps = Muter(Muter(Muter(OrdresEnMarche, "\"maitre\":\"plausible-10461-0\"", "\"maitre\":null"), "\"destination\":[10461,0]", "\"destination\":null"),
                "\"marche\":{\"jours\":18,\"km\":358.6867608542766,\"refus\":null,\"route\":[10461]}", "\"marche\":null");
            Servir(corps);
            using (var c = Client())
            {
                var l = c.LireOrdres(Maison, 10461); Assert.IsTrue(l.Presente, l.Absence);
                Assert.IsNull(l.Donnees.Cible.Maitre); Assert.IsNull(l.Donnees.Armees[0].Destination); Assert.IsNull(l.Donnees.Armees[0].Marche);
            }
        }

        // Une clé absente refuse toute la réponse et nomme son chemin. Chaque clé est renommée dans la réponse figée, une à une.
        [Test] public void Une_cle_absente_des_terres_refuse_la_reponse_et_nomme_son_chemin()
        {
            var fautes = new List<(string corps, string chemin)>
            {
                (Muter(Terres, "\"tick\":6", "\"tickk\":6"), "tick"), (Muter(Terres, "\"annee\":1400", "\"an\":1400"), "date.annee"),
                (Muter(Terres, "\"pays\":[", "\"payss\":["), "pays"), (Muter(Terres, "\"id\":\"puissance-9\"", "\"identifiant\":\"puissance-9\""), "pays[1].id"),
                (Muter(Terres, "\"nom\":\"Saint-Empire\"", "\"noms\":\"Saint-Empire\""), "pays[1].nom"),
                (Muter(Terres, "\"maison\":{\"id\":\"grande-9\",\"nom\":\"Luxembourg\"},\"nom\":\"Bohême\"", "\"maisons\":{\"id\":\"grande-9\",\"nom\":\"Luxembourg\"},\"nom\":\"Bohême\""), "pays[0].maison"),
                (Muter(Terres, "{\"id\":\"grande-9\",\"nom\":\"Luxembourg\"},\"nom\":\"Bohême\"", "{\"identifiant\":\"grande-9\",\"nom\":\"Luxembourg\"},\"nom\":\"Bohême\""), "pays[0].maison.id"),
                (Muter(Terres, "\"nom\":\"Luxembourg\"},\"nom\":\"Bohême\"", "\"noms\":\"Luxembourg\"},\"nom\":\"Bohême\""), "pays[0].maison.nom"),
                (Muter(Terres, "\"terres\":[", "\"terress\":["), "terres"), (Muter(Terres, "\"cell_id\":10461", "\"cell\":10461"), "terres[2].cell_id"),
                (Muter(Terres, "{\"cell_id\":10284,\"maison\":", "{\"cell_id\":10284,\"maisons\":"), "terres[0].maison"),
                (Muter(Terres, "\"cell_id\":10465,\"maison\":\"grande-9\",\"maitre\":\"seigneurie-2\"", "\"cell_id\":10465,\"maison\":\"grande-9\",\"maitres\":\"seigneurie-2\""), "terres[3].maitre"),
                (Muter(Terres, "\"maitre\":\"seigneurie-2\",\"pays\":\"seigneurie-2\"},{\"cell_id\":10465", "\"maitre\":\"seigneurie-2\",\"payss\":\"seigneurie-2\"},{\"cell_id\":10465"), "terres[2].pays"),
            };
            Servir(fautes.Select(f => f.corps).ToArray());
            using (var c = Client())
                foreach (var (corps, chemin) in fautes)
                {
                    var l = c.LireTerres();
                    Assert.IsTrue(!l.Presente && l.Donnees == null && !string.IsNullOrEmpty(l.Absence), chemin + " : lue malgré la faute");
                    StringAssert.StartsWith("terres : ", l.Absence); StringAssert.Contains("clé absente : " + chemin, l.Absence);
                }
        }

        [Test] public void Une_cle_absente_des_guerres_refuse_la_reponse_et_nomme_son_chemin()
        {
            var fautes = new List<(string corps, string chemin)>
            {
                (Muter(EnMarche, "\"tick\":5", "\"tickk\":5"), "tick"), (Muter(EnMarche, "\"jour_de_l_annee\":6", "\"jour\":6"), "date.jour_de_l_annee"),
                (Muter(EnMarche, "\"morts_des_armees\":0", "\"morts\":0"), "morts_des_armees"), (Muter(EnMarche, "\"prises\":[]", "\"prisess\":[]"), "prises"),
                (Muter(EnMarche, "\"defenseur\":", "\"defenseurs\":"), "guerres[0].defenseur"), (Muter(EnMarche, "\"agresseur\":", "\"agresseurs\":"), "guerres[0].agresseur"),
                (Muter(EnMarche, "\"identifiant\":0}],\"morts", "\"id\":0}],\"morts"), "guerres[0].identifiant"), (Muter(EnMarche, "\"identifiant\":0,\"maison\"", "\"id\":0,\"maison\""), "armees[0].identifiant"),
                (Muter(EnMarche, "\"maison\":", "\"maisons\":"), "armees[0].maison"), (Muter(EnMarche, "\"hommes\":1200", "\"gens\":1200"), "armees[0].hommes"),
                (Muter(EnMarche, "\"vivres_kg\":0.0", "\"vivres\":0.0"), "armees[0].vivres_kg"), (Muter(EnMarche, "\"siege\":null", "\"sieges\":null"), "armees[0].siege"),
                (Muter(EnMarche, "\"destination\":[10461,0]", "\"destinations\":[10461,0]"), "armees[0].destination"), (Muter(EnMarche, "\"route\":[10461]", "\"routes\":[10461]"), "armees[0].route"),
                (Muter(EnMarche, "\"point\":{", "\"pointe\":{"), "armees[0].point"),
                (Muter(EnMarche, "\"longitude\":9.183,\"x_m\":", "\"longitude\":9.183,\"xm\":"), "armees[0].point.x_m"),
                (Muter(EnMarche, "\"y_m\":2851742.83", "\"ym\":2851742.83"), "armees[0].point.y_m"),
                (Muter(EnMarche, "\"etapes\":[", "\"etapess\":["), "armees[0].etapes"), (Muter(EnMarche, "\"y_m\":2783959.138", "\"ym\":2783959.138"), "armees[0].etapes[0].y_m"),
                (Muter(EnMarche, "\"x_m\":4268345.375", "\"xm\":4268345.375"), "armees[0].etapes[0].x_m"),
                (Muter(Prise, "\"rangs\":[0,1,2]", "\"rang\":[0,1,2]"), "prises[0].rangs"), (Muter(Prise, "\"de\":\"plausible-10461-0\"", "\"depuis\":\"plausible-10461-0\""), "prises[0].de"),
                (Muter(Prise, "\"a\":\"seigneurie-2\"", "\"vers\":\"seigneurie-2\""), "prises[0].a"), (Muter(Prise, "\"armee\":0", "\"troupe\":0"), "prises[0].armee"),
                (Muter(Prise, "\"tick\":5}", "\"temps\":5}"), "prises[0].tick"),
            };
            Servir(fautes.Select(f => f.corps).ToArray());
            using (var c = Client())
                foreach (var (corps, chemin) in fautes)
                {
                    var l = c.LireGuerres();
                    Assert.IsTrue(!l.Presente && l.Donnees == null && !string.IsNullOrEmpty(l.Absence), chemin + " : lue malgré la faute");
                    StringAssert.StartsWith("guerres : ", l.Absence); StringAssert.Contains("clé absente : " + chemin, l.Absence);
                }
        }

        [Test] public void Une_cle_absente_des_ordres_refuse_la_reponse_et_nomme_son_chemin()
        {
            var fautes = new List<(string corps, string chemin)>
            {
                (Muter(OrdresEnMarche, "\"tick\":5", "\"tickk\":5"), "tick"), (Muter(OrdresEnMarche, "\"maison\":\"seigneurie-2\"", "\"maisons\":\"seigneurie-2\""), "maison"),
                (Muter(OrdresEnMarche, "\"levee\":{", "\"levees\":{"), "levee"), (Muter(OrdresEnMarche, "\"paysans\":78799", "\"gens\":78799"), "levee.paysans"),
                (Muter(OrdresEnMarche, "\"grain_libre_kg\":17084.919665919155", "\"grain\":17084.919665919155"), "levee.grain_libre_kg"),
                (Muter(OrdresEnMarche, "\"ration_kg_par_homme_par_jour\":2.5", "\"ration\":2.5"), "levee.ration_kg_par_homme_par_jour"),
                (Muter(OrdresEnMarche, "\"refus\":null},\"maison\"", "\"refuss\":null},\"maison\""), "levee.refus"),
                (Muter(OrdresEnMarche, "\"batiment\":{", "\"batiments\":{"), "levee.batiment"), (Muter(OrdresEnMarche, "\"journees\":800", "\"jours\":800"), "levee.batiment.journees"),
                (Muter(OrdresEnMarche, "\"cout_kg\":2400.0", "\"cout\":2400.0"), "levee.batiment.cout_kg"), (Muter(OrdresEnMarche, "\"bras_par_jour\":25", "\"bras\":25"), "levee.batiment.bras_par_jour"),
                (Muter(OrdresEnMarche, "\"manque_kg\":0.0", "\"manque\":0.0"), "levee.batiment.manque_kg"),
                (Muter(OrdresEnMarche, "\"nom\":\"Caserne\"", "\"noms\":\"Caserne\""), "levee.batiment.nom"),
                (Muter(OrdresEnMarche, "\"refus\":\"une seule caserne", "\"refuss\":\"une seule caserne"), "levee.batiment.refus"),
                (Muter(OrdresEnMarche, "\"hommes_max\":320", "\"max\":320"), "levee.lieux[0].hommes_max"), (Muter(OrdresEnMarche, "\"lieux\":[", "\"lieuxs\":["), "levee.lieux"),
                (Muter(OrdresEnMarche, "\"cible\":{", "\"cibles\":{"), "cible"), (Muter(OrdresEnMarche, "\"declaration\":{\"refus\":", "\"declarations\":{\"refus\":"), "cible.declaration"),
                (Muter(OrdresEnMarche, "\"maitre\":\"plausible-10461-0\"", "\"maitres\":\"plausible-10461-0\""), "cible.maitre"),
                (Muter(OrdresEnMarche, "\"assieger\":{\"refus\":", "\"assiegeur\":{\"refus\":"), "armees[0].assieger"),
                (Muter(OrdresEnMarche, "\"assieger\":{\"refus\":\"", "\"assieger\":{\"refuss\":\""), "armees[0].assieger.refus"),
                (Muter(OrdresEnMarche, "\"marche\":{", "\"marches\":{"), "armees[0].marche"), (Muter(OrdresEnMarche, "\"jours\":18", "\"duree\":18"), "armees[0].marche.jours"),
                (Muter(OrdresEnMarche, "\"km\":358.6867608542766", "\"distance\":358.6867608542766"), "armees[0].marche.km"),
                (Muter(OrdresEnMarche, "\"refus\":null,\"route\":[10461]", "\"refuss\":null,\"route\":[10461]"), "armees[0].marche.refus"),
                (Muter(OrdresEnMarche, "\"route\":[10461]", "\"routes\":[10461]"), "armees[0].marche.route"),
                (Muter(OrdresEnMarche, "\"renvoyer\":{", "\"renvoyers\":{"), "armees[0].renvoyer"), (Muter(OrdresEnMarche, "\"renvoyer\":{\"hommes\"", "\"renvoyer\":{\"gens\""), "armees[0].renvoyer.hommes"),
                (Muter(OrdresEnMarche, "\"refus\":null,\"vivres_kg\":0.0}", "\"refus\":null,\"vivres\":0.0}"), "armees[0].renvoyer.vivres_kg"),
                (Muter(OrdresEnMarche, "\"renvoyer\":{\"hommes\":1200,\"refus\":null", "\"renvoyer\":{\"hommes\":1200,\"refuss\":null"), "armees[0].renvoyer.refus"),
                (Muter(OrdresEnMarche, "\"siege\":null", "\"sieges\":null"), "armees[0].siege"), (Muter(OrdresEnMarche, "\"destination\":[10461,0]", "\"destinations\":[10461,0]"), "armees[0].destination"),
                (Muter(OrdresEnMarche, "\"armees\":[", "\"armeess\":["), "armees"),
                (Muter(OrdresEnMarche, "\"identifiant\":0", "\"id\":0"), "armees[0].identifiant"), (Muter(OrdresEnMarche, "\"hommes\":1200,\"identifiant\"", "\"gens\":1200,\"identifiant\""), "armees[0].hommes"),
            };
            Servir(fautes.Select(f => f.corps).ToArray());
            using (var c = Client())
                foreach (var (corps, chemin) in fautes)
                {
                    var l = c.LireOrdres(Maison, 10461);
                    Assert.IsTrue(!l.Presente && l.Donnees == null && !string.IsNullOrEmpty(l.Absence), chemin + " : lue malgré la faute");
                    StringAssert.StartsWith("ordres : ", l.Absence); StringAssert.Contains("clé absente : " + chemin, l.Absence);
                }
        }

        [Test] public void Des_terres_incoherentes_sont_refusees()
        {
            var fautes = new List<(string corps, string cle)>
            {
                (Muter(Terres, "\"pays\":\"puissance-9\"}", "\"pays\":\"puissance-30\"}"), "terres[1].pays"),
                (Muter(Terres, "\"cell_id\":10465", "\"cell_id\":10461"), "terres[3].cell_id"),
                (Muter(Terres, "\"id\":\"puissance-9\"", "\"id\":\"puissance-10\""), "pays[1].id"),
                (Muter(Terres, "\"cell_id\":10452", "\"cell_id\":-1"), "terres[1].cell_id"), (Muter(Terres, "\"nom\":\"Saint-Empire\"", "\"nom\":\"\""), "pays[1].nom"),
                (Muter(Terres, "\"maison\":{\"id\":\"grande-9\",\"nom\":\"Luxembourg\"},\"nom\":\"Bohême\"", "\"maison\":3,\"nom\":\"Bohême\""), "pays[0].maison"),
                (Muter(Terres, "{\"id\":\"grande-9\",\"nom\":\"Luxembourg\"},\"nom\":\"Bohême\"", "{\"id\":\"\",\"nom\":\"Luxembourg\"},\"nom\":\"Bohême\""), "pays[0].maison.id"),
                (Muter(Terres, "\"maison\":\"grande-9\",\"maitre\":\"grande-9\"", "\"maison\":7,\"maitre\":\"grande-9\""), "terres[0].maison"),
                (Muter(Terres, "\"maison\":\"grande-9\",\"maitre\":\"grande-9\"", "\"maison\":\"\",\"maitre\":\"grande-9\""), "terres[0].maison"),
            };
            Servir(fautes.Select(f => f.corps).ToArray());
            using (var c = Client())
                foreach (var (corps, cle) in fautes)
                {
                    var l = c.LireTerres();
                    Assert.IsTrue(!l.Presente && !string.IsNullOrEmpty(l.Absence), cle + " : lue malgré la faute"); StringAssert.StartsWith("terres : ", l.Absence); StringAssert.Contains(cle, l.Absence);
                }
        }

        [Test] public void Des_guerres_et_des_ordres_mal_servis_sont_refuses()
        {
            var guerres = new List<(string corps, string cle)>
            {
                (Muter(EnMarche, "\"hommes\":1200", "\"hommes\":1200.5"), "armees[0].hommes"), (Muter(EnMarche, "\"hommes\":1200", "\"hommes\":-1"), "armees[0].hommes"),
                (Muter(EnMarche, "\"destination\":[10461,0]", "\"destination\":[10461]"), "armees[0].destination"), (Muter(EnMarche, "\"destination\":[10461,0]", "\"destination\":[10461,\"0\"]"), "armees[0].destination[1]"),
                (Muter(EnMarche, "\"route\":[10461]", "\"route\":[\"10461\"]"), "armees[0].route[0]"), (Muter(EnMarche, "\"x_m\":4268345.375", "\"x_m\":\"loin\""), "armees[0].etapes[0].x_m"),
                (Muter(EnMarche, "\"vivres_kg\":0.0", "\"vivres_kg\":-3.0"), "armees[0].vivres_kg"), (Muter(EnMarche, "\"maison\":\"seigneurie-2\",\"point\"", "\"maison\":\"\",\"point\""), "armees[0].maison"),
                (Muter(EnMarche, "\"siege\":null", "\"siege\":-1"), "armees[0].siege"), (Muter(EnMarche, "\"armees\":[{", "\"armees\":[7,{"), "armees[0]"),
            };
            Servir(guerres.Select(f => f.corps).ToArray());
            using (var c = Client())
                foreach (var (corps, cle) in guerres)
                {
                    var l = c.LireGuerres();
                    Assert.IsTrue(!l.Presente && !string.IsNullOrEmpty(l.Absence), cle + " : lue malgré la faute"); StringAssert.StartsWith("guerres : ", l.Absence); StringAssert.Contains(cle, l.Absence);
                }
            Fermer(); PortLibre();
            var ordres = new List<(string corps, string cle)>
            {
                (Muter(OrdresEnMarche, "\"maison\":\"seigneurie-2\"", "\"maison\":\"seigneurie-3\""), "maison"), (Muter(OrdresEnMarche, "\"jours\":18", "\"jours\":18.5"), "armees[0].marche.jours"),
                (Muter(OrdresEnMarche, "\"refus\":\"l'armée marche encore : elle assiège une fois arrivée\"", "\"refus\":\"\""), "armees[0].assieger.refus"),
                (Muter(OrdresEnMarche, "\"km\":358.6867608542766", "\"km\":-1.0"), "armees[0].marche.km"), (Muter(OrdresEnMarche, "\"marche\":{\"jours\":18,\"km\":358.6867608542766,\"refus\":null,\"route\":[10461]}", "\"marche\":[]"), "armees[0].marche"),
                (Muter(OrdresEnMarche, "\"cible\":{", "\"cible\":3,\"x\":{"), "cible"),
            };
            Servir(ordres.Select(f => f.corps).ToArray());
            using (var c = Client())
                foreach (var (corps, cle) in ordres)
                {
                    var l = c.LireOrdres(Maison, 10461);
                    Assert.IsTrue(!l.Presente && !string.IsNullOrEmpty(l.Absence), cle + " : lue malgré la faute"); StringAssert.StartsWith("ordres : ", l.Absence); StringAssert.Contains(cle, l.Absence);
                }
        }

        [Test] public void Une_maison_blanche_est_refusee_et_une_maison_reservee_arrive_en_un_seul_parametre()
        {
            const string bizarre = "é /?&=+#";
            Servir(OrdresSansArmee.Replace(Maison, bizarre));
            using (var c = Client())
            {
                Assert.Throws<ArgumentException>(() => c.LireOrdres(" ", null)); Assert.Throws<ArgumentException>(() => c.LireOrdres(null, 3));
                var l = c.LireOrdres(bizarre, null); Assert.IsTrue(l.Presente && l.Donnees.MaisonId == bizarre, l.Absence);
            }
            string valeur = Recues().Single().Substring("GET /guerres/ordres?maison=".Length);
            Assert.AreEqual(bizarre, Uri.UnescapeDataString(valeur), valeur); Assert.IsTrue(valeur.IndexOfAny(new[] { ' ', '/', '?', '&', '=', '+', '#', 'é' }) < 0, valeur);
        }

        [Test] public void Un_service_absent_est_une_absence_qui_nomme_sa_cause()
        {
            using (var c = new ClientGuerre(port, TimeSpan.FromSeconds(5)))
            {
                var terres = c.LireTerres(); var guerres = c.LireGuerres(); var ordres = c.LireOrdres(Maison, 10461);
                Assert.IsTrue(!terres.Presente && terres.Donnees == null); StringAssert.StartsWith("terres : service absent sur 127.0.0.1:" + port, terres.Absence);
                Assert.IsTrue(!guerres.Presente && guerres.Donnees == null); StringAssert.StartsWith("guerres : service absent sur 127.0.0.1:" + port, guerres.Absence);
                Assert.IsTrue(!ordres.Presente && ordres.Donnees == null); StringAssert.StartsWith("ordres : service absent sur 127.0.0.1:" + port, ordres.Absence);
            }
        }

        [Test] public void Un_statut_autre_que_200_est_une_absence_qui_le_nomme()
        {
            statut = 404; Servir("{\"statut\": 404}");
            using (var c = Client())
            {
                var l = c.LireGuerres(); Assert.IsTrue(!l.Presente && l.Donnees == null);
                StringAssert.StartsWith("guerres : statut 404", l.Absence); StringAssert.Contains("{\"statut\": 404}", l.Absence);
                StringAssert.StartsWith("terres : statut 404", c.LireTerres().Absence); StringAssert.StartsWith("ordres : statut 404", c.LireOrdres(Maison, null).Absence);
            }
        }

        // Les phrases du monde sur la guerre portent leurs unités : « 1 200 hommes » et « 0 paysans » passent, « 1 200 » seul non.
        [Test] public void Les_hommes_et_les_paysans_portent_leur_unite()
        {
            Assert.IsNull(TexteDuMonde.SansUnite("1 200 hommes")); Assert.IsNull(TexteDuMonde.SansUnite("0 paysans")); Assert.IsNull(TexteDuMonde.SansUnite("1 200 hommes"));
            Assert.IsNull(TexteDuMonde.SansUnite("1 homme")); Assert.IsNull(TexteDuMonde.SansUnite("1 paysan"));
            Assert.AreEqual("1 200", TexteDuMonde.SansUnite("1 200")); Assert.AreEqual("1 200", TexteDuMonde.SansUnite("1 200 hommesx"));
        }
    }
}
