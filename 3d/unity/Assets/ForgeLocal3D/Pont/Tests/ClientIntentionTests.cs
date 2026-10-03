using System;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using NUnit.Framework;

namespace Forge.Pont.Tests
{
    // Lot #291 — un faux service local rend un statut et des octets fixés et retient la dernière requête.
    public sealed class ClientIntentionTests
    {
        private const string Intention = "{\"type\":\"tracer_route\",\"cell\":9922,\"points\":[[0,0],[40,0],[40,25]],\"largeur_m\":4}";
        private const string Accepte = "{\"acceptee\":true,\"appliquee_au_tick\":7}";
        private const int Ferme = 0, Muet = -1; // statuts fictifs : aucun faux service, ou un faux service qui ne répond pas
        private int port;
        private HttpListener ecoute;
        private Thread fil;
        private volatile Tuple<string, string, byte[]> recue; // méthode, chemin, octets du corps

        [SetUp]
        public void PortLibre()
        {
            var sonde = new TcpListener(IPAddress.Loopback, 0);
            sonde.Start();
            port = ((IPEndPoint)sonde.LocalEndpoint).Port;
            sonde.Stop();
            recue = null;
        }
        [TearDown]
        public void Fermer()
        {
            ecoute?.Close();
            fil?.Join(TimeSpan.FromSeconds(5));
            (ecoute, fil) = (null, null);
        }
        // Retient chaque requête puis rend le statut et les octets fixés (`Muet` : jamais), jusqu'à Fermer qui fait lever GetContext.
        private void Servir(int statut, string corps)
        {
            var auditeur = ecoute = new HttpListener();
            auditeur.Prefixes.Add("http://127.0.0.1:" + port + "/");
            auditeur.Start();
            (fil = new Thread(() => { try { while (true) Repondre(auditeur.GetContext(), statut, Encoding.UTF8.GetBytes(corps)); } catch (Exception) { } }) { IsBackground = true }).Start();
        }
        private void Repondre(HttpListenerContext contexte, int statut, byte[] octets)
        {
            var lu = new MemoryStream(); contexte.Request.InputStream.CopyTo(lu);
            recue = Tuple.Create(contexte.Request.HttpMethod, contexte.Request.Url.AbsolutePath, lu.ToArray());
            if (statut == Muet) return;
            contexte.Response.StatusCode = statut;
            contexte.Response.Close(octets, true);
        }
        private RecuIntention Deposer(int ms = 5000) { using (var client = new ClientIntention(port, TimeSpan.FromMilliseconds(ms))) return client.Deposer(Intention); }

        // Un reçu se relit tel que le service l'écrit (le tick sans +1, la raison mot pour mot) ; l'intention arrive octet pour octet.
        [TestCase(200, Accepte, 7L, null)]
        [TestCase(400, "{\"acceptee\":false,\"erreur\":\"type d'intention inconnu : 'x'\"}", null, "type d'intention inconnu : 'x'")]
        [TestCase(409, "{\"acceptee\":false,\"erreur\":\"départ déjà choisi : X\"}", null, "départ déjà choisi : X")]
        public void UnRecuEstReluTelQueLeServiceLEcrit(int statut, string corps, long? tick, string raison)
        {
            Servir(statut, corps);
            RecuIntention recu = Deposer();
            Assert.IsTrue(recu.Presente && recu.Acceptee == (statut == 200) && recu.Statut == statut && recu.Absence == null, recu.Absence);
            Assert.AreEqual(tick, recu.AppliqueeAuTick, "le tick du service, sans +1");
            Assert.AreEqual(raison, recu.Erreur, "la raison, mot pour mot");
            Assert.AreEqual("POST /intention", recue.Item1 + " " + recue.Item2);
            CollectionAssert.AreEqual(Encoding.UTF8.GetBytes(Intention), recue.Item3, "l'intention arrive octet pour octet");
        }

        // Statut et corps doivent dire la même chose, le tick être écrit exactement ; sinon pas de reçu.
        [TestCase(200, "{\"acceptee\":false,\"erreur\":\"incohérent\"}", "200", "acceptee")]
        [TestCase(200, "{\"acceptee\":true}", "200", "appliquee_au_tick")]
        [TestCase(200, "{\"acceptee\":true,\"appliquee_au_tick\":9007199254740990.5}", "200", "appliquee_au_tick")]
        [TestCase(200, "{\"acceptee\":true,\"appliquee_au_tick\":7.0000000000000001}", "200", "appliquee_au_tick")]
        [TestCase(200, "{\"acceptee\":true,\"appliquee_au_tic\\u006b\":7.0000000000000001,\"extra\":{\"appliquee_au_tick\":7}}", "200", "appliquee_au_tick")]
        [TestCase(400, Accepte, "400", "acceptee")]
        [TestCase(200, "{\"acceptee\":true,\"appliquee_au_tick\":7", "200", "JSON invalide à la position")]
        [TestCase(404, "{\"erreur\":\"chemin inconnu : '/x'\"}", "404", "{\"erreur\":\"chemin inconnu : '/x'\"}")]
        [TestCase(Ferme, null, "service absent sur 127.0.0.1:<port>", "service absent")]
        [TestCase(Muet, Accepte, "délai dépassé", "300 ms")]
        public void SansRecuUneAbsenceNommeSaCause(int statut, string corps, string attendu, string cause)
        {
            if (statut != Ferme) Servir(statut, corps);
            RecuIntention recu = Deposer(statut == Muet ? 300 : 5000);
            Assert.IsTrue(!recu.Presente && !recu.Acceptee && recu.AppliqueeAuTick == null && recu.Statut == null && recu.Erreur == null, "ni présent ni accepté");
            StringAssert.StartsWith("intention : ", recu.Absence);
            StringAssert.Contains(attendu.Replace("<port>", port.ToString()), recu.Absence);
            StringAssert.Contains(cause, recu.Absence);
        }

        [Test]
        public void LesFautesDeLAppelantLeventAvantToutEnvoi()
        {
            Servir(200, Accepte);
            using (var client = new ClientIntention(port, TimeSpan.FromSeconds(5)))
                foreach (string faute in new[] { null, "[1]", "{" })
                    Assert.Throws<ArgumentException>(() => client.Deposer(faute));
            Assert.IsNull(recue, "aucune requête ne part pour une faute de l'appelant");
            foreach (int hors in new[] { 0, 65536 })
                Assert.Throws<ArgumentOutOfRangeException>(() => new ClientIntention(hors, TimeSpan.FromSeconds(5)));
            foreach (TestDelegate fabrique in new TestDelegate[] { () => RecuIntention.Refusee(404, "x"), () => RecuIntention.Refusee(400, ""),
                () => RecuIntention.Absente(""), () => RecuIntention.AccepteeAu(-1) })
                Assert.Throws<ArgumentException>(fabrique);
        }
    }
}
