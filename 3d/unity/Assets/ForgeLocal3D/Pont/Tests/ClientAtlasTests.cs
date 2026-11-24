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
    // Un faux service rend /atlas ; le client relit ce qui est servi, ou nomme la faute.
    public sealed class ClientAtlasTests
    {
        const string Atlas = "atlas-graine0.json";
        int port, statut = 200; HttpListener ecoute; Thread fil;
        [SetUp] public void PortLibre() { var s = new TcpListener(IPAddress.Loopback, 0); s.Start(); port = ((IPEndPoint)s.LocalEndpoint).Port; s.Stop(); statut = 200; }
        [TearDown] public void Fermer() { ecoute?.Close(); fil?.Join(TimeSpan.FromSeconds(5)); (ecoute, fil) = (null, null); }
        void Servir(params string[] corps)
        {
            var a = ecoute = new HttpListener(); a.Prefixes.Add("http://127.0.0.1:" + port + "/"); a.Start(); int code = statut;
            (fil = new Thread(() => {
                try { for (int i = 0; ; i++) { var c = a.GetContext(); byte[] octets = Encoding.UTF8.GetBytes(corps[Math.Min(i, corps.Length - 1)]);
                    c.Response.StatusCode = code; c.Response.ContentLength64 = octets.Length; c.Response.OutputStream.Write(octets, 0, octets.Length); c.Response.Close(); } }
                catch (Exception) { }
            })).Start();
        }
        ClientAtlas Client() => new ClientAtlas(port, TimeSpan.FromSeconds(5));
        static string Muter(string temoin, string ancien, string nouveau)
        {
            int i = temoin.IndexOf(ancien, StringComparison.Ordinal);
            Assert.IsTrue(i >= 0 && temoin.LastIndexOf(ancien, StringComparison.Ordinal) == i, "motif absent ou répété : " + ancien);
            return temoin.Substring(0, i) + nouveau + temoin.Substring(i + ancien.Length);
        }
        static PointCarte Brut(object point) { var p = (Dictionary<string, object>)point; return new PointCarte((double)p["x_m"], (double)p["y_m"]); }
        static List<Dictionary<string, object>> Liste(Dictionary<string, object> racine, string cle) => ((List<object>)racine[cle]).Cast<Dictionary<string, object>>().ToList();

        // Chaque fleuve, mer, région et siège du corps réel est lu avec son nom et ses points, entrée par entrée et dans l'ordre.
        [Test] public void L_atlas_se_lit_tel_que_servi()
        {
            string corps = EuropeDeTest.Corps(Atlas); var brut = LecteurJson.LireObjet(corps); Servir(corps);
            AtlasLu a;
            using (var c = Client()) { var l = c.Lire(); Assert.IsTrue(l.Presente && l.Absence == null, l.Absence); a = l.Donnees; }
            Assert.AreEqual("world-1400-v1", a.Version); Assert.AreEqual((string)brut["version"], a.Version);
            var fleuves = Liste(brut, "fleuves"); Assert.Greater(fleuves.Count, 0, "aucun fleuve servi"); Assert.AreEqual(fleuves.Count, a.Fleuves.Count);
            for (int i = 0; i < fleuves.Count; i++)
            {
                var lignes = ((List<object>)fleuves[i]["lignes"]).Cast<List<object>>().ToList(); var lu = a.Fleuves[i];
                Assert.AreEqual((string)fleuves[i]["nom"], lu.Nom, "fleuves[" + i + "].nom"); Assert.AreEqual(lignes.Count, lu.Lignes.Count, "fleuves[" + i + "].lignes");
                for (int j = 0; j < lignes.Count; j++)
                {
                    Assert.GreaterOrEqual(lu.Lignes[j].Count, 2); Assert.AreEqual(lignes[j].Count, lu.Lignes[j].Count, "fleuves[" + i + "].lignes[" + j + "]");
                    for (int k = 0; k < lignes[j].Count; k++) Assert.AreEqual(Brut(lignes[j][k]), lu.Lignes[j][k], "fleuves[" + i + "].lignes[" + j + "][" + k + "]");
                }
            }
            var nil = a.Fleuves.Single(f => f.Nom == "Nil"); Assert.AreEqual(2, nil.Lignes.Count);
            foreach (string cle in new[] { "mers", "regions" })
            {
                var bruts = Liste(brut, cle); var lus = cle == "mers" ? a.Mers : a.Regions; Assert.Greater(bruts.Count, 0, "aucune entrée servie : " + cle); Assert.AreEqual(bruts.Count, lus.Count, cle);
                for (int i = 0; i < bruts.Count; i++) { Assert.AreEqual((string)bruts[i]["nom"], lus[i].Nom, cle + "[" + i + "].nom"); Assert.AreEqual(Brut(bruts[i]), lus[i].Point, cle + "[" + i + "]"); }
            }
            var sieges = Liste(brut, "sieges"); Assert.Greater(sieges.Count, 0, "aucun siège servi"); Assert.AreEqual(sieges.Count, a.Sieges.Count);
            for (int i = 0; i < sieges.Count; i++)
            {
                Assert.AreEqual((string)sieges[i]["nom"], a.Sieges[i].Nom, "sieges[" + i + "].nom"); Assert.AreEqual((string)sieges[i]["maison"], a.Sieges[i].Maison, "sieges[" + i + "].maison");
                Assert.AreEqual(Brut(sieges[i]), a.Sieges[i].Point, "sieges[" + i + "]");
            }
            var biskra = a.Sieges.Single(s => s.Nom == "Biskra"); Assert.AreEqual("seigneurie-6", biskra.Maison);
            Assert.Throws<NotSupportedException>(() => ((IList<FleuveDeLAtlas>)a.Fleuves).Add(null)); Assert.Throws<NotSupportedException>(() => ((IList<PointCarte>)nil.Lignes[0]).Add(default(PointCarte)));
            Assert.Throws<NotSupportedException>(() => ((IList<NomDeLAtlas>)a.Mers).Add(null)); Assert.Throws<NotSupportedException>(() => ((IList<SiegeDeLAtlas>)a.Sieges).Add(null));
        }

        // L'atlas que `EuropeDeTest` sert aux autres tests est celui que le client lit du même corps.
        [Test] public void L_atlas_de_l_Europe_de_test_est_celui_du_corps_servi()
        {
            var brut = EuropeDeTest.AtlasBrut; var a = EuropeDeTest.AtlasEurope;
            Assert.IsNotNull(a); Assert.AreEqual(Liste(brut, "fleuves").Count, a.Fleuves.Count); Assert.AreEqual(Liste(brut, "mers").Count, a.Mers.Count);
            Assert.AreEqual(Liste(brut, "regions").Count, a.Regions.Count); Assert.AreEqual(Liste(brut, "sieges").Count, a.Sieges.Count); Assert.IsTrue(a.Sieges.Any(s => s.Nom == "Biskra"));
        }

        // Une version servie à null est une mesure ; un texte vide ou un nombre est une faute.
        [Test] public void Une_version_nulle_est_une_mesure_et_une_version_vide_ou_numerique_est_refusee()
        {
            string corps = EuropeDeTest.Corps(Atlas);
            Servir(Muter(corps, "\"version\":\"world-1400-v1\"", "\"version\":null"), Muter(corps, "\"version\":\"world-1400-v1\"", "\"version\":\"\""), Muter(corps, "\"version\":\"world-1400-v1\"", "\"version\":3"));
            using (var c = Client())
            {
                var nulle = c.Lire(); Assert.IsTrue(nulle.Presente, nulle.Absence); Assert.IsNull(nulle.Donnees.Version); Assert.Greater(nulle.Donnees.Fleuves.Count, 0);
                foreach (var l in new[] { c.Lire(), c.Lire() }) { Assert.IsFalse(l.Presente); StringAssert.StartsWith("atlas : ", l.Absence); StringAssert.Contains("version", l.Absence); }
            }
        }

        // Une clé absente refuse toute la réponse et nomme son chemin. Chaque clé est renommée dans le corps réel, une à une.
        [Test] public void Une_cle_absente_refuse_la_reponse_et_nomme_son_chemin()
        {
            string c0 = EuropeDeTest.Corps(Atlas);
            var fautes = new List<(string corps, string chemin)>
            {
                (Muter(c0, "\"crs\":", "\"crss\":"), "crs"), (Muter(c0, "\"version\":", "\"versions\":"), "version"),
                (Muter(c0, "\"fleuves\":[", "\"fleuvess\":["), "fleuves"), (Muter(c0, "\"mers\":[", "\"merss\":["), "mers"),
                (Muter(c0, "\"regions\":[", "\"regionss\":["), "regions"), (Muter(c0, "\"sieges\":[", "\"siegess\":["), "sieges"),
                (Muter(c0, "\"nom\":\"Loire\"", "\"noms\":\"Loire\""), "fleuves[0].nom"), (Muter(c0, "{\"lignes\":[[{\"x_m\":3863724", "{\"lignees\":[[{\"x_m\":3863724"), "fleuves[0].lignes"),
                (Muter(c0, "{\"x_m\":3863724,\"y_m\":2432475}", "{\"xm\":3863724,\"y_m\":2432475}"), "fleuves[0].lignes[0][0].x_m"),
                (Muter(c0, "{\"x_m\":3863724,\"y_m\":2432475}", "{\"x_m\":3863724,\"ym\":2432475}"), "fleuves[0].lignes[0][0].y_m"),
                (Muter(c0, "{\"nom\":\"Méditerranée\",", "{\"noms\":\"Méditerranée\","), "mers[0].nom"), (Muter(c0, "\"nom\":\"Méditerranée\",\"x_m\":", "\"nom\":\"Méditerranée\",\"xm\":"), "mers[0].x_m"),
                (Muter(c0, "{\"nom\":\"Aquitaine\",\"x_m\":3528218,\"y_m\":", "{\"nom\":\"Aquitaine\",\"x_m\":3528218,\"ym\":"), "regions[0].y_m"),
                (Muter(c0, "{\"nom\":\"Aquitaine\",", "{\"noms\":\"Aquitaine\","), "regions[0].nom"),
                (Muter(c0, "\"maison\":\"institution-71\",\"nom\":\"Aschaffenbourg\"", "\"maison\":\"institution-71\",\"noms\":\"Aschaffenbourg\""), "sieges[0].nom"),
                (Muter(c0, "\"maison\":\"institution-71\",\"nom\":\"Aschaffenbourg\"", "\"maisons\":\"institution-71\",\"nom\":\"Aschaffenbourg\""), "sieges[0].maison"),
                (Muter(c0, "\"maison\":\"institution-71\",\"nom\":\"Aschaffenbourg\",\"x_m\":", "\"maison\":\"institution-71\",\"nom\":\"Aschaffenbourg\",\"xm\":"), "sieges[0].x_m"),
            };
            Servir(fautes.Select(f => f.corps).ToArray());
            using (var c = Client())
                foreach (var (corps, chemin) in fautes)
                {
                    var l = c.Lire();
                    Assert.IsTrue(!l.Presente && l.Donnees == null && !string.IsNullOrEmpty(l.Absence), chemin + " : lu malgré la faute");
                    StringAssert.StartsWith("atlas : ", l.Absence); StringAssert.Contains("clé absente : " + chemin, l.Absence);
                }
        }

        // Une projection autre que EPSG:3035, un nom vide, une valeur du mauvais type, un point non numérique, une ligne trop courte et un fleuve sans ligne sont refusés.
        [Test] public void Un_atlas_mal_servi_est_refuse_et_la_cle_est_nommee()
        {
            string c0 = EuropeDeTest.Corps(Atlas);
            var fautes = new List<(string corps, string cle)>
            {
                (Muter(c0, "\"crs\":\"EPSG:3035\"", "\"crs\":\"EPSG:4326\""), "crs"), (Muter(c0, "\"crs\":\"EPSG:3035\"", "\"crs\":null"), "crs"),
                (Muter(c0, "\"nom\":\"Loire\"", "\"nom\":\"\""), "fleuves[0].nom"), (Muter(c0, "\"nom\":\"Loire\"", "\"nom\":3"), "fleuves[0].nom"),
                (Muter(c0, "{\"nom\":\"Méditerranée\",", "{\"nom\":\" \","), "mers[0].nom"), (Muter(c0, "{\"nom\":\"Aquitaine\",", "{\"nom\":\"\","), "regions[0].nom"),
                (Muter(c0, "\"nom\":\"Aschaffenbourg\"", "\"nom\":\"\""), "sieges[0].nom"), (Muter(c0, "\"maison\":\"institution-71\"", "\"maison\":\"\""), "sieges[0].maison"),
                (Muter(c0, "\"fleuves\":[", "\"fleuves\":{},\"fleuvesx\":["), "fleuves"), (Muter(c0, "\"mers\":[", "\"mers\":3,\"mersx\":["), "mers"),
                (Muter(c0, "\"regions\":[", "\"regions\":\"\",\"regionsx\":["), "regions"), (Muter(c0, "\"sieges\":[", "\"sieges\":null,\"siegesx\":["), "sieges"),
                (Muter(c0, "\"fleuves\":[{", "\"fleuves\":[3,{"), "fleuves[0]"),
                (Muter(c0, "{\"lignes\":[[{\"x_m\":3863724", "{\"lignes\":{},\"lignesx\":[[{\"x_m\":3863724"), "fleuves[0].lignes"),
                (Muter(c0, "{\"lignes\":[[{\"x_m\":3863724", "{\"lignes\":[3],\"lignesx\":[[{\"x_m\":3863724"), "fleuves[0].lignes[0]"),
                (Muter(c0, "{\"x_m\":3863724,\"y_m\":2432475}", "{\"x_m\":\"loin\",\"y_m\":2432475}"), "fleuves[0].lignes[0][0].x_m"),
                (Muter(c0, "{\"x_m\":3863724,\"y_m\":2432475}", "{\"x_m\":3863724,\"y_m\":null}"), "fleuves[0].lignes[0][0].y_m"),
                (Muter(c0, "{\"x_m\":3863724,\"y_m\":2432475}", "7"), "fleuves[0].lignes[0][0]"),
                (Muter(c0, "\"x_m\":5057704", "\"x_m\":\"loin\""), "mers[0].x_m"), (Muter(c0, "\"y_m\":2440795", "\"y_m\":true"), "regions[0].y_m"),
                (Muter(c0, "\"x_m\":4260015", "\"x_m\":[]"), "sieges[0].x_m"),
                (Muter(c0, "{\"lignes\":[[{\"x_m\":3863724", "{\"lignes\":[[{\"x_m\":1,\"y_m\":2}],[{\"x_m\":3863724"), "fleuves[0].lignes[0]"),
                (Muter(c0, "{\"lignes\":[[{\"x_m\":3863724", "{\"lignes\":[],\"lignesx\":[[{\"x_m\":3863724"), "fleuves[0].lignes"),
            };
            Servir(fautes.Select(f => f.corps).ToArray());
            using (var c = Client())
                foreach (var (corps, cle) in fautes)
                {
                    var l = c.Lire();
                    Assert.IsTrue(!l.Presente && l.Donnees == null && !string.IsNullOrEmpty(l.Absence), cle + " : lu malgré la faute"); StringAssert.StartsWith("atlas : ", l.Absence); StringAssert.Contains(cle, l.Absence);
                }
        }

        [Test] public void Un_service_absent_est_une_absence_qui_nomme_sa_cause()
        {
            using (var c = new ClientAtlas(port, TimeSpan.FromSeconds(5)))
            {
                var l = c.Lire(); Assert.IsTrue(!l.Presente && l.Donnees == null); StringAssert.StartsWith("atlas : service absent sur 127.0.0.1:" + port, l.Absence);
            }
        }

        [Test] public void Un_statut_500_est_une_absence_qui_le_nomme()
        {
            statut = 500; Servir("{\"erreur\": \"atlas invalide\"}");
            using (var c = Client())
            {
                var l = c.Lire(); Assert.IsTrue(!l.Presente && l.Donnees == null);
                StringAssert.StartsWith("atlas : statut 500", l.Absence); StringAssert.Contains("atlas invalide", l.Absence);
            }
        }

        // Un service qui ne répond pas dans le délai est une absence qui dit le délai.
        [Test] public void Un_service_trop_lent_est_une_absence_qui_dit_le_delai()
        {
            var sourde = new TcpListener(IPAddress.Loopback, port); sourde.Start();
            try
            {
                using (var c = new ClientAtlas(port, TimeSpan.FromMilliseconds(300)))
                {
                    var l = c.Lire(); Assert.IsTrue(!l.Presente && l.Donnees == null); StringAssert.StartsWith("atlas : délai dépassé (300 ms) sur 127.0.0.1:" + port, l.Absence);
                }
            }
            finally { sourde.Stop(); }
        }
    }
}
