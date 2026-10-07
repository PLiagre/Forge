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
        // Trois vraies cellules de `/carte` (seed 0), clés dans l'ordre du service, `cell_count` ramené à 3, recopiées du brief.
        // 10134 n'a ni puissance, ni maison, ni ville ; 10196 a un îlot puis un polygone percé d'un trou ;
        // 10417 a deux villes, et sa maison (27) diffère de sa puissance (3).
        private const string CARTE_TROIS = "{\"cell_count\":3,\"cells\":[{\"cell_id\":10134,\"contour\":{\"coordinates\":[[[[4276473,1135517],[4314106,1026553],[4157452,1024145],[4166760,1118721],[4276473,1135517]]]],\"type\":\"MultiPolygon\"},\"maison\":null,\"puissance\":null,\"relief\":\"plaine\",\"villes\":[]},{\"cell_id\":10196,\"contour\":{\"coordinates\":[[[[3255813,2017207],[3258432,2014942],[3252950,2017349],[3255813,2017207]]],[[[3260904,2014373],[3258233,2018288],[3248052,2019499],[3178677,2049953],[3214016,2181858],[3242818,2196329],[3344599,2164419],[3381106,2073504],[3289024,2001514],[3260904,2014373]],[[3256797,2044933],[3258232,2047203],[3254327,2044953],[3245580,2036516],[3242003,2025951],[3242985,2024693],[3248295,2030701],[3247211,2035050],[3251211,2041050],[3256797,2044933]]]],\"type\":\"MultiPolygon\"},\"maison\":{\"id\":6,\"nom\":\"Barcelone\"},\"puissance\":{\"id\":6,\"nom\":\"Aragon\"},\"relief\":\"montagne\",\"villes\":[]},{\"cell_id\":10417,\"contour\":{\"coordinates\":[[[[3921201,3092821],[3947718,3062031],[3938366,3011532],[3893790,2985836],[3858975,3008678],[3849915,3077567],[3921201,3092821]]]],\"type\":\"MultiPolygon\"},\"maison\":{\"id\":27,\"nom\":\"Valois-Bourgogne\"},\"puissance\":{\"id\":3,\"nom\":\"France\"},\"relief\":\"plaine\",\"villes\":[{\"nom\":\"Tournai\",\"population\":40000,\"x_m\":3853625.55,\"y_m\":3075988.58},{\"nom\":\"Valenciennes\",\"population\":23000,\"x_m\":3860893.43,\"y_m\":3047780.78}]}],\"crs\":\"EPSG:3035\",\"tolerance_m\":1000,\"version\":\"world-1400-v1\",\"villes_hors_carte\":[\"Venise\"]}";

        private int port;
        private HttpListener ecoute;
        private Thread fil;
        private volatile string cheminRecu, requeteRecue;

        [SetUp]
        public void PortLibre()
        {
            var sonde = new TcpListener(IPAddress.Loopback, 0);
            sonde.Start();
            port = ((IPEndPoint)sonde.LocalEndpoint).Port;
            sonde.Stop();
            cheminRecu = requeteRecue = null;
        }

        [TearDown]
        public void Fermer()
        {
            ecoute?.Close();
            fil?.Join(TimeSpan.FromSeconds(5));
            ecoute = null;
            fil = null;
        }

        // `attenteMs` : le service se tait ce temps avant de répondre. `muet` : il ne répond jamais.
        private void Servir(int statut, string corps, int attenteMs = 0, bool muet = false)
        {
            byte[] octets = Encoding.UTF8.GetBytes(corps);
            var auditeur = ecoute = new HttpListener();
            ecoute.Prefixes.Add("http://127.0.0.1:" + port + "/");
            ecoute.Start();
            fil = new Thread(() =>
            {
                HttpListenerContext contexte;
                try { contexte = auditeur.GetContext(); } catch (Exception) { return; }
                cheminRecu = contexte.Request.Url.AbsolutePath;
                requeteRecue = contexte.Request.Url.Query;
                if (muet) return;
                Thread.Sleep(attenteMs);
                contexte.Response.StatusCode = statut;
                contexte.Response.ContentLength64 = octets.Length;
                contexte.Response.OutputStream.Write(octets, 0, octets.Length);
                contexte.Response.OutputStream.Close();
            }) { IsBackground = true };
            fil.Start();
        }

        private LectureCarte Lire(string corps = null)
        {
            if (corps != null) Servir(200, corps);
            using (var client = new ClientCarte(port, ClientCarte.DelaiMinimal)) return client.Lire();
        }

        // Une absence qui commence par `carte : `, sans carte, et qui contient chacun des `attendus`.
        private void Absente(LectureCarte lecture, params string[] attendus)
        {
            Assert.IsFalse(lecture.Presente, "une réponse fautive ne rend jamais de carte");
            Assert.IsNull(lecture.Carte);
            StringAssert.StartsWith("carte : ", lecture.Absence);
            foreach (string attendu in attendus) StringAssert.Contains(attendu, lecture.Absence);
        }

        // `ancien` paraît exactement une fois dans `source` : la faute porte sur l'élément voulu, et sur lui seul.
        private static string RemplacerUneFois(string source, string ancien, string nouveau)
        {
            int premier = source.IndexOf(ancien, StringComparison.Ordinal);
            Assert.IsTrue(premier >= 0 && premier == source.LastIndexOf(ancien, StringComparison.Ordinal), "pas exactement une fois dans la carte : " + ancien);
            return source.Substring(0, premier) + nouveau + source.Substring(premier + ancien.Length);
        }

        // Égalités exactes (`==`) : un anneau de `nombre` points, dont le premier et le dernier valent (x, y).
        private static void Point(PointCarte p, double x, double y) => Assert.IsTrue(p.X == x && p.Y == y, "(" + x + ", " + y + ") attendu, reçu (" + p.X + ", " + p.Y + ")");
        private static void Anneau(IReadOnlyList<PointCarte> anneau, int nombre, double x, double y) { Assert.AreEqual(nombre, anneau.Count); Point(anneau[0], x, y); Point(anneau[nombre - 1], x, y); }
        private static void Identite(IdentiteDeCarte identite, long id, string nom) { Assert.IsTrue(identite != null && identite.Id == id && identite.Nom == nom, "(" + id + ", " + nom + ") attendu"); }

        private static void Cellule10196(CelluleDeCarte cellule)
        {
            Assert.IsTrue(cellule.CellId == 10196 && cellule.Villes.Count == 0 && cellule.Contour.Count == 2);
            Identite(cellule.Puissance, 6, "Aragon");
            Identite(cellule.Maison, 6, "Barcelone");
            Anneau(cellule.Contour[0].Exterieur, 4, 3255813, 2017207);
            Assert.AreEqual(0, cellule.Contour[0].Trous.Count);
            Anneau(cellule.Contour[1].Exterieur, 10, 3260904, 2014373);
            Assert.AreEqual(1, cellule.Contour[1].Trous.Count);
            Anneau(cellule.Contour[1].Trous[0], 10, 3256797, 2044933);
        }

        [Test]
        public void LaCarteServieEstRelueExactement()
        {
            LectureCarte lecture = Lire(CARTE_TROIS);

            Assert.AreEqual("/carte", cheminRecu);
            Assert.AreEqual("", requeteRecue);
            Assert.IsTrue(lecture.Presente && lecture.Absence == null, lecture.Absence);
            IReadOnlyList<CelluleDeCarte> cellules = lecture.Carte.Cellules;
            Assert.IsTrue(lecture.Carte.CellCount == 3 && cellules.Count == 3);
            Assert.IsTrue(cellules[0].CellId == 10134 && cellules[0].Puissance == null && cellules[0].Maison == null && cellules[0].Villes.Count == 0);
            Assert.IsTrue(cellules[0].Contour.Count == 1 && cellules[0].Contour[0].Trous.Count == 0);
            Anneau(cellules[0].Contour[0].Exterieur, 5, 4276473, 1135517);
            Point(cellules[0].Contour[0].Exterieur[3], 4166760, 1118721);
            Cellule10196(cellules[1]);
            Assert.IsTrue(cellules[2].CellId == 10417 && cellules[2].Contour.Count == 1 && cellules[2].Villes.Count == 2);
            Identite(cellules[2].Puissance, 3, "France");
            Identite(cellules[2].Maison, 27, "Valois-Bourgogne");
            Assert.AreEqual(7, cellules[2].Contour[0].Exterieur.Count);
            Point(cellules[2].Contour[0].Exterieur[0], 3921201, 3092821);
            VilleDeCarte tournai = cellules[2].Villes[0], valenciennes = cellules[2].Villes[1];
            Assert.IsTrue(tournai.Nom == "Tournai" && tournai.Population == 40000 && valenciennes.Nom == "Valenciennes" && valenciennes.Population == 23000);
            Point(tournai.Position, 3853625.55, 3075988.58);
            Point(valenciennes.Position, 3860893.43, 3047780.78);
        }

        [Test]
        public void LesClesQueLeClientNeLitPasNeSontPasExigees()
        {
            string allegee = RemplacerUneFois(CARTE_TROIS, "\"relief\":\"montagne\",", "");
            allegee = RemplacerUneFois(allegee, "\"tolerance_m\":1000,", "");
            LectureCarte lecture = Lire(RemplacerUneFois(allegee, ",\"villes_hors_carte\":[\"Venise\"]", ""));

            Assert.IsTrue(lecture.Presente && lecture.Carte.Cellules.Count == 3, lecture.Absence);
            Cellule10196(lecture.Carte.Cellules[1]);
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
            Assert.IsTrue(lecture.Presente && lecture.Carte.Cellules.Count == 3, lecture.Absence);
        }

        [Test]
        public void UnServiceMuetRendUneAbsenceDeDelaiDepasse()
        {
            Servir(200, CARTE_TROIS, muet: true);
            var chrono = Stopwatch.StartNew();
            LectureCarte lecture = Lire();
            Assert.IsTrue(chrono.ElapsedMilliseconds >= 9900, "attendu au moins 9900 ms, mesuré " + chrono.ElapsedMilliseconds);
            Absente(lecture, "délai dépassé");
        }

        [Test]
        public void UnServiceAbsentRendUneAbsence() => Absente(Lire(), "service absent");

        [Test]
        public void UnStatut500RendUneAbsenceQuiCiteLeCorps()
        {
            Servir(500, "{\"erreur\":\"x\"}");
            Absente(Lire(), "500", "x");
        }

        [Test]
        public void UnJsonCoupeRendUneAbsence() => Absente(Lire(CARTE_TROIS.Substring(0, CARTE_TROIS.Length - 1)), "JSON invalide");

        // Une seule faute par cas ; `precision` resserre ce que l'absence doit dire en plus du chemin.
        [TestCase("\"crs\":\"EPSG:3035\"", "\"crs\":\"EPSG:4326\"", "crs", "EPSG:4326")]
        [TestCase("\"cell_count\":3", "\"cell_count\":4", "cell_count", "4 annoncées")]
        [TestCase("{\"cell_id\":10196,", "{\"cell_id\":10134,", "cells[1].cell_id", "déjà lu")]
        [TestCase("{\"cell_id\":10417,", "{\"cell_id\":-1,", "cells[2].cell_id", "un entier ≥ 0")]
        [TestCase("\"type\":\"MultiPolygon\"},\"maison\":{\"id\":6", "\"type\":\"Polygon\"},\"maison\":{\"id\":6", "cells[1].contour.type", "MultiPolygon")]
        [TestCase("]]],[[[3260904", "]]],[],[[[3260904", "cells[1].contour.coordinates[1]", "au moins 1 élément")]
        [TestCase("[4157452,1024145],[4166760,1118721],", "", "cells[0].contour.coordinates[0][0]", "au moins 4 éléments")]
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
        public void UneCarteFautiveEstRefuseeEnNommantSonChemin(string ancien, string nouveau, string chemin, string precision) =>
            Absente(Lire(RemplacerUneFois(CARTE_TROIS, ancien, nouveau)), chemin, precision);

        [Test]
        public void UneCarteSansCelluleEstRefusee()
        {
            int debut = CARTE_TROIS.IndexOf("\"cells\":[", StringComparison.Ordinal), fin = CARTE_TROIS.IndexOf(",\"crs\"", StringComparison.Ordinal);
            string vide = RemplacerUneFois(CARTE_TROIS.Substring(0, debut) + "\"cells\":[]" + CARTE_TROIS.Substring(fin), "\"cell_count\":3", "\"cell_count\":0");
            Assert.IsTrue(debut >= 0 && fin > debut && vide != CARTE_TROIS && !vide.Contains("cell_id"));
            Absente(Lire(vide), "cells");
        }

        [Test]
        public void UneCarteNeSeFabriqueNiSansListeNiSansNomNiSansCause()
        {
            var points = new[] { new PointCarte(0, 0), new PointCarte(1, 0), new PointCarte(1, 1), new PointCarte(0, 0) };
            Assert.Throws<ArgumentNullException>(() => new PolygoneDeCarte(points, new IList<PointCarte>[] { null }));
            Assert.Throws<ArgumentNullException>(() => new CelluleDeCarte(1, new PolygoneDeCarte[0], null, null, null));
            Assert.Throws<ArgumentNullException>(() => new VilleDeCarte(null, 1, new PointCarte(0, 0)));
            Assert.Throws<ArgumentException>(() => LectureCarte.Absent(""));
        }
    }
}
