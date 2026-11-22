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
        const string TERRE = "seigneurie-42";
        static FicheJouable Fiche(string id) => new FicheJouable(id, "Maison de test", "seigneurie", 1, new IdentiteDePays(id, "Terre de test"),
            new[] { new IdentiteDePays(id, "Terre de test") }, new SiegeJouable("Siège de test", "Siège de test", 7), null, new VilleJouable(false, null, "la ville de test n'est pas bâtie"));
        static Lecture<JouablesLus> Jouables() => Lecture<JouablesLus>.De(new JouablesLus(3, new DateDuMonde(1400, 4), new[] { Fiche(TERRE), Fiche("identifiant-servi") }));
        static Lecture<MaisonLue> Maison(string id) => Lecture<MaisonLue>.De(new MaisonLue(id,
            "Nom reçu", new SiegeDeMaison(7, 0, "Siège reçu", new PointCarte(0, 0)),
            new[] { new LieuTenu(7, 0) }, new Dictionary<string, string>()));

        [Test] public async Task LeChoixAttendLeMondeEtNeSeDeposeQuUneFois()
        {
            int envois = 0; string retenue = null;
            var lecture = new LecturePartie(() => Monde(retenue), Maison, Jouables,
                id => { Assert.That(id, Is.EqualTo(TERRE)); envois++; return RecuIntention.AccepteeAu(4); });
            Assert.That(lecture.PeutChoisir, Is.False);
            await lecture.Actualiser();
            Assert.That(lecture.PeutChoisir, Is.True);
            await lecture.Choisir(TERRE);
            await lecture.Choisir(TERRE);
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
                Maison, Jouables, _ => throw new Exception("aucun envoi attendu"));
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
            var lecture = new LecturePartie(() => Monde(), Maison, Jouables,
                _ => { envois++; return RecuIntention.Refusee(409, "Choix déjà engagé"); });
            await lecture.Actualiser();
            await lecture.Choisir("seigneurie-999");
            Assert.That(envois, Is.Zero);
            await lecture.Choisir(TERRE);
            Assert.That(lecture.Recu.Erreur, Is.EqualTo("Choix déjà engagé"));
            Assert.That(lecture.Maison, Is.Null);
        }

        [Test] public async Task UneLectureRetardeeNeDoublePasLesRequetes()
        {
            using var attente = new ManualResetEventSlim(false);
            int appels = 0;
            var lecture = new LecturePartie(() => { Interlocked.Increment(ref appels); attente.Wait(3000); return Monde(); },
                Maison, Jouables, _ => RecuIntention.Absente("Panne"));
            var premiere = lecture.Actualiser();
            try { await lecture.Actualiser(); Assert.That(lecture.Occupee, Is.True); }
            finally { attente.Set(); await premiere; }
            Assert.That(appels, Is.EqualTo(1));
        }

        // Les comptes de la maison du joueur se lisent au même passage que le monde, jamais sans maison.
        [Test] public async Task Les_comptes_se_lisent_avec_la_maison()
        {
            int appels = 0; string recu = null, retenue = null;
            var lecture = new LecturePartie(() => Monde(retenue), Maison, Jouables, _ => RecuIntention.Absente("aucun envoi"),
                id => { appels++; recu = id; return Lecture<ComptesDeMaison>.De(new ComptesDeMaison(Maison(id).Donnees, null, 0.25, new Dictionary<string, double>(), new FluxDeMaison(0, 0, 0, 0, 0, 0, 0, null), 3)); });
            await lecture.Actualiser();
            Assert.That(lecture.Comptes, Is.Null); Assert.That(appels, Is.Zero, "aucun compte lu sans maison");
            retenue = "identifiant-servi";
            await lecture.Actualiser();
            Assert.That(appels, Is.EqualTo(1)); Assert.That(recu, Is.EqualTo(retenue));
            Assert.That(lecture.Comptes.Donnees.Maison.Id, Is.EqualTo(retenue)); Assert.That(lecture.Maison.Donnees.Id, Is.EqualTo(retenue));
            var sansLecteur = new LecturePartie(() => Monde(retenue), Maison, Jouables, _ => RecuIntention.Absente("aucun envoi"));
            await sansLecteur.Actualiser();
            Assert.That(sansLecteur.Maison.Donnees.Id, Is.EqualTo(retenue)); Assert.That(sansLecteur.Comptes, Is.Null);
        }

        // Le pays de la maison du joueur se lit au même passage que les comptes, jamais sans maison.
        static Lecture<PaysLu> Pays(string id) => Lecture<PaysLu>.De(new PaysLu(id, "Nom reçu", 3, new DateDuMonde(1400, 4), new Dictionary<string, JaugeLue>(), new Dictionary<string, PointsLus>(), null, "chef non connu", new PoseLue[0]));
        [Test] public async Task Le_pays_se_lit_avec_la_maison()
        {
            int appels = 0; string recu = null, retenue = null;
            var lecture = new LecturePartie(() => Monde(retenue), Maison, Jouables, _ => RecuIntention.Absente("aucun envoi"), null, id => { appels++; recu = id; return Pays(id); });
            await lecture.Actualiser();
            Assert.That(lecture.Pays, Is.Null); Assert.That(appels, Is.Zero, "aucun pays lu sans maison");
            retenue = "identifiant-servi";
            await lecture.Actualiser();
            Assert.That(appels, Is.EqualTo(1)); Assert.That(recu, Is.EqualTo(retenue)); Assert.That(lecture.Pays.Donnees.MaisonId, Is.EqualTo(retenue)); Assert.That(lecture.Comptes, Is.Null);
            var sansLecteur = new LecturePartie(() => Monde(retenue), Maison, Jouables, _ => RecuIntention.Absente("aucun envoi"));
            await sansLecteur.Actualiser();
            Assert.That(sansLecteur.Maison.Donnees.Id, Is.EqualTo(retenue)); Assert.That(sansLecteur.Pays, Is.Null);
            bool coupe = false;
            var coupee = new LecturePartie(() => coupe ? throw new Exception("service coupé") : Monde(retenue), Maison, Jouables, _ => RecuIntention.Absente("aucun envoi"), null, Pays);
            await coupee.Actualiser(); Assert.That(coupee.Pays, Is.Not.Null);
            coupe = true; await coupee.Actualiser(); Assert.That(coupee.Pays, Is.Null); Assert.That(coupee.Monde.Presente, Is.False);
        }

        // Les terres du pays se lisent au même passage que le pays, juste après lui, jamais sans maison.
        static Lecture<TerresDuPays> Terres(string id) => Lecture<TerresDuPays>.De(new TerresDuPays(id, 3, new DateDuMonde(1400, 4), null, new string[0], new string[0],
            new[] { new LieuDuPays(7, 0) }, new LieuDuPays[0], 1, 12, 12, 0, 0, 0, null, "grenier absent pour la maison " + id, new BatimentDuPays[0]));
        [Test] public async Task Les_terres_se_lisent_avec_le_pays()
        {
            var appels = new List<string>(); string retenue = null;
            var lecture = new LecturePartie(() => Monde(retenue), Maison, Jouables, _ => RecuIntention.Absente("aucun envoi"), null,
                id => { appels.Add("pays " + id); return Pays(id); }, id => { appels.Add("terres " + id); return Terres(id); });
            await lecture.Actualiser();
            Assert.That(lecture.Terres, Is.Null); Assert.That(appels, Is.Empty, "ni pays ni terres lus sans maison");
            retenue = "identifiant-servi";
            await lecture.Actualiser();
            Assert.That(appels, Is.EqualTo(new[] { "pays identifiant-servi", "terres identifiant-servi" }), "un appel avec cet identifiant, après celui du pays");
            Assert.That(lecture.Terres.Donnees.MaisonId, Is.EqualTo(retenue)); Assert.That(lecture.Pays.Donnees.MaisonId, Is.EqualTo(retenue));
            var sixParametres = new LecturePartie(() => Monde(retenue), Maison, Jouables, _ => RecuIntention.Absente("aucun envoi"), null, Pays);
            await sixParametres.Actualiser();
            Assert.That(sixParametres.Pays, Is.Not.Null); Assert.That(sixParametres.Terres, Is.Null);
            bool coupe = false;
            var coupee = new LecturePartie(() => coupe ? throw new Exception("service coupé") : Monde(retenue), Maison, Jouables, _ => RecuIntention.Absente("aucun envoi"), null, Pays, Terres);
            await coupee.Actualiser(); Assert.That(coupee.Terres, Is.Not.Null);
            coupe = true; await coupee.Actualiser(); Assert.That(coupee.Terres, Is.Null);
        }

        // Les gestes du pays se lisent au même passage que les terres, juste après elles, jamais sans maison.
        static Lecture<GestesDuPays> Gestes(string id) => Lecture<GestesDuPays>.De(new GestesDuPays(Pays(id).Donnees,
            new[] { new GesteLu("asseoir_le_droit", "Asseoir le droit", new Dictionary<string, double> { { "sceau", 30 } }, new Dictionary<string, double> { { "droit", 10 } }, null) }));
        [Test] public async Task Les_gestes_se_lisent_avec_les_terres()
        {
            var appels = new List<string>(); string retenue = null;
            var lecture = new LecturePartie(() => Monde(retenue), Maison, Jouables, _ => RecuIntention.Absente("aucun envoi"), null,
                id => { appels.Add("pays " + id); return Pays(id); }, id => { appels.Add("terres " + id); return Terres(id); }, id => { appels.Add("gestes " + id); return Gestes(id); });
            await lecture.Actualiser();
            Assert.That(lecture.Gestes, Is.Null); Assert.That(appels, Is.Empty, "aucun appel au lecteur sans maison");
            retenue = "identifiant-servi";
            await lecture.Actualiser();
            Assert.That(appels, Is.EqualTo(new[] { "pays identifiant-servi", "terres identifiant-servi", "gestes identifiant-servi" }), "un appel avec cet identifiant, après celui des terres");
            Assert.That(lecture.Gestes.Donnees.MaisonId, Is.EqualTo(retenue)); Assert.That(lecture.Gestes.Donnees.Gestes.Count, Is.EqualTo(1));
            var septParametres = new LecturePartie(() => Monde(retenue), Maison, Jouables, _ => RecuIntention.Absente("aucun envoi"), null, Pays, Terres);
            await septParametres.Actualiser();
            Assert.That(septParametres.Terres, Is.Not.Null); Assert.That(septParametres.Gestes, Is.Null);
            bool coupe = false;
            var coupee = new LecturePartie(() => coupe ? throw new Exception("service coupé") : Monde(retenue), Maison, Jouables, _ => RecuIntention.Absente("aucun envoi"), null, Pays, Terres, Gestes);
            await coupee.Actualiser(); Assert.That(coupee.Gestes, Is.Not.Null);
            coupe = true; await coupee.Actualiser(); Assert.That(coupee.Gestes, Is.Null);
        }

        // Sans maison, les jouables se relisent à chaque jour servi ; avec une maison, une seule fois pour elle, et sa fiche se lit.
        [Test] public async Task Les_jouables_se_relisent_chaque_jour_puis_une_fois_par_maison()
        {
            int appels = 0; string retenue = null; long jour = 3; bool panne = false;
            Lecture<MondeAvecMaisonLu> Lu() => Lecture<MondeAvecMaisonLu>.De(new MondeAvecMaisonLu(new MondeLu(jour, new DateDuMonde(1400, (int)jour + 1), 1, new[] { new CelluleDuMonde(7, 12, -1, -1) }), retenue));
            var lecture = new LecturePartie(Lu, Maison, () => { appels++; return panne ? Lecture<JouablesLus>.Absent("jouables : statut 500") : Jouables(); }, _ => RecuIntention.Absente("aucun envoi"));
            await lecture.Actualiser(); await lecture.Actualiser();
            Assert.That(appels, Is.EqualTo(1), "le même jour, sans maison, une seule lecture"); Assert.That(lecture.Jouable, Is.Null, "aucune fiche sans maison");
            jour = 4; await lecture.Actualiser(); Assert.That(appels, Is.EqualTo(2), "un jour nouveau relit les jouables");
            retenue = "identifiant-servi"; await lecture.Actualiser(); jour = 5; await lecture.Actualiser(); await lecture.Actualiser();
            Assert.That(appels, Is.EqualTo(3), "avec une maison, une seule lecture pour elle"); Assert.That(lecture.Jouable.Id, Is.EqualTo(retenue));
            Assert.That(lecture.Jouable.Pays.Nom, Is.EqualTo("Terre de test"));
            retenue = TERRE; panne = true; await lecture.Actualiser();
            Assert.That(lecture.Jouables.Presente, Is.False); Assert.That(lecture.Jouable, Is.Null);
            panne = false; await lecture.Actualiser(); Assert.That(appels, Is.EqualTo(5), "une lecture manquée se relit au passage suivant"); Assert.That(lecture.Jouable.Id, Is.EqualTo(TERRE));
        }

        [Test] public void Le_choix_part_par_l_identifiant_de_la_maison()
        {
            Assert.That(LecturePartie.IntentionDeChoix("grande-3"), Is.EqualTo("{\"type\":\"choisir_depart\",\"maison\":\"grande-3\"}"));
            var lu = LecteurJson.LireObjet(LecturePartie.IntentionDeChoix("a\"b\\c"));
            Assert.That(lu["maison"], Is.EqualTo("a\"b\\c"), "l'identifiant s'échappe");
        }
    }
}
