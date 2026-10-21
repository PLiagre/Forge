using System;
using System.Collections;
using System.Linq;
using System.Threading.Tasks;
using Forge.Pont;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;
using UnityEngine.SceneManagement;
using UnityEngine.UI;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures {
    // Lot 730 : Espace suspend ou reprend la ville, C revient à la carte par le vrai fondu.
    // Les touches passent par le système d'entrée ; `automatique` les ignore. La capture a déjà son service, en pause.
    // Chaque attente passe par `Lot690.Jusqua`, bornée, et lève en disant ce qui manque.
    static class Lot730 {
        const string CARTE = "C : carte", PAUSE = "Espace : pause / reprendre";
        static Frappe frappe;

        [ScenarioDeCapture(730, "01-ville-et-aide")]
        static IEnumerator VilleEtAide(Camera camera) {
            DesertRoadTool outil = Outil(); int port = outil.Port; HorlogeLue lue = null, avant = null;
            DesertCityCamera ville = camera.GetComponent<DesertCityCamera>() ?? Object.FindFirstObjectByType<DesertCityCamera>() ?? throw new InvalidOperationException("pas de caméra de ville");
            ville.VueEnsemble(); camera.aspect = Lot549.FORME; outil.Placer(); outil.automatique = true;
            foreach (Key touche in new[] { Key.Space, Key.C }) for (var e = Touche(touche, null); e.MoveNext();) yield return null;
            for (var e = Secondes(1); e.MoveNext();) yield return null;
            if (Object.FindFirstObjectByType<TransitionDeVue>() != null) throw new InvalidOperationException("automatique : C a lancé une transition");
            for (var e = Servie(port, h => (lue = h) != null, "horloge ignorée"); e.MoveNext();) yield return null;
            if (lue.JoursParSeconde != 0) throw new InvalidOperationException("automatique : Espace a quitté la pause (" + lue.JoursParSeconde + ")");
            outil.automatique = false; Exiger(camera, "route");
            if (!outil.Rafraichir()) throw new InvalidOperationException("rafraîchissement refusé : " + Panneau(camera).text);
            Exiger(camera, "route après rafraîchissement");
            outil.EntrerParcelle(); Exiger(camera, "parcelle");
            outil.EntrerBatiment(PoseDeBatiment.Natures[0]); Exiger(camera, "bâtiment");
            outil.Annuler(); Exiger(camera, "retour route");
            for (var e = Touche(Key.Space, Servie(port, h => Meme(h.JoursParSeconde, ReglagesDesVues.Charger().VitesseVille), "reprise")); e.MoveNext();) yield return null;
            for (var e = Touche(Key.Space, Servie(port, h => h.JoursParSeconde == 0 && (avant = h) != null, "pause")); e.MoveNext();) yield return null;
            for (var e = Secondes(1); e.MoveNext();) yield return null;
            for (var e = Servie(port, h => (lue = h) != null, "second tick en pause"); e.MoveNext();) yield return null;
            if (lue.Tick != avant.Tick || lue.JoursParSeconde != 0) throw new InvalidOperationException("en pause, le tick passe de " + avant.Tick + " à " + lue.Tick + " (" + lue.JoursParSeconde + ")");
            ville.VueEnsemble(); camera.aspect = Lot549.FORME; outil.Placer();
            for (int i = 0; i < 8; i++) yield return null;
            Lisible(camera, Panneau(camera));
        }

        [ScenarioDeCapture(730, "02-carte-apres-retour")]
        static IEnumerator CarteApresRetour(Camera camera) {
            int port = Outil().Port; var reglages = ReglagesDesVues.Charger(); TransitionDeVue transition = null; AsyncOperation chargement = null; string demandee = null;
            for (var e = Touche(Key.Space, Servie(port, h => Meme(h.JoursParSeconde, reglages.VitesseVille), "reprise avant le retour")); e.MoveNext();) yield return null;
            Armer(Key.C);
            for (var e = Lot690.Jusqua(() => (transition = Object.FindFirstObjectByType<TransitionDeVue>()) != null, () => "C n'a pas lancé de transition"); e.MoveNext();) yield return null;
            if (transition.SceneChargee != null) throw new InvalidOperationException("la scène a chargé avant le branchement du fondu");
            transition.ChargerScene = nom => { demandee = nom; chargement = SceneManager.LoadSceneAsync(nom, LoadSceneMode.Additive) ?? throw new InvalidOperationException("« " + nom + " » ne se charge pas"); };
            Armer(null);
            for (var e = Lot690.Jusqua(() => chargement != null && chargement.isDone && (transition == null || !transition.EnCours), () => "fondu ou chargement inachevé : « " + demandee + " »"); e.MoveNext();) yield return null;
            if (demandee != OuvertureDeLaCarte.SCENE) throw new InvalidOperationException("C a demandé « " + demandee + " »");
            Scene scene = SceneManager.GetSceneByName(demandee); SceneManager.SetActiveScene(scene); Ecarter(camera);
            CarteDessinee[] cartes = scene.GetRootGameObjects().SelectMany(r => r.GetComponentsInChildren<CarteDessinee>(true)).ToArray();
            CarteDessinee carte = cartes.Length == 1 ? cartes[0] : throw new InvalidOperationException(cartes.Length + " cartes dans " + demandee);
            for (var e = Lot690.Jusqua(() => carte.CellulesPosees == carte.CellulesServies && carte.CellulesPosees > 0, () => carte.CellulesPosees + " cellules posées pour " + carte.CellulesServies + " servies"); e.MoveNext();) yield return null;
            HorlogeDeCarte horloge = carte.GetComponent<HorlogeDeCarte>() ?? throw new InvalidOperationException("la carte n'a pas d'horloge");
            for (var e = Servie(port, h => Meme(h.JoursParSeconde, reglages.VitesseCarte) && Affiche(horloge, h.JoursParSeconde), "horloge de la carte"); e.MoveNext();) yield return null;
            carte.GetComponent<CommandesDuTemps>().automatique = carte.GetComponent<ParcoursDeCarte>().automatique = carte.GetComponent<SurvolDeCarte>().automatique = true;
            Lot549.Photographier(camera, carte); Cabinet(camera, carte);
            for (int i = 0; i < 8; i++) yield return null;
            if (!Affiche(horloge, reglages.VitesseCarte)) throw new InvalidOperationException("après la pose, l'horloge dit « " + horloge.TexteAffiche + " »");
            Lot690.DansLeChamp(camera, carte.transform.Find("Cabinet").GetComponentsInChildren<Text>().FirstOrDefault(t => t.text == horloge.TexteAffiche)
                ?? throw new InvalidOperationException("le bandeau du cabinet ne montre pas « " + horloge.TexteAffiche + " »"));
        }

        // Le cabinet réserve à la carte les deux tiers gauches et dessine ses dossiers, dont la date, en overlay : la photo
        // d'une seule caméra ne les voit pas. La caméra photographiée prend toute l'image, décalée vers l'est pour garder la
        // carte à sa place, et la toile du cabinet se dessine sur elle.
        static void Cabinet(Camera camera, CarteDessinee carte) {
            Canvas toile = carte.transform.Find("Cabinet")?.GetComponent<Canvas>() ?? throw new InvalidOperationException("la carte n'a pas de cabinet");
            float largeur = camera.rect.width; camera.rect = new Rect(0, 0, 1, 1);
            camera.transform.position += camera.transform.right * (1 - largeur) * camera.orthographicSize * camera.aspect;
            toile.renderMode = RenderMode.ScreenSpaceCamera; toile.worldCamera = camera; toile.planeDistance = camera.nearClipPlane + 0.2f;
        }

        // En batch, la vue de jeu n'a pas le focus : les événements clavier restent dans l'éditeur.
        // La frappe est donc écrite dans l'état du joueur, au début de Update, avant l'outil.
        static void Armer(Key? touche) { if (frappe == null) frappe = new GameObject("Frappe").AddComponent<Frappe>(); (Frappe.tenue, Frappe.armee) = (touche, true); }
        // La touche reste enfoncée jusqu'à la fin de `pendant` (six images sans attente), puis se relâche.
        static IEnumerator Touche(Key touche, IEnumerator pendant) {
            Armer(touche); for (int i = 0; i < 6; i++) yield return null;
            while (pendant != null && pendant.MoveNext()) yield return null;
            Armer(null); yield return null; }
        // Lit /horloge hors du fil principal, une lecture à la fois, jusqu'à une réponse que `voulue` accepte.
        static IEnumerator Servie(int port, Func<HorlogeLue, bool> voulue, string quoi) {
            Task<Lecture<HorlogeLue>> t = null;
            return Lot690.Jusqua(() => {
                if (t != null && t.IsCompleted && t.Result.Presente && voulue(t.Result.Donnees)) return true;
                if (t == null || t.IsCompleted) t = Task.Run(() => { using (var c = new ClientHorloge(port, TimeSpan.FromSeconds(5))) return c.Lire(); });
                return false;
            }, () => quoi + " : " + (t == null || !t.IsCompleted ? "lecture en cours" : t.Result.Presente ? "vitesse " + t.Result.Donnees.JoursParSeconde : t.Result.Absence));
        }
        static bool Affiche(HorlogeDeCarte h, double v) => h.Lue != null && Meme(h.Lue.JoursParSeconde, v) && h.TexteAffiche == HorlogeDeCarte.Decrire(h.Lue);
        static bool Meme(double a, double b) => Math.Abs(a - b) < 1e-6;
        static DesertRoadTool Outil() => Object.FindFirstObjectByType<DesertRoadTool>() ?? throw new InvalidOperationException("pas d'outil des routes");
        static IEnumerator Secondes(double s) { double fin = Time.realtimeSinceStartupAsDouble + s; return Lot690.Jusqua(() => Time.realtimeSinceStartupAsDouble >= fin, () => "attente"); }
        static TextMesh Panneau(Camera camera) => camera.GetComponentsInChildren<TextMesh>(true).FirstOrDefault(t => t.name == "Panneau des routes") ?? throw new InvalidOperationException("panneau des routes absent");
        static void Exiger(Camera camera, string mode) { string texte = Panneau(camera).text;
            if (!texte.Contains(CARTE) || !texte.Contains(PAUSE)) throw new InvalidOperationException(mode + " : « " + texte.Replace("\n", " | ") + " »"); }
        static void Lisible(Camera camera, TextMesh texte) {
            Bounds b = texte.GetComponent<MeshRenderer>().localBounds; string hors = null;
            foreach (float x in new[] { -1f, 1f }) foreach (float y in new[] { -1f, 1f }) {
                Vector3 v = camera.WorldToViewportPoint(texte.transform.TransformPoint(b.center + Vector3.Scale(b.extents, new Vector3(x, y, 0))));
                if (v.z <= 0f || v.x < -0.01f || v.x > 1.01f || v.y < -0.01f || v.y > 1.01f) hors += " " + v.ToString("F3");
            }
            if (hors != null) throw new InvalidOperationException("aide coupée" + hors + " : « " + texte.text.Replace("\n", " | ") + " »");
        }
        // Le désert de côté, comme `Lot549.Ecarter` : hors du chemin de la caméra tout s'éteint ; ce qui la reprendrait aussi.
        static void Ecarter(Camera camera) {
            foreach (GameObject racine in camera.gameObject.scene.GetRootGameObjects()) Ecarter(racine.transform, camera.transform);
            foreach (Behaviour b in new Behaviour[] { camera.GetComponent<DesertCityCamera>(), camera.GetComponent<VillageV2Visit>() }) if (b != null) b.enabled = false;
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
        public static Key? tenue; public static bool armee;
        void Update() {
            if (!armee) return; Keyboard k = Keyboard.current; if (k == null || !k.added) k = InputSystem.AddDevice<Keyboard>(); if (!k.enabled) InputSystem.EnableDevice(k);
            k.MakeCurrent(); InputState.Change(k, tenue is Key t ? new KeyboardState(t) : new KeyboardState(), InputUpdateType.Dynamic); armee = false; }
    }
}
