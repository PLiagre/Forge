using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using NUnit.Framework;

namespace Forge.Pont.Tests
{
    // Lot #520 — un faux service local rend la carte de 1400 ; le client en relit les cellules
    // telles quelles, ou rend une absence qui nomme sa cause et le chemin de la clé fautive.
    public sealed class ClientCarteTests
    {
        // Trois vraies cellules de `/carte` (seed 0), clés dans l'ordre du service, `cell_count` ramené à 3.
        // 10134 n'a ni puissance, ni maison, ni ville ; 10196 a un îlot puis un polygone percé d'un trou ;
        // 10417 a deux villes, et sa maison (27) diffère de sa puissance (3).
        private const string CARTE_TROIS =
            "{\"cell_count\":3,\"cells\":["
            + "{\"cell_id\":10134,\"contour\":{\"coordinates\":[[[[4276473,1135517],[4314106,1026553],[4157452,1024145],[4166760,1118721],[4276473,1135517]]]],\"type\":\"MultiPolygon\"},"
            + "\"maison\":null,\"puissance\":null,\"relief\":\"plaine\",\"villes\":[]},"
            + "{\"cell_id\":10196,\"contour\":{\"coordinates\":[[[[3255813,2017207],[3258432,2014942],[3252950,2017349],[3255813,2017207]]],"
            + "[[[3260904,2014373],[3258233,2018288],[3248052,2019499],[3178677,2049953],[3214016,2181858],[3242818,2196329],[3344599,2164419],[3381106,2073504],[3289024,2001514],[3260904,2014373]],"
            + "[[3256797,2044933],[3258232,2047203],[3254327,2044953],[3245580,2036516],[3242003,2025951],[3242985,2024693],[3248295,2030701],[3247211,2035050],[3251211,2041050],[3256797,2044933]]]],\"type\":\"MultiPolygon\"},"
            + "\"maison\":{\"id\":6,\"nom\":\"Barcelone\"},\"puissance\":{\"id\":6,\"nom\":\"Aragon\"},\"relief\":\"montagne\",\"villes\":[]},"
            + "{\"cell_id\":10417,\"contour\":{\"coordinates\":[[[[3921201,3092821],[3947718,3062031],[3938366,3011532],[3893790,2985836],[3858975,3008678],[3849915,3077567],[3921201,3092821]]]],\"type\":\"MultiPolygon\"},"
            + "\"maison\":{\"id\":27,\"nom\":\"Valois-Bourgogne\"},\"puissance\":{\"id\":3,\"nom\":\"France\"},\"relief\":\"plaine\","
            + "\"villes\":[{\"nom\":\"Tournai\",\"population\":40000,\"x_m\":3853625.55,\"y_m\":3075988.58},{\"nom\":\"Valenciennes\",\"population\":23000,\"x_m\":3860893.43,\"y_m\":3047780.78}]}],"
            + "\"crs\":\"EPSG:3035\",\"tolerance_m\":1000,\"version\":\"world-1400-v1\",\"villes_hors_carte\":[\"Venise\"]}";

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

        // `attenteMs` : le service se tait ce temps avant de répondre. `muet` : il ne répond jamais.
        private void Servir(int statut, string corps, int attenteMs = 0, bool muet = false)
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
                    requeteRecue = contexte.Request.Url.Query;
                    if (muet) continue;
                    if (attenteMs > 0) Thread.Sleep(attenteMs);
                    contexte.Response.StatusCode = statut;
                    contexte.Response.ContentType = "application/json; charset=utf-8";
                    contexte.Response.ContentLength64 = octets.Length;
                    contexte.Response.OutputStream.Write(octets, 0, octets.Length);
                    contexte.Response.OutputStream.Close();
                }
            }) { IsBackground = true };
            fil.Start();
        }

        private LectureCarte Lire()
        {
            using (var client = new ClientCarte(port, ClientCarte.DelaiMinimal)) return client.Lire();
        }

        private LectureCarte Absence()
        {
            LectureCarte lecture = Lire();
            Assert.IsFalse(lecture.Presente, "une réponse fautive ne rend jamais de carte");
            Assert.IsNull(lecture.Carte);
            Assert.IsNotNull(lecture.Absence);
            StringAssert.StartsWith("carte : ", lecture.Absence);
            return lecture;
        }

        // `ancien` paraît exactement une fois dans `source` : la faute porte sur l'élément voulu, et sur lui seul.
        private static string RemplacerUneFois(string source, string ancien, string nouveau)
        {
            int premier = source.IndexOf(ancien, StringComparison.Ordinal);
            Assert.IsTrue(premier >= 0, "absent de la carte : " + ancien);
            Assert.AreEqual(premier, source.LastIndexOf(ancien, StringComparison.Ordinal), "présent plus d'une fois : " + ancien);
            string altere = source.Substring(0, premier) + nouveau + source.Substring(premier + ancien.Length);
            Assert.AreNotEqual(source, altere, "le remplacement de " + ancien + " n'a rien changé");
            return altere;
        }

        private static void Point(PointCarte point, double x, double y)
        {
            Assert.IsTrue(point.X == x, "x attendu " + x + ", reçu " + point.X);
            Assert.IsTrue(point.Y == y, "y attendu " + y + ", reçu " + point.Y);
        }

        // Un anneau de `nombre` points, dont le premier et le dernier valent (x, y).
        private static void Anneau(IReadOnlyList<PointCarte> anneau, int nombre, double x, double y)
        {
            Assert.IsTrue(anneau.Count == nombre, nombre + " points attendus, reçu " + anneau.Count);
            Point(anneau[0], x, y);
            Point(anneau[anneau.Count - 1], x, y);
        }

        private static void Identite(IdentiteDeCarte identite, long id, string nom)
        {
            Assert.IsNotNull(identite);
            Assert.IsTrue(identite.Id == id, "id attendu " + id + ", reçu " + identite.Id);
            Assert.AreEqual(nom, identite.Nom);
        }

        private static void VerifierCellule10196(CelluleDeCarte cellule)
        {
            Assert.IsTrue(cellule.CellId == 10196);
            Identite(cellule.Puissance, 6, "Aragon");
            Identite(cellule.Maison, 6, "Barcelone");
            Assert.IsTrue(cellule.Villes.Count == 0);
            Assert.IsTrue(cellule.Contour.Count == 2);
            Anneau(cellule.Contour[0].Exterieur, 4, 3255813, 2017207);
            Assert.IsTrue(cellule.Contour[0].Trous.Count == 0);
            Anneau(cellule.Contour[1].Exterieur, 10, 3260904, 2014373);
            Assert.IsTrue(cellule.Contour[1].Trous.Count == 1, "un trou attendu, reçu " + cellule.Contour[1].Trous.Count);
            Anneau(cellule.Contour[1].Trous[0], 10, 3256797, 2044933);
        }

        [Test]
        public void LaCarteServieEstRelueExactement()
        {
            Servir(200, CARTE_TROIS);

            LectureCarte lecture = Lire();

            Assert.AreEqual("/carte", cheminRecu);
            Assert.AreEqual("", requeteRecue);
            Assert.IsTrue(lecture.Presente, lecture.Absence);
            Assert.IsNull(lecture.Absence);
            CarteLue carte = lecture.Carte;
            Assert.IsTrue(carte.CellCount == 3);
            Assert.IsTrue(carte.Cellules.Count == 3);

            CelluleDeCarte premiere = carte.Cellules[0];
            Assert.IsTrue(premiere.CellId == 10134);
            Assert.IsNull(premiere.Puissance);
            Assert.IsNull(premiere.Maison);
            Assert.IsTrue(premiere.Villes.Count == 0);
            Assert.IsTrue(premiere.Contour.Count == 1);
            Assert.IsTrue(premiere.Contour[0].Trous.Count == 0);
            Anneau(premiere.Contour[0].Exterieur, 5, 4276473, 1135517);
            Point(premiere.Contour[0].Exterieur[3], 4166760, 1118721);

            VerifierCellule10196(carte.Cellules[1]);

            CelluleDeCarte troisieme = carte.Cellules[2];
            Assert.IsTrue(troisieme.CellId == 10417);
            Identite(troisieme.Puissance, 3, "France");
            Identite(troisieme.Maison, 27, "Valois-Bourgogne");
            Assert.IsTrue(troisieme.Contour.Count == 1);
            Anneau(troisieme.Contour[0].Exterieur, 7, 3921201, 3092821);
            Assert.IsTrue(troisieme.Villes.Count == 2);
            Assert.AreEqual("Tournai", troisieme.Villes[0].Nom);
            Assert.IsTrue(troisieme.Villes[0].Population == 40000);
            Point(troisieme.Villes[0].Position, 3853625.55, 3075988.58);
            Assert.AreEqual("Valenciennes", troisieme.Villes[1].Nom);
            Assert.IsTrue(troisieme.Villes[1].Population == 23000);
            Point(troisieme.Villes[1].Position, 3860893.43, 3047780.78);
        }

        [Test]
        public void LesClesQueLeClientNeLitPasNeSontPasExigees()
        {
            string allegee = RemplacerUneFois(CARTE_TROIS, "\"relief\":\"montagne\",", "");
            allegee = RemplacerUneFois(allegee, "\"tolerance_m\":1000,", "");
            allegee = RemplacerUneFois(allegee, ",\"villes_hors_carte\":[\"Venise\"]", "");
            Servir(200, allegee);

            LectureCarte lecture = Lire();

            Assert.IsTrue(lecture.Presente, lecture.Absence);
            Assert.IsTrue(lecture.Carte.Cellules.Count == 3);
            VerifierCellule10196(lecture.Carte.Cellules[1]);
        }

        [Test]
        public void LeDelaiTientAuMoinsDixSecondesEtLePortSesBornes()
        {
            Assert.IsTrue(ClientCarte.DelaiMinimal == TimeSpan.FromSeconds(10));
            Assert.Throws<ArgumentOutOfRangeException>(() => new ClientCarte(8000, TimeSpan.FromMilliseconds(9999)));
            Assert.Throws<ArgumentOutOfRangeException>(() => new ClientCarte(8000, Timeout.InfiniteTimeSpan));
            Assert.Throws<ArgumentOutOfRangeException>(() => new ClientCarte(0, ClientCarte.DelaiMinimal));
            Assert.Throws<ArgumentOutOfRangeException>(() => new ClientCarte(65536, ClientCarte.DelaiMinimal));
            Assert.DoesNotThrow(() => new ClientCarte(8000, TimeSpan.FromSeconds(10)).Dispose());
        }

        [Test]
        public void UnServiceLentQuiCalculeLaCarteEstAttendu()
        {
            Servir(200, CARTE_TROIS, attenteMs: 2500);

            LectureCarte lecture = Lire();

            Assert.IsTrue(lecture.Presente, lecture.Absence);
            Assert.IsTrue(lecture.Carte.Cellules.Count == 3);
        }

        [Test]
        public void UnServiceMuetRendUneAbsenceDeDelaiDepasse()
        {
            Servir(200, CARTE_TROIS, muet: true);

            var chrono = Stopwatch.StartNew();
            LectureCarte lecture = Absence();
            chrono.Stop();

            StringAssert.Contains("délai dépassé", lecture.Absence);
            Assert.IsTrue(chrono.ElapsedMilliseconds >= 9900, "attendu au moins 9900 ms, mesuré " + chrono.ElapsedMilliseconds);
        }

        [Test]
        public void UnServiceAbsentRendUneAbsence()
        {
            StringAssert.Contains("service absent", Absence().Absence);
        }

        [Test]
        public void UnStatut500RendUneAbsenceQuiCiteLeCorps()
        {
            Servir(500, "{\"erreur\":\"x\"}");

            LectureCarte lecture = Absence();

            StringAssert.Contains("500", lecture.Absence);
            StringAssert.Contains("x", lecture.Absence);
        }

        [Test]
        public void UnJsonCoupeRendUneAbsence()
        {
            Assert.IsTrue(CARTE_TROIS.EndsWith("}"));
            Servir(200, CARTE_TROIS.Substring(0, CARTE_TROIS.Length - 1));

            StringAssert.Contains("JSON invalide", Absence().Absence);
        }

        // Une seule faute par cas ; `precision` resserre ce que l'absence doit dire en plus du chemin.
        [TestCase("\"crs\":\"EPSG:3035\"", "\"crs\":\"EPSG:4326\"", "crs", "EPSG:4326")]
        [TestCase("\"cell_count\":3", "\"cell_count\":4", "cell_count", "4 annoncées")]
        [TestCase("{\"cell_id\":10196,", "{\"cell_id\":10134,", "cells[1].cell_id", "déjà lu")]
        [TestCase("{\"cell_id\":10417,", "{\"cell_id\":-1,", "cells[2].cell_id", "un entier ≥ 0")]
        [TestCase("\"type\":\"MultiPolygon\"},\"maison\":{\"id\":6", "\"type\":\"Polygon\"},\"maison\":{\"id\":6", "cells[1].contour.type", "MultiPolygon")]
        [TestCase("]]],[[[3260904", "]]],[],[[[3260904", "cells[1].contour.coordinates[1]", "au moins un anneau")]
        [TestCase("[4157452,1024145],[4166760,1118721],", "", "cells[0].contour.coordinates[0][0]", "au moins 4 points")]
        [TestCase("[4166760,1118721],[4276473,1135517]]", "[4166760,1118721],[4276473,1135518]]", "cells[0].contour.coordinates[0][0]", "fermé")]
        [TestCase("[[3256797,2044933],", "[[\"3256797\",2044933],", "cells[1].contour.coordinates[1][1][0]", "un nombre attendu")]
        [TestCase("[3921201,3092821],[3947718", "[3921201,3092821,0],[3947718", "cells[2].contour.coordinates[0][0][0]", "exactement 2 nombres")]
        [TestCase("\"puissance\":{\"id\":3,\"nom\":\"France\"},", "", "clé absente : cells[2].puissance", "clé absente")]
        [TestCase("\"maison\":{\"id\":27,", "\"maison\":{\"id\":\"27\",", "cells[2].maison.id", "un nombre attendu")]
        [TestCase("\"nom\":\"Aragon\"", "\"nom\":\" \"", "cells[1].puissance.nom", "un texte non vide")]
        [TestCase("\"maison\":null,", "\"maison\":7,", "cells[0].maison", "null ou un objet")]
        [TestCase(",\"villes\":[]},{\"cell_id\":10196", "},{\"cell_id\":10196", "clé absente : cells[0].villes", "clé absente")]
        [TestCase("\"villes\":[]},{\"cell_id\":10417", "\"villes\":null},{\"cell_id\":10417", "cells[1].villes", "un tableau attendu")]
        [TestCase("\"population\":23000,", "\"population\":23000.5,", "cells[2].villes[1].population", "un entier")]
        [TestCase("\"x_m\":3860893.43,", "", "cells[2].villes[1].x_m", "clé absente")]
        public void UneCarteFautiveEstRefuseeEnNommantSonChemin(string ancien, string nouveau, string chemin, string precision)
        {
            Servir(200, RemplacerUneFois(CARTE_TROIS, ancien, nouveau));

            LectureCarte lecture = Absence();

            StringAssert.Contains(chemin, lecture.Absence);
            StringAssert.Contains(precision, lecture.Absence);
        }

        [Test]
        public void UneCarteSansCelluleEstRefusee()
        {
            int debut = CARTE_TROIS.IndexOf("\"cells\":[", StringComparison.Ordinal);
            int fin = CARTE_TROIS.IndexOf(",\"crs\"", StringComparison.Ordinal);
            Assert.IsTrue(debut >= 0 && fin > debut);
            string vide = CARTE_TROIS.Substring(0, debut) + "\"cells\":[]" + CARTE_TROIS.Substring(fin);
            vide = RemplacerUneFois(vide, "\"cell_count\":3", "\"cell_count\":0");
            Assert.AreNotEqual(CARTE_TROIS, vide);
            StringAssert.DoesNotContain("cell_id", vide);
            Servir(200, vide);

            StringAssert.Contains("cells", Absence().Absence);
        }

        [Test]
        public void UneCarteNeSeFabriqueNiSansListeNiSansNomNiSansCause()
        {
            var points = new[] { new PointCarte(0, 0), new PointCarte(1, 0), new PointCarte(1, 1), new PointCarte(0, 0) };
            Assert.Throws<ArgumentNullException>(() => new PolygoneDeCarte(null, new IList<PointCarte>[0]));
            Assert.Throws<ArgumentNullException>(() => new PolygoneDeCarte(points, null));
            Assert.Throws<ArgumentNullException>(() => new PolygoneDeCarte(points, new IList<PointCarte>[] { null }));
            Assert.Throws<ArgumentNullException>(() => new IdentiteDeCarte(1, null));
            Assert.Throws<ArgumentNullException>(() => new VilleDeCarte(null, 1, new PointCarte(0, 0)));
            Assert.Throws<ArgumentNullException>(() => new CelluleDeCarte(1, null, null, null, new VilleDeCarte[0]));
            Assert.Throws<ArgumentNullException>(() => new CelluleDeCarte(1, new PolygoneDeCarte[0], null, null, null));
            Assert.Throws<ArgumentNullException>(() => new CarteLue(0, null));
            Assert.Throws<ArgumentNullException>(() => LectureCarte.De(null));
            Assert.Throws<ArgumentException>(() => LectureCarte.Absent(null));
            Assert.Throws<ArgumentException>(() => LectureCarte.Absent(""));
        }
    }
}
