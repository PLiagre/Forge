using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using NUnit.Framework;

namespace Forge.Pont.Tests
{
    // Lot #292 — un faux service local rend le plan d'une cellule ; le client en relit
    // le tick et les rues telles quelles, ou rend une absence qui nomme sa cause.
    public sealed class ClientPlanTests
    {
        private const long CellFigee = 9922;
        private static readonly TimeSpan Delai = TimeSpan.FromSeconds(5);

        // La première rue est celle que `test_intentions.py` fige pour le service ; la seconde
        // porte des décimales, une coordonnée négative et `en_chantier` à faux.
        private const string PLAN_DEUX_RUES =
            "{\"cell_id\":9922,\"rang\":0,\"tick\":5,\"date\":{\"annee\":1400,\"jour_de_l_annee\":6},"
            + "\"rues\":[{\"identifiant\":0,\"points\":[[0,0],[40,0],[40,25]],\"largeur_m\":4,\"en_chantier\":true},"
            + "{\"identifiant\":3,\"points\":[[-12.5,7.25],[0,0]],\"largeur_m\":2.5,\"en_chantier\":false}],"
            + "\"parcelles\":[],\"batiments\":[]}";

        private int port;
        private HttpListener ecoute;
        private Thread fil;
        private volatile string cheminRecu;
        private volatile string requeteRecue;

        [SetUp]
        public void PortLibre()
        {
            var sonde = new TcpListener(IPAddress.Loopback, 0);
            sonde.Start();
            port = ((IPEndPoint)sonde.LocalEndpoint).Port;
            sonde.Stop();
            cheminRecu = null;
            requeteRecue = null;
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

        // `muet` : la requête est acceptée et jamais répondue (le délai doit dépasser).
        private void Servir(int statut, string corps, bool muet = false)
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
                    cheminRecu = contexte.Request.Url.AbsolutePath;
                    requeteRecue = contexte.Request.Url.Query.TrimStart('?');
                    if (muet) continue;
                    contexte.Response.StatusCode = statut;
                    contexte.Response.ContentType = "application/json; charset=utf-8";
                    contexte.Response.ContentLength64 = octets.Length;
                    contexte.Response.OutputStream.Write(octets, 0, octets.Length);
                    contexte.Response.OutputStream.Close();
                }
            }) { IsBackground = true };
            fil.Start();
        }

        private LecturePlan Lire(long cellId)
        {
            using (var client = new ClientPlan(port, Delai)) return client.Lire(cellId);
        }

        private LecturePlan Absence(long cellId)
        {
            LecturePlan lecture = Lire(cellId);
            Assert.IsFalse(lecture.Presente, "une réponse fautive ne rend jamais de plan");
            Assert.IsNull(lecture.Plan);
            Assert.IsNotNull(lecture.Absence);
            StringAssert.Contains("9922", lecture.Absence);
            return lecture;
        }

        // Un seul remplacement, et la preuve qu'il a changé le texte.
        private static string Remplacer(string ancien, string nouveau)
        {
            string altere = PLAN_DEUX_RUES.Replace(ancien, nouveau);
            Assert.AreNotEqual(PLAN_DEUX_RUES, altere, "le remplacement de " + ancien + " n'a rien changé");
            return altere;
        }

        private static void Point(PointLocal point, double x, double y)
        {
            Assert.IsTrue(point.X == x, "x attendu " + x + ", reçu " + point.X);
            Assert.IsTrue(point.Y == y, "y attendu " + y + ", reçu " + point.Y);
        }

        [Test]
        public void UnPlanServiEstReluExactement()
        {
            Servir(200, PLAN_DEUX_RUES);

            LecturePlan lecture = Lire(CellFigee);

            Assert.IsTrue(lecture.Presente, lecture.Absence);
            Assert.IsNull(lecture.Absence);
            Assert.AreEqual("/plan", cheminRecu);
            Assert.AreEqual("cell=9922", requeteRecue);
            PlanLu plan = lecture.Plan;
            Assert.IsTrue(plan.CellId == 9922);
            Assert.IsTrue(plan.Tick == 5);
            Assert.IsTrue(plan.Rues.Count == 2);

            RueDuPlan premiere = plan.Rues[0];
            Assert.IsTrue(premiere.Identifiant == 0);
            Assert.IsTrue(premiere.Points.Count == 3);
            Point(premiere.Points[0], 0, 0);
            Point(premiere.Points[1], 40, 0);
            Point(premiere.Points[2], 40, 25);
            Assert.IsTrue(premiere.LargeurM == 4.0);
            Assert.IsTrue(premiere.EnChantier);

            RueDuPlan seconde = plan.Rues[1];
            Assert.IsTrue(seconde.Identifiant == 3);
            Assert.IsTrue(seconde.Points.Count == 2);
            Point(seconde.Points[0], -12.5, 7.25);
            Point(seconde.Points[1], 0, 0);
            Assert.IsTrue(seconde.LargeurM == 2.5);
            Assert.IsFalse(seconde.EnChantier);
        }

        [Test]
        public void UnPlanSansRueEstUnPlanPresentQuiDiffereDuPlanDeReference()
        {
            int debut = PLAN_DEUX_RUES.IndexOf("\"rues\":[", StringComparison.Ordinal);
            int fin = PLAN_DEUX_RUES.IndexOf(",\"parcelles\"", StringComparison.Ordinal);
            Assert.IsTrue(debut >= 0 && fin > debut);
            string vide = PLAN_DEUX_RUES.Substring(0, debut) + "\"rues\":[]" + PLAN_DEUX_RUES.Substring(fin);
            Assert.AreNotEqual(PLAN_DEUX_RUES, vide);
            Servir(200, vide);

            LecturePlan lecture = Lire(CellFigee);

            Assert.IsTrue(lecture.Presente, lecture.Absence);
            Assert.IsTrue(lecture.Plan.Tick == 5);
            Assert.IsNotNull(lecture.Plan.Rues);
            Assert.IsTrue(lecture.Plan.Rues.Count == 0, "zéro rue est une mesure");
            Assert.AreNotEqual(2, lecture.Plan.Rues.Count);
        }

        [Test]
        public void UnPortFermeRendUneAbsenceQuiNommeLePort()
        {
            LecturePlan lecture = Absence(CellFigee);

            StringAssert.Contains("service absent", lecture.Absence);
            StringAssert.Contains(port.ToString(), lecture.Absence);
        }

        [Test]
        public void UnStatut404RendUneAbsenceOuLeClientNommeLaCellule()
        {
            const string corps = "{\"erreur\":\"inconnu\"}";
            StringAssert.DoesNotContain("9922", corps);
            Servir(404, corps);

            LecturePlan lecture = Absence(CellFigee);

            StringAssert.Contains("404", lecture.Absence);
            StringAssert.Contains(corps, lecture.Absence);
        }

        [Test]
        public void UnServiceMuetRendUneAbsenceDeDelaiDepasse()
        {
            Servir(200, PLAN_DEUX_RUES, muet: true);

            LecturePlan lecture;
            using (var client = new ClientPlan(port, TimeSpan.FromMilliseconds(200)))
                lecture = client.Lire(CellFigee);

            Assert.IsFalse(lecture.Presente);
            Assert.IsNull(lecture.Plan);
            StringAssert.Contains("9922", lecture.Absence);
            StringAssert.Contains("délai dépassé", lecture.Absence);
        }

        [Test]
        public void UneAutreCelluleRendUneAbsenceQuiNommeLesDeux()
        {
            Servir(200, PLAN_DEUX_RUES);

            LecturePlan lecture = Lire(9923);

            Assert.IsFalse(lecture.Presente);
            Assert.IsNull(lecture.Plan);
            StringAssert.Contains("9923", lecture.Absence);
            StringAssert.Contains("9922", lecture.Absence);
        }

        [Test]
        public void UneCoordonneeNonNumeriqueRefuseLePlan()
        {
            Servir(200, Remplacer("[-12.5,7.25]", "[\"-12.5\",7.25]"));

            LecturePlan lecture = Absence(CellFigee);

            StringAssert.Contains("rues[1].points[0]", lecture.Absence);
            StringAssert.Contains("un nombre attendu", lecture.Absence);
        }

        [Test]
        public void UneLargeurAbsenteRefuseLePlan()
        {
            Servir(200, Remplacer(",\"largeur_m\":2.5", ""));

            StringAssert.Contains("rues[1].largeur_m", Absence(CellFigee).Absence);
        }

        [Test]
        public void UneRueSansEnChantierRefuseLePlan()
        {
            // Jamais `false` par défaut : la seconde rue vaut faux, la deviner ferait passer le plan.
            Servir(200, Remplacer(",\"en_chantier\":false", ""));

            StringAssert.Contains("rues[1].en_chantier", Absence(CellFigee).Absence);
        }

        [Test]
        public void UnEnChantierQuiNEstPasUnBooleenRefuseLePlan()
        {
            Servir(200, Remplacer("\"en_chantier\":false", "\"en_chantier\":0"));

            StringAssert.Contains("rues[1].en_chantier", Absence(CellFigee).Absence);
        }

        [Test]
        public void DesRuesAbsentesRefusentLePlan()
        {
            int debut = PLAN_DEUX_RUES.IndexOf("\"rues\":[", StringComparison.Ordinal);
            int fin = PLAN_DEUX_RUES.IndexOf("\"parcelles\"", StringComparison.Ordinal);
            Assert.IsTrue(debut >= 0 && fin > debut);
            string sansRues = PLAN_DEUX_RUES.Remove(debut, fin - debut);
            Assert.AreNotEqual(PLAN_DEUX_RUES, sansRues);
            StringAssert.DoesNotContain("\"rues\"", sansRues);
            Servir(200, sansRues);

            StringAssert.Contains("clé absente : rues", Absence(CellFigee).Absence);
        }

        [Test]
        public void UnPointATroisCoordonneesRefuseLePlan()
        {
            Servir(200, Remplacer("[-12.5,7.25]", "[-12.5,7.25,0]"));

            StringAssert.Contains("rues[1].points[0]", Absence(CellFigee).Absence);
        }

        [Test]
        public void UnJsonInvalideRendUneAbsenceQuiNommeLaPosition()
        {
            Assert.IsTrue(PLAN_DEUX_RUES.EndsWith("}"));
            Servir(200, PLAN_DEUX_RUES.Substring(0, PLAN_DEUX_RUES.Length - 1));

            LecturePlan lecture = Absence(CellFigee);

            StringAssert.Contains("JSON invalide", lecture.Absence);
            StringAssert.Contains("position", lecture.Absence);
        }

        [Test]
        public void UnPortHorsBornesEstRefuse()
        {
            Assert.Throws<ArgumentOutOfRangeException>(() => new ClientPlan(0, Delai));
            Assert.Throws<ArgumentOutOfRangeException>(() => new ClientPlan(65536, Delai));
        }

        [Test]
        public void UneLectureNeSeFabriqueNiVideNiSansCause()
        {
            Assert.Throws<ArgumentNullException>(() => LecturePlan.De(null));
            Assert.Throws<ArgumentException>(() => LecturePlan.Absent(null));
            Assert.Throws<ArgumentException>(() => LecturePlan.Absent(""));
        }
    }
}
