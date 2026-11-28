using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Forge.Interface;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures
{
    // L'étape 1 jouée d'un trait contre le vrai service (avec l'IA : -forgeServiceIa), en 1920 × 1080, une image à chaque pas :
    //   00 à 04   les cinq planches de la carte politique à côté de l'atlas (`ScenarioCarteEtAtlas.Planche`), sur le monde frais ;
    //   10, 20, 30   le parcours du joueur pour la Navarre, la Guyenne et l'Émirat du Zab tour à tour, en treize pas chacun :
    //             01 l'accueil, sur un service relancé (un choix ne se défait pas) ; 02 la fiche du pays, cliqué sur la carte après l'avoir
    //             amené sous la souris d'un glisser et rapproché à la molette ; 03 « Commencer » ; 04 « Reprendre », la date avance ;
    //             05 la pause ; 06 un glisser ; 07 la molette jusqu'à la province du siège, ses lieux peints ; 08 à 12 les cinq modes de carte,
    //             la vue reculée sur le pays ; 13 « Ma capitale » ;
    //   40        un lieu qui change de pays, lui seul, sur un service relancé : la veille de la chute de la place, puis le jour de la prise
    //             (`PasDeLaPrise`), le chemin que le joueur ne joue pas encore à la souris faute d'armée à l'écran.
    // Tout passe par la souris : les boutons par un clic de pointeur (`GestesDeCapture.CliquerAuPointeur`), la terre par le chemin du clic
    // du cabinet, le glisser et la molette par le geste que `ParcoursDeCarte` joue avec la vraie souris (`ParcoursDeVue`).
    // Chaque pas échoue si un texte écrit à la place d'un pays un nom des listes de noms-1400.json (`TextesDeCapture`) ou celui d'une
    // dynastie ; si la date servie bouge entre l'ouverture et « Reprendre », ou n'avance pas après ; si le nom du pays diffère entre
    // l'accueil, la carte et la partie servie au cabinet ; si une légende datée ne dit pas la date de l'horloge ; si « Ma capitale » ne
    // pose pas la vue sur le siège que la fiche a dit ; et chaque pas exige l'état que le précédent a laissé. Le temps est remis en pause
    // après avoir avancé, pour que les légendes soient fixes sur les photos. Le tick est celui que le service sert, jamais écrit en dur.
    static class ScenarioDUnTrait
    {
        const string GROUPE = "etape-1-d-un-trait", PAUSE = "Pause / Reprendre";
        const int LARGEUR = 1920, HAUTEUR = 1080, IMAGES_DE_POSE = 4, IMAGES_DU_GLISSER = 12, CRANS_MAX = 60, ESSAIS_DU_GLISSER = 8;
        const float DEMI_POUR_DESIGNER_KM = 400f, DEMI_DES_MODES_KM = 450f, TRAIT_MAX_PX = 700f, ARRIVE_PX = 40f, PAS_DE_RECHERCHE_PX = 16f, RAYON_DE_RECHERCHE_PX = 320f;
        const float TOLERANCE_DU_SOL_KM = 1f, TOLERANCE_DU_CENTRE_KM = 5f, HAUT_DU_BANDEAU = 124f / 1080f;
        const double STABLE_S = 2.5; // les textes du cabinet sont récrits une image après la lecture
        // Les traits essayés pour le glisser, la carte tirée vers le bas d'abord : la vue posée sur un siège du sud est déjà au bord de la carte.
        static readonly Vector2[] GLISSERS = { new Vector2(420, -180), new Vector2(-420, -180), new Vector2(420, 180), new Vector2(-420, 180) };

        enum Etape { Accueil, Fiche, Commencer, Reprendre, Pause, Glisser, Province, Politique, Relief, Population, Vivres, Guerres, MaCapitale }

        // La partie d'un pays, de son accueil à sa capitale : ce qu'un pas laisse au suivant.
        sealed class Partie { public string Nom, Pays, Maison, NomDeLAccueil; public long TickOuvert = -1; public long? Siege; public Etape Faite; public readonly ParcoursDeVue Geste = new ParcoursDeVue(); }
        static Partie enCours;

        [ScenarioDeCapture(GROUPE, "00-planche-europe", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator P0(Camera c) => Planche("europe", true);
        [ScenarioDeCapture(GROUPE, "01-planche-france-et-iles", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator P1(Camera c) => Planche("france-et-iles", false);
        [ScenarioDeCapture(GROUPE, "02-planche-empire", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator P2(Camera c) => Planche("empire", false);
        [ScenarioDeCapture(GROUPE, "03-planche-italie", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator P3(Camera c) => Planche("italie", false);
        [ScenarioDeCapture(GROUPE, "04-planche-balkans", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator P4(Camera c) => Planche("balkans-et-orient", false);

        const string NAVARRE = "Navarre", GUYENNE = "Guyenne", ZAB = "Émirat du Zab";
        [ScenarioDeCapture(GROUPE, "10-navarre-01-accueil", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator N01(Camera c) => Pas(NAVARRE, Etape.Accueil);
        [ScenarioDeCapture(GROUPE, "10-navarre-02-fiche", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator N02(Camera c) => Pas(NAVARRE, Etape.Fiche);
        [ScenarioDeCapture(GROUPE, "10-navarre-03-commencer", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator N03(Camera c) => Pas(NAVARRE, Etape.Commencer);
        [ScenarioDeCapture(GROUPE, "10-navarre-04-reprendre", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator N04(Camera c) => Pas(NAVARRE, Etape.Reprendre);
        [ScenarioDeCapture(GROUPE, "10-navarre-05-pause", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator N05(Camera c) => Pas(NAVARRE, Etape.Pause);
        [ScenarioDeCapture(GROUPE, "10-navarre-06-glisser", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator N06(Camera c) => Pas(NAVARRE, Etape.Glisser);
        [ScenarioDeCapture(GROUPE, "10-navarre-07-province", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator N07(Camera c) => Pas(NAVARRE, Etape.Province);
        [ScenarioDeCapture(GROUPE, "10-navarre-08-politique", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator N08(Camera c) => Pas(NAVARRE, Etape.Politique);
        [ScenarioDeCapture(GROUPE, "10-navarre-09-relief", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator N09(Camera c) => Pas(NAVARRE, Etape.Relief);
        [ScenarioDeCapture(GROUPE, "10-navarre-10-population", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator N10(Camera c) => Pas(NAVARRE, Etape.Population);
        [ScenarioDeCapture(GROUPE, "10-navarre-11-vivres", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator N11(Camera c) => Pas(NAVARRE, Etape.Vivres);
        [ScenarioDeCapture(GROUPE, "10-navarre-12-guerres", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator N12(Camera c) => Pas(NAVARRE, Etape.Guerres);
        [ScenarioDeCapture(GROUPE, "10-navarre-13-ma-capitale", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator N13(Camera c) => Pas(NAVARRE, Etape.MaCapitale);
        [ScenarioDeCapture(GROUPE, "20-guyenne-01-accueil", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator G01(Camera c) => Pas(GUYENNE, Etape.Accueil);
        [ScenarioDeCapture(GROUPE, "20-guyenne-02-fiche", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator G02(Camera c) => Pas(GUYENNE, Etape.Fiche);
        [ScenarioDeCapture(GROUPE, "20-guyenne-03-commencer", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator G03(Camera c) => Pas(GUYENNE, Etape.Commencer);
        [ScenarioDeCapture(GROUPE, "20-guyenne-04-reprendre", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator G04(Camera c) => Pas(GUYENNE, Etape.Reprendre);
        [ScenarioDeCapture(GROUPE, "20-guyenne-05-pause", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator G05(Camera c) => Pas(GUYENNE, Etape.Pause);
        [ScenarioDeCapture(GROUPE, "20-guyenne-06-glisser", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator G06(Camera c) => Pas(GUYENNE, Etape.Glisser);
        [ScenarioDeCapture(GROUPE, "20-guyenne-07-province", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator G07(Camera c) => Pas(GUYENNE, Etape.Province);
        [ScenarioDeCapture(GROUPE, "20-guyenne-08-politique", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator G08(Camera c) => Pas(GUYENNE, Etape.Politique);
        [ScenarioDeCapture(GROUPE, "20-guyenne-09-relief", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator G09(Camera c) => Pas(GUYENNE, Etape.Relief);
        [ScenarioDeCapture(GROUPE, "20-guyenne-10-population", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator G10(Camera c) => Pas(GUYENNE, Etape.Population);
        [ScenarioDeCapture(GROUPE, "20-guyenne-11-vivres", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator G11(Camera c) => Pas(GUYENNE, Etape.Vivres);
        [ScenarioDeCapture(GROUPE, "20-guyenne-12-guerres", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator G12(Camera c) => Pas(GUYENNE, Etape.Guerres);
        [ScenarioDeCapture(GROUPE, "20-guyenne-13-ma-capitale", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator G13(Camera c) => Pas(GUYENNE, Etape.MaCapitale);
        [ScenarioDeCapture(GROUPE, "30-zab-01-accueil", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator Z01(Camera c) => Pas(ZAB, Etape.Accueil);
        [ScenarioDeCapture(GROUPE, "30-zab-02-fiche", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator Z02(Camera c) => Pas(ZAB, Etape.Fiche);
        [ScenarioDeCapture(GROUPE, "30-zab-03-commencer", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator Z03(Camera c) => Pas(ZAB, Etape.Commencer);
        [ScenarioDeCapture(GROUPE, "30-zab-04-reprendre", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator Z04(Camera c) => Pas(ZAB, Etape.Reprendre);
        [ScenarioDeCapture(GROUPE, "30-zab-05-pause", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator Z05(Camera c) => Pas(ZAB, Etape.Pause);
        [ScenarioDeCapture(GROUPE, "30-zab-06-glisser", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator Z06(Camera c) => Pas(ZAB, Etape.Glisser);
        [ScenarioDeCapture(GROUPE, "30-zab-07-province", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator Z07(Camera c) => Pas(ZAB, Etape.Province);
        [ScenarioDeCapture(GROUPE, "30-zab-08-politique", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator Z08(Camera c) => Pas(ZAB, Etape.Politique);
        [ScenarioDeCapture(GROUPE, "30-zab-09-relief", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator Z09(Camera c) => Pas(ZAB, Etape.Relief);
        [ScenarioDeCapture(GROUPE, "30-zab-10-population", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator Z10(Camera c) => Pas(ZAB, Etape.Population);
        [ScenarioDeCapture(GROUPE, "30-zab-11-vivres", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator Z11(Camera c) => Pas(ZAB, Etape.Vivres);
        [ScenarioDeCapture(GROUPE, "30-zab-12-guerres", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator Z12(Camera c) => Pas(ZAB, Etape.Guerres);
        [ScenarioDeCapture(GROUPE, "30-zab-13-ma-capitale", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator Z13(Camera c) => Pas(ZAB, Etape.MaCapitale);
        [ScenarioDeCapture(GROUPE, "40-prise-1-depart", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator L1(Camera c) => PasDeLaPrise(1);
        [ScenarioDeCapture(GROUPE, "40-prise-2-caserne", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator L2(Camera c) => PasDeLaPrise(2);
        [ScenarioDeCapture(GROUPE, "40-prise-3-siege", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator L3(Camera c) => PasDeLaPrise(3);
        [ScenarioDeCapture(GROUPE, "40-prise-4-chute-mesuree", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator L4(Camera c) => PasDeLaPrise(4);
        [ScenarioDeCapture(GROUPE, "40-prise-5-la-veille", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator L5(Camera c) => PasDeLaPrise(5);
        [ScenarioDeCapture(GROUPE, "40-prise-6-la-prise", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator L6(Camera c) => PasDeLaPrise(6);

        // Une planche de l'atlas ; la première ouvre la carte, celle du monde frais, et attend ses couleurs et les noms de l'atlas.
        static IEnumerator Planche(string cadre, bool ouvrir)
        {
            if (ouvrir)
            {
                var o = ScenarioAccueil.OuvrirLaCarte(); while (o.MoveNext()) yield return o.Current;
                var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
                for (var a = AttentesDeCapture.Jusqua(() => guerre.Couleurs != null && carte.GetComponent<AtlasDeCarte>()?.Ecriture != null, () => "couleurs des pays ou noms de l'atlas non prêts"); a.MoveNext();) yield return null;
                TextesDeCapture.Verifier(guerre, cabinet, "planche " + cadre); ScenarioAccueil.VerifierLesNoms(guerre);
                var s = ScenarioAccueil.Stabiliser(cabinet); while (s.MoveNext()) yield return null;
            }
            var p = ScenarioCarteEtAtlas.Planche(cadre); while (p.MoveNext()) yield return p.Current;
        }

        // Un pas du parcours de `nom` : le geste de l'étape, puis ce que tout pas vérifie ; la photo est celle de la caméra de la carte.
        static IEnumerator Pas(string nom, Etape etape)
        {
            if (etape != Etape.Accueil && (enCours == null || enCours.Nom != nom || enCours.Faite != etape - 1))
                throw Faux(nom + ", " + etape + " : le pas d'avant n'a pas réussi (dernier fait : " + (enCours == null ? "aucun" : enCours.Nom + ", " + enCours.Faite) + ")");
            IEnumerator geste;
            switch (etape)
            {
                case Etape.Accueil: geste = Accueil(nom); break;
                case Etape.Fiche: geste = Fiche(); break;
                case Etape.Commencer: geste = Commencer(); break;
                case Etape.Reprendre: geste = Reprendre(); break;
                case Etape.Pause: geste = Pause(); break;
                case Etape.Glisser: geste = Glisser(); break;
                case Etape.Province: geste = Province(); break;
                case Etape.Politique: geste = Mode(ModeDeCarte.Politique, true); break;
                case Etape.Relief: geste = Mode(ModeDeCarte.Relief, false); break;
                case Etape.Population: geste = Mode(ModeDeCarte.Population, false); break;
                case Etape.Vivres: geste = Mode(ModeDeCarte.Vivres, false); break;
                case Etape.Guerres: geste = Mode(ModeDeCarte.Guerres, false); break;
                default: geste = MaCapitale(); break;
            }
            while (geste.MoveNext()) yield return geste.Current;
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            TextesDeCapture.Verifier(guerre, cabinet, nom + ", " + etape); ScenarioAccueil.VerifierLesNoms(guerre);
            Poser(carte, cabinet, guerre);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            enCours.Faite = etape;
            var horloge = Horloge(carte);
            Debug.Log("CAPTURE d'un trait : " + nom + ", " + etape + " au tick " + horloge.Lue?.Tick + (horloge.EnPause ? " (en pause)" : "") + ", centre " + carte.Vue.Centre + ", demi " + carte.Vue.Demi.ToString("0.#", CultureInfo.InvariantCulture) + " km");
            yield return carte.camera;
        }

        // Le service relancé, la carte rouverte sur l'accueil, en pause au jour poussé.
        static IEnumerator Accueil(string nom)
        {
            var o = Rouvrir(); while (o.MoveNext()) yield return o.Current;
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            var horloge = Horloge(carte);
            for (var a = AttentesDeCapture.Jusqua(() => horloge.Lue != null && guerre.Couleurs != null, () => "horloge ou couleurs non servies : " + horloge.Absence); a.MoveNext();) yield return null;
            if (!horloge.EnPause) throw Faux(nom + " : le jeu ne s'ouvre pas en pause (" + horloge.Lue.JoursParSeconde + " jours par seconde)");
            if (horloge.Lue.Tick != Capture.JoursPousses) throw Faux(nom + " : l'horloge sert le tick " + horloge.Lue.Tick + " à l'ouverture, le service a été poussé à " + Capture.JoursPousses);
            enCours = new Partie { Nom = nom, TickOuvert = horloge.Lue.Tick, Faite = Etape.Accueil };            var s = ScenarioAccueil.Stabiliser(cabinet); while (s.MoveNext()) yield return null;
        }

        // Le service relancé et la carte rouverte, sa caméra rendant dans un écran de la taille de la photo.
        static IEnumerator Rouvrir()
        {
            Capture.RelancerLeService();
            var o = ScenarioAccueil.OuvrirLaCarte(); while (o.MoveNext()) yield return o.Current;
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            // Sans écran, la vue du jeu est petite : la caméra de la carte rend dans un écran de la taille de la photo, où tout se règle, les clics compris.
            if (carte.camera.targetTexture == null) carte.camera.targetTexture = new RenderTexture(LARGEUR, HAUTEUR, 24) { name = "Écran d'un trait" };
            carte.camera.aspect = (float)LARGEUR / HAUTEUR; carte.Vue.Changer(carte.camera.aspect); Poser(carte, cabinet, guerre);
            // La vraie souris ne lit rien : le scénario joue le même geste que `ParcoursDeCarte`.
            var parcours = carte.GetComponent<ParcoursDeCarte>(); if (parcours != null) parcours.automatique = true;
        }

        // Le pays amené sous la souris (glisser, molette), puis cliqué sur la carte : sa fiche s'ouvre dans l'accueil, « Commencer » actif.
        static IEnumerator Fiche()
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire(); var p = enCours;
            p.Pays = guerre.Terres.Pays.SingleOrDefault(x => x.Nom == p.Nom)?.Id ?? throw Faux("aucun pays servi ne s'appelle « " + p.Nom + " »");
            string maison = guerre.Terres.MaisonDuPays(p.Pays)?.Id;
            var jouable = cabinet.Partie.Jouables.Donnees.Fiches.FirstOrDefault(f => f.Id == maison);
            if (jouable == null) throw Faux(p.Nom + " ne peut pas commencer : sa maison « " + maison + " » n'est pas parmi les pays que le monde propose au joueur");
            long cible = jouable.Siege.CellId ?? guerre.Terres.Terres.First(t => t.Pays == p.Pays).CellId;
            // La part libre de l'écran : à gauche de l'accueil, sous le bandeau.
            Canvas.ForceUpdateCanvases();
            var coins = new Vector3[4]; cabinet.Accueil.Panneau.GetWorldCorners(coins);
            float bord = coins.Min(c => carte.camera.WorldToViewportPoint(c).x);
            var libre = Rect.MinMaxRect(LARGEUR * 0.03f, HAUTEUR * 0.05f, LARGEUR * (bord - 0.03f), HAUTEUR * (1f - HAUT_DU_BANDEAU - 0.05f));
            if (libre.width < TRAIT_MAX_PX) throw Faux("l'accueil ne laisse que " + libre.width + " px de carte libre");
            Vector2 vise = libre.center; Rect interieur = Rect.MinMaxRect(libre.xMin + libre.width / 4f, libre.yMin + libre.height / 4f, libre.xMax - libre.width / 4f, libre.yMax - libre.height / 4f);
            // Des traits de glisser vers le milieu de la part libre, jusqu'à ce que le siège tombe dans son cœur ; au bord de la carte, la vue
            // s'arrête où elle est bornée.
            Vector2? precedent = null;
            for (int essai = 0; ; essai++)
            {
                Vector2 ici = Ecran(carte, Centre(carte, cible)), trait = vise - ici;
                if (trait.magnitude <= ARRIVE_PX || interieur.Contains(ici)) break;
                if (precedent is Vector2 avant && (ici - avant).magnitude < ARRIVE_PX && libre.Contains(ici)) break; // la vue est bornée : le siège reste où il est
                precedent = ici;
                if (essai >= ESSAIS_DU_GLISSER) throw Faux(p.Nom + " : le siège reste à " + ici + " après " + essai + " glissers vers " + vise);
                trait = Vector2.ClampMagnitude(trait, TRAIT_MAX_PX);
                Vector2 de = vise - trait / 2f;
                var g = Glisser(carte, cabinet, guerre, de, de + trait, false); while (g.MoveNext()) yield return null;
            }
            // La molette sous le siège, jusqu'à voir le pays d'assez près pour le cliquer.
            for (int crans = 0; carte.Vue.Demi > DEMI_POUR_DESIGNER_KM; crans++)
            {
                if (crans >= CRANS_MAX) throw Faux(p.Nom + " : la molette ne rapproche pas la vue (demi " + carte.Vue.Demi + " km)");
                Molette(carte, cabinet, guerre, Ecran(carte, Centre(carte, cible)), 1f); yield return null;
            }
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            // Le point de l'écran, libre de l'interface, le plus près du siège, qui tombe sur une terre du pays : le clic du joueur.
            var fiche = carte.GetComponent<FicheDeCellule>() ?? throw Faux("pas de fiche de cellule sur la carte");
            Vector2 siege = Ecran(carte, Centre(carte, cible)); Vector2? clic = null; CelluleDeCarte sous = null;
            int n = Mathf.RoundToInt(RAYON_DE_RECHERCHE_PX / PAS_DE_RECHERCHE_PX);
            var ecarts = Enumerable.Range(-n, 2 * n + 1).SelectMany(i => Enumerable.Range(-n, 2 * n + 1).Select(j => new Vector2(i, j) * PAS_DE_RECHERCHE_PX)).OrderBy(v => v.sqrMagnitude).ThenBy(v => v.x).ThenBy(v => v.y);
            foreach (Vector2 ecart in ecarts)
            {
                var pt = siege + ecart;
                if (!libre.Contains(pt) || cabinet.HorsCarte(pt)) continue;
                fiche.Survoler(pt);
                if (fiche.Survolee != null && guerre.Terres.PaysDe(fiche.Survolee.CellId) == p.Pays) { clic = pt; sous = fiche.Survolee; break; }
            }
            if (clic == null) throw Faux(p.Nom + " : aucune de ses terres sous la souris autour du siège " + siege);
            fiche.Survoler(clic.Value);
            cabinet.Noter(clic.Value, true, false, false, sous);
            if (!cabinet.Noter(clic.Value, false, true, false, sous)) throw Faux(p.Nom + " : le clic en " + clic.Value + " sur la terre " + sous.CellId + " ne la garde pas");
            for (var a = AttentesDeCapture.Jusqua(() => cabinet.Accueil.TexteDuNom == p.Nom && cabinet.Accueil.Montree != null && cabinet.Accueil.Commencer.interactable
                && cabinet.Accueil.TexteDeLaFiche.StartsWith(p.Nom + " : ", StringComparison.Ordinal) && !cabinet.Accueil.TexteDeLaFiche.Contains("en lecture"),
                () => p.Nom + " ne peut pas commencer : fiche « " + cabinet.Accueil.TexteDuNom + " » « " + cabinet.Accueil.TexteDeLaFiche + " », « Commencer » " + (cabinet.Accueil.Commencer.interactable ? "actif" : "inactif")); a.MoveNext();) yield return null;
            p.Maison = cabinet.Accueil.Montree.Id; p.Siege = cabinet.Accueil.Montree.Siege.CellId; p.NomDeLAccueil = cabinet.Accueil.TexteDuNom;
            DateImmobile(carte, cabinet, "la fiche");
            Debug.Log("CAPTURE d'un trait : " + p.Nom + " cliqué en " + clic.Value + " sur la terre " + sous.CellId + " ; « " + cabinet.Accueil.TexteDeLaFiche.Replace("\n", " | ") + " »");
            var s = ScenarioAccueil.Stabiliser(cabinet); while (s.MoveNext()) yield return null;
        }

        static IEnumerator Commencer()
        {
            var (carte, cabinet, _) = ScenarioAccueil.Lire();
            // « Commencer » se grise le temps que la partie relise le monde : le joueur attend qu'il se rallume.
            for (var a = AttentesDeCapture.Jusqua(() => cabinet.Accueil.Commencer.interactable, () => "« Commencer » reste inactif : « " + cabinet.Accueil.TexteDeLEtat + " »"); a.MoveNext();) yield return null;
            GestesDeCapture.CliquerAuPointeur(carte.camera, cabinet.Accueil.Commencer);
            for (var a = AttentesDeCapture.Jusqua(() => cabinet.Partie.Recu?.Acceptee == true, () => "le choix de " + enCours.Nom + " n'est pas reçu : « " + (cabinet.Partie.Recu?.Erreur ?? cabinet.Partie.Recu?.Absence) + " »"); a.MoveNext();) yield return null;
            DateImmobile(carte, cabinet, "« Commencer »");
            var s = ScenarioAccueil.Stabiliser(cabinet); while (s.MoveNext()) yield return null;        }

        // « Reprendre » : jusque-là la date n'a pas bougé ; après, la maison est servie et la date avance.
        static IEnumerator Reprendre()
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire(); var horloge = Horloge(carte); var p = enCours;
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            DateImmobile(carte, cabinet, "« Reprendre »");
            GestesDeCapture.CliquerAuPointeur(carte.camera, Bouton(cabinet, PAUSE));
            for (var a = AttentesDeCapture.Jusqua(() => ScenarioAccueil.Servie(cabinet) == p.Maison && cabinet.Partie.Maison?.Presente == true && cabinet.Partie.Jouable != null && !cabinet.Accueil.Ouvert
                && horloge.Lue != null && !horloge.EnPause && horloge.Lue.Tick > p.TickOuvert && guerre.Terres.Tick > p.TickOuvert,
                () => "après « Reprendre » : maison « " + ScenarioAccueil.Servie(cabinet) + " », horloge au tick " + horloge.Lue?.Tick + " à " + horloge.Lue?.JoursParSeconde + " jours par seconde, terres du tick " + guerre.Terres.Tick); a.MoveNext();) yield return null;
            NomsDAccord(cabinet, guerre);
        }

        // La pause : la date s'arrête, et la carte, la partie et l'horloge disent le même jour.
        static IEnumerator Pause()
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire(); var horloge = Horloge(carte);
            GestesDeCapture.CliquerAuPointeur(carte.camera, Bouton(cabinet, PAUSE));
            for (var a = AttentesDeCapture.Jusqua(() => horloge.EnPause && guerre.Terres.Tick == horloge.Lue.Tick && cabinet.Partie.Monde.Donnees.Monde.Tick == horloge.Lue.Tick,
                () => "après la pause : horloge au tick " + horloge.Lue?.Tick + " (" + horloge.Lue?.JoursParSeconde + " j/s), terres du tick " + guerre.Terres.Tick + ", monde du tick " + cabinet.Partie.Monde.Donnees.Monde.Tick); a.MoveNext();) yield return null;
            long tick = horloge.Lue.Tick;
            var s = ScenarioAccueil.Stabiliser(cabinet); while (s.MoveNext()) yield return null;
            if (horloge.Lue.Tick != tick) throw Faux("la date bouge en pause : tick " + tick + " puis " + horloge.Lue.Tick);
        }

        // Un glisser sur la carte, qui laisse le siège à l'écran, libre de l'interface, pour la molette du pas suivant.
        static IEnumerator Glisser()
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            Vector2 milieu = new Vector2(LARGEUR / 2f, HAUTEUR / 2f), siege = Ecran(carte, Siege(carte, cabinet));
            Vector2? trait = GLISSERS.Select(v => (Vector2?)v).FirstOrDefault(v => !cabinet.HorsCarte(milieu) && !cabinet.HorsCarte(milieu + v.Value) && Dedans(siege + v.Value) && !cabinet.HorsCarte(siege + v.Value));
            if (trait == null) throw Faux(enCours.Nom + " : aucun glisser depuis le milieu de l'écran ne garde le siège " + siege + " libre de l'interface");
            Vector2 avant = carte.Vue.Centre;
            var g = Glisser(carte, cabinet, guerre, milieu, milieu + trait.Value, true); while (g.MoveNext()) yield return null;
            if ((carte.Vue.Centre - avant).magnitude < TOLERANCE_DU_CENTRE_KM) throw Faux("le glisser n'a pas déplacé la vue : " + avant + " → " + carte.Vue.Centre);
        }

        // La molette sous le siège jusqu'au plus près : le sol sous la souris ne bouge pas, et les lieux de la province sont peints.
        static IEnumerator Province()
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            Vector2 ici = Ecran(carte, Siege(carte, cabinet));
            if (!Dedans(ici) || cabinet.HorsCarte(ici)) throw Faux("le siège " + ici + " n'est pas sous une souris libre de l'interface");
            Vector3 avant = Sol(carte, ici) ?? throw Faux("aucun sol sous le siège " + ici);
            for (int crans = 0; carte.Vue.Demi > VueDeCarte.DEMI_MIN_KM + 1e-3f; crans++)
            {
                if (crans >= CRANS_MAX) throw Faux("la molette n'atteint pas la province : demi " + carte.Vue.Demi + " km");
                Molette(carte, cabinet, guerre, ici, 1f); yield return null;
            }
            Vector3 apres = Sol(carte, ici) ?? throw Faux("aucun sol sous la souris au plus près");
            if (Vector2.Distance(new Vector2(avant.x, avant.z), new Vector2(apres.x, apres.z)) > TOLERANCE_DU_SOL_KM) throw Faux("la molette n'a pas gardé le sol sous la souris : " + avant + " → " + apres);
            var lieux = carte.GetComponent<LieuxDeCarte>() ?? throw Faux("pas de lieux sur la carte");
            for (var a = AttentesDeCapture.Jusqua(() => lieux.Peint && lieux.TexteLegende.Length > LieuxDeCarte.ENTETE.Length, () => "lieux peints " + lieux.Peint + ", lecture en vol " + lieux.LectureEnVol); a.MoveNext();) yield return null;
        }

        // Un mode choisi d'un clic sur son bouton : lui seul enfoncé, la caméra immobile, et une légende datée du jour de l'horloge.
        // Avant le premier, la molette recule sur le pays.
        static IEnumerator Mode(ModeDeCarte mode, bool reculer)
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire(); var horloge = Horloge(carte);
            var calques = carte.GetComponent<CalquesCarte>() ?? throw Faux("pas de calques sur la carte");
            if (reculer)
                for (int crans = 0; carte.Vue.Demi < DEMI_DES_MODES_KM; crans++)
                {
                    if (crans >= CRANS_MAX) throw Faux("la molette ne recule pas : demi " + carte.Vue.Demi + " km");
                    Molette(carte, cabinet, guerre, new Vector2(LARGEUR / 2f, HAUTEUR / 2f), -1f); yield return null;
                }
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            Vector2 centre = carte.Vue.Centre; float demi = carte.Vue.Demi;
            GestesDeCapture.CliquerAuPointeur(carte.camera, calques.BoutonDu(mode));
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            if (calques.Mode != mode) throw Faux("le clic sur « " + mode + " » ne change pas le mode : " + calques.Mode);
            string enfonces = string.Join(", ", ((ModeDeCarte[])Enum.GetValues(typeof(ModeDeCarte))).Where(calques.Enfonce));
            if (enfonces != mode.ToString()) throw Faux("boutons enfoncés : « " + enfonces + " » pour le mode " + mode);
            if (carte.Vue.Centre != centre || carte.Vue.Demi != demi) throw Faux("choisir « " + mode + " » a bougé la vue");
            string Texte() => calques.Legende.GetComponentInParent<Infobulle>().Phrase;
            bool Indisponible() => Texte().StartsWith("Mode ", StringComparison.Ordinal) || Texte().StartsWith("Pays indisponibles", StringComparison.Ordinal) || Texte().StartsWith(CalquesCarte.COUPEE, StringComparison.Ordinal);
            string jour = TexteDuMonde.Date(horloge.Lue.Date);
            bool Datee() => mode == ModeDeCarte.Relief || Texte().Contains(jour) || mode == ModeDeCarte.Guerres && calques.Legende.text == BelligerantsDesPays.AUCUNE_ARMEE;
            for (var a = AttentesDeCapture.Jusqua(() => !Indisponible() && Datee(), () => "légende du mode " + mode + " : « " + Texte() + " », l'horloge dit « " + jour + " »"); a.MoveNext();) yield return null;
            if (!horloge.EnPause || TexteDuMonde.Date(horloge.Lue.Date) != jour) throw Faux("la date a bougé pendant le mode " + mode + " : « " + jour + " » puis « " + TexteDuMonde.Date(horloge.Lue.Date) + " »");
            string avant = calques.Legende.text + "|" + Texte(); double depuis = Time.realtimeSinceStartupAsDouble, fin = depuis + 20;
            while (Time.realtimeSinceStartupAsDouble - depuis < STABLE_S && Time.realtimeSinceStartupAsDouble < fin)
            {
                yield return null; string maintenant = calques.Legende.text + "|" + Texte();
                if (maintenant != avant) { avant = maintenant; depuis = Time.realtimeSinceStartupAsDouble; }
            }
            Debug.Log("CAPTURE d'un trait : " + enCours.Nom + ", mode " + mode + " ; « " + Texte().Replace("\n", " | ") + " »");
        }

        // La carte politique de nouveau, puis « Ma capitale » : la vue se pose sur le siège que la fiche a dit.
        static IEnumerator MaCapitale()
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire(); var calques = carte.GetComponent<CalquesCarte>();
            GestesDeCapture.CliquerAuPointeur(carte.camera, calques.BoutonDu(ModeDeCarte.Politique));
            for (var a = AttentesDeCapture.Jusqua(() => calques.Mode == ModeDeCarte.Politique, () => "le mode Politique ne revient pas : " + calques.Mode); a.MoveNext();) yield return null;
            GestesDeCapture.CliquerAuPointeur(carte.camera, Bouton(cabinet, CabinetDeCarte.CAPITALE));
            Poser(carte, cabinet, guerre);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            var siege = cabinet.Partie.Maison.Donnees.Siege;
            if (siege.CellId != enCours.Siege) throw Faux("le siège servi (" + siege.CellId + ") n'est pas celui que la fiche a dit (" + enCours.Siege + ")");
            Vector3 ici = Siege(carte, cabinet); Vector3 vu = carte.camera.WorldToViewportPoint(carte.transform.TransformPoint(ici));
            // La vue vise le siège autant que les bords de la carte le permettent : il tombe au milieu de l'image en largeur, près du milieu en hauteur.
            if (Mathf.Abs(carte.Vue.Centre.x - ici.x) > TOLERANCE_DU_CENTRE_KM || vu.z <= 0f || Mathf.Abs(vu.x - 0.5f) > 0.1f || Mathf.Abs(vu.y - 0.5f) > 0.25f)
                throw Faux("« Ma capitale » ne pose pas la vue sur " + siege.Nom + " : centre " + carte.Vue.Centre + " pour " + new Vector2(ici.x, ici.z) + ", à l'image " + vu);
            NomsDAccord(cabinet, guerre);
            var s = ScenarioAccueil.Stabiliser(cabinet); while (s.MoveNext()) yield return null;
        }

        // Le geste de la souris qui glisse de `de` à `a` (pixels), bouton tenu, en `IMAGES_DU_GLISSER` images. Avec `exiger`, le sol saisi
        // doit être resté sous elle : hors d'un bord de la carte, où la vue s'arrête, c'est la promesse du geste.
        static IEnumerator Glisser(CarteDessinee carte, CabinetDeCarte cabinet, CarteDeLaGuerre guerre, Vector2 de, Vector2 a, bool exiger)
        {
            if (cabinet.HorsCarte(de)) throw Faux("le glisser commence sur l'interface en " + de);
            var geste = enCours.Geste;
            geste.Pas(carte, de, true, true, 0f); Poser(carte, cabinet, guerre);
            Vector3 point = geste.Saisi ?? throw Faux("le bouton enfoncé en " + de + " ne saisit aucun point de la carte");
            for (int i = 1; i <= IMAGES_DU_GLISSER; i++) { yield return null; geste.Pas(carte, Vector2.Lerp(de, a, (float)i / IMAGES_DU_GLISSER), false, true, 0f); Poser(carte, cabinet, guerre); }
            yield return null; geste.Pas(carte, a, false, false, 0f); Poser(carte, cabinet, guerre);
            yield return null;
            if (!exiger) yield break;
            Vector3 sous = Sol(carte, a) ?? new Vector3(float.NaN, 0f, float.NaN); Vector2 plat = carte.Vue.PointSous(carte.camera.ScreenToViewportPoint(a), point.y);
            float ecart = Mathf.Min(Vector2.Distance(new Vector2(sous.x, sous.z), new Vector2(point.x, point.z)), Vector2.Distance(plat, new Vector2(point.x, point.z)));
            if (!(ecart <= TOLERANCE_DU_SOL_KM + carte.Vue.Demi * 0.01f)) throw Faux("le point saisi en " + de + " n'est pas resté sous la souris en " + a + " : " + ecart.ToString("0.#", CultureInfo.InvariantCulture) + " km d'écart");
        }

        // Un cran de molette (positif pour s'approcher) sous la souris en `ici`, que l'interface ne couvre pas.
        static void Molette(CarteDessinee carte, CabinetDeCarte cabinet, CarteDeLaGuerre guerre, Vector2 ici, float crans)
        {
            if (cabinet.HorsCarte(ici)) throw Faux("la molette tourne sur l'interface en " + ici);
            enCours.Geste.Pas(carte, ici, false, false, crans); Poser(carte, cabinet, guerre);
        }

        // Rien n'a bougé depuis l'ouverture : en pause, au même jour, la partie au même jour.
        static void DateImmobile(CarteDessinee carte, CabinetDeCarte cabinet, string avant)
        {
            var horloge = Horloge(carte); long monde = cabinet.Partie.Monde.Donnees.Monde.Tick;
            if (!horloge.EnPause || horloge.Lue.Tick != enCours.TickOuvert || monde != enCours.TickOuvert)
                throw Faux("la date a bougé avant " + avant + " : ouverte au tick " + enCours.TickOuvert + ", l'horloge sert le tick " + horloge.Lue?.Tick + " à " + horloge.Lue?.JoursParSeconde + " jours par seconde, la partie le tick " + monde);
        }

        // Le même nom de pays dans l'accueil, sur la carte (le pays des terres de la maison et son nom écrit) et dans la partie servie au cabinet.
        static void NomsDAccord(CabinetDeCarte cabinet, CarteDeLaGuerre guerre)
        {
            var p = enCours; string pays = guerre.PaysDeLaMaison(p.Maison), carte = guerre.Terres.NomDuPays(pays), partie = cabinet.Partie.Jouable?.Pays?.Nom;
            bool ecrit = guerre.NomsDesPays.Any(n => n.Pays == pays && n.Texte == carte);
            if (p.NomDeLAccueil != p.Nom || carte != p.Nom || partie != p.Nom || !ecrit)
                throw Faux("le pays ne porte pas le même nom partout : accueil « " + p.NomDeLAccueil + " », carte « " + carte + " »" + (ecrit ? "" : " (non écrit)") + ", partie « " + partie + " », attendu « " + p.Nom + " »");
        }

        // La prise d'un lieu, jouée par les intentions du joueur (le geste n'a pas encore d'écran : il n'y a pas d'armée à la souris), sur
        // un service relancé : 1 le départ choisi et la caserne commandée ; 2 la caserne achevée ; 3 l'armée levée, la guerre déclarée, la
        // marche jusqu'à la place et le siège ; 4 les jours par paquets jusqu'à la chute, dont `/guerres` sert le jour ; 5 le service relancé
        // et les mêmes intentions rejouées aux mêmes jours (le monde est déterministe) jusqu'à la veille de ce jour ; 6 un jour de plus : la
        // prise, au même jour et des mêmes lieux que la première fois. Entre la veille et la prise, les lieux pris prennent la teinte du pays
        // du preneur, et aucun autre lieu de l'image ne change de teinte, hors ceux du joueur dont l'alerte des départs a basculé ce jour-là.
        sealed class Prise { public int Fait; public string Maison; public long Capitale, Tick; public long Armee = -1; public PriseLue Mesuree;
            public readonly List<(long tick, string[] intentions)> Journal = new List<(long, string[])>();
            public Dictionary<(long, long), Color32> Veille; public HashSet<(long, long)> AlertesDeLaVeille; }
        static Prise prise;        const float DEMI_DE_LA_PRISE_KM = 220f; const int IMAGES_DE_PEINTURE = 3;

        static IEnumerator PasDeLaPrise(int n)
        {
            if (n > 1 && (prise == null || prise.Fait != n - 1)) throw Faux("prise, pas " + n + " : le pas d'avant n'a pas réussi");
            IEnumerator geste = n == 1 ? Depart() : n == 2 ? Caserne() : n == 3 ? AuSiege() : n == 4 ? Chute() : n == 5 ? LaVeille() : LaPrise();
            while (geste.MoveNext()) yield return geste.Current;
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            TextesDeCapture.Verifier(guerre, cabinet, "prise, pas " + n); ScenarioAccueil.VerifierLesNoms(guerre);
            prise.Fait = n;
            Debug.Log("CAPTURE d'un trait : prise, pas " + n + " au tick " + prise.Tick + ", " + prise.Maison + (prise.Armee >= 0 ? ", armée " + prise.Armee : ""));
            Poser(carte, cabinet, guerre);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            yield return carte.camera;
        }

        // Les intentions du joueur déposées au tick servi, et gardées pour être rejouées au même tick.
        static void Deposer(int port, params string[] intentions)
        {
            GestesDeCapture.Deposer(port, intentions);
            prise.Journal.Add((prise.Tick, intentions));
        }

        static IEnumerator Depart()
        {
            prise = new Prise { Tick = Capture.JoursPousses };
            var o = Rouvrir(); while (o.MoveNext()) yield return o.Current;
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            Deposer(carte.port, "{\"type\":\"choisir_depart\",\"seigneurie\":" + ScenarioGuerre.SEIGNEURIE + "}");
            for (var e = ScenarioGuerre.Pousser(1, t => prise.Tick = t); e.MoveNext();) yield return null;
            for (var a = AttentesDeCapture.Jusqua(() => ScenarioAccueil.Servie(cabinet) != null && cabinet.Partie.Maison?.Presente == true && !cabinet.Accueil.Ouvert,
                () => "aucune maison du joueur servie après le choix de la seigneurie " + ScenarioGuerre.SEIGNEURIE); a.MoveNext();) yield return null;
            prise.Maison = ScenarioAccueil.Servie(cabinet);
            prise.Capitale = cabinet.Partie.Maison.Donnees.Siege.CellId ?? throw Faux("la maison " + prise.Maison + " n'a pas de siège servi");
            Deposer(carte.port, "{\"type\":\"batir_dans_une_province\",\"maison\":\"" + prise.Maison + "\",\"cell\":" + prise.Capitale.ToString(CultureInfo.InvariantCulture) + ",\"nature\":\"caserne\"}");
            Viser(carte, cabinet, guerre, Siege(carte, cabinet));
        }

        // Les jours passent par paquets jusqu'à ce que le devis dise la levée ouverte.
        static IEnumerator Caserne()
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            for (int jours = 0; ; jours += ScenarioGuerre.PAQUET)
            {
                if (jours > ScenarioGuerre.JOURS_MAX_CASERNE) throw Faux("la caserne n'est pas achevée en " + ScenarioGuerre.JOURS_MAX_CASERNE + " jours");
                for (var e = ScenarioGuerre.Pousser(ScenarioGuerre.PAQUET, t => prise.Tick = t); e.MoveNext();) yield return null;
                var devis = ScenarioGuerre.Lire(() => { using (var c = new ClientGuerre(carte.port, ScenarioGuerre.DELAI)) return c.LireOrdres(prise.Maison, null); });
                for (var e = AttentesDeCapture.Attendre(devis, "lecture du devis"); e.MoveNext();) yield return null;
                if (devis.Result.Presente && devis.Result.Donnees.Levee.Refus == null) break;
            }
            Viser(carte, cabinet, guerre, Siege(carte, cabinet));
        }

        // L'armée levée et la guerre déclarée au maître de la place, la marche jusqu'à elle, puis le siège.
        static IEnumerator AuSiege()
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            var devis = ScenarioGuerre.Lire(() => { using (var c = new ClientGuerre(carte.port, ScenarioGuerre.DELAI)) return c.LireOrdres(prise.Maison, ScenarioGuerre.PLACE); });
            for (var e = AttentesDeCapture.Attendre(devis, "lecture du devis"); e.MoveNext();) yield return null;
            if (!devis.Result.Presente) throw Faux("devis absent : " + devis.Result.Absence);
            var levee = devis.Result.Donnees.Levee; var cible = devis.Result.Donnees.Cible;
            if (cible?.Maitre == null || cible.RefusDeDeclaration != null) throw Faux("la place " + ScenarioGuerre.PLACE + " ne se déclare plus contre " + cible?.Maitre + " : " + cible?.RefusDeDeclaration);
            long hommes = IntentionsDeGuerre.Maximum(levee);
            long vivres = (long)Math.Min(levee.GrainLibreKg * ScenarioGuerre.PART_DU_GRAIN, hommes * levee.RationKgParHommeParJour * ScenarioGuerre.JOURS_DE_VIVRES);
            Deposer(carte.port, IntentionsDeGuerre.Lever(prise.Maison, IntentionsDeGuerre.Repartir(levee, hommes), vivres), IntentionsDeGuerre.Declarer(prise.Maison, cible.Maitre));
            for (var e = ScenarioGuerre.Pousser(1, t => prise.Tick = t); e.MoveNext();) yield return null;
            var guerres = ScenarioGuerre.Lire(() => { using (var c = new ClientGuerre(carte.port, ScenarioGuerre.DELAI)) return c.LireGuerres(); });
            for (var e = AttentesDeCapture.Attendre(guerres, "lecture des guerres"); e.MoveNext();) yield return null;
            var levees = guerres.Result.Presente ? guerres.Result.Donnees.Armees.Where(a => a.Maison == prise.Maison).ToList() : null;
            if (levees == null || levees.Count != 1) throw Faux("l'armée levée n'est pas servie : " + (guerres.Result.Absence ?? levees.Count + " armées"));
            prise.Armee = levees[0].Identifiant;
            Deposer(carte.port, IntentionsDeGuerre.Marcher(prise.Maison, prise.Armee, ScenarioGuerre.PLACE));
            for (int jours = 0; ; jours += ScenarioGuerre.PAQUET)
            {
                if (jours > ScenarioGuerre.JOURS_MAX_MARCHE) throw Faux("l'armée n'est pas arrivée devant la place en " + ScenarioGuerre.JOURS_MAX_MARCHE + " jours");
                var lues = ScenarioGuerre.Lire(() => { using (var c = new ClientGuerre(carte.port, ScenarioGuerre.DELAI)) return c.LireGuerres(); });
                for (var e = AttentesDeCapture.Attendre(lues, "lecture des guerres"); e.MoveNext();) yield return null;
                var a = lues.Result.Presente ? lues.Result.Donnees.Armees.FirstOrDefault(x => x.Identifiant == prise.Armee) : null;
                if (a == null) throw Faux("l'armée n'est plus servie : " + lues.Result.Absence);
                if (a.Destination == null && a.CellId == ScenarioGuerre.PLACE) break;
                for (var e = ScenarioGuerre.Pousser(ScenarioGuerre.PAQUET, t => prise.Tick = t); e.MoveNext();) yield return null;
            }
            Deposer(carte.port, IntentionsDeGuerre.Assieger(prise.Maison, prise.Armee));
            for (var e = ScenarioGuerre.Pousser(1, t => prise.Tick = t); e.MoveNext();) yield return null;
            Viser(carte, cabinet, guerre, Centre(carte, ScenarioGuerre.PLACE));
            for (var a = AttentesDeCapture.Jusqua(() => Relire(guerre) && guerre.Guerres.Armees.Any(x => x.Identifiant == prise.Armee && x.Siege == ScenarioGuerre.PLACE),
                () => "l'armée n'est pas servie au siège de " + ScenarioGuerre.PLACE + " au tick " + prise.Tick); a.MoveNext();) yield return null;
        }

        // Les jours par paquets jusqu'à la chute de la place : son jour et ses lieux, tels que `/guerres` les sert.
        static IEnumerator Chute()
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            for (int jours = 0; prise.Mesuree == null; jours += ScenarioGuerre.PAQUET)
            {
                if (jours > ScenarioGuerre.JOURS_MAX_SIEGE) throw Faux("la place n'est pas tombée en " + ScenarioGuerre.JOURS_MAX_SIEGE + " jours de siège");
                for (var e = ScenarioGuerre.Pousser(ScenarioGuerre.PAQUET, t => prise.Tick = t); e.MoveNext();) yield return null;
                var lues = ScenarioGuerre.Lire(() => { using (var c = new ClientGuerre(carte.port, ScenarioGuerre.DELAI)) return c.LireGuerres(); });
                for (var e = AttentesDeCapture.Attendre(lues, "lecture des guerres"); e.MoveNext();) yield return null;
                if (lues.Result.Presente) prise.Mesuree = lues.Result.Donnees.Prises.FirstOrDefault(p => p.CellId == ScenarioGuerre.PLACE && p.A == prise.Maison);
            }
            for (var a = AttentesDeCapture.Jusqua(() => Relire(guerre), () => "carte non relue au tick " + prise.Tick); a.MoveNext();) yield return null;
            Debug.Log("CAPTURE d'un trait : la place " + ScenarioGuerre.PLACE + " tombe au tick " + prise.Mesuree.Tick + " (rangs " + string.Join(", ", prise.Mesuree.Rangs) + ", de " + prise.Mesuree.De + " à " + prise.Mesuree.A + ")");
        }

        // Le service relancé, les intentions rejouées à leurs jours, puis les jours poussés d'un trait jusqu'à la veille de la chute.
        static IEnumerator LaVeille()
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            Capture.RelancerLeService(); prise.Tick = Capture.JoursPousses;
            foreach (var (tick, intentions) in prise.Journal)
            {
                if (tick > prise.Tick) for (var e = ScenarioGuerre.Pousser((int)(tick - prise.Tick), t => prise.Tick = t); e.MoveNext();) yield return null;
                if (prise.Tick != tick) throw Faux("le service rejoué est au tick " + prise.Tick + ", l'intention était déposée au tick " + tick);
                GestesDeCapture.Deposer(carte.port, intentions);
            }
            // Une prise datée du tick T se joue pendant le jour qui mène le service de T à T + 1 : la veille est le tick servi T.
            long veille = prise.Mesuree.Tick;
            if (veille > prise.Tick) for (var e = ScenarioGuerre.Pousser((int)(veille - prise.Tick), t => prise.Tick = t); e.MoveNext();) yield return null;
            for (var a = AttentesDeCapture.Jusqua(() => Relire(guerre), () => "carte non relue au tick " + prise.Tick); a.MoveNext();) yield return null;
            if (guerre.Guerres.Prises.Any(p => p.CellId == ScenarioGuerre.PLACE)) throw Faux("la place est déjà prise la veille, au tick " + prise.Tick + " du monde rejoué");
            if (!guerre.Guerres.Armees.Any(x => x.Maison == prise.Maison && x.Siege == ScenarioGuerre.PLACE)) throw Faux("le monde rejoué n'a pas l'armée du joueur au siège de " + ScenarioGuerre.PLACE + " au tick " + prise.Tick);
            for (int i = 0; i < IMAGES_DE_PEINTURE; i++) yield return null;
            prise.Veille = Releve(carte); prise.AlertesDeLaVeille = new HashSet<(long, long)>(carte.GetComponent<LieuxDeCarte>().EnAlerte);
            if (prise.Veille.Count == 0) throw Faux("aucun lieu dessiné dans l'image de la veille");        }

        // Un jour de plus : la place tombe au jour mesuré, des mêmes lieux ; ces lieux seuls ont changé de teinte depuis la veille.
        static IEnumerator LaPrise()
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            for (var e = ScenarioGuerre.Pousser(1, t => prise.Tick = t); e.MoveNext();) yield return null;
            for (var a = AttentesDeCapture.Jusqua(() => Relire(guerre), () => "carte non relue au tick " + prise.Tick); a.MoveNext();) yield return null;
            var rejouee = guerre.Guerres.Prises.FirstOrDefault(p => p.CellId == ScenarioGuerre.PLACE && p.A == prise.Maison);
            if (rejouee == null || rejouee.Tick != prise.Mesuree.Tick || !rejouee.Rangs.SequenceEqual(prise.Mesuree.Rangs))
                throw Faux("le monde rejoué ne prend pas la place comme la première fois : " + (rejouee == null ? "aucune prise" : "tick " + rejouee.Tick + ", rangs " + string.Join(", ", rejouee.Rangs))
                    + " pour tick " + prise.Mesuree.Tick + ", rangs " + string.Join(", ", prise.Mesuree.Rangs));
            for (int i = 0; i < IMAGES_DE_PEINTURE; i++) yield return null;
            string preneur = guerre.PaysDeLaMaison(prise.Maison);
            var changes = Comparer(prise.Veille, prise.AlertesDeLaVeille, Releve(carte), new HashSet<(long, long)>(carte.GetComponent<LieuxDeCarte>().EnAlerte), guerre.CouleurDuPays(preneur), rejouee);
            Debug.Log("CAPTURE d'un trait : de la veille à la prise, lieux changés : " + string.Join(", ", changes.Select(l => l.Item1 + "/" + l.Item2)) + " ; preneur " + guerre.Terres.NomDuPays(preneur));
        }

        // Les lieux qui ont changé de teinte d'un relevé à l'autre ; échoue si l'échantillon est vide, si un lieu pris n'a pas la teinte du
        // preneur, ou si un lieu qui n'est pas pris a changé. L'alerte des départs est une marque posée sur le lieu, pas une teinte : un lieu
        // dont l'alerte a basculé garde la teinte de son pays, et se juge comme les autres.
        static List<(long, long)> Comparer(Dictionary<(long, long), Color32> avant, HashSet<(long, long)> alertesAvant, Dictionary<(long, long), Color32> apres, HashSet<(long, long)> alertesApres, Color preneur, PriseLue prisee)
        {
            var communs = avant.Keys.Where(apres.ContainsKey).ToList();
            if (communs.Count == 0) throw Faux("aucun lieu dessiné à la fois la veille et le jour de la prise");
            var pris = new HashSet<(long, long)>(prisee.Rangs.Select(r => (prisee.CellId, r)));
            Color32 duPreneur = preneur;
            var juges = communs;
            var changes = juges.Where(l => !avant[l].Equals(apres[l])).OrderBy(l => l).ToList();
            var visiblesPris = pris.Where(apres.ContainsKey).ToList();
            if (visiblesPris.Count == 0) throw Faux("aucun lieu pris n'est dessiné dans l'image");
            string sansTeinte = string.Join(", ", visiblesPris.Where(l => !apres[l].Equals(duPreneur)).Select(l => l.Item1 + "/" + l.Item2 + " " + apres[l]));
            if (sansTeinte.Length > 0) throw Faux("des lieux pris n'ont pas la teinte du preneur " + duPreneur + " : " + sansTeinte);
            string inchanges = string.Join(", ", visiblesPris.Where(l => avant.ContainsKey(l) && avant[l].Equals(apres[l])).Select(l => l.Item1 + "/" + l.Item2));
            if (inchanges.Length > 0) throw Faux("des lieux pris n'ont pas changé de teinte : " + inchanges);
            string autres = string.Join(", ", changes.Where(l => !pris.Contains(l)).Select(l => l.Item1 + "/" + l.Item2 + " " + avant[l] + " → " + apres[l]));
            if (autres.Length > 0) throw Faux("des lieux qui ne sont pas pris ont changé de teinte : " + autres);
            int basculees = communs.Count(l => alertesAvant.Contains(l) != alertesApres.Contains(l));
            Debug.Log("CAPTURE d'un trait : " + communs.Count + " lieux comparés, dont " + basculees + " dont l'alerte a basculé, " + changes.Count + " changés");
            return changes;
        }

        // La teinte de chaque lieu des terres dont le milieu tombe dans l'image.
        static Dictionary<(long, long), Color32> Releve(CarteDessinee carte)
        {
            var releve = new Dictionary<(long, long), Color32>();
            foreach (var cellule in carte.Lue.Cellules)
            {
                Vector3 vu = carte.camera.WorldToViewportPoint(carte.transform.TransformPoint(Centre(carte, cellule.CellId)));
                if (vu.z <= 0f || vu.x < 0f || vu.x > 1f || vu.y < 0f || vu.y > 1f) continue;
                for (long rang = 0; carte.TeinteDuLieu(cellule.CellId, rang) is Color teinte; rang++) releve[(cellule.CellId, rang)] = teinte;
            }
            return releve;
        }

        // La carte de la guerre relue au tick servi : la lecture suivante est demandée tout de suite, sans attendre sa période.
        static bool Relire(CarteDeLaGuerre guerre)
        {
            if (guerre.Terres != null && guerre.Terres.Tick == prise.Tick && guerre.Guerres != null && guerre.Guerres.Tick == prise.Tick) return true;
            guerre.Pas(Time.realtimeSinceStartupAsDouble + CarteDeLaGuerre.PERIODE_S);
            return false;
        }

        // La vue posée sur `ici` (km locaux), assez près pour lire la place et ses voisines.
        static void Viser(CarteDessinee carte, CabinetDeCarte cabinet, CarteDeLaGuerre guerre, Vector3 ici)
        {
            carte.Vue.Changer(carte.camera.aspect); carte.Vue.Centrer(new Vector2(ici.x, ici.z), DEMI_DE_LA_PRISE_KM); Poser(carte, cabinet, guerre);
        }

        static void Poser(CarteDessinee carte, CabinetDeCarte cabinet, CarteDeLaGuerre guerre)
        {
            carte.Vue.Poser(carte.camera, carte.transform);
            cabinet.transform.Find("Cabinet").GetComponent<Canvas>().planeDistance = carte.camera.nearClipPlane + ScenarioAccueil.ECART_DE_PLAN;
            guerre.SuivreLaVue();
        }

        static HorlogeDeCarte Horloge(CarteDessinee carte) => carte.GetComponent<HorlogeDeCarte>() ?? throw Faux("pas d'horloge sur la carte");
        static Button Bouton(CabinetDeCarte cabinet, string nom) =>
            cabinet.transform.Find("Cabinet").GetComponentsInChildren<Button>(true).SingleOrDefault(b => b.name == nom) ?? throw Faux("« " + nom + " » absent du cabinet");
        static bool Dedans(Vector2 ecran) => ecran.x >= 0f && ecran.x < LARGEUR && ecran.y >= 0f && ecran.y < HAUTEUR;
        static Vector2 Ecran(CarteDessinee carte, Vector3 local) => carte.camera.WorldToScreenPoint(carte.transform.TransformPoint(local));
        static Vector3? Sol(CarteDessinee carte, Vector2 ecran) => carte.SolSous(ecran) is Vector3 monde ? carte.transform.InverseTransformPoint(monde) : (Vector3?)null;
        // Le siège servi de la maison du joueur, en km locaux de la carte, au niveau de la mer.
        static Vector3 Siege(CarteDessinee carte, CabinetDeCarte cabinet) =>
            cabinet.Partie.Maison?.Donnees.Siege.Position is PointCarte p && carte.PositionSurLaCarte(p, 0f) is Vector3 v ? v : throw Faux("le siège de la maison du joueur n'est pas placé sur la carte");
        // Le milieu du plus grand contour d'une terre servie, en km locaux de la carte.
        static Vector3 Centre(CarteDessinee carte, long cellId)
        {
            var cellule = carte.Lue.Cellules.FirstOrDefault(c => c.CellId == cellId) ?? throw Faux("la terre " + cellId + " n'est pas dessinée");
            var points = cellule.Contour.OrderByDescending(c => c.Exterieur.Count).First().Exterieur.Select(x => carte.PositionSurLaCarte(x, 0f)).Where(v => v.HasValue).Select(v => v.Value).ToList();
            if (points.Count == 0) throw Faux("la terre " + cellId + " n'a pas de contour sur la carte");
            return points.Aggregate(Vector3.zero, (s, v) => s + v) / points.Count;
        }

        static InvalidOperationException Faux(string raison) => new InvalidOperationException("d'un trait : " + raison);
    }
}
