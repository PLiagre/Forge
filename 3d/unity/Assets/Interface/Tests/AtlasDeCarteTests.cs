using System.Collections.Generic;
using System.Linq;
using Forge.Pont;
using Forge.Pont.Tests;
using NUnit.Framework;
using UnityEngine;

namespace Forge.Interface.Tests
{
    // Les noms de l'atlas sur l'Europe entière relevée du vrai service : chaque fleuve tracé et nommé, chaque mer et chaque
    // région nommée, en italique, à son corps.
    public sealed class AtlasDeCarteTests
    {
        EuropeDeCarte europe;
        [OneTimeSetUp] public void Poser() => europe = new EuropeDeCarte();
        [OneTimeTearDown] public void Fermer() => europe?.Dispose();
        static AtlasLu Servi => EuropeDeTest.AtlasEurope;
        IEnumerable<NomCourbe> DeSorte(string sorte) => europe.Atlas.Noms.Where(n => europe.Atlas.SorteDe(n) == sorte);
        NomCourbe Nom(string sorte, string texte) => europe.Atlas.Noms.Single(n => europe.Atlas.SorteDe(n) == sorte && n.Texte == texte);

        [Test] public void Chaque_nom_de_l_atlas_est_pose_en_italique_et_chaque_fleuve_trace()
        {
            Assert.That(Servi.Mers.Count > 0 && Servi.Regions.Count > 0 && Servi.Fleuves.Count > 0, Is.True, "échantillon vide : l'atlas servi n'a pas ses trois sortes");
            Assert.That(DeSorte(AtlasDeCarte.MER).Select(n => n.Texte), Is.EquivalentTo(Servi.Mers.Select(m => m.Nom)), "une mer servie n'est pas nommée");
            Assert.That(DeSorte(AtlasDeCarte.REGION).Select(n => n.Texte), Is.EquivalentTo(Servi.Regions.Select(r => r.Nom)), "une région servie n'est pas nommée");
            Assert.That(DeSorte(AtlasDeCarte.FLEUVE).Select(n => n.Texte), Is.EquivalentTo(Servi.Fleuves.Select(f => f.Nom)), "un fleuve servi n'est pas nommé");
            foreach (NomCourbe nom in europe.Atlas.Noms)
                Assert.That((nom.Style, nom.Ecrit), Is.EqualTo((StyleDeNom.Italique, nom.Texte)), nom.Texte + " n'est pas écrit en italique, tel que servi");
            // Une mer et une région au point servi.
            foreach (NomDeLAtlas mer in Servi.Mers) Assert.That((Nom(AtlasDeCarte.MER, mer.Nom).Trace.Centre - europe.Ici(mer.Point)).magnitude, Is.LessThan(1e-2f), mer.Nom + " n'est pas à son point");
            foreach (NomDeLAtlas region in Servi.Regions) Assert.That((Nom(AtlasDeCarte.REGION, region.Nom).Trace.Centre - europe.Ici(region.Point)).magnitude, Is.LessThan(1e-2f), region.Nom + " n'est pas à son point");
            // Chaque ligne servie d'un fleuve a son trait, qui passe par ses points servis ; son nom se tient près de son cours.
            foreach (FleuveDeLAtlas fleuve in Servi.Fleuves)
            {
                var traits = europe.Atlas.Traits.Where(t => europe.Atlas.FleuveDuTrait(t) == fleuve.Nom).ToList();
                Assert.That(traits, Has.Count.EqualTo(fleuve.Lignes.Count), fleuve.Nom + " n'a pas un trait par ligne servie");
                for (int l = 0; l < traits.Count; l++)
                {
                    var trace = Enumerable.Range(0, traits[l].positionCount).Select(k => traits[l].GetPosition(k)).Select(p => new Vector2(p.x, p.z)).ToList();
                    Assert.That(trace.Count, Is.GreaterThanOrEqualTo(fleuve.Lignes[l].Count));
                    foreach (PointCarte point in fleuve.Lignes[l]) Assert.That(trace.Min(p => (p - europe.Ici(point)).magnitude), Is.LessThan(1e-2f), fleuve.Nom + " : le trait ne passe pas par un point servi");
                }
                // Le nom est décalé de sa corde d'un écart fixe, et la corde ne s'écarte du cours que de `DROIT` de sa longueur.
                Vector2 centre = Nom(AtlasDeCarte.FLEUVE, fleuve.Nom).Trace.Centre; float pres = float.MaxValue, longueur = 0f;
                foreach (var ligne in fleuve.Lignes)
                    for (int k = 1; k < ligne.Count; k++)
                    {
                        Vector2 a = europe.Ici(ligne[k - 1]), b = europe.Ici(ligne[k]), ab = b - a; longueur = Mathf.Max(longueur, ab.magnitude);
                        float s = Mathf.Clamp01(Vector2.Dot(centre - a, ab) / Mathf.Max(ab.sqrMagnitude, 1e-6f)); pres = Mathf.Min(pres, (centre - (a + ab * s)).magnitude);
                    }
                float total = fleuve.Lignes.Max(l => Enumerable.Range(1, l.Count - 1).Sum(k => (europe.Ici(l[k]) - europe.Ici(l[k - 1])).magnitude));
                Assert.That(pres, Is.LessThanOrEqualTo(AtlasDeCarte.ECART_DU_NOM * AtlasDeCarte.CORPS_DE_FLEUVE_KM + AtlasDeCarte.DROIT * total + 1f), fleuve.Nom + " : son nom est loin de son cours");
            }
            Assert.That(europe.Atlas.Traits.Sum(t => t.positionCount), Is.GreaterThan(Servi.Fleuves.Sum(f => f.Lignes.Sum(l => l.Count))), "échantillon vide : aucun trait n'est drapé entre ses points");
        }

        [Test] public void Une_mer_s_ecrit_plus_grand_qu_une_region_et_une_region_qu_un_fleuve()
        {
            float Min(string sorte) => DeSorte(sorte).Min(n => n.Corps); float Max(string sorte) => DeSorte(sorte).Max(n => n.Corps);
            Assert.That(Min(AtlasDeCarte.MER), Is.GreaterThan(Max(AtlasDeCarte.REGION)), "une région s'écrit aussi grand qu'une mer");
            Assert.That(Min(AtlasDeCarte.REGION), Is.GreaterThan(Max(AtlasDeCarte.FLEUVE)), "un fleuve s'écrit aussi grand qu'une région");
        }

        // De loin, la taille des mers les laisse lire et cache les fleuves ; de près, c'est l'inverse : les noms des petits pays
        // d'alentour, trop grands pour se lire, ne masquent plus la Loire. Le trait d'un fleuve garde sa largeur à l'écran.
        [Test] public void De_loin_les_mers_de_pres_les_fleuves()
        {
            NomCourbe mediterranee = Nom(AtlasDeCarte.MER, "Méditerranée"), loire = Nom(AtlasDeCarte.FLEUVE, "Loire");
            europe.Voir(mediterranee.Trace.Centre, 1500f);
            foreach (NomCourbe mer in DeSorte(AtlasDeCarte.MER)) Assert.That(NomsCourbes.Opacite(mer.CorpsPx, EuropeDeCarte.ECRAN_PX), Is.GreaterThan(0f), "de loin, " + mer.Texte + " est trop petite pour se lire");
            foreach (NomCourbe fleuve in DeSorte(AtlasDeCarte.FLEUVE)) Assert.That((fleuve.Opacite, fleuve.Rendu.enabled), Is.EqualTo((0f, false)), "de loin, " + fleuve.Texte + " se lit");
            Assert.That(mediterranee.Rendu.enabled, Is.True, "de loin, la Méditerranée n'est pas montrée");
            float kmParPixel = 2f * 1500f / EuropeDeCarte.ECRAN_PX;
            foreach (LineRenderer trait in europe.Atlas.Traits) Assert.That(trait.widthMultiplier / kmParPixel, Is.InRange(AtlasDeCarte.MIN_PX - 1e-3f, AtlasDeCarte.MAX_PX + 1e-3f), "de loin, un fleuve sort de sa largeur à l'écran");
            europe.Voir(loire.Trace.Centre, 100f);
            foreach (NomCourbe mer in DeSorte(AtlasDeCarte.MER)) Assert.That(mer.Opacite, Is.Zero, "de près, " + mer.Texte + " couvre la vue");
            foreach (NomCourbe fleuve in DeSorte(AtlasDeCarte.FLEUVE)) Assert.That(NomsCourbes.Opacite(fleuve.CorpsPx, EuropeDeCarte.ECRAN_PX), Is.GreaterThan(0f), "de près, " + fleuve.Texte + " est trop petit pour se lire");
            Assert.That(loire.Rendu.enabled, Is.True, "de près, la Loire n'est pas montrée : masquée " + loire.Masque + ", " + loire.CorpsPx + " px, opacité " + loire.Opacite + " ; noms lisibles proches : " + string.Join(", ", europe.Guerre.Ecriture.Lignes.Where(n => n.Opacite >= NomsCourbes.OPACITE_QUI_RESERVE).Concat(europe.Atlas.Noms.Where(n => !n.Masque && n.Opacite > 0f)).Where(n => (n.Trace.Centre - loire.Trace.Centre).magnitude < 200f).Select(n => n.Texte + " " + (int)n.CorpsPx)));
            kmParPixel = 2f * 100f / EuropeDeCarte.ECRAN_PX;
            foreach (LineRenderer trait in europe.Atlas.Traits) Assert.That(trait.widthMultiplier / kmParPixel, Is.InRange(AtlasDeCarte.MIN_PX - 1e-3f, AtlasDeCarte.MAX_PX + 1e-3f), "de près, un fleuve sort de sa largeur à l'écran");
        }

        // Un nom de l'atlas ne s'écrit pas sur un nom de pays lisible : la région « Bohême » se cache sous le pays du même nom.
        [Test] public void Un_nom_de_l_atlas_ne_s_ecrit_pas_sur_un_nom_de_pays()
        {
            foreach (float demi in new[] { 1500f, 600f })
            {
                europe.Voir(Nom(AtlasDeCarte.REGION, "Bohême").Trace.Centre, demi);
                var pays = europe.LettresDesPays(); Assert.That(pays, Is.Not.Empty, "échantillon vide : aucun nom de pays lisible");
                int montres = 0, masques = 0;
                foreach (NomCourbe nom in europe.Atlas.Noms)
                {
                    if (nom.Masque) masques++;
                    if (!nom.Rendu.enabled) continue;
                    montres++; var lettres = new List<Rect>(); europe.Atlas.Ecriture.Places(europe.Carte.camera, nom, lettres);
                    Assert.That(lettres.Any(l => pays.Any(p => p.Overlaps(l))), Is.False, nom.Texte + " s'écrit sur un nom de pays, demi " + demi);
                    if (europe.Atlas.SorteDe(nom) == AtlasDeCarte.REGION) Assert.That(europe.Guerre.NomsDesPays.Any(n => n.Texte == nom.Texte && n.Opacite > 0f), Is.False, "la région " + nom.Texte + " redit un nom de pays lisible");
                }
                Assert.That(montres, Is.GreaterThan(0), "échantillon vide : aucun nom de l'atlas montré, demi " + demi); Assert.That(masques, Is.GreaterThan(0), "échantillon vide : aucun nom de l'atlas masqué, demi " + demi);
            }
        }

        // Sans atlas lu, rien n'est posé, et la légende le dit.
        [Test] public void Un_atlas_absent_se_dit_dans_la_legende()
        {
            using (var sans = new EuropeDeCarte(() => Lecture<AtlasLu>.Absent("atlas : service coupé")))
            {
                Assert.That((sans.Atlas.Atlas, sans.Atlas.Noms.Count, sans.Atlas.Absence), Is.EqualTo(((AtlasLu)null, 0, "atlas : service coupé")));
                sans.Peindre(); sans.Peindre();
                Assert.That(sans.Calques.Legende.GetComponentInParent<Infobulle>().Phrase, Does.Contain("Noms de l'atlas non lus : atlas : service coupé"));
            }
        }
    }
}
