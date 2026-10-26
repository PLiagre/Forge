using System;
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;

namespace Forge.Pont.Tests
{
    // Lot #784 — un passant pour dix habitants du bourg (rang 0, jamais la première entrée ni la
    // cellule), réparti par métier au plus grand reste. Les foyers valent personnes / 3 + 1 :
    // ni le cinquième des personnes, ni une source acceptable du compte.
    public sealed class PassantsDuBourgTests
    {
        private const long Max = 9007199254740991; // 2^53 − 1

        private static Dictionary<string, (long Foyers, long Personnes)> M(params (string Nom, long Personnes)[] metiers) =>
            metiers.ToDictionary(m => m.Nom, m => (m.Personnes / 3 + 1, m.Personnes));

        private static readonly (string, long)[] Temoin = { ("artisans", 19), ("mineurs", 24), ("paysans", 957) };

        private static LieuPlace[] Places(long? bourg) =>
            new[] { new LieuPlace(1, null, null, population: 300), new LieuPlace(0, null, null, population: bourg) };

        private static LectureLieu L(long cellule, long? bourg, Dictionary<string, (long, long)> foyers,
            EtatFoyers sansMetiers = EtatFoyers.Absents, long tick = 3, IEnumerable<LieuPlace> lieux = null) =>
            LectureLieu.De(new Lieu(9922, tick, 1400, 1, cellule, new Dictionary<string, double>(), 0, 0,
                foyers != null ? EtatFoyers.Servis : sansMetiers, foyers, null, lieux ?? Places(bourg)));

        private static void Parts(PassantsDuBourg p, long nombre, params (string, long)[] parts)
        {
            Assert.IsTrue(p.Presente, p.Absence);
            Assert.IsNull(p.Absence);
            Assert.AreEqual(nombre, p.Nombre);
            CollectionAssert.AreEqual(parts.Select(x => new KeyValuePair<string, long>(x.Item1, x.Item2)), p.ParMetier);
            Assert.AreEqual(nombre, p.ParMetier.Values.Sum());
        }

        [TestCase(0, 0), TestCase(1, 0), TestCase(9, 0), TestCase(10, 1), TestCase(19, 1), TestCase(20, 2), TestCase(109, 10)]
        public void LeTotalEstLaPopulationDuBourgDiviseeParDixAuPlancher(long bourg, long attendu)
        {
            Assert.AreEqual(10, PassantsDuBourg.HABITANTS_PAR_PASSANT);
            var p = PassantsDuBourg.Projeter(L(1000, bourg, M(Temoin)));
            Assert.IsTrue(p.Presente, p.Absence);
            Assert.AreEqual(attendu, p.Nombre);
            Assert.AreEqual(attendu, p.ParMetier.Values.Sum());
        }

        [Test]
        public void LaRepartitionSuitLesPoidsAuPlusGrandResteSansDependreDeLOrdre()
        {
            Parts(PassantsDuBourg.Projeter(L(1000, 109, M(Temoin))), 10, ("artisans", 2), ("mineurs", 2), ("paysans", 6));
            // Égalité de reste : le nom ordinal départage ; un poids positif reste, même à zéro passant.
            var endroit = PassantsDuBourg.Projeter(L(1000, 10, M(("forgerons", 5), ("mineurs", 5), ("paysans", 990))));
            var envers = PassantsDuBourg.Projeter(L(1000, 10, M(("paysans", 990), ("mineurs", 5), ("forgerons", 5))));
            Parts(endroit, 1, ("forgerons", 1), ("mineurs", 0));
            Parts(envers, 1, ("forgerons", 1), ("mineurs", 0));
            // Les non-paysans dépassent le bourg : des poids, aucun paysan local inventé.
            Parts(PassantsDuBourg.Projeter(L(1000, 20, M(Temoin))), 2, ("artisans", 1), ("mineurs", 1));
            Parts(PassantsDuBourg.Projeter(L(1000, 30, M(("verriers", 12), ("paysans", 988)))), 3, ("paysans", 2), ("verriers", 1));
        }

        [Test]
        public void ChaqueLectureEstReprojeteeSansMemoire()
        {
            var r19 = PassantsDuBourg.Projeter(L(1000, 19, M(Temoin), tick: 1));
            var r20 = PassantsDuBourg.Projeter(L(1000, 20, M(Temoin), tick: 2));
            var r9 = PassantsDuBourg.Projeter(L(1000, 9, M(Temoin), tick: 3));
            Parts(PassantsDuBourg.Projeter(L(1000, 0, M(Temoin), tick: 4)), 0);
            Parts(PassantsDuBourg.Projeter(L(1000, 109, M(("artisans", 60), ("mineurs", 0), ("paysans", 940)), tick: 5)), 10, ("artisans", 6), ("paysans", 4));
            var absente = PassantsDuBourg.Projeter(LectureLieu.Absent("service absent sur 127.0.0.1:8000"));
            Assert.IsFalse(absente.Presente);
            Assert.IsNull(absente.Nombre);
            Assert.IsNull(absente.ParMetier);
            StringAssert.Contains("service absent", absente.Absence);
            Parts(PassantsDuBourg.Projeter(L(1000, 109, M(Temoin), tick: 6)), 10, ("artisans", 2), ("mineurs", 2), ("paysans", 6));
            Parts(r19, 1, ("artisans", 0), ("mineurs", 1));
            Parts(r20, 2, ("artisans", 1), ("mineurs", 1));
            Parts(r9, 0, ("artisans", 0), ("mineurs", 0));
            Assert.Throws<NotSupportedException>(() => ((IDictionary<string, long>)r20.ParMetier)["artisans"] = 5);
            Assert.Throws<NotSupportedException>(() => ((IDictionary<string, long>)r20.ParMetier).Clear());
            Parts(r20, 2, ("artisans", 1), ("mineurs", 1));
        }

        [Test]
        public void UnBourgVideEstUnZeroMesureEtLesGrandsComptesRestentExacts()
        {
            Parts(PassantsDuBourg.Projeter(L(1000, 0, null)), 0);
            Parts(PassantsDuBourg.Projeter(L(1000, 0, null, EtatFoyers.NonCalcules)), 0);
            Parts(PassantsDuBourg.Projeter(L(0, 0, M())), 0);
            var grand = new[] { new LieuPlace(0, null, null, population: Max) };
            Parts(PassantsDuBourg.Projeter(L(Max, Max, M(("mineurs", Max)), lieux: grand)), 900719925474099, ("mineurs", 900719925474099));
            Parts(PassantsDuBourg.Projeter(L(Max, Max, M(("paysans", Max)), lieux: grand)), 900719925474099, ("paysans", 900719925474099));
        }

        [Test]
        public void UneLectureInexploitableRendUneAbsenceNommee()
        {
            var cas = new (LectureLieu Lecture, string Cause)[]
            {
                (null, "lecture nulle"),
                (LectureLieu.Absent("statut 404"), "statut 404"),
                (LectureLieu.De(new Lieu(9922, 3, 1400, 1, 1000, new Dictionary<string, double>(), 0, 0, absenceDesLieux: "clé absente : lieux")), "clé absente : lieux"),
                (L(1000, 109, M(Temoin), lieux: new LieuPlace[0]), "rang 0"),
                (L(1000, 109, M(Temoin), lieux: new[] { new LieuPlace(1, null, null, population: 109) }), "rang 0"),
                (L(1000, null, M(Temoin)), "population non fournie"),
                (L(1000, -1, M(Temoin)), "hors de 0..2^53 − 1"),
                (L(Max + 1, Max + 1, M(("paysans", Max + 1))), "hors de 0..2^53 − 1"),
                (L(1000, 109, null), "métiers absents"),
                (L(1000, 109, null, EtatFoyers.NonCalcules), "métiers non calculés"),
                (L(1000, 109, M(("artisans", 19), (" ", 24), ("paysans", 957))), "nom de métier blanc"),
                (L(1000, 109, M(("artisans", -19), ("mineurs", 62), ("paysans", 957))), "négatif"),
                (L(1000, 109, M(("artisans", 19), ("mineurs", 24), ("paysans", 950))), "somme des métiers 993"),
                (L(1000, 1001, M(Temoin)), "dépasse la cellule"),
            };
            foreach (var (lecture, cause) in cas)
            {
                var p = PassantsDuBourg.Projeter(lecture);
                Assert.IsFalse(p.Presente, cause);
                Assert.IsNull(p.Nombre, cause);
                Assert.IsNull(p.ParMetier, cause);
                StringAssert.Contains(cause, p.Absence);
            }
        }
    }
}
