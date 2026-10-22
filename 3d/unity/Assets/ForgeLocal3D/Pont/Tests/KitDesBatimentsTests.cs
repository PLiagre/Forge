using System;
using System.Collections.Generic;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using Object = UnityEngine.Object;

namespace Forge.Pont.Tests
{
    // Lot #368 — le kit du désert rend, pour chaque nature et chaque étape, sa pièce chargée hors de
    // l'éditeur, ou une absence déclarée ; l'étape suit le travail fourni ; la pose lit la façade sur `c0→c1`.
    public sealed class KitDesBatimentsTests
    {
        private const double Tolerance = 1e-9;

        private static BatimentDuPlan Batiment(bool enChantier, long requis, long fourni, params (double, double)[] emprise)
        {
            var points = new List<PointLocal>();
            foreach (var (x, y) in emprise) points.Add(new PointLocal(x, y));
            return new BatimentDuPlan(7, 0, "maison", points, enChantier, requis, fourni);
        }

        private static (double, double)[] Paires(double[] plat)
        {
            var paires = new (double, double)[plat.Length / 2];
            for (int i = 0; i < paires.Length; i++) paires[i] = (plat[2 * i], plat[2 * i + 1]);
            return paires;
        }

        // ---- Les pièces du kit -------------------------------------------------------------------

        [TestCase("maison", EtapeDuBatiment.Piquets, "chantier_maison_pise_0_piquets")]
        [TestCase("maison", EtapeDuBatiment.Murs, "chantier_maison_pise_0_murs")]
        [TestCase("maison", EtapeDuBatiment.Fini, "maison_pise_0")]
        [TestCase("scierie", EtapeDuBatiment.Piquets, "chantier_scierie_piquets")]
        [TestCase("scierie", EtapeDuBatiment.Murs, "chantier_scierie_murs")]
        [TestCase("scierie", EtapeDuBatiment.Fini, "scierie")]
        [TestCase("four", EtapeDuBatiment.Piquets, "chantier_four_pain_pise_piquets")]
        [TestCase("four", EtapeDuBatiment.Murs, "chantier_four_pain_pise_murs")]
        [TestCase("four", EtapeDuBatiment.Fini, "four_pain_pise")]
        public void LesNeufPiecesSeChargentHorsDeLEditeur(string nature, EtapeDuBatiment etape, string nom)
        {
            var kit = KitDesBatiments.Charger();
            Assert.That(kit, Is.Not.Null, "Resources.Load ne trouve pas " + KitDesBatiments.Ressource);
            var piece = kit.Piece(nature, etape);
            Assert.That(piece.Presente, Is.True, piece.Absence);
            Assert.That(piece.Absence, Is.EqualTo(""));
            Assert.That(piece.Prefab, Is.Not.Null);
            Assert.That(piece.Prefab.name, Is.EqualTo(nom));
            Assert.That(AssetDatabase.GetAssetPath(piece.Prefab),
                Is.EqualTo("Assets/ForgeLocal3D/Desert/Prefabs/" + nom + ".prefab"));
        }

        [TestCase("maison")]
        [TestCase("scierie")]
        [TestCase("four")]
        public void LesTroisPiecesDUneNatureSontDistinctes(string nature)
        {
            var kit = KitDesBatiments.Charger();
            Assert.That(kit, Is.Not.Null);
            var piquets = kit.Piece(nature, EtapeDuBatiment.Piquets).Prefab;
            var murs = kit.Piece(nature, EtapeDuBatiment.Murs).Prefab;
            var fini = kit.Piece(nature, EtapeDuBatiment.Fini).Prefab;
            Assert.That(piquets, Is.Not.Null);
            Assert.That(murs, Is.Not.Null);
            Assert.That(fini, Is.Not.Null);
            Assert.That(piquets, Is.Not.SameAs(murs));
            Assert.That(murs, Is.Not.SameAs(fini));
            Assert.That(piquets, Is.Not.SameAs(fini));
        }

        [Test, Combinatorial]
        public void UneNatureInconnueEstDeclareeAbsente(
            [Values("grenier", "Maison", "maison ", "", null)] string nature, [Values] EtapeDuBatiment etape)
        {
            var kit = KitDesBatiments.Charger();
            Assert.That(kit, Is.Not.Null);
            var piece = kit.Piece(nature, etape);
            Assert.That(piece.Presente, Is.False);
            Assert.That(piece.Prefab, Is.Null);
            Assert.That(piece.Absence, Does.Contain("nature sans pièce au kit"));
            if (nature != null) Assert.That(piece.Absence, Does.Contain(nature));
        }

        [Test]
        public void UnePieceManquanteEstDeclareeAbsenteSansEnChoisirUneAutre()
        {
            var kit = ScriptableObject.CreateInstance<KitDesBatiments>();
            var piquets = new GameObject("piquets");
            var fini = new GameObject("fini");
            try
            {
                kit.natures = new[]
                {
                    new KitDesBatiments.PiecesDUneNature { nature = "maison", piquets = piquets, murs = null, fini = fini },
                };
                var murs = kit.Piece("maison", EtapeDuBatiment.Murs);
                Assert.That(murs.Presente, Is.False);
                Assert.That(murs.Prefab, Is.Null);
                Assert.That(murs.Absence, Is.EqualTo("pièce manquante au kit : maison murs"));
                var present = kit.Piece("maison", EtapeDuBatiment.Piquets);
                Assert.That(present.Presente, Is.True);
                Assert.That(present.Prefab, Is.SameAs(piquets));
                Assert.That(present.Absence, Is.EqualTo(""));
            }
            finally
            {
                Object.DestroyImmediate(piquets);
                Object.DestroyImmediate(fini);
                Object.DestroyImmediate(kit);
            }
        }

        // Lot 737 : les six maisons de terre, dans l'ordre des prefabs, sans repli.
        [Test]
        public void LesSixMaisonsDePiseSontOrdonneesSansRepli()
        {
            var kit = KitDesBatiments.Charger();
            Assert.That(kit, Is.Not.Null);
            for (int i = -1; i <= 6; i++)
            {
                var p = kit.Maison(i); string n = "maison_pise_" + i;
                if (i < 0 || i > 5) { Assert.That(p.Presente, Is.False); Assert.That(p.Prefab, Is.Null); Assert.That(p.Absence, Is.EqualTo("indice invalide : " + i)); }
                else { Assert.That(p.Presente, Is.True, p.Absence); Assert.That(p.Prefab.name, Is.EqualTo(n)); Assert.That(AssetDatabase.GetAssetPath(p.Prefab), Is.EqualTo("Assets/ForgeLocal3D/Desert/Prefabs/" + n + ".prefab")); }
            }
            var v = ScriptableObject.CreateInstance<KitDesBatiments>();
            v.maisonsPise = new[] { kit.Maison(0).Prefab, null, null, null, null, null };
            try { var a = v.Maison(1); Assert.That(a.Presente, Is.False); Assert.That(a.Prefab, Is.Null); Assert.That(a.Absence, Is.EqualTo("référence absente : maison_pise_1")); Assert.That(v.Maison(0).Prefab, Is.SameAs(kit.Maison(0).Prefab)); }
            finally { Object.DestroyImmediate(v); }
        }

        // ---- L'étape -----------------------------------------------------------------------------

        [TestCase(true, 300, 0, EtapeDuBatiment.Piquets)]
        [TestCase(true, 300, 149, EtapeDuBatiment.Piquets)]
        [TestCase(true, 300, 150, EtapeDuBatiment.Murs)]
        [TestCase(true, 300, 299, EtapeDuBatiment.Murs)]
        [TestCase(false, 300, 300, EtapeDuBatiment.Fini)]
        [TestCase(true, 1, 0, EtapeDuBatiment.Piquets)]
        [TestCase(true, 301, 150, EtapeDuBatiment.Piquets)]
        [TestCase(true, 301, 151, EtapeDuBatiment.Murs)]
        public void LEtapeSuitLeTravailFourni(bool enChantier, long requis, long fourni, EtapeDuBatiment attendue)
        {
            var b = Batiment(enChantier, requis, fourni, (5, 2), (15, 2), (15, 22), (5, 22));
            Assert.That(LectureDuBatiment.Etape(b), Is.EqualTo(attendue));
        }

        // ---- La pose -----------------------------------------------------------------------------

        // Les exemples de MODELE.md sur la rue [[0, 0], [40, 0], [40, 25]], largeur 4 m ; la quatrième ligne est
        // le segment 1 à droite, la cinquième le rectangle de la première commencé à un autre coin.
        [TestCase(new double[] { 5, 2, 15, 2, 15, 22, 5, 22 }, 10.0, 12.0, 0.0, -1.0, 0.0)]
        [TestCase(new double[] { 5, -2, 15, -2, 15, -22, 5, -22 }, 10.0, -12.0, 0.0, 1.0, 180.0)]
        [TestCase(new double[] { 38, 0, 38, 25, 28, 25, 28, 0 }, 33.0, 12.5, 1.0, 0.0, 270.0)]
        [TestCase(new double[] { 42, 0, 42, 25, 52, 25, 52, 0 }, 47.0, 12.5, -1.0, 0.0, 90.0)]
        [TestCase(new double[] { 15, 2, 15, 22, 5, 22, 5, 2 }, 10.0, 12.0, 1.0, 0.0, 270.0)]
        public void LaFacadeRegardeLaRue(double[] emprise, double cx, double cy, double fx, double fy, double lacet)
        {
            var pose = LectureDuBatiment.Poser(Batiment(false, 1, 1, Paires(emprise)));
            Assert.That(pose.Presente, Is.True, pose.Absence);
            Assert.That(pose.Absence, Is.EqualTo(""));
            Assert.That(pose.CentreX, Is.EqualTo(cx).Within(Tolerance));
            Assert.That(pose.CentreY, Is.EqualTo(cy).Within(Tolerance));
            Assert.That(pose.FacadeX, Is.EqualTo(fx).Within(Tolerance));
            Assert.That(pose.FacadeY, Is.EqualTo(fy).Within(Tolerance));
            Assert.That(pose.LacetDegres, Is.EqualTo(lacet).Within(Tolerance));
            Assert.That(pose.LacetDegres, Is.GreaterThanOrEqualTo(0.0).And.LessThan(360.0));
            double theta = pose.LacetDegres * Math.PI / 180;
            Assert.That(Math.Sin(theta), Is.EqualTo(-pose.FacadeX).Within(Tolerance));
            Assert.That(Math.Cos(theta), Is.EqualTo(-pose.FacadeY).Within(Tolerance));
        }

        [TestCase(new double[] { 5, 2, 15, 2 }, "emprise de 2 point(s)")]
        [TestCase(new double[] { 5, 2, 5, 2, 15, 22 }, "façade nulle")]
        [TestCase(new double[] { 0, 0, 10, 0, 20, 0 }, "emprise plate")]
        [TestCase(new double[] { 5, 2, 15, double.NaN, 15, 22, 5, 22 }, "point non fini")]
        public void UnePoseImpossibleEstDeclareeAbsente(double[] emprise, string cause)
        {
            var pose = LectureDuBatiment.Poser(Batiment(false, 1, 1, Paires(emprise)));
            Assert.That(pose.Presente, Is.False);
            Assert.That(pose.Absence, Does.Contain("bâtiment 7"));
            Assert.That(pose.Absence, Does.Contain(cause));
            Assert.That(pose.CentreX, Is.NaN);
            Assert.That(pose.CentreY, Is.NaN);
            Assert.That(pose.FacadeX, Is.NaN);
            Assert.That(pose.FacadeY, Is.NaN);
            Assert.That(pose.LacetDegres, Is.NaN);
        }

        // ---- Lot #779 : la fumée et la lampe d'une maison du kit ---------------------------------
        // Cellule 5, tick 3. Base : rang 0 à un foyer, rang 1 îlot de trois ; bâtiments 10 (2 logés sur 4), 11 (vide), 12 (chantier),
        // 13 (four). `cas` décale une seule lecture ; la case de base suivie est (1, 2), le bâtiment le 10.
        private const float Configuree = 2.4f;
        private readonly List<Object> crees779 = new List<Object>();
        [TearDown] public void Detruire779() { foreach (var o in crees779) if (o != null) Object.DestroyImmediate(o); crees779.Clear(); }

        private static LecturePlan Plan779(string cas = "")
        {
            var c = new[] { new PointLocal(0, 0), new PointLocal(6, 0), new PointLocal(6, 6) };
            var bati = new List<BatimentDuPlan> { new BatimentDuPlan(11, 0, "maison", c, false, 300, 300), new BatimentDuPlan(12, 0, "maison", c, true, 300, 9), new BatimentDuPlan(13, 0, "four", c, false, 300, 300) };
            if (cas != "identifiant") bati.Add(new BatimentDuPlan(10, 0, cas == "atelier" ? "four" : "maison", c, cas == "chantier", 300, 300));
            var maisons = new List<MaisonDeBase> { new MaisonDeBase(c, 1) }; if (cas != "rang") maisons.Add(new MaisonDeBase(c, cas == "foyer" ? 2 : 3));
            return cas == "plan absent" ? LecturePlan.Absent("service muet") : LecturePlan.De(new PlanLu(5, cas == "tick plan" ? 4 : 3, new RueDuPlan[0], new ParcelleDuPlan[0], bati, new BaseDuPlan(c, new RueDeBase[0], maisons)));
        }
        private static Lecture<BourgLu> Bourg779(double? nourriture, string cas = "", long faim = 0)
        {
            var stocks = new Dictionary<string, double> { ["bois"] = 40 }; if (nourriture.HasValue) stocks["nourriture"] = nourriture.Value;
            return cas == "bourg absent" ? Lecture<BourgLu>.Absent("service muet") : Lecture<BourgLu>.De(new BourgLu(cas == "cellule" ? 6 : 5, cas == "tick bourg" ? 4 : 3,
                new DateDuMonde(1400, 3), cas == "rang bourg" ? 1 : 0, 120, stocks, faim, cas == "tick bourg" || cas == "tick local" ? 4 : 3));
        }
        private static Lecture<OccupationLue> Occupation779(string cas = "")
        {
            bool inconnue = cas == "inconnue"; long l(long n) => inconnue ? -1 : n;
            var bati = cas == "logement nul" ? new (long, long, long)[0] : new[] { (10L, 4L, l(2)), (11L, 3L, l(0)), (12L, 2L, l(1)), (13L, 2L, l(1)) };
            return cas == "occupation absente" ? Lecture<OccupationLue>.Absent("service muet") : Lecture<OccupationLue>.De(new OccupationLue(5, 0, cas == "tick occupation" ? 4 : 3, new DateDuMonde(1400, 3),
                new[] { (0L, 1L), (1L, cas == "compte" || cas == "foyer" ? 2L : 3L) }, bati, cas == "logement nul" ? null : new Logement(11, l(4), l(0)), null));
        }
        private static bool Lire779(EffetsDeMaison e, float heure = 21f, string cas = "", double? kg = 8, long faim = 0) => e.Appliquer(Bourg779(kg, cas, faim), Occupation779(cas), Plan779(cas), heure);
        // Une vraie maison du kit, ses deux enfants en plus de ses pièces, et le composant sans configuration.
        private EffetsDeMaison Maison779(int variante, out ParticleSystem fumee, out Light lampe)
        {
            var kit = KitDesBatiments.Charger(); Assert.That(kit, Is.Not.Null); var maison = Object.Instantiate(kit.Maison(variante).Prefab); crees779.Add(maison); int pieces = maison.transform.childCount;
            fumee = new GameObject("fumée").AddComponent<ParticleSystem>(); fumee.transform.SetParent(maison.transform, false);
            lampe = new GameObject("lampe").AddComponent<Light>(); lampe.type = LightType.Point; lampe.intensity = Configuree; lampe.transform.SetParent(maison.transform, false);
            Assert.That(maison.transform.childCount, Is.EqualTo(pieces + 2)); return maison.AddComponent<EffetsDeMaison>();
        }
        // Lus sur les composants eux-mêmes : une fumée se simule pour compter ses particules, une éteinte n'en garde aucune.
        private static void Voir779(ParticleSystem f, Light l, bool fume, float intensite)
        {
            Assert.That(f.isEmitting, Is.EqualTo(fume), "émission"); if (fume) { f.Simulate(1f, true, false); Assert.That(f.particleCount, Is.GreaterThan(0)); } else Assert.That(f.particleCount, Is.Zero);
            Assert.That(l.enabled, Is.EqualTo(intensite > 0), "lampe activée"); Assert.That(l.intensity, Is.EqualTo(intensite).Within(1e-4), "intensité");
        }

        [Test, Combinatorial]
        public void LesMaisonsHabiteesFumentEtSEclairentLeSoir779([Values(0, 10, 11)] int qui, [Values(12f, 18.2f, 19.6f, 21f)] float heure)
        {
            var e = Maison779(qui % 6, out var f, out var l); Assert.That(Lire779(e), Is.False); Assert.That(e.Cause, Does.Contain("références"));
            if (qui == 0) e.PourLaBase(f, l, 5, 1, 2); else e.PourLeBatiment(f, l, 5, qui); Voir779(f, l, false, 0f);
            Assert.That(Lire779(e, heure), Is.True, e.Cause); Voir779(f, l, qui != 11, qui == 11 ? 0f : (heure == 21f ? 1f : heure == 19.6f ? .5f : 0f) * Configuree);
        }

        [Test]
        public void LaFumeeNeLitQueLaNourritureEtLaLampeNon779()
        {
            var e = Maison779(0, out var f, out var l); e.PourLaBase(f, l, 5, 1, 2);
            foreach (var (kg, faim, fume) in new (double?, long, bool)[] { (8, 0, true), (0, 0, false), (null, 0, false), (8, 6, true), (0, 0, false) })
            {
                Assert.That(Lire779(e, 20f, "", kg, faim), Is.True, e.Cause); Voir779(f, l, fume, Mathf.InverseLerp(18.2f, 21f, 20f) * Configuree);
                if (kg.HasValue) Assert.That(e.AbsenceAlimentaire, Is.Null); else Assert.That(e.AbsenceAlimentaire, Does.Contain("nourriture absente"));
            }
        }

        // Après un succès, un refus coupe les deux objets et nomme sa cause, puis une lecture rétablie les rallume ; la base reste habitée sans logement.
        [TestCase("logement nul", false, null)] [TestCase("inconnue", false, null)] [TestCase("inconnue", true, "occupation inconnue")] [TestCase("chantier", true, "maison achevée")]
        [TestCase("atelier", true, "maison achevée")] [TestCase("identifiant", true, "introuvable")] [TestCase("rang", false, "introuvable")] [TestCase("foyer", false, "foyer")]
        [TestCase("compte", false, "compte de base")] [TestCase("plan absent", false, "plan absent")] [TestCase("bourg absent", true, "bourg absent")] [TestCase("occupation absente", true, "occupation absente")]
        [TestCase("cellule", false, "cellule")] [TestCase("rang bourg", false, "rang 0")] [TestCase("tick plan", true, "tick")] [TestCase("tick bourg", false, "tick")] [TestCase("tick occupation", true, "tick")]
        [TestCase("tick local", false, "tick")] [TestCase("lampe dehors", true, "références")] [TestCase("spot", false, "références")] [TestCase("", true, "heure", float.NaN)] [TestCase("", false, "heure", 22.5f)] [TestCase("", true, "heure", 11.9f)]
        public void UnRefusEteintLesDeuxEtNommeSaCause779(string cas, bool bati, string cause, float heure = 21f)
        {
            var e = Maison779(2, out var f, out var l); if (bati) e.PourLeBatiment(f, l, 5, 10); else e.PourLaBase(f, l, 5, 1, 2);
            Assert.That(Lire779(e), Is.True, e.Cause); Voir779(f, l, true, Configuree);
            if (cas == "lampe dehors") l.transform.SetParent(null); if (cas == "spot") l.type = LightType.Spot;
            Assert.That(Lire779(e, heure, cas), Is.EqualTo(cause == null)); Voir779(f, l, cause == null, cause == null ? Configuree : 0f);
            if (cause != null) Assert.That(e.Cause, Does.Contain(cause)); l.transform.SetParent(e.transform); l.type = LightType.Point;
            Assert.That(Lire779(e), Is.True, e.Cause); Voir779(f, l, true, Configuree);
        }

        [Test]
        public void LesEffetsRestentLocauxEtStables779()
        {
            var e = Maison779(4, out var f, out var l); var temoin = Maison779(5, out var tf, out var tl); tl.intensity = 1.3f; bool emet = tf.isEmitting;
            e.PourLeBatiment(f, l, 5, 10); int enfants = e.transform.childCount, particules = -1;
            for (int i = 0; i < 10; i++)
            {
                Assert.That(Lire779(e, 19.6f), Is.True, e.Cause); Assert.That(e.Fumee, Is.SameAs(f)); Assert.That(e.Lampe, Is.SameAs(l)); Assert.That(e.transform.childCount, Is.EqualTo(enfants));
                Assert.That(l.intensity, Is.EqualTo(Configuree / 2).Within(1e-4)); Assert.That(f.isEmitting, Is.True); if (particules < 0) { f.Simulate(1f, true, false); particules = f.particleCount; }
                Assert.That(particules, Is.GreaterThan(0)); Assert.That(f.particleCount, Is.EqualTo(particules), "une fumée active n'est pas relancée");
            }
            Assert.That(tl.intensity, Is.EqualTo(1.3f)); Assert.That(tl.enabled, Is.True); Assert.That(tf.isEmitting, Is.EqualTo(emet));
            e.enabled = false; Voir779(f, l, false, 0f); Assert.That(Lire779(e), Is.False);
            e.enabled = true; Assert.That(Lire779(e), Is.True, e.Cause); Voir779(f, l, true, Configuree);
            var maison = e.gameObject; Object.DestroyImmediate(e); Voir779(f, l, false, 0f); Assert.That(maison != null && f != null && l != null && temoin != null, Is.True);
        }
    }
}
