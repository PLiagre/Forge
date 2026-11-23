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
    // Un faux service local rend les formes (`/formes`) ; le client en relit les cellules et les lieux
    // tels quels, ou rend une absence qui nomme sa cause et le chemin de la clé fautive.
    public sealed class ClientFormesTests
    {
        // Deux cellules dans la forme servie (clés dans l'ordre du service), coordonnées réduites et toutes distinctes.
        // La cellule 10 a deux lieux ; la 20, trouée, en a trois, et son premier lieu est fait de deux polygones.
        private const string FORMES =
            "{\"cells\":[" +
            "{\"cell_id\":10,\"contour\":{\"coordinates\":[[[[0,0],[100,0],[100,100],[0,0]]]],\"type\":\"MultiPolygon\"},\"lieux\":[" +
            "{\"contour\":{\"coordinates\":[[[[1,1],[50,1],[50,50],[1,1]]]],\"type\":\"MultiPolygon\"},\"rang\":0}," +
            "{\"contour\":{\"coordinates\":[[[[2,2],[60,2],[60,60],[2,2]]]],\"type\":\"MultiPolygon\"},\"rang\":1}]}," +
            "{\"cell_id\":20,\"contour\":{\"coordinates\":[[[[200,0],[300,0],[300,100],[200,0]],[[210,10],[250,10],[250,50],[210,10]]]],\"type\":\"MultiPolygon\"},\"lieux\":[" +
            "{\"contour\":{\"coordinates\":[[[[3,3],[40,3],[40,40],[3,3]]],[[[4,4],[8,4],[8,8],[4,4]]]],\"type\":\"MultiPolygon\"},\"rang\":0}," +
            "{\"contour\":{\"coordinates\":[[[[5,5],[70,5],[70,70],[5,5]]]],\"type\":\"MultiPolygon\"},\"rang\":1}," +
            "{\"contour\":{\"coordinates\":[[[[6,6],[80,6],[80,80],[6,6]]]],\"type\":\"MultiPolygon\"},\"rang\":2}]}]," +
            "\"crs\":\"EPSG:3035\",\"version\":\"world-1400-v1\"}";

        private const string DOSSIER = "/ForgeLocal3D/Pont/Tests/";

        // Comptes mesurés sur l'extrait figé (seed 0), écrits en dur : le lecteur ne fournit jamais ses propres attentes.
        // Chaque cellule de l'extrait et son nombre de lieux.
        private static readonly (long cellId, int lieux)[] CELLULES_FIGEES =
        {
            (1412, 1), (10177, 19), (10178, 12), (10192, 20), (10196, 25), (10210, 24), (10256, 12), (10260, 10),
            (10265, 9), (10267, 12), (10268, 10), (10446, 10), (10447, 10), (10454, 13), (10456, 12), (10466, 12),
        };

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

        private void Servir(int statut, string corps)
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
                contexte.Response.StatusCode = statut;
                contexte.Response.ContentLength64 = octets.Length;
                contexte.Response.OutputStream.Write(octets, 0, octets.Length);
                contexte.Response.OutputStream.Close();
            }) { IsBackground = true };
            fil.Start();
        }

        private LectureFormes Lire(string corps = null)
        {
            if (corps != null) Servir(200, corps);
            using (var client = new ClientFormes(port, ClientFormes.DelaiMinimal)) return client.Lire();
        }

        private static string Figee(string nom) => System.IO.File.ReadAllText(UnityEngine.Application.dataPath + DOSSIER + nom, Encoding.UTF8);

        // Une absence qui commence par `formes : `, sans formes, et qui contient chacun des `attendus`.
        private static void Absente(LectureFormes lecture, params string[] attendus)
        {
            Assert.IsFalse(lecture.Presente, "une réponse fautive ne rend jamais de formes");
            Assert.IsNull(lecture.Formes);
            StringAssert.StartsWith("formes : ", lecture.Absence);
            foreach (string attendu in attendus) StringAssert.Contains(attendu, lecture.Absence);
        }

        // `ancien` paraît exactement une fois dans `source` : la faute porte sur l'élément voulu, et sur lui seul.
        private static string RemplacerUneFois(string source, string ancien, string nouveau)
        {
            int premier = source.IndexOf(ancien, StringComparison.Ordinal);
            Assert.IsTrue(premier >= 0 && premier == source.LastIndexOf(ancien, StringComparison.Ordinal), "pas exactement une fois dans les formes : " + ancien);
            return source.Substring(0, premier) + nouveau + source.Substring(premier + ancien.Length);
        }

        // Égalités exactes (`==`) : un point relu au mètre près.
        private static void Point(PointCarte p, double x, double y) => Assert.IsTrue(p.X == x && p.Y == y, "(" + x + ", " + y + ") attendu, reçu (" + p.X + ", " + p.Y + ")");
        private static void Anneau(IReadOnlyList<PointCarte> anneau, int nombre, double x, double y) { Assert.AreEqual(nombre, anneau.Count); Point(anneau[0], x, y); Point(anneau[nombre - 1], x, y); }

        [Test]
        public void LesFormesServiesSontReluesExactement()
        {
            LectureFormes lecture = Lire(FORMES);

            Assert.AreEqual("/formes", cheminRecu);
            Assert.AreEqual("", requeteRecue);
            Assert.IsTrue(lecture.Presente && lecture.Absence == null, lecture.Absence);
            FormesLues formes = lecture.Formes;
            Assert.AreEqual("world-1400-v1", formes.Version);
            Assert.AreEqual(2, formes.Cellules.Count);

            FormeDeCellule dix = formes.Cellules[0], vingt = formes.Cellules[1];
            Assert.AreEqual(10, dix.CellId);
            Assert.AreEqual(1, dix.Contour.Count);
            Anneau(dix.Contour[0].Exterieur, 4, 0, 0);
            Assert.AreEqual(0, dix.Contour[0].Trous.Count);
            Assert.AreEqual(2, dix.Lieux.Count);
            Assert.IsTrue(dix.Lieux[0].Rang == 0 && dix.Lieux[1].Rang == 1);
            Anneau(dix.Lieux[0].Contour[0].Exterieur, 4, 1, 1);
            Point(dix.Lieux[1].Contour[0].Exterieur[1], 60, 2);

            Assert.AreEqual(20, vingt.CellId);
            Anneau(vingt.Contour[0].Exterieur, 4, 200, 0);
            Assert.AreEqual(1, vingt.Contour[0].Trous.Count);
            Anneau(vingt.Contour[0].Trous[0], 4, 210, 10);
            Assert.AreEqual(3, vingt.Lieux.Count);
            Assert.IsTrue(vingt.Lieux[0].Rang == 0 && vingt.Lieux[1].Rang == 1 && vingt.Lieux[2].Rang == 2);
            Assert.AreEqual(2, vingt.Lieux[0].Contour.Count);
            Anneau(vingt.Lieux[0].Contour[0].Exterieur, 4, 3, 3);
            Anneau(vingt.Lieux[0].Contour[1].Exterieur, 4, 4, 4);
            Point(vingt.Lieux[2].Contour[0].Exterieur[2], 80, 80);

            Assert.AreSame(dix, formes.De(10));
            Assert.AreSame(vingt, formes.De(20));
            Assert.IsNull(formes.De(15));
            Assert.IsNull(formes.De(0));
        }

        [Test]
        public void LesCollectionsRenduesSontEnLectureSeule()
        {
            FormesLues formes = Lire(FORMES).Formes;

            Assert.Throws<NotSupportedException>(() => ((IList<FormeDeCellule>)formes.Cellules).Add(null));
            Assert.Throws<NotSupportedException>(() => ((IList<FormeDeLieu>)formes.Cellules[0].Lieux).Add(null));
            Assert.Throws<NotSupportedException>(() => ((IList<PolygoneDeCarte>)formes.Cellules[0].Contour).Add(null));
            Assert.Throws<NotSupportedException>(() => ((IList<PolygoneDeCarte>)formes.Cellules[0].Lieux[0].Contour).Add(null));
        }

        [Test]
        public void UneVersionNulleEstUneMesure()
        {
            LectureFormes lecture = Lire(RemplacerUneFois(FORMES, "\"version\":\"world-1400-v1\"", "\"version\":null"));

            Assert.IsTrue(lecture.Presente && lecture.Absence == null, lecture.Absence);
            Assert.IsNull(lecture.Formes.Version);
            Assert.AreEqual(2, lecture.Formes.Cellules.Count);
        }

        [Test]
        public void LExtraitFigeDuServiceEstReluSurToutesSesCellules()
        {
            LectureFormes lecture = Lire(Figee("formes-graine0-ouest.json"));

            Assert.IsTrue(lecture.Presente, lecture.Absence);
            FormesLues formes = lecture.Formes;
            Assert.AreEqual("world-1400-v1", formes.Version);
            Assert.AreEqual(CELLULES_FIGEES.Length, formes.Cellules.Count);
            for (int i = 0; i < CELLULES_FIGEES.Length; i++)
            {
                FormeDeCellule cellule = formes.Cellules[i];
                Assert.AreEqual(CELLULES_FIGEES[i].cellId, cellule.CellId);
                Assert.AreEqual(CELLULES_FIGEES[i].lieux, cellule.Lieux.Count, "lieux de la cellule " + cellule.CellId);
                Assert.IsTrue(cellule.Contour.Count >= 1, "contour vide pour " + cellule.CellId);
                for (int rang = 0; rang < cellule.Lieux.Count; rang++)
                {
                    Assert.AreEqual(rang, cellule.Lieux[rang].Rang, "rang du lieu " + rang + " de la cellule " + cellule.CellId);
                    Assert.IsTrue(cellule.Lieux[rang].Contour.Count >= 1, "contour vide : lieu " + rang + " de la cellule " + cellule.CellId);
                }
                Assert.AreSame(cellule, formes.De(cellule.CellId));
            }

            // Le premier point d'un lieu, relu au mètre près : la cellule partagée de Pampelune, puis Gênes.
            FormeDeCellule pampelune = formes.De(10192);
            Assert.IsNotNull(pampelune);
            Anneau(pampelune.Contour[0].Exterieur, 535, 3279339, 2348928);
            Anneau(pampelune.Lieux[0].Contour[0].Exterieur, 174, 3355768, 2269616);
            Anneau(pampelune.Lieux[19].Contour[0].Exterieur, 81, 3356738, 2293639);
            Anneau(formes.De(10456).Lieux[0].Contour[0].Exterieur, 154, 4209237, 2362798);
            // Un lieu en plusieurs polygones garde chacun des siens.
            Assert.AreEqual(3, formes.De(10454).Lieux[10].Contour.Count);
            Assert.AreEqual(2, formes.De(10260).Lieux[4].Contour.Count);
            // La cellule d'un seul lieu.
            Assert.AreEqual(1, formes.De(1412).Lieux.Count);
            Anneau(formes.De(1412).Lieux[0].Contour[0].Exterieur, 6, 5114521, 4351237);
        }

        // Les formes et la carte figées portent les mêmes cellules, dans le même ordre.
        [Test]
        public void LExtraitFigeCouvreLesCellulesDeLaCarteFigee()
        {
            LectureFormes formes = Lire(Figee("formes-graine0-ouest.json"));
            Assert.IsTrue(formes.Presente, formes.Absence);
            Fermer();
            PortLibre();
            Servir(200, Figee("carte-graine0-ouest.json"));
            LectureCarte carte;
            using (var client = new ClientCarte(port, ClientCarte.DelaiMinimal)) carte = client.Lire();

            Assert.IsTrue(carte.Presente, carte.Absence);
            Assert.AreEqual(CELLULES_FIGEES.Length, carte.Carte.CellCount);
            CollectionAssert.AreEqual(carte.Carte.Cellules.Select(c => c.CellId).ToArray(), formes.Formes.Cellules.Select(c => c.CellId).ToArray());
        }

        [Test]
        public void LeDelaiTientAuMoinsSoixanteSecondesEtLePortSesBornes()
        {
            Assert.IsTrue(ClientFormes.DelaiMinimal == TimeSpan.FromSeconds(60));
            Assert.Throws<ArgumentOutOfRangeException>(() => new ClientFormes(8000, TimeSpan.FromMilliseconds(59999)));
            Assert.Throws<ArgumentOutOfRangeException>(() => new ClientFormes(8000, Timeout.InfiniteTimeSpan));
            Assert.Throws<ArgumentOutOfRangeException>(() => new ClientFormes(0, ClientFormes.DelaiMinimal));
            Assert.Throws<ArgumentOutOfRangeException>(() => new ClientFormes(65536, ClientFormes.DelaiMinimal));
            Assert.DoesNotThrow(() => new ClientFormes(8000, TimeSpan.FromSeconds(60)).Dispose());
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
        public void UnStatut404RendUneAbsenceQuiLeDit()
        {
            Servir(404, "{\"erreur\":\"absent\"}");
            Absente(Lire(), "404", "absent");
        }

        [Test]
        public void UnJsonCoupeRendUneAbsence() => Absente(Lire(FORMES.Substring(0, FORMES.Length - 1)), "JSON invalide");

        // Une seule faute par cas ; `precision` resserre ce que l'absence doit dire en plus du chemin.
        [TestCase("\"crs\":\"EPSG:3035\"", "\"crs\":\"EPSG:4326\"", "crs", "EPSG:4326")]
        [TestCase("\"crs\":\"EPSG:3035\",", "", "clé absente : crs", "clé absente")]
        [TestCase(",\"version\":\"world-1400-v1\"", "", "clé absente : version", "clé absente")]
        [TestCase("\"version\":\"world-1400-v1\"", "\"version\":3", "version", "un texte non vide ou null")]
        [TestCase("\"version\":\"world-1400-v1\"", "\"version\":\"\"", "version", "un texte non vide ou null")]
        [TestCase("\"cells\":[", "\"celles\":[", "clé absente : cells", "clé absente")]
        [TestCase("\"cells\":[", "\"cells\":{},\"autres\":[", "cells", "un tableau attendu")]
        [TestCase("{\"cell_id\":10,\"contour\"", "{\"contour\"", "clé absente : cells[0].cell_id", "clé absente")]
        [TestCase("\"cell_id\":10,", "\"cell_id\":\"10\",", "cells[0].cell_id", "un nombre attendu")]
        [TestCase("\"cell_id\":20,", "\"cell_id\":-1,", "cells[1].cell_id", "un entier ≥ 0")]
        [TestCase("\"cell_id\":20,", "\"cell_id\":20.5,", "cells[1].cell_id", "un entier")]
        [TestCase("\"cell_id\":20,", "\"cell_id\":10,", "cells[1].cell_id", "strictement croissant")]
        [TestCase("\"cell_id\":10,", "\"cell_id\":30,", "cells[1].cell_id", "strictement croissant")]
        [TestCase("\"contour\":{\"coordinates\":[[[[0,0],[100,0],[100,100],[0,0]]]],\"type\":\"MultiPolygon\"},\"lieux\"", "\"lieux\"", "clé absente : cells[0].contour", "clé absente")]
        [TestCase("[[[[0,0],[100,0],[100,100],[0,0]]]],\"type\":\"MultiPolygon\"", "[[[[0,0],[100,0],[100,100],[0,0]]]],\"type\":\"Polygon\"", "cells[0].contour.type", "MultiPolygon")]
        [TestCase("[[[[200,0],[300,0],[300,100],[200,0]],[[210,10],[250,10],[250,50],[210,10]]]],\"type\":\"MultiPolygon\"", "[[[[200,0],[300,0],[300,100],[200,0]],[[210,10],[250,10],[250,50],[210,10]]]],\"kind\":\"MultiPolygon\"", "clé absente : cells[1].contour.type", "clé absente")]
        [TestCase("[[210,10],[250,10],[250,50],[210,10]]", "[[210,10],[250,10],[250,50],[210,11]]", "cells[1].contour.coordinates[0][1]", "fermé")]
        [TestCase("[[[[5,5],[70,5],[70,70],[5,5]]]],\"type\":\"MultiPolygon\"", "[[[[5,5],[70,5],[70,70],[5,5]]]],\"type\":\"Polygon\"", "cells[1].lieux[1].contour.type", "MultiPolygon")]
        [TestCase("[[[[6,6],[80,6],[80,80],[6,6]]]],\"type\":\"MultiPolygon\"", "[[[[6,6],[80,6],[80,80],[6,6]]]],\"type\":\"Polygon\"", "cells[1].lieux[2].contour.type", "MultiPolygon")]
        [TestCase("{\"contour\":{\"coordinates\":[[[[2,2],[60,2],[60,60],[2,2]]]],\"type\":\"MultiPolygon\"},\"rang\":1}", "{\"rang\":1}", "clé absente : cells[0].lieux[1].contour", "clé absente")]
        [TestCase("[[1,1],[50,1],[50,50],[1,1]]", "[[1,1],[50,1],[50,50],[1,2]]", "cells[0].lieux[0].contour.coordinates[0][0]", "fermé")]
        [TestCase("[[2,2],[60,2],[60,60],[2,2]]", "[[2,2],[60,2],[2,2]]", "cells[0].lieux[1].contour.coordinates[0][0]", "au moins 4 éléments")]
        [TestCase("[[4,4],[8,4],[8,8],[4,4]]", "[[4,4],[8,4,1],[8,8],[4,4]]", "cells[1].lieux[0].contour.coordinates[1][0][1]", "exactement 2 nombres")]
        [TestCase("[[3,3],[40,3],[40,40],[3,3]]", "[[3,3],[\"40\",3],[40,40],[3,3]]", "cells[1].lieux[0].contour.coordinates[0][0][1]", "un nombre attendu")]
        [TestCase("\"coordinates\":[[[[5,5]", "\"coordinates\":[[],[[[5,5]", "cells[1].lieux[1].contour.coordinates[0]", "au moins 1 élément")]
        [TestCase("[[[4,4],[8,4],[8,8],[4,4]]]],\"type\":\"MultiPolygon\"},\"rang\":0}", "[[[4,4],[8,4],[8,8],[4,4]]]],\"type\":\"MultiPolygon\"}}", "clé absente : cells[1].lieux[0].rang", "clé absente")]
        [TestCase("\"type\":\"MultiPolygon\"},\"rang\":2}", "\"type\":\"MultiPolygon\"},\"rang\":3}", "cells[1].lieux[2].rang", "2 attendu")]
        [TestCase("[[[[1,1],[50,1],[50,50],[1,1]]]],\"type\":\"MultiPolygon\"},\"rang\":0}", "[[[[1,1],[50,1],[50,50],[1,1]]]],\"type\":\"MultiPolygon\"},\"rang\":1}", "cells[0].lieux[0].rang", "0 attendu")]
        [TestCase("\"rang\":1}]},{\"cell_id\":20", "\"rang\":0}]},{\"cell_id\":20", "cells[0].lieux[1].rang", "1 attendu")]
        [TestCase("\"type\":\"MultiPolygon\"},\"rang\":2}", "\"type\":\"MultiPolygon\"},\"rang\":-1}", "cells[1].lieux[2].rang", "un entier ≥ 0")]
        [TestCase("\"type\":\"MultiPolygon\"},\"rang\":2}", "\"type\":\"MultiPolygon\"},\"rang\":1.5}", "cells[1].lieux[2].rang", "un entier")]
        [TestCase("\"type\":\"MultiPolygon\"},\"rang\":2}", "\"type\":\"MultiPolygon\"},\"rang\":\"2\"}", "cells[1].lieux[2].rang", "un nombre attendu")]
        [TestCase("\"lieux\":[{\"contour\":{\"coordinates\":[[[[3,3]", "\"lieu\":[{\"contour\":{\"coordinates\":[[[[3,3]", "clé absente : cells[1].lieux", "clé absente")]
        [TestCase("\"lieux\":[{\"contour\":{\"coordinates\":[[[[3,3]", "\"lieux\":null,\"autre\":[{\"contour\":{\"coordinates\":[[[[3,3]", "cells[1].lieux", "un tableau attendu")]
        public void DesFormesFautivesSontRefuseesEnNommantLeurChemin(string ancien, string nouveau, string chemin, string precision) =>
            Absente(Lire(RemplacerUneFois(FORMES, ancien, nouveau)), chemin, precision);

        [Test]
        public void DesFormesSansCelluleSontRefusees()
        {
            Absente(Lire("{\"cells\":[],\"crs\":\"EPSG:3035\",\"version\":\"world-1400-v1\"}"), "cells", "au moins 1 élément");
        }

        [Test]
        public void UneCelluleSansLieuEstRefusee()
        {
            int debut = FORMES.IndexOf("\"lieux\":[", StringComparison.Ordinal), fin = FORMES.IndexOf("]},{\"cell_id\":20", StringComparison.Ordinal);
            string sansLieu = FORMES.Substring(0, debut) + "\"lieux\":[" + FORMES.Substring(fin);
            Assert.IsTrue(debut >= 0 && fin > debut && sansLieu != FORMES && !sansLieu.Contains("[[[[1,1]") && !sansLieu.Contains("[[[[2,2]"));

            Absente(Lire(sansLieu), "cells[0].lieux", "au moins 1 élément");
        }

        [Test]
        public void DesFormesNeSeFabriquentNiSansListeNiSansCauseNiSansContour()
        {
            var points = new[] { new PointCarte(0, 0), new PointCarte(1, 0), new PointCarte(1, 1), new PointCarte(0, 0) };
            var polygones = new[] { new PolygoneDeCarte(points, new IList<PointCarte>[0]) };
            var lieu = new FormeDeLieu(0, polygones);
            var cellule = new FormeDeCellule(7, polygones, new[] { lieu });
            Assert.Throws<ArgumentNullException>(() => new FormeDeLieu(0, null));
            Assert.Throws<ArgumentNullException>(() => new FormeDeCellule(7, null, new[] { lieu }));
            Assert.Throws<ArgumentNullException>(() => new FormeDeCellule(7, polygones, null));
            Assert.Throws<ArgumentNullException>(() => new FormesLues("v", null));
            Assert.Throws<ArgumentException>(() => LectureFormes.Absent(""));
            Assert.Throws<ArgumentNullException>(() => LectureFormes.De(null));
            FormesLues formes = new FormesLues(null, new[] { cellule });
            Assert.AreSame(cellule, formes.De(7));
            Assert.IsNull(formes.De(8));
            Assert.IsTrue(LectureFormes.De(formes).Presente && LectureFormes.De(formes).Absence == null);
        }
    }
}
