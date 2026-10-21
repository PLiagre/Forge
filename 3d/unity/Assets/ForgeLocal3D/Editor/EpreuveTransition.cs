using System;
using System.Collections;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using Forge.Interface;
using Forge.Pont;
using ForgeLocal3D.Captures;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace ForgeLocal3D
{
    // Lot 732 : la session Unity de l'épreuve de la transition, moitié Unity du verdict qui suivra #410.
    //   Unity -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.EpreuveTransition.Jouer -forgeEpreuve <rapport.json> [-logFile <journal>]
    // Le service tourne déjà, sa terre choisie. La session double-clique sur le siège servi, descend en ville par le fondu
    // livré, puis revient par C ; elle lit `/horloge` une fois avant et après chaque transition. Elle ne pousse aucun tick,
    // ne règle aucune vitesse et ne juge rien : une vitesse fausse ou une ville ouverte ailleurs restent des observations.
    // Codes : 0 les quatre lectures et l'aller-retour finis ; 1 session impossible (`defaut` le dit) ; 2 arguments, sans rapport.
    [InitializeOnLoad]
    public static class EpreuveTransition
    {
        const string Flag = "Forge.Transition.Epreuve", CleRapport = Flag + ".Rapport", CleSortie = Flag + ".Sortie", RAPPORT = "-forgeEpreuve";
        const double ATTENTE_S = 30, VIDANGE_S = 12, LECTURE_S = 5; // la vidange : sans service, Unity pend sinon à « Cleanup mono »
        const float CRANS = 12; // le cadrage du siège de #729

        [Serializable] public class Releve { public long tick = -1; public double jours_par_seconde = -1; public string scene = ""; }
        [Serializable] public class Rapport
        {
            public long cellule = -1;
            public Releve carte_avant = new Releve(), ville_apres = new Releve(), ville_avant = new Releve(), carte_apres = new Releve();
            public string defaut = "";
        }

        static IEnumerator enCours; static Rapport rapport; static int derniere = -1; static double vidange; static string etape = ""; static bool frappee;
        static EpreuveTransition() { EditorApplication.update += Tick; }

        public static void Jouer()
        {
            string chemin = EpreuveChoix.Argument(RAPPORT);
            if (string.IsNullOrEmpty(chemin) || chemin.StartsWith("-")) { Debug.LogError("EPREUVE_TRANSITION : " + RAPPORT + " <rapport.json> manque"); EditorApplication.Exit(2); return; }
            string complet = Path.GetFullPath(Path.Combine(EpreuveChoix.DossierDeLancement(), chemin));
            try { string dossier = Path.GetDirectoryName(complet); if (!string.IsNullOrEmpty(dossier)) Directory.CreateDirectory(dossier); }
            catch (Exception e) { Debug.LogError("EPREUVE_TRANSITION : dossier du rapport : " + e.Message); EditorApplication.Exit(1); return; }
            SessionState.SetString(CleRapport, complet);
            try { EditorSceneManager.OpenScene(CarteBuilder.Chemin); SessionState.SetBool(Flag, true); EditorApplication.EnterPlaymode(); }
            catch (Exception e) { Debug.LogException(e); Ecrire(new Rapport { defaut = "1. ouverture de " + CarteBuilder.Nom + " : " + e.GetBaseException().Message }); EditorApplication.Exit(1); }
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
            if (enCours == null) { rapport = new Rapport(); enCours = Seance(rapport); }
            try { if (enCours.MoveNext()) return; }
            catch (Exception e) { Debug.LogException(e); if (rapport.defaut == "") rapport.defaut = etape + " : " + e.GetBaseException().Message; }
            Relacher(); SessionState.SetBool(Flag, false); enCours = null;
            SessionState.SetInt(CleSortie, Ecrire(rapport) && rapport.defaut == "" ? 0 : 1); EditorApplication.ExitPlaymode();
        }

        static bool Ecrire(Rapport r)
        {
            string chemin = SessionState.GetString(CleRapport, "");
            try { File.WriteAllText(chemin, JsonUtility.ToJson(r, true)); }
            catch (Exception e) { Debug.LogError("EPREUVE_TRANSITION : rapport « " + chemin + " » impossible à écrire : " + e.Message); return false; }
            Debug.Log("EPREUVE_TRANSITION " + chemin + " : cellule " + N(r.cellule) + ", carte_avant " + Dire(r.carte_avant) + ", ville_apres " + Dire(r.ville_apres)
                + ", ville_avant " + Dire(r.ville_avant) + ", carte_apres " + Dire(r.carte_apres) + (r.defaut == "" ? "" : " ; défaut : " + r.defaut));
            return true;
        }
        static string N(long v) => v.ToString(CultureInfo.InvariantCulture);
        static string Dire(Releve h) => "tick " + N(h.tick) + ", " + h.jours_par_seconde.ToString("R", CultureInfo.InvariantCulture) + " j/s, scène « " + h.scene + " »";

        static IEnumerator Seance(Rapport r)
        {
            etape = "2. carte et maison";
            CarteDessinee[] cartes = Object.FindObjectsByType<CarteDessinee>(FindObjectsSortMode.None);
            if (cartes.Length != 1) throw new InvalidOperationException("CarteDessinee : attendu 1 dans " + CarteBuilder.Nom + ", observé " + cartes.Length);
            CarteDessinee carte = cartes[0]; int port = carte.port;
            PassageALaCapitale passage = null; CabinetDeCarte cabinet = null;
            for (var e = Lot690.Jusqua(() => Posee(carte) && (passage = carte.GetComponent<PassageALaCapitale>()) != null && (cabinet = carte.GetComponent<CabinetDeCarte>()) != null && Servie(cabinet.Partie),
                () => "carte de " + carte.CellulesPosees + " cellules posées sur " + carte.CellulesServies + " (« " + carte.TexteAffiche + " »), "
                    + (carte.GetComponent<CabinetDeCarte>() is CabinetDeCarte c ? Absente(c.Partie) : "sans cabinet")); e.MoveNext();) yield return null;
            // Le siège servi de la maison du joueur, jamais une constante : sans cellule ni place, aucune destination ne se fabrique.
            SiegeDeMaison siege = cabinet.Partie.Maison.Donnees.Siege;
            if (siege.CellId == null || !(siege.Position is PointCarte position)) throw new InvalidOperationException("siège de " + cabinet.Partie.Maison.Donnees.Id + " sans cellule ou sans place sur la carte");
            for (var e = Lot690.Jusqua(() => passage.SiegeLu != null, () => "le passage ne lit aucun siège : « " + passage.Absence + " »"); e.MoveNext();) yield return null;
            SurvolDeCarte survol = carte.GetComponent<SurvolDeCarte>() ?? throw new InvalidOperationException("la carte n'a pas de survol");
            survol.automatique = true; (carte.GetComponent<ParcoursDeCarte>() ?? throw new InvalidOperationException("la carte n'a pas de parcours")).automatique = true;

            etape = "3. double-clic sur le siège";
            Vector3 local = carte.PositionSurLaCarte(position, ReperesDeDepart.HAUTEUR_LIEU) ?? throw new InvalidOperationException("la carte n'a pas d'origine"), point = carte.transform.TransformPoint(local);
            if (carte.Vue == null) throw new InvalidOperationException("la carte n'a pas de vue à cadrer");
            carte.Vue.Zoomer(CRANS, carte.camera.WorldToViewportPoint(point)); carte.Vue.Centrer(new Vector2(local.x, local.z), carte.Vue.Demi);
            yield return null; // la carte se recadre
            Vector2 ecran = carte.camera.WorldToScreenPoint(point);
            if (ecran.x < 0 || ecran.y < 0 || ecran.x >= Screen.width || ecran.y >= Screen.height) throw new InvalidOperationException("siège " + N(siege.CellId.Value) + " hors de l'écran : " + ecran + " pour " + Screen.width + "×" + Screen.height);
            for (var e = Lire(port, r.carte_avant, "carte_avant"); e.MoveNext();) yield return null;
            survol.Cliquer(ecran); survol.Cliquer(ecran);
            TransitionDeVue descente = Object.FindFirstObjectByType<TransitionDeVue>() ?? throw new InvalidOperationException("aucune transition après le double-clic, scène demandée « " + passage.SceneDemandee + " »");

            etape = "4. ville";
            DesertRoadTool outil = null;
            for (var e = Lot690.Jusqua(() => (descente == null || !descente.EnCours) && (outil = Outil()) != null && outil.TickOuverture >= 0,
                () => "transition " + (descente == null ? "finie" : descente.EnCours ? "en cours" : "arrêtée") + ", scène « " + SceneManager.GetActiveScene().name + " », plan « " + (outil == null ? "sans outil unique" : outil.Message) + " »"); e.MoveNext();) yield return null;
            r.cellule = outil.Cellule;
            for (var e = Lire(port, r.ville_apres, "ville_apres"); e.MoveNext();) yield return null;
            for (double fin = Time.realtimeSinceStartupAsDouble + 1; Time.realtimeSinceStartupAsDouble < fin;) yield return null; // une seconde réelle, sans attendre de tick
            for (var e = Lire(port, r.ville_avant, "ville_avant"); e.MoveNext();) yield return null;

            etape = "5. retour par C";
            outil.automatique = false;
            new GameObject("Frappe").AddComponent<Frappe>(); (Frappe.tenue, Frappe.armee, frappee) = (Key.C, true, true);
            TransitionDeVue retour = null;
            for (var e = Lot690.Jusqua(() => (retour = Object.FindObjectsByType<TransitionDeVue>(FindObjectsSortMode.None).FirstOrDefault(t => t != descente)) != null, () => "C n'a lancé aucune transition"); e.MoveNext();) yield return null;
            (Frappe.tenue, Frappe.armee) = (null, true); yield return null; // une frappe sans touche relâche C
            CarteDessinee arrivee = null;
            for (var e = Lot690.Jusqua(() => (retour == null || !retour.EnCours) && (arrivee = Carte()) != null && Posee(arrivee),
                () => "transition " + (retour == null ? "finie" : retour.EnCours ? "en cours" : "arrêtée") + ", scène « " + SceneManager.GetActiveScene().name + " »" + (arrivee == null ? " sans carte unique" : ", " + arrivee.CellulesPosees + " cellules posées sur " + arrivee.CellulesServies)); e.MoveNext();) yield return null;
            frappee = false;
            for (var e = Lire(port, r.carte_apres, "carte_apres"); e.MoveNext();) yield return null;
        }

        static bool Posee(CarteDessinee c) => c.CellulesPosees > 0 && c.CellulesPosees == c.CellulesServies;
        // Le joueur a sa maison, lue avec son siège ; l'absence, elle, se dit.
        static bool Servie(LecturePartie p) => p != null && !p.Occupee && p.Monde != null && p.Monde.Presente && !string.IsNullOrEmpty(p.Monde.Donnees.MaisonDuJoueur)
            && p.Maison != null && p.Maison.Presente && p.Maison.Donnees.Id == p.Monde.Donnees.MaisonDuJoueur;
        static string Absente(LecturePartie p) => p == null ? "partie absente" : p.Occupee ? "lecture en cours" : p.Monde == null ? "monde non lu" : !p.Monde.Presente ? "monde absent : " + p.Monde.Absence
            : string.IsNullOrEmpty(p.Monde.Donnees.MaisonDuJoueur) ? "aucune maison du joueur" : p.Maison == null ? "maison non lue" : !p.Maison.Presente ? "maison absente : " + p.Maison.Absence : "maison " + p.Maison.Donnees.Id + " différente";
        static T Unique<T>() where T : Component
        { T[] tous = SceneManager.GetActiveScene().GetRootGameObjects().SelectMany(o => o.GetComponentsInChildren<T>(true)).ToArray(); return tous.Length == 1 ? tous[0] : null; }
        static DesertRoadTool Outil() => Unique<DesertRoadTool>();
        static CarteDessinee Carte() => Unique<CarteDessinee>();

        // Une seule lecture de `/horloge`, hors du fil principal, par un client de 5 s disposé. Manquée : −1 et sa cause.
        static IEnumerator Lire(int port, Releve releve, string nom)
        {
            string scene = SceneManager.GetActiveScene().name;
            Task<Lecture<HorlogeLue>> lu = Task.Run(() => { using (var c = new ClientHorloge(port, TimeSpan.FromSeconds(LECTURE_S))) return c.Lire(); });
            for (var e = Lot690.Attendre(lu, "lecture /horloge " + nom); e.MoveNext();) yield return null;
            if (!lu.Result.Presente) throw new InvalidOperationException(nom + " : /horloge absente : " + lu.Result.Absence);
            (releve.tick, releve.jours_par_seconde, releve.scene) = (lu.Result.Donnees.Tick, lu.Result.Donnees.JoursParSeconde, scene);
        }

        // Un défaut pendant que C est tenue : la frappe a pu partir avec la ville, le clavier se relâche directement.
        static void Relacher()
        {
            if (!frappee) return; frappee = false; Frappe.tenue = null; Frappe.armee = false;
            if (Keyboard.current != null) InputState.Change(Keyboard.current, new KeyboardState());
        }
    }
}
