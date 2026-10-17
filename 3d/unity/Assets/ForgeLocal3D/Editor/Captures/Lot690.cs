using System;
using System.Collections;
using System.Linq;
using System.Net.Http;
using System.Threading.Tasks;
using Forge.Interface;
using Forge.Pont;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures
{
    // Lot 690 : Bar choisi dans le cabinet, un tick, et la carte dit qu'il n'y a pas de kit. Le scénario n'ajoute
    // jamais le passage. `-forge690SansTick` omet seulement le POST : le reçu ne montre rien, le message rougit.
    static class Lot690
    {
        const string TERRE = "Duché de Bar", SANS_TICK = "-forge690SansTick", MESSAGE = PassageALaCapitale.MESSAGE_SANS_KIT;
        const double ATTENTE_S = 30;
        const int IMAGES_DE_POSE = 10;
        static bool Drapeau() => Environment.GetCommandLineArgs().Contains(SANS_TICK);

        [ScenarioDeCapture(690, "bar-sans-kit")]
        static IEnumerator BarSansKit(Camera camera)
        {
            var ouverte = new Lot549.CarteOuverte();
            for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null;
            CarteDessinee carte = ouverte.Carte;
            PassageALaCapitale[] passages = carte.GetComponents<PassageALaCapitale>();
            if (passages.Length != 1) throw new InvalidOperationException("passage absent : attendu exactement 1 sur la carte, observé " + passages.Length);
            PassageALaCapitale passage = passages[0];
            CabinetDeCarte cabinet = carte.GetComponent<CabinetDeCarte>() ?? throw new InvalidOperationException("la carte n'a pas de CabinetDeCarte");
            Transform toileCabinet = carte.transform.Find("Cabinet");
            if (toileCabinet == null || !toileCabinet.gameObject.activeInHierarchy) throw new InvalidOperationException("la toile du cabinet n'est pas active");
            ReperesDeDepart reperes = carte.GetComponent<ReperesDeDepart>() ?? throw new InvalidOperationException("la carte n'a pas de ReperesDeDepart");
            if (reperes.enabled) throw new InvalidOperationException("ReperesDeDepart est resté actif : le cabinet ne l'a pas désactivé");
            for (var e = Jusqua(() => LecturePrete(cabinet.Partie), () => Dire(cabinet.Partie)); e.MoveNext();) yield return null;
            LecturePartie partie = cabinet.Partie;
            FicheDeDepart[] bar = partie.Departs.Donnees.Fiches.Where(f => f.Nom == TERRE).ToArray();
            if (bar.Length != 1) throw new InvalidOperationException("liste de « " + TERRE + " » : attendu 1 fiche, observé " + bar.Length);
            FicheDeDepart fiche = bar[0]; long tick = partie.Monde.Donnees.Monde.Tick;
            if (partie.Departs.Donnees.Tick != tick) throw new InvalidOperationException("tick des départs " + partie.Departs.Donnees.Tick + " différent du monde " + tick);
            Task choix = partie.Choisir(fiche.Id);
            for (var e = Attendre(choix, "choix de " + fiche.Nom); e.MoveNext();) yield return null;
            RecuIntention recu = partie.Recu;
            if (recu == null || !recu.Acceptee) throw new InvalidOperationException("reçu refusé pour " + fiche.Nom + " : " + (recu == null ? "aucun reçu" : recu.Presente ? recu.Erreur : recu.Absence));
            if (recu.AppliqueeAuTick != tick) throw new InvalidOperationException("reçu accepté au tick " + recu.AppliqueeAuTick + ", attendu " + tick);
            int port = carte.port; Task<Lecture<MondeAvecMaisonLu>> avantTick = LireMonde(port);
            for (var e = Attendre(avantTick, "lecture /monde avant le tick"); e.MoveNext();) yield return null;
            ExigerMonde(avantTick.Result, tick, null, "avant le tick");
            if (passage.TexteAffiche != null || passage.PanneauVisible || passage.SceneDemandee != null)
                throw new InvalidOperationException("avant le tick, le passage montre « " + passage.TexteAffiche + " » ou demande « " + passage.SceneDemandee + " »");
            string observations = null; string maison = null; long apres = tick;
            if (Drapeau())
            {
                string scene = SceneManager.GetActiveScene().name;
                for (double fin = Time.realtimeSinceStartupAsDouble + 2 * PassageALaCapitale.PERIODE_LECTURE_S; Time.realtimeSinceStartupAsDouble < fin;)
                {
                    if (passage.PanneauVisible || passage.TexteAffiche != null) throw new InvalidOperationException("sans tick, le panneau s'est montré : « " + passage.TexteAffiche + " »");
                    if (SceneManager.GetActiveScene().name != scene) throw new InvalidOperationException("sans tick, la scène a changé : " + SceneManager.GetActiveScene().name);
                    yield return null;
                }
                Task<Lecture<MondeAvecMaisonLu>> encore = LireMonde(port);
                for (var e = Attendre(encore, "lecture /monde sans tick"); e.MoveNext();) yield return null;
                ExigerMonde(encore.Result, tick, null, "sans tick");
                observations = "sans tick, service joignable, tick " + tick + ", maison absente, panneau caché, scène " + scene;
            }
            else
            {
                Task<(int statut, string corps)> pousse = PousserTick(port);
                for (var e = Attendre(pousse, "POST /tick?n=1"); e.MoveNext();) yield return null;
                if (pousse.Result.statut != 200) throw new InvalidOperationException("POST /tick?n=1 a rendu " + pousse.Result.statut + " : " + pousse.Result.corps);
                for (var e = Jusqua(() => ApresTick(cabinet, passage, tick), () => "cabinet « " + Dire(cabinet.Partie) + " », passage « " + passage.TexteAffiche + " »"); e.MoveNext();) yield return null;
                maison = cabinet.Partie.Monde.Donnees.MaisonDuJoueur; Task<Lecture<MondeAvecMaisonLu>> confirme = LireMonde(port);
                for (var e = Attendre(confirme, "lecture /monde après le tick"); e.MoveNext();) yield return null;
                ExigerMonde(confirme.Result, tick + 1, maison, "après le tick");
                if (cabinet.Partie.Maison == null || !cabinet.Partie.Maison.Presente || cabinet.Partie.Maison.Donnees.Id != maison || cabinet.Partie.Maison.Donnees.Nom != fiche.Maison)
                    throw new InvalidOperationException("maison du cabinet « " + cabinet.Partie.Maison?.Donnees?.Nom + " » différente de « " + fiche.Maison + " » (" + maison + ")");
                apres = confirme.Result.Donnees.Monde.Tick;
            }
            Canvas toile = Toile(carte.camera);
            bool actif = toile != null && toile.gameObject.activeInHierarchy && toile.transform.parent == null;
            if (passage.TexteAffiche != MESSAGE || !passage.PanneauVisible || !actif || passage.SceneDemandee != null
                || SceneManager.GetActiveScene().name != OuvertureDeLaCarte.SCENE || carte.GetComponents<PassageALaCapitale>().Length != 1)
                throw new InvalidOperationException("message attendu mais absent : « " + (passage.TexteAffiche ?? "(aucun)") + " », panneau " + (passage.PanneauVisible ? "visible" : "caché")
                    + ", toiles " + (toile == null ? 0 : 1) + ", scène " + SceneManager.GetActiveScene().name + (observations == null ? "" : " ; " + observations));
            float distance = toile.planeDistance; Rect vue = carte.camera.rect; // le viewport posé par le cabinet
            Lot549.Photographier(camera, carte);
            if (toile.worldCamera != carte.camera) throw new InvalidOperationException("la toile du passage n'est plus liée à la caméra de la carte");
            toile.worldCamera = camera; Text texte = toile.GetComponentInChildren<Text>(true);
            // La toile garde sa distance ; elle doit tomber entre les plans de la caméra reçue, qui garde le viewport du cabinet.
            if (toile.renderMode != RenderMode.ScreenSpaceCamera || toile.planeDistance != distance || distance <= camera.nearClipPlane || distance >= camera.farClipPlane
                || vue.width >= 1f || camera.rect != vue)
                throw new InvalidOperationException("toile " + toile.renderMode + " distance " + toile.planeDistance + " (plans " + camera.nearClipPlane + "–" + camera.farClipPlane + "), viewport " + camera.rect + " / cabinet " + vue);
            if (toile.worldCamera != camera || !camera.enabled || !toile.gameObject.activeInHierarchy || texte.text != MESSAGE)
                throw new InvalidOperationException("la toile n'est pas active sur la caméra de la photo");
            DansLeChamp(camera, texte);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            if (passage.TexteAffiche != MESSAGE || cabinet.Partie.Monde?.Donnees.MaisonDuJoueur != maison || SceneManager.GetActiveScene().name != OuvertureDeLaCarte.SCENE
                || !cabinet.isActiveAndEnabled || !toileCabinet.gameObject.activeInHierarchy)
                throw new InvalidOperationException("après la pose : message « " + passage.TexteAffiche + " », maison « " + cabinet.Partie.Monde?.Donnees.MaisonDuJoueur + " », scène " + SceneManager.GetActiveScene().name);
            DansLeChamp(camera, texte);
            Debug.Log("CAPTURE_690 tick " + tick + " avant, " + apres + " après, terre " + fiche.Nom + ", maison " + maison + ", scène " + SceneManager.GetActiveScene().name);
        }

        static bool LecturePrete(LecturePartie p) => p != null && !p.Occupee && p.Monde != null && p.Monde.Presente && p.Monde.Donnees.MaisonDuJoueur == null
            && p.Departs != null && p.Departs.Presente && p.Departs.Donnees.Fiches.Count > 0 && p.PeutChoisir;
        static string Dire(LecturePartie p) => p == null ? "partie absente" : p.Occupee ? "lecture en cours" : p.Monde == null ? "monde non lu"
            : !p.Monde.Presente ? "monde absent : " + p.Monde.Absence : p.Monde.Donnees.MaisonDuJoueur != null ? "maison déjà « " + p.Monde.Donnees.MaisonDuJoueur + " »"
            : p.Departs == null || !p.Departs.Presente ? "départs absents : " + (p.Departs == null ? "non lus" : p.Departs.Absence)
            : p.Departs.Donnees.Fiches.Count == 0 ? "liste vide" : p.PeutChoisir ? "prête" : "choix impossible";
        static bool ApresTick(CabinetDeCarte cabinet, PassageALaCapitale passage, long tick)
        {
            LecturePartie p = cabinet.Partie;
            return p != null && !p.Occupee && p.Monde != null && p.Monde.Presente && p.Monde.Donnees.Monde.Tick == tick + 1 && p.Monde.Donnees.MaisonDuJoueur != null
                && p.Maison != null && p.Maison.Presente && p.Maison.Donnees.Id == p.Monde.Donnees.MaisonDuJoueur
                && passage.TexteAffiche == MESSAGE && passage.PanneauVisible && passage.SceneDemandee == null && !passage.RequeteEnVol;
        }
        static void ExigerMonde(Lecture<MondeAvecMaisonLu> lu, long tick, string maison, string moment)
        {
            if (lu == null || !lu.Presente) throw new InvalidOperationException(moment + " : /monde absent : " + (lu == null ? "aucune lecture" : lu.Absence));
            if (lu.Donnees.Monde.Tick != tick || lu.Donnees.MaisonDuJoueur != maison)
                throw new InvalidOperationException(moment + " : tick " + lu.Donnees.Monde.Tick + " (attendu " + tick + "), maison « " + (lu.Donnees.MaisonDuJoueur ?? "absente") + " » (attendue « " + (maison ?? "absente") + " »)");
        }
        static Canvas Toile(Camera ancienne)
        {
            Canvas[] toiles = Object.FindObjectsByType<Canvas>(FindObjectsInactive.Include, FindObjectsSortMode.None)
                .Where(c => c.worldCamera == ancienne && c.GetComponentInChildren<Text>(true) is Text t && t.text == MESSAGE).ToArray();
            return toiles.Length == 1 ? toiles[0] : null;
        }
        static void DansLeChamp(Camera camera, Text texte)
        {
            var coins = new Vector3[4]; texte.rectTransform.GetWorldCorners(coins); string hors = null;
            for (int i = 0; i < 4; i++) { Vector3 v = camera.WorldToViewportPoint(coins[i]); if (v.z <= 0f || v.x < -0.01f || v.x > 1.01f || v.y < -0.01f || v.y > 1.01f) hors = (hors ?? "") + " coin " + i + " " + v.ToString("F3"); }
            if (hors != null) throw new InvalidOperationException("texte hors champ :" + hors);
        }
        static Task<Lecture<MondeAvecMaisonLu>> LireMonde(int port) => Task.Run(() => { using (var c = new ClientMonde(port, TimeSpan.FromSeconds(ATTENTE_S))) return c.LireAvecMaison(); });
        static Task<(int statut, string corps)> PousserTick(int port) => Task.Run(() => {
            using (var http = new HttpClient { Timeout = TimeSpan.FromSeconds(ATTENTE_S) }) using (var contenu = new ByteArrayContent(new byte[0]))
            using (var reponse = http.PostAsync("http://127.0.0.1:" + port + "/tick?n=1", contenu).GetAwaiter().GetResult())
                return ((int)reponse.StatusCode, reponse.Content.ReadAsStringAsync().GetAwaiter().GetResult()); });
        static IEnumerator Jusqua(Func<bool> fini, Func<string> sinon)
        { double fin = Time.realtimeSinceStartupAsDouble + ATTENTE_S; while (!fini()) { if (Time.realtimeSinceStartupAsDouble > fin) throw new InvalidOperationException(sinon() + " en " + ATTENTE_S + " s"); yield return null; } }
        static IEnumerator Attendre(Task tache, string cause)
        {
            for (var e = Jusqua(() => tache.IsCompleted, () => cause); e.MoveNext();) yield return null;
            if (tache.IsFaulted || tache.IsCanceled) throw new InvalidOperationException(cause + " : " + (tache.Exception == null ? tache.Status.ToString() : tache.Exception.GetBaseException().Message));
        }
    }
}
