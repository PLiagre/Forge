using System;
using System.Collections;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using Forge.Pont;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering.Universal;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures
{
    // Lot 786 : civil témoin près de Biskra, phases 1/4 et 3/4, Transform immobile. -forge786SansAnimation fige la pose.
    static class Lot786
    {
        const string Chemin = "Assets/ForgeLocal3D/Desert/Civils/civil.vat"; const int W = 1600, H = 900;
        static Exception Faux(string m) => new InvalidOperationException(m);
        [ScenarioDeCapture(786, "marche-position-fixe")]
        static IEnumerator MarchePositionFixe(Camera camera)
        {
            Mesh mesh = null; Texture2D tex = null; Material src = null;
            foreach (var o in AssetDatabase.LoadAllAssetsAtPath(Chemin)) if (o is Mesh m && !mesh) mesh = m; else if (o is Texture2D t && !tex) tex = t; else if (o is Material a && !src) src = a;
            if (!mesh || !tex || !src || src.shader == null || src.shader.name != "Forge/CivilVAT" || src.GetTexture("_VAT") != tex) throw Faux("référence absente : " + Chemin);
            var args = Environment.GetCommandLineArgs(); int id = Array.IndexOf(args, "-forgeCaptures");
            string dossier = id >= 0 && id + 1 < args.Length ? args[id + 1] : SessionState.GetString("Forge.Capture.Dossier", "");
            if (string.IsNullOrEmpty(dossier)) throw Faux("dossier de capture absent");
            string quart = Path.Combine(dossier, "lot786-quart.png"), trois = Path.Combine(dossier, "lot786-trois-quarts.png"), rapport = Path.Combine(dossier, "lot786-rapport.json");
            if (File.Exists(quart) || File.Exists(trois) || File.Exists(rapport)) throw Faux("image antérieure déjà présente");
            var ville = camera.GetComponent<DesertCityCamera>() ?? throw Faux("pas de caméra de ville"); var outil = ville.outil ?? throw Faux("pas d'outil");
            ville.automatique = true; if (ville.Marcheur) ville.Marcheur.automatic = true;
            var lus = System.Threading.Tasks.Task.Run(() => { using var d = new ClientDeparts(outil.Port, ClientDeparts.DelaiMinimal); return d.Lire(); });
            while (!lus.IsCompleted) yield return null;
            if (lus.IsFaulted || !lus.Result.Presente) throw Faux(lus.IsFaulted ? lus.Exception.GetBaseException().Message : lus.Result.Absence);
            var zab = lus.Result.Donnees.Fiches.Where(f => f.Siege.Nom == "Biskra").ToArray();
            if (zab.Length != 1 || !outil.Ouvrir(zab[0].CellId)) throw Faux(zab.Length != 1 ? zab.Length + " sièges Biskra" : outil.Message);
            var terrain = outil.roads != null ? outil.roads.terrain : null; var racine = outil.Maisons != null ? outil.Maisons.Racine : null;
            if (!terrain || !racine || racine.childCount == 0) throw Faux("Biskra sans sol ni maison");
            var bo = new Bounds(racine.GetChild(0).position, Vector3.zero); for (int i = 0; i < racine.childCount; i++) bo.Encapsulate(racine.GetChild(i).position);
            float Sy(Vector3 p) => terrain.SampleHeight(p) + terrain.transform.position.y; Vector3 pieds = bo.center; float mieux = 1e9f;
            for (int k = 0; k < 8; k++) { var dir = Quaternion.Euler(0, 45f * k, 0) * Vector3.forward; var p = bo.center + dir * (bo.extents.magnitude + 8f); float pente = Mathf.Abs(Sy(p) - Sy(p + dir * 3f)); if (pente < mieux) { mieux = pente; pieds = new Vector3(p.x, Sy(p), p.z); } }
            var ori = terrain.transform.position; var sz = terrain.terrainData.size;
            pieds.x = Mathf.Clamp(pieds.x, ori.x + 4f, ori.x + sz.x - 4f); pieds.z = Mathf.Clamp(pieds.z, ori.z + 4f, ori.z + sz.z - 4f); pieds.y = Sy(pieds);
            var dehors = pieds - bo.center; dehors.y = 0; if (dehors.sqrMagnitude < 1f) dehors = Vector3.forward; dehors.Normalize(); float cap = Mathf.Atan2(-dehors.x, -dehors.z) * Mathf.Rad2Deg;
            var go = new GameObject("Civil de Biskra"); go.transform.SetPositionAndRotation(pieds, Quaternion.Euler(0, cap + 255f, 0));
            go.AddComponent<MeshFilter>().sharedMesh = mesh; var rendu = go.AddComponent<MeshRenderer>(); var mat = new Material(src); rendu.sharedMaterial = mat;
            bool gele = Array.IndexOf(args, "-forge786SansAnimation") >= 0; mat.SetFloat("_VATActif", gele ? 0f : 1f);
            var urp = camera.GetComponent<UniversalAdditionalCameraData>(); if (urp) { urp.antialiasing = AntialiasingMode.None; urp.renderPostProcessing = false; }
            camera.aspect = (float)W / H; const float incl = 17f; float recul = 0.95f / Mathf.Tan(incl * Mathf.Deg2Rad); Rect pix = default; bool cadre = false;
            for (float dist = 8f; dist <= 20f && !cadre; dist += 3f) { ville.Poser(pieds - dehors * recul, cap, incl, dist); cadre = Dans(camera, rendu.bounds, out pix); }
            if (!cadre) throw Faux("civil hors champ"); foreach (var ps in Object.FindObjectsByType<ParticleSystem>(FindObjectsSortMode.None)) ps.Pause(true);
            var p0 = go.transform.position; var r0 = go.transform.rotation; var s0 = go.transform.localScale; var c0 = camera.transform.position; var q0 = camera.transform.rotation;
            mat.SetFloat("_Phase", 0.25f); var ia = CitadelPlayCheck.Capture(camera, quart, W, H); mat.SetFloat("_Phase", 0.75f); var ib = CitadelPlayCheck.Capture(camera, trois, W, H);
            if (go.transform.position != p0 || go.transform.rotation != r0 || go.transform.localScale != s0 || camera.transform.position != c0 || camera.transform.rotation != q0) throw Faux("Transform changé");
            int x0 = Mathf.Clamp(Mathf.FloorToInt(pix.xMin), 0, W - 1), y0 = Mathf.Clamp(Mathf.FloorToInt(pix.yMin), 0, H - 1), x1 = Mathf.Clamp(Mathf.CeilToInt(pix.xMax), x0 + 1, W), y1 = Mathf.Clamp(Mathf.CeilToInt(pix.yMax), y0 + 1, H);
            if (ia == null || ib == null || ia.Length != W * H || ib.Length != ia.Length) throw Faux("mesure vide");
            int compares = 0, changes = 0; for (int y = y0; y < y1; y++) for (int x = x0; x < x1; x++) { compares++; var pa = ia[y * W + x]; var pb = ib[y * W + x]; if (pa.r != pb.r || pa.g != pb.g || pa.b != pb.b) changes++; }
            if (compares == 0) throw Faux("mesure vide");
            string F(float v) => v.ToString("G6", CultureInfo.InvariantCulture); var tr = go.transform;
            File.WriteAllText(rapport, "{\"phase\":[0.25,0.75],\"position\":[" + F(tr.position.x) + "," + F(tr.position.y) + "," + F(tr.position.z) + "],\"rotation\":[" + F(tr.rotation.x) + "," + F(tr.rotation.y) + "," + F(tr.rotation.z) + "," + F(tr.rotation.w) + "],\"echelle\":[" + F(tr.localScale.x) + "," + F(tr.localScale.y) + "," + F(tr.localScale.z) + "],\"rectangle\":[" + x0 + "," + y0 + "," + x1 + "," + y1 + "],\"pixels_compares\":" + compares + ",\"pixels_changes\":" + changes + ",\"sans_animation\":" + (gele ? "true" : "false") + "}\n", new UTF8Encoding(false));
            Debug.Log("CIVIL_PHOTO phase 1/4 et 3/4, pixels " + changes + "/" + compares + (gele ? ", animation coupée" : ""));
            if (gele) { if (changes != 0) throw Faux("animation coupée mais " + changes + " pixels ont changé"); throw Faux("la marche a disparu"); }
            if (changes == 0) throw Faux("aucun pixel changé entre les deux phases");
            for (int i = 0; i < 4; i++) yield return null;
        }
        static bool Dans(Camera c, Bounds b, out Rect pix)
        {
            float x0 = 1, y0 = 1, x1 = 0, y1 = 0; bool ok = true; var e = b.extents; var centre = b.center;
            for (int i = 0; i < 8; i++) { var p = centre + Vector3.Scale(e, new Vector3((i & 1) * 2 - 1, ((i >> 1) & 1) * 2 - 1, ((i >> 2) & 1) * 2 - 1)); var v = c.WorldToViewportPoint(p); if (v.z <= 0 || v.x < 0.03f || v.x > 0.97f || v.y < 0.03f || v.y > 0.97f) ok = false; x0 = Mathf.Min(x0, v.x); x1 = Mathf.Max(x1, v.x); y0 = Mathf.Min(y0, v.y); y1 = Mathf.Max(y1, v.y); }
            pix = Rect.MinMaxRect(x0 * W, y0 * H, x1 * W, y1 * H); return ok;
        }
    }
}
