using System;
using System.Collections;
using System.Globalization;
using System.IO;
using System.Linq;
using Forge.Pont;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Object = UnityEngine.Object;

namespace ForgeLocal3D
{
    // Lot 527 : l'épreuve de la carte, côté Unity. `pc/epreuve_carte.py` a lancé le service et lu `/carte` et `/monde` ;
    //   Unity -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.EpreuveCarte.Jouer -forgeEpreuve <rapport.json>
    //         [-forgeCell C] [-forgeEpreuveRetirer]
    // ouvre la scène de la carte en Play, attend qu'elle soit posée, survole la cellule C (le milieu du plus grand triangle
    // de son dessin), attend que la fiche ait lu le monde, puis écrit un rapport : les cellules posées et servies, la
    // cellule survolée, le texte de la fiche et le tick du monde lu. Il ne juge rien : le verdict est celui du script, qui
    // compare au service. Une carte qui ne se pose pas (le monde ne répond pas) se rapporte telle quelle, avec son message.
    // `-forgeEpreuveRetirer` est la contre-épreuve d'une scène qui perd une cellule : une cellule autre que C est retirée
    // du dessin avant le compte.
    [InitializeOnLoad]
    public static class EpreuveCarte
    {
        const string Flag = "Forge.Carte.Epreuve", CleRapport = "Forge.Carte.Epreuve.Rapport", CleCellule = "Forge.Carte.Epreuve.Cellule", CleRetirer = "Forge.Carte.Epreuve.Retirer";
        const string ARGUMENT_RAPPORT = "-forgeEpreuve", ARGUMENT_RETIRER = "-forgeEpreuveRetirer";
        const double ATTENTE_CARTE_S = 30, ATTENTE_MONDE_S = 20;

        [Serializable]
        public class Rapport
        {
            public int cellules_posees = -1, cellules_servies = -1;
            public long cellule = -1, survolee = -1, retiree = -1, tick = -1;
            public string fiche = "", carte = "", defaut = "";
        }

        static IEnumerator enCours;
        static Rapport rapport;
        static int derniere = -1;

        static EpreuveCarte() { EditorApplication.update += Tick; }

        static string Argument(string nom)
        {
            var a = Environment.GetCommandLineArgs(); int i = Array.IndexOf(a, nom);
            return i >= 0 && i + 1 < a.Length ? a[i + 1] : null;
        }

        public static void Jouer()
        {
            string chemin = Argument(ARGUMENT_RAPPORT);
            if (string.IsNullOrEmpty(chemin)) { Debug.LogError("EPREUVE_CARTE : " + ARGUMENT_RAPPORT + " <rapport.json> manque"); EditorApplication.Exit(2); return; }
            long cellule = PanneauLieu.LireCellule(Environment.GetCommandLineArgs(), PanneauLieu.CELLULE_PAR_DEFAUT, out string erreur);
            if (erreur != null) { Debug.LogError("EPREUVE_CARTE : " + erreur); EditorApplication.Exit(2); return; }
            SessionState.SetString(CleRapport, Path.GetFullPath(chemin));
            SessionState.SetString(CleCellule, cellule.ToString(CultureInfo.InvariantCulture));
            SessionState.SetBool(CleRetirer, Environment.GetCommandLineArgs().Contains(ARGUMENT_RETIRER));
            EditorSceneManager.OpenScene(CarteBuilder.Chemin);
            SessionState.SetBool(Flag, true);
            EditorApplication.EnterPlaymode();
        }

        static void Tick()
        {
            if (!SessionState.GetBool(Flag, false) || !Application.isPlaying || derniere == Time.frameCount) return;
            derniere = Time.frameCount;
            if (enCours == null)
            {
                rapport = new Rapport { cellule = long.Parse(SessionState.GetString(CleCellule, "-1"), CultureInfo.InvariantCulture) };
                enCours = Epreuve(rapport, SessionState.GetBool(CleRetirer, false));
            }
            int code;
            try { if (enCours.MoveNext()) return; code = 0; }
            catch (Exception e) { Debug.LogException(e); rapport.defaut = e.GetBaseException().Message; code = 1; }
            SessionState.SetBool(Flag, false); enCours = null;
            string chemin = SessionState.GetString(CleRapport, "");
            try
            {
                File.WriteAllText(chemin, JsonUtility.ToJson(rapport, true));
                Debug.Log("EPREUVE_CARTE " + chemin + " : " + rapport.cellules_posees + " cellules posées, " + rapport.cellules_servies + " servies, fiche « " + rapport.fiche.Replace("\n", " | ") + " »");
            }
            catch (Exception e) { Debug.LogException(e); code = 1; }
            CitadelEditorBridge.Finish(code);
        }

        static IEnumerator Epreuve(Rapport r, bool retirer)
        {
            var carte = Object.FindFirstObjectByType<CarteDessinee>() ?? throw new InvalidOperationException("la scène " + CarteBuilder.Nom + " n'a pas de carte");
            foreach (var b in new Behaviour[] { carte.GetComponent<ParcoursDeCarte>(), carte.GetComponent<CommandesDuTemps>(), carte.GetComponent<SurvolDeCarte>() })
                if (b == null) throw new InvalidOperationException("la carte n'a pas tous ses composants");
            carte.GetComponent<ParcoursDeCarte>().automatique = true; carte.GetComponent<CommandesDuTemps>().automatique = true; carte.GetComponent<SurvolDeCarte>().automatique = true;
            var fiche = carte.GetComponent<FicheDeCellule>();

            double fin = Time.realtimeSinceStartupAsDouble + ATTENTE_CARTE_S;
            while (carte.CellulesServies < 0 && Time.realtimeSinceStartupAsDouble < fin) yield return null;
            r.carte = carte.TexteAffiche ?? ""; r.cellules_servies = carte.CellulesServies; r.cellules_posees = carte.CellulesPosees;
            if (carte.CellulesServies < 0) yield break; // la carte ne s'est pas posée : le rapport le dit, le script juge

            Transform racine = carte.transform.Find("Cellules de la carte") ?? throw new InvalidOperationException("la carte posée n'a pas de « Cellules de la carte »");
            string nom = "Cellule " + r.cellule.ToString(CultureInfo.InvariantCulture);
            if (retirer)
            {
                Transform autre = racine.Cast<Transform>().FirstOrDefault(t => t.name != nom) ?? throw new InvalidOperationException("aucune autre cellule à retirer");
                r.retiree = long.Parse(autre.name.Substring("Cellule ".Length), CultureInfo.InvariantCulture);
                Object.DestroyImmediate(autre.gameObject);
            }
            r.cellules_posees = carte.CellulesPosees;

            Transform dessin = racine.Find(nom);
            if (dessin == null) { r.defaut = "la cellule " + r.cellule + " n'est pas dessinée"; yield break; }
            Vector3 point = dessin.TransformPoint(Milieu(dessin.GetComponent<MeshFilter>().sharedMesh));
            fin = Time.realtimeSinceStartupAsDouble + ATTENTE_MONDE_S;
            while (fiche.MondeLu == null && fiche.AbsenceDuMonde == null && Time.realtimeSinceStartupAsDouble < fin) yield return null;
            fiche.SurvolerPoint(point);
            r.survolee = fiche.Survolee != null ? fiche.Survolee.CellId : -1;
            r.fiche = fiche.TexteAffiche ?? "";
            r.tick = fiche.MondeLu != null ? fiche.MondeLu.Tick : -1;
        }

        // Le milieu du plus grand triangle du dessin : un point bien à la cellule, loin de ses bords.
        static Vector3 Milieu(Mesh maillage)
        {
            var s = maillage.vertices; var t = maillage.triangles; int meilleur = 0; float aire = -1;
            for (int k = 0; k < t.Length; k += 3)
            {
                float a = Vector3.Cross(s[t[k + 1]] - s[t[k]], s[t[k + 2]] - s[t[k]]).magnitude;
                if (a > aire) { aire = a; meilleur = k; }
            }
            return (s[t[meilleur]] + s[t[meilleur + 1]] + s[t[meilleur + 2]]) / 3;
        }
    }
}
