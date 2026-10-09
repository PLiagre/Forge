using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Pont.Tests {
    // Lot #547 — la carte servie se pose cellule par cellule, à la couleur de sa puissance ; sans carte, le
    // message et rien d'autre. L'attendu vient de la fixture, lue par ClientCarte puis Mailler.
    public sealed class CarteDessineeTests {
        private const int DELAI_MAX_PAS_MS = 100, ATTENTE_LECTURE_MS = 20000, LENTEUR_MS = 2000;
        private int port, requetes; private volatile string chemin;
        private HttpListener ecoute; private Thread fil; private GameObject objet; private CarteDessinee carte;
        private static byte[] Fixture => File.ReadAllBytes(Application.dataPath + "/ForgeLocal3D/Pont/Tests/carte-graine0.json");
        [SetUp] public void PortLibre() {
            var sonde = new TcpListener(IPAddress.Loopback, 0);
            sonde.Start(); port = ((IPEndPoint)sonde.LocalEndpoint).Port; sonde.Stop(); requetes = 0; chemin = null;
        }
        [TearDown] public void Fermer() {
            if (carte != null) carte.Arreter(); if (objet != null) UnityEngine.Object.DestroyImmediate(objet);
            ecoute?.Close(); ecoute = null; fil?.Join(TimeSpan.FromSeconds(5)); fil = null;
        }
        // Rend toujours la même réponse, `lenteur` ms après avoir compté la requête.
        private void Servir(int lenteur, int statut, byte[] octets) {
            ecoute = new HttpListener(); ecoute.Prefixes.Add("http://127.0.0.1:" + port + "/"); ecoute.Start();
            HttpListener auditeur = ecoute;
            fil = new Thread(() => {
                try { while (true) {
                    HttpListenerContext ctx = auditeur.GetContext();
                    chemin = ctx.Request.Url.PathAndQuery; Interlocked.Increment(ref requetes); Thread.Sleep(lenteur);
                    ctx.Response.StatusCode = statut; ctx.Response.ContentLength64 = octets.Length;
                    ctx.Response.OutputStream.Write(octets, 0, octets.Length); ctx.Response.Close();
                } } catch (Exception) { }
            }) { IsBackground = true };
            fil.Start();
        }
        // L'attendu, lu au faux service avant de poser le composant ; le compteur repart ensuite de zéro.
        private CarteMaillee Attendue(out int servies) {
            LectureCarte lecture; using (var client = new ClientCarte(port, ClientCarte.DelaiMinimal)) lecture = client.Lire();
            Assert.IsTrue(lecture.Presente, lecture.Absence);
            Interlocked.Exchange(ref requetes, 0); servies = lecture.Carte.Cellules.Count;
            return MaillageDeCarte.Mailler(lecture.Carte);
        }
        private void Poser() { objet = new GameObject("Carte du test"); carte = objet.AddComponent<CarteDessinee>(); carte.port = port; carte.Demarrer(); }
        private int CellulesSousLaCarte => objet.GetComponentsInChildren<MeshFilter>(true).Length; // toutes racines confondues : une double pose se voit
        // Une lecture complète : le pas la lance, elle finit hors du fil, un pas au même instant l'applique.
        private void Lire(double instant) {
            carte.Pas(instant); var montre = Stopwatch.StartNew();
            while (carte.LectureEnVol && montre.ElapsedMilliseconds < ATTENTE_LECTURE_MS) Thread.Sleep(10);
            Assert.IsFalse(carte.LectureEnVol, "la lecture n'a pas fini"); carte.Pas(instant);
        }
        private void Absence(string cause) {
            string[] l = carte.TexteAffiche.Split('\n'); Text texte = objet.GetComponentInChildren<Text>();
            Assert.IsTrue(carte.CellulesPosees == 0 && carte.CellulesServies == -1, carte.TexteAffiche);
            Assert.AreEqual(CarteDessinee.MESSAGE_ABSENCE, l[0]); StringAssert.Contains(cause, l[1]);
            Assert.IsTrue(texte != null && texte.gameObject.activeInHierarchy && texte.text == carte.TexteAffiche);
        }
        [Test] public void La_carte_servie_pose_une_cellule_par_cellule_servie() {
            Servir(0, 200, Fixture); CarteMaillee attendue = Attendue(out int servies); Poser();
            Lire(1);
            Assert.IsTrue(Volatile.Read(ref requetes) == 1 && chemin == "/carte", requetes + " requêtes, " + chemin);
            Assert.IsTrue(servies == 596 && attendue.Cellules.Count == servies && carte.CellulesServies == servies && carte.CellulesPosees == servies && CellulesSousLaCarte == servies, CellulesSousLaCarte + " posées");
            Transform racine = objet.transform.Find("Cellules de la carte");
            var couleurs = new HashSet<Color>(); var materiaux = new HashSet<Material>(); int ecarts = 0;
            for (int i = 0; i < servies; i++) {
                MaillageDeCellule c = attendue.Cellules[i]; Transform t = racine.GetChild(i); Assert.AreEqual("Cellule " + c.CellId, t.name);
                Mesh m = t.GetComponent<MeshFilter>().sharedMesh; Vector3[] s = m.vertices; Material mat = t.GetComponent<MeshRenderer>().sharedMaterial;
                Assert.AreEqual(c.Maillage.Sommets.Count, s.Length, t.name); CollectionAssert.AreEqual(c.Maillage.Triangles, m.triangles, t.name);
                for (int k = 0; k < s.Length; k++) if (!(s[k].x == c.Maillage.Sommets[k].x && s[k].y == c.Maillage.Sommets[k].y && s[k].z == c.Maillage.Sommets[k].z)) ecarts++;
                Assert.AreEqual((Color32)c.Couleur, (Color32)mat.color, t.name); couleurs.Add(c.Couleur); materiaux.Add(mat);
            }
            Assert.AreEqual(0, ecarts, "sommets différents du maillage attendu");
            Assert.IsTrue(couleurs.Count == 40 && materiaux.Count == couleurs.Count, materiaux.Count + " matériaux, " + couleurs.Count + " couleurs");
            Assert.IsTrue(carte.TexteAffiche == "" && !objet.GetComponentInChildren<Text>(true).gameObject.activeSelf);
            for (int i = 1; i <= 20; i++) { carte.Pas(1 + 10 * i); Assert.IsFalse(carte.LectureEnVol); }
            Assert.IsTrue(Volatile.Read(ref requetes) == 1 && carte.CellulesPosees == servies && CellulesSousLaCarte == servies, CellulesSousLaCarte + " cellules");
        }
        [Test] public void Sans_service_aucune_cellule_et_le_message() {
            Poser(); Lire(1);
            Absence("service absent sur 127.0.0.1:" + port);
            Servir(0, 200, Fixture); Attendue(out int servies);
            carte.Pas(2); Assert.IsTrue(!carte.LectureEnVol && Volatile.Read(ref requetes) == 0, "une lecture est partie 1 s après l'absence");
            Lire(3.5);
            Assert.IsTrue(Volatile.Read(ref requetes) == 1 && servies == 596 && carte.CellulesPosees == servies && carte.CellulesServies == servies, carte.TexteAffiche);
            Assert.IsTrue(carte.TexteAffiche == "" && objet.GetComponentInChildren<Text>() == null);
        }
        [TestCase(404, "statut 404")] [TestCase(200, "JSON invalide")]
        public void Une_reponse_illisible_ne_pose_rien(int statut, string cause) {
            byte[] fixture = Fixture, moitie = new byte[fixture.Length / 2]; Array.Copy(fixture, moitie, moitie.Length);
            Servir(0, statut, statut == 200 ? moitie : System.Text.Encoding.UTF8.GetBytes("{\"erreur\":\"introuvable\"}"));
            Poser(); Lire(1); Absence(cause);
        }
        [Test] public void Le_pas_ne_bloque_pas_pendant_la_lecture() {
            Servir(LENTEUR_MS, 200, Fixture); Poser();
            var montre = Stopwatch.StartNew(); carte.Pas(1); montre.Stop();
            Assert.Less(montre.ElapsedMilliseconds, DELAI_MAX_PAS_MS, "le pas a attendu le service");
            Assert.IsTrue(carte.LectureEnVol);
        }
        // Lot #548 — contours, noms et caméra, avec ou sans caméra donnée. L'attendu : la carte lue par ClientCarte, l'origine de Mailler, et la conversion écrite ici.
        private CarteLue Lue(out PointCarte origine) {
            LectureCarte lecture; using (var client = new ClientCarte(port, ClientCarte.DelaiMinimal)) lecture = client.Lire();
            Assert.IsTrue(lecture.Presente, lecture.Absence); Interlocked.Exchange(ref requetes, 0); origine = MaillageDeCarte.Mailler(lecture.Carte).Origine; return lecture.Carte;
        }
        private static Vector3 Converti(PointCarte p, PointCarte o, float y) => new Vector3((float)((p.X - o.X) / 1000), y, (float)((p.Y - o.Y) / 1000));
        private static bool Egal(Vector3 a, Vector3 b) => a.x == b.x && a.y == b.y && a.z == b.z; // `==` de Vector3 tolère un écart : on compare composante par composante
        private int Nommes(string nom) { int n = 0; foreach (Transform t in objet.GetComponentsInChildren<Transform>(true)) if (t.name == nom) n++; return n; }
        private void Contours(CarteLue lue, PointCarte o) {
            LineRenderer[] traits = objet.transform.Find("Contours de la carte").GetComponentsInChildren<LineRenderer>(true);
            int i = 0, trous = 0, points = 0, ecarts = 0;
            foreach (CelluleDeCarte c in lue.Cellules) { int rang = 0;
                foreach (PolygoneDeCarte p in c.Contour) {
                    var anneaux = new List<IReadOnlyList<PointCarte>> { p.Exterieur }; anneaux.AddRange(p.Trous); trous += p.Trous.Count;
                    foreach (IReadOnlyList<PointCarte> a in anneaux) {
                        Assert.Less(i, traits.Length, "moins de contours que d'anneaux"); LineRenderer t = traits[i++]; Assert.AreEqual("Contour " + c.CellId + "." + rang++, t.name);
                        Assert.IsTrue(!t.useWorldSpace && !t.loop && t.positionCount == a.Count, t.name + " : " + t.positionCount + " positions pour " + a.Count + " points");
                        points += a.Count; for (int k = 0; k < a.Count; k++) if (!Egal(t.GetPosition(k), Converti(a[k], o, CarteDessinee.HAUTEUR_CONTOUR))) ecarts++;
                    }
                }
            }
            Assert.IsTrue(i == traits.Length && i == 746 && trous == 71 && points == 19789, i + " anneaux dont " + trous + " trous, " + points + " points, " + traits.Length + " contours");
            Assert.AreEqual(0, ecarts, "positions différentes des points convertis");
        }
        [Test] public void Chaque_anneau_servi_a_son_contour() { Servir(0, 200, Fixture); CarteLue lue = Lue(out PointCarte o); Poser(); Lire(1); Contours(lue, o);
            Assert.IsTrue(carte.CellulesPosees == 596 && CellulesSousLaCarte == carte.CellulesPosees, CellulesSousLaCarte + " MeshFilter sous la carte");
        }
        private void Noms(CarteLue lue, PointCarte o) {
            TextMesh[] noms = objet.transform.Find("Villes de la carte").GetComponentsInChildren<TextMesh>(true);
            var vus = new HashSet<string>(); int i = 0;
            foreach (CelluleDeCarte c in lue.Cellules)
                foreach (VilleDeCarte v in c.Villes) {
                    Assert.Less(i, noms.Length, "moins de noms que de villes"); TextMesh n = noms[i++]; vus.Add(v.Nom);
                    Assert.IsTrue(n.text == v.Nom && n.name == "Ville " + v.Nom, n.name + " pour " + v.Nom);
                    Vector3 attendu = Converti(v.Position, o, CarteDessinee.HAUTEUR_NOM); Assert.IsTrue(Egal(n.transform.localPosition, attendu),v.Nom + " en " + n.transform.localPosition.ToString("R") + ", attendu " + attendu.ToString("R"));
                    Assert.IsTrue(n.transform.localRotation == Quaternion.Euler(90, 0, 0), v.Nom + " tourné de " + n.transform.localEulerAngles);
                }
            Assert.IsTrue(i == noms.Length && i == 57 && vus.Count == i && vus.Contains("Constantinople"), i + " villes, " + noms.Length + " noms, " + vus.Count + " distincts");
        }
        [Test] public void Chaque_ville_servie_a_son_nom() { Servir(0, 200, Fixture); CarteLue lue = Lue(out PointCarte o); Poser(); Lire(1); Noms(lue, o);
            Assert.IsNull(objet.GetComponentInChildren<Text>(), "un Text d'UI actif sous la carte");
        }
        [Test] public void La_camera_cadre_toute_la_carte() {
            Servir(0, 200, Fixture); CarteMaillee attendue = Attendue(out int servies); Poser(); objet.transform.position = new Vector3(1000, 50, -2000); Lire(1);
            Camera cam = carte.camera; Canvas toile = objet.GetComponentInChildren<Canvas>(true);
            Assert.IsTrue(Nommes("Caméra de la carte") == 1 && cam != null && cam.name == "Caméra de la carte" && cam.transform.parent == objet.transform && cam.orthographic, "caméra de la carte absente ou mal faite");
            Assert.IsTrue(toile.renderMode == RenderMode.ScreenSpaceCamera && toile.worldCamera == cam, "la toile n'est pas sur la caméra de la carte");
            float minX = float.MaxValue, minZ = float.MaxValue, maxX = float.MinValue, maxZ = float.MinValue;
            foreach (MaillageDeCellule c in attendue.Cellules) foreach (Vector3 s in c.Maillage.Sommets) { minX = Mathf.Min(minX, s.x); maxX = Mathf.Max(maxX, s.x); minZ = Mathf.Min(minZ, s.z); maxZ = Mathf.Max(maxZ, s.z); }
            var coins = new[] { new Vector3(minX, 0, minZ), new Vector3(maxX, 0, minZ), new Vector3(maxX, 0, maxZ), new Vector3(minX, 0, maxZ) }; // sud-ouest, sud-est, nord-est, nord-ouest
            foreach (float aspect in new[] { 16f / 9f, 4f / 3f, 0.5f }) {
                cam.aspect = aspect; carte.Pas(2); var vus = new Vector3[4];
                for (int k = 0; k < 4; k++) {
                    vus[k] = cam.WorldToViewportPoint(objet.transform.TransformPoint(coins[k]));
                    Assert.IsTrue(vus[k].x >= 0 && vus[k].x <= 1 && vus[k].y >= 0 && vus[k].y <= 1 && vus[k].z >= cam.nearClipPlane && vus[k].z <= cam.farClipPlane, "aspect " + aspect + ", coin " + k + " hors du champ : " + vus[k].ToString("R"));
                }
                float largeur = vus[1].x - vus[0].x, hauteur = vus[3].y - vus[0].y;
                Assert.IsTrue(largeur >= 0.9f || hauteur >= 0.9f, "aspect " + aspect + " : la carte ne couvre que " + largeur + " × " + hauteur + " du champ");
                Assert.Greater(vus[3].y, vus[0].y, "aspect " + aspect + " : le nord n'est pas en haut");
            }
        }
        [Test] public void Sans_carte_ni_contour_ni_nom() {
            Poser(); Lire(1);
            Assert.IsTrue(objet.GetComponentsInChildren<LineRenderer>(true).Length == 0 && objet.GetComponentsInChildren<TextMesh>(true).Length == 0, carte.TexteAffiche);
            Assert.IsTrue(Nommes("Caméra de la carte") == 1 && carte.camera != null && carte.camera.name == "Caméra de la carte", "pas de caméra de la carte sans carte");
        }
        [Test] public void Une_camera_donnee_n_est_pas_cadree() {
            Servir(0, 200, Fixture); CarteLue lue = Lue(out PointCarte o); int servies = lue.Cellules.Count;
            Camera donnee = new GameObject("Caméra donnée du test").AddComponent<Camera>(); Vector3 position = new Vector3(5, 6, 7); Quaternion rotation = Quaternion.Euler(10, 20, 30);
            try {
                donnee.orthographic = false; donnee.transform.SetPositionAndRotation(position, rotation);
                objet = new GameObject("Carte du test"); carte = objet.AddComponent<CarteDessinee>(); carte.port = port; carte.camera = donnee; carte.Demarrer();
                Lire(1); for (int i = 1; i <= 5; i++) carte.Pas(1 + i);
                Assert.IsTrue(carte.CellulesPosees == servies && carte.camera == donnee && Nommes("Caméra de la carte") == 0, carte.CellulesPosees + " cellules, " + Nommes("Caméra de la carte") + " caméra(s) créée(s)");
                Assert.IsTrue(Egal(donnee.transform.position, position) && donnee.transform.rotation == rotation && !donnee.orthographic, "la caméra donnée a été touchée : " + donnee.transform.position + " " + donnee.transform.eulerAngles);
                Contours(lue, o); Noms(lue, o); // avec une caméra donnée aussi, la carte trace ses bords et nomme ses villes
            } finally { UnityEngine.Object.DestroyImmediate(donnee.gameObject); }
        }
    }
}
