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
    }
}
