using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEngine;

namespace Forge.Pont.Tests {
    // Les figurines de la carte, faites par le code : un bourg de quatre tailles, une armée en marche ou au siège.
    // Chacune tient sur son socle, ses faces tournées vers le dehors, ses parts teintées marquées par l'alpha de
    // leurs sommets ; et une figurine ne descend jamais sous sa taille minimale à l'écran.
    public sealed class FormesDeCarteTests {
        private static readonly Color PIERRE = new Color(0.9f, 0.86f, 0.78f), BOIS = new Color(0.18f, 0.15f, 0.12f), ACIER = new Color(0.5f, 0.52f, 0.55f), TOILE = new Color(0.85f, 0.8f, 0.7f);
        private readonly List<Object> crees = new List<Object>();
        [TearDown] public void Fermer() { foreach (Object o in crees) if (o != null) Object.DestroyImmediate(o); crees.Clear(); }
        private Mesh Garde(Mesh m) { crees.Add(m); return m; }

        // Le rayon d'un maillage autour de son axe, et ses faces : chaque triangle avec sa normale de sommet.
        private static float Rayon(Mesh m) => m.vertices.Max(p => new Vector2(p.x, p.z).magnitude);
        private static void FacesTourneesDehors(Mesh m, string nom) {
            Vector3[] p = m.vertices, n = m.normals; int[] t = m.triangles; Assert.AreEqual(p.Length, n.Length, nom + " : une normale par sommet"); Assert.AreEqual(p.Length, m.colors32.Length, nom + " : une couleur par sommet");
            Assert.Greater(t.Length, 0, nom + " : aucun triangle");
            for (int k = 0; k < t.Length; k += 3) {
                Vector3 face = Vector3.Cross(p[t[k + 1]] - p[t[k]], p[t[k + 2]] - p[t[k]]);
                Assert.Greater(face.magnitude, 1e-6f, nom + " : un triangle plat");
                // Unity voit de face un triangle dont la normale est celle de ce produit : elle doit être celle de ses sommets.
                Assert.Greater(Vector3.Dot(face.normalized, n[t[k]]), 0.99f, nom + " : un triangle tourne le dos à sa normale");
                Assert.AreEqual(1f, n[t[k]].magnitude, 1e-3f, nom + " : une normale qui n'est pas de longueur 1");
            }
        }

        private static bool Est(Color32 c, Color couleur) { Color32 v = couleur; return c.a == 0 && c.r == v.r && c.g == v.g && c.b == v.b; }

        [Test] public void Un_bourg_grandit_avec_sa_taille_et_tient_sur_son_socle() {
            int sommetsDAvant = 0;
            for (int taille = 0; taille <= FormesDeCarte.TAILLE_MAX; taille++) {
                // Une ville de la carte : le dessus du socle d'une couleur donnée, les toits teintés.
                Mesh m = Garde(FormesDeCarte.Bourg(taille, PIERRE, BOIS, null, TOILE)); string nom = "bourg de taille " + taille; Vector3[] p = m.vertices; Color32[] c = m.colors32; Vector3[] n = m.normals;
                Assert.AreEqual("Bourg de taille " + taille, m.name); FacesTourneesDehors(m, nom);
                // Rien ne dépasse du socle, qui a le rayon annoncé ; son bord sombre descend sous son pied, pour ne laisser aucun jour sur une pente.
                Assert.AreEqual(FormesDeCarte.RayonDuBourg(taille), Rayon(m), 1e-3f, nom + " : quelque chose dépasse du socle, ou il n'a pas son rayon");
                Assert.Less(m.bounds.min.y, -0.5f, nom + " : le bord du socle ne descend pas sous son pied");
                var dessus = Enumerable.Range(0, p.Length).Where(k => Mathf.Abs(p[k].y - FormesDeCarte.HAUTEUR_DU_SOCLE_KM) < 1e-4f && n[k].y > 0.99f && new Vector2(p[k].x, p[k].z).magnitude > FormesDeCarte.RayonDuBourg(taille) - 1e-3f).ToList();
                Assert.IsTrue(dessus.Count == 20 && dessus.All(k => Est(c[k], TOILE)), nom + " : le dessus du socle n'a pas sa couleur : " + dessus.Count + " sommets");
                Assert.IsTrue(Enumerable.Range(0, p.Length).Where(k => p[k].y < -1e-3f).All(k => Est(c[k], BOIS)), nom + " : le bord du socle n'est pas sombre");
                // Les toits sont teintés et regardent le ciel ; les murs gardent leur pierre.
                int teintes = c.Count(x => x.a == 255), propres = c.Count(x => x.a == 0);
                Assert.IsTrue(teintes > 0 && propres > 0 && teintes + propres == c.Length, nom + " : " + teintes + " sommets teintés, " + propres + " à leur couleur");
                Assert.IsTrue(Enumerable.Range(0, p.Length).Where(k => c[k].a == 255).All(k => n[k].y > 0.1f && p[k].y > FormesDeCarte.HAUTEUR_DU_SOCLE_KM + 0.5f), nom + " : une part teintée n'est pas un toit");
                Assert.IsTrue(c.Any(x => Est(x, PIERRE)), nom + " : aucun mur à la couleur de la pierre");
                Assert.Greater(p.Length, sommetsDAvant, nom + " : pas plus de sommets que la taille d'avant"); sommetsDAvant = p.Length;
                Assert.Greater(m.bounds.max.y, 1.5f, nom + " : rien ne s'élève au-dessus du socle");
                // La même figurine demandée deux fois est la même.
                Mesh bis = Garde(FormesDeCarte.Bourg(taille, PIERRE, BOIS, null, TOILE)); Assert.IsTrue(p.SequenceEqual(bis.vertices) && m.triangles.SequenceEqual(bis.triangles), nom + " : deux figurines différentes");
                // Un lieu tenu : c'est le dessus du socle qui est teinté, et lui seul ; les toits ont la couleur donnée.
                Mesh lieu = Garde(FormesDeCarte.Bourg(taille, PIERRE, BOIS, ACIER, null)); Vector3[] q = lieu.vertices; Color32[] d = lieu.colors32;
                Assert.IsTrue(q.SequenceEqual(p), nom + " : la couleur change la forme");
                var teintesDuLieu = Enumerable.Range(0, q.Length).Where(k => d[k].a == 255).ToList();
                Assert.IsTrue(teintesDuLieu.Count == 20 && teintesDuLieu.All(k => Mathf.Abs(q[k].y - FormesDeCarte.HAUTEUR_DU_SOCLE_KM) < 1e-4f), nom + " : la teinte d'un lieu n'est pas le dessus de son socle : " + teintesDuLieu.Count + " sommets");
                Assert.AreEqual(teintes, d.Count(x => Est(x, ACIER)), nom + " : les toits d'un lieu n'ont pas la couleur donnée");
            }
            Assert.Greater(FormesDeCarte.RayonDuBourg(FormesDeCarte.TAILLE_MAX), 2f * FormesDeCarte.RayonDuBourg(0), "la cité n'est pas plus de deux fois le hameau");
            Assert.AreEqual(Garde(FormesDeCarte.Bourg(99, PIERRE, BOIS, null, TOILE)).vertexCount, sommetsDAvant, "une taille trop grande n'est pas ramenée à la plus grande");
        }

        [Test] public void Une_armee_porte_sa_banniere_et_change_de_forme_au_siege() {
            Mesh marche = Garde(FormesDeCarte.Armee(false, BOIS, ACIER, TOILE)), siege = Garde(FormesDeCarte.Armee(true, BOIS, ACIER, TOILE));
            foreach (Mesh m in new[] { marche, siege }) {
                FacesTourneesDehors(m, m.name); Vector3[] p = m.vertices; Color32[] c = m.colors32;
                Assert.AreEqual(FormesDeCarte.RAYON_DE_L_ARMEE_KM, Rayon(m), 1e-3f, m.name + " : quelque chose dépasse du socle");
                // Deux parts teintées, et elles seules : le dessus du socle, et l'étoffe de la bannière en haut de sa hampe.
                var teintes = Enumerable.Range(0, p.Length).Where(k => c[k].a == 255).Select(k => p[k]).ToList();
                var socle = teintes.Where(q => Mathf.Abs(q.y - FormesDeCarte.HAUTEUR_DU_SOCLE_KM) < 1e-4f).ToList(); var etoffe = teintes.Where(q => q.y > 4f).ToList();
                Assert.IsTrue(socle.Count == 20 && etoffe.Count == 20 && socle.Count + etoffe.Count == teintes.Count, m.name + " : " + socle.Count + " sommets teintés au socle, " + etoffe.Count + " à l'étoffe, " + teintes.Count + " en tout");
                // L'étoffe se voit du sud, d'où la caméra regarde : large de plus de 4 km, haute de plus de 2.
                Assert.IsTrue(etoffe.Max(q => q.x) - etoffe.Min(q => q.x) > 4f && etoffe.Max(q => q.y) - etoffe.Min(q => q.y) > 2f && etoffe.Max(q => q.z) - etoffe.Min(q => q.z) < 0.3f, m.name + " : l'étoffe ne fait pas face au sud");
                Assert.Greater(m.bounds.max.y, 7f, m.name + " : la hampe ne domine pas l'armée");
            }
            Assert.AreEqual(("Armée en marche", "Armée au siège"), (marche.name, siege.name));
            Assert.AreNotEqual(marche.vertexCount, siege.vertexCount, "la même forme en marche et au siège");
            // En marche, douze piquiers d'acier ; au siège, des tentes de toile et aucun acier.
            Assert.AreEqual(12 * 20, marche.colors32.Count(x => Est(x, ACIER)), "douze piquiers, cinq faces chacun"); Assert.AreEqual(0, siege.colors32.Count(x => Est(x, ACIER)), "des piquiers au siège");
            Assert.AreEqual(3 * 6 * 3, siege.colors32.Count(x => Est(x, TOILE)), "trois tentes de toile à six pans");
        }

        [Test] public void Une_figurine_ne_descend_pas_sous_sa_taille_a_l_ecran() {
            Camera camera = new GameObject("Caméra témoin").AddComponent<Camera>(); crees.Add(camera.gameObject); // détruite avant l'écran qu'elle vise
            var ecran = new RenderTexture(1600, 900, 16); crees.Add(ecran); camera.targetTexture = ecran; camera.fieldOfView = 30f; camera.nearClipPlane = 1f; camera.farClipPlane = 20000f;
            camera.transform.SetPositionAndRotation(new Vector3(0f, 0f, -1000f), Quaternion.identity);
            const float RAYON = 4f, MIN = 24f; float demiChamp = Mathf.Tan(15f * Mathf.Deg2Rad);
            // À 1 000 km : un pixel couvre 2 × 1 000 × tan(15°) / 900 km ; la figurine de 8 km en ferait 13, elle est grossie jusqu'à 24.
            float kmParPixel = 2f * 1000f * demiChamp / 900f; Assert.AreEqual(kmParPixel, FormesDeCarte.KmParPixel(camera, Vector3.zero), 1e-4f);
            float echelle = FormesDeCarte.EchellePourLEcran(camera, Vector3.zero, RAYON, MIN);
            Assert.Greater(echelle, 1.5f, "échantillon vide : la figurine est déjà assez grande"); Assert.AreEqual(MIN, 2f * RAYON * echelle / kmParPixel, 1e-2f, "la figurine grossie n'a pas sa taille minimale à l'écran");
            // De près elle garde sa taille : 100 km devant la caméra, elle fait déjà plus de 24 pixels.
            Assert.AreEqual(1f, FormesDeCarte.EchellePourLEcran(camera, new Vector3(0f, 0f, -900f), RAYON, MIN), "une figurine assez grande est grossie");
            // Derrière la caméra, ni grossie ni mesurée.
            Assert.AreEqual(1f, FormesDeCarte.EchellePourLEcran(camera, new Vector3(0f, 0f, -2000f), RAYON, MIN)); Assert.AreEqual(0f, FormesDeCarte.KmParPixel(camera, new Vector3(0f, 0f, -2000f)));
            // Sous une caméra à plat, la même règle.
            camera.orthographic = true; camera.orthographicSize = 450f; Assert.AreEqual(1f, FormesDeCarte.KmParPixel(camera, Vector3.zero), 1e-5f); Assert.AreEqual(3f, FormesDeCarte.EchellePourLEcran(camera, Vector3.zero, RAYON, MIN), 1e-4f);
        }

        [Test] public void Le_materiau_d_une_figurine_porte_sa_teinte() {
            var teinte = new Color(0.6f, 0.2f, 0.4f, 0.3f); Material m = FormesDeCarte.Matiere(teinte); crees.Add(m);
            Assert.AreEqual(FormesDeCarte.SHADER, m.shader.name, "le matériau n'est pas celui des figurines"); Assert.AreEqual((Color32)new Color(0.6f, 0.2f, 0.4f, 1f), (Color32)m.color, "la teinte du matériau, opaque");
            // Les figurines passent devant les noms des pays, imprimés sur le terrain.
            Assert.Greater(m.shader.renderQueue, Resources.Load<Shader>("Forge/NomDeCarte").renderQueue, "une figurine se dessine avant les noms des pays");
        }
    }
}
