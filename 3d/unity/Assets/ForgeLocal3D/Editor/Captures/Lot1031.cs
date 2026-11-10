using System; using System.Collections; using System.Collections.Generic; using System.Globalization; using System.IO; using System.Linq; using System.Text; using System.Threading.Tasks;
using Forge.Interface; using Forge.Pont; using UnityEngine; using UnityEngine.UI;

namespace ForgeLocal3D.Captures
{
    // Lot 1031 : Paris survolé, avec ses cinq poses. Le service part amorcé par `-forgeServiceModificateurs` (un moulin, trois jauges de la maison, une épreuve de 90 jours) :
    // l'infobulle dit les trois lignes du dossier, puis chaque pose du bourg et le total de sa grandeur, telles que `/modificateurs` les sert au même tick.
    // `-forge1031Decale` pousse un tick avant de juger : l'infobulle et le registre ne sont plus au même tick. `-forge1031SansLigne` retire du feuillet sa dernière ligne de pose.
    static class Lot1031
    {
        const string MOULIN = "batiment:moulin-paris", NOM_DU_BOURG = "Paris", DOSSIER = "Territoire conservé", REGISTRE = "/modificateurs", RAPPORT = "rapport-1031.json";
        const string DECALE = "-forge1031Decale", SANS_LIGNE = "-forge1031SansLigne";
        const int IMAGES_DE_POSE = 10, POSES = 5, MARGE_PX = 30, LARGEUR = 1920, HAUTEUR = 1080, PETITE_LARGEUR = 1280, PETITE_HAUTEUR = 720; const float CARRE = 48; const double PERIODE_S = 0.5;
        [Serializable] sealed class Rapport { public long tick; public string[] lignes_servies; public string[] lignes_montrees; public float[] cadre_du_feuillet; }
        // Une ligne servie par le registre : de quoi retrouver la ligne montrée, dans l'ordre ; `Source` n'est jamais montrée.
        sealed class Servie { public bool Pose; public string[] Morceaux; public string Source; public string Dire => string.Join(" ", Morceaux); }

        static CarteDessinee carte; static CabinetDeCarte cabinet; static FicheDeCellule fiche; static InfobulleDeTerre terre; static DossierTerritoire dossier; static Transform toile; static Vector3 bourg;
        static LectureDossier mienne; static List<Servie> servies; static long cellule; static string maison; static string[] identifiants; static double prochaine; static Vector2 point;
        static string N(long v) => v.ToString(CultureInfo.InvariantCulture); static InvalidOperationException Echec(string cause) => new InvalidOperationException(cause);
        static bool Drapeau(string nom) => Environment.GetCommandLineArgs().Contains(nom);
        static string Ecran(Vector2 p) => "(" + Mathf.RoundToInt(p.x) + ", " + Mathf.RoundToInt(p.y) + ")"; static string Ecran(Rect r) => "[" + Ecran(r.min) + " – " + Ecran(r.max) + "]";
        static string Ligne(string texte, int i = 0) { var l = (texte ?? "(aucun texte)").Split('\n'); return i < l.Length ? l[i] : "(aucune ligne " + (i + 1) + ")"; }

        static IEnumerator LireBourg(int port, long id, string etape, LieuPlace[] lu)
        {
            var lecture = Task.Run(() => { using (var c = new ClientLieu(port, ClientDeparts.DelaiMinimal)) return c.Lire(id); });
            for (var e = Lot690.Attendre(lecture, etape + " : lecture /lieu?cell=" + N(id)); e.MoveNext();) yield return null;
            lu[0] = lecture.Result.Presente ? lecture.Result.Lieu.Bourg : throw Echec(etape + " : /lieu?cell=" + N(id) + " absent : " + lecture.Result.Absence);
            if (lu[0]?.Nom == null || lu[0].Position == null) throw Echec(etape + " : le rang 0 de " + N(id) + " n'a pas de nom ou de point : " + (lu[0]?.AbsenceDuNom ?? lu[0]?.AbsenceDePopulation ?? "rang 0 absent"));
        }

        // Ce que `/modificateurs` sert au bourg, lu sans passer par `InfobulleDeTerre` : pour chaque grandeur, ses poses puis son total, dans l'ordre servi.
        static List<Servie> LesServies(DocumentDuMonde registre, long id)
        {
            var lieux = DocumentDuMonde.Tableau(registre.Champs, "lieux").Select(l => l as Dictionary<string, object> ?? throw Echec("lieu du registre illisible"))
                .Where(l => DocumentDuMonde.Entier(l, "cell_id") == id && DocumentDuMonde.Entier(l, "rang") == 0).ToArray();
            if (lieux.Length != 1) throw Echec("/modificateurs porte " + lieux.Length + " bourg(s) pour la cellule " + N(id) + ", attendu un seul");
            var dites = new List<Servie>();
            foreach (var paire in DocumentDuMonde.Objet(lieux[0], "grandeurs"))
            {
                var grandeur = paire.Value as Dictionary<string, object> ?? throw Echec("grandeur « " + paire.Key + " » illisible"); string nom = DocumentDuMonde.Texte(grandeur, "nom");
                foreach (var brute in DocumentDuMonde.Tableau(grandeur, "lignes"))
                {
                    var l = brute as Dictionary<string, object> ?? throw Echec("ligne de « " + paire.Key + " » illisible");
                    dites.Add(new Servie { Pose = true, Source = DocumentDuMonde.Texte(l, "source"), Morceaux = new[] { nom, TexteDuMonde.Pourcentage(DocumentDuMonde.Nombre(l, "valeur")), DocumentDuMonde.Texte(l, "nom"), DocumentDuMonde.Texte(l, "source_dite") } });
                }
                dites.Add(new Servie { Morceaux = new[] { nom + ", total", TexteDuMonde.Pourcentage(DocumentDuMonde.Nombre(grandeur, "total")) } });
            }
            return dites;
        }
        static bool Dit(string ligne, string[] morceaux)
        {
            int depuis = 0; foreach (string m in morceaux) { int k = ligne.IndexOf(m, depuis, StringComparison.Ordinal); if (k < 0) return false; depuis = k + m.Length; }
            return true;
        }

        // Le compte et l'ordre : autant de lignes que le registre en sert pour le bourg, chacune avec son nom, sa valeur et son mot de source ; le total suit les lignes de sa grandeur.
        static void Juger(string[] montrees, string ou)
        {
            int poses = servies.Count(s => s.Pose); if (poses != POSES) throw Echec(ou + " : " + poses + " pose(s) servie(s) au bourg, attendu " + POSES + " (l'amorçage de -forgeServiceModificateurs)");
            for (int i = 0; i < servies.Count; i++)
                if (i >= montrees.Length || !Dit(montrees[i], servies[i].Morceaux))
                    throw Echec(ou + " : " + (montrees.Length < servies.Count ? "ligne manquante « " + servies[i].Dire + " »" : "la ligne " + (i + 1) + " montre « " + montrees[i] + " », attendu « " + servies[i].Dire + " »")
                        + " (" + montrees.Length + " ligne(s) montrée(s), " + servies.Count + " servie(s))");
            if (montrees.Length > servies.Count) throw Echec(ou + " : " + (montrees.Length - servies.Count) + " ligne(s) en trop, la première « " + montrees[servies.Count] + " »");
        }

        static RectTransform UnFeuillet(string ou)
        {
            RectTransform[] feuillets = toile.GetComponentsInChildren<RectTransform>().Where(t => t.name == "Infobulle").ToArray();
            return feuillets.Length == 1 ? feuillets[0] : throw Echec(ou + " : " + feuillets.Length + " feuillet(s) actif(s), attendu un seul");
        }
        static Rect Cadre(Camera camera, RectTransform feuillet)
        {
            var c = new Vector3[4]; feuillet.GetWorldCorners(c); Vector2[] e = c.Select(v => (Vector2)RectTransformUtility.WorldToScreenPoint(camera, v)).ToArray();
            return Rect.MinMaxRect(e.Min(p => p.x), e.Min(p => p.y), e.Max(p => p.x), e.Max(p => p.y));
        }
        static void EntierDansLImage(Camera camera, Rect r, string ou)
        {
            Rect ecran = camera.pixelRect;
            if (r.xMin < ecran.xMin - .5f || r.yMin < ecran.yMin - .5f || r.xMax > ecran.xMax + .5f || r.yMax > ecran.yMax + .5f) throw Echec(ou + " : feuillet " + Ecran(r) + " coupé par l'image " + Ecran(ecran));
        }

        // Le feuillet tel que l'écran le montre : ses lignes de pose sont jugées, avant tout le reste, sur le `Text` qu'il porte ; `-forge1031SansLigne` en retire la dernière ligne de pose.
        static Rect Juge(Camera camera, string ou, bool sansLigne, bool surLePoint)
        {
            RectTransform feuillet = UnFeuillet(ou); Text ecrit = feuillet.GetComponentInChildren<Text>(true) ?? throw Echec(ou + " : le feuillet n'a pas de texte");
            string[] lignes = (ecrit.text ?? "").Split('\n');
            if (sansLigne) { var restantes = lignes.ToList(); restantes.RemoveAt(InfobulleDeTerre.LIGNES + servies.FindLastIndex(s => s.Pose)); ecrit.text = string.Join("\n", restantes); lignes = restantes.ToArray(); }
            if (lignes.Length < InfobulleDeTerre.LIGNES) throw Echec(ou + " : le feuillet n'a que " + lignes.Length + " ligne(s)");
            Juger(lignes.Skip(InfobulleDeTerre.LIGNES).ToArray(), ou);
            if (ecrit.text != terre.TexteAffiche) throw Echec(ou + " : le feuillet dit « " + ecrit.text + " », attendu « " + terre.TexteAffiche + " »");
            Rect r = Cadre(camera, feuillet); EntierDansLImage(camera, r, ou);
            if (surLePoint && Rect.MinMaxRect(r.xMin + .5f, r.yMin + .5f, r.xMax - .5f, r.yMax - .5f).Overlaps(new Rect(point - Vector2.one * CARRE / 2, Vector2.one * CARRE))) throw Echec(ou + " : feuillet " + Ecran(r) + " sur le point " + Ecran(point));
            if (ecrit.preferredHeight > feuillet.rect.height + .5f) throw Echec(ou + " : le texte demande " + ecrit.preferredHeight + " px, le feuillet n'en a que " + feuillet.rect.height);
            return r;
        }

        // Les trois ticks : celui du dossier de l'infobulle, celui de son registre, celui de la lecture du scénario.
        static bool MemeTick(out string dit)
        {
            long? dossierTick = terre.Lecture?.Document?.Tick, registreTick = terre.LectureModificateurs?.Document?.Tick, lu = mienne.Document?.Tick;
            dit = "dossier de l'infobulle " + (dossierTick?.ToString(CultureInfo.InvariantCulture) ?? "absent") + ", modificateurs de l'infobulle " + (registreTick?.ToString(CultureInfo.InvariantCulture) ?? "absent") + ", lecture du scénario " + (lu?.ToString(CultureInfo.InvariantCulture) ?? "absente");
            return dossierTick != null && dossierTick == registreTick && registreTick == lu;
        }
        static void Relire()
        {
            double maintenant = Time.realtimeSinceStartupAsDouble;
            if (!mienne.EnCours && (mienne.Cle != REGISTRE || maintenant >= prochaine)) { _ = mienne.Actualiser(REGISTRE); prochaine = maintenant + PERIODE_S; }
        }

        static void Tendre(Camera camera, int largeur, int hauteur)
        {
            RenderTexture ancienne = camera.targetTexture; camera.rect = new Rect(0, 0, 1, 1); camera.targetTexture = new RenderTexture(largeur, hauteur, 24); camera.ResetAspect(); if (ancienne != null) ancienne.Release();
            Canvas cab = toile.GetComponent<Canvas>(); cab.renderMode = RenderMode.ScreenSpaceCamera; cab.worldCamera = camera; cab.planeDistance = camera.nearClipPlane + 0.2f;
        }

        [ScenarioDeCapture(1031, "1-paris-survole")] static IEnumerator ParisSurvole(Camera camera)
        {
            if (!Drapeau(Capture.SERVICE_MODIFICATEURS)) throw Echec("lancer avec " + Capture.SERVICE_MODIFICATEURS + " : sans lui, Paris n'a pas de pose");
            var ouverte = new Lot549.CarteOuverte(); for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null;
            carte = ouverte.Carte; cabinet = carte.GetComponent<CabinetDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de CabinetDeCarte");
            fiche = carte.GetComponent<FicheDeCellule>() ?? throw Echec("étape 1 : la carte n'a pas de fiche"); dossier = carte.GetComponent<DossierTerritoire>() ?? throw Echec("étape 1 : le cabinet n'a pas de dossier");
            InfobulleDeTerre[] bulles = carte.GetComponents<InfobulleDeTerre>(); terre = bulles.Length == 1 ? bulles[0] : throw Echec("étape 1 : " + bulles.Length + " InfobulleDeTerre, attendu une seule");
            if (terre.LectureModificateurs == null) throw Echec("étape 1 : l'infobulle n'a pas de lecture des modificateurs");
            toile = carte.transform.Find("Cabinet"); if (toile == null || !toile.gameObject.activeInHierarchy) throw Echec("étape 1 : la toile du cabinet n'est pas active");
            (carte.GetComponent<SurvolDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de survol")).automatique = true; (carte.GetComponent<ParcoursDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de parcours")).automatique = true; terre.automatique = true;
            // Le moulin de Paris, dans le registre lu par un client à part, donne la cellule ; /lieu en dit le nom.
            mienne = LectureDossier.Locale(carte.port); for (var e = Lot690.Attendre(mienne.Actualiser(REGISTRE), "étape 2 : lecture " + REGISTRE); e.MoveNext();) yield return null;
            if (mienne.Document == null) throw Echec("étape 2 : " + REGISTRE + " absent : " + mienne.Erreur);
            var moulins = DocumentDuMonde.Tableau(mienne.Document.Champs, "poses").Select(p => p as Dictionary<string, object> ?? throw Echec("pose du registre illisible")).Where(p => DocumentDuMonde.Texte(p, "source") == MOULIN).ToArray();
            if (moulins.Length != 1) throw Echec("étape 2 : " + moulins.Length + " pose(s) de source « " + MOULIN + " » dans " + REGISTRE + ", attendu une seule");
            cellule = DocumentDuMonde.Entier(DocumentDuMonde.Objet(moulins[0], "cible"), "cellule"); var lu = new LieuPlace[1]; for (var e = LireBourg(carte.port, cellule, "étape 2", lu); e.MoveNext();) yield return null;
            if (lu[0].Nom != NOM_DU_BOURG) throw Echec("étape 2 : le moulin est à « " + lu[0].Nom + " », attendu « " + NOM_DU_BOURG + " »");
            Vector3 local = carte.PositionSurLaCarte(lu[0].Position.Value, ReperesDeDepart.HAUTEUR_LIEU) ?? throw Echec("étape 2 : la carte ne place pas le bourg"); bourg = carte.transform.TransformPoint(local);
            carte.Vue.Zoomer(12, carte.camera.WorldToViewportPoint(bourg)); carte.Vue.Centrer(new Vector2(local.x, local.z), carte.Vue.Demi); yield return null;
            (carte.GetComponent<SurvolDeCarte>()).Survoler(carte.camera.WorldToScreenPoint(bourg));
            if (fiche.Survolee?.CellId != cellule) throw Echec("étape 2 : sous le bourg, la fiche voit " + fiche.Survolee?.CellId + ", attendu Paris " + N(cellule));
            cabinet.Garder(fiche.Survolee); Text texte = toile.Find(DOSSIER)?.Find("Lecture du territoire")?.GetComponentInChildren<Text>(true) ?? throw Echec("étape 2 : le texte du dossier est introuvable");
            Lot549.Photographier(camera, carte); Tendre(camera, LARGEUR, HAUTEUR);
            yield return null; Canvas.ForceUpdateCanvases(); Vector3 vu = camera.WorldToScreenPoint(bourg); if (vu.z <= 0) throw Echec("étape 3 : le bourg est derrière la caméra"); point = vu;
            bool Aligne()
            {
                terre.Pas(point, fiche.Survolee, Time.realtimeSinceStartupAsDouble); Relire();
                return (terre.TexteAffiche ?? "").StartsWith(NOM_DU_BOURG + " · ", StringComparison.Ordinal) && MemeTick(out _) && dossier.Document != null && dossier.Document.Tick == terre.Lecture.Document.Tick;
            }
            for (var e = Lot690.Jusqua(Aligne, () => { MemeTick(out string dit); return "étape 3 : infobulle « " + Ligne(terre.TexteAffiche) + " », dossier du cabinet au tick " + dossier.Document?.Tick + ", " + dit; }); e.MoveNext();) yield return null;
            if (Drapeau(DECALE))
            {
                // Contre-épreuve : un tick de plus, lu avant que l'infobulle ne relise ; ce qu'elle montre n'est plus au tick du registre.
                var pousse = Lot690.PousserTick(carte.port); for (var e = Lot690.Attendre(pousse, "POST /tick?n=1"); e.MoveNext();) yield return null;
                if (pousse.Result.statut != 200) throw Echec("POST /tick?n=1 refusé (" + pousse.Result.statut + ") : " + pousse.Result.corps);
                for (var e = Lot690.Attendre(mienne.Actualiser(REGISTRE), "relecture " + REGISTRE + " après le tick"); e.MoveNext();) yield return null;
                if (MemeTick(out string ecart)) throw Echec(DECALE + " : un tick poussé n'a pas décalé les lectures : " + ecart);
                throw Echec("l'infobulle et " + REGISTRE + " ne sont plus au même tick : " + ecart);
            }
            servies = LesServies(mienne.Document, cellule);
            string[] a = terre.TexteAffiche.Split('\n'), b = (texte.text ?? "").Split('\n');
            if (a.Length < InfobulleDeTerre.LIGNES || b.Length < InfobulleDeTerre.LIGNES || a[0] != b[0] || a[1] != b[1] || a[2] != b[2]) throw Echec("les trois premières lignes de l'infobulle ne sont pas celles du dossier : « " + string.Join(" | ", a.Take(InfobulleDeTerre.LIGNES)) + " » contre « " + string.Join(" | ", b.Take(InfobulleDeTerre.LIGNES)) + " »");
            maison = DocumentDuMonde.Texte(DocumentDuMonde.Tableau(terre.Lecture.Document.Champs, "lieux").OfType<Dictionary<string, object>>().Single(l => DocumentDuMonde.Entier(l, "rang") == 0), "maitre");
            identifiants = servies.Where(s => s.Pose).Select(s => s.Source).Distinct().Concat(new[] { maison }).ToArray();
            void Scene(string ou)
            {
                if (terre.TexteAffiche == null || !terre.TexteAffiche.Contains("Moulin") || !terre.TexteAffiche.Contains("Concorde (-2)")) throw Echec(ou + " : « Moulin » ou « Concorde (-2) » absent de « " + terre.TexteAffiche + " »");
                string interdit = TexteDuMonde.Interdit(terre.TexteAffiche, identifiants); if (interdit != null) throw Echec(ou + " : « " + interdit + " » à l'écran");
                Transform vieille = carte.transform.Find("Toile de la fiche"); if (vieille == null || vieille.gameObject.activeInHierarchy) throw Echec(ou + " : « Toile de la fiche » " + (vieille == null ? "absente" : "encore active"));
            }
            Scene("étape 4"); Juge(camera, "étape 4", Drapeau(SANS_LIGNE), true);
            for (int i = 0; i < IMAGES_DE_POSE; i++) { terre.Pas(point, fiche.Survolee, Time.realtimeSinceStartupAsDouble); Relire(); yield return null; }
            if (!MemeTick(out string dit2)) throw Echec("étape 5 : les ticks ont bougé : " + dit2);
            servies = LesServies(mienne.Document, cellule); Scene("étape 5"); Rect pose = Juge(camera, "étape 5", Drapeau(SANS_LIGNE), true);
            long tick = terre.Lecture.Document.Tick; string[] montrees = terre.TexteAffiche.Split('\n').Skip(InfobulleDeTerre.LIGNES).ToArray();
            File.WriteAllText(Path.Combine(Capture.DossierDesCaptures, RAPPORT), JsonUtility.ToJson(new Rapport { tick = tick, lignes_servies = servies.Select(s => s.Dire).ToArray(), lignes_montrees = montrees, cadre_du_feuillet = new[] { pose.xMin, pose.yMin, pose.xMax, pose.yMax } }, true), new UTF8Encoding(false));
            Debug.Log("CAPTURE_1031 cellule " + N(cellule) + " point " + Ecran(point) + " feuillet " + Ecran(pose) + " tick " + N(tick) + " : " + servies.Count + " lignes servies, " + montrees.Length + " montrées « " + Ligne(terre.TexteAffiche, InfobulleDeTerre.LIGNES) + " »");
        }

        [ScenarioDeCapture(1031, "2-paris-1280x720")] static IEnumerator Paris1280(Camera camera)
        {
            if (carte == null || terre == null || fiche == null || toile == null || servies == null) throw Echec("étape 6 : la carte du scénario 1 manque");
            if (fiche.Survolee?.CellId != cellule) throw Echec("étape 6 : la fiche ne voit plus Paris (" + fiche.Survolee?.CellId + ")");
            Tendre(camera, PETITE_LARGEUR, PETITE_HAUTEUR); yield return null; Canvas.ForceUpdateCanvases();
            Rect image = camera.pixelRect; if (Mathf.RoundToInt(image.width) != PETITE_LARGEUR || Mathf.RoundToInt(image.height) != PETITE_HAUTEUR) throw Echec("étape 6 : l'image fait " + Ecran(image) + ", attendu " + PETITE_LARGEUR + " × " + PETITE_HAUTEUR);
            Vector3 vu = camera.WorldToScreenPoint(bourg); if (vu.z <= 0) throw Echec("étape 6 : le bourg est derrière la caméra");
            var points = new[] { (Vector2)vu, new Vector2(MARGE_PX, MARGE_PX), new Vector2(PETITE_LARGEUR - MARGE_PX, MARGE_PX), new Vector2(MARGE_PX, PETITE_HAUTEUR - MARGE_PX), new Vector2(PETITE_LARGEUR - MARGE_PX, PETITE_HAUTEUR - MARGE_PX) };
            string[] noms = { "le bourg", "le coin bas gauche", "le coin bas droit", "le coin haut gauche", "le coin haut droit" }; var cadres = new List<string>();
            for (int i = 0; i < points.Length; i++)
            {
                point = points[i]; string ou = "étape 7 (" + noms[i] + " " + Ecran(point) + ")";
                terre.Pas(point, fiche.Survolee, Time.realtimeSinceStartupAsDouble); yield return null; Canvas.ForceUpdateCanvases();
                terre.Pas(point, fiche.Survolee, Time.realtimeSinceStartupAsDouble);
                if (!MemeTick(out string dit)) throw Echec(ou + " : les ticks ont bougé : " + dit);
                Rect r = Juge(camera, ou, Drapeau(SANS_LIGNE), i == 0); cadres.Add(Ecran(r));
            }
            Debug.Log("CAPTURE_1031 " + PETITE_LARGEUR + " × " + PETITE_HAUTEUR + " : " + points.Length + " points, feuillets " + string.Join(" ", cadres) + ", " + servies.Count(s => s.Pose) + " poses jugées en chacun");
            point = points[0]; terre.Pas(point, fiche.Survolee, Time.realtimeSinceStartupAsDouble); yield return null; // l'image garde le feuillet au bourg
        }
    }
}
