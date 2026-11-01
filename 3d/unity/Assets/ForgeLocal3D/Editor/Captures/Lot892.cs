using System; using System.Collections; using System.Collections.Generic; using System.Globalization; using System.Linq; using System.Threading.Tasks;
using Forge.Interface; using Forge.Pont; using UnityEngine; using UnityEngine.UI;

namespace ForgeLocal3D.Captures
{
    // Lot 892 : « Les autres maisons » ouvert sur la carte de 1400, IA active, un jour après les 30 de la capture : le journal dit la date
    // servie, « il y a N jours » et le bourg de chaque route. `-forge892Tick` ajoute « <maison> · tick N » au texte et rougit sur « mot interdit ».
    static class Lot892
    {
        const string DRAPEAU_TICK = "-forge892Tick", BOUTON = "Autres maisons", ROUTE = "tracer_route";
        const int IMAGES_DE_POSE = 10;
        static string N(long v) => v.ToString(CultureInfo.InvariantCulture); static InvalidOperationException Echec(string cause) => new InvalidOperationException(cause);
        static string Ligne(string texte, int i = 0) { var l = (texte ?? "(aucun texte)").Replace("\r", "").Split('\n'); return i < l.Length ? l[i] : "(aucune ligne " + (i + 1) + ")"; }
        static Dictionary<string, object> Intention(object e) => DocumentDuMonde.Objet(e as Dictionary<string, object> ?? throw Echec("ordre du journal illisible"), "intention");
        [ScenarioDeCapture(892, "autres-maisons-en-noms")]
        static IEnumerator AutresMaisonsEnNoms(Camera camera)
        {
            if (!Environment.GetCommandLineArgs().Contains(Capture.SERVICE_IA)) throw Echec("lancer avec -forgeServiceIa : /ia est coupé");
            var ouverte = new Lot549.CarteOuverte(); for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null;
            CarteDessinee carte = ouverte.Carte; Lot549.Photographier(camera, carte);
            Canvas toile = carte.transform.Find("Cabinet")?.GetComponent<Canvas>() ?? throw Echec("la carte n'a pas de cabinet");
            // Comme `Lot883` : la caméra prend toute l'image, décalée vers l'est pour garder la carte à sa place, et la toile se dessine sur elle.
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
            boutons[0].onClick.Invoke();
            DossierVoisins dossier = carte.GetComponent<DossierVoisins>() ?? throw Echec("la carte n'a pas de DossierVoisins");

            LectureDossier ia = LectureDossier.Locale(carte.port), maisons = LectureDossier.Locale(carte.port);
            for (var e = Lot690.Attendre(Task.WhenAll(ia.Actualiser("/ia"), maisons.Actualiser("/maisons")), "lecture /ia et /maisons"); e.MoveNext();) yield return null;
            if (ia.Document == null || maisons.Document == null) throw Echec("/ia ou /maisons absent : " + (ia.Erreur ?? maisons.Erreur));
            if (ia.Document.Tick != tick) throw Echec("/ia relevé au tick " + N(ia.Document.Tick) + ", attendu celui du POST, " + N(tick));
            var releve = DocumentDuMonde.Tableau(ia.Document.Champs, "releve");
            var parType = releve.GroupBy(e => DocumentDuMonde.Texte(Intention(e), "type")).OrderBy(g => g.Key, StringComparer.Ordinal).ToArray();
            string compte = parType.Length == 0 ? "aucun ordre" : string.Join(", ", parType.Select(g => g.Key + " " + g.Count()));
            if (!parType.Any(g => g.Key == ROUTE) || parType.All(g => g.Key == ROUTE)) throw Echec("le journal n'a pas de route et d'ordre sans terre : " + compte);
            var routes = releve.Where(e => DocumentDuMonde.Texte(Intention(e), "type") == ROUTE).OrderByDescending(e => DocumentDuMonde.Entier((Dictionary<string, object>)e, "tick")).ToArray();
            var bourgs = new Dictionary<long, string>();
            foreach (long cellule in routes.Select(e => DocumentDuMonde.Entier(Intention(e), "cell")).Distinct().ToArray())
            {
                var lecture = Task.Run(() => { using (var c = new ClientLieu(carte.port, ClientDeparts.DelaiMinimal)) return c.Lire(cellule); });
                for (var e = Lot690.Attendre(lecture, "lecture /lieu?cell=" + N(cellule)); e.MoveNext();) yield return null;
                LieuPlace bourg = lecture.Result.Presente ? lecture.Result.Lieu.Bourg : throw Echec("/lieu?cell=" + N(cellule) + " absent : " + lecture.Result.Absence);
                bourgs[cellule] = bourg?.Nom ?? throw Echec("le rang 0 de /lieu?cell=" + N(cellule) + " n'a pas de nom servi : " + (bourg?.AbsenceDuNom ?? lecture.Result.Lieu.AbsenceDesLieux ?? "rang 0 absent"));
            }

            string attendu = DossierVoisins.Decrire(ia.Document, maisons.Document, c => bourgs[c]);
            for (var e = Lot690.Jusqua(() => dossier.TexteAffiche == attendu, () => "le feuillet dit « " + Ligne(dossier.TexteAffiche) + " | " + Ligne(dossier.TexteAffiche, 1) + " », attendu « " + Ligne(attendu) + " »"); e.MoveNext();) yield return null;
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;

            // Dans l'image de la photo, sans `yield` : le texte du cabinet, jugé tel qu'il sera photographié.
            Text texte = toile.GetComponentsInChildren<Text>(true).FirstOrDefault(t => t.text == dossier.TexteAffiche) ?? throw Echec("aucun texte du cabinet ne montre le journal : « " + Ligne(dossier.TexteAffiche) + " »");
            var premiere = Intention(routes[0]); long cellRoute = DocumentDuMonde.Entier(premiere, "cell");
            string maisonRoute = DocumentDuMonde.Tableau(maisons.Document.Champs, "maisons").Cast<Dictionary<string, object>>()
                .Where(m => DocumentDuMonde.Texte(m, "id") == DocumentDuMonde.Texte(premiere, "maison")).Select(m => DocumentDuMonde.Valeur(m, "nom") as string).FirstOrDefault() ?? "Maison absente du registre";
            if (Environment.GetCommandLineArgs().Contains(DRAPEAU_TICK)) texte.text += "\n" + maisonRoute + " · tick " + N(DocumentDuMonde.Entier((Dictionary<string, object>)routes[0], "tick"));
            if (!texte.text.StartsWith(dossier.TexteAffiche, StringComparison.Ordinal)) throw Echec("le texte affiché ne commence pas par le journal : « " + Ligne(texte.text) + " »");
            string mot = TexteDuMonde.Interdit(texte.text, bourgs.Keys.Select(N).ToArray());
            if (mot != null) throw Echec("mot interdit « " + mot + " » dans le journal : « " + Ligne(texte.text) + " »");
            if (TexteDuMonde.SansUnite(texte.text) is string nu) throw Echec("nombre sans unité « " + nu + " » dans le journal : « " + Ligne(texte.text) + " »");
            string ligneRoute = "Tracer une route à " + bourgs[cellRoute];
            foreach (string nom in bourgs.Values) if (!texte.text.Contains("Tracer une route à " + nom)) throw Echec("le journal ne dit pas « Tracer une route à " + nom + " »");
            Lot690.DansLeChamp(camera, texte);
            float fenetre = ((RectTransform)texte.transform.parent).rect.height;
            if (texte.preferredHeight > fenetre) throw Echec("le journal mesure " + texte.preferredHeight + " px pour une fenêtre de " + fenetre + " px : la fin est coupée en bas du feuillet");
            Debug.Log("CAPTURE_892 « " + Ligne(texte.text) + " » ; ordres : " + compte + " ; route « " + maisonRoute + " · " + ligneRoute + " »");
        }
    }
}
