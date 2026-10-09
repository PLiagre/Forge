using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using UnityEngine;

namespace Forge.Pont {
    // Cellule maillée, puis carte entière dans l'ordre servi, autour du centre de sa boîte.
    public sealed class MaillageDeCellule {
        public long CellId { get; }
        public MaillageDePolygone Maillage { get; }
        public Color Couleur { get; }
        internal MaillageDeCellule(long cellId, MaillageDePolygone maillage, Color couleur) { CellId = cellId; Maillage = maillage; Couleur = couleur; }
    }
    public sealed class CarteMaillee {
        public PointCarte Origine { get; }
        public IReadOnlyList<MaillageDeCellule> Cellules { get; }
        internal CarteMaillee(PointCarte origine, IReadOnlyList<MaillageDeCellule> cellules) { Origine = origine; Cellules = cellules; }
    }
    // La teinte ne dépend que du numéro : l'inverse du nombre d'or éloigne deux puissances voisines.
    public static class MaillageDeCarte {
        public const double PasDeTeinte = 0.6180339887498949;
        public const float Saturation = 0.65f, Valeur = 0.85f;
        public static readonly Color CouleurSansPuissance = new Color(0.5f, 0.5f, 0.5f, 1f);
        public static Color CouleurPourPuissance(long id) {
            Color couleur = Color.HSVToRGB((float)((id * PasDeTeinte) % 1.0), Saturation, Valeur); couleur.a = 1f; return couleur;
        }
        public static CarteMaillee Mailler(CarteLue carte) {
            if (carte == null) throw new ArgumentNullException(nameof(carte));
            if (carte.Cellules.Count == 0) throw new ArgumentException("une carte vide n'a aucun maillage");
            PointCarte origine = Centre(carte);
            var cellules = new List<MaillageDeCellule>(carte.Cellules.Count);
            foreach (CelluleDeCarte cellule in carte.Cellules) {
                var sommets = new List<Vector3>();
                foreach (PolygoneDeCarte polygone in cellule.Contour) sommets.AddRange(TriangulationDeCarte.Trianguler(polygone, origine).Sommets);
                if (sommets.Count == 0) throw new ArgumentException("cellule " + cellule.CellId + " : aucun triangle");
                if (sommets.Count >= 65535) throw new ArgumentException("cellule " + cellule.CellId + " : " + sommets.Count + " sommets");
                Color couleur = cellule.Puissance == null ? CouleurSansPuissance : CouleurPourPuissance(cellule.Puissance.Id);
                cellules.Add(new MaillageDeCellule(cellule.CellId, new MaillageDePolygone(sommets), couleur));
            }
            return new CarteMaillee(origine, new ReadOnlyCollection<MaillageDeCellule>(cellules));
        }
        private static PointCarte Centre(CarteLue carte) {
            double minX = double.PositiveInfinity, minY = double.PositiveInfinity, maxX = double.NegativeInfinity, maxY = double.NegativeInfinity;
            foreach (CelluleDeCarte cellule in carte.Cellules)
                foreach (PolygoneDeCarte polygone in cellule.Contour) {
                    Etendre(polygone.Exterieur, ref minX, ref minY, ref maxX, ref maxY);
                    foreach (IReadOnlyList<PointCarte> trou in polygone.Trous) Etendre(trou, ref minX, ref minY, ref maxX, ref maxY);
                }
            return new PointCarte((minX + maxX) / 2.0, (minY + maxY) / 2.0);
        }
        private static void Etendre(IReadOnlyList<PointCarte> anneau, ref double minX, ref double minY, ref double maxX, ref double maxY) {
            foreach (PointCarte point in anneau) { if (point.X < minX) minX = point.X; if (point.Y < minY) minY = point.Y; if (point.X > maxX) maxX = point.X; if (point.Y > maxY) maxY = point.Y; }
        }
    }
}
