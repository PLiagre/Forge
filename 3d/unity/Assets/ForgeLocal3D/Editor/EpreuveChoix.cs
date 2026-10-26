using System;
using System.Collections;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using Forge.Pont;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Object = UnityEngine.Object;

namespace ForgeLocal3D
{
    // Lot 651 : la session Unity du choix de la Morée, moitié Unity de l'épreuve #615.
    //   Unity -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.EpreuveChoix.Jouer
    //         -forgeEpreuve <rapport.json> -forgeTerre N -forgeSecondeTerre M [-logFile <journal>]
    // ouvre la scène de la carte en Play, attend les six repères des terres de départ, clique comme le joueur (par
    // `SurvolDeCarte`) sur le repère de la terre N, attend son reçu, puis aussitôt sur celui de M, sans jamais toucher
    // `/tick` ni `/vitesse`. Le rapport dit les deux reçus servis et les deux textes du panneau du choix, tels quels : la
    // session ne juge rien, le verdict est celui du script de #615. Le geste est celui de la capture `Lot613`.
    // Codes : 0 les deux reçus relevés, quels qu'ils soient ; 1 session impossible (`defaut` le dit) ; 2 arguments fautifs.
    [InitializeOnLoad]
    public static class EpreuveChoix
    {
        const string Flag = "Forge.Choix.Epreuve", CleRapport = "Forge.Choix.Epreuve.Rapport", CleTerre = "Forge.Choix.Epreuve.Terre", CleSeconde = "Forge.Choix.Epreuve.Seconde";
        const string ARGUMENT_RAPPORT = "-forgeEpreuve", ARGUMENT_TERRE = "-forgeTerre", ARGUMENT_SECONDE = "-forgeSecondeTerre";
        const string RACINE = "Repères des terres de départ";
        const double ATTENTE_S = 30;
        const int FICHES = 6, ACCEPTE = 200;

        [Serializable] public class Recu { public int statut = -1; public long tick = -1; public string raison = ""; }
        [Serializable] public class Rapport {
            public long terre = -1, seconde_terre = -1, tick_avant = -1, tick_apres = -1; public int reperes = -1;
            public Recu premier = new Recu(), second = new Recu();
            public string premier_texte = "", second_texte = "", defaut = "";
        }

        static IEnumerator enCours;
        static Rapport rapport;
        static int derniere = -1;

        static EpreuveChoix() { EditorApplication.update += Tick; }

        internal static string Argument(string nom)
        {
            var a = Environment.GetCommandLineArgs(); int i = Array.IndexOf(a, nom);
            return i >= 0 && i + 1 < a.Length ? a[i + 1] : null;
        }

        // Unity se place dans le projet : un rapport relatif se lit depuis le dossier où la commande a été lancée, que
        // `-projectPath` relatif permet de retrouver (`3d/unity` depuis la racine du dépôt). Sinon, le dossier du projet.
        internal static string DossierDeLancement()
        {
            string projet = Directory.GetCurrentDirectory(), dossier = projet, p = Argument("-projectPath");
            if (string.IsNullOrEmpty(p) || Path.IsPathRooted(p)) return projet;
            foreach (string s in p.Split('/', '\\').Where(s => s != "" && s != ".").Reverse())
            {
                if (dossier == null || !string.Equals(Path.GetFileName(dossier), s, StringComparison.OrdinalIgnoreCase)) return projet;
                dossier = Path.GetDirectoryName(dossier);
            }
            return dossier ?? projet;
        }

        // Un entier ≥ 1 en culture invariante, sans signe ni espace ; sinon null et la raison.
        internal static long? Terre(string nom, out string erreur)
        {
            string brut = Argument(nom); erreur = null;
            if (brut == null) { erreur = nom + " <id de terre> manque"; return null; }
            if (!long.TryParse(brut, NumberStyles.None, CultureInfo.InvariantCulture, out long id) || id < 1) { erreur = nom + " : attendu un entier ≥ 1, reçu « " + brut + " »"; return null; }
            return id;
        }

        public static void Jouer()
        {
            string chemin = Argument(ARGUMENT_RAPPORT);
            if (string.IsNullOrEmpty(chemin)) { Debug.LogError("EPREUVE_CHOIX : " + ARGUMENT_RAPPORT + " <rapport.json> manque"); EditorApplication.Exit(2); return; }
            long? terre = Terre(ARGUMENT_TERRE, out string erreur), seconde = terre == null ? null : Terre(ARGUMENT_SECONDE, out erreur);
            if (erreur != null) { Debug.LogError("EPREUVE_CHOIX : " + erreur); EditorApplication.Exit(2); return; }
            SessionState.SetString(CleRapport, Path.GetFullPath(Path.Combine(DossierDeLancement(), chemin)));
            SessionState.SetString(CleTerre, terre.Value.ToString(CultureInfo.InvariantCulture));
            SessionState.SetString(CleSeconde, seconde.Value.ToString(CultureInfo.InvariantCulture));
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
                rapport = new Rapport {
                    terre = long.Parse(SessionState.GetString(CleTerre, "-1"), CultureInfo.InvariantCulture),
                    seconde_terre = long.Parse(SessionState.GetString(CleSeconde, "-1"), CultureInfo.InvariantCulture),
                };
                enCours = Epreuve(rapport);
            }
            try { if (enCours.MoveNext()) return; }
            catch (Exception e) { Debug.LogException(e); rapport.defaut = e.GetBaseException().Message; }
            int code = rapport.defaut == "" ? 0 : 1;
            SessionState.SetBool(Flag, false); enCours = null;
            string chemin = SessionState.GetString(CleRapport, "");
            try
            {
                File.WriteAllText(chemin, JsonUtility.ToJson(rapport, true));
                Debug.Log("EPREUVE_CHOIX " + chemin + " : premier " + rapport.premier.statut + " « " + rapport.premier.raison + " », second " + rapport.second.statut + " « " + rapport.second.raison + " »"
                    + (code == 0 ? "" : " ; défaut : " + rapport.defaut));
            }
            catch (Exception e) { Debug.LogException(e); code = 1; }
            CitadelEditorBridge.Finish(code);
        }

        static IEnumerator Epreuve(Rapport r)
        {
            var carte = Object.FindFirstObjectByType<CarteDessinee>() ?? throw new InvalidOperationException("la scène " + CarteBuilder.Nom + " n'a pas de carte");
            foreach (var b in new Behaviour[] { carte.GetComponent<ParcoursDeCarte>(), carte.GetComponent<CommandesDuTemps>(), carte.GetComponent<SurvolDeCarte>() })
                if (b == null) throw new InvalidOperationException("la carte n'a pas tous ses composants");
            carte.GetComponent<ParcoursDeCarte>().automatique = true; carte.GetComponent<CommandesDuTemps>().automatique = true;
            var survol = carte.GetComponent<SurvolDeCarte>(); survol.automatique = true;
            ReperesDeDepart[] poses = carte.GetComponents<ReperesDeDepart>();
            if (poses.Length != 1) throw new InvalidOperationException("ReperesDeDepart : attendu 1 sur la carte, observé " + poses.Length);
            ReperesDeDepart reperes = poses[0];

            double fin = Time.realtimeSinceStartupAsDouble + ATTENTE_S;
            while ((reperes.LectureEnVol || reperes.ReperesPoses != FICHES) && Time.realtimeSinceStartupAsDouble < fin) yield return null;
            r.reperes = reperes.ReperesPoses;
            if (reperes.LectureEnVol || reperes.ReperesPoses != FICHES)
            {
                // Sans carte posée, les repères ne lisent rien et n'affichent rien : l'absence affichée est alors celle de la carte.
                r.defaut = "repères : " + reperes.ReperesPoses + " posés sur " + FICHES + " en " + ATTENTE_S + " s"
                    + (reperes.TexteAffiche != null ? " : « " + reperes.TexteAffiche + " »" : ", sans texte des repères ; la carte affiche « " + carte.TexteAffiche + " »");
                yield break;
            }

            var avant = new Lu();
            for (var e = LireDeparts(reperes.port, avant); e.MoveNext();) yield return null;
            if (avant.Lecture == null) { r.defaut = "/departs : " + avant.Panne; yield break; }
            if (!avant.Lecture.Presente) { r.defaut = "/departs absent : " + avant.Lecture.Absence; yield break; }
            r.tick_avant = avant.Lecture.Donnees.Tick;
            FicheDeDepart premiere = avant.Lecture.Donnees.Fiches.FirstOrDefault(f => f.Id == r.terre), seconde = avant.Lecture.Donnees.Fiches.FirstOrDefault(f => f.Id == r.seconde_terre);
            if (premiere == null) { r.defaut = "terre " + r.terre + " absente de /departs"; yield break; }
            if (seconde == null) { r.defaut = "terre " + r.seconde_terre + " absente de /departs"; yield break; }

            var clic = new Clic();
            for (var e = Cliquer(carte, survol, reperes, premiere, clic); e.MoveNext();) yield return null;
            if (clic.Defaut != null) { r.defaut = clic.Defaut; yield break; }
            r.premier = Relever(reperes.RecuDuChoix); r.premier_texte = reperes.ChoixAffiche ?? "";

            // Aussitôt, sans tick entre les deux : la session ne touche jamais `/tick` ni `/vitesse`.
            clic = new Clic();
            for (var e = Cliquer(carte, survol, reperes, seconde, clic); e.MoveNext();) yield return null;
            if (clic.Defaut != null) { r.defaut = clic.Defaut; yield break; }
            r.second = Relever(reperes.RecuDuChoix); r.second_texte = reperes.ChoixAffiche ?? "";

            var apres = new Lu();
            for (var e = LireDeparts(reperes.port, apres); e.MoveNext();) yield return null;
            r.tick_apres = apres.Lecture != null && apres.Lecture.Presente ? apres.Lecture.Donnees.Tick : -1;
        }

        // Le reçu tel que le service l'a rendu : accepté au tick qu'il nomme, refusé avec sa raison, ou absent avec sa cause.
        internal static Recu Relever(RecuIntention r) =>
            r == null ? new Recu { raison = "aucun reçu relevé" }
            : r.Acceptee ? new Recu { statut = ACCEPTE, tick = r.AppliqueeAuTick.Value, raison = "" }
            : r.Presente ? new Recu { statut = r.Statut.Value, tick = -1, raison = r.Erreur }
            : new Recu { statut = -1, tick = -1, raison = r.Absence };

        sealed class Lu { public Lecture<DepartsLus> Lecture; public string Panne; }
        sealed class Clic { public string Defaut; }

        // `/departs` lu hors du fil principal, comme `Lot613` ; une lecture qui lève ou ne finit pas se dit dans `Panne`.
        static IEnumerator LireDeparts(int port, Lu lu)
        {
            var lecture = Task.Run(() => { using (var d = new ClientDeparts(port, ClientDeparts.DelaiMinimal)) return d.Lire(); });
            double fin = Time.realtimeSinceStartupAsDouble + ATTENTE_S;
            while (!lecture.IsCompleted) { if (Time.realtimeSinceStartupAsDouble > fin) { lu.Panne = "pas de réponse en " + ATTENTE_S + " s"; yield break; } yield return null; }
            if (lecture.IsFaulted) lu.Panne = "lecture interrompue : " + lecture.Exception.GetBaseException().Message; else lu.Lecture = lecture.Result;
        }

        // Le clic du joueur, par le survol de la carte, sur le disque de la terre ; puis l'attente du reçu de son dépôt.
        static IEnumerator Cliquer(CarteDessinee carte, SurvolDeCarte survol, ReperesDeDepart reperes, FicheDeDepart terre, Clic clic)
        {
            Transform repere = carte.transform.Find(RACINE + "/Repère " + terre.Nom);
            if (repere == null) { clic.Defaut = "pas de « Repère " + terre.Nom + " » sous « " + RACINE + " »"; yield break; }
            Vector3 ecran = carte.camera.WorldToScreenPoint(repere.position);
            if (ecran.z <= 0 || ecran.x < 0 || ecran.x >= Screen.width || ecran.y < 0 || ecran.y >= Screen.height)
            { clic.Defaut = "repère " + terre.Nom + " hors de l'écran (" + ecran + " pour " + Screen.width + "×" + Screen.height + ")"; yield break; }
            survol.Survoler(ecran); survol.Cliquer(ecran);
            if (!reperes.ChoixEnVol || reperes.TerreDuChoix?.Id != terre.Id)
            { clic.Defaut = "clic sur " + terre.Nom + " : aucun dépôt, terre survolée « " + reperes.Survolee?.Nom + " »"; yield break; }
            double fin = Time.realtimeSinceStartupAsDouble + ATTENTE_S;
            while (reperes.ChoixEnVol) { if (Time.realtimeSinceStartupAsDouble > fin) { clic.Defaut = "pas de reçu pour " + terre.Nom + " en " + ATTENTE_S + " s"; yield break; } yield return null; }
        }
    }
}
