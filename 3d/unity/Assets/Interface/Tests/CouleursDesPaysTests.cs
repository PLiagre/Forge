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
