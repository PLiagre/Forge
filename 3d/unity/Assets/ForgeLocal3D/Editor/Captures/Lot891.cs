using System; using System.Collections; using System.Globalization; using System.Linq; using System.Threading.Tasks;
using Forge.Interface; using Forge.Pont; using UnityEngine; using UnityEngine.UI;
namespace ForgeLocal3D.Captures {
    static class Lot891 {
        const string SIEGE = "Mistra", TICK = "-forge891Tick"; const float VX = .82f, VY = .58f;
        static string N(long v) => v.ToString(CultureInfo.InvariantCulture); static InvalidOperationException Echec(string cause) => new InvalidOperationException(cause);
        static string Ligne(string t) => (t ?? "(aucun)").Replace("\r", "").Replace("\n", " | "); static bool Zone(Vector3 v) => v.z > 0f && v.x >= .68f && v.x <= .98f && v.y >= .40f && v.y <= .95f;
        static IEnumerator Bourg(int port, long cellule, LieuPlace[] lu) { // rang 0 de /lieu?cell=, nom servi, comme Lot873
            var lecture = Task.Run(() => { using (var c = new ClientLieu(port, ClientDeparts.DelaiMinimal)) return c.Lire(cellule); }); for (var e = Lot690.Attendre(lecture, "étape 1 : lecture /lieu?cell=" + N(cellule)); e.MoveNext();) yield return null;
            lu[0] = lecture.Result.Presente ? lecture.Result.Lieu.Bourg : throw Echec("étape 1 : /lieu?cell=" + N(cellule) + " absent : " + lecture.Result.Absence); if (lu[0]?.Nom == null) throw Echec("étape 1 : le rang 0 de /lieu?cell=" + N(cellule) + " n'a pas de nom servi : " + (lu[0]?.AbsenceDuNom ?? lecture.Result.Lieu.AbsenceDesLieux ?? "rang 0 absent")); }
        [ScenarioDeCapture(891, "plan-et-habitants")] static IEnumerator PlanEtHabitants(Camera camera) {
            var ouverte = new Lot549.CarteOuverte(); for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null;
            CarteDessinee carte = ouverte.Carte; CabinetDeCarte cabinet = carte.GetComponent<CabinetDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de CabinetDeCarte");
            DossierBourg dossier = carte.GetComponent<DossierBourg>() ?? throw Echec("étape 1 : le cabinet n'a pas de DossierBourg"); CalquesCarte calques = carte.GetComponent<CalquesCarte>() ?? throw Echec("étape 1 : le cabinet n'a pas de CalquesCarte");
            (carte.GetComponent<SurvolDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de survol")).automatique = true; (carte.GetComponent<ParcoursDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de parcours")).automatique = true;
            Transform toile = carte.transform.Find("Cabinet"); if (toile == null || !toile.gameObject.activeInHierarchy) throw Echec("étape 1 : la toile du cabinet n'est pas active");
            for (var e = Lot690.Jusqua(() => Lot690.LecturePrete(cabinet.Partie), () => "étape 1 : " + Lot690.Dire(cabinet.Partie)); e.MoveNext();) yield return null;
            FicheDeDepart[] mistra = cabinet.Partie.Departs.Donnees.Fiches.Where(f => f.Siege.Nom == SIEGE).ToArray(); if (mistra.Length != 1) throw Echec("étape 1 : " + mistra.Length + " fiche(s) au siège " + SIEGE + " : " + string.Join(", ", mistra.Select(f => f.Nom)));
            long id = mistra[0].CellId; string cellule = N(id); var lu = new LieuPlace[1]; for (var e = Bourg(carte.port, id, lu); e.MoveNext();) yield return null;
            string nom = lu[0].Nom; Vector3 local = carte.PositionSurLaCarte(lu[0].Position ?? throw Echec("étape 2 : le bourg « " + nom + " » n'a pas de point servi"), ReperesDeDepart.HAUTEUR_LIEU) ?? throw Echec("étape 2 : la carte ne place pas le bourg « " + nom + " »");
            Vector3 point = carte.transform.TransformPoint(local); carte.camera.aspect = Lot549.FORME; yield return null; carte.Vue.Zoomer(24, new Vector2(.5f, .5f)); float demi = carte.Vue.Demi;
            carte.Vue.Centrer(new Vector2(local.x - (VX - .5f) * 2f * demi * carte.Vue.Aspect, local.z - (VY - .5f) * 2f * demi), demi); yield return null;
            Vector3 vu = carte.camera.WorldToViewportPoint(point); if (!Zone(vu)) throw Echec("étape 2 : bourg en viewport " + vu.ToString("F3") + ", attendu x 0,68–0,98 et y 0,40–0,95");
            CelluleDeCarte moree = carte.CelluleSous(point); if (moree?.CellId != id) throw Echec("étape 2 : sous le bourg, la carte voit " + (moree == null ? "aucune cellule" : N(moree.CellId)) + ", attendu la Morée " + cellule); cabinet.Garder(moree);
            Button Bouton(string parent, string nomBouton) => toile.Find(parent)?.Find(nomBouton)?.GetComponent<Button>() ?? throw Echec("étape 3 : « " + parent + "/" + nomBouton + " » introuvable");
            Bouton("Territoire conservé", "Plan du bourg").onClick.Invoke(); Bouton("Parcourir le monde", "Habitants").onClick.Invoke();
            string Titre() => dossier.Document?.Annee is long ? DossierBourg.Entete(nom, dossier.Document) + " · Nord en haut · Consultation du plan" : null;
            string Legende() { var m = cabinet.Partie.Monde; return m?.Presente == true ? new RepartitionHabitants(m.Donnees.Monde).Legende + " · Rouge : territoire conservé" : null; }
            for (var e = Lot690.Jusqua(() => dossier.Etat != null && dossier.Etat.text == Titre() && calques.Legende != null && calques.Legende.text == Legende(), () => "étape 4 : titre « " + Ligne(dossier.Etat?.text) + " » / « " + Ligne(Titre()) + " » ; légende « " + Ligne(calques.Legende?.text) + " » / « " + Ligne(Legende()) + " »"); e.MoveNext();) yield return null;
            void Exiger(string moment) { // dans une même image, sans yield
                string titre = dossier.Etat.text, legende = calques.Legende.text; if (Environment.GetCommandLineArgs().Contains(TICK)) titre += " · tick " + dossier.Document.Tick.ToString(CultureInfo.InvariantCulture);
                foreach (string ecrit in new[] { titre, legende }) if ((TexteDuMonde.Interdit(ecrit, cellule) ?? TexteDuMonde.SansUnite(ecrit)) is string mot) throw Echec("mot interdit « " + mot + " » : « " + Ligne(ecrit) + " »"); if (titre != Titre()) throw Echec(moment + " : titre « " + Ligne(titre) + " », attendu « " + Ligne(Titre()) + " »"); if (legende != Legende()) throw Echec(moment + " : légende « " + Ligne(legende) + " », attendu « " + Ligne(Legende()) + " »"); }
            Exiger("étape 5"); foreach (string cache in new[] { "Fond des dossiers", "Votre maison" }) { var p = toile.Find(cache) ?? throw Echec("étape 6 : « " + cache + " » introuvable"); p.gameObject.SetActive(false); }
            Lot549.Photographier(camera, carte); camera.rect = new Rect(0f, 0f, 1f, 1f); camera.aspect = Lot549.FORME; Canvas cab = toile.GetComponent<Canvas>(); cab.renderMode = RenderMode.ScreenSpaceCamera; cab.worldCamera = camera; cab.planeDistance = camera.nearClipPlane + 0.2f; yield return null; Canvas.ForceUpdateCanvases();
            void Visible(string moment) { foreach (string nomPanneau in new[] { "Plan du bourg", "Parcourir le monde" }) { var cadre = (RectTransform)(toile.Find(nomPanneau) ?? throw Echec(moment + " : « " + nomPanneau + " » introuvable")); if (!cadre.gameObject.activeInHierarchy) throw Echec(moment + " : « " + nomPanneau + " » caché"); var coins = new Vector3[4]; cadre.GetWorldCorners(coins); foreach (Vector3 v in coins.Select(camera.WorldToViewportPoint)) if (v.z <= 0f || v.x < -0.01f || v.x > 1.01f || v.y < -0.01f || v.y > 1.01f) throw Echec(moment + " : « " + nomPanneau + " » coupé, coin " + v.ToString("F3")); if (!Zone(camera.WorldToViewportPoint(point))) throw Echec(moment + " : bourg hors de la zone, viewport " + camera.WorldToViewportPoint(point).ToString("F3")); } }
            Exiger("avant la pose"); Visible("avant la pose"); for (int i = 0; i < 10; i++) yield return null; Exiger("après la pose"); Visible("après la pose"); Debug.Log("CAPTURE_891 cellule " + cellule + " titre « " + Ligne(dossier.Etat.text) + " » légende « " + Ligne(calques.Legende.text) + " »");
        }
    }
}
