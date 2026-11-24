using System;
using System.Collections.Generic;
using System.Linq;
using Forge.Pont;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

namespace Forge.Interface.Tests
{
    public sealed class CalquesCarteTests
    {
        [Test] public void LesPigmentsGardentLesFamillesPolitiquesSansCouleursVives()
        {
            var rouge = SocleInterface.Pigment(UnityEngine.Color.red);
            var bleu = SocleInterface.Pigment(UnityEngine.Color.blue);
            Assert.That(rouge.r, Is.GreaterThan(rouge.b));
            Assert.That(bleu.b, Is.GreaterThan(bleu.r));
            foreach (var pigment in new[] { rouge, bleu, SocleInterface.Pigment(UnityEngine.Color.green) })
            {
                UnityEngine.Color.RGBToHSV(pigment, out _, out float saturation, out float valeur);
                Assert.That(saturation, Is.LessThan(.45f));
                Assert.That(valeur, Is.InRange(.5f, .7f));
            }
        }
        // Le thème garde la teinte servie ; un pigment repeint d'un jeton échoue.
        [Test] public void LePigmentGardeLaTeinteServieDeChaqueMaison()
        {
            for (int i = 0; i < 24; i++)
                foreach (float saturation in new[] { 1f, .7f, .5f })
                {
                    var servie = UnityEngine.Color.HSVToRGB(i / 24f, saturation, .9f);
                    UnityEngine.Color.RGBToHSV(SocleInterface.Pigment(servie), out float teinte, out _, out _);
                    float ecart = Math.Abs(teinte - i / 24f);
                    Assert.That(Math.Min(ecart, 1 - ecart) * 360, Is.LessThan(15f), "teinte " + i * 15 + "°");
                }
        }
        static MondeLu Monde(params CelluleDuMonde[] cellules) => new MondeLu(8, new DateDuMonde(1400, 9), cellules.Length, cellules);
        [Test] public void La_legende_et_les_teintes_derivent_des_populations_recues()
        {
            var repartition = new RepartitionHabitants(Monde(new CelluleDuMonde(10, 0, -1, -1), new CelluleDuMonde(20, 90, -1, -1)));
            Assert.AreEqual(0, repartition.Minimum); Assert.AreEqual(90, repartition.Maximum);
            Assert.AreEqual(0, repartition.Position(10)); Assert.AreEqual(1, repartition.Position(20));
            StringAssert.Contains("jour 9 de 1400", repartition.Legende);
            StringAssert.Contains("90 habitants (foncé)", repartition.Legende);
            StringAssert.Contains("échelle logarithmique", repartition.Legende);
            Assert.Throws<ArgumentException>(() => repartition.Position(30));
        }
        [Test] public void Une_cellule_manquante_dupliquee_ou_negative_refuse_le_calque()
        {
            var cellule = new CelluleDuMonde(10, 3, -1, -1);
            Assert.Throws<ArgumentException>(() => new RepartitionHabitants(Monde()));
            Assert.Throws<ArgumentException>(() => new RepartitionHabitants(Monde(cellule, cellule)));
            Assert.Throws<ArgumentException>(() => new RepartitionHabitants(Monde(new CelluleDuMonde(10, -1, -1, -1))));
            Assert.Throws<ArgumentException>(() => new RepartitionHabitants(new MondeLu(0, new DateDuMonde(1400, 1), 2, new[] { cellule })));
            Assert.AreEqual(.5f, new RepartitionHabitants(Monde(cellule)).Position(10));
        }
        [Test] public void La_legende_des_habitants_dit_la_date_et_compte_en_habitants()
        {
            string legende = new RepartitionHabitants(Monde(new CelluleDuMonde(10, 1, -1, -1), new CelluleDuMonde(20, 5631, -1, -1))).Legende;
            Assert.AreEqual("5 631", TexteDuMonde.Nombre(5631));
            Assert.AreEqual("Habitants : 1 habitant (clair) → 5 631 habitants (foncé) · échelle logarithmique · jour 9 de 1400", legende);
            Assert.IsNull(TexteDuMonde.Interdit(legende), legende); Assert.IsNull(TexteDuMonde.SansUnite(legende), legende);
            Assert.Catch<ArgumentException>(() => new RepartitionHabitants(new MondeLu(8, new DateDuMonde(1400, 0), 1, new[] { new CelluleDuMonde(10, 1, -1, -1) })));
            LogAssert.Expect(LogType.Log, "TexteDuMonde : absence déclarée par le monde : Population absente du territoire 30");
            Assert.AreEqual("Mode Population indisponible : déclaré absent par le monde. Carte politique montrée.", CalquesCarte.Indisponible(ModeDeCarte.Population, "Population absente du territoire 30"));
            Assert.AreEqual("Mode Population indisponible : population non lue. Carte politique montrée.", CalquesCarte.Indisponible(ModeDeCarte.Population, "population non lue"));
            Assert.AreEqual("Pays indisponibles : pays en lecture. Couleurs des puissances du départ montrées.", CalquesCarte.Indisponible(ModeDeCarte.Politique, "pays en lecture"));
        }

        // Les données témoin : trois terres 10, 20, 30 aux pays Avalon, Brume et Cendre, tenues par les maisons m10, m20, m30.
        const string A = "pays-a", B = "pays-b", C = "pays-c";
        static readonly Color PA = new Color(.2f, .4f, .8f), PB = new Color(.7f, .5f, .2f), PC = new Color(.3f, .6f, .3f);
        static TerresDeLaCarte Terres(long jour = 6) => new TerresDeLaCarte(jour - 1, new DateDuMonde(1400, jour), new[] { new PaysDeLaCarte(A, "Avalon"), new PaysDeLaCarte(B, "Brume"), new PaysDeLaCarte(C, "Cendre") },
            new[] { new TerreLue(10, "m10", A), new TerreLue(20, "m20", B), new TerreLue(30, "m30", C) });
        static GuerresLues Guerres(GuerreLue[] guerres, params long[] sieges) => new GuerresLues(5, new DateDuMonde(1400, 6), guerres,
            sieges.Select((s, i) => new ArmeeLue(i, "m10", s, 0, 1200, 500, s, null, new long[0], new PointCarte(0, 0), new PointCarte[0])), new PriseLue[0], 0);
        static CelluleDeCarte Cellule(long id, string relief) => new CelluleDeCarte(id, new PolygoneDeCarte[0], null, null, new VilleDeCarte[0], relief);
        static CarteLue Carte(params string[] reliefs) => new CarteLue(reliefs.Length, reliefs.Select((r, i) => Cellule(10 * (i + 1), r)));
        static readonly (long cell, string pays, Color pigment)[] TROIS = { (10, A, PA), (20, B, PB), (30, C, PC) };
        static Color[] Peintes(LectureDuMode l) => TROIS.Select(t => l.Teinte(t.cell, t.pays, t.pigment, false)).ToArray();
        // La légende d'un mode tient en trois lignes sur la toile, aux deux échelles, et passe les juges du clerc.
        static void Tenir(string legende)
        {
            var toile = new GameObject("Toile témoin", typeof(Canvas));
            try
            {
                var calques = toile.AddComponent<CalquesCarte>(); calques.Initialiser(null, toile.transform, () => null, () => null);
                Assert.DoesNotThrow(() => calques.Legender(legende, "détail"), legende);
                Assert.IsNull(TexteDuMonde.Interdit(legende, A, B, C, "m10", "m20") ?? TexteDuMonde.SansUnite(legende), legende);
            }
            finally { UnityEngine.Object.DestroyImmediate(toile); }
        }

        // Chaque légende dit son unité et la date du jour lu ; le relief, qui ne change pas, le dit à la place d'une date.
        [Test] public void La_legende_de_chaque_mode_dit_son_unite_et_sa_date()
        {
            var monde = Monde(new CelluleDuMonde(10, 1, 0, 0), new CelluleDuMonde(20, 5631, 3, 3200), new CelluleDuMonde(30, 90, 12, 25));
            var guerres = Guerres(new[] { new GuerreLue(1, "m10", "m20", 2) }, 20);
            var attendues = new Dictionary<ModeDeCarte, string[]>
            {
                [ModeDeCarte.Politique] = new[] { "Pays au jour 6 de 1400" },
                [ModeDeCarte.Relief] = new[] { "Relief servi, qui ne change pas", "marais", "haute montagne" },
                [ModeDeCarte.Population] = new[] { "habitants", "jour 9 de 1400" },
                [ModeDeCarte.Vivres] = new[] { "Vivres au jour 9 de 1400", "faim : 1 jour (cuivre) → 12 jours (brun)", "or : du grain", CalquesCarte.FLECHES },
                [ModeDeCarte.Guerres] = new[] { "Guerres au jour 6 de 1400", "pays en guerre", "terre assiégée" }
            };
            Assert.That(attendues.Keys, Is.EquivalentTo((ModeDeCarte[])Enum.GetValues(typeof(ModeDeCarte))), "un mode sans légende jugée");
            foreach (var paire in attendues)
            {
                var lecture = new LectureDuMode(paire.Key, monde, Carte("marais", "plaine", "haute_montagne"), Terres(), guerres);
                string legende = lecture.Legende(false); Tenir(legende); Assert.That(legende, Does.EndWith(CalquesCarte.ROUGE), paire.Key.ToString());
                foreach (string attendu in paire.Value) Assert.That(legende, Does.Contain(attendu), paire.Key.ToString());
                Assert.IsNull(TexteDuMonde.Interdit(lecture.Detail, A, B, C) ?? TexteDuMonde.SansUnite(lecture.Detail), lecture.Detail);
            }
            // Au plus long : des milliers de jours de faim, des terres sans faim calculée ou sans relief servi, toujours en trois lignes.
            Tenir(new LectureDuMode(ModeDeCarte.Vivres, new MondeLu(364, new DateDuMonde(1400, 365), 3, new[] { new CelluleDuMonde(10, 1, 12345, 1e9), new CelluleDuMonde(20, 1, -1, -1), new CelluleDuMonde(30, 1, 0, 0) }), null, null, null).Legende(false));
            Tenir(new LectureDuMode(ModeDeCarte.Relief, null, Carte("marais", null, "glacier"), null, null).Legende(false));
            Tenir(new LectureDuMode(ModeDeCarte.Politique, null, null, Terres(365), null).Legende(true));
            // Contre-épreuve : une année écrite sans « jour N de » est un nombre sans unité.
            Assert.AreEqual("1400", TexteDuMonde.SansUnite("Pays de 1400" + CalquesCarte.ROUGE));
        }

        // Le relief peint la classe servie de chaque terre, quel que soit son pays : deux pigments, la même teinte.
        [Test] public void Le_relief_ne_teinte_aucune_terre_d_un_pays()
        {
            var lecture = new LectureDuMode(ModeDeCarte.Relief, null, Carte("plaine", "plaine", "montagne"), Terres(), null);
            Color[] peintes = Peintes(lecture); var relief = SocleInterface.TeintesDuRelief;
            Assert.That((peintes[0], peintes[1], peintes[2]), Is.EqualTo((relief[1].teinte, relief[1].teinte, relief[3].teinte)), "le relief ne suit pas la classe servie");
            Assert.That(TROIS.Select(t => t.pigment).Any(p => peintes.Contains(p)), Is.False, "une terre garde le pigment de son pays");
            Assert.That(new LectureDuMode(ModeDeCarte.Politique, null, null, Terres(), null).Teinte(20, B, PB, false), Is.EqualTo(PB), "contre-épreuve : la carte politique garde le pigment");
            // Les cinq classes servies ont cinq teintes qui se séparent à l'œil.
            for (int i = 0; i < relief.Count; i++) for (int j = i + 1; j < relief.Count; j++)
                Assert.That(CouleursDesPays.Ecart(relief[i].teinte, relief[j].teinte), Is.GreaterThan(8f), relief[i].classe + " et " + relief[j].classe);
            // Une terre sans relief servi, ou d'une classe inconnue, est comptée, en gris, et la légende le dit.
            var partiel = new ReliefDesTerres(Carte("colline", null, "glacier"));
            Assert.That((partiel.SansRelief, partiel.ClasseDe(10), partiel.ClasseDe(20), partiel.Teinte(30)), Is.EqualTo((2, "colline", (string)null, SocleInterface.Attenue)));
            Assert.That(partiel.Legende, Does.Contain("gris : non servi")); Assert.That(partiel.Detail, Does.Contain("En gris, 2 terres sans relief servi."));
            Assert.Throws<ArgumentException>(() => partiel.Teinte(40), "une terre que la carte ne sert pas");
        }

        // Seuls les pays qu'une guerre servie nomme gardent leur couleur ; une terre assiégée prend la sienne, autre que le rouge de la terre gardée.
        [Test] public void Les_guerres_ne_marquent_que_les_pays_que_les_guerres_servies_nomment()
        {
            var guerre = new[] { new GuerreLue(1, "m10", "m20", 2) };
            var lecture = new LectureDuMode(ModeDeCarte.Guerres, null, null, Terres(), Guerres(guerre));
            Assert.That(Peintes(lecture), Is.EqualTo(new[] { PA, PB, BelligerantsDesPays.EN_PAIX }), "Cendre, en paix, est marquée");
            Assert.That(lecture.Guerres.PaysEnGuerre, Is.EquivalentTo(new[] { A, B })); Assert.That(lecture.Detail, Does.Contain("\nAvalon contre Brume.").And.Contain("Aucune terre assiégée."));
            // Contre-épreuve : une guerre servie de plus, entre Cendre et Brume, marque Cendre.
            var deux = new LectureDuMode(ModeDeCarte.Guerres, null, null, Terres(), Guerres(guerre.Concat(new[] { new GuerreLue(2, "m30", "m20", 3) }).ToArray()));
            Assert.That(Peintes(deux), Is.EqualTo(new[] { PA, PB, PC }));
            // Une armée qui assiège la terre 20 la marque ; la terre gardée reste rouge.
            var siege = new LectureDuMode(ModeDeCarte.Guerres, null, null, Terres(), Guerres(guerre, 20));
            Assert.That(Peintes(siege), Is.EqualTo(new[] { PA, BelligerantsDesPays.ASSIEGEE, BelligerantsDesPays.EN_PAIX })); Assert.That(siege.Detail, Does.Contain("1 terre assiégée."));
            Assert.That(BelligerantsDesPays.ASSIEGEE, Is.Not.EqualTo(SocleInterface.Couleur("alerte"))); Assert.That(siege.Teinte(20, B, PB, true), Is.EqualTo(SocleInterface.Couleur("alerte")));
            // Sans guerre servie : tous en paix, et la légende le dit.
            var paix = new LectureDuMode(ModeDeCarte.Guerres, null, null, Terres(), Guerres(new GuerreLue[0]));
            Assert.That(Peintes(paix), Is.All.EqualTo(BelligerantsDesPays.EN_PAIX)); Assert.That(paix.Legende(false), Does.StartWith("Aucune guerre au jour 6 de 1400"));
        }

        // Une donnée qui manque lève l'exception qui la nomme : le mode le dit au lieu de peindre.
        [Test] public void Un_mode_dont_la_donnee_manque_le_dit()
        {
            string Raison(ModeDeCarte mode, MondeLu monde, CarteLue carte, TerresDeLaCarte terres, GuerresLues guerres, string absenceDesTerres = null, string absenceDesGuerres = null) =>
                Assert.Throws<ArgumentException>(() => new LectureDuMode(mode, monde, carte, terres, guerres, absenceDesTerres, absenceDesGuerres), mode.ToString()).Message;
            Assert.That(Raison(ModeDeCarte.Population, null, null, null, null), Is.EqualTo("population non lue"));
            Assert.That(Raison(ModeDeCarte.Vivres, null, null, null, null), Is.EqualTo("vivres non lus"));
            Assert.That(Raison(ModeDeCarte.Vivres, Monde(new CelluleDuMonde(10, 4, -1, -1), new CelluleDuMonde(20, 4, -1, -1)), null, null, null), Is.EqualTo("faim non calculée par le monde"));
            Assert.That(Raison(ModeDeCarte.Relief, null, null, null, null), Is.EqualTo("carte non lue"));
            Assert.That(Raison(ModeDeCarte.Relief, null, Carte(null, null), null, null), Is.EqualTo("relief non servi par la carte"));
            Assert.That(Raison(ModeDeCarte.Guerres, null, null, Terres(), null), Is.EqualTo("guerres en lecture"));
            Assert.That(Raison(ModeDeCarte.Guerres, null, null, Terres(), null, null, "guerres : délai dépassé"), Is.EqualTo("guerres : délai dépassé"));
            Assert.That(Raison(ModeDeCarte.Guerres, null, null, null, Guerres(new GuerreLue[0]), "terres : service coupé"), Is.EqualTo("terres : service coupé"));
            // Contre-épreuve : la carte politique se lit toujours, pays lus ou non, et dit quand ils ne le sont pas.
            Assert.That(new LectureDuMode(ModeDeCarte.Politique, null, null, null, null).Legende(false), Is.EqualTo(CalquesCarte.PAYS_NON_LUS + CalquesCarte.ROUGE));
            Assert.Throws<ArgumentException>(() => new LectureDuMode(ModeDeCarte.Population, Monde(new CelluleDuMonde(10, 4, 0, 0)), null, null, null).Valider(20), "une terre que le monde ne sert pas");
        }

        // -1 dit « non calculé » : jamais une terre nourrie, ni un manque de zéro.
        [Test] public void Moins_un_n_est_jamais_compte_comme_nourri()
        {
            var vivres = new VivresDesTerres(Monde(new CelluleDuMonde(10, 4, -1, -1), new CelluleDuMonde(20, 4, 0, 0), new CelluleDuMonde(30, 4, 5, 3200), new CelluleDuMonde(40, 4, 2, -1)));
            Assert.That((vivres.NonCalculees, vivres.Affamees, vivres.PlusLongueFaim, vivres.PlusGrosManqueKg), Is.EqualTo((1, 2, 5L, 3200d)));
            Assert.That(vivres.Teinte(10), Is.EqualTo(SocleInterface.Attenue)); Assert.That(vivres.Teinte(10), Is.Not.EqualTo(VivresDesTerres.GRAIN), "-1 peint comme une terre nourrie");
            Assert.That((vivres.Teinte(20), vivres.Teinte(30)), Is.EqualTo((VivresDesTerres.GRAIN, VivresDesTerres.PLUS_LONGUE_FAIM)));
            Assert.That(vivres.Teinte(40), Is.EqualTo(Color.Lerp(VivresDesTerres.PREMIERE_FAIM, VivresDesTerres.PLUS_LONGUE_FAIM, .25f)), "la faim ne suit pas ses jours servis");
            Assert.That(vivres.Legende, Does.Contain("faim : 1 jour (cuivre) → 5 jours (brun)").And.Contain("gris : non calculé"));
            Assert.That(vivres.Detail, Is.EqualTo("\n2 terres ont faim au jour 9 de 1400 ; la plus longue faim dure 5 jours ; le plus lourd manque de grain servi est de 3,20 t.\n1 terre sans faim calculée, en gris."));
            // Un manque de -1 n'est pas un manque mesuré : sans autre manque, aucun ne se dit.
            var sansManque = new VivresDesTerres(Monde(new CelluleDuMonde(10, 4, 0, -1), new CelluleDuMonde(20, 4, 0, 0)));
            Assert.That((sansManque.PlusGrosManqueKg, sansManque.Affamees, sansManque.NonCalculees), Is.EqualTo((0d, 0, 0))); Assert.That(sansManque.Detail, Is.EqualTo("\nAucune terre n'a faim au jour 9 de 1400."));
            Assert.That(sansManque.Legende, Does.Contain("or : du grain partout").And.Not.Contain("gris"));
            Assert.Throws<ArgumentException>(() => new VivresDesTerres(Monde(new CelluleDuMonde(10, 4, -2, 0))), "une faim de -2 jours");
            Assert.Throws<ArgumentException>(() => new VivresDesTerres(Monde(new CelluleDuMonde(10, 4, 0, -3))), "un manque de -3 kg");
        }

        // Chaque mode a sa couleur ; la terre gardée reste rouge dans tous ; une légende de quatre lignes est refusée.
        [Test] public void Chaque_mode_a_sa_couleur_et_la_terre_gardee_reste_rouge()
        {
            var monde = Monde(new CelluleDuMonde(10, 1, 0, 0), new CelluleDuMonde(20, 90, 2, 0), new CelluleDuMonde(30, 9000, 0, 0));
            var modes = (ModeDeCarte[])Enum.GetValues(typeof(ModeDeCarte)); Assert.That(modes, Has.Length.EqualTo(5));
            var lectures = modes.Select(m => new LectureDuMode(m, monde, Carte("marais", "plaine", "colline"), Terres(), Guerres(new GuerreLue[0]))).ToArray();
            var teintes = lectures.Select(l => l.Teinte(20, B, PB, false)).ToArray();
            for (int i = 0; i < teintes.Length; i++) for (int j = i + 1; j < teintes.Length; j++) Assert.That(teintes[i], Is.Not.EqualTo(teintes[j]), modes[i] + " et " + modes[j] + " peignent la même teinte");
            foreach (var l in lectures) Assert.That(l.Teinte(20, B, PB, true), Is.EqualTo(SocleInterface.Couleur("alerte")), l.Mode.ToString());
            foreach (var mode in modes) Assert.IsNull(TexteDuMonde.Interdit(CalquesCarte.DetailDuMode(mode)) ?? TexteDuMonde.SansUnite(CalquesCarte.DetailDuMode(mode)), mode.ToString());
            foreach (var mode in modes) { string phrase = CalquesCarte.PhraseDuMode(mode); Assert.That(phrase.StartsWith(mode + " : ") && phrase.Length > mode.ToString().Length + 20, Is.True, "la phrase du mode ne dit que son nom : " + phrase); }
            var toile = new GameObject("Toile témoin", typeof(Canvas));
            try
            {
                var calques = toile.AddComponent<CalquesCarte>(); calques.Initialiser(null, toile.transform, () => null, () => null);
                var texte = SocleInterface.Texte(toile.transform, "", 0, 0, 470); const string QUATRE = "Première ligne\nDeuxième ligne\nTroisième ligne\nQuatrième ligne";
                Assert.AreEqual(SocleInterface.Corps, texte.fontSize); Assert.AreEqual(4, CalquesCarte.Lignes(texte, QUATRE, 1f));
                Assert.Throws<ArgumentException>(() => calques.Legender(QUATRE, CalquesCarte.DetailDuMode(ModeDeCarte.Politique)));
            }
            finally { UnityEngine.Object.DestroyImmediate(toile); }
        }
    }
}
