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
    // Essai du jalon 8 dans le vrai joueur :
    //   Citadelle-Guerre.exe -guerre-essai-carte -guerre-sortie DOSSIER [-guerre-sans-pont | -guerre-sans-murs]
    // Trois régiments de 250 piquiers reçoivent chacun un ordre de marche, comme le joueur le donnerait :
    //   - « vallée » : 750 m le long du fond de la vallée ;
    //   - « pont » : du pied de l'éperon à la place de la cathédrale, par le seul pont sur le ravin, la
    //     porte de 4,5 m et la grand-rue ;
    //   - « rues » : de la place de la cathédrale à la place de l'est, par la grand-rue et la rue traversière.
    // Chaque parcours est franchissable si 95 % des hommes finissent à leur place à l'arrivée, sans
    // qu'aucun homme soit jamais passé dans l'emprise d'un mur, d'une tour ou d'une maison, ni tombé
    // dans le ravin.
    // Avec -guerre-sans-pont, le tablier n'existe plus : le parcours du pont doit échouer. Avec
    // -guerre-sans-murs, les murs et les maisons n'arrêtent plus personne : des hommes doivent y passer.
    public sealed class EssaisCarte : MonoBehaviour
    {
        [Serializable] public class Parcours
        {
            public string nom; public bool route, arrive;
            public int files_en_colonne; public float longueur_route_m, secondes, a_sa_place, ecart_a_l_arrivee_m;
            public int dans_un_mur_max, tombes_dans_le_ravin;
            public bool franchissable;
        }
        [Serializable] public class Rapport
        {
            public string statut, date_utc; public bool sans_pont, sans_murs;
            public int emprises_bloquees; public Parcours[] parcours; public string[] motifs;
        }

        static string sortie; static bool sansPont, sansMurs;
        const float Limite = 1200f, Reste = 30f, APlace = 2.5f, PartMin = 0.95f;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Demarrer()
        {
            var args = Environment.GetCommandLineArgs();
            if (!args.Contains("-guerre-essai-carte")) return;
            int i = Array.IndexOf(args, "-guerre-sortie");
            sortie = i >= 0 && i + 1 < args.Length ? args[i + 1] : Path.Combine(Application.persistentDataPath, "essai-carte");
            sansPont = args.Contains("-guerre-sans-pont");
            sansMurs = args.Contains("-guerre-sans-murs");
            var go = new GameObject("Essais de la carte"); DontDestroyOnLoad(go); go.AddComponent<EssaisCarte>();
        }

        IEnumerator Start()
        {
            Directory.CreateDirectory(sortie);
            QualitySettings.vSyncCount = 0; Application.targetFrameRate = -1;
            while (Bataille.Instance == null || !Bataille.Instance.Pret) yield return null;
            var b = Bataille.Instance; var em = b.Em; var carte = b.carte;
            var cmd = FindFirstObjectByType<Commandement>(); cmd.automatique = true; cmd.montrerAide = false;
            b.Ordonner(b.Regiments().Select(x => (x.e, x.r.Position, x.r.Front, x.r.Files)).ToList());
            yield return null;
            var rapport = new Rapport { date_utc = DateTime.UtcNow.ToString("o"), sans_pont = sansPont, sans_murs = sansMurs, emprises_bloquees = carte != null ? carte.blocs.Count : 0 };
            var motifs = new List<string>();
            if (carte == null) { motifs.Add("la scène n'a pas de carte"); Finir(rapport, motifs); yield break; }

            // La vraie géométrie : les emprises de la carte, quoi que fasse la simulation (sans les murs, elle les ignore).
            var t = b.terrain.transform.position; int cote = Mathf.CeilToInt(b.terrain.terrainData.size.x);
            float2 origine = new float2(t.x, t.z);
            var murs = new byte[cote * cote];
            foreach (var bl in carte.blocs) Bataille.Tracer(murs, cote, origine, bl);
            bool DansUnMur(float2 p)
            {
                int2 c = (int2)math.floor(p - origine);
                return c.x >= 0 && c.y >= 0 && c.x < cote && c.y < cote && murs[c.y * cote + c.x] != 0;
            }
            float2 V(Vector2 v) => new float2(v.x, v.y);
            var citadelle = V(carte.Trouver("citadelle").p);

            // Les régiments qui ne marchent pas sont rangés au sud de la vallée, loin des routes.
            var bleus = b.Regiments(0).OrderBy(x => x.r.Index).Select(x => x.e).ToList();
            var marcheurs = bleus.Take(3).ToArray();
            var autres = b.Regiments().Select(x => x.e).Where(e => !marcheurs.Contains(e)).ToArray();
            for (int k = 0; k < autres.Length; k++)
            {
                float x = 330f + k * 1700f / Math.Max(1, autres.Length - 1);
                b.Deplacer(autres[k], new float2(x, 1200f + 90f * math.sin(x / 520f) - 250f), new float2(1, 0), 25);
            }
            foreach (var e in marcheurs) b.Armer(e, 0);

            var essais = new[]
            {
                (nom: "vallée", e: marcheurs[0], depart: carte.Trouver("vallee_depart"), arrivee: carte.Trouver("vallee_arrivee"), files: 25),
                (nom: "pont", e: marcheurs[1], depart: carte.Trouver("pied"), arrivee: carte.Trouver("place"), files: 25),
                (nom: "rues", e: marcheurs[2], depart: carte.Trouver("place"), arrivee: carte.Trouver("place_est"), files: 20),
            };
            foreach (var x in essais) b.Deplacer(x.e, V(x.depart.p), V(x.depart.front), x.files);
            for (int k = 0; k < 10; k++) yield return null;
            var res = essais.Select(x => new Parcours { nom = x.nom }).ToArray();
            for (int k = 0; k < essais.Length; k++)
            {
                b.Ordonner(essais[k].e, V(essais[k].arrivee.p), V(essais[k].arrivee.front), essais[k].files);
                var r = em.GetComponentData<Regiment>(essais[k].e);
                res[k].route = r.Chemin != 0;
                res[k].files_en_colonne = r.Chemin != 0 ? r.Files : 0;
                res[k].longueur_route_m = r.Chemin != 0 ? r.LongueurChemin : 0;
            }
            Grille(b, em, citadelle, essais.Select(x => x.e).ToArray(), carte);
            cmd.foyer = new Vector3(citadelle.x, 60, citadelle.y - 120); cmd.plongee = 40; cmd.distance = 160; cmd.cap = 0;
            Time.timeScale = 4;

            var soldats = em.CreateEntityQuery(typeof(Soldat), typeof(LocalTransform));
            var arrivee = new float[essais.Length];
            for (int k = 0; k < arrivee.Length; k++) arrivee[k] = -1;
            float debut = Time.time, prochaine = 0;
            bool capturePont = false, captureRue = false;
            while (Time.time - debut < Limite)
            {
                yield return null;
                if (Time.time < prochaine) continue;
                prochaine = Time.time + 0.5f;
                em.CompleteAllTrackedJobs();
                var dansMur = new int[essais.Length];
                float2 teteDuPont = float2.zero; int nPont = 0;
                using (var ss = soldats.ToComponentDataArray<Soldat>(Allocator.Temp))
                using (var tt = soldats.ToComponentDataArray<LocalTransform>(Allocator.Temp))
                    for (int i = 0; i < ss.Length; i++)
                    {
                        int k = Array.FindIndex(essais, x => x.e == ss[i].Regiment);
                        if (k < 0) continue;
                        float2 p = tt[i].Position.xz;
                        if (DansUnMur(p)) dansMur[k]++;
                        float rr = math.distance(p, citadelle);
                        if (rr > 109f && rr < 123f && tt[i].Position.y < 62f - 4f) res[k].tombes_dans_le_ravin++;
                        if (k == 1 && math.abs(rr - 116f) < 8f) { teteDuPont += p; nPont++; }
                    }
                bool tous = true;
                for (int k = 0; k < essais.Length; k++)
                {
                    res[k].dans_un_mur_max = Math.Max(res[k].dans_un_mur_max, dansMur[k]);
                    var r = em.GetComponentData<Regiment>(essais[k].e);
                    // Arrivé : la route est finie et l'ancre est au but ; on laisse aux hommes le temps de se placer.
                    if (arrivee[k] < 0 && r.Chemin == 0 && math.distance(r.Position, V(essais[k].arrivee.p)) < 1f) arrivee[k] = Time.time;
                    if (arrivee[k] < 0 || Time.time - arrivee[k] < Reste) tous = false;
                }
                // Une vue de la colonne sur le pont, et une dans la grand-rue.
                if (!capturePont && nPont > 20)
                {
                    capturePont = true;
                    var c = teteDuPont / nPont;
                    cmd.foyer = new Vector3(c.x, 60, c.y); cmd.plongee = 30; cmd.distance = 55; cmd.cap = 20;
                    yield return Capture("colonne_sur_le_pont");
                }
                if (capturePont && !captureRue)
                {
                    var r = em.GetComponentData<Regiment>(essais[1].e);
                    if (r.Chemin == 1 && math.distance(r.Position, citadelle) < 70f)
                    {
                        captureRue = true;
                        cmd.foyer = new Vector3(r.Position.x, 60, r.Position.y); cmd.plongee = 55; cmd.distance = 70; cmd.cap = 0;
                        yield return Capture("colonne_dans_la_grand_rue");
                    }
                }
                if (tous) break;
            }
            Time.timeScale = 1;

            // À l'arrivée : la part des hommes à leur place, comme au jalon 2.
            em.CompleteAllTrackedJobs();
            using (var ss = soldats.ToComponentDataArray<Soldat>(Allocator.Temp))
            using (var tt = soldats.ToComponentDataArray<LocalTransform>(Allocator.Temp))
                for (int k = 0; k < essais.Length; k++)
                {
                    var r = em.GetComponentData<Regiment>(essais[k].e);
                    int n = 0, bien = 0;
                    for (int i = 0; i < ss.Length; i++)
                    {
                        if (ss[i].Regiment != essais[k].e) continue;
                        n++;
                        float2 place = Formation.VersMonde(Formation.Place(r, ss[i].Numero) + ss[i].Decalage, r.Position, r.Front);
                        if (math.distance(place, tt[i].Position.xz) < APlace) bien++;
                    }
                    res[k].a_sa_place = n > 0 ? bien / (float)n : 0;
                    res[k].arrive = arrivee[k] >= 0;
                    res[k].secondes = arrivee[k] >= 0 ? arrivee[k] - debut : Time.time - debut;
                    res[k].ecart_a_l_arrivee_m = math.distance(r.Position, V(essais[k].arrivee.p));
                }
            var lieux = new[] { ("place", "arrivee_place"), ("place_est", "arrivee_place_est") };
            foreach (var (lieu, nom) in lieux)
            {
                var p = carte.Trouver(lieu).p;
                cmd.foyer = new Vector3(p.x, 60, p.y); cmd.plongee = 60; cmd.distance = 80; cmd.cap = 0;
                yield return Capture(nom);
            }
            cmd.foyer = new Vector3(citadelle.x, 60, citadelle.y); cmd.plongee = 35; cmd.distance = 420; cmd.cap = 200;
            yield return Capture("citadelle");

            foreach (var p in res)
            {
                var m = new List<string>();
                if (!p.arrive) m.Add($"{p.nom} : pas arrivé en {Limite:0} s (à {p.ecart_a_l_arrivee_m:0} m du but)");
                if (p.a_sa_place < PartMin) m.Add($"{p.nom} : {p.a_sa_place:P0} des hommes à leur place à l'arrivée (au moins {PartMin:P0})");
                if (p.dans_un_mur_max > 0) m.Add($"{p.nom} : jusqu'à {p.dans_un_mur_max} hommes dans l'emprise d'un mur ou d'une maison");
                if (p.tombes_dans_le_ravin > 0) m.Add($"{p.nom} : des hommes sont tombés dans le ravin");
                p.franchissable = m.Count == 0;
                motifs.AddRange(m);
            }
            rapport.parcours = res;
            Finir(rapport, motifs);
        }

        // Diagnostic : la grille des obstacles vue par la simulation, un pixel par mètre autour de la
        // citadelle (noir : bloqué), les routes des régiments en rouge, et le dégagement en quelques lieux.
        static void Grille(Bataille b, EntityManager em, float2 centre, Entity[] regiments, CarteDonnees carte)
        {
            const int N = 640;
            var img = new Texture2D(N, N, TextureFormat.RGB24, false);
            var obst = em.CreateEntityQuery(typeof(Obstacles)).GetSingleton<Obstacles>().Blob;
            for (int y = 0; y < N; y++)
                for (int x = 0; x < N; x++)
                {
                    var p = centre + new float2(x - N / 2 + 0.5f, y - N / 2 + 0.5f) * 0.5f;
                    img.SetPixel(x, y, Terrain2D.Bloque(ref obst.Value, p) ? Color.black : new Color(0.9f, 0.88f, 0.8f));
                }
            foreach (var e in regiments)
            {
                var route = em.GetBuffer<PointChemin>(e);
                for (int k = 1; k < route.Length; k++)
                    for (float u = 0; u <= 1; u += 0.02f)
                    {
                        var p = (math.lerp(route[k - 1].P, route[k].P, u) - centre) * 2f + N / 2;
                        if (p.x >= 0 && p.y >= 0 && p.x < N && p.y < N) img.SetPixel((int)p.x, (int)p.y, Color.red);
                    }
            }
            File.WriteAllBytes(Path.Combine(sortie, "grille.png"), img.EncodeToPNG());
            Destroy(img);
            var lignes = new List<string>();
            foreach (var (nom, local) in new[] { ("porte", new float2(0, -95.4f)), ("pont", new float2(0, -116f)), ("grand-rue", new float2(0, -75f)),
                                                  ("rue traversière", new float2(-30, -55f)), ("place", new float2(0, -5f)), ("place de l'est", new float2(48, -55)) })
            {
                var p = centre + local;
                lignes.Add($"{nom} : dégagement {b.Planificateur.DegagementEn(new Vector2(p.x, p.y)):0.0} m");
            }
            File.WriteAllLines(Path.Combine(sortie, "degagements.txt"), lignes);
        }

        void Finir(Rapport r, List<string> motifs)
        {
            r.motifs = motifs.ToArray();
            r.statut = motifs.Count == 0 ? "valide" : "echec";
            File.WriteAllText(Path.Combine(sortie, "essai-carte.json"), JsonUtility.ToJson(r, true));
            Debug.Log("[EssaisCarte] " + r.statut + " " + string.Join(" | ", motifs));
            Application.Quit(motifs.Count == 0 ? 0 : 1);
        }

        IEnumerator Capture(string nom)
        {
            float ts = Time.timeScale; Time.timeScale = 0;
            for (int k = 0; k < 6; k++) yield return null;
            yield return new WaitForEndOfFrame();
            var img = ScreenCapture.CaptureScreenshotAsTexture();
            File.WriteAllBytes(Path.Combine(sortie, nom + ".jpg"), img.EncodeToJPG(85));
            Destroy(img);
            Time.timeScale = ts;
        }
    }
}
