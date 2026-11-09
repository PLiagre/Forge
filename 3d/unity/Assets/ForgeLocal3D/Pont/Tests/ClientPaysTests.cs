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
    // Lot #1032 — un faux service rend /pays?maison= ; le client relit les jauges, les points et les poses, ou nomme la faute.
    public sealed class ClientPaysTests
    {
        const string Id = "seigneurie-1";
        const string Concorde = "\"concorde\":{\"dit\":\"si le pays tient ensemble : la stabilité\",\"maximum\":3,\"minimum\":-3,\"neutre\":0,\"nom\":\"Concorde\",\"valeur\":0}";
        const string Droit = "\"droit\":{\"dit\":\"ce qui fonde le souverain : la légitimité\",\"maximum\":100,\"minimum\":0,\"neutre\":50,\"nom\":\"Droit\",\"valeur\":60}";
        const string Renom = "\"renom\":{\"dit\":\"ce qu'on dit du pays et de sa dynastie : le prestige\",\"maximum\":100,\"minimum\":0,\"neutre\":0,\"nom\":\"Renom\",\"valeur\":0}";
        const string Epee = "\"epee\":{\"dit\":\"combattre\",\"domaine\":\"guerre\",\"nom\":\"Épée\",\"par_mois\":3.5,\"plafond\":999,\"valeur\":7.0}";
        const string Plume = "\"plume\":{\"dit\":\"administrer\",\"domaine\":\"gestion\",\"nom\":\"Plume\",\"par_mois\":5.0,\"plafond\":999,\"valeur\":10.0}";
        const string Sceau = "\"sceau\":{\"dit\":\"traiter\",\"domaine\":\"diplomatie\",\"nom\":\"Sceau\",\"par_mois\":4.5,\"plafond\":999,\"valeur\":9.0}";
        const string Pose = "{\"identifiant\":\"jauge-droit\",\"nom\":\"Droit (+60)\",\"grandeur\":\"prelevement\",\"valeur\":0.02,\"source\":\"jauge:droit:seigneurie-1\",\"cible\":{\"type\":\"pays\",\"maison\":\"seigneurie-1\"},\"debut\":31,\"fin\":null}";
        // Bar au tick 31 (le mois des points est passé), son Droit à 60 : il pose +2 % sur le prélèvement. Les lieux, les totaux et les bâtiments, que le client ne lit pas, ne sont pas servis.
        const string Temoin = "{\"maison\":{\"id\":\"seigneurie-1\",\"nom\":\"Bar\",\"sorte\":\"seigneurie\"},\"tick\":31,\"date\":{\"annee\":1400,\"jour_de_l_annee\":32},"
            + "\"jauges\":{\"absents\":{},\"competences\":{\"diplomatie\":9,\"gestion\":10,\"guerre\":7},\"grandeurs\":{\"commerce\":\"Commerce\",\"departs\":\"Départs\",\"prelevement\":\"Prélèvement\"},"
            + "\"jauges\":{" + Concorde + "," + Droit + "," + Renom + "},\"modificateurs\":[" + Pose + "],\"points\":{" + Epee + "," + Plume + "," + Sceau + "}}}";
        // Lot #1045 : le pays de grande-3 au tick 31, tel que `/pays` le sert hors des jauges : deux vassaux directs, un arrière-vassal, sept lieux, deux bâtiments.
        const string TemoinTerres = "{\"maison\":{\"id\":\"grande-3\",\"nom\":\"Valois\",\"sorte\":\"grande\"},\"tick\":31,\"date\":{\"annee\":1400,\"jour_de_l_annee\":32},\"suzerain\":null,"
            + "\"vassaux\":[\"seigneurie-1\",\"plausible-7-0\"],\"vassaux_tous\":[\"seigneurie-1\",\"plausible-7-0\",\"plausible-8-1\"],"
            + "\"lieux\":[{\"cell_id\":10,\"rang\":0},{\"cell_id\":10,\"rang\":1},{\"cell_id\":10,\"rang\":2},{\"cell_id\":11,\"rang\":1}],"
            + "\"lieux_des_vassaux\":[{\"cell_id\":12,\"rang\":0},{\"cell_id\":13,\"rang\":0},{\"cell_id\":13,\"rang\":3}],"
            + "\"totaux\":{\"lieux\":7,\"habitants\":2450344,\"habitants_propres\":271528,\"recolte_30j_kg\":141439858.6,\"grenier_nourriture_kg\":754362.1,\"greniers_des_vassaux_kg\":6862501.4,\"chantiers\":2},"
            + "\"absents\":{},"
            + "\"batiments\":[{\"identifiant\":1,\"nature\":\"moulin\",\"nom\":\"Moulin\",\"cell_id\":10,\"maison\":\"grande-3\",\"travail_requis\":600,\"travail_fourni\":600,\"en_chantier\":false,\"debut\":5,\"fin\":605},"
            + "{\"identifiant\":2,\"nature\":\"moulin\",\"nom\":\"Moulin\",\"cell_id\":12,\"maison\":\"seigneurie-1\",\"travail_requis\":600,\"travail_fourni\":20,\"en_chantier\":true,\"debut\":30,\"fin\":null}]}";
        int port; HttpListener ecoute; Thread fil; readonly List<string> recues = new List<string>();
        [SetUp] public void PortLibre() { var s = new TcpListener(IPAddress.Loopback, 0); s.Start(); port = ((IPEndPoint)s.LocalEndpoint).Port; s.Stop(); lock (recues) recues.Clear(); }
        [TearDown] public void Fermer() { ecoute?.Close(); fil?.Join(TimeSpan.FromSeconds(5)); (ecoute, fil) = (null, null); }
        void Servir(params string[] corps)
        {
            var a = ecoute = new HttpListener(); a.Prefixes.Add("http://127.0.0.1:" + port + "/"); a.Start();
            (fil = new Thread(() => {
                try { for (int i = 0; ; i++) { var c = a.GetContext(); lock (recues) recues.Add(c.Request.HttpMethod + " " + c.Request.RawUrl);
                    byte[] octets = Encoding.UTF8.GetBytes(corps[Math.Min(i, corps.Length - 1)]); c.Response.StatusCode = 200; c.Response.ContentLength64 = octets.Length; c.Response.OutputStream.Write(octets, 0, octets.Length); c.Response.Close(); } }
                catch (Exception) { }
            })).Start();
        }
        static string Muter(string ancien, string nouveau)
        {
            int i = Temoin.IndexOf(ancien, StringComparison.Ordinal);
            Assert.IsTrue(i >= 0 && Temoin.LastIndexOf(ancien, StringComparison.Ordinal) == i, "motif absent ou répété : " + ancien);
            return Temoin.Substring(0, i) + nouveau + Temoin.Substring(i + ancien.Length);
        }
        static string Premier(string texte, string ancien, string nouveau) { int i = texte.IndexOf(ancien, StringComparison.Ordinal); return texte.Substring(0, i) + nouveau + texte.Substring(i + ancien.Length); }
        static string SansChef() => Muter("\"absents\":{}", "\"absents\":{\"competences\":\"chef de la maison seigneurie-1 non connu : aucun point\"}")
            .Replace("\"competences\":{\"diplomatie\":9,\"gestion\":10,\"guerre\":7}", "\"competences\":null").Replace("\"par_mois\":3.5", "\"par_mois\":null").Replace("\"par_mois\":5.0", "\"par_mois\":null").Replace("\"par_mois\":4.5", "\"par_mois\":null");

        [Test] public void Le_pays_se_lit_avec_ses_jauges_ses_points_et_ses_poses()
        {
            Servir(Temoin);
            using (var c = new ClientPays(port, TimeSpan.FromSeconds(5)))
            {
                var l = c.Lire(Id); Assert.IsTrue(l.Presente && l.Absence == null, l.Absence); var p = l.Donnees;
                Assert.IsTrue(p.MaisonId == Id && p.Nom == "Bar" && p.Tick == 31 && p.Date.Annee == 1400 && p.Date.JourDeLAnnee == 32 && p.SansChef == null);
                Assert.AreEqual(new[] { "concorde", "droit", "renom" }, p.Jauges.Keys.OrderBy(k => k).ToArray());
                var d = p.Jauges["droit"]; Assert.IsTrue(d.Nom == "Droit" && d.Dit == "ce qui fonde le souverain : la légitimité" && d.Valeur == 60 && d.Minimum == 0 && d.Maximum == 100 && d.Neutre == 50);
                Assert.AreEqual(-3, p.Jauges["concorde"].Minimum);
                Assert.AreEqual(new[] { "epee", "plume", "sceau" }, p.Points.Keys.OrderBy(k => k).ToArray());
                var plume = p.Points["plume"]; Assert.IsTrue(plume.Nom == "Plume" && plume.Dit == "administrer" && plume.Valeur == 10 && plume.Plafond == 999 && plume.Domaine == "gestion" && plume.ParMois == 5);
                Assert.AreEqual(4.5, p.Points["sceau"].ParMois); Assert.AreEqual(3.5, p.Points["epee"].ParMois);
                Assert.IsTrue(p.Competences["gestion"] == 10 && p.Competences["diplomatie"] == 9 && p.Competences["guerre"] == 7 && p.Competences.Count == 3);
                Assert.AreEqual(1, p.Poses.Count); var pose = p.Poses[0];
                Assert.IsTrue(pose.Grandeur == "prelevement" && pose.NomDeLaGrandeur == "Prélèvement" && pose.Valeur == 0.02 && pose.Jauge == "droit");
                Assert.Throws<NotSupportedException>(() => ((IDictionary<string, JaugeLue>)p.Jauges).Add("x", null));
            }
            CollectionAssert.AreEqual(new[] { "GET /pays?maison=seigneurie-1" }, Recues());
        }
        string[] Recues() { lock (recues) return recues.ToArray(); }

        [Test] public void Sans_chef_le_gain_est_absent_pas_nul()
        {
            Servir(SansChef());
            using (var c = new ClientPays(port, TimeSpan.FromSeconds(5)))
            {
                var l = c.Lire(Id); Assert.IsTrue(l.Presente, l.Absence); var p = l.Donnees;
                Assert.IsNull(p.Competences); Assert.AreEqual("chef de la maison seigneurie-1 non connu : aucun point", p.SansChef);
                Assert.IsTrue(p.Points.Count == 3 && p.Points.Values.All(x => x.ParMois == null), "un gain absent ne se lit jamais comme 0");
                Assert.AreEqual(10, p.Points["plume"].Valeur);
            }
        }

        [Test] public void Un_pays_mal_servi_est_refuse()
        {
            var fautes = new List<(string corps, string cle)>
            {
                (Temoin.Replace("\"tick\":31,", ""), "clé absente : tick"), (Muter("\"tick\":31", "\"tick\":-1"), "tick"), (Muter("\"tick\":31", "\"tick\":31.5"), "tick"),
                (Muter("\"id\":\"seigneurie-1\"", "\"id\":\"seigneurie-9\""), "maison.id"), (Muter("\"nom\":\"Bar\"", "\"nom\":\"\""), "maison.nom"),
                (Muter("\"dit\":\"administrer\"", "\"dit\":\"\""), "jauges.points.plume.dit"), (Muter("\"dit\":\"si le pays tient ensemble : la stabilité\"", "\"dit\":\" \""), "jauges.jauges.concorde.dit"),
                (Muter("\"nom\":\"Concorde\",\"valeur\":0", "\"nom\":\"Concorde\",\"valeur\":4"), "jauges.jauges.concorde.valeur"), (Muter("\"neutre\":50,", ""), "droit.neutre"),
                (Muter("\"valeur\":10.0", "\"valeur\":-1"), "jauges.points.plume.valeur"),
                (Muter("\"competences\":{\"diplomatie\":9,\"gestion\":10,\"guerre\":7}", "\"competences\":null"), "absents.competences"),
                (Muter("\"absents\":{}", "\"absents\":{\"competences\":\"chef non connu\"}"), "absents.competences"),
                (Muter("\"par_mois\":3.5", "\"par_mois\":null"), "epee.par_mois"), (Premier(SansChef(), "\"par_mois\":null", "\"par_mois\":2"), "par_mois"),
                (Muter("\"domaine\":\"guerre\"", "\"domaine\":\"magie\""), "epee.domaine"), (Muter("\"gestion\":10", "\"gestion\":-1"), "competences.gestion"),
                (Muter("\"source\":\"jauge:droit:seigneurie-1\"", "\"source\":\"jauge:droit:seigneurie-2\""), "source"), (Muter("\"source\":\"jauge:droit:seigneurie-1\"", "\"source\":\"jauge:ardeur:seigneurie-1\""), "source"),
                (Muter("\"grandeur\":\"prelevement\"", "\"grandeur\":\"natalite\""), "grandeur"), (Muter("\"grandeurs\":{\"commerce\"", "\"grandeurs_\":{\"commerce\""), "grandeurs"),
                (Muter("\"valeur\":0.02", "\"valeur\":\"2 %\""), "valeur"),
            };
            Servir(fautes.Select(f => f.corps).ToArray());
            using (var c = new ClientPays(port, TimeSpan.FromSeconds(5)))
                foreach (var (corps, cle) in fautes)
                {
                    var l = c.Lire(Id);
                    Assert.IsTrue(!l.Presente && l.Donnees == null && !string.IsNullOrEmpty(l.Absence), cle + " : lue malgré la faute");
                    StringAssert.StartsWith("pays : ", l.Absence); StringAssert.Contains(cle, l.Absence);
                }
        }

        [Test] public void Un_identifiant_vide_est_refuse_et_un_identifiant_reserve_arrive_en_un_seul_parametre()
        {
            const string bizarre = "é /?&=+#";
            Servir(Temoin.Replace(Id, bizarre));
            using (var c = new ClientPays(port, TimeSpan.FromSeconds(5)))
            {
                Assert.Throws<ArgumentException>(() => c.Lire(" "));
                var l = c.Lire(bizarre); Assert.IsTrue(l.Presente && l.Donnees.MaisonId == bizarre, l.Absence);
            }
            string valeur = Recues().Single().Substring("GET /pays?maison=".Length);
            Assert.AreEqual(bizarre, Uri.UnescapeDataString(valeur), valeur); Assert.IsTrue(valeur.IndexOfAny(new[] { ' ', '/', '?', '&', '=', '+', '#', 'é' }) < 0, valeur);
        }

        // Lot #1045 : les terres du pays (lieux, vassaux, totaux, bâtiments) se lisent en entier ou pas du tout.
        static string Terres(string ancien, string nouveau)
        {
            int i = TemoinTerres.IndexOf(ancien, StringComparison.Ordinal);
            Assert.IsTrue(i >= 0 && TemoinTerres.LastIndexOf(ancien, StringComparison.Ordinal) == i, "motif absent ou répété : " + ancien);
            return TemoinTerres.Substring(0, i) + nouveau + TemoinTerres.Substring(i + ancien.Length);
        }
        static string PremierTerres(string ancien, string nouveau) { int i = TemoinTerres.IndexOf(ancien, StringComparison.Ordinal); Assert.IsTrue(i >= 0, "motif absent : " + ancien); return TemoinTerres.Substring(0, i) + nouveau + TemoinTerres.Substring(i + ancien.Length); }

        [Test] public void Les_terres_du_pays_se_lisent_avec_leurs_vassaux_et_leurs_batiments()
        {
            Servir(TemoinTerres);
            using (var c = new ClientPays(port, TimeSpan.FromSeconds(5)))
            {
                var l = c.LireTerres("grande-3"); Assert.IsTrue(l.Presente && l.Absence == null, l.Absence); var t = l.Donnees;
                Assert.IsTrue(t.MaisonId == "grande-3" && t.Tick == 31 && t.Date.Annee == 1400 && t.Date.JourDeLAnnee == 32 && t.Suzerain == null);
                CollectionAssert.AreEqual(new[] { "seigneurie-1", "plausible-7-0" }, t.Vassaux);
                CollectionAssert.AreEqual(new[] { "seigneurie-1", "plausible-7-0", "plausible-8-1" }, t.VassauxTous);
                CollectionAssert.AreEqual(new[] { (10L, 0L), (10L, 1L), (10L, 2L), (11L, 1L) }, t.Lieux.Select(x => (x.CellId, x.Rang)).ToArray());
                CollectionAssert.AreEqual(new[] { (12L, 0L), (13L, 0L), (13L, 3L) }, t.LieuxDesVassaux.Select(x => (x.CellId, x.Rang)).ToArray());
                Assert.IsTrue(t.NombreDeLieux == 7 && t.Habitants == 2450344 && t.HabitantsPropres == 271528 && t.Chantiers == 2);
                Assert.IsTrue(t.Recolte30jKg == 141439858.6 && t.GreniersDesVassauxKg == 6862501.4 && t.GrenierKg == 754362.1 && t.AbsenceDuGrenier == null);
                Assert.AreEqual(2, t.Batiments.Count);
                var a = t.Batiments[0]; Assert.IsTrue(a.Identifiant == 1 && a.Nature == "moulin" && a.Nom == "Moulin" && a.CellId == 10 && a.Maison == "grande-3" && a.TravailRequis == 600 && a.TravailFourni == 600 && !a.EnChantier);
                var b = t.Batiments[1]; Assert.IsTrue(b.Identifiant == 2 && b.CellId == 12 && b.Maison == "seigneurie-1" && b.TravailRequis == 600 && b.TravailFourni == 20 && b.EnChantier);
                Assert.Throws<NotSupportedException>(() => ((IList<LieuDuPays>)t.Lieux).Add(null));
            }
            CollectionAssert.AreEqual(new[] { "GET /pays?maison=grande-3" }, Recues());
        }

        [Test] public void Un_grenier_absent_se_dit_absent()
        {
            const string raison = "grenier absent pour la maison grande-3";
            Servir(Terres("\"grenier_nourriture_kg\":754362.1", "\"grenier_nourriture_kg\":null").Replace("\"absents\":{}", "\"absents\":{\"grenier\":\"" + raison + "\"}"));
            using (var c = new ClientPays(port, TimeSpan.FromSeconds(5)))
            {
                var l = c.LireTerres("grande-3"); Assert.IsTrue(l.Presente, l.Absence);
                Assert.IsNull(l.Donnees.GrenierKg); Assert.AreEqual(raison, l.Donnees.AbsenceDuGrenier);
            }
        }

        [Test] public void Des_terres_mal_servies_sont_refusees()
        {
            const string Directs = "\"vassaux\":[\"seigneurie-1\",\"plausible-7-0\"]", Tous = "\"vassaux_tous\":[\"seigneurie-1\",\"plausible-7-0\",\"plausible-8-1\"]";
            var fautes = new List<(string corps, string cle)>
            {
                (Terres("\"maison\":{\"id\":\"grande-3\"", "\"maison\":{\"id\":\"grande-9\""), "maison.id"),
                (Terres("\"tick\":31,", ""), "tick"), (Terres("\"tick\":31", "\"tick\":-1"), "tick"), (Terres("\"tick\":31", "\"tick\":31.5"), "tick"),
                (Terres("\"jour_de_l_annee\":32", "\"jour_de_l_annee\":0"), "date.jour_de_l_annee"), (Terres("\"annee\":1400", "\"annee\":\"1400\""), "date.annee"),
                (Terres("\"suzerain\":null", "\"suzerain\":\"\""), "suzerain"), (Terres("\"suzerain\":null", "\"suzerain\":7"), "suzerain"), (Terres("\"suzerain\":null", "\"suzerain\":\"grande-3\""), "suzerain"),
                (Terres(Directs, "\"vassaux\":[7,\"plausible-7-0\"]"), "vassaux[0]"), (Terres(Directs, "\"vassaux\":[\"\",\"plausible-7-0\"]"), "vassaux[0]"),
                (Terres(Directs, "\"vassaux\":[\"seigneurie-1\",\"seigneurie-1\"]"), "vassaux[1]"), (Terres(Directs, "\"vassaux\":[\"grande-3\",\"plausible-7-0\"]"), "vassaux[0]"),
                (Terres(Tous, "\"vassaux_tous\":[\"seigneurie-1\",\"plausible-8-1\"]"), "vassaux"),
                (Terres(Tous, "\"vassaux_tous\":[\"seigneurie-1\",7,\"plausible-8-1\"]"), "vassaux_tous[1]"), (Terres(Tous, "\"vassaux_tous\":[\"seigneurie-1\",\"plausible-7-0\",\"plausible-7-0\"]"), "vassaux_tous[2]"),
                (Terres(Tous, "\"vassaux_tous\":[\"seigneurie-1\",\"plausible-7-0\",\"grande-3\"]"), "vassaux_tous[2]"),
                (Terres("{\"cell_id\":13,\"rang\":3}", "{\"cell_id\":-1,\"rang\":3}"), "lieux_des_vassaux[2].cell_id"), (Terres("{\"cell_id\":13,\"rang\":0}", "{\"cell_id\":13,\"rang\":-1}"), "lieux_des_vassaux[1].rang"),
                (Terres("{\"cell_id\":10,\"rang\":2}", "{\"cell_id\":10,\"rang\":2.5}"), "lieux[2].rang"), (Terres("{\"cell_id\":10,\"rang\":0}", "{\"cell_id\":\"10\",\"rang\":0}"), "lieux[0].cell_id"),
                (Terres("{\"cell_id\":10,\"rang\":1}", "{\"cell_id\":10,\"rang\":0}"), "lieux[1]"), (Terres("{\"cell_id\":12,\"rang\":0}", "{\"cell_id\":10,\"rang\":0}"), "lieux_des_vassaux[0]"),
                (Terres("{\"cell_id\":11,\"rang\":1}", "{\"cell_id\":12,\"rang\":0}"), "lieux_des_vassaux[0]"), // (12, 0) servi dans les deux listes
                (Terres("\"lieux\":7", "\"lieux\":8"), "totaux.lieux"), (Terres("\"habitants_propres\":271528", "\"habitants_propres\":3000000"), "totaux.habitants_propres"),
                (Terres("\"recolte_30j_kg\":141439858.6", "\"recolte_30j_kg\":-1"), "totaux.recolte_30j_kg"), (Terres("\"recolte_30j_kg\":141439858.6", "\"recolte_30j_kg\":\"beaucoup\""), "totaux.recolte_30j_kg"),
                (Terres("\"greniers_des_vassaux_kg\":6862501.4", "\"greniers_des_vassaux_kg\":-5"), "totaux.greniers_des_vassaux_kg"), (Terres("\"grenier_nourriture_kg\":754362.1", "\"grenier_nourriture_kg\":-2"), "totaux.grenier_nourriture_kg"),
                (Terres("\"chantiers\":2", "\"chantiers\":-1"), "totaux.chantiers"), (Terres("\"chantiers\":2", "\"chantiers\":1.5"), "totaux.chantiers"),
                (Terres("\"grenier_nourriture_kg\":754362.1", "\"grenier_nourriture_kg\":null"), "absents.grenier"),
                (Terres("\"absents\":{}", "\"absents\":{\"grenier\":\"grenier absent pour la maison grande-3\"}"), "absents.grenier"),
                (Terres("\"identifiant\":1,", "\"identifiant\":\"un\","), "batiments[0].identifiant"), (PremierTerres("\"nature\":\"moulin\",", ""), "batiments[0].nature"), (Terres("\"cell_id\":10,\"maison\"", "\"cell_id\":99,\"maison\""), "batiments[0].cell_id"),
                (Terres("\"travail_fourni\":20", "\"travail_fourni\":700"), "batiments[1].travail_fourni"), (Terres("\"en_chantier\":false", "\"en_chantier\":0"), "batiments[0].en_chantier"),
                (PremierTerres("\"nom\":\"Moulin\"", "\"nom\":\"\""), "batiments[0].nom"), (Terres("\"maison\":\"seigneurie-1\"", "\"maison\":\"\""), "batiments[1].maison"),
            };
            Servir(fautes.Select(f => f.corps).ToArray());
            using (var c = new ClientPays(port, TimeSpan.FromSeconds(5)))
                foreach (var (corps, cle) in fautes)
                {
                    var l = c.LireTerres("grande-3");
                    Assert.IsTrue(!l.Presente && l.Donnees == null && !string.IsNullOrEmpty(l.Absence), cle + " : lue malgré la faute");
                    StringAssert.StartsWith("pays : ", l.Absence); StringAssert.Contains(cle, l.Absence);
                }
        }

        [Test] public void Le_document_des_jauges_n_a_pas_de_terres()
        {
            Servir(Temoin);
            using (var c = new ClientPays(port, TimeSpan.FromSeconds(5)))
            {
                var terres = c.LireTerres(Id); Assert.IsFalse(terres.Presente); StringAssert.Contains("lieux", terres.Absence);
                Assert.IsTrue(c.Lire(Id).Presente, "les jauges du même document restent lues");
            }
        }
    }
}
