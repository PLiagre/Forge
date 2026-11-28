using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Text.RegularExpressions;
using Forge.Pont;
using Forge.Pont.Tests;
using NUnit.Framework;
using UnityEngine;

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

        // Les lieux servis témoins : (cell, [(habitants, surface en km², réserve en jours ou null)]), le rang étant la place dans la liste.
        static LieuxLus Lieux(params (long cell, (long habitants, double surface, double? reserve)[] lieux)[] cellules) => new LieuxLus(8, new DateDuMonde(1400, 9), cellules.Length,
            cellules.Select(c => new CelluleServie(c.cell, c.lieux.Select((l, rang) => new LieuServi(rang, l.habitants, l.surface, l.reserve)))));
        static (long, (long, double, double?)[]) Une(long cell, params (long, double, double?)[] lieux) => (cell, lieux);

        // Les données témoin : trois terres 10, 20, 30 aux pays Avalon, Brume et Cendre, tenues par les maisons m10, m20, m30.
        const string A = "pays-a", B = "pays-b", C = "pays-c";
        static readonly Color PA = new Color(.2f, .4f, .8f), PB = new Color(.7f, .5f, .2f), PC = new Color(.3f, .6f, .3f);
        static TerresDeLaCarte Terres(long jour = 6) => new TerresDeLaCarte(jour - 1, new DateDuMonde(1400, jour), new[] { new PaysDeLaCarte(A, "Avalon"), new PaysDeLaCarte(B, "Brume"), new PaysDeLaCarte(C, "Cendre") },
            new[] { new TerreLue(10, "m10", A), new TerreLue(20, "m20", B), new TerreLue(30, "m30", C) });
        static GuerresLues Guerres(GuerreLue[] guerres, params long[] sieges) => new GuerresLues(5, new DateDuMonde(1400, 6), guerres,
            sieges.Select((s, i) => new ArmeeLue(i, "m10", s, 0, 1200, 500, s, null, new long[0], new PointCarte(0, 0), new PointCarte[0])), new PriseLue[0], 0);
        static CelluleDeCarte Cellule(long id, string relief, double aire = 1000) => new CelluleDeCarte(id, new PolygoneDeCarte[0], null, null, new VilleDeCarte[0], relief, aire);
        static CarteLue Carte(params string[] reliefs) => new CarteLue(reliefs.Length, reliefs.Select((r, i) => Cellule(10 * (i + 1), r)));
        // Trois terres d'un lieu chacune, le lieu de la 20 à 90 hab./km² et 2 jours de réserve.
        static LieuxLus TroisLieux() => Lieux(Une(10, (1, 1, 0)), Une(20, (90, 1, 2)), Une(30, (9000, 1, 30)));
        static readonly (long cell, string pays, Color pigment)[] TROIS = { (10, A, PA), (20, B, PB), (30, C, PC) };
        static Color[] Peintes(LectureDuMode l) => TROIS.Select(t => l.Teinte(t.cell, 0, t.pays, t.pigment)).ToArray();
        static LectureDuMode Mode(ModeDeCarte mode, LieuxLus lieux = null, IEnumerable<(long, long)> alertes = null) =>
            new LectureDuMode(mode, lieux ?? TroisLieux(), Carte("marais", "plaine", "haute_montagne"), Terres(), Guerres(new[] { new GuerreLue(1, "m10", "m20", 2) }, 20), alertes);

        // Une échelle tient sur la toile, aux deux échelles : chacune de ses étiquettes sur une ligne (trois, ou une par borne entre deux
        // paliers), sans mot interdit ni nombre sans unité, l'unité d'une échelle à paliers valant pour toutes ses bornes ; ce sont des mots
        // ou des chiffres, jamais une phrase, et jamais « rouge ».
        static void Tenir(EchelleDuMode echelle)
        {
            Assert.That(echelle, Is.Not.Null, "pas d'échelle"); Assert.That(echelle.Etiquettes.Count, Is.EqualTo(echelle.Paliers ? echelle.Teintes.Count - 1 : 3));
            if (echelle.Paliers) Assert.That(echelle.Etiquettes.Last(), Does.EndWith(" " + echelle.Unite), "l'unité n'est pas dite après la dernière borne");
            Assert.That(echelle.Etiquettes.Where(e => e.IndexOf("rouge", StringComparison.OrdinalIgnoreCase) >= 0), Is.Empty, "une étiquette dit « rouge »");
            var toile = new GameObject("Toile témoin", typeof(Canvas));
            try
            {
                var calques = toile.AddComponent<CalquesCarte>(); calques.Initialiser(null, toile.transform, () => null, () => null);
                Assert.DoesNotThrow(() => calques.Legender(echelle, "détail"), echelle.Texte);
                Assert.That(calques.EchelleMontree, Is.SameAs(echelle)); Assert.That(calques.Echelle.gameObject.activeSelf && !calques.Legende.enabled, Is.True, "l'échelle n'est pas dessinée, ou le texte se montre à sa place");
                Assert.That(calques.EtiquettesDeLEchelle.Select(t => t.text), Is.EqualTo(echelle.Etiquettes), "les étiquettes dessinées ne sont pas celles de l'échelle");
                foreach (string etiquette in echelle.Etiquettes)
                {
                    string lue = echelle.Paliers && !etiquette.EndsWith(" " + echelle.Unite) ? etiquette + " " + echelle.Unite : etiquette;
                    Assert.IsNull(TexteDuMonde.Interdit(etiquette, A, B, C, "m10", "m20") ?? TexteDuMonde.SansUnite(lue), etiquette);
                    Assert.That(etiquette.Split(' ', ' ', ' ').Length <= 5 && !etiquette.EndsWith("."), Is.True, "une phrase dans l'échelle : « " + etiquette + " »");
                }
            }
            finally { UnityEngine.Object.DestroyImmediate(toile); }
        }

        // La densité est le rapport de deux nombres servis, lieu par lieu : à habitants égaux, le lieu le plus petit est le plus dense, donc
        // le plus foncé, et le bourg d'une terre est plus foncé que ses campagnes quand il est plus dense qu'elles.
        [Test] public void La_densite_se_lit_lieu_par_lieu_et_le_bourg_dense_est_plus_fonce_que_ses_campagnes()
        {
            var lieux = Lieux(Une(10, (12000, 40, 0), (3000, 1000, 0), (2500, 1000, 0)), Une(20, (120000, 7400, 0)), Une(30, (120000, 29000, 0)));
            var lecture = Mode(ModeDeCarte.Population, lieux);
            Assert.That(lecture.Population.DensiteDe(10, 0), Is.EqualTo(12000d / 40)); Assert.That(lecture.Population.DensiteDe(10, 2), Is.EqualTo(2.5));
            float Clarte(long cell, long rang) => lecture.Teinte(cell, rang, null, Color.white).grayscale;
            Assert.That(Clarte(10, 0), Is.LessThan(Clarte(10, 1)), "le bourg dense n'est pas plus foncé que ses campagnes");
            Assert.That(Clarte(10, 1), Is.LessThan(Clarte(10, 2)).Or.EqualTo(Clarte(10, 2)), "une campagne plus dense est plus claire");
            Assert.That(Clarte(20, 0), Is.LessThan(Clarte(30, 0)), "à habitants égaux, la terre de 7 400 km² n'est pas plus foncée que celle de 29 000 km²");
            // Contre-épreuve : à surfaces égales, les mêmes habitants donnent la même teinte.
            var egaux = Mode(ModeDeCarte.Population, Lieux(Une(10, (500, 100, 0), (500, 100, 0)), Une(20, (5, 100, 0)), Une(30, (50000, 100, 0))));
            Assert.That(egaux.Teinte(10, 0, null, Color.white), Is.EqualTo(egaux.Teinte(10, 1, null, Color.white)));
            Assert.Throws<ArgumentException>(() => lecture.Population.Position(10, 3), "un lieu que le service ne sert pas");
            Tenir(lecture.Echelle); Assert.That(lecture.Echelle.Etiquettes.Last(), Does.EndWith(" hab./km²"), lecture.Legende);
        }
        // Les paliers de densité sont ceux d'un atlas, fixes : les mêmes bornes et la même teinte pour une même densité, quels que soient les
        // lieux servis. Un lieu de ville de 275 000 habitants est plus foncé qu'une campagne, même quand presque tous les lieux servis sont
        // vides (une échelle bornée au 95e centile les peignait de la même teinte).
        [Test] public void Les_paliers_de_densite_sont_fixes_et_la_ville_est_plus_foncee_que_la_campagne()
        {
            var vides = Enumerable.Range(1, 40).Select(k => Une(k, (k % 8 + 1, 1, 0))).ToArray();
            var r = new RepartitionHabitants(Lieux(vides.Concat(new[] { Une(100, (30, 1, 0)), Une(200, (275000, 30, 0)) }).ToArray()));
            var denses = new RepartitionHabitants(Lieux(Une(1, (5000, 1, 0)), Une(100, (30, 1, 0)), Une(200, (9000, 1, 0)), Une(300, (12, 1, 0))));
            Assert.That(r.Teinte(200, 0).grayscale, Is.LessThan(r.Teinte(100, 0).grayscale), "la ville de 275 000 habitants n'est pas plus foncée qu'une campagne de 30 hab./km²");
            Assert.That(r.Teinte(100, 0), Is.EqualTo(denses.Teinte(100, 0)), "la même densité change de teinte selon les autres lieux servis");
            Assert.That(r.Echelle.Etiquettes, Is.EqualTo(denses.Echelle.Etiquettes)); Assert.That(r.Echelle.Teintes, Is.EqualTo(denses.Echelle.Teintes));
            Assert.That(r.Echelle.Etiquettes, Is.EqualTo(new[] { "2", "5", "10", "20", "40", "80 hab./km²" })); Assert.That(r.Echelle.Paliers && r.Echelle.Teintes.Count == 7, Is.True);
            // Les bornes : un palier commence à sa borne.
            var bords = new RepartitionHabitants(Lieux(Une(1, (19, 10, 0)), Une(2, (2, 1, 0)), Une(3, (799, 10, 0)), Une(4, (80, 1, 0))));
            Assert.That((bords.Palier(1, 0), bords.Palier(2, 0), bords.Palier(3, 0), bords.Palier(4, 0)), Is.EqualTo((0, 1, 5, 6)));
            Assert.That((bords.Teinte(1, 0), bords.Teinte(4, 0)), Is.EqualTo((RepartitionHabitants.CLAIRE, RepartitionHabitants.FONCEE)));
            Tenir(r.Echelle);
            Assert.That((RepartitionHabitants.Densite(0.04), RepartitionHabitants.Densite(3.26), RepartitionHabitants.Densite(1234.5)), Is.EqualTo(("0 hab./km²", "3,3 hab./km²", TexteDuMonde.Nombre(1235) + " hab./km²")));
            Assert.Throws<ArgumentException>(() => new RepartitionHabitants(Lieux()), "aucun lieu servi");
        }
        // La réserve de chaque lieu se lit par paliers fixes de mois de grain, du vide (ou d'une dette) à un an et plus, quels que soient les
        // autres lieux servis ; un lieu sans habitants est gris, jamais comme un lieu nourri.
        [Test] public void Les_vivres_vont_du_vide_au_plein_et_un_lieu_sans_habitants_est_gris()
        {
            var cellules = new[] { Une(1, (10, 1, -4), (0, 1, null)), Une(2, (10, 1, 0)), Une(3, (10, 1, 10)), Une(4, (10, 1, 40)), Une(5, (10, 1, 100)), Une(6, (10, 1, 200)), Une(7, (10, 1, 400)), Une(8, (10, 1, 5000)) };
            var v = new VivresDesLieux(Lieux(cellules));
            Assert.That((v.Vides, v.SansHabitants), Is.EqualTo((2, 1)));
            Assert.That(v.Teinte(1, 1), Is.EqualTo(SocleInterface.Attenue)); Assert.That(v.JoursDe(1, 1), Is.Null, "un lieu sans habitants a une réserve");
            Assert.That(new[] { 1, 2, 3, 4, 5, 6, 7, 8 }.Select(c => v.Palier(c, 0)), Is.EqualTo(new[] { 0, 0, 1, 2, 3, 4, 5, 5 }), "les paliers ne suivent pas les mois de grain");
            Assert.That((v.Teinte(1, 0), v.Teinte(7, 0), v.Teinte(8, 0)), Is.EqualTo((VivresDesLieux.VIDE, VivresDesLieux.PLEIN, VivresDesLieux.PLEIN)), "la dette n'est pas vide, ou un an n'est pas plein");
            Assert.That(v.Teinte(1, 1), Is.Not.EqualTo(v.Teinte(1, 0)).And.Not.EqualTo(VivresDesLieux.PLEIN), "un lieu sans habitants peint comme vide ou plein");
            // Les mêmes jours gardent leur teinte quand les autres lieux changent.
            Assert.That(new VivresDesLieux(Lieux(Une(4, (10, 1, 40)), Une(9, (10, 1, 9000)))).Teinte(4, 0), Is.EqualTo(v.Teinte(4, 0)), "une même réserve change de teinte selon les autres lieux servis");
            Assert.That(v.Echelle.Etiquettes, Is.EqualTo(new[] { "0", "1", "3", "6", "12 mois" })); Assert.That(v.Echelle.Paliers && v.Echelle.Teintes.Count == 6, Is.True); Tenir(v.Echelle);
            Assert.That(v.Detail, Does.Contain("2 lieux habités sont vides").And.Contain("1 lieu sans habitants, en gris"));
            Assert.Throws<ArgumentException>(() => new VivresDesLieux(Lieux(Une(1, (0, 1, null)))), "aucun lieu habité : rien à échelonner");
        }

        // Chaque mode a son échelle et ses étiquettes ; la règle et la date sont dans l'infobulle.
        [Test] public void Chaque_legende_est_une_echelle_a_trois_etiquettes_et_la_date_est_dans_l_infobulle()
        {
            var attendues = new Dictionary<ModeDeCarte, string[]>
            {
                [ModeDeCarte.Politique] = new[] { "pays", CalquesCarte.ALERTE, CalquesCarte.TERRE_OUVERTE },
                [ModeDeCarte.Relief] = new[] { "marais", "colline", "haute montagne" },
                [ModeDeCarte.Population] = new[] { "2", "5", "10", "20", "40", "80 hab./km²" },
                [ModeDeCarte.Vivres] = new[] { "0", "1", "3", "6", "12 mois" },
                [ModeDeCarte.Guerres] = new[] { "en guerre", "en paix", "assiégée" }
            };
            Assert.That(attendues.Keys, Is.EquivalentTo((ModeDeCarte[])Enum.GetValues(typeof(ModeDeCarte))), "un mode sans légende jugée");
            foreach (var paire in attendues)
            {
                var lecture = Mode(paire.Key); Tenir(lecture.Echelle);
                Assert.That(lecture.Echelle.Etiquettes, Is.EqualTo(paire.Value), paire.Key.ToString());
                // Hors du dessin, chaque borne des paliers porte son unité : la légende lue ne montre aucun nombre nu.
                string unite = lecture.Echelle.Paliers ? " " + lecture.Echelle.Unite : "";
                Assert.That(lecture.Legende, Is.EqualTo(string.Join(" · ", paire.Value.Select(e => unite.Length > 0 && !e.EndsWith(unite) ? e + unite : e)))); Assert.That(TexteDuMonde.SansUnite(lecture.Legende), Is.Null, lecture.Legende);
                Assert.That(lecture.Detail, Does.Contain("de 1400").Or.Contain("ne change pas"), paire.Key + " : l'infobulle ne date pas le mode");
                Assert.IsNull(TexteDuMonde.Interdit(lecture.Detail, A, B, C) ?? TexteDuMonde.SansUnite(lecture.Detail), lecture.Detail);
            }
            Assert.That(Mode(ModeDeCarte.Relief).Echelle.Degrade, Is.True, "une grandeur continue sans dégradé");
            Assert.That(Mode(ModeDeCarte.Population).Echelle.Paliers && Mode(ModeDeCarte.Vivres).Echelle.Paliers, Is.True, "la densité ou les vivres sans paliers fixes");
            Assert.That(Mode(ModeDeCarte.Politique).Echelle.Degrade || Mode(ModeDeCarte.Guerres).Echelle.Degrade, Is.False, "des catégories en dégradé");
        }

        // Aucune légende ne dit « rouge », ni ses étiquettes, ni son infobulle, ni la phrase de son bouton, pays et alertes lus ou non : sur la
        // carte politique, un rouge à côté de pays peints en brique dirait deux choses. Un lieu du joueur en alerte garde le pigment de son
        // pays ; l'alerte est une marque, que la légende dit en mots. Aucun mode ne peint quoi que ce soit au rouge de l'alerte.
        [Test] public void Aucune_legende_ne_dit_rouge_et_un_lieu_en_alerte_garde_le_pigment_de_son_pays()
        {
            var alertes = new[] { (20L, 0L) };
            foreach (var lecture in new[] { Mode(ModeDeCarte.Politique), Mode(ModeDeCarte.Politique, alertes: alertes), new LectureDuMode(ModeDeCarte.Politique, null, null, null, null), new LectureDuMode(ModeDeCarte.Politique, null, null, null, null, alertes) })
            {
                Assert.That(Regex.IsMatch(lecture.Legende + "\n" + lecture.Detail, "rouge", RegexOptions.IgnoreCase), Is.False, lecture.Legende + "\n" + lecture.Detail); Tenir(lecture.Echelle);
                Assert.That(lecture.Detail, Does.Contain(LieuxDeCarte.ENTETE).And.Contain("cernée d'un trait d'encre"));
                Assert.That(lecture.Echelle.Etiquettes[1], Is.EqualTo(CalquesCarte.ALERTE)); Assert.That(lecture.Echelle.Teintes[1], Is.EqualTo(SocleInterface.Couleur("encre")), "la pastille de l'alerte n'est pas l'encre de sa marque");
            }
            foreach (ModeDeCarte mode in Enum.GetValues(typeof(ModeDeCarte)))
            {
                var lecture = Mode(mode, alertes: alertes);
                Assert.That(Regex.IsMatch((lecture.Legende ?? "") + "\n" + lecture.Detail + "\n" + CalquesCarte.PhraseDuMode(mode) + "\n" + CalquesCarte.DetailDuMode(mode), "rouge", RegexOptions.IgnoreCase), Is.False, mode + " dit « rouge »");
                Assert.That(Peintes(lecture), Has.None.EqualTo(SocleInterface.Couleur("alerte")), mode + " peint en rouge");
            }
            var politique = Mode(ModeDeCarte.Politique, alertes: alertes);
            Assert.That(politique.EnAlerte(20, 0), Is.True, "échantillon vide : le lieu n'est pas en alerte");
            Assert.That(Peintes(politique), Is.EqualTo(new[] { PA, PB, PC }), "le lieu en alerte ne garde pas le pigment de son pays");
            Assert.That(Peintes(Mode(ModeDeCarte.Politique)), Is.EqualTo(Peintes(politique)), "l'alerte change une teinte");
            Assert.That(BelligerantsDesPays.ASSIEGEE, Is.Not.EqualTo(SocleInterface.Couleur("alerte")));
        }

        // Le relief peint la classe servie de chaque terre sous un éclat, quel que soit son pays ; le terrain la dessine par l'altitude.
        [Test] public void Le_relief_ne_teinte_aucune_terre_d_un_pays()
        {
            var lecture = new LectureDuMode(ModeDeCarte.Relief, null, Carte("plaine", "plaine", "montagne"), Terres(), null);
            Color[] peintes = Peintes(lecture); var relief = SocleInterface.TeintesDuRelief;
            Assert.That((peintes[0], peintes[1], peintes[2]), Is.EqualTo((relief[1].teinte, relief[1].teinte, relief[3].teinte)), "le relief ne suit pas la classe servie");
            Assert.That(TROIS.Select(t => t.pigment).Any(p => peintes.Contains(p)), Is.False, "une terre garde le pigment de son pays");
            Assert.That(ReliefDesTerres.Paliers, Has.Length.EqualTo(TerrainDeCarte.PALIERS.Count), "une teinte d'altitude par palier du terrain");
            for (int i = 0; i < relief.Count; i++) Assert.That(relief[i].classe, Is.EqualTo(TerrainDeCarte.PALIERS[i].classe), "les paliers du terrain et les teintes du socle ne vont pas dans le même ordre");
            for (int i = 0; i < relief.Count; i++) for (int j = i + 1; j < relief.Count; j++)
                Assert.That(CouleursDesPays.Ecart(relief[i].teinte, relief[j].teinte), Is.GreaterThan(8f), relief[i].classe + " et " + relief[j].classe);
            var partiel = new ReliefDesTerres(Carte("colline", null, "glacier"));
            Assert.That((partiel.SansRelief, partiel.ClasseDe(10), partiel.ClasseDe(20), partiel.Teinte(30)), Is.EqualTo((2, "colline", (string)null, SocleInterface.Attenue)));
            Assert.That(partiel.Detail, Does.Contain("2 terres sans relief servi se dessinent en plaine."));
            Assert.Throws<ArgumentException>(() => partiel.Teinte(40), "une terre que la carte ne sert pas");
        }

        // Seuls les pays qu'une guerre servie nomme gardent leur couleur ; une terre assiégée prend la sienne. Sans guerre ni armée, la
        // légende dit qu'aucune armée n'est en campagne.
        [Test] public void Les_guerres_ne_marquent_que_les_pays_que_les_guerres_servies_nomment()
        {
            var guerre = new[] { new GuerreLue(1, "m10", "m20", 2) };
            var lecture = new LectureDuMode(ModeDeCarte.Guerres, null, null, Terres(), Guerres(guerre));
            Assert.That(Peintes(lecture), Is.EqualTo(new[] { PA, PB, BelligerantsDesPays.EN_PAIX }), "Cendre, en paix, est marquée");
            Assert.That(lecture.Guerres.PaysEnGuerre, Is.EquivalentTo(new[] { A, B })); Assert.That(lecture.Detail, Does.Contain("Guerres au jour 6 de 1400.").And.Contain("\nAvalon contre Brume.").And.Contain("Aucune terre assiégée."));
            var deux = new LectureDuMode(ModeDeCarte.Guerres, null, null, Terres(), Guerres(guerre.Concat(new[] { new GuerreLue(2, "m30", "m20", 3) }).ToArray()));
            Assert.That(Peintes(deux), Is.EqualTo(new[] { PA, PB, PC }));
            var siege = new LectureDuMode(ModeDeCarte.Guerres, null, null, Terres(), Guerres(guerre, 20));
            Assert.That(Peintes(siege), Is.EqualTo(new[] { PA, BelligerantsDesPays.ASSIEGEE, BelligerantsDesPays.EN_PAIX })); Assert.That(siege.Detail, Does.Contain("1 terre assiégée."));
            var paix = new LectureDuMode(ModeDeCarte.Guerres, null, null, Terres(), Guerres(new GuerreLue[0]));
            Assert.That(Peintes(paix), Is.All.EqualTo(BelligerantsDesPays.EN_PAIX)); Assert.That((paix.Echelle, paix.Legende), Is.EqualTo(((EchelleDuMode)null, "Aucune armée en campagne")));
            Assert.That(paix.Detail, Does.Contain("Aucune guerre ni armée servie au jour 6 de 1400."));
            // Contre-épreuve : une armée en campagne sans guerre servie rend l'échelle.
            Assert.That(new LectureDuMode(ModeDeCarte.Guerres, null, null, Terres(), Guerres(new GuerreLue[0], 30)).Echelle, Is.Not.Null);
        }

        // Une donnée qui manque lève l'exception qui la nomme : le mode le dit au lieu de peindre.
        [Test] public void Un_mode_dont_la_donnee_manque_le_dit()
        {
            string Raison(ModeDeCarte mode, LieuxLus lieux, CarteLue carte, TerresDeLaCarte terres, GuerresLues guerres, string absenceDesLieux = null, string absenceDesTerres = null, string absenceDesGuerres = null) =>
                Assert.Throws<ArgumentException>(() => new LectureDuMode(mode, lieux, carte, terres, guerres, null, absenceDesLieux, absenceDesTerres, absenceDesGuerres), mode.ToString()).Message;
            Assert.That(Raison(ModeDeCarte.Population, null, null, null, null), Is.EqualTo("lieux en lecture"));
            Assert.That(Raison(ModeDeCarte.Vivres, null, null, null, null, "lieux : service coupé"), Is.EqualTo("lieux : service coupé"));
            Assert.That(Raison(ModeDeCarte.Vivres, Lieux(Une(10, (0, 1, null))), null, null, null), Is.EqualTo("aucun lieu habité servi"));
            Assert.That(Raison(ModeDeCarte.Relief, null, null, null, null), Is.EqualTo("carte non lue"));
            Assert.That(Raison(ModeDeCarte.Relief, null, Carte(null, null), null, null), Is.EqualTo("relief non servi par la carte"));
            Assert.That(Raison(ModeDeCarte.Guerres, null, null, Terres(), null), Is.EqualTo("guerres en lecture"));
            Assert.That(Raison(ModeDeCarte.Guerres, null, null, Terres(), null, null, null, "guerres : délai dépassé"), Is.EqualTo("guerres : délai dépassé"));
            Assert.That(CalquesCarte.Indisponible(ModeDeCarte.Population, "lieux en lecture"), Is.EqualTo("Mode Population indisponible : lieux en lecture. Carte politique montrée."));
            // Un lieu que le terrain dessine et que le service ne sert pas : le mode le dit.
            Assert.Throws<ArgumentException>(() => Mode(ModeDeCarte.Population).Valider(40, 0)); Assert.Throws<ArgumentException>(() => Mode(ModeDeCarte.Vivres).Valider(10, 1));
            // Contre-épreuve : la carte politique se lit toujours, pays lus ou non, et le dit dans l'infobulle quand ils ne le sont pas.
            var sansPays = new LectureDuMode(ModeDeCarte.Politique, null, null, null, null); Assert.That(sansPays.Detail, Does.StartWith(CalquesCarte.PAYS_NON_LUS));
            Assert.That(sansPays.Echelle.Etiquettes[0], Is.EqualTo("puissance"));
        }

        // Une légende de quatre lignes est refusée ; une étiquette d'échelle de deux lignes aussi.
        [Test] public void Une_legende_trop_longue_est_refusee()
        {
            var toile = new GameObject("Toile témoin", typeof(Canvas));
            try
            {
                var calques = toile.AddComponent<CalquesCarte>(); calques.Initialiser(null, toile.transform, () => null, () => null);
                const string QUATRE = "Première ligne\nDeuxième ligne\nTroisième ligne\nQuatrième ligne";
                Assert.Throws<ArgumentException>(() => calques.Legender(QUATRE, CalquesCarte.DetailDuMode(ModeDeCarte.Politique)));
                Assert.Throws<ArgumentException>(() => calques.Legender(new EchelleDuMode(true, new[] { Color.white, Color.black }, "a", "Une étiquette beaucoup trop longue pour tenir sur une seule ligne de la légende", "c"), "détail"));
                // Deux étiquettes qui tiennent chacune sur une ligne mais empiètent sur leur voisine : sous des pastilles, chacune dans son tiers.
                var pastilles = new[] { Color.white, Color.red, Color.black };
                Assert.Throws<ArgumentException>(() => calques.Legender(new EchelleDuMode(false, pastilles, "pays", "flèche : plus de départs qu'il n'en arrive", "trait : terre ouverte"), "détail"), "deux étiquettes qui se chevauchent");
                Assert.DoesNotThrow(() => calques.Legender(new EchelleDuMode(false, pastilles, "pays", CalquesCarte.ALERTE, CalquesCarte.TERRE_OUVERTE), "détail"), "contre-épreuve : l'échelle politique tient");
                // Sous des paliers, une borne trop large pour l'écart entre deux limites empiète sur sa voisine ; les paliers des modes tiennent.
                var sept = EchelleDuMode.Pas(Color.white, Color.black, 7);
                Assert.Throws<ArgumentException>(() => calques.Legender(EchelleDuMode.EnPaliers(sept, new[] { "2", "5 000 000", "10 000 000", "20", "40", "80" }, "hab./km²"), "détail"), "deux bornes qui se chevauchent");
                Assert.DoesNotThrow(() => calques.Legender(EchelleDuMode.EnPaliers(sept, new[] { "2", "5", "10", "20", "40", "80" }, "hab./km²"), "détail"), "contre-épreuve : les paliers de la densité tiennent");
                Assert.That(calques.EtiquettesDeLEchelle.Count, Is.EqualTo(6)); Assert.That(calques.EtiquettesDeLEchelle.All(t => t.gameObject.activeSelf), Is.True);
                Assert.That(calques.EtiquettesDeLEchelle.Select(t => t.rectTransform.anchoredPosition.x + t.rectTransform.sizeDelta.x / 2f).Zip(Enumerable.Range(1, 6), (x, k) => Mathf.Abs(x - (8 + k * (CalquesCarte.LARGEUR_DE_LA_LEGENDE - 16) / 7f))).Max(), Is.LessThan(1f), "une borne n'est pas sur la limite de ses deux pastilles");
                calques.Legender(new EchelleDuMode(false, pastilles, "pays", CalquesCarte.ALERTE, CalquesCarte.TERRE_OUVERTE), "détail"); Assert.That(calques.EtiquettesDeLEchelle.Count, Is.EqualTo(3), "les bornes d'avant restent montrées");
                Assert.DoesNotThrow(() => calques.Legender("Aucune armée en campagne", "détail")); Assert.That(calques.Legende.enabled && !calques.Echelle.gameObject.activeSelf, Is.True, "un message sans échelle ne se montre pas en texte");
                foreach (ModeDeCarte mode in Enum.GetValues(typeof(ModeDeCarte))) { string phrase = CalquesCarte.PhraseDuMode(mode); Assert.That(phrase.StartsWith(mode + " : ") && phrase.Length > mode.ToString().Length + 20, Is.True, phrase); }
            }
            finally { UnityEngine.Object.DestroyImmediate(toile); }
        }

        // Sur l'Europe figée (sa carte, ses terres, ses lieux servis), en Population et en Vivres, aucune terre ni aucun lieu n'a la teinte de
        // son pays, et le liseré est éteint ; la terre gardée n'est rouge dans aucun mode, cernée à l'encre.
        [Test] public void Sur_l_Europe_figee_aucun_mode_ne_garde_la_teinte_des_pays_ni_le_rouge_de_la_terre_gardee()
        {
            using (var europe = new EuropeDeCarte())
            {
                var carte = europe.Carte; var calques = europe.Calques; var guerre = europe.Guerre; calques.LecteurDesLieux = () => Lecture<LieuxLus>.De(EuropeDeTest.LieuxEurope);
                long gardee = guerre.Terres.Terres.First(t => t.Pays != null).CellId; Assert.That(carte.Marquer(gardee, SocleInterface.Couleur("alerte")), Is.True);
                var matiere = europe.Racine.transform.Find(CarteDessinee.TERRAIN).GetComponent<MeshRenderer>().sharedMaterial;
                foreach (ModeDeCarte mode in Enum.GetValues(typeof(ModeDeCarte)))
                {
                    Choisir(europe, mode);
                    Assert.That(calques.Legende.text, Does.Not.Contain("indisponible"), mode + " : " + calques.Legende.text);
                    Assert.That((Color32)carte.TeinteDe(gardee).Value, Is.Not.EqualTo((Color32)SocleInterface.Couleur("alerte")), mode + " : la terre gardée est rouge");
                    Assert.That((Color32)matiere.GetColor("_CouleurDeLaMarque"), Is.EqualTo((Color32)SocleInterface.Couleur("encre")), mode + " : la terre gardée n'est pas cernée à l'encre");
                    Assert.That(carte.LiseresMontres, Is.EqualTo(mode == ModeDeCarte.Politique), mode + " : le liseré");
                    Assert.That(carte.ParAltitude, Is.EqualTo(mode == ModeDeCarte.Relief), mode + " : la teinte d'altitude");
                    if (mode != ModeDeCarte.Population && mode != ModeDeCarte.Vivres) continue;
                    int jugees = 0, auPays = 0;
                    foreach (var terre in guerre.Terres.Terres.Where(t => t.Pays != null))
                    {
                        Color32 duPays = guerre.CouleurDuPays(terre.Pays); jugees++;
                        for (long rang = 0; carte.TeinteDuLieu(terre.CellId, rang) is Color teinte; rang++) if (((Color32)teinte).Equals(duPays)) auPays++;
                    }
                    Assert.That(jugees, Is.GreaterThan(400), "échantillon vide"); Assert.That(auPays, Is.Zero, mode + " : " + auPays + " lieux gardent la teinte de leur pays");
                }
            }
        }

        // Contre-épreuve à l'image : la Savoie, petite et cernée de voisins, prend tout entière le liseré de son pays, que la teinte d'un mode
        // ne couvre pas. Son liseré passé en couleur franche se voit en Population tant qu'il est allumé, et plus du tout une fois éteint.
        [Test] public void Le_liseré_de_la_Savoie_couvre_le_mode_tant_qu_il_est_allume()
        {
            using (var europe = new EuropeDeCarte())
            {
                var carte = europe.Carte; var guerre = europe.Guerre; europe.Calques.LecteurDesLieux = () => Lecture<LieuxLus>.De(EuropeDeTest.LieuxEurope);
                string savoie = guerre.Terres.Pays.Single(p => p.Nom == "Savoie").Id; var terres = guerre.Terres.Terres.Where(t => t.Pays == savoie).Select(t => t.CellId).ToArray();
                Assert.That(terres, Is.Not.Empty, "la Savoie n'a pas de terre");
                Vector2 centre = terres.Select(id => europe.Ici(carte.Lue.Cellules.First(c => c.CellId == id).Contour[0].Exterieur[0])).Aggregate((a, b) => a + b) / terres.Length;
                Choisir(europe, ModeDeCarte.Population); europe.Voir(centre, 120f); Assert.That(carte.LiseresMontres, Is.False, "le liseré se voit en Population");
                var franche = new Color(1f, 0f, 1f); foreach (long id in terres) carte.Rattacher(id, savoie, franche);
                bool Franc(Color c) => c.r > .45f && c.b > .45f && c.g < .3f;
                int Compter() {
                    typeof(CarteDessinee).GetMethod("LateUpdate", BindingFlags.Instance | BindingFlags.NonPublic).Invoke(carte, null); carte.camera.Render();
                    var ecran = carte.camera.targetTexture; var lu = new Texture2D(ecran.width, ecran.height, TextureFormat.RGBA32, false); RenderTexture.active = ecran;
                    try { lu.ReadPixels(new Rect(0, 0, ecran.width, ecran.height), 0, 0); lu.Apply(); return lu.GetPixels().Count(Franc); } finally { RenderTexture.active = null; UnityEngine.Object.DestroyImmediate(lu); }
                }
                carte.MontrerLesLiseres(true); int allume = Compter(); carte.MontrerLesLiseres(false); int eteint = Compter();
                Assert.That(allume, Is.GreaterThan(200), "liseré allumé, la Savoie ne prend pas la couleur de son pays : " + allume + " pixels");
                Assert.That(eteint, Is.Zero, "liseré éteint, la couleur du pays couvre encore la Savoie : " + eteint + " pixels");
            }
        }

        // Le mode choisi d'un clic sur son bouton, les lieux servis lus, puis la carte repeinte.
        static void Choisir(EuropeDeCarte europe, ModeDeCarte mode)
        {
            europe.Calques.BoutonDu(mode).onClick.Invoke(); europe.Peindre(); var fin = DateTime.UtcNow.AddSeconds(30);
            while (europe.Calques.LieuxEnVol && DateTime.UtcNow < fin) System.Threading.Thread.Sleep(10);
            europe.Peindre(); europe.Peindre();
            if (mode == ModeDeCarte.Population || mode == ModeDeCarte.Vivres) Assert.That(europe.Calques.LieuxLus?.Presente, Is.True, "les lieux servis ne sont pas lus");
        }
    }
}
