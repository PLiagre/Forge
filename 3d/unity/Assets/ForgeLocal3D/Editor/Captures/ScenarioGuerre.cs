using System;
using System.Collections;
using System.Globalization;
using System.Linq;
using System.Net.Http;
using System.Threading.Tasks;
using Forge.Interface;
using Forge.Pont;
using UnityEngine;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures
{
    // La guerre du joueur, jouée par ses gestes (`POST /intention`, puis `/tick`) et photographiée sur la carte : la caserne
    // bâtie, puis l'armée levée qui marche, le siège, et la terre prise qui passe au pays du preneur. Les quatre scénarios
    // se suivent dans l'ordre de leur nom et partagent la partie ; chacun lit le tick servi, jamais un tick écrit en dur.
    // Mesuré sur la graine 0, service sans IA, depuis le tick 30 : seigneurie-2 achève sa caserne en 32 jours, et la place
    // 10461, sans réserve de grain, à 18 jours de marche de sa capitale, tombe 31 jours après le début du siège.
    static class ScenarioGuerre
    {
        // La partie mesurée, que `ScenarioDUnTrait` rejoue aussi pour montrer un lieu qui change de pays.
        internal const int PORT = PanneauLieu.DEFAULT_SERVICE_PORT, SEIGNEURIE = 2, PAQUET = 4;
        internal const long PLACE = 10461;
        internal const int JOURS_MAX_CASERNE = 60, JOURS_MAX_MARCHE = 40, JOURS_MAX_SIEGE = 60; const int JOURS_DE_MARCHE_AVANT_PHOTO = 7, JOURS_DE_SIEGE_AVANT_PHOTO = 3;
        // Les vivres d'une levée : de quoi marcher et tenir un long siège, au plus une part du grain libre servi.
        internal const double JOURS_DE_VIVRES = 140, PART_DU_GRAIN = 0.8;
        const float DEMI_KM = 220f, DEMI_LOIN_KM = 700f; const int IMAGES_DE_POSE = 12;
        internal static readonly TimeSpan DELAI = TimeSpan.FromSeconds(60);
        static string maison; static long armee = -1; static PointCarte? capitale;

        [ScenarioDeCapture("guerre", "01-caserne")]
        static IEnumerator Caserne(Camera camera)
        {
            GestesDeCapture.Deposer(PORT, "{\"type\":\"choisir_depart\",\"seigneurie\":" + SEIGNEURIE + "}");
            for (var e = Pousser(1); e.MoveNext();) yield return null;
            var monde = Lire(() => { using (var c = new ClientMonde(PORT, DELAI)) return c.LireAvecMaison(); });
            for (var e = AttentesDeCapture.Attendre(monde, "lecture du monde"); e.MoveNext();) yield return null;
            maison = monde.Result.Presente ? monde.Result.Donnees.MaisonDuJoueur : null;
            if (maison == null) throw new InvalidOperationException("aucune maison du joueur après le choix : " + (monde.Result.Absence ?? "maison nulle"));
            var fiche = Lire(() => { using (var c = new ClientMaison(PORT, DELAI)) return c.Lire(maison); });
            for (var e = AttentesDeCapture.Attendre(fiche, "lecture de la maison"); e.MoveNext();) yield return null;
            if (!fiche.Result.Presente || fiche.Result.Donnees.Siege.CellId == null) throw new InvalidOperationException("siège de " + maison + " illisible : " + fiche.Result.Absence);
            capitale = fiche.Result.Donnees.Siege.Position;
            GestesDeCapture.Deposer(PORT, "{\"type\":\"batir_dans_une_province\",\"maison\":\"" + maison + "\",\"cell\":" + fiche.Result.Donnees.Siege.CellId.Value.ToString(CultureInfo.InvariantCulture) + ",\"nature\":\"caserne\"}");
            // Les jours passent par paquets jusqu'à ce que le devis dise la levée ouverte.
            for (int jours = 0; ; jours += PAQUET)
            {
                if (jours > JOURS_MAX_CASERNE) throw new TimeoutException("la caserne n'est pas achevée en " + JOURS_MAX_CASERNE + " jours");
                for (var e = Pousser(PAQUET); e.MoveNext();) yield return null;
                var devis = Lire(() => { using (var c = new ClientGuerre(PORT, DELAI)) return c.LireOrdres(maison, null); });
                for (var e = AttentesDeCapture.Attendre(devis, "lecture du devis"); e.MoveNext();) yield return null;
                if (devis.Result.Presente && devis.Result.Donnees.Levee.Refus == null) break;
            }
            // La carte : ses pays, leurs frontières et leurs noms, cadrés sur la capitale du joueur.
            SceneManager.LoadScene(OuvertureDeLaCarte.SCENE);
            CarteDessinee carte = null; CarteDeLaGuerre guerre = null;
            for (var e = AttentesDeCapture.Jusqua(() => (carte = Object.FindFirstObjectByType<CarteDessinee>()) != null && carte.Vue != null && carte.camera != null
                && (guerre = Object.FindFirstObjectByType<CarteDeLaGuerre>()) != null && guerre.Terres != null && guerre.CotesDeFrontiere > 0 && guerre.NomsDesPays.Count > 0,
                () => "carte de la guerre non dessinée (" + (guerre == null ? "pas de vue de la guerre" : "frontières " + guerre.CotesDeFrontiere + ", " + (guerre.AbsenceDesTerres ?? "terres lues")) + ")"); e.MoveNext();) yield return null;
            ScenarioAccueil.VerifierLesNoms(guerre); // aucun pays ne porte le nom d'une dynastie servie
            if (capitale is PointCarte siege) Cadrer(carte, carte.PositionSurLaCarte(siege, 0f).Value, DEMI_KM);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            yield return carte.camera;
        }

        [ScenarioDeCapture("guerre", "02-armee-en-marche")]
        static IEnumerator ArmeeEnMarche(Camera camera)
        {
            var (carte, guerre) = Carte();
            var devis = Lire(() => { using (var c = new ClientGuerre(PORT, DELAI)) return c.LireOrdres(maison, PLACE); });
            for (var e = AttentesDeCapture.Attendre(devis, "lecture du devis"); e.MoveNext();) yield return null;
            if (!devis.Result.Presente) throw new InvalidOperationException("devis absent : " + devis.Result.Absence);
            var levee = devis.Result.Donnees.Levee; var cible = devis.Result.Donnees.Cible;
            if (cible?.Maitre == null || cible.RefusDeDeclaration != null) throw new InvalidOperationException("la place ne se déclare pas : " + cible?.RefusDeDeclaration);
            long hommes = IntentionsDeGuerre.Maximum(levee);
            long vivres = (long)Math.Min(levee.GrainLibreKg * PART_DU_GRAIN, hommes * levee.RationKgParHommeParJour * JOURS_DE_VIVRES);
            GestesDeCapture.Deposer(PORT, IntentionsDeGuerre.Lever(maison, IntentionsDeGuerre.Repartir(levee, hommes), vivres), IntentionsDeGuerre.Declarer(maison, cible.Maitre));
            for (var e = Pousser(1); e.MoveNext();) yield return null;
            var guerres = Lire(() => { using (var c = new ClientGuerre(PORT, DELAI)) return c.LireGuerres(); });
            for (var e = AttentesDeCapture.Attendre(guerres, "lecture des guerres"); e.MoveNext();) yield return null;
            var levees = guerres.Result.Presente ? guerres.Result.Donnees.Armees.Where(a => a.Maison == maison).ToList() : null;
            if (levees == null || levees.Count != 1) throw new InvalidOperationException("l'armée levée n'est pas servie : " + (guerres.Result.Absence ?? levees.Count + " armées"));
            armee = levees[0].Identifiant;
            GestesDeCapture.Deposer(PORT, IntentionsDeGuerre.Marcher(maison, armee, PLACE));
            long tick = 0;
            for (var e = Pousser(JOURS_DE_MARCHE_AVANT_PHOTO, t => tick = t); e.MoveNext();) yield return null;
            // L'armée dessinée au tick servi, en marche, avec sa route.
            for (var e = AttentesDeCapture.Jusqua(() => guerre.Guerres != null && guerre.Guerres.Tick >= tick && Dessinee(guerre, a => a.Destination != null && a.Etapes.Count > 0),
                () => "armée en marche non dessinée au tick " + tick); e.MoveNext();) yield return null;
            var servie = guerre.Guerres.Armees.Single(a => a.Identifiant == armee);
            Cadrer(carte, Vector3.Lerp(carte.PositionSurLaCarte(servie.Point, 0f).Value, carte.PositionSurLaCarte(servie.Etapes[servie.Etapes.Count - 1], 0f).Value, .5f), DEMI_KM);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            yield return carte.camera;
        }

        [ScenarioDeCapture("guerre", "03-siege")]
        static IEnumerator Siege(Camera camera)
        {
            var (carte, guerre) = Carte();
            // Les jours passent jusqu'à l'arrivée de l'armée devant la place.
            for (int jours = 0; ; jours += PAQUET)
            {
                if (jours > JOURS_MAX_MARCHE) throw new TimeoutException("l'armée n'est pas arrivée en " + JOURS_MAX_MARCHE + " jours");
                var lues = Lire(() => { using (var c = new ClientGuerre(PORT, DELAI)) return c.LireGuerres(); });
                for (var e = AttentesDeCapture.Attendre(lues, "lecture des guerres"); e.MoveNext();) yield return null;
                var a = lues.Result.Presente ? lues.Result.Donnees.Armees.FirstOrDefault(x => x.Identifiant == armee) : null;
                if (a == null) throw new InvalidOperationException("l'armée n'est plus servie : " + lues.Result.Absence);
                if (a.Destination == null && a.CellId == PLACE) break;
                for (var e = Pousser(PAQUET); e.MoveNext();) yield return null;
            }
            GestesDeCapture.Deposer(PORT, IntentionsDeGuerre.Assieger(maison, armee));
            long tick = 0;
            for (var e = Pousser(JOURS_DE_SIEGE_AVANT_PHOTO, t => tick = t); e.MoveNext();) yield return null;
            for (var e = AttentesDeCapture.Jusqua(() => guerre.Guerres != null && guerre.Guerres.Tick >= tick && Dessinee(guerre, a => a.Siege == PLACE),
                () => "armée au siège non dessinée au tick " + tick); e.MoveNext();) yield return null;
            Cadrer(carte, carte.PositionSurLaCarte(guerre.Guerres.Armees.Single(a => a.Identifiant == armee).Point, 0f).Value, DEMI_KM);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            yield return carte.camera;
        }

        [ScenarioDeCapture("guerre", "04-terre-prise")]
        static IEnumerator TerrePrise(Camera camera)
        {
            var (carte, guerre) = Carte();
            long tick = 0;
            for (int jours = 0; ; jours += PAQUET)
            {
                if (jours > JOURS_MAX_SIEGE) throw new TimeoutException("la place n'est pas tombée en " + JOURS_MAX_SIEGE + " jours de siège de plus");
                for (var e = Pousser(PAQUET, t => tick = t); e.MoveNext();) yield return null;
                var lues = Lire(() => { using (var c = new ClientGuerre(PORT, DELAI)) return c.LireGuerres(); });
                for (var e = AttentesDeCapture.Attendre(lues, "lecture des guerres"); e.MoveNext();) yield return null;
                if (lues.Result.Presente && lues.Result.Donnees.Prises.Any(p => p.CellId == PLACE && p.A == maison)) break;
            }
            // La terre prise peinte au pays du preneur : les terres relues après la chute, et les calques repassés.
            for (var e = AttentesDeCapture.Jusqua(() => guerre.Terres != null && guerre.Terres.Tick >= tick - 1 && guerre.Terres.MaitreDe(PLACE) == maison
                && guerre.Terres.PaysDe(PLACE) == guerre.PaysDeLaMaison(maison), () => "terre prise non relue au tick " + tick); e.MoveNext();) yield return null;
            var lieu = guerre.Guerres?.Armees.FirstOrDefault(a => a.Identifiant == armee);
            Cadrer(carte, lieu != null ? carte.PositionSurLaCarte(lieu.Point, 0f).Value : carte.PositionSurLaCarte(capitale.Value, 0f).Value, DEMI_KM);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            yield return carte.camera;
        }

        // La même terre vue de loin : les lieux qui se recouvriraient se cachent, l'armée et le nombre de ses hommes restent lisibles.
        [ScenarioDeCapture("guerre", "05-terre-prise-de-loin")]
        static IEnumerator TerrePriseDeLoin(Camera camera)
        {
            var (carte, guerre) = Carte();
            var lieu = guerre.Guerres?.Armees.FirstOrDefault(a => a.Identifiant == armee);
            Cadrer(carte, lieu != null ? carte.PositionSurLaCarte(lieu.Point, 0f).Value : carte.PositionSurLaCarte(capitale.Value, 0f).Value, DEMI_LOIN_KM);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            yield return carte.camera;
        }

        static (CarteDessinee, CarteDeLaGuerre) Carte()
        {
            if (maison == null) throw new InvalidOperationException("la partie n'est pas engagée : « 01-caserne » n'a pas réussi");
            var carte = Object.FindFirstObjectByType<CarteDessinee>(); var guerre = Object.FindFirstObjectByType<CarteDeLaGuerre>();
            if (carte == null || guerre == null || carte.Vue == null) throw new InvalidOperationException("la carte de la guerre n'est pas ouverte");
            return (carte, guerre);
        }
        static bool Dessinee(CarteDeLaGuerre guerre, Func<ArmeeLue, bool> etat)
        {
            var a = guerre.Guerres.Armees.FirstOrDefault(x => x.Identifiant == armee);
            return a != null && etat(a) && guerre.NombresDesArmees.Any(n => n != null && n.text == CarteDeLaGuerre.Nombre(a));
        }
        // Toute la largeur de la photo pour la carte, la vue posée sur `ici` (km locaux) avec `demi` km de demi-hauteur.
        static void Cadrer(CarteDessinee carte, Vector3 ici, float demi)
        {
            carte.camera.rect = new Rect(0, 0, 1, 1);
            carte.Vue.Changer(carte.camera.aspect); carte.Vue.Centrer(new Vector2(ici.x, ici.z), demi); carte.Vue.Poser(carte.camera, carte.transform);
        }
        internal static Task<Lecture<T>> Lire<T>(Func<Lecture<T>> lire) where T : class => Task.Run(lire);
        // `n` jours poussés au service, hors du fil de l'éditeur ; `tick` reçoit le tick que le service rend.
        internal static IEnumerator Pousser(int n, Action<long> tick = null)
        {
            string url = "http://127.0.0.1:" + PORT + "/tick?n=" + n;
            var appel = Task.Run(() =>
            {
                using (var http = new HttpClient { Timeout = DELAI }) using (var corps = new ByteArrayContent(new byte[0]))
                using (var reponse = http.PostAsync(url, corps).GetAwaiter().GetResult())
                    return ((int)reponse.StatusCode, reponse.Content.ReadAsStringAsync().GetAwaiter().GetResult());
            });
            for (var e = AttentesDeCapture.Attendre(appel, "POST " + url); e.MoveNext();) yield return null;
            var (statut, texte) = appel.Result;
            if (statut != 200) throw new InvalidOperationException("POST " + url + " a rendu " + statut + " : " + texte);
            tick?.Invoke((long)(double)LecteurJson.LireObjet(texte)["tick"]);
        }
    }
}
