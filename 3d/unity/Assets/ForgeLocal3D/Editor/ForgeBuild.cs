using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace ForgeLocal3D
{
    // Le build Windows de la nuit (.github/workflows/build-nuit.yml) :
    //   Unity -batchmode -quit -projectPath 3d/unity -executeMethod ForgeLocal3D.Build.Nuit -forgeSortie <dossier>
    // Les scènes sont celles de la liste du build, dans son ordre : la première s'ouvre au lancement. La planche carte et atlas se
    // range à côté du lanceur (`RangerLaPlanche`).
    public static class Build
    {
        static string Argument(string nom)
        {
            var a = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(a, nom);
            return i >= 0 && i + 1 < a.Length ? a[i + 1] : null;
        }

        public static void Nuit()
        {
            string sortie = Argument("-forgeSortie") ?? Path.GetFullPath(Path.Combine(Application.dataPath, "../../../builds/manuel"));
            var scenes = EditorBuildSettings.scenes.Where(s => s.enabled).Select(s => s.path).ToArray();
            if (scenes.Length == 0)
            {
                Debug.LogError("BUILD : aucune scène au build");
                EditorApplication.Exit(2);
                return;
            }
            Directory.CreateDirectory(sortie);
            var rapport = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = scenes,
                locationPathName = Path.Combine(sortie, "Forge.exe"),
                target = BuildTarget.StandaloneWindows64,
                options = BuildOptions.None,
            });
            var s = rapport.summary;
            Debug.Log($"BUILD : {s.result}, {s.totalErrors} erreur(s), {s.totalSize / (1024 * 1024)} Mo, {s.totalTime}");
            if (s.result != BuildResult.Succeeded) { EditorApplication.Exit(1); return; }
            string manque = CopierLaVille(Path.Combine(sortie, "Forge_Data", "StreamingAssets"));
            if (manque != null) { Debug.LogError("BUILD : " + manque); EditorApplication.Exit(1); return; }
            // La planche manque ou se périme sans faire échouer le build : le jeu se joue sans elle, et le LISEZMOI le dit.
            try { Debug.Log("BUILD : planche " + RangerLaPlanche(sortie)); }
            catch (Exception e) { Debug.LogWarning("BUILD : planche non rangée : " + e.GetType().Name + " : " + e.Message); }
            EditorApplication.Exit(0);
        }

        public const string PLANCHE = "Planche carte et atlas";
        static readonly byte[] SIGNATURE_PNG = { 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A };

        // La planche carte et atlas, rangée dans le dépôt (`atlas-1400/planche-du-jeu`), copiée dans `<sortie>/Planche carte et atlas/`
        // avec un LISEZMOI. Le build ne la refait pas : il tourne sous -batchmode -quit, sans mode Play, et le build figé part d'un
        // worktree propre où aucune capture n'a tourné. Il vérifie qu'elle est encore la photo du monde qu'il sert : chaque image est un
        // PNG (pas un pointeur LFS), chaque cadre de `planche.json` a la sienne, et le service relancé comme la fiche le dit (graine, jours
        // poussés, IA) rend les mêmes terres (`ScenarioCarteEtAtlas.Empreinte`). Rend l'état dit : « à jour », « périmée », « absente »,
        // « incomplète » ou « non vérifiée », avec sa raison. Le service lancé est toujours arrêté.
        public static string RangerLaPlanche(string sortie)
        {
            string source = Path.Combine(Captures.ScenarioCarteEtAtlas.DossierDeLAtlas, Captures.ScenarioCarteEtAtlas.DOSSIER_RANGE), cible = Path.Combine(sortie, PLANCHE);
            if (Directory.Exists(cible)) Directory.Delete(cible, true);
            Directory.CreateDirectory(cible);
            string fiche = Path.Combine(source, Captures.ScenarioCarteEtAtlas.FICHE_RANGEE);
            Captures.ScenarioCarteEtAtlas.PlancheRangee monde = File.Exists(fiche) ? JsonUtility.FromJson<Captures.ScenarioCarteEtAtlas.PlancheRangee>(File.ReadAllText(fiche)) : null;
            string etat;
            if (monde?.cadres == null || monde.cadres.Length == 0 || string.IsNullOrEmpty(monde.empreinte)) etat = "absente : pas de " + fiche + " lisible";
            else
            {
                var pointeurs = new System.Collections.Generic.List<string>(); var manquants = new System.Collections.Generic.List<string>();
                foreach (var rangee in monde.cadres)
                {
                    string image = Path.Combine(source, rangee.cadre + ".png");
                    if (!File.Exists(image)) { manquants.Add(rangee.cadre); continue; }
                    byte[] debut = new byte[SIGNATURE_PNG.Length];
                    using (var lu = File.OpenRead(image)) if (lu.Read(debut, 0, debut.Length) != debut.Length || !debut.SequenceEqual(SIGNATURE_PNG)) { pointeurs.Add(rangee.cadre); continue; }
                    File.Copy(image, Path.Combine(cible, rangee.cadre + ".png"), true);
                }
                File.Copy(fiche, Path.Combine(cible, Captures.ScenarioCarteEtAtlas.FICHE_RANGEE), true);
                if (manquants.Count + pointeurs.Count > 0)
                    etat = "incomplète :" + (manquants.Count > 0 ? " images absentes (" + string.Join(", ", manquants) + ")" : "") + (pointeurs.Count > 0 ? " fichiers qui ne sont pas des PNG, sans doute des pointeurs LFS (" + string.Join(", ", pointeurs) + ")" : "");
                else etat = Verifier(monde);
            }
            File.WriteAllText(Path.Combine(cible, "LISEZMOI.txt"), Lisezmoi(monde, etat), new System.Text.UTF8Encoding(true));
            return etat + " ; " + cible;
        }

        // Le service relancé comme la fiche le dit, ses terres relues, l'empreinte comparée.
        static string Verifier(Captures.ScenarioCarteEtAtlas.PlancheRangee monde)
        {
            if (Capture.PortDuServicePris) return "non vérifiée : quelque chose répond déjà sur le port du service, qui servirait un autre monde";
            string temp = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "Temp"));
            Directory.CreateDirectory(temp);
            try
            {
                if (!Capture.LancerLeService(monde.graine, monde.jours, monde.ia, temp)) return "non vérifiée : le service du monde ne démarre pas (voir « CAPTURE : service absent » au journal)";
                var lues = System.Threading.Tasks.Task.Run(() => { using (var c = new Forge.Pont.ClientGuerre(Forge.Pont.PanneauLieu.DEFAULT_SERVICE_PORT, TimeSpan.FromSeconds(60))) return c.LireTerres(); }).GetAwaiter().GetResult();
                if (!lues.Presente) return "non vérifiée : les terres ne se lisent pas (" + lues.Absence + ")";
                string empreinte = Captures.ScenarioCarteEtAtlas.Empreinte(lues.Donnees);
                return empreinte == monde.empreinte ? "à jour : le monde que ce build sert donne les mêmes terres au même jour (empreinte " + empreinte.Substring(0, 12) + ")"
                    : "périmée : le monde que ce build sert ne donne plus les mêmes terres au même jour (empreinte " + empreinte.Substring(0, 12) + ", la planche a " + monde.empreinte.Substring(0, Math.Min(12, monde.empreinte.Length)) + ")";
            }
            finally { Capture.ArreterLeService(); }
        }

        static string Lisezmoi(Captures.ScenarioCarteEtAtlas.PlancheRangee monde, string etat)
        {
            string atlas = Path.Combine(Captures.ScenarioCarteEtAtlas.DossierDeLAtlas, "SOURCES.md");
            return "Planche carte et atlas\r\n\r\n"
                + "La carte politique du jeu posée à côté d'un atlas historique, cadre par cadre : "
                + (monde?.cadres == null ? "aucune image" : string.Join(", ", monde.cadres.Select(r => r.cadre + ".png"))) + ".\r\n\r\n"
                + "L'atlas : W. R. Shepherd, Historical Atlas (1926), « Europe about 1360 », domaine public. Il montre l'Europe vers 1360, "
                + "quarante ans avant le jeu, faute d'un atlas de 1400 libre de droits : les Ottomans n'y tiennent pas encore les Balkans, la Serbie et la Bulgarie "
                + "y sont libres, l'Union de Kalmar et la Bourgogne de Flandre n'existent pas encore.\r\n\r\n"
                + (monde == null ? "" : "Le monde de la planche : graine " + monde.graine + ", " + monde.jours + " jours poussés, " + (monde.ia ? "avec" : "sans") + " l'IA, au " + monde.date + ".\r\n\r\n")
                + "État : " + etat + ".\r\n\r\n"
                + "Europa Universalis IV : sa carte appartient à Paradox et n'entre ni dans le dépôt ni dans cette planche. Pour la poser à côté, "
                + "déposer ses captures dans D:\\Forge\\references\\eu4\\ (europe.png, france-et-iles.png, empire.png, italie.png, balkans-et-orient.png) "
                + "et refaire la planche : la planche complète s'écrit alors dans D:\\Forge\\references\\eu4\\planches\\.\r\n\r\n"
                + "Refaire la planche : la capture -forgeScenario etape-1-d-un-trait -forgeServiceIa -forgeRangerLaPlanche, comme le dit "
                + "docs/interface/references/atlas-1400/SOURCES.md" + (File.Exists(atlas) ? "" : " (absent de ce checkout)") + ".\r\n";
        }

        // Les gestes.json de chaque implantation du désert, que la ville lit au lancement (`DesertRoads.CheminGestes`),
        // copiés sous StreamingAssets du jeu construit : il les lit près de lui, d'où qu'on le lance. Rend la cause d'un
        // manque, ou null.
        public static string CopierLaVille(string streamingAssets)
        {
            string source = Path.GetFullPath(Path.Combine(Application.dataPath, "..", DesertRoads.Sorties));
            if (!Directory.Exists(source)) return "sorties de la ville absentes : " + source;
            int copies = 0;
            foreach (string dossier in Directory.GetDirectories(source).OrderBy(d => d, StringComparer.Ordinal))
            {
                string gestes = Path.Combine(dossier, "routes", "gestes.json");
                if (!File.Exists(gestes)) continue;
                string cible = Path.Combine(streamingAssets, DesertRoads.DossierDuBuild, Path.GetFileName(dossier), "routes", "gestes.json");
                Directory.CreateDirectory(Path.GetDirectoryName(cible));
                File.Copy(gestes, cible, true);
                copies++;
                Debug.Log("BUILD : ville copiée, " + cible);
            }
            return copies == 0 ? "aucun gestes.json sous " + source : null;
        }
    }
}
