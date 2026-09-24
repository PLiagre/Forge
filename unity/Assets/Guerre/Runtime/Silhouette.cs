using System.Collections.Generic;
using UnityEngine;

namespace Guerre
{
    // Silhouette provisoire d'un homme de 1,80 m : un tour de huit faces, aplati
    // de face, en attendant le soldat modulaire de Blender (jalon 3). Environ
    // 150 triangles : 10 000 hommes restent sous deux millions de triangles.
    public static class Silhouette
    {
        // (rayon, hauteur) des pieds au sommet du casque
        static readonly Vector2[] Profil =
        {
            new Vector2(0.15f, 0.00f), new Vector2(0.17f, 0.45f), new Vector2(0.19f, 0.85f),
            new Vector2(0.20f, 1.05f), new Vector2(0.25f, 1.38f), new Vector2(0.09f, 1.50f),
            new Vector2(0.12f, 1.58f), new Vector2(0.12f, 1.72f), new Vector2(0.05f, 1.82f),
        };
        const int Faces = 8;
        const float Profondeur = 0.65f; // un homme est plus large que profond

        public static Mesh Creer()
        {
            var v = new List<Vector3>();
            var tri = new List<int>();
            // Sommets dupliqués par face pour des arêtes franches : la silhouette se lit de loin.
            for (int s = 0; s < Faces; s++)
            {
                float a0 = s * Mathf.PI * 2 / Faces, a1 = (s + 1) * Mathf.PI * 2 / Faces;
                for (int k = 0; k < Profil.Length - 1; k++)
                {
                    Vector3 P(Vector2 pr, float a) => new Vector3(Mathf.Cos(a) * pr.x, pr.y, Mathf.Sin(a) * pr.x * Profondeur);
                    int i = v.Count;
                    v.Add(P(Profil[k], a0)); v.Add(P(Profil[k], a1));
                    v.Add(P(Profil[k + 1], a1)); v.Add(P(Profil[k + 1], a0));
                    tri.AddRange(new[] { i, i + 2, i + 1, i, i + 3, i + 2 });
                }
            }
            var m = new Mesh { name = "Silhouette_soldat" };
            m.SetVertices(v);
            m.SetTriangles(tri, 0);
            m.RecalculateNormals();
            m.RecalculateBounds();
            m.UploadMeshData(false);
            return m;
        }
    }
}
