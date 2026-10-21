using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using Forge.Pont;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace ForgeLocal3D
{
    // Lot 739 : la session Unity de l'épreuve de la ville de 1400, moitié Unity du verdict `pc/epreuve_ville1400.py` (#412).
    //   Unity -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.EpreuveVille1400.Jouer
    //         -forgeEpreuve <dossier> [-forgeSauter | -forgeAjouter] [-logFile <journal>]
    // `Relancer` fait de même, sur un service neuf de même graine : seuls le champ `session` et le nom des fichiers changent.
    // La session ouvre quatre villes dans la scène du désert en Play, comme le joueur, et relève maison par maison ce que
    // `DesertMaisons1400` a posé sous sa racine. Elle ne compare rien : le verdict est celui de `pc/epreuve_ville1400.py`.
    // `-forgeSauter` détruit la première maison posée, `-forgeAjouter` la double à +10 m : le verdict doit alors rougir.
    // Codes : 0 aucun défaut ; 1 un défaut dans au moins un rapport ; 2 arguments fautifs (aucun rapport).
    [InitializeOnLoad]
    public static class EpreuveVille1400
    {
        const string Flag = "Forge.Ville1400.Epreuve", CleDossier = "Forge.Ville1400.Epreuve.Dossier", CleSession = "Forge.Ville1400.Epreuve.Session";
        const string CleContre = "Forge.Ville1400.Epreuve.Contre", CleSortie = "Forge.Ville1400.Epreuve.Sortie";
        const string ARGUMENT_DOSSIER = "-forgeEpreuve", ARGUMENT_SAUTER = "-forgeSauter", ARGUMENT_AJOUTER = "-forgeAjouter";
        const string SCENE = "Assets/ForgeLocal3D/Desert/Scenes/Forge_Desert_Ville_ksar_des_sept_puits.unity";
        // Biskra, le ksar de l'éditeur, 493 maisons seules, 28 îlots : toujours dans cet ordre.
        static readonly long[] CELLULES = { 10103, 1175, 1232, 10337 };
        const int AVANT = 10, IMAGES = 300;
        const double VIDANGE_S = 12; // comme EpreuveCapitale : sans service, Unity pend sinon à « Cleanup mono »
        static readonly Regex NOM = new Regex(@"^Maison (\d+) indice (\d+)$");

        [Serializable] public class Rapport {
            public string session = "", contre_epreuve = "", absence = "", empreinte = "", empreinte_rues = "", defaut = "";
            public long cellule = -1, tick = -1;
            public int foyers = -1, posees = -1, rues_dessinees = -1, images = 0;
            public double duree_dessin_ms = -1, image_ms = -1;
            public string[] refus = new string[0], maisons = new string[0];
        }

        static IEnumerator enCours;
        static Rapport[] rapports;
        static int faits, derniere = -1;
        static double vidange;

        static EpreuveVille1400() { EditorApplication.update += Tick; }

        public static void Jouer() => Lancer("jouer");
        public static void Relancer() => Lancer("relance");

        static void Lancer(string session)
        {
            string dossier = EpreuveChoix.Argument(ARGUMENT_DOSSIER);
            string[] a = Environment.GetCommandLineArgs();
            bool sauter = Array.IndexOf(a, ARGUMENT_SAUTER) >= 0, ajouter = Array.IndexOf(a, ARGUMENT_AJOUTER) >= 0;
            if (string.IsNullOrEmpty(dossier)) { Debug.LogError("EPREUVE_VILLE1400 : " + ARGUMENT_DOSSIER + " <dossier> manque"); EditorApplication.Exit(2); return; }
            if (sauter && ajouter) { Debug.LogError("EPREUVE_VILLE1400 : " + ARGUMENT_SAUTER + " et " + ARGUMENT_AJOUTER + " s'excluent"); EditorApplication.Exit(2); return; }
            string chemin = Path.GetFullPath(Path.Combine(EpreuveChoix.DossierDeLancement(), dossier));
            Directory.CreateDirectory(chemin);
            SessionState.SetString(CleDossier, chemin);
            SessionState.SetString(CleSession, session);
            SessionState.SetString(CleContre, sauter ? "sauter" : ajouter ? "ajouter" : "");
            EditorSceneManager.OpenScene(SCENE);
            SessionState.SetBool(Flag, true);
            EditorApplication.EnterPlaymode();
        }

        static void Tick()
        {
            int sortie = SessionState.GetInt(CleSortie, -1);
            if (sortie >= 0 && !EditorApplication.isPlayingOrWillChangePlaymode)
            {
                if (vidange == 0) vidange = EditorApplication.timeSinceStartup + VIDANGE_S;
                if (EditorApplication.timeSinceStartup < vidange) return;
                SessionState.EraseInt(CleSortie); CitadelEditorBridge.Finish(sortie); return;
            }
            if (!SessionState.GetBool(Flag, false) || !Application.isPlaying || derniere == Time.frameCount) return;
            derniere = Time.frameCount;
            string session = SessionState.GetString(CleSession, ""), contre = SessionState.GetString(CleContre, "");
            if (enCours == null)
            {
                rapports = CELLULES.Select(c => new Rapport { session = session, cellule = c }).ToArray(); faits = 0;
                enCours = Epreuve(contre);
            }
            try { if (enCours.MoveNext()) return; }
            catch (Exception e)
            {
                // Une session impossible le dit dans chaque cellule qu'elle n'a pas finie.
                Debug.LogException(e);
                for (int i = faits; i < rapports.Length; i++) if (rapports[i].defaut == "") rapports[i].defaut = e.GetBaseException().Message;
            }
            SessionState.SetBool(Flag, false); enCours = null;
            int code = rapports.All(r => r.defaut == "") ? 0 : 1;
            string dossier = SessionState.GetString(CleDossier, "");
            try
            {
                foreach (Rapport r in rapports) File.WriteAllText(Path.Combine(dossier, session + "-" + N(r.cellule) + ".json"), JsonUtility.ToJson(r));
                foreach (Rapport r in rapports)
                    Debug.Log("EPREUVE_VILLE1400 " + session + " : " + N(r.cellule) + " " + r.posees.ToString(CultureInfo.InvariantCulture) + "/" + r.foyers.ToString(CultureInfo.InvariantCulture)
                        + ", " + r.refus.Length.ToString(CultureInfo.InvariantCulture) + " refus, " + r.rues_dessinees.ToString(CultureInfo.InvariantCulture) + " rue(s), dessin "
                        + r.duree_dessin_ms.ToString("F0", CultureInfo.InvariantCulture) + " ms, " + r.image_ms.ToString("F1", CultureInfo.InvariantCulture) + " ms/image"
                        + (r.contre_epreuve == "" ? "" : ", contre-épreuve " + r.contre_epreuve) + (r.defaut == "" ? "" : " ; défaut : " + r.defaut));
            }
            catch (Exception e) { Debug.LogException(e); code = 1; }
            SessionState.SetInt(CleSortie, code); EditorApplication.ExitPlaymode();
        }

        static string N(long v) => v.ToString(CultureInfo.InvariantCulture);
        static string F(float v) => v.ToString("F2", CultureInfo.InvariantCulture);

        static T Unique<T>(Scene scene) where T : Component
        {
            T[] tous = scene.GetRootGameObjects().SelectMany(r => r.GetComponentsInChildren<T>(true)).ToArray();
            if (tous.Length != 1) throw new InvalidOperationException("la scène « " + scene.name + " » porte " + tous.Length + " " + typeof(T).Name + ", il en faut un");
            return tous[0];
        }

        static IEnumerator Epreuve(string contre)
        {
            for (int i = 0; i < 2; i++) yield return null;
            Scene scene = SceneManager.GetActiveScene();
            DesertRoadTool outil = Unique<DesertRoadTool>(scene); DesertCityCamera ville = Unique<DesertCityCamera>(scene);
            outil.automatique = ville.automatique = true; if (ville.Marcheur) ville.Marcheur.automatic = true;
            KitDesBatiments kit = KitDesBatiments.Charger() ?? throw new InvalidOperationException("pas de kit des bâtiments");
            Mesh[][] variantes = Enumerable.Range(0, 6).Select(v => kit.Maison(v) is PieceDuKit p && p.Presente
                ? p.Prefab.GetComponentsInChildren<MeshFilter>(true).Select(f => f.sharedMesh).ToArray() : null).ToArray();

            for (; faits < rapports.Length; faits++)
            {
                Rapport r = rapports[faits];
                var montre = System.Diagnostics.Stopwatch.StartNew();
                bool ouverte = outil.Ouvrir(r.cellule);
                r.duree_dessin_ms = montre.Elapsed.TotalMilliseconds;
                // Une ouverture refusée garde la ville précédente : rien n'est relevé, la cellule suivante est essayée.
                if (!ouverte) { r.defaut = "ouverture de la cellule " + N(r.cellule) + " : " + outil.Message; continue; }

                Transform racine = outil.Maisons.Racine;
                r.contre_epreuve = contre;
                if (contre != "" && racine.childCount == 0) r.defaut = "contre-épreuve « " + contre + " » : la racine « " + racine.name + " » est vide";
                else if (contre == "sauter") Object.DestroyImmediate(racine.GetChild(0).gameObject);
                else if (contre == "ajouter")
                {
                    Transform premiere = racine.GetChild(0);
                    GameObject copie = Object.Instantiate(premiere.gameObject, racine);
                    copie.name = premiere.name; copie.transform.position = premiere.position + new Vector3(10f, 0f, 0f);
                }

                var lignes = new List<string>(); float loin = 0f;
                foreach (Transform maison in racine)
                {
                    Match m = NOM.Match(maison.name);
                    int rang = m.Success && int.TryParse(m.Groups[1].Value, NumberStyles.None, CultureInfo.InvariantCulture, out int a) ? a : -1;
                    int indice = rang >= 0 && int.TryParse(m.Groups[2].Value, NumberStyles.None, CultureInfo.InvariantCulture, out int b) ? b : -1;
                    if (indice < 0) rang = -1;
                    Mesh[] maillages = maison.GetComponentsInChildren<MeshFilter>(true).Select(f => f.sharedMesh).ToArray();
                    int variante = Array.FindIndex(variantes, v => v != null && v.SequenceEqual(maillages));
                    DesertMaisons1400.Boite(maison.gameObject, out Bounds boite);
                    Vector3 centre = maison.TransformPoint(boite.center);
                    float sol = maison.TransformPoint(new Vector3(boite.center.x, boite.min.y, boite.center.z)).y;
                    float x = -centre.x, y = -centre.z; loin = Mathf.Max(loin, Mathf.Sqrt(x * x + y * y));
                    lignes.Add(rang.ToString(CultureInfo.InvariantCulture) + " " + indice.ToString(CultureInfo.InvariantCulture) + " " + variante.ToString(CultureInfo.InvariantCulture)
                        + " " + F(x) + " " + F(y) + " " + F(sol) + " " + F(maison.eulerAngles.y));
                }
                r.maisons = lignes.ToArray();
                using (var sha = SHA256.Create())
                    r.empreinte = string.Concat(sha.ComputeHash(Encoding.UTF8.GetBytes(string.Concat(lignes.Select(l => l + "\n")))).Select(o => o.ToString("x2")));
                r.tick = outil.TickOuverture; r.foyers = outil.Maisons.Foyers; r.posees = outil.Maisons.Posees;
                r.absence = outil.Maisons.Absence ?? ""; r.refus = outil.Maisons.Refus.ToArray();
                r.rues_dessinees = outil.Rues1400.Dessinees; r.empreinte_rues = outil.Rues1400.Empreinte;

                // Une mesure de la session, pas la preuve des 60 images par seconde (#422).
                ville.Poser(Vector3.zero, 40f, 68f, Mathf.Max(60f, 2f * loin)); outil.Placer();
                for (int i = 0; i < AVANT; i++) yield return null;
                double somme = 0;
                for (int i = 0; i < IMAGES; i++) { yield return null; somme += Time.unscaledDeltaTime; }
                r.images = IMAGES; r.image_ms = 1000.0 * somme / IMAGES;
            }
        }
    }
}
