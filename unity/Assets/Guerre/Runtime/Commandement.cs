using Unity.Entities;
using Unity.Mathematics;
using UnityEngine;
using UnityEngine.InputSystem;

namespace Guerre
{
    // Caméra de général et ordres au régiment. Les touches sont lues par leur
    // position physique : ZQSD sur un clavier AZERTY, WASD sur un QWERTY.
    [RequireComponent(typeof(Camera))]
    public sealed class Commandement : MonoBehaviour
    {
        public Vector3 foyer = new Vector3(1200, 0, 1200);
        public float cap = 30, plongee = 42, distance = 700;
        public bool automatique;      // la mesure pilote la caméra
        public bool montrerAide = true;

        Camera cam;
        Entity choisi = Entity.Null;
        float fpsLisse;
        const int CampJoueur = 0;

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
            if (!automatique) Piloter(dt);
            Placer();
        }

        void Piloter(float dt)
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
            if (k.aKey.isPressed) d -= droite;
            foyer += d * vitesse * dt;
            if (k.qKey.isPressed) cap -= 70 * dt;
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

            var b = Bataille.Instance;
            if (b == null || !b.Pret) return;
            if (m.leftButton.wasPressedThisFrame && Sol(m, out var p)) Choisir(b, b.RegimentProche(new float2(p.x, p.z), CampJoueur, 45));
            if (m.rightButton.wasPressedThisFrame && choisi != Entity.Null && Sol(m, out var cible)) Ordonner(b, cible);
        }

        bool Sol(Mouse m, out Vector3 point)
        {
            point = default;
            if (!Physics.Raycast(cam.ScreenPointToRay(m.position.ReadValue()), out var hit, 10000)) return false;
            point = hit.point; return true;
        }

        void Choisir(Bataille b, Entity e)
        {
            var em = b.Em;
            if (choisi != Entity.Null && em.Exists(choisi)) { var r = em.GetComponentData<Regiment>(choisi); r.Selection = 0; em.SetComponentData(choisi, r); }
            choisi = e;
            if (e != Entity.Null) { var r = em.GetComponentData<Regiment>(e); r.Selection = 1; em.SetComponentData(e, r); }
        }

        void Ordonner(Bataille b, Vector3 cible)
        {
            var em = b.Em;
            var r = em.GetComponentData<Regiment>(choisi);
            float2 c = new float2(cible.x, cible.z);
            float2 dir = c - r.Position;
            r.Cible = c;
            // Le régiment fait face à la direction de sa marche une fois arrivé.
            if (math.lengthsq(dir) > 1) r.FrontCible = math.normalize(dir);
            r.Ordonne = 1;
            em.SetComponentData(choisi, r);
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
            GUI.DrawTexture(new Rect(10, 10, 430, montrerAide ? 172 : 52), Texture2D.whiteTexture);
            GUI.color = Color.white;
            string etat = b == null || !b.Pret ? "levée des armées…" : $"{b.Leves:N0} hommes";
            GUI.Label(new Rect(20, 16, 420, 24), $"<b>Citadelle — Guerre</b>   {etat}   {fpsLisse:0} i/s{(Time.timeScale == 0 ? "   <b>PAUSE</b>" : "")}", style);
            if (!montrerAide) return;
            GUI.Label(new Rect(20, 44, 420, 140),
                "Clic gauche : choisir un régiment bleu\n" +
                "Clic droit : l'envoyer (il fait face à sa marche)\n" +
                "ZQSD : déplacer · Maj : plus vite · molette : zoom\n" +
                "A / E ou clic molette : tourner · F : vue générale\n" +
                "Espace : pause · H : masquer l'aide", style);
        }
    }
}
