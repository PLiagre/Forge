using System; using System.Collections; using System.Collections.Generic; using System.Globalization; using System.Linq; using System.Threading.Tasks;
using Forge.Interface; using Forge.Pont; using UnityEngine; using UnityEngine.UI;

namespace ForgeLocal3D.Captures
{
    // Lot 1012 : « Les autres maisons » ouvert au jour 71 de 1400, IA active jouée par le programme : le bloc de la première route vers
    // le champ dit la faim du bourg, le champ visé et son coût. `-forge1012Ancienne` remet « Raison non interprétée » à la place de la faim.
    static class Lot1012
    {
        const string DRAPEAU_ANCIENNE = "-forge1012Ancienne", BOUTON = "Autres maisons", ROUTE = "tracer_route", REGLE = "route_vers_le_champ";
        const int IMAGES_DE_POSE = 10;
        static string N(long v) => v.ToString(CultureInfo.InvariantCulture); static InvalidOperationException Echec(string cause) => new InvalidOperationException(cause);
        static Dictionary<string, object> Entree(object e) => e as Dictionary<string, object> ?? throw Echec("ordre du journal illisible");
        static string Regle(object e) => DocumentDuMonde.Texte(DocumentDuMonde.Objet(Entree(e), "raison"), "regle");
        [ScenarioDeCapture(1012, "route-vers-le-champ")]
        static IEnumerator RouteVersLeChamp(Camera camera)
        {
            string[] args = Environment.GetCommandLineArgs(); if (!args.Contains(Capture.SERVICE_IA) || !args.Contains(Capture.SERVICE_PROGRAMME)) throw Echec("lancer avec -forgeServiceIa -forgeServiceProgramme : la route vers le champ n'est pas jouée");
            var ouverte = new Lot549.CarteOuverte(); for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null;
            CarteDessinee carte = ouverte.Carte; Lot549.Photographier(camera, carte);
            Canvas toile = carte.transform.Find("Cabinet")?.GetComponent<Canvas>() ?? throw Echec("la carte n'a pas de cabinet");
            // Comme `Lot892` : la caméra prend toute l'image, décalée vers l'est pour garder la carte à sa place, et la toile se dessine sur elle.
            float largeur = camera.rect.width; camera.rect = new Rect(0, 0, 1, 1);
            camera.transform.position += camera.transform.right * (1 - largeur) * camera.orthographicSize * camera.aspect;
            toile.renderMode = RenderMode.ScreenSpaceCamera; toile.worldCamera = camera; toile.planeDistance = camera.nearClipPlane + 0.2f;
            (carte.GetComponent<SurvolDeCarte>() ?? throw Echec("la carte n'a pas de survol")).automatique = true;
            (carte.GetComponent<ParcoursDeCarte>() ?? throw Echec("la carte n'a pas de parcours")).automatique = true;
            (carte.GetComponent<CommandesDuTemps>() ?? throw Echec("la carte n'a pas de commandes du temps")).automatique = true;
            var pousse = Lot690.PousserTick(carte.port); for (var e = Lot690.Attendre(pousse, "POST /tick"); e.MoveNext();) yield return null;
            if (pousse.Result.statut != 200) throw Echec("POST /tick refusé (" + pousse.Result.statut + ") : " + pousse.Result.corps);
            long tick = new DocumentDuMonde(pousse.Result.corps).Tick;
            Button[] boutons = carte.GetComponentsInChildren<Button>(true).Where(b => b.name == BOUTON).ToArray();
            if (boutons.Length != 1) throw Echec(boutons.Length + " bouton(s) « " + BOUTON + " » sous la carte, attendu un seul");
            boutons[0].onClick.Invoke(); DossierVoisins dossier = carte.GetComponent<DossierVoisins>() ?? throw Echec("la carte n'a pas de DossierVoisins");
            LectureDossier ia = LectureDossier.Locale(carte.port), maisons = LectureDossier.Locale(carte.port);
            for (var e = Lot690.Attendre(Task.WhenAll(ia.Actualiser("/ia"), maisons.Actualiser("/maisons")), "lecture /ia et /maisons"); e.MoveNext();) yield return null;
            if (ia.Document == null || maisons.Document == null) throw Echec("/ia ou /maisons absent : " + (ia.Erreur ?? maisons.Erreur));
            if (ia.Document.Tick != tick) throw Echec("/ia relevé au tick " + N(ia.Document.Tick) + ", attendu celui du POST, " + N(tick));
            // L'ordre de `Decrire` : tick décroissant, tri stable ; l'entrée k y est le bloc k + 1 (le premier est l'en-tête du journal).
            var ordres = DocumentDuMonde.Tableau(ia.Document.Champs, "releve").Select(Entree).OrderByDescending(e => DocumentDuMonde.Entier(e, "tick")).ToList();
            string compte = ordres.Count == 0 ? "aucun ordre" : string.Join(", ", ordres.GroupBy(Regle).OrderBy(g => g.Key, StringComparer.Ordinal).Select(g => g.Key + " " + g.Count()));
            int k = ordres.FindIndex(e => Regle(e) == REGLE); if (k < 0) throw Echec("aucune route vers le champ dans le journal : " + compte);
            var lieux = new Dictionary<long, Lieu>();
            foreach (long cellule in ordres.Select(e => DocumentDuMonde.Objet(e, "intention")).Where(i => DocumentDuMonde.Texte(i, "type") == ROUTE).Select(i => DocumentDuMonde.Entier(i, "cell")).Distinct().ToArray())
            {
                var lecture = Task.Run(() => { using (var c = new ClientLieu(carte.port, ClientDeparts.DelaiMinimal)) return c.Lire(cellule); });
                for (var e = Lot690.Attendre(lecture, "lecture /lieu?cell=" + N(cellule)); e.MoveNext();) yield return null;
                lieux[cellule] = lecture.Result.Presente ? lecture.Result.Lieu : throw Echec("/lieu?cell=" + N(cellule) + " absent : " + lecture.Result.Absence);
            }
            Func<long, long, string> nom = (c, r) => lieux[c].Lieux?.FirstOrDefault(l => l.Rang == r) is LieuPlace p ? p.Nom ?? throw Echec("le rang " + N(r) + " de /lieu?cell=" + N(c) + " n'a pas de nom servi : " + p.AbsenceDuNom)
                : throw Echec("rang " + N(r) + " absent de /lieu?cell=" + N(c) + " : " + (lieux[c].AbsenceDesLieux ?? "liste sans ce rang"));
            var intention = DocumentDuMonde.Objet(ordres[k], "intention"); long cellRoute = DocumentDuMonde.Entier(intention, "cell");
            string champ = nom(cellRoute, DocumentDuMonde.Entier(DocumentDuMonde.Objet(ordres[k], "raison"), "champ_vise"));
            string maison = DocumentDuMonde.Tableau(maisons.Document.Champs, "maisons").Select(Entree).Where(m => DocumentDuMonde.Texte(m, "id") == DocumentDuMonde.Texte(intention, "maison"))
                .Select(m => DocumentDuMonde.Valeur(m, "nom") as string).FirstOrDefault() ?? "Maison absente du registre";
            string attendu = DossierVoisins.Decrire(ia.Document, maisons.Document, nom);
            for (var e = Lot690.Jusqua(() => dossier.TexteAffiche == attendu, () => "le feuillet ne montre pas le journal attendu : « " + (dossier.TexteAffiche ?? "(aucun texte)").Split('\n')[0] + " »"); e.MoveNext();) yield return null;
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            // Dans l'image de la photo, sans `yield` : le texte du cabinet, jugé tel qu'il sera photographié.
            Text texte = toile.GetComponentsInChildren<Text>(true).FirstOrDefault(t => t.text == dossier.TexteAffiche) ?? throw Echec("aucun texte du cabinet ne montre le journal");
            string[] lignes = texte.text.Split('\n'); int debut = 0, fin = 0;
            for (int bloc = 0, i = 0; i <= lignes.Length; i++)
                if (i == lignes.Length || lignes[i].TrimEnd('\r').Length == 0) { if (bloc == k + 1) { fin = i; break; } bloc++; debut = i + 1; }
            if (fin <= debut) throw Echec("le bloc " + (k + 1) + " du journal est introuvable dans le texte affiché");
            if (args.Contains(DRAPEAU_ANCIENNE))
            {
                int faim = Array.FindIndex(lignes, debut, fin - debut, l => l.StartsWith("Faim du bourg : ", StringComparison.Ordinal));
                if (faim >= 0) { lignes[faim] = "Raison non interprétée par cette vue." + (lignes[faim].EndsWith("\r") ? "\r" : ""); texte.text = string.Join("\n", lignes); }
            }
            string blocRoute = string.Join("\n", lignes.Skip(debut).Take(fin - debut)).Replace("\r", "");
            if (!blocRoute.Contains("Faim du bourg : ") || !blocRoute.Contains("Champ visé : " + champ) || !blocRoute.Contains("Coût : ") || blocRoute.Contains("Raison non interprétée"))
                throw Echec("la route de " + maison + " ne dit pas sa raison : « " + blocRoute + " »");
            if (TexteDuMonde.Interdit(texte.text, lieux.Keys.Select(N).ToArray()) is string mot) throw Echec("mot interdit « " + mot + " » dans le journal");
            if (TexteDuMonde.SansUnite(texte.text) is string nu) throw Echec("nombre sans unité « " + nu + " » dans le journal");
            // Le texte est le contenu défilant, plus haut que sa fenêtre : on juge, comme `Lot690.DansLeChamp`, la fenêtre qui le montre.
            var coins = new Vector3[4]; ((RectTransform)texte.transform.parent).GetWorldCorners(coins);
            if (coins.Select(camera.WorldToViewportPoint).Any(v => v.z <= 0f || v.x < -0.01f || v.x > 1.01f || v.y < -0.01f || v.y > 1.01f)) throw Echec("la fenêtre du journal sort du champ de la caméra");
            float fenetre = ((RectTransform)texte.transform.parent).rect.height, hauteur = texte.cachedTextGeneratorForLayout.GetPreferredHeight(
                string.Join("\n", lignes.Take(fin)), texte.GetGenerationSettings(new Vector2(texte.rectTransform.rect.width, 0))) / texte.pixelsPerUnit;
            if (texte.rectTransform.anchoredPosition.y != 0 || hauteur > fenetre) throw Echec("la raison de la route est sous le bas du feuillet");
            Debug.Log("CAPTURE_1012 « " + lignes[0].TrimEnd('\r') + " » ; ordres : " + compte + " ; route « " + blocRoute.Replace("\n", " | ") + " »");
        }
    }
}
