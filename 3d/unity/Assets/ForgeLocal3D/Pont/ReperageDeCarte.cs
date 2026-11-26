using System.Collections.Generic;
using UnityEngine;

namespace Forge.Pont {
    // Quel lieu, et quelle cellule, sont sous un point de la carte. Les anneaux servis sont convertis une fois en km
    // locaux, par la conversion des contours ; un point est dans un lieu s'il croise un nombre impair de ses anneaux,
    // extérieurs et trous confondus (règle pair-impair) : un point d'une enclave n'est pas au lieu qui l'entoure. Une
    // boîte par lieu écarte vite les autres. Hors de tout lieu, la mer : null. Rien n'est deviné : un lieu sans anneau
    // n'est sous aucun point. Repérée sur les formes servies (`GET /formes`), la carte rend le lieu qui contient le
    // point ; repérée sur les seuls contours de `/carte`, chaque cellule compte pour un lieu de rang 0.
    // Ce qui est posé sur la carte y répond sur tout ce qu'il couvre : une ancre (le pied d'une figurine et son rayon en km)
    // tient au lieu de sa cellule le plus proche de son pied. Un point de la mer qui tombe sous une ancre rend ce lieu, celui
    // de l'ancre dont le pied est le plus proche ; hors de toute ancre, la mer reste la mer, et une ancre ne prend jamais la
    // terre d'un autre lieu.
    public sealed class ReperageDeCarte {
        // Le plus loin, en km, où une ancre sans cellule cherche le lieu le plus proche de son pied.
        public const float ANCRE_SANS_CELLULE_MAX_KM = 60f;
        private readonly List<CelluleDeCarte> cellules = new List<CelluleDeCarte>();
        private readonly List<long> rangs = new List<long>();
        private readonly List<Rect> boites = new List<Rect>();
        private readonly List<List<Vector2[]>> anneaux = new List<List<Vector2[]>>();
        private sealed class Ancre { public Vector2 Pied; public float Rayon; public int Indice; }
        private readonly Dictionary<object, Ancre> ancres = new Dictionary<object, Ancre>();

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

        // Pose ou règle l'ancre de cette clé : son pied (km locaux), la cellule servie dont elle tient le lieu le plus proche
        // (sans cellule, le lieu sous son pied, ou le plus proche à moins de `ANCRE_SANS_CELLULE_MAX_KM`), et son rayon ; un
        // rayon nul ne couvre rien. Le lieu ne se cherche qu'à la pose ou quand le pied bouge. Faux, et sans ancre, si aucun
        // lieu ne convient.
        public bool Ancrer(object cle, float x, float z, long? cellId, float rayonKm) {
            var pied = new Vector2(x, z);
            if (ancres.TryGetValue(cle, out Ancre deja) && deja.Pied == pied) { deja.Rayon = Mathf.Max(0f, rayonKm); return true; }
            int indice = PlusProche(x, z, cellId);
            if (indice < 0) { ancres.Remove(cle); return false; }
            ancres[cle] = new Ancre { Pied = pied, Rayon = Mathf.Max(0f, rayonKm), Indice = indice }; return true;
        }
        public void Desancrer(object cle) => ancres.Remove(cle);
        public int Ancres => ancres.Count;

        private int Indice(float x, float z) {
            int ici = Dans(x, z); if (ici >= 0) return ici;
            // La mer : sous une ancre, le lieu de celle dont le pied est le plus proche.
            float plusPres = float.MaxValue;
            foreach (Ancre a in ancres.Values) {
                float d = Vector2.Distance(a.Pied, new Vector2(x, z));
                if (d <= a.Rayon && d < plusPres) { plusPres = d; ici = a.Indice; }
            }
            return ici;
        }
        private int Dans(float x, float z) {
            for (int i = 0; i < cellules.Count; i++) {
                Rect b = boites[i];
                if (x < b.xMin || x > b.xMax || z < b.yMin || z > b.yMax) continue;
                bool dedans = false;
                foreach (Vector2[] anneau in anneaux[i]) if (Croise(anneau, x, z)) dedans = !dedans;
                if (dedans) return i;
            }
            return -1;
        }

        // Le lieu de cette cellule qui contient le point, sinon celui dont un anneau passe le plus près ; une cellule sans lieu
        // repéré, ou sans cellule, cherche parmi tous les lieux, le point d'abord, puis à moins de `ANCRE_SANS_CELLULE_MAX_KM`.
        private int PlusProche(float x, float z, long? cellId) {
            bool dansLaCellule = cellId.HasValue && cellules.Exists(c => c.CellId == cellId.Value);
            if (!dansLaCellule) { int sous = Dans(x, z); if (sous >= 0) return sous; }
            int meilleur = -1; float plusPres = dansLaCellule ? float.MaxValue : ANCRE_SANS_CELLULE_MAX_KM;
            for (int i = 0; i < cellules.Count; i++) {
                if (dansLaCellule && cellules[i].CellId != cellId.Value) continue;
                Rect b = boites[i];
                if (!dansLaCellule && (x < b.xMin - plusPres || x > b.xMax + plusPres || z < b.yMin - plusPres || z > b.yMax + plusPres)) continue;
                bool dedans = false; float d = float.MaxValue;
                foreach (Vector2[] anneau in anneaux[i]) {
                    if (Croise(anneau, x, z)) dedans = !dedans;
                    for (int k = 0, j = anneau.Length - 1; k < anneau.Length; j = k++) d = Mathf.Min(d, DistanceAuCote(anneau[j], anneau[k], x, z));
                }
                if (dedans) return i;
                if (d < plusPres) { plusPres = d; meilleur = i; }
            }
            return meilleur;
        }
        private static float DistanceAuCote(Vector2 a, Vector2 b, float x, float z) {
            Vector2 u = b - a, p = new Vector2(x, z); float l2 = u.sqrMagnitude, t = l2 > 0f ? Mathf.Clamp01(Vector2.Dot(p - a, u) / l2) : 0f;
            return (p - (a + t * u)).magnitude;
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
