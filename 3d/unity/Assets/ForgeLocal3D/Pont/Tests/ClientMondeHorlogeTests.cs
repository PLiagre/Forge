using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using NUnit.Framework;

namespace Forge.Pont.Tests
{
    // Lot #521 — un faux service local rend le monde et l'horloge ; les clients les relisent tels quels,
    // transmettent une vitesse sans avancer le temps, ou rendent une absence qui nomme sa cause.
    public sealed class ClientMondeHorlogeTests
    {
        // Les témoins du brief : 10417 est inhabitée (0 est une mesure), sa faim et sa dette ne sont pas calculées (-1).
        private const string CELLULE_A = "{\"cell_id\":9922,\"population\":123,\"hunger_ticks\":3,\"food_deficit_kg\":12.5}";
        private const string CELLULE_B = "{\"cell_id\":10417,\"population\":0,\"hunger_ticks\":-1,\"food_deficit_kg\":-1}";
        private const string CELLULES = "\"cell_count\":2,\"cells\":[" + CELLULE_A + "," + CELLULE_B + "]";
        private const string MONDE = "{\"tick\":5,\"date\":{\"annee\":1400,\"jour_de_l_annee\":6}," + CELLULES + "}";
        private const string HORLOGE = "{\"tick\":5,\"date\":{\"annee\":1400,\"jour_de_l_annee\":6},\"jours_par_seconde\":2.5,\"duree_dernier_tick_ms\":42.25,\"budget_tick_ms\":100}";
        private const int Muet = -1; // statut fictif : le faux service reçoit la requête et ne répond jamais
        public enum Operation { Monde, Horloge, Regler }

        private int port;
        private HttpListener ecoute;
        private Thread fil;
        private readonly List<string> recues = new List<string>(); // « MÉTHODE chemin?requête [corps] », dans l'ordre reçu

        [SetUp]
        public void PortLibre()
        {
            var sonde = new TcpListener(IPAddress.Loopback, 0);
            sonde.Start();
            port = ((IPEndPoint)sonde.LocalEndpoint).Port;
            sonde.Stop();
            lock (recues) recues.Clear();
        }

        [TearDown]
        public void Fermer()
        {
            ecoute?.Close();
            fil?.Join(TimeSpan.FromSeconds(5));
            (ecoute, fil) = (null, null);
        }

        // Rend les réponses dans l'ordre, la dernière ensuite ; retient chaque requête avant de répondre, jusqu'à Fermer.
        private void Servir(params (int statut, string corps)[] reponses)
        {
            var auditeur = ecoute = new HttpListener();
            auditeur.Prefixes.Add("http://127.0.0.1:" + port + "/");
            auditeur.Start();
            (fil = new Thread(() =>
            {
                try
                {
                    for (int i = 0; ; i++)
                    {
                        HttpListenerContext contexte = auditeur.GetContext();
                        var corps = new MemoryStream();
                        contexte.Request.InputStream.CopyTo(corps);
                        lock (recues) recues.Add(contexte.Request.HttpMethod + " " + contexte.Request.Url.PathAndQuery + " [" + Encoding.UTF8.GetString(corps.ToArray()) + "]");
                        (int statut, string texte) = reponses[Math.Min(i, reponses.Length - 1)];
                        if (statut == Muet) continue;
                        if (statut == 302) contexte.Response.RedirectLocation = "/ailleurs";
                        contexte.Response.StatusCode = statut;
                        contexte.Response.Close(Encoding.UTF8.GetBytes(texte), true);
                    }
                }
                catch (Exception) { }
            }) { IsBackground = true }).Start();
        }

        private string[] Recues() { lock (recues) return recues.ToArray(); }

        // `ancien` paraît exactement une fois dans `source` : la mutation porte sur l'élément voulu, et sur lui seul.
        private static string RemplacerUneFois(string source, string ancien, string nouveau)
        {
            int premier = source.IndexOf(ancien, StringComparison.Ordinal);
            Assert.IsTrue(premier >= 0 && premier == source.LastIndexOf(ancien, StringComparison.Ordinal), "pas exactement une fois dans le témoin : " + ancien);
            return source.Substring(0, premier) + nouveau + source.Substring(premier + ancien.Length);
        }

        // Une absence non vide, préfixée, sans aucune donnée, qui contient chacun des `attendus`.
        private static void Absente<T>(Lecture<T> lecture, string prefixe, params string[] attendus) where T : class
        {
            Assert.IsTrue(!lecture.Presente && lecture.Donnees == null, "une réponse fautive ne rend aucune donnée");
            StringAssert.StartsWith(prefixe, lecture.Absence);
            foreach (string attendu in attendus) StringAssert.Contains(attendu, lecture.Absence);
        }

        private static void Cellule(CelluleDuMonde cellule, long id, long population, long faim, double dette) =>
            Assert.IsTrue(cellule.CellId == id && cellule.Population == population && cellule.HungerTicks == faim && cellule.FoodDeficitKg == dette,
                "(" + id + ", " + population + ", " + faim + ", " + dette + ") attendu, reçu (" + cellule.CellId + ", " + cellule.Population + ", " + cellule.HungerTicks + ", " + cellule.FoodDeficitKg + ")");

        private static void Horloge(Lecture<HorlogeLue> lecture, long tick, long jour, double vitesse)
        {
            Assert.IsTrue(lecture.Presente && lecture.Absence == null, lecture.Absence);
            HorlogeLue h = lecture.Donnees;
            Assert.IsTrue(h.Tick == tick && h.Date.Annee == 1400 && h.Date.JourDeLAnnee == jour && h.JoursParSeconde == vitesse,
                "(" + tick + ", 1400, " + jour + ", " + vitesse + ") attendu, reçu (" + h.Tick + ", " + h.Date.Annee + ", " + h.Date.JourDeLAnnee + ", " + h.JoursParSeconde + ")");
        }

        [Test]
        public void LeMondeServiEstReluExactementPuisRelu()
        {
            string suivant = "{\"tick\":6,\"date\":{\"annee\":1400,\"jour_de_l_annee\":7},\"cell_count\":2,\"cells\":[{\"cell_id\":9922,\"population\":120,\"hunger_ticks\":4,\"food_deficit_kg\":20.75,\"stocks\":{\"ble\":3}},"
                + CELLULE_B + "],\"maison_du_joueur\":27}";
            Servir((200, MONDE), (200, suivant));
            using (var client = new ClientMonde(port, TimeSpan.FromSeconds(5)))
            {
                Lecture<MondeLu> premiere = client.Lire(), seconde = client.Lire();
                CollectionAssert.AreEqual(new[] { "GET /monde []", "GET /monde []" }, Recues(), "GET /monde, sans requête ni corps");
                Assert.IsTrue(premiere.Presente && premiere.Absence == null, premiere.Absence);
                MondeLu monde = premiere.Donnees;
                Assert.IsTrue(monde.Tick == 5 && monde.Date.Annee == 1400 && monde.Date.JourDeLAnnee == 6 && monde.CellCount == 2 && monde.Cellules.Count == 2);
                Cellule(monde.Cellules[0], 9922, 123, 3, 12.5);
                Cellule(monde.Cellules[1], 10417, 0, -1, -1);
                Assert.Throws<NotSupportedException>(() => ((IList<CelluleDuMonde>)monde.Cellules).Add(null), "les cellules se lisent sans s'écrire");
                // La seconde lecture vient du service : tick, date, population et dette ont changé ; `stocks` et `maison_du_joueur` sont ignorés.
                Assert.IsTrue(seconde.Presente && seconde.Donnees.Tick == 6 && seconde.Donnees.Date.JourDeLAnnee == 7, seconde.Absence);
                Cellule(seconde.Donnees.Cellules[0], 9922, 120, 4, 20.75);
                Cellule(seconde.Donnees.Cellules[1], 10417, 0, -1, -1);
            }
        }

        [Test]
        public void LHorlogeEstLueSansRienEnvoyer()
        {
            Servir((200, HORLOGE));
            using (var client = new ClientHorloge(port, TimeSpan.FromSeconds(5))) Horloge(client.Lire(), 5, 6, 2.5);
            CollectionAssert.AreEqual(new[] { "GET /horloge []" }, Recues());
        }

        // La vitesse part en culture invariante même sous fr-FR ; la lecture rendue est celle du service (1.25 au tick 8 pour 2.5 demandé).
        [TestCase(0.0, "POST /vitesse?jours_par_seconde=0 []", "{\"tick\":5,\"date\":{\"annee\":1400,\"jour_de_l_annee\":6},\"jours_par_seconde\":0,\"duree_dernier_tick_ms\":42.25,\"budget_tick_ms\":100}", 5L, 6L, 0.0)]
        [TestCase(2.5, "POST /vitesse?jours_par_seconde=2.5 []", "{\"tick\":8,\"date\":{\"annee\":1400,\"jour_de_l_annee\":9},\"jours_par_seconde\":1.25}", 8L, 9L, 1.25)]
        public void ReglerTransmetLaVitesseEtRelitLaReponse(double demandee, string requete, string reponse, long tick, long jour, double rendue)
        {
            Servir((200, reponse));
            CultureInfo culture = CultureInfo.CurrentCulture;
            try
            {
                CultureInfo.CurrentCulture = new CultureInfo("fr-FR");
                using (var client = new ClientHorloge(port, TimeSpan.FromSeconds(5))) Horloge(client.Regler(demandee), tick, jour, rendue);
            }
            finally { CultureInfo.CurrentCulture = culture; }
            CollectionAssert.AreEqual(new[] { requete }, Recues(), "un seul POST /vitesse, sans corps, jamais /tick");
        }

        // Une lecture réussie, puis une panne : l'absence est nouvelle et ne présente aucune ancienne donnée. Aucune redirection n'est suivie.
        [Test]
        public void UnePanneRendUneAbsenceQuiNommeSaCause([Values] Operation operation, [Values("fermé", "muet", "400", "500", "302", "json")] string panne)
        {
            string temoin = operation == Operation.Monde ? MONDE : HORLOGE, prefixe = operation == Operation.Monde ? "monde : " : "horloge : ";
            int statut = panne == "muet" ? Muet : panne == "json" || panne == "fermé" ? 200 : int.Parse(panne);
            Servir((200, temoin), (statut, panne == "json" ? temoin.Substring(0, temoin.Length - 1) : statut == 200 ? temoin : "{\"erreur\":\"panne " + panne + "\"}"));
            TimeSpan delai = TimeSpan.FromMilliseconds(panne == "muet" ? 300 : 5000);
            using (var monde = new ClientMonde(port, delai))
            using (var horloge = new ClientHorloge(port, delai))
            {
                Func<object> lire = operation == Operation.Monde ? (Func<object>)monde.Lire : operation == Operation.Horloge ? (Func<object>)horloge.Lire : () => horloge.Regler(2.5);
                object avant = lire();
                Assert.IsTrue(avant is Lecture<MondeLu> m ? m.Presente : ((Lecture<HorlogeLue>)avant).Presente, "la lecture d'avant la panne est présente");
                if (panne == "fermé") Fermer();
                var chrono = Stopwatch.StartNew();
                object apres = lire();
                string[] causes = panne == "fermé" ? new[] { "service absent sur 127.0.0.1:" + port } : panne == "muet" ? new[] { "délai dépassé (300 ms)" }
                    : panne == "json" ? new[] { "JSON invalide" } : new[] { "statut " + panne, "{\"erreur\":\"panne " + panne + "\"}" };
                if (apres is Lecture<MondeLu> lu) Absente(lu, prefixe, causes); else Absente((Lecture<HorlogeLue>)apres, prefixe, causes);
                if (panne == "muet") Assert.IsTrue(chrono.ElapsedMilliseconds >= 290, "attendu au moins 290 ms, mesuré " + chrono.ElapsedMilliseconds);
                if (panne != "fermé") Assert.AreEqual(2, Recues().Length, "deux requêtes, aucune redirection suivie");
            }
        }

        // Une seule faute par cas, même dans la seconde cellule ; `precision` resserre ce que l'absence dit en plus du chemin.
        [TestCase(true, "\"tick\":5,", "", "clé absente : tick", "absente")]
        [TestCase(true, "\"date\":{\"annee\":1400,\"jour_de_l_annee\":6},", "", "clé absente : date", "absente")]
        [TestCase(true, "\"annee\":1400,", "", "clé absente : date.annee", "absente")]
        [TestCase(true, ",\"jour_de_l_annee\":6", "", "clé absente : date.jour_de_l_annee", "absente")]
        [TestCase(true, "\"cell_count\":2,", "", "clé absente : cell_count", "absente")]
        [TestCase(true, "\"cells\":[", "\"cellules\":[", "clé absente : cells", "absente")]
        [TestCase(true, "\"cell_id\":10417,", "", "clé absente : cells[1].cell_id", "absente")]
        [TestCase(true, "\"population\":0,", "", "clé absente : cells[1].population", "absente")]
        [TestCase(true, "\"hunger_ticks\":-1,", "", "clé absente : cells[1].hunger_ticks", "absente")]
        [TestCase(true, ",\"food_deficit_kg\":-1", "", "clé absente : cells[1].food_deficit_kg", "absente")]
        [TestCase(true, "\"tick\":5", "\"tick\":null", "clé tick", "reçu null")]
        [TestCase(true, "\"annee\":1400", "\"annee\":\"1400\"", "clé date.annee", "un nombre fini")]
        [TestCase(true, "\"date\":{\"annee\":1400,\"jour_de_l_annee\":6}", "\"date\":\"1400-6\"", "clé date", "un objet")]
        [TestCase(true, "\"cells\":[", "\"cells\":7,\"x\":[", "clé cells", "un tableau")]
        [TestCase(true, "," + CELLULE_B, ",null", "clé cells[1]", "un objet")]
        [TestCase(true, "\"population\":123", "\"population\":true", "clé cells[0].population", "un nombre fini")]
        [TestCase(true, "\"food_deficit_kg\":12.5", "\"food_deficit_kg\":null", "clé cells[0].food_deficit_kg", "reçu null")]
        [TestCase(true, "\"tick\":5", "\"tick\":-1", "clé tick", "un entier ≥ 0")]
        [TestCase(true, "\"tick\":5", "\"tick\":5.5", "clé tick", "5.5")]
        [TestCase(true, "\"annee\":1400", "\"annee\":0", "clé date.annee", "un entier ≥ 1")]
        [TestCase(true, "\"jour_de_l_annee\":6", "\"jour_de_l_annee\":0", "clé date.jour_de_l_annee", "un entier ≥ 1")]
        [TestCase(true, "\"population\":0", "\"population\":-1", "clé cells[1].population", "un entier ≥ 0")]
        [TestCase(true, "\"hunger_ticks\":3", "\"hunger_ticks\":-2", "clé cells[0].hunger_ticks", "-1 (non calculé)")]
        [TestCase(true, "\"hunger_ticks\":3", "\"hunger_ticks\":3.5", "clé cells[0].hunger_ticks", "-1 (non calculé)")]
        [TestCase(true, "\"food_deficit_kg\":12.5", "\"food_deficit_kg\":-0.5", "clé cells[0].food_deficit_kg", "-1 (non calculé)")]
        [TestCase(true, "\"food_deficit_kg\":12.5", "\"food_deficit_kg\":1e400", "JSON invalide", "représentable")]
        [TestCase(true, "\"cell_count\":2", "\"cell_count\":3", "clé cell_count", "3 annoncées, 2 lues")]
        [TestCase(true, "\"cell_id\":10417", "\"cell_id\":9922", "clé cells[1].cell_id", "déjà lu")]
        [TestCase(true, "\"cell_id\":10417", "\"cell_id\":9007199254740992", "clé cells[1].cell_id", "sous 2^53")]
        [TestCase(true, CELLULES, "\"cell_count\":0,\"cells\":[]", "clé cells", "au moins une cellule")]
        [TestCase(false, "\"tick\":5,", "", "clé absente : tick", "absente")]
        [TestCase(false, "\"date\":{\"annee\":1400,\"jour_de_l_annee\":6},", "", "clé absente : date", "absente")]
        [TestCase(false, "\"annee\":1400,", "", "clé absente : date.annee", "absente")]
        [TestCase(false, ",\"jour_de_l_annee\":6", "", "clé absente : date.jour_de_l_annee", "absente")]
        [TestCase(false, "\"jours_par_seconde\":2.5,", "", "clé absente : jours_par_seconde", "absente")]
        [TestCase(false, "\"jours_par_seconde\":2.5", "\"jours_par_seconde\":null", "clé jours_par_seconde", "reçu null")]
        [TestCase(false, "\"jours_par_seconde\":2.5", "\"jours_par_seconde\":\"2.5\"", "clé jours_par_seconde", "un nombre fini")]
        [TestCase(false, "\"jours_par_seconde\":2.5", "\"jours_par_seconde\":-0.5", "clé jours_par_seconde", "un nombre ≥ 0")]
        [TestCase(false, "\"tick\":5", "\"tick\":9007199254740992", "clé tick", "sous 2^53")]
        [TestCase(false, "\"jour_de_l_annee\":6", "\"jour_de_l_annee\":-6", "clé date.jour_de_l_annee", "un entier ≥ 1")]
        public void UneReponseFautiveEstRefuseeEnNommantSonChemin(bool monde, string ancien, string nouveau, string chemin, string precision)
        {
            Servir((200, RemplacerUneFois(monde ? MONDE : HORLOGE, ancien, nouveau)));
            if (monde) using (var client = new ClientMonde(port, TimeSpan.FromSeconds(5))) Absente(client.Lire(), "monde : ", chemin, precision);
            else using (var client = new ClientHorloge(port, TimeSpan.FromSeconds(5))) Absente(client.Lire(), "horloge : ", chemin, precision);
        }

        // Le dernier entier sous 2^53 reste une lecture présente : la borne est stricte, pas plus large.
        [Test]
        public void LeDernierEntierSousDeuxPuissanceCinquanteTroisEstLu()
        {
            Servir((200, RemplacerUneFois(MONDE, "\"cell_id\":10417", "\"cell_id\":9007199254740991")));
            using (var client = new ClientMonde(port, TimeSpan.FromSeconds(5)))
            {
                Lecture<MondeLu> lecture = client.Lire();
                Assert.IsTrue(lecture.Presente && lecture.Donnees.Cellules[1].CellId == 9007199254740991L, lecture.Absence);
            }
        }

        [Test]
        public void LesFautesDeLAppelantLeventAvantToutEnvoi()
        {
            Servir((200, HORLOGE));
            using (var client = new ClientHorloge(port, TimeSpan.FromSeconds(5)))
                foreach (double vitesse in new[] { -0.5, double.NaN, double.PositiveInfinity, double.NegativeInfinity })
                    Assert.Throws<ArgumentOutOfRangeException>(() => client.Regler(vitesse), "vitesse " + vitesse);
            Assert.AreEqual(0, Recues().Length, "aucune requête ne part pour une vitesse refusée");
            foreach (int hors in new[] { 0, 65536 })
            {
                Assert.Throws<ArgumentOutOfRangeException>(() => new ClientMonde(hors, TimeSpan.FromSeconds(5)));
                Assert.Throws<ArgumentOutOfRangeException>(() => new ClientHorloge(hors, TimeSpan.FromSeconds(5)));
            }
            foreach (TimeSpan delai in new[] { TimeSpan.Zero, TimeSpan.FromMilliseconds(-5), Timeout.InfiniteTimeSpan, TimeSpan.MaxValue })
            {
                Assert.Throws<ArgumentOutOfRangeException>(() => new ClientMonde(port, delai));
                Assert.Throws<ArgumentOutOfRangeException>(() => new ClientHorloge(port, delai));
            }
            Assert.Throws<ArgumentException>(() => Lecture<MondeLu>.Absent(""));
            Assert.Throws<ArgumentNullException>(() => Lecture<HorlogeLue>.De(null));
        }
    }
}
