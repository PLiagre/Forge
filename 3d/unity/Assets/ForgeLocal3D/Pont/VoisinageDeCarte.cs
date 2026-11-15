using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using UnityEngine;

namespace Forge.Pont {
    // Un côté d'un contour servi, en km locaux (x vers l'est, z vers le nord) : la cellule qu'il borde et celle
    // qui est juste de l'autre côté (jamais la mer : un côté de côte n'est pas gardé).
    public readonly struct CoteDeCarte {
        public long Dedans { get; } public long Dehors { get; } public Vector2 De { get; } public Vector2 A { get; }
        public CoteDeCarte(long dedans, long dehors, Vector2 de, Vector2 a) { Dedans = dedans; Dehors = dehors; De = de; A = a; }
    }

    // Le voisinage des cellules servies, tiré de leurs seuls contours : pour chaque côté, la cellule sous un point
    // pris à `ECART_KM` de son milieu, de part et d'autre ; et le centre de la boîte de chaque cellule. De la
    // géométrie de dessin, aucun nombre du monde. Se calcule hors du fil principal : rien de Unity n'y est lu.
    public sealed class VoisinageDeCarte {
        // Les contours sont simplifiés à 1 km : un point à 2 km du côté tombe dans la cellule voisine.
        public const float ECART_KM = 2f;
        public IReadOnlyList<CoteDeCarte> Cotes { get; }
        public IReadOnlyDictionary<long, Vector2> Centres { get; }

        public VoisinageDeCarte(CarteLue carte, PointCarte origine) {
            if (carte == null) throw new ArgumentNullException(nameof(carte));
            var reperage = new ReperageDeCarte(carte, origine);
            var cotes = new List<CoteDeCarte>(); var centres = new Dictionary<long, Vector2>();
            foreach (CelluleDeCarte cellule in carte.Cellules) {
                float xMin = float.MaxValue, zMin = float.MaxValue, xMax = float.MinValue, zMax = float.MinValue;
                foreach (PolygoneDeCarte polygone in cellule.Contour)
                    for (int r = -1; r < polygone.Trous.Count; r++) {
                        IReadOnlyList<PointCarte> anneau = r < 0 ? polygone.Exterieur : polygone.Trous[r];
                        var points = new Vector2[anneau.Count];
                        for (int k = 0; k < points.Length; k++) {
                            points[k] = new Vector2((float)((anneau[k].X - origine.X) / 1000.0), (float)((anneau[k].Y - origine.Y) / 1000.0));
                            xMin = Mathf.Min(xMin, points[k].x); xMax = Mathf.Max(xMax, points[k].x); zMin = Mathf.Min(zMin, points[k].y); zMax = Mathf.Max(zMax, points[k].y);
                        }
                        for (int k = 0; k + 1 < points.Length; k++) {
                            Vector2 p = points[k], q = points[k + 1];
                            if (p == q) continue;
                            Vector2 milieu = (p + q) / 2f, d = (q - p).normalized, n = new Vector2(d.y, -d.x) * ECART_KM;
                            CelluleDeCarte plus = reperage.Sous(milieu.x + n.x, milieu.y + n.y), moins = reperage.Sous(milieu.x - n.x, milieu.y - n.y);
                            // Le dehors est le côté qui n'est pas la cellule ; un côté dont aucun bord n'est la cellule est trop étroit pour juger.
                            CelluleDeCarte dehors = plus != null && plus.CellId == cellule.CellId ? moins : moins != null && moins.CellId == cellule.CellId ? plus : null;
                            if (dehors != null && dehors.CellId != cellule.CellId) cotes.Add(new CoteDeCarte(cellule.CellId, dehors.CellId, p, q));
                        }
                    }
                if (xMin <= xMax) centres[cellule.CellId] = new Vector2((xMin + xMax) / 2f, (zMin + zMax) / 2f);
            }
            Cotes = new ReadOnlyCollection<CoteDeCarte>(cotes);
            Centres = new ReadOnlyDictionary<long, Vector2>(centres);
        }
    }
}
