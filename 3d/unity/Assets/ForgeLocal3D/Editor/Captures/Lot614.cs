using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Net.Http;
using System.Threading.Tasks;
using Forge.Pont;
using UnityEngine;
namespace ForgeLocal3D.Captures {
    // Lot 614 : le clic choisit la Morée, un tick applique, la caméra descend seule. `-forge614RetirerLieu` retire un disque tenu.
    static class Lot614 {
        const string RACINE = "Repères des terres de départ", LIEUX = "Lieux du joueur", MOREE = "Despotat de Morée", RETIRER = "-forge614RetirerLieu";
        const double ATTENTE_S = 30; const int FICHES = 6, TENUS = 4, IMAGES = 10;
        [ScenarioDeCapture(614, "mistra-et-ses-lieux")]
        static IEnumerator MistraEtSesLieux(Camera camera) {
            var ouverte = new Lot549.CarteOuverte();
            for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null;
            CarteDessinee carte = ouverte.Carte; var survol = carte.GetComponent<SurvolDeCarte>() ?? throw new InvalidOperationException("pas de survol"); var cellule = carte.GetComponent<FicheDeCellule>() ?? throw new InvalidOperationException("pas de fiche");
            (carte.GetComponent<ParcoursDeCarte>() ?? throw new InvalidOperationException("pas de parcours")).automatique = true; survol.automatique = true; ReperesDeDepart reperes = carte.GetComponent<ReperesDeDepart>() ?? throw new InvalidOperationException("pas de repères");
            for (var e = Attendre(() => !reperes.LectureEnVol && Actifs(carte) == FICHES, () => Actifs(carte) + " repères « " + reperes.TexteAffiche + " »"); e.MoveNext();) yield return null;
            Transform repere = carte.transform.Find(RACINE + "/Repère " + MOREE) ?? throw new InvalidOperationException("pas de " + MOREE);
            Vector2 ecran = carte.camera.WorldToScreenPoint(repere.position); survol.Survoler(ecran); survol.Cliquer(ecran);
            for (var e = Attendre(() => !reperes.ChoixEnVol && reperes.RecuDuChoix != null, () => "pas de reçu"); e.MoveNext();) yield return null;
            if (!reperes.RecuDuChoix.Acceptee) throw new InvalidOperationException(reperes.RecuDuChoix.Presente ? reperes.RecuDuChoix.Erreur : reperes.RecuDuChoix.Absence);
            for (var e = Attendre(() => cellule.MondeLu != null && cellule.MaisonDuJoueur == null && Actifs(carte) == FICHES && carte.Vue.Echelle == 1f, () => "en pause « " + cellule.MaisonDuJoueur + " » repères " + Actifs(carte)); e.MoveNext();) yield return null;
            int port = reperes.port;
            Task<int> tick = Task.Run(() => { using (var http = new HttpClient { Timeout = TimeSpan.FromSeconds(ATTENTE_S) }) using (var c = new ByteArrayContent(new byte[0])) using (var r = http.PostAsync("http://127.0.0.1:" + port.ToString(CultureInfo.InvariantCulture) + "/tick?n=1", c).GetAwaiter().GetResult()) return (int)r.StatusCode; });
            for (var e = Attendre(() => tick.IsCompleted, () => "pas de tick"); e.MoveNext();) yield return null;
            if (tick.IsFaulted || tick.Result != 200) throw new InvalidOperationException(tick.IsFaulted ? tick.Exception.GetBaseException().Message : "tick " + tick.Result);
            for (var e = Attendre(() => cellule.MaisonDuJoueur != null && Actifs(carte) == 0 && carte.Vue.Echelle < 1f, () => "pas de descente « " + reperes.TexteAffiche + " »"); e.MoveNext();) yield return null;
            var lu = Task.Run(() => Lire(port, cellule.MaisonDuJoueur)); for (var e = Attendre(() => lu.IsCompleted, () => "pas de référence"); e.MoveNext();) yield return null; if (lu.IsFaulted) throw new InvalidOperationException(lu.Exception.GetBaseException().Message);
            if (Environment.GetCommandLineArgs().Contains(RETIRER)) { LieuTenu t0 = lu.Result.fiche.Donnees.Lieux[0]; Transform d = carte.transform.Find(LIEUX + "/" + ReperesDeDepart.NomDuLieu(t0.CellId, t0.Rang) + "/Disque"); if (d != null) d.gameObject.SetActive(false); }
            Controler(carte.camera, carte, reperes, lu.Result); Lot549.Photographier(camera, carte);
            for (int i = 0; i < IMAGES; i++) yield return null;
            Controler(camera, carte, reperes, lu.Result);
            Debug.Log("CAPTURE_614 maison " + cellule.MaisonDuJoueur + ", siège " + lu.Result.fiche.Donnees.Siege.Nom + ", couples attendus " + lu.Result.fiche.Donnees.Lieux.Count + ", observés " + Compter(carte) + ", repères actifs " + Actifs(carte) + ", cadrage " + carte.Vue.Centre + " demi " + carte.Vue.Demi);
        }
        static (Lecture<MondeAvecMaisonLu> monde, Lecture<MaisonLue> fiche, List<LectureLieu> lieux) Lire(int port, string id) {
            using (var monde = new ClientMonde(port, TimeSpan.FromSeconds(ATTENTE_S))) using (var maisons = new ClientMaison(port, ClientDeparts.DelaiMinimal)) using (var lieux = new ClientLieu(port, TimeSpan.FromSeconds(ATTENTE_S))) {
                Lecture<MondeAvecMaisonLu> m = monde.LireAvecMaison(); if (!m.Presente || m.Donnees.MaisonDuJoueur != id) throw new InvalidOperationException(m.Presente ? m.Donnees.MaisonDuJoueur : m.Absence);
                Lecture<MaisonLue> h = maisons.Lire(id); if (!h.Presente) throw new InvalidOperationException(h.Absence); var lus = new List<LectureLieu>(); var vus = new HashSet<long>(); foreach (LieuTenu t in h.Donnees.Lieux) if (vus.Add(t.CellId)) lus.Add(lieux.Lire(t.CellId)); return (m, h, lus);
            }
        }
        static void Controler(Camera cam, CarteDessinee carte, ReperesDeDepart reperes, (Lecture<MondeAvecMaisonLu> monde, Lecture<MaisonLue> fiche, List<LectureLieu> lieux) lu) {
            MaisonLue h = lu.fiche.Donnees; if (h.Siege.Nom != "Mistra" || h.Siege.Position == null || h.Lieux.Count != TENUS) throw new InvalidOperationException(h.Siege.Nom + " " + h.Lieux.Count);
            if (Actifs(carte) != 0) throw new InvalidOperationException(Actifs(carte) + " repères actifs");
            foreach (LieuTenu t in h.Lieux) {
                LieuPlace p = null; foreach (LectureLieu l in lu.lieux) if (l.Presente && l.Lieu.CellId == t.CellId && l.Lieu.Lieux != null) foreach (LieuPlace x in l.Lieu.Lieux) if (x.Rang == t.Rang) p = x;
                string couple = t.CellId.ToString(CultureInfo.InvariantCulture) + "-" + t.Rang.ToString(CultureInfo.InvariantCulture); Transform disque = carte.transform.Find(LIEUX + "/" + ReperesDeDepart.NomDuLieu(t.CellId, t.Rang) + "/Disque"); MeshRenderer rendu = disque != null ? disque.GetComponent<MeshRenderer>() : null;
                Vector3 attendu = p != null && p.Position != null ? carte.transform.TransformPoint(carte.PositionSurLaCarte(p.Position.Value, ReperesDeDepart.HAUTEUR_LIEU).Value) : Vector3.zero;
                if (p == null || p.Position == null || p.Maitre != h.Id || rendu == null || !rendu.enabled || !disque.gameObject.activeInHierarchy) throw new InvalidOperationException("couple manquant " + couple);
                if ((disque.position - attendu).sqrMagnitude > 1e-4f || !Champ(cam, disque.position)) throw new InvalidOperationException("couple " + couple + " mal placé ou hors champ");
            }
            if (!Champ(cam, carte.transform.TransformPoint(carte.PositionSurLaCarte(h.Siege.Position.Value, ReperesDeDepart.HAUTEUR_LIEU).Value))) throw new InvalidOperationException("siège hors champ"); if (reperes.TexteAffiche == null || !reperes.TexteAffiche.Contains("Mistra") || !reperes.TexteAffiche.Contains(TENUS.ToString(CultureInfo.InvariantCulture))) throw new InvalidOperationException("texte « " + reperes.TexteAffiche + " »");
        }
        static bool Champ(Camera cam, Vector3 p) { Vector3 v = cam.WorldToViewportPoint(p); return v.z >= cam.nearClipPlane && v.z <= cam.farClipPlane && v.x >= 0f && v.x <= 1f && v.y >= 0f && v.y <= 1f; }
        static IEnumerator Attendre(Func<bool> fini, Func<string> sinon) { double fin = Time.realtimeSinceStartupAsDouble + ATTENTE_S; while (!fini()) { if (Time.realtimeSinceStartupAsDouble > fin) throw new InvalidOperationException(sinon() + " en " + ATTENTE_S + " s"); yield return null; } }
        static int Nombre(CarteDessinee carte, string racine) { Transform r = carte.transform.Find(racine); return r == null ? 0 : r.Cast<Transform>().Count(t => t.gameObject.activeInHierarchy); }
        static int Actifs(CarteDessinee carte) => Nombre(carte, RACINE); static int Compter(CarteDessinee carte) => Nombre(carte, LIEUX);
    }
}
