using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using NUnit.Framework;
using UnityEngine;

namespace Forge.Pont.Tests {
    // Lot #625 — un repère par terre de départ servie, sur le siège que `/maison` donne. Le faux service sert la carte et les départs de
    // la graine 0, et pour chaque maison une fiche écrite ici d'après les sièges mesurés (graine 0, tick 3), remplaçable ; il note chaque requête.
    public sealed class ReperesDeDepartTests {
        private const int ATTENTE_MS = 30000, DELAI_MAX_PAS_MS = 100, LENTEUR_MS = 2000; private const string MOREE = "Despotat de Morée", RACINE = "Repères des terres de départ";
        private static readonly (long id, string maison, long cell, string siege, double x, double y)[] SIEGES = {
            (1, "Bar", 10430, "Bar-le-Duc", 3965409.11, 2862646.57), (2, "Wurtemberg", 10465, "Stuttgart", 4260932.34, 2851742.83),
            (3, "Paléologue", 10340, "Mistra", 5424441.58, 1644956.82), (4, "Branković", 10334, "Vučitrn", 5217097.38, 2256208.68),
            (5, "Evrenosoğulları", 10337, "Giannitsa", 5367717.15, 2051967.94), (6, "Banou Mozni", 10103, "Biskra", 3926430.32, 1322273.47) };
        private int port; private volatile int statutDeparts, lenteurDeparts; private HttpListener ecoute; private Thread fil; private readonly List<string> recues = new List<string>();
        private readonly ConcurrentDictionary<string, (int statut, string corps)> maisons = new ConcurrentDictionary<string, (int, string)>();
        private GameObject objet; private CarteDessinee carte; private ReperesDeDepart reperes;
        private static byte[] Fixture(string nom) => File.ReadAllBytes(Application.dataPath + "/ForgeLocal3D/Pont/Tests/" + nom);
        [SetUp] public void PortLibre() {
            var sonde = new TcpListener(IPAddress.Loopback, 0); sonde.Start(); port = ((IPEndPoint)sonde.LocalEndpoint).Port; sonde.Stop();
            statutDeparts = 200; lenteurDeparts = 0; lock (recues) recues.Clear(); maisons.Clear(); foreach (var s in SIEGES) maisons["/maison?id=seigneurie-" + s.id] = (200, Fiche(s));
        }
        [TearDown] public void Fermer() { reperes?.Arreter(); carte?.Arreter(); if (objet != null) UnityEngine.Object.DestroyImmediate(objet); ecoute?.Close(); fil?.Join(TimeSpan.FromSeconds(5)); (ecoute, fil) = (null, null); }
        private static string Fiche((long id, string maison, long cell, string siege, double x, double y) s) =>
            "{\"id\":\"seigneurie-" + s.id + "\",\"nom\":\"" + s.maison + "\",\"siege\":{\"cell_id\":" + s.cell + ",\"rang\":0,\"nom\":\"" + s.siege + "\",\"point\":{\"x_m\":"
            + s.x.ToString("R", CultureInfo.InvariantCulture) + ",\"y_m\":" + s.y.ToString("R", CultureInfo.InvariantCulture) + "}},\"lieux\":["
            + string.Join(",", Enumerable.Range(0, 4).Select(r => "{\"cell_id\":" + s.cell + ",\"rang\":" + r + "}")) + "],\"absents\":{}}";
        private void Servir() {
            byte[] carteServie = Fixture("carte-graine0.json"), departsServis = Fixture("departs-graine0-tick3.json");
            var auditeur = ecoute = new HttpListener(); auditeur.Prefixes.Add("http://127.0.0.1:" + port + "/"); auditeur.Start();
            (fil = new Thread(() => {
                try { while (true) {
                    HttpListenerContext ctx = auditeur.GetContext(); string ici = ctx.Request.Url.PathAndQuery; lock (recues) recues.Add(ici); if (ici == "/departs") Thread.Sleep(lenteurDeparts);
                    var (statut, corps) = ici == "/carte" ? (200, carteServie) : ici == "/departs" ? (statutDeparts, statutDeparts == 200 ? departsServis : Encoding.UTF8.GetBytes("{\"erreur\":\"panne\"}"))
                        : maisons.TryGetValue(ici, out var m) ? (m.statut, Encoding.UTF8.GetBytes(m.corps)) : (404, Encoding.UTF8.GetBytes("{\"erreur\":\"maison inconnue\"}"));
                    ctx.Response.StatusCode = statut; ctx.Response.Close(corps, true);
                } } catch (Exception) { }
            }) { IsBackground = true }).Start();
        }
        private int Recues(string chemin = null) { lock (recues) return recues.Count(r => chemin == null || r == chemin); }
        // Ce que le service sert, lu par les clients du pont avant de poser les composants ; les requêtes repartent de zéro.
        private IReadOnlyList<FicheDeDepart> Lues(out PointCarte origine) {
            LectureCarte lue; Lecture<DepartsLus> departs;
            using (var c = new ClientCarte(port, ClientCarte.DelaiMinimal)) lue = c.Lire(); using (var d = new ClientDeparts(port, ClientDeparts.DelaiMinimal)) departs = d.Lire();
            Assert.IsTrue(lue.Presente && departs.Presente, lue.Absence + " " + departs.Absence);
            origine = MaillageDeCarte.Mailler(lue.Carte).Origine; lock (recues) recues.Clear(); return departs.Donnees.Fiches;
        }
        private void Poser() { objet = new GameObject("Carte du test"); carte = objet.AddComponent<CarteDessinee>(); carte.port = port; carte.Demarrer(); reperes = objet.AddComponent<ReperesDeDepart>(); reperes.port = port; reperes.Demarrer(); }
        // Des pas au même instant jusqu'à la carte posée et la lecture des repères finie, puis un pas qui l'applique.
        private void Avancer(double t) {
            var montre = Stopwatch.StartNew(); do { carte.Pas(t); reperes.Pas(t); Thread.Sleep(10); } while ((carte.CellulesServies < 0 || carte.LectureEnVol || reperes.LectureEnVol) && montre.ElapsedMilliseconds < ATTENTE_MS);
            Assert.IsFalse(reperes.LectureEnVol, "la lecture des repères n'a pas fini"); reperes.Pas(t);
        }
        private int Nommes(string nom) => objet.GetComponentsInChildren<Transform>(true).Count(t => t.name == nom);
        private long? Sous(double x, double z) => carte.CelluleSous(objet.transform.TransformPoint(new Vector3((float)x, 0, (float)z)))?.CellId;
        private static bool Egal(Vector3 a, Vector3 b) => a.x == b.x && a.y == b.y && a.z == b.z;
        [Test] public void Six_reperes_chacun_dans_la_cellule_de_sa_terre() {
            Servir(); IReadOnlyList<FicheDeDepart> fiches = Lues(out PointCarte o); Poser(); objet.transform.position = new Vector3(1000, 50, -2000); Avancer(1); var cellules = new HashSet<long>();
            Assert.IsTrue(fiches.Count == 6 && reperes.ReperesPoses == fiches.Count && ReperesDeDepart.HAUTEUR_REPERE > CarteDessinee.HAUTEUR_NOM, reperes.ReperesPoses + " repères pour " + fiches.Count + " fiches : " + reperes.TexteAffiche);
            foreach (FicheDeDepart f in fiches) {
                int i = Array.FindIndex(SIEGES, x => x.id == f.Id); var s = SIEGES[i]; var suivant = SIEGES[(i + 1) % SIEGES.Length];
                Transform r = objet.transform.Find(RACINE + "/Repère " + f.Nom); Assert.IsTrue(r != null && Nommes("Repère " + f.Nom) == 1, "pas un seul repère pour " + f.Nom);
                Vector3 attendu = new Vector3((float)((s.x - o.X) / 1000), ReperesDeDepart.HAUTEUR_REPERE, (float)((s.y - o.Y) / 1000));
                Assert.IsTrue(Egal(r.localPosition, attendu), f.Nom + " en " + r.localPosition.ToString("R") + ", attendu " + attendu.ToString("R"));
                Assert.AreEqual(f.CellId, carte.CelluleSous(r.position)?.CellId, f.Nom + " hors de la cellule de sa terre");
                Assert.AreEqual((Color32)ReperesDeDepart.COULEUR_REPERE, (Color32)r.Find("Disque").GetComponent<MeshRenderer>().sharedMaterial.color, f.Nom);
                // Contre-épreuves : le siège suivant, ce siège sans origine ou pris en (lat, lon), ne sont pas dans cette cellule.
                Assert.AreNotEqual(f.CellId, Sous((suivant.x - o.X) / 1000, (suivant.y - o.Y) / 1000), f.Nom + " : le siège suivant tombe dans sa cellule");
                Assert.AreNotEqual(f.CellId, Sous(s.x / 1000, s.y / 1000), f.Nom + " : sans origine, encore dans sa cellule");
                Assert.AreNotEqual(f.CellId, Sous(f.Siege.Lat, f.Siege.Lon), f.Nom + " : en (lat, lon), encore dans sa cellule");
                cellules.Add(f.CellId); Assert.AreEqual(1, Recues("/maison?id=seigneurie-" + f.Id), f.Nom);
            }
            MeshRenderer[] posees = objet.transform.Find("Cellules de la carte").GetComponentsInChildren<MeshRenderer>();
            Assert.IsTrue(cellules.Count == 6 && posees.Length == 596 && posees.All(m => m.sharedMaterial.color != ReperesDeDepart.COULEUR_REPERE), "des terres partagent une cellule, ou une cellule a la couleur des repères");
            Assert.IsTrue(Recues("/departs") == 1 && Recues() == 2 + fiches.Count && reperes.TexteAffiche == null, Recues() + " requêtes ; " + reperes.TexteAffiche);
            for (int i = 1; i <= 20; i++) { carte.Pas(1 + 3 * i); reperes.Pas(1 + 3 * i); Assert.IsFalse(reperes.LectureEnVol, "une lecture repart à " + (1 + 3 * i) + " s"); }
            Thread.Sleep(100); Assert.IsTrue(Recues() == 2 + fiches.Count && reperes.ReperesPoses == 6, Recues() + " requêtes après vingt pas");
        }
        [TestCase("statut 404")] [TestCase("siège hors carte, ")]
        public void Une_maison_absente_se_dit_sans_repere(string cause) {
            const string raison = "siège sans cellule sur la carte servie", demande = "/maison?id=seigneurie-3"; string vraie = maisons[demande].corps;
            maisons[demande] = cause == "statut 404" ? (404, "{\"erreur\":\"maison inconnue\"}")
                : (200, "{\"id\":\"seigneurie-3\",\"nom\":\"Paléologue\",\"siege\":{\"cell_id\":null,\"rang\":null,\"nom\":\"Mistra\",\"point\":null},\"lieux\":[],\"absents\":{\"siege\":\"" + raison + "\"}}");
            Servir(); Lues(out _); Poser(); Avancer(1);
            Assert.IsTrue(reperes.ReperesPoses == 5 && Nommes("Repère " + MOREE) == 0, reperes.ReperesPoses + " repères");
            StringAssert.StartsWith(ReperesDeDepart.MESSAGE_ABSENCE + "\n" + MOREE + " : ", reperes.TexteAffiche);
            StringAssert.Contains(cause == "statut 404" ? "maison : statut 404" : cause + raison, reperes.TexteAffiche);
            Transform racine = objet.transform.Find(RACINE); Transform[] avant = Enumerable.Range(0, 5).Select(racine.GetChild).ToArray();
            maisons[demande] = (200, vraie); reperes.Pas(2); Assert.IsFalse(reperes.LectureEnVol, "une lecture repart 1 s après l'absence");
            Avancer(1 + ReperesDeDepart.PERIODE_RELECTURE_S);
            Assert.IsTrue(reperes.ReperesPoses == 6 && racine.childCount == 6 && Nommes("Repère " + MOREE) == 1 && reperes.TexteAffiche == null, reperes.ReperesPoses + " repères ; " + reperes.TexteAffiche);
            for (int i = 0; i < 5; i++) Assert.AreSame(avant[i], racine.GetChild(i), "un repère déjà posé a été refait");
            Assert.IsTrue(Recues("/departs") == 2 && Recues(demande) == 2 && Recues("/maison?id=seigneurie-1") == 1, Recues() + " requêtes");
        }
        [Test] public void Sans_departs_aucun_repere_et_aucune_maison_demandee() {
            Servir(); Lues(out _); statutDeparts = 500; Poser(); Avancer(1);
            Assert.IsTrue(reperes.ReperesPoses == 0 && objet.transform.Find(RACINE) == null && Recues("/departs") == 1 && Recues() == 2, reperes.ReperesPoses + " repères, " + Recues() + " requêtes");
            StringAssert.StartsWith(ReperesDeDepart.MESSAGE_ABSENCE + "\ndeparts : statut 500", reperes.TexteAffiche);
        }
        [Test] public void Le_pas_n_attend_pas_les_departs() {
            Servir(); Lues(out _); lenteurDeparts = LENTEUR_MS; Poser();
            reperes.Pas(1); Assert.IsFalse(reperes.LectureEnVol, "une lecture part avant que la carte soit posée");
            var attente = Stopwatch.StartNew(); while (carte.CellulesServies < 0 && attente.ElapsedMilliseconds < ATTENTE_MS) { carte.Pas(1); Thread.Sleep(10); }
            Assert.IsTrue(carte.CellulesServies > 0 && Recues("/departs") == 0, carte.TexteAffiche);
            var montre = Stopwatch.StartNew(); reperes.Pas(1); montre.Stop(); Assert.Less(montre.ElapsedMilliseconds, DELAI_MAX_PAS_MS, "le pas a attendu le service"); Assert.IsTrue(reperes.LectureEnVol);
        }
    }
}
