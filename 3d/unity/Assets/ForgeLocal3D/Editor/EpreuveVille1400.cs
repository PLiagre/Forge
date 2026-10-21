using System;
using System.Collections;
using System.IO;
using System.Linq;
using Forge.Pont;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;
using static System.FormattableString;

namespace ForgeLocal3D
{
    // Lot 739 : la session Unity de l'épreuve de la ville de 1400, moitié Unity du verdict `pc/epreuve_ville1400.py` (#412).
    // `Jouer` et `Relancer` (sur un service neuf) ouvrent quatre villes en Play et relèvent ce qui est posé sous la racine
    // des maisons, sans rien comparer. `-forgeSauter` / `-forgeAjouter` faussent le relevé. Codes : 0, 1 un défaut, 2 arguments.
    [InitializeOnLoad]
    public static class EpreuveVille1400
    {
        const string Flag = "Forge.Ville1400.Epreuve", CleDossier = Flag + ".Dossier", CleSession = Flag + ".Session", CleContre = Flag + ".Contre", CleSortie = Flag + ".Sortie";
        const string SCENE = "Assets/ForgeLocal3D/Desert/Scenes/Forge_Desert_Ville_ksar_des_sept_puits.unity";
        static readonly long[] CELLULES = { 10103, 1175, 1232, 10337 }; // Biskra, le ksar de l'éditeur, 493 maisons seules, 28 îlots
        const int AVANT = 10, IMAGES = 300;
        const double VIDANGE_S = 12; // comme EpreuveCapitale : sans service, Unity pend sinon à « Cleanup mono »
        static readonly System.Text.RegularExpressions.Regex NOM = new System.Text.RegularExpressions.Regex("^Maison ([0-9]{1,9}) indice ([0-9]{1,9})$");

        [Serializable] public class Rapport {
            public string session = "", contre_epreuve = "", absence = "", empreinte = "", empreinte_rues = "", defaut = "";
            public long cellule = -1, tick = -1; public int foyers = -1, posees = -1, rues_dessinees = -1, images = 0;
            public double duree_dessin_ms = -1, image_ms = -1; public string[] refus = new string[0], maisons = new string[0]; }

        static IEnumerator enCours; static Rapport[] rapports;
        static int faits, derniere = -1; static double vidange;
        static EpreuveVille1400() { EditorApplication.update += Tick; }
        public static void Jouer() => Lancer("jouer");
        public static void Relancer() => Lancer("relance");

        static void Lancer(string session)
        {
            string dossier = EpreuveChoix.Argument("-forgeEpreuve"); string[] a = Environment.GetCommandLineArgs();
            bool sauter = Array.IndexOf(a, "-forgeSauter") >= 0, ajouter = Array.IndexOf(a, "-forgeAjouter") >= 0;
            string erreur = string.IsNullOrEmpty(dossier) ? "-forgeEpreuve <dossier> manque" : sauter && ajouter ? "-forgeSauter et -forgeAjouter s'excluent" : null;
            if (erreur != null) { Debug.LogError("EPREUVE_VILLE1400 : " + erreur); EditorApplication.Exit(2); return; }
            string chemin = Path.GetFullPath(Path.Combine(EpreuveChoix.DossierDeLancement(), dossier));
            Directory.CreateDirectory(chemin); SessionState.SetString(CleDossier, chemin); SessionState.SetString(CleSession, session);
            SessionState.SetString(CleContre, sauter ? "sauter" : ajouter ? "ajouter" : "");
            UnityEditor.SceneManagement.EditorSceneManager.OpenScene(SCENE); SessionState.SetBool(Flag, true); EditorApplication.EnterPlaymode();
        }

        static void Tick()
        {
            int sortie = SessionState.GetInt(CleSortie, -1);
            bool sortir = sortie >= 0 && !EditorApplication.isPlayingOrWillChangePlaymode;
            if (sortir && vidange == 0) vidange = EditorApplication.timeSinceStartup + VIDANGE_S;
            if (sortir && EditorApplication.timeSinceStartup >= vidange) { SessionState.EraseInt(CleSortie); CitadelEditorBridge.Finish(sortie); }
            if (sortie >= 0 || !SessionState.GetBool(Flag, false) || !Application.isPlaying || derniere == Time.frameCount) return;
            derniere = Time.frameCount;
            string session = SessionState.GetString(CleSession, "");
            if (enCours == null) { rapports = CELLULES.Select(c => new Rapport { session = session, cellule = c }).ToArray(); faits = 0; enCours = Epreuve(SessionState.GetString(CleContre, "")); }
            try { if (enCours.MoveNext()) return; }
            catch (Exception e) // une session impossible le dit dans chaque cellule qu'elle n'a pas finie
            {
                Debug.LogException(e);
                for (int i = faits; i < rapports.Length; i++) if (rapports[i].defaut == "") rapports[i].defaut = e.GetBaseException().Message;
            }
            SessionState.SetBool(Flag, false); enCours = null;
            int code = rapports.All(r => r.defaut == "") ? 0 : 1;
            try { foreach (Rapport r in rapports) File.WriteAllText(Path.Combine(SessionState.GetString(CleDossier, ""), Invariant($"{session}-{r.cellule}.json")), JsonUtility.ToJson(r)); }
            catch (Exception e) { Debug.LogException(e); code = 1; }
            foreach (Rapport r in rapports)
                Debug.Log(Invariant($"EPREUVE_VILLE1400 {session} : {r.cellule} {r.posees}/{r.foyers}, {r.refus.Length} refus, {r.rues_dessinees} rue(s), dessin {r.duree_dessin_ms:F0} ms, {r.image_ms:F1} ms/image")
                    + (r.contre_epreuve == "" ? "" : ", contre-épreuve " + r.contre_epreuve) + (r.defaut == "" ? "" : " ; défaut : " + r.defaut));
            SessionState.SetInt(CleSortie, code); EditorApplication.ExitPlaymode();
        }

        static T Unique<T>(Scene s) where T : Component
        {
            T[] t = s.GetRootGameObjects().SelectMany(r => r.GetComponentsInChildren<T>(true)).ToArray();
            return t.Length == 1 ? t[0] : throw new InvalidOperationException($"la scène « {s.name} » porte {t.Length} {typeof(T).Name}, il en faut un");
        }
        static Mesh[] Maillages(GameObject o) => o.GetComponentsInChildren<MeshFilter>(true).Select(f => f.sharedMesh).ToArray();

        static IEnumerator Epreuve(string contre)
        {
            yield return null; yield return null;
            Scene scene = SceneManager.GetActiveScene();
            DesertRoadTool outil = Unique<DesertRoadTool>(scene); DesertCityCamera ville = Unique<DesertCityCamera>(scene);
            outil.automatique = ville.automatique = true; if (ville.Marcheur) ville.Marcheur.automatic = true;
            KitDesBatiments kit = KitDesBatiments.Charger() ?? throw new InvalidOperationException("pas de kit des bâtiments");
            Mesh[][] variantes = Enumerable.Range(0, 6).Select(v => kit.Maison(v) is PieceDuKit p && p.Presente ? Maillages(p.Prefab) : null).ToArray();
            for (; faits < rapports.Length; faits++)
            {
                Rapport r = rapports[faits]; var montre = System.Diagnostics.Stopwatch.StartNew();
                bool ouverte = outil.Ouvrir(r.cellule); r.duree_dessin_ms = montre.Elapsed.TotalMilliseconds;
                // Une ouverture refusée garde la ville précédente : rien n'est relevé, la cellule suivante est essayée.
                if (!ouverte) { r.defaut = Invariant($"ouverture de la cellule {r.cellule} : {outil.Message}"); continue; }
                Transform racine = outil.Maisons.Racine, premiere = racine.childCount > 0 ? racine.GetChild(0) : null;
                r.contre_epreuve = contre;
                if (contre != "" && premiere == null) r.defaut = $"contre-épreuve « {contre} » : la racine « {racine.name} » est vide";
                else if (contre == "sauter") UnityEngine.Object.DestroyImmediate(premiere.gameObject);
                else if (contre == "ajouter") { GameObject copie = UnityEngine.Object.Instantiate(premiere.gameObject, racine); copie.name = premiere.name; copie.transform.position = premiere.position + new Vector3(10f, 0f, 0f); }
                // Le relevé : ce qui est réellement sous la racine, dans l'ordre de ses enfants.
                var lignes = new System.Collections.Generic.List<string>(); float loin = 0f;
                foreach (Transform maison in racine)
                {
                    var m = NOM.Match(maison.name);
                    int rang = m.Success ? int.Parse(m.Groups[1].Value) : -1, indice = m.Success ? int.Parse(m.Groups[2].Value) : -1;
                    int variante = Array.FindIndex(variantes, v => v != null && v.SequenceEqual(Maillages(maison.gameObject)));
                    DesertMaisons1400.Boite(maison.gameObject, out Bounds b);
                    Vector3 centre = maison.TransformPoint(b.center);
                    float sol = maison.TransformPoint(new Vector3(b.center.x, b.min.y, b.center.z)).y, x = -centre.x, y = -centre.z;
                    loin = Mathf.Max(loin, Mathf.Sqrt(x * x + y * y));
                    lignes.Add(Invariant($"{rang} {indice} {variante} {x:F2} {y:F2} {sol:F2} {maison.eulerAngles.y:F2}"));
                }
                r.maisons = lignes.ToArray();
                using (var sha = System.Security.Cryptography.SHA256.Create())
                    r.empreinte = string.Concat(sha.ComputeHash(System.Text.Encoding.UTF8.GetBytes(string.Concat(lignes.Select(l => l + "\n")))).Select(o => o.ToString("x2")));
                r.tick = outil.TickOuverture; r.foyers = outil.Maisons.Foyers; r.posees = outil.Maisons.Posees; r.absence = outil.Maisons.Absence ?? "";
                r.refus = outil.Maisons.Refus.ToArray(); r.rues_dessinees = outil.Rues1400.Dessinees; r.empreinte_rues = outil.Rues1400.Empreinte;
                // Une mesure de la session, pas la preuve des 60 images par seconde (#422).
                ville.Poser(Vector3.zero, 40f, 68f, Mathf.Max(60f, 2f * loin)); outil.Placer();
                double somme = 0; for (int i = 0; i < AVANT; i++) yield return null;
                for (int i = 0; i < IMAGES; i++) { yield return null; somme += Time.unscaledDeltaTime; }
                r.images = IMAGES; r.image_ms = 1000.0 * somme / IMAGES;
            }
        }
    }
}
