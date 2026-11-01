using System; using System.Collections; using System.Collections.Generic; using System.Globalization; using System.Linq; using System.Threading.Tasks;
using Forge.Interface; using Forge.Pont; using UnityEngine; using UnityEngine.EventSystems; using UnityEngine.UI;

namespace ForgeLocal3D.Captures
{
    // Lot 880 : la Morée survolée. Le feuillet dit les trois premières lignes du dossier, puis la phrase de « Pause / Reprendre ». `-forge880Voisin` garde le voisin : les textes divergent.
    static class Lot880
    {
        const string SIEGE = "Mistra", DOSSIER = "Territoire conservé", BOUTON = "Pause / Reprendre", VOISIN = "-forge880Voisin";
        const int IMAGES_DE_POSE = 10, LARGEUR = 1600, HAUTEUR = 900; const float CARRE = 48;
        static CarteDessinee carte; static CabinetDeCarte cabinet; static FicheDeCellule fiche; static InfobulleDeTerre terre; static DossierTerritoire dossier; static Transform toile; static Vector3 bourg;
        static string N(long v) => v.ToString(CultureInfo.InvariantCulture); static InvalidOperationException Echec(string cause) => new InvalidOperationException(cause);
        static string Ecran(Vector2 p) => "(" + Mathf.RoundToInt(p.x) + ", " + Mathf.RoundToInt(p.y) + ")"; static string Ecran(Rect r) => "[" + Ecran(r.min) + " – " + Ecran(r.max) + "]";
        static string Ligne(string texte, int i = 0) { var l = (texte ?? "(aucun texte)").Split('\n'); return i < l.Length ? l[i] : "(aucune ligne " + (i + 1) + ")"; }
        static IEnumerator Lieu(int port, long cellule, string etape, LieuPlace[] lu)
        {
            var lecture = Task.Run(() => { using (var c = new ClientLieu(port, ClientDeparts.DelaiMinimal)) return c.Lire(cellule); });
            for (var e = Lot690.Attendre(lecture, etape + " : lecture /lieu?cell=" + N(cellule)); e.MoveNext();) yield return null;
            lu[0] = lecture.Result.Presente ? lecture.Result.Lieu.Bourg : throw Echec(etape + " : /lieu?cell=" + N(cellule) + " absent : " + lecture.Result.Absence);
            if (lu[0]?.Nom == null || lu[0].Position == null) throw Echec(etape + " : le rang 0 de " + N(cellule) + " n'a pas de nom ou de point : " + (lu[0]?.AbsenceDuNom ?? lu[0]?.AbsenceDePopulation ?? "rang 0 absent"));
        }

        static Rect Feuillet(Camera camera, Vector2 point, string attendu, string ou)
        {
            RectTransform[] feuillets = toile.GetComponentsInChildren<RectTransform>().Where(t => t.name == "Infobulle").ToArray();
            if (feuillets.Length != 1) throw Echec(ou + " : " + feuillets.Length + " feuillet(s) actif(s), attendu un seul");
            string dit = feuillets[0].GetComponentInChildren<Text>(true)?.text; if (dit != attendu) throw Echec(ou + " : le feuillet dit « " + dit + " », attendu « " + attendu + " »");
            var c = new Vector3[4]; feuillets[0].GetWorldCorners(c); Vector2[] e = c.Select(v => RectTransformUtility.WorldToScreenPoint(camera, v)).ToArray();
            Rect r = Rect.MinMaxRect(e.Min(p => p.x), e.Min(p => p.y), e.Max(p => p.x), e.Max(p => p.y)), ecran = camera.pixelRect;
            if (r.xMin < ecran.xMin - .5f || r.yMin < ecran.yMin - .5f || r.xMax > ecran.xMax + .5f || r.yMax > ecran.yMax + .5f) throw Echec(ou + " : feuillet " + Ecran(r) + " coupé par l'image " + Ecran(ecran));
            if (Rect.MinMaxRect(r.xMin + .5f, r.yMin + .5f, r.xMax - .5f, r.yMax - .5f).Overlaps(new Rect(point - Vector2.one * CARRE / 2, Vector2.one * CARRE))) throw Echec(ou + " : feuillet " + Ecran(r) + " sur le point " + Ecran(point));
            return r;
        }
        static void DansLImage(Camera camera, RectTransform cadre, string ou)
        {
            var c = new Vector3[4]; cadre.GetWorldCorners(c); Rect ecran = camera.pixelRect;
            foreach (Vector2 v in c.Select(p => (Vector2)RectTransformUtility.WorldToScreenPoint(camera, p)))
                if (v.x < ecran.xMin - .5f || v.y < ecran.yMin - .5f || v.x > ecran.xMax + .5f || v.y > ecran.yMax + .5f) throw Echec(ou + " : « " + cadre.name + " » coupé, coin " + Ecran(v));
        }
        [ScenarioDeCapture(880, "1-terre-survolee")] static IEnumerator TerreSurvolee(Camera camera)
        {
            var ouverte = new Lot549.CarteOuverte(); for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null;
            carte = ouverte.Carte; cabinet = carte.GetComponent<CabinetDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de CabinetDeCarte");
            fiche = carte.GetComponent<FicheDeCellule>() ?? throw Echec("étape 1 : la carte n'a pas de fiche"); dossier = carte.GetComponent<DossierTerritoire>() ?? throw Echec("étape 1 : le cabinet n'a pas de dossier");
            InfobulleDeTerre[] bulles = carte.GetComponents<InfobulleDeTerre>(); terre = bulles.Length == 1 ? bulles[0] : throw Echec("étape 1 : " + bulles.Length + " InfobulleDeTerre, attendu une seule");
            toile = carte.transform.Find("Cabinet"); if (toile == null || !toile.gameObject.activeInHierarchy) throw Echec("étape 1 : la toile du cabinet n'est pas active");
            (carte.GetComponent<SurvolDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de survol")).automatique = true; (carte.GetComponent<ParcoursDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de parcours")).automatique = true; terre.automatique = true;
            for (var e = Lot690.Jusqua(() => Lot690.LecturePrete(cabinet.Partie), () => "étape 1 : " + Lot690.Dire(cabinet.Partie)); e.MoveNext();) yield return null;
            FicheDeDepart[] mistra = cabinet.Partie.Departs.Donnees.Fiches.Where(f => f.Siege.Nom == SIEGE).ToArray();
            if (mistra.Length != 1) throw Echec("étape 2 : " + mistra.Length + " fiche(s) au siège " + SIEGE + ", attendu une seule");
            long id = mistra[0].CellId; var lu = new LieuPlace[1]; for (var e = Lieu(carte.port, id, "étape 2", lu); e.MoveNext();) yield return null;
            string nom = lu[0].Nom; Vector3 local = carte.PositionSurLaCarte(lu[0].Position.Value, ReperesDeDepart.HAUTEUR_LIEU) ?? throw Echec("étape 2 : la carte ne place pas le bourg"); bourg = carte.transform.TransformPoint(local);
            carte.Vue.Zoomer(12, carte.camera.WorldToViewportPoint(bourg)); carte.Vue.Centrer(new Vector2(local.x, local.z), carte.Vue.Demi); yield return null;
            (carte.GetComponent<SurvolDeCarte>()).Survoler(carte.camera.WorldToScreenPoint(bourg));
            if (fiche.Survolee?.CellId != id) throw Echec("étape 2 : sous le bourg, la fiche voit " + fiche.Survolee?.CellId + ", attendu la Morée " + N(id));
            bool voisin = Environment.GetCommandLineArgs().Contains(VOISIN); CelluleDeCarte retenue = fiche.Survolee;
            if (voisin && mistra[0].Voisins.Count == 0) throw Echec("étape 2 : la Morée n'a aucun voisin servi (" + VOISIN + ")");
            if (voisin) for (var e = Lieu(carte.port, mistra[0].Voisins[0].CellId, "étape 2 (" + VOISIN + ")", lu); e.MoveNext();) yield return null;
            if (voisin && lu[0].Nom == nom) throw Echec("étape 2 : le voisin a le même nom de bourg que la Morée, « " + nom + " »");
            if (voisin) { Vector3 localV = carte.PositionSurLaCarte(lu[0].Position.Value, ReperesDeDepart.HAUTEUR_LIEU) ?? throw Echec("étape 2 : la carte ne place pas le bourg du voisin");
                retenue = carte.CelluleSous(carte.transform.TransformPoint(localV)) ?? throw Echec("étape 2 : aucune cellule sous le bourg du voisin « " + lu[0].Nom + " »"); }
            cabinet.Garder(retenue); Text texte = toile.Find(DOSSIER)?.Find("Lecture du territoire")?.GetComponentInChildren<Text>(true) ?? throw Echec("étape 2 : le texte du dossier est introuvable");
            Lot549.Photographier(camera, carte); camera.rect = new Rect(0, 0, 1, 1); camera.targetTexture = new RenderTexture(LARGEUR, HAUTEUR, 24); camera.ResetAspect();
            Canvas cab = toile.GetComponent<Canvas>(); cab.renderMode = RenderMode.ScreenSpaceCamera; cab.worldCamera = camera; cab.planeDistance = camera.nearClipPlane + 0.2f;
            yield return null; Canvas.ForceUpdateCanvases(); Vector3 vu = camera.WorldToScreenPoint(bourg); if (vu.z <= 0) throw Echec("étape 3 : le bourg est derrière la caméra"); Vector2 P = vu;
            string ecart = null; string debut = nom + " · ";
            bool Aligne()
            {
                terre.Pas(P, fiche.Survolee, Time.realtimeSinceStartupAsDouble);
                if (!(terre.TexteAffiche ?? "").StartsWith(debut, StringComparison.Ordinal)) return false;
                if (dossier.Document == null || terre.Lecture?.Document == null || dossier.Document.Tick != terre.Lecture.Document.Tick) return false;
                string[] a = terre.TexteAffiche.Split('\n'), b = (texte.text ?? "").Split('\n');
                if (a.Length >= 3 && b.Length >= 3 && a[0] == b[0] && a[1] == b[1] && a[2] == b[2]) { ecart = null; return true; }
                string[] c = DossierTerritoire.Texte(null, dossier.Document, cabinet.Retenue.CellId).Split('\n');
                if (a.Length >= 3 && c.Length >= 3 && a[0] == c[0] && a[1] == c[1] && a[2] == c[2]) return false;
                ecart = (terre.TexteAffiche ?? "(nulle)") + " || " + (texte.text ?? "(nul)"); return true;
            }
            for (var e = Lot690.Jusqua(Aligne, () => "étape 4 : infobulle « " + Ligne(terre.TexteAffiche) + " », dossier « " + Ligne(texte.text) + " », ticks " + dossier.Document?.Tick + "/" + terre.Lecture?.Document?.Tick); e.MoveNext();) yield return null;
            if (ecart != null) throw Echec("l'infobulle et la fiche diffèrent : " + ecart);
            Rect Scene(string ou)
            {
                Rect r = Feuillet(camera, P, terre.TexteAffiche, ou); Transform vieille = carte.transform.Find("Toile de la fiche");
                if (vieille == null || vieille.gameObject.activeInHierarchy) throw Echec(ou + " : « Toile de la fiche » " + (vieille == null ? "absente" : "encore active"));
                Canvas[] toiles = carte.GetComponentsInChildren<Canvas>(); if (toiles.Length != 1 || toiles[0].name != "Cabinet") throw Echec(ou + " : " + toiles.Length + " toile(s) active(s), attendu « Cabinet » seul");
                DansLImage(camera, (RectTransform)toile.Find(DOSSIER), ou); return r;
            }
            Scene("étape 5");
            for (int i = 0; i < IMAGES_DE_POSE; i++) { terre.Pas(P, fiche.Survolee, Time.realtimeSinceStartupAsDouble); yield return null; }
            if (!Aligne() || ecart != null) throw Echec(ecart != null ? "l'infobulle et la fiche diffèrent : " + ecart : "étape 6 : l'infobulle n'a plus les lignes du dossier");
            Rect pose = Scene("étape 6");
            Debug.Log("CAPTURE_880 cellule " + N(fiche.Survolee.CellId) + " point " + Ecran(P) + " feuillet " + Ecran(pose) + " « " + Ligne(terre.TexteAffiche) + " | " + Ligne(terre.TexteAffiche, 1) + " | " + Ligne(terre.TexteAffiche, 2) + " » tick " + terre.Lecture.Document.Tick);
        }
        [ScenarioDeCapture(880, "2-bouton-survole")] static IEnumerator BoutonSurvole(Camera camera)
        {
            if (carte == null || terre == null || fiche == null || toile == null) throw Echec("étape 7 : la carte du scénario 1 manque");
            if (carte.camera != null && !carte.camera.enabled) carte.camera.enabled = true;
            Button[] temps = toile.GetComponentsInChildren<Button>(true).Where(b => b.name == BOUTON).ToArray();
            if (temps.Length != 1) throw Echec("étape 7 : " + temps.Length + " bouton(s) « " + BOUTON + " », attendu un seul"); Button bouton = temps[0];
            var coins = new Vector3[4]; ((RectTransform)bouton.transform).GetWorldCorners(coins); Vector2 B = RectTransformUtility.WorldToScreenPoint(camera, (coins[0] + coins[2]) / 2);
            EventSystem evenements = EventSystem.current ?? throw Echec("étape 7 : aucun EventSystem courant");
            var touches = new List<RaycastResult>(); evenements.RaycastAll(new PointerEventData(evenements) { position = B }, touches);
            if (touches.Count == 0 || (touches[0].gameObject.transform != bouton.transform && !touches[0].gameObject.transform.IsChildOf(bouton.transform))) throw Echec("étape 7 : au point " + Ecran(B) + ", le premier sous le pointeur est « " + (touches.Count == 0 ? "rien" : touches[0].gameObject.name) + " », pas « " + BOUTON + " »");
            string phrase = (bouton.GetComponent<Infobulle>() ?? throw Echec("étape 7 : « " + BOUTON + " » n'a pas d'Infobulle")).Phrase;
            fiche.Quitter(); ExecuteEvents.Execute(bouton.gameObject, new PointerEventData(evenements) { position = B }, ExecuteEvents.pointerEnterHandler); terre.Pas(B, null, Time.realtimeSinceStartupAsDouble);
            void Vue(string ou) { if (terre.TexteAffiche != null) throw Echec(ou + " : TexteAffiche vaut « " + terre.TexteAffiche + " », attendu nul"); Feuillet(camera, B, phrase, ou); }
            Vue("étape 7"); for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null; Rect pose = Feuillet(camera, B, phrase, "étape 8"); Vue("étape 8");
            Debug.Log("CAPTURE_880 point " + Ecran(B) + " au centre de « " + BOUTON + " » feuillet " + Ecran(pose) + " « " + phrase + " »");
        }
    }
}
