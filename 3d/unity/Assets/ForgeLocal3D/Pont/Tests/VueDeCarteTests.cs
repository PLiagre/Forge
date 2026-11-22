using System.Linq;
using NUnit.Framework;
using UnityEngine;

namespace Forge.Pont.Tests {
    // Le joueur parcourt sa carte sans en sortir : le zoom va de toute la carte à `DEMI_MIN_KM`, le glissé et
    // le zoom s'arrêtent aux bords de la carte servie. La caméra est en perspective et regarde à la verticale, nord en
    // haut ; le point du sol sous la souris y reste, à la hauteur où le sol se trouve. La boîte est celle d'une carte de
    // 4 000 × 3 000 km décentrée.
    public sealed class VueDeCarteTests {
        private const float TOLERANCE = 1e-3f, LOIN = 1e7f;
        private static readonly Bounds BOITE = new Bounds(new Vector3(100, 0, -50), new Vector3(4000, 0, 3000));
        private static readonly Vector2 MILIEU = new Vector2(.5f, .5f);

        // Vue d'en haut, la carte se cadre sur sa hauteur ou sa largeur, avec la marge du cadre.
        private static float DemiMaxAttendu(float aspect) => Mathf.Max(BOITE.extents.z, BOITE.extents.x / aspect) * VueDeCarte.MARGE;
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

        // Ce que la vue montre, en (x, z) : gauche, bas, droite, haut.
        private static Vector4 Montre(VueDeCarte v) =>
            new Vector4(v.Centre.x - v.DemiLargeur, v.Centre.y - v.Demi, v.Centre.x + v.DemiLargeur, v.Centre.y + v.Demi);

        private static void DansLaCarte(VueDeCarte v, string quand) {
            Vector4 m = Montre(v);
            if (2 * v.DemiLargeur < BOITE.size.x)
                Assert.IsTrue(m.x >= BOITE.min.x - TOLERANCE && m.z <= BOITE.max.x + TOLERANCE, quand + " : la vue sort de la carte en x : " + m);
            else Assert.AreEqual(BOITE.center.x, v.Centre.x, TOLERANCE, quand + " : plus large que la carte, la vue n'est pas centrée en x");
            if (2 * v.Demi < BOITE.size.z)
                Assert.IsTrue(m.y >= BOITE.min.z - TOLERANCE && m.w <= BOITE.max.z + TOLERANCE, quand + " : la vue sort de la carte en z : " + m);
            else Assert.AreEqual(BOITE.center.z, v.Centre.y, TOLERANCE, quand + " : plus haute que la carte, la vue n'est pas centrée en z");
        }

        [Test] public void La_vue_s_ouvre_sur_toute_la_carte() {
            var v = new VueDeCarte(BOITE, 16f / 9f);
            Assert.AreEqual(1f, v.Echelle); Assert.AreEqual(new Vector2(BOITE.center.x, BOITE.center.z), v.Centre);
            Assert.AreEqual(DemiMaxAttendu(16f / 9f), v.Demi, TOLERANCE);
        }

        [Test] public void Le_zoom_est_borne_des_deux_cotes() {
            var v = new VueDeCarte(BOITE, 16f / 9f);
            v.Zoomer(1000, MILIEU);
            Assert.AreEqual(VueDeCarte.DEMI_MIN_KM, v.Demi, TOLERANCE, "au plus près");
            DansLaCarte(v, "au plus près");
            v.Zoomer(-1000, MILIEU);
            Assert.AreEqual(1f, v.Echelle, "au plus loin"); Assert.AreEqual(DemiMaxAttendu(16f / 9f), v.Demi, TOLERANCE, "au plus loin");
            Assert.AreEqual(new Vector2(BOITE.center.x, BOITE.center.z), v.Centre, "au plus loin, la vue n'est pas recentrée");
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

        // Quelle que soit la forme de la fenêtre, les quatre coins de la carte sont dans la vue du départ, et la carte
        // la remplit sur son axe le plus serré à la marge du cadre près.
        [Test] public void Toute_la_carte_tient_dans_la_vue_du_depart() {
            foreach (float aspect in new[] { 0.5f, 1f, 1.2f, 4f / 3f, 1.4f, 1.5f, 16f / 9f, 2.4f, 3f }) {
                var v = new VueDeCarte(BOITE, aspect); float plusLarge = 0f, plusHaut = 0f;
                foreach (var (x, z) in new[] { (BOITE.min.x, BOITE.min.z), (BOITE.max.x, BOITE.min.z), (BOITE.max.x, BOITE.max.z), (BOITE.min.x, BOITE.max.z) }) {
                    Vector3 vers = new Vector3(x, 0f, z) - v.Position; float profondeur = Vector3.Dot(vers, v.Regard);
                    float enLarge = Vector3.Dot(vers, Vector3.right) / (profondeur * DEMI_CHAMP * aspect), enHaut = Vector3.Dot(vers, v.Haut) / (profondeur * DEMI_CHAMP);
                    Assert.IsTrue(profondeur > 0 && Mathf.Abs(enLarge) <= 1f && Mathf.Abs(enHaut) <= 1f, "aspect " + aspect + " : le coin (" + x + ", " + z + ") est hors de la vue : " + enLarge + ", " + enHaut);
                    plusLarge = Mathf.Max(plusLarge, Mathf.Abs(enLarge)); plusHaut = Mathf.Max(plusHaut, Mathf.Abs(enHaut));
                }
                Assert.AreEqual(1f / VueDeCarte.MARGE, Mathf.Max(plusLarge, plusHaut), 1e-3f, "aspect " + aspect + " : la carte ne remplit pas la vue à la marge près");
            }
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
                v.Glisser(glisse, 900f); DansLaCarte(v, "glissé vers le " + bord);
                Vector4 m = Montre(v);
                float atteint = bord == "ouest" ? m.x - BOITE.min.x : bord == "est" ? m.z - BOITE.max.x : bord == "sud" ? m.y - BOITE.min.z : m.w - BOITE.max.z;
                Assert.AreEqual(0f, atteint, TOLERANCE, "glissé vers le " + bord + " : la vue ne s'arrête pas au bord de la carte");
            }
        }

        [Test] public void Plus_large_que_la_carte_la_vue_se_centre_sur_elle() {
            var v = new VueDeCarte(BOITE, 10f); v.Zoomer(3, MILIEU); v.Glisser(new Vector2(LOIN, LOIN), 900f);
            Assert.Greater(2 * v.DemiLargeur, BOITE.size.x, "le cas n'est pas celui d'une vue plus large que la carte");
            Assert.Less(2 * v.Demi, BOITE.size.z, "le cas n'est pas celui d'une vue moins haute que la carte");
            DansLaCarte(v, "fenêtre très large");
        }

        [Test] public void La_forme_de_la_fenetre_garde_l_echelle() {
            var v = new VueDeCarte(BOITE, 16f / 9f);
            foreach (float aspect in new[] { 4f / 3f, 0.5f, 3f }) { v.Changer(aspect); Assert.AreEqual(DemiMaxAttendu(aspect), v.Demi, TOLERANCE, "toute la carte à " + aspect); DansLaCarte(v, "aspect " + aspect); }
            v.Zoomer(6, MILIEU); float echelle = v.Echelle; v.Changer(16f / 9f);
            Assert.AreEqual(echelle, v.Echelle, "l'échelle change avec la fenêtre"); DansLaCarte(v, "zoomée puis 16:9");
        }

        [Test] public void Le_centrage_demande_reste_dans_la_carte() {
            var v = new VueDeCarte(BOITE, 16f / 9f); var voulu = new Vector2(400f, 200f);
            v.Centrer(voulu, 200f); Assert.AreEqual(voulu, v.Centre); Assert.AreEqual(200f, v.Demi, TOLERANCE); DansLaCarte(v, "centrage décentré");
            v.Centrer(new Vector2(BOITE.min.x, BOITE.min.z), 200f); DansLaCarte(v, "centrage près d'un bord");
            Vector4 m = Montre(v); Assert.AreEqual(BOITE.min.x, m.x, TOLERANCE, "bord ouest"); Assert.AreEqual(BOITE.min.z, m.y, TOLERANCE, "bord sud");
            Assert.AreNotEqual(new Vector2(BOITE.min.x, BOITE.min.z), v.Centre, "le centre demandé hors carte a été gardé");
        }

        [Test] public void Le_jeu_s_ouvre_sur_la_carte_quand_on_le_demande() {
            Assert.IsTrue(OuvertureDeLaCarte.Demandee(new[] { "Forge.exe", "-forgeCell", "1175", OuvertureDeLaCarte.ARGUMENT }));
            Assert.IsFalse(OuvertureDeLaCarte.Demandee(new[] { "Forge.exe", "-forgeCell", "1175" }));
            Assert.IsFalse(OuvertureDeLaCarte.Demandee(null));
        }
    }
}
