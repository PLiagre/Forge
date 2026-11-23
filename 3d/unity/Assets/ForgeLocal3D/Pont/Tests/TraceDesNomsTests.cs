using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using NUnit.Framework;
using UnityEngine;

namespace Forge.Pont.Tests {
    // Le tracé du nom d'un pays, tiré de la forme de sa terre : couché sur son grand axe, creusé comme elle, tenu sur
    // son plus grand morceau, et d'autant plus grand que la terre est étendue. Les terres témoins sont des carrés de
    // 10 km, chacun d'un seul lieu ; la carte figée, lue par ClientCarte, donne les puissances de 1400 pour pays. Un nom
    // suit le pays des cellules : sur la carte entière, chaque cellule se lève de son seul contour ; sur l'Ouest, de ses
    // lieux servis.
    public sealed class TraceDesNomsTests {
        private const double COTE = 10000;
        // Ce que six capitales avancent chacune, en corps : un nom de six lettres.
        private static readonly float[] SIX_LETTRES = { 0.7f, 0.7f, 0.7f, 0.7f, 0.7f, 0.7f };
        private static CarteLue _carte; private static TerrainDeCarte _terrain;

        // Une terre carrée de 10 km, son coin sud-ouest à (colonne, ligne) dizaines de km.
        private static CelluleDeCarte Carre(long id, int colonne, int ligne, double cote = COTE) {
            double x = colonne * COTE, y = ligne * COTE;
            var anneau = new[] { new PointCarte(x, y), new PointCarte(x + cote, y), new PointCarte(x + cote, y + cote), new PointCarte(x, y + cote), new PointCarte(x, y) };
            return new CelluleDeCarte(id, new[] { new PolygoneDeCarte(anneau, new IEnumerable<PointCarte>[0]) }, null, null, new VilleDeCarte[0]);
        }
        // Le terrain de terres carrées et le tracé de leurs pays : `pays[k]` est le pays de la k-ième terre.
        private static Dictionary<int, TraceDeNom> Tracer(out TerrainDeCarte terrain, int[] pays, params (int colonne, int ligne)[] terres) {
            terrain = FormesDeTest.Lever(new CarteLue(terres.Length, terres.Select((t, k) => Carre(k + 1, t.colonne, t.ligne)).ToArray()));
            return TraceDesNoms.Tracer(terrain, pays);
        }
        // Le point local, en km, d'un point donné en dizaines de km des terres témoins.
        private static Vector2 Local(TerrainDeCarte terrain, float colonne, float ligne) =>
            new Vector2((float)((colonne * COTE - terrain.Origine.X) / 1000.0), (float)((ligne * COTE - terrain.Origine.Y) / 1000.0));
        private static bool Chez(TerrainDeCarte terrain, int[] pays, int lePays, Vector2 p) { ushort n = terrain.CelluleEn(p.x, p.y); return n != 0 && pays[n - 1] == lePays; }

        [Test] public void Le_nom_se_couche_sur_le_grand_axe_de_la_terre() {
            // Trois terres d'ouest en est : 30 km sur 10.
            TraceDeNom enLigne = Tracer(out TerrainDeCarte t1, new[] { 0, 0, 0 }, (0, 0), (1, 0), (2, 0))[0];
            Assert.That(enLigne.Axe.x, Is.EqualTo(1f).Within(1e-3f), "le grand axe d'une bande d'ouest en est : " + enLigne.Axe);
            Assert.That((enLigne.Centre - Local(t1, 1.5f, 0.5f)).magnitude, Is.LessThan(0.1f), "le centre n'est pas celui de la bande");
            Assert.That(enLigne.Longueur, Is.EqualTo(28f).Within(1.5f)); Assert.That(enLigne.Largeur, Is.EqualTo(10f).Within(1f));
            Assert.That(Mathf.Abs(enLigne.Courbure), Is.LessThan(1e-4f), "une bande droite n'a pas de creux");
            // Les mêmes du sud au nord : le nom se dresse.
            TraceDeNom enColonne = Tracer(out _, new[] { 0, 0, 0 }, (0, 0), (0, 1), (0, 2))[0];
            Assert.That(Mathf.Abs(enColonne.Axe.y), Is.EqualTo(1f).Within(1e-3f), "le grand axe d'une bande du sud au nord : " + enColonne.Axe);
            Assert.That(enColonne.Longueur, Is.EqualTo(28f).Within(1.5f));
            // En escalier vers le nord-est : le nom monte, et se lit toujours d'ouest en est.
            TraceDeNom enBiais = Tracer(out _, new[] { 0, 0, 0, 0, 0 }, (0, 0), (1, 0), (1, 1), (2, 1), (2, 2))[0];
            Assert.That(enBiais.Axe.x, Is.GreaterThan(0.5f)); Assert.That(enBiais.Axe.y, Is.GreaterThan(0.5f), "le grand axe d'un escalier vers le nord-est : " + enBiais.Axe);
            TraceDeNom enDescente = Tracer(out _, new[] { 0, 0, 0, 0, 0 }, (0, 2), (1, 2), (1, 1), (2, 1), (2, 0))[0];
            Assert.That(enDescente.Axe.x, Is.GreaterThan(0.5f)); Assert.That(enDescente.Axe.y, Is.LessThan(-0.5f), "le grand axe d'un escalier vers le sud-est : " + enDescente.Axe);
        }

        [Test] public void Une_terre_ronde_porte_son_nom_d_ouest_en_est() {
            TraceDeNom rond = Tracer(out _, new[] { 0, 0, 0, 0 }, (0, 0), (1, 0), (0, 1), (1, 1))[0];
            Assert.That(rond.Axe, Is.EqualTo(Vector2.right), "une terre carrée n'a pas de grand axe");
            Assert.That(rond.Longueur, Is.EqualTo(18.8f).Within(1.5f)); Assert.That(rond.Largeur, Is.EqualTo(20f).Within(3f));
        }

        [Test] public void Le_nom_se_creuse_comme_la_terre_et_reste_sur_elle() {
            // Un croissant ouvert vers le nord : un ventre épais de deux rangs, et deux cornes au nord.
            int[] pays = new int[12];
            TraceDeNom croissant = Tracer(out TerrainDeCarte terrain, pays, (1, 0), (2, 0), (3, 0), (4, 0), (0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (0, 2), (5, 2))[0];
            float milieu = (croissant.Debut + croissant.Fin) / 2f;
            Assert.That(croissant.Axe.x, Is.GreaterThan(0.99f), "le grand axe du croissant : " + croissant.Axe);
            Assert.That(croissant.Courbure, Is.GreaterThan(0f), "le tracé ne se creuse pas vers le ventre du croissant");
            Assert.That(croissant.Point(croissant.Debut).y - croissant.Point(milieu).y, Is.GreaterThan(8f), "la corne de l'ouest n'est pas plus au nord que le ventre");
            Assert.That(croissant.Point(croissant.Fin).y - croissant.Point(milieu).y, Is.GreaterThan(8f), "la corne de l'est n'est pas plus au nord que le ventre");
            Assert.That(croissant.Sens(croissant.Debut).y, Is.LessThan(-0.2f), "le nom ne descend pas vers le ventre"); Assert.That(croissant.Sens(croissant.Fin).y, Is.GreaterThan(0.2f), "le nom ne remonte pas vers la corne");
            Assert.That(Mathf.Abs(croissant.Sens(croissant.Fin).y / croissant.Sens(croissant.Fin).x), Is.LessThanOrEqualTo(TraceDesNoms.PENTE_MAX * 1.05f), "le tracé penche trop à son bout");
            Assert.That(croissant.Longueur, Is.GreaterThan(60f), "le tracé ne va pas d'une corne à l'autre : " + croissant.Longueur);
            for (int k = 0; k <= 40; k++) Assert.That(Chez(terrain, pays, 0, croissant.Point(Mathf.Lerp(croissant.Debut, croissant.Fin, k / 40f))), Is.True, "le tracé sort du croissant au point " + k);
            NomCompose nom = croissant.Composer(SIX_LETTRES); Assert.That(nom, Is.Not.Null);
            Assert.That(nom.Lettres.Count(l => Chez(terrain, pays, 0, l.Point)), Is.EqualTo(6), "une lettre du croissant est hors de sa terre");
            Assert.That(nom.Lettres[0].Sens.y, Is.LessThan(0f)); Assert.That(nom.Lettres[5].Sens.y, Is.GreaterThan(0f), "les lettres ne tournent pas avec le tracé");
            // Contre-épreuve : le même croissant retourné se creuse dans l'autre sens.
            TraceDeNom retourne = Tracer(out _, pays, (1, 2), (2, 2), (3, 2), (4, 2), (0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (0, 0), (5, 0))[0];
            Assert.That(retourne.Courbure, Is.LessThan(0f), "le croissant retourné ne se creuse pas vers le nord");
        }

        [Test] public void Le_nom_ne_garde_du_trace_que_ce_qui_tient_sur_la_terre() {
            // Un fer à cheval aux angles vifs : aucune parabole ne le suit, et l'arc coupe la baie entre le ventre et chaque corne.
            int[] pays = new int[8];
            TraceDeNom fer = Tracer(out TerrainDeCarte terrain, pays, (0, 2), (0, 1), (1, 0), (2, 0), (3, 0), (4, 0), (5, 1), (5, 2))[0];
            for (int k = 0; k <= 40; k++) Assert.That(Chez(terrain, pays, 0, fer.Point(Mathf.Lerp(fer.Debut, fer.Fin, k / 40f))), Is.True, "le tracé sort du fer à cheval au point " + k);
            Assert.That(fer.Point(fer.Debut).x, Is.GreaterThanOrEqualTo(Local(terrain, 1f, 0f).x)); Assert.That(fer.Point(fer.Fin).x, Is.LessThanOrEqualTo(Local(terrain, 5f, 0f).x), "le tracé ne s'en tient pas au ventre");
            Assert.That(fer.Longueur, Is.InRange(20f, 42f), "la portion gardée n'est pas le ventre : " + fer.Longueur);
            Assert.That(fer.Composer(SIX_LETTRES).Lettres.Count(l => Chez(terrain, pays, 0, l.Point)), Is.EqualTo(6), "une lettre est écrite dans la baie");
            // Un lac de quelques km au milieu d'une bande ne coupe pas son nom.
            var ouest = new[] { new PointCarte(0, 0), new PointCarte(60000, 0), new PointCarte(60000, 10000), new PointCarte(0, 10000), new PointCarte(0, 0) };
            var est = new[] { new PointCarte(63000, 0), new PointCarte(123000, 0), new PointCarte(123000, 10000), new PointCarte(63000, 10000), new PointCarte(63000, 0) };
            var nord = new[] { new PointCarte(60000, 7000), new PointCarte(63000, 7000), new PointCarte(63000, 10000), new PointCarte(60000, 10000), new PointCarte(60000, 7000) };
            var sud = new[] { new PointCarte(60000, 0), new PointCarte(63000, 0), new PointCarte(63000, 3000), new PointCarte(60000, 3000), new PointCarte(60000, 0) };
            TerrainDeCarte troue = FormesDeTest.Lever(new CarteLue(4, new[] { ouest, est, nord, sud }.Select((anneau, k) =>
                new CelluleDeCarte(k + 1, new[] { new PolygoneDeCarte(anneau, new IEnumerable<PointCarte>[0]) }, null, null, new VilleDeCarte[0])).ToArray()));
            TraceDeNom bande = TraceDesNoms.Tracer(troue, new int[4])[0];
            Assert.That(troue.CelluleEn(bande.Centre.x, bande.Centre.y), Is.Zero, "échantillon vide : le milieu de la bande n'est pas un lac");
            Assert.That(bande.Longueur, Is.GreaterThan(100f), "un lac de quelques km coupe le nom : " + bande.Longueur);
            // Contre-épreuve : le même pays coupé par un voisin large de 20 km n'écrit son nom que d'un côté.
            TraceDeNom coupee = Tracer(out _, new[] { 0, 0, 0, 1, 1, 0, 0, 0 }, (0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (7, 0))[0];
            Assert.That(coupee.Longueur, Is.LessThan(31f), "le nom enjambe un voisin : " + coupee.Longueur);
        }

        [Test] public void Le_nom_tient_sur_le_plus_grand_morceau_du_pays() {
            // Le pays 0 : quatre terres à l'ouest, et une terre seule 80 km plus à l'est, au-delà du pays 1.
            int[] pays = { 0, 0, 0, 0, 1, 0 };
            Dictionary<int, TraceDeNom> traces = Tracer(out TerrainDeCarte terrain, pays, (0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (12, 0));
            TraceDeNom nom = traces[0];
            Assert.That((nom.Centre - Local(terrain, 2f, 0.5f)).magnitude, Is.LessThan(0.1f), "le centre n'est pas celui du grand morceau : " + nom.Centre);
            Assert.That(nom.Point(nom.Fin).x, Is.LessThan(Local(terrain, 4f, 0f).x), "le nom s'étire vers la terre détachée");
            Assert.That(nom.Echantillons, Is.EqualTo(4 * 100), "le tracé compte la terre détachée");
            Assert.That(Chez(terrain, pays, 0, nom.Point(nom.Debut)) && Chez(terrain, pays, 0, nom.Point(nom.Fin)), Is.True, "un bout du tracé est hors du pays");
            Assert.That(traces[1].Echantillons, Is.EqualTo(100)); Assert.That(traces.Keys, Is.EquivalentTo(new[] { 0, 1 }));
        }

        [Test] public void Le_corps_du_nom_suit_l_etendue_de_la_terre() {
            NomCompose petit = Tracer(out _, new[] { 0 }, (0, 0))[0].Composer(SIX_LETTRES);
            NomCompose bande = Tracer(out _, new[] { 0, 0, 0 }, (0, 0), (1, 0), (2, 0))[0].Composer(SIX_LETTRES);
            Assert.That(petit.Corps, Is.GreaterThan(0.5f)); Assert.That(bande.Corps, Is.GreaterThan(1.5f * petit.Corps), "trois terres n'écrivent pas plus grand qu'une");
            // Une longue bande est bornée par sa largeur : deux fois plus large, elle écrit plus grand.
            NomCompose longue = Tracer(out _, new int[6], (0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0))[0].Composer(SIX_LETTRES);
            NomCompose large = Tracer(out _, new int[12], (0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1))[0].Composer(SIX_LETTRES);
            Assert.That(large.Corps, Is.GreaterThan(1.5f * longue.Corps), "une terre deux fois plus large n'écrit pas plus grand");
            // Le nom tient dans la terre : jamais plus haut qu'une part de sa largeur, ni plus long qu'une part de sa longueur.
            TraceDeNom trace = Tracer(out _, new[] { 0, 0, 0 }, (0, 0), (1, 0), (2, 0))[0];
            Assert.That(bande.Corps, Is.LessThanOrEqualTo(TraceDeNom.PART_DE_LA_LARGEUR * trace.Largeur + 1e-3f)); Assert.That(bande.Etendue, Is.LessThanOrEqualTo(TraceDeNom.PART_DE_LA_LONGUEUR * trace.Longueur + 1e-3f));
            // Les lettres se suivent d'ouest en est, à pas égaux, centrées sur le tracé.
            for (int k = 1; k < 6; k++) Assert.That(bande.Lettres[k].Point.x - bande.Lettres[k - 1].Point.x, Is.EqualTo(0.7f * bande.Corps + bande.Interlettre).Within(0.05f));
            Assert.That((bande.Lettres[0].Point + bande.Lettres[5].Point) / 2f, Is.EqualTo(trace.Point((trace.Debut + trace.Fin) / 2f)).Using<Vector2>((u, v) => (u - v).magnitude < 0.1f ? 0 : 1));
            // Un nom de deux lettres sur une longue terre s'étale, sans écarter ses lettres de plus d'une part de son corps.
            NomCompose court = Tracer(out _, new[] { 0, 0, 0, 0, 0, 0 }, (0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0))[0].Composer(new[] { 0.7f, 0.7f });
            Assert.That(court.Interlettre, Is.EqualTo(TraceDeNom.INTERLETTRE_MAX * court.Corps).Within(1e-3f), "un nom court ne s'étale pas sur sa terre");
            Assert.That(Tracer(out _, new[] { 0 }, (0, 0))[0].Composer(new float[0]), Is.Null, "un nom sans lettre se compose");
        }

        [Test] public void Un_petit_pays_a_cote_d_un_grand_garde_tous_ses_points() {
            // Une terre de 600 km de côté fait lire le terrain un texel sur deux ; la terre de 4 km d'à côté est relue texel par texel.
            var grande = new[] { new PointCarte(0, 0), new PointCarte(600000, 0), new PointCarte(600000, 600000), new PointCarte(0, 600000), new PointCarte(0, 0) };
            var petite = new[] { new PointCarte(600000, 0), new PointCarte(604000, 0), new PointCarte(604000, 4000), new PointCarte(600000, 4000), new PointCarte(600000, 0) };
            var terrain = FormesDeTest.Lever(new CarteLue(2, new[] {
                new CelluleDeCarte(1, new[] { new PolygoneDeCarte(grande, new IEnumerable<PointCarte>[0]) }, null, null, new VilleDeCarte[0]),
                new CelluleDeCarte(2, new[] { new PolygoneDeCarte(petite, new IEnumerable<PointCarte>[0]) }, null, null, new VilleDeCarte[0]) }));
            Assert.That(terrain.TexelsDe(0), Is.GreaterThan(TraceDesNoms.ECHANTILLONS_VISES), "échantillon vide : le grand pays se lit texel par texel");
            Dictionary<int, TraceDeNom> traces = TraceDesNoms.Tracer(terrain, new[] { 0, 1 });
            Assert.That(traces[0].Echantillons, Is.LessThan(terrain.TexelsDe(0) / 2), "le grand pays n'est pas lu par échantillons");
            Assert.That(traces[1].Echantillons, Is.EqualTo(terrain.TexelsDe(1)), "le petit pays a perdu des points");
            Assert.That(traces[1].Longueur, Is.GreaterThan(2f)); Assert.That(traces[1].Composer(SIX_LETTRES).Corps, Is.GreaterThan(0.2f));
        }

        [Test] public void Un_pays_sans_terre_n_a_pas_de_trace_et_deux_traces_sont_egaux() {
            int[] pays = { 0, -1, 2 };
            Dictionary<int, TraceDeNom> un = Tracer(out TerrainDeCarte terrain, pays, (0, 0), (1, 0), (2, 0)), deux = TraceDesNoms.Tracer(terrain, pays);
            Assert.That(un.Keys, Is.EquivalentTo(new[] { 0, 2 }), "une terre sans pays a un nom, ou un pays sans terre");
            foreach (int cle in un.Keys) {
                TraceDeNom a = un[cle], b = deux[cle];
                Assert.That((a.Centre, a.Axe, a.Debut, a.Fin, a.Courbure, a.Largeur, a.Longueur, a.Echantillons), Is.EqualTo((b.Centre, b.Axe, b.Debut, b.Fin, b.Courbure, b.Largeur, b.Longueur, b.Echantillons)));
            }
            Assert.Throws<ArgumentNullException>(() => TraceDesNoms.Tracer(null, pays)); Assert.Throws<ArgumentNullException>(() => TraceDesNoms.Tracer(terrain, null));
        }

        // Sur la carte figée, chaque puissance de 1400 qui tient une terre a son tracé, dont les deux bouts tombent
        // sur sa terre ; un nom de six lettres y pose presque toutes ses lettres chez elle.
        [Test] public void Sur_la_carte_figee_chaque_puissance_a_son_trace_sur_sa_terre() {
            Figer();
            var cles = new Dictionary<string, int>(); var pays = new int[_carte.Cellules.Count];
            for (int r = 0; r < pays.Length; r++) {
                IdentiteDeCarte puissance = _carte.Cellules[r].Puissance;
                if (puissance == null || _terrain.TexelsDe(r) == 0) { pays[r] = -1; continue; }
                string cle = puissance.Id.ToString(); if (!cles.TryGetValue(cle, out int k)) { k = cles.Count; cles.Add(cle, k); }
                pays[r] = k;
            }
            Assert.That(cles.Count, Is.GreaterThan(20), "échantillon vide : la carte figée ne sert presque aucune puissance");
            var chrono = Stopwatch.StartNew(); Dictionary<int, TraceDeNom> traces = TraceDesNoms.Tracer(_terrain, pays); chrono.Stop();
            Assert.That(traces.Count, Is.EqualTo(cles.Count), "une puissance qui tient une terre n'a pas de tracé");
            int lettres = 0, chezElle = 0, courbes = 0; float plusGrand = 0f, plusPetit = float.MaxValue; var horsDeChezSoi = new List<string>();
            foreach (KeyValuePair<int, TraceDeNom> paire in traces) {
                TraceDeNom trace = paire.Value; NomCompose nom = trace.Composer(SIX_LETTRES);
                Assert.That(nom, Is.Not.Null, "la puissance " + paire.Key + " n'a nulle part où écrire son nom");
                Assert.That(Chez(_terrain, pays, paire.Key, trace.Point(trace.Debut)) && Chez(_terrain, pays, paire.Key, trace.Point(trace.Fin)), Is.True, "un bout du tracé de la puissance " + paire.Key + " est hors de sa terre");
                Assert.That(nom.Corps, Is.LessThanOrEqualTo(TraceDeNom.PART_DE_LA_LARGEUR * trace.Largeur + 1e-3f)); Assert.That(nom.Etendue, Is.LessThanOrEqualTo(TraceDeNom.PART_DE_LA_LONGUEUR * trace.Longueur + 1e-2f));
                int dedans = nom.Lettres.Count(l => Chez(_terrain, pays, paire.Key, l.Point)); lettres += 6; chezElle += dedans;
                if (dedans < 5) horsDeChezSoi.Add(paire.Key + " (" + dedans + "/6)");
                if (Mathf.Abs(trace.Courbure) * trace.Longueur > 0.15f) courbes++;
                plusGrand = Mathf.Max(plusGrand, nom.Corps); plusPetit = Mathf.Min(plusPetit, nom.Corps);
            }
            UnityEngine.Debug.Log("TRACE DES NOMS : " + traces.Count + " puissances tracées en " + chrono.ElapsedMilliseconds + " ms ; " + chezElle + " lettres sur " + lettres
                + " sur la terre de leur pays ; " + courbes + " tracés courbes ; corps de " + plusPetit.ToString("0.0") + " à " + plusGrand.ToString("0.0") + " km ; moins de cinq lettres chez soi : "
                + (horsDeChezSoi.Count == 0 ? "aucun" : string.Join(", ", horsDeChezSoi)));
            Assert.That(chezElle, Is.GreaterThanOrEqualTo(lettres * 9 / 10), "plus d'une lettre sur dix est écrite hors de la terre de son pays");
            Assert.That(courbes, Is.GreaterThan(0), "échantillon vide : aucun tracé courbe sur la carte de 1400");
            Assert.That(plusGrand, Is.GreaterThan(4f * plusPetit), "les noms ne suivent pas l'étendue des puissances");
        }

        // Sur le terrain des lieux de l'Ouest, chaque puissance servie porte son nom sur sa terre : les lieux d'une
        // cellule portent le nom du pays de leur cellule.
        [Test] public void Sur_le_terrain_des_lieux_chaque_puissance_a_son_trace_sur_sa_terre() {
            CarteLue carte = FormesDeTest.CarteOuest; TerrainDeCarte terrain = FormesDeTest.TerrainOuest;
            var cles = new Dictionary<long, int>(); var pays = new int[carte.Cellules.Count];
            for (int r = 0; r < pays.Length; r++) {
                IdentiteDeCarte puissance = carte.Cellules[r].Puissance;
                if (puissance == null) { pays[r] = -1; continue; }
                if (!cles.TryGetValue(puissance.Id, out int k)) { k = cles.Count; cles.Add(puissance.Id, k); }
                pays[r] = k;
            }
            Assert.That(cles.Count, Is.GreaterThanOrEqualTo(6), "échantillon vide : l'Ouest ne sert presque aucune puissance");
            Assert.That(terrain.NombreDeLieux, Is.GreaterThan(carte.Cellules.Count * 5), "échantillon vide : les cellules de l'Ouest n'ont pas leurs lieux");
            Dictionary<int, TraceDeNom> traces = TraceDesNoms.Tracer(terrain, pays);
            Assert.That(traces.Keys, Is.EquivalentTo(cles.Values), "une puissance qui tient une terre n'a pas de tracé");
            int lettres = 0, chezElle = 0;
            foreach (KeyValuePair<int, TraceDeNom> paire in traces) {
                TraceDeNom trace = paire.Value; NomCompose nom = trace.Composer(SIX_LETTRES);
                Assert.That(nom, Is.Not.Null, "la puissance " + paire.Key + " n'a nulle part où écrire son nom");
                Assert.That(Chez(terrain, pays, paire.Key, trace.Point(trace.Debut)) && Chez(terrain, pays, paire.Key, trace.Point(trace.Fin)), Is.True, "un bout du tracé de la puissance " + paire.Key + " est hors de sa terre");
                lettres += 6; chezElle += nom.Lettres.Count(l => Chez(terrain, pays, paire.Key, l.Point));
            }
            Assert.That(chezElle, Is.GreaterThanOrEqualTo(lettres * 9 / 10), "plus d'une lettre sur dix est écrite hors de la terre de son pays");
        }

        private static void Figer() {
            if (_terrain != null) return;
            byte[] octets = File.ReadAllBytes(Application.dataPath + "/ForgeLocal3D/Pont/Tests/carte-graine0.json");
            var sonde = new TcpListener(IPAddress.Loopback, 0);
            sonde.Start(); int port = ((IPEndPoint)sonde.LocalEndpoint).Port; sonde.Stop();
            var ecoute = new HttpListener(); ecoute.Prefixes.Add("http://127.0.0.1:" + port + "/"); ecoute.Start();
            var fil = new Thread(() => {
                try {
                    HttpListenerContext ctx = ecoute.GetContext();
                    ctx.Response.StatusCode = 200; ctx.Response.ContentLength64 = octets.Length;
                    ctx.Response.OutputStream.Write(octets, 0, octets.Length); ctx.Response.Close();
                } catch (Exception) { }
            }) { IsBackground = true };
            fil.Start();
            try {
                using (var client = new ClientCarte(port, ClientCarte.DelaiMinimal))
                { var lecture = client.Lire(); Assert.IsTrue(lecture.Presente, lecture.Absence); _carte = lecture.Carte; }
            } finally { ecoute.Close(); fil.Join(TimeSpan.FromSeconds(5)); }
            _terrain = FormesDeTest.Lever(_carte);
        }
    }
}
