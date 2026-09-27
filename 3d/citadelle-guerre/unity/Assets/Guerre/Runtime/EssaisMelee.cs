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
    // Essai du jalon 4 dans le vrai joueur :
    //   Citadelle-Guerre.exe -guerre-essai-melee -guerre-sortie DOSSIER [-guerre-sans-poussee]
    // Trois duels de régiments de même front (25 files), qui s'attaquent l'un l'autre :
    //   1. bleus sur 10 rangs contre rouges sur 5 ;   2. bleus sur 5 contre rouges sur 10 ;
    //   3. 10 contre 10, pour témoin.
    // La ligne de contact doit reculer devant le plus profond, dans les deux sens : aucune
    // règle ne donne l'avantage à la profondeur, il vient des rangs arrière qui poussent.
    // Avec -guerre-sans-poussee, seuls les hommes au contact poussent : l'essai doit échouer.
    public sealed class EssaisMelee : MonoBehaviour
    {
        [Serializable] public class Duel
        {
            public string nom; public int rangs_bleus, rangs_rouges;
            public float recul_de_la_ligne_m;   // > 0 : la ligne avance vers les rouges
            public int morts_bleus, morts_rouges, contacts_max;
            public float distance_min_ennemis_m, fatigue_moyenne;
            // Diagnostic : centres des deux régiments le long de l'axe, et part des bleus passés au-delà de la médiane des rouges.
            public float centre_bleu_debut, centre_bleu_fin, centre_rouge_debut, centre_rouge_fin, melange_max, melange_pendant_la_poussee;
            public float presse_front_bleu, presse_front_rouge, ecart_bleu, ecart_rouge, largeur_bleue, largeur_rouge, ancres_m;
            public float[] retard_par_rang_bleu, retard_par_rang_rouge;
            public List<float> melange_au_fil_du_temps = new List<float>();   // toutes les 2 s // m de retard sur sa place, le long de l'axe du régiment
        }
        [Serializable] public class Rapport
        {
            public string statut, date_utc; public bool sans_poussee;
            public float secondes; public Duel[] duels; public string[] motifs;
        }

        static string sortie; static bool sansPoussee;
        // Le mélange est jugé pendant la poussée. Au-delà de 45 s, les régiments témoins, usés
        // (15 % de morts, 40 % de fatigue), commencent à se défaire : c'est au moral de les faire
        // rompre avant (jalon 5). La série complète reste dans le rapport.
        const float Duree = 60f, Seuil = 3f, FenetrePoussee = 45f;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Demarrer()
        {
            var args = Environment.GetCommandLineArgs();
            if (!args.Contains("-guerre-essai-melee")) return;
            int i = Array.IndexOf(args, "-guerre-sortie");
            sortie = i >= 0 && i + 1 < args.Length ? args[i + 1] : Path.Combine(Application.persistentDataPath, "essai-melee");
            sansPoussee = args.Contains("-guerre-sans-poussee");
            var go = new GameObject("Essais de mêlée"); DontDestroyOnLoad(go); go.AddComponent<EssaisMelee>();
        }

        IEnumerator Start()
        {
            Directory.CreateDirectory(sortie);
            QualitySettings.vSyncCount = 0; Application.targetFrameRate = -1;
            while (Bataille.Instance == null || !Bataille.Instance.Pret) yield return null;
            var b = Bataille.Instance; var em = b.Em;
            var cmd = FindFirstObjectByType<Commandement>(); cmd.automatique = true; cmd.montrerAide = false;
            // Tout le monde s'arrête : le scénario de démonstration ne doit rien engager.
            b.Ordonner(b.Regiments().Select(x => (x.e, x.r.Position, x.r.Front, x.r.Files)).ToList());
            yield return null;

            var bleus = b.Regiments(0).OrderBy(x => x.r.Index).Select(x => x.e).ToArray();
            var rouges = b.Regiments(1).OrderBy(x => x.r.Index).Select(x => x.e).ToArray();
            var t = b.terrain.transform.position + b.terrain.terrainData.size * 0.5f;
            float2 centre = new float2(t.x, t.z), axe = new float2(1, 0);
            var duels = new[]
            {
                (nom: "bleus profonds", bleu: bleus[4], rouge: rouges[4], rb: 10, rr: 5, lieu: centre + new float2(0, -160)),
                (nom: "rouges profonds", bleu: bleus[5], rouge: rouges[5], rb: 5, rr: 10, lieu: centre),
                (nom: "témoin", bleu: bleus[6], rouge: rouges[6], rb: 10, rr: 10, lieu: centre + new float2(0, 160)),
            };
            const int Files = 25;
            foreach (var d in duels)
            {
                if (d.rb < 10) b.Reduire(d.bleu, 250 - Files * d.rb);
                if (d.rr < 10) b.Reduire(d.rouge, 250 - Files * d.rr);
                b.Deplacer(d.bleu, d.lieu - axe * 16, axe, Files);
                b.Deplacer(d.rouge, d.lieu + axe * 16, -axe, Files);
            }
            for (int k = 0; k < 10; k++) yield return null;
            foreach (var d in duels) { b.Attaquer(new[] { d.bleu }, d.rouge); b.Attaquer(new[] { d.rouge }, d.bleu); }
            cmd.foyer = new Vector3(centre.x, 0, centre.y - 160); cmd.plongee = 35; cmd.distance = 70; cmd.cap = 0;
            Time.timeScale = 4;

            var soldats = em.CreateEntityQuery(typeof(Soldat), typeof(LocalTransform));
            var resultats = duels.Select(d => new Duel { nom = d.nom, rangs_bleus = d.rb, rangs_rouges = d.rr, distance_min_ennemis_m = float.MaxValue }).ToArray();
            var ligneDebut = new float?[duels.Length];
            var ligneFin = new List<float>[duels.Length];
            for (int k = 0; k < duels.Length; k++) ligneFin[k] = new List<float>();
            float debut = Time.time, prochaine = 0;
            bool capture = false;
            while (Time.time - debut < Duree)
            {
                yield return null;
                if (Time.time < prochaine) continue;
                prochaine = Time.time + 0.5f;
                em.CompleteAllTrackedJobs();
                var ss = soldats.ToComponentDataArray<Soldat>(Allocator.Temp);
                var tt = soldats.ToComponentDataArray<LocalTransform>(Allocator.Temp);
                for (int k = 0; k < duels.Length; k++)
                {
                    var d = duels[k]; var res = resultats[k];
                    // La ligne de contact : la position moyenne, le long de l'axe, des hommes qui touchent l'ennemi.
                    float somme = 0; int n = 0, nb = 0, nr = 0;
                    var pb = new List<float2>(); var pr = new List<float2>();
                    var xb = new List<float>(); var xr = new List<float>();
                    float pfb = 0, pfr = 0, eb = 0, er = 0; int npb = 0, npr = 0;
                    float ymin_b = 1e9f, ymax_b = -1e9f, ymin_r = 1e9f, ymax_r = -1e9f;
                    for (int i = 0; i < ss.Length; i++)
                    {
                        bool estBleu = ss[i].Regiment == d.bleu, estRouge = ss[i].Regiment == d.rouge;
                        if (!estBleu && !estRouge) continue;
                        if (estBleu) nb++; else nr++;
                        float2 p = tt[i].Position.xz;
                        if (ss[i].Contact != 0) { somme += math.dot(p - d.lieu, axe); n++; (estBleu ? pb : pr).Add(p); }
                        (estBleu ? xb : xr).Add(math.dot(p - d.lieu, axe));
                        if (ss[i].Contact != 0) { if (estBleu) { pfb += ss[i].Presse; npb++; } else { pfr += ss[i].Presse; npr++; } }
                        if (estBleu) { eb += ss[i].Ecart; ymin_b = math.min(ymin_b, p.y); ymax_b = math.max(ymax_b, p.y); }
                        else { er += ss[i].Ecart; ymin_r = math.min(ymin_r, p.y); ymax_r = math.max(ymax_r, p.y); }
                    }
                    if (xb.Count > 0 && xr.Count > 0)
                    {
                        xr.Sort();
                        float mediane = xr[xr.Count / 2];
                        float mel = xb.Count(x => x > mediane) / (float)xb.Count;
                        res.melange_max = Mathf.Max(res.melange_max, mel);
                        if (Time.time - debut <= FenetrePoussee) res.melange_pendant_la_poussee = Mathf.Max(res.melange_pendant_la_poussee, mel);
                        if (res.melange_au_fil_du_temps.Count < (Time.time - debut) / 2f) res.melange_au_fil_du_temps.Add((float)Math.Round(mel, 2));
                        if (res.centre_bleu_debut == 0) { res.centre_bleu_debut = xb.Average(); res.centre_rouge_debut = xr.Average(); }
                        res.centre_bleu_fin = xb.Average(); res.centre_rouge_fin = xr.Average();
                    }
                    res.contacts_max = Math.Max(res.contacts_max, n);
                    foreach (var a in pb) foreach (var c in pr) res.distance_min_ennemis_m = Mathf.Min(res.distance_min_ennemis_m, math.distance(a, c));
                    if (n >= 10)
                    {
                        float ligne = somme / n;
                        // Le point de départ : la ligne mesurée pendant les premières secondes du choc.
                        if (ligneDebut[k] == null) ligneDebut[k] = ligne;
                        if (Time.time - debut > Duree - 8f) ligneFin[k].Add(ligne);
                    }
                    if (Time.time - debut > Duree - 8f)
                    {
                        res.presse_front_bleu = npb > 0 ? pfb / npb : 0; res.presse_front_rouge = npr > 0 ? pfr / npr : 0;
                        res.ecart_bleu = nb > 0 ? eb / nb : 0; res.ecart_rouge = nr > 0 ? er / nr : 0;
                        res.largeur_bleue = ymax_b - ymin_b; res.largeur_rouge = ymax_r - ymin_r;
                        res.retard_par_rang_bleu = Retards(em, ss, tt, d.bleu);
                        res.retard_par_rang_rouge = Retards(em, ss, tt, d.rouge);
                        res.ancres_m = math.distance(em.GetComponentData<Regiment>(d.bleu).Position, em.GetComponentData<Regiment>(d.rouge).Position);
                    }
                    res.morts_bleus = Files * d.rb - nb;
                    res.morts_rouges = Files * d.rr - nr;
                }
                ss.Dispose(); tt.Dispose();   // mémoire d'une image : rendue avant tout yield
                if (!capture && Time.time - debut > 25)
                {
                    capture = true;
                    yield return Capture("melee_bleus_profonds");
                }
            }

            // Vues de dessus de chaque duel à la fin, pour voir comment les régiments se tiennent.
            for (int k = 0; k < duels.Length; k++)
            {
                cmd.foyer = new Vector3(duels[k].lieu.x, 0, duels[k].lieu.y); cmd.plongee = 80; cmd.distance = 45; cmd.cap = 0;
                yield return Capture("fin_" + k);
            }
            var motifs = new List<string>();
            em.CompleteAllTrackedJobs();
            using (var ss = soldats.ToComponentDataArray<Soldat>(Allocator.Temp))
                for (int k = 0; k < duels.Length; k++)
                {
                    var hommes = ss.Where(x => x.Regiment == duels[k].bleu || x.Regiment == duels[k].rouge).ToArray();
                    resultats[k].fatigue_moyenne = hommes.Length == 0 ? 0 : hommes.Average(x => x.Fatigue);
                }
            for (int k = 0; k < duels.Length; k++)
            {
                var res = resultats[k];
                if (ligneDebut[k] == null || ligneFin[k].Count == 0) { motifs.Add($"{res.nom} : les régiments ne se sont pas engagés"); continue; }
                res.recul_de_la_ligne_m = ligneFin[k].Average() - ligneDebut[k].Value;
                if (res.distance_min_ennemis_m < 0.4f) motifs.Add($"{res.nom} : deux ennemis à {res.distance_min_ennemis_m:0.00} m, les corps se traversent");
            }
            if (resultats[0].recul_de_la_ligne_m < Seuil)
                motifs.Add($"bleus profonds : la ligne n'a avancé que de {resultats[0].recul_de_la_ligne_m:0.0} m vers les rouges (au moins {Seuil} m attendus)");
            if (resultats[1].recul_de_la_ligne_m > -Seuil)
                motifs.Add($"rouges profonds : la ligne n'a reculé que de {-resultats[1].recul_de_la_ligne_m:0.0} m vers les bleus (au moins {Seuil} m attendus)");
            if (resultats.Sum(x => x.morts_bleus + x.morts_rouges) == 0) motifs.Add("aucun mort : les coups ne portent pas");
            // Repousser n'est pas traverser : chaque régiment reste de son côté, et les rangs ne s'entremêlent pas.
            foreach (var res in resultats)
            {
                if (res.centre_bleu_fin > res.centre_rouge_fin - 1f) motifs.Add($"{res.nom} : les régiments se sont traversés (bleus à {res.centre_bleu_fin:0.0} m, rouges à {res.centre_rouge_fin:0.0} m)");
                if (res.melange_pendant_la_poussee > 0.15f) motifs.Add($"{res.nom} : {res.melange_pendant_la_poussee:P0} des bleus sont passés au-delà du milieu des rouges pendant la poussée");
            }

            var rapport = new Rapport
            {
                date_utc = DateTime.UtcNow.ToString("o"), sans_poussee = sansPoussee, secondes = Time.time - debut,
                duels = resultats, motifs = motifs.ToArray(), statut = motifs.Count == 0 ? "valide" : "echec",
            };
            File.WriteAllText(Path.Combine(sortie, "essai-melee.json"), JsonUtility.ToJson(rapport, true));
            Debug.Log("[EssaisMelee] " + rapport.statut + " " + string.Join(" | ", motifs));
            Application.Quit(motifs.Count == 0 ? 0 : 1);
        }

        static float[] Retards(EntityManager em, NativeArray<Soldat> ss, NativeArray<LocalTransform> tt, Entity e)
        {
            var r = em.GetComponentData<Regiment>(e);
            int rangs = math.max(1, r.Rangs);
            var somme = new float[rangs]; var n = new int[rangs];
            for (int i = 0; i < ss.Length; i++)
            {
                if (ss[i].Regiment != e) continue;
                float2 place = Formation.VersMonde(Formation.Place(r, ss[i].Numero) + ss[i].Decalage, r.Position, r.Front);
                int rg = math.min(rangs - 1, ss[i].Numero / math.max(1, math.min(r.Files, r.Effectif)));
                somme[rg] += math.dot(place - tt[i].Position.xz, r.Front); n[rg]++;
            }
            return somme.Select((x, k) => n[k] > 0 ? (float)Math.Round(x / n[k], 2) : 0f).ToArray();
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
