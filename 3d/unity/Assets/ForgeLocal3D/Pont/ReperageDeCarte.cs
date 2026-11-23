using System.Collections.Generic;
using UnityEngine;

namespace Forge.Pont {
    // Quel lieu, et quelle cellule, sont sous un point de la carte. Les anneaux servis sont convertis une fois en km
    // locaux, par la conversion des contours ; un point est dans un lieu s'il croise un nombre impair de ses anneaux,
    // extérieurs et trous confondus (règle pair-impair) : un point d'une enclave n'est pas au lieu qui l'entoure. Une
    // boîte par lieu écarte vite les autres. Hors de tout lieu, la mer : null. Rien n'est deviné : un lieu sans anneau
    // n'est sous aucun point. Repérée sur les formes servies (`GET /formes`), la carte rend le lieu qui contient le
    // point ; repérée sur les seuls contours de `/carte`, chaque cellule compte pour un lieu de rang 0.
    public sealed class ReperageDeCarte {
        private readonly List<CelluleDeCarte> cellules = new List<CelluleDeCarte>();
        private readonly List<long> rangs = new List<long>();
        private readonly List<Rect> boites = new List<Rect>();
        private readonly List<List<Vector2[]>> anneaux = new List<List<Vector2[]>>();

        // Sur les contours des cellules de la carte servie.
        public ReperageDeCarte(CarteLue carte, PointCarte origine) {
            foreach (CelluleDeCarte cellule in carte.Cellules) Ajouter(cellule, 0, cellule.Contour, origine);
        }
        // Sur les contours des lieux servis : chaque cellule de la carte, lieu par lieu, telle que les formes la découpent.
        // Une cellule que les formes ne servent pas n'est sous aucun point.
        public ReperageDeCarte(CarteLue carte, FormesLues formes, PointCarte origine) {
            foreach (CelluleDeCarte cellule in carte.Cellules) {
                FormeDeCellule forme = formes.De(cellule.CellId); if (forme == null) continue;
                foreach (FormeDeLieu lieu in forme.Lieux) Ajouter(cellule, lieu.Rang, lieu.Contour, origine);
            }
        }
        private void Ajouter(CelluleDeCarte cellule, long rang, IReadOnlyList<PolygoneDeCarte> contour, PointCarte origine) {
            var siens = new List<Vector2[]>(); float xMin = float.MaxValue, zMin = float.MaxValue, xMax = float.MinValue, zMax = float.MinValue;
            foreach (PolygoneDeCarte polygone in contour)
                for (int a = -1; a < polygone.Trous.Count; a++) {
                    IReadOnlyList<PointCarte> anneau = a < 0 ? polygone.Exterieur : polygone.Trous[a];
                    var points = new Vector2[anneau.Count];
                    for (int k = 0; k < points.Length; k++) {
                        Vector3 p = TriangulationDeCarte.Point(anneau[k].X, anneau[k].Y, origine); points[k] = new Vector2(p.x, p.z);
                        xMin = Mathf.Min(xMin, p.x); xMax = Mathf.Max(xMax, p.x); zMin = Mathf.Min(zMin, p.z); zMax = Mathf.Max(zMax, p.z);
                    }
                    siens.Add(points);
                }
            if (siens.Count == 0) return;
            cellules.Add(cellule); rangs.Add(rang); anneaux.Add(siens); boites.Add(Rect.MinMaxRect(xMin, zMin, xMax, zMax));
        }

        // La cellule sous le point (x vers l'est, z vers le nord, en km locaux), null dans la mer.
        public CelluleDeCarte Sous(float x, float z) { int i = Indice(x, z); return i < 0 ? null : cellules[i]; }
        // La cellule et le rang du lieu sous le point ; null dans la mer.
        public (CelluleDeCarte cellule, long rang)? LieuSous(float x, float z) { int i = Indice(x, z); return i < 0 ? ((CelluleDeCarte, long)?)null : (cellules[i], rangs[i]); }

        private int Indice(float x, float z) {
            for (int i = 0; i < cellules.Count; i++) {
                Rect b = boites[i];
                if (x < b.xMin || x > b.xMax || z < b.yMin || z > b.yMax) continue;
                bool dedans = false;
                foreach (Vector2[] anneau in anneaux[i]) if (Croise(anneau, x, z)) dedans = !dedans;
                if (dedans) return i;
            }
            return -1;
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
