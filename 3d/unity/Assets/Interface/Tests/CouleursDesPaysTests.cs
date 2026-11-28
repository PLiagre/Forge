using System;
using System.Collections.Generic;
using System.Linq;
using Forge.Pont;
using Forge.Pont.Tests;
using NUnit.Framework;
using UnityEngine;

namespace Forge.Interface.Tests
{
    // Les couleurs des pays sur l'Europe entière relevée du vrai service (`EuropeDeTest`), avec ses voisinages servis.
    public sealed class CouleursDesPaysTests
    {
        static TerresDeLaCarte Terres => EuropeDeTest.TerresEurope;
        static IReadOnlyList<CoteDeCarte> cotes;
        static IReadOnlyList<CoteDeCarte> Cotes => cotes ?? (cotes = new VoisinageDeCarte(EuropeDeTest.CarteEurope, EuropeDeTest.TerrainEurope.Origine).Cotes);
        static CouleursDesPays Colorier(TerresDeLaCarte terres, CouleursDesPays avant = null) => CouleursDesPays.Colorier(terres, CouleursDesPays.VoisinsDesPays(terres, Cotes), avant);
        // Les pays qui tiennent une terre ou un lieu, et les paires de voisins entre eux.
        static HashSet<string> Tenants(TerresDeLaCarte terres) => new HashSet<string>(terres.Terres.Select(t => t.Pays).Concat(terres.Terres.SelectMany(t => t.AutresPays.Select(l => l.Pays))).Where(p => p != null));
        static List<(string a, string b)> Paires(CouleursDesPays c) => c.Voisins.SelectMany(v => v.Value.Where(b => string.CompareOrdinal(v.Key, b) < 0).Select(b => (v.Key, b))).ToList();
        static float Teinte(Color c) { Color.RGBToHSV(c, out float h, out _, out _); return h * 360f; }
        static float L(Color c) { Color.RGBToHSV(c, out _, out _, out float v); return v; }

        // Le hachage de l'identifiant, tel que la carte le peignait : sur la même Europe, des voisins s'y confondent. Sans cela, le cas d'après ne prouverait rien.
        [Test] public void Le_hachage_de_l_identifiant_confond_des_voisins()
        {
            Color Hache(string id) { uint h = 2166136261u; foreach (char ch in id) { h ^= ch; h *= 16777619u; } return SocleInterface.Pigment(MaillageDeCarte.CouleurPourPuissance(h)); }
            var paires = Paires(Colorier(Terres)); Assert.That(paires, Is.Not.Empty, "échantillon vide : aucun voisinage entre pays");
            Assert.That(paires.Count(p => CouleursDesPays.Ecart(Hache(p.a), Hache(p.b)) < CouleursDesPays.ECART_MIN), Is.GreaterThan(0), "le hachage sépare déjà tous les voisins : le cas des couleurs ne peut pas échouer");
        }

        [Test] public void Chaque_pays_tenant_a_sa_couleur_et_ses_voisins_ne_l_ont_pas()
        {
            var c = Colorier(Terres); var tenants = Tenants(Terres);
            Assert.That(tenants.Count, Is.GreaterThan(1), "échantillon vide : aucun pays ne tient de terre");
            Assert.That(c.Conflits, Is.Zero, "des voisins n'ont pas pu être séparés");
            foreach (string p in tenants) Assert.That(c.Couleur(p), Is.Not.EqualTo(CouleursDesPays.SansPays), p + " n'a pas de couleur à lui");
            var paires = Paires(c); var autres = paires.Where(p => c.Racine(p.a) != c.Racine(p.b)).ToList(); var memes = paires.Where(p => c.Racine(p.a) == c.Racine(p.b)).ToList();
            Assert.That(autres, Is.Not.Empty, "échantillon vide : aucun voisin d'un autre bloc"); Assert.That(memes, Is.Not.Empty, "échantillon vide : aucun vassal voisin de son bloc");
            foreach (var (a, b) in autres)
                Assert.That(CouleursDesPays.Ecart(c.Couleur(a), c.Couleur(b)), Is.GreaterThanOrEqualTo(CouleursDesPays.ECART_MIN), a + " et " + b + " se confondent");
            foreach (var (a, b) in paires) Assert.That((Color32)c.Couleur(a), Is.Not.EqualTo((Color32)c.Couleur(b)), a + " et " + b + " ont la même couleur");
        }

        // Deux blocs voisins ont deux familles de teinte : sur le cercle des teintes perçues, deux de leurs pays qui se touchent sont
        // à `ECART_DE_TEINTE_MIN` au moins l'un de l'autre et à `ECART_MIN` au moins, quel que soit leur éclaircissement, et leurs
        // racines aussi. La France et l'Angleterre se touchent par la Guyenne : la Guyenne a la teinte de l'Angleterre, pas celle de la France.
        const string ANGLETERRE = "puissance-1", FRANCE = "puissance-3", GUYENNE = "puissance-42";
        [Test] public void Deux_blocs_voisins_n_ont_jamais_la_meme_famille_de_teinte()
        {
            var c = Colorier(Terres); Assert.That(c.Conflits, Is.Zero, "des voisins n'ont pas pu être séparés");
            var autres = Paires(c).Where(p => c.Racine(p.a) != c.Racine(p.b)).ToList(); Assert.That(autres, Is.Not.Empty, "échantillon vide : aucun voisin d'un autre bloc");
            Assert.That((Terres.SuzerainDe(GUYENNE), c.Racine(GUYENNE), Terres.NomDuPays(FRANCE), Terres.NomDuPays(ANGLETERRE)), Is.EqualTo((ANGLETERRE, ANGLETERRE, "France", "Angleterre")), "échantillon vide : la Guyenne ne relève pas de l'Angleterre");
            Assert.That(autres.Any(p => new HashSet<string> { c.Racine(p.a), c.Racine(p.b) }.SetEquals(new[] { FRANCE, ANGLETERRE })), Is.True, "échantillon vide : les blocs de la France et de l'Angleterre ne se touchent pas");
            string Nom(string id) => Terres.NomDuPays(id) ?? id;
            var fautes = new List<string>();
            foreach (var (a, b) in autres)
            {
                Color ca = c.Couleur(a), cb = c.Couleur(b), ra = c.Couleur(c.Racine(a)), rb = c.Couleur(c.Racine(b));
                float teinte = CouleursDesPays.EcartDeTeinte(ca, cb), ecart = CouleursDesPays.Ecart(ca, cb), racines = CouleursDesPays.EcartDeTeinte(ra, rb);
                if (teinte < CouleursDesPays.ECART_DE_TEINTE_MIN || racines < CouleursDesPays.ECART_DE_TEINTE_MIN || ecart < CouleursDesPays.ECART_MIN)
                    fautes.Add(Nom(a) + " (bloc " + Nom(c.Racine(a)) + ") et " + Nom(b) + " (bloc " + Nom(c.Racine(b)) + ") : " + teinte.ToString("0") + "° de teinte, racines à " + racines.ToString("0") + "°, ΔE " + ecart.ToString("0.0"));
            }
            Assert.That(fautes, Is.Empty, fautes.Count + " paires de voisins de deux blocs se confondent sur " + autres.Count + " : " + string.Join(" ; ", fautes.Take(12)));
            Assert.That(CouleursDesPays.EcartDeTeinte(c.Couleur(GUYENNE), c.Couleur(ANGLETERRE)), Is.LessThan(CouleursDesPays.ECART_DE_TEINTE_MIN / 4f), "la Guyenne n'a pas la teinte de l'Angleterre");
            Assert.That(CouleursDesPays.EcartDeTeinte(c.Couleur(GUYENNE), c.Couleur(FRANCE)), Is.GreaterThanOrEqualTo(CouleursDesPays.ECART_DE_TEINTE_MIN), "la Guyenne a la teinte de la France");
        }

        // Deux petits voisins se distinguent franchement : Byzance et les Ottomans, qui se touchent aux Détroits, ont deux familles qui ne
        // se suivent pas sur le cercle des sept teintes, à 80° de teinte perçue au moins, et la carte reste sans conflit. Sur toute
        // l'Europe, la plupart des blocs voisins font de même : un bloc ne prend la famille voisine de celle d'un voisin que faute d'autre,
        // et alors celle qui touche le moins de voisins.
        const string BYZANCE = "puissance-25", OTTOMANS = "puissance-26";
        [Test] public void Deux_petits_voisins_ont_deux_teintes_franchement_differentes()
        {
            var c = Colorier(Terres); Assert.That(c.Conflits, Is.Zero, "des voisins n'ont pas pu être séparés");
            Assert.That((Terres.NomDuPays(BYZANCE), Terres.NomDuPays(OTTOMANS)), Is.EqualTo(("Byzance", "Ottomans")));
            Assert.That(c.Voisins.TryGetValue(BYZANCE, out var autour) && autour.Contains(OTTOMANS), Is.True, "échantillon vide : Byzance et les Ottomans ne se touchent pas");
            int familles = SocleInterface.NomsDesFamilles.Count; bool Voisines(int f, int g) => (f - g + familles) % familles == 1 || (g - f + familles) % familles == 1;
            int fb = c.FamilleDe(BYZANCE), fo = c.FamilleDe(OTTOMANS);
            string Entour(string pays) => string.Join(", ", c.Voisins.Where(v => c.Racine(v.Key) == c.Racine(pays)).SelectMany(v => v.Value).Select(c.Racine).Where(r => r != c.Racine(pays)).Distinct()
                .Select(r => (Terres.NomDuPays(r) ?? r) + " " + SocleInterface.NomsDesFamilles[c.FamilleDe(r)]));
            Assert.That(fb != fo && !Voisines(fb, fo), Is.True, "Byzance (" + SocleInterface.NomsDesFamilles[fb] + ") et les Ottomans (" + SocleInterface.NomsDesFamilles[fo] + ") ont deux familles voisines ; autour de Byzance : " + Entour(BYZANCE));
            Assert.That(CouleursDesPays.EcartDeTeinte(c.Couleur(BYZANCE), c.Couleur(OTTOMANS)), Is.GreaterThanOrEqualTo(80f));
            var blocs = Paires(c).Select(p => (c.Racine(p.a), c.Racine(p.b))).Where(p => p.Item1 != p.Item2).Distinct().ToList();
            int proches = blocs.Count(p => Voisines(c.FamilleDe(p.Item1), c.FamilleDe(p.Item2)));
            Assert.That(blocs.Count, Is.GreaterThan(50), "échantillon vide : trop peu de blocs voisins");
            // Sur une carte aussi dense, sept familles ne séparent pas tous les voisins : un sur trois se suivrait sans la préférence, moins de 28 % avec elle.
            Assert.That(proches * 100, Is.LessThan(28 * blocs.Count), proches + " paires de blocs voisins sur " + blocs.Count + " ont deux familles qui se suivent sur le cercle");
        }

        // Deux pigments de deux familles se séparent à toute clarté : à `ECART_DE_TEINTE_MIN` et à `ECART_MIN` au moins, chacun
        // éclairci de n'importe quelle part. Le gris des terres sans pays reste loin de tout pigment, à toute part.
        [Test] public void Deux_familles_se_separent_a_toute_clarte_et_le_gris_reste_neutre()
        {
            int n = SocleInterface.PigmentsDesPays.Count, familles = Enumerable.Range(0, n).Select(SocleInterface.FamilleDuPigment).Distinct().Count();
            Assert.That(familles, Is.GreaterThanOrEqualTo(5), "trop peu de familles pour colorier une carte");
            Assert.That(familles, Is.LessThan(n), "échantillon vide : aucune famille n'a deux clartés");
            var fautes = new List<string>();
            for (int i = 0; i < n; i++)
                for (int j = i + 1; j < n; j++)
                {
                    if (SocleInterface.FamilleDuPigment(i) == SocleInterface.FamilleDuPigment(j)) continue;
                    for (int pi = 0; pi <= CouleursDesPays.PARTS.Count; pi++)
                        for (int pj = 0; pj <= CouleursDesPays.PARTS.Count; pj++)
                        {
                            Color a = CouleursDesPays.Peindre(i, pi), b = CouleursDesPays.Peindre(j, pj);
                            float teinte = CouleursDesPays.EcartDeTeinte(a, b), ecart = CouleursDesPays.Ecart(a, b);
                            if (teinte < CouleursDesPays.ECART_DE_TEINTE_MIN || ecart < CouleursDesPays.ECART_MIN) fautes.Add(i + "/" + pi + " et " + j + "/" + pj + " : " + teinte.ToString("0") + "°, ΔE " + ecart.ToString("0.0"));
                        }
                }
            Assert.That(fautes, Is.Empty, fautes.Count + " paires de pigments de deux familles se confondent : " + string.Join(" ; ", fautes.Take(12)));
            for (int k = 0; k < n; k++)
                for (int p = 0; p <= CouleursDesPays.PARTS.Count; p++)
                    Assert.That(CouleursDesPays.Ecart(CouleursDesPays.SansPays, CouleursDesPays.Peindre(k, p)), Is.GreaterThanOrEqualTo(CouleursDesPays.ECART_MIN), "le gris des terres sans pays se confond avec le pigment " + k + "/" + p);
        }

        // Hors de tout ensemble, un vassal porte le liseré de son bloc, tiré du pigment de sa racine : la frontière du bloc se lit d'un même trait.
        [Test] public void Un_vassal_hors_ensemble_porte_le_lisere_de_son_bloc()
        {
            var c = Colorier(Terres); var tenants = Tenants(Terres);
            var vassaux = Terres.Pays.Where(p => p.Suzerain != null && p.Ensemble == null && tenants.Contains(p.Id)).ToList();
            Assert.That(vassaux.Select(v => v.Id), Does.Contain(GUYENNE), "échantillon vide : la Guyenne n'est pas un vassal hors ensemble qui tient une terre");
            foreach (var v in vassaux)
                Assert.That((Color32)c.Lisere(v.Id), Is.EqualTo((Color32)CalquesCarte.LisereDuPigment(c.Couleur(c.Racine(v.Id)))), v.Nom + " n'a pas le liseré de " + (Terres.NomDuPays(c.Racine(v.Id)) ?? c.Racine(v.Id)));
            Assert.That((Color32)c.Lisere(FRANCE), Is.EqualTo((Color32)CalquesCarte.LisereDuPigment(c.Couleur(FRANCE))), "la France n'a pas le liseré tiré de son pigment");
        }

        // Quand les lieux qui se touchent sont connus, un lieu d'un autre pays ne se lie qu'aux pays des lieux qu'il touche : jamais, par
        // défaut, à tous ceux des terres d'à côté, ce qui ferait de huit petits pays d'une terre des voisins de tout l'entourage, plus
        // qu'aucun coloriage ne sépare. Sans les lieux, la règle grossière reste.
        [Test] public void Avec_les_lieux_un_lieu_d_un_autre_pays_ne_se_lie_qu_a_ceux_qu_il_touche()
        {
            var cote = Cotes.First(k => Terres.PaysDe(k.Dedans) != null && Terres.PaysDe(k.Dehors) != null && Terres.PaysDe(k.Dedans) != Terres.PaysDe(k.Dehors));
            long ici = cote.Dedans; string tenant = Terres.PaysDe(ici), voisin = Terres.PaysDe(cote.Dehors);
            // Huit petits pays, chacun un lieu de la terre, en file : chacun touche le précédent, le premier touche le lieu 0 du tenant.
            var petits = Enumerable.Range(1, 8).Select(k => "petit-" + k).ToList();
            var pays = Terres.Pays.Concat(petits.Select(p => new PaysDeLaCarte(p, p))).ToList();
            var terres = new TerresDeLaCarte(Terres.Tick, Terres.Date, pays, Terres.Terres.Select(t => t.CellId != ici ? t : new TerreLue(t.CellId, t.Maitre, t.Pays, t.Maison, petits.Select((p, k) => new LieuDAutrePays(k + 1, p, p)))));
            var lieux = Enumerable.Range(0, 8).Select(k => (ici, (long)k, ici, (long)k + 1)).ToList();
            var fins = CouleursDesPays.VoisinsDesPays(terres, Cotes, lieux);
            Assert.That(fins["petit-1"], Is.EquivalentTo(new[] { tenant, "petit-2" }), "le premier petit pays se lie à d'autres que ceux qu'il touche");
            Assert.That(fins["petit-5"], Is.EquivalentTo(new[] { "petit-4", "petit-6" }), "un petit pays au milieu de la terre se lie à ceux des terres d'à côté");
            Assert.That(fins[voisin].Overlaps(petits), Is.False, "un petit pays qui ne touche pas la terre d'à côté en est voisin");
            // Contre-épreuve : sans les lieux, chaque petit pays reste lié à sa terre et à celles d'à côté.
            var grossiers = CouleursDesPays.VoisinsDesPays(terres, Cotes);
            Assert.That(grossiers["petit-5"], Does.Contain(tenant).And.Contain(voisin), "sans les lieux, la règle grossière ne lie plus un lieu d'un autre pays à son entourage");
            Assert.That(CouleursDesPays.Colorier(terres, fins).Conflits, Is.Zero, "des voisins n'ont pas pu être séparés");
        }

        [Test] public void Un_vassal_porte_la_teinte_de_son_suzerain_plus_claire()
        {
            var c = Colorier(Terres);
            var vassaux = Terres.Pays.Where(p => p.Suzerain != null).ToList(); Assert.That(vassaux, Is.Not.Empty, "échantillon vide : aucun vassal servi");
            foreach (var v in vassaux)
            {
                Color lui = c.Couleur(v.Id), suzerain = c.Couleur(v.Suzerain); float ecart = Mathf.Abs(Teinte(lui) - Teinte(suzerain));
                Assert.That(Mathf.Min(ecart, 360f - ecart), Is.LessThan(3f), v.Nom + " n'a pas la teinte de son suzerain");
                Assert.That(L(lui), Is.GreaterThan(L(suzerain)), v.Nom + " n'est pas plus clair que son suzerain");
                Assert.That(c.Racine(v.Id), Is.EqualTo(c.Racine(v.Suzerain)));
            }
        }

        [Test] public void Les_membres_d_un_ensemble_partagent_son_lisere()
        {
            var c = Colorier(Terres);
            var membres = Terres.Pays.Where(p => p.Ensemble != null).ToList(); Assert.That(membres.Count, Is.GreaterThan(1), "échantillon vide : moins de deux membres d'un ensemble");
            foreach (var groupe in membres.GroupBy(p => p.Ensemble))
                foreach (var p in groupe) Assert.That((Color32)c.Lisere(p.Id), Is.EqualTo((Color32)SocleInterface.LisereDeLEnsemble(groupe.Key)), p.Nom + " n'a pas le liseré de " + groupe.Key);
            var hors = Terres.Pays.Where(p => p.Ensemble == null && Tenants(Terres).Contains(p.Id)).ToList(); Assert.That(hors, Is.Not.Empty);
            var liseres = new HashSet<Color32>(membres.Select(p => SocleInterface.LisereDeLEnsemble(p.Ensemble)).Select(x => (Color32)x));
            foreach (var p in hors) Assert.That(liseres.Contains(c.Lisere(p.Id)), Is.False, p.Nom + " porte le liseré d'un ensemble dont il n'est pas");
        }

        // Une relecture des mêmes terres ne change rien ; une terre prise ne recolore que les blocs autour d'elle.
        [Test] public void Une_terre_prise_ne_recolore_que_ce_qu_elle_force()
        {
            var c = Colorier(Terres); Assert.That(Colorier(Terres, c).MemesCouleurs(c), Is.True, "une relecture des mêmes terres change des couleurs");
            Assert.That(Colorier(Terres).MemesCouleurs(c), Is.True, "deux coloriages des mêmes terres diffèrent");
            // Chaque terre est prise à son tour par le pays d'une voisine d'un autre bloc, jusqu'à une prise qui force un changement.
            var parCellule = Terres.Terres.ToDictionary(t => t.CellId);
            int prises = 0, forcees = 0, confondues = 0;
            foreach (var cote in Cotes)
            {
                TerreLue prise = parCellule[cote.Dedans]; string preneur = parCellule[cote.Dehors].Pays;
                if (preneur == null || prise.Pays == null || c.Racine(preneur) == c.Racine(prise.Pays) || prises >= 40) continue;
                prises++;
                var apres = new TerresDeLaCarte(Terres.Tick + 1, Terres.Date, Terres.Pays, Terres.Terres.Select(t => t.CellId == prise.CellId ? new TerreLue(t.CellId, t.Maitre, preneur, t.Maison, t.AutresPays) : t));
                var neuves = Colorier(apres, c);
                // Garder les couleurs d'avant ne sépare jamais moins de voisins qu'un coloriage neuf de la même carte.
                int neufs = Colorier(apres).Conflits; Assert.That(neuves.Conflits, Is.LessThanOrEqualTo(neufs), "la prise de " + prise.CellId + " laisse plus de voisins confondus qu'un coloriage neuf");
                if (neuves.Conflits > 0) confondues++;
                // Les blocs qu'une prise peut forcer : celui du preneur et ceux qui touchent la terre prise.
                var autour = new HashSet<string> { c.Racine(preneur) };
                foreach (var k in Cotes.Where(k => k.Dedans == prise.CellId || k.Dehors == prise.CellId)) foreach (long id in new[] { k.Dedans, k.Dehors }) if (parCellule[id].Pays != null) autour.Add(c.Racine(parCellule[id].Pays));
                // Et leur entourage, qu'un bloc sans pigment permis replace autour de lui.
                foreach (string bloc in autour.ToList()) foreach (string membre in Terres.Pays.Select(p => p.Id).Where(id => neuves.Racine(id) == bloc)) if (neuves.Voisins.TryGetValue(membre, out var vs)) foreach (string v in vs) autour.Add(neuves.Racine(v));
                var changes = Terres.Pays.Select(p => p.Id).Where(id => !((Color32)neuves.Couleur(id)).Equals((Color32)c.Couleur(id))).ToList();
                foreach (string id in changes) Assert.That(autour.Contains(c.Racine(id)), Is.True, "la prise de " + prise.CellId + " recolore " + id + ", loin d'elle");
                if (changes.Count > 0) forcees++;
            }
            Assert.That(prises, Is.GreaterThan(0), "échantillon vide : aucune prise essayée");
            TestContext.WriteLine("prises " + prises + ", dont " + forcees + " qui recolorent et " + confondues + " qui laissent des voisins confondus");
        }
    }
}
