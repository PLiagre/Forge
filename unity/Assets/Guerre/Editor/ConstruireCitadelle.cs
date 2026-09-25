using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Unity.Mathematics;
using UnityEditor;
using UnityEngine;
using Object = UnityEngine.Object;

namespace Guerre.EditeurOutils
{
    // La citadelle, recomposée avec le kit de la Citadelle de Forge. Le kit est relu à chaque construction
    // dans ../ForgeLocal3D (jamais modifié) et copié dans Assets/Guerre/Kit, qui n'entre pas dans git :
    // il appartient à Forge. La citadelle se dresse sur un éperon du versant nord, cerné d'un ravin que
    // franchit un seul pont ; l'enceinte, la porte, les rues, les places et la cathédrale sont posées ici.
    public static partial class Construire
    {
        const string Kit = Dossier + "/Kit";
        static string Forge => Path.GetFullPath(Path.Combine(Application.dataPath, "../../../ForgeLocal3D/local3d/citadelle/sorties"));

        // L'éperon : son centre, la hauteur du plateau, le ravin qui le cerne.
        static readonly float2 Eperon = new float2(1900f, 1640f);
        const float Plateau = 62f, RavinDedans = 109.5f, RavinDehors = 122.5f, RavinProfond = 18f, PenteColline = 0.18f;
        const float RayonMurs = 95.54f;   // un polygone de soixante côtés de 10 m

        static readonly string[] Modules =
        {
            "rempart_10m", "tour_0", "tour_2", "porte_ogive", "pont_arche_14m",
            "maison_gothique_0", "maison_gothique_1", "maison_gothique_2", "maison_gothique_3", "maison_gothique_4", "maison_gothique_5",
            "maison_modulaire_0", "maison_modulaire_1", "maison_modulaire_2", "maison_modulaire_3", "maison_modulaire_4", "maison_modulaire_5",
            "cathedrale_facade", "cathedrale_nef_12m", "cathedrale_clocher", "sapin_neige_0", "sapin_neige_1", "sapin_neige_2", "torche", "banniere",
        };

        // Le relief de l'éperon, ajouté à celui de la vallée : un plateau, un ravin aux parois droites,
        // puis une colline qui descend à 18 % jusqu'au terrain naturel.
        static float Relief(float wx, float wz, float naturel)
        {
            float r = math.distance(new float2(wx, wz), Eperon);
            if (r <= RavinDedans) return Plateau;
            if (r < RavinDehors)
            {
                float bord = math.min(r - RavinDedans, RavinDehors - r);
                return Plateau - RavinProfond * math.saturate(bord / 1.2f);
            }
            float colline = Plateau - PenteColline * (r - RavinDehors);
            // Un raccord doux entre la colline et la vallée, sur quelques mètres.
            float k = 4f, hmax = math.max(colline, naturel), hmin = math.min(colline, naturel);
            return hmax + math.max(0f, k - (hmax - hmin)) * math.max(0f, k - (hmax - hmin)) / (4f * k);
        }

        // Copie du kit depuis Forge, textures et matériaux URP, réglages d'import des modèles.
        static Dictionary<string, GameObject> ImporterKit()
        {
            if (!Directory.Exists(Forge)) throw new Exception("kit de Forge introuvable : " + Forge);
            Directory.CreateDirectory(Kit + "/Modeles"); Directory.CreateDirectory(Kit + "/Textures"); Directory.CreateDirectory(Kit + "/Materiaux");
            foreach (var m in Modules) Copier(Path.Combine(Forge, "bibliotheque", m + ".fbx"), Kit + "/Modeles/" + m + ".fbx");
            var noms = new List<string>();
            foreach (var f in Directory.GetFiles(Path.Combine(Forge, "textures"), "*_BaseColor.png"))
            {
                string nom = Path.GetFileName(f).Replace("_BaseColor.png", "");
                if (nom.StartsWith("montagne_") || nom.StartsWith("marche_")) continue;
                noms.Add(nom);
                foreach (var carte in new[] { "BaseColor", "Normal", "MetallicGloss" })
                    Copier(Path.Combine(Forge, "textures", nom + "_" + carte + ".png"), Kit + "/Textures/" + nom + "_" + carte + ".png");
            }
            AssetDatabase.Refresh();

            var shader = Shader.Find("Universal Render Pipeline/Lit");
            var materiaux = new Dictionary<string, Material>();
            foreach (var nom in noms)
            {
                Texture2D T(string carte, bool normale, bool srgb)
                {
                    string p = Kit + "/Textures/" + nom + "_" + carte + ".png";
                    var ti = (TextureImporter)AssetImporter.GetAtPath(p);
                    if (ti == null) return null;
                    var type = normale ? TextureImporterType.NormalMap : TextureImporterType.Default;
                    if (ti.textureType != type || ti.sRGBTexture != srgb || ti.maxTextureSize != 1024)
                    { ti.textureType = type; ti.sRGBTexture = srgb; ti.maxTextureSize = 1024; ti.SaveAndReimport(); }
                    return AssetDatabase.LoadAssetAtPath<Texture2D>(p);
                }
                string chemin = Kit + "/Materiaux/" + nom + ".mat";
                var mat = AssetDatabase.LoadAssetAtPath<Material>(chemin);
                if (mat == null) { mat = new Material(shader); AssetDatabase.CreateAsset(mat, chemin); }
                mat.shader = shader;
                mat.SetTexture("_BaseMap", T("BaseColor", false, true));
                var n = T("Normal", true, false);
                if (n) { mat.SetTexture("_BumpMap", n); mat.EnableKeyword("_NORMALMAP"); }
                var mg = T("MetallicGloss", false, false);
                if (mg) { mat.SetTexture("_MetallicGlossMap", mg); mat.EnableKeyword("_METALLICSPECGLOSSMAP"); mat.SetFloat("_Smoothness", 1f); }
                if (nom == "lumiere")
                {
                    mat.EnableKeyword("_EMISSION");
                    mat.SetColor("_EmissionColor", new Color(1f, 0.62f, 0.3f) * 2.5f);
                    mat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None;
                }
                EditorUtility.SetDirty(mat);
                materiaux[nom] = mat;
            }
            AssetDatabase.SaveAssets();

            var modeles = new Dictionary<string, GameObject>();
            foreach (var m in Modules)
            {
                string p = Kit + "/Modeles/" + m + ".fbx";
                var mi = (ModelImporter)AssetImporter.GetAtPath(p);
                bool change = false;
                if (!mi.bakeAxisConversion || mi.importCameras || mi.importLights || mi.animationType != ModelImporterAnimationType.None || mi.addCollider)
                {
                    mi.bakeAxisConversion = true; mi.importCameras = false; mi.importLights = false;
                    mi.animationType = ModelImporterAnimationType.None; mi.addCollider = false; mi.isReadable = false;
                    mi.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
                    change = true;
                }
                if (change) mi.SaveAndReimport();
                // Les matériaux du modèle sont remplacés par ceux du kit, du même nom.
                foreach (var em in AssetDatabase.LoadAllAssetsAtPath(p).OfType<Material>().ToArray())
                {
                    string nom = em.name;
                    int point = nom.IndexOf('.');
                    if (point > 0) nom = nom.Substring(0, point);
                    if (materiaux.TryGetValue(nom, out var mat)) { mi.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), em.name), mat); change = true; }
                }
                if (change) mi.SaveAndReimport();
                modeles[m] = AssetDatabase.LoadAssetAtPath<GameObject>(p);
            }
            return modeles;
        }

        static void Copier(string source, string cible)
        {
            if (!File.Exists(source)) throw new Exception("module absent du kit de Forge : " + source);
            var s = new FileInfo(source);
            var c = new FileInfo(cible);
            if (c.Exists && c.Length == s.Length && c.LastWriteTimeUtc >= s.LastWriteTimeUtc) return;
            File.Copy(source, cible, true);
        }

        // L'emprise au sol d'un modèle, dans son repère : les limites de son niveau de détail le plus fin.
        static Bounds Emprise(GameObject modele)
        {
            var go = (GameObject)PrefabUtility.InstantiatePrefab(modele);
            go.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
            var rs = go.GetComponentsInChildren<Renderer>().Where(x => x.name.EndsWith("LOD0")).ToArray();
            if (rs.Length == 0) rs = go.GetComponentsInChildren<Renderer>();
            var b = rs[0].bounds;
            foreach (var x in rs) b.Encapsulate(x.bounds);
            Object.DestroyImmediate(go);
            return b;
        }

        sealed class Chantier
        {
            public Transform Racine;
            public CarteDonnees Donnees;
            public Dictionary<string, GameObject> Modeles;
            public Dictionary<string, Bounds> Emprises = new Dictionary<string, Bounds>();
            public TerrainData Td;

            public Bounds E(string m) { if (!Emprises.TryGetValue(m, out var b)) Emprises[m] = b = Emprise(Modeles[m]); return b; }

            // Pose un module ; theta en degrés autour de la verticale ; y sur le sol, sauf hauteur donnée.
            public GameObject Poser(string m, float2 p, float theta, float? y = null)
            {
                var go = (GameObject)PrefabUtility.InstantiatePrefab(Modeles[m], Racine);
                float h = y ?? Td.GetInterpolatedHeight(p.x / Td.size.x, p.y / Td.size.z);
                go.transform.SetPositionAndRotation(new Vector3(p.x, h, p.y), Quaternion.Euler(0, theta, 0));
                GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic);
                return go;
            }

            // Une emprise bloquée : un rectangle du repère du module (centre et demi-côtés), tourné comme lui.
            public void Bloquer(string nature, float2 p, float theta, Vector2 centreLocal, Vector2 demi)
            {
                float t = theta * Mathf.Deg2Rad;
                var c = new Vector2(p.x + centreLocal.x * Mathf.Cos(t) + centreLocal.y * Mathf.Sin(t), p.y - centreLocal.x * Mathf.Sin(t) + centreLocal.y * Mathf.Cos(t));
                Donnees.blocs.Add(new CarteDonnees.Bloc { nature = nature, centre = c, demi = demi, angle = -t });
            }

            public void BloquerTout(string nature, string m, float2 p, float theta, float marge = 0f)
            {
                var b = E(m);
                Bloquer(nature, p, theta, new Vector2(b.center.x, b.center.z), new Vector2(b.extents.x + marge, b.extents.z + marge));
            }

            public bool Libre(float2 p, float theta, Bounds b, float marge)
            {
                float t = theta * Mathf.Deg2Rad;
                for (int i = 0; i <= 4; i++)
                    for (int j = 0; j <= 4; j++)
                    {
                        float lx = b.min.x - marge + (b.size.x + 2 * marge) * i / 4f, lz = b.min.z - marge + (b.size.z + 2 * marge) * j / 4f;
                        var w = new Vector2(p.x + lx * Mathf.Cos(t) + lz * Mathf.Sin(t), p.y - lx * Mathf.Sin(t) + lz * Mathf.Cos(t));
                        if (Donnees.blocs.Any(x => CarteDonnees.Dans(x, w))) return false;
                        if (Reserves.Any(x => CarteDonnees.Dans(x, w))) return false;
                        if (math.distance(new float2(w.x, w.y), Eperon) > 86f) return false;
                    }
                return true;
            }

            public List<CarteDonnees.Bloc> Reserves = new List<CarteDonnees.Bloc>();
            public void Reserver(float2 centre, Vector2 demi) => Reserves.Add(new CarteDonnees.Bloc { nature = "rue", centre = new Vector2(centre.x, centre.y), demi = demi });
        }

        static CarteDonnees BatirCitadelle(Transform racine, TerrainData td, Dictionary<string, GameObject> modeles)
        {
            var donnees = ScriptableObject.CreateInstance<CarteDonnees>();
            var ch = new Chantier { Racine = racine, Donnees = donnees, Modeles = modeles, Td = td };
            float2 P = Eperon;
            float2 L(float x, float z) => P + new float2(x, z);   // repère de la ville : x vers l'est, z vers le nord

            // Le rempart : son corps est d'un côté de son axe ; le chemin de ronde déborde vers l'intérieur.
            // On lit de quel côté l'import l'a mis (Blender y devient Unity -z ou +z).
            var er = ch.E("rempart_10m");
            float signe = er.max.z > 2f ? -1f : 1f;              // z Unity = signe × y Blender
            float zCorps0 = math.min(signe * -2.5f, signe * -1.25f), zCorps1 = math.max(signe * -2.5f, signe * -1.25f);
            Debug.Log($"[Construire] rempart : emprise z {er.min.z:0.00}..{er.max.z:0.00}, corps z {zCorps0:0.00}..{zCorps1:0.00}");
            float apotheme = RayonMurs * math.cos(math.radians(3f));
            for (int k = 1; k < 60; k++)
            {
                float phi = math.radians(-90f + 6f * k);
                float2 p = P + apotheme * new float2(math.cos(phi), math.sin(phi));
                // L'intérieur du rempart (repère local +y Blender) regarde le centre de la ville.
                float theta = math.degrees(math.atan2(-signe * math.cos(phi), -signe * math.sin(phi)));
                ch.Poser("rempart_10m", p, theta, Plateau);
                ch.Bloquer("rempart", p, theta, new Vector2(0, (zCorps0 + zCorps1) / 2), new Vector2(5.05f, (zCorps1 - zCorps0) / 2 + 0.15f));
            }
            // La porte, au sud, dans l'axe du pont : ses deux piédroits laissent un passage de 4,5 m.
            var ep = ch.E("porte_ogive");
            float2 porte = L(0, -apotheme);
            ch.Poser("porte_ogive", porte, 0, Plateau);
            foreach (float cote in new[] { -1f, 1f })
                ch.Bloquer("porte", porte, 0, new Vector2(cote * 4.05f, ep.center.z), new Vector2(1.8f, ep.extents.z));
            Debug.Log($"[Construire] porte : emprise x {ep.min.x:0.00}..{ep.max.x:0.00}, z {ep.min.z:0.00}..{ep.max.z:0.00}");
            // Les tours : deux petites qui flanquent la porte (un segment plus loin, pour ne pas boucher le passage),
            // huit grandes le long de l'enceinte.
            foreach (float a in new[] { -99f, -81f })
            {
                float2 p = P + RayonMurs * new float2(math.cos(math.radians(a)), math.sin(math.radians(a)));
                ch.Poser("tour_2", p, a, Plateau); ch.BloquerTout("tour", "tour_2", p, a);
            }
            for (int m = 1; m <= 8; m++)
            {
                float a = -87f + 36f * m;
                float2 p = P + RayonMurs * new float2(math.cos(math.radians(a)), math.sin(math.radians(a)));
                ch.Poser("tour_0", p, a, Plateau); ch.BloquerTout("tour", "tour_0", p, a);
            }
            // Le pont, au sud, par-dessus le ravin : son tablier est au niveau du plateau, entre deux parapets.
            var eb = ch.E("pont_arche_14m");
            float2 pont = L(0, -(RavinDedans + RavinDehors) / 2);
            ch.Poser("pont_arche_14m", pont, 0, Plateau);
            donnees.tabliers.Add(new CarteDonnees.Tablier { nom = "pont", centre = new Vector2(pont.x, pont.y), demi = new Vector2(4f, eb.extents.z), angle = 0, hauteur = Plateau });
            foreach (float cote in new[] { -1f, 1f })
                ch.Bloquer("parapet", pont, 0, new Vector2(cote * 3.125f, 0), new Vector2(0.4f, eb.extents.z));
            Debug.Log($"[Construire] pont : emprise x {eb.min.x:0.00}..{eb.max.x:0.00}, y {eb.min.y:0.00}..{eb.max.y:0.00}, z {eb.min.z:0.00}..{eb.max.z:0.00}");
            // Deux torches devant la porte.
            foreach (float cote in new[] { -1f, 1f }) ch.Poser("torche", L(cote * 3.6f, -apotheme - 4f), 0, Plateau);

            // Les rues et les places, réservées avant qu'on bâtisse : la grand-rue de la porte à la place,
            // la rue traversière, la place de la cathédrale, la place de l'est.
            ch.Reserver(L(0, -60f), new Vector2(4f, 36f));          // grand-rue, 8 m
            ch.Reserver(L(0, -55f), new Vector2(84f, 3.5f));        // rue traversière, 7 m
            ch.Reserver(L(0, -5f), new Vector2(25f, 20f));          // place de la cathédrale
            ch.Reserver(L(48f, -55f), new Vector2(10f, 13f));       // place de l'est
            ch.Reserver(L(0, -93f), new Vector2(6f, 4f));           // l'entrée sous la porte

            // La cathédrale, au nord de la place : la façade, deux travées de nef, le clocher.
            var ef = ch.E("cathedrale_facade"); var en = ch.E("cathedrale_nef_12m"); var ec = ch.E("cathedrale_clocher");
            float zf = 15f + ef.size.z / 2 + 1f;
            ch.Poser("cathedrale_facade", L(0, zf), 180, Plateau); ch.BloquerTout("cathedrale", "cathedrale_facade", L(0, zf), 180);
            float zn = zf + ef.size.z / 2 + en.size.z / 2;
            for (int k = 0; k < 2; k++)
            {
                float2 p = L(0, zn + k * en.size.z);
                ch.Poser("cathedrale_nef_12m", p, 180, Plateau); ch.BloquerTout("cathedrale", "cathedrale_nef_12m", p, 180);
            }
            float2 clocher = L(-(en.extents.x + ec.extents.x + 1f), zf + 4f);
            ch.Poser("cathedrale_clocher", clocher, 0, Plateau); ch.BloquerTout("cathedrale", "cathedrale_clocher", clocher, 0);

            // Les maisons, en rangs serrés le long des rues : leur façade (le côté -z du modèle) donne sur la rue.
            var alea = new Unity.Mathematics.Random(1400);
            var maisons = Modules.Where(m => m.StartsWith("maison")).ToArray();
            int posees = 0;
            bool Maison(float2 p, float theta)
            {
                string m = maisons[alea.NextInt(maisons.Length)];
                var b = ch.E(m);
                if (!ch.Libre(p, theta, b, 0.15f)) return false;
                ch.Poser(m, p, theta, Plateau);
                ch.BloquerTout("maison", m, p, theta, 0.1f);
                posees++;
                return true;
            }
            // Le long de la grand-rue, des deux côtés ; le long de la rue traversière ; autour de la place.
            for (float z = -88f; z < -28f; z += 8.2f) { Maison(L(-9f, z), 90); Maison(L(9f, z), -90); Maison(L(-18.5f, z), 90); Maison(L(18.5f, z), -90); }
            for (float x = -80f; x < 80f; x += 8.2f) { Maison(L(x, -46.5f), 180); Maison(L(x, -63.5f), 0); Maison(L(x, -37f), 180); Maison(L(x, -73f), 0); }
            for (float z = -22f; z < 14f; z += 8.2f) { Maison(L(-30f, z), 90); Maison(L(30f, z), -90); }
            // Le reste de la ville se remplit d'îlots, là où il reste de la place.
            for (float z = -84f; z < 84f; z += 9f)
                for (float x = -84f; x < 84f; x += 9f)
                    Maison(L(x + alea.NextFloat(-1f, 1f), z + alea.NextFloat(-1f, 1f)), 90f * alea.NextInt(4));
            Debug.Log($"[Construire] citadelle : {posees} maisons, {donnees.blocs.Count} emprises bloquées");

            // Les sapins sur les pentes de la colline, hors du chemin qui monte au pont.
            for (int k = 0; k < 400 && racine.childCount < 2000; k++)
            {
                float a = alea.NextFloat(0, 2 * math.PI), r = alea.NextFloat(RavinDehors + 12f, 280f);
                float2 p = P + r * new float2(math.cos(a), math.sin(a));
                if (math.abs(p.x - P.x) < 30f && p.y < P.y) continue;
                ch.Poser("sapin_neige_" + alea.NextInt(3), p, alea.NextFloat(0, 360));
                ch.Bloquer("arbre", p, 0, Vector2.zero, new Vector2(0.5f, 0.5f));
            }

            // Les lieux que visent les essais.
            float Axe(float x) => 1200f + 90f * math.sin(x / 520f);
            donnees.lieux.Add(new CarteDonnees.Lieu { nom = "citadelle", p = new Vector2(P.x, P.y), front = new Vector2(0, 1) });
            donnees.lieux.Add(new CarteDonnees.Lieu { nom = "pied", p = new Vector2(P.x, P.y - 300f), front = new Vector2(0, 1) });
            donnees.lieux.Add(new CarteDonnees.Lieu { nom = "place", p = new Vector2(P.x, P.y - 5f), front = new Vector2(0, 1) });
            donnees.lieux.Add(new CarteDonnees.Lieu { nom = "place_est", p = new Vector2(P.x + 48f, P.y - 55f), front = new Vector2(1, 0) });
            donnees.lieux.Add(new CarteDonnees.Lieu { nom = "porte", p = new Vector2(porte.x, porte.y), front = new Vector2(0, 1) });
            donnees.lieux.Add(new CarteDonnees.Lieu { nom = "vallee_depart", p = new Vector2(600f, Axe(600f)), front = new Vector2(1, 0) });
            donnees.lieux.Add(new CarteDonnees.Lieu { nom = "vallee_arrivee", p = new Vector2(1350f, Axe(1350f)), front = new Vector2(1, 0) });

            string chemin = Dossier + "/Carte/Citadelle.asset";
            AssetDatabase.DeleteAsset(chemin);
            AssetDatabase.CreateAsset(donnees, chemin);
            AssetDatabase.SaveAssets();
            return AssetDatabase.LoadAssetAtPath<CarteDonnees>(chemin);
        }
    }
}
