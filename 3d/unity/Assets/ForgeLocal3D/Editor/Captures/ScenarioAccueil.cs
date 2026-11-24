using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Forge.Interface;
using Forge.Pont;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures
{
    // L'accueil du jeu sur la carte de 1400, joué par ses boutons et photographié trois fois :
    //   1-accueil                l'accueil ouvert au jour servi, la carte cadrée sur l'Europe où se lisent France, Bohême, Hongrie et
    //                            Castille, la maison en petit sous chaque pays ; la fiche de la Bohême, cliquée sur la carte ;
    //   2-commencer-zab          l'Émirat du Zab pris dans les départs conseillés, « Commencer » puis « Reprendre » pressés ; le choix appliqué, la carte
    //                            est centrée sur Biskra, l'encart des premiers gestes est visible, « Entrer dans la ville » est actif ;
    //   3-commencer-sans-ville   le service relancé (un choix ne se défait pas), la France choisie : « Entrer dans la ville » est
    //                            grisé, et son infobulle dit la raison servie.
    // Chaque scénario vérifie ce qu'il photographie et échoue sinon : aucun pays ne s'écrit du nom d'une dynastie servie (« Luxembourg »,
    // « Évreux », « Valois ») ; la Navarre est écrite ; le bouton de
    // la ville a l'état attendu. Le tick est celui que le service sert, jamais un tick écrit en dur. Le cabinet de la carte est une toile
    // posée sur l'écran : la photo d'une caméra ne la voit pas, et chaque scénario la pose devant la caméra de la carte, que le cabinet
    // garde sur tout l'écran.
    static class ScenarioAccueil
    {
        const long BISKRA = 10103;
        const string ZAB = "seigneurie-6", NOM_DU_ZAB = "Émirat du Zab", FRANCE = "France";
        // Les quatre grands pays cadrés, chacun tenu par une dynastie d'un autre nom ; la Navarre, petite, doit seulement être écrite.
        static readonly string[] PAYS_LUS = { "France", "Bohême", "Hongrie", "Castille" }, PAYS_ECRITS = { "Navarre" }, MAISONS_INTERDITES = { "Luxembourg", "Évreux", "Valois" };
        internal const float ECART_DE_PLAN = 0.2f; // l'écart de la toile devant le plan proche de la caméra
        const float MARGE_DU_CADRE = 1.05f, TOLERANCE_DU_CENTRE_KM = 5f;
        const double STABLE_S = 2.5; // les textes du cabinet sont récrits une image après la lecture

        [ScenarioDeCapture("accueil", "1-accueil")]
        static IEnumerator Accueil(Camera camera)
        {
            var e = OuvrirLaCarte(); while (e.MoveNext()) yield return e.Current;
            var (carte, cabinet, guerre) = Lire();
            VerifierLesNoms(guerre);
            // La Bohême cliquée sur la carte : sa fiche dit sa maison servie (Luxembourg, qui règne aussi sur le Saint-Empire).
            string boheme = guerre.Terres.Pays.Single(p => p.Nom == "Bohême").Id, maisonDeLaBoheme = guerre.Terres.MaisonDuPays(boheme)?.Nom ?? throw Faux("la Bohême n'a pas de maison servie");
            cabinet.Accueil.Designer(guerre.Terres.Terres.First(t => t.Pays == boheme).CellId);
            // « Commencer » s'active une image après la fiche : il s'attend avec elle.
            for (var a = AttentesDeCapture.Jusqua(() => cabinet.Accueil.TexteDuNom == "Bohême" && cabinet.Accueil.TexteDeLaFiche.StartsWith("Bohême : ", StringComparison.Ordinal) && !cabinet.Accueil.TexteDeLaFiche.Contains("en lecture") && cabinet.Accueil.Commencer.interactable,
                () => "fiche de la Bohême : « " + cabinet.Accueil.TexteDuNom + " » « " + cabinet.Accueil.TexteDeLaFiche + " », « Commencer » " + (cabinet.Accueil.Commencer.interactable ? "actif" : "inactif")); a.MoveNext();) yield return null;
            string[] lignesDeLaFiche = cabinet.Accueil.TexteDeLaFiche.Split('\n');
            // La fiche compte la Bohême seule, puis la maison qui y règne, avec ses vassaux : deux nombres, chacun nommé.
            if (lignesDeLaFiche.Length < 2 || !lignesDeLaFiche[1].StartsWith("Maison ", StringComparison.Ordinal) || !lignesDeLaFiche[1].Contains(maisonDeLaBoheme)) throw Faux("la fiche de la Bohême ne dit pas sa maison : « " + cabinet.Accueil.TexteDeLaFiche + " »");
            if (cabinet.Accueil.Commencer.interactable != true) throw Faux("« Commencer » est inactif pour la Bohême");
            // Cadrée sur les quatre pays : tous lisibles à la fois, chacun avec sa maison dessous quand elle porte un autre nom.
            var noms = PAYS_LUS.Select(n => guerre.NomsDesPays.Single(x => x.Texte == n)).ToArray();
            // Le cadre tient chaque lettre des quatre noms, avec un corps de marge.
            var lettres = noms.SelectMany(n => n.Compose.Lettres.Select(l => (p: l.Point, c: n.Corps))).ToArray();
            Vector2 min = new Vector2(lettres.Min(l => l.p.x - l.c), lettres.Min(l => l.p.y - l.c)), max = new Vector2(lettres.Max(l => l.p.x + l.c), lettres.Max(l => l.p.y + l.c));
            // L'accueil ouvert couvre la carte à partir du bord gauche de son panneau : les quatre pays se cadrent dans la part qui reste à gauche.
            float part = PartDeLaCarte(carte, cabinet);
            float demi = Mathf.Max((max.y - min.y) / 2f, (max.x - min.x) / 2f / (carte.camera.aspect * part)) * MARGE_DU_CADRE;
            Vector2 centre = (min + max) / 2f + new Vector2(demi * carte.camera.aspect * (1f - part), 0f);
            carte.Vue.Changer(carte.camera.aspect); carte.Vue.Centrer(centre, demi); carte.Vue.Poser(carte.camera, carte.transform); guerre.SuivreLaVue();
            for (int i = 0; i < 4; i++) yield return null;
            string hors = string.Join(", ", noms.Where(n => n.Compose.Lettres.Any(l => { Vector3 v = carte.camera.WorldToViewportPoint(carte.transform.TransformPoint(new Vector3(l.Point.x, 0f, l.Point.y)));
                return v.z <= 0f || v.x < 0f || v.x > part || v.y < 0f || v.y > 1f; })).Select(n => n.Texte));
            if (hors.Length > 0) throw Faux("noms hors de la carte visible : " + hors);
            string caches = string.Join(", ", noms.Where(n => n.Opacite <= 0f).Select(n => n.Texte + " (" + n.CorpsPx.ToString("0.#", CultureInfo.InvariantCulture) + " px)"));
            if (caches.Length > 0) throw Faux("noms cachés sur le cadre de l'Europe (demi " + demi.ToString("0", CultureInfo.InvariantCulture) + " km) : " + caches);
            if (guerre.NomsDesPays.Single(n => n.Texte == "Bohême").Maison?.Texte != maisonDeLaBoheme) throw Faux("la Bohême n'écrit pas sa maison " + maisonDeLaBoheme + " dessous");
            Debug.Log("CAPTURE accueil : tick " + cabinet.Partie.Monde.Donnees.Monde.Tick + ", " + guerre.NomsDesPays.Count + " pays nommés, demi " + demi.ToString("0", CultureInfo.InvariantCulture) + " km ; "
                + string.Join(", ", noms.Select(n => n.Texte + " " + n.CorpsPx.ToString("0", CultureInfo.InvariantCulture) + " px" + (n.Maison == null ? "" : " (" + n.Maison.Texte + " " + n.Maison.CorpsPx.ToString("0", CultureInfo.InvariantCulture) + " px, opacité " + n.Maison.Opacite.ToString("0.##", CultureInfo.InvariantCulture) + ")"))));
            var s = Stabiliser(cabinet); while (s.MoveNext()) yield return null;
            yield return carte.camera;
        }

        [ScenarioDeCapture("accueil", "2-commencer-zab")]
        static IEnumerator CommencerZab(Camera camera)
        {
            var (carte, cabinet, guerre) = Lire();
            Button zab = cabinet.Accueil.Panneau.GetComponentsInChildren<Button>(true).SingleOrDefault(b => b.name == NOM_DU_ZAB) ?? throw Faux("« " + NOM_DU_ZAB + " » absent des départs conseillés");
            zab.onClick.Invoke();
            for (var a = AttentesDeCapture.Jusqua(() => cabinet.Accueil.Montree?.Id == ZAB && cabinet.Accueil.Commencer.interactable && cabinet.Accueil.TexteDeLaFiche.EndsWith("Ville à bâtir : oui", StringComparison.Ordinal),
                () => "fiche du Zab : « " + cabinet.Accueil.TexteDeLaFiche + " »"); a.MoveNext();) yield return null;
            var commencer = CommencerPuisLancer(cabinet); while (commencer.MoveNext()) yield return commencer.Current;
            for (var a = AttentesDeCapture.Jusqua(() => Servie(cabinet) == ZAB && cabinet.Partie.Jouable != null && cabinet.Partie.Maison?.Presente == true && cabinet.Ville.Actif && cabinet.Gestes.Visible,
                () => "après « Commencer » : maison « " + Servie(cabinet) + " », reçu « " + (cabinet.Partie.Recu?.Erreur ?? cabinet.Partie.Recu?.Absence) + " », bouton " + cabinet.Ville.Actif + ", encart " + cabinet.Gestes.Visible); a.MoveNext();) yield return null;
            var siege = cabinet.Partie.Maison.Donnees.Siege;
            if (siege.CellId != BISKRA || cabinet.Partie.Jouable.Siege.CellId != BISKRA) throw Faux("le siège du Zab n'est pas Biskra (" + siege.CellId + ")");
            Vector3 ici = carte.PositionSurLaCarte(siege.Position.Value, 0f).Value;
            // La vue vise le siège autant que les bords de la carte le permettent : Biskra, au sud, tombe au milieu de l'image.
            Vector3 vu = carte.camera.WorldToViewportPoint(carte.transform.TransformPoint(ici));
            if (Mathf.Abs(carte.Vue.Centre.x - ici.x) > TOLERANCE_DU_CENTRE_KM || vu.z <= 0f || Mathf.Abs(vu.x - 0.5f) > 0.1f || Mathf.Abs(vu.y - 0.5f) > 0.25f)
                throw Faux("la carte n'est pas centrée sur Biskra : vue " + carte.Vue.Centre + " pour " + new Vector2(ici.x, ici.z) + ", à l'image " + vu);
            if (cabinet.Accueil.Panneau.gameObject.activeSelf) throw Faux("l'accueil reste ouvert");
            if (cabinet.Ville.Phrase != "Ouvre Biskra, votre capitale.") throw Faux("l'infobulle du bouton de la ville : « " + cabinet.Ville.Phrase + " »");
            VerifierLesNoms(guerre);
            Debug.Log("CAPTURE accueil : le Zab joue au tick " + cabinet.Partie.Monde.Donnees.Monde.Tick + ", centré sur " + carte.Vue.Centre);
            var s = Stabiliser(cabinet); while (s.MoveNext()) yield return null;
        }

        [ScenarioDeCapture("accueil", "3-commencer-sans-ville")]
        static IEnumerator CommencerSansVille(Camera camera)
        {
            Capture.RelancerLeService();
            var e = OuvrirLaCarte(); while (e.MoveNext()) yield return e.Current;
            var (carte, cabinet, guerre) = Lire();
            string france = guerre.Terres.Pays.Single(p => p.Nom == FRANCE).Id;
            cabinet.Accueil.Designer(guerre.Terres.Terres.First(t => t.Pays == france).CellId);
            for (var a = AttentesDeCapture.Jusqua(() => cabinet.Accueil.TexteDuNom == FRANCE && cabinet.Accueil.Montree != null && cabinet.Accueil.Commencer.interactable,
                () => "fiche de la France : « " + cabinet.Accueil.TexteDuNom + " » « " + cabinet.Accueil.TexteDeLaFiche + " »"); a.MoveNext();) yield return null;
            string maison = cabinet.Accueil.Montree.Id;
            var commencer = CommencerPuisLancer(cabinet); while (commencer.MoveNext()) yield return commencer.Current;
            for (var a = AttentesDeCapture.Jusqua(() => Servie(cabinet) == maison && cabinet.Partie.Jouable != null && cabinet.Ville.Bouton.gameObject.activeSelf && cabinet.Gestes.Visible,
                () => "après « Commencer » : maison « " + Servie(cabinet) + " », reçu « " + (cabinet.Partie.Recu?.Erreur ?? cabinet.Partie.Recu?.Absence) + " »"); a.MoveNext();) yield return null;
            yield return null;
            if (cabinet.Ville.Actif) throw Faux("« Entrer dans la ville » est actif pour la France");
            string raison = cabinet.Partie.Jouable.Ville.Raison;
            if (raison == null || cabinet.Ville.Phrase != AccueilDuPays.PhraseDeRaison(raison)) throw Faux("l'infobulle du bouton grisé ne dit pas la raison servie : « " + cabinet.Ville.Phrase + " »");
            VerifierLesNoms(guerre);
            var s = Stabiliser(cabinet); while (s.MoveNext()) yield return null;
            // L'infobulle du bouton grisé, montrée comme au survol, sous le bouton.
            var toile = cabinet.transform.Find("Cabinet").GetComponent<Canvas>(); Canvas.ForceUpdateCanvases();
            var coins = new Vector3[4]; ((RectTransform)cabinet.Ville.Bouton.transform).GetWorldCorners(coins);
            Infobulle.Montrer(toile, cabinet.Ville.Phrase, RectTransformUtility.WorldToScreenPoint(carte.camera, (coins[0] + coins[2]) / 2f));
            Debug.Log("CAPTURE accueil : la France (" + maison + ") joue au tick " + cabinet.Partie.Monde.Donnees.Monde.Tick + " ; « " + cabinet.Ville.Phrase + " »");
            for (int i = 0; i < 3; i++) yield return null;
            yield return carte.camera;
        }

        // La part de la largeur de l'image que l'accueil ouvert laisse à la carte : le bord gauche de son panneau, lu sur la caméra de la carte
        // (la toile suit son champ, donc ce bord ne dépend ni de la taille de la fenêtre ni de l'aspect posé).
        static float PartDeLaCarte(CarteDessinee carte, CabinetDeCarte cabinet)
        {
            Canvas.ForceUpdateCanvases();
            var coins = new Vector3[4]; cabinet.Accueil.Panneau.GetWorldCorners(coins);
            float bord = coins.Min(c => carte.camera.WorldToViewportPoint(c).x);
            if (!(bord > 0f && bord < 1f)) throw Faux("le panneau de l'accueil ne laisse pas de carte à gauche (bord à " + bord.ToString("0.###", CultureInfo.InvariantCulture) + " de l'image)");
            return bord;
        }

        // La carte ouverte, dessinée, ses pays nommés, la partie et les pays jouables lus ; puis sa toile posée devant sa caméra.
        internal static IEnumerator OuvrirLaCarte()
        {
            SceneManager.LoadScene(OuvertureDeLaCarte.SCENE);
            yield return null;
            CarteDessinee carte = null; CabinetDeCarte cabinet = null; CarteDeLaGuerre guerre = null;
            for (var a = AttentesDeCapture.Jusqua(() => (carte = Object.FindFirstObjectByType<CarteDessinee>()) != null && carte.Vue != null && carte.camera != null
                && (cabinet = carte.GetComponent<CabinetDeCarte>()) != null && cabinet.Partie?.Monde?.Presente == true && cabinet.Partie.Jouables?.Presente == true
                && (guerre = carte.GetComponent<CarteDeLaGuerre>()) != null && guerre.Terres != null && guerre.NomsDesPays.Count > 0,
                () => "carte ou accueil non prêts (" + (cabinet == null ? "pas de cabinet" : cabinet.Partie?.Monde?.Absence ?? cabinet.Partie?.Jouables?.Absence ?? (guerre?.AbsenceDesTerres ?? "terres ou noms en attente")) + ")"); a.MoveNext();) yield return null;
            if (!cabinet.Accueil.Ouvert) throw Faux("l'accueil n'est pas ouvert à l'ouverture de la carte");
            // La toile de l'écran, posée devant la caméra de la carte ; la photo fait 1600 × 900, et le rect de la caméra est celui que le cabinet garde.
            carte.camera.aspect = 1600f / 900f;
            var toile = cabinet.transform.Find("Cabinet").GetComponent<Canvas>();
            toile.renderMode = RenderMode.ScreenSpaceCamera; toile.worldCamera = carte.camera; toile.planeDistance = carte.camera.nearClipPlane + ECART_DE_PLAN;
            carte.Vue.Changer(carte.camera.aspect); carte.Vue.Poser(carte.camera, carte.transform);
            yield return carte.camera;
        }

        internal static (CarteDessinee, CabinetDeCarte, CarteDeLaGuerre) Lire()
        {
            var carte = Object.FindFirstObjectByType<CarteDessinee>() ?? throw Faux("pas de carte");
            return (carte, carte.GetComponent<CabinetDeCarte>() ?? throw Faux("pas de cabinet"), carte.GetComponent<CarteDeLaGuerre>() ?? throw Faux("pas de carte de la guerre"));
        }

        internal static string Servie(CabinetDeCarte cabinet) => cabinet.Partie?.Monde?.Presente == true ? cabinet.Partie.Monde.Donnees.MaisonDuJoueur : null;

        // « Commencer », puis « Reprendre » comme le joueur : le choix reçu laisse le monde en pause, et sa maison n'est servie
        // qu'au jour suivant. Le temps déjà lancé n'est pas basculé.
        internal static IEnumerator CommencerPuisLancer(CabinetDeCarte cabinet)
        {
            cabinet.Accueil.Commencer.onClick.Invoke();
            for (var a = AttentesDeCapture.Jusqua(() => cabinet.Partie.Recu?.Acceptee == true, () => "le choix n'est pas reçu : « " + (cabinet.Partie.Recu?.Erreur ?? cabinet.Partie.Recu?.Absence) + " »"); a.MoveNext();) yield return null;
            var horloge = cabinet.GetComponent<HorlogeDeCarte>();
            for (var a = AttentesDeCapture.Jusqua(() => horloge.Lue != null, () => "l'horloge n'est pas servie : " + horloge.Absence); a.MoveNext();) yield return null;
            if (horloge.EnPause) cabinet.GetComponentsInChildren<Button>(true).Single(b => b.name == "Pause / Reprendre").onClick.Invoke();
        }

        // Les pays de la carte portent leur nom de 1400, jamais celui d'une dynastie servie : la maison d'un pays qui porte un autre
        // nom qu'elle, quand aucun pays servi ne porte ce nom. Les pays attendus sont écrits.
        internal static void VerifierLesNoms(CarteDeLaGuerre guerre)
        {
            var ecrits = new HashSet<string>(guerre.NomsDesPays.Select(n => n.Texte));
            var servis = new HashSet<string>(guerre.Terres.Pays.Select(p => p.Nom).Where(n => n != null));
            var dynasties = new HashSet<string>(guerre.Terres.Pays.Where(p => p.Maison?.Nom != null && p.Maison.Nom != p.Nom && !servis.Contains(p.Maison.Nom)).Select(p => p.Maison.Nom));
            foreach (string interdit in MAISONS_INTERDITES) if (!dynasties.Contains(interdit)) throw Faux("« " + interdit + " » n'est plus une dynastie servie : le contrôle ne prouve plus rien");
            string fautifs = string.Join(", ", ecrits.Where(dynasties.Contains));
            if (fautifs.Length > 0) throw Faux("des noms de dynastie sont écrits comme noms de pays : " + fautifs);
            string manquants = string.Join(", ", PAYS_LUS.Concat(PAYS_ECRITS).Where(p => !ecrits.Contains(p)));
            if (manquants.Length > 0) throw Faux("pays non écrits sur la carte : " + manquants);
        }

        // Les textes de l'accueil, de l'encart et du bouton de la ville ne bougent plus pendant STABLE_S ; la date et les comptes,
        // qui suivent le temps quand il file, n'en sont pas.
        internal static IEnumerator Stabiliser(CabinetDeCarte cabinet)
        {
            var racines = new[] { cabinet.Accueil.Panneau.transform, cabinet.Gestes.Panneau.transform, cabinet.Ville.Bouton.transform };
            string Etat() => string.Join("|", racines.SelectMany(r => r.GetComponentsInChildren<Text>()).Where(t => t.isActiveAndEnabled).Select(t => t.text)) + "|" + cabinet.Ville.Phrase;
            string avant = Etat(); double depuis = Time.realtimeSinceStartupAsDouble, fin = depuis + 20;
            while (Time.realtimeSinceStartupAsDouble - depuis < STABLE_S && Time.realtimeSinceStartupAsDouble < fin)
            {
                yield return null; string maintenant = Etat();
                if (maintenant != avant) { avant = maintenant; depuis = Time.realtimeSinceStartupAsDouble; }
            }
        }

        static InvalidOperationException Faux(string raison) => new InvalidOperationException("accueil : " + raison);
    }
}
