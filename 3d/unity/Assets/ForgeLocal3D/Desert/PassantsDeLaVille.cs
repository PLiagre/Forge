using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Forge.Pont;
using UnityEngine;

namespace ForgeLocal3D
{
    // Lot 788 : passants du bourg sur les trajets du métier. /lieu et /plan hors du fil, toutes les 0,25 s.
    public sealed class PassantsDeLaVille : MonoBehaviour
    {
        const float Vitesse = 1.2f, DureeMarche = 1.15f;
        static readonly Color[] Teintes = { new Color(.82f, .62f, .32f), new Color(.45f, .28f, .18f), new Color(.62f, .22f, .18f), new Color(.28f, .38f, .30f), new Color(.72f, .70f, .58f), new Color(.35f, .32f, .48f) };
        struct Marche { public Transform Corps; public Renderer Rendu; public MaterialPropertyBlock Bloc; public Vector3[] Pts; public float Longueur, Decalage, Phase0; public Color Teinte; }
        readonly List<Marche> marches = new();
        readonly Dictionary<string, long> poses = new();
        readonly List<string> absences = new();
        Mesh maillage; Material materiau; Terrain terrain; DesertRoadTool outil;
        long suivie = long.MinValue; double prochaine;
        Task<(long cell, LectureLieu lieu, LecturePlan plan)> vol;
        public long CelluleAppliquee { get; private set; } = -1; public long TickApplique { get; private set; } = -1;
        public long NombreProjete { get; private set; } = -1; public long NombrePose { get; private set; } = -1;
        public string Cause { get; private set; } public bool Tenir;
        public Transform Racine { get; private set; }
        public IReadOnlyDictionary<string, long> PosesParMetier => poses;
        public IReadOnlyList<string> AbsencesDeTrajet => absences;

        public void Brancher(Mesh mesh, Material mat, Terrain sol, DesertRoadTool routes)
        { maillage = mesh; materiau = mat; terrain = sol; outil = routes; }

        // Une autre cellule : la foule précédente disparaît tout de suite, les mesures redeviennent non calculées.
        public void Retirer()
        {
            vol = null; marches.Clear(); poses.Clear(); absences.Clear();
            if (Racine) DestroyImmediate(Racine.gameObject);
            Racine = null; CelluleAppliquee = TickApplique = NombreProjete = NombrePose = -1; Cause = null;
        }

        void Update()
        {
            long c = outil ? outil.Cellule : -1;
            if (c != suivie) { suivie = c; Retirer(); }
            if (vol != null)
            {
                if (!vol.IsCompleted) { Animer(); return; }
                var fini = vol; vol = null;
                if (!Tenir && fini.IsFaulted) Cause = "lecture hors fil : " + fini.Exception.GetBaseException().Message;
                else if (!Tenir && !fini.IsFaulted && fini.Result.cell == suivie) Presenter(fini.Result.lieu, fini.Result.plan);
            }
            Animer();
            if (Tenir || suivie < 0 || !outil || outil.Port < 1 || vol != null || Time.realtimeSinceStartupAsDouble < prochaine) return;
            prochaine = Time.realtimeSinceStartupAsDouble + .25; long cell = suivie; int port = outil.Port;
            vol = Task.Run(() => { using (var lieux = new ClientLieu(port, TimeSpan.FromSeconds(1))) using (var plans = new ClientPlan(port, TimeSpan.FromSeconds(1))) return (cell: cell, lieu: lieux.Lire(cell), plan: plans.Lire(cell)); });
        }

        // N'applique qu'une paire présente, même cellule ouverte, même tick. Sinon rien ne change, et la cause est nommée.
        public void Presenter(LectureLieu lieu, LecturePlan plan)
        {
            if (lieu == null || plan == null) { Cause = "lecture nulle"; return; }
            if (!lieu.Presente || !plan.Presente) { Cause = !lieu.Presente ? "lieu absent : " + lieu.Absence : "plan absent : " + plan.Absence; return; }
            long ouverte = outil ? outil.Cellule : -1;
            if (lieu.Lieu.CellId != plan.Plan.CellId || lieu.Lieu.Tick != plan.Plan.Tick)
            { Cause = "paire discordante : lieu " + lieu.Lieu.CellId + "/" + lieu.Lieu.Tick + ", plan " + plan.Plan.CellId + "/" + plan.Plan.Tick; return; }
            if (ouverte < 0 || lieu.Lieu.CellId != ouverte) { Cause = "paire d'une autre cellule : " + lieu.Lieu.CellId + ", ouverte " + ouverte; return; }
            if (TickApplique >= 0 && lieu.Lieu.Tick < TickApplique) { Cause = "paire ancienne : tick " + lieu.Lieu.Tick + " < " + TickApplique; return; }
            if (TickApplique == lieu.Lieu.Tick && CelluleAppliquee == ouverte) { Cause = null; return; }
            if (!maillage || !materiau || !terrain) { Cause = "maillage, matériau ou terrain absent"; return; }
            var proj = PassantsDuBourg.Projeter(lieu);
            if (!proj.Presente) { Cause = "effectifs : " + proj.Absence; return; }
            var choix = new List<(string Metier, TrajetDuMetier Trajet, int Indice, int Rang)>();
            int rang = 0;
            poses.Clear(); absences.Clear();
            foreach (var metier in proj.ParMetier.Keys.OrderBy(k => k, StringComparer.Ordinal))
            {
                long n = proj.ParMetier[metier]; if (n <= 0) continue;
                var calc = TrajetsDesMetiers.Calculer(plan, metier);
                var acces = calc.Trajets.Where(t => t.Points != null && t.Points.Count > 1).ToList();
                if (acces.Count == 0)
                {
                    poses[metier] = 0;
                    absences.Add(metier + " : " + (calc.Absence ?? (calc.Trajets.Count == 0 ? "aucun trajet" : string.Join(" ; ", calc.Trajets.Select(t => t.Absence ?? t.Destination)))));
                    continue;
                }
                poses[metier] = n;
                for (int i = 0; i < n; i++) choix.Add((metier, acces[i % acces.Count], i, rang++));
            }
            marches.Clear();
            if (Racine) DestroyImmediate(Racine.gameObject);
            var go = new GameObject("Passants"); go.transform.SetParent(transform, false); Racine = go.transform;
            foreach (var g in choix.GroupBy(x => x.Trajet))
            {
                var liste = g.ToList(); var pts = liste[0].Trajet.Points.Select(p => new Vector3((float)-p.X, 0f, (float)-p.Y)).ToArray();
                float L = 0f; for (int k = 0; k + 1 < pts.Length; k++) L += Vector3.Distance(pts[k], pts[k + 1]); if (L < 1e-3f) L = 1e-3f;
                for (int i = 0; i < liste.Count; i++)
                {
                    var x = liste[i]; float s = (i + .5f) / liste.Count * L; float decalage = (x.Rang & 1) == 1 ? 2f * L - s : s;
                    var corps = new GameObject(x.Metier + "|" + x.Trajet.Destination + "|" + x.Indice); corps.transform.SetParent(Racine, false);
                    corps.AddComponent<MeshFilter>().sharedMesh = maillage; var rendu = corps.AddComponent<MeshRenderer>(); rendu.sharedMaterial = materiau;
                    var bloc = new MaterialPropertyBlock();
                    marches.Add(new Marche { Corps = corps.transform, Rendu = rendu, Bloc = bloc, Pts = pts, Longueur = L, Decalage = decalage, Phase0 = Mathf.Repeat(x.Rang * .173f, 1f), Teinte = Teintes[x.Rang % Teintes.Length] });
                }
            }
            CelluleAppliquee = ouverte; TickApplique = lieu.Lieu.Tick; NombreProjete = proj.Nombre.Value; NombrePose = choix.Count; Cause = null;
        }

        void Animer()
        {
            if (marches.Count == 0 || !terrain) return;
            float t = Time.unscaledTime, y0 = terrain.transform.position.y;
            for (int i = 0; i < marches.Count; i++)
            {
                var m = marches[i]; float boucle = m.Longueur * 2f, d = Mathf.Repeat(t * Vitesse + m.Decalage, boucle); bool retour = d >= m.Longueur;
                Vector3 pos = Marcher(m.Pts, retour ? boucle - d : d, out Vector3 dir); if (retour) dir = -dir; if (dir.sqrMagnitude < 1e-8f) dir = Vector3.forward;
                pos.y = terrain.SampleHeight(pos) + y0; m.Corps.SetPositionAndRotation(pos, Quaternion.LookRotation(dir, Vector3.up));
                m.Bloc.SetFloat("_Phase", Mathf.Repeat(t / DureeMarche + m.Phase0, 1f)); m.Bloc.SetColor("_Teinte", m.Teinte); m.Rendu.SetPropertyBlock(m.Bloc);
            }
        }

        static Vector3 Marcher(Vector3[] pts, float distance, out Vector3 dir)
        {
            dir = Vector3.forward; if (pts == null || pts.Length == 0) return Vector3.zero; if (pts.Length == 1) return pts[0];
            float reste = distance;
            for (int i = 0; i + 1 < pts.Length; i++) { Vector3 ecart = pts[i + 1] - pts[i]; float L = ecart.magnitude; if (L < 1e-5f) continue; if (reste <= L || i + 2 >= pts.Length) { dir = ecart / L; return pts[i] + dir * Mathf.Clamp(reste, 0f, L); } reste -= L; }
            return pts[pts.Length - 1];
        }
    }
}
