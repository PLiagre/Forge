using System;
using System.Collections;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Threading.Tasks;
using Forge.Interface;
using Forge.Pont;
using ForgeLocal3D.Captures;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

namespace ForgeLocal3D
{
    // Lot 659 : la session Unity de l'épreuve de la part, moitié Unity du geste déjà visible dans #656.
    //   Unity -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.EpreuvePart.Jouer
    //         -forgeEpreuve <rapport.json> -forgeTerre N [-forgePart P] [-forgePartSansConfirmation]
    // Le service tourne déjà, en pause. La session ne le lance ni ne l'arrête, ne touche pas /vitesse, et ne juge rien :
    // un refus de part reste un relevé, puis les trente ticks ont lieu quand même. `-forgePartSansConfirmation` omet
    // seulement le clic final. Codes : 0 observations finies ; 1 session impossible ; 2 arguments, sans rapport.
    [InitializeOnLoad]
    public static class EpreuvePart
    {
        const string Flag = "Forge.Part.Epreuve", CleRapport = Flag + ".Rapport", CleTerre = Flag + ".Terre", ClePart = Flag + ".Part", CleSortie = Flag + ".Sortie";
        const string RAPPORT = "-forgeEpreuve", TERRE = "-forgeTerre", PART = "-forgePart", SANS = "-forgePartSansConfirmation", CONFIRMER = "Confirmer l\u2019ordre";
        const double ATTENTE_S = 30, VIDANGE_S = 12, PERIODE_COMPTES_S = 2; // la vidange : sans service, Unity pend sinon à « Cleanup mono »
        const int TICKS = 30, DEFAUT = 50, MAX = 60;

        [Serializable] public class Rapport
        {
            public long terre = -1, tick_avant = -1, tick_apres_choix = -1, tick_apres = -1;
            public int part_demandee_pct = -1, curseur_pct = -1, ticks_part = -1, maison_statut = -1;
            public string maison = "", intention_json = "", message_ordre = "", panneau = "", maison_json = "", defaut = "";
            public EpreuveChoix.Recu choix = new EpreuveChoix.Recu(), ordre = new EpreuveChoix.Recu();
        }

        static IEnumerator enCours; static Rapport rapport; static int derniere = -1; static double vidange;
        static EpreuvePart() { EditorApplication.update += Tick; }
        static string N(long v) => v.ToString(CultureInfo.InvariantCulture);

        public static void Jouer()
        {
            string chemin = EpreuveChoix.Argument(RAPPORT), erreur = null;
            if (string.IsNullOrEmpty(chemin) || chemin.StartsWith("-")) erreur = RAPPORT + " <rapport.json> manque";
            long? terre = erreur != null ? null : EpreuveChoix.Terre(TERRE, out erreur);
            int? part = erreur != null ? null : Part(out erreur);
            if (erreur != null) { Dire(2, erreur); return; }
            string complet = Path.GetFullPath(Path.Combine(EpreuveChoix.DossierDeLancement(), chemin));
            try { string dossier = Path.GetDirectoryName(complet); if (!string.IsNullOrEmpty(dossier)) Directory.CreateDirectory(dossier); }
            catch (Exception e) { Dire(1, "dossier du rapport : " + e.Message); return; }
            SessionState.SetString(CleRapport, complet);
            SessionState.SetString(CleTerre, terre.Value.ToString(CultureInfo.InvariantCulture));
            SessionState.SetString(ClePart, part.Value.ToString(CultureInfo.InvariantCulture));
            EditorSceneManager.OpenScene(CarteBuilder.Chemin); SessionState.SetBool(Flag, true); EditorApplication.EnterPlaymode();
        }

        // Absente : 50, le défaut du curseur. Présente sans entier de 0 à 60 : ce n'est pas une absence, c'est une faute.
        static int? Part(out string erreur)
        {
            erreur = null; string[] a = Environment.GetCommandLineArgs(); int i = Array.IndexOf(a, PART);
            if (i < 0) return DEFAUT;
            if (i + 1 >= a.Length || a[i + 1].StartsWith("-")) { erreur = PART + " : valeur absente"; return null; }
            if (!int.TryParse(a[i + 1], NumberStyles.None, CultureInfo.InvariantCulture, out int p) || p < 0 || p > MAX)
            { erreur = PART + " : attendu un entier de 0 à " + MAX + ", reçu « " + a[i + 1] + " »"; return null; }
            return p;
        }

        static void Dire(int code, string message) { Debug.LogError("EPREUVE_PART : " + message); EditorApplication.Exit(code); }

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
            if (enCours == null)
            {
                rapport = new Rapport {
                    terre = long.Parse(SessionState.GetString(CleTerre, "-1"), CultureInfo.InvariantCulture),
                    part_demandee_pct = int.Parse(SessionState.GetString(ClePart, "-1"), CultureInfo.InvariantCulture),
                };
                enCours = Seance(rapport);
            }
            try { if (enCours.MoveNext()) return; }
            catch (Exception e) { Debug.LogException(e); if (rapport.defaut == "") rapport.defaut = e.GetBaseException().Message; }
            int code = rapport.defaut == "" ? 0 : 1; SessionState.SetBool(Flag, false); enCours = null;
            try
            {
                string chemin = SessionState.GetString(CleRapport, "");
                File.WriteAllText(chemin, JsonUtility.ToJson(rapport, true));
                Debug.Log("EPREUVE_PART " + chemin + " : terre " + N(rapport.terre) + ", part " + rapport.part_demandee_pct + ", curseur " + rapport.curseur_pct
                    + ", ticks " + N(rapport.tick_avant) + "/" + N(rapport.tick_apres_choix) + "/" + N(rapport.tick_apres) + " (" + rapport.ticks_part + ")"
                    + ", choix " + rapport.choix.statut + ", ordre " + rapport.ordre.statut + (code == 0 ? "" : " ; défaut : " + rapport.defaut));
            }
            catch (Exception e) { Debug.LogException(e); code = 1; }
            SessionState.SetInt(CleSortie, code); EditorApplication.ExitPlaymode();
        }

        static IEnumerator Seance(Rapport r)
        {
            CarteDessinee[] cartes = UnityEngine.Object.FindObjectsByType<CarteDessinee>(FindObjectsSortMode.None);
            if (cartes.Length != 1) throw new InvalidOperationException("CarteDessinee : attendu 1, observé " + cartes.Length);
            CarteDessinee carte = cartes[0]; int port = carte.port; Transform toile = null, racine = null;
            for (var e = Lot690.Jusqua(() => { toile = carte.transform.Find("Cabinet"); racine = toile != null ? toile.Find("Votre maison/Commandes de maison") : null; return carte.GetComponents<PassageALaCapitale>().Length == 1 && carte.GetComponent<CabinetDeCarte>() != null && carte.GetComponent<CommandesMaison>() != null && racine != null; },
                () => "carte incomplète, scène " + SceneManager.GetActiveScene().name); e.MoveNext();) yield return null;
            // Cette session seule reste sur la carte, même au Zab. Le passage livré au joueur n'est pas modifié.
            carte.GetComponent<PassageALaCapitale>().enabled = false;
            CabinetDeCarte cabinet = carte.GetComponent<CabinetDeCarte>(); CommandesMaison commandes = carte.GetComponent<CommandesMaison>();
            for (var e = Lot690.Jusqua(() => Lot690.LecturePrete(cabinet.Partie), () => "cabinet : " + Lot690.Dire(cabinet.Partie)); e.MoveNext();) yield return null;
            LecturePartie partie = cabinet.Partie; r.tick_avant = partie.Monde.Donnees.Monde.Tick;
            FicheDeDepart fiche = partie.Departs.Donnees.Fiches.FirstOrDefault(f => f.Id == r.terre) ?? throw new InvalidOperationException("terre " + N(r.terre) + " absente des fiches servies");
            for (var e = Lot690.Jusqua(() => Actif(toile, fiche.Maison), () => "bouton « " + fiche.Maison + " » inactif"); e.MoveNext();) yield return null;
            Bouton(toile, fiche.Maison).onClick.Invoke(); yield return null;
            Button choisir = Bouton(toile, "Choisir cette maison");
            if (!choisir.interactable) throw new InvalidOperationException("« Choisir cette maison » inactif pour " + fiche.Nom);
            choisir.onClick.Invoke();
            for (var e = Lot690.Jusqua(() => partie.Recu != null, () => "reçu du choix absent"); e.MoveNext();) yield return null;
            r.choix = EpreuveChoix.Relever(partie.Recu);
            if (!partie.Recu.Acceptee) throw new InvalidOperationException("choix de " + fiche.Nom + " refusé : " + r.choix.raison);
            Task<(int statut, string corps)> un = Lot690.PousserTick(port);
            for (var e = Lot690.Attendre(un, "POST /tick?n=1"); e.MoveNext();) yield return null;
            if (un.Result.statut != 200) throw new InvalidOperationException("POST /tick?n=1 a rendu " + un.Result.statut + " : " + un.Result.corps);
            for (var e = Lot690.Jusqua(() => Publiee(partie) && Actif(racine, "Prélèvement") && SceneManager.GetActiveScene().name == OuvertureDeLaCarte.SCENE,
                () => "maison ou commandes indisponibles, scène " + SceneManager.GetActiveScene().name + " : " + (partie.Maison == null ? "maison non lue" : partie.Maison.Absence ?? partie.Monde?.Donnees.MaisonDuJoueur ?? "absente")); e.MoveNext();) yield return null;
            Task<Lecture<MondeAvecMaisonLu>> apresChoix = Lot690.LireMonde(port);
            for (var e = Lot690.Attendre(apresChoix, "lecture /monde après le choix"); e.MoveNext();) yield return null;
            if (apresChoix.Result == null || !apresChoix.Result.Presente || string.IsNullOrEmpty(apresChoix.Result.Donnees.MaisonDuJoueur))
                throw new InvalidOperationException("maison non publiée : " + (apresChoix.Result == null ? "aucune lecture" : apresChoix.Result.Absence));
            r.tick_apres_choix = apresChoix.Result.Donnees.Monde.Tick; r.maison = apresChoix.Result.Donnees.MaisonDuJoueur;
            Bouton(racine, "Prélèvement").onClick.Invoke(); yield return null;
            Slider curseur = racine.GetComponentInChildren<Slider>();
            if (curseur == null || !curseur.gameObject.activeInHierarchy) throw new InvalidOperationException("curseur de part inactif");
            curseur.value = r.part_demandee_pct; yield return null; r.curseur_pct = Mathf.RoundToInt(curseur.value);
            Bouton(racine, "Préparer").onClick.Invoke(); yield return null;
            if (string.IsNullOrEmpty(commandes.Ordre.Brouillon)) throw new InvalidOperationException("brouillon absent : « " + commandes.MessageAffiche + " »");
            r.intention_json = commandes.Ordre.Brouillon;
            if (!Environment.GetCommandLineArgs().Contains(SANS))
            {
                Bouton(racine, CONFIRMER).onClick.Invoke();
                for (var e = Lot690.Jusqua(() => commandes.Ordre.Recu != null && !commandes.Ordre.EnCours, () => "reçu de part absent : « " + commandes.MessageAffiche + " »"); e.MoveNext();) yield return null;
                yield return null;
            }
            r.ordre = EpreuveChoix.Relever(commandes.Ordre.Recu); r.message_ordre = commandes.MessageAffiche ?? "";
            r.ticks_part = 0; Task<(int faits, string echec)> boucle = Task.Run(() => Pousser(port, TICKS));
            for (var e = Lot690.Attendre(boucle, "trente ticks"); e.MoveNext();) yield return null;
            r.ticks_part = boucle.Result.faits;
            if (boucle.Result.echec != null) throw new InvalidOperationException(boucle.Result.echec);
            Task<Lecture<MondeAvecMaisonLu>> fini = Lot690.LireMonde(port);
            for (var e = Lot690.Attendre(fini, "lecture /monde après la part"); e.MoveNext();) yield return null;
            if (fini.Result == null || !fini.Result.Presente) throw new InvalidOperationException("/monde après la part : " + (fini.Result == null ? "aucune lecture" : fini.Result.Absence));
            r.tick_apres = fini.Result.Donnees.Monde.Tick; string marque = "tick " + N(r.tick_apres) + "\n"; Text releve = null;
            for (double fin = Time.realtimeSinceStartupAsDouble + 2 * PERIODE_COMPTES_S; Time.realtimeSinceStartupAsDouble < fin;)
            { releve = Releve(racine); if (releve != null && releve.text != null && releve.text.Contains(marque)) break; yield return null; }
            r.panneau = releve != null && releve.text != null ? releve.text : "";
            Task<(int statut, string corps, string panne)> lu = Task.Run(() => CorpsMaison(port, r.maison));
            for (var e = Lot690.Jusqua(() => lu.IsCompleted, () => "GET /maison?id=" + r.maison); e.MoveNext();) yield return null;
            if (lu.Result.panne != null) { r.defaut = lu.Result.panne; yield break; }
            r.maison_statut = lu.Result.statut; r.maison_json = lu.Result.corps ?? "";
        }

        static bool Publiee(LecturePartie p) => p.Monde != null && p.Monde.Presente && !string.IsNullOrEmpty(p.Monde.Donnees.MaisonDuJoueur) && p.Maison != null && p.Maison.Presente && p.Maison.Donnees.Id == p.Monde.Donnees.MaisonDuJoueur;
        static bool Actif(Transform racine, string nom) { Button b = Trouver(racine, nom); return b != null && b.interactable; }
        static Button Bouton(Transform racine, string nom) => Trouver(racine, nom) ?? throw new InvalidOperationException("bouton « " + nom + " » absent");
        static Button Trouver(Transform racine, string nom)
        {
            Button[] t = racine.GetComponentsInChildren<Button>(true).Where(b => b.name == nom).ToArray();
            if (t.Length > 1) throw new InvalidOperationException(t.Length + " boutons « " + nom + " »");
            return t.Length == 1 ? t[0] : null;
        }
        static Text Releve(Transform racine)
        {
            Text[] t = racine.GetComponentsInChildren<Text>(true);
            return t.FirstOrDefault(x => x.name == "Lecture des réserves\u2026") ?? t.FirstOrDefault(x => x.text != null && x.text.StartsWith("Prélèvement :"));
        }
        // Un 200 dont le corps nomme un tick confirme l'exécution. Les autres s'arrêtent, sans les compter.
        static (int faits, string echec) Pousser(int port, int nombre)
        {
            int faits = 0;
            for (int i = 0; i < nombre; i++)
            {
                try
                {
                    var rep = Lot690.PousserTick(port).GetAwaiter().GetResult();
                    if (rep.statut != 200 || rep.corps.IndexOf("\"tick\":", StringComparison.Ordinal) < 0)
                        return (faits, "POST /tick?n=1 a rendu " + rep.statut + " : " + rep.corps);
                }
                catch (Exception e) { return (faits, "POST /tick?n=1 : " + e.GetBaseException().Message); }
                faits++;
            }
            return (faits, null);
        }
        // Le corps intégral. Une coupure garde le statut -1 et sa cause, jamais un panier inventé.
        static (int statut, string corps, string panne) CorpsMaison(int port, string id)
        {
            try
            {
                using (var http = new HttpClient { Timeout = TimeSpan.FromSeconds(ATTENTE_S) })
                using (var reponse = http.GetAsync("http://127.0.0.1:" + port + "/maison?id=" + Uri.EscapeDataString(id)).GetAwaiter().GetResult())
                {
                    byte[] octets = reponse.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult();
                    return ((int)reponse.StatusCode, System.Text.Encoding.UTF8.GetString(octets), null);
                }
            }
            catch (Exception e) { return (-1, "", "GET /maison?id=" + id + " : " + e.GetBaseException().Message); }
        }
    }
}
