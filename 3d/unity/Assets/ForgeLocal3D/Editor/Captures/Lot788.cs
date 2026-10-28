using System; using System.Collections; using System.Collections.Generic; using System.Globalization; using System.IO; using System.Linq; using System.Text;
using Forge.Pont; using UnityEditor; using UnityEngine; using Object = UnityEngine.Object;
namespace ForgeLocal3D.Captures
{
    static class Lot788
    {
        static Exception Faux(string m) => new InvalidOperationException(m);
        static string Q(string s) => "\"" + (s ?? "").Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"";
        [ScenarioDeCapture(788, "rue-de-biskra-vivante")]
        static IEnumerator Rue(Camera camera)
        {
            var args = Environment.GetCommandLineArgs(); int id = Array.IndexOf(args, "-forgeCaptures");
            string dossier = id >= 0 && id + 1 < args.Length ? args[id + 1] : SessionState.GetString("Forge.Capture.Dossier", "");
            if (string.IsNullOrEmpty(dossier)) throw Faux("dossier de capture absent");
            string scene = Path.GetFileNameWithoutExtension(string.IsNullOrEmpty(camera.gameObject.scene.path) ? camera.gameObject.scene.name : camera.gameObject.scene.path);
            string png = Path.Combine(dossier, scene + "--rue-de-biskra-vivante.png"), rapport = Path.Combine(dossier, "lot788-rapport.json");
            if (File.Exists(png) || File.Exists(rapport)) throw Faux("image ou rapport antérieur");
            bool garder = Array.IndexOf(args, "-forge788GarderAnciens") >= 0;
            var ville = camera.GetComponent<DesertCityCamera>() ?? throw Faux("pas de caméra de ville"); var outil = ville.outil ?? throw Faux("pas d'outil");
            ville.automatique = outil.automatique = true; if (ville.Marcheur) ville.Marcheur.automatic = true;
            var env = Object.FindFirstObjectByType<DesertEnvironment>(); if (env) env.showPanel = false; var bandeau = GameObject.Find("/Panneau du lieu"); if (bandeau) bandeau.SetActive(false);
            foreach (var tm in Object.FindObjectsByType<TextMesh>(FindObjectsSortMode.None)) tm.gameObject.SetActive(false);
            foreach (var ps in Object.FindObjectsByType<ParticleSystem>(FindObjectsSortMode.None)) ps.Pause(true);
            var departs = System.Threading.Tasks.Task.Run(() => { using var d = new ClientDeparts(outil.Port, ClientDeparts.DelaiMinimal); return d.Lire(); });
            while (!departs.IsCompleted) yield return null;
            if (departs.IsFaulted || !departs.Result.Presente) throw Faux(departs.IsFaulted ? departs.Exception.GetBaseException().Message : departs.Result.Absence);
            var zab = departs.Result.Donnees.Fiches.Where(f => f.Siege.Nom == "Biskra").ToArray();
            if (zab.Length != 1 || !outil.Ouvrir(zab[0].CellId)) throw Faux(zab.Length != 1 ? zab.Length + " sièges Biskra" : outil.Message);
            long cell = zab[0].CellId; var foule = Object.FindFirstObjectByType<PassantsDeLaVille>() ?? throw Faux("foule absente");
            for (double fin = Time.realtimeSinceStartupAsDouble + 30; foule.CelluleAppliquee != cell && Time.realtimeSinceStartupAsDouble < fin;) yield return null;
            if (foule.CelluleAppliquee != cell) throw Faux(foule.Cause ?? "aucune paire appliquée");
            var lu = System.Threading.Tasks.Task.Run(() => { int port = outil.Port; using var a = new ClientLieu(port, TimeSpan.FromSeconds(2)); using var b = new ClientPlan(port, TimeSpan.FromSeconds(2)); return (a.Lire(cell), b.Lire(cell)); });
            while (!lu.IsCompleted) yield return null; if (lu.IsFaulted) throw Faux(lu.Exception.GetBaseException().Message);
            var (lieu, plan) = lu.Result;
            if (!lieu.Presente || !plan.Presente || lieu.Lieu.CellId != cell || plan.Plan.CellId != cell || lieu.Lieu.Tick != plan.Plan.Tick)
                throw Faux(!lieu.Presente ? lieu.Absence : !plan.Presente ? plan.Absence : "paire incohérente " + lieu.Lieu.CellId + "/" + lieu.Lieu.Tick + " " + plan.Plan.CellId + "/" + plan.Plan.Tick);
            if (foule.TickApplique != lieu.Lieu.Tick) throw Faux("tick appliqué " + foule.TickApplique + " au lieu de " + lieu.Lieu.Tick);
            var proj = PassantsDuBourg.Projeter(lieu); if (!proj.Presente) throw Faux(proj.Absence);
            Balance(foule, proj, plan); foule.Tenir = true; var ids = Identifiants(foule.Racine); long pose = foule.NombrePose, projete = foule.NombreProjete;
            foule.Presenter(lieu, plan);
            if (foule.Cause != null || !Memes(ids, foule.Racine) || foule.NombrePose != pose) throw Faux("relecture du même tick : " + foule.Cause);
            foule.Presenter(LectureLieu.De(Copier(lieu.Lieu, lieu.Lieu.Tick + 5, false)), LecturePlan.De(Copier(plan.Plan, plan.Plan.Tick + 9)));
            if (foule.Cause == null || foule.Cause.IndexOf("discordante", StringComparison.Ordinal) < 0 || !Memes(ids, foule.Racine) || foule.NombrePose != pose || foule.NombreProjete != projete || foule.TickApplique != lieu.Lieu.Tick) throw Faux("discordance acceptée : " + foule.Cause);
            var avant = Decrire(foule.Racine); Transform garde = null;
            if (garder) { garde = new GameObject("Anciens gardés").transform; var src = new List<Transform>(); for (int i = 0; i < foule.Racine.childCount; i++) src.Add(foule.Racine.GetChild(i)); foreach (var e in src) { var clone = Object.Instantiate(e.gameObject, e.position + e.right * .6f, e.rotation, garde); clone.name = "ancien " + e.name; e.SetParent(garde, true); } }
            long tick1 = lieu.Lieu.Tick + 1; foule.Presenter(LectureLieu.De(Copier(lieu.Lieu, tick1, true)), LecturePlan.De(Copier(plan.Plan, tick1)));
            yield return null;
            bool vide = foule.Cause == null && foule.NombrePose == 0 && foule.NombreProjete == 0 && foule.Racine && foule.Racine.childCount == 0 && foule.TickApplique == tick1 && foule.CelluleAppliquee == cell && Partis(ids);
            if (!vide)
            {
                if (!garder) throw Faux("bourg vide non appliqué : pose " + foule.NombrePose + ", " + foule.Cause);
                var gens = Fenetre(garde); Cadrer(ville, camera, gens); for (int i = 0; i < 4; i++) yield return null;
                Ecrire(rapport, cell, lieu.Lieu.Tick, plan.Plan.Tick, foule, avant, Decrire(foule.Racine), Trajets(avant), Visibles(camera, garde), Decrire(garde));
                CitadelPlayCheck.Capture(camera, png, 1600, 900); throw Faux("anciens encore présents : " + garde.childCount);
            }
            long tick2 = lieu.Lieu.Tick + 2; foule.Presenter(LectureLieu.De(Copier(lieu.Lieu, tick2, false)), LecturePlan.De(Copier(plan.Plan, tick2)));
            yield return null;
            if (foule.Cause != null || foule.TickApplique != tick2 || foule.NombrePose < 3) throw Faux("foule non rétablie : " + foule.Cause);
            Balance(foule, proj, plan); var fenetre = Fenetre(foule.Racine); Cadrer(ville, camera, fenetre);
            var p0 = fenetre.Select(g => g.transform.position).ToArray(); var f0 = fenetre.Select(Phase).ToArray(); float t0 = Time.unscaledTime;
            while (Time.unscaledTime - t0 < .35f) yield return null;
            int bouge = 0, change = 0; for (int i = 0; i < fenetre.Count; i++) { if ((fenetre[i].transform.position - p0[i]).sqrMagnitude > .0025f) bouge++; if (Mathf.Abs(Phase(fenetre[i]) - f0[i]) > .01f) change++; }
            int visibles = Visibles(camera, foule.Racine);
            if (bouge < 3 || change < 3 || visibles < 3 || !Entiers(camera, fenetre)) throw Faux("marche invisible : bougés " + bouge + ", phases " + change + ", visibles " + visibles);
            Ecrire(rapport, cell, lieu.Lieu.Tick, plan.Plan.Tick, foule, avant, Decrire(foule.Racine), Trajets(Decrire(foule.Racine)), visibles, Array.Empty<string>());
            Debug.Log("PASSANTS " + foule.NombrePose + " posés, " + visibles + " visibles, tick " + foule.TickApplique);
            for (int i = 0; i < 4; i++) yield return null;
        }
        static void Balance(PassantsDeLaVille foule, PassantsDuBourg proj, LecturePlan plan)
        {
            var noms = new HashSet<string>();
            foreach (var metier in proj.ParMetier.Keys.OrderBy(k => k, StringComparer.Ordinal))
            {
                long n = proj.ParMetier[metier]; if (n <= 0) continue;
                var acces = TrajetsDesMetiers.Calculer(plan, metier).Trajets.Where(t => t.Points != null && t.Points.Count > 1).ToList(); long attendu = acces.Count == 0 ? 0 : n;
                if (!foule.PosesParMetier.TryGetValue(metier, out long vu) || vu != attendu) throw Faux("métier " + metier + " : " + vu + " au lieu de " + attendu);
                if (acces.Count == 0 && !foule.AbsencesDeTrajet.Any(a => a.StartsWith(metier + " :", StringComparison.Ordinal))) throw Faux("absence non déclarée : " + metier);
                for (int i = 0; i < acces.Count && attendu > 0; i++) for (int k = i; k < n; k += acces.Count) noms.Add(metier + "|" + acces[i].Destination + "|" + k);
            }
            if (foule.NombreProjete != proj.Nombre || foule.NombrePose != noms.Count || !foule.Racine || foule.Racine.childCount != noms.Count) throw Faux("bilan " + foule.NombreProjete + "/" + foule.NombrePose);
            var vus = new HashSet<string>(); for (int i = 0; i < foule.Racine.childCount; i++) vus.Add(foule.Racine.GetChild(i).name);
            if (!vus.SetEquals(noms) || noms.Count < 3) throw Faux(noms.Count < 3 ? "moins de trois passants (" + noms.Count + ")" : "répartition différente");
        }

        static Lieu Copier(Lieu l, long tick, bool vide)
        { var lieux = l.Lieux?.Select(p => !vide || p.Rang != 0 ? p : new LieuPlace(p.Rang, p.Position, p.Maitre, p.Flux, p.AbsenceDesFlux, 0L, null)).ToList(); return new Lieu(l.CellId, tick, l.Annee, l.JourDeLAnnee, l.Population, new Dictionary<string, double>(l.Stocks), l.HungerTicks, l.FoodDeficitKg, l.EtatFoyers, l.Foyers == null ? null : l.Foyers.ToDictionary(kv => kv.Key, kv => kv.Value), l.Logement, lieux, l.AbsenceDesLieux); }
        static PlanLu Copier(PlanLu p, long tick) => new PlanLu(p.CellId, tick, p.Rues.ToList(), p.Parcelles.ToList(), p.Batiments.ToList(), p.Base, p.ChantiersDuJour?.ToList(), p.AbsenceDesChantiersDuJour);
        static int[] Identifiants(Transform racine) { var ids = new int[racine.childCount + 1]; ids[0] = racine.GetInstanceID(); for (int i = 0; i < racine.childCount; i++) ids[i + 1] = racine.GetChild(i).GetInstanceID(); return ids; }
        static bool Memes(int[] ids, Transform racine) { var b = Identifiants(racine); if (ids.Length != b.Length) return false; for (int i = 0; i < ids.Length; i++) if (ids[i] != b[i]) return false; return true; }
        static bool Partis(int[] ids) { foreach (var id in ids) if (EditorUtility.InstanceIDToObject(id)) return false; return true; }
        static List<string> Decrire(Transform racine) { var l = new List<string>(); if (!racine) return l; for (int i = 0; i < racine.childCount; i++) { var t = racine.GetChild(i); l.Add(t.name + "#" + t.GetInstanceID().ToString(CultureInfo.InvariantCulture)); } return l; }
        static IEnumerable<string> Trajets(IEnumerable<string> noms) => noms.Select(n => { var p = n.Split('|'); return p.Length > 1 ? p[1].Split('#')[0] : n; }).Distinct().OrderBy(s => s, StringComparer.Ordinal);

        static List<Renderer> Fenetre(Transform racine)
        {
            var par = new Dictionary<string, List<Renderer>>();
            for (int i = 0; i < racine.childCount; i++) { var t = racine.GetChild(i); var r = t.GetComponent<Renderer>(); if (!r) continue; var p = t.name.Split('|'); string cle = p.Length > 1 ? p[1] : t.name; if (!par.TryGetValue(cle, out var liste)) par[cle] = liste = new List<Renderer>(); liste.Add(r); }
            var meilleur = par.Values.OrderByDescending(l => l.Count).FirstOrDefault() ?? throw Faux("aucun passant"); if (meilleur.Count < 3) throw Faux("aucune rue avec trois passants");
            var axe = meilleur[meilleur.Count - 1].transform.position - meilleur[0].transform.position; axe.y = 0f; var ord = meilleur.OrderBy(r => Vector3.Dot(r.transform.position, axe)).ToList(); int n = Mathf.Min(5, ord.Count); return ord.GetRange((ord.Count - n) / 2, n);
        }
        static void Cadrer(DesertCityCamera ville, Camera camera, List<Renderer> gens)
        {
            camera.aspect = 1600f / 900f; Vector3 centre = Vector3.zero; foreach (var g in gens) centre += g.transform.position; centre /= gens.Count;
            Vector3 dir = gens[gens.Count - 1].transform.position - gens[0].transform.position; dir.y = 0f; if (dir.sqrMagnitude < .25f) dir = Vector3.forward; dir.Normalize();
            float cap = Mathf.Atan2(dir.x, dir.z) * Mathf.Rad2Deg + 8f; bool ok = false; for (float dist = 10f; dist <= 70f && !ok; dist += 5f) { ville.Poser(centre, cap, 18f, dist); ok = Entiers(camera, gens); }
            if (!ok) throw Faux("civils hors champ");
        }
        static bool Entiers(Camera c, List<Renderer> gens)
        { foreach (var r in gens) { var b = r.bounds; var e = b.extents; var o = b.center; for (int i = 0; i < 8; i++) { var p = o + Vector3.Scale(e, new Vector3((i & 1) * 2 - 1, ((i >> 1) & 1) * 2 - 1, ((i >> 2) & 1) * 2 - 1)); var v = c.WorldToViewportPoint(p); if (v.z <= 0f || v.x < .03f || v.x > .97f || v.y < .03f || v.y > .97f) return false; } } return true; }
        static int Visibles(Camera c, Transform racine) { int n = 0; for (int i = 0; i < racine.childCount; i++) { var r = racine.GetChild(i).GetComponent<Renderer>(); if (r && Entiers(c, new List<Renderer> { r })) n++; } return n; }
        static float Phase(Renderer r) { var b = new MaterialPropertyBlock(); r.GetPropertyBlock(b); return b.GetFloat("_Phase"); }

        static void Ecrire(string chemin, long cell, long tickLieu, long tickPlan, PassantsDeLaVille foule, IEnumerable<string> avant, IEnumerable<string> apres, IEnumerable<string> trajets, int visibles, IEnumerable<string> anciens)
        { string J(IEnumerable<string> xs) => "[" + string.Join(",", xs.Select(Q)) + "]"; string N(long v) => v.ToString(CultureInfo.InvariantCulture); var mets = string.Join(",", foule.PosesParMetier.OrderBy(kv => kv.Key, StringComparer.Ordinal).Select(kv => Q(kv.Key) + ":" + N(kv.Value))); File.WriteAllText(chemin, "{\"cellule\":" + N(cell) + ",\"tick_lieu\":" + N(tickLieu) + ",\"tick_plan\":" + N(tickPlan) + ",\"projete\":" + N(foule.NombreProjete) + ",\"pose\":" + N(foule.NombrePose) + ",\"par_metier\":{" + mets + "},\"absences\":" + J(foule.AbsencesDeTrajet) + ",\"trajets\":" + J(trajets) + ",\"avant\":" + J(avant) + ",\"apres\":" + J(apres) + ",\"visibles\":" + N(visibles) + ",\"anciens\":" + J(anciens) + "}\n", new UTF8Encoding(false)); }
    }
}
