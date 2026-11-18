using NUnit.Framework;
using UnityEngine;

namespace Forge.Pont.Tests {
    // Le joueur parcourt sa carte sans en sortir : le zoom va de toute la carte à `DEMI_MIN_KM`, le glissé et
    // le zoom s'arrêtent aux bords de la carte servie. La caméra est en perspective et s'incline en s'approchant ;
    // le point du sol sous la souris y reste, à la hauteur où le sol se trouve. La boîte est celle d'une carte de
    // 4 000 × 3 000 km décentrée.
    public sealed class VueDeCarteTests {
        private const float TOLERANCE = 1e-3f, LOIN = 1e7f;
        private static readonly Bounds BOITE = new Bounds(new Vector3(100, 0, -50), new Vector3(4000, 0, 3000));
        private static readonly Vector2 MILIEU = new Vector2(.5f, .5f);

        // Cadrée sur sa largeur, la carte l'est un peu plus large : la perspective resserre son bord du sud.
        private static float DemiMaxAttendu(float aspect) => Mathf.Max(BOITE.extents.z, BOITE.extents.x * VueDeCarte.RESSERRE_AU_SUD / aspect) * VueDeCarte.MARGE;

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

        [Test] public void La_camera_s_incline_en_s_approchant_et_vise_le_centre() {
            var v = new VueDeCarte(BOITE, 16f / 9f); float demiChamp = Mathf.Tan(VueDeCarte.CHAMP * Mathf.Deg2Rad / 2f);
            Assert.AreEqual(VueDeCarte.INCLINAISON_LOIN, v.Inclinaison, TOLERANCE, "sur toute la carte");
            float avant = v.Inclinaison;
            for (int cran = 0; cran < 40 && v.Echelle > v.EchelleMin; cran++) {
                v.Zoomer(1, MILIEU);
                Assert.Less(v.Inclinaison, avant, "un cran de plus n'incline pas davantage la caméra"); avant = v.Inclinaison;
                Assert.AreEqual(v.Demi / demiChamp, v.Distance, 1e-2f, "la distance n'est pas celle d'où la vue remplit le champ");
                Assert.AreEqual(0f, Vector3.Dot(v.Regard, v.Haut), 1e-5f); Assert.AreEqual(-Mathf.Sin(v.Inclinaison * Mathf.Deg2Rad), v.Regard.y, 1e-5f, "le regard ne descend pas de l'inclinaison");
                Assert.Greater(v.Regard.z, 0f, "la caméra ne regarde pas vers le nord");
                Assert.Less((v.PointSous(MILIEU) - v.Centre).magnitude, TOLERANCE, "le milieu de l'écran ne vise pas le centre de la vue");
                Assert.AreEqual(v.Centre.x, v.Position.x, TOLERANCE); Assert.Less(v.Position.z, v.Centre.y, "la caméra n'est pas au sud du point visé");
            }
            Assert.AreEqual(VueDeCarte.INCLINAISON_PRES, v.Inclinaison, TOLERANCE, "au plus près");
            Assert.Greater(VueDeCarte.INCLINAISON_PRES, VueDeCarte.CHAMP / 2f, "le haut de l'écran verrait par-dessus l'horizon");
            // À mi-hauteur de l'écran, les bords de gauche et de droite tombent au sol à la demi-largeur de la vue.
            Assert.Less((v.PointSous(new Vector2(0f, .5f)) - (v.Centre - new Vector2(v.DemiLargeur, 0f))).magnitude, TOLERANCE); Assert.Less((v.PointSous(new Vector2(1f, .5f)) - (v.Centre + new Vector2(v.DemiLargeur, 0f))).magnitude, TOLERANCE);
            // La perspective : le haut de l'écran montre plus de sol que le bas.
            Assert.Greater(v.PointSous(new Vector2(.5f, 1f)).y - v.Centre.y, v.Centre.y - v.PointSous(new Vector2(.5f, 0f)).y, "le nord n'est pas plus loin que le sud");
            Assert.Greater(v.PointSous(new Vector2(1f, 1f)).x - v.PointSous(new Vector2(0f, 1f)).x, v.PointSous(new Vector2(1f, 0f)).x - v.PointSous(new Vector2(0f, 0f)).x, "le haut de l'écran n'est pas plus large au sol que le bas");
        }

        // Quelle que soit la forme de la fenêtre, les quatre coins de la carte sont dans la vue du départ : la perspective
        // resserre le bord du sud, et le cadrage en tient compte.
        [Test] public void Toute_la_carte_tient_dans_la_vue_du_depart() {
            float demiChamp = Mathf.Tan(VueDeCarte.CHAMP * Mathf.Deg2Rad / 2f);
            foreach (float aspect in new[] { 0.5f, 1f, 1.2f, 4f / 3f, 1.4f, 1.5f, 16f / 9f, 2.4f, 3f }) {
                var v = new VueDeCarte(BOITE, aspect); float plusLarge = 0f, plusHaut = 0f;
                foreach (var (x, z) in new[] { (BOITE.min.x, BOITE.min.z), (BOITE.max.x, BOITE.min.z), (BOITE.max.x, BOITE.max.z), (BOITE.min.x, BOITE.max.z) }) {
                    Vector3 vers = new Vector3(x, 0f, z) - v.Position; float profondeur = Vector3.Dot(vers, v.Regard);
                    float enLarge = Vector3.Dot(vers, Vector3.right) / (profondeur * demiChamp * aspect), enHaut = Vector3.Dot(vers, v.Haut) / (profondeur * demiChamp);
                    Assert.IsTrue(profondeur > 0 && Mathf.Abs(enLarge) <= 1f && Mathf.Abs(enHaut) <= 1f, "aspect " + aspect + " : le coin (" + x + ", " + z + ") est hors de la vue : " + enLarge + ", " + enHaut);
                    plusLarge = Mathf.Max(plusLarge, Mathf.Abs(enLarge)); plusHaut = Mathf.Max(plusHaut, Mathf.Abs(enHaut));
                }
                Assert.Greater(Mathf.Max(plusLarge, plusHaut), 0.9f, "aspect " + aspect + " : la carte est loin de remplir la vue");
            }
        }

        [Test] public void Le_point_saisi_reste_sous_la_souris_a_la_hauteur_du_sol() {
            var v = new VueDeCarte(BOITE, 16f / 9f); v.Zoomer(10, MILIEU);
            Vector2 de = new Vector2(.4f, .3f), a = new Vector2(.55f, .62f); const float HAUT = 9f;
            // Glissé : le point du sol saisi, à 9 km de haut, vient sous la souris.
            Vector2 saisi = v.PointSous(de, HAUT); Vector2 centre = v.Centre; v.Glisser(de, a, HAUT);
            Assert.Less((v.PointSous(a, HAUT) - saisi).magnitude, TOLERANCE, "le point saisi n'est pas sous la souris"); Assert.Greater((v.Centre - centre).magnitude, 10f, "la vue n'a pas bougé");
            // Contre-épreuve : lu au niveau de la mer, ce n'est pas le même point ; le relief compte.
            Assert.Greater((v.PointSous(a, 0f) - saisi).magnitude, 1f, "échantillon vide : la hauteur du sol ne change rien au point visé");
            // Molette : le point du sol sous la souris, à sa hauteur, reste sous elle quand la caméra s'approche et s'incline.
            Vector2 sous = v.PointSous(a, HAUT); float inclinaison = v.Inclinaison; v.Zoomer(4, a, HAUT);
            Assert.Less((v.PointSous(a, HAUT) - sous).magnitude, TOLERANCE, "le point sous la souris a bougé au zoom"); Assert.Less(v.Inclinaison, inclinaison);
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
