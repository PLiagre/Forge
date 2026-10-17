using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using NUnit.Framework;
namespace Forge.Pont.Tests
{
    // Lot #610 — un faux service rend /maison?id= ; le client relit la fiche, ou nomme la faute.
    public sealed class ClientMaisonTests
    {
        const string Id = "seigneurie-temoin";
        const string Temoin = "{\"id\":\"seigneurie-temoin\",\"nom\":\"Maison d'Épreuve\",\"siege\":{\"cell_id\":9922,\"rang\":1,\"nom\":\"Le Siège\",\"point\":{\"x_m\":4276473.25,\"y_m\":1135517.5}},\"lieux\":[{\"cell_id\":9922,\"rang\":1},{\"cell_id\":10417,\"rang\":0}],\"absents\":{}}";
        const int Muet = -1;
        int port; HttpListener ecoute; Thread fil; readonly List<string> recues = new List<string>();
        [SetUp] public void PortLibre() { var s = new TcpListener(IPAddress.Loopback, 0); s.Start(); port = ((IPEndPoint)s.LocalEndpoint).Port; s.Stop(); lock (recues) recues.Clear(); }
        [TearDown] public void Fermer() { ecoute?.Close(); fil?.Join(TimeSpan.FromSeconds(5)); (ecoute, fil) = (null, null); }
        void Servir(params (int statut, string corps)[] reponses)
        {
            var a = ecoute = new HttpListener(); a.Prefixes.Add("http://127.0.0.1:" + port + "/"); a.Start();
            (fil = new Thread(() => { try { for (int i = 0; ; i++) { var c = a.GetContext(); lock (recues) recues.Add(c.Request.HttpMethod + " " + c.Request.RawUrl); (int st, string tx) = reponses[Math.Min(i, reponses.Length - 1)]; if (st == Muet) continue; if (st == 302) c.Response.RedirectLocation = "http://127.0.0.1:" + port + "/ailleurs"; c.Response.StatusCode = st; c.Response.Close(Encoding.UTF8.GetBytes(tx), true); } } catch (Exception) { } }) { IsBackground = true }).Start();
        }
        string[] Recues() { lock (recues) return recues.ToArray(); }
        static string Sig(object v)
        {
            if (v == null) return "n"; if (v is string s) return "s" + s; if (v is double d) return d.ToString("R", CultureInfo.InvariantCulture); if (v is bool b) return b ? "t" : "f";
            if (v is List<object> l) { var t = "L" + l.Count.ToString(CultureInfo.InvariantCulture); foreach (object e in l) t += Sig(e); return t; }
            var r = "O"; foreach (var e in (Dictionary<string, object>)v) r += e.Key + Sig(e.Value); return r;
        }
        static string Muter(string ancien, string nouveau)
        {
            int i = Temoin.IndexOf(ancien, StringComparison.Ordinal);
            Assert.IsTrue(i >= 0 && Temoin.LastIndexOf(ancien, StringComparison.Ordinal) == i, ancien);
            string mute = Temoin.Substring(0, i) + nouveau + Temoin.Substring(i + ancien.Length);
            Assert.AreNotEqual(Sig(LecteurJson.LireObjet(Temoin)), Sig(LecteurJson.LireObjet(mute)), ancien);
            return mute;
        }
        static void Absente(Lecture<MaisonLue> l, params string[] attendus)
        { Assert.IsTrue(!l.Presente && l.Donnees == null && !string.IsNullOrEmpty(l.Absence)); StringAssert.StartsWith("maison : ", l.Absence); foreach (string a in attendus) StringAssert.Contains(a, l.Absence); }
        static void Egale(MaisonLue m, string nom, long cell, long rang, string siege, double x, double y, params (long c, long r)[] lieux)
        {
            Assert.IsTrue(m.Id == Id && m.Nom == nom && m.Siege.CellId == cell && m.Siege.Rang == rang && m.Siege.Nom == siege && m.Siege.Position.Value.X == x && m.Siege.Position.Value.Y == y && m.Lieux.Count == lieux.Length && m.Absents.Count == 0, nom);
            for (int i = 0; i < lieux.Length; i++) Assert.IsTrue(m.Lieux[i].CellId == lieux[i].c && m.Lieux[i].Rang == lieux[i].r, "lieu " + i);
        }
        [Test] public void LaFicheTemoinEstReluePuisRemplacee()
        {
            const string suivant = "{\"id\":\"seigneurie-temoin\",\"nom\":\"Autre Maison\",\"siege\":{\"cell_id\":9007199254740991,\"rang\":0,\"nom\":\"Ailleurs\",\"point\":{\"x_m\":1.5,\"y_m\":-2.25}},\"lieux\":[{\"cell_id\":3,\"rang\":4}],\"absents\":{}}";
            Servir((200, Temoin), (200, suivant));
            using (var c = new ClientMaison(port, TimeSpan.FromSeconds(5)))
            {
                var a = c.Lire(Id); var b = c.Lire(Id);
                Assert.IsTrue(a.Presente && a.Absence == null && b.Presente && b.Absence == null, a.Absence ?? b.Absence);
                Egale(a.Donnees, "Maison d'Épreuve", 9922, 1, "Le Siège", 4276473.25, 1135517.5, (9922, 1), (10417, 0));
                Egale(b.Donnees, "Autre Maison", 9007199254740991L, 0, "Ailleurs", 1.5, -2.25, (3, 4));
                Assert.AreNotEqual(a.Donnees.Nom, b.Donnees.Nom);
                Assert.Throws<NotSupportedException>(() => ((IList<LieuTenu>)a.Donnees.Lieux).Add(new LieuTenu(0, 0)));
                Assert.Throws<NotSupportedException>(() => ((IDictionary<string, string>)a.Donnees.Absents).Add("x", "y"));
            }
            CollectionAssert.AreEqual(new[] { "GET /maison?id=seigneurie-temoin", "GET /maison?id=seigneurie-temoin" }, Recues());
        }
        [Test] public void UnIdentifiantReserveArriveEnUnSeulParametre()
        {
            const string bizarre = "é /?&=+#";
            Servir((200, Temoin.Replace(Id, bizarre)));
            using (var c = new ClientMaison(port, TimeSpan.FromSeconds(5)))
            { var l = c.Lire(bizarre); Assert.IsTrue(l.Presente && l.Donnees.Id == bizarre && l.Donnees.Nom == "Maison d'Épreuve", l.Absence); }
            Assert.AreEqual(1, Recues().Length); StringAssert.StartsWith("GET /maison?id=", Recues()[0]);
            string valeur = Recues()[0].Substring("GET /maison?id=".Length);
            Assert.AreEqual(bizarre, Uri.UnescapeDataString(valeur), valeur);
            Assert.IsTrue(valeur.IndexOfAny(new[] { ' ', '/', '?', '&', '=', '+', '#', 'é' }) < 0, valeur);
        }
        [Test] public void LesAbsencesDeclareesRestentLisibles()
        {
            string nomNul = Temoin.Replace("\"nom\":\"Maison d'Épreuve\"", "\"nom\":null").Replace("\"absents\":{}", "\"absents\":{\"nom\":\"nom manquant\"}");
            string hors = Temoin.Replace("\"cell_id\":9922,\"rang\":1,\"nom\":\"Le Siège\",\"point\":{\"x_m\":4276473.25,\"y_m\":1135517.5}", "\"cell_id\":null,\"rang\":null,\"nom\":\"Le Siège\",\"point\":null").Replace("\"absents\":{}", "\"absents\":{\"siege\":\"hors carte\"}");
            string vides = Temoin.Replace("\"lieux\":[{\"cell_id\":9922,\"rang\":1},{\"cell_id\":10417,\"rang\":0}]", "\"lieux\":[]").Replace("\"absents\":{}", "\"absents\":{\"part\":\"  part absente  \",\"grenier\":\"grenier absent\"}");
            string extras = Temoin.Insert(Temoin.Length - 1, ",\"sorte\":\"seigneurie\",\"suzerain\":\"duc\",\"part\":0.25,\"grenier\":{\"ble\":1},\"flux_30j\":{\"preleve_kg\":3},\"tick\":5,\"date\":{\"annee\":1400},\"latitude\":48.8,\"longitude\":2.3");
            foreach (string corps in new[] { nomNul, hors, vides, extras }) { Assert.AreNotEqual(Temoin, corps); LecteurJson.LireObjet(corps); }
            Servir((200, nomNul), (200, hors), (200, vides), (200, extras));
            using (var c = new ClientMaison(port, TimeSpan.FromSeconds(5)))
            {
                var n = c.Lire(Id); var s = c.Lire(Id); var v = c.Lire(Id); var e = c.Lire(Id);
                Assert.IsTrue(n.Presente && n.Donnees.Nom == null && n.Donnees.Absents["nom"] == "nom manquant" && n.Donnees.Siege.Nom == "Le Siège" && n.Donnees.Lieux.Count == 2, n.Absence);
                Assert.IsTrue(s.Presente && s.Donnees.Siege.CellId == null && s.Donnees.Siege.Rang == null && s.Donnees.Siege.Position == null && s.Donnees.Siege.Nom == "Le Siège" && s.Donnees.Absents["siege"] == "hors carte" && s.Donnees.Nom == "Maison d'Épreuve", s.Absence);
                Assert.IsTrue(v.Presente && v.Donnees.Lieux.Count == 0 && v.Donnees.Absents["part"] == "  part absente  " && v.Donnees.Absents["grenier"] == "grenier absent" && v.Donnees.Siege.CellId == 9922, v.Absence);
                Assert.IsTrue(e.Presente && e.Donnees.Nom == "Maison d'Épreuve" && e.Donnees.Lieux.Count == 2 && e.Donnees.Absents.Count == 0 && e.Donnees.Siege.Position.Value.X == 4276473.25, e.Absence);
            }
            var noms = new List<string>(); foreach (var p in typeof(MaisonLue).GetProperties()) noms.Add(p.Name);
            CollectionAssert.AreEquivalent(new[] { "Id", "Nom", "Siege", "Lieux", "Absents" }, noms);
        }
        [TestCase("\"id\":\"seigneurie-temoin\",", "", "clé absente : id")] [TestCase("\"nom\":\"Maison d'Épreuve\",", "", "clé absente : nom")]
        [TestCase("\"siege\":{\"cell_id\":9922,\"rang\":1,\"nom\":\"Le Siège\",\"point\":{\"x_m\":4276473.25,\"y_m\":1135517.5}},", "", "clé absente : siege")] [TestCase(",\"lieux\":[{\"cell_id\":9922,\"rang\":1},{\"cell_id\":10417,\"rang\":0}]", "", "clé absente : lieux")]
        [TestCase(",\"absents\":{}", "", "clé absente : absents")] [TestCase("\"cell_id\":9922,\"rang\":1,\"nom\":\"Le Siège\"", "\"rang\":1,\"nom\":\"Le Siège\"", "clé absente : siege.cell_id")]
        [TestCase("\"rang\":1,\"nom\":\"Le Siège\"", "\"nom\":\"Le Siège\"", "clé absente : siege.rang")] [TestCase(",\"nom\":\"Le Siège\"", "", "clé absente : siege.nom")]
        [TestCase(",\"point\":{\"x_m\":4276473.25,\"y_m\":1135517.5}", "", "clé absente : siege.point")] [TestCase("\"x_m\":4276473.25,", "", "clé absente : siege.point.x_m")]
        [TestCase(",\"y_m\":1135517.5", "", "clé absente : siege.point.y_m")] [TestCase("[{\"cell_id\":9922,", "[{", "clé absente : lieux[0].cell_id")]
        [TestCase("9922,\"rang\":1}", "9922}", "clé absente : lieux[0].rang")] [TestCase("{\"cell_id\":10417,\"rang\":0}", "{\"rang\":0}", "clé absente : lieux[1].cell_id")]
        [TestCase(",\"rang\":0", "", "clé absente : lieux[1].rang")] [TestCase("\"siege\":{\"cell_id\":9922,\"rang\":1,\"nom\":\"Le Siège\",\"point\":{\"x_m\":4276473.25,\"y_m\":1135517.5}}", "\"siege\":[]", "clé siege :")]
        [TestCase("\"lieux\":[{\"cell_id\":9922,\"rang\":1},{\"cell_id\":10417,\"rang\":0}]", "\"lieux\":{}", "clé lieux :")] [TestCase("\"absents\":{}", "\"absents\":[]", "clé absents :")]
        [TestCase("\"point\":{\"x_m\":4276473.25,\"y_m\":1135517.5}", "\"point\":true", "clé siege.point")] [TestCase("{\"cell_id\":10417,\"rang\":0}", "null", "clé lieux[1]")]
        [TestCase("\"nom\":\"Maison d'Épreuve\"", "\"nom\":7", "clé nom :")] [TestCase("\"nom\":\"Le Siège\"", "\"nom\":null", "clé siege.nom")]
        [TestCase("\"id\":\"seigneurie-temoin\"", "\"id\":\" \"", "clé id :")] [TestCase("\"id\":\"seigneurie-temoin\"", "\"id\":\"autre\"", "clé id :")]
        [TestCase("\"nom\":\"Maison d'Épreuve\"", "\"nom\":\" \"", "clé nom :")] [TestCase("\"nom\":\"Le Siège\"", "\"nom\":\"  \"", "clé siege.nom")]
        [TestCase("\"siege\":{\"cell_id\":9922", "\"siege\":{\"cell_id\":-1", "clé siege.cell_id")] [TestCase("\"rang\":1,\"nom\":\"Le Siège\"", "\"rang\":1.5,\"nom\":\"Le Siège\"", "clé siege.rang")]
        [TestCase("\"siege\":{\"cell_id\":9922", "\"siege\":{\"cell_id\":9007199254740992", "clé siege.cell_id")] [TestCase("\"x_m\":4276473.25", "\"x_m\":\"ouest\"", "clé siege.point.x_m")]
        [TestCase(",\"rang\":0", ",\"rang\":-1", "clé lieux[1].rang")] [TestCase("{\"cell_id\":10417,\"rang\":0}", "{\"cell_id\":9922,\"rang\":1}", "clé lieux[1]")]
        [TestCase("\"nom\":\"Maison d'Épreuve\"", "\"nom\":null", "clé absents.nom")] [TestCase("\"absents\":{}", "\"absents\":{\"nom\":\"en trop\"}", "clé absents.nom")]
        [TestCase("\"siege\":{\"cell_id\":9922", "\"siege\":{\"cell_id\":null", "clé siege.cell_id")] [TestCase("\"cell_id\":9922,\"rang\":1,\"nom\":\"Le Siège\",\"point\":{\"x_m\":4276473.25,\"y_m\":1135517.5}", "\"cell_id\":null,\"rang\":null,\"nom\":\"Le Siège\",\"point\":null", "clé absents.siege")]
        [TestCase("\"absents\":{}", "\"absents\":{\"siege\":\"hors carte\"}", "clé absents.siege")] [TestCase("\"absents\":{}", "\"absents\":{\"part\":\" \"}", "clé absents.part")]
        public void UneFauteEstNommeeASonChemin(string ancien, string nouveau, string chemin)
        { Servir((200, Muter(ancien, nouveau))); using (var c = new ClientMaison(port, TimeSpan.FromSeconds(5))) Absente(c.Lire(Id), chemin); }
        [Test] public void UnJsonCoupeOuNonRepresentableEstInvalide()
        {
            string coupe = Temoin.Substring(0, Temoin.Length - 1); int i = Temoin.IndexOf("4276473.25", StringComparison.Ordinal);
            string infini = Temoin.Substring(0, i) + "1e309" + Temoin.Substring(i + "4276473.25".Length);
            Assert.AreNotEqual(Temoin, coupe); Assert.AreNotEqual(Temoin, infini);
            Assert.Throws<ErreurJson>(() => LecteurJson.LireObjet(coupe)); Assert.Throws<ErreurJson>(() => LecteurJson.LireObjet(infini));
            Servir((200, coupe), (200, infini));
            using (var c = new ClientMaison(port, TimeSpan.FromSeconds(5))) { Absente(c.Lire(Id), "JSON invalide"); Absente(c.Lire(Id), "JSON invalide"); }
        }
        [Test] public void UnePanneApresLectureNeRendPasLAncienneFiche()
        {
            const string e404 = "{\"erreur\":\"maison inconnue\"}", e500 = "{\"erreur\":\"casse\"}", e302 = "{\"vers\":\"ailleurs\"}";
            Servir((200, Temoin), (404, e404), (500, e500), (302, e302));
            using (var c = new ClientMaison(port, TimeSpan.FromSeconds(5)))
            { Assert.IsTrue(c.Lire(Id).Presente); Absente(c.Lire(Id), "404", e404); Absente(c.Lire(Id), "500", e500); Absente(c.Lire(Id), "302", e302); }
            Assert.AreEqual(4, Recues().Length); foreach (string r in Recues()) StringAssert.DoesNotContain("ailleurs", r);
        }
        [Test] public void UnServiceAbsentOuMuetEstDeclare()
        {
            Servir((200, Temoin)); using (var c = new ClientMaison(port, TimeSpan.FromSeconds(5))) Assert.IsTrue(c.Lire(Id).Presente); Fermer();
            using (var c = new ClientMaison(port, TimeSpan.FromSeconds(5))) Absente(c.Lire(Id), "service absent", "127.0.0.1:" + port);
            Servir((Muet, Temoin)); var chrono = Stopwatch.StartNew();
            using (var c = new ClientMaison(port, TimeSpan.FromMilliseconds(300))) Absente(c.Lire(Id), "délai dépassé", "300"); Assert.GreaterOrEqual(chrono.ElapsedMilliseconds, 250);
        }
        [Test] public void UnAppelIlliciteNePartPas()
        {
            foreach (int hors in new[] { 0, -1, 65536 }) Assert.Throws<ArgumentOutOfRangeException>(() => new ClientMaison(hors, TimeSpan.FromSeconds(1)));
            foreach (TimeSpan d in new[] { TimeSpan.Zero, TimeSpan.FromTicks(-1), Timeout.InfiniteTimeSpan, TimeSpan.FromMilliseconds((double)int.MaxValue + 1) })
                Assert.Throws<ArgumentOutOfRangeException>(() => new ClientMaison(1, d));
            new ClientMaison(1, TimeSpan.FromMilliseconds(1)).Dispose(); new ClientMaison(65535, TimeSpan.FromSeconds(1)).Dispose();
            Servir((200, Temoin));
            using (var c = new ClientMaison(port, TimeSpan.FromSeconds(5)))
                foreach (string id in new string[] { null, "", " ", "\t" }) Assert.AreEqual(typeof(ArgumentException), Assert.Throws<ArgumentException>(() => c.Lire(id)).GetType());
            Assert.AreEqual(0, Recues().Length);
        }
        const string Complet = "{\"id\":\"seigneurie-temoin\",\"nom\":\"Maison d'Épreuve\",\"siege\":{\"cell_id\":9922,\"rang\":1,\"nom\":\"Le Siège\",\"point\":{\"x_m\":4276473.25,\"y_m\":1135517.5}},\"lieux\":[{\"cell_id\":9922,\"rang\":1},{\"cell_id\":10417,\"rang\":0}],\"absents\":{},\"suzerain\":\"grande-temoin\",\"part\":0.25,\"grenier\":{\"nourriture\":1234.5,\"bois\":0},\"flux_30j\":{\"preleve_kg\":812.25,\"recu_kg\":790.5,\"du_envoye_kg\":81.0,\"mange_en_route_kg\":21.75,\"rendu_kg\":19.25,\"partis_personnes\":7,\"arrives_personnes\":2,\"salaires_payes_kg\":40.5}}";
        static string MuterComplet(string ancien, string nouveau)
        {
            int i = Complet.IndexOf(ancien, StringComparison.Ordinal);
            Assert.IsTrue(i >= 0 && Complet.LastIndexOf(ancien, StringComparison.Ordinal) == i, ancien);
            string mute = Complet.Substring(0, i) + nouveau + Complet.Substring(i + ancien.Length);
            Assert.AreNotEqual(Sig(LecteurJson.LireObjet(Complet)), Sig(LecteurJson.LireObjet(mute)), ancien);
            return mute;
        }
        static void AbsenteComptes(Lecture<ComptesDeMaison> l, params string[] attendus)
        { Assert.IsTrue(!l.Presente && l.Donnees == null && !string.IsNullOrEmpty(l.Absence)); StringAssert.StartsWith("maison : ", l.Absence); foreach (string a in attendus) StringAssert.Contains(a, l.Absence); }
        static void FluxEgal(FluxDeMaison f, double preleve, double recu, double du, double mange, double rendu, long partis, long arrives, double? salaires)
        { Assert.IsTrue(f.PreleveKg == preleve && f.RecuKg == recu && f.DuEnvoyeKg == du && f.MangeEnRouteKg == mange && f.RenduKg == rendu && f.PartisPersonnes == partis && f.ArrivesPersonnes == arrives && f.SalairesPayesKg == salaires, preleve.ToString(CultureInfo.InvariantCulture)); }
        static void Meme(MaisonLue a, MaisonLue b)
        {
            Assert.IsTrue(a.Id == b.Id && a.Nom == b.Nom && a.Siege.CellId == b.Siege.CellId && a.Siege.Rang == b.Siege.Rang && a.Siege.Nom == b.Siege.Nom && a.Siege.Position.Value.X == b.Siege.Position.Value.X && a.Siege.Position.Value.Y == b.Siege.Position.Value.Y && a.Lieux.Count == b.Lieux.Count && a.Absents.Count == b.Absents.Count, a.Nom);
            for (int i = 0; i < a.Lieux.Count; i++) Assert.IsTrue(a.Lieux[i].CellId == b.Lieux[i].CellId && a.Lieux[i].Rang == b.Lieux[i].Rang, "lieu " + i);
            foreach (var e in a.Absents) Assert.AreEqual(e.Value, b.Absents[e.Key]);
        }
        [Test] public void LesComptesCompletsSontRelusPuisRemplaces()
        {
            string autre = Complet.Replace("\"suzerain\":\"grande-temoin\"", "\"suzerain\":\"petite-temoin\"").Replace("\"part\":0.25", "\"part\":1").Replace("\"nourriture\":1234.5", "\"nourriture\":9.5").Replace("\"bois\":0", "\"bois\":4").Replace("\"preleve_kg\":812.25", "\"preleve_kg\":1").Replace("\"recu_kg\":790.5", "\"recu_kg\":2").Replace("\"du_envoye_kg\":81.0", "\"du_envoye_kg\":3").Replace("\"mange_en_route_kg\":21.75", "\"mange_en_route_kg\":4").Replace("\"rendu_kg\":19.25", "\"rendu_kg\":5").Replace("\"partis_personnes\":7", "\"partis_personnes\":11").Replace("\"arrives_personnes\":2", "\"arrives_personnes\":13").Replace("\"salaires_payes_kg\":40.5", "\"salaires_payes_kg\":0.5");
            Servir((200, Complet), (200, Complet), (200, autre));
            using (var c = new ClientMaison(port, TimeSpan.FromSeconds(5)))
            {
                var fiche = c.Lire(Id); var a = c.LireComptes(Id); var b = c.LireComptes(Id);
                Assert.IsTrue(fiche.Presente && a.Presente && a.Absence == null && b.Presente && b.Absence == null, a.Absence ?? b.Absence);
                Meme(fiche.Donnees, a.Donnees.Maison);
                Assert.IsTrue(a.Donnees.Suzerain == "grande-temoin" && a.Donnees.Part == 0.25 && a.Donnees.Grenier.Count == 2 && a.Donnees.Grenier["nourriture"] == 1234.5 && a.Donnees.Grenier["bois"] == 0, a.Donnees.Suzerain);
                FluxEgal(a.Donnees.Flux, 812.25, 790.5, 81, 21.75, 19.25, 7, 2, 40.5);
                Assert.IsTrue(b.Donnees.Suzerain == "petite-temoin" && b.Donnees.Part == 1 && b.Donnees.Grenier["nourriture"] == 9.5 && b.Donnees.Grenier["bois"] == 4 && b.Donnees.Part != a.Donnees.Part, b.Absence);
                FluxEgal(b.Donnees.Flux, 1, 2, 3, 4, 5, 11, 13, 0.5);
                Assert.Throws<NotSupportedException>(() => ((IDictionary<string, double>)a.Donnees.Grenier).Add("sel", 1));
            }
            CollectionAssert.AreEqual(new[] { "GET /maison?id=seigneurie-temoin", "GET /maison?id=seigneurie-temoin", "GET /maison?id=seigneurie-temoin" }, Recues());
        }
        [Test] public void UnSuzerainNulEstUneRacineSansRaison()
        {
            Servir((200, Complet.Replace("\"suzerain\":\"grande-temoin\"", "\"suzerain\":null")));
            using (var c = new ClientMaison(port, TimeSpan.FromSeconds(5))) { var l = c.LireComptes(Id); Assert.IsTrue(l.Presente && l.Donnees.Suzerain == null && l.Donnees.Maison.Absents.Count == 0 && l.Donnees.Part == 0.25, l.Absence); }
        }
        [Test] public void UnePartNulleGardeSaRaison()
        {
            const string raison = "  part absente  ";
            Servir((200, Complet.Replace("\"part\":0.25", "\"part\":null").Replace("\"absents\":{}", "\"absents\":{\"part\":\"" + raison + "\"}")));
            using (var c = new ClientMaison(port, TimeSpan.FromSeconds(5))) { var l = c.LireComptes(Id); Assert.IsTrue(l.Presente && l.Donnees.Part == null && l.Donnees.Maison.Absents["part"] == raison, l.Absence); }
        }
        [Test] public void UnGrenierNulGardeSaRaison()
        {
            const string raison = "  grenier absent  ";
            Servir((200, Complet.Replace("\"grenier\":{\"nourriture\":1234.5,\"bois\":0}", "\"grenier\":null").Replace("\"absents\":{}", "\"absents\":{\"grenier\":\"" + raison + "\"}")));
            using (var c = new ClientMaison(port, TimeSpan.FromSeconds(5))) { var l = c.LireComptes(Id); Assert.IsTrue(l.Presente && l.Donnees.Grenier == null && l.Donnees.Maison.Absents["grenier"] == raison, l.Absence); }
        }
        [Test] public void UnGrenierVideEstUneMesure()
        {
            Servir((200, Complet.Replace("\"grenier\":{\"nourriture\":1234.5,\"bois\":0}", "\"grenier\":{}")));
            using (var c = new ClientMaison(port, TimeSpan.FromSeconds(5))) { var l = c.LireComptes(Id); Assert.IsTrue(l.Presente && l.Donnees.Grenier != null && l.Donnees.Grenier.Count == 0 && !l.Donnees.Maison.Absents.ContainsKey("grenier"), l.Absence); }
        }
        [Test] public void UnePartEtDesFluxAZeroRestentDesMesures()
        {
            string corps = Complet.Replace("\"part\":0.25", "\"part\":0").Replace("\"preleve_kg\":812.25", "\"preleve_kg\":0").Replace("\"recu_kg\":790.5", "\"recu_kg\":0").Replace("\"du_envoye_kg\":81.0", "\"du_envoye_kg\":0").Replace("\"mange_en_route_kg\":21.75", "\"mange_en_route_kg\":0").Replace("\"rendu_kg\":19.25", "\"rendu_kg\":0").Replace("\"partis_personnes\":7", "\"partis_personnes\":0").Replace("\"arrives_personnes\":2", "\"arrives_personnes\":0");
            Servir((200, corps));
            using (var c = new ClientMaison(port, TimeSpan.FromSeconds(5))) { var l = c.LireComptes(Id); Assert.IsTrue(l.Presente && l.Donnees.Part == 0 && l.Donnees.Maison.Absents.Count == 0, l.Absence); FluxEgal(l.Donnees.Flux, 0, 0, 0, 0, 0, 0, 0, 40.5); }
        }
        [Test] public void UnSalaireAbsentNEstPasUnSalaireNul()
        {
            Servir((200, Complet.Replace(",\"salaires_payes_kg\":40.5", "")), (200, Complet.Replace("\"salaires_payes_kg\":40.5", "\"salaires_payes_kg\":0")));
            using (var c = new ClientMaison(port, TimeSpan.FromSeconds(5)))
            { var a = c.LireComptes(Id); var z = c.LireComptes(Id); Assert.IsTrue(a.Presente && a.Donnees.Flux.SalairesPayesKg == null && a.Donnees.Flux.PreleveKg == 812.25, a.Absence); Assert.IsTrue(z.Presente && z.Donnees.Flux.SalairesPayesKg == 0, z.Absence); }
        }
        [TestCase("\"part\":0.25", "\"part\":null", "clé absents.part")] [TestCase("\"grenier\":{\"nourriture\":1234.5,\"bois\":0}", "\"grenier\":null", "clé absents.grenier")]
        [TestCase("\"absents\":{},\"suzerain\":\"grande-temoin\",\"part\":0.25", "\"absents\":{\"part\":\" \"},\"suzerain\":\"grande-temoin\",\"part\":null", "clé absents.part")] [TestCase("\"absents\":{}", "\"absents\":{\"part\":\"en trop\"}", "clé absents.part")]
        [TestCase("\"absents\":{}", "\"absents\":{\"grenier\":\"en trop\"}", "clé absents.grenier")]
        [TestCase(",\"suzerain\":\"grande-temoin\"", "", "clé absente : suzerain")] [TestCase(",\"part\":0.25", "", "clé absente : part")]
        [TestCase(",\"grenier\":{\"nourriture\":1234.5,\"bois\":0}", "", "clé absente : grenier")]
        [TestCase(",\"flux_30j\":{\"preleve_kg\":812.25,\"recu_kg\":790.5,\"du_envoye_kg\":81.0,\"mange_en_route_kg\":21.75,\"rendu_kg\":19.25,\"partis_personnes\":7,\"arrives_personnes\":2,\"salaires_payes_kg\":40.5}", "", "clé absente : flux_30j")]
        [TestCase("\"preleve_kg\":812.25,", "", "clé absente : flux_30j.preleve_kg")] [TestCase(",\"recu_kg\":790.5", "", "clé absente : flux_30j.recu_kg")]
        [TestCase(",\"du_envoye_kg\":81.0", "", "clé absente : flux_30j.du_envoye_kg")] [TestCase(",\"mange_en_route_kg\":21.75", "", "clé absente : flux_30j.mange_en_route_kg")]
        [TestCase(",\"rendu_kg\":19.25", "", "clé absente : flux_30j.rendu_kg")] [TestCase(",\"partis_personnes\":7", "", "clé absente : flux_30j.partis_personnes")]
        [TestCase(",\"arrives_personnes\":2", "", "clé absente : flux_30j.arrives_personnes")]
        [TestCase("\"suzerain\":\"grande-temoin\"", "\"suzerain\":\" \"", "clé suzerain")] [TestCase("\"suzerain\":\"grande-temoin\"", "\"suzerain\":7", "clé suzerain")]
        [TestCase("\"part\":0.25", "\"part\":-0.1", "clé part")] [TestCase("\"part\":0.25", "\"part\":1.1", "clé part")]
        [TestCase("\"part\":0.25", "\"part\":\"quart\"", "clé part")] [TestCase("\"part\":0.25", "\"part\":true", "clé part")]
        [TestCase("\"grenier\":{\"nourriture\":1234.5,\"bois\":0}", "\"grenier\":[]", "clé grenier")] [TestCase("\"nourriture\":1234.5", "\" \":1234.5", "clé grenier")]
        [TestCase("\"nourriture\":1234.5", "\"nourriture\":-1", "grenier.nourriture")] [TestCase("\"nourriture\":1234.5", "\"nourriture\":\"sac\"", "grenier.nourriture")]
        [TestCase("\"flux_30j\":{\"preleve_kg\":812.25,\"recu_kg\":790.5,\"du_envoye_kg\":81.0,\"mange_en_route_kg\":21.75,\"rendu_kg\":19.25,\"partis_personnes\":7,\"arrives_personnes\":2,\"salaires_payes_kg\":40.5}", "\"flux_30j\":[]", "clé flux_30j")]
        [TestCase("\"flux_30j\":{\"preleve_kg\":812.25,\"recu_kg\":790.5,\"du_envoye_kg\":81.0,\"mange_en_route_kg\":21.75,\"rendu_kg\":19.25,\"partis_personnes\":7,\"arrives_personnes\":2,\"salaires_payes_kg\":40.5}", "\"flux_30j\":null", "clé flux_30j")]
        [TestCase("\"preleve_kg\":812.25", "\"preleve_kg\":-1", "flux_30j.preleve_kg")] [TestCase("\"preleve_kg\":812.25", "\"preleve_kg\":null", "flux_30j.preleve_kg")]
        [TestCase("\"recu_kg\":790.5", "\"recu_kg\":-1", "flux_30j.recu_kg")] [TestCase("\"recu_kg\":790.5", "\"recu_kg\":null", "flux_30j.recu_kg")]
        [TestCase("\"du_envoye_kg\":81.0", "\"du_envoye_kg\":-1", "flux_30j.du_envoye_kg")] [TestCase("\"du_envoye_kg\":81.0", "\"du_envoye_kg\":null", "flux_30j.du_envoye_kg")]
        [TestCase("\"mange_en_route_kg\":21.75", "\"mange_en_route_kg\":-1", "flux_30j.mange_en_route_kg")] [TestCase("\"mange_en_route_kg\":21.75", "\"mange_en_route_kg\":null", "flux_30j.mange_en_route_kg")]
        [TestCase("\"rendu_kg\":19.25", "\"rendu_kg\":-1", "flux_30j.rendu_kg")] [TestCase("\"rendu_kg\":19.25", "\"rendu_kg\":null", "flux_30j.rendu_kg")]
        [TestCase("\"partis_personnes\":7", "\"partis_personnes\":-1", "flux_30j.partis_personnes")] [TestCase("\"partis_personnes\":7", "\"partis_personnes\":1.5", "flux_30j.partis_personnes")]
        [TestCase("\"partis_personnes\":7", "\"partis_personnes\":9007199254740992", "flux_30j.partis_personnes")]
        [TestCase("\"arrives_personnes\":2", "\"arrives_personnes\":-1", "flux_30j.arrives_personnes")] [TestCase("\"arrives_personnes\":2", "\"arrives_personnes\":1.5", "flux_30j.arrives_personnes")]
        [TestCase("\"arrives_personnes\":2", "\"arrives_personnes\":9007199254740992", "flux_30j.arrives_personnes")]
        [TestCase("\"salaires_payes_kg\":40.5", "\"salaires_payes_kg\":-1", "flux_30j.salaires_payes_kg")] [TestCase("\"salaires_payes_kg\":40.5", "\"salaires_payes_kg\":null", "flux_30j.salaires_payes_kg")]
        public void UneFauteDeComptesEstNommeeASonChemin(string ancien, string nouveau, string chemin)
        { Servir((200, MuterComplet(ancien, nouveau))); using (var c = new ClientMaison(port, TimeSpan.FromSeconds(5))) AbsenteComptes(c.LireComptes(Id), chemin); }
        [Test] public void UnCompteNonRepresentableEstInvalide()
        {
            int i = Complet.IndexOf("812.25", StringComparison.Ordinal);
            string infini = Complet.Substring(0, i) + "1e309" + Complet.Substring(i + "812.25".Length);
            Assert.AreNotEqual(Complet, infini); Assert.Throws<ErreurJson>(() => LecteurJson.LireObjet(infini));
            Servir((200, infini));
            using (var c = new ClientMaison(port, TimeSpan.FromSeconds(5))) AbsenteComptes(c.LireComptes(Id), "JSON invalide");
        }
        [Test] public void UneFauteDeComptesLaisseLireEtLesClesInconnuesPassent()
        {
            string faute = MuterComplet("\"part\":0.25", "\"part\":2");
            string inconnu = Complet.Replace("\"salaires_payes_kg\":40.5}", "\"salaires_payes_kg\":40.5,\"note\":1}");
            inconnu = inconnu.Insert(inconnu.Length - 1, ",\"sorte\":\"seigneurie\",\"tick\":5,\"date\":{\"annee\":1400}");
            LecteurJson.LireObjet(inconnu);
            Servir((200, faute), (200, faute), (200, inconnu));
            using (var c = new ClientMaison(port, TimeSpan.FromSeconds(5)))
            {
                var l = c.Lire(Id); Assert.IsTrue(l.Presente && l.Donnees.Id == Id && l.Donnees.Nom == "Maison d'Épreuve" && l.Donnees.Lieux.Count == 2, l.Absence);
                AbsenteComptes(c.LireComptes(Id), "clé part");
                var a = c.LireComptes(Id); Assert.IsTrue(a.Presente && a.Donnees.Part == 0.25 && a.Donnees.Flux.SalairesPayesKg == 40.5 && a.Donnees.Suzerain == "grande-temoin", a.Absence);
            }
        }
        [Test] public void UnePanneDeComptesNeRendPasLAncienneFiche()
        {
            const string e404 = "{\"erreur\":\"maison inconnue\"}", e500 = "{\"erreur\":\"casse\"}", e302 = "{\"vers\":\"ailleurs\"}";
            Servir((200, Complet), (404, e404), (500, e500), (302, e302));
            using (var c = new ClientMaison(port, TimeSpan.FromSeconds(5)))
            { Assert.IsTrue(c.LireComptes(Id).Presente); AbsenteComptes(c.LireComptes(Id), "404", e404); AbsenteComptes(c.LireComptes(Id), "500", e500); AbsenteComptes(c.LireComptes(Id), "302", e302); }
            Assert.AreEqual(4, Recues().Length); foreach (string r in Recues()) StringAssert.DoesNotContain("ailleurs", r);
        }
        [Test] public void UnServiceAbsentOuMuetNeRendPasLesComptes()
        {
            Servir((200, Complet));
            using (var c = new ClientMaison(port, TimeSpan.FromSeconds(5))) { Assert.IsTrue(c.LireComptes(Id).Presente); Fermer(); AbsenteComptes(c.LireComptes(Id), "service absent", "127.0.0.1:" + port); }
            Servir((Muet, Complet)); var chrono = Stopwatch.StartNew();
            using (var c = new ClientMaison(port, TimeSpan.FromMilliseconds(300))) AbsenteComptes(c.LireComptes(Id), "délai dépassé", "300");
            Assert.GreaterOrEqual(chrono.ElapsedMilliseconds, 250);
        }
        [Test] public void LeTemoinSansComptesResteLisibleParLire()
        {
            Servir((200, Temoin), (200, Temoin));
            using (var c = new ClientMaison(port, TimeSpan.FromSeconds(5)))
            { AbsenteComptes(c.LireComptes(Id), "clé absente : suzerain"); var l = c.Lire(Id); Assert.IsTrue(l.Presente && l.Donnees.Nom == "Maison d'Épreuve" && l.Donnees.Lieux.Count == 2, l.Absence); }
        }
        [Test] public void UnIdentifiantVideNeDemandePasLesComptes()
        {
            Servir((200, Complet));
            using (var c = new ClientMaison(port, TimeSpan.FromSeconds(5)))
                foreach (string id in new string[] { null, "", " ", "\t" }) Assert.AreEqual(typeof(ArgumentException), Assert.Throws<ArgumentException>(() => c.LireComptes(id)).GetType());
            Assert.AreEqual(0, Recues().Length);
        }
        [Test] public void UnIdentifiantReserveArriveEncodePourLesComptes()
        {
            const string bizarre = "é /?&=+#";
            Servir((200, Complet.Replace(Id, bizarre)));
            using (var c = new ClientMaison(port, TimeSpan.FromSeconds(5)))
            { var l = c.LireComptes(bizarre); Assert.IsTrue(l.Presente && l.Donnees.Maison.Id == bizarre && l.Donnees.Suzerain == "grande-temoin" && l.Donnees.Part == 0.25, l.Absence); }
            Assert.AreEqual(1, Recues().Length); StringAssert.StartsWith("GET /maison?id=", Recues()[0]);
            string valeur = Recues()[0].Substring("GET /maison?id=".Length);
            Assert.AreEqual(bizarre, Uri.UnescapeDataString(valeur), valeur);
            Assert.IsTrue(valeur.IndexOfAny(new[] { ' ', '/', '?', '&', '=', '+', '#', 'é' }) < 0, valeur);
        }
    }
}
