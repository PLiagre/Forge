using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Threading.Tasks;
using Forge.Interface;
using Forge.Pont;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.UI;

namespace ForgeLocal3D.Captures
{
    // Lot 860 : le jeu s'ouvre en pause et dit quoi faire. Trois scénarios, joués dans l'ordre de leur nom, sur le même service, qui se passent leur état par des champs
    // statiques (comme Lot525) :
    //   1. ouverture-1-en-pause : la carte de 1400 au jour 1, le monde en pause, les terres de départ en or et la ligne « Choisissez votre maison… » ;
    //   2. ouverture-2-terre-proposee : un clic sur la Morée la propose dans « Votre maison », « Choisir cette maison » l'envoie, la ligne dit « Espace : lancer le temps… » ;
    //   3. ouverture-3-temps-lance : Espace lance le temps à la vitesse de la carte, le monde applique le choix, plus aucune terre en or ; Espace remet en pause, la ligne dit « Espace : lancer le temps ».
    // Les phrases attendues s'écrivent ici, en littéraux : ni `CabinetDeCarte.Guide` ni ses constantes ne sont lus. Le service se lit à part, hors du fil principal.
    // Contre-épreuves : `-forge860EnMarche` pose la vitesse de la carte au service avant de juger (un jeu qui s'ouvrirait en marche) : le scénario 1 échoue
    // (« à l'ouverture, le monde avance ») ; `-forge860Hors` vise une terre qui n'est celle d'aucune fiche : le scénario 2 échoue (« aucune maison proposée »).
    static class Lot860
    {
        const string EN_MARCHE = "-forge860EnMarche", HORS = "-forge860Hors", SIEGE = "Mistra", TERRE = "Despotat de Morée";
        const string BANDEAU = "FORGE · Le cabinet", DATE = "Lecture de la date…", BARRE = "Lecture de la maison…", GUIDE = "Prochain geste", TERRES = "Terres conseillées", PREFIXE = "Terre conseillée ";
        const string PAUSE = "Pause / Reprendre", CHOISIR_CETTE = "Choisir cette maison", APERCU = "Consultez une maison avant de vous engager.", TICKS_ARG = "-forgeTicks";
        const string CHOISIR = "Choisissez votre maison : cliquez une terre en surbrillance";
        const string CHOIX_RECU = "Espace : lancer le temps ; le monde applique votre choix au jour suivant";
        const string LANCER = "Espace : lancer le temps";
        const int IMAGES_DE_POSE = 10, LARGEUR_LIGNE = 792; const float CRANS = 12, IMMOBILE_S = 2, MARCHE_S = 3;
        static readonly CultureInfo Inv = CultureInfo.InvariantCulture;

        static CarteDessinee carte; static CabinetDeCarte cabinet; static HorlogeDeCarte horloge; static Transform toile, bandeau, terres; static Text guide, barre, date;
        static Frappe frappe; static int port; static long tick0; static FicheDeDepart[] fiches; static HorlogeLue servie;

        static string N(long v) => v.ToString(Inv); static string N(double v) => v.ToString("R", Inv); static bool Meme(double a, double b) => Math.Abs(a - b) < 1e-6;
        static InvalidOperationException Echec(string cause) => new InvalidOperationException(cause); static bool Drapeau(string d) => Environment.GetCommandLineArgs().Contains(d);
        static string Ecran(Vector2 p) => "(" + Mathf.RoundToInt(p.x) + ", " + Mathf.RoundToInt(p.y) + ")"; static string Ecran(Rect r) => "[" + Ecran(r.min) + " – " + Ecran(r.max) + "]";
        static long Depart() { var a = Environment.GetCommandLineArgs(); int i = Array.IndexOf(a, TICKS_ARG); return i >= 0 && i + 1 < a.Length ? long.Parse(a[i + 1], Inv) : 30; }
        static Transform[] Allumees() => terres.Cast<Transform>().Where(t => t.gameObject.activeSelf).ToArray();

        [ScenarioDeCapture(860, "ouverture-1-en-pause")]
        static IEnumerator OuvertureEnPause(Camera camera)
        {
            var ouverte = new Lot549.CarteOuverte(); for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null;
            carte = ouverte.Carte; port = carte.port;
            cabinet = carte.GetComponent<CabinetDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de CabinetDeCarte");
            horloge = carte.GetComponent<HorlogeDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas d'horloge");
            (carte.GetComponent<SurvolDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de survol")).automatique = true; (carte.GetComponent<ParcoursDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de parcours")).automatique = true;
            if ((carte.GetComponent<CommandesDuTemps>() ?? throw Echec("étape 1 : la carte n'a pas de commandes du temps")).automatique) throw Echec("étape 1 : les commandes du temps sont en automatique, Espace ne serait pas lu");
            toile = carte.transform.Find("Cabinet") ?? throw Echec("étape 1 : la toile du cabinet est introuvable"); bandeau = toile.Find(BANDEAU) ?? throw Echec("étape 1 : le bandeau « " + BANDEAU + " » est introuvable");
            for (var e = Lot690.Jusqua(() => Lot690.LecturePrete(cabinet.Partie) && horloge.Lue != null, () => "étape 1 : " + Lot690.Dire(cabinet.Partie) + ", horloge " + (horloge.Lue == null ? "non lue" : "lue")); e.MoveNext();) yield return null;
            fiches = cabinet.Partie.Departs.Donnees.Fiches.ToArray(); tick0 = Depart();
            // La toile sur la caméra de la photo, comme Lot1045 : les jugements de cadre se font sur ce que l'image montre.
            Lot549.Photographier(camera, carte); camera.rect = new Rect(0f, 0f, 1f, 1f);
            var canvas = toile.GetComponent<Canvas>(); canvas.renderMode = RenderMode.ScreenSpaceCamera; canvas.worldCamera = camera; canvas.planeDistance = camera.nearClipPlane + 0.2f;
            yield return null; Canvas.ForceUpdateCanvases();

            if (Drapeau(EN_MARCHE)) // un jeu qui s'ouvrirait en marche : la vitesse de la carte part au service avant tout jugement
            {
                double v = ReglagesDesVues.Charger().VitesseCarte; var pose = Task.Run(() => { using (var c = new ClientHorloge(port, TimeSpan.FromSeconds(5))) return c.Regler(v); });
                for (var e = Lot690.Attendre(pose, "étape 2 : vitesse de la carte posée au service"); e.MoveNext();) yield return null;
                if (!pose.Result.Presente) throw Echec("étape 2 : le service refuse la vitesse " + N(v) + " : " + pose.Result.Absence);
                for (var e = Lot690.Jusqua(() => horloge.Lue != null && horloge.Lue.JoursParSeconde > 0, () => "étape 2 : l'horloge de la carte ne voit pas la vitesse posée"); e.MoveNext();) yield return null;
            }

            for (var e = Relire(); e.MoveNext();) yield return null;
            if (servie.Tick != tick0) throw Echec("à l'ouverture, le monde avance : le tick lu vaut " + N(servie.Tick) + ", attendu " + N(tick0) + " (" + TICKS_ARG + ")");
            HorlogeLue lue = horloge.Lue; string dit = (date = bandeau.Find(DATE)?.GetComponent<Text>())?.text ?? "(date introuvable)"; Transform commande = bandeau.Cast<Transform>().FirstOrDefault(t => t.name == PAUSE); string bouton = commande?.GetComponentInChildren<Text>()?.text ?? "(bouton introuvable)";
            if (lue.JoursParSeconde != 0 || !dit.EndsWith("En pause", StringComparison.Ordinal) || bouton != "Reprendre")
                throw Echec("à l'ouverture, le monde avance : " + N(lue.JoursParSeconde) + " jour(s) par seconde, date « " + dit.Replace("\n", " | ") + " », bouton « " + PAUSE + " » : « " + bouton + " »");
            long avant = servie.Tick; for (var e = Secondes(IMMOBILE_S); e.MoveNext();) yield return null;
            for (var e = Relire(); e.MoveNext();) yield return null;
            if (servie.Tick != avant) throw Echec("à l'ouverture, le tick passe de " + N(avant) + " à " + N(servie.Tick));

            terres = carte.transform.Find(TERRES) ?? throw Echec("étape 3 : la racine « " + TERRES + " » est introuvable, enfant direct de la carte");
            for (var e = Lot690.Jusqua(() => Allumees().Length == fiches.Length, () => "étape 3 : " + Allumees().Length + " surbrillance(s) active(s) pour " + fiches.Length + " fiche(s) servie(s)"); e.MoveNext();) yield return null;
            Cadrer(camera, Allumees().Select(t => t.GetComponent<MeshRenderer>().bounds.center)); yield return null; Canvas.ForceUpdateCanvases();
            JugerTerres(camera, "étape 3", fiches.Select(f => f.CellId).ToArray(), Array.Empty<long>());
            guide = bandeau.Find(GUIDE)?.GetComponent<Text>() ?? throw Echec("étape 4 : le texte « " + GUIDE + " » est introuvable dans le bandeau"); barre = bandeau.Find(BARRE)?.GetComponent<Text>() ?? throw Echec("étape 4 : la barre des comptes est introuvable");
            JugerLigne(camera, CHOISIR, "étape 4");
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            JugerTerres(camera, "après la pose", fiches.Select(f => f.CellId).ToArray(), Array.Empty<long>()); JugerLigne(camera, CHOISIR, "après la pose");
            for (var e = Relire(); e.MoveNext();) yield return null; Trace("ouverture-1-en-pause");
        }

        [ScenarioDeCapture(860, "ouverture-2-terre-proposee")]
        static IEnumerator TerreProposee(Camera camera)
        {
            if (carte == null || guide == null) throw Echec("étape 1 : « ouverture-1-en-pause » n'a pas ouvert la carte");
            bool hors = Drapeau(HORS); var survol = carte.GetComponent<FicheDeCellule>() ?? throw Echec("étape 1 : la carte n'a pas de fiche de cellule");
            FicheDeDepart[] mistra = fiches.Where(f => f.Siege.Nom == SIEGE).ToArray();
            if (mistra.Length != 1 || mistra[0].Nom != TERRE) throw Echec("étape 1 : fiches au siège " + SIEGE + " : " + string.Join(", ", mistra.Select(f => f.Nom)) + ", attendu « " + TERRE + " » seule");
            FicheDeDepart moree = mistra[0]; long cellule = moree.CellId;
            var lecture = Task.Run(() => { using (var c = new ClientLieu(port, ClientDeparts.DelaiMinimal)) return c.Lire(cellule); });
            for (var e = Lot690.Attendre(lecture, "étape 2 : lecture /lieu?cell=" + N(cellule)); e.MoveNext();) yield return null;
            if (!lecture.Result.Presente || !(lecture.Result.Lieu.Bourg?.Position is PointCarte position))
                throw Echec("étape 2 : /lieu?cell=" + N(cellule) + " sans point au rang 0 : " + (lecture.Result.Absence ?? lecture.Result.Lieu.AbsenceDesLieux ?? "rang 0 absent ou sans point"));
            Vector3 local = carte.PositionSurLaCarte(position, ReperesDeDepart.HAUTEUR_LIEU) ?? throw Echec("étape 2 : la carte ne place pas le point du lieu"); Vector3 point = carte.transform.TransformPoint(local);
            long cible = cellule;
            if (hors) { point = HorsDesFiches(point, out cible); local = carte.transform.InverseTransformPoint(point); }
            carte.Vue.Zoomer(CRANS, carte.camera.WorldToViewportPoint(point)); carte.Vue.Centrer(new Vector2(local.x, local.z), carte.Vue.Demi);
            yield return null; // la carte se recadre
            Vector2 P = carte.camera.WorldToScreenPoint(point); survol.Survoler(P); CelluleDeCarte vue = survol.Survolee; survol.Quitter();
            if (vue?.CellId != cible || carte.CelluleSous(point)?.CellId != cible) throw Echec("étape 2 : au point " + Ecran(P) + ", la carte voit la cellule " + vue?.CellId + ", attendu " + N(cible));
            if (cabinet.HorsCarte(P)) throw Echec("étape 2 : le point de la terre " + Ecran(P) + " est hors de la carte ou sous un panneau");

            bool clic = Toucher(P, vue);
            for (int i = 0; i < 3; i++) yield return null; // le cabinet relit sa partie et écrit son aperçu
            if (!clic || cabinet.Retenue?.CellId != cible) throw Echec("étape 3 : la terre " + N(cible) + " n'est pas gardée après le clic : retenue " + (cabinet.Retenue?.CellId.ToString() ?? "nulle"));
            Text apercu = toile.GetComponentsInChildren<Text>(true).FirstOrDefault(t => t.name == APERCU) ?? throw Echec("étape 3 : l'aperçu de « Votre maison » est introuvable");
            Button confirmer = toile.GetComponentsInChildren<Button>(true).FirstOrDefault(b => b.name == CHOISIR_CETTE) ?? throw Echec("étape 3 : « " + CHOISIR_CETTE + " » est introuvable");
            if (!apercu.gameObject.activeInHierarchy || !apercu.text.StartsWith(TERRE + " · " + SIEGE, StringComparison.Ordinal) || !confirmer.gameObject.activeInHierarchy || !confirmer.interactable)
                throw Echec("aucune maison proposée après le clic sur la cellule " + N(cible) + " : l'aperçu dit « " + apercu.text.Replace("\n", " | ") + " », « " + CHOISIR_CETTE + " » " + (confirmer.interactable ? "actif" : "inactif"));
            JugerTerres(camera, "étape 3", fiches.Select(f => f.CellId).Where(c => c != cellule).ToArray(), new[] { cellule });
            JugerLigne(camera, CHOISIR, "étape 3");

            confirmer.onClick.Invoke();
            for (var e = Lot690.Jusqua(() => cabinet.Partie.Recu?.Acceptee == true, () => "étape 4 : reçu du choix " + (cabinet.Partie.Recu == null ? "absent" : cabinet.Partie.Recu.Presente ? "refusé : " + cabinet.Partie.Recu.Erreur : "perdu : " + cabinet.Partie.Recu.Absence)); e.MoveNext();) yield return null;
            for (var e = Lot690.Jusqua(() => guide.gameObject.activeSelf && guide.text == CHOIX_RECU, () => "étape 4 : la ligne " + (guide.gameObject.activeSelf ? "dit « " + guide.text + " »" : "se tait") + ", attendu « " + CHOIX_RECU + " »"); e.MoveNext();) yield return null;
            JugerLigne(camera, CHOIX_RECU, "étape 4");
            for (var e = Relire(); e.MoveNext();) yield return null;
            var monde = Lot690.LireMonde(port); for (var e = Lot690.Attendre(monde, "étape 4 : lecture /monde"); e.MoveNext();) yield return null;
            Lot690.ExigerMonde(monde.Result, tick0, null, "étape 4");
            if (servie.JoursParSeconde != 0 || servie.Tick != tick0) throw Echec("étape 4 : après le choix, le monde est à " + N(servie.JoursParSeconde) + " jour(s) par seconde, au tick " + N(servie.Tick) + " (attendu la pause au tick " + N(tick0) + ")");
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            for (var e = Relire(); e.MoveNext();) yield return null; Trace("ouverture-2-terre-proposee");
        }

        [ScenarioDeCapture(860, "ouverture-3-temps-lance")]
        static IEnumerator TempsLance(Camera camera)
        {
            if (carte == null || guide == null) throw Echec("étape 1 : « ouverture-1-en-pause » n'a pas ouvert la carte");
            double v = ReglagesDesVues.Charger().VitesseCarte; HorlogeLue repris = null, arret = null;
            for (var e = Touche(Key.Space, Servie(h => h.JoursParSeconde > 0 && (repris = h) != null, "étape 2 : reprise")); e.MoveNext();) yield return null;
            if (!Meme(repris.JoursParSeconde, v)) throw Echec("reprise à " + N(repris.JoursParSeconde) + " jours par seconde, attendu la vitesse de la carte " + N(v));
            for (var e = Lot690.Jusqua(() => horloge.Lue != null && horloge.Lue.JoursParSeconde > 0, () => "étape 2 : l'horloge de la carte ne voit pas la reprise"); e.MoveNext();) yield return null;
            if (!Meme(horloge.Lue.JoursParSeconde, v)) throw Echec("reprise à " + N(horloge.Lue.JoursParSeconde) + " jours par seconde sur la carte, attendu la vitesse de la carte " + N(v));
            long depart = repris.Tick; for (var e = Secondes(MARCHE_S); e.MoveNext();) yield return null;
            for (var e = Relire(); e.MoveNext();) yield return null;
            if (servie.Tick < depart + 2) throw Echec("étape 3 : le tick servi passe de " + N(depart) + " à " + N(servie.Tick) + " en " + N(MARCHE_S) + " s, au moins 2 attendus");
            for (var e = Lot690.Jusqua(() => cabinet.Partie.Monde?.Presente == true && cabinet.Partie.Monde.Donnees.MaisonDuJoueur != null && cabinet.Partie.Maison?.Presente == true && cabinet.Partie.Maison.Donnees.Siege.Nom == SIEGE,
                () => "étape 4 : maison du joueur « " + (cabinet.Partie.Monde?.Donnees?.MaisonDuJoueur ?? "aucune") + " », siège lu « " + (cabinet.Partie.Maison?.Presente == true ? cabinet.Partie.Maison.Donnees.Siege.Nom : "aucun") + " », attendu « " + SIEGE + " »"); e.MoveNext();) yield return null;
            for (int i = 0; i < 3; i++) yield return null;
            if (Allumees().Length != 0) throw Echec("étape 4 : " + Allumees().Length + " terre(s) encore en or, la maison est choisie");
            if (guide.gameObject.activeSelf) throw Echec("étape 4 : le temps file, la ligne dit encore « " + guide.text + " »");

            for (var e = Touche(Key.Space, Servie(h => h.JoursParSeconde == 0 && (arret = h) != null, "étape 5 : pause")); e.MoveNext();) yield return null;
            for (var e = Lot690.Jusqua(() => guide.gameObject.activeSelf && guide.text == LANCER, () => "étape 5 : la ligne " + (guide.gameObject.activeSelf ? "dit « " + guide.text + " »" : "se tait") + ", attendu « " + LANCER + " »"); e.MoveNext();) yield return null;
            string nom = cabinet.Partie.Maison.Donnees.Nom ?? throw Echec("étape 5 : la maison du joueur n'a pas de nom servi"); // la barre rattrape le tick de la pause : les comptes se relisent une fois par seconde
            for (var e = Lot690.Jusqua(() => barre.text.StartsWith(nom, StringComparison.Ordinal) && !bandeau.GetComponentsInChildren<Text>().Any(t => t.text.Contains("en attente du monde")),
                () => "étape 5 : la barre dit « " + barre.text.Replace("\n", " | ") + " », attendu la maison « " + nom + " » et des jauges lues"); e.MoveNext();) yield return null;
            var passage = carte.GetComponent<PassageALaCapitale>() ?? throw Echec("étape 5 : la carte n'a pas de passage à la capitale");
            if (passage.SiegeLu != null) throw Echec("étape 5 : le passage lit un siège avec ville (" + N(passage.SiegeLu.Value) + ") : la Morée n'a pas de ville");
            JugerLigne(camera, LANCER, "étape 5"); JugerTerres(camera, "étape 5", Array.Empty<long>(), fiches.Select(f => f.CellId).ToArray());
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            JugerLigne(camera, LANCER, "après la pose");
            for (var e = Relire(); e.MoveNext();) yield return null; Trace("ouverture-3-temps-lance");
        }

        // `allumees` : exactement ces terres ont une surbrillance active, sous « Terres conseillées » et nulle part ailleurs ; `eteintes` : celles-là existent ou non, mais inactives.
        static void JugerTerres(Camera camera, string quand, long[] allumees, long[] eteintes)
        {
            Transform[] actives = Allumees(); string[] voulues = allumees.Select(c => PREFIXE + N(c)).ToArray();
            if (actives.Length != voulues.Length || !voulues.All(n => actives.Any(t => t.name == n)) || carte.GetComponentsInChildren<MeshRenderer>().Count(r => r.name.StartsWith(PREFIXE, StringComparison.Ordinal) && r.gameObject.activeInHierarchy) != voulues.Length)
                throw Echec(quand + " : surbrillances actives « " + string.Join(", ", actives.Select(t => t.name)) + " », attendu « " + string.Join(", ", voulues) + " »");
            foreach (long c in eteintes) { Transform t = terres.Find(PREFIXE + N(c)); if (t != null && t.gameObject.activeSelf) throw Echec(quand + " : la surbrillance de la terre " + N(c) + " est active"); }
            Color32 or = ColorUtility.TryParseHtmlString("#B49A61", out Color brut) ? (Color32)brut : throw Echec("couleur or illisible");
            foreach (Transform t in actives)
            {
                var rendu = t.GetComponent<MeshRenderer>() ?? throw Echec(quand + " : « " + t.name + " » sans MeshRenderer"); Color32 couleur = rendu.sharedMaterial.color;
                if (!couleur.Equals(or)) throw Echec(quand + " : « " + t.name + " » de couleur " + couleur + ", attendu l'or " + or);
                if (t.TryGetComponent<Collider>(out _)) throw Echec(quand + " : « " + t.name + " » porte un collider");
                Vector3 vu = camera.WorldToViewportPoint(rendu.bounds.center);
                if (vu.z <= 0f || vu.x < 0f || vu.x > 0.67f || vu.y < 0f || vu.y > 1f) throw Echec(quand + " : le centre de « " + t.name + " » tombe hors de la vue de la carte, viewport " + vu.ToString("F3"));
            }
        }

        // La phrase, puis ses juges : aucun mot de la machine, aucun nombre nu, tenue dans ses 792, et ses glyphes ne touchent pas ceux de la barre des comptes.
        static void JugerLigne(Camera camera, string attendue, string quand)
        {
            if (!guide.gameObject.activeInHierarchy) throw Echec(quand + " : le texte « " + GUIDE + " » est inactif, attendu « " + attendue + " »");
            string dit = guide.text; if (dit != attendue) throw Echec(quand + " : la ligne dit « " + dit + " », attendu « " + attendue + " »");
            string refus = TexteDuMonde.Interdit(dit, fiches.Select(f => N(f.Id)).Concat(fiches.Select(f => N(f.CellId))).ToArray()) ?? TexteDuMonde.SansUnite(dit);
            if (refus != null) throw Echec(quand + " : « " + refus + " » refusé dans la ligne « " + dit + " »");
            Canvas.ForceUpdateCanvases();
            if (guide.preferredWidth > LARGEUR_LIGNE + .5f) throw Echec(quand + " : la ligne fait " + N(guide.preferredWidth) + " px pour " + LARGEUR_LIGNE);
            Rect a = Glyphes(camera, guide), b = Glyphes(camera, barre);
            if (Rect.MinMaxRect(a.xMin - 1, a.yMin - 1, a.xMax + 1, a.yMax + 1).Overlaps(b)) throw Echec(quand + " : les glyphes de la ligne " + Ecran(a) + " touchent ceux de la barre " + Ecran(b));
        }

        static Rect Glyphes(Camera camera, Text t)
        {
            IList<UIVertex> v = t.cachedTextGenerator.verts; if (v.Count == 0) throw Echec("« " + t.name + " » sans un glyphe dessiné"); float ppu = t.pixelsPerUnit;
            Vector2[] p = v.Select(s => (Vector2)RectTransformUtility.WorldToScreenPoint(camera, t.rectTransform.TransformPoint(s.position / ppu))).ToArray();
            return Rect.MinMaxRect(p.Min(q => q.x), p.Min(q => q.y), p.Max(q => q.x), p.Max(q => q.y));
        }

        // Le centre des terres dans la bande libre de la vue de la carte (à gauche du cabinet, sous le bandeau), avec une marge ; la caméra de la photo, de dessus, nord en haut.
        static void Cadrer(Camera camera, IEnumerable<Vector3> centres)
        {
            const float X0 = .03f, X1 = .64f, Y0 = .04f, Y1 = .8f, MARGE_KM = 90f;
            Vector3[] p = centres.Select(carte.transform.InverseTransformPoint).ToArray(); float minX = p.Min(q => q.x) - MARGE_KM, maxX = p.Max(q => q.x) + MARGE_KM, minZ = p.Min(q => q.z) - MARGE_KM, maxZ = p.Max(q => q.z) + MARGE_KM;
            float demi = Mathf.Max((maxX - minX) / (2f * Lot549.FORME * (X1 - X0)), (maxZ - minZ) / (2f * (Y1 - Y0)));
            float x = (minX + maxX) / 2f - ((X0 + X1) / 2f - .5f) * 2f * demi * Lot549.FORME, z = (minZ + maxZ) / 2f - ((Y0 + Y1) / 2f - .5f) * 2f * demi;
            camera.transform.SetPositionAndRotation(carte.transform.TransformPoint(new Vector3(x, CarteDessinee.HAUTEUR_CAMERA, z)), Quaternion.Euler(90, 0, 0)); camera.orthographicSize = demi;
        }

        // Une terre de la carte qui n'est celle d'aucune fiche : la première trouvée autour du point, par couronnes de 30 km.
        static Vector3 HorsDesFiches(Vector3 depart, out long cellule)
        {
            var celles = new HashSet<long>(fiches.Select(f => f.CellId));
            for (int r = 1; r <= 40; r++)
                for (int d = 0; d < 8; d++)
                {
                    float angle = d * Mathf.PI / 4f; Vector3 p = depart + new Vector3(Mathf.Cos(angle), 0f, Mathf.Sin(angle)) * (30f * r); CelluleDeCarte sous = carte.CelluleSous(p);
                    if (sous != null && !celles.Contains(sous.CellId)) { cellule = sous.CellId; return p; }
                }
            throw Echec("étape 2 : aucune terre hors des fiches autour de la Morée (" + HORS + ")");
        }

        // Le geste de Lot855 : appui, relâché, comme Update ; HorsCarte n'est calculé qu'à l'appui et au relâché.
        static bool Toucher(Vector2 ici, CelluleDeCarte sous)
            => cabinet.Noter(ici, true, false, cabinet.HorsCarte(ici), sous) | cabinet.Noter(ici, false, false, false, sous) | cabinet.Noter(ici, false, true, cabinet.HorsCarte(ici), sous);

        // Une lecture de /horloge, hors du fil principal : `servie`.
        static IEnumerator Relire()
        {
            var t = Task.Run(() => { using (var c = new ClientHorloge(port, TimeSpan.FromSeconds(5))) return c.Lire(); });
            for (var e = Lot690.Attendre(t, "lecture /horloge"); e.MoveNext();) yield return null;
            if (!t.Result.Presente) throw Echec("/horloge absente : " + t.Result.Absence);
            servie = t.Result.Donnees;
        }

        // Copiés de Lot730 (privés là-bas) : la touche passe par le système d'entrée, et /horloge se lit hors du fil principal, une lecture à la fois.
        static void Armer(Key? touche) { if (frappe == null) frappe = new GameObject("Frappe").AddComponent<Frappe>(); (Frappe.tenue, Frappe.armee) = (touche, true); }
        static IEnumerator Touche(Key touche, IEnumerator pendant)
        {
            Armer(touche); for (int i = 0; i < 6; i++) yield return null;
            while (pendant != null && pendant.MoveNext()) yield return null; Armer(null); yield return null;
        }
        static IEnumerator Servie(Func<HorlogeLue, bool> voulue, string quoi)
        {
            Task<Lecture<HorlogeLue>> t = null;
            return Lot690.Jusqua(() => { if (t != null && t.IsCompleted && t.Result.Presente && voulue(t.Result.Donnees)) return true;
                if (t == null || t.IsCompleted) t = Task.Run(() => { using (var c = new ClientHorloge(port, TimeSpan.FromSeconds(5))) return c.Lire(); }); return false; },
                () => quoi + " : " + (t == null || !t.IsCompleted ? "lecture en cours" : t.Result.Presente ? "vitesse " + t.Result.Donnees.JoursParSeconde : t.Result.Absence));
        }
        static IEnumerator Secondes(double s) { double fin = Time.realtimeSinceStartupAsDouble + s; return Lot690.Jusqua(() => Time.realtimeSinceStartupAsDouble >= fin, () => "attente"); }

        static void Trace(string nom)
        {
            var monde = cabinet.Partie.Monde; string id = monde?.Presente == true ? monde.Donnees.MaisonDuJoueur : null;
            string maison = id == null ? "aucune" : cabinet.Partie.Maison?.Presente == true && cabinet.Partie.Maison.Donnees.Nom != null ? cabinet.Partie.Maison.Donnees.Nom : id;
            Debug.Log("CAPTURE_860 " + nom + " tick " + N(servie.Tick) + ", vitesse " + N(servie.JoursParSeconde) + ", maison « " + maison + " », terres éclairées " + Allumees().Length
                + ", ligne « " + (guide.gameObject.activeSelf ? guide.text : "muette") + " »");
        }
    }
}
