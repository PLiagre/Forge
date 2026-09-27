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
    // Essai du jalon 7 dans le vrai joueur, avec 20 000 hommes :
    //   Citadelle-Guerre.exe -guerre-essai-cavalerie -guerre-soldats 20000 -guerre-sortie DOSSIER [-guerre-sans-masse | -guerre-sans-piques]
    // Vingt couloirs côte à côte. Dans chacun, 80 hommes d'armes (20 de front, 4 rangs) chargent
    // à 150 m un régiment immobile de 250 hommes qui leur fait face :
    //   - « non préparé » (dix fois) : des arbalétriers sans pavois, à la dague ;
    //   - « piques » (dix fois) : des piquiers arrêtés, qui baissent leurs piques quand l'ennemi approche.
    // Rien ne dit « cavalerie » dans la victoire : le cheval pèse 620 kg et renverse ce qu'il heurte
    // trop vite pour qu'on le suive d'un pas ; une pique baissée est un ressort planté en terre qui
    // plie, blesse ce qui s'y jette et se rompt.
    // On mesure où entrent les cavaliers par rapport au premier rang tel qu'il se tient (les hommes debout
    // qui ne fuient pas) : un front repoussé en bon ordre n'est pas un front traversé.
    // La charge brise un rang non préparé : les cavaliers entrent d'au moins 3 m dans le régiment,
    // qui rompt dans sept épreuves sur dix au moins. Elle se brise sur les piques : les chevaux ne
    // dépassent pas le premier rang, la cavalerie rompt dans sept épreuves sur dix au moins, perd plus
    // d'hommes qu'elle n'en tue, et les piquiers rompent au plus deux fois.
    // Avec -guerre-sans-masse, un cheval pèse et pousse comme un homme : le rang non préparé ne doit
    // plus être brisé. Avec -guerre-sans-piques, les piques n'arrêtent plus rien : la cavalerie ne
    // doit plus se briser.
    public sealed class EssaisCavalerie : MonoBehaviour
    {
        [Serializable] public class Epreuve
        {
            public string condition;
            public float penetration_max_m;              // où sont entrés les cavaliers les plus avancés, au-delà du premier rang
            public bool infanterie_rompue, cavalerie_rompue;
            public float infanterie_fuyards_max, cavalerie_fuyards_max, contact_apres_s = -1;
            // Diagnostic : l'allure des chevaux et la part des piques baissées au moment du choc.
            public float vitesse_au_contact, piques_baissees_au_contact, vitesse_max_de_la_charge;
            public float recul_du_front_max_m;           // de combien le premier rang debout a été repoussé
            public int morts_cavaliers, morts_fantassins;
        }
        [Serializable] public class Rapport
        {
            public string statut, date_utc; public bool sans_masse, sans_piques; public float secondes;
            // Le rang non préparé.
            public float penetration_non_prepare_m; public int ruptures_non_prepare, morts_cavaliers_non_prepare, morts_fantassins_non_prepare;
            // Les piques.
            public float penetration_piques_m; public int ruptures_cavalerie_piques, ruptures_piquiers, morts_cavaliers_piques, morts_piquiers;
            public int hommes_renverses, piques_rompues;
            public bool brise_le_rang_non_prepare, se_brise_sur_les_piques;
            public Epreuve[] epreuves; public string[] motifs;
        }

        static string sortie; static bool sansMasse, sansPiques;
        const int Couloirs = 20, Cavaliers = 80, FilesCavaliers = 20, Fantassins = 250;
        const float Duree = 75f, Charge = 150f, Ecart = 55f;
        // Ne pas dépasser le premier rang : entrer de moins d'un rang (1,1 m entre deux rangs au repos).
        const float PenetrationMin = 3f, PenetrationPiquesMax = 1.1f;
        const int RupturesMin = 7, RupturesPiquiersMax = 2;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Demarrer()
        {
            var args = Environment.GetCommandLineArgs();
            if (!args.Contains("-guerre-essai-cavalerie")) return;
            int i = Array.IndexOf(args, "-guerre-sortie");
            sortie = i >= 0 && i + 1 < args.Length ? args[i + 1] : Path.Combine(Application.persistentDataPath, "essai-cavalerie");
            sansMasse = args.Contains("-guerre-sans-masse");
            sansPiques = args.Contains("-guerre-sans-piques");
            var go = new GameObject("Essais de cavalerie"); DontDestroyOnLoad(go); go.AddComponent<EssaisCavalerie>();
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
            var rapport = new Rapport { date_utc = DateTime.UtcNow.ToString("o"), sans_masse = sansMasse, sans_piques = sansPiques };
            var motifs = new List<string>();
            if (bleus.Length < Couloirs || rouges.Length < Couloirs)
            {
                motifs.Add($"il faut {Couloirs} régiments par camp (-guerre-soldats 20000)");
                Finir(rapport, motifs); yield break;
            }
            var t = b.terrain.transform.position + b.terrain.terrainData.size * 0.5f;
            float2 centre = new float2(t.x, t.z), axe = new float2(1, 0);

            // Les régiments qui ne servent pas sont rangés loin, aux deux bouts de la vallée.
            for (int k = Couloirs; k < bleus.Length; k++) b.Deplacer(bleus[k], centre + new float2(-1000, (k - Couloirs - 10) * 40f), axe, 25);
            for (int k = Couloirs; k < rouges.Length; k++) b.Deplacer(rouges[k], centre + new float2(1000, (k - Couloirs - 10) * 40f), -axe, 25);

            // Deux rangées de dix couloirs ; les conditions alternent, et s'inversent d'une rangée à l'autre,
            // pour que le terrain ne favorise aucune d'elles.
            var couloirs = new List<(string condition, Entity cav, Entity inf, float2 lieu)>();
            for (int k = 0; k < Couloirs; k++)
            {
                int rangee = k / 10, j = k % 10;
                string condition = (j + rangee) % 2 == 0 ? "piques" : "non préparé";
                float2 lieu = centre + new float2(rangee == 0 ? -340f : 320f, (j - 4.5f) * Ecart);
                b.Armer(bleus[k], Corps.Cavalier);
                b.Reduire(bleus[k], Fantassins - Cavaliers);
                b.Armer(rouges[k], condition == "piques" ? 0 : 2);
                b.Deplacer(bleus[k], lieu - axe * Charge / 2, axe, FilesCavaliers);
                b.Deplacer(rouges[k], lieu + axe * Charge / 2, -axe, 25);
                var rg = em.GetComponentData<Regiment>(rouges[k]);
                rg.SansPavois = 1;
                em.SetComponentData(rouges[k], rg);
                couloirs.Add((condition, bleus[k], rouges[k], lieu));
            }
            for (int k = 0; k < 10; k++) yield return null;
            em.CompleteAllTrackedJobs();
            // La ligne de front de chaque régiment d'infanterie, au départ : les cavaliers la franchissent ou non.
            var fronts = couloirs.Select(c => { var r = em.GetComponentData<Regiment>(c.inf); return math.dot(r.Position, axe) - r.Profondeur / 2; }).ToArray();
            foreach (var c in couloirs) b.Attaquer(new[] { c.cav }, c.inf);
            var premier = couloirs.FindIndex(c => c.condition == "piques");
            var second = couloirs.FindIndex(c => c.condition == "non préparé");
            cmd.foyer = new Vector3(couloirs[premier].lieu.x + 50, 0, couloirs[premier].lieu.y); cmd.plongee = 26; cmd.distance = 75; cmd.cap = -60;
            Time.timeScale = 3;

            var res = couloirs.Select(c => new Epreuve { condition = c.condition, penetration_max_m = -1e3f }).ToArray();
            var soldats = em.CreateEntityQuery(typeof(Soldat), typeof(LocalTransform));
            float debut = Time.time, prochaine = 0;
            bool capturePiques = false, captureRang = false;
            while (Time.time - debut < Duree)
            {
                yield return null;
                if (Time.time < prochaine) continue;
                prochaine = Time.time + 0.5f;
                em.CompleteAllTrackedJobs();
                var positions = new List<float>[couloirs.Count];
                for (int k = 0; k < couloirs.Count; k++) positions[k] = new List<float>();
                var debout = new List<float>[couloirs.Count];
                for (int k = 0; k < couloirs.Count; k++) debout[k] = new List<float>();
                var contacts = new bool[couloirs.Count];
                var vitesses = new float[couloirs.Count]; var nv = new int[couloirs.Count];
                var baissees = new float[couloirs.Count]; var nb = new int[couloirs.Count];
                var infIndex = new Dictionary<Entity, int>();
                for (int k = 0; k < couloirs.Count; k++) infIndex[couloirs[k].inf] = k;
                var index = new Dictionary<Entity, int>();
                for (int k = 0; k < couloirs.Count; k++) index[couloirs[k].cav] = k;
                // Mémoire d'une image : rendue avant tout yield.
                using (var ss = soldats.ToComponentDataArray<Soldat>(Allocator.Temp))
                using (var tt = soldats.ToComponentDataArray<LocalTransform>(Allocator.Temp))
                    for (int i = 0; i < ss.Length; i++)
                    {
                        if (infIndex.TryGetValue(ss[i].Regiment, out int ki))
                        {
                            baissees[ki] += ss[i].Garde > 0.7f ? 1 : 0; nb[ki]++;
                            if (ss[i].Fuite == 0 && ss[i].AuSol <= 0) debout[ki].Add(math.dot(tt[i].Position.xz, axe) - fronts[ki]);
                            continue;
                        }
                        if (!index.TryGetValue(ss[i].Regiment, out int k)) continue;
                        if (ss[i].Contact != 0) contacts[k] = true;
                        if (ss[i].Fuite == 0) { vitesses[k] += math.length(ss[i].Vitesse); nv[k]++; }
                        if (ss[i].Fuite == 0) positions[k].Add(math.dot(tt[i].Position.xz, axe) - fronts[k]);
                    }
                for (int k = 0; k < couloirs.Count; k++)
                {
                    var r = res[k];
                    // Le premier rang tel qu'il se tient : le vingtième de tête des hommes debout qui ne fuient
                    // pas. Un front repoussé en bon ordre n'est pas un front traversé. S'il ne reste personne
                    // debout, on garde la ligne de départ.
                    float premierRang = 0f;
                    if (debout[k].Count > 0)
                    {
                        debout[k].Sort();
                        premierRang = debout[k][Mathf.Clamp((int)(debout[k].Count * 0.05f), 0, debout[k].Count - 1)];
                        r.recul_du_front_max_m = Mathf.Max(r.recul_du_front_max_m, premierRang);
                    }
                    // Les cavaliers les plus avancés : le dixième qui est allé le plus loin au-delà de ce rang.
                    if (positions[k].Count > 0)
                    {
                        positions[k].Sort();
                        r.penetration_max_m = Mathf.Max(r.penetration_max_m, positions[k][Mathf.Clamp((int)(positions[k].Count * 0.9f), 0, positions[k].Count - 1)] - premierRang);
                    }
                    if (r.contact_apres_s < 0 && nv[k] > 0) r.vitesse_max_de_la_charge = Mathf.Max(r.vitesse_max_de_la_charge, vitesses[k] / nv[k]);
                    if (r.contact_apres_s < 0) { r.vitesse_au_contact = nv[k] > 0 ? vitesses[k] / nv[k] : 0; r.piques_baissees_au_contact = nb[k] > 0 ? baissees[k] / nb[k] : 0; }
                    if (contacts[k] && r.contact_apres_s < 0) r.contact_apres_s = Time.time - debut;
                    var cav = em.GetComponentData<Regiment>(couloirs[k].cav);
                    var inf = em.GetComponentData<Regiment>(couloirs[k].inf);
                    r.cavalerie_fuyards_max = Mathf.Max(r.cavalerie_fuyards_max, cav.Fuyards);
                    r.infanterie_fuyards_max = Mathf.Max(r.infanterie_fuyards_max, inf.Fuyards);
                    r.cavalerie_rompue |= cav.Deroute != 0;
                    r.infanterie_rompue |= inf.Deroute != 0;
                    r.morts_cavaliers = Cavaliers - cav.Effectif;
                    r.morts_fantassins = Fantassins - inf.Effectif;
                }
                // Une vue du choc de chaque condition, deux secondes après le contact.
                if (!capturePiques && res[premier].contact_apres_s > 0 && Time.time - debut > res[premier].contact_apres_s + 2f)
                {
                    capturePiques = true;
                    yield return Capture("charge_sur_les_piques");
                    cmd.foyer = new Vector3(couloirs[second].lieu.x + 50, 0, couloirs[second].lieu.y);
                }
                if (capturePiques && !captureRang && res[second].contact_apres_s > 0 && Time.time - debut > res[second].contact_apres_s + 3f)
                {
                    captureRang = true;
                    yield return Capture("charge_sur_un_rang_non_prepare");
                }
            }
            Time.timeScale = 1;
            // Une vue de dessus de chaque condition, à la fin.
            cmd.foyer = new Vector3(couloirs[premier].lieu.x + 50, 0, couloirs[premier].lieu.y); cmd.plongee = 75; cmd.distance = 80; cmd.cap = 0;
            yield return Capture("fin_piques");
            cmd.foyer = new Vector3(couloirs[second].lieu.x + 50, 0, couloirs[second].lieu.y);
            yield return Capture("fin_non_prepare");

            rapport.secondes = Time.time - debut;
            rapport.epreuves = res;
            var np = res.Where(x => x.condition == "non préparé").ToArray();
            var pq = res.Where(x => x.condition == "piques").ToArray();
            rapport.penetration_non_prepare_m = np.Average(x => x.penetration_max_m);
            rapport.ruptures_non_prepare = np.Count(x => x.infanterie_rompue);
            rapport.morts_cavaliers_non_prepare = np.Sum(x => x.morts_cavaliers);
            rapport.morts_fantassins_non_prepare = np.Sum(x => x.morts_fantassins);
            rapport.penetration_piques_m = pq.Average(x => x.penetration_max_m);
            rapport.ruptures_cavalerie_piques = pq.Count(x => x.cavalerie_rompue);
            rapport.ruptures_piquiers = pq.Count(x => x.infanterie_rompue);
            rapport.morts_cavaliers_piques = pq.Sum(x => x.morts_cavaliers);
            rapport.morts_piquiers = pq.Sum(x => x.morts_fantassins);
            var compte = em.CreateEntityQuery(typeof(CompteTir)).GetSingleton<CompteTir>();
            rapport.hommes_renverses = compte.Renverses;
            rapport.piques_rompues = compte.PiquesRompues;

            if (b.soldats < 20000) motifs.Add($"l'essai demande 20 000 hommes (-guerre-soldats 20000), {b.soldats} levés");
            if (res.Any(x => x.contact_apres_s < 0)) motifs.Add($"{res.Count(x => x.contact_apres_s < 0)} charges n'ont pas touché l'ennemi");
            var brise = new List<string>();
            if (rapport.penetration_non_prepare_m < PenetrationMin) brise.Add($"rang non préparé : les cavaliers n'y entrent que de {rapport.penetration_non_prepare_m:0.0} m (au moins {PenetrationMin} m)");
            if (rapport.ruptures_non_prepare < RupturesMin) brise.Add($"rang non préparé : il ne rompt que {rapport.ruptures_non_prepare} fois sur 10 (au moins {RupturesMin})");
            var brisee = new List<string>();
            if (rapport.penetration_piques_m > PenetrationPiquesMax) brisee.Add($"piques : les cavaliers entrent de {rapport.penetration_piques_m:0.0} m au-delà du premier rang (moins d'un rang, {PenetrationPiquesMax} m, attendu)");
            if (rapport.ruptures_cavalerie_piques < RupturesMin) brisee.Add($"piques : la cavalerie ne rompt que {rapport.ruptures_cavalerie_piques} fois sur 10 (au moins {RupturesMin})");
            if (rapport.ruptures_piquiers > RupturesPiquiersMax) brisee.Add($"piques : les piquiers rompent {rapport.ruptures_piquiers} fois sur 10 (au plus {RupturesPiquiersMax})");
            if (rapport.morts_cavaliers_piques <= rapport.morts_piquiers) brisee.Add($"piques : la cavalerie perd {rapport.morts_cavaliers_piques} hommes et en tue {rapport.morts_piquiers}");
            rapport.brise_le_rang_non_prepare = brise.Count == 0;
            rapport.se_brise_sur_les_piques = brisee.Count == 0;
            motifs.AddRange(brise); motifs.AddRange(brisee);
            Finir(rapport, motifs);
        }

        void Finir(Rapport r, List<string> motifs)
        {
            r.motifs = motifs.ToArray();
            r.statut = motifs.Count == 0 ? "valide" : "echec";
            File.WriteAllText(Path.Combine(sortie, "essai-cavalerie.json"), JsonUtility.ToJson(r, true));
            Debug.Log("[EssaisCavalerie] " + r.statut + " " + string.Join(" | ", motifs));
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
