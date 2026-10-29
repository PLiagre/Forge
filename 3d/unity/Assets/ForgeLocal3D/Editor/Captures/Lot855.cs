using System;
using System.Collections;
using System.Globalization;
using System.Linq;
using System.Threading.Tasks;
using Forge.Interface;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;

namespace ForgeLocal3D.Captures
{
    // Lot 855 : la Morée choisie d'un clic gauche sur la carte de 1400, son dossier « Territoire conservé » ouvert à droite. Avant, un clic sur
    // « Parcourir le monde » et un glisser de 40 px ne gardent rien ; Échap ferme le dossier avant d'ouvrir le menu. Les gestes passent par
    // `CabinetDeCarte.Noter` comme le fait son Update, sans image entre l'appui et le relâché. `-forge855Glisser` remplace le clic par le glisser : il rougit.
    static class Lot855
    {
        const string SIEGE = "Mistra", TERRE = "Despotat de Morée", GUIDE = "Parcourir le monde", DOSSIER = "Territoire conservé", GLISSER = "-forge855Glisser";
        const int IMAGES_DE_POSE = 10; const float CRANS = 12, PAS_PX = 40;
        static string N(long v) => v.ToString(CultureInfo.InvariantCulture); static string Ligne(string texte) => texte == null ? "(aucun texte)" : texte.Split('\n')[0];
        static InvalidOperationException Echec(string cause) => new InvalidOperationException(cause); static string Ecran(Vector2 p) => "(" + Mathf.RoundToInt(p.x) + ", " + Mathf.RoundToInt(p.y) + ")";
        static bool Toucher(CabinetDeCarte cabinet, Vector2 appui, Vector2 relache, CelluleDeCarte sous) // HorsCarte n'est calculé qu'à l'appui et au relâché
            => cabinet.Noter(appui, true, false, cabinet.HorsCarte(appui), sous) | cabinet.Noter(relache, false, false, false, sous) | cabinet.Noter(relache, false, true, cabinet.HorsCarte(relache), sous);

        [ScenarioDeCapture(855, "moree-choisie-d-un-clic")]
        static IEnumerator MoreeChoisieDUnClic(Camera camera)
        {
            var ouverte = new Lot549.CarteOuverte(); for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null;
            CarteDessinee carte = ouverte.Carte; CabinetDeCarte cabinet = carte.GetComponent<CabinetDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de CabinetDeCarte");
            MenuCabinet menu = carte.GetComponent<MenuCabinet>() ?? throw Echec("étape 1 : le cabinet n'a pas de MenuCabinet");
            FicheDeCellule fiche = carte.GetComponent<FicheDeCellule>() ?? throw Echec("étape 1 : la carte n'a pas de fiche de cellule");
            (carte.GetComponent<SurvolDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de survol")).automatique = true; (carte.GetComponent<ParcoursDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de parcours")).automatique = true;
            Transform toile = carte.transform.Find("Cabinet"); if (toile == null || !toile.gameObject.activeInHierarchy) throw Echec("étape 1 : la toile du cabinet n'est pas active");
            for (var e = Lot690.Jusqua(() => Lot690.LecturePrete(cabinet.Partie), () => "étape 1 : " + Lot690.Dire(cabinet.Partie)); e.MoveNext();) yield return null;
            if (cabinet.Retenue != null) throw Echec("étape 1 : une terre est déjà gardée avant tout geste : " + N(cabinet.Retenue.CellId));

            FicheDeDepart[] mistra = cabinet.Partie.Departs.Donnees.Fiches.Where(f => f.Siege.Nom == SIEGE).ToArray();
            if (mistra.Length != 1 || mistra[0].Nom != TERRE) throw Echec("étape 2 : fiches au siège " + SIEGE + " : " + string.Join(", ", mistra.Select(f => f.Nom)) + ", attendu « " + TERRE + " » seule");
            long cellule = mistra[0].CellId;
            var lecture = Task.Run(() => { using (var c = new ClientLieu(carte.port, ClientDeparts.DelaiMinimal)) return c.Lire(cellule); });
            for (var e = Lot690.Attendre(lecture, "étape 2 : lecture /lieu?cell=" + N(cellule)); e.MoveNext();) yield return null;
            if (!lecture.Result.Presente || !(lecture.Result.Lieu.Bourg?.Position is PointCarte position))
                throw Echec("étape 2 : /lieu?cell=" + N(cellule) + " sans point au rang 0 : " + (lecture.Result.Absence ?? lecture.Result.Lieu.AbsenceDesLieux ?? "rang 0 absent ou sans point"));
            string bourg = lecture.Result.Lieu.Bourg.Nom ?? throw Echec("étape 2 : le rang 0 de la Morée n'a pas de nom servi : " + lecture.Result.Lieu.Bourg.AbsenceDuNom); // lot #873 : le dossier s'ouvre sur lui
            Vector3 local = carte.PositionSurLaCarte(position, ReperesDeDepart.HAUTEUR_LIEU) ?? throw Echec("étape 2 : la carte ne place pas le point du lieu"); Vector3 point = carte.transform.TransformPoint(local);
            carte.Vue.Zoomer(CRANS, carte.camera.WorldToViewportPoint(point)); carte.Vue.Centrer(new Vector2(local.x, local.z), carte.Vue.Demi);
            yield return null; // la carte se recadre
            Vector2 P = carte.camera.WorldToScreenPoint(point); fiche.Survoler(P); CelluleDeCarte moree = fiche.Survolee; fiche.Quitter();
            if (moree?.CellId != cellule || carte.CelluleSous(point)?.CellId != cellule) throw Echec("étape 2 : au point " + Ecran(P) + ", la carte voit la cellule " + moree?.CellId + ", attendu la Morée " + N(cellule));
            if (cabinet.HorsCarte(P)) throw Echec("étape 2 : le point de la Morée " + Ecran(P) + " est hors de la carte ou sous un panneau");

            RectTransform guide = toile.Cast<Transform>().OfType<RectTransform>().SingleOrDefault(t => t.name == GUIDE) ?? throw Echec("étape 3 : panneau « " + GUIDE + " » introuvable");
            var coins = new Vector3[4]; guide.GetWorldCorners(coins); Vector2 Q = RectTransformUtility.WorldToScreenPoint(null, (coins[0] + coins[2]) / 2);
            if (!carte.camera.pixelRect.Contains(Q)) throw Echec("étape 3 : « " + GUIDE + " » en " + Ecran(Q) + " n'est pas au-dessus de la vue de la carte " + carte.camera.pixelRect);
            if (!cabinet.HorsCarte(Q)) throw Echec("étape 3 : HorsCarte faux sur « " + GUIDE + " » en " + Ecran(Q) + " : le clic traverserait le panneau");
            bool panneau = cabinet.Noter(Q, true, false, true, moree) | cabinet.Noter(Q, false, true, true, moree);
            if (panneau || cabinet.Retenue != null) throw Echec("étape 3 : un clic sur « " + GUIDE + " » a gardé la cellule " + cabinet.Retenue?.CellId);

            Vector2 loin = P + new Vector2(PAS_PX, 0); bool glisse = Toucher(cabinet, P, loin, moree);
            if (glisse || cabinet.Retenue != null) throw Echec("étape 4 : un glisser de " + PAS_PX + " px a gardé la cellule " + cabinet.Retenue?.CellId);

            Text texte = toile.Cast<Transform>().FirstOrDefault(t => t.name == DOSSIER)?.Find("Lecture du territoire")?.GetComponentInChildren<Text>(true) ?? throw Echec("étape 5 : le texte du dossier « " + DOSSIER + " » est introuvable");
            bool glisser = Environment.GetCommandLineArgs().Contains(GLISSER), clic = false; string debut = bourg + " · ", ferme = null; bool Dossier() => texte.text.StartsWith(debut, StringComparison.Ordinal) && texte.text.Split('\n').Length > 1 && texte.text.Split('\n')[1].StartsWith("jour", StringComparison.Ordinal);
            for (int fois = 0; fois < 2; fois++) // le clic, puis son retour après Échap pour la photo
            {
                clic = Toucher(cabinet, P, glisser ? loin : P, moree);
                if (cabinet.Retenue?.CellId != cellule) throw Echec("étape 5 : aucune terre gardée après le geste" + (glisser ? " (glisser de " + PAS_PX + " px, " + GLISSER + ")" : "") + " : retenue " + (cabinet.Retenue?.CellId.ToString() ?? "nulle") + ", attendu " + N(cellule));
                MeshRenderer teinte = carte.GetComponentsInChildren<MeshRenderer>().FirstOrDefault(r => r.name == "Cellule " + N(cellule));
                if (teinte == null || !teinte.HasPropertyBlock()) throw Echec("étape 5 : « Cellule " + N(cellule) + " » " + (teinte == null ? "introuvable" : "sans la teinte de la terre gardée"));
                for (var e = Lot690.Jusqua(Dossier, () => "étape 5 : le dossier dit « " + Ligne(texte.text) + " », attendu « " + debut + "… » puis une ligne « jour … »"); e.MoveNext();) yield return null;
                if (fois == 1) break;
                menu.Echap();
                if (cabinet.Retenue != null || menu.Ouvert || teinte.HasPropertyBlock()) throw Echec("étape 6 : le premier Échap laisse la cellule " + cabinet.Retenue?.CellId + ", menu " + (menu.Ouvert ? "ouvert" : "fermé"));
                for (var e = Lot690.Jusqua(() => !texte.text.StartsWith(debut, StringComparison.Ordinal), () => "étape 6 : le dossier fermé dit encore « " + Ligne(texte.text) + " »"); e.MoveNext();) yield return null;
                ferme = Ligne(texte.text);
                menu.Echap(); if (!menu.Ouvert) throw Echec("étape 6 : le deuxième Échap n'ouvre pas le menu");
                menu.Echap(); if (menu.Ouvert) throw Echec("étape 6 : le troisième Échap ne ferme pas le menu");
            }

            Lot549.Photographier(camera, carte); camera.rect = new Rect(0, 0, 1, 1); Canvas cabinetToile = toile.GetComponent<Canvas>(); // la toile overlay se dessine sur la caméra reçue
            cabinetToile.renderMode = RenderMode.ScreenSpaceCamera; cabinetToile.worldCamera = camera; cabinetToile.planeDistance = camera.nearClipPlane + 0.2f;
            yield return null; Canvas.ForceUpdateCanvases();
            void Visible() // le texte défile dans sa fenêtre (RectMask2D) : la règle de Lot690.DansLeChamp s'applique au panneau et à la fenêtre, où le texte commence
            {
                foreach (var cadre in new[] { (RectTransform)texte.transform.parent.parent, (RectTransform)texte.transform.parent })
                {
                    var c = new Vector3[4]; cadre.GetWorldCorners(c);
                    foreach (Vector3 v in c.Select(camera.WorldToViewportPoint)) if (v.z <= 0f || v.x < -0.01f || v.x > 1.01f || v.y < -0.01f || v.y > 1.01f) throw Echec("photo : « " + cadre.name + " » coupé, coin " + v.ToString("F3"));
                }
                if (Mathf.Abs(texte.rectTransform.anchoredPosition.y) > 0.5f) throw Echec("photo : le dossier a défilé de " + texte.rectTransform.anchoredPosition.y + " px, sa première ligne est cachée");
                Vector3 vu = camera.WorldToViewportPoint(point);
                if (vu.z <= 0 || vu.x < 0 || vu.x > 1 || vu.y < 0 || vu.y > 1) throw Echec("photo : le point de la Morée est hors champ " + vu.ToString("F3"));
            }
            Visible(); for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            if (cabinet.Retenue?.CellId != cellule || !Dossier()) throw Echec("après la pose : retenue " + cabinet.Retenue?.CellId + ", dossier « " + Ligne(texte.text) + " »");
            Visible();
            Debug.Log("CAPTURE_855 Morée cellule " + N(cellule) + ", P " + Ecran(P) + ", Q " + Ecran(Q) + " ; étape 3 panneau " + (panneau ? "gardé" : "rien") + ", étape 4 glisser " + (glisse ? "gardé" : "rien")
                + ", étape 5 clic " + (clic ? "gardé" : "rien") + ", étape 6 Échap ferme le dossier (« " + ferme + " »), puis ouvre et ferme le menu ; dossier « " + Ligne(texte.text) + " »");
        }
    }
}
