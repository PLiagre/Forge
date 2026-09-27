using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Unity.Collections;
using Unity.Entities;
using Unity.Mathematics;
using UnityEngine;

namespace Guerre
{
    // Essai du jalon 6 dans le vrai joueur, avec 20 000 hommes :
    //   Citadelle-Guerre.exe -guerre-essai-tir -guerre-soldats 20000 -guerre-sortie DOSSIER [-guerre-sans-pavois]
    // Dans les deux temps, des régiments d'arbalétriers bleus tirent sur des régiments d'arbalétriers
    // rouges immobiles, face à eux ; une cible sur deux a planté ses pavois, l'autre n'en a pas.
    //   1. La salve plongeante, à 220 m : douze paires. Plus de 2 000 carreaux en vol à la fois, et le
    //      95e centile des images reste sous 16,67 ms. Les carreaux tombent en cloche et frappent les
    //      hommes par le haut : on y relève, pour information, ce que valent les pavois.
    //   2. Le tir tendu, à 100 m : douze autres paires. Les régiments à pavois sont touchés au plus
    //      60 % autant que les autres : le pavois arrête les carreaux par sa seule géométrie.
    // Avec -guerre-sans-pavois, les pavois n'arrêtent plus rien : l'essai doit échouer.
    public sealed class EssaisTir : MonoBehaviour
    {
        [Serializable] public class Rapport
        {
            public string statut, date_utc, gpu; public bool sans_pavois;
            // 1. La salve plongeante.
            public int carreaux_en_vol_max, images_a_plus_de_2000;
            public double p95_ms_a_plus_de_2000, mediane_ms_a_plus_de_2000;
            public int plongeant_touches_avec_pavois, plongeant_touches_sans_pavois;
            public float plongeant_rapport_des_touches;
            // 2. Le tir tendu.
            public int touches_avec_pavois, touches_sans_pavois, morts_avec_pavois, morts_sans_pavois;
            public float rapport_des_touches;
            // L'ensemble.
            public int carreaux_tires, arretes_par_pavois, plantes_au_sol, touches_tireurs;
            public string[] motifs;
        }

        static string sortie; static bool sansPavois;
        const float DureeSalve = 20f, DureeTendu = 40f, DistanceSalve = 220f, DistanceTendu = 100f;
        const int Paires = 12, EnVolMin = 2000;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Demarrer()
        {
            var args = Environment.GetCommandLineArgs();
            if (!args.Contains("-guerre-essai-tir")) return;
            int i = Array.IndexOf(args, "-guerre-sortie");
            sortie = i >= 0 && i + 1 < args.Length ? args[i + 1] : Path.Combine(Application.persistentDataPath, "essai-tir");
            sansPavois = args.Contains("-guerre-sans-pavois");
            var go = new GameObject("Essais de tir"); DontDestroyOnLoad(go); go.AddComponent<EssaisTir>();
        }

        Bataille b; EntityManager em;

        // Place une rangée de paires face à face, une cible sur deux sans pavois ; renvoie tireurs et cibles.
        (Entity[] tireurs, List<Entity> avec, List<Entity> sans) Deployer(Entity[] bleus, Entity[] rouges, float2 centre, float distance)
        {
            var axe = new float2(1, 0);
            var avec = new List<Entity>(); var sans = new List<Entity>();
            for (int k = 0; k < bleus.Length; k++)
            {
                float2 lieu = centre + new float2(0, (k - (bleus.Length - 1) / 2f) * 50f);
                b.Deplacer(bleus[k], lieu - axe * distance / 2, axe, 25);
                b.Deplacer(rouges[k], lieu + axe * distance / 2, -axe, 25);
                // Une paire sur deux sans pavois, en alternance, pour que le lieu ne favorise personne.
                var rg = em.GetComponentData<Regiment>(rouges[k]);
                rg.SansPavois = (byte)(k % 2);
                rg.Touches = 0;
                em.SetComponentData(rouges[k], rg);
                (k % 2 == 0 ? avec : sans).Add(rouges[k]);
            }
            return (bleus, avec, sans);
        }

        int Touches(IEnumerable<Entity> regs) => regs.Sum(e => em.GetComponentData<Regiment>(e).Touches);
        int Morts(IEnumerable<Entity> regs) => regs.Sum(e => 250 - em.GetComponentData<Regiment>(e).Effectif);

        IEnumerator Start()
        {
            Directory.CreateDirectory(sortie);
            QualitySettings.vSyncCount = 0; Application.targetFrameRate = -1;
            while (Bataille.Instance == null || !Bataille.Instance.Pret) yield return null;
            b = Bataille.Instance; em = b.Em;
            var cmd = FindFirstObjectByType<Commandement>(); cmd.automatique = true; cmd.montrerAide = false;
            var motifs = new List<string>();
            b.Ordonner(b.Regiments().Select(x => (x.e, x.r.Position, x.r.Front, x.r.Files)).ToList());
            yield return null;

            var bleus = b.Regiments(0).Where(x => x.r.Arme == 2).OrderBy(x => x.r.Index).Select(x => x.e).ToArray();
            var rouges = b.Regiments(1).Where(x => x.r.Arme == 2).OrderBy(x => x.r.Index).Select(x => x.e).ToArray();
            var r = new Rapport { date_utc = DateTime.UtcNow.ToString("o"), gpu = SystemInfo.graphicsDeviceName, sans_pavois = sansPavois };
            if (bleus.Length < 2 * Paires || rouges.Length < 2 * Paires)
            {
                motifs.Add($"il faut {2 * Paires} régiments d'arbalétriers par camp (-guerre-soldats 20000)");
                Finir(r, motifs); yield break;
            }
            var t = b.terrain.transform.position + b.terrain.terrainData.size * 0.5f;
            float2 centre = new float2(t.x, t.z);
            var salve = Deployer(bleus.Take(Paires).ToArray(), rouges.Take(Paires).ToArray(), centre - new float2(300, 0), DistanceSalve);
            var tendu = Deployer(bleus.Skip(Paires).Take(Paires).ToArray(), rouges.Skip(Paires).Take(Paires).ToArray(), centre + new float2(300, 0), DistanceTendu);
            for (int k = 0; k < 30; k++) yield return null;

            // 1. La salve plongeante.
            for (int k = 0; k < Paires; k++) b.Attaquer(new[] { salve.tireurs[k] }, rouges[k]);
            cmd.foyer = new Vector3(centre.x - 300 + DistanceSalve / 2 - 20, 0, centre.y); cmd.plongee = 22; cmd.distance = 90; cmd.cap = -70;
            var carreaux = em.CreateEntityQuery(typeof(Projectile));
            var temps = new List<double>();
            float debut = Time.time; int enVol = 0, image = 0, pic = 0;
            while (Time.time - debut < DureeSalve)
            {
                cmd.cap += 3f * Time.unscaledDeltaTime;
                yield return null;
                if (image++ % 5 == 0)
                {
                    em.CompleteAllTrackedJobs();
                    using var ps = carreaux.ToComponentDataArray<Projectile>(Allocator.Temp);
                    enVol = 0; foreach (var p in ps) if (p.Etat == 1) enVol++;
                    r.carreaux_en_vol_max = Math.Max(r.carreaux_en_vol_max, enVol);
                }
                if (enVol >= EnVolMin) temps.Add(Time.unscaledDeltaTime * 1000.0);
                if (enVol > pic + 200) { pic = enVol; yield return new WaitForEndOfFrame(); Capture("salve"); }
            }
            // Cessez le tir : les tireurs de la salve s'arrêtent, et l'on attend que leurs carreaux retombent.
            b.Ordonner(salve.tireurs.Select(e => { var x = em.GetComponentData<Regiment>(e); return (e, x.Position, x.Front, x.Files); }).ToList());
            float repos = Time.time; while (Time.time - repos < 6f) yield return null;
            r.images_a_plus_de_2000 = temps.Count;
            if (temps.Count > 0)
            {
                temps.Sort();
                r.p95_ms_a_plus_de_2000 = temps[Mathf.Clamp((int)Math.Ceiling(0.95 * temps.Count) - 1, 0, temps.Count - 1)];
                r.mediane_ms_a_plus_de_2000 = temps[temps.Count / 2];
            }
            r.plongeant_touches_avec_pavois = Touches(salve.avec);
            r.plongeant_touches_sans_pavois = Touches(salve.sans);
            r.plongeant_rapport_des_touches = r.plongeant_touches_sans_pavois > 0 ? r.plongeant_touches_avec_pavois / (float)r.plongeant_touches_sans_pavois : 1f;

            // 2. Le tir tendu.
            for (int k = 0; k < Paires; k++) b.Attaquer(new[] { tendu.tireurs[k] }, rouges[Paires + k]);
            cmd.foyer = new Vector3(centre.x + 300 + DistanceTendu / 2 - 10, 0, centre.y); cmd.plongee = 18; cmd.distance = 45; cmd.cap = -80;
            debut = Time.time; bool capture = false;
            while (Time.time - debut < DureeTendu)
            {
                yield return null;
                if (!capture && Time.time - debut > 12f) { capture = true; yield return new WaitForEndOfFrame(); Capture("tendu"); }
            }
            r.touches_avec_pavois = Touches(tendu.avec);
            r.touches_sans_pavois = Touches(tendu.sans);
            r.morts_avec_pavois = Morts(tendu.avec);
            r.morts_sans_pavois = Morts(tendu.sans);
            r.rapport_des_touches = r.touches_sans_pavois > 0 ? r.touches_avec_pavois / (float)r.touches_sans_pavois : 1f;

            var compte = em.CreateEntityQuery(typeof(CompteTir)).GetSingleton<CompteTir>();
            r.carreaux_tires = compte.Tires; r.arretes_par_pavois = compte.Pavois; r.plantes_au_sol = compte.AuSol;
            r.touches_tireurs = Touches(salve.tireurs) + Touches(tendu.tireurs);

            if (r.carreaux_en_vol_max < EnVolMin) motifs.Add($"{r.carreaux_en_vol_max} carreaux en vol au plus, {EnVolMin} attendus");
            if (r.images_a_plus_de_2000 < 60) motifs.Add($"seulement {r.images_a_plus_de_2000} images mesurées avec plus de {EnVolMin} carreaux en vol");
            else if (r.p95_ms_a_plus_de_2000 >= 1000.0 / 60.0) motifs.Add($"95e centile de {r.p95_ms_a_plus_de_2000:0.00} ms avec plus de {EnVolMin} carreaux en vol");
            if (r.touches_sans_pavois < 100) motifs.Add($"tir tendu : seulement {r.touches_sans_pavois} touches sur les régiments sans pavois, le tir ne porte pas");
            else if (r.rapport_des_touches > 0.6f) motifs.Add($"tir tendu : avec pavois, {r.rapport_des_touches:P0} des touches sans pavois (au plus 60 %)");
            if (r.arretes_par_pavois == 0) motifs.Add("aucun carreau arrêté par un pavois");
            Finir(r, motifs);
        }

        void Finir(Rapport r, List<string> motifs)
        {
            r.motifs = motifs.ToArray();
            r.statut = motifs.Count == 0 ? "valide" : "echec";
            File.WriteAllText(Path.Combine(sortie, "essai-tir.json"), JsonUtility.ToJson(r, true));
            Debug.Log("[EssaisTir] " + r.statut + " " + string.Join(" | ", motifs));
            Application.Quit(motifs.Count == 0 ? 0 : 1);
        }

        void Capture(string nom)
        {
            var img = ScreenCapture.CaptureScreenshotAsTexture();
            File.WriteAllBytes(Path.Combine(sortie, nom + ".jpg"), img.EncodeToJPG(85));
            Destroy(img);
        }
    }
}
