using System;
using System.Collections;
using System.IO;
using System.Linq;
using System.Text;
using Forge.Pont;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace ForgeLocal3D
{
    // Lot #958 — le banc du temps d'image : combien de millisecondes coûte une image vue d'une caméra posée,
    // rendue en 1920 × 1080 sans synchronisation ni plafond, résumée en médiane, 95e centile et maximum.
    // Usage, depuis un scénario de capture (un `yield return` d'un autre IEnumerator ne l'exécuterait pas) :
    //     var m = BancDuTempsDImage.Mesurer(camera, 60, 300, r => releve = r); while (m.MoveNext()) yield return null;
    // Le banc rend lui-même la caméra à chaque image et attend la fin du rendu : en batch, l'éditeur ne rend pas
    // la vue du jeu, et #739 mesurait ainsi 0,226 ms par image (le vide). Il ne touche ni `camera.targetTexture`
    // ni la pose de la caméra.
    [Serializable]
    public sealed class ReleveDuBanc
    {
        public double[] temps_ms;
        public int nombre;
        public double mediane_ms, p95_ms, maximum_ms;
        public int largeur, hauteur, anticrenelage, chauffe, images;
        public bool rendu;
        public int vsync_avant, vsync_pendant, vsync_apres, plafond_avant, plafond_pendant, plafond_apres;
    }

    public static class BancDuTempsDImage
    {
        const int LARGEUR = 1920, HAUTEUR = 1080, CHAUFFE = 60, IMAGES = 300, IMAGES_DE_POSE = 10;
        const string RAPPORT = "lot958-banc.json";
        // Le témoin de la contre-épreuve : la même boucle, sans rendu ; l'image doit alors ne presque rien coûter.
        public const string SANS_RENDU = "-forge958SansRendu";

        [Serializable]
        sealed class SuiteDuRapport { public string camera, contre_epreuve, defaut; public bool optimisations; }

        public static IEnumerator Mesurer(Camera camera, int chauffe, int images, Action<ReleveDuBanc> rendre, bool rendu = true)
        {
            if (camera == null) throw new ArgumentNullException(nameof(camera));
            if (rendre == null) throw new ArgumentNullException(nameof(rendre));
            if (chauffe < 0) throw new ArgumentOutOfRangeException(nameof(chauffe), chauffe, "chauffe ≥ 0");
            if (images < 1) throw new ArgumentOutOfRangeException(nameof(images), images, "images ≥ 1");
            return Derouler(camera, chauffe, images, rendre, rendu);
        }

        static IEnumerator Derouler(Camera camera, int chauffe, int images, Action<ReleveDuBanc> rendre, bool rendu)
        {
            var r = new ReleveDuBanc { largeur = LARGEUR, hauteur = HAUTEUR, chauffe = chauffe, images = images, rendu = rendu,
                vsync_avant = QualitySettings.vSyncCount, plafond_avant = Application.targetFrameRate };
            var temps = new double[images];
            RenderTexture rt = null;
            Texture2D pixel = null;
            try
            {
                QualitySettings.vSyncCount = 0;
                Application.targetFrameRate = -1;
                r.vsync_pendant = QualitySettings.vSyncCount;
                r.plafond_pendant = Application.targetFrameRate;
                r.anticrenelage = Mathf.Max(1, QualitySettings.antiAliasing);
                rt = new RenderTexture(LARGEUR, HAUTEUR, 24, RenderTextureFormat.ARGB32) { antiAliasing = r.anticrenelage };
                rt.Create();
                pixel = new Texture2D(1, 1, TextureFormat.RGB24, false);
                // Un seul chronomètre : le temps d'une image est l'écart entre deux instants consécutifs, et compte tout
                // ce qu'elle a coûté (scripts du jeu, rendu, attente du GPU).
                var montre = System.Diagnostics.Stopwatch.StartNew();
                double precedent = 0;
                for (int i = 0; i <= chauffe + images; i++)
                {
                    if (rendu)
                    {
                        RenderPipeline.SubmitRenderRequest(camera, new UniversalRenderPipeline.SingleCameraRequest { destination = rt });
                        // Lire un pixel attend la fin du rendu GPU.
                        var ancien = RenderTexture.active;
                        RenderTexture.active = rt;
                        pixel.ReadPixels(new Rect(0, 0, 1, 1), 0, 0);
                        RenderTexture.active = ancien;
                    }
                    double instant = montre.Elapsed.TotalMilliseconds;
                    if (i > chauffe) temps[i - chauffe - 1] = instant - precedent;
                    precedent = instant;
                    yield return null;
                }
            }
            finally
            {
                QualitySettings.vSyncCount = r.vsync_avant;
                Application.targetFrameRate = r.plafond_avant;
                r.vsync_apres = QualitySettings.vSyncCount;
                r.plafond_apres = Application.targetFrameRate;
                if (rt != null) { rt.Release(); UnityEngine.Object.DestroyImmediate(rt); }
                if (pixel != null) UnityEngine.Object.DestroyImmediate(pixel);
            }
            var resume = TempsDImage.Resumer(temps);
            r.temps_ms = temps;
            r.nombre = resume.Nombre;
            r.mediane_ms = resume.MedianeMs;
            r.p95_ms = resume.P95Ms;
            r.maximum_ms = resume.MaximumMs;
            rendre(r);
        }

        // Le banc se vérifie lui-même : des réglages non coupés pendant la mesure, ou non rendus après, la faussent.
        static string Defaut(ReleveDuBanc r)
        {
            if (r.vsync_pendant != 0 || r.plafond_pendant != -1) return "réglages pendant : vsync " + r.vsync_pendant + ", plafond " + r.plafond_pendant;
            if (r.vsync_apres != r.vsync_avant || r.plafond_apres != r.plafond_avant) return "réglages non rendus : vsync " + r.vsync_apres + ", plafond " + r.plafond_apres;
            return "";
        }

        // Mesure la caméra de la scène, sans la déplacer, puis écrit `lot958-banc.json`. La photo qui suit doit être
        // le plan fixe : rien ne change à l'écran.
        [ScenarioDeCapture(958, "banc")]
        static IEnumerator Banc(Camera camera)
        {
            string chemin = Path.Combine(Capture.DossierDesCaptures, RAPPORT);
            if (File.Exists(chemin)) throw new InvalidOperationException(RAPPORT + " existe déjà : " + chemin);
            bool sansRendu = Environment.GetCommandLineArgs().Contains(SANS_RENDU);
            ReleveDuBanc releve = null;
            var m = Mesurer(camera, CHAUFFE, IMAGES, x => releve = x, !sansRendu);
            while (m.MoveNext()) yield return null;
            if (releve == null) throw new InvalidOperationException("le banc n'a rien rendu");
            var suite = new SuiteDuRapport { camera = camera.name, optimisations = OptimisationsDeLaVille.Actives,
                contre_epreuve = sansRendu ? SANS_RENDU.Substring(1) : "", defaut = Defaut(releve) };
            string rapport = JsonUtility.ToJson(releve).TrimEnd('}') + "," + JsonUtility.ToJson(suite).Substring(1);
            File.WriteAllText(chemin, rapport, new UTF8Encoding(false));
            Debug.Log("CAPTURE_958 " + rapport);
            if (suite.defaut != "") throw new InvalidOperationException(suite.defaut);
            for (int i = 0; i < IMAGES_DE_POSE; i++)
                yield return null;
        }
    }
}
