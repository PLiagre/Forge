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
    }
}
