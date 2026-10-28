using System.Collections.Generic;
using NUnit.Framework;
using UnityEngine;
using Object = UnityEngine.Object;

namespace Forge.Pont.Tests
{
    // Lot #780 — un étal montre le stock d'une marchandise du bourg : la hauteur de sa garniture, jamais le comptoir.
    // Cellule 5, tick 3, référence 100 kg. `cas` décale une seule lecture.
    public sealed class EtalDuBourgTests
    {
        private readonly List<Object> crees = new List<Object>();
        [TearDown] public void Detruire() { foreach (var o in crees) if (o != null) Object.DestroyImmediate(o); crees.Clear(); }

        private static Lecture<BourgLu> Bourg(Dictionary<string, double> stocks, string cas = "", long faim = 0) => cas == "bourg absent" ? Lecture<BourgLu>.Absent("service muet")
            : Lecture<BourgLu>.De(new BourgLu(cas == "cellule bourg" ? 6 : 5, 3, new DateDuMonde(1400, 3), cas == "rang" ? 1 : 0, 120, stocks, faim, cas == "tick local" ? 4 : 3));
        private static LecturePlan Plan(string cas = "") => cas == "plan absent" ? LecturePlan.Absent("service muet")
            : LecturePlan.De(new PlanLu(cas == "cellule plan" ? 6 : 5, cas == "tick plan" ? 4 : 3, new RueDuPlan[0], new ParcelleDuPlan[0], new BatimentDuPlan[0]));
        private static Dictionary<string, double> Stocks(double? nourriture, double bois = 30) { var s = new Dictionary<string, double> { ["bois"] = bois }; if (nourriture.HasValue) s["nourriture"] = nourriture.Value; return s; }
        private static bool Lire(EtalDuBourg e, double? kg, string cas = "", long faim = 0) => e.Appliquer(Bourg(Stocks(kg), cas, faim), Plan(cas));

        // Un vrai comptoir et une garniture pivotée à sa base (le cube enfant monte d'une demi-hauteur), au plein `echelle`.
        private EtalDuBourg Etal(string marchandise, Vector3 echelle, out Transform garniture, out Renderer comptoir)
        {
            var etal = new GameObject("étal " + marchandise); crees.Add(etal); var c = GameObject.CreatePrimitive(PrimitiveType.Cube); c.transform.SetParent(etal.transform, false); comptoir = c.GetComponent<Renderer>();
            garniture = new GameObject("garniture").transform; garniture.SetParent(etal.transform, false); garniture.localPosition = Vector3.up; garniture.localScale = echelle;
            var denrees = GameObject.CreatePrimitive(PrimitiveType.Cube); denrees.transform.SetParent(garniture, false); denrees.transform.localPosition = Vector3.up * .5f;
            var e = etal.AddComponent<EtalDuBourg>(); e.Configurer(5, marchandise, 100, garniture); return e;
        }
        // Lu sur les objets : rendus effectivement actifs, échelle, base posée au pivot ; le comptoir reste visible.
        private static void Voir(Transform g, Renderer comptoir, Vector3 plein, double rapport)
        {
            var r = g.GetComponentInChildren<MeshRenderer>(true); bool visible = r.enabled && r.gameObject.activeInHierarchy; Assert.That(comptoir.enabled && comptoir.gameObject.activeInHierarchy, Is.True, "comptoir visible");
            Assert.That(visible, Is.EqualTo(rapport > 0), "garniture visible"); if (!visible) return;
            Assert.That(g.localScale.x, Is.EqualTo(plein.x)); Assert.That(g.localScale.z, Is.EqualTo(plein.z)); Assert.That(g.localScale.y, Is.EqualTo(plein.y * rapport).Within(1e-6), "hauteur");
            Assert.That(r.bounds.min.y, Is.EqualTo(g.position.y).Within(1e-5), "base au pivot"); Assert.That(r.bounds.size.y, Is.EqualTo(plein.y * rapport).Within(1e-5)); Assert.That(r.bounds.size.x, Is.EqualTo(plein.x).Within(1e-5));
        }

        [TestCase(1f, 1f, 1f)] [TestCase(1.5f, .8f, .6f)]
        public void LeStockAtteintLaGeometrie780(float x, float y, float z)
        {
            var plein = new Vector3(x, y, z); var e = Etal("nourriture", plein, out var g, out var c); Voir(g, c, plein, 0); Assert.That(e.Rapport, Is.EqualTo(-1));
            foreach (var (kg, rapport) in new (double, double)[] { (100, 1), (50, .5), (12.5, .125), (0, 0), (200, 1) })
            { Assert.That(Lire(e, kg), Is.True, e.Cause); Assert.That(e.Cause, Is.Null); Assert.That(e.Rapport, Is.EqualTo(rapport)); Voir(g, c, plein, rapport); }
            Assert.That(g.position, Is.EqualTo(e.transform.position + Vector3.up)); Assert.That(e.transform.localScale, Is.EqualTo(Vector3.one), "l'étal entier n'est pas réduit");
        }

        // Nourriture et bois au même bourg ; à stock égal, faim nulle ou positive donnent la même garniture.
        [Test]
        public void ChaqueMarchandiseGardeSonSens780([Values(0, 6)] long faim)
        {
            var n = Etal("nourriture", Vector3.one, out var gn, out var cn); var b = Etal("bois", Vector3.one, out var gb, out var cb); var d = Etal("dattes", Vector3.one, out var gd, out var cd);
            foreach (var (kg, rapport) in new (double?, double)[] { (0, 0), (null, 0), (40, .4), (0, 0) })
            {
                var stocks = Stocks(kg); stocks["dattes"] = 25; var bourg = Bourg(stocks, "", faim); var copie = new Dictionary<string, double>(stocks);
                Assert.That(n.Appliquer(bourg, Plan()), Is.EqualTo(kg.HasValue)); Assert.That(b.Appliquer(bourg, Plan()) && d.Appliquer(bourg, Plan()), Is.True);
                if (kg.HasValue) Assert.That(n.Cause, Is.Null, "zéro est une mesure"); else Assert.That(n.Cause, Does.Contain("« nourriture » absente"));
                Voir(gn, cn, Vector3.one, rapport); Voir(gb, cb, Vector3.one, .3); Voir(gd, cd, Vector3.one, .25); Assert.That(b.Cause ?? d.Cause, Is.Null);
                Assert.That(bourg.Donnees.Stocks, Is.EquivalentTo(copie)); Assert.That(bourg.Donnees.DureeFaimTicks, Is.EqualTo(faim));
            }
        }

        // Après un succès, chaque refus masque la garniture et nomme sa cause ; une lecture ou configuration rétablie rend le plein.
        [TestCase("plan absent", "plan absent")] [TestCase("bourg absent", "bourg absent")] [TestCase("cellule plan", "cellule")] [TestCase("cellule bourg", "cellule")]
        [TestCase("rang", "rang 0")] [TestCase("tick plan", "tick")] [TestCase("tick local", "tick")] [TestCase("clé vide", "marchandise vide")] [TestCase("référence nulle", "référence")]
        [TestCase("référence négative", "référence")] [TestCase("référence NaN", "référence")] [TestCase("référence infinie", "référence")] [TestCase("garniture dehors", "hors de l'étal")]
        [TestCase("étal entier", "hors de l'étal")] [TestCase("sans géométrie", "géométrie")]
        public void UneLectureDouteuseNeConserveRien780(string cas, string cause)
        {
            var plein = new Vector3(1.2f, .7f, .9f); var e = Etal("nourriture", plein, out var g, out var c); Assert.That(Lire(e, 100), Is.True, e.Cause); Voir(g, c, plein, 1);
            var filtre = g.GetComponentInChildren<MeshFilter>(); var maillage = filtre.sharedMesh; double reference = cas == "référence nulle" ? 0 : cas == "référence négative" ? -5 : cas == "référence NaN" ? double.NaN : cas == "référence infinie" ? double.PositiveInfinity : 100;
            if (cas == "garniture dehors") g.SetParent(null, false); if (cas == "sans géométrie") filtre.sharedMesh = null;
            if (reference != 100 || cas == "clé vide") e.Configurer(5, cas == "clé vide" ? " " : "nourriture", reference, g); if (cas == "étal entier") e.Configurer(5, "nourriture", 100, e.transform);
            Assert.That(Lire(e, 100, cas), Is.False); Assert.That(e.Cause, Does.Contain(cause)); Assert.That(e.Rapport, Is.EqualTo(-1)); Voir(g, c, plein, 0);
            g.SetParent(e.transform, false); filtre.sharedMesh = maillage; e.Configurer(5, "nourriture", 100, g); Assert.That(Lire(e, 100), Is.True, e.Cause); Voir(g, c, plein, 1);
        }

        [Test]
        public void LesEtalsRestentLocauxEtStables780()
        {
            var plein = new Vector3(1.5f, .8f, .6f); var e = Etal("nourriture", plein, out var g, out var c); var t = Etal("bois", Vector3.one, out var tg, out var tc);
            Assert.That(t.Appliquer(Bourg(Stocks(80)), Plan()), Is.True); var matiere = c.sharedMaterial; int objets = Object.FindObjectsByType<Transform>(FindObjectsSortMode.None).Length, enfants = e.transform.childCount;
            for (int i = 0; i < 10; i++)
            {
                Assert.That(Lire(e, 50), Is.True, e.Cause); Voir(g, c, plein, .5); Assert.That(e.Garniture, Is.SameAs(g)); Assert.That(e.transform.childCount, Is.EqualTo(enfants));
                Assert.That(Object.FindObjectsByType<Transform>(FindObjectsSortMode.None).Length, Is.EqualTo(objets)); Assert.That(c.sharedMaterial, Is.SameAs(matiere)); Voir(tg, tc, Vector3.one, .3);
            }
            e.enabled = false; Voir(g, c, plein, 0); Assert.That(Lire(e, 50), Is.False); Assert.That(e.Cause, Does.Contain("désactivé"));
            e.enabled = true; Voir(g, c, plein, 0); Assert.That(Lire(e, 50), Is.True, e.Cause); Voir(g, c, plein, .5);
            var etal = e.gameObject; Object.DestroyImmediate(e); Voir(g, c, plein, 0); Assert.That(etal != null && g != null && c != null, Is.True); Voir(tg, tc, Vector3.one, .3);
        }

        // Deux étals visibles : configurer le premier avec la garniture du second est refusé sans la masquer, la réduire ni la rétablir.
        [Test]
        public void UneGarnitureEtrangereResteIntacte780()
        {
            var e = Etal("nourriture", Vector3.one, out var g, out var c); var t = Etal("bois", Vector3.one, out var tg, out var tc);
            Assert.That(Lire(e, 50), Is.True, e.Cause); Assert.That(t.Appliquer(Bourg(Stocks(80)), Plan()), Is.True); Voir(tg, tc, Vector3.one, .3);
            e.Configurer(5, "nourriture", 100, tg); Voir(tg, tc, Vector3.one, .3); Voir(g, c, Vector3.one, 0); Assert.That(g.localScale, Is.EqualTo(Vector3.one), "l'ancienne rendue à son plein");
            Assert.That(Lire(e, 50), Is.False); Assert.That(e.Cause, Does.Contain("hors de l'étal")); Voir(tg, tc, Vector3.one, .3);
            e.Configurer(5, "nourriture", 100, g); Voir(tg, tc, Vector3.one, .3); Assert.That(Lire(e, 50), Is.True, e.Cause); Voir(g, c, Vector3.one, .5); Object.DestroyImmediate(e); Voir(tg, tc, Vector3.one, .3); Assert.That(t.Cause, Is.Null);
        }
    }
}
