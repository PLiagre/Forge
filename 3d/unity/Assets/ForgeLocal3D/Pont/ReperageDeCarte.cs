using System.Collections.Generic;
using UnityEngine;

namespace Forge.Pont {
    // Lot #526 : quelle cellule est sous un point de la carte. Les anneaux servis sont convertis une fois en km locaux, par la
    // conversion des contours (#548) ; un point est dans une cellule s'il croise un nombre impair de ses anneaux, extérieurs
    // et trous confondus (règle pair-impair) : un point d'une enclave n'est pas à la cellule qui l'entoure. Une boîte par
    // cellule écarte vite les autres. Hors de toute cellule, la mer : null. Rien n'est deviné : une cellule sans anneau
    // n'est sous aucun point.
    public sealed class ReperageDeCarte {
        private readonly List<CelluleDeCarte> cellules = new List<CelluleDeCarte>();
        private readonly List<Rect> boites = new List<Rect>();
        private readonly List<List<Vector2[]>> anneaux = new List<List<Vector2[]>>();

        public ReperageDeCarte(CarteLue carte, PointCarte origine) {
            foreach (CelluleDeCarte cellule in carte.Cellules) {
                var siens = new List<Vector2[]>(); float xMin = float.MaxValue, zMin = float.MaxValue, xMax = float.MinValue, zMax = float.MinValue;
                foreach (PolygoneDeCarte polygone in cellule.Contour)
                    for (int a = -1; a < polygone.Trous.Count; a++) {
                        IReadOnlyList<PointCarte> anneau = a < 0 ? polygone.Exterieur : polygone.Trous[a];
                        var points = new Vector2[anneau.Count];
                        for (int k = 0; k < points.Length; k++) {
                            Vector3 p = TriangulationDeCarte.Point(anneau[k].X, anneau[k].Y, origine); points[k] = new Vector2(p.x, p.z);
                            xMin = Mathf.Min(xMin, p.x); xMax = Mathf.Max(xMax, p.x); zMin = Mathf.Min(zMin, p.z); zMax = Mathf.Max(zMax, p.z);
                        }
                        siens.Add(points);
                    }
                if (siens.Count == 0) continue;
                cellules.Add(cellule); anneaux.Add(siens); boites.Add(Rect.MinMaxRect(xMin, zMin, xMax, zMax));
            }
        }

        // La cellule sous le point (x vers l'est, z vers le nord, en km locaux), null dans la mer.
        public CelluleDeCarte Sous(float x, float z) {
            for (int i = 0; i < cellules.Count; i++) {
                Rect b = boites[i];
                if (x < b.xMin || x > b.xMax || z < b.yMin || z > b.yMax) continue;
                bool dedans = false;
                foreach (Vector2[] anneau in anneaux[i]) if (Croise(anneau, x, z)) dedans = !dedans;
                if (dedans) return cellules[i];
            }
            return null;
        }

        // Le rayon vers l'est depuis (x, z) coupe-t-il l'anneau un nombre impair de fois ?
        private static bool Croise(Vector2[] anneau, float x, float z) {
            bool impair = false;
            for (int i = 0, j = anneau.Length - 1; i < anneau.Length; j = i++) {
                Vector2 a = anneau[i], b = anneau[j];
                if ((a.y > z) != (b.y > z) && x < (double)(b.x - a.x) * (z - a.y) / (b.y - a.y) + a.x) impair = !impair;
            }
            return impair;
        }
    }
}
