// Mesure jetable du pont entre sim/ (Python) et Unity. Jouée en batch :
//   Unity -batchmode -nographics -projectPath ... -executeMethod MesurePont.Mesurer -quit
// Variables : MESURE_URL, MESURE_ENTREES (entrées du portage), MESURE_SORTIE.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Text;
using UnityEditor;
using UnityEngine;
using UnityEngine.Networking;

public static class MesurePont
{
    [Serializable] public class Constantes { public double prod, rdt_bas, rdt_haut, ration, rembourse, echelle_mort, mort_max, naissances, equinoxe, sensibilite, solstice, annee; }
    [Serializable] public class Cellule { public int id; public double aire, relief, agricole, ete, hiver, stock, dette; public int pop; }
    [Serializable] public class Entrees { public Constantes constantes; public Cellule[] cellules; }

    static readonly Dictionary<string, double> resultats = new Dictionary<string, double>();

    static void Noter(string nom, List<double> valeurs)
    {
        valeurs.Sort();
        resultats[nom + "_mediane"] = Math.Round(valeurs[valeurs.Count / 2], 3);
        resultats[nom + "_p95"] = Math.Round(valeurs[(int)(valeurs.Count * 0.95) - 1], 3);
    }

    public static void Mesurer()
    {
        string url = Environment.GetEnvironmentVariable("MESURE_URL") ?? "http://127.0.0.1:8765";
        string sortie = Environment.GetEnvironmentVariable("MESURE_SORTIE");
        var entrees = JsonUtility.FromJson<Entrees>(File.ReadAllText(Environment.GetEnvironmentVariable("MESURE_ENTREES")));
        int cid = entrees.cellules[0].id;
        try
        {
            using (var http = new HttpClient())
            {
                for (int i = 0; i < 20; i++) http.GetStringAsync($"{url}/lieu?cell={cid}").Result.ToString();
                // 1. lire un lieu, HttpClient (connexion gardée)
                var d = new List<double>();
                for (int i = 0; i < 500; i++)
                {
                    var sw = Stopwatch.StartNew();
                    string corps = http.GetStringAsync($"{url}/lieu?cell={cid}").Result;
                    JsonUtility.FromJson<Cellule>(corps);
                    d.Add(sw.Elapsed.TotalMilliseconds);
                }
                Noter("httpclient_lieu_ms", d);
                // 2. déposer une intention
                d = new List<double>();
                for (int i = 0; i < 100; i++)
                {
                    var sw = Stopwatch.StartNew();
                    var contenu = new StringContent("{\"type\":\"route\",\"cell\":" + cid + ",\"points\":[[0,0],[10,5],[25,9]]}", Encoding.UTF8, "application/json");
                    http.PostAsync($"{url}/intention", contenu).Result.Content.ReadAsStringAsync().Wait();
                    d.Add(sw.Elapsed.TotalMilliseconds);
                }
                Noter("httpclient_intention_ms", d);
                // 3. demander un tick du monde entier, aller-retour compris
                d = new List<double>();
                for (int i = 0; i < 20; i++)
                {
                    var sw = Stopwatch.StartNew();
                    http.PostAsync($"{url}/tick?n=1", new StringContent("")).Result.Content.ReadAsStringAsync().Wait();
                    d.Add(sw.Elapsed.TotalMilliseconds);
                }
                Noter("httpclient_tick_aller_retour_ms", d);
                // 4. l'état léger du monde entier (596 cellules)
                d = new List<double>();
                int octets = 0;
                for (int i = 0; i < 20; i++)
                {
                    var sw = Stopwatch.StartNew();
                    octets = http.GetByteArrayAsync($"{url}/monde").Result.Length;
                    d.Add(sw.Elapsed.TotalMilliseconds);
                }
                Noter("httpclient_monde_ms", d);
                resultats["monde_octets"] = octets;
            }
            // 5. lire un lieu avec UnityWebRequest (le client natif d'Unity)
            var u = new List<double>();
            for (int i = 0; i < 200; i++)
            {
                var sw = Stopwatch.StartNew();
                using (var req = UnityWebRequest.Get($"{url}/lieu?cell={cid}"))
                {
                    var op = req.SendWebRequest();
                    while (!op.isDone) { }
                    JsonUtility.FromJson<Cellule>(req.downloadHandler.text);
                }
                u.Add(sw.Elapsed.TotalMilliseconds);
            }
            Noter("unitywebrequest_lieu_ms", u);
        }
        catch (Exception e)
        {
            resultats["erreur_http"] = 1;
            UnityEngine.Debug.LogError("HTTP : " + e);
        }

        // 6. le sous-ensemble par cellule, porté en C# (runtime d'Unity)
        Noter("csharp_mono_sous_ensemble_ms", SousEnsemble(entrees, 200));

        var sb = new StringBuilder("{\n");
        sb.Append(string.Join(",\n", resultats.Select(kv => $"  \"{kv.Key}\": {kv.Value.ToString(System.Globalization.CultureInfo.InvariantCulture)}")));
        sb.Append("\n}\n");
        File.WriteAllText(sortie, sb.ToString());
        UnityEngine.Debug.Log("mesure écrite : " + sortie);
    }

    // Production, consommation, faim, mort, naissances : la même arithmétique
    // que sim/engine.py, écrite comme un portage C# l'écrirait (facteurs lus
    // une fois, tableaux plutôt que dictionnaires).
    public static List<double> SousEnsemble(Entrees e, int iterations)
    {
        var k = e.constantes;
        int n = e.cellules.Length;
        var pop = new int[n]; var stock = new double[n]; var dette = new double[n]; var faim = new int[n];
        var resteMort = new double[n]; var resteNaiss = new double[n];
        for (int i = 0; i < n; i++) { pop[i] = e.cellules[i].pop; stock[i] = e.cellules[i].stock; dette[i] = e.cellules[i].dette; }
        var rng = new System.Random(0);
        var durees = new List<double>();
        for (int it = 0; it < iterations; it++)
        {
            int jour = it % (int)k.annee;
            var sw = Stopwatch.StartNew();
            for (int i = 0; i < n; i++)
            {
                var c = e.cellules[i];
                double rendement = k.rdt_bas + rng.NextDouble() * (k.rdt_haut - k.rdt_bas);
                double moyenne = (c.ete + c.hiver) / 2, amplitude = (c.ete - c.hiver) / 2;
                double duree = moyenne + amplitude * Math.Cos(2 * Math.PI * (jour - k.solstice) / k.annee);
                double saison = Math.Max(0, 1 + k.sensibilite * (duree - k.equinoxe) / k.equinoxe);
                stock[i] += c.aire * k.prod * rendement * c.relief * c.agricole * saison;
                double besoin = pop[i] * k.ration, reste = stock[i] - besoin, penurie = 0;
                if (reste >= 0)
                {
                    double remb = Math.Min(dette[i], Math.Max(0, reste) * Math.Min(1, k.rembourse));
                    dette[i] -= remb; stock[i] = reste - remb;
                }
                else { penurie = -reste; dette[i] += penurie; stock[i] = 0; }
                faim[i] = penurie > 0 ? faim[i] + 1 : 0;
                if (dette[i] > 0 && pop[i] > 0)
                {
                    double taux = Math.Min(dette[i] / pop[i] * k.echelle_mort, k.mort_max);
                    double brut = pop[i] * taux + resteMort[i]; int morts = (int)brut;
                    resteMort[i] = brut - morts; pop[i] = Math.Max(0, pop[i] - morts);
                }
                if (penurie == 0 && dette[i] == 0 && pop[i] > 0)
                {
                    double brut = pop[i] * k.naissances + resteNaiss[i]; int nes = (int)brut;
                    resteNaiss[i] = brut - nes; pop[i] += nes;
                }
            }
            durees.Add(sw.Elapsed.TotalMilliseconds);
        }
        return durees;
    }
}
