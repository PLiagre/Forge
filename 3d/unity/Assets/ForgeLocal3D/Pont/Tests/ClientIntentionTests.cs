using System;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using NUnit.Framework;

namespace Forge.Pont.Tests
{
    // Lot #291 — un faux service local rend un statut et des octets fixés, et retient la dernière
    // requête ; le client relit le reçu tel quel, ou rend une absence qui nomme sa cause.
    public sealed class ClientIntentionTests
    {
        private const string Intention = "{\"type\":\"tracer_route\",\"cell\":9922,\"points\":[[0,0],[40,0],[40,25]],\"largeur_m\":4}";
        private const string Accepte = "{\"acceptee\":true,\"appliquee_au_tick\":7}";
        private static readonly TimeSpan Delai = TimeSpan.FromSeconds(5);

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
            ecoute = null;
            fil?.Join(TimeSpan.FromSeconds(5));
            fil = null;
        }

        // `muet` : la requête est lue et retenue, jamais répondue (le délai doit dépasser).
        private void Servir(int statut, string corps, bool muet = false)
        {
            byte[] octets = Encoding.UTF8.GetBytes(corps);
            var auditeur = ecoute = new HttpListener();
            ecoute.Prefixes.Add("http://127.0.0.1:" + port + "/");
            ecoute.Start();
            fil = new Thread(() =>
            {
                try
                {
                    while (true)
                    {
                        HttpListenerContext contexte = auditeur.GetContext();
                        var lu = new MemoryStream();
                        contexte.Request.InputStream.CopyTo(lu);
                        recue = Tuple.Create(contexte.Request.HttpMethod, contexte.Request.Url.AbsolutePath, lu.ToArray());
                        if (muet) continue;
                        contexte.Response.StatusCode = statut;
                        contexte.Response.ContentLength64 = octets.Length;
                        contexte.Response.OutputStream.Write(octets, 0, octets.Length);
                        contexte.Response.OutputStream.Close();
                    }
                }
                catch (Exception) { }
            }) { IsBackground = true };
            fil.Start();
        }

        private RecuIntention Deposer(int millisecondes = 5000)
        {
            using (var client = new ClientIntention(port, TimeSpan.FromMilliseconds(millisecondes))) return client.Deposer(Intention);
        }

        private string Absence(int millisecondes = 5000)
        {
            RecuIntention recu = Deposer(millisecondes);
            Assert.IsFalse(recu.Presente || recu.Acceptee, "sans reçu, ni présent ni accepté");
            Assert.IsTrue(recu.AppliqueeAuTick == null && recu.Statut == null && recu.Erreur == null);
            StringAssert.StartsWith("intention : ", recu.Absence);
            return recu.Absence;
        }

        [Test]
        public void UnRecuAccepteEstReluExactementEtLIntentionArriveIntacte()
        {
            Servir(200, Accepte);
            RecuIntention recu = Deposer();
            Assert.IsTrue(recu.Presente && recu.Acceptee, recu.Absence);
            Assert.IsTrue(recu.AppliqueeAuTick == 7, "le tick du service, sans +1 : " + recu.AppliqueeAuTick);
            Assert.IsTrue(recu.Statut == 200 && recu.Erreur == null && recu.Absence == null);
            Assert.AreEqual("POST", recue.Item1);
            Assert.AreEqual("/intention", recue.Item2);
            CollectionAssert.AreEqual(Encoding.UTF8.GetBytes(Intention), recue.Item3, "l'intention arrive octet pour octet");
        }

        [TestCase(400, "{\"acceptee\":false,\"erreur\":\"type d'intention inconnu : 'x'\"}", "type d'intention inconnu : 'x'")]
        [TestCase(409, "{\"acceptee\":false,\"erreur\":\"départ déjà choisi : X\"}", "départ déjà choisi : X")]
        public void UnRefusResteUnRefusAvecLaRaisonDuService(int statut, string corps, string raison)
        {
            Servir(statut, corps);
            RecuIntention recu = Deposer();
            Assert.IsTrue(recu.Presente && !recu.Acceptee, recu.Absence);
            Assert.IsTrue(recu.AppliqueeAuTick == null && recu.Statut == statut && recu.Absence == null);
            Assert.AreEqual(raison, recu.Erreur, "la raison, mot pour mot");
        }

        // Statut et corps doivent dire la même chose ; un corps cassé ou un autre statut n'est pas un reçu.
        [TestCase(200, "{\"acceptee\":false,\"erreur\":\"incohérent\"}", "acceptee")]
        [TestCase(200, "{\"acceptee\":true}", "appliquee_au_tick")]
        [TestCase(400, Accepte, "acceptee")]
        [TestCase(200, "{\"acceptee\":true,\"appliquee_au_tick\":7", "JSON invalide à la position")]
        [TestCase(404, "{\"erreur\":\"chemin inconnu : '/x'\"}", "{\"erreur\":\"chemin inconnu : '/x'\"}")]
        public void UnCorpsQuiNeConcordePasEstUneAbsenceQuiNommeLeStatutEtLaCause(int statut, string corps, string cause)
        {
            Servir(statut, corps);
            string absence = Absence();
            StringAssert.Contains(statut.ToString(), absence);
            StringAssert.Contains(cause, absence);
        }

        [Test]
        public void UnPortFermeRendUneAbsenceQuiNommeLePort()
        {
            StringAssert.Contains("service absent sur 127.0.0.1:" + port, Absence());
        }

        [Test]
        public void UnServiceMuetRendUneAbsenceDeDelaiDepasse()
        {
            Servir(200, Accepte, muet: true);
            StringAssert.Contains("délai dépassé", Absence(300));
        }

        [Test]
        public void LesFautesDeLAppelantLeventAvantToutEnvoi()
        {
            Servir(200, Accepte);
            using (var client = new ClientIntention(port, Delai))
                foreach (string faute in new[] { null, "[1]", "{" })
                    Assert.Throws<ArgumentException>(() => client.Deposer(faute));
            Assert.IsNull(recue, "aucune requête ne part pour une faute de l'appelant");
            Assert.Throws<ArgumentOutOfRangeException>(() => new ClientIntention(0, Delai));
            Assert.Throws<ArgumentOutOfRangeException>(() => new ClientIntention(65536, Delai));
        }

        [Test]
        public void UneFabriqueHorsDeSesBornesLeve()
        {
            Assert.Throws<ArgumentException>(() => RecuIntention.Refusee(404, "x"));
            Assert.Throws<ArgumentException>(() => RecuIntention.Refusee(400, ""));
            Assert.Throws<ArgumentException>(() => RecuIntention.Absente(""));
            Assert.Throws<ArgumentException>(() => RecuIntention.AccepteeAu(-1));
        }
    }
}
