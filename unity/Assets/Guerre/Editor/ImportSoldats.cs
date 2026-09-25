using System;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace Guerre.EditeurOutils
{
    // Transforme les fichiers .vat de fabrique/soldats.py en maillage, texture
    // d'animation (RGBA demi-précision) et matériau, un triplet par arme.
    public static partial class Construire
    {
        static readonly string[] Armes = { "piquier", "hallebardier", "arbaletrier", "cavalier" };

        static (Material[], Mesh[]) Soldats()
        {
            string dossier = Dossier + "/Soldats";
            Directory.CreateDirectory(dossier);
            string sources = Path.GetFullPath(Path.Combine(Application.dataPath, "../../fabrique/sorties"));
            var shader = Shader.Find("Guerre/Soldat");
            if (shader == null) throw new Exception("shader Guerre/Soldat introuvable");
            var materiaux = new Material[Armes.Length];
            var maillages = new Mesh[Armes.Length];
            for (int k = 0; k < Armes.Length; k++)
            {
                string fichier = Path.Combine(sources, Armes[k] + ".vat");
                if (!File.Exists(fichier)) throw new Exception("soldat non fabriqué : " + fichier + " (lancer outils/atelier.ps1 soldats)");
                using var r = new BinaryReader(File.OpenRead(fichier));
                if (Encoding.ASCII.GetString(r.ReadBytes(4)) != "VAT1") throw new Exception("format .vat inconnu : " + fichier);
                int coins = r.ReadInt32(), nClips = r.ReadInt32();
                var images = new int[nClips]; var durees = new float[nClips];
                for (int c = 0; c < nClips; c++) { r.ReadBytes(16); images[c] = r.ReadInt32(); durees[c] = r.ReadSingle(); }

                var pos = new Vector3[coins]; var nor = new Vector3[coins]; var col = new Color[coins];
                for (int i = 0; i < coins; i++)
                {
                    pos[i] = new Vector3(H(r), H(r), H(r));
                    nor[i] = new Vector3(H(r), H(r), H(r));
                    col[i] = new Color(H(r), H(r), H(r), H(r));
                }
                int lignes = 0; foreach (var n in images) lignes += n;
                // Ligne = image ; colonnes [0, coins) les positions, [coins, 2 coins) les normales.
                var texels = new ushort[2 * coins * lignes * 4];
                var bornes = new Bounds(pos[0], Vector3.zero);
                const ushort Un = 0x3C00;
                for (int l = 0; l < lignes; l++)
                    for (int i = 0; i < coins; i++)
                    {
                        int p = (l * 2 * coins + i) * 4, q = (l * 2 * coins + coins + i) * 4;
                        texels[p] = r.ReadUInt16(); texels[p + 1] = r.ReadUInt16(); texels[p + 2] = r.ReadUInt16(); texels[p + 3] = Un;
                        texels[q] = r.ReadUInt16(); texels[q + 1] = r.ReadUInt16(); texels[q + 2] = r.ReadUInt16(); texels[q + 3] = 0;
                        bornes.Encapsulate(new Vector3(Mathf.HalfToFloat(texels[p]), Mathf.HalfToFloat(texels[p + 1]), Mathf.HalfToFloat(texels[p + 2])));
                    }

                var tex = new Texture2D(2 * coins, lignes, TextureFormat.RGBAHalf, false, true)
                {
                    name = "VAT_" + Armes[k], filterMode = FilterMode.Point, wrapMode = TextureWrapMode.Clamp,
                };
                tex.SetPixelData(texels, 0);
                tex.Apply(false, false); // reste lisible : l'asset doit en garder les données
                Remplacer(tex, dossier + "/VAT_" + Armes[k] + ".asset");

                var tris = new int[coins];
                for (int i = 0; i < coins; i++) tris[i] = i;
                var mesh = new Mesh { name = "Soldat_" + Armes[k] };
                mesh.SetVertices(pos); mesh.SetNormals(nor); mesh.SetColors(col);
                mesh.SetTriangles(tris, 0, false);
                // Les bornes couvrent toutes les images cuites : le soldat n'est jamais coupé en marchant.
                bornes.Expand(0.2f);
                mesh.bounds = bornes;
                Remplacer(mesh, dossier + "/Soldat_" + Armes[k] + ".asset");

                var mat = new Material(shader) { name = "Soldat_" + Armes[k], enableInstancing = true };
                mat.SetTexture("_VAT", AssetDatabase.LoadAssetAtPath<Texture2D>(dossier + "/VAT_" + Armes[k] + ".asset"));
                mat.SetFloat("_Coins", coins);
                mat.SetFloat("_ImagesMarche", images[0]);
                mat.SetFloat("_ImagesRepos", images[1]);
                mat.SetFloat("_DureeRepos", durees[1]);
                mat.SetFloat("_ImagesCombat", images[2]);
                mat.SetFloat("_ImagesAbri", images[3]);
                mat.SetFloat("_DureeAbri", durees[3]);
                // Le cavalier range son galop de charge à la place de la posture à l'abri : il se joue au pas de la marche.
                mat.SetFloat("_AbriSuitLaMarche", Armes[k] == "cavalier" ? 1 : 0);
                mat.SetFloat("_VATActif", 1);
                Remplacer(mat, dossier + "/Soldat_" + Armes[k] + ".mat");

                materiaux[k] = AssetDatabase.LoadAssetAtPath<Material>(dossier + "/Soldat_" + Armes[k] + ".mat");
                maillages[k] = AssetDatabase.LoadAssetAtPath<Mesh>(dossier + "/Soldat_" + Armes[k] + ".asset");
                Debug.Log($"[Construire] soldat {Armes[k]} : {coins / 3} triangles, {lignes} images, texture {2 * coins} × {lignes}");
            }
            AssetDatabase.SaveAssets();
            return (materiaux, maillages);
        }

        static float H(BinaryReader r) => Mathf.HalfToFloat(r.ReadUInt16());

        static void Remplacer(UnityEngine.Object o, string chemin)
        {
            AssetDatabase.DeleteAsset(chemin);
            AssetDatabase.CreateAsset(o, chemin);
        }
    }
}
