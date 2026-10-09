using NUnit.Framework;
using UnityEngine;

namespace Forge.Pont.Tests {
    // Lot #524 — le joueur parcourt sa carte sans en sortir : le zoom va de toute la carte à `DEMI_MIN_KM`, le glissé et
    // le zoom s'arrêtent aux bords de la carte servie. La boîte est celle d'une carte de 4 000 × 3 000 km décentrée.
    public sealed class VueDeCarteTests {
        private const float TOLERANCE = 1e-3f, LOIN = 1e7f;
        private static readonly Bounds BOITE = new Bounds(new Vector3(100, 0, -50), new Vector3(4000, 0, 3000));
        private static readonly Vector2 MILIEU = new Vector2(.5f, .5f);

        private static float DemiMaxAttendu(float aspect) => Mathf.Max(BOITE.extents.z, BOITE.extents.x / aspect) * VueDeCarte.MARGE;

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

        [Test] public void Le_jeu_s_ouvre_sur_la_carte_quand_on_le_demande() {
            Assert.IsTrue(OuvertureDeLaCarte.Demandee(new[] { "Forge.exe", "-forgeCell", "1175", OuvertureDeLaCarte.ARGUMENT }));
            Assert.IsFalse(OuvertureDeLaCarte.Demandee(new[] { "Forge.exe", "-forgeCell", "1175" }));
            Assert.IsFalse(OuvertureDeLaCarte.Demandee(null));
        }
    }
}
