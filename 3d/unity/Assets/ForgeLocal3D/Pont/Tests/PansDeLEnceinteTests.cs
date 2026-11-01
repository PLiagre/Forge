using System;
using System.Linq;
using NUnit.Framework;

namespace Forge.Pont.Tests
{
    // Lot #925 — le contour bouclé de l'enceinte se découpe en une tour par sommet et des pans de 10 m au plus.
    public sealed class PansDeLEnceinteTests
    {
        private static EnceinteDuPlan Enceinte(params double[] xy) =>
            new EnceinteDuPlan(Enumerable.Range(0, xy.Length / 2).Select(i => new PointLocal(xy[2 * i], xy[2 * i + 1])).ToList(), true, 2, 19200, 1);
        private static void Piece(PieceDeLEnceinte p, NatureDePiece nature, int cote, int indice, double x, double y, double lacet, double longueur)
        {   Assert.IsTrue(p.Nature == nature && p.Cote == cote && p.Indice == indice, p.Nature + " " + p.Cote + "," + p.Indice);
            Assert.AreEqual(x, p.CentreX, 1e-9); Assert.AreEqual(y, p.CentreY, 1e-9); Assert.AreEqual(lacet, p.LacetDegres, 1e-9); Assert.AreEqual(longueur, p.LongueurM, 1e-9); }

        [Test]
        public void LeCarreSeDecoupeEnToursEtPans()
        {
            DecoupeDeLEnceinte d = PansDeLEnceinte.Decouper(Enceinte(-80, -80, 80, -80, 80, 80, -80, 80)); Assert.IsTrue(d.Presente && d.Absence == "" && d.Pieces.Count == 68, d.Absence + " " + d.Pieces.Count);
            double[] tours = { -80, -80, 45, 80, -80, 315, 80, 80, 225, -80, 80, 135 }, lacets = { 0, 270, 180, 90 };
            for (int q = 0; q < 68; q++)
            {
                PieceDeLEnceinte p = d.Pieces[q]; int i = q / 17, j = q % 17 - 1;
                if (j < 0) { Piece(p, NatureDePiece.Tour, i, 0, tours[3 * i], tours[3 * i + 1], tours[3 * i + 2], 7.2); Assert.AreEqual(0, p.AbscisseM); continue; }
                Assert.IsTrue(p.Nature == NatureDePiece.Pan && p.Cote == i && p.Indice == j, i + "," + j);
                Assert.AreEqual(9.55, p.LongueurM, 1e-9); Assert.AreEqual(8.375 + 9.55 * j, p.AbscisseM, 1e-9); Assert.AreEqual(lacets[i], p.LacetDegres, 1e-9);
            }
            Piece(d.Pieces[1], NatureDePiece.Pan, 0, 0, -71.625, -80, 0, 9.55);
            Piece(d.Pieces[16], NatureDePiece.Pan, 0, 15, 71.625, -80, 0, 9.55);
            Piece(d.Pieces[18], NatureDePiece.Pan, 1, 0, 80, -71.625, 270, 9.55);
        }

        [Test]
        public void LeSensEtLaTailleDuCarre()
        {
            DecoupeDeLEnceinte h = PansDeLEnceinte.Decouper(Enceinte(-80, 80, 80, 80, 80, -80, -80, -80)); Assert.IsTrue(h.Presente && h.Pieces.Count == 68, h.Absence);
            for (int j = 0; j < 16; j++) Piece(h.Pieces[1 + j], NatureDePiece.Pan, 0, j, -71.625 + 9.55 * j, 80, 180, 9.55);
            DecoupeDeLEnceinte c30 = PansDeLEnceinte.Decouper(Enceinte(-15, -15, 15, -15, 15, 15, -15, 15)); Assert.IsTrue(c30.Presente && c30.Pieces.Count == 16, c30.Pieces.Count + " pièces");
            for (int j = 0; j < 3; j++) Piece(c30.Pieces[1 + j], NatureDePiece.Pan, 0, j, -7.6 + 7.6 * j, -15, 0, 7.6);
            DecoupeDeLEnceinte c6 = PansDeLEnceinte.Decouper(Enceinte(-3, -3, 3, -3, 3, 3, -3, 3)); Assert.IsTrue(c6.Presente && c6.Pieces.Count == 4, c6.Pieces.Count + " pièces");
            for (int i = 0; i < 4; i++) Piece(c6.Pieces[i], NatureDePiece.Tour, i, 0, i == 1 || i == 2 ? 3 : -3, i < 2 ? -3 : 3, 45 + 270 * i % 360, 7.2);
        }

        [TestCase(new double[] { -80, -80, 80, -80, 80, -80, 80, 80, -80, 80 }, "côté 1 : longueur nulle")]
        [TestCase(new double[] { 0, 0, 10, 0, 20, 0 }, "contour plat")]
        [TestCase(new double[] { 0, 0, 40, 0, 40, 40, 40, 20 }, "sommet 2 : demi-tour")]
        [TestCase(new double[] { -80, -80, 80, -80, double.NaN, 80, -80, 80 }, "point 2 non fini")]
        public void UneDecoupeImpossibleEstAbsente(double[] xy, string attendu)
        {
            DecoupeDeLEnceinte d = PansDeLEnceinte.Decouper(Enceinte(xy)); Assert.IsTrue(!d.Presente && d.Pieces.Count == 0, d.Pieces.Count + " pièces"); StringAssert.Contains(attendu, d.Absence);
            Assert.Throws<ArgumentNullException>(() => PansDeLEnceinte.Decouper(null)); Assert.Throws<ArgumentNullException>(() => PansDeLEnceinte.Etape(null));
        }

        [TestCase(19200L, 1L, true, EtapeDuBatiment.Piquets)]
        [TestCase(19200L, 9599L, true, EtapeDuBatiment.Piquets)]
        [TestCase(19200L, 9600L, true, EtapeDuBatiment.Murs)]
        [TestCase(19201L, 9600L, true, EtapeDuBatiment.Piquets)]
        [TestCase(19201L, 9601L, true, EtapeDuBatiment.Murs)]
        [TestCase(19200L, 19200L, false, EtapeDuBatiment.Fini)]
        public void LEtapeSuitLaRegleDesBatiments(long requis, long fourni, bool enChantier, EtapeDuBatiment attendue)
        {
            var contour = Enceinte(-80, -80, 80, -80, 80, 80).Contour.ToList();
            Assert.AreEqual(attendue, PansDeLEnceinte.Etape(new EnceinteDuPlan(contour, enChantier, 2, requis, fourni)));
            Assert.AreEqual(attendue, LectureDuBatiment.Etape(new BatimentDuPlan(0, 0, "mur", contour, enChantier, requis, fourni)));
        }

        // Lot #926 — chaque porte servie se pose sur le mur, retire le pan qu'elle couvre et regarde dehors.
        private static readonly double[] C160 = { -80, -80, 80, -80, 80, 80, -80, 80 }, C160h = { -80, 80, 80, 80, 80, -80, -80, -80 }, C6 = { -3, -3, 3, -3, 3, 3, -3, 3 };
        private static PorteDuPlan[] Portes(params double[] xy) => Enumerable.Range(0, xy.Length / 2).Select(i => new PorteDuPlan(new PointLocal(xy[2 * i], xy[2 * i + 1]), "plan", 0, 4)).ToArray();
        private static DecoupeDeLEnceinte Ouvrir(double[] contour, params double[] portes)
        { DecoupeDeLEnceinte d = PansDeLEnceinte.Decouper(Enceinte(contour), Portes(portes)); Assert.IsTrue(d.Presente && d.Absence == "", d.Absence); return d; }
        private static bool Reste(DecoupeDeLEnceinte d, int cote, int indice) => d.Pieces.Any(p => p.Nature == NatureDePiece.Pan && p.Cote == cote && p.Indice == indice);

        [Test]
        public void LaPorteOuvreLePanQuElleCouvre()
        {
            DecoupeDeLEnceinte d = Ouvrir(C160, 16, -80); Assert.AreEqual(68, d.Pieces.Count); Assert.IsFalse(Reste(d, 0, 9), "le pan 9 du côté 0 reste");
            Piece(d.Pieces[9], NatureDePiece.Pan, 0, 8, 4.775, -80, 0, 9.55); Piece(d.Pieces[10], NatureDePiece.Pan, 0, 10, 23.875, -80, 0, 9.55);
            Piece(d.Pieces[67], NatureDePiece.Porte, 0, 0, 16, -80, 0, 4); Assert.AreEqual(96, d.Pieces[67].AbscisseM, 1e-9);
            d = Ouvrir(C160, -78, -80); Assert.AreEqual(68, d.Pieces.Count); Assert.IsFalse(Reste(d, 0, 0), "le pan du coin reste");
            Piece(d.Pieces[1], NatureDePiece.Pan, 0, 1, -62.075, -80, 0, 9.55); Piece(d.Pieces[16], NatureDePiece.Tour, 1, 0, 80, -80, 315, 7.2);
            Piece(d.Pieces[67], NatureDePiece.Porte, 0, 0, -78, -80, 0, 4); Assert.AreEqual(2, d.Pieces[67].AbscisseM, 1e-9);
            d = Ouvrir(C160, 80, 78.5); Assert.IsTrue(!Reste(d, 1, 15) && Reste(d, 1, 14) && Reste(d, 0, 9), "le pan 15 du côté 1, et lui seul");
            Piece(d.Pieces[67], NatureDePiece.Porte, 1, 0, 80, 78.5, 270, 4);
            d = Ouvrir(C160, 12, -80, 10, -80); Assert.IsTrue(d.Pieces.Count == 69 && d.Pieces.Count(p => p.Nature == NatureDePiece.Pan) == 63 && !Reste(d, 0, 9) && Reste(d, 0, 8) && Reste(d, 0, 10), d.Pieces.Count + " pièces");
            Piece(d.Pieces[67], NatureDePiece.Porte, 0, 0, 12, -80, 0, 4); Piece(d.Pieces[68], NatureDePiece.Porte, 0, 1, 10, -80, 0, 4);
            d = Ouvrir(C160, 0, -80.005); Piece(d.Pieces[67], NatureDePiece.Porte, 0, 0, 0, -80, 0, 4);
            d = Ouvrir(C160h, -80, 2.2); Assert.IsTrue(d.Pieces.Count == 68 && !Reste(d, 3, 8) && Reste(d, 3, 7), d.Pieces.Count + " pièces");
            Piece(d.Pieces[67], NatureDePiece.Porte, 3, 0, -80, 2.2, 90, 4); Assert.AreEqual(82.2, d.Pieces[67].AbscisseM, 1e-9);
            d = Ouvrir(C6, 0, -3); Assert.IsTrue(d.Pieces.Count == 5 && d.Pieces.Take(4).All(p => p.Nature == NatureDePiece.Tour), d.Pieces.Count + " pièces");
            Piece(d.Pieces[4], NatureDePiece.Porte, 0, 0, 0, -3, 0, 4);
            DecoupeDeLEnceinte sans = Ouvrir(C160), seul = PansDeLEnceinte.Decouper(Enceinte(C160)); Assert.AreEqual(68, sans.Pieces.Count);
            for (int q = 0; q < 68; q++) { PieceDeLEnceinte a = sans.Pieces[q], b = seul.Pieces[q];
                Piece(a, b.Nature, b.Cote, b.Indice, b.CentreX, b.CentreY, b.LacetDegres, b.LongueurM); Assert.AreEqual(b.AbscisseM, a.AbscisseM, 1e-9); }
        }

        [TestCase(new double[] { -80, -80, 80, -80, 80, 80, -80, 80 }, new double[] { 0, -79 }, "porte 0 hors du mur")]
        [TestCase(new double[] { -80, -80, 80, -80, 80, 80, -80, 80 }, new double[] { 10, -80, 0, -80.02 }, "porte 1 hors du mur")]
        [TestCase(new double[] { -80, -80, 80, -80, 80, 80, -80, 80 }, new double[] { double.NaN, -80 }, "porte 0 hors du mur")]
        [TestCase(new double[] { 0, 0, 10, 0, 20, 0 }, new double[] { 5, 0 }, "contour plat")]
        public void UnePorteHorsDuMurRendLaDecoupeAbsente(double[] xy, double[] portes, string attendu)
        {
            DecoupeDeLEnceinte d = PansDeLEnceinte.Decouper(Enceinte(xy), Portes(portes)); Assert.IsTrue(!d.Presente && d.Pieces.Count == 0, d.Pieces.Count + " pièces"); StringAssert.Contains(attendu, d.Absence);
            Assert.Throws<ArgumentNullException>(() => PansDeLEnceinte.Decouper(Enceinte(C160), null));
            Assert.Throws<ArgumentNullException>(() => PansDeLEnceinte.Decouper(Enceinte(C160), new[] { Portes(0, -80)[0], null }));
        }
    }
}
