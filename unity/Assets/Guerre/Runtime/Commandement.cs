using System.Collections.Generic;
using System.Linq;
using Unity.Entities;
using Unity.Mathematics;
using UnityEngine;
using UnityEngine.InputSystem;

namespace Guerre
{
    // Caméra de général et ordres aux régiments. Les touches de déplacement sont
    // lues par leur position physique : ZQSD sur un clavier AZERTY, WASD sur un QWERTY.
    [RequireComponent(typeof(Camera))]
    public sealed class Commandement : MonoBehaviour
    {
        public Vector3 foyer = new Vector3(1200, 0, 1200);
        public float cap = 30, plongee = 42, distance = 700;
        public bool automatique;      // la mesure pilote la caméra
        public bool montrerAide = true;
        public Material trait;        // tracé des ordres sur le sol

        const int CampJoueur = 0;
        const float Intervalle = 4f;  // mètres entre deux régiments placés sur une même ligne
        const float TraceMin = 6f;    // en deçà, un clic droit glissé reste un simple clic

        Camera cam;
        readonly List<Entity> choisis = new List<Entity>();
        float fpsLisse;
        Vector2 debutBoite; bool boite;
        Vector3 debutLigne; bool ligneCommencee, ligneTracee;
        readonly List<LineRenderer> traces = new List<LineRenderer>();

        public IReadOnlyList<Entity> Choisis => choisis;

        void Start()
        {
            cam = GetComponent<Camera>();
            if (Bataille.Instance && Bataille.Instance.terrain)
            {
                var t = Bataille.Instance.terrain;
                foyer = t.transform.position + t.terrainData.size * 0.5f;
            }
            Placer();
        }

        void Update()
        {
            float dt = Time.unscaledDeltaTime;
            fpsLisse = Mathf.Lerp(fpsLisse, 1f / Mathf.Max(dt, 1e-4f), 0.05f);
            var dessins = new List<(float2 c, float2 f, float w, float d)>();
            if (!automatique) { Camera_(dt); Ordres(dessins); }
            Placer();
            Dessiner(dessins);
        }

        void Camera_(float dt)
        {
            var k = Keyboard.current; var m = Mouse.current;
            if (k == null || m == null) return;
            var avant = Quaternion.Euler(0, cap, 0) * Vector3.forward;
            var droite = Quaternion.Euler(0, cap, 0) * Vector3.right;
            float vitesse = distance * (k.leftShiftKey.isPressed ? 1.6f : 0.8f);
            Vector3 d = Vector3.zero;
            if (k.wKey.isPressed) d += avant;
            if (k.sKey.isPressed) d -= avant;
            if (k.dKey.isPressed) d += droite;
            if (k.aKey.isPressed && !k.ctrlKey.isPressed) d -= droite;
            foyer += d * vitesse * dt;
            if (k.qKey.isPressed && !k.ctrlKey.isPressed) cap -= 70 * dt;
            if (k.eKey.isPressed) cap += 70 * dt;
            if (m.middleButton.isPressed)
            {
                var md = m.delta.ReadValue();
                cap += md.x * 0.25f;
                plongee = Mathf.Clamp(plongee - md.y * 0.2f, 5, 85);
            }
            float roue = m.scroll.ReadValue().y;
            if (Mathf.Abs(roue) > 0.01f) distance = Mathf.Clamp(distance * (roue > 0 ? 0.88f : 1.14f), 12, 2200);
            if (k.spaceKey.wasPressedThisFrame) Time.timeScale = Time.timeScale > 0 ? 0 : 1;
            if (k.fKey.wasPressedThisFrame) { var t = Bataille.Instance.terrain; foyer = t.transform.position + t.terrainData.size * 0.5f; distance = 700; plongee = 42; }
            if (k.hKey.wasPressedThisFrame) montrerAide = !montrerAide;
        }

        void Ordres(List<(float2, float2, float, float)> dessins)
        {
            var k = Keyboard.current; var m = Mouse.current;
            var b = Bataille.Instance;
            if (k == null || m == null || b == null || !b.Pret) return;
            choisis.RemoveAll(e => !b.Em.Exists(e));
            bool ajout = k.shiftKey.isPressed;

            // Sélection : clic sur un régiment, ou boîte tracée au clic gauche.
            if (m.leftButton.wasPressedThisFrame) { debutBoite = m.position.ReadValue(); boite = true; }
            if (boite && m.leftButton.wasReleasedThisFrame)
            {
                boite = false;
                var fin = m.position.ReadValue();
                if (!ajout) Vider(b);
                if ((fin - debutBoite).magnitude > 6)
                {
                    var rect = Rect.MinMaxRect(Mathf.Min(debutBoite.x, fin.x), Mathf.Min(debutBoite.y, fin.y), Mathf.Max(debutBoite.x, fin.x), Mathf.Max(debutBoite.y, fin.y));
                    foreach (var (e, r) in b.Regiments(CampJoueur))
                    {
                        var sp = cam.WorldToScreenPoint(Monde(r.Position));
                        if (sp.z > 0 && rect.Contains(sp)) Ajouter(b, e);
                    }
                }
                else if (Sol(m, out var p))
                {
                    var e = b.RegimentSous(new float2(p.x, p.z), CampJoueur, 20);
                    if (e != Entity.Null)
                    {
                        if (ajout && choisis.Contains(e)) { b.Choisir(e, false); choisis.Remove(e); }
                        else Ajouter(b, e);
                    }
                }
            }
            var toucheA = k.FindKeyOnCurrentKeyboardLayout("a");
            if (k.ctrlKey.isPressed && toucheA != null && toucheA.wasPressedThisFrame)
            {
                Vider(b);
                foreach (var (e, _) in b.Regiments(CampJoueur)) Ajouter(b, e);
            }
            if (k.backspaceKey.wasPressedThisFrame)
                b.Ordonner(choisis.Select(e => { var r = b.Em.GetComponentData<Regiment>(e); return (e, r.Position, r.Front, r.Files); }).ToList());

            // Ordres : clic droit pour aller, clic droit glissé pour tracer la ligne de bataille.
            if (choisis.Count > 0 && m.rightButton.wasPressedThisFrame && Sol(m, out var a))
            {
                // Clic droit sur un régiment ennemi : l'attaquer. Ailleurs : y aller.
                var ennemi = b.RegimentSous(new float2(a.x, a.z), 1 - CampJoueur, 0);
                if (ennemi != Entity.Null) b.Attaquer(choisis, ennemi);
                else { debutLigne = a; ligneCommencee = true; ligneTracee = false; }
            }
            if (ligneCommencee && Sol(m, out var courant))
            {
                var A = new float2(debutLigne.x, debutLigne.z); var B = new float2(courant.x, courant.z);
                if (math.distance(A, B) >= TraceMin) ligneTracee = true;
                var plan = ligneTracee ? Ligne(b, A, B) : Groupe(b, A);
                if (m.rightButton.wasReleasedThisFrame)
                {
                    b.Ordonner(plan);
                    ligneCommencee = false;
                }
                else foreach (var (e, cible, front, files) in plan) dessins.Add(Emprise(b, e, cible, front, files));
            }
            if (!m.rightButton.isPressed) ligneCommencee = false;

            // Les destinations des régiments choisis qui ne sont pas encore arrivés.
            if (!ligneCommencee)
                foreach (var e in choisis)
                {
                    var r = b.Em.GetComponentData<Regiment>(e);
                    if (math.distance(r.Position, r.Cible) > 1f) dessins.Add(Emprise(b, e, r.Cible, r.FrontCible, r.Files));
                }
        }

        // Une ligne tracée de A à B : les régiments s'y rangent dans l'ordre où ils sont
        // déjà, sa longueur fixe leur front, et ils font face au loin, comme la caméra.
        List<(Entity, float2, float2, int)> Ligne(Bataille b, float2 A, float2 B)
        {
            float2 dir = math.normalize(B - A); float L = math.distance(A, B);
            float2 front = new float2(dir.y, -dir.x);
            var vue = new float2(transform.forward.x, transform.forward.z);
            if (math.dot(front, vue) < 0) front = -front;
            var regs = choisis.Select(e => (e, r: b.Em.GetComponentData<Regiment>(e))).OrderBy(x => math.dot(x.r.Position - A, dir)).ToList();
            int n = regs.Count;
            float largeur = math.max((L - Intervalle * (n - 1)) / n, 2f);
            var plan = new List<(Entity, float2, float2, int)>();
            float x = 0;
            foreach (var (e, r) in regs)
            {
                int files = math.clamp((int)math.round(largeur / r.Espacement) + 1, 4, r.Effectif);
                float w = (files - 1) * r.Espacement;
                plan.Add((e, A + dir * (x + w / 2), front, files));
                x += w + Intervalle;
            }
            return plan;
        }

        // Un simple clic : le groupe garde sa disposition, tournée vers sa nouvelle marche.
        List<(Entity, float2, float2, int)> Groupe(Bataille b, float2 C)
        {
            var regs = choisis.Select(e => b.Em.GetComponentData<Regiment>(e)).ToList();
            float2 G = float2.zero, F = float2.zero;
            foreach (var r in regs) { G += r.Position; F += r.Front; }
            G /= regs.Count;
            float2 vers = C - G;
            float2 front = math.lengthsq(vers) > 4f ? math.normalize(vers) : math.normalizesafe(F, new float2(1, 0));
            float angle = math.atan2(front.y, front.x) - math.atan2(F.y, F.x);
            if (math.lengthsq(F) < 1e-4f) angle = 0;
            float cs = math.cos(angle), sn = math.sin(angle);
            var plan = new List<(Entity, float2, float2, int)>();
            for (int i = 0; i < regs.Count; i++)
            {
                float2 o = regs[i].Position - G;
                plan.Add((choisis[i], C + new float2(o.x * cs - o.y * sn, o.x * sn + o.y * cs), front, regs[i].Files));
            }
            return plan;
        }

        (float2, float2, float, float) Emprise(Bataille b, Entity e, float2 cible, float2 front, int files)
        {
            var r = b.Em.GetComponentData<Regiment>(e);
            r.Files = math.clamp(files, 1, r.Effectif);
            return (cible, math.normalizesafe(front, new float2(1, 0)), r.Largeur, r.Profondeur);
        }

        void Ajouter(Bataille b, Entity e) { if (!choisis.Contains(e)) { choisis.Add(e); b.Choisir(e, true); } }
        void Vider(Bataille b) { foreach (var e in choisis) if (b.Em.Exists(e)) b.Choisir(e, false); choisis.Clear(); }

        Vector3 Monde(float2 p)
        {
            var t = Bataille.Instance.terrain;
            var v = new Vector3(p.x, 0, p.y);
            v.y = t.SampleHeight(v) + t.transform.position.y;
            return v;
        }

        // Le contour de chaque formation future, posé sur le relief, avec une pointe vers l'ennemi.
        void Dessiner(List<(float2 c, float2 f, float w, float d)> dessins)
        {
            while (traces.Count < dessins.Count)
            {
                var go = new GameObject("Tracé d'ordre");
                go.transform.SetParent(transform, false);
                var lr = go.AddComponent<LineRenderer>();
                lr.sharedMaterial = trait; lr.widthMultiplier = 0.35f; lr.useWorldSpace = true;
                lr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; lr.receiveShadows = false;
                traces.Add(lr);
            }
            for (int i = 0; i < traces.Count; i++)
            {
                traces[i].enabled = i < dessins.Count;
                if (i >= dessins.Count) continue;
                var (c, f, w, d) = dessins[i];
                float2 dr = new float2(f.y, -f.x);
                float hw = w / 2 + 0.8f, hd = d / 2 + 0.8f;
                float2 fl = c + f * hd - dr * hw, fr = c + f * hd + dr * hw, br = c - f * hd + dr * hw, bl = c - f * hd - dr * hw;
                float2 fm = c + f * hd;
                var pts = new List<Vector3>();
                void Segment(float2 p, float2 q)
                {
                    int n = Mathf.Max(1, Mathf.CeilToInt(math.distance(p, q) / 3f));
                    for (int s = 0; s < n; s++) { var v = Monde(math.lerp(p, q, s / (float)n)); v.y += 0.4f; pts.Add(v); }
                }
                Segment(fl, fm); Segment(fm, fm + f * 4); Segment(fm + f * 4, fm); Segment(fm, fr);
                Segment(fr, br); Segment(br, bl); Segment(bl, fl);
                var fin = Monde(fl); fin.y += 0.4f; pts.Add(fin);
                traces[i].positionCount = pts.Count;
                traces[i].SetPositions(pts.ToArray());
            }
        }

        bool Sol(Mouse m, out Vector3 point)
        {
            point = default;
            if (!Physics.Raycast(cam.ScreenPointToRay(m.position.ReadValue()), out var hit, 10000)) return false;
            point = hit.point; return true;
        }

        void Placer()
        {
            if (Bataille.Instance && Bataille.Instance.terrain)
                foyer.y = Bataille.Instance.terrain.SampleHeight(foyer) + Bataille.Instance.terrain.transform.position.y;
            var rot = Quaternion.Euler(plongee, cap, 0);
            var pos = foyer - rot * Vector3.forward * distance;
            if (Bataille.Instance && Bataille.Instance.terrain)
            {
                float sol = Bataille.Instance.terrain.SampleHeight(pos) + Bataille.Instance.terrain.transform.position.y;
                pos.y = Mathf.Max(pos.y, sol + 2.5f);
            }
            transform.SetPositionAndRotation(pos, Quaternion.LookRotation(foyer - pos));
        }

        void OnGUI()
        {
            var b = Bataille.Instance;
            var style = new GUIStyle(GUI.skin.label) { fontSize = 15, richText = true };
            GUI.color = new Color(0, 0, 0, 0.55f);
            GUI.DrawTexture(new Rect(10, 10, 700, montrerAide ? 254 : 52), Texture2D.whiteTexture);
            GUI.color = Color.white;
            string etat = b == null || !b.Pret ? "levée des armées…" : $"{b.Leves:N0} hommes";
            string pertes = $"   pertes : {SystemePertes.Pertes[0]} bleus, {SystemePertes.Pertes[1]} rouges";
            string choix = choisis.Count > 0 ? $"   {choisis.Count} régiment{(choisis.Count > 1 ? "s" : "")} choisi{(choisis.Count > 1 ? "s" : "")}" : "";
            GUI.Label(new Rect(20, 16, 690, 24), $"<b>Citadelle — Guerre</b>   {etat}   {fpsLisse:0} i/s{pertes}{choix}{(Time.timeScale == 0 ? "   <b>PAUSE</b>" : "")}", style);
            if (montrerAide)
                GUI.Label(new Rect(20, 44, 690, 210),
                    "Clic gauche : choisir un régiment bleu · glisser : boîte\n" +
                    "Maj + clic : ajouter ou retirer · Ctrl + A : toute l'armée\n" +
                    "Clic droit : y aller (le groupe garde sa disposition)\n" +
                    "Clic droit sur un régiment rouge : l'attaquer\n" +
                    "Clic droit glissé : tracer la ligne — sa longueur fixe le front\n" +
                    "Retour arrière : halte\n" +
                    "ZQSD : déplacer · Maj : plus vite · molette : zoom\n" +
                    "A / E ou clic molette : tourner · F : vue générale\n" +
                    "Espace : pause · H : masquer l'aide", style);
            if (boite && Mouse.current != null)
            {
                var p = Mouse.current.position.ReadValue();
                if ((p - debutBoite).magnitude > 6)
                {
                    var r = Rect.MinMaxRect(Mathf.Min(debutBoite.x, p.x), Screen.height - Mathf.Max(debutBoite.y, p.y), Mathf.Max(debutBoite.x, p.x), Screen.height - Mathf.Min(debutBoite.y, p.y));
                    GUI.color = new Color(1f, 0.9f, 0.5f, 0.18f); GUI.DrawTexture(r, Texture2D.whiteTexture);
                    GUI.color = Color.white;
                }
            }
        }
    }
}
