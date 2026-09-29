using System;
using System.Collections.Concurrent;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Debug = UnityEngine.Debug;

namespace ForgeLocal3D
{
    // La photo d'un lot, prise par la chaîne en batch sur le PC :
    //   Unity -batchmode -quit -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeCaptures <dossier>
    //         [-forgeSeed S] [-forgeTicks N] [-forgeCell C]
    // Avant le Play, on lance le service de `sim/` (graine S, poussé au tick N) : le panneau du lieu
    // montre alors les vrais chiffres. La scène du désert se construit à l'exécution (terrain, ville) :
    // on entre en Play, on laisse passer quelques images, on attend que le panneau ait lu le service,
    // on photographie la caméra de la scène, on écrit le texte du panneau, puis on rend la main.
    [InitializeOnLoad]
    public static class Capture
    {
        const string Flag = "Forge.Capture.Actif";
        const string Dossier = "Forge.Capture.Dossier";
        const string Scene = "Forge.Capture.Scene";
        const string Pid = "Forge.Capture.ServicePid";
        const int Attente = 90;

        const int GRAINE_PAR_DEFAUT = 0;
        const int TICKS_PAR_DEFAUT = 30; // les 30 jours de la carte du journal
        const int PORT_SERVICE = 8000; // celui de `PanneauLieu.DEFAULT_SERVICE_PORT` et de `jeu/sim/service.py`
        const string HOTE_SERVICE = "127.0.0.1";
        const int DELAI_SERVICE_PRET_S = 60;
        const int DELAI_TICKS_S = 300;
        const int DELAI_PANNEAU_S = 15;
        const int DELAI_INTERPRETEUR_MS = 30000;
        const int DELAI_CONNEXION_MS = 1000;
        const int DELAI_ARRET_MS = 5000;
        const int PAS_ATTENTE_MS = 100;
        const int LIGNES_STDERR_GARDEES = 20;
        const int CODE_REFUS = 2;
        const int CODE_PORT_PRIS = 3;
        const string PANNEAU = "Panneau du lieu";
        const string PANNEAU_EN_ATTENTE = "service absent : en attente";

        static int images, derniere = -1;
        static double debutPanneau = -1;

        static Capture()
        {
            EditorApplication.update += Tick;
            // Filet : un éditeur qui se ferme sans passer par Terminer n'abandonne pas le service.
            EditorApplication.quitting += ArreterService;
        }

        static string Argument(string nom)
        {
            var a = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(a, nom);
            return i >= 0 && i + 1 < a.Length ? a[i + 1] : null;
        }

        // Absent : le défaut. Présent : un entier ≥ 0, sinon une erreur qui nomme l'argument et la valeur.
        static int Entier(string nom, int defaut, out string erreur)
        {
            erreur = null;
            var a = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(a, nom);
            if (i < 0) return defaut;
            string valeur = i + 1 < a.Length ? a[i + 1] : null;
            if (valeur != null && int.TryParse(valeur, NumberStyles.AllowLeadingSign, CultureInfo.InvariantCulture, out int lu) && lu >= 0)
                return lu;
            erreur = "CAPTURE : " + nom + " attend un entier ≥ 0, reçu " + (valeur == null ? "rien" : "« " + valeur + " »");
            return -1;
        }

        public static void Photographier()
        {
            string dossier = Argument("-forgeCaptures") ?? Path.GetFullPath(Path.Combine(Application.dataPath, "../../../captures"));
            int graine = Entier("-forgeSeed", GRAINE_PAR_DEFAUT, out string erreurGraine);
            int ticks = Entier("-forgeTicks", TICKS_PAR_DEFAUT, out string erreurTicks);
            if (erreurGraine != null || erreurTicks != null)
            {
                Debug.LogError(erreurGraine ?? erreurTicks);
                Sortir(CODE_REFUS);
                return;
            }
            if (PortRepond())
            {
                Debug.LogError("CAPTURE : quelque chose répond déjà sur " + HOTE_SERVICE + ":" + PORT_SERVICE
                    + " : le panneau lirait un autre monde");
                Sortir(CODE_PORT_PRIS);
                return;
            }
            string scene = EditorBuildSettings.scenes.Where(s => s.enabled).Select(s => s.path).FirstOrDefault();
            if (scene == null)
            {
                Debug.LogError("CAPTURE : aucune scène au build");
                Sortir(CODE_REFUS);
                return;
            }
            Directory.CreateDirectory(dossier);
            SessionState.SetString(Dossier, dossier);
            SessionState.SetString(Scene, scene);
            LancerService(graine, ticks, dossier);
            SessionState.SetBool(Flag, true);
            images = 0;
            debutPanneau = -1;
            EditorSceneManager.OpenScene(scene, OpenSceneMode.Single);
            EditorApplication.EnterPlaymode();
        }

        static bool PortRepond()
        {
            using (var client = new TcpClient())
            {
                try { return client.ConnectAsync(HOTE_SERVICE, PORT_SERVICE).Wait(DELAI_CONNEXION_MS) && client.Connected; }
                catch (AggregateException) { return false; }
            }
        }

        // `py` est un lanceur : tuer lui ne tuerait pas forcément son enfant. On lance donc l'interpréteur lui-même.
        static string Interpreteur()
        {
            var info = new ProcessStartInfo("py", "-3 -c \"import sys;print(sys.executable)\"")
            {
                UseShellExecute = false, RedirectStandardOutput = true, CreateNoWindow = true
            };
            Process lanceur;
            try { lanceur = Process.Start(info); }
            catch (System.ComponentModel.Win32Exception e) { throw new InvalidOperationException("py introuvable (" + e.Message + ")"); }
            using (var py = lanceur)
            {
                string sortie = py.StandardOutput.ReadToEnd().Trim();
                if (!py.WaitForExit(DELAI_INTERPRETEUR_MS) || py.ExitCode != 0 || sortie.Length == 0)
                    throw new InvalidOperationException("py -3 n'a pas donné d'interpréteur (sortie « " + sortie + " »)");
                return sortie;
            }
        }

        // Toute cause d'échec se dit, le service est tué s'il vit, et la capture continue :
        // le panneau dira lui-même « service absent ».
        static void LancerService(int graine, int ticks, string dossier)
        {
            string attendue = "service prêt sur " + HOTE_SERVICE + ":" + PORT_SERVICE;
            var stderr = new ConcurrentQueue<string>();
            try
            {
                string python = Interpreteur();
                var info = new ProcessStartInfo(python, "-m sim.service --seed " + graine + " --port " + PORT_SERVICE + " --jours-par-seconde 0")
                {
                    WorkingDirectory = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "..", "jeu")),
                    UseShellExecute = false, CreateNoWindow = true,
                    RedirectStandardOutput = true, RedirectStandardError = true,
                    StandardOutputEncoding = Encoding.UTF8, StandardErrorEncoding = Encoding.UTF8
                };
                info.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
                var pret = new ManualResetEventSlim(false);
                var service = new Process { StartInfo = info };
                service.OutputDataReceived += (_, e) => { if (e.Data == attendue) pret.Set(); };
                service.ErrorDataReceived += (_, e) =>
                {
                    if (e.Data == null) return;
                    stderr.Enqueue(e.Data);
                    while (stderr.Count > LIGNES_STDERR_GARDEES) stderr.TryDequeue(out string _);
                };
                service.Start();
                // Avant toute autre chose : la ligne « prêt » est déjà dans le tube.
                service.BeginOutputReadLine();
                service.BeginErrorReadLine();
                // Le Play recharge le domaine : le pid survit dans SessionState, pas l'objet Process.
                SessionState.SetInt(Pid, service.Id);
                File.WriteAllText(Path.Combine(dossier, "service.pid"), service.Id.ToString(CultureInfo.InvariantCulture));
                var echeance = DateTime.UtcNow.AddSeconds(DELAI_SERVICE_PRET_S);
                while (!pret.Wait(PAS_ATTENTE_MS))
                {
                    if (service.HasExited)
                        throw new InvalidOperationException("le service s'est arrêté (code " + service.ExitCode + ") avant d'être prêt ; stderr : " + string.Join(" | ", stderr));
                    if (DateTime.UtcNow > echeance)
                        throw new TimeoutException("le service n'a pas dit « " + attendue + " » en " + DELAI_SERVICE_PRET_S + " s ; stderr : " + string.Join(" | ", stderr));
                }
                if (ticks >= 1)
                    PousserLesTicks(ticks);
                Debug.Log("CAPTURE_SERVICE graine " + graine + " tick " + ticks + " pid " + service.Id);
            }
            catch (Exception e)
            {
                Debug.LogError("CAPTURE : service absent : " + e.GetType().Name + " : " + e.GetBaseException().Message);
                ArreterService();
            }
        }

        // Hors du fil de l'éditeur : y appeler GetResult() sur HttpClient peut ne jamais revenir.
        static void PousserLesTicks(int ticks)
        {
            var resultat = System.Threading.Tasks.Task.Run(() =>
            {
                using (var http = new HttpClient { Timeout = TimeSpan.FromSeconds(DELAI_TICKS_S) })
                using (var corps = new StringContent(""))
                using (var reponse = http.PostAsync("http://" + HOTE_SERVICE + ":" + PORT_SERVICE + "/tick?n=" + ticks, corps).GetAwaiter().GetResult())
                    return ((int)reponse.StatusCode, reponse.Content.ReadAsStringAsync().GetAwaiter().GetResult());
            }).GetAwaiter().GetResult();
            if (resultat.Item1 != (int)HttpStatusCode.OK)
                throw new InvalidOperationException("POST /tick?n=" + ticks + " a rendu " + resultat.Item1 + " : " + resultat.Item2);
        }

        static void ArreterService()
        {
            int pid = SessionState.GetInt(Pid, -1);
            if (pid < 0) return;
            SessionState.EraseInt(Pid);
            try
            {
                using (var service = Process.GetProcessById(pid))
                {
                    // Un pid se recycle : on ne tue qu'un interpréteur Python.
                    if (service.HasExited || !service.ProcessName.StartsWith("python", StringComparison.OrdinalIgnoreCase)) return;
                    service.Kill();
                    service.WaitForExit(DELAI_ARRET_MS);
                }
                Debug.Log("CAPTURE_SERVICE arrêté pid " + pid);
            }
            catch (ArgumentException) { } // déjà mort
            catch (Exception e) { Debug.LogError("CAPTURE : le service (pid " + pid + ") n'a pas pu être arrêté : " + e.Message); }
        }

        static void Terminer(int code)
        {
            ArreterService();
            CitadelEditorBridge.Finish(code);
        }

        static void Sortir(int code)
        {
            ArreterService();
            EditorApplication.Exit(code);
        }

        // Le texte du panneau, lu par son objet racine (on ne référence pas Forge.Pont) ; null sans panneau.
        static UnityEngine.UI.Text TexteDuPanneau()
        {
            var panneau = GameObject.Find("/" + PANNEAU);
            return panneau != null ? panneau.GetComponentInChildren<UnityEngine.UI.Text>() : null;
        }

        static void Tick()
        {
            if (!SessionState.GetBool(Flag, false) || !Application.isPlaying || derniere == Time.frameCount) return;
            derniere = Time.frameCount;
            if (++images < Attente) return;
            var texte = TexteDuPanneau();
            if (texte != null && texte.text.StartsWith(PANNEAU_EN_ATTENTE, StringComparison.Ordinal))
            {
                double maintenant = Time.realtimeSinceStartupAsDouble;
                if (debutPanneau < 0) debutPanneau = maintenant;
                if (maintenant - debutPanneau < DELAI_PANNEAU_S) return;
                Debug.LogError("CAPTURE : le panneau attend encore le service après " + DELAI_PANNEAU_S + " s");
            }
            SessionState.SetBool(Flag, false);
            try
            {
                var env = UnityEngine.Object.FindFirstObjectByType<DesertEnvironment>();
                var camera = env != null && env.view != null ? env.view : (Camera.main ?? UnityEngine.Object.FindFirstObjectByType<Camera>());
                if (camera == null)
                {
                    Debug.LogError("CAPTURE : aucune caméra dans la scène");
                    Terminer(1);
                    return;
                }
                string nom = Path.GetFileNameWithoutExtension(SessionState.GetString(Scene, "scene"));
                string dossier = SessionState.GetString(Dossier, ".");
                string chemin = Path.Combine(dossier, nom + ".png");
                CitadelPlayCheck.Capture(camera, chemin, 1600, 900);
                Debug.Log("CAPTURE_OK " + chemin);
                if (texte != null)
                {
                    // Exactement ce que l'écran montre, sans BOM.
                    string panneau = Path.Combine(dossier, nom + ".panneau.txt");
                    File.WriteAllText(panneau, texte.text, new UTF8Encoding(false));
                    Debug.Log("CAPTURE_PANNEAU " + panneau);
                }
                else if (GameObject.Find("/" + PANNEAU) != null)
                    Debug.LogError("CAPTURE : le panneau du lieu n'a pas de texte");
                Terminer(0);
            }
            catch (Exception e)
            {
                Debug.LogError("CAPTURE : " + e);
                Terminer(1);
            }
        }
    }
}
