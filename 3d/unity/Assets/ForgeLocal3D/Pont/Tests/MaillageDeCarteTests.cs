using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Threading;
using NUnit.Framework;
using UnityEngine;

namespace Forge.Pont.Tests {
    // Lot #542 — la carte servie devient des maillages, trous vides, une couleur stable par puissance.
    public sealed class MaillageDeCarteTests {
        private const string Empreinte = "9b729f9ada67a1e514a8029893a8cb4d04d2dbb91cd33c5ef5fa83d63a024981";
        private static byte[] _octets; private static CarteLue _carte; private static CarteMaillee _maillee; private static string _chemin, _requete;
        [SetUp] public void Preparer() {
            if (_carte != null) return;
            _octets = File.ReadAllBytes(Application.dataPath + "/ForgeLocal3D/Pont/Tests/carte-graine0.json");
            var sonde = new TcpListener(IPAddress.Loopback, 0);
            sonde.Start(); int port = ((IPEndPoint)sonde.LocalEndpoint).Port; sonde.Stop();
            var ecoute = new HttpListener();
            ecoute.Prefixes.Add("http://127.0.0.1:" + port + "/"); ecoute.Start();
            var fil = new Thread(() => {
                try {
                    HttpListenerContext ctx = ecoute.GetContext();
                    _chemin = ctx.Request.Url.AbsolutePath; _requete = ctx.Request.Url.Query;
                    ctx.Response.StatusCode = 200; ctx.Response.ContentLength64 = _octets.Length;
                    ctx.Response.OutputStream.Write(_octets, 0, _octets.Length); ctx.Response.Close();
                } catch (Exception) { }
            }) { IsBackground = true };
            fil.Start();
            try {
                using (var client = new ClientCarte(port, ClientCarte.DelaiMinimal))
                { var lecture = client.Lire(); Assert.IsTrue(lecture.Presente, lecture.Absence); _carte = lecture.Carte; }
            } finally { ecoute.Close(); fil.Join(TimeSpan.FromSeconds(5)); }
            _maillee = MaillageDeCarte.Mailler(_carte);
        }
        // Produit de #541. L'arête n'est gardée que si elle descend, ou si elle file vers l'ouest. Rayon pair-impair sur les mètres servis.
        private static double S(Vector3 p, Vector3 q, double x, double z) => ((double)q.z - p.z) * (x - p.x) - ((double)q.x - p.x) * (z - p.z);
        private static bool Bord(double s, Vector3 p, Vector3 q) => s > 0 || (s == 0 && (q.z < p.z || (q.z == p.z && q.x < p.x)));
        private static int Couverture(IReadOnlyList<Vector3> s, double x, double z) {
            int n = 0; for (int i = 0; i < s.Count; i += 3) if (Bord(S(s[i], s[i + 1], x, z), s[i], s[i + 1]) && Bord(S(s[i + 1], s[i + 2], x, z), s[i + 1], s[i + 2]) && Bord(S(s[i + 2], s[i], x, z), s[i + 2], s[i])) n++; return n;
        }
        private static bool Pair(IReadOnlyList<PointCarte> a, double x, double y) {
            bool dedans = false;
            for (int i = 0; i + 1 < a.Count; i++)
            { double x0 = a[i].X, y0 = a[i].Y, x1 = a[i + 1].X, y1 = a[i + 1].Y; if ((y0 > y) != (y1 > y) && x < x0 + (y - y0) / (y1 - y0) * (x1 - x0)) dedans = !dedans; }
            return dedans;
        }
        private static bool DansPolygone(PolygoneDeCarte p, double x, double y)
        { if (!Pair(p.Exterieur, x, y)) return false; for (int i = 0; i < p.Trous.Count; i++) if (Pair(p.Trous[i], x, y)) return false; return true; }
        private static bool DansCellule(CelluleDeCarte c, double x, double y)
        { for (int i = 0; i < c.Contour.Count; i++) if (DansPolygone(c.Contour[i], x, y)) return true; return false; }
        private static double Distance(double x, double y, PointCarte a, PointCarte b) {
            double dx = b.X - a.X, dy = b.Y - a.Y, l2 = dx * dx + dy * dy, t = l2 == 0 ? 0 : ((x - a.X) * dx + (y - a.Y) * dy) / l2; if (t < 0) t = 0; else if (t > 1) t = 1;
            return Math.Sqrt((a.X + t * dx - x) * (a.X + t * dx - x) + (a.Y + t * dy - y) * (a.Y + t * dy - y));
        }
        private static double Ecart(IReadOnlyList<PointCarte> a, double x, double y)
        { double m = double.PositiveInfinity; for (int i = 0; i + 1 < a.Count; i++) m = Math.Min(m, Distance(x, y, a[i], a[i + 1])); return m; }
        private static double Ecart(CelluleDeCarte c, double x, double y) {
            double m = double.PositiveInfinity;
            foreach (PolygoneDeCarte p in c.Contour) { m = Math.Min(m, Ecart(p.Exterieur, x, y)); foreach (IReadOnlyList<PointCarte> t in p.Trous) m = Math.Min(m, Ecart(t, x, y)); }
            return m;
        }
        private static void Bornes(IEnumerable<PointCarte> points, ref double minX, ref double minY, ref double maxX, ref double maxY)
        { foreach (PointCarte p in points) { if (p.X < minX) minX = p.X; if (p.Y < minY) minY = p.Y; if (p.X > maxX) maxX = p.X; if (p.Y > maxY) maxY = p.Y; } }
        private static void Boite(CelluleDeCarte c, out double minX, out double minY, out double maxX, out double maxY) {
            minX = minY = double.PositiveInfinity; maxX = maxY = double.NegativeInfinity;
            foreach (PolygoneDeCarte p in c.Contour) { Bornes(p.Exterieur, ref minX, ref minY, ref maxX, ref maxY); foreach (IReadOnlyList<PointCarte> t in p.Trous) Bornes(t, ref minX, ref minY, ref maxX, ref maxY); }
        }
        private static PointCarte Centre(CarteLue carte) {
            double minX = double.PositiveInfinity, minY = double.PositiveInfinity, maxX = double.NegativeInfinity, maxY = double.NegativeInfinity;
            foreach (CelluleDeCarte c in carte.Cellules) { Boite(c, out double x0, out double y0, out double x1, out double y1); if (x0 < minX) minX = x0; if (y0 < minY) minY = y0; if (x1 > maxX) maxX = x1; if (y1 > maxY) maxY = y1; }
            return new PointCarte((minX + maxX) / 2.0, (minY + maxY) / 2.0);
        }
        private static bool Meme(Color a, Color b) => a.r == b.r && a.g == b.g && a.b == b.b && a.a == b.a;

        [Test] public void ToutesLesCellules() {
            Assert.AreEqual(464180, _octets.Length);
            using (var sha = SHA256.Create()) Assert.AreEqual(Empreinte, BitConverter.ToString(sha.ComputeHash(_octets)).Replace("-", "").ToLowerInvariant());
            Assert.AreEqual("/carte", _chemin); Assert.AreEqual("", _requete);
            int polygones = 0, trous = 0, sans = 0; var numeros = new HashSet<long>();
            foreach (CelluleDeCarte c in _carte.Cellules) { if (c.Puissance == null) sans++; else numeros.Add(c.Puissance.Id); foreach (PolygoneDeCarte p in c.Contour) { polygones++; trous += p.Trous.Count; } }
            Assert.IsTrue(_carte.Cellules.Count == 596 && polygones == 675 && trous == 71 && numeros.Count == 39 && sans == 31);
            PointCarte centre = Centre(_carte);
            Assert.IsTrue(centre.X == 4549691.5 && centre.Y == 2747267.5 && _maillee.Origine.X == centre.X && _maillee.Origine.Y == centre.Y);
            Assert.IsInstanceOf<ReadOnlyCollection<MaillageDeCellule>>(_maillee.Cellules); Assert.IsInstanceOf<ReadOnlyCollection<Vector3>>(_maillee.Cellules[0].Maillage.Sommets);
            Assert.AreEqual(_carte.Cellules.Count, _maillee.Cellules.Count); // ni omission ni doublon en fin de liste
            for (int i = 0; i < _carte.Cellules.Count; i++) {
                CelluleDeCarte c = _carte.Cellules[i]; MaillageDePolygone m = _maillee.Cellules[i].Maillage;
                Assert.AreEqual(c.CellId, _maillee.Cellules[i].CellId);
                var attendus = new List<Vector3>();
                foreach (PolygoneDeCarte p in c.Contour) attendus.AddRange(TriangulationDeCarte.Trianguler(p, centre).Sommets);
                Assert.IsTrue(m.Sommets.Count == attendus.Count && m.Sommets.Count >= 1 && m.Sommets.Count <= 65534 && m.Sommets.Count % 3 == 0 && m.Triangles.Count == m.Sommets.Count, c.CellId.ToString());
                for (int k = 0; k < m.Sommets.Count; k++)
                { Vector3 s = m.Sommets[k], a = attendus[k]; Assert.IsTrue(m.Triangles[k] == k && s.y == 0f && s.x == a.x && s.y == a.y && s.z == a.z && !float.IsNaN(s.x) && !float.IsInfinity(s.x) && !float.IsNaN(s.z) && !float.IsInfinity(s.z), c.CellId.ToString()); }
                for (int k = 0; k < m.Sommets.Count; k += 3) Assert.Greater(S(m.Sommets[k], m.Sommets[k + 1], m.Sommets[k + 2].x, m.Sommets[k + 2].z), 0, c.CellId.ToString());
            }
        }

        [Test] public void LaGrilleRespecteLesContours() {
            int controles = 0, dedans = 0, dehors = 0, ecartes = 0; var ecarts = new List<string>();
            for (int c = 0; c < _carte.Cellules.Count; c++) {
                CelluleDeCarte cellule = _carte.Cellules[c]; IReadOnlyList<Vector3> sommets = _maillee.Cellules[c].Maillage.Sommets;
                Boite(cellule, out double minX, out double minY, out double maxX, out double maxY); int locaux = 0;
                for (int i = 0; i < 16; i++) for (int j = 0; j < 16; j++) {
                    double x = minX + (i + 0.5) * (maxX - minX) / 16, y = minY + (j + 0.5) * (maxY - minY) / 16;
                    if (Ecart(cellule, x, y) < 10) { ecartes++; continue; }
                    locaux++; controles++; bool interieur = DansCellule(cellule, x, y); if (interieur) dedans++; else dehors++;
                    int compte = Couverture(sommets, (x - _maillee.Origine.X) / 1000.0, (y - _maillee.Origine.Y) / 1000.0);
                    if (compte != (interieur ? 1 : 0) && ecarts.Count < 8) ecarts.Add(cellule.CellId + " (" + x + " ; " + y + ") couvert " + compte + " fois");
                }
                Assert.Greater(locaux, 0, cellule.CellId.ToString());
            }
            TestContext.WriteLine(controles + " contrôlés, " + dedans + " dedans, " + dehors + " dehors, " + ecartes + " écartés sur " + _carte.Cellules.Count * 256);
            Assert.IsTrue(controles == 152259 && dedans == 89935 && dehors == 62324 && ecartes == 317 && dedans > 0 && dehors > 0);
            Assert.That(ecarts, Is.Empty, string.Join(" | ", ecarts));
        }

        [Test] public void ChaqueTrouResteVide() {
            int trous = 0; bool etroit = false;
            for (int c = 0; c < _carte.Cellules.Count; c++) foreach (PolygoneDeCarte polygone in _carte.Cellules[c].Contour) foreach (IReadOnlyList<PointCarte> trou in polygone.Trous) {
                trous++; var niveaux = new List<double>(); foreach (PointCarte p in trou) if (!niveaux.Contains(p.Y)) niveaux.Add(p.Y);
                niveaux.Sort(); double meilleur = -1, tx = 0, ty = 0;
                for (int k = 0; k + 1 < niveaux.Count; k++) {
                    double y = (niveaux[k] + niveaux[k + 1]) / 2.0; var xs = new List<double>();
                    for (int i = 0; i + 1 < trou.Count; i++) { double x0 = trou[i].X, y0 = trou[i].Y, x1 = trou[i + 1].X, y1 = trou[i + 1].Y; if ((y0 > y) != (y1 > y)) xs.Add(x0 + (y - y0) / (y1 - y0) * (x1 - x0)); }
                    xs.Sort();
                    for (int p = 0; p + 1 < xs.Count; p += 2) {
                        double x = (xs[p] + xs[p + 1]) / 2.0;
                        if (!Pair(trou, x, y) || !Pair(polygone.Exterieur, x, y) || DansCellule(_carte.Cellules[c], x, y)) continue;
                        double d = Ecart(_carte.Cellules[c], x, y); if (d > meilleur) { meilleur = d; tx = x; ty = y; }
                    }
                }
                Assert.Greater(meilleur, 0, "aucun témoin pour " + _carte.Cellules[c].CellId);
                if (_carte.Cellules[c].CellId == 10326 && ty == 2039609) { etroit = true; Assert.AreEqual(5251721.770642202, tx, 1e-6); }
                Assert.AreEqual(0, Couverture(_maillee.Cellules[c].Maillage.Sommets, (tx - _maillee.Origine.X) / 1000.0, (ty - _maillee.Origine.Y) / 1000.0), _carte.Cellules[c].CellId + " (" + tx + " ; " + ty + ")");
            }
            Assert.IsTrue(trous == 71 && etroit, trous + " trous");
        }

        [Test] public void CouleursEtRefus() {
            Color gris = MaillageDeCarte.CouleurSansPuissance;
            Assert.IsTrue(gris.r == 0.5f && gris.r == gris.g && gris.g == gris.b && gris.a == 1f);
            var teintes = new HashSet<(float, float, float, float)>(); int sans = 0;
            for (int i = 0; i < _carte.Cellules.Count; i++) {
                Color couleur = _maillee.Cellules[i].Couleur;
                if (_carte.Cellules[i].Puissance == null) { sans++; Assert.IsTrue(Meme(couleur, gris)); }
                else { Assert.IsTrue(Meme(couleur, MaillageDeCarte.CouleurPourPuissance(_carte.Cellules[i].Puissance.Id)) && couleur.a == 1f && !Meme(couleur, gris)); teintes.Add((couleur.r, couleur.g, couleur.b, couleur.a)); }
            }
            Assert.IsTrue(sans == 31 && teintes.Count == 39);
            CarteMaillee bis = MaillageDeCarte.Mailler(_carte);
            for (int i = 0; i < _maillee.Cellules.Count; i++) {
                MaillageDePolygone a = _maillee.Cellules[i].Maillage, b = bis.Cellules[i].Maillage;
                Assert.IsTrue(Meme(_maillee.Cellules[i].Couleur, bis.Cellules[i].Couleur) && a.Sommets.Count == b.Sommets.Count);
                for (int k = 0; k < a.Sommets.Count; k++) Assert.IsTrue(a.Sommets[k].x == b.Sommets[k].x && a.Sommets[k].z == b.Sommets[k].z && a.Triangles[k] == b.Triangles[k]);
            }
            var inverse = new List<CelluleDeCarte>();
            for (int i = _carte.Cellules.Count - 1; i >= 0; i--) { CelluleDeCarte c = _carte.Cellules[i]; inverse.Add(new CelluleDeCarte(c.CellId, c.Contour, c.Puissance == null ? null : new IdentiteDeCarte(c.Puissance.Id, "Renommée"), new IdentiteDeCarte(9000 + i, "Autre maison"), c.Villes)); }
            CarteMaillee autre = MaillageDeCarte.Mailler(new CarteLue(inverse.Count, inverse));
            for (int i = 0; i < inverse.Count; i++) { Assert.AreEqual(inverse[i].CellId, autre.Cellules[i].CellId); Assert.IsTrue(Meme(_maillee.Cellules[_carte.Cellules.Count - 1 - i].Couleur, autre.Cellules[i].Couleur), inverse[i].CellId.ToString()); }
            Assert.Throws<ArgumentNullException>(() => MaillageDeCarte.Mailler(null));
            Assert.Throws<ArgumentException>(() => MaillageDeCarte.Mailler(new CarteLue(0, Array.Empty<CelluleDeCarte>())));
            var plat = new PolygoneDeCarte(new[] { new PointCarte(0, 0), new PointCarte(3, 0), new PointCarte(6, 0), new PointCarte(0, 0) }, Array.Empty<PointCarte[]>());
            ArgumentException refus = Assert.Throws<ArgumentException>(() => MaillageDeCarte.Mailler(new CarteLue(1, new[] { new CelluleDeCarte(424242, new[] { plat }, null, null, Array.Empty<VilleDeCarte>()) })));
            StringAssert.Contains("424242", refus.Message);
        }
    }
}
