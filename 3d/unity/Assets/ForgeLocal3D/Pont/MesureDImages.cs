using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using Unity.Profiling;
using UnityEngine;

namespace Forge.Pont {
    // Ce qu'une suite d'images a coûté : leur nombre, les images par seconde en moyenne, et le temps d'une image, en
    // ms — au milieu, au 99e centile et au pire. Sans image, tout est à -1 : « non mesuré ».
    public readonly struct ReleveDImages {
        public int Images { get; } public double ImagesParSeconde { get; } public double MedianeMs { get; } public double CentileMs { get; } public double PireMs { get; }
        public ReleveDImages(int images, double imagesParSeconde, double medianeMs, double centileMs, double pireMs) { Images = images; ImagesParSeconde = imagesParSeconde; MedianeMs = medianeMs; CentileMs = centileMs; PireMs = pireMs; }
    }

    // La mesure des images de la carte, dans le build : lancé avec `-forgeMesure <fichier>`, le jeu attend la carte,
    // puis tient tour à tour trois vues — toute la carte, à mi-distance, au plus près — et une traversée de la carte à
    // mi-distance, d'abord avec la synchronisation verticale du réglage livré, puis sans elle. Pour chacune il écrit
    // dans le fichier les images par seconde, le temps d'une image, les appels de dessin, les passes et les triangles,
    // et dit si la fenêtre était au premier plan, d'après ce que le système lui en a dit — « inconnu » s'il ne lui a
    // rien dit : derrière une autre, une mesure ne vaut pas celle d'un joueur. Avec
    // `-forgeMesureQuitte`, le jeu se ferme ensuite. Aucun geste n'est lu ni envoyé ; sans l'argument, rien n'existe.
    public sealed class MesureDImages : MonoBehaviour {
        public const string ARGUMENT = "-forgeMesure", QUITTER = "-forgeMesureQuitte";
        public const float SECONDES_PAR_VUE = 6f, SECONDES_D_ELAN = 1.5f, SECONDES_DE_POSE = 6f, ATTENTE_DE_LA_CARTE_S = 180f;
        private string sortie; private bool quitter; private bool? auPremierPlan; // ce que le système a dit en dernier ; nul s'il n'a rien dit
        private void OnApplicationFocus(bool gagne) => auPremierPlan = gagne;

        // Le fichier demandé sur la ligne de commande ; null sans l'argument ou sans fichier après lui.
        public static string Fichier(string[] arguments) {
            if (arguments == null) return null;
            int i = Array.IndexOf(arguments, ARGUMENT);
            return i >= 0 && i + 1 < arguments.Length && !arguments[i + 1].StartsWith("-") ? arguments[i + 1] : null;
        }

        // Le relevé d'une suite de temps d'image, en ms. La moyenne des images par seconde est celle du temps écoulé :
        // le nombre d'images divisé par leur durée, pas la moyenne de leurs cadences.
        public static ReleveDImages Resumer(IReadOnlyList<float> ms) {
            if (ms == null || ms.Count == 0) return new ReleveDImages(0, -1, -1, -1, -1);
            var tries = new List<float>(ms); tries.Sort(); double somme = 0; foreach (float t in tries) somme += t;
            int centile = Math.Min(tries.Count - 1, (int)Math.Ceiling(0.99 * tries.Count) - 1);
            return new ReleveDImages(tries.Count, somme > 0 ? 1000.0 * tries.Count / somme : -1, tries[tries.Count / 2], tries[Math.Max(0, centile)], tries[tries.Count - 1]);
        }

        // Une ligne du fichier : la vue, la synchronisation, puis le relevé et les compteurs du rendu.
        public static string Ligne(string vue, bool synchro, bool? auPremierPlan, ReleveDImages r, double appels, double passes, double triangles) {
            string N(double v, string format) => v < 0 ? "non mesuré" : v.ToString(format, CultureInfo.InvariantCulture);
            return vue + " ; synchro verticale " + (synchro ? "livrée" : "coupée") + " ; au premier plan : " + (auPremierPlan == null ? "inconnu" : auPremierPlan.Value ? "oui" : "non")
                + " ; " + r.Images + " images ; " + N(r.ImagesParSeconde, "0.0") + " images/s ; image médiane " + N(r.MedianeMs, "0.00") + " ms ; 99e centile " + N(r.CentileMs, "0.00") + " ms ; pire " + N(r.PireMs, "0.00")
                + " ms ; appels de dessin " + N(appels, "0") + " ; passes " + N(passes, "0") + " ; triangles " + N(triangles, "0");
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void AuLancement() {
            string[] arguments = Environment.GetCommandLineArgs(); string fichier = Fichier(arguments);
            if (fichier == null) return;
            var objet = new GameObject("Mesure des images"); DontDestroyOnLoad(objet);
            var mesure = objet.AddComponent<MesureDImages>(); mesure.sortie = fichier; mesure.quitter = Array.IndexOf(arguments, QUITTER) >= 0;
        }

        private IEnumerator Start() {
            var lignes = new StringBuilder(); double debut = Time.realtimeSinceStartupAsDouble; CarteDessinee carte = null;
            while (Time.realtimeSinceStartupAsDouble - debut < ATTENTE_DE_LA_CARTE_S && ((carte = FindFirstObjectByType<CarteDessinee>()) == null || carte.Vue == null || carte.CellulesPosees == 0)) yield return null;
            if (carte == null || carte.Vue == null || carte.CellulesPosees == 0) { Ecrire("MESURE : la carte n'est pas posée après " + ATTENTE_DE_LA_CARTE_S + " s\n"); yield break; }
            // Le temps que les pays, leurs noms, les villes et les étiquettes arrivent.
            for (double t = Time.realtimeSinceStartupAsDouble; Time.realtimeSinceStartupAsDouble - t < SECONDES_DE_POSE;) yield return null;
            VueDeCarte vue = carte.Vue; Vector2 centre = vue.Centre; float tout = vue.DemiMax; int livree = QualitySettings.vSyncCount;
            lignes.Append("MESURE DES IMAGES ; ").Append(Screen.width).Append(" × ").Append(Screen.height).Append(" ; ").Append(SystemInfo.graphicsDeviceName).Append(" ; synchro verticale livrée : ").Append(livree).Append(" ; cellules posées : ").Append(carte.CellulesPosees).Append('\n');
            var vues = new (string nom, float demi, bool traversee)[] { ("toute la carte", tout, false), ("à mi-distance", tout / 4f, false), ("au plus près", VueDeCarte.DEMI_MIN_KM, false), ("traversée à mi-distance", tout / 4f, true) };
            using (ProfilerRecorder appels = ProfilerRecorder.StartNew(ProfilerCategory.Render, "Draw Calls Count"), passes = ProfilerRecorder.StartNew(ProfilerCategory.Render, "SetPass Calls Count"), triangles = ProfilerRecorder.StartNew(ProfilerCategory.Render, "Triangles Count"))
                foreach (bool synchro in new[] { true, false }) {
                    QualitySettings.vSyncCount = synchro ? livree : 0;
                    foreach (var (nom, demi, traversee) in vues) {
                        var ms = new List<float>(4096); double sommeAppels = 0, sommePasses = 0, sommeTriangles = 0; int compteurs = 0; bool? devant = auPremierPlan;
                        double depart = Time.realtimeSinceStartupAsDouble;
                        while (true) {
                            double ecoule = Time.realtimeSinceStartupAsDouble - depart; if (ecoule >= SECONDES_D_ELAN + SECONDES_PAR_VUE) break;
                            // La vue est tenue à chaque image ; la traversée va d'un quart à trois quarts de la carte, d'ouest en est.
                            float avance = Mathf.Clamp01((float)((ecoule - SECONDES_D_ELAN) / SECONDES_PAR_VUE));
                            vue.Centrer(traversee ? centre + new Vector2(Mathf.Lerp(-tout, tout, avance) * vue.Aspect * 0.5f, 0f) : centre, demi);
                            yield return null;
                            if (ecoule < SECONDES_D_ELAN) continue;
                            ms.Add(Time.unscaledDeltaTime * 1000f); if (auPremierPlan == false) devant = false; // perdu une seule image, la vue n'était pas au premier plan
                            if (appels.Valid && passes.Valid && triangles.Valid) { sommeAppels += appels.LastValue; sommePasses += passes.LastValue; sommeTriangles += triangles.LastValue; compteurs++; }
                        }
                        lignes.Append(Ligne(nom, synchro && livree > 0, devant, Resumer(ms), compteurs > 0 ? sommeAppels / compteurs : -1, compteurs > 0 ? sommePasses / compteurs : -1, compteurs > 0 ? sommeTriangles / compteurs : -1)).Append('\n');
                    }
                }
            QualitySettings.vSyncCount = livree; vue.Centrer(centre, tout);
            Ecrire(lignes.ToString());
            if (quitter) Application.Quit();
        }

        private void Ecrire(string texte) {
            try { string dossier = Path.GetDirectoryName(sortie); if (!string.IsNullOrEmpty(dossier)) Directory.CreateDirectory(dossier); File.WriteAllText(sortie, texte, new UTF8Encoding(false)); Debug.Log("MESURE écrite : " + sortie); }
            catch (Exception e) { Debug.LogError("MESURE non écrite : " + e.Message); }
        }
    }
}
