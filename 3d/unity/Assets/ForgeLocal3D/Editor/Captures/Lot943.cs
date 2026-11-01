using System; using System.Collections; using System.Globalization; using System.Linq; using System.Threading.Tasks;
using Forge.Interface; using Forge.Pont; using UnityEngine; using UnityEngine.UI;
namespace ForgeLocal3D.Captures {
    // Lot 943 : la Morée gardée en rouge, en couleurs des puissances ; « Parcourir le monde » entier, sa légende sans année seule.
    // Les deux légendes réellement affichées (habitants, puis puissances) passent `TexteDuMonde.Interdit` et `SansUnite`.
    // `-forge943Annee` remet l'ancienne légende « … de 1400 … » juste avant le dernier jugement : il rougit sur « 1400 ».
    static class Lot943 {
        const string SIEGE = "Mistra", GUIDE = "Parcourir le monde", ANNEE = "-forge943Annee", ANCIENNE = "Puissances de la carte de 1400 · Relief non transmis · Rouge : territoire conservé";
        const float VX = .36f, VY = .58f, DEMI_KM = 220f; // le bourg au-dessus du panneau (x ≤ 0,66 et y ≤ 0,20 de l'image)
        static string N(long v) => v.ToString(CultureInfo.InvariantCulture); static InvalidOperationException Echec(string cause) => new InvalidOperationException(cause);
        static string Ligne(string t) => (t ?? "(aucun)").Replace("\r", "").Replace("\n", " | "); static bool Zone(Vector3 v) => v.z > 0f && v.x >= .10f && v.x <= .62f && v.y >= .30f && v.y <= .88f;
        static IEnumerator Bourg(int port, long cellule, LieuPlace[] lu) { // rang 0 de /lieu?cell=, nom servi, comme Lot891
            var lecture = Task.Run(() => { using (var c = new ClientLieu(port, ClientDeparts.DelaiMinimal)) return c.Lire(cellule); }); for (var e = Lot690.Attendre(lecture, "étape 2 : lecture /lieu?cell=" + N(cellule)); e.MoveNext();) yield return null;
            lu[0] = lecture.Result.Presente ? lecture.Result.Lieu.Bourg : throw Echec("étape 2 : /lieu?cell=" + N(cellule) + " absent : " + lecture.Result.Absence); if (lu[0]?.Nom == null) throw Echec("étape 2 : le rang 0 de /lieu?cell=" + N(cellule) + " n'a pas de nom servi : " + (lu[0]?.AbsenceDuNom ?? lecture.Result.Lieu.AbsenceDesLieux ?? "rang 0 absent")); }
        // Les deux juges du clerc, appelés tels quels, sur le texte affiché.
        static void Juger(string texte, string cellule) {
            if (TexteDuMonde.Interdit(texte, cellule) is string mot) throw Echec("mot interdit « " + mot + " » dans la légende : « " + Ligne(texte) + " »");
            if (TexteDuMonde.SansUnite(texte) is string nombre) throw Echec("nombre sans unité « " + nombre + " » dans la légende : « " + Ligne(texte) + " »"); }
        [ScenarioDeCapture(943, "legende-des-puissances")] static IEnumerator LegendeDesPuissances(Camera camera) {
            var ouverte = new Lot549.CarteOuverte(); for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null;
            CarteDessinee carte = ouverte.Carte; CabinetDeCarte cabinet = carte.GetComponent<CabinetDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de CabinetDeCarte");
            CalquesCarte calques = carte.GetComponent<CalquesCarte>() ?? throw Echec("étape 1 : le cabinet n'a pas de CalquesCarte");
            (carte.GetComponent<SurvolDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de survol")).automatique = true; (carte.GetComponent<ParcoursDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de parcours")).automatique = true;
            Transform toile = carte.transform.Find("Cabinet"); if (toile == null || !toile.gameObject.activeInHierarchy) throw Echec("étape 1 : la toile du cabinet n'est pas active");
            for (var e = Lot690.Jusqua(() => Lot690.LecturePrete(cabinet.Partie), () => "étape 1 : " + Lot690.Dire(cabinet.Partie)); e.MoveNext();) yield return null;
            FicheDeDepart[] mistra = cabinet.Partie.Departs.Donnees.Fiches.Where(f => f.Siege.Nom == SIEGE).ToArray(); if (mistra.Length != 1) throw Echec("étape 2 : " + mistra.Length + " fiche(s) au siège " + SIEGE + " : " + string.Join(", ", mistra.Select(f => f.Nom)));
            long id = mistra[0].CellId; string cellule = N(id); var lu = new LieuPlace[1]; for (var e = Bourg(carte.port, id, lu); e.MoveNext();) yield return null;
            string nom = lu[0].Nom; Vector3 local = carte.PositionSurLaCarte(lu[0].Position ?? throw Echec("étape 2 : le bourg « " + nom + " » n'a pas de point servi"), ReperesDeDepart.HAUTEUR_LIEU) ?? throw Echec("étape 2 : la carte ne place pas le bourg « " + nom + " »");
            Vector3 point = carte.transform.TransformPoint(local); carte.camera.aspect = Lot549.FORME; yield return null; float demi = DEMI_KM; // la Morée rouge parmi les terres des autres puissances
            carte.Vue.Centrer(new Vector2(local.x - (VX - .5f) * 2f * demi * carte.Vue.Aspect, local.z - (VY - .5f) * 2f * demi), demi); yield return null;
            Vector3 vu = carte.camera.WorldToViewportPoint(point); if (!Zone(vu)) throw Echec("étape 2 : bourg en viewport " + vu.ToString("F3") + ", attendu x 0,10–0,62 et y 0,30–0,88");
            CelluleDeCarte moree = carte.CelluleSous(point); if (moree?.CellId != id) throw Echec("étape 2 : sous le bourg, la carte voit " + (moree == null ? "aucune cellule" : N(moree.CellId)) + ", attendu la Morée " + cellule); cabinet.Garder(moree);
            Button Bouton(string nomBouton) => toile.Find(GUIDE)?.Find(nomBouton)?.GetComponent<Button>() ?? throw Echec("« " + GUIDE + "/" + nomBouton + " » introuvable");
            string Habitants() { var m = cabinet.Partie.Monde; return m?.Presente == true ? CalquesCarte.LegendeDuCalque(new RepartitionHabitants(m.Donnees.Monde)) : null; }
            Bouton("Habitants").onClick.Invoke();
            for (var e = Lot690.Jusqua(() => calques.Legende != null && calques.Legende.text == Habitants(), () => "étape 3 : légende « " + Ligne(calques.Legende?.text) + " », attendu « " + Ligne(Habitants()) + " »"); e.MoveNext();) yield return null;
            string habitants = calques.Legende.text; Juger(habitants, cellule);
            string puissances = CalquesCarte.LegendeDuCalque(null); Bouton("Puissances").onClick.Invoke();
            for (var e = Lot690.Jusqua(() => calques.Legende.text == puissances, () => "étape 4 : légende « " + Ligne(calques.Legende.text) + " », attendu « " + Ligne(puissances) + " »"); e.MoveNext();) yield return null;
            void Exiger(string moment, bool dernier) { // dans une même image, sans yield
                string texte = calques.Legende.text; if (dernier && Environment.GetCommandLineArgs().Contains(ANNEE)) texte = ANCIENNE;
                Juger(texte, cellule); if (texte != puissances) throw Echec(moment + " : légende « " + Ligne(texte) + " », attendu « " + Ligne(puissances) + " »"); }
            Exiger("étape 4", false); foreach (string cache in new[] { "Fond des dossiers", "Votre maison" }) { var p = toile.Find(cache) ?? throw Echec("étape 5 : « " + cache + " » introuvable"); p.gameObject.SetActive(false); }
            Lot549.Photographier(camera, carte); camera.rect = new Rect(0f, 0f, 1f, 1f); camera.aspect = Lot549.FORME; Canvas cab = toile.GetComponent<Canvas>(); cab.renderMode = RenderMode.ScreenSpaceCamera; cab.worldCamera = camera; cab.planeDistance = camera.nearClipPlane + 0.2f; yield return null; Canvas.ForceUpdateCanvases();
            void Visible(string moment) {
                var cadre = (RectTransform)(toile.Find(GUIDE) ?? throw Echec(moment + " : « " + GUIDE + " » introuvable")); if (!cadre.gameObject.activeInHierarchy) throw Echec(moment + " : « " + GUIDE + " » caché");
                var coins = new Vector3[4]; cadre.GetWorldCorners(coins); foreach (Vector3 v in coins.Select(camera.WorldToViewportPoint)) if (v.z <= 0f || v.x < -0.01f || v.x > 1.01f || v.y < -0.01f || v.y > 1.01f) throw Echec(moment + " : « " + GUIDE + " » coupé, coin " + v.ToString("F3"));
                foreach (string nomBouton in new[] { "Puissances", "Habitants" }) if (!Bouton(nomBouton).gameObject.activeInHierarchy) throw Echec(moment + " : bouton « " + nomBouton + " » caché");
                if (!Zone(camera.WorldToViewportPoint(point))) throw Echec(moment + " : bourg hors de la zone, viewport " + camera.WorldToViewportPoint(point).ToString("F3")); }
            Exiger("avant la pose", false); Visible("avant la pose"); for (int i = 0; i < 10; i++) yield return null; Exiger("après la pose", true); Visible("après la pose");
            Debug.Log("CAPTURE_943 cellule " + cellule + " bourg « " + nom + " » légende des habitants « " + Ligne(habitants) + " » légende des puissances « " + Ligne(calques.Legende.text) + " »");
        }
    }
}
