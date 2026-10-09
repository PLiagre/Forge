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
    }
}
