using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Forge.Pont;
using NUnit.Framework;

namespace Forge.Interface.Tests
{
    public sealed class LecturePartieTests
    {
        static Lecture<MondeAvecMaisonLu> Monde(string maison = null) => Lecture<MondeAvecMaisonLu>.De(
            new MondeAvecMaisonLu(new MondeLu(3, new DateDuMonde(1400, 4), 1,
                new[] { new CelluleDuMonde(7, 12, -1, -1) }), maison));
        static Lecture<DepartsLus> Departs() => Lecture<DepartsLus>.De(new DepartsLus(3,
            new DateDuMonde(1400, 4), new[] { new FicheDeDepart(42, "Terre de test", "Maison de test",
                new SiegeDeDepart("Siège de test", 0, 0), 7, 12, null, new VoisinDeDepart[0]) }));
        static Lecture<MaisonLue> Maison(string id) => Lecture<MaisonLue>.De(new MaisonLue(id,
            "Nom reçu", new SiegeDeMaison(7, 0, "Siège reçu", new PointCarte(0, 0)),
            new[] { new LieuTenu(7, 0) }, new Dictionary<string, string>()));

        [Test] public async Task LeChoixAttendLeMondeEtNeSeDeposeQuUneFois()
        {
            int envois = 0; string retenue = null;
            var lecture = new LecturePartie(() => Monde(retenue), Maison, Departs,
                id => { Assert.That(id, Is.EqualTo(42)); envois++; return RecuIntention.AccepteeAu(4); });
            Assert.That(lecture.PeutChoisir, Is.False);
            await lecture.Actualiser();
            Assert.That(lecture.PeutChoisir, Is.True);
            await lecture.Choisir(42);
            await lecture.Choisir(42);
            Assert.That(envois, Is.EqualTo(1));
            Assert.That(lecture.Maison, Is.Null, "un reçu ne prouve pas une maison appliquée");
            Assert.That(lecture.PeutChoisir, Is.False);
            retenue = "identifiant-servi";
            await lecture.Actualiser();
            Assert.That(lecture.Maison.Donnees.Id, Is.EqualTo(retenue));
            Assert.That(lecture.Maison.Donnees.Nom, Is.EqualTo("Nom reçu"));
        }

        [Test] public async Task UneCoupureEffaceLaMaisonEtInterditLeChoix()
        {
            bool coupe = false;
            var lecture = new LecturePartie(() => coupe ? Lecture<MondeAvecMaisonLu>.Absent("Service coupé") : Monde("maison"),
                Maison, Departs, _ => throw new Exception("aucun envoi attendu"));
            await lecture.Actualiser();
            Assert.That(lecture.Maison.Donnees.Nom, Is.EqualTo("Nom reçu"));
            coupe = true;
            await lecture.Actualiser();
            Assert.That(lecture.Maison, Is.Null);
            Assert.That(lecture.Monde.Absence, Is.EqualTo("Service coupé"));
            Assert.That(lecture.PeutChoisir, Is.False);
        }

        [Test] public async Task UnRefusConserveSaRaisonEtUnIdHorsListeNePartPas()
        {
            int envois = 0;
            var lecture = new LecturePartie(() => Monde(), Maison, Departs,
                _ => { envois++; return RecuIntention.Refusee(409, "Choix déjà engagé"); });
            await lecture.Actualiser();
            await lecture.Choisir(999);
            Assert.That(envois, Is.Zero);
            await lecture.Choisir(42);
            Assert.That(lecture.Recu.Erreur, Is.EqualTo("Choix déjà engagé"));
            Assert.That(lecture.Maison, Is.Null);
        }

        [Test] public async Task UneLectureRetardeeNeDoublePasLesRequetes()
        {
            using var attente = new ManualResetEventSlim(false);
            int appels = 0;
            var lecture = new LecturePartie(() => { Interlocked.Increment(ref appels); attente.Wait(3000); return Monde(); },
                Maison, Departs, _ => RecuIntention.Absente("Panne"));
            var premiere = lecture.Actualiser();
            try { await lecture.Actualiser(); Assert.That(lecture.Occupee, Is.True); }
            finally { attente.Set(); await premiere; }
            Assert.That(appels, Is.EqualTo(1));
        }
    }
}
