using System;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using NUnit.Framework;
using UnityEngine;

namespace Forge.Pont.Tests
{
    // Lot #186 — un faux service local rend un statut et des octets fixés ;
    // le client en relit les vrais chiffres, ou rend une absence qui nomme sa cause.
    public sealed class ClientLieuTests
    {
        private const long CellFigee = 9922;
        private static readonly TimeSpan Delai = TimeSpan.FromSeconds(5);

        private int port;
        private HttpListener ecoute;
        private Thread fil;

        [SetUp]
        public void PortLibre()
        {
            var sonde = new TcpListener(IPAddress.Loopback, 0);
            sonde.Start();
            port = ((IPEndPoint)sonde.LocalEndpoint).Port;
            sonde.Stop();
        }

        [TearDown]
        public void Fermer()
        {
            if (ecoute != null)
            {
                ecoute.Close();
                ecoute = null;
            }
            fil?.Join(TimeSpan.FromSeconds(5));
            fil = null;
        }

        // `redirection` : `/lieu` répond 302 vers ce chemin, qui rend `statut` et `corps`.
        // `muet` : la requête est acceptée et jamais répondue (le délai doit dépasser).
        private void Servir(int statut, string corps, string redirection = null, bool muet = false)
        {
            byte[] octets = Encoding.UTF8.GetBytes(corps);
            ecoute = new HttpListener();
            ecoute.Prefixes.Add("http://127.0.0.1:" + port + "/");
            ecoute.Start();
            var auditeur = ecoute;
            fil = new Thread(() =>
            {
                while (true)
                {
                    HttpListenerContext contexte;
                    try { contexte = auditeur.GetContext(); }
                    catch (Exception) { return; }
                    if (muet) continue;
                    if (redirection != null && contexte.Request.Url.AbsolutePath == "/lieu")
                    {
                        contexte.Response.StatusCode = 302;
                        contexte.Response.RedirectLocation = "http://127.0.0.1:" + port + redirection;
                        contexte.Response.ContentLength64 = 0;
                        contexte.Response.OutputStream.Close();
                        continue;
                    }
                    contexte.Response.StatusCode = statut;
                    contexte.Response.ContentType = "application/json; charset=utf-8";
                    contexte.Response.ContentLength64 = octets.Length;
                    contexte.Response.OutputStream.Write(octets, 0, octets.Length);
                    contexte.Response.OutputStream.Close();
                }
            }) { IsBackground = true };
            fil.Start();
        }

        private static string TexteFige(string nom)
        {
            string chemin = Path.Combine(Application.dataPath, "ForgeLocal3D/Pont/Tests/" + nom);
            Assert.IsTrue(File.Exists(chemin), "réponse figée absente : " + chemin);
            string texte = File.ReadAllText(chemin);
            Assert.IsNotEmpty(texte, "réponse figée vide : " + chemin);
            return texte;
        }

        private LectureLieu Lire(long cellId)
        {
            using (var client = new ClientLieu(port, Delai)) return client.Lire(cellId);
        }

        private LectureLieu Absence(long cellId)
        {
            LectureLieu lecture = Lire(cellId);
            Assert.IsFalse(lecture.Presente, "une réponse fautive ne rend jamais de lieu");
            Assert.IsNull(lecture.Lieu);
            Assert.IsNotNull(lecture.Absence);
            StringAssert.Contains("9922", lecture.Absence);
            return lecture;
        }

        private static string Sans(string texte, string retrait)
        {
            string prive = texte.Replace(retrait, "");
            Assert.AreNotEqual(texte, prive, "le retrait de " + retrait + " n'a rien changé");
            return prive;
        }

        [Test]
        public void UnLieuServiEstReluExactement()
        {
            Servir(200, TexteFige("lieu-graine0-tick3.json"));

            LectureLieu lecture = Lire(CellFigee);

            Assert.IsTrue(lecture.Presente);
            Assert.IsNull(lecture.Absence);
            Lieu lieu = lecture.Lieu;
            Assert.IsTrue(lieu.CellId == 9922);
            Assert.IsTrue(lieu.Tick == 3);
            Assert.IsTrue(lieu.Annee == 1400);
            Assert.IsTrue(lieu.JourDeLAnnee == 4);
            Assert.IsTrue(lieu.Population == 109752);
            Assert.IsTrue(lieu.HungerTicks == 0);
            Assert.IsTrue(lieu.FoodDeficitKg == 0.0, "0.0 est une mesure et se garde");
            CollectionAssert.AreEquivalent(new[] { "fer", "nourriture", "objet" }, lieu.Stocks.Keys.ToArray());
            Assert.IsTrue(lieu.Stocks["fer"] == 625.890235);
            Assert.IsTrue(lieu.Stocks["nourriture"] == 1086412.323983);
            Assert.IsTrue(lieu.Stocks["objet"] == 19.415859);
        }

        [Test]
        public void UnServiceDecaleDUnTickNePassePasPourLeBon()
        {
            Servir(200, TexteFige("lieu-graine0-tick4.json"));

            LectureLieu lecture = Lire(CellFigee);

            Assert.IsTrue(lecture.Presente, lecture.Absence);
            Assert.IsTrue(lecture.Lieu.Tick == 4);
            Assert.AreNotEqual(1086412.323983, lecture.Lieu.Stocks["nourriture"]);
        }

        [Test]
        public void UneMarchandiseNouvellePasseEtUneAbsenteNEstPasInventee()
        {
            string texte = TexteFige("lieu-graine0-tick3.json");
            string autre = Sans(texte, "\"fer\":625.890235,").Replace("\"stocks\":{", "\"stocks\":{\"zinc_du_test\":0.0,");
            Servir(200, autre);

            LectureLieu lecture = Lire(CellFigee);

            Assert.IsTrue(lecture.Presente, lecture.Absence);
            Assert.IsFalse(lecture.Lieu.Stocks.ContainsKey("fer"), "une marchandise absente n'est jamais inventée à 0");
            Assert.IsTrue(lecture.Lieu.Stocks["zinc_du_test"] == 0.0, "0.0 reçu est une mesure");
            CollectionAssert.AreEquivalent(new[] { "zinc_du_test", "nourriture", "objet" }, lecture.Lieu.Stocks.Keys.ToArray());
        }

        [Test]
        public void UnPortFermeRendUneAbsenceQuiNommeLePort()
        {
            LectureLieu lecture = Absence(CellFigee);

            StringAssert.Contains("service absent", lecture.Absence);
            StringAssert.Contains(port.ToString(), lecture.Absence);
        }

        [Test]
        public void UnStatut404RendUneAbsenceOuLeClientNommeLaCellule()
        {
            const string corps = "{\"erreur\":\"inconnu\"}";
            StringAssert.DoesNotContain("9922", corps);
            Servir(404, corps);

            LectureLieu lecture = Absence(CellFigee);

            StringAssert.Contains("404", lecture.Absence);
            StringAssert.Contains(corps, lecture.Absence);
        }

        [Test]
        public void UneCleRetireeRendUneAbsenceQuiLaNomme()
        {
            Servir(200, Sans(TexteFige("lieu-graine0-tick3.json"), "\"population\":109752,"));

            StringAssert.Contains("population", Absence(CellFigee).Absence);
        }

        [Test]
        public void UneCleDeDateRetireeRendUneAbsenceQuiNommeSonChemin()
        {
            Servir(200, Sans(TexteFige("lieu-graine0-tick3.json"), "\"annee\":1400,"));

            StringAssert.Contains("date.annee", Absence(CellFigee).Absence);
        }

        [Test]
        public void UnTypeInattenduRendUneAbsenceQuiNommeLaCle()
        {
            string texte = TexteFige("lieu-graine0-tick3.json");
            string altere = texte.Replace("\"fer\":625.890235", "\"fer\":\"beaucoup\"");
            Assert.AreNotEqual(texte, altere);
            Servir(200, altere);

            StringAssert.Contains("stocks.fer", Absence(CellFigee).Absence);
        }

        [Test]
        public void UnNombreNonEntierLaOuUnEntierEstAttenduEstRefuse()
        {
            string texte = TexteFige("lieu-graine0-tick3.json");
            string altere = texte.Replace("\"population\":109752", "\"population\":109752.5");
            Assert.AreNotEqual(texte, altere);
            Servir(200, altere);

            StringAssert.Contains("clé population", Absence(CellFigee).Absence);
        }

        [Test]
        public void UnJsonInvalideRendUneAbsenceQuiNommeLaPosition()
        {
            string texte = TexteFige("lieu-graine0-tick3.json");
            Assert.IsTrue(texte.EndsWith("}"));
            Servir(200, texte.Substring(0, texte.Length - 1));

            LectureLieu lecture = Absence(CellFigee);

            StringAssert.Contains("JSON invalide", lecture.Absence);
            StringAssert.Contains("position", lecture.Absence);
        }

        [Test]
        public void UneAutreCelluleRendUneAbsenceQuiNommeLesDeux()
        {
            Servir(200, TexteFige("lieu-graine0-tick3.json"));

            LectureLieu lecture = Lire(9923);

            Assert.IsFalse(lecture.Presente);
            Assert.IsNull(lecture.Lieu);
            StringAssert.Contains("9923", lecture.Absence);
            StringAssert.Contains("9922", lecture.Absence);
        }

        [Test]
        public void UneRedirectionNEstPasSuivie()
        {
            // Suivie, elle mènerait à un lieu valide : seul le refus de la suivre rend l'absence.
            Servir(200, TexteFige("lieu-graine0-tick3.json"), redirection: "/ailleurs");

            LectureLieu lecture = Absence(CellFigee);

            StringAssert.Contains("302", lecture.Absence);
        }

        [Test]
        public void UnEntierAuDelaDeDeuxPuissance53EstRefuse()
        {
            // 9007199254740993 se lit 9007199254740992 en double : accepté, il deviendrait un autre nombre.
            string texte = TexteFige("lieu-graine0-tick3.json");
            string altere = texte.Replace("\"population\":109752", "\"population\":9007199254740993");
            Assert.AreNotEqual(texte, altere);
            Servir(200, altere);

            StringAssert.Contains("clé population", Absence(CellFigee).Absence);
        }

        [Test]
        public void LePlusGrandEntierSurEstReluExactement()
        {
            // Contre-épreuve : juste sous 2^53, l'entier reste lu tel quel.
            string texte = TexteFige("lieu-graine0-tick3.json");
            string altere = texte.Replace("\"population\":109752", "\"population\":9007199254740991");
            Assert.AreNotEqual(texte, altere);
            Servir(200, altere);

            LectureLieu lecture = Lire(CellFigee);

            Assert.IsTrue(lecture.Presente, lecture.Absence);
            Assert.IsTrue(lecture.Lieu.Population == 9007199254740991L);
        }

        [Test]
        public void UnServiceMuetRendUneAbsenceDeDelaiDepasse()
        {
            Servir(200, TexteFige("lieu-graine0-tick3.json"), muet: true);

            LectureLieu lecture;
            using (var client = new ClientLieu(port, TimeSpan.FromMilliseconds(300)))
                lecture = client.Lire(CellFigee);

            Assert.IsFalse(lecture.Presente);
            Assert.IsNull(lecture.Lieu);
            StringAssert.Contains("9922", lecture.Absence);
            StringAssert.Contains("délai dépassé", lecture.Absence);
        }

        [Test]
        public void UnPortHorsBornesEstRefuse()
        {
            Assert.Throws<ArgumentOutOfRangeException>(() => new ClientLieu(0, Delai));
            Assert.Throws<ArgumentOutOfRangeException>(() => new ClientLieu(65536, Delai));
        }
    }
}
