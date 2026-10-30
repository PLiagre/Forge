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

        // Lot #360 — `PLAN_DEUX_RUES` avec deux parcelles et deux bâtiments, valide pour `sim/plan.py`,
        // aux travaux requis que `sim/chantiers.py` calcule pour ces surfaces. Le bâtiment 2 est sur la
        // parcelle 1 : un client qui lirait l'identifiant à la place de la parcelle rougit.
        private const string PLAN_BOURG =
            "{\"cell_id\":9922,\"rang\":0,\"tick\":5,\"date\":{\"annee\":1400,\"jour_de_l_annee\":6},"
            + "\"rues\":[{\"identifiant\":0,\"points\":[[0,0],[40,0],[40,25]],\"largeur_m\":4,\"en_chantier\":true},"
            + "{\"identifiant\":3,\"points\":[[-12.5,7.25],[0,0]],\"largeur_m\":2.5,\"en_chantier\":false}],"
            + "\"parcelles\":[{\"identifiant\":0,\"contour\":[[5,2],[15,2],[15,22],[5,22]],\"en_chantier\":false,\"foyers\":0,\"travail_requis\":20,\"travail_fourni\":20},"
            + "{\"identifiant\":1,\"contour\":[[-12.5,7.25],[-4.5,7.25],[-4.5,22.25],[-12.5,22.25]],\"en_chantier\":true,\"foyers\":1,\"travail_requis\":12,\"travail_fourni\":5}],"
            + "\"batiments\":[{\"identifiant\":0,\"parcelle\":0,\"nature\":\"maison\",\"emprise\":[[5,2],[15,2],[15,22],[5,22]],\"en_chantier\":false,\"foyers\":0,\"travail_requis\":400,\"travail_fourni\":400},"
            + "{\"identifiant\":2,\"parcelle\":1,\"nature\":\"scierie\",\"emprise\":[[-12.5,7.25],[-4.5,7.25],[-4.5,22.25],[-12.5,22.25]],\"en_chantier\":true,\"foyers\":1,\"travail_requis\":240,\"travail_fourni\":0}]}";

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

        // Lot #360 — les parcelles et les bâtiments du plan.

        // `ancien` paraît exactement une fois dans `source` : la faute porte sur l'élément voulu, et sur lui seul.
        private static string RemplacerUneFois(string source, string ancien, string nouveau)
        {
            int premier = source.IndexOf(ancien, StringComparison.Ordinal);
            Assert.IsTrue(premier >= 0, "absent du plan : " + ancien);
            Assert.AreEqual(premier, source.LastIndexOf(ancien, StringComparison.Ordinal), "présent plus d'une fois : " + ancien);
            string altere = source.Substring(0, premier) + nouveau + source.Substring(premier + ancien.Length);
            Assert.AreNotEqual(source, altere, "le remplacement de " + ancien + " n'a rien changé");
            return altere;
        }

        private static void Points(System.Collections.Generic.IReadOnlyList<PointLocal> points, params double[] xy)
        {
            Assert.IsTrue(points.Count * 2 == xy.Length, xy.Length / 2 + " points attendus, reçu " + points.Count);
            for (int i = 0; i < points.Count; i++) Point(points[i], xy[2 * i], xy[2 * i + 1]);
        }

        // Les valeurs de `PLAN_BOURG`, égales aux littéraux et dans l'ordre de la réponse.
        private static void VerifierBourg(PlanLu plan)
        {
            Assert.IsTrue(plan.CellId == 9922);
            Assert.IsTrue(plan.Tick == 5);

            Assert.IsTrue(plan.Rues.Count == 2);
            RueDuPlan premiere = plan.Rues[0];
            Assert.IsTrue(premiere.Identifiant == 0);
            Points(premiere.Points, 0, 0, 40, 0, 40, 25);
            Assert.IsTrue(premiere.LargeurM == 4.0);
            Assert.IsTrue(premiere.EnChantier);
            RueDuPlan seconde = plan.Rues[1];
            Assert.IsTrue(seconde.Identifiant == 3);
            Points(seconde.Points, -12.5, 7.25, 0, 0);
            Assert.IsTrue(seconde.LargeurM == 2.5);
            Assert.IsFalse(seconde.EnChantier);

            Assert.IsTrue(plan.Parcelles.Count == 2, "2 parcelles attendues, reçu " + plan.Parcelles.Count);
            ParcelleDuPlan p0 = plan.Parcelles[0];
            Assert.IsTrue(p0.Identifiant == 0);
            Points(p0.Contour, 5, 2, 15, 2, 15, 22, 5, 22);
            Assert.IsFalse(p0.EnChantier);
            Assert.IsTrue(p0.TravailRequis == 20);
            Assert.IsTrue(p0.TravailFourni == 20);
            ParcelleDuPlan p1 = plan.Parcelles[1];
            Assert.IsTrue(p1.Identifiant == 1);
            Points(p1.Contour, -12.5, 7.25, -4.5, 7.25, -4.5, 22.25, -12.5, 22.25);
            Assert.IsTrue(p1.EnChantier);
            Assert.IsTrue(p1.TravailRequis == 12);
            Assert.IsTrue(p1.TravailFourni == 5);

            Assert.IsTrue(plan.Batiments.Count == 2, "2 bâtiments attendus, reçu " + plan.Batiments.Count);
            BatimentDuPlan b0 = plan.Batiments[0];
            Assert.IsTrue(b0.Identifiant == 0);
            Assert.IsTrue(b0.Parcelle == 0);
            Assert.AreEqual("maison", b0.Nature);
            Points(b0.Emprise, 5, 2, 15, 2, 15, 22, 5, 22);
            Assert.IsFalse(b0.EnChantier);
            Assert.IsTrue(b0.TravailRequis == 400);
            Assert.IsTrue(b0.TravailFourni == 400);
            BatimentDuPlan b2 = plan.Batiments[1];
            Assert.IsTrue(b2.Identifiant == 2);
            Assert.IsTrue(b2.Parcelle == 1);
            Assert.AreEqual("scierie", b2.Nature);
            Points(b2.Emprise, -12.5, 7.25, -4.5, 7.25, -4.5, 22.25, -12.5, 22.25);
            Assert.IsTrue(b2.EnChantier);
            Assert.IsTrue(b2.TravailRequis == 240);
            Assert.IsTrue(b2.TravailFourni == 0);
        }

        // Le texte de `PLAN_BOURG` de `debut` (compris) à `fin` (exclu), remplacé par `nouveau`.
        private static string Couper(string debut, string fin, string nouveau)
        {
            int i = PLAN_BOURG.IndexOf(debut, StringComparison.Ordinal);
            int j = PLAN_BOURG.LastIndexOf(fin, StringComparison.Ordinal);
            Assert.IsTrue(i >= 0 && j > i, "coupe introuvable : " + debut + " … " + fin);
            string coupe = PLAN_BOURG.Substring(0, i) + nouveau + PLAN_BOURG.Substring(j);
            Assert.AreNotEqual(PLAN_BOURG, coupe, "la coupe n'a rien changé");
            return coupe;
        }

        [Test]
        public void LesParcellesEtLesBatimentsServisSontRelusExactement()
        {
            Servir(200, PLAN_BOURG);

            LecturePlan lecture = Lire(CellFigee);

            Assert.IsTrue(lecture.Presente, lecture.Absence);
            Assert.IsNull(lecture.Absence);
            VerifierBourg(lecture.Plan);
        }

        [Test]
        public void UnBatimentSansFoyersEstReluQuandMeme()
        {
            Servir(200, RemplacerUneFois(PLAN_BOURG, "\"foyers\":0,\"travail_requis\":400,", "\"travail_requis\":400,"));

            LecturePlan lecture = Lire(CellFigee);

            Assert.IsTrue(lecture.Presente, lecture.Absence);
            VerifierBourg(lecture.Plan);
        }

        [Test]
        public void UnPlanSansParcelleNiBatimentEstUnPlanPresent()
        {
            Servir(200, PLAN_DEUX_RUES);

            LecturePlan lecture = Lire(CellFigee);

            Assert.IsTrue(lecture.Presente, lecture.Absence);
            Assert.IsTrue(lecture.Plan.Rues.Count == 2);
            Assert.IsNotNull(lecture.Plan.Parcelles);
            Assert.IsNotNull(lecture.Plan.Batiments);
            Assert.IsTrue(lecture.Plan.Parcelles.Count == 0, "zéro parcelle est une mesure");
            Assert.IsTrue(lecture.Plan.Batiments.Count == 0, "zéro bâtiment est une mesure");
        }

        [Test]
        public void DesParcellesSansBatimentSontUnPlanPresent()
        {
            Servir(200, Couper(",\"batiments\":[", "}", ",\"batiments\":[]"));

            LecturePlan lecture = Lire(CellFigee);

            Assert.IsTrue(lecture.Presente, lecture.Absence);
            Assert.IsTrue(lecture.Plan.Parcelles.Count == 2);
            Assert.IsNotNull(lecture.Plan.Batiments);
            Assert.IsTrue(lecture.Plan.Batiments.Count == 0, "zéro bâtiment est une mesure");
            Assert.AreNotEqual(2, lecture.Plan.Batiments.Count);
        }

        // La faute porte toujours sur le second élément de sa liste. `precision` resserre ce que
        // l'absence doit dire : une parcelle sans `en_chantier` est refusée pour la clé absente,
        // pas pour un faux deviné qui contredirait ensuite son travail.
        [TestCase("{\"identifiant\":1,", "{\"identifiant\":-1,", "parcelles[1].identifiant", "un entier ≥ 0")]
        [TestCase("\"contour\":[[-12.5,7.25],[-4.5,7.25],[-4.5,22.25],[-12.5,22.25]]", "\"contour\":[[-12.5,7.25],[-4.5,7.25]]", "parcelles[1].contour", "au moins 3 points")]
        [TestCase("\"contour\":[[-12.5,7.25]", "\"contour\":[[\"-12.5\",7.25]", "parcelles[1].contour[0]", "un nombre attendu")]
        [TestCase("\"contour\":[[-12.5,7.25],", "\"contour\":[[-12.5,7.25,0],", "parcelles[1].contour[0]", "exactement 2 nombres")]
        [TestCase("\"en_chantier\":true,\"foyers\":1,\"travail_requis\":12", "\"foyers\":1,\"travail_requis\":12", "parcelles[1].en_chantier", "clé absente")]
        [TestCase("\"travail_requis\":12,\"travail_fourni\":5}", "\"travail_requis\":12}", "parcelles[1].travail_fourni", "clé absente")]
        [TestCase("\"travail_requis\":12,", "\"travail_requis\":\"12\",", "parcelles[1].travail_requis", "un nombre attendu")]
        [TestCase("\"travail_fourni\":5}", "\"travail_fourni\":13}", "parcelles[1].travail_fourni", "dépasse")]
        [TestCase("\"travail_fourni\":5}", "\"travail_fourni\":12}", "parcelles[1].en_chantier", "contredit")]
        [TestCase("\"parcelle\":1,", "\"parcelle\":7,", "batiments[1].parcelle", "aucune parcelle 7")]
        [TestCase("\"parcelle\":1,", "\"parcelle\":\"1\",", "batiments[1].parcelle", "un nombre attendu")]
        [TestCase("\"nature\":\"scierie\",", "", "batiments[1].nature", "clé absente")]
        [TestCase("\"nature\":\"scierie\"", "\"nature\":\" \"", "batiments[1].nature", "un texte non vide")]
        [TestCase("\"nature\":\"scierie\"", "\"nature\":3", "batiments[1].nature", "un texte non vide")]
        [TestCase("\"emprise\":[[-12.5,7.25]", "\"emprise\":[[-12.5,null]", "batiments[1].emprise[0]", "un nombre attendu")]
        [TestCase("\"travail_requis\":240,", "\"travail_requis\":240.5,", "batiments[1].travail_requis", "un entier")]
        [TestCase("\"travail_fourni\":0}", "\"travail_fourni\":-1}", "batiments[1].travail_fourni", "un entier ≥ 0")]
        [TestCase("\"en_chantier\":true,\"foyers\":1,\"travail_requis\":240", "\"en_chantier\":1,\"foyers\":1,\"travail_requis\":240", "batiments[1].en_chantier", "un booléen attendu")]
        [TestCase("\"batiments\":[{", "\"batiments\":[7,{", "batiments[0]", "un objet attendu")]
        public void UneParcelleOuUnBatimentMalFormeRefuseLePlan(string ancien, string nouveau, string chemin, string precision)
        {
            Servir(200, RemplacerUneFois(PLAN_BOURG, ancien, nouveau));

            LecturePlan lecture = Absence(CellFigee);

            StringAssert.Contains(chemin, lecture.Absence);
            StringAssert.Contains(precision, lecture.Absence);
        }

        [Test]
        public void DesParcellesAbsentesRefusentLePlan()
        {
            string sansParcelles = Couper("\"parcelles\":[", "\"batiments\":[", "");
            StringAssert.DoesNotContain("\"parcelles\"", sansParcelles);
            Servir(200, sansParcelles);

            StringAssert.Contains("clé absente : parcelles", Absence(CellFigee).Absence);
        }

        [Test]
        public void DesBatimentsAbsentsRefusentLePlan()
        {
            string sansBatiments = Couper(",\"batiments\":[", "}", "");
            StringAssert.DoesNotContain("\"batiments\"", sansBatiments);
            Servir(200, sansBatiments);

            StringAssert.Contains("clé absente : batiments", Absence(CellFigee).Absence);
        }

        [Test]
        public void DesBatimentsSurDesParcellesVideesRefusentLePlan()
        {
            Servir(200, Couper("\"parcelles\":[", "\"batiments\":[", "\"parcelles\":[],"));

            StringAssert.Contains("batiments[0].parcelle", Absence(CellFigee).Absence);
        }

        [Test]
        public void UneParcelleOuUnBatimentNeSeFabriqueNiSansListeNiSansNature()
        {
            var points = new[] { new PointLocal(0, 0), new PointLocal(1, 0), new PointLocal(1, 1) };
            Assert.Throws<ArgumentNullException>(() => new ParcelleDuPlan(0, null, false, 0, 0));
            Assert.Throws<ArgumentNullException>(() => new BatimentDuPlan(0, 0, null, points, false, 0, 0));
            Assert.Throws<ArgumentNullException>(() => new BatimentDuPlan(0, 0, "maison", null, false, 0, 0));
            var rues = new RueDuPlan[0];
            var parcelles = new ParcelleDuPlan[0];
            var batiments = new BatimentDuPlan[0];
            Assert.Throws<ArgumentNullException>(() => new PlanLu(1, 0, null, parcelles, batiments));
            Assert.Throws<ArgumentNullException>(() => new PlanLu(1, 0, rues, null, batiments));
            Assert.Throws<ArgumentNullException>(() => new PlanLu(1, 0, rues, parcelles, null));
        }

        // Lot #735 — la ville de 1400 servie sous `base`, en tête et dans l'ordre de clés du service.
        private static readonly string PLAN_BASE = "{\"base\":{\"cell_id\":9922,\"maisons\":[{\"emprise\":[[10,10],[15,10],[15,18],[10,18]],\"foyers\":1},{\"emprise\":[[-30,5],[-20,5],[-20,25],[-30,25]],\"foyers\":12}],\"place\":[[-5,-5],[5,-5],[5,5],[-5,5]],\"rues\":[{\"largeur_m\":6,\"points\":[[5,0.5],[60,2.25]],\"sorte\":\"principale\",\"vers_cell_id\":9923},{\"largeur_m\":3.5,\"points\":[[0,5],[-2.5,40]],\"sorte\":\"ruelle\"}]}," + PLAN_DEUX_RUES.Substring(1);

        [Test]
        public void UneBaseServieEstRelueExactement()
        {
            Servir(200, PLAN_BASE);
            LecturePlan lecture = Lire(CellFigee);
            Assert.IsTrue(lecture.Presente, lecture.Absence);
            BaseDuPlan b = lecture.Plan.Base;
            Points(b.Place, -5, -5, 5, -5, 5, 5, -5, 5);
            Assert.IsTrue(b.Rues.Count == 2 && b.Maisons.Count == 2, b.Rues.Count + " rues, " + b.Maisons.Count + " maisons");
            Points(b.Rues[0].Points, 5, 0.5, 60, 2.25);
            Assert.IsTrue(b.Rues[0].LargeurM == 6.0 && b.Rues[0].Sorte == "principale");
            Points(b.Rues[1].Points, 0, 5, -2.5, 40);
            Assert.IsTrue(b.Rues[1].LargeurM == 3.5 && b.Rues[1].Sorte == "ruelle");
            Points(b.Maisons[0].Emprise, 10, 10, 15, 10, 15, 18, 10, 18);
            Points(b.Maisons[1].Emprise, -30, 5, -20, 5, -20, 25, -30, 25);
            Assert.IsTrue(b.Maisons[0].Foyers == 1 && b.Maisons[1].Foyers == 12, "foyers 1 puis 12 attendus");
            PlanLu p = lecture.Plan;
            Assert.IsTrue(p.CellId == 9922 && p.Tick == 5 && p.Rues.Count == 2 && p.Parcelles.Count == 0 && p.Batiments.Count == 0);
            Points(p.Rues[0].Points, 0, 0, 40, 0, 40, 25);
            Points(p.Rues[1].Points, -12.5, 7.25, 0, 0);
            Assert.IsTrue(p.Rues[0].Identifiant == 0 && p.Rues[0].LargeurM == 4.0 && p.Rues[0].EnChantier && p.Rues[1].Identifiant == 3 && p.Rues[1].LargeurM == 2.5 && !p.Rues[1].EnChantier);
        }

        [Test]
        public void LaBaseDeBiskraServieEstRelue()
        {
            Servir(200, System.IO.File.ReadAllText(UnityEngine.Application.dataPath + "/ForgeLocal3D/Pont/Tests/plan-biskra-graine0-tick0.json"));
            LecturePlan lecture = Lire(10103);
            Assert.IsTrue(lecture.Presente, lecture.Absence);
            PlanLu p = lecture.Plan;
            Assert.IsTrue(p.Tick == 0 && p.Rues.Count == 0 && p.Parcelles.Count == 0 && p.Batiments.Count == 0);
            BaseDuPlan b = p.Base;
            Points(b.Place, -50, -50, 50, -50, 50, 50, -50, 50);
            Assert.IsTrue(b.Rues.Count == 7 && b.Maisons.Count == 33, b.Rues.Count + " rues, " + b.Maisons.Count + " maisons");
            foreach (RueDeBase rue in b.Rues) Assert.IsTrue(rue.Sorte == "principale" && rue.LargeurM == 6.0, rue.Sorte + " de " + rue.LargeurM + " m");
            Points(b.Rues[0].Points, 50.0, 11.428924, 64.622855, 14.771394);
            Points(b.Rues[6].Points, 50.0, -26.353112, 63.269689, -33.347063);
            Point(b.Maisons[0].Emprise[0], -55.392334, -10.181982);
            Point(b.Maisons[32].Emprise[2], -63.427086, -48.928937);
            Assert.IsTrue(b.Maisons.Sum(m => m.Foyers) == 33, b.Maisons.Sum(m => m.Foyers) + " foyers");
            Assert.IsTrue(b.Maisons.Max(m => m.Emprise.Max(q => Math.Max(Math.Abs(q.X), Math.Abs(q.Y)))) == 69.186409, "plus grande coordonnée");
        }

        // Lot #736 — les 33 maisons de Biskra regardent l'arête de façade mesurée sur le générateur.
        [Test]
        public void LaBaseDeBiskraSePoseFaceASesRues()
        {
            Servir(200, System.IO.File.ReadAllText(UnityEngine.Application.dataPath + "/ForgeLocal3D/Pont/Tests/plan-biskra-graine0-tick0.json"));
            LecturePlan lecture = Lire(10103);
            Assert.IsTrue(lecture.Presente, lecture.Absence);
            PoseDesMaisons pose = MaisonsDeLaBase.Poser(lecture.Plan.Base);
            Assert.IsTrue(pose.Presente && pose.Cases.Count == 33, pose.Absence);
            const string aretes = "133113313111313313113313131331313";
            for (int k = 0; k < 33; k++)
            {
                CaseDeMaison c = pose.Cases[k];
                var e = lecture.Plan.Base.Maisons[k].Emprise;
                int a = aretes[k] - '0';
                var t = new[] { e[a], e[(a + 1) % 4], e[(a + 2) % 4], e[(a + 3) % 4] };
                Assert.IsTrue(c.Maison == k && c.Indice == 0);
                Assert.AreEqual(5, c.LargeurM, 1e-5);
                Assert.AreEqual(8, c.ProfondeurM, 1e-5);
                Assert.AreEqual((e[0].X + e[1].X + e[2].X + e[3].X) / 4, c.CentreX, 1e-5);
                Assert.AreEqual((e[0].Y + e[1].Y + e[2].Y + e[3].Y) / 4, c.CentreY, 1e-5);
                Assert.AreEqual(LectureDuBatiment.Poser(new BatimentDuPlan(k, 0, "maison", t, false, 0, 0)).LacetDegres, c.LacetDegres, 1e-5);
            }
            CaseDeMaison c0 = pose.Cases[0], c32 = pose.Cases[32];
            Assert.AreEqual(-52.762008, c0.CentreX, 1e-5); Assert.AreEqual(-6.266451, c0.CentreY, 1e-5); Assert.AreEqual(181.886541, c0.LacetDegres, 1e-5);
            Assert.AreEqual(-62.2654, c32.CentreX, 1e-5); Assert.AreEqual(-53.500643, c32.CentreY, 1e-5); Assert.AreEqual(313.737296, c32.LacetDegres, 1e-5);
        }

        [Test]
        public void UnPlanSansBaseEstLuEtDeclareLaBaseAbsente()
        {
            Servir(200, PLAN_BOURG);
            LecturePlan lecture = Lire(CellFigee);
            Assert.IsTrue(lecture.Presente, lecture.Absence);
            Assert.IsNull(lecture.Plan.Base, "une base non servie se déclare absente, jamais inventée");
            VerifierBourg(lecture.Plan);
        }

        [TestCase("\"base\":{\"cell_id\":9922,", "\"base\":7,\"x\":{\"cell_id\":9922,", "base", "un objet attendu")]
        [TestCase("\"cell_id\":9922,\"maisons\"", "\"cell_id\":9923,\"maisons\"", "base.cell_id", "9923")]
        [TestCase("\"place\":[", "\"lieu\":[", "clé absente : base.place", "base.place")]
        [TestCase("\"place\":[[-5,-5],[5,-5],[5,5],[-5,5]]", "\"place\":[[-5,-5],[5,-5]]", "base.place", "au moins 3 points")]
        [TestCase("\"rues\":[{\"largeur_m\":6", "\"voies\":[{\"largeur_m\":6", "clé absente : base.rues", "base.rues")]
        [TestCase("\"points\":[[0,5],[-2.5,40]]", "\"points\":[[0,5]]", "base.rues[1].points", "au moins 2 points")]
        [TestCase("\"largeur_m\":3.5", "\"largeur_m\":0", "base.rues[1].largeur_m", "> 0")]
        [TestCase(",\"sorte\":\"ruelle\"", "", "base.rues[1].sorte", "clé absente")]
        [TestCase("\"sorte\":\"ruelle\"", "\"sorte\":\"\"", "base.rues[1].sorte", "un texte non vide")]
        [TestCase("\"sorte\":\"ruelle\"", "\"sorte\":3", "base.rues[1].sorte", "un texte non vide")]
        [TestCase("\"maisons\":[{", "\"maisons\":[7,{", "base.maisons[0]", "un objet attendu")]
        [TestCase("\"maisons\":[{", "\"logis\":[{", "clé absente : base.maisons", "base.maisons")]
        [TestCase("[[-30,5],", "[[-30,5,0],", "base.maisons[1].emprise[0]", "exactement 2 nombres")]
        [TestCase("\"foyers\":12", "\"foyers\":0", "base.maisons[1].foyers", "au moins 1 foyer")]
        [TestCase("\"foyers\":12", "\"foyers\":1.5", "base.maisons[1].foyers", "un entier")]
        [TestCase(",\"foyers\":12", "", "base.maisons[1].foyers", "clé absente")]
        public void UneBaseMalFormeeRefuseLePlan(string ancien, string nouveau, string chemin, string precision)
        {
            Servir(200, RemplacerUneFois(PLAN_BASE, ancien, nouveau));
            LecturePlan lecture = Absence(CellFigee);
            StringAssert.Contains(chemin, lecture.Absence);
            StringAssert.Contains(precision, lecture.Absence);
        }

        [Test]
        public void UneBaseNeSeFabriquePasSansListe()
        {
            var points = new[] { new PointLocal(0, 0), new PointLocal(1, 0), new PointLocal(1, 1) };
            Assert.IsNull(new PlanLu(1, 0, new RueDuPlan[0], new ParcelleDuPlan[0], new BatimentDuPlan[0]).Base);
            var b = new BaseDuPlan(points, new RueDeBase[0], new MaisonDeBase[0]);
            Assert.AreSame(b, new PlanLu(1, 0, new RueDuPlan[0], new ParcelleDuPlan[0], new BatimentDuPlan[0], b).Base);
            Assert.Throws<ArgumentNullException>(() => new RueDeBase(null, 6, "ruelle"));
            Assert.Throws<ArgumentNullException>(() => new RueDeBase(points, 6, null));
            Assert.Throws<ArgumentNullException>(() => new MaisonDeBase(null, 1));
            Assert.Throws<ArgumentNullException>(() => new BaseDuPlan(null, new RueDeBase[0], new MaisonDeBase[0]));
            Assert.Throws<ArgumentNullException>(() => new BaseDuPlan(points, null, new MaisonDeBase[0]));
            Assert.Throws<ArgumentNullException>(() => new BaseDuPlan(points, new RueDeBase[0], null));
        }

        // Lot #783 — PLAN_BOURG sous la base de PLAN_BASE : base.rues[0] suit les points de rues[1] mais vise 9923, rues[1] porte
        // vers 10104. Le relevé donne l'identifiant 0 à une rue qui travaille, une parcelle achevée ce jour et un bâtiment arrêté.
        private static readonly string[][] PARCELLE_DU_JOUR = { new[] { "nature", "\"parcelle\"" }, new[] { "identifiant", "0" }, new[] { "bras", "1" }, new[] { "grain_paye_kg", "0.5" }, new[] { "motif_arret", "null" } };
        private static string Entree(string cle, string valeur) => "{" + string.Join(",", PARCELLE_DU_JOUR.Where(p => p[0] != cle || valeur != null).Select(p => "\"" + p[0] + "\":" + (p[0] == cle ? valeur : p[1]))) + "}";
        private static readonly string PLAN_JOUR = PLAN_BASE.Substring(0, PLAN_BASE.Length - PLAN_DEUX_RUES.Length + 1).Replace("[[5,0.5],[60,2.25]]", "[[-12.5,7.25],[0,0]]")
            + PLAN_BOURG.Substring(1, PLAN_BOURG.Length - 2).Replace("\"en_chantier\":false}],\"parcelles\"", "\"en_chantier\":false,\"porte_cell_id\":10104}],\"parcelles\"")
            + ",\"chantiers_du_jour\":[{\"nature\":\"rue\",\"identifiant\":0,\"bras\":3,\"grain_paye_kg\":2.718281828459045,\"motif_arret\":null},"
            + Entree("", "") + ",{\"nature\":\"batiment\",\"identifiant\":0,\"bras\":0,\"grain_paye_kg\":0,\"motif_arret\":\"sans_grain\"}]}";

        // Le témoin sans relevé (`tableau` null) ou avec un autre relevé à sa place.
        private static string Releve(string source, string tableau)
        { int i = source.IndexOf(",\"chantiers_du_jour\":", StringComparison.Ordinal); Assert.IsTrue(i > 0 && source.EndsWith("]}")); return source.Substring(0, i) + (tableau == null ? "" : ",\"chantiers_du_jour\":" + tableau) + "}"; }

        [Test]
        public void LesDebouchesEtLeReleveDuJourSontRelusExactement()
        {
            Assert.IsTrue(PLAN_JOUR.Contains("[[-12.5,7.25],[0,0]],\"sorte\":\"principale\",\"vers_cell_id\":9923}") && PLAN_JOUR.Contains("\"porte_cell_id\":10104}") && !PLAN_JOUR.Contains("[60,2.25]"));
            Servir(200, PLAN_JOUR);
            LecturePlan lecture = Lire(CellFigee);
            Assert.IsTrue(lecture.Presente, lecture.Absence);
            PlanLu p = lecture.Plan; BaseDuPlan b = p.Base; VerifierBourg(p);
            Points(b.Rues[0].Points, -12.5, 7.25, 0, 0); Points(b.Rues[1].Points, 0, 5, -2.5, 40);
            Assert.IsTrue(b.Rues[0].VersCellId == 9923 && b.Rues[1].VersCellId == null && p.Rues[1].PorteCellId == 10104 && p.Rues[0].PorteCellId == null, "les mêmes points servent deux destinations");
            Assert.IsTrue(b.Rues[0].Sorte == "principale" && b.Rues[1].Sorte == "ruelle" && b.Rues[1].LargeurM == 3.5 && b.Maisons.Count == 2 && b.Maisons[1].Foyers == 12);
            IReadOnlyList<ChantierDuJour> c = p.ChantiersDuJour;
            Assert.IsTrue(p.AbsenceDesChantiersDuJour == null && c.Count == 3);
            string[] natures = { "rue", "parcelle", "batiment" }; long[] bras = { 3, 1, 0 }; double[] kg = { 2.718281828459045, 0.5, 0 };
            for (int i = 0; i < 3; i++)
                Assert.IsTrue(c[i].Nature == natures[i] && c[i].Identifiant == 0 && c[i].Bras == bras[i] && c[i].GrainPayeKg == kg[i] && (c[i].MotifArret == null) == (i < 2), "chantier " + i);
            Assert.IsTrue(c[2].MotifArret == "sans_grain" && !p.Parcelles[0].EnChantier, "la parcelle 0 achevée garde son observation");
            Assert.Throws<NotSupportedException>(() => ((IList<ChantierDuJour>)c).Add(null));
        }

        private static IEnumerable<TestCaseData> Debouches()
        {
            foreach (string ancien in new[] { "\"vers_cell_id\":9923", "\"porte_cell_id\":10104" })
                foreach (string valeur in new[] { "retrait", "null", "0", "9007199254740991", "-1", "1.5", "true", "\"9923\"", "9007199254740992" })
                    yield return new TestCaseData(ancien, valeur);
        }

        [TestCaseSource(nameof(Debouches))]
        public void UnDeboucheEstFacultatifEtExact(string ancien, string valeur)
        {
            string cle = ancien.Substring(1, ancien.IndexOf('"', 1) - 1), chemin = (cle == "vers_cell_id" ? "base.rues[0]." : "rues[1].") + cle;
            string corps = valeur == "retrait" ? RemplacerUneFois(PLAN_JOUR, "," + ancien, "") : RemplacerUneFois(PLAN_JOUR, ancien, "\"" + cle + "\":" + valeur);
            Servir(200, corps);
            if (!new[] { "retrait", "null", "0", "9007199254740991" }.Contains(valeur)) { StringAssert.Contains("clé " + chemin + " :", Absence(CellFigee).Absence); return; }
            LecturePlan lecture = Lire(CellFigee);
            Assert.IsTrue(lecture.Presente, lecture.Absence);
            long? attendu = valeur == "retrait" || valeur == "null" ? (long?)null : long.Parse(valeur);
            PlanLu p = lecture.Plan; VerifierBourg(p);
            Assert.IsTrue(cle == "vers_cell_id" ? p.Base.Rues[0].VersCellId == attendu && p.Rues[1].PorteCellId == 10104 : p.Rues[1].PorteCellId == attendu && p.Base.Rues[0].VersCellId == 9923);
            Assert.IsTrue(p.Base.Rues.Count == 2 && p.ChantiersDuJour.Count == 3);
        }

        private static IEnumerable<TestCaseData> RelevesFautifs()
        {
            foreach (string tableau in new[] { "null", "{}", "7" }) yield return new TestCaseData("", tableau);
            string[] entiers = { "-1", "1.5", "true", "9007199254740992" };
            var valeurs = new Dictionary<string, string[]> { ["nature"] = new[] { "\"chose\"", "\" \"", "\"\"" }, ["identifiant"] = entiers, ["bras"] = entiers,
                ["grain_paye_kg"] = new[] { "-0.5", "\"0.5\"", "1e309" }, ["motif_arret"] = new[] { "\" \"", "3" } };
            foreach (var paire in valeurs)
                foreach (string valeur in new string[] { null }.Concat(paire.Value)) yield return new TestCaseData(paire.Key, valeur);
        }

        // `cle` vide : le relevé entier (null, objet) ou sa seconde entrée (7) est remplacé ; `valeur` null retire la clé.
        [TestCaseSource(nameof(RelevesFautifs))]
        public void UnReleveFautifRefuseToutLePlan(string cle, string valeur)
        {
            string corps = cle == "" ? (valeur == "7" ? RemplacerUneFois(PLAN_JOUR, Entree("", ""), "7") : Releve(PLAN_JOUR, valeur)) : RemplacerUneFois(PLAN_JOUR, Entree("", ""), Entree(cle, valeur));
            string chemin = cle == "" ? (valeur == "7" ? "clé chantiers_du_jour[1] :" : "clé chantiers_du_jour :") : valeur == null ? "clé absente : chantiers_du_jour[1]." + cle : "clé chantiers_du_jour[1]." + cle + " :";
            if (valeur == "1e309") { Assert.Throws<ErreurJson>(() => LecteurJson.LireObjet(corps)); chemin = "JSON invalide"; }
            else
            {
                object releve = LecteurJson.LireObjet(corps)["chantiers_du_jour"], touche = cle == "" && valeur != "7" ? releve : ((List<object>)releve)[1];
                if (cle != "")
                {
                    var entree = (Dictionary<string, object>)touche;
                    Assert.IsTrue(entree.Count == (valeur == null ? 4 : 5) && entree.ContainsKey(cle) == (valeur != null), "la mutation touche " + cle);
                    touche = valeur == null ? null : entree[cle];
                }
                Assert.AreEqual(valeur == null ? null : LecteurJson.LireObjet("{\"v\":" + valeur + "}")["v"], touche);
            }
            Servir(200, corps);
            StringAssert.Contains(chemin, Absence(CellFigee).Absence);
        }

        [Test]
        public void UnNouveauReleveRemplaceLePrecedentEtSonAbsenceSeDeclare()
        {
            string change = RemplacerUneFois(RemplacerUneFois(RemplacerUneFois(PLAN_JOUR, "\"bras\":3,\"grain_paye_kg\":2.718281828459045", "\"bras\":4,\"grain_paye_kg\":0.25"),
                "\"porte_cell_id\":10104", "\"porte_cell_id\":0"), "\"vers_cell_id\":9923", "\"vers_cell_id\":7");
            string absent = RemplacerUneFois(RemplacerUneFois(Releve(PLAN_JOUR, null), ",\"porte_cell_id\":10104", ""), ",\"vers_cell_id\":9923", "");
            var lus = new List<PlanLu>(); LecturePlan erreur;
            using (var client = new ClientPlan(port, Delai))
            {
                foreach (string corps in new[] { PLAN_JOUR, change, Releve(PLAN_JOUR, "[]"), absent })
                {
                    Fermer(); Servir(200, corps);
                    LecturePlan lecture = client.Lire(CellFigee);
                    Assert.IsTrue(lecture.Presente, lecture.Absence);
                    VerifierBourg(lecture.Plan); lus.Add(lecture.Plan);
                }
                Fermer(); Servir(500, "{}"); erreur = client.Lire(CellFigee);
            }
            Assert.IsTrue(!erreur.Presente && erreur.Plan == null && erreur.Absence.Contains("500"));
            Assert.IsTrue(lus[0].ChantiersDuJour[0].Bras == 3 && lus[0].Rues[1].PorteCellId == 10104, "la première lecture garde ses valeurs");
            Assert.IsTrue(lus[1].ChantiersDuJour[0].Bras == 4 && lus[1].ChantiersDuJour[0].GrainPayeKg == 0.25 && lus[1].Rues[1].PorteCellId == 0 && lus[1].Base.Rues[0].VersCellId == 7);
            Assert.IsTrue(lus[2].ChantiersDuJour.Count == 0 && lus[2].AbsenceDesChantiersDuJour == null, "un relevé vide est une mesure");
            Assert.IsTrue(lus[3].ChantiersDuJour == null && lus[3].AbsenceDesChantiersDuJour.Contains("chantiers_du_jour") && lus[3].Rues[1].PorteCellId == null && lus[3].Base.Rues[0].VersCellId == null);
            var points = new[] { new PointLocal(0, 0), new PointLocal(1, 0) }; var ancien = new PlanLu(1, 0, new RueDuPlan[0], new ParcelleDuPlan[0], new BatimentDuPlan[0]);
            Assert.IsTrue(ancien.ChantiersDuJour == null && ancien.AbsenceDesChantiersDuJour != null && new RueDuPlan(0, points, 1, false).PorteCellId == null && new RueDeBase(points, 1, "ruelle").VersCellId == null);
        }

        // Lot #904 — la Biskra murée en chantier que le service rend au tick 3 (`test_epreuve_enceinte.py`).
        private static string Fixture(string nom) => System.IO.File.ReadAllText(UnityEngine.Application.dataPath + "/ForgeLocal3D/Pont/Tests/" + nom);
        private const string MUREE = "plan-biskra-enceinte-graine0-tick3.json", PORTE = "\"identifiant\":0,\"largeur_m\":4,\"point\":[-80.0,2.2],\"rue\":\"plan\"";

        private LecturePlan LireBiskra(string corps) { Fermer(); Servir(200, corps); return Lire(10103); }
        private string RefusDeBiskra(string corps)
        { LecturePlan l = LireBiskra(corps); Assert.IsTrue(!l.Presente && l.Plan == null && l.Absence.Contains("10103"), "une faute ne rend jamais de plan partiel"); return l.Absence; }

        [Test]
        public void LaBiskraMureeEnChantierEstRelue()
        {
            string texte = Fixture(MUREE); LecturePlan lecture = LireBiskra(texte);
            Assert.IsTrue(lecture.Presente, lecture.Absence);
            PlanLu p = lecture.Plan; EnceinteDuPlan e = p.Enceinte; IReadOnlyList<ChantierDuJour> c = p.ChantiersDuJour;
            Assert.IsTrue(p.Tick == 3 && p.Parcelles.Count == 0 && p.Batiments.Count == 0 && p.Base.Maisons.Count == 33 && p.Base.Rues.Count == 7 && p.Rues.Count == 1);
            var servie = (Dictionary<string, object>)((List<object>)LecteurJson.LireObjet(texte)["rues"])[0];
            Points(p.Rues[0].Points, -66, 2.2, -120, 2.2);
            Assert.IsTrue(p.Rues[0].Identifiant == 0 && p.Rues[0].LargeurM == 4 && p.Rues[0].EnChantier && (double)servie["travail_fourni"] == 5 && (double)servie["travail_requis"] == 108);
            Points(e.Contour, -80, -80, 80, -80, 80, 80, -80, 80);
            Assert.IsTrue(e.EnChantier && e.Foyers == 2 && e.TravailFourni == 1 && e.TravailRequis == 19200 && p.Portes.Count == 1, p.Portes.Count + " portes");
            Point(p.Portes[0].Point, -80, 2.2);
            Assert.IsTrue(p.Portes[0].Rue == "plan" && p.Portes[0].Identifiant == 0 && p.Portes[0].LargeurM == 4);
            Assert.IsTrue(c.Count == 2 && c[0].Nature == "rue" && c[1].Nature == "enceinte" && c.All(x => x.Identifiant == 0 && x.MotifArret == null), "le relevé dans l'ordre servi");
            Assert.IsTrue(c[0].Bras == 5 && c[0].GrainPayeKg == 15 && c[1].Bras == 1 && c[1].GrainPayeKg == 3);
        }

        [Test] // Lot #925 — le contour servi devient 4 tours et 64 pans, aux piquets tant que la moitié du travail manque.
        public void LaBiskraMureeSeDecoupe()
        {
            LecturePlan lecture = LireBiskra(Fixture(MUREE)); Assert.IsTrue(lecture.Presente, lecture.Absence);
            EnceinteDuPlan e = lecture.Plan.Enceinte; DecoupeDeLEnceinte d = PansDeLEnceinte.Decouper(e);
            Assert.IsTrue(d.Presente && d.Pieces.Count == 68 && d.Pieces[17].Nature == NatureDePiece.Tour && d.Pieces[17].CentreX == 80 && d.Pieces[17].CentreY == -80, d.Absence + " " + d.Pieces.Count);
            Assert.AreEqual(EtapeDuBatiment.Piquets, PansDeLEnceinte.Etape(e));
        }

        [TestCase("\"enceinte\":{\"contour\"", "\"enceinte\":null,\"x\":{\"contour\"", "clé enceinte :", "un objet attendu")]
        [TestCase("[[-80,-80],[80,-80],[80,80],[-80,80]]", "[[-80,-80],[80,-80]]", "enceinte.contour", "au moins 3 points")]
        [TestCase("\"foyers\":2", "\"foyers\":1.5", "enceinte.foyers", "un entier")]
        [TestCase("\"travail_fourni\":1,\"travail_requis\":19200", "\"travail_fourni\":19201,\"travail_requis\":19200", "enceinte.travail_fourni", "dépasse")]
        [TestCase("\"en_chantier\":true,\"foyers\":2", "\"en_chantier\":false,\"foyers\":2", "enceinte.en_chantier", "contredit")]
        [TestCase(",\"portes\":[", ",\"portails\":[", "clé absente : portes", "portes")]
        [TestCase("\"enceinte\":{\"contour\":[[-80,-80],[80,-80],[80,80],[-80,80]],\"en_chantier\":true,\"foyers\":2,\"travail_fourni\":1,\"travail_requis\":19200},", "", "clé portes", "sans enceinte")]
        [TestCase("\"point\":[-80.0,2.2]", "\"point\":[-80.0]", "portes[0].point", "exactement 2 nombres")]
        [TestCase("\"rue\":\"plan\"", "\"rue\":\"chemin\"", "portes[0].rue", "plan ou base")]
        [TestCase("\"largeur_m\":4,\"point\"", "\"largeur_m\":0,\"point\"", "portes[0].largeur_m", "> 0")]
        [TestCase(PORTE, "\"identifiant\":3,\"largeur_m\":4,\"point\":[-80.0,2.2],\"rue\":\"plan\"", "portes[0].identifiant", "aucune rue 3")]
        [TestCase(PORTE, "\"identifiant\":7,\"largeur_m\":4,\"point\":[-80.0,2.2],\"rue\":\"base\"", "portes[0].identifiant", "aucune rue de base 7")]
        [TestCase("\"nature\":\"enceinte\"", "\"nature\":\"mur\"", "chantiers_du_jour[1].nature", "enceinte attendu")]
        public void UneEnceinteOuUnePorteMalFormeeRefuseLePlan(string ancien, string nouveau, string chemin, string precision)
        {
            string absence = RefusDeBiskra(RemplacerUneFois(Fixture(MUREE), ancien, nouveau));
            StringAssert.Contains(chemin, absence); StringAssert.Contains(precision, absence);
        }

        [Test]
        public void UnePorteDeBaseExigeLaBase()
        {
            string texte = RemplacerUneFois(Fixture(MUREE), PORTE, PORTE.Replace("\"plan\"", "\"base\"")); LecturePlan lecture = LireBiskra(texte);
            Assert.IsTrue(lecture.Presente && lecture.Plan.Portes[0].Rue == "base" && lecture.Plan.Portes[0].Identifiant == 0, lecture.Absence);
            StringAssert.Contains("aucune rue de base 0", RefusDeBiskra("{" + texte.Substring(texte.IndexOf("\"batiments\":", StringComparison.Ordinal))));
        }

        [Test]
        public void UnPlanSansEnceinteNAPasDePorte()
        {
            foreach (var (corps, cell) in new[] { (PLAN_JOUR, CellFigee), (Fixture("plan-biskra-graine0-tick0.json"), 10103L) })
            { Fermer(); Servir(200, corps); LecturePlan l = Lire(cell); Assert.IsTrue(l.Presente && l.Plan.Enceinte == null && l.Plan.Portes.Count == 0, l.Absence); }
            var nu = new PlanLu(1, 0, new RueDuPlan[0], new ParcelleDuPlan[0], new BatimentDuPlan[0]);
            Assert.IsTrue(nu.Enceinte == null && nu.Portes.Count == 0);
            Assert.Throws<ArgumentNullException>(() => new EnceinteDuPlan(null, true, 2, 19200, 1));
            Assert.Throws<ArgumentNullException>(() => new PorteDuPlan(new PointLocal(0, 0), null, 0, 4));
            Assert.Throws<NotSupportedException>(() => ((IList<PorteDuPlan>)nu.Portes).Add(null));
        }
    }
}
