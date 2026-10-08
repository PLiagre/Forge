using System;
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEngine;

namespace Forge.Pont.Tests
{
    // Lot #541 — un polygone de la carte, trous compris, devient des triangles posés à plat, en km autour
    // d'une origine. Les polygones sont des littéraux en mètres : 10196 de `/carte` seed 0, et deux formes
    // synthétiques (un nœud qui se croise, un trou qui touche l'extérieur par un sommet).
    public sealed class TriangulationDeCarteTests
    {
        private static readonly PointCarte OrigineDeLaCarte = new PointCarte(4549691.5, 2747267.5);

        private static readonly double[] Ilot10196 = { 3255813, 2017207, 3258432, 2014942, 3252950, 2017349, 3255813, 2017207 };
        private static readonly double[] Exterieur10196 = { 3260904, 2014373, 3258233, 2018288, 3248052, 2019499, 3178677, 2049953,
            3214016, 2181858, 3242818, 2196329, 3344599, 2164419, 3381106, 2073504, 3289024, 2001514, 3260904, 2014373 };
        private static readonly double[] Trou10196 = { 3256797, 2044933, 3258232, 2047203, 3254327, 2044953, 3245580, 2036516,
            3242003, 2025951, 3242985, 2024693, 3248295, 2030701, 3247211, 2035050, 3251211, 2041050, 3256797, 2044933 };

        // Un anneau écrit x0, y0, x1, y1… en mètres.
        private static List<PointCarte> Anneau(params double[] xy) =>
            Enumerable.Range(0, xy.Length / 2).Select(i => new PointCarte(xy[2 * i], xy[2 * i + 1])).ToList();

        private static PolygoneDeCarte Polygone(double[] exterieur, params double[][] trous) =>
            new PolygoneDeCarte(Anneau(exterieur), trous.Select(Anneau));

        private static (PolygoneDeCarte, PointCarte) Nomme(string nom)
        {
            switch (nom)
            {
                case "ilot 10196": return (Polygone(Ilot10196), OrigineDeLaCarte);
                case "troue 10196": return (Polygone(Exterieur10196, Trou10196), OrigineDeLaCarte);
                case "exterieur 10196": return (Polygone(Exterieur10196), OrigineDeLaCarte);
                case "noeud": return (Polygone(new double[] { 0, 0, 2000, 2000, 2000, 0, 0, 2000, 0, 0 }), new PointCarte(1000, 1000));
                case "trou au sommet":
                    return (Polygone(new double[] { 0, 0, 0, 2000, 0, 4000, 4000, 4000, 4000, 0, 0, 0 },
                        new double[] { 0, 2000, 2000, 1000, 2000, 3000, 0, 2000 }), new PointCarte(2000, 2000));
                default: throw new ArgumentException("polygone inconnu : " + nom);
            }
        }

        private static MaillageDePolygone Mailler(string nom) { var (polygone, origine) = Nomme(nom); return TriangulationDeCarte.Trianguler(polygone, origine); }

        // Le produit du filtre : > 0 quand le triangle est tourné vers le haut.
        private static double S(Vector3 p, Vector3 q, Vector3 r) => S(p, q, r.x, r.z);
        private static double S(Vector3 p, Vector3 q, double x, double z) =>
            ((double)q.z - p.z) * (x - p.x) - ((double)q.x - p.x) * (z - p.z);

        private static void Verifier(MaillageDePolygone maillage)
        {
            Assert.That(maillage.Triangles.Count, Is.EqualTo(maillage.Sommets.Count));
            Assert.That(maillage.Sommets.Count % 3, Is.EqualTo(0));
            Assert.That(maillage.Sommets.Count, Is.GreaterThan(0), "un maillage vide ne prouve rien");
            for (int i = 0; i < maillage.Triangles.Count; i++) Assert.That(maillage.Triangles[i], Is.EqualTo(i));
            Assert.That(maillage.Sommets.All(s => s.y == 0f), Is.True, "un sommet hors du plan Y = 0");
            for (int i = 0; i < maillage.Sommets.Count; i += 3)
                Assert.That(S(maillage.Sommets[i], maillage.Sommets[i + 1], maillage.Sommets[i + 2]), Is.GreaterThan(0), "triangle " + i / 3 + " pas tourné vers le haut");
        }

        private static double Aire(MaillageDePolygone maillage) =>
            Enumerable.Range(0, maillage.Sommets.Count / 3).Sum(k => S(maillage.Sommets[3 * k], maillage.Sommets[3 * k + 1], maillage.Sommets[3 * k + 2]) / 2);

        // Le nombre de triangles qui contiennent strictement le point (xM, yM), donné en mètres.
        private static int Couverture(MaillageDePolygone maillage, double xM, double yM, PointCarte origine)
        {
            double x = (xM - origine.X) / 1000, z = (yM - origine.Y) / 1000;
            IReadOnlyList<Vector3> s = maillage.Sommets;
            return Enumerable.Range(0, s.Count / 3).Count(k =>
                S(s[3 * k], s[3 * k + 1], x, z) > 0 && S(s[3 * k + 1], s[3 * k + 2], x, z) > 0 && S(s[3 * k + 2], s[3 * k], x, z) > 0);
        }

        // ---- SC2 à SC4 : les aires (10196 à 1e-4 près en relatif, les formes synthétiques à 1e-6 km²) --

        [TestCase("ilot 10196", 3.0563985, 1e-4 * 3.0563985, TestName = "Aire01_IlotDe10196")]
        [TestCase("troue 10196", 25868.261169, 1e-4 * 25868.261169, TestName = "Aire02_PolygoneTroueDe10196")]
        [TestCase("exterieur 10196", 25921.464329, 1e-4 * 25921.464329, TestName = "Aire03_ExterieurDe10196SansSonTrou")]
        [TestCase("noeud", 2.0, 1e-6, TestName = "Aire04_LeNoeudNEstPasCompteDeuxFois")]
        [TestCase("trou au sommet", 14.0, 1e-6, TestName = "Aire05_LeTrouAuSommetEstRetire")]
        public void LAireEstCelleDuPolygone(string nom, double attendue, double tolerance)
        {
            var maillage = Mailler(nom);
            Verifier(maillage);
            Assert.That(Aire(maillage), Is.EqualTo(attendue).Within(tolerance));
        }

        // Les points sont en mètres ; pour les formes synthétiques, ceux du brief (en km autour de
        // l'origine) sont convertis : origine + 1000 × km.
        [TestCase("ilot 10196", 3255732, 2016499, 1, TestName = "Couverture01_IlotCouvertUneFois")]
        [TestCase("ilot 10196", 3300000, 2100000, 0, TestName = "Couverture02_HorsDeLIlot")]
        [TestCase("troue 10196", 3244636, 2029118, 0, TestName = "Couverture03_LeTrouResteVide")]
        [TestCase("troue 10196", 3300000, 2100000, 1, TestName = "Couverture04_LePolygoneTroueEstCouvert")]
        [TestCase("troue 10196", 3255732, 2016499, 0, TestName = "Couverture05_LIlotNEstPasDansLePolygoneTroue")]
        [TestCase("exterieur 10196", 3244636, 2029118, 1, TestName = "Couverture06_SansLeTrouLePointEstCouvert")]
        [TestCase("noeud", 1000, 1500, 0, TestName = "Couverture07_NoeudAuDessusDuCroisement")]
        [TestCase("noeud", 1000, 500, 0, TestName = "Couverture08_NoeudAuDessousDuCroisement")]
        [TestCase("noeud", 500, 1100, 1, TestName = "Couverture09_NoeudLobeOuest")]
        [TestCase("noeud", 1500, 900, 1, TestName = "Couverture10_NoeudLobeEst")]
        [TestCase("trou au sommet", 1000, 2100, 0, TestName = "Couverture11_DansLeTrou")]
        [TestCase("trou au sommet", 1500, 2500, 0, TestName = "Couverture12_DansLeTrouPresDuBord")]
        [TestCase("trou au sommet", 500, 2500, 1, TestName = "Couverture13_EntreLeTrouEtLeBord")]
        [TestCase("trou au sommet", 50, 2500, 1, TestName = "Couverture14_LeCoinEntreLeTrouEtLeBord")]
        [TestCase("trou au sommet", 3000, 2400, 1, TestName = "Couverture15_ALEstDuTrou")]
        [TestCase("trou au sommet", 500, 500, 1, TestName = "Couverture16_SousLeTrou")]
        public void LaCouvertureEstCelleDuPolygone(string nom, double xM, double yM, int attendu)
        {
            var (polygone, origine) = Nomme(nom);
            var maillage = TriangulationDeCarte.Trianguler(polygone, origine);
            Verifier(maillage);
            Assert.That(Couverture(maillage, xM, yM, origine), Is.EqualTo(attendu));
        }

        // La rangée j = 9 (z = 0 exactement) est sur la ligne de coupe du croisement : un point qui y est
        // n'est strictement dans aucun triangle. Comme pour les autres points des tests, elle est écartée.
        [Test]
        public void LaGrilleDuNoeudEstCouverteUneFoisDansSesLobesEtJamaisAilleurs()
        {
            var (polygone, origine) = Nomme("noeud");
            var maillage = TriangulationDeCarte.Trianguler(polygone, origine);
            Verifier(maillage);
            var ecarts = new List<string>();
            int verifies = 0;
            for (int i = 0; i < 20; i++)
                for (int j = 0; j < 19; j++)
                {
                    double x = -0.95 + 0.1 * i, z = -0.9 + 0.1 * j;
                    if (z == 0) continue;
                    verifies++;
                    int attendu = Math.Abs(z) < Math.Abs(x) ? 1 : 0;
                    int compte = Couverture(maillage, 1000 + 1000 * x, 1000 + 1000 * z, origine);
                    if (compte != attendu) ecarts.Add("(" + x + " ; " + z + ") couvert " + compte + " fois");
                }
            Assert.That(verifies, Is.EqualTo(360), "la grille a perdu des points");
            Assert.That(ecarts, Is.Empty, ecarts.Count + " points sur " + verifies + " en écart : " + string.Join(", ", ecarts.Take(10)));
        }

        // ---- SC5 : les entrées refusées, le polygone plat, le calcul reproductible -----------------

        [Test]
        public void UnPolygoneNulEstRefuse() =>
            Assert.Throws<ArgumentNullException>(() => TriangulationDeCarte.Trianguler(null, OrigineDeLaCarte));

        [TestCase(double.NaN, 0, TestName = "Origine01_XNaNEstRefuse")]
        [TestCase(0, double.PositiveInfinity, TestName = "Origine02_YInfiniEstRefuse")]
        public void UneOrigineNonFinieEstRefusee(double x, double y) =>
            Assert.Throws<ArgumentOutOfRangeException>(() => TriangulationDeCarte.Trianguler(Polygone(Ilot10196), new PointCarte(x, y)));

        [Test]
        public void UnPolygonePlatRendUnMaillageVide()
        {
            var maillage = TriangulationDeCarte.Trianguler(Polygone(new double[] { 0, 0, 1000, 0, 2000, 0, 0, 0 }), new PointCarte(0, 0));
            Assert.That(maillage.Sommets.Count, Is.EqualTo(0));
            Assert.That(maillage.Triangles.Count, Is.EqualTo(0));
        }

        [Test]
        public void DeuxAppelsRendentLesMemesSommets()
        {
            var premier = Mailler("troue 10196");
            var second = Mailler("troue 10196");
            Verifier(premier);
            Assert.That(second.Sommets, Is.EqualTo(premier.Sommets).AsCollection);
        }
    }
}
