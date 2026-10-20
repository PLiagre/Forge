using System;
using System.Collections;
using System.Globalization;
using System.Linq;
using System.Threading.Tasks;
using Forge.Pont;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures
{
    // Lot 729 : le Zab confirmé avant la carte, qui reste sur la carte ; puis un double-clic sur Biskra, et la ville s'ouvre par le
    // fondu de #728, sur le siège. Les deux scénarios jouent dans la même session : le second reprend la carte du premier.
    // `-forge729UnSeulClic` ne clique qu'une fois au scénario 2 : aucune transition ne part, le scénario rougit.
    static class Lot729
    {
        const string SIEGE = "Biskra", KSAR = "Cellule 1175", UN_SEUL_CLIC = "-forge729UnSeulClic";
        const double ATTENTE_S = 30; const int IMAGES_DE_POSE = 10; const float CRANS = 12;
        static CarteDessinee carte; static PassageALaCapitale passage; static long siege, tick; static string scene; static Vector3 point;

        static string N(long v) => v.ToString(CultureInfo.InvariantCulture);
        static string Ligne(string texte) => texte == null ? "(aucun texte)" : texte.Split('\n')[0];
        static T Unique<T>(Scene s, string etape) where T : Component
        {
            T[] tous = s.GetRootGameObjects().SelectMany(r => r.GetComponentsInChildren<T>(true)).ToArray();
            if (tous.Length != 1) throw new InvalidOperationException(etape + " : la scène « " + s.name + " » porte " + tous.Length + " " + typeof(T).Name + ", il en faut un");
            return tous[0];
        }
        static TransitionDeVue[] Transitions() => Object.FindObjectsByType<TransitionDeVue>(FindObjectsSortMode.None);

        [ScenarioDeCapture(729, "1-siege-du-zab")]
        static IEnumerator SiegeDuZab(Camera camera)
        {
            int port = Unique<DesertRoadTool>(camera.gameObject.scene, "étape 1").Port;
            var lecture = Task.Run(() => { using (var d = new ClientDeparts(port, ClientDeparts.DelaiMinimal)) return d.Lire(); });
            for (var e = Lot690.Attendre(lecture, "étape 1 : lecture /departs"); e.MoveNext();) yield return null;
            if (!lecture.Result.Presente) throw new InvalidOperationException("étape 1 : /departs absent : " + lecture.Result.Absence);
            FicheDeDepart zab = lecture.Result.Donnees.Fiches.FirstOrDefault(f => f.Siege.Nom == SIEGE) ?? throw new InvalidOperationException("étape 1 : /departs ne sert pas de terre au siège " + SIEGE);
            string corps = "{\"type\":\"choisir_depart\",\"seigneurie\":" + N(zab.Id) + "}";
            var depot = Task.Run(() => { using (var c = new ClientIntention(port, ClientDeparts.DelaiMinimal)) return c.Deposer(corps); });
            for (var e = Lot690.Attendre(depot, "étape 1 : choix de " + zab.Nom); e.MoveNext();) yield return null;
            RecuIntention recu = depot.Result;
            if (!recu.Acceptee) throw new InvalidOperationException("étape 1 : reçu refusé pour " + zab.Nom + " : " + (recu.Presente ? recu.Erreur : recu.Absence));
            Task<(int statut, string corps)> pousse = Lot690.PousserTick(port);
            for (var e = Lot690.Attendre(pousse, "étape 1 : POST /tick?n=1"); e.MoveNext();) yield return null;
            if (pousse.Result.statut != 200) throw new InvalidOperationException("étape 1 : POST /tick?n=1 a rendu " + pousse.Result.statut + " : " + pousse.Result.corps);
            Task<Lecture<MondeAvecMaisonLu>> monde = Lot690.LireMonde(port);
            for (var e = Lot690.Attendre(monde, "étape 1 : lecture /monde après le tick"); e.MoveNext();) yield return null;
            string id = "seigneurie-" + N(zab.Id); tick = recu.AppliqueeAuTick.Value + 1; Lot690.ExigerMonde(monde.Result, tick, id, "étape 1");
            var fiche = Task.Run(() => { using (var m = new ClientMaison(port, ClientDeparts.DelaiMinimal)) return m.Lire(id); });
            for (var e = Lot690.Attendre(fiche, "étape 1 : lecture /maison?id=" + id); e.MoveNext();) yield return null;
            if (!fiche.Result.Presente || !(fiche.Result.Donnees.Siege.Position is PointCarte position)) throw new InvalidOperationException("étape 1 : siège de " + id + " sans place : " + fiche.Result.Absence);
            if (!TerresAvecKit.Scenes.TryGetValue(id, out scene)) throw new InvalidOperationException("étape 1 : la maison " + id + " n'a pas de kit");

            var ouverte = new Lot549.CarteOuverte();
            for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null;
            carte = ouverte.Carte;
            PassageALaCapitale[] passages = carte.GetComponents<PassageALaCapitale>();
            if (passages.Length != 1) throw new InvalidOperationException("étape 2 : attendu exactement 1 passage sur la carte, observé " + passages.Length);
            passage = passages[0];
            (carte.GetComponent<SurvolDeCarte>() ?? throw new InvalidOperationException("étape 2 : la carte n'a pas de survol")).automatique = true;
            (carte.GetComponent<ParcoursDeCarte>() ?? throw new InvalidOperationException("étape 2 : la carte n'a pas de parcours")).automatique = true;
            siege = zab.CellId;
            if (siege == PanneauLieu.CELLULE_PAR_DEFAUT || fiche.Result.Donnees.Siege.CellId != siege)
                throw new InvalidOperationException("étape 2 : siège " + N(siege) + " de la fiche, " + fiche.Result.Donnees.Siege.CellId + " de la maison : il faut une même cellule, autre que 1175");
            for (var e = Lot690.Jusqua(() => passage.SiegeLu == siege, () => "étape 2 : le passage lit le siège " + passage.SiegeLu + ", attendu " + N(siege) + ", absence « " + passage.Absence + " »"); e.MoveNext();) yield return null;
            // Une terre déjà confirmée ne descend pas seule.
            for (double fin = Time.realtimeSinceStartupAsDouble + 2 * PassageALaCapitale.PERIODE_LECTURE_S; Time.realtimeSinceStartupAsDouble < fin;)
            {
                if (passage.SceneDemandee != null || Transitions().Length > 0) throw new InvalidOperationException("étape 2 : sans geste, le passage demande « " + passage.SceneDemandee + " »");
                yield return null;
            }

            // Le zoom ancré garde le siège là où la carte entière le montre, au bas du cadre : la vue se centre ensuite sur lui.
            Vector3 local = carte.PositionSurLaCarte(position, ReperesDeDepart.HAUTEUR_LIEU).Value; point = carte.transform.TransformPoint(local);
            carte.Vue.Zoomer(CRANS, carte.camera.WorldToViewportPoint(point)); carte.Vue.Centrer(new Vector2(local.x, local.z), carte.Vue.Demi);
            yield return null; // la carte se recadre sur sa vue
            Vector3 vu = carte.camera.WorldToViewportPoint(point); CelluleDeCarte centre = carte.CelluleSous(point);
            if (vu.x < 0.3f || vu.x > 0.7f || vu.y < 0.3f || vu.y > 0.7f || centre?.CellId != siege) // la borne sud de la carte peut retenir la vue
                throw new InvalidOperationException("étape 3 : siège au point " + vu.ToString("F3") + " du cadre, sur la cellule " + centre?.CellId + " : attendu " + N(siege) + " au centre");
            string hors = null; Vector3 vuNom = Vector3.back; // « Biskra » lisible au centre : le mot dans le cadre, pas la cellule seule
            foreach (TextMesh m in Object.FindObjectsByType<TextMesh>(FindObjectsInactive.Exclude, FindObjectsSortMode.None)) if ((m.text ?? "").Contains(SIEGE)) { Vector3 p = carte.camera.WorldToViewportPoint(m.transform.position); if (p.z > 0f && p.x >= 0.3f && p.x <= 0.7f && p.y >= 0.3f && p.y <= 0.7f) vuNom = p; else hors = m.text; }
            foreach (Text t in Object.FindObjectsByType<Text>(FindObjectsInactive.Exclude, FindObjectsSortMode.None)) if ((t.text ?? "").Contains(SIEGE)) { Vector3 p = carte.camera.WorldToViewportPoint(t.rectTransform.position); if (p.z > 0f && p.x >= 0.3f && p.x <= 0.7f && p.y >= 0.3f && p.y <= 0.7f) vuNom = p; else hors = t.text; }
            if (vuNom.z <= 0f) throw new InvalidOperationException("étape 3 : « " + SIEGE + " » n'est pas lisible au centre" + (hors == null ? " : aucun texte ne porte ce nom" : " : « " + hors.Split('\n').First(l => l.Contains(SIEGE)) + " » est hors du centre"));
            Lot549.Photographier(camera, carte);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            if (passage.SceneDemandee != null) throw new InvalidOperationException("étape 3 : pendant la pose, le passage demande « " + passage.SceneDemandee + " »");
            Debug.Log("CAPTURE_729 siège " + N(siege) + " (" + SIEGE + ") lu par le passage, " + id + " au tick " + N(tick) + ", aucune scène demandée, " + SIEGE + " lisible au point " + vuNom.ToString("F3"));
        }

        [ScenarioDeCapture(729, "2-biskra-apres-la-transition")]
        static IEnumerator BiskraApresLaTransition(Camera camera)
        {
            if (carte == null || passage == null) throw new InvalidOperationException("étape 4 : la carte du scénario 1 manque");
            Scene premiere = camera.gameObject.scene;
            SurvolDeCarte survol = carte.GetComponent<SurvolDeCarte>(); FicheDeCellule cellule = carte.GetComponent<FicheDeCellule>();
            Vector2 ecran = carte.camera.WorldToScreenPoint(point);
            survol.Survoler(ecran);
            if (cellule.Survolee?.CellId != siege) throw new InvalidOperationException("étape 4 : au point du siège, la fiche voit la cellule " + cellule.Survolee?.CellId + ", attendu " + N(siege));
            survol.Cliquer(ecran);
            for (double fin = Time.realtimeSinceStartupAsDouble + PassageALaCapitale.DELAI_DOUBLE_CLIC_S + 0.3; Time.realtimeSinceStartupAsDouble < fin;)
            {
                if (Transitions().Length > 0 || passage.SceneDemandee != null) throw new InvalidOperationException("étape 4 : un clic seul a lancé la descente vers « " + passage.SceneDemandee + " »");
                yield return null;
            }

            survol.Cliquer(ecran); if (!Environment.GetCommandLineArgs().Contains(UN_SEUL_CLIC)) survol.Cliquer(ecran);
            TransitionDeVue[] transitions = Transitions();
            if (transitions.Length == 0) throw new InvalidOperationException("étape 5 : aucune transition n'est partie après le double-clic sur " + N(siege) + ", scène demandée « " + passage.SceneDemandee + " »");
            if (transitions.Length != 1 || !transitions[0].EnCours || passage.SceneDemandee != scene)
                throw new InvalidOperationException("étape 5 : " + transitions.Length + " transition(s), scène demandée « " + passage.SceneDemandee + " », attendu une seule en cours vers « " + scene + " »");
            // La transition décide du moment, le scénario charge à côté de la scène de la photo pour garder sa caméra (comme Lot701).
            TransitionDeVue transition = transitions[0]; AsyncOperation chargement = null; int demandes = 0; float opacite = 0;
            transition.ChargerScene = nom => { demandes++; opacite = Mathf.Max(opacite, transition.Opacite); chargement = nom == scene ? SceneManager.LoadSceneAsync(nom, LoadSceneMode.Additive) : null; };
            for (var e = Lot690.Jusqua(() => { if (transition != null) opacite = Mathf.Max(opacite, transition.Opacite); return chargement != null && chargement.isDone && (transition == null || !transition.EnCours); },
                () => "étape 5 : « " + scene + " » chargée ×" + demandes + ", transition " + (transition == null ? "finie" : "en cours, opacité " + transition.Opacite)); e.MoveNext();) yield return null;
            Scene[] neuves = Enumerable.Range(0, SceneManager.sceneCount).Select(SceneManager.GetSceneAt).Where(s => s.isLoaded && s.name == scene && s.handle != premiere.handle).ToArray();
            if (opacite < 1 || demandes != 1 || neuves.Length != 1)
                throw new InvalidOperationException("étape 5 : opacité maximale " + opacite + ", " + demandes + " chargement(s), " + neuves.Length + " scène(s) « " + scene + " » neuve(s) : il faut 1, 1 et 1");
            string reglage = transition.VitessePosee != null ? "vitesse posée " + transition.VitessePosee.Value.ToString(CultureInfo.InvariantCulture) : "absence « " + transition.Absence + " »";

            Scene neuve = neuves[0]; SceneManager.SetActiveScene(neuve);
            AsyncOperation dechargement = SceneManager.UnloadSceneAsync(OuvertureDeLaCarte.SCENE) ?? throw new InvalidOperationException("étape 6 : " + OuvertureDeLaCarte.SCENE + " ne se décharge pas");
            for (var e = Lot690.Jusqua(() => dechargement.isDone, () => "étape 6 : " + OuvertureDeLaCarte.SCENE + " pas déchargée"); e.MoveNext();) yield return null;
            DesertRoadTool outil = Unique<DesertRoadTool>(neuve, "étape 6"); PanneauLieu panneau = Unique<PanneauLieu>(neuve, "étape 6"); DesertCityCamera ville = Unique<DesertCityCamera>(neuve, "étape 6");
            if (outil.Cellule != siege) throw new InvalidOperationException("étape 6 : la ville s'est ouverte sur " + N(outil.Cellule) + ", pas sur le siège " + N(siege));
            string attendu = "Cellule " + N(siege) + " · tick " + N(tick) + "\n";
            for (var e = Lot690.Jusqua(() => (panneau.TexteAffiche ?? "").StartsWith(attendu, StringComparison.Ordinal),
                () => "étape 6 : le panneau dit « " + (panneau.TexteAffiche ?? "").Replace("\n", " | ") + " », attendu « " + attendu.Trim() + " … »"); e.MoveNext();) yield return null;
            if ((panneau.TexteAffiche ?? "").Contains(KSAR)) throw new InvalidOperationException("étape 6 : la ville s'est ouverte sur 1175");
            if (outil.TickOuverture != tick) throw new InvalidOperationException("étape 6 : plan ouvert au tick " + N(outil.TickOuverture) + ", attendu " + N(tick) + " : " + outil.Message);
            Debug.Log("CAPTURE_729 siège " + N(siege) + ", scène " + scene + ", opacité maximale " + opacite.ToString(CultureInfo.InvariantCulture) + ", " + reglage + ", panneau « " + Ligne(panneau.TexteAffiche) + " »");

            // La photo : la vue d'ensemble (touche F) de la ville neuve, prise par la caméra reçue, avec le panneau du lieu.
            outil.automatique = true; ville.automatique = true; ville.VueEnsemble();
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            Camera vue = ville.GetComponent<Camera>(); camera.CopyFrom(vue); camera.aspect = Lot549.FORME; vue.enabled = false;
            Canvas[] toiles = panneau.GetComponentsInChildren<Canvas>(true);
            if (toiles.Length != 1 || toiles[0].renderMode != RenderMode.ScreenSpaceCamera || toiles[0].worldCamera != vue)
                throw new InvalidOperationException("photo : " + toiles.Length + " toile(s) du panneau, attendu une seule en ScreenSpaceCamera sur la caméra de la ville");
            Canvas toile = toiles[0]; toile.worldCamera = camera;
            Text texte = toile.GetComponentsInChildren<Text>(true).FirstOrDefault(t => t.text == panneau.TexteAffiche) ?? throw new InvalidOperationException("photo : le texte du panneau est introuvable");
            Lot690.DansLeChamp(camera, texte);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            if (outil.Cellule != siege || !(panneau.TexteAffiche ?? "").StartsWith(attendu, StringComparison.Ordinal) || toile.worldCamera != camera || !toile.gameObject.activeInHierarchy)
                throw new InvalidOperationException("après la pose : cellule " + N(outil.Cellule) + ", panneau « " + Ligne(panneau.TexteAffiche) + " »");
            Lot690.DansLeChamp(camera, texte);
            Debug.Log("CAPTURE_729 photo : vue d'ensemble de " + scene + ", panneau « " + Ligne(panneau.TexteAffiche) + " »");
        }
    }
}
