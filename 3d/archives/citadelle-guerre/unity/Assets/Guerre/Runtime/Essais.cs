using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Unity.Collections;
using Unity.Entities;
using Unity.Mathematics;
using Unity.Transforms;
using UnityEngine;

namespace Guerre
{
    // Essai du jalon 2 dans le vrai joueur :
    //   Citadelle-Guerre.exe -guerre-essai-ordres -guerre-sortie DOSSIER [-guerre-sans-corps]
    // 1. Un régiment reçoit un ordre de position avec 16 files, puis 40, en pivotant d'un quart
    //    de tour : il doit y arriver, avec la largeur de front demandée.
    // 2. Un second régiment est envoyé à travers le premier : il ne doit pas le traverser,
    //    et aucun homme ne doit en recouvrir un autre.
    // Avec -guerre-sans-corps, les hommes ne se gênent plus : l'essai doit échouer.
    public sealed class Essais : MonoBehaviour
    {
        [Serializable] public class Formation_ { public int files; public float largeur_attendue, largeur_mesuree, a_sa_place, alignement_front, secondes; public bool arrive; public string[] trainards; }
        [Serializable] public class Obstacle { public float traversee_max, distance_min_m, secondes, ecart_moyen_tenant_m; }
        [Serializable] public class Rapport
        {
            public string statut, date_utc; public bool sans_corps;
            public Formation_[] formations; public Obstacle obstacle;
            public string[] motifs;
        }

        static string sortie; static bool sansCorps;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Demarrer()
        {
            var args = Environment.GetCommandLineArgs();
            if (!args.Contains("-guerre-essai-ordres")) return;
            int i = Array.IndexOf(args, "-guerre-sortie");
            sortie = i >= 0 && i + 1 < args.Length ? args[i + 1] : Path.Combine(Application.persistentDataPath, "essai-ordres");
            sansCorps = args.Contains("-guerre-sans-corps");
            var go = new GameObject("Essais"); DontDestroyOnLoad(go); go.AddComponent<Essais>();
        }

        Bataille b; EntityManager em; Commandement cmd; EntityQuery soldats;

        IEnumerator Start()
        {
            Directory.CreateDirectory(sortie);
            QualitySettings.vSyncCount = 0; Application.targetFrameRate = -1;
            while (Bataille.Instance == null || !Bataille.Instance.Pret) yield return null;
            b = Bataille.Instance; em = b.Em;
            cmd = FindFirstObjectByType<Commandement>(); cmd.automatique = true; cmd.montrerAide = false;
            soldats = em.CreateEntityQuery(typeof(Soldat), typeof(LocalTransform));
            // Tout le monde s'arrête : l'essai ne dépend pas du scénario de démonstration.
            b.Ordonner(b.Regiments().Select(x => (x.e, x.r.Position, x.r.Front, x.r.Files)).ToList());
            Time.timeScale = 4;

            var r0 = new Rapport { date_utc = DateTime.UtcNow.ToString("o"), sans_corps = sansCorps };
            var motifs = new List<string>();
            var bleus = b.Regiments(0).OrderBy(x => x.r.Index).ToArray();
            var A = bleus[4].e; var B = bleus[5].e;
            var rA = em.GetComponentData<Regiment>(A);
            float2 P = rA.Position + new float2(80, 0), F = new float2(0, 1);
            Viser(P, 50, 95);

            var formations = new List<Formation_>();
            foreach (int files in new[] { 16, 40 })
            {
                b.Ordonner(A, P, F, files);
                float t0 = Time.time;
                yield return Attendre(A, 150);
                var f = Mesurer(A, files, F);
                f.secondes = Time.time - t0;
                formations.Add(f);
                yield return Capture("formation_" + files);
                if (!f.arrive) motifs.Add($"{files} files : le régiment n'est pas arrivé en {f.secondes:0} s");
                if (Mathf.Abs(f.largeur_mesuree - f.largeur_attendue) > 0.1f * f.largeur_attendue + 1f)
                    motifs.Add($"{files} files : front de {f.largeur_mesuree:0.0} m pour {f.largeur_attendue:0.0} m attendus");
                if (f.a_sa_place < 0.95f) motifs.Add($"{files} files : {f.a_sa_place:P0} des hommes à leur place seulement");
                if (f.alignement_front < 0.99f) motifs.Add($"{files} files : le front n'est pas tourné vers la direction demandée");
            }
            r0.formations = formations.ToArray();

            // Le second régiment se place au sud, puis reçoit l'ordre de marcher à travers le premier.
            float2 S = P - F * 70, T = P + F * 70;
            b.Ordonner(B, S, F, 20);
            yield return Attendre(B, 200);
            b.Ordonner(B, T, F, 20);
            var ob = new Obstacle { distance_min_m = float.MaxValue };
            float debut = Time.time, prochaine = 0;
            bool capture = false;
            while (Time.time - debut < 70)
            {
                if (Time.time >= prochaine)
                {
                    prochaine = Time.time + 0.5f;
                    var (trav, dmin) = Croisement(A, B, F);
                    ob.traversee_max = Mathf.Max(ob.traversee_max, trav);
                    ob.distance_min_m = Mathf.Min(ob.distance_min_m, dmin);
                }
                if (!capture && Time.time - debut > 45) { capture = true; Viser((P + S) / 2 + F * 25, 40, 70); yield return Capture("obstacle"); }
                yield return null;
            }
            ob.secondes = Time.time - debut;
            ob.ecart_moyen_tenant_m = em.GetComponentData<Regiment>(A).Ecart;
            r0.obstacle = ob;
            if (ob.traversee_max > 0.05f) motifs.Add($"{ob.traversee_max:P0} du régiment en marche a traversé le régiment qui tient");
            if (ob.distance_min_m < 0.6f) motifs.Add($"deux hommes se sont approchés à {ob.distance_min_m:0.00} m : les corps se recouvrent");

            r0.motifs = motifs.ToArray();
            r0.statut = motifs.Count == 0 ? "valide" : "echec";
            File.WriteAllText(Path.Combine(sortie, "essai-ordres.json"), JsonUtility.ToJson(r0, true));
            Debug.Log("[Essais] " + r0.statut + " " + string.Join(" | ", motifs));
            Application.Quit(motifs.Count == 0 ? 0 : 1);
        }

        void Viser(float2 p, float plongee, float distance)
        {
            cmd.foyer = new Vector3(p.x, 0, p.y); cmd.plongee = plongee; cmd.distance = distance; cmd.cap = 20;
        }

        // Arrivé : l'ancre est sur la cible, le front est tourné et les hommes ont rejoint leur place.
        IEnumerator Attendre(Entity e, float limite)
        {
            // L'ordre doit d'abord avoir pris effet : l'écart des hommes se mesure à l'image suivante.
            float t0 = Time.time;
            while (Time.time - t0 < 1f) yield return null;
            while (Time.time - t0 < limite)
            {
                var r = em.GetComponentData<Regiment>(e);
                if (math.distance(r.Position, r.Cible) < 0.3f && math.dot(r.Front, r.FrontCible) > 0.999f && AuxPlaces(e) >= 0.98f) yield break;
                yield return null;
            }
        }

        // Part des hommes du régiment à moins d'un mètre de leur place : la moyenne cacherait les traînards.
        float AuxPlaces(Entity e)
        {
            var (s, t) = Hommes();
            int n = 0, ok = 0;
            for (int i = 0; i < s.Length; i++) if (s[i].Regiment == e) { n++; if (s[i].Ecart < 1f) ok++; }
            s.Dispose(); t.Dispose();
            return n == 0 ? 0 : ok / (float)n;
        }

        (NativeArray<Soldat> s, NativeArray<LocalTransform> t) Hommes()
        {
            em.CompleteAllTrackedJobs();
            return (soldats.ToComponentDataArray<Soldat>(Allocator.Temp), soldats.ToComponentDataArray<LocalTransform>(Allocator.Temp));
        }

        Formation_ Mesurer(Entity e, int files, float2 F)
        {
            var r = em.GetComponentData<Regiment>(e);
            var (s, t) = Hommes();
            float2 droite = new float2(r.Front.y, -r.Front.x);
            float mini = float.MaxValue, maxi = float.MinValue; int n = 0, places = 0;
            var trainards = new List<string>();
            for (int i = 0; i < s.Length; i++)
            {
                if (s[i].Regiment != e) continue;
                n++;
                float x = math.dot(t[i].Position.xz - r.Position, droite);
                mini = math.min(mini, x); maxi = math.max(maxi, x);
                if (s[i].Ecart < 1.5f) places++;
                else
                {
                    float2 ici = t[i].Position.xz - r.Position;
                    trainards.Add($"n°{s[i].Numero} à {s[i].Ecart:0.0} m, place {Formation.Place(r, s[i].Numero)}, se tient en ({math.dot(ici, droite):0.0}, {math.dot(ici, r.Front):0.0})");
                }
            }
            s.Dispose(); t.Dispose();
            return new Formation_
            {
                files = files, largeur_attendue = (files - 1) * r.Espacement, largeur_mesuree = maxi - mini,
                a_sa_place = n == 0 ? 0 : places / (float)n, alignement_front = math.dot(r.Front, F),
                trainards = trainards.ToArray(),
                arrive = math.distance(r.Position, r.Cible) < 0.3f && AuxPlaces(e) >= 0.98f,
            };
        }

        // Part des hommes de B passés au-delà du dernier rang de A, et plus petite distance entre un homme de A et un de B.
        (float, float) Croisement(Entity A, Entity B, float2 F)
        {
            var rA = em.GetComponentData<Regiment>(A);
            var (s, t) = Hommes();
            var hA = new List<float2>(); var hB = new List<float2>();
            for (int i = 0; i < s.Length; i++)
            {
                if (s[i].Regiment == A) hA.Add(t[i].Position.xz);
                else if (s[i].Regiment == B) hB.Add(t[i].Position.xz);
            }
            s.Dispose(); t.Dispose();
            float au_dela = rA.Profondeur / 2 + 1.5f;
            int passes = hB.Count(p => math.dot(p - rA.Position, F) > au_dela);
            float dmin = float.MaxValue;
            foreach (var a in hA) foreach (var c in hB) dmin = math.min(dmin, math.distancesq(a, c));
            return (hB.Count == 0 ? 0 : passes / (float)hB.Count, math.sqrt(dmin));
        }

        IEnumerator Capture(string nom)
        {
            float ts = Time.timeScale; Time.timeScale = 0;
            for (int k = 0; k < 4; k++) yield return null;
            yield return new WaitForEndOfFrame();
            var img = ScreenCapture.CaptureScreenshotAsTexture();
            File.WriteAllBytes(Path.Combine(sortie, nom + ".jpg"), img.EncodeToJPG(85));
            Destroy(img);
            Time.timeScale = ts;
        }
    }
}
