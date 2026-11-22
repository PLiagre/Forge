using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Threading.Tasks;
using Forge.Interface;
using Forge.Pont;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures
{
    // La barre d'outils de la ville de Biskra, jouée par ses boutons et photographiée cinq fois, dans la même session :
    //   1-rue-en-main        le bouton Rue enfoncé, un point posé à l'est ; Valider et Annuler apparaissent, la ligne d'aide
    //                        demande le point suivant de la rue ;
    //   2-caserne-grisee     le grenier est encore bas : le bouton Caserne est grisé et dit ce qu'il manque de grain ;
    //   3-caserne-posee      le grenier paie : le bouton Caserne se prend, un clic sur la parcelle dépose la caserne, son chantier
    //                        s'ouvre, et aucun texte visible ne parle d'un refus ;
    //   4-retour-visible     le bouton « Retour à la carte » est actif et tient tout entier dans l'image ;
    //   5-carte-apres-retour le bouton Retour pressé, la carte de 1400 s'ouvre après le fondu, dessinée.
    // Les cinq scénarios se suivent dans l'ordre de leur nom et partagent l'outil, la cellule et le plan par des champs statiques,
    // remis à zéro par le premier. Le tick de départ est celui que le service sert, jamais un tick écrit en dur.
    static class ScenarioOutilsDeLaVille
    {
        const string Groupe = "outils-de-la-ville", Siege = "Biskra";
        const double PartDuGrain = 0.6;
        const int TicksParcelle = 12, TicksGrenier = 15, Images = 10;
        const double DelaiDuBouton_S = 10, DelaiDuDevisGrise_S = 10, DelaiDeLaCarte_S = 20;
        // La rue de l'est, en mètres du bourg : son départ est le point cliqué du premier scénario. Elle tient à l'est des maisons de 1400
        // et sur un relief sous la limite de pente des routes. La parcelle qu'on y découpe est à sa gauche : à 2 m du départ, 10 m de façade, 20 m de fond.
        static readonly (double x, double y)[] Route = { (72, -40), (94, -40) };
        const double DebutM = 2, FacadeM = 10, ProfondeurM = 20, LargeurRoute = 4, Tolerance = 0.5;
        const string Cote = "gauche";
        static readonly double X0 = Route[0].x + DebutM, X1 = X0 + FacadeM, Y0 = Route[0].y + LargeurRoute / 2, Y1 = Y0 + ProfondeurM, CentreX = (X0 + X1) / 2, CentreY = (Y0 + Y1) / 2;
        // La caméra : de trois quarts. La barre couvre le quart bas de l'image, le feuillet du bourg le haut à gauche : l'ensemble se
        // centre dans ce qui reste, et chaque cible doit tomber dans la marge ci-dessous.
        const float CapDeVue = 160f, InclinaisonDeVue = 35f, HauteurDeLaTour = 14f, DistanceMinDuBourg_M = 80f;
        const string PrixNonLu = "prix non lu";
        static readonly Vector2 CentreDeLImage = new(0.62f, 0.62f);
        const float MargeGauche = .08f, MargeDroite = .98f, MargeBasse = .32f, MargeHaute = .96f;
        static readonly string[] Refus = { "refuserait", "refuse" };

        static DesertRoadTool outil;
        static int port, fait;
        static string maison;
        static long cellule, tickDepart, rue, parcelle;
        static (Vector3 vise, float distance) cadreDeLaRue, cadreDeLaCaserne;

        static Exception Faux(string m) => new InvalidOperationException(m);

        [ScenarioDeCapture(Groupe, "1-rue-en-main")]
        static IEnumerator RueEnMain(Camera camera)
        {
            outil = null; port = fait = 0; maison = null; cellule = tickDepart = rue = parcelle = -1;
            outil = Object.FindFirstObjectByType<DesertRoadTool>() ?? throw Faux("pas d'outil de la ville");
            var ville = camera.GetComponent<DesertCityCamera>() ?? throw Faux("pas de caméra de ville");
            var lieu = Object.FindFirstObjectByType<PanneauLieu>() ?? throw Faux("pas de panneau du lieu");
            outil.automatique = ville.automatique = true; if (ville.Marcheur) ville.Marcheur.automatic = true;
            port = outil.Port; int p = port;
            var lus = Task.Run(() => { using (var d = new ClientDeparts(p, ClientDeparts.DelaiMinimal)) return d.Lire(); });
            while (!lus.IsCompleted) yield return null;
            if (lus.IsFaulted || !lus.Result.Presente) throw Faux(lus.IsFaulted ? lus.Exception.GetBaseException().Message : lus.Result.Absence);
            var zab = lus.Result.Donnees.Fiches.Where(f => f.Siege.Nom == Siege).ToArray();
            if (zab.Length != 1) throw Faux(zab.Length + " sièges " + Siege);
            long c = cellule = zab[0].CellId; maison = "seigneurie-" + zab[0].Id;

            // Le choix de départ, un tick : le monde sert alors la maison du joueur et ses gestes de bâtisseur.
            GestesDeCapture.Deposer(port, "{\"type\":\"choisir_depart\",\"seigneurie\":" + zab[0].Id + "}"); GestesDeCapture.Tick(port);
            tickDepart = GestesDeCapture.Lire(port, c).Tick; Debug.Log("CAPTURE_OUTILS départ servi au tick " + L(tickDepart));
            yield return null;

            if (!outil.Ouvrir(c)) throw Faux("ouverture de " + Siege + " refusée : " + outil.Message);
            lieu.Ouvrir(c);
            yield return null;

            // L'outil se prend par son bouton, le point se pose de haut par l'outil du joueur.
            outil.Barre.Bouton(GesteDeLaVille.Rue).onClick.Invoke();
            if (outil.Outil != OutilDeLaVille.Rue) throw Faux("le bouton Rue n'a pas mis l'outil en main : " + outil.Outil);
            var t = outil.roads.terrain;
            GestesDeCapture.Cliquer(camera, ville, outil, GestesDeCapture.Monde(t, Route[0].x, Route[0].y), Route[0]);

            var composition = outil.Recomposer() ?? throw Faux("la ville n'a pas de barre des outils");
            if (!composition[GesteDeLaVille.Rue].Enfonce) throw Faux("le bouton Rue n'est pas enfoncé alors que la rue est en main");
            foreach (var geste in new[] { GesteDeLaVille.Valider, GesteDeLaVille.Annuler })
            {
                if (!composition[geste].Visible) throw Faux("le bouton " + geste + " n'est pas visible avec la rue en main");
                if (!outil.Barre.Bouton(geste).gameObject.activeInHierarchy) throw Faux("le bouton " + geste + " n'est pas actif dans la hiérarchie");
            }
            const string ligne = "Cliquez le point suivant de la rue.";
            if (composition.Ligne != ligne || outil.Barre.Ligne.text != ligne)
                throw Faux("la ligne d'aide dit « " + composition.Ligne + " » (barre : « " + outil.Barre.Ligne.text + " ») au lieu de « " + ligne + " »");
            Debug.Log("CAPTURE_OUTILS rue en main, point posé en " + P(Route[0].x, Route[0].y) + " ; ligne : " + composition.Ligne);

            // Le devis de la caserne est relu au service une fois par seconde : le bouton ne doit plus dire « prix non lu » à la photo.
            double debut = Time.realtimeSinceStartupAsDouble;
            while (outil.Recomposer()[GesteDeLaVille.Caserne].Libelle.Contains(PrixNonLu))
            {
                if (Time.realtimeSinceStartupAsDouble - debut > DelaiDuDevisGrise_S)
                    throw Faux("le bouton Caserne dit encore « " + PrixNonLu + " » après " + DelaiDuDevisGrise_S + " s : « " + outil.Composition[GesteDeLaVille.Caserne].Libelle.Replace("\n", " / ") + " »");
                yield return null;
            }

            // Le bourg de 1400 et le point posé à l'est, ensemble, dans la zone libre de l'image.
            var maisons = outil.Maisons?.Racine != null ? outil.Maisons.Racine.GetComponentsInChildren<Renderer>() : new Renderer[0];
            if (maisons.Length == 0) throw Faux("le bourg de 1400 n'est pas dessiné : aucune maison");
            var boite = maisons[0].bounds; foreach (var r in maisons) boite.Encapsulate(r.bounds);
            var point = GestesDeCapture.Monde(t, Route[0].x, Route[0].y);
            cadreDeLaRue = Cadrage(camera, ville, (boite.center + point) / 2, new List<Vector3> { boite.center, point }, DistanceMinDuBourg_M);
            Cadrer(camera, ville, cadreDeLaRue);
            var vu = camera.WorldToViewportPoint(point);
            if (!(vu.z > camera.nearClipPlane && vu.x > 0 && vu.x < 1 && vu.y > MargeBasse))
                throw Faux("le point posé est hors de l'image ou sous la barre : vue (" + vu.x.ToString("F2", CultureInfo.InvariantCulture) + " ; " + vu.y.ToString("F2", CultureInfo.InvariantCulture) + ")");
            Debug.Log("CAPTURE_OUTILS cadre du bourg à " + cadreDeLaRue.distance.ToString("F0", CultureInfo.InvariantCulture) + " m, point en vue ("
                + vu.x.ToString("F2", CultureInfo.InvariantCulture) + " ; " + vu.y.ToString("F2", CultureInfo.InvariantCulture) + ")");
            for (int k = 0; k < Images; k++) yield return null;
            outil.Recomposer();
            fait = 1;
        }

        [ScenarioDeCapture(Groupe, "2-caserne-grisee")]
        static IEnumerator CaserneGrisee(Camera camera)
        {
            Reprendre(1, "1-rue-en-main");
            var ville = camera.GetComponent<DesertCityCamera>() ?? throw Faux("pas de caméra de ville");
            Cadrer(camera, ville, cadreDeLaRue);

            // Le devis relu au service, hors du fil principal, peut avoir une seconde de retard : on attend que le bouton dise le manque.
            double debut = Time.realtimeSinceStartupAsDouble;
            BoutonCompose bouton;
            while (true)
            {
                bouton = outil.Recomposer()?[GesteDeLaVille.Caserne] ?? throw Faux("la ville n'a pas de barre des outils");
                if (bouton.Actif) throw Faux("le grenier paie déjà la caserne : le bouton est actif (« " + bouton.Libelle + " »), la capture ne prouve rien");
                if (bouton.Libelle.IndexOf("il manque", StringComparison.Ordinal) >= 0) break;
                if (Time.realtimeSinceStartupAsDouble - debut > DelaiDuDevisGrise_S)
                    throw Faux("le bouton Caserne ne dit pas le manque de grain en " + DelaiDuDevisGrise_S + " s : « " + bouton.Libelle + " »");
                yield return null;
            }
            var bout = outil.Barre.Bouton(GesteDeLaVille.Caserne);
            if (bouton.Actif || bout.interactable) throw Faux("le bouton Caserne n'est pas grisé : actif " + bouton.Actif + ", interactable " + bout.interactable);
            if (bouton.Libelle.IndexOf("il manque", StringComparison.Ordinal) < 0 || bouton.Libelle.IndexOf("de grain", StringComparison.Ordinal) < 0)
                throw Faux("le libellé du bouton Caserne ne dit pas le manque de grain : « " + bouton.Libelle + " »");

            // Le monde dit la même chose que le bouton.
            var ordres = Ordres();
            if (!ordres.Presente) throw Faux("devis absent : " + ordres.Absence);
            var bat = ordres.Donnees.Levee.Batiment ?? throw Faux("la capitale est hors de la carte : pas de devis de la caserne");
            if (!(bat.ManqueKg > 0)) throw Faux("le devis du monde ne manque de rien (manque " + N(bat.ManqueKg) + " kg) : un bouton grisé sans cause ne prouve rien");
            Debug.Log("CAPTURE_OUTILS caserne grisée au tick " + L(ordres.Donnees.Tick) + " : « " + bouton.Libelle.Replace("\n", " / ") + " » ; le monde dit manque " + N(bat.ManqueKg) + " kg");
            for (int k = 0; k < Images; k++) yield return null;
            outil.Recomposer();
            fait = 2;
        }

        [ScenarioDeCapture(Groupe, "3-caserne-posee")]
        static IEnumerator CasernePosee(Camera camera)
        {
            Reprendre(2, "2-caserne-grisee");
            var ville = camera.GetComponent<DesertCityCamera>() ?? throw Faux("pas de caméra de ville");
            var lieu = Object.FindFirstObjectByType<PanneauLieu>() ?? throw Faux("pas de panneau du lieu");
            outil.Annuler();
            string geste = "\"maison\":\"" + maison + "\",\"cell\":" + L(cellule);

            // Le grain : la part du joueur au plus haut, puis la route de l'est.
            GestesDeCapture.Deposer(port, "{\"type\":\"fixer_part\",\"maison\":\"" + maison + "\",\"part\":" + N(PartDuGrain) + "}");
            GestesDeCapture.Deposer(port, "{\"type\":\"tracer_route\"," + geste + ",\"points\":[" + string.Join(",", Route.Select(q => P(q.x, q.y))) + "],\"largeur_m\":" + N(LargeurRoute) + "}");
            GestesDeCapture.Tick(port);
            var plan = GestesDeCapture.Lire(port, cellule);
            var route = plan.Rues.FirstOrDefault(u => u.Points.Count == Route.Length && Enumerable.Range(0, Route.Length).All(i => Math.Abs(u.Points[i].X - Route[i].x) < 1e-6 && Math.Abs(u.Points[i].Y - Route[i].y) < 1e-6))
                ?? throw Faux("la route de l'est n'est pas au plan du tick " + L(plan.Tick));
            rue = route.Identifiant; yield return null;

            // La parcelle, puis les ticks qui l'achèvent.
            var avant = new HashSet<long>(plan.Parcelles.Select(q => q.Identifiant));
            GestesDeCapture.Deposer(port, "{\"type\":\"decouper_parcelle\"," + geste + ",\"rue\":" + L(rue) + ",\"segment\":0,\"debut_m\":" + N(DebutM) + ",\"facade_m\":" + N(FacadeM)
                + ",\"profondeur_m\":" + N(ProfondeurM) + ",\"cote\":\"" + Cote + "\"}");
            for (int k = 0; ; k++)
            {
                GestesDeCapture.Tick(port); plan = GestesDeCapture.Lire(port, cellule);
                var neuves = plan.Parcelles.Where(q => !avant.Contains(q.Identifiant)).ToArray();
                if (neuves.Length > 1) throw Faux(neuves.Length + " parcelles neuves au plan du tick " + L(plan.Tick));
                if (neuves.Length == 1 && !neuves[0].EnChantier) { parcelle = neuves[0].Identifiant; break; }
                if (k >= TicksParcelle) throw Faux("parcelle inachevée après " + TicksParcelle + " ticks, au tick " + L(plan.Tick));
                yield return null;
            }
            var contour = plan.Parcelles.First(q => q.Identifiant == parcelle).Contour;
            bool Pres(double a, double b) => Math.Abs(a - b) < Tolerance;
            if (!(Pres(contour.Min(q => q.X), X0) && Pres(contour.Max(q => q.X), X1) && Pres(contour.Min(q => q.Y), Y0) && Pres(contour.Max(q => q.Y), Y1)))
                throw Faux("la parcelle " + L(parcelle) + " n'est pas à (" + N(X0) + " ; " + N(Y0) + ")–(" + N(X1) + " ; " + N(Y1) + ")");

            // Le grenier : le devis du monde, un tick à la fois, jusqu'à ce qu'il paie la caserne.
            for (int k = 0; ; k++)
            {
                var ordres = Ordres();
                if (!ordres.Presente) throw Faux("devis absent : " + ordres.Absence);
                var bat = ordres.Donnees.Levee.Batiment ?? throw Faux("la capitale est hors de la carte : pas de devis de la caserne");
                if (bat.Refus == null) { Debug.Log("CAPTURE_OUTILS le grenier paie la caserne au tick " + L(ordres.Donnees.Tick) + " après " + k + " tick(s)"); break; }
                if (k >= TicksGrenier) throw Faux("le grenier ne paie pas la caserne après " + TicksGrenier + " ticks, au tick " + L(ordres.Donnees.Tick) + " : " + bat.Refus);
                GestesDeCapture.Tick(port); yield return null;
            }

            // La ville rouverte, le bouton Caserne attendu actif, l'outil pris par lui.
            if (!outil.Ouvrir(cellule)) throw Faux("réouverture de " + Siege + " refusée : " + outil.Message);
            lieu.Ouvrir(cellule);
            double attente = Time.realtimeSinceStartupAsDouble;
            while (!(outil.Recomposer()?[GesteDeLaVille.Caserne].Actif ?? false))
            {
                if (Time.realtimeSinceStartupAsDouble - attente > DelaiDuBouton_S)
                    throw Faux("le bouton Caserne reste grisé alors que le monde la permet : « " + outil.Composition?[GesteDeLaVille.Caserne].Libelle + " »");
                yield return null;
            }
            outil.Barre.Bouton(GesteDeLaVille.Caserne).onClick.Invoke();
            if (!outil.ModeCaserne) throw Faux("le bouton Caserne n'a pas mis l'outil en mode caserne : " + outil.Message);
            var t = outil.roads.terrain;
            GestesDeCapture.Cliquer(camera, ville, outil, GestesDeCapture.Monde(t, CentreX, CentreY), (CentreX, CentreY));
            var recu = outil.Recu;
            if (outil.PoseCaserne == null || !outil.PoseCaserne.Presente || outil.PoseCaserne.Parcelle != parcelle)
                throw Faux("caserne désignée sur la parcelle " + (outil.PoseCaserne == null ? "aucune" : outil.PoseCaserne.Presente ? L(outil.PoseCaserne.Parcelle) : outil.PoseCaserne.Absence) + " au lieu de " + L(parcelle));
            if (recu == null || !recu.Acceptee) throw Faux("dépôt de la caserne non accepté : " + (recu == null ? "pas de reçu" : recu.Presente ? recu.Erreur : recu.Absence) + " · " + outil.Message);

            // Un tick : le chantier s'ouvre, l'outil le dessine.
            GestesDeCapture.Tick(port);
            if (!outil.Attendre()) throw Faux("Attendre faux après le tick du dépôt : " + outil.Message);
            Debug.Log("CAPTURE_OUTILS caserne déposée sur la parcelle " + L(parcelle) + ", chantier dessiné");

            // La caserne, sa tour et la rue devant elle, au-dessus de la barre.
            var cibles = contour.Select(q => GestesDeCapture.Monde(t, q.X, q.Y)).Concat(contour.Select(q => GestesDeCapture.Monde(t, q.X, q.Y) + Vector3.up * HauteurDeLaTour))
                .Concat(new[] { X0 - 2, X1 + 6 }.SelectMany(x => new[] { Route[0].y - LargeurRoute / 2, Route[0].y + LargeurRoute / 2 }.Select(y => GestesDeCapture.Monde(t, x, y)))).ToList();
            cadreDeLaCaserne = Cadrage(camera, ville, GestesDeCapture.Monde(t, CentreX, CentreY - 6), cibles);
            Cadrer(camera, ville, cadreDeLaCaserne);
            for (int k = 0; k < Images; k++) yield return null;
            outil.Recomposer();
            foreach (string mot in Refus)
                if (TexteVisible(mot) is string vu) throw Faux("un texte visible à l'image parle d'un refus (« " + mot + " ») : " + vu);
            fait = 3;
        }

        [ScenarioDeCapture(Groupe, "4-retour-visible")]
        static IEnumerator RetourVisible(Camera camera)
        {
            Reprendre(3, "3-caserne-posee");
            var ville = camera.GetComponent<DesertCityCamera>() ?? throw Faux("pas de caméra de ville");
            Cadrer(camera, ville, cadreDeLaCaserne);
            for (int k = 0; k < Images; k++) yield return null;
            var bouton = outil.Barre.Bouton(GesteDeLaVille.Retour);
            outil.Recomposer();
            if (!bouton.gameObject.activeInHierarchy) throw Faux("le bouton Retour à la carte n'est pas actif dans la hiérarchie");
            if (!bouton.interactable) throw Faux("le bouton Retour à la carte est grisé");
            var coins = new Vector3[4]; ((RectTransform)bouton.transform).GetWorldCorners(coins);
            var toile = bouton.GetComponentInParent<Canvas>()?.rootCanvas ?? throw Faux("le bouton Retour n'est sous aucune toile");
            var camDeLaToile = toile.renderMode == RenderMode.ScreenSpaceOverlay ? null : (toile.worldCamera ?? camera);
            Rect image = camera.pixelRect;
            foreach (var coin in coins)
            {
                Vector2 e = RectTransformUtility.WorldToScreenPoint(camDeLaToile, coin);
                if (e.x < image.xMin || e.x > image.xMax || e.y < image.yMin || e.y > image.yMax)
                    throw Faux("le bouton Retour à la carte sort de l'image : coin en " + e + " pour une image de " + image);
            }
            Debug.Log("CAPTURE_OUTILS bouton Retour entier dans l'image " + image.width.ToString("F0", CultureInfo.InvariantCulture) + "×" + image.height.ToString("F0", CultureInfo.InvariantCulture));
            fait = 4;
        }

        [ScenarioDeCapture(Groupe, "5-carte-apres-retour")]
        static IEnumerator CarteApresRetour(Camera camera)
        {
            Reprendre(4, "4-retour-visible");
            outil.Barre.Bouton(GesteDeLaVille.Retour).onClick.Invoke();
            double debut = Time.realtimeSinceStartupAsDouble;
            while (SceneManager.GetActiveScene().name != OuvertureDeLaCarte.SCENE || Object.FindObjectsByType<TransitionDeVue>(FindObjectsSortMode.None).Any(x => x.EnCours))
            {
                if (Time.realtimeSinceStartupAsDouble - debut > DelaiDeLaCarte_S)
                    throw Faux("la carte ne s'ouvre pas en " + DelaiDeLaCarte_S + " s : scène « " + SceneManager.GetActiveScene().name + " », transition "
                        + (Object.FindObjectsByType<TransitionDeVue>(FindObjectsSortMode.None).Any(x => x.EnCours) ? "en cours" : "absente ou finie"));
                yield return null;
            }
            Debug.Log("CAPTURE_OUTILS scène « " + SceneManager.GetActiveScene().name + " » active après " + (Time.realtimeSinceStartupAsDouble - debut).ToString("F1", CultureInfo.InvariantCulture) + " s");
            // La carte dessinée : ses cellules posées, sa caméra et sa vue prêtes.
            CarteDessinee carte = null;
            debut = Time.realtimeSinceStartupAsDouble;
            while (!((carte = Object.FindFirstObjectByType<CarteDessinee>()) != null && carte.Vue != null && carte.camera != null && carte.CellulesPosees > 0 && carte.CellulesPosees == carte.CellulesServies))
            {
                if (Time.realtimeSinceStartupAsDouble - debut > DelaiDeLaCarte_S)
                    throw Faux("la carte n'est pas dessinée en " + DelaiDeLaCarte_S + " s : " + (carte == null ? "pas de carte" : carte.CellulesPosees + " cellules posées sur " + carte.CellulesServies));
                yield return null;
            }
            // Toute la largeur de la photo pour la carte, la vue que le joueur vient d'ouvrir gardée : seul son cadre épouse l'image.
            carte.camera.rect = new Rect(0, 0, 1, 1);
            carte.Vue.Changer(carte.camera.aspect); carte.Vue.Poser(carte.camera, carte.transform);
            for (int k = 0; k < Images; k++) yield return null;
            Debug.Log("CAPTURE_OUTILS carte dessinée : " + carte.CellulesPosees + " cellules");
            yield return carte.camera;
        }

        static void Reprendre(int attendu, string precedent)
        {
            if (fait != attendu || outil == null) throw Faux("le scénario « " + precedent + " » n'a pas joué");
            if (!outil) throw Faux("l'outil de la ville a disparu après « " + precedent + " »");
        }

        // Le devis du monde pour la maison du joueur, lu hors du fil de l'éditeur.
        static Lecture<OrdresDeGuerre> Ordres()
        {
            int p = port; string m = maison;
            return Task.Run(() => { using (var c = new ClientGuerre(p, TimeSpan.FromSeconds(60))) return c.LireOrdres(m, null); }).GetAwaiter().GetResult();
        }

        static void Cadrer(Camera camera, DesertCityCamera ville, (Vector3 vise, float distance) cadre)
        {
            camera.aspect = 1600f / 900f; ville.Poser(cadre.vise, CapDeVue, InclinaisonDeVue, cadre.distance);
        }

        // La plus petite distance où toutes les cibles tombent dans la zone libre de l'image ; à chaque distance, la vise glisse pour
        // centrer l'ensemble sur CentreDeLImage.
        static (Vector3 vise, float distance) Cadrage(Camera camera, DesertCityCamera ville, Vector3 vise, List<Vector3> cibles, float distanceMin = 12f)
        {
            camera.aspect = 1600f / 900f;
            for (float d = distanceMin; d <= DesertCityCamera.DistanceMax; d *= 1.03f)
            {
                var v0 = vise;
                for (int pas = 0; pas < 5; pas++)
                {
                    ville.Poser(v0, CapDeVue, InclinaisonDeVue, d);
                    var q = cibles.Select(x => camera.WorldToViewportPoint(x)).ToArray();
                    float cx = (q.Min(a => a.x) + q.Max(a => a.x)) / 2, cy = (q.Min(a => a.y) + q.Max(a => a.y)) / 2;
                    float demi = d * Mathf.Tan(camera.fieldOfView * Mathf.Deg2Rad / 2);
                    var plat = Vector3.ProjectOnPlane(camera.transform.forward, Vector3.up).normalized;
                    v0 += camera.transform.right * ((cx - CentreDeLImage.x) * 2 * demi * camera.aspect) + plat * ((cy - CentreDeLImage.y) * 2 * demi / Mathf.Sin(InclinaisonDeVue * Mathf.Deg2Rad));
                }
                ville.Poser(v0, CapDeVue, InclinaisonDeVue, d);
                if (cibles.All(v => Dans(camera, v))) return (v0, d);
            }
            throw Faux("cadrage impossible, caméra " + camera.transform.position);
        }

        static bool Dans(Camera camera, Vector3 v)
        {
            var q = camera.WorldToViewportPoint(v);
            return q.z > camera.nearClipPlane && q.x > MargeGauche && q.x < MargeDroite && q.y > MargeBasse && q.y < MargeHaute;
        }

        // Le premier texte visible à l'image qui contient `mot`, sans tenir compte de la casse ; null s'il n'y en a pas. Un texte de toile
        // est visible si son objet et ses toiles sont actifs, un TextMesh si son rendu l'est.
        static string TexteVisible(string mot)
        {
            foreach (var t in Object.FindObjectsByType<Text>(FindObjectsSortMode.None))
                if (t.isActiveAndEnabled && t.GetComponentsInParent<Canvas>().All(c => c.enabled) && t.text.IndexOf(mot, StringComparison.OrdinalIgnoreCase) >= 0)
                    return t.name + " : " + t.text;
            foreach (var t in Object.FindObjectsByType<TextMesh>(FindObjectsSortMode.None))
            {
                var rendu = t.GetComponent<MeshRenderer>();
                if (rendu != null && rendu.enabled && t.gameObject.activeInHierarchy && t.text.IndexOf(mot, StringComparison.OrdinalIgnoreCase) >= 0)
                    return t.name + " : " + t.text;
            }
            return null;
        }

        static string L(long n) => n.ToString(CultureInfo.InvariantCulture);
        static string N(double v) => v.ToString("R", CultureInfo.InvariantCulture);
        static string P(double x, double y) => "[" + N(x) + "," + N(y) + "]";
    }
}
