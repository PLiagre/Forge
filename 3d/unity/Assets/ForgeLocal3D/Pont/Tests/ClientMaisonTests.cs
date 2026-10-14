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
    }
}
