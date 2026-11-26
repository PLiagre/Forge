using System.Collections.Generic;
using System.Linq;
using Forge.Pont;
using NUnit.Framework;
using UnityEngine;

namespace Forge.Interface.Tests
{
    // Les noms courbes posés sur un sol qui n'est pas plat : chaque sommet d'une lettre est à sa place sur le sol, et
    // une grande lettre se découpe en carreaux pour le suivre. Le sol témoin est une pente ondulée, donnée au nom
    // comme la carte donne le sien ; le tracé témoin est une droite de 600 km d'ouest en est, sur une terre large de 300.
    public sealed class NomsCourbesTests
    {
        const int ECRAN_PX = 900;
        GameObject racine; Camera camera; RenderTexture ecran; NomsCourbes noms;

        static Vector3 Sol(Vector2 p) => new Vector3(p.x, 6f + 5f * Mathf.Sin(p.x / 40f) + 0.02f * p.y, p.y);

        [SetUp] public void Ouvrir()
        {
            racine = new GameObject("Noms témoins"); ecran = new RenderTexture(1600, ECRAN_PX, 16);
            camera = new GameObject("Caméra témoin").AddComponent<Camera>(); camera.transform.SetParent(racine.transform, false); camera.targetTexture = ecran;
            camera.orthographic = true; camera.transform.SetPositionAndRotation(new Vector3(0, 500, 0), Quaternion.Euler(90, 0, 0));
        }
        [TearDown] public void Fermer() { noms?.Dispose(); noms = null; camera.targetTexture = null; Object.DestroyImmediate(racine); Object.DestroyImmediate(ecran); }

        NomCourbe Ecrire(float longueur, float largeur, System.Func<Vector2, Vector3> sol)
        {
            noms = new NomsCourbes(racine.transform, SocleInterface.Police(titre: true), SocleInterface.Couleur("encre"), SocleInterface.Couleur("papier"), sol);
            var trace = new TraceDeNom(Vector2.zero, Vector2.right, -longueur / 2f, longueur / 2f, 0f, 0f, 0f, largeur, 100);
            noms.Ecrire(new[] { ("pays-a", "Avalon", trace) }); return noms.Noms.Single();
        }
        // La vue montre `demi` km de part et d'autre du centre, et le nom s'y règle.
        void Voir(float demi) { camera.orthographicSize = demi; noms.Suivre(camera); }

        [Test] public void Une_grande_lettre_se_decoupe_en_carreaux_poses_sur_le_sol()
        {
            NomCourbe nom = Ecrire(600f, 300f, Sol);
            Assert.That(nom.Corps, Is.GreaterThan(4f * NomsCourbes.CARREAU_KM), "échantillon vide : la lettre tient dans un carreau");
            Voir(nom.Corps * ECRAN_PX / (2f * 60f)); // un corps de 60 pixels : lisible, à pleine encre
            Assert.That(nom.Opacite, Is.EqualTo(1f)); Mesh m = nom.Maillage; Vector3[] sommets = m.vertices;
            // Six lettres, chacune découpée au plus fin : sept sommets par côté.
            int cote = NomsCourbes.CARREAUX_MAX + 1;
            Assert.That(sommets.Length, Is.EqualTo(6 * cote * cote), "les lettres ne sont pas découpées en carreaux"); Assert.That(m.GetTriangles(0).Length, Is.EqualTo(6 * 6 * NomsCourbes.CARREAUX_MAX * NomsCourbes.CARREAUX_MAX));
            Assert.That(sommets.All(p => (p - Sol(new Vector2(p.x, p.z))).magnitude < 1e-3f), Is.True, "un sommet d'une lettre n'est pas posé sur le sol");
            Assert.That(sommets.Max(p => p.y) - sommets.Min(p => p.y), Is.GreaterThan(5f), "échantillon vide : le sol sous le nom est plat");
            // Les carreaux d'une lettre lisent l'atlas d'un bord à l'autre de son carré, sans trou : leurs coordonnées vont en ligne droite.
            var uv = new List<Vector2>(); m.GetUVs(0, uv);
            for (int ligne = 0; ligne < cote; ligne++)
                for (int colonne = 1; colonne + 1 < cote; colonne++)
                {
                    int k = ligne * cote + colonne;
                    Assert.That((uv[k] - (uv[k - 1] + uv[k + 1]) / 2f).magnitude, Is.LessThan(1e-5f), "les carreaux de la première lettre ne lisent pas l'atlas en ligne droite");
                    Assert.That((uv[k] - uv[k - 1]).magnitude, Is.GreaterThan(1e-5f));
                }
        }

        [Test] public void Une_petite_lettre_reste_un_seul_carre_et_sans_sol_donne_le_nom_est_a_plat()
        {
            NomCourbe petit = Ecrire(16f, 10f, Sol); Voir(petit.Corps * ECRAN_PX / (2f * 60f));
            Assert.That(petit.Corps, Is.LessThan(NomsCourbes.CARREAU_KM / 2f)); Assert.That(petit.Maillage.vertexCount, Is.EqualTo(6 * 4), "une petite lettre est découpée");
            Assert.That(petit.Maillage.vertices.All(p => (p - Sol(new Vector2(p.x, p.z))).magnitude < 1e-3f), Is.True);
            noms.Dispose(); NomCourbe plat = Ecrire(16f, 10f, null); Voir(plat.Corps * ECRAN_PX / (2f * 60f));
            Assert.That(plat.Maillage.vertices.All(p => p.y == NomsCourbes.HAUTEUR), Is.True, "sans sol donné, le nom n'est pas à plat à sa hauteur");
        }

        // Un nom de l'atlas s'écrit tel que servi, espacé, ses lettres penchées vers l'est ; un nom de pays, en capitales droites.
        // Le tracé est la droite d'ouest en est : le haut des lettres est au nord, et le pied d'une lettre est à l'ouest de son haut.
        [Test] public void Un_nom_de_l_atlas_s_ecrit_en_italique_espace_et_un_pays_en_capitales_droites()
        {
            noms = new NomsCourbes(racine.transform, SocleInterface.Police(titre: true), SocleInterface.Couleur("encre"), SocleInterface.Couleur("papier"), null);
            noms.Ecrire(new[] { ("mer témoin", "Mer du Nord", Vector2.zero, Vector2.right, 3f, StyleDeNom.Italique), ("pays témoin", "Mer du Nord", new Vector2(0f, 50f), Vector2.right, 3f, StyleDeNom.Capitales) });
            NomCourbe mer = noms.Noms[0], pays = noms.Noms[1];
            Assert.That((mer.Ecrit, mer.Style, pays.Ecrit, pays.Style), Is.EqualTo(("Mer du Nord", StyleDeNom.Italique, "MER DU NORD", StyleDeNom.Capitales)), "les styles ne gardent pas le nom servi");
            Assert.That((mer.Corps, pays.Corps), Is.EqualTo((3f, 3f)).Using<(float, float)>((a, b) => Mathf.Abs(a.Item1 - b.Item1) < 1e-2f && Mathf.Abs(a.Item2 - b.Item2) < 1e-2f ? 0 : 1), "le corps donné n'est pas tenu");
            Assert.That(mer.Trace.Centre, Is.EqualTo(Vector2.zero));
            // L'italique s'espace : d'une lettre à la suivante, il avance plus que la police seule.
            Font police = noms.Police; police.RequestCharactersInTexture("Me", 64);
            bool lues = police.GetCharacterInfo('M', out CharacterInfo em, 64); lues &= police.GetCharacterInfo('e', out CharacterInfo e, 64); Assert.That(lues, Is.True);
            float naturelle = (em.advance + e.advance) / 2f / 64f, avancee = (mer.Compose.Lettres[1].Point.x - mer.Compose.Lettres[0].Point.x) / mer.Corps;
            Assert.That(avancee, Is.EqualTo(naturelle + NomsCourbes.ESPACEMENT_DE_L_ITALIQUE).Within(1e-3f), "l'italique ne s'espace pas");
            Voir(3f * ECRAN_PX / (2f * 30f)); Assert.That((mer.Opacite, pays.Opacite), Is.EqualTo((1f, 1f)));
            // La première lettre, un seul carré : ses deux coins de gauche, du pied au haut, dérivent vers l'est de la pente de l'italique.
            Vector3[] m = mer.Maillage.vertices, p = pays.Maillage.vertices;
            Assert.That((m[2].x - m[0].x) / (m[2].z - m[0].z), Is.EqualTo(NomsCourbes.PENTE_DE_L_ITALIQUE).Within(1e-3f), "les lettres de l'italique ne penchent pas");
            Assert.That(p[2].x - p[0].x, Is.EqualTo(0f).Within(1e-4f), "les capitales penchent"); Assert.That(m[2].z - m[0].z, Is.GreaterThan(0f));
            // Un nom sans corps ou sans texte n'est pas écrit.
            noms.Ecrire(new[] { ("vide", "", Vector2.zero, Vector2.right, 3f, StyleDeNom.Italique), ("nul", "Rhin", Vector2.zero, Vector2.right, 0f, StyleDeNom.Italique) });
            Assert.That(noms.Noms, Is.Empty);
        }

        // Le nom du pays du joueur ne se cache jamais faute de taille : de loin, ses lignes s'agrandissent ensemble autour du milieu de son tracé
        // jusqu'à ce que le nom se lise, et un autre pays aussi petit se cache comme avant. De près, il revient à sa taille ; de trop près, il
        // s'efface comme les autres. Sans joueur, il se cache aussi.
        [Test] public void Le_nom_du_joueur_reste_lisible_de_loin_et_un_autre_petit_pays_se_cache()
        {
            noms = new NomsCourbes(racine.transform, SocleInterface.Police(titre: true), SocleInterface.Couleur("encre"), SocleInterface.Couleur("papier"), null);
            var ici = new TraceDeNom(new Vector2(-60f, 0f), Vector2.right, -12f, 12f, 0f, 0f, 0f, 10f, 100); var la = new TraceDeNom(new Vector2(60f, 0f), Vector2.right, -12f, 12f, 0f, 0f, 0f, 10f, 100);
            noms.Ecrire(new (string, string, string, string, TraceDeNom)[] { ("seigneurie-1", "Duché de Bar", "Bar", "France", ici), ("puissance-9", "Lorraine", null, null, la) });
            NomCourbe bar = noms.Noms[0], lorraine = noms.Noms[1]; float corps = bar.Base.Corps; Vector2 milieu = ici.Point(0f);
            void A(float px) { camera.orthographicSize = corps * ECRAN_PX / (2f * px); noms.Suivre(camera); }
            A(4f); Assert.That((bar.Opacite, lorraine.Opacite), Is.EqualTo((0f, 0f)), "contre-épreuve : sans joueur, un nom de 4 pixels se lit");
            noms.PaysDuJoueur = "seigneurie-1"; A(4f);
            Assert.That(bar.CorpsPx, Is.EqualTo(NomsCourbes.CORPS_DU_JOUEUR_PX).Within(0.2f), "le nom du joueur ne prend pas un corps lisible"); Assert.That(bar.Opacite, Is.EqualTo(1f));
            Assert.That(bar.Rendu.enabled && bar.Maillage.vertexCount > 0, Is.True, "le nom du joueur n'est pas dessiné");
            Assert.That(lorraine.Opacite, Is.Zero, "un autre petit pays se lit"); Assert.That(lorraine.Agrandissement, Is.EqualTo(1f));
            Assert.That(bar.Agrandissement, Is.EqualTo(NomsCourbes.CORPS_DU_JOUEUR_PX / 4f).Within(0.05f));
            // Agrandi autour du milieu de son tracé : ses lettres dans le même ordre, à pas égaux grandis d'autant, et sa maison et sa vassalité avec lui.
            var l = bar.Compose.Lettres; Assert.That(((l[0].Point + l[l.Count - 1].Point) / 2f - milieu).magnitude, Is.LessThan(0.05f * bar.Corps), "le nom ne reste pas centré sur son tracé");
            Assert.That((l[1].Point - l[0].Point).magnitude, Is.EqualTo((bar.Base.Lettres[1].Point - bar.Base.Lettres[0].Point).magnitude * bar.Agrandissement).Within(1e-3f));
            Assert.That((bar.Maison.Agrandissement, bar.Vassalite.Agrandissement), Is.EqualTo((bar.Agrandissement, bar.Agrandissement)), "la maison et la vassalité ne suivent pas le nom");
            Assert.That(bar.Maison.Compose.Lettres.Max(p => p.Point.y), Is.LessThan(l.Min(p => p.Point.y)), "la maison n'est plus sous le nom");
            // De près, le nom revient à sa taille ; de trop près, il s'efface.
            A(60f); Assert.That(bar.Agrandissement, Is.EqualTo(1f)); Assert.That(bar.Compose, Is.SameAs(bar.Base)); Assert.That(bar.Opacite, Is.EqualTo(1f));
            A(NomsCourbes.DISPARU * ECRAN_PX); Assert.That(bar.Opacite, Is.Zero, "le nom du joueur ne s'efface pas de trop près");
            noms.PaysDuJoueur = null; A(4f); Assert.That((bar.Opacite, bar.Agrandissement), Is.EqualTo((0f, 1f)), "le nom reste agrandi sans joueur");
        }

        // La maison du pays s'écrit en petit sous son nom, sur le même arc descendu d'environ un corps ; un pays qui porte
        // le nom de sa maison n'a qu'une ligne. Le tracé témoin est la droite d'ouest en est : le haut des lettres est au nord.
        [Test] public void La_maison_s_ecrit_en_petit_au_sud_du_nom_et_suit_son_opacite()
        {
            noms = new NomsCourbes(racine.transform, SocleInterface.Police(titre: true), SocleInterface.Couleur("encre"), SocleInterface.Couleur("papier"), null);
            var trace = new TraceDeNom(Vector2.zero, Vector2.right, -300f, 300f, 0f, 0f, 0f, 300f, 100);
            noms.Ecrire(new[] { ("puissance-10", "Bohême", "Luxembourg", trace), ("seigneurie-1", "Bar", "BAR", trace), ("puissance-2", "France", (string)null, trace) });
            Assert.That(noms.Noms.Select(n => n.Texte), Is.EqualTo(new[] { "Bohême", "Bar", "France" }), "les noms des pays ne restent pas ceux servis");
            NomCourbe boheme = noms.Noms[0], maison = boheme.Maison;
            Assert.That(maison, Is.Not.Null, "la Bohême n'écrit pas sa maison"); Assert.That((maison.Texte, maison.Ecrit, maison.Pays, maison.NomDuPays), Is.EqualTo(("Luxembourg", "LUXEMBOURG", "puissance-10", boheme)));
            Assert.That(noms.Noms[1].Maison, Is.Null, "un pays qui porte le nom de sa maison a deux lignes"); Assert.That(noms.Noms[2].Maison, Is.Null, "un pays sans maison servie a deux lignes");
            Assert.That(maison.Corps, Is.LessThanOrEqualTo(NomsCourbes.PART_DE_LA_MAISON * boheme.Corps + 1e-4f)); Assert.That(maison.Corps, Is.GreaterThan(0.2f * boheme.Corps), "la maison est illisible à côté du nom");
            float nord = maison.Compose.Lettres.Max(l => l.Point.y), sud = boheme.Compose.Lettres.Min(l => l.Point.y);
            Assert.That(nord, Is.LessThan(sud), "la maison n'est pas au sud du nom");
            Assert.That(sud - nord, Is.EqualTo(NomsCourbes.ECART_DE_LA_MAISON * boheme.Corps).Within(1e-3f), "les deux lignes ne sont pas à un corps l'une de l'autre");
            Assert.That(racine.GetComponentsInChildren<MeshFilter>(true).Count(f => f.name.StartsWith("Maison du pays ")), Is.EqualTo(1));
            // Lisible, le nom montre sa maison ; de plus loin, la maison se cache la première ; de trop près, elle s'efface avec lui.
            Voir(boheme.Corps * ECRAN_PX / (2f * 60f)); Assert.That((boheme.Opacite, maison.Opacite), Is.EqualTo((1f, 1f))); Assert.That(maison.Rendu.enabled && maison.Maillage.vertexCount > 0, Is.True, "la maison lisible n'est pas dessinée");
            Voir(boheme.Corps * ECRAN_PX / (2f * 14f)); Assert.That(boheme.Opacite, Is.EqualTo(1f)); Assert.That(maison.Opacite, Is.Zero, "une maison trop petite pour se lire se montre"); Assert.That(maison.Rendu.enabled, Is.False);
            Voir(boheme.Corps * ECRAN_PX / (2f * NomsCourbes.DISPARU * ECRAN_PX)); Assert.That(boheme.Opacite, Is.Zero); Assert.That(maison.Opacite, Is.Zero, "la maison reste quand le nom s'efface");
            noms.Ecrire(new[] { ("puissance-2", "France", (string)null, trace) }); Assert.That(racine.GetComponentsInChildren<MeshFilter>(true).Count(f => f.name.StartsWith("Maison du pays ")), Is.Zero, "la maison d'avant reste dessinée");
        }

        // Un vassal porte sous son nom une ligne de plus, en italique et plus petite que la maison : sous la maison quand il en a une, sous le nom sinon.
        // Elle suit la règle de la maison : plus petite, elle se cache la première de loin, et s'efface avec le nom de près.
        [Test] public void La_vassalite_s_ecrit_en_italique_sous_la_maison_ou_le_nom_et_suit_son_opacite()
        {
            noms = new NomsCourbes(racine.transform, SocleInterface.Police(titre: true), SocleInterface.Couleur("encre"), SocleInterface.Couleur("papier"), null);
            var trace = new TraceDeNom(Vector2.zero, Vector2.right, -300f, 300f, 0f, 0f, 0f, 300f, 100);
            noms.Ecrire(new[] { ("puissance-42", "Guyenne", "Lancastre-Aquitaine", "Angleterre", trace), ("puissance-40", "Bourgogne", (string)null, "France", trace), ("puissance-1", "Angleterre", "Lancastre", (string)null, trace) });
            Assert.That(noms.Noms.Count, Is.EqualTo(3), "la vassalité est comptée comme un nom de pays");
            NomCourbe guyenne = noms.Noms[0], bourgogne = noms.Noms[1], angleterre = noms.Noms[2];
            Assert.That(angleterre.Vassalite, Is.Null, "un pays sans suzerain écrit une vassalité"); Assert.That(angleterre.Maison, Is.Not.Null, "échantillon vide : l'Angleterre n'écrit pas sa maison");
            NomCourbe de = guyenne.Vassalite, deLa = bourgogne.Vassalite;
            Assert.That(de, Is.Not.Null, "la Guyenne n'écrit pas sa vassalité"); Assert.That(deLa, Is.Not.Null, "la Bourgogne n'écrit pas sa vassalité");
            Assert.That((de.Texte, de.Style, de.Pays, de.NomDuPays), Is.EqualTo(("vassal d'Angleterre", StyleDeNom.Italique, "puissance-42", guyenne)));
            Assert.That((deLa.Texte, deLa.Style, deLa.Pays, deLa.NomDuPays), Is.EqualTo(("vassal de France", StyleDeNom.Italique, "puissance-40", bourgogne)));
            Assert.That(noms.Lignes.Count, Is.EqualTo(3 + 2 + 2), "les lignes ne sont pas : trois noms, deux maisons, deux vassalités"); Assert.That(noms.Lignes.Contains(de) && noms.Lignes.Contains(deLa), Is.True, "la vassalité ne réserve pas sa place");
            Assert.That(racine.GetComponentsInChildren<MeshFilter>(true).Count(f => f.name.StartsWith("Vassalité du pays ")), Is.EqualTo(2));
            // La place : la Guyenne l'écrit sous sa maison, plus petite qu'elle ; la Bourgogne, qui n'a pas de maison, sous son nom.
            NomCourbe maison = guyenne.Maison; Assert.That(maison, Is.Not.Null, "échantillon vide : la Guyenne n'écrit pas sa maison"); Assert.That(bourgogne.Maison, Is.Null);
            Assert.That(de.Corps, Is.LessThan(maison.Corps), "la vassalité n'est pas plus petite que la maison"); Assert.That(de.Corps, Is.GreaterThan(0.1f * guyenne.Corps), "la vassalité est illisible à côté du nom");
            Assert.That(de.Corps, Is.LessThanOrEqualTo(NomsCourbes.PART_DE_LA_VASSALITE * guyenne.Corps + 1e-4f)); Assert.That(deLa.Corps, Is.LessThanOrEqualTo(NomsCourbes.PART_DE_LA_VASSALITE * bourgogne.Corps + 1e-4f));
            float basDeLaMaison = maison.Compose.Lettres.Min(l => l.Point.y) - maison.Corps / 2f, hautDeLaVassalite = de.Compose.Lettres.Max(l => l.Point.y) + de.Corps / 2f;
            Assert.That(hautDeLaVassalite, Is.LessThan(basDeLaMaison), "les lettres de la vassalité touchent celles de la maison");
            Assert.That(de.Compose.Lettres.Max(l => l.Point.y), Is.LessThan(maison.Compose.Lettres.Min(l => l.Point.y)), "la vassalité n'est pas au sud de la maison");
            float basDuNom = bourgogne.Compose.Lettres.Min(l => l.Point.y) - bourgogne.Corps / 2f;
            Assert.That(deLa.Compose.Lettres.Max(l => l.Point.y) + deLa.Corps / 2f, Is.LessThan(basDuNom), "les lettres de la vassalité touchent celles du nom"); Assert.That(deLa.Compose.Lettres.Max(l => l.Point.y), Is.LessThan(bourgogne.Compose.Lettres.Min(l => l.Point.y)), "la vassalité n'est pas au sud du nom");
            // L'opacité : à une distance où la maison se lit mais où la vassalité, plus petite, ne se lit plus, elle est cachée.
            Voir(de.Corps * ECRAN_PX / (2f * (NomsCourbes.LISIBLE_PX - NomsCourbes.FONDU_PX - 0.5f)));
            Assert.That(guyenne.Opacite, Is.EqualTo(1f)); Assert.That(maison.Opacite, Is.GreaterThan(0f), "échantillon vide : la maison ne se lit pas à cette distance");
            Assert.That(de.Opacite, Is.Zero, "une vassalité trop petite pour se lire se montre"); Assert.That(de.Rendu.enabled, Is.False);
            // Plus près, les deux se lisent, sans que le nom ne s'efface.
            Voir(de.Corps * ECRAN_PX / (2f * 20f)); Assert.That((guyenne.Opacite, maison.Opacite, de.Opacite), Is.EqualTo((1f, 1f, 1f)));
            Assert.That(de.Rendu.enabled && de.Maillage.vertexCount > 0, Is.True, "la vassalité lisible n'est pas dessinée"); Assert.That(deLa.Opacite, Is.EqualTo(1f)); Assert.That(deLa.Rendu.enabled, Is.True);
            // De plus loin, la maison se cache, et la vassalité avec elle.
            Voir(maison.Corps * ECRAN_PX / (2f * 5f)); Assert.That(guyenne.Opacite, Is.EqualTo(1f)); Assert.That(maison.Opacite, Is.Zero); Assert.That(de.Opacite, Is.Zero, "la vassalité se montre quand la maison est cachée");
            // De trop près, elle s'efface avec le nom.
            Voir(guyenne.Corps * ECRAN_PX / (2f * NomsCourbes.DISPARU * ECRAN_PX)); Assert.That(guyenne.Opacite, Is.Zero); Assert.That(de.Opacite, Is.Zero, "la vassalité reste quand le nom s'efface"); Assert.That(de.Rendu.enabled, Is.False);
            // Sans suzerain, plus aucune ligne de vassal n'est dessinée.
            noms.Ecrire(new[] { ("puissance-42", "Guyenne", "Lancastre-Aquitaine", (string)null, trace) });
            Assert.That(noms.Noms.Single().Vassalite, Is.Null); Assert.That(racine.GetComponentsInChildren<MeshFilter>(true).Count(f => f.name.StartsWith("Vassalité du pays ")), Is.Zero, "la vassalité d'avant reste dessinée");
        }

        // « vassal de » devant une consonne, « vassal d' » devant une voyelle, accentuée ou non ; le h reste aspiré (Hongrie, Hainaut, Hesse).
        [TestCase("Écosse", "vassal d'Écosse")] [TestCase("Angleterre", "vassal d'Angleterre")] [TestCase("Aragon", "vassal d'Aragon")] [TestCase("Ile-de-France", "vassal d'Ile-de-France")] [TestCase("Orléans", "vassal d'Orléans")]
        [TestCase("Utrecht", "vassal d'Utrecht")] [TestCase("Ypres", "vassal d'Ypres")] [TestCase("Ève", "vassal d'Ève")] [TestCase("Âge", "vassal d'Âge")] [TestCase("Île", "vassal d'Île")] [TestCase("Ôde", "vassal d'Ôde")] [TestCase("Ûr", "vassal d'Ûr")] [TestCase("Èze", "vassal d'Èze")] [TestCase("Êta", "vassal d'Êta")] [TestCase("Îles", "vassal d'Îles")] [TestCase("écosse", "vassal d'écosse")]
        [TestCase("France", "vassal de France")] [TestCase("Hongrie", "vassal de Hongrie")] [TestCase("Hainaut", "vassal de Hainaut")] [TestCase("Hesse", "vassal de Hesse")] [TestCase("Bohême", "vassal de Bohême")] [TestCase("Comté de Wurtemberg", "vassal de Comté de Wurtemberg")]
        public void La_vassalite_elide_devant_une_voyelle_et_jamais_devant_un_h(string suzerain, string attendu) => Assert.That(NomsCourbes.Vassalite(suzerain), Is.EqualTo(attendu));

        [TestCase(null)] [TestCase("")] [TestCase("  ")]
        public void Sans_suzerain_servi_la_vassalite_n_a_pas_de_texte(string suzerain) => Assert.That(NomsCourbes.Vassalite(suzerain), Is.Null);
    }
}
