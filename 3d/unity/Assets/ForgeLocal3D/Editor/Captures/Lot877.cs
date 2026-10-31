using System; using System.Collections; using System.Collections.Generic; using System.Globalization; using System.Linq; using System.Threading.Tasks;
using Forge.Interface; using Forge.Pont; using UnityEngine; using UnityEngine.UI;

namespace ForgeLocal3D.Captures
{
    // Lot 877 : l'épreuve du geste « La fiche parle en noms ». La Morée gardée d'un clic, sa maison choisie, un jour poussé, « Terres et comptes » ouvert.
    // Au même tick, chaque texte affiché par le cabinet, l'infobulle et la fiche de survol passent les deux juges de TexteDuMonde, puis chaque valeur
    // servie se relit en tête d'une ligne de son dossier. `-forge877Identifiant` glisse « <Morée>-1 » dans le territoire, `-forge877SansValeur` retire // la ligne « Prélevé : » du feuillet : les deux rougissent.
    static class Lot877
    {
        const string SIEGE = "Mistra", TERRE = "Despotat de Morée", MAISON = "Votre maison", DOSSIER = "Territoire conservé", FEUILLET = "Terres et comptes", INFOBULLE = "Infobulle";
        const string COMMANDES = "Commandes de maison", LIEUX = "Légende des lieux", FLECHES = "Légende des flèches", FICHE = "Fiche de survol", IDENTIFIANT = "-forge877Identifiant", SANS_VALEUR = "-forge877SansValeur";
        const int IMAGES_DE_POSE = 10, TEXTES_MIN = 8; const float CRANS = 12;
        static readonly CultureInfo Fr = CultureInfo.GetCultureInfo("fr-FR");
        static string N(long v) => v.ToString(CultureInfo.InvariantCulture); static InvalidOperationException Echec(string cause) => new InvalidOperationException(cause);
        static string[] Lignes(string texte) => (texte ?? "").Replace("\r", "").Split('\n'); static string Ligne(string texte) => Lignes(texte)[0];
        static bool Drapeau(string nom) => Environment.GetCommandLineArgs().Contains(nom);
        static string Gens(long n) => TexteDuMonde.Nombre(n) + (n > 1 ? " personnes" : " personne"); static string Gens(long n, string fait) => TexteDuMonde.Nombre(n) + (n > 1 ? " personnes " + fait + "s" : " personne " + fait);
        // Ce que le scénario a posé et lu à part ; Juger le lit sans rien attendre.
        static CabinetDeCarte cabinet; static FicheDeCellule fiche; static InfobulleDeTerre terre; static HorlogeDeCarte horloge; static Transform toile;
        static long moree, fin; static string bourg, resume; static int juges, valeurs; static DocumentDuMonde doc; static Lieu lieu; static ComptesDeMaison joueur, suzerain; static List<Lieu> tenues; static MondeLu monde;

        [ScenarioDeCapture(877, "moree-et-ses-comptes")] static IEnumerator MoreeEtSesComptes(Camera camera)
        {
            var ouverte = new Lot549.CarteOuverte(); for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null;
            CarteDessinee carte = ouverte.Carte; int port = carte.port; cabinet = carte.GetComponent<CabinetDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de CabinetDeCarte");
            fiche = carte.GetComponent<FicheDeCellule>() ?? throw Echec("étape 1 : la carte n'a pas de fiche"); horloge = carte.GetComponent<HorlogeDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas d'horloge");
            InfobulleDeTerre[] bulles = carte.GetComponents<InfobulleDeTerre>(); terre = bulles.Length == 1 ? bulles[0] : throw Echec("étape 1 : " + bulles.Length + " InfobulleDeTerre, attendu une seule");
            (carte.GetComponent<SurvolDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de survol")).automatique = true; (carte.GetComponent<ParcoursDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de parcours")).automatique = true; terre.automatique = true;
            toile = carte.transform.Find("Cabinet"); if (toile == null || !toile.gameObject.activeInHierarchy) throw Echec("étape 1 : la toile du cabinet n'est pas active");
            for (var e = Lot690.Jusqua(() => Lot690.LecturePrete(cabinet.Partie), () => "étape 1 : " + Lot690.Dire(cabinet.Partie)); e.MoveNext();) yield return null;
            for (var e = Lot690.Jusqua(() => horloge.Lue != null, () => "étape 1 : horloge jamais lue : " + (horloge.Absence ?? horloge.TexteAffiche)); e.MoveNext();) yield return null;
            if (horloge.Lue.JoursParSeconde != 0) throw Echec("étape 1 : service hors pause : " + horloge.Lue.JoursParSeconde + " jour(s) par seconde");
            FicheDeDepart[] mistra = cabinet.Partie.Departs.Donnees.Fiches.Where(f => f.Siege.Nom == SIEGE).ToArray();
            if (mistra.Length != 1 || mistra[0].Nom != TERRE) throw Echec("étape 2 : fiches au siège " + SIEGE + " : " + string.Join(", ", mistra.Select(f => f.Nom)) + ", attendu « " + TERRE + " » seule");
            FicheDeDepart depart = mistra[0]; long id = moree = depart.CellId;
            var lecture = Task.Run(() => { using (var c = new ClientLieu(port, ClientDeparts.DelaiMinimal)) return c.Lire(id); });
            for (var e = Lot690.Attendre(lecture, "étape 2 : lecture /lieu?cell=" + N(id)); e.MoveNext();) yield return null;
            if (!lecture.Result.Presente || !(lecture.Result.Lieu.Bourg?.Position is PointCarte position) || lecture.Result.Lieu.Bourg.Nom == null)
                throw Echec("étape 2 : /lieu?cell=" + N(id) + " sans bourg nommé et placé : " + (lecture.Result.Absence ?? lecture.Result.Lieu.AbsenceDesLieux ?? lecture.Result.Lieu.Bourg?.AbsenceDuNom ?? "rang 0 absent ou sans point"));
            bourg = lecture.Result.Lieu.Bourg.Nom; Vector3 local = carte.PositionSurLaCarte(position, ReperesDeDepart.HAUTEUR_LIEU) ?? throw Echec("étape 2 : la carte ne place pas le bourg"); Vector3 point = carte.transform.TransformPoint(local);
            carte.Vue.Zoomer(CRANS, carte.camera.WorldToViewportPoint(point)); carte.Vue.Centrer(new Vector2(local.x, local.z), carte.Vue.Demi); yield return null; // la carte se recadre
            Vector2 P = carte.camera.WorldToScreenPoint(point); fiche.Survoler(P); CelluleDeCarte sous = fiche.Survolee;
            if (sous?.CellId != id) throw Echec("étape 2 : sous le bourg, la fiche voit la cellule " + sous?.CellId + ", attendu la Morée " + N(id));
            if (cabinet.HorsCarte(P)) throw Echec("étape 2 : le bourg de la Morée est hors de la carte ou sous un panneau");
            // Un clic, comme le fait l'Update du cabinet : l'appui, le déplacement et le relâché au même point, sans image entre eux.
            bool clic = cabinet.Noter(P, true, false, cabinet.HorsCarte(P), sous) | cabinet.Noter(P, false, false, false, sous) | cabinet.Noter(P, false, true, cabinet.HorsCarte(P), sous);
            if (!clic || cabinet.Retenue?.CellId != id) throw Echec("étape 3 : le clic n'a pas gardé la Morée : retenue " + (cabinet.Retenue?.CellId.ToString() ?? "nulle"));
            Transform maison = toile.Find(MAISON) ?? throw Echec("étape 4 : panneau « " + MAISON + " » introuvable");
            Button[] boutons = (maison.Find("Maisons proposées") ?? throw Echec("étape 4 : « Maisons proposées » introuvable")).GetComponentsInChildren<Button>().Where(b => b.GetComponentInChildren<Text>()?.text == depart.Maison).ToArray();
            if (boutons.Length != 1) throw Echec("étape 4 : " + boutons.Length + " bouton(s) « " + depart.Maison + " », attendu un seul"); boutons[0].onClick.Invoke();
            Button choisir = maison.GetComponentsInChildren<Button>().SingleOrDefault(b => b.name == "Choisir cette maison") ?? throw Echec("étape 4 : « Choisir cette maison » introuvable");
            LecturePartie partie = cabinet.Partie; long tick = partie.Monde.Donnees.Monde.Tick;
            // Choisir ne fait rien pendant une relecture de la partie : le bouton se rejoue tant qu'aucun reçu n'est venu.
            for (var e = Lot690.Jusqua(() => { if (partie.Recu == null && partie.PeutChoisir) choisir.onClick.Invoke(); return partie.Recu != null && !partie.Occupee; }, () => "étape 4 : aucun reçu du choix"); e.MoveNext();) yield return null;
            RecuIntention recu = partie.Recu; if (!recu.Acceptee || recu.AppliqueeAuTick != tick) throw Echec("étape 4 : reçu du choix " + (recu.Acceptee ? "au tick " + recu.AppliqueeAuTick + ", attendu " + N(tick) : recu.Presente ? recu.Erreur : recu.Absence));
            var pousse = Lot690.PousserTick(port); for (var e = Lot690.Attendre(pousse, "étape 4 : POST /tick?n=1"); e.MoveNext();) yield return null;
            if (pousse.Result.statut != 200) throw Echec("étape 4 : POST /tick?n=1 a rendu " + pousse.Result.statut + " : " + pousse.Result.corps); fin = tick + 1;
            for (var e = Lot690.Jusqua(() => { var p = cabinet.Partie; return !p.Occupee && p.Monde?.Presente == true && p.Monde.Donnees.Monde.Tick == fin && p.Monde.Donnees.MaisonDuJoueur != null
                && p.Maison?.Presente == true && p.Maison.Donnees.Id == p.Monde.Donnees.MaisonDuJoueur; }, () => "étape 4 : le cabinet n'a pas lu la maison du joueur : " + Lot690.Dire(cabinet.Partie)); e.MoveNext();) yield return null;
            string maisonJoueur = partie.Monde.Donnees.MaisonDuJoueur; if (partie.Maison.Donnees.Siege.Nom != SIEGE) throw Echec("étape 4 : maison au siège « " + partie.Maison.Donnees.Siege.Nom + " », attendu " + SIEGE);
            Button[] feuillets = toile.GetComponentsInChildren<Button>(true).Where(b => b.name == FEUILLET).ToArray();
            if (feuillets.Length != 1 || !feuillets[0].gameObject.activeInHierarchy) throw Echec("étape 5 : " + feuillets.Length + " bouton(s) « " + FEUILLET + " », attendu un seul actif"); feuillets[0].onClick.Invoke();
            // Les références, lues à part après le dernier jour poussé.
            var dossierLu = LectureDossier.Locale(port); Task lireDoc = dossierLu.Actualiser("/lieu?cell=" + N(id));
            var lireLieu = Task.Run(() => { using (var c = new ClientLieu(port, ClientDeparts.DelaiMinimal)) return c.Lire(id); });
            var lireComptes = Task.Run(() => { Lecture<ComptesDeMaison> j, s = null; using (var c = new ClientMaison(port, ClientDeparts.DelaiMinimal)) j = c.LireComptes(maisonJoueur);
                if (j.Presente && j.Donnees.Suzerain != null) using (var c = new ClientMaison(port, ClientDeparts.DelaiMinimal)) s = c.LireComptes(j.Donnees.Suzerain); return (j, s); }); var lireMonde = Lot690.LireMonde(port);
            for (var e = Lot690.Attendre(Task.WhenAll(lireDoc, lireLieu, lireComptes, lireMonde), "références : /lieu, /maison et /monde au tick " + N(fin)); e.MoveNext();) yield return null;
            doc = dossierLu.Document ?? throw Echec("références : /lieu?cell=" + N(id) + " illisible : " + dossierLu.Erreur);
            lieu = lireLieu.Result.Presente && lireLieu.Result.Lieu.Lieux != null ? lireLieu.Result.Lieu : throw Echec("références : lieux de la Morée absents : " + (lireLieu.Result.Absence ?? lireLieu.Result.Lieu.AbsenceDesLieux));
            var (lj, ls) = lireComptes.Result; joueur = lj.Presente ? lj.Donnees : throw Echec("références : comptes de " + maisonJoueur + " absents : " + lj.Absence);
            suzerain = ls == null ? null : ls.Presente ? ls.Donnees : throw Echec("références : comptes du suzerain absents : " + ls.Absence);
            Lot690.ExigerMonde(lireMonde.Result, fin, maisonJoueur, "références"); monde = lireMonde.Result.Donnees.Monde;
            long[] cellules = joueur.Maison.Lieux.Select(l => l.CellId).Distinct().ToArray();
            var lireTenues = Task.Run(() => { using (var c = new ClientLieu(port, ClientDeparts.DelaiMinimal)) return cellules.Select(x => c.Lire(x)).ToList(); });
            for (var e = Lot690.Attendre(lireTenues, "références : /lieu des terres tenues"); e.MoveNext();) yield return null;
            tenues = lireTenues.Result.Select(l => l.Presente ? l.Lieu : throw Echec("références : terre tenue absente : " + l.Absence)).ToList();
            if (lieu.Tick != fin || tenues.Any(t => t.Tick != fin)) throw Echec("références : ticks /lieu " + lieu.Tick + " et " + string.Join(", ", tenues.Select(t => t.Tick)) + ", attendu " + N(fin));
            string cause = null;
            for (var e = Lot690.Jusqua(() => { try { Juger(false); return true; } catch (InvalidOperationException x) { cause = x.Message; return false; } }, () => "étape 6 : " + cause); e.MoveNext();)
            { fiche.Survoler(P); terre.Pas(P, fiche.Survolee, Time.realtimeSinceStartupAsDouble); yield return null; }
            Juger(true);
            terre.Pas(P, null, Time.realtimeSinceStartupAsDouble); // l'infobulle passerait sur le feuillet
            Text dossier = toile.Find(DOSSIER)?.Find("Lecture du territoire")?.GetComponentInChildren<Text>(true) ?? throw Echec("étape 8 : le texte du dossier est introuvable");
            ScrollRect defile = Defilement() ?? throw Echec("étape 8 : le feuillet est introuvable"); Text ecrit = defile.content.GetComponent<Text>();
            Lot549.Photographier(camera, carte); camera.rect = new Rect(0, 0, 1, 1); Canvas cabinetToile = toile.GetComponent<Canvas>(); // la toile overlay se dessine sur la caméra reçue
            cabinetToile.renderMode = RenderMode.ScreenSpaceCamera; cabinetToile.worldCamera = camera; cabinetToile.planeDistance = camera.nearClipPlane + 0.2f; yield return null; Canvas.ForceUpdateCanvases();
            void Visible(string ou) // les deux panneaux entiers, le feuillet sans texte coupé, le dossier sur sa première ligne
            {
                foreach (var cadre in new[] { (RectTransform)toile.Find(DOSSIER), (RectTransform)dossier.transform.parent, (RectTransform)defile.transform.parent }) { var c = new Vector3[4]; cadre.GetWorldCorners(c);
                    foreach (Vector3 v in c.Select(camera.WorldToViewportPoint)) if (v.z <= 0f || v.x < -0.01f || v.x > 1.01f || v.y < -0.01f || v.y > 1.01f) throw Echec(ou + " : « " + cadre.name + " » coupé, coin " + v.ToString("F3")); }
                if (!defile.gameObject.activeInHierarchy || ecrit.preferredHeight > defile.viewport.rect.height) throw Echec(ou + " : feuillet fermé ou tronqué : " + ecrit.preferredHeight + " px de texte pour " + defile.viewport.rect.height + " px");
                if (Mathf.Abs(dossier.rectTransform.anchoredPosition.y) > 0.5f) throw Echec(ou + " : le dossier a défilé de " + dossier.rectTransform.anchoredPosition.y + " px");
            }
            Visible("étape 8"); for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            Juger(false, false); Visible("étape 9");
            Debug.Log("CAPTURE_877 Morée " + N(moree) + " au tick " + N(fin) + " ; " + juges + " textes jugés, " + valeurs + " valeurs lues ; " + resume);
        }

        static ScrollRect Defilement() => toile.Cast<Transform>().Where(t => t.name == FEUILLET).Select(t => t.GetComponentInChildren<ScrollRect>(true)).FirstOrDefault(s => s != null);
        static string Chemin(Transform t) { string c = t.name; for (Transform p = t.parent; p != null && p != toile; p = p.parent) c = p.name + "/" + c; return c; }
        static Text Actif(Text t, string nom) => t != null && t.gameObject.activeInHierarchy && t.enabled ? t : throw Echec("texte « " + nom + " » absent ou inactif");
        static void Lire(string nom, string texte, string valeur) { if (!Lignes(texte).Any(l => l.StartsWith(valeur, StringComparison.Ordinal))) throw Echec("valeur absente « " + valeur + " » dans « " + nom + " »"); valeurs++; }
        static void Egale(string nom, string texte, string valeur) { if (!Lignes(texte).Contains(valeur)) throw Echec("valeur absente « " + valeur + " » dans « " + nom + " »"); valeurs++; }

        // Le jugement, sans image : les textes nommés, puis tous les autres textes actifs du cabinet ; les deux juges sur chacun, puis les valeurs servies.
        internal static void Juger(bool drapeaux, bool infobulle = true)
        {
            juges = valeurs = 0;
            if (doc.Tick != fin || monde.Tick != fin || horloge.Lue?.Tick != fin || fiche.MondeLu?.Tick != fin)
                throw Echec("ticks : document de lieu " + doc.Tick + ", monde lu " + monde.Tick + ", horloge " + horloge.Lue?.Tick + ", fiche " + fiche.MondeLu?.Tick + ", attendu " + N(fin));
            MaisonLue m = joueur.Maison; string nom = m.Nom ?? throw Echec("le nom de la maison du joueur n'est pas servi"), date = TexteDuMonde.Date(monde.Date);
            string[] ids = new[] { moree }.Concat(m.Lieux.Select(l => l.CellId)).Concat(new[] { m.Siege.CellId, suzerain?.Maison.Siege.CellId }.Where(c => c != null).Select(c => c.Value)).Select(N)
                .Concat(lieu.Lieux.Select(l => N(moree) + "-" + N(l.Rang))).Concat(new[] { m.Id, joueur.Suzerain }.Concat(lieu.Lieux.Select(l => l.Maitre))).Where(s => s != null).Distinct().ToArray();
            Transform maison = toile.Find(MAISON);
            Text territoire = Actif(toile.Find(DOSSIER)?.Find("Lecture du territoire")?.GetComponentInChildren<Text>(true), DOSSIER), feuillet = Actif(Defilement()?.content?.GetComponent<Text>(), FEUILLET);
            Text votre = Actif(maison?.Cast<Transform>().Select(t => t.GetComponent<Text>()).FirstOrDefault(t => t != null && t.text.StartsWith(nom + "\nSiège : ", StringComparison.Ordinal)), MAISON);
            Text commandes = Actif(maison?.Find(COMMANDES)?.GetComponentsInChildren<Text>(true).FirstOrDefault(t => t.text.StartsWith("Prélèvement : ", StringComparison.Ordinal)), COMMANDES);
            Text lieux = Actif(toile.GetComponentsInChildren<Text>(true).FirstOrDefault(t => t.name == LIEUX), LIEUX), fleches = Actif(toile.GetComponentsInChildren<Text>(true).FirstOrDefault(t => t.name == FLECHES), FLECHES);
            Text bulle = infobulle ? Actif(toile.Find(INFOBULLE)?.GetComponentInChildren<Text>(true), INFOBULLE) : null;
            if (bulle != null && bulle.text != terre.TexteAffiche) throw Echec("l'infobulle montre « " + Ligne(bulle.text) + " », InfobulleDeTerre dit « " + Ligne(terre.TexteAffiche) + " »");
            string survol = fiche.TexteAffiche ?? throw Echec("texte « " + FICHE + " » absent : la fiche n'est pas affichée");
            if (drapeaux && Drapeau(IDENTIFIANT)) territoire.text += "\n" + N(moree) + "-1";
            if (drapeaux && Drapeau(SANS_VALEUR)) feuillet.text = string.Join("\n", Lignes(feuillet.text).Where(l => !l.StartsWith("Prélevé : ", StringComparison.Ordinal)));
            var textes = new List<(string nom, string texte)> { (DOSSIER, territoire.text), (FEUILLET, feuillet.text), (MAISON, votre.text), (COMMANDES, commandes.text), (LIEUX, lieux.text), (FLECHES, fleches.text) };
            if (bulle != null) textes.Add((INFOBULLE, bulle.text));
            textes.Add((FICHE, survol));
            resume = string.Join(" ; ", textes.Select(t => t.nom + " « " + Ligne(t.texte) + " »"));
            var nommes = new HashSet<Text> { territoire, feuillet, votre, commandes, lieux, fleches, bulle }; Text[] actifs = toile.GetComponentsInChildren<Text>(false);
            if (actifs.Length < TEXTES_MIN) throw Echec("échantillon trop maigre : " + actifs.Length + " textes actifs dans le cabinet, attendu au moins " + TEXTES_MIN);
            textes.AddRange(actifs.Where(t => !nommes.Contains(t)).Select(t => (Chemin(t.transform), t.text)));
            foreach (var (ou, texte) in textes)
            {
                if (TexteDuMonde.Interdit(texte, ids) is string mot) throw Echec("mot interdit « " + mot + " » dans « " + ou + " » : « " + Ligne(texte) + " »");
                if (TexteDuMonde.SansUnite(texte) is string nu) throw Echec("nombre sans unité « " + nu + " » dans « " + ou + " » : « " + Ligne(texte) + " »");
                juges++;
            }
            // Territoire conservé : l'en-tête, puis une part par lieu servi, coupées aux lignes vides.
            var racine = doc.Champs; var maisons = DocumentDuMonde.Objet(DocumentDuMonde.Objet(racine, "noms"), "maisons");
            string Maitre(Dictionary<string, object> l) => DocumentDuMonde.Valeur(l, "maitre") is string qui ? "Maison : " + DocumentDuMonde.Texte(DocumentDuMonde.Objet(maisons, qui), "nom") : "Sans maître";
            var places = DocumentDuMonde.Tableau(racine, "lieux").Select(l => l as Dictionary<string, object> ?? throw Echec("références : lieu illisible")).ToList();
            var rang0 = places.Single(l => DocumentDuMonde.Entier(l, "rang") == 0);
            string[] parts = territoire.text.Replace("\r", "").Split(new[] { "\n\n" }, StringSplitOptions.None);
            string[] entete = { DocumentDuMonde.Texte(rang0, "nom") + " · " + Maitre(rang0), TexteDuMonde.Date(new DateDuMonde(doc.Annee.Value, doc.JourDeLAnnee.Value)),
                TexteDuMonde.Nombre(DocumentDuMonde.Entier(racine, "population")) + " habitants dans le territoire" };
            foreach (string v in entete) Lire(DOSSIER, parts[0], v);
            foreach (var l in places)
            {
                string appel = DocumentDuMonde.Texte(l, "nom"), ou = DOSSIER + " · " + appel; string[] siennes = parts.Skip(1).Where(p => Ligne(p) == appel).ToArray();
                if (siennes.Length != 1) throw Echec("lieu absent « " + appel + " » dans « " + DOSSIER + " »");
                Lire(ou, siennes[0], TexteDuMonde.Nombre(DocumentDuMonde.Entier(l, "population")) + " habitants · " + DocumentDuMonde.Nombre(l, "surface_km2").ToString("0.##", Fr) + " km²");
                Lire(ou, siennes[0], Maitre(l)); var stocks = DocumentDuMonde.Objet(l, "stocks");
                foreach (string cle in stocks.Keys) Lire(ou, siennes[0], cle + " : " + TexteDuMonde.Masse(DocumentDuMonde.Nombre(stocks, cle)));
                if (!(DocumentDuMonde.Valeur(l, "flux_30j") is Dictionary<string, object> flux)) continue;
                Lire(ou, siennes[0], "Sur 30 jours : " + TexteDuMonde.Masse(DocumentDuMonde.Nombre(flux, "preleve_kg")) + " prélevés");
                Lire(ou, siennes[0], Gens(DocumentDuMonde.Entier(flux, "partis_personnes"), "partie") + " · " + Gens(DocumentDuMonde.Entier(flux, "arrives_personnes"), "arrivée"));
            }
            // Terres et comptes, Votre maison, Commandes de maison : les comptes servis par /maison.
            string f = feuillet.text; FluxDeMaison fx = joueur.Flux;
            if (!Lignes(f).Any(l => l.StartsWith(nom + " · ", StringComparison.Ordinal) && l.Contains(" · " + date))) throw Echec("valeur absente « " + nom + " · … · " + date + " » dans « " + FEUILLET + " »"); valeurs++;
            Lire(FEUILLET, f, "Siège : " + m.Siege.Nom); if (suzerain != null) Lire(FEUILLET, f, "Suzerain : " + suzerain.Maison.Nom);
            string part = joueur.Part is double pj ? (pj * 100).ToString("0.##", Fr) : null, grenier = joueur.Grenier == null ? null
                : "Grenier : " + (joueur.Grenier.Count == 0 ? "vide" : string.Join(" · ", joueur.Grenier.OrderBy(g => g.Key, StringComparer.Ordinal).Select(g => g.Key + " : " + TexteDuMonde.Masse(g.Value))));
            if (part != null) Lire(FEUILLET, f, "Prélèvement : " + part + " %"); if (grenier != null) Lire(FEUILLET, f, grenier);
            string Tenue(long cell, long rang) { Lieu t = tenues.First(x => x.CellId == cell); string b = t.Bourg?.Nom ?? throw Echec("références : bourg sans nom servi");
                return rang == 0 ? b : b + " · " + (t.Lieux?.FirstOrDefault(x => x.Rang == rang)?.Nom ?? throw Echec("références : lieu tenu sans nom servi")); }
            foreach (LieuTenu t in m.Lieux) Egale(FEUILLET, f, Tenue(t.CellId, t.Rang));
            foreach (var (cle, kg) in new[] { ("Prélevé", fx.PreleveKg), ("Reçu", fx.RecuKg), ("Dû envoyé", fx.DuEnvoyeKg), ("Consommé en route", fx.MangeEnRouteKg), ("Rendu", fx.RenduKg) }) Lire(FEUILLET, f, cle + " : " + TexteDuMonde.Masse(kg));
            Lire(FEUILLET, f, "Départs : " + Gens(fx.PartisPersonnes)); Lire(FEUILLET, f, "Arrivées : " + Gens(fx.ArrivesPersonnes)); if (fx.SalairesPayesKg is double paye) Lire(FEUILLET, f, "Salaires : " + TexteDuMonde.Masse(paye));
            Lire(MAISON, votre.text, nom); Lire(MAISON, votre.text, "Siège : " + m.Siege.Nom); Lire(MAISON, votre.text, TexteDuMonde.Nombre(m.Lieux.Count) + (m.Lieux.Count == 1 ? " lieu tenu" : " lieux tenus") + " · relevé au " + date);
            if (part != null) Lire(COMMANDES, commandes.text, "Prélèvement : " + part + " % · relevé au " + date); if (grenier != null) Lire(COMMANDES, commandes.text, grenier);
            // Les légendes : chaque terre tenue relevée au jour servi, chaque prélèvement vers le siège, le dû vers le suzerain.
            foreach (Lieu t in tenues) Lire(LIEUX, lieux.text, Tenue(t.CellId, 0) + " · relevé au " + date);
            foreach (LieuPlace l in lieu.Lieux.Where(x => x.Maitre == m.Id && x.Flux != null))
                Lire(FLECHES, fleches.text, m.Siege.CellId == moree && m.Siege.Rang == l.Rang ? m.Siege.Nom + " : " + TexteDuMonde.Masse(l.Flux.PreleveKg) + " prélevés sur place"
                    : Tenue(moree, l.Rang) + " → " + m.Siege.Nom + " : " + TexteDuMonde.Masse(l.Flux.PreleveKg));
            if (suzerain != null) Lire(FLECHES, fleches.text, m.Siege.Nom + " → " + suzerain.Maison.Siege.Nom + " : " + TexteDuMonde.Masse(fx.DuEnvoyeKg) + " de dû");
            if (bulle != null) { if (Lignes(bulle.text).Length != InfobulleDeTerre.LIGNES) throw Echec("l'infobulle a " + Lignes(bulle.text).Length + " lignes, attendu " + InfobulleDeTerre.LIGNES); foreach (string v in entete) Lire(INFOBULLE, bulle.text, v); }
            Lot526.Juger(fiche, bourg); valeurs++;
        }
    }
}
