using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Unity.Collections;
using Unity.Entities;
using Unity.Rendering;
using Unity.Transforms;
using UnityEngine;

namespace Guerre
{
    // Mesure du jalon 1 dans le vrai joueur :
    //   Citadelle-Guerre.exe -guerre-mesure -guerre-sortie DOSSIER [-guerre-soldats N] [-guerre-sabotage]
    // Elle échoue si un soldat manque, si l'armée ne bouge pas, si les soldats
    // ne changent pas l'image, ou si un 95e centile dépasse 16,67 ms.
    // -guerre-sabotage retire un soldat après la levée : la mesure doit alors échouer.
    public sealed class Mesure : MonoBehaviour
    {
        [Serializable] public class Vue { public string nom; public int images; public double mediane_ms, p95_ms, p99_ms, fps_moyen; public float ecart_type_image; }
        [Serializable] public class Rapport
        {
            public string statut, gpu, cpu, date_utc;
            public int largeur, hauteur, soldats_demandes, soldats_presents;
            public string protocole = "Joueur Windows, cadence libre, vSync coupée. Quatre vues, 3 s de chauffe puis 6 s de mesure chacune, caméra en rotation lente. Les armées marchent pendant la mesure.";
            public Vue[] vues;
            public float deplacement_moyen_m, pixels_changes_par_les_soldats, pixels_changes_par_l_animation;
            public int[] triangles_par_soldat;
            public int soldats_au_contact, morts;
            public float secondes_avant_la_melee;
            public bool objectif_60, soldats_conformes, armee_en_mouvement, soldats_visibles, soldats_animes, melee_engagee;
            public string[] motifs;
        }

        static string sortie;
        static bool sabotage;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Demarrer()
        {
            var args = Environment.GetCommandLineArgs();
            if (!args.Contains("-guerre-mesure")) return;
            int i = Array.IndexOf(args, "-guerre-sortie");
            sortie = i >= 0 && i + 1 < args.Length ? args[i + 1] : Path.Combine(Application.persistentDataPath, "mesure");
            sabotage = args.Contains("-guerre-sabotage");
            var go = new GameObject("Mesure"); DontDestroyOnLoad(go); go.AddComponent<Mesure>();
        }

        IEnumerator Start()
        {
            Directory.CreateDirectory(sortie);
            QualitySettings.vSyncCount = 0; Application.targetFrameRate = -1;
            while (Bataille.Instance == null || !Bataille.Instance.Pret) yield return null;
            var b = Bataille.Instance; var em = b.Em;
            var cmd = FindFirstObjectByType<Commandement>();
            cmd.automatique = true; cmd.montrerAide = false;

            var soldats = em.CreateEntityQuery(typeof(Soldat), typeof(LocalTransform));
            if (sabotage)
            {
                using var tous = soldats.ToEntityArray(Allocator.Temp);
                em.DestroyEntity(tous[tous.Length / 2]);
            }
            var r = new Rapport
            {
                gpu = SystemInfo.graphicsDeviceName, cpu = SystemInfo.processorType, date_utc = DateTime.UtcNow.ToString("o"),
                largeur = Screen.width, hauteur = Screen.height, soldats_demandes = b.soldats,
            };
            var motifs = new List<string>();
            yield return null;

            // Un échantillon fixe de soldats, pour mesurer que l'armée marche vraiment ; les morts gardent leur place.
            Entity[] suivis;
            using (var tous = soldats.ToEntityArray(Allocator.Temp))
                suivis = Enumerable.Range(0, Mathf.Min(400, tous.Length)).Select(k => tous[k * (tous.Length / Mathf.Max(1, Mathf.Min(400, tous.Length)))]).ToArray();
            Vector3[] Echantillon()
            {
                em.CompleteAllTrackedJobs();
                return suivis.Select(e => (Vector3)em.GetComponentData<LocalTransform>(e).Position).ToArray();
            }
            var avant = Echantillon();

            // La mesure porte sur une vraie bataille : on accélère le temps jusqu'à ce que
            // les deux armées soient aux prises, avec plus de mille hommes au contact.
            int AuContact()
            {
                em.CompleteAllTrackedJobs();
                using var ss = soldats.ToComponentDataArray<Soldat>(Allocator.Temp);
                int n = 0; foreach (var x in ss) n += x.Contact;
                return n;
            }
            Vector3 Melee()
            {
                em.CompleteAllTrackedJobs();
                using var ss = soldats.ToComponentDataArray<Soldat>(Allocator.Temp);
                using var tt = soldats.ToComponentDataArray<LocalTransform>(Allocator.Temp);
                Vector3 somme = Vector3.zero; int n = 0;
                for (int k = 0; k < ss.Length; k++) if (ss[k].Contact != 0) { somme += (Vector3)tt[k].Position; n++; }
                return n == 0 ? Vector3.zero : somme / n;
            }
            Time.timeScale = 6;
            float debutAttente = Time.time, limite = Time.realtimeSinceStartup + 150f;
            while (AuContact() < 1000 && Time.realtimeSinceStartup < limite) { for (int k = 0; k < 10; k++) yield return null; }
            r.secondes_avant_la_melee = Time.time - debutAttente;
            Time.timeScale = 1;
            r.melee_engagee = AuContact() >= 1000;
            if (!r.melee_engagee) motifs.Add("les armées ne se sont pas engagées : pas de mêlée à mesurer");

            var centre = b.terrain.transform.position + b.terrain.terrainData.size * 0.5f;
            // Les vues suivent l'armée bleue là où elle se trouve, pas un point fixe de la carte.
            Vector3 Armee()
            {
                using var regs = em.CreateEntityQuery(typeof(Regiment)).ToComponentDataArray<Regiment>(Allocator.Temp);
                Vector2 s = Vector2.zero; int n = 0;
                foreach (var g in regs) if (g.Camp == 0) { s += new Vector2(g.Position.x, g.Position.y); n++; }
                return n == 0 ? centre : new Vector3(s.x / n, 0, s.y / n);
            }
            var vues = new (string nom, bool armee, Vector3 decalage, float plongee, float distance)[]
            {
                ("Vue générale", false, Vector3.zero, 48, 900),
                ("Front", true, new Vector3(20, 0, 0), 24, 160),
                ("Au milieu des rangs", true, new Vector3(0, 0, 12), 9, 45),
                ("Plongée", true, new Vector3(0, 0, -60), 72, 260),
                ("Mêlée", false, Vector3.zero, 28, 60),
            };
            var resultats = new List<Vue>();
            foreach (var v in vues)
            {
                cmd.foyer = (v.nom == "Mêlée" && r.melee_engagee ? Melee() : v.armee ? Armee() : centre) + v.decalage; cmd.plongee = v.plongee; cmd.distance = v.distance;
                if (v.nom == "Mêlée") r.soldats_au_contact = AuContact();
                float t0 = Time.realtimeSinceStartup;
                while (Time.realtimeSinceStartup - t0 < 3f) { cmd.cap += 4f * Time.unscaledDeltaTime; yield return null; }
                var dts = new List<double>();
                t0 = Time.realtimeSinceStartup;
                while (Time.realtimeSinceStartup - t0 < 6f)
                {
                    cmd.cap += 4f * Time.unscaledDeltaTime;
                    yield return null;
                    dts.Add(Time.unscaledDeltaTime * 1000.0);
                }
                dts.Sort();
                double P(double q) => dts[Mathf.Clamp((int)Math.Ceiling(q * dts.Count) - 1, 0, dts.Count - 1)];
                var res = new Vue { nom = v.nom, images = dts.Count, mediane_ms = P(0.5), p95_ms = P(0.95), p99_ms = P(0.99), fps_moyen = 1000.0 / dts.Average() };
                yield return new WaitForEndOfFrame();
                var img = ScreenCapture.CaptureScreenshotAsTexture();
                res.ecart_type_image = EcartType(img);
                File.WriteAllBytes(Path.Combine(sortie, Fichier(v.nom) + ".jpg"), img.EncodeToJPG(85));
                Destroy(img);
                resultats.Add(res);
            }
            r.vues = resultats.ToArray();
            var apres = Echantillon();
            r.deplacement_moyen_m = avant.Length == 0 ? 0 : avant.Zip(apres, (a, c) => Vector3.Distance(a, c)).Average();

            // Contre-épreuve de visibilité : la même image, soldats masqués, doit changer.
            cmd.foyer = Armee() + vues[1].decalage; cmd.plongee = vues[1].plongee; cmd.distance = vues[1].distance;
            Time.timeScale = 0;
            for (int k = 0; k < 5; k++) yield return null;
            yield return new WaitForEndOfFrame();
            var avec = ScreenCapture.CaptureScreenshotAsTexture();
            em.AddComponent<DisableRendering>(soldats);
            for (int k = 0; k < 5; k++) yield return null;
            yield return new WaitForEndOfFrame();
            var sans = ScreenCapture.CaptureScreenshotAsTexture();
            em.RemoveComponent<DisableRendering>(soldats);
            Time.timeScale = 1;
            r.pixels_changes_par_les_soldats = Difference(avec, sans);
            File.WriteAllBytes(Path.Combine(sortie, "controle_sans_soldats.jpg"), sans.EncodeToJPG(85));
            Destroy(avec); Destroy(sans);

            // Preuve de l'animation : la simulation figée, mêmes positions, deux phases de
            // marche différentes. Si le shader ne rejoue pas l'animation cuite, l'image ne change pas.
            cmd.foyer = Armee() + vues[2].decalage; cmd.plongee = vues[2].plongee; cmd.distance = vues[2].distance;
            Pilotage(false);
            var animes = em.CreateEntityQuery(typeof(AnimEtat), typeof(AnimCombat), typeof(Soldat));
            void Phase(float phase)
            {
                em.CompleteAllTrackedJobs();
                var etats = animes.ToComponentDataArray<AnimEtat>(Allocator.Temp);
                for (int k = 0; k < etats.Length; k++) etats[k] = new AnimEtat { Value = new Unity.Mathematics.float4(phase, 1, 0, 0) };
                animes.CopyFromComponentDataArray(etats);
                etats.Dispose();
                // La garde de combat recouvrirait la marche : on la retire pour la durée de la preuve.
                var gardes = animes.ToComponentDataArray<AnimCombat>(Allocator.Temp);
                for (int k = 0; k < gardes.Length; k++) gardes[k] = new AnimCombat();
                animes.CopyFromComponentDataArray(gardes);
                gardes.Dispose();
            }
            Phase(0f);
            for (int k = 0; k < 5; k++) yield return null;
            yield return new WaitForEndOfFrame();
            var pas1 = ScreenCapture.CaptureScreenshotAsTexture();
            Phase(0.25f);
            for (int k = 0; k < 5; k++) yield return null;
            yield return new WaitForEndOfFrame();
            var pas2 = ScreenCapture.CaptureScreenshotAsTexture();
            Pilotage(true);
            r.pixels_changes_par_l_animation = Difference(pas1, pas2);
            File.WriteAllBytes(Path.Combine(sortie, "animation_phase_0.jpg"), pas1.EncodeToJPG(85));
            File.WriteAllBytes(Path.Combine(sortie, "animation_phase_25.jpg"), pas2.EncodeToJPG(85));
            Destroy(pas1); Destroy(pas2);
            r.triangles_par_soldat = b.maillages.Select(m => (int)(m.GetIndexCount(0) / 3)).ToArray();

            // Vivants et morts : un homme tombé reste un homme levé.
            r.morts = em.CreateEntityQuery(typeof(Mort)).CalculateEntityCount();
            r.soldats_presents = soldats.CalculateEntityCount() + r.morts;
            r.soldats_conformes = r.soldats_presents == r.soldats_demandes;
            if (!r.soldats_conformes) motifs.Add($"{r.soldats_presents} soldats présents pour {r.soldats_demandes} demandés");
            r.armee_en_mouvement = r.deplacement_moyen_m > 5f;
            if (!r.armee_en_mouvement) motifs.Add($"déplacement moyen de {r.deplacement_moyen_m:0.0} m seulement");
            r.soldats_visibles = r.pixels_changes_par_les_soldats > 0.02f;
            r.soldats_animes = r.pixels_changes_par_l_animation > 0.004f;
            if (!r.soldats_animes) motifs.Add($"l'animation ne change que {r.pixels_changes_par_l_animation:P2} de l'image : les soldats ne sont pas animés");
            if (!r.soldats_visibles) motifs.Add("les soldats ne changent pas l'image");
            if (r.vues.Any(v => v.ecart_type_image < 0.02f)) motifs.Add("une capture est uniforme");
            r.objectif_60 = r.vues.All(v => v.p95_ms < 1000.0 / 60.0);
            if (!r.objectif_60) motifs.Add("95e centile au-dessus de 16,67 ms : " + string.Join(", ", r.vues.Where(v => v.p95_ms >= 1000.0 / 60.0).Select(v => $"{v.nom} {v.p95_ms:0.00} ms")));
            r.motifs = motifs.ToArray();
            r.statut = motifs.Count == 0 ? "valide" : "echec";
            File.WriteAllText(Path.Combine(sortie, "mesure.json"), JsonUtility.ToJson(r, true));
            Debug.Log("[Mesure] " + r.statut + " " + string.Join(" | ", motifs));
            Application.Quit(motifs.Count == 0 ? 0 : 1);
        }

        static void Pilotage(bool actif)
        {
            var monde = World.DefaultGameObjectInjectionWorld;
            ref var etat = ref monde.Unmanaged.ResolveSystemStateRef(monde.GetExistingSystem<SystemePilotage>());
            etat.Enabled = actif;
        }

        static string Fichier(string nom) => new string(nom.ToLowerInvariant().Select(c => char.IsLetterOrDigit(c) ? c : '_').ToArray());

        static float EcartType(Texture2D t)
        {
            var px = t.GetPixels32(); double s = 0, s2 = 0; int n = 0;
            for (int i = 0; i < px.Length; i += 37) { double l = (0.2126 * px[i].r + 0.7152 * px[i].g + 0.0722 * px[i].b) / 255.0; s += l; s2 += l * l; n++; }
            double m = s / n; return (float)Math.Sqrt(Math.Max(0, s2 / n - m * m));
        }

        static float Difference(Texture2D a, Texture2D b)
        {
            var pa = a.GetPixels32(); var pb = b.GetPixels32(); int n = 0, d = 0;
            for (int i = 0; i < pa.Length && i < pb.Length; i += 7)
            {
                n++;
                if (Mathf.Abs(pa[i].r - pb[i].r) + Mathf.Abs(pa[i].g - pb[i].g) + Mathf.Abs(pa[i].b - pb[i].b) > 24) d++;
            }
            return n == 0 ? 0 : d / (float)n;
        }
    }
}
