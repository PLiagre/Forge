using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEditor.AssetImporters;
using UnityEngine;

namespace ForgeLocal3D
{
    // Lot 786 : VAT1 de #785 → maillage, texture RGBAHalf linéaire, matériau Forge/CivilVAT. Lire refuse toute valeur non finie.
    [ScriptedImporter(1, "vat")]
    public sealed class ImporterCivil : ScriptedImporter
    {
        const string Relatif = "ForgeLocal3D/Desert/Civils/civil.vat", ShaderChemin = "Assets/ForgeLocal3D/Desert/Shaders/Civil.shader";
        static readonly (string nom, int images, float duree)[] Attendu = { ("marche", 24, 1.15f), ("repos", 24, 4f) };
        public sealed class Vat { public int C, Images; public Vector3[] Pos, Nor; public Color[] Col; public ushort[] Texels; public Bounds Bornes; public (string n, int i, float d)[] Clips; }
        public override void OnImportAsset(AssetImportContext ctx)
        {
            var vat = Lire(File.ReadAllBytes(ctx.assetPath)); var tris = new int[vat.C]; for (int i = 0; i < vat.C; i++) tris[i] = i;
            var mesh = new Mesh { name = "Civil" }; mesh.SetVertices(vat.Pos); mesh.SetNormals(vat.Nor); mesh.SetColors(vat.Col); mesh.SetTriangles(tris, 0, false); mesh.bounds = vat.Bornes;
            var tex = new Texture2D(2 * vat.C, vat.Images, TextureFormat.RGBAHalf, false, true) { name = "CivilVAT", filterMode = FilterMode.Point, wrapMode = TextureWrapMode.Clamp };
            tex.SetPixelData(vat.Texels, 0); tex.Apply(false, false);
            var shader = AssetDatabase.LoadAssetAtPath<Shader>(ShaderChemin); if (!shader || shader.name != "Forge/CivilVAT") throw new InvalidDataException("shader Forge/CivilVAT absent");
            var mat = new Material(shader) { name = "Civil" };
            mat.SetTexture("_VAT", tex); mat.SetFloat("_Coins", vat.C); mat.SetFloat("_ImagesMarche", Attendu[0].images); mat.SetFloat("_Phase", 0); mat.SetFloat("_VATActif", 1); mat.SetColor("_Teinte", Color.white);
            ctx.AddObjectToAsset("maillage", mesh); ctx.AddObjectToAsset("texture", tex); ctx.AddObjectToAsset("materiau", mat); ctx.SetMainObject(mesh);
        }
        public static Vat Lire(byte[] d)
        {
            if (d == null || d.Length < 12 || d[0] != (byte)'V' || d[1] != (byte)'A' || d[2] != (byte)'T' || d[3] != (byte)'1') throw new InvalidDataException("signature VAT1 absente");
            int c = BitConverter.ToInt32(d, 4), n = BitConverter.ToInt32(d, 8);
            if (c <= 0 || c % 3 != 0 || n != Attendu.Length) throw new InvalidDataException("compte incohérent : " + c + " coins, " + n + " clips");
            var clips = new (string n, int i, float d)[n]; int images = 0;
            for (int k = 0; k < n; k++)
            {
                int o = 12 + 24 * k; if (o + 24 > d.Length) throw new InvalidDataException("longueur " + d.Length + " octets, en-tête tronqué");
                string nom = Encoding.ASCII.GetString(d, o, 16).TrimEnd('\0'); int nb = BitConverter.ToInt32(d, o + 16); float duree = BitConverter.ToSingle(d, o + 20);
                if (nom != Attendu[k].nom || nb != Attendu[k].images || !float.IsFinite(duree) || Math.Abs(duree - Attendu[k].duree) > 1e-5f) throw new InvalidDataException("clips refusés : " + nom + " " + nb + " / " + duree.ToString(System.Globalization.CultureInfo.InvariantCulture));
                clips[k] = (nom, nb, duree); images += nb;
            }
            int debut = 12 + 24 * n, attendu = debut + 20 * c + 12 * c * images;
            if (d.Length != attendu) throw new InvalidDataException("longueur " + d.Length + " octets, attendue " + attendu);
            var vat = new Vat { C = c, Images = images, Pos = new Vector3[c], Nor = new Vector3[c], Col = new Color[c], Clips = clips, Texels = new ushort[2 * c * images * 4] };
            for (int i = 0; i < c; i++)
            {
                int o = debut + 20 * i; var p = Vec(d, o); var nr = Vec(d, o + 6); var col = new Color(H(d, o + 12), H(d, o + 14), H(d, o + 16), H(d, o + 18));
                Fini(p); Unitaire(nr); if (!float.IsFinite(col.r) || !float.IsFinite(col.g) || !float.IsFinite(col.b) || !float.IsFinite(col.a) || col.r < 0 || col.r > 1 || col.g < 0 || col.g > 1 || col.b < 0 || col.b > 1 || col.a < 0 || col.a > 1) throw new InvalidDataException("couleur hors de [0, 1]");
                vat.Pos[i] = p; vat.Nor[i] = nr; vat.Col[i] = col; if (i == 0) vat.Bornes = new Bounds(p, Vector3.zero); else vat.Bornes.Encapsulate(p);
            }
            for (int ligne = 0; ligne < images; ligne++) for (int i = 0; i < c; i++)
            {
                int o = debut + 20 * c + (ligne * c + i) * 12, t = (ligne * 2 * c + i) * 4, q = t + 4 * c;
                vat.Texels[t] = U(d, o); vat.Texels[t + 1] = U(d, o + 2); vat.Texels[t + 2] = U(d, o + 4); vat.Texels[t + 3] = 0x3C00; vat.Texels[q] = U(d, o + 6); vat.Texels[q + 1] = U(d, o + 8); vat.Texels[q + 2] = U(d, o + 10);
                var p = new Vector3(Mathf.HalfToFloat(vat.Texels[t]), Mathf.HalfToFloat(vat.Texels[t + 1]), Mathf.HalfToFloat(vat.Texels[t + 2]));
                Fini(p); Unitaire(new Vector3(Mathf.HalfToFloat(vat.Texels[q]), Mathf.HalfToFloat(vat.Texels[q + 1]), Mathf.HalfToFloat(vat.Texels[q + 2]))); vat.Bornes.Encapsulate(p);
            }
            return vat;
        }
        static ushort U(byte[] d, int o) => (ushort)(d[o] | (d[o + 1] << 8)); static float H(byte[] d, int o) => Mathf.HalfToFloat(U(d, o)); static Vector3 Vec(byte[] d, int o) => new Vector3(H(d, o), H(d, o + 2), H(d, o + 4));
        static void Fini(Vector3 v) { if (!float.IsFinite(v.x) || !float.IsFinite(v.y) || !float.IsFinite(v.z)) throw new InvalidDataException("valeur non finie"); }
        static void Unitaire(Vector3 n) { Fini(n); if (Mathf.Abs(n.magnitude - 1f) > 0.02f) throw new InvalidDataException("normale incohérente"); }
        public static void Verifier()
        {
            string copie = Path.Combine(Application.dataPath, Relatif), source = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "local3d", "civils", "sorties", "civil.vat"));
            try
            {
                var octets = File.ReadAllBytes(copie);
                if (Array.IndexOf(Environment.GetCommandLineArgs(), "-forge786TronquerVat") >= 0)
                {
                    var coupe = new byte[Math.Max(0, octets.Length - 7)]; Buffer.BlockCopy(octets, 0, coupe, 0, coupe.Length); string message;
                    try { Lire(coupe); message = "longueur tronquée acceptée"; } catch (InvalidDataException e) { message = "longueur invalide : " + e.Message; } Sortir(1, message); return;
                }
                if (!Empreinte(copie).Equals(Empreinte(source), StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException("VAT divergent de la source #785");
                AssetDatabase.ImportAsset(ShaderChemin, ImportAssetOptions.ForceUpdate); AssetDatabase.ImportAsset("Assets/" + Relatif, ImportAssetOptions.ForceUpdate);
                var vat = Lire(octets); Mesh mesh = null; Texture2D tex = null; Material mat = null;
                foreach (var o in AssetDatabase.LoadAllAssetsAtPath("Assets/" + Relatif)) if (o is Mesh m) mesh = m; else if (o is Texture2D t) tex = t; else if (o is Material a) mat = a;
                if (!mesh || !tex || !mat) throw new InvalidDataException("sous-assets manquants");
                var tris = mesh.triangles; var cols = mesh.colors; var pos = mesh.vertices; var nor = mesh.normals;
                if (mesh.vertexCount != vat.C || tris.Length != vat.C || cols.Length != vat.C || pos.Length != vat.C || nor.Length != vat.C) throw new InvalidDataException("coins ou couleurs");
                for (int i = 0; i < vat.C; i++) { if (tris[i] != i) throw new InvalidDataException("triangle " + i); if ((pos[i] - vat.Pos[i]).sqrMagnitude > 1e-10f) throw new InvalidDataException("position " + i); if ((nor[i] - vat.Nor[i]).sqrMagnitude > 1e-10f) throw new InvalidDataException("normale " + i); var e = cols[i] - vat.Col[i]; if (Mathf.Abs(e.r) + Mathf.Abs(e.g) + Mathf.Abs(e.b) + Mathf.Abs(e.a) > 0.002f) throw new InvalidDataException("couleur " + i); }
                if ((mesh.bounds.min - vat.Bornes.min).sqrMagnitude > 1e-6f || (mesh.bounds.max - vat.Bornes.max).sqrMagnitude > 1e-6f) throw new InvalidDataException("bornes " + mesh.bounds);
                var px = tex.GetRawTextureData<ushort>(); if (tex.width != 2 * vat.C || tex.height != vat.Images || tex.format != TextureFormat.RGBAHalf || tex.filterMode != FilterMode.Point || tex.wrapMode != TextureWrapMode.Clamp || tex.isDataSRGB || px.Length != vat.Texels.Length) throw new InvalidDataException("texture " + tex.width + "×" + tex.height + " " + tex.format + ", texels " + px.Length); for (int ti = 0; ti < px.Length; ti++) if (px[ti] != vat.Texels[ti]) throw new InvalidDataException("texel " + ti);
                var shader = AssetDatabase.LoadAssetAtPath<Shader>(ShaderChemin); string texte = File.ReadAllText(Path.Combine(Application.dataPath, "ForgeLocal3D/Desert/Shaders/Civil.shader"));
                if (!shader || shader.name != "Forge/CivilVAT" || mat.shader != shader || mat.GetTexture("_VAT") != tex || !texte.Contains("SV_VertexID") || !texte.Contains("_VATActif") || !mat.HasProperty("_Phase") || !mat.HasProperty("_Teinte"))
                    throw new InvalidDataException("shader ou références");
                if (Mathf.Abs(mat.GetFloat("_Coins") - vat.C) > 0.5f || Mathf.Abs(mat.GetFloat("_ImagesMarche") - Attendu[0].images) > 0.5f || mat.GetFloat("_VATActif") < 0.5f) throw new InvalidDataException("références du matériau incomplètes");
                string clips = ""; foreach (var k in vat.Clips) clips += (clips.Length == 0 ? "" : ", ") + k.n + " " + k.i + " / " + k.d.ToString("0.00", System.Globalization.CultureInfo.InvariantCulture) + " s";
                int entete = 12 + 24 * vat.Clips.Length, teinte = entete + 12, pose = entete + 20 * vat.C; foreach (var piege in new (int o, int n, uint b)[] { (32, 4, 0x7FC00000u), (teinte, 2, 0x7E00u), (teinte + 2, 2, 0x7E00u), (teinte + 4, 2, 0x7E00u), (entete, 2, 0x7E00u), (pose, 2, 0x7E00u) }) { var x = (byte[])octets.Clone(); for (int i = 0; i < piege.n; i++) x[piege.o + i] = (byte)(piege.b >> (8 * i)); var accepte = false; try { Lire(x); accepte = true; } catch (InvalidDataException) { } if (accepte) throw new InvalidDataException("valeur non finie acceptée à l'octet " + piege.o); }
                Sortir(0, "CIVIL " + (vat.C / 3) + " triangles, " + vat.C + " coins ; " + clips + " ; bornes " + vat.Bornes.min.ToString("F3") + " → " + vat.Bornes.max.ToString("F3") + " ; texture " + tex.width + "×" + tex.height + " RGBAHalf linéaire Point Clamp ; shader " + shader.name + " ; non finis refusés");
            }
            catch (Exception e) when (e is not InvalidOperationException) { Sortir(1, e.Message); }
        }
        static void Sortir(int code, string message) { if (code == 0) Debug.Log(message); else Debug.LogError("CIVIL REFUS : " + message); EditorApplication.Exit(code); if (code != 0) throw new InvalidOperationException(message); }
        static string Empreinte(string chemin) { using var sha = SHA256.Create(); using var flux = File.OpenRead(chemin); return BitConverter.ToString(sha.ComputeHash(flux)).Replace("-", ""); }
    }
}
