using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;
using NUnit.Framework;
using UnityEngine;

namespace Forge.Pont.Tests {
    // Le terrain levé de la carte servie et de la forme de ses lieux : aucun lieu ne disparaît, la grille des lieux dit
    // la même terre que leurs contours, le relief suit la classe servie et s'arrête au rivage, le maillage couvre le
    // tout sous le plan 0, et chaque texel porte sa distance au bord de son lieu, à la côte et, selon les pays des
    // lieux, à la frontière, qui passe dans une cellule quand deux pays se la partagent. La carte, ses formes et ses
    // terres sont les réponses figées de l'Ouest (`FormesDeTest`) ; le terrain est levé une fois pour tous les cas.
    public sealed class TerrainDeCarteTests {
        private static CarteLue Carte => FormesDeTest.CarteOuest;
        private static FormesLues Formes => FormesDeTest.FormesOuest;
        private static TerrainDeCarte Terrain => FormesDeTest.TerrainOuest;
        // Une terre carrée, sans puissance ni ville, son coin sud-ouest en (x, y), en mètres.
        private static CelluleDeCarte Carre(long id, double x, double y, double cote, string relief = null, double haut = 0) {
            double h = haut > 0 ? haut : cote;
            var anneau = new[] { new PointCarte(x, y), new PointCarte(x + cote, y), new PointCarte(x + cote, y + h), new PointCarte(x, y + h), new PointCarte(x, y) };
            return new CelluleDeCarte(id, new[] { new PolygoneDeCarte(anneau, new IEnumerable<PointCarte>[0]) }, null, null, new VilleDeCarte[0], relief);
        }
        private static TerrainDeCarte LeveDe(params CelluleDeCarte[] cellules) => FormesDeTest.Lever(new CarteLue(cellules.Length, cellules));
        // Un anneau rectangulaire, en mètres, en polygone sans trou.
        private static PolygoneDeCarte[] Rectangle(double x0, double y0, double x1, double y1) =>
            new[] { new PolygoneDeCarte(new[] { new PointCarte(x0, y0), new PointCarte(x1, y0), new PointCarte(x1, y1), new PointCarte(x0, y1), new PointCarte(x0, y0) }, new IEnumerable<PointCarte>[0]) };
        // Les anneaux d'un lieu en km locaux, extérieurs et trous confondus.
        private static List<double[]> Anneaux(FormeDeLieu lieu, PointCarte o) {
            var anneaux = new List<double[]>();
            foreach (PolygoneDeCarte p in lieu.Contour)
                for (int a = -1; a < p.Trous.Count; a++) {
                    IReadOnlyList<PointCarte> anneau = a < 0 ? p.Exterieur : p.Trous[a]; var km = new double[2 * anneau.Count];
                    for (int k = 0; k < anneau.Count; k++) { km[2 * k] = (anneau[k].X - o.X) / 1000.0; km[2 * k + 1] = (anneau[k].Y - o.Y) / 1000.0; }
                    anneaux.Add(km);
                }
            return anneaux;
        }
        // Un point est au lieu s'il croise un nombre impair de ses anneaux (règle pair-impair).
        private static bool Dans(List<double[]> anneaux, double x, double z) {
            bool dedans = false;
            foreach (double[] a in anneaux)
                for (int k = 0; k + 3 < a.Length; k += 2)
                    if ((a[k + 1] > z) != (a[k + 3] > z) && x < a[k] + (z - a[k + 1]) / (a[k + 3] - a[k + 1]) * (a[k + 2] - a[k])) dedans = !dedans;
            return dedans;
        }
        // La surface d'un lieu en km² : ses anneaux extérieurs, moins ses trous.
        private static double Surface(FormeDeLieu lieu) {
            double s = 0;
            foreach (PolygoneDeCarte p in lieu.Contour)
                for (int a = -1; a < p.Trous.Count; a++) {
                    IReadOnlyList<PointCarte> anneau = a < 0 ? p.Exterieur : p.Trous[a]; double aire = 0;
                    for (int k = 0; k + 1 < anneau.Count; k++) aire += anneau[k].X * anneau[k + 1].Y - anneau[k + 1].X * anneau[k].Y;
                    s += (a < 0 ? 1 : -1) * Math.Abs(aire) / 2e6;
                }
            return s;
        }
        private static FormeDeLieu FormeDuLieu(TerrainDeCarte t, int lieu) => Formes.De(Carte.Cellules[t.CelluleDuLieu(lieu)].CellId).Lieux[t.RangDuLieu(lieu)];
        private static int RangDe(long cellId) { for (int r = 0; r < Carte.Cellules.Count; r++) if (Carte.Cellules[r].CellId == cellId) return r; throw new ArgumentException("cellule " + cellId + " absente de la carte figée"); }

        // La hauteur que le dessin lit sous un point est celle du triangle du maillage qui le porte : à un sommet, la
        // sienne ; au milieu de la diagonale d'une maille, la moyenne de ses deux bouts ; au centre d'un triangle, la
        // moyenne de ses trois sommets. C'est ce sol-là que suivent les calques drapés et le rayon de la souris.
        [Test] public void La_hauteur_du_maillage_se_lit_sur_ses_triangles() {
            TerrainDeCarte t = Terrain; int nx = t.Largeur / TerrainDeCarte.TEXELS_PAR_MAILLE + 1, nz = t.Hauteur / TerrainDeCarte.TEXELS_PAR_MAILLE + 1, vus = 0;
            Assert.AreEqual(nx * nz, t.Sommets.Count, "le maillage n'est pas une grille");
            float plusHaut = float.MinValue, plusBas = float.MaxValue;
            for (int j = 3; j + 4 < nz; j += 3)
                for (int i = 3; i + 4 < nx; i += 3) {
                    Vector3 a = t.Sommets[j * nx + i], b = t.Sommets[j * nx + i + 1], c = t.Sommets[(j + 1) * nx + i], d = t.Sommets[(j + 1) * nx + i + 1];
                    Assert.AreEqual(a.y, t.SolDuMaillage(a.x, a.z), 2e-3f, "au sommet (" + i + ", " + j + ")");
                    Assert.AreEqual((b.y + c.y) / 2f, t.SolDuMaillage((b.x + c.x) / 2f, (b.z + c.z) / 2f), 2e-3f, "au milieu de la diagonale de la maille (" + i + ", " + j + ")");
                    Assert.AreEqual((a.y + b.y + c.y) / 3f, t.SolDuMaillage((a.x + b.x + c.x) / 3f, (a.z + b.z + c.z) / 3f), 2e-3f, "au centre du triangle du sud-ouest de la maille (" + i + ", " + j + ")");
                    Assert.AreEqual((b.y + c.y + d.y) / 3f, t.SolDuMaillage((b.x + c.x + d.x) / 3f, (b.z + c.z + d.z) / 3f), 2e-3f, "au centre du triangle du nord-est de la maille (" + i + ", " + j + ")");
                    plusHaut = Mathf.Max(plusHaut, a.y); plusBas = Mathf.Min(plusBas, a.y); vus++;
                }
            Assert.Greater(vus, 1000, "échantillon vide"); Assert.LessOrEqual(plusHaut, 0f); Assert.Greater(plusHaut - plusBas, 20f, "échantillon vide : aucune montagne ni aucun fond parmi les mailles lues");
            // Hors du rectangle, la hauteur du bord.
            Assert.AreEqual(t.Sommets[0].y, t.SolDuMaillage(t.Coin.x - 500f, t.Coin.y - 500f), 1e-4f); Assert.AreEqual(t.Sommets[nx * nz - 1].y, t.SolDuMaillage(t.Sommets[nx * nz - 1].x + 500f, t.Sommets[nx * nz - 1].z + 500f), 1e-4f);
        }
        // Un texel de relief est à terre si la moitié de ses texels de lieux l'est.
        private static bool ATerre(TerrainDeCarte t, int i, int j) {
            int n = 0;
            for (int dj = 0; dj < TerrainDeCarte.TEXELS_PAR_RELIEF; dj++)
                for (int di = 0; di < TerrainDeCarte.TEXELS_PAR_RELIEF; di++)
                    if (t.Lieux[(j * TerrainDeCarte.TEXELS_PAR_RELIEF + dj) * t.Largeur + i * TerrainDeCarte.TEXELS_PAR_RELIEF + di] != 0) n++;
            return n * 2 >= TerrainDeCarte.TEXELS_PAR_RELIEF * TerrainDeCarte.TEXELS_PAR_RELIEF;
        }
        // L'altitude moyenne des texels de relief à terre.
        private static double MoyenneATerre(TerrainDeCarte t) {
            double somme = 0; int n = 0;
            for (int j = 0; j < t.HauteurDuRelief; j++)
                for (int i = 0; i < t.LargeurDuRelief; i++) if (ATerre(t, i, j)) { somme += t.Altitudes[j * t.LargeurDuRelief + i]; n++; }
            Assert.Greater(n, 0, "aucune terre"); return somme / n;
        }

        [Test] public void Chaque_lieu_servi_a_ses_texels() {
            TerrainDeCarte t = Terrain; int servies = Carte.Cellules.Count, servis = Formes.Cellules.Sum(c => c.Lieux.Count);
            Assert.IsTrue(servies == 16 && servis > 200 && t.NombreDeLieux == servis, servies + " cellules et " + servis + " lieux servis, " + t.NombreDeLieux + " levés");
            var comptes = new int[servis + 1]; int inconnus = 0;
            Assert.AreEqual(t.Largeur * t.Hauteur, t.Lieux.Count);
            for (int k = 0; k < t.Lieux.Count; k++) { int c = t.Lieux[k]; if (c > servis) inconnus++; else comptes[c]++; }
            Assert.AreEqual(0, inconnus, "texels d'un lieu que le service ne sert pas");
            var sans = new List<string>(); int faux = 0;
            for (int l = 0; l < servis; l++) { if (comptes[l + 1] == 0) sans.Add(Carte.Cellules[t.CelluleDuLieu(l)].CellId + "/" + t.RangDuLieu(l)); if (comptes[l + 1] != t.TexelsDuLieu(l)) faux++; }
            Assert.IsEmpty(sans, "lieux servis sans texel : " + string.Join(", ", sans.Take(10)));
            Assert.AreEqual(0, faux, "le compte des texels d'un lieu n'est pas celui de la grille");
            Assert.Greater(comptes[0], 0, "aucune mer");
            // Les lieux d'une cellule se suivent, par rang ; la cellule compte leurs texels.
            for (int r = 0; r < servies; r++) {
                FormeDeCellule forme = Formes.De(Carte.Cellules[r].CellId); int premier = t.PremierLieuDe(r), somme = 0;
                Assert.AreEqual(forme.Lieux.Count, t.LieuxDe(r), "cellule " + forme.CellId);
                for (int k = 0; k < forme.Lieux.Count; k++) {
                    Assert.IsTrue(t.CelluleDuLieu(premier + k) == r && t.RangDuLieu(premier + k) == forme.Lieux[k].Rang && t.LieuDe(r, forme.Lieux[k].Rang) == premier + k, "cellule " + forme.CellId + ", lieu " + k);
                    somme += t.TexelsDuLieu(premier + k);
                }
                Assert.AreEqual(somme, t.TexelsDe(r), "cellule " + forme.CellId + " : ses texels ne sont pas ceux de ses lieux");
                Assert.AreEqual(-1, t.LieuDe(r, forme.Lieux.Count), "un rang que la cellule ne sert pas a un lieu");
            }
        }

        // Chaque lieu porte autant de texels que sa surface en couvre, au bord près : la grille dessine les lieux à
        // leur taille, et le plus petit lieu servi s'y voit. Sur la carte entière, le pas laisse cent texels au moins à
        // un lieu de 1 000 km².
        [Test] public void Chaque_lieu_a_les_texels_de_sa_surface() {
            TerrainDeCarte t = Terrain; double total = 0, ecart = 0, petite = double.MaxValue, texel = (double)t.Pas * t.Pas; int petit = -1, grands = 0; var aLEcart = new List<string>();
            for (int l = 0; l < t.NombreDeLieux; l++) {
                double surface = Surface(FormeDuLieu(t, l)), couverte = t.TexelsDuLieu(l) * texel;
                total += surface; ecart += Math.Abs(couverte - surface);
                if (surface < petite) { petite = surface; petit = l; }
                // Un lieu d'au moins cent texels a ceux de sa surface, à un cinquième près ; plus petit, un texel de plus ou de moins compte.
                if (surface < 100 * texel) continue;
                grands++; if (Math.Abs(couverte - surface) > surface / 5) aLEcart.Add(Carte.Cellules[t.CelluleDuLieu(l)].CellId + "/" + t.RangDuLieu(l));
            }
            TestContext.Out.WriteLine("au pas de " + t.Pas + " km, " + t.NombreDeLieux + " lieux sur " + total.ToString("0") + " km², écart " + ecart.ToString("0") + " km² ; le plus petit lieu, "
                + Carte.Cellules[t.CelluleDuLieu(petit)].CellId + "/" + t.RangDuLieu(petit) + ", fait " + petite.ToString("0.0") + " km² et " + t.TexelsDuLieu(petit) + " texels");
            Assert.Greater(total, 100000, "échantillon vide : les lieux servis ne couvrent presque rien");
            Assert.Less(ecart, total / 50, "les texels des lieux ne suivent pas leur surface");
            Assert.Greater(grands, t.NombreDeLieux / 2, "échantillon vide : presque aucun lieu de cent texels");
            Assert.IsEmpty(aLEcart, "lieux dont les texels ne couvrent pas la surface : " + string.Join(", ", aLEcart.Take(10)));
            // Le pas de la carte entière : son plus grand côté, celui de la carte de 1400 figée, bordé de mer.
            var racine = LecteurJson.LireObjet(File.ReadAllText(Application.dataPath + "/ForgeLocal3D/Pont/Tests/carte-graine0.json", Encoding.UTF8));
            double x0 = double.MaxValue, y0 = double.MaxValue, x1 = double.MinValue, y1 = double.MinValue;
            foreach (Dictionary<string, object> cellule in (List<object>)racine["cells"])
                foreach (List<object> polygone in (List<object>)((Dictionary<string, object>)cellule["contour"])["coordinates"])
                    foreach (List<object> anneau in polygone)
                        foreach (List<object> point in anneau) { double x = (double)point[0], y = (double)point[1]; x0 = Math.Min(x0, x); x1 = Math.Max(x1, x); y0 = Math.Min(y0, y); y1 = Math.Max(y1, y); }
            double pas = TerrainDeCarte.PasPour(Math.Max(x1 - x0, y1 - y0) / 1000 + 2 * TerrainDeCarte.MARGE_DE_MER_KM), mille = 1000 / (pas * pas);
            TestContext.Out.WriteLine("carte entière de " + ((x1 - x0) / 1000).ToString("0") + " × " + ((y1 - y0) / 1000).ToString("0") + " km : pas de " + pas.ToString("0.000") + " km, " + mille.ToString("0") + " texels pour 1 000 km²");
            Assert.GreaterOrEqual(mille, 100, "au pas de la carte entière, un lieu de 1 000 km² n'a pas cent texels");
        }

        [Test] public void Le_rectangle_couvre_les_lieux_bordes_de_mer() {
            TerrainDeCarte t = Terrain; float marge = TerrainDeCarte.MARGE_DE_MER_KM, maille = t.PasDuMaillage;
            PointCarte o = MaillageDeCarte.Mailler(Carte).Origine;
            Assert.IsTrue(t.Origine.X == o.X && t.Origine.Y == o.Y, "l'origine du terrain n'est pas celle des maillages");
            Assert.IsTrue(t.Pas >= TerrainDeCarte.PAS_MINIMAL_KM && Math.Max(t.Largeur, t.Hauteur) <= TerrainDeCarte.COTE_MAXIMAL, t.Largeur + " × " + t.Hauteur + " au pas de " + t.Pas);
            Assert.IsTrue(t.Largeur % TerrainDeCarte.TEXELS_PAR_MAILLE == 0 && t.Hauteur % TerrainDeCarte.TEXELS_PAR_MAILLE == 0 && t.Largeur > 0 && t.Hauteur > 0, "le rectangle n'est pas en mailles entières");
            Assert.IsTrue(t.LargeurDuRelief * TerrainDeCarte.TEXELS_PAR_RELIEF == t.Largeur && t.HauteurDuRelief * TerrainDeCarte.TEXELS_PAR_RELIEF == t.Hauteur && t.Altitudes.Count == t.LargeurDuRelief * t.HauteurDuRelief);
            Assert.IsTrue(t.PasDuRelief == t.Pas * TerrainDeCarte.TEXELS_PAR_RELIEF && maille == t.Pas * TerrainDeCarte.TEXELS_PAR_MAILLE);
            // La boîte est celle des points des lieux servis ; le rectangle la borde de la marge, à une maille près au nord et à l'est.
            double x0 = double.PositiveInfinity, z0 = double.PositiveInfinity, x1 = double.NegativeInfinity, z1 = double.NegativeInfinity;
            foreach (FormeDeCellule c in Formes.Cellules)
                foreach (FormeDeLieu l in c.Lieux)
                    foreach (PolygoneDeCarte p in l.Contour)
                        foreach (PointCarte q in p.Exterieur) { double x = (q.X - o.X) / 1000, z = (q.Y - o.Y) / 1000; if (x < x0) x0 = x; if (x > x1) x1 = x; if (z < z0) z0 = z; if (z > z1) z1 = z; }
            Bounds b = t.Boite;
            Assert.IsTrue(Math.Abs(b.min.x - x0) < 1e-2 && Math.Abs(b.max.x - x1) < 1e-2 && Math.Abs(b.min.z - z0) < 1e-2 && Math.Abs(b.max.z - z1) < 1e-2 && b.size.y == 0, "la boîte n'est pas celle des points servis : " + b);
            Vector2 coin = t.Coin; float est = coin.x + t.Largeur * t.Pas, nord = coin.y + t.Hauteur * t.Pas;
            Assert.IsTrue(Math.Abs(coin.x - (b.min.x - marge)) < 1e-2 && Math.Abs(coin.y - (b.min.z - marge)) < 1e-2, "le coin n'est pas à la marge de la boîte : " + coin);
            Assert.IsTrue(est >= b.max.x + marge - 1e-2 && est < b.max.x + marge + maille && nord >= b.max.z + marge - 1e-2 && nord < b.max.z + marge + maille, "le rectangle ne s'arrête pas à la marge : " + est + ", " + nord);
            Assert.AreEqual(TerrainDeCarte.PasPour(Math.Max(b.size.x, b.size.z) + 2 * marge), t.Pas, 1e-6, "le pas n'est pas celui du plus grand côté");
        }

        // Un texel est au lieu dont un contour contient son centre : la grille et les contours servis des lieux disent
        // la même terre, sauf au ras d'un bord. La cellule d'un texel est celle de son lieu.
        [Test] public void La_grille_des_lieux_dit_la_terre_des_contours() {
            TerrainDeCarte t = Terrain; var anneaux = new List<double[]>[t.NombreDeLieux]; var boites = new Rect[t.NombreDeLieux];
            for (int l = 0; l < anneaux.Length; l++) {
                anneaux[l] = Anneaux(FormeDuLieu(t, l), t.Origine); float a = float.MaxValue, c = float.MaxValue, b = float.MinValue, d = float.MinValue;
                foreach (double[] anneau in anneaux[l]) for (int k = 0; k + 1 < anneau.Length; k += 2) { a = Mathf.Min(a, (float)anneau[k]); b = Mathf.Max(b, (float)anneau[k]); c = Mathf.Min(c, (float)anneau[k + 1]); d = Mathf.Max(d, (float)anneau[k + 1]); }
                boites[l] = Rect.MinMaxRect(a, c, b, d);
            }
            int vus = 0, aTerre = 0, enMer = 0, ecarts = 0, horsGrille = 0, autreCellule = 0;
            for (int j = 3; j < t.Hauteur; j += 7)
                for (int i = 3; i < t.Largeur; i += 7) {
                    float x = t.Coin.x + (i + 0.5f) * t.Pas, z = t.Coin.y + (j + 0.5f) * t.Pas; int grille = t.Lieux[j * t.Largeur + i], attendu = 0;
                    for (int l = 0; l < anneaux.Length && attendu == 0; l++) if (boites[l].Contains(new Vector2(x, z)) && Dans(anneaux[l], x, z)) attendu = l + 1;
                    vus++; if (grille == 0) enMer++; else aTerre++;
                    if (grille != attendu) ecarts++;
                    if (t.LieuEn(x, z) != grille) horsGrille++;
                    if (t.CelluleEn(x, z) != (grille == 0 ? 0 : t.CelluleDuLieu(grille - 1) + 1)) autreCellule++;
                }
            TestContext.Out.WriteLine(vus + " texels vus, " + aTerre + " à terre, " + ecarts + " écarts");
            Assert.IsTrue(aTerre > 1000 && enMer > 1000, aTerre + " à terre, " + enMer + " en mer : l'échantillon ne juge rien");
            Assert.AreEqual(0, horsGrille, "LieuEn ne rend pas le texel de la grille"); Assert.AreEqual(0, autreCellule, "CelluleEn ne rend pas la cellule du lieu");
            Assert.LessOrEqual(ecarts, vus / 10000, ecarts + " texels sur " + vus + " ne sont pas au lieu de leur centre");
            Assert.IsTrue(t.LieuEn(t.Coin.x - 1, 0) == 0 && t.CelluleEn(0, t.Coin.y + t.Hauteur * t.Pas + 1) == 0, "hors du rectangle, ce n'est pas la mer");
        }

        // Ce que la grille distingue, un trait le borde : entre deux texels voisins de lieux différents, de la même
        // cellule ou de deux, chacun a un bord de son lieu à deux texels au plus ; entre la terre et la mer, c'est la
        // côte. Une pointe ou une entaille plus fine qu'un texel, dont il ne reste que des texels épars, garde ainsi son trait.
        [Test] public void Un_changement_de_la_grille_a_son_trait() {
            TerrainDeCarte t = Terrain; int cotes = 0, entreCellules = 0, dansUneCellule = 0, sansTrait = 0; var parDemi = new int[5]; float pire = 0f, seuil = 2f * t.Pas;
            for (int j = 0; j < t.Hauteur; j++)
                for (int i = 0; i < t.Largeur; i++) {
                    int ici = t.Lieux[j * t.Largeur + i];
                    for (int v = 0; v < 2; v++) {
                        int vi = i + 1 - v, vj = j + v; if (vi >= t.Largeur || vj >= t.Hauteur) continue;
                        int la = t.Lieux[vj * t.Largeur + vi]; if (la == ici) continue;
                        float x = t.Coin.x + (i + 0.5f) * t.Pas, z = t.Coin.y + (j + 0.5f) * t.Pas, xv = t.Coin.x + (vi + 0.5f) * t.Pas, zv = t.Coin.y + (vj + 0.5f) * t.Pas;
                        float d;
                        if (ici == 0 || la == 0) { cotes++; d = Mathf.Max(t.CoteEn(x, z), t.CoteEn(xv, zv)); }
                        else { if (t.CelluleDuLieu(ici - 1) == t.CelluleDuLieu(la - 1)) dansUneCellule++; else entreCellules++; d = Mathf.Max(t.BordEn(x, z), t.BordEn(xv, zv)); }
                        parDemi[Mathf.Min(4, Mathf.FloorToInt(2f * d / t.Pas))]++; if (d > seuil) sansTrait++; if (d > pire) pire = d;
                    }
                }
            TestContext.Out.WriteLine(cotes + " changements entre terre et mer, " + entreCellules + " entre deux cellules, " + dansUneCellule + " entre deux lieux d'une cellule ; par demi-texel de distance au trait : "
                + string.Join(" ", parDemi) + " ; le pire à " + pire + " km");
            Assert.IsTrue(cotes > 1000 && entreCellules > 1000 && dansUneCellule > 1000, cotes + " côtes, " + entreCellules + " bords entre cellules, " + dansUneCellule + " dans une cellule : l'échantillon ne juge rien");
            Assert.AreEqual(0, sansTrait, sansTrait + " changements de la grille sont à plus de " + seuil + " km de tout trait, le pire à " + pire + " km");
        }

        // Chaque lieu a le relief de sa cellule : la moyenne des altitudes monte avec la classe servie.
        [Test] public void Le_relief_monte_avec_la_classe_servie() {
            TerrainDeCarte t = Terrain; int servies = Carte.Cellules.Count; var parRang = new double[servies];
            for (int j = 0; j < t.Hauteur; j++)
                for (int i = 0; i < t.Largeur; i++) {
                    int c = t.Lieux[j * t.Largeur + i];
                    if (c != 0) parRang[t.CelluleDuLieu(c - 1)] += t.Altitudes[(j / TerrainDeCarte.TEXELS_PAR_RELIEF) * t.LargeurDuRelief + i / TerrainDeCarte.TEXELS_PAR_RELIEF];
                }
            var sommes = new Dictionary<string, double>(); var comptes = new Dictionary<string, int>();
            for (int r = 0; r < servies; r++) {
                string classe = Carte.Cellules[r].Relief; Assert.IsNotNull(classe, "cellule " + Carte.Cellules[r].CellId + " sans relief servi");
                sommes.TryGetValue(classe, out double s); comptes.TryGetValue(classe, out int n); sommes[classe] = s + parRang[r]; comptes[classe] = n + t.TexelsDe(r);
            }
            string[] ordre = new[] { "marais", "plaine", "colline", "montagne", "haute_montagne" }.Where(sommes.ContainsKey).ToArray();
            CollectionAssert.IsSubsetOf(sommes.Keys, new[] { "marais", "plaine", "colline", "montagne", "haute_montagne" }, "les classes servies ne sont pas celles que le terrain habille");
            Assert.GreaterOrEqual(ordre.Length, 4, "échantillon vide : l'extrait ne sert presque aucune classe");
            double[] moyennes = ordre.Select(c => sommes[c] / comptes[c]).ToArray();
            string lu = string.Join(", ", ordre.Select((c, k) => c + " " + moyennes[k].ToString("0.00")));
            TestContext.Out.WriteLine(lu);
            for (int k = 0; k + 1 < ordre.Length; k++) Assert.Less(moyennes[k], moyennes[k + 1], ordre[k] + " n'est pas plus bas que " + ordre[k + 1] + " : " + lu);
        }

        [Test] public void La_terre_emerge_la_mer_plonge_et_le_bord_est_au_fond() {
            TerrainDeCarte t = Terrain; int l = t.LargeurDuRelief, h = t.HauteurDuRelief, terres = 0, mers = 0, noyees = 0, emergees = 0, hors = 0, horsDuRas = 0; float cime = float.NegativeInfinity, creux = float.PositiveInfinity;
            for (int j = 0; j < h; j++)
                for (int i = 0; i < l; i++) {
                    float a = t.Altitudes[j * l + i]; if (a > cime) cime = a; if (a < creux) creux = a;
                    float x = t.Coin.x + (i + .5f) * t.PasDuRelief, z = t.Coin.y + (j + .5f) * t.PasDuRelief;
                    if (ATerre(t, i, j)) { terres++; if (!(a >= TerrainDeCarte.RIVAGE)) noyees++; }
                    else if (t.HorsCarteEn(x, z)) { hors++; if (a != TerrainDeCarte.RIVAGE) horsDuRas++; } // au-delà d'une coupe : au ras de l'eau, sans fond
                    else { mers++; if (!(a <= 0f)) emergees++; }
                }
            TestContext.Out.WriteLine("de " + creux + " à " + cime + " km de décor ; " + hors + " altitudes de mer hors de la carte");
            Assert.IsTrue(terres > 1000 && mers > 1000, terres + " altitudes à terre, " + mers + " en mer");
            Assert.AreEqual(0, noyees, "altitudes à terre sous le rivage"); Assert.AreEqual(0, emergees, "altitudes en mer au-dessus de l'eau");
            Assert.AreEqual(0, horsDuRas, "altitudes de mer hors de la carte qui ne sont pas au ras de l'eau");
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
            var montre = Stopwatch.StartNew(); TerrainDeCarte second = TerrainDeCarte.Lever(Carte, Formes); montre.Stop(); TerrainDeCarte t = Terrain;
            UnityEngine.Debug.Log("TERRAIN : " + Carte.Cellules.Count + " cellules et " + second.NombreDeLieux + " lieux levés en " + montre.ElapsedMilliseconds + " ms, "
                + second.Largeur + " × " + second.Hauteur + " texels au pas de " + second.Pas + " km, " + second.Separations + " morceaux de côtés");
            Assert.IsTrue(second.Largeur == t.Largeur && second.Hauteur == t.Hauteur && second.Pas == t.Pas && second.Coin == t.Coin);
            int ecarts = 0;
            for (int k = 0; k < second.Lieux.Count; k++) if (second.Lieux[k] != t.Lieux[k]) ecarts++;
            for (int k = 0; k < second.Altitudes.Count; k++) if (second.Altitudes[k] != t.Altitudes[k]) ecarts++;
            for (int k = 0; k < second.Sommets.Count; k++) if (second.Sommets[k] != t.Sommets[k]) ecarts++;
            for (int k = 0; k < second.Bords.Count; k++) if (second.Bords[k] != t.Bords[k]) ecarts++;
            Assert.AreEqual(0, ecarts, "texels, altitudes, sommets ou distances différents d'un levé à l'autre");
            Assert.AreEqual(t.Separations, second.Separations, "les deux levés ne séparent pas les mêmes côtés");
            // Les frontières aussi, pour les mêmes pays : la mesure se partage entre plusieurs fils sans dépendre de leur ordre.
            var pays = new int[t.NombreDeLieux]; for (int l = 0; l < pays.Length; l++) pays[l] = l % 7;
            byte[] un = new byte[second.Largeur * second.Hauteur], deux = new byte[un.Length]; t.Frontieres(pays, un, t.Tout); second.Frontieres(pays, deux, second.Tout);
            Assert.IsTrue(un.SequenceEqual(deux) && un.Any(c => c != TerrainDeCarte.AU_LOIN), "frontières différentes d'un levé à l'autre, ou aucune");
        }

        [Test] public void Le_maillage_couvre_le_rectangle_sous_le_plan_des_calques() {
            TerrainDeCarte t = Terrain; int m = TerrainDeCarte.TEXELS_PAR_MAILLE, nx = t.Largeur / m + 1, nz = t.Hauteur / m + 1;
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
            TerrainDeCarte t = LeveDe(Carre(1, 0, 0, 50000), Carre(2, 100000, 20000, 10)); PointCarte o = t.Origine;
            Assert.AreEqual(1f, t.Pas, "une petite carte se lève au pas minimal");
            Assert.AreEqual(2500, t.TexelsDe(0), "une terre de 50 km de côté, au pas d'un km");
            Assert.AreEqual(1, t.TexelsDe(1), "l'île n'a pas son texel");
            Assert.AreEqual(2, t.CelluleEn((float)((100005 - o.X) / 1000), (float)((20005 - o.Y) / 1000)), "le texel de l'île n'est pas sous l'île");
            Assert.AreEqual(1, t.CelluleEn((float)((25000 - o.X) / 1000), (float)((25000 - o.Y) / 1000)));
            Assert.AreEqual(0, t.CelluleEn((float)((75000 - o.X) / 1000), (float)((25000 - o.Y) / 1000)), "entre la terre et l'île, ce n'est pas la mer");
            Assert.AreEqual(2501, t.Lieux.Count(c => c != 0));
        }

        // Sans formes, ou sans la forme d'une cellule, d'un lieu ou d'un contour, aucun terrain ne se lève : la carte
        // ne retombe jamais sur le dessin des seules cellules.
        [Test] public void Une_carte_sans_terre_ou_sans_formes_n_a_pas_de_terrain() {
            var carte = new CarteLue(2, new[] { Carre(1, 0, 0, 50000), Carre(2, 50000, 0, 50000) }); FormesLues formes = FormesDeTest.UnLieuParCellule(carte);
            Assert.Throws<ArgumentNullException>(() => TerrainDeCarte.Lever(null, formes)); Assert.Throws<ArgumentNullException>(() => TerrainDeCarte.Lever(carte, null));
            StringAssert.Contains("une carte vide n'a aucun terrain", Assert.Throws<ArgumentException>(() => TerrainDeCarte.Lever(new CarteLue(0, new CelluleDeCarte[0]), formes)).Message);
            FormeDeCellule une = formes.Cellules[0], deux = formes.Cellules[1];
            StringAssert.Contains("des formes de 1 cellules pour une carte de 2", Assert.Throws<ArgumentException>(() => TerrainDeCarte.Lever(carte, new FormesLues(null, new[] { une }))).Message);
            var ailleurs = new FormeDeCellule(3, deux.Contour, deux.Lieux);
            StringAssert.Contains("cellule 2 : aucune forme servie", Assert.Throws<ArgumentException>(() => TerrainDeCarte.Lever(carte, new FormesLues(null, new[] { une, ailleurs }))).Message);
            var sansLieu = new FormeDeCellule(2, deux.Contour, new FormeDeLieu[0]);
            StringAssert.Contains("cellule 2 : aucun lieu", Assert.Throws<ArgumentException>(() => TerrainDeCarte.Lever(carte, new FormesLues(null, new[] { une, sansLieu }))).Message);
            var sansContour = new FormeDeCellule(2, deux.Contour, new[] { new FormeDeLieu(0, deux.Contour), new FormeDeLieu(1, new PolygoneDeCarte[0]) });
            StringAssert.Contains("cellule 2, lieu 1 : aucun contour", Assert.Throws<ArgumentException>(() => TerrainDeCarte.Lever(carte, new FormesLues(null, new[] { une, sansContour }))).Message);
            // Le numéro d'un lieu tient dans un texel de seize bits, le zéro étant la mer.
            var foule = new FormeDeCellule(2, deux.Contour, Enumerable.Range(0, ushort.MaxValue - 1).Select(r => new FormeDeLieu(r, deux.Contour)));
            StringAssert.Contains(ushort.MaxValue + " lieux", Assert.Throws<ArgumentException>(() => TerrainDeCarte.Lever(carte, new FormesLues(null, new[] { une, foule }))).Message);
        }

        [Test] public void Un_relief_non_servi_se_dessine_en_plaine() {
            TerrainDeCarte Leve(string relief) => LeveDe(Carre(1, 0, 0, 200000, relief));
            TerrainDeCarte plaine = Leve("plaine"), sans = Leve(null), inconnue = Leve("lagune"), montagne = Leve("montagne"), marais = Leve("marais");
            Assert.AreEqual(plaine.Altitudes.Count, sans.Altitudes.Count);
            int ecarts = 0;
            for (int k = 0; k < plaine.Altitudes.Count; k++) if (plaine.Altitudes[k] != sans.Altitudes[k] || plaine.Altitudes[k] != inconnue.Altitudes[k]) ecarts++;
            Assert.AreEqual(0, ecarts, "un relief absent ou inconnu ne se lève pas comme une plaine");
            double basse = MoyenneATerre(marais), moyenne = MoyenneATerre(plaine), haute = MoyenneATerre(montagne);
            Assert.IsTrue(basse < moyenne && moyenne < haute, "marais " + basse + ", plaine " + moyenne + ", montagne " + haute);
            // La classe ne change que le relief : la terre est la même.
            for (int k = 0; k < plaine.Lieux.Count; k++) if (plaine.Lieux[k] != montagne.Lieux[k]) ecarts++;
            Assert.AreEqual(0, ecarts, "la classe de relief a déplacé la terre");
        }

        // Deux terres de 10 km accolées : la 1 de x = -10 à 0, la 2 de 0 à 10, de z = -5 à 5, les centres des texels
        // d'un km aux demi-entiers. Une distance se lit au texel, à la précision de son octet : 0,1 km suffit.
        [Test] public void Les_bords_et_la_cote_se_mesurent_aux_cotes_servis() {
            TerrainDeCarte t = LeveDe(Carre(1, 0, 0, 10000), Carre(2, 10000, 0, 10000)); float portee = TerrainDeCarte.PORTEE_DES_BORDS_KM;
            Assert.IsTrue(t.Pas == 1f && t.Origine.X == 10000 && t.Origine.Y == 5000, "le cas n'est pas celui qu'on croit : pas " + t.Pas);
            Assert.IsTrue(t.CelluleEn(-.5f, .5f) == 1 && t.CelluleEn(.5f, .5f) == 2 && t.CelluleEn(-.5f, 5.5f) == 0 && t.TexelsDe(0) == 100 && t.TexelsDe(1) == 100, "les terres ne sont pas à leur place");
            Assert.Greater(t.Separations, 0, "aucun côté séparé"); Assert.AreEqual(2 * t.Largeur * t.Hauteur, t.Bords.Count);
            // Le côté commun se voit des deux terres ; le rivage est aussi le bord de sa cellule.
            Assert.AreEqual(.5f, t.BordEn(-.5f, .5f), .1f); Assert.AreEqual(.5f, t.BordEn(.5f, .5f), .1f); Assert.AreEqual(3.5f, t.BordEn(-3.5f, .5f), .1f); Assert.AreEqual(.5f, t.BordEn(-9.5f, .5f), .1f);
            // La côte : le côté commun n'en est pas une.
            Assert.AreEqual(4.5f, t.CoteEn(-.5f, .5f), .1f, "le côté commun compte pour une côte"); Assert.AreEqual(4.5f, t.CoteEn(-3.5f, .5f), .1f); Assert.AreEqual(.5f, t.CoteEn(-9.5f, .5f), .1f);
            // En mer, les deux distances sont celle du rivage, jusqu'à leur portée.
            Assert.AreEqual(.5f, t.BordEn(-10.5f, .5f), .1f); Assert.AreEqual(.5f, t.CoteEn(-10.5f, .5f), .1f); Assert.AreEqual(3.5f, t.BordEn(-13.5f, .5f), .1f); Assert.AreEqual(3.5f, t.CoteEn(-13.5f, .5f), .1f);
            Assert.IsTrue(t.BordEn(-30.5f, .5f) == portee && t.CoteEn(-30.5f, .5f) == portee, "au large, la distance ne sature pas à sa portée");
            Assert.IsTrue(t.BordEn(t.Coin.x - 1, 0) == portee && t.CoteEn(t.Coin.x - 1, 0) == portee, "hors du rectangle, la distance n'est pas la portée");
        }

        // Une cellule de 20 km sur 10 coupée en deux lieux, et une voisine d'un seul lieu : en x local, l'ouest de la
        // première de -15 à -5, son est de -5 à 5, la voisine de 5 à 15. Le côté commun des deux lieux est un bord,
        // jamais une côte ; il devient une frontière quand ils ne sont pas du même pays, et seulement alors.
        [Test] public void Les_lieux_d_une_cellule_ont_leurs_bords_et_leurs_frontieres() {
            var carte = new CarteLue(2, new[] { Carre(1, 0, 0, 20000, null, 10000), Carre(2, 20000, 0, 10000) });
            var formes = new FormesLues(null, new[] {
                new FormeDeCellule(1, carte.Cellules[0].Contour, new[] { new FormeDeLieu(0, Rectangle(0, 0, 10000, 10000)), new FormeDeLieu(1, Rectangle(10000, 0, 20000, 10000)) }),
                new FormeDeCellule(2, carte.Cellules[1].Contour, new[] { new FormeDeLieu(0, carte.Cellules[1].Contour) }) });
            TerrainDeCarte t = TerrainDeCarte.Lever(carte, formes);
            Assert.IsTrue(t.Pas == 1f && t.Origine.X == 15000 && t.Origine.Y == 5000, "le cas n'est pas celui qu'on croit : pas " + t.Pas);
            Assert.IsTrue(t.NombreDeLieux == 3 && t.LieuxDe(0) == 2 && t.LieuxDe(1) == 1 && t.PremierLieuDe(1) == 2 && t.CelluleDuLieu(1) == 0 && t.CelluleDuLieu(2) == 1 && t.RangDuLieu(1) == 1 && t.LieuDe(0, 1) == 1);
            Assert.IsTrue(t.LieuEn(-5.5f, .5f) == 1 && t.LieuEn(-4.5f, .5f) == 2 && t.LieuEn(5.5f, .5f) == 3, "les lieux ne sont pas à leur place");
            Assert.IsTrue(t.CelluleEn(-5.5f, .5f) == 1 && t.CelluleEn(-4.5f, .5f) == 1 && t.CelluleEn(5.5f, .5f) == 2, "les lieux ne sont pas dans leur cellule");
            Assert.IsTrue(t.TexelsDuLieu(0) == 100 && t.TexelsDuLieu(1) == 100 && t.TexelsDe(0) == 200 && t.TexelsDe(1) == 100);
            RectInt cellule = t.ZoneDe(0), ouest = t.ZoneDuLieu(0), est = t.ZoneDuLieu(1);
            Assert.IsTrue(cellule.xMin <= Math.Min(ouest.xMin, est.xMin) && cellule.xMax >= Math.Max(ouest.xMax, est.xMax) && ouest.xMax < est.xMax, "la zone de la cellule ne tient pas celles de ses lieux");
            // Le côté commun des deux lieux, en x = -5 : un bord vu des deux, pas une côte.
            Assert.AreEqual(.5f, t.BordEn(-5.5f, .5f), .1f); Assert.AreEqual(.5f, t.BordEn(-4.5f, .5f), .1f); Assert.AreEqual(2.5f, t.BordEn(-7.5f, .5f), .1f);
            Assert.AreEqual(4.5f, t.CoteEn(-5.5f, .5f), .1f, "le côté commun de deux lieux compte pour une côte");
            var champ = new byte[t.Largeur * t.Hauteur];
            t.Frontieres(new[] { 1, 2, 2 }, champ, t.Tout);
            Assert.AreEqual(.5f, t.FrontiereEn(champ, -5.5f, .5f), .1f, "deux lieux d'une cellule à deux pays n'ont pas de frontière"); Assert.AreEqual(.5f, t.FrontiereEn(champ, -4.5f, .5f), .1f);
            Assert.AreEqual(9.5f, t.FrontiereEn(champ, 4.5f, .5f), .1f, "une frontière entre l'est de la cellule et sa voisine du même pays");
            t.Frontieres(new[] { 1, 1, 2 }, champ, t.Tout);
            Assert.AreEqual(10.5f, t.FrontiereEn(champ, -5.5f, .5f), .1f, "une frontière entre deux lieux du même pays"); Assert.AreEqual(.5f, t.FrontiereEn(champ, 4.5f, .5f), .1f);
            t.Frontieres(new[] { 1, 1, 1 }, champ, t.Tout); Assert.IsTrue(champ.All(c => c == TerrainDeCarte.AU_LOIN), "une frontière dans un même pays");
        }

        // Le service simplifie chaque contour à part : deux terres voisines peuvent laisser entre elles une fente plus
        // étroite que FENTE_KM, qui n'est pas une mer. Elle va à la terre servie la dernière, et il n'y a qu'un trait.
        [Test] public void Une_fente_etroite_se_comble_une_plus_large_reste_la_mer() {
            // Une fente d'un km : la 1 de x = -10,5 à -0,5, la 2 de 0,5 à 10,5 ; en x, les centres des texels sont aux entiers.
            TerrainDeCarte t = LeveDe(Carre(1, 0, 0, 10000), Carre(2, 11000, 0, 10000));
            Assert.IsTrue(t.Pas == 1f && t.Origine.X == 10500, "le cas n'est pas celui qu'on croit");
            Assert.IsTrue(t.CelluleEn(-1f, .5f) == 1 && t.CelluleEn(0f, .5f) == 2 && t.CelluleEn(0f, -3.5f) == 2 && t.CelluleEn(1f, .5f) == 2, "la fente n'est pas comblée par la seconde terre");
            // Les deux texels d'embouchure sont à l'équerre des deux terres : la terre qui comble en a de 110 à 112.
            Assert.AreEqual(100, t.TexelsDe(0)); Assert.IsTrue(t.TexelsDe(1) >= 110 && t.TexelsDe(1) <= 112, t.TexelsDe(1) + " texels pour la terre qui comble");
            Assert.AreEqual(.5f, t.BordEn(0f, .5f), .1f, "le trait n'est pas au côté de la première terre"); Assert.AreEqual(.5f, t.BordEn(-1f, .5f), .1f);
            Assert.AreEqual(4.5f, t.CoteEn(0f, .5f), .1f, "la fente comblée garde une côte");
            // Une fente de 4 km : la 1 de x = -12 à -2, la 2 de 2 à 12. Elle reste la mer, entre ses deux rivages.
            t = LeveDe(Carre(1, 0, 0, 10000), Carre(2, 14000, 0, 10000));
            Assert.IsTrue(t.CelluleEn(-1.5f, .5f) == 0 && t.CelluleEn(.5f, .5f) == 0 && t.TexelsDe(0) == 100 && t.TexelsDe(1) == 100, "une fente de 4 km a été comblée");
            Assert.AreEqual(.5f, t.CoteEn(-1.5f, .5f), .1f); Assert.AreEqual(.5f, t.CoteEn(-2.5f, .5f), .1f);
        }

        // Deux contours qui se recouvrent sur 2 km : la 1 de x = -9 à 1, la 2 de -1 à 9. La première servie garde le
        // recouvrement, et le seul trait est à son côté.
        [Test] public void Sous_deux_contours_le_premier_lieu_servi_fait_foi() {
            TerrainDeCarte t = LeveDe(Carre(1, 0, 0, 10000), Carre(2, 8000, 0, 10000));
            Assert.IsTrue(t.Pas == 1f && t.Origine.X == 9000, "le cas n'est pas celui qu'on croit");
            Assert.IsTrue(t.CelluleEn(-.5f, .5f) == 1 && t.CelluleEn(.5f, .5f) == 1 && t.CelluleEn(1.5f, .5f) == 2, "le recouvrement n'est pas à la première terre");
            Assert.IsTrue(t.TexelsDe(0) == 100 && t.TexelsDe(1) == 80, t.TexelsDe(0) + " et " + t.TexelsDe(1) + " texels");
            Assert.AreEqual(.5f, t.BordEn(.5f, .5f), .1f, "le trait n'est pas au côté de la première terre"); Assert.AreEqual(.5f, t.BordEn(1.5f, .5f), .1f);
            Assert.AreEqual(1.5f, t.BordEn(-.5f, .5f), .1f, "le côté recouvert de la seconde terre fait un second trait");
        }

        // Les frontières des deux terres accolées, selon leurs pays : le côté commun en est une quand les pays
        // diffèrent ; le rivage, jamais.
        [Test] public void Une_frontiere_separe_deux_pays_voisins_jamais_la_terre_de_la_mer() {
            TerrainDeCarte t = LeveDe(Carre(1, 0, 0, 10000), Carre(2, 10000, 0, 10000)); var champ = new byte[t.Largeur * t.Hauteur]; float loin = TerrainDeCarte.PORTEE_DES_FRONTIERES_KM;
            t.Frontieres(new[] { 1, 1 }, champ, t.Tout); Assert.IsTrue(champ.All(c => c == TerrainDeCarte.AU_LOIN), "une frontière dans un même pays");
            t.Frontieres(new[] { 1, 2 }, champ, t.Tout);
            foreach (float x in new[] { -3.5f, -.5f, .5f, 3.5f }) Assert.AreEqual(Mathf.Abs(x), t.FrontiereEn(champ, x, .5f), .1f, "en x = " + x);
            Assert.AreEqual(9.5f, t.FrontiereEn(champ, -9.5f, .5f), .1f, "le rivage compte pour une frontière");
            Assert.IsTrue(t.FrontiereEn(champ, .5f, 5.5f) == loin && t.FrontiereEn(champ, -10.5f, .5f) == loin && t.FrontiereEn(champ, t.Coin.x - 1, 0) == loin, "une frontière est mesurée en mer");
            // Une terre sans pays (0) a une frontière avec celle d'un pays ; une terre que le terrain ne dessine pas (-1) n'en fait aucune.
            t.Frontieres(new[] { 0, 2 }, champ, t.Tout); Assert.AreEqual(.5f, t.FrontiereEn(champ, -.5f, .5f), .1f);
            t.Frontieres(new[] { 0, 0 }, champ, t.Tout); Assert.IsTrue(champ.All(c => c == TerrainDeCarte.AU_LOIN), "une frontière entre deux terres sans pays");
            t.Frontieres(new[] { -1, 2 }, champ, t.Tout); Assert.IsTrue(champ.All(c => c == TerrainDeCarte.AU_LOIN), "une frontière avec une terre retirée");
            StringAssert.Contains("un pays par lieu servi", Assert.Throws<ArgumentException>(() => t.Frontieres(new[] { 1 }, champ, t.Tout)).Message);
            StringAssert.Contains("un pays par lieu servi", Assert.Throws<ArgumentException>(() => t.Frontieres(null, champ, t.Tout)).Message);
            StringAssert.Contains("un octet par texel", Assert.Throws<ArgumentException>(() => t.Frontieres(new[] { 1, 2 }, new byte[3], t.Tout)).Message);
        }

        // La cellule de Pampelune est à la Navarre, et une partie de ses lieux à la Castille (`autres_pays` de `/terres`).
        // Chaque lieu au pays que `/terres` lui donne : une frontière sépare deux lieux voisins de pays différents dans
        // cette cellule, et aucune ne passe entre deux lieux du même pays, où qu'ils soient. Ce qui est loin de tout
        // lieu d'un autre pays (à plus de la portée, et de deux texels) n'a aucune frontière mesurée.
        [Test] public void Une_frontiere_passe_dans_la_cellule_partagee_et_jamais_entre_deux_lieux_du_meme_pays() {
            TerrainDeCarte t = Terrain; int[] pays = FormesDeTest.PaysDesLieux(t, Carte, FormesDeTest.TerresOuest); int rang = RangDe(FormesDeTest.PAMPELUNE);
            var paysDePampelune = Enumerable.Range(t.PremierLieuDe(rang), t.LieuxDe(rang)).Select(l => pays[l]).Distinct().ToArray();
            Assert.GreaterOrEqual(paysDePampelune.Length, 2, "échantillon vide : la cellule de Pampelune n'est qu'à un pays");
            var champ = new byte[t.Largeur * t.Hauteur]; t.Frontieres(pays, champ, t.Tout);
            int rayon = Mathf.CeilToInt(TerrainDeCarte.PORTEE_DES_FRONTIERES_KM / t.Pas) + 3, separees = 0, malSeparees = 0, loinDeTout = 0, fausses = 0;
            int Pays(int k) => t.Lieux[k] == 0 ? -1 : pays[t.Lieux[k] - 1];
            bool SeulPays(int i, int j, int p) {
                for (int dj = -rayon; dj <= rayon; dj++)
                    for (int di = -rayon; di <= rayon; di++) {
                        int vi = i + di, vj = j + dj; if (vi < 0 || vj < 0 || vi >= t.Largeur || vj >= t.Hauteur) continue;
                        int q = Pays(vj * t.Largeur + vi); if (q >= 0 && q != p) return false;
                    }
                return true;
            }
            for (int j = 0; j < t.Hauteur; j++)
                for (int i = 0; i < t.Largeur; i++) {
                    int k = j * t.Largeur + i, ici = t.Lieux[k]; if (ici == 0) continue;
                    for (int v = 0; v < 2; v++) {
                        int vi = i + 1 - v, vj = j + v; if (vi >= t.Largeur || vj >= t.Hauteur) continue;
                        int kv = vj * t.Largeur + vi, la = t.Lieux[kv]; if (la == 0 || la == ici) continue;
                        if (pays[ici - 1] != pays[la - 1]) {
                            if (t.CelluleDuLieu(ici - 1) != rang || t.CelluleDuLieu(la - 1) != rang) continue;
                            separees++; float x = t.Coin.x + (i + 0.5f) * t.Pas, z = t.Coin.y + (j + 0.5f) * t.Pas, xv = t.Coin.x + (vi + 0.5f) * t.Pas, zv = t.Coin.y + (vj + 0.5f) * t.Pas;
                            if (Mathf.Max(t.FrontiereEn(champ, x, z), t.FrontiereEn(champ, xv, zv)) > 2f * t.Pas) malSeparees++;
                        } else if (SeulPays(i, j, pays[ici - 1])) { loinDeTout++; if (champ[k] != TerrainDeCarte.AU_LOIN || champ[kv] != TerrainDeCarte.AU_LOIN) fausses++; }
                    }
                }
            TestContext.Out.WriteLine(paysDePampelune.Length + " pays dans la cellule de Pampelune ; " + separees + " changements de pays entre ses lieux, " + malSeparees + " sans frontière ; "
                + loinDeTout + " bords entre deux lieux du même pays loin de tout autre, " + fausses + " avec une frontière");
            Assert.Greater(separees, 50, "échantillon vide : aucun changement de pays dans la cellule de Pampelune");
            Assert.AreEqual(0, malSeparees, "deux lieux de pays différents de la cellule de Pampelune sans frontière entre eux");
            Assert.Greater(loinDeTout, 1000, "échantillon vide : aucun bord entre deux lieux du même pays");
            Assert.AreEqual(0, fausses, "une frontière entre deux lieux du même pays");
            // Tous les lieux à un seul pays : aucune frontière, ni entre les cellules ni dans aucune.
            t.Frontieres(Enumerable.Repeat(1, t.NombreDeLieux).ToArray(), champ, t.Tout);
            Assert.IsTrue(champ.All(c => c == TerrainDeCarte.AU_LOIN), "une frontière entre deux lieux du même pays");
        }

        // Quand un lieu change de pays, il suffit de mesurer de nouveau sa zone : le champ est celui d'une mesure entière.
        [Test] public void Mesurer_la_zone_d_un_lieu_vaut_tout_mesurer() {
            // Trois terres de 60 km en ligne : la zone de celle du milieu ne couvre pas tout le terrain.
            TerrainDeCarte t = LeveDe(Carre(1, 0, 0, 60000), Carre(2, 60000, 0, 60000), Carre(3, 120000, 0, 60000)); RectInt zone = t.ZoneDe(1);
            Assert.IsTrue(zone.width < t.Largeur && zone.width > 0 && zone.height > 0, "la zone de la terre du milieu couvre tout : l'échantillon ne juge rien");
            var partiel = new byte[t.Largeur * t.Hauteur]; var entier = new byte[partiel.Length];
            t.Frontieres(new[] { 1, 1, 2 }, partiel, t.Tout); t.Frontieres(new[] { 1, 2, 2 }, partiel, zone); t.Frontieres(new[] { 1, 2, 2 }, entier, t.Tout);
            Assert.IsTrue(partiel.SequenceEqual(entier), "la mesure de la zone ne vaut pas la mesure entière");
            Assert.IsTrue(entier.Any(c => c != TerrainDeCarte.AU_LOIN), "aucune frontière mesurée");
            // Sur la carte servie : chaque lieu au pays que `/terres` lui donne, puis un lieu d'une frontière change de pays.
            t = Terrain; int[] pays = FormesDeTest.PaysDesLieux(t, Carte, FormesDeTest.TerresOuest); int nombre = pays.Max();
            var avant = new byte[t.Largeur * t.Hauteur]; var montre = Stopwatch.StartNew(); t.Frontieres(pays, avant, t.Tout); montre.Stop();
            int k0 = Array.FindIndex(avant, c => c < 20); Assert.GreaterOrEqual(k0, 0, "aucune frontière sur la carte servie");
            int lieu = t.Lieux[k0] - 1; Assert.GreaterOrEqual(lieu, 0, "une frontière est mesurée en mer"); pays[lieu] = pays[lieu] % nombre + 1;
            partiel = (byte[])avant.Clone(); var chrono = Stopwatch.StartNew(); t.Frontieres(pays, partiel, t.ZoneDuLieu(lieu)); chrono.Stop();
            entier = new byte[avant.Length]; t.Frontieres(pays, entier, t.Tout);
            TestContext.Out.WriteLine(nombre + " pays ; frontières des lieux servis mesurées en " + montre.ElapsedMilliseconds + " ms, la zone d'un lieu en " + chrono.ElapsedMilliseconds + " ms");
            Assert.IsTrue(partiel.SequenceEqual(entier), "sur la carte servie, la mesure de la zone d'un lieu ne vaut pas la mesure entière");
            Assert.IsFalse(partiel.SequenceEqual(avant), "le changement de pays n'a déplacé aucune frontière : l'échantillon ne juge rien");
        }

        [Test] public void La_zone_d_un_lieu_et_celle_de_sa_cellule_contiennent_tous_ses_texels() {
            TerrainDeCarte t = Terrain; int dehors = 0, horsCellule = 0, vus = 0;
            Assert.AreEqual(new RectInt(0, 0, t.Largeur, t.Hauteur), t.Tout);
            var zones = new RectInt[t.NombreDeLieux]; for (int l = 0; l < zones.Length; l++) zones[l] = t.ZoneDuLieu(l);
            var cellules = new RectInt[Carte.Cellules.Count]; for (int r = 0; r < cellules.Length; r++) cellules[r] = t.ZoneDe(r);
            bool Hors(RectInt z, int i, int j) => i < z.xMin || i >= z.xMax || j < z.yMin || j >= z.yMax;
            for (int j = 0; j < t.Hauteur; j++)
                for (int i = 0; i < t.Largeur; i++) {
                    int c = t.Lieux[j * t.Largeur + i]; if (c == 0) continue;
                    vus++; if (Hors(zones[c - 1], i, j)) dehors++; if (Hors(cellules[t.CelluleDuLieu(c - 1)], i, j)) horsCellule++;
                }
            Assert.Greater(vus, 100000, "aucune terre : l'échantillon ne juge rien");
            Assert.AreEqual(0, dehors, "texels hors de la zone de leur lieu"); Assert.AreEqual(0, horsCellule, "texels hors de la zone de leur cellule");
            // Une zone est à la taille de son lieu : mesurer celle d'un lieu coûte bien moins que tout mesurer.
            int petites = zones.Count(z => z.width < t.Largeur / 10 && z.height < t.Hauteur / 10);
            Assert.Greater(petites, zones.Length / 2, "les zones des lieux couvrent le terrain entier");
        }

        // L'octet d'une distance : zéro sur le trait, la portée au plus loin, et un pas plus fin près du trait, où le shader pose son bord.
        [Test] public void Une_distance_se_code_plus_finement_pres_du_trait() {
            float p = TerrainDeCarte.PORTEE_DES_FRONTIERES_KM;
            Assert.IsTrue(TerrainDeCarte.Distance(0, p) == 0f && TerrainDeCarte.Distance(TerrainDeCarte.AU_LOIN, p) == p, "les bornes du code ne sont pas zéro et la portée");
            for (int c = 1; c <= 255; c++) Assert.Greater(TerrainDeCarte.Distance((byte)c, p), TerrainDeCarte.Distance((byte)(c - 1), p), "code " + c);
            Assert.Less(TerrainDeCarte.Distance(1, p) - TerrainDeCarte.Distance(0, p), TerrainDeCarte.Distance(255, p) - TerrainDeCarte.Distance(254, p));
            Assert.Less(TerrainDeCarte.Distance(32, p) - TerrainDeCarte.Distance(31, p), .02f, "à 250 m du trait, le pas du code dépasse 20 m");
        }

        // Le milieu d'un côté coupé, en mètres EPSG:3035, et vers la terre : le côté de la normale où le terrain a de la terre.
        private static (double x, double y) EnMetres(TerrainDeCarte t, float x, float z) => (t.Origine.X + 1000.0 * x, t.Origine.Y + 1000.0 * z);
        private static bool Dans((double x, double y) p, double x0, double x1, double y0, double y1) => p.x >= x0 && p.x <= x1 && p.y >= y0 && p.y <= y1;
        // L'est de l'Anatolie, la pointe du Sinaï et le sud de l'Égypte : là où la carte figée de l'Europe coupe la terre en ligne droite.
        private static readonly (string nom, double x0, double x1, double y0, double y1)[] COUPES = {
            ("est de l'Anatolie", 6340000, 6520000, 1880000, 2440000), ("sud de l'Égypte", 5900000, 6500000, 990000, 1070000) };
        // La côte atlantique du Portugal et celle de la Bretagne, qui sont des rivages.
        private static readonly (string nom, double x0, double x1, double y0, double y1)[] RIVAGES = {
            ("côte atlantique du Portugal", 2600000, 2900000, 1800000, 2450000), ("Bretagne", 3100000, 3450000, 2720000, 2960000) };

        // Sur la carte figée de toute l'Europe, les côtés qui coupent la terre sont trouvés à l'est de l'Anatolie et au sud
        // de l'Égypte, et aucun côté de la côte atlantique du Portugal ni de la Bretagne ne l'est.
        [Test] public void Les_coupes_de_la_carte_sont_trouvees_et_aucun_rivage_n_en_est_une() {
            TerrainDeCarte t = EuropeDeTest.TerrainEurope; Assert.IsNotEmpty(t.Coupes, "aucune coupe : l'échantillon ne juge rien");
            foreach (var (nom, x0, x1, y0, y1) in COUPES) {
                int trouves = t.Coupes.Count(c => Dans(EnMetres(t, (c.x + c.z) / 2f, (c.y + c.w) / 2f), x0, x1, y0, y1));
                Assert.Greater(trouves, 0, nom + " : aucune coupe trouvée");
            }
            // Les côtés servis des rivages : l'échantillon n'est pas vide, et aucun n'est une coupe.
            foreach (var (nom, x0, x1, y0, y1) in RIVAGES) {
                int cotes = EuropeDeTest.CarteEurope.Cellules.SelectMany(c => c.Contour).SelectMany(p => p.Exterieur.Zip(p.Exterieur.Skip(1), (a, b) => (a, b)))
                    .Count(s => Dans(((s.a.X + s.b.X) / 2, (s.a.Y + s.b.Y) / 2), x0, x1, y0, y1));
                Assert.Greater(cotes, 5, nom + " : échantillon vide");
                var coupees = t.Coupes.Where(c => Dans(EnMetres(t, (c.x + c.z) / 2f, (c.y + c.w) / 2f), x0, x1, y0, y1)).ToList();
                Assert.IsEmpty(coupees, nom + " : " + coupees.Count + " côtés de rivage pris pour une coupe");
            }
        }

        // Au-delà d'une coupe, la mer est hors de la carte ; au large d'un rivage, elle est la mer. La terre ne plonge pas vers
        // la coupe comme vers une côte : à quelques km d'elle, elle a encore sa hauteur ; à autant d'un rivage, elle est au ras de l'eau.
        [Test] public void La_mer_au_dela_d_une_coupe_est_hors_de_la_carte_et_la_terre_n_y_plonge_pas() {
            TerrainDeCarte t = EuropeDeTest.TerrainEurope; int jugees = 0;
            foreach (Vector4 c in t.Coupes.Where(c => Dans(EnMetres(t, (c.x + c.z) / 2f, (c.y + c.w) / 2f), COUPES[0].x0, COUPES[0].x1, COUPES[0].y0, COUPES[0].y1))) {
                Vector2 a = new Vector2(c.x, c.y), b = new Vector2(c.z, c.w), milieu = (a + b) / 2f, normale = new Vector2(b.y - a.y, a.x - b.x).normalized;
                if (t.CelluleEn(milieu.x + 5f * normale.x, milieu.y + 5f * normale.y) == 0) normale = -normale; // vers la terre
                Vector2 dedans = milieu + 4f * normale, dehors = milieu - 20f * normale;
                if ((a - b).magnitude < 20f || t.CelluleEn(dedans.x, dedans.y) == 0) continue;
                Assert.IsTrue(t.HorsCarteEn(dehors.x, dehors.y), "à 20 km au-delà de la coupe " + c + ", la mer n'est pas hors de la carte");
                Assert.IsFalse(t.HorsCarteEn(dedans.x, dedans.y), "la terre en deçà de la coupe est hors de la carte");
                Assert.Greater(t.Altitude(dedans.x, dedans.y), .5f, "à 4 km de la coupe " + c + ", la terre plonge vers elle comme vers une côte");
                jugees++;
            }
            Assert.Greater(jugees, 0, "échantillon vide : aucune coupe de l'est de l'Anatolie jugée");
            // Contre-épreuve : au large de Lisbonne, la mer est la mer, et la terre au bord du rivage est au ras de l'eau.
            PointCarte o = t.Origine; Vector2 large = new Vector2((float)((2600000 - o.X) / 1000), (float)((1940000 - o.Y) / 1000));
            Assert.AreEqual(0, t.CelluleEn(large.x, large.y), "échantillon faussé : le large de Lisbonne est à terre");
            Assert.IsFalse(t.HorsCarteEn(large.x, large.y), "la mer au large de Lisbonne est prise pour hors de la carte");
            int rivages = 0, basses = 0;
            for (float x = large.x; x < large.x + 150f; x += 0.5f) {
                if (t.CelluleEn(x, large.y) == 0) continue;
                rivages++; if (t.Altitude(x + 1f, large.y) < .4f) basses++; break;
            }
            Assert.IsTrue(rivages == 1 && basses == 1, "à 1 km du rivage portugais, la terre n'est pas au ras de l'eau");
        }
    }
}
