using System.Linq;
using NUnit.Framework;

namespace Forge.Pont.Tests {
    // La mesure des images du build : ce qu'elle lit de la ligne de commande, ce qu'elle tire d'une suite de temps
    // d'image, et la ligne qu'elle écrit. Le parcours lui-même se joue dans le build.
    public sealed class MesureDImagesTests {
        [Test] public void Le_fichier_se_lit_apres_l_argument() {
            Assert.AreEqual(@"D:\mesure.txt", MesureDImages.Fichier(new[] { "Forge.exe", "-forgeCarte", MesureDImages.ARGUMENT, @"D:\mesure.txt", MesureDImages.QUITTER }));
            Assert.IsNull(MesureDImages.Fichier(new[] { "Forge.exe", "-forgeCarte" }), "une mesure sans l'argument");
            Assert.IsNull(MesureDImages.Fichier(new[] { "Forge.exe", MesureDImages.ARGUMENT }), "une mesure sans fichier");
            Assert.IsNull(MesureDImages.Fichier(new[] { "Forge.exe", MesureDImages.ARGUMENT, "-forgeCarte" }), "un autre argument pris pour le fichier");
            Assert.IsNull(MesureDImages.Fichier(null));
        }

        [Test] public void Le_releve_dit_la_cadence_du_temps_ecoule_et_les_images_lentes() {
            // Quatre-vingt-dix-huit images de 10 ms et deux de 60 : 100 images en 1,1 s.
            var ms = Enumerable.Repeat(10f, 98).Concat(new[] { 60f, 60f }).ToList(); ReleveDImages r = MesureDImages.Resumer(ms);
            Assert.AreEqual(100, r.Images); Assert.AreEqual(100 / 1.1, r.ImagesParSeconde, 1e-3, "la cadence n'est pas celle du temps écoulé");
            Assert.AreEqual(10.0, r.MedianeMs, 1e-6); Assert.AreEqual(60.0, r.CentileMs, 1e-6, "le 99e centile ne voit pas les deux images lentes"); Assert.AreEqual(60.0, r.PireMs, 1e-6);
            // Une seule image lente sur deux cents reste sous le 99e centile, mais c'est la pire.
            var rare = Enumerable.Repeat(5f, 199).Concat(new[] { 80f }).ToList(); ReleveDImages s = MesureDImages.Resumer(rare);
            Assert.AreEqual(5.0, s.CentileMs, 1e-6); Assert.AreEqual(80.0, s.PireMs, 1e-6);
            // L'ordre des images ne change rien.
            ms.Reverse(); Assert.AreEqual(r.ImagesParSeconde, MesureDImages.Resumer(ms).ImagesParSeconde, 1e-9);
            // Sans image, rien n'est mesuré : -1, jamais 0.
            ReleveDImages vide = MesureDImages.Resumer(new float[0]);
            Assert.AreEqual((0, -1.0, -1.0, -1.0, -1.0), (vide.Images, vide.ImagesParSeconde, vide.MedianeMs, vide.CentileMs, vide.PireMs)); Assert.AreEqual(-1.0, MesureDImages.Resumer(null).ImagesParSeconde);
        }

        [Test] public void La_ligne_dit_la_vue_la_synchro_et_ce_qui_n_est_pas_mesure() {
            string ligne = MesureDImages.Ligne("toute la carte", true, true, MesureDImages.Resumer(new[] { 10f, 10f, 20f, 10f }), 84.4, 31.2, 1234567.8);
            Assert.AreEqual("toute la carte ; synchro verticale livrée ; au premier plan : oui ; 4 images ; 80.0 images/s ; image médiane 10.00 ms ; 99e centile 20.00 ms ; pire 20.00 ms ; appels de dessin 84 ; passes 31 ; triangles 1234568", ligne);
            string sans = MesureDImages.Ligne("au plus près", false, false, MesureDImages.Resumer(new float[0]), -1, -1, -1);
            StringAssert.Contains("synchro verticale coupée ; au premier plan : non ; 0 images ; non mesuré images/s", sans); StringAssert.Contains("appels de dessin non mesuré", sans);
            // Ce que le système n'a pas dit ne s'invente pas.
            StringAssert.Contains("au premier plan : inconnu ;", MesureDImages.Ligne("au plus près", false, null, MesureDImages.Resumer(new[] { 5f }), 1, 1, 1));
        }
    }
}
