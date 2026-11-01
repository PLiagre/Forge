using System;
using System.Collections.Generic;
using System.Linq;using NUnit.Framework;using UnityEngine;using Object = UnityEngine.Object;
namespace Forge.Pont.Tests
{
    // Lot #961 — les lampes allumées (les plus proches, sous un plafond), les fumées en pause (strictement au-delà d'une distance),
    // et un composant qui ne touche qu'aux effets qu'on lui donne.
    public sealed class EffetsAuLoinTests
    {
        static Vector3[] SurX(params float[] x) => x.Select(v => new Vector3(v, 0f, 0f)).ToArray();
        static bool[] Toutes(int n) => Enumerable.Repeat(true, n).ToArray();
        static bool[] Lampes(Vector3[] p, bool[] voulues, int plafond) => EffetsAuLoin.LampesAllumees(Vector3.zero, p, voulues, plafond);

        [Test] public void Plafond()
        {
            var p = SurX(6, 1, 5, 2, 4, 3); var avant = (Vector3[])p.Clone(); var voulues = Toutes(6);
            CollectionAssert.AreEqual(new[] { false, true, false, true, false, true }, Lampes(p, voulues, 3));
            CollectionAssert.AreEqual(avant, p); CollectionAssert.AreEqual(Toutes(6), voulues);
        }
        [Test] public void NonVoulue() => CollectionAssert.AreEqual(new[] { false, true, true, false }, Lampes(SurX(1, 2, 3, 4), new[] { false, true, true, true }, 2));
        [Test] public void Egalite() => CollectionAssert.AreEqual(new[] { true, true, false }, Lampes(new[] { new Vector3(0, 0, -5), new Vector3(0, 5, 0), new Vector3(5, 0, 0) }, Toutes(3), 2));
        [Test] public void PlafondZero() => CollectionAssert.AreEqual(new[] { false, false, false }, Lampes(SurX(1, 2, 3), new[] { true, false, true }, 0));
        [Test] public void PlafondCent() => CollectionAssert.AreEqual(new[] { true, false, true }, Lampes(SurX(1, 2, 3), new[] { true, false, true }, 100));
        [Test] public void Distance()
        {
            CollectionAssert.AreEqual(new[] { false, false, true }, EffetsAuLoin.FumeesEnPause(Vector3.zero, SurX(59.9f, 60f, 60.1f), 60f));
            // En 3D : au-dessus de l'œil (60,5 m de haut), ou à 59 m au sol mais 20 m plus haut, la fumée est au-delà.
            CollectionAssert.AreEqual(new[] { true, true }, EffetsAuLoin.FumeesEnPause(new Vector3(3, 1, 2), new[] { new Vector3(3, 61.5f, 2), new Vector3(3, 21, 61) }, 60f));
        }
        static readonly Vector3 Nan = new Vector3(float.NaN, 0, 0), Infini = new Vector3(0, float.PositiveInfinity, 0);
        [TestCase(0, typeof(ArgumentNullException))] [TestCase(1, typeof(ArgumentNullException))] [TestCase(2, typeof(ArgumentNullException))]
        [TestCase(3, typeof(ArgumentException))] [TestCase(4, typeof(ArgumentException))] [TestCase(5, typeof(ArgumentException))]
        [TestCase(6, typeof(ArgumentException))] [TestCase(7, typeof(ArgumentException))] [TestCase(8, typeof(ArgumentOutOfRangeException))]
        [TestCase(9, typeof(ArgumentOutOfRangeException))] [TestCase(10, typeof(ArgumentOutOfRangeException))] [TestCase(11, typeof(ArgumentOutOfRangeException))]
        [TestCase(12, typeof(ArgumentOutOfRangeException))]
        public void Refus(int cas, Type attendu)
        {
            var p = SurX(1, 2); var v = Toutes(2);
            TestDelegate[] appels = {
                () => Lampes(null, v, 1), () => Lampes(p, null, 1), () => EffetsAuLoin.FumeesEnPause(Vector3.zero, null, 60f),
                () => Lampes(p, Toutes(3), 1), () => EffetsAuLoin.LampesAllumees(Nan, p, v, 1), () => Lampes(new[] { Vector3.one, Infini }, v, 1),
                () => EffetsAuLoin.FumeesEnPause(Infini, p, 60f), () => EffetsAuLoin.FumeesEnPause(Vector3.zero, new[] { Nan }, 60f), () => Lampes(p, v, -1),
                () => EffetsAuLoin.FumeesEnPause(Vector3.zero, p, 0f), () => EffetsAuLoin.FumeesEnPause(Vector3.zero, p, -1f), () => EffetsAuLoin.FumeesEnPause(Vector3.zero, p, float.NaN),
                () => EffetsAuLoin.FumeesEnPause(Vector3.zero, p, float.PositiveInfinity) };
            Assert.Throws(attendu, appels[cas]);
        }

        readonly List<GameObject> objets = new List<GameObject>();
        GameObject Objet(string nom) { var o = new GameObject(nom); objets.Add(o); return o; }
        [TearDown] public void Detruire() { foreach (var o in objets) if (o) Object.DestroyImmediate(o); objets.Clear(); }
        [Test] public void ComposantNeToucheQueSesEffets()
        {
            var camera = Objet("Œil").AddComponent<Camera>(); var lampes = new List<Light>();
            for (int i = 1; i <= 4; i++)
            { var l = Objet("Lampe " + i).AddComponent<Light>(); l.type = LightType.Point; l.intensity = 8f; l.enabled = true; l.transform.position = new Vector3(i, 0, 0); lampes.Add(l); }
            var c = Objet("Effets au loin").AddComponent<EffetsAuLoin>(); c.Configurer(camera, new List<EffetsDeMaison>());
            Assert.AreEqual(OptimisationsDeLaVille.Lire(Environment.GetCommandLineArgs()), c.Actif); Assert.AreEqual(0, c.Effets); Assert.AreSame(camera, c.Camera);
            c.Regler();
            foreach (var l in lampes) { Assert.IsTrue(l.enabled, l.name); Assert.AreEqual(8f, l.intensity, l.name); }
        }
        [TestCase(0)] [TestCase(1)] [TestCase(2)]
        public void ConfigurerRefuseLeNul(int cas)
        {
            var camera = Objet("Œil").AddComponent<Camera>(); var c = Objet("Effets au loin").AddComponent<EffetsAuLoin>();
            TestDelegate[] appels = { () => c.Configurer(null, new List<EffetsDeMaison>()), () => c.Configurer(camera, null), () => c.Configurer(camera, new EffetsDeMaison[] { null }) };
            Assert.Throws<ArgumentNullException>(appels[cas]);
        }
    }
}
