using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Forge.Pont;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using UnityEngine.UI;

namespace Forge.Interface.Tests
{
    // Lot #1045 — le feuillet « Le pays » écrit ce que `/pays` sert au tick du monde lu, en noms, ou attend sans rien inventer.
    public sealed class DossierPaysTests
    {
        const string GRANDE = "grande-3", BAR = "seigneurie-1", MAULEON = "plausible-7-0", SANS_NOM = "plausible-8-1";
        const string Maisons = "{\"tick\":31,\"nombre\":4,\"maisons\":[{\"id\":\"grande-3\",\"nom\":\"Valois\"},{\"id\":\"seigneurie-1\",\"nom\":\"Bar\"},{\"id\":\"plausible-7-0\",\"nom\":\"Mauléon\"},{\"id\":\"plausible-8-1\",\"nom\":null}]}";
        // Le texte du pays témoin : grande-3 au tick 31, date (1400, 32).
        const string TexteTemoin =
            "Valois · relevé au jour 32 de 1400\nSuzerain : aucun\nVassaux : 2 maisons\n\n"
            + "GENS ET GRAIN\nLieux : 7 lieux, dont 4 lieux tenus en propre\nHabitants : 2 450 344 habitants, dont 271 528 habitants sur ses propres lieux\n"
            + "Récolte des trente derniers jours : 141 440 t de grain\nGrenier : 754 t de vivres\nGreniers des vassaux : 6 863 t de vivres\nChantiers des bourgs : 2 chantiers en cours\n\n"
            + "BÂTIMENTS\nMoulin à Paris : achevé\nMoulin à Bar-le-Duc, de Bar : en chantier, 20 jours de travail sur 600 jours\n\n"
            + "SES LIEUX\nParis et 2 lieux : Saint-Denis, Vincennes\nAutour de Melun : Corbeil\n\n"
            + "SES VASSAUX\nBar, Mauléon\nPar leurs vassaux (1 maison) : maison non nommée\n\n"
            + "LIEUX DE SES VASSAUX\nBar-le-Duc\nToul et 1 lieu : Foug";
        static readonly Dictionary<(long, long), string> NomsTemoin = new Dictionary<(long, long), string>
        {
            [(10, 0)] = "Paris", [(10, 1)] = "Saint-Denis", [(10, 2)] = "Vincennes", [(11, 0)] = "Melun", [(11, 1)] = "Corbeil",
            [(12, 0)] = "Bar-le-Duc", [(13, 0)] = "Toul", [(13, 3)] = "Foug",
        };
        static string Lieu(long c, long r) => NomsTemoin[(c, r)];
        static LieuDuPays L(long c, long r) => new LieuDuPays(c, r);
        static Lecture<MondeAvecMaisonLu> Monde(long tick = 31, string maison = GRANDE) => Lecture<MondeAvecMaisonLu>.De(new MondeAvecMaisonLu(
            new MondeLu(tick, new DateDuMonde(1400, tick + 1), 1, new[] { new CelluleDuMonde(10, 1, -1, -1) }), maison));
        static TerresDuPays PaysTemoin(long tick = 31, string maison = GRANDE, double? grenier = 754362.1, string absence = null) => new TerresDuPays(maison, tick, new DateDuMonde(1400, tick + 1), null,
            new[] { BAR, MAULEON }, new[] { BAR, MAULEON, SANS_NOM }, new[] { L(10, 0), L(10, 1), L(10, 2), L(11, 1) }, new[] { L(12, 0), L(13, 0), L(13, 3) },
            7, 2450344, 271528, 2, 141439858.6, 6862501.4, grenier, absence,
            new[] { new BatimentDuPays(1, "moulin", "Moulin", 10, GRANDE, 600, 600, false), new BatimentDuPays(2, "moulin", "Moulin", 12, BAR, 600, 20, true) });
        static Lecture<TerresDuPays> Terres(long tick = 31, string maison = GRANDE) => Lecture<TerresDuPays>.De(PaysTemoin(tick, maison));
        static Lecture<IReadOnlyDictionary<string, string>> Registre(params (string id, string nom)[] maisons) =>
            Lecture<IReadOnlyDictionary<string, string>>.De(maisons.ToDictionary(m => m.id, m => m.nom));
        static Lecture<IReadOnlyDictionary<string, string>> RegistreTemoin() => Registre((GRANDE, "Valois"), (BAR, "Bar"), (MAULEON, "Mauléon"), (SANS_NOM, null));
        static string D(Lecture<TerresDuPays> terres, Lecture<IReadOnlyDictionary<string, string>> registre = null, Func<long, long, string> noms = null) =>
            DossierPays.Decrire(Monde(), terres, registre ?? RegistreTemoin(), noms ?? Lieu);

        [Test] public void Le_feuillet_ecrit_le_pays_en_noms()
        {
            string texte = D(Terres());
            Assert.That(texte, Is.EqualTo(TexteTemoin));
            Assert.That(TexteDuMonde.Interdit(texte, GRANDE, BAR, MAULEON, SANS_NOM), Is.Null, texte); Assert.That(TexteDuMonde.SansUnite(texte), Is.Null, texte);
        }

        [Test] public void Un_petit_seigneur_a_son_suzerain_et_aucun_vassal()
        {
            var bar = new TerresDuPays(BAR, 31, new DateDuMonde(1400, 32), GRANDE, new string[0], new string[0], new[] { L(12, 0) }, new LieuDuPays[0], 1, 1, 1, 0, 100, 0, 5000.0, null, new BatimentDuPays[0]);
            string texte = DossierPays.Decrire(Monde(31, BAR), Lecture<TerresDuPays>.De(bar), RegistreTemoin(), Lieu);
            var lignes = texte.Split('\n');
            Assert.That(lignes, Does.Contain("Suzerain : Valois")); Assert.That(lignes, Does.Contain("Vassaux : aucun"));
            Assert.That(lignes, Does.Contain("Lieux : 1 lieu, dont 1 lieu tenu en propre")); Assert.That(lignes, Does.Contain("Habitants : 1 habitant, dont 1 habitant sur ses propres lieux"));
            foreach (string titre in new[] { "BÂTIMENTS", "SES VASSAUX", "LIEUX DE SES VASSAUX" }) Assert.That(lignes[Array.IndexOf(lignes, titre) + 1], Is.EqualTo("aucun"), titre);
            Assert.That(lignes, Has.None.StartsWith("Par leurs vassaux")); Assert.That(lignes[Array.IndexOf(lignes, "SES LIEUX") + 1], Is.EqualTo("Bar-le-Duc"));
            Assert.That(TexteDuMonde.Interdit(texte, GRANDE, BAR), Is.Null, texte); Assert.That(TexteDuMonde.SansUnite(texte), Is.Null, texte);
        }

        [Test] public void Un_royaume_tient_dans_le_feuillet()
        {
            var vassaux = Enumerable.Range(0, 115).Select(i => "vassal-" + i).ToArray();
            var maisons = new List<(string, string)> { (GRANDE, "Valois") };
            maisons.AddRange(vassaux.Select((v, i) => (v, ("Vassal numero " + i).PadRight(20, 'x'))));
            var lieux = new List<LieuDuPays>();
            for (int terre = 0; terre < 52; terre++) for (int rang = 0; rang < (terre < 35 ? 6 : 5); rang++) lieux.Add(L(1000 + terre, rang));
            Assert.That(lieux.Count, Is.EqualTo(295));
            var pays = new TerresDuPays(GRANDE, 31, new DateDuMonde(1400, 32), null, vassaux.Take(100), vassaux, lieux.Take(40), lieux.Skip(40), 295, 2500000, 300000, 4, 141439858.6, 6862501.4, 754362.1, null, new BatimentDuPays[0]);
            string texte = DossierPays.Decrire(Monde(), Lecture<TerresDuPays>.De(pays), Registre(maisons.ToArray()), (c, r) => ("Lieu " + c + "x" + r).PadRight(14, 'z'));
            Assert.That(texte.Length, Is.LessThanOrEqualTo(16000), "ce qu'un Text d'Unity dessine en entier");
            Assert.That(texte, Does.Contain("Vassaux : 100 maisons")); Assert.That(texte, Does.Contain("Par leurs vassaux (15 maisons) : "));
        }

        [Test] public void Le_feuillet_dit_l_absence_sans_l_inventer()
        {
            const string raison = "grenier absent pour la maison grande-3";
            LogAssert.Expect(LogType.Log, "TexteDuMonde : absence déclarée par le monde : " + raison);
            string sans = DossierPays.Decrire(Monde(), Lecture<TerresDuPays>.De(PaysTemoin(31, GRANDE, null, raison)), RegistreTemoin(), Lieu);
            Assert.That(sans.Split('\n'), Does.Contain("Grenier : déclaré absent par le monde")); Assert.That(sans, Does.Not.Contain(GRANDE));
            string inconnue = D(Terres(), Registre((GRANDE, "Valois"), (MAULEON, "Mauléon"), (SANS_NOM, null)));
            Assert.That(inconnue.Split('\n'), Does.Contain("maison absente du registre, Mauléon"), "dans les vassaux");
            Assert.That(inconnue.Split('\n'), Does.Contain("Moulin à Bar-le-Duc, de maison absente du registre : en chantier, 20 jours de travail sur 600 jours"), "dans le bâtiment");
            string enLecture = D(Terres(), null, (c, r) => NomsDesTerres.NomEnLecture);
            Assert.That(enLecture, Does.Contain("Moulin à nom en cours de lecture : achevé")); Assert.That(enLecture, Does.Contain("nom en cours de lecture et 2 lieux : nom en cours de lecture, nom en cours de lecture"));
            Assert.That(TexteDuMonde.SansUnite(enLecture), Is.Null, "un nom en cours de lecture ne montre pas un nombre nu"); Assert.That(TexteDuMonde.Interdit(enLecture, GRANDE, BAR), Is.Null);
        }

        [Test] public void Le_feuillet_attend_le_meme_tick()
        {
            var registre = RegistreTemoin();
            Assert.That(DossierPays.Decrire(null, Terres(), registre, Lieu), Is.EqualTo("Lecture du pays…"));
            Assert.That(DossierPays.Decrire(Lecture<MondeAvecMaisonLu>.Absent("refus témoin"), Terres(), registre, Lieu), Is.EqualTo("Pays indisponible : refus témoin"));
            Assert.That(DossierPays.Decrire(Monde(31, null), Terres(), registre, Lieu), Is.EqualTo("Choisissez une maison pour lire son pays."));
            foreach (var terres in new[] { null, Terres(30), Terres(32), Terres(31, BAR) })
            {
                string texte = DossierPays.Decrire(Monde(), terres, registre, Lieu);
                Assert.That(texte, Is.EqualTo("Pays en attente du monde")); Assert.That(texte, Does.Not.Contain("Valois"));
            }
            Assert.That(DossierPays.Decrire(Monde(), Lecture<TerresDuPays>.Absent("service coupé"), registre, Lieu), Is.EqualTo("Pays indisponible : service coupé"));
            Assert.That(DossierPays.Decrire(Monde(), Terres(), null, Lieu), Is.EqualTo("Lecture des noms des maisons…"));
            Assert.That(DossierPays.Decrire(Monde(), Terres(), Lecture<IReadOnlyDictionary<string, string>>.Absent("registre coupé"), Lieu), Is.EqualTo("Pays indisponible : registre coupé"));
        }

        [Test] public void Le_registre_se_lit_en_entier()
        {
            var registre = DossierPays.Registre(new DocumentDuMonde(Maisons));
            Assert.That(registre.Count, Is.EqualTo(4)); Assert.That(registre[GRANDE], Is.EqualTo("Valois")); Assert.That(registre[BAR], Is.EqualTo("Bar")); Assert.That(registre[MAULEON], Is.EqualTo("Mauléon"));
            Assert.That(registre.ContainsKey(SANS_NOM) && registre[SANS_NOM] == null, Is.True, "un nom nul reste nul");
            Assert.Throws<ArgumentException>(() => DossierPays.Registre(new DocumentDuMonde("{\"tick\":31,\"nombre\":0,\"maisons\":[]}")));
            Assert.Throws<ArgumentException>(() => DossierPays.Registre(new DocumentDuMonde(Maisons.Replace("\"nombre\":4", "\"nombre\":5"))));
            Assert.Throws<ArgumentException>(() => DossierPays.Registre(new DocumentDuMonde(Maisons.Replace("\"id\":\"seigneurie-1\"", "\"id\":\"grande-3\""))));
            Assert.Throws<ArgumentException>(() => DossierPays.Registre(new DocumentDuMonde(Maisons.Replace("\"id\":\"seigneurie-1\"", "\"id\":\"\""))));
        }

        // Un GameObject témoin avec sa toile et sa barre : le feuillet, son icône et ses lectures sont les vrais ; le registre et les noms sont servis par le test.
        GameObject racine; Transform toile, barre; DossierPays dossier; LecturePartie partie; int appelsRegistre; int appelsLieux;
        [SetUp] public void Ouvrir()
        {
            racine = new GameObject("Pays de contrôle"); toile = new GameObject("toile", typeof(RectTransform)).transform; barre = new GameObject("barre", typeof(RectTransform)).transform;
            toile.SetParent(racine.transform, false); barre.SetParent(racine.transform, false);
            partie = new LecturePartie(() => null, _ => null, () => null, _ => null);
            appelsRegistre = 0; appelsLieux = 0;
        }
        [TearDown] public void Fermer() => UnityEngine.Object.DestroyImmediate(racine);
        static void Poser(object cible, string nom, object valeur) => cible.GetType().GetProperty(nom).GetSetMethod(true).Invoke(cible, new[] { valeur });
        Button Icone => barre.GetComponentsInChildren<Button>(true).Single(b => b.name == DossierPays.ICONE);
        void Poser(Lecture<MondeAvecMaisonLu> monde, Lecture<TerresDuPays> terres)
        {
            Poser(partie, "Monde", monde); Poser(partie, "Terres", terres);
            if (dossier != null) return;
            var registre = new LectureDossier(_ => { appelsRegistre++; return Task.FromResult(new DocumentDuMonde(Maisons)); });
            var noms = new NomsDesTerres(c => { Interlocked.Increment(ref appelsLieux); return LectureLieu.De(new Lieu(c, 31, 1400, 32, 1, new Dictionary<string, double>(), 0, 0,
                lieux: NomsTemoin.Where(n => n.Key.Item1 == c).Select(n => new LieuPlace(n.Key.Item2, null, null, nom: n.Value)).ToArray())); });
            dossier = racine.AddComponent<DossierPays>(); dossier.Initialiser(toile, barre, () => partie.Monde, () => partie.Terres, registre, noms);
        }
        // Jusqu'à ce que les noms soient lus : au plus 100 appels, `maintenant` croissant.
        double Jusqu_aux_noms(double maintenant)
        {
            for (int i = 0; i < 100; i++)
            {
                dossier.Pas(maintenant);
                if (dossier.TexteAffiche != null && !dossier.TexteAffiche.Contains(NomsDesTerres.NomEnLecture)) return maintenant;
                Thread.Sleep(20); maintenant += 0.1;
            }
            Assert.Fail("noms non lus en 100 appels : " + dossier.TexteAffiche); return maintenant;
        }
        [Test] public void Le_feuillet_egale_le_pays_servi_au_meme_tick()
        {
            Poser(Monde(), Terres());
            Icone.onClick.Invoke();
            double t = Jusqu_aux_noms(0);
            Assert.That(dossier.TexteAffiche, Is.EqualTo(TexteTemoin));
            Assert.That(appelsRegistre, Is.EqualTo(1), "le registre est lu une fois à l'ouverture");
            dossier.Pas(t + 10); dossier.Pas(t + 20); Assert.That(appelsRegistre, Is.EqualTo(1), "puis plus jamais tant qu'il est complet");
            Poser(partie, "Terres", Terres(32)); dossier.Pas(t + 30); Assert.That(dossier.TexteAffiche, Is.EqualTo("Pays en attente du monde"));
            Poser(partie, "Terres", Terres()); dossier.Pas(t + 31); Assert.That(dossier.TexteAffiche, Is.EqualTo(TexteTemoin));
            Icone.onClick.Invoke(); dossier.Pas(t + 40); Icone.onClick.Invoke(); dossier.Pas(t + 41);
            Assert.That(appelsRegistre, Is.EqualTo(2), "fermé puis rouvert : le registre est relu une fois de plus");
            Icone.onClick.Invoke(); string garde = dossier.TexteAffiche; Poser(partie, "Terres", Terres(32)); dossier.Pas(t + 50);
            Assert.That(dossier.TexteAffiche, Is.EqualTo(garde), "fermé, Pas laisse le texte tel quel");
        }
    }
}
