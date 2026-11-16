using System;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using NUnit.Framework;

namespace Forge.Pont.Tests
{
    // La caserne de Biskra que le service rend (`test_batiments.py` reproduit ces octets) : le Zab, une route à
    // l'est de la place, la parcelle 0 de 10 m × 20 m, puis la caserne sur elle, au premier jour de son chantier
    // (tick 8) et au jour de son achèvement (tick 39). Le pont la lit, en tire son étape et sa pose, et forme
    // l'intention qui la pose.
    public sealed class PoseDeCaserneTests
    {
        private const long Biskra = 10103;
        private const string EN_CHANTIER = "plan-biskra-caserne-graine0-tick8.json";
        private const string ACHEVEE = "plan-biskra-caserne-achevee-graine0-tick39.json";
        private const string CASERNE_SERVIE =
            "{\"en_chantier\":true,\"identifiant\":0,\"nature\":\"caserne\",\"parcelle\":0,\"travail_fourni\":25,\"travail_requis\":800}";

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
            if (ecoute != null) { ecoute.Close(); ecoute = null; }
            fil?.Join(TimeSpan.FromSeconds(5));
            fil = null;
        }

        private static string Fixture(string nom) =>
            System.IO.File.ReadAllText(UnityEngine.Application.dataPath + "/ForgeLocal3D/Pont/Tests/" + nom);

        // Un seul remplacement, et la preuve qu'il a changé le texte.
        private static string Remplacer(string source, string ancien, string nouveau)
        {
            string altere = source.Replace(ancien, nouveau);
            Assert.AreNotEqual(source, altere, "le remplacement de " + ancien + " n'a rien changé");
            return altere;
        }

        private LecturePlan Lire(string corps)
        {
            Fermer();
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
                    contexte.Response.StatusCode = 200;
                    contexte.Response.ContentType = "application/json; charset=utf-8";
                    contexte.Response.ContentLength64 = octets.Length;
                    contexte.Response.OutputStream.Write(octets, 0, octets.Length);
                    contexte.Response.OutputStream.Close();
                }
            }) { IsBackground = true };
            fil.Start();
            using (var client = new ClientPlan(port, TimeSpan.FromSeconds(5))) return client.Lire(Biskra);
        }

        private PlanLu Plan(string corps)
        {
            LecturePlan lecture = Lire(corps);
            Assert.IsTrue(lecture.Presente, lecture.Absence);
            return lecture.Plan;
        }

        private string Refus(string corps)
        {
            LecturePlan lecture = Lire(corps);
            Assert.IsTrue(!lecture.Presente && lecture.Plan == null && lecture.Absence.Contains("10103"), "une faute ne rend jamais de plan partiel");
            return lecture.Absence;
        }

        // ---- Le chantier que le monde sert ------------------------------------------------------

        [Test]
        public void LaCaserneEnChantierEstCelleQueLeMondeSert()
        {
            string texte = Fixture(EN_CHANTIER);
            StringAssert.Contains(CASERNE_SERVIE, texte, "la réponse figée porte la caserne au premier jour");
            PlanLu p = Plan(texte);
            Assert.IsTrue(p.Tick == 8 && p.Parcelles.Count == 1 && p.Batiments.Count == 0 && p.BatimentsDeProvince.Count == 1);
            BatimentDeProvinceDuPlan c = p.BatimentsDeProvince[0];
            Assert.IsTrue(c.Identifiant == 0 && c.Nature == "caserne" && c.Parcelle == 0, c.Nature + " sur " + c.Parcelle);
            Assert.IsTrue(c.EnChantier && c.TravailRequis == 800 && c.TravailFourni == 25, c.TravailFourni + " / " + c.TravailRequis);
            Assert.IsTrue(!p.Parcelles[0].EnChantier, "la caserne se tient sur une parcelle achevée");
            Assert.AreEqual(EtapeDuBatiment.Piquets, LectureDuBatiment.Etape(c));
        }

        [Test]
        public void LaCaserneAcheveeEstFinie()
        {
            PlanLu p = Plan(Fixture(ACHEVEE));
            Assert.IsTrue(p.Tick == 39 && p.BatimentsDeProvince.Count == 1 && p.Batiments.Count == 0);
            BatimentDeProvinceDuPlan c = p.BatimentsDeProvince[0];
            Assert.IsTrue(c.Nature == "caserne" && c.Parcelle == 0 && !c.EnChantier && c.TravailFourni == 800 && c.TravailRequis == 800);
            Assert.AreEqual(EtapeDuBatiment.Fini, LectureDuBatiment.Etape(c));
        }

        // Piquets tant que moins de la moitié du travail est fournie, murs ensuite, finie une fois achevée.
        [TestCase(0, true, EtapeDuBatiment.Piquets)]
        [TestCase(25, true, EtapeDuBatiment.Piquets)]
        [TestCase(399, true, EtapeDuBatiment.Piquets)]
        [TestCase(400, true, EtapeDuBatiment.Murs)]
        [TestCase(799, true, EtapeDuBatiment.Murs)]
        [TestCase(800, false, EtapeDuBatiment.Fini)]
        public void LaCasernePasseParSesTroisEtats(long fourni, bool enChantier, EtapeDuBatiment attendue)
        {
            var c = new BatimentDeProvinceDuPlan(0, "caserne", 0, enChantier, 800, fourni);
            Assert.AreEqual(attendue, LectureDuBatiment.Etape(c));
        }

        // La caserne se pose sur le contour servi de sa parcelle, par la règle de façade des bâtiments du plan :
        // la parcelle borde la route au sud (y = -8), sa façade regarde le sud.
        [Test]
        public void LaCaserneSePoseSurSaParcelleFaceALaRue()
        {
            PlanLu p = Plan(Fixture(EN_CHANTIER));
            PoseDuBatiment pose = LectureDuBatiment.Poser(p.BatimentsDeProvince[0], p);
            Assert.IsTrue(pose.Presente, pose.Absence);
            var commeUnBatiment = LectureDuBatiment.Poser(new BatimentDuPlan(9, 0, "maison", new List<PointLocal>(p.Parcelles[0].Contour), false, 1, 1));
            Assert.AreEqual(85, pose.CentreX, 1e-9); Assert.AreEqual(4, pose.CentreY, 1e-9);
            Assert.AreEqual(0, pose.FacadeX, 1e-9); Assert.AreEqual(-1, pose.FacadeY, 1e-9);
            Assert.AreEqual(commeUnBatiment.LacetDegres, pose.LacetDegres, 1e-9);
            Assert.AreEqual(commeUnBatiment.CentreX, pose.CentreX, 1e-9);
        }

        [Test]
        public void UneCaserneSansParcelleOuHorsDuPlanNEstPasPosee()
        {
            PlanLu p = Plan(Fixture(EN_CHANTIER));
            var carte = new BatimentDeProvinceDuPlan(3, "caserne", BatimentDeProvinceDuPlan.SansParcelle, true, 800, 0);
            PoseDuBatiment sans = LectureDuBatiment.Poser(carte, p);
            Assert.IsTrue(!sans.Presente && sans.Absence.Contains("aucune parcelle") && double.IsNaN(sans.CentreX), sans.Absence);
            var ailleurs = new BatimentDeProvinceDuPlan(4, "caserne", 7, true, 800, 0);
            PoseDuBatiment hors = LectureDuBatiment.Poser(ailleurs, p);
            Assert.IsTrue(!hors.Presente && hors.Absence.Contains("parcelle 7 absente"), hors.Absence);
        }

        // ---- La lecture et ses refus --------------------------------------------------------------

        [Test]
        public void UnPlanSansBatimentDeProvinceEnSertUneListeVide()
        {
            PlanLu p = Plan(Fixture("plan-biskra-graine0-tick0.json"));
            Assert.IsTrue(p.BatimentsDeProvince != null && p.BatimentsDeProvince.Count == 0);
        }

        [Test]
        public void UnBatimentPoseDepuisLaCarteEstSansParcelle()
        {
            PlanLu p = Plan(Remplacer(Fixture(EN_CHANTIER), "\"parcelle\":0,\"travail_fourni\":25", "\"parcelle\":null,\"travail_fourni\":25"));
            Assert.AreEqual(BatimentDeProvinceDuPlan.SansParcelle, p.BatimentsDeProvince[0].Parcelle);
        }

        [TestCase("\"parcelle\":0,\"travail_fourni\":25", "\"parcelle\":7,\"travail_fourni\":25", "batiments_de_province[0].parcelle", "aucune parcelle 7")]
        [TestCase("\"parcelle\":0,\"travail_fourni\":25", "\"travail_fourni\":25", "batiments_de_province[0].parcelle", "clé absente")]
        [TestCase("\"nature\":\"caserne\"", "\"nature\":\"\"", "batiments_de_province[0].nature", "texte non vide")]
        [TestCase("\"travail_fourni\":25", "\"travail_fourni\":801", "batiments_de_province[0].travail_fourni", "dépasse")]
        [TestCase("\"en_chantier\":true,\"identifiant\":0", "\"en_chantier\":false,\"identifiant\":0", "batiments_de_province[0].en_chantier", "contredit")]
        [TestCase(CASERNE_SERVIE, "", "batiments_de_province", "servie vide")]
        public void UnBatimentDeProvinceMalFormeRefuseLePlan(string ancien, string nouveau, string chemin, string motif)
        {
            string absence = Refus(Remplacer(Fixture(EN_CHANTIER), ancien, nouveau));
            StringAssert.Contains(chemin, absence);
            StringAssert.Contains(motif, absence);
        }

        // ---- Le geste ------------------------------------------------------------------------------

        // L'intention est celle que le joueur du Zab dépose au service dans `test_batiments.py`.
        [Test]
        public void LaCaserneSePoseEtLIntentionEstCelleQueLeMondeAttend()
        {
            PlanLu p = Plan(Fixture(EN_CHANTIER));
            CasernePosee pose = PoseDeCaserne.Calculer(p, new PointLocal(85, 4), "seigneurie-6");
            Assert.IsTrue(pose.Presente, pose.Absence);
            Assert.AreEqual(0, pose.Parcelle);
            Assert.AreEqual("{\"type\":\"batir_dans_une_province\",\"maison\":\"seigneurie-6\",\"cell\":10103,\"nature\":\"caserne\",\"parcelle\":0}",
                pose.IntentionJson);
            var relue = LecteurJson.LireObjet(pose.IntentionJson);
            Assert.IsTrue(relue.Count == 5 && (string)relue["nature"] == "caserne" && (double)relue["parcelle"] == 0 && (double)relue["cell"] == 10103);
        }

        // Le pont ne juge pas la parcelle prise : la caserne déjà là, il forme la même intention et le monde refusera.
        [Test]
        public void LePontLaisseLeMondeJugerLaParcellePrise()
        {
            PlanLu p = Plan(Fixture(ACHEVEE));
            CasernePosee pose = PoseDeCaserne.Calculer(p, new PointLocal(81, 13), "seigneurie-6");
            Assert.IsTrue(pose.Presente && pose.Parcelle == 0, pose.Absence);
        }

        [TestCase(200, 4, "seigneurie-6", "aucune parcelle sous le point : (200, 4)")]
        [TestCase(double.NaN, 4, "seigneurie-6", "point non fini")]
        [TestCase(85, 4, null, "maison mal formée : null")]
        [TestCase(85, 4, "", "maison mal formée")]
        [TestCase(85, 4, "Seigneurie-6", "maison mal formée")]
        [TestCase(85, 4, "seigneurie-6\",\"x\":\"", "maison mal formée")]
        public void UneCaserneQuiNeSePosePasNommeSaCause(double x, double y, string maison, string cause)
        {
            CasernePosee pose = PoseDeCaserne.Calculer(Plan(Fixture(EN_CHANTIER)), new PointLocal(x, y), maison);
            Assert.IsTrue(!pose.Presente && pose.IntentionJson == null && pose.Parcelle == -1);
            StringAssert.Contains(cause, pose.Absence);
        }

        [Test]
        public void SansParcelleAuPlanLaCaserneNeSePosePas()
        {
            var vide = new PlanLu(Biskra, 0, new RueDuPlan[0], new ParcelleDuPlan[0], new BatimentDuPlan[0]);
            Assert.AreEqual("aucune parcelle au plan", PoseDeCaserne.Calculer(vide, new PointLocal(0, 0), "seigneurie-6").Absence);
        }
    }
}
