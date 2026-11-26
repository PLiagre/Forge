using System.Linq;
using NUnit.Framework;
using UnityEngine;

namespace Forge.Pont.Tests {
    // Le joueur parcourt toute sa carte, même quand l'interface en cache une part : le zoom va de toute la carte, tenue
    // dans la partie libre de l'écran, à `DEMI_MIN_KM` ; le glissé et le zoom mènent le point visé, sous le milieu de la
    // partie libre, jusqu'aux bords de la carte servie, et pas au-delà. La caméra est en perspective et regarde à la
    // verticale, nord en haut ; le point du sol sous la souris y reste, à la hauteur où le sol se trouve. La boîte est
    // celle d'une carte de 4 000 × 3 000 km décentrée ; la partie libre de l'accueil est celle d'un écran de 1 920 × 1 080
    // points sous un bandeau de 124 points, à gauche d'un panneau de 584 points.
    public sealed class VueDeCarteTests {
        private const float TOLERANCE = 1e-3f, LOIN = 1e7f;
        private static readonly Bounds BOITE = new Bounds(new Vector3(100, 0, -50), new Vector3(4000, 0, 3000));
        private static readonly Vector2 MILIEU = new Vector2(.5f, .5f);
        private static readonly Rect TOUT = new Rect(0f, 0f, 1f, 1f), ACCUEIL = new Rect(0f, 0f, 1312f / 1920f, (1080f - 124f) / 1080f);

        // Au plus loin, toute la carte tient dans la partie libre : sa hauteur et sa largeur, la plus large des deux la touche.
        private static float DemiMaxAttendu(float aspect, Rect libre) => Mathf.Max(BOITE.extents.z / libre.height, BOITE.extents.x / (aspect * libre.width));
        private static float DemiMaxAttendu(float aspect) => DemiMaxAttendu(aspect, TOUT);
        private static readonly float DEMI_CHAMP = Mathf.Tan(VueDeCarte.CHAMP * Mathf.Deg2Rad / 2f);
        private static readonly float[] HAUTEURS = { 0f, 2f, 4.5f }; // le niveau de la mer, une colline, un sommet des Alpes

        // Une vraie caméra, posée par la vue sur une carte décalée de l'origine, qui rend 1920 × 1080 pixels.
        private sealed class CameraTemoin : System.IDisposable {
            public readonly Camera Camera; public readonly Transform Carte; private readonly RenderTexture ecran;
            public CameraTemoin() {
                Carte = new GameObject("carte témoin").transform; Carte.position = new Vector3(1000f, 50f, -2000f);
                Camera = new GameObject("caméra témoin").AddComponent<Camera>(); ecran = new RenderTexture(1920, 1080, 16); Camera.targetTexture = ecran;
            }
            public void Poser(VueDeCarte v) { v.Changer(Camera.aspect); v.Poser(Camera, Carte); }
            // Le point du sol (x, hauteur, z) de la carte, en pixels de l'écran.
            public Vector2 AEcran(Vector2 sol, float hauteur) => Camera.WorldToScreenPoint(Carte.TransformPoint(new Vector3(sol.x, hauteur, sol.y)));
            // Le même point en parts de la fenêtre, depuis le bas à gauche.
            public Vector2 AFenetre(Vector2 sol) => Camera.WorldToViewportPoint(Carte.TransformPoint(new Vector3(sol.x, 0f, sol.y)));
            public void Dispose() { Camera.targetTexture = null; Object.DestroyImmediate(ecran); Object.DestroyImmediate(Camera.gameObject); Object.DestroyImmediate(Carte.gameObject); }
        }

        // La carte se lit droite, nord en haut, sans cadre penché : de toute la carte au plus près, la caméra regarde
        // à la verticale, et le rectangle visé est exactement celui que l'écran montre au niveau de la mer.
        [Test] public void La_camera_regarde_a_la_verticale_a_toute_echelle() {
            var v = new VueDeCarte(BOITE, 16f / 9f); int crans = 0;
            using var temoin = new CameraTemoin();
            for (bool fin = false; !fin; crans++) {
                fin = v.Echelle <= v.EchelleMin; string quand = "échelle " + v.Echelle;
                Assert.Less((v.Regard - Vector3.down).magnitude, 1e-6f, quand + " : la caméra ne regarde pas à la verticale : " + v.Regard);
                Assert.Less((v.Haut - Vector3.forward).magnitude, 1e-6f, quand + " : le haut de l'écran n'est pas le nord : " + v.Haut);
                Assert.AreEqual(v.Demi / DEMI_CHAMP, v.Distance, 1e-2f, quand + " : la distance n'est pas celle d'où la vue remplit le champ");
                Assert.Less((new Vector2(v.Position.x, v.Position.z) - v.Centre).magnitude, TOLERANCE, quand + " : la caméra n'est pas à l'aplomb du point visé");
                Assert.Less((v.PointSous(new Vector2(0f, 0f)) - (v.Centre - new Vector2(v.DemiLargeur, v.Demi))).magnitude, TOLERANCE, quand + " : le coin sud-ouest de l'écran");
                Assert.Less((v.PointSous(new Vector2(1f, 1f)) - (v.Centre + new Vector2(v.DemiLargeur, v.Demi))).magnitude, TOLERANCE, quand + " : le coin nord-est de l'écran");
                temoin.Poser(v);
                Assert.Less(Vector3.Angle(temoin.Camera.transform.forward, Vector3.down), 1e-3f, quand + " : la caméra posée penche de " + Vector3.Angle(temoin.Camera.transform.forward, Vector3.down) + "°");
                Assert.Less(Vector3.Angle(temoin.Camera.transform.up, Vector3.forward), 1e-3f, quand + " : la caméra posée tourne le nord hors du haut de l'écran");
                v.Zoomer(1, MILIEU);
            }
            Assert.Greater(crans, 10, "échantillon vide : la vue n'a pas parcouru le zoom");
        }

        // Où qu'elle soit sur l'écran, coins compris, et quel que soit le relief sous elle, la souris garde son point du
        // sol quand la molette rapproche la vue, de loin comme de près.
        [Test] public void Le_point_sous_la_souris_reste_sous_elle_partout() {
            int essais = 0;
            foreach (float echelle in new[] { .6f, .15f, 0f }) foreach (float hauteur in HAUTEURS)
                for (int i = 0; i <= 4; i++) for (int j = 0; j <= 4; j++) {
                    var v = new VueDeCarte(BOITE, 16f / 9f); v.Centrer(new Vector2(BOITE.center.x, BOITE.center.z), Mathf.Max(v.DemiMax * echelle, VueDeCarte.DEMI_MIN_KM / VueDeCarte.PAS_DE_ZOOM));
                    var ancre = new Vector2(i / 4f, j / 4f); Vector2 avant = v.PointSous(ancre, hauteur); float demi = v.Demi;
                    v.Zoomer(1, ancre, hauteur); essais++;
                    Assert.Less(v.Demi, demi - 1e-3f, "le cran n'a pas rapproché la vue");
                    Assert.Less((v.PointSous(ancre, hauteur) - avant).magnitude, TOLERANCE, "échelle " + echelle + ", hauteur " + hauteur + " km, souris en " + ancre + " : le point a bougé de " + (v.PointSous(ancre, hauteur) - avant).magnitude + " km");
                }
            Assert.AreEqual(3 * 3 * 25, essais);
            // Contre-épreuve : au coin de l'écran, le relief change le point visé ; la hauteur du sol compte dans l'épreuve.
            var temoin = new VueDeCarte(BOITE, 16f / 9f); temoin.Zoomer(8, MILIEU);
            Assert.Greater((temoin.PointSous(Vector2.one, 4.5f) - temoin.PointSous(Vector2.one, 0f)).magnitude, 1f, "échantillon vide : la hauteur du sol ne change rien au coin de l'écran");
        }

        // Glisser de cent pixels déplace le sol de cent pixels, à la souris (le point saisi, à sa hauteur) comme au geste
        // mesuré à plat, en x et en y, au centre de l'écran comme près d'un bord.
        [Test] public void Glisser_de_cent_pixels_deplace_le_sol_de_cent_pixels() {
            using var temoin = new CameraTemoin(); var taille = new Vector2(1920f, 1080f); int essais = 0;
            foreach (Vector2 ici in new[] { new Vector2(960f, 540f), new Vector2(200f, 900f), new Vector2(1700f, 150f) })
                foreach (Vector2 pas in new[] { new Vector2(100f, 0f), new Vector2(0f, -100f), new Vector2(-100f, 100f) }) {
                    foreach (float hauteur in HAUTEURS) {
                        var v = new VueDeCarte(BOITE, taille.x / taille.y); v.Zoomer(8, MILIEU); temoin.Poser(v);
                        Vector2 saisi = v.PointSous(ici / taille, hauteur); Assert.Less((temoin.AEcran(saisi, hauteur) - ici).magnitude, .5f, "le point saisi n'est pas sous la souris");
                        v.Glisser(ici / taille, (ici + pas) / taille, hauteur); temoin.Poser(v); essais++;
                        Assert.Less((temoin.AEcran(saisi, hauteur) - (ici + pas)).magnitude, .5f, "à la souris, de " + ici + " par " + pas + ", hauteur " + hauteur + " : le sol est en " + temoin.AEcran(saisi, hauteur));
                    }
                    var plat = new VueDeCarte(BOITE, taille.x / taille.y); plat.Zoomer(8, MILIEU); temoin.Poser(plat);
                    Vector2 sol = plat.PointSous(ici / taille); plat.Glisser(pas, taille.y); temoin.Poser(plat); essais++;
                    Assert.Less((temoin.AEcran(sol, 0f) - (ici + pas)).magnitude, .5f, "à plat, de " + ici + " par " + pas + " : le sol est en " + temoin.AEcran(sol, 0f));
                }
            Assert.AreEqual(9 * 4, essais);
        }

        // Au plus près, on lit une province et ses lieux : un lieu de 1 000 km² au centre de l'écran en tient au moins
        // le quart de la hauteur ; vu de toute la carte, il en tient bien moins.
        [Test] public void Au_plus_pres_un_lieu_de_1000_km2_tient_un_quart_de_la_hauteur() {
            using var temoin = new CameraTemoin(); float cote = Mathf.Sqrt(1000f);
            float Hauteur(VueDeCarte v) {
                temoin.Poser(v); var ys = new[] { new Vector2(-1, -1), new Vector2(1, -1), new Vector2(1, 1), new Vector2(-1, 1) }
                    .Select(c => temoin.AEcran(v.Centre + c * (cote / 2f), 0f).y).ToArray();
                return (ys.Max() - ys.Min()) / temoin.Camera.pixelHeight;
            }
            var pres = new VueDeCarte(BOITE, 16f / 9f); pres.Zoomer(1000, MILIEU);
            Assert.AreEqual(VueDeCarte.DEMI_MIN_KM, pres.Demi, TOLERANCE, "la vue n'est pas au plus près");
            Assert.GreaterOrEqual(Hauteur(pres), .25f, "au plus près, le lieu de 1 000 km² ne tient que " + Hauteur(pres) + " de la hauteur");
            float loin = Hauteur(new VueDeCarte(BOITE, 16f / 9f));
            Assert.Less(loin, .25f / 10f, "contre-épreuve : de toute la carte, le lieu tient " + loin + " de la hauteur");
        }

        // Le point visé, sous le milieu de la partie libre, ne sort jamais de la carte.
        private static void ViseDansLaCarte(VueDeCarte v, string quand) {
            Vector2 p = v.Vise;
            Assert.IsTrue(p.x >= BOITE.min.x - TOLERANCE && p.x <= BOITE.max.x + TOLERANCE && p.y >= BOITE.min.z - TOLERANCE && p.y <= BOITE.max.z + TOLERANCE, quand + " : le point visé sort de la carte : " + p);
        }

        // Le jeu s'ouvre sur la carte qui remplit l'écran, centrée ; on peut encore reculer jusqu'à toute la carte.
        [Test] public void La_vue_s_ouvre_sur_la_carte_qui_remplit_l_ecran() {
            var v = new VueDeCarte(BOITE, 16f / 9f);
            Assert.AreEqual(new Vector2(BOITE.center.x, BOITE.center.z), v.Centre);
            Assert.AreEqual(Mathf.Min(BOITE.extents.z, BOITE.extents.x / (16f / 9f)), v.Demi, TOLERANCE, "la carte ne remplit pas l'écran sur son axe le plus serré");
            Assert.Less(v.Echelle, 1f, "à l'ouverture, la vue est déjà au plus loin : on ne peut pas reculer jusqu'à toute la carte");
            Assert.AreEqual(TOUT, v.Libre, "sans partie libre donnée, tout l'écran est libre");
            // Tant que rien ne l'a menée, la vue d'ouverture suit la forme de la fenêtre.
            foreach (float aspect in new[] { 0.5f, 4f / 3f, 2.4f }) { v.Changer(aspect); Assert.AreEqual(Mathf.Min(BOITE.extents.z, BOITE.extents.x / aspect), v.Demi, TOLERANCE, "à l'ouverture, en " + aspect + ", la carte ne remplit pas l'écran"); }
        }

        [Test] public void Le_zoom_est_borne_des_deux_cotes() {
            var v = new VueDeCarte(BOITE, 16f / 9f);
            v.Zoomer(1000, MILIEU);
            Assert.AreEqual(VueDeCarte.DEMI_MIN_KM, v.Demi, TOLERANCE, "au plus près");
            ViseDansLaCarte(v, "au plus près");
            v.Zoomer(-1000, MILIEU);
            Assert.AreEqual(1f, v.Echelle, "au plus loin"); Assert.AreEqual(DemiMaxAttendu(16f / 9f), v.Demi, TOLERANCE, "au plus loin");
            Assert.Less((v.Vise - new Vector2(BOITE.center.x, BOITE.center.z)).magnitude, TOLERANCE, "au plus loin, la vue n'est pas recentrée");
        }

        [Test] public void Un_cran_rapproche_du_pas_de_zoom() {
            var v = new VueDeCarte(BOITE, 16f / 9f); float avant = v.Demi;
            v.Zoomer(1, MILIEU); Assert.AreEqual(avant * VueDeCarte.PAS_DE_ZOOM, v.Demi, TOLERANCE);
            v.Zoomer(-1, MILIEU); Assert.AreEqual(avant, v.Demi, TOLERANCE);
        }

        [Test] public void Le_point_sous_la_souris_reste_sous_la_souris() {
            var v = new VueDeCarte(BOITE, 16f / 9f); v.Zoomer(8, MILIEU);
            var ancre = new Vector2(.7f, .35f); Vector2 avant = v.PointSous(ancre);
            v.Zoomer(3, ancre);
            Assert.Less((v.PointSous(ancre) - avant).magnitude, TOLERANCE, "le point sous la souris a bougé : " + v.PointSous(ancre) + " pour " + avant);
        }

        // L'accueil tient la droite de l'écran : glissée vers l'est, la carte amène son bord est à gauche du panneau,
        // sous le milieu de la partie libre, et l'Orient se lit au lieu de rester sous le panneau.
        [Test] public void Avec_l_accueil_ouvert_le_bord_est_de_la_carte_vient_a_gauche_du_panneau() {
            using var temoin = new CameraTemoin(); int essais = 0;
            foreach (float crans in new[] { 2f, 6f, 12f }) {
                var v = new VueDeCarte(BOITE, 16f / 9f); v.Liberer(ACCUEIL); v.Zoomer(crans, ACCUEIL.center);
                v.Glisser(new Vector2(-LOIN, 0f), 1080f); temoin.Poser(v); essais++;
                Assert.AreEqual(BOITE.max.x, v.Vise.x, TOLERANCE, crans + " crans : le point visé ne va pas jusqu'au bord est de la carte");
                float est = temoin.AEcran(new Vector2(BOITE.max.x, v.Vise.y), 0f).x;
                Assert.AreEqual(1312f / 2f, est, .5f, crans + " crans : le bord est de la carte est à " + est + " px, pas au milieu de la partie libre");
                Assert.Less(est, 1312f, crans + " crans : le bord est de la carte reste sous le panneau");
            }
            Assert.AreEqual(3, essais, "échantillon vide");
        }

        // Amener le coin sud-est de la carte au milieu de la partie libre, à la souris : il y vient, et pas plus loin.
        [Test] public void Le_coin_sud_est_se_pose_au_milieu_de_la_partie_libre() {
            using var temoin = new CameraTemoin(); var coin = new Vector2(BOITE.max.x, BOITE.min.z); var pixels = new Vector2(1920f, 1080f);
            var v = new VueDeCarte(BOITE, 16f / 9f); v.Liberer(ACCUEIL); v.Zoomer(8, ACCUEIL.center);
            v.Amener(coin, ACCUEIL.center); temoin.Poser(v);
            Assert.Less((v.Vise - coin).magnitude, TOLERANCE, "le coin sud-est n'est pas sous le milieu de la partie libre : " + v.Vise);
            Assert.Less((temoin.AEcran(coin, 0f) - Vector2.Scale(ACCUEIL.center, pixels)).magnitude, .5f, "le coin sud-est est à l'écran en " + temoin.AEcran(coin, 0f));
            // Au-delà du coin, la vue ne suit plus : le point visé reste sur le coin.
            v.Amener(coin + new Vector2(500f, -500f), ACCUEIL.center);
            Assert.Less((v.Vise - coin).magnitude, TOLERANCE, "le point visé sort de la carte : " + v.Vise);
        }

        // Au plus loin, quelle que soit la forme de la fenêtre et la part qu'en prend l'interface, et d'où qu'on recule,
        // les quatre coins de la carte tombent dans la partie libre, et la carte la touche sur son axe le plus serré.
        [Test] public void Au_plus_loin_la_carte_tient_dans_la_partie_libre() {
            int coins = 0;
            foreach (Rect libre in new[] { TOUT, ACCUEIL }) foreach (float aspect in new[] { 0.5f, 1f, 4f / 3f, 16f / 9f, 2.4f }) foreach (Vector2 depart in new[] { Vector2.zero, Vector2.one }) {
                using var temoin = new CameraTemoin(); var v = new VueDeCarte(BOITE, aspect); v.Liberer(libre);
                v.Zoomer(8, libre.center); v.Amener(new Vector2(depart.x > 0 ? BOITE.max.x : BOITE.min.x, depart.y > 0 ? BOITE.max.z : BOITE.min.z), libre.center);
                v.Zoomer(-1000, libre.center); v.Poser(temoin.Camera, temoin.Carte); temoin.Camera.aspect = aspect; float touche = 0f; string quand = "aspect " + aspect + ", libre " + libre + ", depuis " + depart;
                Assert.AreEqual(DemiMaxAttendu(aspect, libre), v.Demi, TOLERANCE, quand + " : la vue n'est pas au plus loin");
                foreach (var c in new[] { Vector2.zero, Vector2.right, Vector2.one, Vector2.up }) {
                    Vector2 f = temoin.AFenetre(new Vector2(Mathf.Lerp(BOITE.min.x, BOITE.max.x, c.x), Mathf.Lerp(BOITE.min.z, BOITE.max.z, c.y))); coins++;
                    Assert.IsTrue(f.x >= libre.xMin - 1e-4f && f.x <= libre.xMax + 1e-4f && f.y >= libre.yMin - 1e-4f && f.y <= libre.yMax + 1e-4f, quand + " : le coin " + c + " de la carte tombe hors de la partie libre, en " + f);
                    touche = Mathf.Max(touche, Mathf.Abs(f.x - libre.center.x) / (libre.width / 2f), Mathf.Abs(f.y - libre.center.y) / (libre.height / 2f));
                }
                Assert.AreEqual(1f, touche, 1e-3f, quand + " : au plus loin, la carte ne touche pas le bord de la partie libre");
            }
            Assert.AreEqual(2 * 5 * 2 * 4, coins, "échantillon vide");
            // Contre-épreuve : la vue d'ouverture, qui remplit l'écran, met le coin est de la carte sous le panneau de l'accueil.
            using var autre = new CameraTemoin(); var ouverte = new VueDeCarte(BOITE, 16f / 9f); ouverte.Liberer(ACCUEIL); autre.Poser(ouverte);
            Assert.Greater(autre.AFenetre(new Vector2(BOITE.max.x, BOITE.center.z)).x, ACCUEIL.xMax, "la contre-épreuve ne cache rien sous le panneau");
        }

        // Quand l'accueil se ferme, la vue ne saute pas : même demi-hauteur, même centre ; seules ses bornes changent.
        // Une partie libre vide ou hors de la fenêtre est refusée.
        [Test] public void Quand_la_partie_libre_change_la_vue_garde_sa_demi_hauteur() {
            var v = new VueDeCarte(BOITE, 16f / 9f); v.Liberer(ACCUEIL); v.Zoomer(6, ACCUEIL.center); v.Glisser(new Vector2(-300f, 120f), 1080f);
            float demi = v.Demi; Vector2 centre = v.Centre;
            Assert.IsTrue(v.Liberer(new Rect(0f, 0f, 1f, ACCUEIL.height)), "la partie libre n'a pas changé");
            Assert.AreEqual(demi, v.Demi, TOLERANCE, "la vue a changé de demi-hauteur"); Assert.Less((v.Centre - centre).magnitude, TOLERANCE, "la vue a sauté");
            Assert.IsFalse(v.Liberer(new Rect(0f, 0f, 1f, ACCUEIL.height)), "la même partie libre change la vue");
            foreach (Rect fausse in new[] { new Rect(0f, 0f, 0f, 1f), new Rect(0f, 0f, 1f, -1f), new Rect(.5f, 0f, 1f, 1f), new Rect(-.1f, 0f, 1f, 1f) })
                Assert.Throws<System.ArgumentException>(() => v.Liberer(fausse), "partie libre acceptée : " + fausse);
        }

        // En reculant vers le plus loin, le point visé revient au milieu de la carte sans jamais s'en écarter ni sauter.
        [Test] public void En_reculant_la_carte_revient_au_milieu_de_la_partie_libre() {
            var v = new VueDeCarte(BOITE, 16f / 9f); v.Liberer(ACCUEIL); v.Zoomer(1000, ACCUEIL.center);
            var coin = new Vector2(BOITE.max.x, BOITE.min.z); var milieu = new Vector2(BOITE.center.x, BOITE.center.z); v.Amener(coin, ACCUEIL.center);
            float ecart = (v.Vise - milieu).magnitude; int crans = 0;
            while (v.Echelle < 1f) {
                Vector2 avant = v.Vise; v.Zoomer(-1, ACCUEIL.center); crans++;
                float apres = (v.Vise - milieu).magnitude;
                Assert.LessOrEqual(apres, ecart + TOLERANCE, "cran " + crans + " : le point visé s'écarte du milieu de la carte");
                Assert.Less((v.Vise - avant).magnitude, v.Demi, "cran " + crans + " : la vue saute de " + (v.Vise - avant).magnitude + " km");
                ecart = apres;
            }
            Assert.Greater(crans, 10, "échantillon vide : la vue n'a pas reculé");
            Assert.Less(ecart, TOLERANCE, "au plus loin, la carte n'est pas au milieu de la partie libre");
        }

        [Test] public void Le_point_saisi_reste_sous_la_souris_a_la_hauteur_du_sol() {
            var v = new VueDeCarte(BOITE, 16f / 9f); v.Zoomer(10, MILIEU);
            // La souris finit loin du milieu de l'écran : à la verticale, c'est là que la hauteur du sol déplace le point visé.
            Vector2 de = new Vector2(.4f, .3f), a = new Vector2(.9f, .85f); const float HAUT = 9f;
            // Glissé : le point du sol saisi, à 9 km de haut, vient sous la souris.
            Vector2 saisi = v.PointSous(de, HAUT); Vector2 centre = v.Centre; v.Glisser(de, a, HAUT);
            Assert.Less((v.PointSous(a, HAUT) - saisi).magnitude, TOLERANCE, "le point saisi n'est pas sous la souris"); Assert.Greater((v.Centre - centre).magnitude, 10f, "la vue n'a pas bougé");
            // Contre-épreuve : lu au niveau de la mer, ce n'est pas le même point ; le relief compte.
            Assert.Greater((v.PointSous(a, 0f) - saisi).magnitude, 1f, "échantillon vide : la hauteur du sol ne change rien au point visé");
            // Molette : le point du sol sous la souris, à sa hauteur, reste sous elle quand la caméra s'approche.
            Vector2 sous = v.PointSous(a, HAUT); float demi = v.Demi; v.Zoomer(4, a, HAUT);
            Assert.Less((v.PointSous(a, HAUT) - sous).magnitude, TOLERANCE, "le point sous la souris a bougé au zoom"); Assert.Less(v.Demi, demi, "la vue ne s'est pas approchée");
            Assert.Greater((v.PointSous(a, 0f) - sous).magnitude, 1f, "échantillon vide : au zoom, la hauteur du sol ne change rien");
            // Amener un point sous une ancre, puis le relire.
            var voulu = new Vector2(250f, -120f); v.Amener(voulu, new Vector2(.2f, .8f), 3f); Assert.Less((v.PointSous(new Vector2(.2f, .8f), 3f) - voulu).magnitude, TOLERANCE);
        }

        [Test] public void Le_glisse_suit_la_souris_puis_s_arrete_aux_bords() {
            var v = new VueDeCarte(BOITE, 16f / 9f); v.Zoomer(10, MILIEU);
            Vector2 avant = v.Centre; float kmParPixel = 2 * v.Demi / 900f;
            v.Glisser(new Vector2(30, -20), 900f);
            Assert.Less((v.Centre - (avant - new Vector2(30, -20) * kmParPixel)).magnitude, TOLERANCE, "la vue n'a pas suivi le glissé");
            foreach (var (glisse, bord) in new[] { (new Vector2(LOIN, 0), "ouest"), (new Vector2(-LOIN, 0), "est"), (new Vector2(0, LOIN), "sud"), (new Vector2(0, -LOIN), "nord") }) {
                v.Glisser(glisse, 900f); ViseDansLaCarte(v, "glissé vers le " + bord);
                Vector2 p = v.Vise;
                float atteint = bord == "ouest" ? p.x - BOITE.min.x : bord == "est" ? p.x - BOITE.max.x : bord == "sud" ? p.y - BOITE.min.z : p.y - BOITE.max.z;
                Assert.AreEqual(0f, atteint, TOLERANCE, "glissé vers le " + bord + " : le point visé ne s'arrête pas au bord de la carte");
            }
        }

        // Une fenêtre très large : au plus loin, la carte tient en hauteur, centrée ; à l'ouverture, elle remplit la
        // largeur, et le glissé mène le point visé jusqu'au bord sud, la largeur restant centrée.
        [Test] public void Une_fenetre_tres_large_tient_la_carte_en_hauteur() {
            var v = new VueDeCarte(BOITE, 10f);
            Assert.AreEqual(BOITE.size.x, 2 * v.DemiLargeur, TOLERANCE, "à l'ouverture, la vue n'a pas la largeur de la carte");
            v.Glisser(new Vector2(LOIN, LOIN), 900f);
            Assert.AreEqual(BOITE.min.z, v.Vise.y, TOLERANCE, "le glissé ne mène pas au bord sud"); Assert.AreEqual(BOITE.center.x, v.Vise.x, TOLERANCE, "la largeur n'est plus centrée");
            v.Zoomer(-1000, MILIEU);
            Assert.AreEqual(BOITE.size.z, 2 * v.Demi, TOLERANCE, "au plus loin, la vue n'a pas la hauteur de la carte");
            Assert.Less((v.Vise - new Vector2(BOITE.center.x, BOITE.center.z)).magnitude, TOLERANCE, "au plus loin, la carte n'est pas centrée");
        }

        [Test] public void La_forme_de_la_fenetre_garde_l_echelle() {
            var v = new VueDeCarte(BOITE, 16f / 9f); v.Zoomer(-1000, MILIEU);
            foreach (float aspect in new[] { 4f / 3f, 0.5f, 3f }) { v.Changer(aspect); Assert.AreEqual(DemiMaxAttendu(aspect), v.Demi, TOLERANCE, "toute la carte à " + aspect); ViseDansLaCarte(v, "aspect " + aspect); }
            v.Zoomer(6, MILIEU); float echelle = v.Echelle; v.Changer(16f / 9f);
            Assert.AreEqual(echelle, v.Echelle, "l'échelle change avec la fenêtre"); ViseDansLaCarte(v, "zoomée puis 16:9");
        }

        // Un centrage demandé est tenu tant que le point visé reste dans la carte ; un centrage hors de la carte
        // ramène le point visé au bord le plus proche.
        [Test] public void Le_centrage_demande_reste_dans_la_carte() {
            var v = new VueDeCarte(BOITE, 16f / 9f); var voulu = new Vector2(400f, 200f);
            v.Centrer(voulu, 200f); Assert.AreEqual(voulu, v.Centre); Assert.AreEqual(200f, v.Demi, TOLERANCE); ViseDansLaCarte(v, "centrage décentré");
            var coin = new Vector2(BOITE.min.x, BOITE.min.z);
            v.Centrer(coin, 200f); Assert.Less((v.Vise - coin).magnitude, TOLERANCE, "le centrage sur le coin sud-ouest n'y est pas tenu : " + v.Vise);
            v.Centrer(coin - new Vector2(800f, 800f), 200f); ViseDansLaCarte(v, "centrage hors de la carte");
            Assert.Less((v.Vise - coin).magnitude, TOLERANCE, "le centrage hors de la carte n'est pas ramené au coin : " + v.Vise);
        }

        [Test] public void Le_jeu_s_ouvre_sur_la_carte_quand_on_le_demande() {
            Assert.IsTrue(OuvertureDeLaCarte.Demandee(new[] { "Forge.exe", "-forgeCell", "1175", OuvertureDeLaCarte.ARGUMENT }));
            Assert.IsFalse(OuvertureDeLaCarte.Demandee(new[] { "Forge.exe", "-forgeCell", "1175" }));
            Assert.IsFalse(OuvertureDeLaCarte.Demandee(null));
        }
    }
}
