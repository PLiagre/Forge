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
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace ForgeLocal3D
{
    // Lot 702 : la session Unity de l'épreuve de la capitale, moitié Unity de l'épreuve #684.
    //   Unity -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.EpreuveCapitale.Jouer
    //         -forgeEpreuve <rapport.json> -forgeTerre N [-logFile <journal>]
    // ouvre la scène de la carte en Play, choisit la terre N dans le cabinet, pousse un seul tick, puis relève ce que le
    // passage fait : une ville chargée par lui-même (`SceneManager.LoadScene`, comme dans le jeu) et son panneau du lieu, ou
    // son message. La session ne juge rien : ni la cellule, ni le message ; le verdict est celui de `pc/epreuve_capitale.py`.
    // Le geste est celui des captures `Lot690` (Bar) et `Lot701` (Zab), sans chargement additif ni photo.
    // Codes : 0 une ville ou un message relevé, quel qu'il soit ; 1 session impossible (`defaut` le dit) ; 2 arguments fautifs.
    [InitializeOnLoad]
    public static class EpreuveCapitale
    {
        const string Flag = "Forge.Capitale.Epreuve", CleRapport = "Forge.Capitale.Epreuve.Rapport", CleTerre = "Forge.Capitale.Epreuve.Terre", CleSortie = "Forge.Capitale.Epreuve.Sortie";
        const string ARGUMENT_RAPPORT = "-forgeEpreuve", ARGUMENT_TERRE = "-forgeTerre";
        const double ATTENTE_S = 30, VIDANGE_S = 12; // plus que le délai de 10 s des lectures du cabinet

        [Serializable] public class Rapport {
            public long terre = -1, tick_avant = -1, tick_apres = -1, cellule = -1, tick_ouverture = -1;
            public EpreuveChoix.Recu choix = new EpreuveChoix.Recu();
            public string scene_active = "", panneau_lieu = "", message_passage = "", defaut = "";
        }

        static IEnumerator enCours;
        static Rapport rapport;
        static int derniere = -1;
        static double vidange;

        static EpreuveCapitale() { EditorApplication.update += Tick; }

        public static void Jouer()
        {
            string chemin = EpreuveChoix.Argument(ARGUMENT_RAPPORT);
            if (string.IsNullOrEmpty(chemin)) { Debug.LogError("EPREUVE_CAPITALE : " + ARGUMENT_RAPPORT + " <rapport.json> manque"); EditorApplication.Exit(2); return; }
            long? terre = EpreuveChoix.Terre(ARGUMENT_TERRE, out string erreur);
            if (erreur != null) { Debug.LogError("EPREUVE_CAPITALE : " + erreur); EditorApplication.Exit(2); return; }
            SessionState.SetString(CleRapport, Path.GetFullPath(Path.Combine(EpreuveChoix.DossierDeLancement(), chemin)));
            SessionState.SetString(CleTerre, terre.Value.ToString(CultureInfo.InvariantCulture));
            EditorSceneManager.OpenScene(CarteBuilder.Chemin);
            SessionState.SetBool(Flag, true);
            EditorApplication.EnterPlaymode();
        }

        static void Tick()
        {
            // Sans service, quitter pendant que les lectures de la carte attendent un port fermé laisse Unity pendu à « Cleanup
            // mono » (mesuré le 18/10/2026) : la session sort d'abord du Play, laisse ces lectures finir, puis rend son code.
            int sortie = SessionState.GetInt(CleSortie, -1);
            if (sortie >= 0 && !EditorApplication.isPlayingOrWillChangePlaymode)
            {
                if (vidange == 0) vidange = EditorApplication.timeSinceStartup + VIDANGE_S;
                if (EditorApplication.timeSinceStartup < vidange) return;
                SessionState.EraseInt(CleSortie); CitadelEditorBridge.Finish(sortie); return;
            }
            if (!SessionState.GetBool(Flag, false) || !Application.isPlaying || derniere == Time.frameCount) return;
            derniere = Time.frameCount;
            if (enCours == null)
            {
                rapport = new Rapport { terre = long.Parse(SessionState.GetString(CleTerre, "-1"), CultureInfo.InvariantCulture) };
                enCours = Epreuve(rapport);
            }
            try { if (enCours.MoveNext()) return; }
            catch (Exception e) { Debug.LogException(e); rapport.defaut = e.GetBaseException().Message; }
            int code = rapport.defaut == "" ? 0 : 1;
            SessionState.SetBool(Flag, false); enCours = null;
            string chemin = SessionState.GetString(CleRapport, "");
            try
            {
                rapport.scene_active = SceneManager.GetActiveScene().name;
                File.WriteAllText(chemin, JsonUtility.ToJson(rapport, true));
                Debug.Log("EPREUVE_CAPITALE " + chemin + " : scène " + rapport.scene_active + ", cellule " + N(rapport.cellule) + ", tick " + N(rapport.tick_ouverture)
                    + ", panneau « " + rapport.panneau_lieu + " », message « " + rapport.message_passage + " »" + (code == 0 ? "" : " ; défaut : " + rapport.defaut));
            }
            catch (Exception e) { Debug.LogException(e); code = 1; }
            SessionState.SetInt(CleSortie, code); EditorApplication.ExitPlaymode();
        }

        static string N(long v) => v.ToString(CultureInfo.InvariantCulture);

        static T Unique<T>(Scene scene, string etape) where T : Component
        {
            T[] tous = scene.GetRootGameObjects().SelectMany(r => r.GetComponentsInChildren<T>(true)).ToArray();
            if (tous.Length != 1) throw new InvalidOperationException(etape + " : la scène « " + scene.name + " » porte " + tous.Length + " " + typeof(T).Name + ", il en faut un");
            return tous[0];
        }

        static IEnumerator Epreuve(Rapport r)
        {
            // Le cabinet : la carte, son passage et son cabinet, tous posés d'eux-mêmes à l'ouverture de la carte en Play.
            CarteDessinee[] cartes = Object.FindObjectsByType<CarteDessinee>(FindObjectsSortMode.None);
            if (cartes.Length != 1) throw new InvalidOperationException("CarteDessinee : attendu 1 dans la scène " + CarteBuilder.Nom + ", observé " + cartes.Length);
            CarteDessinee carte = cartes[0]; int port = carte.port;
            PassageALaCapitale[] passages = carte.GetComponents<PassageALaCapitale>();
            if (passages.Length != 1) throw new InvalidOperationException("PassageALaCapitale : attendu 1 sur la carte, observé " + passages.Length);
            PassageALaCapitale passage = passages[0];
            CabinetDeCarte cabinet = carte.GetComponent<CabinetDeCarte>() ?? throw new InvalidOperationException("la carte n'a pas de CabinetDeCarte");
            for (var e = Lot690.Jusqua(() => Lot690.LecturePrete(cabinet.Partie), () => "cabinet : " + Lot690.Dire(cabinet.Partie)); e.MoveNext();) yield return null;
            LecturePartie partie = cabinet.Partie;
            r.tick_avant = partie.Monde.Donnees.Monde.Tick;
            FicheDeDepart fiche = partie.Departs.Donnees.Fiches.FirstOrDefault(f => f.Id == r.terre) ?? throw new InvalidOperationException("terre " + N(r.terre) + " absente de /departs");

            // Le choix, puis le temps que le passage voie le départ avant le tick.
            for (var e = Lot690.Attendre(partie.Choisir(fiche.Id), "choix de " + fiche.Nom); e.MoveNext();) yield return null;
            r.choix = EpreuveChoix.Relever(partie.Recu);
            if (partie.Recu == null || !partie.Recu.Acceptee) throw new InvalidOperationException("choix de " + fiche.Nom + " refusé : " + r.choix.raison);
            for (double fin = Time.realtimeSinceStartupAsDouble + 2 * PassageALaCapitale.PERIODE_LECTURE_S + 0.25; Time.realtimeSinceStartupAsDouble < fin;)
            {
                if (passage.Absence != null || passage.TexteAffiche != null || passage.SceneDemandee != null)
                    throw new InvalidOperationException("passage avant le tick : absence « " + passage.Absence + " », message « " + passage.TexteAffiche + " », scène « " + passage.SceneDemandee + " »");
                yield return null;
            }

            // Un seul tick ; la session ne touche jamais `/vitesse`.
            Task<(int statut, string corps)> pousse = Lot690.PousserTick(port);
            for (var e = Lot690.Attendre(pousse, "POST /tick?n=1"); e.MoveNext();) yield return null;
            if (pousse.Result.statut != 200) throw new InvalidOperationException("POST /tick?n=1 a rendu " + pousse.Result.statut + " : " + pousse.Result.corps);

            // Ville ou message, tel que le passage le décide.
            for (double fin = Time.realtimeSinceStartupAsDouble + ATTENTE_S; passage.TexteAffiche == null && passage.SceneDemandee == null;)
            {
                if (Time.realtimeSinceStartupAsDouble > fin)
                    throw new InvalidOperationException("après le tick, ni ville ni message en " + ATTENTE_S + " s : passage « " + passage.Absence + " », cabinet « " + Lot690.Dire(cabinet.Partie) + " »");
                yield return null;
            }
            if (passage.SceneDemandee == null) r.message_passage = passage.TexteAffiche;
            else
            {
                // La carte disparaît au chargement : le nom de la scène se retient tout de suite.
                string scene = passage.SceneDemandee;
                for (var e = Lot690.Jusqua(() => SceneManager.GetActiveScene() is Scene s && s.name == scene && s.GetRootGameObjects().Any(o => o.GetComponentInChildren<DesertRoadTool>(true) != null),
                    () => "ville « " + scene + " » : scène active « " + SceneManager.GetActiveScene().name + " »"); e.MoveNext();) yield return null;
                Scene ville = SceneManager.GetActiveScene();
                DesertRoadTool outil = Unique<DesertRoadTool>(ville, "ville « " + scene + " »"); PanneauLieu panneau = Unique<PanneauLieu>(ville, "ville « " + scene + " »");
                for (double fin = Time.realtimeSinceStartupAsDouble + ATTENTE_S; !(outil.TickOuverture >= 0 && panneau.Reconstructions > 0);)
                {
                    if (Time.realtimeSinceStartupAsDouble > fin)
                    {
                        r.cellule = outil.Cellule; r.panneau_lieu = (panneau.TexteAffiche ?? "").Split('\n')[0];
                        throw new InvalidOperationException("ville « " + scene + " » : plan ou lieu non lu en " + ATTENTE_S + " s : « " + outil.Message + " »");
                    }
                    yield return null;
                }
                r.cellule = outil.Cellule; r.tick_ouverture = outil.TickOuverture; r.panneau_lieu = (panneau.TexteAffiche ?? "").Split('\n')[0];
            }

            // `/monde` relu après coup : son tick, ou -1 s'il est absent.
            Task<Lecture<MondeAvecMaisonLu>> monde = Lot690.LireMonde(port);
            for (var e = Lot690.Jusqua(() => monde.IsCompleted, () => "lecture /monde après le tick"); e.MoveNext();) yield return null;
            r.tick_apres = monde.Status == TaskStatus.RanToCompletion && monde.Result != null && monde.Result.Presente ? monde.Result.Donnees.Monde.Tick : -1;
        }
    }
}
