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
    // Essai du jalon 5 dans le vrai joueur :
    //   Citadelle-Guerre.exe -guerre-essai-moral -guerre-sortie DOSSIER [-guerre-sans-peur]
    // Lancé avec -guerre-soldats 20000 : vingt épreuves côte à côte, à armes égales (des piquiers partout). Dans chacune, un régiment
    // bleu est aux prises de front avec un régiment rouge de même force, et un second régiment
    // rouge est là :
    //   - « flanc » (dix fois) : au bout de 12 s, il attaque par le côté ;
    //   - « réserve » (dix fois) : il reste placé derrière le premier, sans attaquer.
    // La simulation est chaotique : on juge sur la moyenne, par condition, de la part la plus haute
    // des hommes en fuite (une grandeur continue), et sur le nombre de ruptures.
    // Une réserve qui attaquait aussi contournait ses amis et frappait de flanc : le témoin était faux.
    // Le régiment pris de flanc doit rompre plus souvent. Rien ne dit « flanc » dans la peur :
    // on ne pare et ne frappe que devant soi, et l'on a peur de voir tomber ses voisins.
    // Des fuyards doivent aussi revenir : la fuite n'est pas une disparition.
    // Avec -guerre-sans-peur, personne ne fuit : l'essai doit échouer.
    public sealed class EssaisMoral : MonoBehaviour
    {
        [Serializable] public class Epreuve
        {
            public string condition; public bool rompu; public float rompu_apres_s = -1, fuyards_max;
            public int morts_bleus, morts_rouges, ralliements;
        }
        [Serializable] public class Rapport
        {
            public string statut, date_utc; public bool sans_peur; public float secondes;
            public int ruptures_flanc, ruptures_reserve, ralliements;
            public float fuite_moyenne_flanc, fuite_moyenne_reserve;
            public Epreuve[] epreuves; public string[] motifs;
        }

        static string sortie; static bool sansPeur;
        const float Duree = 90f, Renfort = 12f;
        const int Epreuves = 20, ParCondition = Epreuves / 2;
        const float EcartMin = 0.10f;   // la fuite doit être plus forte de dix points quand on est pris de flanc

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Demarrer()
        {
            var args = Environment.GetCommandLineArgs();
            if (!args.Contains("-guerre-essai-moral")) return;
            int i = Array.IndexOf(args, "-guerre-sortie");
            sortie = i >= 0 && i + 1 < args.Length ? args[i + 1] : Path.Combine(Application.persistentDataPath, "essai-moral");
            sansPeur = args.Contains("-guerre-sans-peur");
            var go = new GameObject("Essais de moral"); DontDestroyOnLoad(go); go.AddComponent<EssaisMoral>();
        }

        IEnumerator Start()
        {
            Directory.CreateDirectory(sortie);
            QualitySettings.vSyncCount = 0; Application.targetFrameRate = -1;
            while (Bataille.Instance == null || !Bataille.Instance.Pret) yield return null;
            var b = Bataille.Instance; var em = b.Em;
            var cmd = FindFirstObjectByType<Commandement>(); cmd.automatique = true; cmd.montrerAide = false;
            b.Ordonner(b.Regiments().Select(x => (x.e, x.r.Position, x.r.Front, x.r.Files)).ToList());
            yield return null;

            var bleus = b.Regiments(0).OrderBy(x => x.r.Index).Select(x => x.e).ToArray();
            var rouges = b.Regiments(1).OrderBy(x => x.r.Index).Select(x => x.e).ToArray();
            var t = b.terrain.transform.position + b.terrain.terrainData.size * 0.5f;
            float2 centre = new float2(t.x, t.z), axe = new float2(1, 0), cote = new float2(0, 1);
            const int Files = 25;
            var epreuves = new List<(string condition, Entity bleu, Entity r1, Entity r2, float2 lieu)>();
            for (int k = 0; k < Epreuves; k++)
            {
                string condition = k % 2 == 0 ? "flanc" : "réserve";
                // Quatre colonnes de cinq épreuves, dans le fond plat de la vallée.
                float2 lieu = centre + new float2((k / 5) * 150f - 225f, (k % 5) * 110f - 220f);
                epreuves.Add((condition, bleus[k], rouges[2 * k], rouges[2 * k + 1], lieu));
                // À armes égales : des piquiers partout, pour que seule la disposition diffère.
                foreach (var x in new[] { bleus[k], rouges[2 * k], rouges[2 * k + 1] }) b.Armer(x, 0);
                b.Deplacer(bleus[k], lieu - axe * 16, axe, Files);
                b.Deplacer(rouges[2 * k], lieu + axe * 16, -axe, Files);
                if (condition == "flanc") b.Deplacer(rouges[2 * k + 1], lieu + cote * 40, -cote, Files);
                else b.Deplacer(rouges[2 * k + 1], lieu + axe * 32, -axe, Files);
            }
            for (int k = 0; k < 10; k++) yield return null;
            foreach (var p in epreuves) { b.Attaquer(new[] { p.bleu }, p.r1); b.Attaquer(new[] { p.r1 }, p.bleu); }
            cmd.foyer = new Vector3(epreuves[0].lieu.x, 0, epreuves[0].lieu.y); cmd.plongee = 50; cmd.distance = 90; cmd.cap = 0;
            Time.timeScale = 4;

            var res = epreuves.Select(p => new Epreuve { condition = p.condition }).ToArray();
            float debut = Time.time, prochaine = 0;
            bool renforts = false, capture = false;
            var soldats = em.CreateEntityQuery(typeof(Soldat));
            while (Time.time - debut < Duree)
            {
                yield return null;
                if (!renforts && Time.time - debut > Renfort)
                {
                    renforts = true;
                    foreach (var p in epreuves) if (p.condition == "flanc") b.Attaquer(new[] { p.r2 }, p.bleu);
                }
                if (!capture && Time.time - debut > 40) { capture = true; yield return Capture("flanc_40s"); }
                if (Time.time < prochaine) continue;
                prochaine = Time.time + 0.5f;
                for (int k = 0; k < epreuves.Count; k++)
                {
                    var rg = em.GetComponentData<Regiment>(epreuves[k].bleu);
                    res[k].fuyards_max = Mathf.Max(res[k].fuyards_max, rg.Fuyards);
                    if (!res[k].rompu && rg.Deroute != 0) { res[k].rompu = true; res[k].rompu_apres_s = Time.time - debut; }
                }
            }

            em.CompleteAllTrackedJobs();
            var ss = soldats.ToComponentDataArray<Soldat>(Allocator.Temp);
            for (int k = 0; k < epreuves.Count; k++)
            {
                var p = epreuves[k];
                int vivantsB = 0, vivantsR = 0;
                foreach (var x in ss)
                {
                    if (x.Regiment == p.bleu) vivantsB++;
                    if (x.Regiment == p.r1 || x.Regiment == p.r2) vivantsR++;
                    if (x.Regiment == p.bleu || x.Regiment == p.r1 || x.Regiment == p.r2) res[k].ralliements += x.Ralliements;
                }
                res[k].morts_bleus = 250 - vivantsB;
                res[k].morts_rouges = 500 - vivantsR;
            }
            ss.Dispose();

            var rapport = new Rapport
            {
                date_utc = DateTime.UtcNow.ToString("o"), sans_peur = sansPeur, secondes = Time.time - debut, epreuves = res,
                ruptures_flanc = res.Count(x => x.condition == "flanc" && x.rompu),
                ruptures_reserve = res.Count(x => x.condition == "réserve" && x.rompu),
                ralliements = res.Sum(x => x.ralliements),
                fuite_moyenne_flanc = res.Where(x => x.condition == "flanc").Average(x => x.fuyards_max),
                fuite_moyenne_reserve = res.Where(x => x.condition == "réserve").Average(x => x.fuyards_max),
            };
            var motifs = new List<string>();
            if (b.Leves < 20000) motifs.Add($"l'essai demande 20 000 hommes (-guerre-soldats 20000), {b.Leves} levés");
            if (rapport.fuite_moyenne_flanc < rapport.fuite_moyenne_reserve + EcartMin)
                motifs.Add($"pris de flanc, on ne fuit pas plus : {rapport.fuite_moyenne_flanc:P0} au plus fort contre {rapport.fuite_moyenne_reserve:P0} face à une réserve");
            if (rapport.ruptures_flanc <= rapport.ruptures_reserve)
                motifs.Add($"le flanc ne fait pas rompre plus souvent : {rapport.ruptures_flanc} ruptures de flanc contre {rapport.ruptures_reserve} face à une réserve");
            if (rapport.ralliements == 0) motifs.Add("aucun fuyard n'est revenu : la fuite n'a pas de retour");
            rapport.motifs = motifs.ToArray();
            rapport.statut = motifs.Count == 0 ? "valide" : "echec";
            File.WriteAllText(Path.Combine(sortie, "essai-moral.json"), JsonUtility.ToJson(rapport, true));
            Debug.Log("[EssaisMoral] " + rapport.statut + " " + string.Join(" | ", motifs));
            Application.Quit(motifs.Count == 0 ? 0 : 1);
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
