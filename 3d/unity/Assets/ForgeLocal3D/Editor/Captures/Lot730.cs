using System;
using System.Collections;
using System.Linq;
using System.Threading.Tasks;
using Forge.Pont;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures {
    // Lot 730 : Espace suspend ou reprend la ville, C revient à la carte par le vrai fondu.
    // Les touches passent par le système d'entrée ; `automatique` les ignore. La capture a déjà son service, en pause.
    static class Lot730 {
        const double ATTENTE_S = 20, IMMOBILE_S = 1;
        const int IMAGES = 8;
        const string CARTE = "C : carte", PAUSE = "Espace : pause / reprendre";
        static Frappe frappe;

        [ScenarioDeCapture(730, "01-ville-et-aide")]
        static IEnumerator VilleEtAide(Camera camera) {
            DesertRoadTool outil = Outil(); DesertCityCamera ville = camera.GetComponent<DesertCityCamera>() ?? Object.FindFirstObjectByType<DesertCityCamera>() ?? throw new InvalidOperationException("pas de caméra de ville");
            int port = outil.Port; double reprise = ReglagesDesVues.Charger().VitesseVille;
            ville.VueEnsemble(); camera.aspect = Lot549.FORME; outil.Placer();
            outil.automatique = true;
            for (var e = Touche(Key.Space, 6); e.MoveNext();) yield return null;
            for (var e = Touche(Key.C, 6); e.MoveNext();) yield return null;
            for (var e = Secondes(IMMOBILE_S); e.MoveNext();) yield return null;
            if (Object.FindFirstObjectByType<TransitionDeVue>() != null) throw new InvalidOperationException("automatique : C a lancé une transition");
            Lecture<HorlogeLue> ignoree = null; for (var e = Lire(port, l => ignoree = l, "horloge ignorée"); e.MoveNext();) yield return null;
            if (ignoree.Donnees.JoursParSeconde != 0) throw new InvalidOperationException("automatique : Espace a quitté la pause (" + ignoree.Donnees.JoursParSeconde + ")");
            outil.automatique = false;
            Exiger(Panneau(camera), "route");
            if (!outil.Rafraichir()) throw new InvalidOperationException("rafraîchissement refusé : " + Panneau(camera));
            Exiger(Panneau(camera), "route après rafraîchissement");
            outil.EntrerParcelle(); Exiger(Panneau(camera), "parcelle");
            outil.EntrerBatiment(PoseDeBatiment.Natures[0]); Exiger(Panneau(camera), "bâtiment");
            outil.Annuler(); Exiger(Panneau(camera), "retour route");
            for (var e = JusquaVitesse(Key.Space, port, reprise, "reprise"); e.MoveNext();) yield return null;
            for (var e = JusquaVitesse(Key.Space, port, 0, "pause"); e.MoveNext();) yield return null;
            Lecture<HorlogeLue> avant = null; for (var e = Lire(port, l => avant = l, "tick en pause"); e.MoveNext();) yield return null;
            for (var e = Secondes(IMMOBILE_S); e.MoveNext();) yield return null;
            Lecture<HorlogeLue> apres = null; for (var e = Lire(port, l => apres = l, "second tick en pause"); e.MoveNext();) yield return null;
            if (apres.Donnees.Tick != avant.Donnees.Tick || apres.Donnees.JoursParSeconde != 0)
                throw new InvalidOperationException("en pause, le tick passe de " + avant.Donnees.Tick + " à " + apres.Donnees.Tick + " (" + apres.Donnees.JoursParSeconde + ")");
            ville.VueEnsemble(); camera.aspect = Lot549.FORME; outil.Placer();
            for (int i = 0; i < IMAGES; i++) yield return null;
            Lisible(camera, PanneauMesh(camera));
        }

        [ScenarioDeCapture(730, "02-carte-apres-retour")]
        static IEnumerator CarteApresRetour(Camera camera) {
            DesertRoadTool outil = Outil(); int port = outil.Port;
            double carteV = ReglagesDesVues.Charger().VitesseCarte, villeV = ReglagesDesVues.Charger().VitesseVille;
            for (var e = JusquaVitesse(Key.Space, port, villeV, "reprise avant le retour"); e.MoveNext();) yield return null;
            Armer(Key.C);
            TransitionDeVue transition = null; double fin = Time.realtimeSinceStartupAsDouble + 5;
            while ((transition = Object.FindFirstObjectByType<TransitionDeVue>()) == null) {
                if (Time.realtimeSinceStartupAsDouble > fin) throw new InvalidOperationException("C n'a pas lancé de transition");
                yield return null;
            }
            if (transition.SceneChargee != null) throw new InvalidOperationException("la scène a chargé avant le branchement du fondu");
            AsyncOperation chargement = null; string demandee = null;
            transition.ChargerScene = nom => { demandee = nom; chargement = SceneManager.LoadSceneAsync(nom, LoadSceneMode.Additive) ?? throw new InvalidOperationException("« " + nom + " » ne se charge pas"); };
            Armer(null);
            fin = Time.realtimeSinceStartupAsDouble + ATTENTE_S;
            while (chargement == null || !chargement.isDone || (transition != null && transition.EnCours)) {
                if (Time.realtimeSinceStartupAsDouble > fin) throw new InvalidOperationException("fondu ou chargement inachevé : « " + demandee + " »");
                yield return null;
            }
            if (demandee != OuvertureDeLaCarte.SCENE) throw new InvalidOperationException("C a demandé « " + demandee + " »");
            Scene scene = SceneManager.GetSceneByName(demandee); SceneManager.SetActiveScene(scene); Ecarter(camera);
            CarteDessinee[] cartes = scene.GetRootGameObjects().SelectMany(r => r.GetComponentsInChildren<CarteDessinee>(true)).ToArray();
            if (cartes.Length != 1) throw new InvalidOperationException(cartes.Length + " cartes dans " + demandee);
            CarteDessinee carte = cartes[0];
            fin = Time.realtimeSinceStartupAsDouble + ATTENTE_S;
            while (carte.CellulesPosees != carte.CellulesServies || carte.CellulesPosees <= 0) {
                if (Time.realtimeSinceStartupAsDouble > fin) throw new InvalidOperationException(carte.CellulesPosees + " cellules posées pour " + carte.CellulesServies + " servies");
                yield return null;
            }
            HorlogeDeCarte horloge = carte.GetComponent<HorlogeDeCarte>() ?? throw new InvalidOperationException("la carte n'a pas d'horloge");
            Lecture<HorlogeLue> servie = null; fin = Time.realtimeSinceStartupAsDouble + ATTENTE_S;
            while (servie == null || !servie.Presente || !Meme(servie.Donnees.JoursParSeconde, carteV) || horloge.Lue == null || !Meme(horloge.Lue.JoursParSeconde, servie.Donnees.JoursParSeconde) || horloge.TexteAffiche != HorlogeDeCarte.Decrire(horloge.Lue)) {
                if (Time.realtimeSinceStartupAsDouble > fin) throw new InvalidOperationException("horloge « " + horloge.TexteAffiche + " », service " + (servie != null && servie.Presente ? servie.Donnees.JoursParSeconde.ToString() : servie?.Absence ?? "non lu"));
                for (var e = Lire(port, l => servie = l, "horloge de la carte"); e.MoveNext();) yield return null;
                yield return null;
            }
            var temps = carte.GetComponent<CommandesDuTemps>(); if (temps != null) temps.automatique = true;
            var parcours = carte.GetComponent<ParcoursDeCarte>(); if (parcours != null) parcours.automatique = true;
            var survol = carte.GetComponent<SurvolDeCarte>(); if (survol != null) survol.automatique = true;
            Lot549.Photographier(camera, carte);
            for (int i = 0; i < IMAGES; i++) yield return null;
            if (horloge.Lue == null || !Meme(horloge.Lue.JoursParSeconde, carteV) || horloge.TexteAffiche != HorlogeDeCarte.Decrire(horloge.Lue))
                throw new InvalidOperationException("après la pose, l'horloge dit « " + horloge.TexteAffiche + " »");
        }

        // En batch, la vue de jeu n'a pas le focus : les événements clavier restent dans l'éditeur.
        // La frappe est donc écrite dans l'état du joueur, au début de Update, avant l'outil.
        static void Armer(Key? touche) {
            if (frappe == null) frappe = new GameObject("Frappe").AddComponent<Frappe>();
            Frappe.tenue = touche; Frappe.armee = true;
        }
        static bool Meme(double a, double b) => Math.Abs(a - b) < 1e-6;
        static DesertRoadTool Outil() => Object.FindFirstObjectByType<DesertRoadTool>() ?? throw new InvalidOperationException("pas d'outil des routes");
        static IEnumerator Touche(Key touche, int images) {
            Armer(touche);
            for (int i = 0; i < images; i++) yield return null;
            Armer(null);
            yield return null;
        }
        static IEnumerator JusquaVitesse(Key touche, int port, double vitesse, string quoi) {
            Armer(touche);
            double fin = Time.realtimeSinceStartupAsDouble + ATTENTE_S; Lecture<HorlogeLue> lue = null;
            while (lue == null || !Meme(lue.Donnees.JoursParSeconde, vitesse)) {
                if (Time.realtimeSinceStartupAsDouble > fin) throw new InvalidOperationException(quoi + " : vitesse " + (lue == null ? "inconnue" : lue.Donnees.JoursParSeconde.ToString(System.Globalization.CultureInfo.InvariantCulture)) + ", attendue " + vitesse.ToString(System.Globalization.CultureInfo.InvariantCulture));
                for (var e = Lire(port, l => lue = l, quoi); e.MoveNext();) yield return null;
                yield return null;
            }
            Armer(null);
            yield return null;
        }
        static IEnumerator Lire(int port, Action<Lecture<HorlogeLue>> noter, string quoi) {
            Task<Lecture<HorlogeLue>> tache = Task.Run(() => { using (var c = new ClientHorloge(port, TimeSpan.FromSeconds(5))) return c.Lire(); });
            for (var e = Lot690.Attendre(tache, quoi); e.MoveNext();) yield return null;
            if (!tache.Result.Presente) throw new InvalidOperationException(quoi + " : " + tache.Result.Absence);
            noter(tache.Result);
        }
        static IEnumerator Secondes(double s) { for (double fin = Time.realtimeSinceStartupAsDouble + s; Time.realtimeSinceStartupAsDouble < fin;) yield return null; }
        static TextMesh PanneauMesh(Camera camera) {
            foreach (TextMesh t in camera.GetComponentsInChildren<TextMesh>(true)) if (t.name == "Panneau des routes") return t;
            throw new InvalidOperationException("panneau des routes absent");
        }
        static string Panneau(Camera camera) => PanneauMesh(camera).text;
        static void Exiger(string texte, string mode) {
            if (!texte.Contains(CARTE) || !texte.Contains(PAUSE)) throw new InvalidOperationException(mode + " : « " + texte.Replace("\n", " | ") + " »");
        }
        static void Lisible(Camera camera, TextMesh texte) {
            var r = texte.GetComponent<MeshRenderer>(); Bounds b = r.localBounds; Transform tr = texte.transform;
            Vector3 c = b.center, e = b.extents; string hors = null;
            Vector3[] coins = { new Vector3(c.x - e.x, c.y - e.y, c.z), new Vector3(c.x + e.x, c.y - e.y, c.z), new Vector3(c.x - e.x, c.y + e.y, c.z), new Vector3(c.x + e.x, c.y + e.y, c.z) };
            foreach (Vector3 coin in coins) {
                Vector3 v = camera.WorldToViewportPoint(tr.TransformPoint(coin));
                if (v.z <= 0f || v.x < -0.01f || v.x > 1.01f || v.y < -0.01f || v.y > 1.01f) hors = (hors ?? "") + " " + v.ToString("F3");
            }
            if (hors != null) throw new InvalidOperationException("aide coupée" + hors + " : « " + texte.text.Replace("\n", " | ") + " »");
        }
        static void Ecarter(Camera camera) {
            foreach (GameObject racine in camera.gameObject.scene.GetRootGameObjects()) Ecarter(racine.transform, camera.transform);
            var ville = camera.GetComponent<DesertCityCamera>(); if (ville != null) ville.enabled = false;
            var visite = camera.GetComponent<VillageV2Visit>(); if (visite != null) visite.enabled = false;
        }
        static void Ecarter(Transform t, Transform camera) {
            if (t == camera) { foreach (Transform enfant in t) enfant.gameObject.SetActive(false); return; }
            if (!camera.IsChildOf(t)) { t.gameObject.SetActive(false); return; }
            foreach (Renderer r in t.GetComponents<Renderer>()) r.enabled = false;
            foreach (Transform enfant in t) Ecarter(enfant, camera);
        }
    }

    // Avant DesertRoadTool : la touche est dans l'état dynamique, visible par wasPressedThisFrame.
    [DefaultExecutionOrder(-10000)]
    sealed class Frappe : MonoBehaviour {
        public static Key? tenue;
        public static bool armee;
        void Update() {
            if (!armee) return;
            Keyboard k = Keyboard.current;
            if (k == null || !k.added) k = InputSystem.AddDevice<Keyboard>();
            if (!k.enabled) InputSystem.EnableDevice(k);
            k.MakeCurrent();
            InputState.Change(k, tenue is Key t ? new KeyboardState(t) : new KeyboardState(), InputUpdateType.Dynamic);
            armee = false;
        }
    }
}
