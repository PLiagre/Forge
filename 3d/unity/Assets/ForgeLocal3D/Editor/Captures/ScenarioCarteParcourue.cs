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
    // Toute la carte se parcourt, l'accueil ouvert, contre le vrai service, en douze photos qui partent chacune de l'état de la précédente :
    //   a, b, c        la carte glissée à la souris, sans sortir de la partie libre de l'écran, jusqu'à Constantinople, Nicosie et Le
    //                  Caire, cherchées par leur nom servi (une ville de `/carte` ou un siège de `/atlas`) ; chacune est cliquée au
    //                  sud-est de son pied, sur sa figurine, comme le testeur, et l'accueil montre la fiche de son pays ;
    //   d, e, f, g     les quatre coins des bornes de la carte, chacun amené au milieu de la partie libre ;
    //   h              la vue reculée au plus loin : toute la carte tient dans la partie libre ;
    //   i, j, k        l'est de l'Anatolie, le sud de l'Égypte et le Sahara au sud de Tripoli, là où la carte coupe la terre : la terre
    //                  s'estompe dans le papier, et « hors de la carte » se lit ;
    //   l              la France prise, « Commencer » cliqué : l'accueil se ferme, la barre nomme la France, et le premier « Reprendre »
    //                  part à la vitesse de départ, écrite à côté de la date.
    // Sur les photos d à k, un échantillon de pixels de la vue, hors de l'interface, est lu : chacun est de la terre (son rayon touche un
    // lieu), de la mer ou du papier (près des couleurs de la mer, du rivage et du papier de la carte), jamais du noir ; les traits, les
    // noms et les figurines posés sur la carte n'en prennent qu'une petite part. Un échantillon vide échoue. La caméra de la carte
    // rend dans un écran de la taille de la photo, où se règlent la toile, la partie libre et les clics.
    static class ScenarioCarteParcourue
    {
        const string GROUPE = "carte-parcourue", FRANCE = "France";
        const int LARGEUR = 1920, HAUTEUR = 1080, IMAGES_DE_POSE = 6, IMAGES_DU_GLISSER = 8, ESSAIS_DE_GLISSER = 16, PAS_DE_LA_GRILLE_PX = 40;
        // La demi-hauteur de la vue pour visiter les villes, les coins et les coupes ; le pas d'un glisser ; à combien de pixels du milieu
        // de la partie libre une ville est arrivée.
        const float DEMI_DES_VILLES_KM = 600f, DEMI_DES_COINS_KM = 700f, DEMI_DES_COUPES_KM = 450f, PAS_DU_GLISSER_PX = 600f, ARRIVEE_PX = 60f;
        // Un pixel de mer ou de papier est à moins de cet écart, par composante, d'une couleur de la carte ; un pixel noir n'a aucune
        // composante au-dessus de NOIR ; les traits, noms et figurines prennent au plus PART_DES_TRAITS de l'échantillon.
        const float ECART_DE_COULEUR = 0.09f, NOIR = 0.06f, PART_DES_TRAITS = 0.15f;
        // À ce nombre de km de la coupe, la terre a presque pris le papier.
        const float ESTOMPE_KM = 15f, ESTOMPE_MIN = 0.7f;

        static readonly ParcoursDeVue geste = new ParcoursDeVue();

        [ScenarioDeCapture(GROUPE, "a-constantinople", Largeur = LARGEUR, Hauteur = HAUTEUR)]
        static IEnumerator Constantinople(Camera camera)
        {
            var e = ScenarioAccueil.OuvrirLaCarte(); while (e.MoveNext()) yield return e.Current;
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            if (carte.camera.targetTexture == null) carte.camera.targetTexture = new RenderTexture(LARGEUR, HAUTEUR, 24) { name = "Écran de la carte parcourue" };
            carte.camera.aspect = (float)LARGEUR / HAUTEUR;
            for (var a = AttentesDeCapture.Jusqua(() => carte.Vue.Libre.width < 1f && Villes(carte).Posees > 0,
                () => "la partie libre ne compte pas l'accueil (" + carte.Vue.Libre + ") ou les villes ne sont pas posées"); a.MoveNext();) yield return null;
            // De la vue d'ouverture à une vue où se lisent les villes, molette au milieu de la partie libre.
            float crans = Mathf.Log(DEMI_DES_VILLES_KM / carte.Vue.Demi) / Mathf.Log(VueDeCarte.PAS_DE_ZOOM);
            Molette(carte, cabinet, Milieu(carte), crans);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            var v = Visiter(carte, cabinet, guerre, "Constantinople"); while (v.MoveNext()) yield return v.Current;
            yield return carte.camera;
        }

        [ScenarioDeCapture(GROUPE, "b-nicosie", Largeur = LARGEUR, Hauteur = HAUTEUR)]
        static IEnumerator Nicosie(Camera camera)
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            var v = Visiter(carte, cabinet, guerre, "Nicosie"); while (v.MoveNext()) yield return v.Current;
        }

        [ScenarioDeCapture(GROUPE, "c-le-caire", Largeur = LARGEUR, Hauteur = HAUTEUR)]
        static IEnumerator LeCaire(Camera camera)
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            var v = Visiter(carte, cabinet, guerre, "Le Caire"); while (v.MoveNext()) yield return v.Current;
        }

        [ScenarioDeCapture(GROUPE, "d-coin-nord-ouest", Largeur = LARGEUR, Hauteur = HAUTEUR)]
        static IEnumerator CoinNordOuest(Camera camera) => Coin(new Vector2(0f, 1f), "nord-ouest");
        [ScenarioDeCapture(GROUPE, "e-coin-nord-est", Largeur = LARGEUR, Hauteur = HAUTEUR)]
        static IEnumerator CoinNordEst(Camera camera) => Coin(new Vector2(1f, 1f), "nord-est");
        [ScenarioDeCapture(GROUPE, "f-coin-sud-est", Largeur = LARGEUR, Hauteur = HAUTEUR)]
        static IEnumerator CoinSudEst(Camera camera) => Coin(new Vector2(1f, 0f), "sud-est");
        [ScenarioDeCapture(GROUPE, "g-coin-sud-ouest", Largeur = LARGEUR, Hauteur = HAUTEUR)]
        static IEnumerator CoinSudOuest(Camera camera) => Coin(new Vector2(0f, 0f), "sud-ouest");

        [ScenarioDeCapture(GROUPE, "h-au-plus-loin", Largeur = LARGEUR, Hauteur = HAUTEUR)]
        static IEnumerator AuPlusLoin(Camera camera)
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            Molette(carte, cabinet, Milieu(carte), -1000f);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            if (!Mathf.Approximately(carte.Vue.Echelle, 1f)) throw Faux("la molette ne mène pas au plus loin : échelle " + F(carte.Vue.Echelle));
            Rect cadre = carte.Cadre, libre = carte.Vue.Libre;
            foreach (var bout in new[] { new Vector2(cadre.xMin, cadre.yMin), new Vector2(cadre.xMax, cadre.yMin), new Vector2(cadre.xMin, cadre.yMax), new Vector2(cadre.xMax, cadre.yMax) })
            {
                Vector3 f = carte.camera.WorldToViewportPoint(carte.transform.TransformPoint(new Vector3(bout.x, 0f, bout.y)));
                if (f.x < libre.xMin - 1e-3f || f.x > libre.xMax + 1e-3f || f.y < libre.yMin - 1e-3f || f.y > libre.yMax + 1e-3f)
                    throw Faux("au plus loin, le coin " + bout + " de la carte tombe en " + f + " de l'écran, hors de la partie libre " + libre);
            }
            VerifierLesPixels(carte, cabinet, "au plus loin");
            yield return carte.camera;
        }

        [ScenarioDeCapture(GROUPE, "i-est-de-l-anatolie", Largeur = LARGEUR, Hauteur = HAUTEUR)]
        static IEnumerator EstDeLAnatolie(Camera camera)
        {
            var (carte, _, _) = ScenarioAccueil.Lire(); var o = carte.Terrain.Origine;
            Vector4? coupe = carte.Terrain.Coupes.Where(c => Dans(o, (c.x + c.z) / 2f, (c.y + c.w) / 2f)).OrderByDescending(c => new Vector2(c.z - c.x, c.w - c.y).magnitude).Cast<Vector4?>().FirstOrDefault();
            return Coupe(coupe ?? throw Faux("aucune coupe à l'est de l'Anatolie parmi les " + carte.Terrain.Coupes.Count + " servies"), "l'est de l'Anatolie");
        }

        [ScenarioDeCapture(GROUPE, "j-sud-de-l-egypte", Largeur = LARGEUR, Hauteur = HAUTEUR)]
        static IEnumerator SudDeLEgypte(Camera camera) => Coupe(CoupeAuSudDe("Le Caire"), "le sud de l'Égypte");

        [ScenarioDeCapture(GROUPE, "k-sahara-pres-de-tripoli", Largeur = LARGEUR, Hauteur = HAUTEUR)]
        static IEnumerator SaharaPresDeTripoli(Camera camera) => Coupe(CoupeAuSudDe("Tripoli"), "le Sahara au sud de Tripoli");

        [ScenarioDeCapture(GROUPE, "l-commencer", Largeur = LARGEUR, Hauteur = HAUTEUR)]
        static IEnumerator Commencer(Camera camera)
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            string france = guerre.Terres.Pays.Single(p => p.Nom == FRANCE).Id;
            cabinet.Accueil.Designer(guerre.Terres.Terres.First(t => t.Pays == france).CellId);
            for (var a = AttentesDeCapture.Jusqua(() => cabinet.Accueil.TexteDuNom == FRANCE && cabinet.Accueil.Montree != null && cabinet.Accueil.Commencer.interactable,
                () => "fiche de la France : « " + cabinet.Accueil.TexteDuNom + " »"); a.MoveNext();) yield return null;
            string maison = cabinet.Accueil.Montree.Id;
            GestesDeCapture.CliquerAuPointeur(carte.camera, cabinet.Accueil.Commencer);
            for (var a = AttentesDeCapture.Jusqua(() => cabinet.Partie.Recu?.Acceptee == true, () => "le choix n'est pas reçu : « " + (cabinet.Partie.Recu?.Erreur ?? cabinet.Partie.Recu?.Absence) + " »"); a.MoveNext();) yield return null;
            // Le choix reçu, monde en pause, sa maison pas encore servie : l'accueil est fermé et la barre nomme la France.
            Text barre = null;
            for (var a = AttentesDeCapture.Jusqua(() => !cabinet.Accueil.Ouvert && !cabinet.Accueil.Panneau.gameObject.activeSelf && (barre = Barre(cabinet, FRANCE + " · choix reçu")) != null,
                () => "après « Commencer » : accueil " + (cabinet.Accueil.Ouvert ? "ouvert" : "fermé") + ", barre « " + string.Join(" | ", TextesDuBandeau(cabinet)) + " »"); a.MoveNext();) yield return null;
            if (ScenarioAccueil.Servie(cabinet) != null) throw Faux("la maison est déjà servie : le cas du choix reçu, monde en pause, n'est pas jugé");
            Debug.Log("CAPTURE carte parcourue : après « Commencer », la barre dit « " + barre.text + " »");
            // Le premier « Reprendre » part à la vitesse de départ, que la date écrit sur sa ligne.
            var horloge = carte.GetComponent<HorlogeDeCarte>() ?? throw Faux("pas d'horloge sur la carte");
            for (var a = AttentesDeCapture.Jusqua(() => horloge.Lue != null, () => "l'horloge n'est pas servie : " + horloge.Absence); a.MoveNext();) yield return null;
            if (!horloge.EnPause) throw Faux("le monde ne reste pas en pause après le choix");
            double depart = ReglagesDesVues.Charger().VitesseDepart;
            GestesDeCapture.CliquerAuPointeur(carte.camera, cabinet.GetComponentsInChildren<Button>(true).Single(b => b.name == "Pause / Reprendre"));
            for (var a = AttentesDeCapture.Jusqua(() => horloge.Lue != null && horloge.Lue.JoursParSeconde == depart, () => "le premier « Reprendre » ne part pas à " + F((float)depart) + " jour par seconde : " + horloge.Lue?.JoursParSeconde); a.MoveNext();) yield return null;
            // La maison servie, la barre s'ouvre sur le pays du joueur.
            for (var a = AttentesDeCapture.Jusqua(() => ScenarioAccueil.Servie(cabinet) == maison && cabinet.Partie.Jouable != null && (barre = Barre(cabinet, FRANCE + " · ")) != null && !barre.text.Contains("choix reçu"),
                () => "la maison servie : « " + ScenarioAccueil.Servie(cabinet) + " », barre « " + string.Join(" | ", TextesDuBandeau(cabinet)) + " »"); a.MoveNext();) yield return null;
            // Le temps file : la date du bandeau change, sa fin dit la vitesse, sur la même ligne.
            string date = HorlogeDeCarte.Decrire(horloge.Lue), vitesse = date.Substring(Math.Max(0, date.IndexOf(" · ", StringComparison.Ordinal)));
            if (date.Contains("\n") || !TextesDuBandeau(cabinet).Any(t => t.StartsWith("Jour ", StringComparison.Ordinal) && t.EndsWith(vitesse, StringComparison.Ordinal) && !t.Contains("\n")))
                throw Faux("la date et la vitesse ne tiennent pas sur une ligne du bandeau : « " + string.Join(" | ", TextesDuBandeau(cabinet)) + " »");
            Debug.Log("CAPTURE carte parcourue : la France joue ; barre « " + barre.text + " » ; date « " + date + " »");
            PoserLaToile(carte, cabinet);
            var s = ScenarioAccueil.Stabiliser(cabinet); while (s.MoveNext()) yield return null;
            yield return carte.camera;
        }

        // La ville de ce nom servi glissée à la souris jusqu'au milieu de la partie libre, puis cliquée sur sa figurine, au sud-est de son
        // pied ; le point sous la souris rend un lieu, et l'accueil montre le pays de sa terre.
        static IEnumerator Visiter(CarteDessinee carte, CabinetDeCarte cabinet, CarteDeLaGuerre guerre, string nom)
        {
            var villes = Villes(carte);
            var figurine = villes.Figurines.FirstOrDefault(f => f.ville == nom);
            if (figurine.ville == null) throw Faux("« " + nom + " » n'est ni une ville servie ni un siège posé (" + villes.Posees + " figurines)");
            Vector2 cible = Milieu(carte); int glisses = 0;
            for (; glisses < ESSAIS_DE_GLISSER; glisses++)
            {
                Vector2 ecart = cible - Ecran(carte, figurine.pied);
                if (ecart.magnitude <= ARRIVEE_PX) break;
                var g = Glisser(carte, cabinet, cible, cible + Vector2.ClampMagnitude(ecart, PAS_DU_GLISSER_PX)); while (g.MoveNext()) yield return null;
                yield return null; // la caméra se pose sur la vue à l'image suivante
            }
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            Vector2 ici = Ecran(carte, figurine.pied);
            if (!PixelsLibres(carte).Contains(ici)) throw Faux(nom + " n'est pas dans la partie libre de l'écran après " + glisses + " glissers : en " + ici + ", partie libre " + PixelsLibres(carte));
            figurine = villes.Figurines.First(f => f.ville == nom && f.pied == figurine.pied);
            if (!figurine.montree) throw Faux("la figurine de " + nom + " est cachée");
            // Au sud-est du pied, aux six dixièmes du rayon de la figurine à l'écran : là où le testeur l'a cliquée.
            float rayonPx = (Ecran(carte, figurine.pied + Vector3.right * figurine.rayonKm) - ici).magnitude;
            Vector2 clic = ici + new Vector2(.6f, -.6f) * rayonPx;
            if (cabinet.HorsCarte(clic)) throw Faux("le clic sur " + nom + " en " + clic + " tombe sur l'interface");
            var fiche = carte.GetComponent<FicheDeCellule>() ?? throw Faux("pas de fiche sur la carte");
            fiche.Survoler(clic); CelluleDeCarte sous = fiche.Survolee ?? throw Faux(nom + " ne rend pas de lieu sous la souris en " + clic);
            bool surLaMer = carte.SolSous(clic) is Vector3 sol && carte.Terrain.CelluleEn(carte.transform.InverseTransformPoint(sol).x, carte.transform.InverseTransformPoint(sol).z) == 0;
            cabinet.Noter(clic, true, false, false, sous);
            if (!cabinet.Noter(clic, false, true, false, sous)) throw Faux("le clic sur " + nom + " ne garde pas sa terre");
            string pays = guerre.Terres.PaysDe(sous.CellId), attendu = pays != null ? guerre.Terres.NomDuPays(pays) : null;
            if (attendu == null) throw Faux("la terre de " + nom + " (" + sous.CellId + ") n'a pas de pays servi : l'accueil ne peut rien montrer");
            for (var a = AttentesDeCapture.Jusqua(() => cabinet.Accueil.TexteDuNom == attendu && !cabinet.Accueil.TexteDeLaFiche.Contains("en lecture"),
                () => "l'accueil ne montre pas la fiche de " + attendu + " après le clic sur " + nom + " : « " + cabinet.Accueil.TexteDuNom + " » « " + cabinet.Accueil.TexteDeLaFiche + " »"); a.MoveNext();) yield return null;
            Debug.Log("CAPTURE carte parcourue : " + nom + " cliquée en " + clic + (surLaMer ? ", sur la mer que couvre sa figurine" : ", sur sa terre") + ", après " + glisses + " glissers ; fiche « "
                + cabinet.Accueil.TexteDuNom + " » : " + cabinet.Accueil.TexteDeLaFiche.Replace("\n", " · "));
            PoserLaToile(carte, cabinet);
            var s = ScenarioAccueil.Stabiliser(cabinet); while (s.MoveNext()) yield return null;
        }

        // Le coin des bornes de la carte (0 ou 1 sur chaque axe) amené au milieu de la partie libre : le point visé va jusqu'à lui.
        static IEnumerator Coin(Vector2 quel, string nom)
        {
            var (carte, cabinet, _) = ScenarioAccueil.Lire(); Rect cadre = carte.Cadre;
            var coin = new Vector2(Mathf.Lerp(cadre.xMin, cadre.xMax, quel.x), Mathf.Lerp(cadre.yMin, cadre.yMax, quel.y));
            carte.Vue.Changer(carte.camera.aspect); carte.Vue.Centrer(coin, DEMI_DES_COINS_KM); carte.Vue.Amener(coin, carte.Vue.Libre.center); carte.Vue.Poser(carte.camera, carte.transform);
            PoserLaToile(carte, cabinet);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            if (Vector2.Distance(carte.Vue.Vise, coin) > 1f) throw Faux("le coin " + nom + " " + coin + " ne vient pas au milieu de la partie libre : le point visé est en " + carte.Vue.Vise);
            VerifierLesPixels(carte, cabinet, "le coin " + nom);
            yield return carte.camera;
        }

        // Une coupe de la carte, centrée avec le « hors de la carte » le plus proche dans la partie libre : la terre à `ESTOMPE_KM` d'elle
        // a presque pris le papier, et le mot se lit.
        static IEnumerator Coupe(Vector4 cote, string ou)
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire(); var terrain = carte.Terrain;
            Vector2 a = new Vector2(cote.x, cote.y), b = new Vector2(cote.z, cote.w), milieu = (a + b) / 2f, versLaTerre = new Vector2(b.y - a.y, a.x - b.x).normalized;
            if (terrain.CelluleEn(milieu.x + 5f * versLaTerre.x, milieu.y + 5f * versLaTerre.y) == 0) versLaTerre = -versLaTerre;
            Transform mot = carte.transform.Find(CarteDessinee.HORS_CARTE)?.Cast<Transform>().OrderBy(t => Vector2.Distance(new Vector2(t.localPosition.x, t.localPosition.z), milieu)).FirstOrDefault()
                ?? throw Faux("aucun « hors de la carte » sur la carte");
            Vector2 auMot = new Vector2(mot.localPosition.x, mot.localPosition.z), centre = (milieu + auMot) / 2f; Rect libre = carte.Vue.Libre;
            float demi = Mathf.Max(DEMI_DES_COUPES_KM, 0.75f * Mathf.Max(Mathf.Abs(auMot.y - milieu.y) / libre.height, Mathf.Abs(auMot.x - milieu.x) / (carte.camera.aspect * libre.width)) + 100f);
            carte.Vue.Changer(carte.camera.aspect); carte.Vue.Centrer(centre, demi); carte.Vue.Amener(centre, libre.center); carte.Vue.Poser(carte.camera, carte.transform);
            PoserLaToile(carte, cabinet); guerre.SuivreLaVue();
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            Vector3 vu = carte.camera.WorldToViewportPoint(mot.position);
            if (!mot.gameObject.activeInHierarchy || vu.z <= 0f || !libre.Contains(vu)) throw Faux("« hors de la carte » ne se lit pas près de " + ou + " : en " + vu + " de l'écran, partie libre " + libre);
            Vector2 pres = milieu + ESTOMPE_KM * versLaTerre;
            if (terrain.CelluleEn(pres.x, pres.y) == 0) throw Faux("échantillon faussé : à " + ESTOMPE_KM + " km de la coupe de " + ou + ", la mer");
            if (terrain.EstompeEn(pres.x, pres.y) < ESTOMPE_MIN) throw Faux("à " + ESTOMPE_KM + " km de la coupe de " + ou + ", la terre ne s'estompe que de " + F(terrain.EstompeEn(pres.x, pres.y)));
            Color papier = Matiere(carte).GetColor("_Papier"); Color[] image = Rendre(carte); Vector2 ecran = Ecran(carte, carte.SurLeSol(pres.x, pres.y, 0f));
            int prises = 0, lus = 0;
            for (int dy = -2; dy <= 2; dy++) for (int dx = -2; dx <= 2; dx++) { lus++; if (Ecart(Pixel(image, ecran + new Vector2(dx, dy)), papier) <= 2f * ECART_DE_COULEUR) prises++; }
            if (prises * 2 < lus) throw Faux("à " + ESTOMPE_KM + " km de la coupe de " + ou + ", la terre n'a pas pris le papier à l'écran : " + prises + " pixels sur " + lus + " (" + Pixel(image, ecran) + " pour " + papier + ")");
            VerifierLesPixels(carte, cabinet, ou);
            Debug.Log("CAPTURE carte parcourue : " + ou + ", coupe en " + milieu + ", « hors de la carte » en " + auMot + ", estompe à " + ESTOMPE_KM + " km : " + F(terrain.EstompeEn(pres.x, pres.y)));
            yield return carte.camera;
        }

        // Le côté coupé le plus proche au sud de la figurine de ce nom servi.
        static Vector4 CoupeAuSudDe(string nom)
        {
            var (carte, _, _) = ScenarioAccueil.Lire();
            var figurine = Villes(carte).Figurines.FirstOrDefault(f => f.ville == nom);
            if (figurine.ville == null) throw Faux("« " + nom + " » n'est ni une ville servie ni un siège posé");
            var ici = new Vector2(figurine.pied.x, figurine.pied.z);
            var au = carte.Terrain.Coupes.Where(c => (c.y + c.w) / 2f < ici.y).OrderBy(c => Vector2.Distance(new Vector2((c.x + c.z) / 2f, (c.y + c.w) / 2f), ici)).Cast<Vector4?>().FirstOrDefault();
            return au ?? throw Faux("aucune coupe au sud de " + nom);
        }

        // L'échantillon de pixels de la vue, dans la partie libre et hors de l'interface : de la terre, de la mer ou du papier, jamais du noir.
        static void VerifierLesPixels(CarteDessinee carte, CabinetDeCarte cabinet, string ou)
        {
            Material m = Matiere(carte); Color mer = m.GetColor("_Mer"), rivage = m.GetColor("_Rivage"), papier = m.GetColor("_Papier");
            Color[] image = Rendre(carte); Rect libre = PixelsLibres(carte);
            int lus = 0, terre = 0, eau = 0, noirs = 0, traits = 0; var exemples = new List<string>();
            for (int y = PAS_DE_LA_GRILLE_PX / 2; y < HAUTEUR; y += PAS_DE_LA_GRILLE_PX)
                for (int x = PAS_DE_LA_GRILLE_PX / 2; x < LARGEUR; x += PAS_DE_LA_GRILLE_PX)
                {
                    var ici = new Vector2(x + .5f, y + .5f);
                    if (!libre.Contains(ici) || cabinet.HorsCarte(ici)) continue;
                    lus++; Color c = Pixel(image, ici);
                    if (Mathf.Max(c.r, Mathf.Max(c.g, c.b)) < NOIR) { noirs++; if (exemples.Count < 6) exemples.Add("noir en " + ici); continue; }
                    if (carte.SolSous(ici) is Vector3 sol && carte.LieuSous(sol) != null) { terre++; continue; }
                    if (Segment(c, rivage, mer) <= ECART_DE_COULEUR || Segment(c, papier, mer) <= ECART_DE_COULEUR) { eau++; continue; }
                    traits++; if (exemples.Count < 6) exemples.Add(c + " en " + ici);
                }
            Debug.Log("CAPTURE carte parcourue : " + ou + ", " + lus + " pixels lus : " + terre + " de terre, " + eau + " de mer ou de papier, " + traits + " de traits, noms ou figurines, " + noirs + " noirs" + (exemples.Count > 0 ? " (" + string.Join(" ; ", exemples) + ")" : ""));
            if (lus == 0) throw Faux(ou + " : échantillon vide, aucun pixel de la vue hors de l'interface");
            if (noirs > 0) throw Faux(ou + " : " + noirs + " pixels noirs dans la vue : " + string.Join(" ; ", exemples));
            if (traits > PART_DES_TRAITS * lus) throw Faux(ou + " : " + traits + " pixels sur " + lus + " ne sont ni terre, ni mer, ni papier : " + string.Join(" ; ", exemples));
        }

        // Le geste de la souris qui glisse de `de` à `a` (pixels), bouton tenu, comme `ParcoursDeCarte` le joue avec la vraie souris.
        static IEnumerator Glisser(CarteDessinee carte, CabinetDeCarte cabinet, Vector2 de, Vector2 a)
        {
            if (cabinet.HorsCarte(de)) throw Faux("le glisser commence sur l'interface en " + de);
            geste.Pas(carte, de, true, true, 0f);
            if (geste.Saisi == null) throw Faux("le bouton enfoncé en " + de + " ne saisit aucun point de la carte");
            for (int i = 1; i <= IMAGES_DU_GLISSER; i++) { yield return null; geste.Pas(carte, Vector2.Lerp(de, a, (float)i / IMAGES_DU_GLISSER), false, true, 0f); }
            yield return null; geste.Pas(carte, a, false, false, 0f); carte.Vue.Poser(carte.camera, carte.transform); PoserLaToile(carte, cabinet);
        }

        static void Molette(CarteDessinee carte, CabinetDeCarte cabinet, Vector2 ici, float crans)
        {
            if (cabinet.HorsCarte(ici)) throw Faux("la molette tourne sur l'interface en " + ici);
            geste.Pas(carte, ici, false, false, crans); carte.Vue.Poser(carte.camera, carte.transform); PoserLaToile(carte, cabinet);
        }

        // La caméra de la carte rendue dans son écran, lu en couleurs comme la photo les écrit.
        static Color[] Rendre(CarteDessinee carte)
        {
            var ecran = carte.camera.targetTexture ?? throw Faux("la caméra de la carte ne rend pas dans un écran"); carte.camera.Render();
            var lu = new Texture2D(ecran.width, ecran.height, TextureFormat.RGBA32, false); var avant = RenderTexture.active; RenderTexture.active = ecran;
            try { lu.ReadPixels(new Rect(0, 0, ecran.width, ecran.height), 0, 0); lu.Apply(false); return lu.GetPixels(); }
            finally { RenderTexture.active = avant; Object.DestroyImmediate(lu); }
        }
        static Color Pixel(Color[] image, Vector2 ici) => image[Mathf.Clamp((int)ici.y, 0, HAUTEUR - 1) * LARGEUR + Mathf.Clamp((int)ici.x, 0, LARGEUR - 1)];
        // Le plus grand écart par composante entre deux couleurs ; puis entre une couleur et le segment de deux autres.
        static float Ecart(Color a, Color b) => Mathf.Max(Mathf.Abs(a.r - b.r), Mathf.Max(Mathf.Abs(a.g - b.g), Mathf.Abs(a.b - b.b)));
        static float Segment(Color c, Color a, Color b)
        {
            Vector3 p = new Vector3(c.r, c.g, c.b), u = new Vector3(a.r, a.g, a.b), v = new Vector3(b.r, b.g, b.b), d = v - u;
            float t = d.sqrMagnitude > 0f ? Mathf.Clamp01(Vector3.Dot(p - u, d) / d.sqrMagnitude) : 0f; Vector3 q = u + t * d;
            return Ecart(c, new Color(q.x, q.y, q.z));
        }

        static Vector2 Ecran(CarteDessinee carte, Vector3 local) => carte.camera.WorldToScreenPoint(carte.transform.TransformPoint(local));
        static Rect PixelsLibres(CarteDessinee carte) { Rect l = carte.Vue.Libre; return new Rect(l.x * LARGEUR, l.y * HAUTEUR, l.width * LARGEUR, l.height * HAUTEUR); }
        static Vector2 Milieu(CarteDessinee carte) => PixelsLibres(carte).center;
        static bool Dans(PointCarte o, float x, float z)
        {
            double mx = o.X + 1000.0 * x, my = o.Y + 1000.0 * z;
            return mx >= ScenarioModesDeCarte.ANATOLIE_X_MIN && mx <= ScenarioModesDeCarte.ANATOLIE_X_MAX && my >= ScenarioModesDeCarte.ANATOLIE_Y_MIN && my <= ScenarioModesDeCarte.ANATOLIE_Y_MAX;
        }
        static VillesDeCarte Villes(CarteDessinee carte) => carte.GetComponent<VillesDeCarte>() ?? throw Faux("pas de villes sur la carte");
        static Material Matiere(CarteDessinee carte) => carte.transform.Find(CarteDessinee.TERRAIN)?.GetComponent<MeshRenderer>().sharedMaterial ?? throw Faux("pas de terrain posé");
        static string[] TextesDuBandeau(CabinetDeCarte cabinet) => cabinet.transform.Find("Cabinet/FORGE · Le cabinet").GetComponentsInChildren<Text>().Select(t => t.text).ToArray();
        static Text Barre(CabinetDeCarte cabinet, string debut) => cabinet.transform.Find("Cabinet/FORGE · Le cabinet").GetComponentsInChildren<Text>().FirstOrDefault(t => t.text.StartsWith(debut, StringComparison.Ordinal));
        // La toile se pose juste derrière le plan proche de la caméra posée : à poser après la caméra, sans quoi un recul la laisse devant ce plan.
        static void PoserLaToile(CarteDessinee carte, CabinetDeCarte cabinet) =>
            cabinet.transform.Find("Cabinet").GetComponent<Canvas>().planeDistance = carte.camera.nearClipPlane + ScenarioAccueil.ECART_DE_PLAN;
        static string F(float v) => v.ToString("0.###", CultureInfo.InvariantCulture);
        static InvalidOperationException Faux(string raison) => new InvalidOperationException("carte parcourue : " + raison);
    }
}
