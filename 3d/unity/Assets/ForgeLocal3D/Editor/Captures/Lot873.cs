using System; using System.Collections; using System.Globalization; using System.Linq; using System.Threading.Tasks;
using Forge.Interface; using Forge.Pont; using UnityEngine; using UnityEngine.UI;

namespace ForgeLocal3D.Captures
{
    // Lot 873 : la Morée gardée sur la carte de 1400. « Territoire conservé » s'ouvre sur le nom de son bourg et la maison de son maître, puis la date servie ;
    // « Votre maison » montre l'aperçu de la Morée, « … habitants autour de Mistra ». `-forge873Voisin` attend le bourg du premier voisin : il rougit.
    static class Lot873
    {
        const string SIEGE = "Mistra", MAISON = "Votre maison", DOSSIER = "Territoire conservé", APERCU = "Consultez une maison avant de vous engager.", VOISIN = "-forge873Voisin";
        static string N(long v) => v.ToString(CultureInfo.InvariantCulture); static InvalidOperationException Echec(string cause) => new InvalidOperationException(cause);
        static string Ligne(string texte, int i = 0) { var l = (texte ?? "(aucun texte)").Split('\n'); return i < l.Length ? l[i] : "(aucune ligne " + (i + 1) + ")"; }
        static IEnumerator Bourg(int port, long cellule, string etape, LieuPlace[] lu) // le rang 0 de /lieu?cell=, avec son nom servi
        {
            var lecture = Task.Run(() => { using (var c = new ClientLieu(port, ClientDeparts.DelaiMinimal)) return c.Lire(cellule); }); for (var e = Lot690.Attendre(lecture, etape + " : lecture /lieu?cell=" + N(cellule)); e.MoveNext();) yield return null;
            lu[0] = lecture.Result.Presente ? lecture.Result.Lieu.Bourg : throw Echec(etape + " : /lieu?cell=" + N(cellule) + " absent : " + lecture.Result.Absence);
            if (lu[0]?.Nom == null) throw Echec(etape + " : le rang 0 de /lieu?cell=" + N(cellule) + " n'a pas de nom servi : " + (lu[0]?.AbsenceDuNom ?? lecture.Result.Lieu.AbsenceDesLieux ?? "rang 0 absent"));
        }
        [ScenarioDeCapture(873, "moree-en-noms")] static IEnumerator MoreeEnNoms(Camera camera)
        {
            var ouverte = new Lot549.CarteOuverte(); for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null;
            CarteDessinee carte = ouverte.Carte; CabinetDeCarte cabinet = carte.GetComponent<CabinetDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de CabinetDeCarte"); DossierTerritoire dossier = carte.GetComponent<DossierTerritoire>() ?? throw Echec("étape 1 : le cabinet n'a pas de DossierTerritoire");
            (carte.GetComponent<SurvolDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de survol")).automatique = true; (carte.GetComponent<ParcoursDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de parcours")).automatique = true;
            Transform toile = carte.transform.Find("Cabinet"); if (toile == null || !toile.gameObject.activeInHierarchy) throw Echec("étape 1 : la toile du cabinet n'est pas active");
            for (var e = Lot690.Jusqua(() => Lot690.LecturePrete(cabinet.Partie), () => "étape 1 : " + Lot690.Dire(cabinet.Partie)); e.MoveNext();) yield return null;
            FicheDeDepart[] mistra = cabinet.Partie.Departs.Donnees.Fiches.Where(f => f.Siege.Nom == SIEGE).ToArray();
            if (mistra.Length != 1) throw Echec("étape 2 : " + mistra.Length + " fiche(s) au siège " + SIEGE + " : " + string.Join(", ", mistra.Select(f => f.Nom)) + ", attendu une seule");
            FicheDeDepart fiche = mistra[0]; long id = fiche.CellId; string cellule = N(id); var lu = new LieuPlace[1]; for (var e = Bourg(carte.port, id, "étape 2", lu); e.MoveNext();) yield return null;
            string nomBourg = lu[0].Nom; PointCarte position = lu[0].Position ?? throw Echec("étape 2 : le bourg de la Morée n'a pas de point servi");
            Vector3 local = carte.PositionSurLaCarte(position, ReperesDeDepart.HAUTEUR_LIEU) ?? throw Echec("étape 2 : la carte ne place pas le bourg"); Vector3 point = carte.transform.TransformPoint(local);
            carte.Vue.Zoomer(12, carte.camera.WorldToViewportPoint(point)); carte.Vue.Centrer(new Vector2(local.x, local.z), carte.Vue.Demi); yield return null; // la carte se recadre
            CelluleDeCarte moree = carte.CelluleSous(point); if (moree?.CellId != id) throw Echec("étape 2 : sous le bourg, la carte voit la cellule " + moree?.CellId + ", attendu la Morée " + cellule);
            cabinet.Garder(moree); Transform maison = toile.Find(MAISON) ?? throw Echec("étape 3 : panneau « " + MAISON + " » introuvable");
            Button[] boutons = (maison.Find("Maisons proposées") ?? throw Echec("étape 3 : « Maisons proposées » introuvable")).GetComponentsInChildren<Button>().Where(b => b.GetComponentInChildren<Text>()?.text == fiche.Maison).ToArray();
            if (boutons.Length != 1) throw Echec("étape 3 : " + boutons.Length + " bouton(s) « " + fiche.Maison + " » dans « " + MAISON + "/Maisons proposées », attendu un seul");
            boutons[0].onClick.Invoke(); Text apercu = maison.GetComponentsInChildren<Text>(true).FirstOrDefault(t => t.name == APERCU) ?? throw Echec("étape 3 : l'aperçu du choix est introuvable");
            string habitants = TexteDuMonde.Nombre(fiche.Habitants) + " habitants autour de " + SIEGE;
            for (var e = Lot690.Jusqua(() => apercu.text.Contains(habitants), () => "étape 3 : l'aperçu dit « " + apercu.text.Replace("\n", " | ") + " », attendu « " + habitants + " »"); e.MoveNext();) yield return null;
            bool voisin = Environment.GetCommandLineArgs().Contains(VOISIN); if (voisin && fiche.Voisins.Count == 0) throw Echec("étape 4 : la Morée n'a aucun voisin servi (" + VOISIN + ")");
            if (voisin) for (var e = Bourg(carte.port, fiche.Voisins[0].CellId, "étape 4 (" + VOISIN + ")", lu); e.MoveNext();) yield return null;
            string attendu = !voisin ? nomBourg : lu[0].Nom != nomBourg ? lu[0].Nom : throw Echec("étape 4 : le voisin a le même nom de bourg que la Morée, « " + nomBourg + " »"), debut = attendu + " · ";
            Text texte = toile.Find(DOSSIER)?.Find("Lecture du territoire")?.GetComponentInChildren<Text>(true) ?? throw Echec("étape 4 : le texte du dossier « " + DOSSIER + " » est introuvable");
            for (var e = Lot690.Jusqua(() => cabinet.Retenue?.CellId == id && texte.text.StartsWith(debut, StringComparison.Ordinal),
                () => "étape 4 : le dossier commence par « " + Ligne(texte.text) + " », attendu « " + debut + "… »" + (voisin ? " (bourg du voisin, " + VOISIN + ")" : "")); e.MoveNext();) yield return null;
            void Exiger(string moment) // la première ligne, la date du document lu, les deux juges sur le dossier et l'aperçu
            {
                string tete = " ; première ligne « " + Ligne(texte.text) + " »", date = dossier.Document?.Annee is long an ? TexteDuMonde.Date(new DateDuMonde(an, dossier.Document.JourDeLAnnee.Value)) : "(document non daté)";
                if (cabinet.Retenue?.CellId != id || !texte.text.StartsWith(debut, StringComparison.Ordinal) || Ligne(texte.text, 1) != date) throw Echec(moment + " : retenue " + cabinet.Retenue?.CellId + ", deuxième ligne « " + Ligne(texte.text, 1) + " », attendu « " + date + " »" + tete);
                foreach (var (nom, ecrit) in new[] { ("le dossier", texte.text), ("l'aperçu", apercu.text) }) if ((TexteDuMonde.Interdit(ecrit, cellule) ?? TexteDuMonde.SansUnite(ecrit)) is string mot) throw Echec(moment + " : " + nom + " montre « " + mot + " » ; première ligne « " + Ligne(ecrit) + " »");
                if (!apercu.text.Contains(habitants)) throw Echec(moment + " : l'aperçu ne dit plus « " + habitants + " » : « " + apercu.text.Replace("\n", " | ") + " »");
            }
            Exiger("étape 4"); Lot549.Photographier(camera, carte); camera.rect = new Rect(0, 0, 1, 1); Canvas cabinetToile = toile.GetComponent<Canvas>(); // la toile overlay se dessine sur la caméra reçue
            cabinetToile.renderMode = RenderMode.ScreenSpaceCamera; cabinetToile.worldCamera = camera; cabinetToile.planeDistance = camera.nearClipPlane + 0.2f; yield return null; Canvas.ForceUpdateCanvases();
            void Visible() // les deux panneaux entiers, la fenêtre du dossier où son texte commence, et le bourg gardé
            {
                foreach (var cadre in new[] { (RectTransform)maison, (RectTransform)texte.transform.parent.parent, (RectTransform)texte.transform.parent }) { var c = new Vector3[4]; cadre.GetWorldCorners(c);
                    foreach (Vector3 v in c.Select(camera.WorldToViewportPoint)) if (v.z <= 0f || v.x < -0.01f || v.x > 1.01f || v.y < -0.01f || v.y > 1.01f) throw Echec("photo : « " + cadre.name + " » coupé, coin " + v.ToString("F3")); }
                if (Mathf.Abs(texte.rectTransform.anchoredPosition.y) > 0.5f) throw Echec("photo : le dossier a défilé de " + texte.rectTransform.anchoredPosition.y + " px, sa première ligne est cachée");
                Vector3 vu = camera.WorldToViewportPoint(point); if (vu.z <= 0 || vu.x < 0 || vu.x > 1 || vu.y < 0 || vu.y > 1) throw Echec("photo : le bourg de la Morée est hors champ " + vu.ToString("F3"));
            }
            Visible(); for (int i = 0; i < 10; i++) yield return null; Exiger("après la pose"); Visible();
            Debug.Log("CAPTURE_873 Morée cellule " + cellule + " ; dossier « " + Ligne(texte.text) + " | " + Ligne(texte.text, 1) + " » ; aperçu « " + Ligne(apercu.text) + " | " + Ligne(apercu.text, 1) + " »");
        }
    }
}
