using System;
using System.Collections;
using System.Globalization;
using System.Linq;
using System.Threading.Tasks;
using Forge.Interface;
using Forge.Pont;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures
{
    // Lot 701 : le Zab choisi dans le cabinet, un tick, et la carte cède la place à Biskra. Le passage décide seul ; le
    // scénario ne remplace que son chargement, fait à côté de la scène de la photo pour garder sa caméra. La ville neuve
    // doit s'ouvrir sur le siège remis par le passage, jamais sur le ksar de 1175 que l'éditeur ouvre sans -forgeCell.
    // `-forge701SansRemise` jette la remise juste avant le chargement : la ville s'ouvre sur 1175, le scénario rougit.
    static class Lot701
    {
        const string TERRE = "Émirat du Zab", KSAR = "Cellule 1175", SANS_REMISE = "-forge701SansRemise";
        const double ATTENTE_PANNEAU_S = 15;
        const int IMAGES_DE_POSE = 10;

        static string N(long v) => v.ToString(CultureInfo.InvariantCulture);
        static string Ligne(string texte) => texte == null ? "(aucun texte)" : texte.Split('\n')[0];
        static T Unique<T>(Scene scene, string etape) where T : Component
        {
            T[] tous = scene.GetRootGameObjects().SelectMany(r => r.GetComponentsInChildren<T>(true)).ToArray();
            if (tous.Length != 1) throw new InvalidOperationException(etape + " : la scène « " + scene.name + " » porte " + tous.Length + " " + typeof(T).Name + ", il en faut un");
            return tous[0];
        }
        static void SansKsar(PanneauLieu panneau, string etape)
        {
            if ((panneau.TexteAffiche ?? "").Contains(KSAR))
                throw new InvalidOperationException(etape + " : la ville s'est ouverte sur 1175, le panneau dit « " + panneau.TexteAffiche.Replace("\n", " | ") + " »");
        }

        [ScenarioDeCapture(701, "zab-biskra-depuis-la-carte")]
        static IEnumerator ZabBiskraDepuisLaCarte(Camera camera)
        {
            // 1. La scène ouverte au lancement, sans -forgeCell, reste sur le ksar.
            Scene premiere = camera.gameObject.scene;
            string avant = Unique<PanneauLieu>(premiere, "étape 1").TexteAffiche ?? "";
            if (!avant.StartsWith(KSAR + " · tick ", StringComparison.Ordinal))
                throw new InvalidOperationException("étape 1 : sans -forgeCell, le panneau devait lire le ksar, il dit « " + avant.Replace("\n", " | ") + " »");

            // 2. La carte, son seul passage, le cabinet et une partie prête.
            var ouverte = new Lot549.CarteOuverte();
            for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null;
            CarteDessinee carte = ouverte.Carte; int port = carte.port;
            PassageALaCapitale[] passages = carte.GetComponents<PassageALaCapitale>();
            if (passages.Length != 1) throw new InvalidOperationException("étape 2 : attendu exactement 1 passage sur la carte, observé " + passages.Length);
            PassageALaCapitale passage = passages[0];
            CabinetDeCarte cabinet = carte.GetComponent<CabinetDeCarte>() ?? throw new InvalidOperationException("étape 2 : la carte n'a pas de CabinetDeCarte");
            for (var e = Lot690.Jusqua(() => Lot690.LecturePrete(cabinet.Partie), () => "étape 2 : " + Lot690.Dire(cabinet.Partie)); e.MoveNext();) yield return null;

            // 3. Le Zab choisi, son reçu accepté, puis deux périodes du passage : il voit le départ.
            LecturePartie partie = cabinet.Partie;
            FicheDeDepart[] zab = partie.Departs.Donnees.Fiches.Where(f => f.Nom == TERRE).ToArray();
            if (zab.Length != 1) throw new InvalidOperationException("étape 3 : attendu 1 fiche « " + TERRE + " », observé " + zab.Length);
            FicheDeDepart fiche = zab[0]; long tick = partie.Monde.Donnees.Monde.Tick;
            for (var e = Lot690.Attendre(partie.Choisir(fiche.Id), "étape 3 : choix de " + fiche.Nom); e.MoveNext();) yield return null;
            RecuIntention recu = partie.Recu;
            if (recu == null || !recu.Acceptee) throw new InvalidOperationException("étape 3 : reçu refusé pour " + fiche.Nom + " : " + (recu == null ? "aucun reçu" : recu.Presente ? recu.Erreur : recu.Absence));
            for (double fin = Time.realtimeSinceStartupAsDouble + 2 * PassageALaCapitale.PERIODE_LECTURE_S + 0.25; Time.realtimeSinceStartupAsDouble < fin;)
            {
                if (passage.Absence != null || passage.SceneDemandee != null)
                    throw new InvalidOperationException("étape 3 : avant le tick, le passage dit « " + passage.Absence + " » ou demande « " + passage.SceneDemandee + " »");
                yield return null;
            }

            // 5. Le chargement du passage, à côté de la scène de la photo : le passage décide, le scénario charge.
            AsyncOperation chargement = null; string demandee = null; int demandes = 0;
            passage.ChargerScene = nom =>
            {
                demandes++; demandee = nom;
                if (Environment.GetCommandLineArgs().Contains(SANS_REMISE)) PassageALaCapitale.PrendreCelluleRemise(nom);
                chargement = SceneManager.LoadSceneAsync(nom, LoadSceneMode.Additive);
            };

            // 4. Un seul tick ; le passage demande la scène du Zab, et /monde dit le tick N+1 avec la maison choisie.
            Task<(int statut, string corps)> pousse = Lot690.PousserTick(port);
            for (var e = Lot690.Attendre(pousse, "étape 4 : POST /tick?n=1"); e.MoveNext();) yield return null;
            if (pousse.Result.statut != 200) throw new InvalidOperationException("étape 4 : POST /tick?n=1 a rendu " + pousse.Result.statut + " : " + pousse.Result.corps);
            for (var e = Lot690.Jusqua(() => passage.SceneDemandee != null, () => "étape 4 : aucune scène demandée par le passage, absence « " + passage.Absence + " »"); e.MoveNext();) yield return null;
            for (var e = Lot690.Jusqua(() => cabinet.Partie is LecturePartie p && !p.Occupee && p.Monde != null && p.Monde.Presente && p.Monde.Donnees.Monde.Tick == tick + 1
                && p.Maison != null && p.Maison.Presente && p.Maison.Donnees.Id == p.Monde.Donnees.MaisonDuJoueur, () => "étape 4 : cabinet « " + Lot690.Dire(cabinet.Partie) + " »"); e.MoveNext();) yield return null;
            MaisonLue maison = cabinet.Partie.Maison.Donnees;
            Task<Lecture<MondeAvecMaisonLu>> confirme = Lot690.LireMonde(port);
            for (var e = Lot690.Attendre(confirme, "étape 4 : lecture /monde après le tick"); e.MoveNext();) yield return null;
            Lot690.ExigerMonde(confirme.Result, tick + 1, maison.Id, "étape 4");
            if (maison.Nom != fiche.Maison || !TerresAvecKit.Scenes.TryGetValue(maison.Id, out string scene) || passage.SceneDemandee != scene || demandee != scene || demandes != 1)
                throw new InvalidOperationException("étape 4 : maison « " + maison.Nom + " » (" + maison.Id + ") pour « " + fiche.Maison + " », scène demandée « " + passage.SceneDemandee + " », chargée « " + demandee + " » ×" + demandes);
            long siege = maison.Siege?.CellId ?? throw new InvalidOperationException("étape 4 : la maison « " + maison.Id + " » n'a pas de siège sur la carte");
            if (siege != fiche.CellId || siege == PanneauLieu.CELLULE_PAR_DEFAUT)
                throw new InvalidOperationException("étape 4 : siège " + N(siege) + ", fiche " + N(fiche.CellId) + " : il faut une même cellule, autre que 1175");

            // 5 (suite). La scène neuve chargée devient active ; la carte est déchargée.
            for (var e = Lot690.Jusqua(() => chargement != null && chargement.isDone, () => "étape 5 : « " + demandee + " » pas chargée"); e.MoveNext();) yield return null;
            Scene[] neuves = Enumerable.Range(0, SceneManager.sceneCount).Select(SceneManager.GetSceneAt).Where(s => s.isLoaded && s.name == scene && s.handle != premiere.handle).ToArray();
            if (neuves.Length != 1) throw new InvalidOperationException("étape 5 : " + neuves.Length + " scène(s) « " + scene + " » neuve(s), il en faut une");
            Scene neuve = neuves[0]; SceneManager.SetActiveScene(neuve);
            AsyncOperation dechargement = SceneManager.UnloadSceneAsync(OuvertureDeLaCarte.SCENE) ?? throw new InvalidOperationException("étape 5 : " + OuvertureDeLaCarte.SCENE + " ne se décharge pas");
            for (var e = Lot690.Jusqua(() => dechargement.isDone, () => "étape 5 : " + OuvertureDeLaCarte.SCENE + " pas déchargée"); e.MoveNext();) yield return null;

            // 6. Dans la ville neuve : l'outil sur le siège, le panneau qui le lit au tick N+1, jamais le ksar.
            DesertRoadTool outil = Unique<DesertRoadTool>(neuve, "étape 6"); PanneauLieu panneau = Unique<PanneauLieu>(neuve, "étape 6");
            DesertCityCamera ville = Unique<DesertCityCamera>(neuve, "étape 6");
            if (outil.Cellule != siege)
                throw new InvalidOperationException("étape 6 : la ville s'est ouverte sur " + N(outil.Cellule) + ", pas sur le siège " + N(siege) + " remis par le passage");
            string attendu = "Cellule " + N(siege) + " · tick " + N(tick + 1) + "\n";
            for (double fin = Time.realtimeSinceStartupAsDouble + ATTENTE_PANNEAU_S; !(panneau.TexteAffiche ?? "").StartsWith(attendu, StringComparison.Ordinal);)
            {
                SansKsar(panneau, "étape 6");
                if (Time.realtimeSinceStartupAsDouble > fin)
                    throw new InvalidOperationException("étape 6 : en " + ATTENTE_PANNEAU_S + " s, le panneau dit « " + (panneau.TexteAffiche ?? "").Replace("\n", " | ") + " », attendu « " + attendu.Trim() + " … »");
                yield return null;
            }
            SansKsar(panneau, "étape 6");
            if (outil.TickOuverture != tick + 1) throw new InvalidOperationException("étape 6 : plan ouvert au tick " + N(outil.TickOuverture) + ", attendu " + N(tick + 1) + " : " + outil.Message);
            Debug.Log("CAPTURE_701 tick " + N(tick) + " avant, " + N(confirme.Result.Donnees.Monde.Tick) + " après, maison " + maison.Id + " (" + maison.Nom + "), cellule de l'outil "
                + N(outil.Cellule) + ", panneau « " + Ligne(panneau.TexteAffiche) + " »");

            // La photo : la vue d'ensemble (touche F) de la ville neuve, prise par la caméra reçue, avec le panneau du lieu.
            outil.automatique = true; ville.automatique = true;
            ville.VueEnsemble();
            for (int i = 0; i < IMAGES_DE_POSE; i++) { yield return null; SansKsar(panneau, "vue d'ensemble"); }
            Camera vue = ville.GetComponent<Camera>();
            camera.CopyFrom(vue); camera.aspect = Lot549.FORME; vue.enabled = false;
            Canvas[] toiles = panneau.GetComponentsInChildren<Canvas>(true);
            if (toiles.Length != 1 || toiles[0].renderMode != RenderMode.ScreenSpaceCamera || toiles[0].worldCamera != vue)
                throw new InvalidOperationException("photo : " + toiles.Length + " toile(s) du panneau, attendu une seule en ScreenSpaceCamera sur la caméra de la ville");
            Canvas toile = toiles[0]; toile.worldCamera = camera;
            Text texte = toile.GetComponentsInChildren<Text>(true).FirstOrDefault(t => t.text == panneau.TexteAffiche) ?? throw new InvalidOperationException("photo : le texte du panneau est introuvable");
            Lot690.DansLeChamp(camera, texte);
            for (int i = 0; i < IMAGES_DE_POSE; i++) { yield return null; SansKsar(panneau, "pose de la photo"); }
            if (outil.Cellule != siege || !(panneau.TexteAffiche ?? "").StartsWith(attendu, StringComparison.Ordinal) || toile.worldCamera != camera || !toile.gameObject.activeInHierarchy)
                throw new InvalidOperationException("après la pose : cellule " + N(outil.Cellule) + ", panneau « " + Ligne(panneau.TexteAffiche) + " »");
            Lot690.DansLeChamp(camera, texte);
            Debug.Log("CAPTURE_701 photo : vue d'ensemble de " + scene + ", panneau « " + Ligne(panneau.TexteAffiche) + " »");
        }
    }
}
