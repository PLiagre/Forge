using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using NUnit.Framework;
using UnityEngine;

namespace Forge.Pont.Tests {
    // Le terrain levé de la carte servie : aucune cellule ne disparaît, la grille des cellules dit la même terre que
    // les contours, le relief suit la classe servie et s'arrête au rivage, le maillage couvre le tout sous le plan 0.
    // La carte vient de la fixture, lue par ClientCarte ; le terrain est levé une fois pour tous les cas.
    public sealed class TerrainDeCarteTests {
        private static byte[] _octets; private static CarteLue _carte; private static TerrainDeCarte _terrain;
        [SetUp] public void Preparer() {
            if (_terrain != null) return;
            _octets = File.ReadAllBytes(Application.dataPath + "/ForgeLocal3D/Pont/Tests/carte-graine0.json");
            var sonde = new TcpListener(IPAddress.Loopback, 0);
            sonde.Start(); int port = ((IPEndPoint)sonde.LocalEndpoint).Port; sonde.Stop();
            var ecoute = new HttpListener();
            ecoute.Prefixes.Add("http://127.0.0.1:" + port + "/"); ecoute.Start();
            var fil = new Thread(() => {
                try {
                    HttpListenerContext ctx = ecoute.GetContext();
                    ctx.Response.StatusCode = 200; ctx.Response.ContentLength64 = _octets.Length;
                    ctx.Response.OutputStream.Write(_octets, 0, _octets.Length); ctx.Response.Close();
                } catch (Exception) { }
            }) { IsBackground = true };
            fil.Start();
            try {
                using (var client = new ClientCarte(port, ClientCarte.DelaiMinimal))
                { var lecture = client.Lire(); Assert.IsTrue(lecture.Presente, lecture.Absence); _carte = lecture.Carte; }
            } finally { ecoute.Close(); fil.Join(TimeSpan.FromSeconds(5)); }
            _terrain = TerrainDeCarte.Lever(_carte);
        }
        // Une terre carrée, sans puissance ni ville, son coin sud-ouest en (x, y), en mètres.
        private static CelluleDeCarte Carre(long id, double x, double y, double cote, string relief = null) {
            var anneau = new[] { new PointCarte(x, y), new PointCarte(x + cote, y), new PointCarte(x + cote, y + cote), new PointCarte(x, y + cote), new PointCarte(x, y) };
            return new CelluleDeCarte(id, new[] { new PolygoneDeCarte(anneau, new IEnumerable<PointCarte>[0]) }, null, null, new VilleDeCarte[0], relief);
        }
        // Un texel de relief est à terre si la moitié de ses texels de cellules l'est.
        private static bool ATerre(TerrainDeCarte t, int i, int j) {
            int n = 0;
            for (int dj = 0; dj < TerrainDeCarte.TEXELS_PAR_RELIEF; dj++)
                for (int di = 0; di < TerrainDeCarte.TEXELS_PAR_RELIEF; di++)
                    if (t.Cellules[(j * TerrainDeCarte.TEXELS_PAR_RELIEF + dj) * t.Largeur + i * TerrainDeCarte.TEXELS_PAR_RELIEF + di] != 0) n++;
            return n * 2 >= TerrainDeCarte.TEXELS_PAR_RELIEF * TerrainDeCarte.TEXELS_PAR_RELIEF;
        }
        // L'altitude moyenne des texels de relief à terre.
        private static double MoyenneATerre(TerrainDeCarte t) {
            double somme = 0; int n = 0;
            for (int j = 0; j < t.HauteurDuRelief; j++)
                for (int i = 0; i < t.LargeurDuRelief; i++) if (ATerre(t, i, j)) { somme += t.Altitudes[j * t.LargeurDuRelief + i]; n++; }
            Assert.Greater(n, 0, "aucune terre"); return somme / n;
        }

        [Test] public void Chaque_cellule_servie_a_ses_texels() {
            TerrainDeCarte t = _terrain; int servies = _carte.Cellules.Count;
            Assert.IsTrue(servies == 596 && _carte.CellCount == servies, servies + " cellules servies");
            var comptes = new int[servies + 1]; int inconnus = 0;
            Assert.AreEqual(t.Largeur * t.Hauteur, t.Cellules.Count);
            for (int k = 0; k < t.Cellules.Count; k++) { int c = t.Cellules[k]; if (c > servies) inconnus++; else comptes[c]++; }
            Assert.AreEqual(0, inconnus, "texels d'un rang que le service ne sert pas");
            var sans = new List<long>(); int faux = 0;
            for (int r = 0; r < servies; r++) { if (comptes[r + 1] == 0) sans.Add(_carte.Cellules[r].CellId); if (comptes[r + 1] != t.TexelsDe(r)) faux++; }
            Assert.IsEmpty(sans, "cellules servies sans texel : " + string.Join(", ", sans.Take(10)));
            Assert.AreEqual(0, faux, "le compte des texels d'une cellule n'est pas celui de la grille");
            Assert.Greater(comptes[0], 0, "aucune mer");
        }

        [Test] public void Le_rectangle_couvre_les_cellules_bordees_de_mer() {
            TerrainDeCarte t = _terrain; float marge = TerrainDeCarte.MARGE_DE_MER_KM, maille = t.PasDuMaillage;
            PointCarte o = MaillageDeCarte.Mailler(_carte).Origine;
            Assert.IsTrue(t.Origine.X == o.X && t.Origine.Y == o.Y, "l'origine du terrain n'est pas celle des maillages");
            Assert.IsTrue(t.Pas >= TerrainDeCarte.PAS_MINIMAL_KM && Math.Max(t.Largeur, t.Hauteur) <= TerrainDeCarte.COTE_MAXIMAL, t.Largeur + " × " + t.Hauteur + " au pas de " + t.Pas);
            Assert.IsTrue(t.Largeur % TerrainDeCarte.TEXELS_PAR_MAILLE == 0 && t.Hauteur % TerrainDeCarte.TEXELS_PAR_MAILLE == 0 && t.Largeur > 0 && t.Hauteur > 0, "le rectangle n'est pas en mailles entières");
            Assert.IsTrue(t.LargeurDuRelief * TerrainDeCarte.TEXELS_PAR_RELIEF == t.Largeur && t.HauteurDuRelief * TerrainDeCarte.TEXELS_PAR_RELIEF == t.Hauteur && t.Altitudes.Count == t.LargeurDuRelief * t.HauteurDuRelief);
            Assert.IsTrue(t.PasDuRelief == t.Pas * TerrainDeCarte.TEXELS_PAR_RELIEF && maille == t.Pas * TerrainDeCarte.TEXELS_PAR_MAILLE);
            // La boîte est celle des points servis ; le rectangle la borde de la marge, à une maille près au nord et à l'est.
            double x0 = double.PositiveInfinity, z0 = double.PositiveInfinity, x1 = double.NegativeInfinity, z1 = double.NegativeInfinity;
            foreach (CelluleDeCarte c in _carte.Cellules)
                foreach (PolygoneDeCarte p in c.Contour)
                    foreach (PointCarte q in p.Exterieur) { double x = (q.X - o.X) / 1000, z = (q.Y - o.Y) / 1000; if (x < x0) x0 = x; if (x > x1) x1 = x; if (z < z0) z0 = z; if (z > z1) z1 = z; }
            Bounds b = t.Boite;
            Assert.IsTrue(Math.Abs(b.min.x - x0) < 1e-2 && Math.Abs(b.max.x - x1) < 1e-2 && Math.Abs(b.min.z - z0) < 1e-2 && Math.Abs(b.max.z - z1) < 1e-2 && b.size.y == 0, "la boîte n'est pas celle des points servis : " + b);
            Vector2 coin = t.Coin; float est = coin.x + t.Largeur * t.Pas, nord = coin.y + t.Hauteur * t.Pas;
            Assert.IsTrue(Math.Abs(coin.x - (b.min.x - marge)) < 1e-2 && Math.Abs(coin.y - (b.min.z - marge)) < 1e-2, "le coin n'est pas à la marge de la boîte : " + coin);
            Assert.IsTrue(est >= b.max.x + marge - 1e-2 && est < b.max.x + marge + maille && nord >= b.max.z + marge - 1e-2 && nord < b.max.z + marge + maille, "le rectangle ne s'arrête pas à la marge : " + est + ", " + nord);
        }

        // Un texel est à la cellule dont un contour contient son centre : la grille et le repérage par les contours
        // disent la même terre, sauf au ras d'un bord, où l'un calcule en flottants simples et l'autre en doubles.
        [Test] public void La_grille_des_cellules_dit_la_terre_des_contours() {
            TerrainDeCarte t = _terrain; var reperage = new ReperageDeCarte(_carte, t.Origine);
            var rangs = new Dictionary<long, int>(); for (int r = 0; r < _carte.Cellules.Count; r++) rangs[_carte.Cellules[r].CellId] = r + 1;
            int vus = 0, aTerre = 0, enMer = 0, ecarts = 0, horsGrille = 0;
            for (int j = 3; j < t.Hauteur; j += 7)
                for (int i = 3; i < t.Largeur; i += 7) {
                    float x = t.Coin.x + (i + 0.5f) * t.Pas, z = t.Coin.y + (j + 0.5f) * t.Pas; int grille = t.Cellules[j * t.Largeur + i];
                    CelluleDeCarte sous = reperage.Sous(x, z); int attendu = sous == null ? 0 : rangs[sous.CellId];
                    vus++; if (grille == 0) enMer++; else aTerre++;
                    if (grille != attendu) ecarts++;
                    if (t.CelluleEn(x, z) != grille) horsGrille++;
                }
            TestContext.Out.WriteLine(vus + " texels vus, " + aTerre + " à terre, " + ecarts + " écarts");
            Assert.IsTrue(aTerre > 1000 && enMer > 1000, aTerre + " à terre, " + enMer + " en mer : l'échantillon ne juge rien");
            Assert.AreEqual(0, horsGrille, "CelluleEn ne rend pas le texel de la grille");
            Assert.LessOrEqual(ecarts, vus / 10000, ecarts + " texels sur " + vus + " ne sont pas à la cellule de leur centre");
            Assert.IsTrue(t.CelluleEn(t.Coin.x - 1, 0) == 0 && t.CelluleEn(0, t.Coin.y + t.Hauteur * t.Pas + 1) == 0, "hors du rectangle, ce n'est pas la mer");
        }

        [Test] public void Le_relief_monte_avec_la_classe_servie() {
            TerrainDeCarte t = _terrain; int servies = _carte.Cellules.Count; var parRang = new double[servies];
            for (int j = 0; j < t.Hauteur; j++)
                for (int i = 0; i < t.Largeur; i++) {
                    int c = t.Cellules[j * t.Largeur + i];
                    if (c != 0) parRang[c - 1] += t.Altitudes[(j / TerrainDeCarte.TEXELS_PAR_RELIEF) * t.LargeurDuRelief + i / TerrainDeCarte.TEXELS_PAR_RELIEF];
                }
            var sommes = new Dictionary<string, double>(); var comptes = new Dictionary<string, int>();
            for (int r = 0; r < servies; r++) {
                string classe = _carte.Cellules[r].Relief; Assert.IsNotNull(classe, "cellule " + _carte.Cellules[r].CellId + " sans relief servi");
                sommes.TryGetValue(classe, out double s); comptes.TryGetValue(classe, out int n); sommes[classe] = s + parRang[r]; comptes[classe] = n + t.TexelsDe(r);
            }
            string[] ordre = { "marais", "plaine", "colline", "montagne", "haute_montagne" };
            CollectionAssert.AreEquivalent(ordre, sommes.Keys, "les classes servies ne sont pas celles que le terrain habille");
            double[] moyennes = ordre.Select(c => sommes[c] / comptes[c]).ToArray();
            string lu = string.Join(", ", ordre.Select((c, k) => c + " " + moyennes[k].ToString("0.00")));
            TestContext.Out.WriteLine(lu);
            for (int k = 0; k + 1 < ordre.Length; k++) Assert.Less(moyennes[k], moyennes[k + 1], ordre[k] + " n'est pas plus bas que " + ordre[k + 1] + " : " + lu);
        }

        [Test] public void La_terre_emerge_la_mer_plonge_et_le_bord_est_au_fond() {
            TerrainDeCarte t = _terrain; int l = t.LargeurDuRelief, h = t.HauteurDuRelief, terres = 0, mers = 0, noyees = 0, emergees = 0; float cime = float.NegativeInfinity, creux = float.PositiveInfinity;
            for (int j = 0; j < h; j++)
                for (int i = 0; i < l; i++) {
                    float a = t.Altitudes[j * l + i]; if (a > cime) cime = a; if (a < creux) creux = a;
                    if (ATerre(t, i, j)) { terres++; if (!(a >= TerrainDeCarte.RIVAGE)) noyees++; } else { mers++; if (!(a <= 0f)) emergees++; }
                }
            TestContext.Out.WriteLine("de " + creux + " à " + cime + " km de décor");
            Assert.IsTrue(terres > 1000 && mers > 1000, terres + " altitudes à terre, " + mers + " en mer");
            Assert.AreEqual(0, noyees, "altitudes à terre sous le rivage"); Assert.AreEqual(0, emergees, "altitudes en mer au-dessus de l'eau");
            Assert.IsTrue(cime <= TerrainDeCarte.PLAFOND && cime > 10f, "la plus haute cime : " + cime);
            Assert.IsTrue(creux >= -TerrainDeCarte.FOND - 1e-3f, "le creux le plus bas : " + creux);
            foreach (int k in new[] { 0, l - 1, (h - 1) * l, h * l - 1 }) Assert.AreEqual(-TerrainDeCarte.FOND, t.Altitudes[k], 1e-2f, "un coin du terrain n'est pas au fond");
            // Entre les altitudes, la lecture est continue ; hors du rectangle, elle garde celle du bord.
            float pas = t.PasDuRelief; Vector2 coin = t.Coin;
            Assert.AreEqual(t.Altitudes[5 * l + 7], t.Altitude(coin.x + 7.5f * pas, coin.y + 5.5f * pas), 1e-3f, "au centre d'un texel de relief");
            Assert.AreEqual((t.Altitudes[5 * l + 7] + t.Altitudes[5 * l + 8]) / 2, t.Altitude(coin.x + 8f * pas, coin.y + 5.5f * pas), 1e-3f, "entre deux texels de relief");
            Assert.AreEqual(t.Altitudes[0], t.Altitude(coin.x - 500, coin.y - 500), 1e-3f, "hors du rectangle");
        }

        [Test] public void Deux_leves_de_la_meme_carte_sont_egaux() {
            var montre = Stopwatch.StartNew(); TerrainDeCarte second = TerrainDeCarte.Lever(_carte); montre.Stop();
            TestContext.Out.WriteLine("levé en " + montre.ElapsedMilliseconds + " ms, " + second.Largeur + " × " + second.Hauteur + " texels au pas de " + second.Pas + " km");
            Assert.IsTrue(second.Largeur == _terrain.Largeur && second.Hauteur == _terrain.Hauteur && second.Pas == _terrain.Pas && second.Coin == _terrain.Coin);
            int ecarts = 0;
            for (int k = 0; k < second.Cellules.Count; k++) if (second.Cellules[k] != _terrain.Cellules[k]) ecarts++;
            for (int k = 0; k < second.Altitudes.Count; k++) if (second.Altitudes[k] != _terrain.Altitudes[k]) ecarts++;
            for (int k = 0; k < second.Sommets.Count; k++) if (second.Sommets[k] != _terrain.Sommets[k]) ecarts++;
            Assert.AreEqual(0, ecarts, "texels, altitudes ou sommets différents d'un levé à l'autre");
        }

        [Test] public void Le_maillage_couvre_le_rectangle_sous_le_plan_des_calques() {
            TerrainDeCarte t = _terrain; int m = TerrainDeCarte.TEXELS_PAR_MAILLE, nx = t.Largeur / m + 1, nz = t.Hauteur / m + 1;
            Assert.IsTrue(t.Sommets.Count == nx * nz && t.Uv.Count == nx * nz && t.Triangles.Count == (nx - 1) * (nz - 1) * 6, t.Sommets.Count + " sommets, " + t.Triangles.Count + " indices");
            Vector3 premier = t.Sommets[0], dernier = t.Sommets[nx * nz - 1];
            Assert.IsTrue(Math.Abs(premier.x - t.Coin.x) < 1e-2 && Math.Abs(premier.z - t.Coin.y) < 1e-2, "le premier sommet n'est pas au coin sud-ouest");
            Assert.IsTrue(Math.Abs(dernier.x - (t.Coin.x + t.Largeur * t.Pas)) < 1e-2 && Math.Abs(dernier.z - (t.Coin.y + t.Hauteur * t.Pas)) < 1e-2, "le dernier sommet n'est pas au coin nord-est");
            Assert.IsTrue(t.Uv[0] == Vector2.zero && t.Uv[nx * nz - 1] == Vector2.one, "les uv ne vont pas d'un coin à l'autre des grilles");
            int hauts = 0, faux = 0, horsGrille = 0; float sommet = float.NegativeInfinity;
            for (int k = 0; k < t.Sommets.Count; k++) {
                Vector3 s = t.Sommets[k]; if (s.y > 0f) hauts++; if (s.y > sommet) sommet = s.y;
                if (Math.Abs(s.y - (t.Altitude(s.x, s.z) - TerrainDeCarte.PLAFOND)) > 1e-4f) faux++;
                // Un sommet lit les grilles là où il est posé.
                Vector2 uv = t.Uv[k]; if (Math.Abs(uv.x * t.Largeur * t.Pas - (s.x - t.Coin.x)) > 1e-2 || Math.Abs(uv.y * t.Hauteur * t.Pas - (s.z - t.Coin.y)) > 1e-2) horsGrille++;
            }
            Assert.AreEqual(0, hauts, "sommets au-dessus du plan des calques"); Assert.AreEqual(0, faux, "sommets qui ne sont pas à l'altitude du relief");
            Assert.AreEqual(0, horsGrille, "sommets dont les uv ne désignent pas leur place");
            Assert.Greater(sommet, -TerrainDeCarte.PLAFOND + 10f, "le maillage est plat : sa plus haute cime est à " + sommet);
            int renverses = 0, horsBornes = 0;
            for (int k = 0; k < t.Triangles.Count; k += 3) {
                int a = t.Triangles[k], b = t.Triangles[k + 1], c = t.Triangles[k + 2];
                if (a < 0 || b < 0 || c < 0 || a >= nx * nz || b >= nx * nz || c >= nx * nz) { horsBornes++; continue; }
                if (!(Vector3.Cross(t.Sommets[b] - t.Sommets[a], t.Sommets[c] - t.Sommets[a]).y > 0f)) renverses++;
            }
            Assert.AreEqual(0, horsBornes, "indices hors des sommets"); Assert.AreEqual(0, renverses, "triangles qui ne regardent pas vers le haut");
        }

        // Une île de dix mètres ne contient le centre d'aucun texel : elle en reçoit un quand même, là où elle est.
        [Test] public void Une_ile_plus_petite_qu_un_texel_garde_un_texel() {
            var carte = new CarteLue(2, new[] { Carre(1, 0, 0, 50000), Carre(2, 100000, 20000, 10) });
            TerrainDeCarte t = TerrainDeCarte.Lever(carte); PointCarte o = t.Origine;
            Assert.AreEqual(1f, t.Pas, "une petite carte se lève au pas minimal");
            Assert.AreEqual(2500, t.TexelsDe(0), "une terre de 50 km de côté, au pas d'un km");
            Assert.AreEqual(1, t.TexelsDe(1), "l'île n'a pas son texel");
            Assert.AreEqual(2, t.CelluleEn((float)((100005 - o.X) / 1000), (float)((20005 - o.Y) / 1000)), "le texel de l'île n'est pas sous l'île");
            Assert.AreEqual(1, t.CelluleEn((float)((25000 - o.X) / 1000), (float)((25000 - o.Y) / 1000)));
            Assert.AreEqual(0, t.CelluleEn((float)((75000 - o.X) / 1000), (float)((25000 - o.Y) / 1000)), "entre la terre et l'île, ce n'est pas la mer");
            Assert.AreEqual(2501, t.Cellules.Count(c => c != 0));
        }

        [Test] public void Une_carte_sans_terre_n_a_pas_de_terrain() {
            Assert.Throws<ArgumentNullException>(() => TerrainDeCarte.Lever(null));
            var vide = Assert.Throws<ArgumentException>(() => TerrainDeCarte.Lever(new CarteLue(0, new CelluleDeCarte[0])));
            StringAssert.Contains("une carte vide n'a aucun terrain", vide.Message);
            var sansContour = new CelluleDeCarte(5, new PolygoneDeCarte[0], null, null, new VilleDeCarte[0]);
            var refus = Assert.Throws<ArgumentException>(() => TerrainDeCarte.Lever(new CarteLue(2, new[] { Carre(1, 0, 0, 50000), sansContour })));
            StringAssert.Contains("cellule 5 : aucun contour", refus.Message);
            // Le rang d'une cellule tient dans un texel de seize bits, le zéro étant la mer.
            var trop = Assert.Throws<ArgumentException>(() => TerrainDeCarte.Lever(new CarteLue(ushort.MaxValue, Enumerable.Range(0, ushort.MaxValue).Select(i => Carre(i, 0, 0, 1000)).ToArray())));
            StringAssert.Contains(ushort.MaxValue + " cellules", trop.Message);
        }

        [Test] public void Un_relief_non_servi_se_dessine_en_plaine() {
            TerrainDeCarte Leve(string relief) => TerrainDeCarte.Lever(new CarteLue(1, new[] { Carre(1, 0, 0, 200000, relief) }));
            TerrainDeCarte plaine = Leve("plaine"), sans = Leve(null), inconnue = Leve("lagune"), montagne = Leve("montagne"), marais = Leve("marais");
            Assert.AreEqual(plaine.Altitudes.Count, sans.Altitudes.Count);
            int ecarts = 0;
            for (int k = 0; k < plaine.Altitudes.Count; k++) if (plaine.Altitudes[k] != sans.Altitudes[k] || plaine.Altitudes[k] != inconnue.Altitudes[k]) ecarts++;
            Assert.AreEqual(0, ecarts, "un relief absent ou inconnu ne se lève pas comme une plaine");
            double basse = MoyenneATerre(marais), moyenne = MoyenneATerre(plaine), haute = MoyenneATerre(montagne);
            Assert.IsTrue(basse < moyenne && moyenne < haute, "marais " + basse + ", plaine " + moyenne + ", montagne " + haute);
            // La classe ne change que le relief : la terre est la même.
            for (int k = 0; k < plaine.Cellules.Count; k++) if (plaine.Cellules[k] != montagne.Cellules[k]) ecarts++;
            Assert.AreEqual(0, ecarts, "la classe de relief a déplacé la terre");
        }
    }
}
