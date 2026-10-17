using System;
using System.Globalization;
using System.IO;
using System.Net;
using System.Reflection;
using System.Text;
using System.Threading;
using UnityEditor;
using UnityEngine;
namespace ForgeLocal3D
{
    public static class DesertCityRelief
    {
        const int Attendu = 21, N = 513; const float Bas = -8f, Haut = 40f; const string Id = "ksar_des_sept_puits";
        public static void Verifier()
        {
            Svc svc = null; int code = 1;
            try { code = Jouer(out svc) ? 0 : 1; }
            catch (Exception e) { Debug.LogException(e); code = 1; }
            finally { svc?.Dispose(); Debug.Log("RELIEF code " + code); EditorApplication.Exit(code); }
        }
        static bool Jouer(out Svc svc)
        {
            svc = null; int cas = 0; bool echec = false;
            void Cas(bool ok, string nom) { cas++; if (ok) Debug.Log("RELIEF ok " + cas + " " + nom); else { echec = true; Debug.LogError("RELIEF ECHEC " + cas + " " + nom); } }
            var td = new TerrainData(); td.heightmapResolution = N; td.size = new Vector3(1024, Haut, 1024); td.alphamapResolution = 32; td.SetDetailResolution(16, 8);
            td.terrainLayers = new[] { new TerrainLayer() }; td.detailPrototypes = new DetailPrototype[0];
            double pas = 1024.0 / (N - 1), moitie = 512; int centre = (N - 1) / 2, ip = centre - 40;
            var h = new float[N, N];
            for (int j = 0; j < N; j++) for (int i = 0; i < N; i++) h[j, i] = (float)((10 + 0.015 * (moitie - i * pas) + 2 * Math.Sin((moitie - j * pas) * 0.02) - Bas) / Haut);
            h[ip, ip] = (float)((-1.0 - Bas) / Haut); td.SetHeights(0, 0, h);
            var go = Terrain.CreateTerrainGameObject(td); go.transform.position = new Vector3(0, Bas, 0);
            var terrain = go.GetComponent<Terrain>(); var routes = new GameObject("routes").AddComponent<DesertRoads>();
            routes.transform.SetParent(go.transform, false); routes.terrain = terrain; routes.terreBattue = new TerrainLayer(); routes.paves = new TerrainLayer(); routes.implantation = Id;
            var outil = new GameObject("outil").AddComponent<DesertRoadTool>(); outil.roads = routes; outil.view = new GameObject("cam").AddComponent<Camera>();
            string json = File.ReadAllText(DesertRoads.CheminGestes(Id)); var lu = DesertRoads.Lire(Id); var p = lu.parametres;
            double Cle(string cle) { int i = json.IndexOf("\"" + cle + "\"", StringComparison.Ordinal), a = json.IndexOf(':', i) + 1; while (json[a] <= ' ') a++; int b = a; while ("0123456789+-.eE".IndexOf(json[b]) >= 0) b++; return double.Parse(json.Substring(a, b - a), CultureInfo.InvariantCulture); }
            Cas(p.pivot < 0, "pivot " + p.pivot.ToString("R", CultureInfo.InvariantCulture));
            bool absent = false; try { DesertRoads.ControlerRelief(json.Replace("\"relief_nul\":", "\"relief_nul_omis\":"), p); } catch (InvalidOperationException e) { absent = e.Message.Contains("relief_nul"); }
            Cas(absent, "paramètre absent");
            Cas(routes.FacteurRelief == 1, "facteur initial");
            string assetAvant = DesertRoads.Empreintes(td).Tout; routes.AppliquerRelief(2, "essai"); bool jete = false;
            try { routes.Preparer(new DesertRoads.Parametres { relief_plein = p.relief_plein, relief_nul = -1, pivot = p.pivot }, 1); } catch (InvalidOperationException) { jete = true; }
            Cas(jete && terrain.terrainData == td && DesertRoads.Empreintes(td).Tout == assetAvant, "invalide, terrain intact");
            routes.AppliquerRelief(1, null); p.pivot = Bas + td.GetHeights(ip, ip, 1, 1)[0, 0] * Haut;
            routes.Preparer(p, lu.graine); string vierge = routes.Empreintes().Tout; var baseH = routes.Copie.GetHeights(0, 0, N, N);
            double Att(float norm, double f) { if (f == 1) return norm; double m = Bas + norm * Haut; return (p.pivot + (m - p.pivot) * f - Bas) / Haut; }
            double tol = 2.0 / 32766.0; float Lu(int i, int j) => routes.Copie.GetHeights(i, j, 1, 1)[0, 0];
            bool centres = true; string classes = "";
            foreach (var classe in new[] { "plaine", "marais", "colline", "montagne", "haute_montagne" })
            {
                bool resolu = routes.ResoudreRelief(p, classe, out var f, out var cause) && cause == null && Math.Abs(f - Cle("relief_" + classe)) < 1e-9;
                routes.AppliquerRelief(f, classe); routes.Preparer(p, lu.graine);
                float luC = Lu(centre, centre); double att = Att(baseH[centre, centre], Cle("relief_" + classe)); bool plat = classe == "plaine" || classe == "marais";
                bool ok = resolu && (plat ? routes.Empreintes().Tout == vierge && luC == baseH[centre, centre] : Math.Abs(luC - att) <= tol);
                centres &= ok; classes += " " + classe + (ok ? "" : "=ECHEC");
            }
            Cas(centres, "cinq classes" + classes);
            double nul = Cle("relief_nul"), plein = Cle("relief_plein"), f450 = 1 + (Cle("relief_montagne") - 1) * ((nul - 450) / (nul - plein));
            int i450 = centre - (int)Math.Round(450 / pas), iNul = centre - (int)Math.Round(nul / pas);
            routes.ResoudreRelief(p, "montagne", out var fm, out _); routes.AppliquerRelief(fm, "montagne"); routes.Preparer(p, lu.graine);
            Cas(Math.Abs(f450 - 1.15) < 1e-9 && Math.Abs(Math.Abs(moitie - i450 * pas) - 450) < 1e-6 && Math.Abs(Lu(i450, centre) - Att(baseH[centre, i450], f450)) <= tol, "450 m ×1,15");
            Cas(Math.Abs(moitie - iNul * pas) >= 500 && Lu(iNul, centre) == baseH[centre, iNul] && Lu(0, 0) == baseH[0, 0], "bord");
            Cas(Math.Abs(Bas + Lu(ip, ip) * Haut - p.pivot) <= 2 * Haut / 32766.0, "pivot");
            string une = routes.Empreintes().Tout; routes.Preparer(p, lu.graine);
            Cas(routes.Empreintes().Tout == une && Math.Abs(Lu(centre, centre) - Att(baseH[centre, centre], Cle("relief_montagne"))) <= tol, "deux préparations");
            Cas(DesertRoads.Empreintes(td).Tout == assetAvant && routes.Original == td && terrain.terrainData == routes.Copie && terrain.GetComponent<TerrainCollider>().terrainData == routes.Copie, "original et collider");
            var service = svc = new Svc(); typeof(DesertRoadTool).GetMethod("Awake", BindingFlags.Instance | BindingFlags.NonPublic).Invoke(outil, null);
            Cas(outil.TickOuverture == -1, "à froid");
            int cartes = svc.Cartes; Cas(!outil.Ouvrir(-1L) && svc.Cartes == cartes && outil.Message.Contains("invalide") && outil.TickOuverture == -1, "invalide " + outil.Message);
            bool Refus(string mode, string extrait)
            {
                service.Mode = mode; outil.Lancer(new[] { "Forge.exe", "-forgeCell", "7" }, false, null);
                string avant = routes.Empreintes().Tout; int n = outil.Ouverture.Count;
                return !outil.Ouvrir() && outil.TickOuverture == -1 && routes.Empreintes().Tout == avant && outil.Ouverture.Count == n && outil.Message.Contains("7") && outil.Message.Contains(extrait);
            }
            Cas(Refus("erreur", "carte"), "carte " + outil.Message); Cas(Refus("absent", "absente"), "absente " + outil.Message);
            Cas(Refus("omis", "relief absent"), "omis " + outil.Message); Cas(Refus("desert", "desert"), "desert " + outil.Message);
            svc.Mode = "ok"; svc.Cartes = 0; outil.Lancer(new[] { "Forge.exe", "-forgeCell", "7" }, false, null);
            bool premiere = outil.Ouvrir(); float hMont = Lu(centre, centre); bool deuxieme = outil.Ouvrir(); bool rafrai = outil.Rafraichir();
            var mesh = GameObject.Find("Panneau des routes")?.GetComponent<TextMesh>();
            Cas(premiere && deuxieme && rafrai && svc.Cartes == 1 && mesh != null && mesh.text.Contains("Relief : montagne") && !outil.Message.Contains("Relief :"), "une lecture " + svc.Cartes);
            Cas(outil.Ouvrir(8) && svc.Cartes == 1 && mesh.text.Contains("Relief : colline") && Lu(centre, centre) != hMont, "autre relief");
            outil.Lancer(new[] { "Forge.exe", "-forgeCell", "7" }, false, null);
            Cas(outil.Ouvrir() && svc.Cartes == 2 && mesh.text.Contains("Relief : montagne"), "nouveau Lancer " + svc.Cartes);
            string empreinte = routes.Empreintes().Tout; var g = DesertRoads.Lire(Id); routes.Preparer(g.parametres, g.graine);
            var pose = routes.Poser(new DesertRoads.Geste { id = "direct", revetement = "terre", largeur = 4, x = new[] { 0d, 40d }, y = new[] { 0d, 0d } });
            Cas(outil.Ouverture.Exists(e => e.resultat.acceptee) && pose.acceptee && routes.Empreintes().Tout == empreinte, "rue " + (pose.acceptee ? "posée" : pose.motif + " " + pose.message));
            long cell = outil.Cellule, tick = outil.TickOuverture; int dessins = outil.Ouverture.Count, avantCartes = svc.Cartes; string garde = routes.Empreintes().Tout;
            outil.Annuler(); bool conserve = !outil.Ouvrir(99) && outil.Cellule == cell && outil.TickOuverture == tick && outil.Ouverture.Count == dessins && routes.Empreintes().Tout == garde && svc.Cartes == avantCartes;
            Cas(mesh.text.Contains("Relief : montagne") && !outil.Message.Contains("Relief :") && conserve, "conserve " + outil.Message);
            Debug.Log("RELIEF compte " + cas); return !echec && cas == Attendu;
        }
        sealed class Svc : IDisposable
        {
            public int Cartes; public volatile string Mode = "ok";
            readonly HttpListener http = new HttpListener();
            public Svc()
            {
                http.Prefixes.Add("http://127.0.0.1:8000/"); http.Start();
                new Thread(() => { while (http.IsListening) { HttpListenerContext c; try { c = http.GetContext(); } catch { return; } Repondre(c); } }) { IsBackground = true }.Start();
            }
            void Repondre(HttpListenerContext c)
            {
                bool carte = c.Request.Url.AbsolutePath == "/carte"; if (carte) Interlocked.Increment(ref Cartes);
                string corps = !carte ? "{\"cell_id\":" + c.Request.QueryString["cell"] + ",\"tick\":4,\"rues\":[{\"identifiant\":1,\"points\":[[0,0],[40,0]],\"largeur_m\":4,\"en_chantier\":false}],\"parcelles\":[],\"batiments\":[]}" : Carte();
                int st = carte && Mode == "erreur" ? 500 : 200; if (st != 200) corps = "panne";
                var b = Encoding.UTF8.GetBytes(corps); c.Response.StatusCode = st; c.Response.ContentLength64 = b.Length; c.Response.OutputStream.Write(b, 0, b.Length); c.Response.Close();
            }
            static string Cell(long id, string relief) => "{\"cell_id\":" + id + ",\"maison\":null,\"puissance\":null,\"villes\":[]" + (relief == null ? "" : ",\"relief\":\"" + relief + "\"") + ",\"contour\":{\"type\":\"MultiPolygon\",\"coordinates\":[[[[0,0],[1,0],[1,1],[0,0]]]]}}";
            string Carte() { string a = Mode == "omis" ? Cell(7, null) : Mode == "desert" ? Cell(7, "desert") : Mode == "absent" ? null : Cell(7, "montagne"); return "{\"cell_count\":" + (a == null ? 1 : 2) + ",\"crs\":\"EPSG:3035\",\"cells\":[" + (a == null ? "" : a + ",") + Cell(8, "colline") + "]}"; }
            public void Dispose() { try { http.Close(); } catch (Exception) { } }
        }
    }
}
