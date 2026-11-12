using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using Forge.Interface;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;

namespace ForgeLocal3D.Captures
{
    // Lot 1030 : le jeu se lance en observateur, avec la pause et cinq vitesses. Trois scénarios, joués dans l'ordre de leur nom, sur le même service (`-forgeServiceIa`, parti du
    // jour 1 : `-forgeTicks 0`), qui se passent leur état par des champs statiques (comme Lot860) :
    //   1. observateur-1-cinq-vitesses : la carte s'ouvre en pause, sans maison, « Vous observez le monde… » ; cinq appuis sur « Accélérer » allument les cinq marques une à une
    //      jusqu'à 10 jours par seconde, un sixième ne va pas plus loin, « Ralentir » en éteint une ; le tick du service tient 10 jours par seconde pendant 5 s ;
    //   2. observateur-2-pause : « Pause / Reprendre » met le monde en pause, le tick du service, de l'horloge et du monde lu sont le même et ne bougent plus ; `lot1030-observateur.json` les dit ;
    //   3. observateur-3-prendre-un-pays : en pause, au jour suivant, un clic sur la Morée et « Choisir cette maison » prennent le pays ; la reprise rend les 10 jours par seconde, la maison
    //      est posée au tick suivant ; une dernière pause.
    // Les phrases attendues et les paliers s'écrivent ici, en littéraux : ni `HorlogeDeCarte.PALIERS`, ni `Rang`, ni `CabinetDeCarte.OBSERVER` ne sont lus (`Decrire` est la date servie). Le service se lit à part,
    // hors du fil principal. Contre-épreuve : `-forge1030Fuite` pousse un tick pendant la pause (une pause qui laisserait filer un jour) : le scénario 2 échoue (« en pause, le tick du service passe de T à T+1 »).
    static class Lot1030
    {
        const string FUITE = "-forge1030Fuite", SIEGE = "Mistra", TERRE = "Despotat de Morée", RAPPORT = "lot1030-observateur.json";
        const string BANDEAU = "FORGE · Le cabinet", DATE = "Lecture de la date…", BARRE = "Lecture de la maison…", MAISON = "Lecture de la partie…", VITESSES = "Vitesses", MARQUE = "Vitesse ";
        const string TERRES = "Terres conseillées", APERCU = "Consultez une maison avant de vous engager.", CHOISIR_CETTE = "Choisir cette maison", PAUSE = "Pause / Reprendre", TICKS_ARG = "-forgeTicks";
        const string AUCUNE = "Aucune maison choisie", OBSERVER = "Vous observez le monde, sans maison.\nPrenez-en une quand vous voulez.";
        const int IMAGES_DE_POSE = 10, CRANS = 12; const float IMMOBILE_S = 2, TENUE_S = 3, RELECTURE_S = 0.25f;
        const double MESURE_S = 5, TENUE = 0.8, PLUS_RAPIDE = 10;
        static readonly double[] PALIERS = { 0.5, 1, 2, 5, 10 };
        static readonly CultureInfo Inv = CultureInfo.InvariantCulture;

        [Serializable] sealed class Rapport
        {
            public long tick_service, tick_horloge, tick_monde, jours_avances, jours_mesures; public double secondes_mesurees, vitesse_la_plus_rapide, budget_tick_ms; public string maison_du_joueur;
        }
        [Serializable] sealed class HorlogeBrute { public double budget_tick_ms; }

        static CarteDessinee carte; static CabinetDeCarte cabinet; static HorlogeDeCarte horloge; static Transform toile, bandeau, terres, vitesses; static Text barre, date, dossier;
        static int port; static HorlogeLue servie; static FicheDeDepart[] fiches; static long mesure0, mesure1, pause; static double budget;

        static string N(long v) => v.ToString(Inv); static string N(double v) => v.ToString("R", Inv); static bool Meme(double a, double b) => Math.Abs(a - b) < 1e-6;
        static InvalidOperationException Echec(string cause) => new InvalidOperationException(cause); static bool Drapeau(string d) => Environment.GetCommandLineArgs().Contains(d);
        static string Ecran(Vector2 p) => "(" + Mathf.RoundToInt(p.x) + ", " + Mathf.RoundToInt(p.y) + ")";
        static long Depart() { var a = Environment.GetCommandLineArgs(); int i = Array.IndexOf(a, TICKS_ARG); return i >= 0 && i + 1 < a.Length ? long.Parse(a[i + 1], Inv) : 0; }
        static Transform[] Allumees() => terres.Cast<Transform>().Where(t => t.gameObject.activeSelf).ToArray();
        static string Une(string texte) => (texte ?? "(aucun texte)").Replace("\n", " | ");

        [ScenarioDeCapture(1030, "observateur-1-cinq-vitesses")]
        static IEnumerator CinqVitesses(Camera camera)
        {
            // La carte s'ouvre comme à l'étape 1 de Lot860.
            var ouverte = new Lot549.CarteOuverte(); for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null;
            carte = ouverte.Carte; port = carte.port;
            cabinet = carte.GetComponent<CabinetDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de CabinetDeCarte");
            horloge = carte.GetComponent<HorlogeDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas d'horloge");
            (carte.GetComponent<SurvolDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de survol")).automatique = true; (carte.GetComponent<ParcoursDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de parcours")).automatique = true;
            toile = carte.transform.Find("Cabinet") ?? throw Echec("étape 1 : la toile du cabinet est introuvable"); bandeau = toile.Find(BANDEAU) ?? throw Echec("étape 1 : le bandeau « " + BANDEAU + " » est introuvable");
            for (var e = Lot690.Jusqua(() => Lot690.LecturePrete(cabinet.Partie) && horloge.Lue != null, () => "étape 1 : " + Lot690.Dire(cabinet.Partie) + ", horloge " + (horloge.Lue == null ? "non lue" : "lue")); e.MoveNext();) yield return null;
            fiches = cabinet.Partie.Departs.Donnees.Fiches.ToArray();
            Lot549.Photographier(camera, carte); camera.rect = new Rect(0f, 0f, 1f, 1f);
            var canvas = toile.GetComponent<Canvas>(); canvas.renderMode = RenderMode.ScreenSpaceCamera; canvas.worldCamera = camera; canvas.planeDistance = camera.nearClipPlane + 0.2f;
            yield return null; Canvas.ForceUpdateCanvases();
            date = bandeau.Find(DATE)?.GetComponent<Text>() ?? throw Echec("étape 1 : la date du bandeau est introuvable"); barre = bandeau.Find(BARRE)?.GetComponent<Text>() ?? throw Echec("étape 1 : la barre des comptes est introuvable");
            dossier = toile.GetComponentsInChildren<Text>(true).FirstOrDefault(t => t.name == MAISON) ?? throw Echec("étape 1 : le texte de « Votre maison » est introuvable");
            vitesses = bandeau.Find(VITESSES) ?? throw Echec("étape 1 : le conteneur « " + VITESSES + " » est introuvable dans le bandeau");
            terres = carte.transform.Find(TERRES) ?? throw Echec("étape 1 : la racine « " + TERRES + " » est introuvable, enfant direct de la carte");

            // L'ouverture en observateur.
            for (var e = Relire(); e.MoveNext();) yield return null;
            if (servie.Tick != 0 || Depart() != 0) throw Echec("à l'ouverture, le tick lu vaut " + N(servie.Tick) + ", attendu 0 (" + TICKS_ARG + " 0)");
            if (servie.JoursParSeconde != 0) throw Echec("à l'ouverture, le monde avance : " + N(servie.JoursParSeconde) + " jour(s) par seconde");
            if (cabinet.Partie.Monde.Donnees.MaisonDuJoueur != null) throw Echec("à l'ouverture, le monde a une maison du joueur : « " + cabinet.Partie.Monde.Donnees.MaisonDuJoueur + " »");
            if (barre.text != AUCUNE) throw Echec("à l'ouverture, la barre dit « " + Une(barre.text) + " », attendu « " + AUCUNE + " »");
            if (dossier.text != OBSERVER) throw Echec("à l'ouverture, « Votre maison » dit « " + Une(dossier.text) + " », attendu « " + Une(OBSERVER) + " »");
            JugerMarques(0, "à l'ouverture");

            // Cinq appuis sur « Accélérer » : le palier attendu est servi, puis lu par la carte, et les marques suivent.
            for (int k = 1; k <= 5; k++)
            {
                Commande("Accélérer").onClick.Invoke();
                for (var e = Servie(k, PALIERS[k - 1]); e.MoveNext();) yield return null;
                for (var e = Lue(k, PALIERS[k - 1]); e.MoveNext();) yield return null;
                JugerMarques(k, "après " + k + " appui(s)"); JugerDate("après " + k + " appui(s)");
            }
            Commande("Accélérer").onClick.Invoke(); for (var e = Secondes(2); e.MoveNext();) yield return null;
            for (var e = Relire(); e.MoveNext();) yield return null;
            if (!Meme(servie.JoursParSeconde, PLUS_RAPIDE)) throw Echec("au-delà de la plus rapide : " + N(servie.JoursParSeconde));
            for (var e = Lue(5, PLUS_RAPIDE); e.MoveNext();) yield return null;
            if (Rang() != 5) throw Echec("au-delà de la plus rapide : " + Rang() + " marque(s) allumée(s)");
            Commande("Ralentir").onClick.Invoke();
            for (var e = Servie(5, PALIERS[3]); e.MoveNext();) yield return null;
            for (var e = Lue(5, PALIERS[3]); e.MoveNext();) yield return null;
            JugerMarques(4, "après « Ralentir »");
            Commande("Accélérer").onClick.Invoke();
            for (var e = Servie(5, PLUS_RAPIDE); e.MoveNext();) yield return null;
            for (var e = Lue(5, PLUS_RAPIDE); e.MoveNext();) yield return null;
            JugerMarques(5, "après « Accélérer »");

            // La tenue : à 10 jours par seconde, au moins TENUE × 10 × MESURE_S jours en MESURE_S secondes de temps réel.
            for (var e = Secondes(2); e.MoveNext();) yield return null;
            for (var e = Relire(); e.MoveNext();) yield return null; mesure0 = servie.Tick;
            for (var e = Secondes(MESURE_S); e.MoveNext();) yield return null;
            for (var e = Relire(); e.MoveNext();) yield return null; mesure1 = servie.Tick;
            if (mesure1 - mesure0 < TENUE * PLUS_RAPIDE * MESURE_S) throw Echec("à 10 jours par seconde, " + N(mesure1 - mesure0) + " jours en " + N(MESURE_S) + " s : le tick ne tient pas la vitesse");
            if (cabinet.Partie.Monde.Donnees.MaisonDuJoueur != null) throw Echec("le monde a une maison du joueur : « " + cabinet.Partie.Monde.Donnees.MaisonDuJoueur + " »");

            // L'image est prise en marche, les six terres de départ en or, la carte cadrée sur elles.
            for (var e = Lot690.Jusqua(() => Allumees().Length == fiches.Length, () => "étape 3 : " + Allumees().Length + " surbrillance(s) active(s) pour " + fiches.Length + " fiche(s) servie(s)"); e.MoveNext();) yield return null;
            Cadrer(camera, Allumees().Select(t => t.GetComponent<MeshRenderer>().bounds.center)); yield return null; Canvas.ForceUpdateCanvases();
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            for (var e = Relire(); e.MoveNext();) yield return null;
            JugerMarques(5, "à la pose"); Trace("observateur-1-cinq-vitesses");
        }

        [ScenarioDeCapture(1030, "observateur-2-pause")]
        static IEnumerator Pause(Camera camera)
        {
            if (carte == null || vitesses == null) throw Echec("étape 1 : « observateur-1-cinq-vitesses » n'a pas ouvert la carte");
            Commande(PAUSE).onClick.Invoke();
            for (var e = Servie(0, 0); e.MoveNext();) yield return null;
            pause = servie.Tick;
            for (var e = Lot690.Jusqua(() => horloge.Lue != null && horloge.Lue.Tick == pause && Monde()?.Tick == pause,
                () => "étape 2 : tick servi " + N(pause) + ", horloge " + (horloge.Lue == null ? "non lue" : N(horloge.Lue.Tick)) + ", monde lu " + (Monde() == null ? "absent" : N(Monde().Tick))); e.MoveNext();) yield return null;
            if (pause < 40) throw Echec("étape 2 : le monde a avancé de " + N(pause) + " jour(s) seulement, au moins 40 attendus");
            if (Drapeau(FUITE)) // une pause qui laisserait filer un jour
            {
                var pousse = Lot690.PousserTick(port); for (var e = Lot690.Attendre(pousse, "POST /tick?n=1"); e.MoveNext();) yield return null;
                if (pousse.Result.statut != 200) throw Echec("POST /tick?n=1 refusé (" + pousse.Result.statut + ") : " + pousse.Result.corps);
            }

            // La pause tient : relu toutes les 0,25 s pendant TENUE_S secondes de temps réel.
            for (double fin = Time.realtimeSinceStartupAsDouble + TENUE_S; Time.realtimeSinceStartupAsDouble < fin;)
            {
                for (var e = Relire(); e.MoveNext();) yield return null;
                if (servie.Tick != pause) throw Echec("en pause, le tick du service passe de " + N(pause) + " à " + N(servie.Tick));
                JugerPause("en pause");
                for (var e = Secondes(RELECTURE_S); e.MoveNext();) yield return null;
            }

            // Le même tick : le service, l'horloge de la carte et le monde lu.
            for (var e = Relire(); e.MoveNext();) yield return null;
            long horlogeTick = horloge.Lue.Tick, mondeTick = Monde()?.Tick ?? -1;
            if (servie.Tick != pause || horlogeTick != pause || mondeTick != pause)
                throw Echec("en pause, le service dit le tick " + N(servie.Tick) + ", l'horloge " + N(horlogeTick) + ", le monde lu " + N(mondeTick) + " : attendu " + N(pause) + " partout");
            var lecture = Task.Run(() => { using (var c = new HttpClient { Timeout = TimeSpan.FromSeconds(5) }) return c.GetStringAsync("http://127.0.0.1:" + port + "/horloge").GetAwaiter().GetResult(); });
            for (var e = Lot690.Attendre(lecture, "lecture brute de /horloge"); e.MoveNext();) yield return null;
            budget = JsonUtility.FromJson<HorlogeBrute>(lecture.Result).budget_tick_ms; if (budget <= 0) throw Echec("/horloge ne sert pas de budget_tick_ms");
            File.WriteAllText(Path.Combine(Capture.DossierDesCaptures, RAPPORT), JsonUtility.ToJson(new Rapport
            {
                tick_service = servie.Tick, tick_horloge = horlogeTick, tick_monde = mondeTick, jours_avances = pause, jours_mesures = mesure1 - mesure0, secondes_mesurees = MESURE_S,
                vitesse_la_plus_rapide = PLUS_RAPIDE, budget_tick_ms = budget, maison_du_joueur = ""
            }, true), new UTF8Encoding(false));
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            JugerPause("à la pose"); Trace("observateur-2-pause");
        }

        [ScenarioDeCapture(1030, "observateur-3-prendre-un-pays")]
        static IEnumerator PrendreUnPays(Camera camera)
        {
            if (carte == null || vitesses == null || pause < 40) throw Echec("étape 1 : « observateur-2-pause » n'a pas mis le monde en pause");
            // Toujours en pause, au jour suivant : les départs sont ceux du jour courant.
            for (var e = Lot690.Jusqua(() => Lot690.LecturePrete(cabinet.Partie) && cabinet.Partie.Departs.Donnees.Tick == pause,
                () => "étape 1 : " + Lot690.Dire(cabinet.Partie) + ", départs au tick " + (cabinet.Partie.Departs?.Presente == true ? N(cabinet.Partie.Departs.Donnees.Tick) : "inconnu") + ", attendu " + N(pause)); e.MoveNext();) yield return null;
            fiches = cabinet.Partie.Departs.Donnees.Fiches.ToArray();
            FicheDeDepart[] mistra = fiches.Where(f => f.Siege.Nom == SIEGE).ToArray();
            if (mistra.Length != 1 || mistra[0].Nom != TERRE) throw Echec("au jour " + N(pause + 1) + ", fiches au siège " + SIEGE + " : " + string.Join(", ", mistra.Select(f => f.Nom)) + ", attendu « " + TERRE + " » seule");
            long cellule = mistra[0].CellId; var survol = carte.GetComponent<FicheDeCellule>() ?? throw Echec("étape 1 : la carte n'a pas de fiche de cellule");
            var lecture = Task.Run(() => { using (var c = new ClientLieu(port, ClientDeparts.DelaiMinimal)) return c.Lire(cellule); });
            for (var e = Lot690.Attendre(lecture, "étape 2 : lecture /lieu?cell=" + N(cellule)); e.MoveNext();) yield return null;
            if (!lecture.Result.Presente || !(lecture.Result.Lieu.Bourg?.Position is PointCarte position))
                throw Echec("étape 2 : /lieu?cell=" + N(cellule) + " sans point au rang 0 : " + (lecture.Result.Absence ?? lecture.Result.Lieu.AbsenceDesLieux ?? "rang 0 absent ou sans point"));
            Vector3 local = carte.PositionSurLaCarte(position, ReperesDeDepart.HAUTEUR_LIEU) ?? throw Echec("étape 2 : la carte ne place pas le point du lieu"); Vector3 point = carte.transform.TransformPoint(local);
            carte.Vue.Zoomer(CRANS, carte.camera.WorldToViewportPoint(point)); carte.Vue.Centrer(new Vector2(local.x, local.z), carte.Vue.Demi);
            yield return null; // la carte se recadre
            Vector2 P = carte.camera.WorldToScreenPoint(point); survol.Survoler(P); CelluleDeCarte vue = survol.Survolee; survol.Quitter();
            if (vue?.CellId != cellule || carte.CelluleSous(point)?.CellId != cellule) throw Echec("étape 2 : au point " + Ecran(P) + ", la carte voit la cellule " + vue?.CellId + ", attendu " + N(cellule));
            if (cabinet.HorsCarte(P)) throw Echec("étape 2 : le point de la terre " + Ecran(P) + " est hors de la carte ou sous un panneau");
            bool clic = Toucher(P, vue);
            for (int i = 0; i < 3; i++) yield return null; // le cabinet relit sa partie et écrit son aperçu
            if (!clic || cabinet.Retenue?.CellId != cellule) throw Echec("étape 3 : la terre " + N(cellule) + " n'est pas gardée après le clic : retenue " + (cabinet.Retenue?.CellId.ToString() ?? "nulle"));
            Text apercu = toile.GetComponentsInChildren<Text>(true).FirstOrDefault(t => t.name == APERCU) ?? throw Echec("étape 3 : l'aperçu de « Votre maison » est introuvable");
            Button confirmer = toile.GetComponentsInChildren<Button>(true).FirstOrDefault(b => b.name == CHOISIR_CETTE) ?? throw Echec("étape 3 : « " + CHOISIR_CETTE + " » est introuvable");
            if (!apercu.gameObject.activeInHierarchy || !apercu.text.StartsWith(TERRE + " · " + SIEGE, StringComparison.Ordinal) || !confirmer.gameObject.activeInHierarchy || !confirmer.interactable)
                throw Echec("aucune maison proposée après le clic sur la cellule " + N(cellule) + " : l'aperçu dit « " + Une(apercu.text) + " », « " + CHOISIR_CETTE + " » " + (confirmer.interactable ? "actif" : "inactif"));
            confirmer.onClick.Invoke();
            for (var e = Lot690.Jusqua(() => cabinet.Partie.Recu?.Acceptee == true, () => "étape 4 : reçu du choix " + (cabinet.Partie.Recu == null ? "absent" : cabinet.Partie.Recu.Presente ? "refusé : " + cabinet.Partie.Recu.Erreur : "perdu : " + cabinet.Partie.Recu.Absence)); e.MoveNext();) yield return null;

            // La reprise rend la vitesse du monde vu en marche : 10 jours par seconde.
            Commande(PAUSE).onClick.Invoke();
            HorlogeLue repris = null; for (var e = Servie(h => h.JoursParSeconde > 0 && (repris = h) != null, "étape 5 : reprise"); e.MoveNext();) yield return null;
            if (!Meme(repris.JoursParSeconde, PLUS_RAPIDE)) throw Echec("reprise à " + N(repris.JoursParSeconde) + " jours par seconde, attendu 10, la vitesse du monde vu en marche");
            for (var e = Lot690.Jusqua(() => cabinet.Partie.Monde?.Presente == true && cabinet.Partie.Monde.Donnees.MaisonDuJoueur != null && cabinet.Partie.Maison?.Presente == true && cabinet.Partie.Maison.Donnees.Siege.Nom == SIEGE,
                () => "étape 5 : maison du joueur « " + (cabinet.Partie.Monde?.Donnees?.MaisonDuJoueur ?? "aucune") + " », siège lu « " + (cabinet.Partie.Maison?.Presente == true ? cabinet.Partie.Maison.Donnees.Siege.Nom : "aucun") + " », attendu « " + SIEGE + " »"); e.MoveNext();) yield return null;
            for (int i = 0; i < 3; i++) yield return null;
            if (cabinet.Partie.Monde.Donnees.Monde.Tick <= pause) throw Echec("étape 5 : le tick du monde lu vaut " + N(cabinet.Partie.Monde.Donnees.Monde.Tick) + ", attendu plus que " + N(pause));
            if (barre.text == AUCUNE) throw Echec("étape 5 : la barre dit encore « " + AUCUNE + " »");
            if (dossier.text == OBSERVER) throw Echec("étape 5 : « Votre maison » dit encore l'observateur");

            Commande(PAUSE).onClick.Invoke();
            for (var e = Servie(0, 0); e.MoveNext();) yield return null;
            string nom = cabinet.Partie.Maison.Donnees.Nom ?? throw Echec("étape 6 : la maison du joueur n'a pas de nom servi"); // la barre rattrape le tick de la pause
            for (var e = Lot690.Jusqua(() => barre.text.StartsWith(nom, StringComparison.Ordinal) && !bandeau.GetComponentsInChildren<Text>().Any(t => t.text.Contains("en attente du monde")) && dossier.text.StartsWith(nom, StringComparison.Ordinal),
                () => "étape 6 : la barre dit « " + Une(barre.text) + " », « Votre maison » « " + Une(dossier.text) + " », attendu la maison « " + nom + " » et des jauges lues"); e.MoveNext();) yield return null;
            if (Allumees().Length != 0) throw Echec("étape 6 : " + Allumees().Length + " terre(s) encore en or, la maison est choisie");
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            for (var e = Relire(); e.MoveNext();) yield return null;
            JugerMarques(0, "à la fin"); Trace("observateur-3-prendre-un-pays");
        }

        static Button Commande(string nom) => bandeau.Cast<Transform>().FirstOrDefault(t => t.name == nom)?.GetComponent<Button>() ?? throw Echec("le bouton « " + nom + " » est introuvable, enfant direct du bandeau");
        static MondeLu Monde() => cabinet.Partie.Monde?.Presente == true ? cabinet.Partie.Monde.Donnees.Monde : null;

        static Color32 Teinte(string hex) => ColorUtility.TryParseHtmlString(hex, out Color brut) ? (Color32)brut : throw Echec("couleur " + hex + " illisible");
        // Les marques allumées, comptées sur la couleur de chacune : or (#B49A61) allumée, secondaire (#625548) éteinte, rien d'autre.
        static int Rang()
        {
            Color32 or = Teinte("#B49A61"), eteinte = Teinte("#625548"); int allumees = 0;
            for (int i = 1; i <= 5; i++)
            {
                var image = vitesses.Find(MARQUE + i)?.GetComponent<Image>() ?? throw Echec("la marque « " + MARQUE + i + " » est introuvable");
                Color32 c = image.color; if (c.Equals(or)) allumees++; else if (!c.Equals(eteinte)) throw Echec("la marque « " + MARQUE + i + " » est de couleur " + c + ", ni l'or ni le secondaire");
            }
            return allumees;
        }
        // Les k premières en or, les autres éteintes, le conteneur actif.
        static void JugerMarques(int k, string quand)
        {
            if (!vitesses.gameObject.activeInHierarchy) throw Echec(quand + " : le conteneur « " + VITESSES + " » est inactif");
            if (vitesses.childCount != 5) throw Echec(quand + " : le conteneur porte " + vitesses.childCount + " marque(s), attendu 5");
            Color32 or = Teinte("#B49A61");
            for (int i = 1; i <= 5; i++)
            {
                bool allumee = vitesses.Find(MARQUE + i).GetComponent<Image>().color.Equals(or);
                if (allumee != (i <= k)) throw Echec(quand + " : la marque " + i + " est " + (allumee ? "allumée" : "éteinte") + ", attendu " + k + " marque(s) allumée(s) de la plus basse à la plus haute");
            }
        }
        static void JugerDate(string quand)
        {
            string attendue = HorlogeDeCarte.Decrire(horloge.Lue);
            if (date.text != attendue) throw Echec(quand + " : la date dit « " + Une(date.text) + " », attendu « " + Une(attendue) + " »");
        }
        // Le monde en pause : la date, le bouton et les marques le disent, et le tick lu par la carte est celui du service.
        static void JugerPause(string quand)
        {
            if (horloge.Lue.Tick != pause) throw Echec(quand + " : le tick de l'horloge passe de " + N(pause) + " à " + N(horloge.Lue.Tick));
            if (!date.text.EndsWith("En pause", StringComparison.Ordinal)) throw Echec(quand + " : la date dit « " + Une(date.text) + " », attendu « … En pause »");
            string bouton = Commande(PAUSE).GetComponentInChildren<Text>()?.text ?? "(bouton sans texte)"; if (bouton != "Reprendre") throw Echec(quand + " : le bouton dit « " + bouton + " », attendu « Reprendre »");
            JugerMarques(0, quand);
        }

        // Le service sert la vitesse attendue : la dernière lue dit pourquoi, quand elle ne vient pas.
        static IEnumerator Servie(int appuis, double attendue) => Servie(h => Meme(h.JoursParSeconde, attendue), "après " + appuis + " appuis, le service sert", attendue);
        static IEnumerator Servie(Func<HorlogeLue, bool> voulue, string quoi, double? attendue = null)
        {
            Task<Lecture<HorlogeLue>> t = null; string vu = "rien";
            return Lot690.Jusqua(() =>
            {
                if (t != null && t.IsCompleted && t.Result.Presente) { vu = N(t.Result.Donnees.JoursParSeconde); if (voulue(t.Result.Donnees)) { servie = t.Result.Donnees; return true; } }
                if (t == null || t.IsCompleted) t = Task.Run(() => { using (var c = new ClientHorloge(port, TimeSpan.FromSeconds(5))) return c.Lire(); });
                return false;
            }, () => attendue == null ? quoi + " : vitesse " + vu : quoi + " " + vu + ", attendu " + N(attendue.Value));
        }
        // La carte lit la vitesse servie : `horloge.Lue`, puis quelques images pour que le bandeau la dise.
        static IEnumerator Lue(int appuis, double attendue)
        {
            for (var e = Lot690.Jusqua(() => horloge.Lue != null && Meme(horloge.Lue.JoursParSeconde, attendue), () => "après " + appuis + " appuis, la carte lit " + (horloge.Lue == null ? "rien" : N(horloge.Lue.JoursParSeconde)) + ", attendu " + N(attendue)); e.MoveNext();) yield return null;
            for (int i = 0; i < 3; i++) yield return null;
        }

        // Une lecture de /horloge, hors du fil principal : `servie`.
        static IEnumerator Relire()
        {
            var t = Task.Run(() => { using (var c = new ClientHorloge(port, TimeSpan.FromSeconds(5))) return c.Lire(); });
            for (var e = Lot690.Attendre(t, "lecture /horloge"); e.MoveNext();) yield return null;
            if (!t.Result.Presente) throw Echec("/horloge absente : " + t.Result.Absence);
            servie = t.Result.Donnees;
        }
        static IEnumerator Secondes(double s) { double fin = Time.realtimeSinceStartupAsDouble + s; return Lot690.Jusqua(() => Time.realtimeSinceStartupAsDouble >= fin, () => "attente"); }

        // Le centre des terres dans la bande libre de la vue de la carte (à gauche du cabinet, sous le bandeau), avec une marge ; la caméra de la photo, de dessus, nord en haut.
        static void Cadrer(Camera camera, IEnumerable<Vector3> centres)
        {
            const float X0 = .03f, X1 = .64f, Y0 = .04f, Y1 = .8f, MARGE_KM = 90f;
            Vector3[] p = centres.Select(carte.transform.InverseTransformPoint).ToArray(); float minX = p.Min(q => q.x) - MARGE_KM, maxX = p.Max(q => q.x) + MARGE_KM, minZ = p.Min(q => q.z) - MARGE_KM, maxZ = p.Max(q => q.z) + MARGE_KM;
            float demi = Mathf.Max((maxX - minX) / (2f * Lot549.FORME * (X1 - X0)), (maxZ - minZ) / (2f * (Y1 - Y0)));
            float x = (minX + maxX) / 2f - ((X0 + X1) / 2f - .5f) * 2f * demi * Lot549.FORME, z = (minZ + maxZ) / 2f - ((Y0 + Y1) / 2f - .5f) * 2f * demi;
            camera.transform.SetPositionAndRotation(carte.transform.TransformPoint(new Vector3(x, CarteDessinee.HAUTEUR_CAMERA, z)), Quaternion.Euler(90, 0, 0)); camera.orthographicSize = demi;
        }

        // Le geste de Lot855 : appui, relâché, comme Update ; HorsCarte n'est calculé qu'à l'appui et au relâché.
        static bool Toucher(Vector2 ici, CelluleDeCarte sous)
            => cabinet.Noter(ici, true, false, cabinet.HorsCarte(ici), sous) | cabinet.Noter(ici, false, false, false, sous) | cabinet.Noter(ici, false, true, cabinet.HorsCarte(ici), sous);

        static void Trace(string nom)
        {
            var monde = cabinet.Partie.Monde; string id = monde?.Presente == true ? monde.Donnees.MaisonDuJoueur : null;
            string maison = id == null ? "aucune" : cabinet.Partie.Maison?.Presente == true && cabinet.Partie.Maison.Donnees.Nom != null ? cabinet.Partie.Maison.Donnees.Nom : id;
            Debug.Log("CAPTURE_1030 " + nom + " tick " + N(servie.Tick) + ", vitesse " + N(servie.JoursParSeconde) + ", marques allumées " + Rang() + ", maison « " + maison + " »");
        }
    }
}
